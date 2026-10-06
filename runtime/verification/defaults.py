"""No silent fallback — missing information is UNRESOLVED, never assumed.

A missing field must produce an explicit ``Unresolved`` failure (routed to
REPAIR), NOT a silent default.  Only *registered* defaults may be applied
automatically, and every application must leave a ``DEFAULT_APPLIED`` + reason
ledger entry.
"""


class Unresolved(Exception):
    """A required value is missing and no registered default covers it."""


# Only explicitly registered defaults may fill a gap. key = (field, reason_code).
REGISTERED_DEFAULTS = {
    ("visual_director.strategy", "role_missing"):
        ("single_focus", "visual_grammar.SEMANTIC_DEFAULT has no role-specific default"),
    ("entrance.min_gap", "unspecified"):
        ("G_MIN_WAVE_GAP", "production fixed inter-wave gap (common.G_MIN_WAVE_GAP)"),
}


def resolve(field, value, *, reason=None, ledger=None):
    """Return ``value`` if present; else a registered default (logged) or raise.

    - value is not None            -> returned as-is (no ledger entry)
    - (field, reason) registered   -> default returned + DEFAULT_APPLIED entry
    - otherwise                    -> raise Unresolved (routes to FAIL/Repair)
    """
    if value is not None:
        return value
    key = (field, reason)
    if key in REGISTERED_DEFAULTS:
        default, why = REGISTERED_DEFAULTS[key]
        if ledger is not None:
            ledger.append({"field": field, "event": "DEFAULT_APPLIED",
                           "value": default, "reason": why})
        return default
    raise Unresolved("%s is missing and has no registered default" % field)


def audit_entrance_completeness(dsl, entrance):
    """Every DSL element must carry an explicit enter motion in the entrance plan.

    A missing entry is reported as an issue (NOT silently faded by the runtime).
    """
    issues = []
    plan = {b["beat_id"]: b for b in entrance.get("beats", [])}
    for beat in dsl.get("beats", []):
        bid = beat.get("beat_id")
        life = plan.get(bid, {}).get("lifecycle", {})
        for el in beat.get("elements", []):
            eid = el.get("id")
            enter = (life.get(eid) or {}).get("enter")
            if not enter or not enter.get("motion"):
                issues.append({"beat": bid, "element": eid,
                               "issue": "missing_enter_motion"})
    return issues
