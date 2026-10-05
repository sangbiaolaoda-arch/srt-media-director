"""Spec §36 — Composition Family: visual grammar, not templates.

A family is a way of *saying* something; its strategies are ways of *drawing*
it. The agent picks by semantic shape, never by "this template looks nice".
Every family must expose >= 1 concrete layout/motion strategy.
"""
from __future__ import annotations

FAMILIES = {
    "Comparison": ["two_column", "split_screen", "mirror"],
    "Conflict": ["facing_shapes", "push_toward", "collision_point"],
    "Hierarchy": ["size_ladder", "top_down", "nested_containers"],
    "Growth": ["bar_rise", "line_up", "stack_up"],
    "Decline": ["bar_fall", "line_down", "fade_shift"],
    "Process": ["arrow_chain", "node_flow", "step_ladder"],
    "Cycle": ["circular_flow", "loop_arrows", "ring_nodes"],
    "Isolation": ["single_figure_void", "closing_frame", "distance_gap"],
    "Accumulation": ["count_up", "pile_up", "many_small"],
    "Expansion": ["scale_out", "distance_open", "camera_out", "branching", "container_grow"],
    "Collapse": ["scale_in", "distance_close", "camera_in", "converge"],
    "Cause-Effect": ["left_cause_right_effect", "arrow_bridge", "chain"],
    "Before-After": ["split_temporal", "wipe_reveal", "two_states"],
    "Timeline": ["horizontal_track", "milestone_marks", "progress_bar"],
    "Network": ["hub_spokes", "mesh", "connected_nodes"],
    "Flow": ["left_to_right_flow", "stream", "funnel"],
}

ALIASES = {
    "grow": "Growth", "decline": "Decline", "compare": "Comparison",
    "comparison": "Comparison", "conflict": "Conflict", "cycle": "Cycle",
    "network": "Network", "flow": "Flow", "timeline": "Timeline",
    "collapse": "Collapse", "expand": "Expansion", "expansion": "Expansion",
    "isolation": "Isolation", "accumulate": "Accumulation", "accumulation": "Accumulation",
    "cause": "Cause-Effect", "cause-effect": "Cause-Effect", "cause_effect": "Cause-Effect",
    "before_after": "Before-After", "before-after": "Before-After",
    "process": "Process", "hierarchy": "Hierarchy", "growth": "Growth",
}


def choose_family(semantic_shape):
    """Map a free semantic shape to a canonical family (or None)."""
    s = (semantic_shape or "").strip()
    low = s.lower().replace("-", "_")
    for fam in FAMILIES:
        if fam.lower() == s.lower() or fam.lower().replace("-", "_") == low:
            return fam
    return ALIASES.get(low)


def strategies(family):
    return list(FAMILIES.get(family, []))


def validate_families():
    bad = [f for f, s in FAMILIES.items() if not s]
    return {"status": "PASS" if not bad else "FAIL",
            "families": len(FAMILIES), "bad": bad}


def audit_beats(beats):
    """Each beat that declares a semantic_shape must resolve to a known family
    and pick one of that family's strategies."""
    issues = []
    for b in beats:
        fam = choose_family(b.get("semantic_shape"))
        if b.get("semantic_shape") and not fam:
            issues.append({"code": "FAMILY_UNKNOWN", "severity": "warn",
                           "beat_id": b.get("beat_id"),
                           "msg": "semantic_shape %r has no family" % b.get("semantic_shape")})
            continue
        if fam and b.get("strategy") and b["strategy"] not in FAMILIES[fam]:
            issues.append({"code": "FAMILY_STRATEGY_MISMATCH", "severity": "warn",
                           "beat_id": b.get("beat_id"),
                           "msg": "strategy %r not in family %s %s"
                                  % (b.get("strategy"), fam, FAMILIES[fam])})
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues}
