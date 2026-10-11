"""Synthetic-only S6 guards. No source authentication or financial authority.

Clocks here are nonnegative signed-64-bit UTC nanosecond claims, not an owner
clock attestation. Roster completeness, calendars, per-quote receipt provenance,
real data admission and dependence-aware inference are deliberately not supplied.
Numeric resource bounds are for this research instrument, not production policy.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import islice
from statistics import median
from typing import Iterable

NOT_ADMITTED = "STRUCTURAL_ONLY_NOT_ADMITTED"
BLOCKED = "BLOCKED_NOT_ADMITTED"
MAX_RECORDS = 100_000
ARITHMETIC_PRECISION = 1024


def _clock(value: object) -> bool:
    return type(value) is int and 0 <= value <= (1 << 63) - 1


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _valid_amount(value: object) -> bool:
    if not isinstance(value, Decimal) or not value.is_finite():
        return False
    parts = value.as_tuple()
    return len(parts.digits) <= 128 and abs(parts.exponent) <= 128


def _records(rows: Iterable) -> tuple | None:
    try:
        result = tuple(islice(iter(rows), MAX_RECORDS + 1))
    except (TypeError, ValueError):
        return None
    return result if len(result) <= MAX_RECORDS else None


@dataclass(frozen=True)
class MinuteClaim:
    factor_id: str
    security_id: str
    minute_start_ns: int
    minute_end_ns: int
    cutoff_ns: int
    source_known_ns: int | None
    reader_complete_ns: int | None
    membership_known_ns: int | None
    revision_id: str | None
    monetary_basis_id: str | None
    corporate_action_vintage: str | None
    rights_claim: str
    finality_claim: str
    gross_notional: Decimal | None
    signed_pressure: Decimal | None
    weight: Decimal | None
    label_start_ns: int | None = None
    label_end_ns: int | None = None
    last_correction_known_ns: int | None = None


@dataclass(frozen=True)
class Assessment:
    status: str
    reasons: tuple[str, ...]
    source_authenticated: bool = False
    rights_approved: bool = False
    prediction_authorized: bool = False
    publication_authorized: bool = False


def assess_minute(row: MinuteClaim) -> Assessment:
    if not isinstance(row, MinuteClaim):
        return Assessment(BLOCKED, ("INVALID_MINUTE_CLAIM_TYPE",))
    issues = set()
    if not _identifier(row.factor_id) or not _identifier(row.security_id):
        issues.add("MISSING_IDENTITY")
    mandatory = ("minute_start_ns", "minute_end_ns", "cutoff_ns")
    optional = ("source_known_ns", "reader_complete_ns", "membership_known_ns",
                "label_start_ns", "label_end_ns", "last_correction_known_ns")
    for field in mandatory + optional:
        value = getattr(row, field)
        if (field in mandatory or value is not None) and not _clock(value):
            issues.add("INVALID_CLOCK:" + field)
    if issues:
        return Assessment(BLOCKED, tuple(sorted(issues)))
    if row.minute_start_ns >= row.minute_end_ns or row.minute_end_ns - row.minute_start_ns != 60_000_000_000:
        issues.add("INVALID_MINUTE_SPAN")
    if any(t is None for t in (row.source_known_ns, row.reader_complete_ns, row.membership_known_ns)):
        issues.add("MISSING_KNOWLEDGE_CLOCK")
    else:
        if row.source_known_ns < row.minute_end_ns:
            issues.add("SOURCE_BEFORE_BAR_END")
        if row.reader_complete_ns < row.source_known_ns:
            issues.add("READER_BEFORE_SOURCE")
        if row.reader_complete_ns > row.cutoff_ns:
            issues.add("FEATURE_AFTER_CUTOFF")
        if row.membership_known_ns > row.cutoff_ns:
            issues.add("FUTURE_MEMBERSHIP")
    if row.last_correction_known_ns is not None and row.last_correction_known_ns > row.cutoff_ns:
        issues.add("CORRECTION_AFTER_CUTOFF")
    if not _identifier(row.revision_id):
        issues.add("MISSING_REVISION")
    if not _identifier(row.monetary_basis_id) or not _identifier(row.corporate_action_vintage):
        issues.add("UNPROVEN_MONETARY_BASIS")
    if row.rights_claim != "PERMITTED_BY_OWNER":
        issues.add("RIGHTS_NOT_CLAIMED")
    if row.finality_claim != "FINAL_AS_KNOWN":
        issues.add("NOT_FINAL_AS_KNOWN")
    if row.gross_notional is None:
        issues.add("MISSING_GROSS_NOTIONAL")
    elif not _valid_amount(row.gross_notional) or row.gross_notional < 0:
        issues.add("INVALID_GROSS_NOTIONAL")
    if row.signed_pressure is None:
        issues.add("MISSING_SIGNED_PRESSURE")
    elif not _valid_amount(row.signed_pressure):
        issues.add("INVALID_SIGNED_PRESSURE")
    if _valid_amount(row.gross_notional) and _valid_amount(row.signed_pressure):
        if row.signed_pressure.copy_abs() > row.gross_notional:
            issues.add("SIGN_EXCEEDS_GROSS")
    if not _valid_amount(row.weight) or row.weight < 0 or row.weight > 1:
        issues.add("INVALID_MEMBERSHIP_WEIGHT")
    if row.label_start_ns is not None:
        if row.label_start_ns <= row.cutoff_ns:
            issues.add("OUTCOME_NOT_FUTURE")
        if row.label_end_ns is None or row.label_end_ns < row.label_start_ns:
            issues.add("INVALID_LABEL_WINDOW")
    elif row.label_end_ns is not None:
        issues.add("INVALID_LABEL_WINDOW")
    return Assessment(BLOCKED if issues else NOT_ADMITTED, tuple(sorted(issues)))


@dataclass(frozen=True)
class Aggregation:
    status: str
    reasons: tuple[str, ...]
    per_factor_allocated: tuple[tuple[str, Decimal], ...]
    unique_raw_gross: Decimal | None
    duplicated_raw_gross: Decimal | None
    source_authenticated: bool = False
    prediction_authorized: bool = False


def aggregate_synthetic(rows: Iterable[MinuteClaim]) -> Aggregation:
    material = _records(rows)
    if material is None or not material:
        return Aggregation(BLOCKED, ("EMPTY_OR_INVALID_POPULATION",), (), None, None)
    reasons = {r for row in material for r in assess_minute(row).reasons}
    if reasons:
        return Aggregation(BLOCKED, tuple(sorted(reasons)), (), None, None)
    if len({row.cutoff_ns for row in material}) != 1:
        reasons.add("MIXED_CUTOFFS")
    seen_factor = set()
    seen_market = {}
    for row in material:
        fkey = (row.factor_id, row.security_id, row.minute_start_ns, row.minute_end_ns)
        if fkey in seen_factor:
            reasons.add("DUPLICATE_FACTOR_SECURITY_MINUTE")
        seen_factor.add(fkey)
        mkey = (row.security_id, row.minute_start_ns, row.minute_end_ns)
        identity = (row.revision_id, row.monetary_basis_id, row.corporate_action_vintage,
                    row.gross_notional, row.signed_pressure)
        prior = seen_market.get(mkey)
        if prior is not None and prior != identity:
            reasons.add("CONFLICTING_SHARED_MEMBER_SOURCE")
        seen_market[mkey] = identity
    if reasons:
        return Aggregation(BLOCKED, tuple(sorted(reasons)), (), None, None)
    # Input bounds plus MAX_RECORDS make 1024 digits sufficient for exact sums/products.
    with localcontext() as ctx:
        ctx.prec = ARITHMETIC_PRECISION
        allocated = {}
        for row in material:
            allocated[row.factor_id] = allocated.get(row.factor_id, Decimal(0)) + row.weight * row.gross_notional
        naive = sum((row.gross_notional for row in material), Decimal(0))
        unique = sum((x[3] for x in seen_market.values()), Decimal(0))
        return Aggregation(NOT_ADMITTED, (), tuple(sorted(allocated.items())), unique, naive - unique)


@dataclass(frozen=True)
class BaselineObservation:
    source_row_id: str
    known_ns: int
    value: Decimal


@dataclass(frozen=True)
class BaselineCheck:
    status: str
    reasons: tuple[str, ...]
    median: Decimal | None = None
    mad: Decimal | None = None
    source_authenticated: bool = False


def check_prior_baseline(current_row_id: str, cutoff_ns: int,
                         rows: Iterable[BaselineObservation], *, min_history: int = 20) -> BaselineCheck:
    data = _records(rows)
    if data is None or not _identifier(current_row_id) or not _clock(cutoff_ns):
        return BaselineCheck(BLOCKED, ("INVALID_BASELINE_INPUT",))
    if type(min_history) is not int or not 2 <= min_history <= MAX_RECORDS:
        return BaselineCheck(BLOCKED, ("INVALID_HISTORY_FLOOR",))
    if any(not isinstance(x, BaselineObservation) or not _identifier(x.source_row_id) or not _clock(x.known_ns) for x in data):
        return BaselineCheck(BLOCKED, ("INVALID_BASELINE_IDENTITY_OR_CLOCK",))
    reasons = set()
    if any(x.source_row_id == current_row_id for x in data):
        reasons.add("SAME_MINUTE_SELF_CONTAMINATION")
    if len({x.source_row_id for x in data}) != len(data):
        reasons.add("DUPLICATE_BASELINE_MEMBER")
    if any(x.known_ns >= cutoff_ns for x in data):
        reasons.add("BASELINE_FUTURE_KNOWLEDGE")
    if any(not _valid_amount(x.value) for x in data):
        reasons.add("INVALID_BASELINE_VALUE")
    if len(data) < min_history:
        reasons.add("INSUFFICIENT_HISTORY")
    if reasons:
        return BaselineCheck(BLOCKED, tuple(sorted(reasons)))
    with localcontext() as ctx:
        ctx.prec = ARITHMETIC_PRECISION
        med = median(x.value for x in data)
        mad = median((x.value - med).copy_abs() for x in data)
    if mad == 0:
        return BaselineCheck(BLOCKED, ("ZERO_MAD_UNDEFINED_Z",), med, mad)
    return BaselineCheck(NOT_ADMITTED, (), med, mad)


@dataclass(frozen=True)
class PrintQuoteClaim:
    print_time_ns: int
    quote_time_ns: int | None
    source_receipt_ns: int | None
    cutoff_ns: int
    quote_age_limit_ns: int
    print_condition: str
    correction_state: str
    signed_notional: Decimal | None


def assess_quote_reference(row: PrintQuoteClaim) -> Assessment:
    if not isinstance(row, PrintQuoteClaim):
        return Assessment(BLOCKED, ("INVALID_QUOTE_CLAIM_TYPE",))
    reasons = set()
    for field in ("print_time_ns", "cutoff_ns", "quote_age_limit_ns", "quote_time_ns", "source_receipt_ns"):
        value = getattr(row, field)
        optional = field in ("quote_time_ns", "source_receipt_ns")
        if (not optional or value is not None) and not _clock(value):
            reasons.add("INVALID_CLOCK:" + field)
    if reasons:
        return Assessment(BLOCKED, tuple(sorted(reasons)))
    if row.print_time_ns > row.cutoff_ns:
        reasons.add("PRINT_AFTER_CUTOFF")
    if row.source_receipt_ns is not None and row.source_receipt_ns < row.print_time_ns:
        reasons.add("RECEIPT_BEFORE_PRINT")
    if row.quote_time_ns is None or row.source_receipt_ns is None:
        reasons.add("UNKNOWN_QUOTE_OR_RECEIPT")
    else:
        if row.quote_time_ns >= row.print_time_ns:
            reasons.add("QUOTE_NOT_STRICTLY_PRIOR")
        if row.print_time_ns - row.quote_time_ns > row.quote_age_limit_ns:
            reasons.add("STALE_QUOTE")
        if row.source_receipt_ns > row.cutoff_ns:
            reasons.add("SOURCE_RECEIPT_AFTER_CUTOFF")
    if row.print_condition != "ELIGIBLE_REGULAR":
        reasons.add("INELIGIBLE_TRADE_CONDITION")
    if row.correction_state != "FINAL_UNCORRECTED":
        reasons.add("UNKNOWN_OR_CORRECTED_PRINT")
    if not _valid_amount(row.signed_notional):
        reasons.add("UNKNOWN_SIGNED_NOTIONAL")
    if row.quote_age_limit_ns <= 0:
        reasons.add("INVALID_QUOTE_AGE_LIMIT")
    return Assessment(BLOCKED if reasons else NOT_ADMITTED, tuple(sorted(reasons)))


@dataclass(frozen=True)
class LossRow:
    independent_episode_id: str
    label: int
    baseline_probability: Decimal
    challenger_probability: Decimal


@dataclass(frozen=True)
class LossDiagnostic:
    status: str
    average_paired_brier_gain: Decimal | None
    n_episodes: int
    inference_status: str = "NO_P_VALUE_NO_CI_NOT_A_VALIDATION"
    prediction_authorized: bool = False


def brier_diagnostic_only(rows: Iterable[LossRow]) -> LossDiagnostic:
    data = _records(rows)
    if not data or any(not isinstance(x, LossRow) or not _identifier(x.independent_episode_id) for x in data):
        return LossDiagnostic(BLOCKED, None, 0)
    keys = [x.independent_episode_id for x in data]
    if len(set(keys)) != len(data):
        return LossDiagnostic(BLOCKED, None, len(set(keys)))
    for row in data:
        if type(row.label) is not int or row.label not in (0, 1):
            return LossDiagnostic(BLOCKED, None, len(data))
        if any(not _valid_amount(x) or x < 0 or x > 1 for x in (row.baseline_probability, row.challenger_probability)):
            return LossDiagnostic(BLOCKED, None, len(data))
    with localcontext() as ctx:
        ctx.prec = ARITHMETIC_PRECISION
        total = sum(((r.baseline_probability-r.label)**2 - (r.challenger_probability-r.label)**2 for r in data), Decimal(0))
        ctx.prec = 50  # Display rounding only; no inference or threshold is computed here.
        gain = total / Decimal(len(data))
    # n_episodes is a count of supplied unique IDs, not proof of independence.
    return LossDiagnostic(NOT_ADMITTED, gain, len(data))
