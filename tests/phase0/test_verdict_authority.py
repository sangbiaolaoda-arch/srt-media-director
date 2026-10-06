"""P0-1 / P1 gates — verdict authority isolation + evidence binding.

Facts under test:
  * an agent cannot self-declare PASS/verified/approved;
  * "by=validator" is not enough — a PASS needs the signing authority;
  * a signed verdict stops verifying when its evidence file is deleted/changed;
  * a forged signature never verifies.
"""
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from verification import acceptance, authority, claims, stages  # noqa: E402


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("SMD_JUDGE_KEY", "unit-test-secret")
    yield "unit-test-secret"


def test_agent_cannot_self_declare():
    with pytest.raises(claims.AgentSelfCertification):
        claims.AgentOutput("agent_claim", "done", {"verdict": "PASS"})
    with pytest.raises(claims.AgentSelfCertification):
        claims.AgentOutput("artifact", "ok", {"approved": True})


def test_pass_requires_authority_even_as_validator():
    # no key in the environment -> cannot mint a PASS, whatever we call ourselves.
    with pytest.raises(claims.Unauthorized):
        claims.issue_verdict("s", "PASS", by="validator", evidence=["e"])
    with pytest.raises(claims.Unauthorized):
        claims.issue_verdict("s", "FAIL", by="gate", evidence=["e"])


def test_unauthorized_role_cannot_issue():
    with pytest.raises(claims.Unauthorized):
        claims.issue_verdict("s", "UNRESOLVED", by="agent", evidence=[])


def test_signed_pass_verifies_then_dies_with_evidence(tmp_path, key):
    art = tmp_path / "artifact.json"
    art.write_text('{"ok": true}')
    with authority.JudgeSession(by="validator") as sess:
        doc = acceptance.issue("s", "PASS", by="validator",
                               evidence=[{"path": str(art), "observed": "artifact"}],
                               run_id=sess.run_id)
    assert doc["verdict"] == "PASS"
    assert doc["signature"]
    assert acceptance.evaluate(doc)[0] == "PASS"

    # Deleting the artifact the verdict was bound to invalidates the verdict.
    os.remove(art)
    v, reasons = acceptance.evaluate(doc)
    assert v == "UNRESOLVED"
    assert any("evidence" in r for r in reasons)

    # Changing the artifact also invalidates it.
    art2 = tmp_path / "artifact2.json"
    art2.write_text("original")
    with authority.JudgeSession(by="validator"):
        doc2 = acceptance.issue("s", "PASS", by="validator",
                                evidence=[{"path": str(art2), "observed": "x"}])
    art2.write_text("tampered")
    assert acceptance.evaluate(doc2)[0] == "UNRESOLVED"


def test_forged_signature_and_no_session_are_unresolved(tmp_path, key):
    art = tmp_path / "a.json"
    art.write_text("x")
    doc = {"subject": "s", "verdict": "PASS", "by": "validator",
           "evidence": [{"path": str(art), "observed": "x"}],
           "evidence_digest": acceptance.evidence_digest(
               [{"path": str(art), "observed": "x"}])[0],
           "run_id": "r", "issued_at": "now", "signature": "deadbeef"}
    assert acceptance.evaluate(doc)[0] == "UNRESOLVED"      # bad signature

    # No key -> not even a direct sign() call can produce a valid signature.
    payload = {"verdict": "PASS"}
    forged = authority.sign(payload) if authority.signing_available() else ""
    # simulate the no-key world
    import importlib
    monkeypatch_key = os.environ.pop("SMD_JUDGE_KEY", None)
    try:
        assert authority.verify_signature(payload, forged) is False
    finally:
        if monkeypatch_key is not None:
            os.environ["SMD_JUDGE_KEY"] = monkeypatch_key


def test_unsigned_verdict_is_unresolved_without_key():
    doc = acceptance.issue("s", "PASS", by="validator",
                           evidence=[{"path": "runtime/pipeline.py", "observed": "x"}])
    assert doc["verdict"] == "UNRESOLVED"
    assert "signing authority" in doc.get("reason", "")


def test_stage_promote_needs_authority():
    m = stages.StageMachine()
    m.submit("PLANNED", "x", {"task_contract": "c"})
    with pytest.raises(claims.Unauthorized):
        m.promote("PLANNED", "PASS", by="validator")     # judge role, no key
    assert m.promote("PLANNED", "UNRESOLVED", by="validator").verdict == "UNRESOLVED"
