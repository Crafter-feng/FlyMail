# -*- coding: utf-8 -*-
"""统一 HTTP 客户端（可选注入 HTTP 代理，复用 Gmail 代理 URL）。"""
from __future__ import annotations

from typing import Optional

import httpx


def build_async_client(
    proxy_url: Optional[str] = None,
    timeout: float = 15.0,
) -> httpx.AsyncClient:
    """构建 httpx.AsyncClient；proxy_url 非空时走 HTTP 代理。

    兼容不同 httpx 版本的 proxy / proxies 参数名。
    """
    proxy_url = (proxy_url or "").strip() or None
    kwargs = {"timeout": timeout}
    if not proxy_url:
        return httpx.AsyncClient(**kwargs)
    # 优先新版 proxy= 参数
    try:
        return httpx.AsyncClient(proxy=proxy_url, **kwargs)
    except TypeError:
        return httpx.AsyncClient(proxies=proxy_url, **kwargs)
