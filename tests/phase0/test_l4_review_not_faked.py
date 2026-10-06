"""P3 — L4 must NOT be machine-faked (VAL-01 invariant) + review scaffold gate.

L4 (semantic / visual aesthetic review) is human/agent work and may not be
automated until enough human-scored data exists. This gate locks the project's
own VAL-01 guarantee and the review-report contract that a future L4
auto-aesthetic must feed:

  1. the validator always emits ``l4: PENDING`` on real content (never a PASS);
  2. the review-report schema requires an explicit human verdict field per case
     (a machine cannot omit it) and only allows PENDING/PASS/FAIL;
  3. the scaffold starts every verdict PENDING and is schema-valid — so it can be
     filled by a human/agent but cannot self-certify.
"""
import json
import os
import subprocess
import sys
import tempfile

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, RUNTIME)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import l4_review_scaffold  # noqa: E402

SCHEMA = json.load(open(os.path.join(ROOT, "schemas", "review-report.schema.json")))
GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


def test_validator_l4_is_pending_on_real_content():
    out = tempfile.mkdtemp(prefix="l4gate_")
    subprocess.run(
        [sys.executable, "-c",
         "import sys;sys.path.insert(0,'%s');import pipeline;"
         "pipeline.run('%s','%s',render_previews=False,log=lambda *a:None)" % (RUNTIME, GOLDEN, out)],
        check=True, capture_output=True)
    rep = json.load(open(os.path.join(out, "work", "validation-report.json")))
    l4 = rep["layers"]["l4"]
    assert l4.startswith("PENDING"), l4
    assert "PASS" not in l4, l4


def test_review_schema_requires_human_verdict_per_case():
    item = SCHEMA["properties"]["cases"]["items"]
    for field in ("ppt_l4_1_standalone_claim", "ppt_l4_2_template_diversity",
                  "ppt_l4_3_graphic_necessity", "ppt_l4_4_memory_point", "verdict"):
        assert field in item["required"], field
    assert set(SCHEMA["definitions"]["verdict"]["enum"]) == {"PENDING", "PASS", "FAIL"}


def test_scaffold_starts_pending_and_is_schema_valid():
    report = l4_review_scaffold.build_report()
    body = {k: v for k, v in report.items() if k != "prompts"}
    jsonschema.validate(body, SCHEMA)
    assert report["l4_status"] == "PENDING"
    assert report["reviewer"] is None
    assert report["cases"]
    for c in report["cases"]:
        assert c["verdict"] == "PENDING"
        for f in ("ppt_l4_1_standalone_claim", "ppt_l4_2_template_diversity",
                  "ppt_l4_3_graphic_necessity", "ppt_l4_4_memory_point"):
            assert c[f] == "PENDING"
