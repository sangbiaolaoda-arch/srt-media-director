"""aesthetic_canonical — the single source of truth for *post-process grading*.

AESTHETIC NORMALIZATION · P2
----------------------------
The grade is what turns a finished frame into a *look*: background gradient,
radial vignette, film grain, letterbox bars. The numbers already live in one
place (``common.THEME``), but the **code** did not: ``raster_renderer`` (PIL) and
``html_adapter`` (canvas JS) each implemented the grade, with two different
vignette falloff models and an inner ratio ``0.45`` hardcoded only in the JS. If
either surface is tuned, the raster reference and the HTML player silently
diverge while both still claim "cinematic".

This package owns ONE model (see :mod:`aesthetic_canonical.grade`) and the
parameters that feed it. Both surfaces read from here.

What it deliberately does NOT own
---------------------------------
* timing      -> :mod:`motion_canonical` (motion_semantics.v2)
* space       -> :mod:`geometry` (transform_vocabulary.v1)
* time        -> :mod:`timeline` (easing_vocabulary.v1)
* objects     -> :mod:`primitives` (primitive_catalog.v1)
* generation  -> :mod:`procedural_canonical` (procedural_semantics.v1)
* luminance   -> :mod:`observer.pixel` keeps its own ``_luma`` (the observer
                measures the picture; it must not inherit the producer's model)

Boundary guard
--------------
This is a leaf that takes the theme mapping as an argument. It must not import a
renderer or the observer. ``assert_boundaries()`` enforces that at import time.
"""
from __future__ import annotations

import os
import sys

_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RUNTIME_DIR not in sys.path:
    sys.path.insert(0, _RUNTIME_DIR)

from . import grade, audit  # noqa: E402,F401

__all__ = ["grade", "audit", "assert_boundaries", "boundary_report"]

_FORBIDDEN_IMPORTS = (
    "raster_renderer", "html_adapter", "observer", "pipeline", "visual_director",
    "ref_frame", "svg_art", "motion_canonical", "geometry", "timeline",
    "primitives", "procedural_canonical", "render_video",
)


def boundary_report() -> dict:
    """Report whether canonical aesthetic accidentally imports a surface."""
    import re
    import subprocess

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    pat = re.compile(r"^\s*(?:from|import)\s+(%s)\b" % "|".join(_FORBIDDEN_IMPORTS))
    static_hits = []
    for fn in sorted(os.listdir(pkg_dir)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(pkg_dir, fn), encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if pat.match(line):
                    static_hits.append({"file": fn, "line": lineno, "code": line.strip()})

    runtime_hits = []
    code = ("import sys; sys.path.insert(0, %r); import aesthetic_canonical; "
            "print('|'.join(sorted({m for m in sys.modules if m in %r})))"
            % (_RUNTIME_DIR, list(_FORBIDDEN_IMPORTS)))
    try:
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=60)
        runtime_hits = [m for m in out.stdout.strip().split("|") if m]
    except Exception as exc:  # pragma: no cover
        runtime_hits = ["<subprocess-error:%s>" % exc]

    ok = not static_hits and not runtime_hits
    return {
        "status": "PASS" if ok else "FAIL",
        "static_forbidden_imports": static_hits,
        "runtime_loaded_forbidden": runtime_hits,
        "owns": ["grade (vignette/letterbox/grain/gradient model + params)"],
        "must_never": [
            "hardcode a grade literal in a renderer",
            "inherit the observer's luminance model",
            "re-implement timing/space/time/objects/generation",
        ],
    }


def assert_boundaries() -> None:
    report = boundary_report()
    if report["status"] != "PASS":
        raise AssertionError("aesthetic_canonical must stay a leaf: %s %s"
                             % (report["static_forbidden_imports"],
                                report["runtime_loaded_forbidden"]))
