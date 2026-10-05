"""Phase 0 — aesthetic canonicalization machine checks (P2).

Proves the post-process grade is single-sourced:

  * one vignette falloff model (zero inside the inner ratio, rising to strength);
  * both surfaces (raster + player) consume the canonical grade;
  * no renderer hardcodes a grade literal;
  * the observer keeps its own, independent luminance model.
"""
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from aesthetic_canonical import grade, audit, boundary_report  # noqa: E402

THEME = {"vignette": 0.55, "letterbox": 0.06, "grain": 6.0,
         "bg_top": "#0a0a0c", "bg_bottom": "#141418"}


def test_falloff_is_zero_inside_inner_and_monotonic():
    inner = grade.VIGNETTE_INNER_RATIO
    assert grade.vignette_falloff(inner * 0.5, inner) == 0.0
    assert grade.vignette_falloff(inner, inner) == 0.0
    assert grade.vignette_falloff(1.0, inner) == 1.0
    prev = -1.0
    for i in range(101):
        v = grade.vignette_falloff(inner + (1 - inner) * i / 100.0, inner)
        assert v >= prev
        prev = v


def test_letterbox_single_formula():
    assert grade.letterbox_px(720, {"letterbox": 0.06}) == 43
    assert grade.letterbox_px(720, {"letterbox": 0.0}) == 0


def test_strength_readers_default_to_zero():
    assert grade.vignette_strength({}) == 0.0
    assert grade.grain_strength({}) == 0.0
    assert grade.letterbox_frac({}) == 0.0


def test_pil_mask_matches_falloff_and_is_zero_when_disabled():
    m = grade.vignette_mask_pil(32, 18, {"vignette": 0.0})
    assert m.size == (32, 18)
    assert set(m.getdata()) == {0}
    m2 = grade.vignette_mask_pil(32, 18, {"vignette": 1.0})
    assert max(m2.getdata()) > 0


def test_js_mirror_reports_canonical_inner_ratio():
    js = grade.js_grade_literals(THEME)
    assert js["inner_ratio"] == grade.VIGNETTE_INNER_RATIO == 0.45
    assert js["vignette"] == 0.55


def test_both_surfaces_consume_canonical_grade():
    div = audit.divergence()
    assert "raster_renderer.py" in div["consumers"], div
    assert "html_adapter.py" in div["consumers"], div
    assert div["both_surfaces_consume"], div


def test_no_hardcoded_grade_literal_remains():
    hits = audit.hardcoded_grade_literals()
    assert hits == [], hits


def test_observer_luma_stays_independent():
    """The observer must not import the canonical grade (it measures, not grades)."""
    import observer.pixel as px
    src = inspect.getsource(px)
    assert "aesthetic_canonical" not in src


def test_canonical_boundary_is_clean():
    assert boundary_report()["status"] == "PASS", boundary_report()
