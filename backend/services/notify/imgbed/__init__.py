# -*- coding: utf-8 -*-
"""用户自建 Cloudflare 图床客户端。

全局模块：供需要公网图片 URL 的通知渠道复用（非单一渠道专属）。
"""
from services.notify.imgbed.client import (
    ImgbedClient,
    ImgbedConfigError,
    ImgbedError,
    get_imgbed_client,
)
from services.notify.imgbed.settings import (
    DEFAULT_IMGBED,
    load_imgbed_settings,
    normalize_imgbed,
)

__all__ = [
    "DEFAULT_IMGBED",
    "ImgbedClient",
    "ImgbedConfigError",
    "ImgbedError",
    "get_imgbed_client",
    "load_imgbed_settings",
    "normalize_imgbed",
]
