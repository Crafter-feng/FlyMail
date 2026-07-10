"""Outlook OAuth2 认证提供者

授权和 token 刷新统一通过 Cloudflare OAuth Broker 完成，
本地不再保存 Microsoft OAuth Client 密钥。
"""
import time

import httpx

from config import OAUTH_BROKER_URL
from ..base import AuthProvider, Credentials, OAuthTokenError, parse_retry_after
from utils.logger import get_logger

logger = get_logger("outlook.auth")


class OutlookAuthProvider(AuthProvider):
    """Microsoft/Outlook OAuth2 认证提供者"""

    def get_auth_url(self, redirect_uri: str = "", state: str = "") -> str:
        """Microsoft 授权入口已迁移到 Cloudflare Broker，本地不再生成直连授权 URL。"""
        raise ValueError("Microsoft OAuth 授权必须通过 Cloudflare Broker 发起。")

    async def handle_callback(self, code: str, redirect_uri: str = "", state: str = "") -> Credentials:
        """Microsoft 授权码换 token 已迁移到 Cloudflare Broker，本地不再直连 token endpoint。"""
        raise ValueError("Microsoft OAuth 回调必须通过 Cloudflare Broker 交换 broker_code。")

    async def refresh_token(self, credentials: Credentials) -> Credentials:
        """通过 Cloudflare Broker 刷新 Microsoft 访问令牌。

        Microsoft OAuth Client Secret 已统一放在 Cloudflare Worker 中，
        本地只提交用户 refresh_token，并兼容 Microsoft 返回新的 refresh_token。
        """
        if not credentials.refresh_token:
            raise ValueError("No refresh token available")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{OAUTH_BROKER_URL.rstrip('/')}/oauth/refresh",
                    json={
                        "provider": "outlook",
                        "refresh_token": credentials.refresh_token,
                    },
                )
        except Exception as e:
            logger.warning("通过 Broker 刷新 Outlook token 网络异常: %s", e)
            raise OAuthTokenError(
                f"Outlook Broker 刷新 token 网络异常: {e}",
                error_code="network_error",
                http_status=0,
                provider="outlook",
            )

        if response.status_code != 200:
            error_data = None
            try:
                error_data = response.json()
            except Exception as e:
                logger.debug("解析 Broker 错误响应 JSON 失败: %s", e)
            if error_data and error_data.get("error"):
                error_code = error_data["error"]
                retry_after = parse_retry_after(response.headers.get("retry-after"))
                logger.error("通过 Broker 刷新 Outlook token 失败: %s, retry_after=%s", error_code, retry_after)
                raise OAuthTokenError(
                    f"Outlook Broker OAuth 错误: {error_code}",
                    error_code=error_code,
                    http_status=response.status_code,
                    provider="outlook",
                    retry_after=retry_after,
                )
            logger.error("通过 Broker 刷新 Outlook token 失败: HTTP %d", response.status_code)
            response.raise_for_status()
        data = response.json()

        return Credentials(
            provider_type="outlook",
            access_token=data.get("access_token", credentials.access_token),
            refresh_token=data.get("refresh_token") or credentials.refresh_token,
            expires_at=int(time.time()) + data.get("expires_in", 3600),
            extra=credentials.extra,
        )

    async def revoke_token(self, credentials: Credentials) -> bool:
        """Microsoft 邮箱授权暂不在本地撤销，调用方可直接视为成功。"""
        return True
