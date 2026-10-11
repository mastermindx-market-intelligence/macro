"""Market-neutral core of the Risk Radar measured-pullback popup.

The single owner of the episode is lib.pullback_observation.observe(). This
module admits one market's licensed settled-close series into that owner,
checks the result against the market's own session clock, and shapes the
popup read model. It computes no forecast, probability, ledger or sizing, and
reads no source itself: each market adapter supplies its reader, calendar and
labels (lib.us_pullback_observation, lib.cn_pullback_observation).
"""
from __future__ import annotations

from datetime import date, datetime, time
from math import isfinite
from numbers import Real
from typing import Callable, NamedTuple

OBSERVATION_SCHEMA = "pullback_observation.v1"
# Below this many points the shared renderer draws its "No history yet"
# placeholder, which would contradict the measured figures beside it.
MIN_CHART_POINTS = 4
# The owner rounds path values to 4 dp; its last value is the current drawdown.
PATH_TOLERANCE_PP = 0.01
# No broad-market close moves beyond 3:4 in one session (a market-wide halt caps
# a US session near -20%; mainland index members are limited to +/-20%). A
# consecutive ratio past it is a split or rebased series, never a market move.
LEVEL_BREAK_RATIO = 0.75
PHASES = frozenset({
    "monitoring", "developing", "underway", "stabilizing", "recovering", "repaired",
})


class SourceRefused(ValueError):
    """The licensed series cannot vouch for its price basis; display unavailable."""

    def __init__(self, quality: str):
        super().__init__(quality)
        self.quality = quality


class LicensedCloses(NamedTuple):
    rows: list
    appended: tuple = ()
    hold: str | None = None


def unavailable(expected: date, quality: str) -> dict:
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


def price_rows(frame, column: str = "close") -> list[tuple[str, float]]:
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


def session_day(label) -> date | None:
    if not isinstance(label, str) or len(label) != 10:
        return None
    try:
        return date.fromisoformat(label)
    except ValueError:
        return None


def positive(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    price = float(value)
    return price if isfinite(price) and price > 0 else None


def level_break(rows: list[tuple[str, float]]) -> bool:
    dated = sorted((day, price) for day, price in (
        (session_day(label), positive(value)) for label, value in rows)
        if day is not None and price is not None)
    return any(
        not LEVEL_BREAK_RATIO <= later / earlier <= 1 / LEVEL_BREAK_RATIO
        for (_, earlier), (_, later) in zip(dated, dated[1:]))


def observe_closes(expected: date, *, read: Callable | None,
                   observer: Callable | None,
                   is_session: Callable[[date], bool]) -> tuple[dict, dict]:
    """Run the owner over ``read(expected)``; anything not current is unavailable.

    Returns ``(observation, session_tip)``. Dependency admission is explicit:
    no source is read until the caller admits an observer.
    """
    tip = {"appended": [], "hold": None}
    if observer is None:
        return unavailable(expected, "observer_unavailable"), tip
    if read is None:
        return unavailable(expected, "source_unavailable"), tip
    try:
        got = read(expected)
        if not isinstance(got, LicensedCloses) or not got.rows:
            return unavailable(expected, "source_unavailable"), tip
        tip = {"appended": list(got.appended), "hold": got.hold}
        result = observer(list(got.rows), expected_session=expected,
                          is_session=is_session)
        if not isinstance(result, dict) or result.get("schema") != OBSERVATION_SCHEMA:
            result = unavailable(expected, "observation_inconsistent")
        elif result.get("available") and (
            result.get("quality") != "current"
            or result.get("asof") != expected.isoformat()
            or result.get("expected_session") != expected.isoformat()
        ):
            result = unavailable(expected, "observation_inconsistent")
    except SourceRefused as exc:
        result = unavailable(expected, exc.quality)
    except (OSError, TypeError, ValueError, KeyError, ArithmeticError):
        result = unavailable(expected, "source_unavailable")
    return result, tip


def episode_window(obs: dict) -> dict | None:
    """Display window only: the episode starts at the retained peak.

    The owner's path also carries closes from before that peak, measured against
    a high that did not exist yet; drawn as drawdown, a rally reads as damage.
    None, so no chart or table is drawn, unless the window agrees with the
    measured figures beside it. Length is the caller's check: a young window
    can be valid yet too short to draw. The observation itself is not modified.
    """
    path, peak_session = obs.get("price_path"), obs.get("peak_session")
    low_session = obs.get("low_session")
    # Before an episode the owner retains no low, and the fragment prints no
    # worst figure for the chart to contradict; the window still starts at the
    # reference high and ends at the current figure.
    no_episode = (obs.get("phase") in ("monitoring", "developing")
                  and obs.get("low_close") is None and low_session is None)
    if (not isinstance(path, dict) or not isinstance(peak_session, str)
            or not (no_episode or isinstance(low_session, str))):
        return None
    dates, vals = list(path.get("dates") or []), list(path.get("vals") or [])
    if len(dates) != len(vals) or not all(isinstance(d, str) for d in dates):
        return None
    # The owner's path reaches back to the retained high only within its cap,
    # so a very long episode's peak can predate it; starting mid-decline
    # would draw a partial episode.
    if peak_session not in dates:
        return None
    start = dates.index(peak_session)
    dates, vals = dates[start:], vals[start:]
    if not dates or dates[-1] != obs.get("asof"):
        return None
    if any(later <= earlier for earlier, later in zip(dates, dates[1:])):
        return None
    if not all(isinstance(v, Real) and not isinstance(v, bool) and isfinite(v)
               and -100.0 <= v <= 0.0 for v in vals):
        return None
    close, peak = positive(obs.get("close")), positive(obs.get("peak_close"))
    if close is None or peak is None:
        return None
    # A reclaimed close sits at the 0% line, as the owner draws it.
    end = min(0.0, 100.0 * (close / peak - 1.0))
    if abs(vals[0]) > PATH_TOLERANCE_PP or abs(vals[-1] - end) > PATH_TOLERANCE_PP:
        return None
    if not no_episode:
        low = positive(obs.get("low_close"))
        if low is None or low_session not in dates:
            return None
        low_pct = 100.0 * (low / peak - 1.0)
        if (abs(vals[dates.index(low_session)] - low_pct) > PATH_TOLERANCE_PP
                or min(vals) < low_pct - PATH_TOLERANCE_PP):
            return None
    # The owner rounds each point; a second rounding for the end tag can land
    # one tenth away from the metric. Draw the end from the metric's own ratio.
    return {"dates": dates, "vals": vals[:-1] + [end]}


def present(observation: dict, *, market: str, aria_en: str, aria_zh: str) -> dict:
    """Minimal shared-modal read model; risk odds are intentionally not ingested.

    Reuses the shared illustration renderer; no new visual charting engine.
    This does not confirm a trade, an episode, or a remaining-depth forecast.
    """
    obs = observation if isinstance(observation, dict) else {}
    qualified = (
        obs.get("market") == market
        and obs.get("schema") == OBSERVATION_SCHEMA
        and obs.get("available") is True
        and obs.get("quality") == "current"
        and obs.get("clock") == "settled_close"
    )
    phase = obs.get("phase") if qualified else None
    phase = phase if phase in PHASES else "unavailable"
    chart = ""
    window = episode_window(obs) if phase != "unavailable" else None
    # Below MIN_CHART_POINTS the shared renderer would print "No history yet".
    # A window that young is valid, not uncovered, and the copy must say which.
    shown = window if window is not None and len(window["dates"]) >= MIN_CHART_POINTS else None
    withheld = (None if shown is not None or phase == "unavailable"
                else "short" if window is not None else "uncovered")
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
            aria_en=aria_en,
            aria_zh=aria_zh,
        )
    # The table beside the chart is its text alternative; it reads the same window.
    return {"observation": obs, "phase": phase, "detail_chart_html": chart,
            "detail_path": shown, "detail_withheld": withheld}
