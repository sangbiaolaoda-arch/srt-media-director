"""Phase 0 "Runtime" — a deterministic director stand-in.

In Phase 0 there is no browser and no renderer. To prove the validator is
*falsifiable* we need a runtime that is (a) deterministic and (b) can be made
to emit a specific defect on demand. This module is that runtime.

It is intentionally tiny and honest: it emits the world state a correct
director *should* produce for a single CAUSES claim, and flags let a test
inject exactly one defect the validator must catch.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model import Frame, Obj, Relation, WorldState

_PREDICATE_TO_TYPE = {"CAUSES": "causes"}


def compile_world_state(anchor: Dict[str, Any], *,
                        reverse_direction: bool = False,
                        drop_staging: bool = False) -> WorldState:
    """Emit a :class:`WorldState` for a single-claim anchor.

    Fault injection (test-only, never used in production paths):
      * ``reverse_direction`` : emit the relation and focus order backwards
        (effect -> cause), i.e. a *runtime* defect.
      * ``drop_staging``      : skip the ``establishing`` phase, i.e. a
        *staging* (soft) defect that must NOT cause a hard failure.
    """
    if len(anchor["claims"]) != 1:
        raise ValueError("Phase 0 compiler handles exactly one claim")
    claim = anchor["claims"][0]
    subj, obj = claim["subject"], claim["object"]
    rel_type = _PREDICATE_TO_TYPE.get(claim["predicate"], claim["predicate"].lower())
    if reverse_direction:
        subj, obj = obj, subj

    # objects always keep their canonical identity; only focus-order and the
    # relation direction are affected by the injected runtime fault.
    def frame(t: float, focus: str, phase: Optional[str] = None) -> Frame:
        objects = {
            claim["subject"]: Obj(claim["subject"], visible=True, focus=False),
            claim["object"]: Obj(claim["object"], visible=True, focus=False),
        }
        objects[focus].focus = True
        relations: List[Relation] = []
        if phase is not None:
            relations = [Relation(subj, obj, rel_type, phase)]
        return Frame(t, objects, relations)

    phases = ["active"] if drop_staging else ["establishing", "active"]
    frames = [
        frame(0.0, subj),
        frame(1.0, subj, phases[0]),
        frame(2.0, subj, phases[-1]),
        frame(3.0, obj, phases[-1]),
        frame(4.0, obj, phases[-1]),
    ]
    return WorldState(anchor["case_id"], frames)
