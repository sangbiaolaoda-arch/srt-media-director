"""Motion Compiler — 语义动作 → 动画参数（Phase 2 · 第五优先级）。

Agent 只说语义动作（expand / collapse / appear / disappear / surround /
stagger ...），Motion Compiler 把它翻译成真正的
position / scale / opacity / rotation / delay / duration / easing。

语义动画库（§8）：
- 出现：fade slide scale pop reveal draw type wipe mask
- 强调：scale_pulse stroke_emphasis glow shake focus isolate
- 关系：connect follow point surround orbit attach
- 状态变化：expand collapse split merge morph transform grow shrink
"""
from __future__ import annotations

# --- canonical delegation bootstrap (single source of truth) ---------------
# 语义动作里的 easing 名称不再自成体系：它们必须能被唯一真相源
# timeline.easing 解析。此模块只提供语义→通道参数，不持有任何曲线数学。
import os as _os
import sys as _sys
_RUNTIME_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _RUNTIME_DIR not in _sys.path:
    _sys.path.insert(0, _RUNTIME_DIR)
from motion_canonical import easing as _canon_easing  # noqa: E402

# 动作 → 通道参数（通道: from → to）
BASE = {
    # ---- 出现 ----
    "fade":    {"opacity": (0.0, 1.0), "dur": 0.45, "ease": "easeOut"},
    "slide":   {"offset": (28, 0), "opacity": (0.0, 1.0), "dur": 0.5, "ease": "easeOutCubic"},
    "scale":   {"scale": (0.7, 1.0), "opacity": (0.0, 1.0), "dur": 0.45, "ease": "easeOutBack"},
    "pop":     {"scale": (0.4, 1.0), "opacity": (0.0, 1.0), "dur": 0.42, "ease": "easeOutBack"},
    "reveal":  {"clip": (0.0, 1.0), "opacity": (0.0, 1.0), "dur": 0.55, "ease": "easeOut"},
    "draw":    {"clip": (0.0, 1.0), "dur": 0.7, "ease": "easeInOut"},
    "type":    {"chars": (0, 1.0), "dur": 0.9, "ease": "linear"},
    "wipe":    {"clip": (0.0, 1.0), "dur": 0.5, "ease": "easeInOut"},
    "mask":    {"clip": (0.0, 1.0), "dur": 0.5, "ease": "easeOut"},
    # ---- 强调 ----
    "scale_pulse":   {"scale": (1.0, 1.12), "dur": 0.3, "ease": "easeInOutBack", "emphasis": True},
    "stroke_emphasis": {"stroke": (1.0, 2.4), "dur": 0.35, "ease": "easeOut", "emphasis": True},
    "glow":          {"glow": (0.0, 1.0), "dur": 0.5, "ease": "easeInOut", "emphasis": True},
    "shake":         {"offset": (6, 0), "dur": 0.25, "ease": "easeInOut", "emphasis": True},
    "focus":         {"dim_others": (0.0, 0.55), "dur": 0.4, "ease": "easeOut", "emphasis": True},
    "isolate":       {"dim_others": (0.0, 0.7), "dur": 0.4, "ease": "easeOut", "emphasis": True},
    # ---- 关系 ----
    "connect":  {"endpoint": (0.0, 1.0), "dur": 0.5, "ease": "easeInOut"},
    "follow":   {"offset": (18, 0), "dur": 0.45, "ease": "easeOut"},
    "point":    {"endpoint": (0.0, 1.0), "dur": 0.4, "ease": "easeOut"},
    "surround": {"radius": (0.35, 1.0), "dur": 0.6, "ease": "easeOutCubic", "stagger": 0.09},
    "orbit":    {"rotation": (0.0, 360.0), "dur": 3.0, "ease": "linear"},
    "attach":   {"offset": (0, 6), "dur": 0.4, "ease": "easeOut"},
    # ---- 状态变化 ----
    "appear":   {"opacity": (0.0, 1.0), "scale": (0.9, 1.0), "dur": 0.5, "ease": "easeOut"},
    "disappear": {"opacity": (1.0, 0.0), "dur": 0.4, "ease": "easeIn"},
    "expand":   {"scale": (0.4, 1.0), "opacity": (0.0, 1.0), "dur": 0.55,
                 "ease": "easeOutCubic", "stagger": 0.12, "group": True},
    "collapse": {"scale": (1.0, 0.45), "dur": 0.5, "ease": "easeInOut",
                 "stagger": 0.08, "group": True},
    "grow":     {"scale": (1.0, 1.6), "dur": 0.6, "ease": "easeOutCubic"},
    "shrink":   {"scale": (1.0, 0.6), "dur": 0.5, "ease": "easeInOut"},
    "split":    {"offset": (24, 0), "dur": 0.55, "ease": "easeOutCubic", "stagger": 0.1},
    "merge":    {"offset": (-24, 0), "dur": 0.55, "ease": "easeInCubic"},
    "morph":    {"path": (0.0, 1.0), "dur": 0.7, "ease": "easeInOut"},
    "transform": {"matrix": (0.0, 1.0), "dur": 0.6, "ease": "easeInOut"},
}

SEMANTIC_ACTIONS = set(BASE)


def compile_action(action, **kw):
    """语义动作 → 通道参数字典（含 duration / easing / stagger）。"""
    if action not in BASE:
        raise ValueError("unknown semantic action: %s" % action)
    spec = {"action": action}
    for k, v in BASE[action].items():
        if k == "dur":
            spec["duration"] = kw.get("duration", v)
        elif k == "ease":
            spec["easing"] = kw.get("easing", v)
        elif k in ("stagger", "group", "emphasis"):
            spec[k] = v
        else:
            spec.setdefault("channels", {})[k] = v
    for k in ("delay", "duration", "easing", "start", "dependency", "reason"):
        if k in kw:
            spec[k] = kw[k]
    return spec


def compile_transition(start_state, end_state, actions, targets=None):
    """把状态迁移里的语义动作列表编译成动画意图序列。

    actions: [("expand", {"stagger": 0.12}), ("stagger", None), ...]
    返回 [{action, duration, easing, channels, targets, delay?}, ...]
    """
    out = []
    for act in actions:
        if isinstance(act, tuple):
            name, opts = act[0], (act[1] or {})
        else:
            name, opts = act, {}
        spec = compile_action(name, **opts)
        if targets is not None:
            spec["targets"] = list(targets)
        out.append(spec)
    return out


def audit_easing():
    """语义动作的 easing 必须全部可被 canonical 缓动解析（单一真相源）。

    这是行为保持的**契约检查**：只报告，不改动 BASE 或编译输出。
    """
    names = sorted({v["ease"] for v in BASE.values()})
    unknown = [n for n in names if not _canon_easing.is_known(n)]
    return {"status": "FAIL" if unknown else "PASS",
            "source": "timeline.easing", "checked": len(names), "unknown": unknown}
