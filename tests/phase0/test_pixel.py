"""Phase 0 step 9 — Pixel Signal tests.

Pure fingerprint / region logic is browser-free. Screenshot capture and the
structural-vs-pixel cross-check are browser-gated.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from entailment import load_contract  # noqa: E402
from observer import browser, fidelity, normalize, pixel, render, thresholds  # noqa: E402

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
    elif kind == "blank":
        pass
    im.save(path)
    return str(path)


# --- pure (no browser) ------------------------------------------------------


def test_fingerprint_deterministic(tmp_path):
    a = _make_png(tmp_path / "a.png", "split")
    b = _make_png(tmp_path / "b.png", "split")
    assert pixel.fingerprint(a)["hash"] == pixel.fingerprint(b)["hash"]


def test_fingerprint_separates_images(tmp_path):
    a = _make_png(tmp_path / "a.png", "split")
    z = _make_png(tmp_path / "z.png", "blank")
    assert pixel.fingerprint(a)["hash"] != pixel.fingerprint(z)["hash"]


def test_signal_without_browser_is_honest(monkeypatch, tmp_path):
    monkeypatch.setattr(pixel, "find_browser", lambda: None)
    monkeypatch.setattr(pixel, "available", lambda: False)
    p = tmp_path / "x.html"
    p.write_text("<html></html>", encoding="utf-8")
    s = pixel.signal(str(p), {"nodes": []})
    assert s["available"] is False


def test_compare_detects_blank(tmp_path):
    png = _make_png(tmp_path / "blank.png", "blank")
    observed = {"nodes": [{"id": "a", "x": 0, "y": 0, "w": 50, "h": 50}]}
    sig = pixel.signal("", observed, _png_override=png)
    rep = pixel.compare(observed, sig, thresholds.default())
    assert any(p["kind"] == "blank_screenshot" for p in rep["problems"])


def test_compare_detects_region_equals_background(tmp_path):
    png = _make_png(tmp_path / "blank.png", "blank")  # all white
    observed = {"nodes": [{"id": "a", "x": 0, "y": 0, "w": 50, "h": 50}]}
    sig = pixel.signal("", observed, _png_override=png)
    rep = pixel.compare(observed, sig, thresholds.default())
    assert any(p["kind"] == "pixel_region_matches_background" for p in rep["problems"])


def test_compare_ok_when_region_differs(tmp_path):
    png = _make_png(tmp_path / "split.png", "split")
    observed = {"nodes": [{"id": "dark", "x": 0, "y": 0, "w": 100, "h": 120},
                          {"id": "light", "x": 100, "y": 0, "w": 100, "h": 120}]}
    sig = pixel.signal("", observed, _png_override=png)
    rep = pixel.compare(observed, sig, thresholds.default())
    assert rep["status"] == "PIXEL_OK", rep
    assert rep["fingerprint_hash"]


def test_pixel_unavailable_is_honest(monkeypatch):
    observed = {"nodes": [{"id": "a", "x": 0, "y": 0, "w": 10, "h": 10}]}
    rep = pixel.compare(observed, {"available": False}, thresholds.default())
    assert rep["status"] == "PIXEL_UNAVAILABLE" and rep["available"] is False


# --- browser-gated ----------------------------------------------------------


@needs_browser
def test_real_screenshot_deterministic(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    a = pixel.capture(html, str(tmp_path / "a.png"))
    b = pixel.capture(html, str(tmp_path / "b.png"))
    assert a["available"] and b["available"]
    assert pixel.fingerprint(a["png"])["hash"] == pixel.fingerprint(b["png"])["hash"]


@needs_browser
def test_structural_and_pixel_both_ok(tmp_path):
    ws = compiler.compile_world_state(_anchor())
    html = render.render_world_state(ws, str(tmp_path / "w.html"))
    obs = browser.observe(html)
    assert fidelity.compare(ws, obs)["status"] == "FIDELITY_OK"
    sig = pixel.signal(html, obs)
    assert sig["available"]
    rep = pixel.compare(obs, sig, thresholds.effective())
    assert rep["status"] == "PIXEL_OK", rep
