"""Display-only US petroleum-balance context from the existing EIA cache.

Never feed conviction, alerts, scoring or latest.json. Inventory balance is not a
directional signal; see research/OIL_PHYSICAL_TIGHTNESS.md. Seasonal anomalies use
the existing ISO-week method. Explicit windows disclose actual history coverage.
Observation dates do not establish release availability or historical vintage.
"""
from __future__ import annotations

import datetime
from collections.abc import Mapping


from hashlib import sha256
import json

import numpy as np
import pandas as pd

PHYSICAL_SCHEMA = "mmx.commodities.petroleum_balance.v1"
METHOD_REVISION = "eia-seasonal-balance-20261020-r2"
SERIES = (
    "crude_stocks", "cushing_stocks", "gasoline_stocks", "distillate_stocks",
    "refinery_inputs", "gasoline_supplied", "distillate_supplied",
    "crude_production", "refinery_util", "spr_stocks",
)
SUPPLY_CAVEAT = {
    "en": ("Physical balance ≠ price direction. Seasonal inventory deviations describe "
           "US stocks, not a buy signal or a global balance. Reference dates and coverage "
           "are shown with the evidence. Product supplied is a consumption proxy. "
           "Observation dates do not establish when a release or revision was available."),
    "zh": ("实物供需≠价格方向。季节性库存偏离描述美国库存，不构成买入信号或全球供需判断。"
           "参照日期与覆盖范围随证据列示。产品供应量是消费代理指标；观察日期不能证明"
           "数据发布或修订在何时可得。"),
}


def _weekly(s: pd.Series | None) -> pd.Series | None:
    """Clean dated weekly values; conflicting duplicate dates fail locally."""
    if s is None:
        return None
    s = pd.Series(s).copy()
    if pd.api.types.is_numeric_dtype(s.index.dtype):
        return None
    s.index = pd.to_datetime(s.index, errors="coerce", utc=True).tz_convert(None).normalize()
    s = s[s.index.notna()].sort_index()
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if s.index.has_duplicates:
        if (s.groupby(level=0).nunique() > 1).any():
            return None
        s = s[~s.index.duplicated(keep="first")]
    return s if not s.empty else None


def last_value(s: pd.Series | None) -> float | None:
    """Latest finite value of a stored series, or None."""
    s = _weekly(s)
    return None if s is None else float(s.iloc[-1])


def seasonal_reference(s: pd.Series | None, years: int = 5) -> dict:
    """Actual reference window for the established trailing ISO-week method."""
    s = _weekly(s)
    window = None if s is None or type(years) is not int or years < 2 else s.iloc[-(years * 53):]
    return {
        "target_years": years,
        "start": None if window is None else window.index[0].date().isoformat(),
        "end": None if window is None else window.index[-1].date().isoformat(),
        "observations": 0 if window is None else len(window),
        "same_week_observations": 0 if window is None else int(
            (window.index.isocalendar().week == window.index[-1].isocalendar().week).sum()),
        "latest_included": True,
        "method": "iso_week_mean_then_population_sd_of_anomalies",
    }


def seasonal_z(s: pd.Series | None, years: int = 5) -> float | None:
    """Preserve the existing seasonal-anomaly method; disclose its actual window.

    anomaly_t = value_t - mean(value | ISO-week(t), trailing window);
    z = anomaly_latest / std(anomalies). Negative means below-season stocks.
    This is not EIA's published five-year range or a calibrated return forecast.
    """
    s = _weekly(s)
    if s is None or len(s) < 104 or type(years) is not int or years < 2:
        return None
    window = s.iloc[-(years * 53):]
    woy = window.index.isocalendar().week.astype(int)
    if int((woy == woy.iloc[-1]).sum()) < 2:
        return None
    clim = window.groupby(woy.values).transform("mean")
    anom = window - clim
    sd = float(anom.std(ddof=0))
    if not np.isfinite(sd) or sd == 0:
        return None
    return float(anom.iloc[-1] / sd)


def delta_4w(s: pd.Series | None) -> float | None:
    """Latest minus the observation exactly 28 calendar days earlier.

    Two endpoint observations suffice for a stock difference. Missing endpoints
    cannot be replaced with the fourth available row or a shorter interval.
    """
    s = _weekly(s)
    if s is None:
        return None
    start = s.index[-1] - pd.Timedelta(weeks=4)
    if start not in s.index:
        return None
    return float(s.iloc[-1] - s.loc[start])


def _demand_window(demand: pd.Series | None, endpoint: pd.Timestamp, weeks: int) -> pd.Series | None:
    dm = _weekly(demand)
    if dm is None or type(weeks) is not int or weeks < 1:
        return None
    expected = pd.date_range(end=endpoint, periods=weeks, freq="7D")
    window = dm.reindex(expected)
    if window.isna().any() or (window <= 0).any():
        return None
    return window


def days_of_supply(stocks: pd.Series | None, demand: pd.Series | None,
                   weeks: int = 4) -> float | None:
    """Stocks / mean daily flow over exact weekly dates ending on the stock date.

    Crude uses refinery net inputs; products use product supplied. All requested
    weeks must be present and positive. Future or stale demand cannot be borrowed.
    """
    st = _weekly(stocks)
    if st is None or float(st.iloc[-1]) < 0:
        return None
    window = _demand_window(demand, st.index[-1], weeks)
    if window is None:
        return None
    daily = float(window.mean())
    return round(float(st.iloc[-1]) / daily, 1) if np.isfinite(daily) and daily > 0 else None


def balance_z(zmap: dict[str, float | None]) -> float | None:
    """Existing display average; not a confidence count or a scored leg."""
    vals = [v for v in zmap.values() if v is not None and np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def balance_word(z: float | None) -> str:
    """Neutral inventory label; no return-direction meaning."""
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


def build_physical_context(series: dict, *, as_of: str, years: int = 5,
                           dos_weeks: int = 4, source_identities: dict | None = None) -> dict:
    """One pure owner for the legacy panel and R3, with observation-window receipts.

    Filter observation periods to the explicit analysis cutoff. The input cache
    has no release/vintage metadata; filtering MUST NOT imply point-in-time proof.
    No clock, collector, persistence, forecast or scoring work occurs here.
    """
    try:
        cutoff = pd.Timestamp(as_of)
        if cutoff.date().isoformat() != as_of:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Physical context requires an explicit ISO analysis date") from None
    clean, sources = {}, {}
    for name in SERIES:
        raw = _weekly(series.get(name))
        clipped = None if raw is None else raw.loc[raw.index <= cutoff]
        invalid_stock = (name.endswith("_stocks") and clipped is not None and (clipped < 0).any())
        clean[name] = clipped if clipped is not None and not clipped.empty and not invalid_stock else None
        rows = [] if raw is None else [(d.date().isoformat(), float(v)) for d, v in raw.items()]
        sources[name] = {
            "path": f"data/eia/{name}.parquet",
            "state": "invalid_negative_stock" if invalid_stock else "available" if clean[name] is not None else "missing",
            "fingerprint": sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
            "input_latest_observation": None if raw is None else raw.index[-1].date().isoformat(),
            "observation_at": None if clean[name] is None else clean[name].index[-1].date().isoformat(),
            "release_at": None, "point_in_time_verified": False,
            "immutable_source": (source_identities or {}).get(name),
        }
    evidence = {}

    def emit(key, value, unit, names, *, start=None, end=None, reference=None, reason="missing_or_incomplete"):
        primary = clean[names[0]]
        end = end or (None if primary is None else primary.index[-1].date().isoformat())
        value = None if value is None or not np.isfinite(value) else float(value)
        evidence[key] = {
            "value": value, "unit": unit, "observation_at": end,
            "window_start": start, "window_end": end, "reference": reference,
            "source_ids": names, "release_at": None, "point_in_time_verified": False,
            "state": "available" if value is not None else reason,
        }

    def rounded(v, scale=1, digits=2):
        return None if v is None else round(v / scale, digits)

    zmap = {}
    for name, stem in (("crude_stocks", "crude"), ("cushing_stocks", "cushing"),
                       ("gasoline_stocks", "gasoline"), ("distillate_stocks", "distillate")):
        s = clean[name]
        zmap[stem] = seasonal_z(s, years)
        emit(f"{stem}_stocks_mb", rounded(last_value(s), 1000, 1), "million_barrels", [name])
        emit(f"{stem}_z", rounded(zmap[stem]), "seasonal_z", [name],
             reference=seasonal_reference(s, years), reason="insufficient_or_flat_seasonal_history")
        end = None if s is None else s.index[-1]
        emit(f"{stem}_chg_4w_mb", rounded(delta_4w(s), 1000, 1), "million_barrels", [name],
             start=None if end is None else (end - pd.Timedelta(weeks=4)).date().isoformat(),
             reason="four_week_endpoint_missing")

    for key, stocks, demand in (
        ("days_supply", "crude_stocks", "refinery_inputs"),
        ("gasoline_days", "gasoline_stocks", "gasoline_supplied"),
        ("distillate_days", "distillate_stocks", "distillate_supplied"),
    ):
        st = clean[stocks]
        end = None if st is None else st.index[-1]
        start = None if end is None or type(dos_weeks) is not int or dos_weeks < 1 else (
            end - pd.Timedelta(weeks=dos_weeks - 1)).date().isoformat()
        emit(key, days_of_supply(st, clean[demand], dos_weeks), "days", [stocks, demand],
             start=start, reason="aligned_demand_weeks_missing")
        dm = None if end is None else _demand_window(clean[demand], end, dos_weeks)
        emit(f"{demand}_avg", None if dm is None else round(float(dm.mean()) / 1000, 3),
             "million_barrels_per_day", [demand], start=start,
             end=None if end is None else end.date().isoformat(),
             reason="aligned_demand_weeks_missing")

    emit("production_mbd", rounded(last_value(clean["crude_production"]), 1000),
         "million_barrels_per_day", ["crude_production"])
    for key, name, scale, unit in (
        ("production_chg_4w", "crude_production", 1000, "million_barrels_per_day"),
        ("spr_chg_4w_mb", "spr_stocks", 1000, "million_barrels"),
    ):
        s = clean[name]
        emit(key, rounded(delta_4w(s), scale), unit, [name],
             start=None if s is None else (s.index[-1] - pd.Timedelta(weeks=4)).date().isoformat(),
             reason="four_week_endpoint_missing")
    emit("refinery_util", rounded(last_value(clean["refinery_util"]), digits=1),
         "percent", ["refinery_util"])

    crude_date = sources["crude_stocks"]["observation_at"]
    # Preserve the legacy aggregate, but never average different observation weeks.
    aligned_z = {k: v for k, v in zmap.items()
                 if sources[f"{k}_stocks"]["observation_at"] == crude_date}
    bz = balance_z(aligned_z)
    out = {k: v["value"] for k, v in evidence.items() if v["value"] is not None}
    if "cushing_stocks_mb" in out:
        out["cushing_mb"] = out["cushing_stocks_mb"]
    if "crude_chg_4w_mb" in out:
        out["draw"] = out["crude_chg_4w_mb"] < 0
    out.update({
        "schema": PHYSICAL_SCHEMA, "method_revision": METHOD_REVISION,
        "asof": crude_date, "analysis_cutoff": as_of, "display_only": True,
        "geography": "US", "release_at": None, "point_in_time_verified": False,
        "hypothesis_confirmation_eligible": False, "observation_filter_only": True,
        "crude_z": evidence["crude_z"]["value"],
        "balance_z": rounded(bz), "balance_word": balance_word(bz),
        "caveat_en": SUPPLY_CAVEAT["en"], "caveat_zh": SUPPLY_CAVEAT["zh"],
        "sources": sources, "evidence": evidence,
        "method": {"seasonal_years_target": years, "dos_window_weeks": dos_weeks,
                   "seasonal_latest_included": True, "same_week_stock_difference_days": 28},
    })
    return out
