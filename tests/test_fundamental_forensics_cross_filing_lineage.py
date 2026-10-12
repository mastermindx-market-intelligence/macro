"""FIF-3A4: cutoff-visible cross-filing fact lineage through the real query path.

Authority: ``DEC:FIF-3A4R-CROSS-FILING-LINEAGE-ACCEPTED-ON-MAIN`` plus the
accepted protocol ``research/financial_intelligence_fabric/FIF_3A4R_CROSS_FILING_LINEAGE_PROTOCOL.md``.

Every test here is one of the fifteen discriminating behaviours the accepted
A4R protocol §9 requires of an implementation: each must fail on plain FIF-3A3
and pass only once cutoff-visible lineage evidence is wired. Only the frozen
A1/A2 golden pair participates; ``GOLDEN_AAPL_FIXTURES`` is never widened, and
the research census JSON is never loaded.
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    GoldenAaplFinancialQueryProvider,
    original_concept_namespace_uris,
    parse_and_convert_golden_packages,
)
from engine.fundamental_forensics.lineage_evidence import (
    CONFIRMATION_RULE_AVAILABLE_AT,
    LineageEvidenceError,
    LineageEvidenceReceipt,
    derive_confirmation_receipts,
    evaluate_confirmation,
)
from engine.fundamental_forensics.query_service import (
    FinancialQueryUnavailableError,
    execute_financial_query,
)
from engine.fundamental_forensics.raw_ledger import RawFactLedger
from engine.fundamental_forensics.statement_graph import load_golden_aapl_package

ROOT = Path(__file__).resolve().parents[1]

_GOLDEN_ENTITY = "ISS:US-XNAS-AAPL"
_A1 = "0000320193-25-000079"
_A2 = "0000320193-26-000020"

# Accepted FIF-3A3 identities. A4 must not move any of them.
_LEDGER_SHA = "ba149bd55d929d843f353e91bbf68147791fb8b4a20c258426ea2eb7527019d8"
_AAPL_QUERY_RESPONSE_SHA = "58972cb88f82483e86acc9d9fc3b1cbce046f466ff8665ae214909d90ab078b0"
_AAPL_QUERY_HASH = "f8f6dc3134592c817001738cbdefb09ee1b71798ef24a8e64dc75685a6f9c7a1"
_A1_ASSETS_OCCURRENCE = "rawfact_bc9355a292f06baaaf988b683106b2b02e3dd9c4a9555f1eb160a94643e4feaf"
_A2_ASSETS_OCCURRENCE = "rawfact_9669446bc8076fa26bca33a3d9a067093bddadbb28e4617318bb3de33a4eca29"

# The accepted A4R AAPL calibration census.
_EXPECTED_POSITIVE_CONFIRMATIONS = 130
_EXPECTED_OVERLAP_LOGICAL_KEYS = 133

# FIF-3A3 cutoffs: before the A4R lineage rule existed.
_A3_SOURCE = "2026-08-01T00:00:00Z"
_A3_RECORDED = "2026-08-23T12:00:00Z"
# FIF-3A4 cutoffs: after the rule clock and the receipt recording.
_A4_SOURCE = "2026-09-20T00:00:00Z"
_A4_RECORDED = "2026-09-20T00:00:00Z"
_A4_AVAILABLE_AT = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

_FY2025_REV = {"kind": "duration", "start": "2024-09-29", "end": "2025-09-27", "label": "FY2025"}
_Q3_REV = {"kind": "duration", "start": "2026-03-29", "end": "2026-06-27", "label": "FY2026Q3"}
_YTD_REV = {"kind": "duration", "start": "2025-09-28", "end": "2026-06-27", "label": "FY2026YTD"}
_A2_ASSETS = {"kind": "instant", "start": None, "end": "2026-06-27", "label": "2026-06-27"}
_COMPARATIVE = {"kind": "instant", "start": None, "end": "2025-09-27", "label": "2025-09-27"}

_GOLDEN_METRICS = ["revenue", "total_assets", "gross_margin", "net_cash_from_operating_activities"]
_GOLDEN_PERIODS = [_FY2025_REV, _Q3_REV, _YTD_REV, _A2_ASSETS]


def _body(*, metric_ids, periods, source, recorded, selection="latest_known_as_of"):
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": _GOLDEN_ENTITY,
            "policy": {
                "selection": selection,
                "source_snapshot_at": source,
                "recorded_at": recorded,
            },
            "metric_ids": metric_ids,
            "periods": periods,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _root_cell(envelope, metric_id, *, start, end):
    receipt = envelope["receipt"]
    roots = set(receipt["root_cell_ids"])
    for node in receipt["nodes"]:
        if node["cell_id"] not in roots or node["metric_id"] != metric_id:
            continue
        period = node["period"]
        if period.get("start") == start and period.get("end") == end:
            return node
    raise AssertionError(f"no root cell for {metric_id} {start}..{end}")


@pytest.fixture(scope="module")
def golden_packages():
    return [load_golden_aapl_package(ROOT, accession=item) for item in GOLDEN_AAPL_QUERY_ACCESSIONS]


@pytest.fixture(scope="module")
def golden_ledger(golden_packages):
    ledger, _metadata, report = parse_and_convert_golden_packages(golden_packages)
    assert report.ledger_sha256 == _LEDGER_SHA
    return ledger


@pytest.fixture(scope="module")
def golden_receipts(golden_packages, golden_ledger):
    return derive_confirmation_receipts(
        golden_ledger.events,
        system_available_at=_A4_AVAILABLE_AT,
        original_taxonomy_uris=original_concept_namespace_uris(golden_packages),
    )


def _bare_provider():
    return GoldenAaplFinancialQueryProvider(ROOT)


def _lineage_provider():
    return GoldenAaplFinancialQueryProvider(ROOT, lineage_evidence_available_at=_A4_AVAILABLE_AT)


# ---------------------------------------------------------------------------
# Source law: the v1 rule reproduces the accepted AAPL calibration exactly
# ---------------------------------------------------------------------------


def test_only_the_frozen_a1_a2_pair_participates():
    assert GOLDEN_AAPL_QUERY_ACCESSIONS == (_A1, _A2)


def test_confirmation_count_matches_accepted_a4r_census(golden_receipts, golden_ledger):
    """130 exact candidates, derived from source and never from the census JSON."""
    assert len(golden_receipts) == _EXPECTED_POSITIVE_CONFIRMATIONS
    overlap = {
        key
        for key, accessions in _by_logical_key(golden_ledger).items()
        if len(accessions) == 2
    }
    assert len(overlap) == _EXPECTED_OVERLAP_LOGICAL_KEYS
    assert all(item.is_positive_confirmation for item in golden_receipts)
    assert all(item.relation_type == "xbrl_confirmation" for item in golden_receipts)


def _by_logical_key(ledger):
    grouped: dict[str, dict[str, list]] = {}
    for event in ledger.events:
        grouped.setdefault(event.logical_key, {}).setdefault(event.source.accession, []).append(event)
    return grouped


def test_dimensioned_lineage_is_retained_not_discarded(golden_receipts, golden_ledger):
    """Sol amendment 2: source lineage is not metric eligibility."""
    by_id = {event.occurrence_id: event for event in golden_ledger.events}
    dimensioned = 0
    empty_dimension = 0
    for receipt in golden_receipts:
        child = by_id[receipt.child_occurrence_id]
        if child.context.explicit_dimensions or child.context.typed_dimensions:
            dimensioned += 1
        else:
            empty_dimension += 1
    assert dimensioned == 93
    assert empty_dimension == 37


def test_confirmation_is_never_a_fact_event_type(golden_ledger, golden_receipts):
    """A1/A2 occurrences stay FILED. Nothing is reminted or appended."""
    assert all(event.event_type.value == "filed" for event in golden_ledger.events)
    assert all(event.revision_of is None for event in golden_ledger.events)
    assert len(RawFactLedger(golden_ledger.events).events) == len(golden_ledger.events)


# ---------------------------------------------------------------------------
# §9.8 / §9.9 / §9.13 — the three accepted refusals
# ---------------------------------------------------------------------------


def _receipt_concepts(receipts, ledger):
    by_id = {event.occurrence_id: event for event in ledger.events}
    return {by_id[item.child_occurrence_id].concept_qname for item in receipts}


def test_changed_value_never_receives_confirmation(golden_receipts, golden_ledger):
    """§9.8: us-gaap:OtherAssetsNoncurrent 83,727M vs 72,634M."""
    assert "us-gaap:OtherAssetsNoncurrent" not in _receipt_concepts(golden_receipts, golden_ledger)


def test_precision_consistent_is_refused_by_exact_v1(golden_receipts, golden_ledger):
    """§9.9: us-gaap:LongTermDebt 90,678M/-6 vs 90,700M/-8; _duplicates_agree is true."""
    assert "us-gaap:LongTermDebt" not in _receipt_concepts(golden_receipts, golden_ledger)


def test_nil_pair_is_outside_v1(golden_receipts, golden_ledger):
    """§9.13: us-gaap:CommitmentsAndContingencies nil/nil."""
    assert "us-gaap:CommitmentsAndContingencies" not in _receipt_concepts(golden_receipts, golden_ledger)


def test_refusal_classes_are_named_honestly(golden_ledger):
    """The refusal taxonomy separates precision-consistency from a real change."""
    grouped = _by_logical_key(golden_ledger)
    seen = {}
    for accessions in grouped.values():
        if len(accessions) != 2:
            continue
        (_a, parent), (_b, child) = sorted(accessions.items())
        if parent[0].accepted_at > child[0].accepted_at:
            parent, child = child, parent
        reason = evaluate_confirmation(parent, child, require_taxonomy_uri=False)
        if reason is not None:
            seen.setdefault(reason, 0)
            seen[reason] += 1
    assert seen.get("changed_value") == 1
    assert seen.get("precision_consistent_unconfirmed") == 1
    assert seen.get("nil_confirmation_unspecified") == 1


# ---------------------------------------------------------------------------
# §9.10 — absent evidence is byte-identical FIF-3A3 / FIP1
# ---------------------------------------------------------------------------


def test_absent_evidence_keeps_accepted_hashes_byte_identical():
    provider = _bare_provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    assert tuple(dataset.lineage_evidence) == ()
    assert provider.conversion_report().ledger_sha256 == _LEDGER_SHA
    result = execute_financial_query(
        body=_body(
            metric_ids=_GOLDEN_METRICS,
            periods=_GOLDEN_PERIODS,
            source=_A3_SOURCE,
            recorded=_A3_RECORDED,
        ),
        provider=provider,
    )
    assert result.sha256 == _AAPL_QUERY_RESPONSE_SHA
    assert result.envelope["receipt"]["query_hash"] == _AAPL_QUERY_HASH
    assert "lineage" not in result.envelope


def test_attaching_evidence_does_not_move_the_a3_ledger_sha():
    provider = _lineage_provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    assert len(tuple(dataset.lineage_evidence)) == _EXPECTED_POSITIVE_CONFIRMATIONS
    assert provider.conversion_report().ledger_sha256 == _LEDGER_SHA


# ---------------------------------------------------------------------------
# §9.1 / §9.14 — a historical cutoff is never retroactively repaired
# ---------------------------------------------------------------------------


def test_historical_a3_cutoff_preserves_not_evaluable():
    provider = _lineage_provider()
    result = execute_financial_query(
        body=_body(
            metric_ids=_GOLDEN_METRICS,
            periods=_GOLDEN_PERIODS,
            source=_A3_SOURCE,
            recorded=_A3_RECORDED,
        ),
        provider=provider,
    )
    assert result.sha256 == _AAPL_QUERY_RESPONSE_SHA
    assert result.envelope["receipt"]["query_hash"] == _AAPL_QUERY_HASH
    assert "lineage" not in result.envelope

    comparative = execute_financial_query(
        body=_body(
            metric_ids=["total_assets"],
            periods=[_COMPARATIVE],
            source=_A3_SOURCE,
            recorded=_A3_RECORDED,
        ),
        provider=provider,
    )
    cell = _root_cell(comparative.envelope, "total_assets", start=None, end="2025-09-27")
    assert cell["state"] == "not_evaluable"
    assert cell["reason"] == "unlinked source vintages require an explicit typed revision lineage"


def test_rule_clock_floor_refuses_a_backdated_receipt(golden_packages, golden_ledger):
    """§8: the research census timestamp cannot authorize runtime lineage."""
    uris = original_concept_namespace_uris(golden_packages)
    with pytest.raises(LineageEvidenceError):
        derive_confirmation_receipts(
            golden_ledger.events,
            system_available_at=CONFIRMATION_RULE_AVAILABLE_AT.replace(day=24),
            original_taxonomy_uris=uris,
        )


# ---------------------------------------------------------------------------
# §9.2 / §9.3 / §9.4 / §9.5 — policy isolation after the receipt is visible
# ---------------------------------------------------------------------------


def _comparative_cell(selection):
    result = execute_financial_query(
        body=_body(
            metric_ids=["total_assets"],
            periods=[_COMPARATIVE],
            source=_A4_SOURCE,
            recorded=_A4_RECORDED,
            selection=selection,
        ),
        provider=_lineage_provider(),
    )
    return result, _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")


def test_latest_known_as_of_resolves_through_the_confirmed_child():
    """§9.2: VALUE 359,241M selected from the A2 FILED occurrence."""
    _result, cell = _comparative_cell("latest_known_as_of")
    assert cell["state"] == "value"
    assert cell["value"] == "359241000000"
    provenance = cell["provenance"]
    assert provenance["source_occurrence_ids"] == [_A2_ASSETS_OCCURRENCE]
    assert provenance["accession"] == _A2
    assert provenance["form"] == "10-Q"


def test_as_reported_still_selects_the_original_filed_root():
    """§9.3: confirmation never moves AS_REPORTED off the first filing."""
    _result, cell = _comparative_cell("as_reported")
    assert cell["state"] == "value"
    assert cell["value"] == "359241000000"
    provenance = cell["provenance"]
    assert provenance["source_occurrence_ids"] == [_A1_ASSETS_OCCURRENCE]
    assert provenance["accession"] == _A1
    assert provenance["form"] == "10-K"


def test_latest_restated_ignores_confirmation():
    """§9.4: a confirmation is not a reported revision vintage."""
    _result, cell = _comparative_cell("latest_restated")
    assert cell["state"] == "missing"
    assert cell["reason"] == "no eligible explicitly typed reported revision vintage"


def test_confirmation_does_not_advertise_a_revision():
    """§9.5: no confirmation row reaches revision projection; event_type stays filed."""
    from engine.fundamental_forensics.financial_intelligence_packet import (
        REPORTED_REVISION_EVENT_TYPES,
    )
    from engine.fundamental_forensics.query import _REPORTED_REVISION_EVENT_TYPES

    provider = _lineage_provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    assert all(event.event_type.value == "filed" for event in dataset.ledger.events)
    assert all(
        item.value != "xbrl_confirmation"
        for item in (*REPORTED_REVISION_EVENT_TYPES, *_REPORTED_REVISION_EVENT_TYPES)
    )
    # Every reported-revision row requires revision_of; no golden occurrence has one.
    assert all(event.revision_of is None for event in dataset.ledger.events)


def test_lineage_disclosure_names_the_supporting_filing():
    """A user-facing answer stays receipt-bearing about the source relation."""
    result, cell = _comparative_cell("latest_known_as_of")
    lineage = result.envelope["lineage"]
    assert lineage["relation"] == "xbrl_confirmation"
    assert lineage["is_reported_revision"] is False
    confirmations = lineage["confirmations"]
    assert len(confirmations) == 1
    row = confirmations[0]
    assert row["parent_occurrence_id"] == _A1_ASSETS_OCCURRENCE
    assert row["child_occurrence_id"] == _A2_ASSETS_OCCURRENCE
    assert row["comparison_basis"] == "exact_parsed_value_and_accuracy_tokens"
    assert row["positive_evidence"]["parent_accession"] == _A1
    assert row["positive_evidence"]["child_accession"] == _A2
    assert row["positive_evidence"]["parsed_value"] == "359241000000"
    assert row["positive_evidence"]["parent_taxonomy_uri"] == "http://fasb.org/us-gaap/2025"
    assert row["positive_evidence"]["child_taxonomy_uri"] == "http://fasb.org/us-gaap/2025"
    assert row["source_known_at"] == "2026-07-31T10:01:02.000000Z"
    assert row["refusal_reason"] is None


# ---------------------------------------------------------------------------
# §9.6 / §9.11 / §9.12 / §9.15 — hostile cases fail closed
# ---------------------------------------------------------------------------


def test_mutating_the_confirmed_child_value_restores_not_evaluable(
    golden_packages, golden_ledger, golden_receipts
):
    """§9.6: evidence is re-proved at query time; no silent interval rescue."""
    from engine.fundamental_forensics.query import BitemporalMetricQueryEngine
    from engine.fundamental_forensics.query import QueryPolicy

    mutated_events = []
    for event in golden_ledger.events:
        if event.occurrence_id == _A2_ASSETS_OCCURRENCE:
            event = replace(event, parsed_value="359241000001", occurrence_id=None)
        mutated_events.append(event)
    mutated = RawFactLedger(tuple(mutated_events))
    surviving = tuple(
        item
        for item in golden_receipts
        if item.child_occurrence_id in {e.occurrence_id for e in mutated.events}
        and item.parent_occurrence_id in {e.occurrence_id for e in mutated.events}
    )
    # The mutated child no longer carries the receipt's occurrence id at all,
    # so the bundle is mis-bound and admission itself fail-closes.
    with pytest.raises(LineageEvidenceError):
        BitemporalMetricQueryEngine(
            mutated,
            _lineage_provider().resolve(_GOLDEN_ENTITY).registry,
            entities={"AAPL": "0000320193"},
            lineage_evidence=golden_receipts,
        )
    assert len(surviving) < len(golden_receipts)


def test_refused_receipt_is_unavailable_at_runtime(golden_receipts):
    """§9.15: only accepted positive immutable relations are legal."""
    sample = golden_receipts[0]
    with pytest.raises(LineageEvidenceError):
        LineageEvidenceReceipt(
            parent_occurrence_id=sample.parent_occurrence_id,
            child_occurrence_id=sample.child_occurrence_id,
            logical_key=sample.logical_key,
            source_known_at=sample.source_known_at,
            system_available_at=sample.system_available_at,
            refusal_reason="changed_value",
            relation_type="xbrl_confirmation",
        )


def test_hostile_extra_evidence_keys_are_unavailable(golden_receipts):
    """§9.11: extra keys / true attestation flags fail closed, not partially."""
    sample = golden_receipts[0]
    hostile = dict(sample.positive_evidence)
    hostile["production_issuer_service"] = True
    with pytest.raises(LineageEvidenceError):
        LineageEvidenceReceipt(
            parent_occurrence_id=sample.parent_occurrence_id,
            child_occurrence_id=sample.child_occurrence_id,
            logical_key=sample.logical_key,
            source_known_at=sample.source_known_at,
            system_available_at=sample.system_available_at,
            positive_evidence=hostile,
        )


def test_evidence_for_an_unknown_occurrence_is_unavailable(golden_receipts):
    """A bundle bound to facts this ledger does not hold is a provider fault."""
    from engine.fundamental_forensics.query import BitemporalMetricQueryEngine

    provider = _lineage_provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    stray = replace(golden_receipts[0], parent_occurrence_id="rawfact_" + "0" * 64, receipt_id="", evidence_digest="")
    with pytest.raises(LineageEvidenceError):
        BitemporalMetricQueryEngine(
            dataset.ledger,
            dataset.registry,
            entities={"AAPL": "0000320193"},
            lineage_evidence=(stray,),
        )


def test_query_before_the_child_is_accepted_cannot_see_the_receipt():
    """§9.12: the source clock still gates everything."""
    result = execute_financial_query(
        body=_body(
            metric_ids=["total_assets"],
            periods=[_COMPARATIVE],
            source="2026-07-30T00:00:00Z",
            recorded=_A4_RECORDED,
        ),
        provider=_lineage_provider(),
    )
    cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
    assert cell["state"] == "value"
    assert cell["provenance"]["source_occurrence_ids"] == [_A1_ASSETS_OCCURRENCE]
    assert "lineage" not in result.envelope


def test_http_transport_fail_closes_a_malformed_bundle():
    """A malformed bundle is a private unavailable, never a leaked 400 body."""

    class _HostileProvider:
        def resolve(self, entity_id):
            dataset = _lineage_provider().resolve(entity_id)
            return replace(dataset, lineage_evidence=("not-a-receipt",))

    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_query(
            body=_body(
                metric_ids=["total_assets"],
                periods=[_COMPARATIVE],
                source=_A4_SOURCE,
                recorded=_A4_RECORDED,
            ),
            provider=_HostileProvider(),
        )


# ---------------------------------------------------------------------------
# §9.7 — a third filing of one logical key has no unique parent
# ---------------------------------------------------------------------------


def _synthetic_fact(*, accession, body, value="359241000000", accepted_at, decimals="-6"):
    from engine.fundamental_forensics.raw_ledger import (
        FactContext,
        FactUnit,
        SourceIdentity,
        make_raw_fact,
    )

    return make_raw_fact(
        source=SourceIdentity(
            source="sec-edgar",
            entity_id="0000320193",
            accession=accession,
            document_id=f"doc-{accession}.htm",
            body_sha256=body,
            source_url="https://www.sec.gov/Archives/example",
        ),
        concept_qname="us-gaap:Assets",
        context=FactContext(
            context_id="ctx",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier="0000320193",
            instant="2025-09-27",
        ),
        unit=FactUnit("usd", ["iso4217:USD"]),
        raw_token=value,
        parsed_value=value,
        decimals=decimals,
        source_span=(10, 20),
        accepted_at=accepted_at,
        recorded_at="2026-08-23T00:00:00Z",
    )


def test_three_filings_of_one_logical_key_have_no_unique_parent():
    """§9.7: v1 admits one parent and one child. A third filing fails closed."""
    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at="2025-10-31T10:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at="2026-01-31T10:00:00Z"),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at="2026-07-31T10:00:00Z"),
    ]
    uris = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://fasb.org/us-gaap/2025"
        for fact in facts
    }
    assert derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=uris
    ) == ()
    # Two of the same three still confirm, so the refusal is the third filing
    # and not an unrelated defect in the rule.
    pair = facts[:2]
    assert len(
        derive_confirmation_receipts(
            pair, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=uris
        )
    ) == 1


def test_query_time_refuses_a_chained_three_filing_component():
    """A hand-built bundle cannot chain A->B->C into one effective root."""
    from engine.fundamental_forensics.query import BitemporalMetricQueryEngine

    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at="2025-10-31T10:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at="2026-01-31T10:00:00Z"),
        _synthetic_fact(accession="0003", body="c" * 64, accepted_at="2026-07-31T10:00:00Z"),
    ]
    uris = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://fasb.org/us-gaap/2025"
        for fact in facts
    }
    chained = (
        derive_confirmation_receipts(
            facts[:2], system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=uris
        )
        + derive_confirmation_receipts(
            facts[1:], system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=uris
        )
    )
    assert len(chained) == 2

    provider = _lineage_provider()
    registry = provider.resolve(_GOLDEN_ENTITY).registry
    # A bundle spanning three filings for one logical key is refused outright.
    with pytest.raises(LineageEvidenceError):
        BitemporalMetricQueryEngine(
            RawFactLedger(tuple(facts)),
            registry,
            entities={"AAPL": "0000320193"},
            lineage_evidence=chained,
        )
    # And the surviving two-filing bundle still leaves the third unlinked.
    from engine.fundamental_forensics.query import QueryPolicy

    engine = BitemporalMetricQueryEngine(
        RawFactLedger(tuple(facts)),
        registry,
        entities={"AAPL": "0000320193"},
        lineage_evidence=chained[:1],
    )
    policy = QueryPolicy(
        source_snapshot_at=_A4_SOURCE,
        recorded_at=_A4_RECORDED,
        selection="latest_known_as_of",
    )
    selection = engine._select_source_group(tuple(facts), policy)
    assert selection.state.value == "not_evaluable"
    assert selection.reason == "unlinked source vintages require an explicit typed revision lineage"


def test_forged_taxonomy_uri_is_refused():
    """Guard 11 believes an attested URI only if policy approves it.

    Two matching but invented namespace URIs are not evidence: the URI must be
    in TAXONOMY_NAMESPACE_POLICY and must resolve to the prefix the retained
    concept_qname already carries.
    """
    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at="2025-10-31T10:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at="2026-07-31T10:00:00Z"),
    ]
    forged = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://attacker.example/v99"
        for fact in facts
    }
    assert derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=forged
    ) == ()

    # A real namespace that disagrees with the concept is also refused.
    wrong_family = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://xbrl.sec.gov/dei/2025"
        for fact in facts
    }
    assert derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=wrong_family
    ) == ()

    # The genuine namespace still mints.
    honest = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://fasb.org/us-gaap/2025"
        for fact in facts
    }
    assert len(
        derive_confirmation_receipts(
            facts, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=honest
        )
    ) == 1


def test_forged_uri_is_also_refused_at_admission():
    """The same forgery cannot be smuggled in on a hand-built bundle."""
    from engine.fundamental_forensics.query import BitemporalMetricQueryEngine

    facts = [
        _synthetic_fact(accession="0001", body="a" * 64, accepted_at="2025-10-31T10:00:00Z"),
        _synthetic_fact(accession="0002", body="b" * 64, accepted_at="2026-07-31T10:00:00Z"),
    ]
    honest = {
        (fact.source.accession, fact.source_occurrence_key or ""): "http://fasb.org/us-gaap/2025"
        for fact in facts
    }
    genuine = derive_confirmation_receipts(
        facts, system_available_at=_A4_AVAILABLE_AT, original_taxonomy_uris=honest
    )[0]
    tampered_evidence = dict(genuine.positive_evidence)
    tampered_evidence["parent_taxonomy_uri"] = "http://attacker.example/v99"
    tampered_evidence["child_taxonomy_uri"] = "http://attacker.example/v99"
    tampered = LineageEvidenceReceipt(
        parent_occurrence_id=genuine.parent_occurrence_id,
        child_occurrence_id=genuine.child_occurrence_id,
        logical_key=genuine.logical_key,
        source_known_at=genuine.source_known_at,
        system_available_at=genuine.system_available_at,
        positive_evidence=tampered_evidence,
    )
    registry = _lineage_provider().resolve(_GOLDEN_ENTITY).registry
    with pytest.raises(LineageEvidenceError):
        BitemporalMetricQueryEngine(
            RawFactLedger(tuple(facts)),
            registry,
            entities={"AAPL": "0000320193"},
            lineage_evidence=(tampered,),
        )
