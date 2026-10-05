"""Independent Motion (transform) projection (Final Practical Closeout Directive, P2).

The production chain's Motion layer maps a declared entrance/exit motion
(``rise`` / ``pop`` / ``sink`` / ``shrink`` / ``fade`` / ``inherit``) to a
per-element transform state ``(dy, scale, alpha)`` at time ``t``. Until now no
*independent* expectation verified that layer — the production observer checked
only whether an element painted ink somewhere in its declared box, not whether it
arrived with the motion the director authored.

This module is the *expected* side of that dimension. Like
:mod:`observer.projection`, it is driven by a declarative, auditable artifact
(``contracts/motion_projection.v1.json``) and **MUST NOT** import the renderer or
read the player's embedded ``BEATS``. The renderer animates; this contract
adjudicates.

Pure, browser-free and deterministic: given a lifecycle entry and a time, it
returns the transform the element *should* have.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "motion_projection.v1.json")

# Motions that change geometry (not opacity alone). ``fade`` / ``inherit`` are
# opacity-only or identity and carry no transform to adjudicate.
TRANSFORM_MOTIONS = {"rise", "pop", "sink", "shrink"}

_EPS = 1e-3


def contract_path() -> str:
    return os.environ.get("MOTION_PROJECTION_CONTRACT", CONTRACT_PATH)


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or contract_path(), encoding="utf-8") as f:
        return json.load(f)


def ease(t: float) -> float:
    """Smoothstep easing, clamped to [0, 1] — reimplemented from the contract."""
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return t * t * (3.0 - 2.0 * t)


def expected_transform(lc: Dict[str, Any], t: float,
                       contract: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """The transform ``{dy, scale, alpha}`` an element should have at time ``t``.

    Mirrors the declared Motion vocabulary: entering ``rise`` displaces the
    element downward by up to ``dy.max`` and lets it settle; ``pop`` grows it from
    ``scale.min`` to 1; an exiting ``sink``/``shrink`` displaces/shrinks it back
    out. ``inherit`` is identity. Nothing is read from the renderer.
    """
    c = contract or load_contract()
    en = lc.get("enter") or {}
    x = lc.get("exit")
    motion_in = en.get("motion")
    if motion_in == "inherit":
        return {"dy": 0.0, "scale": 1.0, "alpha": 1.0}

    en_at = float(en.get("at", 0.0))
    en_dur = float(en.get("dur", 0.0))
    a = ease((t - en_at) / max(en_dur, _EPS))

    dy = 0.0
    scale = 1.0
    if a < 1.0:
        spec = (c["enter"].get(motion_in) or {})
        if "dy" in spec:
            dy = (1.0 - a) * float(spec["dy"]["max"])
        if "scale" in spec:
            mn = float(spec["scale"]["min"])
            mx = float(spec["scale"]["max"])
            scale = mn + (mx - mn) * a

    alpha = a
    if x and t >= float(x.get("at", 0.0)):
        x_at = float(x.get("at", 0.0))
        x_dur = float(x.get("dur", 0.0))
        q = ease((t - x_at) / max(x_dur, _EPS))
        alpha = a * (1.0 - q)
        spec = (c["exit"].get(x.get("motion")) or {})
        if "dy" in spec:
            dy += q * float(spec["dy"]["max"])
        if "scale" in spec:
            mn = float(spec["scale"]["min"])
            scale *= 1.0 - (1.0 - mn) * q
    return {"dy": dy, "scale": scale, "alpha": alpha}


def transform_element(lc: Dict[str, Any]) -> Optional[str]:
    """The transform motion an element carries (enter preferred), or ``None``."""
    en = (lc.get("enter") or {}).get("motion")
    if en in TRANSFORM_MOTIONS:
        return en
    ex = (lc.get("exit") or {}).get("motion")
    if ex in TRANSFORM_MOTIONS:
        return ex
    return None


# Which transform channel a motion exercises.
_CHANNEL = {"rise": "dy", "sink": "dy", "pop": "scale", "shrink": "scale"}


def observable(el_type: str, motion_name: str,
               contract: Optional[Dict[str, Any]] = None) -> bool:
    """Whether ``motion_name`` on ``el_type`` is observable, per the contract.

    A motion is only adjudicated when its channel is actually rendered for that
    element type. ``dy`` shifts every element's box, so it is observable
    everywhere; ``scale`` is only applied to text/motif geometry. This keeps the
    verdict honest instead of asserting a transform the renderer never applies.
    """
    channel = _CHANNEL.get(motion_name)
    if channel is None:
        return False
    c = contract or load_contract()
    types = (c.get("observability") or {}).get(channel, [])
    return el_type in types
