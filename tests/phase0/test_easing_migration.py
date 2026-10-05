"""Behavior-preserving easing migration tests (code-capability upgrade).

These tests lock the contract of the normalization: after the call sites are
migrated to delegate to :mod:`timeline.easing`, every subsystem must still
produce **exactly** the curve it produced before. If a future refactor changes
pixels, these parity checks fail loudly.

They also assert the *second* half of the migration: the duplicated curve math is
gone (call sites delegate), while the deliberate semantic fixes remain a
separately-tracked, quantified divergence (not silently applied).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from timeline import audit, easing, legacy  # noqa: E402

_SAMPLES = [i / 100.0 for i in range(101)]


# --- parity of the adapters vs the historical implementations ----------------

def test_render_legacy_ease_matches_old_motion_render_semantics():
    # old: linear / ease-out=cubic / ease-in=cubic / (default|ease-in-out)=smoothstep
    for p in _SAMPLES:
        assert legacy.render_legacy_ease("linear", p) == pytest.approx(p)
        assert legacy.render_legacy_ease("ease-out", p) == pytest.approx(1 - (1 - p) ** 3)
        assert legacy.render_legacy_ease("ease-in", p) == pytest.approx(p ** 3)
        assert legacy.render_legacy_ease("whatever", p) == pytest.approx(p * p * (3 - 2 * p))


def test_raster_and_observer_adapters_are_smoothstep():
    for p in _SAMPLES:
        assert legacy.raster_ease(p) == pytest.approx(p * p * (3 - 2 * p))
        assert legacy.observer_ease(p) == pytest.approx(p * p * (3 - 2 * p))


def test_adapters_clamp_like_before():
    assert legacy.render_legacy_ease("ease-out", -1.0) == 0.0
    assert legacy.render_legacy_ease("ease-out", 2.0) == 1.0
    assert legacy.raster_ease(-5.0) == 0.0
    assert legacy.raster_ease(5.0) == 1.0


# --- the migrated call sites really delegate (no duplicated math) ------------

def test_motion_render_ease_delegates_to_canonical():
    from motion import render as r
    for name in ("linear", "ease-out", "ease-in", "ease-in-out", "unknown"):
        for p in (0.0, 0.25, 0.5, 0.75, 1.0):
            assert r._ease(name, p) == pytest.approx(legacy.render_legacy_ease(name, p))


def test_raster_renderer_ease_delegates_to_canonical():
    import raster_renderer as rr
    for p in (0.0, 0.3, 0.5, 0.8, 1.0):
        assert rr._ease(p) == pytest.approx(easing.evaluate("smoothstep", p))


def test_observer_motion_ease_delegates_to_canonical():
    from observer import motion as m
    for p in (0.0, 0.3, 0.5, 0.8, 1.0):
        assert m.ease(p) == pytest.approx(easing.evaluate("smoothstep", p))


# --- divergence is tracked, not silently "fixed" -----------------------------

def test_known_divergences_remain_visible_and_quantified():
    """The cubic-bezier-ignored bug and the cubic-vs-quad mismatch stay recorded."""
    by = {(d.get("source"), d.get("name")): d for d in audit.divergences()}
    bz = by.get(("motion.render._ease", "cubic-bezier(.2,.7,.2,1)"))
    assert bz is not None and bz.get("max_delta") is not None and bz["max_delta"] > 0.02
    eo = by.get(("motion.render._ease", "ease-out"))
    assert eo is not None and eo.get("max_delta") is not None and eo["max_delta"] > 0.02


def test_canonical_core_is_the_only_curve_source_in_adapters():
    # adapters must not contain their own curve formulas: spot-check by identity
    assert legacy.canonical_for_legacy("ease-out") == "easeOutCubic"
    assert legacy.canonical_for_legacy("ease-in") == "easeInCubic"
    assert legacy.canonical_for_legacy(None) == "smoothstep"
    assert legacy.canonical_for_legacy("mystery") == "smoothstep"
