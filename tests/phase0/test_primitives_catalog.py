"""Primitive catalog tests (code-capability upgrade).

Locks the "declared catalog == code, every primitive renders" contract: the
catalog is the single source of truth for reusable parts, and drift (an
undocumented helper, a declared-but-missing member, a primitive that throws)
is surfaced rather than hidden.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from primitives import audit, catalog  # noqa: E402


def test_contract_loads():
    c = catalog.load_contract()
    assert c["contract_id"] == "primitive_catalog.v1"
    assert set(c["categories"]) == {"shape", "text", "path", "chart", "connector", "motif"}


def test_declared_members_all_exist_in_code():
    assert catalog.missing() == [], catalog.missing()


def test_no_undeclared_public_helpers():
    # every public primitive function is declared in the catalog
    # (registries/diagnostics are declared separately as non-primitive helpers)
    assert catalog.undeclared() == [], catalog.undeclared()


def test_every_primitive_renders_nonempty_svg():
    for rec in audit.smoke():
        assert rec["severity"] == "ok", rec
        assert rec["len"] > 0, rec


def test_catalog_has_no_divergences():
    assert audit.divergences() == [], audit.divergences()


def test_new_primitives_present_and_render():
    # the expansion added in this step
    for name in ("ring", "arc", "sparkline", "multiline"):
        assert catalog.get(name) is not None, name
        assert len(catalog.render(name)) > 0, name


def test_ring_and_arc_produce_expected_svg_shape():
    assert "<circle" in catalog.render("ring")
    assert "<path" in catalog.render("arc")


def test_sparkline_normalizes_into_box():
    svg = catalog.render("sparkline")
    assert "<polyline" in svg


def test_summary_counts():
    s = audit.summary()
    assert s["total_primitives"] == len(catalog.declared())
    assert s["severe"] == 0
    assert s["divergences"] == 0


# --- provenance: catalog is declared, not hardcoded in two places -----------

def test_categories_come_from_contract_file():
    assert os.path.exists(catalog.CONTRACT_PATH)
    assert catalog.categories()["motif"] == ["bell", "focus_break", "bar_half", "door", "phone"]
