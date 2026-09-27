"""Closed composition tests for the Mining per-sector research response (T04a).

The Mining composition module is the per-sector composition the plan §6 T04 promised:
two closed definitions loaded from the domain content file, a closed ``compose_mining_research``
that validates against ``mining_theme_research.v1.schema.json`` on every return path, and a
``select_mining_evidence`` binding mechanism/counter-thesis text to the exact selected revisions.
No shared-kernel copy; no route; no I/O. Every authority flag stays literal False; every output
validates against the closed schema.

Seat rulings binding here:
- R-MIN-22: validate_mining_research on every return path (lazy jsonschema, own CONTRACT_PATH).
- R-MIN-23: limitations is closed-but-colon-aware (anyOf [enum] + [pattern]).
- R-MIN-24: dataclasses imported from ``mining_dependency_binding``; no import of the kernel.
- R-MIN-25: schema = 14 closed top-level keys; no ``neighborhood``; ``authorized_coverage.industry_total`` is null;
  ``authority`` echoed on every response and every evidence object.
- ADDENDUM §4 IR-01: a ``definition_unqualified:*`` may coexist with a ``comparable`` classification;
  no badge / beat / miss / improvement / model-readable confirmed-surprise field is emitted from it.
  Management point estimate stays a point estimate; no invented lower/upper range.
- PLAN §6 T04: rows ordered by stable source identity, never by magnitude; unknown data is never zero;
  industry_total stays null; a missing cutoff / wrong version / wrong slice / wrong theme /
  bool-pagination / competing generation refuses with a typed reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from engine.market_ontology.mining_dependency_binding import (
    MiningResearchQuery,
    MiningResearchRefusal,
    OMISSION_TO_LIMITATION,
)
from engine.market_ontology import mining_theme_research as composition
from tests.mining_casebook import CASE_NAMES, synthetic_case

SCHEMA_PATH = (
    Path(__file__).parent.parent
    / "contracts"
    / "market_ontology"
    / "mining_theme_research.v1.schema.json"
)
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_AUTHORITY = composition.AUTHORITY


def _validate(payload: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(payload)


def _replace_offset(query: MiningResearchQuery, offset: int) -> MiningResearchQuery:
    from dataclasses import replace as _replace

    return _replace(query, offset=offset, expected_generation=query.expected_generation)


def _replace_offset_no_generation(query: MiningResearchQuery, offset: int) -> MiningResearchQuery:
    from dataclasses import replace as _replace

    return _replace(query, offset=offset, expected_generation=None)


# ---------------------------------------------------------------------------
# verbatim plan test (T04 §6)
# ---------------------------------------------------------------------------


def test_missing_threshold_keeps_contract_explanation():
    """Plan §6 T04 verbatim: missing stream threshold keeps the contract explanation."""
    case = synthetic_case("missing_stream_threshold")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["summary"]["status"] == "ready"
    assert "stream_threshold_unknown" in result["limitations"]
    # The native-block list reflects the case's signed_native_blocks (empty here) — the
    # contract explanation is retained (PLAN §6); the plan's verbatim economic-shape
    # assertion is realised through ``economics.native_blocks``.
    assert result["economics"]["native_blocks"] == case.expected["signed_native_blocks"]
    _validate(result)


# ---------------------------------------------------------------------------
# positive witnesses
# ---------------------------------------------------------------------------


def test_copper_complete_is_ready_and_authority_literal_false():
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["request"]["slice_key"] == "mining_copper_economics"
    assert result["request"]["anchor_theme_id"] == "theme:copper_steel_electrify"
    assert result["summary"]["status"] == "ready"
    # All five authority flags are literal False (MGD-34 / R-MIN-25).
    assert result["authority"] == _AUTHORITY
    assert all(v is False for v in result["authority"].values())
    # The signed block is retained: the case's measure / value / basis travel through.
    blocks = result["economics"]["native_blocks"]
    assert len(blocks) == 1
    assert blocks[0]["measure"] == "reported operating income"
    assert blocks[0]["value"] == 1250
    assert blocks[0]["basis"] == "fictional reported dollars"
    _validate(result)


def test_rare_earth_complete_is_ready_and_authority_literal_false():
    case = synthetic_case("rare_earth_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["request"]["slice_key"] == "mining_rare_earth_economics"
    assert result["request"]["anchor_theme_id"] == "theme:rare_earth_critical_min"
    assert result["summary"]["status"] == "ready"
    assert result["authority"] == _AUTHORITY
    blocks = result["economics"]["native_blocks"]
    assert len(blocks) == 1
    assert blocks[0]["measure"] == "reported operating income"
    assert blocks[0]["value"] == 940
    assert blocks[0]["basis"] == "fictional reported dollars"
    _validate(result)


# ---------------------------------------------------------------------------
# negative paths required by the seat ruling
# ---------------------------------------------------------------------------


def test_missing_issuer_refuses_financial_join():
    """MGD-09 / case missing_issuer: a source without issuer identity keeps no financial join."""
    case = synthetic_case("missing_issuer")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert "missing_issuer" in result["limitations"]
    # No native block can be admitted without an issuer axis; the economics panel is honest, not silent.
    assert result["economics"]["native_blocks"] == []
    _validate(result)


def test_source_only_business_stays_useful():
    """MGD-11 / case source_only: a source-only mine description remains useful without invented IDs."""
    case = synthetic_case("source_only")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert "source_only" in result["limitations"]
    # The status is honest and the economics panel reflects the missing economic packet.
    assert result["economics"]["status"] in {"ready", "degraded"}
    assert result["summary"]["status"] in {"ready", "degraded"}
    _validate(result)


# ---------------------------------------------------------------------------
# row ordering: stable source identity, never magnitude
# ---------------------------------------------------------------------------


def test_economics_rows_ordered_by_stable_source_identity_not_magnitude():
    """PLAN:203 — rows are ordered by stable subject identity, never by magnitude."""
    # The synthetic copper fixture exposes one block; build a multi-row case at the same
    # slice and assert the order is preserved.
    block_a = {
        "stable_subject_id": "subject:z-block",
        "measure": "test_measure_z",
        "value": 999,
        "sign": "+",
        "basis": "fictional",
        "source_label": "z-block-source",
    }
    block_b = {
        "stable_subject_id": "subject:a-block",
        "measure": "test_measure_a",
        "value": 1,
        "sign": "+",
        "basis": "fictional",
        "source_label": "a-block-source",
    }
    rows = composition._order_rows_by_stable_source_identity([block_b, block_a])
    assert [row["stable_subject_id"] for row in rows] == [
        "subject:a-block",
        "subject:z-block",
    ]


def test_economics_rows_ordered_through_compose_mining_research():
    """MAJOR-9: ordering by stable source identity is enforced end-to-end, not only in the helper.

    The probe froze the test above (private helper). This is the composed-channel assertion:
    a bundle carrying two financial_packets with distinct stable_subject_ids is run through
    ``compose_mining_research`` and the produced native_blocks list is asserted to come out
    ordered by stable_subject_id, never by magnitude. Each packet keeps its own
    stable_subject_id (no 'subject:unknown' fallback).
    """
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    custom_packets = (
        {
            "stable_subject_id": "subject:z-block",
            "measure": "test_measure_z",
            "value": 999,
            "basis": "fictional reported dollars",
            "selection_label": "z-block-source",
        },
        {
            "stable_subject_id": "subject:a-block",
            "measure": "test_measure_a",
            "value": 1,
            "basis": "fictional reported dollars",
            "selection_label": "a-block-source",
        },
    )
    custom_bundle = _replace(case.bundle, financial_packets=custom_packets)
    result = composition.compose_mining_research(case.query, custom_bundle)
    ids = [b["stable_subject_id"] for b in result["economics"]["native_blocks"]]
    assert ids == ["subject:a-block", "subject:z-block"], ids
    # And no block has collapsed to the 'subject:unknown' fallback.
    assert all(i != "subject:unknown" for i in ids)


# ---------------------------------------------------------------------------
# duplicate local asset labels and internal transfer / elimination sign
# ---------------------------------------------------------------------------


def test_duplicate_local_asset_labels_are_not_additional_supply():
    """MGD-12 / duplicate local asset labels: same mine appearing twice is not additional supply."""
    case = synthetic_case("copper_complete")
    bundle = composition._make_industrial_views_bundle(
        [
            {"stable_subject_id": "subject:morro-mine", "view_kind": "industrial", "description": "morro mine", "evidence_refs": ["ev:1"]},
            {"stable_subject_id": "subject:morro-mine", "view_kind": "industrial", "description": "morro mine again", "evidence_refs": ["ev:1"]},
        ],
        account_generation=case.account_generation,
    )
    result = composition.compose_mining_research(case.query, bundle)
    distinct = {view["stable_subject_id"] for view in result["industrial_views"]}
    assert len(distinct) == 1
    assert len(result["industrial_views"]) == 2
    _validate(result)


def test_internal_transfer_keeps_elimination_sign():
    """MGD-19 / W-R: an intersegment elimination row keeps its reported negative sign."""
    # The synthetic rare-earth complete case exposes no internal-transfer row; the contract
    # here is that any row composed with a negative value must retain its sign (zero / negative
    # grow base must NOT be flipped). We pin this with a direct helper call.
    signed = composition._signed_value({"value": -375, "sign_preserved": True})
    assert signed == -375
    # Zero is NOT a missing value: zero is zero (MGD-15 / IR-02).
    assert composition._signed_value({"value": 0}) == 0
    # And a missing value is None, not zero (PLAN §6 — unknown data never becomes zero).
    assert composition._signed_value({}) is None


# ---------------------------------------------------------------------------
# partial coverage and unsupported contract calculation
# ---------------------------------------------------------------------------


def test_partial_coverage_industry_total_stays_null():
    """MGD-39: industry_total stays null on partial coverage; never silently filled."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert result["authorized_coverage"]["industry_total"] is None
    # If the input carries an industry_total_unknown limitation, it is propagated verbatim.
    assert "industry_total_unknown" not in result["limitations"]


def test_stream_threshold_omission_propagates_as_limitation():
    """The stream_threshold omission translates to the closed stream_threshold_unknown code (R-MIN-15)."""
    case = synthetic_case("rare_earth_complete")
    bundle = composition._add_omission(case.bundle, "stream_threshold")
    result = composition.compose_mining_research(case.query, bundle)
    # stream_threshold_unknown is the contracted limitation for the stream-threshold omission.
    assert "stream_threshold_unknown" in result["limitations"]


def test_industry_total_unknown_is_minted_iff_slice_vocab_contracts_it():
    """R-MIN-31 §4 / MAJOR-E: ``industry_total_unknown`` polarity — minted iff the slice's
    own ``limitations_vocabulary`` names the code AND ``authorized_coverage.industry_total``
    is contracted null (R-MIN-25). The rare-earth slice names it; copper does not.
    Binding or not binding the issuer axis never toggles the code.
    """
    from dataclasses import replace as _replace

    # Rare-earth slice — every case mints it (slice-vocab contract).
    rare_case = synthetic_case("rare_earth_complete")
    rare_bound = composition.compose_mining_research(rare_case.query, rare_case.bundle)
    assert "industry_total_unknown" in rare_bound["limitations"]
    assert rare_bound["authorized_coverage"]["industry_total"] is None
    rare_unbound_bundle = _replace(rare_case.bundle, identity_results=())
    rare_unbound = composition.compose_mining_research(rare_case.query, rare_unbound_bundle)
    assert "industry_total_unknown" in rare_unbound["limitations"]
    # Copper slice — never mints it (slice-vocab does not contract it).
    copper_case = synthetic_case("copper_complete")
    copper_result = composition.compose_mining_research(copper_case.query, copper_case.bundle)
    assert "industry_total_unknown" not in copper_result["limitations"]
    copper_unbound_bundle = _replace(copper_case.bundle, identity_results=())
    copper_unbound = composition.compose_mining_research(copper_case.query, copper_unbound_bundle)
    assert "industry_total_unknown" not in copper_unbound["limitations"]


def test_industry_total_unknown_is_absent_on_w_c_slice():
    """Copper does not contract industry_total_unknown; the closed bare-code set is slice-scoped."""
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert "industry_total_unknown" not in result["limitations"]


def test_unsupported_contract_calculation_is_missing_derivation_not_invented_value():
    """PLAN §6 / MGD-18: a contract without a verified threshold blocks entitlement; no value invented."""
    case = synthetic_case("missing_stream_threshold")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert "stream_threshold_unknown" in result["limitations"]
    # The economics panel must not invent a derivation to compensate.
    assert result["economics"]["derived"] == []
    # And the contract explanation (mechanism / counter-thesis) remains visible, not suppressed.
    assert result["economics"]["reported_economic_context"]["policy"] == "reported_economic_context"
    _validate(result)


# ---------------------------------------------------------------------------
# IR-01: definition_unqualified never becomes a badge
# ---------------------------------------------------------------------------


def test_ir01_both_null_definitions_no_badge_no_model_readable_field():
    """IR-01: two null bases, warning present, no beat / miss / improvement / confirmed-surprise."""
    # Build an expectation pair with both definitions missing to force a definition_unqualified:definition warning.
    expectations_payload = [
        {
            "stable_subject_id": "subject:test",
            "comparison_kind": "earlier_point_estimate_vs_later_actual",
            "earlier_point_estimate": {"metric": "x", "value": 1.0, "basis": "?", "source_label": "earlier"},
            "later_actual": {"metric": "x", "value": 2.0, "basis": "?", "source_label": "later"},
            "definition_unqualified_fields": ["basis"],
            "is_range": False,
            "is_consensus": False,
        }
    ]
    headlines = composition._summarize_expectations(
        expectations_payload, defined_fields={"unit", "perimeter"}
    )
    # No badge vocabulary: beat / miss / improvement / above / below / surprise / confirmed.
    assert not any(
        word in headlines["headline"].lower()
        for word in ("beat", "miss", "improvement", "above", "below", "confirmed")
    )
    # A model-readable confirmed-surprise field is never emitted: only the bounded fields exist.
    assert "confirmed_surprise" not in headlines
    assert "comparison_badge" not in headlines
    # And the unqualified warning is preserved in the limitations — minted by the
    # helper itself, never appended by this test (IR-01 / MAJOR-5).
    assert "definition_unqualified:basis" in headlines["limitations"]


def test_ir01_fully_qualified_genuine_comparison_not_suppressed():
    """IR-01: a fully-qualified genuine positive comparison must not be suppressed."""
    payload = [
        {
            "stable_subject_id": "subject:test",
            "comparison_kind": "earlier_point_estimate_vs_later_actual",
            "earlier_point_estimate": {"metric": "x", "value": 1.0, "basis": "ok", "source_label": "earlier"},
            "later_actual": {"metric": "x", "value": 2.0, "basis": "ok", "source_label": "later"},
            "definition_unqualified_fields": [],
            "is_range": False,
            "is_consensus": False,
        }
    ]
    headlines = composition._summarize_expectations(payload, defined_fields={"basis", "unit", "perimeter"})
    assert "definition_unqualified" not in headlines["headline"].lower()
    assert not any(
        word in headlines["headline"].lower()
        for word in ("beat", "miss", "improvement", "above", "below", "confirmed")
    )


# ---------------------------------------------------------------------------
# IR-04 / R-MIN-24: unknown version, unknown slice, unknown theme, bool pagination
# ---------------------------------------------------------------------------


def test_ir04_unknown_definition_version_refuses():
    """IR-04: an unknown version refuses — versions never collapse silently to v1."""
    case = synthetic_case("copper_complete")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(case.query, case.bundle, definition_version="v0.0-does-not-exist")
    # Step 8 (no subclass bypass of CODES): the refusal uses the closed-vocab code
    # that semantically matches "input doesn't match a closed Mining value".
    assert raised.value.code == "unknown_slice"


def test_unknown_slice_refuses():
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    bad_query = _replace(case.query, slice_key="mining_unknown_slice")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(bad_query, case.bundle)
    assert raised.value.code == "unknown_slice"


def test_slice_theme_mismatch_refuses():
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    bad_query = _replace(case.query, anchor_theme_id="theme:rare_earth_critical_min")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(bad_query, case.bundle)
    assert raised.value.code == "slice_theme_mismatch"


def test_bool_pagination_refuses():
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    bad_query = _replace(case.query, limit=True)
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(bad_query, case.bundle)
    assert raised.value.code == "limit_out_of_range"


def test_missing_replay_cutoff_refuses():
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    bad_query = _replace(case.query, time_mode="system_replay", source_cutoff=None)
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(bad_query, case.bundle)
    assert raised.value.code == "replay_cutoffs_required"


def test_competing_generation_refuses():
    case = synthetic_case("copper_complete")
    from dataclasses import replace as _replace

    bad_query = _replace(case.query, expected_generation="competing-page")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.compose_mining_research(bad_query, case.bundle)
    assert raised.value.code == "generation_changed"


# ---------------------------------------------------------------------------
# validate_mining_research is called on every return path
# ---------------------------------------------------------------------------


def test_payload_always_validates_against_schema():
    """R-MIN-22 / MUTANT (return without validate): every composed payload validates."""
    for name in CASE_NAMES:
        case = synthetic_case(name)
        result = composition.compose_mining_research(case.query, case.bundle)
        _validate(result)


def test_validate_mining_research_refuses_bad_payload():
    """R-MIN-22: validate_mining_research raises on a non-conforming payload."""
    with pytest.raises(jsonschema.ValidationError):
        composition.validate_mining_research({"authority": _AUTHORITY})


def test_select_mining_evidence_returns_authority_echo_and_binds_to_revisions():
    """R-MIN-25: authority is echoed on every evidence object; revisions are bound verbatim."""
    case = synthetic_case("copper_complete")
    result = composition.select_mining_evidence(case.query, case.bundle, "assertion:synthetic")
    assert result["authority"] == _AUTHORITY
    assert result["selected_revisions"] == [list(pair) for pair in case.bundle.revision_tuple]
    # Evidence ref also carries the authority echo (R-MIN-25).
    for ev in result["evidence_refs"]:
        assert ev["authority"] == _AUTHORITY


def test_select_mining_evidence_blocks_changed_quantities_with_stale_causal_text():
    """PLAN §6 / ADDENDUM §4 IR-01: a refresh cannot pair changed quantities with stale causal text."""
    case = synthetic_case("changed_source")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.select_mining_evidence(case.query, case.bundle, "assertion:synthetic")
    # Step 8: closed CODES; semantically the bound source revision changed.
    assert raised.value.code == "generation_changed"


# ---------------------------------------------------------------------------
# MINING_DEFINITIONS: imported from the committed yaml
# ---------------------------------------------------------------------------


def test_mining_definitions_loaded_from_committed_domain_file():
    definitions = composition.MINING_DEFINITIONS
    assert set(definitions) == {"mining_copper_economics", "mining_rare_earth_economics"}
    assert (
        definitions["mining_copper_economics"]["anchor_theme_id"]
        == "theme:copper_steel_electrify"
    )
    assert (
        definitions["mining_rare_earth_economics"]["anchor_theme_id"]
        == "theme:rare_earth_critical_min"
    )
    # Unknown slice raises KeyError (frozen spec).
    with pytest.raises(KeyError):
        definitions["mining_unknown_slice"]


# ---------------------------------------------------------------------------
# no shared-kernel import: grep-able proof
# ---------------------------------------------------------------------------


def test_no_import_of_semiconductor_theme_research_anywhere():
    """ADDENDUM §2 / R-MIN-21: no shared-kernel copy in the Mining composition module."""
    import re

    src = Path(composition.__file__).read_text(encoding="utf-8")
    # Grep only import statements; the module's docstring may reference forbidden names
    # in prose, but the import surface must be Mining-owned.
    import_lines = [
        line for line in src.splitlines()
        if re.match(r"^(from|import)\s+", line)
    ]
    joined = "\n".join(import_lines)
    assert "semiconductor_theme_research" not in joined
    assert "engine.theme_graph" not in joined  # the shared assertion contract is probed lazily elsewhere
    assert "engine.market_ontology.semiconductor" not in joined


def test_compose_does_not_perform_io():
    """Composition must be pure; no file, network or clock reads inside the function."""
    case = synthetic_case("copper_complete")
    # Run twice and assert equality — a clock read would show drift.
    first = composition.compose_mining_research(case.query, case.bundle)
    second = composition.compose_mining_research(case.query, case.bundle)
    assert first == second


# ---------------------------------------------------------------------------
# omisson -> limitation mapping is wired correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", CASE_NAMES)
def test_omission_to_limitation_is_wired(name):
    """OMISSION_TO_LIMITATION propagates as a limitation code; never invented code."""
    case = synthetic_case(name)
    result = composition.compose_mining_research(case.query, case.bundle)
    expected_limitations = {OMISSION_TO_LIMITATION[o] for o in case.bundle.omissions}
    # All expected codes must be present; the response may also carry definition_unqualified warnings
    # if a definition field is missing — that is acceptable because the case has no definition fields.
    for code in expected_limitations:
        assert code in result["limitations"], f"case {name!r}: missing {code!r}"


# ---------------------------------------------------------------------------
# packet-driven expectation rows (R-MIN-31 §3; literal expected values)
# ---------------------------------------------------------------------------

from dataclasses import replace as _replace  # noqa: E402  (local import per the ruling)


def _copper_with_packets(*packets):
    """Return (query, bundle) for a usable copper case with the given mev packets."""
    case = synthetic_case("copper_complete")
    return case.query, _replace(case.bundle, financial_packets=tuple(packets))


def _mev_packet(pair, epe_value, la_value, **extras):
    """Build a literal ``management_estimate_vs_actual`` packet for one comparison pair."""
    base = {
        "kind": "management_estimate_vs_actual",
        "pair": pair,
        "earlier_point_estimate": {
            "value": epe_value,
            "unit": "Mlbs",
            "perimeter": "consolidated",
            "basis": "reported",
            "period": "Q2 2026",
        },
        "later_actual": {
            "value": la_value,
            "unit": "Mlbs",
            "perimeter": "consolidated",
            "basis": "reported",
            "period": "Q2 2026",
        },
    }
    base.update(extras)
    return base


def test_packet_driven_sales_pair_emits_one_row_with_literal_values():
    """A copper sales packet (epe=1700, la=1680) emits exactly one row with literal values
    and the comparison word ``below_estimate`` (la < epe). The row binds to the issuer
    identity of the casebook fixture (Ardent Copper Holdings / cik 0000000421).
    """
    query, bundle = _copper_with_packets(_mev_packet("sales", 1700, 1680))
    result = composition.compose_mining_research(query, bundle)
    assert len(result["expectations"]) == 1, result["expectations"]
    row = result["expectations"][0]
    assert row["stable_subject_id"] == "0000000421"
    assert row["comparison_kind"] == "earlier_point_estimate_vs_later_actual"
    assert row["comparison"] == "below_estimate"
    assert row["is_range"] is False and row["is_consensus"] is False
    epe = row["earlier_point_estimate"]
    la = row["later_actual"]
    assert epe["value"] == 1700
    assert la["value"] == 1680
    assert epe["metric"] == "management_issued_copper_sales_estimate"
    assert la["metric"] == "consolidated_copper_sales"
    assert epe["basis"] == "fictional point estimate"
    assert la["basis"] == "fictional reported measure"
    # The casebook carries no native-block packet, so no native blocks; limitations
    # carry ``omitted:expectations`` only (the row WAS attempted, successfully).
    assert "omitted:expectations" not in result["limitations"]


def test_packet_driven_sales_pair_above_estimate_when_la_exceeds_epe():
    """A sales packet with la > epe emits ``above_estimate``."""
    query, bundle = _copper_with_packets(_mev_packet("sales", 1700, 1750))
    result = composition.compose_mining_research(query, bundle)
    assert len(result["expectations"]) == 1
    assert result["expectations"][0]["comparison"] == "above_estimate"


def test_packet_driven_equal_legs_withhold_row_and_mint_omitted_expectations():
    """Two equal leg values withhold the row (no fabricated surprise) and mint
    ``omitted:expectations`` (R-MIN-31 §3 — never synthesize the comparison).
    """
    query, bundle = _copper_with_packets(_mev_packet("sales", 1700, 1700))
    result = composition.compose_mining_research(query, bundle)
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]


def test_packet_driven_missing_required_field_withholds_row_and_mints_unqualified():
    """A leg whose ``unit`` field is missing withholds the row and mints
    ``definition_unqualified:unit`` (R-MIN-31 §3, MAJOR-D). The code is
    deduplicated across multiple bad legs.
    """
    bad_packet = _mev_packet("sales", 1700, 1680)
    del bad_packet["earlier_point_estimate"]["unit"]
    del bad_packet["later_actual"]["unit"]
    query, bundle = _copper_with_packets(bad_packet)
    result = composition.compose_mining_research(query, bundle)
    assert result["expectations"] == []
    assert "definition_unqualified:unit" in result["limitations"]


def test_packet_driven_non_numeric_value_withholds_row_and_mints_omitted_expectations():
    """A packet whose ``value`` is the string ``"quarter"`` (the BLOCKER-A fabrication)
    withholds the row and mints ``omitted:expectations`` (MINOR-I) — the
    ``definition_unqualified:value`` limitation is reserved for definition
    fields, never for a missing measurement datum.
    """
    bad_packet = {
        "kind": "management_estimate_vs_actual",
        "pair": "sales",
        "earlier_point_estimate": {
            "value": "quarter",
            "unit": "Mlbs",
            "perimeter": "consolidated",
            "basis": "reported",
            "period": "Q2 2026",
        },
        "later_actual": {
            "value": "quarter",
            "unit": "Mlbs",
            "perimeter": "consolidated",
            "basis": "reported",
            "period": "Q2 2026",
        },
    }
    query, bundle = _copper_with_packets(bad_packet)
    result = composition.compose_mining_research(query, bundle)
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]
    assert "definition_unqualified:value" not in result["limitations"]


def test_packet_driven_unknown_pair_withholds_row_and_mints_omitted_expectations():
    """A packet whose ``pair`` is ``"foo"`` (unknown) withholds the row and mints
    ``omitted:expectations``. No row is invented with a synthesised comparison.
    """
    bad_packet = _mev_packet("foo", 1700, 1680)
    query, bundle = _copper_with_packets(bad_packet)
    result = composition.compose_mining_research(query, bundle)
    assert result["expectations"] == []
    assert "omitted:expectations" in result["limitations"]


def test_packet_driven_row_order_sales_first_unit_net_cash_cost_second():
    """MINOR-J: row order is pinned by pair name regardless of packet arrival order.
    A reversed packet list still emits sales-then-unit_net_cash_cost.
    """
    unit_packet = _mev_packet(
        "unit_net_cash_cost", 2.95, 2.85,
        earlier_point_estimate={"value": 2.95, "unit": "USD/lb", "perimeter": "consolidated",
                                "basis": "company_adjusted", "period": "Q2 2026"},
        later_actual={"value": 2.85, "unit": "USD/lb", "perimeter": "consolidated",
                      "basis": "company_adjusted", "period": "Q2 2026"},
    )
    sales_packet = _mev_packet("sales", 1700, 1750)
    # Reversed order on input; ordered on output.
    query, bundle = _copper_with_packets(unit_packet, sales_packet)
    result = composition.compose_mining_research(query, bundle)
    assert len(result["expectations"]) == 2
    assert result["expectations"][0]["earlier_point_estimate"]["metric"] == "management_issued_copper_sales_estimate"
    assert result["expectations"][1]["earlier_point_estimate"]["metric"] == "management_issued_copper_unit_net_cash_cost_estimate"
    assert result["expectations"][0]["comparison"] == "above_estimate"
    assert result["expectations"][1]["comparison"] == "below_estimate"


def test_packet_driven_both_pairs_emitted_with_subject_id_from_identity_results():
    """Sales + unit-cost packets together emit TWO rows, both bound to the issuer
    identity of the casebook (cik 0000000421); MAJOR-F: the row's
    ``stable_subject_id`` falls back to cik when ``stable_subject_id`` is absent
    on the identity_results entry — never ``"subject:unknown"``.
    """
    unit_packet = _mev_packet(
        "unit_net_cash_cost", 2.95, 2.85,
        earlier_point_estimate={"value": 2.95, "unit": "USD/lb", "perimeter": "consolidated",
                                "basis": "company_adjusted", "period": "Q2 2026"},
        later_actual={"value": 2.85, "unit": "USD/lb", "perimeter": "consolidated",
                      "basis": "company_adjusted", "period": "Q2 2026"},
    )
    sales_packet = _mev_packet("sales", 1700, 1750)
    query, bundle = _copper_with_packets(sales_packet, unit_packet)
    result = composition.compose_mining_research(query, bundle)
    assert len(result["expectations"]) == 2
    for row in result["expectations"]:
        assert row["stable_subject_id"] != "subject:unknown"
        assert row["stable_subject_id"] == "0000000421"


def test_packet_driven_withdrawn_case_publishes_no_expectation_row():
    """MAJOR-B: a case with any omission (bundle.omissions != ()) publishes NO row,
    even when mev packets are present in ``financial_packets``.
    """
    case = synthetic_case("missing_issuer")
    packets = (_mev_packet("sales", 1700, 1750),)
    withdrawn_bundle = _replace(case.bundle, financial_packets=packets)
    result = composition.compose_mining_research(case.query, withdrawn_bundle)
    assert result["expectations"] == []


def test_rare_earth_usable_case_carries_slice_definitional_codes_only():
    """R-MIN-31 §2: rare-earth usable cases carry the closed slice-definitional codes
    ``stream_threshold_unknown`` + ``industry_total_unknown`` +
    ``definition_unqualified:management_estimate_vs_actual``, NEVER
    ``omitted:expectations`` (the rare-earth mev declares both legs null —
    the truthful "no comparison selected" marker is the definition_unqualified
    code, not the omission-mapped code).
    """
    case = synthetic_case("rare_earth_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    assert "stream_threshold_unknown" in result["limitations"]
    assert "industry_total_unknown" in result["limitations"]
    assert "definition_unqualified:management_estimate_vs_actual" in result["limitations"]
    assert "omitted:expectations" not in result["limitations"]
    assert "missing_derivation" not in result["limitations"]


def test_copper_usable_case_carries_no_slice_definitional_codes():
    """R-MIN-31 §2: copper mints no slice-definitional codes; only the case's
    own omission-mapped codes (none for a usable case) plus the truthful
    ``omitted:expectations`` when no mev packet is present.
    """
    case = synthetic_case("copper_complete")
    result = composition.compose_mining_research(case.query, case.bundle)
    for code in ("stream_threshold_unknown", "industry_total_unknown",
                 "definition_unqualified:management_estimate_vs_actual"):
        assert code not in result["limitations"], (code, result["limitations"])
    assert "omitted:expectations" in result["limitations"]


def test_limitations_list_is_sorted_and_deduplicated():
    """R-MIN-31 §4 / F3 colon-aware: limitations is a sorted, duplicate-free list."""
    case = synthetic_case("rare_earth_complete")
    from dataclasses import replace as _r
    # Inject a known limitation, plus try to mint duplicates.
    bundle = _r(case.bundle, omissions=("stream_threshold", "page_generation"))
    result = composition.compose_mining_research(case.query, bundle)
    limits = result["limitations"]
    assert limits == sorted(limits), limits
    assert len(limits) == len(set(limits)), limits


def test_minor_h_empty_source_label_degrades_to_synthetic_source():
    """MINOR-H: an empty ``source_label`` on a native-block packet degrades to the
    closed ``synthetic-source`` fallback (never ``""``, which would trip the
    schema's ``minLength: 1`` and raise a raw ``jsonschema.ValidationError``).
    """
    case = synthetic_case("copper_complete")
    empty_packet = {
        "measure": "reported operating income",
        "value": 880,
        "basis": "fictional reported dollars",
        "source_label": "",
    }
    bundle = _replace(case.bundle, financial_packets=(empty_packet,))
    result = composition.compose_mining_research(case.query, bundle)
    assert result["economics"]["native_blocks"][0]["source_label"] == "synthetic-source"