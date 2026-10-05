"""Pixel regression lane — Directive v5 §37-§39, §64 Experiment F.

Pixel is a *perceptual advisory*, never the semantic judge (§37, §39). These
tests pin down two things:

  * a stable render produces an identical fingerprint (no drift);
  * a pixel-corrupted render (structure intact) -> PERCEPTUAL_DRIFT, while the
    structural contract still says the semantics are fine.

Experiment F: correct structure + pixel corruption => PERCEPTUAL_DRIFT.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from observer import browser, fidelity, pixel, render, taxonomy, thresholds  # noqa: E402

CASES = os.path.join(ROOT, "cases")
HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no functional browser")


def _anchor(case="cause_effect"):
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def _make_png(path, kind="split"):
    from PIL import Image
    im = Image.new("L", (200, 120), color=255)
    if kind == "split":
        for x in range(100):
            for y in range(120):
                im.putpixel((x, y), 20)
    elif kind == "corrupt":
        for x in range(200):
            for y in range(120):
                im.putpixel((x, y), (x * 7 + y * 3) % 256)
    im.save(path)
    return str(path)


# --- pure (no browser) ------------------------------------------------------

def test_identical_fingerprints_have_zero_drift(tmp_path):
    a = _make_png(tmp_path / "a.png", "split")
    b = _make_png(tmp_path / "b.png", "split")
    fa, fb = pixel.fingerprint(a), pixel.fingerprint(b)
    dist = pixel.fingerprint_distance(fa, fb)
    assert dist["comparable"] and dist["identical"]
    assert dist["drift_ratio"] == 0.0


def test_regression_detects_perceptual_drift(tmp_path):
    base = _make_png(tmp_path / "base.png", "split")
    corrupt = _make_png(tmp_path / "corrupt.png", "corrupt")
    sig_base = pixel.signal("", {"nodes": []}, _png_override=base)
    sig_corrupt = pixel.signal("", {"nodes": []}, _png_override=corrupt)
    rep = pixel.regression(sig_base["fingerprint"], sig_corrupt["fingerprint"], thresholds.default())
    assert rep["status"] == "PIXEL_DRIFT"
    assert rep["failure_class"] == taxonomy.PERCEPTUAL_DRIFT
    assert rep["fault_domain"] == "pixel"


def test_regression_ok_when_unchanged(tmp_path):
    base = _make_png(tmp_path / "base.png", "split")
    sig = pixel.signal("", {"nodes": []}, _png_override=base)
    rep = pixel.regression(sig["fingerprint"], sig["fingerprint"], thresholds.default())
    assert rep["status"] == "PIXEL_OK"
    assert rep["failure_class"] == taxonomy.PASS


def test_regression_without_baseline_is_neutral(tmp_path):
    base = _make_png(tmp_path / "base.png", "split")
    sig = pixel.signal("", {"nodes": []}, _png_override=base)
    rep = pixel.regression(None, sig["fingerprint"], thresholds.default())
    assert rep["status"] == "NO_BASELINE"
    assert rep["failure_class"] == taxonomy.PASS


def test_pixel_unavailable_is_environment_fail():
    rep = pixel.regression({"cells": []}, {"available": False, "error": "no browser"},
                           thresholds.default())
    assert rep["failure_class"] == taxonomy.ENVIRONMENT_FAIL


def test_compare_conflict_is_perceptual_drift(tmp_path):
    """A structural-vs-pixel contradiction is PERCEPTUAL_DRIFT, not a semantic fail."""
    png = _make_png(tmp_path / "blank.png", "blank")  # all white
    observed = {"nodes": [{"id": "a", "x": 0, "y": 0, "w": 50, "h": 50}]}
    sig = pixel.signal("", observed, _png_override=png)
    rep = pixel.compare(observed, sig, thresholds.default())
    assert rep["failure_class"] == taxonomy.PERCEPTUAL_DRIFT


# --- Experiment F end-to-end (browser-gated) --------------------------------

@needs_browser
def test_experiment_F_structure_ok_pixel_corrupted(tmp_path):
    """Correct structure + pixel corruption => PERCEPTUAL_DRIFT, structure stays OK."""
    ws = compiler.compile_world_state(_anchor())
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    obs = browser.observe(html)

    # structure is correct
    assert fidelity.compare(ws, obs)["status"] == "FIDELITY_OK"

    # baseline vs a *pixel-corrupted* capture of the same structure
    baseline = pixel.signal(html, obs, png_path=str(tmp_path / "base.png"))
    corrupt = pixel.signal(html, obs, _png_override=_make_png(tmp_path / "c.png", "corrupt"))
    rep = pixel.regression(baseline["fingerprint"], corrupt["fingerprint"], thresholds.effective())
    assert rep["status"] == "PIXEL_DRIFT", rep
    assert rep["failure_class"] == taxonomy.PERCEPTUAL_DRIFT
