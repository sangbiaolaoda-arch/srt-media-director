"""motion_canonical — the single source of truth for *motion* in the runtime.

Normalization contract (MOTION UNIFICATION · P0)
------------------------------------------------
Motion answers exactly one question: **how does state change over time?**
It must NOT re-implement the other subsystems' truth:

* time / easing            -> delegated to :mod:`timeline` (single source of truth)
* space / transform / box  -> delegated to :mod:`geometry` (single source of truth)
* visual object identity   -> owned by :mod:`primitives` (catalog)

Every motion package that previously duplicated curve math, time math or matrix
math (``motion/``, ``motion_runtime/``, ``scene/``) converges here. The four-way
easing divergence (timeline / motion_runtime / motion / scene) collapses onto
:mod:`timeline.easing`.

Boundary guard
--------------
This package must never import the legacy motion packages. ``assert_boundaries()``
verifies that at import time so a future regression fails loudly instead of
silently re-forking the truth.

Observer independence
---------------------
``runtime/observer/*`` (and its projection contracts) is a *validator*, not a
producer. It stays independent and is deliberately NOT merged here: a validator
that reuses the producer's internals proves nothing.
"""
from __future__ import annotations

import os
import sys

# --- path bootstrap -------------------------------------------------------
# The runtime uses top-level package imports (``from timeline import easing``)
# with the ``runtime/`` directory on ``sys.path`` (see ``scene/scene_graph.py``).
# Make this package self-sufficient under both import styles
# (``import motion_canonical`` and ``from runtime.motion_canonical import ...``).
_RUNTIME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RUNTIME_DIR not in sys.path:
    sys.path.insert(0, _RUNTIME_DIR)

from . import easing, progress, transform  # noqa: E402,F401
from . import vocabulary, sequencing, transition, continuity, entrance, validate  # noqa: E402,F401

__all__ = [
    "easing", "progress", "transform",
    "vocabulary", "sequencing", "transition", "continuity", "entrance", "validate",
    "assert_boundaries", "boundary_report",
]

# Legacy packages that must never be imported by canonical motion.
_LEGACY_MOTION_PACKAGES = ("motion_runtime", "scene")


def boundary_report() -> dict:
    """Report whether canonical motion accidentally imports legacy producers.

    Two independent checks:
      1. static scan of this package's own source for forbidden imports;
      2. a *clean interpreter* import of this package, then inspect that
         interpreter's ``sys.modules`` (a same-process check is unreliable
         because unrelated code may have imported the legacy packages).
    """
    import re
    import subprocess

    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    # from/import motion_runtime | scene, or bare ``motion`` (but not motion_canonical)
    forbidden_pat = re.compile(
        r"^\s*from\s+(motion_runtime|scene)\b"
        r"|^\s*import\s+(motion_runtime|scene)\b"
        r"|^\s*from\s+motion\b(?!_canonical)"
        r"|^\s*import\s+motion\b(?!_canonical)")

    static_hits = []
    for fn in sorted(os.listdir(pkg_dir)):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(pkg_dir, fn), encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if forbidden_pat.match(line):
                    static_hits.append({"file": fn, "line": lineno,
                                        "code": line.strip()})

    runtime_hits = []
    code = (
        "import sys; sys.path.insert(0, %r); import motion_canonical; "
        "bad=[m for m in sys.modules if m=='motion_runtime' "
        "or m.startswith('motion_runtime.') or m=='scene' "
        "or m.startswith('scene.') or m=='motion' or m.startswith('motion.')]; "
        "print('|'.join(bad))" % _RUNTIME_DIR)
    try:
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=60)
        runtime_hits = [m for m in (out.stdout.strip().split("|")) if m]
    except Exception as exc:  # pragma: no cover
        runtime_hits = ["<subprocess-error:%s>" % exc]

    ok = not static_hits and not runtime_hits
    return {
        "status": "PASS" if ok else "FAIL",
        "static_forbidden_imports": static_hits,
        "runtime_loaded_legacy": runtime_hits,
        "legacy_motion_imported": sorted(set(runtime_hits)),
        "owns": ["easing(via timeline)", "progress(via timeline)",
                 "transform(via geometry)", "vocabulary", "sequencing",
                 "transition", "continuity", "entrance", "validate"],
    }


def assert_boundaries() -> None:
    """Raise if canonical motion has pulled in a legacy motion producer."""
    report = boundary_report()
    if report["status"] != "PASS":
        raise AssertionError(
            "motion_canonical must not import legacy motion producers: %s"
            % report["legacy_motion_imported"])
