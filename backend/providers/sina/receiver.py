import asyncio
import re
from typing import List, Optional
from ..base import Credentials, Folder, Message, MessageList
from ..base_imap import BaseIMAPReceiver
from ..ipv4 import IPv4IMAP4_SSL
from .config import (
    IMAP_SINA_COM_HOST, IMAP_SINA_COM_PORT,
    IMAP_SINA_CN_HOST, IMAP_SINA_CN_PORT,
    IMAP_VIP_SINA_COM_HOST, IMAP_VIP_SINA_COM_PORT,
    IMAP_VIP_SINA_CN_HOST, IMAP_VIP_SINA_CN_PORT,
)
from utils.logger import get_logger

logger = get_logger("sina")


class SinaReceiver(BaseIMAPReceiver):
    """新浪邮箱 IMAP 接收器（支持 sina.com / sina.cn / 2008.sina.com / vip.sina.com / vip.sina.cn）

    新浪邮箱机制：
    1. 使用 16 位客户端授权码（非登录密码）认证
    2. 使用 NOOP/STATUS 轮询检测新邮件（与网易一致）
    3. 不需要发送 IMAP ID 命令（与网易不同，新浪无此要求）

    服务器选择：按邮箱后缀区分 4 套独立服务器
    - @sina.com / @2008.sina.com → imap.sina.com
    - @sina.cn → imap.sina.cn
    - @vip.sina.com → imap.vip.sina.com
    - @vip.sina.cn → imap.vip.sina.cn
    """

    TIMEOUT = 30  # 单个 socket 操作超时 30 秒

    def __init__(self):
        self.conn: Optional[IPv4IMAP4_SSL] = None
        self.email_addr: str = ""
        self._auth_code: str = ""  # 保存授权码，用于自动重连
        self._folder_counts: dict = {}  # 各文件夹上次已知邮件数，用于 NOOP 轮询检测变化

    # ---- _conn 属性别名，使基类方法兼容 self.conn 命名 ----

    @property
    def _conn(self):
        """基类使用 self._conn 访问 IMAP 连接，新浪使用 self.conn，通过属性别名统一"""
        return self.conn

    @_conn.setter
    def _conn(self, value):
        self.conn = value

    # ---- 服务器选择（按邮箱后缀区分 4 套服务器）----

    def _get_imap_host(self, email_addr: str) -> str:
        """根据邮箱后缀返回对应的 IMAP 服务器地址

        新浪邮箱按后缀区分 4 套独立服务器：
        - sina.cn → imap.sina.cn
        - vip.sina.com → imap.vip.sina.com
        - vip.sina.cn → imap.vip.sina.cn
        - sina.com / 2008.sina.com 及其他 → imap.sina.com（默认）
        """
        suffix = email_addr.split("@")[-1].lower() if "@" in email_addr else ""
        host_map = {
            "sina.cn": IMAP_SINA_CN_HOST,
            "vip.sina.com": IMAP_VIP_SINA_COM_HOST,
            "vip.sina.cn": IMAP_VIP_SINA_CN_HOST,
        }
        # sina.com / 2008.sina.com 及其他未知后缀默认走 imap.sina.com
        return host_map.get(suffix, IMAP_SINA_COM_HOST)

    def _get_imap_port(self, email_addr: str) -> int:
        """根据邮箱后缀返回对应的 IMAP 端口（所有新浪邮箱统一 993）"""
        return 993

    # ---- 连接管理 ----

    async def connect(self, credentials: Credentials) -> None:
        """连接到新浪邮箱 IMAP 服务器（在线程池中执行阻塞操作）"""
        self.email_addr = credentials.extra.get("email", "")
        self._auth_code = credentials.access_token  # 新浪邮箱使用授权码

        try:
            # 在线程池中执行阻塞的 IMAP 连接，避免卡住事件循环
            self._conn = await asyncio.to_thread(self._connect_imap, self.email_addr, self._auth_code)
        except Exception as e:
            self._conn = None
            raise Exception(f"新浪邮箱连接失败: {str(e)}")

    def _connect_imap(self, email_addr: str, auth_code: str) -> IPv4IMAP4_SSL:
        """同步建立 IMAP 连接（在线程池中运行，使用 IPv4 强制子类）

        新浪邮箱不需要发送 IMAP ID 命令（与网易不同），
        login 成功后即可直接 SELECT/EXAMINE 文件夹。
        """
        host = self._get_imap_host(email_addr)
        port = self._get_imap_port(email_addr)
        conn = IPv4IMAP4_SSL(host, port, timeout=self.TIMEOUT)
        # 登录失败时关闭连接，防止 socket 泄漏
        try:
            conn.login(email_addr, auth_code)
            return conn
        except Exception:
            # 登录失败，关闭连接防止 socket 泄漏
            try:
                conn.logout()
            except Exception as e:
                logger.debug("登录失败后关闭连接失败: %s", e)
            raise

    async def _reconnect(self) -> None:
        """重连新浪邮箱 IMAP"""
        self._conn = await asyncio.to_thread(self._connect_imap, self.email_addr, self._auth_code)

    async def disconnect(self) -> None:
        """断开连接"""
        if self._conn:
            try:
                await asyncio.to_thread(self._disconnect_sync)
            except Exception as e:
                logger.debug("断开连接失败: %s", e)
            self._conn = None

    def _disconnect_sync(self) -> None:
        """同步断开连接（在线程池中运行）"""
        try:
            self._conn.close()
        except Exception as e:
            logger.debug("关闭 IMAP 连接失败: %s", e)
        try:
            self._conn.logout()
        except Exception as e:
            logger.debug("登出 IMAP 连接失败: %s", e)

    # ---- NOOP 轮询（STATUS 命令检测新邮件）----

    async def idle_wait(self, folder: str = "INBOX", timeout_seconds: int = 1740) -> str:
        """NOOP/STATUS 轮询检测邮件数量变化

        等待过程使用 asyncio.sleep，不再在线程池里 time.sleep，避免长期占用 worker。
        使用 _folder_counts 维护每个文件夹的上次已知邮件数，
        避免新邮件在两次调用之间到达时被错过。

        返回值：
        - "new_mail": 数量增加
        - "expunge": 数量减少
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
            # 更新已知计数
            self._folder_counts[folder] = current_count
            # NOOP 保持连接活跃
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

    # ---- 文件夹列表 ----

    async def fetch_folders(self) -> List[Folder]:
        """获取邮箱文件夹列表"""
        if not self._conn:
            raise ConnectionError("未连接到邮箱服务器")

        try:
            return await asyncio.to_thread(self._fetch_folders_sync)
        except Exception as e:
            raise Exception(f"获取文件夹失败: {str(e)}")

    def _fetch_folders_sync(self) -> List[Folder]:
        """同步获取文件夹列表（在线程池中运行）

        新浪邮箱的文件夹名使用 Modified UTF-7 编码（如 &XfJT0ZAB- 表示"已发送"），
        无法通过英文路径名匹配。但 IMAP LIST 返回了特殊标志（\\Sent, \\Drafts 等），
        通过特殊标志识别核心文件夹，路径保留 Modified UTF-7 原始编码供后续 IMAP 命令使用。
        """
        status, folders = self._conn.list()
        result = []

        # 解析 IMAP LIST 响应，提取标志和文件夹名
        # 格式: (\HasNoChildren \Sent) "/" "&XfJT0ZAB-"
        folder_infos = []  # [(flags: list, name: str), ...]
        for folder_data in folders or []:
            if isinstance(folder_data, bytes):
                folder_str = folder_data.decode("utf-8", errors="ignore")
            else:
                folder_str = str(folder_data)

            # 匹配: (标志列表) "分隔符" "文件夹名"
            match = re.match(r'\(([^)]*)\)\s+"[^"]+"\s+"([^"]+)"', folder_str)
            if match:
                flags_str, folder_name = match.groups()
                flags = flags_str.split()
                folder_infos.append((flags, folder_name))
            else:
                # 备选：提取最后一个引号中的内容作为文件夹名
                match = re.search(r'"([^"]+)"$', folder_str)
                if match:
                    folder_name = match.group(1)
                    folder_infos.append(([], folder_name))

        # INBOX 始终在第一位
        result.append(Folder(name="收件箱", path="INBOX", unread_count=0, total_count=0))

        # 使用特殊标志识别核心文件夹（顺序：已发送、草稿箱、垃圾邮件、已删除）
        # 与 QQ/网易等保持一致的显示顺序
        ordered_flags = [("\\Sent", "已发送"), ("\\Drafts", "草稿箱"),
                         ("\\Junk", "垃圾邮件"), ("\\Trash", "已删除")]
        for target_flag, display_name in ordered_flags:
            for flags, folder_name in folder_infos:
                if target_flag in flags:
                    result.append(Folder(
                        name=display_name,
                        path=folder_name,  # 保留 Modified UTF-7 原始路径
                        unread_count=0,
                        total_count=0,
                    ))
                    break

        return result

    # ---- 邮件列表 ----

    async def fetch_messages(self, folder: str = "INBOX", page: int = 1, page_size: int = 20) -> MessageList:
        """获取邮件列表"""
        if not self._conn:
            raise ConnectionError("未连接到邮箱服务器")

        try:
            return await asyncio.to_thread(self._fetch_messages_sync, folder, page, page_size)
        except Exception as e:
            raise Exception(f"获取邮件失败: {str(e)}")

    def _fetch_messages_sync(self, folder: str, page: int, page_size: int) -> MessageList:
        """同步获取邮件列表（在线程池中运行，只获取头部不下载正文）

        使用 UID SEARCH + 批量 UID FETCH 替代逐封 FETCH，减少 IMAP 命令往返次数。
        - UID SEARCH: 获取所有邮件的 UID 列表（比序列号更稳定，不受邮箱变动影响）
        - 批量 UID FETCH: 用逗号拼接 UID 集合，一次请求获取整页邮件摘要

        已读/未读状态判断：
        使用 FETCH (FLAGS BODY.PEEK[HEADER.FIELDS ...]) 一次请求同时获取 FLAGS 和头部。
        - BODY.PEEK 不会隐式设置 \\Seen 标志
        - FLAGS 中包含 \\Seen 表示已读，不包含表示未读
        """
        # SELECT 必须用 readonly=True，避免意外修改邮件状态
        status, data = self._conn.select(self._quote_mailbox(folder), readonly=True)
        if status != "OK":
            return MessageList(messages=[], total=0, page=page, page_size=page_size)

        # 使用 UID SEARCH 获取所有邮件 UID，比序列号 SEARCH 更稳定可靠
        status, data = self._conn.uid('SEARCH', None, 'ALL')
        if not data[0]:
            return MessageList(messages=[], total=0, page=page, page_size=page_size)

        # 解析 UID 列表
        msg_uids = data[0].split()
        total = len(msg_uids)

        # 获取未读邮件总数（用于侧边栏计数）
        unread_total = 0
        try:
            s, u_data = self._conn.search(None, "UNSEEN")
            if s == "OK" and u_data[0]:
                unread_total = len(u_data[0].split())
        except Exception as e:
            logger.debug("获取未读邮件总数失败: %s", e)

        # 分页：取最新的一页（倒序，最新的在前面）
        # 只用 UID 做分页，绝不使用序列号（1:20）
        start = max(0, total - page * page_size)
        end = max(0, total - (page - 1) * page_size)
        page_uids = list(reversed(msg_uids[start:end]))

        if not page_uids:
            return MessageList(messages=[], total=total, unread_total=unread_total, page=page, page_size=page_size)

        # 批量 UID FETCH：用逗号拼接 UID 集合，一次请求获取整页邮件
        uid_set = b",".join(page_uids)
        status, msg_data = self._conn.uid(
            'FETCH', uid_set,
            '(FLAGS BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])'
        )
        if status != 'OK':
            return MessageList(messages=[], total=total, unread_total=unread_total, page=page, page_size=page_size)

        # 使用基类统一方法解析批量 FETCH 返回数据
        messages = self._parse_batch_fetch_response(msg_data, folder)

        # 批量 FETCH 不保证返回顺序，必须按 UID 降序排列（最新的在前）
        messages.sort(key=lambda m: m.uid, reverse=True)

        return MessageList(
            messages=messages,
            total=total,
            unread_total=unread_total,
            page=page,
            page_size=page_size
        )
