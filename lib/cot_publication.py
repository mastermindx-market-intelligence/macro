"""COT source clocks and causal joins shared by positioning consumers.

A report date is NOT a release date. Strict replay uses observed vintage clocks;
legacy reconstruction is explicitly estimated, never original-vintage proof.
All dates below come from CFTC announcements, not a vendor's price calendar.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

ANNOUNCEMENTS = (
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/"
    "HistoricalSpecialAnnouncements/index.htm"
)
SCHEDULE_SOURCE = (
    "https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm"
)
# Date evidence only: reconstruction waits until the NEXT local midnight. Do not
# pretend these announcements attest the first public byte at exactly 15:30.
PUBLICATION_DATES = {
    "2023-01-31": "2023-02-24", "2023-02-07": "2023-03-03",
    "2023-02-14": "2023-03-08", "2023-02-21": "2023-03-10",
    "2023-02-28": "2023-03-14", "2023-03-07": "2023-03-16",
    "2023-03-14": "2023-03-21",
    # Final, accelerated December 9 schedule supersedes November 18's plan.
    "2025-09-30": "2025-11-19", "2025-10-07": "2025-11-21",
    "2025-10-14": "2025-11-25", "2025-10-21": "2025-12-02",
    "2025-10-28": "2025-12-05", "2025-11-04": "2025-12-09",
    "2025-11-10": "2025-12-10", "2025-11-18": "2025-12-12",
    "2025-11-25": "2025-12-15", "2025-12-02": "2025-12-17",
    "2025-12-09": "2025-12-19", "2025-12-16": "2025-12-23",
    "2025-12-23": "2025-12-29",
    "2025-01-07": "2025-01-13", "2021-06-15": "2021-06-21",
    "2020-12-21": "2020-12-28", "2015-06-30": "2015-07-06",
    "2014-12-23": "2014-12-30",
}
# Known disruption, but no observation-specific verified release ledger yet.
# Exclude rather than assigning an invented catch-up date to every report.
UNRESOLVED_RANGES = (
    ("2013-10-01", "2013-11-05"),
    ("2018-12-24", "2019-03-05"),
)
NY = "America/New_York"


def utc_timestamp(value: object) -> pd.Timestamp:
    """Require an explicit timezone on instants; dates are not instants."""
    if not pd.api.types.is_scalar(value) or isinstance(value, (bool, int, float, np.number)):
        return pd.NaT
    if value is None or pd.isna(value):
        return pd.NaT
    try:
        t = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return pd.NaT
    if t.tzinfo is None:
        return pd.NaT
    return t.tz_convert("UTC")


@lru_cache(maxsize=96)
def _holidays(year: int) -> frozenset:
    dates = USFederalHolidayCalendar().holidays(
        start=f"{year - 1}-12-20", end=f"{year + 1}-01-10"
    )
    return frozenset(d.date() for d in dates)


def scheduled_release(report_date: object) -> pd.Timestamp:
    """Expected Friday at 15:30 ET, holiday-adjusted; NOT release confirmation."""
    try:
        d = pd.Timestamp(report_date)
        if pd.isna(d):
            return pd.NaT
        d = d.tz_localize(None).normalize()
    except (TypeError, ValueError, OverflowError):
        return pd.NaT
    # Monday observations occur around Tuesday holidays; Friday stays Friday.
    friday = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    holidays = _holidays(d.year)
    # CFTC: Wed/Thu/Fri federal holidays postpone by one/two working days.
    count = sum((friday - pd.Timedelta(days=i)).date() in holidays for i in range(3))
    release = friday
    if count:
        for _ in range(count):
            release += pd.Timedelta(days=1)
            while release.weekday() >= 5 or release.date() in holidays:
                release += pd.Timedelta(days=1)
    return (release + pd.Timedelta(hours=15, minutes=30)).tz_localize(NY).tz_convert("UTC")


def reconstruction_bound(report_date: object) -> pd.Timestamp:
    """Conservative local-date bound for latest-revised historical context.

    Unverified normal weeks use a holiday-adjusted schedule, with next-day
    availability. Thus this repairs known leakage, but does NOT certify all
    historical releases or revisions. Strict as-published replay is separate.
    """
    try:
        day = pd.Timestamp(report_date).date().isoformat()
    except (TypeError, ValueError, AttributeError):
        return pd.NaT
    if any(start <= day <= end for start, end in UNRESOLVED_RANGES):
        return pd.NaT
    if day in PUBLICATION_DATES:
        local = pd.Timestamp(PUBLICATION_DATES[day]) + pd.Timedelta(days=1)
        return local.tz_localize(NY).tz_convert("UTC")
    expected = scheduled_release(report_date)
    if pd.isna(expected):
        return pd.NaT
    local = expected.tz_convert(NY).tz_localize(None).normalize() + pd.Timedelta(days=1)
    return local.tz_localize(NY).tz_convert("UTC")


def available_at(row: pd.Series | dict, *, report_date: object,
                 mode: Literal["observed", "reconstructed"] = "observed") -> pd.Timestamp:
    """Clock for THIS version of a row. Never backdate a later correction."""
    if mode not in {"observed", "reconstructed"}:
        raise ValueError("unknown COT availability mode")
    seen = utc_timestamp(row.get("version_observed_at"))
    if pd.isna(seen):
        seen = utc_timestamp(row.get("first_observed_at"))
    revised = utc_timestamp(row.get("revised_at"))
    if mode == "observed":
        # A scheduled/claimed release alone cannot grant vintage access.
        if pd.isna(seen):
            return pd.NaT
        if not pd.isna(revised):
            seen = max(seen, revised)
        try:
            report = pd.Timestamp(report_date)
            if pd.isna(report) or report.date() > seen.tz_convert(NY).date():
                return pd.NaT
        except (TypeError, ValueError):
            return pd.NaT
        return seen
    bound = reconstruction_bound(report_date)
    if pd.isna(bound):
        return pd.NaT
    if not pd.isna(revised):
        return max(bound, revised, seen) if not pd.isna(seen) else max(bound, revised)
    return bound


def released_series(frame: pd.DataFrame | None, column: str = "net_spec_pct_oi", *,
                    mode: Literal["observed", "reconstructed"] = "observed",
                    daily: bool = False) -> pd.Series:
    """Map reports to availability, preserving missing releases as barriers.

    ``daily=True`` produces naive local next-day dates for legacy daily engines;
    an instant obtained intraday is never rounded backwards to that morning.
    Returned attrs explicitly distinguish reconstruction from vintage proof.
    """
    empty = pd.Series(dtype=float, name=column)
    if frame is None or frame.empty or column not in frame:
        return empty
    points = []
    for report_date, row in frame.sort_index().iterrows():
        clock = available_at(row, report_date=report_date, mode=mode)
        if pd.isna(clock):
            continue
        if daily:
            local = clock.tz_convert(NY).tz_localize(None)
            clock = local.normalize() + (pd.Timedelta(days=1) if local != local.normalize() else pd.Timedelta(0))
        value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
        points.append((clock, value, pd.Timestamp(report_date)))
    if not points:
        return empty
    # Multiple reports released together: latest observation wins, independent
    # of input ordering. Do not accidentally bring an older report forward.
    p = pd.DataFrame(points, columns=["clock", "value", "asof"]).sort_values(["clock", "asof"])
    # A late correction to an older report changes history, not today's latest
    # observation. The vintage store retains that correction for replay.
    p = p.loc[p["asof"] >= p["asof"].cummax()]
    out = p.drop_duplicates("clock", keep="last").set_index("clock")["value"]
    out.name = column
    out.attrs.update(cot_availability_mode=mode, original_vintage_certified=False,
                     excluded_unknown_timing=len(frame) - len(points))
    return out


def align_released(series: pd.Series, index: pd.DatetimeIndex, *, max_age_days: int = 12) -> pd.Series:
    """Causal as-of join. Unlike reindex(index).ffill(), keeps weekend releases.

    Age is wall-clock days from publication, NOT a count of target chart bars.
    Explicit null observations form barriers and do not resurrect prior values.
    """
    idx = pd.DatetimeIndex(index)
    if series is None or series.empty:
        return pd.Series(np.nan, index=idx, dtype=float)
    if max_age_days < 0:
        raise ValueError("max_age_days must be nonnegative")
    source = series.copy().sort_index()
    source.index = pd.DatetimeIndex(source.index)
    if (source.index.tz is None) != (idx.tz is None):
        raise ValueError("source and decision timestamps must share timezone awareness")
    source = source[~source.index.duplicated(keep="last")]
    positions = source.index.get_indexer(idx, method="pad")
    result = np.full(len(idx), np.nan)
    valid = positions >= 0
    where = np.flatnonzero(valid)
    if len(where):
        ages = idx[where] - source.index[positions[where]]
        fresh = ages <= pd.Timedelta(days=max_age_days)
        selected = where[fresh]
        result[selected] = pd.to_numeric(source.iloc[positions[selected]], errors="coerce").to_numpy(dtype=float)
    return pd.Series(result, index=idx, name=series.name)


def legacy_series(frame: pd.DataFrame | None, column: str = "net_spec_pct_oi") -> pd.Series:
    """Explicit non-certified reconstruction for existing daily context engines."""
    return released_series(frame, column, mode="reconstructed", daily=True)
