"""Spec §5 — Visual Weight Hierarchy (P0..P3).

Hard rule: a P3 decoration may never out-weigh the P0 Primary. Weight is a
deterministic scalar derived from measurable cues (normalized area, contrast
role, primitive complexity, motion amplitude) so the gate is reproducible and
testable rather than a subjective score.

P0 = Primary   (strongest visual weight)
P1 = Secondary (explains P0)
P2 = Support   (aids understanding)
P3 = Decoration (space-filling / atmosphere only)
"""
from __future__ import annotations

P_LEVELS = ("P0", "P1", "P2", "P3")

ROLE_TO_P = {
    "primary": "P0",
    "secondary": "P1",
    "support": "P2",
    "ambient": "P3",
    "decor": "P3",
    "decoration": "P3",
}

# Nominal weight ceiling per level, used to flag overreach.
P_CEILING = {"P0": 1.0, "P1": 0.62, "P2": 0.40, "P3": 0.26}

_CONTRAST = {"positive": 1.0, "negative": 1.0, "accent": 1.05,
             "neutral": 0.7, "muted": 0.5}
_COMPLEXITY = {"motif": 1.15, "chart": 1.2, "text": 0.95, "connector": 0.8,
               "decor": 0.7, "shape": 0.9, "path": 0.8}

_MOVING = {"fade", "rise", "pop", "slide", "scale", "draw", "grow", "emerge",
           "reveal", "expand", "converge", "diverge", "rotate", "wipe"}


def p_level(el):
    if el.get("p_level") in P_LEVELS:
        return el["p_level"]
    return ROLE_TO_P.get(el.get("role"), "P2")


def _area(box):
    if not box:
        return 0.0
    try:
        _, _, w, h = box
    except Exception:
        return 0.0
    return max(0.0, float(w)) * max(0.0, float(h))


def _motion_amplitude(el):
    mp = el.get("motion_policy")
    if isinstance(mp, dict) and mp.get("amplitude") is not None:
        try:
            return max(0.6, float(mp["amplitude"]))
        except Exception:
            return 1.0
    t = (mp or {}).get("type") if isinstance(mp, dict) else None
    if t in {"scale", "pop", "expand", "converge", "diverge", "rotate"}:
        return 1.12
    if t in {"fade", "static", "none", "continue", "carry_over", "handoff", "transform"}:
        return 0.95
    return 1.0


def visual_weight(el, box=None, motion_amplitude=None):
    box = box if box is not None else el.get("box")
    area = _area(box)
    contrast = _CONTRAST.get(el.get("color_role"), 0.8)
    complexity = _COMPLEXITY.get(el.get("type"), 1.0)
    amp = float(motion_amplitude) if motion_amplitude is not None else _motion_amplitude(el)
    if el.get("emphasis"):
        contrast = min(1.2, contrast * 1.1)
    return round(area * contrast * complexity * amp, 6)


def audit_hierarchy(beat):
    """Return {'status','issues','weights','levels'} for one beat."""
    elements = beat.get("elements", [])
    boxes = beat.get("boxes") or {}
    weights = {}
    levels = {}
    for e in elements:
        eid = e.get("id")
        weights[eid] = visual_weight(e, boxes.get(eid))
        levels[eid] = p_level(e)

    issues = []
    primaries = [e for e in elements if p_level(e) == "P0"]
    if len(primaries) != 1:
        issues.append({"code": "PRIMARY_NOT_UNIQUE", "severity": "err",
                       "beat_id": beat.get("beat_id"),
                       "msg": "P0 primary count = %d (must be exactly 1)" % len(primaries)})
    if primaries:
        pw = weights[primaries[0].get("id")]
        for e in elements:
            eid = e.get("id")
            if p_level(e) == "P3" and weights[eid] > pw:
                issues.append({"code": "DECORATION_OVERREACH", "severity": "err",
                               "beat_id": beat.get("beat_id"),
                               "msg": "%s (P3)=%.4f exceeds primary=%.4f"
                                      % (eid, weights[eid], pw),
                               "fix": ["reduce size", "lower contrast", "reduce motion amplitude",
                                       "reduce visual complexity"]})
        # softer check: any level above its ceiling
        for e in elements:
            eid = e.get("id")
            lv = p_level(e)
            if lv != "P0" and weights.get(eid, 0) > P_CEILING.get(lv, 1.0):
                issues.append({"code": "LEVEL_WEIGHT_CEILING", "severity": "warn",
                               "beat_id": beat.get("beat_id"),
                               "msg": "%s (%s)=%.4f > ceiling %.2f"
                                      % (eid, lv, weights[eid], P_CEILING.get(lv, 1.0))})

    status = "FAIL" if any(i["severity"] == "err" for i in issues) else "PASS"
    return {"status": status, "issues": issues, "weights": weights, "levels": levels}
