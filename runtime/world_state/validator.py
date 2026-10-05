"""Phase 0 Validator — the falsifiable loop.

Verdicts are mutually exclusive and total:

  PASS         : Expected matches the Anchor (via the contract) AND the
                 Runtime's world state satisfies the derived expectation.
  SPEC_FAIL    : the human/agent ``expected_semantic`` is NOT entailed by the
                 LOCKED Anchor under the audited Entailment Contract.
  RUNTIME_FAIL : the Expected is sound, but the Runtime's world state violates it.
  AMBIGUOUS    : Spec and Runtime disagree *simultaneously* -> the system
                 refuses to attribute blame and emits an evidence request.

Crucial design point (Falsifiability First v4, "Anchor Challenge"):

  The **trusted oracle** is the expectation *derived* from the LOCKED Anchor
  through the audited Entailment Contract -- NOT the human-authored
  ``expected_semantic`` file. The human Expected is itself put on trial: if it
  deviates from the derived expectation, that is precisely ``SPEC_FAIL``.

  This is what lets a *double* fault (wrong spec + wrong runtime) be told apart
  from a *single* spec fault: the runtime is always judged against the derived
  (anchor-trusted) expectation, independent of the possibly-wrong human spec.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import serializer
from .model import WorldState


def derive_expected(anchor: Dict[str, Any], contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Mechanically map an Anchor's claims to hard constraints via a contract.

    ``$subject`` / ``$object`` / ``$predicate`` bind to the claim's slots.
    This function is the *only* path from Anchor to Expectation; the contract
    is data, so it can be audited and versioned outside the runtime.
    """
    out: List[Dict[str, Any]] = []
    for claim in anchor["claims"]:
        bind = {
            "$subject": claim["subject"],
            "$object": claim["object"],
            "$predicate": claim["predicate"],
        }
        for rule in contract["entailment"]:
            c = {}
            for k, v in rule.items():
                c[k] = bind.get(v, v) if isinstance(v, str) else v
            c["derived_from"] = claim["id"]
            out.append(c)
    return out


def check_hard(facts: Dict[str, Any], constraints: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any], str]]:
    """Return a list of ``(kind, constraint, message)`` violations."""
    violations: List[Tuple[str, Dict[str, Any], str]] = []
    for c in constraints:
        kind = c["kind"]
        if kind == "relation_direction":
            key = (c["source"], c["target"], c["relation_type"])
            if key not in facts["relation_dirs"]:
                violations.append((kind, c, "missing directed relation %s" % (key,)))
        elif kind == "temporal_precedence":
            a = facts["first_focus"].get(c["before"])
            b = facts["first_focus"].get(c["after"])
            if a is None or b is None:
                violations.append((kind, c, "precedence object never focused"))
            elif not (a < b):
                violations.append((kind, c, "before=%r !< after=%r" % (a, b)))
        elif kind == "final_focus":
            if facts["last_focus"] != c["object"]:
                violations.append((kind, c, "last_focus=%r != %r" % (facts["last_focus"], c["object"])))
        else:  # pragma: no cover - guarded by serializer tests
            raise ValueError("unknown hard-constraint kind: %r" % (kind,))
    return violations


def check_staging(facts: Dict[str, Any], staging: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any], str]]:
    """Soft checks. Deviation is ``DRIFT`` (advisory), never a failure."""
    drifts: List[Tuple[str, Dict[str, Any], str]] = []
    for c in staging.get("soft_constraints", []):
        if c["kind"] == "phase_sequence":
            key = (c["source"], c["target"], c["relation_type"])
            actual = facts["phase_seq"].get(key, [])
            expected = c["sequence"]
            it = iter(actual)
            ok = all(any(x == e for x in it) for e in expected)
            if not ok:
                drifts.append((c["kind"], c, "actual=%s expected~%s" % (actual, expected)))
        else:  # pragma: no cover
            raise ValueError("unknown soft-constraint kind: %r" % (c["kind"],))
    return drifts


def _evidence_request(case_id: str, spec_diff: Dict[str, Any],
                      runtime_violations: List[Tuple[str, Any, str]]) -> Dict[str, Any]:
    """AMBIGUOUS is not a dead end: it must ask exactly four questions."""
    return {
        "case_id": case_id,
        "reason": "spec and runtime disagree simultaneously; blame is not attributable",
        "questions": [
            {"q": "Q1", "ask": "Which of the two defects was introduced first in history?",
             "why": "temporal order of the two faults decides which expectation to trust"},
            {"q": "Q2", "ask": "Is the Anchor itself still valid, or has it been challenged?",
             "why": "an invalid Anchor would make the derived oracle untrustworthy too"},
            {"q": "Q3", "ask": "Did the runtime change without a corresponding spec change?",
             "why": "a runtime-only change with a spec fault indicates an independent runtime bug"},
            {"q": "Q4", "ask": "Provide one additional observation (browser/geometry) to break the tie.",
             "why": "an independent evidence source separates spec error from runtime error"},
        ],
        "spec_diff": spec_diff,
        "runtime_violations": [
            {"kind": k, "derived_from": c.get("derived_from"), "detail": m}
            for k, c, m in runtime_violations
        ],
    }


def validate(anchor: Dict[str, Any],
             contract: Dict[str, Any],
             expected_semantic: Dict[str, Any],
             expected_staging: Dict[str, Any],
             world_state: WorldState) -> Dict[str, Any]:
    """Run the full falsifiable loop and return a verdict record."""
    derived = derive_expected(anchor, contract)
    spec_set = serializer.norm_constraint_set(expected_semantic["hard_constraints"])
    derived_set = serializer.norm_constraint_set(derived)
    spec_ok = spec_set == derived_set
    spec_diff = {
        "missing_in_expected": sorted(derived_set - spec_set),
        "extra_in_expected": sorted(spec_set - derived_set),
    }

    facts = world_state.facts()
    # The runtime is judged against the ANCHOR-TRUSTED derived expectation,
    # never against the (possibly wrong) human spec.
    runtime_violations = check_hard(facts, derived)
    runtime_ok = not runtime_violations

    staging_drifts = check_staging(facts, expected_staging)

    if spec_ok and runtime_ok:
        verdict = "PASS"
    elif (not spec_ok) and runtime_ok:
        verdict = "SPEC_FAIL"
    elif spec_ok and (not runtime_ok):
        verdict = "RUNTIME_FAIL"
    else:
        verdict = "AMBIGUOUS"

    result: Dict[str, Any] = {
        "case_id": anchor["case_id"],
        "verdict": verdict,
        "spec_ok": spec_ok,
        "runtime_ok": runtime_ok,
        "spec_diff": spec_diff,
        "runtime_violations": [
            {"kind": k, "derived_from": c.get("derived_from"), "detail": m}
            for k, c, m in runtime_violations
        ],
        "staging": "DRIFT" if staging_drifts else "OK",
        "staging_drifts": [
            {"kind": k, "derived_from": None, "detail": m} for k, c, m in staging_drifts
        ],
        "world_state_hash": serializer.world_state_hash(world_state.to_dict()),
    }
    if verdict == "AMBIGUOUS":
        result["evidence_request"] = _evidence_request(anchor["case_id"], spec_diff,
                                                       runtime_violations)
    return result
