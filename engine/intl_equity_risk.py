"""Per-market equity-health / risk reads for the International dashboard
(DISPLAY-ONLY, descriptive).

For each country's primary index: distance from the 1y high, 50/200-day trend,
realised vol, RSI, and an own-history extension grade (reusing engine.extension —
the same in-trend/stretched/parabolic lens as the US Top-Picks board) for a
bubble / over-extension read. A 0-100 `drawdown_risk` gauge blends drawdown depth
+ below-trend + elevated vol with history-anchored bands. None of this is a
backtested signal — it is a cross-country market-stress comparator.
"""
from __future__ import annotations

import numbers

import numpy as np
import pandas as pd

from engine import intl_inputs
from engine.extension import extension_signals
from engine.technicals import rsi
from lib import config
from lib.intl_country_inputs import EQUITY_OBSERVATION_SCHEMA, equity_source_for


def _band(x: float | None) -> str:
    if x is None or np.isnan(x):
        return "n/a"
    if x >= 60:
        return "elevated"
    if x >= 35:
        return "watch"
    return "low"


def index_matrix() -> pd.DataFrame:
    closes = intl_inputs._intl_closes()
    cols = {cc: closes[c["index"]] for cc, c in intl_inputs.countries().items()
            if c["index"] in closes}
    return pd.DataFrame(cols).sort_index()



def _valid_equity_source_series(px: pd.Series) -> bool:
    """Require unambiguous provider daily labels and finite positive stored prices."""
    if not isinstance(px, pd.Series) or len(px) < 60:
        return False
    index = px.index
    if (not isinstance(index, pd.DatetimeIndex) or index.tz is not None or index.hasnans
            or index.has_duplicates or not index.is_monotonic_increasing
            or not index.equals(index.normalize())):
        return False
    for value in px:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
            return False
        try:
            if not np.isfinite(value) or value <= 0 or float(value) != value:
                return False
        except (TypeError, ValueError, OverflowError):
            return False
    return True


def _window_evidence(window, value, *, target, minimum, method):
    return {"method": method, "target_observations": target, "minimum_observations": minimum,
            "observations": len(window), "start": str(window.index[0].date()),
            "end": str(window.index[-1].date()),
            "value": float(value) if np.isfinite(value) else None}


def _source_evidence(px, source, *, last, ma50, ma200, hi52):
    if source is None or not _valid_equity_source_series(px):
        return None
    recent = px.iloc[-252:]
    high_matches = recent[recent.eq(hi52)]
    if high_matches.empty:
        return None
    return {
        "schema": EQUITY_OBSERVATION_SCHEMA, "source": source, "as_of": str(px.index[-1].date()),
        "rows": [[str(stamp.date()), float(value)] for stamp, value in recent.items()],
        "latest_close": float(last),
        "mean_50": _window_evidence(px.iloc[-50:], ma50, target=50, minimum=25, method="arithmetic_mean"),
        "mean_200": _window_evidence(px.iloc[-200:], ma200, target=200, minimum=100, method="arithmetic_mean"),
        "recent_high": {**_window_evidence(recent, hi52, target=252, minimum=60, method="maximum"),
                        "high_date": str(high_matches.index[-1].date()), "tie_policy": "most_recent"},
    }


def equity_risk_all(mat: pd.DataFrame | None = None) -> dict[str, dict]:
    canonical_input = mat is None
    source_countries = intl_inputs.countries() if canonical_input else {}
    if mat is None:
        mat = index_matrix()
    if mat.empty:
        return {}
    out: dict[str, dict] = {}
    for cc in mat.columns:
        px = mat[cc].dropna()
        if len(px) < 60:
            continue
        # per-index extension (own series only — avoids cross-market NaN holes
        # when one market trades on a day another doesn't)
        ex = extension_signals(px.to_frame(cc)).get(cc, {})
        last = float(px.iloc[-1])
        hi52 = float(px.rolling(252, min_periods=60).max().iloc[-1])
        off_high = (last / hi52 - 1.0) * 100 if hi52 else 0.0
        ma50 = float(px.rolling(50, min_periods=25).mean().iloc[-1])
        ma200 = float(px.rolling(200, min_periods=100).mean().iloc[-1]) if len(px) >= 100 else np.nan
        rv = float(px.pct_change(fill_method=None).rolling(21).std().iloc[-1]) * np.sqrt(252) * 100
        rsi_v = float(rsi(px).iloc[-1])

        dd_leg = np.clip(-off_high / 25.0, 0, 1)              # 0 at high, 1 at -25%
        trend_leg = 1.0 if (not np.isnan(ma200) and last < ma200) else 0.0
        vol_leg = np.clip((rv - 15.0) / 25.0, 0, 1)           # vol above 15% annualised
        ddrisk = round((0.5 * dd_leg + 0.3 * trend_leg + 0.2 * vol_leg) * 100, 0)

        grade = ex.get("grade", "na")
        bubble = grade in ("stretched", "parabolic") or (rsi_v >= 72 and off_high > -3)
        out[cc] = {
            "as_of": str(px.index[-1].date()),
            "high_window_observations": min(252, len(px)),
            "high_window_start": str(px.index[max(0, len(px) - 252)].date()),
            "trend_200d_complete": bool(len(px) >= 200),
            "price": round(last, 2), "off_52w_high": round(off_high, 1),
            "above_50d": bool(last > ma50),
            "above_200d": bool(not np.isnan(ma200) and last > ma200),
            "realvol": round(rv, 1), "rsi": round(rsi_v, 0),
            "ext_z": ex.get("ext_z"), "ext_grade": grade,
            "drawdown_risk": ddrisk, "drawdown_band": _band(ddrisk),
            "bubble_flag": bool(bubble),
        }

        # A caller-supplied matrix cannot acquire canonical Yahoo attribution.
        source = equity_source_for(cc) if canonical_input else None
        country_config = source_countries.get(cc)
        if (source is None or type(country_config) is not dict
                or country_config.get("index") != source["symbol"]):
            source = None
        out[cc]["observation_evidence"] = _source_evidence(
            px, source, last=last, ma50=ma50, ma200=ma200, hi52=hi52)
    return out
