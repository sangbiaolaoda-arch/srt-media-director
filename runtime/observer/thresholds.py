"""Render Fidelity thresholds (Phase 0, step 8).

Fidelity thresholds must be *measured*, not guessed. They are also **browser**
thresholds and must never be mixed with runtime thresholds (Falsifiability
First v4). This module holds:

  * documented defaults (what we use until a calibration artifact exists), and
  * a loader for a calibrated artifact produced by :mod:`calibrate`.

The effective threshold set is always explicit about its provenance
(``source: default`` vs ``source: calibrated``) and the sample size ``n`` it
was derived from, so no calibrated number can masquerade as ground truth.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
CALIBRATED_PATH = os.path.join(_HERE, "browser_thresholds.v1.json")

# Documented defaults. Conservative on purpose: until measured, tolerate 1px of
# engine rounding and require any real area / non-trivial opacity for "visible".
_DEFAULT: Dict[str, Any] = {
    "version": "1",
    "source": "default",
    "n": 0,
    "geometry_tol_px": 1.0,
    "area_min_px2": 1.0,
    "opacity_min": 0.01,
    "p99_geometry_delta_px": None,
    "max_geometry_delta_px": None,
}


def default() -> Dict[str, Any]:
    return dict(_DEFAULT)


def calibrated_path() -> str:
    return CALIBRATED_PATH


def load_calibrated(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    p = path or CALIBRATED_PATH
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def effective(path: Optional[str] = None) -> Dict[str, Any]:
    """Calibrated thresholds if present, else documented defaults."""
    cal = load_calibrated(path)
    return cal if cal is not None else default()


def save(thresholds: Dict[str, Any], path: Optional[str] = None) -> str:
    p = path or CALIBRATED_PATH
    with open(p, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return p
