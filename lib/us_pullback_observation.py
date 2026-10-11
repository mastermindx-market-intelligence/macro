"""US settled-price pullback adapter; consumes the single existing raw-close observer.

No new episode ledger, forecast, source feed, or capital policy. The existing
held PR #8188 owns lib.pullback_observation.observe(). This module never imports
it: the builder must pass it to snapshot() as ``observer``. Until that binding
lands with the #8188 integration, every snapshot is unavailable.

Prices come only from the licensed whole-market daily store plus the same
vendor's same-session regular-hours close (both raw prints, one basis). The
Yahoo store is internal-only under the source-rights register and is never read.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from math import isfinite
from numbers import Real
from typing import Callable, NamedTuple

from lib import nyse_calendar

BENCHMARK = "SPY"
# Internal provenance label. Product surfaces never name the vendor.
SOURCE = "licensed_us_daily_bars/SPY.regular_session_close"
# Raw regular-session closes are this basis only while no split sits inside the
# observed window; licensed_spy_closes() refuses when one might.
PRICE_BASIS = "split_adjusted_dividend_unadjusted_close"
OBSERVATION_SCHEMA = "pullback_observation.v1"
# The daily store lands T+1; a longer gap is a stalled store, not a tip to patch.
MAX_SESSION_TIP = 3
# A market-wide halt caps one regular session near -20%, so a consecutive close
# ratio beyond 3:4 is a split-like basis break, never a market move.
SPLIT_LIKE_RATIO = 0.75
# Below this many points the shared renderer draws its "No history yet"
# placeholder, which would contradict the measured figures beside it.
MIN_CHART_POINTS = 4
# The owner rounds path values to 4 dp; its last value is the current drawdown.
PATH_TOLERANCE_PP = 0.01


class SourceRefused(ValueError):
    """The licensed series cannot vouch for its price basis; display unavailable."""

    def __init__(self, quality: str):
        super().__init__(quality)
        self.quality = quality


class LicensedCloses(NamedTuple):
    rows: list
    appended: tuple = ()
    hold: str | None = None


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


def _price_rows(frame, column: str = "close") -> list[tuple[str, float]]:
    """Do not fill gaps, select total-return close, or normalize intraday rows."""
    rows: list[tuple[str, float]] = []
    for stamp, value in frame[column].items():
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


def _session_day(label) -> date | None:
    if not isinstance(label, str) or len(label) != 10:
        return None
    try:
        return date.fromisoformat(label)
    except ValueError:
        return None


def _positive(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    price = float(value)
    return price if isfinite(price) and price > 0 else None


def _split_like_break(rows: list[tuple[str, float]]) -> bool:
    dated = sorted((day, price) for day, price in (
        (_session_day(label), _positive(value)) for label, value in rows)
        if day is not None and price is not None)
    return any(
        not SPLIT_LIKE_RATIO <= later / earlier <= 1 / SPLIT_LIKE_RATIO
        for (_, earlier), (_, later) in zip(dated, dated[1:]))


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
    rows = _price_rows(frame)
    stored = [day for day in (_session_day(label) for label, _ in rows)
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
        price = _positive((getattr(got, "closes", None) or {}).get(BENCHMARK))
        if getattr(got, "session", None) != session or price is None:
            hold = "session_close_unavailable"
            break
        if getattr(got, "finalized", False) is not True:
            # A snapshot close can still be revised; the popup says "Settled close".
            hold = "session_close_provisional"
            break
        rows.append((session, price))
        appended.append({"session": session, "settlement": "final"})
    if _split_like_break(rows):
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
    # Dependency admission is explicit: the held #8188 observer is never
    # auto-imported, and no source is read until an observer is admitted.
    tip = {"appended": [], "hold": None}
    if observer is None:
        result = _unavailable(expected, "observer_unavailable")
    elif read is None:
        result = _unavailable(expected, "source_unavailable")
    else:
        try:
            got = read(expected)
            if not isinstance(got, LicensedCloses) or not got.rows:
                result = _unavailable(expected, "source_unavailable")
            else:
                tip = {"appended": list(got.appended), "hold": got.hold}
                result = observer(
                    list(got.rows),
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
        except SourceRefused as exc:
            result = _unavailable(expected, exc.quality)
        except (OSError, TypeError, ValueError, KeyError, ArithmeticError):
            result = _unavailable(expected, "source_unavailable")

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


def _episode_window(obs: dict) -> dict | None:
    """Display window only: the episode starts at the retained peak.

    The owner's path also carries closes from before that peak, measured against
    a high that did not exist yet; drawn as drawdown, a rally reads as damage.
    None, so no chart or table is drawn, unless the window agrees with the
    measured figures beside it. The observation itself is not modified.
    """
    path, peak_session = obs.get("price_path"), obs.get("peak_session")
    if not isinstance(path, dict) or not isinstance(peak_session, str):
        return None
    dates, vals = list(path.get("dates") or []), list(path.get("vals") or [])
    if len(dates) != len(vals) or not all(isinstance(d, str) for d in dates):
        return None
    start = next((i for i, d in enumerate(dates) if d >= peak_session), len(dates))
    dates, vals = dates[start:], vals[start:]
    if len(dates) < MIN_CHART_POINTS or dates[-1] != obs.get("asof"):
        return None
    if any(later <= earlier for earlier, later in zip(dates, dates[1:])):
        return None
    if not all(isinstance(v, Real) and not isinstance(v, bool) and isfinite(v)
               and -100.0 <= v <= 0.0 for v in vals):
        return None
    close, peak = _positive(obs.get("close")), _positive(obs.get("peak_close"))
    if close is None or peak is None:
        return None
    # A reclaimed close sits at the 0% line, as the owner draws it.
    if abs(vals[-1] - min(0.0, 100.0 * (close / peak - 1.0))) > PATH_TOLERANCE_PP:
        return None
    low = _positive(obs.get("low_close"))
    if low is not None and min(vals) < 100.0 * (low / peak - 1.0) - PATH_TOLERANCE_PP:
        return None
    return {"dates": dates, "vals": vals}


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
    shown = _episode_window(obs) if phase != "unavailable" else None
    if shown is not None:
        from lib import illus
        chart = illus.illus(
            shown,
            kind="drawdown",
            height=188,
            accent="var(--down)",
            reference=0,
            # "z": a value that rounds to zero prints 0.0%, as the metric does.
            value_fmt="{:z.1f}%",
            aria_en="Observed SPY price closing drawdown from the retained episode high",
            aria_zh="SPY实际收盘价相对本轮参考高点的回撤",
        )
    # The table beside the chart is its text alternative; it reads the same window.
    return {"observation": obs, "phase": phase, "detail_chart_html": chart,
            "detail_path": shown}
