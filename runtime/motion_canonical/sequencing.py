"""Canonical motion sequencing — the *relationship* between motions in time.

Sequencing decides *who goes when and how they group*; it does not decide the
animation itself, and it does not own time math — absolute times are produced by
adding durations/delays, i.e. the same span model used by :mod:`timeline`.
"""
from __future__ import annotations

from typing import Dict, List

# Grammar -> sequencing mode (merged from motion/semantics.GRAMMAR_SEQUENCING).
GRAMMAR_SEQUENCING = {
    "branching": "sequential_stagger",
    "accumulation": "sequential_stagger",
    "causality": "chain",
    "progression": "left_to_right",
    "trajectory": "left_to_right",
    "contrast": "split_two_groups",
    "juxtapose": "split_two_groups",
    "hierarchy": "focal_last",
    "emphasis": "focal_last",
    "establish": "ambient_then_focal",
    "threshold": "chain",
}

# Semantic role weights (merged from motion/semantics.ROLE_WEIGHT).
ROLE_WEIGHT = {
    "background": 0.0, "decoration": 0.05, "annotation": 0.35, "label": 0.3,
    "supporting": 0.55, "data": 0.6, "relationship": 0.65, "focal": 1.0,
}

NO_MOTION_ROLES = ("background", "decoration")

ROLE_ALIAS = {
    "primary": "focal", "hero": "focal", "focal": "focal",
    "secondary": "supporting", "support": "supporting", "supporting": "supporting",
    "ambient": "background", "background": "background",
    "decor": "decoration", "decoration": "decoration",
    "connect": "relationship", "connector": "relationship",
    "relationship": "relationship",
    "note": "annotation", "annotation": "annotation",
    "data": "data", "label": "label",
}


def normalize_role(role):
    if not role:
        return None
    return ROLE_ALIAS.get(str(role).strip().lower(), role)


def mode_for_grammar(grammar) -> str:
    if not grammar:
        return "ambient_then_focal"
    if isinstance(grammar, (list, tuple)):
        grammar = grammar[0] if grammar else "establish"
    return GRAMMAR_SEQUENCING.get(grammar, "ambient_then_focal")


# ---------------------------------------------------------------- combinators
def sequence(specs: List[dict], start: float = 0.0) -> List[dict]:
    """Each spec starts after the previous ends (duration + delay)."""
    out, t = [], start
    for s in specs:
        s = dict(s)
        s["start"] = t
        out.append(s)
        t += s.get("duration", 0.5) + s.get("delay", 0.0)
    return out


def parallel(specs: List[dict], start: float = 0.0) -> List[dict]:
    out = []
    for s in specs:
        s = dict(s)
        s["start"] = start
        out.append(s)
    return out


def stagger(specs: List[dict], offset: float = 0.1, start: float = 0.0) -> List[dict]:
    out = []
    for i, s in enumerate(specs):
        s = dict(s)
        s["start"] = start + i * offset
        out.append(s)
    return out


def dependency(specs: List[dict], deps: Dict[int, int], start: float = 0.0) -> List[dict]:
    """spec[i] starts after spec[deps[i]] finishes."""
    out = [dict(s) for s in specs]
    for i, s in enumerate(out):
        if i in deps:
            j = deps[i]
            if "start" in out[j] and "duration" in out[j]:
                s["start"] = out[j]["start"] + out[j]["duration"]
    for s in out:
        s.setdefault("start", start)
    return out


def cues_from_lifecycle(life, elements, start, dur) -> List[dict]:
    """Group elements that enter at the same time into cues (read-only view)."""
    groups = {}
    for el in elements:
        e = life[el["id"]]["enter"]
        groups.setdefault(round(e["at"], 3), []).append(el["id"])
    cues = []
    for i, at in enumerate(sorted(groups)):
        cues.append({
            "cue_id": "cue_%d" % (i + 1),
            "at": at,
            "at_ratio": round((at - start) / dur, 3),
            "purpose": "wave_%d" % (i + 1),
            "elements": sorted(groups[at]),
        })
    return cues
