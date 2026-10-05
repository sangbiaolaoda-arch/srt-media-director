"""Production render-chain contract tests (Final Practical Closeout Directive, P0).

Two tiers:

  * always-run (no browser): the expectation builder and the adjudicator must
    behave, and must never fabricate a PASS from an empty/unavailable
    observation.
  * browser-gated: compile the REAL film/index.html through the production
    pipeline, drive a REAL Chromium over it, and require the observer to confirm
    every declared element is actually painted (honestly degrading only the
    theme-dependent ``decor`` layer to advisory).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from observer import browser, production  # noqa: E402

HAS_BROWSER = browser.available()
needs_browser = pytest.mark.skipif(not HAS_BROWSER, reason="no Chromium binary available")

GOLDEN = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")


def _obs(samples, ink_of):
    """Synthesize a complete observation (all dimensions) from probe samples.

    Camera probes are answered with the *expected* zoom so a test that is only
    about the presence dimension is not falsely failed by the camera dimension.
    """
    rows = []
    for s in samples:
        if s.get("probe") == "camera":
            z = float(s["exp"]["zoom"])
            rows.append({"id": s["id"], "beat_id": s["beat_id"], "t": s["t"],
                         "present": True, "probe": "camera", "phase": s["phase"],
                         "zw": z, "zh": z})
        elif s.get("probe") == "relation":
            rel = s.get("rel") or {}
            if rel.get("channel") == "bridge_corridor":
                c = rel["corridor"]
                cx = (c["x0"] + c["x1"]) / 2.0
                cy = (c["y0"] + c["y1"]) / 2.0
                w = max(float(c.get("min_w", 120)), 120.0)
                gb = {"x": cx - w / 2.0, "y": cy - 2.0, "w": w, "h": 4.0}
            else:
                cx = float(rel.get("target_cx", 0))
                gb = {"x": cx - 30.0, "y": 0.0, "w": 60.0, "h": 10.0}
            rows.append({"id": s["id"], "beat_id": s["beat_id"], "t": s["t"],
                         "probe": "relation", "gink": 5000, "gbbox": gb})
        elif s.get("probe") == "temporal":
            ink = 0 if s.get("phase") == "onset" else 500
            rows.append({"id": s["id"], "beat_id": s["beat_id"], "t": s["t"],
                         "probe": "temporal", "phase": s["phase"], "ink": ink})
        else:
            rows.append({"id": s["id"], "t": s["t"], "present": s["present"],
                         "ink": ink_of(s)})
    return {"available": True, "backend": "x", "beats": 1, "samples": rows}


def _tiny_plan():
    """A tiny synthetic upstream plan: one beat, one text + one decor element."""
    dsl = {"beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 4.0,
                      "elements": [{"id": "t1", "type": "text"},
                                   {"id": "d1", "type": "decor"}]}]}
    render_plan = {"beats": [{"beat_id": "b1",
                              "boxes": {"t1": {"x": 100, "y": 100, "w": 200, "h": 40},
                                        "d1": {"x": 50, "y": 50, "w": 120, "h": 90}}}]}
    entrance = {"beats": [{"beat_id": "b1",
                           "lifecycle": {"t1": {"enter": {"at": 0.2, "dur": 0.5}},
                                         "d1": {"enter": {"at": 0.0, "dur": 0.4}}},
                           "events": []}]}
    return dsl, render_plan, entrance


# --- always-run -------------------------------------------------------------


def test_build_samples_is_deterministic_and_upstream_only():
    dsl, rp, en = _tiny_plan()
    a = production.build_samples(dsl, rp, en)
    b = production.build_samples(dsl, rp, en)
    assert a == b and a, a
    # presence dimension only; transform/camera/relation/temporal are separate dimensions
    presence = [s for s in a if s.get("probe") not in ("transform", "camera", "relation", "temporal")]
    ids = {s["id"] for s in presence}
    assert ids == {"t1", "d1"}
    # multiple times per element (progressive reveal must be sampled, not assumed)
    assert sum(1 for s in presence if s["id"] == "t1") >= 2
    # the camera dimension is expected for the beat too (independent expectation)
    assert any(s.get("probe") == "camera" for s in a)


def test_verify_pass_on_synthetic_paint():
    dsl, rp, en = _tiny_plan()
    samples = production.build_samples(dsl, rp, en)
    observed = _obs(samples, lambda s: 500)
    rep = production.verify(samples, observed)
    assert rep["verdict"] == "PASS", rep


def test_verify_render_fail_on_unpainted_content():
    dsl, rp, en = _tiny_plan()
    samples = production.build_samples(dsl, rp, en)
    observed = {"available": True, "backend": "x", "beats": 1,
                "samples": [{"id": s["id"], "t": s["t"], "present": s["present"],
                             "ink": 0} for s in samples]}
    rep = production.verify(samples, observed)
    assert rep["verdict"] == "RENDER_FAIL"
    assert any(p["kind"] == "element_not_painted" for p in rep["problems"])


def test_decor_unpainted_is_advisory_not_failure():
    dsl, rp, en = _tiny_plan()
    samples = production.build_samples(dsl, rp, en)
    observed = _obs(samples, lambda s: 500 if s["id"] == "t1" else 0)
    rep = production.verify(samples, observed)
    assert rep["verdict"] == "PASS", rep
    assert any(a["kind"] == "element_not_painted" for a in rep["advisory"])


def test_unavailable_observation_is_environment_fail_not_pass():
    dsl, rp, en = _tiny_plan()
    samples = production.build_samples(dsl, rp, en)
    rep = production.verify(samples, {"available": False, "samples": [],
                                      "error": "no functional browser"})
    assert rep["verdict"] == "ENVIRONMENT_FAIL"
    assert rep["verdict"] != "PASS"


# --- browser-gated ----------------------------------------------------------


@needs_browser
def test_production_chain_end_to_end(tmp_path):
    """SRT → ... → film/index.html → Chromium → production observer → verdict."""
    import pipeline

    out = str(tmp_path / "out")
    pipeline.run(GOLDEN, out, render_previews=False, log=lambda *a: None)
    film = os.path.join(out, "film", "index.html")
    assert os.path.exists(film), "production pipeline did not emit film/index.html"

    report = production.run(film, os.path.join(out, "work"))
    assert report["available"] is True, report
    assert report["verdict"] == "PASS", json.dumps(report, ensure_ascii=False)
    assert report["painted"] >= 1
