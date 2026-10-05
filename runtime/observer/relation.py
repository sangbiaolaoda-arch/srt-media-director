"""Independent Relation (semantic) projection (Final Practical Closeout Directive, P2).

The production chain's Relation layer realizes the director's declared per-beat
relations (``visual-dsl.json`` -> ``beat.relations``, each ``{from, to, type}``)
as a *visible link* between the two named elements. The presence observer asked
"did ink appear?" and the motion/camera observers asked about per-element motion
and whole-frame magnification — none of them noticed whether a declared
relationship is actually *drawn as a legible link*.

The film realizes relations two ways:

* ``flow_to`` / ``causes`` -> a **connector** element bridges the two endpoints:
  it sits in the horizontal corridor between their facing edges, at their
  vertical middle. A relation with nothing in the corridor is a dangling claim.
* ``bound_to`` -> the subject label is **bound onto** its target: its painted ink
  is horizontally centred on the target and sits within a small margin of it.

This module is the *expected* side. Like :mod:`observer.projection`,
:mod:`observer.motion` and :mod:`observer.camera`, it is driven by a declarative,
auditable artifact (``contracts/relation_projection.v1.json``) and **MUST NOT**
import the renderer or read the player's embedded ``BEATS``.

Pure, browser-free and deterministic: given the upstream relations and element
boxes, it returns the geometry the link *should* occupy.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "relation_projection.v1.json")


def contract_path() -> str:
    return os.environ.get("RELATION_PROJECTION_CONTRACT", CONTRACT_PATH)


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or contract_path(), encoding="utf-8") as f:
        return json.load(f)


def center(box: Dict[str, Any]) -> "tuple[float, float]":
    return float(box["x"]) + float(box["w"]) / 2.0, float(box["y"]) + float(box["h"]) / 2.0


def realization(rtype: Optional[str],
                contract: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    c = contract or load_contract()
    return (c.get("realizations") or {}).get(rtype)


def observable(rtype: Optional[str],
               contract: Optional[Dict[str, Any]] = None) -> bool:
    """Whether this relation type has a formable expectation (known realization)."""
    return realization(rtype, contract) is not None


def channel(rtype: Optional[str],
            contract: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    c = contract or load_contract()
    r = realization(rtype, c)
    if not r:
        return None
    return (c.get("channels") or {}).get(r.get("channel"))


def bridge_expectation(fb: Dict[str, Any], tb: Dict[str, Any],
                       contract: Optional[Dict[str, Any]] = None
                       ) -> Optional[Dict[str, Any]]:
    """The corridor a bridging connector ink should occupy, or ``None`` if the
    endpoints are not horizontally separated (no corridor exists)."""
    c = contract or load_contract()
    tol = float((c.get("tolerance") or {}).get("corridor_px", 18))
    band = float((c.get("tolerance") or {}).get("band_px", 30))
    min_w = float(c.get("min_bridge_px", 110))
    fcx, fcy = center(fb)
    tcx, tcy = center(tb)
    left, right = (fb, tb) if fcx <= tcx else (tb, fb)
    lx = float(left["x"]) + float(left["w"])   # left box's facing (right) edge
    rx = float(right["x"])                      # right box's facing (left) edge
    if rx <= lx:                                # boxes overlap horizontally: no corridor
        return None
    return {
        "channel": "bridge_corridor",
        "x0": lx - tol, "x1": rx + tol,
        "y0": min(fcy, tcy) - band, "y1": max(fcy, tcy) + band,
        "min_w": min_w, "span": rx - lx,
        "element_type": ((channel("flow_to", c) or {}).get("element_type") or "connector"),
    }


def find_bridge(elements: List[Dict[str, Any]], boxes: Dict[str, Any],
                exp: Dict[str, Any],
                contract: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """The id of the connector element that occupies the corridor, if any."""
    want = exp.get("element_type") or "connector"
    for el in elements:
        if el.get("type") != want:
            continue
        eid = el.get("id")
        box = boxes.get(eid)
        if not box:
            continue
        cx, cy = center(box)
        if exp["x0"] <= cx <= exp["x1"] and exp["y0"] <= cy <= exp["y1"]:
            return eid
    return None


def align_expectation(fb: Dict[str, Any], tb: Dict[str, Any],
                      contract: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Where a bound label's painted ink should sit relative to its target."""
    c = contract or load_contract()
    ch = channel("bound_to", c) or {}
    tcx, _ = center(tb)
    return {
        "channel": "align_x",
        "target_cx": tcx,
        "target_box": {k: float(tb[k]) for k in ("x", "y", "w", "h")},
        "bind_margin": float(ch.get("bind_margin_px", 130)),
        "align_px": float((c.get("tolerance") or {}).get("align_px", 16)),
    }


def point_to_box_dist(px: float, py: float, box: Dict[str, Any]) -> float:
    """Euclidean distance from a point to an axis-aligned box (0 if inside)."""
    x0, y0 = float(box["x"]), float(box["y"])
    x1, y1 = x0 + float(box["w"]), y0 + float(box["h"])
    dx = max(x0 - px, 0.0, px - x1)
    dy = max(y0 - py, 0.0, py - y1)
    return (dx * dx + dy * dy) ** 0.5
