"""Canonical motion validation — one producer-side validator.

Consolidates the three forked validators:
* ``motion/validator.py``            coverage + Anti-PPT (the architecture-critical layer)
* ``scene/validator.py``             machine validator (safe area / parents / charts)
* ``motion_runtime/invariants.py``   7 motion invariants (identity/parent/...)

IMPORTANT — observer independence
---------------------------------
``runtime/observer/*`` implements its OWN independent checks and projection
contracts. It must remain a separate validator (a validator that reuses the
producer's internals proves nothing). This module deliberately does NOT import
or absorb the observer.
"""
from __future__ import annotations

from collections import Counter

from . import vocabulary as _vocab

# Canonical static-like motions (explicit "we decided not to move").
STATIC_LIKE = ("static", "continue", "carry_over", "handoff", "none")

MOVING_CATEGORIES = ("enter", "exit", "emphasis", "relational", "state")


def _visible(els):
    return [e for e in els if e.get("visible", True)]


def is_valid_motion(name) -> bool:
    return _vocab.is_canonical(_vocab.canonical(name))


def _resolved_type(mp):
    if not mp or not mp.get("type"):
        return None
    return _vocab.canonical(mp["type"])


def coverage(plan):
    total = missing = static_explicit = moving = 0
    for bp in plan.get("beats", []):
        for e in _visible(bp.get("elements", [])):
            total += 1
            mp = e.get("motion_policy")
            t = _resolved_type(mp)
            if not t or not _vocab.is_canonical(t):
                missing += 1
            elif t in STATIC_LIKE or t == "none":
                static_explicit += 1
            else:
                moving += 1
    cov = 1.0 if total == 0 else (total - missing) / total
    return {"motion_coverage": round(cov, 4), "motion_missing": missing,
            "static_explicit": static_explicit, "moving": moving, "visible": total}


class AntiPPTChecker:
    """Not "any animation passes" — checks motion serves semantics and isn't overused."""

    def __init__(self, repeat_ratio=0.7, max_concurrent=2, density_cap=4):
        self.repeat_ratio = repeat_ratio
        self.max_concurrent = max_concurrent
        self.density_cap = density_cap

    def check_beat(self, bp):
        issues = []
        els = _visible(bp.get("elements", []))
        moving = [e for e in els
                  if _resolved_type(e.get("motion_policy")) not in (None,) + STATIC_LIKE]
        types = [_resolved_type(e["motion_policy"]) for e in moving]

        if len(types) >= 4:
            top, cnt = Counter(types).most_common(1)[0]
            if cnt / len(types) >= self.repeat_ratio:
                issues.append(self._i(bp, "REPETITIVE_MOTION",
                                      "%d/%d 个运动元素都是 %s" % (cnt, len(types), top)))

        windows = {}
        for e in moving:
            p = e["motion_policy"]
            w = round(p.get("delay", 0) / 0.2)
            windows.setdefault(w, []).append(e["id"])
        for w, ids in windows.items():
            if len(ids) > self.max_concurrent:
                issues.append(self._i(bp, "TOO_MANY_SIMULTANEOUS_MOTIONS",
                                      "%.1fs 附近 %d 个元素同时入场: %s" % (
                                          w * 0.2, len(ids), ids)))

        cap = bp.get("motion_budget", {}).get("max_secondary_motion", 3) + \
            bp.get("motion_budget", {}).get("max_primary_motion", 1)
        if len(moving) > cap:
            issues.append(self._i(bp, "EXCESSIVE_MOTION",
                                  "运动元素 %d > 预算 %d" % (len(moving), cap)))

        for e in els:
            if e.get("semantic_role") in ("background", "decoration"):
                if _resolved_type(e.get("motion_policy")) not in (None,) + STATIC_LIKE:
                    issues.append(self._i(bp, "DECORATIVE_MOTION",
                                          "背景/装饰元素 %s 发生了运动" % e["id"]))

        focals = [e for e in els if e.get("semantic_role") == "focal"]
        if len(focals) > 1:
            issues.append(self._i(bp, "FOCAL_MOTION_CONFLICT",
                                  "焦点元素 %d 个（应唯一）" % len(focals)))

        dur = bp.get("duration") or 1.0
        if len(moving) / max(dur, 0.1) > self.density_cap:
            issues.append(self._i(bp, "MOTION_DENSITY_TOO_HIGH",
                                  "运动密度 %.2f/s 过高" % (len(moving) / max(dur, 0.1))))

        for e in moving:
            if not (e.get("motion_policy", {}).get("reason") or "").strip():
                issues.append(self._i(bp, "MOTION_WITHOUT_SEMANTIC_PURPOSE",
                                      "%s 的运动缺少语义解释" % e["id"]))
        return issues

    @staticmethod
    def _i(bp, code, msg):
        return {"severity": "warn", "layer": "motion", "code": code,
                "beat_id": bp.get("beat_id"), "msg": msg}


def validate_motion(plan, autocomp=True, budget=None, checker=None, planner=None):
    """Main entry — returns {status, coverage..., errors, warnings, issues}."""
    checker = checker or AntiPPTChecker()
    issues = []
    autocompleted = []

    cov = coverage(plan)
    if cov["motion_missing"] > 0:
        if not autocomp or planner is None:
            issues.append({"severity": "err", "layer": "motion",
                           "code": "MOTION_POLICY_MISSING",
                           "msg": "%d 个可见元素缺少 Motion Policy" % cov["motion_missing"]})
        else:
            filled = planner.fill_missing(plan)
            autocompleted = [{"beat_id": b, "element": e} for b, e in filled]
            cov = coverage(plan)
            if cov["motion_missing"] > 0:
                issues.append({"severity": "err", "layer": "motion",
                               "code": "MOTION_POLICY_MISSING",
                               "msg": "自动补全后仍有 %d 个缺失" % cov["motion_missing"]})

    for bp in plan.get("beats", []):
        for e in _visible(bp.get("elements", [])):
            mp = e.get("motion_policy") or {}
            t = _resolved_type(mp)
            if mp.get("type") and (not t or not _vocab.is_canonical(t)):
                issues.append({"severity": "err", "layer": "motion",
                               "code": "MOTION_TYPE_UNKNOWN",
                               "beat_id": bp.get("beat_id"),
                               "msg": "%s 的类型 %r 不在 Registry" % (e["id"], mp["type"])})

    for bp in plan.get("beats", []):
        issues += checker.check_beat(bp)

    errs = [i for i in issues if i["severity"] == "err"]
    warns = [i for i in issues if i["severity"] == "warn"]
    status = "FAIL" if errs else "PASS"
    result = {"status": status, "motion_coverage": cov["motion_coverage"],
              "motion_missing": cov["motion_missing"],
              "static_explicit": cov["static_explicit"],
              "moving": cov["moving"], "visible": cov["visible"],
              "errors": errs, "warnings": warns, "issues": issues,
              "autocompleted": autocompleted}
    plan["validation"] = result
    return result


# ------------------------------------------------------------ invariants (names)
def invariant_names():
    """The canonical motion invariants (structure preserved from invariants.py)."""
    return ("Identity", "Parent", "Connector", "State", "Relation",
            "Motion", "Cleanup")


def invariant_state_trigger(transitions) -> dict:
    bad = [t for t in transitions if not getattr(t, "trigger", None)]
    return {"name": "State", "status": "PASS" if not bad else "FAIL",
            "detail": "%d transition(s) without trigger" % len(bad)}


def audit() -> dict:
    """Self-check the canonical validator's vocabulary wiring."""
    issues = []
    for name in STATIC_LIKE:
        if name != "none" and not _vocab.is_canonical(name):
            issues.append("static-like '%s' not in vocabulary" % name)
    return {"status": "FAIL" if issues else "PASS", "issues": issues}
