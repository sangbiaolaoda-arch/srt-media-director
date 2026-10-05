"""Phase 0 "Runtime" — a deterministic director stand-in.

In Phase 0 there is no browser and no renderer. To prove the validator is
*falsifiable* we need a runtime that is (a) deterministic and (b) can be made
to emit a specific defect on demand. This module is that runtime.

It is intentionally tiny and honest: it emits the world state a correct
director *should* produce for a single-claim anchor, driven by the audited
contract (so FOLLOWS / CONNECTS / CAUSES all route through the same code), and
flags let a test inject exactly one defect the validator must catch.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model import Frame, Obj, Relation, WorldState


def _relation_type(contract: Dict[str, Any]) -> Optional[str]:
    """A contract may (or may not) entail a directed relation."""
    for rule in contract["entailment"]:
        if rule["kind"] == "relation_direction":
            return rule["relation_type"]
    return None


def _resolve_contract(anchor: Dict[str, Any], contract: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if contract is not None:
        return contract
    from entailment import load_contract  # local import: keep core import-light
    return load_contract(anchor["claims"][0]["contract"])


def compile_world_state(anchor: Dict[str, Any], *,
                        contract: Optional[Dict[str, Any]] = None,
                        reverse_direction: bool = False,
                        drop_staging: bool = False) -> WorldState:
    """Emit a deterministic :class:`WorldState` for a single-claim anchor.

    Fault injection (test-only, never used in production paths):
      * ``reverse_direction`` : emit the relation and focus order backwards
        (effect -> cause), i.e. a *runtime* defect.
      * ``drop_staging``      : skip the ``establishing`` phase, i.e. a
        *staging* (soft) defect that must NOT cause a hard failure.
    """
    if len(anchor["claims"]) != 1:
        raise ValueError("Phase 0 compiler handles exactly one claim")
    contract = _resolve_contract(anchor, contract)
    claim = anchor["claims"][0]
    subj, obj = claim["subject"], claim["object"]
    rel_type = _relation_type(contract)

    if reverse_direction:
        subj, obj = obj, subj

    def frame(t: float, focus: str, phase: Optional[str]) -> Frame:
        objects = {
            claim["subject"]: Obj(claim["subject"], visible=True, focus=False),
            claim["object"]: Obj(claim["object"], visible=True, focus=False),
        }
        objects[focus].focus = True
        relations: List[Relation] = []
        if phase is not None and rel_type is not None:
            relations = [Relation(subj, obj, rel_type, phase)]
        return Frame(t, objects, relations)

    def phase_at(order: int) -> Optional[str]:
        # order: 1 = first relation keyframe, 2 = subsequent ones
        if rel_type is None:
            return None
        if drop_staging:
            return "active"
        return "establishing" if order == 1 else "active"

    # canonical timeline: cause established -> relation engaged -> effect focus
    frames = [
        frame(0.0, subj, None),
        frame(1.0, subj, phase_at(1)),
        frame(2.0, subj, phase_at(2)),
        frame(3.0, obj, phase_at(2)),
        frame(4.0, obj, None),
    ]
    return WorldState(anchor["case_id"], frames)
