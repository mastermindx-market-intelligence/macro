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

import pytest
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


# ---------------------------------------------------------------------------
# The source-prefix table (Sol #7780 issuecomment-5825621672 items 5 and 6,
# confirmed 5825811888 items 2 and 5). Applied ONCE here by the shared rights
# owner; neither prefix table had a test of its own before this.
# ---------------------------------------------------------------------------

RECOGNITION_ONLY = (
    "jpx_tdnet_issuer_disclosure", "hkexnews_issuer_disclosure",
    "orbbec_vendor_case_study", "parker_vendor_catalogue",
    "robotis_vendor_catalogue", "onex_vendor_product_page",
    "hexagon_robotics_press", "zebra_press", "ptc_press",
    "teradyne_ir_sec_wrapper", "stabilus_press",
)


def test_every_prefix_family_has_a_registry_row():
    """The module's own stated law: an UNKNOWN family fails CLOSED, because a
    family nobody wrote down is a family nobody reviewed. A prefix naming a
    family with no row would make ``rights_class`` RAISE on a real request
    instead of refusing — this is what keeps the two tables honest."""
    from engine.theme_graph.rights import (
        NODE_PREFIX_FAMILY, SOURCE_PREFIX_FAMILY, rights_class,
    )

    for prefix, family in (*SOURCE_PREFIX_FAMILY, *NODE_PREFIX_FAMILY):
        assert rights_class(family) in RIGHTS_CLASSES, f"{prefix} -> {family}"


def test_no_prefix_shadows_another_family():
    """``family_for_source_ref`` is first-match-wins over a tuple, so an entry
    that is itself the prefix of a later one naming a DIFFERENT family makes
    the later one unreachable — and unreachable is refused by accident."""
    from engine.theme_graph.rights import SOURCE_PREFIX_FAMILY

    for i, (outer, outer_family) in enumerate(SOURCE_PREFIX_FAMILY):
        for inner, inner_family in SOURCE_PREFIX_FAMILY[i + 1:]:
            if inner.startswith(outer):
                assert inner_family == outer_family, (
                    f"{inner!r} ({inner_family}) is unreachable behind "
                    f"{outer!r} ({outer_family})"
                )


def test_an_edgar_filing_url_binds_to_the_admitted_sec_edgar_family():
    """Sol item 5: one narrowly scoped family through the EXISTING registry,
    exact recognition prefix ``https://www.sec.gov/Archives/``, and no emission
    special case. Before this the family was admitted but UNREACHABLE from a
    filing URL, so the witnesses' own evidence would have been refused for want
    of a mapping rather than for want of a right."""
    from engine.theme_graph import rights

    assert rights.family_for_source_ref(
        "https://www.sec.gov/Archives/edgar/data/1046179/tsmc-6k.htm"
    ) == "sec_edgar"
    rights.assert_public_emission_allowed("sec_edgar")  # direct_display_ok


def test_a_sec_gov_url_outside_archives_is_not_the_admitted_family():
    """The prefix is EXACT. The ruling scoped the family to SEC-hosted filing
    content under ``/Archives/``, not to everything on the host."""
    from engine.theme_graph.rights import family_for_source_ref

    assert family_for_source_ref("https://www.sec.gov/litigation/x.htm") is None
    assert family_for_source_ref("https://data.sec.gov/submissions/CIK1.json") is None


@pytest.mark.parametrize("family", RECOGNITION_ONLY)
def test_a_recognition_only_family_is_named_and_still_refused(family):
    """Sol item 6 / 5825811888 item 2: recognition changes the refusal REASON,
    not the serving result. The family must be findable from its prefix AND
    must still refuse at the emission gate."""
    from engine.theme_graph import rights

    prefixes = [p for p, f in rights.SOURCE_PREFIX_FAMILY if f == family]
    assert len(prefixes) == 1, f"{family} must have exactly one exact prefix"
    assert rights.family_for_source_ref(prefixes[0] + "anything") == family
    assert rights.rights_class(family) == "unresolved"
    with pytest.raises(rights.RightsRefusal):
        rights.assert_public_emission_allowed(family)


@pytest.mark.parametrize("family", RECOGNITION_ONLY)
def test_a_recognition_only_row_records_that_keyless_public_is_inferred(family):
    """5825811888 item 2 REQUIRES the R7 warning to ride with the row:
    ``keyless_public`` is the current no-credential access descriptor, never an
    acquisition or retention permission receipt."""
    row = _doc()["families"][family]
    assert row["auth_class"] == "keyless_public"
    assert "INFERRED" in row["notes"]
    assert "permission receipt" in row["notes"]
    assert "RECOGNITION ONLY" in row["review"]["outcome"]


def test_the_recognition_prefixes_are_exact_pages_not_host_roots():
    """Two rows are a single exact page. A prefix widened to its host would
    admit documents nobody qualified."""
    from engine.theme_graph.rights import SOURCE_PREFIX_FAMILY

    exact = dict((f, p) for p, f in SOURCE_PREFIX_FAMILY)
    assert exact["parker_vendor_catalogue"] == "https://discover.parker.com/K-Series"
    assert exact["hexagon_robotics_press"].endswith("-humanoids/")
    for family in RECOGNITION_ONLY:
        prefix = exact[family]
        assert prefix.startswith("https://")
        # A host root is "https://host" or "https://host/" — nothing after the
        # authority. Every recognition prefix must name a path below it.
        authority, _, path = prefix[len("https://"):].partition("/")
        assert authority and path, f"{family}: {prefix} is a host root"


def test_example_invalid_is_absent_from_the_table_by_ruling():
    """Fixture-only, unmapped by design — so it fails closed like any other
    unmapped source instead of acquiring a family it should not have."""
    from engine.theme_graph.rights import SOURCE_PREFIX_FAMILY, family_for_source_ref

    assert not any("example.invalid" in p for p, _ in SOURCE_PREFIX_FAMILY)
    assert family_for_source_ref("https://example.invalid/doc.html") is None


def test_sec_edgar_family_is_display_ok_but_never_redistributable():
    """Display with attribution is granted; redistribution as a dataset is not
    (auth_class is keyless_public, not house). The basis is the SEC Website
    Dissemination policy, NOT "all filings are federal-government works" —
    issuer-authored filing text is the issuer's expression, and Sol
    #7780 issuecomment-5825621672 item 5 forbids the federal-works rationale
    explicitly. The YAML row was corrected by 7d456cd37d8; this docstring had
    kept the superseded wording. Admitted 2026-09-24 for Finance Intelligence
    and the Semiconductor B witnesses; the rights module must read it fresh."""
    from engine.theme_graph import rights
    assert rights.rights_class("sec_edgar") == "direct_display_ok"
    assert rights.auth_class("sec_edgar") == "keyless_public"
    assert rights.licensing_for_family("sec_edgar") == (True, True, False)
    _, families = rights.load_registry_snapshot()
    assert families["sec_edgar"]["review"]["date"] == "2026-09-24"
    rights.assert_current_emission_allowed(["sec_edgar"], snapshot=rights.load_registry_snapshot())
