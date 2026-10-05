"""procedural_canonical — the single source of truth for *procedural generation*.

PROCEDURAL NORMALIZATION · P1
-----------------------------
"Procedural" answers exactly two questions and nothing else:

* **what seed does this frame / beat use?**        -> :mod:`procedural_canonical.rng`
* **how does a count become a layout / lattice?**  -> :mod:`procedural_canonical.layout`

Everything a scene draws procedurally must be *reproducible*: the same inputs
must yield the same picture on every machine and every run. Before this package
the runtime hard-coded the video-level seed ``20261003`` in two separate
producers (``raster_renderer`` and ``visual_director``) and derived a per-beat
seed with an inline md5 recipe. That is two truths for "what seed does this
frame use" -- if they drift, the L3 raster probe and the HTML player render
different pictures while both still claim determinism. Likewise the "n columns
-> positions" rule lived in ``ref_frame.cols`` and the dot-lattice loops were
hand-rolled inside ``svg_art``.

This package owns ONE policy for each, so the claim "seeded, cross-machine
reproducible" has a single implementation to audit against.

What it deliberately does NOT own (no re-implementation of other truths)
-------------------------------------------------------------------------
* drawing / shapes / text / color  -> :mod:`primitives` (primitive_catalog.v1)
* time / easing                    -> :mod:`timeline` (easing_vocabulary.v1)
* space / transform / box          -> :mod:`geometry` (transform_vocabulary.v1)
* when a motion runs               -> :mod:`motion_canonical` (motion_semantics.v2)

Boundary guard
--------------
``ref_frame`` consumes this package (its ``cols``/``rows`` delegate here), so
this package must never import ``ref_frame`` -- that would be a cycle. More
generally it must stay dependency-free (stdlib only) so it can be a leaf that
everyone else builds on. ``assert_boundaries()`` verifies that at import time so
a future regression fails loudly instead of silently re-forking the seed policy.
"""
from __future__ import annotations

import os
import sys

# --- path bootstrap -------------------------------------------------------
# The runtime uses top-level imports (``import ref_frame``) with the ``runtime/``
# directory on ``sys.path``. Make this package self-sufficient under both import
# styles (``import procedural_canonical`` and ``from runtime.procedural_canonical``).
_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RUNTIME_DIR not in sys.path:
    sys.path.insert(0, _RUNTIME_DIR)

from . import rng, layout, audit  # noqa: E402,F401

__all__ = [
    "rng", "layout", "audit",
    "assert_boundaries", "boundary_report",
]

# The canonical procedural package must depend on nothing but the stdlib.
_FORBIDDEN_IMPORTS = (
    "ref_frame", "svg_art", "primitives", "geometry", "timeline",
    "motion_canonical", "motion", "motion_runtime", "scene",
    "visual_director", "raster_renderer", "html_adapter", "pipeline",
)


def boundary_report() -> dict:
    """Report whether canonical procedural accidentally imports a producer.

    Two independent checks:
      1. static scan of this package's own source for forbidden imports;
      2. a *clean interpreter* import of this package, then inspect that
         interpreter's ``sys.modules`` (a same-process check is unreliable
         because unrelated code may have imported those modules).
    """
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
                    static_hits.append({"file": fn, "line": lineno,
                                        "code": line.strip()})

    runtime_hits = []
    code = (
        "import sys; sys.path.insert(0, %r); import procedural_canonical; "
        "bad=[m for m in sys.modules if m in %r]; "
        "print('|'.join(sorted(set(bad))))" % (_RUNTIME_DIR, list(_FORBIDDEN_IMPORTS))
    )
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
        "owns": ["rng (seed policy)", "layout (slots/stacks/lattice)", "audit"],
        "must_never": [
            "re-implement drawing (use primitives.catalog)",
            "re-implement easing (use timeline.easing)",
            "re-implement transforms (use geometry)",
            "re-implement motion timing (use motion_canonical)",
        ],
    }


def assert_boundaries() -> None:
    """Raise if canonical procedural has pulled in a forbidden dependency."""
    report = boundary_report()
    if report["status"] != "PASS":
        raise AssertionError(
            "procedural_canonical must stay dependency-free (stdlib only): %s %s"
            % (report["static_forbidden_imports"], report["runtime_loaded_forbidden"]))
