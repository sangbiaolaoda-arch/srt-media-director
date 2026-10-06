#!/usr/bin/env python3
"""Acceptance runner — the SINGLE machine gate for "is this change really done?".

There is exactly one place that defines completion.  It runs the mandatory chain,
binds each layer's evidence to a REAL output file, and issues a verdict through
the signed acceptance path (verification.acceptance).  An agent may run it, but:

  * without the judge signing authority (SMD_JUDGE_KEY) the verdict is UNRESOLVED;
  * it cannot skip a layer — every layer needs a recorded evidence file;
  * deleting those evidence files invalidates the verdict (digest breaks).

Chain (one question per layer; see verification.threelayer.QUESTIONS):

    targeted      -> pytest <targeted>        did the edit break its module?
    full_pytest   -> pytest                   did it break the rest?
    real_srt      -> tools/equivalence_probe  does real input still generate?
    render        -> real SRT raster render    did a render actually happen?
    adversarial   -> verification.adversarial  did the agent cheat?
    judge_guard   -> verification.judge_guard  was the judge system modified?
    evaluation    -> human/agent review file   is it *better*? (never auto-passed)

Any layer missing -> UNRESOLVED.  A non-PASS verdict exits 1; PASS exits 0.

Usage:
    python tools/verify_change.py --targeted tests/phase0 [--changed-path runtime/x.py]
        [--out DIR] [--evaluation docs/review-report.json] [--judge-key SECRET]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(REPO, "runtime")
sys.path.insert(0, RUNTIME)

from verification import (acceptance, adversarial, authority, judge_guard,  # noqa: E402
                          threelayer)


def _write(run_dir, name, obj):
    path = os.path.join(run_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2))
    return path


def _step(run_dir, name, cmd, timeout=3600):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    text = r.stdout + r.stderr
    path = _write(run_dir, name + ".log", text)
    return r.returncode, path, text.strip().splitlines()[-1:]


def _render_check(run_dir, srt="tests/golden/01-minimal/case.srt"):
    import pipeline
    out = tempfile.mkdtemp(prefix="verify_render_")
    rep = pipeline.run(os.path.join(REPO, srt), out, render_previews=True,
                       log=lambda *a: None)
    report = json.load(open(os.path.join(out, "work", "validation-report.json")))
    film = os.path.join(out, "film")
    ok = rep.get("status") == "PASS"
    info = {"srt": srt, "status": rep.get("status"), "film_dir_exists": os.path.isdir(film),
            "l4": report["layers"]["l4"], "work_dir": out}
    return info, _write(run_dir, "render.json", info), ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targeted", default="tests/phase0")
    ap.add_argument("--changed-path", action="append", default=[])
    ap.add_argument("--out", default=None)
    ap.add_argument("--evaluation", default=None,
                    help="path to a human/agent review file (evaluation layer)")
    ap.add_argument("--judge-key", default=None,
                    help="judge signing secret; if omitted, SMD_JUDGE_KEY is used")
    args = ap.parse_args()

    if args.judge_key:
        os.environ["SMD_JUDGE_KEY"] = args.judge_key

    run_dir = args.out or tempfile.mkdtemp(prefix="verify_change_")
    os.makedirs(run_dir, exist_ok=True)

    ledger = threelayer.empty_ledger()
    checks = {}

    # 1. targeted ------------------------------------------------------------
    rc, p, tail = _step(run_dir, "targeted", [sys.executable, "-m", "pytest", args.targeted, "-q"])
    checks["targeted"] = {"rc": rc, "evidence": p, "tail": tail}
    if rc == 0:
        threelayer.record(ledger, "targeted", p, "pytest %s rc=0" % args.targeted)

    # 2. full pytest ---------------------------------------------------------
    rc, p, tail = _step(run_dir, "full_pytest", [sys.executable, "-m", "pytest", "-q"])
    checks["full_pytest"] = {"rc": rc, "evidence": p, "tail": tail}
    if rc == 0:
        threelayer.record(ledger, "full_pytest", p, "full pytest rc=0")

    # 3. real SRT ------------------------------------------------------------
    rc, p, tail = _step(run_dir, "real_srt", [sys.executable, os.path.join("tools", "equivalence_probe.py")])
    checks["real_srt"] = {"rc": rc, "evidence": p, "tail": tail}
    if rc == 0:
        threelayer.record(ledger, "real_srt", p, "legacy==canonical")

    # 4. render --------------------------------------------------------------
    render, rp, r_ok = _render_check(run_dir)
    checks["render"] = render
    if r_ok:
        threelayer.record(ledger, "render", rp, "real raster render status=PASS")

    # 5. adversarial ---------------------------------------------------------
    adv = adversarial.scan(changed_paths=args.changed_path or None)
    ap_ = _write(run_dir, "adversarial.json", adv)
    checks["adversarial"] = {"findings": adv, "evidence": ap_}
    if not adv:
        threelayer.record(ledger, "adversarial", ap_, "no lazy path detected")

    # 6. judge guard ---------------------------------------------------------
    sealed = judge_guard.verify()
    gp = _write(run_dir, "judge_guard.json", sealed)
    checks["judge_guard"] = {"result": sealed, "evidence": gp}
    if sealed["ok"]:
        threelayer.record(ledger, "judge_guard", gp, "judge seal intact")

    # 7. evaluation (human/agent; never auto-passed) -------------------------
    if args.evaluation and os.path.isfile(args.evaluation):
        threelayer.record(ledger, "evaluation", os.path.abspath(args.evaluation),
                          "human/agent review supplied")
    checks["evaluation"] = {"evidence": args.evaluation, "present": bool(
        args.evaluation and os.path.isfile(args.evaluation))}

    # verdict — signed path; unsigned/failed -> UNRESOLVED/FAIL -----------------
    with authority.JudgeSession(by="validator") as sess:
        v, reasons = threelayer.verdict(ledger, by="validator")
        if adv:
            v, reasons = "FAIL", reasons + ["adversarial findings: %s" % adv]
        if not sealed["ok"]:
            v, reasons = "FAIL", reasons + ["judge seal broken: %s" % sealed]
        if not r_ok:
            v, reasons = "FAIL", reasons + ["render check failed"]

    result = {
        "verdict": v,
        "reasons": reasons,
        "run_id": sess.run_id,
        "signed": authority.signing_available(),
        "layers": threelayer.LAYERS,
        "questions": threelayer.QUESTIONS,
        "ledger": ledger,
        "missing_layers": threelayer.missing_layers(ledger),
        "checks": checks,
        "note": ("evaluation is human/agent review and stays PENDING until supplied; "
                 "without the judge signing authority the verdict cannot become PASS"),
    }
    if args.out:
        _write(run_dir, "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if v == "PASS" else 1)


if __name__ == "__main__":
    main()
