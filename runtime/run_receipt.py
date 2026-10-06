"""Production run receipt — every pipeline.run leaves WHAT / EVIDENCE / VERDICT / NEXT.

This module is *glue, not a judge*.  It collects the facts a run already produced
and hands them to the independent judge role (``validator``).  It deliberately
never issues PASS/FAIL — the strongest thing it can emit is UNRESOLVED plus the
missing stage.  An agent editing this file can therefore only make the run *more*
honest, never fake a completion.

WHY this exists (anti-laziness principle, runtime/verification): an agent may not
disguise "not done" as "done".  The cheapest disguise is to stop right after
generation and declare victory.  The receipt makes that impossible by construction:
EVALUATED (human/agent review) has no automatic evidence, so a run that has not
been reviewed ends UNRESOLVED.

P1 evidence binding: the verdict is issued through ``acceptance`` and carries each
artifact's path + sha256.  Deleting or changing an artifact after the fact breaks
the evidence digest, so the verdict no longer verifies (see acceptance.evaluate).

The enter-motion "machine teeth" live in validator L1 (LIFECYCLE_ENTER /
LIFECYCLE_MISSING); the receipt only *records* the independently computed gap list
for cross-checking — it does not re-implement that gate.
"""
import json
import os

from verification import acceptance, adversarial, claims, defaults, stages

STAGE_WHAT = {
    "PLANNED": "compile SRT -> deterministic artifacts",
    "GENERATED": "intermediate artifacts written under work/",
    "VERIFIED": "validator schema + L1 + L3 (machine gates)",
    "RENDERED": "raster preview probe actually executed",
}


def _load(work_dir, name):
    with open(os.path.join(work_dir, name), encoding="utf-8") as fh:
        return json.load(fh)


def _evidence_files(work_dir):
    return {
        "PLANNED": {"task_contract": "pipeline.run(srt_path, out_dir)"},
        "GENERATED": {"artifact_path": os.path.join(work_dir, "visual-dsl.json")},
        "VERIFIED": {"validator_report": os.path.join(work_dir, "validation-report.json")},
        "RENDERED": {"render_report": os.path.join(work_dir, "validation-report.json")},
    }


def build(work_dir, film_index, report, changed_paths=None):
    """Assemble the machine receipt for one run. Returns a plain dict (audit trail)."""
    dsl = _load(work_dir, "visual-dsl.json")
    entrance = _load(work_dir, "entrance-plan.json")

    sm = stages.StageMachine()
    evidence = _evidence_files(work_dir)
    l3 = str(report.get("layers", {}).get("l3", ""))

    for stage in ("PLANNED", "GENERATED", "VERIFIED", "RENDERED"):
        ev = evidence[stage]
        # RENDERED is only earned if the raster probe actually ran (not SKIPPED).
        if stage == "RENDERED" and l3.startswith("SKIPPED"):
            break
        # A stage whose required evidence file is absent is NOT advanced.
        if any(isinstance(v, str) and v.endswith(".json") and not os.path.exists(v)
               for v in ev.values()):
            break
        sm.submit(stage, STAGE_WHAT[stage], ev)

    findings = adversarial.scan(dsl=dsl, entrance=entrance, changed_paths=changed_paths)
    gaps = defaults.audit_entrance_completeness(dsl, entrance)

    # Evidence is bound to REAL files (path); acceptance re-hashes them, so a
    # deleted/changed artifact invalidates the verdict.
    ev_items = []
    for name in ("visual-dsl.json", "render-plan.json", "entrance-plan.json",
                 "validation-report.json"):
        p = os.path.join(work_dir, name)
        if os.path.exists(p):
            ev_items.append({"path": p, "observed": "pipeline artifact"})
    if film_index and os.path.exists(film_index):
        ev_items.append({"path": film_index, "observed": "film index"})

    nxt = sm.expected_next() or "DONE"
    # Only the independent judge role may issue a verdict; this path only ever says
    # UNRESOLVED (a run is not a signed acceptance). PASS/FAIL must come from a
    # signed verification run (tools/verify_change.py with the judge authority).
    verdict = acceptance.issue("pipeline.run", "UNRESOLVED", by="validator", evidence=ev_items)

    receipt = {
        "stages": [r.to_dict() for r in sm.receipts],
        "current_stage": sm.current,
        "next_stage": nxt,
        "verdict": verdict,
        "blocking_reason": (
            "EVALUATED requires human/agent review evidence; "
            "no automatic evidence exists by design (policy VAL-01)"
        ) if nxt == "EVALUATED" else None,
        "evidence_pointers": [e["path"] for e in ev_items],
        "adversarial_findings": findings,
        "entrance_completeness_gaps": gaps,
        "defaults_ledger": [],
    }

    # The receipt is an *artifact*, never a self-certification: AgentOutput raises
    # if any status field ever dares to read PASS / verified / approved.
    claims.AgentOutput(kind="artifact", summary="pipeline run receipt", data=receipt)
    return receipt
