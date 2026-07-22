# -*- coding: utf-8 -*-
"""读写第三方通知配置（user_settings）。"""
from __future__ import annotations

from typing import Any, Dict

from db import get_user_settings, set_user_settings
from services.notify.imgbed.settings import (
    DEFAULT_DEPLOY_URL,
    DEFAULT_IMGBED,
    KEY_IMGBED,
    normalize_imgbed,
)

# 配置 key（与应用内铃铛无关）
KEY_ENABLED = "ext_notify_enabled"
KEY_DND_START = "ext_notify_dnd_start"
KEY_DND_END = "ext_notify_dnd_end"
KEY_MODE = "ext_notify_mode"
KEY_BARK = "ext_notify_bark"
KEY_TELEGRAM = "ext_notify_telegram"
KEY_WEBHOOK = "ext_notify_webhook"

DEFAULT_BARK: Dict[str, Any] = {
    "enabled": False,
    "server": "https://api.day.app",
    "device_key": "",
}

DEFAULT_TELEGRAM: Dict[str, Any] = {
    "enabled": False,
    "bot_token": "",
    "chat_id": "",
    "use_gmail_proxy": False,
}

DEFAULT_WEBHOOK: Dict[str, Any] = {
    "enabled": False,
    "url": "",
    # 可选密钥：通用=Bearer；钉钉/飞书=加签；企微忽略
    "secret": "",
    "use_gmail_proxy": False,
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "dnd_start": "21:00",
    "dnd_end": "07:00",
    # text | image
    # image：Telegram/企微直传；Bark/钉钉/飞书需图床；通用 Webhook Base64
    "mode": "text",
    "bark": dict(DEFAULT_BARK),
    "telegram": dict(DEFAULT_TELEGRAM),
    "webhook": dict(DEFAULT_WEBHOOK),
    "imgbed": dict(DEFAULT_IMGBED),
    "imgbed_deploy_url": DEFAULT_DEPLOY_URL,
}


def _norm_bark(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    server = str(raw.get("server") or DEFAULT_BARK["server"]).strip().rstrip("/")
    if not server:
        server = DEFAULT_BARK["server"]
    return {
        "enabled": bool(raw.get("enabled", False)),
        "server": server,
        "device_key": str(raw.get("device_key") or "").strip(),
    }


def _norm_telegram(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "enabled": bool(raw.get("enabled", False)),
        "bot_token": str(raw.get("bot_token") or "").strip(),
        "chat_id": str(raw.get("chat_id") or "").strip(),
        "use_gmail_proxy": bool(raw.get("use_gmail_proxy", False)),
    }


def _norm_webhook(raw: Any) -> Dict[str, Any]:
    """规范化 Webhook 配置。"""
    raw = raw if isinstance(raw, dict) else {}
    url = str(raw.get("url") or "").strip()
    return {
        "enabled": bool(raw.get("enabled", False)),
        "url": url,
        "secret": str(raw.get("secret") or "").strip(),
        "use_gmail_proxy": bool(raw.get("use_gmail_proxy", False)),
    }


def _norm_mode(mode: Any) -> str:
    m = str(mode or "text").strip().lower()
    return m if m in ("text", "image") else "text"


def _norm_hm(value: Any, default: str) -> str:
    s = str(value or default).strip()
    try:
        parts = s.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    except (TypeError, ValueError, IndexError):
        pass
    return default


async def load_ext_notify_settings(user_uid: str) -> Dict[str, Any]:
    """加载用户第三方通知配置（带默认值）。"""
    raw = await get_user_settings(
        user_uid,
        [
            KEY_ENABLED,
            KEY_DND_START,
            KEY_DND_END,
            KEY_MODE,
            KEY_BARK,
            KEY_TELEGRAM,
            KEY_WEBHOOK,
            KEY_IMGBED,
        ],
    )
    return {
        "enabled": bool(raw.get(KEY_ENABLED, DEFAULT_SETTINGS["enabled"])),
        "dnd_start": _norm_hm(raw.get(KEY_DND_START), DEFAULT_SETTINGS["dnd_start"]),
        "dnd_end": _norm_hm(raw.get(KEY_DND_END), DEFAULT_SETTINGS["dnd_end"]),
        "mode": _norm_mode(raw.get(KEY_MODE, DEFAULT_SETTINGS["mode"])),
        "bark": _norm_bark(raw.get(KEY_BARK)),
        "telegram": _norm_telegram(raw.get(KEY_TELEGRAM)),
        "webhook": _norm_webhook(raw.get(KEY_WEBHOOK)),
        "imgbed": normalize_imgbed(raw.get(KEY_IMGBED)),
        "imgbed_deploy_url": DEFAULT_DEPLOY_URL,
    }


async def save_ext_notify_settings(user_uid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """保存并返回规范化后的配置。"""
    data = data or {}
    bark = _norm_bark(data.get("bark"))
    telegram = _norm_telegram(data.get("telegram"))
    webhook = _norm_webhook(data.get("webhook"))
    imgbed = normalize_imgbed(data.get("imgbed"))

    settings = {
        KEY_ENABLED: bool(data.get("enabled", False)),
        KEY_DND_START: _norm_hm(data.get("dnd_start"), DEFAULT_SETTINGS["dnd_start"]),
        KEY_DND_END: _norm_hm(data.get("dnd_end"), DEFAULT_SETTINGS["dnd_end"]),
        KEY_MODE: _norm_mode(data.get("mode")),
        KEY_BARK: bark,
        KEY_TELEGRAM: telegram,
        KEY_WEBHOOK: webhook,
        KEY_IMGBED: imgbed,
    }
    await set_user_settings(user_uid, settings)
    return {
        "enabled": settings[KEY_ENABLED],
        "dnd_start": settings[KEY_DND_START],
        "dnd_end": settings[KEY_DND_END],
        "mode": settings[KEY_MODE],
        "bark": bark,
        "telegram": telegram,
        "webhook": webhook,
        "imgbed": imgbed,
        "imgbed_deploy_url": DEFAULT_DEPLOY_URL,
    }
