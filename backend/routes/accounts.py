"""账号管理路由

处理邮箱账号的添加（QQ/iCloud/网易/OAuth）、删除、更新、测试连接、
重建同步等操作。同时包含 OAuth 授权流程所需的辅助函数。
"""
import asyncio
import json
import ssl
import time
import uuid
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Request, Body, Path as FastAPIPath

from errors import AppError

from db import (
    get_accounts,
    create_account,
    delete_account,
    update_account_info,
    delete_cached_messages_by_account,
    delete_folder_stats_by_account,
    get_db,
)
from deps import get_uid
from models import Account
from providers.base import Credentials
from providers.factory import ProviderFactory
from services.mail_cache import initial_sync
from services.sync import sync_service
from services.token import ensure_token as _ensure_gmail_token
from utils.logger import get_logger
from utils.tasks import create_background_task
from schemas import (
    AccountAddResponse,
    AccountListResponse,
    AccountTestResponse,
    AccountUpdateRequest,
    AuthCodeAccountRequest,
    AuthUrlRequest,
    AuthUrlResponse,
    CustomAccountRequest,
    DeleteResponse,
    MessageResponse,
)

logger = get_logger("routes.accounts")

router = APIRouter(prefix="/api/accounts", tags=["账号"])

# ==================== 常量定义 ====================

# 网关前缀（与 main.py 中的 StripPrefixMiddleware 对应）
from config import GATEWAY_PREFIX, OAUTH_BROKER_URL
from services.broker_security import generate_pkce_verifier, compute_pkce_challenge, store_pkce_verifier

# 授权码类邮箱的邮箱后缀验证规则
_AUTH_CODE_EMAIL_SUFFIXES = {
    "icloud": ("@icloud.com", "@me.com", "@mac.com"),
    "netease": ("@163.com", "@126.com", "@188.com", "@yeah.net"),
    "sina": ("@sina.com", "@sina.cn", "@2008.sina.com", "@vip.sina.com", "@vip.sina.cn"),
}

# 授权码类邮箱的后缀验证错误提示
_AUTH_CODE_SUFFIX_ERRORS = {
    "icloud": "请输入icloud.com、me.com或mac.com邮箱地址",
    "netease": "请输入163、126、188或yeah.net邮箱地址",
    "sina": "请输入sina.com、sina.cn、2008.sina.com、vip.sina.com或vip.sina.cn邮箱地址",
}

# ==================== 内部辅助函数 ====================
# 从 _helpers 复用共享辅助函数，避免与其他 routes 模块重复定义
from routes._helpers import _find_account_or_error, _safe_disconnect



async def _add_auth_code_account(request: Request, provider: str, body: AuthCodeAccountRequest = None):
    """授权码类邮箱的统一添加逻辑（QQ、网易、iCloud）"""
    uid = await get_uid(request)

    if body is None:
        raise AppError(400, "邮箱地址和授权码不能为空")
    email_addr = body.email.strip()
    auth_code = body.auth_code.strip()

    if not email_addr or not auth_code:
        raise AppError(400, "邮箱地址和授权码不能为空")

    # 邮箱后缀验证（QQ 无限制，iCloud 和网易有特定后缀要求）
    valid_suffixes = _AUTH_CODE_EMAIL_SUFFIXES.get(provider)
    if valid_suffixes and not email_addr.endswith(valid_suffixes):
        raise AppError(400, _AUTH_CODE_SUFFIX_ERRORS.get(provider, "邮箱地址格式不正确"))

    try:
        # 根据平台创建凭据
        if provider == "qq":
            from providers.qq.auth import QQAuthProvider
            credentials = QQAuthProvider.create_credentials(email_addr, auth_code)
            # 腾讯企业邮箱标记：存入 credentials.extra，供 receiver/sender/sync 选择服务器
            if body.is_exmail:
                credentials.extra["is_exmail"] = True
        elif provider == "icloud":
            from providers.icloud.auth import ICloudAuthProvider
            credentials = ICloudAuthProvider.create_credentials(email_addr, auth_code)
        elif provider == "netease":
            from providers.netease.auth import NeteaseAuthProvider
            credentials = NeteaseAuthProvider.create_credentials(email_addr, auth_code)
        elif provider == "sina":
            from providers.sina.auth import SinaAuthProvider
            credentials = SinaAuthProvider.create_credentials(email_addr, auth_code)
        else:
            raise AppError(400, f"不支持的平台: {provider}")

        receiver = ProviderFactory.get_receiver(provider)
        await receiver.connect(credentials)
        await _safe_disconnect(receiver)

        account = Account(
            id=str(uuid.uuid4()),
            user_uid=uid,
            email=email_addr,
            provider=provider,
            credentials_json=json.dumps({
                # 授权码存入 access_token 字段（复用 OAuth 字段结构），expires_at=0 和 refresh_token="" 为占位值
                "access_token": auth_code,
                "refresh_token": "",
                "expires_at": 0,
                "extra": credentials.extra,
            }),
            status="connected",
            created_at=time.time(),
            updated_at=time.time(),
        )

        await create_account(account)
        create_background_task(sync_service.add_account(account.id), name="add_account_imap")
        # 后台全量同步收件箱（首次添加账号时缓存为空，需要拉取邮件摘要）
        create_background_task(initial_sync(account.id), name="initial_sync")

        return {
            "success": True,
            "account": {
                "id": account.id,
                "email": account.email,
                "provider": account.provider,
                "status": account.status,
                "remark": "",
                "group_name": "",
                "hide_email": False,
                "created_at": account.created_at,
            }
        }
    except AppError:
        raise  # 保留原始的 AppError（如 400 验证错误），不要覆盖为 500
    except Exception as e:
        raise AppError(500, str(e))


def _build_oauth_frontend_url(request: Request) -> str:
    """根据当前网关请求构造 OAuth 完成后的前端回跳地址。"""
    scheme = request.headers.get("X-Forwarded-Proto") or request.url.scheme
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("host", "")
    return f"{scheme}://{host}{GATEWAY_PREFIX}/"


def _build_oauth_callback_url(request: Request) -> str:
    """根据当前网关请求构造 51010 OAuth 专用回调地址。

    Cloudflare Broker 授权完成后会把 broker_code 回跳到这里。
    不能使用 /app/flymail/api/auth/callback，因为该路径会先经过飞牛应用网关登录鉴权，
    第三方 OAuth 弹窗回跳时通常没有网关 token，会被网关拦截为 invalid token。
    """
    scheme = request.headers.get("X-Forwarded-Proto") or request.url.scheme
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("host", "")
    parsed = urlparse(f"//{host}")
    hostname = parsed.hostname or host.split(":", 1)[0]
    return f"{scheme}://{hostname}:51010/api/auth/callback"


def _build_broker_auth_url(provider: str, oauth_state: str, return_url: str, code_challenge: str) -> str:
    """生成 Cloudflare Broker 授权入口，Gmail 和 Outlook 共用。"""
    broker_base = OAUTH_BROKER_URL.rstrip("/")
    params = {
        "provider": provider,
        "state": oauth_state,
        "return_url": return_url,
        "code_challenge": code_challenge,
    }
    return f"{broker_base}/oauth/start?{urlencode(params)}"


# OAuth state 解析辅助函数：从 auth.py 导入（OAuth 回调和账号添加共用）
from routes.auth import (
    _build_oauth_result_html,
    _extract_oauth_frontend_url_from_state,
    _extract_oauth_provider_from_state,
    _extract_oauth_state_data,
    _extract_oauth_uid_from_state,
)


# ==================== 账号管理接口 ====================


@router.get("", response_model=AccountListResponse, summary="获取所有邮箱账号")
async def list_accounts(request: Request):
    """获取当前飞牛用户下所有已绑定的邮箱账号列表"""
    uid = await get_uid(request)
    accounts = await get_accounts(uid)
    safe_accounts = []
    for acc in accounts:
        safe_accounts.append({
            "id": acc.id,
            "email": acc.email,
            "provider": acc.provider,
            "status": acc.status,
            "remark": acc.remark,
            "group_name": acc.group_name,
            "hide_email": acc.hide_email,
            "sort_order": acc.sort_order,
            "created_at": acc.created_at,
            "reauth_needed": acc.id in sync_service.reauth_account_ids,
        })
    return {"accounts": safe_accounts}


@router.put("/sort-order", summary="更新邮箱账号排序")
async def update_sort_order(request: Request, body: list = Body(description="排序列表 [{id, sort_order}]")):
    """批量更新邮箱账号的显示排序"""
    uid = await get_uid(request)
    # 验证每个账号属于当前用户
    accounts = await get_accounts(uid)
    valid_ids = {acc.id for acc in accounts}
    for item in body:
        if item.get("id") not in valid_ids:
            raise AppError(400, f"账号不存在: {item.get('id')}")
    from db import update_account_sort_orders
    await update_account_sort_orders(body)
    return {"success": True}


@router.post("/auth-url", response_model=AuthUrlResponse, summary="获取 OAuth 授权URL")
async def get_auth_url(request: Request, body: AuthUrlRequest = Body(description="OAuth 授权参数")):
    """获取第三方邮箱的 OAuth2 授权跳转地址。

    Gmail / Outlook 统一通过 Cloudflare Broker 授权，本地只负责生成签名 state。
    """
    provider_type = body.provider
    # 从网关请求头获取当前用户 uid，编码到 OAuth state 中，回调时恢复
    uid = await get_uid(request)
    # 记录当前前端入口，OAuth 结果页通过 postMessage 通知这个飞牛应用窗口。
    # broker_code 的实际回调走 51010 专用端口，不经过飞牛应用网关鉴权。
    frontend_url = _build_oauth_frontend_url(request)
    broker_return_url = _build_oauth_callback_url(request)
    # state 加入 HMAC 签名和时间戳，防止篡改 uid 冒充其他用户
    from routes.auth import _sign_oauth_state
    state_payload = {
        "uid": uid,
        "provider": provider_type,
        "frontend_url": frontend_url,
        "_ts": int(time.time()),
    }
    state_payload["_sig"] = _sign_oauth_state(state_payload)
    oauth_state = json.dumps(state_payload, separators=(",", ":"))

    try:
        if provider_type in ("gmail", "outlook"):
            # Gmail / Outlook 统一走 Cloudflare Broker：
            # 本地只生成已签名用户上下文，第三方 client_secret 由 Broker 统一持有。
            # PKCE（RFC 7636）：code_verifier 存本地，code_challenge 发给 Worker，
            # 回调时用 code_verifier 兑换 token，防止 broker_code 被截获盗用。
            code_verifier = generate_pkce_verifier()
            code_challenge = compute_pkce_challenge(code_verifier)
            store_pkce_verifier(oauth_state, code_verifier)
            url = _build_broker_auth_url(provider_type, oauth_state, broker_return_url, code_challenge)
            return {"auth_url": url, "provider": provider_type}

        raise ValueError(f"{provider_type} 不支持 OAuth 授权入口")
    except ValueError as e:
        logger.error("生成授权URL失败: %s", e)
        raise AppError(400, str(e))


@router.post("/add-qq", response_model=AccountAddResponse, summary="添加QQ邮箱账号")
async def add_qq_account(request: Request, body: AuthCodeAccountRequest = Body(description="QQ邮箱授权码账号信息")):
    """使用授权码直接添加QQ邮箱账号"""
    return await _add_auth_code_account(request, "qq", body)


@router.post("/add-icloud", response_model=AccountAddResponse, summary="添加iCloud邮箱账号")
async def add_icloud_account(request: Request, body: AuthCodeAccountRequest = Body(description="iCloud应用专用密码账号信息")):
    """使用应用专用密码添加iCloud邮箱账号"""
    return await _add_auth_code_account(request, "icloud", body)


@router.post("/add-netease", response_model=AccountAddResponse, summary="添加网易邮箱账号")
async def add_netease_account(request: Request, body: AuthCodeAccountRequest = Body(description="网易邮箱授权码账号信息")):
    """使用授权码添加网易邮箱账号"""
    return await _add_auth_code_account(request, "netease", body)


@router.post("/add-sina", response_model=AccountAddResponse, summary="添加新浪邮箱账号")
async def add_sina_account(request: Request, body: AuthCodeAccountRequest = Body(description="新浪邮箱授权码账号信息")):
    """使用授权码添加新浪邮箱账号（sina.com/sina.cn/2008.sina.com/vip.sina.com/vip.sina.cn）"""
    return await _add_auth_code_account(request, "sina", body)


@router.post("/add-custom", response_model=AccountAddResponse, summary="添加自定义邮箱账号")
async def add_custom_account(request: Request, body: CustomAccountRequest = Body(description="自定义邮箱配置信息")):
    """添加自定义 IMAP/SMTP 邮箱账号

    用户填写 IMAP/SMTP 服务器地址、端口、加密方式、邮箱地址和授权码，
    兼容所有支持标准 IMAP/SMTP 协议的邮箱服务。
    """
    uid = await get_uid(request)
    email_addr = body.email.strip()
    auth_code = body.auth_code.strip()
    imap_host = body.imap_host.strip()
    smtp_host = body.smtp_host.strip()

    # 参数校验：邮箱地址、授权码、IMAP/SMTP 服务器地址均不能为空
    if not email_addr or not auth_code or not imap_host or not smtp_host:
        raise AppError(400, "邮箱地址、授权码、IMAP/SMTP 服务器地址不能为空")

    # IMAP 加密方式校验
    if body.imap_ssl not in ("ssl", "starttls", "none"):
        raise AppError(400, "IMAP 加密方式仅支持 ssl、starttls 或 none")

    # SMTP 加密方式校验
    if body.smtp_ssl not in ("ssl", "starttls"):
        raise AppError(400, "SMTP 加密方式仅支持 ssl 或 starttls")

    try:
        # 创建凭据：服务器配置存入 credentials.extra，供 receiver/sender/sync 读取
        from providers.custom.auth import CustomAuthProvider
        server_config = {
            "imap_host": imap_host,
            "imap_port": body.imap_port,
            "imap_ssl": body.imap_ssl,
            "smtp_host": smtp_host,
            "smtp_port": body.smtp_port,
            "smtp_ssl": body.smtp_ssl,
        }
        credentials = CustomAuthProvider.create_credentials(email_addr, auth_code, server_config)

        # 测试 IMAP 连接（验证服务器配置和授权码是否正确）
        receiver = ProviderFactory.get_receiver("custom")
        await receiver.connect(credentials)
        await _safe_disconnect(receiver)

        # 创建账号记录
        account = Account(
            id=str(uuid.uuid4()),
            user_uid=uid,
            email=email_addr,
            provider="custom",
            credentials_json=json.dumps({
                "access_token": auth_code,
                "refresh_token": "",
                "expires_at": 0,
                "extra": credentials.extra,
            }),
            status="connected",
            created_at=time.time(),
            updated_at=time.time(),
        )

        await create_account(account)
        create_background_task(sync_service.add_account(account.id), name="add_account_imap")
        # 后台全量同步收件箱（首次添加账号时缓存为空，需要拉取邮件摘要）
        create_background_task(initial_sync(account.id), name="initial_sync")

        return {
            "success": True,
            "account": {
                "id": account.id,
                "email": account.email,
                "provider": account.provider,
                "status": account.status,
                "remark": "",
                "group_name": "",
                "hide_email": False,
                "created_at": account.created_at,
            }
        }
    except AppError:
        raise
    except Exception as e:
        raise AppError(500, str(e))


@router.delete("/{account_id}", response_model=DeleteResponse, summary="删除邮箱账号")
async def remove_account(
    account_id: str = FastAPIPath(description="账号唯一ID"),
    request: Request = None,
):
    """删除邮箱账号，同时撤销第三方令牌并停止后台同步"""
    uid = await get_uid(request)

    accounts = await get_accounts(uid)
    target = None
    for acc in accounts:
        if acc.id == account_id:
            target = acc
            break

    if not target:
        # 幂等删除：账号不存在也算成功（避免前端重复请求时误报错误）
        return {"success": True, "message": "账号不存在或已删除"}

    try:
        creds_data = json.loads(target.credentials_json)
        credentials = Credentials(
            provider_type=target.provider,
            access_token=creds_data.get("access_token", ""),
            refresh_token=creds_data.get("refresh_token", ""),
            expires_at=creds_data.get("expires_at", 0),
            extra=creds_data.get("extra", {}),
        )
        auth = ProviderFactory.get_auth(target.provider)
        await auth.revoke_token(credentials)
    except Exception as e:
        logger.debug("撤销 OAuth token 失败（不影响删除账号）: %s", e)

    await sync_service.remove_account(account_id)
    # 删除账号的邮件缓存和关联数据
    try:
        await delete_cached_messages_by_account(account_id)
        await delete_folder_stats_by_account(account_id)
        # 单例数据库连接不能在业务代码中 close，只执行删除和提交即可。
        db = await get_db()
        await db.execute("DELETE FROM notifications WHERE account_id = ?", (account_id,))
        await db.commit()
    except Exception as e:
        logger.debug("清理账号关联数据失败: %s", e)
    # 清理同步锁，防止内存泄漏
    from services.mail_cache import remove_sync_lock
    remove_sync_lock(account_id)
    # 清理 token 锁，防止内存泄漏
    from services.token import remove_token_lock
    remove_token_lock(account_id)
    deleted = await delete_account(account_id, uid)
    if deleted:
        return {"success": True}
    raise AppError(500, "Failed to delete account")


@router.post("/{account_id}/rebuild-sync", response_model=MessageResponse, summary="重建同步：清空缓存并重新拉取")
async def rebuild_sync(
    account_id: str = FastAPIPath(description="账号唯一ID"),
    request: Request = None,
):
    """清空当前账号的所有邮件缓存和文件夹统计，然后触发全量重新同步

    适用场景：缓存数据不一致、邮件列表显示异常时，手动触发重建。
    """
    uid = await get_uid(request)
    accounts = await get_accounts(uid)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        raise AppError(404, "Account not found")

    try:
        msg_count = await delete_cached_messages_by_account(account_id)
        await delete_folder_stats_by_account(account_id)
        logger.info("重建同步: 已清空账号 %s 的缓存（%d 条邮件）", account.email, msg_count)

        # 2. 后台触发全量重新同步，完成后通过 WebSocket 通知前端刷新
        async def _rebuild_and_notify():
            try:
                await initial_sync(account_id, force_full=True)
                # 同步完成，通知前端刷新列表和计数
                msg = json.dumps({
                    "type": "rebuild_done",
                    "account_id": account_id,
                    "message": f"重建同步完成，共同步邮件",
                })
                await sync_service._broadcast(msg, uid)
                logger.info("重建同步完成: 账号 %s，已通知前端", account.email)
            except Exception as e:
                logger.error("重建同步后台任务失败: %s", e)
                msg = json.dumps({
                    "type": "rebuild_done",
                    "account_id": account_id,
                    "error": str(e),
                })
                await sync_service._broadcast(msg, uid)

        create_background_task(_rebuild_and_notify(), name="rebuild_and_notify")

        return {"success": True, "message": f"已清空 {msg_count} 条缓存，正在后台重新同步"}
    except Exception as e:
        logger.error("重建同步失败: %s", e)
        raise AppError(500, str(e))


@router.post("/{account_id}/test", response_model=AccountTestResponse, summary="测试账号连接")
async def test_account(
    account_id: str = FastAPIPath(description="账号唯一ID"),
    request: Request = None,
):
    """测试邮箱账号的 IMAP 连接是否正常，同时刷新 OAuth 令牌"""
    uid = await get_uid(request)
    accounts = await get_accounts(uid)
    target = None
    for acc in accounts:
        if acc.id == account_id:
            target = acc
            break

    if not target:
        raise AppError(404, "Account not found")

    try:
        credentials = await _ensure_gmail_token(target)

        receiver = ProviderFactory.get_receiver(target.provider)
        try:
            await receiver.connect(credentials)
        except (ssl.SSLError, ConnectionError) as e:
            # SSL 瞬时错误（如 EOF），等待后重试一次，避免误报连接失败
            if "eof" in str(e).lower():
                await asyncio.sleep(3)
                await receiver.connect(credentials)
            else:
                raise
        try:
            if target.provider == "outlook":
                folders = await receiver.fetch_folders()
        finally:
            await _safe_disconnect(receiver)

        return {"success": True, "status": "connected"}
    except Exception as e:
        # token 永久失效时通知前端显示重新授权按钮
        from services.token import TokenRefreshError
        from providers.base import OAuthTokenError
        is_permanent = (isinstance(e, TokenRefreshError) and e.is_permanent) or (isinstance(e, OAuthTokenError) and e.is_permanent)
        if is_permanent:
            logger.error("测试连接失败，token 失效需重新授权: %s", target.email)
            sync_service.reauth_account_ids.add(target.id)
            try:
                await sync_service.notify_connection_status(
                    target.id, "reauth_needed", uid, error=str(e),
                )
            except Exception as notify_err:
                logger.debug("通知 reauth_needed 失败: %s", notify_err)
        else:
            logger.error("测试连接失败: %s, %s", target.email, e)
        return {"success": False, "status": "error", "error": str(e)}


# 更新账号信息返回 success + message，复用 MessageResponse（含 success 和 message 字段）
@router.put("/{account_id}", response_model=MessageResponse, summary="更新账号信息")
async def update_account(
    account_id: str = FastAPIPath(description="账号唯一ID"),
    request: Request = None,
    body: AccountUpdateRequest = Body(description="要更新的账号字段"),
):
    """更新账号的备注名、分组和邮箱隐藏设置"""
    uid = await get_uid(request)
    updated = await update_account_info(account_id, uid, body.remark, body.group_name, body.hide_email)
    if updated:
        return {"success": True, "message": "账号信息已更新"}
    raise AppError(404, "Account not found")
