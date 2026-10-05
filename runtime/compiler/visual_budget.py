"""Spec §18/§19 — Visual budget: complexity must fit the viewing time.

A 1.2s beat must never carry a 5s beat's information. The budget turns
(duration, speech_density, semantic_density) into hard ceilings on visible
element count, motion count and total on-screen text.
"""
from __future__ import annotations

# (upper duration bound sec, tier name) — the first bound the duration beats.
TIERS = ((1.5, "low"), (3.0, "medium"), (6.0, "rich"), (float("inf"), "evolving"))

MAX_ELEMENTS = {"low": 3, "medium": 5, "rich": 8, "evolving": 12}
MAX_MOTIONS = {"low": 1, "medium": 2, "rich": 3, "evolving": 4}
TEXT_CHARS = {"low": 14, "medium": 28, "rich": 46, "evolving": 70}

ORDER = ["low", "medium", "rich", "evolving"]

_MOVING = {"fade", "rise", "pop", "slide", "scale", "draw", "grow", "emerge",
           "reveal", "expand", "converge", "diverge", "rotate", "wipe"}


def tier_for(duration, speech_density=0.5, semantic_density=0.5):
    d = float(duration)
    base = next(name for lim, name in TIERS if d < lim)
    load = 0.5 * float(speech_density) + 0.5 * float(semantic_density)
    idx = ORDER.index(base)
    if load >= 0.66 and idx < len(ORDER) - 1:
        idx += 1  # dense content earns one tier up; never earns a tier down
    return ORDER[idx]


def budget_for(duration, speech_density=0.5, semantic_density=0.5):
    t = tier_for(duration, speech_density, semantic_density)
    return {"tier": t, "max_elements": MAX_ELEMENTS[t],
            "max_motions": MAX_MOTIONS[t], "max_text_chars": TEXT_CHARS[t]}


def _dur(beat):
    d = beat.get("duration_sec")
    if d:
        return float(d)
    return float(beat.get("end_sec", 0)) - float(beat.get("start_sec", 0))


def audit_budget(beat, strict=False):
    b = budget_for(_dur(beat), beat.get("speech_density", 0.5),
                   beat.get("semantic_density", 0.5))
    visible = [e for e in beat.get("elements", []) if e.get("visible", True)]
    motions = [e for e in visible
               if ((e.get("motion_policy") or {}).get("type")) in _MOVING]
    chars = sum(len(e.get("text", "")) for e in visible if e.get("type") == "text")
    sev = "err" if strict else "warn"
    issues = []
    if len(visible) > b["max_elements"]:
        issues.append({"code": "BUDGET_ELEMENTS", "severity": sev,
                       "beat_id": beat.get("beat_id"),
                       "msg": "%d visible > %d (%s)" % (len(visible), b["max_elements"], b["tier"])})
    if len(motions) > b["max_motions"]:
        issues.append({"code": "BUDGET_MOTIONS", "severity": sev,
                       "beat_id": beat.get("beat_id"),
                       "msg": "%d motions > %d (%s)" % (len(motions), b["max_motions"], b["tier"])})
    if chars > b["max_text_chars"]:
        issues.append({"code": "BUDGET_TEXT", "severity": sev,
                       "beat_id": beat.get("beat_id"),
                       "msg": "%d text chars > %d (%s)" % (chars, b["max_text_chars"], b["tier"])})
    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "budget": b, "issues": issues,
            "observed": {"elements": len(visible), "motions": len(motions), "chars": chars}}
