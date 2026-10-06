"""The single acceptance chain — one data model shared by verify_change.py.

Each layer answers exactly one question, and the SAME tuple is used both by the
runner (which records every check it really executed) and by the verdict (which
refuses PASS while any layer is missing).  This removes the old mismatch where
the runner did 7 checks but the ledger only modelled 3.

    targeted       -> did the edit immediately break its own module?
    full_pytest    -> did it break the rest of the system?
    real_srt       -> does real input still generate deterministically?
    render         -> did an actual render happen (not just JSON)?
    adversarial    -> did the agent take a cheap lazy path?
    judge_guard    -> was the judge system itself modified?
    evaluation     -> is the new version BETTER? (human/agent; never auto-passed)

A promotion (PASS) requires an explicit ledger entry with a real evidence pointer
for EVERY layer.  The final verdict is issued through ``acceptance`` (signed), so
without the signing authority even a fully-evidenced chain stays UNRESOLVED.
"""
from . import acceptance
import os

LAYERS = ("targeted", "full_pytest", "real_srt", "render", "adversarial",
          "judge_guard", "evaluation")

# Human-readable question per layer (single source of truth for the docs + tests).
QUESTIONS = {
    "targeted": "did the edit break its own module?",
    "full_pytest": "did it break the rest of the system?",
    "real_srt": "does real input still generate deterministically?",
    "render": "did an actual render happen?",
    "adversarial": "did the agent take a cheap lazy path?",
    "judge_guard": "was the judge system modified?",
    "evaluation": "is the new version better? (human/agent)",
}


def empty_ledger():
    return {layer: None for layer in LAYERS}


def record(ledger, layer, evidence_pointer, observed):
    if layer not in LAYERS:
        raise ValueError("unknown layer %r (valid: %s)" % (layer, LAYERS))
    ledger[layer] = {"evidence": evidence_pointer, "observed": observed}
    return ledger


def _evidence_ok(entry):
    """A layer counts only if its evidence pointer is a REAL file on disk.

    Recording a path that does not exist (line deleted, artifact never written)
    does not count — so a skipped/faked layer stays missing rather than silently
    satisfied.
    """
    if not entry:
        return False
    ev = entry.get("evidence")
    if isinstance(ev, dict):
        ev = ev.get("path")
    return bool(ev) and os.path.exists(ev)


def missing_layers(ledger):
    return [layer for layer in LAYERS if not _evidence_ok(ledger.get(layer))]


def verdict(ledger, by="validator"):
    """Return (verdict, reasons) via the signed acceptance path.

    All layers present does NOT by itself yield PASS: the candidate is run through
    ``acceptance.issue`` which downgrades to UNRESOLVED unless a signing authority
    is present.
    """
    missing = missing_layers(ledger)
    if missing:
        return "UNRESOLVED", ["missing layer evidence: %s" % ", ".join(missing)]
    evidence = [{"path": ledger[l]["evidence"], "observed": ledger[l]["observed"]}
                for l in LAYERS]
    doc = acceptance.issue("motion-director/change", "PASS", by, evidence)
    v, reasons = acceptance.evaluate(doc)
    if v != "PASS":
        return v, reasons or ["verdict not signed by an independent authority"]
    return v, []
