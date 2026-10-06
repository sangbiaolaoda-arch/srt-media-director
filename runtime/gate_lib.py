"""Gate registry + shared fixtures for runtime self-test gates.

Split out of runtime/self_test.py. Import-safe: no gate implementations here,
only the registry, shared example fixtures, and the runner.
"""
import json
import os
import shutil
import sys
import tempfile
import re

RUNTIME = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(RUNTIME)
sys.path.insert(0, RUNTIME)

import beat_planner  # noqa: E402,F401
import composition_planner  # noqa: E402,F401
import entrance_planner  # noqa: E402,F401
import html_adapter  # noqa: E402,F401
import pipeline  # noqa: E402,F401
import raster_renderer  # noqa: E402,F401
import srt_parser  # noqa: E402,F401
import svg_art  # noqa: E402,F401
import visual_director  # noqa: E402,F401

EXAMPLE_SRT = os.path.join(ROOT, "examples", "minimal", "attention.srt")
EXAMPLE_OVERRIDES = os.path.join(ROOT, "examples", "minimal", "director_overrides.json")

GATES = []


def gate(name):
    def deco(fn):
        GATES.append((name, fn))
        return fn
    return deco


def _example_beats():
    analysis = srt_parser.analyze(EXAMPLE_SRT)
    return analysis, beat_planner.plan_beats(analysis["cues"])


def _example_dsl():
    _, beats = _example_beats()
    ov = visual_director.load_overrides(EXAMPLE_OVERRIDES)
    vplan, dsl = visual_director.direct(beats, ov)
    return vplan, dsl


def pytest_approx(x, tol=1e-9):
    """无需引入 pytest 的近似比较（self_test 是独立可执行脚本）。"""
    class _A:
        def __eq__(self, other):
            return abs(other - x) <= tol
    return _A()


_MOTION_TRUTH_DIRS = ("timeline", "observer", "motion_canonical", "geometry")


_EASE_FINGERPRINTS = (
    "1.0 - (1.0 - p)",
    "1 - (1 - p) ** 3",
    "1.70158",
    "2 * p * p",
    "def ease_out_cubic",
    "def ease_in_cubic",
    "def ease_out_back",
)


_MAT_FINGERPRINTS = (
    "a1 * a2 + c1 * b2",
    "b1 * a2 + d1 * b2",
    "cos, sin = math.cos(rad)",
)


def ordered_gates():
    """Gates in their original numeric order, independent of import order."""
    return sorted(GATES, key=lambda item: int(re.match(r"(\d+)", item[0]).group(1)))


def run_all():
    print("SRT Media Director — runtime self-test")
    failures = []
    for name, fn in ordered_gates():
        try:
            fn()
            print("  PASS  %s" % name)
        except Exception as e:  # noqa: BLE001 — report all failures, not the first
            failures.append((name, repr(e)))
            print("  FAIL  %s -> %r" % (name, e))
    if failures:
        print("\nSELF-TEST FAILED: %d gate(s)" % len(failures))
        for name, err in failures:
            print("  - %s: %s" % (name, err))
        return False
    print("\nSELF-TEST VERIFIED \u2714  (runtime may enter the directing pipeline)")
    return True
