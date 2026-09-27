"""Point-in-time replay helpers for Finviz subtheme repricing context.

This module closes one specific gap in the live Finviz owner surface: today's member
breadth can be measured, but historical breadth must never reuse today's membership or
silently carry a stale member price through a missing session.

Inputs remain owned elsewhere:
- Finviz structure vintages: engine.theme_graph.local_sources.Ladder.
- Finviz subtheme performance: subsector_perf_history.jsonl rows supplied by caller.
- Member closes: supplied by caller on a declared split-adjusted price-return basis.
- Repricing classification: engine.theme_repricing_context.

No store, grader, ranking, signal, gate, sizing, escalation or trading authority is
created here. A replay is descriptive evidence for later evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from typing import Callable, Mapping

import pandas as pd

from engine import theme_repricing_context as trc
from engine.theme_graph import local_sources
from lib import nyse_calendar

SCHEMA = "theme_repricing_pit.v1"

HORIZON_SESSIONS: dict[str, int] = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
}

AUTHORITY = {
    "context_only": True,
    "display_only": True,
    "not_a_signal": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_trade": False,
}


class ReplayRefusal(ValueError):
    """The requested PIT replay cannot be answered without inventing a fact."""


@dataclass(frozen=True)
class ReplayMembership:
    asof: str
    vintage_asof: str
    vintage_source_ref: str
    members_by_subtheme: dict[str, tuple[str, ...]]


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ReplayRefusal(f"unreadable replay date: {value!r}") from exc
    if pd.isna(ts):
        raise ReplayRefusal(f"unreadable replay date: {value!r}")
    return ts.date()


def vintage_at(ladder: local_sources.Ladder, asof: object) -> local_sources.Vintage:
    """Newest observed structure vintage with vintage.asof <= asof."""
    day = _as_date(asof)
    eligible = [
        vintage
        for vintage in ladder.vintages
        if _as_date(vintage.asof) <= day
    ]
    if not eligible:
        first = ladder.vintages[0].asof if ladder.vintages else None
        raise ReplayRefusal(
            f"no Finviz structure vintage known by {day.isoformat()} "
            f"(first_vintage={first!r})"
        )
    return max(eligible, key=lambda vintage: vintage.asof)


def membership_at(ladder: local_sources.Ladder, asof: object) -> ReplayMembership:
    """PIT member roster grouped by source-local subtheme for asof."""
    day = _as_date(asof)
    if not nyse_calendar.is_session(day):
        raise ReplayRefusal(
            f"repricing replay requires an NYSE session date, got {day.isoformat()}"
        )
    vintage = vintage_at(ladder, day)
    grouped: dict[str, list[str]] = {}
    for key, ticker in local_sources.memberships_of(vintage):
        grouped.setdefault(key, []).append(ticker)
    frozen = {
        key: tuple(sorted(set(tickers)))
        for key, tickers in grouped.items()
    }
    return ReplayMembership(
        asof=day.isoformat(),
        vintage_asof=vintage.asof,
        vintage_source_ref=vintage.source_ref,
        members_by_subtheme=frozen,
    )


def prior_session(asof: object, sessions: int) -> date:
    """Exactly sessions NYSE sessions before asof."""
    if sessions < 1:
        raise ReplayRefusal(f"sessions must be >=1, got {sessions}")
    day = _as_date(asof)
    if not nyse_calendar.is_session(day):
        raise ReplayRefusal(
            f"repricing replay requires an NYSE session date, got {day.isoformat()}"
        )
    cursor = day - timedelta(days=1)
    seen = 0
    for _ in range(max(45, sessions * 3)):
        if nyse_calendar.is_session(cursor):
            seen += 1
            if seen == sessions:
                return cursor
        cursor -= timedelta(days=1)
    raise ReplayRefusal(
        f"could not resolve {sessions} prior NYSE sessions before {day.isoformat()}"
    )


def _series_by_date(close: pd.Series | None) -> dict[date, float]:
    """Finite exact-session close map; duplicate dates keep the last row."""
    if close is None or len(close) == 0:
        return {}
    try:
        series = close.dropna().copy()
        index = pd.DatetimeIndex(series.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        series.index = index
        series = series[~series.index.duplicated(keep="last")].sort_index()
    except Exception:
        return {}
    out: dict[date, float] = {}
    for stamp, value in series.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number > 0:
            out[pd.Timestamp(stamp).date()] = number
    return out


def exact_horizon_return(
    close: pd.Series | None,
    asof: object,
    sessions: int,
) -> float | None:
    """Percent return on exact session endpoints; no previous-row fallback."""
    day = _as_date(asof)
    start = prior_session(day, sessions)
    by_date = _series_by_date(close)
    p0, p1 = by_date.get(start), by_date.get(day)
    if p0 is None or p1 is None or p0 <= 0:
        return None
    return (p1 / p0 - 1.0) * 100.0


def member_perf_at(
    membership: ReplayMembership,
    close_loader: Callable[[str], pd.Series | None],
) -> tuple[dict[str, dict[str, float]], dict]:
    """Reconstruct 1W/1M/3M member returns on exact exchange-session endpoints."""
    tickers = sorted({
        ticker
        for members in membership.members_by_subtheme.values()
        for ticker in members
    })
    perf: dict[str, dict[str, float]] = {}
    horizon_coverage = {
        horizon: {"expected": len(tickers), "observed": 0}
        for horizon in HORIZON_SESSIONS
    }
    readable = 0
    for ticker in tickers:
        close = close_loader(ticker)
        if close is not None and len(close):
            readable += 1
        row: dict[str, float] = {}
        for horizon, n_sessions in HORIZON_SESSIONS.items():
            value = exact_horizon_return(close, membership.asof, n_sessions)
            if value is None:
                continue
            row[horizon] = round(value, 6)
            horizon_coverage[horizon]["observed"] += 1
        if row:
            perf[ticker] = row
    for rec in horizon_coverage.values():
        expected = int(rec["expected"])
        rec["coverage"] = (
            round(int(rec["observed"]) / expected, 4) if expected else None
        )
    return perf, {
        "expected_unique_members": len(tickers),
        "readable_price_series": readable,
        "horizons": horizon_coverage,
    }


def build_pit_context(
    *,
    ladder: local_sources.Ladder,
    asof: object,
    subsector_perf: Mapping[str, Mapping[str, float]],
    close_loader: Callable[[str], pd.Series | None],
    price_source: str,
    price_basis: str,
) -> dict:
    """Build current repricing schema against PIT membership + exact member returns."""
    membership = membership_at(ladder, asof)
    vintage = vintage_at(ladder, membership.asof)
    member_perf, coverage = member_perf_at(membership, close_loader)
    context = trc.build_context(
        vintage.themes,
        subsector_perf,
        member_perf,
        asof=membership.asof,
        source="finviz-themes-pit-replay",
    )
    return {
        "schema": SCHEMA,
        "asof": membership.asof,
        "authority": dict(AUTHORITY),
        "membership": {
            "vintage_asof": membership.vintage_asof,
            "source_ref": membership.vintage_source_ref,
            "semantics": "latest_observed_structure_vintage_known_by_decision_date",
            "interval_censoring": (
                "removal known only at first later observed vintage without it"
            ),
        },
        "prices": {
            "source": price_source,
            "basis": price_basis,
            "endpoint_policy": "exact_session_only_no_ffill",
        },
        "coverage": coverage,
        "repricing": context,
    }
