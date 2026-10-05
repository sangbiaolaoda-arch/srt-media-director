"""Repair (Phase 0, step 10) — the loop closes by *re-verification*, not trust.

Design (Falsifiability First v4 §53 step 10):

    Diagnosis  ->  Evidence Request  ->  RESOLVED / BLOCKED

The one rule that makes this step honest:

    **A proposed repair is never trusted on its own.** Whatever correction the
    repair logic proposes must be applied and then pushed back through the SAME
    validator. Only a re-validation that returns ``PASS`` yields ``RESOLVED``.
    If the re-validation still fails, the result is ``BLOCKED`` — the repair
    is just another falsifiable claim, and it did not survive.

Other invariants:

  * Repair does not silently mutate inputs; :func:`propose` only *names* the
    minimal correction and the side it blames.
  * ``AMBIGUOUS`` is not repairable by guessing: blame is unattributable, so
    repair returns ``BLOCKED`` and carries the validator's evidence request
    (the four questions) forward.
  * Diagnosis is by construction: a ``SPEC_FAIL`` (spec wrong, runtime right)
    can only be fixed on the spec side; a ``RUNTIME_FAIL`` (spec right, runtime
    wrong) can only be fixed on the runtime side. This keeps the two repair
    families from being confused.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from world_state import compiler, serializer, validator
from world_state.model import WorldState


CATEGORY_NO_FAULT = "NO_FAULT"
CATEGORY_SPEC_DEFECT = "SPEC_DEFECT"
CATEGORY_RUNTIME_DEFECT = "RUNTIME_DEFECT"
CATEGORY_RENDER_DEFECT = "RENDER_DEFECT"
CATEGORY_OBSERVATION_DEFECT = "OBSERVATION_DEFECT"
CATEGORY_ENVIRONMENT_DEFECT = "ENVIRONMENT_DEFECT"
CATEGORY_PERCEPTUAL = "PERCEPTUAL"
CATEGORY_UNATTRIBUTED = "UNATTRIBUTED"

STATUS_NO_REPAIR = "NO_REPAIR_NEEDED"
STATUS_RESOLVED = "RESOLVED"
STATUS_BLOCKED = "BLOCKED"
STATUS_ESCALATED = "ESCALATED"
STATUS_UNREPAIRABLE = "UNREPAIRABLE"

# Directive v5 §46: repair is driven strictly by the *verdict*. Map each verdict
# to the one repair family allowed to touch it (§41-§43 own their own domains).
VERDICT_TO_CATEGORY = {
    "PASS": CATEGORY_NO_FAULT,
    "SPEC_FAIL": CATEGORY_SPEC_DEFECT,
    "RUNTIME_FAIL": CATEGORY_RUNTIME_DEFECT,
    "RENDER_FAIL": CATEGORY_RENDER_DEFECT,
    "OBSERVATION_FAIL": CATEGORY_OBSERVATION_DEFECT,
    "ENVIRONMENT_FAIL": CATEGORY_ENVIRONMENT_DEFECT,
    "PERCEPTUAL_DRIFT": CATEGORY_PERCEPTUAL,
    "AMBIGUOUS": CATEGORY_UNATTRIBUTED,
}

# The layer that must be corrected for each defect category (§46).
CATEGORY_TARGET = {
    CATEGORY_SPEC_DEFECT: "spec",
    CATEGORY_RUNTIME_DEFECT: "runtime",
    CATEGORY_RENDER_DEFECT: "renderer",
    CATEGORY_OBSERVATION_DEFECT: "observer",
    CATEGORY_PERCEPTUAL: "pixel",
}


_CATEGORY_DETAIL = {
    CATEGORY_NO_FAULT: "no defect: both spec and runtime satisfy the anchor contract",
    CATEGORY_SPEC_DEFECT: "spec violates the anchor-derived expectation while the runtime satisfies it",
    CATEGORY_RUNTIME_DEFECT: "runtime violates the anchor-derived expectation while the spec matches it",
    CATEGORY_RENDER_DEFECT: "the renderer's output violates the independent render projection",
    CATEGORY_OBSERVATION_DEFECT: "the observer dropped nodes the renderer actually emitted",
    CATEGORY_ENVIRONMENT_DEFECT: "the environment could not produce a valid observation",
    CATEGORY_PERCEPTUAL: "the rendered picture drifted, though the structure holds",
    CATEGORY_UNATTRIBUTED: "spec and runtime both deviate; blame is not attributable",
}


def diagnose(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a verdict into one repair category (Directive v5 §46).

    The verdict — never a guess about "where it probably is" — decides which
    repair family is allowed to act.
    """
    v = verdict["verdict"]
    cat = VERDICT_TO_CATEGORY.get(v)
    if cat is None:
        raise ValueError("unknown verdict: %r" % (v,))
    out: Dict[str, Any] = {"category": cat, "verdict": v, "detail": _CATEGORY_DETAIL[cat]}
    if cat == CATEGORY_SPEC_DEFECT:
        out["spec_diff"] = verdict.get("spec_diff", {})
    elif cat == CATEGORY_RUNTIME_DEFECT:
        out["runtime_violations"] = verdict.get("runtime_violations", [])
    elif cat in (CATEGORY_RENDER_DEFECT, CATEGORY_OBSERVATION_DEFECT,
                 CATEGORY_PERCEPTUAL):
        out["problems"] = verdict.get("problems", [])
    return out


# Directive v5 §46: which domains Repair is even allowed to touch automatically.
# A broken observation/ENVIRONMENT is not a code defect to patch — it is a
# precondition to restore; and AMBIGUOUS needs evidence, not a guess.
AUTO_REPAIRABLE = (CATEGORY_SPEC_DEFECT, CATEGORY_RUNTIME_DEFECT, CATEGORY_RENDER_DEFECT)


def workflow_state(outcome: str) -> str:
    """Map a repair outcome onto the workflow layer (§44-§45)."""
    return {
        STATUS_NO_REPAIR: "RESOLVED",
        STATUS_RESOLVED: "RESOLVED",
        STATUS_BLOCKED: "BLOCKED",
        STATUS_ESCALATED: "ESCALATED",
        STATUS_UNREPAIRABLE: "BLOCKED",
    }.get(outcome, "OPEN")


def propose(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Name the minimal correction for a diagnosable defect (no mutation)."""
    cat = diagnosis["category"]
    if cat == CATEGORY_SPEC_DEFECT:
        return {"target": "spec", "action": "replace_spec_with_anchor_derivation",
                "rationale": "the anchor is trusted; the spec must be entailed by it"}
    if cat == CATEGORY_RUNTIME_DEFECT:
        return {"target": "runtime", "action": "recompile_world_state_from_anchor",
                "rationale": "the expected is sound; the runtime must be brought to match"}
    if cat == CATEGORY_RENDER_DEFECT:
        return {"target": "renderer", "action": "repair_renderer_to_projection",
                "rationale": "the world-state is sound; the renderer must honour the projection"}
    if cat == CATEGORY_OBSERVATION_DEFECT:
        return {"target": "observer", "action": "repair_observer_to_emit_all_nodes",
                "rationale": "the renderer emitted the nodes; the observer must not drop them"}
    if cat == CATEGORY_NO_FAULT:
        return {"target": None, "action": "none", "rationale": "nothing to repair"}
    if cat == CATEGORY_PERCEPTUAL:
        return {"target": None, "action": "flag_perceptual_drift",
                "rationale": "pixel is advisory; flag for a human, do not auto-patch semantics"}
    if cat == CATEGORY_ENVIRONMENT_DEFECT:
        return {"target": None, "action": "restore_environment",
                "rationale": "the observation environment is invalid; restore it, do not patch code"}
    return {"target": None, "action": "request_evidence",
            "rationale": "unattributed: gather evidence before attempting any change"}


def _derived_spec(anchor: Dict[str, Any], contract: Dict[str, Any],
                  base: Dict[str, Any]) -> Dict[str, Any]:
    """The anchor-trusted spec: hard constraints derived from the contract."""
    return {
        "case_id": base.get("case_id", anchor.get("case_id")),
        "layer": base.get("layer", "SEMANTIC"),
        "rigidity": "HARD",
        "note": "repaired: replaced with the expectation derived from the locked anchor",
        "hard_constraints": validator.derive_expected(anchor, contract),
    }


def apply_correction(proposal: Dict[str, Any],
                     anchor: Dict[str, Any],
                     contract: Dict[str, Any],
                     expected_semantic: Dict[str, Any],
                     expected_staging: Dict[str, Any],
                     world_state: WorldState) -> Dict[str, Any]:
    """Return corrected inputs for re-validation. Does NOT mutate the originals."""
    target = proposal["target"]
    corrected = {
        "anchor": anchor, "contract": contract,
        "expected_semantic": expected_semantic,
        "expected_staging": expected_staging,
        "world_state": world_state,
    }
    if target == "spec":
        corrected["expected_semantic"] = _derived_spec(anchor, contract, expected_semantic)
    elif target == "runtime":
        corrected["world_state"] = compiler.compile_world_state(anchor, contract=contract)
    return corrected


def repair(anchor: Dict[str, Any],
           contract: Dict[str, Any],
           expected_semantic: Dict[str, Any],
           expected_staging: Dict[str, Any],
           world_state: WorldState,
           *,
           verdict: Optional[Dict[str, Any]] = None,
           propose_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
           apply_fn: Optional[Callable[..., Dict[str, Any]]] = None,
           validate_fn: Optional[Callable[..., Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Diagnose, propose, apply, then RE-VALIDATE to close the loop.

    Overrides (``propose_fn`` / ``apply_fn`` / ``validate_fn``) exist only so
    tests can prove the re-verification gate really blocks an ineffective fix.
    """
    validate_fn = validate_fn or validator.validate
    propose_fn = propose_fn or propose
    apply_fn = apply_fn or apply_correction

    if verdict is None:
        verdict = validate_fn(anchor, contract, expected_semantic,
                              expected_staging, world_state)

    diag = diagnose(verdict)
    out: Dict[str, Any] = {"diagnosis": diag, "original_verdict": verdict["verdict"]}

    if diag["category"] == CATEGORY_NO_FAULT:
        out.update({"status": STATUS_NO_REPAIR, "proposal": propose_fn(diag)})
        return out

    if diag["category"] == CATEGORY_UNATTRIBUTED:
        # refuse to guess: carry the evidence request forward.
        out.update({
            "status": STATUS_BLOCKED,
            "proposal": propose_fn(diag),
            "reason": "unattributed defect: repair refuses to guess; evidence required",
            "evidence_request": verdict.get("evidence_request"),
        })
        return out

    if diag["category"] not in AUTO_REPAIRABLE:
        # Directive v5 §46: never auto-patch a non-code fault. A broken
        # observation/environment is a precondition to restore, and pixel drift
        # is advisory — none of these may be "fixed" by editing code.
        non_auto = {
            CATEGORY_OBSERVATION_DEFECT: STATUS_BLOCKED,
            CATEGORY_ENVIRONMENT_DEFECT: STATUS_UNREPAIRABLE,
            CATEGORY_PERCEPTUAL: STATUS_BLOCKED,
        }
        out.update({
            "status": non_auto[diag["category"]],
            "workflow": workflow_state(non_auto[diag["category"]]),
            "proposal": propose_fn(diag),
            "reason": "not auto-repairable: correct the %s, not the code" % (
                CATEGORY_TARGET.get(diag["category"], "environment")),
        })
        return out

    proposal = propose_fn(diag)
    corrected = apply_fn(proposal, anchor, contract, expected_semantic,
                         expected_staging, world_state)
    re = validate_fn(corrected["anchor"], corrected["contract"],
                     corrected["expected_semantic"], corrected["expected_staging"],
                     corrected["world_state"])
    out["proposal"] = proposal
    out["revalidation"] = {"verdict": re["verdict"],
                           "spec_ok": re.get("spec_ok"),
                           "runtime_ok": re.get("runtime_ok")}
    if re["verdict"] == "PASS":
        out.update({"status": STATUS_RESOLVED,
                    "corrected_world_state_hash": serializer.world_state_hash(
                        corrected["world_state"].to_dict())})
    else:
        out.update({"status": STATUS_BLOCKED,
                    "reason": "proposed repair did not survive re-validation",
                    "evidence_request": re.get("evidence_request")})
    return out


# --- Phase 3: Improvement Gate + Rollback (Directive v5 §62) ------------------
#
# A repair is only *kept* if it strictly improves the score. Otherwise we roll
# back to the last known-good state. This is what makes repair an experiment
# rather than an edit: "裁判已经可靠以后，再让 Agent 学会接受裁判".

def improvement_gate(before: float, after: float, *, min_gain: float = 0.0,
                     ) -> Dict[str, Any]:
    """Decide whether a change should be kept or rolled back.

    Keep only on a strict improvement beyond ``min_gain``. Equal-or-worse is
    rolled back — never "kept because it didn't break anything".
    """
    gain = after - before
    keep = gain > min_gain
    return {
        "before": before,
        "after": after,
        "gain": round(gain, 6),
        "min_gain": min_gain,
        "decision": "KEEP" if keep else "ROLLBACK",
    }


def repair_with_gate(before_score: float, after_score: float, *,
                     rollback_to: Any, candidate: Any,
                     min_gain: float = 0.0) -> Dict[str, Any]:
    """Apply the improvement gate to a candidate state and pick the survivor.

    Returns the decision plus the surviving state, so the caller never keeps a
    non-improving change "because it compiled".
    """
    gate = improvement_gate(before_score, after_score, min_gain=min_gain)
    survived = candidate if gate["decision"] == "KEEP" else rollback_to
    return {**gate, "survived": survived,
            "workflow": "RESOLVED" if gate["decision"] == "KEEP" else "BLOCKED"}
