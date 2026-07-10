import os

# Gmail IMAP/SMTP 服务器配置。OAuth Client 密钥由 Cloudflare Worker 统一管理，本地不再保存。

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

# HTTP 代理配置（用于网络受限环境访问 Google 服务）
# 启用后对 Gmail 的 OAuth2 授权、IMAP 收件、SMTP 发件全链路生效
GMAIL_PROXY_ENABLED = os.environ.get("GMAIL_PROXY_ENABLED", "").lower() in ("1", "true", "yes")
GMAIL_PROXY_URL = os.environ.get("GMAIL_PROXY_URL", "")
