"""P0 Real Content Evaluation: run the real SRT corpus through the converged
Production Path and prove byte-identical behaviour vs the ORIGINAL legacy planner.

Evidence:
  - per-SRT pipeline status (does real content render end-to-end?)
  - legacy(HEAD) entrance plan/audit  ==  new(canonical-delegated) plan/audit
"""
import importlib.util
import json
import os
import subprocess
import sys

ROOT = "/mnt/work/smd"
sys.path.insert(0, os.path.join(ROOT, "runtime"))

# Extract ORIGINAL legacy planner from HEAD (true pre-change implementation).
with open("/mnt/work/legacy_ep.py", "wb") as fh:
    fh.write(subprocess.check_output(
        ["git", "-C", ROOT, "show", "HEAD:runtime/entrance_planner.py"]))

spec = importlib.util.spec_from_file_location("legacy_ep", "/mnt/work/legacy_ep.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

import pipeline  # noqa: E402
import entrance_planner as new  # noqa: E402

SRTS = [
    "examples/minimal/attention.srt",
    "examples/run/attention-30s.srt",
    "examples/run/10月2日.srt",
    "examples/run/10月4日.srt",
    "examples/showcase/01-explanatory-tech/case.srt",
    "examples/showcase/02-narrative-emotion/case.srt",
    "examples/showcase/03-data-comparison/case.srt",
    "examples/showcase/04-longform-3min/case.srt",
    "tests/golden/01-minimal/case.srt",
    "tests/golden/02-numeric/case.srt",
    "tests/known-failures/F02-homogeneous-content/case.srt",
]

rows, eq_all = [], True
for srt in SRTS:
    out = "/mnt/work/eval_out"
    subprocess.run(["rm", "-rf", out])
    status = "?"
    try:
        rep = pipeline.run(os.path.join(ROOT, srt), out, render_previews=False,
                           log=lambda *a: None)
        status = rep["status"]
    except SystemExit as e:
        status = "GATE_FAIL: %s" % str(e)[:60]
    except Exception as e:  # noqa: BLE001
        status = "ERROR: %s" % str(e)[:60]
    vpath = os.path.join(out, "work", "visual-dsl.json")
    eq = None
    if os.path.isfile(vpath):
        dsl = json.load(open(vpath))
        a, b = legacy.plan(json.loads(json.dumps(dsl))), new.plan(json.loads(json.dumps(dsl)))
        eq = (a == b) and (legacy.audit(json.loads(json.dumps(a))) == new.audit(json.loads(json.dumps(b))))
        eq_all = eq_all and eq
    rows.append({"srt": srt, "status": status, "legacy==canonical": eq})

print(json.dumps({"all_equivalent": eq_all, "rows": rows}, ensure_ascii=False, indent=2))
json.dump({"all_equivalent": eq_all, "rows": rows},
          open("/mnt/work/real_eval.json", "w"), ensure_ascii=False, indent=2)
