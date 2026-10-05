import os as _os
import sys as _sys

# Allow `import repair` (or `python -m runtime.repair.*`) from anywhere to
# resolve the sibling `world_state` package regardless of cwd.
_rt = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _rt not in _sys.path:
    _sys.path.insert(0, _rt)

from . import repair as repair  # noqa: E402

__all__ = ["repair"]
