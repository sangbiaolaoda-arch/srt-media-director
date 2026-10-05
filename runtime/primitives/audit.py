"""audit.py — primitive coverage / smoke audit (code-capability upgrade).

Answers "does the declared catalog match the code, and does every primitive
actually render?" Findings are evidence, not failures: too-thin areas and
undocumented helpers stay visible as quantified divergences.

Records::

    {"source": <module/member>, "case": <what>, "severity": <str>, "detail": ...}
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import catalog

_THIN_CATEGORY_LOC = 60  # a category below this many LOC is "thin"


def coverage() -> List[Dict[str, Any]]:
    """Per-category declared/actual member counts."""
    recs: List[Dict[str, Any]] = []
    for cat, declared_members in catalog.categories().items():
        actual = catalog.module_publics(cat)
        recs.append({"source": "primitives.%s" % cat, "case": "coverage",
                     "declared": len(declared_members), "actual": len(actual),
                     "members": declared_members, "severity": "ok"})
    return recs


def smoke() -> List[Dict[str, Any]]:
    """Call every declared primitive with its sample args; record ok/len/error."""
    recs: List[Dict[str, Any]] = []
    for name in catalog.declared():
        if catalog.sample(name) is None:
            recs.append({"source": "primitives.%s" % name, "case": "smoke",
                         "ok": False, "len": 0, "severity": "severe",
                         "detail": "no sample args declared"})
            continue
        try:
            svg = catalog.render(name)
            ok = isinstance(svg, str) and len(svg) > 0
            recs.append({"source": "primitives.%s" % name, "case": "smoke",
                         "ok": bool(ok), "len": len(svg) if isinstance(svg, str) else 0,
                         "severity": "ok" if ok else "severe",
                         "detail": "" if ok else "empty or non-str output"})
        except Exception as e:  # noqa: BLE001 - audit must not crash
            recs.append({"source": "primitives.%s" % name, "case": "smoke",
                         "ok": False, "len": 0, "severity": "severe",
                         "detail": repr(e)})
    return recs


def divergences() -> List[Dict[str, Any]]:
    """Undocumented helpers, declared-but-missing members, and failed smoke calls."""
    out: List[Dict[str, Any]] = []
    for name in catalog.undeclared():
        out.append({"source": name, "case": "undeclared", "severity": "material",
                    "detail": "exists in code but not in the catalog"})
    for name in catalog.missing():
        out.append({"source": name, "case": "missing", "severity": "severe",
                    "detail": "declared in the catalog but absent in code"})
    for rec in smoke():
        if rec["severity"] != "ok":
            out.append({"source": rec["source"], "case": "smoke_failed",
                        "severity": rec["severity"], "detail": rec.get("detail", "")})
    return out


def thin_categories() -> List[Dict[str, Any]]:
    """Categories whose declared member count is below the thin threshold."""
    return [{"source": "primitives.%s" % c, "case": "thin", "declared": len(m),
             "threshold": _THIN_CATEGORY_LOC, "severity": "material"}
            for c, m in catalog.categories().items() if len(m) < 3]


def summary() -> Dict[str, Any]:
    divs = divergences()
    return {"total_primitives": len(catalog.declared()),
            "categories": len(catalog.categories()),
            "divergences": len(divs),
            "severe": sum(1 for d in divs if d["severity"] == "severe"),
            "thin_categories": len(thin_categories())}
