"""Behavior-preserving geometry migration tests (code-capability upgrade).

These tests lock the contract of the migration: after ``scene.scene_graph`` is
pointed at ``geometry.legacy``, every world box / origin / scale it produces must
be **exactly** what it produced before (golden frames depend on it). They also
assert the second half: the duplicated math is gone (call sites delegate), and
the deliberate semantic difference (rotation handling) stays a separately
tracked, quantified divergence rather than being silently applied.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from geometry import audit, legacy  # noqa: E402


def _build():
    # import lazily so path shim above applies
    from scene.scene_graph import SceneGraph
    g = SceneGraph("scene")
    g.add("scene", "group", x=100.0, y=50.0, scale=1.5, w=40.0, h=20.0)
    g.add("group", "child", x=10.0, y=5.0, scale=2.0, w=8.0, h=6.0)
    return g


# --- adapter reproduces the historical scalar math exactly --------------------

def test_scene_adapter_world_scale_matches_chain_product():
    g = _build()
    child = g.get("child")
    assert legacy.scene_world_scale(child) == pytest.approx(3.0)
    assert legacy.scene_world_scale(g.get("group")) == pytest.approx(1.5)


def test_scene_adapter_world_origin_matches_manual():
    g = _build()
    child = g.get("child")
    # group origin = (100,50); child offsets by group world scale (1.5)
    ox, oy = legacy.scene_world_origin(child)
    assert (ox, oy) == pytest.approx((100.0 + 10.0 * 1.5, 50.0 + 5.0 * 1.5))


def test_scene_adapter_world_box_matches_manual():
    g = _build()
    child = g.get("child")
    assert legacy.scene_world_box(child) == pytest.approx(
        [115.0, 57.5, 8.0 * 3.0, 6.0 * 3.0])


# --- the migrated call sites really delegate (no duplicated math) ------------

def test_scene_graph_methods_delegate_to_adapter():
    g = _build()
    child = g.get("child")
    assert child.world_scale() == pytest.approx(legacy.scene_world_scale(child))
    assert child.world_origin() == pytest.approx(legacy.scene_world_origin(child))
    assert child.world_box() == pytest.approx(legacy.scene_world_box(child))
    # center is defined from world_box, so it follows too
    assert child.world_center() == pytest.approx(legacy.scene_world_center(child))


def test_scene_graph_box_is_rotation_blind_like_before():
    from scene.scene_graph import SceneGraph
    g = SceneGraph("scene")
    g.add("scene", "a", x=0.0, y=0.0, rotation=45.0, scale=1.0, w=10.0, h=10.0)
    # historical behavior: rotation ignored -> box unchanged by rotation
    assert g.get("a").world_box() == pytest.approx([0.0, 0.0, 10.0, 10.0])


# --- divergence is tracked, not silently "fixed" -----------------------------

def test_rotation_divergence_stays_quantified():
    recs = audit.audit_scene_graph()
    rot = [d for d in recs if d.get("case") == "rotated parent chain"][0]
    assert rot["severity"] in ("material", "severe")
    assert rot["max_delta"] > 20.0


def test_no_rotation_still_matches_canonical():
    recs = audit.audit_scene_graph()
    plain = [d for d in recs if d.get("case") == "translate+scale (no rotation)"][0]
    assert plain["severity"] == "match"
