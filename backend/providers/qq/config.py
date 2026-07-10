"""QQ 邮箱配置

QQ 邮箱使用授权码认证（非 OAuth2），IMAP/SMTP 连接参数固定。
腾讯企业邮箱与 QQ 邮箱使用相同的认证机制，仅服务器地址不同。
"""
# QQ 邮箱 IMAP/SMTP 配置
IMAP_HOST = "imap.qq.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465

# 腾讯企业邮箱 IMAP/SMTP 配置
EXMAIL_IMAP_HOST = "imap.exmail.qq.com"
EXMAIL_IMAP_PORT = 993
EXMAIL_SMTP_HOST = "smtp.exmail.qq.com"
EXMAIL_SMTP_PORT = 465
