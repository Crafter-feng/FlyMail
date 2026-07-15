import asyncio
import os
import json
import time
import aiosqlite
from typing import Any, List, Optional
from models import Account, CachedMessage, Notification, Signature
from utils.logger import get_logger

logger = get_logger("db")

DB_PATH = os.environ.get("FLYMAIL_DATA_DIR", ".") + "/flymail.db"

# 全局单例数据库连接，避免每次操作都新建连接（连接创建开销大，且每次设置 WAL 是冗余操作）
_db_instance: Optional[aiosqlite.Connection] = None
# 保护单例创建的锁，防止并发 get_db() 创建多个连接
_db_lock = asyncio.Lock()


def make_cached_message_id(account_id: str, folder: str, uid: int | str) -> str:
    """Build a cache primary key. IMAP UIDs are unique per folder, not per account."""
    return f"{account_id}:{folder}:{uid}"


async def get_db() -> aiosqlite.Connection:
    """获取全局单例数据库连接

    使用单例模式复用连接，WAL 模式只在首次连接时设置一次。
    如果旧代码误关了连接，这里会自动重建，避免出现 no active connection。

    修复 P3：用 asyncio.Lock 保护创建逻辑，防止并发 get_db() 创建多个连接导致旧连接泄漏。
    """
    global _db_instance
    # 快速路径：连接已存在直接返回（无锁，性能优先）
    if _db_instance is not None and getattr(_db_instance, "_connection", None) is not None:
        return _db_instance
    # 慢速路径：需要创建连接，加锁防止并发创建
    async with _db_lock:
        # 双重检查：可能在等锁期间已被其他协程创建
        if _db_instance is None or getattr(_db_instance, "_connection", None) is None:
            _db_instance = await aiosqlite.connect(DB_PATH)
            await _db_instance.execute("PRAGMA journal_mode=WAL")
            # 设置行工厂，让 fetchall 返回的行支持按列名访问
            _db_instance.row_factory = aiosqlite.Row
    return _db_instance


async def init_db():
    """初始化数据库：创建所有表和索引

    表结构:
      - accounts: 邮箱账号（provider/credentials/连接状态等）
      - folder_stats: 文件夹统计（邮件数/未读数/同步时间）
      - cached_messages: 邮件摘要缓存（主题/发件人/时间/已读等）
      - notifications: 新邮件通知记录

    迁移策略: 使用 try-except 逐表创建，已存在的表会跳过
    """
    db = await get_db()
    await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                user_uid TEXT NOT NULL,
                email TEXT NOT NULL,
                provider TEXT NOT NULL,
                credentials_json TEXT DEFAULT '',
                status TEXT DEFAULT 'disconnected',
                remark TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                hide_email INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            )
        """)
    await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_messages (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                user_uid TEXT NOT NULL,
                uid INTEGER NOT NULL,
                folder TEXT NOT NULL,
                subject TEXT DEFAULT '',
                from_addr TEXT DEFAULT '',
                to_addr TEXT DEFAULT '',
                date TEXT DEFAULT '',
                is_read INTEGER DEFAULT 0,
                is_starred INTEGER DEFAULT 0,
                body_text TEXT DEFAULT '',
                body_html TEXT DEFAULT '',
                cached_at REAL DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON cached_messages(user_uid)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_folder ON cached_messages(folder)")
    # 新增索引：按账号+文件夹查询缓存（列表接口核心查询）
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_account_folder ON cached_messages(account_id, folder)")
    # 新增索引：按账号+文件夹+UID查询，用于增量同步时获取最大UID
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_uid ON cached_messages(account_id, folder, uid)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_unified ON cached_messages(user_uid, folder, account_id)")
    # 修复 Q5：新增索引：按账号+文件夹+已读状态查询，用于未读计数和筛选
    await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_read ON cached_messages(account_id, folder, is_read)")
    # 修复 Q5：新增索引：accounts 表按 user_uid 查询（get_accounts 核心查询，几乎所有API都调用）
    await db.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_uid)")

    # 通知表：持久化新邮件通知记录
    await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_uid TEXT NOT NULL,
                account_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                email TEXT NOT NULL,
                folder TEXT DEFAULT 'INBOX',
                is_read INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0
            )
        """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_uid)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_uid, is_read)")

    # 文件夹统计表：存储 IMAP 返回的真实邮件总数和未读数
    # 解决缓存只存部分邮件时 COUNT(*) 不等于 IMAP 真实总数的问题
    await db.execute("""
            CREATE TABLE IF NOT EXISTS folder_stats (
                account_id TEXT NOT NULL,
                folder TEXT NOT NULL,
                total_count INTEGER DEFAULT 0,
                unread_count INTEGER DEFAULT 0,
                updated_at REAL DEFAULT 0,
                PRIMARY KEY (account_id, folder)
            )
        """)

    # 签名模板表：支持多签名模板管理（替代原来 settings.json 中的单一签名）
    await db.execute("""
            CREATE TABLE IF NOT EXISTS signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content_html TEXT DEFAULT '',
                is_default INTEGER DEFAULT 0,
                account_id TEXT DEFAULT '',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            )
        """)

    # 修复 D1：用户级配置表，按 user_uid 隔离（unified_account_ids/signature_html/signature_enabled）
    # 替代原来全局 settings.json 中混存的用户级配置，避免多用户互相覆盖
    await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_uid TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT DEFAULT '',
                updated_at REAL DEFAULT 0,
                PRIMARY KEY (user_uid, key)
            )
        """)

    # 数据库迁移：为已有数据库补充新列（SQLite 不支持 IF NOT EXISTS 加列，需要 try-except）
    try:
        await db.execute("ALTER TABLE accounts ADD COLUMN hide_email INTEGER DEFAULT 0")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 accounts.hide_email: %s", e)

    try:
        await db.execute("ALTER TABLE cached_messages ADD COLUMN has_attachments INTEGER DEFAULT 0")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 cached_messages.has_attachments: %s", e)

    # 通知表新增 type 和 message 字段（兼容旧数据）
    try:
        await db.execute("ALTER TABLE notifications ADD COLUMN type TEXT DEFAULT 'new_mail'")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 notifications.type: %s", e)
    try:
        await db.execute("ALTER TABLE notifications ADD COLUMN message TEXT DEFAULT ''")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 notifications.message: %s", e)

    # 安全修复 S3：signatures 表添加 user_uid 字段，支持多用户隔离
    try:
        await db.execute("ALTER TABLE signatures ADD COLUMN user_uid TEXT DEFAULT ''")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 signatures.user_uid: %s", e)

    # accounts 表添加 sort_order 字段，支持手动拖拽排序
    try:
        await db.execute("ALTER TABLE accounts ADD COLUMN sort_order INTEGER DEFAULT 0")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 accounts.sort_order: %s", e)

    # cached_messages 表添加 cc 字段，存储抄送人（回复时填充抄送列表用）
    try:
        await db.execute("ALTER TABLE cached_messages ADD COLUMN cc TEXT DEFAULT ''")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 cached_messages.cc: %s", e)

    # 数据迁移：将 message_archive 表的 date 字段从 RFC 2822 格式转为 ISO 格式
    # RFC 2822（如 'Fri, 11 Jul 2026 02:17:55 +0000'）无法被 SQLite 字符串排序正确处理
    # ISO 格式（如 '2026-07-11 02:17:55'）字符串排序等价于时间排序
    try:
        from services.backup import normalize_date_for_sort
        cursor = await db.execute(
            "SELECT id, date FROM message_archive WHERE date LIKE '%,%' OR date LIKE '%+%'"
        )
        rows = await cursor.fetchall()
        migrated = 0
        for row in rows:
            new_date = normalize_date_for_sort(row[1])
            if new_date and new_date != row[1]:
                await db.execute("UPDATE message_archive SET date = ? WHERE id = ?", (new_date, row[0]))
                migrated += 1
        if migrated > 0:
            await db.commit()
            logger.info("归档日期迁移完成: %d 条记录转为 ISO 格式", migrated)
    except Exception as e:
        logger.debug("归档日期迁移失败（不影响启动）: %s", e)

    # 联系人表：存储联系人基本信息（不含邮箱，邮箱在 contact_emails 子表）
    # CREATE IF NOT EXISTS 保证不丢数据；ALTER TABLE 补列保证字段完整
    await db.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_uid TEXT NOT NULL,
                name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                company TEXT DEFAULT '',
                remark TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            )
        """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_uid)")

    # 联系人邮箱子表：一个联系人可关联多个邮箱
    await db.execute("""
            CREATE TABLE IF NOT EXISTS contact_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                is_primary INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
                UNIQUE(contact_id, email)
            )
        """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_contact_emails_contact ON contact_emails(contact_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_contact_emails_email ON contact_emails(email)")

    # 补充 company 字段（旧表无此列时自动添加，已有则忽略）
    try:
        await db.execute("ALTER TABLE contacts ADD COLUMN company TEXT DEFAULT ''")
    except Exception as e:
        logger.debug("迁移加列已存在，忽略 contacts.company: %s", e)

    # 邮件归档表：存储备份元数据，与 cached_messages 完全独立，持久保留
    # 即使服务器删除邮件，本表记录和对应 .eml 文件也保留
    await db.execute("""
        CREATE TABLE IF NOT EXISTS message_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_uid TEXT NOT NULL,
            account_id TEXT NOT NULL,
            folder TEXT NOT NULL,
            uid INTEGER NOT NULL,
            message_id TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            from_addr TEXT DEFAULT '',
            to_addr TEXT DEFAULT '',
            cc TEXT DEFAULT '',
            date TEXT DEFAULT '',
            size INTEGER DEFAULT 0,
            eml_path TEXT NOT NULL,
            flags TEXT DEFAULT '',
            has_attachments INTEGER DEFAULT 0,
            archived_at REAL DEFAULT 0,
            is_deleted_on_server INTEGER DEFAULT 0,
            deleted_at REAL DEFAULT 0,
            UNIQUE(account_id, folder, uid)
        )
    """)
    # 索引加速常用查询：按用户查、按账号+文件夹查、按日期排序、按删除状态筛选
    await db.execute("CREATE INDEX IF NOT EXISTS idx_archive_user ON message_archive(user_uid)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_archive_account_folder ON message_archive(account_id, folder)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_archive_date ON message_archive(date)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_archive_deleted ON message_archive(user_uid, is_deleted_on_server)")

    await db.commit()

async def get_accounts(user_uid: str) -> List[Account]:
    """获取账号列表。user_uid 为空字符串时返回所有用户的账号。按 sort_order 排序。"""
    db = await get_db()
    if user_uid:
        cursor = await db.execute(
            "SELECT * FROM accounts WHERE user_uid = ? ORDER BY sort_order, created_at", (user_uid,)
        )
    else:
        cursor = await db.execute("SELECT * FROM accounts ORDER BY sort_order, created_at")
    rows = await cursor.fetchall()
    # 获取列名
    columns = [description[0] for description in cursor.description]
    return [Account(**dict(zip(columns, row))) for row in rows]


async def get_account_by_id(account_id: str) -> Account | None:
    """按主键直接查询单个账号。

    O4 修复：token 刷新锁内 double-check 使用此函数，避免查询所有用户账号
    （原 get_accounts("") 会加载所有用户的 email 和 credentials_json 到内存，
    存在性能和隐私问题）。
    """
    db = await get_db()
    cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    columns = [description[0] for description in cursor.description]
    return Account(**dict(zip(columns, row)))


async def create_account(account: Account) -> Account:
    """创建邮箱账号记录，返回新账号的 id"""
    db = await get_db()
    await db.execute(
        """INSERT INTO accounts
           (id, user_uid, email, provider, credentials_json, status,
            remark, group_name, hide_email, created_at, updated_at, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (account.id, account.user_uid, account.email, account.provider,
         account.credentials_json, account.status,
         account.remark, account.group_name,
         1 if account.hide_email else 0,
         account.created_at, account.updated_at, account.sort_order)
    )
    await db.commit()
    return account


async def update_account_sort_orders(sort_orders: list[dict]) -> None:
    """批量更新账号排序。sort_orders 格式: [{"id": "xxx", "sort_order": 0}, ...]"""
    db = await get_db()
    for item in sort_orders:
        await db.execute(
            "UPDATE accounts SET sort_order = ? WHERE id = ?",
            (item["sort_order"], item["id"])
        )
    await db.commit()


async def delete_account(account_id: str, user_uid: str) -> bool:
    """删除账号记录

    注意：cached_messages 由 main.py 的 remove_account 接口显式调用
    delete_cached_messages_by_account 删除，此处不再重复删除。
    """
    db = await get_db()
    cursor = await db.execute("DELETE FROM accounts WHERE id = ? AND user_uid = ?", (account_id, user_uid))
    await db.commit()
    return cursor.rowcount > 0


async def update_account_credentials(account_id: str, credentials_json: str) -> bool:
    """更新账号的凭据信息（用于令牌刷新后持久化）"""
    db = await get_db()
    cursor = await db.execute(
        "UPDATE accounts SET credentials_json = ?, updated_at = ? WHERE id = ?",
        (credentials_json, time.time(), account_id)
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_account_info(account_id: str, user_uid: str, remark: str = "", group_name: str = "", hide_email: bool = False) -> bool:
    """更新账号的备注、分组和隐藏邮箱设置"""
    db = await get_db()
    cursor = await db.execute(
        "UPDATE accounts SET remark = ?, group_name = ?, hide_email = ?, updated_at = ? WHERE id = ? AND user_uid = ?",
        (remark, group_name, 1 if hide_email else 0, time.time(), account_id, user_uid)
    )
    await db.commit()
    return cursor.rowcount > 0


# ==================== 通知 CRUD ====================

async def create_notification(notification: Notification) -> Notification:
    """创建通知记录（新邮件、定时发送结果等）"""
    db = await get_db()
    await db.execute(
        "INSERT INTO notifications (id, user_uid, account_id, provider, email, folder, is_read, created_at, type, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (notification.id, notification.user_uid, notification.account_id,
         notification.provider, notification.email, notification.folder,
         1 if notification.is_read else 0, notification.created_at,
         notification.type, notification.message)
    )
    await db.commit()
    return notification


async def get_notifications(user_uid: str, limit: int = 50) -> List[Notification]:
    """获取用户的通知列表（按时间倒序，最多 limit 条）"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM notifications WHERE user_uid = ? ORDER BY created_at DESC LIMIT ?",
        (user_uid, limit)
    )
    rows = await cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    return [Notification(**dict(zip(columns, row))) for row in rows]


async def mark_notification_read(notification_id: str, user_uid: str) -> bool:
    """标记单条通知为已读"""
    db = await get_db()
    cursor = await db.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_uid = ?",
        (notification_id, user_uid)
    )
    await db.commit()
    return cursor.rowcount > 0


async def mark_all_notifications_read(user_uid: str) -> int:
    """标记用户所有通知为已读，返回更新的行数"""
    db = await get_db()
    cursor = await db.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_uid = ? AND is_read = 0",
        (user_uid,)
    )
    await db.commit()
    return cursor.rowcount


async def clear_notifications(user_uid: str) -> int:
    """清空用户所有通知，返回删除的行数"""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM notifications WHERE user_uid = ?",
        (user_uid,)
    )
    await db.commit()
    return cursor.rowcount


async def get_unread_notification_count(user_uid: str) -> int:
    """获取用户未读通知数量"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_uid = ? AND is_read = 0",
        (user_uid,)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


# ==================== 邮件缓存 CRUD ====================

async def upsert_cached_messages(messages: List[CachedMessage]) -> int:
    """批量写入/更新邮件缓存（UPSERT）

    使用 INSERT ... ON CONFLICT DO UPDATE 合并为单步操作：
    - 新记录：直接插入
    - 已存在记录：更新摘要字段，不覆盖已有正文（body_text/body_html 用 COALESCE 保留旧值）

    返回写入的记录数。
    """
    if not messages:
        return 0
    db = await get_db()
    rows = []
    id_updates = []
    id_cleanup = []
    for m in messages:
        cache_id = make_cached_message_id(m.account_id, m.folder, m.uid)
        rows.append(
            (cache_id, m.account_id, m.user_uid, m.uid, m.folder,
             m.subject, m.from_addr, m.to_addr, m.cc or "", m.date,
             1 if m.is_read else 0, 1 if m.is_starred else 0,
             1 if m.has_attachments else 0,
             m.body_text or None, m.body_html or None, m.cached_at)
        )
        id_updates.append((cache_id, m.account_id, m.folder, m.uid, cache_id))
        id_cleanup.append((m.account_id, m.folder, m.uid, cache_id))

    # Older cache rows used account_id + uid as the primary key. Normalize matching
    # rows first so cross-folder UIDs can coexist and existing bodies are preserved.
    await db.executemany(
        """UPDATE OR IGNORE cached_messages
           SET id = ?
           WHERE account_id = ? AND folder = ? AND uid = ? AND id <> ?""",
        id_updates,
    )
    await db.executemany(
        """INSERT INTO cached_messages
           (id, account_id, user_uid, uid, folder, subject, from_addr, to_addr, cc,
            date, is_read, is_starred, has_attachments, body_text, body_html, cached_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
            subject = excluded.subject,
            from_addr = excluded.from_addr,
            to_addr = excluded.to_addr,
            cc = excluded.cc,
            date = excluded.date,
            is_read = excluded.is_read,
            is_starred = excluded.is_starred,
            has_attachments = excluded.has_attachments,
            cached_at = excluded.cached_at,
            body_text = COALESCE(excluded.body_text, cached_messages.body_text),
            body_html = COALESCE(excluded.body_html, cached_messages.body_html)""",
        rows,
    )
    await db.executemany(
        """UPDATE cached_messages
           SET body_text = COALESCE(NULLIF(body_text, ''), (
                SELECT old.body_text
                FROM cached_messages old
                WHERE old.account_id = ?
                  AND old.folder = ?
                  AND old.uid = ?
                  AND old.id <> ?
                  AND old.body_text IS NOT NULL
                  AND old.body_text <> ''
                LIMIT 1
           )),
           body_html = COALESCE(NULLIF(body_html, ''), (
                SELECT old.body_html
                FROM cached_messages old
                WHERE old.account_id = ?
                  AND old.folder = ?
                  AND old.uid = ?
                  AND old.id <> ?
                  AND old.body_html IS NOT NULL
                  AND old.body_html <> ''
                LIMIT 1
           ))
           WHERE id = ?""",
        [
            (account_id, folder, uid, cache_id, account_id, folder, uid, cache_id, cache_id)
            for account_id, folder, uid, cache_id in id_cleanup
        ],
    )
    await db.executemany(
        """DELETE FROM cached_messages
           WHERE account_id = ? AND folder = ? AND uid = ? AND id <> ?""",
        id_cleanup,
    )
    await db.commit()
    return len(messages)


async def batch_update_is_read(account_id: str, folder: str, updates: List[tuple]) -> int:
    """批量更新邮件的 is_read 状态（只更新需要修正的记录）

    updates: [(uid, is_read), ...]  其中 is_read 为 0 或 1
    用于同步后批量校正 is_read，避免逐条 UPDATE 的性能问题。
    """
    if not updates:
        return 0
    db = await get_db()
    await db.executemany(
        "UPDATE cached_messages SET is_read = ? WHERE account_id = ? AND folder = ? AND uid = ?",
        [(v, account_id, folder, uid) for uid, v in updates]
    )
    await db.commit()
    return len(updates)


async def get_cached_unread_count(account_id: str, folder: str) -> int:
    """获取缓存中指定文件夹的未读邮件数量（轻量查询，用于判断是否需要校正 is_read）"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM cached_messages WHERE account_id = ? AND folder = ? AND is_read = 0",
        (account_id, folder)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_cached_is_read(account_id: str, uid: int, folder: str) -> bool:
    """查询缓存中单封邮件的 is_read 状态（轻量查询，不依赖正文）

    用于 fetch_message_detail 写入缓存时保留已有的 is_read，
    因为 get_cached_message_detail 在正文为空时返回 None，无法获取 is_read。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT is_read FROM cached_messages WHERE account_id = ? AND folder = ? AND uid = ?",
        (account_id, folder, uid),
    )
    row = await cursor.fetchone()
    return bool(row[0]) if row else False


async def get_cached_messages_by_folder(
    user_uid: str, account_id: str, folder: str,
    page: int = 1, page_size: int = 40,
    read_filter: str = "", attachment_filter: bool = False,
) -> dict:
    """从缓存分页读取邮件列表（按邮件时间倒序，时间相同时按 UID 倒序）

    返回格式与 list_messages API 一致：{messages, total, page, page_size, unread_total}
    total 和 unread_total 优先从 folder_stats 读取（IMAP 真实总数），
    如果 folder_stats 无记录则回退到 COUNT(*)（兼容旧数据）。

    参数：
        read_filter: "unread"=仅未读, "read"=仅已读, 空=全部
        attachment_filter: True=仅有附件的邮件
    """
    db = await get_db()

    # 构建 WHERE 条件（筛选模式下直接从缓存 COUNT，不依赖 folder_stats）
    conditions = ["user_uid = ?", "account_id = ?", "folder = ?"]
    params: list = [user_uid, account_id, folder]

    if read_filter == "unread":
        conditions.append("is_read = 0")
    elif read_filter == "read":
        conditions.append("is_read = 1")

    if attachment_filter:
        conditions.append("has_attachments = 1")

    where_clause = " AND ".join(conditions)
    has_filter = read_filter or attachment_filter

    # 查询当前文件夹实际已缓存的邮件数量
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM cached_messages WHERE {where_clause}",
        params,
    )
    filtered_total = (await cursor.fetchone())[0]

    if has_filter:
        # 有筛选条件时，直接用筛选后的计数
        total = filtered_total
        unread_total = 0  # 筛选模式下不单独计算未读数
    else:
        # 无筛选时，优先从 folder_stats 获取 IMAP 真实总数
        stats = await get_folder_stats(account_id, folder)
        if stats["total_count"] > 0:
            total = stats["total_count"]
            unread_total = stats["unread_count"]
        else:
            total = filtered_total
            cursor = await db.execute(
                "SELECT COUNT(*) FROM cached_messages WHERE user_uid = ? AND account_id = ? AND folder = ? AND is_read = 0",
                (user_uid, account_id, folder),
            )
            unread_total = (await cursor.fetchone())[0]

    # 分页查询（按邮件时间倒序，时间相同时按 UID 倒序）
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"""SELECT id, uid, subject, from_addr, to_addr, date, is_read, is_starred, folder, has_attachments
           FROM cached_messages
           WHERE {where_clause}
           ORDER BY date DESC, uid DESC
           LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )
    rows = await cursor.fetchall()
    messages = [
        {
            "id": str(row[1]),  # 返回 str(uid)，与 IMAP 的 Message.id 格式一致
            "uid": row[1],
            "subject": row[2],
            "from_addr": row[3],
            "to_addr": row[4],
            "date": row[5],
            "is_read": bool(row[6]),
            "is_starred": bool(row[7]),
            "folder": row[8],
            "has_attachments": bool(row[9]),
        }
        for row in rows
    ]

    result = {
        "messages": messages,
        "total": total,
        "unread_total": unread_total,
        "page": page,
        "page_size": page_size,
    }
    # 无筛选时附加缓存统计（兼容旧逻辑）
    if not has_filter:
        stats = await get_folder_stats(account_id, folder)
        result["cached_count"] = filtered_total
        result["stats_updated_at"] = stats["updated_at"]
    return result


async def get_folder_filter_counts(user_uid: str, account_id: str, folder: str) -> dict:
    """获取单账号文件夹各筛选条件的计数

    all 和 unread 优先从 folder_stats 获取（IMAP真实值，与左侧边栏一致），
    read 和 attachments 从 cached_messages 统计（folder_stats 不跟踪这两个维度）。
    当 folder_stats 无记录时，回退到 cached_messages 的 COUNT。
    """
    # 从 folder_stats 获取 IMAP 真实总数和未读数
    stats = await get_folder_stats(account_id, folder)

    # 从缓存统计 read 和 attachments 计数
    db = await get_db()
    cursor = await db.execute(
        """SELECT
            SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read_count,
            SUM(CASE WHEN has_attachments = 1 THEN 1 ELSE 0 END) as attachment_count
           FROM cached_messages
           WHERE user_uid = ? AND account_id = ? AND folder = ?""",
        (user_uid, account_id, folder),
    )
    row = await cursor.fetchone()

    # all 和 unread 优先用 folder_stats（与左侧边栏数据源一致，避免缓存不完整导致数字不一致）
    if stats["total_count"] > 0:
        all_count = stats["total_count"]
        unread_count = stats["unread_count"]
    else:
        # folder_stats 无记录时回退到缓存 COUNT（兼容旧数据）
        cursor = await db.execute(
            """SELECT COUNT(*), SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END)
               FROM cached_messages
               WHERE user_uid = ? AND account_id = ? AND folder = ?""",
            (user_uid, account_id, folder),
        )
        fallback_row = await cursor.fetchone()
        all_count = fallback_row[0] if fallback_row else 0
        unread_count = fallback_row[1] if fallback_row else 0

    return {
        "all": all_count,
        "unread": unread_count,
        "read": row[0] if row and row[0] else 0,
        "attachments": row[1] if row and row[1] else 0,
    }


async def get_cached_message_detail(account_id: str, uid: int, folder: str) -> Optional[dict]:
    """从缓存获取单封邮件的完整详情（含正文）

    如果缓存中有 body_html 或 body_text，直接返回（毫秒级），
    避免每次查看邮件都去 IMAP 拉取（秒级）。
    返回 None 表示缓存中没有正文内容，需要从 IMAP 拉取。
    """
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, uid, subject, from_addr, to_addr, date, is_read, is_starred,
                  folder, body_text, body_html, has_attachments, cc
           FROM cached_messages
           WHERE account_id = ? AND folder = ? AND uid = ?""",
        (account_id, folder, uid),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    body_html = row[10] or ""
    body_text = row[9] or ""
    # 如果正文为空，说明列表同步时只存了摘要，需要从 IMAP 拉取
    if not body_html and not body_text:
        return None
    return {
        "id": str(row[1]),
        "uid": row[1],
        "subject": row[2],
        "from_addr": row[3],
        "to_addr": row[4],
        "date": row[5],
        "is_read": bool(row[6]),
        "is_starred": bool(row[7]),
        "folder": row[8],
        "body_text": body_text,
        "body_html": body_html,
        "has_attachments": bool(row[11]),
        "cc": row[12] or "",  # 抄送人（回复时填充抄送列表）
        "attachments": [],  # 缓存中不存附件列表，需要 IMAP 拉取时补充
    }


async def get_cached_message_flags(account_id: str, uid: int, folder: str) -> Optional[dict]:
    """获取邮件的已读/星标状态（不检查正文是否存在）

    与 get_cached_message_detail 不同，此函数即使 cached_messages 表中
    没有正文（body_html/body_text 为空）也会返回 is_read/is_starred，
    供从 .eml 备份读取详情时补充邮件状态。

    Returns:
        {"is_read": bool, "is_starred": bool} 或 None（记录不存在）
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT is_read, is_starred FROM cached_messages WHERE account_id = ? AND folder = ? AND uid = ?",
        (account_id, folder, uid),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {"is_read": bool(row[0]), "is_starred": bool(row[1])}


async def get_max_cached_uid(user_uid: str, account_id: str, folder: str) -> int:
    """获取文件夹中最大的已缓存 UID（用于增量同步起点）

    返回 0 表示该文件夹没有缓存（需要全量同步）。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT MAX(uid) FROM cached_messages WHERE user_uid = ? AND account_id = ? AND folder = ?",
        (user_uid, account_id, folder),
    )
    row = await cursor.fetchone()
    return row[0] if row and row[0] else 0


async def delete_cached_messages_by_account(account_id: str) -> int:
    """删除账号的所有邮件缓存（删除账号时调用）"""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM cached_messages WHERE account_id = ?",
        (account_id,)
    )
    await db.commit()
    return cursor.rowcount


async def purge_deleted_from_cache(account_id: str, folder: str, existing_uids: set) -> int:
    """清理缓存中已不在 IMAP 服务器上的邮件

    对比缓存中的 UID 和 IMAP 返回的 UID 列表，删除缓存中多余的邮件。
    返回删除的记录数。
    使用临时表避免将所有缓存 UID 加载到 Python 内存。
    """
    if not existing_uids:
        return 0
    db = await get_db()
    # 用临时表存储 IMAP 上存在的 UID，然后用 SQL 子查询删除过期缓存
    # 避免将所有缓存 UID 加载到 Python 内存（万封邮箱时节省大量内存）
    await db.execute("CREATE TEMP TABLE IF NOT EXISTS _tmp_existing_uids (uid INTEGER)")
    await db.execute("DELETE FROM _tmp_existing_uids")
    await db.executemany(
        "INSERT INTO _tmp_existing_uids (uid) VALUES (?)",
        [(uid,) for uid in existing_uids]
    )
    cursor = await db.execute(
        """DELETE FROM cached_messages
           WHERE account_id = ? AND folder = ?
           AND uid NOT IN (SELECT uid FROM _tmp_existing_uids)""",
        (account_id, folder),
    )
    await db.execute("DROP TABLE IF EXISTS _tmp_existing_uids")
    await db.commit()
    return cursor.rowcount


async def delete_cached_message(account_id: str, uid: int, folder: str) -> bool:
    """删除单封邮件缓存（删除/移动邮件后同步缓存）"""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM cached_messages WHERE account_id = ? AND uid = ? AND folder = ?",
        (account_id, uid, folder)
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_cached_message_read(account_id: str, uid: int, folder: str, is_read: bool) -> bool:
    """更新缓存中邮件的已读状态（标记已读后同步缓存）"""
    db = await get_db()
    cursor = await db.execute(
        "UPDATE cached_messages SET is_read = ? WHERE account_id = ? AND uid = ? AND folder = ?",
        (1 if is_read else 0, account_id, uid, folder)
    )
    await db.commit()
    return cursor.rowcount > 0


async def batch_delete_cached_messages(account_id: str, uids: list[int], folder: str) -> int:
    """批量删除缓存邮件（单次数据库操作，替代逐条删除的 N+1 问题）"""
    if not uids:
        return 0
    db = await get_db()
    placeholders = ",".join("?" * len(uids))
    cursor = await db.execute(
        f"DELETE FROM cached_messages WHERE account_id = ? AND folder = ? AND uid IN ({placeholders})",
        [account_id, folder] + uids
    )
    await db.commit()
    return cursor.rowcount


async def get_cached_count(account_id: str, folder: str) -> int:
    """获取指定文件夹的缓存邮件数量（用于删除后快速更新 folder_stats）"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM cached_messages WHERE account_id = ? AND folder = ?",
        (account_id, folder),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_cached_uids(account_id: str, folder: str) -> set:
    """获取指定文件夹缓存中所有邮件的 UID 集合（用于补全同步时对比差异）"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT uid FROM cached_messages WHERE account_id = ? AND folder = ?",
        (account_id, folder),
    )
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def batch_update_cached_messages_read(account_id: str, uids: list[int], folder: str, is_read: bool) -> int:
    """批量更新缓存邮件已读状态（单次数据库操作，替代逐条更新的 N+1 问题）"""
    if not uids:
        return 0
    db = await get_db()
    placeholders = ",".join("?" * len(uids))
    cursor = await db.execute(
        f"UPDATE cached_messages SET is_read = ? WHERE account_id = ? AND folder = ? AND uid IN ({placeholders})",
        [1 if is_read else 0, account_id, folder] + uids
    )
    await db.commit()
    return cursor.rowcount


async def mark_all_cached_messages_read(account_id: str, folder: str) -> int:
    """将该账号+文件夹下所有缓存邮件标记为已读（全量更新，不依赖 UID 列表）

    与 batch_update_cached_messages_read 的区别：
    - batch_update 按 UID 列表更新，只能更新 SEARCH UNSEEN 返回的
    - mark_all 直接 UPDATE 全表，确保数据库里不会有残留的未读标记
      （比如 IMAP 已读但数据库还标记为未读的脏数据）
    用于"一键全部已读"功能。
    """
    db = await get_db()
    cursor = await db.execute(
        "UPDATE cached_messages SET is_read = 1 WHERE account_id = ? AND folder = ?",
        (account_id, folder)
    )
    await db.commit()
    return cursor.rowcount


# ==================== 文件夹统计 CRUD ====================

async def upsert_folder_stats(account_id: str, folder: str, total_count: int, unread_count: int) -> None:
    """更新文件夹的邮件总数和未读数（IMAP 同步后调用）

    使用 INSERT OR REPLACE 确保始终保存最新的 IMAP 统计数据。
    """
    db = await get_db()
    await db.execute(
        """INSERT OR REPLACE INTO folder_stats (account_id, folder, total_count, unread_count, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (account_id, folder, total_count, unread_count, time.time())
    )
    await db.commit()


async def get_folder_stats(account_id: str, folder: str) -> dict:
    """获取文件夹的邮件统计（总数、未读数）

    返回 {"total_count": int, "unread_count": int, "updated_at": float}，无记录时 updated_at 为 0。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT total_count, unread_count, updated_at FROM folder_stats WHERE account_id = ? AND folder = ?",
        (account_id, folder),
    )
    row = await cursor.fetchone()
    if row:
        return {"total_count": row[0], "unread_count": row[1], "updated_at": row[2]}
    return {"total_count": 0, "unread_count": 0, "updated_at": 0}


async def delete_folder_stats_by_account(account_id: str) -> None:
    """删除账号的所有文件夹统计（删除账号时调用）"""
    db = await get_db()
    await db.execute("DELETE FROM folder_stats WHERE account_id = ?", (account_id,))
    await db.commit()


# ==================== 签名模板 CRUD ====================

async def get_signatures(user_uid: str = "") -> List[Signature]:
    """获取签名模板列表。user_uid 为空时返回所有（仅管理员场景用），否则按用户过滤。"""
    db = await get_db()
    if user_uid:
        cursor = await db.execute(
            "SELECT * FROM signatures WHERE user_uid = ? ORDER BY is_default DESC, id ASC",
            (user_uid,)
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM signatures ORDER BY is_default DESC, id ASC"
        )
    rows = await cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    return [Signature(**dict(zip(columns, row))) for row in rows]


async def get_signature_by_id(sig_id: int, user_uid: str = "") -> Optional[Signature]:
    """根据 ID 获取单个签名模板。传入 user_uid 时校验归属，不匹配返回 None。"""
    db = await get_db()
    if user_uid:
        cursor = await db.execute("SELECT * FROM signatures WHERE id = ? AND user_uid = ?", (sig_id, user_uid))
    else:
        cursor = await db.execute("SELECT * FROM signatures WHERE id = ?", (sig_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    columns = [description[0] for description in cursor.description]
    return Signature(**dict(zip(columns, row)))


async def create_signature(sig: Signature) -> Signature:
    """创建签名模板

    若 is_default=1，先将该用户的其他模板 is_default 设为 0（确保只有一个默认签名）。
    修复 D3：用显式事务包裹，确保清默认+插入的原子性。
    """
    db = await get_db()
    now = time.time()
    # 修复 D3：显式事务，防止清默认后插入失败导致所有默认签名丢失
    await db.execute("BEGIN")
    try:
        if sig.is_default:
            await db.execute("UPDATE signatures SET is_default = 0 WHERE user_uid = ?", (sig.user_uid or "",))
        cursor = await db.execute(
            """INSERT INTO signatures (name, content_html, is_default, account_id, user_uid, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sig.name, sig.content_html, 1 if sig.is_default else 0,
             sig.account_id or "", sig.user_uid or "", now, now)
        )
        await db.execute("COMMIT")
    except Exception:
        await db.execute("ROLLBACK")
        raise
    sig.id = cursor.lastrowid
    sig.created_at = now
    sig.updated_at = now
    return sig


async def update_signature(sig: Signature) -> bool:
    """更新签名模板

    若 is_default=1，先将该用户的其他模板 is_default 设为 0。
    返回是否更新成功。
    修复 D3：用显式事务包裹，确保清默认+更新的原子性。
    """
    db = await get_db()
    now = time.time()
    # 修复 D3：显式事务，防止清默认后更新失败导致所有默认签名丢失
    await db.execute("BEGIN")
    try:
        if sig.is_default:
            await db.execute("UPDATE signatures SET is_default = 0 WHERE user_uid = ?", (sig.user_uid or "",))
        cursor = await db.execute(
            """UPDATE signatures SET name = ?, content_html = ?, is_default = ?,
               account_id = ?, updated_at = ?
               WHERE id = ?""",
            (sig.name, sig.content_html, 1 if sig.is_default else 0,
             sig.account_id or "", now, sig.id)
        )
        await db.execute("COMMIT")
    except Exception:
        await db.execute("ROLLBACK")
        raise
    return cursor.rowcount > 0


async def delete_signature(sig_id: int, user_uid: str = "") -> bool:
    """删除签名模板，返回是否成功。传入 user_uid 时校验归属。"""
    db = await get_db()
    if user_uid:
        cursor = await db.execute("DELETE FROM signatures WHERE id = ? AND user_uid = ?", (sig_id, user_uid))
    else:
        cursor = await db.execute("DELETE FROM signatures WHERE id = ?", (sig_id,))
    await db.commit()
    return cursor.rowcount > 0


# ==================== 聚合收件箱查询 ====================

async def get_unified_inbox_messages(
    user_uid: str,
    account_ids: list,
    page: int = 1,
    page_size: int = 40,
    account_filter: str = "",
    read_filter: str = "",
    attachment_filter: bool = False,
) -> dict:
    """从缓存中聚合多个账号的收件箱邮件，按时间倒序排列

    复用 cached_messages 表中的缓存数据，不需要额外的缓存逻辑。
    现有缓存同步机制（IDLE监听、增量同步）已在维护 INBOX 的缓存数据。

    参数：
        user_uid: 飞牛OS用户ID
        account_ids: 要聚合的账号ID列表
        page: 页码（从1开始）
        page_size: 每页数量
        account_filter: 按账号ID进一步筛选，空=全部
        read_filter: "unread"=仅未读, "read"=仅已读, 空=全部
        attachment_filter: True=仅有附件的邮件
    """
    if not account_ids:
        return {"messages": [], "total": 0, "unread_total": 0, "page": page, "page_size": page_size}

    db = await get_db()
    # where_clause 通过字符串拼接构建，但 conditions 列表中的条件均为硬编码字符串（不接受用户输入），SQL 注入安全
    conditions = ["user_uid = ?", "folder = 'INBOX'"]
    params: list = [user_uid]

    # 限定聚合的账号范围
    placeholders = ",".join("?" * len(account_ids))
    conditions.append(f"account_id IN ({placeholders})")
    params.extend(account_ids)

    # 按账号进一步筛选
    if account_filter and account_filter in account_ids:
        conditions.append("account_id = ?")
        params.append(account_filter)

    # 按已读/未读筛选
    if read_filter == "unread":
        conditions.append("is_read = 0")
    elif read_filter == "read":
        conditions.append("is_read = 1")

    # 按附件筛选
    if attachment_filter:
        conditions.append("has_attachments = 1")

    where_clause = " AND ".join(conditions)

    # 合并 total 和 unread COUNT 为单次查询，减少一次全表扫描
    cursor = await db.execute(
        f"SELECT COUNT(*), SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) FROM cached_messages WHERE {where_clause}",
        params
    )
    row = await cursor.fetchone()
    total = row[0] or 0
    unread_total = row[1] or 0

    # 分页查询（按日期倒序，最新的在前）
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"""SELECT id, uid, subject, from_addr, to_addr, date, is_read, is_starred, folder, account_id, has_attachments
           FROM cached_messages
           WHERE {where_clause}
           ORDER BY date DESC
           LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )
    rows = await cursor.fetchall()
    messages = [
        {
            "id": str(row[1]),  # 返回 str(uid)
            "uid": row[1],
            "subject": row[2],
            "from_addr": row[3],
            "to_addr": row[4],
            "date": row[5],
            "is_read": bool(row[6]),
            "is_starred": bool(row[7]),
            "folder": row[8],
            "account_id": row[9],  # 聚合视图需要知道每封邮件的所属账号
            "has_attachments": bool(row[10]),
        }
        for row in rows
    ]

    return {
        "messages": messages,
        "total": total,
        "unread_total": unread_total,
        "page": page,
        "page_size": page_size,
    }


async def get_unified_inbox_filter_counts(user_uid: str, account_ids: list, account_filter: str = "") -> dict:
    """获取聚合收件箱各筛选条件的计数

    一次查询返回 all、unread、read、attachments 四个维度的计数，
    避免前端多次请求。
    """
    if not account_ids:
        return {"all": 0, "unread": 0, "read": 0, "attachments": 0}

    db = await get_db()
    placeholders = ",".join("?" * len(account_ids))
    conditions = [f"user_uid = ?", "folder = 'INBOX'", f"account_id IN ({placeholders})"]
    base_params = [user_uid] + account_ids

    # 按账号进一步筛选
    if account_filter and account_filter in account_ids:
        conditions.append("account_id = ?")
        base_params.append(account_filter)

    where_clause = " AND ".join(conditions)

    # 一次查询获取所有计数
    cursor = await db.execute(
        f"""SELECT
            COUNT(*) as all_count,
            SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread_count,
            SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read_count,
            SUM(CASE WHEN has_attachments = 1 THEN 1 ELSE 0 END) as attachment_count
           FROM cached_messages
           WHERE {where_clause}""",
        base_params,
    )
    row = await cursor.fetchone()
    return {
        "all": row[0] if row else 0,
        "unread": row[1] if row else 0,
        "read": row[2] if row else 0,
        "attachments": row[3] if row else 0,
    }


async def get_unified_inbox_stats(user_uid: str, account_ids: list) -> dict:
    """聚合指定账号 INBOX 的 total_count 和 unread_count

    从 folder_stats 表中汇总，比 COUNT(cached_messages) 更准确（因为缓存可能只存了部分邮件）。
    """
    if not account_ids:
        return {"total_count": 0, "unread_count": 0}

    db = await get_db()
    placeholders = ",".join("?" * len(account_ids))
    cursor = await db.execute(
        f"""SELECT COALESCE(SUM(total_count), 0), COALESCE(SUM(unread_count), 0)
           FROM folder_stats
           WHERE folder = 'INBOX' AND account_id IN ({placeholders})""",
        account_ids,
    )
    row = await cursor.fetchone()
    return {
        "total_count": row[0] if row else 0,
        "unread_count": row[1] if row else 0,
    }


# ==================== 用户级配置（D1 修复） ====================


async def get_user_setting(user_uid: str, key: str, default: Any = None) -> Any:
    """读取单个用户级配置项

    value 以 JSON 字符串存储，读取时还原为原始类型。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT value FROM user_settings WHERE user_uid = ? AND key = ?",
        (user_uid, key),
    )
    row = await cursor.fetchone()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return default


async def set_user_setting(user_uid: str, key: str, value: Any) -> None:
    """写入单个用户级配置项（upsert 语义）"""
    db = await get_db()
    value_json = json.dumps(value, ensure_ascii=False)
    await db.execute(
        """INSERT INTO user_settings (user_uid, key, value, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_uid, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (user_uid, key, value_json, time.time()),
    )
    await db.commit()


async def get_user_settings(user_uid: str, keys: Optional[List[str]] = None) -> dict:
    """批量读取用户级配置，返回 dict

    Args:
        user_uid: 用户 ID
        keys: 要读取的 key 列表，None 表示读取该用户全部配置
    """
    db = await get_db()
    if keys:
        placeholders = ",".join("?" * len(keys))
        cursor = await db.execute(
            f"SELECT key, value FROM user_settings WHERE user_uid = ? AND key IN ({placeholders})",
            [user_uid] + list(keys),
        )
    else:
        cursor = await db.execute(
            "SELECT key, value FROM user_settings WHERE user_uid = ?",
            (user_uid,),
        )
    rows = await cursor.fetchall()
    result = {}
    for row in rows:
        try:
            result[row[0]] = json.loads(row[1])
        except (json.JSONDecodeError, TypeError):
            logger.debug("用户配置解析失败 user_uid=%s key=%s", user_uid, row[0])
    return result


async def set_user_settings(user_uid: str, settings: dict) -> None:
    """批量写入用户级配置（upsert 语义）"""
    db = await get_db()
    now = time.time()
    for key, value in settings.items():
        value_json = json.dumps(value, ensure_ascii=False)
        await db.execute(
            """INSERT INTO user_settings (user_uid, key, value, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_uid, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (user_uid, key, value_json, now),
        )
    await db.commit()


# ==================== 联系人 CRUD ====================


async def _fetch_emails_for_contacts(db, contact_ids: list[int]) -> dict:
    """批量获取多个联系人的邮箱列表，返回 { contact_id: [{id, email, is_primary}] }"""
    if not contact_ids:
        return {}
    placeholders = ",".join("?" * len(contact_ids))
    cursor = await db.execute(
        f"SELECT id, contact_id, email, is_primary FROM contact_emails "
        f"WHERE contact_id IN ({placeholders}) ORDER BY is_primary DESC, id ASC",
        contact_ids,
    )
    rows = await cursor.fetchall()
    result: dict[int, list] = {}
    for row in rows:
        cid = row[1]
        if cid not in result:
            result[cid] = []
        result[cid].append({"id": row[0], "email": row[2], "is_primary": bool(row[3])})
    return result


async def get_contacts(user_uid: str, search: str = "") -> list:
    """获取联系人列表，支持按姓名/邮箱模糊搜索。每个联系人含 emails 数组。"""
    db = await get_db()
    if search:
        like = f"%{search}%"
        # JOIN contact_emails 匹配姓名或邮箱
        cursor = await db.execute(
            """SELECT DISTINCT c.* FROM contacts c
               LEFT JOIN contact_emails ce ON ce.contact_id = c.id
               WHERE c.user_uid = ? AND (c.name LIKE ? OR ce.email LIKE ?)
               ORDER BY c.name ASC, c.id ASC""",
            (user_uid, like, like),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM contacts WHERE user_uid = ? ORDER BY name ASC, id ASC",
            (user_uid,),
        )
    rows = await cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    contacts = [dict(zip(columns, row)) for row in rows]
    # 批量获取邮箱
    emails_map = await _fetch_emails_for_contacts(db, [c["id"] for c in contacts])
    for c in contacts:
        c["emails"] = emails_map.get(c["id"], [])
    return contacts


async def get_contact_by_id(contact_id: int, user_uid: str) -> Optional[dict]:
    """按 ID 获取单个联系人（含邮箱列表），传入 user_uid 校验归属。"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM contacts WHERE id = ? AND user_uid = ?",
        (contact_id, user_uid),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    columns = [d[0] for d in cursor.description]
    contact = dict(zip(columns, row))
    emails_map = await _fetch_emails_for_contacts(db, [contact_id])
    contact["emails"] = emails_map.get(contact_id, [])
    return contact


async def create_contact(user_uid: str, name: str, emails: list[str], phone: str = "", company: str = "", remark: str = "", group_name: str = "") -> dict:
    """新增联系人（含多个邮箱），返回完整记录。第一个邮箱标记为主邮箱。"""
    db = await get_db()
    now = time.time()
    cursor = await db.execute(
        """INSERT INTO contacts (user_uid, name, phone, company, remark, group_name, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_uid, name, phone, company, remark, group_name, now, now),
    )
    contact_id = cursor.lastrowid
    # 插入邮箱（去空、去重）
    email_list = []
    seen = set()
    for i, email in enumerate(emails):
        e = email.strip()
        if not e or e in seen:
            continue
        seen.add(e)
        is_primary = 1 if i == 0 else 0
        ec = await db.execute(
            "INSERT INTO contact_emails (contact_id, email, is_primary, created_at) VALUES (?, ?, ?, ?)",
            (contact_id, e, is_primary, now),
        )
        email_list.append({"id": ec.lastrowid, "email": e, "is_primary": bool(is_primary)})
    await db.commit()
    return {"id": contact_id, "user_uid": user_uid, "name": name, "phone": phone,
            "company": company, "remark": remark, "group_name": group_name,
            "created_at": now, "updated_at": now, "emails": email_list}


async def update_contact(contact_id: int, user_uid: str, name: str, emails: list[str], phone: str = "", company: str = "", remark: str = "", group_name: str = "") -> bool:
    """更新联系人基本信息和邮箱列表。传入 user_uid 校验归属。"""
    db = await get_db()
    cursor = await db.execute(
        """UPDATE contacts SET name = ?, phone = ?, company = ?, remark = ?, group_name = ?, updated_at = ?
           WHERE id = ? AND user_uid = ?""",
        (name, phone, company, remark, group_name, time.time(), contact_id, user_uid),
    )
    if cursor.rowcount == 0:
        return False
    # 邮箱全量更新：先删旧的后插新的
    await db.execute("DELETE FROM contact_emails WHERE contact_id = ?", (contact_id,))
    now = time.time()
    seen = set()
    for i, email in enumerate(emails):
        e = email.strip()
        if not e or e in seen:
            continue
        seen.add(e)
        is_primary = 1 if i == 0 else 0
        await db.execute(
            "INSERT INTO contact_emails (contact_id, email, is_primary, created_at) VALUES (?, ?, ?, ?)",
            (contact_id, e, is_primary, now),
        )
    await db.commit()
    return True


async def delete_contact(contact_id: int, user_uid: str) -> bool:
    """删除联系人（含邮箱），返回是否成功。传入 user_uid 校验归属。"""
    db = await get_db()
    # 先删子表邮箱（SQLite 默认未开启外键级联）
    await db.execute("DELETE FROM contact_emails WHERE contact_id = ?", (contact_id,))
    cursor = await db.execute(
        "DELETE FROM contacts WHERE id = ? AND user_uid = ?",
        (contact_id, user_uid),
    )
    await db.commit()
    return cursor.rowcount > 0


async def upsert_contact_by_email(user_uid: str, name: str, email: str) -> tuple[dict, bool]:
    """按邮箱去重添加联系人（邮件详情快速添加用）。

    返回 (联系人记录, 是否新建)。邮箱已存在时返回 (已有记录, False)，
    不存在则创建并返回 (新记录, True)。
    """
    db = await get_db()
    # 查 contact_emails 是否已有该邮箱
    cursor = await db.execute(
        """SELECT c.* FROM contacts c
           JOIN contact_emails ce ON ce.contact_id = c.id
           WHERE c.user_uid = ? AND ce.email = ?""",
        (user_uid, email),
    )
    row = await cursor.fetchone()
    if row:
        columns = [d[0] for d in cursor.description]
        contact = dict(zip(columns, row))
        emails_map = await _fetch_emails_for_contacts(db, [contact["id"]])
        contact["emails"] = emails_map.get(contact["id"], [])
        return (contact, False)
    # 不存在则创建新联系人
    return (await create_contact(user_uid, name, [email]), True)


def _normalize_contact_email(email: str) -> str:
    """规范化联系人统计用的邮箱地址（去空白、转小写）。"""
    return (email or "").strip().lower()


def _like_escape(value: str) -> str:
    """转义 SQL LIKE 通配符，避免邮箱中的 %/_ 被当作通配符。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _address_field_contains_email(field: str, email_norm: str) -> bool:
    """判断邮件地址字段是否精确包含指定邮箱。

    使用标准库 email.utils.getaddresses 解析 RFC 地址列表，兼容：
    - 纯地址：user@domain.com
    - 显示名：Name <user@domain.com>
    - 多人列表：a@x.com, Name <b@y.com>
    不会因子串包含而误匹配（如 bob@x.com 不匹配 alicebob@x.com / bob@x.com.cn）。
    """
    if not field or not email_norm:
        return False
    from email.utils import getaddresses

    for _, addr in getaddresses([field]):
        if addr and addr.strip().lower() == email_norm:
            return True
    return False


async def get_contact_stats(user_uid: str, email: str) -> dict:
    """统计与某邮箱地址的往来邮件数量和最近联系时间。

    S5 修复：废弃 LIKE %email% 子串匹配，改为「候选预筛 + RFC 精确解析」：
    1. 先用转义后的 LIKE 缩小候选行（性能）
    2. 再用 getaddresses 做完整邮箱 token 精确匹配（正确性）
    """
    email_norm = _normalize_contact_email(email)
    if not email_norm or "@" not in email_norm:
        return {"count": 0, "last_date": ""}

    db = await get_db()
    # 预筛：仍用包含查询缩小范围，但通配符已转义；最终结果以精确解析为准
    like = f"%{_like_escape(email_norm)}%"
    cursor = await db.execute(
        """SELECT date, from_addr, to_addr
           FROM cached_messages
           WHERE user_uid = ?
             AND (from_addr LIKE ? ESCAPE '\\' OR to_addr LIKE ? ESCAPE '\\')""",
        (user_uid, like, like),
    )
    rows = await cursor.fetchall()

    count = 0
    last_date = ""
    for row in rows:
        date_val = row[0] or ""
        from_addr = row[1] or ""
        to_addr = row[2] or ""
        if _address_field_contains_email(from_addr, email_norm) or _address_field_contains_email(to_addr, email_norm):
            count += 1
            # date 存 ISO 或可比较字符串时，字典序近似时间序；取最大作为最近联系
            if date_val and date_val > last_date:
                last_date = date_val

    return {"count": count, "last_date": last_date}


# ==================== 邮件归档 CRUD ====================
# message_archive 表的增删改查，与 cached_messages 完全独立
# .eml 文件永不删除，即使服务器删除邮件也保留本地备份


async def upsert_message_archive(archive: dict) -> bool:
    """插入或更新归档记录（UPSERT，基于 account_id+folder+uid 唯一约束）

    新记录插入时 is_deleted_on_server 默认为 0；
    已存在记录更新时保留原有的 is_deleted_on_server 和 deleted_at 字段（避免误覆盖）。
    """
    db = await get_db()
    now = time.time()
    await db.execute(
        """INSERT INTO message_archive
           (user_uid, account_id, folder, uid, message_id, subject,
            from_addr, to_addr, cc, date, size, eml_path, flags,
            has_attachments, archived_at, is_deleted_on_server, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(account_id, folder, uid) DO UPDATE SET
               message_id = excluded.message_id,
               subject = excluded.subject,
               from_addr = excluded.from_addr,
               to_addr = excluded.to_addr,
               cc = excluded.cc,
               date = excluded.date,
               size = excluded.size,
               eml_path = excluded.eml_path,
               flags = excluded.flags,
               has_attachments = excluded.has_attachments,
               archived_at = excluded.archived_at""",
        (
            archive["user_uid"], archive["account_id"], archive["folder"],
            archive["uid"], archive.get("message_id", ""),
            archive.get("subject", ""), archive.get("from_addr", ""),
            archive.get("to_addr", ""), archive.get("cc", ""),
            archive.get("date", ""), archive.get("size", 0),
            archive["eml_path"], archive.get("flags", ""),
            archive.get("has_attachments", 0), now,
            archive.get("is_deleted_on_server", 0),
            archive.get("deleted_at", 0),
        ),
    )
    await db.commit()
    return True


async def get_archived_messages(
    user_uid: str,
    account_id: str = "",
    folder: str = "",
    page: int = 1,
    page_size: int = 40,
    deleted_filter: str = "",
) -> dict:
    """分页查询归档邮件列表（按 date 倒序）

    folder 参数支持核心类别路径（INBOX/Sent/Drafts/Junk/Trash），
    会自动匹配所有映射到该类别的 IMAP 路径（含网易 Modified UTF-7 编码）。
    deleted_filter: ""=全部, "deleted"=仅服务器已删除, "alive"=仅存活
    """
    db = await get_db()
    where = ["user_uid = ?"]
    params: list = [user_uid]

    if account_id:
        where.append("account_id = ?")
        params.append(account_id)
    if folder:
        # 核心类别文件夹：查询所有映射到该类别的 IMAP 路径
        from services.backup import classify_folder_category
        target_category = classify_folder_category(folder)
        if target_category != 'other':
            # 先查询该用户所有不同的 folder 值
            if account_id:
                cursor = await db.execute(
                    "SELECT DISTINCT folder FROM message_archive WHERE user_uid = ? AND account_id = ?",
                    (user_uid, account_id),
                )
            else:
                cursor = await db.execute(
                    "SELECT DISTINCT folder FROM message_archive WHERE user_uid = ?",
                    (user_uid,),
                )
            all_folders = [r[0] for r in await cursor.fetchall()]
            # 筛选出匹配该类别的 IMAP 路径
            matching = [f for f in all_folders if classify_folder_category(f) == target_category]
            if matching:
                placeholders = ",".join("?" * len(matching))
                where.append(f"folder IN ({placeholders})")
                params.extend(matching)
            else:
                # 没有匹配的路径，返回空结果
                where.append("1=0")
        else:
            where.append("folder = ?")
            params.append(folder)
    if deleted_filter == "deleted":
        where.append("is_deleted_on_server = 1")
    elif deleted_filter == "alive":
        where.append("is_deleted_on_server = 0")

    where_clause = " AND ".join(where)

    # 查总数
    cursor = await db.execute(
        f"SELECT COUNT(*) FROM message_archive WHERE {where_clause}", params
    )
    total = (await cursor.fetchone())[0]

    # 分页查询（按 date 倒序，ISO 格式字符串排序等价于时间排序）
    offset = (page - 1) * page_size
    cursor = await db.execute(
        f"""SELECT * FROM message_archive
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    )
    rows = await cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    messages = [dict(zip(columns, row)) for row in rows]

    return {
        "messages": messages,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_archived_message_by_uid(user_uid: str, account_id: str, folder: str, uid: int) -> dict | None:
    """按 user_uid+account_id+folder+uid 查询单封归档邮件

    必须传入 user_uid 做归属校验，避免越权访问其他用户的归档邮件。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM message_archive WHERE user_uid = ? AND account_id = ? AND folder = ? AND uid = ?",
        (user_uid, account_id, folder, uid),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    columns = [d[0] for d in cursor.description]
    return dict(zip(columns, row))


async def mark_archive_deleted(account_id: str, folder: str, uids: list[int]) -> int:
    """批量标记归档邮件为"服务器已删除"（不删除 .eml 文件）

    只更新 is_deleted_on_server=0 的记录，避免重复更新已标记的记录。
    返回实际标记的行数。
    """
    if not uids:
        return 0
    db = await get_db()
    now = time.time()
    placeholders = ",".join("?" * len(uids))
    cursor = await db.execute(
        f"""UPDATE message_archive
            SET is_deleted_on_server = 1, deleted_at = ?
            WHERE account_id = ? AND folder = ?
              AND uid IN ({placeholders})
              AND is_deleted_on_server = 0""",
        [now, account_id, folder] + list(uids),
    )
    await db.commit()
    return cursor.rowcount


async def get_archive_stats(user_uid: str) -> dict:
    """获取归档统计：总数量、各邮箱归档数量、最后归档时间、已删除数量

    JOIN accounts 表获取 email 和 provider，供前端账号 tabs 显示。
    """
    db = await get_db()
    # 总体统计
    cursor = await db.execute(
        """SELECT COUNT(*) as total,
                  SUM(is_deleted_on_server) as deleted,
                  MAX(archived_at) as last_archived
           FROM message_archive WHERE user_uid = ?""",
        (user_uid,),
    )
    row = await cursor.fetchone()
    total = row[0] if row else 0
    deleted = row[1] if row and row[1] else 0
    last_archived = row[2] if row and row[2] else 0

    # 各账号统计（JOIN accounts 表获取 email 和 provider）
    cursor = await db.execute(
        """SELECT ma.account_id,
                  COUNT(*) as count,
                  SUM(ma.is_deleted_on_server) as deleted_count,
                  MAX(ma.archived_at) as last_time,
                  a.email,
                  a.provider
           FROM message_archive ma
           LEFT JOIN accounts a ON ma.account_id = a.id
           WHERE ma.user_uid = ?
           GROUP BY ma.account_id""",
        (user_uid,),
    )
    rows = await cursor.fetchall()
    accounts = []
    for r in rows:
        accounts.append({
            "account_id": r[0],
            "count": r[1],
            "deleted_count": r[2] if r[2] else 0,
            "last_archived": r[3] if r[3] else 0,
            "email": r[4] or "",
            "provider": r[5] or "",
        })

    return {
        "total": total,
        "deleted": deleted,
        "last_archived": last_archived,
        "accounts": accounts,
    }


async def get_archive_folders(user_uid: str, account_id: str = "") -> list[dict]:
    """获取归档邮件的文件夹列表（按5个核心文件夹类别汇总统计）

    固定返回5个核心文件夹（收件箱/已发送/草稿箱/垃圾邮件/已删除），
    将所有 IMAP 路径（含网易 Modified UTF-7 编码）映射到对应类别。
    account_id 为空时返回所有账号的文件夹汇总。
    """
    db = await get_db()
    if account_id:
        cursor = await db.execute(
            """SELECT folder,
                      COUNT(*) as count,
                      SUM(is_deleted_on_server) as deleted_count
               FROM message_archive
               WHERE user_uid = ? AND account_id = ?
               GROUP BY folder""",
            (user_uid, account_id),
        )
    else:
        cursor = await db.execute(
            """SELECT folder,
                      COUNT(*) as count,
                      SUM(is_deleted_on_server) as deleted_count
               FROM message_archive
               WHERE user_uid = ?
               GROUP BY folder""",
            (user_uid,),
        )
    rows = await cursor.fetchall()

    # 按核心文件夹类别汇总（将所有 IMAP 路径映射到5个类别）
    from services.backup import classify_folder_category
    categories = {
        'inbox':  {'folder': 'INBOX',          'count': 0, 'deleted_count': 0},
        'sent':   {'folder': 'Sent',           'count': 0, 'deleted_count': 0},
        'drafts': {'folder': 'Drafts',         'count': 0, 'deleted_count': 0},
        'junk':   {'folder': 'Junk',           'count': 0, 'deleted_count': 0},
        'trash':  {'folder': 'Trash',          'count': 0, 'deleted_count': 0},
    }
    for r in rows:
        folder_path = r[0]
        count = r[1]
        deleted = r[2] or 0
        category = classify_folder_category(folder_path)
        if category in categories:
            categories[category]['count'] += count
            categories[category]['deleted_count'] += deleted

    # 固定顺序返回5个核心文件夹
    return [
        categories['inbox'],
        categories['sent'],
        categories['drafts'],
        categories['junk'],
        categories['trash'],
    ]


async def get_archived_uids(account_id: str, folder: str) -> dict[int, str]:
    """获取指定文件夹已归档的 UID 及其 eml_path（用于增量归档时跳过已存在的）

    返回 dict: {uid: eml_path（相对路径）}
    调用方可结合 backup_root 拼接绝对路径后校验本地文件是否真实存在，
    避免数据库有记录但文件丢失时不重新归档的问题。
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT uid, eml_path FROM message_archive WHERE account_id = ? AND folder = ?",
        (account_id, folder),
    )
    rows = await cursor.fetchall()
    return {row[0]: (row[1] or "") for row in rows}
