"""engine/basket_index.py — the consolidated ETF-like CANDLE for a thematic basket.

The baskets page already builds an equal-weight close LEVEL per basket (engine.baskets
._ew_level). That is the consolidated index's close, but it carries no intraday range and
no volume, so it can't feed the technical/flow engines that need a real candle (ATR /
Bollinger vol-hole, whale accumulation, Chaikin money-flow). This module builds the full
basket CANDLE — open/high/low/close + traded dollar-volume — from the deep per-member
OHLCV store (data/baskets/ohlcv, fetched by scripts/fetch_basket_ohlcv), with point-in-time
dated membership and a choice of weighting.

CONSTRUCTION (return-space, so it reduces EXACTLY to _ew_level when mode="equal"):
  • per member, daily close-to-close return r_i(t), and intraday range returns measured off
    the PRIOR close: open/high/low_ret_i(t) = open/high/low_i(t)/close_i(t-1) − 1;
  • a member is live only within [added, removed); weights are renormalised over the live set
    each day (so an entry/exit rebalances exactly like the EW level);
  • basket close return R(t) = Σ w_i(t)·r_i(t) → close level = cumprod(1+R) from 1.0;
    the basket high/low/open levels = prior close level × (1 + weighted range return), which
    keeps high ≥ close ≥ low bar-by-bar (the weighting preserves the per-member ordering);
  • dollar-volume(t) = Σ_live close_i(t)·volume_i(t) — the basket's true traded dollars (raw
    share volume is meaningless across different-priced names; dollars are the right unit and
    the right weight for the money-flow math downstream).

WEIGHTING modes (the user's "equal weighted, or weighted as you think"):
  • "equal"     — 1/n_live(t); the honest default and the SCORED baseline.
  • "relevance" — by an explicit member `weight` (membership.json) else the per-stock
    Conviction score (passed in as conv_map); a higher-conviction / more on-thesis name
    carries more of the index. Static weights, renormalised over the live set.
  • "alpha"     — tilt by each member's trailing risk-adjusted relative strength (60d return
    over realised vol vs the basket); capped. DISPLAY/EXPLORATORY — a directional bet on
    close-only momentum with ~0 validated cross-sectional edge (house finding), so never the
    scored baseline.

HONEST BY CONSTRUCTION: like the baskets themselves the membership is ~hindsight-curated, so
this is a descriptive consolidated tape, not an out-of-sample backtest. Coverage is reported
(n_live / n_with_ohlcv) so a thin pull degrades visibly rather than silently.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lib import config, store as data_store

log = logging.getLogger(__name__)

OHLCV_COLS = ["open", "high", "low", "close", "volume"]
ALPHA_CAP = 2.0            # alpha-tilt weight is capped at this × the equal weight
ALPHA_LOOKBACK = 120       # trailing days of risk-adjusted strength for the alpha tilt
ALPHA_REBAL = "MS"         # POINT-IN-TIME rebalance grid (month-start) — a strength
                           # vector is recomputed from data up to each rebalance and
                           # held forward, so no future ranking ever reweights the past
_STALE_TAIL_GRACE = 5      # bars a member may ride the ffill past its last real bar
                           # before it exits the live set (suspension/holiday tolerance)
_CACHE: dict[str, pd.DataFrame | None] = {}


def _alpha_strength(seg: pd.DataFrame) -> pd.Series:
    """Risk-adjusted trailing strength → capped softmax-ish tilt weight per column,
    from a return window `seg` (already restricted to each member's live days).
    Shared by the point-in-time grid so the tilt math has one definition."""
    mu = seg.mean()
    sd = seg.std().replace(0, np.nan)
    strength = (mu / sd).replace([np.inf, -np.inf], np.nan)
    sstd = strength.std()
    denom = sstd if (sstd and np.isfinite(sstd)) else 1.0        # no spread → equal
    z = (strength - strength.mean()) / denom
    w = np.exp(np.clip(z.fillna(0.0), -1.5, 1.5))                # softmax-ish tilt
    return (w / w.mean()).clip(1.0 / ALPHA_CAP, ALPHA_CAP)       # capped vs equal


def _alpha_weights_pit(present: list[str], ret: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """POINT-IN-TIME alpha tilt: a DAILY weight matrix (idx × present). On each
    monthly rebalance the trailing-ALPHA_LOOKBACK strength is recomputed using ONLY
    returns up to that date, then held forward to the next rebalance. This replaces
    the old single as-of-today vector that was applied across ALL history (audit #44:
    today's momentum leaders over-weighted through their entire past — undisclosed
    look-ahead). Before the first full lookback window the tilt is equal (1.0)."""
    idx = ret.index
    rr = ret[present].where(mask)
    W = pd.DataFrame(1.0, index=idx, columns=present)            # equal until first rebal
    rebal_dates = pd.date_range(idx.min(), idx.max(), freq=ALPHA_REBAL)
    for rb in rebal_dates:
        pos = idx.searchsorted(rb, side="right")                # strictly-past window end
        if pos < ALPHA_LOOKBACK:
            continue                                            # not enough history yet
        seg = rr.iloc[pos - ALPHA_LOOKBACK:pos]                 # data KNOWN at the rebalance
        w = _alpha_strength(seg).reindex(present).fillna(1.0)
        # apply from this rebalance forward (until the next one overwrites it)
        W.iloc[pos:] = w.to_numpy()
    return W


def _parquet_last_date(path) -> pd.Timestamp | None:
    """Last index date of a per-ticker parquet WITHOUT reading any data column —
    ``pd.read_parquet(path, columns=[])`` loads only the index (the
    engine/hk_freshness probe idiom), so probing a fallback's recency costs ~1ms
    on the render path instead of a full 5-column read. None on empty / non-date
    index / any error — the caller treats None as "no opinion, skip the guard"."""
    try:
        idx = pd.DatetimeIndex(pd.read_parquet(path, columns=[]).index)
        if not len(idx):
            return None
        if idx.tz is not None:              # must compare cleanly with a naive deep tape
            idx = idx.tz_localize(None)
        last = idx.max()
        return None if pd.isna(last) else last
    except Exception:  # noqa: BLE001
        return None


def _splice_fresher_tail(ticker: str, deep: pd.DataFrame, fresh: pd.DataFrame,
                         store: str = "data/stocks") -> pd.DataFrame:
    """Append a FRESHER fallback store's tail onto a stale deep-store tape. The tail is
    ratio-rescaled at the last shared bar so an adjustment-basis mismatch between the
    two stores can't manufacture a seam return; volume passes through unscaled.
    Returns `deep` unchanged when it is already current (the common case)."""
    if deep.empty or fresh.empty or "close" not in deep.columns or "close" not in fresh.columns:
        return deep
    deep = deep.copy()
    deep.index = pd.DatetimeIndex(deep.index)
    fresh = fresh.copy()
    fresh.index = pd.DatetimeIndex(fresh.index)
    # tz-strip both tapes — a tz-aware store vs a naive one must seam-compare and
    # concat instead of raising (a raise here would skip the heal, not just a row)
    if deep.index.tz is not None:
        deep.index = deep.index.tz_localize(None)
    if fresh.index.tz is not None:
        fresh.index = fresh.index.tz_localize(None)
    fresh = fresh[~fresh.index.duplicated(keep="last")].sort_index()
    if fresh.index.max() <= deep.index.max():
        return deep
    for c in ("open", "high", "low"):
        if c not in fresh.columns:
            fresh[c] = fresh["close"]
    tail = fresh[fresh.index > deep.index.max()]
    if tail.empty:
        return deep
    common = deep.index.intersection(fresh.index)
    if not len(common):
        # Without a matched price observation, the bases are unrelated; joining
        # the two series at factor=1 would fabricate a seam return.
        log.warning("basket member %s: newer %s lacks a shared price anchor; skip tail",
                    ticker, store)
        return deep
    try:
        d = common.max()
        dc, fc = float(deep.loc[d, "close"]), float(fresh.loc[d, "close"])
    except (KeyError, TypeError, ValueError):
        return deep
    if not (np.isfinite(dc) and np.isfinite(fc) and dc > 0 and fc > 0):
        log.warning("basket member %s: newer %s has no valid shared price; skip tail",
                    ticker, store)
        return deep
    factor = dc / fc
    tail = tail.copy()
    px = [c for c in ("open", "high", "low", "close") if c in tail.columns]
    tail[px] = tail[px] * factor
    log.warning("basket member %s: deep OHLCV stale (ends %s) — spliced %d fresher rows "
                "from %s", ticker, deep.index.max().date(), len(tail), store)
    return pd.concat([deep, tail])


def _load_member_ohlcv(ticker: str) -> pd.DataFrame | None:
    """Per-member OHLCV, preferring the deep baskets store, then data/stocks (already OHLCV),
    then the China A-share store (data/china_stocks, .SS/.SZ tickers — close/high/low/volume, no
    open), then the yahoo store (close+volume → high/low/open synthesised as the close). Cached.
    The china_stocks fallback never collides with the US stores (A-share tickers carry a .SS/.SZ
    suffix), so it makes the basket machinery China-capable without touching the US path.
    Deep store preferred, but all existing fallback stores are recency-probed
    (index-only read); the freshest usable tail wins, preserving provider order
    on equal timestamps. A stale/empty deep tape is healed without misdating it."""
    runtime_frame = data_store.read_runtime_history("yahoo", ticker)
    if runtime_frame is not None:
        # Preserve the existing Yahoo close-only candle representation, but use
        # this verified generation before any global cache or fallback store.
        for column in ("open", "high", "low"):
            if column not in runtime_frame.columns:
                runtime_frame[column] = runtime_frame["close"]
        if "volume" not in runtime_frame.columns:
            runtime_frame["volume"] = np.nan
        return runtime_frame[OHLCV_COLS].copy(deep=True)
    if ticker in _CACHE:
        return _CACHE[ticker]
    out: pd.DataFrame | None = None
    bp = config.data_dir() / "baskets" / "ohlcv" / f"{ticker}.parquet"
    sp = config.data_dir() / "stocks" / f"{ticker}.parquet"
    cp = config.data_dir() / "china_stocks" / f"{ticker}.parquet"
    yp = config.data_dir() / "yahoo" / f"{ticker}.parquet"
    try:
        if bp.exists():
            df = pd.read_parquet(bp)
            if len(df):
                out = df
                # 2026-07 staleness audit (#2697/#2698): the nightly deep-store refresh
                # covers only the NDX/Russell finviz lists, so a membership-only name can
                # freeze (522 tickers ended 06-29) and SHADOW a fresher fallback tape.
                # The probe is an INDEX-ONLY read (columns=[], the hk_freshness idiom):
                # the all-fresh common case costs no second full parquet read on the
                # render path; the full fallback read + tail-splice run only on an
                # actual probed lead.
                try:
                    di = pd.DatetimeIndex(df.index)
                    deep_last = (di.tz_localize(None) if di.tz is not None else di).max()
                except Exception:  # noqa: BLE001
                    deep_last = pd.NaT
                # A present but stale stocks file must not mask a later Yahoo bar.
                # The 2026-10-16 renderer census found 151 live basket members
                # where the *first* probeable fallback ended before the last
                # Yahoo observation.  Rank lightweight index probes by actual
                # timestamp; on equal dates keep the richer stocks/China source.
                # Read full OHLCV only for the best usable candidate, never
                # every fallback's price columns on the common fresh path.
                candidates = []
                for priority, (fpath, store) in enumerate((
                    (sp, "data/stocks"), (cp, "data/china_stocks"),
                    (yp, "data/yahoo"),
                )):
                    if not fpath.exists():
                        continue
                    fb_last = _parquet_last_date(fpath)
                    if fb_last is None or (not pd.isna(deep_last) and fb_last <= deep_last):
                        continue
                    candidates.append((fb_last, -priority, fpath, store))
                for _date, _priority, fpath, store in sorted(candidates, reverse=True):
                    try:
                        candidate = _splice_fresher_tail(
                            ticker, out, pd.read_parquet(fpath), store,
                        )
                        if len(candidate) > len(out):
                            out = candidate
                            break
                    except Exception as e:  # noqa: BLE001
                        log.debug("basket member %s: tail-splice skipped: %s", ticker, e)
                    # A timestamp probe is not proof that a full parquet has a
                    # usable close; try the next *already probed* fresher source.
            # an EMPTY deep-store file must not shadow a full fallback tape — fall through
        if out is None:
            if sp.exists():
                df = pd.read_parquet(sp)            # close/high/low/volume (no open)
                df = df.copy()
                if "open" not in df.columns:
                    df["open"] = df["close"]
                out = df
            elif cp.exists():
                df = pd.read_parquet(cp)            # A-share close/high/low/volume (no open)
                df = df.copy()
                if "open" not in df.columns:
                    df["open"] = df["close"]
                out = df
            elif yp.exists():
                df = pd.read_parquet(yp)            # close[,volume]
                df = df.copy()
                for c in ("open", "high", "low"):
                    if c not in df.columns:
                        df[c] = df["close"]
                if "volume" not in df.columns:
                    df["volume"] = np.nan
                out = df
        if out is not None:
            out = out[[c for c in OHLCV_COLS if c in out.columns]].copy()
            out.index = pd.DatetimeIndex(out.index)
            out = out[~out.index.duplicated(keep="last")].sort_index()
            # zero/negative "prices" are vendor placeholders, not trades (e.g. DEC ships
            # 3y of all-zero OHLC before its US listing) — through close/prev_close they
            # manufacture an inf return that poisons the basket level from that day on.
            # Mask them so the member simply isn't live until it has a real tape.
            px = [c for c in ("open", "high", "low", "close") if c in out.columns]
            out[px] = out[px].where(out[px] > 0)
    except Exception as e:  # noqa: BLE001
        log.warning("basket member OHLCV unreadable %s: %s", ticker, e)
        out = None
    _CACHE[ticker] = out
    return out


def deep_calendar(members: list[dict], min_start: str | None = None) -> pd.DatetimeIndex:
    """Union trading calendar across the members' deep OHLCV (back to ~2014), so the MONTHLY /
    weekly MTF timeframes resolve — the shallow ~3y baskets close-cache index is too short for
    month-end MACD (engine.cycles needs ~900 trading days). Empty index if nothing loads."""
    cals = []
    for m in members:
        df = _load_member_ohlcv(m.get("ticker"))
        if df is not None and not df.empty:
            cals.append(df.index)
    if not cals:
        return pd.DatetimeIndex([])
    idx = cals[0]
    for c in cals[1:]:
        idx = idx.union(c)
    idx = pd.DatetimeIndex(idx).sort_values()
    if min_start:
        idx = idx[idx >= pd.Timestamp(min_start)]
    return idx


def _live_mask(members: list[dict], idx: pd.DatetimeIndex, present: list[str],
               pit: bool = True, close: pd.DataFrame | None = None) -> pd.DataFrame:
    """Boolean [date × ticker] membership mask.

    pit=True  → strict point-in-time: a member is live only in [added, removed). This is the
                perf-faithful index that matches engine.baskets._ew_level.
    pit=False → CURRENT membership over its FULL available history: live wherever the member has
                traded (and not after `removed`), ignoring `added`. This is the read the MTF /
                vol-hole engines want — the technical picture of the basket AS CONSTITUTED TODAY,
                deep enough for the monthly timeframe — not gated to when the curator added a name.
    """
    mask = pd.DataFrame(False, index=idx, columns=present)
    for m in members:
        t = m.get("ticker")
        if t not in present:
            continue
        if pit:
            a = np.asarray(idx >= pd.Timestamp(m["added"]))
        elif close is not None and t in close:
            fv = close[t].first_valid_index()
            a = np.asarray(idx >= fv) if fv is not None else np.zeros(len(idx), dtype=bool)
        else:
            a = np.ones(len(idx), dtype=bool)
        if m.get("removed"):
            a = a & np.asarray(idx < pd.Timestamp(m["removed"]))
        mask[t] = a
    return mask


def _base_weights(members: list[dict], present: list[str], mode: str,
                  conv_map: dict | None, ret: pd.DataFrame, mask: pd.DataFrame) -> pd.Series:
    """Per-member STATIC base weight (renormalised over the live set each day downstream)."""
    if mode == "relevance":
        wm = {}
        cm = conv_map or {}
        for m in members:
            t = m.get("ticker")
            if t not in present:
                continue
            w = m.get("weight")
            if w is None:
                sc = cm.get(t)
                w = (float(sc) / 50.0) if sc is not None else 1.0   # conviction 50 ⇒ equal
            wm[t] = max(float(w), 0.05)
        return pd.Series(wm).reindex(present).fillna(1.0)
    if mode == "alpha":
        # STATIC (in-sample) as-of-today strength vector — retained only for callers
        # that explicitly opt out of point-in-time. The default alpha path is the
        # point-in-time matrix in _alpha_weights_pit (audit #44). Emitting this vector
        # across all history is look-ahead; consolidated_candle marks it accordingly.
        rr = ret[present].where(mask)
        win = min(ALPHA_LOOKBACK, len(rr))
        seg = rr.iloc[-win:]
        return _alpha_strength(seg).reindex(present).fillna(1.0)
    return pd.Series(1.0, index=present)                            # equal


@dataclass(frozen=True)
class _CloseIndexKernel:
    close: pd.DataFrame
    previous_close: pd.DataFrame
    mask: pd.DataFrame
    weights: pd.DataFrame
    level: pd.Series | None
    previous_level: pd.Series | None
    first: pd.Timestamp | None
    stale_tail: tuple[str, ...]
    lookahead: bool


def _weighted_return(returns: pd.DataFrame, present: list[str], weights: pd.DataFrame) -> pd.Series:
    return (returns[present] * weights).sum(axis=1, min_count=1)


def _close_index_kernel(*, members, idx, present, close_raw, mode, conv_map, pit, alpha_pit):
    """The incumbent close/membership/weight calculation; no loading or diagnostics."""
    close = close_raw.ffill()
    prev_close = close.shift(1)
    r_close = close / prev_close - 1.0
    mask = _live_mask(members, idx, present, pit=pit, close=close)
    # 2026-07 staleness audit: a member whose tape ENDED (deep-store fetch gap, delisting
    # missing its `removed` stamp) would otherwise ride the ffill at a frozen price,
    # contributing 0% daily returns that dilute every subsequent basket move (ai_infra
    # printed −10% off its June top while its median member was −23%). Exit each member
    # from the live set a few grace bars past its last REAL bar, and disclose in meta.
    stale_tail = []
    for t in present:
        lv = close_raw[t].last_valid_index()
        if lv is None or lv >= idx[-1]:
            continue
        pos_lv = int(idx.get_loc(lv))
        if (len(idx) - 1 - pos_lv) <= _STALE_TAIL_GRACE:
            continue
        cutoff = idx[pos_lv + _STALE_TAIL_GRACE]
        live_after = mask.loc[mask.index > cutoff, t]
        if live_after.any():
            mask.loc[mask.index > cutoff, t] = False
            stale_tail.append(t)

    # daily renormalised weights over the live set
    lookahead = False
    if mode == "alpha" and alpha_pit:
        # POINT-IN-TIME: a per-day tilt from a monthly rebalance grid (no look-ahead).
        wmat = _alpha_weights_pit(present, r_close, mask)[present]
        w = mask.astype(float) * wmat.to_numpy()
    else:
        base_w = _base_weights(members, present, mode, conv_map, r_close, mask)
        w = mask.astype(float) * base_w.reindex(present).to_numpy()
        lookahead = (mode == "alpha")           # static alpha vector = in-sample illustration
    wsum = w.sum(axis=1).replace(0, np.nan)
    w = w.div(wsum, axis=0)

    Rc = _weighted_return(r_close, present, w)
    first = Rc.first_valid_index()
    if first is None:
        return _CloseIndexKernel(close, prev_close, mask, w, None, None, None,
                                 tuple(stale_tail), lookahead)
    lvl_close = pd.Series(np.nan, index=idx)
    lvl_close.loc[first:] = (1.0 + Rc.loc[first:].fillna(0.0)).cumprod()
    prev_lvl = lvl_close.shift(1)
    prev_lvl.loc[first] = 1.0
    return _CloseIndexKernel(close, prev_close, mask, w, lvl_close, prev_lvl, first,
                             tuple(stale_tail), lookahead)


MIN_MEMBER_INDEX_SESSIONS = 300


def _capture_index_panel(frame, *, volume=False):
    """Primitive value validation for an explicit calculation, without acquisition."""
    from lib.adjusted_price_capture import MAX_ROWS, MAX_COLUMNS, MAX_PANEL_CELLS
    if (not isinstance(frame, pd.DataFrame) or len(frame) > MAX_ROWS
            or len(frame.columns) > MAX_COLUMNS or frame.size > MAX_PANEL_CELLS
            or frame.columns.has_duplicates
            or any(not isinstance(t, str) or not t or len(t) > 24 for t in frame.columns)):
        raise ValueError("Invalid member-index panel")
    idx = frame.index
    if (not isinstance(idx, pd.DatetimeIndex) or idx.hasnans or idx.has_duplicates
            or not idx.is_monotonic_increasing or idx.tz is not None
            or not idx.equals(idx.normalize())):
        raise ValueError("Invalid member-index calendar")
    if any(not pd.api.types.is_numeric_dtype(frame[t]) or pd.api.types.is_bool_dtype(frame[t])
           or pd.api.types.is_complex_dtype(frame[t]) for t in frame.columns):
        raise ValueError("Invalid member-index value")
    raw = frame.to_numpy(dtype=float, na_value=np.nan)
    present = ~np.isnan(raw)
    if (not np.isfinite(raw[present]).all() or (raw[present] < 0).any()
            or not volume and (raw[present] == 0).any()):
        raise ValueError("Invalid member-index value")
    return pd.DataFrame(raw.copy(), index=idx.copy().as_unit("ns"), columns=frame.columns.copy())


def _capture_member_index_scope(members, idx: pd.DatetimeIndex):
    """One explicit membership/calendar identity and allocation-bound validator."""
    from datetime import date
    from lib.adjusted_price_capture import MAX_ROWS, MAX_COLUMNS, MAX_PANEL_CELLS
    if (not isinstance(members, (list, tuple)) or len(members) > MAX_COLUMNS
            or not isinstance(idx, pd.DatetimeIndex) or len(idx) > MAX_ROWS
            or idx.hasnans or idx.has_duplicates or not idx.is_monotonic_increasing
            or idx.tz is not None or not idx.equals(idx.normalize())):
        raise ValueError("Invalid explicit member-index inputs")
    document = deepcopy(list(members))
    tickers = []
    for member in document:
        ticker = member.get("ticker") if isinstance(member, Mapping) else None
        if not isinstance(ticker, str) or not ticker or len(ticker) > 24 or ticker in tickers:
            raise ValueError("Ambiguous member-index membership")
        for when in (member.get("added"), member.get("removed")):
            if when is not None and (not isinstance(when, str) or date.fromisoformat(when).isoformat() != when):
                raise ValueError("Invalid member-index membership date")
        tickers.append(ticker)
    calendar = idx.copy().as_unit("ns")
    if len(calendar) * len(tickers) > MAX_PANEL_CELLS:
        raise ValueError("Member-index projection bound")
    return document, calendar, tickers


def member_index_from_inputs(members, idx: pd.DatetimeIndex, *, close: pd.DataFrame,
                             volume: pd.DataFrame | None = None) -> tuple[pd.Series | None, dict]:
    """Current-membership equal-weight close index from actual captured fields.

    This is the Sector-cycle close-index contract, not a full candle. The caller
    supplies an admitted source calendar; this function has no loader, cache,
    provider, config, clock, publication or session-calendar lookup. Missing range
    fields are never invented. Volume is optional coverage evidence, never filled.
    """
    document, calendar, tickers = _capture_member_index_scope(members, idx)
    captured = _capture_index_panel(close)
    captured_volume = None if volume is None else _capture_index_panel(volume, volume=True)
    # Membership order is retained. A nonempty frame outside the supplied
    # calendar or an all-null column is not a resolved member.
    raw = captured.reindex(index=calendar, columns=[t for t in tickers if t in captured])
    present = [t for t in tickers if t in raw and bool(raw[t].notna().any())]
    meta = {"mode": "equal", "pit": False, "n_total": len(tickers), "n_with_close": len(present),
            "coverage_pct": None, "n_live_with_volume": None, "status": "unavailable",
            "reason": "insufficient_resolved_members", "index_sessions": 0}
    if len(present) < 3:
        return None, meta
    core = _close_index_kernel(members=document, idx=calendar, present=present,
        close_raw=raw[present], mode="equal", conv_map=None, pit=False, alpha_pit=True)
    if core.level is None:
        return None, {**meta, "reason": "no_member_index_returns"}
    full = core.level.replace([np.inf, -np.inf], np.nan).dropna().rename("close")
    n_live = int(core.mask.iloc[-1].sum())
    meta.update({"n_live": n_live, "n_stale_tail": len(core.stale_tail),
        "stale_tail": sorted(core.stale_tail)[:12], "index_sessions": len(full),
        "as_of": str(full.index[-1].date()) if len(full) else None,
        "start": str(full.index[0].date()) if len(full) else None, "lookahead": core.lookahead})
    if captured_volume is not None:
        latest = captured_volume.reindex(index=calendar, columns=present).iloc[-1]
        observed = int((latest.notna() & (latest > 0) & core.mask.iloc[-1]).sum())
        meta.update({"n_live_with_volume": observed,
                     "coverage_pct": round(observed / n_live, 3) if n_live else None})
    if len(full) < MIN_MEMBER_INDEX_SESSIONS:
        return None, {**meta, "reason": "insufficient_index_history"}
    return full.copy(deep=True), {**meta, "status": "available", "reason": None}


def _consolidated_candle_from_loaded(members, idx, loaded, *, mode, conv_map,
                                    pit, alpha_pit, diagnostics):
    """Incumbent OHLC construction over supplied frames; one numerical owner."""
    tickers = [m.get("ticker") for m in members if m.get("ticker")]
    present = [t for t in tickers if loaded.get(t) is not None and not loaded[t].empty]
    n_total = len(set(tickers))
    if len(present) < 3:
        return None, {"n_total": n_total, "n_with_ohlcv": len(present), "coverage_pct": None,
                      "mode": mode}

    # align each field to the basket calendar
    def _field(col: str) -> pd.DataFrame:
        cols = {t: loaded[t][col].reindex(idx) for t in present if col in loaded[t].columns}
        return pd.DataFrame(cols, index=idx)

    close_raw = _field("close")
    high = _field("high").ffill()
    low = _field("low").ffill()
    open_ = _field("open").ffill()
    vol = _field("volume")

    core = _close_index_kernel(members=members, idx=idx, present=present,
        close_raw=close_raw, mode=mode, conv_map=conv_map, pit=pit, alpha_pit=alpha_pit)
    close, prev_close, mask, w = core.close, core.previous_close, core.mask, core.weights
    stale_tail, lookahead = list(core.stale_tail), core.lookahead
    if stale_tail and diagnostics:
        log.warning("basket candle: %d member tape(s) stale past %d-bar grace — exited "
                    "from the live set at tape end: %s", len(stale_tail), _STALE_TAIL_GRACE,
                    ",".join(sorted(stale_tail)[:12]))
    r_high = high / prev_close - 1.0
    r_low = low / prev_close - 1.0
    r_open = open_ / prev_close - 1.0
    Rh, Rl, Ro = (_weighted_return(frame, present, w) for frame in (r_high, r_low, r_open))
    first = core.first
    if first is None:
        return None, {"n_total": n_total, "n_with_ohlcv": len(present), "coverage_pct": None,
                      "mode": mode}
    lvl_close, prev_lvl = core.level, core.previous_level

    cand = pd.DataFrame(index=idx)
    cand["close"] = lvl_close
    cand["high"] = prev_lvl * (1.0 + Rh)
    cand["low"] = prev_lvl * (1.0 + Rl)
    cand["open"] = prev_lvl * (1.0 + Ro)
    # guard the candle ordering (numerical safety): high ≥ {open,close} ≥ low
    cand["high"] = cand[["high", "open", "close"]].max(axis=1)
    cand["low"] = cand[["low", "open", "close"]].min(axis=1)

    # traded dollar-volume over the live set = Σ price·volume
    dvol = (close[present] * vol[present]).where(mask)
    cand["dollar_vol"] = dvol.sum(axis=1, min_count=1)
    cand["n_live"] = mask.sum(axis=1)
    cand = cand.loc[first:]

    n_live_now = int(mask.iloc[-1].sum())
    with_vol_now = int((vol[present].iloc[-1].notna() & (vol[present].iloc[-1] > 0) & mask.iloc[-1]).sum())
    meta = {
        "mode": mode, "n_total": n_total, "n_with_ohlcv": len(present),
        "n_live": n_live_now, "n_live_with_volume": with_vol_now,
        # stale-tape disclosure (nulls printed, not hidden): members exited early
        # because their OHLCV tape ended before the basket's last bar.
        "n_stale_tail": len(stale_tail), "stale_tail": sorted(stale_tail)[:12],
        "coverage_pct": round(with_vol_now / n_live_now, 3) if n_live_now else None,
        "as_of": str(cand.index.max().date()) if not cand.empty else None,
        "start": str(cand.index.min().date()) if not cand.empty else None,
        # True only for the legacy static alpha vector applied across all history — an
        # in-sample illustration a template must disclose as look-ahead (audit #44).
        # The default point-in-time alpha path (alpha_pit=True) sets this False.
        "lookahead": lookahead,
    }
    return cand, meta


def consolidated_candle(members: list[dict], idx: pd.DatetimeIndex, mode: str = "equal",
                        conv_map: dict | None = None, pit: bool = True,
                        alpha_pit: bool = True
                        ) -> tuple[pd.DataFrame | None, dict]:
    """The basket CANDLE on calendar `idx`: columns [open, high, low, close, dollar_vol, n_live],
    + a coverage/meta dict. None if fewer than 3 members resolve OHLCV. close is a LEVEL from 1.0.

    `members` are membership entries ({ticker, added, removed, weight?}); `idx` the basket
    calendar; `conv_map` ticker→conviction score for relevance weighting; `pit` selects strict
    point-in-time membership (True, perf-faithful) vs current-membership-over-full-history
    (False, for the deep MTF/vol-hole technical read). See _live_mask.

    `alpha_pit` (mode=='alpha' only): True (default) recomputes the trailing-strength tilt
    on a monthly rebalance grid and holds each vector forward — a point-in-time curve with
    no look-ahead. False reproduces the legacy static as-of-today vector applied across all
    history (an in-sample illustration); meta is stamped `lookahead: true` so any display
    can disclose it. See _alpha_weights_pit / audit #44."""
    tickers = [m.get("ticker") for m in members if m.get("ticker")]
    loaded = {t: _load_member_ohlcv(t) for t in tickers}
    return _consolidated_candle_from_loaded(
        members, idx, loaded, mode=mode, conv_map=conv_map, pit=pit,
        alpha_pit=alpha_pit, diagnostics=True)


def consolidated_candle_from_inputs(members, idx: pd.DatetimeIndex, *,
                                    frames: Mapping, mode: str = "equal",
                                    conv_map: dict | None = None, pit: bool = False,
                                    alpha_pit: bool = True,
                                    reference_close: pd.DataFrame | None = None,
                                    basis_tolerance: float = 1e-3):
    """Build the incumbent full candle from detached genuine member fields.

    Missing field identities are unavailable, never substituted with closes.
    The calendar stops at an eligible actual observation; a later removed
    member or an empty provider tail cannot advance the candle's source date.
    """
    from lib.adjusted_price_capture import OHLCV_FIELDS, MAX_PANEL_CELLS, validate_ohlcv_geometry
    document, calendar, tickers = _capture_member_index_scope(members, idx)
    if (not isinstance(frames, Mapping) or not set(frames).issubset(tickers)
            or mode not in ("equal", "relevance", "alpha")
            or type(pit) is not bool or type(alpha_pit) is not bool
            or (pit and any(not row.get("added") for row in document))):
        raise ValueError("Invalid explicit member-candle scope")
    if (type(basis_tolerance) not in (int, float) or not np.isfinite(basis_tolerance)
            or not 0 <= basis_tolerance < 1):
        raise ValueError("Invalid member-candle basis tolerance")
    if sum(frame.size for frame in frames.values() if isinstance(frame, pd.DataFrame)) > MAX_PANEL_CELLS * len(OHLCV_FIELDS):
        raise ValueError("Captured member-frame allocation bound")
    reference = None if reference_close is None else _capture_index_panel(reference_close)
    if reference is not None and not set(reference.columns).issubset(tickers):
        raise ValueError("Unexpected member-candle reference population")
    loaded, unavailable, basis_checks = {}, {}, {}
    observation_dates = {}
    for ticker in tickers:
        frame = frames.get(ticker)
        if frame is None:
            unavailable[ticker] = "no_captured_frame"
            continue
        if not isinstance(frame, pd.DataFrame) or frame.columns.has_duplicates:
            raise ValueError("Invalid explicit member-candle frame")
        if frame.empty:
            unavailable[ticker] = "no_captured_observations"
            continue
        if set(frame.columns) != set(OHLCV_FIELDS):
            unavailable[ticker] = "genuine_ohlcv_fields_required"
            continue
        values = {}
        dates = {}
        for field in OHLCV_FIELDS:
            column = _capture_index_panel(
                frame[[field]].rename(columns={field: ticker}), volume=field == "volume")[ticker]
            actual = column.dropna()
            if len(calendar) and len(actual) and actual.index[-1] > calendar[-1]:
                raise ValueError("Future member-candle observations")
            values[field] = column
            dates[field] = actual.index[-1] if len(actual) else None
        validate_ohlcv_geometry({field: column.to_frame(ticker) for field, column in values.items()})
        if any(value is None for value in dates.values()):
            unavailable[ticker] = "genuine_ohlcv_observations_required"
            continue
        if len(set(dates.values())) != 1:
            unavailable[ticker] = "mixed_field_observation_dates"
            continue
        if reference is not None:
            from lib import store
            prior_close = (reference[ticker].dropna() if ticker in reference
                           else pd.Series(dtype=float))
            comparison = store.compare_basis(prior_close.to_frame("close"),
                values["close"].dropna().to_frame("close"), strict=True, tol=basis_tolerance)
            basis_checks[ticker] = {"status": comparison.status,
                                    "overlap_dates": comparison.overlap_dates}
            if comparison.status != store.BASIS_ALIGNED or comparison.overlap_dates < 3:
                unavailable[ticker] = "reference_basis_unqualified"
                continue
        loaded[ticker] = pd.DataFrame(values)
        observation_dates[ticker] = {
            field: stamp.date().isoformat() for field, stamp in dates.items()}
    present = [ticker for ticker in tickers if ticker in loaded]
    evidence = {"unavailable_members": unavailable, "member_field_dates": observation_dates,
                "required_fields": list(OHLCV_FIELDS), "status": "unavailable",
                "observed_member_coverage_pct": None,
                "reference_basis_qualified": reference is not None and len(present) >= 3,
                "reference_basis_checks": basis_checks,
                "reference_basis_tolerance": basis_tolerance}
    if len(present) < 3 or not len(calendar):
        return None, {"n_total": len(tickers), "n_with_ohlcv": len(present),
                      "coverage_pct": None, "mode": mode, **evidence}
    close = pd.DataFrame({ticker: loaded[ticker]["close"].reindex(calendar) for ticker in present},
                         index=calendar)
    eligible = _live_mask(document, calendar, present, pit=pit, close=close)
    observed = (close.notna() & eligible).any(axis=1)
    endpoints = calendar[observed]
    if not len(endpoints):
        return None, {"n_total": len(tickers), "n_with_ohlcv": len(present),
                      "coverage_pct": None, "mode": mode, **evidence}
    calendar = calendar[calendar <= endpoints[-1]]
    candle, meta = _consolidated_candle_from_loaded(
        document, calendar, loaded, mode=mode, conv_map=deepcopy(conv_map),
        pit=pit, alpha_pit=alpha_pit, diagnostics=False)
    at_end = eligible.loc[calendar[-1]] & close.loc[calendar[-1]].notna()
    count = int(at_end.sum())
    evidence.update({"status": "available" if candle is not None else "unavailable",
                     "observed_members_at_endpoint": count,
                     "observed_member_coverage_pct": round(count / len(tickers), 3) if tickers else None,
                     "observed_endpoint": calendar[-1].date().isoformat()})
    return (None if candle is None else candle.copy(deep=True)), {**meta, **evidence}


def weight_variants(members: list[dict], idx: pd.DatetimeIndex,
                    conv_map: dict | None = None) -> dict:
    """The three weighting schemes' CLOSE levels (rebased to 1.0), for the comparison overlay.
    Display-only — lets the user see how a conviction- or alpha-tilt reshapes the same basket.
    The alpha curve is POINT-IN-TIME (monthly-rebalanced trailing strength, no look-ahead —
    audit #44); `alpha_lookahead` reports whether any emitted curve used the legacy static
    vector (always False here)."""
    out: dict = {}
    lookahead = False
    for mode in ("equal", "relevance", "alpha"):
        cand, meta = consolidated_candle(members, idx, mode, conv_map)   # alpha_pit=True default
        if cand is not None and not cand["close"].dropna().empty:
            out[mode] = [None if pd.isna(v) else round(float(v), 5) for v in cand["close"].reindex(idx)]
            lookahead = lookahead or bool(meta.get("lookahead"))
    out["alpha_lookahead"] = lookahead
    return out
