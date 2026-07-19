# -*- coding: utf-8 -*-
"""渠道注册表：一渠道一模块，便于扩展。"""
from __future__ import annotations

from typing import Dict

from services.notify.channels.base import NotifyChannel
from services.notify.channels.bark import BarkChannel
from services.notify.channels.telegram import TelegramChannel
from services.notify.channels.webhook import WebhookChannel

# 渠道名 -> 实例
_REGISTRY: Dict[str, NotifyChannel] = {
    "bark": BarkChannel(),
    "telegram": TelegramChannel(),
    "webhook": WebhookChannel(),
}


def get_channel(name: str) -> NotifyChannel | None:
    """按名称获取渠道实例。"""
    return _REGISTRY.get((name or "").strip().lower())


def list_channels() -> list[str]:
    """返回已注册渠道名列表。"""
    return list(_REGISTRY.keys())
