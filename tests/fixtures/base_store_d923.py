"""Exact pre-extraction store functions retained solely for behavior comparisons.

Source: mastermindx-market-intelligence/macro at d9236cdb6a8c64e4543cf93d2f537b7b11400812,
lib/store.py. Functions are verbatim; tests inject only their existing IO boundaries.
"""
from __future__ import annotations
import logging
import pandas as pd
log = logging.getLogger(__name__)
BASE_SOURCE_SHA256 = '14907e9d2bd6e7ae6498a7cdd3f28a5764433114d10c50681828446ce7764413'

def upsert(group: str, name: str, new: pd.DataFrame, outlier_col: str | None = None,
           normalize_index: bool = True, overwrite_overlap: bool = False) -> pd.DataFrame:
    """Merge new rows into the stored series. New values win on date collision;
    The default path keeps rows present only on disk (append-only history).
    normalize_index=False preserves intraday timestamps (hourly candles).

    overwrite_overlap=True — for DIVIDEND/SPLIT-ADJUSTED series (yfinance
    auto_adjust=True). An adjusted history is a coherent whole: after an ex-dividend
    every prior bar is re-scaled, so a fresh pull's values for the overlapping window
    are the corrected truth and the stored ones are stale. Plain combine_first keeps
    old values wherever the fresh pull did not re-cover them, leaving a PERMANENT basis
    STEP at the refresh edge (measured 17/300 A-share names >0.4%, worst 40%, May-dividend
    clustered) that seasonally biases rev_z and can fabricate MACD/StochRSI crosses.
    With overwrite_overlap=True the fresh pull FULLY OVERWRITES its own date span
    [new.index.min(), new.index.max()]; only stored rows OUTSIDE that span (older deep
    history the short refresh window did not reach) are carried forward. A response
    that does not reach the stored latest timestamp, or becomes empty after outlier
    filtering, is rejected with ValueError before writing. Retain the whole known-good
    cache rather than splice a stale adjustment basis against newer stored rows.
    Reaching that timestamp still allows complete overlap replacement, including
    omitted interior bars. See research/ENGINE_FIX_MASTERPLAN.md §W6-CN fix 2."""
    if new is None or new.empty:
        raise ValueError(f"upsert called with empty frame for {group}/{name}")
    new = new.copy()
    new.index = pd.to_datetime(new.index)
    if normalize_index:
        new.index = new.index.normalize()
    new = new[~new.index.duplicated(keep="last")].sort_index()

    old = read(group, name)
    if old is not None and not old.empty and outlier_col and outlier_col in new.columns:
        new = _guard_outliers(group, name, old, new, outlier_col)

    if old is None or old.empty:
        merged = new
    elif overwrite_overlap:
        # A closure-time/throttled response may end before the last stored bar.
        # Keeping its changed adjustment window alongside newer old bars would mix
        # bases; deleting those newer bars would regress the cache. Reject both.
        if new.empty:
            raise ValueError(
                f"empty overwrite_overlap frame after filtering for {group}/{name}; "
                "retained complete stored history")
        if new.index.max() < old.index.max():
            raise ValueError(
                f"stale overwrite_overlap frame for {group}/{name}: latest returned "
                f"{new.index.max()} precedes stored {old.index.max()}; "
                "retained complete stored history to avoid mixing adjustment bases")
        # Keep only stored rows strictly OLDER than the fresh pull's window; the fresh
        # pull owns its whole overlapping span (no combine_first seam).
        lo = new.index.min()
        kept_old = old[old.index < lo]
        merged = (pd.concat([kept_old, new]) if not kept_old.empty else new)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    else:
        merged = new.combine_first(old)  # new wins where both exist; old-only rows kept
        merged = merged.sort_index()

    merged.to_parquet(_path(group, name))
    return merged

def basis_shifted(group: str, name: str, new: pd.DataFrame, col: str = "close",
                  tol: float = 1e-3) -> bool:
    """True when a freshly fetched refresh window sits on a DIFFERENT adjustment
    basis than the stored series — the signature of a dividend/split between
    fetches. yfinance re-adjusts the WHOLE series at every fetch, so splicing a
    short re-based window onto stored history strands every pre-window row on a
    stale basis: seam-crossing returns/SMAs go silently wrong and an unnoticed
    split is a 10x level step (measured: data/yahoo/SPY.parquet uniformly
    +0.2576% off a fresh fetch on all 8,382 rows before 2026-05-18 — exactly one
    dividend of drift). Note upsert(overwrite_overlap=True) cannot fix this
    class: it makes the fresh pull own its OWN span but never touches rows older
    than the window.

    Compares ``col`` on the overlap dates; a relative diff > ``tol`` is a shift.
    NO overlap at all (stored series ended before the window starts) also
    returns True — the basis is unverifiable and a splice would leave a bar gap.
    False when nothing is stored yet (fresh name — nothing to corrupt). Never
    raises: on a comparison error it logs and returns False (old splice
    behavior). Callers respond by discarding the window and refetching
    period='max' for the flagged name — ported from the odds-store guard in
    scripts/build_odds.ensure_store."""
    try:
        old = read(group, name)
        if old is None or old.empty or col not in old.columns or col not in new.columns:
            return False
        oc = old[col].dropna()
        nc = new[col].dropna()
        if oc.empty or nc.empty:
            return False
        idx = pd.to_datetime(nc.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        nc = pd.Series(nc.to_numpy(), index=idx.normalize())
        nc = nc[~nc.index.duplicated(keep="last")]
        overlap = oc.index.intersection(nc.index)
        if len(overlap) == 0:
            log.info("basis guard %s/%s: no overlap between the refresh window and "
                     "stored history — full refetch required", group, name)
            return True
        oc = oc.loc[overlap].astype(float)
        nv = nc.loc[overlap].astype(float)
        rel = (oc - nv).abs() / nv.abs().clip(lower=1e-9)
        worst = float(rel.max())
        if worst > tol:
            log.info("basis guard %s/%s: adjustment basis shifted (max overlap diff "
                     "%.4f%% over %d dates)", group, name, worst * 100.0, len(overlap))
            return True
        return False
    except Exception as e:  # noqa: BLE001 — a guard must never kill the collect
        log.warning("basis guard %s/%s: comparison failed (%s) — treating as unshifted",
                    group, name, e)
        return False
