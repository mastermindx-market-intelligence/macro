"""BEA Global Value Chain Analyzer: guarded industry-context research projection.

No fetching, filesystem access, native dataset registration, GMI graph mutation,
company/ticker inference, signal production, or public emission. The only source
is a caller-supplied, already-qualified *May 21, 2026 edition* Data Lab row.
The historical accounting year is NOT a historical source-availability clock.

This deliberately does not implement another temporal, rights, identity, or
source registry. Native source admission belongs to the existing Data OS owner.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, ROUND_HALF_EVEN
import json
import re
from typing import Any

from lib.dataos.temporal import TemporalError, utc

PANEL_SHA256 = "f3ecdda2a8161b2f4ffa893d9d5ff43896280339ca85d76240d4979404e95448"
LINEAGE_SHA256 = "e8856b6f546d55b8e0c41561cb0e60f28ddcd06a78fd04f70d05355890c745a7"
PUBLISHER_EDITION_DATE = "2026-05-21"
EXACT_CODE_NAMESPACE = "BEA_APP157_MAY2026_EXACT"
SOURCE_KIND = "industry_commodity_input"
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


def _source_guard(row: Mapping[str, Any], *, industry: str, commodity: str) -> str:
    if not isinstance(row, Mapping):
        raise BEAContextRefused("unrecognized research row")
    if not all(isinstance(x, str) and _CODE.fullmatch(x) for x in (industry, commodity)):
        raise BEAContextRefused("exact BEA source code required, not company alias")
    if (row.get("industry_code_exact") != industry
            or row.get("commodity_code_exact") != commodity
            or row.get("code_namespace") != EXACT_CODE_NAMESPACE
            or row.get("source_kind") != SOURCE_KIND):
        raise BEAContextRefused("BEA code/namespace or industry-input source mismatch")
    if (row.get("source_lineage_sha256") != LINEAGE_SHA256
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
    """Require exactly eight distinct same-edition accounting years in order."""
    observations = [
        adapt_industry_commodity_input(row, industry_code=industry_code,
                                       commodity_code=commodity_code,
                                       as_of=as_of, purpose=purpose)
        for row in rows
    ]
    if [x["accounting_year"] for x in observations] != list(range(2017, 2025)):
        raise BEAContextRefused("eight distinct ordered source years required")
    return {
        "schema": "market_ontology.bea_industry_input_history_research/v1",
        "authority": "PRIVATE_RESEARCH_ONLY",
        "using_industry_code_exact": industry_code,
        "commodity_code_exact": commodity_code,
        "observations": observations,
        "no_named_company_relationships": True,
        "source_adopted": False,
        "public_or_predictive_use": False,
    }
