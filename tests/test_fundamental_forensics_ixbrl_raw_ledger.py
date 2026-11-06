"""FIF-3A3: real AAPL iXBRL → RawFactLedger → governed query convergence."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    GOLDEN_AAPL_QUERY_ACCESSIONS,
    GoldenAaplFinancialQueryProvider,
    canonicalize_clark_qname,
    parse_and_convert_golden_packages,
)
from engine.fundamental_forensics.models import stable_id
from engine.fundamental_forensics.query_service import (
    FinancialQueryDataset,
    FinancialQueryUnavailableError,
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.raw_ledger import RawFactLedger
from engine.fundamental_forensics.sec_document_spine import FilingManifestError, sec_document_id
from engine.fundamental_forensics.statement_graph import (
    GOLDEN_AAPL_FIXTURES,
    load_golden_aapl_package,
)
from engine.fundamental_forensics.statement_service import (
    GoldenAaplStatementProvider,
    execute_financial_statements,
)

ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_ENTITY = "ISS:US-XNAS-AAPL"
_A1 = "0000320193-25-000079"
_A2 = "0000320193-26-000020"
_A1_PRIMARY = "aapl-20250927.htm"
_A2_PRIMARY = "aapl-20260627.htm"
_CIK = "0000320193"
_A1_DOCUMENT_ID = "sec_document_d23a609841f9a32489dd7abc952d39622540f8a24905612bda1d43e5577860b8"
_A2_DOCUMENT_ID = "sec_document_29a36fa46a0bc5309f17bd254c3061f20c4b3de7e05898a2fec9ee58f89e8760"

_AAPL_QUERY_RESPONSE_SHA = "fbae153c5fccd26b747be10239fe4b5fcd0e30113604597d16b01bf31b875c48"
_AAPL_QUERY_HASH = "a4b04952c3df3e50936d4229b018f0a7f7035edb24139ba936aa58f913515920"
_LEDGER_SHA = "ba149bd55d929d843f353e91bbf68147791fb8b4a20c258426ea2eb7527019d8"
_A1_STATEMENT_SHA = "25e5562e81cb80bd42d0feb544c212c4471e11736601aaee418a60981a457184"
_A2_STATEMENT_SHA = "b98602a299996ff7ea58b842364031547df795d1458b51134eef0e37159b7918"
# The five FIP1 query hashes were re-captured at the FIF G0-r1p3 re-pin
# commit e94ba62aa89 with the same hermetic industrial resolver the FIP1 packet-service
# tests inject: the values are byte-equal to that already-pinned family
# (tests/test_fundamental_forensics_financial_packet_service.py:78,
# tests/test_fundamental_forensics_financial_revision_service.py:70) over the
# same scenario, per the G0-r1p3 seat ruling on same-input families.
_HASH_AS_REPORTED_T1_T2 = "58d438ec81d287f81e6981cf01ac6d16d57cf50689cc826cad39962742efa821"
_HASH_LATEST_KNOWN_T1_T2 = "f275a7e02aff6e1119f1275365549e1fa9aa2d3f45dbc3cd0f4ba5fdb76f1d37"
_HASH_LATEST_KNOWN_T3 = "2f8d30baf2d49aef0cc6936613eca1f9aa980e10ed56da135a75dd4238349915"
_HASH_LATEST_RESTATED_T3 = "531309e192ac923e466365b05380a197f67d6df01c1d5fd9062a0e93aaf20b9f"
_HASH_MIXED_T3 = "26a7ed7d95f861d3352c3a7e5fb6a0f52833ccf69947b10ca9da1f9662c44133"
# The rich packet keeps the production default (no injected resolver): FIP1
# has no shipped coverage record, so gross_margin (class-restricted under the
# G0 catalog) reads NOT_EVALUABLE(issuer_class_unknown) and the packet's
# digest layer moved with the catalog; re-captured at the same commit e94ba62aa89.
_RICH_PACKET_ID = "fip_5d77c1349de4f829db2c422a"
_RICH_CONTENT_SHA = "5d77c1349de4f829db2c422a3000049cb12b6f0c16dbcd57686a0c0cd41c0af0"
_RICH_RESPONSE_SHA = "a9c5a8657e7c5cb7e6789cd6d2ea4f78a1c14100c33a00d959856d7375045ca8"

# FIP1 is a synthetic industrial issuer with no shipped coverage record, so
# the five-hash family injects its SIC hermetically (same shape as the FIP1
# packet-service tests); the fixture ledger's entity id is its CIK.
_FIP1_CIK = "0000999999"
_INDUSTRIAL_SIC = "3571"


def _fip1_issuer_sic_resolver(cik: str) -> str | None:
    return _INDUSTRIAL_SIC if cik == _FIP1_CIK else None

VISIBLE_SOURCE = "2026-08-01T00:00:00Z"
VISIBLE_RECORDED = "2026-08-23T12:00:00Z"
A1_ACCEPT = "2025-10-31T10:01:26.000Z"

FY2025_REV = {
    "kind": "duration",
    "start": "2024-09-29",
    "end": "2025-09-27",
    "label": "FY2025",
}
Q3_REV = {
    "kind": "duration",
    "start": "2026-03-29",
    "end": "2026-06-27",
    "label": "FY2026Q3",
}
YTD_REV = {
    "kind": "duration",
    "start": "2025-09-28",
    "end": "2026-06-27",
    "label": "FY2026YTD",
}
A2_ASSETS = {
    "kind": "instant",
    "start": None,
    "end": "2026-06-27",
    "label": "2026-06-27",
}
A1_ASSETS_COMPARATIVE = {
    "kind": "instant",
    "start": None,
    "end": "2025-09-27",
    "label": "2025-09-27",
}

# FIF-3A4 (DEC:FIF-3A4R-CROSS-FILING-LINEAGE-ACCEPTED-ON-MAIN, protocol §10)
# commissions exactly one product change to ``query.py``: effective-root
# unification in ``_select_source_group`` from cutoff-visible lineage evidence.
# The byte-freeze on that one file was the *A4R research wave's* self-restraint,
# not a permanent kernel law, so it is released here for the authorized change.
# What the freeze actually protected — accepted A3 source identity — is still
# asserted directly and independently by ``_LEDGER_SHA``, ``_AAPL_QUERY_HASH``
# and ``_AAPL_QUERY_RESPONSE_SHA`` in this file, and by the FIF-3A4 battery in
# ``tests/test_fundamental_forensics_cross_filing_lineage.py``.
#
# FIF G0 shared-kernel integrator (seat ruling 2026-10-13, frozen spec
# e7b0286c) releases two more of these self-restraint freezes for the
# authorized G0 change: ``engine/fundamental_forensics/financial_intelligence_packet.py``
# (G0 wired the optional issuer-SIC resolver seam through the production
# entity construction) leaves ``_FROZEN_FIF1``, and
# ``engine/fundamental_forensics/metric_registry.py`` (G0 extended the metric
# catalog contract with issuer-class applicability) leaves ``_FROZEN_KERNEL``.
# The golden fixture ``expected_financial_intelligence_packet_v1.json`` also
# leaves ``_FROZEN_FIF1`` for the P2-E G-c re-capture: its protection is
# asserted directly by the golden battery (schema + content addressing +
# canonical rebuild equality in
# tests/test_fundamental_forensics_financial_intelligence_packet.py:540-546 and
# law11 cross-process byte equality :444-449) and by the packet_id regression
# witness in tests/test_fundamental_forensics_financial_packet_service.py:200.
# What those freezes protected is still asserted directly and independently:
# packet schema validity and content addressing by the golden battery, catalog
# digests by ``_PIN``/``PINNED_*`` captures in
# tests/test_fundamental_forensics_metric_qualification.py, and this file's
# ``_AAPL_QUERY_HASH`` / ``_AAPL_QUERY_RESPONSE_SHA`` / ``_LEDGER_SHA`` pins.
# ``raw_ledger.py`` remains byte-frozen (G0 does not touch occurrence
# identity, ``logical_key``, ``_duplicates_agree``, or ``FactEventType``
# membership), and so do the packet schema and the synthetic fixture package.
_FROZEN_FIF1 = (
    "contracts/financial_intelligence_packet.schema.json",
    "engine/fundamental_forensics/synthetic_filing_package.py",
)
_FROZEN_KERNEL = (
    "engine/fundamental_forensics/raw_ledger.py",
)

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _query_body(*, metric_ids, periods, source=VISIBLE_SOURCE, recorded=VISIBLE_RECORDED, entity_id=_GOLDEN_ENTITY):
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": entity_id,
            "policy": {
                "selection": "latest_known_as_of",
                "source_snapshot_at": source,
                "recorded_at": recorded,
            },
            "metric_ids": metric_ids,
            "periods": periods,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _provider() -> GoldenAaplFinancialQueryProvider:
    return GoldenAaplFinancialQueryProvider(ROOT)


def _root_cell(envelope: dict, metric_id: str, *, start: str | None, end: str) -> dict:
    receipt = envelope["receipt"]
    roots = set(receipt["root_cell_ids"])
    matches = []
    for node in receipt["nodes"]:
        if node["cell_id"] not in roots:
            continue
        if node["metric_id"] != metric_id:
            continue
        period = node["period"]
        if period.get("start") == start and period.get("end") == end:
            matches.append(node)
    assert len(matches) == 1, (metric_id, start, end, [item["period"] for item in matches])
    return matches[0]


def _statement_cell(envelope: dict, metric_id: str, *, start: str | None, end: str) -> dict:
    for statement in envelope["statements"]:
        for row in statement["rows"]:
            if row.get("standardized_metric_id") != metric_id:
                continue
            if row.get("mapping_state") != "mapped":
                continue
            dims = row.get("cells", [{}])[0].get("dimensions") if row.get("cells") else None
            if dims:
                continue
            for cell in row["cells"]:
                period = cell.get("period") or {}
                if period.get("start") == start and period.get("end") == end:
                    if cell.get("quality_state") == "available" and cell.get("value") is not None:
                        return cell
    raise AssertionError(f"no statement cell for {metric_id} {start}->{end}")


def test_qname_bridge_reuses_attestation_namespace_policy() -> None:
    assert (
        canonicalize_clark_qname("{http://fasb.org/us-gaap/2025}Assets")
        == "us-gaap:Assets"
    )
    assert canonicalize_clark_qname("{http://xbrl.sec.gov/dei/2025}EntityCentralIndexKey") == (
        "dei:EntityCentralIndexKey"
    )
    assert canonicalize_clark_qname("{http://www.xbrl.org/2003/iso4217}USD") == "iso4217:USD"
    assert canonicalize_clark_qname("{http://www.xbrl.org/2003/instance}shares") == "xbrli:shares"
    custom = "{http://www.apple.com/20250927}RevenueFromContractWithCustomerExcludingAssessedTax"
    assert canonicalize_clark_qname(custom) == custom
    srt = "{http://fasb.org/srt/2025}ProductOrServiceAxis"
    assert canonicalize_clark_qname(srt) == srt
    local_only = "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert canonicalize_clark_qname(local_only) == local_only


def test_document_id_reuses_sec_spine_formula() -> None:
    a1 = sec_document_id(_CIK, _A1, "primary", _A1_PRIMARY)
    a2 = sec_document_id(_CIK, _A2, "primary", _A2_PRIMARY)
    assert a1 == _A1_DOCUMENT_ID
    assert a2 == _A2_DOCUMENT_ID
    assert a1 == stable_id("sec_document", _CIK, _A1, "primary", _A1_PRIMARY)
    assert a2 == stable_id("sec_document", _CIK, _A2, "primary", _A2_PRIMARY)
    assert sec_document_id("320193", _A1, "primary", _A1_PRIMARY) == a1
    assert sec_document_id(320193, _A1, "primary", _A1_PRIMARY) == a1
    assert a1 != a2
    with pytest.raises(FilingManifestError):
        sec_document_id(_CIK, "not-an-accession", "primary", _A1_PRIMARY)
    with pytest.raises(FilingManifestError):
        sec_document_id(_CIK, _A1, "attachment", _A1_PRIMARY)
    with pytest.raises(FilingManifestError):
        sec_document_id(_CIK, _A1, "primary", "../" + _A1_PRIMARY)


def test_future_statement_fixture_cannot_enter_a3_ledger(monkeypatch) -> None:
    hostile = "0000320193-99-999999"
    expanded = dict(GOLDEN_AAPL_FIXTURES)
    expanded[hostile] = GOLDEN_AAPL_FIXTURES[_A1]
    monkeypatch.setattr(
        "engine.fundamental_forensics.statement_graph.GOLDEN_AAPL_FIXTURES",
        expanded,
    )
    assert hostile in expanded
    assert GOLDEN_AAPL_QUERY_ACCESSIONS == (_A1, _A2)
    provider = GoldenAaplFinancialQueryProvider(ROOT)
    dataset = provider.resolve(_GOLDEN_ENTITY)
    report = provider.conversion_report()
    assert report.ledger_sha256 == _LEDGER_SHA
    assert set(dataset.filing_metadata) == {_A1, _A2}
    assert hostile not in dataset.filing_metadata
    assert all(event.source.accession in {_A1, _A2} for event in dataset.ledger.events)
    result = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue", "total_assets", "gross_margin", "net_cash_from_operating_activities"],
            periods=[FY2025_REV, Q3_REV, YTD_REV, A2_ASSETS],
        ),
        provider=provider,
    )
    assert result.sha256 == _AAPL_QUERY_RESPONSE_SHA
    assert result.envelope["receipt"]["query_hash"] == _AAPL_QUERY_HASH


def test_conversion_report_is_complete_and_deterministic() -> None:
    from engine.fundamental_forensics.raw_ledger import canonical_json

    packages = [load_golden_aapl_package(ROOT, accession=item) for item in GOLDEN_AAPL_QUERY_ACCESSIONS]
    first = parse_and_convert_golden_packages(packages)
    second = parse_and_convert_golden_packages(packages)
    ledger, metadata, report = first
    assert report.ledger_sha256 == _LEDGER_SHA
    assert second[2].ledger_sha256 == report.ledger_sha256
    assert report.ledger_sha256 == hashlib.sha256(
        canonical_json(ledger.to_dict()).encode("utf-8")
    ).hexdigest()
    assert set(metadata) == {_A1, _A2}
    assert len(report.filings) == 2
    for item in report.filings:
        numeric_excluded = sum(
            count
            for reason, count in item.excluded.items()
            if reason not in {"nonnumeric", "fraction", "unsupported_kind"}
        )
        assert item.represented_count + numeric_excluded == item.parser_numeric_fact_count
        assert item.ledger_occurrence_count == item.represented_count
        assert item.parser_numeric_fact_count > 0
        assert item.represented_count > 0
    assert ledger.events
    assert any("us-gaap" in item or "fasb.org/us-gaap" in item for item in report.source_namespace_families)


def test_raw_occurrences_preserve_source_identity_and_clocks() -> None:
    provider = _provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    report = provider.conversion_report()
    assert report.filings
    a1_events = [item for item in dataset.ledger.events if item.source.accession == _A1]
    a2_events = [item for item in dataset.ledger.events if item.source.accession == _A2]
    assert a1_events and a2_events
    for event in a1_events:
        assert event.source.source == "sec-edgar"
        assert event.source.entity_id == _CIK
        assert event.source.document_id == sec_document_id(_CIK, _A1, "primary", _A1_PRIMARY)
        assert event.source.source_url.endswith(f"/{_A1_PRIMARY}")
        assert event.event_type.value == "filed"
        assert event.revision_of is None
        assert event.clocks.mapping_available_at is None
        assert event.clocks.computed_at is None
        assert event.clocks.published_at is None
        assert event.source_occurrence_key
    meta = dataset.filing_metadata[_A1]
    assert str(meta.available_at).startswith("2026-08-23 00:32:31")
    assert meta.form == "10-K"
    a1_package = load_golden_aapl_package(ROOT, accession=_A1)
    witness_rel = a1_package.manifest["acceptance_witness"]["path"]
    witness = json.loads(
        (ROOT / "tests/fixtures/fundamental_forensics/aapl_10k_2025" / witness_rel).read_text(
            encoding="utf-8"
        )
    )
    assert witness["acceptanceDateTime"] == A1_ACCEPT
    assert meta.content_sha256
    assert dataset.delivery == {
        "kind": "committed_golden_fixture",
        "attested": False,
        "production_issuer_service": False,
    }


def test_required_governed_aapl_values() -> None:
    result = execute_financial_query(
        body=_query_body(
            metric_ids=[
                "revenue",
                "total_assets",
                "net_cash_from_operating_activities",
                "gross_margin",
            ],
            periods=[FY2025_REV, Q3_REV, YTD_REV, A2_ASSETS],
        ),
        provider=_provider(),
    )
    assert result.sha256 == _AAPL_QUERY_RESPONSE_SHA
    assert result.envelope["receipt"]["query_hash"] == _AAPL_QUERY_HASH
    assert result.envelope["authority"] == {"class": "context_only", "display_only": True}
    assert result.envelope["delivery"] == {
        "kind": "committed_golden_fixture",
        "attested": False,
        "production_issuer_service": False,
    }
    revenue_fy = _root_cell(result.envelope, "revenue", start="2024-09-29", end="2025-09-27")
    revenue_q3 = _root_cell(result.envelope, "revenue", start="2026-03-29", end="2026-06-27")
    revenue_ytd = _root_cell(result.envelope, "revenue", start="2025-09-28", end="2026-06-27")
    assets = _root_cell(result.envelope, "total_assets", start=None, end="2026-06-27")
    cfo = _root_cell(
        result.envelope,
        "net_cash_from_operating_activities",
        start="2025-09-28",
        end="2026-06-27",
    )
    assert revenue_fy["state"] == "value"
    assert revenue_fy["value"] == "416161000000"
    assert revenue_q3["state"] == "value"
    assert revenue_q3["value"] == "109417000000"
    assert revenue_ytd["state"] == "value"
    assert revenue_ytd["value"] == "364357000000"
    assert assets["state"] == "value"
    assert assets["value"] == "383266000000"
    assert cfo["state"] == "value"
    assert cfo["value"] == "116996000000"
    margin = _root_cell(result.envelope, "gross_margin", start="2024-09-29", end="2025-09-27")
    assert margin["state"] == "value"
    assert margin["provenance"]["formula_rule_id"]


def test_statement_query_reconciliation_for_direct_metrics() -> None:
    provider = _provider()
    query = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue", "total_assets", "net_cash_from_operating_activities"],
            periods=[FY2025_REV, Q3_REV, YTD_REV, A2_ASSETS],
        ),
        provider=provider,
    )
    a1 = execute_financial_statements(
        body=json.dumps(
            {
                "schema": "fundamental_forensics.financial_statement_request/v1",
                "entity_id": _GOLDEN_ENTITY,
                "accession": _A1,
            },
            separators=(",", ":"),
        ).encode("utf-8"),
        repo_root=ROOT,
        provider=GoldenAaplStatementProvider(ROOT),
    )
    a2 = execute_financial_statements(
        body=json.dumps(
            {
                "schema": "fundamental_forensics.financial_statement_request/v1",
                "entity_id": _GOLDEN_ENTITY,
                "accession": _A2,
            },
            separators=(",", ":"),
        ).encode("utf-8"),
        repo_root=ROOT,
        provider=GoldenAaplStatementProvider(ROOT),
    )
    assert a1.sha256 == _A1_STATEMENT_SHA
    assert a2.sha256 == _A2_STATEMENT_SHA
    pairs = [
        ("revenue", "2024-09-29", "2025-09-27", a1.envelope, _A1),
        ("revenue", "2026-03-29", "2026-06-27", a2.envelope, _A2),
        ("revenue", "2025-09-28", "2026-06-27", a2.envelope, _A2),
        ("total_assets", None, "2026-06-27", a2.envelope, _A2),
        ("net_cash_from_operating_activities", "2025-09-28", "2026-06-27", a2.envelope, _A2),
    ]
    for metric_id, start, end, statement, accession in pairs:
        qcell = _root_cell(query.envelope, metric_id, start=start, end=end)
        scell = _statement_cell(statement, metric_id, start=start, end=end)
        raw = qcell["provenance"]["selected_raw_fact"]
        assert raw is not None
        assert raw["source"]["accession"] == accession
        assert raw["source"]["accession"] == statement["filing"]["accession"]
        assert raw["parsed_value"] == str(scell["value"])
        assert raw["source"]["body_sha256"] == scell["source_receipt"]["content_sha256"]
        assert list(raw["source_span"]) == [
            scell["source_receipt"]["source_span"]["start"],
            scell["source_receipt"]["source_span"]["end"],
        ]
        assert raw["source_occurrence_key"] == scell["source_receipt"]["fact_id"]
        period = raw["context"]
        if start is None:
            assert period["instant"] == end
        else:
            assert period["start"] == start
            assert period["end"] == end


def test_pit_cutoffs_hide_future_knowledge() -> None:
    provider = _provider()
    before_accept = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue"],
            periods=[FY2025_REV],
            source="2025-10-31T10:01:25Z",
            recorded=VISIBLE_RECORDED,
        ),
        provider=provider,
    )
    hidden = _root_cell(before_accept.envelope, "revenue", start="2024-09-29", end="2025-09-27")
    assert hidden["state"] == "missing"
    dumped = json.dumps(hidden)
    assert hidden["provenance"]["selected_raw_fact"] is None
    assert not hidden["provenance"].get("source_occurrence_ids")
    assert A1_ACCEPT not in dumped

    before_recorded = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue"],
            periods=[FY2025_REV],
            source="2025-10-31T12:00:00Z",
            recorded="2026-08-23T00:32:30Z",
        ),
        provider=provider,
    )
    still_hidden = _root_cell(before_recorded.envelope, "revenue", start="2024-09-29", end="2025-09-27")
    assert still_hidden["state"] == "missing"
    assert still_hidden["provenance"]["selected_raw_fact"] is None

    a2_before_accept = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue"],
            periods=[Q3_REV],
            source="2026-07-31T10:01:01Z",
            recorded=VISIBLE_RECORDED,
        ),
        provider=provider,
    )
    assert _root_cell(a2_before_accept.envelope, "revenue", start="2026-03-29", end="2026-06-27")["state"] == "missing"

    a2_before_recorded = execute_financial_query(
        body=_query_body(
            metric_ids=["revenue"],
            periods=[Q3_REV],
            source="2026-07-31T12:00:00Z",
            recorded="2026-08-23T07:02:12Z",
        ),
        provider=provider,
    )
    assert _root_cell(a2_before_recorded.envelope, "revenue", start="2026-03-29", end="2026-06-27")["state"] == "missing"


def test_unlinked_vintages_are_not_evaluable() -> None:
    result = execute_financial_query(
        body=_query_body(metric_ids=["total_assets"], periods=[A1_ASSETS_COMPARATIVE]),
        provider=_provider(),
    )
    cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
    assert cell["state"] == "not_evaluable"
    assert cell["reason"] == "unlinked source vintages require an explicit typed revision lineage"
    raw_events = [
        event
        for event in _provider().resolve(_GOLDEN_ENTITY).ledger.events
        if event.concept_qname == "us-gaap:Assets"
        and event.context.instant == date(2025, 9, 27)
        and event.dimensions_known
        and not event.context.explicit_dimensions
        and not event.context.typed_dimensions
    ]
    accessions = {event.source.accession for event in raw_events}
    assert accessions == {_A1, _A2}
    assert all(event.revision_of is None for event in raw_events)


def test_agreeing_and_conflicting_duplicates() -> None:
    packages = [load_golden_aapl_package(ROOT, accession=item) for item in GOLDEN_AAPL_QUERY_ACCESSIONS]
    ledger, metadata, _report = parse_and_convert_golden_packages(packages)
    source = next(
        event
        for event in ledger.events
        if event.source.accession == _A1
        and event.concept_qname == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        and event.context.start == date(2024, 9, 29)
        and event.context.end == date(2025, 9, 27)
        and event.dimensions_known
        and not event.context.explicit_dimensions
    )
    agreeing = replace(
        source,
        source_occurrence_key="agreeing-duplicate",
        source_span=(0, 8),
        occurrence_id=None,
    )
    provider = _provider()
    dataset = provider.resolve(_GOLDEN_ENTITY)
    agreeing_dataset = FinancialQueryDataset(
        binding=dataset.binding,
        ledger=RawFactLedger((*ledger.events, agreeing)),
        filing_metadata=metadata,
        registry=dataset.registry,
        delivery=dataset.delivery,
    )

    class _Agreeing:
        def resolve(self, entity_id: str):
            return agreeing_dataset

    agreeing_result = execute_financial_query(
        body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
        provider=_Agreeing(),
    )
    assert _root_cell(agreeing_result.envelope, "revenue", start="2024-09-29", end="2025-09-27")["state"] == "value"

    hostile = replace(
        source,
        parsed_value="1",
        raw_token="1",
        source_occurrence_key="hostile-duplicate",
        source_span=(0, 1),
        occurrence_id=None,
    )
    hostile_dataset = FinancialQueryDataset(
        binding=dataset.binding,
        ledger=RawFactLedger((*ledger.events, hostile)),
        filing_metadata=metadata,
        registry=dataset.registry,
        delivery=dataset.delivery,
    )

    class _Hostile:
        def resolve(self, entity_id: str):
            return hostile_dataset

    hostile_result = execute_financial_query(
        body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
        provider=_Hostile(),
    )
    cell = _root_cell(hostile_result.envelope, "revenue", start="2024-09-29", end="2025-09-27")
    assert cell["state"] == "not_evaluable"
    assert cell["reason"] == "conflicting duplicate raw facts cannot be selected"


def test_product_service_dimensions_are_not_consolidated_revenue() -> None:
    dataset = _provider().resolve(_GOLDEN_ENTITY)
    dimensional = [
        event
        for event in dataset.ledger.events
        if event.concept_qname == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        and event.context.explicit_dimensions
    ]
    assert dimensional
    assert any(
        "ProductOrService" in axis or "ProductOrService" in member
        for event in dimensional
        for axis, member in event.context.explicit_dimensions
    )
    result = execute_financial_query(
        body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
        provider=_provider(),
    )
    cell = _root_cell(result.envelope, "revenue", start="2024-09-29", end="2025-09-27")
    selected = cell["provenance"]["selected_raw_fact"]
    assert selected["dimensions_known"] is True
    assert selected["context"]["explicit_dimensions"] == {}
    assert selected["context"]["typed_dimensions"] == {}
    assert cell["value"] == "416161000000"

    incomplete = replace(
        next(
            event
            for event in dataset.ledger.events
            if event.source_occurrence_key == selected["source_occurrence_key"]
        ),
        dimensions_known=False,
        occurrence_id=None,
        source_occurrence_key="incomplete-dimension-scope",
        source_span=(1, 2),
    )
    incomplete_dataset = FinancialQueryDataset(
        binding=dataset.binding,
        ledger=RawFactLedger((incomplete,)),
        filing_metadata={selected["source"]["accession"]: dataset.filing_metadata[_A1]},
        registry=dataset.registry,
        delivery=dataset.delivery,
    )

    class _Incomplete:
        def resolve(self, entity_id: str):
            return incomplete_dataset

    incomplete_result = execute_financial_query(
        body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
        provider=_Incomplete(),
    )
    incomplete_cell = _root_cell(
        incomplete_result.envelope, "revenue", start="2024-09-29", end="2025-09-27"
    )
    assert incomplete_cell["state"] == "not_evaluable"
    assert "unknown_dimension_scope" in (incomplete_cell["reason"] or "")


def test_unknown_issuer_is_private_400() -> None:
    with pytest.raises(Exception) as exc:
        execute_financial_query(
            body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV], entity_id="ISS:US-XNAS-MSFT"),
            provider=_provider(),
        )
    from engine.fundamental_forensics.query_service import FinancialQueryAdmissionError

    assert isinstance(exc.value, FinancialQueryAdmissionError)
    assert exc.value.status_code == 400
    assert exc.value.detail == "unknown entity"


def test_corrupt_golden_source_is_private_503(tmp_path) -> None:
    from engine.fundamental_forensics.query_service import FinancialQueryUnavailableError

    with pytest.raises(FinancialQueryUnavailableError):
        GoldenAaplFinancialQueryProvider(tmp_path).resolve(_GOLDEN_ENTITY)


def test_no_request_time_network_or_write(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise AssertionError("FIF-3A3 requested the network")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    writes: list[str] = []
    original = Path.write_bytes

    def _track(self: Path, data: bytes) -> int:
        writes.append(str(self))
        return original(self, data)

    monkeypatch.setattr(Path, "write_bytes", _track)
    result = execute_financial_query(
        body=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
        provider=_provider(),
    )
    assert _root_cell(result.envelope, "revenue", start="2024-09-29", end="2025-09-27")["state"] == "value"
    assert writes == []


def test_fip1_response_remains_byte_identical_without_delivery() -> None:
    class _P:
        def resolve(self, entity_id: str):
            return fip1_fixture_dataset(ROOT)

    result = execute_financial_query(
        body=json.dumps(
            {
                "schema": "fundamental_forensics.financial_query_request/v1",
                "entity_id": "mmx.issuer.fip1",
                "policy": {
                    "selection": "as_reported",
                    "source_snapshot_at": "2024-12-31T23:59:59Z",
                    "recorded_at": "2026-08-03T12:00:00Z",
                },
                "metric_ids": ["revenue"],
                "periods": [{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}],
            },
            separators=(",", ":"),
        ).encode("utf-8"),
        provider=_P(),
    )
    assert "delivery" not in result.envelope


def _fip1_dataset_with_delivery(delivery):
    base = fip1_fixture_dataset(ROOT)
    return FinancialQueryDataset(
        binding=base.binding,
        ledger=base.ledger,
        filing_metadata=base.filing_metadata,
        registry=base.registry,
        delivery=delivery,
    )


def _fip1_query_bytes() -> bytes:
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": "mmx.issuer.fip1",
            "policy": {
                "selection": "as_reported",
                "source_snapshot_at": "2024-12-31T23:59:59Z",
                "recorded_at": "2026-08-03T12:00:00Z",
            },
            "metric_ids": ["revenue"],
            "periods": [{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}],
        },
        separators=(",", ":"),
    ).encode("utf-8")


@pytest.mark.parametrize(
    "delivery",
    (
        {
            "kind": "production_attested",
            "attested": False,
            "production_issuer_service": False,
        },
        {
            "kind": "committed_golden_fixture",
            "attested": True,
            "production_issuer_service": False,
        },
        {
            "kind": "committed_golden_fixture",
            "attested": False,
            "production_issuer_service": True,
        },
        {
            "kind": "committed_golden_fixture",
            "attested": 0,
            "production_issuer_service": False,
        },
        {
            "kind": "committed_golden_fixture",
            "attested": False,
            "production_issuer_service": 0,
        },
        {
            "kind": "committed_golden_fixture",
            "attested": "false",
            "production_issuer_service": False,
        },
        {"kind": "committed_golden_fixture", "attested": False},
        {
            "kind": "committed_golden_fixture",
            "attested": False,
            "production_issuer_service": False,
            "authority": "context_only",
        },
        {},
        "committed_golden_fixture",
    ),
)
def test_unlawful_delivery_is_unavailable(delivery) -> None:
    class _P:
        def resolve(self, entity_id: str):
            return _fip1_dataset_with_delivery(delivery)

    with pytest.raises(FinancialQueryUnavailableError):
        execute_financial_query(body=_fip1_query_bytes(), provider=_P())


def test_five_5983_query_hashes_and_fif2c_pins() -> None:
    class _P:
        def resolve(self, entity_id: str):
            return fip1_fixture_dataset(ROOT)

    def _hash(*, selection, source, recorded, metric_ids, periods):
        body = json.dumps(
            {
                "schema": "fundamental_forensics.financial_query_request/v1",
                "entity_id": "mmx.issuer.fip1",
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
        return execute_financial_query(
            body=body, provider=_P(), issuer_sic_resolver=_fip1_issuer_sic_resolver
        ).envelope["receipt"]["query_hash"]

    fy_metrics = ["revenue", "gross_margin"]
    fy = [{"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}]
    mixed = fy + [{"kind": "instant", "start": None, "end": "2023-12-31", "label": "2023-12-31"}]
    t1, t2, t3s, t3r = "2024-12-31T23:59:59Z", "2026-08-03T12:00:00Z", "2025-12-31T23:59:59Z", "2026-08-05T12:00:02Z"
    assert _hash(selection="as_reported", source=t1, recorded=t2, metric_ids=fy_metrics, periods=fy) == _HASH_AS_REPORTED_T1_T2
    assert _hash(selection="latest_known_as_of", source=t1, recorded=t2, metric_ids=fy_metrics, periods=fy) == _HASH_LATEST_KNOWN_T1_T2
    assert _hash(selection="latest_known_as_of", source=t3s, recorded=t3r, metric_ids=fy_metrics, periods=fy) == _HASH_LATEST_KNOWN_T3
    assert _hash(selection="latest_restated", source=t3s, recorded=t3r, metric_ids=fy_metrics, periods=fy) == _HASH_LATEST_RESTATED_T3
    assert _hash(
        selection="latest_known_as_of",
        source=t3s,
        recorded=t3r,
        metric_ids=["revenue", "accounts_receivable_net"],
        periods=mixed,
    ) == _HASH_MIXED_T3
    from engine.fundamental_forensics.packet_service import execute_financial_packet
    from engine.fundamental_forensics.revision_service import fip1_packet_dataset

    class _Packet:
        def resolve(self, entity_id: str):
            return fip1_packet_dataset(ROOT)

    rich = execute_financial_packet(
        body=json.dumps(
            {
                "schema": "fundamental_forensics.financial_packet_request/v1",
                "entity_id": "mmx.issuer.fip1",
                "policy": {
                    "selection": "latest_known_as_of",
                    "source_snapshot_at": t3s,
                    "recorded_at": t3r,
                },
                "metric_ids": ["revenue", "accounts_receivable_net", "gross_margin", "CustomerCount"],
                "periods": mixed,
            },
            separators=(",", ":"),
        ).encode("utf-8"),
        provider=_Packet(),
    )
    assert rich.packet["packet_id"] == _RICH_PACKET_ID
    assert rich.packet["content_sha256"] == _RICH_CONTENT_SHA
    assert rich.response_sha256 == _RICH_RESPONSE_SHA


def test_frozen_predecessor_paths_are_empty_diff() -> None:
    for group in (_FROZEN_FIF1, _FROZEN_KERNEL):
        dirty = subprocess.run(
            ["git", "diff", "--exit-code", "--", *group],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        assert dirty.returncode == 0, dirty.stdout.decode("utf-8", "replace") + dirty.stderr.decode(
            "utf-8", "replace"
        )
        against_main = subprocess.run(
            ["git", "diff", "--exit-code", "origin/main...HEAD", "--", *group],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        assert against_main.returncode == 0, against_main.stdout.decode("utf-8", "replace")


def test_http_aapl_query_is_private_200() -> None:
    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    forensics_api.REPO = ROOT
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/forensics/v1/financial/query",
            content=_query_body(metric_ids=["revenue"], periods=[FY2025_REV]),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 200
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected
    payload = response.json()
    assert payload["delivery"]["kind"] == "committed_golden_fixture"
    assert payload["delivery"]["attested"] is False
    assert payload["authority"] == {"class": "context_only", "display_only": True}
    cell = _root_cell(payload, "revenue", start="2024-09-29", end="2025-09-27")
    assert cell["value"] == "416161000000"


# ---------------------------------------------------------------------------
# Golden statement pins run on the committed byte-copy of the 1.0.0 registry.
# Appended at the end of the module so no pinned line moves. The live-registry
# statement bytes are pinned in test_fundamental_forensics_financial_statement_api.py,
# which also proves the 1.0.0 registry re-derives the pins in this module.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def _golden_statement_pins_on_registry_v1_0_0():
    import engine.fundamental_forensics.statement_service as statement_service
    from engine.fundamental_forensics.financial_intelligence_packet import load_core_registry

    registry_root = ROOT / "tests" / "fixtures" / "fundamental_forensics_registry_v1_0_0"
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            statement_service,
            "load_core_registry",
            lambda _repo_root: load_core_registry(registry_root),
        )
        yield
