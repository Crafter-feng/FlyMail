# -*- coding: utf-8 -*-
"""Bark 通知渠道。

文字模式标题固定「飞邮」；仅 Server + Device Key。
兼容用户粘贴完整推送链接时自动提取 Key。

文字模式：Markdown 正文 + 项目 LOGO 图标（icon）。
图片模式：对齐 Telegram——仅推送大图（image），不传 title/icon，不附文案。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from utils.logger import get_logger
from services.notify.channels.base import NotifyChannel
from services.notify.http_client import build_async_client
from services.notify.types import ChannelMessage
from services.notify.render import build_body_markdown

logger = get_logger("notify.bark")

# 飞邮项目 LOGO（公开直链，Bark 拉取后显示为通知图标）
DEFAULT_BARK_ICON = (
    "https://raw.githubusercontent.com/cliii-one/FnDepot/main/flymail/ICON.PNG"
)


def _normalize_bark_config(config: Dict[str, Any]) -> Tuple[str, str]:
    """规范化 Server 与 Device Key。

    支持：
    - device_key 为纯 key
    - device_key 为完整 URL：https://api.day.app/{key} 或 https://host/{key}/title/body
    - server 末尾多余斜杠自动去掉
    """
    server = str((config or {}).get("server") or "https://api.day.app").strip().rstrip("/")
    raw_key = str((config or {}).get("device_key") or "").strip()

    if not raw_key:
        return server, ""

    # 用户误把完整推送链接贴进 Device Key
    if raw_key.startswith("http://") or raw_key.startswith("https://"):
        parsed = urlparse(raw_key)
        if parsed.scheme and parsed.netloc:
            server = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            parts = [p for p in (parsed.path or "").split("/") if p]
            if parts:
                raw_key = parts[0]
            else:
                raw_key = ""

    # 去掉路径残留（如 key/title/body）
    if "/" in raw_key:
        raw_key = raw_key.split("/")[0].strip()

    return server, raw_key


def _friendly_bark_error(status_code: int, text: str) -> str:
    """将 Bark 原始错误转成可操作的中文提示。"""
    lower = (text or "").lower()
    if "failed to get" in lower and "device token" in lower:
        return (
            "Bark Device Key 无效或未在该 Server 注册。"
            "请打开 Bark App 复制当前设备 Key，并确认 Server 与 App 一致"
            "（官方一般为 https://api.day.app；自建服必须填自建地址）。"
        )
    if status_code == 400:
        return f"Bark 请求参数错误 HTTP 400: {(text or '')[:200]}"
    if status_code in (401, 403):
        return f"Bark 鉴权失败 HTTP {status_code}，请检查 Server / Key"
    if status_code >= 500:
        return f"Bark 服务端异常 HTTP {status_code}，请稍后重试"
    return f"Bark 请求失败 HTTP {status_code}: {(text or '')[:300]}"


class BarkChannel(NotifyChannel):
    name = "bark"

    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        _, key = _normalize_bark_config(config or {})
        if not key:
            return "请填写 Bark Device Key"
        return None

    async def send(
        self,
        message: ChannelMessage,
        config: Dict[str, Any],
        *,
        user_uid: str = "",
    ) -> None:
        """按消息模式发送文字或图片。"""
        err = self.validate_config(config)
        if err:
            raise ValueError(err)

        server, device_key = _normalize_bark_config(config or {})
        url = f"{server}/{device_key}"

        mode = (message.mode or "text").strip().lower()
        if mode == "image":
            await self._send_image(url, message, user_uid=user_uid, server=server)
        else:
            await self._send_text(url, message, user_uid=user_uid, server=server)

    async def _send_text(
        self,
        url: str,
        message: ChannelMessage,
        *,
        user_uid: str,
        server: str,
    ) -> None:
        payload: Dict[str, Any] = {
            "title": message.title or "飞邮",
            "body": message.body or "",
            "icon": DEFAULT_BARK_ICON,
        }
        if message.extra:
            payload["markdown"] = build_body_markdown(message.extra, dialect="common")
        await self._post_json(url, payload, user_uid=user_uid, server=server)

    async def _send_image(
        self,
        url: str,
        message: ChannelMessage,
        *,
        user_uid: str,
        server: str,
    ) -> None:
        """图片模式：对齐 Telegram——只推大图，不推标题/图标/正文。

        Bark 协议说明：
        - ``image``：通知大图（Notification Service 拉取展示）
        - ``icon``：左侧小图标（图片模式故意不传，避免看起来像“只有小图”）
        - ``title``：不传；``body`` 仅用零宽占位（Bark/APNs 要求 alert 非全空，
          否则会被改成 “Empty Message”）

        不静默降级为文字；必须由分发层上传图床后写入 extra.image_url。
        不再在渠道内二次上传图床（避免无效兜底路径）。
        """
        image_url = str((message.extra or {}).get("image_url") or "").strip()
        if not image_url:
            raise RuntimeError(
                "Bark 图片模式缺少图片 URL：请在通知设置配置 Cloudflare 图床，"
                "并由分发层完成上传后再发送。"
            )

        if not (image_url.startswith("https://") or image_url.startswith("http://")):
            raise RuntimeError(
                f"Bark 图片 URL 无效（需公网 http/https）: {image_url[:120]}"
            )
        # Bark App 需公网拉取图片，强烈建议 HTTPS
        if image_url.startswith("http://"):
            logger.warning(
                "Bark 图片 URL 为 HTTP（非 HTTPS），大图可能无法展示 user_uid=%s",
                user_uid or "-",
            )

        # 只发大图：不传 title / icon / subtitle
        # body 必须非空（见 bark-server IsEmptyAlert），用零宽字符占位
        payload: Dict[str, Any] = {
            "body": "​",
            "image": image_url,
        }
        await self._post_json(url, payload, user_uid=user_uid, server=server)

    async def _post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        *,
        user_uid: str,
        server: str,
    ) -> None:
        async with build_async_client(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                text = (resp.text or "")[:400]
                logger.warning(
                    "Bark 推送失败 user_uid=%s status=%s body=%s",
                    user_uid or "-",
                    resp.status_code,
                    text,
                )
                raise RuntimeError(_friendly_bark_error(resp.status_code, text))
            try:
                data = resp.json()
                code = data.get("code")
                if code is not None and int(code) != 200:
                    msg = str(data.get("message") or data)
                    raise RuntimeError(_friendly_bark_error(400, msg))
            except RuntimeError:
                raise
            except Exception:
                # 非 JSON 且 HTTP 已 2xx 时视为成功
                pass

        kind = "image" if "image" in payload and not payload.get("title") else "text"
        logger.info(
            "Bark 推送成功 user_uid=%s server=%s mode=%s",
            user_uid or "-",
            server,
            kind,
        )
