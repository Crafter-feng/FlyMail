"""共享配置常量

存放多个模块共用的配置常量，避免循环导入。
"""
import os

# 飞牛OS 网关前缀：StripPrefixMiddleware 会剥离此前缀
GATEWAY_PREFIX = "/app/flymail"

# Cloudflare OAuth Broker 地址：Gmail 和 Outlook 都通过 Broker 授权和刷新，避免用户各自配置 OAuth Client 密钥。
OAUTH_BROKER_URL = os.environ.get("OAUTH_BROKER_URL", os.environ.get("OUTLOOK_OAUTH_BROKER_URL", "https://flymail.xinxing.eu.org"))
# 兼容旧环境变量名，避免已部署用户升级后配置失效。
OUTLOOK_OAUTH_BROKER_URL = OAUTH_BROKER_URL
