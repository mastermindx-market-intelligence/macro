"""BEA Global Value Chain Analyzer: guarded industry-context research projection.

No fetching, filesystem access, native dataset registration, GMI graph mutation,
company/ticker inference, signal production, or public emission. The only source
is a caller-supplied, already-qualified *May 21, 2026 edition* Data Lab row.
The historical accounting year is NOT a historical source-availability clock.

This deliberately does not implement another temporal, rights, identity, or
source registry. Native source admission belongs to the existing Data OS owner.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import re
from typing import Any

from lib.dataos.temporal import TemporalError, utc

PANEL_SHA256 = "f3ecdda2a8161b2f4ffa893d9d5ff43896280339ca85d76240d4979404e95448"
LINEAGE_SHA256 = "e8856b6f546d55b8e0c41561cb0e60f28ddcd06a78fd04f70d05355890c745a7"
# Separate testable metadata-receipt pin from the immutable signed row contract.
METADATA_LINEAGE_SHA256 = LINEAGE_SHA256
BUILD_RECEIPT_SHA256 = "ff6e2b3070e10f45ed2d14508c0425cde2aa5c687f0e289f9b7010dcdcf215ed"
HARDENING_RECEIPT_SHA256 = "dcb553712321a37f297fe7e33e6ac2095c0165a9207bb87afdf7fad5185322b4"
USE_PANEL_SHA256 = "99059f4530f6a2de18b571a5e9378f44fffece256f5c9c2516ee8717203beaa5"
QUALIFICATION_RECEIPT_SHA256 = "c9eeb8e3469eef23749e7edafdf88ff3e9a18d1656b6c054e2d67a77fc5a0589"
DECLARED_TOTAL_INDUSTRY_VIEW_BYTES = 353_940_588
# All 138 accepted views are below 2.7 MiB. Bound owner-supplied bytes.
MAX_SUPPLIED_INDUSTRY_VIEW_BYTES = 4 * 1024 * 1024
EXPECTED_INDUSTRY_VIEW_COUNT = 138
PUBLISHER_EDITION_DATE = "2026-05-21"
EXACT_CODE_NAMESPACE = "BEA_APP157_MAY2026_EXACT"
SOURCE_KIND = "industry_commodity_input"
# Accepted immutable view-build receipt: 8 accounting years x 139 commodities.
SOURCE_ROWS_PER_INDUSTRY = 8 * 139
# Bound interactive private research reads; this is not a 138-file bulk producer.
MAX_COMPARISON_INDUSTRIES = 12
RESEARCH_VIEW_SUBDIR = (
    "bea_2024_public_itable_research/"
    "bea_2017_2022_may2026_remaining_six_regions/"
    "data_workspace_views_20261011"
)
REGIONS = (
    ("canada", "Canada"),
    ("china", "China"),
    ("europe", "Europe"),
    ("japan", "Japan"),
    ("mexico", "Mexico"),
    ("rest_of_asia_and_pacific", "Rest of Asia and Pacific"),
    ("rest_of_world", "Rest of World"),
)
_AMOUNT_FIELDS = (
    "total_use_million_USD",
    "world_import_million_USD",
    *(f"{key}_import_million_USD" for key, _ in REGIONS),
)
_REQUIRED_NULLS = (
    "original_historical_available_at",
    "publication_timestamp",
    "native_ingested_at",
    "native_known_at",
    "native_revision_seq",
    "canonical_industry_id",
    "canonical_security_id",
)
_DENIED_BOOL_FIELDS = (
    "dataos_native_admitted",
    "historical_pit_eligible",
    "named_company_relationship",
    "may_publish",
    "may_rank",
    "may_train",
    "may_trade",
)
_SHARE_REASONS = frozenset({
    "WORLD_IMPORT_NONPOSITIVE",
    "RESEARCH_DENOMINATOR_BELOW_50M_FLOOR",
    "SOURCE_NEGATIVE_REGION_ADJUSTMENT",
    "REGION_EXCEEDS_WORLD_DENOMINATOR",
    "PUBLISHER_ROUNDING_MATERIAL_TO_DENOMINATOR",
})
_CODE = re.compile(r"^[A-Z0-9]{2,9}$")


class BEAContextRefused(ValueError):
    """Research source or requested authority is unqualified."""


def _integer(row: Mapping[str, Any], name: str) -> int:
    value = row.get(name)
    if type(value) is not int:
        raise BEAContextRefused(f"{name}: signed integer USD millions required")
    return value


def _date_only_capture(row: Mapping[str, Any]) -> str:
    if (row.get("publication_date") != PUBLISHER_EDITION_DATE
            or row.get("publication_precision") != "DAY"
            or row.get("publication_timestamp_null_reason") != "PUBLISHER_DAY_PRECISION_ONLY"):
        raise BEAContextRefused("publisher-edition or source date precision mismatch")
    value = row.get("research_source_capture_completed_at")
    try:
        parsed = utc(value)
    except (TemporalError, TypeError, ValueError) as exc:
        raise BEAContextRefused("actual source capture requires offset-aware timestamp") from exc
    if parsed.date().isoformat() < PUBLISHER_EDITION_DATE:
        raise BEAContextRefused("research capture before publisher edition")
    return parsed.isoformat()


def _source_guard(
    row: Mapping[str, Any], *, industry: str, commodity: str,
    expected_lineage_sha256: str = LINEAGE_SHA256,
) -> str:
    if not isinstance(row, Mapping):
        raise BEAContextRefused("unrecognized research row")
    if not all(isinstance(x, str) and _CODE.fullmatch(x) for x in (industry, commodity)):
        raise BEAContextRefused("exact BEA source code required, not company alias")
    if (row.get("industry_code_exact") != industry
            or row.get("commodity_code_exact") != commodity
            or row.get("code_namespace") != EXACT_CODE_NAMESPACE
            or row.get("source_kind") != SOURCE_KIND):
        raise BEAContextRefused("BEA code/namespace or industry-input source mismatch")
    if (row.get("source_lineage_sha256") != expected_lineage_sha256
            or row.get("source_lineage_file") != "source_lineage.json"):
        raise BEAContextRefused("unrecognized immutable source lineage")
    if (row.get("source_units") != "million USD"
            or type(row.get("accounting_year")) is not int
            or row["accounting_year"] not in range(2017, 2025)):
        raise BEAContextRefused("source unit or accounting period mismatch")
    for key in _REQUIRED_NULLS:
        if key not in row or row[key] is not None:
            raise BEAContextRefused(f"{key}: native identity/clock unavailable")
    for key in _DENIED_BOOL_FIELDS:
        if row.get(key) is not False:
            raise BEAContextRefused(f"{key}: source rights or authority changed")
    if row.get("period_end") != f'{row["accounting_year"]}-12-31':
        raise BEAContextRefused("accounting period is not a publication clock")
    if row.get("period_end_is_availability") is not False:
        raise BEAContextRefused("period-end must not claim availability")
    if (row.get("schema") != "mastermind.bea_industry_commodity_input_research_row/v1"
            or row.get("source_lineage_accounting_year") != row["accounting_year"]
            or row.get("canonical_identity_null_reason") != "CANONICAL_IDENTITY_NOT_ADOPTED"
            or row.get("native_fields_null_reason") != "NATIVE_SOURCE_NOT_ADOPTED"
            or row.get("capture_clock_semantics") != "LATEST_COMPLETION_OF_NINE_BOUND_SOURCE_CAPTURES"):
        raise BEAContextRefused("source row or native admission semantics changed")
    if row.get("historical_availability_null_reason") != "HISTORICAL_AVAILABILITY_UNVERIFIED":
        raise BEAContextRefused("unknown historical availability reason changed")
    expected_mapping = "UNRESOLVED_5241X_VS_5241XX" if industry == "5241X" else "NOT_APPLIED"
    if row.get("legacy_industry_mapping_state") != expected_mapping:
        raise BEAContextRefused("unadopted code crosswalk cannot be asserted")
    if not isinstance(row.get("industry_name"), str) or not row["industry_name"].strip():
        raise BEAContextRefused("original using-industry name required")
    if not isinstance(row.get("commodity_name"), str) or not row["commodity_name"].strip():
        raise BEAContextRefused("original commodity name required")
    return _date_only_capture(row)


def _shares(row: Mapping[str, Any], world: int, regions: dict[str, int], diff: int) -> tuple[dict[str, str] | None, list[str]]:
    reasons: list[str] = []
    if world <= 0:
        reasons.append("WORLD_IMPORT_NONPOSITIVE")
    elif world < 50:
        reasons.append("RESEARCH_DENOMINATOR_BELOW_50M_FLOOR")
    if any(v < 0 for v in regions.values()):
        reasons.append("SOURCE_NEGATIVE_REGION_ADJUSTMENT")
    if any(v > world for v in regions.values()):
        reasons.append("REGION_EXCEEDS_WORLD_DENOMINATOR")
    if world > 0 and abs(diff) > min(3, world * .05):
        reasons.append("PUBLISHER_ROUNDING_MATERIAL_TO_DENOMINATOR")
    reason_str = row.get("research_ratio_null_reasons_json")
    try:
        reported_reasons = json.loads(reason_str)
    except (TypeError, ValueError) as exc:
        raise BEAContextRefused("missing or malformed typed ratio-null reasons") from exc
    if (not isinstance(reported_reasons, list)
            or len(reported_reasons) != len(set(map(str, reported_reasons)))
            or any(not isinstance(x, str) or x not in _SHARE_REASONS for x in reported_reasons)
            or set(reported_reasons) != set(reasons)):
        raise BEAContextRefused("ratio-null reasons no longer match signed source")
    if reasons:
        if any(row.get(f"{key}_fraction_of_world_import") is not None for key, _ in REGIONS):
            raise BEAContextRefused("ineligible ratio cannot be displayed")
        if row.get("research_ratio_null_reason") != reasons[0]:
            raise BEAContextRefused("primary ratio-null reason changed")
        return None, reasons
    if row.get("research_ratio_null_reason") is not None:
        raise BEAContextRefused("eligible ratio has unexplained null reason")
    expected = {}
    for key, _ in REGIONS:
        calculated = str((Decimal(regions[key]) / Decimal(world)).quantize(
            Decimal("0.0000001"), rounding=ROUND_HALF_EVEN
        ))
        reported = row.get(f"{key}_fraction_of_world_import")
        if reported != calculated:
            raise BEAContextRefused(f"{key} origin share mismatches the source values")
        expected[key] = calculated
    return expected, []


def adapt_industry_commodity_input(
    row: Mapping[str, Any], *, industry_code: str, commodity_code: str,
    as_of: object = None, purpose: str = "private_research"
) -> dict[str, Any]:
    """Validate a qualified Data Lab row and emit *non-published* research context.

    This is deliberately not an as-of reader: the source's historical first-known
    clock is unknown and its day-only revised 2026 edition is retrospective.
    Any promotion request fails regardless of caller identity or account mode.
    """
    if as_of is not None:
        raise BEAContextRefused("historical/current native as-of requires admitted source clock")
    if purpose != "private_research":
        raise BEAContextRefused("BEA source not admitted for public, predictive, or trading use")
    capture_at = _source_guard(row, industry=industry_code, commodity=commodity_code)
    amounts = {field: _integer(row, field) for field in _AMOUNT_FIELDS}
    world = amounts["world_import_million_USD"]
    regions = {key: amounts[f"{key}_import_million_USD"] for key, _ in REGIONS}
    diff = world - sum(regions.values())
    if type(row.get("source_rounding_difference_million_USD")) is not int or (
            diff != row["source_rounding_difference_million_USD"] or abs(diff) > 3):
        raise BEAContextRefused("source world/region rounding no longer reconciles")
    shares, reasons = _shares(row, world, regions, diff)
    return {
        "schema": "market_ontology.bea_industry_commodity_context_research/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "source_kind": SOURCE_KIND,
        "measurement_class": "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION",
        "source_methodology": {
            "source_url": "https://www.bea.gov/help/faq/453",
            "method": "commodity_import_share_of_domestic_supply_imputation",
            "industry_specific_import_transaction_observed": False,
            "named_supplier_customer_pair_observed": False,
            "industry_input_allocation_is_estimate": True,
        },
        "source": {
            "publisher": "U.S. Bureau of Economic Analysis",
            "edition_date": PUBLISHER_EDITION_DATE,
            "edition_precision": "DAY",
            "publication_timestamp": None,
            "original_historical_known_at": None,
            "research_capture_at": capture_at,
            "full_2017_2024_panel_sha256": PANEL_SHA256,
            "source_lineage_sha256": LINEAGE_SHA256,
        },
        "accounting_year": row["accounting_year"],
        "period_end_not_known_at": row["period_end"],
        "using_industry": {"namespace": EXACT_CODE_NAMESPACE,
                           "code": industry_code, "name": row["industry_name"],
                           "legacy_mapping": row.get("legacy_industry_mapping_state")},
        "input_commodity": {"namespace": EXACT_CODE_NAMESPACE,
                            "code": commodity_code, "name": row["commodity_name"]},
        "total_use_million_USD": amounts["total_use_million_USD"],
        "world_import_million_USD": world,
        "regional_import_million_USD": regions,
        "regional_origin_fraction_of_world": shares,
        "source_rounding_difference_million_USD": diff,
        "ratio_null_reasons": reasons,
        "historical_pit_eligible": False,
        "upstream_source_read_attestation_required": True,
        "source_bytes_authenticated_by_this_projection": False,
        "source_adopted": False,
        "named_supplier_customer_evidence": False,
        "graph_edge": None,
        "rank_size_or_trade_authority": False,
        "publishable": False,
    }


def adapt_eight_year_input_history(
    rows: Iterable[Mapping[str, Any]], *, industry_code: str, commodity_code: str,
    as_of: object = None, purpose: str = "private_research"
) -> dict[str, Any]:
    """Require exactly eight ordered years; refuse unbounded caller iterables."""
    if purpose != "private_research" or as_of is not None:
        raise BEAContextRefused(
            "history projection is research-only and not PIT-readable"
        )
    bounded_rows = []
    for row in rows:
        if len(bounded_rows) == 8:
            raise BEAContextRefused("more than eight industry input rows")
        bounded_rows.append(row)
    if len(bounded_rows) != 8:
        raise BEAContextRefused("exactly eight industry input rows required")
    observations = [
        adapt_industry_commodity_input(row, industry_code=industry_code,
                                       commodity_code=commodity_code,
                                       as_of=as_of, purpose=purpose)
        for row in bounded_rows
    ]
    if [x["accounting_year"] for x in observations] != list(range(2017, 2025)):
        raise BEAContextRefused("eight distinct ordered source years required")
    return {
        "schema": "market_ontology.bea_industry_input_history_research/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "measurement_class": "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION",
        "industry_specific_transactions_observed": False,
        "using_industry_code_exact": industry_code,
        "commodity_code_exact": commodity_code,
        "observations": observations,
        "no_named_company_relationships": True,
        "source_adopted": False,
        "public_or_predictive_use": False,
    }

def adapt_workspace_bea_history(
    response: Mapping[str, Any], *, industry_code: str, commodity_code: str,
    purpose: str = "private_research", as_of: object = None,
) -> dict[str, Any]:
    """Consume one *already completed* canonical DataWorkspace research read.

    This function never opens a source file, creates a root binding, selects
    credentials, admits rights, or turns a stat-based file version into a
    cryptographic source attestation. The host-owned DataWorkspace must have
    already performed its own read. Call with a 9-row limit so a complete scan
    distinguishes exactly eight annual observations from an extra ninth row.
    """
    if purpose != "private_research" or as_of is not None:
        raise BEAContextRefused("workspace evidence has no public or PIT authority")
    if (not isinstance(industry_code, str) or not _CODE.fullmatch(industry_code)
            or not isinstance(commodity_code, str) or not _CODE.fullmatch(commodity_code)):
        raise BEAContextRefused("exact BEA code required")
    if (not isinstance(response, Mapping)
            or response.get("schema_version") != "mastermind.data_workspace/v1"
            or response.get("action") != "read"
            or response.get("source_access") != "read_only"
            or response.get("production_qualification") != "NOT_ESTABLISHED_BY_THIS_ADAPTER"
            or response.get("temporal_caution") !=
            "Filtering stored rows does not reconstruct point-in-time availability."):
        raise BEAContextRefused("not a qualified read-only workspace envelope")

    source, query, result = (
        response.get("source"), response.get("query"), response.get("result")
    )
    if not all(isinstance(item, Mapping) for item in (source, query, result)):
        raise BEAContextRefused("workspace source/query/result envelope missing")

    ref = source.get("ref")
    version = source.get("file_version")
    if (not isinstance(ref, str) or not ref.startswith("free_source_research:")
            or not isinstance(version, str)
            or not re.fullmatch(r"statv1:[0-9a-f]{64}", version)):
        raise BEAContextRefused("workspace binding or version not recognized")
    relative = ref.split(":", 1)[1]
    expected_relative = f"{RESEARCH_VIEW_SUBDIR}/industry_{industry_code}.jsonl"
    if (relative != expected_relative
            or source.get("root_alias") != "free_source_research"
            or source.get("relative_path") != relative
            or source.get("evidence_kind") not in {"research_capture", "research_sample"}
            or source.get("registry_admission") != "NOT_INFERRED_FROM_FILE_PRESENCE"
            or source.get("content_sha256") is not None
            or source.get("file_version_basis") !=
            "device_inode_size_mtime_ctime_not_content_hash"
            or type(source.get("file_bytes")) is not int
            or source["file_bytes"] <= 0):
        raise BEAContextRefused("research file is not an admitted source proof")

    if (set(query) != {"ref", "file_version", "columns", "time_column", "start",
                       "end", "equals", "offset", "limit"}
            or query.get("ref") != ref
            or query.get("file_version") != version
            or query.get("columns") is not None
            or any(query.get(k) is not None for k in ("time_column", "start", "end"))
            or query.get("equals") != {"commodity_code_exact": commodity_code}
            or type(query.get("offset")) is not int or query["offset"] != 0
            or type(query.get("limit")) is not int or query["limit"] != 9):
        raise BEAContextRefused("workspace query must scan exact full-source commodity history")
    try:
        receipt = hashlib.sha256(json.dumps(
            dict(query), sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise BEAContextRefused("unverifiable workspace query") from exc
    if response.get("query_receipt_sha256") != receipt:
        raise BEAContextRefused("workspace query receipt mismatch")

    rows = result.get("rows")
    positions = result.get("row_positions")
    scanned = result.get("scanned_rows")
    if (result.get("scan_complete") is not True
            or result.get("next_offset") is not None
            or type(scanned) is not int or scanned != SOURCE_ROWS_PER_INDUSTRY
            or not isinstance(rows, list) or len(rows) != 8
            or not isinstance(positions, list) or len(positions) != 8
            or any(type(n) is not int or n < 0 for n in positions)
            or positions != sorted(set(positions))
            or positions[-1] >= scanned):
        raise BEAContextRefused("workspace scan incomplete, partial or ambiguous")
    try:
        observed_at = utc(response.get("observed_at"))
    except (TemporalError, TypeError, ValueError) as exc:
        raise BEAContextRefused("workspace read observation instant unavailable") from exc
    history = adapt_eight_year_input_history(
        rows, industry_code=industry_code, commodity_code=commodity_code,
        purpose=purpose, as_of=as_of,
    )
    if observed_at < max(utc(item["source"]["research_capture_at"])
                         for item in history["observations"]):
        raise BEAContextRefused("workspace read cannot precede underlying capture")
    history["reader_provenance"] = {
        "canonical_reader": "lib.dataos.web_workspace.DataWorkspace.read",
        "root_alias": "free_source_research",
        "read_observed_at": observed_at.isoformat(),
        "stat_file_version": version,
        "query_receipt_sha256": receipt,
        "original_file_content_sha256_verified": False,
        "native_dataset_admission": False,
        "public_or_historical_pit_serving": False,
        "source_row_count": len(rows),
        "source_records_scanned": scanned,
        "scan_complete": True,
    }
    return history


def compose_bea_industry_accounting_change(
    response: Mapping[str, Any], *, industry_code: str, commodity_code: str,
    purpose: str = "private_research", as_of: object = None,
) -> dict[str, Any]:
    """Deterministic descriptive 2023->2024 brief over the incumbent Data OS read.

    The source is a retrospectively revised *imputed* import-allocation matrix.
    A signed dollar change is arithmetic only; it asserts no causation, named
    counterparty, demand forecast, company exposure or historical availability.
    """
    history = adapt_workspace_bea_history(
        response, industry_code=industry_code, commodity_code=commodity_code,
        purpose=purpose, as_of=as_of,
    )
    earlier, latest = history["observations"][-2:]
    if earlier["accounting_year"] != 2023 or latest["accounting_year"] != 2024:
        raise BEAContextRefused("only exact 2023->2024 research comparison admitted")
    def signed_change(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "total_use": after["total_use_million_USD"] - before["total_use_million_USD"],
            "world_import": after["world_import_million_USD"] - before["world_import_million_USD"],
            "regions": {
                name: (after["regional_import_million_USD"][name]
                       - before["regional_import_million_USD"][name])
                for name, _ in REGIONS
            },
        }

    annual = history["observations"]
    adjacent = [
        {
            "earlier_accounting_year": annual[i - 1]["accounting_year"],
            "later_accounting_year": annual[i]["accounting_year"],
            "earlier_research_capture_at": annual[i - 1]["source"]["research_capture_at"],
            "later_research_capture_at": annual[i]["source"]["research_capture_at"],
            "publisher_edition_date": PUBLISHER_EDITION_DATE,
            "publisher_edition_precision": "DAY",
            "original_historical_known_at": None,
            "historical_pit_eligible": False,
            "signed_change_million_USD": signed_change(annual[i - 1], annual[i]),
        }
        for i in range(1, len(annual))
    ]
    return {
        "schema": "market_ontology.bea_industry_accounting_change_research/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "measurement_class": "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION",
        "source_methodology": latest["source_methodology"],
        "source": latest["source"],
        "source_capture_window_utc": {
            "earliest": min(
                utc(row["source"]["research_capture_at"])
                for row in history["observations"]
            ).isoformat(),
            "latest": max(
                utc(row["source"]["research_capture_at"])
                for row in history["observations"]
            ).isoformat(),
        },
        "reader_provenance": history["reader_provenance"],
        "using_industry": latest["using_industry"],
        "input_commodity": latest["input_commodity"],
        "periods": {
            "earlier_year": 2023,
            "latest_year": 2024,
            "original_historical_known_at": None,
        },
        "annual_observations": [
            {
                "accounting_year": row["accounting_year"],
                "period_end_not_known_at": row["period_end_not_known_at"],
                "publisher_edition_date": row["source"]["edition_date"],
                "publisher_edition_precision": row["source"]["edition_precision"],
                "research_capture_at": row["source"]["research_capture_at"],
                "original_historical_known_at": row["source"]["original_historical_known_at"],
                "using_industry": row["using_industry"],
                "input_commodity": row["input_commodity"],
                "total_use_million_USD": row["total_use_million_USD"],
                "world_import_million_USD": row["world_import_million_USD"],
                "source_rounding_difference_million_USD": row[
                    "source_rounding_difference_million_USD"
                ],
                "regional_import_million_USD": row["regional_import_million_USD"],
                "regional_origin_fraction_of_world": row[
                    "regional_origin_fraction_of_world"
                ],
                "ratio_null_reasons": row["ratio_null_reasons"],
            }
            for row in history["observations"]
        ],
        "signed_change_2024_minus_2023_million_USD": signed_change(earlier, latest),
        "signed_change_2024_minus_2017_million_USD": signed_change(annual[0], latest),
        "consecutive_year_signed_changes_million_USD": adjacent,
        "publisher_day_precision_only": True,
        "historical_pit_eligible": False,
        "source_bytes_authenticated_by_this_projection": False,
        "dataos_native_admitted": False,
        "named_company_relationship": False,
        "estimated_allocation_not_observed_purchase": True,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
    }


def read_private_bea_accounting_brief(
    workspace: Any, *, industry_code: str, commodity_code: str,
    purpose: str = "private_research", as_of: object = None,
) -> dict[str, Any]:
    """Query the incumbent owner-bound DataWorkspace for research, never for release.

    The caller supplies an already-authorized DataWorkspace with its host-owned
    research root. We do not create a root, grant entitlement, guess a source
    clock, or substitute a new file opener. Version fencing is delegated to
    DataWorkspace.describe/read and evidence shape to the existing projection.
    """
    if purpose != "private_research" or as_of is not None:
        raise BEAContextRefused("workspace query is research-only and not PIT-readable")
    if (not isinstance(industry_code, str) or not _CODE.fullmatch(industry_code)
            or not isinstance(commodity_code, str) or not _CODE.fullmatch(commodity_code)):
        raise BEAContextRefused("exact BEA industry and commodity codes required")

    from lib.dataos.web_workspace import DataWorkspace, WorkspaceError

    if type(workspace) is not DataWorkspace:
        raise BEAContextRefused("host-bound DataWorkspace required")

    ref = f"free_source_research:{RESEARCH_VIEW_SUBDIR}/industry_{industry_code}.jsonl"
    try:
        description = workspace.describe(ref)
        if (description.get("schema_version") != "mastermind.data_workspace/v1"
                or description.get("action") != "describe_file"
                or description.get("production_qualification") !=
                "NOT_ESTABLISHED_BY_THIS_ADAPTER"):
            raise BEAContextRefused("DataWorkspace file description refused")
        source = description.get("source")
        details = description.get("details")
        if (not isinstance(source, Mapping) or source.get("ref") != ref
                or not isinstance(details, Mapping)
                or details.get("format") != "jsonl"
                or details.get("schema_complete") is not True
                or details.get("scan_complete") is not True
                or type(details.get("row_count")) is not int
                or details["row_count"] != SOURCE_ROWS_PER_INDUSTRY):
            raise BEAContextRefused("expected read-only research JSONL source")
        version = source.get("file_version")
        if not isinstance(version, str):
            raise BEAContextRefused("missing original file version")
        result = workspace.read(
            ref,
            columns=None,
            equals={"commodity_code_exact": commodity_code},
            offset=0, limit=9,
            expected_version=version,
        )
    except WorkspaceError as exc:
        # WorkspaceError has closed error codes, never native paths/secrets.
        raise BEAContextRefused(f"canonical DataWorkspace source refused: {exc.code}") from None
    return compose_bea_industry_accounting_change(
        result, industry_code=industry_code, commodity_code=commodity_code,
        purpose=purpose, as_of=as_of,
    )


def compare_private_bea_using_industries(
    workspace: Any, *, industry_codes: Sequence[str], commodity_code: str,
    purpose: str = "private_research", as_of: object = None,
    research_receipts: tuple[bytes, bytes, bytes] | None = None,
) -> dict[str, Any]:
    """Compare one imputed commodity input across bounded BEA using industries.

    Preserves caller order rather than ranking. An imported commodity *input*
    is neither a company-to-company relationship nor an observed supply route.
    Every source is read through the existing DataWorkspace with a separately
    verified 1,112-record industry view and original exact source code.
    Any missing, version-changed, or refused member aborts the whole result.
    """
    if purpose != "private_research" or as_of is not None:
        raise BEAContextRefused("cross-industry research is not public or PIT eligible")
    if not isinstance(commodity_code, str) or not _CODE.fullmatch(commodity_code):
        raise BEAContextRefused("exact BEA input commodity code required")
    if (not isinstance(industry_codes, (tuple, list))
            or not 1 <= len(industry_codes) <= MAX_COMPARISON_INDUSTRIES
            or any(not isinstance(code, str) or not _CODE.fullmatch(code)
                   for code in industry_codes)
            or len(set(industry_codes)) != len(industry_codes)):
        raise BEAContextRefused(
            "one to twelve distinct exact BEA using-industry codes required"
        )
    from lib.dataos.web_workspace import DataWorkspace
    if type(workspace) is not DataWorkspace:
        raise BEAContextRefused("host-bound DataWorkspace required")
    receipt_evidence = None
    if research_receipts is not None:
        if (not isinstance(research_receipts, tuple)
                or len(research_receipts) != 3
                or any(type(item) is not bytes for item in research_receipts)):
            raise BEAContextRefused("three immutable metadata receipt byte strings required")
        # Authenticate only the accepted metadata claims, BEFORE opening a view
        # through the existing reader. Neither result verifies view file bytes.
        receipt_evidence = qualify_private_bea_research_manifest(
            *research_receipts, industry_codes=industry_codes,
        )

    briefs: list[dict[str, Any]] = []
    for code in industry_codes:
        # Do not degrade a missing industry to zero, and never return a partial
        # cross-industry panel. Only the host-owned reader may open source files.
        brief = read_private_bea_accounting_brief(
            workspace, industry_code=code, commodity_code=commodity_code,
            purpose=purpose, as_of=as_of,
        )
        if (brief["using_industry"]["code"] != code
                or brief["input_commodity"]["code"] != commodity_code
                or brief["source"]["edition_date"] != PUBLISHER_EDITION_DATE
                or brief["reader_provenance"]["source_records_scanned"]
                != SOURCE_ROWS_PER_INDUSTRY):
            raise BEAContextRefused("source history differs across using industries")
        briefs.append(brief)

    return {
        "schema": "market_ontology.bea_cross_industry_input_research/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "measurement_class": "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION",
        "source_kind": SOURCE_KIND,
        "exact_code_namespace": EXACT_CODE_NAMESPACE,
        "input_commodity_code_exact": commodity_code,
        "publisher_edition_date": PUBLISHER_EDITION_DATE,
        "publisher_edition_precision": "DAY",
        "requested_using_industry_codes": list(industry_codes),
        "returned_using_industry_count": len(briefs),
        "source_records_scanned": SOURCE_ROWS_PER_INDUSTRY * len(briefs),
        "complete_requested_cohort": True,
        "industry_research_briefs": briefs,
        "pinned_research_manifest_evidence": receipt_evidence,
        "original_view_bytes_hashed_by_this_comparison": False,
        "comparability": "SAME_SOURCE_EDITION_SAME_COMMODITY_DISTINCT_USING_INDUSTRIES",
        "industry_input_allocation_is_estimate": True,
        "named_company_supplier_buyer_evidence": False,
        "original_historical_known_at": None,
        "historical_pit_eligible": False,
        "source_bytes_authenticated_by_this_projection": False,
        "dataos_native_admitted": False,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
    }


def _pinned_research_receipt_document(raw: bytes, expected_sha: str) -> dict[str, Any]:
    """Strictly parse pre-existing *metadata*, never open original source files."""
    if type(raw) is not bytes or not 1 <= len(raw) <= 65_536:
        raise BEAContextRefused("bounded immutable research metadata bytes required")
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise BEAContextRefused("research metadata digest differs from accepted receipt")

    def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        doc: dict[str, Any] = {}
        for key, value in pairs:
            if key in doc:
                raise BEAContextRefused("duplicate key in source metadata")
            doc[key] = value
        return doc

    def no_nonfinite(_value: str) -> None:
        raise BEAContextRefused("nonfinite source metadata refused")

    try:
        result = json.loads(
            raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys,
            parse_constant=no_nonfinite,
        )
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        raise BEAContextRefused("malformed source receipt metadata") from exc
    if not isinstance(result, dict):
        raise BEAContextRefused("research metadata must be a JSON object")
    return result


def qualify_private_bea_research_manifest(
    build_receipt_bytes: bytes, lineage_bytes: bytes, hardening_bytes: bytes,
    *, industry_codes: Sequence[str] = (),
) -> dict[str, Any]:
    """Validate the accepted BEA *builder receipts*, not original source bytes.

    Callers provide three already-retained metadata bytes. This pure function
    neither opens the 138 industry JSONL source files nor attests their present
    contents. It binds the original generation code hashes to the subsequent
    tested guard-hardening generation, without conflating either with Data OS
    native adoption or historical point-in-time evidence.
    """
    if (not isinstance(industry_codes, (list, tuple))
            or len(industry_codes) > MAX_COMPARISON_INDUSTRIES
            or any(not isinstance(code, str) or not _CODE.fullmatch(code)
                   for code in industry_codes)
            or len(set(industry_codes)) != len(industry_codes)):
        raise BEAContextRefused("at most twelve distinct exact BEA industry codes")
    build = _pinned_research_receipt_document(
        build_receipt_bytes, BUILD_RECEIPT_SHA256,
    )
    lineage = _pinned_research_receipt_document(lineage_bytes, METADATA_LINEAGE_SHA256)
    hardening = _pinned_research_receipt_document(
        hardening_bytes, HARDENING_RECEIPT_SHA256,
    )
    if (build.get("schema") != "mastermind.bea_research_view_build_receipt/v1"
            or build.get("industry_files") != EXPECTED_INDUSTRY_VIEW_COUNT
            or build.get("rows_per_industry") != SOURCE_ROWS_PER_INDUSTRY
            or build.get("total_rows") !=
            EXPECTED_INDUSTRY_VIEW_COUNT * SOURCE_ROWS_PER_INDUSTRY
            or build.get("source_lineage_sha256") != METADATA_LINEAGE_SHA256
            or build.get("original_inputs_unchanged") != {
                "full_panel": PANEL_SHA256,
                "full_receipt": QUALIFICATION_RECEIPT_SHA256,
                "use_panel": USE_PANEL_SHA256,
            }):
        raise BEAContextRefused("BEA research builder contract mismatch")
    for flag in ("dataos_native_admitted", "historical_pit_eligible",
                 "may_publish", "may_rank", "may_train", "may_trade"):
        if build.get(flag) is not False or hardening.get(flag) is not False:
            raise BEAContextRefused("research metadata cannot promote source authority")
    files = build.get("files")
    if not isinstance(files, dict) or len(files) != EXPECTED_INDUSTRY_VIEW_COUNT:
        raise BEAContextRefused("industry file coverage inconsistent with receipt")
    if any(
        not isinstance(filename, str)
        or re.fullmatch(r"industry_[A-Z0-9]{2,9}\.jsonl", filename) is None
        or not isinstance(claim, Mapping)
        or type(claim.get("bytes")) is not int or claim["bytes"] <= 0
        or type(claim.get("rows")) is not int
        or claim["rows"] != SOURCE_ROWS_PER_INDUSTRY
        or not isinstance(claim.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", claim["sha256"]) is None
        for filename, claim in files.items()
    ):
        raise BEAContextRefused("industry digest/row metadata invalid")
    if sum(v["bytes"] for v in files.values()) != DECLARED_TOTAL_INDUSTRY_VIEW_BYTES:
        raise BEAContextRefused("industry file byte-count total mismatch")
    for code in industry_codes:
        if f"industry_{code}.jsonl" not in files:
            raise BEAContextRefused("selected source industry absent from manifest")

    if (lineage.get("schema") != "mastermind.bea_industry_input_research_lineage/v1"
            or lineage.get("panel_sha256") != PANEL_SHA256
            or lineage.get("qualification_receipt_sha256") !=
            QUALIFICATION_RECEIPT_SHA256
            or lineage.get("use_panel_sha256") != USE_PANEL_SHA256
            or lineage.get("code_namespace") != EXACT_CODE_NAMESPACE
            or lineage.get("publication_date") != PUBLISHER_EDITION_DATE
            or lineage.get("publication_precision") != "DAY"
            or lineage.get("publication_timestamp") is not None
            or lineage.get("publication_timestamp_null_reason") !=
            "PUBLISHER_DAY_PRECISION_ONLY"
            or lineage.get("original_historical_available_at") is not None
            or lineage.get("historical_availability_null_reason") !=
            "HISTORICAL_AVAILABILITY_UNVERIFIED"
            or lineage.get("native_known_at") is not None
            or lineage.get("native_source_adoption") is not False
            or lineage.get("public_purpose_adoption") is not False
            or lineage.get("source_is_retrospectively_revised_2026_snapshot") is not True
            or lineage.get("legacy_mapping_unresolved") != {"5241X": "5241XX"}):
        raise BEAContextRefused("source lineage/edition/PIT contract mismatch")

    receipts = lineage.get("capture_receipt_sha256")
    by_year = lineage.get("sources_by_accounting_year")
    years = [str(year) for year in range(2017, 2025)]
    source_keys = {
        "Use", "ImMatAll", "ImMatCan", "ImMatChi", "ImMatEur",
        "ImMatJap", "ImMatMex", "ImMatRoa", "ImMatRow",
    }
    if (not isinstance(receipts, dict) or len(receipts) != 10
            or any(not isinstance(v, str)
                   or re.fullmatch(r"[0-9a-f]{64}", v) is None
                   for v in receipts.values())
            or not isinstance(by_year, dict) or set(by_year) != set(years)):
        raise BEAContextRefused("capture receipts or eight-year original lineage missing")
    receipt_hashes = set(receipts.values())
    observed_receipts: set[str] = set()
    capture_clocks = []
    for year in years:
        entries = by_year[year]
        if not isinstance(entries, dict) or set(entries) != source_keys:
            raise BEAContextRefused("missing world/region/Use origin source receipt")
        for source in entries.values():
            if (not isinstance(source, Mapping)
                    or not isinstance(source.get("source_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", source["source_sha256"]) is None
                    or source.get("capture_receipt_sha256") not in receipt_hashes):
                raise BEAContextRefused("source digest/receipt lineage mismatch")
            try:
                captured = utc(source.get("research_source_capture_completed_at"))
            except (TemporalError, TypeError, ValueError) as exc:
                raise BEAContextRefused("source-capture clock is not exact UTC") from exc
            if captured.date().isoformat() < PUBLISHER_EDITION_DATE:
                raise BEAContextRefused("retrospective source capture predates its edition")
            observed_receipts.add(source["capture_receipt_sha256"])
            capture_clocks.append(captured)
    if observed_receipts != receipt_hashes:
        raise BEAContextRefused("declared source capture receipts unreferenced")

    gen_code = build.get("code_sha256")
    current_code = hardening.get("current_code_sha256")
    if (not isinstance(gen_code, dict) or
            set(gen_code) != {
                "bea_research_views.py", "query_bea_full_region_research.py",
            }
            or hardening.get("schema") !=
            "mastermind.bea_research_view_source_hardening/v1"
            or hardening.get("generation_code_sha256") != gen_code
            or not isinstance(current_code, dict)
            or not set(gen_code).issubset(current_code)
            or any(not isinstance(v, str) or re.fullmatch(r"[0-9a-f]{64}", v) is None
                   for v in current_code.values())
            or hardening.get("immutable_lineage_sha256") != METADATA_LINEAGE_SHA256
            or hardening.get("immutable_view_build_receipt_sha256") !=
            BUILD_RECEIPT_SHA256
            or hardening.get("rows_compared") !=
            EXPECTED_INDUSTRY_VIEW_COUNT * SOURCE_ROWS_PER_INDUSTRY
            or hardening.get("all_138_file_row_bytes_unchanged_under_current_code")
            is not True
            or hardening.get("existing_view_generation_reused") is not True
            or hardening.get("fresh_source_checks_mandatory_for_new_build")
            is not True
            or hardening.get("focused_test_exit_code") != 0):
        raise BEAContextRefused("source builder/guard-hardening receipt mismatch")

    return {
        "schema": "market_ontology.bea_research_manifest_qualification/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "metadata_receipts_pin_verified": True,
        "generation_code_hardening_transition_reconciled": True,
        "research_build_receipt_sha256": BUILD_RECEIPT_SHA256,
        "research_lineage_sha256": METADATA_LINEAGE_SHA256,
        "research_hardening_receipt_sha256": HARDENING_RECEIPT_SHA256,
        "original_full_panel_declared_sha256": PANEL_SHA256,
        "edition_date": PUBLISHER_EDITION_DATE,
        "edition_precision": "DAY",
        "exact_code_namespace": EXACT_CODE_NAMESPACE,
        "industry_files_claimed": EXPECTED_INDUSTRY_VIEW_COUNT,
        "rows_per_industry_claimed": SOURCE_ROWS_PER_INDUSTRY,
        "total_rows_claimed": EXPECTED_INDUSTRY_VIEW_COUNT * SOURCE_ROWS_PER_INDUSTRY,
        "source_bytes_claimed": DECLARED_TOTAL_INDUSTRY_VIEW_BYTES,
        "original_source_capture_receipt_count": len(receipt_hashes),
        "original_source_lineage_entries": len(capture_clocks),
        "research_capture_window_utc": {
            "earliest": min(capture_clocks).isoformat(),
            "latest": max(capture_clocks).isoformat(),
        },
        "requested_using_industry_codes": list(industry_codes),
        "selected_original_builder_digest_claims": {
            code: files[f"industry_{code}.jsonl"]["sha256"]
            for code in industry_codes
        },
        "selected_original_view_byte_counts_claimed": {
            code: files[f"industry_{code}.jsonl"]["bytes"]
            for code in industry_codes
        },
        "selected_original_view_bytes_hashed_by_this_projection": False,
        "original_source_bytes_authenticated_by_this_projection": False,
        "actual_writer_admitted": False,
        "native_utc_ingest_and_revision_clock_established": False,
        "original_historical_known_at": None,
        "historical_pit_eligible": False,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
    }


def verify_supplied_bea_research_view_bytes(
    source_bytes: bytes, *, industry_code: str,
    build_receipt_bytes: bytes, lineage_bytes: bytes, hardening_bytes: bytes,
) -> dict[str, Any]:
    """Authenticate *caller-supplied* research-view bytes against pinned receipts.

    This adds no file opener or source admission. A trusted future Data OS
    producer must separately authenticate original BEA L0 responses, custody,
    rights and actual native ingest/revisions. Research JSONL bytes are not
    upstream BEA original response bytes, regardless of a matching view digest.
    """
    if not isinstance(industry_code, str) or not _CODE.fullmatch(industry_code):
        raise BEAContextRefused("one exact BEA industry code required")
    if (type(source_bytes) is not bytes
            or not 1 <= len(source_bytes) <= MAX_SUPPLIED_INDUSTRY_VIEW_BYTES):
        raise BEAContextRefused("bounded caller-supplied research-view bytes required")
    evidence = qualify_private_bea_research_manifest(
        build_receipt_bytes, lineage_bytes, hardening_bytes,
        industry_codes=(industry_code,),
    )
    claimed = evidence["selected_original_builder_digest_claims"][industry_code]
    claimed_size = evidence["selected_original_view_byte_counts_claimed"][industry_code]
    if len(source_bytes) != claimed_size:
        raise BEAContextRefused("supplied view length differs from pinned research receipt")
    calculated = hashlib.sha256(source_bytes).hexdigest()
    if calculated != claimed:
        raise BEAContextRefused("supplied view SHA256 differs from pinned research receipt")
    if not source_bytes.endswith(b"\n") or b"\r" in source_bytes:
        raise BEAContextRefused("research view must have exact LF-ended JSONL framing")
    rows = source_bytes.split(b"\n")
    if len(rows) != SOURCE_ROWS_PER_INDUSTRY + 1 or rows[-1] != b"":
        raise BEAContextRefused("research industry view does not contain 1112 rows")

    def no_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, value in pairs:
            if key in parsed:
                raise BEAContextRefused("duplicate key in a supplied BEA source row")
            parsed[key] = value
        return parsed

    def no_nonfinite(_value: str) -> None:
        raise BEAContextRefused("nonfinite BEA source value")

    first_year_order: list[str] = []
    visited: set[tuple[int, str]] = set()
    negative_world_rows = 0
    negative_region_rows = 0
    capture_clocks = []
    for position, raw in enumerate(rows[:-1]):
        if not 1 <= len(raw) <= 16_384:
            raise BEAContextRefused("invalid source-row byte bound")
        try:
            row = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=no_duplicate_fields,
                parse_constant=no_nonfinite,
            )
        except (UnicodeDecodeError, TypeError, ValueError) as exc:
            raise BEAContextRefused("malformed UTF8 research source row") from exc
        if not isinstance(row, dict):
            raise BEAContextRefused("source row is not a JSON object")
        year = 2017 + position // 139
        code = row.get("commodity_code_exact")
        if (row.get("accounting_year") != year
                or not isinstance(code, str) or not _CODE.fullmatch(code)):
            raise BEAContextRefused("source accounting-year or commodity order mismatches")
        offset = position % 139
        if year == 2017:
            first_year_order.append(code)
        elif code != first_year_order[offset]:
            raise BEAContextRefused("139 source commodities differ across accounting years")
        grain = (year, code)
        if grain in visited:
            raise BEAContextRefused("duplicate annual BEA source commodity grain")
        visited.add(grain)
        capture = _source_guard(
            row, industry=industry_code, commodity=code,
            expected_lineage_sha256=evidence["research_lineage_sha256"],
        )
        amounts = {field: _integer(row, field) for field in _AMOUNT_FIELDS}
        world = amounts["world_import_million_USD"]
        regions = {
            region: amounts[f"{region}_import_million_USD"]
            for region, _ in REGIONS
        }
        rounding = world - sum(regions.values())
        if (type(row.get("source_rounding_difference_million_USD")) is not int
                or row["source_rounding_difference_million_USD"] != rounding
                or abs(rounding) > 3):
            raise BEAContextRefused("signed source reconciliation mismatch")
        _shares(row, world, regions, rounding)
        negative_world_rows += world < 0
        negative_region_rows += any(v < 0 for v in regions.values())
        capture_clocks.append(utc(capture))
    if len(set(first_year_order)) != 139 or len(visited) != SOURCE_ROWS_PER_INDUSTRY:
        raise BEAContextRefused("139 exact source commodities required in each year")

    return {
        "schema": "market_ontology.bea_supplied_research_view_byte_check/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "industry_code_exact": industry_code,
        "exact_code_namespace": EXACT_CODE_NAMESPACE,
        "publisher_edition_date": PUBLISHER_EDITION_DATE,
        "publisher_edition_precision": "DAY",
        "measurement_class": "BEA_IMPUTED_INDUSTRY_IMPORT_ALLOCATION",
        "supplied_view_sha256": calculated,
        "pinned_builder_view_sha256": claimed,
        "supplied_view_bytes": len(source_bytes),
        "industry_view_rows_checked": SOURCE_ROWS_PER_INDUSTRY,
        "accounting_years_checked": list(range(2017, 2025)),
        "commodity_codes_per_year_checked": 139,
        "signed_negative_world_import_rows_checked": negative_world_rows,
        "signed_negative_region_adjustment_rows_checked": negative_region_rows,
        "research_capture_window_utc": {
            "earliest": min(capture_clocks).isoformat(),
            "latest": max(capture_clocks).isoformat(),
        },
        "pinned_receipt_metadata_authenticated": True,
        "supplied_research_view_bytes_authenticated": True,
        "original_BEA_L0_response_bytes_authenticated": False,
        "native_dataset_producer_admitted": False,
        "source_rights_accepted_for_public_product": False,
        "historical_pit_eligible": False,
        "original_historical_known_at": None,
        "named_company_supplier_buyer_evidence": False,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
    }


def attest_workspace_bea_selection_against_supplied_view(
    response: Mapping[str, Any], supplied_view_bytes: bytes, *,
    industry_code: str, commodity_code: str,
    build_receipt_bytes: bytes, lineage_bytes: bytes, hardening_bytes: bytes,
) -> dict[str, Any]:
    """Match selected *read-only DataWorkspace rows* to pinned research-view bytes.

    This attests the selected eight result rows only. The separate supplied
    research-view file has its *own* complete-byte hash check. The existing
    DataWorkspace stat version is NOT converted into a file-content hash and
    is not proof that unselected on-disk bytes equal the supplied view.
    No file is opened, no registration is performed, and nothing is published.
    """
    if not isinstance(commodity_code, str) or not _CODE.fullmatch(commodity_code):
        raise BEAContextRefused("one exact BEA commodity code required")
    provenance = verify_supplied_bea_research_view_bytes(
        supplied_view_bytes, industry_code=industry_code,
        build_receipt_bytes=build_receipt_bytes,
        lineage_bytes=lineage_bytes, hardening_bytes=hardening_bytes,
    )
    history = adapt_workspace_bea_history(
        response, industry_code=industry_code, commodity_code=commodity_code,
        purpose="private_research", as_of=None,
    )
    result = response["result"]
    positions = result["row_positions"]
    returned = result["rows"]
    lines = supplied_view_bytes.split(b"\n")
    if len(positions) != len(returned) or len(positions) != 8:
        raise BEAContextRefused("exact eight workspace source rows required")

    for year, (position, workspace_row) in enumerate(
        zip(positions, returned, strict=True), start=2017,
    ):
        if type(position) is not int or not 0 <= position < SOURCE_ROWS_PER_INDUSTRY:
            raise BEAContextRefused("workspace source position outside pinned view")
        # The view's entire original JSONL was strictly parsed and verified
        # above. Repeating only eight decoded rows cannot grant L0 authority.
        raw_row = json.loads(lines[position].decode("utf-8"))
        if raw_row != workspace_row:
            raise BEAContextRefused("workspace row differs from authenticated research view")
        if (raw_row.get("accounting_year") != year
                or raw_row.get("industry_code_exact") != industry_code
                or raw_row.get("commodity_code_exact") != commodity_code
                or history["observations"][year - 2017]["accounting_year"] != year):
            raise BEAContextRefused("workspace selection does not match exact source grain")

    return {
        "schema": "market_ontology.bea_workspace_selection_receipt/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "industry_code_exact": industry_code,
        "commodity_code_exact": commodity_code,
        "exact_code_namespace": EXACT_CODE_NAMESPACE,
        "publisher_edition_date": PUBLISHER_EDITION_DATE,
        "publisher_edition_precision": "DAY",
        "source_research_view_sha256": provenance["supplied_view_sha256"],
        "pinned_builder_view_sha256": provenance["pinned_builder_view_sha256"],
        "workspace_stat_file_version": history["reader_provenance"]["stat_file_version"],
        "workspace_query_receipt_sha256": history["reader_provenance"]["query_receipt_sha256"],
        "selected_workspace_row_positions": list(positions),
        "selected_workspace_rows_matched": 8,
        "research_view_bytes_verified_by_supplied_input": True,
        "selected_workspace_rows_match_pinned_view_bytes": True,
        "unselected_workspace_disk_bytes_authenticated": False,
        "upstream_original_BEA_L0_response_bytes_authenticated": False,
        "native_dataset_admitted": False,
        "original_historical_known_at": None,
        "historical_pit_eligible": False,
        "may_publish": False,
        "may_rank": False,
        "may_train": False,
        "may_trade": False,
    }
