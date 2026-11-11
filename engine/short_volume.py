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
    """File-read state plus retained rows. OBSERVED means a readable container;
    in-memory _pair_state flags qualify individual numeric observations without
    discarding other tickers or changing the stored panel schema.
    """
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
    try:
        return _qualify_panel(df), OBSERVED
    except (ValueError, TypeError, OverflowError) as e:
        log.warning("short_volume: panel calendar unreadable %s (%s)", p, e)
        return None, PARSE_ERROR


def load_panel(path=None) -> pd.DataFrame | None:
    return panel_state(path)[0]


def ticker_state(sig: dict | None, *, baseline: int = 20) -> str:
    """State of one signal_map() entry: NO_OBSERVATION when the ticker produced no
    signal, PARTIAL when its history is shorter than the baseline window or too
    thin for a z-score, OBSERVED_ZERO when the recent window shorted nothing."""
    if not sig:
        return NO_OBSERVATION
    states = {c["state"] for c in sig.get("coverage", {}).values()}
    for state in (PARSE_ERROR, UNAVAILABLE, NO_OBSERVATION):
        if state in states:
            return state
    if sig.get("n_days", 0) < baseline or sig.get("ratio_z") is None:
        return PARTIAL
    if sig.get("ratio_recent") == 0 and not sig.get("_recent_nonzero", False):
        return OBSERVED_ZERO
    return OBSERVED


def _numeric(frame: pd.DataFrame, column: str) -> np.ndarray:
    return pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float, na_value=np.nan)


def _qualify_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Retain every row and raw operand; qualify each pair before any slicing."""
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if frame["date"].isna().any():
        raise ValueError("missing observation date")
    short, total = _numeric(frame, "short_vol"), _numeric(frame, "total_vol")
    short_missing = frame["short_vol"].isna().to_numpy()
    total_missing = frame["total_vol"].isna().to_numpy()
    # Missingness is recorded BEFORE coercion; a bad string is invalid, not absent.
    # An independently invalid operand wins even when its counterpart is missing.
    invalid = ((~short_missing & (~np.isfinite(short) | (short < 0)))
               | (~total_missing & (~np.isfinite(total) | (total < 0)))
               | (np.isfinite(short) & np.isfinite(total) & (short > total)))
    missing = ~invalid & (short_missing | total_missing | ((short == 0) & (total == 0)))
    states = np.full(len(frame), OBSERVED, dtype=object)
    states[missing], states[invalid] = NO_OBSERVATION, PARSE_ERROR
    frame["_pair_state"] = states
    return frame


def _scope_coverage(frame: pd.DataFrame, *, stored: bool = False) -> dict | None:
    """Admission for one original calculation slice, never a complete-case slice.

    Optional stored-ratio absence preserves the existing nan-aware estimator.
    Nonmissing cached ratios must be finite, bounded and consistent with their
    pair within the producer's four-decimal quantization (half a unit plus slack).
    """
    invalid = frame["_pair_state"].eq(PARSE_ERROR).to_numpy()
    missing = frame["_pair_state"].eq(NO_OBSERVATION).to_numpy()
    reason = "paired_operands"
    if not (invalid.any() or missing.any()) and stored:
        ratios = _numeric(frame, "short_ratio")
        expected = _numeric(frame, "short_vol") / _numeric(frame, "total_vol")
        present = frame["short_ratio"].notna().to_numpy()
        invalid = present & (~np.isfinite(ratios) | (ratios < 0) | (ratios > 1)
                             | (np.abs(ratios - expected) > 0.00005 + 1e-12))
        reason = "stored_ratio"
    n_invalid, n_missing = int(invalid.sum()), int(missing.sum())
    if not (n_invalid or n_missing):
        return None
    state = (PARSE_ERROR if n_invalid else
             NO_OBSERVATION if n_missing == len(frame) else UNAVAILABLE)
    return {"state": state, "reason": reason, "n_rows": int(len(frame)),
            "n_missing": n_missing, "n_invalid": n_invalid}


def _ticker_signal(g: pd.DataFrame, recent: int, baseline: int) -> dict | None:
    g = g.sort_values("date")
    if len(g) < 3:
        return None
    base = g.tail(baseline)
    rec = g.tail(recent)
    if base.empty or rec.empty:
        return None
    coverage: dict[str, dict] = {}

    def qualify(scope: str, frame: pd.DataFrame, *, stored: bool = False) -> bool:
        result = _scope_coverage(frame, stored=stored)
        if result is not None:
            coverage[scope] = result
            return False
        return True

    def _vw(scope: str, frame: pd.DataFrame) -> float | None:
        if not qualify(scope, frame):
            return None
        short, total = _numeric(frame, "short_vol"), _numeric(frame, "total_vol")
        # Keep ordinary arithmetic byte-compatible. Scale only if individually
        # finite, admitted volumes overflow their sums; this is the same VW ratio.
        with np.errstate(over="ignore", invalid="ignore"):
            numerator, denominator = float(short.sum()), float(total.sum())
        if not (np.isfinite(numerator) and np.isfinite(denominator)):
            scale = float(total.max())
            numerator, denominator = float((short / scale).sum()), float((total / scale).sum())
        return round(numerator / denominator, 4)

    vw_base = _vw("baseline", base)
    vw_rec = _vw("recent", rec)
    latest = g.iloc[-1]

    # Short ratio for z-score: use pre-computed column if available, else vw_rec
    has_col = "short_ratio" in g.columns and pd.notna(latest.get("short_ratio"))
    latest_ok = qualify("latest", g.tail(1), stored=has_col)
    short_ratio_latest = (float(latest["short_ratio"]) if has_col else vw_rec) if latest_ok else None
    if latest_ok and not has_col and vw_rec is None:
        # The legacy displayed-ratio fallback depends on the recent window.
        coverage["latest"] = dict(coverage["recent"])

    # Z-score vs own full history — same definition as build_darkpool_desk.py:
    # nanmean/nanstd over ALL rows, min 5 rows, 0.0 when sigma is zero.
    if has_col and len(g) >= 5 and qualify("history_z", g, stored=True):
        ratios = _numeric(g, "short_ratio")
        mu = float(np.nanmean(ratios))
        sigma = float(np.nanstd(ratios))
        ratio_z = round((short_ratio_latest - mu) / sigma, 2) if sigma > 0 else 0.0
    else:
        ratio_z = None

    result = {
        "short_ratio": round(short_ratio_latest, 4) if short_ratio_latest is not None else None,
        "ratio_recent": vw_rec,
        "ratio_baseline": vw_base,
        "trend_pp": round((vw_rec - vw_base) * 100, 2) if vw_rec is not None and vw_base is not None else None,
        "ratio_z": ratio_z,
        "n_days": int(len(g)),
        "asof": str(latest["date"].date()),
    }
    if coverage:
        result["coverage"] = coverage
    if vw_rec == 0 and (_numeric(rec, "short_vol") > 0).any():
        # Rounded-positive is not measured zero. This internal bit is not projected
        # into positioning; ordinary healthy and genuine-zero payloads stay exact.
        result["_recent_nonzero"] = True
    return result


def signal_map(panel: pd.DataFrame | None = None, *, recent: int = 5,
               baseline: int = 20) -> dict[str, dict]:
    """{ticker: {short_ratio, ratio_recent, ratio_baseline, trend_pp, ratio_z, n_days, asof}}.
    Empty dict when the panel is missing — callers degrade gracefully."""
    if panel is None:
        panel = load_panel()
    if panel is None or panel.empty:
        return {}
    panel = _qualify_panel(panel)
    out: dict[str, dict] = {}
    for tk, g in panel.groupby("ticker"):
        sig = _ticker_signal(g, recent, baseline)
        if sig is not None:
            out[str(tk)] = sig
    return out
