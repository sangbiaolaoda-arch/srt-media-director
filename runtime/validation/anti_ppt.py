"""Spec §28 — Anti-PPT checks (7 gates) + §34 no gaming the validator.

The classic slide smell set. Codes are stable and consumable by the spec audit
registry. A missing trigger is a PASS; presence raises a WARN (or ERR when the
caller requests strict mode).
"""
from __future__ import annotations

MOVING = ("fade", "rise", "pop", "slide", "scale", "draw", "grow", "emerge",
          "reveal", "expand", "converge", "diverge", "rotate", "wipe")


def _i(bid, code, msg=None):
    return {"severity": "warn", "layer": "anti_ppt", "code": code,
            "beat_id": bid, "msg": msg or code.replace("_", " ").lower()}


def check_beat(beat):
    issues = []
    bid = beat.get("beat_id")
    els = [e for e in beat.get("elements", []) if e.get("visible", True)]
    boxes = beat.get("boxes") or {}
    texts = [e for e in els if e.get("type") == "text"]
    titles = [t for t in texts if t.get("size") in ("title", "heading")]
    bullets = [t for t in texts if t.get("size") in ("bullet", "list", "note")]
    icons = [e for e in els if e.get("type") in ("motif", "icon", "shape")]

    # 1) title + icon + >= 3 bullets
    if titles and icons and len(bullets) >= 3:
        issues.append(_i(bid, "PPT_TITLE_ICON_BULLETS"))

    # 2) perfectly even distribution
    if (beat.get("visual_balance") or {}).get("even") is True:
        issues.append(_i(bid, "PPT_EVEN_DISTRIBUTION"))

    # 3) all text stacked at the bottom
    tb = [boxes.get(t.get("id")) for t in texts]
    tb = [b for b in tb if b]
    if tb and all((b[1] + b[3] / 2.0) > 0.62 for b in tb):
        issues.append(_i(bid, "PPT_ALL_TEXT_BOTTOM"))

    # 4) everything enters with the same fade
    mp = [(e.get("motion_policy") or {}).get("type") for e in els]
    mp = [t for t in mp if t in MOVING]
    if len(mp) >= 3 and set(mp) == {"fade"}:
        issues.append(_i(bid, "MOTION_ALL_FADE"))

    # 5) hard reset each beat
    if beat.get("scene_change") is not True and beat.get("shared_entities") == 0:
        issues.append(_i(bid, "CONTINUITY_RISK_RESET"))

    # 6) semantic-free decoration
    for e in els:
        if (e.get("role") in ("ambient", "decor", "decoration")
                and e.get("semantic_role") in (None, "decoration")
                and e.get("reason") is None):
            issues.append(_i(bid, "DECORATION_RISK"))
            break

    # 7) primary not obvious
    if beat.get("primary_prominence", 1.0) < 0.25:
        issues.append(_i(bid, "HIERARCHY_RISK_PRIMARY_WEAK"))
    return issues


def audit(plan, strict=False):
    issues = []
    for bp in plan.get("beats", []):
        issues += check_beat(bp)
    if strict:
        issues = [dict(i, severity="err") for i in issues]
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues,
            "codes": sorted({i["code"] for i in issues})}
