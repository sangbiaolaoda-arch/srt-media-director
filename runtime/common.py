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
    "paper": "#F7F4EE",
    "panel": "#FFFFFF",
    "ink": "#211D17",
    "neutral": "#8F887C",
    "line": "#C9C2B4",
    "negative": "#D64541",   # 危险 / 风险 / 失败
    "positive": "#2E9E63",   # 安全 / 保护 / 通过
    "info": "#3E7CB1",
    "warning": "#E08A2E",
}

# v4.2 电影感暗色主题 —— 情感/独白类内容的默认画布。语义颜色保持
# COLORS 不变（negative/positive/info 承担语义，CORE-20），主题只决定
# 背景、墨色与强调色。HTML 播放器与光栅渲染器共用同一份（双侧一致）。
THEME = {
    "name": "cinema",
    "bg_top": "#17130E",      # 渐变底：上
    "bg_bottom": "#241C12",   # 渐变底：下（略暖，像暗室里的暖光）
    "ink": "#F2E9D8",         # 主墨色：暖米白
    "muted": "#9A9081",       # 次要文字
    "accent": "#D4A94E",      # 强调金（keyword / 强调线 / 数字）
    "vignette": 0.42,         # 径向暗角强度（四角压暗比例）
    "grain": 5,               # 胶片颗粒强度（0-255 幅值）
    "letterbox": 0.04,        # 上下遮幅黑边占画布高度比例
    "ghost_alpha": 0.10,      # 幽灵大字基础透明度（暗底上的浅色淡字）
    "motif_watermark": 0.15,  # motif 背景水印透明度
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
    "night": {"top": "#12100C", "bottom": "#241C12", "accent": "#D4A94E"},
    "warm":  {"top": "#1A120B", "bottom": "#2E1C0E", "accent": "#E0A85C"},
    "cold":  {"top": "#0E1418", "bottom": "#16242C", "accent": "#6FB3C9"},
    "tense": {"top": "#160E12", "bottom": "#2C1418", "accent": "#C96F6F"},
    "calm":  {"top": "#10140F", "bottom": "#1C2418", "accent": "#9EC98A"},
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
