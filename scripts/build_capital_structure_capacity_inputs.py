"""Build the Capital Structure capacity inputs bundle over the served state.

SPEC_U1B §3.  This offline, fail-closed producer reads the SERVED
``state_bundle.json`` (U1a) for the issuer set, cutoff and served generation,
and the verified projection generation through the same verifier the projection
uses, then binds per issuer exactly what each nightly run can lawfully produce:

* instruments — from ``instrument_candidate_terms.parquet`` when the candidate
  compiler has materialized rows for the issuer that are available at the
  cutoff, resolved with an owner
  decisions ledger when one is admitted (never fuzzy, never invented);
* share basis — only from admitted share-count observations and corporate
  actions under the root (never from a provider, a publication chain or R2);
* financials — three balance-sheet cells (cash and cash equivalents, short-
  term investments, accounts receivable) bound point-in-time from the
  EXISTING Fundamental Forensics financial query service under the
  production dataset mode (F0b); every issuer FIF does not cover, and any
  unselected store, stays honestly unavailable;
* commitments — from the covenant-term ledger, falling back to document-term
  rows, with the quarantine twin excluded by name;
* rules — the L0 rule applicability pack as of the cutoff's date.

It publishes ONE ``capacity_inputs.json`` — one generation or nothing: a
missing generation, a missing or invalid state bundle, or any family binding
failure exits non-zero and leaves the last good bundle byte-identical.  It
never reads raw SEC objects, never performs network I/O, never touches a path
outside ``--root``, and never widens a frozen contract.

Usage:
    python -m scripts.build_capital_structure_capacity_inputs
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.covenant_terms import COVENANT_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.document_terms import DOCUMENT_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.funding import ITEM_RULES  # noqa: E402
from engine.capital_structure.instrument_candidates import INSTRUMENT_CANDIDATE_TERM_SCHEMA  # noqa: E402
from engine.capital_structure.instrument_resolution import (  # noqa: E402
    resolve_instruments,
    visible_candidate_count,
)
from engine.capital_structure.issuer_state_contracts import (  # noqa: E402
    COMPATIBLE_INPUT_SCHEMAS,
    CandidateBundle,
    CommitmentInputs,
    FinancialInputs,
    GenerationBinding,
    ResolutionInputs,
    ShareInputs,
    CorporateActionInputs,
    sha256_of,
)
from engine.capital_structure.rule_applicability import (  # noqa: E402
    build_rule_pack,
    load_rule_applicability_pack,
)
from engine.capital_structure.scenario_inputs import (  # noqa: E402
    CAPACITY_INPUTS_FILENAME,
    COMMITMENTS_FAMILY,
    FINANCIALS_FAMILY,
    INSTRUMENTS_FAMILY,
    RULES_FAMILY,
    SHARE_BASIS_FAMILY,
    CapacityInputsBundle,
    FamilyEntry,
    RulesEntry,
    ScenarioInputsError,
    validate_capacity_inputs_bundle,
)
from engine.capital_structure.share_basis import select_share_basis  # noqa: E402
from engine.capital_structure.state_bundle import validate_state_bundle  # noqa: E402
from engine.capital_structure.term_integration import CANDIDATE_FAMILY  # noqa: E402
from engine.capital_structure.verified_projection_generation import (  # noqa: E402
    read_verified_projection_generation,
)
from engine.fundamental_forensics.query_service import (  # noqa: E402
    FinancialQueryAdmissionError,
    execute_financial_query,
)
from engine.fundamental_forensics.raw_ledger import (  # noqa: E402
    decimal_text,
    parse_utc,
    utc_text,
)

STATE_BUNDLE_FILENAME = "state_bundle.json"
CANDIDATE_TERMS_FILENAME = "instrument_candidate_terms.parquet"
DECISIONS_FILENAME = "instrument_resolution_decisions.jsonl"
SHARE_OBSERVATIONS_FILENAME = "share_count_observations.jsonl"
CORPORATE_ACTIONS_FILENAME = "corporate_actions.jsonl"
COVENANT_LEDGER_FILENAME = "covenant_term_observations.parquet"
DOCUMENT_LEDGER_FILENAME = "document_term_observations.parquet"

#: The owner that adjudicates instrument identity when a decisions ledger is
#: admitted; ``none`` when no ledger exists (SPEC_U1B §3).
DECIDED_BY_LEDGER = "capital-structure-owner"
DECIDED_BY_NONE = "none"

# ---------------------------------------------------------------------------
# F0b — financials binding over the EXISTING Fundamental Forensics service
# ---------------------------------------------------------------------------

#: Dataset-mode switch owned by ``app.forensics`` (spell the literal here so
#: this producer never imports a FastAPI module; the test suite asserts the
#: two spellings stay equal).
FIF_FINANCIAL_DATASET_MODE_ENV = "FIF_FINANCIAL_DATASET_MODE"
FIF_PRODUCTION_DATASET_MODE = "production"

#: FIF metric id -> capital-structure item_kind.  The dict order is the
#: canonical query order; no other metric is ever requested (no net_debt, no
#: working capital, no derived headline).
FIF_METRIC_ITEM_KINDS = {
    "cash_and_cash_equivalents": "unrestricted_cash",
    "short_term_investments": "marketable_securities",
    "accounts_receivable_net": "receivables",
}
FINANCIAL_ITEM_SCHEMA = "capital_structure.financial_item_observation.v1"
FINANCIAL_BINDING_CONFIG = Path("config") / "capital_structure_financial_input_binding.v1.json"
FIF_COVERAGE_DIR = Path("config") / "fundamental_forensics" / "coverage"
FIF_QUERY_REQUEST_SCHEMA = "fundamental_forensics.financial_query_request/v1"

#: The published denial for an unavailable financials family is ONE closed
#: string (SPEC_U1B §2 vocabulary).  The specific internal cause is a DETAIL
#: this binder returns beside the facts and never publishes:
#:   fif_production_store_not_selected  — dataset mode is not "production"
#:   fif_dataset_unavailable            — production mode but no usable store
#:   fif_entity_not_covered             — CIK absent from the coverage contracts
#:   fif_entity_ambiguous               — two contracts bind one CIK differently
#:   fif_entity_unknown                 — FIF admits no such entity id
#:   fif_no_balance_sheet_before_as_of  — no filing was readable at the cutoff
#:   fif_query_unavailable              — the query service refused or failed
#:   fif_no_reported_cells              — the receipt carried no reportable cell
_DETAIL_STORE_NOT_SELECTED = "fif_production_store_not_selected"
_DETAIL_DATASET_UNAVAILABLE = "fif_dataset_unavailable"
_DETAIL_ENTITY_NOT_COVERED = "fif_entity_not_covered"
_DETAIL_ENTITY_AMBIGUOUS = "fif_entity_ambiguous"
_DETAIL_ENTITY_UNKNOWN = "fif_entity_unknown"
_DETAIL_NO_BALANCE_SHEET = "fif_no_balance_sheet_before_as_of"
_DETAIL_QUERY_UNAVAILABLE = "fif_query_unavailable"
_DETAIL_NO_REPORTED_CELLS = "fif_no_reported_cells"

#: ``sec:cik:<10-digit CIK>`` — the only issuer-id spelling the mapping admits.
_ISSUER_CIK_RE = re.compile(r"\Asec:cik:([0-9]{10})\Z")
_USD_UNITS = frozenset({"usd", "iso4217:usd"})
_ISO_DATE_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_ITEM_ID_BAD_CHARACTER = re.compile(r"[^A-Za-z0-9:._/-]")
#: Every availability clock a FIF provenance cell may carry
#: (``engine.fundamental_forensics.query`` provenance); a fact is available at
#: the latest one present.
_FIF_PROVENANCE_CLOCKS = (
    "accepted_at",
    "filing_metadata_available_at",
    "recorded_at",
    "mapping_available_at",
    "governance_available_at",
    "computed_at",
    "published_at",
    "source_ready_at",
    "system_ready_at",
)

_BINDING_CONCEPTS_CACHE: dict[str, str] | None = None
_COVERAGE_INDEX_CACHE: dict[str, frozenset[str]] | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _data_root() -> Path:
    from lib import config

    return config.data_dir() / "capital_structure"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write_one(payload: bytes, target: Path) -> None:
    """Replace one target atomically using a same-directory staged file.

    Copied line-for-line from ``scripts/build_capital_structure_projection.py``
    (SPEC_U1B packet: the helper is private there, so the producer carries its
    own 10-line copy rather than importing a private name).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    staged = Path(staged_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, target)
    finally:
        if staged.exists():
            staged.unlink()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ScenarioInputsError(f"{label} is required: {path} is absent")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScenarioInputsError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ScenarioInputsError(f"{label} must be a JSON object")
    return dict(value)


def _read_jsonl_records(path: Path, label: str) -> tuple[dict[str, Any], ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScenarioInputsError(f"{label} is unreadable: {exc}") from exc
    records = []
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScenarioInputsError(f"{label} line {index} is not valid JSON") from exc
        if not isinstance(value, Mapping):
            raise ScenarioInputsError(f"{label} line {index} must be a JSON object")
        records.append(dict(value))
    return tuple(records)


#: Payload indexes per (file, json_column) pair: ``(stat stamp, index)``, where
#: the stamp is ``(st_mtime_ns, st_size, st_ino)`` — a rewritten ledger is
#: re-read — and the index maps each ``issuer_id`` string to its raw payload
#: values in file order.  Rows are cached UNPARSED (lazy ``json.loads`` stays
#: with ``_issuer_rows``), and at most 8 keys are held: inserting a 9th drops
#: the oldest inserted.
_ISSUER_PAYLOAD_CACHE: dict[
    tuple[str, str], tuple[tuple[int, int, int], dict[str, tuple[Any, ...]]]
] = {}


def _issuer_payloads(path: Path, json_column: str, label: str) -> dict[str, tuple[Any, ...]]:
    """Read one (file, json_column) pair once per file version.

    Returns ``{issuer_id_string: (raw payload values in original row order)}``.
    Raw values stay unparsed, so ``_issuer_rows`` still validates and
    ``json.loads`` lazily, per row, only for the issuers actually bound.
    """
    import pandas as pd

    st = path.stat()
    stamp = (st.st_mtime_ns, st.st_size, st.st_ino)
    key = (str(path.resolve()), json_column)
    cached = _ISSUER_PAYLOAD_CACHE.get(key)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    frame = pd.read_parquet(path)
    if "issuer_id" not in frame.columns:
        raise ScenarioInputsError(f"{label} carries no issuer_id column")
    payloads = frame[json_column]  # before grouping: a missing column raises the same KeyError
    identifiers = frame["issuer_id"].astype(str)
    grouped: dict[str, list[Any]] = {}
    for issuer_key, raw in zip(identifiers.tolist(), payloads.tolist()):
        grouped.setdefault(issuer_key, []).append(raw)
    index = {issuer_key: tuple(rows) for issuer_key, rows in grouped.items()}
    _ISSUER_PAYLOAD_CACHE.pop(key, None)
    _ISSUER_PAYLOAD_CACHE[key] = (stamp, index)
    while len(_ISSUER_PAYLOAD_CACHE) > 8:
        _ISSUER_PAYLOAD_CACHE.pop(next(iter(_ISSUER_PAYLOAD_CACHE)))
    return index


def _issuer_rows(path: Path, json_column: str, issuer_id: str, label: str) -> tuple[dict[str, Any], ...]:
    raw_values = _issuer_payloads(path, json_column, label).get(issuer_id, ())
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_values):
        if not isinstance(raw, str) or not raw:
            raise ScenarioInputsError(f"{label} row {index} lacks a {json_column} payload")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScenarioInputsError(f"{label} row {index} has malformed {json_column}") from exc
        if not isinstance(value, Mapping):
            raise ScenarioInputsError(f"{label} row {index} {json_column} must be an object")
        rows.append(dict(value))
    return tuple(rows)


def _candidate_bundle(records: tuple[dict[str, Any], ...], support: str, as_of: str) -> CandidateBundle:
    return CandidateBundle(
        GenerationBinding(
            CANDIDATE_FAMILY,
            INSTRUMENT_CANDIDATE_TERM_SCHEMA,
            support,
            artifact_sha256=sha256_of(list(records)),
            as_of=as_of,
        ),
        records,
        as_of,
    )


def _bind_instruments(root: Path, issuer_id: str, as_of: str) -> FamilyEntry:
    """Bind the instruments family, or name why nothing is bound (SPEC_U1B §3)."""
    ledger_path = root / CANDIDATE_TERMS_FILENAME
    if not ledger_path.exists():
        return FamilyEntry(
            family=INSTRUMENTS_FAMILY,
            support="unavailable",
            reason_codes=("candidate_terms_not_materialized",),
        )
    records = _issuer_rows(ledger_path, "candidate_term_json", issuer_id, "instrument_candidate_terms")
    # The nightly compiles candidates after the state step, so a freshly
    # compiled candidate is stamped available after the state's cutoff.  An
    # issuer none of whose candidates is visible at the cutoff has no candidate
    # terms as of it: unavailable, never a resolver refusal.  Carried rows keep
    # their first available_at, so they bind on the next night's cutoff.  The
    # count runs every row check resolution runs, so lateness never hides a
    # tampered, malformed or incomplete row.
    if not records or not visible_candidate_count(_candidate_bundle(records, "partial", as_of), as_of):
        return FamilyEntry(
            family=INSTRUMENTS_FAMILY,
            support="unavailable",
            reason_codes=("candidate_terms_not_materialized",),
        )
    decisions_path = root / DECISIONS_FILENAME
    if decisions_path.exists():
        decisions = _issuer_decisions(
            _read_jsonl_records(decisions_path, "instrument_resolution_decisions"), issuer_id
        )
        decided_by = DECIDED_BY_LEDGER
        limits: tuple[str, ...] = ()
    else:
        decisions = ()
        decided_by = DECIDED_BY_NONE
        limits = ("decisions_ledger_absent",)
    resolution_inputs = ResolutionInputs(tuple(decisions), decided_by, as_of)
    # Mirror term_integration.CandidateIntegration.candidate_binding: the
    # candidate family binds its artifact digest and its own as_of.  Support is
    # the resolution's outcome — one deterministic re-resolve at "supported"
    # when every candidate resolved, so the published binding never overstates.
    support = "partial"
    while True:
        instrument_set = resolve_instruments(_candidate_bundle(records, support, as_of), resolution_inputs, as_of)
        if support == "partial" and not instrument_set.unresolved_candidate_ids:
            support = "supported"
            continue
        break
    entry_support = "partial" if instrument_set.unresolved_candidate_ids else "supported"
    return FamilyEntry(
        family=INSTRUMENTS_FAMILY,
        support=entry_support,
        reason_codes=limits if entry_support == "partial" else (),
        binding=GenerationBinding(
            CANDIDATE_FAMILY,
            INSTRUMENT_CANDIDATE_TERM_SCHEMA,
            entry_support,
            artifact_sha256=sha256_of(list(records)),
            as_of=as_of,
        ),
        record=instrument_set,
    )


def _issuer_decisions(
    decisions: Sequence[Mapping[str, Any]], issuer_id: str
) -> tuple[Mapping[str, Any], ...]:
    """The decisions that can bear on one issuer's resolution.

    The ledger holds every issuer's decisions, while the resolver requires
    exactly one issuer per resolution.  Only a decision naming another issuer
    is left out; a record without a usable ``issuer_id`` still reaches the
    resolver, which refuses it as the integrity fault it is.
    """
    kept = []
    for record in decisions:
        owner = record.get("issuer_id")
        if isinstance(owner, str) and owner and owner != issuer_id:
            continue
        kept.append(record)
    return tuple(kept)


def _bind_share_basis(root: Path, issuer_id: str, as_of: str) -> FamilyEntry:
    """Bind the share-basis family only from admitted files under the root."""
    share_path = root / SHARE_OBSERVATIONS_FILENAME
    actions_path = root / CORPORATE_ACTIONS_FILENAME
    if not share_path.exists():
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("share_observations_not_admitted",),
        )
    if not actions_path.exists():
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("corporate_actions_absent",),
        )
    observations = _read_jsonl_records(share_path, "share_count_observations")
    actions = _read_jsonl_records(actions_path, "corporate_actions")
    if not observations:
        return FamilyEntry(
            family=SHARE_BASIS_FAMILY,
            support="unavailable",
            reason_codes=("share_observations_not_admitted",),
        )
    accepted_share_schemas = COMPATIBLE_INPUT_SCHEMAS["share_count_observations"]
    share_schema = observations[0].get("schema")
    if share_schema not in accepted_share_schemas or any(
        row.get("schema") != share_schema for row in observations
    ):
        raise ScenarioInputsError(
            f"share_count_observations: records do not share one accepted schema ({share_schema!r})"
        )
    share_binding = GenerationBinding(
        "share_count_observations",
        share_schema,
        "partial",
        artifact_sha256=sha256_of(list(observations)),
        as_of=as_of,
    )
    action_schema = COMPATIBLE_INPUT_SCHEMAS["corporate_actions"][0]
    actions_binding = GenerationBinding(
        "corporate_actions",
        action_schema,
        "partial",
        artifact_sha256=sha256_of(list(actions)),
        as_of=as_of,
    )
    basis = select_share_basis(
        ShareInputs(share_binding, observations),
        CorporateActionInputs(actions_binding, actions),
        as_of,
    )
    support = basis.provenance.support
    return FamilyEntry(
        family=SHARE_BASIS_FAMILY,
        support=support,
        reason_codes=(),
        binding=share_binding,
        record=basis,
    )


def _normalize_clock(value: str) -> str:
    """Date-only cutoffs become midnight UTC (same law as the FIF consumers).

    Copied from ``app.integrated_answer._normalize_clock``: the FIF query
    policy admits timezone-aware ISO-8601 only, and the state bundle's
    ``as_of`` may be date-only.  A missing cutoff is never silently "now".
    """
    text = value.strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return f"{text}T00:00:00Z"
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _clock_moment(value: Any) -> datetime | None:
    """One FIF clock (metadata entry, provenance cell) as aware UTC, or None."""
    if value is None:
        return None
    try:
        return parse_utc(value, field_name="fif_clock")
    except (TypeError, ValueError):
        return None


def _binding_concepts() -> dict[str, str]:
    """XBRL concept -> FIF metric id, read from the binding config (never retyped)."""
    global _BINDING_CONCEPTS_CACHE
    if _BINDING_CONCEPTS_CACHE is None:
        payload = _read_json_object(
            _repo_root() / FINANCIAL_BINDING_CONFIG, "financial input binding config"
        )
        concepts: dict[str, str] = {}
        for item in payload.get("items") or ():
            if not isinstance(item, Mapping):
                continue
            source = item.get("source")
            if not isinstance(source, Mapping) or source.get("metric_id") not in FIF_METRIC_ITEM_KINDS:
                continue
            for concept in source.get("concepts") or ():
                concepts[str(concept)] = str(source["metric_id"])
        missing = sorted(set(FIF_METRIC_ITEM_KINDS) - set(concepts.values()))
        if missing:
            raise ScenarioInputsError(
                f"financial input binding config exposes no source concept for {missing}"
            )
        _BINDING_CONCEPTS_CACHE = concepts
    return _BINDING_CONCEPTS_CACHE


def _coverage_index() -> dict[str, frozenset[str]]:
    """CIK (10-digit) -> FIF entity ids over every shipped coverage contract.

    A row is any record carrying both ``cik`` and
    ``security_master_binding.issuer_id``.  CIKs compare as zero-padded
    10-digit strings; a CIK two contracts bind to two DIFFERENT entity ids is
    refused downstream as ambiguous, never picked.
    """
    global _COVERAGE_INDEX_CACHE
    if _COVERAGE_INDEX_CACHE is None:
        index: dict[str, set[str]] = {}

        def walk(node: Any) -> None:
            if isinstance(node, Mapping):
                cik = node.get("cik")
                binding = node.get("security_master_binding")
                if (
                    isinstance(cik, str)
                    and isinstance(binding, Mapping)
                    and isinstance(binding.get("issuer_id"), str)
                ):
                    digits = cik.strip()
                    if digits.isdigit():
                        index.setdefault(digits.zfill(10), set()).add(str(binding["issuer_id"]))
                for value in node.values():
                    walk(value)
            elif isinstance(node, (list, tuple)):
                for value in node:
                    walk(value)

        for path in sorted((_repo_root() / FIF_COVERAGE_DIR).glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ScenarioInputsError(f"FIF coverage contract is unreadable: {exc}") from exc
            walk(payload)
        _COVERAGE_INDEX_CACHE = {cik: frozenset(ids) for cik, ids in sorted(index.items())}
    return _COVERAGE_INDEX_CACHE


def _default_financial_provider() -> tuple[Any | None, str | None]:
    """Select the FIF query provider under the explicit dataset mode (F0b §2).

    ``production`` builds ``ProductionFinancialQueryProvider`` over the
    immutable dataset store and NEVER falls back to the golden corpus — no
    golden or fixture provider is reachable from production code.  Any other
    mode (unset, ``golden``, anything) selects no provider, and so does a
    store that cannot build.
    """
    if os.environ.get(FIF_FINANCIAL_DATASET_MODE_ENV) != FIF_PRODUCTION_DATASET_MODE:
        return None, _DETAIL_STORE_NOT_SELECTED
    try:
        from engine.fundamental_forensics.production_datasets import (  # noqa: PLC0415
            build_production_dataset_store,
        )

        store = build_production_dataset_store()
    except Exception:  # noqa: BLE001 - any store failure is dataset unavailability
        return None, _DETAIL_DATASET_UNAVAILABLE
    if store is None:
        return None, _DETAIL_DATASET_UNAVAILABLE
    from engine.fundamental_forensics.production_provider import (  # noqa: PLC0415
        ProductionFinancialQueryProvider,
    )

    return ProductionFinancialQueryProvider(store), None


def _filing_available_at_index(dataset: Any) -> dict[str, datetime]:
    """accession -> the filing's ``available_at``, joined without inventing fields.

    Filing metadata is accession-keyed on production datasets and
    occurrence-keyed on the admitted golden fixtures; both shapes expose
    ``accession`` and ``available_at`` per entry, which is the only join this
    binder reads.  Conflicting clocks for one accession resolve to the LATEST,
    so an event can never be selected before its filing was actually readable.
    """
    index: dict[str, datetime] = {}
    metadata = getattr(dataset, "filing_metadata", None)
    if not isinstance(metadata, Mapping):
        return index
    for entry in metadata.values():
        if isinstance(entry, Mapping):
            accession = entry.get("accession")
            available_at = entry.get("available_at")
        else:
            accession = getattr(entry, "accession", None)
            available_at = getattr(entry, "available_at", None)
        if not isinstance(accession, str) or not accession:
            continue
        moment = _clock_moment(available_at)
        if moment is None:
            continue
        previous = index.get(accession)
        index[accession] = moment if previous is None else max(previous, moment)
    return index


def _select_instant_date(
    dataset: Any, as_of_moment: datetime, concepts: Mapping[str, str]
) -> str | None:
    """The latest instant balance-sheet date provable at the cutoff (F0b §3)."""
    filing_available = _filing_available_at_index(dataset)
    events = getattr(getattr(dataset, "ledger", None), "events", None) or ()
    best: date | None = None
    for event in events:
        if concepts.get(getattr(event, "concept_qname", None)) is None:
            continue
        instant = getattr(getattr(event, "context", None), "instant", None)
        if instant is None:
            continue  # instant balance sheets only; a duration never substitutes
        filing = filing_available.get(getattr(getattr(event, "source", None), "accession", None))
        if filing is None or filing > as_of_moment:
            continue  # that filing was not readable at the cutoff
        if best is None or instant > best:
            best = instant
    return best.isoformat() if best is not None else None


def _facts_from_receipt(
    result: Any, entity_id: str, as_of_moment: datetime
) -> tuple[tuple[dict[str, Any], ...], str, str | None]:
    """Metric-matrix receipt cells -> financial_item_observation facts (F0b §5).

    A receipt that does not parse exactly as the service publishes it is
    query unavailability, never a guessed fact; a cell that is not a reported
    value emits nothing at all (absence, never a zero).
    """
    envelope = result.envelope if isinstance(result.envelope, Mapping) else None
    receipt = envelope.get("receipt") if isinstance(envelope, Mapping) else None
    if not isinstance(receipt, Mapping):
        return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
    root_ids = {cell for cell in (receipt.get("root_cell_ids") or ()) if isinstance(cell, str)}
    nodes = receipt.get("nodes")
    if not isinstance(nodes, (list, tuple)):
        return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
    facts: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, Mapping) or node.get("cell_id") not in root_ids:
            continue  # a dependency node, not a requested cell
        metric_id = node.get("metric_id")
        if metric_id not in FIF_METRIC_ITEM_KINDS:
            return (), "unknown", _DETAIL_QUERY_UNAVAILABLE  # an answer to a metric never asked
        period = node.get("period")
        provenance = node.get("provenance")
        if not isinstance(period, Mapping) or period.get("kind") != "instant":
            return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
        if not isinstance(provenance, Mapping):
            return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
        period_end = period.get("end")
        if not isinstance(period_end, str) or not _ISO_DATE_RE.fullmatch(period_end):
            return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
        state = node.get("state")
        if state in ("missing", "not_evaluable", "not_applicable"):
            continue  # absence is absence: no fact, never a zero
        if state != "value":
            return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
        unit = node.get("unit")
        unit_text = str(unit).strip().lower() if isinstance(unit, str) else ""
        if unit_text in _USD_UNITS:
            try:
                value_text = decimal_text(node.get("value"))
            except (TypeError, ValueError, ArithmeticError):
                return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
            if value_text is None:
                return (), "unknown", _DETAIL_QUERY_UNAVAILABLE
            amount = {"value": value_text, "unit": "usd", "status": "known"}
        else:
            # A cell the owner reported outside USD is carried unknown in its
            # own unit; funding excludes it rather than converting (F0b §5).
            amount = {"value": None, "unit": unit_text, "status": "unknown"}
        # A cell is knowable only once EVERY clock it depends on has passed, so
        # its availability is the LATEST present clock (FIF validates
        # ``system_ready_at`` as the max of its prerequisites), never the first.
        clocks = [
            moment
            for moment in (
                _clock_moment(provenance.get(name)) for name in _FIF_PROVENANCE_CLOCKS
            )
            if moment is not None
        ]
        moment = max(clocks) if clocks else None
        if moment is None or moment > as_of_moment:
            continue  # no provable availability, or defence in depth past the cutoff
        filed = provenance.get("filed_at")
        item_kind = FIF_METRIC_ITEM_KINDS[metric_id]
        item_id = _ITEM_ID_BAD_CHARACTER.sub("-", f"fif:{metric_id}:{entity_id}:{period_end}")
        facts.append(
            {
                "schema": FINANCIAL_ITEM_SCHEMA,
                "item_id": item_id,
                "item_kind": item_kind,
                "availability": ITEM_RULES[item_kind]["availability"],
                "amount": amount,
                "measured_at": period_end,
                "period_start": None,
                "period_end": None,
                "due_date": None,
                "gross_net": "not_applicable",
                "condition": None,
                "source": {
                    "owner": "fundamental_forensics",
                    "metric_id": metric_id,
                    "term_name": None,
                    "receipt_sha256": result.sha256,
                    "accession": (
                        provenance.get("accession")
                        if isinstance(provenance.get("accession"), str)
                        else None
                    ),
                    "filed": (
                        filed
                        if isinstance(filed, str) and _ISO_DATE_RE.fullmatch(filed)
                        else None
                    ),
                },
                "available_at": utc_text(moment),
            }
        )
    if not facts:
        return (), "unknown", _DETAIL_NO_REPORTED_CELLS
    facts.sort(key=lambda fact: fact["item_id"])
    cash_basis = (
        "unrestricted_cash"
        if any(
            fact["item_kind"] == "unrestricted_cash" and fact["amount"]["status"] == "known"
            for fact in facts
        )
        else "unknown"
    )
    return tuple(facts), cash_basis, None


def _resolve_financial_facts(
    issuer_id: str,
    as_of: str,
    *,
    provider: Any | None,
    provider_detail: str | None = None,
    entity_resolver: Callable[[str], str | None] | None = None,
) -> tuple[tuple[dict[str, Any], ...], str, str | None]:
    """(facts, cash_basis, detail); detail is None exactly when facts bound.

    The published reason vocabulary is closed (SPEC_U1B §2), so EVERY
    unavailable path returns the same published denial upstream and this
    binder keeps the specific internal cause as ``detail`` for tests and
    diagnosis.  Nothing on a per-issuer path ever raises out of here; a
    malformed cutoff or a drifted binding config is a build defect and
    aborts the build instead of hiding as per-issuer unavailability.
    """
    if provider is None:
        return (), "unknown", provider_detail or _DETAIL_STORE_NOT_SELECTED
    try:
        as_of_moment = parse_utc(_normalize_clock(as_of), field_name="as_of")
    except (TypeError, ValueError):
        raise ScenarioInputsError(
            f"financials binder: as_of {as_of!r} is not an ISO-8601 instant"
        ) from None
    concepts = _binding_concepts()

    # §1 — entity mapping: CS issuer -> FIF entity id over the shipped
    # coverage contracts (or a test-injected resolver).  No mapping is
    # unavailability, never a guess; two bindings are ambiguity, never a pick.
    if entity_resolver is not None:
        entity_id = entity_resolver(issuer_id)
        if not entity_id:
            return (), "unknown", _DETAIL_ENTITY_NOT_COVERED
        entity_id = str(entity_id)
    else:
        match = _ISSUER_CIK_RE.fullmatch(issuer_id)
        entity_ids = _coverage_index().get(match.group(1)) if match else frozenset()
        if not entity_ids:
            return (), "unknown", _DETAIL_ENTITY_NOT_COVERED
        if len(entity_ids) != 1:
            return (), "unknown", _DETAIL_ENTITY_AMBIGUOUS
        entity_id = next(iter(entity_ids))

    # §3 — resolve the dataset, then pick ONE instant balance-sheet date that
    # is provable at the cutoff.  Admission failures and provider failures are
    # distinct details; neither leaks a payload.
    try:
        dataset = provider.resolve(entity_id)
    except FinancialQueryAdmissionError:
        return (), "unknown", _DETAIL_ENTITY_UNKNOWN
    except Exception:  # noqa: BLE001 - FinancialQueryUnavailableError and every other failure
        return (), "unknown", _DETAIL_DATASET_UNAVAILABLE
    try:
        period_end = _select_instant_date(dataset, as_of_moment, concepts)
    except Exception:  # noqa: BLE001 - a damaged ledger is dataset unavailability
        return (), "unknown", _DETAIL_DATASET_UNAVAILABLE
    if period_end is None:
        return (), "unknown", _DETAIL_NO_BALANCE_SHEET

    # §4 — one query per covered issuer over exactly the three bound metrics.
    clock = _normalize_clock(as_of)
    request = {
        "schema": FIF_QUERY_REQUEST_SCHEMA,
        "entity_id": entity_id,
        "policy": {
            "selection": "latest_known_as_of",
            "source_snapshot_at": clock,
            "recorded_at": clock,
        },
        "metric_ids": list(FIF_METRIC_ITEM_KINDS),
        "periods": [{"kind": "instant", "start": None, "end": period_end, "label": period_end}],
    }
    body = json.dumps(request, separators=(",", ":")).encode("utf-8")
    try:
        result = execute_financial_query(body=body, provider=provider)
    except Exception:  # noqa: BLE001 - admission, unavailability and kernel failures alike
        return (), "unknown", _DETAIL_QUERY_UNAVAILABLE

    return _facts_from_receipt(result, entity_id, as_of_moment)


def _bind_financials(
    issuer_id: str,
    as_of: str,
    *,
    provider: Any | None = None,
    entity_resolver: Callable[[str], str | None] | None = None,
    provider_detail: str | None = None,
    detail_tally: dict[str, int] | None = None,
) -> FamilyEntry:
    """Bind the financials family from FIF, or name why nothing is bound (F0b).

    Unavailable financials carry the closed published reason alone; a partial
    bind carries every reportable cell as a
    ``capital_structure.financial_item_observation.v1`` fact whose digest and
    cutoff the binding pins.  ``detail_tally`` (the build's) counts each
    internal cause for the run summary; the bundle never carries it.
    """
    facts, cash_basis, detail = _resolve_financial_facts(
        issuer_id,
        as_of,
        provider=provider,
        provider_detail=provider_detail,
        entity_resolver=entity_resolver,
    )
    if detail is not None:
        if detail_tally is not None:
            detail_tally[detail] = detail_tally.get(detail, 0) + 1
        return FamilyEntry(
            family=FINANCIALS_FAMILY,
            support="unavailable",
            reason_codes=("companyfacts_snapshot_unavailable",),
        )
    binding = GenerationBinding(
        "financials",
        FINANCIAL_ITEM_SCHEMA,
        "partial",
        artifact_sha256=sha256_of(list(facts)),
        as_of=as_of,
    )
    return FamilyEntry(
        family=FINANCIALS_FAMILY,
        support="partial",
        reason_codes=(),
        binding=binding,
        record=FinancialInputs(binding, facts, cash_basis),
    )


def _bind_commitments(
    root: Path, issuer_id: str, as_of: str, source_generation_id: str
) -> FamilyEntry:
    """Bind commitments from covenant rows, falling back to document rows."""
    covenant_path = root / COVENANT_LEDGER_FILENAME
    records: tuple[dict[str, Any], ...] = ()
    family: str | None = None
    if covenant_path.exists():
        records = _issuer_rows(
            covenant_path, "observation_json", issuer_id, "covenant_term_observations"
        )
        family = "covenant_terms"
    if not records:
        document_path = root / DOCUMENT_LEDGER_FILENAME
        if document_path.exists():
            records = _issuer_rows(
                document_path, "observation_json", issuer_id, "document_term_observations"
            )
            family = "document_terms"
    if not records or family is None:
        return FamilyEntry(
            family=COMMITMENTS_FAMILY,
            support="unavailable",
            reason_codes=("commitment_rows_absent",),
        )
    schema = COVENANT_TERM_SCHEMA if family == "covenant_terms" else DOCUMENT_TERM_SCHEMA
    binding = GenerationBinding(
        family,
        schema,
        "partial",
        generation_id=source_generation_id,
        artifact_sha256=sha256_of(list(records)),
        as_of=as_of,
    )
    return FamilyEntry(
        family=COMMITMENTS_FAMILY,
        support="partial",
        reason_codes=(),
        binding=binding,
        record=CommitmentInputs(binding, records),
    )


def _bind_rules(as_of_date: str) -> RulesEntry:
    """The L0 pack as of the cutoff's date; ``None`` is typed unavailability."""
    built, unknowns, _conditions, _excluded = build_rule_pack(load_rule_applicability_pack(), as_of_date)
    if built is None:
        return RulesEntry(
            support="unavailable",
            reason_codes=("no_rule_governs_as_of",),
            unknowns=tuple(unknowns),
        )
    return RulesEntry(support="supported", unknowns=tuple(unknowns), record=built)


def build_from_disk(
    *,
    root: Path | str | None = None,
    generated_at: str | None = None,
    out_path: Path | None = None,
    financial_provider: Any | None = None,
) -> dict[str, Any]:
    """Verify the generation and the served state, and publish one bundle — or nothing.

    ``financial_provider`` injects a FIF query provider (tests); ``None``
    means the dataset-mode default, selected ONCE per build and passed down.
    """
    root = Path(root) if root is not None else _data_root()
    target = Path(out_path) if out_path is not None else (root / CAPACITY_INPUTS_FILENAME)

    state_bundle = _read_json_object(root / STATE_BUNDLE_FILENAME, "state bundle")
    try:
        validate_state_bundle(state_bundle)
    except ValueError as exc:
        raise ScenarioInputsError(f"state bundle is invalid: {exc}") from exc

    generation = read_verified_projection_generation(root)
    telemetry = generation.telemetry
    if telemetry.get("status") == "missing" or not telemetry.get("generation_id"):
        raise ScenarioInputsError(
            "no verified capital-structure generation: the producer writes nothing over a missing generation"
        )
    source_generation_id = str(telemetry["generation_id"])
    as_of = str(state_bundle["as_of"])
    state_generation_id = str(state_bundle["generation_id"])
    as_of_date = as_of[:10]

    if financial_provider is None:
        provider, provider_detail = _default_financial_provider()
    else:
        provider, provider_detail = financial_provider, None

    issuers: dict[str, dict[str, FamilyEntry]] = {}
    # Internal causes behind the one published financials denial; logged in
    # the summary for diagnosis, never written into the bundle.
    financials_details: dict[str, int] = {}
    for record in state_bundle.get("issuers") or ():
        issuer_id = str(record["request"]["issuer_id"])
        issuers[issuer_id] = {
            INSTRUMENTS_FAMILY: _bind_instruments(root, issuer_id, as_of),
            SHARE_BASIS_FAMILY: _bind_share_basis(root, issuer_id, as_of),
            FINANCIALS_FAMILY: _bind_financials(
                issuer_id,
                as_of,
                provider=provider,
                provider_detail=provider_detail,
                detail_tally=financials_details,
            ),
            COMMITMENTS_FAMILY: _bind_commitments(root, issuer_id, as_of, source_generation_id),
        }
    rules = _bind_rules(as_of_date)

    bundle = CapacityInputsBundle(
        as_of=as_of,
        generated_at=generated_at or _now_iso(),
        state_generation_id=state_generation_id,
        source_generation_id=source_generation_id,
        rules=rules,
        issuers=issuers,
    )
    record = bundle.as_record()
    # Validate the exact bytes that will be published, never the in-memory form.
    payload = (json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    validate_capacity_inputs_bundle(json.loads(payload.decode("utf-8")))
    _atomic_write_one(payload, target)
    tallies = record["coverage"]["families"]
    return {
        "status": "ok",
        "generation_id": record["generation_id"],
        "state_generation_id": state_generation_id,
        "source_generation_id": source_generation_id,
        "as_of": as_of,
        "issuers": record["coverage"]["issuer_count"],
        "families": {family: tally["unavailable"] for family, tally in tallies.items()},
        "financials_details": dict(sorted(financials_details.items())),
        "out_path": str(target),
        "byte_length": len(payload),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="capital-structure data root (default data/capital_structure)")
    parser.add_argument("--out-path", type=Path, default=None)
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args(argv)
    try:
        summary = build_from_disk(root=args.root, generated_at=args.generated_at, out_path=args.out_path)
    except (ScenarioInputsError, ValueError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
