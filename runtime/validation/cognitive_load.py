"""Spec §29 — Cognitive load: information must fit the viewing time.

Load is a processing-index (reading + elements + motions) divided by the beat's
duration. A ratio above OVERLOAD means the beat carries more than a viewer can
absorb in the time given → extend, split, or cut.
"""
from __future__ import annotations

CHARS_PER_SEC = 12.0       # comfortable on-screen reading rate
ELEMENTS_PER_SEC = 1.6
MOTIONS_PER_SEC = 1.2
OVERLOAD = 1.15            # index/duration ratio that counts as over-budget

MOVING = {"fade", "rise", "pop", "slide", "scale", "draw", "grow", "emerge",
          "reveal", "expand", "converge", "diverge", "rotate", "wipe"}


def _dur(beat):
    d = beat.get("duration_sec")
    if d:
        return float(d)
    return max(1e-6, float(beat.get("end_sec", 0)) - float(beat.get("start_sec", 0)))


def load_index(beat):
    dur = _dur(beat)
    els = [e for e in beat.get("elements", []) if e.get("visible", True)]
    chars = sum(len(e.get("text", "")) for e in els if e.get("type") == "text")
    motions = [e for e in els if (e.get("motion_policy") or {}).get("type") in MOVING]
    index = (chars / CHARS_PER_SEC + len(els) / ELEMENTS_PER_SEC
             + len(motions) / MOTIONS_PER_SEC)
    return round(index / dur, 4), dur, chars, len(els), len(motions)


def audit(plan):
    issues = []
    details = []
    for bp in plan.get("beats", []):
        ratio, dur, chars, nels, nmot = load_index(bp)
        details.append({"beat_id": bp.get("beat_id"), "load_ratio": ratio,
                        "duration": round(dur, 3), "chars": chars,
                        "elements": nels, "motions": nmot})
        if ratio > OVERLOAD:
            issues.append({"severity": "err", "layer": "cognitive_load",
                           "code": "COGNITIVE_OVERLOAD", "beat_id": bp.get("beat_id"),
                           "msg": "load %.2f > %.2f (reduce elements / extend beat / split)"
                                  % (ratio, OVERLOAD)})
    return {"status": "FAIL" if issues else "PASS", "issues": issues, "beats": details}
