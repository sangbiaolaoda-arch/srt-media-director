"""Easing divergence audit (code-capability upgrade).

Measures how far each subsystem's easing implementation drifts from the canonical
vocabulary in :mod:`timeline.easing`. Findings are *evidence*, not failures: the
audit exists so that "the Agent described one curve and two render paths drew
two curves" is a visible, quantified fact instead of a silent bug.

Every ``audit_*`` function returns a list of divergence records::

    {"source": <module>, "name": <spelling as used there>,
     "canonical": <canonical id>, "max_delta": <float 0..~1>, "severity": <str>}

``max_delta`` is the max absolute difference over 101 samples on [0, 1].
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import easing

_SAMPLES = 101


def _max_delta(a, b) -> float:
    worst = 0.0
    for i in range(_SAMPLES):
        p = i / (_SAMPLES - 1)
        worst = max(worst, abs(float(a(p)) - float(b(p))))
    return worst


def _severity(delta: float) -> str:
    if delta <= 1e-6:
        return "match"
    if delta < 0.02:
        return "minor"
    if delta < 0.1:
        return "material"
    return "severe"


def _rec(source: str, name: Any, canonical: Any, theirs, max_delta: float) -> Dict[str, Any]:
    return {"source": source, "name": name, "canonical": canonical,
            "max_delta": round(max_delta, 6), "severity": _severity(max_delta),
            "theirs": getattr(theirs, "__name__", str(theirs))}


def audit_motion_runtime() -> List[Dict[str, Any]]:
    """motion_runtime.contracts.EASINGS vs canonical (same-name curves)."""
    out: List[Dict[str, Any]] = []
    try:
        from motion_runtime import contracts as c  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "motion_runtime.contracts", "error": repr(e)}]
    for name, fn in getattr(c, "EASINGS", {}).items():
        canon = easing.resolve(name)
        if canon is None:
            out.append({"source": "motion_runtime.contracts", "name": name,
                        "canonical": None, "max_delta": None,
                        "severity": "unknown-name", "theirs": getattr(fn, "__name__", str(fn))})
            continue
        out.append(_rec("motion_runtime.contracts", name, easing.canonical_name(name), fn,
                        _max_delta(fn, canon)))
    return out


def audit_motion_render() -> List[Dict[str, Any]]:
    """motion.render._ease vs canonical, incl. an emitted cubic-bezier string."""
    names = ["linear", "ease-out", "ease-in", "ease-in-out", "cubic-bezier(.2,.7,.2,1)"]
    out: List[Dict[str, Any]] = []
    try:
        from motion import render as r  # type: ignore
        fn = getattr(r, "_ease")
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "motion.render._ease", "error": repr(e)}]
    for name in names:
        canon = easing.resolve(name)
        if canon is None:
            continue
        out.append(_rec("motion.render._ease", name, easing.canonical_name(name),
                        lambda p, _n=name: fn(_n, p), _max_delta(lambda p, _n=name: fn(_n, p), canon)))
    return out


def audit_observer_motion() -> List[Dict[str, Any]]:
    """observer.motion.ease (smoothstep) vs canonical smoothstep."""
    try:
        from observer import motion as m  # type: ignore
        fn = getattr(m, "ease")
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "observer.motion.ease", "error": repr(e)}]
    return [_rec("observer.motion.ease", "smoothstep", "smoothstep", fn,
                 _max_delta(fn, easing.resolve("smoothstep")))]


def audit_raster() -> List[Dict[str, Any]]:
    """raster_renderer._ease (smoothstep) vs canonical smoothstep."""
    try:
        import raster_renderer as rr  # type: ignore
        fn = getattr(rr, "_ease")
    except Exception as e:  # pragma: no cover - import guard
        return [{"source": "raster_renderer._ease", "error": repr(e)}]
    return [_rec("raster_renderer._ease", "smoothstep", "smoothstep", fn,
                 _max_delta(fn, easing.resolve("smoothstep")))]


def divergences() -> List[Dict[str, Any]]:
    """All divergence records across the audited subsystems."""
    out: List[Dict[str, Any]] = []
    for fn in (audit_motion_runtime, audit_motion_render, audit_observer_motion, audit_raster):
        out.extend(fn())
    return out


def diverging() -> List[Dict[str, Any]]:
    """Only records whose curve materially differs from canonical."""
    return [d for d in divergences() if d.get("severity") in ("material", "severe", "unknown-name")]
