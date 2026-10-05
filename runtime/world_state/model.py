"""World-State model (Phase 0) — browser-free structured state.

A :class:`WorldState` is a deterministic, ordered list of keyframes. Each
keyframe records the render state of named objects and the active typed
relations at a discrete time. It is the single structure that both:

  * the Runtime (a director stand-in) *emits*, and
  * the Validator *consumes*.

Phase 0 is deliberately browser-free. The later Browser Observer must emit
exactly this structure; nothing here depends on Playwright or the DOM. Keeping
the model pure-data is what makes the falsifiable loop trustworthy: the
validator can never "see" the render, only the structured claim about it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Obj:
    """A named object in the scene (a node the director placed)."""

    id: str
    visible: bool = True
    focus: bool = False  # is this object what the current beat is *about*?

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "visible": self.visible, "focus": self.focus}


@dataclass
class Relation:
    """A typed, *directed* relation active at a keyframe.

    ``phase`` follows the casebook staging vocabulary:
    ``establishing`` -> ``active`` (-> ``resolved``).
    """

    source: str
    target: str
    type: str
    phase: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "phase": self.phase,
        }


@dataclass
class Frame:
    """A single keyframe of the world state."""

    t: float
    objects: Dict[str, Obj] = field(default_factory=dict)
    relations: List[Relation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": self.t,
            "objects": {k: v.to_dict() for k, v in self.objects.items()},
            "relations": [r.to_dict() for r in self.relations],
        }


@dataclass
class WorldState:
    """An ordered timeline of keyframes for one case."""

    case_id: str
    frames: List[Frame] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "frames": [f.to_dict() for f in self.frames],
        }

    # --- semantic projection -------------------------------------------------
    def facts(self) -> Dict[str, Any]:
        """Project the raw timeline into *semantic facts*.

        The Validator checks semantics, never raw JSON shape. Every predicate
        the entailment contracts can talk about is derived here:

        * ``relation_dirs``  : set of ``(source, target, type)`` triples
        * ``relation_types`` : set of relation type names
        * ``first_focus``    : first time each object became the focus
        * ``last_focus``     : the focus object of the final frame
        * ``phase_seq``      : ordered distinct phase runs per relation key
        """
        relation_dirs: set = set()
        relation_types: set = set()
        for f in self.frames:
            for r in f.relations:
                relation_dirs.add((r.source, r.target, r.type))
                relation_types.add(r.type)

        first_focus: Dict[str, float] = {}
        for f in self.frames:
            for oid, o in f.objects.items():
                if o.focus and oid not in first_focus:
                    first_focus[oid] = f.t

        last_focus: Optional[str] = None
        if self.frames:
            focused = [oid for oid, o in self.frames[-1].objects.items() if o.focus]
            if focused:
                last_focus = sorted(focused)[0]

        phase_seq: Dict[Tuple[str, str, str], List[str]] = {}
        for f in self.frames:
            for r in f.relations:
                key = (r.source, r.target, r.type)
                seq = phase_seq.setdefault(key, [])
                if not seq or seq[-1] != r.phase:
                    seq.append(r.phase)

        return {
            "relation_dirs": relation_dirs,
            "relation_types": relation_types,
            "first_focus": first_focus,
            "last_focus": last_focus,
            "phase_seq": phase_seq,
        }
