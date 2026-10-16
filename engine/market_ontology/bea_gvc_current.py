"""Read-only BEA GVC descriptive projection; never a source or publication owner.

This leaf consumes Data OS registry contracts and owner-supplied current-vintage
bytes. It authenticates neither the supplied bytes' custody nor the user's
access. The host must independently qualify its native source-generation,
rights, and session before ever serving a projection. No route, store, source
registry, graph/company edge, ranking or trading output is installed here.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from lib.dataos.registry import DatasetStatus, Layer, Registry

SCHEMA = "market_ontology.bea_gvc_current_descriptive/v1"
L0_ID = "bea.gvc.may2026.original_responses"
L1_ID = "bea.gvc.may2026.industry_import_inputs"
EDITION_DATE = "2026-05-21"
RIGHTS_SCOPE = "bea_public_domain_current_descriptive_scope_20261014"
MAX_BYTES = 16 * 1024 * 1024
MAX_JSON_SAFE_INTEGER = (1 << 53) - 1
YEARS = tuple(range(2017, 2025))
REGIONS = (
    "canada", "china", "europe", "japan", "mexico",
    "rest_of_asia_and_pacific", "rest_of_world",
)
_AMOUNT_FIELDS = ("total_use_million_USD", "world_import_million_USD") + tuple(
    region + "_import_million_USD" for region in REGIONS
)
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_TABLES = frozenset({
    "Use", "ImMatAll", "ImMatCan", "ImMatChi", "ImMatEur", "ImMatJap",
    "ImMatMex", "ImMatRoa", "ImMatRow",
})
SOURCE_NAMESPACE = "BEA_APP157_MAY2026_EXACT"
AUTHORITY = "internal_descriptive_candidate_only"


class BEADescriptiveRefused(ValueError):
    """Malformed trusted input; never leak data from a partial source."""


def _payload(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BEADescriptiveRefused("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _nonfinite(value: str) -> None:
    raise BEADescriptiveRefused("NONFINITE_JSON_VALUE")


def _clock(value: Any) -> str:
    if type(value) is not str:
        raise BEADescriptiveRefused("MISSING_NATIVE_CLOCK")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise BEADescriptiveRefused("INVALID_NATIVE_CLOCK") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise BEADescriptiveRefused("NAIVE_NATIVE_CLOCK")
    stamp = stamp.astimezone(timezone.utc)
    if stamp.date().isoformat() < EDITION_DATE or stamp > datetime.now(timezone.utc):
        raise BEADescriptiveRefused("NATIVE_CLOCK_OUTSIDE_EDITION")
    return stamp.isoformat()


def _hex(value: Any, label: str) -> str:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise BEADescriptiveRefused(label)
    return value


def _unavailable(code: str, exact_industry: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNAVAILABLE",
        "reason": code,
        "authority_ceiling": AUTHORITY,
        "may_publish": False,
        "may_rank": False,
        "may_trade": False,
        "industry_code_exact": exact_industry,
        "publisher_edition_date": EDITION_DATE,
        "publication_precision": "DAY",
        "source_generation_id": None,
        "native_ingested_at": None,
        "rows_examined": 0,
        "annual_descriptive": [],
    }


def _source_gate(registry: Registry) -> str | None:
    if not isinstance(registry, Registry):
        raise TypeError("existing Data OS Registry is required")
    if registry.duplicate_ids():
        return "DUPLICATE_SOURCE_REGISTRY_ID"
    l0, l1 = registry.get(L0_ID), registry.get(L1_ID)
    if l0 is None or l1 is None:
        return "SOURCE_UNREGISTERED"
    if (l0.layer is not Layer.L0_SOURCE or l1.layer is not Layer.L1_NORMALIZED
            or l1.inputs != (L0_ID,)
            or l0.owner != l1.owner or l0.owner != "macro-dashboard"):
        return "SOURCE_CONTRACT_NOT_BOUND"
    # An approved purpose or proposed registry entry is NOT a produced source.
    if l0.status is not DatasetStatus.PRODUCED or l1.status is not DatasetStatus.PRODUCED:
        return "SOURCE_NOT_PRODUCED"
    if l0.licensing != RIGHTS_SCOPE or l1.licensing != RIGHTS_SCOPE:
        return "SOURCE_SCOPE_UNQUALIFIED"
    for contract in (l0, l1):
        rights = contract.rights
        for key in ("internal_computation", "redistribution"):
            if (rights.get(key) != "granted"
                    or not isinstance(rights.get("evidence"), dict)
                    or not isinstance(rights["evidence"].get(key), str)
                    or not rights["evidence"][key].startswith("DEC:")):
                return "SOURCE_RIGHTS_NOT_GRANTED"
    return None


def current_industry_candidate(
    registry: Registry, *, industry_code_exact: str,
    owner_bound_jsonl: bytes | None = None,
    owner_expected_sha256: str | None = None,
    owner_generation_id: str | None = None,
    owner_native_ingested_at: str | None = None,
    owner_native_revision_seq: int | None = None,
) -> dict[str, Any]:
    """Project an industry candidate for internal integration checks, never serving.

    A digest supplied by a caller is not authentication. Even with all locally
    checked data, the result is marked CANDIDATE_NOT_PUBLISHED. The existing
    Data OS and app owners must separately authenticate the source, native
    clocks/revisions, and current session before any human/API publication.
    """
    if type(industry_code_exact) is not str or not _CODE.fullmatch(industry_code_exact):
        raise BEADescriptiveRefused("UNSAFE_EXACT_INDUSTRY_CODE")
    blocked = _source_gate(registry)
    if blocked:
        # Crucial: an unproduced/unlicensed source is blocked BEFORE reading
        # one-shot payload bytes or consulting any supplied owner claim.
        return _unavailable(blocked, industry_code_exact)
    if (type(owner_bound_jsonl) is not bytes or not owner_bound_jsonl
            or len(owner_bound_jsonl) > MAX_BYTES):
        return _unavailable("OWNER_VIEW_BYTES_MISSING_OR_OVERSIZED", industry_code_exact)
    digest = _hex(owner_expected_sha256, "OWNER_VIEW_DIGEST_NOT_BOUND")
    generation = _hex(owner_generation_id, "OWNER_GENERATION_NOT_BOUND")
    if hashlib.sha256(owner_bound_jsonl).hexdigest() != digest:
        return _unavailable("SOURCE_VIEW_DIGEST_MISMATCH", industry_code_exact)
    stamp = _clock(owner_native_ingested_at)
    if type(owner_native_revision_seq) is not int or owner_native_revision_seq < 0:
        raise BEADescriptiveRefused("NATIVE_REVISION_NOT_BOUND")
    if not owner_bound_jsonl.endswith(b"\n") or b"\r" in owner_bound_jsonl:
        return _unavailable("VIEW_FRAMING_INVALID", industry_code_exact)
    annual = {y: {field: 0 for field in _AMOUNT_FIELDS +
                         ("region_rounding_difference_million_USD",)} for y in YEARS}
    quality = {y: {
        "nonpositive_world_commodities": 0,
        "negative_region_adjustment_commodities": 0,
        "rounding_residual_commodities": 0,
    } for y in YEARS}
    visited: set[tuple[int, str]] = set()
    # The full 9-table source/receipt population is constant within each
    # accounting year. A digest is integrity, never authentication by itself.
    annual_lineage: dict[int, tuple[Any, ...]] = {}
    source_lineage_sha256: str | None = None
    producer_code_sha256: str | None = None
    seen_commodity_order: tuple[str, ...] | None = None
    by_year: dict[int, list[str]] = {year: [] for year in YEARS}
    for raw in owner_bound_jsonl.splitlines():
        if len(raw) > 32_768 or not raw:
            return _unavailable("VIEW_ROW_FRAMING_INVALID", industry_code_exact)
        try:
            row = json.loads(raw, object_pairs_hook=_json_pairs,
                             parse_constant=_nonfinite)
        except (UnicodeError, TypeError, ValueError, RecursionError):
            return _unavailable("VIEW_ROW_MALFORMED", industry_code_exact)
        if type(row) is not dict:
            return _unavailable("VIEW_ROW_MALFORMED", industry_code_exact)
        year = row.get("accounting_year")
        commodity = row.get("commodity_code_exact")
        if (type(year) is not int or year not in YEARS or
                type(commodity) is not str or not _CODE.fullmatch(commodity) or
                row.get("industry_code_exact") != industry_code_exact or
                (year, commodity) in visited):
            return _unavailable("SOURCE_GRAIN_OR_IDENTITY_INVALID", industry_code_exact)
        visited.add((year, commodity))
        by_year[year].append(commodity)
        try:
            row_native_clock = _clock(row.get("native_ingested_at"))
        except BEADescriptiveRefused:
            return _unavailable("SOURCE_PROVENANCE_OR_AUTHORITY_INVALID", industry_code_exact)
        if (row.get("dataset_id") != L1_ID or
                row.get("publisher_edition_date") != EDITION_DATE or
                row.get("publication_precision") != "DAY" or
                row.get("published_at", "MISSING") is not None or
                row.get("original_historical_available_at", "MISSING") is not None or
                row.get("source_generation_id") != generation or
                row_native_clock != stamp or
                type(row.get("native_revision_seq")) is not int or
                row["native_revision_seq"] != owner_native_revision_seq or
                row.get("dataos_native_admitted") is not True or
                row.get("may_publish") is not True or
                row.get("may_rank") is not False or
                row.get("may_trade") is not False or
                row.get("named_company_relationship") is not False or
                row.get("canonical_security_id", "MISSING") is not None):
            return _unavailable("SOURCE_PROVENANCE_OR_AUTHORITY_INVALID", industry_code_exact)
        sources = row.get("source_response_sha256_by_table")
        captures = row.get("capture_receipt_sha256_by_table")
        lineage_sha = row.get("source_lineage_sha256")
        producer_sha = row.get("producer_code_sha256")
        if (row.get("source_kind") != "imputed_industry_commodity_accounting"
                or row.get("source_units") != "million USD"
                or row.get("code_namespace") != SOURCE_NAMESPACE
                or type(sources) is not dict or set(sources) != SOURCE_TABLES
                or type(captures) is not dict or set(captures) != SOURCE_TABLES
                or any(type(value) is not str or not _SHA.fullmatch(value)
                       for value in (*sources.values(), *captures.values()))
                or type(lineage_sha) is not str or not _SHA.fullmatch(lineage_sha)
                or type(producer_sha) is not str or not _SHA.fullmatch(producer_sha)):
            return _unavailable("ORIGINAL_RESPONSE_LINEAGE_UNBOUND", industry_code_exact)
        if source_lineage_sha256 is None:
            source_lineage_sha256, producer_code_sha256 = lineage_sha, producer_sha
        elif (lineage_sha != source_lineage_sha256 or
              producer_sha != producer_code_sha256):
            return _unavailable("SOURCE_PRODUCER_OR_LINEAGE_DRIFT", industry_code_exact)
        exact_year_lineage = (
            tuple(sorted(sources.items())), tuple(sorted(captures.items())))
        if year not in annual_lineage:
            annual_lineage[year] = exact_year_lineage
        elif annual_lineage[year] != exact_year_lineage:
            return _unavailable("SOURCE_ANNUAL_RESPONSE_DRIFT", industry_code_exact)
        amounts: dict[str, int] = {}
        for field in _AMOUNT_FIELDS:
            value = row.get(field)
            if type(value) is not int:
                return _unavailable("SOURCE_AMOUNTS_INVALID", industry_code_exact)
            if abs(value) > MAX_JSON_SAFE_INTEGER:
                return _unavailable("SOURCE_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER",
                                    industry_code_exact)
            amounts[field] = value
        rounding = amounts["world_import_million_USD"] - sum(
            amounts[region + "_import_million_USD"] for region in REGIONS
        )
        if (type(row.get("region_rounding_difference_million_USD")) is not int
                or rounding != row["region_rounding_difference_million_USD"]
                or abs(rounding) > 3):
            return _unavailable("SOURCE_SIGNED_ACCOUNTING_INVALID", industry_code_exact)
        expected_flags: list[str] = []
        if amounts["world_import_million_USD"] <= 0:
            expected_flags.append("WORLD_IMPORT_NONPOSITIVE")
        if any(amounts[region + "_import_million_USD"] < 0 for region in REGIONS):
            expected_flags.append("SOURCE_NEGATIVE_REGION_ADJUSTMENT")
        if rounding != 0:
            expected_flags.append("PUBLISHER_ROUNDING_RESIDUAL")
        if row.get("quality_flags") != expected_flags:
            return _unavailable("SOURCE_QUALITY_FLAG_DRIFT", industry_code_exact)
        for field, value in (*amounts.items(),
                             ("region_rounding_difference_million_USD", rounding)):
            updated = annual[year][field] + value
            if abs(updated) > MAX_JSON_SAFE_INTEGER:
                return _unavailable("ANNUAL_AMOUNT_EXCEEDS_JSON_SAFE_INTEGER",
                                    industry_code_exact)
            annual[year][field] = updated
        if amounts["world_import_million_USD"] <= 0:
            quality[year]["nonpositive_world_commodities"] += 1
        if any(amounts[region + "_import_million_USD"] < 0 for region in REGIONS):
            quality[year]["negative_region_adjustment_commodities"] += 1
        if rounding != 0:
            quality[year]["rounding_residual_commodities"] += 1
    if len(visited) != len(YEARS) * 139:
        return _unavailable("INCOMPLETE_COMMODITY_YEARS", industry_code_exact)
    for year in YEARS:
        codes = tuple(by_year[year])
        if len(codes) != 139 or len(set(codes)) != 139:
            return _unavailable("INCOMPLETE_COMMODITY_YEARS", industry_code_exact)
        if seen_commodity_order is None:
            seen_commodity_order = codes
        elif codes != seen_commodity_order:
            return _unavailable("COMMODITY_IDENTITY_DRIFT", industry_code_exact)
    annual_descriptive: list[dict[str, Any]] = []
    previous_year: int | None = None
    for year in YEARS:
        change = None if previous_year is None else {
            field: annual[year][field] - annual[previous_year][field]
            for field in annual[year]
        }
        if change is not None and any(abs(v) > MAX_JSON_SAFE_INTEGER
                                      for v in change.values()):
            return _unavailable("ANNUAL_CHANGE_EXCEEDS_JSON_SAFE_INTEGER",
                                industry_code_exact)
        annual_descriptive.append({
            "accounting_year": year, **annual[year],
            "quality": quality[year],
            "year_over_year_change_million_USD": change,
        })
        previous_year = year
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_NOT_PUBLISHED",
        "reason": "OWNER_AUTHENTICATION_AND_RUNTIME_RELEASE_UNPROVEN",
        "authority_ceiling": AUTHORITY,
        "may_publish": False, "may_rank": False, "may_trade": False,
        "industry_code_exact": industry_code_exact,
        "publisher_edition_date": EDITION_DATE,
        "publication_precision": "DAY",
        "source_generation_id": generation,
        "source_lineage_sha256": source_lineage_sha256,
        "producer_code_sha256": producer_code_sha256,
        "native_ingested_at": stamp,
        "rows_examined": len(visited),
        "annual_descriptive": annual_descriptive,
        "annual_comparison_basis":
            "RETROSPECTIVE_2026_VINTAGE_NOT_ORIGINAL_HISTORICAL_KNOWLEDGE",
        "attribution": "Source: U.S. Bureau of Economic Analysis",
        "measurement_class": "IMPUTED_INDUSTRY_IMPORT_ALLOCATION_NOT_COMPANY_SUPPLY_CHAINS",
        "historical_pit_eligible": False,
        "historical_availability_null_reason": "HISTORICAL_AVAILABILITY_UNVERIFIED",
        "canonical_security_id": None,
        "legacy_mapping_state": ("UNRESOLVED_5241X_VS_5241XX"
                                 if industry_code_exact == "5241X" else "NOT_APPLIED"),
        "owner_expected_view_sha256_claim": digest,
        "owner_digest_is_not_authenticated_here": True,
    }


def candidate_packet_bytes(packet: Mapping[str, Any]) -> bytes:
    """One deterministic serialization for prospective human and machine clients.

    This never changes packet authority. A caller must reject may_publish=False,
    including a well-formed CANDIDATE_NOT_PUBLISHED result.
    """
    if type(packet) is not dict or packet.get("schema") != SCHEMA:
        raise BEADescriptiveRefused("WRONG_PROJECTION_SCHEMA")
    if packet.get("may_publish") is not False:
        raise BEADescriptiveRefused("UNSUPPORTED_PUBLICATION_ESCALATION")
    return _payload(packet)
