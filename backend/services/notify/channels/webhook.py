# -*- coding: utf-8 -*-
"""通用 Webhook 通知渠道。

向用户配置的 HTTP URL 发送 JSON：
- 文字模式：主题 / 元信息 / 正文（与 Bark、Telegram 同一套渲染数据）
- 图片模式：仅推送卡片 PNG（Base64），对齐 Telegram「只要图」；不依赖图床

鉴权：可选 Bearer Token；可选复用 Gmail 网络代理。
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from utils.logger import get_logger
from services.notify.channels.base import NotifyChannel
from services.notify.http_client import build_async_client
from services.notify.render import build_body_markdown, _format_mail_date, _s
from services.notify.types import ChannelMessage

logger = get_logger("notify.webhook")


def _valid_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


class WebhookChannel(NotifyChannel):
    """通用 Webhook：POST application/json。"""

    name = "webhook"

    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        cfg = config or {}
        url = str(cfg.get("url") or "").strip()
        if not url:
            return "请填写 Webhook URL"
        if not _valid_http_url(url):
            return "Webhook URL 须为合法 http/https 地址"
        return None

    async def _resolve_proxy(self, config: Dict[str, Any], user_uid: str) -> Optional[str]:
        """若开启 use_gmail_proxy，则读取 Gmail 代理 URL。"""
        if not config.get("use_gmail_proxy"):
            return None
        if not user_uid:
            logger.debug("Webhook 已勾选代理但 user_uid 为空，直连")
            return None
        try:
            from services.settings import get_gmail_proxy_settings

            ps = await get_gmail_proxy_settings(user_uid)
            if ps.get("gmail_proxy_enabled") and ps.get("gmail_proxy_url"):
                return str(ps["gmail_proxy_url"]).strip()
            logger.debug(
                "Webhook 已勾选复用 Gmail 代理，但代理未启用或 URL 为空，将直连"
            )
        except Exception as e:
            logger.warning("读取 Gmail 代理失败，Webhook 将直连: %s", e)
        return None

    def _auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """构建鉴权头：有 secret 时使用 Authorization: Bearer <secret>。"""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "FlyMail-Webhook/1.0",
        }
        secret = str(config.get("secret") or "").strip()
        if secret:
            # 允许用户直接填完整 "Bearer xxx" 或仅 token
            if secret.lower().startswith("bearer "):
                headers["Authorization"] = secret
            else:
                headers["Authorization"] = f"Bearer {secret}"
        return headers

    def _build_text_payload(self, message: ChannelMessage) -> Dict[str, Any]:
        """文字模式 JSON：结构化字段 + Markdown 正文。"""
        extra = dict(message.extra or {})
        # 与渠道共用的 Markdown（common 方言，通用 Webhook 易解析）
        if extra:
            body_md = build_body_markdown(extra, dialect="common")
        else:
            body_md = message.body or ""

        subject = _s(extra.get("subject"), "(无主题)")
        cc = str(extra.get("cc") or "").strip()
        payload: Dict[str, Any] = {
            "event": str(extra.get("type") or "new_mail"),
            "mode": "text",
            "title": message.title or "飞邮",
            "subject": subject,
            "body": body_md,
            "from": _s(extra.get("from_addr"), ""),
            "to": _s(extra.get("to_addr"), ""),
            "time": _format_mail_date(extra.get("mail_date")),
            "account": _s(extra.get("email"), ""),
            "preview": str(extra.get("body_preview") or "").strip(),
            "message_cache_id": str(extra.get("message_cache_id") or "").strip(),
        }
        # 无抄送时不输出空字段，减少噪音
        if cc:
            payload["cc"] = cc
        return payload

    def _build_image_payload(self, message: ChannelMessage) -> Dict[str, Any]:
        """图片模式：仅推送卡片图（Base64），对齐 Telegram 只要图。

        仍附带少量结构化元数据，方便自动化脚本识别；不附长正文/标题文案。
        """
        if not message.image_bytes:
            raise RuntimeError("图片模式缺少卡片数据，无法推送 Webhook")

        extra = dict(message.extra or {})
        b64 = base64.b64encode(message.image_bytes).decode("ascii")
        payload: Dict[str, Any] = {
            "event": str(extra.get("type") or "new_mail"),
            "mode": "image",
            "image_base64": b64,
            "image_content_type": "image/png",
            "filename": "flymail-notify.png",
            "subject": _s(extra.get("subject"), "(无主题)"),
            "message_cache_id": str(extra.get("message_cache_id") or "").strip(),
        }
        return payload

    async def send(
        self,
        message: ChannelMessage,
        config: Dict[str, Any],
        *,
        user_uid: str = "",
    ) -> None:
        err = self.validate_config(config)
        if err:
            raise ValueError(err)

        url = str(config.get("url") or "").strip()
        proxy_url = await self._resolve_proxy(config, user_uid)
        headers = self._auth_headers(config)

        mode = (message.mode or "text").strip().lower()
        if mode == "image":
            payload = self._build_image_payload(message)
            timeout = 45.0
        else:
            payload = self._build_text_payload(message)
            timeout = 20.0

        async with build_async_client(proxy_url=proxy_url, timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Webhook 请求失败 HTTP {resp.status_code}: {(resp.text or '')[:300]}"
                )

        via = "代理" if proxy_url else "直连"
        logger.info(
            "Webhook 推送成功 user_uid=%s mode=%s via=%s status=%s",
            user_uid or "-",
            mode,
            via,
            resp.status_code,
        )
