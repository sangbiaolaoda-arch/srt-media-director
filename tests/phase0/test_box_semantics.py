"""Canonical box-semantics tests (code-capability upgrade).

Locks the single source of truth for box area/center/overlap, the
behavior-preserving adapters used by composition_planner and negative_space, and
the tracked divergence (planner's unclamped area) rather than a silent change.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from geometry import audit, box, legacy  # noqa: E402


# ------------------------------------------------------------------ canonical

def test_area_clamps_degenerate():
    assert box.area((0, 0, 10, 10)) == 100.0
    assert box.area((0, 0, -5, 4)) == 0.0


def test_area_unsafe_is_raw_product():
    assert box.area_unsafe((0, 0, -5, 4)) == -20.0


def test_center():
    assert box.center((10, 20, 4, 6)) == (12.0, 23.0)


def test_rect_from_norm():
    assert box.rect_from_norm((0.5, 0.5, 0.1, 0.2), 1000, 500) == (500.0, 250.0, 100.0, 100.0)


def test_overlaps_uses_strict_tolerance():
    assert box.overlaps((0, 0, 10, 10), (5, 5, 10, 10)) is True
    assert box.overlaps((0, 0, 10, 10), (10, 0, 10, 10)) is False  # edge touch
    assert box.overlaps((0, 0, 10, 10), (11, 0, 10, 10)) is False


def test_intersect_area():
    assert box.intersect_area((0, 0, 10, 10), (5, 5, 10, 10)) == 25.0


def test_bbox_of():
    assert box.bbox_of([(0, 0, 10, 10), (20, 5, 10, 10)]) == (0, 0, 30, 15)


# ---------------------------------------------------------------- adapters

def test_planner_rect_matches_manual():
    assert legacy.planner_rect((0.07, 0.125, 0.62, 0.095), 1280, 720) == \
        {"x": 0.07 * 1280, "y": 0.125 * 720, "w": 0.62 * 1280, "h": 0.095 * 720}


def test_planner_area_is_the_historical_unsafe_rule():
    assert legacy.planner_area({"x": 0, "y": 0, "w": 4, "h": 5}) == 20.0


def test_planner_intersect_matches_historical():
    a = {"x": 0, "y": 0, "w": 10, "h": 10}
    b = {"x": 5, "y": 5, "w": 10, "h": 10}
    edge = {"x": 10, "y": 0, "w": 10, "h": 10}
    assert legacy.planner_intersect(a, b) is True
    assert legacy.planner_intersect(a, edge) is False


def test_negspace_area_matches_historical():
    assert legacy.negspace_area([0, 0, 10, 10]) == 100.0
    assert legacy.negspace_area([0, 0, -5, 4]) == 0.0  # clamped
    assert legacy.negspace_area([]) == 0.0


# --------------------------------------------------------- call sites delegate

def test_composition_planner_delegates():
    import composition_planner as cp
    assert cp._area({"x": 0, "y": 0, "w": 4, "h": 5}) == legacy.planner_area({"x": 0, "y": 0, "w": 4, "h": 5})
    assert cp._center_of({"x": 10, "y": 20, "w": 4, "h": 6}) == legacy.planner_center({"x": 10, "y": 20, "w": 4, "h": 6})
    assert cp._rect((0.5, 0.5, 0.1, 0.1)) == legacy.planner_rect((0.5, 0.5, 0.1, 0.1), cp.W, cp.H)


def test_negative_space_delegates():
    from compiler import negative_space as ns
    assert ns._area([0, 0, 10, 10]) == legacy.negspace_area([0, 0, 10, 10])


# ---------------------------------------------------- divergence stays tracked

def test_box_divergence_is_quantified():
    recs = audit.audit_box_helpers()
    normal = [d for d in recs if d["case"] == "normal boxes"][0]
    degen = [d for d in recs if d["case"] == "degenerate box"][0]
    assert normal["severity"] == "match"
    assert degen["severity"] != "match"
    assert degen["max_delta"] > 0.0


def test_contract_loads():
    import json
    with open(os.path.join(ROOT, "contracts", "box_semantics.v1.json"), encoding="utf-8") as f:
        c = json.load(f)
    assert c["contract_id"] == "box_semantics.v1"
