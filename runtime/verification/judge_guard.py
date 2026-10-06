"""Judge seal — the agent may modify production code, never the judges.

A sealed manifest of judge files (validator / observer / thresholds / gates /
golden oracle / eval dataset) is committed.  ``verify()`` recomputes hashes and
reports any change.  A change to a judge file makes the guard FAIL until the
manifest is *deliberately re-sealed* (an explicit, auditable act).
"""
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
    "tools/verify_change.py",
    "tests/golden/**",
    "tests/test_golden.py",
    "tests/test_known_failures.py",
    "tools/real_content_eval.py",
    "tools/equivalence_probe.py",
    "docs/real-content-eval.json",
]

MANIFEST = os.path.join(_REPO, "runtime", "verification", "judge_manifest.json")


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


def write_manifest(path=MANIFEST):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = seal()
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


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "seal":
        d = write_manifest()
        print("sealed %d judge files" % d["count"])
    else:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
