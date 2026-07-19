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

def _assets_dir() -> Path:
    """解析通知卡片资源目录（字体 / LOGO）。
    查找策略（修复「中文有、拉丁无」的关键路径问题）：
    1. 环境变量 FLYMAIL_NOTIFY_ASSETS（飞牛 cmd/main 会显式注入）
    2. 可执行文件 / argv0 旁的 notify-assets/（正式 FPK 唯一字体位置）
    3. 本模块旁 assets/（本地开发）
    4. 其它兼容路径
    重要：必须优先选择「含字体文件」的目录。
    旧逻辑只要有 icon.png 就返回，可能误选只有图标、没有 OTF 的目录，
    随后落到系统残缺 CJK 字体——中文能显示，数字/字母变成空白。
    """
    import sys
    candidates: List[Path] = []
    env = (os.environ.get("FLYMAIL_NOTIFY_ASSETS") or "").strip()
    if env:
        candidates.append(Path(env))
    try:
        exe_dir = Path(sys.executable).resolve().parent
        argv0_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else exe_dir
        for base in (exe_dir, argv0_dir):
            for rel in (
                Path("notify-assets"),
                Path("assets"),
                Path("services") / "notify" / "assets",
            ):
                p = base / rel
                if p not in candidates:
                    candidates.append(p)
    except Exception:
        pass
    mod_assets = Path(__file__).resolve().parent / "assets"
    if mod_assets not in candidates:
        candidates.append(mod_assets)
    # 1) 优先：目录内有内置字体
    for d in candidates:
        if (d / "SourceHanSansSC-Regular.otf").is_file():
            return d
        if (d / "NotoSansSC-Regular.otf").is_file():
            return d
        if (d / "wqy-microhei.ttc").is_file():
            return d
    # 2) 其次：仅有图标（仅供 LOGO 查找，字体另寻）
    for d in candidates:
        if (d / "icon.png").is_file():
            return d
    return candidates[0] if candidates else mod_assets

def _builtin_font_paths() -> List[Path]:
    """内置字体文件的全部可能路径（不依赖 _assets_dir 的「首个命中」）。"""
    import sys
    names = (
        "SourceHanSansSC-Regular.otf",
        "NotoSansSC-Regular.otf",
        "wqy-microhei.ttc",
    )
    dirs: List[Path] = []
    env = (os.environ.get("FLYMAIL_NOTIFY_ASSETS") or "").strip()
    if env:
        dirs.append(Path(env))
    try:
        exe_dir = Path(sys.executable).resolve().parent
        argv0_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else exe_dir
        for base in (exe_dir, argv0_dir):
            dirs.extend(
                [
                    base / "notify-assets",
                    base / "assets",
                    base / "services" / "notify" / "assets",
                ]
            )
    except Exception:
        pass
    dirs.append(Path(__file__).resolve().parent / "assets")
    out: List[Path] = []
    seen = set()
    for d in dirs:
        for name in names:
            fp = d / name
            key = str(fp)
            if key in seen:
                continue
            seen.add(key)
            out.append(fp)
    return out

def _font_candidates(bold: bool = False) -> List[Path]:
    """字体候选：内置中文字体优先，再回退系统字体。
    飞牛正式环境（Nuitka onefile）系统通常无完整中文字体；
    正式包字体位于可执行文件旁 notify-assets/（仅一份，不内嵌进二进制）。
    若全部失败回退 Pillow 默认位图字体，中文会显示为方框（tofu）。
    """
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    fonts: List[Path] = list(_builtin_font_paths())
    if bold:
        fonts += [
            windir / "Fonts" / "msyhbd.ttc",
            windir / "Fonts" / "msyh.ttc",
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
            Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
            # 西文兜底（bold 场景也补上，避免数字/字母空白）
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]
    else:
        fonts += [
            windir / "Fonts" / "msyh.ttc",
            windir / "Fonts" / "msyhbd.ttc",
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
            Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
            # 西文兜底
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            windir / "Fonts" / "arial.ttf",
            windir / "Fonts" / "segoeui.ttf",
        ]
    return fonts
_font_cache: Dict[Tuple[int, bool], ImageFont.ImageFont] = {}
_font_warn_once = False
_font_path_logged = False
# 主字体 + 西文回退字体（当主字体缺拉丁字形时按字符混排）
_mixed_font_cache: Dict[Tuple[int, bool], Tuple[ImageFont.ImageFont, Optional[ImageFont.ImageFont]]] = {}

def _probe_font_coverage(font: ImageFont.ImageFont) -> Tuple[bool, bool]:
    """探测字体是否具备可用的拉丁 / CJK 字形。
    返回 (has_latin, has_cjk)。
    某些残缺 CJK 字体对缺字返回零宽，会导致「中文正常、数字字母空白」。
    """
    has_latin = False
    has_cjk = False
    try:
        for ch in ("A", "a", "0", "@"):
            if hasattr(font, "getbbox"):
                bb = font.getbbox(ch)
            else:
                bb = None
            if bb is not None and (bb[2] - bb[0]) > 1 and (bb[3] - bb[1]) > 1:
                has_latin = True
                break
        for ch in ("中", "邮", "件"):
            if hasattr(font, "getbbox"):
                bb = font.getbbox(ch)
            else:
                bb = None
            if bb is not None and (bb[2] - bb[0]) > 1 and (bb[3] - bb[1]) > 1:
                has_cjk = True
                break
    except Exception:
        pass
    return has_latin, has_cjk

def _try_truetype(fp: Path, size: int) -> Optional[ImageFont.FreeTypeFont]:
    """尝试加载 TrueType/OpenType；兼容不同 Pillow 的 layout_engine 参数。"""
    if not fp.exists() or not fp.is_file():
        return None
    # 过小文件多半是损坏/指针文件，直接跳过
    try:
        if fp.stat().st_size < 1024:
            return None
    except Exception:
        return None
    attempts = []
    # 优先 BASIC：避免个别环境 RAQM/HarfBuzz 对 CFF OTF 拉丁字形异常
    layout = getattr(ImageFont, "Layout", None)
    if layout is not None and hasattr(layout, "BASIC"):
        attempts.append({"size": size, "index": 0, "layout_engine": layout.BASIC})
    attempts.append({"size": size, "index": 0})
    for kwargs in attempts:
        try:
            return ImageFont.truetype(str(fp), **kwargs)
        except TypeError:
            try:
                return ImageFont.truetype(str(fp), size=size, index=0)
            except Exception:
                continue
        except Exception:
            continue
    return None

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载可渲染中文的 TrueType/OpenType 字体；失败时记录一次警告。
    优先选择「同时覆盖拉丁 + CJK」的字体，避免数字/字母空白。
    """
    global _font_warn_once, _font_path_logged
    key = (size, bold)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    best_cjk_only: Optional[Tuple[ImageFont.ImageFont, Path]] = None
    chosen: Optional[ImageFont.ImageFont] = None
    chosen_path: Optional[Path] = None
    for fp in _font_candidates(bold=bold):
        font = _try_truetype(fp, size)
        if font is None:
            continue
        has_latin, has_cjk = _probe_font_coverage(font)
        if has_latin and has_cjk:
            chosen, chosen_path = font, fp
            break
        if has_cjk and best_cjk_only is None:
            best_cjk_only = (font, fp)
    if chosen is None and best_cjk_only is not None:
        # 退而求其次：至少保证中文，后续混排时用西文回退字体补拉丁
        chosen, chosen_path = best_cjk_only
    if chosen is not None:
        _font_cache[key] = chosen
        if not _font_path_logged:
            _font_path_logged = True
            try:
                import logging
                has_latin, has_cjk = _probe_font_coverage(chosen)
                logging.getLogger("flymail.notify.image_card").info(
                    "通知卡片字体: path=%s size=%s bold=%s latin=%s cjk=%s",
                    str(chosen_path) if chosen_path else "?",
                    size,
                    bold,
                    has_latin,
                    has_cjk,
                )
            except Exception:
                pass
        return chosen
    if not _font_warn_once:
        _font_warn_once = True
        try:
            import logging
            logging.getLogger("flymail.notify.image_card").warning(
                "通知卡片未找到可用中文字体，将使用 Pillow 默认字体（中文可能显示为方框）。"
                "请确认 app/server/notify-assets/ 或 services/notify/assets/ 含 SourceHanSansSC-Regular.otf；"
                "飞牛环境可检查 FLYMAIL_NOTIFY_ASSETS 是否指向该目录。"
            )
        except Exception:
            pass
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font

def _load_latin_fallback(size: int) -> Optional[ImageFont.ImageFont]:
    """加载西文回退字体（主字体缺拉丁时使用）。"""
    cached = _font_cache.get((-size - 1, False))  # 特殊键：负 size 标记 latin fallback
    if cached is not None:
        return cached
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    paths: List[Path] = []
    # 可选：notify-assets / assets 旁路西文字体
    for d in {fp.parent for fp in _builtin_font_paths()}:
        paths.append(d / "DejaVuSans.ttf")
        paths.append(d / "LiberationSans-Regular.ttf")
    paths += [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
        windir / "Fonts" / "arial.ttf",
        windir / "Fonts" / "segoeui.ttf",
        windir / "Fonts" / "calibri.ttf",
        windir / "Fonts" / "tahoma.ttf",
    ]
    for fp in paths:
        font = _try_truetype(fp, size)
        if font is None:
            continue
        has_latin, _ = _probe_font_coverage(font)
        if has_latin:
            _font_cache[(-size - 1, False)] = font
            return font
    return None

def _glyph_ok(font: ImageFont.ImageFont, ch: str) -> bool:
    """字符在该字体下是否有正宽度字形。"""
    if not ch or ch.isspace():
        return True
    try:
        if hasattr(font, "getbbox"):
            bb = font.getbbox(ch)
            if bb is None:
                return False
            return (bb[2] - bb[0]) > 0 and (bb[3] - bb[1]) > 0
    except Exception:
        return False
    return True

def _fonts_for_draw(size: int, bold: bool = False) -> Tuple[ImageFont.ImageFont, Optional[ImageFont.ImageFont]]:
    """返回 (主字体, 西文回退字体|None)。主字体已覆盖拉丁时回退为 None。"""
    key = (size, bold)
    cached = _mixed_font_cache.get(key)
    if cached is not None:
        return cached
    primary = _load_font(size, bold=bold)
    has_latin, _ = _probe_font_coverage(primary)
    fallback = None if has_latin else _load_latin_fallback(size)
    _mixed_font_cache[key] = (primary, fallback)
    return primary, fallback

def _measure_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    latin_font: Optional[ImageFont.ImageFont] = None,
) -> Tuple[int, int]:
    """测量文本宽高；若提供西文回退则按字符混排宽度累加。"""
    if not text:
        return 0, 0
    if latin_font is None:
        return _text_size(draw, text, font)
    w = 0
    h = 0
    for ch in text:
        use = font if _glyph_ok(font, ch) else (latin_font if _glyph_ok(latin_font, ch) else font)
        cw, chh = _text_size(draw, ch, use)
        w += cw
        h = max(h, chh)
    return w, h

def _draw_text_mixed(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill,
    latin_font: Optional[ImageFont.ImageFont] = None,
) -> None:
    """绘制文本；主字体缺字形时用西文回退，避免数字/字母空白。"""
    if not text:
        return
    if latin_font is None:
        draw.text(xy, text, font=font, fill=fill)
        return
    x, y = xy
    buf = ""
    buf_font = font

    def flush() -> None:
        nonlocal x, buf, buf_font
        if not buf:
            return
        draw.text((x, y), buf, font=buf_font, fill=fill)
        x += _text_size(draw, buf, buf_font)[0]
        buf = ""
    for ch in text:
        use = font if _glyph_ok(font, ch) else (latin_font if _glyph_ok(latin_font, ch) else font)
        if buf and use is not buf_font:
            flush()
        buf_font = use
        buf += ch
    flush()

def _icon_path() -> Optional[Path]:
    """定位项目 LOGO：内置资源 → 运行时 UI 目录 → 开发源码路径。"""
    here = Path(__file__).resolve()
    assets = _assets_dir()
    candidates: List[Path] = [
        assets / "icon.png",
    ]
    # 飞牛正式环境：cmd/main 注入 FLYMAIL_UI_DIR
    ui_env = (os.environ.get("FLYMAIL_UI_DIR") or "").strip()
    if ui_env:
        ui = Path(ui_env)
        candidates += [
            ui / "icon.png",
            ui / "icon-full.png",
            ui / "icons" / "icon-192.png",
            ui / "icons" / "icon-512.png",
        ]
    candidates += [
        here.parents[2] / "ui" / "icon.png",  # backend/ui/icon.png
        here.parents[2] / "ui" / "icon-full.png",
        here.parents[3] / "pages" / "icon.png",
        here.parents[3] / "flymail" / "ICON.PNG",
    ]
    for ip in candidates:
        if ip.exists() and ip.is_file():
            return ip
    return None

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]

def _wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
    latin_font: Optional[ImageFont.ImageFont] = None,
) -> List[str]:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines: List[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            w, _ = _measure_text(draw, trial, font, latin_font)
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
    f_brand, lat_brand = _fonts_for_draw(34, bold=True)
    f_subh, lat_subh = _fonts_for_draw(22, bold=False)
    f_subject, lat_subject = _fonts_for_draw(40, bold=True)
    f_label, lat_label = _fonts_for_draw(24, bold=True)
    f_val, lat_val = _fonts_for_draw(24, bold=False)
    f_body, lat_body = _fonts_for_draw(26, bold=False)
    pad_x = 44
    inner_w = CARD_W - pad_x * 2
    sub_lines = _wrap(pd, subject, f_subject, inner_w, lat_subject)[:MAX_SUBJECT_LINES]
    if len(_wrap(pd, subject, f_subject, inner_w, lat_subject)) > MAX_SUBJECT_LINES:
        # 末行加省略
        last = sub_lines[-1]
        while last and _measure_text(pd, last + "…", f_subject, lat_subject)[0] > inner_w:
            last = last[:-1]
        sub_lines[-1] = last + "…"
    body_lines: List[str] = []
    if body_preview:
        body_lines = _wrap(pd, body_preview, f_body, inner_w - 36, lat_body)[:MAX_BODY_LINES]
        full = _wrap(pd, body_preview, f_body, inner_w - 36, lat_body)
        if len(full) > MAX_BODY_LINES:
            last = body_lines[-1]
            while last and _measure_text(pd, last + "…", f_body, lat_body)[0] > inner_w - 36:
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
        vlines = _wrap(pd, val, f_val, max_vw, lat_val) or [""]
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
    _draw_text_mixed(draw, (128, 46), "飞邮", f_brand, (255, 255, 255, 255), lat_brand)
    _draw_text_mixed(draw, (128, 92), "新邮件通知", f_subh, (255, 255, 255, 220), lat_subh)
    # 正文区
    cy = HEADER_H + 34
    for line in sub_lines:
        _draw_text_mixed(draw, (pad_x, cy), line, f_subject, C["text"], lat_subject)
        cy += 50
    cy += 10
    draw.line((pad_x, cy, CARD_W - pad_x, cy), fill=C["line"], width=2)
    cy += 22
    label_w = 108
    for lab, val in rows:
        lab_disp = _label_display(lab)
        _draw_text_mixed(draw, (pad_x, cy), lab_disp, f_label, C["text2"], lat_label)
        max_vw = inner_w - label_w
        vlines = _wrap(draw, val, f_val, max_vw, lat_val) or [""]
        _draw_text_mixed(draw, (pad_x + label_w, cy), vlines[0], f_val, C["text"], lat_val)
        cy += 44
        for extra in vlines[1:]:
            _draw_text_mixed(draw, (pad_x + label_w, cy - 8), extra, f_val, C["text"], lat_val)
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
            _draw_text_mixed(draw, (pad_x + 22, ty), line, f_body, C["text2"], lat_body)
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
