"""Close-to-close breadth on the existing heatmap cohort and US session calendar.

The cohort is today's classified snapshot. The six historical daily readings are
a reconstruction on identical names, never a historical membership or flow claim.
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from engine.spotlight import GICS_TO_ETF
from lib.us_cash_calendar import is_session, sessions_between


def sector_breadth(closes, tiles, asof):
    """Return a small count series; missing exact observations are never carried."""
    if not isinstance(closes, pd.DataFrame) or closes.empty or not asof:
        return None
    index = closes.index
    if (not isinstance(index, pd.DatetimeIndex) or index.hasnans or not index.is_unique
            or not closes.columns.is_unique or not index.equals(index.normalize())):
        return None
    day = pd.Timestamp(asof).date()
    if not is_session(day):
        return None
    # Seven exchange sessions produce six separate 1D return observations.
    dates = sessions_between(day - timedelta(days=21), day)[-7:]
    if len(dates) != 7:
        return None
    by_day = closes.set_axis(index.date)
    if not by_day.index.is_unique:
        return None
    frame = by_day.reindex(dates)
    symbols = [row["t"] for row in tiles]
    if len(set(symbols)) != len(symbols):
        return None
    # The heatmap can mix primary and GICS fallback labels in the same snapshot.
    # Every tile must have exactly one home before any sector is ranked.
    groups = {ticker: [] for ticker in sorted(set(GICS_TO_ETF.values()))}
    for tile in tiles:
        ticker = GICS_TO_ETF.get(tile["sector"])
        if ticker is None:
            return None
        groups[ticker].append(tile["t"])
    rows = {}
    for ticker, members in groups.items():
        values = frame.reindex(columns=members).apply(pd.to_numeric, errors="coerce")
        # Reject bad or absent closes throughout the full comparison window.
        usable = values.loc[:, (np.isfinite(values) & (values > 0)).all(axis=0)]
        delta = usable.diff().iloc[1:]
        rows[ticker] = {
            "eligible": len(members),
            "matched": len(usable.columns),
            "advancing": (delta > 0).sum(axis=1).astype(int).tolist(),
            "declining": (delta < 0).sum(axis=1).astype(int).tolist(),
        }
    return {"schema": "sector_breadth_close.v1", "basis": "current_cohort_daily_closes",
            "dates": [d.isoformat() for d in dates[1:]], "sectors": rows}
