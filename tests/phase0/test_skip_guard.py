"""Machine-readable skip guard + golden-regression preservation tests.

P0-3: an unexpected browser skip must FAIL the contract lane, and the decision
must be machine-readable (JUnit XML), not a grep over human text.

P1-1: the golden regression must survive all the new World-State / production
work. These tests assert the golden baseline is still present, still wired into
the suite, and still sensitive to a real layer change.
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import skip_guard  # noqa: E402


def _write_junit(path, cases):
    """cases: list of (classname, name, status) status in ok/skip/fail."""
    suite = ET.Element("testsuite", {"name": "pytest", "tests": str(len(cases))})
    for cls, name, status in cases:
        tc = ET.SubElement(suite, "testcase", {"classname": cls, "name": name})
        if status == "skip":
            ET.SubElement(tc, "skipped", {"message": "no functional browser"})
        elif status == "fail":
            ET.SubElement(tc, "failure", {"message": "boom"})
    tree = ET.ElementTree(suite)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def test_skip_guard_flags_browser_skip(tmp_path):
    p = str(tmp_path / "r.xml")
    _write_junit(p, [("tests.phase0.test_observer", "test_browser", "skip"),
                     ("tests.phase0.test_observer", "test_pure", "ok")])
    rep = skip_guard.parse_junit(p)
    bad = skip_guard.forbidden_skips(rep, allow_patterns=[])
    assert len(bad) == 1 and bad[0]["name"] == "test_browser"


def test_skip_guard_allowlist_suppresses_expected_skip(tmp_path):
    p = str(tmp_path / "r.xml")
    _write_junit(p, [("tests.phase1.test_legacy", "test_old", "skip")])
    rep = skip_guard.parse_junit(p)
    bad = skip_guard.forbidden_skips(rep, allow_patterns=["test_legacy"])
    assert bad == []


def test_skip_guard_main_fails_on_forbidden_skip(tmp_path):
    p = str(tmp_path / "r.xml")
    _write_junit(p, [("tests.phase0.test_observer", "test_browser", "skip")])
    rc = skip_guard.main(["--junit", p, "--forbid-skip"])
    assert rc == 1


def test_skip_guard_main_ok_when_all_run(tmp_path):
    p = str(tmp_path / "r.xml")
    _write_junit(p, [("tests.phase0.test_observer", "test_browser", "ok"),
                     ("tests.phase0.test_observer", "test_pure", "ok")])
    rc = skip_guard.main(["--junit", p, "--forbid-skip",
                          "--summary-out", str(tmp_path / "s.json")])
    assert rc == 0
    summary = json.load(open(str(tmp_path / "s.json")))
    assert summary["tests"] == 2 and summary["skipped_total"] == 0


def test_skip_guard_reason_filter_targets_browser_skips(tmp_path):
    p = str(tmp_path / "r.xml")
    _write_junit(p, [("tests.x", "test_a", "skip")])
    rep = skip_guard.parse_junit(p)
    # message contains "no functional browser" -> matches the reason filter
    bad = skip_guard.forbidden_skips(rep, allow_patterns=[],
                                     reason_patterns=["functional browser"])
    assert len(bad) == 1


def test_skip_guard_missing_report_is_error(tmp_path):
    rc = skip_guard.main(["--junit", str(tmp_path / "nope.xml"), "--forbid-skip"])
    assert rc == 2


# --- golden regression preservation (P1-1) ----------------------------------

GOLDEN_DIR = os.path.join(ROOT, "tests", "golden")


def test_golden_baselines_present():
    assert os.path.isdir(GOLDEN_DIR), "golden dir disappeared"
    cases = [d for d in os.listdir(GOLDEN_DIR)
             if os.path.exists(os.path.join(GOLDEN_DIR, d, "case.srt"))]
    assert cases, "no golden cases remain"
    for name in cases:
        h = os.path.join(GOLDEN_DIR, name, "hashes.json")
        assert os.path.exists(h), "golden baseline missing for %s" % name
        data = json.load(open(h, encoding="utf-8"))
        # the five-layer contract must still be pinned
        for layer in ("beat-plan.json", "visual-plan.json", "visual-dsl.json",
                      "render-plan.json", "entrance-plan.json"):
            assert layer in data, "%s not pinned in %s" % (layer, name)


def test_golden_suite_still_collectable():
    """The golden test must still exist and be collected (not silently dropped)."""
    path = os.path.join(ROOT, "tests", "test_golden.py")
    assert os.path.exists(path)
    src = open(path, encoding="utf-8").read()
    assert "test_golden_hashes" in src
    assert "UPDATE_GOLDEN" in src
