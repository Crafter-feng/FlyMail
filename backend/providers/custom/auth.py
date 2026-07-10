from typing import Dict, Any
from ..base import AuthProvider, Credentials


class CustomAuthProvider(AuthProvider):
    """自定义邮箱认证提供者（使用授权码/密码，不需要 OAuth）

    服务器配置（imap_host/imap_port/smtp_host/smtp_port/smtp_ssl）存入 credentials.extra，
    供 CustomReceiver/CustomSender/sync 读取。
    """

    def get_auth_url(self, redirect_uri: str = "", state: str = "") -> str:
        """自定义邮箱不需要 OAuth 授权 URL"""
        return ""

    async def handle_callback(self, code: str, redirect_uri: str = "") -> Credentials:
        """自定义邮箱不需要 OAuth 回调"""
        return Credentials(provider_type="custom")

    async def refresh_token(self, credentials: Credentials) -> Credentials:
        """自定义邮箱不需要刷新令牌"""
        return credentials

    async def revoke_token(self, credentials: Credentials) -> bool:
        """自定义邮箱不需要撤销令牌"""
        return True

    @staticmethod
    def create_credentials(email: str, auth_code: str, server_config: Dict[str, Any]) -> Credentials:
        """创建自定义邮箱凭据

        Args:
            email: 邮箱地址
            auth_code: 授权码或登录密码
            server_config: 服务器配置，包含 imap_host/imap_port/smtp_host/smtp_port/smtp_ssl
        """
        return Credentials(
            provider_type="custom",
            access_token=auth_code,  # 授权码或密码
            refresh_token="",
            expires_at=0,  # 授权码不过期
            extra={"email": email, **server_config},
        )
