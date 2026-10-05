"""Canonical geometry / transform subsystem.

* :mod:`geometry.matrix` -- the single source of truth for 2D affine transforms
  and axis-aligned world boxes.
* :mod:`geometry.audit`  -- a divergence audit that measures how far the other
  subsystems' transform math drifts from the canonical algebra.
"""
from . import audit, matrix  # noqa: F401

__all__ = ["matrix", "audit"]
