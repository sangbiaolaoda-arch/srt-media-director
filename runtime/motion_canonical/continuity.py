"""Canonical cross-beat continuity — one implementation for "keep it continuous".

Merges ``motion/continuity.py``, ``scene/continuity.py`` and the identity part
of ``motion_runtime/identity.py``: an element shared across beats must not
re-enter; it carries over, continues, or transforms, and an element that stops
appearing records an exit.

Easing used for continuity records is the *canonical* easing name; callers
resolve it via :mod:`motion_canonical.easing`.
"""
from __future__ import annotations

from . import transition as _transition

# Default easing for a cross-beat transform (canonical name).
CONTINUITY_EASING = "easeOutCubic"


def link_beats(beat_plans):
    """In-place: mark shared-id elements carry_over / continue / transform.

    Returns a list of per-beat continuity records. Also records an informational
    ``exit`` on elements that disappear in the following beat.
    """
    records = []
    prev = None
    for bp in beat_plans:
        by_id = {e["id"]: e for e in bp["elements"]}
        cont = []
        if prev is not None:
            prev_by_id = {e["id"]: e for e in prev["elements"]}
            shared = set(by_id) & set(prev_by_id)
            for eid in sorted(shared):
                cur, pre = by_id[eid], prev_by_id[eid]
                changed, fields = _transition.detect_state_change(pre, cur)
                mtype = _transition.state_motion(
                    changed, is_focal=(cur.get("semantic_role") == "focal"))
                cur["motion_policy"] = {
                    "type": mtype,
                    "source": "continuity",
                    "role": cur.get("semantic_role"),
                    "duration": 0.6 if mtype == "transform" else 0.0,
                    "delay": 0.0,
                    "easing": CONTINUITY_EASING,
                    "reason": "跨拍延续（%s），不重新入场%s" % (
                        "状态改变→transform" if changed else "保持",
                        ("；变化字段 %s" % fields) if fields else ""),
                    "carry_from": prev["beat_id"],
                    "changed_fields": fields,
                }
                cont.append({"element": eid, "type": mtype,
                             "changed_fields": fields, "from": prev["beat_id"]})
        bp["continuity"] = {
            "carried": cont,
            "shared_with_prev": sorted(
                set(by_id) & set(e["id"] for e in prev["elements"])) if prev else [],
        }
        records.append({"beat_id": bp["beat_id"], "carried": cont})
        prev = bp

    for i, bp in enumerate(beat_plans):
        nxt = beat_plans[i + 1] if i + 1 < len(beat_plans) else None
        if not nxt:
            continue
        nxt_ids = {e["id"] for e in nxt["elements"]}
        for e in bp["elements"]:
            if e["id"] not in nxt_ids and \
                    e.get("motion_policy", {}).get("type") not in ("static", "none"):
                e.setdefault("motion_policy", {})["exit"] = {
                    "type": "fade_out", "requested": True}
    return records
