from typing import Dict, Any
from ..base import AuthProvider, Credentials


class SinaAuthProvider(AuthProvider):
    """新浪邮箱认证提供者（使用客户端授权码认证，不需要 OAuth）

    新浪邮箱强制要求第三方客户端使用 16 位客户端授权码（非登录密码），
    授权码在邮箱网页「设置 → 客户端 POP/IMAP/SMTP」中通过手机短信验证生成。

    支持的邮箱后缀：
    - @sina.com / @2008.sina.com（免费邮箱，使用 imap.sina.com）
    - @sina.cn（免费邮箱，使用 imap.sina.cn）
    - @vip.sina.com（VIP 邮箱，使用 imap.vip.sina.com）
    - @vip.sina.cn（VIP 邮箱，使用 imap.vip.sina.cn）
    """

    def get_auth_url(self, redirect_uri: str = "", state: str = "") -> str:
        """新浪邮箱不需要 OAuth 授权 URL，返回空字符串"""
        return ""

    async def handle_callback(self, code: str, redirect_uri: str = "") -> Credentials:
        """新浪邮箱不需要 OAuth 回调，返回空凭据"""
        return Credentials(provider_type="sina")

    async def refresh_token(self, credentials: Credentials) -> Credentials:
        """新浪邮箱使用授权码，不需要刷新令牌"""
        return credentials

    async def revoke_token(self, credentials: Credentials) -> bool:
        """新浪邮箱不需要撤销令牌（授权码在网页端管理）"""
        return True

    @staticmethod
    def create_credentials(email: str, auth_code: str) -> Credentials:
        """创建新浪邮箱凭据（使用客户端授权码）

        Args:
            email: 新浪邮箱地址（如 example@sina.com / @sina.cn / @2008.sina.com / @vip.sina.com / @vip.sina.cn）
            auth_code: 16 位客户端授权码（非登录密码）
        """
        return Credentials(
            provider_type="sina",
            access_token=auth_code,  # 新浪邮箱使用授权码作为访问令牌
            refresh_token="",
            expires_at=0,  # 授权码不过期（由用户在网页端管理）
            extra={"email": email}
        )
