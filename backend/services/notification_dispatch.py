# -*- coding: utf-8 -*-
"""通知通道分发（预留）。

P1：仅提供空实现钩子，应用内 WebSocket/DB 通知不依赖此模块的副作用。
P2+：在此读取 notification_channels 配置，对接 Webhook / Telegram / Bark 等。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("flymail.notification_dispatch")


async def dispatch(event: Dict[str, Any]) -> None:
    """分发统一通知事件到外部通道。

    当前为 no-op；调用方应忽略异常与返回值。
    """
    try:
        # 预留：读取用户启用的通道并异步发送
        # channel adapters will consume fields like subject/from_addr/body_preview/message_cache_id
        _ = event
        return
    except Exception as e:
        logger.debug("notification dispatch skipped: %s", e)
