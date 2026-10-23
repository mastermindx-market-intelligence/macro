#!/usr/bin/env python3
"""Optional OHLC retention candidate at the incumbent extraction seam only."""
import pandas as pd

from contract import opening_refusal


def retain_optional_ohlcv(frame, ticker):
    names = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    try:
        sub = frame[ticker] if isinstance(frame.columns, pd.MultiIndex) else frame
        sub[["Close", "Volume"]]
        observed = sub[[column for column in names if column in sub]].rename(columns=names).dropna(subset=["close"]).copy()
    except KeyError:
        return None, {"status": "MISSING_REQUIRED_COLUMN"}
    if observed.empty:
        return None, {"status": "NO_CLOSE_ROWS"}
    refused = []
    # iterrows constructs a Series and can itself overflow on a hostile optional
    # Python integer before our scalar validator runs. Tuples preserve scalars.
    columns = list(observed.columns)
    for values in observed.itertuples(index=True, name=None):
        day, row = values[0], dict(zip(columns, values[1:]))
        reason = opening_refusal(row)
        if reason:
            refused.append({"session": str(pd.Timestamp(day).date()), "reason": reason})
    return observed, {"status": "OBSERVATIONS_RETAINED", "opening_mark_refusals": refused,
                      "qualified_open_rows": len(observed) - len(refused)}
