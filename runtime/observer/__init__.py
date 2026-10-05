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
from . import browser, fidelity, normalize, render

__all__ = ["browser", "normalize", "fidelity", "render"]
