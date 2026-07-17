import os
from typing import Any, Dict

# Gmail IMAP/SMTP 服务器配置。OAuth Client 密钥由 Cloudflare Worker 统一管理，本地不再保存。

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

# 进程级环境变量兜底（非用户设置）。多用户代理请走 Credentials.extra + proxy_url_from_extra。
# 保留变量名供测试/运维注入，业务路径不得再 sync 用户设置到此处。
GMAIL_PROXY_ENABLED = os.environ.get("GMAIL_PROXY_ENABLED", "").lower() in ("1", "true", "yes")
GMAIL_PROXY_URL = os.environ.get("GMAIL_PROXY_URL", "")


def proxy_url_from_extra(extra: Dict[str, Any] | None) -> str:
    """从用户级 Credentials.extra 读取代理 URL。

    启用且配置了 URL 时返回地址，否则空串（直连）。
    优先用户 extra，避免多用户共用进程全局代理。
    """
    if not extra:
        return ""
    if not bool(extra.get("gmail_proxy_enabled")):
        return ""
    return str(extra.get("gmail_proxy_url") or "").strip()
