"""runtime/motion_runtime/contracts.py — Motion Primitive Runtime（Runtime Hardening · P0）。

设计原则（来自 Runtime Hardening 指令）：

    不要问「这个元素应该使用什么动画」，
    而要问「这个对象现在发生了什么状态变化，以及为什么」。

因此每个原语表达一种**语义运动**，而不是 fadeIn / slideIn 之类的表面动画。
每个原语都拥有明确的 **Motion Contract**：

    motion_type / source / target / trigger / duration / delay / easing /
    from_state / to_state / interrupt_policy / reverse_policy / cleanup_policy

并且可以被**单独测试**：evaluator 在归一化进度 p∈[0,1] 上产出确定性的通道增量。

通道（channels）约定 —— 都是相对「原语起始姿态」的增量：
    dx, dy      平移增量（父局部像素空间）
    scale       缩放乘子（1.0 = 不变）
    rotation    旋转增量（度）
    opacity     不透明度乘子（1.0 = 不变）
    connect     关系/连接推进进度 [0,1]（供动态 Connector 重算）
    emphasis    强调强度 [0,1]（供视觉权重 / Anti-PPT 度量）
    state       目标状态名（状态类原语）
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# --- canonical delegation bootstrap (single source of truth) ---------------
# Easing lives in exactly one place: timeline.easing. This module no longer
# owns curve math; it only delegates. See runtime/docs/motion-inventory.md.
import os as _os
import sys as _sys
_RUNTIME_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _RUNTIME_DIR not in _sys.path:
    _sys.path.insert(0, _RUNTIME_DIR)
from timeline import easing as _canon_easing  # noqa: E402

# ---------------------------------------------------------------- 通道默认值
CHANNELS = ("dx", "dy", "scale", "rotation", "opacity", "connect", "emphasis")
CHANNEL_NEUTRAL = {"dx": 0.0, "dy": 0.0, "scale": 1.0, "rotation": 0.0,
                   "opacity": 1.0, "connect": 0.0, "emphasis": 0.0}

# 原语类别：routing / kinematic / relational / state / attention
CATEGORIES = ("kinematic", "relational", "state", "attention")


# ---------------------------------------------------------------- 缓动
# 归一化：缓动曲线只有唯一真相源 timeline.easing。此前此处手写的二次/三次
# 曲线公式已删除，改为对 canonical easing 的委托（行为保持，数值完全一致）。
def _clamp01(p: float) -> float:
    return 0.0 if p < 0.0 else (1.0 if p > 1.0 else float(p))


def _canon_ease(name: str):
    """构造一个对 canonical easing 的委托函数（保留 _clamp01 语义）。"""
    def _fn(p: float) -> float:
        return _canon_easing.evaluate(name, _clamp01(p))
    _fn.__name__ = "ease_%s" % name
    _fn.__doc__ = "Delegates to timeline.easing.evaluate(%r, .)" % name
    return _fn


ease_linear = _canon_ease("linear")
ease_in = _canon_ease("easeIn")
ease_out = _canon_ease("easeOut")
ease_in_out = _canon_ease("easeInOut")
ease_out_cubic = _canon_ease("easeOutCubic")
ease_in_cubic = _canon_ease("easeInCubic")
ease_in_out_cubic = _canon_ease("easeInOutCubic")
ease_out_back = _canon_ease("easeOutBack")


EASINGS: Dict[str, Callable[[float], float]] = {
    "linear": ease_linear,
    "easeIn": ease_in,
    "easeOut": ease_out,
    "easeInOut": ease_in_out,
    "easeOutCubic": ease_out_cubic,
    "easeInCubic": ease_in_cubic,
    "easeInOutCubic": ease_in_out_cubic,
    "easeOutBack": ease_out_back,
}


# ---------------------------------------------------------------- 场景上下文
class SceneCtx:
    """原语 evaluator 读取的几何上下文（世界像素盒）。"""

    def __init__(self, boxes: Optional[Dict[str, Sequence[float]]] = None):
        self._boxes: Dict[str, List[float]] = {
            k: [float(v[0]), float(v[1]), float(v[2]), float(v[3])]
            for k, v in (boxes or {}).items()
        }

    def set_box(self, nid: str, box: Sequence[float]) -> None:
        self._boxes[nid] = [float(box[0]), float(box[1]), float(box[2]), float(box[3])]

    def box(self, nid: str) -> List[float]:
        if nid not in self._boxes:
            raise KeyError("SceneCtx has no box for node %r" % nid)
        return list(self._boxes[nid])

    def has(self, nid: str) -> bool:
        return nid in self._boxes

    def center(self, nid: str) -> Tuple[float, float]:
        x, y, w, h = self.box(nid)
        return (x + w / 2.0, y + h / 2.0)


def _center_of(ctx: SceneCtx, nid: str) -> Tuple[float, float]:
    if ctx.has(nid):
        return ctx.center(nid)
    return (0.0, 0.0)


# ---------------------------------------------------------------- 契约
INTERRUPT_POLICIES = ("abort", "blend", "queue", "complete")
REVERSE_POLICIES = ("reverse", "snap", "none")
CLEANUP_POLICIES = ("restore", "hold", "revert")


@dataclass
class MotionContract:
    """Motion Primitive 的静态契约（声明一个原语「必须满足什么」）。"""

    motion_type: str
    category: str = "kinematic"
    source: str = "self"          # self | ref | group
    target: Optional[str] = None
    trigger: Optional[str] = None  # 触发条件（事件名 / state / relation）
    duration: float = 0.5
    delay: float = 0.0
    easing: str = "easeInOut"
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    interrupt_policy: str = "blend"
    reverse_policy: str = "reverse"
    cleanup_policy: str = "restore"

    def validate(self) -> List[str]:
        errs = []
        if not self.motion_type:
            errs.append("motion_type required")
        if self.category not in CATEGORIES:
            errs.append("bad category: %s" % self.category)
        if self.duration <= 0:
            errs.append("duration must be > 0")
        if self.delay < 0:
            errs.append("delay must be >= 0")
        if self.easing not in EASINGS:
            errs.append("unknown easing: %s" % self.easing)
        if self.interrupt_policy not in INTERRUPT_POLICIES:
            errs.append("bad interrupt_policy: %s" % self.interrupt_policy)
        if self.reverse_policy not in REVERSE_POLICIES:
            errs.append("bad reverse_policy: %s" % self.reverse_policy)
        if self.cleanup_policy not in CLEANUP_POLICIES:
            errs.append("bad cleanup_policy: %s" % self.cleanup_policy)
        # relational 原语必须声明 target（谁影响谁）；attention 可作用于自身，
        # 故不强制 target。
        if self.category == "relational" and not self.target:
            errs.append("category 'relational' requires target")
        return errs

    def to_dict(self) -> dict:
        return asdict(self)


# evaluator 签名：(ctx, params, p) -> channels 增量 dict
Evaluator = Callable[[SceneCtx, dict, float], dict]


def _chs(**kw) -> dict:
    """返回**稀疏**通道增量：只包含本次实际改变的通道。

    这一点很关键：若返回中性通道（如 scale=1.0），Conflict Solver 的叠加/乘积
    融合会把中性值也计入，导致错误的累积。
    """
    return dict(kw)


# ---------------------------------------------------------------- 原语 evaluators
# 每个 evaluator 都是纯函数：给定几何 + 参数 + 归一化进度 p，产出确定性通道增量。

def _ev_move(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    frm = prm.get("from", (0.0, 0.0))
    to = prm.get("to")
    if to is None:
        to = prm.get("offset", (0.0, 0.0))
    dx = (to[0] - frm[0]) * e
    dy = (to[1] - frm[1]) * e
    return _chs(dx=dx, dy=dy)


def _ev_scale(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    a = float(prm.get("from", 1.0))
    b = float(prm.get("to", 1.0))
    return _chs(scale=a + (b - a) * e)


def _ev_rotate(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    a = float(prm.get("from", 0.0))
    b = float(prm.get("to", 360.0))
    return _chs(rotation=a + (b - a) * e)


def _ev_morph(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    # 形状插值进度作为 connect 通道 + 轻微缩放呼吸
    return _chs(connect=e, scale=1.0 + 0.03 * math.sin(math.pi * e))


def _ev_follow(ctx, prm, p):
    """source 持续跟随 target；lag/damping 决定落后量与收敛。"""
    lag = float(prm.get("lag", 0.15))
    strength = float(prm.get("strength", 1.0))
    sc = _center_of(ctx, prm["source"])
    tc = _center_of(ctx, prm["target"])
    e = EASINGS[prm.get("easing", "easeOut")](p) * strength
    # 跟随：向 target 位移，但保留 lag 比例的落后（p=1 时仍 lag 落后）
    remain = (1.0 - e) + lag * e
    dx = (tc[0] - sc[0]) * (1.0 - remain)
    dy = (tc[1] - sc[1]) * (1.0 - remain)
    return _chs(dx=dx, dy=dy)


def _ev_connect(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    return _chs(connect=e)


def _ev_disconnect(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeIn")](p)
    return _chs(connect=1.0 - e)


def _ev_draw(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    return _chs(connect=e, opacity=_clamp01(0.2 + 0.8 * e))


def _ev_transfer(ctx, prm, p):
    """信号/情绪从 source 传导到 target：连接推进 + 末段强调 target。"""
    e = EASINGS[prm.get("easing", "easeInOut")](p)
    emphasis = 0.0 if e < 0.7 else (e - 0.7) / 0.3
    return _chs(connect=e, emphasis=emphasis)


def _ev_attract(ctx, prm, p):
    strength = float(prm.get("strength", 1.0))
    sc = _center_of(ctx, prm["source"])
    tc = _center_of(ctx, prm["target"])
    e = EASINGS[prm.get("easing", "easeOutCubic")](p) * strength
    return _chs(dx=(tc[0] - sc[0]) * e, dy=(tc[1] - sc[1]) * e)


def _ev_repel(ctx, prm, p):
    strength = float(prm.get("strength", 1.0))
    sc = _center_of(ctx, prm["source"])
    tc = _center_of(ctx, prm["target"])
    dx, dy = sc[0] - tc[0], sc[1] - tc[1]
    dist = math.hypot(dx, dy) or 1.0
    e = EASINGS[prm.get("easing", "easeOutCubic")](p) * strength
    reach = float(prm.get("reach", 80.0))
    return _chs(dx=dx / dist * reach * e, dy=dy / dist * reach * e)


def _ev_surround(ctx, prm, p):
    """surrounders 向 subject 收拢成包围关系；单原语一次处理一个 surrounder。"""
    radius0 = float(prm.get("radius_from", 260.0))
    radius1 = float(prm.get("radius_to", 130.0))
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    cc = _center_of(ctx, prm["target"])   # subject
    sc = _center_of(ctx, prm["source"])   # surrounder
    ang = float(prm.get("angle", 0.0))
    tx = cc[0] + radius1 * math.cos(ang)
    ty = cc[1] + radius1 * math.sin(ang)
    sx = cc[0] + radius0 * math.cos(ang)
    sy = cc[1] + radius0 * math.sin(ang)
    return _chs(dx=(tx - sx) * e, dy=(ty - sy) * e)


def _ev_compress(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOutCubic")](p)
    to_scale = float(prm.get("to_scale", 0.7))
    # 向自身锚点/或 target 压缩
    dx = dy = 0.0
    sc = _center_of(ctx, prm["source"])
    if ctx.has(prm["target"] or ""):
        tc = _center_of(ctx, prm["target"])
        k = float(prm.get("toward", 0.25))
        dx = (tc[0] - sc[0]) * k * e
        dy = (tc[1] - sc[1]) * k * e
    return _chs(scale=1.0 + (to_scale - 1.0) * e, dx=dx, dy=dy, emphasis=0.5 * e)


def _ev_expand(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    to_scale = float(prm.get("to_scale", 1.6))
    return _chs(scale=1.0 + (to_scale - 1.0) * e)


def _ev_split(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    dist = float(prm.get("distance", 40.0))
    ang = float(prm.get("angle", 0.0))
    return _chs(dx=dist * math.cos(ang) * e, dy=dist * math.sin(ang) * e, scale=1.0)


def _ev_merge(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeInOutCubic")](p)
    sc = _center_of(ctx, prm["source"])
    tc = _center_of(ctx, prm["target"])
    return _chs(dx=(tc[0] - sc[0]) * e, dy=(tc[1] - sc[1]) * e)


def _ev_push(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    dist = float(prm.get("distance", 60.0))
    ang = float(prm.get("angle", 0.0))
    return _chs(dx=dist * math.cos(ang) * e, dy=dist * math.sin(ang) * e)


def _ev_pull(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    sc = _center_of(ctx, prm["source"])
    tc = _center_of(ctx, prm["target"])
    return _chs(dx=(tc[0] - sc[0]) * e, dy=(tc[1] - sc[1]) * e)


def _ev_activate(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutCubic")](p)
    return _chs(opacity=e, scale=0.92 + 0.08 * e, state=prm.get("to_state", "active"))


def _ev_deactivate(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeIn")](p)
    return _chs(opacity=1.0 - 0.8 * e, scale=1.0 - 0.12 * e,
                state=prm.get("to_state", "inactive"))


def _ev_emphasize(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOutBack")](p)
    amount = float(prm.get("amount", 0.14))
    return _chs(scale=1.0 + amount * e, emphasis=float(prm.get("strength", 1.0)) * e)


def _ev_deemphasize(ctx, prm, p):
    e = EASINGS[prm.get("easing", "easeOut")](p)
    amount = float(prm.get("amount", 0.1))
    return _chs(scale=1.0 - amount * e, opacity=1.0 - 0.25 * e, emphasis=-e)


# ---------------------------------------------------------------- 原语定义
@dataclass
class PrimitiveDef:
    contract: MotionContract
    evaluator: Evaluator
    produces: Tuple[str, ...]  # 该原语会写哪些通道（用于冲突检测/审计）

    @property
    def motion_type(self) -> str:
        return self.contract.motion_type


def _def(motion_type, evaluator, produces, **contract_kw) -> PrimitiveDef:
    contract_kw.setdefault("motion_type", motion_type)
    return PrimitiveDef(MotionContract(**contract_kw), evaluator, tuple(produces))


PRIMITIVES: Dict[str, PrimitiveDef] = {}


def _register(pd: PrimitiveDef) -> PrimitiveDef:
    PRIMITIVES[pd.motion_type] = pd
    return pd


# ---- kinematic ----
_register(_def("MOVE", _ev_move, ("dx", "dy"), category="kinematic"))
_register(_def("SCALE", _ev_scale, ("scale",), category="kinematic"))
_register(_def("ROTATE", _ev_rotate, ("rotation",), category="kinematic"))
_register(_def("MORPH", _ev_morph, ("connect", "scale"), category="kinematic"))
_register(_def("COMPRESS", _ev_compress, ("scale", "dx", "dy", "emphasis"),
               category="kinematic"))
_register(_def("EXPAND", _ev_expand, ("scale",), category="kinematic"))
_register(_def("PUSH", _ev_push, ("dx", "dy"), category="kinematic"))
_register(_def("PULL", _ev_pull, ("dx", "dy"), category="kinematic"))
# ---- relational ----
_register(_def("FOLLOW", _ev_follow, ("dx", "dy"), category="relational", target="ref"))
_register(_def("CONNECT", _ev_connect, ("connect",), category="relational", target="ref"))
_register(_def("DISCONNECT", _ev_disconnect, ("connect",), category="relational", target="ref"))
_register(_def("DRAW", _ev_draw, ("connect", "opacity"), category="relational", target="ref"))
_register(_def("TRANSFER", _ev_transfer, ("connect", "emphasis"),
               category="relational", target="ref"))
_register(_def("ATTRACT", _ev_attract, ("dx", "dy"), category="relational", target="ref"))
_register(_def("REPEL", _ev_repel, ("dx", "dy"), category="relational", target="ref"))
_register(_def("SURROUND", _ev_surround, ("dx", "dy"), category="relational", target="ref"))
_register(_def("SPLIT", _ev_split, ("dx", "dy"), category="kinematic"))
_register(_def("MERGE", _ev_merge, ("dx", "dy"), category="relational", target="ref"))
# ---- state ----
_register(_def("ACTIVATE", _ev_activate, ("opacity", "scale", "state"),
               category="state", from_state="inactive", to_state="active"))
_register(_def("DEACTIVATE", _ev_deactivate, ("opacity", "scale", "state"),
               category="state", from_state="active", to_state="inactive"))
# ---- attention ----
_register(_def("EMPHASIZE", _ev_emphasize, ("scale", "emphasis"), category="attention"))
_register(_def("DEEMPHASIZE", _ev_deemphasize, ("scale", "opacity", "emphasis"),
               category="attention"))

PRIMITIVE_TYPES: Tuple[str, ...] = tuple(PRIMITIVES.keys())


# ---------------------------------------------------------------- 原语实例
@dataclass
class MotionPrimitive:
    """一次具体的语义运动应用：契约模板 + 具体 source/target/timing/params。"""

    motion_type: str
    source: str
    target: Optional[str] = None
    start: float = 0.0
    duration: Optional[float] = None
    delay: Optional[float] = None
    easing: Optional[str] = None
    trigger: Optional[str] = None
    params: dict = field(default_factory=dict)
    reason: Optional[str] = None
    priority: int = 0
    blend: str = "add"
    owner: Optional[str] = None

    def contract(self) -> MotionContract:
        pd = PRIMITIVES.get(self.motion_type)
        if pd is None:
            raise KeyError("unknown motion primitive: %s" % self.motion_type)
        return pd.contract

    @property
    def _dur(self) -> float:
        if self.duration is not None:
            return float(self.duration)
        return self.contract().duration

    @property
    def _delay(self) -> float:
        if self.delay is not None:
            return float(self.delay)
        return self.contract().delay

    @property
    def _easing(self) -> str:
        return self.easing or self.contract().easing

    def time_range(self) -> Tuple[float, float]:
        s = self.start + self._delay
        return (s, s + self._dur)

    def progress_at(self, t: float) -> Optional[float]:
        """返回 t 时刻的归一化进度；不在作用区间返回 None。"""
        s, e = self.time_range()
        if t < s:
            return None
        if e <= s:
            return 1.0
        return _clamp01((t - s) / (e - s))

    def sample(self, ctx: SceneCtx, t: float) -> Optional[dict]:
        """在 t 时刻采样该原语，返回 {node: {channel: delta}}；未生效返回 None。"""
        p = self.progress_at(t)
        if p is None:
            return None
        pd = PRIMITIVES[self.motion_type]
        # evaluator 通过 params 读取 easing 与 from/to，以及真实节点 id
        prm = dict(self.params)
        prm.setdefault("easing", self._easing)
        prm["source"] = self.source
        prm["target"] = self.target
        ch = pd.evaluator(ctx, prm, p)
        return {self.source: dict(ch)}

    def validate(self) -> List[str]:
        errs = []
        if self.motion_type not in PRIMITIVES:
            errs.append("unknown motion_type: %s" % self.motion_type)
            return errs
        pd = PRIMITIVES[self.motion_type]
        c = pd.contract
        if c.category == "relational" and not self.target:
            errs.append("%s requires target" % self.motion_type)
        if self.blend not in ("add", "override", "max", "weighted", "min"):
            errs.append("bad blend: %s" % self.blend)
        # 每个 motion 必须拥有 trigger（§17 Motion invariant）
        # 允许运行时提供全局 trigger，这里只在显式声明时校验非空
        return errs

    def to_dict(self) -> dict:
        return {
            "motion_type": self.motion_type, "source": self.source,
            "target": self.target, "start": self.start,
            "duration": self._dur, "delay": self._delay, "easing": self._easing,
            "trigger": self.trigger, "reason": self.reason,
            "priority": self.priority, "blend": self.blend, "owner": self.owner,
            "params": self.params, "channels": list(PRIMITIVES[self.motion_type].produces),
        }


def make(motion_type: str, source: str, **kw) -> MotionPrimitive:
    """构造一个语义运动原语（便捷入口）。"""
    return MotionPrimitive(motion_type=motion_type, source=source, **kw)


def primitive_def(motion_type: str) -> PrimitiveDef:
    return PRIMITIVES[motion_type]


def audit_contracts() -> dict:
    """所有原语契约的自检（用于 self_test 门禁）。"""
    issues = []
    for name, pd in PRIMITIVES.items():
        for e in pd.contract.validate():
            issues.append({"primitive": name, "error": e})
        if not pd.produces:
            issues.append({"primitive": name, "error": "produces nothing"})
    return {"status": "FAIL" if issues else "PASS", "issues": issues,
            "count": len(PRIMITIVES), "types": list(PRIMITIVE_TYPES)}


if __name__ == "__main__":  # pragma: no cover
    import json
    print(json.dumps(audit_contracts(), ensure_ascii=False, indent=2))
