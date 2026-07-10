"""FlyMail application settings.

Only Gmail proxy settings are persisted locally. OAuth client credentials are
managed by the Cloudflare OAuth Broker and must not be written to settings.json.
"""
import asyncio
import json
import os
from typing import Any, Dict

from utils.logger import get_logger

logger = get_logger("settings")

DATA_DIR = os.environ.get("FLYMAIL_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "gmail_proxy_enabled": False,
    "gmail_proxy_url": "",
}


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _normalize_settings(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = raw or {}
    return {
        "gmail_proxy_enabled": bool(raw.get("gmail_proxy_enabled", False)),
        "gmail_proxy_url": str(raw.get("gmail_proxy_url", "") or "").strip(),
    }


def _write_settings(settings: Dict[str, Any]) -> None:
    _ensure_data_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_normalize_settings(settings), f, ensure_ascii=False, indent=2)


def load_settings() -> Dict[str, Any]:
    """Load local settings and remove any legacy OAuth credential fields."""
    _ensure_data_dir()
    if not os.path.exists(SETTINGS_FILE):
        logger.debug("配置文件不存在，使用默认值: %s", SETTINGS_FILE)
        return dict(DEFAULT_SETTINGS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("加载配置失败: %s, 使用默认值", e)
        return dict(DEFAULT_SETTINGS)

    if not isinstance(saved, dict):
        logger.warning("配置文件格式不是对象，使用默认值")
        return dict(DEFAULT_SETTINGS)

    settings = _normalize_settings(saved)
    if saved != settings:
        _write_settings(settings)
        logger.info("已清理 settings.json 中的旧配置字段，仅保留 Gmail 代理设置")

    logger.debug(
        "加载配置成功: gmail_proxy_enabled=%s, gmail_proxy_url=%s",
        settings["gmail_proxy_enabled"],
        "有" if settings["gmail_proxy_url"] else "空",
    )
    return settings


def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Save non-sensitive local runtime settings."""
    current = load_settings()
    allowed_update = {k: v for k, v in settings.items() if k in DEFAULT_SETTINGS}
    current.update(allowed_update)
    current = _normalize_settings(current)
    _write_settings(current)

    logger.debug(
        "保存配置成功: gmail_proxy_enabled=%s, gmail_proxy_url=%s",
        current["gmail_proxy_enabled"],
        "有" if current["gmail_proxy_url"] else "空",
    )
    return current


def get_setting(key: str, default: Any = None) -> Any:
    settings = load_settings()
    return settings.get(key, default)


async def async_load_settings() -> Dict[str, Any]:
    return await asyncio.to_thread(load_settings)


async def async_save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(save_settings, settings)
