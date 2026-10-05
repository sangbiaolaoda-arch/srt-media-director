"""Canonical motion vocabulary — the SINGLE list of motion actions.

This merges the three previously-forked vocabularies onto one canonical set:

* ``motion/motion_registry.py``   MOTION_PRIMITIVES (21 names)
* ``motion_runtime/contracts.py`` PRIMITIVES (22 uppercase names)
* ``scene/motion_compiler.py``    BASE (38 semantic actions)

Every legacy spelling is preserved as an *alias* so behaviour-preserving
migration (PHASE 3) can map old call sites onto the canonical names without
inventing semantics. Each canonical action declares:

    category    enter | exit | emphasis | relational | state | continue | static
    produces    the channel deltas it touches (see transform.CHANNELS)
    easing      canonical easing name (resolved by timeline.easing)
    duration    default seconds
    aliases     legacy spellings that must resolve to this action
    description why this action exists (semantics, not surface animation)
"""
from __future__ import annotations

CATEGORIES = ("enter", "exit", "emphasis", "relational",
              "state", "continue", "static")


def _a(category, produces, easing, duration, description, aliases=()):
    return {
        "category": category,
        "produces": tuple(produces),
        "easing": easing,
        "duration": float(duration),
        "description": description,
        "aliases": tuple(aliases),
    }


# --------------------------------------------------------------------------
# The canonical vocabulary. Keys are the canonical names.
# --------------------------------------------------------------------------
ACTIONS = {
    # ---- enter: how an element enters attention ---------------------------
    "fade": _a("enter", ("opacity",), "easeOut", 0.45,
               "平缓出现，不抢焦点", aliases=("fade_in", "fadeIn")),
    "emerge": _a("enter", ("opacity", "dy", "scale"), "easeOutCubic", 0.5,
                 "重要信息进入注意力", aliases=("EMERGE",)),
    "rise": _a("enter", ("opacity", "dy"), "easeOutCubic", 0.5,
               "自下方升起（生产链使用）", aliases=("slide_up",)),
    "slide": _a("enter", ("dx", "opacity"), "easeOutCubic", 0.5,
                "从方向进入，表达来源 / 流向", aliases=("slide_in", "slideIn")),
    "pop": _a("enter", ("scale", "opacity"), "easeOutBack", 0.42,
              "由小弹入，表达强调 / 生长（生产链使用）", aliases=()),
    "scale_in": _a("enter", ("scale", "opacity"), "easeOutBack", 0.45,
                   "由小放大，表达强调 / 生长",
                   aliases=("scaleIn", "scale_up", "scale")),
    "reveal": _a("enter", ("clip", "opacity"), "easeOut", 0.55,
                 "信息逐渐揭示", aliases=("REVEAL",)),
    "wipe": _a("enter", ("clip", "opacity"), "easeInOut", 0.5,
               "擦除式揭示", aliases=("WIPE",)),
    "mask": _a("enter", ("clip", "opacity"), "easeOut", 0.5,
               "遮罩揭示", aliases=("MASK",)),
    "draw": _a("relational", ("connect", "clip", "opacity"), "easeInOut", 0.7,
               "关系建立 / 连接形成", aliases=("DRAW",)),
    "type": _a("enter", ("chars",), "linear", 0.9,
               "打字机揭示", aliases=("TYPE", "typewriter")),

    # ---- exit -------------------------------------------------------------
    "fade_out": _a("exit", ("opacity",), "easeIn", 0.4,
                   "淡出退场", aliases=("FADE_OUT", "disappear")),
    "sink": _a("exit", ("opacity", "dy"), "easeIn", 0.45,
               "下沉退场（生产链使用）", aliases=("SINK",)),
    "shrink": _a("exit", ("scale", "opacity"), "easeInOut", 0.5,
                 "收缩退场（生产链使用）", aliases=("SHRINK",)),

    # ---- emphasis ---------------------------------------------------------
    "scale_pulse": _a("emphasis", ("scale", "emphasis"), "easeInOutBack", 0.3,
                      "脉冲强调", aliases=("SCALE_PULSE",)),
    "stroke_emphasis": _a("emphasis", ("stroke", "emphasis"), "easeOut", 0.35,
                          "描边强调", aliases=("STROKE_EMPHASIS",)),
    "glow": _a("emphasis", ("glow", "emphasis"), "easeInOut", 0.5,
               "发光强调", aliases=("GLOW",)),
    "shake": _a("emphasis", ("dx", "emphasis"), "easeInOut", 0.25,
                "抖动强调", aliases=("SHAKE",)),
    "focus": _a("emphasis", ("dim_others", "emphasis"), "easeOut", 0.4,
                "聚焦（压暗其他）", aliases=("FOCUS",)),
    "isolate": _a("emphasis", ("dim_others", "emphasis"), "easeOut", 0.4,
                  "孤立（更强压暗）", aliases=("ISOLATE",)),
    "emphasize": _a("emphasis", ("scale", "emphasis"), "easeOutCubic", 0.5,
                    "强化（Runtime 原语）", aliases=("EMPHASIZE",)),
    "deemphasize": _a("emphasis", ("scale", "opacity", "emphasis"), "easeInOut", 0.5,
                      "弱化（Runtime 原语）", aliases=("DEEMPHASIZE",)),

    # ---- relational -------------------------------------------------------
    "connect": _a("relational", ("connect",), "easeInOut", 0.5,
                  "建立连接（关系推进）", aliases=("CONNECT",)),
    "disconnect": _a("relational", ("connect",), "easeInOut", 0.5,
                     "断开连接", aliases=("DISCONNECT",)),
    "trace": _a("relational", ("connect", "clip"), "linear", 0.6,
                "沿路径推进 / 传导", aliases=("TRACE",)),
    "follow": _a("relational", ("dx", "dy"), "easeOut", 0.45,
                 "跟随参照物", aliases=("FOLLOW",)),
    "point": _a("relational", ("connect",), "easeOut", 0.4,
                "指向", aliases=("POINT",)),
    "attach": _a("relational", ("dx", "dy"), "easeOut", 0.4,
                 "附着", aliases=("ATTACH",)),
    "surround": _a("relational", ("dx", "dy"), "easeOutCubic", 0.6,
                   "环绕", aliases=("SURROUND",)),
    "orbit": _a("relational", ("rotation",), "linear", 3.0,
                "环绕轨道", aliases=("ORBIT",)),
    "attract": _a("relational", ("dx", "dy"), "easeInOut", 0.5,
                  "吸引", aliases=("ATTRACT",)),
    "repel": _a("relational", ("dx", "dy"), "easeInOut", 0.5,
                "排斥", aliases=("REPEL",)),
    "transfer": _a("relational", ("connect", "emphasis"), "easeOutCubic", 0.6,
                   "传导 / 转移", aliases=("TRANSFER",)),
    "merge": _a("relational", ("dx", "dy"), "easeInCubic", 0.55,
                "合并", aliases=("MERGE",)),
    "split": _a("relational", ("dx", "dy"), "easeOutCubic", 0.55,
                "分裂", aliases=("SPLIT",)),

    # ---- state ------------------------------------------------------------
    "grow": _a("state", ("scale",), "easeOutCubic", 0.6,
               "增加 / 累积", aliases=("GROW", "count")),
    "converge": _a("state", ("dx", "scale"), "easeOutCubic", 0.6,
                   "集中 / 压力 / 收敛", aliases=("CONVERGE",)),
    "diverge": _a("state", ("dx", "scale"), "easeOutCubic", 0.6,
                  "分裂 / 选择 / 发散", aliases=("DIVERGE",)),
    "expand": _a("state", ("scale", "opacity"), "easeOutCubic", 0.55,
                 "扩大", aliases=("EXPAND",)),
    "collapse": _a("state", ("scale",), "easeInOut", 0.5,
                   "收缩 / 收束", aliases=("COLLAPSE",)),
    "compress": _a("state", ("scale", "dx", "dy", "emphasis"), "easeInOut", 0.5,
                   "压缩", aliases=("COMPRESS",)),
    "rotate": _a("state", ("rotation",), "easeInOut", 0.6,
                 "转动", aliases=("ROTATE",)),
    "morph": _a("state", ("connect", "scale"), "easeInOut", 0.7,
                "形变", aliases=("MORPH",)),
    "move": _a("state", ("dx", "dy"), "easeInOut", 0.5,
               "平移", aliases=("MOVE", "push", "PUSH")),
    "pull": _a("state", ("dx", "dy"), "easeInOut", 0.5,
               "拉近", aliases=("PULL",)),
    "appear": _a("state", ("opacity", "scale"), "easeOut", 0.5,
                 "出现（状态变化）", aliases=("APPEAR",)),
    "activate": _a("state", ("opacity", "scale"), "easeOut", 0.5,
                   "激活", aliases=("ACTIVATE",)),
    "deactivate": _a("state", ("opacity", "scale"), "easeIn", 0.5,
                     "停用", aliases=("DEACTIVATE",)),

    # ---- continue / static ------------------------------------------------
    "continue": _a("continue", (), "linear", 0.0,
                   "延续上一拍状态", aliases=("CONTINUE",)),
    "carry_over": _a("continue", (), "linear", 0.0,
                     "跨拍延续：上一拍已存在，不重新入场",
                     aliases=("CARRY_OVER", "inherit")),
    "handoff": _a("continue", (), "linear", 0.0,
                  "跨拍交接，保持连续性", aliases=("HANDOFF",)),
    "transform": _a("continue", (), "easeInOut", 0.6,
                    "同一元素跨拍状态改变（而非重新入场）", aliases=("TRANSFORM",)),
    "static": _a("static", (), "linear", 0.0,
                 "稳定 / 背景 / 对照（明确的运动决策：不动）",
                 aliases=("STATIC", "none")),
}

CANONICAL_ACTIONS = tuple(ACTIONS.keys())

# Legacy-spelling -> canonical name, case/space/underscore-insensitive.
_ALIASES = {}


def _norm(name) -> str:
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


for _name, _spec in ACTIONS.items():
    _ALIASES[_norm(_name)] = _name
    for _al in _spec["aliases"]:
        _ALIASES[_norm(_al)] = _name

# Production-chain vocabulary (entrance_planner) maps onto canonical actions.
_PRODUCTION = {
    "fade": "fade", "rise": "rise", "pop": "pop", "inherit": "carry_over",
    "sink": "sink", "shrink": "shrink",
}
for _k, _v in _PRODUCTION.items():
    _ALIASES.setdefault(_norm(_k), _v)


def canonical(name) -> str:
    """Resolve any legacy/canonical spelling to a canonical action name."""
    return _ALIASES.get(_norm(name), str(name))


def is_canonical(name) -> bool:
    return name in ACTIONS


def spec(name):
    """Return the canonical spec for ``name`` (resolving aliases), or ``None``."""
    return ACTIONS.get(canonical(name))


def category(name):
    s = spec(name)
    return s["category"] if s else None


def produces(name):
    s = spec(name)
    return s["produces"] if s else ()


def aliases_of(name) -> tuple:
    s = spec(name)
    return s["aliases"] if s else ()


def audit() -> dict:
    """Machine check: no alias may point at two different canonical actions."""
    issues = []
    seen = {}
    for raw, canon in _ALIASES.items():
        if raw in seen and seen[raw] != canon:
            issues.append({"alias": raw, "to": [seen[raw], canon]})
        seen[raw] = canon
    # every canonical action must have a defined category and easing
    for name, s in ACTIONS.items():
        if s["category"] not in CATEGORIES:
            issues.append({"action": name, "error": "bad category %s" % s["category"]})
        if not s["easing"]:
            issues.append({"action": name, "error": "missing easing"})
    return {
        "status": "FAIL" if issues else "PASS",
        "canonical_actions": len(ACTIONS),
        "aliases": len(_ALIASES),
        "issues": issues,
    }
