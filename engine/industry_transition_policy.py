"""Fixed research policies around industry momentum; no live rank mutations.

Selectors consume only explicitly named decision-time columns. Outcome columns
may accompany rows for subsequent evaluation but never enter a selection key.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

POLICIES = ("momentum", "price_risk", "context_risk", "low_volatility", "expected_excess")


def combine_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    keys = ["decision_date", "industry"]
    context = predictions[predictions.model == "context"].copy()
    price = predictions[predictions.model == "price"].copy()
    if context.empty or price.empty:
        raise ValueError("both original model prediction sets required")
    if context.duplicated(keys).any() or price.duplicated(keys).any():
        raise ValueError("duplicate prediction identities")
    a = context.set_index(keys).sort_index()
    b = price.set_index(keys).sort_index()
    if not a.index.equals(b.index):
        raise ValueError("models have different candidate populations")
    for column in ("relative126", "vol63", "fold"):
        np.testing.assert_allclose(a[column], b[column], rtol=0, atol=0, equal_nan=True)
    a["p_bad_loss_price"] = b.p_bad_loss
    return a.reset_index()


def _validate(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    if frame.duplicated(["decision_date", "industry"]).any():
        raise ValueError("duplicate candidates")
    if not np.isfinite(frame[list(columns)].to_numpy(float)).all():
        raise ValueError("nonfinite required selection inputs")
    if not frame.industry.map(lambda x: isinstance(x, str) and bool(x)).all():
        raise ValueError("industry keys must be nonempty strings")


def momentum_protected(frame: pd.DataFrame, policy: str, *, fraction: float = .2,
                       pool_fraction: float = .4) -> pd.DataFrame:
    """Equal date-level coverage, fixed momentum prefilter and deterministic ties."""
    if policy not in POLICIES: raise ValueError("unknown research policy")
    if not 0 < fraction <= pool_fraction <= 1: raise ValueError("invalid coverage")
    feature, ascending = {
        "momentum": ("relative126", False), "price_risk": ("p_bad_loss_price", True),
        "context_risk": ("p_bad_loss", True), "low_volatility": ("vol63", True),
        "expected_excess": ("expected_excess_net", False),
    }[policy]
    _validate(frame, tuple(dict.fromkeys(("relative126", feature))))
    selections = []
    for _, group in frame.groupby("decision_date", sort=True):
        k = max(1, int(np.ceil(len(group) * fraction)))
        n = max(k, int(np.ceil(len(group) * pool_fraction)))
        pool = group.sort_values(["relative126", "industry"], ascending=[False, True], kind="stable").head(n)
        take = pool.sort_values([feature, "industry"], ascending=[ascending, True], kind="stable").head(k)
        selections.append(take)
    return pd.concat(selections, ignore_index=True) if selections else frame.iloc[:0].copy()


def reversal_half(frame: pd.DataFrame, policy: str, minimum_candidates: int = 4) -> pd.DataFrame:
    """Secondary reversal-only challenger at identical half-population coverage."""
    feature, ascending = {
        "momentum_half": ("relative126", False),
        "context_risk_half": ("p_bad_loss", True),
        "price_risk_half": ("p_bad_loss_price", True),
        "expected_excess_half": ("expected_excess_net", False),
    }.get(policy, (None, None))
    if feature is None: raise ValueError("unknown reversal policy")
    if type(minimum_candidates) is not int or minimum_candidates < 1:
        raise ValueError("positive minimum count required")
    subset = frame[frame.state == "reversal_attempt"]
    _validate(subset, (feature,))
    selections = []
    for _, group in subset.groupby("decision_date", sort=True):
        if len(group) < minimum_candidates: continue
        k = int(np.ceil(len(group) / 2))
        selections.append(group.sort_values([feature, "industry"], ascending=[ascending, True], kind="stable").head(k))
    return pd.concat(selections, ignore_index=True) if selections else subset.iloc[:0].copy()


def calendar_paired_interval(a: pd.DataFrame, b: pd.DataFrame, metric: str,
                            replicates: int = 1000, seed: int = 20261114) -> dict:
    """Resample actual calendar-month blocks, including missing-month positions."""
    aa = a.groupby("decision_date")[metric].mean()
    bb = b.groupby("decision_date")[metric].mean()
    common = aa.index.intersection(bb.index)
    if len(common) == 0: return {"difference": None, "ci95": None, "months": 0}
    d = aa.loc[common] - bb.loc[common]
    d.index = d.index.to_period("M")
    if d.index.has_duplicates: raise ValueError("more than one decision date per month")
    full = pd.period_range(d.index.min(), d.index.max(), freq="M")
    values = d.reindex(full).to_numpy(float); n = len(values); block = 12
    out = {"difference": float(np.nanmean(values)), "months": len(common), "calendar_month_span": n,
           "interval_kind": "unadjusted_exploratory_12_calendar_month_moving_block"}
    if n < block: return out | {"ci95": None}
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, size=(replicates, int(np.ceil(n / block))))
    idx = (starts[:, :, None] + np.arange(block)).reshape(replicates, -1)[:, :n]
    sampled = values[idx]
    valid = np.isfinite(sampled).sum(axis=1)
    estimates = np.nansum(sampled, axis=1) / np.maximum(valid, 1)
    estimates = estimates[valid > 0]
    return out | {"ci95": np.quantile(estimates, [.025, .975]).tolist(), "usable_replicates": len(estimates)}
