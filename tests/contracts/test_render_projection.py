"""Render Projection Contract tests (Final Directive v5, §3-§5, §53).

These tests exercise the projection contract *without* the renderer. They prove
the expected projection is a real, declarative, auditable policy and that it is
an implementation independent of ``runtime/observer/render.py``.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler  # noqa: E402
from observer import projection  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _anchor(case="cause_effect"):
    import json
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


def test_contract_artifact_is_wellformed_and_traceable():
    c = projection.load_contract()
    assert c["contract_id"] == "render_projection.v1"
    assert c["layer"] == "RENDER_PROJECTION"
    assert c["provenance"]["reason"], "contract must state why it exists"
    assert c["provenance"]["author"]
    # priority order must lead with identity, not geometry (§5)
    assert c["projection"]["priority"][0] == "identity"


def test_expected_layout_is_declarative_slot_arithmetic():
    ws = compiler.compile_world_state(_anchor())
    order = projection.projection_order(ws)
    geo = projection.expected_layout(ws)
    c = projection.load_contract()
    ox, oy = c["projection"]["slot"]["origin"]
    sx, sy = c["projection"]["slot"]["step"]
    bw, bh = c["projection"]["slot"]["box"]
    for i, oid in enumerate(order):
        assert geo[oid] == {"x": ox + i * sx, "y": oy + i * sy, "w": bw, "h": bh}


def test_projection_order_is_first_focus_then_id():
    ws = compiler.compile_world_state(_anchor())
    order = projection.projection_order(ws)
    first_focus = {}
    for f in ws.frames:
        for oid, o in f.objects.items():
            if o.focus and oid not in first_focus:
                first_focus[oid] = f.t
    assert order == sorted(first_focus, key=lambda k: (first_focus[k], k))


def test_projection_module_does_not_import_renderer():
    """The projection must be an independent implementation (§1, §66)."""
    import ast
    path = os.path.join(ROOT, "runtime", "observer", "projection.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
            imported.update(a.name for a in node.names)
    assert "render" not in imported, imported


def test_structure_captures_identity_visibility_focus_relations():
    ws = compiler.compile_world_state(_anchor())
    st = projection.expected_structure(ws)
    rf = ws.frames[-1]
    assert st["ids"] == set(rf.objects.keys())
    assert st["focus"] == {oid for oid, o in rf.objects.items() if o.focus}
    assert st["edges"] == {(r.source, r.target, r.type) for r in rf.relations}
