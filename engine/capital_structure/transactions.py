"""Capital-structure V2 task X0a: transaction reconciliation (SPEC_X0 §1-§9).

``reconcile_transactions`` is the single place where the product learns what the
issuer ALREADY did — shelf takedowns and ATM sales that used up registered
capacity, warrants exercised and notes converted that shrank the outstanding
claims, shares repurchased or retired — and ``apply_outstanding`` is the single
place where that history replaces an instrument's stale I1 balance so
:mod:`engine.capital_structure.supply_scenarios` reads the post-X0 claim.

Laws enforced here (gates A09, A15, A20, A23, A24, A27; lines L98, L100):

* A cumulative usage figure and the individual transactions explaining it never
  both decrement (A15, L98).  A window that contains another dominates it; an
  individual inside a maximal window is ``covered`` and never adds.
* Incomplete history is never usage 0 (A20).  Without a completeness proof the
  usage is ``unknown`` and only the ``evidenced_floor`` — a true lower bound —
  is known.  Unknown is never 0 and never infinity.
* A resale by an existing holder normally does not itself fund the company
  (A23, L98): it contributes 0 incremental shares, lands in a ``no_cash``
  realized-cash row, and never enters shelf usage, programme usage or an
  instrument decrement.
* An already-issued security is never counted again as future issuance (A27,
  review focus 2): flows dated on or before the latest ``outstanding_balance``
  are already reflected in it and are never applied twice, two observations of
  one economic event share one ``transaction_id`` and decrement once, and every
  prior instrument version is emitted with its ``supersedes_version_id`` rather
  than overwritten.
* A pre-funded warrant pays ONLY the residual actually paid at exercise; the
  prepaid part is never counted again (A24, L100).
* Only ``canonical_extraction`` and ``adjudicated_gold`` may state a transaction
  (A09); every other origin is refused.  A ``canonical_join`` binding is allowed
  only on an exact unique SEC file number; an instrument binding is an owner
  adjudication and nothing else.
* Exact arithmetic only.  Every numeric field is an exact decimal string, a
  float input raises ``TypeError``, and no score, rank, sizing, probability or
  recommendation is produced.  A doubtful decrement is never applied and a
  doubtful observation is deferred with a named reason.

Realized cash here is a historical fact and is deliberately NOT a scenario
``CashEffect``: scenario cash stays with I1/S0.  Nothing in this module is a
capacity or a supply answer — C2 and I1 consume ``transaction_usage`` and the
post-X0 ``InstrumentSet``.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from typing import Any, Callable, Mapping, NamedTuple, Sequence

from engine.capital_structure.issuer_state_contracts import (
    BINDING_ORIGINS,
    BINDING_TARGET_KINDS,
    ECONOMIC_TERM_UNITS,
    REALIZED_CASH_KINDS,
    REPORTING_BASES,
    SETTLEMENTS,
    SUPPORT_STATES,
    TRANSACTION_KINDS,
    TRANSACTION_ORIGINS,
    USAGE_CLASSES,
    CalculationReceipt,
    ContractViolation,
    EconomicTerm,
    EvidenceRef,
    FamilyProvenance,
    FamilyState,
    Instrument,
    InstrumentSet,
    Provenance,
    Quantity,
    ShareObservationRef,
    Unknown,
    _DECIMAL,
    _assert_safe_keys,
    _date,
    _identifier,
    _member,
    _plain,
    _record,
    _require,
    _timestamp,
    sha256_of,
    stable_id,
)

IMPLEMENTATION = "capital_structure.transactions.reconcile.v1"
LEDGER_SCHEMA = "capital_structure.transaction_ledger.v1"
OBSERVATION_SCHEMA = "capital_structure.transaction_observation.v1"
BINDING_SCHEMA = "capital_structure.transaction_binding.v1"
FILING_COVERAGE_SCHEMA = "capital_structure.transaction_filing_coverage.v1"
USAGE_SCHEMA = "capital_structure.transaction_usage.v1"
INSTRUMENT_VERSION_SCHEMA = "capital_structure.instrument_version.v1"
SHARE_RECONCILIATION_SCHEMA = "capital_structure.share_reconciliation.v1"
REALIZED_CASH_SCHEMA = "capital_structure.realized_cash.v1"

GOLD_ORIGIN = "adjudicated_gold"
CANONICAL_EXTRACTION = "canonical_extraction"
CANONICAL_JOIN = "canonical_join"

#: The three verdicts a derived ledger record may carry.  ``unknown`` is never
#: 0 and never infinity; ``contradicted`` is never resolved into a choice.
VERDICTS = ("known", "unknown", "contradicted")
CONTRIBUTOR_ROLES = ("window", "dominated", "covered", "added")
VERSION_UNITS = ("instruments", "principal_usd")
FORM_CLASSES = ("424B", "periodic")
PERIODIC_FORMS = frozenset({"10-Q", "10-K", "10-QT", "10-KT", "20-F", "40-F", "6-K"})

#: Which usage question each observation kind answers (§3).  ``resale`` is its
#: own class because it never funds the company (A23, L98).
USAGE_CLASS_FOR_KIND: Mapping[str, str] = {
    "registered_takedown": "shelf_takedown",
    "atm_sales": "programme_sale",
    "resale": "resale",
    "warrant_exercise": "not_applicable",
    "conversion": "not_applicable",
    "redemption": "not_applicable",
    "repurchase": "not_applicable",
    "cancellation": "not_applicable",
    "outstanding_balance": "not_applicable",
    "instrument_issuance": "not_applicable",
}
#: A usage class fixes the target kind: only ``not_applicable`` is an instrument.
TARGET_KIND_FOR_USAGE_CLASS: Mapping[str, str] = {
    "shelf_takedown": "registration_path",
    "programme_sale": "registration_path",
    "resale": "registration_path",
    "not_applicable": "instrument",
}
#: Usage keys X0a computes.  ``resale`` deliberately has none (A23).
USAGE_KEY_CLASSES = ("shelf_takedown", "programme_sale")
USAGE_KEY_PREFIX: Mapping[str, str] = {"shelf_takedown": "shelf_usage", "programme_sale": "programme_usage"}

#: §5 flow directions.  A stock (``outstanding_balance``) is never a flow.
DECREMENT_KINDS = ("warrant_exercise", "conversion", "redemption", "repurchase", "cancellation")
INCREMENT_KINDS = ("instrument_issuance",)
FLOW_KINDS = DECREMENT_KINDS + INCREMENT_KINDS
STOCK_KIND = "outstanding_balance"
#: Instruments whose I0 unit is principal rather than a count (§5).
PRINCIPAL_INSTRUMENT_KINDS = ("convertible_note", "debt")

#: §6 share flows.  A resale is neither: it contributes exactly 0 (A23).
ISSUED_SHARE_KINDS = (
    "registered_takedown",
    "atm_sales",
    "warrant_exercise",
    "conversion",
    "instrument_issuance",
)
RETIRED_SHARE_KINDS = ("repurchase", "redemption", "cancellation")
SHARE_FLOW_KINDS = ISSUED_SHARE_KINDS + RETIRED_SHARE_KINDS

#: §7 realized cash.  ``warrant_exercise`` is settled by its settlement kind.
PROCEEDS_KINDS = ("registered_takedown", "atm_sales")
REPAYMENT_KINDS = ("redemption", "repurchase")
NO_CASH_KINDS = ("conversion", "resale", "cancellation", "outstanding_balance")
CASH_PAYING_SETTLEMENTS = ("cash", "pre_funded")
NO_CASH_SETTLEMENTS = ("cashless", "net_share")

#: Why an observation contributes nothing.  A deferral is a named reason, never
#: a silent drop and never a zero.
DEFERRAL_REASONS = (
    "no_binding",
    "binding_not_visible",
    "binding_superseded",
    "path_join_ambiguous",
)

#: The frozen §4-§7 rule text.  ``sha256_of(RULES)`` is the receipt's rule
#: digest, so a changed rule is a different receipt.
RULES: dict[str, Any] = {
    "a15_no_double_decrement": (
        "A cumulative usage figure and the individual transactions explaining it "
        "must not both decrement capacity (masterplan L98, gate A15). A window "
        "that contains another dominates it; an individual dated inside a maximal "
        "window is 'covered' and never adds; only individuals outside every window "
        "are 'added'."
    ),
    "a20_incomplete_history_is_unknown": (
        "Incomplete history is never usage 0 and never infinity. Without a "
        "completeness proof reaching as_of the usage is unknown and only the "
        "evidenced_floor - a true lower bound on dollar usage - is known. A window "
        "or event whose gross is unknown makes the usage unknown "
        "(usage_amount_unknown:<transaction_id>); share-denominated shelf usage is "
        "out of scope for X0a and contributes the same unknown."
    ),
    "a23_resale_funds_nobody": (
        "A resale by an existing holder normally does not itself fund the company "
        "(masterplan L98, gate A23). A resale yields 0 incremental shares, a "
        "no_cash realized-cash row, and never appears in shelf_usage, "
        "programme_usage or any instrument decrement."
    ),
    "a24_prefunded_residual_only": (
        "A pre-funded warrant exercise pays ONLY the residual actually paid at "
        "exercise; the prepaid amount is never counted again (masterplan L100, "
        "gate A24). Realized cash is never inferred from a scenario price."
    ),
    "a27_one_decrement_per_event": (
        "An already-issued security is never counted again as future issuance "
        "(gate A27, review focus 2). Observations of one economic event share one "
        "transaction_id and decrement once. Flows dated on or before the anchor "
        "balance are already reflected in it and are never applied again. Every "
        "prior instrument version is emitted with its supersedes_version_id; a "
        "version is never overwritten. A computed balance below 0 is contradicted "
        "(flows_exceed_balance) and is never clamped. An unexplained delta between "
        "two balances is reported and never plugged."
    ),
    "a09_closed_origins": (
        "Only canonical_extraction and adjudicated_gold may state a transaction; "
        "every other origin is refused (gate A09). canonical_join binds only on an "
        "exact unique SEC file number for the same issuer; an ambiguous or absent "
        "file number yields no binding and is deferred (path_join_ambiguous). An "
        "instrument binding is adjudicated_gold only."
    ),
    "window_dominance": (
        "Windows are ordered by (start, end descending, value descending, "
        "transaction_id). Window B is dominated when an earlier window A satisfies "
        "A.start <= B.start and B.end <= A.end; None start means INCEPTION. A "
        "dominated window whose value exceeds its container is contradicted "
        "(contained_window_exceeds_container) and never silently dropped."
    ),
    "window_overlap": (
        "Two non-dominated windows that partially overlap are not apportionable: "
        "usage is unknown (overlapping_cumulative_windows_not_apportionable). The "
        "evidenced_floor then takes the largest value in the overlapping cluster, "
        "which is still a true lower bound, never the sum."
    ),
    "individual_consistency": (
        "Covered individuals summing above their window's value are contradicted "
        "(individual_exceeds_cumulative). A contradiction makes usage contradicted, "
        "never a choice."
    ),
    "completeness": (
        "complete_through is the larger of (a) the end of the contiguous chain of "
        "maximal windows beginning at INCEPTION, each next window starting the day "
        "after the previous end, and (b) for shelf_takedown only, the "
        "complete_through of a visible 424B filing_coverage record for this issuer "
        "whose covered_from <= INCEPTION, whose complete_through <= as_of, and "
        "where no observation of that form class is deferred with a source date <= "
        "that date. Individual events alone never establish completeness."
    ),
    "inception": (
        "INCEPTION is the path's origin.sec_accepted_at date for shelf_takedown and "
        "the binding's programme_inception_date for programme_sale. Without a "
        "programme inception date only windows whose period_start is None - 'since "
        "inception' in the filing's own words - are inception-anchored."
    ),
    "usage_verdict": (
        "usage is known and equals evidenced_floor exactly when complete_through >= "
        "the as_of date and the window steps raised nothing; otherwise unknown with "
        "usage_history_incomplete:<usage_key>, whose resolving_fact names 424B final "
        "pricing supplements (shelf) or 10-Q/10-K ATM sales disclosures (programme) "
        "after complete_through, or since INCEPTION when there is none."
    ),
    "point_in_time": (
        "Nothing with available_at, decided_at, event_date or period_end after "
        "as_of is visible. A filing_coverage attestation whose complete_through is "
        "after as_of is future knowledge and establishes no completeness."
    ),
    "observation_agreement": (
        "Observations sharing a transaction_id must agree on kind, reporting basis, "
        "dates and every known numeric field. Disagreement is contradicted "
        "(transaction_observations_disagree:<transaction_id>) and contributes an "
        "unknown, never a choice. Gross absent with shares and price known is "
        "computed exactly (gross_derived); all three present and disagreeing is "
        "contradicted, never silently picked."
    ),
    "binding_choice": (
        "Among the visible non-superseded bindings of one observation the latest "
        "decided_at wins; a superseded binding is never used. Observations of one "
        "transaction bound to different targets are contradicted "
        "(transaction_bindings_disagree), never merged by guesswork."
    ),
    "share_reconciliation": (
        "evidenced_net_issuance is the sum over visible transactions dated in "
        "(d1, d2] of issued shares minus retired shares for the same security "
        "class. A transaction whose share count is unknown, or whose class is not "
        "stated, makes evidenced unknown. A cumulative window straddling d1 or d2 "
        "is not apportioned (window_straddles_observation). A resale contributes 0. "
        "unexplained_delta is observed minus evidenced and is never plugged."
    ),
    "realized_cash": (
        "One record per visible transaction: proceeds for a registered takedown, an "
        "ATM sale and a cash or pre-funded exercise (residual only); repayment for "
        "a redemption or repurchase; no_cash for a cashless or net-share exercise, "
        "a conversion, a resale, a cancellation, a balance and an issuance without "
        "a priced sale. gross_usd and net_usd are stated facts or unknown, never "
        "inferred from a scenario price."
    ),
    "retirement": (
        "An instrument whose I0 status is retired is not decremented again "
        "(already_retired). A computed balance of 0 on a non-retired instrument "
        "flags retirement_decision_pending and X0 never changes the I0 status. A "
        "positive balance after an I0 retirement is contradicted "
        "(retired_instrument_with_positive_balance)."
    ),
    "apply_outstanding": (
        "apply_outstanding returns a NEW InstrumentSet and never mutates its input. "
        "Each bound instrument's instruments_outstanding or principal_outstanding "
        "term is replaced by an X0-derived term whose origin is inherited from the "
        "anchor, whose effective_at is the version date and whose evidence is the "
        "anchor plus the flow evidence; Instrument.outstanding is set to the "
        "matching Quantity (instruments x shares_per_instrument when that term is "
        "known, basis assumed_as_converted; otherwise principal). Unbound "
        "instruments pass through byte-identical."
    ),
    "exact_arithmetic": (
        "Exact arithmetic only: Decimal strings, never float. A float input raises "
        "TypeError. No score, rank, sizing, probability or recommendation is "
        "produced, and the four supply components are never summed here."
    ),
}
RULE_DIGEST = sha256_of(RULES)

_SOURCE_KEYS = ("accession", "form", "sec_accepted_at", "mastermind_available_at", "file_number")
_SOURCE_REQUIRED_KEYS = ("accession", "form", "sec_accepted_at", "mastermind_available_at")
_COVERAGE_SOURCE_KEYS = ("manifest_generation_id", "filing_index_sha256")
_NUMERIC_FIELDS = (
    "shares",
    "price_per_share",
    "gross_proceeds_usd",
    "net_proceeds_usd",
    "principal_usd",
    "instruments",
)
_DATE_FIELDS = ("event_date", "period_start", "period_end")


# ---------------------------------------------------------------------------
# Exact-value helpers — a float is a type error, never a rounding decision
# ---------------------------------------------------------------------------


def _refuse_floats(value: Any, path: str = "<root>") -> None:
    """Reject a float anywhere in a record: exact decimal strings only (§2, A20)."""
    if isinstance(value, float):
        raise TypeError(f"{path}: a float is never accepted; an exact decimal string is required (got {value!r})")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _refuse_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _refuse_floats(item, f"{path}[{index}]")


def _exact(value: Any, label: str, *, signed: bool = False) -> str | None:
    """An exact nonnegative (or signed) decimal string, ``None``, or a refusal."""
    if value is None:
        return None
    if isinstance(value, float):
        raise TypeError(f"{label}: a float is never accepted; an exact decimal string is required (got {value!r})")
    if not isinstance(value, str):
        raise TypeError(f"{label}: an exact decimal string is required, got {type(value).__name__}")
    _require(bool(value), f"{label}: an empty string is not a decimal")
    # Plain text only: exponents, underscores and a leading '+' are refused (S4).
    _require(bool(_DECIMAL.match(value)), f"{label}: {value!r} is not a plain exact decimal")
    try:
        number = Decimal(value)
    except Exception as exc:  # InvalidOperation / ArithmeticError
        raise ContractViolation(f"{label}: {value!r} is not an exact decimal") from exc
    _require(number.is_finite(), f"{label}: must be finite, never infinity")
    if not signed:
        _require(number >= 0, f"{label}: must be nonnegative, got {value!r}")
    return value


def _decimal_text(value: Decimal) -> str:
    """Plain, exponent-free exact text; never ``-0``."""
    with localcontext() as context:
        context.prec = 60
        text = format(value.normalize(), "f")
    if text in ("-0", "-0.0"):
        return "0"
    return text


def _dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _instant(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"{label}: {value!r} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{label}: timestamp must carry a timezone")
    return parsed


def _day(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ContractViolation(f"{label}: {value!r} is not an ISO date") from exc


def _daystamp(day: date) -> str:
    """The version/effective timestamp of a date, at midnight UTC."""
    return f"{day.isoformat()}T00:00:00Z"


def _form_class(form: Any) -> str | None:
    text = str(form or "").strip().upper()
    if not text:
        return None
    if text.startswith("424B"):
        return "424B"
    if text in PERIODIC_FORMS:
        return "periodic"
    return None


def _evidence_union(groups: Sequence[Sequence[Any]]) -> tuple[EvidenceRef, ...]:
    seen: dict[tuple[str, str, str], EvidenceRef] = {}
    for group in groups:
        for item in group:
            if isinstance(item, EvidenceRef):
                seen[(item.manifest_id, item.span_id, item.text_sha256)] = item
    return tuple(seen[key] for key in sorted(seen))


def _records_of(items: Sequence[EvidenceRef]) -> tuple[dict[str, Any], ...]:
    return tuple(item.as_record() for item in items)

def _derived_id(prefix: str, cls: type, kwargs: Mapping[str, Any], id_field: str) -> str:
    """Content-addressed id over the record body minus the id itself (§2, §3, §4.1)."""
    body: dict[str, Any] = {}
    for item in dataclasses.fields(cls):  # type: ignore[arg-type]
        if item.name == id_field:
            continue
        if item.name in kwargs:
            value = kwargs[item.name]
        elif item.default is not dataclasses.MISSING:
            value = item.default
        else:
            raise ContractViolation(f"{cls.__name__}.build: {item.name!r} is required")
        body[item.name] = _record(value)
    return stable_id(prefix, body)




# ---------------------------------------------------------------------------
# §2 Observation record — WHAT the filing says, never which target it belongs to
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TransactionObservation:
    """One pre-identity statement of what a retained filing says (§2)."""

    observation_id: str
    issuer_id: str
    kind: str
    reporting_basis: str
    source: Mapping[str, Any]
    evidence: tuple[EvidenceRef, ...]
    origin: str
    available_at: str
    schema: str = OBSERVATION_SCHEMA
    event_date: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    shares: str | None = None
    price_per_share: str | None = None
    gross_proceeds_usd: str | None = None
    net_proceeds_usd: str | None = None
    principal_usd: str | None = None
    instruments: str | None = None
    settlement: str | None = None
    security_class_id: str | None = None
    extraction_method: str | None = None
    decided_at: str | None = None

    def __post_init__(self) -> None:
        _refuse_floats(_plain(self), "transaction_observation")
        label = "transaction_observation"
        _require(self.schema == OBSERVATION_SCHEMA, f"{label}.schema: must be {OBSERVATION_SCHEMA!r}")
        _identifier(self.observation_id, f"{label}.observation_id")
        _identifier(self.issuer_id, f"{label}.issuer_id")
        _member(self.kind, TRANSACTION_KINDS, f"{label}.kind")
        _member(self.reporting_basis, REPORTING_BASES, f"{label}.reporting_basis")
        _member(self.origin, TRANSACTION_ORIGINS, f"{label}.origin")

        object.__setattr__(self, "evidence", tuple(self.evidence))
        for item in self.evidence:
            _require(isinstance(item, EvidenceRef), f"{label}.evidence: EvidenceRef required")
        _require(len(self.evidence) > 0, f"{label}.evidence: at least one reference required")

        object.__setattr__(self, "source", dict(self.source))
        _require(set(self.source) <= set(_SOURCE_KEYS), f"{label}.source: closed key set {list(_SOURCE_KEYS)}")
        for key in _SOURCE_REQUIRED_KEYS:
            value = self.source.get(key)
            _require(isinstance(value, str) and bool(value.strip()), f"{label}.source.{key}: non-empty string required")
        for key in ("sec_accepted_at", "mastermind_available_at"):
            _timestamp(self.source[key], f"{label}.source.{key}")
        if self.source.get("file_number") is not None:
            _identifier(self.source["file_number"], f"{label}.source.file_number")

        # reporting_basis / kind coupling (§2)
        if self.reporting_basis == "point_in_time":
            _require(self.kind == STOCK_KIND, f"{label}: point_in_time is reserved for {STOCK_KIND!r}")
        if self.kind == STOCK_KIND:
            _require(self.reporting_basis == "point_in_time", f"{label}: {STOCK_KIND!r} must be point_in_time")

        for name in _DATE_FIELDS:
            value = getattr(self, name)
            if value is not None:
                _date(value, f"{label}.{name}")
        if self.reporting_basis in ("individual", "point_in_time"):
            _require(self.event_date is not None, f"{label}.event_date: required for {self.reporting_basis!r}")
            _require(self.period_start is None and self.period_end is None,
                     f"{label}: a {self.reporting_basis!r} observation carries no window")
        else:
            _require(self.event_date is None, f"{label}.event_date: a cumulative observation carries no event date")
            _require(self.period_end is not None, f"{label}.period_end: required for 'cumulative'")
            if self.period_start is not None:
                _require(self.period_start <= self.period_end,
                         f"{label}: period_start {self.period_start!r} is after period_end {self.period_end!r}")

        for name in _NUMERIC_FIELDS:
            object.__setattr__(self, name, _exact(getattr(self, name), f"{label}.{name}"))
        if self.net_proceeds_usd is not None and self.gross_proceeds_usd is not None:
            _require(Decimal(self.net_proceeds_usd) <= Decimal(self.gross_proceeds_usd),
                     f"{label}: net_proceeds_usd {self.net_proceeds_usd!r} exceeds gross {self.gross_proceeds_usd!r}")

        if self.settlement is not None:
            _member(self.settlement, SETTLEMENTS, f"{label}.settlement")
        if self.kind == "warrant_exercise":
            _require(self.settlement is not None, f"{label}.settlement: required for a warrant_exercise")
        if self.security_class_id is not None:
            _identifier(self.security_class_id, f"{label}.security_class_id")

        if self.origin == CANONICAL_EXTRACTION:
            _require(isinstance(self.extraction_method, str) and bool(self.extraction_method.strip()),
                     f"{label}.extraction_method: required for a canonical_extraction origin")
            _require(self.decided_at is None, f"{label}.decided_at: only an adjudicated_gold origin is decided")
        else:
            _require(self.extraction_method is None,
                     f"{label}.extraction_method: an adjudicated_gold origin carries no extraction method")
            _require(self.decided_at is not None, f"{label}.decided_at: required for an adjudicated_gold origin")
        if self.decided_at is not None:
            _timestamp(self.decided_at, f"{label}.decided_at")

        _timestamp(self.available_at, f"{label}.available_at")
        available = _instant(self.available_at, f"{label}.available_at")
        _require(available >= _instant(self.source["mastermind_available_at"], f"{label}.source.mastermind_available_at"),
                 f"{label}.available_at: earlier than source.mastermind_available_at")
        # An event dated in the future of its own availability is not a fact yet.
        for name in _DATE_FIELDS:
            value = getattr(self, name)
            if value is not None:
                _require(_day(value, f"{label}.{name}") <= available.date(),
                         f"{label}.{name}: {value!r} is in the future of available_at")

        expected = stable_id("txobs", self.body())
        _require(self.observation_id == expected,
                 f"{label}.observation_id: must be stable_id('txobs', body), expected {expected!r}")

    def body(self) -> dict[str, Any]:
        """The content-addressed body: every field except ``observation_id``."""
        record = _plain(self)
        record.pop("observation_id", None)
        return record

    @classmethod
    def build(cls, **kwargs: Any) -> "TransactionObservation":
        """Build with a derived ``observation_id``; the id is never invented."""
        kwargs = {key: value for key, value in kwargs.items() if key != "observation_id"}
        return cls(observation_id=_derived_id("txobs", cls, kwargs, "observation_id"), **kwargs)

    @property
    def source_date(self) -> str | None:
        """The filing's own date, for a deferral's completeness check (§4 6b)."""
        return self.event_date or self.period_end or _instant(
            self.source["sec_accepted_at"], "transaction_observation.source.sec_accepted_at"
        ).date().isoformat()

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


# ---------------------------------------------------------------------------
# §3 Binding record — which target an observation belongs to
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TransactionBinding:
    """One adjudicated or canonically joined observation → target binding (§3)."""

    binding_id: str
    observation_id: str
    target_kind: str
    target_id: str
    transaction_id: str
    usage_class: str
    origin: str
    decided_at: str
    schema: str = BINDING_SCHEMA
    programme_key: str | None = None
    programme_inception_date: str | None = None
    supersedes: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _refuse_floats(_plain(self), "transaction_binding")
        label = "transaction_binding"
        _require(self.schema == BINDING_SCHEMA, f"{label}.schema: must be {BINDING_SCHEMA!r}")
        _identifier(self.binding_id, f"{label}.binding_id")
        _identifier(self.observation_id, f"{label}.observation_id")
        _identifier(self.target_id, f"{label}.target_id")
        _identifier(self.transaction_id, f"{label}.transaction_id")
        _member(self.target_kind, BINDING_TARGET_KINDS, f"{label}.target_kind")
        _member(self.usage_class, USAGE_CLASSES, f"{label}.usage_class")
        _member(self.origin, BINDING_ORIGINS, f"{label}.origin")
        _timestamp(self.decided_at, f"{label}.decided_at")
        _require(
            self.target_kind == TARGET_KIND_FOR_USAGE_CLASS[self.usage_class],
            f"{label}: usage_class {self.usage_class!r} binds a "
            f"{TARGET_KIND_FOR_USAGE_CLASS[self.usage_class]!r}, got {self.target_kind!r}",
        )
        if self.programme_key is not None:
            _identifier(self.programme_key, f"{label}.programme_key")
            _require(self.usage_class == "programme_sale",
                     f"{label}.programme_key: only a programme_sale binding carries one")
        if self.programme_inception_date is not None:
            _date(self.programme_inception_date, f"{label}.programme_inception_date")
            _require(self.origin == GOLD_ORIGIN and self.usage_class == "programme_sale",
                     f"{label}.programme_inception_date: only an adjudicated_gold programme_sale binding carries one")
        if self.origin == CANONICAL_JOIN:
            _require(self.target_kind == "registration_path",
                     f"{label}: canonical_join binds only a registration_path")
        if self.supersedes is not None:
            _identifier(self.supersedes, f"{label}.supersedes")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        for item in self.evidence:
            _require(isinstance(item, EvidenceRef), f"{label}.evidence: EvidenceRef required")
        if self.origin == GOLD_ORIGIN:
            _require(len(self.evidence) > 0, f"{label}.evidence: an adjudicated_gold binding carries evidence")
        expected = stable_id("txbind", self.body())
        _require(self.binding_id == expected,
                 f"{label}.binding_id: must be stable_id('txbind', body), expected {expected!r}")

    def body(self) -> dict[str, Any]:
        record = _plain(self)
        record.pop("binding_id", None)
        return record

    @classmethod
    def build(cls, **kwargs: Any) -> "TransactionBinding":
        """Build with a derived ``binding_id``; the id is never invented."""
        kwargs = {key: value for key, value in kwargs.items() if key != "binding_id"}
        return cls(binding_id=_derived_id("txbind", cls, kwargs, "binding_id"), **kwargs)

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


# ---------------------------------------------------------------------------
# §4.1 Filing coverage — an attestation produced by X0b, only consumed here
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class FilingCoverage:
    """Every filing of one form class in one window was retrieved and extracted."""

    coverage_id: str
    issuer_id: str
    form_class: str
    covered_from: str
    complete_through: str
    source: Mapping[str, Any]
    extractor_implementation: str
    available_at: str
    schema: str = FILING_COVERAGE_SCHEMA

    def __post_init__(self) -> None:
        _refuse_floats(_plain(self), "transaction_filing_coverage")
        label = "transaction_filing_coverage"
        _require(self.schema == FILING_COVERAGE_SCHEMA, f"{label}.schema: must be {FILING_COVERAGE_SCHEMA!r}")
        _identifier(self.coverage_id, f"{label}.coverage_id")
        _identifier(self.issuer_id, f"{label}.issuer_id")
        _member(self.form_class, FORM_CLASSES, f"{label}.form_class")
        _date(self.covered_from, f"{label}.covered_from")
        _date(self.complete_through, f"{label}.complete_through")
        _require(self.covered_from <= self.complete_through,
                 f"{label}: covered_from {self.covered_from!r} is after complete_through {self.complete_through!r}")
        object.__setattr__(self, "source", dict(self.source))
        _require(set(self.source) == set(_COVERAGE_SOURCE_KEYS),
                 f"{label}.source: exactly {list(_COVERAGE_SOURCE_KEYS)} required")
        _identifier(self.source["manifest_generation_id"], f"{label}.source.manifest_generation_id")
        _require(isinstance(self.source["filing_index_sha256"], str)
                 and len(self.source["filing_index_sha256"]) == 64
                 and all(ch in "0123456789abcdefABCDEF" for ch in self.source["filing_index_sha256"]),
                 f"{label}.source.filing_index_sha256: sha256 hex required")
        _require(isinstance(self.extractor_implementation, str) and bool(self.extractor_implementation.strip()),
                 f"{label}.extractor_implementation: non-empty string required")
        _timestamp(self.available_at, f"{label}.available_at")
        expected = stable_id("txcov", self.body())
        _require(self.coverage_id == expected,
                 f"{label}.coverage_id: must be stable_id('txcov', body), expected {expected!r}")

    def body(self) -> dict[str, Any]:
        record = _plain(self)
        record.pop("coverage_id", None)
        return record

    @classmethod
    def build(cls, **kwargs: Any) -> "FilingCoverage":
        """Build with a derived ``coverage_id``; the id is never invented."""
        kwargs = {key: value for key, value in kwargs.items() if key != "coverage_id"}
        return cls(coverage_id=_derived_id("txcov", cls, kwargs, "coverage_id"), **kwargs)

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


# ---------------------------------------------------------------------------
# Unknown collection — an unknown is a named fact, never a zero
# ---------------------------------------------------------------------------


class _Unknowns:
    """De-duplicating, deterministically ordered ``Unknown`` collector."""

    def __init__(self) -> None:
        self._items: dict[str, Unknown] = {}

    def add(self, unknown: Unknown) -> str:
        existing = self._items.get(unknown.unknown_id)
        if existing is None:
            self._items[unknown.unknown_id] = unknown
        return unknown.unknown_id

    def note(self, unknown_id: str, description: str, resolving_fact: str, affects: Sequence[str]) -> str:
        return self.add(Unknown(unknown_id, description, resolving_fact, tuple(affects)))

    def sorted(self) -> tuple[Unknown, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


_BEGIN = date(1, 1, 1)


@dataclasses.dataclass(frozen=True)
class _Window:
    """One cumulative usage window, normalized for the §4 dominance order."""

    transaction_id: str
    start: date | None
    end: date
    value: Decimal | None

    @property
    def start_key(self) -> date:
        return self.start if self.start is not None else _BEGIN

    def sort_key(self) -> tuple[Any, ...]:
        return (
            self.start_key.toordinal(),
            -self.end.toordinal(),
            Decimal(0) if self.value is None else -self.value,
            self.transaction_id,
        )

    def contains(self, other: "_Window") -> bool:
        return self.start_key <= other.start_key and other.end <= self.end

    def overlaps(self, other: "_Window") -> bool:
        return self.start_key <= other.end and other.start_key <= self.end


def _clusters(windows: Sequence[_Window]) -> list[list[_Window]]:
    """Transitively group maximal windows that partially overlap."""
    groups: list[list[_Window]] = [[item] for item in windows]
    merged = True
    while merged:
        merged = False
        for index in range(len(groups)):
            for other in range(index + 1, len(groups)):
                if any(a.overlaps(b) for a in groups[index] for b in groups[other]):
                    groups[index] = groups[index] + groups[other]
                    del groups[other]
                    merged = True
                    break
            if merged:
                break
    return groups


def _usage_record(
    *,
    usage_key: str,
    usage_class: str,
    path_id: str,
    transactions: Sequence[Mapping[str, Any]],
    inception: date | None,
    coverage: Sequence[FilingCoverage],
    deferred: Sequence[Mapping[str, Any]],
    as_of_date: date,
    unknowns: _Unknowns,
) -> dict[str, Any]:
    """§4 usage coverage for one (path, usage_class[, programme]) key."""
    reasons: list[str] = []
    contradicted = False
    incomplete_amount = False
    floor_known = True

    for item in transactions:
        for reason in item["contradictions"]:
            contradicted = True
            reasons.append(reason)
        if item["gross_proceeds_usd"] is None:
            # Usage is dollar usage only: an unknown gross, including a
            # share-denominated takedown, makes the whole answer unknown (A20).
            incomplete_amount = True
            unknown_id = f"usage_amount_unknown:{item['transaction_id']}"
            reasons.append(unknown_id)
            unknowns.note(
                unknown_id,
                f"the gross dollar amount of transaction {item['transaction_id']} is not stated",
                "a priced 424B final pricing supplement or a 10-Q/10-K disclosure stating the gross dollar amount",
                (usage_key,),
            )

    windows = [
        _Window(item["transaction_id"],
                _day(item["period_start"], "period_start") if item["period_start"] else inception,
                _day(item["period_end"], "period_end"),
                _dec(item["gross_proceeds_usd"]))
        for item in transactions if item["reporting_basis"] == "cumulative"
    ]
    individuals = [item for item in transactions if item["reporting_basis"] == "individual"]

    # -- step 1: containment ------------------------------------------------
    ordered = sorted(windows, key=_Window.sort_key)
    maximal: list[_Window] = []
    dominated: list[_Window] = []
    for index, candidate in enumerate(ordered):
        if any(item.contains(candidate) for item in ordered[:index]):
            dominated.append(candidate)
        else:
            maximal.append(candidate)
    # A contained window can never exceed its container.  Every ordered pair is
    # checked, not only the sort order's containers: two identical windows
    # contain each other, so two different amounts for one window contradict.
    exceeding = sorted({
        inner.transaction_id
        for outer in ordered for inner in ordered
        if inner is not outer and outer.contains(inner)
        and inner.value is not None and outer.value is not None and inner.value > outer.value
    })
    for transaction_id in exceeding:
        contradicted = True
        reasons.append(f"contained_window_exceeds_container:{transaction_id}")

    maximal = sorted(maximal, key=lambda item: (item.start_key.toordinal(), item.end.toordinal(), item.transaction_id))
    roles: dict[str, str] = {item.transaction_id: "window" for item in maximal}
    roles.update({item.transaction_id: "dominated" for item in dominated})

    # -- steps 2 and 3: overlap is not apportionable; disjoint windows sum ---
    floor: Decimal | None = Decimal(0)
    overlapped = False
    for group in _clusters(maximal):
        if len(group) > 1:
            overlapped = True
            known = [item.value for item in group if item.value is not None]
            if not known:
                floor_known = False
            elif floor is not None:
                # A true lower bound on an unapportionable overlap is its largest
                # single window, never the sum of windows that may share sales.
                floor += max(known)
            continue
        value = group[0].value
        if value is None:
            floor_known = False
        elif floor is not None:
            floor += value
    if overlapped:
        unknown_id = f"overlapping_cumulative_windows_not_apportionable:{path_id}"
        reasons.append(unknown_id)
        unknowns.note(
            unknown_id,
            f"two cumulative usage windows under {usage_key} partially overlap and cannot be apportioned",
            "cumulative usage windows with non-overlapping period_start and period_end dates",
            (usage_key,),
        )

    # -- steps 4 and 5: covered individuals never add -----------------------
    covered_totals: dict[str, Decimal | None] = {}
    window_by_id = {item.transaction_id: item for item in maximal}
    added: list[tuple[date, Decimal | None]] = []
    for item in sorted(individuals, key=lambda row: (row["event_date"] or "", row["transaction_id"])):
        value = _dec(item["gross_proceeds_usd"])
        day = _day(item["event_date"], "event_date")
        covering = [w for w in maximal if w.start_key <= day <= w.end]
        if covering:
            roles[item["transaction_id"]] = "covered"
            key = covering[0].transaction_id
            previous = covered_totals.get(key, Decimal(0))
            covered_totals[key] = None if (previous is None or value is None) else previous + value
            continue
        roles[item["transaction_id"]] = "added"
        if value is None:
            floor_known = False
        elif floor is not None:
            floor += value
        added.append((day, value))
    for transaction_id, total in sorted(covered_totals.items()):
        window = window_by_id[transaction_id]
        if total is not None and window.value is not None and total > window.value:
            contradicted = True
            reasons.append(f"individual_exceeds_cumulative:{transaction_id}")

    # -- step 6a: the contiguous chain of maximal windows from INCEPTION ----
    chain: list[_Window] = []
    if inception is not None:
        anchors = [item for item in maximal if item.start_key <= inception]
    else:
        anchors = [item for item in maximal if item.start is None]
    if anchors:
        current = max(anchors, key=lambda item: (item.end.toordinal(), item.transaction_id))
        chain.append(current)
        while True:
            next_day = current.end + timedelta(days=1)
            following = [item for item in maximal if item not in chain and item.start_key == next_day]
            if not following:
                break
            current = max(following, key=lambda item: (item.end.toordinal(), item.transaction_id))
            chain.append(current)
    complete_through = chain[-1].end if chain else None

    chain_total: Decimal | None = Decimal(0)
    for item in chain:
        if item.value is None:
            chain_total = None
        elif chain_total is not None:
            chain_total += item.value

    # -- step 6b: a 424B filing-coverage attestation (shelf only) -----------
    if usage_class == "shelf_takedown" and inception is not None:
        for record in sorted(coverage, key=lambda item: item.coverage_id):
            if record.form_class != "424B":
                continue
            if _day(record.covered_from, "covered_from") > inception:
                continue
            through = _day(record.complete_through, "complete_through")
            if through > as_of_date:
                # A completeness attestation reaching past as_of is future knowledge.
                continue
            blocked = any(
                row["form_class"] == "424B" and row["source_date"] is not None
                and _day(row["source_date"], "deferred.source_date") <= through
                for row in deferred
            )
            if blocked:
                continue
            if complete_through is None or through > complete_through:
                complete_through = through

    # -- step 7: the verdict ------------------------------------------------
    resolving = (
        "424B final pricing supplements" if usage_class == "shelf_takedown" else "10-Q/10-K ATM sales disclosures"
    )
    since = complete_through.isoformat() if complete_through is not None else (
        inception.isoformat() if inception is not None else "the path's inception"
    )
    if contradicted:
        status = "contradicted"
    elif incomplete_amount or overlapped or not floor_known:
        status = "unknown"
    elif complete_through is not None and complete_through >= as_of_date:
        status = "known"
    else:
        status = "unknown"
        unknown_id = f"usage_history_incomplete:{usage_key}"
        reasons.append(unknown_id)
        unknowns.note(
            unknown_id,
            f"the usage history of {usage_key} is not complete through {as_of_date.isoformat()}"
            f"{'' if complete_through is None else f'; it is complete only through {complete_through.isoformat()}'}",
            f"{resolving} after {since}",
            (usage_key,),
        )

    if contradicted:
        # Contradicting documents leave no bound C2 may rely on (S2).
        floor_quantity = Quantity(unit="usd", status="contradicted", note="; ".join(sorted(set(reasons))) or None)
    elif not floor_known:
        floor_quantity = Quantity.unknown("usd", note="; ".join(sorted(set(reasons))) or None)
    else:
        floor_quantity = Quantity.known(_decimal_text(floor or Decimal(0)), "usd")

    if status == "known":
        usage = Quantity.known(_decimal_text(floor or Decimal(0)), "usd")
    elif status == "contradicted":
        usage = Quantity(unit="usd", status="contradicted", note="; ".join(sorted(set(reasons))) or None)
    else:
        usage = Quantity.unknown("usd", note="; ".join(sorted(set(reasons))) or None)

    # Added individuals split around the completeness date (§4 step 8).
    through_quantity: Quantity | None = None
    post_quantity: Quantity | None = None
    if complete_through is not None:
        before: Decimal | None = Decimal(0)
        after: Decimal | None = Decimal(0)
        for day, value in added:
            bucket_is_before = day <= complete_through
            if value is None:
                before = None
                after = None
            elif bucket_is_before:
                if before is not None:
                    before += value
            elif after is not None:
                after += value
        if chain_total is None or before is None:
            through_quantity = Quantity.unknown("usd")
        else:
            through_quantity = Quantity.known(_decimal_text(chain_total + before), "usd")
        post_quantity = Quantity.unknown("usd") if after is None else Quantity.known(_decimal_text(after), "usd")

    return {
        "schema": USAGE_SCHEMA,
        "usage_key": usage_key,
        "evidenced_floor": floor_quantity.as_record(),
        "complete_through": complete_through.isoformat() if complete_through else None,
        "usage_through_complete": None if through_quantity is None else through_quantity.as_record(),
        "post_window_additions": None if post_quantity is None else post_quantity.as_record(),
        "usage": usage.as_record(),
        "contributors": [
            {"transaction_id": transaction_id, "role": roles[transaction_id]}
            for transaction_id in sorted(roles)
        ],
        "status": status,
    }


def _instrument_unit(
    transactions: Sequence[Mapping[str, Any]], instrument: Instrument | None
) -> tuple[str, bool]:
    """The I0 unit of one instrument, and whether the evidence leaves it ambiguous."""
    if instrument is not None:
        return ("principal_usd" if instrument.kind in PRINCIPAL_INSTRUMENT_KINDS else "instruments"), False
    counted = any(item["instruments"] is not None for item in transactions)
    principal = any(item["principal_usd"] is not None for item in transactions)
    if counted and principal:
        return "instruments", True
    return ("principal_usd", False) if principal else ("instruments", False)


class _Cover(NamedTuple):
    """How the flows of one interval count, by the §4 window-coverage rules."""

    counted: list[Mapping[str, Any]]
    covered: list[Mapping[str, Any]]
    unknown: list[tuple[str, Mapping[str, Any]]]
    contradicted: list[tuple[str, Mapping[str, Any]]]


def _cover_group(row: Mapping[str, Any]) -> tuple[Any, ...]:
    """Windows and events cover each other only within one kind, target and programme."""
    return (row["kind"], row["target_kind"], row["target_id"], row["programme_key"])


def _effective(row: Mapping[str, Any]) -> date:
    """The day a flow or balance takes effect: its event date, or a window's end."""
    return _day(row["event_date"] or row["period_end"], "event_date")


def _interval_cover(
    rows: Sequence[Mapping[str, Any]],
    lo: date,
    hi: date,
    quantity: Callable[[Mapping[str, Any]], Decimal | None],
) -> _Cover:
    """Window coverage of the flows in the interval ``(lo, hi]``.

    A cumulative window counts only when it lies wholly inside the interval;
    one that straddles either end is unknown and never apportioned.  Inside
    the interval the §4 rules apply per cover group: a contained window is
    dominated, an individual event inside a maximal window is covered, a
    contained window larger than its container is contradicted, and
    partially overlapping maximal windows are unknown.  A contradicted flow
    never counts.
    """
    counted: list[Mapping[str, Any]] = []
    covered: list[Mapping[str, Any]] = []
    unknown: list[tuple[str, Mapping[str, Any]]] = []
    contradicted: list[tuple[str, Mapping[str, Any]]] = []
    inside: dict[tuple[Any, ...], list[_Window]] = {}
    dated: list[tuple[date, Mapping[str, Any]]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    ordered = sorted(rows, key=lambda row: (row["event_date"] or row["period_end"] or "", row["transaction_id"]))
    for row in ordered:
        if row["reporting_basis"] == "cumulative":
            end = _day(row["period_end"], "period_end")
            start = _day(row["period_start"], "period_start") if row["period_start"] else None
            if end <= lo or (start is not None and start > hi):
                continue
            if start is None or start <= lo or end > hi:
                unknown.append(("window_straddles_interval", row))
            elif row["status"] == "contradicted":
                contradicted.append(("contradicted_flow", row))
            else:
                by_id[row["transaction_id"]] = row
                inside.setdefault(_cover_group(row), []).append(
                    _Window(row["transaction_id"], start, end, quantity(row)))
            continue
        day = _day(row["event_date"], "event_date")
        if not lo < day <= hi:
            continue
        if row["status"] == "contradicted":
            contradicted.append(("contradicted_flow", row))
        else:
            dated.append((day, row))

    maximal: dict[tuple[Any, ...], list[_Window]] = {}
    for group, members in inside.items():
        windows = sorted(members, key=_Window.sort_key)
        tops: list[_Window] = []
        for index, window in enumerate(windows):
            if any(earlier.contains(window) for earlier in windows[:index]):
                covered.append(by_id[window.transaction_id])
            else:
                tops.append(window)
        # Every pair, not only the dominating one: a nested window larger than
        # any window containing it is a contradiction, never a dominated row.
        for outer in windows:
            for inner in windows:
                if (inner is not outer and outer.contains(inner)
                        and inner.value is not None and outer.value is not None and inner.value > outer.value):
                    contradicted.append(("contained_window_exceeds_container", by_id[inner.transaction_id]))
        maximal[group] = tops
        for window in tops:
            if any(other is not window and other.overlaps(window) for other in tops):
                unknown.append(("overlapping_cumulative_windows_not_apportionable", by_id[window.transaction_id]))
            else:
                counted.append(by_id[window.transaction_id])

    covered_totals: dict[str, Decimal] = {}
    for day, row in dated:
        holders = [window for window in maximal.get(_cover_group(row), ()) if window.start_key <= day <= window.end]
        if not holders:
            counted.append(row)
            continue
        covered.append(row)
        value = quantity(row)
        if value is not None:
            covered_totals[holders[0].transaction_id] = covered_totals.get(holders[0].transaction_id, Decimal(0)) + value
    for windows in maximal.values():
        for window in windows:
            total = covered_totals.get(window.transaction_id)
            if total is not None and window.value is not None and total > window.value:
                contradicted.append(("individual_exceeds_cumulative", by_id[window.transaction_id]))

    def unique(problems: list[tuple[str, Mapping[str, Any]]]) -> list[tuple[str, Mapping[str, Any]]]:
        seen: dict[tuple[str, str], tuple[str, Mapping[str, Any]]] = {}
        for reason, row in problems:
            seen.setdefault((reason, row["transaction_id"]), (reason, row))
        return [seen[key] for key in sorted(seen)]

    return _Cover(counted, covered, unique(unknown), unique(contradicted))


def _first_day(row: Mapping[str, Any], floor: date) -> date:
    """The first day a coverage problem reaches, never before ``floor``."""
    if row["reporting_basis"] == "cumulative":
        start = _day(row["period_start"], "period_start") if row["period_start"] else None
        return floor if start is None else max(floor, start)
    return max(floor, _day(row["event_date"], "event_date"))


def _instrument_versions(
    *,
    instrument_id: str,
    transactions: Sequence[Mapping[str, Any]],
    instrument: Instrument | None,
    as_of_date: date,
    unknowns: _Unknowns,
) -> list[dict[str, Any]]:
    """§5 instrument versions: anchor, post-anchor flows and every prior version."""
    unit, ambiguous = _instrument_unit(transactions, instrument)
    retired = instrument is not None and instrument.status == "retired"
    affects = (f"instrument:{instrument_id}",)

    def quantity_of(item: Mapping[str, Any]) -> Decimal | None:
        return _dec(item["instruments"] if unit == "instruments" else item["principal_usd"])

    if ambiguous:
        unknowns.note(
            f"instrument_unit_ambiguous:{instrument_id}",
            f"transactions bound to {instrument_id} state both an instrument count and a principal amount",
            "the I0 instrument kind for this instrument, which fixes its unit",
            affects,
        )

    balances = sorted(
        (item for item in transactions if item["kind"] == STOCK_KIND),
        key=lambda item: (_effective(item), item["transaction_id"]),
    )
    flows = [item for item in transactions if item["kind"] in FLOW_KINDS]
    entries: list[dict[str, Any]] = []

    def emit(*, effective_date: date, outstanding: Decimal | None, status: str,
             basis: Sequence[str], flags: Sequence[str] = (),
             decrease: Decimal | None = None, increase: Decimal | None = None,
             unexplained: Decimal | None = None) -> None:
        entries.append({
            "effective_date": effective_date.isoformat(),
            "unit": unit,
            "outstanding": None if outstanding is None else _decimal_text(outstanding),
            "status": status,
            "basis_transaction_ids": sorted(set(basis)),
            "explained_decrease": None if decrease is None else _decimal_text(decrease),
            "explained_increase": None if increase is None else _decimal_text(increase),
            "unexplained_delta": None if unexplained is None else _decimal_text(unexplained),
            "flags": sorted(set(flags)),
        })

    def note_amount(row: Mapping[str, Any]) -> None:
        unknowns.note(
            f"instrument_flow_amount_unknown:{row['transaction_id']}",
            f"a {row['kind']} flow on {_effective(row).isoformat()} states no {unit} amount",
            f"a filing stating the {unit} amount of that {row['kind']}",
            affects,
        )

    def note_window(reason: str, row: Mapping[str, Any]) -> None:
        span = f"{row['period_start'] or 'inception'} to {row['period_end']}"
        if reason == "window_straddles_interval":
            description = (f"the cumulative {row['kind']} window of {row['transaction_id']} ({span}) "
                           f"straddles a balance date of {instrument_id} and is not apportioned")
        else:
            description = (f"the cumulative {row['kind']} window of {row['transaction_id']} ({span}) "
                           "partially overlaps another window and is not apportioned")
        unknowns.note(
            f"instrument_flow_window_not_apportioned:{row['transaction_id']}",
            description,
            f"{row['kind']} figures whose windows nest, or fall wholly between two balance dates of this instrument",
            affects,
        )

    if not balances:
        unknowns.note(
            f"instrument_balance_missing:{instrument_id}",
            f"no outstanding_balance observation for {instrument_id} is visible at as_of",
            "a point-in-time outstanding balance disclosure for this instrument on or before as_of",
            affects,
        )
        emit(effective_date=as_of_date, outstanding=None, status="unknown", basis=())
        return _mint_versions(instrument_id, entries)

    by_day: dict[date, list[Mapping[str, Any]]] = {}
    for item in balances:
        by_day.setdefault(_effective(item), []).append(item)

    previous: tuple[date, Decimal | None] | None = None
    anchor_date = as_of_date
    anchor_value: Decimal | None = None
    anchor_ids: list[str] = []
    for day, rows in by_day.items():
        ids = [row["transaction_id"] for row in rows]
        flags: list[str] = []
        values = {quantity_of(row) for row in rows if row["status"] != "contradicted"} - {None}
        value: Decimal | None
        if any(row["status"] == "contradicted" for row in rows) or len(values) > 1:
            # Two balances for one day that disagree are a contradiction, never a choice.
            status, value = "contradicted", None
            if len(rows) > 1:
                flags.append(f"conflicting_balances:{instrument_id}")
        elif values:
            status, value = "known", next(iter(values))
        else:
            status, value = "unknown", None
            for row in rows:
                unknowns.note(
                    f"instrument_balance_unknown:{row['transaction_id']}",
                    f"the outstanding_balance of {instrument_id} on {day.isoformat()} states no {unit} amount",
                    f"a balance disclosure stating the {unit} amount outstanding",
                    affects,
                )
        decrease = increase = unexplained = None
        if previous is not None and previous[1] is not None and value is not None:
            cover = _interval_cover(flows, previous[0], day, quantity_of)
            if cover.contradicted:
                flags.extend(f"{reason}:{row['transaction_id']}" for reason, row in cover.contradicted)
            elif cover.unknown:
                for reason, row in cover.unknown:
                    note_window(reason, row)
            else:
                missing = [row for row in cover.counted if quantity_of(row) is None]
                for row in missing:
                    note_amount(row)
                if not missing:
                    decrease = sum((quantity_of(row) for row in cover.counted if row["kind"] in DECREMENT_KINDS), Decimal(0))
                    increase = sum((quantity_of(row) for row in cover.counted if row["kind"] in INCREMENT_KINDS), Decimal(0))
                    # Never plugged: the residual is reported exactly, whatever it is.
                    unexplained = value - (previous[1] - decrease + increase)
        emit(effective_date=day, outstanding=value, status=status, basis=ids, flags=flags,
             decrease=decrease, increase=increase, unexplained=unexplained)
        previous = (day, value)
        anchor_date, anchor_value, anchor_ids = day, value, ids

    post = [row for row in flows if _effective(row) > anchor_date]
    post_ids = [row["transaction_id"] for row in post]

    if retired:
        # §5.6: an I0-retired instrument is never decremented a second time.
        if post:
            emit(effective_date=max(_effective(row) for row in post),
                 outstanding=anchor_value,
                 status="known" if anchor_value is not None else "unknown",
                 basis=anchor_ids + post_ids,
                 flags=["already_retired"])
    elif anchor_value is None:
        if post:
            emit(effective_date=max(_effective(row) for row in post), outstanding=None,
                 status="unknown", basis=anchor_ids + post_ids)
    else:
        cover = _interval_cover(post, anchor_date, date.max, quantity_of)
        floor = anchor_date + timedelta(days=1)
        problems = [(reason, row, _first_day(row, floor), False) for reason, row in cover.unknown]
        problems += [(reason, row, _first_day(row, floor), True) for reason, row in cover.contradicted]
        applied: dict[date, list[Mapping[str, Any]]] = {}
        for row in cover.counted:
            applied.setdefault(_effective(row), []).append(row)
        windows = [
            (_day(row["period_start"], "period_start"), _day(row["period_end"], "period_end"))
            for row in cover.counted if row["reporting_basis"] == "cumulative"
        ]
        running = anchor_value
        basis = list(anchor_ids)
        for day in sorted(set(applied) | {problem[2] for problem in problems}):
            reached = [problem for problem in problems if problem[2] <= day]
            if reached:
                # From the first day a window cannot be apportioned, or a flow is
                # contradicted, the balance is not known at all; it is never the
                # anchor less only the flows that happen to be usable.
                for reason, row, _first, is_contradiction in reached:
                    if not is_contradiction:
                        note_window(reason, row)
                emit(effective_date=day, outstanding=None,
                     status="contradicted" if any(problem[3] for problem in reached) else "unknown",
                     basis=basis + [problem[1]["transaction_id"] for problem in reached],
                     flags=[f"{problem[0]}:{problem[1]['transaction_id']}" for problem in reached])
                break
            halted = False
            for row in sorted(applied.get(day, ()), key=lambda item: item["transaction_id"]):
                basis.append(row["transaction_id"])
                value = quantity_of(row)
                if value is None:
                    note_amount(row)
                    emit(effective_date=day, outstanding=None, status="unknown", basis=basis)
                    halted = True
                    break
                running = running - value if row["kind"] in DECREMENT_KINDS else running + value
            if halted:
                break
            basis.extend(row["transaction_id"] for row in cover.covered if _effective(row) <= day)
            if any(start <= day < end for start, end in windows):
                # Inside a counted window only its total is known, not its path,
                # so no version is stated until the window closes.
                continue
            status = "known"
            flags = []
            if running < 0:
                # Never clamped: a negative balance is a contradiction, not a zero.
                status = "contradicted"
                flags.append(f"flows_exceed_balance:{instrument_id}")
            emit(effective_date=day, outstanding=running, status=status, basis=list(basis), flags=flags)
            if running < 0:
                break

    if entries:
        last = entries[-1]
        if last["outstanding"] is not None:
            balance = Decimal(last["outstanding"])
            if retired and balance > 0:
                last["status"] = "contradicted"
                last["flags"] = sorted(set(last["flags"]) | {f"retired_instrument_with_positive_balance:{instrument_id}"})
            elif not retired and balance == 0:
                # X0 flags the decision; it never changes the I0 status itself.
                last["flags"] = sorted(set(last["flags"]) | {f"retirement_decision_pending:{instrument_id}"})
    return _mint_versions(instrument_id, entries)


def _mint_versions(instrument_id: str, entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Content-address the version chain in date order; earlier versions are kept."""
    records: list[dict[str, Any]] = []
    previous_id: str | None = None
    for entry in entries:
        body = {"instrument_id": instrument_id, "supersedes_version_id": previous_id, **dict(entry)}
        version_id = stable_id("instver", body)
        records.append({
            "schema": INSTRUMENT_VERSION_SCHEMA,
            "version_id": version_id,
            "instrument_id": instrument_id,
            "supersedes_version_id": previous_id,
            **dict(entry),
        })
        previous_id = version_id
    return records


def _share_reconciliation(
    *,
    security_class_id: str,
    earlier: ShareObservationRef,
    later: ShareObservationRef,
    transactions: Sequence[Mapping[str, Any]],
    unknowns: _Unknowns,
) -> dict[str, Any]:
    """§6: observed change against evidenced net issuance, never plugged."""
    from_date = _day(earlier.as_of_date, "share_observation.as_of_date")
    to_date = _day(later.as_of_date, "share_observation.as_of_date")
    affects = (f"share_reconciliation:{security_class_id}",)
    observed: Decimal | None = None
    if earlier.value is None or later.value is None:
        unknowns.note(
            f"share_observation_value_unknown:{earlier.observation_id}:{later.observation_id}",
            "a share observation in this pair states no value",
            "an issued_and_outstanding share count for both observation dates",
            affects,
        )
    else:
        observed = Decimal(later.value) - Decimal(earlier.value)

    def in_class(item: Mapping[str, Any]) -> bool:
        return item["security_class_id"] is None or item["security_class_id"] == security_class_id

    # The same §4 window coverage as usage and instrument versions: a covered
    # event is already inside a counted window and never adds a second time.
    rows = [item for item in transactions if item["kind"] in SHARE_FLOW_KINDS and in_class(item)]
    cover = _interval_cover(rows, from_date, to_date, lambda row: _dec(row["shares"]))
    evidenced = Decimal(0)
    evidenced_unknown = False
    contradicted = bool(cover.contradicted)
    transaction_ids: list[str] = []
    unknown_ids: list[str] = []
    for reason, item in cover.unknown:
        evidenced_unknown = True
        transaction_ids.append(item["transaction_id"])
        if reason == "window_straddles_interval":
            unknown_ids.append(unknowns.note(
                f"window_straddles_observation:{item['transaction_id']}",
                f"a cumulative window of {item['transaction_id']} straddles an observation date and is not apportioned",
                "cumulative windows whose period_start and period_end fall between the two observation dates",
                affects,
            ))
        else:
            unknown_ids.append(unknowns.note(
                f"overlapping_cumulative_windows_not_apportionable:{item['transaction_id']}",
                f"a cumulative window of {item['transaction_id']} partially overlaps another window "
                "of the same kind and is not apportioned",
                "cumulative share figures whose windows nest or do not overlap",
                affects,
            ))
    transaction_ids.extend(item["transaction_id"] for _reason, item in cover.contradicted)
    transaction_ids.extend(item["transaction_id"] for item in cover.covered)
    for item in cover.counted:
        transaction_ids.append(item["transaction_id"])
        if item["security_class_id"] is None:
            evidenced_unknown = True
            unknown_ids.append(unknowns.note(
                f"share_class_not_stated:{item['transaction_id']}",
                f"{item['transaction_id']} states no security class, so it cannot be attributed to {security_class_id}",
                "the security class the issued or retired shares belong to",
                affects,
            ))
            continue
        amount = _dec(item["shares"])
        if amount is None:
            evidenced_unknown = True
            unknown_ids.append(unknowns.note(
                f"share_amount_unknown:{item['transaction_id']}",
                f"{item['transaction_id']} states no share count",
                "a filing stating the number of shares issued or retired by that transaction",
                affects,
            ))
            continue
        evidenced += -amount if item["kind"] in RETIRED_SHARE_KINDS else amount

    for item in transactions:
        if item["kind"] != "resale" or not in_class(item):
            continue
        # A23: a resale of already outstanding shares issues nothing; it is
        # listed in the interval it falls in and never adds.
        if item["reporting_basis"] == "cumulative":
            end = _day(item["period_end"], "period_end")
            start = _day(item["period_start"], "period_start") if item["period_start"] else None
            if end > from_date and (start is None or start <= to_date):
                transaction_ids.append(item["transaction_id"])
        elif from_date < _day(item["event_date"], "event_date") <= to_date:
            transaction_ids.append(item["transaction_id"])

    if contradicted:
        status = "contradicted"
    elif observed is None or evidenced_unknown:
        status = "unknown"
    else:
        status = "known"
    # A contradicted or incomplete flow set states no evidenced figure, so the
    # observed change is never compared against a partial sum.
    stated = not (evidenced_unknown or contradicted)
    unexplained = observed - evidenced if (observed is not None and stated) else None
    return {
        "schema": SHARE_RECONCILIATION_SCHEMA,
        "security_class_id": security_class_id,
        "from_observation_id": earlier.observation_id,
        "to_observation_id": later.observation_id,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "observed_delta": None if observed is None else _decimal_text(observed),
        "evidenced_net_issuance": _decimal_text(evidenced) if stated else None,
        "unexplained_delta": None if unexplained is None else _decimal_text(unexplained),
        "status": status,
        "transaction_ids": sorted(set(transaction_ids)),
        "unknown_ids": sorted(set(unknown_ids)),
    }


def _share_reconciliations(
    *,
    share_observations: Sequence[ShareObservationRef],
    transactions: Sequence[Mapping[str, Any]],
    cutoff: datetime,
    as_of_date: date,
    unknowns: _Unknowns,
) -> list[dict[str, Any]]:
    # A figure with no stated availability cannot be shown to be known at the
    # cutoff, so it is never visible; it is reported as an unknown instead.
    visible: list[ShareObservationRef] = []
    for item in share_observations:
        if item.basis != "issued_and_outstanding":
            continue
        if _day(item.as_of_date, "share_observation.as_of_date") > as_of_date:
            continue
        if item.source is None or item.source.available_at is None:
            unknowns.note(
                f"share_observation_availability_unstated:{item.observation_id}",
                f"share observation {item.observation_id} states no availability time, so it is not visible at the cutoff",
                "the time the share figure became available",
                (f"share_observation:{item.observation_id}",),
            )
            continue
        if _instant(item.source.available_at, "share_observation.source.available_at") <= cutoff:
            visible.append(item)
    by_class: dict[str, list[ShareObservationRef]] = {}
    for item in visible:
        by_class.setdefault(item.security_class_id, []).append(item)
    records: list[dict[str, Any]] = []
    for security_class_id in sorted(by_class):
        ordered = sorted(by_class[security_class_id], key=lambda item: (item.as_of_date, item.observation_id))
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.as_of_date == later.as_of_date:
                continue
            records.append(_share_reconciliation(
                security_class_id=security_class_id, earlier=earlier, later=later,
                transactions=transactions, unknowns=unknowns,
            ))
    return records


def _realized_cash(transaction: Mapping[str, Any], unknowns: _Unknowns) -> dict[str, Any]:
    """§7: the historical cash fact of one transaction, never a scenario effect."""
    transaction_id = str(transaction["transaction_id"])
    kind = str(transaction["kind"])
    settlement = transaction["settlement"]
    if transaction["status"] == "contradicted":
        cash_kind: str | None = None
        status = "contradicted"
    elif kind in PROCEEDS_KINDS:
        cash_kind, status = "proceeds", "known"
    elif kind in REPAYMENT_KINDS:
        cash_kind, status = "repayment", "known"
    elif kind in NO_CASH_KINDS:
        cash_kind, status = "no_cash", "known"
    elif kind == "warrant_exercise":
        if settlement in CASH_PAYING_SETTLEMENTS:
            cash_kind, status = "proceeds", "known"
        elif settlement in NO_CASH_SETTLEMENTS:
            cash_kind, status = "no_cash", "known"
        else:
            cash_kind, status = None, "unknown"
            unknowns.note(
                f"realized_cash_kind_undetermined:{transaction_id}",
                f"the settlement of warrant exercise {transaction_id} is not stated, so its cash kind is undetermined",
                "the exercise settlement (cash, cashless, net share or pre-funded)",
                (f"transaction:{transaction_id}",),
            )
    elif kind == "instrument_issuance":
        priced = transaction["gross_proceeds_usd"] is not None or transaction["net_proceeds_usd"] is not None
        cash_kind, status = ("proceeds" if priced else "no_cash"), "known"
    else:  # pragma: no cover - TRANSACTION_KINDS is closed
        cash_kind, status = "no_cash", "known"

    gross: str | None
    net: str | None
    if cash_kind == "no_cash":
        # Structurally no issuer cash: zero is a fact here, not an inference.
        gross, net = "0", "0"
    elif cash_kind is None:
        gross, net = None, None
    else:
        # Reported cash only.  A redemption or repurchase can pay a premium or a
        # discount, so its principal is never taken as the cash paid.
        gross = transaction["gross_proceeds_usd"]
        net = transaction["net_proceeds_usd"]
        if gross is None or net is None:
            status = "unknown"
    return {
        "schema": REALIZED_CASH_SCHEMA,
        "transaction_id": transaction_id,
        "kind": kind,
        "settlement": settlement,
        "realized_cash_kind": cash_kind,
        "gross_usd": gross,
        "net_usd": net,
        "status": status,
    }


# ---------------------------------------------------------------------------
# §8 The ledger
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TransactionLedger:
    """Everything X0a knows about what the issuer already did, at one ``as_of``."""

    issuer_id: str
    as_of: str
    transactions: tuple[dict[str, Any], ...]
    usage: tuple[dict[str, Any], ...]
    instrument_versions: tuple[dict[str, Any], ...]
    share_reconciliations: tuple[dict[str, Any], ...]
    realized_cash: tuple[dict[str, Any], ...]
    deferred: tuple[dict[str, Any], ...]
    unknowns: tuple[Unknown, ...]
    receipt: CalculationReceipt
    support: str

    def __post_init__(self) -> None:
        _identifier(self.issuer_id, "transaction_ledger.issuer_id")
        _timestamp(self.as_of, "transaction_ledger.as_of")
        for name in ("transactions", "usage", "instrument_versions", "share_reconciliations",
                     "realized_cash", "deferred"):
            items = tuple(getattr(self, name))
            for item in items:
                _require(isinstance(item, Mapping), f"transaction_ledger.{name}: mapping records required")
            object.__setattr__(self, name, tuple(dict(item) for item in items))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        for item in self.unknowns:
            _require(isinstance(item, Unknown), "transaction_ledger.unknowns: Unknown required")
        _require(isinstance(self.receipt, CalculationReceipt), "transaction_ledger.receipt: CalculationReceipt required")
        _member(self.support, SUPPORT_STATES, "transaction_ledger.support")
        if self.support == "partial":
            _require(len(self.support_limits()) > 0, "transaction_ledger: partial support names its limits")
        _assert_safe_keys(self.as_record(), "transaction_ledger")

    def records(self) -> tuple[dict[str, Any], ...]:
        """Every ledger record, in a fixed order, for the ``transactions`` family."""
        return (
            tuple(self.transactions) + tuple(self.usage) + tuple(self.instrument_versions)
            + tuple(self.share_reconciliations) + tuple(self.realized_cash) + tuple(self.deferred)
        )

    def support_limits(self) -> tuple[str, ...]:
        """The deferred and contradicted ids that keep this ledger ``partial``."""
        limits = {f"deferred:{item['observation_id']}" for item in self.deferred}
        limits.update(
            f"contradicted:{item['transaction_id']}"
            for item in self.transactions if item["status"] == "contradicted"
        )
        limits.update(f"contradicted:{item['usage_key']}" for item in self.usage if item["status"] == "contradicted")
        limits.update(
            f"contradicted:{item['instrument_id']}"
            for item in self.instrument_versions if item["status"] == "contradicted"
        )
        limits.update(
            f"contradicted:{item['security_class_id']}"
            for item in self.share_reconciliations if item["status"] == "contradicted"
        )
        return tuple(sorted(limits))

    def family_state(self) -> FamilyState:
        """The ``transactions`` twin family C0 already admits (§1)."""
        if self.support in ("unavailable", "not_built"):
            provenance = FamilyProvenance(
                family="transactions",
                input_family="transaction_observations",
                input_schema=None,
                support=self.support,
                as_of=self.as_of,
            )
            return FamilyState("transactions", provenance,
                               unavailable=("no transaction observation is visible at as_of",))
        provenance = FamilyProvenance(
            family="transactions",
            input_family="transaction_observations",
            input_schema=OBSERVATION_SCHEMA,
            support=self.support,
            compiler_version=IMPLEMENTATION,
            artifact_sha256=self.receipt.input_digest,
            support_limits=self.support_limits(),
            as_of=self.as_of,
        )
        return FamilyState("transactions", provenance, records=self.records())

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": LEDGER_SCHEMA,
            "implementation": IMPLEMENTATION,
            "issuer_id": self.issuer_id,
            "as_of": self.as_of,
            "support": self.support,
            "transactions": [dict(item) for item in self.transactions],
            "usage": [dict(item) for item in self.usage],
            "instrument_versions": [dict(item) for item in self.instrument_versions],
            "share_reconciliations": [dict(item) for item in self.share_reconciliations],
            "realized_cash": [dict(item) for item in self.realized_cash],
            "deferred": [dict(item) for item in self.deferred],
            "unknowns": [item.as_record() for item in self.unknowns],
            "receipt": self.receipt.as_record(),
        }


def _path_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """The four registration-path facts X0a reads; nothing else is touched."""
    path_id = record.get("path_id")
    _identifier(path_id, "registration_path.path_id")
    issuer = record.get("issuer") or {}
    registration = record.get("registration") or {}
    origin = record.get("origin") or {}
    accepted = origin.get("sec_accepted_at")
    inception = None
    if isinstance(accepted, str) and accepted:
        inception = _instant(accepted, "registration_path.origin.sec_accepted_at").date()
    file_number = registration.get("file_number")
    return {
        "path_id": str(path_id),
        "issuer_id": str(issuer.get("issuer_id")) if issuer.get("issuer_id") else None,
        "file_number": str(file_number) if file_number else None,
        "inception": inception,
    }


def receipt_inputs(
    *,
    issuer_id: str,
    as_of: str,
    observations: Sequence[TransactionObservation],
    bindings: Sequence[TransactionBinding],
    filing_coverage: Sequence[FilingCoverage],
    registration_paths: Sequence[Mapping[str, Any]],
    instruments: InstrumentSet | None,
    share_observations: Sequence[ShareObservationRef],
) -> dict[str, Any]:
    """The canonical, order-invariant plain-record inputs behind the receipt."""
    return {
        "issuer_id": issuer_id,
        "as_of": as_of,
        "observations": [item.as_record() for item in sorted(observations, key=lambda row: row.observation_id)],
        "bindings": [item.as_record() for item in sorted(bindings, key=lambda row: row.binding_id)],
        "filing_coverage": [item.as_record() for item in sorted(filing_coverage, key=lambda row: row.coverage_id)],
        "paths": sorted((_record(dict(item)) for item in registration_paths), key=sha256_of),
        "instruments": None if instruments is None else {
            "issuer_id": instruments.issuer_id,
            "as_of": instruments.as_of,
            "receipt_id": instruments.receipt.receipt_id,
            "provenance": instruments.provenance.as_record(),
            "unresolved_candidate_ids": sorted(instruments.unresolved_candidate_ids),
            "instruments": sorted((item.as_record() for item in instruments.instruments), key=sha256_of),
        },
        "share_observations": [
            item.as_record() for item in sorted(share_observations, key=lambda row: row.observation_id)
        ],
    }


def _observation_visible(item: TransactionObservation, cutoff: datetime, as_of_date: date) -> bool:
    """§0 item 8: nothing dated after ``as_of`` is visible."""
    if _instant(item.available_at, "transaction_observation.available_at") > cutoff:
        return False
    if item.decided_at is not None and _instant(item.decided_at, "transaction_observation.decided_at") > cutoff:
        return False
    if item.event_date is not None and _day(item.event_date, "transaction_observation.event_date") > as_of_date:
        return False
    if item.period_end is not None and _day(item.period_end, "transaction_observation.period_end") > as_of_date:
        return False
    return True


def _transaction_record(
    transaction_id: str,
    pairs: Sequence[tuple[TransactionObservation, TransactionBinding]],
) -> dict[str, Any]:
    """Group the observations of one economic event into one transaction (§3)."""
    observations = [pair[0] for pair in pairs]
    bindings = [pair[1] for pair in pairs]
    contradictions: list[str] = []

    for name in ("kind", "reporting_basis", "event_date", "period_start", "period_end"):
        if len({getattr(item, name) for item in observations}) > 1:
            contradictions.append(f"transaction_observations_disagree:{transaction_id}")
            break
    for name in _NUMERIC_FIELDS + ("settlement", "security_class_id"):
        # Numbers compare by value, so "1000" and "1000.00" are one amount (S5).
        stated = {
            Decimal(getattr(item, name)) if name in _NUMERIC_FIELDS else getattr(item, name)
            for item in observations if getattr(item, name) is not None
        }
        if len(stated) > 1:
            contradictions.append(f"transaction_observations_disagree:{transaction_id}")
            break
    targets = {
        (item.target_kind, item.target_id, item.usage_class, item.programme_key, item.programme_inception_date)
        for item in bindings
    }
    if len(targets) > 1:
        contradictions.append(f"transaction_bindings_disagree:{transaction_id}")

    merged: dict[str, Any] = {}
    for name in ("kind", "reporting_basis", "event_date", "period_start", "period_end", "settlement",
                 "security_class_id") + _NUMERIC_FIELDS:
        stated = [getattr(item, name) for item in observations if getattr(item, name) is not None]
        merged[name] = stated[0] if stated else None

    gross = merged["gross_proceeds_usd"]
    gross_derived = False
    shares = _dec(merged["shares"])
    price = _dec(merged["price_per_share"])
    with localcontext() as context:
        context.prec = 60
        if gross is None and shares is not None and price is not None:
            # The engine computes it exactly and says so; it is never a guess.
            gross = _decimal_text(shares * price)
            gross_derived = True
        elif gross is not None and shares is not None and price is not None:
            if shares * price != Decimal(gross):
                contradictions.append(f"gross_proceeds_disagree:{transaction_id}")
    merged["gross_proceeds_usd"] = gross

    # A None programme key sorts first instead of raising against a string (S1).
    target_kind, target_id, usage_class, programme_key, programme_inception_date = sorted(
        targets, key=lambda target: tuple((part is not None, "" if part is None else str(part)) for part in target)
    )[0]
    origin = GOLD_ORIGIN if all(item.origin == GOLD_ORIGIN for item in observations) else CANONICAL_EXTRACTION
    available_at = max(item.available_at for item in observations)
    evidence = _evidence_union(
        [item.evidence for item in observations] + [item.evidence for item in bindings]
    )
    return {
        "transaction_id": transaction_id,
        "kind": merged["kind"],
        "reporting_basis": merged["reporting_basis"],
        "event_date": merged["event_date"],
        "period_start": merged["period_start"],
        "period_end": merged["period_end"],
        "shares": merged["shares"],
        "price_per_share": merged["price_per_share"],
        "gross_proceeds_usd": merged["gross_proceeds_usd"],
        "gross_derived": gross_derived,
        "net_proceeds_usd": merged["net_proceeds_usd"],
        "principal_usd": merged["principal_usd"],
        "instruments": merged["instruments"],
        "settlement": merged["settlement"],
        "security_class_id": merged["security_class_id"],
        "target_kind": target_kind,
        "target_id": target_id,
        "usage_class": usage_class,
        "programme_key": programme_key,
        "programme_inception_date": programme_inception_date,
        "status": "contradicted" if contradictions else "observed",
        "contradictions": sorted(set(contradictions)),
        "observation_ids": sorted(item.observation_id for item in observations),
        "binding_ids": sorted(item.binding_id for item in bindings),
        "origin": origin,
        "available_at": available_at,
        "evidence": _records_of(evidence),
    }


def reconcile_transactions(
    *,
    issuer_id: str,
    as_of: str,
    observations: Sequence[TransactionObservation],
    bindings: Sequence[TransactionBinding],
    filing_coverage: Sequence[FilingCoverage] = (),
    registration_paths: Sequence[Mapping[str, Any]] = (),
    instruments: InstrumentSet | None = None,
    share_observations: Sequence[ShareObservationRef] = (),
) -> TransactionLedger:
    """Reconcile what the issuer already did into one point-in-time ledger (§8)."""
    # A float is refused as a float, never laundered into a contract violation.
    _refuse_floats(issuer_id, "reconcile_transactions.issuer_id")
    _refuse_floats(as_of, "reconcile_transactions.as_of")
    _identifier(issuer_id, "reconcile_transactions.issuer_id")
    as_of = _timestamp(as_of, "reconcile_transactions.as_of")
    cutoff = _instant(as_of, "reconcile_transactions.as_of")
    as_of_date = cutoff.date()

    observation_records = tuple(observations)
    for item in observation_records:
        _require(isinstance(item, TransactionObservation),
                 "reconcile_transactions.observations: TransactionObservation required")
        _require(item.issuer_id == issuer_id,
                 f"transaction_observation[{item.observation_id}]: issuer {item.issuer_id!r} differs from {issuer_id!r}")
    _require(len({item.observation_id for item in observation_records}) == len(observation_records),
             "reconcile_transactions.observations: duplicate observation_id")

    binding_records = tuple(bindings)
    for item in binding_records:
        _require(isinstance(item, TransactionBinding),
                 "reconcile_transactions.bindings: TransactionBinding required")
    _require(len({item.binding_id for item in binding_records}) == len(binding_records),
             "reconcile_transactions.bindings: duplicate binding_id")

    coverage_records = tuple(filing_coverage)
    for item in coverage_records:
        _require(isinstance(item, FilingCoverage),
                 "reconcile_transactions.filing_coverage: FilingCoverage required")
        _require(item.issuer_id == issuer_id,
                 f"transaction_filing_coverage[{item.coverage_id}]: issuer {item.issuer_id!r} differs from {issuer_id!r}")

    path_records = tuple(registration_paths)
    for item in path_records:
        _require(isinstance(item, Mapping), "reconcile_transactions.registration_paths: mapping records required")
    paths_by_id = {row["path_id"]: row for row in (_path_view(item) for item in path_records)}
    _require(len(paths_by_id) == len(path_records), "reconcile_transactions.registration_paths: duplicate path_id")

    if instruments is not None:
        _require(isinstance(instruments, InstrumentSet), "reconcile_transactions.instruments: InstrumentSet required")
        _require(instruments.issuer_id == issuer_id,
                 f"reconcile_transactions.instruments: issuer {instruments.issuer_id!r} differs from {issuer_id!r}")

    share_refs = tuple(share_observations)
    for item in share_refs:
        _require(isinstance(item, ShareObservationRef),
                 "reconcile_transactions.share_observations: ShareObservationRef required")

    unknowns = _Unknowns()

    by_observation_id = {item.observation_id: item for item in observation_records}
    visible_bindings = [
        item for item in binding_records
        if _instant(item.decided_at, "transaction_binding.decided_at") <= cutoff
    ]
    for item in binding_records:
        _require(item.observation_id in by_observation_id,
                 f"transaction_binding[{item.binding_id}]: names unknown observation {item.observation_id!r}")
        observation = by_observation_id[item.observation_id]
        expected = USAGE_CLASS_FOR_KIND[observation.kind]
        _require(item.usage_class == expected,
                 f"transaction_binding[{item.binding_id}]: a {observation.kind!r} observation is usage_class "
                 f"{expected!r}, got {item.usage_class!r}")
    superseded_names = {item.supersedes for item in visible_bindings if item.supersedes}
    live_bindings = [item for item in visible_bindings if item.binding_id not in superseded_names]

    paths_by_file_number: dict[str, list[str]] = {}
    for row in paths_by_id.values():
        if row["file_number"] and row["issuer_id"] in (None, issuer_id):
            paths_by_file_number.setdefault(row["file_number"], []).append(row["path_id"])

    visible_observations = {
        item.observation_id: item for item in observation_records
        if _observation_visible(item, cutoff, as_of_date)
    }
    bindings_by_observation: dict[str, list[TransactionBinding]] = {}
    for item in binding_records:
        bindings_by_observation.setdefault(item.observation_id, []).append(item)

    def canonical_match(binding: TransactionBinding, observation: TransactionObservation) -> bool:
        """§3: a canonical join needs an exact unique file number for this issuer."""
        file_number = observation.source.get("file_number")
        if not file_number:
            return False
        matches = paths_by_file_number.get(str(file_number), [])
        return len(matches) == 1 and matches[0] == binding.target_id

    chosen: dict[str, TransactionBinding] = {}
    deferred: list[dict[str, str]] = []
    deferred_detail: list[dict[str, Any]] = []
    for observation_id in sorted(visible_observations):
        observation = visible_observations[observation_id]
        named = bindings_by_observation.get(observation_id, [])
        visible_named = [item for item in named if item in visible_bindings]
        eligible: list[TransactionBinding] = []
        ambiguous = False
        for item in visible_named:
            if item.binding_id in superseded_names:
                continue
            if item.origin == CANONICAL_JOIN and not canonical_match(item, observation):
                ambiguous = True
                continue
            eligible.append(item)
        if eligible:
            chosen[observation_id] = max(
                eligible, key=lambda item: (_instant(item.decided_at, "decided_at").timestamp(), item.binding_id)
            )
            continue
        if ambiguous:
            reason = "path_join_ambiguous"
        elif not named:
            reason = "no_binding"
        elif not visible_named:
            reason = "binding_not_visible"
        else:
            reason = "binding_superseded"
        deferred.append({"observation_id": observation_id, "reason": reason})
        deferred_detail.append({
            "observation_id": observation_id,
            "reason": reason,
            "form_class": _form_class(observation.source.get("form")),
            "source_date": observation.source_date,
        })

    groups: dict[str, list[tuple[TransactionObservation, TransactionBinding]]] = {}
    for observation_id in sorted(chosen):
        binding = chosen[observation_id]
        groups.setdefault(binding.transaction_id, []).append((visible_observations[observation_id], binding))
    transactions = tuple(
        _transaction_record(transaction_id, groups[transaction_id]) for transaction_id in sorted(groups)
    )

    usage: list[dict[str, Any]] = []
    usage_groups: dict[tuple[str, str, str | None], list[dict[str, Any]]] = {}
    for item in transactions:
        if item["target_kind"] != "registration_path" or item["usage_class"] not in USAGE_KEY_CLASSES:
            continue
        key = (item["target_id"], item["usage_class"], item["programme_key"])
        usage_groups.setdefault(key, []).append(item)
    for target_id, usage_class, programme_key in sorted(usage_groups, key=lambda key: (key[0], key[1], key[2] or "")):
        grouped = usage_groups[(target_id, usage_class, programme_key)]
        prefix = USAGE_KEY_PREFIX[usage_class]
        usage_key = f"{prefix}:{target_id}" if programme_key is None else f"{prefix}:{target_id}:{programme_key}"
        inception: date | None = None
        contradiction: str | None = None
        if usage_class == "shelf_takedown":
            path = paths_by_id.get(target_id)
            inception = path["inception"] if path else None
        else:
            stated = sorted({
                item["programme_inception_date"] for item in grouped
                if item["programme_inception_date"] is not None
            })
            if len(stated) > 1:
                contradiction = f"programme_inception_dates_disagree:{usage_key}"
            elif stated:
                inception = _day(stated[0], "programme_inception_date")
        visible_coverage = [
            item for item in coverage_records
            if _instant(item.available_at, "transaction_filing_coverage.available_at") <= cutoff
        ]
        record = _usage_record(
            usage_key=usage_key, usage_class=usage_class, path_id=target_id, transactions=grouped,
            inception=inception, coverage=visible_coverage, deferred=deferred_detail,
            as_of_date=as_of_date, unknowns=unknowns,
        )
        if contradiction is not None:
            record["status"] = "contradicted"
            note = contradiction if record["usage"]["note"] is None else f"{contradiction}; {record['usage']['note']}"
            record["usage"] = Quantity(unit="usd", status="contradicted", note=note).as_record()
        usage.append(record)

    versions: list[dict[str, Any]] = []
    version_groups: dict[str, list[dict[str, Any]]] = {}
    for item in transactions:
        if item["target_kind"] != "instrument":
            continue
        version_groups.setdefault(item["target_id"], []).append(item)
    instruments_by_id = {
        row.instrument_id: row for row in (instruments.instruments if instruments is not None else ())
    }
    for target_id in sorted(version_groups):
        versions.extend(_instrument_versions(
            instrument_id=target_id,
            transactions=version_groups[target_id],
            instrument=instruments_by_id.get(target_id),
            as_of_date=as_of_date,
            unknowns=unknowns,
        ))

    reconciliations = _share_reconciliations(
        share_observations=share_refs, transactions=transactions,
        cutoff=cutoff, as_of_date=as_of_date, unknowns=unknowns,
    )
    realized = [_realized_cash(item, unknowns) for item in transactions]

    contradicted = any(
        item["status"] == "contradicted"
        for item in list(transactions) + usage + versions + reconciliations
    )
    if not visible_observations:
        support = "unavailable"
    elif deferred or contradicted:
        support = "partial"
    else:
        support = "supported"

    receipt = CalculationReceipt.build(
        inputs=receipt_inputs(
            issuer_id=issuer_id, as_of=as_of, observations=observation_records, bindings=binding_records,
            filing_coverage=coverage_records, registration_paths=path_records, instruments=instruments,
            share_observations=share_refs,
        ),
        rule_digest=RULE_DIGEST,
        implementation=IMPLEMENTATION,
        computed_at=as_of,
    )
    return TransactionLedger(
        issuer_id=issuer_id,
        as_of=as_of,
        transactions=transactions,
        usage=tuple(sorted(usage, key=lambda item: item["usage_key"])),
        instrument_versions=tuple(versions),
        share_reconciliations=tuple(reconciliations),
        realized_cash=tuple(realized),
        deferred=tuple(sorted(deferred, key=lambda item: (item["observation_id"], item["reason"]))),
        unknowns=unknowns.sorted(),
        receipt=receipt,
        support=support,
    )


def _evidence_refs(records: Sequence[Mapping[str, Any]]) -> tuple[EvidenceRef, ...]:
    return tuple(
        EvidenceRef(str(item["manifest_id"]), str(item["span_id"]), str(item["text_sha256"])) for item in records
    )


def apply_outstanding(instruments: InstrumentSet, ledger: TransactionLedger) -> InstrumentSet:
    """Replace each bound instrument's stale I1 balance with the X0-derived one.

    Returns a NEW :class:`InstrumentSet`; the input is never mutated.  Unbound
    instruments pass through byte-identical, so review focus (2) closes: I1 reads
    the post-X0 claim and an already-exercised warrant is never counted again as
    future issuance.
    """
    _require(isinstance(instruments, InstrumentSet), "apply_outstanding.instruments: an InstrumentSet is required")
    _require(isinstance(ledger, TransactionLedger), "apply_outstanding.ledger: a TransactionLedger is required")
    _require(instruments.issuer_id == ledger.issuer_id,
             f"apply_outstanding: instrument set issuer {instruments.issuer_id!r} differs from ledger {ledger.issuer_id!r}")
    # A ledger reconciled after the instrument set would feed it flows it could
    # not have known (N2).
    _require(_instant(ledger.as_of, "apply_outstanding.ledger.as_of")
             <= _instant(instruments.as_of, "apply_outstanding.instruments.as_of"),
             f"apply_outstanding: ledger as_of {ledger.as_of!r} is after instrument set as_of {instruments.as_of!r}")

    latest: dict[str, dict[str, Any]] = {}
    for version in ledger.instrument_versions:
        instrument_id = str(version["instrument_id"])
        current = latest.get(instrument_id)
        key = (str(version["effective_date"]), str(version["version_id"]))
        if current is None or key >= (str(current["effective_date"]), str(current["version_id"])):
            latest[instrument_id] = dict(version)
    if not latest:
        return instruments

    transactions_by_id = {str(item["transaction_id"]): item for item in ledger.transactions}
    rebuilt: list[Instrument] = []
    applied: list[dict[str, str]] = []
    for instrument in instruments.instruments:
        version = latest.get(instrument.instrument_id)
        if version is None:
            rebuilt.append(instrument)  # byte-identical: the same frozen object
            continue
        unit = str(version["unit"])
        term_name = "principal_outstanding" if unit == "principal_usd" else "instruments_outstanding"
        unit_kind, share_basis = ECONOMIC_TERM_UNITS[term_name]
        status = str(version["status"])
        if status == "known":
            value: Quantity | None = Quantity.known(str(version["outstanding"]), unit_kind, share_basis=share_basis)
        elif status == "contradicted":
            value = Quantity(unit=unit_kind, status="contradicted", share_basis=share_basis)
        else:
            value = Quantity.unknown(unit_kind, share_basis=share_basis)

        basis_ids = [str(item) for item in version["basis_transaction_ids"]]
        basis_transactions = [transactions_by_id[item] for item in basis_ids if item in transactions_by_id]
        evidence = _evidence_refs([row for item in basis_transactions for row in item["evidence"]])
        fact_origin = GOLD_ORIGIN if all(
            item["origin"] == GOLD_ORIGIN for item in basis_transactions
        ) and basis_transactions else CANONICAL_EXTRACTION
        available_at = max(
            (str(item["available_at"]) for item in basis_transactions), default=ledger.as_of
        )
        term_id = stable_id("x0term", {
            "instrument_id": instrument.instrument_id,
            "name": term_name,
            "version_id": version["version_id"],
            "outstanding": version["outstanding"],
            "status": status,
        })
        term = EconomicTerm(
            term_id=term_id,
            instrument_id=instrument.instrument_id,
            name=term_name,
            status="admitted" if status == "known" else status,
            value=value,
            flag=None,
            expression=None,
            date_value=None,
            evidence=evidence,
            fact_origin=fact_origin,
            interpretation_version=IMPLEMENTATION,
            available_at=available_at,
            effective_at=_daystamp(_day(str(version["effective_date"]), "instrument_version.effective_date")),
        )
        kept = tuple(item for item in instrument.economic_terms if item.name != term_name)
        terms = tuple(sorted(kept + (term,), key=lambda item: (item.name, item.term_id)))

        outstanding: Quantity | None
        if status == "known" and version["outstanding"] is not None:
            amount = Decimal(str(version["outstanding"]))
            if unit == "principal_usd":
                outstanding = Quantity.known(_decimal_text(amount), "usd")
            else:
                ratio = next((item for item in terms if item.name == "shares_per_instrument"
                              and item.status == "admitted" and item.value is not None
                              and item.value.status == "known"), None)
                if ratio is None or ratio.value is None or ratio.value.value is None:
                    outstanding = Quantity.unknown("shares", share_basis="assumed_as_converted",
                                                   security_class_id=instrument.security_class_id)
                else:
                    with localcontext() as context:
                        context.prec = 60
                        shares = amount * Decimal(ratio.value.value)
                    outstanding = Quantity.known(
                        _decimal_text(shares), "shares", share_basis="assumed_as_converted",
                        security_class_id=instrument.security_class_id,
                    )
        elif status == "contradicted":
            outstanding = Quantity(unit="usd" if unit == "principal_usd" else "shares",
                                   status="contradicted",
                                   share_basis=None if unit == "principal_usd" else "assumed_as_converted",
                                   security_class_id=None if unit == "principal_usd" else instrument.security_class_id)
        else:
            outstanding = Quantity.unknown(
                "usd" if unit == "principal_usd" else "shares",
                share_basis=None if unit == "principal_usd" else "assumed_as_converted",
                security_class_id=None if unit == "principal_usd" else instrument.security_class_id,
            )

        rebuilt.append(dataclasses.replace(
            instrument,
            economic_terms=terms,
            outstanding=outstanding,
            provenance=Provenance(
                input_family="transaction_observations",
                generation_id=None,
                evidence=evidence,
                available_at=available_at,
            ),
        ))
        applied.append({"instrument_id": instrument.instrument_id, "version_id": str(version["version_id"])})

    if not applied:
        return instruments
    receipt = CalculationReceipt.build(
        inputs={
            "instrument_set_receipt_id": instruments.receipt.receipt_id,
            "ledger_receipt_id": ledger.receipt.receipt_id,
            "as_of": instruments.as_of,
            "applied": sorted(applied, key=lambda item: (item["instrument_id"], item["version_id"])),
        },
        rule_digest=RULE_DIGEST,
        implementation=IMPLEMENTATION,
        computed_at=instruments.as_of,
    )
    return dataclasses.replace(instruments, instruments=tuple(rebuilt), receipt=receipt)


__all__ = [
    "BINDING_SCHEMA",
    "CANONICAL_EXTRACTION",
    "CANONICAL_JOIN",
    "CONTRIBUTOR_ROLES",
    "DECREMENT_KINDS",
    "DEFERRAL_REASONS",
    "FILING_COVERAGE_SCHEMA",
    "FLOW_KINDS",
    "FORM_CLASSES",
    "GOLD_ORIGIN",
    "IMPLEMENTATION",
    "INCREMENT_KINDS",
    "INSTRUMENT_VERSION_SCHEMA",
    "ISSUED_SHARE_KINDS",
    "LEDGER_SCHEMA",
    "NO_CASH_KINDS",
    "OBSERVATION_SCHEMA",
    "PRINCIPAL_INSTRUMENT_KINDS",
    "PROCEEDS_KINDS",
    "REALIZED_CASH_SCHEMA",
    "REPAYMENT_KINDS",
    "RETIRED_SHARE_KINDS",
    "RULES",
    "RULE_DIGEST",
    "SHARE_FLOW_KINDS",
    "SHARE_RECONCILIATION_SCHEMA",
    "STOCK_KIND",
    "TARGET_KIND_FOR_USAGE_CLASS",
    "USAGE_CLASS_FOR_KIND",
    "USAGE_KEY_CLASSES",
    "USAGE_KEY_PREFIX",
    "USAGE_SCHEMA",
    "VERDICTS",
    "FilingCoverage",
    "TransactionBinding",
    "TransactionLedger",
    "TransactionObservation",
    "apply_outstanding",
    "receipt_inputs",
    "reconcile_transactions",
]
