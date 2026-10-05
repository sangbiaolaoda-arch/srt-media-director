"""Independent Render Projection Contract implementation (Final Directive v5).

This module is the *expected* projection: it maps a WorldState to the observable
DOM/SVG structure that a faithful renderer must produce. It exists so that the
verifier (``fidelity``) and the calibration step never ask the renderer what the
answer is.

Hard rule (§1, §4, §7, §66): this module MUST NOT import
``runtime/observer/render.py``. The renderer draws; this contract adjudicates.
If they shared a decision source, a sabotaged renderer would sabotage the
validator too and the system would be grading its own homework.

The projection is driven by a declarative, auditable artifact
(``contracts/render_projection.v1.json``), not by renderer internals. Changing
the contract changes the expectation; the renderer is untouched.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from world_state.model import WorldState

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "render_projection.v1.json")


def contract_path() -> str:
    return os.environ.get("RENDER_PROJECTION_CONTRACT", CONTRACT_PATH)


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or contract_path(), encoding="utf-8") as f:
        return json.load(f)


def projection_order(ws: WorldState, contract: Optional[Dict[str, Any]] = None) -> List[str]:
    """Order objects by (first-focus time, id) — independently of the renderer."""
    c = contract or load_contract()
    ordering = c["projection"]["ordering"]
    fallback = float(ordering.get("first_focus_fallback", 1e9))

    first_focus: Dict[str, float] = {}
    for f in ws.frames:
        for oid, o in f.objects.items():
            if o.focus and oid not in first_focus:
                first_focus[oid] = f.t

    all_ids: List[str] = []
    seen = set()
    for f in ws.frames:
        for oid in f.objects.keys():
            if oid not in seen:
                seen.add(oid)
                all_ids.append(oid)
    return sorted(all_ids, key=lambda k: (first_focus.get(k, fallback), k))


def expected_layout(ws: WorldState,
                    contract: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, float]]:
    """Expected observable geometry derived from the contract's slot rule."""
    c = contract or load_contract()
    slot = c["projection"]["slot"]
    ox, oy = slot["origin"]
    sx, sy = slot["step"]
    bw, bh = slot["box"]
    order = projection_order(ws, c)
    return {
        oid: {"x": ox + i * sx, "y": oy + i * sy, "w": bw, "h": bh}
        for i, oid in enumerate(order)
    }


def expected_structure(ws: WorldState) -> Dict[str, Any]:
    """Expected identity / visibility / focus / relation endpoints (final frame)."""
    rf = ws.frames[-1]
    return {
        "ids": set(rf.objects.keys()),
        "visible": {oid for oid, o in rf.objects.items() if o.visible},
        "focus": {oid for oid, o in rf.objects.items() if o.focus},
        "edges": {(r.source, r.target, r.type) for r in rf.relations},
    }


def expected(ws: WorldState,
             contract: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Full expected projection bundle: structure + geometry."""
    return {
        "contract_id": (contract or load_contract()).get("contract_id"),
        "structure": expected_structure(ws),
        "geometry": expected_layout(ws, contract),
    }
