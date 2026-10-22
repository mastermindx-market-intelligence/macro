"""Display-only US petroleum-balance context from the existing EIA cache.

Never feed conviction, alerts, scoring or latest.json. Inventory balance is not a
directional signal; see research/OIL_PHYSICAL_TIGHTNESS.md. Seasonal anomalies use
the existing ISO-week method. Explicit windows disclose actual history coverage.
Observation dates do not establish release availability or historical vintage.
"""
from __future__ import annotations

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
