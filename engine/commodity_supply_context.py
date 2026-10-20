"""Physical petroleum-balance CONTEXT helpers — a DISPLAY-ONLY read over the EIA
Weekly Petroleum Status Report.  LEAF: never imported by the scoring path, never
feeds conviction / alerts / MRS / latest.json.  Pure functions + thin callers.

WHY THIS IS DISPLAY-ONLY (and uses seasonal anomalies, not raw levels)
The original oil-supply read ranked crude stocks by a *raw* trailing percentile and
colored a 4-week draw green ("bullish") / build red.  Two problems that this module
fixes:

  * RAW LEVELS ARE A CALENDAR.  US crude/gasoline/distillate stocks have a large,
    deterministic annual cycle (refinery turnarounds, summer driving, heating oil).
    A raw z/percentile mostly measures the time of year.  We instead z-score the
    *seasonal anomaly* — today's deviation from the same-week-of-year climatology over
    a trailing 5y window — so the number reflects balance, not the calendar.

  * DRAW ≠ BULLISH.  The weekly EIA print is the most-arbitraged number in oil: it is
    released Wed 10:30 ET and the surprise-vs-consensus reprices within minutes, then
    it is gone.  Inventory *levels/draws* have weak forward-return predictability — the
    same single-asset-timing trap that sank the backwardation leg (see
    commodity_carry_context: 63d IC −0.16).  So this panel is neutral-colored and
    explicitly framed as physical BALANCE, not a price call.

Sign convention: seasonal-z is in NATURAL inventory units — NEGATIVE z = stocks below
their 5y seasonal norm = physically TIGHT; POSITIVE z = above norm = AMPLE.
"""
from __future__ import annotations

import datetime
from collections.abc import Mapping

import numpy as np
import pandas as pd

# Surfaced verbatim on the panel — the honesty layer.
SUPPLY_CAVEAT = {
    "en": ("Physical balance ≠ price direction. EIA weekly inventories are the most-"
           "arbitraged number in oil — the surprise reprices at the 10:30 ET release, "
           "not after — so this is a supply-tightness CONTEXT read, not a buy signal. "
           "Shown as deviation from the 5y seasonal norm (a draw in winter is normal)."),
    "zh": ("实物供需≠价格方向。EIA 每周库存是原油市场最被套利的数字——意外会在 10:30(美东)"
           "公布瞬间被price in，而非之后——故此为供给松紧的背景参考，而非买入信号。"
           "以相对5年季节常态的偏离展示（冬季去库本属正常）。"),
}


def _weekly(s: pd.Series | None) -> pd.Series | None:
    """Coerce a stored EIA series to a clean, datetime-indexed, sorted weekly series."""
    if s is None:
        return None
    s = pd.Series(s).copy()
    s.index = pd.to_datetime(s.index, errors="coerce")
    s = s[s.index.notna()].sort_index()
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return s if not s.empty else None


def last_value(s: pd.Series | None) -> float | None:
    """Latest finite value of a stored series, or None — NaN/empty safe."""
    s = _weekly(s)
    return None if s is None else float(s.iloc[-1])


def seasonal_z(s: pd.Series | None, years: int = 5) -> float | None:
    """Z-score of the latest value's SEASONAL ANOMALY vs the same-week-of-year
    climatology over a trailing `years` window.

    anomaly_t = value_t − mean(value | ISO-week(t), trailing window);
    z = anomaly_latest / std(anomalies).  Negative = below-season (tight).

    Returns None when there is too little history (< ~2y) or no dispersion."""
    s = _weekly(s)
    if s is None or len(s) < 104:                  # need ≥ ~2y of weekly prints
        return None
    window = s.iloc[-(years * 53):]                # ~5y of weekly obs (53 to cover ISO-53)
    woy = window.index.isocalendar().week.astype(int)
    clim = window.groupby(woy.values).transform("mean")   # per-week-of-year mean
    anom = window - clim
    sd = float(anom.std(ddof=0))
    if not np.isfinite(sd) or sd == 0:
        return None
    return float(anom.iloc[-1] / sd)


def delta_4w(s: pd.Series | None) -> float | None:
    """Latest minus ~4 weekly prints ago, in the series' native units (e.g. kbbl)."""
    s = _weekly(s)
    if s is None or len(s) < 2:
        return None
    return float(s.iloc[-1] - s.iloc[-min(5, len(s))])     # 4 steps back (inclusive guard)


def days_of_supply(stocks: pd.Series | None, demand: pd.Series | None,
                   weeks: int = 4) -> float | None:
    """Days of forward cover = latest stocks (kbbl) ÷ trailing-`weeks` mean daily
    demand (kbbl/d). Crude → refinery net inputs; products → product supplied.
    Returns None if either series is missing or demand is non-positive."""
    st = _weekly(stocks)
    dm = _weekly(demand)
    if st is None or dm is None:
        return None
    daily = float(dm.iloc[-weeks:].mean())
    if not np.isfinite(daily) or daily <= 0:
        return None
    return round(float(st.iloc[-1]) / daily, 1)


def balance_z(zmap: dict[str, float | None]) -> float | None:
    """Composite physical-balance gauge = mean of the available inventory seasonal-z's.
    Natural sign (negative = tight). DISPLAY summary only — never a scored leg."""
    vals = [v for v in zmap.values() if v is not None and np.isfinite(v)]
    if not vals:
        return None
    return float(np.mean(vals))


def balance_word(z: float | None) -> str:
    """Neutral 3-state label for the composite — NO directional (green/red) meaning."""
    if z is None:
        return "n/a"
    if z <= -0.5:
        return "tight"
    if z >= 0.5:
        return "ample"
    return "balanced"


# ---------------------------------------------------------------------------
# Three-stage physical petroleum-flow CONTEXT — a pure DISPLAY-ONLY consumer of
# four native EIA weekly series (MO-PAID-040 / MO-DELTA-027).  CONTEXT authority
# only: no price, score, execution or forecast authority, and NOT a traced barrel
# flow / mass balance — see PETROLEUM_FLOW_CAVEAT.
# ---------------------------------------------------------------------------

# A weekly period observation is stale for this panel once older than this many
# days relative to the explicit as_of.  A stale value stays VISIBLE with its
# historical date and an explicit "stale" status — it is never promoted current.
PETROLEUM_FLOW_STALE_AFTER_DAYS = 9

# Fixed, verified EIA series identities (Weekly Petroleum Status Report, weekly,
# native units thousand barrels per day).  Stage 3 is reported as two SEPARATE
# quantities — gasoline and distillate product supplied — never a summed total.
PETROLEUM_FLOW_SOURCES: dict[str, dict[str, str]] = {
    "crude_production": {
        "stage": "1_us_field_crude_production",
        "stage_description": "US field crude production",
        "eia_series_code": "WCRFPUS2",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCRFPUS2&f=W",
    },
    "refinery_inputs": {
        "stage": "2_us_refinery_net_crude_input",
        "stage_description": "US refinery net input of crude (includes imported crude)",
        "eia_series_code": "WCRRIUS2",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCRRIUS2&f=W",
    },
    "gasoline_supplied": {
        "stage": "3_us_product_supplied",
        "stage_description": "US gasoline product supplied — disappearance from primary supply, ~consumption",
        "eia_series_code": "WGFUPUS2",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WGFUPUS2&f=W",
    },
    "distillate_supplied": {
        "stage": "3_us_product_supplied",
        "stage_description": "US distillate product supplied — disappearance from primary supply, ~consumption",
        "eia_series_code": "WDIUPUS2",
        "source_url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WDIUPUS2&f=W",
    },
}

# Surfaced verbatim — the honesty layer for the flow panel.
PETROLEUM_FLOW_CAVEAT = {
    "en": ("Three aggregate industry stages — US field crude production, US refinery net "
           "input of crude, and gasoline & distillate product supplied — NOT a traced "
           "barrel flow, a conversion yield, a balance equality or exhaustive end-use "
           "consumption. Refinery input includes imported crude; product supplied measures "
           "disappearance from primary supply (approximately consumption), not direct "
           "end-user measurement. No mass-balance arrows, differences or ratios are computed."),
    "zh": ("三个加总产业阶段——美国原油田产量、美国炼厂原油净投入、汽油与馏分油产品供应——"
           "并非可追踪的桶流、转化收率、平衡等式或穷尽式终端消费。炼厂投入包含进口原油；"
           "产品供应度量一次供应端的消失量（近似消费），并非终端用户直接测量。"
           "不计算任何暗示质量平衡的箭头、差值或比率。"),
}

_PF_UNITS_NATIVE = "thousand barrels per day (kbbl/d)"
_PF_UNITS_DISPLAY = "million barrels per day (mbbl/d) = native / 1000"
_PF_RELEASE_NOTE = ("Stored EIA period series carry observation PERIODS only; a period end "
                    "is not a release/knowledge time, so known_at / published_at / "
                    "retrieved_at stay None rather than being invented from the calendar.")


def _pf_parse_as_of(as_of: object) -> pd.Timestamp:
    """Parse the EXPLICIT as_of (date / datetime / ISO string) to a normalized
    midnight-naive Timestamp.  No ambient clock is ever consulted; anything
    unparseable fails loudly with ValueError."""
    if isinstance(as_of, bool) or as_of is None:
        raise ValueError(f"petroleum_flow_context: invalid as_of {as_of!r}")
    if not isinstance(as_of, (datetime.date, np.datetime64, pd.Timestamp, str)):
        raise ValueError(
            f"petroleum_flow_context: invalid as_of type {type(as_of).__name__}: {as_of!r}"
        )
    try:
        # pandas accepts "now"/"today" using an ambient clock. This contract
        # accepts explicit ISO dates/times only, including for series periods.
        value = datetime.datetime.fromisoformat(as_of.replace("Z", "+00:00")) if isinstance(as_of, str) else as_of
        ts = pd.Timestamp(value)
    except Exception as exc:
        raise ValueError(f"petroleum_flow_context: invalid as_of {as_of!r}") from exc
    if ts is pd.NaT or pd.isna(ts):
        raise ValueError(f"petroleum_flow_context: invalid as_of {as_of!r}")
    if ts.tzinfo is not None:                      # pin tz-aware input to UTC, naive
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts.normalize()


def _pf_clean_series(s: pd.Series | None, as_of_ts: pd.Timestamp,
                     ) -> tuple[pd.Series | None, str | None]:
    """Validate one stored series into exact-date, finite, NON-NEGATIVE quantity
    observations at or before `as_of`.

    Returns (clean_series, reason).  Non-observations — NaN/inf, bools, non-numeric
    junk, negative quantities, unparseable periods — are skipped: never filled,
    never coerced to 0 (missing native data must not become 0).  Duplicate periods
    collapse only if their values are equal; conflicting values at one period fail
    that series CLOSED.  The caller's series object is never modified."""
    if s is None:
        return None, "missing"
    try:
        raw = pd.Series(s)
    except (TypeError, ValueError):
        return None, "not a pandas Series"
    if len(raw) == 0:
        return None, "empty"
    dates: list[pd.Timestamp] = []
    vals: list[float] = []
    for raw_dt, v in zip(raw.index, raw.values):
        # An integer index is not an observation date; do not interpret it as
        # nanoseconds since 1970. Normalize dated/tz-aware inputs consistently.
        try:
            dt = _pf_parse_as_of(raw_dt)
        except ValueError:
            continue
        if v is None or isinstance(v, (bool, np.bool_)):   # bool is NOT an observation
            continue
        try:
            f = float(v)                           # non-numeric junk is skipped
        except (TypeError, ValueError):
            continue
        if not np.isfinite(f) or f < 0:            # NaN/inf/negative are not quantities
            continue
        dates.append(pd.Timestamp(dt).normalize())
        vals.append(f)
    if not dates:
        return None, "no valid observations"
    clean = pd.Series(vals, index=pd.DatetimeIndex(dates), dtype="float64").sort_index()
    clean = clean[clean.index <= as_of_ts]         # observations after as_of excluded FIRST
    if clean.empty:
        return None, "no observations at or before as_of"
    for dt, grp in clean.groupby(clean.index):     # then duplicate-period integrity
        if grp.nunique() > 1:
            return None, (f"conflicting duplicate observations at period "
                          f"{pd.Timestamp(dt).date().isoformat()}")
    clean = clean[~clean.index.duplicated(keep="last")]   # identical duplicates collapse
    return clean, None


def petroleum_flow_context(series: Mapping[str, pd.Series | None], *, as_of: object) -> dict:
    """Three-stage physical petroleum-flow CONTEXT from four native EIA weekly series.

    Pure display-only read (MO-PAID-040 / MO-DELTA-027).  Requires `crude_production`,
    `refinery_inputs`, `gasoline_supplied` and `distillate_supplied` (pandas Series with
    EIA period date indexes, native kbbl/d) to have FINITE observations at one COMMON
    exact date at or before the explicit `as_of` — the LATEST such common date is
    selected.  No interpolation, no forward-fill, no ambient clock, no invented values:
    missing/empty/invalid series yield status "unavailable" with a reason and the list of
    unavailable inputs.  Duplicate periods collapse only when equal; conflicting
    duplicates close that series.  Observations after as_of are excluded, so a
    future-only series is unavailable, not zero.

    These are three AGGREGATE industry stages — NOT a traced barrel flow, conversion
    yield, balance equality or exhaustive end-use consumption (refinery input includes
    imported crude; product supplied ≈ disappearance from primary supply).  No
    mass-balance arithmetic is computed and NO total is emitted.  Context authority only:
    no price, score, execution or forecast authority.  A period end is not a release
    time, so known_at / published_at / retrieved_at stay None.
    """
    if not isinstance(series, Mapping):
        raise TypeError("petroleum_flow_context: `series` must be a mapping of the four "
                        "required EIA series")
    as_of_ts = _pf_parse_as_of(as_of)
    as_of_iso = as_of_ts.date().isoformat()

    cleaned: dict[str, pd.Series | None] = {}
    reasons: dict[str, str | None] = {}
    for name in PETROLEUM_FLOW_SOURCES:
        try:
            s = series[name]
        except (KeyError, TypeError):
            s = None
        cleaned[name], reasons[name] = _pf_clean_series(s, as_of_ts)

    entries: dict[str, dict] = {}
    for name, meta in PETROLEUM_FLOW_SOURCES.items():
        clean = cleaned[name]
        entry: dict = {
            "stage": meta["stage"],
            "stage_description": meta["stage_description"],
            "eia_series_code": meta["eia_series_code"],
            "source_url": meta["source_url"],
            "units": _PF_UNITS_NATIVE,
            "reason": reasons[name] if clean is None else None,
            "status": "observed" if clean is not None else "unavailable",
            "latest_period": None,
            "latest_value_kbbl_d": None,
            "display_value_mbbl_d": None,
            "at_selected_common_period": None,
        }
        if clean is not None:
            entry["latest_period"] = clean.index[-1].date().isoformat()
            entry["latest_value_kbbl_d"] = float(clean.iloc[-1])
            entry["display_value_mbbl_d"] = float(clean.iloc[-1]) / 1000.0
        entries[name] = entry

    missing = [n for n, c in cleaned.items() if c is None]
    period_ts: pd.Timestamp | None = None
    reason: str | None = None
    if missing:
        status = "unavailable"
        reason = "required series unavailable: " + "; ".join(
            f"{n} ({reasons[n]})" for n in missing)
    else:
        common: set[pd.Timestamp] = set(cleaned["crude_production"].index)
        for name in ("refinery_inputs", "gasoline_supplied", "distillate_supplied"):
            common &= set(cleaned[name].index)
        if not common:
            status = "unavailable"
            detail = ", ".join(f"{n}={cleaned[n].index[-1].date().isoformat()}"
                               for n in PETROLEUM_FLOW_SOURCES)
            reason = ("no common observation period with finite observations across all "
                      f"four required series at or before as_of (latest per series: {detail})")
        else:
            period_ts = max(common)
            age_days = int((as_of_ts - period_ts).days)
            status = "available" if age_days <= PETROLEUM_FLOW_STALE_AFTER_DAYS else "stale"
            for name, entry in entries.items():
                entry["at_selected_common_period"] = (
                    entry["latest_period"] == period_ts.date().isoformat())

    return {
        "status": status,
        "state": status,
        "reason": reason,
        "as_of": as_of_iso,
        "evaluated_on": as_of_iso,                 # the explicit as_of — never "now"
        "period": period_ts.date().isoformat() if period_ts is not None else None,
        "common_period": period_ts.date().isoformat() if period_ts is not None else None,
        # These selected-period values alone feed the panel. Per-series latest
        # metadata above must never mix newer weeks into this common-week read.
        "values": ({name: float(clean.loc[period_ts]) for name, clean in cleaned.items()}
                   if period_ts is not None else {}),
        "age_days": (int((as_of_ts - period_ts).days) if period_ts is not None else None),
        "stale_after_days": PETROLEUM_FLOW_STALE_AFTER_DAYS,
        "units": {"native": _PF_UNITS_NATIVE, "display": _PF_UNITS_DISPLAY},
        "series": entries,
        "unavailable_inputs": missing,
        "known_at": None,
        "published_at": None,
        "retrieved_at": None,
        "release_time_note": _PF_RELEASE_NOTE,
        "authority": "context_only",
        "authority_note": ("Descriptive physical-flow context only — no price, score, "
                           "execution or forecast authority."),
        "caveat": dict(PETROLEUM_FLOW_CAVEAT),
    }
