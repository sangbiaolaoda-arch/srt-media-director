"""capability_library — additive layout + motion capability catalogs.

This package is *additive*: it never mutates the existing director pipeline.
It exposes three catalogs used by the optional capability surfaces:

* :mod:`capability_library.layout_library`   — 110 composition blueprints
* :mod:`capability_library.entrance_library`  — 50 GSAP entrance specs
* :mod:`capability_library.relation_library`  — 50 GSAP relation specs
* :mod:`capability_library.gsap_emit`         — compile the catalog to a
  browser-ready GSAP bundle (``capability-library.gsap.js``).

Run ``python -m capability_library.gsap_emit --out <dir>`` to emit JSON + JS.
"""
from __future__ import annotations

from . import layout_library, entrance_library, relation_library

__all__ = ["layout_library", "entrance_library", "relation_library",
           "summary"]


def summary() -> dict:
    return {
        "layouts": layout_library.counts(),
        "entrances": len(entrance_library.all_entrances()),
        "relations": len(relation_library.all_relations()),
    }
