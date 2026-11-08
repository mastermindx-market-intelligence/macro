"""Deterministic, bounded bitemporal metric queries over the raw fact ledger.

This module is intentionally a query *kernel*, not an API handler or a storage
adapter.  It composes three immutable contracts:

* :mod:`raw_ledger` owns individual source occurrences and their revision
  history;
* :mod:`metric_registry` is the only authority for concept aliases and
  formulae; and
* :mod:`periods` owns typed period normalization.

The raw ledger has a one-clock selector.  A production query, however, must
apply both a source-event and a system/recorded cutoff at once.  The small
adapter below therefore selects a duplicate group only when the group and its
entire revision ancestry are available on *both* clocks.  It deliberately does
not reinterpret an unavailable mapping, a withdrawn fact, an ambiguous
duplicate, or an issuer extension as a numeric value.

There is no database or HTTP dependency here.  A caller supplies a bounded
``RawFactLedger``, a validated ``MetricRegistry``, entity identities, and (when
needed) an accession metadata adapter that can attest filing forms/dates.
"""
from __future__ import annotations

import ast
import csv
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import (
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    Subnormal,
    Underflow,
    localcontext,
)
from enum import Enum
import hashlib
import io
from itertools import islice
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol, Sequence
from zoneinfo import ZoneInfo

from .metric_registry import (
    ConceptAlias,
    FormulaRule,
    GovernanceBundle,
    MappingRule,
    MetricContract,
    MetricRegistry,
    formula_signed_terms,
    qualify_metric,
)
from .periods import CalendarKind, PeriodKind, TypedPeriod
from .lineage_evidence import (
    CONFIRMATION_CHAIN_RULE_VERSION,
    MAX_LINEAGE_RECEIPTS,
    REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE,
    REFUSAL_MISSING_OCCURRENCE,
    LineageEvidenceError,
    LineageEvidenceReceipt,
    _approved_taxonomy_uri,
    _chain_accepted_by_accession,
    _freeze_evidence,
    _positive_evidence_payload,
    evaluate_confirmation,
    receipt_envelope_refusal,
)
from .raw_ledger import (
    FactEventType,
    FactContext,
    FactUnit,
    HARD_MAX_RAW_LEDGER_EVENTS,
    MAX_DECIMAL_SOURCE_CHARS,
    MAX_XBRL_ACCURACY_MAGNITUDE,
    RawFactLedger,
    RawFactOccurrence,
    SourceIdentity,
    TemporalClocks,
    _canonical_duplicate_representative,
    canonical_json,
    decimal_text,
    parse_utc,
    stable_id,
    utc_text,
)
from .detectors import issuer_class_for_sic
from .not_presented import (
    NA_BASIS_NOT_PRESENTED_ITEM,
    NOT_PRESENTED_REASON,
    NotPresentedError,
    NotPresentedEvidence,
    NotPresentedPack,
    evaluate_not_presented_package,
    package_linkbases,
    verify_not_presented_evidence,
)

# An empty projection for the overwhelmingly common no-evidence path, so a
# FIF-3A3 query allocates nothing new.
_EMPTY_ROOT_MAP: Mapping[str, str] = MappingProxyType({})
_EMPTY_PACKAGE_MAP: Mapping[str, Any] = MappingProxyType({})

# Per-engine memo ceiling for confirmation-unified roots.
MAX_EFFECTIVE_ROOT_CACHE_ENTRIES = 4096

# Revalidation refusal reasons for a receipt that is simply not applicable
# under the query policy's clocks.  Engine-level diagnostics only: they
# classify why an admitted receipt is not applied under a policy and never
# enter a response body.  Every other refusal vocabulary used when
# re-proving a receipt comes from ``lineage_evidence``; in particular any
# mismatch between the receipt's positive evidence and the current eligible
# ledger is classified ``REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE``.
REFUSAL_RECEIPT_NOT_YET_SOURCE_VISIBLE = "receipt_not_yet_source_visible"
REFUSAL_RECEIPT_NOT_YET_SYSTEM_AVAILABLE = "receipt_not_yet_system_available"
REFUSAL_OCCURRENCE_NOT_TEMPORALLY_ELIGIBLE = "occurrence_not_temporally_eligible"


QUERY_SCHEMA = "fundamental_forensics.metric_query/v1"
CELL_RECEIPT_SCHEMA = "fundamental_forensics.metric_cell_receipt/v1"
REGISTRY_PROJECTION_SCHEMA = "fundamental_forensics.registry_projection/v1"
REGISTRY_PROJECTION_VERSION = "cutoff-projection-v1"
FILING_METADATA_SCHEMA = "fundamental_forensics.filing_metadata/v1"

# The first synchronous peer-grid contract is deliberately small.  A caller
# that needs a bulk history/export job must use a durable worker lane rather
# than accidentally turn a request path into an unbounded scan.
HARD_MAX_TICKERS = 50
HARD_MAX_ENTITY_BINDINGS = HARD_MAX_TICKERS
HARD_MAX_METRICS = 50
HARD_MAX_PERIODS = 32
HARD_MAX_CELLS = 10_000
HARD_MAX_VISIBLE_SOURCE_EVENTS_PER_CELL = 10_000
HARD_MAX_PROVENANCE_IDS = 10_000
HARD_MAX_DEPENDENCY_RECEIPTS = HARD_MAX_METRICS
HARD_MAX_RECEIPT_NODES = HARD_MAX_DEPENDENCY_RECEIPTS
HARD_MAX_RECEIPT_EDGES = HARD_MAX_DEPENDENCY_RECEIPTS
HARD_MAX_RECEIPT_DEPTH = HARD_MAX_DEPENDENCY_RECEIPTS
HARD_MAX_MATRIX_NODES = 50_000
HARD_MAX_MATRIX_EDGES = 200_000
HARD_MAX_RECEIPT_WIRE_BYTES = 128 * 1024 * 1024
HARD_MAX_RECEIPT_CONTAINER_ITEMS = HARD_MAX_MATRIX_NODES
MAX_QUERY_TEXT_CHARS = 4096
# Filing packages admitted beside a not-presented rule pack (step 5 b2).
HARD_MAX_NOT_PRESENTED_PACKAGES = 10_000

# A selected occurrence can prove that the normalized value is internally
# consistent with one immutable source artifact.  It cannot, without the
# external append-only ledger, prove that no higher-precedence occurrence was
# eligible or that an absence result was exhaustive.
RECEIPT_PROOF_SCOPE = "selected_occurrence_consistency_only"
RECEIPT_SELECTION_PROOF = "external_immutable_ledger_required"

# Formula arithmetic is deliberately owned by this kernel rather than by the
# process-global Decimal context. The contract is IEEE decimal128-shaped:
# 34 significant digits, round-half-even, exponent range -6143..6144, and
# traps for exceptional/non-representable results. Inexact division is a
# normal deterministic rounding operation under this contract; it is not a
# reason to discard a governed formula result.
FORMULA_DECIMAL_PRECISION = 34
FORMULA_DECIMAL_EMIN = -6143
FORMULA_DECIMAL_EMAX = 6144
MAX_DECIMAL_COEFFICIENT_DIGITS = 8192
MAX_DECIMAL_SERIALIZED_CHARS = 8192
SOURCE_COMPARISON_PRECISION = 2 * MAX_DECIMAL_SOURCE_CHARS + 8
SOURCE_COMPARISON_EXPONENT_LIMIT = (
    2 * MAX_DECIMAL_SOURCE_CHARS + 2 * MAX_XBRL_ACCURACY_MAGNITUDE + 8
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class QueryError(ValueError):
    """Base class for safe, client-actionable query errors."""


class QueryValidationError(QueryError):
    """The query shape or a supplied selector is malformed."""


class QueryBoundsError(QueryValidationError):
    """The request exceeds its explicitly declared synchronous bounds."""


class UnsupportedMetricError(QueryValidationError):
    """The metric is not in the immutable governed registry."""


class UnsupportedConceptError(QueryValidationError):
    """The concept is not a governed registry concept for this engine."""


class BitemporalPolicy(str, Enum):
    """The three externally meaningful raw-vintage policies.

    ``AS_REPORTED`` means the original source group, never a later amended
    value. ``LATEST_KNOWN_AS_OF`` selects the newest eligible source vintage
    of any immutable event type. ``LATEST_RESTATED`` is intentionally *not*
    an alias: it selects only an eligible, explicitly typed reported revision
    (amendment, comparative recast, restatement, source correction, or
    withdrawal). If no such vintage is known at both cutoffs, it is missing
    rather than silently returning the latest ordinary filing or a
    parser/mapping correction.

    Formula outputs are calculated on demand from the selected raw vintages;
    a formula query never pretends to be a separately materialized historical
    occurrence.
    """

    AS_REPORTED = "as_reported"
    LATEST_KNOWN_AS_OF = "latest_known_as_of"
    LATEST_RESTATED = "latest_restated"


# A descriptive compatibility spelling for callers that prefer the longer
# noun.  It remains an Enum, while QueryPolicy below carries the two cutoffs.
MetricQueryPolicy = BitemporalPolicy


class CellState(str, Enum):
    """A cell has a value, lacks evidence, is unsafe to evaluate, or is refused.

    ``NOT_APPLICABLE`` is the metric-qualification refusal state (S1-b): the
    issuer class or a declared denominator places this metric outside the
    governed contract's applicability.  It is unreachable under the
    constraint-free production catalog, which declares no applicability or
    denominator constraints.
    """

    VALUE = "value"
    MISSING = "missing"
    NOT_EVALUABLE = "not_evaluable"
    NOT_APPLICABLE = "not_applicable"


MetricCellState = CellState


class ProvenanceKind(str, Enum):
    """Whether a receipt describes absence, a raw fact, or an on-demand formula."""

    OPAQUE = "opaque"
    DIRECT = "direct"
    FORMULA = "formula"


class EvaluationPolicy(str, Enum):
    """How a normalized answer was produced from cutoff-visible artifacts."""

    ON_DEMAND_CUTOFF_PROJECTION = "on_demand_cutoff_projection"


_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,15}$")


def _require_text(value: Any, *, field_name: str) -> str:
    if isinstance(value, float):
        raise QueryValidationError(f"{field_name} cannot be a binary float")
    text = str(value or "").strip()
    if not text:
        raise QueryValidationError(f"{field_name} is required")
    if len(text) > MAX_QUERY_TEXT_CHARS:
        raise QueryValidationError(f"{field_name} exceeds the text safety limit")
    return text


def _required_utc(value: datetime | str | None, *, field_name: str) -> datetime:
    try:
        parsed = parse_utc(value, field_name=field_name)
    except ValueError as exc:
        raise QueryValidationError(str(exc)) from exc
    if parsed is None:
        raise QueryValidationError(f"{field_name} is required")
    return parsed


def _date_value(value: date | datetime | str | None, *, field_name: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise QueryValidationError(f"invalid {field_name}: {value!r}") from exc


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


_EDGAR_TIMEZONE = ZoneInfo("America/New_York")
_EDGAR_FILING_CUTOFF = time(17, 30)
_EDGAR_MAX_WEEKDAY_ROLL = 3


def _latest_edgar_filed_date(accepted_at: datetime) -> date:
    """Return the latest SEC filing date consistent with an EDGAR acceptance.

    Regulation S-T Rule 13(a): a submission accepted after 5:30 p.m. Eastern
    time, or on a non-business day, is deemed filed on the next business day,
    so its filing date legitimately follows the acceptance date (in UTC and
    in Eastern time).  Within filing hours the filing date may not follow the
    Eastern acceptance date.  Federal holidays and unscheduled EDGAR closures
    are not modelled: an out-of-hours acceptance may roll to at most the third
    weekday after its Eastern date (the next business day past two intervening
    weekday closures).  ``filed_at`` never gates availability; this bound only
    keeps filing metadata consistent with the occurrence it describes.
    """
    eastern = accepted_at.astimezone(_EDGAR_TIMEZONE)
    bound = eastern.date()
    if bound.weekday() < 5 and eastern.time() < _EDGAR_FILING_CUTOFF:
        return bound
    rolled = 0
    while rolled < _EDGAR_MAX_WEEKDAY_ROLL:
        bound += timedelta(days=1)
        if bound.weekday() < 5:
            rolled += 1
    return bound


def _positive_int(value: int, *, field_name: str, ceiling: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise QueryBoundsError(f"{field_name} must be a positive integer")
    if value > ceiling:
        raise QueryBoundsError(f"{field_name} exceeds hard safety ceiling {ceiling}")
    return value


def _formula_context() -> Context:
    """Return a fresh, fixed Decimal context for every formula evaluation.

    Returning a new context prevents an importer from mutating a module-level
    ``Context`` object and thereby changing a query hash or a cell result.
    """
    context = Context(
        prec=FORMULA_DECIMAL_PRECISION,
        rounding=ROUND_HALF_EVEN,
        Emin=FORMULA_DECIMAL_EMIN,
        Emax=FORMULA_DECIMAL_EMAX,
        capitals=1,
        clamp=0,
    )
    for signal in (InvalidOperation, DivisionByZero, Overflow, Underflow, Subnormal):
        context.traps[signal] = True
    return context


def _source_comparison_context() -> Context:
    """Exact bounded context for raw XBRL duplicate interval comparison.

    Formula decimal128 rounding is intentionally unsuitable here: source
    coefficients can exceed 34 digits and XBRL accuracy exponents extend to
    10,000.  The raw-ledger token and accuracy ceilings provide a separate,
    finite context large enough to preserve those values exactly.
    """
    context = Context(
        prec=SOURCE_COMPARISON_PRECISION,
        rounding=ROUND_HALF_EVEN,
        Emin=-SOURCE_COMPARISON_EXPONENT_LIMIT,
        Emax=SOURCE_COMPARISON_EXPONENT_LIMIT,
        capitals=1,
        clamp=0,
    )
    for signal in (InvalidOperation, DivisionByZero, Overflow, Underflow, Subnormal):
        context.traps[signal] = True
    return context


def _bounded_decimal(value: Decimal | str | int, *, field_name: str) -> Decimal:
    """Normalize a finite Decimal without permitting unbounded wire values."""
    if isinstance(value, float):
        raise QueryValidationError(f"{field_name} cannot be a binary float")
    if isinstance(value, str) and len(value) > MAX_DECIMAL_SERIALIZED_CHARS:
        raise QueryValidationError(f"{field_name} exceeds the decimal text safety limit")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (DecimalException, TypeError, ValueError) as exc:
        raise QueryValidationError(f"invalid {field_name}: {value!r}") from exc
    if not parsed.is_finite():
        raise QueryValidationError(f"{field_name} must be finite")
    digits = parsed.as_tuple().digits
    if len(digits) > MAX_DECIMAL_COEFFICIENT_DIGITS:
        raise QueryValidationError(f"{field_name} exceeds the decimal coefficient safety limit")
    if parsed != 0 and not FORMULA_DECIMAL_EMIN <= parsed.adjusted() <= FORMULA_DECIMAL_EMAX:
        raise QueryValidationError(f"{field_name} exponent is outside the query decimal contract")
    # This formatting is bounded by the checks above and protects the stable
    # cell ID/export path from an attacker-controlled million-character zero
    # expansion such as Decimal('1e-1000000').
    serialized = decimal_text(parsed)
    if serialized is None or len(serialized) > MAX_DECIMAL_SERIALIZED_CHARS:
        raise QueryValidationError(f"{field_name} exceeds the decimal serialization safety limit")
    return parsed


def _optional_text(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise QueryValidationError(f"{field_name} must be text when supplied")
    return _require_text(value, field_name=field_name)


def _optional_utc(value: Any, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, (datetime, str)):
        raise QueryValidationError(f"{field_name} must be an aware datetime or UTC text")
    try:
        return parse_utc(value, field_name=field_name)
    except ValueError as exc:
        raise QueryValidationError(str(exc)) from exc


def _bounded_collection(
    value: Any,
    *,
    field_name: str,
    maximum: int,
) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise QueryValidationError(f"{field_name} must be a bounded collection")
    try:
        count = len(value)
    except (TypeError, AttributeError):
        count = None
    except QueryError:
        raise
    except Exception as exc:
        raise QueryValidationError(f"{field_name} has an invalid length contract") from exc
    if count is not None and count > maximum:
        raise QueryBoundsError(f"{field_name} exceeds the item safety limit {maximum}")
    try:
        items = tuple(islice(iter(value), maximum + 1))
    except Exception as exc:
        raise QueryValidationError(f"{field_name} must be a bounded collection") from exc
    if len(items) > maximum:
        raise QueryBoundsError(f"{field_name} exceeds the item safety limit {maximum}")
    return items


def _canonical_text_tuple(
    value: Any,
    *,
    field_name: str,
    maximum: int = HARD_MAX_PROVENANCE_IDS,
) -> tuple[str, ...]:
    items = _bounded_collection(value, field_name=field_name, maximum=maximum)
    return tuple(sorted({_require_text(item, field_name=field_name) for item in items}))


def _ordered_text_tuple(
    value: Any,
    *,
    field_name: str,
    maximum: int = HARD_MAX_DEPENDENCY_RECEIPTS,
) -> tuple[str, ...]:
    """Freeze an order-sensitive identifier sequence without deduplicating it."""
    items = tuple(
        _require_text(item, field_name=field_name)
        for item in _bounded_collection(value, field_name=field_name, maximum=maximum)
    )
    if len(set(items)) != len(items):
        raise QueryValidationError(f"{field_name} cannot contain duplicates")
    return items


def _strict_wire_mapping(
    value: Any,
    *,
    field_name: str,
    allowed: frozenset[str],
    required: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Read a small wire object without trusting a hostile Mapping iterator."""
    if not isinstance(value, Mapping):
        raise QueryValidationError(f"{field_name} must be an object")
    pairs = _bounded_collection(
        value.items(),
        field_name=field_name,
        maximum=len(allowed),
    )
    out: dict[str, Any] = {}
    for key, item in pairs:
        normalized_key = _require_text(key, field_name=f"{field_name} field")
        if normalized_key in out:
            raise QueryValidationError(f"{field_name} contains duplicate field {normalized_key}")
        out[normalized_key] = item
    unknown = set(out) - set(allowed)
    if unknown:
        raise QueryValidationError(
            f"{field_name} contains unsupported field(s): {', '.join(sorted(unknown))}"
        )
    missing = set(required or ()) - set(out)
    if missing:
        raise QueryValidationError(
            f"{field_name} is missing required field(s): {', '.join(sorted(missing))}"
        )
    return out


def _wire_list(
    value: Any,
    *,
    field_name: str,
    maximum: int,
) -> tuple[Any, ...]:
    """Admit only a real decoded-JSON list, then enforce ``limit + 1``."""
    if type(value) is not list:
        raise QueryValidationError(f"{field_name} must be a JSON list")
    return _bounded_collection(value, field_name=field_name, maximum=maximum)


def _bounded_json_string_wire_size(
    value: str,
    *,
    remaining: int,
    field_name: str,
) -> int:
    """Count canonical JSON string bytes without materializing escaped text.

    ``canonical_json`` uses ``ensure_ascii=False``.  Quotes, backslashes, and
    control characters can therefore expand far beyond the raw UTF-8 length;
    counting only decoded text bytes would let an attacker evade the receipt
    ceiling.  This is the exact byte cost of Python's canonical encoding for a
    valid Unicode scalar string, including the surrounding quotes.
    """
    if remaining < 2 or len(value) > remaining - 2:
        raise QueryBoundsError(
            f"{field_name} exceeds the receipt byte safety limit"
        )
    consumed = 2
    for character in value:
        codepoint = ord(character)
        if character in {'"', "\\"}:
            consumed += 2
        elif codepoint <= 0x1F:
            consumed += 2 if character in "\b\t\n\f\r" else 6
        elif codepoint <= 0x7F:
            consumed += 1
        elif codepoint <= 0x7FF:
            consumed += 2
        elif 0xD800 <= codepoint <= 0xDFFF:
            raise QueryValidationError(
                f"{field_name} contains a non-encodable Unicode surrogate"
            )
        elif codepoint <= 0xFFFF:
            consumed += 3
        else:
            consumed += 4
        if consumed > remaining:
            raise QueryBoundsError(
                f"{field_name} exceeds the receipt byte safety limit"
            )
    return consumed


def _json_integer_wire_size(value: int) -> int:
    """Return a safe decimal-literal upper bound without allocating ``str``."""
    if value == 0:
        return 1
    # log10(2) < 30103 / 100000, so this never undercounts decimal digits.
    digits = (abs(value).bit_length() * 30_103 + 99_999) // 100_000
    return digits + (1 if value < 0 else 0)


def _json_wire_cost(
    value: Any,
    *,
    field_name: str,
    maximum_bytes: int | None = None,
) -> int:
    """Bound an already-decoded JSON tree before semantic reconstruction.

    Exact built-in containers make iteration terminating; the byte counter is
    deliberately conservative and prevents a bounded node count from hiding
    an enormous aggregate of maximum-sized raw tokens.
    """
    limit = HARD_MAX_RECEIPT_WIRE_BYTES if maximum_bytes is None else maximum_bytes
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise QueryValidationError("receipt byte safety limit must be a positive integer")
    stack = [value]
    consumed = 0
    while stack:
        item = stack.pop()
        if item is None:
            consumed += 4
        elif isinstance(item, bool):
            consumed += 4 if item else 5
        elif isinstance(item, int):
            consumed += _json_integer_wire_size(item)
        elif isinstance(item, str):
            consumed += _bounded_json_string_wire_size(
                item,
                remaining=limit - consumed,
                field_name=field_name,
            )
        elif type(item) is list:
            if len(item) > HARD_MAX_RECEIPT_CONTAINER_ITEMS:
                raise QueryBoundsError(
                    f"{field_name} exceeds the JSON container item safety limit "
                    f"{HARD_MAX_RECEIPT_CONTAINER_ITEMS}"
                )
            consumed += 2 + max(0, len(item) - 1)
            stack.extend(item)
        elif type(item) is dict:
            if len(item) > HARD_MAX_RECEIPT_CONTAINER_ITEMS:
                raise QueryBoundsError(
                    f"{field_name} exceeds the JSON container item safety limit "
                    f"{HARD_MAX_RECEIPT_CONTAINER_ITEMS}"
                )
            consumed += 2 + (2 * len(item)) - (1 if item else 0)
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise QueryValidationError(f"{field_name} object keys must be strings")
                consumed += _bounded_json_string_wire_size(
                    key,
                    remaining=limit - consumed,
                    field_name=field_name,
                )
                stack.append(nested)
        else:
            raise QueryValidationError(
                f"{field_name} must contain only decoded JSON values"
            )
        if consumed > limit:
            raise QueryBoundsError(
                f"{field_name} exceeds the receipt byte safety limit {limit}"
            )
    return consumed


def _admit_json_wire(
    value: Any,
    *,
    field_name: str,
    maximum_bytes: int | None = None,
) -> None:
    _json_wire_cost(
        value,
        field_name=field_name,
        maximum_bytes=maximum_bytes,
    )


def _optional_digest(value: Any, *, field_name: str) -> str | None:
    text = _optional_text(value, field_name=field_name)
    if text is not None and not _SHA256_RE.fullmatch(text):
        raise QueryValidationError(f"{field_name} must be lowercase 64-hex")
    return text


def _csv_safe(value: Any) -> str:
    """Prevent spreadsheet formula interpretation of textual export fields."""
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


# In-row marker for a qualified sum in the tabular exports (CSV, XLSX derived
# from CSV, and the Parquet cells projection).  A qualified sum is a formula
# VALUE whose versioned not-presented policy omitted one or more operands; the
# JSON receipt prints them as ``provenance.qualified_not_presented``.  The
# tabular rows have one fixed column set, so the reason column (always empty
# on a VALUE) carries this marker plus the omitted operand IDs instead.  A
# reader therefore never sees a qualified sum as a plain number.  No kernel
# reason starts with this prefix.
QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX = "qualified_not_presented: "


def _export_reason_text(cell: Any) -> str | None:
    """Reason-column text shared by the CSV/XLSX and Parquet projections.

    Every cell exports its kernel reason unchanged, except a qualified sum,
    which exports the in-row qualifier marker.  Before the not-presented
    policy clock no cell carries a qualifier, so pre-clock export bytes are
    the historical bytes.
    """
    qualified = cell.provenance.qualified_not_presented
    if not qualified:
        return cell.reason
    if cell.state is not CellState.VALUE or cell.reason is not None:
        raise QueryValidationError(
            "a not-presented qualifier is exported only on a formula value"
        )
    return QUALIFIED_NOT_PRESENTED_EXPORT_PREFIX + ", ".join(qualified)


@dataclass(frozen=True)
class QueryPolicy:
    """Both cutoffs are mandatory; a missing cutoff is never silently "now".

    The source cutoff gates ``accepted_at`` for every selected source group and
    its revision lineage.  The recorded cutoff gates every retained source
    artifact clock plus the filing-metadata and governance definitions used by
    the answer.  Normalized cells are evaluated on demand from that cutoff
    projection: absent raw mapping/compute/publish clocks therefore mean the
    source was not materialized through those lanes, not that this query
    invented historical materialization timestamps.
    """

    source_snapshot_at: datetime | str | None
    recorded_at: datetime | str | None
    selection: BitemporalPolicy | str = BitemporalPolicy.LATEST_KNOWN_AS_OF

    def __post_init__(self) -> None:
        source_snapshot_at = _required_utc(
            self.source_snapshot_at, field_name="source_snapshot_at"
        )
        recorded_at = _required_utc(self.recorded_at, field_name="recorded_at")
        try:
            selection = (
                self.selection
                if isinstance(self.selection, BitemporalPolicy)
                else BitemporalPolicy(str(self.selection).strip().lower().replace("-", "_"))
            )
        except ValueError as exc:
            allowed = ", ".join(item.value for item in BitemporalPolicy)
            raise QueryValidationError(f"selection must be one of {allowed}") from exc
        object.__setattr__(self, "source_snapshot_at", source_snapshot_at)
        object.__setattr__(self, "recorded_at", recorded_at)
        object.__setattr__(self, "selection", selection)

    def to_dict(self) -> dict[str, str]:
        return {
            "selection": self.selection.value,
            "source_snapshot_at": utc_text(self.source_snapshot_at) or "",
            "recorded_at": utc_text(self.recorded_at) or "",
        }


# The public names make it easy for adapters written during the source-lane
# build to converge without retaining ambiguous "as_of" terminology.
BitemporalQueryPolicy = QueryPolicy
QueryCutoffs = QueryPolicy


@dataclass(frozen=True)
class QueryBounds:
    """Hard request limits for deterministic in-process query work."""

    max_tickers: int = HARD_MAX_TICKERS
    max_metrics: int = HARD_MAX_METRICS
    max_periods: int = HARD_MAX_PERIODS
    max_cells: int = HARD_MAX_CELLS
    max_visible_source_events_per_cell: int = HARD_MAX_VISIBLE_SOURCE_EVENTS_PER_CELL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_tickers",
            _positive_int(self.max_tickers, field_name="max_tickers", ceiling=HARD_MAX_TICKERS),
        )
        object.__setattr__(
            self,
            "max_metrics",
            _positive_int(self.max_metrics, field_name="max_metrics", ceiling=HARD_MAX_METRICS),
        )
        object.__setattr__(
            self,
            "max_periods",
            _positive_int(self.max_periods, field_name="max_periods", ceiling=HARD_MAX_PERIODS),
        )
        object.__setattr__(
            self,
            "max_cells",
            _positive_int(self.max_cells, field_name="max_cells", ceiling=HARD_MAX_CELLS),
        )
        object.__setattr__(
            self,
            "max_visible_source_events_per_cell",
            _positive_int(
                self.max_visible_source_events_per_cell,
                field_name="max_visible_source_events_per_cell",
                ceiling=HARD_MAX_VISIBLE_SOURCE_EVENTS_PER_CELL,
            ),
        )


@dataclass(frozen=True)
class QueryEntity:
    """A display ticker bound to the immutable ledger entity identity."""

    ticker: str
    entity_id: str
    # Optional issuer SIC for metric applicability (S1-b).  Normalized to a
    # digit-string or ``None``; an unparseable spelling passes through
    # unchanged and E0's classifier maps it to the ``unknown`` issuer class —
    # this class adds no parsing policy of its own.
    issuer_sic: str | int | None = None

    def __post_init__(self) -> None:
        ticker = _require_text(self.ticker, field_name="ticker").upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise QueryValidationError(f"invalid ticker: {self.ticker!r}")
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "entity_id", _require_text(self.entity_id, field_name="entity_id"))
        sic = self.issuer_sic
        if sic is None or isinstance(sic, bool):
            # bool is an int subclass but is not a SIC spelling; fall through
            # to the passthrough text below so it classifies as unknown.
            normalized_sic = None if sic is None else str(sic)
        elif isinstance(sic, int):
            normalized_sic = str(sic)
        elif isinstance(sic, str):
            text = sic.strip()
            normalized_sic = text if text else None
        else:
            raise QueryValidationError(
                f"issuer_sic must be a string, integer, or None: {sic!r}"
            )
        object.__setattr__(self, "issuer_sic", normalized_sic)

    def to_dict(self) -> dict[str, str]:
        payload = {"ticker": self.ticker, "entity_id": self.entity_id}
        if self.issuer_sic is not None:
            payload["issuer_sic"] = self.issuer_sic
        return payload


@dataclass(frozen=True)
class PeriodRequest:
    """A query-period selector normalized by :class:`TypedPeriod`.

    Raw facts do not carry an inferred fiscal label.  Callers therefore provide
    the requested fiscal metadata explicitly when it matters; the exact source
    interval must still match.  This prevents a 90-day fact from silently
    becoming a fiscal quarter or annual result merely because its length looks
    plausible.
    """

    kind: PeriodKind | str
    end: date | str
    start: date | str | None = None
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    calendar_kind: CalendarKind | str = CalendarKind.UNKNOWN
    fiscal_year_weeks: int | None = None
    week_count: int | None = None
    label: str | None = None
    normalized: TypedPeriod = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            normalized = TypedPeriod(
                kind=self.kind,
                end=self.end,
                start=self.start,
                fiscal_year=self.fiscal_year,
                fiscal_quarter=self.fiscal_quarter,
                calendar_kind=self.calendar_kind,
                fiscal_year_weeks=self.fiscal_year_weeks,
                week_count=self.week_count,
            )
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(str(exc)) from exc
        label = _require_text(self.label, field_name="period label") if self.label else None
        object.__setattr__(self, "kind", normalized.kind)
        object.__setattr__(self, "end", normalized.end)
        object.__setattr__(self, "start", normalized.start)
        object.__setattr__(self, "fiscal_year", normalized.fiscal_year)
        object.__setattr__(self, "fiscal_quarter", normalized.fiscal_quarter)
        object.__setattr__(self, "calendar_kind", normalized.calendar_kind)
        object.__setattr__(self, "fiscal_year_weeks", normalized.fiscal_year_weeks)
        object.__setattr__(self, "week_count", normalized.week_count)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "normalized", normalized)

    @classmethod
    def instant(cls, end: date | str, **kwargs: Any) -> "PeriodRequest":
        return cls(kind=PeriodKind.INSTANT, end=end, **kwargs)

    @classmethod
    def duration(cls, start: date | str, end: date | str, **kwargs: Any) -> "PeriodRequest":
        return cls(kind=PeriodKind.DURATION, start=start, end=end, **kwargs)

    @classmethod
    def from_typed(cls, period: TypedPeriod, *, label: str | None = None) -> "PeriodRequest":
        if not isinstance(period, TypedPeriod):
            raise QueryValidationError("period must be a TypedPeriod")
        return cls(
            kind=period.kind,
            start=period.start,
            end=period.end,
            fiscal_year=period.fiscal_year,
            fiscal_quarter=period.fiscal_quarter,
            calendar_kind=period.calendar_kind,
            fiscal_year_weeks=period.fiscal_year_weeks,
            week_count=period.week_count,
            label=label,
        )

    @property
    def key(self) -> tuple[Any, ...]:
        period = self.normalized
        return (
            period.kind.value,
            period.start.isoformat() if period.start else "",
            period.end.isoformat(),
            period.fiscal_year or 0,
            period.fiscal_quarter or 0,
            period.calendar_kind.value,
            period.fiscal_year_weeks or 0,
            period.week_count or 0,
            self.label or "",
        )

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized.to_dict()
        value["label"] = self.label
        return value


# More explicit spellings used by API/adapter code are aliases, not separate
# classes with subtly divergent normalization rules.
MetricPeriod = PeriodRequest
PeriodSelector = PeriodRequest


@dataclass(frozen=True)
class FilingMetadata:
    """Immutable, source-bound filing metadata with an explicit system clock."""

    accession: str
    document_id: str
    source_body_sha256: str
    available_at: datetime | str
    form: str | None = None
    filed_at: date | datetime | str | None = None
    content_sha256: str | None = None
    schema: str = FILING_METADATA_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != FILING_METADATA_SCHEMA:
            raise QueryValidationError(f"unsupported filing metadata schema: {self.schema}")
        accession = _require_text(self.accession, field_name="filing_metadata.accession")
        document_id = _require_text(self.document_id, field_name="filing_metadata.document_id")
        source_body_sha256 = _optional_digest(
            self.source_body_sha256,
            field_name="filing_metadata.source_body_sha256",
        )
        if source_body_sha256 is None:  # pragma: no cover - required field guard.
            raise QueryValidationError("filing_metadata.source_body_sha256 is required")
        available_at = _required_utc(
            self.available_at,
            field_name="filing_metadata.available_at",
        )
        form = _require_text(self.form, field_name="form").upper() if self.form else None
        filed_at = _date_value(self.filed_at, field_name="filed_at")
        payload = {
            "schema": self.schema,
            "accession": accession,
            "document_id": document_id,
            "source_body_sha256": source_body_sha256,
            "available_at": utc_text(available_at),
            "form": form,
            "filed_at": _date_text(filed_at),
        }
        expected_digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
        supplied_digest = _optional_digest(
            self.content_sha256,
            field_name="filing_metadata.content_sha256",
        )
        if supplied_digest is not None and supplied_digest != expected_digest:
            raise QueryValidationError(
                "filing_metadata.content_sha256 does not match canonical metadata content"
            )
        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "source_body_sha256", source_body_sha256)
        object.__setattr__(self, "available_at", available_at)
        object.__setattr__(self, "form", form)
        object.__setattr__(self, "filed_at", filed_at)
        object.__setattr__(self, "content_sha256", expected_digest)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "schema": self.schema,
            "accession": self.accession,
            "document_id": self.document_id,
            "source_body_sha256": self.source_body_sha256,
            "available_at": utc_text(self.available_at),
            "form": self.form,
            "filed_at": _date_text(self.filed_at),
            "content_sha256": self.content_sha256,
        }


class FilingMetadataResolver(Protocol):
    """Legacy shape retained for typing; query engines reject late resolvers."""

    def metadata_for_fact(self, fact: RawFactOccurrence) -> FilingMetadata | Mapping[str, Any] | None:
        """Return filing metadata for one raw occurrence, if authoritatively known."""


@dataclass(frozen=True)
class CellProvenance:
    """The complete receipt needed to reproduce one cell decision."""

    kind: ProvenanceKind | str
    evaluation_policy: EvaluationPolicy | str | None
    policy: BitemporalPolicy
    source_snapshot_at: datetime
    recorded_cutoff_at: datetime
    source_entity_id: str | None = None
    source: str | None = None
    accession: str | None = None
    document_id: str | None = None
    source_url: str | None = None
    source_body_sha256: str | None = None
    form: str | None = None
    filed_at: date | None = None
    filing_metadata_available_at: datetime | None = None
    filing_metadata_content_sha256: str | None = None
    accepted_at: datetime | None = None
    recorded_at: datetime | None = None
    # Raw artifact's recorded mapping clock, if the fact was already through a
    # materialization lane.  It is not overloaded with the registry's rule
    # availability below.
    mapping_available_at: datetime | None = None
    # Latest catalog/metric/mapping-or-formula availability required to govern
    # this answer; included separately so a replay receipt retains both clocks.
    governance_available_at: datetime | None = None
    computed_at: datetime | None = None
    published_at: datetime | None = None
    source_ready_at: datetime | None = None
    system_ready_at: datetime | None = None
    concept_qname: str | None = None
    taxonomy: str | None = None
    concept: str | None = None
    unit: str | None = None
    metric_rule_id: str | None = None
    metric_rule_version: str | None = None
    metric_rule_digest: str | None = None
    mapping_rule_id: str | None = None
    mapping_rule_version: str | None = None
    mapping_digest: str | None = None
    mapping_rule_ids: tuple[str, ...] = ()
    mapping_rule_versions: tuple[str, ...] = ()
    mapping_digests: tuple[str, ...] = ()
    formula_rule_id: str | None = None
    formula_rule_version: str | None = None
    formula_digest: str | None = None
    catalog_id: str | None = None
    catalog_version: str | None = None
    catalog_digest: str | None = None
    mapping_pack_version: str | None = None
    mapping_pack_digest: str | None = None
    formula_pack_version: str | None = None
    formula_pack_digest: str | None = None
    confidence: str | None = None
    alias_priority: int | None = None
    source_occurrence_ids: tuple[str, ...] = ()
    dependency_cell_ids: tuple[str, ...] = ()
    selected_raw_fact: RawFactOccurrence | None = None
    reason: str | None = None
    # Issuer-class applicability verdict (S1-b).  Printed only on metric
    # qualification refusals, where a class was determined; absent from every
    # other receipt so existing bytes stay identical.
    issuer_class: str | None = None
    issuer_class_basis: str | None = None
    # Not-presented (NP) verdict (step 5 b2).  Printed only on a direct
    # ``not_presented`` NOT_APPLICABLE cell; absent from every other receipt
    # so existing bytes stay identical.  ``na_basis`` names why N/A is lawful;
    # ``not_presented`` is the recomputable linkbase evidence behind it.
    na_basis: str | None = None
    not_presented: NotPresentedEvidence | None = None
    # Formula not-presented qualifier (step 5 build-c, R-FORMULA F3).  Printed
    # only on a formula VALUE cell whose governed policy left a not-presented
    # operand out of a signed sum, or that inherited such a qualifier from a
    # VALUE operand; it names the omitted metric IDs.  Absent from every other
    # receipt so existing bytes stay identical.
    qualified_not_presented: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            kind = ProvenanceKind(self.kind)
        except ValueError as exc:
            raise QueryValidationError(f"invalid provenance kind: {self.kind!r}") from exc
        object.__setattr__(self, "kind", kind)
        if self.evaluation_policy is None:
            evaluation_policy = None
        else:
            try:
                evaluation_policy = EvaluationPolicy(self.evaluation_policy)
            except ValueError as exc:
                raise QueryValidationError(
                    f"invalid evaluation policy: {self.evaluation_policy!r}"
                ) from exc
        object.__setattr__(self, "evaluation_policy", evaluation_policy)
        try:
            policy = BitemporalPolicy(self.policy)
        except ValueError as exc:
            raise QueryValidationError(f"invalid provenance policy: {self.policy!r}") from exc
        object.__setattr__(self, "policy", policy)
        object.__setattr__(
            self,
            "source_snapshot_at",
            _required_utc(self.source_snapshot_at, field_name="provenance.source_snapshot_at"),
        )
        object.__setattr__(
            self,
            "recorded_cutoff_at",
            _required_utc(self.recorded_cutoff_at, field_name="provenance.recorded_cutoff_at"),
        )
        for field_name in (
            "accepted_at",
            "recorded_at",
            "mapping_available_at",
            "filing_metadata_available_at",
            "governance_available_at",
            "computed_at",
            "published_at",
            "source_ready_at",
            "system_ready_at",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_utc(getattr(self, field_name), field_name=f"provenance.{field_name}"),
            )
        if self.accepted_at is not None and self.accepted_at > self.source_snapshot_at:
            raise QueryValidationError("provenance.accepted_at exceeds source_snapshot_at")
        if self.source_ready_at is not None and self.source_ready_at > self.source_snapshot_at:
            raise QueryValidationError("provenance.source_ready_at exceeds source_snapshot_at")
        for field_name in (
            "recorded_at",
            "mapping_available_at",
            "filing_metadata_available_at",
            "governance_available_at",
            "computed_at",
            "published_at",
            "system_ready_at",
        ):
            value = getattr(self, field_name)
            if value is not None and value > self.recorded_cutoff_at:
                raise QueryValidationError(
                    f"provenance.{field_name} exceeds recorded_cutoff_at"
                )
        object.__setattr__(
            self,
            "filed_at",
            _date_value(self.filed_at, field_name="provenance.filed_at"),
        )
        for field_name in (
            "source_entity_id",
            "source",
            "accession",
            "document_id",
            "source_url",
            "form",
            "concept_qname",
            "taxonomy",
            "concept",
            "unit",
            "metric_rule_id",
            "metric_rule_version",
            "mapping_rule_id",
            "mapping_rule_version",
            "formula_rule_id",
            "formula_rule_version",
            "catalog_id",
            "catalog_version",
            "mapping_pack_version",
            "formula_pack_version",
            "confidence",
            "reason",
            "issuer_class",
            "issuer_class_basis",
            "na_basis",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name=f"provenance.{field_name}"),
            )
        if self.form is not None:
            object.__setattr__(self, "form", self.form.upper())
        if self.not_presented is not None and not isinstance(
            self.not_presented, NotPresentedEvidence
        ):
            raise QueryValidationError("provenance.not_presented must be NP evidence")
        # The NP pair is all-or-nothing and closed: a basis without evidence
        # (or evidence without a basis) is an N/A nobody can recompute.
        if (self.na_basis is None) is not (self.not_presented is None):
            raise QueryValidationError(
                "provenance.na_basis and provenance.not_presented must appear together"
            )
        if self.na_basis is not None and self.na_basis != NA_BASIS_NOT_PRESENTED_ITEM:
            raise QueryValidationError("provenance.na_basis is not a governed N/A basis")
        if (self.not_presented is not None) is not (self.reason == NOT_PRESENTED_REASON):
            raise QueryValidationError(
                "not-presented evidence must match the not_presented reason"
            )
        for field_name in (
            "source_body_sha256",
            "filing_metadata_content_sha256",
            "metric_rule_digest",
            "mapping_digest",
            "formula_digest",
            "catalog_digest",
            "mapping_pack_digest",
            "formula_pack_digest",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_digest(getattr(self, field_name), field_name=f"provenance.{field_name}"),
            )
        metadata_evidence = (
            self.form,
            self.filed_at,
            self.filing_metadata_available_at,
            self.filing_metadata_content_sha256,
        )
        if any(value is not None for value in metadata_evidence):
            required_metadata = {
                "accession": self.accession,
                "document_id": self.document_id,
                "source_body_sha256": self.source_body_sha256,
                "filing_metadata_available_at": self.filing_metadata_available_at,
                "filing_metadata_content_sha256": self.filing_metadata_content_sha256,
            }
            missing_metadata = tuple(
                name for name, value in required_metadata.items() if value is None
            )
            if missing_metadata:
                raise QueryValidationError(
                    "filing metadata provenance is incomplete: "
                    + ", ".join(missing_metadata)
                )
            FilingMetadata(
                accession=self.accession,
                document_id=self.document_id,
                source_body_sha256=self.source_body_sha256,
                available_at=self.filing_metadata_available_at,
                form=self.form,
                filed_at=self.filed_at,
                content_sha256=self.filing_metadata_content_sha256,
            )
            if (
                self.accepted_at is not None
                and self.filing_metadata_available_at < self.accepted_at
            ):
                raise QueryValidationError(
                    "filing metadata provenance cannot precede source acceptance"
                )
            if (
                self.accepted_at is not None
                and self.filed_at is not None
                and self.filed_at > _latest_edgar_filed_date(self.accepted_at)
            ):
                raise QueryValidationError(
                    "filing metadata provenance filed_at follows the EDGAR filing date "
                    "of source acceptance"
                )
        if self.alias_priority is not None and (
            isinstance(self.alias_priority, bool)
            or not isinstance(self.alias_priority, int)
            or self.alias_priority < 1
        ):
            raise QueryValidationError("provenance.alias_priority must be a positive integer")
        mapping_rule_ids = set(
            _canonical_text_tuple(self.mapping_rule_ids, field_name="provenance.mapping_rule_ids")
        )
        mapping_rule_versions = set(
            _canonical_text_tuple(
                self.mapping_rule_versions, field_name="provenance.mapping_rule_versions"
            )
        )
        mapping_digests = set(
            _canonical_text_tuple(self.mapping_digests, field_name="provenance.mapping_digests")
        )
        if self.mapping_rule_id:
            mapping_rule_ids.add(self.mapping_rule_id)
        if self.mapping_rule_version:
            mapping_rule_versions.add(self.mapping_rule_version)
        if self.mapping_digest:
            mapping_digests.add(self.mapping_digest)
        if any(not _SHA256_RE.fullmatch(item) for item in mapping_digests):
            raise QueryValidationError("provenance.mapping_digests must be lowercase 64-hex")
        object.__setattr__(self, "mapping_rule_ids", tuple(sorted(mapping_rule_ids)))
        object.__setattr__(self, "mapping_rule_versions", tuple(sorted(mapping_rule_versions)))
        object.__setattr__(self, "mapping_digests", tuple(sorted(mapping_digests)))
        object.__setattr__(
            self,
            "source_occurrence_ids",
            _canonical_text_tuple(
                self.source_occurrence_ids, field_name="provenance.source_occurrence_ids"
            ),
        )
        object.__setattr__(
            self,
            "dependency_cell_ids",
            _ordered_text_tuple(
                self.dependency_cell_ids,
                field_name="provenance.dependency_cell_ids",
            ),
        )
        object.__setattr__(
            self,
            "qualified_not_presented",
            _canonical_text_tuple(
                self.qualified_not_presented,
                field_name="provenance.qualified_not_presented",
            ),
        )
        if self.qualified_not_presented and (
            self.kind is not ProvenanceKind.FORMULA or self.reason is not None
        ):
            raise QueryValidationError(
                "provenance.qualified_not_presented is printed only on a formula value"
            )
        if self.selected_raw_fact is not None and not isinstance(
            self.selected_raw_fact, RawFactOccurrence
        ):
            raise QueryValidationError(
                "provenance.selected_raw_fact must be an immutable RawFactOccurrence"
            )

        self._validate_clock_order()
        self._validate_kind_completeness()

    def _validate_clock_order(self) -> None:
        if self.accepted_at is not None and self.recorded_at is not None:
            if self.accepted_at > self.recorded_at:
                raise QueryValidationError("provenance.accepted_at cannot follow recorded_at")
        if self.source_ready_at is not None and self.accepted_at is not None:
            if self.source_ready_at < self.accepted_at:
                raise QueryValidationError("provenance.source_ready_at cannot precede accepted_at")
        if self.computed_at is not None:
            prerequisites = tuple(
                value for value in (self.recorded_at, self.mapping_available_at) if value is not None
            )
            if prerequisites and self.computed_at < max(prerequisites):
                raise QueryValidationError("provenance.computed_at precedes its prerequisites")
        if self.published_at is not None:
            prerequisites = tuple(
                value
                for value in (self.recorded_at, self.mapping_available_at, self.computed_at)
                if value is not None
            )
            if prerequisites and self.published_at < max(prerequisites):
                raise QueryValidationError("provenance.published_at precedes its prerequisites")
        if self.system_ready_at is not None:
            prerequisites = tuple(
                value
                for value in (
                    self.source_ready_at,
                    self.recorded_at,
                    self.mapping_available_at,
                    self.filing_metadata_available_at,
                    self.governance_available_at,
                    self.computed_at,
                    self.published_at,
                )
                if value is not None
            )
            if prerequisites and self.system_ready_at < max(prerequisites):
                raise QueryValidationError("provenance.system_ready_at precedes its prerequisites")

    def _validate_kind_completeness(self) -> None:
        if self.kind is ProvenanceKind.OPAQUE:
            if self.reason is None:
                raise QueryValidationError("opaque provenance requires a generic reason")
            excluded = (
                self.source_entity_id,
                self.source,
                self.evaluation_policy,
                self.accession,
                self.document_id,
                self.source_url,
                self.source_body_sha256,
                self.form,
                self.filed_at,
                self.filing_metadata_available_at,
                self.filing_metadata_content_sha256,
                self.accepted_at,
                self.recorded_at,
                self.mapping_available_at,
                self.governance_available_at,
                self.computed_at,
                self.published_at,
                self.source_ready_at,
                self.system_ready_at,
                self.concept_qname,
                self.taxonomy,
                self.concept,
                self.unit,
                self.metric_rule_id,
                self.metric_rule_version,
                self.metric_rule_digest,
                self.mapping_rule_id,
                self.mapping_rule_version,
                self.mapping_digest,
                self.mapping_rule_ids,
                self.mapping_rule_versions,
                self.mapping_digests,
                self.formula_rule_id,
                self.formula_rule_version,
                self.formula_digest,
                self.catalog_id,
                self.catalog_version,
                self.catalog_digest,
                self.mapping_pack_version,
                self.mapping_pack_digest,
                self.formula_pack_version,
                self.formula_pack_digest,
                self.confidence,
                self.alias_priority,
                self.source_occurrence_ids,
                self.dependency_cell_ids,
                self.selected_raw_fact,
                self.issuer_class,
                self.issuer_class_basis,
                self.na_basis,
                self.not_presented,
                self.qualified_not_presented,
            )
            if any(value not in (None, (), []) for value in excluded):
                raise QueryValidationError("opaque provenance cannot expose receipt details")
            return

        required = {
            "evaluation_policy": self.evaluation_policy,
            "metric_rule_id": self.metric_rule_id,
            "metric_rule_version": self.metric_rule_version,
            "metric_rule_digest": self.metric_rule_digest,
            "catalog_id": self.catalog_id,
            "catalog_version": self.catalog_version,
            "catalog_digest": self.catalog_digest,
            "confidence": self.confidence,
            "governance_available_at": self.governance_available_at,
        }
        if self.kind is ProvenanceKind.DIRECT:
            required.update(
                {
                    "mapping_pack_version": self.mapping_pack_version,
                    "mapping_pack_digest": self.mapping_pack_digest,
                    "mapping_rule_ids": self.mapping_rule_ids,
                    "mapping_rule_versions": self.mapping_rule_versions,
                    "mapping_digests": self.mapping_digests,
                }
            )
        else:
            required.update(
                {
                    "formula_pack_version": self.formula_pack_version,
                    "formula_pack_digest": self.formula_pack_digest,
                }
            )
        missing = tuple(
            name for name, value in required.items() if value is None or value == ()
        )
        if missing:
            raise QueryValidationError(
                f"{self.kind.value} provenance is incomplete: {', '.join(missing)}"
            )
        if self.evaluation_policy is not EvaluationPolicy.ON_DEMAND_CUTOFF_PROJECTION:
            raise QueryValidationError(
                "normalized provenance must explicitly use on-demand cutoff projection"
            )
        if self.kind is ProvenanceKind.DIRECT:
            if any(
                value not in (None, (), [])
                for value in (
                    self.formula_rule_id,
                    self.formula_rule_version,
                    self.formula_digest,
                    self.dependency_cell_ids,
                )
            ):
                raise QueryValidationError("direct provenance cannot contain formula receipts")
            if self.selected_raw_fact is not None and self.source_entity_id is None:
                raise QueryValidationError(
                    "direct raw evidence requires provenance.source_entity_id"
                )
            return
        if self.source_entity_id is not None:
            raise QueryValidationError(
                "formula provenance cannot claim a direct source entity"
            )
        if self.formula_rule_id is None or self.formula_rule_version is None:
            raise QueryValidationError("formula provenance requires its immutable formula rule")
        if self.formula_digest is None:
            raise QueryValidationError("formula provenance requires its formula digest")
        if self.selected_raw_fact is not None:
            raise QueryValidationError("formula provenance cannot embed a selected raw fact")
        if self.computed_at is not None or self.published_at is not None:
            raise QueryValidationError(
                "on-demand formula provenance cannot claim computed_at or published_at"
            )
        if any(
            value not in (None, (), [])
            for value in (
                self.form,
                self.filed_at,
                self.filing_metadata_available_at,
                self.filing_metadata_content_sha256,
                self.accepted_at,
                self.recorded_at,
                self.mapping_available_at,
                self.concept_qname,
                self.taxonomy,
                self.concept,
                self.alias_priority,
                self.source_occurrence_ids,
            )
        ):
            raise QueryValidationError(
                "formula provenance cannot contain direct source receipts"
            )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "kind": self.kind.value,
            "evaluation_policy": (
                self.evaluation_policy.value if self.evaluation_policy is not None else None
            ),
            "policy": self.policy.value,
            "source_snapshot_at": utc_text(self.source_snapshot_at),
            "recorded_cutoff_at": utc_text(self.recorded_cutoff_at),
            "source_entity_id": self.source_entity_id,
            "source": self.source,
            "accession": self.accession,
            "document_id": self.document_id,
            "source_url": self.source_url,
            "source_body_sha256": self.source_body_sha256,
            "form": self.form,
            "filed_at": _date_text(self.filed_at),
            "filing_metadata_available_at": utc_text(self.filing_metadata_available_at),
            "filing_metadata_content_sha256": self.filing_metadata_content_sha256,
            "accepted_at": utc_text(self.accepted_at),
            "recorded_at": utc_text(self.recorded_at),
            "mapping_available_at": utc_text(self.mapping_available_at),
            "governance_available_at": utc_text(self.governance_available_at),
            "computed_at": utc_text(self.computed_at),
            "published_at": utc_text(self.published_at),
            "source_ready_at": utc_text(self.source_ready_at),
            "system_ready_at": utc_text(self.system_ready_at),
            "concept_qname": self.concept_qname,
            "taxonomy": self.taxonomy,
            "concept": self.concept,
            "unit": self.unit,
            "metric_rule_id": self.metric_rule_id,
            "metric_rule_version": self.metric_rule_version,
            "metric_rule_digest": self.metric_rule_digest,
            "mapping_rule_id": self.mapping_rule_id,
            "mapping_rule_version": self.mapping_rule_version,
            "mapping_digest": self.mapping_digest,
            "mapping_rule_ids": list(self.mapping_rule_ids),
            "mapping_rule_versions": list(self.mapping_rule_versions),
            "mapping_digests": list(self.mapping_digests),
            "formula_rule_id": self.formula_rule_id,
            "formula_rule_version": self.formula_rule_version,
            "formula_digest": self.formula_digest,
            "catalog_id": self.catalog_id,
            "catalog_version": self.catalog_version,
            "catalog_digest": self.catalog_digest,
            "mapping_pack_version": self.mapping_pack_version,
            "mapping_pack_digest": self.mapping_pack_digest,
            "formula_pack_version": self.formula_pack_version,
            "formula_pack_digest": self.formula_pack_digest,
            "confidence": self.confidence,
            "alias_priority": self.alias_priority,
            "source_occurrence_ids": list(self.source_occurrence_ids),
            "dependency_cell_ids": list(self.dependency_cell_ids),
            "selected_raw_fact": (
                self.selected_raw_fact.to_dict()
                if self.selected_raw_fact is not None
                else None
            ),
            "reason": self.reason,
        }
        # The issuer-class verdict is conditional: absent key <=> None <=>
        # omitted on re-emit, so every receipt without a verdict keeps its
        # exact historical bytes.
        if self.issuer_class is not None:
            payload["issuer_class"] = self.issuer_class
        if self.issuer_class_basis is not None:
            payload["issuer_class_basis"] = self.issuer_class_basis
        if self.na_basis is not None:
            payload["na_basis"] = self.na_basis
        if self.not_presented is not None:
            payload["not_presented"] = self.not_presented.to_dict()
        if self.qualified_not_presented:
            payload["qualified_not_presented"] = list(self.qualified_not_presented)
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CellProvenance":
        return _cell_provenance_from_dict(value)


def _period_request_from_dict(value: Any) -> PeriodRequest:
    allowed = frozenset(
        {
            "kind",
            "start",
            "end",
            "fiscal_year",
            "fiscal_quarter",
            "calendar_kind",
            "fiscal_year_weeks",
            "week_count",
            "inferred_week_count",
            "semantics",
            "label",
        }
    )
    raw = _strict_wire_mapping(
        value,
        field_name="cell.period",
        allowed=allowed,
        required=allowed,
    )
    try:
        period = PeriodRequest(
            kind=raw["kind"],
            start=raw["start"],
            end=raw["end"],
            fiscal_year=raw["fiscal_year"],
            fiscal_quarter=raw["fiscal_quarter"],
            calendar_kind=raw["calendar_kind"],
            fiscal_year_weeks=raw["fiscal_year_weeks"],
            week_count=raw["week_count"],
            label=raw["label"],
        )
    except (TypeError, ValueError) as exc:
        raise QueryValidationError(f"invalid cell period: {exc}") from exc
    if canonical_json(period.to_dict()) != canonical_json(raw):
        raise QueryValidationError("cell.period derived fields do not match canonical period")
    return period


def _raw_fact_from_dict(value: Any) -> RawFactOccurrence:
    raw_allowed = frozenset(
        {
            "occurrence_id",
            "logical_key",
            "duplicate_group_key",
            "source",
            "concept_qname",
            "context",
            "unit",
            "dimensions_known",
            "source_occurrence_key",
            "raw_token",
            "parsed_value",
            "is_nil",
            "xml_lang",
            "decimals",
            "precision",
            "inline_format",
            "inline_sign",
            "inline_scale",
            "hidden",
            "source_span",
            "event_type",
            "revision_of",
            "clocks",
        }
    )
    raw = _strict_wire_mapping(
        value,
        field_name="selected_raw_fact",
        allowed=raw_allowed,
        required=raw_allowed,
    )
    source_allowed = frozenset(
        {"source", "entity_id", "accession", "document_id", "body_sha256", "source_url"}
    )
    source_raw = _strict_wire_mapping(
        raw["source"],
        field_name="selected_raw_fact.source",
        allowed=source_allowed,
        required=source_allowed,
    )
    context_allowed = frozenset(
        {
            "context_id",
            "entity_scheme",
            "entity_identifier",
            "instant",
            "start",
            "end",
            "explicit_dimensions",
            "typed_dimensions",
            "semantic_key",
        }
    )
    context_raw = _strict_wire_mapping(
        raw["context"],
        field_name="selected_raw_fact.context",
        allowed=context_allowed,
        required=context_allowed,
    )
    clocks_allowed = frozenset(
        {"accepted_at", "recorded_at", "mapping_available_at", "computed_at", "published_at"}
    )
    clocks_raw = _strict_wire_mapping(
        raw["clocks"],
        field_name="selected_raw_fact.clocks",
        allowed=clocks_allowed,
        required=clocks_allowed,
    )
    unit: FactUnit | None = None
    if raw["unit"] is not None:
        unit_allowed = frozenset(
            {"unit_id", "measures", "denominator_measures", "semantic_key"}
        )
        unit_raw = _strict_wire_mapping(
            raw["unit"],
            field_name="selected_raw_fact.unit",
            allowed=unit_allowed,
            required=unit_allowed,
        )
        measures = _wire_list(
            unit_raw["measures"],
            field_name="selected_raw_fact.unit.measures",
            maximum=16,
        )
        denominator_measures = _wire_list(
            unit_raw["denominator_measures"],
            field_name="selected_raw_fact.unit.denominator_measures",
            maximum=16,
        )
        try:
            unit = FactUnit(
                unit_id=unit_raw["unit_id"],
                measures=list(measures),
                denominator_measures=list(denominator_measures),
            )
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(f"invalid selected raw unit: {exc}") from exc
        if canonical_json(unit.to_dict()) != canonical_json(unit_raw):
            raise QueryValidationError("selected raw unit semantic_key is invalid")
    try:
        source = SourceIdentity(**source_raw)
        context = FactContext(
            context_id=context_raw["context_id"],
            entity_scheme=context_raw["entity_scheme"],
            entity_identifier=context_raw["entity_identifier"],
            instant=context_raw["instant"],
            start=context_raw["start"],
            end=context_raw["end"],
            explicit_dimensions=context_raw["explicit_dimensions"],
            typed_dimensions=context_raw["typed_dimensions"],
        )
        clocks = TemporalClocks(**clocks_raw)
        source_span: tuple[int, int] | None = None
        if raw["source_span"] is not None:
            span = _wire_list(
                raw["source_span"],
                field_name="selected_raw_fact.source_span",
                maximum=2,
            )
            if len(span) != 2:
                raise QueryValidationError(
                    "selected_raw_fact.source_span must contain exactly two integers"
                )
            source_span = (span[0], span[1])
        fact = RawFactOccurrence(
            source=source,
            concept_qname=raw["concept_qname"],
            context=context,
            clocks=clocks,
            unit=unit,
            dimensions_known=raw["dimensions_known"],
            source_occurrence_key=raw["source_occurrence_key"],
            raw_token=raw["raw_token"],
            parsed_value=raw["parsed_value"],
            is_nil=raw["is_nil"],
            xml_lang=raw["xml_lang"],
            decimals=raw["decimals"],
            precision=raw["precision"],
            inline_format=raw["inline_format"],
            inline_sign=raw["inline_sign"],
            inline_scale=raw["inline_scale"],
            hidden=raw["hidden"],
            source_span=source_span,
            event_type=raw["event_type"],
            revision_of=raw["revision_of"],
            occurrence_id=raw["occurrence_id"],
        )
    except (TypeError, ValueError) as exc:
        raise QueryValidationError(f"invalid selected raw fact: {exc}") from exc
    if canonical_json(context.to_dict()) != canonical_json(context_raw):
        raise QueryValidationError("selected raw context semantic_key is invalid")
    if canonical_json(fact.to_dict()) != canonical_json(raw):
        raise QueryValidationError("selected raw fact derived identity is invalid")
    return fact


def _cell_provenance_from_dict(value: Any) -> CellProvenance:
    allowed = frozenset(
        {
            "kind",
            "evaluation_policy",
            "policy",
            "source_snapshot_at",
            "recorded_cutoff_at",
            "source_entity_id",
            "source",
            "accession",
            "document_id",
            "source_url",
            "source_body_sha256",
            "form",
            "filed_at",
            "filing_metadata_available_at",
            "filing_metadata_content_sha256",
            "accepted_at",
            "recorded_at",
            "mapping_available_at",
            "governance_available_at",
            "computed_at",
            "published_at",
            "source_ready_at",
            "system_ready_at",
            "concept_qname",
            "taxonomy",
            "concept",
            "unit",
            "metric_rule_id",
            "metric_rule_version",
            "metric_rule_digest",
            "mapping_rule_id",
            "mapping_rule_version",
            "mapping_digest",
            "mapping_rule_ids",
            "mapping_rule_versions",
            "mapping_digests",
            "formula_rule_id",
            "formula_rule_version",
            "formula_digest",
            "catalog_id",
            "catalog_version",
            "catalog_digest",
            "mapping_pack_version",
            "mapping_pack_digest",
            "formula_pack_version",
            "formula_pack_digest",
            "confidence",
            "alias_priority",
            "source_occurrence_ids",
            "dependency_cell_ids",
            "selected_raw_fact",
            "reason",
            # Optional issuer-class verdict keys (S1-b): absent <=> None, so
            # historical receipts replay unchanged and refusals parse back.
            "issuer_class",
            "issuer_class_basis",
            # Optional not-presented verdict keys (step 5 b2), same contract.
            "na_basis",
            "not_presented",
            # Optional formula qualifier (step 5 build-c), same contract.
            "qualified_not_presented",
        }
    )
    raw = _strict_wire_mapping(
        value,
        field_name="cell.provenance",
        allowed=allowed,
        required=allowed
        - {
            "issuer_class",
            "issuer_class_basis",
            "na_basis",
            "not_presented",
            "qualified_not_presented",
        },
    )
    if raw.get("not_presented") is not None:
        try:
            raw = {
                **raw,
                "not_presented": NotPresentedEvidence.from_dict(raw["not_presented"]),
            }
        except NotPresentedError as exc:
            raise QueryValidationError(f"invalid cell provenance: {exc}") from exc
    selected = (
        _raw_fact_from_dict(raw["selected_raw_fact"])
        if raw["selected_raw_fact"] is not None
        else None
    )
    mapping_rule_ids = _wire_list(
        raw["mapping_rule_ids"],
        field_name="cell.provenance.mapping_rule_ids",
        maximum=HARD_MAX_PROVENANCE_IDS,
    )
    mapping_rule_versions = _wire_list(
        raw["mapping_rule_versions"],
        field_name="cell.provenance.mapping_rule_versions",
        maximum=HARD_MAX_PROVENANCE_IDS,
    )
    mapping_digests = _wire_list(
        raw["mapping_digests"],
        field_name="cell.provenance.mapping_digests",
        maximum=HARD_MAX_PROVENANCE_IDS,
    )
    source_occurrence_ids = _wire_list(
        raw["source_occurrence_ids"],
        field_name="cell.provenance.source_occurrence_ids",
        maximum=HARD_MAX_PROVENANCE_IDS,
    )
    dependency_cell_ids = _wire_list(
        raw["dependency_cell_ids"],
        field_name="cell.provenance.dependency_cell_ids",
        maximum=HARD_MAX_DEPENDENCY_RECEIPTS,
    )
    qualified_not_presented: tuple[Any, ...] = ()
    if "qualified_not_presented" in raw:
        qualified_not_presented = _wire_list(
            raw["qualified_not_presented"],
            field_name="cell.provenance.qualified_not_presented",
            maximum=HARD_MAX_PROVENANCE_IDS,
        )
        if not qualified_not_presented:
            raise QueryValidationError(
                "cell.provenance.qualified_not_presented is omitted, never empty"
            )
    try:
        return CellProvenance(
            **{
                **raw,
                "selected_raw_fact": selected,
                "mapping_rule_ids": mapping_rule_ids,
                "mapping_rule_versions": mapping_rule_versions,
                "mapping_digests": mapping_digests,
                "source_occurrence_ids": source_occurrence_ids,
                "dependency_cell_ids": dependency_cell_ids,
                "qualified_not_presented": qualified_not_presented,
            }
        )
    except (TypeError, ValueError) as exc:
        raise QueryValidationError(f"invalid cell provenance: {exc}") from exc


def _cell_node_from_dict(value: Any) -> "CellNode":
    allowed = frozenset(
        {
            "cell_id",
            "governance_bundle_id",
            "ticker",
            "entity_id",
            "metric_id",
            "period",
            "state",
            "status",
            "value",
            "unit",
            "reason",
            "provenance",
        }
    )
    raw = _strict_wire_mapping(
        value,
        field_name="cell_node",
        allowed=allowed,
        required=allowed,
    )
    if raw["status"] != raw["state"]:
        raise QueryValidationError("cell node status must equal state")
    return CellNode(
        governance_bundle_id=raw["governance_bundle_id"],
        ticker=raw["ticker"],
        entity_id=raw["entity_id"],
        metric_id=raw["metric_id"],
        period=_period_request_from_dict(raw["period"]),
        state=raw["state"],
        value=raw["value"],
        unit=raw["unit"],
        provenance=CellProvenance.from_dict(raw["provenance"]),
        reason=raw["reason"],
        cell_id=raw["cell_id"],
    )


@dataclass(frozen=True)
class CellNode:
    """One immutable row in a non-recursive metric receipt DAG."""

    governance_bundle_id: str
    ticker: str
    entity_id: str
    metric_id: str
    period: PeriodRequest
    state: CellState | str
    value: Decimal | str | int | None
    unit: str | None
    provenance: CellProvenance
    reason: str | None = None
    cell_id: str | None = None

    def __post_init__(self) -> None:
        bundle_id = _require_text(
            self.governance_bundle_id,
            field_name="governance_bundle_id",
        )
        if not _SHA256_RE.fullmatch(bundle_id):
            raise QueryValidationError("governance_bundle_id must be lowercase 64-hex")
        ticker = _require_text(self.ticker, field_name="ticker").upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise QueryValidationError(f"invalid ticker: {self.ticker!r}")
        try:
            state = CellState(self.state)
        except ValueError as exc:
            raise QueryValidationError(f"invalid cell state: {self.state!r}") from exc
        if not isinstance(self.period, PeriodRequest):
            raise TypeError("period must be a PeriodRequest")
        if not isinstance(self.provenance, CellProvenance):
            raise TypeError("provenance must be CellProvenance")
        if state is CellState.VALUE:
            if self.value is None:
                raise QueryValidationError("value cells require a Decimal value")
            parsed_value = _bounded_decimal(self.value, field_name="cell value")
            if not self.unit:
                raise QueryValidationError("value cells require a unit")
        else:
            if self.value is not None:
                raise QueryValidationError(
                    "missing/not_evaluable/not_applicable cells cannot contain a value"
                )
            parsed_value = None
        metric_id = _require_text(self.metric_id, field_name="metric_id")
        entity_id = _require_text(self.entity_id, field_name="entity_id")
        unit = _require_text(self.unit, field_name="unit") if self.unit else None
        reason = _require_text(self.reason, field_name="reason") if self.reason else None
        if state is CellState.VALUE and reason is not None:
            raise QueryValidationError("value cells cannot carry a reason")
        if state is not CellState.VALUE and reason is None:
            raise QueryValidationError(
                "missing/not_evaluable/not_applicable cells require a reason"
            )
        if reason != self.provenance.reason:
            raise QueryValidationError("cell reason must exactly match provenance.reason")
        if state is CellState.VALUE:
            if self.provenance.kind is ProvenanceKind.OPAQUE:
                raise QueryValidationError("value cells cannot carry opaque provenance")
            if unit != self.provenance.unit:
                raise QueryValidationError("value cell unit must match provenance.unit")
            if self.provenance.kind is ProvenanceKind.DIRECT:
                required = {
                    "source_entity_id": self.provenance.source_entity_id,
                    "source": self.provenance.source,
                    "accession": self.provenance.accession,
                    "document_id": self.provenance.document_id,
                    "source_body_sha256": self.provenance.source_body_sha256,
                    "form": self.provenance.form,
                    "filing_metadata_available_at": self.provenance.filing_metadata_available_at,
                    "filing_metadata_content_sha256": self.provenance.filing_metadata_content_sha256,
                    "accepted_at": self.provenance.accepted_at,
                    "recorded_at": self.provenance.recorded_at,
                    "source_ready_at": self.provenance.source_ready_at,
                    "system_ready_at": self.provenance.system_ready_at,
                    "concept_qname": self.provenance.concept_qname,
                    "taxonomy": self.provenance.taxonomy,
                    "concept": self.provenance.concept,
                    "mapping_rule_id": self.provenance.mapping_rule_id,
                    "mapping_rule_version": self.provenance.mapping_rule_version,
                    "mapping_digest": self.provenance.mapping_digest,
                    "source_occurrence_ids": self.provenance.source_occurrence_ids,
                    "selected_raw_fact": self.provenance.selected_raw_fact,
                }
            else:
                required = {
                    "source": self.provenance.source,
                    "accession": self.provenance.accession,
                    "document_id": self.provenance.document_id,
                    "source_body_sha256": self.provenance.source_body_sha256,
                    "source_ready_at": self.provenance.source_ready_at,
                    "system_ready_at": self.provenance.system_ready_at,
                    "formula_rule_id": self.provenance.formula_rule_id,
                    "formula_rule_version": self.provenance.formula_rule_version,
                    "formula_digest": self.provenance.formula_digest,
                    "dependency_cell_ids": self.provenance.dependency_cell_ids,
                }
            missing_receipts = tuple(name for name, item in required.items() if not item)
            if missing_receipts:
                raise QueryValidationError(
                    "value cell provenance is incomplete: " + ", ".join(missing_receipts)
                )
        elif self.provenance.kind is ProvenanceKind.OPAQUE and unit is not None:
            raise QueryValidationError("opaque cells cannot expose a governed unit")
        payload = {
            "governance_bundle_id": bundle_id,
            "ticker": ticker,
            "entity_id": entity_id,
            "metric_id": metric_id,
            "period": self.period.to_dict(),
            "state": state.value,
            "value": decimal_text(parsed_value),
            "unit": unit,
            "reason": reason,
            "provenance": self.provenance.to_dict(),
        }
        expected_cell_id = stable_id("metric_cell", payload)
        if self.cell_id is not None:
            supplied = _require_text(self.cell_id, field_name="cell_id")
            if supplied != expected_cell_id:
                raise QueryValidationError("cell_id does not match the canonical cell payload")
        object.__setattr__(self, "governance_bundle_id", bundle_id)
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "entity_id", entity_id)
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "value", parsed_value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "cell_id", expected_cell_id)

    @property
    def status(self) -> CellState:
        return self.state

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "governance_bundle_id": self.governance_bundle_id,
            "ticker": self.ticker,
            "entity_id": self.entity_id,
            "metric_id": self.metric_id,
            "period": self.period.to_dict(),
            "state": self.state.value,
            "status": self.state.value,
            "value": decimal_text(self.value),
            "unit": self.unit,
            "reason": self.reason,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CellNode":
        return _cell_node_from_dict(value)


@dataclass(frozen=True)
class MetricCell:
    """A self-validating root cell plus its bounded, flat dependency DAG."""

    governance_bundle: GovernanceBundle
    ticker: str
    entity_id: str
    metric_id: str
    period: PeriodRequest
    state: CellState | str
    value: Decimal | str | int | None
    unit: str | None
    provenance: CellProvenance
    dependency_nodes: tuple[CellNode, ...] = ()
    reason: str | None = None
    cell_id: str | None = None
    proof_scope: str = RECEIPT_PROOF_SCOPE
    selection_proof: str = RECEIPT_SELECTION_PROOF
    _root_node: CellNode = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.governance_bundle, GovernanceBundle):
            raise TypeError("governance_bundle must be a GovernanceBundle")
        if self.proof_scope != RECEIPT_PROOF_SCOPE:
            raise QueryValidationError("metric receipt proof_scope is unsupported")
        if self.selection_proof != RECEIPT_SELECTION_PROOF:
            raise QueryValidationError("metric receipt selection_proof is unsupported")
        dependencies = _bounded_collection(
            self.dependency_nodes,
            field_name="dependency_nodes",
            maximum=HARD_MAX_RECEIPT_NODES - 1,
        )
        if any(not isinstance(item, CellNode) for item in dependencies):
            raise QueryValidationError("dependency_nodes must contain CellNode values")
        root = CellNode(
            governance_bundle_id=self.governance_bundle.content_id,
            ticker=self.ticker,
            entity_id=self.entity_id,
            metric_id=self.metric_id,
            period=self.period,
            state=self.state,
            value=self.value,
            unit=self.unit,
            provenance=self.provenance,
            reason=self.reason,
            cell_id=self.cell_id,
        )
        nodes: dict[str, CellNode] = {root.cell_id: root}
        for node in dependencies:
            if node.governance_bundle_id != self.governance_bundle.content_id:
                raise QueryValidationError("receipt DAG node references a different governance bundle")
            existing = nodes.get(node.cell_id)
            if existing is not None:
                if existing != node:
                    raise QueryValidationError("receipt DAG contains conflicting duplicate cell_id")
                raise QueryValidationError("dependency_nodes cannot repeat a cell_id")
            nodes[node.cell_id] = node
        postorder = _validate_receipt_graph(
            root_cell_ids=(root.cell_id,),
            nodes=nodes,
            maximum_nodes=HARD_MAX_RECEIPT_NODES,
            maximum_edges=HARD_MAX_RECEIPT_EDGES,
            maximum_depth=HARD_MAX_RECEIPT_DEPTH,
        )
        _validate_node_semantics(
            root_cell_ids=(root.cell_id,),
            nodes=nodes,
            postorder=postorder,
            governance_bundle=self.governance_bundle,
        )
        object.__setattr__(self, "ticker", root.ticker)
        object.__setattr__(self, "entity_id", root.entity_id)
        object.__setattr__(self, "metric_id", root.metric_id)
        object.__setattr__(self, "period", root.period)
        object.__setattr__(self, "state", root.state)
        object.__setattr__(self, "value", root.value)
        object.__setattr__(self, "unit", root.unit)
        object.__setattr__(self, "provenance", root.provenance)
        object.__setattr__(self, "reason", root.reason)
        object.__setattr__(self, "cell_id", root.cell_id)
        object.__setattr__(
            self,
            "dependency_nodes",
            tuple(sorted((node for key, node in nodes.items() if key != root.cell_id), key=lambda item: item.cell_id)),
        )
        object.__setattr__(self, "_root_node", root)

    @property
    def status(self) -> CellState:
        return self.state

    @property
    def is_value(self) -> bool:
        return self.state is CellState.VALUE

    @property
    def root_node(self) -> CellNode:
        return self._root_node

    @property
    def nodes(self) -> tuple[CellNode, ...]:
        return tuple(sorted((self._root_node, *self.dependency_nodes), key=lambda item: item.cell_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CELL_RECEIPT_SCHEMA,
            "proof_scope": self.proof_scope,
            "selection_proof": self.selection_proof,
            "governance_bundle": self.governance_bundle.to_dict(),
            "root_cell_id": self.cell_id,
            "nodes": [item.to_dict() for item in self.nodes],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MetricCell":
        raw = _strict_wire_mapping(
            value,
            field_name="metric_cell_receipt",
            allowed=frozenset(
                {
                    "schema",
                    "proof_scope",
                    "selection_proof",
                    "governance_bundle",
                    "root_cell_id",
                    "nodes",
                }
            ),
            required=frozenset(
                {
                    "schema",
                    "proof_scope",
                    "selection_proof",
                    "governance_bundle",
                    "root_cell_id",
                    "nodes",
                }
            ),
        )
        if raw["schema"] != CELL_RECEIPT_SCHEMA:
            raise QueryValidationError("unsupported metric cell receipt schema")
        if raw["proof_scope"] != RECEIPT_PROOF_SCOPE:
            raise QueryValidationError("metric receipt proof_scope is unsupported")
        if raw["selection_proof"] != RECEIPT_SELECTION_PROOF:
            raise QueryValidationError("metric receipt selection_proof is unsupported")
        try:
            bundle = GovernanceBundle.from_dict(raw["governance_bundle"])
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(f"invalid governance bundle: {exc}") from exc
        node_values = _wire_list(
            raw["nodes"],
            field_name="metric_cell_receipt.nodes",
            maximum=HARD_MAX_RECEIPT_NODES,
        )
        # Cheap schema and limit+1 admission must precede an aggregate byte
        # walk; otherwise a many-million-item decoded list can consume CPU
        # before its O(1) length violation is reported.
        _admit_json_wire(raw, field_name="metric_cell_receipt")
        nodes = tuple(CellNode.from_dict(item) for item in node_values)
        root_id = _require_text(raw["root_cell_id"], field_name="root_cell_id")
        matches = tuple(item for item in nodes if item.cell_id == root_id)
        if len(matches) != 1:
            raise QueryValidationError("metric receipt root_cell_id must identify exactly one node")
        root = matches[0]
        result = cls(
            governance_bundle=bundle,
            ticker=root.ticker,
            entity_id=root.entity_id,
            metric_id=root.metric_id,
            period=root.period,
            state=root.state,
            value=root.value,
            unit=root.unit,
            provenance=root.provenance,
            dependency_nodes=tuple(item for item in nodes if item.cell_id != root_id),
            reason=root.reason,
            cell_id=root.cell_id,
            proof_scope=raw["proof_scope"],
            selection_proof=raw["selection_proof"],
        )
        if canonical_json(result.to_dict()) != canonical_json(raw):
            raise QueryValidationError("metric receipt is not in canonical wire form")
        return result

    verify_receipt_dict = from_dict


def _validate_receipt_graph(
    *,
    root_cell_ids: Sequence[str],
    nodes: Mapping[str, CellNode],
    maximum_nodes: int,
    maximum_edges: int,
    maximum_depth: int,
) -> tuple[str, ...]:
    """Validate a flat DAG iteratively and return a children-first order."""
    roots = _ordered_text_tuple(
        root_cell_ids,
        field_name="root_cell_ids",
        maximum=HARD_MAX_CELLS,
    )
    if not roots:
        raise QueryValidationError("receipt DAG requires at least one root_cell_id")
    if len(nodes) > maximum_nodes:
        raise QueryBoundsError(f"receipt DAG exceeds the node safety limit {maximum_nodes}")
    for key, node in nodes.items():
        if key != node.cell_id:
            raise QueryValidationError("receipt DAG key does not match node.cell_id")
    missing_roots = tuple(root for root in roots if root not in nodes)
    if missing_roots:
        raise QueryValidationError("receipt DAG root_cell_id does not identify a node")
    edge_count = 0
    for node in nodes.values():
        edge_count += len(node.provenance.dependency_cell_ids)
        if edge_count > maximum_edges:
            raise QueryBoundsError(
                f"receipt DAG exceeds the edge safety limit {maximum_edges}"
            )
        for dependency_id in node.provenance.dependency_cell_ids:
            if dependency_id not in nodes:
                raise QueryValidationError(
                    "receipt DAG dependency_cell_id does not identify a node"
                )

    color: dict[str, int] = {}
    subtree_height: dict[str, int] = {}
    postorder: list[str] = []
    for root in roots:
        if color.get(root) == 2:
            continue
        stack: list[tuple[str, bool, int]] = [(root, False, 1)]
        while stack:
            node_id, exiting, depth = stack.pop()
            if depth > maximum_depth:
                raise QueryBoundsError(
                    f"receipt DAG exceeds the depth safety limit {maximum_depth}"
                )
            state = color.get(node_id, 0)
            if exiting:
                if state == 1:
                    dependencies = nodes[node_id].provenance.dependency_cell_ids
                    height = 1 + max(
                        (subtree_height[dependency_id] for dependency_id in dependencies),
                        default=0,
                    )
                    if height > maximum_depth:
                        raise QueryBoundsError(
                            f"receipt DAG exceeds the depth safety limit {maximum_depth}"
                        )
                    subtree_height[node_id] = height
                    color[node_id] = 2
                    postorder.append(node_id)
                continue
            if state == 2:
                continue
            if state == 1:
                raise QueryValidationError("receipt DAG contains a dependency cycle")
            color[node_id] = 1
            stack.append((node_id, True, depth))
            dependencies = nodes[node_id].provenance.dependency_cell_ids
            for dependency_id in reversed(dependencies):
                if dependency_id == node_id or color.get(dependency_id) == 1:
                    raise QueryValidationError("receipt DAG contains a dependency cycle")
                if color.get(dependency_id) != 2:
                    stack.append((dependency_id, False, depth + 1))
    if set(color) != set(nodes):
        raise QueryValidationError("receipt DAG contains orphan/unreachable nodes")
    return tuple(postorder)


def _reachable_receipt_nodes(
    root_cell_id: str,
    nodes: Mapping[str, CellNode],
    *,
    maximum: int,
) -> tuple[str, ...]:
    """Collect one root's unique local proof without recursive expansion."""
    pending = [root_cell_id]
    seen: set[str] = set()
    ordered: list[str] = []
    edge_count = 0
    while pending:
        node_id = pending.pop()
        if node_id in seen:
            continue
        if node_id not in nodes:
            raise QueryValidationError("receipt dependency references a missing node")
        seen.add(node_id)
        ordered.append(node_id)
        if len(seen) > maximum:
            raise QueryBoundsError(f"local receipt exceeds the node safety limit {maximum}")
        dependencies = nodes[node_id].provenance.dependency_cell_ids
        edge_count += len(dependencies)
        if edge_count > HARD_MAX_RECEIPT_EDGES:
            raise QueryBoundsError(
                f"local receipt exceeds the edge safety limit {HARD_MAX_RECEIPT_EDGES}"
            )
        pending.extend(reversed(dependencies))
    return tuple(ordered)


def _enforce_matrix_wire_budget(
    *,
    governance_bundle: GovernanceBundle,
    policy: QueryPolicy,
    entities: Sequence[QueryEntity],
    metric_ids: Sequence[str],
    periods: Sequence[PeriodRequest],
    root_cell_ids: Sequence[str],
    nodes: Sequence[CellNode],
) -> None:
    """Reject an in-memory matrix that could not pass its own wire parser."""
    base = {
        "schema": QUERY_SCHEMA,
        "proof_scope": RECEIPT_PROOF_SCOPE,
        "selection_proof": RECEIPT_SELECTION_PROOF,
        "policy": policy.to_dict(),
        # Mirror the wire form exactly (identity-only entities; see
        # MetricMatrix._unsigned_dict).
        "entities": [
            {"ticker": item.ticker, "entity_id": item.entity_id} for item in entities
        ],
        "metric_ids": list(metric_ids),
        "periods": [item.to_dict() for item in periods],
        "governance_bundle": governance_bundle.to_dict(),
        "root_cell_ids": list(root_cell_ids),
        "nodes": [],
        "query_hash": "0" * 64,
    }
    # Use the exact same conservative decoded-tree accounting as from_dict().
    # The empty list already contributes its two delimiters; replacing it with
    # N nodes adds N list-entry units plus each node's independent tree cost.
    consumed = _json_wire_cost(
        base,
        field_name="metric_matrix_receipt",
        maximum_bytes=HARD_MAX_RECEIPT_WIRE_BYTES,
    ) + max(0, len(nodes) - 1)
    if consumed > HARD_MAX_RECEIPT_WIRE_BYTES:
        raise QueryBoundsError(
            "metric_matrix_receipt exceeds the receipt byte safety limit"
        )
    for node in nodes:
        remaining = HARD_MAX_RECEIPT_WIRE_BYTES - consumed
        consumed += _json_wire_cost(
            node.to_dict(),
            field_name="metric_matrix_receipt",
            maximum_bytes=remaining,
        )
        if consumed > HARD_MAX_RECEIPT_WIRE_BYTES:
            raise QueryBoundsError(
                "metric_matrix_receipt exceeds the receipt byte safety limit"
            )


def _period_contract_error_for(
    contract: MetricContract,
    period: PeriodRequest,
) -> str | None:
    expected = PeriodKind(contract.period_constraints.kind)
    actual = PeriodKind.INSTANT if period.normalized.is_instant else PeriodKind.DURATION
    if actual is not expected:
        return f"outside_period_constraint: metric requires {expected.value}, requested {actual.value}"
    if expected is PeriodKind.DURATION:
        days = period.normalized.duration_days
        minimum = contract.period_constraints.min_duration_days
        maximum = contract.period_constraints.max_duration_days
        if days is None or minimum is None or maximum is None:
            return "outside_period_constraint: duration bounds are not evaluable"
        if not minimum <= days <= maximum:
            return (
                "outside_period_constraint: duration "
                f"{days} days is outside {minimum}..{maximum}"
            )
    return None


def _dependency_period_for(
    output_period: PeriodRequest,
    dependency: MetricContract,
    formula: FormulaRule,
) -> PeriodRequest:
    dependency_kind = PeriodKind(dependency.period_constraints.kind)
    if formula.dependency_period_alignment == "same_period":
        return output_period
    if formula.dependency_period_alignment == "ending_instant_to_duration":
        if dependency_kind is PeriodKind.INSTANT:
            return PeriodRequest(
                kind=PeriodKind.INSTANT,
                end=output_period.normalized.end,
                fiscal_year=output_period.normalized.fiscal_year,
                fiscal_quarter=output_period.normalized.fiscal_quarter,
            )
        return output_period
    raise QueryValidationError(
        "unsupported governed dependency_period_alignment: "
        f"{formula.dependency_period_alignment}"
    )


def _eval_formula_decimal(expression: str, values: Mapping[str, Decimal]) -> Decimal:
    """Evaluate governed arithmetic under the fixed query Decimal contract."""
    try:
        root = ast.parse(expression, mode="eval").body
    except SyntaxError as exc:
        raise QueryValidationError("formula expression is invalid") from exc
    try:
        with localcontext(_formula_context()):
            normalized_values: dict[str, Decimal] = {}
            for name, value in values.items():
                if not isinstance(value, Decimal):
                    raise QueryValidationError(
                        f"formula dependency {name} is not a Decimal value"
                    )
                normalized_values[name] = +_bounded_decimal(
                    value,
                    field_name=f"formula dependency {name}",
                )

            def visit(node: ast.AST) -> Decimal:
                if isinstance(node, ast.Name):
                    try:
                        return normalized_values[node.id]
                    except KeyError as exc:
                        raise QueryValidationError(
                            f"formula references unbound dependency: {node.id}"
                        ) from exc
                if isinstance(node, ast.BinOp):
                    left, right = visit(node.left), visit(node.right)
                    if isinstance(node.op, ast.Add):
                        return left + right
                    if isinstance(node.op, ast.Sub):
                        return left - right
                    if isinstance(node.op, ast.Mult):
                        return left * right
                    if isinstance(node.op, ast.Div):
                        if right == 0:
                            raise ZeroDivisionError
                        return left / right
                raise QueryValidationError(
                    "formula contains unsupported expression construct"
                )

            result = +visit(root)
            if not result.is_finite():
                raise QueryValidationError("formula result is not finite")
            return _bounded_decimal(result, field_name="formula result")
    except (DecimalException, OverflowError) as exc:
        raise QueryValidationError(
            "formula numeric result violates the fixed decimal contract"
        ) from exc


def _bundle_projection_receipt(bundle: GovernanceBundle) -> dict[str, str]:
    """Recompute the legacy per-lane digests from the authoritative bundle."""
    out: dict[str, str] = {}
    contract_payloads = [_contract_definition_payload(item) for item in bundle.contracts]
    if bundle.catalog is not None:
        out.update(
            {
                "catalog_id": bundle.catalog.identifier,
                "catalog_version": REGISTRY_PROJECTION_VERSION,
                "catalog_content_sha256": _content_digest(
                    {
                        "schema": REGISTRY_PROJECTION_SCHEMA,
                        "lane": "catalog",
                        "catalog_id": bundle.catalog.identifier,
                        "contracts": contract_payloads,
                    }
                ),
            }
        )
    mapping_payloads = [
        _mapping_rule_payload(mapping)
        for contract in bundle.contracts
        for mapping in contract.mappings
    ]
    if bundle.mapping_pack is not None:
        out.update(
            {
                "mapping_pack_version": REGISTRY_PROJECTION_VERSION,
                "mapping_pack_content_sha256": _content_digest(
                    {
                        "schema": REGISTRY_PROJECTION_SCHEMA,
                        "lane": "mapping",
                        "mappings": sorted(
                            mapping_payloads,
                            key=lambda item: (
                                item["metric_id"],
                                item["rule"]["rule_id"],
                                item["rule"]["version"],
                            ),
                        ),
                    }
                ),
            }
        )
    formula_payloads = [
        _formula_rule_payload(contract.formula)
        for contract in bundle.contracts
        if contract.formula is not None
    ]
    if bundle.formula_pack is not None:
        out.update(
            {
                "formula_pack_version": REGISTRY_PROJECTION_VERSION,
                "formula_pack_content_sha256": _content_digest(
                    {
                        "schema": REGISTRY_PROJECTION_SCHEMA,
                        "lane": "formula",
                        "formulas": sorted(
                            formula_payloads,
                            key=lambda item: (
                                item["metric_id"],
                                item["rule"]["rule_id"],
                                item["rule"]["version"],
                            ),
                        ),
                    }
                ),
            }
        )
    return out


def _governance_available_at(
    bundle: GovernanceBundle,
    contract: MetricContract,
) -> datetime:
    if bundle.catalog is None:
        raise QueryValidationError("cell metric has no visible catalog lane")
    clocks = [bundle.catalog.available_at, contract.rule.available_at]
    if contract.mappings:
        if bundle.mapping_pack is None:
            raise QueryValidationError("direct metric has no visible mapping lane")
        clocks.append(bundle.mapping_pack.available_at)
        clocks.extend(mapping.rule.available_at for mapping in contract.mappings)
    if contract.formula is not None:
        if bundle.formula_pack is None:
            raise QueryValidationError("formula metric has no visible formula lane")
        clocks.extend((bundle.formula_pack.available_at, contract.formula.rule.available_at))
        if contract.formula.not_presented_policy is not None:
            clocks.append(contract.formula.not_presented_policy.rule.available_at)
    return max(clocks)


def _validate_node_governance(
    node: CellNode,
    bundle: GovernanceBundle,
    receipt: Mapping[str, str],
) -> MetricContract:
    provenance = node.provenance
    if node.governance_bundle_id != bundle.content_id:
        raise QueryValidationError("cell node governance bundle reference is invalid")
    if provenance.recorded_cutoff_at != bundle.recorded_at:
        raise QueryValidationError("cell cutoff does not match governance bundle cutoff")
    try:
        contract = bundle.metric(node.metric_id)
    except KeyError as exc:
        raise QueryValidationError("cell metric is absent from the governance bundle") from exc
    if provenance.kind is ProvenanceKind.OPAQUE:
        if contract.mappings or contract.formula is not None:
            raise QueryValidationError("opaque provenance contradicts visible metric governance")
        if (
            node.state is not CellState.MISSING
            or node.value is not None
            or node.unit is not None
            or node.reason != "governance unavailable at recorded_at cutoff"
            or provenance.dependency_cell_ids
        ):
            raise QueryValidationError("opaque cell does not match governance-unavailable result")
        return contract

    expected_contract_digest = _content_digest(_contract_definition_payload(contract))
    expected_contract = (
        contract.rule.rule_id,
        contract.rule.version,
        expected_contract_digest,
    )
    actual_contract = (
        provenance.metric_rule_id,
        provenance.metric_rule_version,
        provenance.metric_rule_digest,
    )
    if actual_contract != expected_contract:
        raise QueryValidationError("cell metric contract receipt does not match governance bundle")
    if bundle.catalog is None:
        raise QueryValidationError("normalized cell requires a visible catalog lane")
    expected_catalog = (
        receipt.get("catalog_id"),
        receipt.get("catalog_version"),
        receipt.get("catalog_content_sha256"),
    )
    actual_catalog = (
        provenance.catalog_id,
        provenance.catalog_version,
        provenance.catalog_digest,
    )
    if actual_catalog != expected_catalog:
        raise QueryValidationError("cell catalog receipt does not match governance bundle")
    expected_mapping_pack = (
        receipt.get("mapping_pack_version"),
        receipt.get("mapping_pack_content_sha256"),
    )
    actual_mapping_pack = (
        provenance.mapping_pack_version,
        provenance.mapping_pack_digest,
    )
    if actual_mapping_pack != expected_mapping_pack:
        raise QueryValidationError("cell mapping pack receipt does not match governance bundle")
    expected_formula_pack = (
        receipt.get("formula_pack_version"),
        receipt.get("formula_pack_content_sha256"),
    )
    actual_formula_pack = (
        provenance.formula_pack_version,
        provenance.formula_pack_digest,
    )
    if actual_formula_pack != expected_formula_pack:
        raise QueryValidationError("cell formula pack receipt does not match governance bundle")
    if provenance.governance_available_at != _governance_available_at(bundle, contract):
        raise QueryValidationError("cell governance availability does not match governance bundle")

    if provenance.kind is ProvenanceKind.DIRECT:
        if not contract.mappings or contract.formula is not None:
            raise QueryValidationError("direct provenance contradicts metric governance")
        expected_mapping_ids = tuple(sorted({item.rule.rule_id for item in contract.mappings}))
        expected_mapping_versions = tuple(sorted({item.rule.version for item in contract.mappings}))
        expected_mapping_digests = tuple(
            sorted(_content_digest(_mapping_rule_payload(item)) for item in contract.mappings)
        )
        if provenance.mapping_rule_ids != expected_mapping_ids:
            raise QueryValidationError("cell omits or invents a visible mapping rule ID")
        if provenance.mapping_rule_versions != expected_mapping_versions:
            raise QueryValidationError("cell omits or invents a visible mapping rule version")
        if provenance.mapping_digests != expected_mapping_digests:
            raise QueryValidationError("cell omits or invents a visible mapping rule digest")
        if provenance.confidence != contract.confidence:
            raise QueryValidationError("direct cell confidence does not match metric contract")
    else:
        formula = contract.formula
        if formula is None or contract.mappings:
            raise QueryValidationError("formula provenance contradicts metric governance")
        expected_formula = (
            formula.rule.rule_id,
            formula.rule.version,
            _content_digest(_formula_rule_payload(formula)),
        )
        actual_formula = (
            provenance.formula_rule_id,
            provenance.formula_rule_version,
            provenance.formula_digest,
        )
        if actual_formula != expected_formula:
            raise QueryValidationError("cell formula receipt does not match governance bundle")
        if provenance.confidence != formula.rule.confidence:
            raise QueryValidationError("formula cell confidence does not match formula rule")
    return contract


def _selected_mapping_alias(
    provenance: CellProvenance,
    contract: MetricContract,
) -> ConceptAlias | None:
    selected = (
        provenance.mapping_rule_id,
        provenance.mapping_rule_version,
        provenance.mapping_digest,
    )
    if all(item is None for item in selected):
        if any(
            item is not None
            for item in (
                provenance.concept_qname,
                provenance.taxonomy,
                provenance.concept,
                provenance.alias_priority,
            )
        ):
            raise QueryValidationError("cell alias receipt is incomplete")
        return None
    if any(item is None for item in selected):
        raise QueryValidationError("cell selected mapping receipt is incomplete")
    matches = tuple(
        mapping
        for mapping in contract.mappings
        if (
            mapping.rule.rule_id,
            mapping.rule.version,
            _content_digest(_mapping_rule_payload(mapping)),
        )
        == selected
    )
    if len(matches) != 1:
        raise QueryValidationError("cell selected mapping is absent or ambiguous in bundle")
    aliases = tuple(
        alias
        for alias in matches[0].taxonomy_concept_aliases
        if (
            f"{alias.taxonomy}:{alias.concept}" == provenance.concept_qname
            and alias.taxonomy == provenance.taxonomy
            and alias.concept == provenance.concept
            and alias.priority == provenance.alias_priority
        )
    )
    if len(aliases) != 1:
        raise QueryValidationError("cell selected alias does not match governed mapping")
    return aliases[0]


def _validate_period_rejection_provenance(
    provenance: CellProvenance,
    *,
    allow_mapping_inventory: bool,
) -> None:
    """A request-shape rejection occurs before any source evidence is read."""
    forbidden = (
        provenance.source_entity_id,
        provenance.source,
        provenance.accession,
        provenance.document_id,
        provenance.source_url,
        provenance.source_body_sha256,
        provenance.form,
        provenance.filed_at,
        provenance.filing_metadata_available_at,
        provenance.filing_metadata_content_sha256,
        provenance.accepted_at,
        provenance.recorded_at,
        provenance.mapping_available_at,
        provenance.computed_at,
        provenance.published_at,
        provenance.source_ready_at,
        provenance.system_ready_at,
        provenance.concept_qname,
        provenance.taxonomy,
        provenance.concept,
        provenance.unit,
        provenance.mapping_rule_id,
        provenance.mapping_rule_version,
        provenance.mapping_digest,
        provenance.alias_priority,
        provenance.source_occurrence_ids,
        provenance.dependency_cell_ids,
        provenance.selected_raw_fact,
        provenance.qualified_not_presented,
    )
    if any(value not in (None, (), []) for value in forbidden):
        raise QueryValidationError(
            "period rejection provenance must be governance-only"
        )
    if not allow_mapping_inventory and any(
        value
        for value in (
            provenance.mapping_rule_ids,
            provenance.mapping_rule_versions,
            provenance.mapping_digests,
        )
    ):
        raise QueryValidationError(
            "period rejection provenance must be governance-only"
        )


def _validate_qualification_refusal_provenance(
    provenance: CellProvenance,
    *,
    allow_mapping_inventory: bool,
) -> None:
    """A qualification refusal occurs before any source evidence is read.

    Mirrors :func:`_validate_period_rejection_provenance` for the S1-b issuer
    stage.  ``issuer_class``/``issuer_class_basis`` are the refusal's own
    printed verdict and are explicitly allowed here; everything source-shaped
    is forbidden.
    """
    forbidden = (
        provenance.source_entity_id,
        provenance.source,
        provenance.accession,
        provenance.document_id,
        provenance.source_url,
        provenance.source_body_sha256,
        provenance.form,
        provenance.filed_at,
        provenance.filing_metadata_available_at,
        provenance.filing_metadata_content_sha256,
        provenance.accepted_at,
        provenance.recorded_at,
        provenance.mapping_available_at,
        provenance.computed_at,
        provenance.published_at,
        provenance.source_ready_at,
        provenance.system_ready_at,
        provenance.concept_qname,
        provenance.taxonomy,
        provenance.concept,
        provenance.unit,
        provenance.mapping_rule_id,
        provenance.mapping_rule_version,
        provenance.mapping_digest,
        provenance.alias_priority,
        provenance.source_occurrence_ids,
        provenance.dependency_cell_ids,
        provenance.selected_raw_fact,
        provenance.qualified_not_presented,
    )
    if any(value not in (None, (), []) for value in forbidden):
        raise QueryValidationError(
            "qualification refusal provenance must be governance-only"
        )
    if not allow_mapping_inventory and any(
        value
        for value in (
            provenance.mapping_rule_ids,
            provenance.mapping_rule_versions,
            provenance.mapping_digests,
        )
    ):
        raise QueryValidationError(
            "qualification refusal provenance must be governance-only"
        )
    # Bind the printed verdict to the refusal reason: a class-based refusal
    # must name the class it determined; an unknown-class refusal cannot.
    expected_class_present = provenance.reason == "not_applicable_for_issuer_class"
    if (provenance.issuer_class is not None) is not expected_class_present:
        raise QueryValidationError(
            "qualification refusal issuer-class receipt does not match its reason"
        )


_DIRECT_SOURCELESS_NON_VALUE_OUTCOMES = {
    "no governed concept alias applies to the requested taxonomy period": CellState.MISSING,
    "missing_standard_fact: no governed concept alias supplied an exact eligible source interval": CellState.MISSING,
    "no eligible explicitly typed reported revision vintage": CellState.MISSING,
    "ambiguous governed alias priorities across visible mapping rules": CellState.NOT_EVALUABLE,
    "visible source history exceeds the synchronous per-cell bound": CellState.NOT_EVALUABLE,
    # Metric-qualification issuer refusals (S1-b) are governance-only verdicts
    # emitted before any source evidence is read.  The denominator refusal
    # reasons carry a dynamic ``:<input_id>`` suffix and can only attach to
    # formula nodes (direct contracts carry no denominator constraints), so
    # they live in the formula-side recompute, not in these closed tables.
    "not_applicable_for_issuer_class": CellState.NOT_APPLICABLE,
    "issuer_class_unknown": CellState.NOT_EVALUABLE,
}
# The exact-match table the pre-source qualification branches dispatch on;
# kept separate from the outcome tables above so the branch can also bind the
# issuer-class receipt fields to the refusal reason.
_QUALIFICATION_ISSUER_REFUSAL_OUTCOMES = {
    "not_applicable_for_issuer_class": CellState.NOT_APPLICABLE,
    "issuer_class_unknown": CellState.NOT_EVALUABLE,
}
_DIRECT_ALIAS_EVIDENCE_NON_VALUE_OUTCOMES = {
    "selected source vintage is withdrawn": CellState.MISSING,
    "selected source fact has no numeric value": CellState.MISSING,
    "multiple raw economic identities require an explicit governed source-fusion rule": CellState.NOT_EVALUABLE,
    "unlinked source vintages require an explicit typed revision lineage": CellState.NOT_EVALUABLE,
    "ambiguous equal-precedence source vintages cannot be selected": CellState.NOT_EVALUABLE,
    "conflicting duplicate raw facts cannot be selected": CellState.NOT_EVALUABLE,
    "unknown_dimension_scope: source does not expose dimensions, so consolidated-only eligibility cannot be established": CellState.NOT_EVALUABLE,
    "disallowed_dimension: governed metric requires consolidated dimensionless fact": CellState.NOT_EVALUABLE,
    "unexpected_unit: source unit is outside the governed metric contract": CellState.NOT_EVALUABLE,
}
_DIRECT_SOURCE_WITNESS_NON_VALUE_OUTCOMES = {
    "filing form is unavailable or outside the governed metric contract": CellState.NOT_EVALUABLE,
    "source numeric value is outside the query decimal contract": CellState.NOT_EVALUABLE,
}
# Not-presented (step 5 b2): the standard-absence branch upgraded to N/A only
# when governed linkbase evidence recomputes.  Source-less like the absence it
# replaces; the evidence object carries the filing binding instead.
_DIRECT_NOT_PRESENTED_OUTCOMES = {
    NOT_PRESENTED_REASON: CellState.NOT_APPLICABLE,
}


def _applicable_direct_alias_identities(
    contract: MetricContract,
    period: PeriodRequest,
) -> tuple[tuple[str, str, str, str, int], ...]:
    tax_year = period.normalized.end.year
    return tuple(
        (
            mapping.rule.rule_id,
            mapping.rule.version,
            alias.taxonomy,
            alias.concept,
            alias.priority,
        )
        for mapping in contract.mappings
        for alias in mapping.taxonomy_concept_aliases
        if alias.taxonomy_version_start <= tax_year <= alias.taxonomy_version_end
    )


def _has_ambiguous_direct_alias_priorities(
    identities: Sequence[tuple[str, str, str, str, int]],
) -> bool:
    identities_by_priority: dict[int, set[tuple[str, str, str, str]]] = {}
    for rule_id, version, taxonomy, concept, priority in identities:
        identities_by_priority.setdefault(priority, set()).add(
            (taxonomy, concept, rule_id, version)
        )
    return any(len(values) > 1 for values in identities_by_priority.values())


def _validate_direct_non_value_shape(
    node: CellNode,
    contract: MetricContract,
    alias: ConceptAlias | None,
) -> None:
    """Bind non-value receipts to one finite query-kernel branch shape.

    Ledger-wide absence and selection optimality still require the immutable
    external ledger under this receipt's declared proof scope.  This validator
    prevents a canonical receipt from inventing a state, reason, unit, or
    source-witness shape that the kernel itself never emits.
    """
    provenance = node.provenance
    reason = node.reason or ""
    expected_state = (
        _DIRECT_SOURCELESS_NON_VALUE_OUTCOMES.get(reason)
        or _DIRECT_ALIAS_EVIDENCE_NON_VALUE_OUTCOMES.get(reason)
        or _DIRECT_SOURCE_WITNESS_NON_VALUE_OUTCOMES.get(reason)
        or _DIRECT_NOT_PRESENTED_OUTCOMES.get(reason)
    )
    if expected_state is None or node.state is not expected_state:
        raise QueryValidationError(
            "direct non-value state/reason does not match a governed kernel outcome"
        )

    direct_source_fields = (
        provenance.source_entity_id,
        provenance.source,
        provenance.accession,
        provenance.document_id,
        provenance.source_url,
        provenance.source_body_sha256,
        provenance.form,
        provenance.filed_at,
        provenance.filing_metadata_available_at,
        provenance.filing_metadata_content_sha256,
        provenance.accepted_at,
        provenance.recorded_at,
        provenance.mapping_available_at,
        provenance.computed_at,
        provenance.published_at,
        provenance.unit,
    )
    if reason in _DIRECT_NOT_PRESENTED_OUTCOMES:
        evidence = provenance.not_presented
        if (
            evidence is None
            or provenance.na_basis != NA_BASIS_NOT_PRESENTED_ITEM
            or alias is not None
            or any(value is not None for value in direct_source_fields)
            or provenance.source_ready_at is not None
            or provenance.system_ready_at is not None
            or provenance.source_occurrence_ids
        ):
            raise QueryValidationError(
                "not-presented outcome has an invalid provenance shape"
            )
        if not evidence.rule_id.startswith(f"not_presented.{node.metric_id}/"):
            raise QueryValidationError(
                "not-presented evidence names another metric's rule"
            )
        applicable_aliases = _applicable_direct_alias_identities(contract, node.period)
        if not applicable_aliases or _has_ambiguous_direct_alias_priorities(
            applicable_aliases
        ):
            raise QueryValidationError(
                "not-presented outcome requires one unambiguous applicable alias set"
            )
        if provenance.policy is BitemporalPolicy.LATEST_RESTATED:
            raise QueryValidationError(
                "not-presented outcome contradicts latest_restated policy"
            )
        return
    if provenance.not_presented is not None or provenance.na_basis is not None:
        raise QueryValidationError("only a not-presented outcome carries NP evidence")
    if reason in _DIRECT_SOURCELESS_NON_VALUE_OUTCOMES:
        if (
            alias is not None
            or any(value is not None for value in direct_source_fields)
            or provenance.source_ready_at is not None
            or provenance.system_ready_at is not None
            or provenance.source_occurrence_ids
        ):
            raise QueryValidationError(
                "source-less direct outcome cannot contain source evidence"
            )
        applicable_aliases = _applicable_direct_alias_identities(
            contract,
            node.period,
        )
        if (
            reason
            == "no governed concept alias applies to the requested taxonomy period"
            and applicable_aliases
        ):
            raise QueryValidationError(
                "no-alias outcome contradicts applicable governed aliases"
            )
        if (
            reason
            != "no governed concept alias applies to the requested taxonomy period"
            and not applicable_aliases
        ):
            raise QueryValidationError(
                "direct source-less outcome requires an applicable governed alias"
            )
        has_ambiguous_priorities = _has_ambiguous_direct_alias_priorities(
            applicable_aliases
        )
        if reason == "ambiguous governed alias priorities across visible mapping rules":
            if not has_ambiguous_priorities:
                raise QueryValidationError(
                    "ambiguous-alias outcome contradicts governed alias priorities"
                )
        elif has_ambiguous_priorities:
            raise QueryValidationError(
                "direct source-less outcome bypasses governed alias ambiguity"
            )
        if (
            reason == "no eligible explicitly typed reported revision vintage"
            and provenance.policy is not BitemporalPolicy.LATEST_RESTATED
        ):
            raise QueryValidationError(
                "reported-revision absence requires latest_restated policy"
            )
        if (
            reason
            == "missing_standard_fact: no governed concept alias supplied an exact eligible source interval"
            and provenance.policy is BitemporalPolicy.LATEST_RESTATED
        ):
            raise QueryValidationError(
                "generic source absence contradicts latest_restated policy"
            )
        return

    if reason in _DIRECT_ALIAS_EVIDENCE_NON_VALUE_OUTCOMES:
        if (
            alias is None
            or any(value is not None for value in direct_source_fields)
            or provenance.source_ready_at is None
            or provenance.system_ready_at is None
            or not provenance.source_occurrence_ids
        ):
            raise QueryValidationError(
                "direct alias-evidence outcome has an invalid provenance shape"
            )
        if (
            reason == "selected source vintage is withdrawn"
            and provenance.policy is BitemporalPolicy.AS_REPORTED
        ):
            raise QueryValidationError(
                "withdrawn source outcome contradicts as_reported policy"
            )
        return

    core_witness = (
        provenance.source_entity_id,
        provenance.source,
        provenance.accession,
        provenance.document_id,
        provenance.source_body_sha256,
        provenance.accepted_at,
        provenance.recorded_at,
        provenance.source_ready_at,
        provenance.system_ready_at,
        provenance.source_occurrence_ids,
    )
    if alias is None or any(value in (None, (), []) for value in core_witness):
        raise QueryValidationError(
            "direct source-witness outcome has an incomplete provenance shape"
        )
    if provenance.unit != node.unit:
        raise QueryValidationError(
            "direct source-witness unit does not match cell unit"
        )
    if (
        reason == "source numeric value is outside the query decimal contract"
        and provenance.form not in contract.period_constraints.allowed_forms
    ):
        raise QueryValidationError(
            "numeric source rejection requires an allowed filing form"
        )
    if (
        reason == "filing form is unavailable or outside the governed metric contract"
        and provenance.form in contract.period_constraints.allowed_forms
    ):
        raise QueryValidationError(
            "filing-form rejection contradicts an allowed filing form"
        )


def _validate_direct_node(node: CellNode, contract: MetricContract) -> None:
    provenance = node.provenance
    if (
        provenance.source_entity_id is not None
        and provenance.source_entity_id != node.entity_id
    ):
        raise QueryValidationError("direct source entity does not match cell entity")
    alias = _selected_mapping_alias(provenance, contract)
    period_error = _period_contract_error_for(contract, node.period)
    if period_error is not None:
        _validate_period_rejection_provenance(
            provenance,
            allow_mapping_inventory=True,
        )
        if (
            node.state is not CellState.NOT_EVALUABLE
            or node.value is not None
            or node.reason != period_error
            or node.unit != (contract.units[0] if contract.units else None)
            or provenance.selected_raw_fact is not None
        ):
            raise QueryValidationError("direct period rejection does not match governance")
        return
    qualification_state = _QUALIFICATION_ISSUER_REFUSAL_OUTCOMES.get(node.reason or "")
    if qualification_state is not None:
        # S1-b issuer-stage refusal: governance-only verdict emitted before
        # any alias or source evidence is consulted.
        _validate_qualification_refusal_provenance(
            provenance,
            allow_mapping_inventory=True,
        )
        if (
            node.state is not qualification_state
            or node.value is not None
            or node.unit != (contract.units[0] if contract.units else None)
            or provenance.selected_raw_fact is not None
        ):
            raise QueryValidationError(
                "direct qualification refusal does not match governance"
            )
        return
    applicable_aliases = _applicable_direct_alias_identities(contract, node.period)
    has_ambiguous_priorities = _has_ambiguous_direct_alias_priorities(
        applicable_aliases
    )
    claims_ambiguous_priorities = (
        node.state is CellState.NOT_EVALUABLE
        and node.reason
        == "ambiguous governed alias priorities across visible mapping rules"
        and alias is None
    )
    if has_ambiguous_priorities != claims_ambiguous_priorities:
        raise QueryValidationError(
            "direct outcome does not honor governed alias-priority precedence"
        )
    if alias is not None:
        tax_year = node.period.normalized.end.year
        if not alias.taxonomy_version_start <= tax_year <= alias.taxonomy_version_end:
            raise QueryValidationError(
                "selected alias is outside its governed taxonomy-year range"
            )
    expected_unit = contract.units[0] if contract.units else None
    if node.unit != expected_unit:
        raise QueryValidationError(
            "direct non-opaque cell unit does not match metric contract"
        )
    if provenance.unit is not None and provenance.unit != node.unit:
        raise QueryValidationError("direct provenance unit does not match cell unit")
    if node.state is not CellState.VALUE:
        if provenance.selected_raw_fact is not None:
            raise QueryValidationError("non-value direct cell cannot claim selected raw evidence")
        _validate_direct_non_value_shape(node, contract, alias)
        return
    if provenance.not_presented is not None or provenance.na_basis is not None:
        raise QueryValidationError("direct value cell cannot carry NP evidence")
    fact = provenance.selected_raw_fact
    if fact is None or alias is None:
        raise QueryValidationError("direct value cell requires selected raw fact and alias")
    if fact.is_withdrawn:
        raise QueryValidationError("direct value cell cannot select a withdrawn raw fact")
    if fact.is_nil or fact.parsed_value is None:
        raise QueryValidationError("direct value cell requires non-nil numeric raw evidence")
    if provenance.policy is BitemporalPolicy.AS_REPORTED and (
        fact.revision_of is not None or fact.event_type is not FactEventType.FILED
    ):
        raise QueryValidationError(
            "as_reported value must select an unrevised filed root occurrence"
        )
    if (
        provenance.policy is BitemporalPolicy.LATEST_RESTATED
        and fact.event_type not in _REPORTED_REVISION_EVENT_TYPES
    ):
        raise QueryValidationError(
            "latest_restated value must select an explicitly typed reported revision"
        )
    if provenance.form not in contract.period_constraints.allowed_forms:
        raise QueryValidationError("direct value filing form violates metric contract")
    if provenance.source_entity_id != node.entity_id or fact.source.entity_id != node.entity_id:
        raise QueryValidationError("selected raw fact entity does not match cell entity")
    if _bounded_decimal(fact.parsed_value, field_name="raw fact value") != node.value:
        raise QueryValidationError("selected raw fact value does not match cell value")
    if _canonical_raw_unit(fact) != node.unit or node.unit not in contract.units:
        raise QueryValidationError("selected raw fact unit does not match governed cell unit")
    if fact.concept_qname != provenance.concept_qname:
        raise QueryValidationError("selected raw fact concept does not match provenance")
    if fact.concept_qname != f"{alias.taxonomy}:{alias.concept}":
        raise QueryValidationError("selected raw fact concept does not match governed alias")
    expected_source = (
        fact.source.source,
        fact.source.accession,
        fact.source.document_id,
        fact.source.source_url,
        fact.source.body_sha256,
    )
    actual_source = (
        provenance.source,
        provenance.accession,
        provenance.document_id,
        provenance.source_url,
        provenance.source_body_sha256,
    )
    if actual_source != expected_source:
        raise QueryValidationError("selected raw fact source identity does not match provenance")
    expected_clocks = (
        fact.accepted_at,
        fact.recorded_at,
        fact.mapping_available_at,
        fact.computed_at,
        fact.published_at,
    )
    actual_clocks = (
        provenance.accepted_at,
        provenance.recorded_at,
        provenance.mapping_available_at,
        provenance.computed_at,
        provenance.published_at,
    )
    if actual_clocks != expected_clocks:
        raise QueryValidationError("selected raw fact clocks do not match provenance")
    if fact.occurrence_id not in provenance.source_occurrence_ids:
        raise QueryValidationError("selected raw occurrence is absent from lineage IDs")
    if provenance.source_ready_at is None or fact.accepted_at is None:
        raise QueryValidationError("selected raw fact requires source readiness")
    if provenance.source_ready_at < fact.accepted_at:
        raise QueryValidationError("source_ready_at precedes selected raw fact")
    if (
        provenance.system_ready_at is None
        or provenance.system_ready_at < fact.clocks.system_ready_at
    ):
        raise QueryValidationError("system_ready_at precedes selected raw fact")
    if not BitemporalMetricQueryEngine._context_matches_period(fact, node.period):
        raise QueryValidationError("selected raw fact period does not match cell period")
    if not BitemporalMetricQueryEngine._fact_dimensions_allowed(fact, contract):
        raise QueryValidationError("selected raw fact dimensions violate metric contract")


# R-FORMULA F3 (step 5 build-c): reasons a governed formula not-presented
# policy prints.  The N/A prefix also marks a formula cell as a not-presented
# operand of a downstream formula.
FORMULA_NOT_PRESENTED_PREFIX = "formula_not_presented: "
FORMULA_NOT_PRESENTED_WITHHELD_PREFIX = "not_presented_dependency: "
FORMULA_QUALIFIED_WITHHELD_PREFIX = "qualified_dependency: "
_FORMULA_REVISION_BASIS_REASON = (
    "incompatible_revision_basis: formula dependencies require one shared source accession/document"
)


@dataclass(frozen=True)
class _FormulaPolicyOutcome:
    state: CellState
    value: Decimal | None
    reason: str | None
    qualified_not_presented: tuple[str, ...] = ()
    # True when the receipt summarizes its revision basis over the presented
    # (VALUE) operands only, because an operand was left out of the sum.
    value_summary: bool = False


def _is_not_presented_operand(item: Any) -> bool:
    if item.state is not CellState.NOT_APPLICABLE:
        return False
    reason = item.reason or ""
    return reason == NOT_PRESENTED_REASON or reason.startswith(FORMULA_NOT_PRESENTED_PREFIX)


def _eval_qualified_sum(formula: FormulaRule, values: Mapping[str, Decimal]) -> Decimal:
    """Add the presented operands of a governed signed sum (R-FORMULA F3).

    An omitted operand is left out of the sum; it is never materialized as
    zero.  The fixed query Decimal contract is the one ``_eval_formula_decimal``
    applies.
    """
    try:
        terms = formula_signed_terms(formula.expression, formula.dependencies)
    except ValueError as exc:
        raise QueryValidationError(str(exc)) from exc
    try:
        with localcontext(_formula_context()):
            result: Decimal | None = None
            for name, sign in terms:
                if name not in values:
                    continue
                value = values[name]
                if not isinstance(value, Decimal):
                    raise QueryValidationError(
                        f"formula dependency {name} is not a Decimal value"
                    )
                term = +_bounded_decimal(value, field_name=f"formula dependency {name}")
                if sign < 0:
                    term = -term
                result = term if result is None else result + term
            if result is None:
                raise QueryValidationError("qualified_sum has no presented operand")
            result = +result
            if not result.is_finite():
                raise QueryValidationError("formula result is not finite")
            return _bounded_decimal(result, field_name="formula result")
    except (DecimalException, OverflowError) as exc:
        raise QueryValidationError(
            "formula numeric result violates the fixed decimal contract"
        ) from exc


def _formula_policy_outcome(
    dependencies: Sequence[Any],
    formula: FormulaRule,
) -> _FormulaPolicyOutcome | None:
    """Formula stage for not-presented operands, shared by kernel and replay.

    Returns ``None`` unless a dependency is a governed not-presented N/A (or a
    formula N/A that a not-presented operand caused) or a VALUE dependency
    carries a not-presented qualifier; the historical triage then decides with
    unchanged bytes.  Any other N/A dependency also defers to that triage.

    The formula's versioned ``not_presented_policy`` decides; without one the
    formula is withheld (MISSING), never zero-filled.  A qualified sum adds the
    presented operands only when every omitted operand is eligible, every
    presented operand shares one revision basis, and every omission's
    linkbase evidence comes from that same accession; the omitted IDs are
    printed on the VALUE receipt.
    """
    np_ops = [item for item in dependencies if _is_not_presented_operand(item)]
    qualified_ops = [
        item
        for item in dependencies
        if item.state is CellState.VALUE and item.provenance.qualified_not_presented
    ]
    if not np_ops and not qualified_ops:
        return None
    if any(
        item.state is CellState.NOT_APPLICABLE and not _is_not_presented_operand(item)
        for item in dependencies
    ):
        return None
    if np_ops:
        not_evaluable = [item for item in dependencies if item.state is CellState.NOT_EVALUABLE]
        if not_evaluable:
            return _FormulaPolicyOutcome(
                CellState.NOT_EVALUABLE,
                None,
                "incompatible_dependencies: "
                + ", ".join(
                    f"{item.metric_id} ({item.reason or 'not_evaluable'})"
                    for item in not_evaluable
                ),
            )
        missing = [item for item in dependencies if item.state is CellState.MISSING]
        if missing:
            return _FormulaPolicyOutcome(
                CellState.MISSING,
                None,
                "missing_dependency: "
                + ", ".join(f"{item.metric_id} ({item.reason or 'missing'})" for item in missing),
            )
    elif any(item.state is not CellState.VALUE for item in dependencies):
        return None
    np_policy = formula.not_presented_policy
    mode = np_policy.mode if np_policy is not None else "withhold"
    np_ids = [item.metric_id for item in np_ops]
    if np_ops and np_policy is not None and mode == "qualified_sum":
        if any(item not in np_policy.eligible_operands for item in np_ids):
            mode = "withhold"
        elif len(np_ops) == len(dependencies):
            mode = np_policy.all_not_presented or "withhold"
    if np_ops and mode == "withhold":
        return _FormulaPolicyOutcome(
            CellState.MISSING, None, FORMULA_NOT_PRESENTED_WITHHELD_PREFIX + ", ".join(np_ids)
        )
    if np_ops and mode == "not_applicable":
        return _FormulaPolicyOutcome(
            CellState.NOT_APPLICABLE, None, FORMULA_NOT_PRESENTED_PREFIX + ", ".join(np_ids)
        )
    if qualified_ops and (np_policy is None or np_policy.qualified_operand == "withhold"):
        return _FormulaPolicyOutcome(
            CellState.MISSING,
            None,
            FORMULA_QUALIFIED_WITHHELD_PREFIX
            + ", ".join(item.metric_id for item in qualified_ops),
        )
    presented = [item for item in dependencies if item.state is CellState.VALUE]
    revision_bases = {
        (
            item.provenance.source,
            item.provenance.accession,
            item.provenance.document_id,
            item.provenance.source_body_sha256,
        )
        for item in presented
    }
    if len(revision_bases) != 1 or any(
        any(part is None for part in basis) for basis in revision_bases
    ):
        return _FormulaPolicyOutcome(CellState.NOT_EVALUABLE, None, _FORMULA_REVISION_BASIS_REASON)
    shared_accession = next(iter(revision_bases))[1]
    if any(
        item.provenance.not_presented is None
        or item.provenance.not_presented.accession != shared_accession
        for item in np_ops
    ):
        return _FormulaPolicyOutcome(CellState.NOT_EVALUABLE, None, _FORMULA_REVISION_BASIS_REASON)
    values = {item.metric_id: item.value for item in presented}
    if any(value is None for value in values.values()):
        raise QueryValidationError("formula value dependency lacks a Decimal value")
    bound = {key: value for key, value in values.items() if value is not None}
    try:
        result = (
            _eval_qualified_sum(formula, bound)
            if np_ops
            else _eval_formula_decimal(formula.expression, bound)
        )
    except ZeroDivisionError:
        return _FormulaPolicyOutcome(CellState.NOT_EVALUABLE, None, "division_by_zero")
    except QueryValidationError as exc:
        return _FormulaPolicyOutcome(CellState.NOT_EVALUABLE, None, str(exc))
    qualifiers = set(np_ids)
    for item in qualified_ops:
        qualifiers.update(item.provenance.qualified_not_presented)
    return _FormulaPolicyOutcome(
        CellState.VALUE,
        result,
        None,
        tuple(sorted(qualifiers)),
        value_summary=bool(np_ops),
    )


def _expected_denominator_refusal(
    dependencies: Sequence[CellNode],
    formula: FormulaRule,
) -> tuple[CellState, str] | None:
    """Replay parity for the kernel's pre-triage denominator stage (S1-b).

    Mirrors ``qualify_metric``'s constraint loop over the dependency nodes: a
    declared denominator that is not a VALUE dependency counts as missing; a
    non-positive VALUE dependency is an applicability refusal.  The first
    failing input decides (single ``<input_id>``, no joining).
    """
    inputs = {
        item.metric_id: (item.value if item.state is CellState.VALUE else None)
        for item in dependencies
    }
    for input_id in formula.denominator_constraints:
        value = inputs[input_id] if input_id in inputs else None
        if value is None:
            return CellState.NOT_EVALUABLE, f"denominator_missing:{input_id}"
        if value <= 0:
            return CellState.NOT_APPLICABLE, f"denominator_not_positive:{input_id}"
    return None


def _expected_formula_outcome(
    dependencies: Sequence[CellNode],
    formula: FormulaRule,
) -> tuple[CellState, Decimal | None, str | None]:
    # Denominator qualification runs before the dependency triage, exactly as
    # the kernel's _evaluate_formula stage does, so a constraint-named
    # denominator that is missing or non-positive wins over the generic
    # dependency vocabulary below.
    refusal = _expected_denominator_refusal(dependencies, formula)
    if refusal is not None:
        return refusal[0], None, refusal[1]
    np_outcome = _formula_policy_outcome(dependencies, formula)
    if np_outcome is not None:
        return np_outcome.state, np_outcome.value, np_outcome.reason
    not_applicable = [item for item in dependencies if item.state is CellState.NOT_APPLICABLE]
    if not_applicable:
        return (
            CellState.NOT_APPLICABLE,
            None,
            "not_applicable_dependency: "
            + ", ".join(
                f"{item.metric_id} ({item.reason or 'not_applicable'})"
                for item in not_applicable
            ),
        )
    not_evaluable = [item for item in dependencies if item.state is CellState.NOT_EVALUABLE]
    if not_evaluable:
        return (
            CellState.NOT_EVALUABLE,
            None,
            "incompatible_dependencies: "
            + ", ".join(
                f"{item.metric_id} ({item.reason or 'not_evaluable'})"
                for item in not_evaluable
            ),
        )
    missing = [item for item in dependencies if item.state is CellState.MISSING]
    if missing:
        return (
            CellState.MISSING,
            None,
            "missing_dependency: "
            + ", ".join(
                f"{item.metric_id} ({item.reason or 'missing'})" for item in missing
            ),
        )
    revision_bases = {
        (
            item.provenance.source,
            item.provenance.accession,
            item.provenance.document_id,
            item.provenance.source_body_sha256,
        )
        for item in dependencies
    }
    if (
        len(revision_bases) != 1
        or any(any(part is None for part in basis) for basis in revision_bases)
    ):
        return (
            CellState.NOT_EVALUABLE,
            None,
            "incompatible_revision_basis: formula dependencies require one shared source accession/document",
        )
    values = {item.metric_id: item.value for item in dependencies}
    if any(value is None for value in values.values()):
        raise QueryValidationError("formula value dependency lacks a Decimal value")
    try:
        result = _eval_formula_decimal(
            formula.expression,
            {key: value for key, value in values.items() if value is not None},
        )
    except ZeroDivisionError:
        return CellState.NOT_EVALUABLE, None, "division_by_zero"
    except QueryValidationError as exc:
        return CellState.NOT_EVALUABLE, None, str(exc)
    return CellState.VALUE, result, None


def _validate_formula_node(
    node: CellNode,
    contract: MetricContract,
    nodes: Mapping[str, CellNode],
) -> None:
    formula = contract.formula
    if formula is None:
        raise QueryValidationError("formula node has no governed formula")
    period_error = _period_contract_error_for(contract, node.period)
    if period_error is not None:
        _validate_period_rejection_provenance(
            node.provenance,
            allow_mapping_inventory=False,
        )
        if (
            node.state is not CellState.NOT_EVALUABLE
            or node.value is not None
            or node.reason != period_error
            or node.unit != formula.output_unit
        ):
            raise QueryValidationError("formula period rejection does not match governance")
        return
    qualification_state = _QUALIFICATION_ISSUER_REFUSAL_OUTCOMES.get(node.reason or "")
    if qualification_state is not None:
        # S1-b issuer-stage refusal on a formula metric: the verdict fires in
        # _evaluate before any dependency is assembled, so the receipt is
        # governance-only and pre-dependency by construction.
        _validate_qualification_refusal_provenance(
            node.provenance,
            allow_mapping_inventory=False,
        )
        if (
            node.state is not qualification_state
            or node.value is not None
            or node.unit != (contract.units[0] if contract.units else None)
            or node.provenance.dependency_cell_ids
        ):
            raise QueryValidationError(
                "formula qualification refusal does not match governance"
            )
        return
    provenance = node.provenance
    if provenance.unit != formula.output_unit:
        raise QueryValidationError("formula provenance unit does not match output unit")
    dependency_ids = node.provenance.dependency_cell_ids
    dependencies = tuple(nodes[item] for item in dependency_ids)
    if tuple(item.metric_id for item in dependencies) != formula.dependencies:
        raise QueryValidationError("formula dependency metric IDs/order do not match governance")
    for dependency, dependency_id in zip(dependencies, formula.dependencies):
        if dependency.ticker != node.ticker or dependency.entity_id != node.entity_id:
            raise QueryValidationError("formula dependency entity does not match parent cell")
        if (
            dependency.provenance.policy is not provenance.policy
            or dependency.provenance.source_snapshot_at
            != provenance.source_snapshot_at
            or dependency.provenance.recorded_cutoff_at
            != provenance.recorded_cutoff_at
        ):
            raise QueryValidationError(
                "formula dependency policy/cutoffs do not match parent cell"
            )
    # Contract resolution needs the bundle, but period alignment can be checked
    # by the outer semantic validator before calling this helper.
    expected_mapping_ids = tuple(
        sorted(
            {
                identifier
                for item in dependencies
                for identifier in item.provenance.mapping_rule_ids
            }
        )
    )
    expected_mapping_versions = tuple(
        sorted(
            {
                version
                for item in dependencies
                for version in item.provenance.mapping_rule_versions
            }
        )
    )
    expected_mapping_digests = tuple(
        sorted(
            {
                digest
                for item in dependencies
                for digest in item.provenance.mapping_digests
            }
        )
    )
    if provenance.mapping_rule_ids != expected_mapping_ids:
        raise QueryValidationError("formula mapping rule ID summary does not match dependencies")
    if provenance.mapping_rule_versions != expected_mapping_versions:
        raise QueryValidationError("formula mapping rule version summary does not match dependencies")
    if provenance.mapping_digests != expected_mapping_digests:
        raise QueryValidationError("formula mapping digest summary does not match dependencies")
    expected_selected_mapping = (
        expected_mapping_ids[0] if len(expected_mapping_ids) == 1 else None,
        expected_mapping_versions[0] if len(expected_mapping_versions) == 1 else None,
        expected_mapping_digests[0] if len(expected_mapping_digests) == 1 else None,
    )
    actual_selected_mapping = (
        provenance.mapping_rule_id,
        provenance.mapping_rule_version,
        provenance.mapping_digest,
    )
    if actual_selected_mapping != expected_selected_mapping:
        raise QueryValidationError(
            "formula selected mapping summary does not match dependencies"
        )
    np_outcome = (
        _formula_policy_outcome(dependencies, formula)
        if _expected_denominator_refusal(dependencies, formula) is None
        else None
    )
    summary = (
        tuple(item for item in dependencies if item.state is CellState.VALUE)
        if np_outcome is not None and np_outcome.value_summary
        else dependencies
    )
    expected_qualifier = np_outcome.qualified_not_presented if np_outcome is not None else ()
    if provenance.qualified_not_presented != expected_qualifier:
        raise QueryValidationError(
            "formula not-presented qualifier does not recompute from governed dependencies"
        )
    for field_name in ("source", "accession", "document_id", "source_body_sha256", "source_url"):
        values = {getattr(item.provenance, field_name) for item in summary}
        expected = next(iter(values)) if len(values) == 1 else None
        if getattr(provenance, field_name) != expected:
            raise QueryValidationError(f"formula {field_name} summary does not match dependencies")
    expected_source_ready = _clock_max(
        item.provenance.source_ready_at for item in dependencies
    )
    expected_system_ready = _clock_max(
        [_formula_governed_available_at(contract, formula)]
        + [item.provenance.system_ready_at for item in dependencies]
    )
    if provenance.source_ready_at != expected_source_ready:
        raise QueryValidationError("formula source_ready_at does not match dependencies")
    if provenance.system_ready_at != expected_system_ready:
        raise QueryValidationError("formula system_ready_at does not match dependencies")
    expected_state, expected_value, expected_reason = _expected_formula_outcome(
        dependencies,
        formula,
    )
    if (
        node.state is not expected_state
        or node.value != expected_value
        or node.reason != expected_reason
        or node.unit != formula.output_unit
    ):
        raise QueryValidationError("formula cell result does not recompute from governed dependencies")


def _validate_node_semantics(
    *,
    root_cell_ids: Sequence[str],
    nodes: Mapping[str, CellNode],
    postorder: Sequence[str],
    governance_bundle: GovernanceBundle,
) -> None:
    del root_cell_ids  # graph validation already binds reachability to roots.
    receipt = _bundle_projection_receipt(governance_bundle)
    contracts: dict[str, MetricContract] = {}
    for node_id in postorder:
        node = nodes[node_id]
        contract = _validate_node_governance(node, governance_bundle, receipt)
        contracts[node_id] = contract
        if node.provenance.kind is ProvenanceKind.OPAQUE:
            continue
        if node.provenance.kind is ProvenanceKind.DIRECT:
            _validate_direct_node(node, contract)
            continue
        formula = contract.formula
        if formula is None:
            raise QueryValidationError("formula node has no governed formula")
        if _period_contract_error_for(contract, node.period) is None:
            dependencies = tuple(
                nodes[item] for item in node.provenance.dependency_cell_ids
            )
            for dependency, dependency_metric_id in zip(
                dependencies,
                formula.dependencies,
            ):
                dependency_contract = contracts[dependency.cell_id]
                expected_period = _dependency_period_for(
                    node.period,
                    dependency_contract,
                    formula,
                )
                if dependency.metric_id != dependency_metric_id:
                    raise QueryValidationError(
                        "formula dependency metric IDs/order do not match governance"
                    )
                if dependency.period != expected_period:
                    raise QueryValidationError(
                        "formula dependency period alignment does not match governance"
                    )
        _validate_formula_node(node, contract, nodes)


@dataclass(frozen=True)
class DeterministicExport:
    """One reproducible wire representation plus its content hash."""

    media_type: str
    payload: bytes
    sha256: str

    def __post_init__(self) -> None:
        media_type = _require_text(self.media_type, field_name="media_type")
        if not isinstance(self.payload, bytes):
            raise TypeError("export payload must be immutable bytes")
        sha256 = _require_text(self.sha256, field_name="sha256")
        expected = hashlib.sha256(self.payload).hexdigest()
        if not _SHA256_RE.fullmatch(sha256) or sha256 != expected:
            raise QueryValidationError("export sha256 does not match its payload")
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "sha256", sha256)

    @classmethod
    def from_payload(cls, *, media_type: str, payload: bytes) -> "DeterministicExport":
        return cls(
            media_type=_require_text(media_type, field_name="media_type"),
            payload=bytes(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )


def _cell_sort_key(cell: MetricCell) -> tuple[Any, ...]:
    return cell.ticker, cell.metric_id, *cell.period.key, cell.entity_id


@dataclass(frozen=True)
class MetricMatrix:
    """A cross-company/metric/period result with stable JSON and CSV exports."""

    governance_bundle: GovernanceBundle
    policy: QueryPolicy
    entities: tuple[QueryEntity, ...]
    metric_ids: tuple[str, ...]
    periods: tuple[PeriodRequest, ...]
    cells: tuple[MetricCell, ...]
    schema: str = QUERY_SCHEMA
    proof_scope: str = RECEIPT_PROOF_SCOPE
    selection_proof: str = RECEIPT_SELECTION_PROOF
    _nodes: tuple[CellNode, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema != QUERY_SCHEMA:
            raise QueryValidationError(f"unsupported matrix schema: {self.schema}")
        if not isinstance(self.governance_bundle, GovernanceBundle):
            raise TypeError("governance_bundle must be a GovernanceBundle")
        if not isinstance(self.policy, QueryPolicy):
            raise TypeError("policy must be QueryPolicy")
        if self.governance_bundle.recorded_at != self.policy.recorded_at:
            raise QueryValidationError("matrix governance cutoff does not match matrix policy")
        if self.proof_scope != RECEIPT_PROOF_SCOPE:
            raise QueryValidationError("matrix receipt proof_scope is unsupported")
        if self.selection_proof != RECEIPT_SELECTION_PROOF:
            raise QueryValidationError("matrix receipt selection_proof is unsupported")
        entities_input = _bounded_collection(
            self.entities,
            field_name="matrix.entities",
            maximum=HARD_MAX_TICKERS,
        )
        metrics_input = _bounded_collection(
            self.metric_ids,
            field_name="matrix.metric_ids",
            maximum=HARD_MAX_METRICS,
        )
        periods_input = _bounded_collection(
            self.periods,
            field_name="matrix.periods",
            maximum=HARD_MAX_PERIODS,
        )
        cells_input = _bounded_collection(
            self.cells,
            field_name="matrix.cells",
            maximum=HARD_MAX_CELLS,
        )
        if any(not isinstance(item, QueryEntity) for item in entities_input):
            raise TypeError("matrix entities must be QueryEntity instances")
        if any(not isinstance(item, PeriodRequest) for item in periods_input):
            raise TypeError("matrix periods must be PeriodRequest instances")
        if any(not isinstance(item, MetricCell) for item in cells_input):
            raise TypeError("matrix cells must be MetricCell instances")
        entities = tuple(sorted(entities_input, key=lambda item: (item.ticker, item.entity_id)))
        metrics_raw = tuple(_require_text(item, field_name="metric_id") for item in metrics_input)
        metrics = tuple(sorted(metrics_raw))
        periods = tuple(sorted(periods_input, key=lambda item: item.key))
        cells = tuple(sorted(cells_input, key=_cell_sort_key))
        if not entities or not metrics or not periods:
            raise QueryValidationError("matrix requires at least one entity, metric, and period")
        if len({item.ticker for item in entities}) != len(entities):
            raise QueryValidationError("matrix entities must have unique tickers")
        if len({item.entity_id for item in entities}) != len(entities):
            raise QueryValidationError("matrix entities must have unique entity_ids")
        if len(set(metrics_raw)) != len(metrics_raw):
            raise QueryValidationError("matrix metric_ids must be unique")
        if len({item.key for item in periods}) != len(periods):
            raise QueryValidationError("matrix periods must be unique")
        expected = len(entities) * len(metrics) * len(periods)
        if len(cells) != expected:
            raise QueryValidationError(
                f"matrix must contain one cell per entity/metric/period ({expected}); got {len(cells)}"
            )
        entity_by_ticker = {item.ticker: item.entity_id for item in entities}
        expected_keys = {
            (entity.ticker, entity.entity_id, metric_id, period.key)
            for entity in entities
            for metric_id in metrics
            for period in periods
        }
        cell_keys = {(cell.ticker, cell.entity_id, cell.metric_id, cell.period.key) for cell in cells}
        if len(cell_keys) != len(cells):
            raise QueryValidationError("matrix contains duplicate entity/metric/period cells")
        if len({cell.cell_id for cell in cells}) != len(cells):
            raise QueryValidationError("matrix contains duplicate cell_id values")
        if cell_keys != expected_keys:
            raise QueryValidationError("matrix cells do not match the declared entity/metric/period membership")
        for cell in cells:
            if cell.governance_bundle.content_id != self.governance_bundle.content_id:
                raise QueryValidationError("matrix cells must reference one governance bundle")
            if entity_by_ticker.get(cell.ticker) != cell.entity_id:
                raise QueryValidationError("matrix cell ticker/entity identity does not match its entity binding")
            provenance = cell.provenance
            if (
                provenance.policy is not self.policy.selection
                or provenance.source_snapshot_at != self.policy.source_snapshot_at
                or provenance.recorded_cutoff_at != self.policy.recorded_at
            ):
                raise QueryValidationError("matrix cell provenance policy/cutoffs do not match matrix policy")
        node_by_id: dict[str, CellNode] = {}
        for cell in cells:
            for node in cell.nodes:
                existing_node = node_by_id.get(node.cell_id)
                if existing_node is not None and existing_node != node:
                    raise QueryValidationError("matrix contains conflicting duplicate DAG nodes")
                node_by_id[node.cell_id] = node
                if len(node_by_id) > HARD_MAX_MATRIX_NODES:
                    raise QueryBoundsError(
                        f"matrix receipt exceeds the node safety limit {HARD_MAX_MATRIX_NODES}"
                    )
        root_cell_ids = tuple(cell.cell_id for cell in cells)
        postorder = _validate_receipt_graph(
            root_cell_ids=root_cell_ids,
            nodes=node_by_id,
            maximum_nodes=HARD_MAX_MATRIX_NODES,
            maximum_edges=HARD_MAX_MATRIX_EDGES,
            maximum_depth=HARD_MAX_RECEIPT_DEPTH,
        )
        for node in node_by_id.values():
            provenance = node.provenance
            if (
                provenance.policy is not self.policy.selection
                or provenance.source_snapshot_at != self.policy.source_snapshot_at
                or provenance.recorded_cutoff_at != self.policy.recorded_at
            ):
                raise QueryValidationError(
                    "matrix DAG node policy/cutoffs do not match matrix policy"
                )
        _validate_node_semantics(
            root_cell_ids=root_cell_ids,
            nodes=node_by_id,
            postorder=postorder,
            governance_bundle=self.governance_bundle,
        )
        ordered_nodes = tuple(sorted(node_by_id.values(), key=lambda item: item.cell_id))
        _enforce_matrix_wire_budget(
            governance_bundle=self.governance_bundle,
            policy=self.policy,
            entities=entities,
            metric_ids=metrics,
            periods=periods,
            root_cell_ids=root_cell_ids,
            nodes=ordered_nodes,
        )
        object.__setattr__(self, "entities", entities)
        object.__setattr__(self, "metric_ids", metrics)
        object.__setattr__(self, "periods", periods)
        object.__setattr__(self, "cells", cells)
        object.__setattr__(
            self,
            "_nodes",
            ordered_nodes,
        )

    def _unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proof_scope": self.proof_scope,
            "selection_proof": self.selection_proof,
            "policy": self.policy.to_dict(),
            # Identity fields only: the matrix hash and its wire form bind
            # ticker/entity_id membership.  An issuer SIC is an evaluation
            # input (like the policy clocks), visible through the cells when
            # it changes an outcome and byte-inert when it does not.
            "entities": [
                {"ticker": item.ticker, "entity_id": item.entity_id}
                for item in self.entities
            ],
            "metric_ids": list(self.metric_ids),
            "periods": [item.to_dict() for item in self.periods],
            "governance_bundle": self.governance_bundle.to_dict(),
            "root_cell_ids": [item.cell_id for item in self.cells],
            "nodes": [item.to_dict() for item in self._nodes],
        }

    @property
    def query_hash(self) -> str:
        return hashlib.sha256(canonical_json(self._unsigned_dict()).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        value = self._unsigned_dict()
        value["query_hash"] = self.query_hash
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MetricMatrix":
        allowed = frozenset(
            {
                "schema",
                "proof_scope",
                "selection_proof",
                "policy",
                "entities",
                "metric_ids",
                "periods",
                "governance_bundle",
                "root_cell_ids",
                "nodes",
                "query_hash",
            }
        )
        raw = _strict_wire_mapping(
            value,
            field_name="metric_matrix_receipt",
            allowed=allowed,
            required=allowed,
        )
        if raw["schema"] != QUERY_SCHEMA:
            raise QueryValidationError("unsupported matrix schema")
        if raw["proof_scope"] != RECEIPT_PROOF_SCOPE:
            raise QueryValidationError("matrix receipt proof_scope is unsupported")
        if raw["selection_proof"] != RECEIPT_SELECTION_PROOF:
            raise QueryValidationError("matrix receipt selection_proof is unsupported")
        policy_raw = _strict_wire_mapping(
            raw["policy"],
            field_name="matrix.policy",
            allowed=frozenset({"selection", "source_snapshot_at", "recorded_at"}),
            required=frozenset({"selection", "source_snapshot_at", "recorded_at"}),
        )
        try:
            bundle = GovernanceBundle.from_dict(raw["governance_bundle"])
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(f"invalid governance bundle: {exc}") from exc
        entity_values = _wire_list(
            raw["entities"],
            field_name="matrix.entities",
            maximum=HARD_MAX_TICKERS,
        )
        metric_values = _wire_list(
            raw["metric_ids"],
            field_name="matrix.metric_ids",
            maximum=HARD_MAX_METRICS,
        )
        period_values = _wire_list(
            raw["periods"],
            field_name="matrix.periods",
            maximum=HARD_MAX_PERIODS,
        )
        node_values = _wire_list(
            raw["nodes"],
            field_name="matrix.nodes",
            maximum=HARD_MAX_MATRIX_NODES,
        )
        root_values = _wire_list(
            raw["root_cell_ids"],
            field_name="matrix.root_cell_ids",
            maximum=HARD_MAX_CELLS,
        )
        # Enforce all cheap top-level limit+1 contracts before the aggregate
        # byte walk. GovernanceBundle performs the same staged admission for
        # its nested lanes.
        _admit_json_wire(raw, field_name="metric_matrix_receipt")
        policy = QueryPolicy(**policy_raw)
        entities: list[QueryEntity] = []
        for item in entity_values:
            entity_raw = _strict_wire_mapping(
                item,
                field_name="matrix.entity",
                allowed=frozenset({"ticker", "entity_id"}),
                required=frozenset({"ticker", "entity_id"}),
            )
            entities.append(QueryEntity(**entity_raw))
        metric_ids = tuple(
            _require_text(item, field_name="matrix.metric_id")
            for item in metric_values
        )
        periods = tuple(
            _period_request_from_dict(item)
            for item in period_values
        )
        node_by_id: dict[str, CellNode] = {}
        for item in node_values:
            node = CellNode.from_dict(item)
            if node.cell_id in node_by_id:
                raise QueryValidationError("matrix wire contains duplicate cell_id nodes")
            node_by_id[node.cell_id] = node
        root_ids = _ordered_text_tuple(
            root_values,
            field_name="matrix.root_cell_ids",
            maximum=HARD_MAX_CELLS,
        )
        postorder = _validate_receipt_graph(
            root_cell_ids=root_ids,
            nodes=node_by_id,
            maximum_nodes=HARD_MAX_MATRIX_NODES,
            maximum_edges=HARD_MAX_MATRIX_EDGES,
            maximum_depth=HARD_MAX_RECEIPT_DEPTH,
        )
        _validate_node_semantics(
            root_cell_ids=root_ids,
            nodes=node_by_id,
            postorder=postorder,
            governance_bundle=bundle,
        )
        cells: list[MetricCell] = []
        for root_id in root_ids:
            root = node_by_id[root_id]
            reachable = _reachable_receipt_nodes(
                root_id,
                node_by_id,
                maximum=HARD_MAX_RECEIPT_NODES,
            )
            cells.append(
                MetricCell(
                    governance_bundle=bundle,
                    ticker=root.ticker,
                    entity_id=root.entity_id,
                    metric_id=root.metric_id,
                    period=root.period,
                    state=root.state,
                    value=root.value,
                    unit=root.unit,
                    provenance=root.provenance,
                    dependency_nodes=tuple(
                        node_by_id[item] for item in reachable if item != root_id
                    ),
                    reason=root.reason,
                    cell_id=root.cell_id,
                )
            )
        result = cls(
            governance_bundle=bundle,
            policy=policy,
            entities=tuple(entities),
            metric_ids=metric_ids,
            periods=periods,
            cells=tuple(cells),
            schema=raw["schema"],
            proof_scope=raw["proof_scope"],
            selection_proof=raw["selection_proof"],
        )
        supplied_hash = _require_text(raw["query_hash"], field_name="query_hash")
        if not _SHA256_RE.fullmatch(supplied_hash) or supplied_hash != result.query_hash:
            raise QueryValidationError("query_hash does not match canonical unsigned receipt")
        if canonical_json(result.to_dict()) != canonical_json(raw):
            raise QueryValidationError("matrix receipt is not in canonical wire form")
        return result

    verify_receipt_dict = from_dict

    def to_json_bytes(self) -> bytes:
        return canonical_json(self.to_dict()).encode("utf-8")

    def to_csv_bytes(self) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        query_hash = self.query_hash
        writer.writerow(
            (
                "query_hash",
                "receipt_authority",
                "proof_scope",
                "selection_proof",
                "governance_bundle_id",
                "root_cell_id",
                "ticker",
                "entity_id",
                "metric_id",
                "period_kind",
                "period_start",
                "period_end",
                "period_fiscal_year",
                "period_fiscal_quarter",
                "state",
                "value",
                "unit",
                "reason",
                "accession",
                "form",
                "filed_at",
                "accepted_at",
                "recorded_at",
                "mapping_available_at",
                "governance_available_at",
                "source_ready_at",
                "system_ready_at",
                "concept_qname",
                "mapping_rule_id",
                "mapping_rule_version",
                "mapping_digest",
                "formula_rule_id",
                "formula_rule_version",
                "formula_digest",
                "confidence",
                "source_occurrence_ids",
                "dependency_cell_ids",
                "provenance_kind",
                "document_id",
                "filing_metadata_content_sha256",
            )
        )
        for cell in self.cells:
            provenance = cell.provenance
            period = cell.period.normalized
            # Excel/Sheets treats several leading characters as a formula.
            # The canonical numeric value is intentionally excluded: a
            # negative Decimal must remain a negative numeric field, not a
            # text value with a leading apostrophe.
            row = (
                query_hash,
                "json_sidecar_required",
                self.proof_scope,
                self.selection_proof,
                self.governance_bundle.content_id,
                cell.cell_id,
                cell.ticker,
                cell.entity_id,
                cell.metric_id,
                period.kind.value,
                period.start.isoformat() if period.start else "",
                period.end.isoformat(),
                period.fiscal_year or "",
                period.fiscal_quarter or "",
                cell.state.value,
                decimal_text(cell.value) or "",
                cell.unit or "",
                _export_reason_text(cell) or "",
                provenance.accession or "",
                provenance.form or "",
                _date_text(provenance.filed_at) or "",
                utc_text(provenance.accepted_at) or "",
                utc_text(provenance.recorded_at) or "",
                utc_text(provenance.mapping_available_at) or "",
                utc_text(provenance.governance_available_at) or "",
                utc_text(provenance.source_ready_at) or "",
                utc_text(provenance.system_ready_at) or "",
                provenance.concept_qname or "",
                provenance.mapping_rule_id or "",
                provenance.mapping_rule_version or "",
                provenance.mapping_digest or "",
                provenance.formula_rule_id or "",
                provenance.formula_rule_version or "",
                provenance.formula_digest or "",
                provenance.confidence or "",
                canonical_json(list(provenance.source_occurrence_ids)),
                canonical_json(list(provenance.dependency_cell_ids)),
                provenance.kind.value,
                provenance.document_id or "",
                provenance.filing_metadata_content_sha256 or "",
            )
            writer.writerow(
                tuple(value if index == 15 else _csv_safe(value) for index, value in enumerate(row))
            )
        return output.getvalue().encode("utf-8")

    def export(self, format: str) -> DeterministicExport:
        normalized = _require_text(format, field_name="export format").lower()
        if normalized == "json":
            return DeterministicExport.from_payload(
                media_type="application/json", payload=self.to_json_bytes()
            )
        if normalized == "csv":
            return DeterministicExport.from_payload(media_type="text/csv", payload=self.to_csv_bytes())
        raise QueryValidationError("export format must be json or csv")

    def export_json(self) -> DeterministicExport:
        return self.export("json")

    def export_csv(self) -> DeterministicExport:
        return self.export("csv")


@dataclass(frozen=True)
class _SourceSelection:
    state: CellState
    occurrence: RawFactOccurrence | None
    source_ready_at: datetime | None
    system_ready_at: datetime | None
    source_occurrence_ids: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True)
class _AliasCandidate:
    mapping: MappingRule
    alias: ConceptAlias


@dataclass(frozen=True)
class _RegistryProjection:
    recorded_at: datetime
    governance_bundle: GovernanceBundle
    contracts_by_metric: Mapping[str, MetricContract]
    mappings_by_metric: Mapping[str, tuple[MappingRule, ...]]
    formulas_by_metric: Mapping[str, FormulaRule]
    contract_digests: Mapping[str, str]
    mapping_digests: Mapping[tuple[str, str, str], str]
    formula_digests: Mapping[str, str]
    governance_available_by_metric: Mapping[str, datetime]
    catalog_digest: str | None
    mapping_pack_digest: str | None
    formula_pack_digest: str | None
    receipt: Mapping[str, str]


@dataclass(frozen=True)
class _LineageMetadata:
    root_duplicate_group_key: str
    depth: int
    source_ready_at: datetime | None
    system_ready_at: datetime


def _content_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _immutable_rule_payload(rule: Any) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "version": rule.version,
        "available_at": utc_text(rule.available_at),
        "confidence": rule.confidence,
    }


def _contract_definition_payload(contract: MetricContract) -> dict[str, Any]:
    period = contract.period_constraints
    dimensions = contract.dimensional_profile
    presentation = contract.presentation_constraints
    return {
        "metric_id": contract.metric_id,
        "label": contract.label,
        "category": contract.category,
        "rule": _immutable_rule_payload(contract.rule),
        "units": list(contract.units),
        "period_constraints": {
            "kind": period.kind,
            "allowed_forms": list(period.allowed_forms),
            "min_duration_days": period.min_duration_days,
            "max_duration_days": period.max_duration_days,
        },
        "dimensional_profile": {
            "mode": dimensions.mode,
            "allowed_axes": list(dimensions.allowed_axes),
            "require_dimensions": dimensions.require_dimensions,
            "allow_member_selection": dimensions.allow_member_selection,
        },
        "presentation_constraints": {
            "statement": presentation.statement,
            "sign_convention": presentation.sign_convention,
            "display_scale": presentation.display_scale,
            "comparability": presentation.comparability,
        },
        "review": {
            "required": contract.review.required,
            "triggers": list(contract.review.triggers),
        },
        "no_result": {
            "mode": contract.no_result.mode,
            "codes": list(contract.no_result.codes),
        },
        "declared_formula_dependencies": list(contract.declared_formula_dependencies),
    }


def _mapping_rule_payload(mapping: MappingRule) -> dict[str, Any]:
    aliases = sorted(
        mapping.taxonomy_concept_aliases,
        key=lambda item: (
            item.priority,
            item.taxonomy,
            item.concept,
            item.taxonomy_version_start,
            item.taxonomy_version_end,
        ),
    )
    return {
        "metric_id": mapping.metric_id,
        "rule": _immutable_rule_payload(mapping.rule),
        "taxonomy_concept_aliases": [
            {
                "taxonomy": alias.taxonomy,
                "concept": alias.concept,
                "priority": alias.priority,
                "taxonomy_version_start": alias.taxonomy_version_start,
                "taxonomy_version_end": alias.taxonomy_version_end,
            }
            for alias in aliases
        ],
    }


def _formula_rule_payload(formula: FormulaRule) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric_id": formula.metric_id,
        "rule": _immutable_rule_payload(formula.rule),
        "expression": formula.expression,
        "dependencies": list(formula.dependencies),
        "output_unit": formula.output_unit,
        "dependency_period_alignment": formula.dependency_period_alignment,
    }
    np_policy = formula.not_presented_policy
    if np_policy is not None:
        # R-FORMULA F3: the policy joins the governed formula digest from its
        # own rule clock.  Before that clock the cutoff bundle strips it, so
        # every historical digest keeps its exact bytes.
        policy_payload: dict[str, Any] = {
            "rule": _immutable_rule_payload(np_policy.rule),
            "mode": np_policy.mode,
            "qualified_operand": np_policy.qualified_operand,
            "reason": np_policy.reason,
        }
        if np_policy.mode == "qualified_sum":
            policy_payload["eligible_operands"] = list(np_policy.eligible_operands)
            policy_payload["all_not_presented"] = np_policy.all_not_presented
        payload["not_presented_policy"] = policy_payload
    return payload


_REPORTED_REVISION_EVENT_TYPES = frozenset(
    {
        FactEventType.AMENDMENT,
        FactEventType.COMPARATIVE_RECAST,
        FactEventType.RESTATEMENT,
        FactEventType.SOURCE_CORRECTION,
        FactEventType.WITHDRAWN,
    }
)


def _clock_max(values: Iterable[datetime | None]) -> datetime | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None


def _formula_governed_available_at(contract: MetricContract, formula: FormulaRule) -> datetime:
    """Rule knowledge gate for a formula cell: contract, formula and visible policy."""
    clocks = [contract.rule.available_at, formula.rule.available_at]
    if formula.not_presented_policy is not None:
        clocks.append(formula.not_presented_policy.rule.available_at)
    return max(clocks)


def _rounding_tolerance(fact: RawFactOccurrence) -> Decimal:
    """Mirror the ledger's public selection semantics without importing private API."""
    if fact.parsed_value is None:
        return Decimal("0")
    if fact.decimals is not None:
        return (
            Decimal("0")
            if fact.decimals == "INF"
            else Decimal((0, (5,), -int(fact.decimals) - 1))
        )
    if fact.precision is not None:
        value = Decimal(fact.parsed_value)
        if value == 0:
            return Decimal("0")
        scale = value.copy_abs().adjusted() - int(fact.precision) + 1
        return Decimal((0, (5,), scale - 1))
    return Decimal("0")


def _duplicate_interval(item: RawFactOccurrence) -> tuple[Decimal, Decimal]:
    """Return one source fact's exact inclusive XBRL accuracy interval."""
    value = +Decimal(item.parsed_value)
    tolerance = _rounding_tolerance(item)
    return value - tolerance, value + tolerance


def _duplicates_agree(items: Sequence[RawFactOccurrence]) -> bool:
    if len(items) < 2:
        return True
    if len({item.is_nil for item in items}) != 1:
        return False
    if items[0].is_nil:
        return True
    numeric = [item.parsed_value is not None for item in items]
    if any(numeric) and not all(numeric):
        return False
    if not any(numeric):
        return len({item.raw_token for item in items}) == 1
    try:
        with localcontext(_source_comparison_context()):
            greatest_lower: Decimal | None = None
            least_upper: Decimal | None = None
            for item in items:
                lower, upper = _duplicate_interval(item)
                greatest_lower = (
                    lower
                    if greatest_lower is None or lower > greatest_lower
                    else greatest_lower
                )
                least_upper = (
                    upper if least_upper is None or upper < least_upper else least_upper
                )
                if greatest_lower > least_upper:
                    return False
            return True
    except (DecimalException, OverflowError, ValueError):
        # An invalid raw numeric interval cannot prove duplicate equivalence.
        return False


def _duplicate_representative(items: Sequence[RawFactOccurrence]) -> RawFactOccurrence:
    return min(
        items,
        key=lambda item: (
            item.source_span is None,
            item.source_span or (0, 0),
            item.occurrence_id,
        ),
    )


def _qname_parts(value: str) -> tuple[str, str] | None:
    text = str(value or "").strip()
    if text.count(":") != 1:
        return None
    taxonomy, concept = text.split(":", 1)
    return (taxonomy, concept) if taxonomy and concept else None


def _canonical_raw_unit(fact: RawFactOccurrence) -> str | None:
    unit = fact.unit
    if unit is None:
        return None
    numerator = tuple(str(item).strip() for item in unit.measures)
    denominator = tuple(str(item).strip() for item in unit.denominator_measures)
    usd_measures = {"USD", "iso4217:USD"}
    share_measures = {"share", "shares", "xbrli:shares"}
    if len(numerator) == 1 and numerator[0] in usd_measures and not denominator:
        return "USD"
    if len(numerator) == 1 and numerator[0] in share_measures and not denominator:
        return "shares"
    if (
        len(numerator) == 1
        and numerator[0] in usd_measures
        and len(denominator) == 1
        and denominator[0] in share_measures
    ):
        return "USD/shares"
    return None


def _formula_digest(formula: FormulaRule | None) -> str | None:
    if formula is None:
        return None
    return _content_digest(_formula_rule_payload(formula))


def _fact_period_index_key(fact: RawFactOccurrence) -> tuple[str, str, str]:
    context = fact.context
    if context.instant is not None:
        return (PeriodKind.INSTANT.value, "", context.instant.isoformat())
    # RawFactOccurrence validates an exact instant-or-duration context.
    assert context.start is not None and context.end is not None
    return (PeriodKind.DURATION.value, context.start.isoformat(), context.end.isoformat())


def _request_period_index_key(period: PeriodRequest) -> tuple[str, str, str]:
    normalized = period.normalized
    return (
        (
            PeriodKind.INSTANT.value
            if normalized.is_instant
            else PeriodKind.DURATION.value
        ),
        normalized.start.isoformat() if normalized.start else "",
        normalized.end.isoformat(),
    )


class BitemporalMetricQueryEngine:
    """Evaluate a bounded governed metric matrix with complete decision receipts."""

    def __init__(
        self,
        ledger: RawFactLedger | Iterable[RawFactOccurrence],
        registry: MetricRegistry | GovernanceBundle,
        *,
        entities: Mapping[str, str] | Iterable[QueryEntity] = (),
        filing_metadata: Mapping[str, FilingMetadata | Mapping[str, Any]] | None = None,
        bounds: QueryBounds | None = None,
        lineage_evidence: Iterable[LineageEvidenceReceipt] = (),
        not_presented_pack: NotPresentedPack | None = None,
        filing_packages: Iterable[Any] = (),
        source_taxonomy_uris: Mapping[tuple[str, str], str] | None = None,
    ) -> None:
        # FIF A01/A11: the original Clark namespace per (accession,
        # source_occurrence_key), read from the source filings by the same
        # helper the mint path uses.  When supplied, a lineage receipt's
        # attested taxonomy URI pair must equal the source's, so a forgery
        # that swaps both URIs to another approved namespace (with a
        # recomputed receipt_id) fails closed.  Absent keeps the receipt's
        # policy-gated attestation as the only URI evidence.
        self._source_taxonomy_uris = self._freeze_source_taxonomy_uris(source_taxonomy_uris)
        if isinstance(ledger, RawFactLedger):
            self.ledger = ledger
        else:
            # RawFactLedger owns the hard ``limit + 1`` materialization.  Do
            # not eagerly tuple an adversarial/non-terminating iterable first.
            self.ledger = RawFactLedger(ledger)
        if isinstance(registry, MetricRegistry):
            self.registry: MetricRegistry | None = registry
            self._frozen_governance_bundle: GovernanceBundle | None = None
        elif isinstance(registry, GovernanceBundle):
            # A durable query snapshot owns the exact governance receipt it
            # was materialized under. It must be replayable even when the
            # live registry is unavailable or has subsequently changed.
            self.registry = None
            self._frozen_governance_bundle = registry
        else:
            raise TypeError("registry must be a MetricRegistry or GovernanceBundle")
        self.bounds = bounds or QueryBounds()
        if not isinstance(self.bounds, QueryBounds):
            raise TypeError("bounds must be QueryBounds")
        self._entities = self._normalize_entities(entities)
        # Immutable indexes make a matrix query proportional to the requested
        # cells and their matching fact groups, not to all ledger events for
        # every alias. Revision traversal uses the event-id parent index rather
        # than rebuilding a ledger-wide id map for each selected group.
        by_entity_qname_period: dict[tuple[str, str, tuple[str, str, str]], list[RawFactOccurrence]] = {}
        by_accession: dict[str, list[RawFactOccurrence]] = {}
        event_by_id: dict[str, RawFactOccurrence] = {}
        parent_by_id: dict[str, str | None] = {}
        lineage_by_id: dict[str, _LineageMetadata] = {}
        for event in self.ledger.events:
            key = (event.source.entity_id, event.concept_qname, _fact_period_index_key(event))
            by_entity_qname_period.setdefault(key, []).append(event)
            by_accession.setdefault(event.source.accession, []).append(event)
            event_by_id[event.occurrence_id] = event
            parent_by_id[event.occurrence_id] = event.revision_of
            parent_lineage = lineage_by_id.get(event.revision_of) if event.revision_of else None
            if parent_lineage is None:
                source_ready_at = event.accepted_at
                root_duplicate_group_key = event.duplicate_group_key
                depth = 0
                system_ready_at = event.clocks.system_ready_at
            else:
                source_ready_at = (
                    max(parent_lineage.source_ready_at, event.accepted_at)
                    if parent_lineage.source_ready_at is not None and event.accepted_at is not None
                    else None
                )
                root_duplicate_group_key = parent_lineage.root_duplicate_group_key
                depth = parent_lineage.depth + 1
                system_ready_at = max(
                    parent_lineage.system_ready_at,
                    event.clocks.system_ready_at,
                )
            lineage_by_id[event.occurrence_id] = _LineageMetadata(
                root_duplicate_group_key=root_duplicate_group_key,
                depth=depth,
                source_ready_at=source_ready_at,
                system_ready_at=system_ready_at,
            )
        self._events_by_entity_qname_period = MappingProxyType(
            {
                key: tuple(sorted(events, key=lambda item: item.occurrence_id))
                for key, events in by_entity_qname_period.items()
            }
        )
        self._event_by_occurrence_id = MappingProxyType(event_by_id)
        self._events_by_accession = MappingProxyType(
            {key: tuple(events) for key, events in by_accession.items()}
        )
        self._parent_by_occurrence_id = MappingProxyType(parent_by_id)
        self._lineage_by_occurrence_id = MappingProxyType(lineage_by_id)
        self._filing_metadata_by_occurrence = self._freeze_filing_metadata(filing_metadata)
        # FIF-3A4 cross-filing lineage.  Absent/empty is the FIF-3A3 contract
        # and must stay byte-identical, so nothing below runs for an empty
        # bundle.  The ledger itself is untouched: receipts point at unchanged
        # FILED occurrences and never enter ``self.ledger.events``.
        self._confirmations_by_logical_key = self._admit_lineage_evidence(lineage_evidence)
        self._effective_root_cache: dict[
            tuple[str, datetime, datetime], Mapping[str, str]
        ] = {}
        # Step 5 b2 not-presented evidence.  Absent pack => the standard
        # absence branch is untouched and every receipt stays byte-identical.
        (
            self._not_presented_pack,
            self._packages_by_accession,
        ) = self._admit_not_presented(not_presented_pack, filing_packages)

    @staticmethod
    def _freeze_source_taxonomy_uris(
        source_taxonomy_uris: Mapping[tuple[str, str], str] | None,
    ) -> Mapping[tuple[str, str], str] | None:
        if source_taxonomy_uris is None:
            return None
        if not isinstance(source_taxonomy_uris, Mapping):
            raise LineageEvidenceError("source_taxonomy_uris must be a mapping")
        frozen: dict[tuple[str, str], str] = {}
        for key, uri in source_taxonomy_uris.items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not all(isinstance(part, str) for part in key)
                or not isinstance(uri, str)
            ):
                raise LineageEvidenceError(
                    "source_taxonomy_uris maps (accession, source_occurrence_key) to a URI"
                )
            frozen[key] = uri
        return MappingProxyType(frozen)

    def _taxonomy_uris_match_source(
        self,
        parent_representative: RawFactOccurrence,
        child_representative: RawFactOccurrence,
        evidence: Mapping[str, Any],
    ) -> bool:
        """Whether the receipt's URI pair is the source's own namespace pair.

        Without a source map the receipt's policy-gated attestation is the
        only URI evidence and this is vacuously true.  With one, both
        representatives must have a source namespace, those must agree (the
        guard-11 rule the mint applied), and the receipt must carry exactly
        that namespace on both sides.
        """
        if self._source_taxonomy_uris is None:
            return True
        parent_uri = self._source_taxonomy_uris.get(
            (
                parent_representative.source.accession,
                parent_representative.source_occurrence_key or "",
            )
        )
        child_uri = self._source_taxonomy_uris.get(
            (
                child_representative.source.accession,
                child_representative.source_occurrence_key or "",
            )
        )
        if not parent_uri or parent_uri != child_uri:
            return False
        return (
            evidence.get("parent_taxonomy_uri") == parent_uri
            and evidence.get("child_taxonomy_uri") == child_uri
        )

    @staticmethod
    def _normalize_entities(
        entities: Mapping[str, str] | Iterable[QueryEntity],
    ) -> dict[str, QueryEntity]:
        if isinstance(entities, Mapping):
            bindings = _bounded_collection(
                entities.items(),
                field_name="entities",
                maximum=HARD_MAX_ENTITY_BINDINGS,
            )
            raw = tuple(
                QueryEntity(ticker=str(ticker), entity_id=str(entity_id))
                for ticker, entity_id in bindings
            )
        else:
            raw = _bounded_collection(
                entities,
                field_name="entities",
                maximum=HARD_MAX_ENTITY_BINDINGS,
            )
        out: dict[str, QueryEntity] = {}
        for item in raw:
            if isinstance(item, QueryEntity):
                entity = item
            elif isinstance(item, Mapping):
                # The optional ``issuer_sic`` wire key widens the allowed set
                # only when the mapping actually carries it (one keyed probe;
                # ``Mapping.__contains__`` reads no iterator items).  A
                # sic-less entity therefore parses against exactly the
                # historical two-key allowance, hostile-iterator bound
                # included.
                entity_allowed = frozenset({"ticker", "entity_id"})
                if "issuer_sic" in item:
                    entity_allowed = entity_allowed | {"issuer_sic"}
                entity = QueryEntity(
                    **_strict_wire_mapping(
                        item,
                        field_name="entity",
                        allowed=entity_allowed,
                        required=frozenset({"ticker", "entity_id"}),
                    )
                )
            else:
                raise QueryValidationError(
                    "entities must contain QueryEntity values or exact entity mappings"
                )
            if entity.ticker in out and out[entity.ticker] != entity:
                raise QueryValidationError(f"ticker maps to multiple entity_ids: {entity.ticker}")
            out[entity.ticker] = entity
        return out

    def _registry_projection(self, policy: QueryPolicy) -> _RegistryProjection:
        """Project immutable governance definitions at the recorded cutoff.

        Original pack versions and full-pack digests describe the registry
        object's latest contents.  They cannot identify a historical view:
        adding one future rule would otherwise rewrite old query hashes.  This
        projection therefore derives every catalog/pack and per-rule digest
        exclusively from definitions whose own availability clock is visible.
        """
        frozen = self._frozen_governance_bundle
        if frozen is not None:
            return self._frozen_governance_projection(policy, frozen)
        if self.registry is None:  # pragma: no cover - constructor invariant.
            raise QueryValidationError("live governance registry is unavailable")
        try:
            bundle = self.registry.governance_bundle_at(policy.recorded_at)
        except (TypeError, ValueError) as exc:
            raise QueryValidationError(f"cannot construct governance bundle: {exc}") from exc
        return self._projection_from_governance_bundle(policy, bundle)

    def _frozen_governance_projection(
        self,
        policy: QueryPolicy,
        governance_bundle: GovernanceBundle,
    ) -> _RegistryProjection:
        """Project an already materialized governance receipt without live lookup.

        Durable query snapshots persist the exact ``GovernanceBundle`` that
        governed their matrix.  Replaying one must not consult the engine's
        current registry: a later catalog/mapping/formula change is not part of
        an older snapshot.  The bundle's own constructor verifies its complete
        internal lane/contract graph and content ID; this boundary additionally
        binds it to the query's system cutoff.
        """
        if not isinstance(governance_bundle, GovernanceBundle):
            raise QueryValidationError("frozen governance_bundle must be a GovernanceBundle")
        if governance_bundle.recorded_at != policy.recorded_at:
            raise QueryValidationError(
                "frozen governance bundle recorded_at must equal query policy.recorded_at"
            )
        return self._projection_from_governance_bundle(policy, governance_bundle)

    def _projection_for(
        self,
        policy: QueryPolicy,
        *,
        governance_bundle: GovernanceBundle | None = None,
    ) -> _RegistryProjection:
        """Choose live cutoff governance or an explicitly frozen snapshot bundle."""
        if governance_bundle is not None and not isinstance(governance_bundle, GovernanceBundle):
            raise QueryValidationError("governance_bundle must be a GovernanceBundle")
        frozen = self._frozen_governance_bundle
        if frozen is not None:
            if governance_bundle is not None and governance_bundle.content_id != frozen.content_id:
                raise QueryValidationError(
                    "query governance_bundle conflicts with the engine's frozen governance bundle"
                )
            return self._frozen_governance_projection(policy, frozen)
        if governance_bundle is None:
            return self._registry_projection(policy)
        return self._frozen_governance_projection(policy, governance_bundle)

    def _projection_from_governance_bundle(
        self,
        policy: QueryPolicy,
        bundle: GovernanceBundle,
    ) -> _RegistryProjection:
        """Compile one validated bundle into the kernel's immutable lookup maps."""
        if bundle.recorded_at != policy.recorded_at:
            raise QueryValidationError(
                "governance bundle recorded_at must equal query policy.recorded_at"
            )
        catalog_visible = bundle.catalog is not None
        mapping_pack_visible = bundle.mapping_pack is not None
        formula_pack_visible = bundle.formula_pack is not None
        visible_contracts = bundle.contracts
        contracts_by_metric = {item.metric_id: item for item in visible_contracts}
        mappings_by_metric: dict[str, tuple[MappingRule, ...]] = {}
        formulas_by_metric: dict[str, FormulaRule] = {}
        contract_digests: dict[str, str] = {}
        mapping_digests: dict[tuple[str, str, str], str] = {}
        formula_digests: dict[str, str] = {}
        governance_available: dict[str, datetime] = {}
        catalog_payloads: list[dict[str, Any]] = []
        mapping_payloads: list[dict[str, Any]] = []
        formula_payloads: list[dict[str, Any]] = []

        for contract in visible_contracts:
            contract_payload = _contract_definition_payload(contract)
            catalog_payloads.append(contract_payload)
            contract_digests[contract.metric_id] = _content_digest(contract_payload)
            visible_mappings = contract.mappings
            mappings_by_metric[contract.metric_id] = visible_mappings
            if bundle.catalog is None:  # pragma: no cover - bundle invariant.
                raise QueryValidationError("visible contract requires a catalog lane")
            governing_clocks = [bundle.catalog.available_at, contract.rule.available_at]
            for mapping in visible_mappings:
                payload = _mapping_rule_payload(mapping)
                mapping_payloads.append(payload)
                key = (contract.metric_id, mapping.rule.rule_id, mapping.rule.version)
                mapping_digests[key] = _content_digest(payload)
                governing_clocks.extend(
                    (bundle.mapping_pack.available_at, mapping.rule.available_at)  # type: ignore[union-attr]
                )
            formula = contract.formula
            if formula is not None:
                formulas_by_metric[contract.metric_id] = formula
                payload = _formula_rule_payload(formula)
                formula_payloads.append(payload)
                formula_digests[contract.metric_id] = _content_digest(payload)
                governing_clocks.extend(
                    (bundle.formula_pack.available_at, formula.rule.available_at)  # type: ignore[union-attr]
                )
                if formula.not_presented_policy is not None:
                    governing_clocks.append(formula.not_presented_policy.rule.available_at)
            governance_available[contract.metric_id] = max(governing_clocks)

        catalog_digest = (
            _content_digest(
                {
                    "schema": REGISTRY_PROJECTION_SCHEMA,
                    "lane": "catalog",
                    "catalog_id": bundle.catalog.identifier,
                    "contracts": catalog_payloads,
                }
            )
            if catalog_visible
            else None
        )
        mapping_pack_digest = (
            _content_digest(
                {
                    "schema": REGISTRY_PROJECTION_SCHEMA,
                    "lane": "mapping",
                    "mappings": sorted(
                        mapping_payloads,
                        key=lambda item: (
                            item["metric_id"],
                            item["rule"]["rule_id"],
                            item["rule"]["version"],
                        ),
                    ),
                }
            )
            if mapping_pack_visible
            else None
        )
        formula_pack_digest = (
            _content_digest(
                {
                    "schema": REGISTRY_PROJECTION_SCHEMA,
                    "lane": "formula",
                    "formulas": sorted(
                        formula_payloads,
                        key=lambda item: (
                            item["metric_id"],
                            item["rule"]["rule_id"],
                            item["rule"]["version"],
                        ),
                    ),
                }
            )
            if formula_pack_visible
            else None
        )
        receipt_values: dict[str, str] = {}
        if catalog_visible:
            assert catalog_digest is not None
            receipt_values.update(
                {
                "catalog_id": bundle.catalog.identifier,
                "catalog_version": REGISTRY_PROJECTION_VERSION,
                "catalog_content_sha256": catalog_digest,
                }
            )
        if mapping_pack_visible:
            assert mapping_pack_digest is not None
            receipt_values.update(
                {
                "mapping_pack_version": REGISTRY_PROJECTION_VERSION,
                "mapping_pack_content_sha256": mapping_pack_digest,
                }
            )
        if formula_pack_visible:
            assert formula_pack_digest is not None
            receipt_values.update(
                {
                "formula_pack_version": REGISTRY_PROJECTION_VERSION,
                "formula_pack_content_sha256": formula_pack_digest,
                }
            )
        receipt = MappingProxyType(receipt_values)
        return _RegistryProjection(
            recorded_at=policy.recorded_at,
            governance_bundle=bundle,
            contracts_by_metric=MappingProxyType(contracts_by_metric),
            mappings_by_metric=MappingProxyType(mappings_by_metric),
            formulas_by_metric=MappingProxyType(formulas_by_metric),
            contract_digests=MappingProxyType(contract_digests),
            mapping_digests=MappingProxyType(mapping_digests),
            formula_digests=MappingProxyType(formula_digests),
            governance_available_by_metric=MappingProxyType(governance_available),
            catalog_digest=catalog_digest,
            mapping_pack_digest=mapping_pack_digest,
            formula_pack_digest=formula_pack_digest,
            receipt=receipt,
        )

    @staticmethod
    def _fact_metadata_binding(fact: RawFactOccurrence) -> tuple[str, str, str]:
        return (
            fact.source.accession,
            fact.source.document_id,
            fact.source.body_sha256,
        )

    @staticmethod
    def _coerce_bound_metadata(
        value: FilingMetadata | Mapping[str, Any],
        *,
        binding: tuple[str, str, str],
    ) -> FilingMetadata:
        if isinstance(value, FilingMetadata):
            metadata = value
        elif isinstance(value, Mapping):
            allowed = frozenset(
                {
                    "schema",
                    "accession",
                    "document_id",
                    "source_body_sha256",
                    "available_at",
                    "form",
                    "filed_at",
                    "content_sha256",
                }
            )
            raw = _strict_wire_mapping(
                value,
                field_name="filing metadata",
                allowed=allowed,
                required=frozenset({"available_at"}),
            )
            metadata = FilingMetadata(
                schema=raw.get("schema", FILING_METADATA_SCHEMA),
                accession=raw.get("accession", binding[0]),
                document_id=raw.get("document_id", binding[1]),
                source_body_sha256=raw.get("source_body_sha256", binding[2]),
                available_at=raw.get("available_at"),
                form=raw.get("form"),
                filed_at=raw.get("filed_at"),
                content_sha256=raw.get("content_sha256"),
            )
        else:  # pragma: no cover - constructor annotation plus caller guard.
            raise QueryValidationError("filing metadata values must be mappings or FilingMetadata")
        if (metadata.accession, metadata.document_id, metadata.source_body_sha256) != binding:
            raise QueryValidationError(
                "filing metadata binding does not match accession/document/source body"
            )
        return metadata

    def _freeze_filing_metadata(
        self,
        value: Mapping[str, FilingMetadata | Mapping[str, Any]] | None,
    ) -> Mapping[str, FilingMetadata]:
        if value is None:
            return MappingProxyType({})
        if not isinstance(value, Mapping):
            raise QueryValidationError(
                "filing_metadata must be a construction-time mapping; mutable late resolvers are unsupported"
            )
        frozen: dict[str, FilingMetadata] = {}
        bindings = _bounded_collection(
            value.items(),
            field_name="filing_metadata",
            maximum=HARD_MAX_RAW_LEDGER_EVENTS,
        )
        for raw_key, raw_metadata in bindings:
            key = _require_text(raw_key, field_name="filing_metadata key")
            occurrence = self._event_by_occurrence_id.get(key)
            candidates = (
                (occurrence,)
                if occurrence is not None
                else self._events_by_accession.get(key, ())
            )
            if not candidates:
                raise QueryValidationError(
                    f"filing metadata key does not identify a ledger occurrence/accession: {key}"
                )
            bindings = {self._fact_metadata_binding(fact) for fact in candidates}
            if len(bindings) != 1:
                raise QueryValidationError(
                    "accession-level filing metadata spans multiple document bodies; use occurrence IDs"
                )
            binding = next(iter(bindings))
            metadata = self._coerce_bound_metadata(raw_metadata, binding=binding)
            for fact in candidates:
                if fact.accepted_at is not None and metadata.available_at < fact.accepted_at:
                    raise QueryValidationError(
                        "filing metadata available_at cannot precede source acceptance"
                    )
                if metadata.filed_at is not None and fact.accepted_at is not None:
                    if metadata.filed_at > _latest_edgar_filed_date(fact.accepted_at):
                        raise QueryValidationError(
                            "filing metadata filed_at follows the EDGAR filing date of source acceptance"
                        )
                existing = frozen.get(fact.occurrence_id)
                if existing is not None and existing != metadata:
                    raise QueryValidationError(
                        f"conflicting filing metadata for occurrence {fact.occurrence_id}"
                    )
                frozen[fact.occurrence_id] = metadata
        return MappingProxyType(frozen)

    def _entity_for(self, ticker: str | QueryEntity) -> QueryEntity:
        if isinstance(ticker, QueryEntity):
            known = self._entities.get(ticker.ticker)
            # Identity fields only: a caller-supplied entity may carry an
            # issuer SIC the engine map lacks; identity decides the match and
            # the caller's (richer) entity wins evaluation.
            if known is not None and (
                known.ticker != ticker.ticker or known.entity_id != ticker.entity_id
            ):
                raise QueryValidationError(f"ticker maps to a different entity_id: {ticker.ticker}")
            return ticker
        normalized = _require_text(ticker, field_name="ticker").upper()
        entity = self._entities.get(normalized)
        if entity is None:
            raise QueryValidationError(f"unknown ticker/entity: {normalized}")
        return entity

    @staticmethod
    def _period_for(value: PeriodRequest | TypedPeriod | Mapping[str, Any]) -> PeriodRequest:
        if isinstance(value, PeriodRequest):
            return value
        if isinstance(value, TypedPeriod):
            return PeriodRequest.from_typed(value)
        if isinstance(value, Mapping):
            try:
                raw = _strict_wire_mapping(
                    value,
                    field_name="period selector",
                    allowed=frozenset(
                        {
                            "kind",
                            "end",
                            "start",
                            "fiscal_year",
                            "fiscal_quarter",
                            "calendar_kind",
                            "fiscal_year_weeks",
                            "week_count",
                            "label",
                        }
                    ),
                    required=frozenset({"kind", "end"}),
                )
                return PeriodRequest(**raw)
            except QueryError:
                raise
            except (TypeError, ValueError) as exc:
                raise QueryValidationError(f"invalid period selector: {exc}") from exc
        raise QueryValidationError("period must be PeriodRequest, TypedPeriod, or mapping")

    @staticmethod
    def _policy_for(value: QueryPolicy | Mapping[str, Any]) -> QueryPolicy:
        if isinstance(value, QueryPolicy):
            return value
        if isinstance(value, Mapping):
            try:
                raw = _strict_wire_mapping(
                    value,
                    field_name="query policy",
                    allowed=frozenset(
                        {"source_snapshot_at", "recorded_at", "selection"}
                    ),
                    required=frozenset({"source_snapshot_at", "recorded_at"}),
                )
                return QueryPolicy(**raw)
            except QueryError:
                raise
            except (TypeError, ValueError) as exc:
                raise QueryValidationError(f"invalid query policy: {exc}") from exc
        raise QueryValidationError("policy must be QueryPolicy")

    def governed_metric_for_concept(
        self,
        concept_qname: str,
        policy: QueryPolicy | Mapping[str, Any],
        *,
        governance_bundle: GovernanceBundle | None = None,
    ) -> str:
        """Return the sole governed metric for a concept under active governance.

        Supplying a frozen bundle gives source-ingestion adapters the same
        no-live-registry replay boundary as ``query_cell`` and
        ``query_matrix``.
        """
        parts = _qname_parts(_require_text(concept_qname, field_name="concept_qname"))
        if parts is None:
            raise UnsupportedConceptError("concept_qname must have taxonomy:concept form")
        projection = self._projection_for(
            self._policy_for(policy),
            governance_bundle=governance_bundle,
        )
        matches = sorted(
            {
                metric_id
                for metric_id, mappings in projection.mappings_by_metric.items()
                for mapping in mappings
                for alias in mapping.taxonomy_concept_aliases
                if (alias.taxonomy, alias.concept) == parts
            }
        )
        if len(matches) != 1:
            raise UnsupportedConceptError(f"unsupported or ambiguous governed concept: {concept_qname}")
        return matches[0]

    # A concise API spelling for source ingestion/adapters.
    query_concept = governed_metric_for_concept

    def query_cell(
        self,
        ticker: str | QueryEntity,
        metric_id: str,
        period: PeriodRequest | TypedPeriod | Mapping[str, Any],
        policy: QueryPolicy | Mapping[str, Any],
        *,
        governance_bundle: GovernanceBundle | None = None,
    ) -> MetricCell:
        """Evaluate one cell under live or explicitly frozen governance.

        Passing ``GovernanceBundle`` makes that receipt authoritative for this
        query and never looks up the live registry. Constructing the engine
        with a bundle instead of a registry establishes the same frozen mode
        for every query. In either case its ``recorded_at`` must exactly equal
        the policy cutoff.
        """
        entity = self._entity_for(ticker)
        selector = self._period_for(period)
        query_policy = self._policy_for(policy)
        projection = self._projection_for(
            query_policy,
            governance_bundle=governance_bundle,
        )
        metric = _require_text(metric_id, field_name="metric_id")
        if metric not in projection.contracts_by_metric:
            raise UnsupportedMetricError(f"unsupported metric: {metric}")
        cache: dict[tuple[Any, ...], MetricCell] = {}
        return self._evaluate(
            entity,
            metric,
            selector,
            query_policy,
            projection,
            cache,
            stack=(),
        )

    # API aliases make the narrow kernel pleasant to use without broadening its
    # semantics or exporting a second result shape.
    cell = query_cell
    evaluate_cell = query_cell

    def query_matrix(
        self,
        *,
        tickers: Sequence[str | QueryEntity],
        metrics: Sequence[str],
        periods: Sequence[PeriodRequest | TypedPeriod | Mapping[str, Any]],
        policy: QueryPolicy | Mapping[str, Any],
        governance_bundle: GovernanceBundle | None = None,
    ) -> MetricMatrix:
        """Evaluate a bounded matrix under live or explicitly frozen governance."""
        raw_tickers = self._bounded_materialize(
            tickers, maximum=self.bounds.max_tickers, field_name="max_tickers"
        )
        raw_metrics = self._bounded_materialize(
            metrics, maximum=self.bounds.max_metrics, field_name="max_metrics"
        )
        raw_periods = self._bounded_materialize(
            periods, maximum=self.bounds.max_periods, field_name="max_periods"
        )
        entities = tuple(self._entity_for(item) for item in raw_tickers)
        metric_ids = tuple(_require_text(item, field_name="metric_id") for item in raw_metrics)
        selectors = tuple(self._period_for(item) for item in raw_periods)
        query_policy = self._policy_for(policy)
        projection = self._projection_for(
            query_policy,
            governance_bundle=governance_bundle,
        )
        self._validate_matrix_shape(entities, metric_ids, selectors)
        unsupported = sorted(set(metric_ids) - set(projection.contracts_by_metric))
        if unsupported:
            raise UnsupportedMetricError(f"unsupported metric(s): {', '.join(unsupported)}")
        cache: dict[tuple[Any, ...], MetricCell] = {}
        cells = tuple(
            self._evaluate(
                entity,
                metric,
                selector,
                query_policy,
                projection,
                cache,
                stack=(),
            )
            for entity in sorted(entities, key=lambda item: (item.ticker, item.entity_id))
            for metric in sorted(metric_ids)
            for selector in sorted(selectors, key=lambda item: item.key)
        )
        return MetricMatrix(
            governance_bundle=projection.governance_bundle,
            policy=query_policy,
            entities=entities,
            metric_ids=metric_ids,
            periods=selectors,
            cells=cells,
        )

    query = query_matrix
    matrix = query_matrix

    @staticmethod
    def _bounded_materialize(
        values: Sequence[Any], *, maximum: int, field_name: str
    ) -> tuple[Any, ...]:
        """Consume at most ``maximum + 1`` even when a Sequence lies about length."""
        if isinstance(values, (str, bytes, bytearray)):
            raise QueryValidationError(f"{field_name} must be a sequence of items")
        try:
            count = len(values)
        except TypeError:
            count = None
        except QueryError:
            raise
        except Exception as exc:
            raise QueryValidationError(f"{field_name} has an invalid length contract") from exc
        if count is not None and count > maximum:
            raise QueryBoundsError(f"{field_name} exceeds the configured bound {maximum}")
        try:
            materialized = tuple(islice(iter(values), maximum + 1))
        except QueryError:
            raise
        except Exception as exc:
            raise QueryValidationError(f"{field_name} must be a bounded iterable") from exc
        if len(materialized) > maximum:
            raise QueryBoundsError(f"{field_name} exceeds the configured bound {maximum}")
        return materialized

    def _validate_matrix_shape(
        self,
        entities: Sequence[QueryEntity],
        metric_ids: Sequence[str],
        periods: Sequence[PeriodRequest],
    ) -> None:
        if not entities:
            raise QueryBoundsError("at least one ticker/entity is required")
        if not metric_ids:
            raise QueryBoundsError("at least one metric is required")
        if not periods:
            raise QueryBoundsError("at least one period is required")
        if len(entities) > self.bounds.max_tickers:
            raise QueryBoundsError(f"ticker count exceeds max_tickers={self.bounds.max_tickers}")
        if len(metric_ids) > self.bounds.max_metrics:
            raise QueryBoundsError(f"metric count exceeds max_metrics={self.bounds.max_metrics}")
        if len(periods) > self.bounds.max_periods:
            raise QueryBoundsError(f"period count exceeds max_periods={self.bounds.max_periods}")
        if len({item.ticker for item in entities}) != len(entities):
            raise QueryBoundsError("tickers must be unique")
        if len({item.entity_id for item in entities}) != len(entities):
            raise QueryBoundsError("entity_ids must be unique")
        if len(set(metric_ids)) != len(metric_ids):
            raise QueryBoundsError("metrics must be unique")
        if len({item.key for item in periods}) != len(periods):
            raise QueryBoundsError("periods must be unique")
        cells = len(entities) * len(metric_ids) * len(periods)
        if cells > self.bounds.max_cells:
            raise QueryBoundsError(f"cell count {cells} exceeds max_cells={self.bounds.max_cells}")

    @staticmethod
    def _opaque_provenance(policy: QueryPolicy, *, reason: str) -> CellProvenance:
        """A historical no-result that deliberately carries no future receipt."""
        return CellProvenance(
            kind=ProvenanceKind.OPAQUE,
            evaluation_policy=None,
            policy=policy.selection,
            source_snapshot_at=policy.source_snapshot_at,
            recorded_cutoff_at=policy.recorded_at,
            reason=reason,
        )

    def _base_provenance(
        self,
        projection: _RegistryProjection,
        policy: QueryPolicy,
        contract: MetricContract,
        *,
        kind: ProvenanceKind = ProvenanceKind.DIRECT,
        reason: str | None = None,
        **overrides: Any,
    ) -> CellProvenance:
        values: dict[str, Any] = {
            "kind": kind,
            "evaluation_policy": EvaluationPolicy.ON_DEMAND_CUTOFF_PROJECTION,
            "policy": policy.selection,
            "source_snapshot_at": policy.source_snapshot_at,
            "recorded_cutoff_at": policy.recorded_at,
            "metric_rule_id": contract.rule.rule_id,
            "metric_rule_version": contract.rule.version,
            "metric_rule_digest": projection.contract_digests[contract.metric_id],
            "catalog_id": projection.receipt["catalog_id"],
            "catalog_version": REGISTRY_PROJECTION_VERSION,
            "catalog_digest": projection.catalog_digest,
            "confidence": contract.confidence,
            "governance_available_at": projection.governance_available_by_metric[
                contract.metric_id
            ],
            "reason": reason,
        }
        if "mapping_pack_content_sha256" in projection.receipt:
            values.update(
                {
                    "mapping_pack_version": REGISTRY_PROJECTION_VERSION,
                    "mapping_pack_digest": projection.mapping_pack_digest,
                }
            )
        if kind is ProvenanceKind.DIRECT:
            visible_mappings = projection.mappings_by_metric.get(contract.metric_id, ())
            values.update(
                {
                    "mapping_rule_ids": tuple(
                        mapping.rule.rule_id for mapping in visible_mappings
                    ),
                    "mapping_rule_versions": tuple(
                        mapping.rule.version for mapping in visible_mappings
                    ),
                    "mapping_digests": tuple(
                        projection.mapping_digests[
                            (
                                contract.metric_id,
                                mapping.rule.rule_id,
                                mapping.rule.version,
                            )
                        ]
                        for mapping in visible_mappings
                    ),
                }
            )
        if "formula_pack_content_sha256" in projection.receipt:
            values.update(
                {
                    "formula_pack_version": REGISTRY_PROJECTION_VERSION,
                    "formula_pack_digest": projection.formula_pack_digest,
                }
            )
        if kind is ProvenanceKind.FORMULA:
            formula = projection.formulas_by_metric.get(contract.metric_id)
            if formula is None:
                raise QueryValidationError("formula provenance requires a cutoff-visible formula rule")
            values.update(
                {
                    "formula_rule_id": formula.rule.rule_id,
                    "formula_rule_version": formula.rule.version,
                    "formula_digest": projection.formula_digests[contract.metric_id],
                }
            )
        values.update(overrides)
        return CellProvenance(**values)

    def _new_cell(
        self,
        *,
        entity: QueryEntity,
        metric_id: str,
        period: PeriodRequest,
        state: CellState,
        value: Decimal | None,
        unit: str | None,
        provenance: CellProvenance,
        dependency_cells: Sequence[MetricCell] = (),
        governance_bundle: GovernanceBundle,
        reason: str | None = None,
    ) -> MetricCell:
        dependencies = _bounded_collection(
            dependency_cells,
            field_name="formula dependency cells",
            maximum=HARD_MAX_RECEIPT_NODES - 1,
        )
        if any(not isinstance(item, MetricCell) for item in dependencies):
            raise QueryValidationError("formula dependency cells must be MetricCell receipts")
        if not isinstance(governance_bundle, GovernanceBundle):  # pragma: no cover - private caller invariant.
            raise QueryValidationError("cell construction requires a GovernanceBundle")
        bundle = governance_bundle
        node_by_id: dict[str, CellNode] = {}
        for dependency in dependencies:
            if dependency.governance_bundle.content_id != bundle.content_id:
                raise QueryValidationError("formula dependencies use a different governance bundle")
            for node in dependency.nodes:
                existing = node_by_id.get(node.cell_id)
                if existing is not None and existing != node:
                    raise QueryValidationError("formula dependencies contain conflicting cell IDs")
                node_by_id[node.cell_id] = node
                if len(node_by_id) > HARD_MAX_RECEIPT_NODES - 1:
                    raise QueryBoundsError(
                        f"formula receipt exceeds {HARD_MAX_RECEIPT_NODES} unique nodes"
                    )
        return MetricCell(
            governance_bundle=bundle,
            ticker=entity.ticker,
            entity_id=entity.entity_id,
            metric_id=metric_id,
            period=period,
            state=state,
            value=value,
            unit=unit,
            provenance=provenance,
            dependency_nodes=tuple(node_by_id.values()),
            reason=reason,
        )

    def _evaluate(
        self,
        entity: QueryEntity,
        metric_id: str,
        period: PeriodRequest,
        policy: QueryPolicy,
        projection: _RegistryProjection,
        cache: dict[tuple[Any, ...], MetricCell],
        *,
        stack: tuple[str, ...],
    ) -> MetricCell:
        cache_key = (
            entity.entity_id,
            metric_id,
            period.key,
            policy.selection.value,
            utc_text(policy.source_snapshot_at),
            utc_text(policy.recorded_at),
        )
        existing = cache.get(cache_key)
        if existing is not None:
            return existing
        contract = projection.contracts_by_metric.get(metric_id)
        if contract is None:
            reason = "governance unavailable at recorded_at cutoff"
            result = self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=metric_id,
                period=period,
                state=CellState.MISSING,
                value=None,
                unit=None,
                provenance=self._opaque_provenance(policy, reason=reason),
                reason=reason,
            )
            cache[cache_key] = result
            return result
        # Issuer qualification stage (S1-b): the pure applicability gate from
        # the metric registry, fired after contract resolution and before any
        # cycle guard, dispatch, or source read.  Default-inert by
        # construction — an empty class policy admits every issuer, and
        # formula=None keeps the denominator branch out of this stage (the
        # formula is qualified in _evaluate_formula once its dependency values
        # exist).  Period-first precedence: the receipt validators weigh a
        # period-contract rejection above an issuer-class refusal, so when the
        # requested period violates the contract this stage stands down and
        # the direct/formula period-rejection paths below emit the cell.
        issuer_class = (
            issuer_class_for_sic(entity.issuer_sic) if entity.issuer_sic is not None else None
        )
        qualification = (
            None
            if self._period_contract_error(contract, period) is not None
            else qualify_metric(contract, None, issuer_class, {})
        )
        if qualification is not None and qualification.state != "applicable":
            reason = qualification.reason
            provenance_overrides: dict[str, Any] = {}
            if issuer_class is not None:
                provenance_overrides["issuer_class"] = issuer_class
                provenance_overrides[
                    "issuer_class_basis"
                ] = contract.applicability.issuer_class_basis
            result = self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=metric_id,
                period=period,
                state=(
                    CellState.NOT_APPLICABLE
                    if qualification.state == "not_applicable"
                    else CellState.NOT_EVALUABLE
                ),
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    kind=(
                        ProvenanceKind.FORMULA
                        if metric_id in projection.formulas_by_metric
                        else ProvenanceKind.DIRECT
                    ),
                    reason=reason,
                    **provenance_overrides,
                ),
                reason=reason,
            )
            cache[cache_key] = result
            return result
        if metric_id in stack:
            # Registry construction rejects formula cycles; retain a safe guard
            # here so a hand-built registry cannot recurse forever.
            reason = f"formula dependency cycle at {metric_id}"
            result = self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    kind=(
                        ProvenanceKind.FORMULA
                        if metric_id in projection.formulas_by_metric
                        else ProvenanceKind.DIRECT
                    ),
                    reason=reason,
                ),
                reason=reason,
            )
            cache[cache_key] = result
            return result
        if contract.formula is None:
            result = self._evaluate_direct(entity, contract, period, policy, projection)
        else:
            result = self._evaluate_formula(
                entity,
                contract,
                period,
                policy,
                projection,
                cache,
                stack + (metric_id,),
            )
        cache[cache_key] = result
        return result

    def _period_contract_error(self, contract: MetricContract, period: PeriodRequest) -> str | None:
        return _period_contract_error_for(contract, period)

    def _direct_rule_available_at(self, contract: MetricContract, mapping: MappingRule) -> datetime:
        # Rule availability is a system knowledge gate, not a source-event
        # claim.  It is intentionally separate from the raw source clocks.
        return max(contract.rule.available_at, mapping.rule.available_at)

    def _formula_rule_available_at(self, contract: MetricContract, formula: FormulaRule) -> datetime:
        return _formula_governed_available_at(contract, formula)

    def _aliases_for_period(
        self,
        contract: MetricContract,
        period: PeriodRequest,
        projection: _RegistryProjection,
    ) -> tuple[_AliasCandidate, ...]:
        # Wave 3A boundary: the raw v1 occurrence does not yet carry an
        # attested taxonomy-version field. Until that source contract exists,
        # registry applicability remains a requested-period guard only; it
        # must not be misrepresented as source-taxonomy attestation.
        tax_year = period.normalized.end.year
        values = [
            _AliasCandidate(mapping=mapping, alias=alias)
            for mapping in projection.mappings_by_metric.get(contract.metric_id, ())
            for alias in mapping.taxonomy_concept_aliases
            if alias.taxonomy_version_start <= tax_year <= alias.taxonomy_version_end
        ]
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.alias.priority,
                    item.alias.taxonomy,
                    item.alias.concept,
                    item.mapping.rule.rule_id,
                ),
            )
        )

    def _events_for_alias(
        self,
        entity: QueryEntity,
        alias: ConceptAlias,
        period: PeriodRequest,
    ) -> tuple[RawFactOccurrence, ...]:
        return self._events_by_entity_qname_period.get(
            (
                entity.entity_id,
                f"{alias.taxonomy}:{alias.concept}",
                _request_period_index_key(period),
            ),
            (),
        )

    @staticmethod
    def _context_matches_period(fact: RawFactOccurrence, period: PeriodRequest) -> bool:
        requested = period.normalized
        context = fact.context
        if requested.kind is PeriodKind.INSTANT:
            return context.instant == requested.end
        return context.start == requested.start and context.end == requested.end

    @staticmethod
    def _fact_dimensions_allowed(fact: RawFactOccurrence, contract: MetricContract) -> bool:
        # The ordinary registry remains consolidated-only.  The sole separate
        # evidence bridge admits *only* Company Facts rows whose dimensional
        # scope is explicitly unknown; it does not infer that an empty context
        # means consolidated.
        mode = contract.dimensional_profile.mode
        if mode == "consolidated_only":
            return (
                fact.dimensions_known
                and not fact.context.explicit_dimensions
                and not fact.context.typed_dimensions
            )
        if mode == "dimensions_unknown_only":
            return (
                fact.source.source == "sec-companyfacts"
                and fact.dimensions_known is False
                and not fact.context.explicit_dimensions
                and not fact.context.typed_dimensions
            )
        return False

    @staticmethod
    def _fact_unit_allowed(fact: RawFactOccurrence, contract: MetricContract) -> bool:
        return _canonical_raw_unit(fact) in set(contract.units)

    def _metadata_for(
        self,
        fact: RawFactOccurrence,
        policy: QueryPolicy,
    ) -> FilingMetadata | None:
        metadata = self._filing_metadata_by_occurrence.get(fact.occurrence_id)
        if metadata is not None and metadata.available_at <= policy.recorded_at:
            return metadata
        # A document filename is not an attested SEC form.  More importantly,
        # absence is not a retained negative metadata artifact: emit no digest
        # or availability clock until an explicitly bound witness is visible.
        return None

    @staticmethod
    def _admit_not_presented(
        pack: NotPresentedPack | None,
        packages: Iterable[Any],
    ) -> tuple[NotPresentedPack | None, Mapping[str, Any]]:
        if isinstance(packages, (str, bytes, bytearray, Mapping)):
            raise QueryValidationError("filing_packages must be a bounded collection")
        materialized = tuple(islice(packages, HARD_MAX_NOT_PRESENTED_PACKAGES + 1))
        if len(materialized) > HARD_MAX_NOT_PRESENTED_PACKAGES:
            raise QueryValidationError("filing_packages exceed the hard package bound")
        if pack is None:
            if materialized:
                raise QueryValidationError("filing_packages require a not_presented_pack")
            return None, _EMPTY_PACKAGE_MAP
        if not isinstance(pack, NotPresentedPack):
            raise QueryValidationError("not_presented_pack must be a loaded NP rule pack")
        by_accession: dict[str, Any] = {}
        for package in materialized:
            manifest = getattr(package, "manifest", None)
            accession = manifest.get("accession") if isinstance(manifest, Mapping) else None
            if not isinstance(accession, str) or not accession:
                raise QueryValidationError("filing package has no accession identity")
            if accession in by_accession:
                raise QueryValidationError(f"duplicate filing package for {accession}")
            by_accession[accession] = package
        return pack, MappingProxyType(by_accession)

    @staticmethod
    def _np_consolidated_usd(fact: RawFactOccurrence) -> bool:
        return bool(
            fact.dimensions_known
            and not fact.context.explicit_dimensions
            and not fact.context.typed_dimensions
            and _canonical_raw_unit(fact) == "USD"
        )

    def _not_presented_slot(
        self,
        entity_id: str,
        parent_tiers: Sequence[Sequence[str]],
        period: PeriodRequest,
        policy: QueryPolicy,
    ) -> tuple[str, dict[str, Decimal]] | None:
        """Anchor the slot to one filing and build its exact context fact map.

        The anchor is the filing whose consolidated USD parent total the
        ordinary selector would pick for this period; the first parent tier
        with a selectable total decides.  Two tier members anchored to
        different filings, a bound overflow, or two different values for one
        concept in the anchor filing all fail closed (``None``: stay absent).
        """
        period_key = _request_period_index_key(period)
        anchor: str | None = None
        for tier in parent_tiers:
            accessions: set[str] = set()
            for concept in tier:
                events = self._events_by_entity_qname_period.get(
                    (entity_id, concept, period_key), ()
                )
                visible, over_bound = self._bounded_visible_events(events, policy)
                if over_bound:
                    return None
                eligible = tuple(item for item in visible if self._np_consolidated_usd(item))
                if not eligible:
                    continue
                selection = self._select_source_group(eligible, policy)
                if selection.state is not CellState.VALUE or selection.occurrence is None:
                    continue
                accessions.add(selection.occurrence.source.accession)
            if len(accessions) > 1:
                return None
            if accessions:
                anchor = accessions.pop()
                break
        if anchor is None:
            return None
        facts: dict[str, Decimal] = {}
        for item in self._events_by_accession.get(anchor, ()):
            if (
                item.source.entity_id != entity_id
                or not self._context_matches_period(item, period)
                or not self._event_temporally_eligible(item, policy)
                or not self._np_consolidated_usd(item)
                or item.is_withdrawn
                or item.is_nil
                or item.parsed_value is None
            ):
                continue
            try:
                value = Decimal(str(item.parsed_value))
            except (InvalidOperation, ValueError):
                return None
            if not value.is_finite():
                return None
            prior = facts.get(item.concept_qname)
            if prior is not None and prior != value:
                return None
            facts[item.concept_qname] = value
        return anchor, facts

    def _not_presented_verdict_for(
        self,
        entity_id: str,
        metric_id: str,
        period: PeriodRequest,
        policy: QueryPolicy,
    ) -> NotPresentedEvidence | None:
        pack = self._not_presented_pack
        if pack is None or policy.selection is BitemporalPolicy.LATEST_RESTATED:
            return None
        rule = pack.visible_rule(metric_id, recorded_at=policy.recorded_at)
        if rule is None:
            return None
        slot = self._not_presented_slot(entity_id, rule.parent_tiers, period, policy)
        if slot is None:
            return None
        accession, facts = slot
        package = self._packages_by_accession.get(accession)
        if package is None:
            return None
        calculation, presentation = package_linkbases(package)
        try:
            verdict = evaluate_not_presented_package(
                pack,
                metric_id,
                calculation=calculation,
                presentation=presentation,
                facts_in_context=facts,
                recorded_at=policy.recorded_at,
                accession=accession,
            )
        except NotPresentedError:
            return None
        if not verdict.is_not_presented:
            return None
        return NotPresentedEvidence.from_verdict(verdict)

    def verify_not_presented(self, cell: "MetricCell | CellNode") -> None:
        """Recompute a ``not_presented`` cell from the admitted package bytes.

        Refuses a cell whose evidence (rule identity, pack digest, linkbase
        digests, counts, accession) does not equal a fresh recomputation
        under the cell's own cutoffs and its own anchor filing.
        """
        provenance = cell.provenance
        evidence = provenance.not_presented
        if (
            evidence is None
            or cell.state is not CellState.NOT_APPLICABLE
            or cell.reason != NOT_PRESENTED_REASON
        ):
            raise QueryValidationError("cell is not a not-presented verdict")
        pack = self._not_presented_pack
        if pack is None:
            raise QueryValidationError("no not-presented pack is admitted")
        if provenance.policy is BitemporalPolicy.LATEST_RESTATED:
            raise QueryValidationError("not-presented evidence contradicts latest_restated policy")
        policy = QueryPolicy(
            source_snapshot_at=provenance.source_snapshot_at,
            recorded_at=provenance.recorded_cutoff_at,
            selection=provenance.policy,
        )
        package = self._packages_by_accession.get(evidence.accession)
        if package is None:
            raise QueryValidationError("not-presented evidence names no admitted package")
        slot = self._not_presented_slot(
            cell.entity_id,
            self._np_parent_tiers(pack, cell.metric_id),
            cell.period,
            policy,
        )
        if slot is None or slot[0] != evidence.accession:
            raise QueryValidationError("not-presented evidence does not anchor to its filing")
        calculation, presentation = package_linkbases(package)
        try:
            verify_not_presented_evidence(
                pack,
                cell.metric_id,
                {"na_basis": provenance.na_basis, **evidence.to_dict()},
                calculation=calculation,
                presentation=presentation,
                facts_in_context=slot[1],
                recorded_at=policy.recorded_at,
            )
        except NotPresentedError as exc:
            raise QueryValidationError(str(exc)) from exc

    @staticmethod
    def _np_parent_tiers(
        pack: NotPresentedPack, metric_id: str
    ) -> tuple[tuple[str, ...], ...]:
        rule = pack.rules.get(metric_id)
        return rule.parent_tiers if rule is not None else ()

    def _admit_lineage_evidence(
        self,
        lineage_evidence: Iterable[LineageEvidenceReceipt],
    ) -> Mapping[str, tuple[LineageEvidenceReceipt, ...]]:
        """Fail-closed admission of a runtime cross-filing lineage bundle.

        Sol amendment 6: runtime evidence carries **only accepted positive
        immutable relations**.  A refusal row, a non-confirmation relation, a
        receipt for a fact this ledger does not contain, or a duplicated
        parent/child edge is a malformed provider, not a smaller answer.
        """
        if isinstance(lineage_evidence, (str, bytes, bytearray)):
            raise LineageEvidenceError("lineage_evidence must be a bounded collection")
        receipts = _bounded_collection(
            lineage_evidence,
            field_name="lineage_evidence",
            maximum=MAX_LINEAGE_RECEIPTS,
        )
        if not receipts:
            return MappingProxyType({})
        by_key: dict[str, list[LineageEvidenceReceipt]] = {}
        seen_edges: set[tuple[str, str]] = set()
        for receipt in receipts:
            if not isinstance(receipt, LineageEvidenceReceipt):
                raise LineageEvidenceError("lineage_evidence must contain receipts")
            if not receipt.is_positive_confirmation:
                raise LineageEvidenceError(
                    "runtime lineage evidence admits accepted positive relations only"
                )
            edge = (receipt.parent_occurrence_id, receipt.child_occurrence_id)
            if edge in seen_edges:
                raise LineageEvidenceError("duplicate lineage evidence edge")
            seen_edges.add(edge)
            parent = self._event_by_occurrence_id.get(receipt.parent_occurrence_id)
            child = self._event_by_occurrence_id.get(receipt.child_occurrence_id)
            if parent is None or child is None:
                raise LineageEvidenceError("lineage evidence references an unknown occurrence")
            if parent.logical_key != receipt.logical_key or child.logical_key != receipt.logical_key:
                raise LineageEvidenceError("lineage evidence logical_key does not bind its facts")
            # The full per-accession groups the mint path groups by — the
            # same groups the envelope pin and the payload bind re-derive
            # from below, never a cutoff-filtered subset.
            parent_group = self._accession_group(parent)
            child_group = self._accession_group(child)
            # FIF T1b: pin the receipt ENVELOPE before any payload work.  A
            # correctly recomputed digest over genuine evidence still says
            # nothing about the envelope around it: a backdated
            # ``system_available_at`` (below the mint floor) or a foreign
            # rule id/version would make the receipt visible under policies
            # where the honest mint is not, flipping lineage answers.  The
            # named refusal is an engine-level diagnostic, never a response
            # body, and admission fail-closes the whole provider bundle.
            envelope_refusal = receipt_envelope_refusal(receipt, parent_group, child_group)
            if envelope_refusal is not None:
                raise LineageEvidenceError(
                    "lineage evidence envelope is not the one the current rule "
                    f"mints ({envelope_refusal})"
                )
            evidence = receipt.positive_evidence or {}
            # FIF A01/A11: with a source namespace map, the attested URI
            # pair must be the source's, keyed exactly as the mint keyed it
            # (the canonical representative of each full group).
            if not self._taxonomy_uris_match_source(
                _canonical_duplicate_representative(parent_group),
                _canonical_duplicate_representative(child_group),
                evidence,
            ):
                raise LineageEvidenceError(
                    "lineage evidence taxonomy namespace is not the source's "
                    f"({REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE})"
                )
            # FIF T1: bind the WHOLE payload, not just the edge.  A receipt
            # digest only proves internal self-consistency, so a forged
            # bundle with a correctly recomputed receipt_id must still equal
            # what the canonical builder reconstructs from THIS ledger before
            # it is ever visible to a selection.  Admission has no policy, so
            # the groups are the full per-accession groups the constructor
            # can already resolve here; the cutoff-filtered re-derivation
            # runs per query in ``_receipt_still_proves_confirmation``.  The
            # taxonomy URI pair is the mint-time attestation the canonical
            # ledger cannot re-derive, reconstructed in its canonical equal
            # form so a one-sided URI edit is an evidence mismatch too.
            expected = self._expected_positive_evidence(
                parent_group,
                child_group,
                common_taxonomy_uri=evidence.get("parent_taxonomy_uri"),
            )
            if _freeze_evidence(expected) != receipt.positive_evidence:
                raise LineageEvidenceError(
                    "lineage evidence positive payload does not match the current "
                    f"ledger ({REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE})"
                )
            # Re-prove the edge against the ledger now, not only per query. A
            # bundle assembled without ``derive_confirmation_receipts`` cannot
            # smuggle in an edge the v1 rule would never have minted.
            if evaluate_confirmation(
                parent_group,
                child_group,
                parent_taxonomy_uri=evidence.get("parent_taxonomy_uri"),
                child_taxonomy_uri=evidence.get("child_taxonomy_uri"),
                require_taxonomy_uri=True,
            ) is not None:
                raise LineageEvidenceError("lineage evidence is not a v1 positive for this ledger")
            by_key.setdefault(receipt.logical_key, []).append(receipt)
        for key, values in by_key.items():
            versions = {receipt.evidence_rule_version for receipt in values}
            if len(versions) != 1:
                raise LineageEvidenceError(
                    "lineage evidence mixes confirmation rule versions for one logical key"
                )
            if values[0].evidence_rule_version != CONFIRMATION_CHAIN_RULE_VERSION:
                accessions: set[str] = set()
                for receipt in values:
                    for occurrence_id in (receipt.parent_occurrence_id, receipt.child_occurrence_id):
                        accessions.add(self._event_by_occurrence_id[occurrence_id].source.accession)
                if len(accessions) > 2:
                    # v1 admits exactly one parent and one child per logical key.
                    # Chained receipts across three filings have no unique parent.
                    raise LineageEvidenceError(
                        "lineage evidence spans more than two filings for one logical key"
                    )
                continue
            # FIF S2 (A05): the versioned v2 chain rule admits 3+ filings of one
            # logical key, but only as ONE strictly ordered adjacent path over
            # every filing the ledger holds for the key — L is rebuilt from the
            # dataset's own events via ``_event_by_occurrence_id``.  A skip
            # edge, a fork, a cycle, or a missing accession is a malformed
            # provider, not a smaller answer.
            chain_by_accession: dict[str, list[RawFactOccurrence]] = {}
            for event in self._event_by_occurrence_id.values():
                if event.logical_key == key:
                    chain_by_accession.setdefault(event.source.accession, []).append(event)
            _times, ordered_accessions = _chain_accepted_by_accession(
                chain_by_accession
            )
            if (
                len(chain_by_accession) < 3
                or ordered_accessions is None
                or len(values) != len(chain_by_accession) - 1
            ):
                raise LineageEvidenceError(
                    "chain lineage evidence must form one strictly ordered path "
                    "across every filing of its logical key"
                )
            edge_pairs = sorted(
                (
                    self._event_by_occurrence_id[receipt.parent_occurrence_id].source.accession,
                    self._event_by_occurrence_id[receipt.child_occurrence_id].source.accession,
                )
                for receipt in values
            )
            expected_pairs = sorted(
                (ordered_accessions[index], ordered_accessions[index + 1])
                for index in range(len(ordered_accessions) - 1)
            )
            if edge_pairs != expected_pairs:
                raise LineageEvidenceError(
                    "chain lineage evidence must form one strictly ordered path "
                    "across every filing of its logical key"
                )
        return MappingProxyType(
            {
                key: tuple(sorted(values, key=lambda item: item.receipt_id))
                for key, values in by_key.items()
            }
        )

    def _accession_group(
        self,
        fact: RawFactOccurrence,
    ) -> tuple[RawFactOccurrence, ...]:
        """Every occurrence of this fact's logical key inside its own filing."""
        key = (fact.source.entity_id, fact.concept_qname, _fact_period_index_key(fact))
        return tuple(
            item
            for item in self._events_by_entity_qname_period.get(key, ())
            if item.source.accession == fact.source.accession
            and item.logical_key == fact.logical_key
        )

    def applied_lineage_evidence(
        self,
        matrix: MetricMatrix,
    ) -> tuple[LineageEvidenceReceipt, ...]:
        """Confirmation receipts that actually support this matrix's answers.

        Read-only and idempotent: it re-derives eligibility under the matrix's
        own policy rather than recording hidden state during evaluation. The
        result is the honest answer to "which other filing supports this
        number", and it is deliberately **not** folded into
        ``source_occurrence_ids`` — that tuple feeds revision-adjacent packet
        machinery, and a confirmation is lineage, never a reported revision.
        """
        if not self._confirmations_by_logical_key:
            return ()
        policy = matrix.policy
        selected: set[str] = set()
        for cell in matrix.cells:
            provenance = getattr(cell, "provenance", None)
            if provenance is None or cell.state is not CellState.VALUE:
                continue
            selected.update(provenance.source_occurrence_ids or ())
        if not selected:
            return ()
        applied: dict[str, LineageEvidenceReceipt] = {}
        for occurrence_id in sorted(selected):
            fact = self._event_by_occurrence_id.get(occurrence_id)
            if fact is None:
                continue
            for receipt in self._confirmations_by_logical_key.get(fact.logical_key, ()):
                if occurrence_id not in (
                    receipt.parent_occurrence_id,
                    receipt.child_occurrence_id,
                ):
                    continue
                if self._receipt_still_proves_confirmation(receipt, policy) is not None:
                    continue
                applied[receipt.receipt_id] = receipt
        return tuple(applied[key] for key in sorted(applied))

    def _expected_positive_evidence(
        self,
        parent_group: Sequence[RawFactOccurrence],
        child_group: Sequence[RawFactOccurrence],
        *,
        common_taxonomy_uri: str | None,
    ) -> Mapping[str, Any]:
        """The canonical positive-evidence payload the current groups carry.

        FIF T1: a receipt's internal digest proves only self-consistency,
        never that its source fields still describe the current eligible
        ledger.  This rebuilds the expected payload with the canonical
        builder from ``lineage_evidence`` — the same builder
        ``derive_confirmation_receipts`` minted the receipt with — so the
        comparisons in admission and in ``_receipt_still_proves_confirmation``
        bind all eighteen fields to live facts.

        The two ``*_taxonomy_uri`` fields are the one thing the canonical
        ledger cannot re-derive (it retains ``us-gaap:Assets``, not the
        original Clark namespace), so the caller passes the receipt's
        attested URI, which is only reached after that URI has passed the
        guard-11 namespace gauntlet.  Guard 11 mints both URI fields from one
        original namespace and requires them equal, so the canonical expected
        form carries that one common URI on both sides; a receipt that edited
        only one of the two fields fails the payload equality instead of
        merely the namespace check.
        """
        return _positive_evidence_payload(
            parent_group,
            child_group,
            parent_taxonomy_uri=common_taxonomy_uri,
            child_taxonomy_uri=common_taxonomy_uri,
        )

    def _receipt_still_proves_confirmation(
        self,
        receipt: LineageEvidenceReceipt,
        policy: QueryPolicy,
    ) -> str | None:
        """Re-prove a receipt against live facts and both cutoffs.

        A receipt is an assertion about source facts, never a cached answer.
        Every query re-derives guards 1-10 and 12 from the current ledger and
        re-checks the receipt's asserted evidence against it, so mutating a
        confirmed value refuses the relation and restores the unlinked
        ``NOT_EVALUABLE`` state instead of silently rescuing it.

        Returns ``None`` while the receipt still proves its confirmation, else
        the refusal reason the receipt is reported unavailable with.  The
        reason is an engine-level diagnostic only and never enters a response
        body.  Any mismatch between the receipt's positive evidence and the
        current eligible ledger — accessions, document ids, source occurrence
        keys, parsed value, accuracy tokens, dimensional scope, nil state,
        clocks, concept, or the attested namespace pair — is classified
        ``evidence_does_not_match_source``.  A receipt whose envelope is not
        the one the current rule mints — foreign rule id/version, or a system
        availability backdated below the mint floor — is classified
        ``receipt_rule_mismatch`` / ``receipt_system_availability_backdated``.
        """
        if receipt.source_known_at > policy.source_snapshot_at:
            return REFUSAL_RECEIPT_NOT_YET_SOURCE_VISIBLE
        if receipt.system_available_at > policy.recorded_at:
            return REFUSAL_RECEIPT_NOT_YET_SYSTEM_AVAILABLE
        parent = self._event_by_occurrence_id.get(receipt.parent_occurrence_id)
        child = self._event_by_occurrence_id.get(receipt.child_occurrence_id)
        if parent is None or child is None:
            return REFUSAL_MISSING_OCCURRENCE
        # A confirmation cannot make an otherwise invisible fact visible.
        if not self._event_temporally_eligible(parent, policy):
            return REFUSAL_OCCURRENCE_NOT_TEMPORALLY_ELIGIBLE
        if not self._event_temporally_eligible(child, policy):
            return REFUSAL_OCCURRENCE_NOT_TEMPORALLY_ELIGIBLE
        evidence = receipt.positive_evidence or {}
        parent_group = self._visible_accession_group(parent, policy)
        child_group = self._visible_accession_group(child, policy)
        # FIF T1b: pin the envelope against the SAME full groups the mint
        # path groups by — never the cutoff-filtered subsets above, whose
        # floor can only be weaker than the one the receipt was minted
        # under.  Passing the policy cutoffs merely means the receipt is not
        # claiming to be newer than the policy; it must additionally not be
        # OLDER than the lawful floor, or the relation would be visible
        # under policies the honest mint cannot serve.
        envelope_refusal = receipt_envelope_refusal(
            receipt,
            self._accession_group(parent),
            self._accession_group(child),
        )
        if envelope_refusal is not None:
            return envelope_refusal
        refusal = evaluate_confirmation(
            parent_group,
            child_group,
            require_taxonomy_uri=False,
        )
        if refusal is not None:
            return refusal
        # Guard 11 (original source taxonomy namespace/version) is attested by
        # the mint-time receipt because the canonical ledger does not retain the
        # original Clark URI.  Re-prove that the facts the receipt was minted
        # against are still exactly these facts.
        representative = _canonical_duplicate_representative(child_group)
        parent_representative = _canonical_duplicate_representative(parent_group)
        parent_uri = evidence.get("parent_taxonomy_uri")
        child_uri = evidence.get("child_taxonomy_uri")
        if not parent_uri or parent_uri != child_uri:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        # An attested URI is only believed when it is a policy-approved standard
        # namespace whose prefix matches the concept the ledger still carries.
        # Two matching but invented URIs are not evidence of anything.
        if not _approved_taxonomy_uri(parent_uri, parent_representative.concept_qname):
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if not _approved_taxonomy_uri(child_uri, representative.concept_qname):
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if parent_representative.occurrence_id != receipt.parent_occurrence_id:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if representative.occurrence_id != receipt.child_occurrence_id:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        # FIF A01/A11: a policy-approved URI pair is still only an
        # attestation; with a source namespace map it must be the source's.
        if not self._taxonomy_uris_match_source(
            parent_representative, representative, evidence
        ):
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("concept_qname") != representative.concept_qname:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("parsed_value") != decimal_text(representative.parsed_value):
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("decimals") != representative.decimals:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("precision") != representative.precision:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("is_nil") is not representative.is_nil:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("parent_accession") != parent_representative.source.accession:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if evidence.get("child_accession") != representative.source.accession:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        if receipt.source_known_at != max(
            parent_representative.accepted_at, representative.accepted_at
        ):
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        # FIF T1 full bind: after the identity, namespace and cutoff checks,
        # the ENTIRE payload must still equal what the canonical builder
        # reconstructs from the current eligible groups — including the fields
        # the named checks above never reached (document ids, source
        # occurrence keys, dimensions_known, the per-filing accepted/recorded
        # clocks).  A forged payload with a correctly recomputed receipt_id —
        # a valid digest over invented evidence — fails here.
        expected = self._expected_positive_evidence(
            parent_group,
            child_group,
            common_taxonomy_uri=parent_uri,
        )
        if _freeze_evidence(expected) != receipt.positive_evidence:
            return REFUSAL_EVIDENCE_DOES_NOT_MATCH_SOURCE
        return None

    def _visible_accession_group(
        self,
        fact: RawFactOccurrence,
        policy: QueryPolicy,
    ) -> tuple[RawFactOccurrence, ...]:
        """Every cutoff-visible occurrence of this fact's logical key in its filing."""
        key = (fact.source.entity_id, fact.concept_qname, _fact_period_index_key(fact))
        candidates = self._events_by_entity_qname_period.get(key, ())
        return tuple(
            item
            for item in candidates
            if item.source.accession == fact.source.accession
            and item.logical_key == fact.logical_key
            and self._event_temporally_eligible(item, policy)
        )

    def _effective_roots(
        self,
        logical_key: str,
        policy: QueryPolicy,
    ) -> Mapping[str, str]:
        """Map a root duplicate-group key to its confirmation-unified root.

        Two ``FILED`` groups joined by a cutoff-visible, still-provable
        confirmation are one vintage family rather than two unlinked roots.
        This is a general root-unification law keyed on evidence; no issuer,
        accession, or metric is special-cased.
        """
        receipts = self._confirmations_by_logical_key.get(logical_key, ())
        if not receipts:
            return _EMPTY_ROOT_MAP
        # FIF S2: admission proves the receipts of one key are
        # version-homogeneous, so the first receipt names the rule the whole
        # union-find below runs under.
        chain_rule = receipts[0].evidence_rule_version == CONFIRMATION_CHAIN_RULE_VERSION
        cache_key = (logical_key, policy.source_snapshot_at, policy.recorded_at)
        cached = self._effective_root_cache.get(cache_key)
        if cached is not None:
            return cached
        parent_of: dict[str, str] = {}

        def find(node: str) -> str:
            root = node
            while parent_of.get(root, root) != root:
                root = parent_of[root]
            while parent_of.get(node, node) != node:
                parent_of[node], node = root, parent_of[node]
            return root

        def union(left: str, right: str) -> None:
            a, b = find(left), find(right)
            if a == b:
                return
            # Deterministic label: the lexicographically smallest member wins,
            # so an effective root never depends on receipt ordering.
            low, high = (a, b) if a < b else (b, a)
            parent_of[high] = low

        for receipt in receipts:
            if self._receipt_still_proves_confirmation(receipt, policy) is not None:
                continue
            parent_meta = self._lineage_by_occurrence_id.get(receipt.parent_occurrence_id)
            child_meta = self._lineage_by_occurrence_id.get(receipt.child_occurrence_id)
            if parent_meta is None or child_meta is None:
                continue
            parent_of.setdefault(parent_meta.root_duplicate_group_key, parent_meta.root_duplicate_group_key)
            parent_of.setdefault(child_meta.root_duplicate_group_key, child_meta.root_duplicate_group_key)
            union(parent_meta.root_duplicate_group_key, child_meta.root_duplicate_group_key)
        resolved = {node: find(node) for node in parent_of}
        # FIF S2: for a version-2 key keep every component.  Admission already
        # proved the receipts are one strictly ordered adjacent path over
        # every filing of the key, so a still-proving cutoff-visible subset is
        # a union of contiguous sub-paths — no rounded or skip link can join a
        # component, and unification can never outrun the admitted path.
        if not chain_rule:
            # v1 admits exactly one parent and one child. A component that has
            # transitively accumulated a third filing has an ambiguous parent, so
            # refuse the whole component rather than chaining across vintages: the
            # cell then keeps the honest unlinked-vintage refusal. Widening this is
            # a separately adjudicated v2 question, not an implementation detail.
            sizes: dict[str, int] = {}
            for label in resolved.values():
                sizes[label] = sizes.get(label, 0) + 1
            resolved = {
                node: label for node, label in resolved.items() if sizes[label] <= 2
            }
        projection = MappingProxyType(resolved)
        # Bounded even if an engine is pooled and callers vary cutoffs: the
        # cache is a speed aid, never a correctness input, so evicting is safe.
        if len(self._effective_root_cache) >= MAX_EFFECTIVE_ROOT_CACHE_ENTRIES:
            self._effective_root_cache.clear()
        self._effective_root_cache[cache_key] = projection
        return projection

    def _event_temporally_eligible(
        self,
        fact: RawFactOccurrence,
        policy: QueryPolicy,
    ) -> bool:
        """Whether this fact *and all required ancestry* is visible on both clocks."""
        lineage = self._lineage_by_occurrence_id[fact.occurrence_id]
        return (
            lineage.source_ready_at is not None
            and lineage.source_ready_at <= policy.source_snapshot_at
            and lineage.system_ready_at <= policy.recorded_at
        )

    def _bounded_visible_events(
        self,
        events: Sequence[RawFactOccurrence],
        policy: QueryPolicy,
        *,
        maximum: int | None = None,
    ) -> tuple[tuple[RawFactOccurrence, ...], bool]:
        limit = (
            self.bounds.max_visible_source_events_per_cell
            if maximum is None
            else maximum
        )
        visible: list[RawFactOccurrence] = []
        for item in events:
            if not self._event_temporally_eligible(item, policy):
                continue
            visible.append(item)
            if len(visible) > limit:
                return (), True
        return tuple(visible), False

    def _lineage_ids_for(
        self,
        group: Sequence[RawFactOccurrence],
    ) -> tuple[str, ...]:
        """Materialize a candidate set's unique ancestry in one linear walk."""
        identifiers: set[str] = set()
        for fact in group:
            current_id: str | None = fact.occurrence_id
            while current_id is not None and current_id not in identifiers:
                identifiers.add(current_id)
                current_id = self._parent_by_occurrence_id.get(current_id)
        return tuple(sorted(identifiers))

    def _group_readiness(
        self,
        group: Sequence[RawFactOccurrence],
    ) -> tuple[datetime | None, datetime | None]:
        metadata = tuple(self._lineage_by_occurrence_id[item.occurrence_id] for item in group)
        if not metadata or any(item.source_ready_at is None for item in metadata):
            source_ready_at = None
        else:
            source_ready_at = max(
                item.source_ready_at for item in metadata if item.source_ready_at is not None
            )
        system_ready_at = max((item.system_ready_at for item in metadata), default=None)
        return source_ready_at, system_ready_at

    def _group_clocks(
        self,
        group: Sequence[RawFactOccurrence],
    ) -> tuple[datetime | None, datetime | None, tuple[str, ...]]:
        source_ready, system_ready = self._group_readiness(group)
        return source_ready, system_ready, self._lineage_ids_for(group)

    def _select_source_group(
        self,
        events: Sequence[RawFactOccurrence],
        policy: QueryPolicy,
    ) -> _SourceSelection:
        """Select one fully visible economic vintage without tie-breaking by ID.

        All temporal filtering happens before duplicate, unit, dimension, or
        revision reasoning. A fact unavailable on either clock is therefore
        indistinguishable from absence to this query snapshot: no occurrence
        ID, exact future clock, or future-specific explanation escapes.
        """
        if not events:
            return _SourceSelection(
                state=CellState.MISSING,
                occurrence=None,
                source_ready_at=None,
                system_ready_at=None,
                source_occurrence_ids=(),
                reason="missing_standard_fact",
            )
        visible_events = tuple(
            item for item in events if self._event_temporally_eligible(item, policy)
        )
        if not visible_events:
            return _SourceSelection(
                state=CellState.MISSING,
                occurrence=None,
                source_ready_at=None,
                system_ready_at=None,
                source_occurrence_ids=(),
                reason="missing_standard_fact",
            )
        # A raw-ledger logical key includes the source origin as well as the
        # economic context.  A query must never choose between two origins by
        # timestamp alone; a source-fusion policy would need its own governed
        # contract and receipt.
        logical_keys = {item.logical_key for item in visible_events}
        if len(logical_keys) != 1:
            source_ready_at, system_ready_at = self._group_readiness(visible_events)
            return _SourceSelection(
                state=CellState.NOT_EVALUABLE,
                occurrence=None,
                source_ready_at=source_ready_at,
                system_ready_at=system_ready_at,
                source_occurrence_ids=self._lineage_ids_for(visible_events),
                reason="multiple raw economic identities require an explicit governed source-fusion rule",
            )
        groups: dict[str, list[RawFactOccurrence]] = {}
        for event in visible_events:
            groups.setdefault(event.duplicate_group_key, []).append(event)
        ordered: list[
            tuple[datetime, datetime, int, tuple[RawFactOccurrence, ...], str]
        ] = []
        for key, values in groups.items():
            group = tuple(values)
            source_ready, system_ready = self._group_readiness(group)
            # ``visible_events`` gates every ancestry member, so source_ready
            # is non-null and both clocks are known to the snapshot.
            if source_ready is None:
                continue
            depth = max(
                self._lineage_by_occurrence_id[item.occurrence_id].depth for item in group
            )
            ordered.append((source_ready, system_ready, depth, group, key))
        if not ordered:
            return _SourceSelection(
                state=CellState.MISSING,
                occurrence=None,
                source_ready_at=None,
                system_ready_at=None,
                source_occurrence_ids=(),
                reason="missing_standard_fact",
            )

        def ids_for(
            items: Sequence[
                tuple[datetime, datetime, int, tuple[RawFactOccurrence, ...], str]
            ],
        ) -> tuple[str, ...]:
            return self._lineage_ids_for(
                tuple(event for item in items for event in item[3])
            )

        # Two visible roots have no attested revision relationship. Filing
        # time and hashes are not a source-fusion policy, so never infer one.
        #
        # FIF-3A4: a cutoff-visible, still-provable ``xbrl_confirmation``
        # receipt is exactly such an explicit relationship. It unifies the two
        # FILED roots into one effective root. It does not remint either
        # occurrence, does not create a revision, and does not change depth, so
        # AS_REPORTED still resolves to the earliest filed root and
        # LATEST_RESTATED still finds no reported revision vintage.
        effective_roots = self._effective_roots(next(iter(logical_keys)), policy)
        root_ids = {
            effective_roots.get(
                self._lineage_by_occurrence_id[
                    item[3][0].occurrence_id
                ].root_duplicate_group_key,
                self._lineage_by_occurrence_id[
                    item[3][0].occurrence_id
                ].root_duplicate_group_key,
            )
            for item in ordered
            if item[3]
        }
        if len(root_ids) != 1:
            return _SourceSelection(
                state=CellState.NOT_EVALUABLE,
                occurrence=None,
                source_ready_at=_clock_max(item[0] for item in ordered),
                system_ready_at=_clock_max(item[1] for item in ordered),
                source_occurrence_ids=ids_for(ordered),
                reason="unlinked source vintages require an explicit typed revision lineage",
            )

        if policy.selection is BitemporalPolicy.AS_REPORTED:
            candidates = [item for item in ordered if all(event.revision_of is None for event in item[3])]
            if not candidates:
                return _SourceSelection(
                    state=CellState.MISSING,
                    occurrence=None,
                    source_ready_at=None,
                    system_ready_at=None,
                    source_occurrence_ids=(),
                    reason="missing_standard_fact",
                )
            rank = min(item[0] for item in candidates)
            winners = [item for item in candidates if item[0] == rank]
        elif policy.selection is BitemporalPolicy.LATEST_RESTATED:
            candidates = [
                item
                for item in ordered
                if all(event.event_type in _REPORTED_REVISION_EVENT_TYPES for event in item[3])
            ]
            if not candidates:
                return _SourceSelection(
                    state=CellState.MISSING,
                    occurrence=None,
                    source_ready_at=None,
                    system_ready_at=None,
                    source_occurrence_ids=(),
                    reason="no eligible explicitly typed reported revision vintage",
                )
            rank = max((item[0], item[2]) for item in candidates)
            winners = [item for item in candidates if (item[0], item[2]) == rank]
        else:
            candidates = ordered
            rank = max((item[0], item[2]) for item in candidates)
            winners = [item for item in candidates if (item[0], item[2]) == rank]

        if len(winners) != 1:
            return _SourceSelection(
                state=CellState.NOT_EVALUABLE,
                occurrence=None,
                source_ready_at=_clock_max(item[0] for item in winners),
                system_ready_at=_clock_max(item[1] for item in winners),
                source_occurrence_ids=ids_for(winners),
                reason="ambiguous equal-precedence source vintages cannot be selected",
            )
        source_ready, system_ready, _, group, _ = winners[0]
        ids = ids_for(winners)
        if any(item.is_withdrawn for item in group):
            return _SourceSelection(
                state=CellState.MISSING,
                occurrence=None,
                source_ready_at=source_ready,
                system_ready_at=system_ready,
                source_occurrence_ids=ids,
                reason="selected source vintage is withdrawn",
            )
        if not _duplicates_agree(group):
            return _SourceSelection(
                state=CellState.NOT_EVALUABLE,
                occurrence=None,
                source_ready_at=source_ready,
                system_ready_at=system_ready,
                source_occurrence_ids=ids,
                reason="conflicting duplicate raw facts cannot be selected",
            )
        chosen = _duplicate_representative(group)
        if chosen.is_nil or chosen.parsed_value is None:
            return _SourceSelection(
                state=CellState.MISSING,
                occurrence=None,
                source_ready_at=source_ready,
                system_ready_at=system_ready,
                source_occurrence_ids=ids,
                reason="selected source fact has no numeric value",
            )
        return _SourceSelection(
            state=CellState.VALUE,
            occurrence=chosen,
            source_ready_at=source_ready,
            system_ready_at=system_ready,
            source_occurrence_ids=ids,
        )

    def _ambiguous_alias_priorities(
        self,
        candidates: Sequence[_AliasCandidate],
    ) -> set[int]:
        """Return fallback priorities claimed by multiple visible aliases.

        Priority is metric-global.  Treating it as local to each mapping rule
        would make lexical concept/rule order an undocumented tie-breaker.
        """
        by_priority: dict[int, set[tuple[str, str, str, str]]] = {}
        for item in candidates:
            by_priority.setdefault(item.alias.priority, set()).add(
                (
                    item.alias.taxonomy,
                    item.alias.concept,
                    item.mapping.rule.rule_id,
                    item.mapping.rule.version,
                )
            )
        return {priority for priority, aliases in by_priority.items() if len(aliases) > 1}

    def _evaluate_direct(
        self,
        entity: QueryEntity,
        contract: MetricContract,
        period: PeriodRequest,
        policy: QueryPolicy,
        projection: _RegistryProjection,
    ) -> MetricCell:
        """Evaluate a direct metric after temporal and governance eligibility.

        A visible-but-unsafe candidate is retained as a governed N/E outcome
        only after every eligible governed alias has failed to supply a safe
        consolidated/unit-compatible source. This permits a valid
        consolidated fact to coexist with segmented inventory without opening
        an ungoverned fallback path.
        """
        visible_mappings = projection.mappings_by_metric.get(contract.metric_id, ())
        if not visible_mappings:
            reason = "governance unavailable at recorded_at cutoff"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.MISSING,
                value=None,
                unit=None,
                provenance=self._opaque_provenance(policy, reason=reason),
                reason=reason,
            )
        contract_error = self._period_contract_error(contract, period)
        if contract_error:
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection, policy, contract, reason=contract_error
                ),
                reason=contract_error,
            )
        # Invisible future mappings were already removed by the cutoff
        # projection above.  Once a mapping lane is visible, request-shape
        # validity precedes taxonomy-year applicability, matching formula
        # evaluation and receipt reconstruction.
        candidates = self._aliases_for_period(contract, period, projection)
        if not candidates:
            reason = "no governed concept alias applies to the requested taxonomy period"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.MISSING,
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection, policy, contract, reason=reason
                ),
                reason=reason,
            )
        ambiguous_priorities = self._ambiguous_alias_priorities(candidates)
        if ambiguous_priorities:
            reason = "ambiguous governed alias priorities across visible mapping rules"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    reason=reason,
                ),
                reason=reason,
            )
        visible_candidate_events: list[
            tuple[_AliasCandidate, tuple[RawFactOccurrence, ...]]
        ] = []
        visible_source_count = 0
        for candidate in candidates:
            raw_events = self._events_for_alias(entity, candidate.alias, period)
            remaining = (
                self.bounds.max_visible_source_events_per_cell
                - visible_source_count
            )
            period_events, source_history_over_bound = self._bounded_visible_events(
                raw_events,
                policy,
                maximum=remaining,
            )
            if source_history_over_bound:
                reason = "visible source history exceeds the synchronous per-cell bound"
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=CellState.NOT_EVALUABLE,
                    value=None,
                    unit=contract.units[0] if contract.units else None,
                    provenance=self._base_provenance(
                        projection,
                        policy,
                        contract,
                        reason=reason,
                    ),
                    reason=reason,
                )
            visible_source_count += len(period_events)
            visible_candidate_events.append((candidate, period_events))
        structural_failure: tuple[_AliasCandidate, str, tuple[RawFactOccurrence, ...]] | None = None
        for candidate, period_events in visible_candidate_events:
            mapping, alias = candidate.mapping, candidate.alias
            mapping_digest = projection.mapping_digests[
                (contract.metric_id, mapping.rule.rule_id, mapping.rule.version)
            ]
            if not period_events:
                # A higher-priority alias that exists only in the future is
                # indistinguishable from absent and cannot block a lower one.
                continue
            unknown_dimension_scope = tuple(
                item
                for item in period_events
                if (
                    contract.dimensional_profile.mode == "consolidated_only"
                    and not item.dimensions_known
                )
            )
            disallowed_dimensions = tuple(
                item for item in period_events if not self._fact_dimensions_allowed(item, contract)
            )
            unit_events = tuple(item for item in period_events if not self._fact_unit_allowed(item, contract))
            eligible_structure = tuple(
                item
                for item in period_events
                if self._fact_dimensions_allowed(item, contract) and self._fact_unit_allowed(item, contract)
            )
            if not eligible_structure:
                if structural_failure is None:
                    if unknown_dimension_scope:
                        structural_failure = (
                            candidate,
                            "unknown_dimension_scope: source does not expose dimensions, "
                            "so consolidated-only eligibility cannot be established",
                            unknown_dimension_scope,
                        )
                    elif disallowed_dimensions:
                        structural_failure = (
                            candidate,
                            "disallowed_dimension: governed metric requires consolidated dimensionless fact",
                            disallowed_dimensions,
                        )
                    elif unit_events:
                        structural_failure = (
                            candidate,
                            "unexpected_unit: source unit is outside the governed metric contract",
                            unit_events,
                        )
                continue
            selection = self._select_source_group(eligible_structure, policy)
            if selection.state is not CellState.VALUE:
                reason = selection.reason or "missing_standard_fact"
                if selection.state is CellState.MISSING and reason in {
                    "missing_standard_fact",
                    "no eligible explicitly typed reported revision vintage",
                }:
                    continue
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=selection.state,
                    value=None,
                    unit=contract.units[0] if contract.units else None,
                    provenance=self._base_provenance(
                        projection,
                        policy,
                        contract,
                        reason=reason,
                        concept_qname=f"{alias.taxonomy}:{alias.concept}",
                        taxonomy=alias.taxonomy,
                        concept=alias.concept,
                        mapping_rule_id=mapping.rule.rule_id,
                        mapping_rule_version=mapping.rule.version,
                        mapping_digest=mapping_digest,
                        alias_priority=alias.priority,
                        source_ready_at=selection.source_ready_at,
                        system_ready_at=_clock_max(
                            (
                                selection.system_ready_at,
                                projection.governance_available_by_metric[contract.metric_id],
                            )
                        ),
                        source_occurrence_ids=selection.source_occurrence_ids,
                    ),
                    reason=reason,
                )
            fact = selection.occurrence
            if fact is None:  # pragma: no cover - _SourceSelection guards this invariant.
                raise AssertionError("value source selection omitted occurrence")
            metadata = self._metadata_for(fact, policy)
            source_receipt = {
                "source_entity_id": fact.source.entity_id,
                "source": fact.source.source,
                "accession": fact.source.accession,
                "document_id": fact.source.document_id,
                "source_url": fact.source.source_url,
                "source_body_sha256": fact.source.body_sha256,
                "form": metadata.form if metadata is not None else None,
                "filed_at": metadata.filed_at if metadata is not None else None,
                "filing_metadata_available_at": (
                    metadata.available_at if metadata is not None else None
                ),
                "filing_metadata_content_sha256": (
                    metadata.content_sha256 if metadata is not None else None
                ),
                "accepted_at": fact.accepted_at,
                "recorded_at": fact.recorded_at,
                "mapping_available_at": fact.mapping_available_at,
                "computed_at": fact.computed_at,
                "published_at": fact.published_at,
                "source_ready_at": selection.source_ready_at,
                "system_ready_at": _clock_max(
                    (
                        selection.system_ready_at,
                        metadata.available_at if metadata is not None else None,
                        projection.governance_available_by_metric[contract.metric_id],
                    )
                ),
                "concept_qname": fact.concept_qname,
                "taxonomy": alias.taxonomy,
                "concept": alias.concept,
                "unit": _canonical_raw_unit(fact),
                "mapping_rule_id": mapping.rule.rule_id,
                "mapping_rule_version": mapping.rule.version,
                "mapping_digest": mapping_digest,
                "alias_priority": alias.priority,
                "source_occurrence_ids": selection.source_occurrence_ids,
            }
            if (
                metadata is None
                or metadata.form not in contract.period_constraints.allowed_forms
            ):
                reason = "filing form is unavailable or outside the governed metric contract"
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=CellState.NOT_EVALUABLE,
                    value=None,
                    unit=contract.units[0] if contract.units else None,
                    provenance=self._base_provenance(
                        projection,
                        policy,
                        contract,
                        reason=reason,
                        **source_receipt,
                    ),
                    reason=reason,
                )
            try:
                numeric_value = _bounded_decimal(fact.parsed_value, field_name="source fact value")
            except QueryValidationError:
                reason = "source numeric value is outside the query decimal contract"
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=CellState.NOT_EVALUABLE,
                    value=None,
                    unit=contract.units[0] if contract.units else None,
                    provenance=self._base_provenance(
                        projection,
                        policy,
                        contract,
                        reason=reason,
                        **source_receipt,
                    ),
                    reason=reason,
                )
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.VALUE,
                value=numeric_value,
                unit=_canonical_raw_unit(fact),
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    selected_raw_fact=fact,
                    **source_receipt,
                ),
            )
        if structural_failure is not None:
            candidate, reason, evidence = structural_failure
            mapping, alias = candidate.mapping, candidate.alias
            mapping_digest = projection.mapping_digests[
                (contract.metric_id, mapping.rule.rule_id, mapping.rule.version)
            ]
            source_ready_at, evidence_system_ready_at, evidence_ids = self._group_clocks(evidence)
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=contract.units[0] if contract.units else None,
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    reason=reason,
                    concept_qname=f"{alias.taxonomy}:{alias.concept}",
                    taxonomy=alias.taxonomy,
                    concept=alias.concept,
                    mapping_rule_id=mapping.rule.rule_id,
                    mapping_rule_version=mapping.rule.version,
                    mapping_digest=mapping_digest,
                    alias_priority=alias.priority,
                    source_ready_at=source_ready_at,
                    system_ready_at=_clock_max(
                        (
                            evidence_system_ready_at,
                            projection.governance_available_by_metric[contract.metric_id],
                        )
                    ),
                    source_occurrence_ids=evidence_ids,
                ),
                reason=reason,
            )
        if self._not_presented_pack is not None and not any(
            events for _candidate, events in visible_candidate_events
        ):
            # Step 5 b2: an absence with no visible alias fact at all may be
            # upgraded to N/A, but only on governed, recomputable linkbase
            # evidence from the slot's own filing.  Anything else stays absent.
            not_presented = self._not_presented_verdict_for(
                entity.entity_id, contract.metric_id, period, policy
            )
            if not_presented is not None:
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=CellState.NOT_APPLICABLE,
                    value=None,
                    unit=contract.units[0] if contract.units else None,
                    provenance=self._base_provenance(
                        projection,
                        policy,
                        contract,
                        reason=NOT_PRESENTED_REASON,
                        na_basis=NA_BASIS_NOT_PRESENTED_ITEM,
                        not_presented=not_presented,
                    ),
                    reason=NOT_PRESENTED_REASON,
                )
        reason = (
            "no eligible explicitly typed reported revision vintage"
            if policy.selection is BitemporalPolicy.LATEST_RESTATED
            else "missing_standard_fact: no governed concept alias supplied an exact eligible source interval"
        )
        return self._new_cell(
            entity=entity,
            governance_bundle=projection.governance_bundle,
            metric_id=contract.metric_id,
            period=period,
            state=CellState.MISSING,
            value=None,
            unit=contract.units[0] if contract.units else None,
            provenance=self._base_provenance(
                projection, policy, contract, reason=reason
            ),
            reason=reason,
        )

    @staticmethod
    def _dependency_period(
        output_period: PeriodRequest,
        dependency: MetricContract,
        formula: FormulaRule,
    ) -> PeriodRequest:
        return _dependency_period_for(output_period, dependency, formula)

    @staticmethod
    def _eval_formula(expression: str, values: Mapping[str, Decimal]) -> Decimal:
        return _eval_formula_decimal(expression, values)

    def _formula_provenance(
        self,
        projection: _RegistryProjection,
        policy: QueryPolicy,
        contract: MetricContract,
        formula: FormulaRule,
        dependencies: Sequence[MetricCell],
        *,
        reason: str | None = None,
        summary_dependencies: Sequence[MetricCell] | None = None,
        qualified_not_presented: tuple[str, ...] = (),
    ) -> CellProvenance:
        # A qualified sum summarizes its revision basis over the presented
        # operands only: a not-presented operand has no source of its own.
        summary = dependencies if summary_dependencies is None else summary_dependencies

        def common(field_name: str) -> Any | None:
            values = {getattr(item.provenance, field_name) for item in summary}
            if len(values) != 1:
                return None
            value = next(iter(values))
            return value if value is not None else None

        mapping_rule_ids = tuple(
            sorted({identifier for item in dependencies for identifier in item.provenance.mapping_rule_ids})
        )
        mapping_rule_versions = tuple(
            sorted({version for item in dependencies for version in item.provenance.mapping_rule_versions})
        )
        mapping_digests = tuple(
            sorted({digest for item in dependencies for digest in item.provenance.mapping_digests})
        )
        formula_available_at = self._formula_rule_available_at(contract, formula)
        source_ready_at = _clock_max(item.provenance.source_ready_at for item in dependencies)
        system_ready_at = _clock_max(
            [formula_available_at]
            + [item.provenance.system_ready_at for item in dependencies]
        )
        return self._base_provenance(
            projection,
            policy,
            contract,
            kind=ProvenanceKind.FORMULA,
            reason=reason,
            source_ready_at=source_ready_at,
            system_ready_at=system_ready_at,
            mapping_rule_id=mapping_rule_ids[0] if len(mapping_rule_ids) == 1 else None,
            mapping_rule_version=(
                mapping_rule_versions[0] if len(mapping_rule_versions) == 1 else None
            ),
            mapping_digest=mapping_digests[0] if len(mapping_digests) == 1 else None,
            mapping_rule_ids=mapping_rule_ids,
            mapping_rule_versions=mapping_rule_versions,
            mapping_digests=mapping_digests,
            confidence=formula.rule.confidence,
            source=common("source"),
            accession=common("accession"),
            document_id=common("document_id"),
            source_body_sha256=common("source_body_sha256"),
            source_url=common("source_url"),
            dependency_cell_ids=tuple(item.cell_id for item in dependencies),
            unit=formula.output_unit,
            qualified_not_presented=qualified_not_presented,
        )

    def _evaluate_formula(
        self,
        entity: QueryEntity,
        contract: MetricContract,
        period: PeriodRequest,
        policy: QueryPolicy,
        projection: _RegistryProjection,
        cache: dict[tuple[Any, ...], MetricCell],
        stack: tuple[str, ...],
    ) -> MetricCell:
        formula = projection.formulas_by_metric.get(contract.metric_id)
        # Do not inspect dependencies before the formula itself existed in the
        # system's governed state. Otherwise a future formula ID/digest and
        # dependency lineage can leak into an historical query result.
        if formula is None:
            reason = "governance unavailable at recorded_at cutoff"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.MISSING,
                value=None,
                unit=None,
                provenance=self._opaque_provenance(policy, reason=reason),
                reason=reason,
            )
        contract_error = self._period_contract_error(contract, period)
        if contract_error:
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._base_provenance(
                    projection,
                    policy,
                    contract,
                    kind=ProvenanceKind.FORMULA,
                    reason=contract_error,
                ),
                reason=contract_error,
            )
        dependency_cells: list[MetricCell] = []
        for dependency_id in formula.dependencies:
            dependency_contract = projection.contracts_by_metric.get(dependency_id)
            if dependency_contract is None:
                reason = "governance unavailable at recorded_at cutoff"
                return self._new_cell(
                    entity=entity,
                    governance_bundle=projection.governance_bundle,
                    metric_id=contract.metric_id,
                    period=period,
                    state=CellState.MISSING,
                    value=None,
                    unit=None,
                    provenance=self._opaque_provenance(policy, reason=reason),
                    reason=reason,
                )
            dependency_period = self._dependency_period(period, dependency_contract, formula)
            dependency_cells.append(
                self._evaluate(
                    entity,
                    dependency_id,
                    dependency_period,
                    policy,
                    projection,
                    cache,
                    stack=stack,
                )
            )
        # Denominator qualification stage (S1-b): runs after the dependency
        # cells are assembled and before the not_evaluable/missing triage, so
        # a constraint-named denominator that could not be assembled (or is a
        # non-positive VALUE) yields the explicit qualification vocabulary
        # instead of the generic dependency vocabulary.  The issuer branch
        # here re-passes deterministically: _evaluate already refused
        # non-applicable issuers for this metric before dispatch.
        denominator_inputs = {
            dependency_id: (
                cell.value if cell.state is CellState.VALUE else None
            )
            for dependency_id, cell in zip(formula.dependencies, dependency_cells)
        }
        issuer_class = (
            issuer_class_for_sic(entity.issuer_sic) if entity.issuer_sic is not None else None
        )
        qualification = qualify_metric(contract, formula, issuer_class, denominator_inputs)
        if qualification.state != "applicable":
            reason = qualification.reason
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=(
                    CellState.NOT_APPLICABLE
                    if qualification.state == "not_applicable"
                    else CellState.NOT_EVALUABLE
                ),
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        # R-FORMULA F3 (step 5 build-c): a governed not-presented operand, or
        # a VALUE operand carrying a not-presented qualifier, is decided by the
        # formula's versioned policy; every other case keeps the historical
        # triage below byte for byte.
        np_outcome = _formula_policy_outcome(dependency_cells, formula)
        if np_outcome is not None:
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=np_outcome.state,
                value=np_outcome.value,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection,
                    policy,
                    contract,
                    formula,
                    dependency_cells,
                    reason=np_outcome.reason,
                    summary_dependencies=(
                        [item for item in dependency_cells if item.state is CellState.VALUE]
                        if np_outcome.value_summary
                        else None
                    ),
                    qualified_not_presented=np_outcome.qualified_not_presented,
                ),
                dependency_cells=dependency_cells,
                reason=np_outcome.reason,
            )
        not_applicable = [
            item for item in dependency_cells if item.state is CellState.NOT_APPLICABLE
        ]
        if not_applicable:
            reason = "not_applicable_dependency: " + ", ".join(
                f"{item.metric_id} ({item.reason or 'not_applicable'})"
                for item in not_applicable
            )
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_APPLICABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        not_evaluable = [item for item in dependency_cells if item.state is CellState.NOT_EVALUABLE]
        if not_evaluable:
            reason = "incompatible_dependencies: " + ", ".join(
                f"{item.metric_id} ({item.reason or 'not_evaluable'})" for item in not_evaluable
            )
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        missing = [item for item in dependency_cells if item.state is CellState.MISSING]
        if missing:
            reason = "missing_dependency: " + ", ".join(
                f"{item.metric_id} ({item.reason or 'missing'})" for item in missing
            )
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.MISSING,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        values = {item.metric_id: item.value for item in dependency_cells}
        if any(value is None for value in values.values()):  # pragma: no cover - state invariant.
            raise AssertionError("value dependencies must carry Decimal values")
        revision_bases = {
            (
                item.provenance.source,
                item.provenance.accession,
                item.provenance.document_id,
                item.provenance.source_body_sha256,
            )
            for item in dependency_cells
        }
        if (
            len(revision_bases) != 1
            or any(any(part is None for part in basis) for basis in revision_bases)
        ):
            reason = "incompatible_revision_basis: formula dependencies require one shared source accession/document"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        try:
            result = self._eval_formula(
                formula.expression,
                {key: value for key, value in values.items() if value is not None},
            )
        except ZeroDivisionError:
            reason = "division_by_zero"
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        except QueryValidationError as exc:
            reason = str(exc)
            return self._new_cell(
                entity=entity,
                governance_bundle=projection.governance_bundle,
                metric_id=contract.metric_id,
                period=period,
                state=CellState.NOT_EVALUABLE,
                value=None,
                unit=formula.output_unit,
                provenance=self._formula_provenance(
                    projection, policy, contract, formula, dependency_cells, reason=reason
                ),
                dependency_cells=dependency_cells,
                reason=reason,
            )
        return self._new_cell(
            entity=entity,
            governance_bundle=projection.governance_bundle,
            metric_id=contract.metric_id,
            period=period,
            state=CellState.VALUE,
            value=result,
            unit=formula.output_unit,
            provenance=self._formula_provenance(
                projection, policy, contract, formula, dependency_cells
            ),
            dependency_cells=dependency_cells,
        )


# The shorter name is the natural import in request handlers; preserve the
# fully explicit class above for code that makes temporal semantics visible.
MetricQueryEngine = BitemporalMetricQueryEngine


__all__ = [
    "BitemporalMetricQueryEngine",
    "BitemporalPolicy",
    "BitemporalQueryPolicy",
    "CELL_RECEIPT_SCHEMA",
    "CellNode",
    "CellProvenance",
    "CellState",
    "DeterministicExport",
    "EvaluationPolicy",
    "FilingMetadata",
    "FilingMetadataResolver",
    "FORMULA_DECIMAL_EMAX",
    "FORMULA_DECIMAL_EMIN",
    "FORMULA_DECIMAL_PRECISION",
    "HARD_MAX_CELLS",
    "HARD_MAX_DEPENDENCY_RECEIPTS",
    "HARD_MAX_ENTITY_BINDINGS",
    "HARD_MAX_MATRIX_EDGES",
    "HARD_MAX_MATRIX_NODES",
    "HARD_MAX_METRICS",
    "HARD_MAX_PERIODS",
    "HARD_MAX_PROVENANCE_IDS",
    "HARD_MAX_RECEIPT_DEPTH",
    "HARD_MAX_RECEIPT_EDGES",
    "HARD_MAX_RECEIPT_NODES",
    "HARD_MAX_RECEIPT_WIRE_BYTES",
    "HARD_MAX_TICKERS",
    "HARD_MAX_VISIBLE_SOURCE_EVENTS_PER_CELL",
    "MAX_QUERY_TEXT_CHARS",
    "MetricCell",
    "MetricCellState",
    "MetricMatrix",
    "MetricPeriod",
    "MetricQueryEngine",
    "MetricQueryPolicy",
    "PeriodRequest",
    "PeriodSelector",
    "ProvenanceKind",
    "QUERY_SCHEMA",
    "RECEIPT_PROOF_SCOPE",
    "RECEIPT_SELECTION_PROOF",
    "QueryBounds",
    "QueryBoundsError",
    "QueryCutoffs",
    "QueryEntity",
    "QueryError",
    "QueryPolicy",
    "QueryValidationError",
    "UnsupportedConceptError",
    "UnsupportedMetricError",
]
