"""Read existing Macro stores for Regime One research; collect and persist nothing.

This is a downstream adapter, not a source registry or an economic classifier.
The existing debounced ``quad`` is the only target. Latest-revised source files
remain exploratory, even when conservative publication-lag assumptions are used.
Every loaded byte sequence is bound to its own SHA-256; missing, ambiguous and
invalid files are explicit. Only closed calendar months enter the monthly model.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping
import hashlib
import re

import numpy as np
import pandas as pd

from engine.regime_transition_research import MonthlyPanel, PanelError


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    unit: str
    max_age_days: int
    lag_months: int = 0
    lag_days: int = 0
    positive: bool = False


# An analytical selection from existing FRED stores, NOT authority to collect a
# missing series. A missing tenor stays missing. DGS20 is never substituted into
# the separate canonical yield_momentum us20y construction.
NOMINAL_TENORS = {"3m": "DGS3MO", "6m": "DGS6MO", "1y": "DGS1", "2y": "DGS2",
                  "3y": "DGS3", "5y": "DGS5", "7y": "DGS7", "10y": "DGS10",
                  "20y": "DGS20", "30y": "DGS30"}
REAL_TENORS = {"5y": "DFII5", "7y": "DFII7", "10y": "DFII10",
               "20y": "DFII20", "30y": "DFII30"}
CURVE_SPECS = tuple(SeriesSpec(s, "percent", 7) for s in
                    (*NOMINAL_TENORS.values(), *REAL_TENORS.values(), "T5YIE", "T10YIE", "T5YIFR"))
CONTEXT_SPECS = (
    SeriesSpec("DTWEXBGS", "index", 7, positive=True),
    SeriesSpec("BAMLH0A0HYM2", "percentage_points", 7),
    SeriesSpec("ICSA", "persons", 21, lag_days=7, positive=True),
    SeriesSpec("PCEPILFE", "index", 75, lag_months=1, positive=True),
    SeriesSpec("DCOILWTICO", "usd_per_barrel", 7, positive=True),
    SeriesSpec("THREEFYTP10", "percentage_points", 21),
)
FEATURES = ("growth_score", "inflation_score", "real10_pct", "breakeven10_pct",
            "curve_2s10s_pp", "broad_usd_3m_pct", "hy_spread_pp", "claims_yoy_pct",
            "core_pce_3m_annualized_pct", "oil_3m_pct")
METHOD = "owner_month_end_with_disclosed_lags_v1"


def cutoff_utc(value: str | datetime) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if not isinstance(dt, datetime) or dt.tzinfo is None:
            raise ValueError("Timezone required")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as exc:
        raise PanelError("An explicit representable timezone-aware cutoff is required") from exc


def last_closed_month(cutoff: str | datetime) -> pd.Period:
    return pd.Period(cutoff_utc(cutoff).date(), freq="M") - 1


def _plain(v: Any) -> float | None:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        return None
    return float(v) if np.isfinite(v) else None


def _index(frame: pd.DataFrame) -> pd.DatetimeIndex:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise PanelError("Owner parquet must carry a DatetimeIndex; no guessed date column")
    idx = frame.index
    if idx.hasnans or idx.has_duplicates or not idx.is_monotonic_increasing:
        raise PanelError("Source dates must be ordered, unique and present")
    if idx.tz is not None:
        # Observation dates retain their source calendar, not a guessed UTC
        # economic-release instant. Availability remains unverified.
        idx = idx.tz_localize(None)
    idx = idx.normalize()
    if idx.has_duplicates:
        raise PanelError("Multiple intraday observations cannot be silently collapsed")
    return idx


def read_frame(data_root: Path, relative: str) -> tuple[pd.DataFrame | None, dict]:
    root = Path(data_root).resolve()
    path = root / relative
    receipt = {"path": "data/" + relative, "status": "missing", "sha256": None,
               "observation_first": None, "observation_last": None,
               "availability_basis": "latest_revised_store_not_vintage_attested"}
    try:
        if not path.resolve().is_relative_to(root):
            receipt["status"] = "outside_source_root"
            return None, receipt
        if not path.exists():
            return None, receipt
        raw = path.read_bytes()
        receipt["sha256"] = hashlib.sha256(raw).hexdigest()
        frame = pd.read_parquet(BytesIO(raw))
        idx = _index(frame)
        frame = frame.copy()
        frame.index = idx
        receipt.update(status="present", rows=len(frame), columns=[str(c) for c in frame.columns],
                       observation_first=None if frame.empty else str(idx[0].date()),
                       observation_last=None if frame.empty else str(idx[-1].date()))
        return frame, receipt
    except ImportError as exc:
        receipt.update(status="runtime_dependency_unavailable", error_type=type(exc).__name__)
        return None, receipt
    except (OSError, ValueError, TypeError, PanelError) as exc:
        # A file read failure is not a macro signal, and exception text may carry
        # local paths. Keep a closed diagnostic type rather than leaking it.
        receipt.update(status="invalid", error_type=type(exc).__name__)
        return None, receipt


def _select_value(frame: pd.DataFrame, spec: SeriesSpec) -> pd.Series:
    if len(frame.columns) != 1:
        raise PanelError("FRED input has an ambiguous value column")
    values = frame.iloc[:, 0]
    if any(isinstance(v, (bool, np.bool_)) for v in values.array):
        raise PanelError("Boolean source observation")
    if not pd.api.types.is_numeric_dtype(values):
        raise PanelError("Non-numeric source observations")
    arr = values.to_numpy(dtype=float)
    if np.isinf(arr).any():
        raise PanelError("Infinite source observation")
    if spec.positive:
        arr = np.where(arr > 0, arr, np.nan)
    return pd.Series(arr, index=frame.index, name=spec.series_id)


def monthly_series(series: pd.Series, spec: SeriesSpec, periods: pd.PeriodIndex,
                   cutoff: str | datetime) -> tuple[np.ndarray, list[str | None]]:
    """Latest eligible observation at each closed month; no unbounded fill.

    Monthly macro data use a disclosed one-month publication-lag assumption;
    weekly claims use seven days. These are conservative research assumptions,
    not actual release receipts and not PIT certification. The monthly reference
    period does not become the date the observation was publicly knowable.
    """
    c = pd.Timestamp(cutoff_utc(cutoff).date())
    obs = series.loc[series.index <= c].dropna()
    effective = ((obs.index.to_period("M") + spec.lag_months).to_timestamp(how="end").normalize()
                 if spec.lag_months else obs.index + pd.Timedelta(days=spec.lag_days))
    vals = np.full(len(periods), np.nan)
    dates: list[str | None] = [None] * len(periods)
    if not len(obs):
        return vals, dates
    if not effective.is_monotonic_increasing:
        raise PanelError("Availability alignment is not ordered")
    for i, period in enumerate(periods):
        boundary = period.end_time.normalize()
        if period > last_closed_month(cutoff):
            raise PanelError("An incomplete month cannot enter the model")
        k = effective.searchsorted(boundary, side="right") - 1
        if k < 0:
            continue
        age = (boundary - obs.index[k]).days
        if age < 0 or age > spec.max_age_days:
            continue
        vals[i] = float(obs.iloc[k])
        dates[i] = str(obs.index[k].date())
    return vals, dates


def _pct(values: np.ndarray, lag: int, *, annualize: bool = False) -> np.ndarray:
    out = np.full(len(values), np.nan)
    if len(values) <= lag:
        return out
    a, b = values[lag:], values[:-lag]
    valid = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ratio = a[valid] / b[valid]
        result = ((ratio ** (12 / lag)) - 1) * 100 if annualize else (ratio - 1) * 100
    indices = np.flatnonzero(valid) + lag
    out[indices] = np.where(np.isfinite(result), result, np.nan)
    return out


def load_research_panel(data_root: Path, cutoff: str | datetime, *,
                        history_snapshot: tuple[pd.DataFrame, dict] | None = None) -> tuple[MonthlyPanel | None, dict]:
    c = cutoff_utc(cutoff)
    if history_snapshot is None:
        hist, history_receipt = read_frame(data_root, "regime/regime_history.parquet")
    else:
        hist, history_receipt = history_snapshot
        history_receipt = dict(history_receipt)
        try:
            hist = hist.copy(deep=True)
            hist.index = _index(hist)
            if not isinstance(history_receipt.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", history_receipt["sha256"]) is None:
                raise PanelError("Prepared owner history needs its exact byte digest")
        except (AttributeError, TypeError, ValueError, PanelError):
            hist = None
            history_receipt["status"] = "invalid_prepared_history"
    report: dict = {"schema": "regime_one.research_input.v1", "method": METHOD,
                    "analysis_cutoff": c.isoformat(), "source_basis": "LATEST_REVISED_EXPLORATORY",
                    "pit_eligible": False, "receipts": [history_receipt], "feature_definitions": {},
                    "limits": ["Debounced house quadrant is an operational target, not an external economic fact.",
                               "Historical source and label revisions are not point-in-time certified.",
                               "Publication-lag assumptions do not replace actual availability receipts."],
                    "status": "unavailable"}
    if hist is None or not {"quad", "growth_score", "inflation_score"}.issubset(hist.columns):
        report["reason"] = "canonical_history_or_columns_missing"
        return None, report
    hist = hist.loc[hist.index <= pd.Timestamp(c.date())]
    if hist.empty:
        report["reason"] = "no_history_at_cutoff"
        return None, report
    end = last_closed_month(c)
    start = hist.index[0].to_period("M")
    if end < start:
        report["reason"] = "no_closed_month"
        return None, report
    periods = pd.period_range(start, end, freq="M")
    # Reindex the complete month grid. resample(...).dropna() would bridge a
    # missing month and fabricate a one-month state transition.
    h = hist.groupby(hist.index.to_period("M"), sort=True).tail(1).copy()
    h.index = h.index.to_period("M")
    h = h.reindex(periods)
    label_values = []
    for v in h["quad"]:
        if pd.isna(v):
            label_values.append(None)
        elif not isinstance(v, str) or v not in ("Q1", "Q2", "Q3", "Q4"):
            report["reason"] = "invalid_canonical_label"
            return None, report
        else:
            label_values.append(v)
    columns = {name: np.full(len(periods), np.nan) for name in FEATURES}
    for name in ("growth_score", "inflation_score"):
        raw_values = h[name].to_numpy(dtype=object)
        if any(isinstance(v, (bool, np.bool_)) for v in raw_values):
            report["reason"] = "invalid_canonical_axis"
            return None, report
        columns[name] = np.array([np.nan if _plain(v) is None else float(v) for v in raw_values])
        report["feature_definitions"][name] = {"source": history_receipt["path"], "basis": "existing_owner_axis", "unit": "owner_score"}
    source_values, source_dates = {}, {}
    for spec in (*CURVE_SPECS, *CONTEXT_SPECS):
        frame, rec = read_frame(data_root, f"fred/{spec.series_id}.parquet")
        rec.update(series_id=spec.series_id, unit=spec.unit, assumed_lag_months=spec.lag_months,
                   assumed_lag_days=spec.lag_days, maximum_observation_age_days=spec.max_age_days)
        report["receipts"].append(rec)
        if frame is None:
            continue
        try:
            s = _select_value(frame, spec)
            values, dates = monthly_series(s, spec, periods, c)
            rec["future_observations_excluded"] = int((s.index > pd.Timestamp(c.date())).sum())
            source_values[spec.series_id], source_dates[spec.series_id] = values, dates
        except PanelError as exc:
            rec.update(status="invalid", error_type=type(exc).__name__)
    def value(key: str) -> np.ndarray:
        return source_values.get(key, np.full(len(periods), np.nan))
    columns.update(real10_pct=value("DFII10"), breakeven10_pct=value("T10YIE"),
                   broad_usd_3m_pct=_pct(value("DTWEXBGS"), 3),
                   hy_spread_pp=value("BAMLH0A0HYM2"),
                   claims_yoy_pct=_pct(value("ICSA"), 12),
                   core_pce_3m_annualized_pct=_pct(value("PCEPILFE"), 3, annualize=True),
                   oil_3m_pct=_pct(value("DCOILWTICO"), 3))
    n10, n2 = value("DGS10"), value("DGS2")
    d10 = source_dates.get("DGS10", [None] * len(periods))
    d2 = source_dates.get("DGS2", [None] * len(periods))
    aligned = np.array([a is not None and a == b for a, b in zip(d10, d2)])
    columns["curve_2s10s_pp"] = np.where(aligned, n10 - n2, np.nan)
    definitions = {
        "real10_pct": ("DFII10", "level", "percent"),
        "breakeven10_pct": ("T10YIE", "inflation_compensation_not_pure_expectations", "percent"),
        "curve_2s10s_pp": ("DGS10,DGS2", "same_observation_date_difference", "percentage_points"),
        "broad_usd_3m_pct": ("DTWEXBGS", "3_closed_month_percent_change_not_DXY", "percent"),
        "hy_spread_pp": ("BAMLH0A0HYM2", "option_adjusted_spread_level", "percentage_points"),
        "claims_yoy_pct": ("ICSA", "12_closed_month_percent_change", "percent"),
        "core_pce_3m_annualized_pct": ("PCEPILFE", "3_closed_month_compound_annualization", "percent"),
        "oil_3m_pct": ("DCOILWTICO", "3_closed_month_price_change_not_shock_cause", "percent"),
    }
    report["feature_definitions"].update({k: {"source": v[0], "transform": v[1], "unit": v[2]} for k, v in definitions.items()})
    x = np.column_stack([columns[k] for k in FEATURES])
    receipts = tuple(f"{r['path']}@sha256:{r['sha256']}" for r in report["receipts"] if r["sha256"])
    panel = MonthlyPanel(tuple(str(p) for p in periods), x, tuple(label_values), FEATURES,
                         "operational_house_quadrant_at_closed_month_end", "LATEST_REVISED_EXPLORATORY", receipts)
    report.update(status="available", rows=len(periods), first_period=str(periods[0]), last_period=str(periods[-1]),
                  panel_sha256=panel.fingerprint, finite_by_feature={k: int(np.isfinite(x[:, j]).sum()) for j, k in enumerate(FEATURES)},
                  current_coverage=float(np.isfinite(x[-1]).mean()),
                  label_count=int(sum(v is not None for v in label_values)))
    return panel, report


def curve_snapshot(data_root: Path, cutoff: str | datetime) -> dict:
    """Observed tenor coverage and precisely labelled row-window technicals.

    No interpolation, zero-curve bootstrap, or extra shock classification. Changes
    are explicitly in observed intervals; they are NOT silently named trading days.
    Dates/endpoints/span are carried so irregular/missing observations remain visible.
    """
    c = pd.Timestamp(cutoff_utc(cutoff).date())
    output: dict = {"schema": "rates_command.curve_research.v1", "cutoff": str(c.date()),
                    "curves": {"nominal": {}, "real": {}, "inflation_compensation": {}},
                    "derived": {}, "can_trade": False,
                    "convention": "Existing constant-maturity source yields; no zero-coupon forward inference."}
    groups = {"nominal": NOMINAL_TENORS, "real": REAL_TENORS,
              "inflation_compensation": {"5y": "T5YIE", "10y": "T10YIE", "5y5y": "T5YIFR"}}
    for group, tenors in groups.items():
        for tenor, series_id in tenors.items():
            frame, rec = read_frame(data_root, f"fred/{series_id}.parquet")
            node: dict = {"source": rec, "value": None, "observation_date": None, "freshness": "unavailable", "changes_bp": {}}
            output["curves"][group][tenor] = node
            if frame is None:
                continue
            try:
                s = _select_value(frame, SeriesSpec(series_id, "percent", 7)).loc[:c].dropna()
            except PanelError:
                node["freshness"] = "invalid"
                continue
            if s.empty:
                continue
            age = int((c - s.index[-1]).days)
            node.update(value=float(s.iloc[-1]), observation_date=str(s.index[-1].date()),
                        age_calendar_days=age, freshness="current_observation" if age <= 7 else "stale_observation",
                        percentile_1260_observations=None, percentile_sample_count=min(1260, len(s)))
            if len(s) >= 252:
                window = s.iloc[-1260:]
                node["percentile_1260_observations"] = float((window <= s.iloc[-1]).mean())
            for n in (5, 22, 63):
                if len(s) <= n:
                    node["changes_bp"][str(n)] = None
                    continue
                delta = float((s.iloc[-1] - s.iloc[-n - 1]) * 100)
                span = int((s.index[-1] - s.index[-n - 1]).days)
                node["changes_bp"][str(n)] = {"value": delta, "basis": "observed_intervals", "intervals": n,
                    "from": str(s.index[-n - 1].date()), "through": str(s.index[-1].date()), "calendar_days": span,
                    "large_calendar_gap": span > 2 * n + 5}
            if len(s) >= 45:
                latest = float((s.iloc[-1] - s.iloc[-23]) * 100)
                prior = float((s.iloc[-23] - s.iloc[-45]) * 100)
                node["equal_window_acceleration_bp"] = latest - prior
                node["acceleration_basis"] = "difference_between_two_adjacent_22_observed_interval_changes"
                node["direction"] = "rising" if latest > 0 else "falling" if latest < 0 else "flat"
                node["speed_change"] = "accelerating" if abs(latest) > abs(prior) else "decelerating" if abs(latest) < abs(prior) else "unchanged"
    for tenor in ("5y", "10y"):
        n, r = output["curves"]["nominal"].get(tenor, {}), output["curves"]["real"].get(tenor, {})
        good = n.get("value") is not None and r.get("value") is not None and n.get("observation_date") == r.get("observation_date")
        output["derived"]["nominal_minus_real_" + tenor] = {
            "value_pp": n["value"] - r["value"] if good else None,
            "observation_date": n.get("observation_date") if good else None,
            "reason": "same_date_constant_maturity_spread_not_pure_expectations" if good else "matched_observations_unavailable"}
    return output


# A fixed research comparison set, not a new security/universe registry. Stores
# remain with the existing Yahoo owner. Missing ETF history is not backfilled.
RESEARCH_ASSETS = ('SPY', 'IEF', 'TLT', 'GLD', 'SLV', 'IWM', 'XLP', 'XLV', 'SMH', 'UUP', 'USO', 'BIL')


def load_asset_panel(data_root: Path, periods: tuple[str, ...], cutoff: str | datetime):
    """Read the owner's documented split+dividend-adjusted `close` basis.

    Source contract: collectors/yahoo.py dual-basis store. `close_price` is NOT
    a substitute. This selected present-day ETF set is not a survivorship-free
    all-asset study; inception gaps and a missing cash benchmark remain visible.
    """
    from engine.cycle_pattern.macro_regime import AssetPanel
    grid = pd.PeriodIndex(periods, freq='M')
    rows, receipts = [], []
    for ticker in RESEARCH_ASSETS:
        frame, receipt = read_frame(data_root, f'yahoo/{ticker}.parquet')
        receipt.update(asset_id=ticker, value_column='close',
                       return_basis='ADJUSTED_CLOSE_TOTAL_RETURN_PROXY', currency='USD',
                       contract_owner='collectors/yahoo.py', universe_basis='fixed_present_day_research_selection')
        receipts.append(receipt)
        values = np.full(len(grid), np.nan)
        if frame is not None:
            try:
                if 'close' not in frame:
                    raise PanelError('Owner adjusted-close column missing; no price-basis fallback')
                spec = SeriesSpec(ticker, 'adjusted_close', 7, positive=True)
                series = _select_value(frame[['close']], spec)
                values, dates = monthly_series(series, spec, grid, cutoff)
                receipt.update(monthly_observations=int(np.isfinite(values).sum()),
                               selected_observation_dates=dates)
            except (PanelError, ValueError, TypeError) as exc:
                receipt.update(status='invalid', error_type=type(exc).__name__)
        rows.append(values)
    result = AssetPanel(periods, np.column_stack(rows), RESEARCH_ASSETS,
                        tuple('ADJUSTED_CLOSE_TOTAL_RETURN_PROXY' for _ in RESEARCH_ASSETS),
                        tuple('USD' for _ in RESEARCH_ASSETS),
                        tuple(f"{r['path']}@{r['sha256'] or r['status']}" for r in receipts))
    return result, {'receipts': receipts, 'selection_uses_outcomes': False,
                    'survivorship_free_universe': False,
                    'limitations': ['Fixed present-day ETF comparison set; no delisting-complete universe claim.',
                                    'Inception/missing dates stay absent; total-return basis is an owner adjusted-close proxy.',
                                    'BIL is a Treasury-bill ETF comparison, not a constructed risk-free cash index.']}
