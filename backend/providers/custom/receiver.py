import asyncio
import base64
import imaplib
import re
import ssl
from typing import Optional
from ..base import Credentials, Folder, Message, MessageList
from ..base_imap import BaseIMAPReceiver
from ..ipv4 import IPv4IMAP4_SSL
from .config import TIMEOUT
from utils.logger import get_logger

logger = get_logger("custom")


def _decode_modified_utf7(value: str) -> str:
    """Decode IMAP Modified UTF-7 folder names while preserving undecodable input."""
    result = []
    i = 0
    while i < len(value):
        if value[i] != "&":
            result.append(value[i])
            i += 1
            continue

        end = value.find("-", i)
        if end == -1:
            result.append(value[i:])
            break
        if end == i + 1:
            result.append("&")
        else:
            encoded = value[i + 1:end].replace(",", "/")
            padding = 4 - len(encoded) % 4
            if padding < 4:
                encoded += "=" * padding
            try:
                result.append(base64.b64decode(encoded).decode("utf-16-be"))
            except Exception:
                result.append(value[i:end + 1])
        i = end + 1
    return "".join(result)


def _classify_core_folder(folder_name: str, flags: list[str]) -> str:
    """识别核心文件夹，返回统一的中文显示名；无法识别时返回空字符串。

    识别优先级：
    1. IMAP 特殊标志（\\Sent \\Drafts \\Junk \\Trash）— 最可靠
    2. 文件夹名关键词匹配（英文/中文，支持多种变体）
    """
    flag_set = set(flags)
    if "\\Sent" in flag_set:
        return "已发送"
    if "\\Drafts" in flag_set:
        return "草稿箱"
    if "\\Junk" in flag_set:
        return "垃圾邮件"
    if "\\Trash" in flag_set:
        return "已删除"

    decoded = _decode_modified_utf7(folder_name).strip()
    lowered = decoded.lower()
    if lowered == "inbox":
        return "收件箱"
    # 已发送：兼容 outbox（发件箱）、多种英文变体和中文别名
    if lowered in {"sent", "sent messages", "sent items", "outbox"} or decoded in {"已发送", "已发送邮件", "发件箱"}:
        return "已发送"
    # 草稿箱：增加 "draft messages" 和 "草稿"
    if lowered in {"draft", "drafts", "draft messages"} or decoded in {"草稿箱", "草稿"}:
        return "草稿箱"
    # 垃圾邮件：增加 "bulk"、"bulk mail" 和 "垃圾箱"
    if lowered in {"junk", "spam", "junk email", "bulk", "bulk mail"} or decoded in {"垃圾邮件", "垃圾箱"}:
        return "垃圾邮件"
    # 已删除：增加 "bin" 和 "删除"
    if lowered in {"trash", "deleted", "deleted items", "deleted messages", "bin"} or decoded in {"已删除", "已删除邮件", "删除邮件", "删除"}:
        return "已删除"
    return ""


def _create_custom_ssl_context():
    """创建自定义邮箱 SSL 上下文：兼容自签名证书和旧 TLS 服务"""
    ctx = ssl._create_unverified_context()
    # 某些老服务器只支持旧 TLS，降低安全等级以提升自定义邮箱兼容性
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    return ctx


class CustomIMAP4_SSL(IPv4IMAP4_SSL):
    """自定义邮箱专用 IMAP4_SSL：宽松 SSL 上下文，兼容自签名证书

    默认 SSL 上下文（ssl.create_default_context）会严格验证服务器证书，
    自建邮箱服务器常使用自签名证书或私有 CA，会导致 SSLV3_ALERT_HANDSHAKE_FAILURE。
    这里覆盖 _get_ssl_context() 关闭证书验证，并放宽协议版本范围。
    """

    def _get_ssl_context(self):
        return _create_custom_ssl_context()


class CustomIMAP4(imaplib.IMAP4):
    """自定义邮箱专用 IMAP4：强制 IPv4，支持明文和 STARTTLS

    139 邮箱这类服务可能只开放 143 明文 IMAP，993 SSL 会握手失败。
    所以自定义邮箱需要允许用户选择 none/starttls/ssl 三种模式。
    """

    def open(self, host='', port=143, timeout=None):
        """建立 IPv4 明文 IMAP 连接"""
        import socket

        addr_infos = socket.getaddrinfo(
            host, port or 143, socket.AF_INET, socket.SOCK_STREAM
        )
        if not addr_infos:
            raise socket.gaierror(f"无法解析 {host} 的 IPv4 地址")
        af, socktype, proto, canonname, sa = addr_infos[0]
        sock = socket.socket(af, socktype, proto)
        sock.settimeout(timeout or TIMEOUT)
        sock.connect(sa)
        self.host = host
        self.port = port
        self.sock = sock
        self.file = self.sock.makefile('rb')


class CustomReceiver(BaseIMAPReceiver):
    """自定义邮箱 IMAP 接收器

    服务器地址/端口从 credentials.extra 读取，支持 SSL / STARTTLS / 不加密三种 IMAP 连接方式。
    新邮件监听使用 provider 自身的 NOOP/STATUS 单连接轮询，避免自定义服务器不兼容 IDLE 或 aioimaplib 并行轮询。
    文件夹识别复用 BaseIMAPReceiver 的通用逻辑（按 IMAP flags 识别核心文件夹）。

    SSL 上下文采用宽松策略（不验证证书），兼容自签名证书和私有 CA 的自建邮箱服务器。
    """

    TIMEOUT = TIMEOUT

    def __init__(self):
        self.conn: Optional[CustomIMAP4_SSL] = None
        self.email_addr: str = ""
        self._auth_code: str = ""
        self._last_credentials: Optional[Credentials] = None  # 保存凭据供重连使用
        self._folder_counts: dict = {}  # 每个文件夹的上次已知邮件数，用于轮询检测新邮件

    # ---- _conn 属性别名，使基类方法兼容 self.conn 命名 ----
    @property
    def _conn(self):
        return self.conn

    @_conn.setter
    def _conn(self, value):
        self.conn = value

    async def connect(self, credentials: Credentials) -> None:
        """连接到自定义邮箱 IMAP 服务器（在线程池中执行阻塞操作）"""
        self.email_addr = credentials.extra.get("email", "")
        self._auth_code = credentials.access_token  # 授权码或密码
        self._last_credentials = credentials  # 保存凭据供重连使用

        try:
            self._conn = await asyncio.to_thread(self._connect_imap, credentials)
        except Exception as e:
            self._conn = None
            raise Exception(f"自定义邮箱连接失败: {str(e)}")

    def _connect_imap(self, credentials: Credentials):
        """同步建立 IMAP 连接（在线程池中运行）

        根据 imap_ssl 选择连接方式：
        - ssl：SSL 直连，常用 993
        - starttls：143 明文连接后升级 TLS
        - none：143 明文连接，兼容 139 邮箱等特殊服务
        """
        host = credentials.extra.get("imap_host", "")
        port = credentials.extra.get("imap_port", 993)
        ssl_mode = credentials.extra.get("imap_ssl", "ssl")
        if not host:
            raise ValueError("缺少 IMAP 服务器地址")

        if ssl_mode == "ssl":
            conn = CustomIMAP4_SSL(host, port, timeout=self.TIMEOUT)
        else:
            conn = CustomIMAP4(host, port, timeout=self.TIMEOUT)
            if ssl_mode == "starttls":
                # STARTTLS：先连 143，再升级 TLS；自定义邮箱使用宽松 SSL 上下文兼容私有证书
                conn.starttls(ssl_context=_create_custom_ssl_context())
        # 登录失败时关闭连接，防止 socket 泄漏
        try:
            conn.login(self.email_addr, self._auth_code)
            return conn
        except Exception:
            try:
                conn.logout()
            except Exception as e:
                logger.debug("登录失败后关闭连接失败: %s", e)
            raise

    async def fetch_folders(self) -> list:
        """获取文件夹列表

        复用 BaseIMAPReader 的通用 IMAP 文件夹解析逻辑，
        按 IMAP flags（\\Sent \\Drafts \\Junk \\Trash）识别核心文件夹。
        """
        # BaseIMAPReceiver 的辅助方法可直接使用 self._conn
        return await asyncio.to_thread(self._fetch_folders_sync)

    def _fetch_folders_sync(self) -> list:
        """同步获取文件夹列表（在线程池中运行）

        识别核心文件夹（收件箱/已发送/草稿箱/垃圾邮件/已删除），
        同时显示其他非核心、非子文件夹（用解码后的名称作为显示名）。
        参考 QQ receiver 逻辑：未识别的文件夹也展示给用户，避免只显示收件箱。
        """
        status, folder_list = self._conn.list()
        if status != "OK":
            return []

        folder_infos: list[tuple[list[str], str]] = []
        for item in folder_list or []:
            if isinstance(item, bytes):
                item = item.decode("utf-8", errors="ignore")
            else:
                item = str(item)

            # LIST 常见格式: (\HasNoChildren \Sent) "/" "&XfJT0ZAB-"
            match = re.match(r'\(([^)]*)\)\s+"[^"]*"\s+"([^"]+)"', item)
            if not match:
                match = re.match(r'\(([^)]*)\)\s+\S+\s+(.+)$', item)
            if not match:
                continue

            flags_part, folder_name = match.groups()
            folder_name = folder_name.strip().strip('"')
            flags = flags_part.split()
            folder_infos.append((flags, folder_name))

        # 第一步：识别核心文件夹（保持原有顺序：收件箱 → 已发送 → 草稿箱 → 垃圾邮件 → 已删除）
        result = [Folder(name="收件箱", path="INBOX", unread_count=0, total_count=0)]
        # 跟踪已添加的 IMAP 路径（而非显示名），避免同名文件夹被误判
        # IMAP 协议规定 INBOX 不区分大小写，服务器可能返回 "Inbox"/"INBOX" 等变体
        added_paths = {"INBOX"}
        for flags, folder_name in folder_infos:
            if _classify_core_folder(folder_name, flags) == "收件箱" and folder_name not in added_paths:
                added_paths.add(folder_name)
        ordered_names = ["已发送", "草稿箱", "垃圾邮件", "已删除"]
        classified = [
            (_classify_core_folder(folder_name, flags), folder_name)
            for flags, folder_name in folder_infos
        ]

        for display_name in ordered_names:
            for name, folder_name in classified:
                if name == display_name and folder_name not in added_paths:
                    result.append(Folder(name=display_name, path=folder_name, unread_count=0, total_count=0))
                    added_paths.add(folder_name)
                    break

        # 第二步：添加其他非核心、非子文件夹（参考 QQ receiver 逻辑）
        # 确保未识别的文件夹也能显示，避免只显示收件箱
        for flags, folder_name in folder_infos:
            # 跳过已添加的核心文件夹
            if folder_name in added_paths:
                continue
            # 跳过子文件夹（包含分隔符 / 或 \，如 "INBOX/Sent" 或 "INBOX.Sent"）
            if "/" in folder_name or "\\" in folder_name:
                continue
            # 跳过特殊系统文件夹（以 [ 开头，如 "[Gmail]/..."）
            if folder_name.startswith("["):
                continue
            # 用解码后的名称作为显示名（Modified UTF-7 解码中文文件夹名）
            display_name = _decode_modified_utf7(folder_name).strip() or folder_name
            result.append(Folder(name=display_name, path=folder_name, unread_count=0, total_count=0))
            added_paths.add(folder_name)

        return result

    async def disconnect(self) -> None:
        """断开 IMAP 连接"""
        if self.conn:
            try:
                await asyncio.to_thread(self.conn.logout)
            except Exception as e:
                logger.debug("断开连接失败: %s", e)
            self.conn = None

    # ---- 邮件列表 ----

    async def fetch_messages(self, folder: str = "INBOX", page: int = 1, page_size: int = 20) -> MessageList:
        """获取邮件列表（分页，只获取头部不下载正文）"""
        if not self._conn:
            raise ConnectionError("未连接到邮箱服务器")

        try:
            return await asyncio.to_thread(self._fetch_messages_sync, folder, page, page_size)
        except Exception as e:
            raise Exception(f"获取邮件失败: {str(e)}")

    def _fetch_messages_sync(self, folder: str, page: int, page_size: int) -> MessageList:
        """同步获取邮件列表（在线程池中运行）

        使用 UID SEARCH + 批量 UID FETCH，与新浪/QQ 等授权码类 provider 逻辑一致。
        """
        # SELECT 只读模式打开文件夹
        status, data = self._conn.select(self._quote_mailbox(folder), readonly=True)
        if status != "OK":
            return MessageList(messages=[], total=0, page=page, page_size=page_size)

        # UID SEARCH 获取所有邮件 UID
        status, data = self._conn.uid('SEARCH', None, 'ALL')
        if not data[0]:
            return MessageList(messages=[], total=0, page=page, page_size=page_size)

        msg_uids = data[0].split()
        total = len(msg_uids)

        # 获取未读邮件总数
        unread_total = 0
        try:
            s, u_data = self._conn.search(None, "UNSEEN")
            if s == "OK" and u_data[0]:
                unread_total = len(u_data[0].split())
        except Exception as e:
            logger.debug("获取未读邮件总数失败: %s", e)

        # 分页：取最新的一页（倒序，最新的在前面）
        start = max(0, total - page * page_size)
        end = max(0, total - (page - 1) * page_size)
        page_uids = list(reversed(msg_uids[start:end]))

        if not page_uids:
            return MessageList(messages=[], total=total, unread_total=unread_total, page=page, page_size=page_size)

        # 批量 UID FETCH：一次请求获取整页邮件摘要
        uid_set = b",".join(page_uids)
        status, msg_data = self._conn.uid(
            'FETCH', uid_set,
            self._LIST_FETCH_ITEMS,
        )
        if status != 'OK':
            return MessageList(messages=[], total=total, unread_total=unread_total, page=page, page_size=page_size)

        # 使用基类统一方法解析批量 FETCH 返回数据
        messages = self._parse_batch_fetch_response(msg_data, folder)
        messages.sort(key=lambda m: m.uid, reverse=True)

        return MessageList(
            messages=messages,
            total=total,
            unread_total=unread_total,
            page=page,
            page_size=page_size,
        )

    async def idle_wait(self, folder: str = "INBOX", timeout_seconds: int = 1740) -> str:
        """自定义邮箱使用 NOOP/STATUS 轮询检测邮件数量变化

        自定义邮箱服务商差异较大，不默认使用 IMAP IDLE 或 aioimaplib 并行轮询。
        这里复用网易邮箱的稳定策略：单连接串行轮询 STATUS，并用 NOOP 保活。
        等待过程使用 asyncio.sleep，不再在线程池里 time.sleep，避免长期占用 worker。

        返回值：
        - "new_mail": 邮件数量增加
        - "expunge": 邮件数量减少
        - "timeout": 超时无变化
        """
        if not self._conn:
            raise Exception("未连接到邮箱服务器")

        poll_interval = max(1, min(5, int(timeout_seconds or 5)))
        actual_timeout = max(poll_interval, min(timeout_seconds, 60))
        last_count = self._folder_counts.get(folder, -1)
        if last_count < 0:
            last_count = await asyncio.to_thread(self._get_folder_message_count, folder)
            if last_count < 0:
                raise ConnectionError("NOOP 轮询启动失败，IMAP 连接不可用")
            self._folder_counts[folder] = last_count

        elapsed = 0
        while elapsed < actual_timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            event = await asyncio.to_thread(self._noop_poll_once, folder, last_count)
            if event in ("new_mail", "expunge"):
                return event
            last_count = self._folder_counts.get(folder, last_count)
        return "timeout"

    def _noop_poll_once(self, folder: str, last_count: int) -> str:
        """执行一次 STATUS + NOOP 检测，避免在线程里长时间 sleep"""
        try:
            current_count = self._get_folder_message_count(folder)
            if current_count < 0:
                raise ConnectionError("IMAP 连接已断开")
            if current_count > last_count:
                logger.info("检测到新邮件: folder=%s, %d -> %d", folder, last_count, current_count)
                self._folder_counts[folder] = current_count
                return "new_mail"
            if current_count < last_count:
                logger.info("检测到邮件减少: folder=%s, %d -> %d", folder, last_count, current_count)
                self._folder_counts[folder] = current_count
                return "expunge"

            self._folder_counts[folder] = current_count
            if self._conn:
                try:
                    self._conn.noop()
                except Exception:
                    self._conn = None
                    raise ConnectionError("IMAP 连接已断开")
        except Exception as e:
            if "IMAP 连接已断开" in str(e):
                raise
            # 降级为 DEBUG：轮询异常是预期的瞬态错误，重连机制会自动恢复
            logger.debug("NOOP 轮询异常: %s", e)
        return "timeout"

    async def _reconnect(self) -> None:
        """重连 IMAP 服务器（基类 _ensure_connected 在连接断开时调用）"""
        if self.conn:
            try:
                self.conn.logout()
            except Exception:
                pass
            self.conn = None

        # 重新建立连接（复用 connect 方法的逻辑）
        from providers.custom.auth import CustomAuthProvider
        server_config = {
            "imap_host": self._last_credentials.extra.get("imap_host", ""),
            "imap_port": self._last_credentials.extra.get("imap_port", 993),
            "imap_ssl": self._last_credentials.extra.get("imap_ssl", "ssl"),
        }
        self._conn = await asyncio.to_thread(self._connect_imap, CustomAuthProvider.create_credentials(
            self.email_addr, self._auth_code, server_config
        ))
