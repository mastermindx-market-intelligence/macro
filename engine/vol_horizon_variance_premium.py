from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED. Horizon-matched variance-risk-premium measurement (brief Q14).

VERDICT (Q14 forward variance premium, frozen comparison): see
research/quant_assessment_2026_10/Q14_forward_variance_premium/VERDICT.md.
REJECT the predictive upgrade (trial Q14-T1, S&P 500 / VIX 30cd, holdout 2012-01-30..2026-09-08,
170 non-overlapping 30cd windows, 58 63-day blocks): adding premium_hat to [1, IV2, RV_trail]
cut holdout MSE by 2.0% (bar 5%), block-bootstrap 95% lower bound of the loss gain -7.3e-08
(not > 0), HAC t 1.10, QLIKE slightly worse. The horizon-matched MEASUREMENT is retained as
research-only; no forecast, trade or short-volatility authority follows.

What this module is
-------------------
A pure-function reference for measuring an equity variance risk premium on ONE basis:

    premium_hat(t) = IV2_h(t) - F_h(t)            (ex ante, both legs known at t)
    premium_ex_post(t) = IV2_h(t) - RV_h(t, t+h]  (ex post, a forward LABEL)

where every leg is a variance over the same horizon ``h`` calendar days, expressed
in HORIZON VARIANCE UNITS (not volatility points, not annualized), with an explicit
day-count basis, session label, measure kind and coverage receipt.

It exists because the incumbent repo numbers are NOT this estimand:
``engine/vol_regime.py`` computes ``VIX - cone_vol_ann`` (volatility points, a
252-trading-day multi-scale trailing std of demeaned percent returns against a
365-calendar-day 30-day variance-swap strip), ``engine/conditions.py`` computes
``VIX - trailing realized std``, and ``engine/options_hub.py`` computes
``atm_iv_30 - rv20``. Those incumbents are untouched; this module neither replaces
nor feeds them.

Acceptance contract (each enforced in code, see tests/test_vol_horizon_variance_premium.py)
-----------------------------------------------------------------------------------------
req1  Both legs share horizon, day-count basis, session and variance units, or the
      premium builder refuses.
req2  A forward-realized LABEL can never enter the ex-ante estimate; a forecast whose
      information time is after the as-of time is refused.
req3  Overnight and tail-strike coverage are explicit fields; a leg without a coverage
      receipt is refused.
req4  Strip (model-free-style) and ATM-proxy estimates are never mixed in one history
      unless the caller asks for an explicit per-kind segmentation.
req5  Incremental evidence is judged against simple IV/RV controls on a chronological
      holdout with moving-block-bootstrap and HAC uncertainty.
req6  No expected-profit, probability, trade-selection or short-volatility authority:
      output records carry ``authority = "none"`` and forbidden keys are refused.

Identity worth stating once: given IV2, the information in premium_hat equals the
information in its forecast leg F. Predicting the ex-post premium is the same problem
as forecasting realized variance. A premium "adds information" only if F adds
information beyond the controls that already contain IV2.

Not wired: nothing imports this module; it registers nothing, schedules nothing and
performs no I/O at import. RESEARCH_ONLY is True.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

RESEARCH_ONLY = True

AUTHORITY = "none"
UNITS_HORIZON_VARIANCE = "horizon_variance"
MEASURE_KINDS = ("strip", "atm_proxy")
PHYSICAL_KINDS = ("forecast", "forward_label")
SAMPLINGS = ("close_to_close", "open_to_close")
DAY_COUNTS = {"calendar365": 365.0, "trading252": 252.0}
FORBIDDEN_OUTPUT_KEYS = frozenset({
    "expected_profit", "expected_pnl", "pnl", "profit", "edge", "win_probability",
    "probability", "risk_probability", "crash_probability", "trade", "trade_signal",
    "signal", "position", "size", "sizing", "rank", "sell_vol", "short_vol",
    "short_volatility", "recommendation", "action",
})

__all__ = [
    "RESEARCH_ONLY", "AUTHORITY", "FORBIDDEN_OUTPUT_KEYS", "HorizonBasis",
    "StripVarianceResult", "ImpliedLeg", "PhysicalLeg", "PremiumRecord",
    "vol_index_to_horizon_variance", "horizon_variance_to_annualized_vol",
    "daily_variance_to_horizon_variance", "strip_variance", "atm_proxy_leg",
    "strip_leg", "daily_log_returns", "forward_realized_variance",
    "trailing_realized_variance", "realized_coverage", "build_premium",
    "ex_post_premium", "assemble_history", "assert_no_authority", "ols_fit",
    "ols_predict", "qlike", "newey_west_mean", "moving_block_bootstrap_mean",
    "incremental_comparison",
]


# ─────────────────────────────── basis and units ───────────────────────────────

@dataclass(frozen=True)
class HorizonBasis:
    """The shared basis both legs must carry (req1)."""

    horizon_calendar_days: int
    day_count: str = "calendar365"
    units: str = UNITS_HORIZON_VARIANCE
    session_close: str = "unspecified"

    def __post_init__(self) -> None:
        if not isinstance(self.horizon_calendar_days, (int, np.integer)) or self.horizon_calendar_days <= 0:
            raise ValueError("horizon_calendar_days must be a positive integer")
        if self.horizon_calendar_days > 3660:
            raise ValueError("horizon_calendar_days is bounded at 3660")
        if self.day_count not in DAY_COUNTS:
            raise ValueError(f"day_count must be one of {sorted(DAY_COUNTS)}")
        if self.units != UNITS_HORIZON_VARIANCE:
            raise ValueError("only horizon_variance units are admitted")

    @property
    def basis_days(self) -> float:
        """Horizon length in the day-count's own units: calendar days under
        ``calendar365``; expected trading days ``252*h/365`` under ``trading252``."""
        return basis_days(self.horizon_calendar_days, self.day_count)

    @property
    def year_fraction(self) -> float:
        """basis_days / year_days, which equals h/365 under every admitted day count."""
        return self.basis_days / DAY_COUNTS[self.day_count]


def basis_days(horizon_calendar_days: int, day_count: str) -> float:
    """Horizon length in day-count units: h * year_days / 365 (h calendar days)."""
    if day_count not in DAY_COUNTS:
        raise ValueError(f"day_count must be one of {sorted(DAY_COUNTS)}")
    return float(horizon_calendar_days) * DAY_COUNTS[day_count] / 365.0


def vol_index_to_horizon_variance(level_pct: Any, horizon_calendar_days: int = 30,
                                  year_days: float = 365.0) -> np.ndarray:
    """A VIX-style index (annualized vol in percent on a calendar basis) to the
    variance over ``horizon_calendar_days`` calendar days: (level/100)^2 * h/year_days."""
    lv = np.asarray(level_pct, dtype=float)
    if np.any(lv[np.isfinite(lv)] < 0):
        raise ValueError("vol index level must be non-negative")
    return (lv / 100.0) ** 2 * (float(horizon_calendar_days) / float(year_days))


def horizon_variance_to_annualized_vol(var_h: Any, horizon_calendar_days: int,
                                       year_days: float = 365.0) -> np.ndarray:
    """Inverse view for display in the SAME basis: sqrt(var_h * year_days / h)."""
    v = np.asarray(var_h, dtype=float)
    return np.sqrt(np.clip(v, 0.0, None) * float(year_days) / float(horizon_calendar_days))


def daily_variance_to_horizon_variance(daily_var: Any, horizon_calendar_days: int,
                                       trading_days_per_year: float = 252.0) -> np.ndarray:
    """Per-trading-day variance to horizon variance: daily_var * N, with
    N = trading_days_per_year * h / 365 expected trading days in the horizon."""
    n = float(trading_days_per_year) * float(horizon_calendar_days) / 365.0
    return np.asarray(daily_var, dtype=float) * n


# ─────────────────────────────── implied leg ───────────────────────────────

@dataclass(frozen=True)
class StripVarianceResult:
    variance_annual: float
    variance_horizon: float
    t_years: float
    k0: float
    n_puts_used: int
    n_calls_used: int
    k_low_over_forward: float
    k_high_over_forward: float
    put_wing_stopped_by_zero_bids: bool
    call_wing_stopped_by_zero_bids: bool
    discretization: str = "cboe_midpoint_rule"
    jump_correction: str = "none"
    measure_kind: str = "strip"


def strip_variance(strikes: Sequence[float], call_bid: Sequence[float], call_ask: Sequence[float],
                   put_bid: Sequence[float], put_ask: Sequence[float], forward: float,
                   rate: float, t_years: float) -> StripVarianceResult:
    """CBOE-style discretized log-contract strip for ONE expiry.

    sigma^2 = (2/T) * sum_i dK_i / K_i^2 * exp(rT) * Q(K_i) - (1/T) * (F/K0 - 1)^2

    Out-of-the-money puts below K0 and calls above K0 are included moving away from
    K0; a zero-bid strike is skipped and the wing stops after two consecutive zero
    bids (the vendor truncation rule, which biases the strip DOWN). The receipt
    records the strike range actually used and whether each wing was truncated.
    No jump correction is applied.
    """
    k = np.asarray(strikes, dtype=float)
    cb, ca = np.asarray(call_bid, dtype=float), np.asarray(call_ask, dtype=float)
    pb, pa = np.asarray(put_bid, dtype=float), np.asarray(put_ask, dtype=float)
    n = k.size
    if n < 3 or n > 20000:
        raise ValueError("strip needs between 3 and 20000 strikes")
    if not (cb.size == ca.size == pb.size == pa.size == n):
        raise ValueError("quote arrays must match strikes")
    if np.any(np.diff(k) <= 0) or np.any(k <= 0):
        raise ValueError("strikes must be positive and strictly increasing")
    if not (forward > 0 and t_years > 0 and math.isfinite(rate)):
        raise ValueError("forward and t_years must be positive, rate finite")
    if t_years > 10:
        raise ValueError("t_years is bounded at 10")
    below = np.nonzero(k <= forward)[0]
    if below.size == 0:
        raise ValueError("no strike at or below the forward")
    i0 = int(below[-1])
    k0 = float(k[i0])

    def wing(indices: Iterable[int], bid: np.ndarray) -> tuple[list[int], bool]:
        used: list[int] = []
        zeros = 0
        stopped = False
        for i in indices:
            if bid[i] <= 0:
                zeros += 1
                if zeros >= 2:
                    stopped = True
                    break
                continue
            zeros = 0
            used.append(i)
        return used, stopped

    puts, put_stop = wing(range(i0 - 1, -1, -1), pb)
    calls, call_stop = wing(range(i0 + 1, n), cb)
    q: dict[int, float] = {}
    for i in puts:
        q[i] = 0.5 * (pb[i] + pa[i])
    for i in calls:
        q[i] = 0.5 * (cb[i] + ca[i])
    q[i0] = 0.5 * (0.5 * (pb[i0] + pa[i0]) + 0.5 * (cb[i0] + ca[i0]))
    idx = sorted(q)
    ks = k[idx]
    dk = np.empty(len(idx))
    if len(idx) == 1:
        raise ValueError("strip needs at least two usable strikes")
    dk[0] = ks[1] - ks[0]
    dk[-1] = ks[-1] - ks[-2]
    if len(idx) > 2:
        dk[1:-1] = (ks[2:] - ks[:-2]) / 2.0
    qv = np.array([q[i] for i in idx])
    contrib = np.sum(dk / ks ** 2 * math.exp(rate * t_years) * qv)
    var_ann = (2.0 / t_years) * contrib - (1.0 / t_years) * (forward / k0 - 1.0) ** 2
    return StripVarianceResult(
        variance_annual=float(var_ann), variance_horizon=float(var_ann * t_years),
        t_years=float(t_years), k0=k0, n_puts_used=len(puts), n_calls_used=len(calls),
        k_low_over_forward=float(ks[0] / forward), k_high_over_forward=float(ks[-1] / forward),
        put_wing_stopped_by_zero_bids=put_stop, call_wing_stopped_by_zero_bids=call_stop,
    )


@dataclass(frozen=True)
class ImpliedLeg:
    """Risk-neutral variance over the basis horizon, in horizon variance units."""

    value: float
    basis: HorizonBasis
    measure_kind: str
    asof: int
    coverage: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.measure_kind not in MEASURE_KINDS:
            raise ValueError(f"measure_kind must be one of {MEASURE_KINDS}")
        _require_coverage(self.coverage, ("tail_strikes", "overnight"))


def strip_leg(result: StripVarianceResult, basis: HorizonBasis, asof: int) -> ImpliedLeg:
    """Wrap a strip result; refuses when the strip maturity differs from the basis horizon."""
    if abs(result.t_years - basis.year_fraction) > 0.5 / 365.0:
        raise ValueError("strip maturity does not match the basis horizon (interpolate first)")
    truncated = result.put_wing_stopped_by_zero_bids or result.call_wing_stopped_by_zero_bids
    cov = {
        "tail_strikes": "strip_truncated" if truncated else "strip_listed_range",
        "k_low_over_forward": result.k_low_over_forward,
        "k_high_over_forward": result.k_high_over_forward,
        "jump_correction": result.jump_correction,
        "overnight": "risk_neutral_horizon_includes_overnight",
    }
    return ImpliedLeg(result.variance_horizon, basis, "strip", int(asof), cov)


def atm_proxy_leg(atm_iv: float, basis: HorizonBasis, asof: int) -> ImpliedLeg:
    """ATM implied vol (annualized, decimal, in the basis' day count) as a PROXY: one
    strike, no tail coverage. Labelled ``atm_proxy`` so it never passes as a strip.
    Horizon variance = atm_iv^2 * basis_days / year_days = atm_iv^2 * year_fraction."""
    if not (atm_iv >= 0 and math.isfinite(atm_iv)) or atm_iv > 10:
        raise ValueError("atm_iv must be a finite decimal in [0, 10]")
    value = atm_iv ** 2 * basis.year_fraction
    cov = {"tail_strikes": "single_strike_none",
           "overnight": "risk_neutral_horizon_includes_overnight"}
    return ImpliedLeg(float(value), basis, "atm_proxy", int(asof), cov)


# ─────────────────────────────── physical leg ───────────────────────────────

def daily_log_returns(close: Sequence[float]) -> np.ndarray:
    """Close-to-close log returns; element i is realized at observation i (element 0 NaN)."""
    c = np.asarray(close, dtype=float)
    if c.size > 200000:
        raise ValueError("series bounded at 200000 observations")
    if np.any(c[np.isfinite(c)] <= 0):
        raise ValueError("prices must be positive")
    r = np.full(c.size, np.nan)
    r[1:] = np.diff(np.log(c))
    return r


def _cum_sq(returns: np.ndarray) -> np.ndarray:
    sq = np.where(np.isfinite(returns), returns ** 2, 0.0)
    return np.concatenate([[0.0], np.cumsum(sq)])


def _check_days(day: np.ndarray, n: int) -> None:
    if day.size != n:
        raise ValueError("day offsets must align with returns")
    if np.any(np.diff(day) <= 0):
        raise ValueError("day offsets must be strictly increasing integers")


def forward_realized_variance(returns: Sequence[float], day: Sequence[int],
                              horizon_calendar_days: int) -> np.ndarray:
    """LABEL: sum of squared (non-demeaned) returns realized on days in
    (day[t], day[t] + h]. NaN when the window is not complete in the data.
    ``day`` is an integer calendar-day offset (any origin)."""
    r = np.asarray(returns, dtype=float)
    d = np.asarray(day, dtype=np.int64)
    _check_days(d, r.size)
    cs = _cum_sq(r)
    end = np.searchsorted(d, d + int(horizon_calendar_days), side="right") - 1
    i = np.arange(r.size)
    out = (cs[end + 1] - cs[i + 1]).astype(float)
    miss = np.concatenate([[0], np.cumsum(~np.isfinite(r))])
    nmiss = miss[end + 1] - miss[i + 1]
    out[(d + int(horizon_calendar_days) > d[-1]) | (nmiss > 0)] = np.nan
    return out


def trailing_realized_variance(returns: Sequence[float], day: Sequence[int],
                               horizon_calendar_days: int) -> np.ndarray:
    """Known at t: sum of squared returns realized on days in (day[t]-h, day[t]].
    NaN when the window starts before the data or contains a missing return."""
    r = np.asarray(returns, dtype=float)
    d = np.asarray(day, dtype=np.int64)
    _check_days(d, r.size)
    cs = _cum_sq(r)
    miss = np.concatenate([[0], np.cumsum(~np.isfinite(r))])
    start = np.searchsorted(d, d - int(horizon_calendar_days), side="right")
    i = np.arange(r.size)
    out = (cs[i + 1] - cs[start]).astype(float)
    nmiss = miss[i + 1] - miss[start]
    out[(d - int(horizon_calendar_days) < d[0]) | (nmiss > 0)] = np.nan
    return out


def realized_coverage(sampling: str) -> dict[str, Any]:
    """Explicit overnight/intraday coverage receipt for a realized leg (req3)."""
    if sampling not in SAMPLINGS:
        raise ValueError(f"sampling must be one of {SAMPLINGS}")
    return {
        "sampling": sampling,
        "overnight": "included" if sampling == "close_to_close" else "excluded",
        "intraday_path": "not_observed_daily_sampling",
        "tail_strikes": "not_applicable_physical_leg",
        "demeaned": False,
    }


@dataclass(frozen=True)
class PhysicalLeg:
    """Physical (statistical) variance over the basis horizon, horizon variance units.

    ``kind == "forecast"``: built only from information at or before
    ``information_time``. ``kind == "forward_label"``: realized after ``asof``; it may
    only enter :func:`ex_post_premium`, never :func:`build_premium`.
    """

    value: float
    basis: HorizonBasis
    kind: str
    asof: int
    information_time: int
    coverage: Mapping[str, Any]
    method: str = "unspecified"

    def __post_init__(self) -> None:
        if self.kind not in PHYSICAL_KINDS:
            raise ValueError(f"kind must be one of {PHYSICAL_KINDS}")
        _require_coverage(self.coverage, ("overnight", "sampling"))


def _require_coverage(cov: Mapping[str, Any] | None, keys: Sequence[str]) -> None:
    if not isinstance(cov, Mapping):
        raise ValueError("a coverage receipt is required (req3)")
    for key in keys:
        if key not in cov or cov[key] in (None, "", "unknown_unstated"):
            raise ValueError(f"coverage receipt must state {key!r} explicitly (req3)")


# ─────────────────────────────── premium records ───────────────────────────────

@dataclass(frozen=True)
class PremiumRecord:
    asof: int
    implied_variance: float
    physical_variance: float
    premium_variance: float
    horizon_calendar_days: int
    day_count: str
    units: str
    measure_kind: str
    physical_kind: str
    timing: str
    session_note: str
    implied_coverage: Mapping[str, Any]
    physical_coverage: Mapping[str, Any]
    authority: str = AUTHORITY
    notes: tuple = field(default_factory=tuple)

    def annualized_vol_view(self) -> dict[str, float]:
        yd = DAY_COUNTS[self.day_count]
        n = basis_days(self.horizon_calendar_days, self.day_count)
        return {
            "implied_vol_ann": float(horizon_variance_to_annualized_vol(self.implied_variance, n, yd)),
            "physical_vol_ann": float(horizon_variance_to_annualized_vol(self.physical_variance, n, yd)),
            "premium_variance_ann": float(self.premium_variance * yd / n),
        }

    def to_dict(self) -> dict[str, Any]:
        out = {
            "asof": self.asof, "implied_variance": self.implied_variance,
            "physical_variance": self.physical_variance,
            "premium_variance": self.premium_variance,
            "horizon_calendar_days": self.horizon_calendar_days, "day_count": self.day_count,
            "units": self.units, "measure_kind": self.measure_kind,
            "physical_kind": self.physical_kind, "timing": self.timing,
            "session_note": self.session_note,
            "implied_coverage": dict(self.implied_coverage),
            "physical_coverage": dict(self.physical_coverage),
            "authority": self.authority, "notes": list(self.notes),
        }
        assert_no_authority(out)
        return out


def _check_basis(implied: ImpliedLeg, physical: PhysicalLeg, acknowledge_session_offset: bool) -> str:
    a, b = implied.basis, physical.basis
    if a.horizon_calendar_days != b.horizon_calendar_days:
        raise ValueError("horizon mismatch between legs (req1)")
    if a.day_count != b.day_count:
        raise ValueError("day-count basis mismatch between legs (req1)")
    if a.units != b.units:
        raise ValueError("variance units mismatch between legs (req1)")
    if implied.asof != physical.asof:
        raise ValueError("legs are stamped at different as-of times (req1)")
    if a.session_close != b.session_close:
        if not acknowledge_session_offset:
            raise ValueError("session close differs between legs; acknowledge explicitly (req1)")
        return f"session offset acknowledged: implied {a.session_close} vs physical {b.session_close}"
    return f"same session close {a.session_close}"


def build_premium(implied: ImpliedLeg, physical: PhysicalLeg, *,
                  acknowledge_session_offset: bool = False) -> PremiumRecord:
    """Ex-ante premium estimate IV2_h - F_h. Refuses a forward label or a forecast that
    used information after the as-of time (req2), and any basis mismatch (req1)."""
    if physical.kind != "forecast":
        raise ValueError("a forward-realized label cannot enter the ex-ante premium (req2)")
    if physical.information_time > physical.asof:
        raise ValueError("forecast uses information after the as-of time (req2)")
    note = _check_basis(implied, physical, acknowledge_session_offset)
    if not (math.isfinite(implied.value) and math.isfinite(physical.value)):
        raise ValueError("legs must be finite")
    return PremiumRecord(
        asof=implied.asof, implied_variance=float(implied.value),
        physical_variance=float(physical.value),
        premium_variance=float(implied.value - physical.value),
        horizon_calendar_days=implied.basis.horizon_calendar_days,
        day_count=implied.basis.day_count, units=implied.basis.units,
        measure_kind=implied.measure_kind, physical_kind="forecast", timing="ex_ante",
        session_note=note, implied_coverage=dict(implied.coverage),
        physical_coverage=dict(physical.coverage),
        notes=(f"physical method: {physical.method}",),
    )


def ex_post_premium(implied: ImpliedLeg, label: PhysicalLeg, *,
                    acknowledge_session_offset: bool = False) -> PremiumRecord:
    """Ex-post premium IV2_h - RV_h(t, t+h]. Requires a forward label; timing is
    ``ex_post`` so it can never be read as a contemporaneous estimate."""
    if label.kind != "forward_label":
        raise ValueError("ex_post_premium needs a forward_label leg")
    if label.information_time <= label.asof:
        raise ValueError("a forward label must be realized after the as-of time")
    note = _check_basis(implied, label, acknowledge_session_offset)
    return PremiumRecord(
        asof=implied.asof, implied_variance=float(implied.value),
        physical_variance=float(label.value),
        premium_variance=float(implied.value - label.value),
        horizon_calendar_days=implied.basis.horizon_calendar_days,
        day_count=implied.basis.day_count, units=implied.basis.units,
        measure_kind=implied.measure_kind, physical_kind="forward_label", timing="ex_post",
        session_note=note, implied_coverage=dict(implied.coverage),
        physical_coverage=dict(label.coverage),
        notes=("ex-post label; not available at as-of",),
    )


def assemble_history(records: Sequence[PremiumRecord], *, segment_by_kind: bool = False
                     ) -> list[PremiumRecord] | dict[str, list[PremiumRecord]]:
    """One history per measure kind and basis (req4). Mixed kinds raise unless the
    caller asks for an explicit ``{kind: records}`` segmentation; mixed horizon,
    day-count or timing always raise."""
    recs = list(records)
    if len(recs) > 1_000_000:
        raise ValueError("history bounded at 1,000,000 records")
    if not recs:
        return {} if segment_by_kind else []
    for attr in ("horizon_calendar_days", "day_count", "units", "timing"):
        vals = {getattr(r, attr) for r in recs}
        if len(vals) > 1:
            raise ValueError(f"history mixes {attr}: {sorted(map(str, vals))}")
    kinds = {r.measure_kind for r in recs}
    ordered = sorted(recs, key=lambda r: r.asof)
    if segment_by_kind:
        return {k: [r for r in ordered if r.measure_kind == k] for k in sorted(kinds)}
    if len(kinds) > 1:
        raise ValueError("history silently mixes strip and atm_proxy estimates (req4)")
    return ordered


def assert_no_authority(obj: Any) -> None:
    """Refuse any output that carries profit, probability, trade or short-vol keys (req6)."""
    if isinstance(obj, Mapping):
        for key, val in obj.items():
            if str(key).lower() in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"output key {key!r} implies authority this module does not hold (req6)")
            if str(key).lower() == "authority" and val != AUTHORITY:
                raise ValueError("authority must be 'none' (req6)")
            assert_no_authority(val)
    elif isinstance(obj, (list, tuple)):
        for val in obj:
            assert_no_authority(val)


# ─────────────────────────────── evaluation helpers (req5) ───────────────────────────────

def ols_fit(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Least squares with an intercept column prepended. Returns coefficients."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[0] != y.size or y.size < x.shape[1] + 2:
        raise ValueError("ols needs aligned rows and more rows than regressors")
    xx = np.column_stack([np.ones(y.size), x])
    beta, *_ = np.linalg.lstsq(xx, y, rcond=None)
    return beta


def ols_predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    return np.column_stack([np.ones(x.shape[0]), x]) @ beta


def qlike(y: np.ndarray, f: np.ndarray, floor: float = 1e-8) -> np.ndarray:
    """Patton QLIKE loss y/f - log(y/f) - 1 with the forecast floored at ``floor``."""
    y = np.clip(np.asarray(y, dtype=float), floor, None)
    f = np.clip(np.asarray(f, dtype=float), floor, None)
    ratio = y / f
    return ratio - np.log(ratio) - 1.0


def newey_west_mean(d: np.ndarray, lags: int) -> dict[str, float]:
    """Mean of ``d`` with a Bartlett-kernel HAC standard error and the DM-style t."""
    d = np.asarray(d, dtype=float)
    n = d.size
    if n < 10 or lags < 0 or lags >= n:
        raise ValueError("need n >= 10 and 0 <= lags < n")
    m = float(d.mean())
    e = d - m
    s = float(e @ e) / n
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        s += 2.0 * w * float(e[k:] @ e[:-k]) / n
    se = math.sqrt(max(s, 0.0) / n)
    return {"mean": m, "se": se, "t": (m / se) if se > 0 else float("nan"), "lags": int(lags)}


def moving_block_bootstrap_mean(d: np.ndarray, block: int, n_boot: int, seed: int,
                                alpha: float = 0.05) -> dict[str, float]:
    """Moving-block bootstrap percentile interval for the mean of ``d``."""
    d = np.asarray(d, dtype=float)
    n = d.size
    if block < 1 or block > n or n_boot < 100 or n_boot > 100000:
        raise ValueError("bounded inputs: 1 <= block <= n, 100 <= n_boot <= 100000")
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block))
    starts_max = n - block + 1
    cs = np.concatenate([[0.0], np.cumsum(d)])
    block_sums = cs[block:] - cs[:-block]
    means = np.empty(n_boot)
    for b in range(n_boot):
        s = rng.integers(0, starts_max, size=n_blocks)
        means[b] = block_sums[s].sum() / (n_blocks * block)
    lo, hi = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi),
            "block": int(block), "n_boot": int(n_boot), "seed": int(seed)}


def incremental_comparison(y_train: np.ndarray, xc_train: np.ndarray, xa_train: np.ndarray,
                           y_test: np.ndarray, xc_test: np.ndarray, xa_test: np.ndarray, *,
                           block: int, n_boot: int, seed: int, hac_lags: int,
                           practical_bar: float, n_segments: int = 3) -> dict[str, Any]:
    """Fit controls C and augmented A on the training rows only, score both on the
    untouched test rows, and decide with the pre-registered rule:

    keep_predictive iff relative MSE reduction >= practical_bar AND the moving-block
    bootstrap lower bound of mean(L_C - L_A) > 0 AND the reduction is positive in at
    least ceil(2/3 * n_segments) of ``n_segments`` chronological test segments.
    """
    bc = ols_fit(xc_train, y_train)
    ba = ols_fit(xa_train, y_train)
    fc = ols_predict(bc, xc_test)
    fa = ols_predict(ba, xa_test)
    y = np.asarray(y_test, dtype=float)
    lc, la = (y - fc) ** 2, (y - fa) ** 2
    d = lc - la
    mse_c, mse_a = float(lc.mean()), float(la.mean())
    rel = (mse_c - mse_a) / mse_c if mse_c > 0 else float("nan")
    boot = moving_block_bootstrap_mean(d, block, n_boot, seed)
    hac = newey_west_mean(d, hac_lags)
    seg_rel = []
    for seg in np.array_split(np.arange(y.size), n_segments):
        sc, sa = float(lc[seg].mean()), float(la[seg].mean())
        seg_rel.append((sc - sa) / sc if sc > 0 else float("nan"))
    need = int(math.ceil(2.0 * n_segments / 3.0))
    stable = sum(1 for v in seg_rel if v > 0) >= need
    ql_c, ql_a = qlike(y, fc), qlike(y, fa)
    ql_d = ql_c - ql_a
    keep = bool(rel >= practical_bar and boot["lo"] > 0 and stable)
    out = {
        "beta_controls": [float(v) for v in bc], "beta_augmented": [float(v) for v in ba],
        "mse_controls": mse_c, "mse_augmented": mse_a, "relative_mse_reduction": float(rel),
        "loss_diff_bootstrap": boot, "loss_diff_hac": hac,
        "segment_relative_reduction": [float(v) for v in seg_rel],
        "segments_positive": int(sum(1 for v in seg_rel if v > 0)), "segments_needed": need,
        "qlike_controls": float(ql_c.mean()), "qlike_augmented": float(ql_a.mean()),
        "qlike_diff_hac": newey_west_mean(ql_d, hac_lags),
        "practical_bar": float(practical_bar), "keep_predictive_upgrade": keep,
        "authority": AUTHORITY,
    }
    assert_no_authority(out)
    return out
