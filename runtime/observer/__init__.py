"""Browser Observer (Phase 0, step 7).

Bridges the browser-free world-state core to a *real* browser engine, so the
loop can be grounded on observed reality rather than only on the runtime's own
claim.

Honesty rules (matching the repo's "有则用，无则明确降级"):
  * If no browser can be launched, :func:`browser.observe` returns
    ``available=False`` with empty observations. It never fabricates geometry.
  * It does not depend on Playwright. Any Chromium/Chrome binary (system, or a
    Playwright-downloaded build) is driven through the stable
    ``--headless --dump-dom`` CLI, which needs no Python browser bindings.
"""
import os as _os
import sys as _sys

# Allow `import observer` (or `python -m runtime.observer.*`) from anywhere to
# resolve the sibling `world_state` package regardless of cwd.
_rt = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _rt not in _sys.path:
    _sys.path.insert(0, _rt)

from . import browser, calibrate, camera, fidelity, normalize, pixel, relation, render, temporal, thresholds  # noqa: E402

__all__ = ["browser", "normalize", "fidelity", "render", "calibrate",
           "thresholds", "pixel", "camera", "relation", "temporal"]
