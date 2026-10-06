#!/usr/bin/env python
"""Acceptance runner — the machine gate for "is this change really done?".

Runs the mandatory chain and writes a machine verdict.  An agent may run it and
report its output, but the verdict it prints is issued by this judge script, not
by the agent.

    targeted tests        ->   pytest <targeted>            (did code break?)
    full pytest           ->   pytest                       (did code break, wide?)
    real SRT regression   ->   tools/equivalence_probe.py + real_content_eval (film worse?)
    render check          ->   >=1 real SRT renders & validates (render actually happens?)
    adversarial scan      ->   verification.adversarial     (did the agent cheat?)

Evaluation (is it *better*) is human/agent review and stays PENDING by design.

Usage:
    python tools/verify_change.py --targeted tests/phase0 [--changed-path runtime/x.py ...]
"""
import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(REPO, "runtime")
sys.path.insert(0, RUNTIME)

from verification import adversarial, defaults, judge_guard, threelayer  # noqa: E402


def _run(cmd, timeout=1800):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def _render_check(srt="tests/golden/01-minimal/case.srt"):
    import tempfile
    sys.path.insert(0, RUNTIME)
    import pipeline
    out = tempfile.mkdtemp(prefix="verify_render_")
    rep = pipeline.run(os.path.join(REPO, srt), out, render_previews=False,
                       log=lambda *a: None)
    report = json.load(open(os.path.join(out, "work", "validation-report.json")))
    frames = os.path.join(out, "film")
    has_film = os.path.isdir(frames)
    ok = rep.get("status") == "PASS"
    return {"status": rep.get("status"), "film_dir": has_film,
            "l4": report["layers"]["l4"]}, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targeted", default="tests/phase0")
    ap.add_argument("--changed-path", action="append", default=[])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ledger = threelayer.empty_ledger()
    checks = {}

    rc, out = _run([sys.executable, "-m", "pytest", args.targeted, "-q"])
    checks["targeted"] = {"rc": rc, "tail": out.strip().splitlines()[-1:] }
    if rc == 0:
        threelayer.record(ledger, "tests", "pytest %s (rc=0)" % args.targeted,
                          checks["targeted"]["tail"])

    rc, out = _run([sys.executable, "-m", "pytest", "-q"])
    checks["full_pytest"] = {"rc": rc, "tail": out.strip().splitlines()[-1:]}

    rc, out = _run([sys.executable, os.path.join("tools", "equivalence_probe.py")])
    eq_ok = rc == 0
    checks["real_srt_equivalence"] = {"rc": rc, "ok": eq_ok}
    if eq_ok:
        threelayer.record(ledger, "real_srt", "tools/equivalence_probe.py (rc=0)", "legacy==canonical")

    render, r_ok = _render_check()
    checks["render"] = render
    checks["render"]["ok"] = r_ok

    adv = adversarial.scan(changed_paths=args.changed_path or None)
    checks["adversarial"] = adv

    sealed = judge_guard.verify()
    checks["judge_guard"] = sealed

    v, reasons = threelayer.verdict(ledger, by="validator")
    if not render.get("ok"):
        v, reasons = "FAIL", reasons + ["render check failed"]
    if adv:
        v, reasons = "FAIL", reasons + ["adversarial findings: %s" % adv]
    if not sealed["ok"]:
        v, reasons = "FAIL", reasons + ["judge seal broken: %s" % sealed]

    result = {
        "verdict": v,
        "reasons": reasons,
        "three_layer_ledger": ledger,
        "checks": checks,
        "note": "evaluation layer is human/agent review and stays PENDING",
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
    print(text)
    sys.exit(0 if v == "PASS" else 1)


if __name__ == "__main__":
    main()
