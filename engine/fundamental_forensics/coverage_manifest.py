"""FIF coverage step 6 (b3): the served-only coverage manifest producer.

The manifest is the per-cell input the coverage proof recomputes tier coverage
from.  This module derives every cell from what the production request path
actually serves at one ``as_of`` cutoff:

* Membership comes only from the tiers file: ``core_1000`` plus ``deep_R1``
  (refused unless ``deep_R1`` and ``deep_R2`` name the same issuers).  A deep
  member is ``tier_assigned: deep``; every other member is ``core``.  The
  ticker printed on an issuer row is the tiers file's own ticker.
* An issuer is served only through its coverage-contract
  ``security_master_binding.issuer_id``, the latest verified production
  generation for that issuer, and the production query and statement
  providers over that same generation.  The generation id is pinned once and
  every provider delivery must carry it (``generation_moved`` otherwise).
* A member that is not served gets every in-window cell ``absent`` with
  reason ``not_served`` — there is no fallback source.  A served member whose
  generation has no filing for a slot gets that slot's cells ``absent`` with
  reason ``slot_not_filed``.
* Statement slots (A1/A2 annual, I1/I2 interim) come from the served
  generation's statement packages, cut off at ``as_of`` on both the filing
  date and the acceptance clock.
* Metric cells come from the kernel itself: ``BitemporalMetricQueryEngine``
  built with exactly the keywords ``query_service`` passes — no
  not-presented pack and no filing packages, because production serves no
  not-presented verdicts today.  The cell state mapping never upgrades a
  kernel answer.  ``reason_code`` is the bare kernel code (the text before
  the first ``:``); the full kernel text rides in ``kernel_reason``.  The
  not-presented / qualified mapping is kept for the day production serves
  those verdicts; the governed pack identity is recorded in the header with
  ``applied_by_kernel: false``.
* The windowless deep components run their production producers.  Every
  ``specialist:PKnn`` cell is the registered pack producer's envelope over
  the served generation's admitted packages (the producers build their own
  ledger from those packages), and the ``packet`` cell is the financial
  intelligence packet built for the member's A1 slot under the frozen
  request (seat ruling ``DEC:FIF-MANIFEST-PACKET-REQUEST-FROZEN-2026-10-20``).
  A refused producer or builder is one absent cell — never a refused
  manifest — and every answered specialist cell pins the producer bytes
  through ``pack_content_sha256`` / ``pack_schema_digest``.  The ``journey``
  cell keeps ``no_production_producer`` until the journey ledger has an
  engine home.

The module never imports the coverage proof or any script: the producer and
the proof are independent reimplementations of the same rules, and the proof
only accepts a manifest whose rollups it recomputes identically.  Output is
canonical JSON with no wall clock; the same inputs give the same bytes.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml

from .financial_intelligence_packet import (
    DEFAULT_REQUESTED_METRICS,
    EntityInput,
    PacketQueryRequest,
    build_financial_intelligence_packet_from_repo,
    visible_query_from_request,
)
from .issuer_sic import resolve_issuer_sic
from .metric_registry import CATALOG_SCHEMA, FORMULAS_SCHEMA
from .not_presented import NA_BASIS_NOT_PRESENTED_ITEM, load_not_presented_pack
from .production_datasets import (
    build_production_dataset_store,
    load_entity_role,
    load_latest_generation,
)
from .production_provider import (
    ProductionFinancialQueryProvider,
    ProductionFinancialStatementProvider,
)
from .query import (
    HARD_MAX_METRICS,
    HARD_MAX_PERIODS,
    QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX,
    BitemporalMetricQueryEngine,
    CellState,
    PeriodRequest,
    QueryBounds,
    QueryEntity,
    QueryPolicy,
)
from .query_service import (
    FinancialQueryAdmissionError,
    FinancialQueryUnavailableError,
    enforce_dataset_admission_floor,
    validate_supplied_dataset,
)
from .raw_ledger import canonical_json, parse_utc
from .revision_service import occurrence_keyed_filing_metadata
from .specialist_pack_contract import load_pack_schema
from .specialist_packs import (
    PackInput,
    SpecialistPackError,
    produce_pack,
    registered_pack_ids,
)
from .specialist_packs.base import _primary_duration_opening_bound
from .statement_graph import StatementGraphError

MANIFEST_SCHEMA = "fundamental_forensics.coverage_manifest/v1"
TIERS_SCHEMA = "fundamental_forensics.coverage_tiers/v1"
COVERAGE_CONTRACT_SCHEMA = "fundamental_forensics.coverage_contract/v1"
THRESHOLDS_SCHEMA = "fundamental_forensics.coverage_thresholds/v1"
PRODUCER_ID = "fundamental_forensics.coverage_manifest.b3"
BASIS_SERVED_ONLY = "served_only"
SERVED_SET_PREFIX = "served-set/sha256:"
UNSERVED_GENERATION_PREFIX = "unserved:"
WILDCARD_PERIOD = "*"
QUERY_SELECTION = "latest_known_as_of"
QUERY_CHUNK_PERIODS = 32

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THRESHOLDS = (
    _REPO_ROOT / "config" / "fundamental_forensics" / "coverage" / "c2_thresholds_v1.json"
)
DEFAULT_CATALOG = (
    _REPO_ROOT / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"
)
DEFAULT_FORMULAS = (
    _REPO_ROOT
    / "config"
    / "fundamental_forensics"
    / "metrics"
    / "v1"
    / "formulas"
    / "core.yaml"
)

# Statement slot families.  An amendment ("/A") belongs to its base form.
ANNUAL_FORMS = frozenset({"10-K", "20-F", "40-F"})
INTERIM_FORMS = frozenset({"10-Q"})
_AMENDMENT_SUFFIX = "/A"
_FAMILY_ANNUAL = "annual"
_FAMILY_INTERIM = "interim"
_PERIOD_ID = re.compile(r"^([AI])([1-9][0-9]*)$")
_CIK = re.compile(r"^[0-9]{10}$")
_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_BARE_REASON = re.compile(r"^[a-z0-9_]+$")

# Issuer serve states.
SERVE_SERVED = "served"
SERVE_NO_BINDING = "no_binding"
SERVE_NO_GENERATION = "no_generation"
SERVE_GENERATION_UNAVAILABLE = "generation_unavailable"
SERVE_ADMITTED_AFTER_AS_OF = "admitted_after_as_of"
SERVE_BINDING_MISMATCH = "binding_mismatch"

# Cell statuses (the proof's vocabulary; this producer emits three of them).
STATUS_PRESENT = "present"
STATUS_ABSENT = "absent"
STATUS_NOT_APPLICABLE = "not_applicable"

# N/A bases.
NA_BASIS_KERNEL = "kernel"
NA_BASIS_CLASS = "class_policy"
_CLASS_POLICY_REASON = "not_applicable_for_issuer_class"

# Reason codes.
REASON_PRESENT = "present"
REASON_NOT_SERVED = "not_served"
REASON_SLOT_NOT_FILED = "slot_not_filed"
REASON_PERIOD_NOT_IN_LEDGER = "period_not_in_ledger"
REASON_METRIC_UNSUPPORTED = "metric_unsupported"
REASON_KERNEL_REFUSED = "kernel_refused"
REASON_KERNEL_UNSPECIFIED = "kernel_reason_unspecified"
REASON_NO_PRODUCTION_PRODUCER = "no_production_producer"
REASON_PACK_PRODUCER_REFUSED = "pack_producer_refused"
REASON_PACK_REQUIRED_FIELDS_ABSENT = "pack_required_fields_absent"
REASON_PACKET_BUILDER_REFUSED = "packet_builder_refused"
REASON_PACKET_NO_VALUED_CELL = "packet_no_valued_cell"
REASON_PACKET_IDENTITY_INCOMPLETE = "packet_identity_incomplete"
REASON_PACKAGE_ROLE_ABSENT = "package_role_absent"
REASON_PACKAGE_MEMBER_NOT_STORED = "package_member_not_stored"
REASON_PACKAGE_BYTES_ABSENT = "package_bytes_absent"
REASON_STATEMENT_ABSENT = "statement_absent"
REASON_STATEMENT_REFUSED = "statement_refused"
REASON_STATEMENT_EMPTY = "statement_empty"

_COMPLETE_BAND = "complete"
_NO_APPLICABLE_FIELDS_BAND = "no_applicable_fields"

# Windowless deep-component literals (the producer framework's own closed
# vocabularies, kept private here so the manifest's constants stay its own).
# The packet contract admits exactly two evaluation modes; the seat ruling's
# ``production_manifest`` label is not among them (EVALUATION_MODES and the
# packet schema enum both refuse it), so the frozen request carries the
# contract's default label — recorded as a lane deviation.  The pack envelope
# contract's closed ``sic_source`` enum admits only
# sec_submissions/dei/unbound/null.  The shipped coverage contracts record each
# member's SIC with its capture provenance (the issuer's SEC submissions
# document, ``sic_source.capture_path``), so a SIC the contract resolver
# returns is labelled ``sec_submissions``; a CIK the contracts do not bind
# rides as ``unbound`` and the pack keeps its issuer_class_unknown path.
_PACKET_EVALUATION_MODE = "historical_replay"
_IDENTITY_BASIS = "production_generation_binding_v1"
_SIC_SOURCE_RESOLVED = "sec_submissions"
_SIC_SOURCE_UNBOUND = "unbound"
_APPLICABILITY_APPLICABLE = "applicable"
_APPLICABILITY_NOT_APPLICABLE = "not_applicable"
_APPLICABILITY_NOT_EVALUABLE = "not_evaluable"
_ROW_VALUED = "valued"
_CLASS_NA_CODES = frozenset(
    {"issuer_class_not_bank", "issuer_class_unknown", "sic_outside_biotech_codes"}
)
_MISSING_FIELD_IDS_BOUND = 32
_PRODUCER_REASON_BOUND = 128


class CoverageManifestError(ValueError):
    """A typed refusal: the manifest is not produced at all."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Input readers
# ---------------------------------------------------------------------------


def _read_bytes(path: str | Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise CoverageManifestError(f"{label}_unreadable", f"{label} is unreadable: {path}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_mapping(data: bytes, label: str) -> dict[str, Any]:
    try:
        document = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise CoverageManifestError(f"{label}_malformed", f"{label} is not decodable") from exc
    if not isinstance(document, dict):
        raise CoverageManifestError(f"{label}_malformed", f"{label} must be a mapping")
    return document


def _json_mapping(data: bytes, label: str) -> dict[str, Any]:
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageManifestError(f"{label}_malformed", f"{label} is not decodable JSON") from exc
    if not isinstance(document, dict):
        raise CoverageManifestError(f"{label}_malformed", f"{label} must be an object")
    return document


@dataclass(frozen=True)
class SlotPeriod:
    """One declared statement period id (``A1`` .. ``I2``)."""

    period_id: str
    family: str
    rank: int


def _slot_period(period_id: Any) -> SlotPeriod:
    if not isinstance(period_id, str):
        raise CoverageManifestError("thresholds_malformed", "period ids must be strings")
    match = _PERIOD_ID.fullmatch(period_id)
    if match is None:
        raise CoverageManifestError(
            "thresholds_malformed", f"unsupported period id {period_id!r}"
        )
    family = _FAMILY_ANNUAL if match.group(1) == "A" else _FAMILY_INTERIM
    return SlotPeriod(period_id=period_id, family=family, rank=int(match.group(2)))


@dataclass(frozen=True)
class ManifestThresholds:
    core_periods: tuple[SlotPeriod, ...]
    deep_periods: tuple[SlotPeriod, ...]
    package_roles: tuple[str, ...]
    statements: tuple[str, ...]
    specialist_packs: tuple[str, ...]
    require_packet: bool
    require_journey: bool
    bands: tuple[tuple[str, float], ...]

    def band_for_rate(self, rate: float | None) -> str:
        if rate is None:
            return _NO_APPLICABLE_FIELDS_BAND
        for name, min_rate in self.bands:
            if rate >= min_rate:
                return name
        return self.bands[-1][0]


def _names(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise CoverageManifestError(
            "thresholds_malformed", f"{field_name} must be a list of names"
        )
    if len(set(value)) != len(value):
        raise CoverageManifestError("thresholds_malformed", f"{field_name} repeats a name")
    return tuple(value)


def load_manifest_thresholds(data: bytes) -> ManifestThresholds:
    document = _safe_mapping(data, "thresholds")
    if document.get("schema") != THRESHOLDS_SCHEMA:
        raise CoverageManifestError("thresholds_malformed", "unsupported thresholds schema")
    tiers = document.get("tiers")
    if not isinstance(tiers, dict):
        raise CoverageManifestError("thresholds_malformed", "thresholds tiers must be a mapping")
    deep = tiers.get("deep")
    core = tiers.get("core")
    if not isinstance(deep, dict) or not isinstance(core, dict):
        raise CoverageManifestError("thresholds_malformed", "thresholds tiers need deep and core")
    core_periods = tuple(_slot_period(p) for p in _names(core.get("periods"), "core.periods"))
    deep_periods = tuple(_slot_period(p) for p in _names(deep.get("periods"), "deep.periods"))
    if not {p.period_id for p in core_periods} <= {p.period_id for p in deep_periods}:
        raise CoverageManifestError(
            "thresholds_malformed", "core periods must be a subset of deep periods"
        )
    for flag in ("require_packet", "require_journey"):
        if not isinstance(deep.get(flag), bool):
            raise CoverageManifestError("thresholds_malformed", f"deep.{flag} must be a boolean")
    packs = _names(deep.get("specialist_packs"), "deep.specialist_packs")
    for pack in packs:
        if not re.fullmatch(r"PK[0-9]{2}", pack):
            raise CoverageManifestError("thresholds_malformed", f"bad specialist pack {pack!r}")
    raw_bands = document.get("field_presence_bands")
    if not isinstance(raw_bands, list) or not raw_bands:
        raise CoverageManifestError("thresholds_malformed", "field_presence_bands must be a list")
    bands: list[tuple[str, float]] = []
    for entry in raw_bands:
        if not isinstance(entry, dict):
            raise CoverageManifestError("thresholds_malformed", "band entries must be mappings")
        name = entry.get("band")
        min_rate = entry.get("min_rate")
        if (
            not isinstance(name, str)
            or isinstance(min_rate, bool)
            or not isinstance(min_rate, (int, float))
        ):
            raise CoverageManifestError("thresholds_malformed", "band entry is malformed")
        bands.append((name, float(min_rate)))
    if _COMPLETE_BAND not in {name for name, _ in bands}:
        raise CoverageManifestError("thresholds_malformed", "no complete band is declared")
    return ManifestThresholds(
        core_periods=core_periods,
        deep_periods=deep_periods,
        package_roles=_names(deep.get("required_package_roles"), "deep.required_package_roles"),
        statements=_names(deep.get("required_statements"), "deep.required_statements"),
        specialist_packs=packs,
        require_packet=deep["require_packet"],
        require_journey=deep["require_journey"],
        bands=tuple(bands),
    )


def load_metric_ids(catalog: bytes, formulas: bytes) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(direct, formula)`` metric ids; direct = catalog minus formula ids."""

    def ids(document: Mapping[str, Any], key: str, label: str) -> list[str]:
        entries = document.get(key)
        if not isinstance(entries, list) or not entries:
            raise CoverageManifestError(f"{label}_malformed", f"{label} lists no {key}")
        out: list[str] = []
        for entry in entries:
            metric_id = entry.get("metric_id") if isinstance(entry, dict) else None
            if not isinstance(metric_id, str) or not metric_id:
                raise CoverageManifestError(f"{label}_malformed", f"{label} entry has no metric_id")
            out.append(metric_id)
        if len(set(out)) != len(out):
            raise CoverageManifestError(f"{label}_malformed", f"{label} repeats a metric_id")
        return out

    catalog_doc = _safe_mapping(catalog, "catalog")
    formulas_doc = _safe_mapping(formulas, "formulas")
    if catalog_doc.get("schema") != CATALOG_SCHEMA:
        raise CoverageManifestError("catalog_malformed", "unsupported metric catalog schema")
    if formulas_doc.get("schema") != FORMULAS_SCHEMA:
        raise CoverageManifestError("formulas_malformed", "unsupported metric formulas schema")
    catalog_ids = ids(catalog_doc, "metrics", "catalog")
    formula_ids = ids(formulas_doc, "formulas", "formulas")
    unknown = sorted(set(formula_ids) - set(catalog_ids))
    if unknown:
        raise CoverageManifestError(
            "catalog_drift", f"formula ids missing from the catalog: {', '.join(unknown)}"
        )
    formula_set = set(formula_ids)
    direct = tuple(sorted(m for m in catalog_ids if m not in formula_set))
    return direct, tuple(sorted(formula_set))


@dataclass(frozen=True)
class TierMember:
    cik: str
    ticker: str
    tier_assigned: str


@dataclass(frozen=True)
class TiersInput:
    cutoff_at: str
    members: tuple[TierMember, ...]


def _tier_entries(document: Mapping[str, Any], key: str) -> list[tuple[str, str]]:
    entries = document.get(key)
    if not isinstance(entries, list):
        raise CoverageManifestError("tiers_malformed", f"tiers {key} must be a list")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CoverageManifestError("tiers_malformed", f"tiers {key} entry is malformed")
        cik = entry.get("canonical_cik")
        ticker = entry.get("ticker")
        if not isinstance(cik, str) or not _CIK.fullmatch(cik):
            raise CoverageManifestError("tiers_malformed", f"tiers {key} entry has a bad cik")
        if not isinstance(ticker, str) or not ticker:
            raise CoverageManifestError("tiers_malformed", f"tiers {key} entry has no ticker")
        if cik in seen:
            raise CoverageManifestError("tiers_malformed", f"tiers {key} repeats cik {cik}")
        seen.add(cik)
        out.append((cik, ticker))
    return out


def load_tiers(data: bytes) -> TiersInput:
    document = _json_mapping(data, "tiers")
    if document.get("schema") != TIERS_SCHEMA:
        raise CoverageManifestError("tiers_malformed", "unsupported tiers schema")
    cutoff_at = document.get("cutoff_at")
    if not isinstance(cutoff_at, str) or not cutoff_at:
        raise CoverageManifestError("tiers_malformed", "tiers cutoff_at is required")
    core = _tier_entries(document, "core_1000")
    deep_r1 = _tier_entries(document, "deep_R1")
    deep_r2 = _tier_entries(document, "deep_R2")
    if {cik for cik, _ in deep_r1} != {cik for cik, _ in deep_r2}:
        raise CoverageManifestError(
            "deep_rounds_disagree", "deep_R1 and deep_R2 do not name the same issuers"
        )
    if dict(deep_r1) != dict(deep_r2):
        raise CoverageManifestError(
            "deep_rounds_disagree", "deep_R1 and deep_R2 give an issuer different tickers"
        )
    deep_ciks = {cik for cik, _ in deep_r1}
    tickers: dict[str, str] = {}
    for cik, ticker in core + deep_r1:
        known = tickers.setdefault(cik, ticker)
        if known != ticker:
            raise CoverageManifestError(
                "tiers_malformed", f"tiers give cik {cik} two different tickers"
            )
    members = tuple(
        TierMember(
            cik=cik,
            ticker=tickers[cik],
            tier_assigned="deep" if cik in deep_ciks else "core",
        )
        for cik in sorted(tickers)
    )
    return TiersInput(cutoff_at=cutoff_at, members=members)


def load_coverage_contract(data: bytes) -> dict[str, dict[str, Any]]:
    """Coverage-contract issuers by CIK.

    Reimplements the publisher's reader
    (``scripts/publish_fif_production_datasets.py`` ``load_fif_coverage_contract``)
    without importing it: same schema, identity, accession and binding shape
    checks; a repeated CIK refuses the whole contract.
    """
    document = _json_mapping(data, "coverage_contract")
    if not isinstance(document.get("issuers"), list):
        raise CoverageManifestError("contract_malformed", "coverage contract shape is invalid")
    if document.get("schema") != COVERAGE_CONTRACT_SCHEMA:
        raise CoverageManifestError("contract_malformed", "unsupported coverage contract schema")
    by_cik: dict[str, dict[str, Any]] = {}
    for issuer in document["issuers"]:
        if not isinstance(issuer, dict):
            raise CoverageManifestError("contract_malformed", "coverage contract issuer is malformed")
        cik = issuer.get("cik")
        ticker = issuer.get("ticker")
        if not isinstance(cik, str) or not isinstance(ticker, str) or not cik or not ticker:
            raise CoverageManifestError(
                "contract_malformed", "coverage contract issuer identity is malformed"
            )
        if cik in by_cik:
            raise CoverageManifestError("contract_malformed", f"coverage contract repeats a CIK: {cik}")
        accessions = issuer.get("accessions")
        if not isinstance(accessions, list) or not accessions:
            raise CoverageManifestError(
                "contract_malformed", f"coverage contract issuer lists no accessions: {cik}"
            )
        for entry in accessions:
            if not isinstance(entry, dict) or not isinstance(entry.get("accession"), str):
                raise CoverageManifestError(
                    "contract_malformed", f"coverage contract accession entry is malformed: {cik}"
                )
        binding = issuer.get("security_master_binding")
        if binding is not None and not isinstance(binding, dict):
            raise CoverageManifestError(
                "contract_malformed", f"coverage contract security_master_binding is malformed: {cik}"
            )
        by_cik[cik] = issuer
    return by_cik


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------


@dataclass
class ServedIssuer:
    """One issuer the production request path serves at ``as_of``."""

    issuer_id: str
    generation_id: str
    dataset: Any
    binding: Any
    packages: tuple[Any, ...]
    # The served generation's stored issuer display name (the entity role's
    # ``entity.name``); ``None`` when the generation stored no name.
    name: str | None = None


@dataclass
class _ServeResult:
    state: str
    served: ServedIssuer | None = None


def _delivery_generation(delivery: Any) -> Any:
    if isinstance(delivery, Mapping):
        return delivery.get("dataset_generation_id")
    return None


def serve_issuer(
    cik: str,
    contract_issuer: Mapping[str, Any] | None,
    *,
    store: Any,
    as_of: datetime,
    policy: QueryPolicy,
    query_provider: Any,
    statement_provider: Any,
) -> _ServeResult:
    """Resolve one member through its binding and the production providers."""
    if contract_issuer is None:
        return _ServeResult(SERVE_NO_BINDING)
    binding = contract_issuer.get("security_master_binding")
    if not isinstance(binding, Mapping):
        return _ServeResult(SERVE_NO_BINDING)
    issuer_id = binding.get("issuer_id")
    if not isinstance(issuer_id, str) or not issuer_id:
        return _ServeResult(SERVE_NO_BINDING)
    if binding.get("issuer_cik") != cik:
        return _ServeResult(SERVE_BINDING_MISMATCH)

    try:
        generation = load_latest_generation(store, issuer_id)
    except Exception:  # noqa: BLE001 - every damage class is unavailability
        return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
    if generation is None:
        return _ServeResult(SERVE_NO_GENERATION)
    try:
        generation_id = generation.generation_id
        generation_binding = generation.binding
        admitted_at = generation.admitted_at
        accessions = tuple(generation.statement_accessions())
    except Exception:  # noqa: BLE001
        return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
    if generation_binding.cik != cik or generation_binding.entity_id != issuer_id:
        return _ServeResult(SERVE_BINDING_MISMATCH)
    if admitted_at > as_of:
        return _ServeResult(SERVE_ADMITTED_AFTER_AS_OF)

    try:
        dataset = query_provider.resolve(issuer_id)
    except FinancialQueryAdmissionError as exc:
        if getattr(exc, "status_code", None) == 400:
            return _ServeResult(SERVE_NO_GENERATION)
        return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
    except Exception:  # noqa: BLE001 - FinancialQueryUnavailableError and damage
        return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
    if _delivery_generation(dataset.delivery) != generation_id:
        raise CoverageManifestError(
            "generation_moved",
            f"the query provider served a different generation for cik {cik}",
        )
    try:
        served_binding = validate_supplied_dataset(issuer_id, dataset)
    except (FinancialQueryAdmissionError, FinancialQueryUnavailableError):
        return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
    if served_binding.cik != cik:
        return _ServeResult(SERVE_BINDING_MISMATCH)
    try:
        enforce_dataset_admission_floor(policy, dataset)
    except FinancialQueryUnavailableError:
        return _ServeResult(SERVE_ADMITTED_AFTER_AS_OF)

    packages: list[Any] = []
    for accession in accessions:
        try:
            package = statement_provider.resolve(issuer_id, accession)
        except Exception:  # noqa: BLE001
            return _ServeResult(SERVE_GENERATION_UNAVAILABLE)
        if _delivery_generation(getattr(package, "delivery", None)) != generation_id:
            raise CoverageManifestError(
                "generation_moved",
                f"the statement provider served a different generation for cik {cik}",
            )
        packages.append(package)
    try:
        entity_role = load_entity_role(generation)
        stored_name = entity_role.get("entity", {}).get("name")
    except Exception:  # noqa: BLE001 - a damaged entity role stores no name
        stored_name = None
    name = stored_name if isinstance(stored_name, str) and stored_name else None
    return _ServeResult(
        SERVE_SERVED,
        ServedIssuer(
            issuer_id=issuer_id,
            generation_id=generation_id,
            dataset=dataset,
            binding=served_binding,
            packages=tuple(packages),
            name=name,
        ),
    )


# ---------------------------------------------------------------------------
# Statement slots
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Slot:
    family: str
    rank: int
    period_of_report: str
    accession: str
    package: Any = field(repr=False, compare=False)


def _form_family(form: Any) -> tuple[str | None, bool]:
    if not isinstance(form, str):
        return None, False
    amendment = form.endswith(_AMENDMENT_SUFFIX)
    base = form[: -len(_AMENDMENT_SUFFIX)] if amendment else form
    if base in ANNUAL_FORMS:
        return _FAMILY_ANNUAL, amendment
    if base in INTERIM_FORMS:
        return _FAMILY_INTERIM, amendment
    return None, amendment


def _strict_date(value: Any) -> date:
    """A ``YYYY-MM-DD`` date; ``fromisoformat`` alone also takes ``YYYYMMDD``."""
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError(f"not a YYYY-MM-DD date: {value!r}")
    return date.fromisoformat(value)


def _visible_clock(manifest: Mapping[str, Any], as_of: datetime) -> datetime | None:
    """The acceptance clock when the filing is visible at ``as_of``, else None."""
    try:
        filed = _strict_date(manifest.get("filing_date"))
        accepted = parse_utc(manifest.get("source_accepted_at"), field_name="source_accepted_at")
        _strict_date(manifest.get("period_of_report"))
    except (TypeError, ValueError):
        return None
    if accepted is None:
        return None
    if filed > as_of.date() or accepted > as_of:
        return None
    return accepted


def select_slots(packages: Iterable[Any], as_of: datetime) -> dict[tuple[str, int], Slot]:
    """Distinct period_of_report values per family, newest first.

    Within one period the original filing outranks an amendment; then the
    latest acceptance; then the greatest accession number.
    """
    pools: dict[str, dict[str, list[tuple[bool, datetime, str, Any]]]] = {
        _FAMILY_ANNUAL: {},
        _FAMILY_INTERIM: {},
    }
    for package in packages:
        manifest = package.manifest
        family, amendment = _form_family(manifest.get("form"))
        if family is None:
            continue
        accepted = _visible_clock(manifest, as_of)
        if accepted is None:
            continue
        accession = manifest.get("accession")
        if not isinstance(accession, str):
            continue
        por = str(manifest["period_of_report"])
        pools[family].setdefault(por, []).append((amendment, accepted, accession, package))
    slots: dict[tuple[str, int], Slot] = {}
    for family, by_period in pools.items():
        for rank, por in enumerate(sorted(by_period, reverse=True), start=1):
            candidates = by_period[por]
            originals = [c for c in candidates if not c[0]]
            pool = originals or candidates
            _amendment, _accepted, accession, package = max(pool, key=lambda c: (c[1], c[2]))
            slots[(family, rank)] = Slot(
                family=family,
                rank=rank,
                period_of_report=por,
                accession=accession,
                package=package,
            )
    return slots


# ---------------------------------------------------------------------------
# Periods and kernel queries
# ---------------------------------------------------------------------------


def governed_duration_universe(ledger: Any, registry: Any) -> list[tuple[str, str]]:
    """Distinct ``(start, end)`` durations of governed ledger occurrences.

    Mirrors ``scripts/fif_a1_journey_ledger.py`` ``_period_universe``: only
    occurrences whose concept is governed by a registry alias count, and a
    duration is ``(context.start, context.end)``.
    """
    governed = set()
    for contract in registry.contracts:
        for mapping in contract.mappings:
            for alias in mapping.taxonomy_concept_aliases:
                governed.add(f"{alias.taxonomy}:{alias.concept}")
    keys: dict[tuple[str, str], None] = {}
    for event in ledger.events:
        if event.concept_qname not in governed:
            continue
        context = event.context
        if context.instant is None:
            keys.setdefault((context.start.isoformat(), context.end.isoformat()))
    return sorted(keys)


def duration_for_slot(
    universe: Sequence[tuple[str, str]], period_of_report: str, family: str
) -> tuple[str, str] | None:
    """Longest duration ending at the report date (annual), shortest (interim)."""
    ending = [
        (date.fromisoformat(end) - date.fromisoformat(start), start, end)
        for start, end in universe
        if end == period_of_report
    ]
    if not ending:
        return None
    choose = max if family == _FAMILY_ANNUAL else min
    _length, start, end = choose(ending)
    return start, end


def visible_metric_kinds(registry: Any, as_of: datetime) -> dict[str, str]:
    bundle = registry.governance_bundle_at(as_of)
    return {
        contract.metric_id: contract.period_constraints.kind for contract in bundle.contracts
    }


def _chunks(items: Sequence[Any], size: int) -> list[Sequence[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _cell_state(state: Any) -> CellState:
    return state if isinstance(state, CellState) else CellState(state)


def split_kernel_reason(reason: Any) -> tuple[str | None, str | None]:
    """``(bare code, full kernel text)`` for one kernel reason.

    The kernel writes ``"<code>: <detail>"``; the proof keys failures by the
    text after the last ``:`` of ``<period>/<field>:<reason_code>``, so the
    manifest's ``reason_code`` must be the bare code alone.  A code that is
    not ``[a-z0-9_]+`` becomes ``kernel_reason_unspecified``; the full text is
    kept either way.
    """
    if not isinstance(reason, str) or not reason.strip():
        return None, None
    text = reason.strip()
    code = text.split(":", 1)[0].strip()
    if not _BARE_REASON.fullmatch(code):
        code = REASON_KERNEL_UNSPECIFIED
    return code, text


def _evidence_fields(evidence: Any, out: Mapping[str, Any]) -> dict[str, Any]:
    """The not-presented evidence keys; never a key the cell already carries."""
    fields = dict(evidence.to_dict())
    clash = sorted(key for key in fields if key in out or not str(key).startswith("np_"))
    if clash:
        raise CoverageManifestError(
            "not_presented_evidence_collision",
            f"not-presented evidence may add only new np_* keys; got {', '.join(map(str, clash))}",
        )
    return fields


def map_metric_cell(
    cell: Any,
    *,
    cik: str,
    period_id: str,
    source_generation_id: str,
    np_pack: Any,
) -> dict[str, Any]:
    """Map one kernel cell to a manifest cell without upgrading its state."""
    out: dict[str, Any] = {
        "cik": cik,
        "period_id": period_id,
        "field_id": f"metric:{cell.metric_id}",
        "source_generation_id": source_generation_id,
    }
    state = _cell_state(cell.state)
    provenance = cell.provenance
    reason, kernel_reason = split_kernel_reason(
        cell.reason or getattr(provenance, "reason", None)
    )
    if state is CellState.VALUE:
        out["status"] = STATUS_PRESENT
        out["reason_code"] = REASON_PRESENT
        qualified = tuple(getattr(provenance, "qualified_not_presented", ()) or ())
        if qualified:
            out["qualifier"] = QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX + ", ".join(qualified)
            out["qualifier_policy"] = f"{np_pack.pack_id}/{np_pack.pack_version}"
        return out
    if state is CellState.NOT_APPLICABLE:
        out["status"] = STATUS_NOT_APPLICABLE
        if reason:
            out["reason_code"] = reason
            out["kernel_reason"] = kernel_reason
        evidence = getattr(provenance, "not_presented", None)
        if (
            getattr(provenance, "na_basis", None) == NA_BASIS_NOT_PRESENTED_ITEM
            and evidence is not None
        ):
            out.update(_evidence_fields(evidence, out))
            out["na_basis"] = NA_BASIS_NOT_PRESENTED_ITEM
        elif reason == _CLASS_POLICY_REASON:
            out["na_basis"] = NA_BASIS_CLASS
        else:
            out["na_basis"] = NA_BASIS_KERNEL
        return out
    out["status"] = STATUS_ABSENT
    out["reason_code"] = reason or REASON_KERNEL_UNSPECIFIED
    if kernel_reason:
        out["kernel_reason"] = kernel_reason
    out["kernel_state"] = state.value
    return out


def _absent(cik: str, period_id: str, field_id: str, reason: str, generation: str) -> dict[str, Any]:
    return {
        "cik": cik,
        "period_id": period_id,
        "field_id": field_id,
        "status": STATUS_ABSENT,
        "reason_code": reason,
        "source_generation_id": generation,
    }


def _present(cik: str, period_id: str, field_id: str, generation: str) -> dict[str, Any]:
    return {
        "cik": cik,
        "period_id": period_id,
        "field_id": field_id,
        "status": STATUS_PRESENT,
        "reason_code": REASON_PRESENT,
        "source_generation_id": generation,
    }


def _query_cells(
    engine: Any,
    *,
    ticker: str,
    metrics: Sequence[str],
    requests: Sequence[tuple[tuple[Any, ...], PeriodRequest]],
    policy: QueryPolicy,
) -> tuple[dict[tuple[str, tuple[Any, ...]], Any], set[tuple[str, tuple[Any, ...]]]]:
    """Query in bounded chunks; a refused chunk marks its cells refused."""
    results: dict[tuple[str, tuple[Any, ...]], Any] = {}
    refused: set[tuple[str, tuple[Any, ...]]] = set()
    if not metrics or not requests:
        return results, refused
    for metric_chunk in _chunks(list(metrics), HARD_MAX_METRICS):
        for period_chunk in _chunks(list(requests), QUERY_CHUNK_PERIODS):
            try:
                matrix = engine.query_matrix(
                    tickers=[ticker],
                    metrics=list(metric_chunk),
                    periods=[request for _key, request in period_chunk],
                    policy=policy,
                )
            except Exception:  # noqa: BLE001 - the kernel refused this chunk
                for metric_id in metric_chunk:
                    for key, _request in period_chunk:
                        refused.add((metric_id, key))
                continue
            for cell in matrix.cells:
                results[(cell.metric_id, cell.period.key)] = cell
    return results, refused


def _served_metric_cells(
    cik: str,
    served: ServedIssuer,
    periods: Sequence[SlotPeriod],
    slots: Mapping[tuple[str, int], Slot],
    metric_ids: Sequence[str],
    *,
    as_of: datetime,
    policy: QueryPolicy,
    np_pack: Any,
    sic_resolver: Callable[[str], Any],
) -> list[dict[str, Any]]:
    dataset = served.dataset
    binding = served.binding
    generation = served.generation_id
    kinds = visible_metric_kinds(dataset.registry, as_of)
    universe = governed_duration_universe(dataset.ledger, dataset.registry)

    # Per (period_id, metric_id): either a planned request key or a reason.
    plan: dict[tuple[str, str], tuple[str, Any]] = {}
    requests: dict[str, dict[tuple[Any, ...], PeriodRequest]] = {"instant": {}, "duration": {}}
    for period in periods:
        slot = slots.get((period.family, period.rank))
        instant_request = duration_request = None
        if slot is not None:
            instant_request = PeriodRequest.instant(slot.period_of_report)
            span = duration_for_slot(universe, slot.period_of_report, period.family)
            if span is not None:
                duration_request = PeriodRequest.duration(span[0], span[1])
        for metric_id in metric_ids:
            if slot is None:
                plan[(period.period_id, metric_id)] = ("reason", REASON_SLOT_NOT_FILED)
                continue
            kind = kinds.get(metric_id)
            if kind == "instant":
                request = instant_request
            elif kind == "duration":
                request = duration_request
                if request is None:
                    plan[(period.period_id, metric_id)] = ("reason", REASON_PERIOD_NOT_IN_LEDGER)
                    continue
            else:
                plan[(period.period_id, metric_id)] = ("reason", REASON_METRIC_UNSUPPORTED)
                continue
            requests[kind].setdefault(request.key, request)
            plan[(period.period_id, metric_id)] = ("query", (kind, request.key))

    results: dict[tuple[str, tuple[Any, ...]], Any] = {}
    refused: set[tuple[str, tuple[Any, ...]]] = set()
    construction_refused = False
    if requests["instant"] or requests["duration"]:
        # Built with exactly query_service's keywords (no not-presented pack,
        # no filing packages): the manifest measures what production serves.
        try:
            engine = BitemporalMetricQueryEngine(
                ledger=dataset.ledger,
                registry=dataset.registry,
                entities=[
                    QueryEntity(
                        ticker=binding.ticker,
                        entity_id=binding.source_entity_id,
                        issuer_sic=sic_resolver(binding.source_entity_id),
                    )
                ],
                filing_metadata=dataset.filing_metadata,
                bounds=QueryBounds(
                    max_tickers=1,
                    max_metrics=HARD_MAX_METRICS,
                    max_periods=HARD_MAX_PERIODS,
                    max_cells=HARD_MAX_METRICS * QUERY_CHUNK_PERIODS,
                ),
                lineage_evidence=getattr(dataset, "lineage_evidence", ()) or (),
                source_taxonomy_uris=getattr(dataset, "source_taxonomy_uris", None),
            )
        except Exception:  # noqa: BLE001 - the kernel refused the dataset
            construction_refused = True
        if not construction_refused:
            for kind in ("instant", "duration"):
                kind_metrics = sorted(
                    metric_id for metric_id in metric_ids if kinds.get(metric_id) == kind
                )
                kind_requests = sorted(requests[kind].items(), key=lambda item: repr(item[0]))
                found, failed = _query_cells(
                    engine,
                    ticker=binding.ticker,
                    metrics=kind_metrics,
                    requests=kind_requests,
                    policy=policy,
                )
                results.update(found)
                refused |= failed

    cells: list[dict[str, Any]] = []
    for (period_id, metric_id), (action, detail) in plan.items():
        field_id = f"metric:{metric_id}"
        if action == "reason":
            cells.append(_absent(cik, period_id, field_id, detail, generation))
            continue
        _kind, key = detail
        cell = results.get((metric_id, key))
        if construction_refused or cell is None or (metric_id, key) in refused:
            cells.append(_absent(cik, period_id, field_id, REASON_KERNEL_REFUSED, generation))
            continue
        cells.append(
            map_metric_cell(
                cell,
                cik=cik,
                period_id=period_id,
                source_generation_id=generation,
                np_pack=np_pack,
            )
        )
    return cells


# ---------------------------------------------------------------------------
# Deep components
# ---------------------------------------------------------------------------


def package_role_reason(package: Any, role: str) -> str | None:
    """None when the role is stored with bytes present; else the absent reason."""
    members = package.manifest.get("members") or []
    stored_bytes = getattr(package, "members", None) or {}
    with_role = [m for m in members if isinstance(m, Mapping) and m.get("role") == role]
    if not with_role:
        return REASON_PACKAGE_ROLE_ABSENT
    stored = [m for m in with_role if m.get("state") == "stored"]
    if not stored:
        return REASON_PACKAGE_MEMBER_NOT_STORED
    for member in stored:
        data = stored_bytes.get(member.get("name"))
        if isinstance(data, (bytes, bytearray)) and len(data) > 0:
            return None
    return REASON_PACKAGE_BYTES_ABSENT


def statement_reason(package: Any, kind: str) -> str | None:
    """None when a non-refused tree of this kind has rows; else the reason."""
    trees = getattr(package, "statement_trees", None) or {}
    statements = trees.get("statements") if isinstance(trees, Mapping) else None
    matching = [
        s for s in (statements or []) if isinstance(s, Mapping) and s.get("statement_type") == kind
    ]
    if not matching:
        return REASON_STATEMENT_ABSENT
    unrefused = [s for s in matching if not s.get("refusal")]
    if not unrefused:
        return REASON_STATEMENT_REFUSED
    for statement in unrefused:
        rows = statement.get("row_count")
        if isinstance(rows, int) and not isinstance(rows, bool) and rows > 0:
            return None
    return REASON_STATEMENT_EMPTY


# ---------------------------------------------------------------------------
# Windowless deep components: the specialist pack producers and the packet
# ---------------------------------------------------------------------------


def _producer_entity_input(served: ServedIssuer, cik: str, name: str) -> EntityInput:
    """A.2: the packet ``EntityInput`` for the served generation binding."""
    return EntityInput(
        entity_id=served.binding.entity_id,
        cik=cik,
        ticker=served.binding.ticker,
        name=name,
        identity_basis=_IDENTITY_BASIS,
        source_entity_id=served.binding.source_entity_id,
    )


def _frozen_packet_request(
    served: ServedIssuer,
    thresholds: ManifestThresholds,
    slots: Mapping[tuple[str, int], Slot],
    *,
    policy: QueryPolicy,
) -> PacketQueryRequest | str:
    """B.2: the frozen packet request over the A1 slot, or its absent reason.

    The A1 fiscal start is the pack framework's primary fiscal duration
    start — the earliest start of a duration context ending exactly at the
    report date inside the annual window — so the packet's A1 window and the
    packs' primary period share one basis by construction.
    """
    period = next(
        (p for p in thresholds.deep_periods if p.period_id == "A1"),
        None,
    )
    slot = slots.get((period.family, period.rank)) if period is not None else None
    if slot is None:
        return REASON_SLOT_NOT_FILED
    opening = _primary_duration_opening_bound(
        served.dataset.ledger, date.fromisoformat(slot.period_of_report)
    )
    if opening is None:
        return REASON_PERIOD_NOT_IN_LEDGER
    try:
        return PacketQueryRequest(
            policy=policy,
            metrics=DEFAULT_REQUESTED_METRICS,
            periods=(
                PeriodRequest.duration(
                    (opening + timedelta(days=1)).isoformat(),
                    slot.period_of_report,
                    label="A1",
                ),
                PeriodRequest.instant(slot.period_of_report, label="A1_instant"),
            ),
            evaluation_mode=_PACKET_EVALUATION_MODE,
        )
    except (TypeError, ValueError):  # noqa: BLE001 - the frozen request was refused
        return REASON_PACKET_BUILDER_REFUSED


def _pack_query_mapping(
    request: PacketQueryRequest | str, policy: QueryPolicy
) -> dict[str, Any]:
    """A.3: the frozen request as the packet query object the pack CLI takes.

    A request that could not be built (no A1 slot, no qualifying duration)
    still renders the six query keys: the packs are produced over the served
    packages whatever the slot census says, and no period is invented.
    """
    if isinstance(request, PacketQueryRequest):
        return visible_query_from_request(request)
    clocks = policy.to_dict()
    return {
        "policy": clocks["selection"],
        "source_event_cutoff": clocks["source_snapshot_at"],
        "system_recorded_cutoff": clocks["recorded_at"],
        "requested_metrics": list(DEFAULT_REQUESTED_METRICS),
        "requested_periods": [],
        "evaluation_mode": _PACKET_EVALUATION_MODE,
    }


def _required_fields_missing(envelope: Mapping[str, Any], pack: str) -> list[str]:
    """A.1: required catalogue field ids the envelope did not answer valued."""
    required: list[str] = []
    for field in load_pack_schema(pack).get("fields") or ():
        if isinstance(field, Mapping) and field.get("required") is True:
            field_id = field.get("field_id")
            if isinstance(field_id, str) and field_id:
                required.append(field_id)
    rows: dict[str, list[Mapping[str, Any]]] = {}
    for row in envelope.get("fields") or ():
        if isinstance(row, Mapping) and isinstance(row.get("field_id"), str):
            rows.setdefault(row["field_id"], []).append(row)
    missing = [
        field_id
        for field_id in sorted(required)
        if not rows.get(field_id)
        or any(row.get("quality_state") != _ROW_VALUED for row in rows[field_id])
    ]
    return missing[:_MISSING_FIELD_IDS_BOUND]


def _specialist_cell(
    cik: str,
    pack: str,
    served: ServedIssuer,
    serve_generation: str,
    *,
    query: Mapping[str, Any],
    issuer_sic: str | None,
) -> dict[str, Any]:
    """A.1: one ``specialist:PKnn`` cell from the registered producer."""
    field_id = f"specialist:{pack}"
    if pack not in registered_pack_ids():
        return _absent(
            cik, WILDCARD_PERIOD, field_id, REASON_NO_PRODUCTION_PRODUCER, serve_generation
        )
    try:
        pack_input = PackInput(
            packages=tuple(served.packages),
            # EntityInput rejects an empty name, so a generation that stored
            # none falls back to the binding ticker (A.5).
            entity=asdict(
                _producer_entity_input(served, cik, served.name or served.binding.ticker)
            ),
            query=dict(query),
            issuer_sic=issuer_sic,
            sic_source=_SIC_SOURCE_RESOLVED if issuer_sic is not None else _SIC_SOURCE_UNBOUND,
            packet_id=None,
        )
        envelope = produce_pack(pack, pack_input)
    except (SpecialistPackError, ValueError, KeyError, StatementGraphError) as exc:
        cell = _absent(
            cik, WILDCARD_PERIOD, field_id, REASON_PACK_PRODUCER_REFUSED, serve_generation
        )
        # The class name alone: a message may carry paths.
        cell["producer_reason"] = type(exc).__name__[:_PRODUCER_REASON_BOUND]
        return cell
    applicability = envelope.get("applicability")
    state = applicability.get("state") if isinstance(applicability, Mapping) else None
    raw_reason = (
        applicability.get("reason") if isinstance(applicability, Mapping) else None
    )
    code = str(raw_reason or "").split(":", 1)[0]
    if not _BARE_REASON.fullmatch(code):
        code = REASON_PACK_PRODUCER_REFUSED
    if state == _APPLICABILITY_NOT_APPLICABLE:
        cell = {
            "cik": cik,
            "period_id": WILDCARD_PERIOD,
            "field_id": field_id,
            "status": STATUS_NOT_APPLICABLE,
            "reason_code": code,
            "na_basis": NA_BASIS_CLASS if code in _CLASS_NA_CODES else NA_BASIS_KERNEL,
            "source_generation_id": serve_generation,
        }
    elif state == _APPLICABILITY_NOT_EVALUABLE:
        cell = _absent(cik, WILDCARD_PERIOD, field_id, code, serve_generation)
    elif state == _APPLICABILITY_APPLICABLE:
        missing = _required_fields_missing(envelope, pack)
        if missing:
            cell = _absent(
                cik, WILDCARD_PERIOD, field_id, REASON_PACK_REQUIRED_FIELDS_ABSENT, serve_generation
            )
            cell["missing_required_fields"] = missing
        else:
            cell = _present(cik, WILDCARD_PERIOD, field_id, serve_generation)
    else:
        cell = _absent(
            cik, WILDCARD_PERIOD, field_id, REASON_PACK_PRODUCER_REFUSED, serve_generation
        )
        cell["producer_reason"] = "applicability_state_unknown"
        return cell
    # Pin which producer bytes answered (the envelope always carries both).
    cell["pack_content_sha256"] = envelope.get("pack_content_sha256")
    cell["pack_schema_digest"] = envelope.get("pack_schema_digest")
    return cell


def _packet_cell(
    cik: str,
    served: ServedIssuer,
    serve_generation: str,
    *,
    request: PacketQueryRequest | str,
    sic_resolver: Callable[[str], Any],
) -> dict[str, Any]:
    """B: the ``packet`` cell from the production packet builder."""
    if not served.name:
        return _absent(
            cik, WILDCARD_PERIOD, "packet", REASON_PACKET_IDENTITY_INCOMPLETE, serve_generation
        )
    if isinstance(request, str):
        return _absent(cik, WILDCARD_PERIOD, "packet", request, serve_generation)
    try:
        packet = build_financial_intelligence_packet_from_repo(
            entity=_producer_entity_input(served, cik, served.name),
            ledger=served.dataset.ledger,
            # The production store keys filing metadata by accession while
            # the packet assembler resolves it by occurrence id; rekey at
            # this boundary exactly as the packet service does.
            filing_metadata=occurrence_keyed_filing_metadata(
                served.dataset.ledger, served.dataset.filing_metadata
            ),
            query_request=request,
            repo_root=_REPO_ROOT,
            issuer_sic_resolver=sic_resolver,
        )
    except (ValueError, TypeError, KeyError) as exc:
        cell = _absent(
            cik, WILDCARD_PERIOD, "packet", REASON_PACKET_BUILDER_REFUSED, serve_generation
        )
        cell["producer_reason"] = type(exc).__name__[:_PRODUCER_REASON_BOUND]
        return cell
    valued = any(
        isinstance(row, Mapping) and row.get("quality_state") == _ROW_VALUED
        for row in packet.get("cells") or ()
    )
    receipts = packet.get("receipts")
    digest = (
        receipts.get("query_request_digest") if isinstance(receipts, Mapping) else None
    )
    if valued:
        cell = _present(cik, WILDCARD_PERIOD, "packet", serve_generation)
    else:
        cell = _absent(
            cik, WILDCARD_PERIOD, "packet", REASON_PACKET_NO_VALUED_CELL, serve_generation
        )
    # The packet bytes themselves never ride on the manifest; the two
    # digests pin which build answered.
    cell["packet_id"] = packet.get("packet_id")
    cell["query_request_digest"] = digest
    return cell


def _deep_component_cells(
    cik: str,
    served: ServedIssuer | None,
    serve_generation: str,
    thresholds: ManifestThresholds,
    slots: Mapping[tuple[str, int], Slot],
    *,
    policy: QueryPolicy,
    sic_resolver: Callable[[str], Any],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    # A served issuer's empty slot is unfiled; an unserved issuer has no slots.
    empty_slot = REASON_NOT_SERVED if served is None else REASON_SLOT_NOT_FILED
    for period in thresholds.deep_periods:
        slot = slots.get((period.family, period.rank)) if served is not None else None
        for role in thresholds.package_roles:
            field_id = f"package:{role}"
            reason = empty_slot if slot is None else package_role_reason(slot.package, role)
            if reason is None:
                cells.append(_present(cik, period.period_id, field_id, serve_generation))
            else:
                cells.append(_absent(cik, period.period_id, field_id, reason, serve_generation))
        for kind in thresholds.statements:
            field_id = f"statement:{kind}"
            reason = empty_slot if slot is None else statement_reason(slot.package, kind)
            if reason is None:
                cells.append(_present(cik, period.period_id, field_id, serve_generation))
            else:
                cells.append(_absent(cik, period.period_id, field_id, reason, serve_generation))
    if served is None:
        windowless: list[tuple[str, str]] = [
            (f"specialist:{pack}", REASON_NOT_SERVED)
            for pack in thresholds.specialist_packs
        ]
        if thresholds.require_packet:
            windowless.append(("packet", REASON_NOT_SERVED))
        if thresholds.require_journey:
            windowless.append(("journey", REASON_NOT_SERVED))
        for field_id, reason in windowless:
            cells.append(_absent(cik, WILDCARD_PERIOD, field_id, reason, serve_generation))
        return cells
    issuer_sic = sic_resolver(served.binding.source_entity_id)
    request = _frozen_packet_request(served, thresholds, slots, policy=policy)
    query = _pack_query_mapping(request, policy)
    for pack in thresholds.specialist_packs:
        cells.append(
            _specialist_cell(
                cik, pack, served, serve_generation, query=query, issuer_sic=issuer_sic
            )
        )
    if thresholds.require_packet:
        cells.append(
            _packet_cell(
                cik, served, serve_generation, request=request, sic_resolver=sic_resolver
            )
        )
    if thresholds.require_journey:
        cells.append(
            _absent(
                cik, WILDCARD_PERIOD, "journey", REASON_NO_PRODUCTION_PRODUCER, serve_generation
            )
        )
    return cells


# ---------------------------------------------------------------------------
# Rollups (an independent reimplementation of the proof's rules)
# ---------------------------------------------------------------------------


def _metric_scope_pass(
    index: Mapping[tuple[str, str], Mapping[str, Any]],
    periods: Sequence[SlotPeriod],
    direct: Sequence[str],
    formula: Sequence[str],
) -> tuple[bool, float | None]:
    present = applicable = 0
    failed = False
    formula_set = set(formula)
    for period in periods:
        for metric_id in sorted(set(direct) | formula_set):
            cell = index.get((period.period_id, f"metric:{metric_id}"))
            status = cell.get("status") if cell is not None else STATUS_ABSENT
            if status == STATUS_PRESENT:
                present += 1
                applicable += 1
            elif status == STATUS_NOT_APPLICABLE:
                continue
            else:
                applicable += 1
                failed = True
    rate = (present / applicable) if applicable else None
    return failed, rate


def issuer_rollup(
    cells: Sequence[Mapping[str, Any]],
    *,
    is_deep: bool,
    thresholds: ManifestThresholds,
    direct: Sequence[str],
    formula: Sequence[str],
) -> dict[str, Any]:
    counts = {STATUS_PRESENT: 0, STATUS_ABSENT: 0, STATUS_NOT_APPLICABLE: 0}
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in cells:
        counts[cell["status"]] += 1
        index[(cell["period_id"], cell["field_id"])] = cell
    core_failed, core_rate = _metric_scope_pass(
        index, thresholds.core_periods, direct, formula
    )
    rollup: dict[str, Any] = {
        "core_pass": (not core_failed)
        and thresholds.band_for_rate(core_rate) == _COMPLETE_BAND,
        "present_cells": counts[STATUS_PRESENT],
        "absent_cells": counts[STATUS_ABSENT],
        "na_cells": counts[STATUS_NOT_APPLICABLE],
    }
    if is_deep:
        deep_failed, deep_rate = _metric_scope_pass(
            index, thresholds.deep_periods, direct, formula
        )
        component_failed = False
        for period in thresholds.deep_periods:
            for field_id in [f"package:{r}" for r in thresholds.package_roles] + [
                f"statement:{k}" for k in thresholds.statements
            ]:
                cell = index.get((period.period_id, field_id))
                if cell is None or cell["status"] != STATUS_PRESENT:
                    component_failed = True
        windowless = [(f"specialist:{p}", True) for p in thresholds.specialist_packs]
        if thresholds.require_packet:
            windowless.append(("packet", False))
        if thresholds.require_journey:
            windowless.append(("journey", False))
        for field_id, allows_na in windowless:
            cell = index.get((WILDCARD_PERIOD, field_id))
            if cell is None:
                component_failed = True
            elif cell["status"] == STATUS_PRESENT:
                continue
            elif cell["status"] == STATUS_NOT_APPLICABLE and allows_na:
                continue
            else:
                component_failed = True
        rollup["deep_pass"] = (
            not deep_failed
            and not component_failed
            and thresholds.band_for_rate(deep_rate) == _COMPLETE_BAND
        )
    return rollup


# ---------------------------------------------------------------------------
# Manifest assembly
# ---------------------------------------------------------------------------


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_as_of(value: str | datetime) -> datetime:
    try:
        parsed = parse_utc(value, field_name="as_of")
    except Exception as exc:  # noqa: BLE001 - naive or malformed
        raise CoverageManifestError("as_of_invalid", "as_of must be an aware UTC timestamp") from exc
    if parsed is None:
        raise CoverageManifestError("as_of_invalid", "as_of is required")
    return parsed


def build_coverage_manifest(
    *,
    tiers_file: str | Path,
    coverage_file: str | Path,
    store_dir: str | Path,
    as_of: str | datetime,
    thresholds_file: str | Path = DEFAULT_THRESHOLDS,
    catalog_file: str | Path = DEFAULT_CATALOG,
    formulas_file: str | Path = DEFAULT_FORMULAS,
    np_pack: Any | None = None,
    sic_resolver: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Build the served-only draft coverage manifest at ``as_of``."""
    cutoff = parse_as_of(as_of)
    store_path = Path(store_dir)
    if not store_path.is_dir():
        raise CoverageManifestError("store_unavailable", f"store dir is not a directory: {store_dir}")

    tiers_bytes = _read_bytes(tiers_file, "tiers")
    coverage_bytes = _read_bytes(coverage_file, "coverage_contract")
    thresholds_bytes = _read_bytes(thresholds_file, "thresholds")
    catalog_bytes = _read_bytes(catalog_file, "catalog")
    formulas_bytes = _read_bytes(formulas_file, "formulas")

    tiers = load_tiers(tiers_bytes)
    contract = load_coverage_contract(coverage_bytes)
    thresholds = load_manifest_thresholds(thresholds_bytes)
    direct, formula = load_metric_ids(catalog_bytes, formulas_bytes)
    metric_ids = tuple(sorted(set(direct) | set(formula)))
    pack = np_pack if np_pack is not None else load_not_presented_pack()
    resolver = sic_resolver if sic_resolver is not None else partial(resolve_issuer_sic)

    store = build_production_dataset_store(store_path)
    query_provider = ProductionFinancialQueryProvider(store)
    statement_provider = ProductionFinancialStatementProvider(store)
    cutoff_text = _iso_utc(cutoff)
    policy = QueryPolicy(
        selection=QUERY_SELECTION,
        source_snapshot_at=cutoff_text,
        recorded_at=cutoff_text,
    )

    issuers: list[dict[str, Any]] = []
    all_cells: list[dict[str, Any]] = []
    served_set: list[dict[str, str]] = []
    for member in tiers.members:
        is_deep = member.tier_assigned == "deep"
        windows = thresholds.deep_periods if is_deep else thresholds.core_periods
        result = serve_issuer(
            member.cik,
            contract.get(member.cik),
            store=store,
            as_of=cutoff,
            policy=policy,
            query_provider=query_provider,
            statement_provider=statement_provider,
        )
        served = result.served
        if served is not None:
            generation = served.generation_id
            slots = select_slots(served.packages, cutoff)
            cells = _served_metric_cells(
                member.cik,
                served,
                windows,
                slots,
                metric_ids,
                as_of=cutoff,
                policy=policy,
                np_pack=pack,
                sic_resolver=resolver,
            )
            served_set.append({"cik": member.cik, "generation_id": generation})
        else:
            generation = f"{UNSERVED_GENERATION_PREFIX}{result.state}"
            slots = {}
            cells = [
                _absent(member.cik, period.period_id, f"metric:{metric_id}", REASON_NOT_SERVED, generation)
                for period in windows
                for metric_id in metric_ids
            ]
        if is_deep:
            cells.extend(
                _deep_component_cells(
                    member.cik,
                    served,
                    generation,
                    thresholds,
                    slots,
                    policy=policy,
                    sic_resolver=resolver,
                )
            )
        entry: dict[str, Any] = {
            "cik": member.cik,
            "ticker": member.ticker,
            "tier_assigned": member.tier_assigned,
            "serve_state": result.state,
        }
        if served is not None:
            entry["generation_id"] = served.generation_id
            entry["slots"] = {
                period.period_id: (
                    {
                        "accession": slots[(period.family, period.rank)].accession,
                        "period_of_report": slots[(period.family, period.rank)].period_of_report,
                    }
                    if (period.family, period.rank) in slots
                    else None
                )
                for period in windows
            }
        entry.update(
            issuer_rollup(
                cells,
                is_deep=is_deep,
                thresholds=thresholds,
                direct=direct,
                formula=formula,
            )
        )
        issuers.append(entry)
        all_cells.extend(cells)

    served_set.sort(key=lambda item: item["cik"])
    served_digest = hashlib.sha256(canonical_json(served_set).encode("utf-8")).hexdigest()
    issuers.sort(key=lambda item: item["cik"])
    all_cells.sort(key=lambda c: (c["cik"], c["period_id"], c["field_id"]))
    return {
        "schema": MANIFEST_SCHEMA,
        "draft": True,
        "attested": False,
        "basis": BASIS_SERVED_ONLY,
        "source_generation_id": f"{SERVED_SET_PREFIX}{served_digest}",
        "cutoff_at": tiers.cutoff_at,
        "recorded_at": cutoff_text,
        "header": {
            "producer": PRODUCER_ID,
            "as_of": cutoff_text,
            "query_selection": QUERY_SELECTION,
            "inputs_sha256": {
                "tiers": _sha256(tiers_bytes),
                "coverage_contract": _sha256(coverage_bytes),
                "thresholds": _sha256(thresholds_bytes),
                "metric_catalog": _sha256(catalog_bytes),
                "metric_formulas": _sha256(formulas_bytes),
            },
            "not_presented_pack": {
                "pack_id": pack.pack_id,
                "pack_version": pack.pack_version,
                "content_sha256": pack.content_sha256,
                "applied_by_kernel": False,
            },
            "metric_counts": {
                "direct": len(direct),
                "formula": len(formula),
            },
            "member_counts": {
                "core": sum(1 for m in tiers.members if m.tier_assigned == "core"),
                "deep": sum(1 for m in tiers.members if m.tier_assigned == "deep"),
                "served": len(served_set),
            },
            "served_set": served_set,
        },
        "issuers": issuers,
        "cells": all_cells,
    }


def render_manifest(manifest: Mapping[str, Any]) -> bytes:
    """Canonical JSON bytes plus a trailing newline."""
    return (canonical_json(manifest) + "\n").encode("utf-8")


__all__ = [
    "ANNUAL_FORMS",
    "INTERIM_FORMS",
    "MANIFEST_SCHEMA",
    "CoverageManifestError",
    "build_coverage_manifest",
    "issuer_rollup",
    "load_coverage_contract",
    "load_manifest_thresholds",
    "load_metric_ids",
    "load_tiers",
    "map_metric_cell",
    "package_role_reason",
    "parse_as_of",
    "render_manifest",
    "select_slots",
    "serve_issuer",
    "statement_reason",
]
