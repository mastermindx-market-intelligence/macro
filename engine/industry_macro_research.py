"""Industry exposure x macro-state research features.

Extends the industry research reader, not the production transmission owner.
Current-vintage data with assumed lag is explicitly supported for discovery.
No claim of original publication clocks, causal exposure or trading authority.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.industry_transition_research import validate_panel

SERIES = ("FEDFUNDS", "TB3MS", "GS10", "CPIAUCSL", "INDPRO")
MACRO_STATES = ("policy_level", "policy_delta3", "policy_delta12", "real_short_proxy",
                "curve10y3m", "inflation_yoy", "inflation_change3", "industrial_growth6")
EXPOSURES = ("exposure_policy", "exposure_yield", "exposure_inflation", "exposure_growth")
MACRO_INTERACTIONS = ("policy_fit", "yield_fit", "inflation_fit", "growth_fit",
                      "improving__real_short", "leading__policy_change", "market_beta__growth")


def macro_state(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not isinstance(monthly.index, pd.PeriodIndex) or monthly.index.freqstr != "M":
        raise ValueError("monthly PeriodIndex required")
    if not monthly.index.is_unique or not monthly.index.is_monotonic_increasing or not set(SERIES).issubset(monthly):
        raise ValueError("ordered unique macro observations and required series needed")
    m = monthly[list(SERIES)].astype(float).copy()
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    if np.isinf(m.to_numpy()).any() or (m[["CPIAUCSL", "INDPRO"]].dropna() <= 0).any().any():
        raise ValueError("invalid macro measurement")
    inflation = 100 * m.CPIAUCSL.pct_change(12, fill_method=None)
    state = pd.DataFrame({
        "policy_level": m.FEDFUNDS, "policy_delta3": m.FEDFUNDS.diff(3),
        "policy_delta12": m.FEDFUNDS.diff(12), "real_short_proxy": m.TB3MS - inflation,
        "curve10y3m": m.GS10 - m.TB3MS, "inflation_yoy": inflation,
        "inflation_change3": inflation.diff(3),
        "industrial_growth6": 100 * ((m.INDPRO / m.INDPRO.shift(6)) ** 2 - 1),
        "yield_delta3": m.GS10.diff(3), "growth_delta3": 100 * np.log(m.INDPRO / m.INDPRO.shift(3)),
    })
    shocks = pd.DataFrame({"policy": m.FEDFUNDS.diff(), "yield": m.GS10.diff(),
                           "inflation": inflation.diff(), "growth": 100 * np.log(m.INDPRO).diff()})
    return state, shocks


def add_macro_context(features: pd.DataFrame, returns: pd.DataFrame, market: pd.Series,
                      monthly: pd.DataFrame, *, publication_lag_months: int = 2) -> pd.DataFrame:
    """Merge fixed slow exposures and lag-available states onto industry decisions.

    A decision in month T sees macro month T-lag. Exposure estimation ends one
    month before that macro month and uses 60 complete months. Missing exposures
    are excluded rather than set to zero. Historical index revisions remain.
    """
    if not isinstance(publication_lag_months, int) or isinstance(publication_lag_months, bool) or publication_lag_months < 1:
        raise ValueError("positive explicit publication lag required")
    if features.duplicated(["as_of", "industry"]).any():
        raise ValueError("duplicate industry decision")
    r, m = validate_panel(returns, market)
    state, shocks = macro_state(monthly)
    # Complete monthly return sums: an internal missing daily observation does
    # not become a shorter month with a deceptively valid return.
    periods = r.index.to_period("M")
    industry_month = np.log1p(r).groupby(periods).agg(lambda x: x.sum(skipna=False))
    market_month = np.log1p(m).groupby(periods).agg(lambda x: x.sum(skipna=False))
    grid = pd.period_range(min(shocks.index.min(), industry_month.index.min()),
                           max(shocks.index.max(), industry_month.index.max()), freq="M")
    x_all = pd.concat([market_month.rename("market"), shocks], axis=1).reindex(grid)
    y_all = industry_month.reindex(grid)
    state = state.reindex(grid)
    positions = {value: k for k, value in enumerate(grid)}
    output = []
    for period, decisions in features.groupby(pd.to_datetime(features.as_of).dt.to_period("M"), sort=True):
        available = period - publication_lag_months
        j = positions.get(available)
        if j is None or j < 60:
            continue
        current = state.iloc[j]
        if not np.isfinite(current.to_numpy()).all():
            continue
        x = x_all.iloc[j - 60:j].to_numpy(float)
        if not np.isfinite(x).all():
            continue
        mean, scale = x.mean(axis=0), x.std(axis=0)
        if (scale < 1e-8).any():
            continue
        design = np.column_stack([np.ones(60), (x - mean) / scale])
        penalty = np.diag([0.] + [6.] * 5)
        inverse = np.linalg.solve(design.T @ design + penalty, design.T)
        for row in decisions.to_dict("records"):
            y = y_all[row["industry"]].iloc[j - 60:j].to_numpy(float)
            if not np.isfinite(y).all():
                continue
            coef = (inverse @ y)[1:] / scale
            # coef[0] is market sensitivity; four remaining slopes correspond
            # to percentage-point policy/yield/inflation and percent IP growth.
            extra = {name: float(current[name]) for name in MACRO_STATES}
            extra.update(dict(zip(EXPOSURES, map(float, coef[1:]))))
            extra.update({
                "policy_fit": float(coef[1] * current.policy_delta3),
                "yield_fit": float(coef[2] * current.yield_delta3),
                "inflation_fit": float(coef[3] * current.inflation_change3),
                "growth_fit": float(coef[4] * current.growth_delta3),
                "improving__real_short": float(row["improving"] * current.real_short_proxy),
                "leading__policy_change": float(row["leading"] * current.policy_delta3),
                "market_beta__growth": float(row["beta_old"] * current.industrial_growth6),
                "macro_observation_month": str(available),
                "exposure_last_fit_month": str(grid[j - 1]),
                "macro_basis": "CURRENT_VINTAGE_RECONSTRUCTION_ASSUMED_PUBLICATION_LAG",
                "macro_assumed_lag_months": publication_lag_months,
            })
            output.append({**row, **extra})
    return pd.DataFrame(output).sort_values(["as_of", "industry"]).reset_index(drop=True) if output else pd.DataFrame()
