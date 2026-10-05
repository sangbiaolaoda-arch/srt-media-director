"""Spec §6/§7/§8/§23 — Continuity Graph: entity-level continuity across beats.

Every entity keeps a stable id. If a beat still contains an entity, the default
is PERSIST (never a destroy+recreate). This module builds the entity graph and
audits whether a plan illegally resets the visuals between beats.
"""
from __future__ import annotations

# §7 — the transition vocabulary an entity may undergo between beats.
TRANSITIONS = ("PERSIST", "MOVE", "SCALE", "ROTATE", "TRANSFORM",
               "DUPLICATE", "SPLIT", "MERGE", "HIDE", "EXIT", "REENTER")

# §8/§23 — state change is preferred over hard replacement; these are the
# in-place actions that keep continuity.
IN_PLACE = {"PERSIST", "MOVE", "SCALE", "ROTATE", "TRANSFORM", "HIDE"}


def entity_ids(beat):
    return [e.get("id") for e in beat.get("elements", [])]


def _declared(beat, eid):
    for a in beat.get("continuity", []) or []:
        if a.get("entity") == eid:
            return a
    return None


def build_continuity_graph(beats):
    """Return {'nodes':[{id, beats}], 'edges':[{from_beat,to_beat,entity,action}]}."""
    nodes = {}
    edges = []
    prev_ids = None
    prev_beat = None
    for b in beats:
        ids = list(entity_ids(b))
        idset = set(ids)
        for eid in ids:
            nodes.setdefault(eid, {"id": eid, "beats": []})
            nodes[eid]["beats"].append(b.get("beat_id"))
        if prev_ids is not None:
            for eid in sorted(idset & prev_ids):
                act = _declared(b, eid) or {"action": "PERSIST"}
                edges.append({"from_beat": prev_beat, "to_beat": b.get("beat_id"),
                              "entity": eid, "action": act.get("action", "PERSIST")})
            for eid in sorted(prev_ids - idset):
                edges.append({"from_beat": prev_beat, "to_beat": b.get("beat_id"),
                              "entity": eid, "action": "EXIT"})
            for eid in sorted(idset - prev_ids):
                edges.append({"from_beat": prev_beat, "to_beat": b.get("beat_id"),
                              "entity": eid, "action": "REENTER"})
        prev_ids = idset
        prev_beat = b.get("beat_id")
    return {"nodes": list(nodes.values()), "edges": edges}


def audit_continuity(beats, allow_scene_changes=None):
    """Flag a visual reset (no shared entity and no declared scene change)."""
    allow = set(allow_scene_changes or [])
    issues = []
    prev = None
    for b in beats:
        if prev is not None:
            shared = set(entity_ids(prev)) & set(entity_ids(b))
            bid = b.get("beat_id")
            if not shared and bid not in allow and not b.get("scene_change"):
                issues.append({"code": "CONTINUITY_RESET", "severity": "warn",
                               "beat_id": bid,
                               "msg": "no shared entity with previous beat "
                                      "(visual reset without scene_change)"})
            # invalid transition vocabulary
            for a in b.get("continuity", []) or []:
                if a.get("action") and a["action"] not in TRANSITIONS:
                    issues.append({"code": "CONTINUITY_ACTION_UNKNOWN", "severity": "err",
                                   "beat_id": bid,
                                   "msg": "unknown action %r" % a["action"]})
        prev = b
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues}


def persist_ratio(beats):
    """Fraction of cross-beat entity links that are in-place (continuity kept)."""
    g = build_continuity_graph(beats)
    links = [e for e in g["edges"] if e["action"] != "REENTER"]
    if not links:
        return 1.0
    good = [e for e in links if e["action"] in IN_PLACE]
    return round(len(good) / len(links), 4)
