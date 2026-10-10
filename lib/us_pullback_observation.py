"""US settled-price pullback adapter; consumes the single existing raw-close observer.

No new episode ledger, forecast, source feed, or capital policy. The existing
held PR #8188 owns lib.pullback_observation.observe(); this code imports that
owner only at evaluation time. Until integrated, its absence is unavailable.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Callable

from lib import nyse_calendar

BENCHMARK = "SPY"
SOURCE = "yahoo/SPY.close_price"
PRICE_BASIS = "split_adjusted_dividend_unadjusted_close"
OBSERVATION_SCHEMA = "pullback_observation.v1"


def _unavailable(expected: date, quality: str) -> dict:
    return {
        "schema": OBSERVATION_SCHEMA,
        "available": False,
        "quality": quality,
        "expected_session": expected.isoformat(),
        "asof": None,
        "phase": "unavailable",
        "active": None,
        "drawdown_pct": None,
        "loss_recovered_pct": None,
        "close": None,
        "peak_close": None,
        "low_close": None,
        "source_digest": None,
    }


def _price_rows(frame) -> list[tuple[str, float]]:
    """Do not fill gaps, select total-return close, or normalize intraday rows."""
    rows: list[tuple[str, float]] = []
    for stamp, value in frame["close_price"].items():
        if isinstance(stamp, datetime):
            # Non-midnight/tz-aware labels are deliberately preserved so the
            # canonical observer rejects rather than laundering them to a day.
            if stamp.time() != time(0) or stamp.tzinfo is not None:
                label = stamp.isoformat()
            else:
                label = stamp.date().isoformat()
        elif isinstance(stamp, date):
            label = stamp.isoformat()
        elif isinstance(stamp, str):
            label = stamp
        elif hasattr(stamp, "isoformat"):
            label = str(stamp.isoformat())
        else:
            label = str(stamp)
        rows.append((label, value))
    return rows


def snapshot(*, now: datetime | None = None, read: Callable | None = None,
             observer: Callable | None = None) -> dict:
    """Assess SPY's *price* close against the owning NYSE session calendar.

    The observer's price phases and retained episode reference are authoritative.
    No prediction is computed. Never substitute yahoo/SPY.close (total return)
    when close_price is missing. Negative or stale results are display-unavailable.
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
    if read is None:
        from lib import store
        read = store.read
    if observer is None:
        try:
            from lib.pullback_observation import observe as observer
        except ModuleNotFoundError as exc:
            if exc.name != "lib.pullback_observation":
                raise
            observer = None

    try:
        frame = read("yahoo", BENCHMARK)
        if frame is None or "close_price" not in frame.columns or frame.empty:
            result = _unavailable(expected, "source_unavailable")
        elif observer is None:
            result = _unavailable(expected, "observer_unavailable")
        else:
            result = observer(
                _price_rows(frame),
                expected_session=expected,
                is_session=nyse_calendar.is_session,
            )
            if not isinstance(result, dict) or result.get("schema") != OBSERVATION_SCHEMA:
                result = _unavailable(expected, "observation_inconsistent")
            elif result.get("available") and (
                result.get("quality") != "current"
                or result.get("asof") != expected.isoformat()
                or result.get("expected_session") != expected.isoformat()
            ):
                result = _unavailable(expected, "observation_inconsistent")
    except (OSError, TypeError, ValueError, KeyError, ArithmeticError):
        result = _unavailable(expected, "source_unavailable")

    return {
        **result,
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
    obs = observation if isinstance(observation, dict) else {}
    qualified = (
        obs.get("market") == "us"
        and obs.get("schema") == OBSERVATION_SCHEMA
        and obs.get("available") is True
        and obs.get("quality") == "current"
        and obs.get("clock") == "settled_close"
    )
    phase = obs.get("phase") if qualified else None
    phase = phase if phase in {
        "monitoring", "developing", "underway", "stabilizing",
        "recovering", "repaired",
    } else "unavailable"
    chart = ""
    if phase != "unavailable" and obs.get("price_path"):
        from lib import illus
        chart = illus.illus(
            obs["price_path"],
            kind="drawdown",
            height=188,
            accent="var(--down)",
            reference=0,
            value_fmt="{:.1f}%",
            aria_en="Observed SPY price closing drawdown from the retained episode high",
            aria_zh="SPY实际收盘价相对本轮参考高点的回撤",
        )
    return {"observation": obs, "phase": phase, "detail_chart_html": chart}
