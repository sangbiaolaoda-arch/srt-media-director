"""Runtime self-test gates, split by concern (entry: runtime/self_test.py)."""
from gate_lib import GATES, gate, ordered_gates, run_all  # noqa: F401
from gates import (  # noqa: F401
    aesthetic,
    architecture,
    beats,
    composition,
    contracts,
    director,
    entrance,
    grammar,
    motion,
    pipeline,
    procedural,
    render,
    repair,
    style,
)

__all__ = ["GATES", "gate", "ordered_gates", "run_all"]
