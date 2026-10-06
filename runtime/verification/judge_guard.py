"""Judge seal — the agent may modify production code, never the judges.

A sealed manifest of judge files (validator / observer / thresholds / gates /
golden oracle / eval dataset) is committed.  ``verify()`` recomputes hashes and
reports any change.  A change to a judge file makes the guard FAIL until the
manifest is *deliberately re-sealed*.

Re-seal is a PRIVILEGED, auditable act: it requires the judge signing authority
(``SMD_JUDGE_KEY``, see ``authority``).  An agent without the key cannot silently
"fix" the seal after editing a judge — the guard stays FAILED.  Every re-seal
appends an entry to ``reseal_log.json`` (who / when / how many files / key id).
``reseal_log.json`` is ITSELF a sealed file, so ``write_manifest`` must write the
log entry BEFORE computing the seal (see the ordering note in ``write_manifest``).

HONEST LIMITS (see ``audit()``): this is tamper-EVIDENT, not tamper-PROOF.  In a
single sandbox with arbitrary code execution and the key present, an agent could
still edit both the judge and the log.  Real isolation needs a separate process /
host that holds the key and re-seals off-agent.  We do not pretend otherwise.
"""
import datetime
import glob
import hashlib
import json
import os

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JUDGE_PATTERNS = [
    "runtime/validator.py",
    "runtime/rep_metrics.py",
    "runtime/observer/**/*.py",
    "runtime/observer/**/*.json",
    "runtime/gates/**/*.py",
    "runtime/gate_lib.py",
    "runtime/self_test.py",
    "runtime/verification/**/*.py",
    # The reseal log is itself a judge artifact: seal it too (judge_manifest.json
    # is excluded by basename in judge_files(); it cannot seal its own hash).
    "runtime/verification/**/*.json",
    "tools/verify_change.py",
    "tests/golden/**",
    "tests/test_golden.py",
    "tests/test_known_failures.py",
    "tools/real_content_eval.py",
    "tools/equivalence_probe.py",
    "docs/real-content-eval.json",
]

MANIFEST = os.path.join(_REPO, "runtime", "verification", "judge_manifest.json")
RESEAL_LOG = os.path.join(_REPO, "runtime", "verification", "reseal_log.json")


def _rel(path):
    return os.path.relpath(path, _REPO).replace(os.sep, "/")


def judge_files():
    out = set()
    for pat in JUDGE_PATTERNS:
        for p in glob.glob(os.path.join(_REPO, pat), recursive=True):
            if os.path.isfile(p) and os.path.basename(p) != "judge_manifest.json":
                out.add(p)
    return sorted(out)


def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def seal():
    files = {_rel(p): _hash(p) for p in judge_files()}
    return {"sealed": True, "count": len(files), "files": files}


def write_manifest(path=MANIFEST, by="operator"):
    """Re-seal — PRIVILEGED.  Refuses without the judge signing authority.

    ORDERING MATTERS.  ``reseal_log.json`` is itself a sealed file, so it must be
    FINAL before ``seal()`` runs.  The old order sealed first and appended the log
    afterwards, so the manifest committed the log's *pre-write* hash — the act of
    appending the reseal entry then made ``verify()`` report the log as changed and
    a "successful" re-seal still failed verify (a self-referential-hash bug).

    Correct order:
      1. make sure the reseal log exists (so it is part of the sealed set);
      2. append THIS reseal entry and write the log;
      3. ``seal()`` — captures the log's final content;
      4. write ``judge_manifest.json`` with that seal.
    Then ``write_manifest(...)`` followed by ``verify()`` is consistent (ok=True).
    """
    from . import authority  # local import: authority imports claims, avoid cycle
    if not authority.signing_available():
        raise PermissionError(
            "re-seal requires the judge signing authority (SMD_JUDGE_KEY); "
            "an agent without the key cannot re-seal the judge system")

    # 1. Ensure the reseal log exists so judge_files() includes it.
    if not os.path.isfile(RESEAL_LOG):
        with open(RESEAL_LOG, "w", encoding="utf-8") as fh:
            json.dump([], fh)
    # The sealed-file count is content-independent, so it is stable across the log
    # write below; the entry records it and it equals data["count"].
    count = len(judge_files())

    # 2. Append this reseal entry and write the log BEFORE sealing.
    log = []
    if os.path.isfile(RESEAL_LOG):
        try:
            log = json.load(open(RESEAL_LOG, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            log = []
    entry = {"by": by, "count": count,
             "key": authority.key_fingerprint(),
             "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    log.append(entry)
    with open(RESEAL_LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=2)

    # 3. Seal AFTER the log is final, then 4. write the manifest.
    data = seal()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return data


def verify(path=MANIFEST):
    if not os.path.isfile(path):
        return {"ok": False, "reason": "no sealed manifest at %s" % _rel(path),
                "changed": [], "added": [], "removed": []}
    sealed = json.load(open(path, encoding="utf-8"))["files"]
    current = {_rel(p): _hash(p) for p in judge_files()}
    changed = sorted(k for k in sealed if k in current and sealed[k] != current[k])
    added = sorted(k for k in current if k not in sealed)
    removed = sorted(k for k in sealed if k not in current)
    ok = not (changed or added or removed)
    return {"ok": ok, "changed": changed, "added": added, "removed": removed}


def audit():
    """Answer the judge-seal attack-surface questions with the current facts."""
    res = verify()
    from . import authority
    return {
        "q1_can_agent_edit_manifest_and_reseal": (
            "no without key: write_manifest() requires SMD_JUDGE_KEY; "
            "editing judge_manifest.json directly is itself a sealed-file change "
            "detected on next verify()"),
        "q2_who_holds_reseal": "the judge signing authority (SMD_JUDGE_KEY holder)",
        "q3_reseal_is_explicit": bool(os.path.isfile(RESEAL_LOG)),
        "q4_new_file_bypass": "any file matching JUDGE_PATTERNS is auto-sealed; "
                              "a new judge-named file shows up as 'added' -> FAIL",
        "q5_move_logic_to_unsealed_file": (
            "detected only if the new path matches JUDGE_PATTERNS; otherwise this is "
            "a residual gap -> requires review (not silently trusted)"),
        "q6_import_path_swap": (
            "a swapped import that pulls judge logic from an unsealed module is NOT "
            "machine-detected here -> residual gap, needs human review"),
        "signing_available_in_this_process": authority.signing_available(),
        "current": res,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "seal":
        d = write_manifest()
        print("sealed %d judge files" % d["count"])
    elif len(sys.argv) > 1 and sys.argv[1] == "audit":
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
