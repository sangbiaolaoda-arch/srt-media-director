"""motion_registry.py — 可复用动画原语注册表。

设计：Motion Planner 只负责「选择什么」，Registry 负责「怎么实现」。
每个原语声明：
  kind        enter | relation | state | static | continue
  supported   支持的元素类型（"*" 表示任意）
  semantic    语义解释（动画必须能回答「为什么这样出现」）
  easing      默认缓动
  css         该原语在时长百分比上的关键帧骨架（供 Renderer 编译为 CSS keyframes）

新增原语只需 register_motion(...)，不必改 Planner 或 Renderer。
"""

# ---------------------------------------------------------------- 原语定义
def _kf(*frames):
    """frames: (pct, dict(props)) 序列。"""
    return tuple(frames)


MOTION_PRIMITIVES = {
    # --- 进入类：回答「元素如何进入注意力」 ---
    "emerge": {
        "kind": "enter", "supported": ("*",), "easing": "cubic-bezier(.2,.7,.2,1)",
        "semantic": "重要信息进入注意力",
        "css": _kf((0, {"opacity": 0, "transform": "translateY(10px) scale(.94)"}),
                   (100, {"opacity": 1, "transform": "translateY(0) scale(1)"})),
    },
    "fade": {
        "kind": "enter", "supported": ("*",), "easing": "ease-out",
        "semantic": "平缓出现，不抢焦点",
        "css": _kf((0, {"opacity": 0}), (100, {"opacity": 1})),
    },
    "slide": {
        "kind": "enter", "supported": ("*",), "easing": "cubic-bezier(.2,.7,.2,1)",
        "semantic": "从方向进入，表达来源 / 流向",
        "css": _kf((0, {"opacity": 0, "transform": "translateX(-28px)"}),
                   (100, {"opacity": 1, "transform": "translateX(0)"})),
    },
    "scale": {
        "kind": "enter", "supported": ("*",), "easing": "cubic-bezier(.2,.8,.2,1)",
        "semantic": "由小放大，表达强调 / 生长",
        "css": _kf((0, {"opacity": 0, "transform": "scale(.55)"}),
                   (100, {"opacity": 1, "transform": "scale(1)"})),
    },
    "reveal": {
        "kind": "enter", "supported": ("*",), "easing": "ease-out",
        "semantic": "信息逐渐揭示",
        "css": _kf((0, {"opacity": 0, "clip-path": "inset(0 100% 0 0)"}),
                   (100, {"opacity": 1, "clip-path": "inset(0 0 0 0)"})),
    },
    "wipe": {
        "kind": "enter", "supported": ("*",), "easing": "ease-out",
        "semantic": "擦除式揭示",
        "css": _kf((0, {"opacity": 0, "clip-path": "inset(0 100% 0 0)"}),
                   (100, {"opacity": 1, "clip-path": "inset(0 0 0 0)"})),
    },
    # --- 关系类：表达元素之间关系如何建立 ---
    "draw": {
        "kind": "relation", "supported": ("connector", "path", "line"),
        "easing": "ease-in-out", "semantic": "关系建立 / 连接形成",
        "css": _kf((0, {"opacity": 0, "clip-path": "inset(0 100% 0 0)"}),
                   (100, {"opacity": 1, "clip-path": "inset(0 0 0 0)"})),
    },
    "trace": {
        "kind": "relation", "supported": ("connector", "path"),
        "easing": "linear", "semantic": "沿路径推进 / 传导",
        "css": _kf((0, {"opacity": 0, "clip-path": "inset(0 100% 0 0)"}),
                   (100, {"opacity": 1, "clip-path": "inset(0 0 0 0)"})),
    },
    # --- 状态类：表达元素自身如何变化 ---
    "grow": {
        "kind": "state", "supported": ("chart", "bar", "data"),
        "easing": "cubic-bezier(.2,.8,.2,1)", "semantic": "增加 / 累积",
        "css": _kf((0, {"opacity": 0, "transform": "scaleY(.02)"}),
                   (100, {"opacity": 1, "transform": "scaleY(1)"})),
        "origin": "50% 100%",
    },
    "count": {
        "kind": "state", "supported": ("chart", "data", "label"),
        "easing": "ease-out", "semantic": "数值累加",
        "css": _kf((0, {"opacity": 0, "transform": "translateY(6px)"}),
                   (100, {"opacity": 1, "transform": "translateY(0)"})),
    },
    "converge": {
        "kind": "state", "supported": ("*",), "easing": "cubic-bezier(.3,.8,.2,1)",
        "semantic": "集中 / 压力 / 收敛",
        "css": _kf((0, {"opacity": 0, "transform": "translateX(60px) scale(1.05)"}),
                   (100, {"opacity": 1, "transform": "translateX(0) scale(1)"})),
    },
    "diverge": {
        "kind": "state", "supported": ("*",), "easing": "cubic-bezier(.3,.8,.2,1)",
        "semantic": "分裂 / 选择 / 发散",
        "css": _kf((0, {"opacity": 0, "transform": "translateX(-40px)"}),
                   (100, {"opacity": 1, "transform": "translateX(0)"})),
    },
    "expand": {
        "kind": "state", "supported": ("*",), "easing": "cubic-bezier(.3,.8,.2,1)",
        "semantic": "扩大",
        "css": _kf((0, {"opacity": 0, "transform": "scale(.7)"}),
                   (100, {"opacity": 1, "transform": "scale(1)"})),
    },
    "collapse": {
        "kind": "state", "supported": ("*",), "easing": "cubic-bezier(.3,.8,.2,1)",
        "semantic": "收缩 / 收束",
        "css": _kf((0, {"opacity": 1, "transform": "scale(1)"}),
                   (100, {"opacity": .9, "transform": "scale(.86)"})),
    },
    "rotate": {
        "kind": "state", "supported": ("*",), "easing": "ease-in-out",
        "semantic": "转动",
        "css": _kf((0, {"opacity": 0, "transform": "rotate(-12deg) scale(.9)"}),
                   (100, {"opacity": 1, "transform": "rotate(0) scale(1)"})),
    },
    # --- 静止 / 延续 ---
    "static": {
        "kind": "static", "supported": ("*",), "easing": "linear",
        "semantic": "稳定 / 背景 / 对照（明确的运动决策：不动）",
        "css": _kf((0, {"opacity": 1}), (100, {"opacity": 1})),
    },
    "carry_over": {
        "kind": "continue", "supported": ("*",), "easing": "linear",
        "semantic": "跨拍延续：上一拍已存在，不重新入场",
        "css": _kf((0, {"opacity": 1}), (100, {"opacity": 1})),
    },
    "continue": {
        "kind": "continue", "supported": ("*",), "easing": "linear",
        "semantic": "延续上一拍状态",
        "css": _kf((0, {"opacity": 1}), (100, {"opacity": 1})),
    },
    "transform": {
        "kind": "continue", "supported": ("*",), "easing": "cubic-bezier(.2,.8,.2,1)",
        "semantic": "同一元素跨拍状态改变（而非重新入场）",
        "css": _kf((0, {"opacity": 1, "transform": "scale(1)"}),
                   (100, {"opacity": 1, "transform": "scale(1.08)"})),
    },
    "handoff": {
        "kind": "continue", "supported": ("*",), "easing": "linear",
        "semantic": "跨拍交接，保持连续性",
        "css": _kf((0, {"opacity": 1}), (100, {"opacity": 1})),
    },
    "none": {
        "kind": "static", "supported": ("*",), "easing": "linear",
        "semantic": "显式不运动（none 为 static 的别名）",
        "css": _kf((0, {"opacity": 1}), (100, {"opacity": 1})),
    },
}

VALID_MOTIONS = tuple(MOTION_PRIMITIVES.keys())

# 已知静态 / 延续的 type（在覆盖度统计中记为「已明确决策」）
STATIC_LIKE = ("static", "none", "carry_over", "continue", "handoff", "transform")


def register_motion(name, kind, supported=("*",), semantic="", easing="linear", css=None):
    """注册一个新动画原语（Motion Planner 只选择，Registry 决定实现）。"""
    if not name or not isinstance(name, str):
        raise ValueError("motion name 必须是非空字符串")
    MOTION_PRIMITIVES[name] = {
        "kind": kind, "supported": tuple(supported), "semantic": semantic,
        "easing": easing, "css": css or _kf((0, {"opacity": 0}), (100, {"opacity": 1})),
    }
    global VALID_MOTIONS
    VALID_MOTIONS = tuple(MOTION_PRIMITIVES.keys())
    return MOTION_PRIMITIVES[name]


def primitive(name):
    return MOTION_PRIMITIVES.get(name)


def is_valid_motion(name):
    return name in MOTION_PRIMITIVES


def supports(name, element_type, fallback="*"):
    p = MOTION_PRIMITIVES.get(name)
    if not p:
        return False
    sup = p["supported"]
    return "*" in sup or fallback in sup or element_type in sup
