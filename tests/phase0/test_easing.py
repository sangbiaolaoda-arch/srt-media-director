"""Canonical easing / time-parameterization tests (code-capability upgrade).

Proves the canonical vocabulary is a real single source of truth:

* every named curve is a valid easing (f(0)=0, f(1)=1),
* alias/format resolution is consistent (camel == kebab == snake == bezier),
* unknown names degrade to linear instead of raising,
* ``pr`` is pure and clamped, and
* the divergence audit actually measures drift between subsystems (documenting
  the known divergences as live, quantified facts).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from timeline import audit, easing  # noqa: E402


# --- curve validity ----------------------------------------------------------

def test_all_named_curves_hit_both_endpoints():
    for name in easing.canonical_names():
        fn = easing.resolve(name)
        assert fn is not None, name
        assert fn(0.0) == pytest.approx(0.0, abs=1e-9), name
        assert fn(1.0) == pytest.approx(1.0, abs=1e-9), name


def test_standard_curves_are_monotone_nondecreasing():
    monotone = ["linear", "smoothstep", "easeInQuad", "easeOutQuad", "easeInOutQuad",
                "easeInCubic", "easeOutCubic", "easeInOutCubic", "easeInSine",
                "easeOutSine", "easeInOutSine", "easeInExpo", "easeOutExpo"]
    for name in monotone:
        prev = -1.0
        for i in range(41):
            v = easing.evaluate(name, i / 40.0)
            assert v >= prev - 1e-9, (name, i, v, prev)
            prev = v


def test_out_curves_lead_in_curves_in_the_middle():
    # at p=0.5 a decelerating ("out") curve is ahead of an accelerating ("in") one
    assert easing.evaluate("easeOutQuad", 0.5) > easing.evaluate("easeInQuad", 0.5)
    assert easing.evaluate("easeOutCubic", 0.5) > easing.evaluate("easeInCubic", 0.5)


# --- alias / format resolution ----------------------------------------------

def test_kebab_camel_snake_are_equivalent():
    vals = [easing.evaluate(s, 0.37) for s in ("ease-out", "easeOut", "ease_out", "easeout")]
    assert max(vals) - min(vals) < 1e-12
    assert easing.canonical_name("ease-out") == "easeOutQuad"


def test_bare_keywords_are_penner_not_css():
    # 'ease-in' (kebab) must resolve to the Penner quadratic, NOT the CSS keyword
    assert easing.canonical_name("ease-in") == "easeInQuad"
    assert easing.canonical_name("cssEaseIn") == "cssEaseIn"
    assert easing.canonical_name("ease") == "cssEase"


def test_cubic_bezier_parsing_and_identity_line():
    # cubic-bezier(0,0,1,1) is exactly linear
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert easing.evaluate("cubic-bezier(0,0,1,1)", p) == pytest.approx(p, abs=1e-6)
    assert easing.is_known("cubic-bezier(.2,.7,.2,1)") is True
    # cssEaseIn equals its explicit bezier form
    for p in (0.1, 0.4, 0.9):
        assert easing.evaluate("cssEaseIn", p) == pytest.approx(
            easing.evaluate("cubic-bezier(0.42,0,1,1)", p), abs=1e-6)


def test_unknown_is_flagged_and_degrades_to_linear():
    assert easing.is_known("nonsense") is False
    assert easing.canonical_name("nonsense") is None
    # never raises: falls back to linear
    assert easing.evaluate("nonsense", 0.42) == pytest.approx(0.42)


def test_absent_easing_is_linear():
    assert easing.canonical_name(None) == "linear"
    assert easing.canonical_name("") == "linear"
    assert easing.evaluate(None, 0.3) == pytest.approx(0.3)


# --- time parameterization ---------------------------------------------------

def test_pr_before_and_after_the_span():
    assert easing.pr(0.0, 1.0, 2.0) == 0.0
    assert easing.pr(0.5, 1.0, 2.0) == 0.0
    assert easing.pr(3.0, 1.0, 2.0) == 1.0


def test_pr_midpoint_and_easing_applied():
    assert easing.pr(1.5, 1.0, 2.0) == pytest.approx(0.5)
    # easeOutBack overshoots beyond 1 inside the span (a real, expected property)
    mid = easing.pr(1.5, 1.0, 2.0, "easeOutBack")
    assert mid != pytest.approx(0.5)
    assert easing.pr(2.0, 1.0, 2.0, "easeOutBack") == pytest.approx(1.0)


def test_pr_zero_span_is_instant_step():
    assert easing.pr(1.0, 1.0, 1.0) == 1.0
    assert easing.pr(0.999, 1.0, 1.0) == 0.0


def test_lerp_and_mix():
    assert easing.lerp(10.0, 20.0, 0.25) == pytest.approx(12.5)
    assert easing.mix(10.0, 20.0, 0.25) == easing.lerp(10.0, 20.0, 0.25)


def test_evaluation_is_deterministic():
    a = [easing.evaluate("easeInOutCubic", i / 50.0) for i in range(51)]
    b = [easing.evaluate("easeInOutCubic", i / 50.0) for i in range(51)]
    assert a == b


# --- divergence audit (documents real cross-subsystem drift) ------------------

def test_audit_runs_on_the_real_subsystems():
    recs = audit.divergences()
    assert recs, recs
    # every record must carry a measurable delta OR an explicit error/unknown tag
    for r in recs:
        assert "source" in r
        assert ("max_delta" in r) or ("error" in r)


def test_audit_quantifies_the_known_easing_divergences():
    by = {(r.get("source"), r.get("name")): r for r in audit.divergences()}

    # motion/render treats 'ease-out' as CUBIC while canonical is QUADRATIC
    mr = by.get(("motion.render._ease", "ease-out"))
    if mr is not None and mr.get("max_delta") is not None:
        assert mr["max_delta"] > 0.02, mr

    # motion/render IGNORES a cubic-bezier string (falls back to smoothstep)
    bz = by.get(("motion.render._ease", "cubic-bezier(.2,.7,.2,1)"))
    if bz is not None and bz.get("max_delta") is not None:
        assert bz["max_delta"] > 0.02, bz

    # motion_runtime uses quad for 'easeOut' -> matches canonical quad (no drift)
    rt = by.get(("motion_runtime.contracts", "easeOut"))
    if rt is not None and rt.get("max_delta") is not None:
        assert rt["max_delta"] < 1e-6, rt
