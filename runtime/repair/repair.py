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
CATEGORY_UNATTRIBUTED = "UNATTRIBUTED"

STATUS_NO_REPAIR = "NO_REPAIR_NEEDED"
STATUS_RESOLVED = "RESOLVED"
STATUS_BLOCKED = "BLOCKED"


def diagnose(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a verdict into one repair category."""
    v = verdict["verdict"]
    if v == "PASS":
        return {"category": CATEGORY_NO_FAULT, "verdict": v,
                "detail": "no defect: both spec and runtime satisfy the anchor contract"}
    if v == "SPEC_FAIL":
        return {"category": CATEGORY_SPEC_DEFECT, "verdict": v,
                "detail": "spec violates the anchor-derived expectation while the runtime satisfies it",
                "spec_diff": verdict.get("spec_diff", {})}
    if v == "RUNTIME_FAIL":
        return {"category": CATEGORY_RUNTIME_DEFECT, "verdict": v,
                "detail": "runtime violates the anchor-derived expectation while the spec matches it",
                "runtime_violations": verdict.get("runtime_violations", [])}
    if v == "AMBIGUOUS":
        return {"category": CATEGORY_UNATTRIBUTED, "verdict": v,
                "detail": "spec and runtime both deviate; blame is not attributable"}
    raise ValueError("unknown verdict: %r" % (v,))


def propose(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """Name the minimal correction for a diagnosable defect (no mutation)."""
    cat = diagnosis["category"]
    if cat == CATEGORY_SPEC_DEFECT:
        return {"target": "spec", "action": "replace_spec_with_anchor_derivation",
                "rationale": "the anchor is trusted; the spec must be entailed by it"}
    if cat == CATEGORY_RUNTIME_DEFECT:
        return {"target": "runtime", "action": "recompile_world_state_from_anchor",
                "rationale": "the expected is sound; the runtime must be brought to match"}
    if cat == CATEGORY_NO_FAULT:
        return {"target": None, "action": "none", "rationale": "nothing to repair"}
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
