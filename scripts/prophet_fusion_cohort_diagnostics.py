"""Research-only context and attribution for the existing Conditional Fusion owner.

No oscillator, event, cohort, regime score, ranker, trading rule or market-data store
is created here. Native EntryEvent records, the house session calendar, the existing
volatility percentile primitive and native grader outputs remain their owners.
A prior-session date label is NOT proof of original source publication/receipt time.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from engine.entry_radar.entry_events import EntryEvent
from engine.vol_regime import _pctile
from lib.nyse_calendar import sessions_between

SCHEMA = "prophet.cohort_diagnostics/v1"
CLOCK_LIMIT = "PRIOR_SESSION_LABEL_PROXY_NOT_ORIGINAL_RECEIPT"
AUTHORITY = "RESEARCH_DIAGNOSTIC_ONLY"


class DiagnosticRefusal(ValueError):
    """The evidence cannot support this diagnostic; never a negative market signal."""


@dataclass(frozen=True)
class TrajectorySpec:
    """One non-optimized measurement definition; changes require another version."""

    moving_average_sessions: int = 20
    slope_sessions: int = 5
    rank_sessions: int = 252
    peak_sessions: int = 63
    observation_lag_sessions: int = 1

    def __post_init__(self) -> None:
        values = (self.moving_average_sessions, self.slope_sessions, self.rank_sessions,
                  self.peak_sessions, self.observation_lag_sessions)
        if any(type(x) is not int for x in values) or values != (20, 5, 252, 63, 1):
            raise DiagnosticRefusal("V1_MEASUREMENT_IS_FIXED_NOT_A_SEARCH_GRID")


def _dates(index: pd.Index, *, complete: bool = False) -> pd.DatetimeIndex:
    if (not isinstance(index, pd.DatetimeIndex) or index.tz is not None
            or index.hasnans or not index.is_unique or not index.is_monotonic_increasing
            or not index.equals(index.normalize())):
        raise DiagnosticRefusal("UNIQUE_ORDERED_NAIVE_SESSION_DATES_REQUIRED")
    if len(index):
        expected = pd.DatetimeIndex(sessions_between(index[0].date(), index[-1].date()))
        if (complete and not index.equals(expected)) or not index.isin(expected).all():
            raise DiagnosticRefusal("SESSION_CALENDAR_MISMATCH")
    return index


def _levels(series: pd.Series, grid: pd.DatetimeIndex, name: str) -> pd.Series:
    _dates(series.index)
    if pd.api.types.is_bool_dtype(series.dtype):
        raise DiagnosticRefusal(f"{name}:BOOLEAN_IS_NOT_A_LEVEL")
    try:
        values = pd.to_numeric(series, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise DiagnosticRefusal(f"{name}:NONNUMERIC_LEVEL") from exc
    if ((~np.isfinite(values) & values.notna()) | (values <= 0)).any():
        raise DiagnosticRefusal(f"{name}:NONPOSITIVE_OR_NONFINITE_LEVEL")
    return values.reindex(grid)  # No fill: a missing session breaks every affected window.


def implied_volatility_trajectory(
    vix: pd.Series, vvix: pd.Series, sessions: pd.DatetimeIndex,
    *, spec: TrajectorySpec = TrajectorySpec(),
) -> pd.DataFrame:
    """Lagged raw VIX/VVIX level, MA direction and retreat; no bullish/bearish verdict.

    Slopes are fractional MA(t)/MA(t-5)-1, not point changes. The existing native
    percentile compares current level with the preceding 251 observations within
    its 252-session window. Unlike that primitive's optional short-history mode,
    this consumer requires every one of the 252 session observations to exist.
    Features are then delayed one common trading session. This is a conservative
    date proxy, not authentication of an intraday or contemporaneous data vintage.
    """
    grid = _dates(sessions, complete=True)
    out = pd.DataFrame(index=grid)
    for name, raw in (("vix", vix), ("vvix", vvix)):
        level = _levels(raw, grid, name)
        ma = level.rolling(spec.moving_average_sessions,
                           min_periods=spec.moving_average_sessions).mean()
        full_rank = level.rolling(spec.rank_sessions, min_periods=spec.rank_sessions).count()
        values = pd.DataFrame({
            f"{name}_level": level,
            f"{name}_ma20": ma,
            f"{name}_ma20_slope5": ma / ma.shift(spec.slope_sessions) - 1,
            f"{name}_level_to_ma20": level / ma - 1,
            f"{name}_rank252": _pctile(level, spec.rank_sessions).where(
                full_rank.eq(spec.rank_sessions)),
            f"{name}_retreat_from63_peak": 1 - level / level.rolling(
                spec.peak_sessions, min_periods=spec.peak_sessions).max(),
        }, index=grid).shift(spec.observation_lag_sessions)
        out = out.join(values)
    out["feature_session"] = pd.Series(grid, index=grid).shift(spec.observation_lag_sessions)
    a, b = out["vix_ma20_slope5"], out["vvix_ma20_slope5"]
    known = a.notna() & b.notna()
    direction = pd.Series("UNAVAILABLE", index=grid, dtype="string")
    direction.loc[known] = "FLAT_OR_MIXED"
    for mask, label in (
        ((a > 0) & (b > 0), "BOTH_RISING"),
        ((a < 0) & (b < 0), "BOTH_FALLING"),
        ((a > 0) & (b < 0), "VIX_RISING_VVIX_FALLING"),
        ((a < 0) & (b > 0), "VIX_FALLING_VVIX_RISING"),
    ):
        direction.loc[known & mask] = label
    out["direction_pair"] = direction
    out["trajectory_available"] = known
    out["rank_pair_available"] = out[["vix_rank252", "vvix_rank252"]].notna().all(axis=1)
    out.attrs.update(schema=SCHEMA, authority=AUTHORITY, clock_limit=CLOCK_LIMIT,
                     promotion_eligible=False, forecast_probability=None)
    return out


def join_native_event_context(events: Sequence[EntryEvent], context: pd.DataFrame) -> list[dict]:
    """Decorate native events, retaining unknown clocks and provisional status.

    No first-observation clock is reconstructed from signal_ts. Native finality is
    preserved, never upgraded. A joined date is diagnostic availability, not PIT
    certification; original receipts remain required for any historical hypothesis.
    """
    _dates(context.index, complete=True)
    if (context.attrs.get("schema") != SCHEMA or context.attrs.get("authority") != AUTHORITY
            or context.attrs.get("promotion_eligible") is not False
            or context.attrs.get("clock_limit") != CLOCK_LIMIT):
        raise DiagnosticRefusal("UNQUALIFIED_CONTEXT_CONTRACT")
    required = {"feature_session", "trajectory_available", "direction_pair"}
    if not required.issubset(context.columns):
        raise DiagnosticRefusal("CONTEXT_FIELDS_REQUIRED")
    if not pd.api.types.is_bool_dtype(context["trajectory_available"].dtype):
        raise DiagnosticRefusal("CONTEXT_AVAILABILITY_MUST_BE_BOOLEAN")
    ids: set[str] = set()
    result: list[dict] = []
    for event in events:
        if not isinstance(event, EntryEvent):
            raise DiagnosticRefusal("NATIVE_ENTRY_EVENT_REQUIRED")
        # Revalidate the immutable contract against mutated nested mappings too.
        EntryEvent.from_dict(event.to_dict())
        if not event.event_id or event.event_id in ids:
            raise DiagnosticRefusal("DUPLICATE_OR_MISSING_EVENT_ID")
        ids.add(event.event_id)
        row = {"event_id": event.event_id, "ticker": event.ticker,
               "family": event.family, "detector_id": event.detector_id,
               "source_identity": event.source_identity.to_dict(),
               "signal_ts": event.signal_ts, "signal_known_ts": event.signal_known_ts,
               "bar_state": event.bar_state, "final": event.final,
               "field_origin": dict(event.field_origin),
               "family_first_available": dict(event.family_first_available or {}),
               "pre_channel_reconstruction": event.pre_channel_reconstruction,
               "join_status": "SIGNAL_KNOWABILITY_UNAVAILABLE", "context": None,
               "authority": AUTHORITY, "promotion_eligible": False}
        if event.signal_known_ts is not None:
            try:
                day = pd.Timestamp(event.signal_known_ts)
                signal_day = pd.Timestamp(event.signal_ts)
                if (day.tz is not None or day != day.normalize() or pd.isna(day)
                        or signal_day.tz is not None or pd.isna(signal_day) or day < signal_day):
                    raise ValueError("inconsistent session label")
                _dates(pd.DatetimeIndex([day]))
            except (ValueError, TypeError, DiagnosticRefusal):
                row["join_status"] = "INVALID_KNOWN_SESSION"
            else:
                if day not in context.index:
                    row["join_status"] = "CONTEXT_SESSION_UNAVAILABLE"
                elif pd.isna(context.at[day, "trajectory_available"]) or not bool(context.at[day, "trajectory_available"]):
                    row["join_status"] = "CONTEXT_WINDOW_INCOMPLETE"
                else:
                    features = context.loc[day].to_dict()
                    source_day = features.get("feature_session")
                    if pd.isna(source_day) or pd.Timestamp(source_day) >= day:
                        raise DiagnosticRefusal("CONTEXT_NOT_STRICTLY_PRIOR_SESSION")
                    row.update(join_status="JOINED_DATE_PROXY_ONLY", context=features,
                               clock_limit=CLOCK_LIMIT)
        result.append(row)
    return result


def _finite(value: Any, label: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise DiagnosticRefusal(f"{label}:BOOLEAN_NOT_NUMBER")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DiagnosticRefusal(f"{label}:FINITE_NUMBER_REQUIRED") from exc
    if not math.isfinite(number):
        raise DiagnosticRefusal(f"{label}:FINITE_NUMBER_REQUIRED")
    return number


def rate_change_decomposition(
    before: Mapping[str, Mapping[str, float]], after: Mapping[str, Mapping[str, float]],
    *, before_contract: Mapping[str, str], after_contract: Mapping[str, str],
) -> dict:
    """Exact symmetric split of aggregate-rate change into mix and within-state terms.

    Each cell has `weight` and `rate`. Weights must already follow the declared
    date/episode/other ruler and sum to one; no automatic reweighting. Every state
    needs support on both sides. No p-values, causal effects or probabilities are
    inferred. Formula: mix=sum((p1-p0)*(q1+q0)/2), within=sum((q1-q0)*(p1+p0)/2).
    """
    required = {"outcome_definition", "horizon", "weighting", "population_rule"}
    if (set(before_contract) != required or dict(before_contract) != dict(after_contract)
            or any(not isinstance(v, str) or not v.strip() for v in before_contract.values())):
        raise DiagnosticRefusal("INCOMPATIBLE_RATE_RULERS")
    if (not before or set(before) != set(after)
            or any(not isinstance(k, str) or not k.strip() for k in before)):
        raise DiagnosticRefusal("COMMON_STATE_SUPPORT_REQUIRED")
    totals = [0.0, 0.0]
    means = [0.0, 0.0]
    rows = []
    for state in sorted(before):
        p, q = [], []
        for k, cells in enumerate((before, after)):
            cell = cells[state]
            if set(cell) != {"weight", "rate"}:
                raise DiagnosticRefusal("EXACT_RATE_CELL_REQUIRED")
            p.append(_finite(cell["weight"], "weight"))
            q.append(_finite(cell["rate"], "rate"))
            if not 0 < p[k] <= 1 or not 0 <= q[k] <= 1:
                raise DiagnosticRefusal("POSITIVE_SUPPORT_AND_RATE_IN_UNIT_INTERVAL_REQUIRED")
            totals[k] += p[k]
            means[k] += p[k] * q[k]
        rows.append({"state": state, "mix": (p[1]-p[0])*(q[1]+q[0])/2,
                     "within": (q[1]-q[0])*(p[1]+p[0])/2})
    if any(not math.isclose(x, 1, abs_tol=1e-10, rel_tol=0) for x in totals):
        raise DiagnosticRefusal("WEIGHTS_MUST_SUM_TO_ONE_NO_SILENT_NORMALIZATION")
    mix, within = sum(x["mix"] for x in rows), sum(x["within"] for x in rows)
    delta = means[1] - means[0]
    if not math.isclose(mix + within, delta, abs_tol=1e-12):
        raise DiagnosticRefusal("DECOMPOSITION_IDENTITY_FAILED")
    return {"schema": SCHEMA, "contract": dict(before_contract), "before_rate": means[0],
            "after_rate": means[1], "difference": delta, "mix_component": mix,
            "within_state_component": within, "cells": rows,
            "interpretation": "DESCRIPTIVE_IDENTITY_NOT_CAUSAL", "promotion_eligible": False}


def same_entry_horizon_attribution(short: pd.DataFrame, long: pd.DataFrame) -> pd.DataFrame:
    """Explain 21-to-63 continuation from already-graded identical entries.

    Both inputs use native canonical_outcome fields plus event_id, horizon and
    price_basis. No prices are read or outcomes generated. Incomplete or unmatched
    rows remain in output. Returns are gross so transaction costs cannot be charged
    twice; no interval is interpreted as an executable sell/rebuy policy.
    """
    required = {"event_id", "horizon", "fill_date", "price_basis", "status",
                "gross_return", "benchmark_return"}
    for frame, horizon in ((short, 21), (long, 63)):
        if not required.issubset(frame.columns):
            raise DiagnosticRefusal("CANONICAL_OUTCOME_FIELDS_REQUIRED")
        if (frame["event_id"].isna().any() or frame["event_id"].duplicated().any()
                or not frame["event_id"].map(lambda x: isinstance(x, str) and bool(x.strip())).all()
                or not frame["horizon"].eq(horizon).all()):
            raise DiagnosticRefusal("UNIQUE_EVENT_ID_AND_EXACT_HORIZON_REQUIRED")
    a, b = short.set_index("event_id"), long.set_index("event_id")
    rows = []
    for event_id in sorted(set(a.index) | set(b.index)):
        row = {"event_id": event_id, "status": "UNMATCHED_HORIZON", "continuation_return": None,
               "benchmark_continuation_return": None, "continuation_excess": None,
               "gross21": None, "gross63": None, "promotion_eligible": False}
        if event_id not in a.index or event_id not in b.index:
            rows.append(row)
            continue
        x, y = a.loc[event_id], b.loc[event_id]
        if x["status"] != "MATURED" or y["status"] != "MATURED":
            row.update(status="INCOMPLETE_OR_CENSORED", short_status=x["status"], long_status=y["status"])
            rows.append(row)
            continue
        if (pd.isna(x["fill_date"]) or pd.isna(x["price_basis"])
                or not isinstance(x["price_basis"], str) or not x["price_basis"].strip()
                or x["fill_date"] != y["fill_date"] or x["price_basis"] != y["price_basis"]):
            raise DiagnosticRefusal("ENTRY_OR_PRICE_BASIS_MISMATCH")
        try:
            _dates(pd.DatetimeIndex([pd.Timestamp(x["fill_date"])]))
        except (ValueError, TypeError, DiagnosticRefusal) as exc:
            raise DiagnosticRefusal("INVALID_FILL_SESSION") from exc
        r21, r63 = (_finite(z["gross_return"], "gross_return") for z in (x, y))
        b21, b63 = (_finite(z["benchmark_return"], "benchmark_return") for z in (x, y))
        if min(r21, r63, b21, b63) < -1:
            raise DiagnosticRefusal("GROSS_RETURN_BELOW_TOTAL_LOSS")
        if (r21 == -1 and r63 != -1) or (b21 == -1 and b63 != -1):
            raise DiagnosticRefusal("ZERO_WEALTH_CANNOT_REBOUND_WITHOUT_NEW_CAPITAL")
        row.update(gross21=r21, gross63=r63, fill_date=x["fill_date"], price_basis=x["price_basis"])
        if r21 == -1 or b21 == -1:
            row["status"] = "TOTAL_LOSS_CONTINUATION_UNDEFINED"
        else:
            continuation, market = (1+r63)/(1+r21)-1, (1+b63)/(1+b21)-1
            row.update(status="PAIRED_GROSS_SEGMENTS", continuation_return=continuation,
                       benchmark_continuation_return=market, continuation_excess=continuation-market)
            if not math.isclose((1+r21)*(1+continuation)-1, r63, abs_tol=1e-12):
                raise DiagnosticRefusal("HORIZON_ACCOUNTING_IDENTITY_FAILED")
        rows.append(row)
    output = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "event_id", "status", "continuation_return", "benchmark_continuation_return",
        "continuation_excess", "gross21", "gross63", "promotion_eligible"])
    output.attrs.update(schema=SCHEMA, authority=AUTHORITY, costs_reapplied=False,
                        interpretation="DESCRIPTIVE_SAME_ENTRY_PATH_NOT_AN_EXIT_POLICY")
    return output
