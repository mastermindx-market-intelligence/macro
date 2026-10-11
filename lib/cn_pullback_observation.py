"""China settled-close pullback adapter; consumes the single existing raw-close observer.

No new episode ledger, forecast, source feed, or capital policy. The episode
owner is lib.pullback_observation.observe(); this module never imports it. The
builder admits it by passing it to snapshot() as ``observer``; without one,
every snapshot is unavailable and no source is read.

Prices come only from the licensed benchmark index store written by
collectors.tushare_index_daily. The free Yahoo China store is internal-only
under the source-rights register and is never read.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable

from lib import cn_calendar
from lib import pullback_depth as core
from lib.pullback_depth import (  # noqa: F401 — the adapter's public contract
    MIN_CHART_POINTS, OBSERVATION_SCHEMA, PATH_TOLERANCE_PP, LicensedCloses,
    SourceRefused,
)

BENCHMARK = "000001.SS"
# Internal provenance label. Product surfaces never name the vendor.
SOURCE = "licensed_cn_index_daily/000001.SS.close"
# A price index level: no dividends to adjust and no splits to restate.
PRICE_BASIS = "index_level_close"
# The rule calendar never closes the market longer than this; a successor
# beyond it means the calendar cannot place the next session.
_MAX_SUCCESSOR_DAYS = cn_calendar.MAX_LEGIT_CLOSURE_DAYS + 7


def _load_store():
    import pandas as pd
    from collectors.tushare_index_daily import OUT
    return pd.read_parquet(OUT) if OUT.exists() else None


def licensed_index_closes(expected: date, *, load: Callable | None = None) -> LicensedCloses:
    """Shanghai Composite settled closes from the licensed store, as held.

    Sessions the store has not landed are not patched from any other source;
    the observer then reports the series as delayed. ``expected`` is accepted
    for the reader contract shared with the US adapter.
    """
    frame = (load or _load_store)()
    if (frame is None or frame.empty
            or not {"ticker", "trade_date", "close"} <= set(frame.columns)):
        raise SourceRefused("source_unavailable")
    if set(frame["ticker"]) != {BENCHMARK}:
        raise SourceRefused("source_unavailable")
    rows = core.price_rows(frame.set_index("trade_date"))
    if core.level_break(rows):
        raise SourceRefused("price_basis_discontinuity")
    return LicensedCloses(rows=rows)


def _next_session(day: date) -> date | None:
    for step in range(1, _MAX_SUCCESSOR_DAYS + 1):
        candidate = day + timedelta(days=step)
        if cn_calendar.is_session(candidate):
            return candidate
    return None


def snapshot(*, now: datetime | None = None, read: Callable | None = None,
             observer: Callable | None = None) -> dict:
    """Assess the Shanghai Composite close against the owning SSE rule calendar.

    The observer's price phases and retained episode reference are authoritative.
    No prediction is computed. ``read(expected_session)`` returns LicensedCloses
    (see licensed_index_closes). Negative or stale results are display-unavailable.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("CN pullback snapshot requires an aware datetime")
    expected = cn_calendar.expected_last_session(now)
    successor = _next_session(expected)
    if successor is None:
        raise ValueError("SSE successor settlement session unavailable")
    expiry = datetime.combine(
        successor, cn_calendar._CLOSE_PLUS_SETTLE, tzinfo=cn_calendar.CST,
    ).astimezone(timezone.utc)
    result, tip = core.observe_closes(
        expected, read=read, observer=observer, is_session=cn_calendar.is_session)
    return {
        **result,
        "session_tip": tip,
        "expected_session": expected.isoformat(),
        "market": "cn",
        "benchmark": BENCHMARK,
        "benchmark_en": "Shanghai Composite",
        "benchmark_zh": "上证综指",
        "price_basis": PRICE_BASIS,
        "source": SOURCE,
        "clock": "settled_close",
        "produced_at": now.astimezone(timezone.utc).isoformat(),
        "valid_until": expiry.isoformat(),
    }


def present(observation: dict, radar: dict | None = None) -> dict:
    """Minimal shared-modal read model; risk odds are intentionally not ingested.

    Reuses the shared illustration renderer; no new visual charting engine.
    This does not confirm a trade, an episode, or a remaining-depth forecast.
    """
    return core.present(
        observation, market="cn",
        aria_en="Observed Shanghai Composite closing drawdown from the retained episode high",
        aria_zh="上证综指实际收盘价相对本轮参考高点的回撤",
    )
