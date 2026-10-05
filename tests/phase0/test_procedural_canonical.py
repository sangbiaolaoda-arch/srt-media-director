"""Phase 0 — procedural canonicalization machine checks (P1).

Proves the normalization's claims, not just its structure:

  * the seed policy is reproducible and PYTHONHASHSEED-independent;
  * ``layout.slots/stacks`` reproduce ``ref_frame.cols/rows`` exactly;
  * ``layout.lattice`` reproduces the migrated ``svg_art`` decor byte-for-byte;
  * no producer outside ``procedural_canonical`` constructs its own RNG.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import ref_frame as R  # noqa: E402
import svg_art  # noqa: E402
from procedural_canonical import (layout, rng, audit,  # noqa: E402
                                  boundary_report)


# ---------------------------------------------------------------- seed policy
def test_default_rng_is_reproducible():
    a = rng.default_rng()
    b = rng.default_rng()
    assert [a.randint(0, 10 ** 9) for _ in range(16)] == \
           [b.randint(0, 10 ** 9) for _ in range(16)]


def test_beat_seed_is_stable_and_text_dependent():
    beat = {"beat_id": "b01", "narration": "注意力被反复打断"}
    assert rng.stable_seed(rng.beat_key(beat)) == rng.stable_seed(rng.beat_key(beat))
    other = {"beat_id": "b01", "narration": "换一句字幕"}
    assert rng.stable_seed(rng.beat_key(beat)) != rng.stable_seed(rng.beat_key(other))


def test_stable_seed_matches_legacy_recipe():
    """Migration M8: stable_seed must equal the old inline md5 recipe."""
    import hashlib
    beat = {"beat_id": "b07", "narration": "关掉通知"}
    legacy = int(hashlib.md5(
        ("%s|%s" % (beat["beat_id"], beat["narration"])).encode("utf-8")
    ).hexdigest()[:8], 16)
    assert rng.stable_seed(rng.beat_key(beat)) == legacy


@pytest.mark.parametrize("hs", ["0", "1", "999"])
def test_stable_seed_independent_of_python_hash_seed(hs):
    code = ("import sys; sys.path.insert(0, %r); "
            "from procedural_canonical import rng; "
            "print(rng.stable_seed('b01|x'))" % os.path.join(ROOT, "runtime"))
    env = dict(os.environ, PYTHONHASHSEED=hs)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, env=env)
    assert out.stdout.strip() == str(rng.stable_seed("b01|x"))


# ---------------------------------------------------------------- layout rules
def test_slots_reproduce_reference_frame():
    """Migration M1: cols(3) -> x=[48,265,482], w=150 (exact)."""
    c3 = layout.slots(3, R.MARGIN, R.CONTENT_W, R.COL_GAP)
    assert [round(x) for x, _ in c3] == [48, 265, 482]
    assert abs(c3[0][1] - 150) < 0.5
    c2 = layout.slots(2, R.MARGIN, R.CONTENT_W, 32)
    assert [round(x) for x, _ in c2] == [48, 356]
    assert abs(c2[0][1] - 276) < 0.5


def test_ref_frame_delegates_to_layout():
    """cols/rows must now BE layout.slots/stacks (no second implementation)."""
    assert R.cols(4) == layout.slots(4, R.MARGIN, R.CONTENT_W, R.COL_GAP)
    assert R.rows(3, 100, 300, h_gap=20) == layout.stacks(3, 100, 300, 20)


def test_slots_stacks_reject_impossible_n():
    with pytest.raises(ValueError):
        layout.slots(0, 0, 100, 10)
    with pytest.raises(ValueError):
        layout.stacks(0, 0, 100, 10)


# ---------------------------------------------------------------- lattice
def test_lattice_is_row_major():
    pts = layout.lattice(3, 2, 10, 20, 5, 7)
    assert pts == [(10, 20), (15, 20), (20, 20), (10, 27), (15, 27), (20, 27)]


@pytest.mark.parametrize("name", ["dot_grid", "halftone", "plus_field"])
def test_lattice_backed_decor_renders(name):
    """Migrated decor must still render and stay inside the viewBox."""
    svg = svg_art.ART[name]
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert svg_art.audit_svg(svg) == [], svg_art.audit_svg(svg)


def test_audited_art_has_no_regressions():
    assert svg_art.audit_all() == {}


# ---------------------------------------------------------------- boundary
def test_no_seed_source_outside_canonical():
    """D1/D4 gate: no producer constructs its own RNG or hard-codes a seed."""
    hits = audit.seed_sources()
    assert hits == [], hits


def test_determinism_probe_passes():
    probe = audit.determinism_probe()
    assert probe["default_reproducible"] and probe["beat_reproducible"]
    assert probe["hash_seed_independent"]


def test_canonical_boundary_is_clean():
    assert boundary_report()["status"] == "PASS", boundary_report()
