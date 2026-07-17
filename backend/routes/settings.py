"""设置管理路由

OAuth 授权已迁移到 Cloudflare Broker，本地不再保存客户端密钥。
Gmail 网络代理按 user_uid 存 user_settings，连接时经 Credentials.extra 注入。
"""
import asyncio
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Request

from services.settings import (
    get_gmail_proxy_settings,
    save_gmail_proxy_settings,
)
from deps import get_uid
from schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    UnifiedSettingsRequest,
    ProxyTestRequest,
    ProxyTestResponse,
)

router = APIRouter(tags=["设置"])


# ==================== 辅助函数 ====================


async def reset_gmail_idle_connections(user_uid: str = ""):
    """代理设置变更后断开本用户 Gmail IDLE 连接，让后台监听按新配置重建。

    只重置指定 user_uid 的账号；user_uid 为空时不操作（避免误断全站）。
    """
    if not user_uid:
        return
    try:
        from db import get_accounts
        from services.idle_manager import idle_manager

        accounts = await get_accounts(user_uid)
        for account in accounts:
            if account.provider == "gmail":
                await idle_manager.remove(account.id)
    except Exception:
        # 保存设置不能因为后台连接清理失败而失败；连接会在后续重连时读取新配置。
        pass


def _test_proxy_to_google_sync(proxy_url: str) -> dict:
    """同步探测：经 HTTP 代理 CONNECT 到 Google 相关主机，验证代理可用。

    策略（与 Gmail 实际链路一致）：
    1. 优先 CONNECT imap.gmail.com:993（收件主路径）
    2. 失败再试 www.google.com:443（通用 Google 可达性兜底）

    在后台线程中执行，避免阻塞事件循环。
    """
    from providers.proxy import create_proxy_socket

    proxy_url = (proxy_url or "").strip()
    if not proxy_url:
        return {
            "success": False,
            "message": "请填写代理地址",
            "latency_ms": 0,
            "target": "",
        }

    parsed = urlparse(proxy_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {
            "success": False,
            "message": "代理地址格式无效，请使用 http://host:port 或 http://user:pass@host:port",
            "latency_ms": 0,
            "target": "",
        }

    # 探测目标：与 Gmail 使用场景对齐
    targets = [
        ("imap.gmail.com", 993),
        ("www.google.com", 443),
    ]
    last_error = ""
    started = time.perf_counter()

    for host, port in targets:
        sock = None
        try:
            # 单目标超时 12 秒，避免长时间卡住 UI
            sock = create_proxy_socket(proxy_url, host, port, timeout=12)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "success": True,
                "message": f"代理连通正常（经 {host}:{port}，{latency_ms}ms）",
                "latency_ms": latency_ms,
                "target": f"{host}:{port}",
            }
        except Exception as e:
            last_error = str(e) or e.__class__.__name__
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    latency_ms = int((time.perf_counter() - started) * 1000)
    # 面向用户的简短中文说明
    hint = last_error
    if "CONNECT" in last_error or "200" in last_error:
        hint = f"代理拒绝隧道（{last_error}）"
    elif "timed out" in last_error.lower() or "timeout" in last_error.lower():
        hint = "连接超时，请检查代理地址、端口与网络"
    elif "解析" in last_error or "gaierror" in last_error.lower() or "getaddrinfo" in last_error.lower():
        hint = "无法解析代理主机名"
    elif "refused" in last_error.lower() or "积极拒绝" in last_error:
        hint = "无法连接代理服务，请确认代理已启动"
    return {
        "success": False,
        "message": f"代理无法连通 Google：{hint}",
        "latency_ms": latency_ms,
        "target": "",
    }


# ==================== 设置接口 ====================


@router.get("/api/settings", response_model=SettingsResponse, summary="获取 Gmail 网络代理设置")
async def get_settings(request: Request):
    """获取当前用户的 Gmail 代理设置（按 user_uid 隔离）。"""
    uid = await get_uid(request)
    settings = await get_gmail_proxy_settings(uid)
    return {
        "gmail_proxy_enabled": bool(settings.get("gmail_proxy_enabled", False)),
        "gmail_proxy_url": settings.get("gmail_proxy_url", ""),
    }


@router.put("/api/settings", response_model=SettingsUpdateResponse, summary="更新 Gmail 网络代理设置")
async def update_settings(request: Request, body: SettingsUpdateRequest):
    """更新当前用户 Gmail 代理；不写进程全局 gmail_config，不保存 OAuth 密钥。"""
    uid = await get_uid(request)
    update_data = body.model_dump(exclude_none=True)
    await save_gmail_proxy_settings(uid, update_data)
    # 仅重置本用户 Gmail IDLE，按新代理重连
    await reset_gmail_idle_connections(uid)

    return {"success": True, "message": "设置已保存"}


@router.post(
    "/api/settings/proxy/test",
    response_model=ProxyTestResponse,
    summary="测试 Gmail HTTP 代理连通性",
)
async def test_gmail_proxy(body: ProxyTestRequest):
    """测试用户填写的 HTTP 代理是否能连通 Google（IMAP/HTTPS）。

    不要求先保存设置；使用请求体中的 proxy_url 即时探测。
    """
    result = await asyncio.to_thread(_test_proxy_to_google_sync, body.proxy_url)
    return result


# ==================== 聚合收件箱设置 ====================


@router.get("/api/settings/unified", summary="获取聚合收件箱设置")
async def get_unified_settings(request: Request):
    """获取聚合收件箱的设置：用户选择要聚合的邮箱账号列表

    unified_account_ids 按 user_uid 存储在 user_settings 表，避免多用户互相覆盖
    """
    from db import get_accounts, get_user_settings

    uid = await get_uid(request)
    accounts = await get_accounts(uid)

    # 从用户级配置表读取（按 user_uid 隔离）
    user_settings = await get_user_settings(uid, ["unified_account_ids"])
    unified_ids = user_settings.get("unified_account_ids", [])
    if not isinstance(unified_ids, list):
        unified_ids = []

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

    unified_account_ids 按 user_uid 存储在 user_settings 表，避免多用户互相覆盖
    """
    from db import set_user_settings

    uid = await get_uid(request)
    account_ids = body.account_ids

    # 写入用户级配置表
    await set_user_settings(uid, {"unified_account_ids": account_ids})

    return {"success": True}
