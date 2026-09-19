"""R5 Stage-0 PIT spot/IV shock conditioning.

Research-only transform over the EXISTING options-hub volatility owner.

This module does not create a volatility feed, a scenario engine, an outcome label,
or trade authority. It reuses options_hub's exact 30-DTE ATM-IV construction and
the same ThetaData Greeks snapshots, then asks a narrower construction question:

    given an explicitly declared spot shock, what trailing PIT distribution of
    same-session 30-DTE ATM-IV changes is consistent with the observed spot/IV
    relationship?

Stage 0 deliberately starts with the falsifiable linear baseline

    dIV_30 = alpha + beta * dSpot_pct + residual

and keeps the residual distribution empirical. Event-state and volatility-regime
conditioning are NOT implemented here and are named as missing dimensions in the
returned object.

No future session is read: every source row is filtered to `date <= asof` before
the shock panel is formed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import numpy as np
import pandas as pd

from engine.options_hub import _atm_iv_for_expiry, _iv30_from_term
from lib import nyse_calendar

SCHEMA = "options.r5_spot_vol_stage0/v1"
MODEL = "pit_linear_spot_to_iv30_empirical_residual/v1"
SOURCE_METHOD = "options_hub_30d_atm_iv_plus_snapshot_spot/v1"


@dataclass(frozen=True)
class ShockObservation:
    prior_date: str
    date: str
    spot_pct: float
    iv_change_pts: float


def _parse_day(value: object) -> date | None:
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(ts):
        return None
    return ts.date()


def _session_point(day_df: pd.DataFrame, day: date) -> tuple[float, float] | None:
    """Return (median spot, 30-DTE ATM IV in vol points) for one source session."""
    spot_values = pd.to_numeric(day_df["underlying_price"], errors="coerce")
    spot_values = spot_values[np.isfinite(spot_values) & (spot_values > 0)]
    if spot_values.empty:
        return None
    spot = float(spot_values.median())

    term_rows: list[dict] = []
    for expiration, grp in day_df.groupby("expiration"):
        exp_day = _parse_day(expiration)
        if exp_day is None:
            continue
        dte = (exp_day - day).days
        # Match options_hub._compute_iv_history: 0DTE is not a 30-DTE term point.
        if dte <= 0:
            continue
        atm = _atm_iv_for_expiry(grp, spot)
        if atm is None or not np.isfinite(atm) or atm <= 0:
            continue
        term_rows.append({"dte": dte, "atm_iv": float(atm) * 100.0})

    iv30 = _iv30_from_term(term_rows)
    if iv30 is None or not np.isfinite(iv30) or iv30 <= 0:
        return None
    return spot, float(iv30)


def build_spot_iv_shocks(
    greeks_df: pd.DataFrame,
    asof: str,
) -> tuple[list[ShockObservation], dict]:
    """Build adjacent-NYSE-session spot/IV shocks from source rows at or before `asof`.

    Store holes are not bridged. Friday->Monday is adjacent because the NYSE calendar
    contains no session between them; Monday->Wednesday is rejected when Tuesday was a
    session but is absent from the source points.
    """
    required = {"date", "expiration", "strike", "implied_vol", "underlying_price"}
    missing = sorted(required - set(getattr(greeks_df, "columns", ())))
    if missing:
        raise ValueError(f"R5 spot/IV source is missing required columns: {missing}")

    asof_day = _parse_day(asof)
    if asof_day is None:
        raise ValueError("R5 asof must contain a valid date")

    if greeks_df.empty:
        return [], {
            "source_rows": 0,
            "source_sessions": 0,
            "qualified_sessions": 0,
            "shock_observations": 0,
            "gap_pairs_refused": 0,
            "first_session": None,
            "last_session": None,
        }

    work = greeks_df.copy()
    parsed = pd.to_datetime(work["date"], errors="coerce")
    work["_r5_day"] = parsed.dt.date
    work = work[work["_r5_day"].notna()]
    work = work[work["_r5_day"] <= asof_day]

    source_sessions = int(work["_r5_day"].nunique())
    points: list[tuple[date, float, float]] = []
    for day, grp in work.groupby("_r5_day", sort=True):
        if not isinstance(day, date) or not nyse_calendar.is_session(day):
            continue
        point = _session_point(grp, day)
        if point is None:
            continue
        points.append((day, point[0], point[1]))

    points.sort(key=lambda row: row[0])
    shocks: list[ShockObservation] = []
    gap_pairs_refused = 0
    for prior, current in zip(points, points[1:]):
        prior_day, prior_spot, prior_iv = prior
        day, spot, iv = current
        if nyse_calendar.sessions_strictly_between(prior_day, day):
            gap_pairs_refused += 1
            continue
        if prior_spot <= 0 or not np.isfinite(prior_spot):
            continue
        spot_pct = (spot / prior_spot - 1.0) * 100.0
        iv_change = iv - prior_iv
        if not (np.isfinite(spot_pct) and np.isfinite(iv_change)):
            continue
        shocks.append(
            ShockObservation(
                prior_date=str(prior_day),
                date=str(day),
                spot_pct=float(spot_pct),
                iv_change_pts=float(iv_change),
            )
        )

    return shocks, {
        "source_rows": int(len(work)),
        "source_sessions": source_sessions,
        "qualified_sessions": len(points),
        "shock_observations": len(shocks),
        "gap_pairs_refused": gap_pairs_refused,
        "first_session": str(points[0][0]) if points else None,
        "last_session": str(points[-1][0]) if points else None,
    }


def fit_pit_spot_iv_distribution(
    greeks_df: pd.DataFrame,
    asof: str,
    *,
    lookback_observations: int,
    min_observations: int,
    spot_shocks_pct: Sequence[float],
    residual_quantiles: Sequence[float],
) -> dict:
    """Fit the R5 Stage-0 PIT spot/IV baseline and evaluate declared spot shocks.

    All configuration is explicit. `spot_shocks_pct` is bounded to the existing
    Market Structure Core first-order scenario envelope (+/-3%). Returned scenario
    quantiles are empirical-residual translations around the fitted conditional mean,
    not Gaussian intervals and not future realized outcomes.
    """
    if not isinstance(lookback_observations, int) or lookback_observations < 2:
        raise ValueError("lookback_observations must be an integer >= 2")
    if not isinstance(min_observations, int) or min_observations < 2:
        raise ValueError("min_observations must be an integer >= 2")
    if min_observations > lookback_observations:
        raise ValueError("min_observations cannot exceed lookback_observations")

    shocks_declared = [float(v) for v in spot_shocks_pct]
    if not shocks_declared:
        raise ValueError("spot_shocks_pct must be non-empty")
    if any(not np.isfinite(v) or abs(v) > 3.0 for v in shocks_declared):
        raise ValueError("spot_shocks_pct must be finite and within +/-3%")

    quantiles = [float(q) for q in residual_quantiles]
    if not quantiles:
        raise ValueError("residual_quantiles must be non-empty")
    if any(not np.isfinite(q) or not (0.0 < q < 1.0) for q in quantiles):
        raise ValueError("residual_quantiles must be finite and strictly between 0 and 1")
    if quantiles != sorted(set(quantiles)):
        raise ValueError("residual_quantiles must be unique and ascending")

    observations, coverage = build_spot_iv_shocks(greeks_df, asof)
    selected = observations[-lookback_observations:]

    base = {
        "schema": SCHEMA,
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "asof": str(_parse_day(asof)),
        "source_method": SOURCE_METHOD,
        "conditioning": {
            "model": MODEL,
            "lookback_observations": lookback_observations,
            "min_observations": min_observations,
            "vol_regime": "not_conditioned_stage0",
            "event_state": "not_conditioned_stage0",
            "residual_distribution": "empirical",
        },
        "coverage": {
            **coverage,
            "fit_observations": len(selected),
            "fit_first_date": selected[0].date if selected else None,
            "fit_last_date": selected[-1].date if selected else None,
        },
        "fit": None,
        "scenarios": [],
        "status": "insufficient_history",
    }
    if len(selected) < min_observations:
        return base

    x = np.asarray([row.spot_pct for row in selected], dtype=float)
    y = np.asarray([row.iv_change_pts for row in selected], dtype=float)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError("R5 fit observations must be finite")
    if float(np.ptp(x)) <= 1e-12:
        return {**base, "status": "degenerate_spot_variation"}

    design = np.column_stack([np.ones(len(x), dtype=float), x])
    alpha, beta = np.linalg.lstsq(design, y, rcond=None)[0]
    fitted = design @ np.asarray([alpha, beta])
    residuals = y - fitted
    ss_res = float(np.sum(residuals ** 2))
    centered = y - float(np.mean(y))
    ss_tot = float(np.sum(centered ** 2))
    r2 = None if ss_tot <= 1e-18 else 1.0 - ss_res / ss_tot
    x_std = float(np.std(x))
    y_std = float(np.std(y))
    corr = None if x_std <= 1e-18 or y_std <= 1e-18 else float(np.corrcoef(x, y)[0, 1])

    residual_q = [
        {
            "q": q,
            "residual_iv_change_pts": float(np.quantile(residuals, q, method="linear")),
        }
        for q in quantiles
    ]

    scenarios = []
    for shock in shocks_declared:
        mean_change = float(alpha + beta * shock)
        scenarios.append(
            {
                "spot_shock_pct": shock,
                "conditional_mean_iv_change_pts": mean_change,
                "iv_change_quantiles": [
                    {
                        "q": row["q"],
                        "iv_change_pts": mean_change + row["residual_iv_change_pts"],
                    }
                    for row in residual_q
                ],
            }
        )

    return {
        **base,
        "status": "ok",
        "fit": {
            "alpha_iv_change_pts": float(alpha),
            "beta_iv_pts_per_1pct_spot": float(beta),
            "r2": r2,
            "correlation": corr,
            "spot_abs_median_pct": float(np.median(np.abs(x))),
            "iv_change_abs_median_pts": float(np.median(np.abs(y))),
            "residual_quantiles": residual_q,
        },
        "scenarios": scenarios,
    }
