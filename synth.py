#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math, random, re, json, os  # <<< NEW: os
import unicodedata as ud
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Iterable, Set
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ================== 外觀 / 參數 ==================
TEXT_GRAY_14 = [
    "#000000","#141414","#282828","#3C3C3C","#505050",
    "#646464","#787878","#8C8C8C","#A0A0A0","#B4B4B4",
    "#C8C8C8","#DCDCDC","#F0F0F0"
]
GRAY_IDX_RANGE = (0, 8)
FONT_SIZE_RANGE = (26, 44)
HORIZ_CHAR_SPACING_RANGE = (0, 12)
VERT_CHAR_SPACING_RANGE  = (0, 12)

ASSUMED_DPI     = 96
BG_RANDOM_POS   = True
BG_ZOOM_JITTER  = (1.0, 1.15)
UNION_PAD_PT_RANGE = (0, 4)

ENABLE_BLUR       = True
BLUR_SIGMA_RANGE  = (0.2, 0.9)

DEBUG_BOXES_DEFAULT = False
BOX_JITTER_DEFAULT  = (0, 0)

# ================== 字重推斷（僅用於備用字體查找） ==================
WEIGHT_ORDER = [
    "thin","extralight","ultralight","light","book","regular","normal",
    "medium","semibold","demibold","bold","extrabold","ultrabold","black","heavy"
]
WEIGHT_INDEX: Dict[str,int] = {w:i for i,w in enumerate(WEIGHT_ORDER)}

def _infer_weight_idx(name: str) -> int:
    n = name.lower()
    n = n.replace("blk","black").replace("ultra","extra").replace("demi","semi")
    for w in WEIGHT_ORDER:
        if re.search(rf"(?:^|[^a-z]){w}(?:[^a-z]|$)", n):
            return WEIGHT_INDEX[w]
    return WEIGHT_INDEX["regular"]

# ================== 直排映射（渲染用，不影響 label） ==================
VERT_MAP = {
    "(": "︵", ")": "︶", "[": "﹇", "]": "﹈", "{": "︷", "}": "︸",
    "（": "︵", "）": "︶", "［": "﹇", "］": "﹈", "｛": "︷", "｝": "︸",
    "〈": "︿", "〉": "﹀", "《": "︽", "》": "︾", "「": "﹁", "」": "﹂",
    "『": "﹃", "』": "﹄", "【": "︻", "】": "︼", "〔": "︹", "〕": "︺",
    "—": "︱", "–": "︲", "_": "︳", "…": "︙",
}
VERT_BLOCKS = ((0xFE10,0xFE1F),(0xFE30,0xFE4F))
def _is_vertical_form(ch: str) -> bool:
    cp = ord(ch);  return any(a <= cp <= b for a,b in VERT_BLOCKS)

# ================== 小工具 ==================
def pt_to_px(pts: float, dpi: float = ASSUMED_DPI) -> int:
    return max(1, int(round(pts * dpi / 72.0)))

def list_fonts(font_dir: Path) -> List[Path]:
    fonts = [p for p in font_dir.glob("*") if p.suffix.lower() in (".ttf", ".otf")]
    fonts.sort(key=lambda p: p.name.lower())  # <<< NEW: 固定順序
    return fonts

def load_background(bg_dir: Path, size: Tuple[int, int]) -> Image.Image:
    bgs = [p for p in bg_dir.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")]
    bgs.sort(key=lambda p: p.name.lower())  # <<< NEW: 固定順序
    out_w, out_h = size
    if not bgs:
        return Image.new("RGB", size, "white")
    bg = Image.open(random.choice(bgs)).convert("RGB")
    bg = ImageOps.exif_transpose(bg)
    s_cover = max(out_w / bg.width, out_h / bg.height)
    s = s_cover * random.uniform(*BG_ZOOM_JITTER)
    new_w = max(out_w, int(math.ceil(bg.width * s)))
    new_h = max(out_h, int(math.ceil(bg.height * s)))
    bg = bg.resize((new_w, new_h), Image.BICUBIC)
    if BG_RANDOM_POS and (new_w > out_w or new_h > out_h):
        left = random.randint(0, new_w - out_w) if new_w > out_w else 0
        top  = random.randint(0, new_h - out_h) if new_h > out_h else 0
    else:
        left = (new_w - out_w) // 2;  top = (new_h - out_h) // 2
    return bg.crop((left, top, left + out_w, top + out_h))

# ================== font coverage / 快取 ==================
try:
    from fontTools.ttLib import TTFont
except Exception:
    TTFont = None
_COVERAGE_CACHE: Dict[str,set] = {}
_FONT_OBJ_CACHE: Dict[Tuple[str,int], ImageFont.FreeTypeFont] = {}

def _get_font_coverage(path: Path) -> Set[int]:
    if TTFont is None:
        raise RuntimeError("請先安裝 fonttools： pip install fonttools")
    key = str(path.resolve())
    if key in _COVERAGE_CACHE:
        return _COVERAGE_CACHE[key]
    tt = TTFont(str(path), lazy=True)
    cps: Set[int] = set()
    if "cmap" in tt:
        for table in tt["cmap"].tables:
            if getattr(table, "isUnicode", lambda: True)():
                cps.update(table.cmap.keys())
    tt.close()
    _COVERAGE_CACHE[key] = cps
    return cps

def _font_supports_char(path: Path, ch: str) -> bool:
    return ord(ch) in _get_font_coverage(path)

def _load_font_cached(path: Path, size: int) -> ImageFont.FreeTypeFont:
    key = (str(path.resolve()), size)
    if key not in _FONT_OBJ_CACHE:
        _FONT_OBJ_CACHE[key] = ImageFont.truetype(str(path), size=size)
    return _FONT_OBJ_CACHE[key]

# ================== 直排映射（帶最後備援檢查） ==================
def map_to_vertical_forms(text: str, font_chain: List[Path], last_resort: Path) -> str:
    out = []
    for ch in text:
        if _is_vertical_form(ch):
            out.append(ch); continue
        alt = VERT_MAP.get(ch)
        if not alt:
            out.append(ch); continue
        if any(_font_supports_char(p, alt) for p in font_chain) or _font_supports_char(last_resort, alt):
            out.append(alt)
        else:
            out.append(ch)
    return "".join(out)

def map_to_vertical_forms_for_check(text: str, font_chain: List[Path], last_resort: Path) -> str:
    return map_to_vertical_forms(text, font_chain, last_resort)

# ================== 測量 ==================
def measure_bbox(font: ImageFont.FreeTypeFont, ch: str):
    tmp = Image.new("L", (4, 4))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), ch, font=font)
    if not bbox:
        l = t = 0
        approx_w = max(1, int(round(font.size * 0.6)))
        approx_h = max(1, int(round(font.size * 1.0)))
        r = l + approx_w
        b = t + approx_h
    else:
        l, t, r, b = bbox
        if l == r: r = l + 1
        if t == b: b = t + 1
    try:
        adv = font.getlength(ch)
    except Exception:
        try: adv = d.textlength(ch, font=font)
        except Exception: adv = max(1, r - l)
    return adv, l, t, r, b

# ================== 版面規劃 / 渲染 ==================
@dataclass
class GlyphPlan:
    ch: str
    font: ImageFont.FreeTypeFont
    font_path: Path
    box_x: float; box_y: float
    box_w: int;   box_h: int
    l: int; t: int; r: int; b: int

@dataclass
class LayoutPlan:
    glyphs: List[GlyphPlan]
    union_l: float; union_t: float; union_r: float; union_b: float
    pad_l: int; pad_t: int; pad_r: int; pad_b: int

def plan_layout(
    text: str,
    font_size: int,
    orientation: str,
    char_spacing: int,
    fallback_chain: List[Path],
    box_jitter: Tuple[int,int],
    union_pad_pt_range: Tuple[int,int],
    last_resort: Path,
) -> LayoutPlan:
    primary_path = fallback_chain[0]

    def choose_font_for_char(ch: str) -> Tuple[ImageFont.FreeTypeFont, Path]:
        if _font_supports_char(primary_path, ch):
            return _load_font_cached(primary_path, font_size), primary_path
        for p in fallback_chain[1:]:
            if _font_supports_char(p, ch):
                return _load_font_cached(p, font_size), p
        return _load_font_cached(last_resort, font_size), last_resort

    ink_ws, ink_hs, fonts_for_char = [], [], []
    for ch in text:
        f, p = choose_font_for_char(ch)
        _, l, t, r, b = measure_bbox(f, ch)
        ink_w, ink_h = int(r - l), int(b - t)
        ink_ws.append(max(1, ink_w));  ink_hs.append(max(1, ink_h));  fonts_for_char.append((f, p, l, t, r, b))

    glyphs: List[GlyphPlan] = []
    if orientation == "horizontal":
        line_h = max(ink_hs) if ink_hs else 1
        x = 0.0
        for ch, (f, p, l, t, r, b), iw, ih in zip(text, fonts_for_char, ink_ws, ink_hs):
            box_w, box_h = iw, line_h
            jx = random.randint(-box_jitter[0], box_jitter[0]) if box_jitter[0] else 0
            jy = random.randint(-box_jitter[1], box_jitter[1]) if box_jitter[1] else 0
            glyphs.append(GlyphPlan(ch, f, p, x+jx, 0+jy, box_w, box_h, l,t,r,b))
            x += box_w + char_spacing
    else:
        col_w = max(ink_ws) if ink_ws else 1
        y = 0.0
        for ch, (f, p, l, t, r, b), iw, ih in zip(text, fonts_for_char, ink_ws, ink_hs):
            box_w, box_h = col_w, ih
            jx = random.randint(-box_jitter[0], box_jitter[0]) if box_jitter[0] else 0
            jy = random.randint(-box_jitter[1], box_jitter[1]) if box_jitter[1] else 0
            glyphs.append(GlyphPlan(ch, f, p, 0+jx, y+jy, box_w, box_h, l,t,r,b))
            y += box_h + char_spacing

    union_l = min((g.box_x for g in glyphs), default=0.0)
    union_t = min((g.box_y for g in glyphs), default=0.0)
    union_r = max((g.box_x + g.box_w for g in glyphs), default=1.0)
    union_b = max((g.box_y + g.box_h for g in glyphs), default=1.0)

    lo, hi = union_pad_pt_range
    pad_l = pt_to_px(random.randint(lo, hi))
    pad_r = pt_to_px(random.randint(lo, hi))
    pad_t = pt_to_px(random.randint(lo, hi))
    pad_b = pt_to_px(random.randint(lo, hi))

    return LayoutPlan(glyphs, union_l, union_t, union_r, union_b, pad_l, pad_t, pad_r, pad_b)

def render_layout(layout: LayoutPlan, text_color: str, last_resort: Path, debug_boxes: bool = False) -> Image.Image:
    W = int(math.ceil(layout.union_r - layout.union_l) + layout.pad_l + layout.pad_r)
    H = int(math.ceil(layout.union_b - layout.union_t) + layout.pad_t + layout.pad_b)
    img = Image.new("RGBA", (max(1, W), max(1, H)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for p in layout.glyphs:
        bx = layout.pad_l + (p.box_x - layout.union_l)
        by = layout.pad_t + (p.box_y - layout.union_t)
        anchor_x = bx + (p.box_w - (p.r - p.l)) / 2 - p.l
        anchor_y = by + (p.box_h - (p.b - p.t)) / 2 - p.t
        d.text((anchor_x, anchor_y), p.ch, font=p.font, fill=text_color)
        crop_box = (int(bx), int(by), int(bx + p.box_w), int(by + p.box_h))
        region = img.crop(crop_box)
        if not region.getbbox():
            print(f"[WARN] 字元 '{p.ch}' (U+{ord(p.ch):04X}) 在字體 {p.font_path.name} 渲染失敗 (空字元)。嘗試使用最後備援字體重新渲染。")
            try:
                last_resort_font = _load_font_cached(last_resort, p.font.size)
                d.text((anchor_x, anchor_y), p.ch, font=last_resort_font, fill=text_color)
            except Exception as e:
                print(f"[ERROR] 使用最後備援字體渲染 '{p.ch}' 失敗: {e}")

    if debug_boxes:
        for p in layout.glyphs:
            bx = layout.pad_l + (p.box_x - layout.union_l)
            by = layout.pad_t + (p.box_y - layout.union_t)
            d.rectangle([int(bx), int(by), int(bx + p.box_w), int(by + p.box_h)],
                        outline=(255, 0, 0, 192), width=1)
        union_w = layout.union_r - layout.union_l
        union_h = layout.union_b - layout.union_t
        d.rectangle([int(layout.pad_l), int(layout.pad_t),
                     int(layout.pad_l + union_w), int(layout.pad_t + union_h)],
                    outline=(0, 255, 0, 192), width=2)
    return img

def compose_tight_with_texture(text_rgba: Image.Image, bg_dir: Path) -> Image.Image:
    tw, th = text_rgba.size
    bg = load_background(bg_dir, (tw, th))
    out = bg.convert("RGBA")
    out.alpha_composite(text_rgba, (0, 0))
    return out

# ================== Preflight：確保 100% 可渲染 ==================
AUTO_LAST_RESORT_PATTERNS = [
    "notosanscjk","noto sans cjk","sourcehansans","source han sans",
    "notoserifcjk","sourcehanserif","source han serif"
]

def resolve_font_in_dir(name_or_path: Optional[str], fonts_dir: Path, fonts: Optional[List[Path]] = None) -> Optional[Path]:
    if not name_or_path: return None
    raw = name_or_path.strip(); p = Path(raw)
    if p.exists(): return p
    if fonts is None: fonts = list_fonts(fonts_dir)
    key = raw.lower()
    for q in fonts:
        if q.name.lower()==key or q.stem.lower()==key: return q
    matches = [q for q in fonts if key in q.name.lower()]
    if matches:
        matches.sort(key=lambda x: (abs(_infer_weight_idx(x.name)-WEIGHT_INDEX["regular"]), x.name.lower()))
        return matches[0]
    for ext in (".ttf",".otf"):
        cand = fonts_dir / f"{raw}{ext}"
        if cand.exists(): return cand
    return None

def auto_pick_last_resort(fonts_dir: Path, fonts: List[Path]) -> Optional[Path]:
    cands = [p for p in fonts if any(k in p.name.lower() for k in AUTO_LAST_RESORT_PATTERNS)]
    if not cands: return None
    cands.sort(key=lambda p: (abs(_infer_weight_idx(p.name)-WEIGHT_INDEX["regular"]), p.name.lower()))
    return cands[0]

def gather_all_chars(lines: Iterable[str], vertical: bool, fallback_chain: List[Path], last_resort: Path) -> Set[str]:
    s: Set[str] = set()
    for ln in lines:
        ln = ln.strip()
        if not ln: continue
        if vertical:
            ln_mapped = map_to_vertical_forms_for_check(ln, fallback_chain, last_resort)
            s.update(list(ln_mapped))
        else:
            s.update(list(ln))
    return s

def preflight_ensure_full_coverage(
    lines: List[str],
    vertical: bool,
    fonts_dir: Path,
    last_resort_font: Optional[str]
) -> Tuple[List[Path], Path]:
    all_fonts = list_fonts(fonts_dir)
    if not all_fonts:
        raise FileNotFoundError(f"No fonts found in {fonts_dir.resolve()}")
    last_resort_path = resolve_font_in_dir(last_resort_font, fonts_dir, all_fonts) if last_resort_font else auto_pick_last_resort(fonts_dir, all_fonts)
    if last_resort_path is None:
        raise RuntimeError("找不到最後備援字體。請在 fonts/ 放入高覆蓋 CJK（Noto/SourceHan），或用 --last_resort_font 指定。")
    _ = _get_font_coverage(last_resort_path)
    for p in all_fonts: _ = _get_font_coverage(p)
    charset = gather_all_chars(lines, vertical, all_fonts, last_resort_path)
    missing: Set[str] = set()
    for ch in charset:
        if any(_font_supports_char(p, ch) for p in all_fonts) or _font_supports_char(last_resort_path, ch):
            continue
        missing.add(ch)
    if missing:
        examples = "".join(sorted(list(missing))[:80])
        raise RuntimeError(
            f"Preflight 失敗：仍有 {len(missing)} 個字元未被任何字體覆蓋。\n"
            f"缺字範例（最多 80）：{examples}\n"
            f"請安裝/指定更高覆蓋率的最後備援字體（--last_resort_font），或補充 fonts/。"
        )
    return all_fonts, last_resort_path

# ================== 單張生成 ==================
def synth_one(
    text_raw: str,
    orientation: str,
    all_fonts: List[Path],
    last_resort: Path,
    bgs_dir="backgrounds",
    debug_boxes: bool = DEBUG_BOXES_DEFAULT,
    box_jitter: Tuple[int,int] = BOX_JITTER_DEFAULT,
    union_pad_pt_range: Tuple[int,int] = UNION_PAD_PT_RANGE,
) -> Image.Image:
    primary_font = random.choice(all_fonts)
    other_fonts = [f for f in all_fonts if f != primary_font]
    random.shuffle(other_fonts)
    fallback_chain = [primary_font] + other_fonts

    render_text = text_raw
    if orientation == "vertical":
        render_text = map_to_vertical_forms(render_text, fallback_chain, last_resort)

    char_spacing = random.randint(*(HORIZ_CHAR_SPACING_RANGE if orientation=="horizontal" else VERT_CHAR_SPACING_RANGE))
    font_size    = random.randint(*FONT_SIZE_RANGE)

    layout = plan_layout(
        text=render_text, font_size=font_size,
        orientation=orientation, char_spacing=char_spacing,
        fallback_chain=fallback_chain, box_jitter=box_jitter,
        union_pad_pt_range=union_pad_pt_range, last_resort=last_resort
    )

    text_color = TEXT_GRAY_14[random.randint(*GRAY_IDX_RANGE)]
    text_rgba = render_layout(layout, text_color, last_resort, debug_boxes)
    out = compose_tight_with_texture(text_rgba, Path(bgs_dir))

    if ENABLE_BLUR:
        s = random.uniform(*BLUR_SIGMA_RANGE)
        if s > 0: out = out.filter(ImageFilter.GaussianBlur(radius=s))
    return out.convert("RGB")

# ================== CLI ==================
def _parse_pair(s: str, typ=int, default=(0,0)) -> Tuple[int,int]:
    try:
        a,b = s.split(",");  return typ(a), typ(b)
    except Exception:
        return default

def main():
    import argparse
    p = argparse.ArgumentParser(description="Single-line OCR synth with random primary font + per-glyph fallback.")
    p.add_argument("--lines", type=str, default="lines.txt")
    p.add_argument("--fonts_dir", type=str, default="fonts")
    p.add_argument("--bgs_dir", type=str, default="backgrounds")
    p.add_argument("--out_dir", type=str, default="out")
    p.add_argument("--manifest", type=str, default="", help="JSONL（預設：out_dir/manifest.jsonl）")
    p.add_argument("--n_per_line", type=int, default=1)
    p.add_argument("--vertical", action="store_true")
    p.add_argument("--max_lines", type=int, default=None)
    p.add_argument("--debug_boxes", dest="debug_boxes", action="store_true")
    p.add_argument("--no_debug_boxes", dest="debug_boxes", action="store_false")
    p.set_defaults(debug_boxes=DEBUG_BOXES_DEFAULT)
    p.add_argument("--box_jitter", type=str, default=f"{BOX_JITTER_DEFAULT[0]},{BOX_JITTER_DEFAULT[1]}",
                   help="每字框隨機偏移 (max_jx,max_jy)，例如 2,2；0,0 關閉")
    p.add_argument("--union_pad", type=str, default=f"{UNION_PAD_PT_RANGE[0]},{UNION_PAD_PT_RANGE[1]}",
                   help="綠框外四邊隨機邊距（pt），min,max；最小可 0")
    p.add_argument("--last_resort_font", type=str, default="", help="最後備援字體（路徑或 fonts 內名稱/關鍵字）。未指定會自動從 fonts/ 嘗試挑 Noto/SourceHan。")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducible synthesis")  # <<< NEW
    args = p.parse_args()

    # <<< NEW: 固定隨機性（在任何隨機操作前）
    if args.seed is not None:
        os.environ["PYTHONHASHSEED"] = str(args.seed)
        random.seed(args.seed)

    outdir = Path(args.out_dir); outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else outdir / "manifest.jsonl"

    lines = [ln.strip() for ln in Path(args.lines).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.max_lines is not None:
        lines = lines[:args.max_lines]
    vertical = bool(args.vertical)
    box_jitter  = _parse_pair(args.box_jitter, int, BOX_JITTER_DEFAULT)
    union_pad_pt = _parse_pair(args.union_pad, int, UNION_PAD_PT_RANGE)
    debug_boxes = args.debug_boxes

    all_fonts, last_resort = preflight_ensure_full_coverage(
        lines=lines, vertical=vertical, fonts_dir=Path(args.fonts_dir),
        last_resort_font=(args.last_resort_font or None)
    )

    with open(manifest_path, "w", encoding="utf-8") as mf:
        for i, text_raw in enumerate(lines):
            for k in range(args.n_per_line):
                img = synth_one(
                    text_raw=text_raw,
                    orientation=("vertical" if vertical else "horizontal"),
                    all_fonts=all_fonts,
                    last_resort=last_resort,
                    bgs_dir=args.bgs_dir,
                    debug_boxes=debug_boxes,
                    box_jitter=box_jitter,
                    union_pad_pt_range=union_pad_pt,
                )
                fn = f"{i:06d}_{'v' if vertical else 'h'}_{k}.jpg"
                fpath = outdir / fn
                img.save(fpath, quality=95)
                mf.write(json.dumps({"image_path": str(fpath), "label": text_raw}, ensure_ascii=False) + "\n")

    print(f"Done. Saved images to {outdir.resolve()}, manifest -> {manifest_path.resolve()}")

if __name__ == "__main__":
    main()
