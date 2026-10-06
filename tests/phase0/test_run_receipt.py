"""Gates for the production run receipt (anti-laziness, wired into pipeline.run).

The receipt must (a) always be written, (b) record stages in order without
skipping, (c) never earn the RENDERED stage when the raster probe was skipped,
(d) leave EVALUATED unrecorded (so a run ends UNRESOLVED, not PASS), and
(e) contain no self-certifying status token.
"""
import json
import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

SRT = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


def _run(render):
    import pipeline

    out = tempfile.mkdtemp(prefix="receipt_")
    pipeline.run(SRT, out, render_previews=render, log=lambda *a: None)
    path = os.path.join(out, "work", "run-receipt.json")
    assert os.path.exists(path), "pipeline.run must leave work/run-receipt.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_receipt_is_machine_unresolved():
    r = _run(render=True)
    # The machine path must never self-declare PASS; it can only raise the floor.
    assert r["verdict"]["verdict"] == "UNRESOLVED"
    assert r["verdict"]["by"] == "validator"
    assert r["verdict"]["evidence"], "a verdict must carry evidence pointers"


def test_stages_are_ordered_and_never_skip():
    r = _run(render=True)
    order = ["PLANNED", "GENERATED", "VERIFIED", "RENDERED"]
    got = [s["stage"] for s in r["stages"]]
    assert got == order[:len(got)], got
    # EVALUATED has no automatic evidence -> it can never be recorded here.
    assert "EVALUATED" not in got
    assert r["next_stage"] == "EVALUATED"


def test_render_skipped_does_not_earn_rendered_stage():
    r = _run(render=False)
    got = [s["stage"] for s in r["stages"]]
    assert "RENDERED" not in got, "skipped raster probe must not earn RENDERED"
    assert r["next_stage"] == "RENDERED"


def test_receipt_carries_no_forbidden_self_status():
    r = _run(render=True)
    blob = json.dumps(r, ensure_ascii=False).lower()
    for bad in ('"status": "pass"', '"verified": true', '"approved": true',
                '"verdict": "pass"'):
        assert bad not in blob, "receipt must not self-certify: %s" % bad
