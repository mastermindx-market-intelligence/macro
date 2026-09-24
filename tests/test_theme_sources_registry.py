"""The theme source-family rights registry is the SOLE rights authority (plan §9.4).

Ship note (2026-08-15): docs-only and empty commits do not re-trigger the PR packs on
this repo — re-triggers must touch a watched path, which is why this file carries the
ship-chain timestamp line below.

These tests pin the registry's shape, not its verdicts: an operator resolving
`finviz_themes` to `derived_display_ok` should touch nothing here. What may never
happen silently is (a) a family appearing in the store without a registry row —
the guard owns that, fail-closed — (b) an enum value the emission gate does not
understand, or (c) the F20 grandfather list growing without a review row, which
would turn a content-scoped exemption back into the lineage-scoped one the
adversarial review rejected.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "config" / "theme_sources.yml"

RIGHTS_CLASSES = {"internal_only", "derived_display_ok", "direct_display_ok", "unresolved"}
AUTH_CLASSES = {"house", "keyless_public", "receipted_scrape", "entitled", "licensed"}


def _doc() -> dict:
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def test_registry_parses_with_version_and_families():
    doc = _doc()
    assert doc["version"] == 1
    assert isinstance(doc["families"], dict) and doc["families"]


def test_w3a_families_present_with_lawful_enums():
    fams = _doc()["families"]
    for required in ("mastermind_curated", "finviz_themes", "ths_concepts"):
        assert required in fams, f"family {required!r} missing — the guard fails closed on it"
    for name, row in fams.items():
        assert row["rights_class"] in RIGHTS_CLASSES, (name, row.get("rights_class"))
        assert row["auth_class"] in AUTH_CLASSES, (name, row.get("auth_class"))
        assert row.get("source_route"), name


def test_every_family_row_carries_a_review_record():
    for name, row in _doc()["families"].items():
        review = row.get("review")
        assert isinstance(review, dict), f"{name}: rights are stated, never assumed — review row required"
        for field in ("date", "by", "outcome"):
            assert review.get(field), f"{name}: review.{field} missing"


def test_grandfather_list_is_path_scoped_with_review_rows():
    """F20: the exemption is an enumerated path list; every entry carries its review.

    Growing this list without a review row is the lineage-scoped grandfather the
    plan §9.4 rejected — this test makes that growth loud.
    """
    doc = _doc()
    surfaces = doc.get("grandfathered_surfaces", [])
    assert isinstance(surfaces, list)
    fams = set(doc["families"])
    seen_paths: set[str] = set()
    for entry in surfaces:
        path = entry.get("path")
        assert path and isinstance(path, str), entry
        assert path not in seen_paths, f"duplicate grandfather entry {path!r}"
        seen_paths.add(path)
        assert entry.get("family") in fams, f"{path}: unknown family {entry.get('family')!r}"
        review = entry.get("review")
        assert isinstance(review, dict), f"{path}: grandfather without a review row"
        for field in ("date", "by", "outcome"):
            assert review.get(field), f"{path}: review.{field} missing"


def test_rights_module_reads_this_registry():
    """The emission gate and this file must be one authority, not two."""
    from engine.theme_graph import rights

    assert rights.rights_class("mastermind_curated") == "direct_display_ok"
    # Both unresolved families refuse public emission today; flipping the registry
    # to a display class is the operator's act and flips the gate with no code change.
    for fam in ("finviz_themes", "ths_concepts"):
        klass = rights.rights_class(fam)
        assert klass in RIGHTS_CLASSES
        if klass in ("unresolved", "internal_only"):
            try:
                rights.assert_public_emission_allowed(fam)
            except Exception:
                pass
            else:  # pragma: no cover — the gate silently passing is the defect
                raise AssertionError(f"{fam}: emission gate passed while {klass}")


def test_sec_edgar_family_is_display_ok_but_never_redistributable():
    """SEC filings are public-domain federal works: display with attribution is
    granted; redistribution as a dataset is not (auth_class is keyless_public,
    not house). Admitted 2026-09-24 for Finance Intelligence and the
    Semiconductor B witnesses; the rights module must read it fresh."""
    from engine.theme_graph import rights
    assert rights.rights_class("sec_edgar") == "direct_display_ok"
    assert rights.auth_class("sec_edgar") == "keyless_public"
    assert rights.licensing_for_family("sec_edgar") == (True, True, False)
    _, families = rights.load_registry_snapshot()
    assert families["sec_edgar"]["review"]["date"] == "2026-09-24"
    rights.assert_current_emission_allowed(["sec_edgar"], snapshot=rights.load_registry_snapshot())
