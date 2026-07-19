# -*- coding: utf-8 -*-
"""通知渠道抽象基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from services.notify.types import ChannelMessage


class NotifyChannel(ABC):
    """外部通知渠道接口（一渠道一实现文件）。"""

    name: str = "base"

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        """校验配置；返回错误文案，通过则返回 None。"""

    @abstractmethod
    async def send(
        self,
        message: ChannelMessage,
        config: Dict[str, Any],
        *,
        user_uid: str = "",
    ) -> None:
        """发送通知；失败抛异常，由编排层记录。"""
