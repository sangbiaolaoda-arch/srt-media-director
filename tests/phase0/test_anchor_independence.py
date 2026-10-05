"""Anchor provenance & lifecycle tests — Directive v5 §8-§13.

The point: a *declaration* of dual annotation is not evidence. These tests prove
the two annotations are independently reproducible and mutually invisible, that
agreement is COMPUTED (not asserted), that disagreement routes to AMBIGUOUS, and
that a locked anchor can be challenged/superseded without in-place mutation.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import anchor as anchor_mod  # noqa: E402

CASES = os.path.join(ROOT, "cases")
CASE = "cause_effect"


def _load(*parts):
    with open(os.path.join(CASES, *parts), encoding="utf-8") as f:
        return json.load(f)


def _source(case=CASE):
    return _load(case, "source.json")


# --- §9 independence --------------------------------------------------------

def test_annotators_reproduce_the_committed_artifacts():
    """The committed A/B files must be exactly what the annotators produce."""
    src = _source()
    a = anchor_mod.annotate_a(src)
    b = anchor_mod.annotate_b(src)
    assert a == _load(CASE, "anchor", "annotation_a.json")
    assert b == _load(CASE, "anchor", "annotation_b.json")


def test_annotators_do_not_see_each_other():
    """Neither annotator receives the other's output; both read only source."""
    src = _source()
    a = anchor_mod.annotate_a(src)
    b = anchor_mod.annotate_b(src)
    assert a["sees_only"] == "source.json"
    assert b["sees_only"] == "source.json"


def test_annotators_are_independent_implementations():
    """A and B must differ in method (different code + lookup), so agreement counts."""
    src = _source()
    a = anchor_mod.annotate_a(src)
    b = anchor_mod.annotate_b(src)
    assert a["method"] != b["method"]


# --- §9 computed agreement, not declared ------------------------------------

def test_agreement_is_computed_from_claims():
    src = _source()
    a = anchor_mod.annotate_a(src)
    b = anchor_mod.annotate_b(src)
    adj = anchor_mod.adjudicate(a, b)
    assert adj["agree"] is True
    assert adj["outcome"] == "LOCKED"
    assert anchor_mod.agrees(a, b)


def test_disagreement_routes_to_ambiguous_not_locked():
    """If A != B the outcome is AMBIGUOUS and locking must be refused."""
    src = _source()
    a = anchor_mod.annotate_a(src)
    b = json.loads(json.dumps(anchor_mod.annotate_b(src)))
    b["claim"]["object"] = "somewhere_else"          # inject disagreement
    adj = anchor_mod.adjudicate(a, b)
    assert adj["agree"] is False
    assert adj["outcome"] == "AMBIGUOUS"
    assert "disagreement" in adj
    with pytest.raises(ValueError):
        anchor_mod.final_anchor(src, adj)


def test_adjudication_matches_committed_artifact():
    src = _source()
    adj = anchor_mod.adjudicate(
        anchor_mod.annotate_a(src), anchor_mod.annotate_b(src),
        source_span={"source": "source.json", "text": src["srt"]})
    assert adj == _load(CASE, "anchor", "adjudication.json")


def test_final_anchor_matches_committed_artifact():
    src = _source()
    adj = anchor_mod.adjudicate(anchor_mod.annotate_a(src), anchor_mod.annotate_b(src))
    assert anchor_mod.final_anchor(src, adj) == _load(CASE, "anchor", "final_anchor.json")


# --- §11-§13 lifecycle ------------------------------------------------------

def test_locked_anchor_is_locked():
    fa = _load(CASE, "anchor", "final_anchor.json")
    assert anchor_mod.state(fa) == anchor_mod.LOCKED
    assert anchor_mod.is_locked(fa)


@pytest.mark.parametrize("trigger", list(anchor_mod.CHALLENGE_TRIGGERS))
def test_challenge_moves_locked_to_challenged(trigger):
    fa = _load(CASE, "anchor", "final_anchor.json")
    ch = anchor_mod.challenge(fa, trigger=trigger, evidence="span mismatch", by="reviewer")
    assert anchor_mod.state(ch) == anchor_mod.CHALLENGED
    assert not ch["locked"]
    # input not mutated in place (§13)
    assert fa["locked"] is True
    assert "lifecycle" not in fa


def test_unknown_challenge_trigger_rejected():
    fa = _load(CASE, "anchor", "final_anchor.json")
    with pytest.raises(ValueError):
        anchor_mod.challenge(fa, trigger="made_up", evidence="x", by="y")


def test_supersession_is_versioned_and_traceable():
    v1 = _load(CASE, "anchor", "final_anchor.json")
    old = anchor_mod.mark_superseded(
        v1, reason="new_evidence", evidence="doc #42", adjudicator="adjudicator",
        superseded_by="2.0")
    v2 = anchor_mod.supersede(
        v1, new_version="2.0", reason="new_evidence", evidence="doc #42",
        adjudicator="adjudicator")
    assert anchor_mod.state(old) == anchor_mod.SUPERSEDED
    assert old["lifecycle"]["superseded_by"] == "2.0"
    assert v2["anchor_version"] == "2.0"
    assert v2["lifecycle"]["supersedes"] == "1.0"
    assert v2["lifecycle"]["reason"] == "new_evidence"
    assert anchor_mod.state(v2) == anchor_mod.LOCKED
    # v1 untouched
    assert v1["anchor_version"] == "1.0"


# --- §8 provenance cross-checks ---------------------------------------------

def test_committed_anchor_matches_legacy_anchor_claims():
    """The new provenance anchor must agree with the pipeline's anchor.json claims."""
    legacy = _load(CASE, "anchor.json")
    final = _load(CASE, "anchor", "final_anchor.json")
    lc = legacy["claims"][0]
    fc = final["claims"][0]
    assert (lc["subject"], lc["predicate"], lc["object"], lc["contract"]) == \
           (fc["subject"], fc["predicate"], fc["object"], fc["contract"])


def test_anchor_module_does_not_import_runtime_engine():
    """The annotators must not depend on the runtime under test (§10)."""
    import ast
    path = os.path.join(ROOT, "runtime", "world_state", "anchor.py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    assert not (imported & {"compiler", "runtime", "world_state.compiler"})
