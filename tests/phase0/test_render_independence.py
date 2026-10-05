"""Final Directive v5 §66 — prove the verifier does not share the renderer's blind spot.

Experiment E (§64): correct WorldState + a *corrupted renderer* => RENDER_FAIL.
Experiment H (§64): the renderer's layout algorithm is deliberately broken; the
validator must STILL catch the error. If fidelity stayed green under a corrupted
renderer, the system would be "setting its own exam and grading itself".

The strongest assertion here: monkeypatch ``render``'s layout decision source to
something wrong/raising, and confirm ``fidelity`` is completely unaffected because
it now judges against the independent Render Projection Contract.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from observer import browser, fidelity, projection, render  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _anchor(case="cause_effect"):
    import json
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def _faithful_observation(ws):
    """An observation as a *faithful* renderer of the projection would produce."""
    geo = projection.expected_layout(ws)
    rf = ws.frames[-1]
    nodes = []
    for oid in sorted(geo):
        obj = rf.objects.get(oid)
        nodes.append({
            "id": oid, "x": geo[oid]["x"], "y": geo[oid]["y"],
            "w": geo[oid]["w"], "h": geo[oid]["h"], "opacity": 1,
            "visibility": "visible" if (obj is None or obj.visible) else "hidden",
            "display": "block", "focus": bool(obj and obj.focus),
        })
    edges = [{"source": r.source, "target": r.target, "type": r.type,
              "phase": r.phase} for r in rf.relations]
    return {"available": True, "backend": "synthetic", "nodes": nodes, "edges": edges}


# --- Experiment H: sabotage the renderer's shared decision source -------------


def test_sabotaging_renderer_layout_does_not_move_the_validator(monkeypatch):
    """H: break render.layout_geometry; the validator must be unaffected."""
    ws = compiler.compile_world_state(_anchor())

    def sabotaged(order):  # the bug that used to fool both sides (§66)
        return {oid: {"x": 9999, "y": 9999, "w": 1, "h": 1} for oid in order}

    monkeypatch.setattr(render, "layout_geometry", sabotaged)
    rep = fidelity.compare(ws, _faithful_observation(ws))
    # validator judges the observation, NOT the renderer -> still OK
    assert rep["status"] == "FIDELITY_OK", rep
    assert rep["failure_class"] == "PASS"


def test_validator_survives_renderer_module_exploding(monkeypatch):
    """Even if the renderer's layout source raises, fidelity still works."""
    ws = compiler.compile_world_state(_anchor())

    def boom(order):
        raise RuntimeError("renderer sabotaged")

    monkeypatch.setattr(render, "layout_geometry", boom)
    rep = fidelity.compare(ws, _faithful_observation(ws))
    assert rep["status"] == "FIDELITY_OK", rep


def test_projection_layout_differs_when_renderer_is_redefined(monkeypatch):
    """projection is the source of truth, independent of renderer constants."""
    ws = compiler.compile_world_state(_anchor())
    before = projection.expected_layout(ws)
    monkeypatch.setattr(render, "_DX", 4242)  # corrupt the renderer's spacing
    after = projection.expected_layout(ws)
    assert before == after, "projection must not read renderer internals"


# --- Experiment E: corrupted renderer is caught as RENDER_FAIL ----------------


def test_corrupted_renderer_produces_render_fail():
    """E: world state is correct, but the renderer drew wrong geometry."""
    ws = compiler.compile_world_state(_anchor())
    obs = _faithful_observation(ws)
    for n in obs["nodes"]:  # renderer fault: shift every box (§41 x += 40)
        n["x"] += 40
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "FIDELITY_FAIL"
    assert rep["failure_class"] == "RENDER_FAIL"
    assert any(p["kind"] == "geometry_out_of_tolerance" for p in rep["problems"])


def test_faithful_renderer_is_fidelity_ok():
    """Sanity: a faithful renderer passes the independent projection."""
    ws = compiler.compile_world_state(_anchor())
    rep = fidelity.compare(ws, _faithful_observation(ws))
    assert rep["status"] == "FIDELITY_OK"
    assert rep["failure_class"] == "PASS"


# --- Real end-to-end proof with a real browser (Experiment E, live) ------------

needs_browser = pytest.mark.skipif(not browser.available(),
                                   reason="no functional browser")


@needs_browser
def test_live_corrupted_renderer_is_caught_end_to_end(tmp_path, monkeypatch):
    """§66 live proof: corrupt the renderer's real layout, then render + observe.

    The browser observes what the corrupted renderer actually drew; the validator
    (using the independent projection) must flag RENDER_FAIL. This is the
    experiment that decides whether the verification architecture actually holds.
    """
    ws = compiler.compile_world_state(_anchor())
    monkeypatch.setattr(render, "_DX", 4242)  # renderer now draws wrong spacing
    html = render.render_world_state(ws, str(tmp_path / "corrupt.html"))
    obs = browser.observe(html)
    assert obs["available"] and obs["nodes"], obs
    rep = fidelity.compare(ws, obs)
    assert rep["status"] == "FIDELITY_FAIL", rep
    assert rep["failure_class"] == "RENDER_FAIL"
    assert any(p["kind"] == "geometry_out_of_tolerance" for p in rep["problems"])
