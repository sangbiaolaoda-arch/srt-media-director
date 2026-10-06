"""P0-2 gates — the single acceptance chain (verification.threelayer).

The runner (tools/verify_change.py) and the verdict share ONE data model.  These
tests lock the data model and the "no skip -> no PASS" rule without paying for a
full pytest run (the runner is exercised end-to-end separately).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from verification import acceptance, authority, threelayer  # noqa: E402

EXPECTED = ("targeted", "full_pytest", "real_srt", "render", "adversarial",
            "judge_guard", "evaluation")


def test_layer_model_is_the_seven_chain():
    assert threelayer.LAYERS == EXPECTED
    # each layer has exactly one question
    assert set(threelayer.QUESTIONS) == set(EXPECTED)


def test_empty_ledger_has_all_layers_missing():
    led = threelayer.empty_ledger()
    assert threelayer.missing_layers(led) == list(EXPECTED)
    v, reasons = threelayer.verdict(led, by="validator")
    assert v == "UNRESOLVED" and reasons


def test_cannot_skip_a_layer(tmp_path):
    led = threelayer.empty_ledger()
    for layer in EXPECTED[:-1]:
        ev = tmp_path / (layer + ".txt")
        ev.write_text("ok")
        threelayer.record(led, layer, str(ev), "ok")
    # evaluation still missing -> cannot PASS even though anything else is present
    v, reasons = threelayer.verdict(led, by="validator")
    assert v == "UNRESOLVED"
    assert threelayer.missing_layers(led) == ["evaluation"]


def test_recorded_but_nonexistent_evidence_does_not_count():
    led = threelayer.empty_ledger()
    threelayer.record(led, "targeted", "/no/such/evidence.log", "claimed")
    assert "targeted" in threelayer.missing_layers(led)


def test_all_layers_but_no_authority_is_unresolved(tmp_path):
    led = threelayer.empty_ledger()
    for layer in EXPECTED:
        ev = tmp_path / (layer + ".txt")
        ev.write_text("evidence")
        threelayer.record(led, layer, str(ev), "ok")
    v, reasons = threelayer.verdict(led, by="validator")
    assert v == "UNRESOLVED"          # no signing authority present
    assert reasons


def test_all_layers_with_authority_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("SMD_JUDGE_KEY", "chain-secret")
    led = threelayer.empty_ledger()
    for layer in EXPECTED:
        ev = tmp_path / (layer + ".txt")
        ev.write_text("evidence")
        threelayer.record(led, layer, str(ev), "ok")
    with authority.JudgeSession(by="validator"):
        v, reasons = threelayer.verdict(led, by="validator")
    assert v == "PASS" and reasons == []

    # and the same chain collapses to UNRESOLVED once one evidence file is gone
    os.remove(str(tmp_path / "render.txt"))
    with authority.JudgeSession(by="validator"):
        v2, _ = threelayer.verdict(led, by="validator")
    assert v2 == "UNRESOLVED"
