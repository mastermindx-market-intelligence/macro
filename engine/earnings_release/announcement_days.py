"""Collapse same-day Item-2.02 filings to one row per (ticker, filing_date) for consumers.

The EDGAR earnings store retains every filing per (cik, accession). Multiple 8-K / 8-K/A
rows on one announcement day are collapsed here — never in the store. The earliest
SEC acceptance timestamp represents that day; empty or missing acceptance sorts last.
"""
from __future__ import annotations

import pandas as pd

_ACCEPTANCE_SENTINEL = "9999-99-99"


def _acceptance_sort_key(df: pd.DataFrame) -> pd.Series:
    if "acceptance_datetime" not in df.columns:
        return pd.Series(_ACCEPTANCE_SENTINEL, index=df.index, dtype=object)
    s = df["acceptance_datetime"]
    key = s.where(s.notna(), "").astype(str)
    key = key.replace("nan", _ACCEPTANCE_SENTINEL).replace("None", _ACCEPTANCE_SENTINEL)
    key = key.mask(key == "", _ACCEPTANCE_SENTINEL)
    return key


def announcement_days(df: pd.DataFrame) -> pd.DataFrame:
    """One announcement day per (ticker, filing_date); earliest acceptance wins.

    The store keeps every filing; consumers call this helper to avoid double-counting
    same-day 8-K and 8-K/A rows. Idempotent and does not mutate the input frame.
    """
    if df.empty or not {"ticker", "filing_date"} <= set(df.columns):
        return df

    out = df.copy()
    sort_key = _acceptance_sort_key(out)
    out = out.assign(_announcement_days_sort_key=sort_key)
    out = out.sort_values(
        ["ticker", "filing_date", "_announcement_days_sort_key"],
        kind="mergesort",
    )
    out = out.drop_duplicates(["ticker", "filing_date"], keep="first")
    out = out.drop(columns=["_announcement_days_sort_key"])
    return out
