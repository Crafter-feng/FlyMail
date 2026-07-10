"""IPv4 强制连接子类

某些系统（如飞牛OS）优先解析 IPv6，导致 IMAP/SMTP 连接超时。
此模块提供统一的 IPv4 强制连接子类，供所有 Provider 共享使用。

使用方式：
    from providers.ipv4 import IPv4IMAP4_SSL, IPv4SMTP, IPv4SMTP_SSL

    # IMAP 连接（默认 SSL）
    conn = IPv4IMAP4_SSL(host, port, timeout=30)

    # SMTP 连接（STARTTLS 模式）
    smtp = IPv4SMTP(host, port, timeout=30)

    # SMTP 连接（SSL 直连模式）
    smtp = IPv4SMTP_SSL(host, port, timeout=30)
"""
import socket
import ssl
import imaplib
import smtplib


class IPv4IMAP4_SSL(imaplib.IMAP4_SSL):
    """强制 IPv4 的 IMAP4_SSL 子类

    覆盖 open() 方法，使用 socket.getaddrinfo(AF_INET) 强制 IPv4 解析，
    避免某些系统优先使用 IPv6 导致连接超时。
    """

    def open(self, host='', port=993, timeout=None):
        """建立 IPv4 SSL 连接"""
        addr_infos = socket.getaddrinfo(
            host, port or 993, socket.AF_INET, socket.SOCK_STREAM
        )
        if not addr_infos:
            raise socket.gaierror(f"无法解析 {host} 的 IPv4 地址")
        af, socktype, proto, canonname, sa = addr_infos[0]
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(timeout or 30)
        sock.connect(sa)
        context = self._get_ssl_context()
        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        self.host = host
        self.port = port
        self.sock = ssl_sock
        self.file = self.sock.makefile('rb')

    def _get_ssl_context(self):
        """获取 SSL 上下文，子类可覆盖以自定义（如 Outlook 需要 TLS 1.2）"""
        return ssl.create_default_context()


class IPv4SMTP(smtplib.SMTP):
    """强制 IPv4 的 SMTP 子类（STARTTLS 模式）

    覆盖 _get_socket() 方法，使用 IPv4 强制解析。
    包含 timeout 哨兵值保护，避免 smtplib 传入 _GLOBAL_DEFAULT_TIMEOUT 时报错。
    """

    TIMEOUT = 30

    def _get_socket(self, host, port, timeout):
        """获取 IPv4 socket 连接"""
        if not isinstance(timeout, (int, float)):
            timeout = self.TIMEOUT
        addr_infos = socket.getaddrinfo(
            host, port, socket.AF_INET, socket.SOCK_STREAM
        )
        if not addr_infos:
            raise socket.gaierror(f"无法解析 {host} 的 IPv4 地址")
        af, socktype, proto, canonname, sa = addr_infos[0]
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(timeout)
        sock.connect(sa)
        return sock


class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """强制 IPv4 的 SMTP_SSL 子类（SSL 直连模式）

    覆盖 _get_socket() 方法，使用 IPv4 强制解析并包装 SSL。
    """

    TIMEOUT = 30

    def _get_socket(self, host, port, timeout):
        """获取 IPv4 SSL socket 连接"""
        if not isinstance(timeout, (int, float)):
            timeout = self.TIMEOUT
        addr_infos = socket.getaddrinfo(
            host, port, socket.AF_INET, socket.SOCK_STREAM
        )
        if not addr_infos:
            raise socket.gaierror(f"无法解析 {host} 的 IPv4 地址")
        af, socktype, proto, canonname, sa = addr_infos[0]
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(timeout)
        sock.connect(sa)
        ssl_sock = self.context.wrap_socket(sock, server_hostname=self._host)
        return ssl_sock


# ==================== HTTP 代理子类（网络受限环境） ====================


class ProxyIMAP4_SSL(IPv4IMAP4_SSL):
    """支持 HTTP 代理的 IMAP4_SSL

    通过 HTTP CONNECT 隧道连接到 IMAP 服务器，用于网络受限环境访问 Google 等服务。
    继承 IPv4IMAP4_SSL 的 SSL 上下文逻辑，仅覆盖 open() 插入代理隧道建立步骤。
    """

    def __init__(self, host, port=993, proxy_url="", timeout=None):
        # 先存代理地址，再调用父类构造（父类构造会触发 open()）
        self._proxy_url = proxy_url
        super().__init__(host, port, timeout=timeout)

    def open(self, host='', port=993, timeout=None):
        """通过 HTTP 代理建立 SSL IMAP 连接

        流程：连接代理服务器 → CONNECT 隧道 → 在隧道上做 SSL 握手
        """
        from providers.proxy import create_proxy_socket

        target_host = host or self.host
        target_port = port or 993
        # 通过 HTTP CONNECT 建立到目标的裸 socket 隧道
        sock = create_proxy_socket(self._proxy_url, target_host, target_port, timeout or 30)
        # 在隧道上做 SSL 握手（与 IPv4IMAP4_SSL 一致使用默认 SSL 上下文）
        context = self._get_ssl_context()
        ssl_sock = context.wrap_socket(sock, server_hostname=target_host)
        self.host = target_host
        self.port = target_port
        self.sock = ssl_sock
        self.file = self.sock.makefile('rb')


class ProxySMTP(IPv4SMTP):
    """支持 HTTP 代理的 SMTP（STARTTLS 模式）

    通过 HTTP CONNECT 隧道连接到 SMTP 服务器，STARTTLS 在隧道内进行。
    继承 IPv4SMTP 的 timeout 哨兵保护逻辑，仅覆盖 _get_socket() 插入代理隧道。
    """

    def __init__(self, host, port=587, proxy_url="", timeout=30):
        self._proxy_url = proxy_url
        super().__init__(host, port, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        """通过 HTTP 代理建立 TCP 连接（STARTTLS 由外层 GmailSender 处理）"""
        from providers.proxy import create_proxy_socket

        if not isinstance(timeout, (int, float)):
            timeout = self.TIMEOUT
        # 通过代理建立隧道，返回裸 socket（STARTTLS 后续会 wrap SSL）
        return create_proxy_socket(self._proxy_url, host, port, timeout)
