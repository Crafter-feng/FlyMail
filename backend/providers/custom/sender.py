import asyncio
import os
import urllib.parse
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from typing import Optional
from ..base import MailSender, Credentials, SendResult
from providers.ipv4 import IPv4SMTP_SSL, IPv4SMTP
from .config import TIMEOUT
from utils.logger import get_logger

logger = get_logger("custom.sender")


class CustomSender(MailSender):
    """自定义邮箱 SMTP 发送器

    支持两种加密方式：
    - SSL 直连（465）：用 IPv4SMTP_SSL
    - STARTTLS（587）：用 IPv4SMTP + starttls()
    服务器地址/端口/加密方式从 credentials.extra 读取。
    """

    TIMEOUT = TIMEOUT

    def __init__(self):
        self.conn = None
        self.email_addr: str = ""

    async def connect(self, credentials: Credentials) -> None:
        """连接到自定义邮箱 SMTP 服务器"""
        self.email_addr = credentials.extra.get("email", "")
        auth_code = credentials.access_token

        try:
            self.conn = await asyncio.to_thread(self._connect_smtp, credentials, auth_code)
        except Exception as e:
            self.conn = None
            raise Exception(f"自定义邮箱SMTP连接失败: {str(e)}")

    def _connect_smtp(self, credentials: Credentials, auth_code: str):
        """同步建立 SMTP 连接（在线程池中运行）

        根据加密方式选择 SSL 直连或 STARTTLS。
        """
        host = credentials.extra.get("smtp_host", "")
        port = credentials.extra.get("smtp_port", 465)
        ssl_mode = credentials.extra.get("smtp_ssl", "ssl")
        if not host:
            raise ValueError("缺少 SMTP 服务器地址")

        if ssl_mode == "starttls":
            # STARTTLS：先明文连接，再升级为 TLS
            conn = IPv4SMTP(host, port, timeout=self.TIMEOUT)
            conn.ehlo()
            conn.starttls()
            conn.ehlo()
        else:
            # SSL 直连（默认）
            conn = IPv4SMTP_SSL(host, port, timeout=self.TIMEOUT)

        # 登录失败时关闭连接，防止 socket 泄漏
        try:
            conn.login(self.email_addr, auth_code)
            return conn
        except Exception:
            try:
                conn.quit()
            except Exception as e:
                logger.debug("登录失败后关闭连接失败: %s", e)
            raise

    async def send_message(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str = "",
        cc: list[str] = None,
        bcc: list[str] = None,
        attachments: list[str] = None,
        in_reply_to: str = None,
    ) -> SendResult:
        """发送邮件"""
        if not self.conn:
            raise Exception("未连接到SMTP服务器")

        try:
            return await asyncio.to_thread(
                self._send_sync, to, subject, body_html, body_text, cc, bcc, attachments, in_reply_to
            )
        except Exception as e:
            return SendResult(success=False, error=str(e))

    def _send_sync(self, to, subject, body_html, body_text="", cc=None, bcc=None, attachments=None, in_reply_to=None):
        """同步发送邮件（在线程池中运行）

        使用 MIMEMultipart("mixed") 作为外层，内嵌 alternative 放纯文本+HTML，
        附件用 MIMEBase 编码，支持 CC/BCC/In-Reply-To。
        逻辑与 QQSender._send_sync 一致。
        """
        msg = MIMEMultipart("mixed")
        msg["From"] = self.email_addr
        msg["To"] = ", ".join(to) if isinstance(to, list) else to
        if cc:
            msg["Cc"] = ", ".join(cc) if isinstance(cc, list) else cc
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        # 正文：纯文本+HTML
        alt = MIMEMultipart("alternative")
        if body_text:
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
        alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)

        # 附件
        if attachments:
            for file_path in attachments:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_path)
                part.add_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}")
                msg.attach(part)

        # 所有收件人（包括 CC/BCC）
        all_recipients = list(to) if isinstance(to, list) else [to]
        if cc:
            all_recipients.extend(cc if isinstance(cc, list) else [cc])
        if bcc:
            all_recipients.extend(bcc if isinstance(bcc, list) else [bcc])

        self.conn.sendmail(self.email_addr, all_recipients, msg.as_string())
        return SendResult(success=True)

    async def disconnect(self) -> None:
        """断开连接"""
        if self.conn:
            try:
                await asyncio.to_thread(self.conn.quit)
            except Exception as e:
                logger.debug("断开连接失败: %s", e)
            self.conn = None
