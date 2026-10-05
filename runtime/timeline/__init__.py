"""Canonical timeline / easing subsystem.

* :mod:`timeline.easing`  -- the single source of truth for easing curves and the
  pure time-parameterization helper ``pr(t, start, end)``.
* :mod:`timeline.audit`   -- a divergence audit that measures how far the other
  subsystems' easing implementations drift from the canonical vocabulary.
"""
from . import audit, easing, legacy  # noqa: F401

__all__ = ["easing", "audit", "legacy"]
