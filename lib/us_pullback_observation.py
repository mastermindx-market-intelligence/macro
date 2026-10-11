"""US settled-price pullback adapter; consumes the single existing raw-close observer.

No new episode ledger, forecast, source feed, or capital policy. The episode
owner is lib.pullback_observation.observe(); this module never imports it. The
builder admits it by passing it to snapshot() as ``observer``; without one,
every snapshot is unavailable and no source is read.

Prices come only from the licensed whole-market daily store plus the same
vendor's same-session regular-hours close (both raw prints, one basis). The
Yahoo store is internal-only under the source-rights register and is never read.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable

from lib import nyse_calendar
from lib import pullback_depth as core
from lib.pullback_depth import (  # noqa: F401 — the adapter's public contract
    MIN_CHART_POINTS, OBSERVATION_SCHEMA, PATH_TOLERANCE_PP, LicensedCloses,
    SourceRefused,
)

BENCHMARK = "SPY"
# Internal provenance label. Product surfaces never name the vendor.
SOURCE = "licensed_us_daily_bars/SPY.regular_session_close"
# Raw regular-session closes are this basis only while no split sits inside the
# observed window; licensed_spy_closes() refuses when one might.
PRICE_BASIS = "split_adjusted_dividend_unadjusted_close"
# The daily store lands T+1; a longer gap is a stalled store, not a tip to patch.
MAX_SESSION_TIP = 3
SPLIT_LIKE_RATIO = core.LEVEL_BREAK_RATIO


def licensed_spy_closes(expected: date, *, load: Callable | None = None,
                        session_closes: Callable | None = None,
                        corp_actions: Callable | None = None) -> LicensedCloses:
    """SPY raw regular-session closes through ``expected`` from licensed sources.

    History is the licensed daily store. Sessions it has not landed yet (at most
    MAX_SESSION_TIP) come from the same vendor's finalized per-session close,
    appended in order and never skipped. A tip that cannot be appended, including
    a not-yet-finalized snapshot close, is held, and the observer reports the
    series as delayed. Never falls back to another vendor.
    """
    if load is None:
        from collectors.massive_stock_day import load_ticker as load
    if session_closes is None or corp_actions is None:
        from engine.close_pass import massive_close
        session_closes = session_closes or massive_close.fetch_session_closes
        corp_actions = corp_actions or massive_close.corp_action_tickers
    frame = load(BENCHMARK)
    if frame is None or frame.empty or "close" not in frame.columns:
        raise SourceRefused("source_unavailable")
    rows = core.price_rows(frame)
    stored = [day for day in (core.session_day(label) for label, _ in rows)
              if day is not None and day <= expected]
    if not stored:
        raise SourceRefused("source_unavailable")
    tip = nyse_calendar.sessions_between(max(stored) + timedelta(days=1), expected)
    appended: list[dict] = []
    hold = None
    if len(tip) > MAX_SESSION_TIP:
        hold = "store_behind"
        tip = []
    for day in tip:
        session = day.isoformat()
        # Raw-on-raw is dividend-safe; a split is not. The shared guard cannot
        # say which action it saw, so any action on SPY holds the tip.
        actions = corp_actions(session)
        if not getattr(actions, "complete", False):
            hold = "corporate_action_guard_down"
            break
        if BENCHMARK in getattr(actions, "tickers", ()):
            hold = "corporate_action_on_session"
            break
        got = session_closes(session, {BENCHMARK})
        price = core.positive((getattr(got, "closes", None) or {}).get(BENCHMARK))
        if getattr(got, "session", None) != session or price is None:
            hold = "session_close_unavailable"
            break
        if getattr(got, "finalized", False) is not True:
            # A snapshot close can still be revised; the popup says "Settled close".
            hold = "session_close_provisional"
            break
        rows.append((session, price))
        appended.append({"session": session, "settlement": "final"})
    if core.level_break(rows):
        raise SourceRefused("price_basis_discontinuity")
    return LicensedCloses(rows=rows, appended=tuple(appended), hold=hold)


def snapshot(*, now: datetime | None = None, read: Callable | None = None,
             observer: Callable | None = None) -> dict:
    """Assess SPY's *price* close against the owning NYSE session calendar.

    The observer's price phases and retained episode reference are authoritative.
    No prediction is computed. ``read(expected_session)`` returns LicensedCloses
    (see licensed_spy_closes). Negative or stale results are display-unavailable.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("US pullback snapshot requires an aware datetime")
    expected = nyse_calendar.expected_last_session(now)
    successor = nyse_calendar.session_n_forward(expected, 1)
    if successor is None:
        raise ValueError("NYSE successor settlement session unavailable")
    expiry = datetime.combine(
        successor, nyse_calendar._CLOSE_PLUS_SETTLE,
        tzinfo=nyse_calendar.ET,
    ).astimezone(timezone.utc)
    result, tip = core.observe_closes(
        expected, read=read, observer=observer, is_session=nyse_calendar.is_session)
    return {
        **result,
        "session_tip": tip,
        "expected_session": expected.isoformat(),
        "market": "us",
        "benchmark": BENCHMARK,
        "benchmark_en": "S&P 500 ETF (SPY)",
        "benchmark_zh": "标普500 ETF (SPY)",
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
        observation, market="us",
        aria_en="Observed SPY price closing drawdown from the retained episode high",
        aria_zh="SPY实际收盘价相对本轮参考高点的回撤",
    )
