"""OAuth 认证路由

处理 OAuth2 回调流程，包括：
- 解析 OAuth state 参数（provider、uid、frontend_url）
- 用授权码换取 token 并创建邮箱账号
- 生成 OAuth 结果页（postMessage 通知原窗口）
- 51010 端口专用的 oauth_callback_app（不走 fnOS 网关）
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import uuid

import httpx
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse

from errors import AppError
from fastapi.middleware.cors import CORSMiddleware

from db import create_account, get_accounts, update_account_credentials
from models import Account
from providers.base import Credentials
from services.mail_cache import initial_sync
from services.sync import sync_service
from services.broker_security import retrieve_pkce_verifier
from utils.logger import get_logger
from utils.tasks import create_background_task
from version import VERSION

logger = get_logger("routes.auth")

# 飞牛网关前缀，用于拼接前端回跳地址
from config import GATEWAY_PREFIX, OAUTH_BROKER_URL


# ==================== OAuth state 签名与验证 ====================

# state 有效期 10 分钟，防止重放攻击
_OAUTH_STATE_MAX_AGE = 600


def _get_oauth_secret() -> bytes:
    """获取 OAuth state 签名密钥。

    不再用 data_dir 拼接固定字符串（可被本地复现），
    改为首次启动时生成 32 字节随机密钥，持久化到 data_dir 下的 .oauth_secret 文件。
    - 飞牛OS：文件权限 0600，仅 owner 可读
    - 不同实例密钥不同，且不可预测
    - 密钥文件丢失会导致旧 state 失效（用户需重新授权），但不会泄露密钥
    """
    global _OAUTH_SECRET_CACHE
    data_dir = os.environ.get("FLYMAIL_DATA_DIR", "/tmp/flymail")
    secret_file = os.path.join(data_dir, ".oauth_secret")

    # 已缓存则直接返回（避免每次签名都读文件）
    if _OAUTH_SECRET_CACHE is not None:
        return _OAUTH_SECRET_CACHE

    # 尝试读取已有密钥
    try:
        with open(secret_file, "rb") as f:
            secret = f.read().strip()
        if len(secret) >= 32:
            _OAUTH_SECRET_CACHE = secret
            return secret
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("读取 OAuth 密钥文件失败，将重新生成: %s", e)

    # 生成新密钥并持久化
    secret = os.urandom(32)
    try:
        os.makedirs(data_dir, exist_ok=True)
        # 写入临时文件再重命名，避免写入中途崩溃导致密钥损坏
        tmp_file = secret_file + ".tmp"
        with open(tmp_file, "wb") as f:
            f.write(secret)
        os.replace(tmp_file, secret_file)
        # 设置文件权限 0600（仅 owner 可读写）
        try:
            os.chmod(secret_file, 0o600)
        except Exception:
            # Windows 不支持 chmod，忽略错误
            pass
        logger.info("已生成新的 OAuth state 签名密钥: %s", secret_file)
    except Exception as e:
        logger.error("持久化 OAuth 密钥失败，将使用内存中的临时密钥: %s", e)

    _OAUTH_SECRET_CACHE = secret
    return secret


# OAuth 密钥内存缓存（避免每次签名都读文件）
_OAUTH_SECRET_CACHE: bytes | None = None


def _sign_oauth_state(state_data: dict) -> str:
    """对 state 数据生成 HMAC-SHA256 签名"""
    payload = json.dumps(state_data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(_get_oauth_secret(), payload, hashlib.sha256).hexdigest()


def _verify_oauth_signature(state_data: dict) -> bool:
    """验证 state 数据的 HMAC 签名和时间戳

    返回 True 表示验证通过，False 表示签名无效或已过期。
    """
    sig = state_data.pop("_sig", "")
    # 用 get 而非 pop 获取 _ts，保留 _ts 在 state_data 中参与签名计算
    # （若 pop 掉 _ts，验签时与签发时的输入不一致，签名永远不匹配）
    ts = state_data.get("_ts", 0)
    if not sig or not ts:
        return False
    # 验证时间戳：不超过 10 分钟
    if time.time() - ts > _OAUTH_STATE_MAX_AGE:
        return False
    # 重新计算签名并比较（使用 compare_digest 防止时序攻击）
    expected_sig = _sign_oauth_state(state_data)
    return hmac.compare_digest(sig, expected_sig)


# ==================== OAuth state 解析辅助函数 ====================


def _extract_oauth_state_data(state: str) -> dict:
    """解析 OAuth state，将 user_state 字段展开到顶层，失败时返回空字典。

    支持两种格式：
    - Gmail/本地 OAuth 原格式：Provider 外层 base64 JSON + user_state 签名 JSON
    - Outlook Broker 试点格式：直接回传本地签名 JSON state
    两种格式都必须通过 HMAC 签名验证。
    """
    if not state:
        return {}

    # Outlook Broker 会原样回传本地签名 JSON state，先尝试按 JSON 解析并验签。
    try:
        direct_state = json.loads(state)
        if isinstance(direct_state, dict) and direct_state.get("_sig"):
            if not _verify_oauth_signature(direct_state):
                logger.warning("OAuth 直传 state 签名验证失败，可能被篡改")
                return {}
            return direct_state
    except Exception:
        pass

    try:
        padded_state = state + "=" * (-len(state) % 4)
        decoded = base64.urlsafe_b64decode(padded_state).decode("utf-8")
        state_data = json.loads(decoded)
        if isinstance(state_data, dict):
            # 解析 user_state 字段并合并到顶层
            raw_user_state = state_data.pop("user_state", "")
            if raw_user_state:
                # 强制要求 user_state 必须是带签名的 JSON dict
                # 不再兼容"纯 uid 字符串"格式（该格式无签名，可被攻击者伪造）
                try:
                    user_context = json.loads(raw_user_state)
                except Exception:
                    logger.warning("OAuth state 的 user_state 不是合法 JSON，已拒绝")
                    return {}
                if not isinstance(user_context, dict):
                    logger.warning("OAuth state 的 user_state 不是 JSON 对象，已拒绝")
                    return {}
                # 验证 user_state 中的 HMAC 签名
                if not _verify_oauth_signature(user_context):
                    logger.warning("OAuth state 签名验证失败，可能被篡改")
                    return {}
                state_data.update(user_context)
            return state_data
    except Exception as e:
        logger.debug("解析 OAuth state 失败: %s", e)

    return {}


def _extract_oauth_provider_from_state(state: str) -> str:
    """从 OAuth state 中提取邮箱平台，解析失败时默认兼容 Gmail。"""
    state_data = _extract_oauth_state_data(state)
    provider = state_data.get("provider")
    if provider:
        return provider

    return "gmail"


def _extract_oauth_uid_from_state(state: str) -> str:
    """从 OAuth state 中提取用户 uid，失败时回退到 default。"""
    state_data = _extract_oauth_state_data(state)
    uid = state_data.get("uid", "")
    return uid or "default"


def _extract_oauth_frontend_url_from_state(state: str) -> str:
    """从 OAuth state 中提取授权完成后的前端回跳地址。"""
    state_data = _extract_oauth_state_data(state)
    return state_data.get("frontend_url") or f"{GATEWAY_PREFIX}/"


def _get_url_origin(url: str) -> str:
    """从 URL 中提取 origin（scheme://host[:port]），失败时返回空字符串。"""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return ""


def _build_oauth_result_html(params: dict) -> HTMLResponse:
    """生成 OAuth 结果页。

    OAuth 回调在 TCP 51010 端口处理（不走飞牛网关），不能重定向回前端页面
    （飞牛网关需要登录认证，且应用在 iframe 中，重定向会丢失登录态）。

    解决方案：展示轻量结果页，页面加载后通过 window.opener.postMessage()
    通知原窗口（飞牛应用）刷新账号列表，然后自动关闭弹出窗口。
    原窗口收到 postMessage 后设置 flymail_oauth_just_added 标记，
    避免账号页立即做连接测试导致误报 invalid token。

    postMessage 的 targetOrigin 不再使用 '*'，改为从 state 中
    提取 frontend_url 的 origin（已签名验证），仅允许飞牛前端源接收消息。
    JS 字符串拼接改用 json.dumps 生成 JS 安全字面量，
    避免 html.escape 在 JS 上下文中无效转义的问题。
    """
    import html as html_module
    import json as json_module

    success = params.get("oauth_success") == "1"
    provider = html_module.escape(params.get("provider", "mail"))
    email = html_module.escape(params.get("email", ""))
    error = html_module.escape(params.get("oauth_error", ""))
    title = "授权成功" if success else "授权失败"
    message = f"{provider} 账号已添加成功：{email}" if success else f"{provider} 授权失败：{error}"
    color = "#16a34a" if success else "#dc2626"
    icon = "✓" if success else "!"

    # 从 state 中提取 frontend_url 的 origin 作为 targetOrigin
    # 仅允许飞牛前端源接收 postMessage，避免任意源截获含 email 的消息
    state = params.get("state", "")
    frontend_url = _extract_oauth_frontend_url_from_state(state) if state else ""
    target_origin = _get_url_origin(frontend_url)
    # 若无法确定 origin（如 state 缺失），fallback 到空字符串（postMessage 会拒绝所有源）
    # 这比 '*' 更安全：宁可通知失败，也不泄露 email
    target_origin_js = json_module.dumps(target_origin)

    # 用 json.dumps 生成可安全嵌入 JS 的字符串字面量
    provider_js = json_module.dumps(params.get("provider", "mail"))
    email_js = json_module.dumps(params.get("email", ""))
    error_js = json_module.dumps(params.get("oauth_error", ""))

    # postMessage 通知原窗口的 JavaScript 代码
    # 成功时通知原窗口刷新账号列表，失败时通知原窗口显示错误
    notify_js = ""
    if success:
        notify_js = f"""
      // 通知打开此窗口的原窗口（飞牛应用），OAuth 授权成功
      // targetOrigin 使用飞牛前端 origin，不再用 '*'
      if (window.opener) {{
        window.opener.postMessage({{
          type: 'flymail_oauth_success',
          provider: {provider_js},
          email: {email_js}
        }}, {target_origin_js});
      }}
      // 1秒后自动关闭弹出窗口
      setTimeout(function() {{ window.close(); }}, 1000);
"""
    elif error:
        notify_js = f"""
      // 通知原窗口 OAuth 授权失败
      // targetOrigin 使用飞牛前端 origin，不再用 '*'
      if (window.opener) {{
        window.opener.postMessage({{
          type: 'flymail_oauth_error',
          provider: {provider_js},
          error: {error_js}
        }}, {target_origin_js});
      }}
"""

    return HTMLResponse(
        content=f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f6f7fb; color:#111827; }}
    .card {{ width:min(420px, calc(100vw - 32px)); background:#fff; border-radius:18px; box-shadow:0 20px 60px rgba(15,23,42,.12); padding:28px; text-align:center; }}
    .status {{ width:56px; height:56px; margin:0 auto 16px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:{color}; color:#fff; font-size:30px; }}
    h1 {{ margin:0 0 10px; font-size:22px; }}
    p {{ margin:0 0 18px; line-height:1.6; color:#4b5563; word-break:break-all; }}
    .hint {{ font-size:13px; color:#6b7280; }}
    button {{ border:0; border-radius:10px; padding:11px 16px; background:#2563eb; color:#fff; cursor:pointer; font-size:14px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="status">{icon}</div>
    <h1>{title}</h1>
    <p>{message}</p>
    <button onclick="tryClose()">关闭此页</button>
    <p class="hint">请回到飞牛 NAS 中已登录的飞邮应用查看账号状态。</p>
  </div>
  <script>
function tryClose() {{
  window.close();
  // 大部分浏览器不允许关闭非脚本打开的页面，回退为提示用户手动关闭
  setTimeout(function() {{
    document.querySelector('button').textContent = '请手动关闭此标签页';
    document.querySelector('button').onclick = null;
    document.querySelector('button').style.opacity = '0.6';
  }}, 300);
}}
{notify_js}
  </script>
</body>
</html>
""",
        status_code=200,
    )


# ==================== OAuth 回调端点 ====================


async def _exchange_broker_code(provider: str, broker_code: str, state: str) -> Credentials:
    """用 Cloudflare Broker 的一次性 broker_code 换取 OAuth token。

    Gmail 和 Outlook 都通过同一个 Broker 入口授权。
    broker_code 和 state 必须同时提交，Cloudflare 会校验二者绑定关系。
    PKCE（RFC 7636）：兑换时提交 code_verifier，Worker 验证其哈希与存储的
    code_challenge 匹配，防止 broker_code 被截获盗用。
    """
    if not broker_code:
        raise ValueError(f"{provider} Broker 回调缺少 broker_code")
    # 从内存缓存取回 code_verifier（授权时存入，一次性使用）
    code_verifier = retrieve_pkce_verifier(state)
    if not code_verifier:
        raise ValueError(f"{provider} Broker 回调缺少 code_verifier，可能已过期")
    broker_base = OAUTH_BROKER_URL.rstrip("/")
    payload = {
        "provider": provider,
        "broker_code": broker_code,
        "state": state,
        "code_verifier": code_verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{broker_base}/oauth/exchange", json=payload)
    except httpx.TimeoutException:
        raise ValueError(f"连接 {provider} Broker 超时，请稍后重试")
    except httpx.ConnectError:
        raise ValueError(f"无法连接 {provider} Broker，请检查网络连接")

    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = {}
        error_msg = error_data.get("error") or response.text[:120]
        raise ValueError(f"{provider} Broker 换取 token 失败: {error_msg}")

    data = response.json()
    email = data.get("email", "")
    if not email:
        raise ValueError(f"{provider} Broker 未返回邮箱地址")
    return Credentials(
        provider_type=provider,
        access_token=data.get("access_token", ""),
        refresh_token=data.get("refresh_token", ""),
        expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
        extra={"email": email},
    )


async def oauth_callback(
    request: Request,
    code: str = Query(default="", description="第三方返回的授权码"),
    state: str = Query(default="", description="防CSRF的state参数"),
    error: str = Query(default="", description="第三方返回的错误（用户拒绝授权等）"),
    broker_code: str = Query(default="", description="Cloudflare Broker 返回的一次性授权码"),
):
    """处理通用 OAuth2 回调（通过TCP端口51010直接访问，不走fnOS网关）。

    流程：
    1. Cloudflare Broker 完成第三方授权后，把 broker_code 回跳到本地 51010 端口。
    2. 本地用 broker_code 向 Broker 换取 token。
    3. 本地创建或更新邮箱账号。
    4. 展示轻量结果页并通过 postMessage 通知原窗口。
    """
    provider = _extract_oauth_provider_from_state(state)

    if error:
        logger.warning("OAuth 返回错误: provider=%s, error=%s", provider, error)
        params = {"oauth_error": error, "provider": provider, "state": state}
        return _build_oauth_result_html(params)

    if not code and not broker_code:
        logger.error("OAuth 回调缺少 authorization code/broker_code: provider=%s", provider)
        return HTMLResponse(content="<html><body><h3>授权失败：缺少授权码</h3></body></html>", status_code=400)

    try:
        # 从 OAuth state 中恢复用户 uid，确保账号归属正确的 NAS 用户
        uid = _extract_oauth_uid_from_state(state)
        if provider not in ("gmail", "outlook"):
            raise ValueError(f"{provider} 不支持 OAuth 回调")
        if not broker_code:
            raise ValueError(f"{provider} 授权必须通过 Cloudflare Broker 回调")
        credentials = await _exchange_broker_code(provider, broker_code, state)

        email = credentials.extra.get("email", "")

        # 检查是否为重新授权（已有同邮箱账号），如果是则更新凭据而非创建新账号
        existing_accounts = await get_accounts(uid)
        existing = next((a for a in existing_accounts if a.email == email and a.provider == provider), None)

        if existing:
            # 重新授权：更新已有账号的凭据
            new_creds = json.dumps({
                "access_token": credentials.access_token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expires_at,
                "extra": credentials.extra,
            })
            await update_account_credentials(existing.id, new_creds)
            logger.info("重新授权成功，已更新凭据: email=%s, provider=%s", email, provider)
            # 先停止旧的 IMAP 监听任务（用旧 token 的任务会持续认证失败），
            # 再启动新的监听任务
            await sync_service.remove_account(existing.id)
            # 重启该账号的 IMAP 监听
            create_background_task(sync_service.add_account(existing.id), name="reauth_add_account")
            # 同步 token 失效期间错过的邮件
            create_background_task(initial_sync(existing.id), name="reauth_initial_sync")

            params = {"oauth_success": "1", "provider": provider, "email": email, "state": state}
            return _build_oauth_result_html(params)

        account = Account(
            id=str(uuid.uuid4()),
            user_uid=uid,
            email=email,
            provider=provider,
            credentials_json=json.dumps({
                "access_token": credentials.access_token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expires_at,
                "extra": credentials.extra,
            }),
            status="connected",
            created_at=time.time(),
            updated_at=time.time(),
        )

        await create_account(account)
        # 启动后台 IMAP 监听 + 全量同步邮件摘要到缓存
        # Microsoft IMAP 在 OAuth 刚完成后可能短暂不可用，延迟5秒再连接
        async def _start_outlook_with_delay():
            await asyncio.sleep(5)
            create_background_task(sync_service.add_account(account.id), name="outlook_delayed_add_account")
            create_background_task(initial_sync(account.id), name="outlook_delayed_initial_sync")

        if provider == "outlook":
            create_background_task(_start_outlook_with_delay(), name="outlook_delayed_start")
        else:
            create_background_task(sync_service.add_account(account.id), name="oauth_add_account")
            create_background_task(initial_sync(account.id), name="oauth_initial_sync")

        logger.info("OAuth 授权成功，重定向回前端页面: provider=%s, email=%s", provider, credentials.extra.get("email", ""))
        params = {"oauth_success": "1", "provider": provider, "email": credentials.extra.get("email", ""), "state": state}
        return _build_oauth_result_html(params)

    except Exception as e:
        error_msg = str(e)
        logger.error("OAuth 授权失败: provider=%s, error=%s", provider, error_msg)
        params = {"oauth_error": error_msg, "provider": provider, "state": state}
        return _build_oauth_result_html(params)


# ==================== OAuth 回调专用独立应用（51010 端口） ====================

# OAuth 回调专用应用：51010 端口只暴露授权回调，不能访问主应用页面、文档和其他 API。
oauth_callback_app = FastAPI(
    title="FlyMail OAuth Callback",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
oauth_callback_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# 注册 AppError 异常处理器（与主应用一致）
from errors import app_error_handler as _app_error_handler
oauth_callback_app.add_exception_handler(AppError, _app_error_handler)

oauth_callback_app.add_api_route("/api/auth/callback", oauth_callback, methods=["GET"])


@oauth_callback_app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def oauth_callback_app_not_found(full_path: str):
    """51010 端口只服务 OAuth 回调，其他路径全部拒绝。"""
    raise AppError(404, "not_found")
