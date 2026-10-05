"""Failure taxonomy & workflow status — Final Engineering Directive v5 §44-§45.

Verdict (WHY something is wrong) and Workflow (WHERE the case is in its
lifecycle) are two different semantic layers and must not be conflated (§45).

    Verdict:  PASS, SPEC_FAIL, RUNTIME_FAIL, RENDER_FAIL,
              OBSERVATION_FAIL, ENVIRONMENT_FAIL, PERCEPTUAL_DRIFT, AMBIGUOUS
    Workflow: OPEN, ESCALATED, RESOLVED, BLOCKED

BLOCKED is a *workflow* state, not a root cause (§44). Keeping them in one enum
is exactly the mistake this module prevents.
"""
from __future__ import annotations

from typing import Any, Dict

# --- Verdict (root-cause layer) --------------------------------------------
PASS = "PASS"
SPEC_FAIL = "SPEC_FAIL"
RUNTIME_FAIL = "RUNTIME_FAIL"
RENDER_FAIL = "RENDER_FAIL"
OBSERVATION_FAIL = "OBSERVATION_FAIL"
ENVIRONMENT_FAIL = "ENVIRONMENT_FAIL"
PERCEPTUAL_DRIFT = "PERCEPTUAL_DRIFT"
AMBIGUOUS = "AMBIGUOUS"

VERDICTS = (
    PASS, SPEC_FAIL, RUNTIME_FAIL, RENDER_FAIL,
    OBSERVATION_FAIL, ENVIRONMENT_FAIL, PERCEPTUAL_DRIFT, AMBIGUOUS,
)

# Verdicts that mean "the expectation itself is untrustworthy / undecidable".
UNDECIDABLE_VERDICTS = (AMBIGUOUS,)

# --- Workflow (lifecycle layer) --------------------------------------------
OPEN = "OPEN"
ESCALATED = "ESCALATED"
RESOLVED = "RESOLVED"
BLOCKED = "BLOCKED"

WORKFLOW_STATES = (OPEN, ESCALATED, RESOLVED, BLOCKED)

# --- Which fault domain owns each verdict (§41-§43) -------------------------
FAULT_DOMAIN = {
    PASS: "none",
    SPEC_FAIL: "spec",
    RUNTIME_FAIL: "runtime",
    RENDER_FAIL: "renderer",
    OBSERVATION_FAIL: "observer",
    ENVIRONMENT_FAIL: "environment",
    PERCEPTUAL_DRIFT: "pixel",
    AMBIGUOUS: "unknown",
}


def is_verdict(value: str) -> bool:
    return value in VERDICTS


def is_workflow_state(value: str) -> bool:
    return value in WORKFLOW_STATES


def fault_domain(verdict: str) -> str:
    return FAULT_DOMAIN.get(verdict, "unknown")


def workflow_for(verdict: str, *, repaired: bool = False) -> str:
    """Map a verdict onto a workflow state (§44-§46).

    AMBIGUOUS escalates (it needs an evidence request); a resolved repair is
    RESOLVED; everything else that is not PASS is OPEN/BLOCKED depending on
    whether a next experiment can make progress.
    """
    if verdict == PASS:
        return RESOLVED if repaired else RESOLVED
    if verdict == AMBIGUOUS:
        return ESCALATED
    if repaired:
        return RESOLVED
    return OPEN


def summarize(verdict: str) -> Dict[str, Any]:
    return {"verdict": verdict, "fault_domain": fault_domain(verdict),
            "is_verdict": is_verdict(verdict)}
