"""META-0 - judge seal portability tests.

The verdict must depend on the repository's LOGICAL content, not on the working
tree's line endings:

    same logical content  ->  LF / CRLF / CR  ->  same canonical hash  ->  ok
    real content mutation ->  different hash  ->  FAIL

T1  LF == CRLF hash              T2  CR == LF hash
T3  CRLF seal -> LF verify PASS  T4  LF seal -> CRLF verify PASS
T5  content mutation FAIL        T6  added judge file FAIL
T7  removed judge file FAIL      T8  line-ending-only change PASS
T9  real content change FAIL     T10 manifest self-excluded, reseal log sealed
T11 write_manifest -> verify closed loop

Re-seal cases run against an ISOLATED repo skeleton: they never touch the real
runtime/verification/judge_manifest.json or reseal_log.json.  Operator authority
is monkeypatched for the test process only; production re-seal still requires the
real SMD_JUDGE_KEY, so CI (which holds no key) can only VERIFY.

Line endings are built as bytes([13]) / bytes([10]) instead of escape sequences,
so this file's own content cannot be corrupted by editor or transport handling of
backslash escapes.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_ROOT, os.path.join(_ROOT, "runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from runtime.verification import authority, judge_guard  # noqa: E402

CR = bytes([13])
LF = bytes([10])


def _fake_authority(monkeypatch):
    """Test-process-only stand-in for the operator's signing authority."""
    monkeypatch.setattr(authority, "signing_available", lambda: True)
    monkeypatch.setattr(authority, "key_fingerprint", lambda: "test000000000000")


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Isolated repo skeleton so a test re-seal can never touch the real seal."""
    repo = tmp_path / "repo"
    guard = repo / "runtime" / "verification"
    guard.mkdir(parents=True)
    (guard / "a_judge.py").write_bytes(b"import json" + LF + b"x = 1" + LF)
    (guard / "b_judge.py").write_bytes(b"y = 2" + LF)
    monkeypatch.setattr(judge_guard, "_REPO", str(repo))
    monkeypatch.setattr(judge_guard, "RESEAL_LOG", str(guard / "reseal_log.json"))
    return repo, str(guard / "judge_manifest.json")


# --- T1 / T2: canonicalisation folds REPRESENTATION, not content --------------
def test_T1_lf_and_crlf_hash_identically(tmp_path):
    lf = tmp_path / "lf.py"
    lf.write_bytes(b"a" + LF + b"b" + LF)
    crlf = tmp_path / "crlf.py"
    crlf.write_bytes(b"a" + CR + LF + b"b" + CR + LF)
    assert judge_guard._hash(str(lf)) == judge_guard._hash(str(crlf))


def test_T2_cr_and_lf_hash_identically(tmp_path):
    cr = tmp_path / "cr.py"
    cr.write_bytes(b"a" + CR + b"b" + CR)
    lf = tmp_path / "lf.py"
    lf.write_bytes(b"a" + LF + b"b" + LF)
    assert judge_guard._hash(str(cr)) == judge_guard._hash(str(lf))


def test_binary_bytes_are_never_line_canonicalised(tmp_path):
    a = tmp_path / "a.bin"
    a.write_bytes(bytes([0]) + CR + LF + bytes([1]))
    b = tmp_path / "b.bin"
    b.write_bytes(bytes([0]) + LF + bytes([1]))
    assert judge_guard._hash(str(a)) != judge_guard._hash(str(b))


# --- T3 / T4: the real cross-line-ending seal -> verify flow ------------------
def test_T3_crlf_seal_then_lf_verify_passes(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    f = repo / "runtime" / "verification" / "a_judge.py"
    f.write_bytes(b"import json" + CR + LF + b"x = 1" + CR + LF)
    judge_guard.write_manifest(path=manifest, by="test-t3")
    f.write_bytes(b"import json" + LF + b"x = 1" + LF)   # representation only
    res = judge_guard.verify(path=manifest)
    assert res["ok"], res


def test_T4_lf_seal_then_crlf_verify_passes(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    f = repo / "runtime" / "verification" / "a_judge.py"
    f.write_bytes(b"import json" + LF + b"x = 1" + LF)
    judge_guard.write_manifest(path=manifest, by="test-t4")
    f.write_bytes(b"import json" + CR + LF + b"x = 1" + CR + LF)
    res = judge_guard.verify(path=manifest)
    assert res["ok"], res


# --- T5 / T8 / T9: content must still be detected -----------------------------
def test_T5_content_mutation_fails(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    f = repo / "runtime" / "verification" / "a_judge.py"
    f.write_bytes(b"foo" + LF)
    judge_guard.write_manifest(path=manifest, by="test-t5")
    f.write_bytes(b"bar" + LF)
    res = judge_guard.verify(path=manifest)
    assert not res["ok"] and res["changed"], res


def test_T8_line_ending_only_change_passes(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    f = repo / "runtime" / "verification" / "a_judge.py"
    f.write_bytes(b"x = 1" + LF + b"y = 2" + LF)
    judge_guard.write_manifest(path=manifest, by="test-t8")
    f.write_bytes(b"x = 1" + CR + LF + b"y = 2" + CR + LF)
    assert judge_guard.verify(path=manifest)["ok"]


def test_T9_real_content_change_fails(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    f = repo / "runtime" / "verification" / "a_judge.py"
    f.write_bytes(b"import json" + LF)
    judge_guard.write_manifest(path=manifest, by="test-t9")
    f.write_bytes(b"import os" + LF)
    res = judge_guard.verify(path=manifest)
    assert not res["ok"]
    assert res["changed"] == ["runtime/verification/a_judge.py"], res


# --- T6 / T7: added / removed judge files -------------------------------------
def test_T6_added_judge_file_fails(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    judge_guard.write_manifest(path=manifest, by="test-t6")
    (repo / "runtime" / "verification" / "fake_judge.py").write_bytes(
        b"VALUE = 1" + LF)
    res = judge_guard.verify(path=manifest)
    assert not res["ok"]
    assert res["added"] == ["runtime/verification/fake_judge.py"], res


def test_T7_removed_judge_file_fails(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    judge_guard.write_manifest(path=manifest, by="test-t7")
    os.remove(repo / "runtime" / "verification" / "b_judge.py")
    res = judge_guard.verify(path=manifest)
    assert not res["ok"]
    assert res["removed"] == ["runtime/verification/b_judge.py"], res


# --- scheme identity: an unknown scheme must FAIL, never fall back ------------
def test_unknown_hash_scheme_fails_explicitly(tmp_repo, monkeypatch):
    _repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    doc = judge_guard.write_manifest(path=manifest, by="test-scheme")
    assert doc["hash_scheme"] == judge_guard.HASH_SCHEME
    doc["hash_scheme"] = "sha256-legacy-raw-v0"
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    res = judge_guard.verify(path=manifest)
    assert not res["ok"] and "migration" in res["reason"], res


# --- T10: sealed-set membership, on the REAL repository -----------------------
def test_T10_manifest_self_excluded_reseal_log_sealed_real_repo():
    rels = {judge_guard._rel(p) for p in judge_guard.judge_files()}
    assert "runtime/verification/judge_manifest.json" not in rels
    assert "runtime/verification/reseal_log.json" in rels


# --- T11: write_manifest -> verify closed loop --------------------------------
def test_T11_write_manifest_then_verify_closes_the_loop(tmp_repo, monkeypatch):
    repo, manifest = tmp_repo
    _fake_authority(monkeypatch)
    judge_guard.write_manifest(path=manifest, by="test-t11")
    res = judge_guard.verify(path=manifest)
    assert res["ok"] and res["hash_scheme"] == judge_guard.HASH_SCHEME, res
    log = json.load(open(repo / "runtime" / "verification" / "reseal_log.json",
                        encoding="utf-8"))
    assert log[-1]["by"] == "test-t11"


# --- real repository gate: the COMMITTED seal must verify ---------------------
def test_real_repo_committed_manifest_verifies():
    """The committed seal must verify on a clean checkout of THIS platform."""
    res = judge_guard.verify()
    assert res["ok"], res
