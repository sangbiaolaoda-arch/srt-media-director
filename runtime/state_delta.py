"""P2-2 Phase-1 — State -> Delta -> Transition -> Motion (minimal closed loop).

Pure data + pure functions; no renderer dependency, no side effects.

Core rule (frozen decision): ``identity`` is an **explicit, independent** field.
It is NEVER derived from the beat-scoped ``id``. A missing ``identity`` means the
element is NOT a cross-beat continuous entity (``id`` may still be used as a local
render-address fallback, but never as cross-beat continuity evidence).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# Allowed delta kinds (see contracts/state_delta.v1.json).
DELTA_KINDS = ("value", "position", "scale", "opacity", "status", "visibility")

# Transition types.
TRANSITION_TYPES = ("carry", "cut", "dissolve", "transform")


@dataclass
class EntityState:
    """One entity's *steady* snapshot at a given beat."""

    entity_id: str
    visible: bool = True
    value: Optional[float] = None
    position: Optional[tuple] = None      # normalized centre (cx, cy)
    scale: float = 1.0
    opacity: float = 1.0
    status: Optional[str] = None


@dataclass
class StateDelta:
    """A single 'from -> to' semantic change. NOT an animation plan."""

    entity_id: str
    kind: str
    frm: Any
    to: Any
    reason: str                           # required: unreasoned change is forbidden

    def magnitude(self) -> Optional[float]:
        if self.kind == "value" and _is_num(self.frm) and _is_num(self.to):
            return float(self.to) - float(self.frm)
        return None

    def direction(self) -> str:
        m = self.magnitude()
        if m is None:
            return "n/a"
        if m > 0:
            return "up"
        if m < 0:
            return "down"
        return "flat"


@dataclass
class IdentityMatch:
    """Machine representation of 'these two are the same visual entity'."""

    entity_id: str
    rule: str                             # same_id | transform | move | grow | shrink | split | merge
    confidence: float = 1.0


@dataclass
class Transition:
    """Migration between two adjacent beats (upgrades contracts.transition_in)."""

    from_beat: str
    to_beat: str
    type: str                             # carry | cut | dissolve | transform
    carried: list = field(default_factory=list)
    deltas: list = field(default_factory=list)
    motion_policy: str = "required"       # required | optional | hold


@dataclass
class MotionSpec:
    """Executable form of a Transition (fed to motion_canonical / renderer)."""

    entity_id: str
    action: str                           # growth | decline | transform | hold
    channels: dict = field(default_factory=dict)
    span: tuple = (0.0, 1.0)               # absolute [start, end] seconds


# ---------------------------------------------------------------- helpers

def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _ease(x: float) -> float:
    """Smoothstep, clamped to [0, 1]."""
    if x < 0.0:
        x = 0.0
    elif x > 1.0:
        x = 1.0
    return x * x * (3.0 - 2.0 * x)


# ---------------------------------------------------------------- identity

def element_identity(el: dict) -> Optional[str]:
    """Explicit identity ONLY. Never inferred from ``id`` (frozen decision)."""
    ident = el.get("identity")
    return ident if ident else None


def match_identity(prev_elements: list, cur_elements: list) -> list:
    """Phase-1 identity matching: ``same_id`` only, over the explicit identity field.

    Elements without an ``identity`` are never matched -> they cannot be
    declared cross-beat continuous.
    """
    prev_ids = {element_identity(e) for e in prev_elements if element_identity(e)}
    out = []
    for e in cur_elements:
        ident = element_identity(e)
        if ident and ident in prev_ids:
            out.append(IdentityMatch(entity_id=ident, rule="same_id"))
    return out


# ---------------------------------------------------------------- delta

def entity_state(el: dict, box: Optional[dict] = None) -> EntityState:
    """Extract the steady EntityState of an element (merging its box, if any)."""
    st = el.get("state") or {}
    pos = None
    if box:
        pos = (round(box["x"] + box["w"] / 2.0, 4),
               round(box["y"] + box["h"] / 2.0, 4))
    return EntityState(
        entity_id=element_identity(el) or el.get("id"),
        visible=st.get("visible", True),
        value=st.get("value"),
        position=pos,
        scale=st.get("scale", 1.0),
        opacity=st.get("opacity", 1.0),
        status=st.get("status"),
    )


def derive_delta(prev: EntityState, cur: EntityState, reason: str) -> list:
    """Diff two EntityStates of the SAME identity into a StateDelta list."""
    deltas = []
    if (prev.value != cur.value) and (prev.value is not None or cur.value is not None):
        deltas.append(StateDelta(cur.entity_id, "value", prev.value, cur.value, reason))
    if (prev.position != cur.position) and (prev.position or cur.position):
        deltas.append(StateDelta(cur.entity_id, "position", prev.position, cur.position, reason))
    if prev.scale != cur.scale:
        deltas.append(StateDelta(cur.entity_id, "scale", prev.scale, cur.scale, reason))
    if prev.opacity != cur.opacity:
        deltas.append(StateDelta(cur.entity_id, "opacity", prev.opacity, cur.opacity, reason))
    if prev.status != cur.status:
        deltas.append(StateDelta(cur.entity_id, "status", prev.status, cur.status, reason))
    if prev.visible != cur.visible:
        deltas.append(StateDelta(cur.entity_id, "visibility", prev.visible, cur.visible, reason))
    return deltas


def classify_transition(from_beat: str, to_beat: str, carried: list,
                        deltas: list, *, dissolve: bool = False,
                        cut: bool = False) -> Transition:
    """carry (continuous, no change) vs transform (continuous, real change) vs cut / dissolve."""
    if cut:
        ttype = "cut"
    elif dissolve:
        ttype = "dissolve"
    elif carried and deltas:
        ttype = "transform"
    elif carried:
        ttype = "carry"
    else:
        ttype = "cut"
    return Transition(from_beat, to_beat, ttype, list(carried), list(deltas))


# ---------------------------------------------------------------- motion grammar

def compile_motion(delta: StateDelta, span: tuple) -> MotionSpec:
    """Map a *semantic* delta to a semantic action (growth / decline) — not an effect."""
    m = delta.magnitude()
    if m is None:
        action = "transform"
    elif m > 0:
        action = "growth"
    elif m < 0:
        action = "decline"
    else:
        action = "hold"
    channels = {delta.kind: {"from": delta.frm, "to": delta.to}}
    return MotionSpec(entity_id=delta.entity_id, action=action,
                      channels=channels, span=span)


def sample_value(spec: MotionSpec, t: float) -> float:
    """Executor: interpolate the semantic value channel at absolute time ``t``."""
    span0, span1 = spec.span
    ch = spec.channels["value"]
    p = _ease((t - span0) / max(span1 - span0, 1e-9))
    return ch["from"] + (ch["to"] - ch["from"]) * p


# ---------------------------------------------------------------- validation

def validate_deltas(deltas: list, span: Optional[tuple] = None) -> list:
    """Continuity rules (mirror the codes declared in contracts/state_delta.v1.json)."""
    issues = []
    for d in deltas:
        if not d.reason:
            issues.append({"code": "DELTA_NO_REASON", "entity": d.entity_id, "kind": d.kind})
        if d.kind == "value" and d.magnitude() == 0:
            issues.append({"code": "DELTA_DIRECTION_UNSIGNED", "entity": d.entity_id})
    if span is not None and (span[1] - span[0]) <= 0.0:
        issues.append({"code": "DELTA_INSTANT", "span": list(span)})
    return issues


def as_dict(obj: Any) -> Any:
    """dataclass -> plain dict (for JSON evidence)."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: as_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, (list, tuple)):
        return [as_dict(v) for v in obj]
    return obj
