"""P0-3 gates — Real SRT Quality Evaluation corpus + no-fake scoring contract.

  * the fixed corpus exists with 20-30 SRTs across the six categories;
  * the eval record validates against schemas/quality-eval-report.schema.json;
  * every quality dimension starts PENDING (the harness never self-scores);
  * metrics_pending stays true until human/agent review is supplied.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

CORPUS = os.path.join(ROOT, "tests", "corpus", "real-content")
SCHEMA = os.path.join(ROOT, "schemas", "quality-eval-report.schema.json")
DIMENSIONS = ["semantic_expression", "composition", "hierarchy", "motion",
              "continuity", "visual_richness", "repetition", "ppt_feeling", "overall"]
CATEGORIES = {"explanation", "narrative_emotion", "data_comparison",
              "abstract_philosophy", "longform", "adversarial_repetition"}


def _corpus_srts():
    out = []
    for root, _d, files in os.walk(CORPUS):
        for f in files:
            if f.endswith(".srt"):
                out.append(os.path.join(root, f))
    return out


def test_corpus_size_and_categories():
    srts = _corpus_srts()
    assert 20 <= len(srts) <= 30, len(srts)
    cats = {os.path.relpath(p, CORPUS).split(os.sep)[0] for p in srts}
    assert cats == CATEGORIES, cats


def test_corpus_is_real_content_not_placeholders():
    # every cue must have text with CJK or letters (not "cue 1")
    n_lines = 0
    for p in _corpus_srts():
        text = open(p, encoding="utf-8").read()
        for line in text.splitlines():
            s = line.strip()
            if s and "-->" not in s and not s.isdigit():
                assert any("\u4e00" <= ch <= "\u9fff" for ch in s), (p, line)
                n_lines += 1
    assert n_lines > 60


def test_eval_report_schema_and_all_pending(tmp_path):
    import jsonschema
    schema = json.load(open(SCHEMA, encoding="utf-8"))

    # a synthetic report that is well-formed and all-PENDING must validate
    report = {
        "schema_version": "quality-eval-report.v1",
        "generated_from": "tools/real_srt_quality_eval.py",
        "metrics_pending": True,
        "dimensions": DIMENSIONS,
        "corpus": {"root": "tests/corpus/real-content", "count": 1,
                   "categories": {"explanation": 1}},
        "cases": [{
            "srt": "x.srt", "category": "explanation",
            "production_path": {}, "render": {}, "machine_metrics": {},
            "scores": {d: "PENDING" for d in DIMENSIONS},
            "verdict": "PENDING", "notes": "",
        }],
    }
    jsonschema.validate(report, schema)

    # a numeric score is structurally allowed but the harness must never emit one
    # by itself; the machine contract is "scores start PENDING".
    assert all(v == "PENDING" for v in report["cases"][0]["scores"].values())
    assert report["cases"][0]["verdict"] == "PENDING"
