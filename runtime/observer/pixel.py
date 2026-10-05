"""Pixel signal (Phase 0, step 9) — screenshot-backed evidence.

Structural observation (``browser.py``) recovers geometry from the DOM. That
alone can be fooled by a style rule that lays an element out but paints nothing.
The pixel signal is the independent second opinion: an actual screenshot of the
same page, reduced to a deterministic fingerprint plus per-region luminance and
contrast.

``structural`` and ``pixel`` signals therefore *coexist*: a node the DOM calls
visible but whose pixel region is uniform AND equals the page background is a
real contradiction and is reported as such. Pixel thresholds are their own
family (see ``thresholds``) and are never mixed with runtime thresholds.

No Playwright, no numpy: Chromium ``--screenshot`` + Pillow only.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from .browser import find_browser, available

GRID_W, GRID_H = 32, 18
LEVELS = 16  # quantize mean luminance into 16 buckets


def _luma(px: Tuple[int, int, int]) -> float:
    r, g, b = px[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def capture(html_path: str, png_path: str, *, width: int = 680, height: int = 382,
            timeout: int = 60) -> Dict[str, Any]:
    """Screenshot ``html_path`` via the Chromium CLI. Honest degradation."""
    binary = find_browser()
    if not binary or not available():
        return {"available": False, "png": None, "error": "no functional browser"}

    os.makedirs(os.path.dirname(os.path.abspath(png_path)), exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="pixel-")
    try:
        cmd = [
            binary, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            "--user-data-dir=" + os.path.join(tmpdir, "profile"),
            "--window-size=%d,%d" % (width, height),
            "--virtual-time-budget=2000",
            "--screenshot=" + os.path.abspath(png_path),
            "file://" + os.path.abspath(html_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"available": True, "png": None, "error": "screenshot timed out"}
        if not os.path.exists(png_path):
            return {"available": True, "png": None, "error": "screenshot not produced"}
        return {"available": True, "png": png_path, "backend": os.path.basename(binary)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def fingerprint(png_path: str, grid: Tuple[int, int] = (GRID_W, GRID_H)) -> Dict[str, Any]:
    """Deterministic perceptual fingerprint of an image.

    Downsample to a coarse grid of mean-luminance cells, quantize, then hash.
    Pure function of the image bytes -> no browser, unit-testable.
    """
    from PIL import Image

    with Image.open(png_path) as im:
        small = im.convert("L").resize(grid)
        cells = list(small.tobytes())
    step = 256 // LEVELS
    quant = [min(LEVELS - 1, c // step) for c in cells]
    canon = ",".join(str(q) for q in quant)
    return {
        "grid": [grid[0], grid[1]],
        "levels": LEVELS,
        "cells": quant,
        "hash": hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16],
    }


def _region_stats(im, box: Tuple[float, float, float, float]) -> Optional[Dict[str, float]]:
    """Mean and variance of a rectangular region, in luminance."""
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return None
    crop = im.crop((int(x), int(y), int(x + w), int(y + h)))
    if crop.width <= 0 or crop.height <= 0:
        return None
    data = list(crop.tobytes())
    if not data:
        return None
    mean = sum(data) / len(data)
    var = sum((v - mean) ** 2 for v in data) / len(data)
    return {"mean": round(mean, 3), "var": round(var, 3)}


def _border_luma(im, frac: float = 0.06) -> float:
    """Mean luminance of the image border band — a proxy for page background."""
    w, h = im.size
    bw = max(1, int(w * frac))
    bh = max(1, int(h * frac))
    vals: List[int] = []
    vals += list(im.crop((0, 0, w, bh)).tobytes())          # top
    vals += list(im.crop((0, h - bh, w, h)).tobytes())      # bottom
    vals += list(im.crop((0, 0, bw, h)).tobytes())          # left
    vals += list(im.crop((w - bw, 0, w, h)).tobytes())      # right
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def signal(html_path: str, observed: Dict[str, Any], *,
           width: int = 680, height: int = 382,
           png_path: Optional[str] = None,
           _png_override: Optional[str] = None) -> Dict[str, Any]:
    """Full pixel signal: screenshot + fingerprint + per-node region statistics.

    ``_png_override`` lets tests inject an image without a browser.
    """
    if _png_override is not None:
        png = _png_override
        cap = {"available": True, "png": png, "backend": "override"}
    else:
        png = png_path or os.path.join(tempfile.gettempdir(), "pixel_signal.png")
        cap = capture(html_path, png, width=width, height=height)
    if not cap.get("available") or not cap.get("png"):
        return {"available": False, "error": cap.get("error", "no screenshot"),
                "fingerprint": None, "regions": {}, "blank": None}

    from PIL import Image
    import statistics
    with Image.open(cap["png"]) as im:
        im = im.convert("L")
        regions: Dict[str, Optional[Dict[str, float]]] = {}
        for n in observed.get("nodes", []):
            regions[n["id"]] = _region_stats(im, (n["x"], n["y"], n["w"], n["h"]))
        background = _border_luma(im)
        data = list(im.tobytes())
        variance = statistics.pvariance(data) if len(data) > 1 else 0.0
        size = list(im.size)

    fp = fingerprint(cap["png"])
    return {
        "available": True,
        "backend": cap.get("backend"),
        "fingerprint": fp,
        "regions": regions,
        "background_luma": background,
        "variance": round(variance, 4),
        "blank": variance <= 0.0,
        "size": size,
    }


def fingerprint_distance(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Fraction of coarse cells whose quantized luminance differs.

    Pure function of two fingerprints -> browser-free, unit-testable. This is
    the *perceptual advisory* signal: it says "the picture looks different", not
    "the semantics are wrong" (§39). A stable render must keep it at zero.
    """
    ca, cb = a.get("cells", []), b.get("cells", [])
    if not ca or not cb or len(ca) != len(cb):
        return {"comparable": False, "drift_ratio": None, "changed_cells": None}
    changed = sum(1 for x, y in zip(ca, cb) if x != y)
    return {
        "comparable": True,
        "changed_cells": changed,
        "total_cells": len(ca),
        "drift_ratio": round(changed / len(ca), 4),
        "identical": changed == 0,
    }


def regression(baseline: Optional[Dict[str, Any]], current: Dict[str, Any],
               thr: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Pixel regression lane — has the rendered picture drifted (§38, §64 F).

    Compares a stored baseline fingerprint against a freshly captured one. Drift
    above ``pixel_drift_ratio_max`` is ``PERCEPTUAL_DRIFT``: a *perceptual*
    finding, explicitly NOT a semantic verdict (§37, §39).
    """
    from . import taxonomy
    thr = thr or {}
    max_ratio = float(thr.get("pixel_drift_ratio_max", 0.02))
    if not current.get("available", True):
        return {"status": "PIXEL_UNAVAILABLE", "available": False,
                "failure_class": taxonomy.ENVIRONMENT_FAIL,
                "fault_domain": taxonomy.fault_domain(taxonomy.ENVIRONMENT_FAIL),
                "drift_ratio": None, "problems": [
                    {"kind": "no_screenshot", "detail": current.get("error")}]}
    if baseline is None:
        return {"status": "NO_BASELINE", "available": True,
                "failure_class": taxonomy.PASS, "fault_domain": "none",
                "drift_ratio": None, "problems": [],
                "note": "no baseline fingerprint recorded"}
    dist = fingerprint_distance(baseline, current)
    if not dist["comparable"]:
        return {"status": "PIXEL_UNAVAILABLE", "available": True,
                "failure_class": taxonomy.ENVIRONMENT_FAIL, "fault_domain": "environment",
                "drift_ratio": None,
                "problems": [{"kind": "fingerprint_mismatch", "detail": "grid mismatch"}]}
    drift = not dist["identical"] and dist["drift_ratio"] > max_ratio
    return {
        "status": "PIXEL_DRIFT" if drift else "PIXEL_OK",
        "available": True,
        "failure_class": taxonomy.PERCEPTUAL_DRIFT if drift else taxonomy.PASS,
        "fault_domain": taxonomy.fault_domain(
            taxonomy.PERCEPTUAL_DRIFT if drift else taxonomy.PASS),
        "drift_ratio": dist["drift_ratio"],
        "max_drift_ratio": max_ratio,
        "problems": ([{"kind": "perceptual_drift",
                       "detail": {"ratio": dist["drift_ratio"],
                                  "changed_cells": dist["changed_cells"]}}]
                     if drift else []),
    }


def compare(observed: Dict[str, Any], pixel: Dict[str, Any],
            thr: Dict[str, Any], *, background_luma: Optional[float] = None) -> Dict[str, Any]:
    """Cross-check the structural observation against the pixel signal.

    Contradiction rules (Phase 0):
      * screenshot must not be blank when the DOM claims visible content;
      * a structurally-visible node is suspicious ONLY if its pixel region is
        BOTH close to the page background (mean delta < ``pixel_region_delta_min``)
        AND internally flat (variance < ``pixel_region_var_min``). A thin dark
        border around a white fill is low-delta but high-variance, so it is not
        a contradiction.
    """
    from . import taxonomy
    if not pixel.get("available"):
        return {"status": "PIXEL_UNAVAILABLE", "available": False, "problems": [],
                "failure_class": taxonomy.ENVIRONMENT_FAIL,
                "fault_domain": taxonomy.fault_domain(taxonomy.ENVIRONMENT_FAIL),
                "note": "no screenshot; pixel signal not evaluated (honest degradation)"}

    delta_min = float(thr.get("pixel_region_delta_min", 6.0))
    var_min = float(thr.get("pixel_variance_min", 1.0))
    region_var_min = float(thr.get("pixel_region_var_min", 4.0))
    problems: List[Tuple[str, Any]] = []

    bg = background_luma
    if bg is None:
        bg = pixel.get("background_luma", 0.0)

    visible_nodes = [n for n in observed.get("nodes", [])
                     if n.get("w", 0) > 0 and n.get("h", 0) > 0]
    if visible_nodes and pixel.get("variance", 0.0) < var_min:
        problems.append(("blank_screenshot", pixel.get("variance")))

    regions = pixel.get("regions", {})
    for n in visible_nodes:
        r = regions.get(n["id"])
        if r is None:
            problems.append(("pixel_region_unreadable", n["id"]))
            continue
        delta = abs(r["mean"] - bg)
        if delta < delta_min and r["var"] < region_var_min:
            problems.append(("pixel_region_matches_background",
                             (n["id"], round(r["mean"], 3), round(bg, 3), round(r["var"], 3))))

    # A structural-vs-pixel contradiction is a PERCEPTUAL finding; pixel is NOT
    # the semantic judge (§37, §39) — it flags "the picture disagrees with the DOM".
    verdict = taxonomy.PERCEPTUAL_DRIFT if problems else taxonomy.PASS
    return {
        "status": "PIXEL_OK" if not problems else "PIXEL_CONFLICT",
        "available": True,
        "failure_class": verdict,
        "fault_domain": taxonomy.fault_domain(verdict),
        "fingerprint_hash": (pixel.get("fingerprint") or {}).get("hash"),
        "background_luma": bg,
        "problems": [{"kind": k, "detail": d} for k, d in problems],
    }
