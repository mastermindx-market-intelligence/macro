"""Literal original owner at 84f1b7287c8f7298e502eb67949f01ee7c40ef1e."""
import pandas as pd
from lib import config
_BREADTH_DIR = {"us": "breadth", "china": "china_breadth", "hk": "hk_breadth", "canada": "canada_breadth", "intl": "intl_breadth"}

def _acquire_earnings_calendar(panel: dict) -> dict:
    """READ-ONLY acquisition of the near-earnings chip's calendar.

    Display-only (MLC-R10): never gates, orders, or scores any basket. Fail-open: an
    absent/stale store simply leaves near_earnings_count absent from the payload. The
    freshness window is measured against the PANEL session, never a wall clock.
    """
    out: dict = {}
    try:
        idx = panel["idx"]
        today = idx.max().date()
        earn_path = config.data_dir() / "earnings" / "earnings.parquet"
        if earn_path.exists():
            import pandas as _pd_w5
            earn_df = _pd_w5.read_parquet(earn_path)
            # Only use the store if as_of is within 10 trading days (mirrors earn_blackout SLA)
            earn_as_of_col = earn_df.get("as_of") if hasattr(earn_df, "get") else None
            earn_fresh = False
            if earn_as_of_col is not None and not earn_as_of_col.empty:
                earn_most_recent = _pd_w5.Timestamp(str(earn_as_of_col.dropna().max()))
                if earn_most_recent.tzinfo is not None:
                    earn_most_recent = earn_most_recent.tz_convert(None)
                age_cal = (_pd_w5.Timestamp(today) - earn_most_recent).days
                earn_fresh = age_cal <= 14  # generous: 2 calendar weeks
            if earn_fresh:
                for tk, row in earn_df.iterrows():
                    nd = row.get("next_date") if hasattr(row, "get") else None
                    if nd and str(nd) not in ("", "nan", "None"):
                        out[str(tk).upper()] = str(nd)[:10]
    except Exception:  # noqa: BLE001 — tripwire-level; earnings chip must never crash the desk
        out = {}
    return out
