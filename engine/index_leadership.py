"""engine/index_leadership.py — INDEX-LEVEL leadership & rotation acceleration.

Pure compute. Lifts the subsector RRG / velocity math (``engine.subsector_rotation``)
to the INDEX level so the Subsector Confluence board can answer two questions the
per-subsector tabs cannot on their own:

  1. **Which of the four universes is the RISING STAR** — not the one leading *now*,
     but the one whose leadership is *accelerating* most vs the others. Measured on
     three orthogonal legs, cross-ranked across the tabs:
       • return acceleration   (index vs the cross-tab median, recent pace vs baseline)
       • breadth thrust        (Δ share of the tab's subsector-baskets above their 50-DMA)
       • participation         (share of the tab's subsectors improving / accelerating)

  2. **Within each universe, two DELIBERATELY-SEPARATE rotation lists** (the user's
     runner-vs-bottomer split — a runner must never crowd out a bottomer):
       • RUNNING  — already leading AND accelerating  (RRG 'leading' quadrant).
       • COILING  — laggards turning up               (RRG 'improving' quadrant), with a
         higher-timeframe guard so a relative-strength uptick in a subsector still in a
         confirmed downtrend / distribution does NOT masquerade as 'about to run'
         (the "3-day bounce in a 2-week/monthly bear" trap). This is a v1 rotation-derived
         coil list; the deeper bottom-radar port (2W timeframe + macro veto + capitulation
         legs) is a later phase.

It also reads the observable LEADERSHIP-DRIVER ratios (RSP/SPY breadth-of-leadership,
IWM/SPY size, IWF/IWD style, XLK/RSP tech-concentration) so the page can say WHY
leadership sits where it does — the measurable read, not a regime label.

HONEST BY CONSTRUCTION. Cross-sectional (each tab is judged vs the other tabs); a
4-point z-score is noisy, so the raw legs are always surfaced alongside the composite.
DISPLAY-ONLY context, never scored into an allocation — the same posture as
``engine.subsector_rotation`` / ``engine.velocity`` / ``engine.market_state``.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from engine import bottom_radar as _br
from engine import cycles as _cyc
from engine.subsector_rotation import _rotation_metrics, _zscore, _rotation_number

# trading-day windows for the rolling horizons (match subsector_rotation's MOM set).
_HZ_BARS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252}
_BW = "2W-FRI"  # the bi-weekly (2-week) bar — the timeframe the user names as "2W"


# ----------------------------------------------------------------- primitives ----

def horizon_returns(close: pd.Series | None) -> dict[str, float | None]:
    """{'1W','1M','3M','6M','1Y': pct} rolling returns off a close series (leak-free —
    each is last / bar-n-ago). None per horizon when the series is too short."""
    out = {h: None for h in _HZ_BARS}
    if close is None:
        return out
    c = close.dropna()
    if len(c) < 6:
        return out
    last = float(c.iloc[-1])
    for h, n in _HZ_BARS.items():
        if len(c) > n:
            base = c.iloc[-1 - n]
            if not pd.isna(base) and float(base) != 0.0:
                out[h] = round((last / float(base) - 1.0) * 100.0, 3)
    return out


def _above_ma(close: pd.Series, window: int = 50, lag: int = 0) -> float | None:
    """1.0 if close is above its `window`-DMA `lag` bars back, else 0.0 (None if short)."""
    c = close.dropna()
    if len(c) < window + lag + 1:
        return None
    ma = c.rolling(window).mean()
    i = -1 - lag
    px, m = c.iloc[i], ma.iloc[i]
    if pd.isna(px) or pd.isna(m):
        return None
    return 1.0 if float(px) > float(m) else 0.0


def breadth_thrust(closes: Sequence[pd.Series], window: int = 50, lag: int = 20) -> float | None:
    """Δ in the share of a tab's subsector-baskets trading above their own `window`-DMA
    (now vs `lag` bars ago) — a self-contained breadth THRUST off price history alone
    (no snapshot log needed). Positive = more baskets reclaiming their trend = broadening."""
    now, prev = [], []
    for c in closes:
        a = _above_ma(c, window, 0)
        b = _above_ma(c, window, lag)
        if a is not None:
            now.append(a)
        if b is not None:
            prev.append(b)
    if not now or not prev:
        return None
    return round(float(np.mean(now)) - float(np.mean(prev)), 4)


# -------------------------------------------------------------- within-a-tab ----

def within_tab_rotation(groups: Mapping[str, Mapping]) -> dict:
    """Cross-sectional RRG over ONE tab's subsectors (benchmark = the median subsector,
    exactly like subsector_rotation), then split into the two separate lists.

    `groups` : {key: {"hz": {horizon: pct}, "regime_state", "regime_side", "above200",
                       "n_priced", "label", "sector", "entry_tier", "rs_60d"}}
    Returns  : {"metrics": {key: rot}, "rising": [entry], "coiling": [entry],
                "participation": {"frac_improving", "mean_emerging", "n"}}
    """
    keys = list(groups)
    if not keys:
        return {"metrics": {}, "rising": [], "coiling": [],
                "participation": {"frac_improving": None, "mean_emerging": None, "n": 0}}

    met = _rotation_metrics({k: dict(groups[k].get("hz") or {}) for k in keys})

    def _entry(k: str) -> dict:
        g, m = groups[k], met[k]
        return {
            "key": k, "label": g.get("label") or k, "sector": g.get("sector"),
            "rs_ratio": m["rs_ratio"], "rs_mom": m["rs_mom"], "accel": m["accel"],
            "quadrant": m["quadrant"], "emerging_score": m["emerging_score"],
            "regime_state": g.get("regime_state"), "regime_side": g.get("regime_side"),
            "entry_tier": g.get("entry_tier"), "rs_60d": g.get("rs_60d"),
            "above200": bool(g.get("above200")),
        }

    def _rising_ok(k: str) -> bool:
        g, m = groups[k], met[k]
        if (g.get("n_priced") or 0) < 3 or m["quadrant"] != "leading" or m["rs_mom"] <= 0:
            return False
        # a genuine RUNNER leads its peers AND is not distributing / below its own trend — a
        # relative-strength 'leader' that is TOPPING/SELLING or below its 200-DMA is a late/hollow
        # leader (it belongs to the board's headwind list), not a rising star.
        return g.get("regime_state") not in ("TOPPING", "SELL", "BELOW_TREND")

    def _coiling_ok(k: str) -> bool:
        g, m = groups[k], met[k]
        if (g.get("n_priced") or 0) < 3 or m["quadrant"] != "improving":
            return False
        if m["accel"] is not None and m["accel"] < 0:
            return False
        side, state = g.get("regime_side"), g.get("regime_state")
        if side == "avoid" or state in ("SELL", "TOPPING"):
            return False
        # the "3D bounce in a 2W/1M bear" guard: a laggard turning up while still below its
        # own trend is a knife, not a coil — require it be above its 200-DMA to qualify.
        if state == "BELOW_TREND" and not g.get("above200"):
            return False
        return True

    rising = sorted((_entry(k) for k in keys if _rising_ok(k)),
                    key=lambda e: e["emerging_score"], reverse=True)
    coiling = sorted((_entry(k) for k in keys if _coiling_ok(k)),
                     key=lambda e: e["emerging_score"], reverse=True)

    measured = [k for k in keys if met[k]['rotation_status'] == 'MEASURED']
    improving = [k for k in measured if met[k]['rs_mom'] > 0 and met[k]['accel'] >= 0]
    emerging_vals = [met[k]['emerging_score'] for k in measured]
    complete = len(measured) == len(keys)
    partic = {
        'frac_improving': round(len(improving) / len(keys), 3) if complete and keys else None,
        'mean_emerging': round(float(np.mean(emerging_vals)), 3) if complete and emerging_vals else None,
        'n': len(keys), 'n_measured': len(measured), 'n_unavailable': len(keys) - len(measured),
        'population_basis': 'all_expected_groups_required',
    }

    return {"metrics": met, "rising": rising, "coiling": coiling, "participation": partic}


# --------------------------------------------------------------- cross-a-tab ----

def cross_tab_leadership(
    tab_reps: Mapping[str, Mapping[str, float]],
    tab_breadth: Mapping[str, float | None],
    tab_partic: Mapping[str, float | None],
    *, weights: tuple[float, float, float] = (0.40, 0.30, 0.30),
) -> dict:
    """Existing three-leg composite on a shared complete cohort, without zero imputation."""
    tabs = list(tab_reps)
    rot = _rotation_metrics(dict(tab_reps)) if tabs else {}
    raw = [{t: _rotation_number(rot.get(t, {}).get('z_accel')) for t in tabs},
           {t: _rotation_number(tab_breadth.get(t)) for t in tabs},
           {t: _rotation_number(tab_partic.get(t)) for t in tabs}]
    w1, w2, w3 = weights  # preserve the existing three-weight input contract
    comparable = [t for t in tabs if all(leg[t] is not None for leg in raw)]
    zs = [_zscore({t: leg[t] if t in comparable else None for t in tabs}) for leg in raw]
    out = {}
    for t in tabs:
        m = rot.get(t, {})
        values = [z[t] for z in zs]
        las = (_rotation_number(sum(w * value for w, value in zip((w1, w2, w3), values)))
               if all(value is not None for value in values) else None)
        def rounded(value):
            return round(value, 3) if value is not None else None
        out[t] = {
            'rs_ratio': m.get('rs_ratio'), 'rs_mom': m.get('rs_mom'),
            'accel': m.get('accel'), 'quadrant': m.get('quadrant'),
            'breadth_thrust': raw[1][t], 'participation': raw[2][t],
            'z_return': rounded(values[0]), 'z_breadth': rounded(values[1]),
            'z_participation': rounded(values[2]), 'las': rounded(las),
            'leadership_status': 'MEASURED' if las is not None else 'UNAVAILABLE',
            'leadership_comparison_tabs': len(comparable),
        }
    stars = [t for t in tabs if out[t]['las'] is not None and out[t]['las'] > 0]
    leaders = [t for t in tabs if out[t]['rs_ratio'] is not None and out[t]['rs_ratio'] > 0]
    return {'tabs': out,
            'rising_star': max(stars, key=lambda t: out[t]['las']) if stars else None,
            'leader_now': max(leaders, key=lambda t: out[t]['rs_ratio']) if leaders else None}


# ----------------------------------------------------------- driver ratios ----

def ratio_read(num: pd.Series, den: pd.Series) -> dict | None:
    """RS-ratio read for a leadership pair: latest ratio, 20d/60d momentum, 200-DMA
    posture, 1y percentile. All leak-free (trailing only)."""
    if num is None or den is None:
        return None
    r = (num.dropna() / den.reindex(num.index)).dropna()
    if len(r) < 70:
        return None

    def _mom(n: int) -> float | None:
        if len(r) <= n:
            return None
        base = float(r.iloc[-1 - n])
        return round((float(r.iloc[-1]) / base - 1.0) * 100.0, 2) if base else None

    ma200 = r.rolling(200).mean().iloc[-1] if len(r) >= 200 else None
    win = r.iloc[-252:]
    pctile = round(float(win.rank(pct=True).iloc[-1]) * 100.0, 0) if len(win) > 20 else None
    return {
        "last": round(float(r.iloc[-1]), 4),
        "mom20": _mom(20), "mom60": _mom(60),
        "above200": (bool(r.iloc[-1] > ma200) if ma200 is not None and not pd.isna(ma200) else None),
        "pctile": pctile,
    }


# ------------------------------------------------- coil confirmation (Phase 2) ----
# A multi-factor confirmation that a laggard turning up (RRG 'improving') is a DURABLE
# coil, not a bounce inside a higher-timeframe downtrend. Reuses the validated, standalone,
# close-only leg helpers (bottom_radar) + the per-timeframe indicator engine (cycles._tf_state)
# — adds NO new signal math. DISPLAY-ONLY: bottom-timing is a drawdown / watchlist-ORDERING
# lever, not return-alpha (bottom_radar's honesty contract). The point the user asked for:
# guard against "a 3D technical bounce in a 2W/1M bear that is just showing its teeth".

_COIL_W = {"divergence": 0.24, "mtf_turn": 0.24, "vol_contract": 0.14,
           "rs_hold": 0.16, "deter_easing": 0.10, "trend": 0.12}


def _tf_falling(s: dict) -> bool:
    """A timeframe is FALLING when momentum just crossed down, or is negative and NOT
    turning up (curling/approaching/crossing up) — a confirmed higher-TF downtrend."""
    if not s:
        return False
    if s.get("macd_cross_dn"):
        return True
    return (not s.get("macd_pos") and not s.get("macd_cross_up")
            and not s.get("macd_curl_up") and not s.get("macd_approaching_up"))


def _tf_dir(s: dict) -> str:
    if not s:
        return "na"
    if _br._tf_up(s):
        return "up"
    if _tf_falling(s):
        return "down"
    return "flat"


def _above_rising_200(close: pd.Series) -> tuple[bool | None, bool | None]:
    c = close.dropna()
    if len(c) < 210:
        return None, None
    ma = c.rolling(200).mean()
    above = bool(c.iloc[-1] > ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None
    rising = bool(ma.iloc[-1] > ma.iloc[-21]) if pd.notna(ma.iloc[-21]) else None
    return above, rising


def coil_assess(close: pd.Series | None, bench: pd.Series | None = None) -> dict | None:
    """Confirm a bottoming/coil candidate. Returns coil_score (0-100), a stage, the
    W/2W/M/3D trend directions, and the per-leg breakdown — or None if uncomputable.

    stage: 'knife'   — bounce inside a confirmed weekly / 2-week / monthly downtrend (VETOED);
           'primed'  — turning up, above a rising 200-DMA, higher-TF confirming (durable coil);
           'coiling' — turning up but higher-TF not yet confirming / below trend;
           'watch'   — no lead (no divergence, no MTF turn) yet.
    """
    if close is None:
        return None
    c = close.dropna()
    if len(c) < 220:
        return None
    try:
        mtf = _cyc.mtf_snapshot(c) or {}
        bw = _cyc._tf_state(c.resample(_BW).last().dropna())
    except Exception:  # noqa: BLE001
        return None
    W, M, D3 = mtf.get("W") or {}, mtf.get("M") or {}, mtf.get("3D") or {}

    htf_falling = _tf_falling(W) or _tf_falling(bw) or _tf_falling(M)
    htf_turning = bool(_br._tf_up(W) or _br._tf_up(bw))
    above200, rising200 = _above_rising_200(c)

    legs = {
        "divergence": _br._divergence_grade(c, mtf),
        "mtf_turn": float(np.clip(sum(w * _br._tf_up(mtf.get(tf, {})) for tf, w in _br._TF_W.items()), 0, 1)),
        "vol_contract": _br._vol_contraction(c),
        "rs_hold": _br._rs_hold(c, bench),
        "deter_easing": _br._deter_easing(c, bench),
        "trend": (1.0 if (above200 and rising200) else 0.5 if above200 else 0.0),
    }
    score = 100.0 * sum(_COIL_W[k] * legs[k] for k in _COIL_W)
    if htf_turning:
        score = min(100.0, score + 8.0)  # higher-TF is confirming the turn
    lead = legs["divergence"] > 0 or legs["mtf_turn"] >= 0.2

    if htf_falling:
        stage = "knife"
    elif not lead:
        stage = "watch"
    elif above200 and rising200 and (htf_turning or legs["divergence"] >= 0.6):
        stage = "primed"
    else:
        stage = "coiling"

    return {
        "coil_score": round(score, 1), "stage": stage, "lead": lead,
        "htf_falling": htf_falling, "htf_turning": htf_turning,
        "above200": above200, "rising200": rising200,
        "tf": {"W": _tf_dir(W), "2W": _tf_dir(bw), "M": _tf_dir(M), "3D": _tf_dir(D3)},
        "legs": {k: round(v, 2) for k, v in legs.items()},
    }
