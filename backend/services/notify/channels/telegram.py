# -*- coding: utf-8 -*-
"""Telegram 通知渠道。

可复用 Gmail 网络代理（get_gmail_proxy_settings），不另建代理配置。
文字模式：MarkdownV2 正文。
图片模式：sendPhoto 仅上传 B 方案卡片，不附标题/caption。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from utils.logger import get_logger
from services.notify.channels.base import NotifyChannel
from services.notify.http_client import build_async_client
from services.notify.types import ChannelMessage
from services.notify.render import build_body_markdown, truncate_telegram_text, _escape_mdv2

logger = get_logger("notify.telegram")


class TelegramChannel(NotifyChannel):
    name = "telegram"

    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        cfg = config or {}
        if not str(cfg.get("bot_token") or "").strip():
            return "请填写 Telegram Bot Token"
        if not str(cfg.get("chat_id") or "").strip():
            return "请填写 Telegram Chat ID"
        return None

    async def _resolve_proxy(self, config: Dict[str, Any], user_uid: str) -> Optional[str]:
        """若开启 use_gmail_proxy，则读取 Gmail 代理 URL。"""
        if not config.get("use_gmail_proxy"):
            return None
        if not user_uid:
            logger.debug("Telegram 已勾选代理但 user_uid 为空，直连")
            return None
        try:
            from services.settings import get_gmail_proxy_settings

            ps = await get_gmail_proxy_settings(user_uid)
            if ps.get("gmail_proxy_enabled") and ps.get("gmail_proxy_url"):
                return str(ps["gmail_proxy_url"]).strip()
            logger.debug(
                "Telegram 已勾选复用 Gmail 代理，但代理未启用或 URL 为空，将直连"
            )
        except Exception as e:
            logger.warning("读取 Gmail 代理失败，Telegram 将直连: %s", e)
        return None

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

        token = str(config.get("bot_token") or "").strip()
        chat_id = str(config.get("chat_id") or "").strip()
        proxy_url = await self._resolve_proxy(config, user_uid)

        if message.mode == "image":
            await self._send_photo(
                message,
                token=token,
                chat_id=chat_id,
                proxy_url=proxy_url,
                user_uid=user_uid,
            )
            return

        # —— 文字模式 ——
        # 标题行 + 与 Bark 一致的 Markdown 正文（MarkdownV2）
        title_raw = message.title or "飞邮"
        title_line = f"*✈ {_escape_mdv2(title_raw)}*"
        if message.extra:
            body_part = build_body_markdown(message.extra, dialect="telegram")
        else:
            body_part = _escape_mdv2(message.body or "")
        text = f"{title_line}\n\n{body_part}"
        # Telegram 文本上限 4096，超长截断避免整条失败
        text = truncate_telegram_text(text)

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        }

        async with build_async_client(proxy_url=proxy_url, timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Telegram 请求失败 HTTP {resp.status_code}: {(resp.text or '')[:300]}"
                )
            try:
                data = resp.json()
            except Exception as e:
                raise RuntimeError(f"Telegram 响应非 JSON: {e}") from e
            if not data.get("ok"):
                desc = data.get("description") or data
                raise RuntimeError(f"Telegram 返回错误: {desc}")

        via = "代理" if proxy_url else "直连"
        logger.info("Telegram 推送成功 user_uid=%s via=%s", user_uid or "-", via)

    async def _send_photo(
        self,
        message: ChannelMessage,
        *,
        token: str,
        chat_id: str,
        proxy_url: Optional[str],
        user_uid: str,
    ) -> None:
        """图片模式：仅 multipart 上传卡片图，不附 caption/标题。"""
        if not message.image_bytes:
            raise RuntimeError("图片模式缺少卡片数据，无法推送 Telegram")

        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        # 只要图片：不传 caption，避免再出现「飞邮 / 主题」文字
        data = {
            "chat_id": chat_id,
        }
        files = {
            "photo": ("flymail-notify.png", message.image_bytes, "image/png"),
        }

        async with build_async_client(proxy_url=proxy_url, timeout=45.0) as client:
            resp = await client.post(url, data=data, files=files)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Telegram 图片发送失败 HTTP {resp.status_code}: {(resp.text or '')[:300]}"
                )
            try:
                result = resp.json()
            except Exception as e:
                raise RuntimeError(f"Telegram 响应非 JSON: {e}") from e
            if not result.get("ok"):
                desc = result.get("description") or result
                raise RuntimeError(f"Telegram 图片发送错误: {desc}")

        via = "代理" if proxy_url else "直连"
        logger.info("Telegram 图片推送成功 user_uid=%s via=%s", user_uid or "-", via)
