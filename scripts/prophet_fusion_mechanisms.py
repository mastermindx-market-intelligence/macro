"""Point-in-time feature adapters for the existing Prophet fusion research owner.

Research only: no live ranker, sizing, ledger, or publication imports. The technical
core is the incumbent gate's explicit no-washout-waiver research path, not a replay
of the context-waived or event-latched board. Unknown observations stay unknown.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

SCHEMA = "prophet.entry_regime_mechanism_spec/v1"
TRIGGERS = ("technical_core_t12", "trend_126_20_50", "breakout_63", "pullback_reclaim_20")
CONTEXTS = ("unfiltered", "market_uptrend", "no_volatility_stress")
OBSERVATION_SCHEMA = "prophet.technical_core_prefix_observation/v1"


class MechanismRefusal(ValueError):
    """Unqualified evidence, not a negative market signal."""


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_spec(path: Path | str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    spec = json.loads(raw)
    if spec.get("schema") != SCHEMA:
        raise MechanismRefusal("SPEC_SCHEMA")
    if not re.fullmatch(r"[0-9a-f]{40}", spec.get("source_base", "")):
        raise MechanismRefusal("SOURCE_PIN_REQUIRED")
    names = spec.get("universe", [])
    if not names or len(names) != len(set(names)) or any(
        not isinstance(n, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", n) for n in names
    ):
        raise MechanismRefusal("UNIVERSE_INVALID")
    if tuple(spec.get("triggers", [])) != TRIGGERS or tuple(spec.get("contexts", [])) != CONTEXTS:
        raise MechanismRefusal("UNSUPPORTED_ARM_CONTRACT")
    arms = {f"{t}__{c}" for t in TRIGGERS for c in CONTEXTS}
    contrasts = spec.get("primary_comparisons", [])
    if (len(contrasts) != spec.get("integer_primary_comparison_count")
            or len({tuple(x) for x in contrasts}) != len(contrasts)
            or any(len(x) != 2 or x[0] == x[1] or not set(x) <= arms for x in contrasts)):
        raise MechanismRefusal("COMPARISON_COUNT_OR_IDENTITY")
    if spec.get("fill_basis") != "next_session_close" or spec.get("promotion_eligible") is not False:
        raise MechanismRefusal("PILOT_AUTHORITY_BOUNDARY")
    if spec.get("entry_gap_sessions") != 3 or spec.get("minimum_history_sessions") != 252:
        raise MechanismRefusal("UNSUPPORTED_OBSERVATION_CONTRACT")
    horizons = [spec.get("primary_horizon"), spec.get("secondary_horizon")]
    if horizons != [21, 63]:
        raise MechanismRefusal("UNSUPPORTED_OUTCOME_HORIZON")
    if pd.Timestamp(spec["start"]) >= pd.Timestamp(spec["end"]):
        raise MechanismRefusal("EMPTY_DATE_WINDOW")
    if not pd.Timestamp(spec["start"]) < pd.Timestamp(spec["split_date"]) < pd.Timestamp(spec["end"]):
        raise MechanismRefusal("SPLIT_OUTSIDE_WINDOW")
    u = spec["uncertainty"]
    if (u["block_sessions"] < 2 * max(horizons) or u["replications"] < 2000
            or not 0 < u["familywise_alpha"] < 0.5):
        raise MechanismRefusal("UNCERTAINTY_CONTRACT")
    costs = spec["cost_sensitivity_bps"]
    if (spec["primary_round_trip_cost_bps"] not in costs or len(costs) != len(set(costs))
            or any(not np.isfinite(x) or x < 0 or x >= 10000 for x in costs)):
        raise MechanismRefusal("COST_CONTRACT")
    spec = dict(spec)
    spec["_sha256"] = digest_bytes(raw)
    return spec


def validate_close(close: pd.Series, name: str = "close") -> pd.Series:
    """Refuse repairs that could silently change the economic/session population."""
    if not isinstance(close, pd.Series) or close.empty:
        raise MechanismRefusal(f"{name}:EMPTY_PRICE_SOURCE")
    if not isinstance(close.index, pd.DatetimeIndex):
        raise MechanismRefusal(f"{name}:DAILY_DATETIME_INDEX_REQUIRED")
    if close.index.tz is not None or not close.index.equals(close.index.normalize()):
        raise MechanismRefusal(f"{name}:AMBIGUOUS_SESSION_CLOCK")
    if not close.index.is_unique or not close.index.is_monotonic_increasing:
        raise MechanismRefusal(f"{name}:DUPLICATE_OR_UNSORTED_SESSIONS")
    try:
        out = close.astype(float)
    except (ValueError, TypeError) as exc:
        raise MechanismRefusal(f"{name}:NONNUMERIC_PRICE") from exc
    if not np.isfinite(out.to_numpy()).all() or (out <= 0).any():
        raise MechanismRefusal(f"{name}:NONFINITE_OR_NONPOSITIVE_PRICE")
    return out


def align_calendar(close: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Use observed benchmark sessions; never compress a missing stock session."""
    c = validate_close(close)
    b = validate_close(benchmark, "benchmark")
    end = min(c.index[-1], b.index[-1])
    c = c.loc[c.index[0]:end]
    expected = b.index[(b.index >= c.index[0]) & (b.index <= end)]
    if c.empty or not c.index.equals(expected):
        missing = expected.difference(c.index)
        extra = c.index.difference(expected)
        raise MechanismRefusal(f"CALENDAR_MISMATCH missing={len(missing)} extra={len(extra)}")
    return c


def _known_bool(value: pd.Series, known: pd.Series) -> pd.Series:
    return value.astype("boolean").where(known, pd.NA)


def market_context(benchmark: pd.Series) -> pd.DataFrame:
    b = validate_close(benchmark, "benchmark")
    r = b.pct_change(fill_method=None)
    ma = b.rolling(200, min_periods=200).mean()
    rv21 = r.rolling(21, min_periods=21).std(ddof=1)
    rv252 = r.rolling(252, min_periods=252).std(ddof=1)
    trend_known = ma.notna() & ma.shift(20).notna()
    stress_known = rv21.notna() & rv252.notna() & (rv252 > 0)
    out = pd.DataFrame(index=b.index)
    out["market_uptrend"] = _known_bool((b > ma) & (ma > ma.shift(20)), trend_known)
    out["no_volatility_stress"] = _known_bool(rv21 <= 1.5 * rv252, stress_known)
    out["market_context_known"] = trend_known & stress_known
    out["market_vol_ratio"] = (rv21 / rv252).where(stress_known)
    return out


def momentum_triggers(close: pd.Series) -> pd.DataFrame:
    c = validate_close(close)
    ma20 = c.rolling(20, min_periods=20).mean()
    ma50 = c.rolling(50, min_periods=50).mean()
    prior_high = c.rolling(63, min_periods=63).max().shift(1)
    prior126 = c.shift(126)
    out = pd.DataFrame(index=c.index)
    out["trend_126_20_50"] = _known_bool(
        (c > prior126) & (ma20 > ma50), prior126.notna() & ma50.notna())
    out["breakout_63"] = _known_bool(c > prior_high, prior_high.notna())
    out["pullback_reclaim_20"] = _known_bool(
        (c > prior126) & (c.shift(1) <= ma20.shift(1)) & (c > ma20),
        prior126.notna() & ma20.shift(1).notna())
    # The common history floor avoids giving simpler challengers a different early sample.
    out.loc[out.index[:251], :] = pd.NA
    return out


def ex_ante_beta(close: pd.Series, benchmark: pd.Series) -> pd.Series:
    c = validate_close(close)
    b = validate_close(benchmark, "benchmark").reindex(c.index)
    x = c.pct_change(fill_method=None)
    y = b.pct_change(fill_method=None)
    var = y.rolling(252, min_periods=252).var(ddof=1)
    return (x.rolling(252, min_periods=252).cov(y) / var).where(var > 0)


def technical_core_observations(
    ticker: str,
    close: pd.Series,
    dates: pd.DatetimeIndex,
    *,
    gate_fn: Callable[..., dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Evaluate only prefixes, explicitly excluding non-reconstructable context.

    A failure does not become a false trigger. Forming/provisional observations are
    retained as such; they are not retroactively moved to their event/pivot date.
    """
    c = validate_close(close, ticker)
    if gate_fn is None:
        from engine.signal_gate import gate
        gate_fn = gate
    if not dates.is_unique or not dates.is_monotonic_increasing or not dates.isin(c.index).all():
        raise MechanismRefusal("OBSERVATION_DATES_NOT_EXACT_SESSIONS")
    rows: list[dict[str, Any]] = []
    for date in dates:
        i = int(c.index.get_loc(date))
        row: dict[str, Any] = {
            "date": date, "ticker": ticker, "signal": None, "tier": None,
            "provisional": None, "event_date": None, "observed_date": None,
            "status": "HISTORY_UNAVAILABLE", "reason": "fewer_than_252_bars",
        }
        if i >= 251:
            try:
                v = gate_fn(ticker, c.iloc[:i + 1].copy(), reclaim_veto=True,
                            washout_waiver=False, event_latch=None)
                if not isinstance(v, dict) or v.get("result") is None:
                    raise MechanismRefusal("ENGINE_UNAVAILABLE")
                if v.get("waiver"):
                    raise MechanismRefusal("UNEXPECTED_CONTEXT_WAIVER")
                if not isinstance(v.get("eligible"), (bool, np.bool_)):
                    raise MechanismRefusal("ELIGIBILITY_TYPE")
                tier = v.get("tier_cascade")
                if tier not in (None, "T1", "T2", "T3", "T4"):
                    raise MechanismRefusal("TIER_CONTRACT")
                signal = bool(v["eligible"] and tier in ("T1", "T2"))
                event_date = v.get("tier_event_date")
                observed_date = v.get("tier_observed_date")
                for value in (event_date, observed_date):
                    if value is not None and pd.Timestamp(value) > date:
                        raise MechanismRefusal("FUTURE_PROVENANCE")
                if signal and (event_date is None or observed_date is None):
                    raise MechanismRefusal("SIGNAL_PROVENANCE_UNAVAILABLE")
                provisional = v.get("provisional")
                if provisional is not None and not isinstance(provisional, (bool, np.bool_)):
                    raise MechanismRefusal("PROVISIONAL_TYPE")
                provisional = (None if provisional is None else bool(provisional))
                if v.get("tier_observation_provisional") is True or v.get("sub") == "pending":
                    provisional = True
                row.update(signal=signal, tier=tier, provisional=provisional,
                           event_date=event_date, observed_date=observed_date,
                           status="EVALUATED", reason=str(v.get("reason", "")))
            except Exception as exc:  # preserve a typed non-market refusal, never invent a signal
                row.update(status="UNAVAILABLE", reason=f"{type(exc).__name__}:{str(exc)[:180]}")
        rows.append(row)
    out = pd.DataFrame(rows).set_index("date")
    out["signal"] = out["signal"].astype("boolean")
    out["provisional"] = out["provisional"].astype("boolean")
    return out


def onset_mask(signal: pd.Series, gap: int = 3) -> pd.Series:
    """Regime filtering must happen AFTER this; filtering must not manufacture re-fires."""
    if gap < 1:
        raise MechanismRefusal("INVALID_ONSET_GAP")
    s = signal.astype("boolean")
    prior_known = s.notna().shift(1, fill_value=False).rolling(gap, min_periods=gap).sum() == gap
    prior_true = s.astype("Float64").shift(1).rolling(gap, min_periods=gap).sum()
    return (s.fillna(False) & prior_known & prior_true.eq(0)).astype(bool)


def net_return(gross: float | np.ndarray, round_trip_bps: float) -> float | np.ndarray:
    """Symmetric half-spread/impact on entry and exit; no claim of calibrated fill costs."""
    if not np.isfinite(round_trip_bps) or not 0 <= round_trip_bps < 10000:
        raise MechanismRefusal("INVALID_COST")
    half = round_trip_bps / 20000.0
    return (1.0 + gross) * (1.0 - half) / (1.0 + half) - 1.0


def canonical_outcome(close: pd.Series, benchmark: pd.Series, date: pd.Timestamp, horizon: int) -> dict:
    """Delegate the outcome to the existing grader after exact-calendar qualification."""
    from engine.grading import forward_metrics
    if horizon not in (21, 63):
        raise MechanismRefusal("UNREGISTERED_HORIZON")
    if date not in close.index or date not in benchmark.index:
        raise MechanismRefusal("DECISION_DATE_NOT_AN_OBSERVED_SESSION")
    i, j = int(close.index.get_loc(date)), int(benchmark.index.get_loc(date))
    stop, bstop = i + 1 + horizon, j + 1 + horizon
    if stop >= len(close) or bstop >= len(benchmark):
        return {"status": "UNMATURED"}
    stock_window = close.iloc[i:stop + 1]
    market_window = benchmark.iloc[j:bstop + 1]
    if not stock_window.index.equals(market_window.index):
        raise MechanismRefusal("FORWARD_CALENDAR_MISMATCH")
    if not np.isfinite(stock_window.to_numpy()).all() or not np.isfinite(market_window.to_numpy()).all():
        raise MechanismRefusal("FORWARD_PRICE_UNAVAILABLE")
    a = forward_metrics(close, date, horizons=(horizon,))
    b = forward_metrics(benchmark, date, horizons=(horizon,))
    if a["fill_date"] != b["fill_date"]:
        raise MechanismRefusal("FILL_CALENDAR_MISMATCH")
    return {
        "status": "MATURED", "fill_date": a["fill_date"],
        "exit_date": str(close.index[stop].date()),
        "gross_return": float(a[f"fwd_ret_{horizon}"]),
        "benchmark_return": float(b[f"fwd_ret_{horizon}"]),
        "forward_mdd_close": float(a[f"fwd_mdd_{horizon}"]),
        "forward_mfe_close": float(a[f"fwd_mfe_{horizon}"]),
    }
