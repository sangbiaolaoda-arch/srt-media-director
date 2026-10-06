"""M3 P0 regression — bounded numeric labels must not overflow fixed text regions.

The real-content corpus case ``d01-gdp`` exposed a genuine production bug: the
``before_after`` delta annotation was built with ``"%g"``, whose 6-significant-
digit precision is unbounded in *length*.  ``after/before = 0.3088235…`` produced
the 8-glyph label ``×0.308824``, which measured wider (230px) than the fixed
``delta`` region (179px) at ``display_small`` and raised ``LayoutIntentIncomplete``.

The fix is generic (a shared bounded formatter), not a case-specific exception.
These tests lock the generic contract so any future label producer stays bounded.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from common import format_compact_num, measure_text  # noqa: E402
from composition_planner import FONT_SIZES, TEMPLATES  # noqa: E402

CANVAS_W = 1280
CASES = {
    "explanation": "tests/corpus/real-content/data_comparison/d01-gdp.srt",
}


def test_formatter_is_bounded():
    # never longer than a human legible label; the unbounded "%g" output was 8 chars
    assert len(format_compact_num(0.3088235294)) <= 4
    assert format_compact_num(0.3088235294) == "0.31"
    # integer-ish and small values keep their meaning
    assert format_compact_num(100.0) == "100"
    assert format_compact_num(6.8) == "6.8"
    # pathological / non-finite never explodes the length
    assert len(format_compact_num(float("inf"))) <= 4
    assert len(format_compact_num(float("nan"))) <= 4


def test_delta_label_fits_its_region():
    ds = FONT_SIZES["display_small"]
    region = TEMPLATES["before_after"]["delta"]
    region_w = region[2] * CANVAS_W
    label = "×" + format_compact_num(0.3088235294)      # the exact d01 ratio
    w, _h = measure_text(label, ds, bold=True)
    # planner adds padding; the producer must keep the label inside the region
    assert w + 12 <= region_w, (label, w, region_w)


def test_real_corpus_case_renders_without_layout_overflow():
    import pipeline
    import tempfile
    out = tempfile.mkdtemp(prefix="m3_regress_")
    report = pipeline.run(os.path.join(ROOT, CASES["explanation"]), out,
                          render_previews=False, log=lambda *a: None)
    assert report["status"] == "PASS"
