"""audit.py — aesthetic divergences as measured evidence.

Two questions, both answerable from code:

  1. **do both surfaces consume the canonical grade?** (raster_renderer and
     html_adapter must import ``aesthetic_canonical.grade``.)
  2. **does any renderer still hardcode a grade literal?** (a vignette inner
     ratio ``r*0.XX`` in JS, or a letterbox formula computed locally, is a
     second, undocumented grade policy.)
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

# r*0.45 style hardcoded vignette inner ratio in JS.
_HARDCODED_VIGN_INNER = re.compile(r"createRadialGradient\([^)]*\*\s*0\.\d+\s*,")
# A local letterbox computation (should be grade.letterbox_px).
_LOCAL_LETTERBOX = re.compile(r"round\(\s*H\s*\*\s*THEME\[?\.?\"?letterbox")

_CONSUMER = "aesthetic_canonical"


def grade_consumers(runtime_dir: str = None) -> List[str]:
    """Modules that import the canonical grade (should include both surfaces)."""
    if runtime_dir is None:
        runtime_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = []
    for root, _dirs, files in os.walk(runtime_dir):
        if "__pycache__" in root or os.path.basename(root) == "aesthetic_canonical":
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            if _CONSUMER in src:
                found.append(os.path.relpath(path, runtime_dir))
    return sorted(found)


def hardcoded_grade_literals(runtime_dir: str = None) -> List[Dict[str, Any]]:
    """Renderers that still hardcode a grade literal instead of reading canonical."""
    if runtime_dir is None:
        runtime_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits: List[Dict[str, Any]] = []
    for root, _dirs, files in os.walk(runtime_dir):
        if "__pycache__" in root or os.path.basename(root) == "aesthetic_canonical":
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if _HARDCODED_VIGN_INNER.search(line) or _LOCAL_LETTERBOX.search(line):
                        hits.append({"file": os.path.relpath(path, runtime_dir),
                                     "line": lineno, "code": line.strip()})
    return hits


def divergence() -> Dict[str, Any]:
    consumers = grade_consumers()
    hard = hardcoded_grade_literals()
    return {
        "consumers": consumers,
        "both_surfaces_consume": ("raster_renderer.py" in consumers
                                  and "html_adapter.py" in consumers),
        "hardcoded_grade_literals": hard,
    }
