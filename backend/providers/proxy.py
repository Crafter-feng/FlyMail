"""HTTP 代理隧道工具

通过 HTTP CONNECT 方法建立到目标主机的 TCP 隧道，
让 imaplib/smtplib 这类原生不支持代理的库也能走 HTTP 代理。

支持代理认证（用户名/密码），通过 URL 格式 http://user:pass@host:port 传入。
"""
import socket
import base64
from urllib.parse import urlparse, unquote

from utils.logger import get_logger

logger = get_logger("proxy")


def create_proxy_socket(proxy_url: str, target_host: str, target_port: int, timeout: int = 30) -> socket.socket:
    """通过 HTTP 代理建立到 target_host:target_port 的隧道 socket

    原理：先 TCP 连接 HTTP 代理服务器，再发送 CONNECT 请求建立到目标的隧道，
    代理返回 200 后，这个 socket 就可以当作直连目标的裸 socket 使用（调用方再做 SSL wrap）。

    Args:
        proxy_url: HTTP 代理地址，如 http://127.0.0.1:7890 或 http://user:pass@host:port
        target_host: 最终目标主机（如 imap.gmail.com）
        target_port: 最终目标端口（如 993）
        timeout: 连接超时秒数

    Returns:
        已建立隧道的裸 socket，调用方负责在其上做 SSL wrap

    Raises:
        ValueError: 代理地址格式无效
        ConnectionError: 代理连接失败或 CONNECT 被拒绝
        socket.gaierror: 代理服务器域名解析失败
    """
    parsed = urlparse(proxy_url)
    proxy_host = parsed.hostname
    proxy_port = parsed.port or 8080
    if not proxy_host:
        raise ValueError(f"代理地址无效: {proxy_url}")

    # 1. 建立到代理服务器的 TCP 连接（强制 IPv4，与 IPv4IMAP4_SSL 保持一致）
    addr_infos = socket.getaddrinfo(proxy_host, proxy_port, socket.AF_INET, socket.SOCK_STREAM)
    if not addr_infos:
        raise socket.gaierror(f"无法解析代理服务器 {proxy_host} 的 IPv4 地址")
    af, socktype, proto, _, sa = addr_infos[0]
    sock = socket.socket(af, socktype, proto)
    sock.settimeout(timeout)
    sock.connect(sa)

    # 2. 构造 CONNECT 请求（建立到目标主机的隧道）
    connect_lines = [
        f"CONNECT {target_host}:{target_port} HTTP/1.1",
        f"Host: {target_host}:{target_port}",
    ]
    # 代理认证（URL 中携带用户名密码时，用 Proxy-Authorization: Basic）
    if parsed.username:
        username = unquote(parsed.username)
        password = unquote(parsed.password) if parsed.password else ""
        credentials = f"{username}:{password}"
        b64 = base64.b64encode(credentials.encode()).decode()
        connect_lines.append(f"Proxy-Authorization: Basic {b64}")
    connect_request = "\r\n".join(connect_lines) + "\r\n\r\n"

    sock.sendall(connect_request.encode())

    # 3. 读取代理响应，期望 HTTP/1.1 200
    # 只读响应头（直到空行），避免读到目标服务器的握手数据
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise ConnectionError("代理服务器关闭连接，未返回 CONNECT 响应")
        buf += chunk
        if len(buf) > 8192:
            sock.close()
            raise ConnectionError("代理响应头过长，可能不是标准 HTTP 代理")

    status_line = buf.split(b"\r\n", 1)[0].decode("ascii", errors="ignore")
    # 状态行格式：HTTP/1.1 200 Connection established
    if " 200 " not in status_line and not status_line.endswith(" 200"):
        sock.close()
        raise ConnectionError(f"代理 CONNECT 失败: {status_line}")

    logger.debug("代理隧道建立成功: %s -> %s:%d", proxy_url, target_host, target_port)
    return sock
