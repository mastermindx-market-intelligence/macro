"""Descriptive OKX BTC/CONTRACTS aggressor-flow context, never a sizing signal.

Native provider units and label-time windows are retained. Unknown dollar units,
bucket boundary, publication/finality and contract composition are not inferred.
Exact elapsed coverage is necessary but does not prove historical availability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import numpy as np
import pandas as pd
from lib import store

log = logging.getLogger(__name__)
DIV_W = 720
RUBIK_WINDOW_H = 720  # Provider retrieval depth, NOT a tolerance for shorter gaps.
STALE_AFTER_H = 48
MIN_HOURS_DIV = 2 * DIV_W + 72
ACCRUE_NOTE = (
    "OKX BTC aggregate derivatives aggressor flow in native reported units. "
    "Observation-label windows; bucket boundary, units, publication and finality "
    "remain unqualified. Descriptive only, not scored or an allocation trigger."
)


def _f(v):
    try:
        n = float(v)
        return n if np.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _causal_z(s: pd.Series, w: int) -> pd.Series:
    mu = s.rolling(w).mean().shift(1)
    sd = s.rolling(w).std().shift(1)
    return (s - mu) / sd.replace(0.0, np.nan)


def _index(index) -> pd.DatetimeIndex:
    # Existing hourly stores use UTC-naive labels. Do not interpret their labels
    # as proof of a completed interval or a source publication timestamp.
    idx = pd.DatetimeIndex(pd.to_datetime(index))
    return idx.tz_convert('UTC').tz_localize(None) if idx.tz is not None else idx


def compute(sig_df: pd.DataFrame | None = None, *, as_of=None) -> dict:
    """Bounded descriptive projection. Explicit as_of is a UTC snapshot cutoff."""
    try:
        clock = pd.Timestamp(as_of if as_of is not None else datetime.now(timezone.utc))
        if pd.isna(clock) or clock.tz is None:
            raise ValueError('Timezone-aware evaluation clock required')
        clock = clock.tz_convert('UTC').tz_localize(None)
        h = store.read('okx', 'taker_volume_hourly')
        if h is None or h.empty or not {'taker_buy_vol', 'taker_sell_vol'} <= set(h.columns):
            return {'ok': False, 'reason': 'okx/taker_volume_hourly unavailable',
                    'display_only': True, 'accruing': True, 'causally_qualified': False}
        h = h.copy(); h.index = _index(h.index)
        if h.index.hasnans:
            raise ValueError('Undated observation cannot be assigned to an as-of window')
        h = h.loc[h.index <= clock].sort_index()
        if h.empty or h.index.hasnans or h.index.has_duplicates or (h.index != h.index.floor('h')).any():
            raise ValueError('Missing, duplicate or off-hour observation labels')
        okx_last = h.index[-1]
        raw = h[['taker_buy_vol', 'taker_sell_vol']]
        boolean = raw.apply(lambda col: col.map(lambda v: isinstance(v, (bool, np.bool_)))).any(axis=1)
        numeric = raw.apply(pd.to_numeric, errors='coerce')
        valid = np.isfinite(numeric).all(axis=1) & (numeric >= 0).all(axis=1) & ~boolean
        gap_detected = bool((h.index.to_series().diff().dropna() != pd.Timedelta(hours=1)).any() or (~valid).any())
        # Walk backward to the latest contiguous valid segment, without allocating
        # a huge resampled index across a provider outage. No fallback past a bad tail.
        n = 0
        for i in range(len(h) - 1, -1, -1):
            if not valid.iloc[i] or (i < len(h) - 1 and h.index[i + 1] - h.index[i] != pd.Timedelta(hours=1)):
                break
            n += 1
        seg = numeric.iloc[len(h) - n:] if n else numeric.iloc[:0]
        signed = seg.taker_buy_vol - seg.taker_sell_vol
        cvd = signed.cumsum()
        net24 = _f(signed.tail(24).sum()) if n >= 24 else None
        net72 = _f(signed.tail(72).sum()) if n >= 72 else None
        total24 = _f(seg.tail(24).sum().sum()) if n >= 24 else None
        buy_share = _f(seg.taker_buy_vol.tail(24).sum() / total24) if total24 and total24 > 0 else None
        behind_clock = round(float((clock - okx_last) / pd.Timedelta(hours=1)), 6)
        ref = store.read('coinbase', 'btc_hourly')
        behind_ref = None
        if ref is not None and not ref.empty:
            ref = ref.copy(); ref.index = _index(ref.index)
            ref = ref.loc[ref.index <= clock]
            if not ref.empty:
                behind_ref = round(float((ref.index.max() - okx_last) / pd.Timedelta(hours=1)), 6)
        stale = behind_clock > STALE_AFTER_H or (behind_ref is not None and behind_ref > STALE_AFTER_H)
        state = 'unavailable'
        if n >= 24 and not stale:
            if total24 == 0:
                state = 'no_activity'
            elif net24 == 0:
                state = 'balanced'
            elif n >= 168:
                scale = _f(signed.abs().tail(168).mean())
                if scale and scale > 0:
                    z24 = net24 / (scale * 24 ** .5)
                    state = 'sell_dominant' if z24 <= -1 else 'buy_dominant' if z24 >= 1 else 'balanced'
        out = {
            'ok': n >= 24, 'display_only': True, 'causally_qualified': False,
            'scope': 'OKX/BTC/CONTRACTS', 'volume_unit': None,
            'timestamp_role': None, 'first_available_at': None,
            'asof': str(okx_last), 'evaluated_at': str(clock), 'n_hours': n,
            'stored_rows': len(h), 'stale': bool(stale), 'hours_behind_ref': behind_ref,
            'hours_behind_clock': behind_clock, 'gap_detected': gap_detected,
            'window_24h_complete': n >= 24, 'window_72h_complete': n >= 72,
            'cvd_native': _f(cvd.iloc[-1]) if n else None,
            'net_flow_24h_native': net24, 'net_flow_72h_native': net72,
            'buy_share_24h': buy_share,
            # Compatibility keys remain, but an unknown unit cannot become USD.
            'cvd_last_bn': None, 'net_flow_24h_mn': None, 'net_flow_72h_mn': None,
            'flow_state': state, 'accruing': n < MIN_HOURS_DIV,
            'history_note': f'{n} contiguous hourly observations; {MIN_HOURS_DIV} needed for descriptive divergence. Not forecast qualification.',
            'price_alignment_complete': None, 'divergence': None, 'note': ACCRUE_NOTE,
        }
        if n >= MIN_HOURS_DIV:
            out['price_alignment_complete'] = False
            if ref is not None and not ref.empty and 'close' in ref.columns and not ref.index.has_duplicates:
                close = pd.to_numeric(ref['close'], errors='coerce').sort_index().reindex(cvd.index)
                tail = close.tail(MIN_HOURS_DIV)
                complete = bool(np.isfinite(tail).all() and (tail > 0).all())
                out['price_alignment_complete'] = complete
                if complete and not stale:
                    close = close.where(np.isfinite(close) & (close > 0))
                    ret24 = close / close.shift(24) - 1.
                    div = _causal_z(ret24, DIV_W) - _causal_z(cvd.diff(24), DIV_W)
                    dp = _f(div.rolling(DIV_W).rank(pct=True).iloc[-1])
                    if dp is not None:
                        dstate = 'price_flow_high' if dp >= .90 else 'price_flow_low' if dp <= .10 else 'none'
                        out['divergence'] = {
                            'value': _f(div.iloc[-1]), 'pctile': round(dp, 3), 'state': dstate,
                            'note': 'Cross-venue price/native-flow contrast; timestamp roles and composition not qualified. Descriptive, not a predictive or passive-absorption claim.',
                        }
        return out
    except Exception as exc:  # Additive context cannot crash the primary model.
        return {'ok': False, 'reason': f'{type(exc).__name__}: {exc}',
                'display_only': True, 'accruing': True, 'causally_qualified': False}
