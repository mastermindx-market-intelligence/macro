"""Deterministic, offline PB-D v1.0 evaluation; no enrollment or signal authority.

Frozen design: research/policy_behavior/pro_returns/PB-D/
PB_D_PROSPECTIVE_PREREG.md at df2091915159dab94f316718caa9b2662098eae4.

All return inputs and effect outputs use PERCENTAGE POINTS: 3.0 means +3%,
and the practical floor is 2.0. A supplied numeric outcome declares a mature,
price-valid, timestamp-aligned outcome from the existing price/receipt owner;
None means unknown, pending, unfilled, or missing, never zero. Rate effects are
also percentage points; the separately named arm positive rates are fractions.

The caller supplies immutable original pairs. This module never selects an
episode, adjudicates a label, matches on an outcome, fetches prices, or rematches
an incomplete pair. Rematched omission inputs must come from the complete
eligible pre-outcome pools and name their receipt. Receipt references are
reported as caller attestations, not authenticated by this pure calculation.

NumPy is already pinned by the frozen PB-D requirements. Its version and the
exact fixed resampling procedure are recorded in every evaluation report.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import date, datetime
from functools import lru_cache
import math
import platform
from typing import Any, Sequence

import numpy as np


CALENDAR_SESSIONS = 252
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 2_601_007
MIN_VALID_DRAWS = 9_900
BLOCK_LENGTHS = (21, 10, 42)
PRACTICAL_FLOOR_PP = 2.0
FIXED_ROUND_TRIP_COSTS_BPS = (10, 25, 50)
PRIMARY_ENDPOINT = "h5_spy_mean_increment_pp"
SECONDARY_ENDPOINTS = (
    "h5_spy_positive_rate_difference_pp",
    "h10_spy_mean_increment_pp",
    "h21_spy_mean_increment_pp",
    "h5_clean_liftoff_rate_difference_pp",
)


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number, not bool/NaN/infinity")
    return float(value)


def _nonnegative_count(value: int | None, name: str) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"{name} must be a nonnegative integer or None")


def _truth(value: bool | None, name: str) -> None:
    if value is not None and type(value) is not bool:
        raise ValueError(f"{name} must be True, False, or None")


@dataclass(frozen=True)
class Outcome:
    """One immutable issuer outcome. Missing reasons are optional audit text.

    A return with a missing reason is contradictory and rejected. UNFILLED
    cannot carry returns or an observed clean-liftoff label. No missing status
    is inferred to be a failure. Optional root IDs describe lineage only;
    this module does not certify their semantic independence.
    """

    issuer_id: str
    ticker_at_cut: str
    h5_spy_excess_pp: float | None = None
    h10_spy_excess_pp: float | None = None
    h21_spy_excess_pp: float | None = None
    h5_clean_liftoff: bool | None = None
    h1_spy_excess_pp: float | None = None
    h1_absolute_return_pp: float | None = None
    h5_absolute_return_pp: float | None = None
    h10_absolute_return_pp: float | None = None
    h21_absolute_return_pp: float | None = None
    h1_sector_excess_pp: float | None = None
    h5_sector_excess_pp: float | None = None
    h10_sector_excess_pp: float | None = None
    h21_sector_excess_pp: float | None = None
    entry_status: str = "UNKNOWN"
    h1_missing_reason: str | None = None
    h5_missing_reason: str | None = None
    h10_missing_reason: str | None = None
    h21_missing_reason: str | None = None
    root_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.issuer_id, str) or not self.issuer_id or not isinstance(self.ticker_at_cut, str) or not self.ticker_at_cut:
            raise ValueError("issuer_id and ticker_at_cut are required")
        if self.entry_status not in {"FILLED", "UNFILLED", "UNKNOWN"}:
            raise ValueError("entry_status must be FILLED, UNFILLED, or UNKNOWN")
        _truth(self.h5_clean_liftoff, "h5_clean_liftoff")
        for item in fields(self):
            if item.name.endswith("_pp"):
                value = getattr(self, item.name)
                if value is not None:
                    _finite_number(value, item.name)
                    horizon = item.name.split("_", 1)[0]
                    if item.name.endswith("spy_excess_pp") and getattr(self, f"{horizon}_missing_reason") is not None:
                        raise ValueError(f"{horizon} cannot have a return and a missing reason")
                    if self.entry_status == "UNFILLED":
                        raise ValueError("an unfilled entry cannot have observed returns")
        if self.entry_status == "UNFILLED" and self.h5_clean_liftoff is not None:
            raise ValueError("an unfilled entry cannot have an observed path label")
        if self.root_ids is not None:
            object.__setattr__(self, "root_ids", tuple(self.root_ids))
            if any(not isinstance(root, str) or not root for root in self.root_ids):
                raise ValueError("root_ids must contain nonempty strings")
            if len(set(self.root_ids)) != len(self.root_ids):
                raise ValueError("duplicate root ID in issuer outcome")


@dataclass(frozen=True)
class FrozenPair:
    """A Q1/Q0 pair frozen before outcomes; session_index is zero based."""

    pair_id: str
    session_index: int
    q1: Outcome
    q0: Outcome
    sector: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pair_id, str) or not self.pair_id:
            raise ValueError("pair_id is required")
        if type(self.session_index) is not int or not 0 <= self.session_index < CALENDAR_SESSIONS:
            raise ValueError("session_index must be an integer in 0..251")
        if not isinstance(self.q1, Outcome) or not isinstance(self.q0, Outcome):
            raise ValueError("pair legs must be immutable Outcome instances")
        if self.q1.issuer_id == self.q0.issuer_id:
            raise ValueError("a pair must contain two distinct issuers")
        if self.sector is not None and (not isinstance(self.sector, str) or not self.sector):
            raise ValueError("sector must be a nonempty frozen identifier or None")


@dataclass(frozen=True)
class EvaluationContext:
    """External cohort facts; absent attestations stay unknown.

    session_dates is the owner's 252-session exchange calendar, not a calendar
    generated here. Four enrollment quarters are fixed indices 0:63, 63:126,
    126:189, 189:252. Counts include the full first-T2 ledger before exclusions.
    eligible_issuer_ids includes BOTH full pre-outcome matching pools, including
    unmatched issuers. intc_issuer_ids=() is an explicit attested absence; None
    is unknown. Full-cohort observed H5 range is distinct from matched range.
    """

    cohort_id: str
    session_dates: tuple[str, ...]
    dataset_kind: str = "SYNTHETIC_DRY_RUN"
    first_t2_count: int | None = None
    complete_primary_exposure_count: int | None = None
    eligible_q1_count: int | None = None
    activation_receipt_ref: str | None = None
    calendar_receipt_ref: str | None = None
    calendar_complete: bool | None = None
    enrollment_complete: bool | None = None
    final_h21_matured: bool | None = None
    frozen_matching_receipt_ref: str | None = None
    eligible_pool_receipt_ref: str | None = None
    eligible_issuer_ids: tuple[str, ...] | None = None
    intc_issuer_ids: tuple[str, ...] | None = None
    integrity_audit_passed: bool | None = None
    integrity_audit_receipt_ref: str | None = None
    observed_cohort_h5_range_pp: tuple[float, float] | None = None
    observed_cohort_h5_range_receipt_ref: str | None = None
    missingness_robustness_ruling: bool | None = None
    missingness_ruling_receipt_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.cohort_id, str) or not self.cohort_id:
            raise ValueError("cohort_id is required")
        object.__setattr__(self, "session_dates", tuple(self.session_dates))
        if len(self.session_dates) != CALENDAR_SESSIONS:
            raise ValueError("the frozen calendar must contain exactly 252 sessions")
        try:
            parsed = tuple(date.fromisoformat(item) for item in self.session_dates)
        except (TypeError, ValueError) as exc:
            raise ValueError("session_dates must be ISO dates") from exc
        if any(a >= b for a, b in zip(parsed, parsed[1:])):
            raise ValueError("session_dates must be unique and strictly increasing")
        if self.dataset_kind not in {"SYNTHETIC_DRY_RUN", "OFFLINE_OBSERVATION", "PROSPECTIVE_ENROLLED"}:
            raise ValueError("unknown dataset_kind")
        for name in ("first_t2_count", "complete_primary_exposure_count", "eligible_q1_count"):
            _nonnegative_count(getattr(self, name), name)
        if self.first_t2_count is not None and self.complete_primary_exposure_count is not None:
            if self.complete_primary_exposure_count > self.first_t2_count:
                raise ValueError("complete primary exposure count exceeds first-T2 count")
        if self.eligible_q1_count is not None and self.complete_primary_exposure_count is not None:
            if self.eligible_q1_count > self.complete_primary_exposure_count:
                raise ValueError("eligible Q1 count exceeds complete primary exposure count")
        for name in ("calendar_complete", "enrollment_complete", "final_h21_matured",
                     "integrity_audit_passed", "missingness_robustness_ruling"):
            _truth(getattr(self, name), name)
        for name in ("eligible_issuer_ids", "intc_issuer_ids"):
            value = getattr(self, name)
            if value is not None:
                value = tuple(value)
                object.__setattr__(self, name, value)
                if len(set(value)) != len(value) or any(not isinstance(x, str) or not x for x in value):
                    raise ValueError(f"{name} must contain unique nonempty strings")
        if self.eligible_issuer_ids is not None and self.intc_issuer_ids is not None:
            if not set(self.intc_issuer_ids).issubset(self.eligible_issuer_ids):
                raise ValueError("INTC identifiers are outside the full eligible pool")
        if self.observed_cohort_h5_range_pp is not None:
            values = tuple(self.observed_cohort_h5_range_pp)
            if len(values) != 2:
                raise ValueError("observed cohort range needs minimum and maximum")
            lower, upper = (_finite_number(value, "observed_cohort_h5_range_pp") for value in values)
            if lower > upper:
                raise ValueError("observed cohort range is reversed")
            object.__setattr__(self, "observed_cohort_h5_range_pp", (lower, upper))


@dataclass(frozen=True)
class OmissionSensitivity:
    """Externally recomputed matching, never an outcome-driven repair.

    ISSUER requires one omitted canonical ID. INTC may contain several IDs from
    the supplied full eligible pool. DATE/SECTOR/ROOT_COMPONENT are descriptive
    and do not substitute for the required issuer/INTC robustness evidence.
    """

    kind: str
    label: str
    pairs: tuple[FrozenPair, ...]
    omitted_issuer_ids: tuple[str, ...] = ()
    full_pool_rematch_receipt_ref: str | None = None
    eligible_q1_count: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"ISSUER", "INTC", "DATE", "SECTOR", "ROOT_COMPONENT"}:
            raise ValueError("unknown omission kind")
        if not self.label:
            raise ValueError("omission label is required")
        object.__setattr__(self, "pairs", tuple(self.pairs))
        object.__setattr__(self, "omitted_issuer_ids", tuple(self.omitted_issuer_ids))
        if len(set(self.omitted_issuer_ids)) != len(self.omitted_issuer_ids):
            raise ValueError("duplicate omitted issuer")
        if self.kind == "ISSUER" and len(self.omitted_issuer_ids) != 1:
            raise ValueError("ISSUER omission must remove exactly one canonical issuer")
        _nonnegative_count(self.eligible_q1_count, "eligible_q1_count")


@dataclass(frozen=True)
class BootstrapResult:
    block_length: int
    estimate_pp: float | None
    interval_pp: tuple[float, float] | None
    valid_draw_count: int
    no_active_date_draw_count: int
    nonfinite_draw_count: int
    replicates: tuple[float | None, ...]

    @property
    def inference_valid(self) -> bool:
        return self.valid_draw_count >= MIN_VALID_DRAWS and self.interval_pp is not None

    def report(self) -> dict[str, Any]:
        return {
            "block_length": self.block_length,
            "draw_count": BOOTSTRAP_DRAWS,
            "valid_draw_count": self.valid_draw_count,
            "no_active_date_draw_count": self.no_active_date_draw_count,
            "nonfinite_draw_count": self.nonfinite_draw_count,
            "interval_95_pp": self.interval_pp,
            "inference_valid": self.inference_valid,
            "lower_bound_above_zero": None if self.interval_pp is None else self.interval_pp[0] > 0,
        }


@lru_cache(maxsize=3)
def _calendar_samples(block_length: int) -> np.ndarray:
    if type(block_length) is not int or block_length not in BLOCK_LENGTHS:
        raise ValueError("PB-D fixes block lengths at 21, 10, and 42")
    # One fresh generator per L. Matrix order is draw, then block, then offset.
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    starts = rng.integers(0, CALENDAR_SESSIONS,
                          size=(BOOTSTRAP_DRAWS, math.ceil(CALENDAR_SESSIONS / block_length)))
    indices = (starts[:, :, None] + np.arange(block_length)) % CALENDAR_SESSIONS
    indices = indices.reshape(BOOTSTRAP_DRAWS, -1)[:, :CALENDAR_SESSIONS].astype(np.int16)
    indices.setflags(write=False)
    return indices


def circular_block_bootstrap(
    date_effects_pp: Sequence[float | None], *, block_length: int = 21
) -> BootstrapResult:
    """Exact frozen circular-calendar bootstrap, including inactive dates.

    Replicates retain fixed draw order; None denotes an invalid draw. The
    inactive-date computational placeholder contributes neither numerator nor
    denominator. It is never a zero-return observation. Linear quantiles are
    reported even for an insufficient draw count, with inference_valid=False.
    """
    values = tuple(date_effects_pp)
    if len(values) != CALENDAR_SESSIONS:
        raise ValueError("bootstrap requires the entire 252-session calendar")
    active = np.array([value is not None for value in values], dtype=bool)
    numbers = np.array([0.0 if value is None else _finite_number(value, "date effect")
                        for value in values], dtype=np.float64)
    indices = _calendar_samples(block_length)
    counts = active[indices].sum(axis=1)
    draws = np.full(BOOTSTRAP_DRAWS, np.nan, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        sums = numbers[indices].sum(axis=1)
        np.divide(sums, counts, out=draws, where=counts > 0)
    finite = (counts > 0) & np.isfinite(draws)
    valid = draws[finite]
    interval = None
    if len(valid):
        endpoints = np.quantile(valid, (0.025, 0.975), method="linear")
        if np.isfinite(endpoints).all():
            interval = (float(endpoints[0]), float(endpoints[1]))
    estimate = math.fsum(numbers[active]) / int(active.sum()) if active.any() else None
    return BootstrapResult(
        block_length=block_length,
        estimate_pp=estimate,
        interval_pp=interval,
        valid_draw_count=int(finite.sum()),
        no_active_date_draw_count=int((counts == 0).sum()),
        nonfinite_draw_count=int(((counts > 0) & ~np.isfinite(draws)).sum()),
        replicates=tuple(float(value) if known else None for value, known in zip(draws, finite)),
    )


def centered_bootstrap_p_value(estimate_pp: float, replicates: Sequence[float | None]) -> float:
    """The prespecified approximate null-centered, two-sided p-value.

    This is neither an exact randomization test nor an inversion of the
    percentile confidence interval. Eligibility is enforced by evaluate_pb_d.
    """
    theta = _finite_number(estimate_pp, "estimate_pp")
    valid = [_finite_number(value, "replicate") for value in replicates if value is not None]
    if not valid:
        raise ValueError("no valid bootstrap draws")
    exceedances = sum(abs(value - theta) >= abs(theta) for value in valid)
    return (1 + exceedances) / (1 + len(valid))


def holm_adjust(p_values: Sequence[float]) -> tuple[float, float, float, float]:
    """Holm step-down adjustment for the fixed FOUR-member secondary family."""
    values = tuple(_finite_number(value, "p-value") for value in p_values)
    if len(values) != 4 or any(not 0 <= value <= 1 for value in values):
        raise ValueError("Holm family must contain exactly four p-values in [0, 1]")
    adjusted = [1.0] * 4
    running = 0.0
    for rank, index in enumerate(sorted(range(4), key=lambda item: (values[item], item))):
        running = max(running, min(1.0, (4 - rank) * values[index]))
        adjusted[index] = running
    return tuple(adjusted)  # type: ignore[return-value]


def _validate_pairs(pairs: Sequence[FrozenPair]) -> None:
    pair_ids: set[str] = set()
    issuer_ids: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, FrozenPair):
            raise ValueError("pairs must be FrozenPair instances")
        if pair.pair_id in pair_ids:
            raise ValueError("duplicate frozen pair ID")
        pair_ids.add(pair.pair_id)
        for leg in (pair.q1, pair.q0):
            if leg.issuer_id in issuer_ids:
                raise ValueError("primary issuer reused across pairs or exposure arms")
            issuer_ids.add(leg.issuer_id)


def _endpoint_value(leg: Outcome, endpoint: str) -> float | None:
    if endpoint == PRIMARY_ENDPOINT:
        return leg.h5_spy_excess_pp
    if endpoint == SECONDARY_ENDPOINTS[0]:
        return None if leg.h5_spy_excess_pp is None else 100.0 * (leg.h5_spy_excess_pp > 0)
    if endpoint == SECONDARY_ENDPOINTS[1]:
        return leg.h10_spy_excess_pp
    if endpoint == SECONDARY_ENDPOINTS[2]:
        return leg.h21_spy_excess_pp
    if endpoint == SECONDARY_ENDPOINTS[3]:
        return None if leg.h5_clean_liftoff is None else 100.0 * leg.h5_clean_liftoff
    raise ValueError("unknown frozen endpoint")


def _statistics_from_differences(
    pairs: Sequence[FrozenPair], differences: Sequence[float | None]
) -> dict[str, Any]:
    if len(pairs) != len(differences):
        raise ValueError("a difference or an explicit None is required for every original pair")
    by_date: dict[int, list[float]] = defaultdict(list)
    complete_ids = []
    complete_differences = []
    for pair, difference in zip(pairs, differences):
        if difference is not None:
            by_date[pair.session_index].append(difference)
            complete_ids.append(pair.pair_id)
            complete_differences.append(difference)
    calendar = tuple(math.fsum(by_date[index]) / len(by_date[index]) if by_date[index] else None
                     for index in range(CALENDAR_SESSIONS))
    active_values = [value for value in calendar if value is not None]
    return {
        "original_pair_count": len(pairs),
        "complete_pair_count": len(complete_ids),
        "incomplete_pair_count": len(pairs) - len(complete_ids),
        "active_date_count": len(active_values),
        "endpoint_completeness": len(complete_ids) / len(pairs) if pairs else None,
        "equal_date_mean_increment_pp": math.fsum(active_values) / len(active_values) if active_values else None,
        "equal_pair_mean_increment_pp": math.fsum(complete_differences) / len(complete_differences)
        if complete_differences else None,
        "complete_pair_ids": tuple(complete_ids),
        "inactive_dates_are_zero_returns": False,
        "date_effects_pp": calendar,
        "complete_pairs_by_session": tuple(len(by_date[index]) for index in range(CALENDAR_SESSIONS)),
    }


def _endpoint_statistics(pairs: Sequence[FrozenPair], endpoint: str) -> dict[str, Any]:
    differences = []
    for pair in pairs:
        q1, q0 = _endpoint_value(pair.q1, endpoint), _endpoint_value(pair.q0, endpoint)
        differences.append(None if q1 is None or q0 is None else float(q1) - float(q0))
    return _statistics_from_differences(pairs, differences)


def _gate(passed: bool | None, **details: Any) -> dict[str, Any]:
    return {"status": "UNKNOWN" if passed is None else "PASS" if passed else "FAIL", **details}


def _ratio_gate(numerator: int | None, denominator: int | None, threshold: float) -> dict[str, Any]:
    value = None if numerator is None or denominator in (None, 0) else numerator / denominator
    return _gate(None if value is None else value >= threshold, numerator=numerator,
                 denominator=denominator, value=value, required_minimum=threshold)


def _attested_gate(value: bool | None, receipt: str | None, reason: str) -> dict[str, Any]:
    # A known failure does not become unknown merely because its citation is absent.
    return _gate(False if value is False else value if receipt else None,
                 receipt_ref=receipt, reason=reason, verified_by_this_module=False)


def _quarter_reports(primary: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    reports = []
    for quarter in range(4):
        start, stop = quarter * 63, (quarter + 1) * 63
        effects = primary["date_effects_pp"][start:stop]
        values = [value for value in effects if value is not None]
        pair_counts = primary["complete_pairs_by_session"][start:stop]
        reports.append({
            "enrollment_quarter": quarter + 1,
            "start_session_index": start, "stop_session_index_exclusive": stop,
            "complete_pair_count": sum(pair_counts), "active_date_count": len(values),
            "equal_date_mean_increment_pp": math.fsum(values) / len(values) if values else None,
            "equal_pair_mean_increment_pp": math.fsum(value * count for value, count in zip(effects, pair_counts)
                                                        if value is not None) / sum(pair_counts)
            if sum(pair_counts) else None,
            "active_date_sd_pp": float(np.std(values, ddof=1)) if len(values) > 1 else None,
            "descriptive_only": True,
        })
    return tuple(reports)


def _arm_summary(values: Sequence[float | None]) -> dict[str, Any]:
    known = [float(value) for value in values if value is not None]
    return {
        "valid_mature_count": len(known), "unknown_or_pending_count": len(values) - len(known),
        "equal_issuer_mean_pp": math.fsum(known) / len(known) if known else None,
        "median_pp": float(np.median(known)) if known else None,
        "strictly_positive_count": sum(value > 0 for value in known),
        "strictly_positive_rate": sum(value > 0 for value in known) / len(known) if known else None,
    }


def _descriptive_returns(
    pairs: Sequence[FrozenPair], *, cost_deduction_pp: float = 0.0
) -> dict[str, Any]:
    report = {}
    for horizon in (1, 5, 10, 21):
        report[f"h{horizon}"] = {}
        for measure in ("absolute_return_pp", "spy_excess_pp", "sector_excess_pp"):
            name = f"h{horizon}_{measure}"
            q1, q0 = [getattr(pair.q1, name) for pair in pairs], [getattr(pair.q0, name) for pair in pairs]
            differences = [None if a is None or b is None else a - b for a, b in zip(q1, q0)]
            stats = _statistics_from_differences(pairs, differences)
            report[f"h{horizon}"][measure] = {
                "q1": _arm_summary([None if value is None else value - cost_deduction_pp for value in q1]),
                "q0": _arm_summary([None if value is None else value - cost_deduction_pp for value in q0]),
                "complete_pair_count": stats["complete_pair_count"],
                # The same fixed deduction on both legs cancels algebraically.
                # Preserve the gross difference rather than manufacture a
                # floating-point residual by subtracting the deduction twice.
                "equal_date_mean_increment_pp": stats["equal_date_mean_increment_pp"],
                "equal_pair_mean_increment_pp": stats["equal_pair_mean_increment_pp"],
                "descriptive_only": True,
            }
    return report


def _fixed_cost_scenarios(pairs: Sequence[FrozenPair]) -> dict[str, Any]:
    """Fixed round-trip assumptions, not measured execution or added tests."""
    return {
        "descriptive_only": True,
        "scope": "original_frozen_pair_legs_by_exposure_arm",
        "gross_returns_remain_primary": True,
        "measured_execution_costs": False,
        "same_cost_deducted_from_each_issuer_return": True,
        "benchmark_return_is_not_charged_the_issuer_cost": True,
        "identical_costs_cancel_in_complete_pair_mean_increments": True,
        "arm_denominators": "valid_mature_individual_legs_for_each_horizon_and_return_measure",
        "paired_denominators": "original_pairs_with_both_outcomes_known_for_the_measure",
        "scenarios": tuple({
            "round_trip_cost_bps": bps,
            "deduction_pp": bps / 100.0,
            "horizons": _descriptive_returns(pairs, cost_deduction_pp=bps / 100.0),
        } for bps in FIXED_ROUND_TRIP_COSTS_BPS),
        "limitations": (
            "These fixed deductions do not measure spreads, slippage, market impact, capacity, borrow, or achievable fills.",
            "Equal cost deductions cancel in the paired mean; they do not estimate differential costs between exposure arms.",
            "Individual net-return hit rates can change even though the paired mean increment is unchanged.",
        ),
    }


def _responder_persistence(pairs: Sequence[FrozenPair]) -> dict[str, Any]:
    """Gross H5 SPY responders, with separate known H10/H21 denominators.

    The cumulative excess change is later excess minus H5 excess for the SAME
    mature responders. It is not a compounded return earned after H5. An
    unknown later outcome is censored, never counted as a reversal or failure.
    """
    report: dict[str, Any] = {
        "descriptive_only": True,
        "scope": "original_frozen_pair_legs_by_exposure_arm",
        "response_definition": "gross_h5_spy_excess_pp_strictly_greater_than_zero",
        "paired_completeness_required_for_individual_responder_report": False,
        "arms": {},
    }
    for arm in ("q1", "q0"):
        legs = [getattr(pair, arm) for pair in pairs]
        known_h5 = [leg for leg in legs if leg.h5_spy_excess_pp is not None]
        responders = [leg for leg in known_h5 if leg.h5_spy_excess_pp > 0]
        horizons = {}
        for horizon in (10, 21):
            field_name = f"h{horizon}_spy_excess_pp"
            mature = [leg for leg in responders if getattr(leg, field_name) is not None]
            later = [float(getattr(leg, field_name)) for leg in mature]
            earlier = [float(leg.h5_spy_excess_pp) for leg in mature]
            count = len(mature)
            positive = sum(value > 0 for value in later)
            reversals = sum(value <= 0 for value in later)
            horizons[f"h{horizon}"] = {
                "mature_known_denominator": count,
                "missing_or_pending_responder_count": len(responders) - count,
                "mature_responder_issuer_ids": tuple(leg.issuer_id for leg in mature),
                "still_spy_positive_count": positive,
                "persistence_fraction": positive / count if count else None,
                "reversal_count": reversals,
                "reversal_fraction": reversals / count if count else None,
                "mean_later_cumulative_spy_excess_pp": math.fsum(later) / count if count else None,
                "mean_h5_cumulative_spy_excess_pp_same_mature_responders": math.fsum(earlier) / count if count else None,
                "mean_change_in_cumulative_spy_excess_pp": math.fsum(b - a for a, b in zip(earlier, later)) / count
                if count else None,
                "post_h5_drawdown_pp": None,
                "post_h5_drawdown_status": "UNKNOWN_POST_H5_PRICE_PATH_NOT_SUPPLIED",
            }
        report["arms"][arm] = {
            "original_matched_issuer_count": len(legs),
            "h5_known_count": len(known_h5),
            "h5_unknown_or_pending_count": len(legs) - len(known_h5),
            "h5_responder_count": len(responders),
            "h5_known_nonresponder_count": len(known_h5) - len(responders),
            "h5_responder_issuer_ids": tuple(leg.issuer_id for leg in responders),
            "horizons": horizons,
        }
    return report


def _missingness_report(
    pairs: Sequence[FrozenPair], context: EvaluationContext, primary: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    known = [leg.h5_spy_excess_pp for pair in pairs for leg in (pair.q1, pair.q0)
             if leg.h5_spy_excess_pp is not None]
    report: dict[str, Any] = {
        "original_pairs_retained": True, "rematching_performed": False,
        "known_matched_h5_range_pp": (min(known), max(known)) if known else None,
        "observed_cohort_h5_range_pp": context.observed_cohort_h5_range_pp,
        "range_receipt_ref": context.observed_cohort_h5_range_receipt_ref,
        "scenarios_are_identification_bounds": False,
        "unobserved_returns_may_exceed_observed_range": True,
        "by_arm": {}, "scenarios": {},
    }
    for arm in ("q1", "q0"):
        legs = [getattr(pair, arm) for pair in pairs]
        report["by_arm"][arm] = {
            "entry_status_counts": dict(Counter(leg.entry_status for leg in legs)),
            "missing_h5_leg_count": sum(leg.h5_spy_excess_pp is None for leg in legs),
            "missing_h5_reason_counts": dict(Counter(leg.h5_missing_reason or "UNKNOWN_REASON"
                for leg in legs if leg.h5_spy_excess_pp is None)),
        }
    if not primary["incomplete_pair_count"]:
        report["scenario_status"] = "NOT_NEEDED_NO_MISSING_H5_LEGS"
        return report, _gate(True, reason="All original frozen pairs have two valid H5 legs")
    if context.observed_cohort_h5_range_pp is not None:
        low, high = context.observed_cohort_h5_range_pp
        if any(value < low or value > high for value in known):
            raise ValueError("declared full-cohort observed range omits a known matched outcome")
        if context.observed_cohort_h5_range_receipt_ref:
            for label, q1_fill, q0_fill in (("adverse_q1", low, high), ("favorable_q1", high, low)):
                differences = []
                imputations = []
                for pair in pairs:
                    a, b = pair.q1.h5_spy_excess_pp, pair.q0.h5_spy_excess_pp
                    for arm, original, replacement in (("q1", a, q1_fill), ("q0", b, q0_fill)):
                        if original is None:
                            imputations.append({"pair_id": pair.pair_id, "arm": arm, "assigned_h5_spy_excess_pp": replacement})
                    differences.append((q1_fill if a is None else a) - (q0_fill if b is None else b))
                stats = _statistics_from_differences(pairs, differences)
                intervals = {str(length): circular_block_bootstrap(stats["date_effects_pp"], block_length=length).report()
                             for length in BLOCK_LENGTHS}
                report["scenarios"][label] = {
                    "hypothetical_not_observed": True, "known_legs_retained": True,
                    "imputations": tuple(imputations), "point_estimate_pp": stats["equal_date_mean_increment_pp"],
                    "active_date_count": stats["active_date_count"], "bootstrap": intervals,
                    "practical_floor_met": stats["equal_date_mean_increment_pp"] >= PRACTICAL_FLOOR_PP,
                }
            report["scenario_status"] = "DESCRIPTIVE_OBSERVED_RANGE_SCENARIOS"
        else:
            report["scenario_status"] = "UNKNOWN_FULL_COHORT_RANGE_RECEIPT"
    else:
        report["scenario_status"] = "UNKNOWN_FULL_COHORT_OBSERVED_RANGE"
    gate = _attested_gate(context.missingness_robustness_ruling, context.missingness_ruling_receipt_ref,
                         "Frozen text leaves conclusion-dependence adjudication to an evidence-backed review; scenarios are not bounds")
    if not report["scenarios"] and gate["status"] == "PASS":
        gate = _gate(None, reason="Missing outcomes require the prespecified full-cohort range scenarios before a robustness ruling")
    if primary["equal_date_mean_increment_pp"] is not None and primary["equal_date_mean_increment_pp"] > 0:
        if any(scenario["point_estimate_pp"] <= 0 for scenario in report["scenarios"].values()):
            gate = _gate(False, reason="An observed-range scenario erases or reverses the observed positive increment",
                         supplied_ruling_receipt_ref=context.missingness_ruling_receipt_ref)
    return report, gate


def _omission_report(
    original_pairs: Sequence[FrozenPair], context: EvaluationContext,
    omissions: Sequence[OmissionSensitivity],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    original_legs = {leg.issuer_id: leg for pair in original_pairs for leg in (pair.q1, pair.q0)}
    original_strata = {getattr(pair, arm).issuer_id: (arm, pair.session_index, pair.sector)
                       for pair in original_pairs for arm in ("q1", "q0")}
    original_ids = set(original_legs)
    expected = set(context.eligible_issuer_ids) if context.eligible_issuer_ids is not None else None
    records = []
    issuer_results: dict[str, dict[str, Any]] = {}
    intc_results = []
    seen_labels = set()
    for omission in omissions:
        if (omission.kind, omission.label) in seen_labels:
            raise ValueError("duplicate omission kind/label")
        seen_labels.add((omission.kind, omission.label))
        _validate_pairs(omission.pairs)
        omitted = set(omission.omitted_issuer_ids)
        ids = {leg.issuer_id for pair in omission.pairs for leg in (pair.q1, pair.q0)}
        if ids & omitted:
            raise ValueError("omitted issuer remains in rematched sensitivity")
        if expected is not None and (not ids.issubset(expected) or not omitted.issubset(expected)):
            raise ValueError("omission contains issuers outside the original eligible pool")
        for pair in omission.pairs:
            for arm in ("q1", "q0"):
                leg = getattr(pair, arm)
                if leg.issuer_id in original_legs and leg != original_legs[leg.issuer_id]:
                    raise ValueError("omission changed an original issuer outcome")
                if leg.issuer_id in original_strata and original_strata[leg.issuer_id] != (arm, pair.session_index, pair.sector):
                    raise ValueError("omission changed an original issuer arm or frozen date/sector stratum")
        if omission.eligible_q1_count is not None and len(omission.pairs) > omission.eligible_q1_count:
            raise ValueError("omission matched count exceeds its eligible Q1 denominator")
        stats = _endpoint_statistics(omission.pairs, PRIMARY_ENDPOINT)
        estimate = stats["equal_date_mean_increment_pp"]
        evidence = bool(omission.full_pool_rematch_receipt_ref and context.eligible_pool_receipt_ref and expected is not None)
        record = {
            "kind": omission.kind, "label": omission.label, "omitted_issuer_ids": tuple(sorted(omitted)),
            "full_pool_rematch_receipt_ref": omission.full_pool_rematch_receipt_ref,
            "rematching_verified_by_this_module": False, "has_full_pool_receipt": evidence,
            "estimate_pp": estimate, "original_pair_count_after_rematch": len(omission.pairs),
            "complete_pair_count": stats["complete_pair_count"], "active_date_count": stats["active_date_count"],
            "matched_support": len(omission.pairs) / omission.eligible_q1_count if omission.eligible_q1_count else None,
            "matched_pair_count_change": len(omission.pairs) - len(original_pairs),
            "newly_matched_issuer_ids": tuple(sorted(ids - original_ids)),
            "no_longer_matched_issuer_ids": tuple(sorted(original_ids - ids)),
            "sign_gate": "UNKNOWN" if not evidence or estimate is None else "FAIL" if estimate < 0 else "PASS",
            "descriptive_only": True,
        }
        records.append(record)
        if omission.kind == "ISSUER":
            key = omission.omitted_issuer_ids[0]
            if key in issuer_results:
                raise ValueError("duplicate single-issuer omission")
            issuer_results[key] = record
        elif omission.kind == "INTC":
            intc_results.append(record)
    missing = None if expected is None else tuple(sorted(expected - set(issuer_results)))
    if any(record["sign_gate"] == "FAIL" for record in issuer_results.values()):
        issuer_gate = _gate(False, reason="Negative estimate after at least one attested full-pool issuer omission")
    elif expected is None or missing or not context.eligible_pool_receipt_ref:
        issuer_gate = _gate(None, reason="Complete eligible-pool issuer list and every rematched omission are required")
    else:
        issuer_gate = _gate(all(record["sign_gate"] == "PASS" for record in issuer_results.values())
                            if all(record["sign_gate"] != "UNKNOWN" for record in issuer_results.values()) else None)
    intc_ids = None if context.intc_issuer_ids is None else set(context.intc_issuer_ids)
    if intc_ids == set() and expected is not None and context.eligible_pool_receipt_ref:
        intc_gate = _gate(True, reason="INTC absent from the attested complete eligible pools; omission changes nothing")
    elif intc_ids is None:
        intc_gate = _gate(None, reason="Canonical INTC identifiers in the full eligible pool are unknown")
    else:
        matching = [record for record in intc_results if set(record["omitted_issuer_ids"]) == intc_ids]
        if len(matching) > 1:
            raise ValueError("duplicate complete INTC omission")
        status = matching[0]["sign_gate"] if matching else "UNKNOWN"
        intc_gate = _gate(None if status == "UNKNOWN" else status == "PASS")
    report = {
        "records": tuple(records), "required_issuer_omission_count": None if expected is None else len(expected),
        "missing_issuer_omissions": missing, "original_pair_filter_is_rematching": False,
        "largest_matched_pair_count_loss": max((max(0, -record["matched_pair_count_change"]) for record in records), default=None),
        "date_sector_root_sensitivities": {kind: "REPORTED" if any(record["kind"] == kind for record in records) else "UNKNOWN_NOT_SUPPLIED"
                                           for kind in ("DATE", "SECTOR", "ROOT_COMPONENT")},
    }
    return report, issuer_gate, intc_gate


def evaluate_pb_d(
    pairs: Sequence[FrozenPair], context: EvaluationContext,
    *, omissions: Sequence[OmissionSensitivity] = (),
) -> dict[str, Any]:
    """Evaluate frozen pairs without modifying inputs or creating observations.

    The result is JSON-ready (allow_nan=False). Synthetic/dry-run inputs always
    have status NOT_ENROLLED and no preregistered cohort classification. Missing
    adequacy evidence produces DESCRIPTIVE_INSUFFICIENT for observational inputs.
    Even a fully supported positive result is RESEARCH_POSITIVE_REVIEW_ONLY.
    """
    pairs, omissions = tuple(pairs), tuple(omissions)
    if not isinstance(context, EvaluationContext):
        raise ValueError("context must be EvaluationContext")
    _validate_pairs(pairs)
    if context.eligible_q1_count is not None and len(pairs) > context.eligible_q1_count:
        raise ValueError("matched Q1 count exceeds the full eligible Q1 denominator")
    if context.complete_primary_exposure_count is not None and 2 * len(pairs) > context.complete_primary_exposure_count:
        raise ValueError("original pairs exceed the fully covered first-T2 issuer count")
    original_ids = {leg.issuer_id for pair in pairs for leg in (pair.q1, pair.q0)}
    if context.eligible_issuer_ids is not None and not original_ids.issubset(context.eligible_issuer_ids):
        raise ValueError("original pair issuer is outside the declared full eligible pool")
    if context.intc_issuer_ids is not None:
        known_intc = {leg.issuer_id for pair in pairs for leg in (pair.q1, pair.q0) if leg.ticker_at_cut.upper() == "INTC"}
        if not known_intc.issubset(context.intc_issuer_ids):
            raise ValueError("INTC pool declaration omits a known matched INTC issuer")
    primary = _endpoint_statistics(pairs, PRIMARY_ENDPOINT)
    bootstrap = {str(length): circular_block_bootstrap(primary["date_effects_pp"], block_length=length)
                 for length in BLOCK_LENGTHS}
    primary["bootstrap"] = {key: result.report() for key, result in bootstrap.items()}
    quarters = _quarter_reports(primary)
    # These validate the cohort on which an endpoint test would operate. They
    # are distinct from primary significance, practical size, and support gates;
    # a null/adverse primary does not disable a prespecified secondary endpoint.
    secondary_context_gates = {
        "calendar": _attested_gate(context.calendar_complete, context.calendar_receipt_ref,
                                    "An invalid or unverified calendar cannot support inference"),
        "source_integrity": _attested_gate(context.integrity_audit_passed, context.integrity_audit_receipt_ref,
                                            "An invalid or unverified timing/root/price/version audit cannot support inference"),
        "frozen_pre_outcome_matching": _gate(True if context.frozen_matching_receipt_ref else None,
                                              receipt_ref=context.frozen_matching_receipt_ref),
    }
    secondary = {}
    p_values = []
    for endpoint in SECONDARY_ENDPOINTS:
        stats = _endpoint_statistics(pairs, endpoint)
        result = circular_block_bootstrap(stats["date_effects_pp"], block_length=21)
        reasons = []
        if stats["complete_pair_count"] < 200:
            reasons.append("FEWER_THAN_200_COMPLETE_PAIRS")
        if stats["active_date_count"] < 50:
            reasons.append("FEWER_THAN_50_ACTIVE_DATES")
        if stats["endpoint_completeness"] is None or stats["endpoint_completeness"] < 0.95:
            reasons.append("ENDPOINT_COMPLETENESS_BELOW_95_PERCENT")
        if not result.inference_valid:
            reasons.append("INSUFFICIENT_VALID_BOOTSTRAP_DRAWS_OR_NONFINITE_INTERVAL")
        numerical_gates_passed = not reasons
        if context.dataset_kind != "PROSPECTIVE_ENROLLED" or not context.activation_receipt_ref:
            reasons.append("NOT_AN_ENROLLED_PROSPECTIVE_COHORT")
        elif context.enrollment_complete is not True or context.final_h21_matured is not True:
            reasons.append("FIXED_COHORT_OR_FINAL_MATURITY_WAIT_NOT_CONFIRMED_COMPLETE")
        for name, gate in secondary_context_gates.items():
            if gate["status"] != "PASS":
                reasons.append(f"{name.upper()}_NOT_CONFIRMED_VALID")
        p_value = 1.0 if reasons else centered_bootstrap_p_value(stats["equal_date_mean_increment_pp"], result.replicates)
        stats.update({"bootstrap": result.report(), "test_eligible": not reasons,
                      "numerical_endpoint_gates_passed": numerical_gates_passed,
                      "descriptive_only": bool(reasons), "ineligibility_reasons": tuple(reasons),
                      "family_p_value": p_value,
                      "p_value_method": "approximate_null_centered_calendar_bootstrap" if not reasons else "fixed_family_placeholder_1"})
        secondary[endpoint] = stats
        p_values.append(p_value)
    adjusted = holm_adjust(p_values)
    for endpoint, p_value in zip(SECONDARY_ENDPOINTS, adjusted):
        secondary[endpoint]["holm_adjusted_p_value"] = p_value
        secondary[endpoint]["holm_reject_at_0_05"] = secondary[endpoint]["test_eligible"] and p_value <= 0.05
    missingness, missingness_gate = _missingness_report(pairs, context, primary)
    omission_report, issuer_gate, intc_gate = _omission_report(pairs, context, omissions)
    primary_interval = bootstrap["21"].interval_pp
    point = primary["equal_date_mean_increment_pp"]
    adequacy = {
        "prospective_activation": _gate(bool(context.activation_receipt_ref) if context.dataset_kind == "PROSPECTIVE_ENROLLED" else None,
                                       receipt_ref=context.activation_receipt_ref),
        "fixed_252_session_exchange_calendar": _attested_gate(context.calendar_complete, context.calendar_receipt_ref,
                                                              "Calendar dates are checked for length/order; exchange-session correctness is externally attested"),
        "enrollment_complete": _gate(context.enrollment_complete),
        "final_21_session_maturity_wait_complete": _gate(context.final_h21_matured),
        "frozen_pre_outcome_matching": _gate(True if context.frozen_matching_receipt_ref else None,
                                             receipt_ref=context.frozen_matching_receipt_ref),
        "complete_distinct_q1_q0_pairs": _gate(primary["complete_pair_count"] >= 200,
                                               observed=primary["complete_pair_count"], required_minimum=200,
                                               power_guarantee=False),
        "complete_pair_decision_dates": _gate(primary["active_date_count"] >= 50,
                                               observed=primary["active_date_count"], required_minimum=50),
        "all_four_fixed_enrollment_quarters": _gate(all(item["complete_pair_count"] > 0 for item in quarters)),
        "matched_support": _ratio_gate(len(pairs), context.eligible_q1_count, 0.70),
        "primary_exposure_coverage": _ratio_gate(context.complete_primary_exposure_count, context.first_t2_count, 0.80),
        "h5_complete_pair_outcomes": _ratio_gate(primary["complete_pair_count"], len(pairs), 0.95),
        "timing_root_price_version_integrity": _attested_gate(context.integrity_audit_passed, context.integrity_audit_receipt_ref,
                                                              "No material unresolved timing, root, price, or version audit failure"),
        "valid_bootstrap_all_lengths": _gate(all(result.inference_valid for result in bootstrap.values())),
    }
    robustness = {
        "primary_l21_interval_above_zero": _gate(None if primary_interval is None else primary_interval[0] > 0),
        "all_three_interval_lower_bounds_above_zero": _gate(all(result.interval_pp[0] > 0 for result in bootstrap.values())
                                                            if all(result.interval_pp is not None for result in bootstrap.values()) else None),
        "practical_point_increment_at_least_2_pp": _gate(None if point is None else point >= PRACTICAL_FLOOR_PP,
                                                        point_increment_pp=point, required_minimum_pp=PRACTICAL_FLOOR_PP,
                                                        establishes_true_effect_at_least_2_pp=False),
        "no_single_issuer_omission_sign_reversal": issuer_gate,
        "no_intc_omission_sign_reversal": intc_gate,
        "not_dependent_on_missing_outcome_sensitivity": missingness_gate,
    }
    adequate = all(value["status"] == "PASS" for value in adequacy.values())
    robust = all(value["status"] == "PASS" for value in robustness.values())
    if context.dataset_kind == "SYNTHETIC_DRY_RUN":
        status, classification = "NOT_ENROLLED", None
    elif not adequate:
        status, classification = "DESCRIPTIVE_INSUFFICIENT", "INCONCLUSIVE_UNDERPOWERED_OR_INVALID"
    elif primary_interval is None or primary_interval[0] <= 0:
        status = classification = "PRIMARY_NOT_CONFIRMED"
    elif not robust:
        status = classification = "PRIMARY_POSITIVE_NOT_ROBUST"
    else:
        status = classification = "RESEARCH_POSITIVE_REVIEW_ONLY"
    sector_counts = Counter(pair.sector for pair in pairs if pair.sector is not None)
    root_counts = Counter(root for pair in pairs for leg in (pair.q1, pair.q0) for root in (leg.root_ids or ()))
    return {
        "schema_version": "pb-d-offline-evaluation-v1", "cohort_id": context.cohort_id,
        "dataset_kind": context.dataset_kind, "status": status, "preregistered_classification": classification,
        "signal_authority": "ZERO", "automatic_promotion": False, "enrollment_created": False,
        "method": {"calendar_sessions": CALENDAR_SESSIONS, "bootstrap_draws": BOOTSTRAP_DRAWS,
                   "frozen_design_commit": "df2091915159dab94f316718caa9b2662098eae4",
                   "block_lengths": BLOCK_LENGTHS, "primary_block_length": 21, "rng": "Generator(PCG64)",
                   "seed_restarted_per_block_length": BOOTSTRAP_SEED, "minimum_valid_draws": MIN_VALID_DRAWS,
                   "quantile_method": "linear", "interval_quantiles": (0.025, 0.975),
                   "input_and_effect_units": "percentage_points", "numpy_version": np.__version__,
                   "python_version": platform.python_version(), "secondary_family_size": 4,
                   "secondary_family_order": SECONDARY_ENDPOINTS,
                   "descriptive_round_trip_cost_scenarios_bps": FIXED_ROUND_TRIP_COSTS_BPS,
                   "synthetic_results_are_enrolled_observations": False,
                   "receipt_authentication_performed": False},
        "session_dates": context.session_dates, "primary": primary, "secondary": secondary,
        "secondary_context_gates": secondary_context_gates,
        "adequacy_gates": adequacy, "robustness_gates": robustness,
        "primary_interval_is_adverse": None if primary_interval is None else primary_interval[1] < 0,
        "quarters": quarters, "descriptive_horizons": _descriptive_returns(pairs),
        "fixed_round_trip_cost_scenarios": _fixed_cost_scenarios(pairs),
        "h5_spy_responder_persistence": _responder_persistence(pairs),
        "missingness": missingness, "omission_sensitivity": omission_report,
        "flow": {"first_t2": context.first_t2_count, "complete_primary_exposure": context.complete_primary_exposure_count,
                 "eligible_q1": context.eligible_q1_count, "matched_q1": len(pairs), "matched_q0": len(pairs),
                 "unmatched_eligible_q1": None if context.eligible_q1_count is None else context.eligible_q1_count - len(pairs),
                 "complete_h5_pairs": primary["complete_pair_count"],
                 "unknown_primary_exposure": None if context.first_t2_count is None or context.complete_primary_exposure_count is None
                 else context.first_t2_count - context.complete_primary_exposure_count,
                 "stratified_coverage": "UNKNOWN_NOT_SUPPLIED_BY_PAIR_ONLY_API"},
        "concentration": {"scope": "original_matched_issuers", "distinct_issuer_count": 2 * len(pairs),
                          "largest_complete_date_pair_count": max(primary["complete_pairs_by_session"], default=0),
                          "sector_pair_counts": dict(sorted(sector_counts.items())),
                          "unknown_sector_pair_count": sum(pair.sector is None for pair in pairs),
                          "root_issuer_counts": dict(sorted(root_counts.items())),
                          "unknown_root_lineage_issuer_count": sum(leg.root_ids is None for pair in pairs for leg in (pair.q1, pair.q0))},
        "limitations": (
            "200 complete pairs is a breadth floor, not an 80% power claim.",
            "Calendar-block intervals are approximate; gates do not certify nominal coverage.",
            "Unplanned subgroups and T1 interactions remain descriptive and cannot rescue a failed primary.",
            "Equal shared benchmark/cost deductions cancel in same-time paired mean increments.",
            "Practical-floor failure maps to PRIMARY_POSITIVE_NOT_ROBUST; the frozen text does not name a separate category.",
            "Missing-outcome conclusion dependence requires an evidence-backed ruling; observed-range scenarios are not identification bounds.",
        ),
    }


@dataclass(frozen=True)
class OHLCBar:
    """One corporate-action-consistent daily bar, timed at regular close."""

    close_at: str
    high: float | None
    low: float | None
    close: float | None

    def __post_init__(self) -> None:
        _aware_time(self.close_at)
        for name in ("high", "low", "close"):
            value = getattr(self, name)
            if value is not None and _finite_number(value, name) <= 0:
                raise ValueError("OHLC prices must be positive")
        if self.high is not None and self.low is not None and self.high < self.low:
            raise ValueError("bar high is below low")
        if self.close is not None and ((self.high is not None and self.close > self.high)
                                      or (self.low is not None and self.close < self.low)):
            raise ValueError("close lies outside bar range")


def _aware_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("a timestamp with an explicit UTC offset is required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("date-only or naive timestamps cannot certify price clocks")
    return parsed


def compute_ohlc_path(
    *, entry_close: float, entry_close_at: str, decision_cut: str,
    pre_cut_bars: Sequence[OHLCBar], post_entry_bars: Sequence[OHLCBar],
    expected_post_entry_closes: Sequence[str], price_basis_receipt_ref: str | None,
    expected_pre_cut_closes: Sequence[str] | None = None,
    calendar_receipt_ref: str | None = None,
) -> dict[str, Any]:
    """Research OHLC utility; absent bars retain their calendar position.

    The caller supplies an exchange calendar and aligned-price receipt. ATR20
    and B20 remain unknown without expected_pre_cut_closes AND its calendar
    receipt. At least 21 expected pre-cut slots supply the prior close for 20
    true ranges. Missing bars retain their expected calendar positions; 21
    supplied bars cannot silently bridge a missing session. The calendar owner
    attests the complete schedule; structural checks do not authenticate it.
    The utility rejects any pre-fill bar, future pre-cut bar, or extra post
    bar instead of silently changing the measurement window. Receipt identity
    is reported but not authenticated here. No intraday ordering is invented.
    """
    entry = _finite_number(entry_close, "entry_close")
    if entry <= 0:
        raise ValueError("entry_close must be positive")
    cut, entry_time = _aware_time(decision_cut), _aware_time(entry_close_at)
    if cut >= entry_time:
        raise ValueError("hypothetical entry must be after the decision cut")
    before, after = tuple(pre_cut_bars), tuple(post_entry_bars)
    pre_times = tuple(_aware_time(bar.close_at) for bar in before)
    if any(a >= b for a, b in zip(pre_times, pre_times[1:])) or any(time >= cut for time in pre_times):
        raise ValueError("pre-cut bars must be ordered completed sessions strictly before cut")
    expected_before = None
    aligned_before = ()
    if expected_pre_cut_closes is not None:
        expected_before = tuple(_aware_time(value) for value in expected_pre_cut_closes)
        if any(time >= cut for time in expected_before) or any(a >= b for a, b in zip(expected_before, expected_before[1:])):
            raise ValueError("pre-cut calendar must contain ordered completed sessions strictly before cut")
        pre_supplied = dict(zip(pre_times, before))
        if not set(pre_supplied).issubset(expected_before):
            raise ValueError("pre-cut bar is outside the explicit expected calendar")
        aligned_before = tuple(pre_supplied.get(time) for time in expected_before)
    expected = tuple(_aware_time(value) for value in expected_post_entry_closes)
    if any(time <= entry_time for time in expected) or any(a >= b for a, b in zip(expected, expected[1:])):
        raise ValueError("post-entry calendar must be ordered and strictly after entry close")
    supplied = {_aware_time(bar.close_at): bar for bar in after}
    if len(supplied) != len(after) or not set(supplied).issubset(expected):
        raise ValueError("duplicate or out-of-calendar post-entry bar (entry-session high/low is prohibited)")
    aligned = tuple(supplied.get(time) for time in expected)
    basis_known = bool(price_basis_receipt_ref)
    pre_calendar_known = expected_before is not None and bool(calendar_receipt_ref)
    b20 = None
    atr20 = None
    if (basis_known and pre_calendar_known and len(aligned_before) >= 20
            and all(bar is not None and bar.high is not None for bar in aligned_before[-20:])):
        b20 = max(bar.high for bar in aligned_before[-20:])
    if basis_known and pre_calendar_known and len(aligned_before) >= 21:
        ranges = []
        for previous, current in zip(aligned_before[-21:-1], aligned_before[-20:]):
            if previous is None or current is None or previous.close is None or current.high is None or current.low is None:
                break
            ranges.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
        if len(ranges) == 20:
            atr20 = math.fsum(ranges) / 20
    horizons = {}
    for horizon in (1, 5, 10, 21):
        window = aligned[:horizon]
        complete_close = basis_known and len(window) == horizon and all(bar is not None and bar.close is not None for bar in window)
        complete_ohlc = complete_close and all(bar.high is not None and bar.low is not None for bar in window)
        result: dict[str, Any] = {"status": "KNOWN" if complete_ohlc else "UNKNOWN_PATH_OR_PRICE_BASIS",
                                  "expected_sessions": horizon,
                                  "observed_close_count": sum(bar is not None and bar.close is not None for bar in window),
                                  "mfe_pp": None, "mae_pp": None, "close_mfe_pp": None,
                                  "close_mae_pp": None, "close_peak_to_trough_drawdown_pp": None,
                                  "absolute_return_pp": None}
        if complete_close:
            closes = [bar.close for bar in window]
            peak, drawdown = entry, 0.0
            for close in closes:
                peak = max(peak, close)
                drawdown = min(drawdown, 100 * (close / peak - 1))
            result.update(close_mfe_pp=max(0.0, max(100 * (value / entry - 1) for value in closes)),
                          close_mae_pp=min(0.0, min(100 * (value / entry - 1) for value in closes)),
                          close_peak_to_trough_drawdown_pp=drawdown,
                          absolute_return_pp=100 * (closes[-1] / entry - 1))
        if complete_ohlc:
            result.update(mfe_pp=max(0.0, max(100 * (bar.high / entry - 1) for bar in window)),
                          mae_pp=min(0.0, min(100 * (bar.low / entry - 1) for bar in window)))
        horizons[f"h{horizon}"] = result
    path5 = horizons["h5"]["status"] == "KNOWN"
    clean = {"label": None, "reason": "UNKNOWN_ATR_OR_H5_PATH", "first_upper_session": None, "first_lower_session": None}
    if path5 and atr20 is not None:
        upper = next((i + 1 for i, bar in enumerate(aligned[:5]) if bar.high >= entry + atr20), None)
        lower = next((i + 1 for i, bar in enumerate(aligned[:5]) if bar.low <= entry - atr20), None)
        clean.update(first_upper_session=upper, first_lower_session=lower)
        if atr20 == 0:
            clean["reason"] = "UNKNOWN_COINCIDENT_ZERO_ATR_BARRIERS"
        elif upper is not None and upper == lower:
            clean["reason"] = "UNKNOWN_SAME_BAR_FIRST_CROSSING_ORDER"
        else:
            clean.update(label=bool(upper is not None and (lower is None or upper < lower) and aligned[4].close > entry),
                         reason="UNAMBIGUOUS_DAILY_PATH")
    failed = {"label": None, "status": "UNKNOWN", "at_entry_subset": None}
    if b20 is not None:
        failed["at_entry_subset"] = entry > b20
        if entry <= b20:
            failed["status"] = "NOT_APPLICABLE"
        elif atr20 is not None and horizons["h5"]["absolute_return_pp"] is not None:
            failed.update(label=any(bar.close < b20 - 0.5 * atr20 for bar in aligned[:5]), status="KNOWN")
    return {
        "scope": "OFFLINE_RESEARCH_PATH_MEASUREMENT", "signal_authority": "ZERO",
        "price_basis_receipt_ref": price_basis_receipt_ref, "receipt_authentication_performed": False,
        "calendar_receipt_ref": calendar_receipt_ref,
        "pre_cut_session_contiguity": "EXPLICIT_OWNER_SCHEDULE_ALIGNED" if pre_calendar_known else "UNKNOWN_EXPECTED_CALENDAR_OR_RECEIPT",
        "expected_pre_cut_bar_count": None if expected_before is None else len(expected_before),
        "missing_expected_pre_cut_bar_count": None if expected_before is None else sum(bar is None for bar in aligned_before),
        "atr20_at_cut": atr20, "b20_at_cut": b20,
        "horizons": horizons, "h5_clean_liftoff": clean, "h5_failed_breakout": failed,
        "entry_session_intraday_range_included": False,
    }
