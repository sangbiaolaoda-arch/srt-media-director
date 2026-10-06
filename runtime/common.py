"""Shared constants, colors, fonts and IO helpers for the reference runtime.

This runtime is the *reference implementation* of the SRT Media Director skill.
It is deliberately dependency-light (Pillow only) so that `runtime/self_test.py`
can run in CI without a browser or a video encoder.
"""
import json
import os

from PIL import ImageFont

CANVAS_W, CANVAS_H = 1280, 720
FPS = 30
SAFE = 0.07  # safe-area margin as a fraction of the canvas

COLORS = {
    # v7.1：对齐用户参考帧（frame_01/02/03）的封闭调色板。
    "paper": "#F3F2EF",      # 画布底（warm grey）
    "panel": "#FAFAF8",      # 卡片 / 主体填充
    "ink": "#2B2B2B",        # 主描边 / 主文字（≈12:1 on bg）
    "neutral": "#8A8A86",    # 次级描边（≈3:1 on bg）
    "line": "#D3D2CD",       # 灰填充 / 分隔
    "negative": "#C4452B",   # 唯一强调砖红（参考帧 accent）
    "positive": "#5E8C7E",   # 安全 / 保护 / 通过
    "info": "#8A8A86",       # 图示灰（参考帧用单一次级灰）
    "warning": "#C4452B",
    "rose_fill": "#F0DED6",  # 玫色浅填充
    "rose_edge": "#DDB6A6",  # 玫色描边
    "diagram_green": "#C9C2B4",  # 示意图灰绿
}

# v5.0 米白纸感主题 —— 默认画布底色 #F4EFE6。语义颜色保持 COLORS 不变
# （negative/positive/info 承担语义，CORE-20），主题只决定背景、墨色与强调色。
# HTML 播放器与光栅渲染器共用同一份（双侧一致）。浅底上不再用黑遮幅，
# 暗角与颗粒降到最低，幽灵字/水印透明度上调以在浅底上仍可读。
THEME = {
    "name": "reference_flat",  # v7.1 对齐用户参考帧（frame_01/02/03）视觉系统
    "bg_top": "#F3F2EF",      # 中性暖灰底（参考帧实测 bg）
    "bg_bottom": "#F3F2EF",   # 上下同色 = 纯色平底，无渐变
    "ink": "#2B2B2B",         # 主墨色：中性近黑（参考帧 ink，≈12:1）
    "muted": "#6B6B67",       # 次要文字（参考帧 text-mid，≈4.9:1）
    "text_negative": "#A83A22",  # 主体语义文字：风险/否定（砖红压深保可读）
    "text_positive": "#3E6B5C",  # 主体语义文字：安全/正向
    "text_info": "#5C5C58",      # 主体语义文字：图示灰（压深保可读）
    "accent": "#C4452B",      # 唯一强调砖红（参考帧 accent）
    "rose_fill": "#F0DED6",   # 玫色浅填充
    "rose_edge": "#DDB6A6",   # 玫色描边
    "diagram": "#8A8A86",     # 图示灰（连接线 / 节点，参考帧次级灰）
    "diagram_green": "#C9C2B4",  # 图示灰绿
    "vignette": 0.0,          # 纯平底，无暗角
    "grain": 0,               # 纯平底，无颗粒
    "letterbox": 0.0,
    "ghost_alpha": 0.0,
    "motif_watermark": 0.0,
}

_FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_FONT_SERIF_BOLD = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
_font_cache = {}


def font(size, bold=False, serif=False):
    """CJK-capable font loader with a graceful fallback.

    serif=True 加载衬线（宋体类）——标题/金句/大字的电影感排版用。
    """
    key = (int(size), bool(bold), bool(serif))
    if key not in _font_cache:
        path = None
        cands = ([_FONT_SERIF_BOLD] if serif else []) + \
                ([_FONT_BOLD] if bold else []) + [_FONT_REG]
        for cand in cands:
            if os.path.exists(cand):
                path = cand
                break
        _font_cache[key] = ImageFont.truetype(path, key[0]) if path else ImageFont.load_default()
    return _font_cache[key]

# 字体常量与 _font_cache 已在文件上部（THEME 之后）定义，此处不重复；
# 旧的两参数 font() 已整体移除，统一由上方带 serif 参数的版本提供。


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def measure_text(text, size, bold=False):
    """Real text measurement — the basis of the Content Footprint Preflight."""
    f = font(size, bold)
    bbox = f.getbbox(text)
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def format_compact_num(x, sig=3):
    """Bounded, human-legible numeric label shared by every on-canvas producer.

    Root cause behind the d01-gdp layout overflow: producers formatted numbers
    with ``"%g"``, whose precision (6 significant digits) is unbounded in length,
    so ``after/before = 0.3088235…`` became the 8-glyph ``×0.308824`` — wider than
    the fixed ``delta`` region.  A human-readable annotation never needs that
    precision, so we bound it generically here instead of special-casing a case.

    Examples: 0.3088235 -> "0.31"; 6.8 -> "6.8"; 45 -> "45"; 99.99 -> "100".
    """
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    if x != x or x in (float("inf"), float("-inf")):
        return "0"
    if x == int(x):
        return str(int(x))
    ax = abs(x)
    if ax >= 100:
        dec = 0
    elif ax >= 10:
        dec = 1
    else:
        dec = 2
    s = ("%%.%df" % dec) % x
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def dump_json(obj, path):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- choreography / narrative shared constants ------------------------------

G_MIN_WAVE_GAP = 0.25  # seconds; entrance wave separation (GATE-G2)

_NARRATIVE_ORDER = ("hook", "explanation", "comparison", "turning_point",
                    "emphasis", "conclusion")


def narrative_function_rank(role):
    """Stable ordering of semantic roles along a narrative arc."""
    try:
        return _NARRATIVE_ORDER.index(role)
    except ValueError:
        return len(_NARRATIVE_ORDER)


# --- v4.4 分段情绪背景调色板（回应「背景颜色不好看 / 全片一个色」）-------------
# 每拍按字幕情绪选一套渐变（top/bottom/accent），渲染器与 HTML 播放器共用。
PALETTES = {
    # v7.1：统一中性暖灰底（#F3F2EF），情绪只体现在强调色上（参考帧配色）。
    "night": {"top": "#F3F2EF", "bottom": "#F3F2EF", "accent": "#8A8A86"},
    "warm":  {"top": "#F3F2EF", "bottom": "#F3F2EF", "accent": "#C4452B"},
    "cold":  {"top": "#F3F2EF", "bottom": "#F3F2EF", "accent": "#8A8A86"},
    "tense": {"top": "#F3F2EF", "bottom": "#F3F2EF", "accent": "#C4452B"},
    "calm":  {"top": "#F3F2EF", "bottom": "#F3F2EF", "accent": "#5E8C7E"},
}

# 关键词 → 情绪（命中即返回；顺序敏感，越靠前越优先）
_MOOD_WORDS = (
    ("calm", ("放下", "安静", "平静", "自己签", "算了", "不需要", "判完")),
    ("tense", ("赢", "仗", "拼", "看错", "不行", "无话可说", "恨", "失败")),
    ("cold", ("时间", "过去", "多年", "结案", "原地", "空气", "方向", "签字")),
    ("warm", ("承认", "回家", "自己", "那一刻", "挺厉害")),
)


def mood_palette(narration, semantic_role=None):
    """按字幕情绪/语义选背景调色板（night 为默认暖暗）。"""
    text = narration or ""
    for name, words in _MOOD_WORDS:
        if any(w in text for w in words):
            return name
    return "night"
