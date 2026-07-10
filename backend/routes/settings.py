"""设置管理路由

OAuth 授权已迁移到 Cloudflare Broker，本地不再保存客户端密钥。
本模块只保存 Gmail 网络代理和用户级聚合收件箱设置。
"""
from fastapi import APIRouter, Request

from services.settings import async_load_settings, async_save_settings
from schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    UnifiedSettingsRequest,
)

router = APIRouter(tags=["设置"])


# ==================== 辅助函数 ====================


def sync_gmail_config(settings: dict):
    """将 Gmail 网络代理设置同步到运行时配置。"""
    from providers.gmail import config as gmail_config

    gmail_config.GMAIL_PROXY_ENABLED = bool(settings.get("gmail_proxy_enabled", False))
    gmail_config.GMAIL_PROXY_URL = settings.get("gmail_proxy_url", "") or ""


async def reset_gmail_idle_connections():
    """代理设置变更后断开 Gmail IDLE 连接，让后台监听按新配置重建。"""
    try:
        from db import get_accounts
        from services.idle_manager import idle_manager

        accounts = await get_accounts("")
        for account in accounts:
            if account.provider == "gmail":
                await idle_manager.remove(account.id)
    except Exception:
        # 保存设置不能因为后台连接清理失败而失败；连接会在后续重连时读取新配置。
        pass


# ==================== 设置接口 ====================


@router.get("/api/settings", response_model=SettingsResponse, summary="获取 Gmail 网络代理设置")
async def get_settings():
    """获取本地 Gmail 代理设置。OAuth Client 密钥由 Cloudflare Broker 管理。"""
    settings = await async_load_settings()
    return {
        "gmail_proxy_enabled": bool(settings.get("gmail_proxy_enabled", False)),
        "gmail_proxy_url": settings.get("gmail_proxy_url", ""),
    }


@router.put("/api/settings", response_model=SettingsUpdateResponse, summary="更新 Gmail 网络代理设置")
async def update_settings(body: SettingsUpdateRequest):
    """更新 Gmail 网络代理设置，不保存任何 OAuth Client 密钥。"""
    update_data = body.model_dump(exclude_none=True)
    saved = await async_save_settings(update_data)
    sync_gmail_config(saved)
    await reset_gmail_idle_connections()

    return {"success": True, "message": "设置已保存"}


# ==================== 聚合收件箱设置 ====================


@router.get("/api/settings/unified", summary="获取聚合收件箱设置")
async def get_unified_settings(request: Request):
    """获取聚合收件箱的设置：用户选择要聚合的邮箱账号列表

    修复 D1：unified_account_ids 改为按 user_uid 存储在 user_settings 表，避免多用户互相覆盖
    """
    from db import get_accounts, get_user_settings
    from deps import get_uid

    uid = await get_uid(request)
    accounts = await get_accounts(uid)

    # 从用户级配置表读取（D1 修复）
    user_settings = await get_user_settings(uid, ["unified_account_ids"])
    unified_ids = user_settings.get("unified_account_ids", [])

    return {
        "account_ids": unified_ids,
        "accounts": [
            {
                "id": a.id,
                "email": a.email,
                "provider": a.provider,
                "selected": a.id in unified_ids,
            }
            for a in accounts
        ],
    }


@router.put("/api/settings/unified", summary="保存聚合收件箱设置")
async def save_unified_settings(request: Request, body: UnifiedSettingsRequest):
    """保存聚合收件箱的账号ID列表

    修复 D1：unified_account_ids 改为按 user_uid 存储在 user_settings 表，避免多用户互相覆盖
    """
    from db import set_user_settings
    from deps import get_uid

    uid = await get_uid(request)
    account_ids = body.account_ids

    # 写入用户级配置表（D1 修复）
    await set_user_settings(uid, {"unified_account_ids": account_ids})

    return {"success": True}
