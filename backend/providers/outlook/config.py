# Outlook IMAP/SMTP 服务器配置。OAuth Client 密钥由 Cloudflare Worker 统一管理，本地不再保存。
OUTLOOK_IMAP_HOST = "outlook.office365.com"
OUTLOOK_IMAP_PORT = 993
# SMTP 服务器：个人账户（outlook.com/hotmail.com）用 smtp-mail.outlook.com，
# 企业账户（Microsoft 365）用 smtp.office365.com。
# 实际使用中 smtp-mail.outlook.com 兼容性更好，两个地址均可用于个人和企业账户。
OUTLOOK_SMTP_HOST = "smtp-mail.outlook.com"
OUTLOOK_SMTP_PORT = 587
SUPPORTED_DOMAINS = ("@outlook.com", "@hotmail.com", "@live.com", "@msn.com")
