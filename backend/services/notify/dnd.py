# -*- coding: utf-8 -*-
"""免打扰时段判断（固定 Asia/Shanghai，支持跨午夜）。"""
from __future__ import annotations

from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Asia/Shanghai")


def _parse_hm(value: str) -> Tuple[int, int]:
    """解析 HH:MM，非法时回退 0:0。"""
    try:
        parts = (value or "").strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (TypeError, ValueError, IndexError):
        pass
    return 0, 0


def _to_minutes(h: int, m: int) -> int:
    return h * 60 + m


def is_in_dnd(dnd_start: str, dnd_end: str, now: datetime | None = None) -> bool:
    """判断当前是否处于免打扰时段。

    - start == end：视为未启用免打扰
    - start < end：同日窗口，如 12:00–14:00
    - start > end：跨午夜，如 21:00–07:00
    """
    sh, sm = _parse_hm(dnd_start)
    eh, em = _parse_hm(dnd_end)
    start_m = _to_minutes(sh, sm)
    end_m = _to_minutes(eh, em)
    if start_m == end_m:
        return False

    if now is None:
        now = datetime.now(_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=_TZ)
    else:
        now = now.astimezone(_TZ)

    cur = _to_minutes(now.hour, now.minute)
    if start_m < end_m:
        return start_m <= cur < end_m
    # 跨午夜
    return cur >= start_m or cur < end_m
