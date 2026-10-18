"""Vol-weather organ — display-only volatility context chips (VSB masterplan W3).

Implements compute_vol_weather() -> dict | None, exposing a strip of volatility-
surface context chips for the Market Sentiment dialog.  The chips are pure display
tier: they feed NO score, NO gate, NO forward claim.

RRX-R10 kill compliance: ALL threshold bands are percentile/relative constructions
computed against trailing history.  The ONLY absolute boundary used is the
VIX9D/VIX3M > 1.0 inversion line (chip: term_slope) — this is a DEFINITIONAL
backwardation boundary, not a tuned threshold (see comment at the relevant code).

Chips:
  vix_level     — VIX close 252d trailing percentile rank
  vix_velocity  — VIX 5-day-change percentile (+ 20d secondary); spike/fall state
  vvix_vix      — VVIX/VIX divergence chip
  term_slope    — VIX9D/VIX3M term structure state
  vix1d         — CBOE VIX1D 252d percentile
  dspx          — CBOE DSPX (single-name vol) 252d percentile + VIXEQ−VIX gap
  cor1m         — CBOE COR1M 1-month implied correlation percentile
  cor3m         — CBOE COR3M 3-month implied correlation percentile

All chips follow the absent-safe idiom: a missing file/column returns a chip with
freshness='missing', pctile=None, and plain-word copy saying data is unavailable.
A Young chip (<252 obs) returns freshness='young', pctile=None, copy='still
collecting history'.

Top-level payload:
  {
    chips: [...],                 # list of chip dicts
    as_of: "YYYY-MM-DD",         # MAX last_date across non-missing chips
    generated_utc: "...",
    n_young: int,
    disclaimer_en: str,
    disclaimer_zh: str,
  }

Returns None only if ALL chips are missing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lib import config, store

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Calibration overlay — all percentile band thresholds live here so a
# calibration pass can retune without touching chip logic.
# ---------------------------------------------------------------------------
_BANDS: dict = {
    # vix_level: percentile bands (0-100)
    "vix_level": {
        "calm":     25,   # below this -> calm
        "normal":   75,   # 25-75 -> normal
        "elevated": 90,   # 75-90 -> elevated, >=90 -> stressed
    },
    # vix_velocity: percentile thresholds for spike/fall states
    "vix_velocity": {
        "spiking":      95,   # >=95 -> spiking
        "rising_fast":  85,   # >=85 -> rising_fast
        "falling_hard":  5,   # <=5  -> falling_hard
    },
    # vvix_vix divergence: thresholds
    "vvix_vix": {
        "vvix_pctile_hi": 70,   # VVIX pctile >= this
        "vix_pctile_lo":  40,   # VIX pctile  <= this
    },
    # term_slope: percentile bands for non-inverted state classification
    "term_slope": {
        "steep_contango": 20,   # <=20 -> steep_contango
        "flattening":     80,   # >80  -> flattening, else normal
    },
    # cboe family chips: percentile thresholds (same construction as vix_level)
    "cboe_chip": {
        "low":  25,
        "high": 75,
    },
}

MIN_OBS = 252          # gate for ANY percentile (below -> pctile None, freshness 'young')
_STALE_CALENDAR_DAYS = 10   # freshness window (<=10 calendar days -> 'fresh')
_SPARK_WINDOW = 60     # last N daily pctile ints for spark


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _r(x, n: int = 2):
    """Round x to n decimal places; return None for NaN/inf/None."""
    if x is None:
        return None
    try:
        f = float(x)
        return round(f, n) if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _freshness(ts: pd.Timestamp | None) -> str:
    """'fresh' / 'stale' / 'missing' based on calendar days since last obs."""
    if ts is None:
        return "missing"
    try:
        today = pd.Timestamp.now(tz=None).normalize()
        delta = (today - pd.Timestamp(ts)).days
        return "fresh" if delta <= _STALE_CALENDAR_DAYS else "stale"
    except Exception:   # noqa: BLE001
        return "missing"


def _trailing_pctile(series: pd.Series, window: int = MIN_OBS) -> pd.Series:
    """252-obs trailing percentile rank, MIDRANK form (tie-robust).

    pctile[t] = (count(< series[t]) + 0.5 * count(== series[t])) / window * 100
    over the window [t-window+1..t]. No look-ahead.

    Midrank instead of (<= latest) on purpose: a frozen/repeating feed makes the
    window all-ties, which the naive inclusive form scores as pctile 100 — i.e. a
    stale feed would read as an extreme ("spiking") at exactly the moment the data
    is broken. Midrank scores an all-tied window as 50 (neutral). On continuous
    data the two forms differ by <=0.2pp (the half-weight self-tie).
    """
    if len(series) < window:
        return pd.Series(np.nan, index=series.index)
    return series.rolling(window, min_periods=window).apply(
        lambda w: (float(np.sum(w < w[-1])) + 0.5 * float(np.sum(w == w[-1])))
        / len(w) * 100,
        raw=True,
    )


def _spark(pctile_series: pd.Series) -> list[int] | None:
    """Last 60 daily pctile ints; None if the series has no valid rows."""
    s = pctile_series.dropna()
    if s.empty:
        return None
    tail = s.tail(_SPARK_WINDOW)
    return [int(round(v)) for v in tail]


def _last_date(series: pd.Series) -> str | None:
    """ISO date of last valid observation in the index."""
    s = series.dropna()
    if s.empty:
        return None
    ts = s.index[-1]
    try:
        return pd.Timestamp(ts).strftime("%Y-%m-%d")
    except Exception:   # noqa: BLE001
        return None


def _missing_chip(key: str, name_en: str, name_zh: str, extra: dict | None = None) -> dict:
    """Return a chip with freshness='missing' and null numerics."""
    base = {
        "key": key, "name_en": name_en, "name_zh": name_zh,
        "value": None, "pctile": None, "band": None, "state": None,
        "plain_en": "No data available.", "plain_zh": "数据暂不可用。",
        "freshness": "missing", "obs_count": None,
        "last_date": None, "spark": None,
    }
    if extra:
        base.update(extra)
    return base


def _young_chip(key: str, name_en: str, name_zh: str, value, obs: int,
                last_dt: str | None, extra: dict | None = None) -> dict:
    """Return a chip with freshness='young' — pctile None, plain copy 'still collecting'."""
    base = {
        "key": key, "name_en": name_en, "name_zh": name_zh,
        "value": value, "pctile": None, "band": None, "state": None,
        "plain_en": "Still collecting history.",
        "plain_zh": "数据历史尚短，仍在积累中。",
        "freshness": "young", "obs_count": obs,
        "last_date": last_dt, "spark": None,
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Chip builders
# ---------------------------------------------------------------------------

def _chip_vix_level() -> dict:
    """VIX close 252d trailing percentile rank."""
    key = "vix_level"
    name_en, name_zh = "VIX level", "VIX 水平"
    try:
        vix = store.read("yahoo", "_VIX")
        if vix is None or "close" not in vix.columns:
            return _missing_chip(key, name_en, name_zh)
        c = vix["close"].dropna()
        obs = int(len(c))
        last_dt = _last_date(c)
        fresh = _freshness(pd.Timestamp(c.index[-1]) if obs else None)
        val = _r(float(c.iloc[-1]), 1) if obs else None
        if obs < MIN_OBS:
            return _young_chip(key, name_en, name_zh, val, obs, last_dt)
        pct_series = _trailing_pctile(c)
        pct_val = pct_series.dropna().iloc[-1] if not pct_series.dropna().empty else None
        pct = int(round(pct_val)) if pct_val is not None else None
        # Band classification (thresholds from _BANDS)
        b = _BANDS["vix_level"]
        if pct is not None:
            if pct < b["calm"]:
                band, state = "calm", "calm"
                plain_en = "Volatility is low by recent standards."
                plain_zh = "近期波动率偏低。"
            elif pct < b["normal"]:
                band, state = "normal", "normal"
                plain_en = "Volatility is in a normal range."
                plain_zh = "波动率处于正常区间。"
            elif pct < b["elevated"]:
                band, state = "elevated", "elevated"
                plain_en = "Volatility is running above average — options are pricing in more uncertainty."
                plain_zh = "波动率高于均值，期权隐含不确定性上升。"
            else:
                band, state = "stressed", "stressed"
                plain_en = "Volatility is near historical highs — the market is pricing in significant stress."
                plain_zh = "波动率接近历史高位，市场正在对重大压力定价。"
        else:
            band, state, plain_en, plain_zh = None, None, "Percentile unavailable.", "百分位暂不可用。"
        spark = _spark(pct_series)
        return {
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "value": val, "pctile": pct, "band": band, "state": state,
            "plain_en": plain_en, "plain_zh": plain_zh,
            "freshness": fresh, "obs_count": obs,
            "last_date": last_dt, "spark": spark,
        }
    except Exception as e:   # noqa: BLE001
        log.warning("%s chip failed: %s", key, e)
        return _missing_chip(key, name_en, name_zh)


def _chip_vix_velocity() -> dict:
    """VIX 5-day-change percentile rank + 20d secondary; spike/fall state."""
    key = "vix_velocity"
    name_en, name_zh = "VIX velocity (5d change)", "VIX 速度（5日变动）"
    try:
        vix = store.read("yahoo", "_VIX")
        if vix is None or "close" not in vix.columns:
            return _missing_chip(key, name_en, name_zh, {"chg20_pctile": None})
        c = vix["close"].dropna()
        obs = int(len(c))
        last_dt = _last_date(c)
        fresh = _freshness(pd.Timestamp(c.index[-1]) if obs else None)
        chg5 = c.diff(5).dropna()
        chg20 = c.diff(20).dropna()
        val = _r(float(chg5.iloc[-1]), 2) if len(chg5) else None
        if obs < MIN_OBS:
            return _young_chip(key, name_en, name_zh, val, obs, last_dt,
                               extra={"chg20_pctile": None})
        # 5d change percentile
        pct5_series = _trailing_pctile(chg5)
        pct5_val = pct5_series.dropna().iloc[-1] if not pct5_series.dropna().empty else None
        pct5 = int(round(pct5_val)) if pct5_val is not None else None
        # 20d change percentile
        pct20_series = _trailing_pctile(chg20)
        pct20_val = pct20_series.dropna().iloc[-1] if not pct20_series.dropna().empty else None
        pct20 = int(round(pct20_val)) if pct20_val is not None else None
        # State classification
        b = _BANDS["vix_velocity"]
        if pct5 is not None:
            if pct5 >= b["spiking"]:
                state = "spiking"
                plain_en = "Volatility is spiking sharply — one of the fastest moves in recent history."
                plain_zh = "波动率急剧飙升，属近期历史上最快的上升之一。"
            elif pct5 >= b["rising_fast"]:
                state = "rising_fast"
                plain_en = "Volatility is rising quickly."
                plain_zh = "波动率正在快速上升。"
            elif pct5 <= b["falling_hard"]:
                state = "falling_hard"
                plain_en = "Volatility is dropping sharply — one of the fastest declines in recent history."
                plain_zh = "波动率急剧下降，属近期历史上最快的回落之一。"
            else:
                state = "quiet"
                plain_en = "Volatility change is within normal daily variation."
                plain_zh = "波动率变化处于正常日常波动范围内。"
        else:
            state = None
            plain_en = "Percentile unavailable."
            plain_zh = "百分位暂不可用。"
        spark = _spark(pct5_series)
        return {
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "value": val, "pctile": pct5, "band": state, "state": state,
            "chg20_pctile": pct20,
            "plain_en": plain_en, "plain_zh": plain_zh,
            "freshness": fresh, "obs_count": obs,
            "last_date": last_dt, "spark": spark,
        }
    except Exception as e:   # noqa: BLE001
        log.warning("%s chip failed: %s", key, e)
        return _missing_chip(key, name_en, name_zh, {"chg20_pctile": None})


def _chip_vvix_vix() -> dict:
    """VVIX/VIX ratio percentile chip; divergence flag when VVIX is bid vs calm VIX."""
    key = "vvix_vix"
    name_en, name_zh = "VVIX / VIX divergence", "VVIX / VIX 背离"
    try:
        vvix_path = config.data_dir() / "cboe" / "vvix.parquet"
        if not vvix_path.exists():
            return _missing_chip(key, name_en, name_zh,
                                 {"vvix_pctile": None, "vix_pctile": None, "divergence": False})
        vvix_df = pd.read_parquet(vvix_path).sort_index()
        # Column may be named 'vvix' or 'close'
        col = "vvix" if "vvix" in vvix_df.columns else ("close" if "close" in vvix_df.columns else None)
        if col is None or vvix_df[col].dropna().empty:
            return _missing_chip(key, name_en, name_zh,
                                 {"vvix_pctile": None, "vix_pctile": None, "divergence": False})
        vvix = vvix_df[col].dropna()

        vix_raw = store.read("yahoo", "_VIX")
        if vix_raw is None or "close" not in vix_raw.columns:
            return _missing_chip(key, name_en, name_zh,
                                 {"vvix_pctile": None, "vix_pctile": None, "divergence": False})
        vix_c = vix_raw["close"].dropna()

        # Align on common dates
        vvix_a, vix_a = vvix.align(vix_c, join="inner")
        obs = int(len(vvix_a))
        last_dt = _last_date(vvix_a) if obs else None
        fresh = _freshness(pd.Timestamp(vvix_a.index[-1]) if obs else None)
        ratio_val = _r(float(vvix_a.iloc[-1]) / float(vix_a.iloc[-1]), 3) if obs else None

        if obs < MIN_OBS:
            return _young_chip(key, name_en, name_zh, ratio_val, obs, last_dt,
                               extra={"vvix_pctile": None, "vix_pctile": None, "divergence": False})

        # 252d trailing pctiles
        vvix_pct_series = _trailing_pctile(vvix_a)
        vix_pct_series  = _trailing_pctile(vix_a)
        vvix_pct_val = vvix_pct_series.dropna().iloc[-1] if not vvix_pct_series.dropna().empty else None
        vix_pct_val  = vix_pct_series.dropna().iloc[-1]  if not vix_pct_series.dropna().empty  else None
        vvix_pct = int(round(vvix_pct_val)) if vvix_pct_val is not None else None
        vix_pct  = int(round(vix_pct_val))  if vix_pct_val  is not None else None

        # Divergence flag (thresholds from _BANDS)
        b = _BANDS["vvix_vix"]
        divergence = bool(
            vvix_pct is not None and vix_pct is not None
            and vvix_pct >= b["vvix_pctile_hi"]
            and vix_pct  <= b["vix_pctile_lo"]
        )

        if divergence:
            plain_en = ("Insurance on volatility itself is getting bid while the surface looks "
                        "calm — watch, don't chase.")
            plain_zh = "波动率的波动率正在被推高，而表面看起来仍然平静——观察，不要追。"
            band, state = "diverging", "diverging"
        elif vvix_pct is not None:
            if vvix_pct >= b["vvix_pctile_hi"]:
                plain_en = "Implied vol-of-vol is elevated — traders are paying up for vol protection."
                plain_zh = "隐含波动率的波动率偏高，交易者正在为波动保护付出更高溢价。"
                band, state = "elevated", "elevated"
            else:
                plain_en = "Implied vol-of-vol is within normal range."
                plain_zh = "隐含波动率的波动率处于正常区间。"
                band, state = "normal", "normal"
        else:
            plain_en = "Percentile unavailable."
            plain_zh = "百分位暂不可用。"
            band, state = None, None

        spark = _spark(vvix_pct_series)
        return {
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "value": ratio_val, "pctile": vvix_pct, "band": band, "state": state,
            "vvix_pctile": vvix_pct, "vix_pctile": vix_pct, "divergence": divergence,
            "plain_en": plain_en, "plain_zh": plain_zh,
            "freshness": fresh, "obs_count": obs,
            "last_date": last_dt, "spark": spark,
        }
    except Exception as e:   # noqa: BLE001
        log.warning("%s chip failed: %s", key, e)
        return _missing_chip(key, name_en, name_zh,
                             {"vvix_pctile": None, "vix_pctile": None, "divergence": False})


def _chip_term_slope() -> dict:
    """VIX9D/VIX3M term structure state chip.

    The ratio > 1.0 boundary is DEFINITIONAL: VIX9D > VIX3M means near-term
    demand exceeds far-term demand (textbook backwardation) — this is a
    definitional boundary, NOT a tuned threshold.
    All other state thresholds are percentile/relative (RRX-R10 compliant).
    """
    key = "term_slope"
    name_en, name_zh = "VIX term slope (9D / 3M)", "VIX 期限斜率（9D / 3M）"
    try:
        v9  = store.read("yahoo", "_VIX9D")
        v3m = store.read("yahoo", "_VIX3M")
        if v9 is None or v3m is None:
            return _missing_chip(key, name_en, name_zh)
        c9  = v9["close"].dropna()  if "close" in v9.columns  else pd.Series(dtype=float)
        c3m = v3m["close"].dropna() if "close" in v3m.columns else pd.Series(dtype=float)
        c9, c3m = c9.align(c3m, join="inner")
        obs = int(len(c9))
        last_dt = _last_date(c9) if obs else None
        fresh = _freshness(pd.Timestamp(c9.index[-1]) if obs else None)
        ratio = (c9 / c3m.replace(0, np.nan)).dropna()
        val = _r(float(ratio.iloc[-1]), 3) if len(ratio) else None

        # DEFINITIONAL boundary: ratio > 1.0 = backwardation (near > far demand)
        # This is NOT a tuned constant — it is a mathematical definition.
        if val is not None and val > 1.0:
            band, state = "inverted", "inverted"
            plain_en = ("Near-term vol demand exceeds longer-term — the curve is inverted, "
                        "a sign of acute near-term stress.")
            plain_zh = "近端波动率需求超过远端，曲线倒挂，显示短期压力明显。"
            pct = None
            spark = None
            return {
                "key": key, "name_en": name_en, "name_zh": name_zh,
                "value": val, "pctile": pct, "band": band, "state": state,
                "plain_en": plain_en, "plain_zh": plain_zh,
                "freshness": fresh, "obs_count": obs,
                "last_date": last_dt, "spark": spark,
            }

        # Not inverted — use percentile banding on contango depth
        if obs < MIN_OBS:
            return _young_chip(key, name_en, name_zh, val, obs, last_dt)
        pct_series = _trailing_pctile(ratio)
        pct_val = pct_series.dropna().iloc[-1] if not pct_series.dropna().empty else None
        pct = int(round(pct_val)) if pct_val is not None else None
        b = _BANDS["term_slope"]
        if pct is not None:
            if pct <= b["steep_contango"]:
                band, state = "steep_contango", "steep_contango"
                plain_en = "The curve is steeply in contango — vol market is calm, sellers in control."
                plain_zh = "曲线深度顺结构，波动率市场平静，做空方占主导。"
            elif pct > b["flattening"]:
                band, state = "flattening", "flattening"
                plain_en = "The term structure is flattening — watch for a potential inversion ahead."
                plain_zh = "期限结构正在平坦化，需关注可能的倒挂风险。"
            else:
                band, state = "normal", "normal"
                plain_en = "Term structure is normal — vol market shows no unusual stress."
                plain_zh = "期限结构正常，波动率市场无异常压力。"
        else:
            band, state = None, None
            plain_en = "Percentile unavailable."
            plain_zh = "百分位暂不可用。"
        spark = _spark(pct_series)
        return {
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "value": val, "pctile": pct, "band": band, "state": state,
            "plain_en": plain_en, "plain_zh": plain_zh,
            "freshness": fresh, "obs_count": obs,
            "last_date": last_dt, "spark": spark,
        }
    except Exception as e:   # noqa: BLE001
        log.warning("%s chip failed: %s", key, e)
        return _missing_chip(key, name_en, name_zh)


def _chip_cboe_simple(key: str, name_en: str, name_zh: str,
                       filename: str, plain_hi: str, plain_hi_zh: str,
                       plain_lo: str, plain_lo_zh: str,
                       plain_normal: str, plain_normal_zh: str,
                       extra_builder=None) -> dict:
    """Generic chip builder for CBOE cboe/ parquets with 'close' column.

    extra_builder: optional callable(df, last_dt) -> dict of secondary fields.
    """
    try:
        path = config.data_dir() / "cboe" / filename
        if not path.exists():
            chip = _missing_chip(key, name_en, name_zh)
            if extra_builder:
                chip.update(extra_builder(None, None))
            return chip
        df = pd.read_parquet(path).sort_index()
        if "close" not in df.columns or df["close"].dropna().empty:
            chip = _missing_chip(key, name_en, name_zh)
            if extra_builder:
                chip.update(extra_builder(None, None))
            return chip
        c = df["close"].dropna()
        obs = int(len(c))
        last_dt = _last_date(c)
        fresh = _freshness(pd.Timestamp(c.index[-1]) if obs else None)
        val = _r(float(c.iloc[-1]), 2) if obs else None
        extras = extra_builder(df, last_dt) if extra_builder else {}
        if obs < MIN_OBS:
            chip = _young_chip(key, name_en, name_zh, val, obs, last_dt)
            chip.update(extras)
            return chip
        pct_series = _trailing_pctile(c)
        pct_val = pct_series.dropna().iloc[-1] if not pct_series.dropna().empty else None
        pct = int(round(pct_val)) if pct_val is not None else None
        b = _BANDS["cboe_chip"]
        if pct is not None:
            if pct >= b["high"]:
                band, state = "high", "high"
                plain_en, plain_zh = plain_hi, plain_hi_zh
            elif pct <= b["low"]:
                band, state = "low", "low"
                plain_en, plain_zh = plain_lo, plain_lo_zh
            else:
                band, state = "normal", "normal"
                plain_en, plain_zh = plain_normal, plain_normal_zh
        else:
            band, state = None, None
            plain_en, plain_zh = "Percentile unavailable.", "百分位暂不可用。"
        spark = _spark(pct_series)
        chip = {
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "value": val, "pctile": pct, "band": band, "state": state,
            "plain_en": plain_en, "plain_zh": plain_zh,
            "freshness": fresh, "obs_count": obs,
            "last_date": last_dt, "spark": spark,
        }
        chip.update(extras)
        return chip
    except Exception as e:   # noqa: BLE001
        log.warning("%s chip failed: %s", key, e)
        chip = _missing_chip(key, name_en, name_zh)
        if extra_builder:
            chip.update(extra_builder(None, None))
        return chip


def _vixeq_minus_vix_builder(df_dspx, last_dt: str | None):
    """Secondary field: VIXEQ minus VIX at the last common date (single-name vs index gap)."""
    try:
        vixeq_path = config.data_dir() / "cboe" / "vixeq.parquet"
        vix_raw = store.read("yahoo", "_VIX")
        if not vixeq_path.exists() or vix_raw is None or "close" not in vix_raw.columns:
            return {"vixeq_minus_vix": None}
        vixeq_df = pd.read_parquet(vixeq_path).sort_index()
        if "close" not in vixeq_df.columns:
            return {"vixeq_minus_vix": None}
        vixeq_c = vixeq_df["close"].dropna()
        vix_c = vix_raw["close"].dropna()
        aligned, vix_aligned = vixeq_c.align(vix_c, join="inner")
        if aligned.empty:
            return {"vixeq_minus_vix": None}
        gap = float(aligned.iloc[-1]) - float(vix_aligned.iloc[-1])
        return {"vixeq_minus_vix": _r(gap, 1)}
    except Exception:   # noqa: BLE001
        return {"vixeq_minus_vix": None}


def _chip_vix1d() -> dict:
    return _chip_cboe_simple(
        key="vix1d",
        name_en="VIX1D (intraday vol demand)",
        name_zh="VIX1D（盘中波动需求）",
        filename="vix1d.parquet",
        plain_hi="Very short-term vol demand is high — traders are paying up for same-day protection.",
        plain_hi_zh="超短期波动需求偏高，交易者正为当日保护支付溢价。",
        plain_lo="Very short-term vol demand is low — intraday hedging costs are below average.",
        plain_lo_zh="超短期波动需求偏低，盘中对冲成本低于均值。",
        plain_normal="Very short-term vol demand is normal.",
        plain_normal_zh="超短期波动需求处于正常水平。",
    )


def _chip_dspx() -> dict:
    """DSPX chip with secondary field: VIXEQ − VIX single-name-vs-index gap."""
    return _chip_cboe_simple(
        key="dspx",
        name_en="DSPX (single-stock vol vs index)",
        name_zh="DSPX（个股波动 vs 指数）",
        filename="dspx.parquet",
        plain_hi="Single-stock vol is running well above index vol — individual names are unusually risky relative to the market.",
        plain_hi_zh="个股波动率远高于指数波动率，个股相对市场的风险溢价偏高。",
        plain_lo="Single-stock vol is subdued relative to index vol — stocks are moving in lockstep.",
        plain_lo_zh="个股波动率相对指数偏低，个股走势趋于同步。",
        plain_normal="Single-stock vol is in line with index vol.",
        plain_normal_zh="个股波动率与指数波动率基本一致。",
        extra_builder=_vixeq_minus_vix_builder,
    )


def _chip_cor1m() -> dict:
    return _chip_cboe_simple(
        key="cor1m",
        name_en="COR1M (1-month implied correlation)",
        name_zh="COR1M（1个月隐含相关性）",
        filename="cor1m.parquet",
        plain_hi="Stocks are moving together more than usual — diversification is offering less protection than normal.",
        plain_hi_zh="股票正以高于寻常的同步性运动，分散化保护效果弱于正常水平。",
        plain_lo="Stocks are moving more independently — the market is rewarding stock selection.",
        plain_lo_zh="股票走势更加独立，市场正在奖励个股选择能力。",
        plain_normal="How much stocks move together is within the normal range.",
        plain_normal_zh="股票的同步程度处于正常区间。",
    )


def _chip_cor3m() -> dict:
    return _chip_cboe_simple(
        key="cor3m",
        name_en="COR3M (3-month implied correlation)",
        name_zh="COR3M（3个月隐含相关性）",
        filename="cor3m.parquet",
        plain_hi="Stocks are expected to move together over the coming quarter — diversification is likely to underperform.",
        plain_hi_zh="预计未来一个季度股票将高度同步，分散化可能表现欠佳。",
        plain_lo="Stocks are expected to behave more independently over the coming quarter.",
        plain_lo_zh="预计未来一个季度股票走势将更加独立。",
        plain_normal="Expected co-movement among stocks over the next quarter is normal.",
        plain_normal_zh="预期未来一季度股票间的联动程度处于正常区间。",
    )


# ---------------------------------------------------------------------------
# Top-level compute
# ---------------------------------------------------------------------------

def compute_vol_weather() -> dict | None:
    """Compute the vol-weather chip strip payload.

    Masterplan: VSB W3.
    RRX-R10 compliance: all band thresholds are percentile/relative constructions.
    The sole absolute boundary (VIX9D/VIX3M > 1.0) is definitional backwardation.
    Display-only: chips feed no score, no gate, no forward claim.

    Returns None only if ALL chips are missing.
    """
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    chips = [
        _chip_vix_level(),
        _chip_vix_velocity(),
        _chip_vvix_vix(),
        _chip_term_slope(),
        _chip_vix1d(),
        _chip_dspx(),
        _chip_cor1m(),
        _chip_cor3m(),
    ]

    # as_of = max last_date across non-missing chips
    dates = [c["last_date"] for c in chips if c.get("last_date") is not None]
    if not dates:
        return None     # all missing
    as_of = max(dates)

    n_young = sum(1 for c in chips if c.get("freshness") in ("young", "missing"))

    return {
        "chips": chips,
        "as_of": as_of,
        "generated_utc": generated,
        "n_young": n_young,
        "disclaimer_en": (
            "Display-only context — volatility surface indicators from public CBOE / "
            "Yahoo data. Never scored, no forward claim. These chips describe the current "
            "vol environment; they do not predict direction."
        ),
        "disclaimer_zh": (
            "仅供展示的背景 — 来自公开 CBOE / Yahoo 数据的波动率曲面指标。"
            "不计分，无前瞻判断。这些芯片描述当前波动率环境，不预测方向。"
        ),
    }


# Fear/Greed dynamics v1: descriptive extensions of this existing volatility owner.
# No changes to the accepted regime engine, score weights, alerts or trade gates.
def session_series(series: pd.Series | None, as_of=None, *, positive=False) -> pd.Series:
    """Daily NYSE-session grid, cutoff before calculation; gaps are never filled.

    Conflicting duplicate dates become unknown instead of choosing a correction
    without its publication time. Daily labels retain their exchange-date meaning.
    Historical stores are revised observations, NOT point-in-time vintages.
    """
    from lib import nyse_calendar

    if series is None or not len(series):
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    end = pd.Timestamp(as_of or nyse_calendar.expected_last_session()).tz_localize(None).normalize()
    idx = pd.to_datetime(series.index, errors="coerce")
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    s = pd.Series(pd.to_numeric(series, errors="coerce").to_numpy(), index=idx.normalize())
    s = s.loc[s.index.notna() & (s.index <= end)].sort_index()
    s = s.replace([np.inf, -np.inf], np.nan)
    if positive:
        s = s.where(s > 0)
    if s.empty:
        return s
    # Same-value duplicate rows are harmless; conflicting values are not.
    if s.index.has_duplicates:
        s = s.groupby(level=0).agg(lambda x: x.iloc[0] if x.nunique(dropna=False) == 1 else np.nan)
    days = nyse_calendar.sessions_between(s.index.min().date(), end.date())
    return s.reindex(pd.DatetimeIndex(days))


def causal_midrank(series: pd.Series, window=252) -> pd.Series:
    """252 valid observations within at most 504 sessions; no short-history promotion.

    Gaps remain missing, but do not erase a whole year of valid observations.
    The age ceiling prevents ancient pre-gap history becoming today's baseline.
    All-tied windows rank at 50. Reindexed missing sessions stay missing.
    """
    valid = series.dropna()
    positions = pd.Series(np.arange(len(series)), index=series.index).loc[valid.index]
    rank = 100 * valid.rolling(window, min_periods=window).rank(method="average", pct=True) - 50 / window
    rank = rank.where(positions - positions.shift(window - 1) < 2 * window)
    return rank.reindex(series.index)


def vix_dynamics_frame(vix: pd.Series, as_of=None) -> pd.DataFrame:
    """Causal level, signed log velocity and its first difference per session.

    velocity = EWMA_5(100 * diff(log(VIX))); acceleration = diff(velocity).
    EWMA starts over after every absent/invalid return and needs five returns.
    Positive acceleration with negative velocity means relief is SLOWING.
    """
    c = session_series(vix, as_of, positive=True)
    out = pd.DataFrame({"vix": c})
    raw = 100 * np.log(c).diff()
    groups = raw.isna().cumsum()
    vel = raw.groupby(groups).transform(lambda x: x.ewm(span=5, adjust=False, min_periods=5).mean())
    out["velocity"] = vel
    out["acceleration"] = vel.diff()
    out["level_percentile"] = causal_midrank(c)
    out["velocity_percentile"] = causal_midrank(vel)
    out["acceleration_percentile"] = causal_midrank(out.acceleration)
    for h in (1, 5, 20):
        # A missing intermediate session invalidates the whole measurement.
        complete = c.rolling(h + 1, min_periods=h + 1).count().eq(h + 1)
        out[f"change_{h}d_pct"] = (100 * (c / c.shift(h) - 1)).where(complete)
        out[f"change_{h}d_points"] = c.diff(h).where(complete)
    out["phase"] = [volatility_phase(v, a) for v, a in zip(vel, out.acceleration)]
    for name, direction in (("up_sessions", 1), ("down_sessions", -1)):
        agrees = (direction * vel > 1e-10) & (direction * out.change_1d_points > 1e-10)
        out[name] = agrees.groupby((~agrees).cumsum()).cumsum().astype(int)
    return out


def volatility_phase(velocity, acceleration) -> str:
    """Signed quadrants, not percentile-only direction or a turning-point forecast."""
    if not np.isfinite(velocity) or not np.isfinite(acceleration):
        return "unavailable"
    # Numerical tolerance only; not an absolute VIX market-state threshold.
    if abs(velocity) < 1e-10:
        return "steady"
    if abs(acceleration) < 1e-10:
        return "rising_steady" if velocity > 0 else "falling_steady"
    if velocity > 0:
        return "stress_accelerating" if acceleration > 0 else "stress_decelerating"
    return "relief_accelerating" if acceleration < 0 else "relief_decelerating"


_DYNAMICS_COPY = {
    "unavailable": ("Risk direction unavailable", "风险方向暂不可用"),
    "steady": ("Volatility is steady", "波动率平稳"),
    "rising_steady": ("Risk is rising steadily", "风险持续上升"),
    "falling_steady": ("Risk is easing steadily", "风险持续缓解"),
    "stress_accelerating": ("Risk is rising faster", "风险加速上升"),
    "stress_decelerating": ("Risk is rising more slowly", "风险上升放缓"),
    "relief_accelerating": ("Risk is easing faster", "风险加速缓解"),
    "relief_decelerating": ("Relief is losing momentum", "风险缓解势头减弱"),
}


def compute_vix_dynamics(vix: pd.Series | None, *, vix3m=None, vix9d=None,
                         vvix=None, as_of=None) -> dict:
    """One authoritative calculation for Fear/Greed's descriptive VIX detail.

    All ratios use the SAME session. No stale tail is promoted to today's state.
    Curve ratios are spot implied-volatility horizons, NOT VIX futures roll yield.
    VVIX is options-implied volatility of forward VIX, NOT VIX acceleration.
    """
    from engine import canon
    from lib import nyse_calendar

    end = pd.Timestamp(as_of or nyse_calendar.expected_last_session()).tz_localize(None).normalize()
    end = pd.Timestamp(nyse_calendar.last_session_on_or_before(end.date()))
    frame = vix_dynamics_frame(vix, end)
    valid = frame.vix.dropna()
    last_date = valid.index[-1].strftime("%Y-%m-%d") if len(valid) else None
    current = frame.iloc[-1] if len(frame) else pd.Series(dtype=object)
    fresh = len(valid) > 0 and valid.index[-1] == end
    phase = str(current.get("phase", "unavailable")) if fresh else "unavailable"
    label_en, label_zh = _DYNAMICS_COPY[phase]
    out = {
        "schema": "mastermind.vix_dynamics.v1", "as_of": last_date,
        "expected_session": end.strftime("%Y-%m-%d"),
        "status": "fresh" if fresh else ("stale" if last_date else "missing"),
        "phase": phase, "label_en": label_en, "label_zh": label_zh,
        "velocity_unit": "log-percent per session", "acceleration_unit": "log-percent per session squared",
        "vix": _r(current.get("vix")), "velocity": _r(current.get("velocity"), 4),
        "acceleration": _r(current.get("acceleration"), 4),
        "level_percentile": _r(current.get("level_percentile"), 1),
        "velocity_percentile": _r(current.get("velocity_percentile"), 1),
        "acceleration_percentile": _r(current.get("acceleration_percentile"), 1),
        "mature": bool(fresh and pd.notna(current.get("acceleration_percentile"))),
        "up_sessions": 0, "down_sessions": 0, "term_ratio": None,
        "front_ratio": None, "term_change_5d": None, "curve_as_of": None,
        "vvix": None, "vvix_change_5d_pct": None, "vvix_percentile": None,
        "vvix_as_of": None, "vvix_status": "missing", "history": [],
    }
    for h in (1, 5, 20):
        for unit in ("pct", "points"):
            key = f"change_{h}d_{unit}"
            out[key] = _r(current.get(key), 3)
    if fresh:
        # Same streak definition is used by the research replay, without refitting.
        out["up_sessions"] = int(current.up_sessions)
        out["down_sessions"] = int(current.down_sessions)
        v3 = session_series(vix3m, end, positive=True)
        if len(v3):
            ratio = canon.vix_term(frame.vix, v3)
            out["term_ratio"] = _r(ratio.iloc[-1], 4)
            complete = ratio.tail(6).notna().all() and len(ratio) >= 6
            out["term_change_5d"] = _r(ratio.iloc[-1] - ratio.iloc[-6], 4) if complete else None
            if out["term_ratio"] is not None:
                out["curve_as_of"] = out["expected_session"]
        v9 = session_series(vix9d, end, positive=True)
        if len(v9):
            out["front_ratio"] = _r((v9.reindex(frame.index) / frame.vix).iloc[-1], 4)
    vv = session_series(vvix, end, positive=True)
    vv_valid = vv.dropna()
    if len(vv_valid):
        out["vvix_as_of"] = vv_valid.index[-1].strftime("%Y-%m-%d")
        out["vvix_status"] = "fresh" if vv_valid.index[-1] == end else "stale"
        if out["vvix_status"] == "fresh":
            out["vvix"] = _r(vv.iloc[-1])
            out["vvix_percentile"] = _r(causal_midrank(vv).iloc[-1], 1)
            if len(vv) >= 6 and vv.tail(6).notna().all():
                out["vvix_change_5d_pct"] = _r(100 * (vv.iloc[-1] / vv.iloc[-6] - 1), 3)
    for date, row in frame.tail(60).iterrows():
        out["history"].append({"date": date.strftime("%Y-%m-%d"),
                               **{k: _r(row[k], 4) for k in ("vix", "velocity", "acceleration")},
                               "phase": row.phase})
    return out
