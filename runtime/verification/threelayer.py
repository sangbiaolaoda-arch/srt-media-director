"""Three-layer verification: tests / real-SRT regression / evaluation.

    targeted tests  ->  answers "did the code break?"
    real SRT        ->  answers "did the film get worse?"
    evaluation      ->  answers "is the new version better?"

A promotion (verdict PASS) requires an explicit ledger with evidence pointers
for EACH layer; a missing layer leaves the whole thing UNRESOLVED.
"""
from . import claims

LAYERS = ("tests", "real_srt", "evaluation")


def empty_ledger():
    return {"tests": None, "real_srt": None, "evaluation": None}


def record(ledger, layer, evidence_pointer, observed):
    if layer not in LAYERS:
        raise ValueError("unknown layer %r" % layer)
    ledger[layer] = {"evidence": evidence_pointer, "observed": observed}
    return ledger


def verdict(ledger, by):
    """Return (verdict, reasons). PASS only if all three layers carry evidence."""
    missing = [l for l in LAYERS if not ledger.get(l)]
    if missing:
        return "UNRESOLVED", ["missing layer evidence: %s" % ", ".join(missing)]
    # a judge role must sign; reuse claims enforcement by constructing a verdict
    v = claims.JudgeVerdict(subject="three-layer", verdict="PASS", by=by,
                            evidence=[ledger[l]["evidence"] for l in LAYERS])
    return v.verdict, []
