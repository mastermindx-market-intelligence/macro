"""Small acceptance rules for real provider observations, using existing calendars.

Retrieval/heartbeat timestamps never become market observation dates. Without a
complete verified annual notice, guessed holiday rules cannot delete a provider
weekday observation, including historical bars. No I/O or persistence.
"""
from __future__ import annotations

from datetime import datetime
import pandas as pd

from lib import market_session


def observation_date_allowed(value, market: str, *, now: datetime | None = None,
                             completed_only: bool = False) -> bool:
    try:
        day = pd.Timestamp(str(value) if isinstance(value, int) else value)
        if pd.isna(day):
            return False
        day = day.date()
        today = market_session.market_local_date(market, now)
        if day > today or day.weekday() >= 5:
            return False
        verified = market_session.calendar_verified(market, day.year)
        if verified and not market_session.is_session_date(market, day):
            return False
        if completed_only and market_session.calendar_verified(market, today.year):
            return day <= market_session.expected_session(market, now)
        return True
    except (ValueError, TypeError, OverflowError):
        return False


def filter_session_observations(frame: pd.DataFrame, market: str, *, date_col: str | None = None,
                                now: datetime | None = None,
                                completed_only: bool = False) -> pd.DataFrame:
    """Keep genuine observation dates and original labels; no synthetic fill."""
    dates = frame[date_col] if date_col is not None else frame.index
    keep = [observation_date_allowed(value, market, now=now, completed_only=completed_only)
            for value in dates]
    return frame.loc[keep].copy()


def snapshot_rejection_reason(new: pd.DataFrame, old: pd.DataFrame | None, market: str, *,
                              date_col: str = "trade_date", identity_col: str = "ticker",
                              value_cols: tuple[str, ...] = (),
                              now: datetime | None = None) -> str | None:
    """Latest-table acceptance based on vendor observation date, never retrieval asof."""
    if new is None or new.empty:
        return "empty provider snapshot"
    if date_col not in new or identity_col not in new:
        return "missing provider observation date or identity"
    identities = new[identity_col].fillna("").astype(str).str.strip()
    if not identities.ne("").all():
        return "invalid provider identities"
    if len(filter_session_observations(new, market, date_col=date_col, now=now)) != len(new):
        return "non-session, future or malformed provider observation date"
    dates = pd.to_datetime(new[date_col].astype(str), errors="coerce", format="mixed")
    if dates.nunique() != 1:
        return "mixed provider observation dates in latest snapshot"
    if value_cols:
        values = [pd.to_numeric(new[col], errors="coerce").replace(
            [float("inf"), float("-inf")], float("nan")) for col in value_cols if col in new]
        if not values or not pd.concat(values, axis=1).notna().any(axis=1).all():
            return "invalid provider snapshot values"
    if old is not None and not old.empty and date_col in old:
        previous = pd.to_datetime(old[date_col].astype(str), errors="coerce", format="mixed")
        if dates.max() < previous.max():
            return "older provider snapshot would replace newer last-good data"
    return None



def current_adjusted_columns(fresh: pd.DataFrame, old: pd.DataFrame | None) -> pd.DataFrame:
    """Discard a stale adjusted column as a whole; retain no partial changed basis."""
    if fresh is None:
        return pd.DataFrame()
    safe = fresh.loc[:, ~fresh.columns.duplicated(keep="last")].copy()
    for col in list(safe.columns):
        values = pd.to_numeric(safe[col], errors="coerce").replace(
            [float("inf"), float("-inf")], float("nan")).where(lambda series: series > 0)
        safe[col] = values
        if values.dropna().empty:
            safe = safe.drop(columns=[col])
            continue
        if old is not None and col in old:
            previous = old[col].dropna()
            if not previous.empty and values.dropna().index.max() < previous.index.max():
                safe = safe.drop(columns=[col])
    return safe



def provider_date_matches(frame: pd.DataFrame, selected_date, date_col: str = "trade_date") -> bool:
    """A query date may label rows only when actual provider dates agree with it."""
    if date_col not in frame:
        return True
    try:
        expected = pd.Timestamp(str(selected_date)).normalize()
        actual = pd.to_datetime(frame[date_col].astype(str), errors="coerce", format="mixed")
        return bool(actual.notna().all() and actual.dt.normalize().eq(expected).all())
    except (ValueError, TypeError, OverflowError):
        return False
