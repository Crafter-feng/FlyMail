"""PKCE 辅助模块：为 Cloudflare OAuth Broker 流程提供安全绑定。

实现 OAuth 2.0 PKCE（RFC 7636），安全地将授权启动请求与后续的
token 兑换绑定，无需各飞邮实例与 Cloudflare Worker 之间预共享密钥。

每个飞邮实例为每次授权请求生成自己的 code_verifier，
向 Worker 发送 code_challenge（SHA-256 哈希），
兑换时再提交 code_verifier，Worker 验证哈希是否匹配。

这样 N 个飞邮实例可以安全地共用 1 个 Cloudflare Worker，
无需配置共享密钥。
"""
import base64
import hashlib
import secrets
import time

from utils.logger import get_logger

logger = get_logger("services.broker_security")

# 内存缓存：存储 code_verifier，键为 oauth_state
# 格式: {state_key: (code_verifier, expire_time)}
_pkce_cache: dict[str, tuple[str, float]] = {}

# code_verifier 缓存有效期（秒），与 OAuth state 有效期一致
_PKCE_CACHE_TTL = 600


def generate_pkce_verifier() -> str:
    """生成 PKCE code_verifier（RFC 7636: 43~128 字符的 URL 安全字符串）。"""
    return secrets.token_urlsafe(32)


def compute_pkce_challenge(code_verifier: str) -> str:
    """根据 code_verifier 计算 code_challenge（S256 方式）。

    code_challenge = BASE64URL(SHA256(code_verifier))
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def store_pkce_verifier(state_key: str, code_verifier: str) -> None:
    """将 code_verifier 存入内存缓存，供回调时取回。"""
    _cleanup_expired_entries()
    _pkce_cache[state_key] = (code_verifier, time.time() + _PKCE_CACHE_TTL)


def retrieve_pkce_verifier(state_key: str) -> str:
    """从内存缓存取回并删除 code_verifier（一次性使用）。"""
    entry = _pkce_cache.pop(state_key, None)
    if entry is None:
        return ""
    code_verifier, expire_time = entry
    if time.time() > expire_time:
        return ""
    return code_verifier


def _cleanup_expired_entries() -> None:
    """清理过期的 PKCE 缓存条目，防止内存泄漏。"""
    now = time.time()
    expired_keys = [k for k, (_, exp) in _pkce_cache.items() if now > exp]
    for k in expired_keys:
        del _pkce_cache[k]
