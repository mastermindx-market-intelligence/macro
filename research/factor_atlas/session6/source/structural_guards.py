"""Factor Atlas S6 independent synthetic-only structural evaluation guards.

This module cannot authenticate source rights, source receipts, or numerical truth.
Even valid caller-supplied claims are always STRUCTURAL_ONLY_NOT_ADMITTED. It
never writes a dataset, reports empirical p values, or releases a prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Iterable


NOT_ADMITTED = "STRUCTURAL_ONLY_NOT_ADMITTED"
BLOCKED = "BLOCKED_NOT_ADMITTED"


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


def _valid_amount(value: Decimal | None) -> bool:
    return isinstance(value, Decimal) and value.is_finite()


def assess_minute(row: MinuteClaim) -> Assessment:
    issues: list[str] = []
    if not row.factor_id or not row.security_id:
        issues.append("MISSING_IDENTITY")
    if row.minute_start_ns >= row.minute_end_ns or row.minute_end_ns - row.minute_start_ns != 60_000_000_000:
        issues.append("INVALID_MINUTE_SPAN")
    if any(t is None for t in (row.source_known_ns, row.reader_complete_ns, row.membership_known_ns)):
        issues.append("MISSING_KNOWLEDGE_CLOCK")
    else:
        if row.source_known_ns < row.minute_end_ns:
            issues.append("SOURCE_BEFORE_BAR_END")
        if row.reader_complete_ns < row.source_known_ns:
            issues.append("READER_BEFORE_SOURCE")
        if row.reader_complete_ns > row.cutoff_ns:
            issues.append("FEATURE_AFTER_CUTOFF")
        if row.membership_known_ns > row.cutoff_ns:
            issues.append("FUTURE_MEMBERSHIP")
    if row.last_correction_known_ns is not None and row.last_correction_known_ns > row.cutoff_ns:
        issues.append("CORRECTION_AFTER_CUTOFF")
    if not row.revision_id:
        issues.append("MISSING_REVISION")
    if not row.monetary_basis_id or not row.corporate_action_vintage:
        issues.append("UNPROVEN_MONETARY_BASIS")
    if row.rights_claim != "PERMITTED_BY_OWNER":
        issues.append("RIGHTS_NOT_CLAIMED")
    if row.finality_claim != "FINAL_AS_KNOWN":
        issues.append("NOT_FINAL_AS_KNOWN")
    if row.gross_notional is None:
        issues.append("MISSING_GROSS_NOTIONAL")
    elif not _valid_amount(row.gross_notional) or row.gross_notional < 0:
        issues.append("INVALID_GROSS_NOTIONAL")
    if row.signed_pressure is None:
        issues.append("MISSING_SIGNED_PRESSURE")
    elif not _valid_amount(row.signed_pressure):
        issues.append("INVALID_SIGNED_PRESSURE")
    if _valid_amount(row.gross_notional) and _valid_amount(row.signed_pressure):
        if abs(row.signed_pressure) > row.gross_notional:
            issues.append("SIGN_EXCEEDS_GROSS")
    if not _valid_amount(row.weight) or row.weight < 0 or row.weight > 1:
        issues.append("INVALID_MEMBERSHIP_WEIGHT")
    if row.label_start_ns is not None:
        if row.label_start_ns <= row.cutoff_ns:
            issues.append("OUTCOME_NOT_FUTURE")
        if row.label_end_ns is None or row.label_end_ns < row.label_start_ns:
            issues.append("INVALID_LABEL_WINDOW")
    elif row.label_end_ns is not None:
        issues.append("INVALID_LABEL_WINDOW")
    # Even complete metadata may be fabricated: this method grants no rights or authority.
    return Assessment(BLOCKED if issues else NOT_ADMITTED, tuple(sorted(set(issues))))


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
    material = tuple(rows)
    reasons: set[str] = set()
    seen_factor: set[tuple[str, str, int, int]] = set()
    seen_market: dict[tuple[str, int, int], tuple[str, str, Decimal]] = {}
    allocated: dict[str, Decimal] = {}
    naive_raw = Decimal(0)
    for row in material:
        result = assess_minute(row)
        reasons.update(result.reasons)
        fkey = (row.factor_id, row.security_id, row.minute_start_ns, row.minute_end_ns)
        if fkey in seen_factor:
            reasons.add("DUPLICATE_FACTOR_SECURITY_MINUTE")
        seen_factor.add(fkey)
        if not _valid_amount(row.gross_notional) or not _valid_amount(row.weight):
            continue
        naive_raw += row.gross_notional
        allocated[row.factor_id] = allocated.get(row.factor_id, Decimal(0)) + row.weight * row.gross_notional
        mkey = (row.security_id, row.minute_start_ns, row.minute_end_ns)
        identity = (row.revision_id or "", row.monetary_basis_id or "", row.gross_notional)
        prior = seen_market.get(mkey)
        if prior is not None and prior != identity:
            reasons.add("CONFLICTING_SHARED_MEMBER_SOURCE")
        seen_market[mkey] = identity
    if reasons:
        return Aggregation(BLOCKED, tuple(sorted(reasons)), (), None, None)
    unique = sum((x[2] for x in seen_market.values()), Decimal(0))
    return Aggregation(NOT_ADMITTED, (), tuple(sorted(allocated.items())), unique, naive_raw - unique)


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


def check_prior_baseline(
    current_row_id: str,
    cutoff_ns: int,
    rows: Iterable[BaselineObservation],
    *,
    min_history: int = 20,
) -> BaselineCheck:
    data = tuple(rows)
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
    med = median(x.value for x in data)
    mad = median(abs(x.value - med) for x in data)
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
    reasons: set[str] = set()
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
    data = tuple(rows)
    keys = [x.independent_episode_id for x in data]
    if not data or len(set(keys)) != len(data) or any(not k for k in keys):
        return LossDiagnostic(BLOCKED, None, len(set(keys)))
    for row in data:
        if row.label not in (0, 1):
            return LossDiagnostic(BLOCKED, None, len(data))
        if any(not _valid_amount(x) or x < 0 or x > 1 for x in (row.baseline_probability, row.challenger_probability)):
            return LossDiagnostic(BLOCKED, None, len(data))
    diffs = [
        (row.baseline_probability - row.label) ** 2 - (row.challenger_probability - row.label) ** 2
        for row in data
    ]
    return LossDiagnostic(NOT_ADMITTED, sum(diffs, Decimal(0)) / Decimal(len(data)), len(data))
