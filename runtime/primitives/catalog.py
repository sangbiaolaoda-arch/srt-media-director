"""catalog.py — primitive catalog: the single source of truth for "what reusable parts exist".

``contracts/primitive_catalog.v1.json`` *declares* the inventory; this module
*introspects* the code and reconciles the two. A primitive added in code but not
declared (or declared but missing) becomes a visible divergence instead of an
undocumented helper. ``_SAMPLES`` gives every declared primitive callable sample
arguments so the audit can prove each one actually renders.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from . import chart, connector, motif, path, shape, text

_MODULES = {
    "shape": shape, "text": text, "path": path,
    "chart": chart, "connector": connector, "motif": motif,
}

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "primitive_catalog.v1.json")

# name -> (positional args, keyword args) used by the smoke audit
_SAMPLES: Dict[str, Any] = {
    "card": ((10, 10, 80, 40), {}),
    "dot": ((30, 30), {}),
    "bar": ((10, 100, 20, 40), {}),
    "track": ((10, 10, 100, 12), {}),
    "fill": ((10, 10, 100, 12), {}),
    "ring": ((30, 30, 20), {}),
    "title": (("标题",), {}),
    "caption": (("说明",), {}),
    "label": (("标签", 30, 30), {}),
    "badge": ((1, 30, 30), {}),
    "multiline": ((["a", "b"], 10, 10), {}),
    "line": ((0, 0, 10, 10), {}),
    "arrow": ((0, 20, 10), {}),
    "polyline": (([(0, 0), (10, 10)],), {}),
    "threshold": ((50, 0, 100), {}),
    "arc": ((30, 30, 20, 0, 180), {}),
    "accumulating_bars": ((10, 100), {}),
    "baseline": ((0, 100, 50), {}),
    "ticks": ((0, 100, 50), {}),
    "sparkline": (([1, 2, 3], 0, 0, 50, 20), {}),
    "elbow": ((0, 0, 50, 50), {}),
    "dashed": ((0, 0, 50, 50), {}),
    "relation_edges": (([{"from": "a", "to": "b"}], {"a": (0, 0), "b": (10, 10)}), {}),
    "bell": ((30, 30), {}),
    "focus_break": ((30, 30), {}),
    "bar_half": ((30, 30), {}),
    "door": ((30, 30), {}),
    "phone": ((30, 30), {}),
}


def load_contract(path: str = None) -> dict:
    with open(path or CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)


def categories() -> Dict[str, List[str]]:
    c = load_contract()["categories"]
    return {k: list(v["members"]) for k, v in c.items()}


def members(category: str) -> List[str]:
    return categories()[category]


def declared() -> List[str]:
    out: List[str] = []
    for ms in categories().values():
        out.extend(ms)
    return out


def get(name: str):
    """Return the callable for a primitive name, or None if unknown."""
    for mod in _MODULES.values():
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def helpers() -> List[str]:
    """Public functions that are helpers (registries/diagnostics), not primitives."""
    return list(load_contract().get("helpers_are_not_primitives", []))


def module_publics(category: str) -> List[str]:
    mod = _MODULES[category]
    h = set(helpers())
    return sorted(n for n, v in vars(mod).items()
                  if callable(v) and not n.startswith("_") and n not in h
                  and getattr(v, "__module__", "").endswith(category))


def sample(name: str):
    return _SAMPLES.get(name)


def render(name: str) -> str:
    """Render a primitive using its declared sample args (audit helper)."""
    args, kwargs = _SAMPLES[name]
    return get(name)(*args, **kwargs)


def render_all() -> Dict[str, str]:
    return {n: render(n) for n in declared()}


def undeclared() -> List[str]:
    """Public functions that exist in code but are not declared in the contract."""
    out: List[str] = []
    for cat in categories():
        for fn in module_publics(cat):
            if fn not in declared():
                out.append("%s.%s" % (cat, fn))
    return sorted(out)


def missing() -> List[str]:
    """Declared primitives with no callable in code."""
    return [n for n in declared() if get(n) is None]


def catalog() -> Dict[str, Any]:
    return {"contract": load_contract()["contract_id"],
            "categories": categories(),
            "count": len(declared())}
