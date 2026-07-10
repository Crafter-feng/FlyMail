"""自定义邮箱配置

服务器地址/端口由用户在添加账号时填写，存入 credentials.extra。
本文件仅提供默认端口和加密方式常量，供前端联动和后端 fallback 使用。
"""

# SMTP 默认端口（按加密方式），IMAP 首期仅支持 SSL 直连 993
DEFAULT_SMTP_PORT = {"ssl": 465, "starttls": 587}

# 默认加密方式
DEFAULT_SSL = "ssl"

# 单个 socket 操作超时秒数
TIMEOUT = 30
