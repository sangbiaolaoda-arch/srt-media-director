"""entrance_library.py — 50 GSAP entrance specs for SRT Media Director.

Additive capability library. This is **not** the existing entrance planner
(``runtime/entrance_planner.py`` / ``motion_registry.py`` / ``skills/07``);
it is a richer, self-contained catalog of *entrance motions* authored in the
GSAP vocabulary so the front-end can drive them directly in the browser.

Each spec::

    {"id", "name", "kind",        # kind in {text, image, chart, "*"}
     "family", "semantic",         # why the motion exists (never decorative)
     "from": {...}, "to": {...},   # gsap property target pairs
     "ease", "duration", "stagger", "origin"}

Design rules (from the motion doctrine in skills/07 + the methodology doc):
  * every motion must answer "why does it appear this way";
  * entrance is a *consequence* of a state change, not decoration;
  * no "lazy breathing" — motion is event-driven, then holds.

Pure data; deterministic; no renderer dependency.
"""
from __future__ import annotations

from typing import Dict, List

_ENTRANCES: List[Dict] = []


def _e(eid, name, kind, family, semantic, frm, to, ease, dur, stagger, origin="50% 50%"):
    _ENTRANCES.append({
        "id": eid, "name": name, "kind": kind, "family": family,
        "semantic": semantic, "from": frm, "to": to,
        "ease": ease, "duration": dur, "stagger": stagger, "origin": origin,
    })


def _build() -> None:
    # --- universal entrances -------------------------------------------------
    _e("e01", "淡入", "*", "fade", "平缓出现，不抢焦点",
       {"opacity": 0}, {"opacity": 1}, "power2.out", 0.6, 0.0)
    _e("e02", "升入", "*", "rise", "自下而上浮现，表达生长",
       {"y": 36, "opacity": 0}, {"y": 0, "opacity": 1}, "power3.out", 0.7, 0.0)
    _e("e03", "垂入", "*", "sink", "自上而下落定，表达确立",
       {"y": -36, "opacity": 0}, {"y": 0, "opacity": 1}, "power3.out", 0.7, 0.0)
    _e("e04", "左侧滑入", "*", "slide", "从方位进入，表达来源",
       {"x": -64, "opacity": 0}, {"x": 0, "opacity": 1}, "power3.out", 0.65, 0.0)
    _e("e05", "右侧滑入", "*", "slide", "从方位进入，表达流向",
       {"x": 64, "opacity": 0}, {"x": 0, "opacity": 1}, "power3.out", 0.65, 0.0)
    _e("e06", "去模糊浮现", "*", "blur", "从失焦到聚焦，表达认知清晰",
       {"filter": "blur(12px)", "opacity": 0}, {"filter": "blur(0px)", "opacity": 1},
       "power2.out", 0.8, 0.0)
    _e("e07", "缩放进入", "*", "scale", "由小放大，表达强调/生长",
       {"scale": 0.6, "opacity": 0}, {"scale": 1, "opacity": 1},
       "power3.out", 0.6, 0.0)
    _e("e08", "弹入", "*", "pop", "回弹式出现，表达活力",
       {"scale": 0.5, "opacity": 0}, {"scale": 1, "opacity": 1}, "back.out(2.2)", 0.7, 0.0)
    _e("e09", "穿越缩放", "*", "zoom_through", "由大收至正常，表达进入场景",
       {"scale": 1.6, "opacity": 0}, {"scale": 1, "opacity": 1}, "power2.out", 0.75, 0.0)
    _e("e10", "对焦拉近", "*", "focus_pull", "焦点从远到近，表达锁定主体",
       {"scale": 1.08, "filter": "blur(10px)", "opacity": 0},
       {"scale": 1, "filter": "blur(0px)", "opacity": 1}, "power2.inOut", 0.85, 0.0)
    _e("e11", "旋转进入", "*", "rotate", "带旋转落位，表达动态建立",
       {"rotation": -12, "opacity": 0, "scale": 0.9},
       {"rotation": 0, "opacity": 1, "scale": 1}, "power3.out", 0.7, 0.0)
    _e("e12", "X 翻入", "*", "flip_x", "沿水平轴翻出，表达揭示",
       {"rotationX": -90, "opacity": 0}, {"rotationX": 0, "opacity": 1},
       "power2.out", 0.75, 0.0, origin="50% 0%")
    _e("e13", "Y 翻入", "*", "flip_y", "沿垂直轴翻出，表达揭示",
       {"rotationY": 90, "opacity": 0}, {"rotationY": 0, "opacity": 1},
       "power2.out", 0.75, 0.0, origin="0% 50%")
    _e("e14", "摆入", "*", "swing", "顶部悬挂式摆动落定",
       {"rotation": 14, "opacity": 0}, {"rotation": 0, "opacity": 1},
       "elastic.out(1, 0.5)", 0.9, 0.0, origin="50% 0%")
    _e("e15", "翻滚进入", "*", "tumble", "翻滚后落定，表达强劲建立",
       {"rotation": -40, "scale": 0.7, "opacity": 0},
       {"rotation": 0, "scale": 1, "opacity": 1}, "power3.out", 0.8, 0.0)
    # --- clip / mask wipes ---------------------------------------------------
    _e("e16", "右擦除揭示", "*", "wipe", "从左向右擦除揭示",
       {"clipPath": "inset(0 100% 0 0)"}, {"clipPath": "inset(0 0% 0 0)"},
       "power2.inOut", 0.7, 0.0)
    _e("e17", "左擦除揭示", "*", "wipe", "从右向左擦除揭示",
       {"clipPath": "inset(0 0 0 100%)"}, {"clipPath": "inset(0 0 0 0%)"},
       "power2.inOut", 0.7, 0.0)
    _e("e18", "上擦除揭示", "*", "wipe", "自下向上揭示",
       {"clipPath": "inset(100% 0 0 0)"}, {"clipPath": "inset(0% 0 0 0)"},
       "power2.inOut", 0.7, 0.0)
    _e("e19", "下擦除揭示", "*", "wipe", "自上向下揭示",
       {"clipPath": "inset(0 0 100% 0)"}, {"clipPath": "inset(0 0 0% 0)"},
       "power2.inOut", 0.7, 0.0)
    _e("e20", "幕布拉开", "*", "curtain", "从中线向两侧拉开",
       {"clipPath": "inset(0 50% 0 50%)"}, {"clipPath": "inset(0 0% 0 0%)"},
       "power2.inOut", 0.8, 0.0)
    _e("e21", "光圈张开", "*", "iris", "圆形光圈由小张开",
       {"clipPath": "circle(0% at 50% 50%)"}, {"clipPath": "circle(75% at 50% 50%)"},
       "power2.out", 0.8, 0.0)
    # --- text-specific -------------------------------------------------------
    _e("e22", "逐字 3D 翻入", "text", "split_chars", "逐字翻转，强调词句建立",
       {"opacity": 0, "rotationX": -80, "y": 20}, {"opacity": 1, "rotationX": 0, "y": 0},
       "power3.out", 0.5, 0.03, origin="50% 0%")
    _e("e23", "逐词错位入", "text", "split_words", "逐词错位浮现，表达节奏",
       {"opacity": 0, "y": 24}, {"opacity": 1, "y": 0}, "power3.out", 0.5, 0.06)
    _e("e24", "逐行升起", "text", "split_lines", "逐行升起，表达段落推进",
       {"opacity": 0, "y": 28}, {"opacity": 1, "y": 0}, "power3.out", 0.6, 0.12)
    _e("e25", "卡拉OK高亮", "text", "karaoke", "逐字点亮，表达朗读/强调",
       {"color": "rgba(255,255,255,0.25)"}, {"color": "#FFFFFF"},
       "none", 0.4, 0.05)
    _e("e26", "打字机", "text", "typewriter", "逐字吐出，表达实时生成",
       {"width": "0%"}, {"width": "100%"}, "steps(24)", 1.2, 0.0)
    _e("e27", "字母坠落", "text", "letter_drop", "字母自上坠落，表达重量",
       {"opacity": 0, "y": -40, "rotation": -6}, {"opacity": 1, "y": 0, "rotation": 0},
       "bounce.out", 0.7, 0.04)
    _e("e28", "下划线生长", "text", "line_grow", "线条自左生长，表达强调",
       {"scaleX": 0}, {"scaleX": 1}, "power2.out", 0.5, 0.0, origin="0% 50%")
    _e("e29", "描线揭示", "text", "underline_draw", "笔画写出，表达手写感",
       {"strokeDashoffset": 400}, {"strokeDashoffset": 0}, "power1.inOut", 0.9, 0.0)
    _e("e30", "划除揭示", "text", "strike", "删除线扫过后显出保留项",
       {"clipPath": "inset(0 0 100% 0)"}, {"clipPath": "inset(0 0 0% 0)"},
       "power2.out", 0.6, 0.0)
    _e("e31", "盖章落定", "text", "stamp", "由大快速砸下，表达终局判定",
       {"scale": 2.4, "opacity": 0}, {"scale": 1, "opacity": 1},
       "power4.out", 0.4, 0.0)
    _e("e32", "卡片翻转", "text", "card_flip", "卡片翻面，表达前后语义切换",
       {"rotationY": 180, "opacity": 0}, {"rotationY": 0, "opacity": 1},
       "power2.inOut", 0.8, 0.0, origin="50% 50%")
    # --- structural unfolds --------------------------------------------------
    _e("e33", "横向展开", "*", "unfold", "宽度展开，表达容器建立",
       {"scaleX": 0, "opacity": 0}, {"scaleX": 1, "opacity": 1},
       "power3.out", 0.7, 0.0, origin="0% 50%")
    _e("e34", "纵向展开", "*", "unfold", "高度展开，表达容器建立",
       {"scaleY": 0, "opacity": 0}, {"scaleY": 1, "opacity": 1},
       "power3.out", 0.7, 0.0, origin="50% 0%")
    # --- image-specific ------------------------------------------------------
    _e("e35", "绽放进入", "image", "bloom", "亮度+缩放绽放，表达曝光",
       {"scale": 1.15, "opacity": 0, "filter": "brightness(2.2)"},
       {"scale": 1, "opacity": 1, "filter": "brightness(1)"}, "power2.out", 0.9, 0.0)
    _e("e36", "显影进入", "image", "develop", "灰度到彩色的显影",
       {"filter": "grayscale(1) brightness(0.6)", "opacity": 0},
       {"filter": "grayscale(0) brightness(1)", "opacity": 1}, "power2.out", 1.0, 0.0)
    _e("e37", "视差升起", "image", "parallax_rise", "慢速升起带视差，表达纵深",
       {"y": 48, "scale": 1.08, "opacity": 0}, {"y": 0, "scale": 1, "opacity": 1},
       "power2.out", 1.0, 0.0)
    _e("e38", "肯·伯恩斯", "image", "ken_burns", "缓慢推近，表达凝视",
       {"scale": 1.0}, {"scale": 1.06}, "none", 4.0, 0.0)
    _e("e39", "mask 扫过", "image", "mask_sweep", "对角扫过揭示",
       {"clipPath": "polygon(0 0, 0 0, 0 100%, 0 100%)"},
       {"clipPath": "polygon(0 0, 100% 0, 100% 100%, 0 100%)"},
       "power2.inOut", 0.9, 0.0)
    _e("e40", "堆叠进入", "image", "stack_in", "多层错位堆叠，表达图层关系",
       {"opacity": 0, "y": 30, "rotation": 4}, {"opacity": 1, "y": 0, "rotation": 0},
       "power3.out", 0.7, 0.08)
    # --- chart / svg ---------------------------------------------------------
    _e("e41", "SVG 描画", "*", "draw_svg", "描边绘出，表达结构生成",
       {"strokeDashoffset": 1000, "opacity": 0},
       {"strokeDashoffset": 0, "opacity": 1}, "power1.inOut", 1.1, 0.0)
    _e("e42", "路径追踪", "*", "trace_path", "沿路径出现，表达流动",
       {"drawSVG": "0%"}, {"drawSVG": "100%"}, "power1.inOut", 1.0, 0.0)
    _e("e43", "数值滚动", "chart", "count_up", "数字从 0 增长，表达量变",
       {"textContent": 0}, {"textContent": "__VALUE__"}, "power2.out", 1.2, 0.0)
    _e("e44", "柱体生长", "chart", "bars_grow", "柱子从 0 长高，表达增长",
       {"scaleY": 0, "opacity": 0}, {"scaleY": 1, "opacity": 1},
       "power3.out", 0.8, 0.05, origin="50% 100%")
    _e("e45", "环形填充", "chart", "donut_sweep", "环按比例填充，表达占比",
       {"strokeDashoffset": "__CIRC__"}, {"strokeDashoffset": 0},
       "power2.inOut", 1.0, 0.0)
    _e("e46", "折线绘出", "chart", "line_draw", "折线逐段绘制，表达趋势",
       {"drawSVG": "0%"}, {"drawSVG": "100%"}, "power1.inOut", 1.1, 0.0)
    _e("e47", "散点落位", "chart", "plot_drop", "点从上方落到坐标，表达落点",
       {"opacity": 0, "y": -20, "scale": 0}, {"opacity": 1, "y": 0, "scale": 1},
       "back.out(1.8)", 0.5, 0.03)
    _e("e48", "涟漪扩散", "*", "ripple", "波纹扩散，表达事件触发",
       {"scale": 0, "opacity": 0.9}, {"scale": 2.4, "opacity": 0},
       "power2.out", 0.9, 0.0)
    _e("e49", "波纹交错", "*", "wave_stagger", "从中心向两侧交错出现",
       {"opacity": 0, "y": 18}, {"opacity": 1, "y": 0},
       "power3.out", 0.6, 0.06)
    _e("e50", "层叠 3D", "*", "cascade_3d", "沿 Z 轴层叠推入",
       {"opacity": 0, "z": -120, "rotationX": 12}, {"opacity": 1, "z": 0, "rotationX": 0},
       "power3.out", 0.8, 0.07, origin="50% 100%")


_build()
_BY_ID = {e["id"]: e for e in _ENTRANCES}


def all_entrances() -> List[Dict]:
    return list(_ENTRANCES)


def by_kind(kind: str) -> List[Dict]:
    return [e for e in _ENTRANCES if e["kind"] in (kind, "*")]


def by_family(family: str) -> List[Dict]:
    return [e for e in _ENTRANCES if e["family"] == family]


def ids() -> List[str]:
    return [e["id"] for e in _ENTRANCES]


def get(eid: str) -> Dict:
    return _BY_ID[eid]


def counts() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in _ENTRANCES:
        out[e["kind"]] = out.get(e["kind"], 0) + 1
    out["total"] = len(_ENTRANCES)
    return out


def validate(spec: Dict) -> List[str]:
    errs: List[str] = []
    for key in ("id", "name", "kind", "family", "semantic", "from", "to",
                "ease", "duration", "stagger", "origin"):
        if key not in spec:
            errs.append(f"missing {key}")
    if spec.get("kind") not in ("text", "image", "chart", "*"):
        errs.append(f"bad kind: {spec.get('kind')}")
    if not isinstance(spec.get("from"), dict) or not isinstance(spec.get("to"), dict):
        errs.append("from/to must be objects")
    elif set(spec["from"]) != set(spec["to"]):
        errs.append("from/to property mismatch")
    if not spec.get("semantic"):
        errs.append("empty semantic (motion must be reasoned)")
    if not isinstance(spec.get("duration"), (int, float)) or spec["duration"] <= 0:
        errs.append("bad duration")
    return errs
