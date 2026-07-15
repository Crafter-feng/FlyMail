"""S5 修复验证：联系人往来统计精确邮箱匹配

不依赖真实业务库，使用临时 SQLite 文件验证：
1. 精确匹配 Name <email> / 纯地址 / 多收件人列表
2. 不因子串包含误匹配（alicebob / 子域）
3. 大小写不敏感
4. 非法邮箱输入返回空统计
5. LIKE 通配符转义
"""
import asyncio
import os
import sys
import tempfile
import time

# 保证可导入 backend 包内模块
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import aiosqlite
import db as db_mod


async def _setup_temp_db(db_path: str):
    """初始化最小表结构并注入到 db 模块单例。"""
    # 重置全局连接，指向临时库
    if db_mod._db_instance is not None:
        try:
            await db_mod._db_instance.close()
        except Exception:
            pass
        db_mod._db_instance = None

    db_mod.DB_PATH = db_path
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = aiosqlite.Row
    await conn.execute(
        """
        CREATE TABLE cached_messages (
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
            cached_at REAL DEFAULT 0
        )
        """
    )
    await conn.commit()
    db_mod._db_instance = conn
    return conn


async def _insert_msg(conn, *, msg_id, user_uid, from_addr, to_addr, date):
    await conn.execute(
        """INSERT INTO cached_messages
           (id, account_id, user_uid, uid, folder, subject, from_addr, to_addr, date, cached_at)
           VALUES (?, 'acc1', ?, 1, 'INBOX', 't', ?, ?, ?, ?)""",
        (msg_id, user_uid, from_addr, to_addr, date, time.time()),
    )
    await conn.commit()


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


async def run_tests():
    # ---- 纯函数：地址字段精确匹配 ----
    contains = db_mod._address_field_contains_email
    _assert(contains("bob@example.com", "bob@example.com"), "纯地址应匹配")
    _assert(contains("Bob <bob@example.com>", "bob@example.com"), "显示名格式应匹配")
    _assert(contains("a@x.com, Bob <bob@example.com>", "bob@example.com"), "多地址列表应匹配")
    _assert(contains("BOB@EXAMPLE.COM", "bob@example.com"), "大小写不敏感")
    _assert(not contains("alicebob@example.com", "bob@example.com"), "子串本地部分不应匹配")
    _assert(not contains("bob@example.com.cn", "bob@example.com"), "子域不应匹配")
    _assert(not contains("other@example.com", "bob@example.com"), "无关地址不匹配")
    _assert(not contains("", "bob@example.com"), "空字段不匹配")
    print("[OK] _address_field_contains_email 用例通过")

    # ---- 纯函数：LIKE 转义 ----
    esc = db_mod._like_escape
    _assert(esc("a%b_c") == r"a\%b\_c", "应转义 % 和 _")
    _assert(esc(r"a\b") == r"a\\b", r"应转义反斜杠")
    print("[OK] _like_escape 用例通过")

    # ---- 集成：get_contact_stats ----
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_s5.db")
        conn = await _setup_temp_db(db_path)
        uid = "user1"

        # 应计入
        await _insert_msg(conn, msg_id="1", user_uid=uid,
                          from_addr="Bob <bob@example.com>", to_addr="me@test.com",
                          date="2026-07-10 10:00:00")
        await _insert_msg(conn, msg_id="2", user_uid=uid,
                          from_addr="me@test.com", to_addr="bob@example.com, other@x.com",
                          date="2026-07-12 12:00:00")
        # 不应计入：子串误匹配场景
        await _insert_msg(conn, msg_id="3", user_uid=uid,
                          from_addr="alicebob@example.com", to_addr="me@test.com",
                          date="2026-07-13 13:00:00")
        await _insert_msg(conn, msg_id="4", user_uid=uid,
                          from_addr="bob@example.com.cn", to_addr="me@test.com",
                          date="2026-07-14 14:00:00")
        # 其他用户隔离
        await _insert_msg(conn, msg_id="5", user_uid="user2",
                          from_addr="bob@example.com", to_addr="me@test.com",
                          date="2026-07-15 15:00:00")

        stats = await db_mod.get_contact_stats(uid, "bob@example.com")
        _assert(stats["count"] == 2, f"期望 count=2，实际 {stats}")
        _assert(stats["last_date"] == "2026-07-12 12:00:00", f"期望最近日期为 07-12，实际 {stats}")
        print("[OK] 精确匹配 count/last_date 正确")

        # 大小写输入
        stats2 = await db_mod.get_contact_stats(uid, "  Bob@Example.COM ")
        _assert(stats2["count"] == 2, f"大小写规范化后应仍为 2，实际 {stats2}")
        print("[OK] 输入邮箱大小写/空白规范化正确")

        # 非法输入
        empty = await db_mod.get_contact_stats(uid, "")
        _assert(empty == {"count": 0, "last_date": ""}, f"空邮箱应返回空统计，实际 {empty}")
        bad = await db_mod.get_contact_stats(uid, "not-an-email")
        _assert(bad == {"count": 0, "last_date": ""}, f"无 @ 应返回空统计，实际 {bad}")
        print("[OK] 非法邮箱输入处理正确")

        # 旧 LIKE 行为回归：alicebob / 子域 不得计入
        only_sub = await db_mod.get_contact_stats(uid, "alicebob@example.com")
        _assert(only_sub["count"] == 1, f"alicebob 自己应计 1，实际 {only_sub}")
        only_cn = await db_mod.get_contact_stats(uid, "bob@example.com.cn")
        _assert(only_cn["count"] == 1, f"bob@example.com.cn 自己应计 1，实际 {only_cn}")
        print("[OK] 子串/子域不再误计入目标邮箱统计")

        await conn.close()
        db_mod._db_instance = None

    print("\n全部 S5 验证通过。")


if __name__ == "__main__":
    asyncio.run(run_tests())
