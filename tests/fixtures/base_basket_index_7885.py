"""Literal pre-extraction full candle kernel for numerical parity.
Source: 7885f75fc27877b5757fdafc860da6552a2f52bf:engine/basket_index.py
Whole-source SHA256: 92cd14b8224a5444e05dfc79a41612b13fa74cb9d055ff6aa10f8d696abb3151
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
log = logging.getLogger(__name__)
ALPHA_CAP=2.0
ALPHA_LOOKBACK=120
ALPHA_REBAL="MS"
_STALE_TAIL_GRACE=5

def _load_member_ohlcv(ticker):
    raise AssertionError("Frozen baseline requires explicit test loader")

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
    return (w / w.mean()).clip(1.0 / ALPHA_CAP, ALPHA_CAP)

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
    return pd.Series(1.0, index=present)

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
    close = close_raw.ffill()
    high = _field("high").ffill()
    low = _field("low").ffill()
    open_ = _field("open").ffill()
    vol = _field("volume")

    prev_close = close.shift(1)
    r_close = close / prev_close - 1.0
    r_high = high / prev_close - 1.0
    r_low = low / prev_close - 1.0
    r_open = open_ / prev_close - 1.0

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
    if stale_tail:
        log.warning("basket candle: %d member tape(s) stale past %d-bar grace — exited "
                    "from the live set at tape end: %s", len(stale_tail), _STALE_TAIL_GRACE,
                    ",".join(sorted(stale_tail)[:12]))

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

    def _wret(rf: pd.DataFrame) -> pd.Series:
        return (rf[present] * w).sum(axis=1, min_count=1)

    Rc, Rh, Rl, Ro = _wret(r_close), _wret(r_high), _wret(r_low), _wret(r_open)
    first = Rc.first_valid_index()
    if first is None:
        return None, {"n_total": n_total, "n_with_ohlcv": len(present), "coverage_pct": None,
                      "mode": mode}
    lvl_close = pd.Series(np.nan, index=idx)
    lvl_close.loc[first:] = (1.0 + Rc.loc[first:].fillna(0.0)).cumprod()
    prev_lvl = lvl_close.shift(1)
    prev_lvl.loc[first] = 1.0    # the implicit cumprod base — the level the day before `first`

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
