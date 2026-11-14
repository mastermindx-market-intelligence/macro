"""Under the index: EMITTER_SPEC rev 2 / READER_STATE_RULE (2026-11-13).

Description only. Each panel owns its entire rolling history; no splicing,
forward outcomes, scoring, ranking, or index-return attribution.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Incumbent proxies: scripts/seed_us_sector_baskets.py. Never publish these keys.
SECTORS = {
    "XLB": "Materials", "XLE": "Energy", "XLF": "Financials",
    "XLI": "Industrials", "XLK": "Technology", "XLP": "Consumer Staples",
    "XLU": "Utilities", "XLV": "Health Care", "XLY": "Consumer Discretionary",
    "XLRE": "Real Estate", "XLC": "Communication Services",
}
NINE = tuple(SECTORS)[:9]
ELEVEN = tuple(SECTORS)
SWITCH_DATE = "2019-07-19"
METHOD = "counts sectors equally; not an attribution of the index's return"
LIMIT = ("Describes what is happening under the index today. "
         "It has not been shown to predict turns.")


@dataclass(frozen=True)
class Config:
    # EMITTER_SPEC rev 2: 25th/75th percentile of the nine-fund 21-session
    # rolling median of K, 2004-01-02..2023-12-29. Fixed full-precision cuts,
    # shared by both panels; never recompute live. Display only: .011 / .346.
    offsetting_low: float = 0.011158259853538948
    offsetting_high: float = 0.34622932464889694


def display_form(state: str, band: str) -> str:
    if state == "n/a" or band == "n/a":
        return "unavailable"
    if state in ("rising together", "quiet") and band in ("flat", "up"):
        return "compact"
    if state == "falling together" and band == "down":
        return "falling_with_index"
    return "full"


def offsetting_band(value: float, config: Config = Config()) -> str:
    if pd.isna(value):
        return "n/a"
    if value <= config.offsetting_low:
        return "almost none"
    if value > config.offsetting_high:
        return "more than usual"
    return "about usual"


def daily_fields(close: pd.DataFrame, index_close: pd.Series,
                 config: Config = Config()) -> pd.DataFrame:
    """Compute one panel on its union calendar, including warm-up rows.

    Inputs must be dividend-adjusted closes already cut to completed sessions.
    No filling of missing values. The caller chooses S9 or S11 before computing.
    Name columns are lists of sector names, never vendor/group keys.
    """
    if close.empty or not close.index.is_unique or not close.index.is_monotonic_increasing:
        raise ValueError("nonempty, unique, sorted panel required")
    if set(close.columns) - SECTORS.keys():
        raise ValueError("unknown sector proxy")
    close = close.where(np.isfinite(close) & (close > 0))
    index_close = index_close.reindex(close.index).where(lambda x: np.isfinite(x) & (x > 0))
    lc = np.log(close)
    r = lc - lc.shift(21)
    present = r.notna()
    n = present.sum(axis=1)
    up, down = (r > 0) & present, (r < 0) & present
    up_n, down_n = up.sum(axis=1), down.sum(axis=1)
    g = r.abs().sum(axis=1) / n.where(n > 0)
    u = r.clip(lower=0).sum(axis=1) / n.where(n > 0)
    loss = (-r.clip(upper=0)).sum(axis=1) / n.where(n > 0)
    k = 2 * np.minimum(u, loss) / g.where(g > 0)
    pct = g.rolling(1260, min_periods=252).rank(method="average", pct=True)
    need = np.ceil(0.75 * n)
    state = pd.Series(np.where(pct >= .16, "pulling apart", "quiet"), index=close.index)
    state[(up_n >= need) & (n > 0)] = "rising together"
    state[(down_n >= need) & (n > 0) & ~(up_n >= need)] = "falling together"
    state[(n == 0) | pct.isna()] = "n/a"
    high = close.rolling(252, min_periods=252).max()
    damage_present = close.notna() & high.notna()
    damaged = (close <= .90 * high) & damage_present
    ret = index_close / index_close.shift(21) - 1
    band = pd.Series(np.where(ret < -.02, "down", np.where(ret > .02, "up", "flat")),
                     index=close.index).where(ret.notna(), "n/a")
    median = k.rolling(21, min_periods=21).median()

    def names(mask):
        return mask.apply(lambda row: [SECTORS[c] for c in close.columns if row[c]], axis=1)

    result = pd.DataFrame({
        "index_gap_to_252_high": index_close / index_close.rolling(252, min_periods=252).max() - 1,
        "index_ret_21": ret, "index_band_21": band, "groups_N": n,
        "up_n": up_n, "down_n": down_n, "up_names": names(up), "down_names": names(down),
        "gross_motion_G21": g, "pct_G21": pct, "reader_state": state,
        "damaged_n": damaged.sum(axis=1), "damaged_of": damage_present.sum(axis=1),
        "damaged_names": names(damaged), "cancelled_share_K21": k,
        "cancelled_share_median_21": median,
    }, index=close.index)
    result["offsetting_band"] = median.map(lambda value: offsetting_band(value, config))
    result["display_form"] = [display_form(s, b) for s, b in zip(state, band)]
    for col, digits in (("index_gap_to_252_high", 6), ("index_ret_21", 6),
                        ("gross_motion_G21", 8), ("pct_G21", 8),
                        ("cancelled_share_K21", 6), ("cancelled_share_median_21", 6)):
        result[col] = result[col].round(digits)
    return result


def member_counts(prices: dict[str, pd.Series], members: list[str],
                  calendar: pd.DatetimeIndex, as_of: pd.Timestamp) -> dict:
    """Counts only; missing/full-window-ineligible members remain in total."""
    near, deep, eligible = 0, 0, 0
    for ticker in set(members):
        series = prices.get(ticker)
        if series is None:
            continue
        values = series.reindex(calendar).loc[:as_of].tail(252)
        if len(values) != 252 or not (np.isfinite(values) & (values > 0)).all():
            continue
        eligible += 1
        gap = values.iloc[-1] / values.max() - 1
        near += int(gap >= -.05)
        deep += int(gap <= -.20)
    return {"within_5pct_high": near, "at_least_20pct_below_high": deep,
            "member_total": len(set(members)), "eligible_members": eligible}
