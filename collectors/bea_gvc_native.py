"""Byte-bound BEA May-2026 native-producer candidates; no live admission.

Reuse owner-supplied original responses and capture receipts, never the private
research JSONL views. No fetching, credentials, registry mutation, data writes,
public serving, trading, or source-rights decision occurs here. The only local
read is this module's own bytes, to identify the actual producer implementation.
The existing Data OS storage/release owner must install and admit a candidate;
these functions deliberately cannot change a dataset to PRODUCED.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from lib.dataos.temporal import TemporalError, utc

LINEAGE_SHA256 = "e8856b6f546d55b8e0c41561cb0e60f28ddcd06a78fd04f70d05355890c745a7"
EDITION_DATE = "2026-05-21"
EDITION_LABEL = "May 21, 2026"
L0_DATASET = "bea.gvc.may2026.original_responses"
L1_DATASET = "bea.gvc.may2026.industry_import_inputs"
CODE_NAMESPACE = "BEA_APP157_MAY2026_EXACT"
YEARS = tuple(range(2017, 2025))
REGIONS = (
    ("ImMatCan", "canada", "Canada"),
    ("ImMatChi", "china", "China"),
    ("ImMatEur", "europe", "Europe"),
    ("ImMatJap", "japan", "Japan"),
    ("ImMatMex", "mexico", "Mexico"),
    ("ImMatRoa", "rest_of_asia_and_pacific", "Rest of Asia and Pacific"),
    ("ImMatRow", "rest_of_world", "Rest of World"),
)
TABLES = ("Use", "ImMatAll", *(key for key, _, _ in REGIONS))
TITLES = {
    "Use": "Use Table, After Redefinitions",
    "ImMatAll": "Import Matrix, After Redefinitions",
    **{key: f"Import Matrix, {name}, After Redefinitions" for key, _, name in REGIONS},
}
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_METADATA_BYTES = 256 * 1024
MAX_INDUSTRY_VIEW_BYTES = 16 * 1024 * 1024
_SHA = re.compile(r"[0-9a-f]{64}\Z")
# Preserve opaque publisher tokens; case is part of identity, not an alias.
# Meaning comes from pinned original bytes, never this lexical safety envelope.
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}\Z")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)\Z")


class BEAGVCRefused(ValueError):
    """A candidate cannot be built without guessing or weakening source truth."""


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _producer_sha256() -> str:
    """Observe this producer's source identity; never trust a candidate's claim."""
    try:
        return _sha(Path(__file__).read_bytes())
    except OSError as exc:
        raise BEAGVCRefused("producer source identity unavailable") from exc


def _encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise BEAGVCRefused("duplicate JSON object key")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise BEAGVCRefused(f"non-JSON numeric constant: {value}")


def _json(blob: bytes | str, limit: int) -> Any:
    if type(blob) not in (bytes, str) or len(blob) > limit:
        raise BEAGVCRefused("wrong JSON type or byte/character bound")
    try:
        return json.loads(blob, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise BEAGVCRefused("invalid or ambiguous source JSON") from exc


def _digest(value: Any) -> str:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise BEAGVCRefused("exact lower-case SHA-256 required")
    return value


def _instant(value: Any) -> str:
    if type(value) is not str:
        raise BEAGVCRefused("capture clock must be an offset-aware string")
    try:
        return utc(value).isoformat()
    except (TemporalError, ValueError, TypeError) as exc:
        raise BEAGVCRefused("invalid capture UTC clock") from exc


@dataclass(frozen=True)
class _Table:
    industry_codes: tuple[str, ...]
    industry_names: tuple[str, ...]
    commodity_codes: tuple[str, ...]
    commodity_names: tuple[str, ...]
    amounts: tuple[tuple[int, ...], ...]


def _parse_response(blob: bytes, key: str, year: int) -> _Table:
    if type(key) is not str or key not in TABLES or type(year) is not int or year not in YEARS:
        raise BEAGVCRefused("unsupported exact source table or accounting year")
    if type(blob) is not bytes or not 0 < len(blob) <= MAX_RESPONSE_BYTES:
        raise BEAGVCRefused("original response bytes required within 4 MiB")
    page = _json(blob, MAX_RESPONSE_BYTES)
    if type(page) is str:  # retained official GetStep response is double-encoded
        page = _json(page, MAX_RESPONSE_BYTES)
    if (type(page) is not dict or type(page.get("AppId")) is not int
            or page["AppId"] != 157 or type(page.get("Number")) is not int
            or page["Number"] != 2 or type(page.get("Prompts")) is not list):
        raise BEAGVCRefused("not the exact BEA app 157 result step")
    prompts = [p for p in page["Prompts"] if type(p) is dict
               and p.get("Name") == "TheTable" and p.get("UIControl") == "Table"]
    if len(prompts) != 1 or type(prompts[0].get("PromtData")) is not str:
        raise BEAGVCRefused("missing or ambiguous source table prompt")
    wrapped = _json(prompts[0]["PromtData"], MAX_RESPONSE_BYTES)
    if type(wrapped) is not dict or type(wrapped.get("Table")) is not str:
        raise BEAGVCRefused("invalid original table wrapper")
    table = _json(wrapped["Table"], MAX_RESPONSE_BYTES)
    rows, cols = (147, 163) if key == "Use" else (141, 161)
    if (type(table) is not dict or table.get("Title") != TITLES[key]
            or table.get("Description") != EDITION_LABEL
            or table.get("Sub_Title") != f"{year}, [Millions of Dollars]"
            or table.get("Number_Of_Rows") != str(rows)
            or table.get("Number_Of_Columns") != str(cols)
            or table.get("Number_Of_Header_Rows") != "2"):
        raise BEAGVCRefused("source table identity, edition, units or shape changed")
    data = table.get("Data_Rows")
    if (type(data) is not list or len(data) != rows
            or any(type(row) is not list or len(row) != cols for row in data)):
        raise BEAGVCRefused("source table truncated or ragged")
    if any(type(c) is not dict or type(c.get("CV")) is not str
           for row in data for c in row):
        raise BEAGVCRefused("source cells must contain original CV strings")
    grid = [[c["CV"] for c in row] for row in data]
    industries = tuple(grid[0][2:140])
    commodities = tuple(row[0] for row in grid[2:141])
    if (len(set(industries)) != 138 or len(set(commodities)) != 139
            or any(not _CODE.fullmatch(code) for code in industries + commodities)):
        raise BEAGVCRefused("nonunique or nonexact source axes")
    industry_names = tuple(grid[1][2:140])
    commodity_names = tuple(row[1] for row in grid[2:141])
    if any(not name.strip() for name in industry_names + commodity_names):
        raise BEAGVCRefused("missing published source names")
    amounts = []
    for row in grid[2:141]:
        values = row[2:140]
        if any(not _NUMBER.fullmatch(value) for value in values):
            raise BEAGVCRefused("suppressed, fractional or malformed signed source amount")
        amounts.append(tuple(int(value.replace(",", "")) for value in values))
    return _Table(industries, industry_names, commodities, commodity_names, tuple(amounts))


@dataclass(frozen=True)
class _Source:
    year: int
    table_id: str
    sha256: str
    capture_receipt_sha256: str
    captured_at: str
    original_bytes: bytes
    table: _Table


@dataclass(frozen=True)
class BEAGVCCandidate:
    """An in-process result, not an authorization token or installed source store."""
    manifest_bytes: bytes
    sources: tuple[_Source, ...]
    lineage_bytes: bytes
    capture_receipts: tuple[tuple[str, bytes], ...]

    @property
    def generation_id(self) -> str:
        return _sha(self.manifest_bytes)

    @property
    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_bytes)


def _years(values: Sequence[int]) -> tuple[int, ...]:
    if (type(values) not in (tuple, list) or not values
            or any(type(v) is not int or v not in YEARS for v in values)
            or len(set(values)) != len(values)):
        raise BEAGVCRefused("select unique explicit accounting years in 2017..2024")
    return tuple(sorted(values))


def _receipt_source(receipt: dict[str, Any], year: int, key: str) -> tuple[str, str, int | None]:
    """Resolve the four already-retained capture shapes; never reinterpret rights."""
    schema = receipt.get("schema")
    if schema == "mastermind.bea_2024_source_qualification_receipt/v1":
        records = receipt.get("source_artifacts")
        item = records.get(key) if type(records) is dict else None
        if type(item) is not dict or type(item.get("year")) is not int or item["year"] != year:
            raise BEAGVCRefused("capture receipt source identity missing")
        return _digest(item.get("file_sha256")), _instant(item.get("capture_utc")), None
    shapes = {
        "mastermind.bea_2017_2022_world_china_imports_capture/v1":
            ("raw_files", "year", "source_sha256", "raw_bytes", None),
        "mastermind.bea_six_regions_single_year_official_capture/v1":
            ("files", "year", "sha256", "bytes", None),
        "mastermind.bea_public_2017_2022_may2026_use_private/v1":
            ("files", "year", "sha256", "raw_bytes", None),
        "mastermind.bea_public_itable_2023_same_2026_release_capture/v1":
            ("tables", "source_effective_year", "sha256", "original_bytes", "acquired_at_utc"),
    }
    if type(schema) is not str or schema not in shapes:
        raise BEAGVCRefused("unsupported capture receipt schema")
    field, year_field, sha_field, size_field, clock_field = shapes[schema]
    records = receipt.get(field)
    if type(records) is not list or any(type(item) is not dict for item in records):
        raise BEAGVCRefused("invalid capture receipt records")
    use_only = schema == "mastermind.bea_public_2017_2022_may2026_use_private/v1"
    selected = [item for item in records
                if type(item.get(year_field)) is int and item[year_field] == year
                and ("Use" if use_only else item.get("key")) == key]
    if len(selected) != 1:
        raise BEAGVCRefused("capture receipt source absent or duplicated")
    item = selected[0]
    size = item.get(size_field)
    if type(size) is not int or not 0 < size <= MAX_RESPONSE_BYTES:
        raise BEAGVCRefused("capture receipt byte length invalid")
    clock = item.get(clock_field) if clock_field else receipt.get("captured_at_utc")
    return _digest(item.get(sha_field)), _instant(clock), size


def _prepare_sources(
    lineage_bytes: bytes,
    source_bytes: Mapping[tuple[int, str], bytes],
    capture_receipts: Mapping[str, bytes],
    expected_lineage_sha256: str,
    years: tuple[int, ...],
    observed_at: str,
) -> tuple[_Source, ...]:
    if type(lineage_bytes) is not bytes or _sha(lineage_bytes) != _digest(expected_lineage_sha256):
        raise BEAGVCRefused("retained source lineage digest mismatch")
    lineage = _json(lineage_bytes, MAX_METADATA_BYTES)
    if (type(lineage) is not dict
            or lineage.get("schema") != "mastermind.bea_industry_input_research_lineage/v1"
            or lineage.get("publication_date") != EDITION_DATE
            or lineage.get("publication_precision") != "DAY"
            or lineage.get("publication_timestamp", "MISSING") is not None
            or lineage.get("publication_timestamp_null_reason") != "PUBLISHER_DAY_PRECISION_ONLY"
            or lineage.get("original_historical_available_at", "MISSING") is not None
            or lineage.get("native_known_at", "MISSING") is not None
            or lineage.get("native_source_adoption") is not False
            or lineage.get("code_namespace") != CODE_NAMESPACE):
        raise BEAGVCRefused("lineage edition, historical clock or admission semantics changed")
    by_year = lineage.get("sources_by_accounting_year")
    receipt_ids = lineage.get("capture_receipt_sha256")
    if (type(by_year) is not dict or set(by_year) != {str(y) for y in YEARS}
            or type(receipt_ids) is not dict or not receipt_ids):
        raise BEAGVCRefused("complete eight-year lineage and capture references required")
    allowed_receipts = {_digest(v) for v in receipt_ids.values()}
    for year in YEARS:
        tables = by_year[str(year)]
        if type(tables) is not dict or set(tables) != set(TABLES):
            raise BEAGVCRefused("lineage requires Use plus eight import matrices per year")
        for entry in tables.values():
            if (type(entry) is not dict
                    or set(entry) != {"source_sha256", "capture_receipt_sha256",
                                      "research_source_capture_completed_at"}):
                raise BEAGVCRefused("invalid source lineage entry")
            _digest(entry["source_sha256"])
            if _digest(entry["capture_receipt_sha256"]) not in allowed_receipts:
                raise BEAGVCRefused("unbound capture receipt reference")
            clock = _instant(entry["research_source_capture_completed_at"])
            if utc(clock) > utc(observed_at) or utc(clock).date().isoformat() < EDITION_DATE:
                raise BEAGVCRefused("source capture outside known edition/observation interval")
    expected_keys = {(year, key) for year in years for key in TABLES}
    if (not isinstance(source_bytes, Mapping) or set(source_bytes) != expected_keys
            or any(type(k) is not tuple or len(k) != 2 or type(k[0]) is not int
                   or type(k[1]) is not str for k in source_bytes)):
        raise BEAGVCRefused("supplied original response population differs from explicit scope")
    needed = {by_year[str(y)][k]["capture_receipt_sha256"] for y, k in expected_keys}
    if not isinstance(capture_receipts, Mapping) or set(capture_receipts) != needed:
        raise BEAGVCRefused("supply exactly the capture receipts referenced by this scope")
    decoded_receipts = {}
    for sha, blob in capture_receipts.items():
        if type(blob) is not bytes or _sha(blob) != _digest(sha):
            raise BEAGVCRefused("original capture receipt bytes changed")
        receipt = _json(blob, MAX_METADATA_BYTES)
        if type(receipt) is not dict:
            raise BEAGVCRefused("capture receipt must be an object")
        decoded_receipts[sha] = receipt
    bound = []
    reference_axes = None
    for year in years:
        annual = {}
        for key in TABLES:
            meta = by_year[str(year)][key]
            blob = source_bytes[year, key]
            if type(blob) is not bytes or _sha(blob) != meta["source_sha256"]:
                raise BEAGVCRefused("original response does not match retained lineage")
            rsha = meta["capture_receipt_sha256"]
            sha, captured, size = _receipt_source(decoded_receipts[rsha], year, key)
            if (sha != meta["source_sha256"]
                    or captured != _instant(meta["research_source_capture_completed_at"])
                    or (size is not None and len(blob) != size)):
                raise BEAGVCRefused("capture receipt does not bind these exact original bytes/clocks")
            table = _parse_response(blob, key, year)
            axes = (table.industry_codes, table.commodity_codes)
            if reference_axes is None:
                reference_axes = axes
            elif axes != reference_axes:
                raise BEAGVCRefused("industry/commodity axes differ across sources or years")
            source = _Source(year, key, sha, rsha, captured, blob, table)
            annual[key] = source
            bound.append(source)
        for i in range(139):
            for j in range(138):
                delta = annual["ImMatAll"].table.amounts[i][j] - sum(
                    annual[key].table.amounts[i][j] for key, _, _ in REGIONS)
                if abs(delta) > 3:
                    raise BEAGVCRefused("signed regional accounting exceeds publisher rounding bound")
    return tuple(bound)


def _source_records(sources: tuple[_Source, ...]) -> list[dict[str, Any]]:
    return [{"accounting_year":s.year, "source_table_id":s.table_id,
             "original_response_sha256":s.sha256, "original_response_bytes":len(s.original_bytes),
             "capture_receipt_sha256":s.capture_receipt_sha256,
             "research_source_capture_completed_at":s.captured_at} for s in sources]


def _manifest(
    sources: tuple[_Source, ...], lineage_sha: str, producer_sha: str,
    years: tuple[int, ...], ingested_at: str, revision: int, predecessor: str | None,
) -> dict[str, Any]:
    inputs = {"accounting_years":list(years), "source_lineage_sha256":lineage_sha,
              "producer_code_sha256":producer_sha, "sources":_source_records(sources)}
    return {
        "schema":"mastermind.bea_gvc_source_candidate/v1", **inputs,
        "input_fingerprint_sha256":_sha(_encoded(inputs)),
        "candidate_state":"BYTE_VERIFIED_NOT_INSTALLED",
        "l0_dataset_id":L0_DATASET, "l1_dataset_id":L1_DATASET,
        "code_namespace":CODE_NAMESPACE, "publisher_edition_date":EDITION_DATE,
        "publication_precision":"DAY", "published_at":None,
        "published_at_null_reason":"PUBLISHER_DAY_PRECISION_ONLY",
        "candidate_ingested_at":ingested_at, "candidate_revision_seq":revision,
        "supersedes_candidate_generation":predecessor,
        "native_ingested_at":None, "native_known_at":None, "native_revision_seq":None,
        "original_historical_available_at":None,
        "historical_availability_null_reason":"HISTORICAL_AVAILABILITY_UNVERIFIED",
        "source_response_count":len(sources), "expected_l1_rows":len(years)*138*139,
        "complete_2017_2024_panel":years == YEARS,
        "dataos_native_admitted":False, "historical_pit_eligible":False,
        "may_publish":False, "may_rank":False, "may_train":False, "may_trade":False,
        "source_kind":"imputed_industry_commodity_accounting",
        "named_company_relationship":False,
        "required_owner_action":"REVIEW_INSTALL_AND_ADMIT_THROUGH_EXISTING_DATA_OS",
    }


def _audit_candidate(candidate: BEAGVCCandidate) -> tuple[dict[str, Any], tuple[_Source, ...]]:
    """Recheck retained bytes, not a caller's mutable parsed table or green flag."""
    if (type(candidate) is not BEAGVCCandidate or type(candidate.sources) is not tuple
            or not 0 < len(candidate.sources) <= 72
            or any(type(s) is not _Source for s in candidate.sources)
            or type(candidate.capture_receipts) is not tuple):
        raise BEAGVCRefused("invalid in-process source candidate")
    manifest = _json(candidate.manifest_bytes, MAX_METADATA_BYTES)
    if type(manifest) is not dict:
        raise BEAGVCRefused("invalid candidate manifest")
    years = _years(manifest.get("accounting_years"))
    source_map = {(s.year, s.table_id):s.original_bytes for s in candidate.sources}
    if len(source_map) != len(candidate.sources):
        raise BEAGVCRefused("candidate contains duplicate source identities")
    if any(type(pair) is not tuple or len(pair) != 2 for pair in candidate.capture_receipts):
        raise BEAGVCRefused("invalid retained receipt tuple")
    receipts = dict(candidate.capture_receipts)
    if len(receipts) != len(candidate.capture_receipts):
        raise BEAGVCRefused("duplicate retained capture receipts")
    stamp = _instant(manifest.get("candidate_ingested_at"))
    if utc(stamp) > datetime.now(timezone.utc):
        raise BEAGVCRefused("candidate ingestion clock is in the future")
    bound = _prepare_sources(candidate.lineage_bytes, source_map, receipts,
                             manifest.get("source_lineage_sha256"), years, stamp)
    if (bound != candidate.sources
            or any(type(s.table) is not _Table or any(type(v) is not int
                   for row in s.table.amounts for v in row) for s in candidate.sources)):
        raise BEAGVCRefused("candidate table values or source metadata do not match original bytes")
    revision = manifest.get("candidate_revision_seq")
    prior = manifest.get("supersedes_candidate_generation")
    if type(revision) is not int or revision < 0:
        raise BEAGVCRefused("invalid candidate correction sequence")
    if (revision == 0 and prior is not None) or (revision > 0 and prior is None):
        raise BEAGVCRefused("missing or spurious candidate predecessor")
    if prior is not None:
        _digest(prior)
    expected = _manifest(bound, _digest(manifest.get("source_lineage_sha256")),
                         _digest(manifest.get("producer_code_sha256")),
                         years, stamp, revision, prior)
    if _encoded(expected) != candidate.manifest_bytes:
        raise BEAGVCRefused("candidate manifest is not canonical or claims different capabilities")
    return expected, bound


def bind_retained_responses(
    lineage_bytes: bytes,
    source_bytes: Mapping[tuple[int, str], bytes],
    capture_receipt_bytes: Mapping[str, bytes],
    *,
    selected_years: Sequence[int] = YEARS,
    expected_lineage_sha256: str = LINEAGE_SHA256,
    predecessor: BEAGVCCandidate | None = None,
) -> BEAGVCCandidate:
    """Bind complete selected years from retained original bytes, without I/O effects.

    The default lineage is the accepted research evidence pin. An explicit new
    expected pin supports a separately reviewed correction or a hermetic fixture;
    a supplied hash never grants source rights, installation or admission.
    Unchanged inputs and producer return the supplied predecessor unchanged.
    Changed evidence creates a linked candidate revision, never overwrites it.
    Concurrent storage/custody fencing remains the existing Data OS owner's job.
    """
    years = _years(selected_years)
    pin = _digest(expected_lineage_sha256)
    observed = datetime.now(timezone.utc).isoformat()
    bound = _prepare_sources(lineage_bytes, source_bytes, capture_receipt_bytes,
                             pin, years, observed)
    # Hash this exact implementation, not a caller's claimed code version.
    producer_sha = _producer_sha256()
    ingested = datetime.now(timezone.utc).isoformat()
    proposal = _manifest(bound, pin, producer_sha, years, ingested, 0, None)
    if predecessor is not None:
        prior, _ = _audit_candidate(predecessor)
        if prior["accounting_years"] != list(years):
            raise BEAGVCRefused("candidate correction must keep the same selected-year scope")
        if prior["input_fingerprint_sha256"] == proposal["input_fingerprint_sha256"]:
            return predecessor
        if utc(ingested) <= utc(prior["candidate_ingested_at"]):
            raise BEAGVCRefused("correction clock did not advance")
        proposal = _manifest(bound, pin, producer_sha, years, ingested,
                             prior["candidate_revision_seq"] + 1, predecessor.generation_id)
    return BEAGVCCandidate(_encoded(proposal), bound, lineage_bytes,
                          tuple(sorted(capture_receipt_bytes.items())))


def materialize_industry_inputs(candidate: BEAGVCCandidate) -> Iterator[dict[str, Any]]:
    """Return one coherent candidate generation; verify all inputs before any row.

    This is a candidate L1 transform, not a registered read service. Every row
    retains its original-byte lineage and negative accounting adjustments. There
    is no company mapping, historical PIT, ranking, sizing or publication grant.
    Installation and native ingestion clocks are intentionally still absent.
    """
    manifest, checked_sources = _audit_candidate(candidate)
    if manifest["producer_code_sha256"] != _producer_sha256():
        raise BEAGVCRefused("candidate producer differs; explicitly rebind before materialization")
    generation = candidate.generation_id
    by_year = {year:{s.table_id:s for s in checked_sources if s.year == year}
               for year in manifest["accounting_years"]}

    def rows() -> Iterator[dict[str, Any]]:
        for year, annual in by_year.items():
            use = annual["Use"].table
            source_ids = {key:annual[key].sha256 for key in TABLES}
            receipt_ids = {key:annual[key].capture_receipt_sha256 for key in TABLES}
            latest_capture = max((s.captured_at for s in annual.values()), key=utc)
            for j, industry in enumerate(use.industry_codes):
                for i, commodity in enumerate(use.commodity_codes):
                    world = annual["ImMatAll"].table.amounts[i][j]
                    regional = {name:annual[key].table.amounts[i][j] for key, name, _ in REGIONS}
                    delta = world - sum(regional.values())
                    flags = []
                    if world <= 0:
                        flags.append("WORLD_IMPORT_NONPOSITIVE")
                    if any(value < 0 for value in regional.values()):
                        flags.append("SOURCE_NEGATIVE_REGION_ADJUSTMENT")
                    if delta:
                        flags.append("PUBLISHER_ROUNDING_RESIDUAL")
                    yield {
                        "schema":"mastermind.bea_gvc_industry_input_candidate/v1",
                        "dataset_id":L1_DATASET, "source_generation_id":generation,
                        "candidate_state":"BYTE_VERIFIED_NOT_INSTALLED",
                        "publisher_edition_date":EDITION_DATE, "publication_precision":"DAY",
                        "published_at":None, "published_at_null_reason":"PUBLISHER_DAY_PRECISION_ONLY",
                        "accounting_year":year, "period_start":f"{year}-01-01",
                        "period_end":f"{year}-12-31", "period_end_is_availability":False,
                        "code_namespace":CODE_NAMESPACE, "industry_code_exact":industry,
                        "commodity_code_exact":commodity, "industry_name":use.industry_names[j],
                        "commodity_name":use.commodity_names[i],
                        "canonical_industry_id":None, "canonical_security_id":None,
                        "canonical_identity_null_reason":"CANONICAL_IDENTITY_NOT_ADOPTED",
                        "legacy_industry_mapping_state":(
                            "UNRESOLVED_5241X_VS_5241XX" if industry == "5241X" else "NOT_APPLIED"),
                        "source_kind":"imputed_industry_commodity_accounting",
                        "source_units":"million USD", "total_use_million_USD":use.amounts[i][j],
                        "world_import_million_USD":world,
                        **{f"{key}_import_million_USD":value for key, value in regional.items()},
                        "region_rounding_difference_million_USD":delta, "quality_flags":flags,
                        "source_lineage_sha256":manifest["source_lineage_sha256"],
                        "source_response_sha256_by_table":dict(source_ids),
                        "capture_receipt_sha256_by_table":dict(receipt_ids),
                        "research_source_capture_completed_at":latest_capture,
                        "capture_clock_semantics":"LATEST_COMPLETION_OF_NINE_BOUND_SOURCE_CAPTURES",
                        "producer_code_sha256":manifest["producer_code_sha256"],
                        "candidate_ingested_at":manifest["candidate_ingested_at"],
                        "candidate_revision_seq":manifest["candidate_revision_seq"],
                        "supersedes_candidate_generation":manifest["supersedes_candidate_generation"],
                        "native_ingested_at":None, "native_known_at":None, "native_revision_seq":None,
                        "original_historical_available_at":None,
                        "historical_availability_null_reason":"HISTORICAL_AVAILABILITY_UNVERIFIED",
                        "dataos_native_admitted":False, "historical_pit_eligible":False,
                        "named_company_relationship":False, "may_publish":False,
                        "may_rank":False, "may_train":False, "may_trade":False,
                        "attribution":"Source: U.S. Bureau of Economic Analysis",
                    }
    return rows()


@dataclass(frozen=True)
class BEAGVCCandidateIndustryView:
    """Complete immutable L1 candidate bytes; not an installed Data OS store."""

    industry_code_exact: str
    source_generation_id: str
    proposed_relative_storage_path: str
    jsonl_bytes: bytes
    sha256: str
    row_count: int


def candidate_industry_jsonl(
    candidate: BEAGVCCandidate, industry_code_exact: str,
) -> BEAGVCCandidateIndustryView:
    """Package one exact industry across every selected accounting year.

    Revalidate the entire original-byte candidate before producing anything.
    This is an in-memory, digest-bound export for the incumbent native owner,
    not a source-store write, native ingestion, public serving or rights grant.
    The proposed path is informational; no directory or file is opened.
    """
    if type(industry_code_exact) is not str or not _CODE.fullmatch(industry_code_exact):
        raise BEAGVCRefused("exact safe source industry code required")
    all_rows = materialize_industry_inputs(candidate)
    payload_rows: list[bytes] = []
    total_bytes = 0
    for row in all_rows:
        if row["industry_code_exact"] == industry_code_exact:
            encoded = _encoded(row) + b"\n"
            total_bytes += len(encoded)
            if total_bytes > MAX_INDUSTRY_VIEW_BYTES:
                raise BEAGVCRefused("candidate industry view exceeds byte bound")
            payload_rows.append(encoded)
    expected = 139 * len(candidate.manifest["accounting_years"])
    if len(payload_rows) != expected:
        raise BEAGVCRefused("industry absent or incomplete in candidate source axes")
    payload = b"".join(payload_rows)
    return BEAGVCCandidateIndustryView(
        industry_code_exact=industry_code_exact,
        source_generation_id=candidate.generation_id,
        proposed_relative_storage_path=(
            "data/bea/gvc/may2026/industry_inputs/"
            f"industry_{industry_code_exact}.jsonl"
        ),
        jsonl_bytes=payload,
        sha256=_sha(payload),
        row_count=len(payload_rows),
    )
