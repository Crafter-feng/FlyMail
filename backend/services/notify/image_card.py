# -*- coding: utf-8 -*-
"""飞邮通知卡片图片渲染（方案 B · 蓝顶栏）。

设计要点：
- 仅输出卡片本体，无外围渐变/装饰边距（推送更干净）
- 版式与文字模式一致：主题 → 元信息 → 正文预览
- 无抄送时不绘制抄送行
- 高度随内容自适应，避免固定大留白
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from services.notify.render import _format_mail_date, _s

# 卡片宽度（推送预览友好）
CARD_W = 1000
# 圆角
CARD_RADIUS = 28
# 顶栏高度
HEADER_H = 148
# 正文最多行数（防止超长正文撑爆图片）
MAX_BODY_LINES = 8
# 主题最多行数
MAX_SUBJECT_LINES = 3

# 色板（对齐项目 macos 蓝）
C = {
    "text": (29, 29, 31),
    "text2": (110, 110, 115),
    "line": (0, 0, 0, 22),
    "body_bg": (245, 248, 255),
    "white": (255, 255, 255),
}


def _font_candidates(bold: bool = False) -> List[Path]:
    """系统字体候选（Windows / Linux 常见中文字体）。"""
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    fonts: List[Path] = []
    if bold:
        fonts += [
            windir / "Fonts" / "msyhbd.ttc",
            windir / "Fonts" / "msyh.ttc",
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        ]
    else:
        fonts += [
            windir / "Fonts" / "msyh.ttc",
            windir / "Fonts" / "msyhbd.ttc",
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    return fonts


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _font_candidates(bold=bold):
        if not p.exists():
            continue
        try:
            return ImageFont.truetype(str(p), size=size, index=0)
        except Exception:
            continue
    return ImageFont.load_default()


def _icon_path() -> Optional[Path]:
    """定位项目 LOGO。"""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "ui" / "icon.png",  # backend/ui/icon.png
        here.parents[2] / "ui" / "icon-full.png",
        here.parents[3] / "pages" / "icon.png",
        here.parents[3] / "flymail" / "ICON.PNG",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> List[str]:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines: List[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            w, _ = _text_size(draw, trial, font)
            if w <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines or [""]


def _meta_rows(event: Dict[str, Any]) -> List[Tuple[str, str]]:
    """组装元信息；无抄送不输出。"""
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


def _label_display(lab: str) -> str:
    if len(lab) == 2:
        return f"{lab[0]}　{lab[1]}"
    return lab


def _paste_icon(base: Image.Image, xy: Tuple[int, int], size: int, radius: int = 16) -> None:
    path = _icon_path()
    if not path:
        # 无图标时画白色圆角占位
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle(
            (xy[0], xy[1], xy[0] + size, xy[1] + size),
            radius=radius,
            fill=(255, 255, 255, 230),
        )
        base.alpha_composite(layer)
        return

    icon = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)

    # 轻微阴影
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (xy[0] + 2, xy[1] + 3, xy[0] + size + 2, xy[1] + size + 3),
        radius=radius,
        fill=(0, 0, 0, 50),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    base.alpha_composite(shadow)

    icon_m = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon_m.paste(icon, (0, 0), icon)
    base.paste(icon_m, xy, mask)


def _header_gradient(width: int, height: int) -> Image.Image:
    """蓝系竖直渐变顶栏。"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = img.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(0 * (1 - t) + 70 * t)
        g = int(100 * (1 - t) + 160 * t)
        b = int(230 * (1 - t) + 255 * t)
        for x in range(width):
            px[x, y] = (r, g, b, 255)
    return img


def _rounded_mask(w: int, h: int, radius: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    return mask


def render_notify_card(event: Dict[str, Any]) -> Image.Image:
    """根据事件渲染方案 B 通知卡片（仅卡片本体，透明圆角外）。"""
    event = event or {}
    subject = _s(event.get("subject"), "(无主题)")
    body_preview = str(event.get("body_preview") or "").strip()
    rows = _meta_rows(event)

    # 先用临时画布测量文本行数
    probe = Image.new("RGBA", (CARD_W, 200), (0, 0, 0, 0))
    pd = ImageDraw.Draw(probe)

    f_brand = _load_font(34, bold=True)
    f_subh = _load_font(22, bold=False)
    f_subject = _load_font(40, bold=True)
    f_label = _load_font(24, bold=True)
    f_val = _load_font(24, bold=False)
    f_body = _load_font(26, bold=False)

    pad_x = 44
    inner_w = CARD_W - pad_x * 2

    sub_lines = _wrap(pd, subject, f_subject, inner_w)[:MAX_SUBJECT_LINES]
    if len(_wrap(pd, subject, f_subject, inner_w)) > MAX_SUBJECT_LINES:
        # 末行加省略
        last = sub_lines[-1]
        while last and _text_size(pd, last + "…", f_subject)[0] > inner_w:
            last = last[:-1]
        sub_lines[-1] = last + "…"

    body_lines: List[str] = []
    if body_preview:
        body_lines = _wrap(pd, body_preview, f_body, inner_w - 36)[:MAX_BODY_LINES]
        full = _wrap(pd, body_preview, f_body, inner_w - 36)
        if len(full) > MAX_BODY_LINES:
            last = body_lines[-1]
            while last and _text_size(pd, last + "…", f_body)[0] > inner_w - 36:
                last = last[:-1]
            body_lines[-1] = last + "…"

    # 估算高度
    y = HEADER_H + 36
    y += len(sub_lines) * 50 + 16  # 主题
    y += 2 + 24  # 分割线
    # 元信息：每行可能换行
    meta_h = 0
    for lab, val in rows:
        max_vw = inner_w - 110
        vlines = _wrap(pd, val, f_val, max_vw) or [""]
        meta_h += 44 + max(0, len(vlines) - 1) * 34
    y += meta_h
    y += 8 + 2 + 22  # 下分割线
    if body_lines:
        box_h = 22 + len(body_lines) * 36 + 18
        y += box_h
    y += 40  # 底边距

    card_h = max(y, HEADER_H + 280)

    # 画卡片
    card = Image.new("RGBA", (CARD_W, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # 白底圆角
    draw.rounded_rectangle((0, 0, CARD_W - 1, card_h - 1), radius=CARD_RADIUS, fill=(*C["white"], 255))

    # 顶栏渐变（仅顶部，带上圆角）
    header = _header_gradient(CARD_W, HEADER_H + CARD_RADIUS)
    # 裁掉底部多余，保留顶栏高度
    header = header.crop((0, 0, CARD_W, HEADER_H))
    # 用上圆角遮罩
    hmask = Image.new("L", (CARD_W, HEADER_H), 0)
    ImageDraw.Draw(hmask).rounded_rectangle(
        (0, 0, CARD_W - 1, HEADER_H + CARD_RADIUS),
        radius=CARD_RADIUS,
        fill=255,
    )
    # 去掉下半圆角延伸区
    ImageDraw.Draw(hmask).rectangle((0, HEADER_H - 8, CARD_W, HEADER_H), fill=255)
    header_rgba = Image.new("RGBA", (CARD_W, HEADER_H), (0, 0, 0, 0))
    header_rgba.paste(header, (0, 0))
    header_rgba.putalpha(hmask)
    card.alpha_composite(header_rgba, (0, 0))

    # 顶栏内容
    _paste_icon(card, (40, 38), 68, radius=16)
    draw = ImageDraw.Draw(card)
    draw.text((128, 46), "飞邮", font=f_brand, fill=(255, 255, 255, 255))
    draw.text((128, 92), "新邮件通知", font=f_subh, fill=(255, 255, 255, 220))

    # 正文区
    cy = HEADER_H + 34
    for line in sub_lines:
        draw.text((pad_x, cy), line, font=f_subject, fill=C["text"])
        cy += 50
    cy += 10
    draw.line((pad_x, cy, CARD_W - pad_x, cy), fill=C["line"], width=2)
    cy += 22

    label_w = 108
    for lab, val in rows:
        lab_disp = _label_display(lab)
        draw.text((pad_x, cy), lab_disp, font=f_label, fill=C["text2"])
        max_vw = inner_w - label_w
        vlines = _wrap(draw, val, f_val, max_vw) or [""]
        draw.text((pad_x + label_w, cy), vlines[0], font=f_val, fill=C["text"])
        cy += 44
        for extra in vlines[1:]:
            draw.text((pad_x + label_w, cy - 8), extra, font=f_val, fill=C["text"])
            cy += 34

    cy += 4
    draw.line((pad_x, cy, CARD_W - pad_x, cy), fill=C["line"], width=2)
    cy += 20

    if body_lines:
        box_h = 22 + len(body_lines) * 36 + 18
        draw.rounded_rectangle(
            (pad_x, cy, CARD_W - pad_x, cy + box_h),
            radius=16,
            fill=(*C["body_bg"], 255),
        )
        # 左侧蓝色点缀条
        draw.rounded_rectangle(
            (pad_x, cy + 10, pad_x + 6, cy + box_h - 10),
            radius=3,
            fill=(0, 122, 255, 255),
        )
        ty = cy + 18
        for line in body_lines:
            draw.text((pad_x + 22, ty), line, font=f_body, fill=C["text2"])
            ty += 36

    # 整体圆角遮罩，去掉直角残留
    out = Image.new("RGBA", (CARD_W, card_h), (0, 0, 0, 0))
    out.paste(card, (0, 0), _rounded_mask(CARD_W, card_h, CARD_RADIUS))
    return out


def render_notify_card_png(event: Dict[str, Any], *, background: str = "white") -> bytes:
    """渲染为 PNG 字节。

    background:
      - white : 白底（兼容 Bark 等对透明图支持不一的渠道，默认）
      - transparent : 透明底圆角卡片
    """
    card = render_notify_card(event)
    if background == "transparent":
        img = card
    else:
        # 白底铺满，再贴卡片（卡片本身已是白底圆角，外围也白，更稳妥）
        img = Image.new("RGB", card.size, (255, 255, 255))
        img.paste(card, (0, 0), card)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
