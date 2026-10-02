"""SUE — Standardized Unexpected Earnings (earnings-momentum) from the quarterly
EDGAR EPS panel (collectors/edgar_eps.py).

SUE expresses the post-earnings-announcement-drift (PEAD) effect: a company whose
latest quarterly EPS beat a naive seasonal-random-walk expectation (the same quarter
a year ago) tends to keep drifting in that direction. We compute, per company:

    surprise   = EPS_q − EPS_{q-4}                 (seasonal random walk)
    SUE        = surprise / σ(trailing surprises)  (standardized by its own history)

Quarters are matched by CALENDAR (the year-ago quarter within ±50 days), so a gap in
the filing history does not silently misalign the lag. Everything is point-in-time:
only quarters whose synthetic as-of date (period_end + reporting lag) is on or before
the rebalance date are visible, and a stale name (no fresh filing within ~7 months) is
dropped. Returns one raw SUE per ticker; the caller cross-sectionally winsorizes/z's.

DISPLAY/SIGNAL status is decided by scripts/validate_sue.py (Phase-0 IC/FDR) before
any wiring — see research/DATA_SIGNAL_EXPANSION_2026.md.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from math import isfinite, isclose
from statistics import mean, median, stdev
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from collectors.edgar_eps import eps_panel_path


def load_panel() -> pd.DataFrame | None:
    p = eps_panel_path()
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["asof_date"] = pd.to_datetime(df["asof_date"])
    return df


def _seasonal_diffs(period_end: np.ndarray, eps: np.ndarray,
                    tol_days: int = 50) -> list[tuple[pd.Timestamp, float]]:
    """[(period_end, EPS_q − EPS_year-ago)] matched by calendar (year-ago within ±tol)."""
    out = []
    pe = period_end.astype("datetime64[D]")
    for i in range(len(pe)):
        target = pe[i] - np.timedelta64(365, "D")
        best_j, best_gap = -1, tol_days + 1
        for j in range(i):
            gap = abs(int((pe[j] - target) / np.timedelta64(1, "D")))
            if gap <= best_gap:
                best_gap, best_j = gap, j
        if best_j >= 0 and best_gap <= tol_days:
            out.append((pd.Timestamp(pe[i]), float(eps[i] - eps[best_j])))
    return out


def sue_cross_section(panel: pd.DataFrame, asof, *, min_diffs: int = 4,
                      vol_window: int = 12, recency_days: int = 215) -> pd.Series:
    """Point-in-time raw SUE per ticker knowable on `asof`. None of the inputs use a
    quarter not yet 'filed' (asof_date <= asof). Stale names (latest filed quarter older
    than recency_days) are dropped so we only ever read a recent surprise."""
    asof = pd.Timestamp(asof)
    sub = panel[panel["asof_date"] <= asof]
    out: dict[str, float] = {}
    for tic, g in sub.groupby("ticker"):
        g = g.sort_values("period_end")
        if len(g) < min_diffs + 2:
            continue
        diffs = _seasonal_diffs(g["period_end"].values, g["eps_q"].values)
        if len(diffs) < min_diffs:
            continue
        last_pe, last_d = diffs[-1]
        if (asof - last_pe).days > recency_days:        # no fresh quarter -> stale/delisted
            continue
        recent = pd.Series([d for _pe, d in diffs[-vol_window:]])
        sd = recent.std()
        if not sd or np.isnan(sd) or sd == 0:
            continue
        out[tic] = last_d / sd
    return pd.Series(out, dtype=float)


def winsor_z(s: pd.Series, cap: float = 3.0) -> pd.Series:
    """Cross-sectional standardize + clip (for the LIVE factor score; rank IC is
    invariant to this, so the Phase-0 harness ranks the raw SUE directly)."""
    s = s.replace([np.inf, -np.inf], np.nan)
    mu, sd = s.mean(), s.std()
    if not sd or np.isnan(sd):
        return pd.Series(np.nan, index=s.index)
    return ((s - mu) / sd).clip(-cap, cap)

# ---------------------------------------------------------------------------
# Prophet Earnings / Expectation Revision factual evidence — v1
# ---------------------------------------------------------------------------
SCHEMA = "prophet.earnings_evidence/v1"
SUE_OBSERVATION_SCHEMA = "prophet.sue_observation/v2"
SUE_COMPAT_VERSION = "numeric-sue-compat-v1.1"

EXPECTATION_KINDS = frozenset({"ANALYST_CONSENSUS", "SEASONAL_MODEL"})
FORECAST_STATES = frozenset({"ACTIVE", "WITHDRAWN"})
# A numerical value above expectation is not automatically a favorable earnings result.
HIGHER_IS_IMPROVEMENT_METRICS = frozenset({"revenue", "total_net_sales", "gross_profit", "operating_income", "net_income", "EPS", "eps_diluted"})


class EvidenceError(ValueError):
    """Evidence is invalid or incomparable; never coerce it into a negative signal."""


def finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if isfinite(result) else None


def aware_utc(value: str, field: str = "timestamp") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"missing {field}")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"invalid {field}") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise EvidenceError(f"naive {field}")
    return result.astimezone(timezone.utc)


def required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"missing {field}")
    return value


def legacy_sue_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    """Correct the meaning of the legacy SUE observation without adding authority.

    The board's sue_z is a cross-sectional standardization of a seasonal EPS-change
    proxy.  It is not evidence of an analyst-consensus beat and its sign is not a
    retained raw EPS_q - EPS_year_ago value.  Legacy ranking remains frozen unless
    an explicit caller selects SUE_COMPAT_VERSION.
    """
    if not isinstance(row, Mapping):
        raise EvidenceError("earnings evidence row must be a mapping")
    z = finite(row.get("sue_z"))
    age = finite(row.get("sue_fresh_days"))
    age_ok = age is not None and age >= 0 and age.is_integer()
    reasons: list[str] = []
    if z is None:
        reasons.append("relative_value_missing_or_invalid")
    if age is None:
        reasons.append("reported_age_missing_or_invalid")
    elif not age_ok:
        reasons.append("reported_age_negative_or_fractional")

    if z is None or not age_ok:
        state, positive = "UNAVAILABLE", None
    elif age > 60:
        state, positive = "STALE", False
    else:
        state, positive = "FRESH_REPORTED_RELATIVE_VALUE", z > 0

    return {
        "schema": SUE_OBSERVATION_SCHEMA,
        "measure": "cross_sectional_z_of_seasonal_eps_momentum",
        "relative_z": z,
        "relative_direction": (
            None
            if z is None
            else "ABOVE_PEERS"
            if z > 0
            else "BELOW_PEERS"
            if z < 0
            else "AT_PEER_MEAN"
        ),
        "reported_age_days": int(age) if age_ok else None,
        "age_basis": "legacy_reported_days_not_verified_event_availability",
        "state": state,
        "fresh_positive_relative": positive,
        "raw_seasonal_surprise_direction": None,
        "analyst_consensus_beat": None,
        "rank_authority": False,
        "entry_authority": False,
        "reasons": reasons,
    }


@dataclass(frozen=True)
class MetricBasis:
    """Comparable identity and accounting basis resolved by a native source owner."""

    issuer_id: str
    issuer_name: str
    metric: str
    fiscal_period: str
    period_role: str
    period_start: str
    period_end: str
    currency: str
    unit: str
    accounting_basis: str
    share_basis: str = "NOT_APPLICABLE"

    def __post_init__(self) -> None:
        for field, value in asdict(self).items():
            required_text(value, field)
        try:
            start = date.fromisoformat(self.period_start)
            end = date.fromisoformat(self.period_end)
        except ValueError as exc:
            raise EvidenceError("invalid fiscal period") from exc
        if end < start:
            raise EvidenceError("reversed fiscal period")

    @property
    def days(self) -> int:
        return (date.fromisoformat(self.period_end) - date.fromisoformat(self.period_start)).days + 1

    @property
    def comparison_key(self) -> tuple[str, ...]:
        return (
            self.issuer_id,
            self.metric,
            self.period_role,
            self.currency,
            self.unit,
            self.accounting_basis,
            self.share_basis,
        )


@dataclass(frozen=True)
class Actual:
    basis: MetricBasis
    value: float
    public_at: str
    available_at: str
    source_ref: str
    event_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MetricBasis) or finite(self.value) is None:
            raise EvidenceError("invalid actual")
        public = aware_utc(self.public_at, "public_at")
        available = aware_utc(self.available_at, "available_at")
        if available < public:
            raise EvidenceError("actual available before publication")
        required_text(self.source_ref, "actual source_ref")
        required_text(self.event_id, "event_id")


@dataclass(frozen=True)
class Expectation:
    basis: MetricBasis
    value: float
    forecast_at: str
    available_at: str
    source_ref: str
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MetricBasis) or finite(self.value) is None:
            raise EvidenceError("invalid expectation")
        if self.kind not in EXPECTATION_KINDS:
            raise EvidenceError("unknown expectation kind")
        forecast = aware_utc(self.forecast_at, "forecast_at")
        available = aware_utc(self.available_at, "expectation available_at")
        if available < forecast:
            raise EvidenceError("expectation available before forecast observation")
        required_text(self.source_ref, "expectation source_ref")


@dataclass(frozen=True)
class HistoricalForecastError:
    error: float
    available_at: str
    event_id: str
    source_ref: str
    calibration_key: str
    expectation_kind: str

    def __post_init__(self) -> None:
        if finite(self.error) is None:
            raise EvidenceError("invalid historical forecast error")
        aware_utc(self.available_at, "historical error available_at")
        if self.expectation_kind not in EXPECTATION_KINDS:
            raise EvidenceError("invalid historical expectation kind")
        for field in ("event_id", "source_ref", "calibration_key"):
            required_text(getattr(self, field), field)


@dataclass(frozen=True)
class Forecast:
    basis: MetricBasis
    contributor: str
    value: float | None
    forecast_at: str
    available_at: str
    revision_id: str
    source_ref: str
    state: str = "ACTIVE"
    valid_until: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MetricBasis) or self.state not in FORECAST_STATES:
            raise EvidenceError("invalid forecast")
        if self.state == "ACTIVE" and finite(self.value) is None:
            raise EvidenceError("invalid active forecast value")
        forecast = aware_utc(self.forecast_at, "forecast_at")
        available = aware_utc(self.available_at, "forecast available_at")
        if available < forecast:
            raise EvidenceError("forecast available before observation")
        if self.valid_until is not None and aware_utc(self.valid_until, "valid_until") <= available:
            raise EvidenceError("forecast expiry must follow availability")
        for field in ("contributor", "revision_id", "source_ref"):
            required_text(getattr(self, field), field)


def _same_observation_basis(left: MetricBasis, right: MetricBasis) -> bool:
    return left == right


def _same_reported_change_basis(left: MetricBasis, right: MetricBasis) -> bool:
    if left.comparison_key != right.comparison_key:
        return False
    # Quarterly and annual comparisons can tolerate ordinary calendar-length drift,
    # but not a 3M-vs-9M or 3M-vs-12M mismatch.
    tolerance = 7 if left.period_role.upper() in {"QUARTER", "QUARTERLY", "THREE_MONTHS"} else 15
    return abs(left.days - right.days) <= tolerance


def reported_change(
    current: Actual,
    prior: Actual,
    *,
    decision_at: str,
) -> dict[str, Any]:
    """Comparable current-versus-prior reported change.

    This is a factual operating change, not an expectation surprise.  Both source
    observations must already be lawful and comparable under their native owner.
    """
    if not isinstance(current, Actual) or not isinstance(prior, Actual):
        raise EvidenceError("actual observations required")
    decision = aware_utc(decision_at, "decision_at")
    if aware_utc(current.available_at) > decision or aware_utc(prior.available_at) > decision:
        raise EvidenceError("reported observation unavailable at decision")
    if not _same_reported_change_basis(current.basis, prior.basis):
        raise EvidenceError("reported-change basis mismatch")
    # Same-period revisions are correction evidence, not time-series growth.
    # Comparative values can share one release/availability clock, but their
    # reporting intervals must still be chronological and disjoint.
    if date.fromisoformat(current.basis.period_start) <= date.fromisoformat(prior.basis.period_end):
        raise EvidenceError("reported-change periods must be nonoverlapping and chronological")
    now = float(current.value)
    before = float(prior.value)
    diff = now - before
    if not isfinite(diff):
        raise EvidenceError("reported-change difference overflow")
    pct = None if before == 0 else diff / abs(before)
    if pct is not None and not isfinite(pct):
        pct = None
    if pct is not None and not isfinite(pct * 100.0):
        raise EvidenceError("reported-change percent overflow")
    return {
        "schema": SCHEMA,
        "kind": "COMPARABLE_REPORTED_CHANGE",
        "issuer_id": current.basis.issuer_id,
        "issuer_name": current.basis.issuer_name,
        "metric": current.basis.metric,
        "period_role": current.basis.period_role,
        "current_fiscal_period": current.basis.fiscal_period,
        "prior_fiscal_period": prior.basis.fiscal_period,
        "current_value": now,
        "prior_value": before,
        "signed_difference": diff,
        "change_fraction": pct,
        "change_pct": None if pct is None else pct * 100.0,
        "current_source_ref": current.source_ref,
        "prior_source_ref": prior.source_ref,
        "current_event_id": current.event_id,
        "prior_event_id": prior.event_id,
        "current_available_at": current.available_at,
        "prior_available_at": prior.available_at,
        "decision_at": decision_at,
        "rank_authority": False,
        "entry_authority": False,
    }


def surprise(
    actual: Actual,
    expected: Expectation | None,
    *,
    decision_at: str,
    calibration: Sequence[HistoricalForecastError] = (),
    calibration_key: str | None = None,
    min_history: int = 4,
    error_window: int = 12,
) -> dict[str, Any]:
    """Signed expectation surprise with past-only optional error scaling."""
    if not isinstance(actual, Actual):
        raise EvidenceError("actual observation required")
    if expected is not None and not isinstance(expected, Expectation):
        raise EvidenceError("expectation object required")
    decision = aware_utc(decision_at, "decision_at")
    if aware_utc(actual.available_at) > decision:
        raise EvidenceError("actual unavailable at decision")
    if not isinstance(min_history, int) or isinstance(min_history, bool) or min_history < 2:
        raise EvidenceError("invalid min_history")
    if not isinstance(error_window, int) or isinstance(error_window, bool) or error_window < min_history:
        raise EvidenceError("invalid error_window")

    base = {
        "schema": SCHEMA,
        "kind": "EXPECTATION_SURPRISE",
        "basis": asdict(actual.basis),
        "event_id": actual.event_id,
        "actual": float(actual.value),
        "actual_source_ref": actual.source_ref,
        "actual_available_at": actual.available_at,
        "decision_at": decision_at,
        "rank_authority": False,
        "entry_authority": False,
    }
    if expected is None:
        return {
            **base,
            "status": "EXPECTATION_UNAVAILABLE",
            "expectation_kind": None,
            "signed_difference": None,
            "direction_vs_expectation": None,
            "standardized": None,
            "analyst_consensus_beat": None,
            "reasons": ["no qualified pre-release expectation"],
        }
    if not _same_observation_basis(actual.basis, expected.basis):
        raise EvidenceError("expectation basis mismatch")
    if aware_utc(expected.forecast_at) >= aware_utc(actual.public_at):
        raise EvidenceError("expectation observed at or after release")
    if aware_utc(expected.available_at) >= aware_utc(actual.public_at):
        raise EvidenceError("expectation unavailable strictly before release")

    diff = float(actual.value) - float(expected.value)
    if not isfinite(diff):
        raise EvidenceError("surprise difference overflow")
    direction = "ABOVE" if diff > 0 else "BELOW" if diff < 0 else "IN_LINE"

    valid: list[HistoricalForecastError] = []
    excluded: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in calibration:
        if not isinstance(item, HistoricalForecastError):
            raise EvidenceError("invalid calibration row")
        if item.event_id in seen:
            raise EvidenceError("duplicate calibration event")
        seen.add(item.event_id)
        reason = None
        if item.event_id == actual.event_id:
            reason = "current_event"
        elif aware_utc(item.available_at) >= aware_utc(actual.public_at):
            reason = "unavailable_before_event"
        elif item.expectation_kind != expected.kind:
            reason = "expectation_method_mismatch"
        elif calibration_key is None or item.calibration_key != calibration_key:
            reason = "calibration_scope_mismatch"
        if reason is None:
            valid.append(item)
        else:
            excluded.append({"event_id": item.event_id, "reason": reason})
    valid.sort(key=lambda row: (aware_utc(row.available_at), row.event_id))
    used = valid[-error_window:]
    sigma = stdev([float(row.error) for row in used]) if len(used) >= min_history else None
    if sigma is not None and (not isfinite(sigma) or sigma <= 0):
        sigma = None
    standardized = diff / sigma if sigma else None
    if standardized is not None and not isfinite(standardized):
        standardized = None

    return {
        **base,
        "status": "COMPARABLE",
        "expectation_kind": expected.kind,
        "expectation": float(expected.value),
        "expectation_source_ref": expected.source_ref,
        "expectation_available_at": expected.available_at,
        "signed_difference": diff,
        "direction_vs_expectation": direction,
        "analyst_consensus_beat": (diff > 0 if expected.kind == "ANALYST_CONSENSUS"
                                   and actual.basis.metric in HIGHER_IS_IMPROVEMENT_METRICS else None),
        "percent_beat": None,
        "percent_reason": "absolute difference plus past-only error scaling; no unstable denominator",
        "standardized": standardized,
        "scaling_std": sigma,
        "calibration_count": len(used),
        "calibration_event_ids": [row.event_id for row in used],
        "excluded_calibration": excluded,
        "calibration_reason": None if standardized is not None else "insufficient_or_zero_variance_pre_event_errors",
    }


def matched_revisions(
    rows: Iterable[Forecast],
    *,
    basis: MetricBasis,
    before: str,
    after: str,
) -> dict[str, Any]:
    """Compare fixed contributors for the same forecast basis at two usable-time cuts."""
    first = aware_utc(before, "before")
    second = aware_utc(after, "after")
    if first >= second:
        raise EvidenceError("non-increasing revision window")
    records = tuple(rows)
    if any(not isinstance(row, Forecast) for row in records):
        raise EvidenceError("invalid forecast row")
    ids = [row.revision_id for row in records]
    if len(ids) != len(set(ids)):
        raise EvidenceError("duplicate revision id")

    def select(cut: datetime) -> dict[str, Forecast]:
        grouped: dict[str, list[Forecast]] = {}
        for row in records:
            if row.basis != basis or aware_utc(row.available_at) > cut:
                continue
            grouped.setdefault(row.contributor, []).append(row)
        chosen: dict[str, Forecast] = {}
        for contributor, group in grouped.items():
            key = lambda row: (aware_utc(row.forecast_at), aware_utc(row.available_at))
            newest = max(key(row) for row in group)
            tied = [row for row in group if key(row) == newest]
            semantics = {(row.state, finite(row.value), row.valid_until) for row in tied}
            if len(semantics) != 1:
                raise EvidenceError("ambiguous equal-time forecast values")
            row = min(tied, key=lambda item: item.revision_id)
            if row.state == "WITHDRAWN":
                continue
            if row.valid_until is not None and cut >= aware_utc(row.valid_until):
                continue
            chosen[contributor] = row
        return chosen

    left, right = select(first), select(second)
    names = sorted(left.keys() & right.keys())
    delta = [float(right[name].value) - float(left[name].value) for name in names]
    if any(not isfinite(value) for value in delta):
        raise EvidenceError("revision difference overflow")
    naive = (
        mean(float(row.value) for row in right.values()) - mean(float(row.value) for row in left.values())
        if left and right
        else None
    )
    matched_mean = mean(delta) if delta else None
    # statistics.median's even case adds the middle values before halving.
    # mean uses exact accumulation, avoiding an infinite intermediate sum.
    ordered = sorted(delta)
    count = len(ordered)
    matched_median = mean(ordered[(count - 1) // 2:count // 2 + 1]) if count else None
    residual = naive - matched_mean if naive is not None and matched_mean is not None else None
    if any(value is not None and not isfinite(value)
           for value in (naive, matched_mean, matched_median, residual)):
        raise EvidenceError("revision aggregate overflow")
    return {
        "schema": SCHEMA,
        "kind": "FIXED_CONTRIBUTOR_FIXED_PERIOD_REVISION",
        "basis": asdict(basis),
        "before": before,
        "after": after,
        "before_count": len(left),
        "after_count": len(right),
        "matched_count": len(names),
        "entered": sorted(right.keys() - left.keys()),
        "exited": sorted(left.keys() - right.keys()),
        "matched_mean_change": matched_mean,
        "matched_median_change": matched_median,
        "upward_share": sum(value > 0 for value in delta) / len(delta) if delta else None,
        "naive_changing_roster_mean_change": naive,
        "roster_difference_residual": residual,
        "pairs": [
            {
                "contributor": name,
                "before_revision": left[name].revision_id,
                "after_revision": right[name].revision_id,
                "difference": value,
            }
            for name, value in zip(names, delta)
        ],
        "rank_authority": False,
    }


def per_share_bridge(
    *,
    old_income: float,
    new_income: float,
    old_shares: float,
    new_shares: float,
) -> dict[str, Any]:
    """Exact arithmetic decomposition, not causal attribution."""
    values = [finite(value) for value in (old_income, new_income, old_shares, new_shares)]
    if any(value is None for value in values):
        raise EvidenceError("finite income and share values required")
    income0, income1, shares0, shares1 = values
    assert income0 is not None and income1 is not None and shares0 is not None and shares1 is not None
    if shares0 <= 0 or shares1 <= 0:
        raise EvidenceError("strictly positive diluted shares required")
    eps0, eps1 = income0 / shares0, income1 / shares1
    income_effect = (income1 - income0) / shares0
    share_effect = income1 / shares1 - income1 / shares0
    if not all(isfinite(value) for value in (eps0, eps1, income_effect, share_effect)):
        raise EvidenceError("per-share bridge overflow")
    return {
        "schema": SCHEMA,
        "kind": "PER_SHARE_BRIDGE",
        "old_eps": eps0,
        "new_eps": eps1,
        "eps_change": eps1 - eps0,
        "income_effect_at_old_share_count": income_effect,
        "share_count_effect_at_new_income": share_effect,
        "decomposition_order": "income_then_share_count",
        "not_causal_attribution": True,
        "income_grew": income1 > income0,
        "eps_grew": eps1 > eps0,
        "share_count_grew": shares1 > shares0,
        "rank_authority": False,
    }


def entry_economics(
    *,
    price: float,
    target: float,
    stop: float,
    win_cost: float,
    loss_cost: float,
    required_reward_risk: float,
) -> dict[str, Any]:
    """Scenario arithmetic at the current price; never an estimated win probability."""
    values = [finite(value) for value in (price, target, stop, win_cost, loss_cost, required_reward_risk)]
    if any(value is None for value in values):
        raise EvidenceError("non-finite entry scenario")
    p, target_value, stop_value, win_fee, loss_fee, ratio = values
    assert all(value is not None for value in values)
    if not (0 < stop_value < p < target_value):
        raise EvidenceError("invalid long scenario geometry")
    if min(win_fee, loss_fee) < 0 or ratio <= 0:
        raise EvidenceError("invalid cost or reward/risk requirement")
    upside = target_value - p - win_fee
    loss = p - stop_value + loss_fee
    if upside <= 0 or not all(isfinite(value) for value in (upside, loss)):
        raise EvidenceError("non-positive net scenario upside")
    ceiling = (target_value - win_fee) / (1 + ratio) + (ratio / (1 + ratio)) * (stop_value - loss_fee)
    return {
        "schema": SCHEMA,
        "kind": "ENTRY_ECONOMICS",
        "net_upside": upside,
        "scenario_loss": loss,
        "net_reward_risk": upside / loss,
        "break_even_target_probability": loss / (upside + loss),
        "price_ceiling_for_required_reward_risk": ceiling,
        "within_scenario_ceiling": p <= ceiling,
        "estimated_win_probability": None,
        "entry_permission": False,
        "assumed_stop_execution_not_guaranteed": True,
    }


def joint_earnings_state(eps: Mapping[str, Any], revenue: Mapping[str, Any]) -> dict[str, Any]:
    """Describe EPS/revenue agreement without converting it to a confidence bonus."""
    if eps.get("status") != "COMPARABLE" or revenue.get("status") != "COMPARABLE":
        return {
            "schema": SCHEMA,
            "state": "INCOMPLETE",
            "rank_authority": False,
            "reason": "both qualified expectation comparisons required",
        }
    eps_basis = eps.get("basis", {})
    rev_basis = revenue.get("basis", {})
    if eps_basis.get("metric") != "EPS" or rev_basis.get("metric") != "revenue":
        raise EvidenceError("joint evidence requires EPS and revenue")
    if eps.get("expectation_kind") != revenue.get("expectation_kind"):
        raise EvidenceError("different expectation methods are not one corroboration")
    identity_fields = ("issuer_id", "fiscal_period", "period_start", "period_end", "currency", "accounting_basis")
    if eps.get("event_id") != revenue.get("event_id"):
        raise EvidenceError("different earnings events")
    if any(eps_basis.get(field) != rev_basis.get(field) for field in identity_fields):
        raise EvidenceError("different issuer, period, currency or accounting basis")
    if eps.get("decision_at") != revenue.get("decision_at"):
        raise EvidenceError("different decision snapshots")
    eps_diff = finite(eps.get("signed_difference"))
    revenue_diff = finite(revenue.get("signed_difference"))
    if eps_diff is None or revenue_diff is None:
        raise EvidenceError("invalid comparable differences")

    def sign(value: float) -> str:
        return "ABOVE" if value > 0 else "BELOW" if value < 0 else "IN_LINE"

    return {
        "schema": SCHEMA,
        "state": f"EPS_{sign(eps_diff)}_REVENUE_{sign(revenue_diff)}",
        "expectation_kind": eps["expectation_kind"],
        "event_id": eps["event_id"],
        "both_positive": eps_diff > 0 and revenue_diff > 0,
        "rank_authority": False,
        "not_causal_profit_attribution": True,
    }


def factual_dossier(
    *,
    event_id: str,
    issuer_id: str,
    decision_at: str,
    reported_changes: Sequence[Mapping[str, Any]] = (),
    surprises: Sequence[Mapping[str, Any]] = (),
    revisions: Sequence[Mapping[str, Any]] = (),
    per_share: Mapping[str, Any] | None = None,
    entry: Mapping[str, Any] | None = None,
    source_contract_refs: Sequence[str] = (),
    guidance_results: Sequence[Mapping[str, Any]] = (),
    guidance_updates: Sequence[Mapping[str, Any]] = (),
    profit_bridges: Sequence[Mapping[str, Any]] = (),
    valuation_case: Mapping[str, Any] | None = None,
    cash_flows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Assemble factual evidence while preserving every downstream authority boundary."""
    required_text(event_id, "event_id")
    required_text(issuer_id, "issuer_id")
    aware_utc(decision_at, "decision_at")
    refs = [required_text(ref, "source_contract_ref") for ref in source_contract_refs]
    if not refs:
        raise EvidenceError("at least one source contract reference required")
    if len(refs) != len(set(refs)):
        raise EvidenceError("duplicate source contract reference")

    decision = aware_utc(decision_at, "decision_at")

    def no_child_authority(item: Mapping[str, Any]) -> None:
        for field in (
            "rank_authority", "entry_authority", "policy_authority",
            "sizing_authority", "trade_authority", "entry_permission",
        ):
            if item.get(field) is True:
                raise EvidenceError("authoritative child cannot enter factual dossier")

    for item in reported_changes:
        if not isinstance(item, Mapping):
            raise EvidenceError("dossier evidence must be mappings")
        if item.get("schema") != SCHEMA or item.get("kind") != "COMPARABLE_REPORTED_CHANGE":
            raise EvidenceError("invalid reported-change evidence")
        if item.get("issuer_id") != issuer_id or item.get("current_event_id") != event_id:
            raise EvidenceError("reported-change identity mismatch")
        if aware_utc(str(item.get("decision_at")), "reported-change decision_at") > decision:
            raise EvidenceError("reported-change evidence is from the future")
        no_child_authority(item)

    for item in surprises:
        if not isinstance(item, Mapping):
            raise EvidenceError("dossier evidence must be mappings")
        if item.get("schema") != SCHEMA or item.get("kind") != "EXPECTATION_SURPRISE":
            raise EvidenceError("invalid surprise evidence")
        basis = item.get("basis")
        if not isinstance(basis, Mapping) or basis.get("issuer_id") != issuer_id or item.get("event_id") != event_id:
            raise EvidenceError("surprise identity mismatch")
        if aware_utc(str(item.get("decision_at")), "surprise decision_at") > decision:
            raise EvidenceError("surprise evidence is from the future")
        no_child_authority(item)

    for item in revisions:
        if not isinstance(item, Mapping):
            raise EvidenceError("dossier evidence must be mappings")
        if item.get("schema") != SCHEMA or item.get("kind") != "FIXED_CONTRIBUTOR_FIXED_PERIOD_REVISION":
            raise EvidenceError("invalid revision evidence")
        basis = item.get("basis")
        if not isinstance(basis, Mapping) or basis.get("issuer_id") != issuer_id:
            raise EvidenceError("revision identity mismatch")
        if aware_utc(str(item.get("after")), "revision after") > decision:
            raise EvidenceError("revision evidence is from the future")
        no_child_authority(item)

    for item in guidance_results:
        if not isinstance(item, Mapping) or item.get("schema") != SCHEMA or item.get("kind") != "ISSUER_GUIDANCE_DELIVERY":
            raise EvidenceError("invalid issuer-guidance evidence")
        basis = item.get("basis")
        if not isinstance(basis, Mapping) or basis.get("issuer_id") != issuer_id or item.get("event_id") != event_id:
            raise EvidenceError("guidance evidence identity mismatch")
        if aware_utc(str(item.get("decision_at"))) > decision:
            raise EvidenceError("guidance evidence is from the future")
        no_child_authority(item)

    for item in guidance_updates:
        if (not isinstance(item, Mapping) or item.get("schema") != SCHEMA
                or item.get("kind") != "ISSUER_GUIDANCE_CHANGE"):
            raise EvidenceError("invalid issuer-guidance update")
        basis = item.get("basis")
        if not isinstance(basis, Mapping) or basis.get("issuer_id") != issuer_id:
            raise EvidenceError("guidance update identity mismatch")
        if (aware_utc(str(item.get("decision_at"))) > decision
                or aware_utc(str(item.get("current_available_at"))) > decision):
            raise EvidenceError("guidance update is from the future")
        if item.get("actual_result_used") is not False:
            raise EvidenceError("guidance update cannot use future actual result")
        no_child_authority(item)

    for item in profit_bridges:
        if (not isinstance(item, Mapping) or item.get("schema") != SCHEMA
                or item.get("kind") != "COMPARABLE_PROFITABILITY_BRIDGE"):
            raise EvidenceError("invalid profitability bridge")
        if item.get("issuer_id") != issuer_id or item.get("current_event_id") != event_id:
            raise EvidenceError("profitability bridge identity mismatch")
        if aware_utc(str(item.get("decision_at"))) > decision:
            raise EvidenceError("profitability bridge is from the future")
        no_child_authority(item)

    for cash in cash_flows:
        _validate_cash_flow_case(cash,issuer_id=issuer_id,event_id=event_id,decision_at=decision_at)

    if per_share is not None:
        if not isinstance(per_share, Mapping) or per_share.get("schema") != SCHEMA or per_share.get("kind") != "PER_SHARE_BRIDGE":
            raise EvidenceError("invalid per-share evidence")
        no_child_authority(per_share)
    if entry is not None:
        if not isinstance(entry, Mapping) or entry.get("schema") != SCHEMA or entry.get("kind") != "ENTRY_ECONOMICS":
            raise EvidenceError("invalid entry evidence")
        no_child_authority(entry)

    if valuation_case is not None:
        _validate_valuation_case(valuation_case, issuer_id=issuer_id,
                                 event_id=event_id, decision_at=decision_at)

    limitations: list[str] = []
    if not reported_changes:
        limitations.append("no comparable reported change")
    if not surprises:
        limitations.append("no qualified pre-release expectation surprise")
    if entry is None:
        limitations.append("no price-sensitive entry scenario")
    return {
        "schema": "prophet.earnings_dossier/v1",
        "event_id": event_id,
        "issuer_id": issuer_id,
        "decision_at": decision_at,
        "reported_changes": [deepcopy(dict(item)) for item in reported_changes],
        "expectation_surprises": [deepcopy(dict(item)) for item in surprises],
        "matched_revisions": [deepcopy(dict(item)) for item in revisions],
        "per_share_bridge": None if per_share is None else deepcopy(dict(per_share)),
        "entry_economics": None if entry is None else deepcopy(dict(entry)),
        "source_contract_refs": refs,
        **({"valuation_scenario": deepcopy(dict(valuation_case))} if valuation_case is not None else {}),
        **({"issuer_guidance_delivery": [deepcopy(dict(item)) for item in guidance_results]}
           if guidance_results else {}),
        **({"issuer_guidance_updates": [deepcopy(dict(item)) for item in guidance_updates]}
           if guidance_updates else {}),
        **({"profitability_bridges": [deepcopy(dict(item)) for item in profit_bridges]}
           if profit_bridges else {}),
        **({"cash_flow_reconciliations":[deepcopy(dict(item)) for item in cash_flows]} if cash_flows else {}),
        "limitations": limitations,
        "authority": {
            "rank": False,
            "entry": False,
            "size": False,
            "execution": False,
            "trade": False,
        },
    }



@dataclass(frozen=True)
class IssuerGuidance:
    """One source-qualified management forecast revision, not analyst consensus.

    Its range is management's stated interval, NOT a confidence interval. The
    existing source owner supplies comparable basis, clocks and history coverage.
    """
    basis: MetricBasis
    low: float | None
    high: float | None
    public_at: str
    available_at: str
    revision_id: str
    source_ref: str
    state: str = "ACTIVE"
    valid_until: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MetricBasis):
            raise EvidenceError("invalid guidance basis")
        if self.state not in {"ACTIVE", "WITHDRAWN"}:
            raise EvidenceError("invalid guidance state")
        if self.state == "ACTIVE":
            low, high = finite(self.low), finite(self.high)
            if low is None or high is None or low > high:
                raise EvidenceError("invalid guidance range")
        elif self.low is not None or self.high is not None:
            raise EvidenceError("withdrawn guidance must not retain a numeric range")
        issued = aware_utc(self.public_at, "guidance public_at")
        available = aware_utc(self.available_at, "guidance available_at")
        if available < issued:
            raise EvidenceError("guidance available before publication")
        if self.valid_until is not None and aware_utc(self.valid_until) <= available:
            raise EvidenceError("guidance validity must follow availability")
        required_text(self.revision_id, "guidance revision_id")
        required_text(self.source_ref, "guidance source_ref")


def guidance_delivery(
    actual: Actual, revisions: Sequence[IssuerGuidance], *, decision_at: str,
    source_history_complete: bool,
) -> dict[str, Any]:
    """Compare the actual with the latest comparable pre-release issuer guidance.

    Initial-to-latest guidance change is earlier information; only the residual
    against the latest qualified forecast belongs to the eventual results event.
    A later withdrawal/expiry never falls back to an older optimistic forecast.
    Incomplete history cannot certify that the retained record was the latest.
    """
    if not isinstance(actual, Actual) or not isinstance(source_history_complete, bool):
        raise EvidenceError("actual and explicit guidance history state required")
    decision = aware_utc(decision_at, "decision_at")
    event_cut = aware_utc(actual.public_at)
    if aware_utc(actual.available_at) > decision:
        raise EvidenceError("actual unavailable at guidance-delivery decision")
    rows = tuple(revisions)
    if any(not isinstance(row, IssuerGuidance) for row in rows):
        raise EvidenceError("invalid guidance revision")
    if len({row.revision_id for row in rows}) != len(rows):
        raise EvidenceError("duplicate guidance revision")
    visible = []
    excluded = []
    for row in rows:
        reason = None
        if row.basis != actual.basis:
            reason = "incomparable_basis_or_period"
        elif aware_utc(row.public_at) >= event_cut:
            reason = "published_at_or_after_result"
        elif aware_utc(row.available_at) >= event_cut:
            reason = "not_usable_before_result"
        if reason is None:
            visible.append(row)
        else:
            excluded.append({"revision_id": row.revision_id, "reason": reason})
    visible.sort(key=lambda row: (aware_utc(row.public_at), aware_utc(row.available_at), row.revision_id))
    result = {
        "schema": SCHEMA, "kind": "ISSUER_GUIDANCE_DELIVERY",
        "basis": asdict(actual.basis), "event_id": actual.event_id,
        "actual": float(actual.value), "actual_source_ref": actual.source_ref,
        "actual_public_at": actual.public_at, "actual_available_at": actual.available_at,
        "decision_at": decision_at,
        "history_scope": "COMPLETE_FOR_METRIC_PERIOD" if source_history_complete else "INCOMPLETE",
        "visible_revision_ids": [row.revision_id for row in visible],
        "excluded_revisions": excluded,
        "selected_revision_id": None, "selected_source_ref": None,
        "latest_range": None, "range_position": None,
        "signed_gap_to_latest_midpoint": None, "distance_outside_latest_range": None,
        "initial_to_latest_midpoint_change": None, "earlier_revision_public_at": None,
        "initial_guidance_midpoint": None, "signed_gap_to_initial_midpoint": None,
        "analyst_consensus_beat": None, "estimated_return": None,
        "range_interpretation": "ISSUER_STATED_RANGE_NOT_PROBABILITY_INTERVAL",
        "rank_authority": False, "entry_authority": False,
    }
    if not source_history_complete:
        return {**result, "status": "GUIDANCE_HISTORY_UNAVAILABLE"}
    if not visible:
        return {**result, "status": "GUIDANCE_UNAVAILABLE"}
    newest_public = max(aware_utc(row.public_at) for row in visible)
    tied = [row for row in visible if aware_utc(row.public_at) == newest_public]
    signatures = {(row.state, finite(row.low), finite(row.high), row.valid_until) for row in tied}
    if len(signatures) != 1:
        raise EvidenceError("ambiguous equal-publication guidance")
    latest = max(tied, key=lambda row: (aware_utc(row.available_at), row.revision_id))
    result.update(selected_revision_id=latest.revision_id, selected_source_ref=latest.source_ref)
    if latest.state == "WITHDRAWN":
        return {**result, "status": "GUIDANCE_WITHDRAWN"}
    if latest.valid_until is not None and event_cut >= aware_utc(latest.valid_until):
        return {**result, "status": "GUIDANCE_EXPIRED"}
    low, high = float(latest.low), float(latest.high)
    midpoint = low / 2 + high / 2
    value = float(actual.value)
    diff = value - midpoint
    distance = value - high if value > high else value - low if value < low else 0.0
    if not isfinite(diff) or not isfinite(distance):
        raise EvidenceError("guidance arithmetic overflow")
    result.update(status="COMPARABLE_TO_ISSUER_GUIDANCE",
        latest_range={"low": low, "midpoint": midpoint, "high": high},
        range_position="ABOVE_RANGE" if value > high else "BELOW_RANGE" if value < low else "WITHIN_RANGE",
        signed_gap_to_latest_midpoint=diff, distance_outside_latest_range=distance)
    # The earlier-change decomposition is withheld across a withdrawal/restart;
    # do not present a broken forecasting episode as one continuous promise.
    if all(row.state == "ACTIVE" for row in visible):
        oldest_public = min(aware_utc(row.public_at) for row in visible)
        firsts = [row for row in visible if aware_utc(row.public_at) == oldest_public]
        signatures = {(finite(row.low), finite(row.high), row.valid_until) for row in firsts}
        if len(signatures) == 1:
            first = min(firsts, key=lambda row: (aware_utc(row.available_at), row.revision_id))
            initial = float(first.low) / 2 + float(first.high) / 2
            earlier = midpoint - initial
            total = value - initial
            if not all(isfinite(x) for x in (earlier, total)):
                raise EvidenceError("guidance decomposition overflow")
            result.update(initial_guidance_midpoint=initial,
                signed_gap_to_initial_midpoint=total,
                initial_to_latest_midpoint_change=earlier,
                earlier_revision_public_at=latest.public_at)
    return result



def guidance_change(
    previous: IssuerGuidance, current: IssuerGuidance, *,
    decision_at: str, source_pair_is_adjacent: bool,
) -> dict[str, Any]:
    """A source-known forecast change BEFORE the eventual results are available.

    No actual result is an input. The source owner must qualify the adjacent
    revision pair; nonadjacent records cannot stand in for the latest change.
    Midpoint movement and range uncertainty are distinct observations.
    """
    if not isinstance(previous, IssuerGuidance) or not isinstance(current, IssuerGuidance):
        raise EvidenceError("issuer guidance pair required")
    if not isinstance(source_pair_is_adjacent, bool):
        raise EvidenceError("explicit adjacent guidance-pair state required")
    if previous.basis != current.basis:
        raise EvidenceError("guidance revision basis mismatch")
    decision = aware_utc(decision_at)
    if aware_utc(previous.public_at) >= aware_utc(current.public_at):
        raise EvidenceError("guidance revision publication order invalid")
    if max(aware_utc(previous.available_at), aware_utc(current.available_at)) > decision:
        raise EvidenceError("guidance revision unavailable at decision")
    result = {
        "schema": SCHEMA, "kind": "ISSUER_GUIDANCE_CHANGE",
        "basis": asdict(current.basis), "previous_revision_id": previous.revision_id,
        "current_revision_id": current.revision_id,
        "previous_source_ref": previous.source_ref, "current_source_ref": current.source_ref,
        "current_public_at": current.public_at, "current_available_at": current.available_at,
        "decision_at": decision_at, "actual_result_used": False,
        "midpoint_change": None, "lower_bound_change": None, "upper_bound_change": None,
        "width_change": None, "interval_relationship": None,
        "consensus_revision": None, "return_forecast": None,
        "rank_authority": False, "entry_authority": False,
    }
    if not source_pair_is_adjacent:
        return {**result, "status": "ADJACENT_REVISION_PAIR_UNAVAILABLE"}
    if current.state == "WITHDRAWN":
        return {**result, "status": "GUIDANCE_WITHDRAWN"}
    if current.valid_until is not None and decision >= aware_utc(current.valid_until):
        return {**result, "status": "GUIDANCE_EXPIRED"}
    if previous.state == "WITHDRAWN" or (
        previous.valid_until is not None and aware_utc(current.public_at) >= aware_utc(previous.valid_until)
    ):
        return {**result, "status": "GUIDANCE_REINTRODUCED_NO_CONTINUOUS_COMPARISON"}
    pl, ph = float(previous.low), float(previous.high)
    cl, ch = float(current.low), float(current.high)
    lower, upper = cl - pl, ch - ph
    midpoint = (cl / 2 + ch / 2) - (pl / 2 + ph / 2)
    width = (ch - cl) - (ph - pl)
    if not all(isfinite(x) for x in [lower, upper, midpoint, width]):
        raise EvidenceError("guidance revision arithmetic overflow")
    relationship = (
        "ENTIRE_RANGE_ABOVE_PREVIOUS" if cl > ph else
        "ENTIRE_RANGE_BELOW_PREVIOUS" if ch < pl else
        "UNCHANGED_RANGE" if cl == pl and ch == ph else
        "BOTH_BOUNDS_RAISED" if lower > 0 and upper > 0 else
        "BOTH_BOUNDS_LOWERED" if lower < 0 and upper < 0 else
        "OVERLAPPING_MIXED_BOUND_CHANGE"
    )
    return {**result, "status": "COMPARABLE_ISSUER_OUTLOOK_CHANGE",
            "previous_range": {"low": pl, "midpoint": pl / 2 + ph / 2, "high": ph},
            "current_range": {"low": cl, "midpoint": cl / 2 + ch / 2, "high": ch},
            "midpoint_change": midpoint, "lower_bound_change": lower,
            "upper_bound_change": upper, "width_change": width,
            "interval_relationship": relationship}



def earnings_evidence_brief(dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Bounded, deterministic explanation of the existing factual dossier.

    No weights, votes, confidence probability or buy permission are inferred.
    The same evidence can support an operating improvement while contradicting
    per-share improvement or an attractive entry at the supplied scenario price.
    References address the input dossier; this neither fetches nor authenticates
    documents and creates no second source or signal owner.
    """
    if (not isinstance(dossier, Mapping)
            or dossier.get("schema") != "prophet.earnings_dossier/v1"):
        raise EvidenceError("earnings dossier required")
    authority = dossier.get("authority")
    if (not isinstance(authority, Mapping) or not authority
            or any(value is not False for value in authority.values())):
        raise EvidenceError("brief cannot promote authoritative dossier")
    decision = aware_utc(dossier.get("decision_at"), "dossier decision_at")
    issuer = required_text(dossier.get("issuer_id"), "dossier issuer_id")
    event = required_text(dossier.get("event_id"), "dossier event_id")
    facts: list[dict[str, Any]] = []
    counters: list[dict[str, Any]] = []
    context: list[dict[str, Any]] = []
    higher_is_improvement = HIGHER_IS_IMPROVEMENT_METRICS

    def direction_bucket(metric: str, direction: float):
        if metric not in higher_is_improvement:
            missing.append("DIRECTION_FOR_UNSUPPORTED_METRIC")
            return context
        return counters if direction < 0 else facts if direction > 0 else context
    missing: list[str] = []

    def item(code: str, text: str, ref: str, values: Mapping[str, Any] | None = None):
        return {"code": code, "text": text, "evidence_ref": ref,
                "values": deepcopy(dict(values or {}))}

    def number(value: Any, label: str) -> float:
        out = finite(value)
        if out is None:
            raise EvidenceError("brief has invalid " + label)
        return out

    def rows(key: str) -> list[Mapping[str, Any]]:
        value = dossier.get(key, [])
        if not isinstance(value, (list, tuple)) or len(value) > 128:
            raise EvidenceError("brief evidence population invalid")
        if any(not isinstance(row, Mapping) for row in value):
            raise EvidenceError("brief evidence must be mappings")
        return list(value)

    for index, change in enumerate(rows("reported_changes")):
        if (change.get("issuer_id") != issuer or change.get("current_event_id") != event
                or aware_utc(change.get("decision_at")) > decision):
            raise EvidenceError("brief reported change identity or clock mismatch")
        ref = f"reported_changes[{index}]"
        metric = str(change.get("metric") or "reported measure")
        diff = number(change.get("signed_difference"), "reported difference")
        pct = finite(change.get("change_pct"))
        # A positive comparison is an operating fact, not a positive stock forecast.
        verb = "rose" if diff > 0 else "fell" if diff < 0 else "was unchanged"
        label = "Revenue" if metric in {"revenue", "total_net_sales"} else "Reported measure"
        magnitude = f" {abs(pct):.1f}%" if pct is not None and diff != 0 else ""
        entry = item("REPORTED_INCREASE" if diff > 0 else "REPORTED_DECREASE" if diff < 0 else "REPORTED_UNCHANGED",
                     f"{label} {verb}{magnitude} against the comparable period.", ref,
                     {"metric": metric, "change_pct": pct, "signed_difference": diff})
        direction_bucket(metric, diff).append(entry)
    if not rows("reported_changes"):
        missing.append("COMPARABLE_OPERATING_CHANGE")

    comparable = []
    for index, surprise_row in enumerate(rows("expectation_surprises")):
        if surprise_row.get("status") != "COMPARABLE":
            continue
        basis = surprise_row.get("basis", {})
        if (basis.get("issuer_id") != issuer or surprise_row.get("event_id") != event
                or aware_utc(surprise_row.get("decision_at")) > decision):
            raise EvidenceError("brief surprise identity or clock mismatch")
        diff = number(surprise_row.get("signed_difference"), "surprise difference")
        kind = surprise_row.get("expectation_kind")
        if kind not in EXPECTATION_KINDS:
            raise EvidenceError("brief expectation kind invalid")
        metric = str(basis.get("metric") or "measure")
        noun = "analyst expectation" if kind == "ANALYST_CONSENSUS" else "seasonal-model expectation"
        direction = "above" if diff > 0 else "below" if diff < 0 else "in line with"
        entry = item("ABOVE_EXPECTATION" if diff > 0 else "BELOW_EXPECTATION" if diff < 0 else "IN_LINE_EXPECTATION",
                     f"{metric} was {direction} the comparable pre-release {noun}.",
                     f"expectation_surprises[{index}]", {"expectation_kind": kind, "signed_difference": diff})
        direction_bucket(metric, diff).append(entry)
        comparable.append(surprise_row)
    if not comparable:
        missing.append("QUALIFIED_PRE_RELEASE_EXPECTATION")
    if not any(row.get("expectation_kind") == "ANALYST_CONSENSUS" for row in comparable):
        missing.append("ANALYST_CONSENSUS_COMPARISON")
    if not any(row.get("matched_count", 0) for row in rows("matched_revisions")):
        missing.append("MATCHED_CONTRIBUTOR_REVISIONS")
    if not rows("profitability_bridges"):
        missing.append("COMPARABLE_PROFITABILITY")

    for index, revision in enumerate(rows("matched_revisions")):
        if revision.get("basis", {}).get("issuer_id") != issuer or aware_utc(revision.get("after")) > decision:
            raise EvidenceError("brief forecast revision identity or clock mismatch")
        count = revision.get("matched_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise EvidenceError("brief matched count invalid")
        if count == 0:
            missing.append("MATCHED_CONTRIBUTOR_REVISIONS")
            continue
        delta = number(revision.get("matched_mean_change"), "matched revision")
        naive = finite(revision.get("naive_changing_roster_mean_change"))
        text = f"The same {count} contributors {'raised' if delta > 0 else 'lowered' if delta < 0 else 'did not change'} their mean forecast for the same period."
        direction_bucket(str(revision.get("basis", {}).get("metric")), delta).append(item("MATCHED_FORECAST_REVISION", text,
            f"matched_revisions[{index}]", {"matched_count": count, "matched_mean_change": delta}))
        if delta == 0 and naive is not None and naive != 0:
            counters.append(item("ROSTER_CHANGE_NOT_UPGRADE",
                "The aggregate forecast moved, but the matched contributors did not revise; roster change is not an upgrade.",
                f"matched_revisions[{index}]", {"naive_mean_change": naive}))

    for index, change in enumerate(rows("issuer_guidance_updates")):
        if (change.get("basis", {}).get("issuer_id") != issuer
                or aware_utc(change.get("decision_at")) > decision
                or change.get("actual_result_used") is not False):
            raise EvidenceError("brief guidance update identity or clock mismatch")
        ref = f"issuer_guidance_updates[{index}]"
        status = change.get("status")
        if status != "COMPARABLE_ISSUER_OUTLOOK_CHANGE":
            missing.append("CONTINUOUS_COMPARABLE_ISSUER_OUTLOOK")
            continue
        relationship = change.get("interval_relationship")
        labels = {
            "ENTIRE_RANGE_ABOVE_PREVIOUS": "The new issuer outlook range is entirely above the prior range.",
            "ENTIRE_RANGE_BELOW_PREVIOUS": "The new issuer outlook range is entirely below the prior range.",
            "BOTH_BOUNDS_RAISED": "Both bounds of the issuer outlook rose; the ranges still overlap.",
            "BOTH_BOUNDS_LOWERED": "Both bounds of the issuer outlook fell; the ranges still overlap.",
            "UNCHANGED_RANGE": "The issuer outlook range is unchanged.",
            "OVERLAPPING_MIXED_BOUND_CHANGE": "The issuer outlook changed unevenly; a higher midpoint alone does not establish a stronger range.",
        }
        if relationship not in labels:
            raise EvidenceError("brief guidance range relationship invalid")
        is_counter = relationship in {"ENTIRE_RANGE_BELOW_PREVIOUS", "BOTH_BOUNDS_LOWERED", "OVERLAPPING_MIXED_BOUND_CHANGE"}
        guidance_metric = str(change.get("basis", {}).get("metric"))
        target = (counters if is_counter else context if relationship == "UNCHANGED_RANGE" else facts)
        if guidance_metric not in higher_is_improvement:
            missing.append("DIRECTION_FOR_UNSUPPORTED_METRIC")
            target = context
        target.append(item("ISSUER_RANGE_CHANGE", labels[relationship], ref,
            {"interval_relationship": relationship, "midpoint_change": change.get("midpoint_change")}))

    for index, delivered in enumerate(rows("issuer_guidance_delivery")):
        if (delivered.get("basis", {}).get("issuer_id") != issuer or delivered.get("event_id") != event
                or aware_utc(delivered.get("decision_at")) > decision):
            raise EvidenceError("brief guidance delivery identity or clock mismatch")
        if delivered.get("status") != "COMPARABLE_TO_ISSUER_GUIDANCE":
            missing.append("COMPLETE_PRE_RELEASE_ISSUER_GUIDANCE_HISTORY")
            continue
        ref = f"issuer_guidance_delivery[{index}]"
        position = delivered.get("range_position")
        residual = number(delivered.get("signed_gap_to_latest_midpoint"), "guidance residual")
        description = {"ABOVE_RANGE": "above", "WITHIN_RANGE": "within", "BELOW_RANGE": "below"}.get(position)
        if description is None:
            raise EvidenceError("brief guidance range position invalid")
        direction_bucket(str(delivered.get("basis", {}).get("metric")),
                         -1 if position == "BELOW_RANGE" else 1 if position == "ABOVE_RANGE" else 0).append(item("DELIVERY_VS_LATEST_ISSUER_RANGE",
            f"The result was {description} the latest qualified issuer range, not analyst consensus.", ref,
            {"signed_gap_to_latest_midpoint": residual, "range_position": position}))
        earlier = finite(delivered.get("initial_to_latest_midpoint_change"))
        if earlier is not None and earlier != 0:
            counters.append(item("EARLIER_GUIDANCE_ALREADY_KNOWN",
                "Part of the difference from the initial outlook was disclosed before results; do not count that revision again as new earnings information.",
                ref, {"earlier_midpoint_change": earlier, "new_result_residual": residual,
                      "signed_gap_to_initial_midpoint": delivered.get("signed_gap_to_initial_midpoint")}))

    for index, bridge in enumerate(rows("profitability_bridges")):
        if (bridge.get("issuer_id") != issuer or bridge.get("current_event_id") != event
                or aware_utc(bridge.get("decision_at")) > decision):
            raise EvidenceError("brief profitability identity or clock mismatch")
        delta = number(bridge.get("margin_change_bps"), "margin change")
        sales = number(bridge.get("revenue_change_fraction"), "sales change")
        metric = bridge.get("profit_metric")
        name = {"gross_profit": "Gross margin", "operating_income": "Operating margin", "net_income": "Net margin"}.get(metric)
        if name is None:
            raise EvidenceError("brief profit metric invalid")
        ref = f"profitability_bridges[{index}]"
        text = f"{name} {'expanded' if delta > 0 else 'compressed' if delta < 0 else 'was unchanged'}"
        if delta != 0:
            text += f" by {abs(delta):.1f} basis points"
        text += ". Revenue growth and margin improvement are separate facts."
        (counters if delta < 0 else facts).append(item("MARGIN_COMPRESSION" if delta < 0 else "MARGIN_EXPANSION" if delta > 0 else "MARGIN_UNCHANGED",text,ref,
            {"margin_change_bps": delta, "revenue_change_fraction": sales,
             "profit_change": bridge.get("profit_change"),
             "revenue_component": bridge.get("revenue_component"),
             "margin_component": bridge.get("margin_component")}))

    if not rows("cash_flow_reconciliations"):
        missing.append("MATCHED_PERIOD_CASH_FLOW_RECONCILIATION")
    for index,cash in enumerate(rows("cash_flow_reconciliations")):
        _validate_cash_flow_case(cash,issuer_id=issuer,event_id=event,decision_at=dossier["decision_at"])
        ref=f"cash_flow_reconciliations[{index}]"
        ni=cash["reported_net_income"];ocf=cash["reported_operating_cash"]
        target=counters if ni>0 and ocf<=0 else context
        target.append(item("PROFIT_WITHOUT_POSITIVE_OPERATING_CASH" if target is counters else "OPERATING_CASH_RECONCILIATION",
            "Reported profit was not accompanied by positive operating cash this period; timing and source components still require assessment." if target is counters else
            "Operating cash and accounting profit differ; the reconciliation does not prove that cash generation will recur.",
            ref,{"reported_net_income":ni,"reported_operating_cash":ocf,
                 "cash_minus_income":cash["cash_minus_income"],
                 "reconciliation_state":cash["reconciliation_state"]}))
        if cash["reconciliation_state"]!="COMPLETE_RECONCILIATION":
            missing.append("COMPLETE_CASH_FLOW_COMPONENT_RECONCILIATION")
        components=cash["component_totals"]
        if components.get("WORKING_CAPITAL",0)>0:
            context.append(item("WORKING_CAPITAL_CASH_RELEASE",
                "Reported working-capital changes added operating cash; this is not automatically recurring earnings.",ref,
                {"reported_working_capital_contribution":components["WORKING_CAPITAL"]}))
        if components.get("SHARE_BASED_COMPENSATION",0)!=0:
            context.append(item("NONCASH_COMPENSATION_RECONCILIATION",
                "Share-based compensation is a reported noncash adjustment; its add-back is not evidence of cost-free equity financing.",ref,
                {"reported_share_based_compensation":components["SHARE_BASED_COMPENSATION"]}))
        if cash["cash_less_gross_capex"] is not None:
            context.append(item("OPERATING_CASH_LESS_GROSS_CAPEX",
                "Operating cash less gross property-and-equipment outflows excludes issuer-specific adjustments and is not cash available for distribution.",ref,
                {"cash_less_gross_capex":cash["cash_less_gross_capex"]}))

    for scenario_key, expected_kind in (("per_share_bridge", "PER_SHARE_BRIDGE"), ("entry_economics", "ENTRY_ECONOMICS")):
        scenario_child = dossier.get(scenario_key)
        if scenario_child is not None:
            if (not isinstance(scenario_child, Mapping) or scenario_child.get("schema") != SCHEMA
                    or scenario_child.get("kind") != expected_kind):
                raise EvidenceError("brief scenario evidence invalid")
            for flag in ("rank_authority", "entry_authority", "entry_permission", "trade_authority"):
                if flag in scenario_child and scenario_child[flag] is not False:
                    raise EvidenceError("brief scenario cannot grant permission")
    bridge = dossier.get("per_share_bridge")
    if isinstance(bridge, Mapping) and bridge.get("income_grew") is True and bridge.get("eps_grew") is False:
        counters.append(item("INCOME_GROWTH_NOT_PER_SHARE_GROWTH",
            "In the supplied per-share scenario, total profit rose but earnings per diluted share did not; this calculation is not a source-qualified company fact.",
            "per_share_bridge", {"old_eps": bridge.get("old_eps"), "new_eps": bridge.get("new_eps")}))
    scenario = dossier.get("entry_economics")
    if isinstance(scenario, Mapping):
        if scenario.get("within_scenario_ceiling") is False:
            counters.append(item("PRICE_ABOVE_SCENARIO_CEILING",
                "The supplied price exceeds the maximum entry for the stated net reward/risk scenario; this is not a live quote or an entry decision.",
                "entry_economics", {"price_ceiling": scenario.get("price_ceiling_for_required_reward_risk")}))
    else:
        missing.append("PRICE_SENSITIVE_ENTRY_SCENARIO")
    # This earnings-only function never reads market, portfolio, or B4 permissions.
    missing.append("CURRENT_MARKET_AND_PORTFOLIO_PERMISSION")
    for key in ("reported_changes", "expectation_surprises", "matched_revisions", "issuer_guidance_updates", "issuer_guidance_delivery", "profitability_bridges"):
        for child in rows(key):
            for flag in ("rank_authority", "entry_authority", "policy_authority", "trade_authority"):
                if flag in child and child[flag] is not False:
                    raise EvidenceError("brief contains authoritative child")
    valuation = dossier.get("valuation_scenario")
    if valuation is not None:
        _validate_valuation_case(valuation, issuer_id=dossier["issuer_id"],
                                 event_id=dossier["event_id"], decision_at=dossier["decision_at"])
    return {
        "schema": "prophet.earnings_evidence_brief/v1",
        "issuer_id": issuer, "event_id": event, "decision_at": dossier["decision_at"],
        "summary_state": "MIXED_FACTS" if facts and counters else "CAUTIONARY_FACTS" if counters else "FACTS_AVAILABLE" if facts or context else "EVIDENCE_INCOMPLETE",
        "supporting_facts": facts, "counterevidence": counters, "context_facts": context,
        "not_established": sorted(set(missing)),
        "next_step": "Review the unresolved evidence and obtain current entry, market and portfolio permission before treating this research as a trade.",
        "interpretation": "Evidence explanation only; fact count and agreement are not conviction, expected return or buy permission.",
        "authority": {"rank": False, "entry": False, "size": False, "execution": False, "trade": False},
        **({"valuation_scenario": deepcopy(dict(valuation))} if valuation is not None else {}),
    }



def profitability_bridge(
    current_revenue: Actual, prior_revenue: Actual,
    current_profit: Actual, prior_profit: Actual, *, decision_at: str,
) -> dict[str, Any]:
    """Exact revenue/margin arithmetic on comparable, source-qualified actuals.

    P = R*m; the symmetric decomposition is
    delta_P = delta_R * average(m) + delta_m * average(R).
    It is a bookkeeping identity, not evidence that pricing, volume, management
    decisions or any stock-return mechanism caused those components. No quantity,
    mix, asset denominator, quality premium or price target is inferred.
    """
    inputs = (current_revenue, prior_revenue, current_profit, prior_profit)
    if any(not isinstance(value, Actual) for value in inputs):
        raise EvidenceError("profitability requires source-qualified actuals")
    decision = aware_utc(decision_at, "profitability decision_at")
    if any(aware_utc(value.available_at) > decision for value in inputs):
        raise EvidenceError("profitability evidence unavailable at decision")
    if any(date.fromisoformat(value.basis.period_end) > aware_utc(value.public_at).date() for value in inputs):
        raise EvidenceError("profitability actual precedes completed reporting period")
    if (current_revenue.basis.metric not in {"revenue", "total_net_sales"}
            or current_profit.basis.metric not in {"gross_profit", "operating_income", "net_income"}):
        raise EvidenceError("profitability requires revenue and a declared profit measure")
    if (current_revenue.basis.metric != prior_revenue.basis.metric
            or current_profit.basis.metric != prior_profit.basis.metric):
        raise EvidenceError("profitability current/prior metric mismatch")

    def period_identity(basis: MetricBasis) -> tuple[str, ...]:
        return (basis.issuer_id,basis.fiscal_period,basis.period_role,basis.period_start,
                basis.period_end,basis.currency,basis.unit,basis.accounting_basis,basis.share_basis)

    if (period_identity(current_revenue.basis) != period_identity(current_profit.basis)
            or period_identity(prior_revenue.basis) != period_identity(prior_profit.basis)):
        raise EvidenceError("profitability within-period basis mismatch")
    if (not _same_reported_change_basis(current_revenue.basis, prior_revenue.basis)
            or not _same_reported_change_basis(current_profit.basis, prior_profit.basis)):
        raise EvidenceError("profitability current/prior basis mismatch")
    if (date.fromisoformat(prior_revenue.basis.period_end) >= date.fromisoformat(current_revenue.basis.period_start)):
        raise EvidenceError("profitability periods overlap or are reversed")
    if (current_revenue.event_id != current_profit.event_id
            or prior_revenue.event_id != prior_profit.event_id):
        raise EvidenceError("profitability source event mismatch")
    if current_revenue.basis.share_basis != "NOT_APPLICABLE":
        raise EvidenceError("profitability revenue/profit must not be per share")
    cr, pr = float(current_revenue.value), float(prior_revenue.value)
    cp, pp = float(current_profit.value), float(prior_profit.value)
    if cr <= 0 or pr <= 0:
        raise EvidenceError("profitability revenue denominators must be positive")
    cm, pm = cp/cr, pp/pr
    revenue_change = cr-pr
    margin_change = cm-pm
    profit_change = cp-pp
    revenue_component = revenue_change * (cm/2 + pm/2)
    margin_component = margin_change * (cr/2 + pr/2)
    output_numbers=(cm,pm,revenue_change,margin_change,profit_change,revenue_component,margin_component,
                    margin_change*10000,revenue_change/pr)
    if not all(isfinite(value) for value in output_numbers):
        raise EvidenceError("profitability calculation overflow")
    if not isclose(revenue_component+margin_component,profit_change,rel_tol=1e-10,
                   abs_tol=1e-10*max(1.0,abs(revenue_component),abs(margin_component))):
        raise EvidenceError("profitability arithmetic failed to reconcile")
    return {
        "schema": SCHEMA, "kind": "COMPARABLE_PROFITABILITY_BRIDGE",
        "issuer_id": current_revenue.basis.issuer_id,
        "profit_metric": current_profit.basis.metric,
        "current_fiscal_period": current_revenue.basis.fiscal_period,
        "prior_fiscal_period": prior_revenue.basis.fiscal_period,
        "currency": current_revenue.basis.currency, "unit": current_revenue.basis.unit,
        "accounting_basis": current_revenue.basis.accounting_basis,
        "current_event_id": current_revenue.event_id, "prior_event_id": prior_revenue.event_id,
        "current_revenue": cr, "prior_revenue": pr, "current_profit": cp, "prior_profit": pp,
        "current_margin": cm, "prior_margin": pm, "margin_change_bps": margin_change*10000,
        "revenue_change_fraction": revenue_change/pr, "profit_change": profit_change,
        "revenue_component": revenue_component, "margin_component": margin_component,
        "decomposition": "SYMMETRIC_REVENUE_MARGIN_IDENTITY_NOT_CAUSAL_ATTRIBUTION",
        "source_refs": [value.source_ref for value in inputs],
        "source_available_at": [value.available_at for value in inputs],
        "decision_at": decision_at,
        "rank_authority": False, "entry_authority": False,
    }


def earnings_valuation_scenario(
    actual_eps: Actual, *, reference_price: float, terminal_eps: float,
    terminal_pe: float, cash_distributions: float, horizon_years: float,
    required_annual_return: float, decision_at: str,
) -> dict[str, Any]:
    """Explain the price paid for an explicit earnings/multiple scenario.

    Annual/TTM diluted EPS is a source-qualified fact. Price, terminal earnings,
    terminal P/E and distributions are supplied assumptions, NOT a live quote,
    forecast, fair-value estimate, calibrated return or native entry permission.
    Distributions are held as cash without reinvestment through the horizon.
    """
    if not isinstance(actual_eps, Actual):
        raise EvidenceError("source-qualified annual diluted EPS required")
    b = actual_eps.basis
    if b.metric != "EPS" or b.share_basis != "DILUTED":
        raise EvidenceError("valuation requires diluted EPS, not total profit")
    if b.period_role.upper() not in {"ANNUAL", "YEAR", "FULL_YEAR", "TTM", "TRAILING_TWELVE_MONTHS"} or not 350 <= b.days <= 380:
        raise EvidenceError("valuation requires annual or TTM EPS; quarterly extrapolation is not allowed")
    if b.unit != b.currency + "_per_share":
        raise EvidenceError("valuation EPS currency/per-share unit mismatch")
    decision = aware_utc(decision_at, "decision_at")
    if aware_utc(actual_eps.available_at) > decision:
        raise EvidenceError("valuation EPS unavailable at decision")
    values = [finite(v) for v in [reference_price, terminal_eps, terminal_pe,
                                cash_distributions, horizon_years, required_annual_return]]
    if any(v is None for v in values):
        raise EvidenceError("finite valuation scenario assumptions required")
    price, future_eps, multiple, distributions, years, hurdle = values
    if price <= 0 or multiple <= 0 or distributions < 0 or years <= 0 or hurdle <= -1:
        raise EvidenceError("invalid valuation scenario geometry")
    eps = float(actual_eps.value)
    result = {
        "schema": SCHEMA, "kind": "EARNINGS_VALUATION_SCENARIO",
        "issuer_id": b.issuer_id, "event_id": actual_eps.event_id,
        "basis": asdict(b), "actual_eps": eps,
        "actual_source_ref": actual_eps.source_ref,
        "actual_public_at": actual_eps.public_at,
        "actual_available_at": actual_eps.available_at,
        "decision_at": decision_at, "reference_price": price,
        "terminal_eps_assumption": future_eps, "terminal_pe_assumption": multiple,
        "cash_distributions_assumption": distributions, "horizon_years": years,
        "required_annual_return_assumption": hurdle,
        "price_origin": "SUPPLIED_SCENARIO_NOT_VERIFIED_QUOTE",
        "forecast_origin": "SUPPLIED_SCENARIO_NOT_MODEL_PREDICTION",
        "distribution_convention": "CASH_HELD_WITHOUT_REINVESTMENT_TO_HORIZON",
        "costs_and_taxes_included": False,
        "estimated_win_probability": None,
        "rank_authority": False, "entry_authority": False,
        "sizing_authority": False, "trade_authority": False,
        "entry_permission": False,
    }
    if eps <= 0 or future_eps <= 0:
        return {**result, "status": "PE_MODEL_NOT_APPLICABLE_NONPOSITIVE_EARNINGS"}
    try:
        reference_multiple = price / eps
        future_price = future_eps * multiple
        wealth = future_price + distributions
        discount = (1.0 + hurdle) ** years
        total_return = wealth / price - 1.0
        annualized_return = (wealth / price) ** (1.0 / years) - 1.0
        price_ceiling = wealth / discount
        required_eps_raw = (price * discount - distributions) / multiple
        required_eps = max(0.0, required_eps_raw)
        eps_component = (future_eps-eps) * (multiple/2.0+reference_multiple/2.0)
        multiple_component = (multiple-reference_multiple) * (future_eps/2.0+eps/2.0)
    except (ArithmeticError, ValueError):
        raise EvidenceError("valuation scenario arithmetic overflow") from None
    computed = [reference_multiple,future_price,wealth,discount,total_return,
                annualized_return,price_ceiling,required_eps,eps_component,multiple_component]
    if not all(isfinite(v) for v in computed) or discount <= 0:
        raise EvidenceError("valuation scenario arithmetic overflow")
    if abs(eps_component+multiple_component-(future_price-price)) > 1e-9 * max(1.0,abs(future_price),abs(price)):
        raise EvidenceError("valuation scenario price identity failed")
    return {**result, "status": "AVAILABLE_SCENARIO_ONLY",
        "reference_price_to_annual_eps": reference_multiple,
        "terminal_price_assumption": future_price,
        "terminal_wealth_assumption": wealth,
        "scenario_total_return_before_costs": total_return,
        "scenario_annualized_return_before_costs": annualized_return,
        "eps_change_price_component": eps_component,
        "multiple_change_price_component": multiple_component,
        "cash_distribution_price_component": distributions,
        "maximum_reference_price_for_hurdle": price_ceiling,
        "required_terminal_eps_for_hurdle": required_eps,
        "required_terminal_eps_change_fraction": required_eps/eps-1.0,
        "hurdle_covered_by_assumed_distributions": required_eps_raw <= 0,
        "within_scenario_price_ceiling": price <= price_ceiling,
        "interpretation": "Scenario price/earnings hurdle, not a forecast, intrinsic value or permission to buy",
    }


def _validate_valuation_case(item: Mapping[str, Any], *, issuer_id: str, event_id: str,
                             decision_at: str) -> None:
    if not isinstance(item, Mapping) or item.get("schema") != SCHEMA or item.get("kind") != "EARNINGS_VALUATION_SCENARIO":
        raise EvidenceError("invalid valuation scenario evidence")
    if item.get("issuer_id") != issuer_id or item.get("event_id") != event_id:
        raise EvidenceError("valuation scenario identity mismatch")
    if max(aware_utc(str(item.get("decision_at"))), aware_utc(str(item.get("actual_available_at")))) > aware_utc(decision_at):
        raise EvidenceError("valuation scenario evidence is from the future")
    for field in ("rank_authority", "entry_authority", "sizing_authority", "trade_authority", "entry_permission"):
        if item.get(field) is not False:
            raise EvidenceError("authoritative valuation scenario refused")
    if item.get("price_origin") != "SUPPLIED_SCENARIO_NOT_VERIFIED_QUOTE" or item.get("forecast_origin") != "SUPPLIED_SCENARIO_NOT_MODEL_PREDICTION":
        raise EvidenceError("valuation scenario cannot claim observed quote or prediction")

    # Recompute the pure case before it reaches an explanation. Matching names,
    # clocks and false flags alone do not establish the arithmetic. This does not
    # authenticate the source fact or convert assumed prices into observed quotes.
    try:
        basis = MetricBasis(**dict(item["basis"]))
        actual = Actual(basis=basis, value=item["actual_eps"],
            public_at=item["actual_public_at"], available_at=item["actual_available_at"],
            source_ref=item["actual_source_ref"], event_id=item["event_id"])
        expected = earnings_valuation_scenario(actual,
            reference_price=item["reference_price"], terminal_eps=item["terminal_eps_assumption"],
            terminal_pe=item["terminal_pe_assumption"], cash_distributions=item["cash_distributions_assumption"],
            horizon_years=item["horizon_years"], required_annual_return=item["required_annual_return_assumption"],
            decision_at=item["decision_at"])
        import json
        encode = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if encode(dict(item)) != encode(expected):
            raise EvidenceError("valuation scenario arithmetic or shape mismatch")
    except (KeyError, TypeError):
        raise EvidenceError("valuation scenario fields are incomplete") from None


@dataclass(frozen=True)
class CashFlowComponent:
    """One disjoint, signed statement adjustment supplied by the source owner.

    This is not an inference from balance-sheet changes or a recurrence estimate.
    Positive amounts increase reported operating cash relative to net income.
    """
    item_id: str
    category: str
    fact: Actual

    def __post_init__(self) -> None:
        required_text(self.item_id, "cash flow component id")
        if not isinstance(self.category, str) or self.category not in {
            "DEPRECIATION_AMORTIZATION", "SHARE_BASED_COMPENSATION",
            "WORKING_CAPITAL", "OTHER_NONCASH", "OTHER",
        }:
            raise EvidenceError("cash flow component category invalid")
        if not isinstance(self.fact, Actual) or self.fact.basis.metric != "cash_flow_adjustment":
            raise EvidenceError("cash flow component requires qualified adjustment fact")


def cash_flow_reconciliation(
    income: Actual, operating_cash: Actual, *,
    components: Sequence[CashFlowComponent] = (),
    source_reconciliation_complete: bool,
    capex_outflow: Actual | None = None,
    decision_at: str,
) -> dict[str, Any]:
    """Explain one matched-period cash/earnings bridge, not forecast persistence.

    CFO = income + signed reported adjustments. Completeness comes from the
    existing source owner AND numeric reconciliation, never a zero residual alone.
    CFO less gross capex is explicitly named, not an issuer-adjusted FCF measure,
    distributable cash, Ball et al. cash profitability, or a live ranking signal.
    """
    from math import fsum
    if not isinstance(income, Actual) or not isinstance(operating_cash, Actual):
        raise EvidenceError("cash flow requires qualified income and operating cash")
    if type(source_reconciliation_complete) is not bool:
        raise EvidenceError("cash flow explicit completeness state required")
    rows=tuple(components)
    if len(rows)>128 or any(not isinstance(row,CashFlowComponent) for row in rows):
        raise EvidenceError("cash flow components invalid")
    if len({row.item_id for row in rows})!=len(rows):
        raise EvidenceError("cash flow duplicate component")
    if income.basis.metric!="net_income" or operating_cash.basis.metric!="operating_cash_flow":
        raise EvidenceError("cash flow metric mismatch")
    facts=[income,operating_cash,*[row.fact for row in rows]]
    if capex_outflow is not None:
        if not isinstance(capex_outflow,Actual) or capex_outflow.basis.metric!="capital_expenditures":
            raise EvidenceError("cash flow capex metric invalid")
        if float(capex_outflow.value)<0:
            raise EvidenceError("cash flow capex must be an explicit positive outflow magnitude")
        facts.append(capex_outflow)
    decision=aware_utc(decision_at,"cash flow decision_at")
    def key(value: Actual) -> tuple[str,...]:
        b=value.basis
        return (b.issuer_id,b.fiscal_period,b.period_role,b.period_start,b.period_end,
                b.currency,b.unit,b.accounting_basis,b.share_basis)
    if income.basis.share_basis!="NOT_APPLICABLE":
        raise EvidenceError("cash flow cannot mix per-share with total amounts")
    if any(key(fact)!=key(income) for fact in facts):
        raise EvidenceError("cash flow issuer or exact reporting-period basis mismatch")
    if any(fact.event_id!=income.event_id for fact in facts):
        raise EvidenceError("cash flow source event mismatch")
    if any(aware_utc(fact.available_at)>decision for fact in facts):
        raise EvidenceError("cash flow evidence unavailable at decision")
    if any(date.fromisoformat(fact.basis.period_end)>aware_utc(fact.public_at).date() for fact in facts):
        raise EvidenceError("cash flow reporting period not completed")
    ni,ocf=float(income.value),float(operating_cash.value)
    try:
        reported_adjustments=fsum(float(row.fact.value) for row in rows)
        residual=fsum([ocf,-ni,-reported_adjustments])
        gap=ocf-ni
        category_totals={category:fsum(float(row.fact.value) for row in rows if row.category==category)
                         for category in sorted({row.category for row in rows})}
        cash_less_capex=None if capex_outflow is None else ocf-float(capex_outflow.value)
    except (OverflowError,ValueError) as exc:
        raise EvidenceError("cash flow arithmetic overflow") from exc
    if any(not isfinite(v) for v in [reported_adjustments,residual,gap,*category_totals.values()]
           +([] if cash_less_capex is None else [cash_less_capex])):
        raise EvidenceError("cash flow arithmetic overflow")
    reconciles=isclose(residual,0,rel_tol=0,abs_tol=1e-12*max(1,abs(ni),abs(ocf),abs(reported_adjustments)))
    state=("COMPLETE_RECONCILIATION" if reconciles else "UNRECONCILED") if source_reconciliation_complete else "PARTIAL_RECONCILIATION"
    ratio=ocf/ni if ni>0 else None
    ratio_reason="NONPOSITIVE_INCOME" if ni<=0 else None
    if ratio is not None and not isfinite(ratio):
        ratio=None;ratio_reason="RATIO_OUT_OF_RANGE"
    return {
        "schema":SCHEMA,"kind":"CASH_FLOW_RECONCILIATION",
        "issuer_id":income.basis.issuer_id,"event_id":income.event_id,
        "basis":asdict(income.basis),"decision_at":decision_at,
        "source_inputs":{"income":asdict(income),"operating_cash":asdict(operating_cash),
                         "components":[asdict(row) for row in rows],
                         "capex_outflow":None if capex_outflow is None else asdict(capex_outflow)},
        "reported_net_income":ni,"reported_operating_cash":ocf,
        "cash_minus_income":gap,"operating_cash_to_positive_income":ratio,
        "ratio_unavailable_reason":ratio_reason,
        "source_reconciliation_complete":source_reconciliation_complete,
        "reconciliation_state":state,"reported_adjustments_total":reported_adjustments,
        "unexplained_residual":residual,"component_totals":category_totals,
        "gross_capex_outflow":None if capex_outflow is None else float(capex_outflow.value),
        "cash_less_gross_capex":cash_less_capex,
        "cash_after_capex_interpretation":"OPERATING_CASH_MINUS_GROSS_PPE_OUTFLOW_NOT_ISSUER_ADJUSTED_OR_DISTRIBUTABLE_CASH",
        "quality_interpretation":"PERIOD_ACCOUNTING_RECONCILIATION_NOT_RECURRING_CASH_OR_RETURN_FORECAST",
        "source_refs":[fact.source_ref for fact in facts],
        "source_available_at":[fact.available_at for fact in facts],
        "rank_authority":False,"entry_authority":False,
    }


def _validate_cash_flow_case(item: Mapping[str,Any], *, issuer_id: str,
                             event_id: str, decision_at: str) -> None:
    """Recompute this function's closed output; never trust a recomputed hash."""
    import json
    if (not isinstance(item,Mapping) or item.get("schema")!=SCHEMA
            or item.get("kind")!="CASH_FLOW_RECONCILIATION"):
        raise EvidenceError("cash flow dossier evidence invalid")
    if item.get("issuer_id")!=issuer_id or item.get("event_id")!=event_id:
        raise EvidenceError("cash flow dossier identity mismatch")
    if aware_utc(str(item.get("decision_at")))>aware_utc(decision_at):
        raise EvidenceError("cash flow dossier evidence is from the future")
    def actual(raw):
        if not isinstance(raw,Mapping):raise EvidenceError("cash flow input fact invalid")
        values=dict(raw);values["basis"]=MetricBasis(**values["basis"]);return Actual(**values)
    try:
        raw=item["source_inputs"]
        expected=cash_flow_reconciliation(actual(raw["income"]),actual(raw["operating_cash"]),
            components=tuple(CashFlowComponent(x["item_id"],x["category"],actual(x["fact"])) for x in raw["components"]),
            source_reconciliation_complete=item["source_reconciliation_complete"],
            capex_outflow=None if raw["capex_outflow"] is None else actual(raw["capex_outflow"]),
            decision_at=item["decision_at"])
        canonical=lambda obj:json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)
        if canonical(expected)!=canonical(dict(item)):
            raise EvidenceError("cash flow dossier arithmetic or provenance changed")
    except (KeyError,TypeError,OverflowError) as exc:
        raise EvidenceError("cash flow dossier input contract invalid") from exc
