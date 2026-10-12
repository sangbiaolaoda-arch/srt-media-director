"""tests/phase0/test_capability_library.py

Gates for the additive capability library (layouts / entrances / relations).

These tests are pure-data contracts; they do not touch the golden-hash pipeline.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_RUNTIME = os.path.join(_ROOT, "runtime")
for p in (_RUNTIME, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from capability_library import (  # noqa: E402
    entrance_library, layout_library, relation_library, gsap_emit, summary,
)


# ------------------------------------------------------------------- layouts
def test_layout_count_over_100():
    counts = layout_library.counts()
    assert counts["total"] >= 100, counts
    assert counts["text"] >= 30
    assert counts["image"] >= 25
    assert counts["chart"] >= 25


def test_layout_ids_unique():
    ids = layout_library.ids()
    assert len(ids) == len(set(ids))


def test_every_layout_passes_contract():
    bad = {}
    for l in layout_library.all_layouts():
        errs = layout_library.validate(l)
        if errs:
            bad[l["id"]] = errs
    assert not bad, bad


def test_layout_regions_within_canvas_and_safe_area():
    for l in layout_library.all_layouts():
        for slot, (x, y, w, h) in l["regions"].items():
            assert -1e-6 <= x and -1e-6 <= y, (l["id"], slot)
            assert x + w <= 1 + 1e-6 and y + h <= 1 + 1e-6, (l["id"], slot)


def test_layout_reading_order_matches_slots():
    for l in layout_library.all_layouts():
        assert set(l["reading_order"]) == set(l["regions"].keys()), l["id"]


def test_layout_by_kind_and_family():
    assert all(l["kind"] == "text" for l in layout_library.by_kind("text"))
    fam = layout_library.by_family("donut")
    assert len(fam) == 9


def test_layout_deterministic_across_imports():
    a = layout_library.counts()
    b = layout_library.counts()
    assert a == b


# ---------------------------------------------------------------- entrances
def test_entrance_count_is_50():
    assert len(entrance_library.all_entrances()) == 50


def test_entrance_ids_unique_and_all_valid():
    ids = entrance_library.ids()
    assert len(ids) == len(set(ids))
    bad = {e["id"]: entrance_library.validate(e)
           for e in entrance_library.all_entrances()
           if entrance_library.validate(e)}
    assert not bad, bad


def test_entrance_semantic_is_non_empty():
    for e in entrance_library.all_entrances():
        assert e["semantic"].strip(), e["id"]


def test_entrance_prop_pairs_match():
    for e in entrance_library.all_entrances():
        assert set(e["from"]) == set(e["to"]), e["id"]


# ---------------------------------------------------------------- relations
def test_relation_count_is_50():
    assert len(relation_library.all_relations()) == 50


def test_relation_ids_unique_and_all_valid():
    ids = relation_library.ids()
    assert len(ids) == len(set(ids))
    bad = {r["id"]: relation_library.validate(r)
           for r in relation_library.all_relations()
           if relation_library.validate(r)}
    assert not bad, bad


def test_relation_semantic_non_empty():
    for r in relation_library.all_relations():
        assert r["semantic"].strip(), r["id"]


# ---------------------------------------------------------------- emitter
def test_emitter_produces_all_artifacts(tmp_path):
    info = gsap_emit.emit(str(tmp_path))
    assert info["layouts"] >= 100
    assert info["entrances"] == 50
    assert info["relations"] == 50
    for name in info["files"]:
        path = os.path.join(str(tmp_path), name)
        assert os.path.getsize(path) > 0
    # JSON is loadable and round-trips
    with open(os.path.join(str(tmp_path), "capability-layouts.json"),
              encoding="utf-8") as fh:
        assert len(json.load(fh)) >= 100
    # JS bundle parses as text and exposes the namespace
    with open(os.path.join(str(tmp_path), "capability-library.gsap.js"),
              encoding="utf-8") as fh:
        js = fh.read()
    assert "CapabilityLibrary" in js
    assert "applyEntrance" in js and "runRelation" in js and "applyLayout" in js


def test_summary_matches_catalogs():
    s = summary()
    assert s["layouts"]["total"] >= 100
    assert s["entrances"] == 50
    assert s["relations"] == 50


def test_import_does_not_require_pil_or_renderer():
    # the catalog modules must be importable with stdlib only
    code = ("import sys;sys.path.insert(0,%r);"
            "from capability_library import layout_library,entrance_library,"
            "relation_library;print(layout_library.counts()['total'])"
            % _RUNTIME)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True)
    assert out.returncode == 0, out.stderr
    assert int(out.stdout.strip()) >= 100
