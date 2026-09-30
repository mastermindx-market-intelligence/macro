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
from math import isfinite
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
    now = float(current.value)
    before = float(prior.value)
    diff = now - before
    pct = None if before == 0 else diff / abs(before)
    if pct is not None and not isfinite(pct):
        pct = None
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
        "analyst_consensus_beat": diff > 0 if expected.kind == "ANALYST_CONSENSUS" else None,
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
    residual = naive - matched_mean if naive is not None and matched_mean is not None else None
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
        "matched_median_change": median(delta) if delta else None,
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

    if per_share is not None:
        if not isinstance(per_share, Mapping) or per_share.get("schema") != SCHEMA or per_share.get("kind") != "PER_SHARE_BRIDGE":
            raise EvidenceError("invalid per-share evidence")
        no_child_authority(per_share)
    if entry is not None:
        if not isinstance(entry, Mapping) or entry.get("schema") != SCHEMA or entry.get("kind") != "ENTRY_ECONOMICS":
            raise EvidenceError("invalid entry evidence")
        no_child_authority(entry)

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
        "limitations": limitations,
        "authority": {
            "rank": False,
            "entry": False,
            "size": False,
            "execution": False,
            "trade": False,
        },
    }
