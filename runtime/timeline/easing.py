"""Canonical easing / time-parameterization vocabulary (code-capability upgrade).

The project already animates well, but the *same easing name* means different
curves in different subsystems:

* ``motion_runtime.contracts.EASINGS['easeOut']``  -> quadratic  1-(1-p)^2
* ``motion.render._ease('ease-out')``              -> cubic      1-(1-p)^3
* ``motion.render._ease('cubic-bezier(...)')``     -> IGNORED (falls back to smoothstep)
* ``motion_registry`` emits ``cubic-bezier(.2,.7,.2,1)`` style strings
* ``raster_renderer._ease`` / ``observer.motion.ease`` -> smoothstep

So when the Agent declares ``easing: "ease-out"``, different render/observe paths
disagree about the resulting motion. This module is the single source of truth:
one name -> one curve, with alias resolution (camel / kebab / snake / CSS
keyword) and real ``cubic-bezier`` evaluation, plus a pure time-parameterization
helper :func:`pr`.

Pure, browser-free, deterministic, no project imports.
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "easing_vocabulary.v1.json")

_EPS = 1e-9


# --------------------------------------------------------------------- basics


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation; ``t`` is NOT clamped (callers may extrapolate)."""
    return a + (b - a) * t


def mix(a: float, b: float, t: float) -> float:
    """Alias of :func:`lerp` for readability in visual code."""
    return lerp(a, b, t)


# ---------------------------------------------------------- cubic-bezier solver


def _bezier_axis(t: float, a1: float, a2: float) -> float:
    """Coordinate on one axis of a cubic-bezier with P0=0, P3=1."""
    mt = 1.0 - t
    return 3.0 * mt * mt * t * a1 + 3.0 * mt * t * t * a2 + t * t * t


def _bezier_y_for_x(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Invert x(t) for t via bisection (monotone for x1,x2 in [0,1]), then y(t)."""
    x = clamp01(x)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        xm = _bezier_axis(mid, x1, x2)
        if xm < x:
            lo = mid
        else:
            hi = mid
    t = (lo + hi) / 2.0
    return _bezier_axis(t, y1, y2)


def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> Callable[[float], float]:
    def curve(p: float) -> float:
        return _bezier_y_for_x(clamp01(p), x1, y1, x2, y2)
    curve.__name__ = "cubic-bezier(%g,%g,%g,%g)" % (x1, y1, x2, y2)
    return curve


_BEZIER_RE = re.compile(
    r"^\s*cubic-bezier\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,"
    r"\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)\s*$")


# ------------------------------------------------------------------ named set


def _linear(p: float) -> float:
    return p


def _smoothstep(p: float) -> float:
    return p * p * (3.0 - 2.0 * p)


def _in_quad(p: float) -> float:
    return p * p


def _out_quad(p: float) -> float:
    return 1.0 - (1.0 - p) * (1.0 - p)


def _in_out_quad(p: float) -> float:
    return 2.0 * p * p if p < 0.5 else 1.0 - 2.0 * (1.0 - p) * (1.0 - p)


def _in_cubic(p: float) -> float:
    return p ** 3


def _out_cubic(p: float) -> float:
    return 1.0 - (1.0 - p) ** 3


def _in_out_cubic(p: float) -> float:
    return 4.0 * p ** 3 if p < 0.5 else 1.0 - (-2.0 * p + 2.0) ** 3 / 2.0


def _in_quart(p: float) -> float:
    return p ** 4


def _out_quart(p: float) -> float:
    return 1.0 - (1.0 - p) ** 4


def _in_sine(p: float) -> float:
    return 1.0 - math.cos((p * math.pi) / 2.0)


def _out_sine(p: float) -> float:
    return math.sin((p * math.pi) / 2.0)


def _in_out_sine(p: float) -> float:
    return -(math.cos(math.pi * p) - 1.0) / 2.0


def _in_expo(p: float) -> float:
    return 0.0 if p <= 0.0 else (1.0 if p >= 1.0 else 2.0 ** (10.0 * p - 10.0))


def _out_expo(p: float) -> float:
    return 1.0 if p >= 1.0 else (0.0 if p <= 0.0 else 1.0 - 2.0 ** (-10.0 * p))


def _in_back(p: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * p ** 3 - c1 * p * p


def _out_back(p: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (p - 1.0) ** 3 + c1 * (p - 1.0) ** 2


def _in_out_back(p: float) -> float:
    c1 = 1.70158
    c2 = c1 * 1.525
    if p < 0.5:
        return ((2.0 * p) ** 2 * ((c2 + 1.0) * 2.0 * p - c2)) / 2.0
    return ((2.0 * p - 2.0) ** 2 * ((c2 + 1.0) * (p * 2.0 - 2.0) + c2) + 2.0) / 2.0


def _out_elastic(p: float) -> float:
    c4 = (2.0 * math.pi) / 3.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    return 2.0 ** (-10.0 * p) * math.sin((p * 10.0 - 0.75) * c4) + 1.0


def _out_bounce(p: float) -> float:
    n1 = 7.5625
    d1 = 2.75
    if p < 1.0 / d1:
        return n1 * p * p
    if p < 2.0 / d1:
        p -= 1.5 / d1
        return n1 * p * p + 0.75
    if p < 2.5 / d1:
        p -= 2.25 / d1
        return n1 * p * p + 0.9375
    p -= 2.625 / d1
    return n1 * p * p + 0.984375


_NAMED: Dict[str, Callable[[float], float]] = {
    "linear": _linear,
    "smoothstep": _smoothstep,
    "easeInQuad": _in_quad, "easeOutQuad": _out_quad, "easeInOutQuad": _in_out_quad,
    "easeInCubic": _in_cubic, "easeOutCubic": _out_cubic, "easeInOutCubic": _in_out_cubic,
    "easeInQuart": _in_quart, "easeOutQuart": _out_quart,
    "easeInSine": _in_sine, "easeOutSine": _out_sine, "easeInOutSine": _in_out_sine,
    "easeInExpo": _in_expo, "easeOutExpo": _out_expo,
    "easeInBack": _in_back, "easeOutBack": _out_back, "easeInOutBack": _in_out_back,
    "easeOutElastic": _out_elastic, "easeOutBounce": _out_bounce,
    # W3C keywords under explicit css* names (see contract)
    "cssEase": cubic_bezier(0.25, 0.1, 0.25, 1.0),
    "cssEaseIn": cubic_bezier(0.42, 0.0, 1.0, 1.0),
    "cssEaseOut": cubic_bezier(0.0, 0.0, 0.58, 1.0),
    "cssEaseInOut": cubic_bezier(0.42, 0.0, 0.58, 1.0),
}


def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(name)).lower()


_ALIASES: Dict[str, str] = {_norm(k): k for k in _NAMED}
# extra human spellings mapped onto canonical names
_ALIASES.update({
    "easein": "easeInQuad",
    "easeout": "easeOutQuad",
    "easeinout": "easeInOutQuad",
    "ease": "cssEase",
})


# ------------------------------------------------------------------- public API


def canonical_names() -> List[str]:
    return list(_NAMED.keys())


def resolve(name: Any) -> Optional[Callable[[float], float]]:
    """Return the canonical curve for ``name`` or ``None`` if unknown.

    Accepts a named easing, an alias, or a ``cubic-bezier(...)`` string.
    ``None``/empty resolves to ``linear`` (the honest default).
    """
    if name is None or (isinstance(name, str) and name.strip() == ""):
        return _NAMED["linear"]
    s = str(name)
    m = _BEZIER_RE.match(s)
    if m:
        return cubic_bezier(*[float(g) for g in m.groups()])
    key = _ALIASES.get(_norm(s))
    return _NAMED.get(key) if key else None


def canonical_name(name: Any) -> Optional[str]:
    """The canonical identifier for ``name`` (or a normalized bezier descriptor)."""
    if name is None or (isinstance(name, str) and name.strip() == ""):
        return "linear"
    s = str(name)
    m = _BEZIER_RE.match(s)
    if m:
        return "cubic-bezier(" + ",".join("%g" % float(g) for g in m.groups()) + ")"
    key = _ALIASES.get(_norm(s))
    return key


def is_known(name: Any) -> bool:
    return resolve(name) is not None


def evaluate(name: Any, p: float) -> float:
    """Eased value of progress ``p`` in [0, 1] under easing ``name``.

    Unknown names fall back to linear (never raise), so a malformed Agent value
    degrades to a defined curve instead of breaking the render.
    """
    fn = resolve(name)
    pp = clamp01(p)
    return fn(pp) if fn else pp


def curve(name: Any) -> Callable[[float], float]:
    return resolve(name) or _NAMED["linear"]


def pr(t: float, start: float, end: float, easing: Any = "linear") -> float:
    """Pure time-parameterization: eased progress of a span [start, end] at time t.

    * before the span -> 0.0; after the span -> 1.0 (eased endpoint)
    * a zero/negative span is treated as an instantaneous step (0 -> 1)
    """
    if end <= start:
        return 1.0 if t >= end else 0.0
    return evaluate(easing, clamp01((t - start) / (end - start)))


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)
