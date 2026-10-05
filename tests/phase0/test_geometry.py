"""Canonical geometry / transform tests (code-capability upgrade).

Locks the canonical affine algebra and the divergence audit: the two scene
systems agree without rotation, and scene.scene_graph drifts (rotation ignored)
once a node is rotated. The divergence is *tracked*, not silently "fixed".
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from geometry import audit, matrix  # noqa: E402


# ------------------------------------------------------------------ algebra

def test_identity_and_apply():
    assert matrix.mat_apply(matrix.IDENTITY, 3.0, 4.0) == (3.0, 4.0)


def test_translation_only_box():
    b = matrix.world_box(matrix.mat_from_parts(10.0, 20.0), 4.0, 6.0)
    assert b == (10.0, 20.0, 4.0, 6.0)


def test_rotation_90_maps_axes():
    x, y = matrix.mat_apply(matrix.mat_rotate(90.0), 1.0, 0.0)
    assert abs(x - 0.0) < 1e-9 and abs(y - 1.0) < 1e-9


def test_world_box_is_rotation_aware():
    b = matrix.world_box(matrix.mat_rotate(45.0), 10.0, 10.0)
    assert abs(b[2] - 10.0 * math.sqrt(2.0)) < 1e-6
    assert abs(b[3] - 10.0 * math.sqrt(2.0)) < 1e-6


def test_local_from_parts_matches_t_r_s():
    got = matrix.mat_from_parts(5.0, 7.0, 30.0, 2.0)
    expected = matrix.compose(matrix.mat_translate(5.0, 7.0),
                              matrix.mat_rotate(30.0),
                              matrix.mat_scale(2.0))
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, expected))


def test_compose_order_applies_rightmost_first():
    m = matrix.compose(matrix.mat_translate(10.0, 0.0), matrix.mat_rotate(90.0))
    x, y = matrix.mat_apply(m, 1.0, 0.0)  # rotate -> (0,1), then translate
    assert abs(x - 10.0) < 1e-9 and abs(y - 1.0) < 1e-9


def test_invert_roundtrip():
    m = matrix.mat_from_parts(5.0, 7.0, 33.0, 1.7)
    back = matrix.mat_mul(m, matrix.mat_invert(m))
    x, y = matrix.mat_apply(back, 3.0, 4.0)
    assert abs(x - 3.0) < 1e-9 and abs(y - 4.0) < 1e-9


# --------------------------------------------------------------- divergence


def _by_case(recs, case):
    for d in recs:
        if d.get("case") == case:
            return d
    raise AssertionError("missing case %r in %r" % (case, recs))


def test_motion_runtime_scene_matches_canonical():
    for d in audit.audit_motion_runtime_scene():
        assert d.get("severity") == "match", d


def test_scene_graph_matches_without_rotation():
    d = _by_case(audit.audit_scene_graph(), "translate+scale (no rotation)")
    assert d["severity"] == "match", d


def test_scene_graph_diverges_under_rotation():
    d = _by_case(audit.audit_scene_graph(), "rotated parent chain")
    assert d["severity"] in ("material", "severe"), d
    assert d["max_delta"] > 20.0, d


def test_divergence_is_tracked_not_silently_fixed():
    div = audit.diverging()
    assert any(x.get("source") == "scene.scene_graph.world_box" for x in div)


def test_contract_loads():
    c = matrix.load_contract()
    assert c["contract_id"] == "transform_vocabulary.v1"
    assert c["model"]["identity"] == [1, 0, 0, 1, 0, 0]
