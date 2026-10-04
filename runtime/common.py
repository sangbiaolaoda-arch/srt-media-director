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
    "paper": "#E9E4DE",
    "panel": "#FFFFFF",
    "ink": "#2B2723",
    "neutral": "#8F887C",
    "line": "#C9C2B4",
    "negative": "#E14D49",   # 危险 / 风险 / 失败（v6.0 参考图正红）
    "positive": "#5E8C7E",   # 安全 / 保护 / 通过
    "info": "#787C90",       # 图示蓝灰
    "warning": "#E08A2E",
    # v6.0 参考图（教科书信息图）新增语义通道
    "rose_fill": "#F0D8CC",  # 玫色浅填充（半透明红箱）
    "rose_edge": "#D8B4A8",  # 玫色描边
    "diagram_green": "#AFCAC1",  # 示意图绿灰
}

# v5.0 米白纸感主题 —— 默认画布底色 #F4EFE6。语义颜色保持 COLORS 不变
# （negative/positive/info 承担语义，CORE-20），主题只决定背景、墨色与强调色。
# HTML 播放器与光栅渲染器共用同一份（双侧一致）。浅底上不再用黑遮幅，
# 暗角与颗粒降到最低，幽灵字/水印透明度上调以在浅底上仍可读。
THEME = {
    "name": "textbook",       # v6.0 参考图（教科书式知识信息图）视觉系统
    "bg_top": "#E9E4DE",      # 暖米灰底（参考图实测 modal bg #E9E4DE）
    "bg_bottom": "#E9E4DE",   # 上下同色 = 纯色平底，无渐变
    "ink": "#26221E",         # 主墨色：暗暖黑（v6.1 加深，主体文字不再发灰）
    "muted": "#5F564B",       # 次要文字（v6.1 加深，浅底上可读）
    "text_negative": "#A8281F",  # 主体语义文字：风险/否定（正红压深，浅底够重）
    "text_positive": "#2E5A4A",  # 主体语义文字：安全/正向（压深保可读）
    "text_info": "#33374D",      # 主体语义文字：图示蓝灰（压深保可读）
    "accent": "#E14D49",      # 强调正红（参考图 red median #E14D49）
    "rose_fill": "#F0D8CC",   # 玫色浅填充（盒装标签底）
    "rose_edge": "#D8B4A8",   # 玫色描边
    "diagram": "#787C90",     # 图示蓝灰（连接线 / 节点）
    "diagram_green": "#AFCAC1",  # 图示绿灰
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
    # v6.0：统一暖米灰底（#E9E4DE），情绪只体现在强调色上（参考图配色）。
    "night": {"top": "#E9E4DE", "bottom": "#E9E4DE", "accent": "#787C90"},
    "warm":  {"top": "#E9E4DE", "bottom": "#E9E4DE", "accent": "#E14D49"},
    "cold":  {"top": "#E9E4DE", "bottom": "#E9E4DE", "accent": "#787C90"},
    "tense": {"top": "#E9E4DE", "bottom": "#E9E4DE", "accent": "#E14D49"},
    "calm":  {"top": "#E9E4DE", "bottom": "#E9E4DE", "accent": "#5E8C7E"},
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
