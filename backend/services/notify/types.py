# -*- coding: utf-8 -*-
"""第三方通知通用数据结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ChannelMessage:
    """发往外部渠道的统一消息体。"""

    title: str
    body: str
    mode: str = "text"  # text | image
    # 原始事件字段，便于渠道扩展
    extra: Dict[str, Any] = field(default_factory=dict)
    # 图片模式：PNG 字节（Telegram sendPhoto / Webhook Base64 直传；Bark 先上传图床再取 image_url）
    image_bytes: Optional[bytes] = None  # PNG：Telegram/Webhook 直传；Bark 先上图床

