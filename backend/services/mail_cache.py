"""邮件缓存同步服务 - 将邮件摘要缓存到 SQLite，增量拉取新邮件

架构:
  前端请求 → 先返回数据库缓存（瞬间） → 后台增量同步 → WebSocket 通知前端刷新

核心功能:
  1. 全量同步：首次添加账号时，批量拉取最近 N 封邮件摘要写入缓存
  2. 增量同步：基于 UID SEARCH UID > max_cached_uid 只拉取新邮件
  3. 并发控制：每个账号的同步操作用 asyncio.Lock 保护，避免同一连接并发操作
"""

import asyncio
import time

from dataclasses import dataclass, field
from typing import Any, List as _ListTyping

BODY_PREVIEW_MAX = 1000  # 通知/列表正文截取：兼顾 TG 4096、Bark 与图片长图可读性


@dataclass
class SyncFolderResult:
    """文件夹同步结果：新增数量 + 本次新邮件摘要（供通知全部展开）。"""
    new_count: int = 0
    new_items: list = field(default_factory=list)

    def __int__(self) -> int:
        return int(self.new_count)

    def __index__(self) -> int:
        return int(self.new_count)

    def __bool__(self) -> bool:
        return self.new_count > 0


def build_body_preview(body_text: str = "", body_html: str = "", max_len: int = BODY_PREVIEW_MAX) -> str:
    """生成列表/通知用纯文本截取；尽量保留段落与换行。

    优先纯文本；否则从 HTML 抽取，并将 <br>/<p>/<div> 等转为换行。
    不再把全文空白压成单行，避免推送正文「一整段糊在一起」。
    """
    import html as _html
    import re as _re

    text_val = (body_text or "").strip()
    if not text_val and body_html:
        html = body_html or ""
        # 去掉不可见脚本样式
        html = _re.sub(r"(?is)<script[^>]*>.*?</script>", "\n", html)
        html = _re.sub(r"(?is)<style[^>]*>.*?</style>", "\n", html)
        # 块级 / 换行标签 → 换行，保留段落结构
        html = _re.sub(r"(?i)<br\s*/?>", "\n", html)
        html = _re.sub(
            r"(?i)</?(p|div|tr|li|h[1-6]|blockquote|section|article|"
            r"header|footer|table|thead|tbody|ul|ol|hr|pre)(\s[^>]*)?>",
            "\n",
            html,
        )
        # 去掉剩余标签
        text_val = _re.sub(r"(?s)<[^>]+>", "", html)
        text_val = _html.unescape(text_val).strip()

    if not text_val:
        return ""

    text_val = text_val.replace("\r\n", "\n").replace("\r", "\n")
    # 行内空白折叠，行与空行（段落）保留
    raw_lines = []
    prev_blank = True
    for line in text_val.split("\n"):
        collapsed = " ".join(line.split())
        if not collapsed:
            if not prev_blank and raw_lines:
                raw_lines.append("")
                prev_blank = True
            continue
        raw_lines.append(collapsed)
        prev_blank = False
    while raw_lines and raw_lines[-1] == "":
        raw_lines.pop()

    # 软换行回流：上一行较长且不像句末时，与下一行用空格拼接（常见邮件 72 列硬折行）
    # 空行始终作为段落分隔保留
    lines: list = []
    buf = ""
    for line in raw_lines:
        if line == "":
            if buf:
                lines.append(buf)
                buf = ""
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if not buf:
            buf = line
            continue
        ends_sentence = buf.endswith(
            (".", "!", "?", "。", "！", "？", "…", ":", "：", '"', "'", "”", "’", ")", "）", "」", "』")
        )
        # 较短行更可能是有意换行（列表/签名/中文分段），不合并
        if (not ends_sentence) and len(buf) >= 48:
            buf = f"{buf} {line}"
        else:
            lines.append(buf)
            buf = line
    if buf:
        lines.append(buf)

    # 再次压掉连续空行
    out_lines: list = []
    prev_blank = False
    for line in lines:
        if line == "":
            if not prev_blank and out_lines:
                out_lines.append("")
                prev_blank = True
            continue
        out_lines.append(line)
        prev_blank = False

    text_val = "\n".join(out_lines).strip()
    if not text_val:
        return ""
    if len(text_val) > max_len:
        cut = text_val[:max_len].rstrip()
        # 尽量在段落或空格边界截断，避免半截词
        for sep in ("\n\n", "\n", " "):
            pos = cut.rfind(sep)
            if pos >= max_len // 2:
                cut = cut[:pos].rstrip()
                break
        return cut + "…"
    return text_val


def messages_to_new_mail_items(messages, account, folder: str, existing_uids: set) -> list:
    """从本次同步的 Message 列表提取真正新增邮件的通知摘要项。"""
    items = []
    for m in messages:
        if not m.uid or m.uid in existing_uids:
            continue
        cache_id = make_cached_message_id(account.id, folder or m.folder, m.uid)
        subject = (getattr(m, "subject", None) or "").strip()
        items.append({
            "account_id": account.id,
            "folder": folder or m.folder or "INBOX",
            "uid": int(m.uid),
            "message_cache_id": cache_id,
            "subject": subject,
            "from_addr": getattr(m, "from_addr", "") or "",
            "to_addr": getattr(m, "to_addr", "") or "",
            "cc": getattr(m, "cc", "") or "",
            "mail_date": getattr(m, "date", "") or "",
            "body_preview": build_body_preview(
                getattr(m, "body_text", "") or "",
                getattr(m, "body_html", "") or "",
            ),
            "has_attachments": bool(getattr(m, "has_attachments", False)),
            "rfc_message_id": getattr(m, "message_id", "") or "",
        })
    # 新到旧
    items.sort(key=lambda x: x.get("uid", 0), reverse=True)
    return items

from typing import Dict, List

from db import (
    upsert_cached_messages, get_max_cached_uid, get_accounts,
    upsert_folder_stats, get_folder_stats,
    purge_deleted_from_cache, get_cached_count, get_cached_uids,
    get_cached_messages_by_folder, batch_update_is_read,
    make_cached_message_id,
)
from models import CachedMessage, Account
from providers.base import Message
from providers.factory import ProviderFactory
from utils.logger import get_logger
from utils.tasks import create_background_task

logger = get_logger("cache")

# 新邮件通知补拉正文预览的上限（避免离线堆积时一次 BODY.PEEK 过多；最新优先）
# 第三方推送依赖 body_preview，默认 50 封可覆盖常见突发量
BODY_PREVIEW_ENRICH_MAX = 50


async def enrich_new_mail_body_previews(receiver, folder: str, items: list, max_items: int = BODY_PREVIEW_ENRICH_MAX) -> None:
    """为通知摘要补齐 body_preview。

    列表/增量同步只 FETCH 头字段，Message 无正文，导致第三方通知缺正文。
    此处仅对「真正新增且预览为空」的少量邮件按 UID 拉详情（BODY.PEEK[]，不改 Seen）。
    失败不抛错，保证同步与通知主路径不受影响。
    """
    if not items or receiver is None:
        return

    need = [
        it for it in items
        if not str(it.get("body_preview") or "").strip() and int(it.get("uid") or 0) > 0
    ]
    if not need:
        return

    # 最新优先；超出上限的仍发通知，只是可能无正文截取
    limit = max(1, int(max_items or BODY_PREVIEW_ENRICH_MAX))
    need_sorted = sorted(need, key=lambda x: int(x.get("uid") or 0), reverse=True)
    skipped = max(0, len(need_sorted) - limit)
    need = need_sorted[:limit]
    if skipped:
        logger.info(
            "新邮件正文预览补齐超限: folder=%s total=%d limit=%d skipped=%d（超出部分仍推送，可能无正文）",
            folder or "INBOX",
            len(need_sorted),
            limit,
            skipped,
        )
    folder_path = folder or "INBOX"
    filled = 0
    for it in need:
        uid = int(it.get("uid") or 0)
        try:
            detail = await receiver.fetch_message_detail(str(uid), folder_path)
            preview = build_body_preview(
                getattr(detail, "body_text", "") or "",
                getattr(detail, "body_html", "") or "",
            )
            if preview:
                it["body_preview"] = preview
                filled += 1
            # 详情里若有更完整元信息，顺带补齐（不覆盖已有非空）
            if not str(it.get("cc") or "").strip():
                cc_val = getattr(detail, "cc", "") or ""
                if cc_val:
                    it["cc"] = cc_val
            if not str(it.get("rfc_message_id") or "").strip():
                mid = getattr(detail, "message_id", "") or ""
                if mid:
                    it["rfc_message_id"] = mid
        except Exception as e:
            logger.debug("补拉正文预览失败 uid=%s folder=%s: %s", uid, folder_path, e)
    if filled:
        logger.info(
            "新邮件正文预览已补齐: folder=%s, filled=%d/%d",
            folder_path, filled, len(need),
        )


# 全量同步：分页拉满，避免只取首页 500 封导致大邮箱缺信
FULL_SYNC_PAGE_SIZE = 500
FULL_SYNC_MAX_PAGES = 40  # 上限约 20000 封，防止极端邮箱拖垮
MISSING_BATCH_RETRIES = 2

# 每个账号的同步锁，防止同一账号并发同步（IMAP 连接不能并发操作）
_sync_locks: Dict[str, asyncio.Lock] = {}


async def _fetch_all_message_pages(receiver, account: Account, folder: str):
    """按页拉取直至凑齐 total 或达到页数上限（Gmail/QQ 等 page 语义）。

    Outlook 的 page 语义不可靠，改走 UID 全量 + 分批摘要，避免漏信。
    """
    # Outlook：page 翻页会漏信，走 UID 分批路径
    if getattr(account, "provider", "") == "outlook":
        return await _fetch_all_messages_by_uids(receiver, account, folder)

    all_messages: List[Message] = []
    total = 0
    unread = 0
    for page in range(1, FULL_SYNC_MAX_PAGES + 1):
        result = await receiver.fetch_messages(
            folder, page=page, page_size=FULL_SYNC_PAGE_SIZE
        )
        total = result.total
        unread = result.unread_total
        batch = [m for m in result.messages if m.uid > 0]
        if not batch:
            break
        all_messages.extend(batch)
        if len(all_messages) >= total or len(batch) < FULL_SYNC_PAGE_SIZE:
            break
    # 按 UID 去重（分页重叠时）
    seen: set[int] = set()
    uniq: List[Message] = []
    for m in all_messages:
        if m.uid in seen:
            continue
        seen.add(m.uid)
        uniq.append(m)
    return uniq, total, unread


async def _fetch_all_messages_by_uids(receiver, account: Account, folder: str):
    """Outlook 等：UID 全量 + 分批摘要，避免错误 page 翻页漏信。"""
    all_uids = await receiver.fetch_new_message_uids(folder, since_uid=0)
    if not all_uids:
        return [], 0, 0
    # 优先用 STATUS/folder_counts 的未读数；失败再退到 UNSEEN UID 计数
    unread = 0
    try:
        if hasattr(receiver, "fetch_folder_counts"):
            counts = await receiver.fetch_folder_counts([folder])
            folder_count = counts.get(folder, {}) if isinstance(counts, dict) else {}
            unread = int(folder_count.get("unread", 0) or 0)
        else:
            unseen = set(await receiver.fetch_unseen_uids(folder))
            unread = len(unseen)
    except Exception:
        try:
            unseen = set(await receiver.fetch_unseen_uids(folder))
            unread = len(unseen)
        except Exception:
            unread = 0
    total = len(all_uids)
    messages: List[Message] = []
    for i in range(0, len(all_uids), FULL_SYNC_PAGE_SIZE):
        chunk = all_uids[i:i + FULL_SYNC_PAGE_SIZE]
        batch = await receiver.fetch_messages_by_uids(folder, chunk)
        messages.extend([m for m in batch if m.uid > 0])
    return messages, total, unread


def _get_lock(account_id: str) -> asyncio.Lock:
    """获取账号级别的同步锁"""
    if account_id not in _sync_locks:
        _sync_locks[account_id] = asyncio.Lock()
    return _sync_locks[account_id]


def remove_sync_lock(account_id: str):
    """清理指定账号的同步锁（账号删除时调用，防止内存泄漏）"""
    _sync_locks.pop(account_id, None)


async def sync_folder_to_cache(account: Account, folder: str = "INBOX", force_full: bool = False) -> SyncFolderResult:
    """将文件夹的邮件摘要同步到本地缓存（增量：只拉取新邮件）

    使用独立的 IMAP 连接，不影响后台实时监听连接。
    返回新增的邮件数量。
    force_full: 强制全量同步（rebuild-sync 时使用）
    """
    lock = _get_lock(account.id)
    # 等待锁释放后再同步，而非跳过（跳过会导致新邮件不写入缓存）
    async with lock:
        # 建立独立连接（不复用后台监听连接，避免干扰）
        # Gmail 需要检查 access_token 是否过期并自动刷新
        receiver = None
        try:
            from services.token import ensure_token
            credentials = await ensure_token(account)
            receiver = ProviderFactory.get_receiver(account.provider)
            await receiver.connect(credentials)
            return await _do_sync(receiver, account, folder, force_full=force_full)
        except Exception as e:
            logger.warning("同步账号 %s 文件夹 %s 失败: %s", account.email, folder, e)
            return SyncFolderResult(0, [])
        finally:
            if receiver:
                try:
                    await receiver.disconnect()
                except Exception as e:
                    logger.debug("同步后断开连接失败: %s", e)


async def _do_sync(receiver, account: Account, folder: str, force_full: bool = False) -> SyncFolderResult:
    """执行增量同步核心逻辑

    统一使用 UID SEARCH 做增量检查：
    1. 查询缓存中最大的 UID
    2. 如果没有缓存也没有同步记录 → 全量拉取（批量 UID FETCH）
    3. 如果有缓存或同步记录 → 增量拉取（UID SEARCH UID > max_uid）
    4. 写入缓存（INSERT OR IGNORE + UPDATE，不覆盖已有正文）
    5. 更新 folder_stats（IMAP 真实总数和未读数）
    6. 清理缓存中已不在 IMAP 服务器上的邮件（仅全量同步时）

    force_full: 强制全量同步（rebuild-sync 时使用，避免并发写入导致增量同步遗漏）
    """
    max_uid = await get_max_cached_uid(account.user_uid, account.id, folder)
    folder_stats = await get_folder_stats(account.id, folder)
    inserted_count = 0
    new_mail_items = []

    # 首次同步判断：max_uid=0 且从未同步过（updated_at=0）。若 max_uid=0 但 updated_at≠0，说明曾经同步过但邮件被全部删除，走增量同步即可
    # force_full=True 时强制走全量同步（rebuild-sync 场景）
    if (max_uid == 0 and folder_stats["updated_at"] == 0) or force_full:
        # 首次/强制全量：分页或 UID 分批拉满，避免只取首页 500 封导致大邮箱缺信
        logger.info("首次同步: 账号=%s, 文件夹=%s, 全量拉取", account.email, folder)
        # 不再先删后写，避免中间时间窗口前端请求看到空缓存
        # 改为先写后删：写入新数据后，用 purge_deleted_from_cache 清理不在新数据中的旧记录
        messages, total_count, unread_count = await _fetch_all_message_pages(
            receiver, account, folder
        )
        messages = [m for m in messages if m.uid > 0]
        # 只有当拉取了全部邮件时（messages 数量等于 total_count），才用 all_uids 做清理
        # 否则 all_uids 不完整，purge_deleted_from_cache 会误删未拉取的缓存
        if total_count > 0 and len(messages) >= total_count:
            all_uids = {m.uid for m in messages}
        else:
            all_uids = None  # 拉取不完整，不做清理
    else:
        # 增量同步：统一用 UID SEARCH 检查新邮件
        # Outlook/Hotmail 的 UID 不一定按邮件时间递增，使用 max_cached_uid 会漏掉新邮件。
        # 因此 Outlook 优先用 STATUS 总数判断：只要 IMAP 总数增加，就拉取最新一页写缓存。
        if account.provider == "outlook":
            try:
                counts = await receiver.fetch_folder_counts([folder])
                folder_count = counts.get(folder, {})
                current_total = folder_count.get("total", 0)
                current_unread = folder_count.get("unread", 0)
            except Exception:
                current_total = 0
                current_unread = 0
            if current_total > folder_stats.get("total_count", 0):
                diff = current_total - folder_stats.get("total_count", 0)
                page_size = min(max(diff + 20, 40), 100)
                logger.debug(
                    "Outlook 总数增加，拉取最新邮件: 账号=%s, 文件夹=%s, 本地=%d, IMAP=%d, page_size=%d",
                    account.email, folder, folder_stats.get("total_count", 0), current_total, page_size,
                )
                result = await receiver.fetch_messages(folder, page=1, page_size=page_size)
                messages = [m for m in result.messages if m.uid > 0]
                all_uids = None  # 增量同步不做全量UID清理
                total_count = current_total
                unread_count = current_unread
            else:
                # Outlook UID 不按时间递增，回退 500 个 UID 作为增量窗口，避免漏收
                since_uid = max(0, max_uid - 500)
                logger.debug(
                    "Outlook 增量窗口同步: 账号=%s, 文件夹=%s, max_uid=%d, since_uid=%d",
                    account.email, folder, max_uid, since_uid,
                )
                new_uids = await receiver.fetch_new_message_uids(folder, since_uid=since_uid)
                if not new_uids:
                    messages = []
                    all_uids = None  # 无新邮件时不做全量UID清理
                else:
                    messages = await receiver.fetch_messages_by_uids(folder, new_uids)
                    messages = [m for m in messages if m.uid > 0]
                    all_uids = None  # 增量同步不做全量UID清理
                # -1 为哨兵值，表示尚未获取真实计数；后续通过 IMAP STATUS 命令获取实际值
                total_count = -1
                unread_count = -1
        else:
            # 非 Outlook 账号：基于 max_uid 做增量同步
            if max_uid == 0:
                pass  # 空文件夹，跳过增量检查
            else:
                logger.debug("增量同步: 账号=%s, 文件夹=%s, since_uid=%d", account.email, folder, max_uid)
            new_uids = await receiver.fetch_new_message_uids(folder, since_uid=max_uid)
            if not new_uids:
                messages = []
                all_uids = None  # 无新邮件时不做全量UID清理
            else:
                messages = await receiver.fetch_messages_by_uids(folder, new_uids)
                # 过滤无效 UID（uid=0），避免写入后又被清理
                messages = [m for m in messages if m.uid > 0]
                all_uids = None  # 增量同步不做全量UID清理，减少IMAP开销
            total_count = -1
            unread_count = -1
        # 增量同步时不再获取全量 UID 列表（减少 IMAP 开销）
        # 删除清理在下方通过 STATUS 总数比对触发，仅在检测到删除时才获取全量 UID

    # 如果没有从 fetch_messages 获取到总数，用 STATUS 命令获取
    if total_count < 0:
        try:
            counts = await receiver.fetch_folder_counts([folder])
            if folder in counts:
                total_count = counts[folder].get("total", 0)
                unread_count = counts[folder].get("unread", 0)
            else:
                total_count = 0
                unread_count = 0
        except Exception as e:
            logger.warning("获取文件夹统计失败: %s, %s", folder, e)
            total_count = 0
            unread_count = 0

    # 即使文件夹为空也要写入 folder_stats，作为"已同步过"的标记，避免下次刷新重复全量拉取
    if total_count >= 0:
        await upsert_folder_stats(account.id, folder, total_count, unread_count)

    # 增量同步时检测删除：当缓存行数 > IMAP 总数，说明有邮件被删除/移动
    # 仅在检测到删除时获取全量 UID 做清理，避免每次增量同步都获取
    if not force_full and total_count > 0:
        try:
            cached_count = await get_cached_count(account.id, folder)
            if cached_count > total_count:
                all_uids_for_purge = set(await receiver.fetch_new_message_uids(folder, since_uid=0))
                if all_uids_for_purge:
                    # 先标记归档表（在 purge 删除缓存记录之前，否则无法计算差集）
                    # 保留 .eml 文件和归档记录，仅标记 is_deleted_on_server=1
                    try:
                        from services.backup import mark_archived_as_deleted
                        cached_uids = await get_cached_uids(account.id, folder)
                        deleted_uids = cached_uids - all_uids_for_purge
                        if deleted_uids:
                            await mark_archived_as_deleted(account.id, folder, list(deleted_uids))
                    except Exception as e:
                        logger.debug("标记归档删除失败(增量): %s", e)
                    # 再执行原有的缓存清理
                    purged = await purge_deleted_from_cache(account.id, folder, all_uids_for_purge)
                    if purged > 0:
                        logger.info("增量清理过期缓存: 账号=%s, 文件夹=%s, 删除 %d 封",
                                   account.email, folder, purged)
        except Exception as e:
            logger.debug("增量清理过期缓存失败: %s", e)

    # 获取 UNSEEN UID 集合，用于校正 is_read（只查一次，新邮件校正和全量校正复用）
    unseen_uids = None
    try:
        unseen_uids = set(await receiver.fetch_unseen_uids(folder))
    except Exception as e:
        logger.debug("获取 UNSEEN UID 失败: %s", e)

    if messages:
        existing_uids = await get_cached_uids(account.id, folder)
        inserted_count = sum(1 for m in messages if m.uid not in existing_uids)

        new_mail_items = messages_to_new_mail_items(messages, account, folder, existing_uids)
        # 列表同步无正文：增量场景为第三方通知补拉纯文本预览
        # 首次/全量同步 new_mail_items 可能极多且通常不发通知，跳过 BODY.PEEK
        if new_mail_items and max_uid > 0 and len(new_mail_items) <= 100:
            try:
                await enrich_new_mail_body_previews(receiver, folder, new_mail_items)
            except Exception as e:
                logger.debug("enrich body_preview 跳过: %s", e)


        # 用 UNSEEN 校正本次拉取邮件的 is_read 状态
        if unseen_uids is not None:
            for m in messages:
                m.is_read = m.uid not in unseen_uids
            logger.debug(
                "is_read 校正: 账号=%s, 文件夹=%s, 未读UID=%s",
                account.email, folder, unseen_uids or "无"
            )

        cached = _messages_to_cached(messages, account)
        await upsert_cached_messages(cached)

        # 邮件归档触发：检查用户是否开启备份，且当前账号在备份列表中
        # 只归档真正新增的邮件（uid 不在 existing_uids 中的）
        # 使用批量归档（复用一个 IMAP 连接），避免每封邮件创建连接导致 IMAP 服务器拒绝
        try:
            from services.backup import archive_messages_batch, should_archive
            if await should_archive(account.user_uid, account.id):
                new_uids = [m.uid for m in messages if m.uid not in existing_uids]
                if new_uids:
                    create_background_task(
                        archive_messages_batch(account, folder, new_uids),
                        name=f"archive_batch_{account.id}_{folder}"
                    )
        except Exception as e:
            logger.debug("归档触发失败（不影响同步）: %s", e)

        # 日志中包含已读/未读统计，方便排查问题
        read_count = sum(1 for m in messages if m.is_read)
        logger.info(
            "同步完成: 账号=%s, 文件夹=%s, 拉取 %d 封, 真正新增 %d 封 (已读 %d, 未读 %d)",
            account.email, folder, len(messages), inserted_count, read_count, len(messages) - read_count
        )

    # 增量同步时校正已有缓存邮件的 is_read 状态
    # 场景：用户在其他客户端标记已读/未读 → 后台监听/刷新触发同步 → 更新缓存
    # 复用上面获取的 unseen_uids，不额外查询 IMAP
    if not force_full and unseen_uids is not None:
        try:
            cached_msgs = await get_cached_messages_by_folder(
                account.user_uid, account.id, folder, page=1, page_size=10000
            )
            if cached_msgs.get("messages"):
                to_fix = []
                for msg in cached_msgs["messages"]:
                    should_read = msg["uid"] not in unseen_uids
                    if bool(msg["is_read"]) != should_read:
                        to_fix.append((msg["uid"], 1 if should_read else 0))
                if to_fix:
                    await batch_update_is_read(account.id, folder, to_fix)
                    fixed_read = sum(1 for _, v in to_fix if v == 1)
                    logger.info(
                        "增量 is_read 校正: 账号=%s, 文件夹=%s, 修正 %d 封 (→已读 %d, →未读 %d)",
                        account.email, folder, len(to_fix), fixed_read, len(to_fix) - fixed_read
                    )
        except Exception as e:
            logger.debug("增量 is_read 校正失败: %s", e)

    # 同步完成后，批量校正整个文件夹缓存中的 is_read（force_full 时执行全量校正）
    # 增量同步已在上方校正所有缓存邮件的 is_read，force_full 时再做一次确保完整
    if force_full:
        try:
            cached_msgs = await get_cached_messages_by_folder(
                account.user_uid, account.id, folder, page=1, page_size=10000
            )
            if cached_msgs.get("messages"):
                all_unseen = set(await receiver.fetch_unseen_uids(folder))
                # 找出需要更新的邮件（is_read 与实际不符的）
                to_fix = []
                for msg in cached_msgs["messages"]:
                    should_read = msg["uid"] not in all_unseen
                    if bool(msg["is_read"]) != should_read:
                        to_fix.append((msg["uid"], 1 if should_read else 0))
                if to_fix:
                    await batch_update_is_read(account.id, folder, to_fix)
                    fixed_read = sum(1 for _, v in to_fix if v == 1)
                    logger.info(
                        "批量 is_read 校正: 账号=%s, 文件夹=%s, 修正 %d 封 (→已读 %d, →未读 %d)",
                        account.email, folder, len(to_fix), fixed_read, len(to_fix) - fixed_read
                    )
        except Exception as e:
            logger.warning("批量 is_read 校正失败: %s", e)

    # 清理缓存中已不在 IMAP 服务器上的邮件
    if all_uids is not None and len(all_uids) > 0:
        # 先标记归档表（在 purge 删除缓存记录之前）
        # 保留 .eml 文件和归档记录，仅标记 is_deleted_on_server=1
        try:
            from services.backup import mark_archived_as_deleted
            cached_uids = await get_cached_uids(account.id, folder)
            deleted_uids = cached_uids - all_uids
            if deleted_uids:
                await mark_archived_as_deleted(account.id, folder, list(deleted_uids))
        except Exception as e:
            logger.debug("标记归档删除失败(全量): %s", e)
        # 再执行原有的缓存清理
        purged = await purge_deleted_from_cache(account.id, folder, all_uids)
        if purged > 0:
            logger.info("清理过期缓存: 账号=%s, 文件夹=%s, 删除 %d 封", account.email, folder, purged)

    # 缓存完整性检查：对比 IMAP 总数与实际缓存行数
    if total_count > 0:
        cached_count = await get_cached_count(account.id, folder)
        if cached_count < total_count:
            logger.warning(
                "缓存不完整: 账号=%s, 文件夹=%s, IMAP总数=%d, 缓存行数=%d, 缺失 %d 封",
                account.email, folder, total_count, cached_count, total_count - cached_count
            )
            # 缓存不完整时自动触发补全；整次补全最多重试 2 次，降低瞬态失败导致长期缺信
            for attempt in range(2):
                try:
                    supplemented = await _sync_missing_messages_unlocked(account, folder)
                    if supplemented > 0:
                        logger.info(
                            "自动补全缓存: 账号=%s, 文件夹=%s, 补充 %d 封 (attempt=%d)",
                            account.email, folder, supplemented, attempt + 1,
                        )
                    cached_count = await get_cached_count(account.id, folder)
                    if cached_count >= total_count:
                        break
                except Exception as e:
                    logger.warning(
                        "自动补全缓存失败: 账号=%s, 文件夹=%s, attempt=%d, 错误=%s",
                        account.email, folder, attempt + 1, e,
                    )

    return SyncFolderResult(inserted_count, new_mail_items)


async def sync_missing_messages(account: Account, folder: str) -> int:
    """补全缓存中缺失的邮件（对外入口，会获取账号级同步锁）

    当外部接口或后台任务单独触发补全时，通过账号锁避免与同账号其他 IMAP 同步并发。
    sync_folder_to_cache 已经持有这把锁，内部会直接调用 _sync_missing_messages_unlocked，避免自锁死。
    """
    lock = _get_lock(account.id)
    async with lock:
        return await _sync_missing_messages_unlocked(account, folder)


async def _sync_missing_messages_unlocked(account: Account, folder: str) -> int:
    """补全缓存中缺失的邮件（内部实现，不再获取锁）

    调用方必须保证同账号同步已串行化：
    - sync_folder_to_cache 内部调用时已经持有账号锁
    - sync_missing_messages 对外入口会先获取账号锁
    """
    receiver = None
    try:
        from services.token import ensure_token
        credentials = await ensure_token(account)
        receiver = ProviderFactory.get_receiver(account.provider)
        await receiver.connect(credentials)

        # 1. 获取 IMAP 全量 UID 列表
        try:
            imap_uids = set(await receiver.fetch_new_message_uids(folder, since_uid=0))
        except Exception as e:
            logger.warning("获取 IMAP UID 列表失败: %s, %s", folder, e)
            return 0

        if not imap_uids:
            return 0

        # 2. 获取缓存中的 UID 集合
        cached_uids = await get_cached_uids(account.id, folder)

        # 3. 找出差异（IMAP 有但缓存没有的 UID）
        missing_uids = imap_uids - cached_uids
        if not missing_uids:
            return 0

        logger.info(
            "补全同步: 账号=%s, 文件夹=%s, IMAP=%d封, 缓存=%d封, 缺失=%d封",
            account.email, folder, len(imap_uids), len(cached_uids), len(missing_uids)
        )

        # 4. 分批拉取缺失的邮件（每批100个UID，避免单次请求过大）
        total_filled = 0
        missing_list = sorted(missing_uids)
        batch_size = 100
        # is_read 校正：只调用一次 fetch_unseen_uids，避免每批重复查询
        unseen_uids = set()
        try:
            unseen_uids = set(await receiver.fetch_unseen_uids(folder))
        except Exception as e:
            logger.debug("获取未读 uid 列表失败，跳过 is_read 校正: %s", e)
        for i in range(0, len(missing_list), batch_size):
            batch = missing_list[i:i + batch_size]
            # 单批失败时有限重试，避免一整批缺失长期留在缓存外
            last_err = None
            for attempt in range(MISSING_BATCH_RETRIES + 1):
                try:
                    messages = await receiver.fetch_messages_by_uids(folder, batch)
                    messages = [m for m in messages if m.uid > 0]
                    if messages:
                        # 用之前获取的 unseen_uids 校正 is_read
                        for m in messages:
                            m.is_read = m.uid not in unseen_uids
                        cached = _messages_to_cached(messages, account)
                        await upsert_cached_messages(cached)
                        total_filled += len(messages)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if attempt < MISSING_BATCH_RETRIES:
                        logger.warning(
                            "补全同步批次失败将重试: %s, UIDs=%s, attempt=%d, 错误=%s",
                            folder, batch[:5], attempt + 1, e,
                        )
                        await asyncio.sleep(0.3 * (attempt + 1))
            if last_err is not None:
                logger.warning(
                    "补全同步批次失败: %s, UIDs=%s, 错误=%s",
                    folder, batch[:5], last_err,
                )

        if total_filled > 0:
            logger.info(
                "补全同步完成: 账号=%s, 文件夹=%s, 补全 %d 封",
                account.email, folder, total_filled
            )
        return total_filled
    except Exception as e:
        logger.error("补全同步失败: 账号=%s, 文件夹=%s, %s", account.email, folder, e)
        return 0
    finally:
        if receiver:
            try:
                await receiver.disconnect()
            except Exception as e:
                logger.debug("同步后断开连接失败: %s", e)


def _messages_to_cached(messages: List[Message], account: Account) -> List[CachedMessage]:
    """将 IMAP 获取的 Message 列表转换为 CachedMessage 列表（用于写入数据库）"""
    return [
        CachedMessage(
            id=make_cached_message_id(account.id, m.folder, m.uid),
            account_id=account.id,
            user_uid=account.user_uid,
            uid=m.uid,
            folder=m.folder,
            subject=m.subject,
            from_addr=m.from_addr,
            to_addr=m.to_addr,
            date=m.date,
            is_read=m.is_read,
            is_starred=m.is_starred,
            has_attachments=m.has_attachments,
            # 列表摘要通常无 Message-ID；若详情已解析则一并写入
            message_id=getattr(m, "message_id", "") or "",
            cached_at=time.time(),
        )
        for m in messages
    ]


async def sync_all_folders(account: Account, folder_paths: List[str], force_full: bool = False, user_uid: str = "") -> int:
    """同步账号的所有文件夹（用于首次添加账号时的全量同步）"""
    total_new = 0
    total_folders = len(folder_paths)
    for i, folder_path in enumerate(folder_paths):
        try:
            result = await sync_folder_to_cache(account, folder_path, force_full=force_full)
            total_new += int(result)
            # 推送同步进度
            if user_uid:
                try:
                    from services.sync import sync_service
                    await sync_service.notify_sync_progress(
                        account.id, folder_path, i + 1, total_folders, user_uid
                    )
                except Exception as e:
                    logger.debug("推送同步进度失败: %s", e)
        except Exception as e:
            logger.warning("同步文件夹 %s 失败，跳过继续: %s", folder_path, e)
    return total_new


async def initial_sync(account_id: str, force_full: bool = False, user_uid: str = ""):
    """首次添加账号时的全量同步（后台任务）

    同步所有核心文件夹的邮件摘要到缓存。
    Microsoft IMAP 在 OAuth 刚完成后可能短暂不可用（"User is authenticated but not connected"），
    因此增加重试逻辑：最多3次，间隔递增（5/10/15秒）。

    force_full: 强制全量同步（rebuild-sync 时使用，确保清空缓存后重新拉取所有邮件）
    """
    try:
        # 查找所有用户中匹配的账号
        accounts = await get_accounts("")
        account = next((a for a in accounts if a.id == account_id), None)
        if not account:
            logger.error("初始同步失败: 找不到账号 %s", account_id)
            return

        # Microsoft IMAP 在 OAuth 刚完成后可能短暂不可用，增加重试
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                # 先尝试连接 IMAP 并获取文件夹列表
                # 如果这一步就失败，说明连接不可用，直接触发重试
                from services.token import ensure_token
                credentials = await ensure_token(account)
                receiver = ProviderFactory.get_receiver(account.provider)
                folders = []
                try:
                    await receiver.connect(credentials)
                    folders = await receiver.fetch_folders()
                    folder_paths = [f.path for f in folders]
                except Exception as e:
                    # 连接/获取文件夹失败，直接抛出异常触发重试
                    raise
                finally:
                    await receiver.disconnect()

                # 同步所有文件夹。Outlook 必须强制包含 INBOX（Microsoft IMAP 的 LIST 命令有时不返回 INBOX，是已知问题）
                if account.provider == "outlook":
                    folder_paths = [f.path for f in folders if f.path]
                    if "INBOX" not in folder_paths:
                        folder_paths.insert(0, "INBOX")
                total = await sync_all_folders(account, folder_paths, force_full=force_full)

                # sync_folder_to_cache 内部会吞掉异常返回0，
                # 区分"邮箱为空"和"连接异常"：文件夹列表已成功获取说明连接正常，0封就是空邮箱
                if total == 0 and account.provider == "outlook" and not folders:
                    raise ConnectionError(
                        "Outlook 初始同步返回0封邮件且无法获取文件夹列表，可能 IMAP 连接异常"
                    )

                logger.info("初始同步完成: 账号=%s, 共同步 %d 封邮件", account.email, total)
                return  # 同步成功，退出
            except Exception as e:
                error_msg = str(e)
                # 判断是否为 Microsoft IMAP 暂时不可用的错误（可重试）
                is_retryable = (
                    "User is authenticated but not connected" in error_msg
                    or "NOOP verification failed" in error_msg
                    or "AUTHENTICATE UNAVAILABLE" in error_msg
                    or "Outlook 初始同步返回0封邮件" in error_msg
                    or "Outlook IMAP 认证成功但连接不可用" in error_msg
                )
                if is_retryable and attempt < max_retries:
                    delay = attempt * 5  # 5/10/15 秒递增
                    logger.warning(
                        "初始同步第 %d 次失败（Microsoft IMAP 暂不可用），%d 秒后重试: %s",
                        attempt, delay, e,
                    )
                    await asyncio.sleep(delay)
                    continue
                # 不可重试或已达到最大重试次数
                logger.error("初始同步异常: %s", e)
                return
    except Exception as e:
        logger.error("初始同步异常: %s", e)
