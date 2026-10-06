"""Pytest harness over the runtime self-test gate registry.

Lets the same 25 gates run under pytest (in addition to
``python runtime/self_test.py``).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"))

import pytest  # noqa: E402
import gates  # noqa: E402

_GATES = gates.ordered_gates()


@pytest.mark.parametrize("name,fn", _GATES, ids=[n for n, _ in _GATES])
def test_gate(name, fn):
    fn()
