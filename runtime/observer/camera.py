"""Independent Camera projection (Final Practical Closeout Directive, P2).

The production chain's Camera layer maps a director's per-beat camera intent
(``visual-dsl.json`` -> ``beat.camera``) to a *uniform magnification* of the
whole composited beat: every element is drawn first, then the finished picture is
scaled about the canvas centre. ``static`` is identity; ``push_in`` ramps a small
zoom in over the back half of the beat so the eye settles on the beat's core.

Until now no *independent* expectation verified that layer. The presence
observer asked "did ink appear?" and the motion observer asked "did the element
arrive with its transform?" — neither noticed that the finished picture is
magnified as a whole.

This module is the *expected* side of that dimension. Like
:mod:`observer.projection` and :mod:`observer.motion`, it is driven by a
declarative, auditable artifact (``contracts/camera_projection.v1.json``) and
**MUST NOT** import the renderer or read the player's embedded ``BEATS``. The
renderer magnifies; this contract adjudicates.

Pure, browser-free and deterministic: given a beat's camera intent and a time,
it returns the magnification the picture *should* have.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "camera_projection.v1.json")

_EPS = 1e-9


def contract_path() -> str:
    return os.environ.get("CAMERA_PROJECTION_CONTRACT", CONTRACT_PATH)


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or contract_path(), encoding="utf-8") as f:
        return json.load(f)


def clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _spec(camera: Optional[Dict[str, Any]],
          contract: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    c = contract or load_contract()
    mode = (camera or {}).get("mode", "static")
    return (c.get("modes") or {}).get(mode)


def observable(camera: Optional[Dict[str, Any]],
               contract: Optional[Dict[str, Any]] = None) -> bool:
    """Whether this camera intent has a formable expectation (known mode).

    A known mode — including ``static`` — is observable: identity is itself a
    falsifiable rendering claim (a renderer that leaked a zoom into a static beat
    would be wrong). An unknown mode is not adjudicated.
    """
    return _spec(camera, contract) is not None


def is_identity(camera: Optional[Dict[str, Any]],
                contract: Optional[Dict[str, Any]] = None) -> bool:
    spec = _spec(camera, contract)
    if spec is None:
        return False
    if "zoom" in spec:
        return abs(float(spec["zoom"]) - 1.0) < _EPS
    return abs(float(spec.get("amplitude", 0.0))) < _EPS


def expected_zoom(camera: Optional[Dict[str, Any]], start: float, end: float,
                  t: float,
                  contract: Optional[Dict[str, Any]] = None) -> float:
    """The magnification ``z`` the composited beat should have at time ``t``.

    Mirrors the declared Camera vocabulary: ``static`` is 1.0 everywhere; a
    ``push_in`` ramps ``1 + amplitude * clamp01(ramp)`` across the back of the
    beat. Nothing is read from the renderer.
    """
    spec = _spec(camera, contract)
    if spec is None:
        # Unknown mode: no magnification claimed.
        return 1.0
    if "zoom" in spec:
        return float(spec["zoom"])
    amp = float(spec.get("amplitude", 0.0))
    dur = max(end - start, _EPS)
    frac = clamp01((t - start - float(spec.get("ramp_start_frac", 0.0)) * dur)
                   / (float(spec.get("ramp_len_frac", 1.0)) * dur + _EPS))
    return 1.0 + amp * frac


def zoom_series(beats: Any, t: float,
                contract: Optional[Dict[str, Any]] = None) -> float:
    """Expected magnification at global time ``t`` for the beat that contains it.

    ``beats`` is the upstream ``visual-dsl.json`` beat list. Used to sanity-check
    a schedule against the plan without ever touching the player.
    """
    for b in beats:
        start = float(b["start_sec"])
        end = float(b["end_sec"])
        if start <= t < end:
            return expected_zoom(b.get("camera"), start, end, t, contract)
    return 1.0
