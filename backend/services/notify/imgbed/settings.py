# -*- coding: utf-8 -*-
"""图床配置读写（ext_notify_imgbed）。

全局配置：供所有「需要公网图片 URL」的通知渠道复用（当前为 Bark 图片模式，
后续其它渠道也可接入，非某一渠道专属）。
"""
from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

# 用户设置 key：整段 JSON
KEY_IMGBED = "ext_notify_imgbed"

# Deploy 按钮默认模板（公开仓路径；推送到 GitHub 后生效）
DEFAULT_DEPLOY_URL = (
    "https://deploy.workers.cloudflare.com/"
    "?url=https://github.com/DinDing1/FlyMail/tree/main/flymail-imgbed"
)

DEFAULT_IMGBED: Dict[str, Any] = {
    "base_url": "",
    "upload_token": "",
}


def normalize_imgbed(raw: Any) -> Dict[str, Any]:
    """规范化图床配置。

    无独立开关：填写了有效地址 + 上传密钥即视为已配置。
    兼容旧数据中的 enabled 字段（忽略，不参与判定）。
    """
    raw = raw if isinstance(raw, dict) else {}
    base = str(raw.get("base_url") or "").strip().rstrip("/")
    # 用户可能误填带路径后缀的地址
    for suffix in ("/upload", "/purge", "/health", "/i"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
    token = str(raw.get("upload_token") or "").strip()
    return {
        "base_url": base,
        "upload_token": token,
    }


def imgbed_is_ready(cfg: Dict[str, Any] | None) -> bool:
    """是否已配置完整（有合法 base_url + token）。"""
    cfg = cfg or {}
    base = str(cfg.get("base_url") or "").strip()
    token = str(cfg.get("upload_token") or "").strip()
    if not base or not token:
        return False
    try:
        p = urlparse(base)
        if p.scheme not in ("http", "https") or not p.netloc:
            return False
    except Exception:
        return False
    return True


async def load_imgbed_settings(user_uid: str) -> Dict[str, Any]:
    """从 user_settings 加载图床配置。"""
    from db import get_user_settings

    raw = await get_user_settings(user_uid, [KEY_IMGBED])
    return normalize_imgbed(raw.get(KEY_IMGBED))
