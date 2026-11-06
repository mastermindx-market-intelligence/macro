#!/usr/bin/env python3
"""FIF T2 — pre-T1 compatibility hash seal (MASTERPLAN §4.3 / A02).

Executes every hash-bearing golden AAPL / FIP1 response family through the
REAL services and kernel at the current commit and writes the values to a
committed manifest.  T1 (lineage repair) must later leave every VALID-receipt
response byte-identical; this manifest plus its pinning test module
(``tests/test_fundamental_forensics_t1_compatibility_seal.py``) is the
independent proof instrument that makes any drift red.

Usage (from the repo root, offline, deterministic):

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/fif_compatibility_seal.py \
        --out tests/fixtures/fundamental_forensics/t1_compatibility_seal_manifest_v1.json

Laws this tool enforces on itself:
  * No network: every value is computed from the committed tree.
  * Deterministic sealed values: the only non-deterministic manifest field is
    ``generated_at`` (execution metadata); every sealed hash/value is a pure
    function of the committed tree at ``base_commit``.
  * Pinned-literal cross-check: every value that an existing test already
    pins (FIF_T2_SEAL_REPORT §3.2) is compared against that literal at
    generation time.  Any disagreement prints BOTH values plus the producing
    command and the tool exits 1 WITHOUT writing the manifest — the operator
    decides, the tool never papers over a moved hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.fundamental_forensics.ixbrl_raw_ledger import (  # noqa: E402
    FIF3A4_LINEAGE_AVAILABLE_AT,
    GoldenAaplFinancialQueryProvider,
)
from engine.fundamental_forensics.query_service import (  # noqa: E402
    execute_financial_query,
    fip1_fixture_dataset,
)
from engine.fundamental_forensics.revision_service import (  # noqa: E402
    execute_financial_revisions,
    fip1_packet_dataset,
)
from engine.fundamental_forensics.packet_service import (  # noqa: E402
    execute_financial_packet,
)
from engine.fundamental_forensics.statement_service import (  # noqa: E402
    GoldenAaplStatementProvider,
    execute_financial_statements,
)
from engine.fundamental_forensics.statement_graph import (  # noqa: E402
    load_golden_aapl_package,
)

EXPECTED_BASE_COMMIT = "a6bed4b64ff999077545bca3ee4157e02387a47a"
MANIFEST_SCHEMA = "fundamental_forensics.t1_compatibility_seal_manifest/v1"
DEFAULT_OUT = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics"
    / "t1_compatibility_seal_manifest_v1.json"
)
TOOL_COMMAND = (
    "PYTHONDONTWRITEBYTECODE=1 python3 scripts/fif_compatibility_seal.py "
    "--out tests/fixtures/fundamental_forensics/t1_compatibility_seal_manifest_v1.json"
)

# --- golden request constructions (mirror the pinned tests byte for byte) ----

GOLDEN = "ISS:US-XNAS-AAPL"
A1, A2 = "0000320193-25-000079", "0000320193-26-000020"
A3_SOURCE, A3_RECORDED = "2026-08-01T00:00:00Z", "2026-08-23T12:00:00Z"
A4_SOURCE, A4_RECORDED = "2026-09-20T00:00:00Z", "2026-09-20T00:00:00Z"
A4_AVAILABLE_AT = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
PRE_LINEAGE_SOURCE = "2026-07-30T00:00:00Z"

FY2025_REV = {"kind": "duration", "start": "2024-09-29", "end": "2025-09-27", "label": "FY2025"}
Q3_REV = {"kind": "duration", "start": "2026-03-29", "end": "2026-06-27", "label": "FY2026Q3"}
YTD_REV = {"kind": "duration", "start": "2025-09-28", "end": "2026-06-27", "label": "FY2026YTD"}
A2_ASSETS = {"kind": "instant", "start": None, "end": "2026-06-27", "label": "2026-06-27"}
COMPARATIVE = {"kind": "instant", "start": None, "end": "2025-09-27", "label": "2025-09-27"}
GOLDEN_METRICS = ["revenue", "total_assets", "gross_margin", "net_cash_from_operating_activities"]
GOLDEN_PERIODS = [FY2025_REV, Q3_REV, YTD_REV, A2_ASSETS]

FY2023 = {"kind": "duration", "start": "2023-01-01", "end": "2023-12-31", "label": "FY2023"}
AR_INSTANT = {"kind": "instant", "start": None, "end": "2023-12-31", "label": "2023-12-31"}
T1_KERNEL, T2_KERNEL_RECORDED = "2024-12-31T23:59:59Z", "2026-08-03T12:00:00Z"
T3_KERNEL, T3_KERNEL_RECORDED = "2025-12-31T23:59:59Z", "2026-08-05T12:00:02Z"
FIP1 = "mmx.issuer.fip1"
RICH_METRICS = ["revenue", "accounts_receivable_net", "gross_margin", "CustomerCount"]
RICH_PERIODS = [FY2023, AR_INSTANT]

QUERY_REQUEST_SCHEMA = "fundamental_forensics.financial_query_request/v1"
PACKET_REQUEST_SCHEMA = "fundamental_forensics.financial_packet_request/v1"
REVISION_REQUEST_SCHEMA = "fundamental_forensics.financial_revision_request/v1"
STATEMENT_REQUEST_SCHEMA = "fundamental_forensics.financial_statement_request/v1"

# --- producing sites (re-verified at the G0 commit; #8936 history carries the
# pre-T1 5267c668 site map) ----------------------------------------------------

SITE_QUERY_RESPONSE_SHA = "engine/fundamental_forensics/query_service.py:752-759"
SITE_QUERY_HASH = "engine/fundamental_forensics/query.py:3685-3687"
SITE_LEDGER_SHA = "engine/fundamental_forensics/ixbrl_raw_ledger.py:446-448"
SITE_OCCURRENCE_ID = "engine/fundamental_forensics/raw_ledger.py:494-497"
SITE_LINEAGE_DISCLOSURE = "engine/fundamental_forensics/query_service.py:739-749"
SITE_REVISION_RESPONSE_SHA = "engine/fundamental_forensics/revision_service.py:359-363"
SITE_PACKET_RESPONSE_SHA = "engine/fundamental_forensics/packet_service.py:108-114"
SITE_PACKET_IDENTITY = "engine/fundamental_forensics/financial_intelligence_packet.py:1070-1075"
SITE_STATEMENT_RESPONSE_SHA = "engine/fundamental_forensics/statement_service.py:401-405"
SITE_STATEMENT_PACKAGE = "engine/fundamental_forensics/statement_service.py:357-372"
SITE_WITNESS_DIGESTS = "engine/fundamental_forensics/revision_service.py:123-131"
SITE_API_HEADER = "app/forensics.py:1024"
SITE_GOLDEN_PACKET_FIXTURE = (
    "tests/fixtures/fundamental_forensics/expected_financial_intelligence_packet_v1.json"
)

# --- existing test-pinned literals (FIF_T2_SEAL_REPORT §3.2) ------------------
# The tool compares every recomputation against these AT GENERATION TIME.

PIN_LEDGER_SHA = "ba149bd55d929d843f353e91bbf68147791fb8b4a20c258426ea2eb7527019d8"
PIN_AAPL_RESPONSE_SHA = "fbae153c5fccd26b747be10239fe4b5fcd0e30113604597d16b01bf31b875c48"
PIN_AAPL_QUERY_HASH = "a4b04952c3df3e50936d4229b018f0a7f7035edb24139ba936aa58f913515920"
PIN_A1_OCCURRENCE = "rawfact_bc9355a292f06baaaf988b683106b2b02e3dd9c4a9555f1eb160a94643e4feaf"
PIN_A2_OCCURRENCE = "rawfact_9669446bc8076fa26bca33a3d9a067093bddadbb28e4617318bb3de33a4eca29"

# Kernel five sealed on the BARE production-default path (no injected SIC
# resolver).  The source tests pin the injected 58d438ec... family by design,
# so the seal no longer mirrors them for the kernel five (seat ruling G0-R2).
PIN_KERNEL_HASHES = {
    "as_reported_t1_t2": "f4ed662fda31a10e5d93930914263f86e3ff58abffa3f14100ad428eedd82959",
    "latest_known_t1_t2": "6385734fbe500e88e2af76483c34200ea2609e888aa7f7425d3f43ec03c9b20d",
    "latest_known_t3": "b5db79e8dc60619c19f6c3f1bfe62657226f1b9f78e2ac7bbfad74afa86d5471",
    "latest_restated_t3": "4650f7985f438b04a4274053dd0c5e1721e7c12840eb077156fd4d745c574ac2",
    "mixed_t3": "26a7ed7d95f861d3352c3a7e5fb6a0f52833ccf69947b10ca9da1f9662c44133",
}

PIN_STATEMENT_10K = {
    "index_sha256": "d61dde83df2dde7d63041e443321eab963b245e4c0090ba6240ce1711329de83",
    "primary_member_sha256": "548ae59778cf08ee0f2ee088e7ece20d947076c3c01f74d2d65db4c2777e436a",
    "response_sha256": "25e5562e81cb80bd42d0feb544c212c4471e11736601aaee418a60981a457184",
    "response_bytes": 196310,
    "witness_sha256": "6449489eef577b096abeb79f5375b7df9c95c23e4765a075222a765a19124d83",
}
PIN_STATEMENT_10Q = {
    "index_sha256": "3e5dde4c0403da2358df715608c679d66223c8d716a75fe1136d9257ba812fdc",
    "primary_member_sha256": "4ad5bea67cedfa7542d623900355cc8d143ef95c1acc135a597f2eedabdb9177",
    "response_sha256": "b98602a299996ff7ea58b842364031547df795d1458b51134eef0e37159b7918",
    "response_bytes": 190019,
    "witness_sha256": "6727f5eb1815b2b6b580f69caa76fd644ad6fc651c6b7082f9045459f72f370c",
}
PIN_RICH_PACKET = {
    "packet_id": "fip_5d77c1349de4f829db2c422a",
    "content_sha256": "5d77c1349de4f829db2c422a3000049cb12b6f0c16dbcd57686a0c0cd41c0af0",
    "response_sha256": "a9c5a8657e7c5cb7e6789cd6d2ea4f78a1c14100c33a00d959856d7375045ca8",
}
PIN_GOLDEN_PACKET_ID = "fip_efe52d02d4a72a5a19f85a60"

PIN_LATEST_KNOWN_VALUE = "359241000000"
PIN_LATEST_RESTATED_REASON = "no eligible explicitly typed reported revision vintage"
PIN_HISTORICAL_REASON = "unlinked source vintages require an explicit typed revision lineage"

# Site strings re-derived at the G0 commit: the FIF G0-r1/r1p3 re-pins moved
# the source-test literals (kernel five now at financial_revision_service:70-74
# where the source pins the injected 58d438ec... family BY DESIGN, so the seal
# no longer mirrors them for the kernel five — seat ruling G0-R2), and the
# engine producing sites moved with the G0 kernel/catalog edits.  The pre-T1
# seal at 5267c66846e7733bc1eb30edc1524daff51598ca is preserved in #8936
# history.
PIN_SITES = {
    "ledger_sha256": "tests/test_fundamental_forensics_cross_filing_lineage.py:48",
    "aapl_response_sha256": "tests/test_fundamental_forensics_cross_filing_lineage.py:53",
    "aapl_query_hash": "tests/test_fundamental_forensics_cross_filing_lineage.py:54",
    "a1_occurrence": "tests/test_fundamental_forensics_cross_filing_lineage.py:55",
    "a2_occurrence": "tests/test_fundamental_forensics_cross_filing_lineage.py:56",
    "kernel_hashes": "tests/test_fundamental_forensics_financial_revision_service.py:70-74",
    "statement_10k": "tests/test_fundamental_forensics_financial_statement_service.py:50-56",
    "statement_10q": "tests/test_fundamental_forensics_financial_statement_service.py:925-931",
    "rich_packet": "tests/test_fundamental_forensics_financial_statement_service.py:75-77",
    "golden_packet_id": "tests/test_fundamental_forensics_financial_statement_service.py:81",
    "latest_known_cell": "tests/test_fundamental_forensics_cross_filing_lineage.py:331-334",
    "as_reported_cell": "tests/test_fundamental_forensics_cross_filing_lineage.py:342-345",
    "latest_restated_cell": "tests/test_fundamental_forensics_cross_filing_lineage.py:353-354",
    "historical_cell": "tests/test_fundamental_forensics_cross_filing_lineage.py:294-295",
    "pre_lineage_cell": "tests/test_fundamental_forensics_cross_filing_lineage.py:491-492",
}


# --- helpers ------------------------------------------------------------------


def _query_body(
    metric_ids: list,
    periods: list,
    source: str,
    recorded: str,
    *,
    selection: str = "latest_known_as_of",
    entity: str = GOLDEN,
) -> bytes:
    return json.dumps(
        {
            "schema": QUERY_REQUEST_SCHEMA,
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


def _packet_body(schema: str, *, metrics: list, periods: list, source: str, recorded: str,
                 selection: str = "latest_known_as_of", entity: str = FIP1) -> bytes:
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


def _statement_body(accession: str) -> bytes:
    return json.dumps(
        {"schema": STATEMENT_REQUEST_SCHEMA, "entity_id": GOLDEN, "accession": accession},
        separators=(",", ":"),
    ).encode("utf-8")


def _root_cell(envelope: dict, metric_id: str, *, start, end) -> dict:
    receipt = envelope["receipt"]
    roots = set(receipt["root_cell_ids"])
    for node in receipt["nodes"]:
        if node["cell_id"] not in roots or node["metric_id"] != metric_id:
            continue
        period = node["period"]
        if period.get("start") == start and period.get("end") == end:
            return node
    raise AssertionError(f"no root cell for {metric_id} {start}..{end}")


def _sorted_keys_sha(envelope: dict) -> str:
    """Independent canonicalization cross-check: re-serialize with sort_keys."""
    return hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _provenance(cell: dict) -> dict:
    return cell.get("provenance") or {}


def _first_confirmation(envelope: dict) -> dict | None:
    rows = envelope.get("lineage", {}).get("confirmations") or []
    return rows[0] if rows else None


class _SealFailure(Exception):
    pass


def _pin_check(mismatches: list, *, case: str, key: str, recomputed, pinned, site: str) -> None:
    if recomputed == pinned:
        return
    mismatches.append(
        f"  case={case} value={key}\n"
        f"    recomputed : {recomputed!r}\n"
        f"    pinned     : {pinned!r}\n"
        f"    pin site   : {site}\n"
        f"    command    : {TOOL_COMMAND}"
    )


# --- entry builders -----------------------------------------------------------


def build_manifest() -> tuple[dict, list[str]]:
    mismatches: list[str] = []
    entries: list[dict] = []

    def add(case: str, inputs: str, sites: dict, values: dict, pins: dict | None = None) -> None:
        entries.append(
            {
                "case": case,
                "inputs": inputs,
                "sites": sites,
                "pins": pins or {},
                "values": values,
            }
        )

    bare = GoldenAaplFinancialQueryProvider(ROOT)
    lineage = GoldenAaplFinancialQueryProvider(
        ROOT, lineage_evidence_available_at=A4_AVAILABLE_AT
    )

    # (1) no-lineage A3 golden bytes — the accepted FIF-3A3 identities
    result = execute_financial_query(
        body=_query_body(GOLDEN_METRICS, GOLDEN_PERIODS, A3_SOURCE, A3_RECORDED),
        provider=bare,
    )
    ledger_sha = bare.conversion_report().ledger_sha256
    query_hash = result.envelope["receipt"]["query_hash"]
    _pin_check(mismatches, case="no_lineage_a3_golden", key="response_sha256",
               recomputed=result.sha256, pinned=PIN_AAPL_RESPONSE_SHA,
               site=PIN_SITES["aapl_response_sha256"])
    _pin_check(mismatches, case="no_lineage_a3_golden", key="query_hash",
               recomputed=query_hash, pinned=PIN_AAPL_QUERY_HASH,
               site=PIN_SITES["aapl_query_hash"])
    _pin_check(mismatches, case="no_lineage_a3_golden", key="ledger_sha256",
               recomputed=ledger_sha, pinned=PIN_LEDGER_SHA, site=PIN_SITES["ledger_sha256"])
    add(
        "no_lineage_a3_golden",
        "golden AAPL entity, metrics [revenue,total_assets,gross_margin,"
        "net_cash_from_operating_activities], periods [FY2025,FY2026Q3,FY2026YTD,"
        "2026-06-27 instant], policy latest_known_as_of source 2026-08-01T00:00:00Z "
        "recorded 2026-08-23T12:00:00Z, provider without lineage clock",
        {
            "response_sha256": SITE_QUERY_RESPONSE_SHA,
            "query_hash": SITE_QUERY_HASH,
            "ledger_sha256": SITE_LEDGER_SHA,
        },
        {
            "response_sha256": result.sha256,
            "response_bytes": len(result.body),
            "query_hash": query_hash,
            "ledger_sha256": ledger_sha,
            "has_lineage_key": "lineage" in result.envelope,
            "sorted_keys_envelope_sha256": _sorted_keys_sha(result.envelope),
        },
        {
            "response_sha256": PIN_SITES["aapl_response_sha256"],
            "query_hash": PIN_SITES["aapl_query_hash"],
            "ledger_sha256": PIN_SITES["ledger_sha256"],
        },
    )

    # (2) pre-lineage source clock — the A2 child is not yet accepted
    result = execute_financial_query(
        body=_query_body(["total_assets"], [COMPARATIVE], PRE_LINEAGE_SOURCE, A4_RECORDED),
        provider=lineage,
    )
    cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
    prov = _provenance(cell)
    _pin_check(mismatches, case="pre_lineage_source_clock", key="source_occurrence_ids",
               recomputed=prov.get("source_occurrence_ids"), pinned=[PIN_A1_OCCURRENCE],
               site=PIN_SITES["pre_lineage_cell"])
    add(
        "pre_lineage_source_clock",
        "golden AAPL total_assets @2025-09-27 comparative, policy latest_known_as_of "
        "source 2026-07-30T00:00:00Z recorded 2026-09-20T00:00:00Z, provider with "
        "lineage clock 2026-08-25T12:00:00Z (receipt not yet source-visible)",
        {
            "response_sha256": SITE_QUERY_RESPONSE_SHA,
            "query_hash": SITE_QUERY_HASH,
            "source_occurrence_ids": SITE_OCCURRENCE_ID,
        },
        {
            "response_sha256": result.sha256,
            "query_hash": result.envelope["receipt"]["query_hash"],
            "cell_state": cell["state"],
            "cell_value": cell.get("value"),
            "source_occurrence_ids": prov.get("source_occurrence_ids"),
            "accession": prov.get("accession"),
            "form": prov.get("form"),
            "has_lineage_key": "lineage" in result.envelope,
        },
        {"source_occurrence_ids": PIN_SITES["pre_lineage_cell"]},
    )

    # (3) historical A3 cutoff under the lineage provider — never retro-repaired
    result = execute_financial_query(
        body=_query_body(GOLDEN_METRICS, GOLDEN_PERIODS, A3_SOURCE, A3_RECORDED),
        provider=lineage,
    )
    comparative = execute_financial_query(
        body=_query_body(["total_assets"], [COMPARATIVE], A3_SOURCE, A3_RECORDED),
        provider=lineage,
    )
    cell = _root_cell(comparative.envelope, "total_assets", start=None, end="2025-09-27")
    _pin_check(mismatches, case="historical_a3_cutoff", key="response_sha256",
               recomputed=result.sha256, pinned=PIN_AAPL_RESPONSE_SHA,
               site=PIN_SITES["aapl_response_sha256"])
    _pin_check(mismatches, case="historical_a3_cutoff", key="cell_state",
               recomputed=cell["state"], pinned="not_evaluable",
               site=PIN_SITES["historical_cell"])
    _pin_check(mismatches, case="historical_a3_cutoff", key="cell_reason",
               recomputed=cell.get("reason"), pinned=PIN_HISTORICAL_REASON,
               site=PIN_SITES["historical_cell"])
    add(
        "historical_a3_cutoff_preserves_not_evaluable",
        "lineage provider (clock 2026-08-25T12:00:00Z) queried at the historical A3 "
        "cutoff source 2026-08-01T00:00:00Z recorded 2026-08-23T12:00:00Z — golden "
        "metrics response plus the total_assets @2025-09-27 comparative cell",
        {
            "response_sha256": SITE_QUERY_RESPONSE_SHA,
            "query_hash": SITE_QUERY_HASH,
            "ledger_sha256": SITE_LEDGER_SHA,
        },
        {
            "response_sha256": result.sha256,
            "query_hash": result.envelope["receipt"]["query_hash"],
            "has_lineage_key": "lineage" in result.envelope,
            "comparative_cell_state": cell["state"],
            "comparative_cell_reason": cell.get("reason"),
            "ledger_sha256": lineage.conversion_report().ledger_sha256,
        },
        {
            "response_sha256": PIN_SITES["aapl_response_sha256"],
            "comparative_cell_state": PIN_SITES["historical_cell"],
            "comparative_cell_reason": PIN_SITES["historical_cell"],
        },
    )

    # (4) the three selection policies on the confirmed comparative cell @A4
    for selection, occurrence_pin, pin_key in (
        ("latest_known_as_of", PIN_A2_OCCURRENCE, "latest_known_cell"),
        ("as_reported", PIN_A1_OCCURRENCE, "as_reported_cell"),
    ):
        result = execute_financial_query(
            body=_query_body(
                ["total_assets"], [COMPARATIVE], A4_SOURCE, A4_RECORDED, selection=selection
            ),
            provider=lineage,
        )
        cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
        prov = _provenance(cell)
        _pin_check(mismatches, case=f"{selection}_a4_comparative", key="cell_value",
                   recomputed=cell.get("value"), pinned=PIN_LATEST_KNOWN_VALUE,
                   site=PIN_SITES[pin_key])
        _pin_check(mismatches, case=f"{selection}_a4_comparative", key="source_occurrence_ids",
                   recomputed=prov.get("source_occurrence_ids"), pinned=[occurrence_pin],
                   site=PIN_SITES[pin_key])
        confirmation = _first_confirmation(result.envelope)
        add(
            f"{selection}_a4_comparative",
            f"golden AAPL total_assets @2025-09-27 comparative, policy {selection} "
            "source 2026-09-20T00:00:00Z recorded 2026-09-20T00:00:00Z, lineage "
            "provider (clock 2026-08-25T12:00:00Z)",
            {
                "response_sha256": SITE_QUERY_RESPONSE_SHA,
                "query_hash": SITE_QUERY_HASH,
                "source_occurrence_ids": SITE_OCCURRENCE_ID,
                "first_confirmation": SITE_LINEAGE_DISCLOSURE,
            },
            {
                "response_sha256": result.sha256,
                "query_hash": result.envelope["receipt"]["query_hash"],
                "cell_state": cell["state"],
                "cell_value": cell.get("value"),
                "cell_reason": cell.get("reason"),
                "source_occurrence_ids": prov.get("source_occurrence_ids"),
                "accession": prov.get("accession"),
                "form": prov.get("form"),
                "lineage_confirmation_rows": len(
                    result.envelope.get("lineage", {}).get("confirmations") or []
                ),
                "first_confirmation": confirmation,
            },
            {
                "cell_value": PIN_SITES[pin_key],
                "source_occurrence_ids": PIN_SITES[pin_key],
            },
        )

    result = execute_financial_query(
        body=_query_body(
            ["total_assets"], [COMPARATIVE], A4_SOURCE, A4_RECORDED, selection="latest_restated"
        ),
        provider=lineage,
    )
    cell = _root_cell(result.envelope, "total_assets", start=None, end="2025-09-27")
    _pin_check(mismatches, case="latest_restated_a4_comparative", key="cell_state",
               recomputed=cell["state"], pinned="missing",
               site=PIN_SITES["latest_restated_cell"])
    _pin_check(mismatches, case="latest_restated_a4_comparative", key="cell_reason",
               recomputed=cell.get("reason"), pinned=PIN_LATEST_RESTATED_REASON,
               site=PIN_SITES["latest_restated_cell"])
    add(
        "latest_restated_a4_comparative",
        "golden AAPL total_assets @2025-09-27 comparative, policy latest_restated "
        "source 2026-09-20T00:00:00Z recorded 2026-09-20T00:00:00Z, lineage provider "
        "(clock 2026-08-25T12:00:00Z) — a confirmation is not a revision vintage",
        {
            "response_sha256": SITE_QUERY_RESPONSE_SHA,
            "query_hash": SITE_QUERY_HASH,
        },
        {
            "response_sha256": result.sha256,
            "query_hash": result.envelope["receipt"]["query_hash"],
            "cell_state": cell["state"],
            "cell_reason": cell.get("reason"),
            "cell_value": cell.get("value"),
        },
        {
            "cell_state": PIN_SITES["latest_restated_cell"],
            "cell_reason": PIN_SITES["latest_restated_cell"],
        },
    )

    # (5) kernel FIP1 query_hash pins (entity mmx.issuer.fip1)
    class _KernelProvider:
        def resolve(self, entity_id: str):
            return fip1_fixture_dataset(ROOT)

    kernel_cases = (
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
    )
    pin_key_by_case = {
        "kernel_fip1_as_reported_t1_t2": "as_reported_t1_t2",
        "kernel_fip1_latest_known_t1_t2": "latest_known_t1_t2",
        "kernel_fip1_latest_known_t3": "latest_known_t3",
        "kernel_fip1_latest_restated_t3": "latest_restated_t3",
        "kernel_fip1_mixed_t3": "mixed_t3",
    }
    for case, selection, source, recorded, metrics, periods in kernel_cases:
        result = execute_financial_query(
            body=_query_body(metrics, periods, source, recorded, selection=selection, entity=FIP1),
            provider=_KernelProvider(),
        )
        query_hash = result.envelope["receipt"]["query_hash"]
        _pin_check(mismatches, case=case, key="query_hash", recomputed=query_hash,
                   pinned=PIN_KERNEL_HASHES[pin_key_by_case[case]],
                   site=PIN_SITES["kernel_hashes"])
        add(
            case,
            f"FIP1 fixture entity, policy {selection} source {source} recorded "
            f"{recorded}, metrics {metrics}, periods {periods}",
            {
                "query_hash": SITE_QUERY_HASH,
                "response_sha256": SITE_QUERY_RESPONSE_SHA,
            },
            {
                "query_hash": query_hash,
                "response_sha256": result.sha256,
            },
            {"query_hash": PIN_SITES["kernel_hashes"]},
        )

    # (6) statement service golden calls — 10-K and 10-Q
    for case, accession, primary_name, pins in (
        ("statement_service_10k", A1, "aapl-20250927.htm", PIN_STATEMENT_10K),
        ("statement_service_10q", A2, "aapl-20260627.htm", PIN_STATEMENT_10Q),
    ):
        result = execute_financial_statements(
            body=_statement_body(accession),
            repo_root=ROOT,
            provider=GoldenAaplStatementProvider(ROOT),
        )
        package = envelope = result.envelope["package"]
        primary = next(
            (m for m in package["members"] if m["name"] == primary_name), None
        )
        witness = load_golden_aapl_package(ROOT, accession=accession).manifest[
            "acceptance_witness"
        ]
        values = {
            "response_sha256": result.sha256,
            "response_bytes": len(result.body),
            "index_sha256": envelope["index_sha256"],
            "primary_member_sha256": primary["content_sha256"] if primary else None,
            "witness_sha256": witness["content_sha256"],
            "witness_bytes": witness["byte_length"],
            "sorted_keys_envelope_sha256": _sorted_keys_sha(result.envelope),
        }
        for key, pinned in pins.items():
            _pin_check(mismatches, case=case, key=key, recomputed=values[key], pinned=pinned,
                       site=PIN_SITES["statement_10k" if accession == A1 else "statement_10q"])
        add(
            case,
            f"statement request entity {GOLDEN} accession {accession}, "
            "GoldenAaplStatementProvider over the committed golden filing package",
            {
                "response_sha256": SITE_STATEMENT_RESPONSE_SHA,
                "index_sha256": SITE_STATEMENT_PACKAGE,
                "primary_member_sha256": SITE_STATEMENT_PACKAGE,
                "witness_sha256": SITE_STATEMENT_PACKAGE,
            },
            values,
            {key: PIN_SITES["statement_10k" if accession == A1 else "statement_10q"]
             for key in pins},
        )
        del envelope, package

    # (7) witness digests of the committed FIP1 evidence + golden fixture identity
    dataset = fip1_packet_dataset(ROOT)
    digests = dataset.input_digests
    golden_fixture = json.loads(
        (ROOT / SITE_GOLDEN_PACKET_FIXTURE).read_text(encoding="utf-8")
    )
    _pin_check(mismatches, case="fip1_evidence_witnesses", key="golden_packet_id",
               recomputed=golden_fixture["packet_id"], pinned=PIN_GOLDEN_PACKET_ID,
               site=PIN_SITES["golden_packet_id"])
    add(
        "fip1_evidence_witnesses",
        "PacketEvidenceDigests over the committed FIP1 fixture/witness files, plus "
        "the packet identity recorded in expected_financial_intelligence_packet_v1.json",
        {
            "filing_package_fixture_sha256": SITE_WITNESS_DIGESTS,
            "companyfacts_witness_sha256": SITE_WITNESS_DIGESTS,
            "submissions_witness_sha256": SITE_WITNESS_DIGESTS,
            "golden_fixture_packet_id": SITE_GOLDEN_PACKET_FIXTURE,
        },
        {
            "filing_package_fixture_sha256": digests.filing_package_fixture_sha256,
            "companyfacts_witness_sha256": digests.companyfacts_witness_sha256,
            "submissions_witness_sha256": digests.submissions_witness_sha256,
            "golden_fixture_packet_id": golden_fixture["packet_id"],
            "golden_fixture_content_sha256": golden_fixture["content_sha256"],
        },
        {"golden_fixture_packet_id": PIN_SITES["golden_packet_id"]},
    )

    # (8) packet service — the golden T3 revenue packet and the rich research packet
    class _PacketProvider:
        def resolve(self, entity_id: str):
            return dataset

    for case, metrics, periods, pins in (
        ("packet_service_fip1_t3", ["revenue"], [FY2023], None),
        ("packet_service_fip1_rich_t3", RICH_METRICS, RICH_PERIODS, PIN_RICH_PACKET),
    ):
        result = execute_financial_packet(
            body=_packet_body(
                PACKET_REQUEST_SCHEMA, metrics=metrics, periods=periods,
                source=T3_KERNEL, recorded=T3_KERNEL_RECORDED,
            ),
            provider=_PacketProvider(),
        )
        values = {
            "response_sha256": result.response_sha256,
            "response_bytes": len(result.body),
            "packet_id": result.packet["packet_id"],
            "content_sha256": result.packet["content_sha256"],
        }
        if pins:
            for key, pinned in pins.items():
                _pin_check(mismatches, case=case, key=key, recomputed=values[key],
                           pinned=pinned, site=PIN_SITES["rich_packet"])
        add(
            case,
            f"packet request entity {FIP1}, policy latest_known_as_of source "
            f"{T3_KERNEL} recorded {T3_KERNEL_RECORDED}, metrics {metrics}, "
            f"periods {periods}",
            {
                "response_sha256": SITE_PACKET_RESPONSE_SHA,
                "packet_id": SITE_PACKET_IDENTITY,
                "content_sha256": SITE_PACKET_IDENTITY,
            },
            values,
            {key: PIN_SITES["rich_packet"] for key in pins} if pins else {},
        )

    # (9) revision service — full-response projection of the T3 packet
    revisions = execute_financial_revisions(
        body=_packet_body(
            REVISION_REQUEST_SCHEMA, metrics=["revenue"], periods=[FY2023],
            source=T3_KERNEL, recorded=T3_KERNEL_RECORDED,
        ),
        provider=_PacketProvider(),
    )
    add(
        "revision_service_fip1_t3",
        f"revision request entity {FIP1}, policy latest_known_as_of source "
        f"{T3_KERNEL} recorded {T3_KERNEL_RECORDED}, metrics [revenue], periods [FY2023]",
        {
            "response_sha256": SITE_REVISION_RESPONSE_SHA,
            "packet_ref.packet_id": SITE_PACKET_IDENTITY,
        },
        {
            "response_sha256": revisions.sha256,
            "response_bytes": len(revisions.body),
            "packet_ref": revisions.envelope["packet_ref"],
            "revision_rows": len(revisions.envelope["revisions"]),
        },
    )

    # (10) API transport — X-FIF-Response-SHA256 equals the served body sha
    from fastapi import FastAPI  # noqa: PLC0415
    from fastapi.testclient import TestClient  # noqa: PLC0415
    import app.forensics as forensics_api  # noqa: PLC0415

    saved_repo = forensics_api.REPO
    forensics_api.REPO = ROOT
    try:
        api = FastAPI()
        api.include_router(forensics_api.router)
        api.dependency_overrides[forensics_api.require_site_full_user] = lambda: {
            "id": "paid-user"
        }
        api_body = _query_body(["total_assets"], [COMPARATIVE], A4_SOURCE, A4_RECORDED)
        with TestClient(api, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/forensics/v1/financial/query",
                content=api_body,
                headers={"content-type": "application/json"},
            )
        header_sha = response.headers.get("X-FIF-Response-SHA256")
        body_sha = hashlib.sha256(response.content).hexdigest()
        direct = execute_financial_query(
            body=api_body,
            provider=GoldenAaplFinancialQueryProvider(
                ROOT, lineage_evidence_available_at=FIF3A4_LINEAGE_AVAILABLE_AT
            ),
        )
        values = {
            "status_code": response.status_code,
            "header_sha256": header_sha,
            "body_sha256": body_sha,
            "header_equals_body_sha256": header_sha == body_sha,
            "direct_service_response_sha256": direct.sha256,
            "api_body_equals_service_bytes": body_sha == direct.sha256,
        }
        add(
            "api_transport_query_a4_comparative",
            "POST /api/forensics/v1/financial/query (router-only app, paid-user "
            "dependency override), golden AAPL total_assets @2025-09-27 comparative, "
            "policy latest_known_as_of source 2026-09-20T00:00:00Z recorded "
            "2026-09-20T00:00:00Z; production default provider clock "
            "FIF3A4_LINEAGE_AVAILABLE_AT=2026-09-20T00:00:00Z",
            {
                "header_sha256": SITE_API_HEADER,
                "body_sha256": SITE_QUERY_RESPONSE_SHA,
            },
            values,
        )
    finally:
        forensics_api.REPO = saved_repo

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "seal": "fif-t2-compatibility-seal",
        "base_commit": _head_commit(),
        "expected_base_commit": EXPECTED_BASE_COMMIT,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "tool": "scripts/fif_compatibility_seal.py",
        "tool_command": TOOL_COMMAND,
        "determinism_note": (
            "every sealed value is a pure function of the committed tree at "
            "base_commit; generated_at is execution metadata and is the only "
            "field that varies between runs"
        ),
        "entries": entries,
    }
    return manifest, mismatches


def _head_commit() -> str:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise _SealFailure(f"cannot resolve HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", default=str(DEFAULT_OUT), help="manifest output path (default: committed fixture)"
    )
    args = parser.parse_args(argv)

    manifest, mismatches = build_manifest()
    if mismatches:
        print(
            "FIF T2 seal REFUSED: recomputation disagrees with an existing "
            f"test-pinned literal in {len(mismatches)} case(s) — nothing written.\n"
            + "\n".join(mismatches),
            file=sys.stderr,
        )
        return 1
    if manifest["base_commit"] != EXPECTED_BASE_COMMIT:
        print(
            f"worktree-sparse-style warning: HEAD {manifest['base_commit']} is not the "
            f"expected pre-T1 base {EXPECTED_BASE_COMMIT}; recording actual HEAD — "
            "the pinning test module will fail unless it expects this commit.",
            file=sys.stderr,
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"fif-compatibility-seal: wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    print(f"  base_commit : {manifest['base_commit']}")
    print(f"  entries     : {len(manifest['entries'])}")
    pinned = sum(1 for e in manifest["entries"] if e["pins"])
    print(f"  pinned fams : {pinned} (all recomputations matched their literals)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
