"""Spec §38/§39 — Scene-level Style Lock + reuse-first priority.

Within a scene, font / stroke / radius / line-weight / icon / chart / motion
style must stay consistent; different scenes may differ. §39 reuse order:
entity > motif > style > layout > animation > new.
"""
from __future__ import annotations

KEYS = ("font", "stroke", "radius", "line_weight", "icon_style",
        "chart_style", "motion_style")

REUSE_ORDER = ("entity", "motif", "style", "layout", "animation", "new")


def lock_from(beats_of_scene):
    """Derive the scene style from the first beat that declares each key."""
    lock = {}
    for b in beats_of_scene:
        st = b.get("style") or {}
        for k in KEYS:
            if k not in lock and k in st:
                lock[k] = st[k]
    return lock


def audit_style_lock(beats_of_scene):
    lock = lock_from(beats_of_scene)
    issues = []
    for b in beats_of_scene:
        st = b.get("style") or {}
        for k in KEYS:
            if k in st and k in lock and st[k] != lock[k]:
                issues.append({"code": "STYLE_LOCK_VIOLATION", "severity": "warn",
                               "beat_id": b.get("beat_id"),
                               "msg": "%s: %r != scene %r" % (k, st[k], lock[k])})
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "lock": lock, "issues": issues}


def group_by_scene(beats):
    """Split a flat beat list into scenes by scene_id (default: one scene)."""
    scenes = {}
    for b in beats:
        scenes.setdefault(b.get("scene_id", "__default__"), []).append(b)
    return scenes


def audit_plan(plan):
    issues = []
    for scene_id, bs in group_by_scene(plan.get("beats", [])).items():
        r = audit_style_lock(bs)
        for i in r["issues"]:
            i["scene_id"] = scene_id
            issues.append(i)
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues}


def reuse_decision(have, need):
    """Given available asset categories `have` and desired `need`, return the
    earliest matching category per §39 priority (else 'new')."""
    for cat in REUSE_ORDER:
        if cat in have and need.get(cat):
            return cat
    return "new"
