"""Daily short-volume signal — a CONTEXT confirmer derived from the keyless FINRA
daily short-sale volume panel (collectors/finra_short_volume.py).

For each ticker we compare a short window (default last 5 sessions) against a
baseline window (default last 20) of volume-weighted short ratio
(sum ShortVolume / sum TotalVolume). `trend_pp` = recent - baseline, in
percentage points: positive = off-exchange short flow building *recently* vs the
trailing norm — a fresher read than the bi-monthly short-interest settlement.

`ratio_z` = (latest short_ratio − mean) / std over ALL available history, using
the same formula as build_darkpool_desk.py (nanmean / nanstd, min 5 rows, 0.0
when sigma is zero). Surfaces on the per-stock page as context only.

Honest framing: daily short-volume is noisy and its standalone edge is
modest/contested, so this is surfaced as a positioning confirmer on the stock
page, NOT folded into any scored alpha factor. Pure + import-light so it stays
trivially testable.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from lib import config

log = logging.getLogger(__name__)

_PANEL = ("finra_short_volume", "panel.parquet")
_REQUIRED = {"date", "ticker", "short_vol", "total_vol"}

# C19 WP24 DQ3 consumer states. A missing panel, an unreadable panel and an empty
# panel all used to collapse into the same None; these keep them distinct so a
# reader can tell "nothing published" from "file broken" from "no rows".
OBSERVED = "observed"
OBSERVED_ZERO = "observed_zero"
NO_OBSERVATION = "no_observation"
PARTIAL = "partial"
PARSE_ERROR = "parse_error"
UNAVAILABLE = "unavailable"
CENSORED_LOWER_BOUND = "censored_lower_bound"

# FINRA short-interest days-to-cover at/above this is the 999.99 "average daily
# volume ~0" sentinel: a censored lower bound, never a measurement. Mirrors
# collectors/finra.py DTC_SENTINEL (kept separate so engine consumers never pull
# the collector into their import closure).
DTC_SENTINEL = 999.0


def panel_state(path=None) -> tuple[pd.DataFrame | None, str]:
    """(panel, state). The panel is non-None only when state is OBSERVED."""
    p = path or (config.data_dir() / _PANEL[0] / _PANEL[1])
    if not p.exists():
        return None, UNAVAILABLE
    try:
        df = pd.read_parquet(p)
    except Exception as e:  # noqa: BLE001
        log.warning("short_volume: panel unreadable %s (%s)", p, e)
        return None, PARSE_ERROR
    if not _REQUIRED <= set(df.columns):
        log.warning("short_volume: panel %s missing columns %s", p,
                    sorted(_REQUIRED - set(df.columns)))
        return None, PARSE_ERROR
    if df.empty:
        return None, NO_OBSERVATION
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df, OBSERVED


def load_panel(path=None) -> pd.DataFrame | None:
    return panel_state(path)[0]


def ticker_state(sig: dict | None, *, baseline: int = 20) -> str:
    """State of one signal_map() entry: NO_OBSERVATION when the ticker produced no
    signal, PARTIAL when its history is shorter than the baseline window or too
    thin for a z-score, OBSERVED_ZERO when the recent window shorted nothing."""
    if not sig:
        return NO_OBSERVATION
    if sig.get("n_days", 0) < baseline or sig.get("ratio_z") is None:
        return PARTIAL
    if sig.get("ratio_recent") == 0:
        return OBSERVED_ZERO
    return OBSERVED


def _ticker_signal(g: pd.DataFrame, recent: int, baseline: int) -> dict | None:
    g = g.sort_values("date")
    if len(g) < 3:
        return None
    base = g.tail(baseline)
    rec = g.tail(recent)

    def _vw(frame: pd.DataFrame) -> float | None:
        tot = float(frame["total_vol"].sum())
        return round(float(frame["short_vol"].sum()) / tot, 4) if tot > 0 else None

    vw_base = _vw(base)
    vw_rec = _vw(rec)
    latest = g.iloc[-1]
    if vw_base is None or vw_rec is None:
        return None

    # Short ratio for z-score: use pre-computed column if available, else vw_rec
    has_col = "short_ratio" in g.columns and pd.notna(latest.get("short_ratio"))
    short_ratio_latest = float(latest["short_ratio"]) if has_col else vw_rec

    # Z-score vs own full history — same definition as build_darkpool_desk.py:
    # nanmean/nanstd over ALL rows, min 5 rows, 0.0 when sigma is zero.
    if has_col and len(g) >= 5:
        ratios = g["short_ratio"].values
        mu = float(np.nanmean(ratios))
        sigma = float(np.nanstd(ratios))
        ratio_z = round((short_ratio_latest - mu) / sigma, 2) if sigma > 0 else 0.0
    else:
        ratio_z = None

    return {
        "short_ratio": round(short_ratio_latest, 4),
        "ratio_recent": vw_rec,
        "ratio_baseline": vw_base,
        "trend_pp": round((vw_rec - vw_base) * 100, 2),
        "ratio_z": ratio_z,
        "n_days": int(len(g)),
        "asof": str(latest["date"].date()),
    }


def signal_map(panel: pd.DataFrame | None = None, *, recent: int = 5,
               baseline: int = 20) -> dict[str, dict]:
    """{ticker: {short_ratio, ratio_recent, ratio_baseline, trend_pp, ratio_z, n_days, asof}}.
    Empty dict when the panel is missing — callers degrade gracefully."""
    if panel is None:
        panel = load_panel()
    if panel is None or panel.empty:
        return {}
    out: dict[str, dict] = {}
    for tk, g in panel.groupby("ticker"):
        sig = _ticker_signal(g, recent, baseline)
        if sig is not None:
            out[str(tk)] = sig
    return out
