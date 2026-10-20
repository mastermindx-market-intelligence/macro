"""FIF T2: pre-T1 compatibility hash seal — pinning tests (MASTERPLAN §4.3 / A02).

The committed manifest ``tests/fixtures/fundamental_forensics/
t1_compatibility_seal_manifest_v1.json`` was re-executed at FIF G0 commit
``a6bed4b64ff999077545bca3ee4157e02387a47a`` by
``scripts/fif_compatibility_seal.py`` (seat ruling G0-R2; the pre-T1 seal at
``5267c66846e7733bc1eb30edc1524daff51598ca`` is preserved in #8936 history).
Every test here recomputes one sealed
family through the REAL services/kernel and asserts

    recomputed value == manifest value == existing test-pinned literal

(the third leg only where an existing suite already pins the literal).  T1
(lineage repair) must keep every one of these green: a moved byte anywhere in
a VALID-receipt golden AAPL / FIP1 response is a compatibility break, not a
refactor.

Self-contained: no dependence on any T1 code.  Skips nothing.  Requires the
committed fixtures under ``tests/fixtures/fundamental_forensics/`` plus the
``data/reference/`` issuer tables the golden providers bind through
(``engine/fundamental_forensics/statement_service.py:102-110``) — present in
every full checkout and materializable in a sparse session worktree with
``git sparse-checkout add data/reference``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.fundamental_forensics.financial_intelligence_packet import sha256_file
from engine.fundamental_forensics.ixbrl_raw_ledger import (
    FIF3A4_LINEAGE_AVAILABLE_AT,
    GoldenAaplFinancialQueryProvider,
)
from engine.fundamental_forensics.packet_service import execute_financial_packet
from engine.fundamental_forensics.query_service import (
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.revision_service import (
    execute_financial_revisions,
    fip1_packet_dataset,
)
from engine.fundamental_forensics.statement_graph import load_golden_aapl_package
from engine.fundamental_forensics.statement_service import (
    GoldenAaplStatementProvider,
    execute_financial_statements,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics"
    / "t1_compatibility_seal_manifest_v1.json"
)
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

# The pre-T1 seal at 5267c66846e7733bc1eb30edc1524daff51598ca is preserved in
# #8936 history; this constant re-targets the G0 re-seal (seat ruling G0-R2).
SEALED_BASE_COMMIT = "a6bed4b64ff999077545bca3ee4157e02387a47a"

EXPECTED_CASES = {
    "no_lineage_a3_golden",
    "pre_lineage_source_clock",
    "historical_a3_cutoff_preserves_not_evaluable",
    "latest_known_as_of_a4_comparative",
    "as_reported_a4_comparative",
    "latest_restated_a4_comparative",
    "kernel_fip1_as_reported_t1_t2",
    "kernel_fip1_latest_known_t1_t2",
    "kernel_fip1_latest_known_t3",
    "kernel_fip1_latest_restated_t3",
    "kernel_fip1_mixed_t3",
    "statement_service_10k",
    "statement_service_10q",
    "fip1_evidence_witnesses",
    "packet_service_fip1_t3",
    "packet_service_fip1_rich_t3",
    "revision_service_fip1_t3",
    "api_transport_query_a4_comparative",
}

# --- existing test-pinned literals (FIF_T2_SEAL_REPORT §3.2) ------------------
# Sources (re-derived at the G0 commit; the FIF G0-r1/r1p3 re-pins moved them):
# tests/test_fundamental_forensics_cross_filing_lineage.py:48,53-56,
# tests/test_fundamental_forensics_financial_revision_service.py:70-74,
# tests/test_fundamental_forensics_financial_statement_service.py:50-56,75-77,81,925-931.

_PIN_LEDGER_SHA = "ba149bd55d929d843f353e91bbf68147791fb8b4a20c258426ea2eb7527019d8"
_PIN_AAPL_RESPONSE_SHA = "fbae153c5fccd26b747be10239fe4b5fcd0e30113604597d16b01bf31b875c48"
_PIN_AAPL_QUERY_HASH = "a4b04952c3df3e50936d4229b018f0a7f7035edb24139ba936aa58f913515920"
_PIN_A1_OCCURRENCE = "rawfact_bc9355a292f06baaaf988b683106b2b02e3dd9c4a9555f1eb160a94643e4feaf"
_PIN_A2_OCCURRENCE = "rawfact_9669446bc8076fa26bca33a3d9a067093bddadbb28e4617318bb3de33a4eca29"
_PIN_VALUE = "359241000000"
_PIN_HISTORICAL_REASON = (
    "unlinked source vintages require an explicit typed revision lineage"
)
_PIN_LATEST_RESTATED_REASON = (
    "no eligible explicitly typed reported revision vintage"
)
# Kernel five sealed on the BARE production-default path (no injected SIC
# resolver).  The source tests pin the injected 58d438ec... family by design,
# so the seal no longer mirrors them for the kernel five (seat ruling G0-R2).
_PIN_KERNEL_HASHES = {
    "kernel_fip1_as_reported_t1_t2": "f4ed662fda31a10e5d93930914263f86e3ff58abffa3f14100ad428eedd82959",
    "kernel_fip1_latest_known_t1_t2": "6385734fbe500e88e2af76483c34200ea2609e888aa7f7425d3f43ec03c9b20d",
    "kernel_fip1_latest_known_t3": "b5db79e8dc60619c19f6c3f1bfe62657226f1b9f78e2ac7bbfad74afa86d5471",
    "kernel_fip1_latest_restated_t3": "4650f7985f438b04a4274053dd0c5e1721e7c12840eb077156fd4d745c574ac2",
    "kernel_fip1_mixed_t3": "26a7ed7d95f861d3352c3a7e5fb6a0f52833ccf69947b10ca9da1f9662c44133",
}
_PIN_STATEMENT_10K = {
    "response_sha256": "25e5562e81cb80bd42d0feb544c212c4471e11736601aaee418a60981a457184",
    "response_bytes": 196310,
    "index_sha256": "d61dde83df2dde7d63041e443321eab963b245e4c0090ba6240ce1711329de83",
    "primary_member_sha256": "548ae59778cf08ee0f2ee088e7ece20d947076c3c01f74d2d65db4c2777e436a",
    "witness_sha256": "6449489eef577b096abeb79f5375b7df9c95c23e4765a075222a765a19124d83",
}
_PIN_STATEMENT_10Q = {
    "response_sha256": "b98602a299996ff7ea58b842364031547df795d1458b51134eef0e37159b7918",
    "response_bytes": 190019,
    "index_sha256": "3e5dde4c0403da2358df715608c679d66223c8d716a75fe1136d9257ba812fdc",
    "primary_member_sha256": "4ad5bea67cedfa7542d623900355cc8d143ef95c1acc135a597f2eedabdb9177",
    "witness_sha256": "6727f5eb1815b2b6b580f69caa76fd644ad6fc651c6b7082f9045459f72f370c",
}
_PIN_RICH_PACKET = {
    "packet_id": "fip_5d77c1349de4f829db2c422a",
    "content_sha256": "5d77c1349de4f829db2c422a3000049cb12b6f0c16dbcd57686a0c0cd41c0af0",
    "response_sha256": "a9c5a8657e7c5cb7e6789cd6d2ea4f78a1c14100c33a00d959856d7375045ca8",
}
_PIN_GOLDEN_PACKET_ID = "fip_efe52d02d4a72a5a19f85a60"
_PIN_CONFIRMATION_SOURCE_KNOWN_AT = "2026-07-31T10:01:02.000000Z"

# --- golden request constructions (byte-identical to the seal tool) -----------

GOLDEN = "ISS:US-XNAS-AAPL"
A1, A2 = "0000320193-25-000079", "0000320193-26-000020"
A3_SOURCE, A3_RECORDED = "2026-08-01T00:00:00Z", "2026-08-23T12:00:00Z"
A4_SOURCE, A4_RECORDED = "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z"
A4_AVAILABLE_AT = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
PRE_LINEAGE_SOURCE = "2026-07-30T00:00:00Z"

FY2025_REV = {"kind": "duration", "start": "2024-09-29", "end": "2025-09-27", "label": "FY2025"}
Q3_REV = {"kind": "duration", "start": "2026-03-29", "end": "2026-06-27", "label": "FY2026Q3"}
YTD_REV = {"kind": "duration", "start": "2025-09-28", "end": "2026-06-27", "label": "FY2026YTD"}
GOLDEN_METRICS = ["revenue", "total_assets", "gross_margin", "net_cash_from_operating_activities"]
GOLDEN_PERIODS = [FY2025_REV, Q3_REV, YTD_REV,
                  {"kind": "instant", "start": None, "end": "2026-06-27", "label": "2026-06-27"}]
COMPARATIVE = {"kind": "instant", "start": None, "end": "2025-09-27", "label": "2025-09-27"}

FY2023 = {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
AR_INSTANT = {"kind": "instant", "start": None, "end": "2023-12-31", "label": "2023-12-31"}
T1_KERNEL, T2_KERNEL_RECORDED = "2024-12-31T23:59:59Z", "2026-08-03T12:00:00Z"
T3_KERNEL, T3_KERNEL_RECORDED = "2025-12-31T23:59:59Z", "2026-08-05T12:00:02Z"
FIP1 = "mmx.issuer.fip1"
RICH_METRICS = ["revenue", "accounts_receivable_net", "gross_margin", "CustomerCount"]
RICH_PERIODS = [FY2023, AR_INSTANT]


def _entry(case: str) -> dict:
    matches = [e for e in MANIFEST["entries"] if e["case"] == case]
    assert len(matches) == 1, f"manifest must hold exactly one {case!r} entry"
    return matches[0]


def _query_body(metric_ids, periods, source, recorded, *, selection="latest_known_as_of",
                entity=GOLDEN) -> bytes:
    return json.dumps(
        {
            "schema": "fundamental_forensics.financial_query_request/v1",
            "entity_id": entity,
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


def _packet_body(schema, *, metrics, periods, source, recorded,
                 selection="latest_known_as_of", entity=FIP1) -> bytes:
    return json.dumps(
        {
            "schema": schema,
            "entity_id": entity,
            "policy": {
                "selection": selection,
                "source_snapshot_at": source,
                "recorded_at": recorded,
            },
            "metric_ids": metrics,
            "periods": periods,
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _root_cell(envelope, metric_id, *, start, end) -> dict:
    receipt = envelope["receipt"]
    roots = set(receipt["root_cell_ids"])
    for node in receipt["nodes"]:
        if node["cell_id"] not in roots or node["metric_id"] != metric_id:
            continue
        period = node["period"]
        if period.get("start") == start and period.get("end") == end:
            return node
    raise AssertionError(f"no root cell for {metric_id} {start}..{end}")


def _comparative_result(provider, *, selection, source=A4_SOURCE, recorded=A4_RECORDED):
    result = execute_financial_query(
        body=_query_body(["total_assets"], [COMPARATIVE], source, recorded, selection=selection),
        provider=provider,
    )
    cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
    return result, cell


# --- shared heavy fixtures (module scope: parse the golden filings once) ------


@pytest.fixture(scope="module")
def bare_provider():
    return GoldenAaplFinancialQueryProvider(ROOT)


@pytest.fixture(scope="module")
def lineage_provider():
    return GoldenAaplFinancialQueryProvider(
        ROOT, lineage_evidence_available_at=A4_AVAILABLE_AT
    )


@pytest.fixture(scope="module")
def a3_bare_result(bare_provider):
    return execute_financial_query(
        body=_query_body(GOLDEN_METRICS, GOLDEN_PERIODS, A3_SOURCE, A3_RECORDED),
        provider=bare_provider,
    )


@pytest.fixture(scope="module")
def a3_lineage_result(lineage_provider):
    return execute_financial_query(
        body=_query_body(GOLDEN_METRICS, GOLDEN_PERIODS, A3_SOURCE, A3_RECORDED),
        provider=lineage_provider,
    )


@pytest.fixture(scope="module")
def statement_results():
    outcomes = {}
    provider = GoldenAaplStatementProvider(ROOT)
    for accession in (A1, A2):
        body = json.dumps(
            {
                "schema": "fundamental_forensics.financial_statement_request/v1",
                "entity_id": GOLDEN,
                "accession": accession,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        outcomes[accession] = execute_financial_statements(
            body=body, repo_root=ROOT, provider=provider
        )
    return outcomes


@pytest.fixture(scope="module")
def packet_dataset():
    return fip1_packet_dataset(ROOT)


class _PacketProvider:
    def __init__(self, dataset):
        self._dataset = dataset

    def resolve(self, entity_id: str):
        return self._dataset


# ---------------------------------------------------------------------------
# Family 1 — the manifest itself
# ---------------------------------------------------------------------------


def test_manifest_pins_the_executed_pre_t1_base_commit():
    assert MANIFEST["schema"] == "fundamental_forensics.t1_compatibility_seal_manifest/v1"
    assert MANIFEST["seal"] == "fif-t2-compatibility-seal"
    assert MANIFEST["base_commit"] == SEALED_BASE_COMMIT
    assert MANIFEST["expected_base_commit"] == SEALED_BASE_COMMIT
    assert MANIFEST["tool"] == "scripts/fif_compatibility_seal.py"
    assert MANIFEST["tool_command"].startswith("PYTHONDONTWRITEBYTECODE=1 python3 scripts/")
    parsed = datetime.fromisoformat(MANIFEST["generated_at"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert {e["case"] for e in MANIFEST["entries"]} == EXPECTED_CASES
    for entry in MANIFEST["entries"]:
        assert entry["inputs"], entry["case"]
        assert entry["sites"], entry["case"]
        assert entry["values"], entry["case"]
        for value_key, site in entry["sites"].items():
            assert value_key in entry["values"] or "." in value_key, (entry["case"], value_key)
            assert site, (entry["case"], value_key)


# ---------------------------------------------------------------------------
# Families 2-3 — no-lineage golden bytes and the raw ledger sha
# ---------------------------------------------------------------------------


def test_no_lineage_a3_golden_response_bytes_unchanged(a3_bare_result):
    values = _entry("no_lineage_a3_golden")["values"]
    result = a3_bare_result
    assert result.sha256 == values["response_sha256"] == _PIN_AAPL_RESPONSE_SHA
    assert result.envelope["receipt"]["query_hash"] == values["query_hash"] == _PIN_AAPL_QUERY_HASH
    assert ("lineage" in result.envelope) is values["has_lineage_key"] is False
    assert len(result.body) == values["response_bytes"]
    assert hashlib.sha256(result.body).hexdigest() == result.sha256


def test_ledger_sha_unchanged_for_bare_and_lineage_providers(bare_provider, lineage_provider):
    values = _entry("no_lineage_a3_golden")["values"]
    historical = _entry("historical_a3_cutoff_preserves_not_evaluable")["values"]
    bare_sha = bare_provider.conversion_report().ledger_sha256
    lineage_sha = lineage_provider.conversion_report().ledger_sha256
    assert bare_sha == lineage_sha == values["ledger_sha256"] == _PIN_LEDGER_SHA
    assert historical["ledger_sha256"] == _PIN_LEDGER_SHA


# ---------------------------------------------------------------------------
# Family 4 — a historical cutoff is never retroactively repaired
# ---------------------------------------------------------------------------


def test_historical_a3_cutoff_still_refuses_retroactive_repair(lineage_provider, a3_lineage_result):
    values = _entry("historical_a3_cutoff_preserves_not_evaluable")["values"]
    assert a3_lineage_result.sha256 == values["response_sha256"] == _PIN_AAPL_RESPONSE_SHA
    assert (
        a3_lineage_result.envelope["receipt"]["query_hash"]
        == values["query_hash"]
        == _PIN_AAPL_QUERY_HASH
    )
    assert ("lineage" in a3_lineage_result.envelope) is values["has_lineage_key"] is False
    result, cell = _comparative_result(
        lineage_provider, selection="latest_known_as_of", source=A3_SOURCE, recorded=A3_RECORDED
    )
    assert cell["state"] == values["comparative_cell_state"] == "not_evaluable"
    assert cell["reason"] == values["comparative_cell_reason"] == _PIN_HISTORICAL_REASON


# ---------------------------------------------------------------------------
# Family 5 — pre-lineage source clock selects the first filing root
# ---------------------------------------------------------------------------


def test_pre_lineage_source_clock_selects_the_first_filing_root(lineage_provider):
    values = _entry("pre_lineage_source_clock")["values"]
    result, cell = _comparative_result(
        lineage_provider, selection="latest_known_as_of",
        source=PRE_LINEAGE_SOURCE, recorded=A4_RECORDED,
    )
    assert result.sha256 == values["response_sha256"]
    assert result.envelope["receipt"]["query_hash"] == values["query_hash"]
    assert cell["state"] == values["cell_state"] == "value"
    assert cell["value"] == values["cell_value"] == _PIN_VALUE
    assert cell["provenance"]["source_occurrence_ids"] == (
        values["source_occurrence_ids"]
    ) == [_PIN_A1_OCCURRENCE]
    assert cell["provenance"]["accession"] == values["accession"] == A1
    assert cell["provenance"]["form"] == values["form"] == "10-K"
    assert ("lineage" in result.envelope) is values["has_lineage_key"] is False


# ---------------------------------------------------------------------------
# Family 6 — the three selection policies on the confirmed comparative cell
# ---------------------------------------------------------------------------


def test_latest_known_comparative_value_and_receipt_unchanged(lineage_provider):
    values = _entry("latest_known_as_of_a4_comparative")["values"]
    result, cell = _comparative_result(lineage_provider, selection="latest_known_as_of")
    assert result.sha256 == values["response_sha256"]
    assert result.envelope["receipt"]["query_hash"] == values["query_hash"]
    assert cell["state"] == values["cell_state"] == "value"
    assert cell["value"] == values["cell_value"] == _PIN_VALUE
    assert cell["provenance"]["source_occurrence_ids"] == (
        values["source_occurrence_ids"]
    ) == [_PIN_A2_OCCURRENCE]
    assert cell["provenance"]["accession"] == values["accession"] == A2
    assert cell["provenance"]["form"] == values["form"] == "10-Q"
    confirmations = result.envelope.get("lineage", {}).get("confirmations") or []
    assert len(confirmations) == values["lineage_confirmation_rows"] == 1
    # json round-trip normalizes tuple->list (the in-memory disclosure carries
    # `*_source_occurrence_keys` as a tuple; the served bytes are identical).
    assert json.loads(json.dumps(confirmations[0])) == values["first_confirmation"]
    row = confirmations[0]
    assert row["parent_occurrence_id"] == _PIN_A1_OCCURRENCE
    assert row["child_occurrence_id"] == _PIN_A2_OCCURRENCE
    assert row["comparison_basis"] == "exact_parsed_value_and_accuracy_tokens"
    assert row["positive_evidence"]["parsed_value"] == _PIN_VALUE
    assert row["source_known_at"] == _PIN_CONFIRMATION_SOURCE_KNOWN_AT
    assert row["refusal_reason"] is None


def test_as_reported_comparative_root_unchanged(lineage_provider):
    values = _entry("as_reported_a4_comparative")["values"]
    result, cell = _comparative_result(lineage_provider, selection="as_reported")
    assert result.sha256 == values["response_sha256"]
    assert result.envelope["receipt"]["query_hash"] == values["query_hash"]
    assert cell["state"] == values["cell_state"] == "value"
    assert cell["value"] == values["cell_value"] == _PIN_VALUE
    assert cell["provenance"]["source_occurrence_ids"] == (
        values["source_occurrence_ids"]
    ) == [_PIN_A1_OCCURRENCE]
    assert cell["provenance"]["accession"] == values["accession"] == A1
    assert cell["provenance"]["form"] == values["form"] == "10-K"


def test_latest_restated_comparative_still_missing(lineage_provider):
    values = _entry("latest_restated_a4_comparative")["values"]
    result, cell = _comparative_result(lineage_provider, selection="latest_restated")
    assert result.sha256 == values["response_sha256"]
    assert result.envelope["receipt"]["query_hash"] == values["query_hash"]
    assert cell["state"] == values["cell_state"] == "missing"
    assert cell["reason"] == values["cell_reason"] == _PIN_LATEST_RESTATED_REASON
    assert cell.get("value") is values["cell_value"] is None


# ---------------------------------------------------------------------------
# Family 7 — kernel FIP1 query_hash pins
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case, selection, source, recorded, metrics, periods",
    [
        ("kernel_fip1_as_reported_t1_t2", "as_reported", T1_KERNEL, T2_KERNEL_RECORDED,
         ["revenue", "gross_margin"], [FY2023]),
        ("kernel_fip1_latest_known_t1_t2", "latest_known_as_of", T1_KERNEL, T2_KERNEL_RECORDED,
         ["revenue", "gross_margin"], [FY2023]),
        ("kernel_fip1_latest_known_t3", "latest_known_as_of", T3_KERNEL, T3_KERNEL_RECORDED,
         ["revenue", "gross_margin"], [FY2023]),
        ("kernel_fip1_latest_restated_t3", "latest_restated", T3_KERNEL, T3_KERNEL_RECORDED,
         ["revenue", "gross_margin"], [FY2023]),
        ("kernel_fip1_mixed_t3", "latest_known_as_of", T3_KERNEL, T3_KERNEL_RECORDED,
         ["revenue", "accounts_receivable_net"], [FY2023, AR_INSTANT]),
    ],
)
def test_kernel_fip1_query_hashes_unchanged(case, selection, source, recorded, metrics, periods):
    class _KernelProvider:
        def resolve(self, entity_id: str):
            return fip1_fixture_dataset(ROOT)

    values = _entry(case)["values"]
    result = execute_financial_query(
        body=_query_body(metrics, periods, source, recorded, selection=selection, entity=FIP1),
        provider=_KernelProvider(),
    )
    assert (
        result.envelope["receipt"]["query_hash"]
        == values["query_hash"]
        == _PIN_KERNEL_HASHES[case]
    )
    assert result.sha256 == values["response_sha256"]


# ---------------------------------------------------------------------------
# Family 8 — statement service 10-K / 10-Q responses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("accession, pins, case", [
    (A1, _PIN_STATEMENT_10K, "statement_service_10k"),
    (A2, _PIN_STATEMENT_10Q, "statement_service_10q"),
])
def test_statement_service_response_shas_unchanged(statement_results, accession, pins, case):
    values = _entry(case)["values"]
    result = statement_results[accession]
    assert result.sha256 == values["response_sha256"] == pins["response_sha256"]
    assert len(result.body) == values["response_bytes"] == pins["response_bytes"]
    assert hashlib.sha256(result.body).hexdigest() == result.sha256
    package = result.envelope["package"]
    assert package["index_sha256"] == values["index_sha256"] == pins["index_sha256"]
    primary_name = result.envelope["filing"]["primary_document"]
    primary = next(m for m in package["members"] if m["name"] == primary_name)
    assert primary["content_sha256"] == (
        values["primary_member_sha256"]
    ) == pins["primary_member_sha256"]
    witness = load_golden_aapl_package(ROOT, accession=accession).manifest["acceptance_witness"]
    assert witness["content_sha256"] == values["witness_sha256"] == pins["witness_sha256"]
    assert witness["byte_length"] == values["witness_bytes"] == 364


# ---------------------------------------------------------------------------
# Family 9 — committed FIP1 evidence witnesses and the golden fixture identity
# ---------------------------------------------------------------------------


def test_fip1_evidence_witnesses_and_golden_fixture_identity_unchanged():
    values = _entry("fip1_evidence_witnesses")["values"]
    fixtures = ROOT / "tests" / "fixtures" / "fundamental_forensics"
    assert sha256_file(fixtures / "filing_package_raw_ledger_v1.json") == (
        values["filing_package_fixture_sha256"]
    )
    assert sha256_file(fixtures / "companyfacts_versions.json") == (
        values["companyfacts_witness_sha256"]
    )
    assert sha256_file(fixtures / "submissions_versions.json") == (
        values["submissions_witness_sha256"]
    )
    golden = json.loads(
        (fixtures / "expected_financial_intelligence_packet_v1.json").read_text(encoding="utf-8")
    )
    assert golden["packet_id"] == (
        values["golden_fixture_packet_id"]
    ) == _PIN_GOLDEN_PACKET_ID
    assert golden["content_sha256"] == values["golden_fixture_content_sha256"]


# ---------------------------------------------------------------------------
# Family 10 — packet service responses and packet identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case, metrics, periods, pins", [
    ("packet_service_fip1_t3", ["revenue"], [FY2023], None),
    ("packet_service_fip1_rich_t3", RICH_METRICS, RICH_PERIODS, _PIN_RICH_PACKET),
])
def test_packet_service_response_and_identity_unchanged(packet_dataset, case, metrics, periods,
                                                        pins):
    values = _entry(case)["values"]
    result = execute_financial_packet(
        body=_packet_body(
            "fundamental_forensics.financial_packet_request/v1",
            metrics=metrics, periods=periods, source=T3_KERNEL, recorded=T3_KERNEL_RECORDED,
        ),
        provider=_PacketProvider(packet_dataset),
    )
    assert result.response_sha256 == values["response_sha256"]
    assert len(result.body) == values["response_bytes"]
    assert result.packet["packet_id"] == values["packet_id"] == (
        f"fip_{result.packet['content_sha256'][:24]}"
    )
    assert result.packet["content_sha256"] == values["content_sha256"]
    if pins:
        assert values["packet_id"] == pins["packet_id"]
        assert values["content_sha256"] == pins["content_sha256"]
        assert values["response_sha256"] == pins["response_sha256"]


# ---------------------------------------------------------------------------
# Family 11 — revision service full-response projection
# ---------------------------------------------------------------------------


def test_revision_service_response_and_packet_ref_unchanged(packet_dataset):
    values = _entry("revision_service_fip1_t3")["values"]
    packet = _entry("packet_service_fip1_t3")["values"]
    result = execute_financial_revisions(
        body=_packet_body(
            "fundamental_forensics.financial_revision_request/v1",
            metrics=["revenue"], periods=[FY2023],
            source=T3_KERNEL, recorded=T3_KERNEL_RECORDED,
        ),
        provider=_PacketProvider(packet_dataset),
    )
    assert result.sha256 == values["response_sha256"]
    assert len(result.body) == values["response_bytes"]
    assert result.envelope["packet_ref"] == values["packet_ref"]
    assert result.envelope["packet_ref"]["packet_id"] == packet["packet_id"]
    assert result.envelope["packet_ref"]["content_sha256"] == packet["content_sha256"]
    assert len(result.envelope["revisions"]) == values["revision_rows"] == 1
    direct = execute_financial_packet(
        body=_packet_body(
            "fundamental_forensics.financial_packet_request/v1",
            metrics=["revenue"], periods=[FY2023],
            source=T3_KERNEL, recorded=T3_KERNEL_RECORDED,
        ),
        provider=_PacketProvider(packet_dataset),
    )
    assert result.envelope["revisions"] == direct.packet["revisions"]


# ---------------------------------------------------------------------------
# Family 12 — API transport: X-FIF-Response-SHA256 equals the served body
# ---------------------------------------------------------------------------


def test_api_transport_header_sha_equals_body_sha(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.forensics as forensics_api

    values = _entry("api_transport_query_a4_comparative")["values"]
    monkeypatch.setattr(forensics_api, "REPO", ROOT)
    api = FastAPI()
    api.include_router(forensics_api.router)
    api.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    api_body = _query_body(["total_assets"], [COMPARATIVE], A4_SOURCE, A4_RECORDED)
    with TestClient(api, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/forensics/v1/financial/query",
            content=api_body,
            headers={"content-type": "application/json"},
        )
    assert response.status_code == values["status_code"] == 200
    header_sha = response.headers.get("X-FIF-Response-SHA256")
    body_sha = hashlib.sha256(response.content).hexdigest()
    assert header_sha == values["header_sha256"]
    assert body_sha == values["body_sha256"] == header_sha
    direct = execute_financial_query(
        body=api_body,
        provider=GoldenAaplFinancialQueryProvider(
            ROOT, lineage_evidence_available_at=FIF3A4_LINEAGE_AVAILABLE_AT
        ),
    )
    assert direct.sha256 == values["direct_service_response_sha256"] == body_sha


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
