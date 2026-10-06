"""M3 gates — anti-PPT observable metrics + version-comparison contract.

Locks the auxiliary metrics that turn "ppt_feeling" from a free-text note into
countable signals (they never decide PASS by themselves), and the before/after
comparison data model that must classify improvement/regression per case.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from real_srt_quality_eval import _anti_ppt, DIMENSIONS  # noqa: E402
import compare_quality  # noqa: E402


def _dsl():
    return {"beats": [
        {"beat_id": "b1", "strategy": "single_focus", "elements": [
            {"id": "t", "type": "text", "text": "a"}, {"id": "d", "role": "decoration"}]},
        {"beat_id": "b2", "strategy": "single_focus", "elements": [
            {"id": "t2", "type": "text", "text": "b"}]},
        {"beat_id": "b3", "strategy": "compare_split", "elements": [
            {"id": "n", "type": "number"}, {"id": "m", "type": "motif"}]},
    ]}


def _entrance():
    return {"beats": [
        {"beat_id": "b1", "lifecycle": {"t": {"enter": {"motion": "fade"}},
                                        "d": {"enter": {"motion": "fade"}}}},
        {"beat_id": "b2", "lifecycle": {"t2": {"enter": {"motion": "fade"}}}},
        {"beat_id": "b3", "lifecycle": {"n": {"enter": {"motion": "rise"}},
                                        "m": {"enter": {"motion": "pop"}}}},
    ]}


def test_anti_ppt_signals_are_countable_not_verdicts():
    m = _anti_ppt(_dsl(), _entrance())
    assert m["text_ratio"] == 0.4           # 2/5 elements are text
    assert m["template_repeat"] == round(2 / 3, 3)   # single_focus x2 of 3 beats
    assert m["max_consecutive_same_strategy"] == 2
    assert m["fade_only_motion_ratio"] == round(3 / 5, 3)  # 3 of 5 motions are fade
    assert m["text_dominant_beats"] == 1
    # it must be explicit that this is auxiliary, not a PPT verdict
    assert "not a PPT verdict" in m["_note"]


def test_dimensions_are_the_nine_review_axes():
    assert DIMENSIONS == ["semantic_expression", "composition", "hierarchy", "motion",
                          "continuity", "visual_richness", "repetition", "ppt_feeling", "overall"]


def test_comparison_classifies_direction(tmp_path):
    def mk(increase):
        return {"dimensions": DIMENSIONS, "cases": [{
            "srt": "x.srt", "category": "explanation",
            "production_path": {"status": "PASS"}, "render": {},
            "machine_metrics": {"distinct_strategies": 2 + increase, "ink_mean": 0.1,
                                "anti_ppt": {"text_ratio": 0.5 - 0.1 * increase,
                                             "fade_only_motion_ratio": 0.5}},
            "scores": {d: "PENDING" for d in DIMENSIONS}, "verdict": "PENDING"}]}

    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(mk(0)))
    c.write_text(json.dumps(mk(1)))
    out = tmp_path / "cmp"
    sys.argv = ["compare_quality", "--baseline", str(b), "--candidate", str(c), "--out", str(out)]
    compare_quality.main()
    md = json.load(open(out / "machine-diff.json", encoding="utf-8"))
    # more distinct strategies + lower text ratio => improved
    assert md["summary_counts"]["improved"] == 1
    assert md["per_case"][0]["verdict"] == "improved"
    assert os.path.isfile(out / "summary.md")
    assert os.path.isfile(out / "score-diff.json")
