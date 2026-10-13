"""Asof-aware Tushare-vs-free-fallback preference + a consume-time staleness badge.

THE BUG (masterplan §W6-CN fix 4): the gated Tushare drip plane (``data/tushare/*.parquet``)
was PREFERRED over fresh free fallbacks on FILE PRESENCE ALONE — never asof. When the
Tushare token drops out of the collection environment the client no-ops silently
(``collectors/tushare_client.query`` returns None with no token), so the last committed
Tushare parquet freezes in place. Consumers kept reading that frozen plane in preference
to the free siblings that were updating daily — inverted source preference: STALE gated
beats FRESH free. (Live 2026-07-01: all ``data/tushare/*`` stuck at 2026-06-18/06-21 while
``china_a_val`` etc. read 2026-06-30/07-01.)

THE FIX: prefer Tushare only when its data-through date is within ``max_lag_sessions`` of
the free source's — otherwise fall back to the fresh free plane. Also exposes the Tushare
plane's data-through date so run_status/health can register it and surfaces can render a
staleness badge.

Pure/best-effort: any parse issue degrades to "unknown asof" which, being conservative,
DE-prefers Tushare (fresh free wins) rather than silently trusting a stale gated file.
"""
from __future__ import annotations

import logging

import pandas as pd

from lib import config

log = logging.getLogger("tushare_freshness")

# A Tushare drip may legitimately lag the free daily by one session (its cron runs on a
# different lane); beyond that it is stale and the fresh free source should win.
DEFAULT_MAX_LAG_SESSIONS = 1
_DAILY_TRADE_TABLES = frozenset({"valuation", "margin", "moneyflow", "chips"})

# Column names that carry a Tushare frame's data-through date, most-authoritative first.
# trade_date = the actual market session the row describes (the honest data-through date).
# ann_date = announcement date (forecast/report tables — when the number became public).
# NOTE: end_date is a reporting-PERIOD end (e.g. the fiscal quarter a forecast covers), NOT a
# data-through date — it runs AHEAD of announcement, so it must rank LAST or it overstates
# freshness (a forecast frozen since its ann_date would read fresh-through its period end).
# asof/date are build stamps (later than the data), so they sit below the true market dates
# but above end_date.
_ASOF_COLS = ("trade_date", "ann_date", "date", "asof", "end_date")


def frame_asof(df: pd.DataFrame | None) -> pd.Timestamp | None:
    """The data-through date of a stored frame (max over its date-ish column/index).

    Reads ``trade_date`` in preference to the build ``asof`` — a frozen Tushare plane
    still stamps a fresh ``asof`` at each no-op build, so ``asof`` would MASK the freeze;
    ``trade_date`` is the honest market-session date. None if undatable."""
    if df is None or len(df) == 0:
        return None
    for col in _ASOF_COLS:
        if col in df.columns:
            s = pd.to_datetime(df[col].astype(str), errors="coerce", format="mixed")
            if s.notna().any():
                return s.max().normalize()
    idx = getattr(df, "index", None)
    if isinstance(idx, pd.DatetimeIndex) and len(idx):
        return idx.max().normalize()
    return None


def tushare_asof(table: str) -> pd.Timestamp | None:
    """data-through date of ``data/tushare/<table>.parquet`` (via frame_asof). None if absent."""
    p = config.data_dir() / "tushare" / f"{table}.parquet"
    if not p.exists():
        return None
    try:
        return frame_asof(pd.read_parquet(p))
    except Exception as e:  # noqa: BLE001 — a broken cache must never break a build
        log.warning("tushare_freshness: %s unreadable (%s)", table, e)
        return None


def prefer_tushare(tushare_df: pd.DataFrame | None, free_df: pd.DataFrame | None, *,
                   max_lag_sessions: int = DEFAULT_MAX_LAG_SESSIONS) -> tuple[pd.DataFrame | None, str]:
    """Choose between a gated Tushare frame and a free-fallback frame, ASOF-AWARE.

    Returns ``(chosen_df, source)`` where source ∈ {"tushare", "free", "none"}. Tushare
    wins only when present AND its data-through date is no more than ``max_lag_sessions``
    sessions behind the free source's for trade_date tables (elapsed days for reports) (or the free source is itself undatable/missing).
    A frozen Tushare plane (older than the gate) loses to a fresh free frame. Conservative:
    an undatable Tushare frame de-prefers itself.
    """
    if tushare_df is None or len(tushare_df) == 0:
        return (free_df, "free" if free_df is not None else "none")
    if free_df is None or len(free_df) == 0:
        return (tushare_df, "tushare")          # nothing fresher to compare against
    t_as, f_as = frame_asof(tushare_df), frame_asof(free_df)
    if t_as is None:                            # can't date Tushare → don't trust it over fresh free
        return (free_df, "free")
    if f_as is None:                            # can't date free → keep Tushare (its own asof known)
        return (tushare_df, "tushare")
    lag = (f_as - t_as).days
    if "trade_date" in tushare_df.columns:
        from lib.market_session import is_session_date, missed_sessions
        if not is_session_date("CN", t_as.date()):
            return (free_df, "free")
        lag = missed_sessions("CN", t_as.date(), f_as.date())
    if lag > max_lag_sessions:
        log.info("tushare_freshness: Tushare stale (through %s, free through %s, lag %d > %d) — using free",
                 t_as.date(), f_as.date(), lag, max_lag_sessions)
        return (free_df, "free")
    return (tushare_df, "tushare")


def staleness_badge(table: str, *, expected_cadence_days: int = 1,
                    ref: pd.Timestamp | None = None) -> dict:
    """Consume-time freshness descriptor for a Tushare table:
    ``{table, asof, lag_days, state}`` with state ∈ {fresh, slow, stale, dead}. ``ref`` is
    the comparison instant (default: now, UTC). Daily trade tables grade completed CN
    sessions; periodic announcements retain elapsed days. lag_days remains raw elapsed
    days. ``dead`` = >10× cadence, missing, or an invalid daily observation."""
    # ref must be tz-NAIVE to line up with frame_asof(), which returns naive timestamps.
    # pandas >= 3 makes Timestamp.utcnow() tz-AWARE (and deprecates it), so the old
    # `(ref or pd.Timestamp.utcnow()).normalize()` raised
    # "Cannot subtract tz-naive and tz-aware datetime-like objects" on the lag line below —
    # for every PRESENT table. build_china_library's invisible-freeze guard caught that
    # TypeError in its own try/except and logged "health registration failed", so
    # run_status never carried a `tushare` block and the STALE/DEAD warning could never
    # fire: the freeze guard was itself silently frozen. Strip the tz, never subtract raw.
    instant = pd.Timestamp(ref) if ref is not None else pd.Timestamp.now("UTC")
    ref = instant
    if ref.tzinfo is not None:
        ref = ref.tz_localize(None)
    ref = ref.normalize()
    asof = tushare_asof(table)
    if asof is None:
        return {"table": table, "asof": None, "lag_days": None, "state": "dead"}
    lag = int((ref - asof).days)
    lag_sessions = None
    grade_lag = lag
    extra = {}
    if table in _DAILY_TRADE_TABLES and expected_cadence_days == 1:
        from lib.market_session import session_freshness
        freshness = session_freshness("CN", asof.date(), instant.to_pydatetime())
        lag_sessions = freshness["lag_sessions"]
        extra = {"lag_sessions": lag_sessions, "expected_session": freshness["expected_session"],
                 "calendar_verified": freshness["calendar_verified"]}
        if freshness["state"] in ("missing", "invalid", "unverified") or lag_sessions is None:
            return {"table": table, "asof": str(asof.date()), "lag_days": lag,
                    "state": "dead", **extra}
        grade_lag = lag_sessions
    if grade_lag <= expected_cadence_days:
        state = "fresh"
    elif grade_lag <= expected_cadence_days * 3:
        state = "slow"
    elif grade_lag <= expected_cadence_days * 10:
        state = "stale"
    else:
        state = "dead"
    return {"table": table, "asof": str(asof.date()), "lag_days": lag, "state": state, **extra}
