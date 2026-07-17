"""FlyMail application settings.

Gmail 代理按 user_uid 存 user_settings（多用户隔离）。
settings.json 仅作兼容回退（老版本全局配置），新写入不再依赖全局。
OAuth client credentials 由 Cloudflare OAuth Broker 管理，不得写入本地。
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

# user_settings 表中的代理键名
_PROXY_ENABLED_KEY = "gmail_proxy_enabled"
_PROXY_URL_KEY = "gmail_proxy_url"


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
    """Load local settings and remove any legacy OAuth credential fields.

    仅兼容旧全局 settings.json；多用户场景请用 get_gmail_proxy_settings(user_uid)。
    """
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
    """Save non-sensitive local runtime settings（兼容旧全局文件，新代码优先 user_settings）。"""
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


# ==================== 按用户隔离的 Gmail 代理 ====================


def apply_proxy_to_credentials_extra(
    extra: Dict[str, Any] | None,
    proxy_settings: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """把用户级代理写入 Credentials.extra（不落库，仅运行时）。

    extra 原有字段（如 email）保留；代理键覆盖写入。
    """
    out = dict(extra or {})
    ps = _normalize_settings(proxy_settings)
    out[_PROXY_ENABLED_KEY] = ps["gmail_proxy_enabled"]
    out[_PROXY_URL_KEY] = ps["gmail_proxy_url"]
    return out


def resolve_gmail_proxy_url(extra: Dict[str, Any] | None) -> str:
    """从 Credentials.extra 解析出实际可用的代理 URL；关闭或未配则空串。"""
    if not extra:
        return ""
    if not bool(extra.get(_PROXY_ENABLED_KEY)):
        return ""
    return str(extra.get(_PROXY_URL_KEY) or "").strip()


async def get_gmail_proxy_settings(user_uid: str) -> Dict[str, Any]:
    """读取指定用户的 Gmail 代理；user_settings 无记录时回退 settings.json。"""
    from db import get_user_settings

    uid = (user_uid or "").strip()
    if uid:
        try:
            raw = await get_user_settings(uid, [_PROXY_ENABLED_KEY, _PROXY_URL_KEY])
            # 用户表有任一键即视为已配置（含显式关闭）
            if _PROXY_ENABLED_KEY in raw or _PROXY_URL_KEY in raw:
                return _normalize_settings({
                    "gmail_proxy_enabled": raw.get(_PROXY_ENABLED_KEY, False),
                    "gmail_proxy_url": raw.get(_PROXY_URL_KEY, ""),
                })
        except Exception as e:
            logger.debug("读取 user_settings 代理失败，回退全局: %s", e)

    # 兼容旧全局配置
    return await async_load_settings()


async def save_gmail_proxy_settings(user_uid: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """按 user_uid 写入 Gmail 代理到 user_settings（不写进程全局 gmail_config）。"""
    from db import set_user_settings

    uid = (user_uid or "").strip()
    if not uid:
        raise ValueError("user_uid 不能为空")

    normalized = _normalize_settings(settings)
    await set_user_settings(uid, {
        _PROXY_ENABLED_KEY: 1 if normalized["gmail_proxy_enabled"] else 0,
        _PROXY_URL_KEY: normalized["gmail_proxy_url"],
    })
    logger.info(
        "已保存用户 Gmail 代理: user_uid=%s, enabled=%s, url=%s",
        uid,
        normalized["gmail_proxy_enabled"],
        "有" if normalized["gmail_proxy_url"] else "空",
    )
    return normalized
