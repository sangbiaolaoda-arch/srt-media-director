"""Normalize raw browser observations into a deterministic, comparable state.

Quantization absorbs sub-pixel jitter so the same HTML observed twice yields an
identical normalized hash. ``to_world_state`` projects an observation back into
the shared :class:`WorldState` shape, letting the *same* validator judge
observed reality.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple

from world_state.model import Frame, Obj, Relation, WorldState

GRID = 0.5


def quantize(v: float, grid: float = GRID) -> float:
    return round(round(v / grid) * grid, 3)


def normalize_observation(observed: Dict[str, Any]) -> Dict[str, Any]:
    nodes = []
    for n in observed.get("nodes", []):
        nodes.append({
            "id": n["id"],
            "x": quantize(n["x"]), "y": quantize(n["y"]),
            "w": quantize(n["w"]), "h": quantize(n["h"]),
            "opacity": round(float(n.get("opacity", 1)), 3),
            "visible": (n.get("visibility") != "hidden"
                        and n.get("display") != "none"
                        and float(n.get("opacity", 1)) > 0.01
                        and n["w"] > 0 and n["h"] > 0),
            "focus": bool(n.get("focus")),
        })
    nodes.sort(key=lambda n: n["id"])
    edges = sorted(
        ({"source": e["source"], "target": e["target"], "type": e["type"],
          "phase": e.get("phase")} for e in observed.get("edges", [])),
        key=lambda e: (e["source"], e["target"], e["type"]))
    return {"nodes": nodes, "edges": edges}


def normalized_hash(observed: Dict[str, Any]) -> str:
    canon = json.dumps(normalize_observation(observed), sort_keys=True,
                       ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def to_world_state(observed: Dict[str, Any], case_id: str, t: float = 0.0) -> WorldState:
    """Project a single observation into the shared WorldState shape."""
    norm = normalize_observation(observed)
    objects = {n["id"]: Obj(n["id"], visible=n["visible"], focus=n["focus"])
               for n in norm["nodes"]}
    relations = [Relation(e["source"], e["target"], e["type"], e.get("phase") or "active")
                 for e in norm["edges"]]
    return WorldState(case_id, [Frame(t, objects, relations)])


def to_world_state_timeline(observations: List[Tuple[float, Dict[str, Any]]],
                            case_id: str) -> WorldState:
    """Project a replayed observation timeline into the shared WorldState shape.

    ``observations`` is ``[(t, observed), ...]`` from the browser replay. This
    is what lets ``temporal_precedence`` be judged on *observed* reality: the
    observer recovers when each object became the focus, frame by frame.
    """
    frames: List[Frame] = []
    for t, observed in observations:
        norm = normalize_observation(observed)
        objects = {n["id"]: Obj(n["id"], visible=n["visible"], focus=n["focus"])
                   for n in norm["nodes"]}
        relations = [Relation(e["source"], e["target"], e["type"],
                              e.get("phase") or "active")
                     for e in norm["edges"]]
        frames.append(Frame(t, objects, relations))
    return WorldState(case_id, frames)
