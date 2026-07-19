# -*- coding: utf-8 -*-
"""通知正文渲染（标题固定「飞邮」）。

版式原则（Bark / Telegram 共用 Markdown）：
- 主题置顶
- 分割线
- 发件人 / 收件人 / 抄送人（无则隐藏）/ 时间 / 账户
- 分割线
- 正文预览
- 不展示文件夹
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from services.notify.types import ChannelMessage

# 推送标题固定，不做模板变量
FIXED_TITLE = "飞邮"

# 正文预览与元信息之间的分隔
_SEPARATOR = "────────────────────────"

# 通知展示时区（与免打扰逻辑一致）
_TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _format_mail_date(value: Any) -> str:
    """将邮件时间格式化为本地可读形式。

    输入常见：
    - 2026-07-18T08:14:46Z  （UTC ISO，项目内部存储）→ 转 Asia/Shanghai
    - 2026-07-18 16:14:46   （已是友好格式，原样规范输出）
    输出：
    - 2026-07-18 16:14:46
    """
    # None / 空 / 字面量 "None"/"null" 均视为无时间
    if value is None:
        return "—"
    text = str(value).strip()
    if not text or text == "—" or text.lower() in ("none", "null", "undefined", "nan"):
        return "—"

    # 已是友好本地样式（无 T / 无时区偏移）：直接规范，不再当 UTC 转换
    if "T" not in text and "t" not in text and not text.endswith("Z") and not text.endswith("z"):
        # 排除尾部显式偏移，如 "2026-07-18 08:14:46+00:00"
        has_offset = False
        if len(text) > 10:
            tail = text[10:]
            if "+" in tail or tail.count("-") >= 1 and (":" in tail.split("-")[-1] if "-" in tail else False):
                # 简单判断：空格后的部分是否含 +hh:mm / -hh:mm
                import re as _re
                if _re.search(r"[+-]\d{2}:?\d{2}$", text):
                    has_offset = True
        if not has_offset:
            for fmt, out_fmt in (
                ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"),
                ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:00"),
                ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"),
                ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:00"),
            ):
                try:
                    return datetime.strptime(text, fmt).strftime(out_fmt)
                except Exception:
                    continue

    dt = None
    # ISO（含 Z / 偏移）
    try:
        iso = text
        if iso.endswith("Z") or iso.endswith("z"):
            iso = iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso)
    except Exception:
        dt = None

    # RFC 邮件 Date 头
    if dt is None:
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(text)
        except Exception:
            dt = None

    if dt is None:
        mild = text.replace("T", " ").replace("Z", "").replace("z", "").strip()
        return mild or "—"

    if dt.tzinfo is None:
        # 带 T 的无时区 ISO：按 UTC 处理（与 IMAP 存储一致）
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")


def _s(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _meta_rows(event: Dict[str, Any]) -> List[Tuple[str, str]]:
    """组装元信息行（标签, 值）；无抄送时不包含抄送。"""
    rows: List[Tuple[str, str]] = [
        ("发件人", _s(event.get("from_addr"))),
        ("收件人", _s(event.get("to_addr"))),
    ]
    cc = str(event.get("cc") or "").strip()
    if cc:
        rows.append(("抄送人", cc))
    rows.extend(
        [
            ("时间", _format_mail_date(event.get("mail_date"))),
            ("账户", _s(event.get("email"))),
        ]
    )
    return rows


def _format_label(label: str) -> str:
    """两字标签插入全角空格，与三字标签视觉对齐。"""
    if len(label) == 2:
        return f"{label[0]}　{label[1]}"
    return label


def build_body_text(event: Dict[str, Any]) -> str:
    """纯文本正文（通用回退）：主题 → 分割线 → 元信息 → 分割线 → 正文。"""
    subject = _s(event.get("subject"), "(无主题)")
    lines: List[str] = [
        f"主题  {subject}",
        "",
        _SEPARATOR,
    ]
    for label, value in _meta_rows(event):
        lines.append(f"{_format_label(label)}  {value}")
    lines.append(_SEPARATOR)

    preview = str(event.get("body_preview") or "").strip()
    if preview:
        lines.append("")
        # 纯文本回退同样保留段落空行
        lines.extend(preview.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    return "\n".join(lines)


# 元信息中的邮箱类字段（便于等宽/防自动链接）
_EMAIL_META_LABELS = frozenset({"发件人", "收件人", "抄送人", "账户"})


# Markdown 行内需转义的符号（CommonMark 轻度转义，供 Bark）
_MD_INLINE_SPECIAL = ("\\", "`", "*", "_", "[", "]", "(", ")")

# Telegram MarkdownV2 必须转义的字符
_MDV2_SPECIAL = set(r"_*[]()~`>#+-=|{}.!\\")


def _escape_md_inline(text: str) -> str:
    """CommonMark 轻度转义，避免破坏加粗 / 行内代码。"""
    if not text:
        return ""
    out = text
    # 反斜杠优先
    out = out.replace("\\", "\\\\")
    for ch in _MD_INLINE_SPECIAL[1:]:
        out = out.replace(ch, "\\" + ch)
    return out


def _escape_mdv2(text: str) -> str:
    """Telegram MarkdownV2 纯文本转义。"""
    if not text:
        return ""
    return "".join(("\\" + ch) if ch in _MDV2_SPECIAL else ch for ch in text)


def _escape_mdv2_code(text: str) -> str:
    """MarkdownV2 行内 code 内仅转义 ` 与 \\。"""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("`", "\\`")


def _md_meta_value_common(label: str, value: str) -> str:
    """Bark CommonMark 元信息值。"""
    raw = str(value or "").strip()
    if not raw or raw == "—":
        return "—"
    if label in _EMAIL_META_LABELS:
        safe = raw.replace("`", "'")
        return f"`{safe}`"
    return _escape_md_inline(raw)


def _md_meta_value_mdv2(label: str, value: str) -> str:
    """Telegram MarkdownV2 元信息值。"""
    raw = str(value or "").strip()
    if not raw or raw == "—":
        return _escape_mdv2("—")
    if label in _EMAIL_META_LABELS:
        # 行内 code 可避免邮箱被识别成链接，且无需转义点号
        return f"`{_escape_mdv2_code(raw)}`"
    return _escape_mdv2(raw)


def build_body_markdown(event: Dict[str, Any], *, dialect: str = "common") -> str:
    """统一 Markdown 正文。

    版式：
        主题
        ────────────────────────
        发件人 / 收件人 / 抄送人 / 时间 / 账户
        ────────────────────────
        正文

    dialect:
      - common   : Bark（CommonMark）。单换行会被折叠为空格，
                   因此每行末尾加两个空格做「硬换行」。
      - telegram : Telegram MarkdownV2（*加粗* + 严格转义，原生保留换行）
    """
    subject_raw = _s(event.get("subject"), "(无主题)")
    use_tg = dialect == "telegram"
    sep = _SEPARATOR

    if use_tg:
        subject = _escape_mdv2(subject_raw)
        head = f"*主题*  *{subject}*"
    else:
        subject = _escape_md_inline(subject_raw)
        head = f"**主题**  **{subject}**"

    lines: List[str] = [head, "", sep]

    for label, value in _meta_rows(event):
        label_disp = _format_label(label)
        if use_tg:
            lab = _escape_mdv2(label_disp)
            lines.append(f"*{lab}*  {_md_meta_value_mdv2(label, value)}")
        else:
            lab = _escape_md_inline(label_disp)
            lines.append(f"**{lab}**  {_md_meta_value_common(label, value)}")

    lines.append(sep)

    preview = str(event.get("body_preview") or "").strip()
    if preview:
        lines.append("")
        # 保留正文空行作为段落分隔；行内内容按渠道转义
        for pline in preview.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if pline == "":
                lines.append("")
                continue
            if use_tg:
                lines.append(_escape_mdv2(pline))
            else:
                lines.append(_escape_md_inline(pline))

    if use_tg:
        return "\n".join(lines)

    # Bark / CommonMark：空行保留段落；非空行末尾加两个空格强制换行
    out: List[str] = []
    for line in lines:
        if line == "":
            out.append("")
        else:
            # 已有尾随空格时不重复添加
            out.append(line if line.endswith("  ") else line + "  ")
    return "\n".join(out)



# Telegram sendMessage 文本上限 4096；截断时预留标记空间
TELEGRAM_TEXT_LIMIT = 4096
_TG_TRUNCATE_MARK = "…(正文过长已截断)"


def truncate_telegram_text(text: str, max_len: int = TELEGRAM_TEXT_LIMIT) -> str:
    """将 Telegram MarkdownV2 全文截断到 API 上限内。

    尽量不在反斜杠转义中间切断；超长时追加截断提示。
    """
    raw = text or ""
    limit = max(64, int(max_len or TELEGRAM_TEXT_LIMIT))
    if len(raw) <= limit:
        return raw

    mark = _escape_mdv2(_TG_TRUNCATE_MARK)
    budget = limit - len(mark) - 2  # 换行 + 标记
    if budget < 32:
        return raw[: max(1, limit - 1)] + "…"

    cut = raw[:budget]
    # 若以奇数个连续反斜杠结尾，说明转义未闭合，再削掉一个
    bs = 0
    for ch in reversed(cut):
        if ch == "\\":
            bs += 1
        else:
            break
    if bs % 2 == 1:
        cut = cut[:-1]
    cut = cut.rstrip()
    return cut + "\n\n" + mark


def build_channel_message(event: Dict[str, Any], mode: str = "text") -> ChannelMessage:
    """构建 ChannelMessage。

    body 为纯文本回退；结构化字段放 extra，由各渠道选用 markdown。
    """
    return ChannelMessage(
        title=FIXED_TITLE,
        body=build_body_text(event),
        mode=mode if mode in ("text", "image") else "text",
        extra=dict(event or {}),
    )


def build_test_event() -> Dict[str, Any]:
    """测试发送用固定样例事件（无抄送，验证抄送行隐藏）。"""
    return {
        "type": "new_mail",
        "subject": "飞邮通知测试",
        "from_addr": "sender@example.com",
        "to_addr": "you@example.com",
        "cc": "",
        "mail_date": "2026-07-18 15:30",
        "email": "demo@example.com",
        "body_preview": (
            "这是一条来自飞邮的第三方通知测试消息。\n\n"
            "第二段：用于确认段落与换行是否正常显示。\n\n"
            "第三段：Bark / Telegram 正文应有清晰分段。"
        ),
        "message_cache_id": "",
    }
