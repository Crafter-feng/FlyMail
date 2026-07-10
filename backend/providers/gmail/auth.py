"""Gmail OAuth2 认证提供者

授权和 token 刷新统一通过 Cloudflare OAuth Broker 完成，
本地不再保存 Google OAuth Client 密钥。
"""
import time
import httpx
from config import OAUTH_BROKER_URL
from ..base import AuthProvider, Credentials, OAuthTokenError, parse_retry_after
from . import config as gmail_config
from utils.logger import get_logger

# 模块级日志
logger = get_logger("gmail.auth")


class GmailAuthProvider(AuthProvider):
    """Gmail OAuth2 认证提供者"""

    REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

    def get_auth_url(self, redirect_uri: str = "", state: str = "") -> str:
        """Gmail 授权入口已迁移到 Cloudflare Broker，本地不再生成直连授权 URL。"""
        raise ValueError("Gmail OAuth 授权必须通过 Cloudflare Broker 发起。")

    async def handle_callback(self, code: str, redirect_uri: str = "", state: str = "") -> Credentials:
        """Gmail 授权码换 token 已迁移到 Cloudflare Broker，本地不再直连 Google token endpoint。"""
        raise ValueError("Gmail OAuth 回调必须通过 Cloudflare Broker 交换 broker_code。")

    def _get_http_proxy(self):
        """获取 httpx 代理参数

        启用代理且配置了代理地址时返回代理 URL，否则返回 None（直连）。
        用于 OAuth2 的 token 交换、userinfo 获取、token 刷新。
        """
        if gmail_config.GMAIL_PROXY_ENABLED and gmail_config.GMAIL_PROXY_URL:
            return gmail_config.GMAIL_PROXY_URL
        return None

    async def refresh_token(self, credentials: Credentials) -> Credentials:
        """通过 Cloudflare Broker 刷新 Gmail 访问令牌。

        Gmail 的 OAuth Client Secret 已统一放在 Cloudflare Worker 中，
        本地只持有用户 refresh_token，避免在用户 NAS 上继续保存平台密钥。
        """
        if not credentials.refresh_token:
            raise ValueError("No refresh token available")

        logger.debug("通过 OAuth Broker 刷新 Gmail access_token")

        try:
            async with httpx.AsyncClient(timeout=30.0, proxy=self._get_http_proxy()) as client:
                response = await client.post(
                    f"{OAUTH_BROKER_URL.rstrip('/')}/oauth/refresh",
                    json={
                        "provider": "gmail",
                        "refresh_token": credentials.refresh_token,
                    },
                )
        except Exception as e:
            # 网络异常（超时、连接失败等）视为瞬态错误，上层会重试
            logger.warning("通过 Broker 刷新 Gmail token 网络异常: %s", e)
            raise OAuthTokenError(
                f"Gmail Broker 刷新 token 网络异常: {e}",
                error_code="network_error",
                http_status=0,
                provider="gmail",
            )

        if response.status_code != 200:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_code = error_data.get("error", "unknown")
            retry_after = parse_retry_after(response.headers.get("retry-after"))
            logger.error("通过 Broker 刷新 Gmail token 失败: %s, retry_after=%s", error_code, retry_after)
            raise OAuthTokenError(
                f"Gmail Broker OAuth 错误: {error_code}",
                error_code=error_code,
                http_status=response.status_code,
                provider="gmail",
                retry_after=retry_after,
            )
        data = response.json()

        return Credentials(
            provider_type="gmail",
            access_token=data.get("access_token", credentials.access_token),
            refresh_token=data.get("refresh_token") or credentials.refresh_token,
            expires_at=int(time.time()) + data.get("expires_in", 3600),
            extra=credentials.extra,
        )

    async def revoke_token(self, credentials: Credentials) -> bool:
        """撤销访问令牌"""
        if not credentials.access_token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.REVOKE_ENDPOINT,
                    params={"token": credentials.access_token},
                )
                return response.status_code == 200
        except Exception:
            return False
