"""邮件备份服务 - 将邮件以 .eml 格式归档到飞牛OS 授权目录

架构:
  同步管道 → archive_message() → FETCH BODY[] → 写 .eml → 写 message_archive 表

存储结构:
  {备份根目录}/{邮箱地址}/{文件夹中文名}/{日期}_{主题}_{uid}.eml
  示例: /授权目录/zhangsan@qq.com/收件箱/2026-07-13_项目周报_12345.eml

备份根目录来源（按优先级）:
  1. 用户在设置中选择的授权目录（user_settings.backup_target_dir）
  2. 飞牛授权目录（优先读 accessible_paths.env 落盘文件，兜底读 TRIM_DATA_ACCESSIBLE_PATHS 环境变量）
  3. 无授权目录时禁止备份并提示用户先授权
"""
import asyncio
import base64
import os
import re
import time
from email import message_from_bytes, policy
from email.utils import parsedate_to_datetime, formatdate, make_msgid
from email.encoders import encode_base64
from pathlib import Path
from typing import Optional

from db import (
    upsert_message_archive,
    get_archived_uids,
    get_user_setting,
    get_accounts,
)
from models import Account
from providers.base_imap import BaseIMAPReceiver
from providers.factory import ProviderFactory
from utils.logger import get_logger
from utils.paths import get_accessible_paths, is_path_authorized

logger = get_logger("backup")


# ==================== 备份目录管理 ====================

def get_backup_root() -> Optional[Path]:
    """获取备份根目录（同步，无授权目录时返回 None）

    优先级：
    1. 飞牛授权目录（优先读 accessible_paths.env 落盘文件，兜底读环境变量）
    2. 无授权目录时返回 None，调用方应禁止备份并提示用户先授权

    注意：不再降级到 FLYMAIL_DATA_DIR/backup/，避免在非授权位置创建备份文件。
    """
    accessible = get_accessible_paths()
    for p in accessible:
        try:
            if os.path.isdir(p) and os.access(p, os.W_OK):
                return Path(p)
        except Exception:
            continue
    return None


async def get_backup_root_async(user_uid: str) -> Optional[Path]:
    """获取备份根目录（异步，读用户设置，无授权目录时返回 None）

    优先级：
    1. 用户设置的授权目录（user_settings 表 backup_target_dir，必须在飞牛授权目录内）
    2. 飞牛授权目录（get_backup_root）
    3. 无授权目录时返回 None，调用方应禁止备份并提示用户先授权
    """
    user_target = await get_user_setting(user_uid, "backup_target_dir", "")
    if user_target:
        path = Path(user_target)
        try:
            # 校验用户设置的目录必须在飞牛授权目录内
            if path.exists() and os.access(path, os.W_OK) and is_path_authorized(str(path)):
                return path
        except Exception:
            pass
    # 降级到飞牛授权目录（同步函数用 to_thread 包装避免阻塞事件循环）
    return await asyncio.to_thread(get_backup_root)


def sanitize_filename(text: str, max_len: int = 30) -> str:
    """清洗文件名中的非法字符

    替换 Windows/Linux 文件名非法字符（\\ / : * ? " < > |）为下划线，
    去除首尾空格和点，截断到最大长度。
    """
    safe = re.sub(r'[\\/:*?"<>|]', '_', text)
    safe = safe.strip(' .')
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe or 'untitled'


def folder_display_name(folder: str) -> str:
    """将 IMAP 文件夹路径转换为中文显示名

    常见邮箱文件夹（如 INBOX、Sent Messages）映射为中文名，
    未识别的文件夹使用原始名（清洗斜杠后）。
    """
    # 常见文件夹中文名映射（覆盖 QQ/网易/Gmail/iCloud/Outlook 等主流邮箱）
    folder_map = {
        'INBOX': '收件箱',
        'Sent': '已发送',
        'Sent Messages': '已发送',
        'Sent Items': '已发送',
        'Outbox': '发件箱',
        'Drafts': '草稿箱',
        'Draft Messages': '草稿箱',
        'Junk': '垃圾邮件',
        'Junk Email': '垃圾邮件',
        'Junk E-mail': '垃圾邮件',
        'Spam': '垃圾邮件',
        'Bulk Mail': '垃圾邮件',
        'Trash': '已删除',
        'Deleted': '已删除',
        'Deleted Messages': '已删除',
        'Deleted Items': '已删除',
        'Archive': '归档',
        'Archives': '归档',
        # Gmail 特殊文件夹
        '[Gmail]/Sent Mail': '已发送',
        '[Gmail]/Drafts': '草稿箱',
        '[Gmail]/Trash': '已删除',
        '[Gmail]/Spam': '垃圾邮件',
        '[Gmail]/All Mail': '所有邮件',
        '[Gmail]/Starred': '已加星标',
        '[Gmail]/Important': '重要邮件',
        '[Gmail]/Archived': '归档',
    }
    return folder_map.get(folder, sanitize_filename(folder.replace("/", "_").replace("\\", "_"), 50))


def normalize_date_for_sort(date_str: str) -> str:
    """将 RFC 2822 日期转为 ISO 格式，供 SQLite 排序

    SQLite 字符串排序无法正确处理 RFC 2822 格式（如 'Fri, 11 Jul 2026 02:17:55 +0000'），
    转为 'YYYY-MM-DD HH:MM:SS' 后字符串排序等价于时间排序。

    解析失败时返回空字符串（排序时排到最后）。
    """
    if not date_str:
        return ''
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ''


def normalize_eml(raw_bytes: bytes) -> bytes:
    """规范化 .eml 内容，确保完整的 MIME 结构和 base64 编码

    解决 IMAP 原始字节直接写入 .eml 后的问题：
    1. 部分邮件缺失 MIME-Version / Date / Message-ID 头，导致邮件客户端解析异常
    2. 正文或附件使用 8bit / 7bit / quoted-printable 编码，记事本打开显示乱码
    3. 行结束符不统一（\\n 与 \\r\\n 混用）

    处理流程:
    1. 解析原始字节为 Message 对象
    2. 补全缺失的必需头（MIME-Version、Date、Message-ID）
    3. 遍历所有非 multipart 部分，统一转为 base64 编码
    4. 用 SMTP policy 序列化为标准 MIME 格式（统一 \\r\\n 行结束符）

    异常时回退原字节，保证备份不中断。
    """
    if not raw_bytes:
        return raw_bytes

    try:
        msg = message_from_bytes(raw_bytes)
    except Exception as e:
        logger.warning("解析邮件失败，保留原始字节: %s", e)
        return raw_bytes

    # 1. 补全缺失的必需邮件头
    if not msg.get('MIME-Version'):
        msg['MIME-Version'] = '1.0'
    if not msg.get('Date'):
        msg['Date'] = formatdate(localtime=True)
    if not msg.get('Message-ID'):
        msg['Message-ID'] = make_msgid()

    # 2. 遍历所有部分，统一使用 base64 编码（跳过 multipart 容器）
    for part in msg.walk():
        if part.is_multipart():
            continue
        cte = (part.get('Content-Transfer-Encoding', '') or '').lower()
        if cte == 'base64':
            continue  # 已是 base64，无需重新编码
        # 解码出原始字节（自动处理 8bit/7bit/quoted-printable）
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        # 删除旧的编码头，重新以 base64 编码
        del part['Content-Transfer-Encoding']
        part.set_payload(payload)
        encode_base64(part)  # 自动设置 Content-Transfer-Encoding: base64

    # 3. 序列化为标准 MIME 格式（SMTP policy 保证 \\r\\n 行结束符）
    try:
        return msg.as_bytes(policy=policy.SMTP)
    except Exception as e:
        logger.warning("序列化规范化邮件失败，保留原始字节: %s", e)
        return raw_bytes


def classify_folder_category(folder: str) -> str:
    """将 IMAP 文件夹路径映射到5个核心文件夹类别

    覆盖主流邮箱的文件夹路径（含网易 Modified UTF-7 编码）：
    - 网易: &XfJT0ZAB-(已发送) &g0l6P3ux-(草稿箱) &XfJT0ZCu-(垃圾邮件) &YkBnCZCu-(已删除)

    返回: inbox / sent / drafts / junk / trash / other
    """
    f = folder.lower()

    # 收件箱
    if f == 'inbox':
        return 'inbox'

    # 已发送（含网易 &XfJT0ZAB- 编码）
    if any(p in f for p in ['sent', '&xfjt0zab-', '[gmail]/sent', 'outbox']):
        return 'sent'

    # 草稿箱（含网易 &g0l6p3ux- 编码）
    if any(p in f for p in ['draft', '&g0l6p3ux-', '[gmail]/draft']):
        return 'drafts'

    # 垃圾邮件（含网易 &XfJT0ZCu- 编码）
    if any(p in f for p in ['junk', 'spam', '&xfjt0zcu-', '[gmail]/spam', 'bulk']):
        return 'junk'

    # 已删除（含网易 &YkBnCZCu- 编码）
    if any(p in f for p in ['trash', 'deleted', '&ykbnczcu-', '[gmail]/trash']):
        return 'trash'

    return 'other'


def build_eml_filename(uid: int, subject: str, date_str: str) -> str:
    """生成邮件 .eml 文件名

    格式: {YYYY-MM-DD}_{主题前30字}_{uid}.eml
    示例: 2026-07-13_项目周报_12345.eml

    日期解析失败时使用 unknown-date，主题为空时使用 untitled。
    """
    # 解析日期头（RFC 2822 格式 → YYYY-MM-DD）
    try:
        dt = parsedate_to_datetime(date_str)
        date_prefix = dt.strftime('%Y-%m-%d')
    except Exception:
        date_prefix = 'unknown-date'

    # 清洗主题
    safe_subject = sanitize_filename(subject, 30)

    return f"{date_prefix}_{safe_subject}_{uid}.eml"


def build_eml_path(backup_root: Path, email_addr: str, folder: str, filename: str) -> Path:
    """构建 .eml 文件的存储路径

    目录结构: backup_root/{邮箱地址}/{文件夹中文名}/{filename}
    示例: /授权目录/zhangsan@qq.com/收件箱/2026-07-13_项目周报_12345.eml
    """
    safe_email = sanitize_filename(email_addr, 100)
    folder_name = folder_display_name(folder)
    return backup_root / safe_email / folder_name / filename


async def get_available_backup_dirs(user_uid: str) -> list[dict]:
    """获取可用的备份目录列表（供前端选择）

    数据源：飞牛授权目录（优先读 accessible_paths.env 落盘文件，兜底读环境变量）
    无授权目录时返回空列表，前端应提示用户先在飞牛应用设置中授权目录。
    """
    dirs: list[dict] = []
    accessible = get_accessible_paths()

    for p in accessible:
        try:
            exists = os.path.isdir(p)
            writable = exists and os.access(p, os.W_OK)
            dirs.append({
                "path": p,
                "label": f"授权目录: {os.path.basename(p)}",
                "writable": writable,
                "exists": exists,
            })
        except Exception:
            continue

    return dirs


# ==================== 归档条件判断 ====================

async def should_archive(user_uid: str, account_id: str) -> bool:
    """判断是否应该归档该账号的邮件

    条件：
    1. 用户开启了备份总开关
    2. 该账号在备份邮箱列表中
    3. 备份目录可用（飞牛授权目录存在且可写）
    """
    # 1. 检查总开关
    enabled = await get_user_setting(user_uid, "backup_enabled", False)
    if not enabled:
        return False

    # 2. 检查账号是否在备份列表
    account_ids = await get_user_setting(user_uid, "backup_account_ids", [])
    if account_id not in account_ids:
        return False

    # 3. 检查备份目录可用（无授权目录时返回 None，禁止备份）
    backup_root = await get_backup_root_async(user_uid)
    if backup_root is None:
        logger.warning("无飞牛授权目录，跳过归档: user_uid=%s", user_uid)
        return False
    try:
        backup_root.mkdir(parents=True, exist_ok=True)
        return os.access(backup_root, os.W_OK)
    except Exception:
        return False


async def mark_archived_as_deleted(account_id: str, folder: str, uids: list[int]) -> int:
    """标记归档邮件为"服务器已删除"（保留 .eml 文件）

    在 purge_deleted_from_cache 之前调用，保留已删除邮件的本地备份。
    """
    from db import mark_archive_deleted
    return await mark_archive_deleted(account_id, folder, uids)


# ==================== 归档核心逻辑 ====================

def _has_attachments(msg) -> bool:
    """检查邮件是否包含附件（非内嵌图片的 part）"""
    if not msg.is_multipart():
        return False
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type.startswith("multipart/"):
            continue
        if content_type.startswith("image/"):
            # 内嵌图片（有 Content-ID）不算附件
            if part.get("Content-ID"):
                continue
        # 有 filename 或 Content-Disposition: attachment 的算附件
        if part.get_filename() or part.get_content_disposition() == "attachment":
            return True
    return False


async def _archive_one_email(
    account: Account,
    folder: str,
    uid: int,
    raw_email: bytes,
    backup_root: Path,
) -> bool:
    """归档单封邮件的公共逻辑（解析 + 规范化 + 写入文件 + 写入 DB）

    被 archive_message / archive_messages_batch / archive_folder 三个入口复用，
    消除重复代码。统一处理：
    - 解析邮件头（基于规范化后的 msg，保证 DB 记录与 .eml 文件一致）
    - 规范化 .eml 内容（补全必需头 + 统一 base64）
    - 写入 .eml 文件
    - 写入 message_archive 表（archived_at 由 upsert_message_archive 内部生成）

    返回 True 表示归档成功，False 表示失败。
    """
    try:
        # 1. 规范化邮件内容（补全必需头 + 统一 base64 + 标准 MIME 格式）
        normalized_email = normalize_eml(raw_email)
        # 2. 基于规范化后的字节解析邮件头，保证 DB 记录与 .eml 文件内容一致
        #    （如原始邮件缺 Message-ID，normalize_eml 会补全，此处取补全后的值）
        msg = message_from_bytes(normalized_email)
        subject = BaseIMAPReceiver._decode_header(msg.get("Subject", ""))
        date_str = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")

        # 3. 生成 .eml 文件路径并写入
        filename = build_eml_filename(uid, subject, date_str)
        eml_path = build_eml_path(backup_root, account.email, folder, filename)
        eml_path.parent.mkdir(parents=True, exist_ok=True)
        eml_path.write_bytes(normalized_email)

        # 4. 写入归档数据库（archived_at 由 upsert_message_archive 内部 now 生成，无需传入）
        archive_data = {
            "user_uid": account.user_uid,
            "account_id": account.id,
            "folder": folder,
            "uid": uid,
            "message_id": message_id,
            "subject": subject,
            "from_addr": BaseIMAPReceiver._decode_header(msg.get("From", "")),
            "to_addr": BaseIMAPReceiver._decode_header(msg.get("To", "")),
            "cc": BaseIMAPReceiver._decode_header(msg.get("Cc", "")),
            "date": normalize_date_for_sort(date_str),
            "size": len(normalized_email),
            "eml_path": str(eml_path.relative_to(backup_root)),
            "flags": "",
            "has_attachments": 1 if _has_attachments(msg) else 0,
            "is_deleted_on_server": 0,
        }
        await upsert_message_archive(archive_data)
        return True
    except Exception as e:
        logger.warning("归档单封失败: %s/%s uid=%d, %s", account.email, folder, uid, e)
        return False


async def archive_message(account: Account, folder: str, uid: int) -> bool:
    """归档单封邮件（由同步管道调用）

    步骤:
    1. 获取备份根目录 + 检查是否已归档（DB 有记录且本地文件存在则跳过）
    2. 建立独立 IMAP 连接，FETCH BODY.PEEK[] 获取完整 MIME 源码
    3. 调用公共函数 _archive_one_email 完成解析+规范化+写入+入库

    返回 True 表示归档成功（新建），False 表示已存在或失败
    """
    # 1. 检查是否已归档 + 本地文件是否存在
    # 数据库有记录但文件丢失时，仍需重新归档（避免文件永久缺失）
    backup_root = await get_backup_root_async(account.user_uid)
    if backup_root is None:
        logger.warning("归档失败: 无飞牛授权目录 %s/%s uid=%d", account.email, folder, uid)
        return False
    archived_map = await get_archived_uids(account.id, folder)
    if uid in archived_map:
        rel_path = archived_map[uid]
        eml_abs = (backup_root / rel_path) if rel_path else None
        if eml_abs and eml_abs.exists():
            return False  # 数据库 + 文件都在，真正跳过
        # 文件丢失：继续走归档流程，覆盖写入
        logger.warning("归档文件丢失，将重新生成: %s/%s uid=%d", account.email, folder, uid)

    # 2. 建立独立 IMAP 连接获取邮件源码
    # 注意：不复用 IDLE/Poll 监听连接，避免打断监听
    receiver = None
    try:
        from services.token import ensure_token
        credentials = await ensure_token(account)
        receiver = ProviderFactory.get_receiver(account.provider)
        await receiver.connect(credentials)

        raw_email = await receiver.fetch_raw_email(folder, uid)
        if not raw_email:
            logger.warning("归档失败: 无法获取邮件源码 uid=%s folder=%s", uid, folder)
            return False

        # 3. 调用公共函数完成解析+规范化+写入+入库
        ok = await _archive_one_email(account, folder, uid, raw_email, backup_root)
        if ok:
            logger.info("归档成功: %s/%s uid=%d", account.email, folder, uid)
        return ok

    except Exception as e:
        logger.error("归档失败: %s/%s uid=%d, %s", account.email, folder, uid, e)
        return False
    finally:
        if receiver:
            try:
                await receiver.disconnect()
            except Exception:
                pass


async def archive_messages_batch(account: Account, folder: str, uids: list[int]) -> int:
    """批量归档多封邮件（由同步管道调用，复用一个 IMAP 连接）

    与 archive_message 不同，此函数只建立一次 IMAP 连接，逐封 FETCH 归档。
    适用于同步管道发现新邮件时触发，避免每封邮件创建一个连接导致 IMAP 服务器拒绝。

    返回成功归档的数量
    """
    if not uids:
        return 0

    # 过滤掉"已归档且本地文件存在"的 UID（文件丢失的需重新归档）
    backup_root = await get_backup_root_async(account.user_uid)
    if backup_root is None:
        logger.warning("批量归档失败: 无飞牛授权目录 %s/%s", account.email, folder)
        return 0
    archived_map = await get_archived_uids(account.id, folder)
    to_archive: list[int] = []
    for uid in uids:
        if uid not in archived_map:
            to_archive.append(uid)  # 数据库无记录
            continue
        # 数据库有记录：校验本地文件是否真实存在
        rel_path = archived_map[uid]
        eml_abs = (backup_root / rel_path) if rel_path else None
        if eml_abs and eml_abs.exists():
            continue  # 数据库 + 文件都在，跳过
        to_archive.append(uid)  # 文件丢失，重新归档
        logger.warning("批量归档: 文件丢失将重新生成 %s/%s uid=%d", account.email, folder, uid)
    if not to_archive:
        return 0

    # 建立一个 IMAP 连接，归档所有新邮件
    receiver = None
    archived_count = 0
    try:
        from services.token import ensure_token
        credentials = await ensure_token(account)
        receiver = ProviderFactory.get_receiver(account.provider)
        await receiver.connect(credentials)

        for uid in to_archive:
            raw_email = await receiver.fetch_raw_email(folder, uid)
            if not raw_email:
                logger.warning("批量归档: 无法获取邮件源码 uid=%s folder=%s", uid, folder)
                continue
            # 调用公共函数完成解析+规范化+写入+入库
            if await _archive_one_email(account, folder, uid, raw_email, backup_root):
                archived_count += 1

        if archived_count > 0:
            logger.info("批量归档完成: %s/%s, 成功 %d/%d 封",
                       account.email, folder, archived_count, len(to_archive))

    except Exception as e:
        logger.error("批量归档失败: %s/%s, %s", account.email, folder, e)
    finally:
        if receiver:
            try:
                await receiver.disconnect()
            except Exception:
                pass

    return archived_count


async def archive_folder(account: Account, folder: str, max_count: int = 0) -> int:
    """归档整个文件夹（手动触发或全量备份）

    max_count=0 表示归档所有未归档的邮件
    返回新增归档数量
    """
    receiver = None
    try:
        from services.token import ensure_token
        credentials = await ensure_token(account)
        receiver = ProviderFactory.get_receiver(account.provider)
        await receiver.connect(credentials)

        # 1. 获取 IMAP 全量 UID
        all_uids = await receiver.fetch_new_message_uids(folder, since_uid=0)
        if not all_uids:
            logger.info("文件夹为空，无需归档: %s/%s", account.email, folder)
            return 0

        # 2. 获取已归档 UID 及其 eml_path，校验本地文件存在性
        # 数据库有记录但文件丢失的 UID 也要重新归档
        backup_root = await get_backup_root_async(account.user_uid)
        if backup_root is None:
            logger.warning("归档文件夹失败: 无飞牛授权目录 %s/%s", account.email, folder)
            return 0
        archived_map = await get_archived_uids(account.id, folder)

        # 3. 计算待归档列表：DB 无记录 或 DB 有记录但文件不存在的
        to_archive: list[int] = []
        for uid in all_uids:
            if uid not in archived_map:
                to_archive.append(uid)
                continue
            rel_path = archived_map[uid]
            eml_abs = (backup_root / rel_path) if rel_path else None
            if not (eml_abs and eml_abs.exists()):
                to_archive.append(uid)  # 文件丢失，重新归档
                logger.warning("归档文件夹: 文件丢失将重新生成 %s/%s uid=%d", account.email, folder, uid)
        if max_count > 0:
            to_archive = to_archive[:max_count]

        if not to_archive:
            logger.info("文件夹已全部归档: %s/%s", account.email, folder)
            return 0

        logger.info("开始归档文件夹: %s/%s, 待归档 %d 封", account.email, folder, len(to_archive))

        # 4. 逐封归档（顺序执行，避免 IMAP 并发压力）
        archived_count = 0
        for uid in to_archive:
            raw_email = await receiver.fetch_raw_email(folder, uid)
            if not raw_email:
                continue
            # 调用公共函数完成解析+规范化+写入+入库
            if await _archive_one_email(account, folder, uid, raw_email, backup_root):
                archived_count += 1

        logger.info("文件夹归档完成: %s/%s, 新增 %d 封", account.email, folder, archived_count)
        return archived_count

    except Exception as e:
        logger.error("归档文件夹失败: %s/%s, %s", account.email, folder, e)
        return 0
    finally:
        if receiver:
            try:
                await receiver.disconnect()
            except Exception:
                pass


async def _archive_one_account(
    account: Account,
    backup_root: Path,
    user_uid: str,
    notify: bool,
) -> dict:
    """备份单个账号的所有文件夹（内部公共函数）

    供 archive_all_accounts 和 archive_single_account 复用，避免代码重复。
    返回 {folder: archived_count}
    """
    result: dict = {}

    try:
        # 获取该账号所有文件夹
        from services.token import ensure_token
        credentials = await ensure_token(account)
        receiver = ProviderFactory.get_receiver(account.provider)
        await receiver.connect(credentials)
        try:
            folders = await receiver.fetch_folders()
        finally:
            await receiver.disconnect()

        # 逐个文件夹归档
        folder_total = 0
        for f in folders:
            try:
                count = await archive_folder(account, f.path)
                result[f.path] = count
                folder_total += count
            except Exception as e:
                logger.error("归档文件夹失败: %s/%s, %s", account.email, f.path, e)
                result[f.path] = 0

        # 手动触发时，备份完成后发送通知
        if notify:
            from services.sync import sync_service
            await sync_service.notify_backup_result(
                user_uid=user_uid,
                account_id=account.id,
                provider=account.provider,
                email=account.email,
                success=True,
                archived_count=folder_total,
            )

    except Exception as e:
        logger.error("归档账号失败: %s, %s", account.email, e)
        if notify:
            from services.sync import sync_service
            await sync_service.notify_backup_result(
                user_uid=user_uid,
                account_id=account.id,
                provider=account.provider,
                email=account.email,
                success=False,
                error_msg=str(e),
            )

    return result


async def archive_all_accounts(user_uid: str, notify: bool = False) -> dict:
    """全量备份所有选中邮箱的所有文件夹

    Args:
        user_uid: 用户UID
        notify: 是否在备份完成后发送通知（仅手动点击"立即备份"时为True）

    返回 {account_id: {folder: archived_count}}
    """
    result: dict = {}

    # 1. 检查备份开关
    enabled = await get_user_setting(user_uid, "backup_enabled", False)
    if not enabled:
        logger.warning("备份功能未开启，跳过全量备份")
        return result

    # 2. 获取选中的账号
    account_ids = await get_user_setting(user_uid, "backup_account_ids", [])
    if not account_ids:
        logger.warning("未选择备份邮箱，跳过全量备份")
        return result

    # 3. 逐个账号归档（调用公共函数）
    accounts = await get_accounts(user_uid)
    target_accounts = [a for a in accounts if a.id in account_ids]
    backup_root = await get_backup_root_async(user_uid)
    if backup_root is None:
        logger.error("全量备份失败: 无飞牛授权目录，请先在飞牛应用设置中授权目录")
        return result

    for account in target_accounts:
        result[account.id] = await _archive_one_account(
            account, backup_root, user_uid, notify
        )

    return result


async def archive_single_account(
    user_uid: str, account_id: str, notify: bool = False
) -> dict:
    """备份单个账号的所有文件夹（手动触发，仅备份指定账号）

    Args:
        user_uid: 用户UID
        account_id: 要备份的账号ID
        notify: 是否发送通知

    返回 {account_id: {folder: archived_count}}
    """
    result: dict = {}

    # 1. 检查备份开关
    enabled = await get_user_setting(user_uid, "backup_enabled", False)
    if not enabled:
        logger.warning("备份功能未开启，跳过备份")
        return result

    # 2. 查找指定账号
    accounts = await get_accounts(user_uid)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        logger.warning("账号不存在: %s", account_id)
        return result

    # 3. 备份该账号（调用公共函数）
    backup_root = await get_backup_root_async(user_uid)
    if backup_root is None:
        logger.error("备份失败: 无飞牛授权目录，请先在飞牛应用设置中授权目录")
        return result
    result[account.id] = await _archive_one_account(
        account, backup_root, user_uid, notify
    )

    return result


# ==================== .eml 解析（供备份页面查看） ====================

def parse_eml_to_message(
    raw_bytes: bytes,
    archive_meta: dict,
    is_read: bool = False,
    is_starred: bool = False,
    folder: str = "",
    account_id: str = "",
) -> dict:
    """解析 .eml 字节流为前端可展示的邮件详情

    复用 BaseIMAPReceiver 的静态解码方法，避免重复代码。
    part_index 按 walk() 顺序递增（与 base_imap._fetch_detail_sync 完全一致），
    保证附件的 part_number 与 IMAP 拉取一致，附件下载时可从 .eml 按 part_number 提取。

    Args:
        raw_bytes: .eml 文件的原始字节流
        archive_meta: message_archive 表的归档记录
        is_read: 是否已读（从 cached_messages 表补充）
        is_starred: 是否星标（从 cached_messages 表补充）
        folder: 邮件所在文件夹（从请求参数获取）
        account_id: 账号ID（从请求参数获取）
    """
    msg = message_from_bytes(raw_bytes)

    subject = BaseIMAPReceiver._decode_header(msg.get("Subject", ""))
    from_addr = BaseIMAPReceiver._decode_header(msg.get("From", ""))
    to_addr = BaseIMAPReceiver._decode_header(msg.get("To", ""))
    cc = BaseIMAPReceiver._decode_header(msg.get("Cc", ""))
    reply_to = BaseIMAPReceiver._decode_header(msg.get("Reply-To", ""))
    date_str = msg.get("Date", "")

    body_text = ""
    body_html = ""
    cid_map: dict[str, str] = {}
    attachments: list[dict] = []
    # part_index 对每个 walk() 元素递增（包括 multipart 容器和 text/plain、text/html），
    # 必须与 base_imap.py 的 _fetch_detail_sync 逻辑完全一致，保证附件下载 part_number 可靠
    part_index = 0

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body_text = BaseIMAPReceiver._decode_part(part)
            elif content_type == "text/html":
                body_html = BaseIMAPReceiver._decode_part(part)
            elif content_type.startswith("image/"):
                # 内嵌图片转为 base64 data URI
                content_id = part.get("Content-ID", "").strip("<>")
                if content_id:
                    img_data = part.get_payload(decode=True)
                    if img_data:
                        b64 = base64.b64encode(img_data).decode("ascii")
                        data_uri = f"data:{content_type};base64,{b64}"
                        cid_map[content_id] = data_uri
                # 同时记录为附件
                filename = part.get_filename() or ""
                if filename or not content_id:
                    img_data = part.get_payload(decode=True)
                    attachments.append({
                        "filename": BaseIMAPReceiver._decode_header(filename) if filename else "",
                        "content_type": content_type,
                        "size": len(img_data) if img_data else 0,
                        "part_number": part_index,
                        "is_inline": bool(content_id),
                    })
            elif not content_type.startswith("multipart/"):
                filename = part.get_filename() or ""
                payload = part.get_payload(decode=True)
                content_id = part.get("Content-ID", "").strip("<>")
                is_inline = bool(content_id) and part.get_content_disposition() != "attachment"
                if filename or payload:
                    attachments.append({
                        "filename": BaseIMAPReceiver._decode_header(filename) if filename else "",
                        "content_type": content_type,
                        "size": len(payload) if payload else 0,
                        "part_number": part_index,
                        "is_inline": is_inline,
                    })
            part_index += 1
    else:
        if msg.get_content_type() == "text/html":
            body_html = BaseIMAPReceiver._decode_part(msg)
        else:
            body_text = BaseIMAPReceiver._decode_part(msg)

    # 替换 body_html 中的 cid: 引用为 base64 data URI
    if body_html and cid_map:
        for cid, data_uri in cid_map.items():
            body_html = body_html.replace(f"cid:{cid}", data_uri)

    return {
        "id": str(archive_meta["uid"]),
        "uid": archive_meta["uid"],
        "subject": subject,
        "from_addr": from_addr,
        "to_addr": to_addr,
        "cc": cc,
        "reply_to": reply_to,
        # 日期统一为 UTC ISO 格式（与 IMAP _parse_date 一致），前端 new Date() 自动转本地时区
        "date": BaseIMAPReceiver._parse_date(date_str),
        "is_read": is_read,
        "is_starred": is_starred,
        "folder": folder,
        "account_id": account_id,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
        "has_attachments": len(attachments) > 0,
        "is_deleted_on_server": archive_meta.get("is_deleted_on_server", 0),
        "archived_at": archive_meta.get("archived_at", 0),
        "size": archive_meta.get("size", 0),
    }


def extract_attachment_from_eml(raw_bytes: bytes, part_number: int) -> tuple[bytes, str, str] | None:
    """从 .eml 字节流中提取指定 part_number 的附件

    part_number 的分配逻辑与 parse_eml_to_message 和 base_imap._fetch_detail_sync 完全一致：
    对每个 walk() 元素递增 part_index（包括 multipart 容器和 text/plain、text/html），
    只有非 multipart 的叶子节点才可能包含附件数据。

    Args:
        raw_bytes: .eml 文件的原始字节流
        part_number: 附件的 part 编号（与 parse_eml_to_message 返回的 part_number 一致）

    Returns:
        (附件二进制数据, content_type, filename) 或 None（未找到指定 part_number）
    """
    msg = message_from_bytes(raw_bytes)
    part_index = 0

    if not msg.is_multipart():
        return None

    for part in msg.walk():
        content_type = part.get_content_type()
        if not content_type.startswith("multipart/"):
            if part_index == part_number:
                payload = part.get_payload(decode=True)
                if payload is not None:
                    filename = part.get_filename() or ""
                    return (payload, content_type, filename)
                return None
        # part_index 对每个 walk() 元素递增（与 parse_eml_to_message 一致）
        part_index += 1

    return None
