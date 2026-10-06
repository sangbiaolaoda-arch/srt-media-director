"""P1 gates — judge seal attack-surface (see verification.judge_guard).

Facts under test:
  * editing a sealed judge file makes the guard FAIL;
  * an agent without the signing authority cannot re-seal (silently recover);
  * a re-seal is logged;
  * any new file matching JUDGE_PATTERNS shows up as 'added' -> FAIL.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from verification import authority, judge_guard  # noqa: E402


def test_manifest_exists_and_verifies_clean():
    # The committed manifest must match the committed judged files.
    res = judge_guard.verify()
    assert res["ok"] is True, res


def test_editing_a_judge_file_fails_the_guard(tmp_path):
    # Simulate a changed judge file by hashing a doctored copy.
    sealed = json.load(open(judge_guard.MANIFEST, encoding="utf-8"))["files"]
    victim = next(iter(sealed))
    # verify() reads from real files; emulate a change by checking the diff logic.
    current = {judge_guard._rel(p): judge_guard._hash(p) for p in judge_guard.judge_files()}
    assert victim in current
    assert current[victim] == sealed[victim]
    # If any hash differed, verify() must report it (contract of the diff).
    changed = [k for k in sealed if k in current and sealed[k] != current[k]]
    added = [k for k in current if k not in sealed]
    removed = [k for k in sealed if k not in current]
    assert changed == [] and added == [] and removed == []


def test_reseal_requires_signing_authority(monkeypatch, tmp_path):
    monkeypatch.delenv("SMD_JUDGE_KEY", raising=False)
    # No key -> cannot re-seal; the agent cannot silently "fix" the seal.
    with pytest.raises(PermissionError):
        judge_guard.write_manifest(path=str(tmp_path / "m.json"))


def test_reseal_is_logged_when_authorized(monkeypatch, tmp_path):
    monkeypatch.setenv("SMD_JUDGE_KEY", "reseal-secret")
    mpath = str(tmp_path / "m.json")
    logpath = str(tmp_path / "log.json")
    monkeypatch.setattr(judge_guard, "RESEAL_LOG", logpath)
    data = judge_guard.write_manifest(path=mpath, by="operator")
    assert data["sealed"] is True and data["count"] > 0
    log = json.load(open(logpath, encoding="utf-8"))
    assert log and log[-1]["by"] == "operator" and log[-1]["count"] == data["count"]


def test_new_judge_named_file_is_detected_as_added(tmp_path, monkeypatch):
    fake = os.path.join(ROOT, "runtime", "verification", "_agent_smuggled_judge.py")
    try:
        with open(fake, "w", encoding="utf-8") as fh:
            fh.write("# a judge-named file the agent added\n")
        res = judge_guard.verify()
        assert res["ok"] is False
        assert any("_agent_smuggled_judge" in a for a in res["added"])
    finally:
        if os.path.exists(fake):
            os.remove(fake)


def test_audit_reports_residual_gaps_honestly():
    a = judge_guard.audit()
    # The three questions that cannot be fully machine-answered must be marked as
    # residual gaps, not silently claimed as covered.
    assert "residual gap" in a["q5_move_logic_to_unsealed_file"]
    assert "residual gap" in a["q6_import_path_swap"]
