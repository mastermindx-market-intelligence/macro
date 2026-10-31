"""Shanghai Composite settled daily closes — Tushare index_daily (GATED).

The China Risk Radar measured-pullback section (lib.cn_pullback_observation)
replays the benchmark's settled closes through the one episode owner
(lib.pullback_observation). That reader admits only this licensed store.

GATED: no-ops unless ``TUSHARE_TOKEN`` is set.

STORE (merge by session, refuse disagreement):
  data/tushare/index_daily.parquet — one row per trade_date for ``000001.SS``:
  ticker, trade_date (YYYY-MM-DD), close (index points), first_seen (UTC ISO)
  The replay starts at a fixed ANCHOR, never a rolling window, so a figure does
  not move because the window slid. A run fetches from the anchor when the store
  is empty and otherwise re-reads a short overlap. A vendor close that disagrees
  with a held session rejects the whole fetch: the last-good store is kept and
  the reader's session check turns the popup unavailable rather than mixing
  two series. The run prints a ``::warning`` naming the session and both
  closes. To accept a vendor revision, delete the store in a reviewed commit;
  the next asia-close run rebuilds it from the anchor.
  Asia-close slots run before the settle buffer (17:00 CST), so a session is
  stored only once ``lib.cn_calendar`` counts it as settled; an earlier bar is
  left for the next run, never held and later refused as a revision.

DISPLAY/CONTEXT-ONLY — an observation of closes that already settled; no score,
forecast or sizing reads it.
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
import pandas as pd

from lib import config
from collectors import tushare_client as tc

log = logging.getLogger("tushare_index_daily")

OUT = config.data_dir() / "tushare" / "index_daily.parquet"
TS_CODE = "000001.SH"
TICKER = "000001.SS"
_FIELDS = "ts_code,trade_date,close"
COLUMNS = ("ticker", "trade_date", "close", "first_seen")
# Well over the observer's 63-close reference window before any episode a
# reader can be shown; one call (~1k rows) stays under the vendor page limit.
ANCHOR = date(2023, 1, 1)
# Re-read enough sessions to cross a Golden Week closure and late corrections.
OVERLAP_DAYS = 30
# Vendor index closes carry 4 dp; anything wider is a different series.
_CLOSE_DP = 4


def _held() -> pd.DataFrame | None:
    if not OUT.exists():
        return None
    try:
        held = pd.read_parquet(OUT)
    except Exception:  # noqa: BLE001 — unreadable store is refetched from the anchor
        log.warning("%s unreadable; refetching from %s", OUT.name, ANCHOR)
        return None
    if held.empty or not set(COLUMNS) <= set(held.columns):
        return None
    return held[list(COLUMNS)]


def normalize(raw: pd.DataFrame | None) -> pd.DataFrame | None:
    """Vendor frame -> {trade_date: close}; None unless every row is admissible."""
    if raw is None or raw.empty or not {"ts_code", "trade_date", "close"} <= set(raw.columns):
        return None
    if set(raw["ts_code"]) != {TICKER}:
        return None
    closes: dict[str, float] = {}
    for stamp, value in zip(raw["trade_date"], raw["close"]):
        try:
            day = datetime.strptime(str(stamp), "%Y%m%d").date().isoformat()
            price = round(float(value), _CLOSE_DP)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(price) or price <= 0:
            return None
        if day in closes and closes[day] != price:
            return None
        closes[day] = price
    return pd.DataFrame({"trade_date": list(closes), "close": list(closes.values())})


def _session_key(day: object) -> str | None:
    """The one YYYY-MM-DD key a held or fetched session is compared on.

    The store's contract is YYYY-MM-DD strings, but a stamp that reaches the
    store as a date/datetime/Timestamp, a numpy datetime64, or as a
    "YYYY-MM-DD 00:00:00" or "YYYYMMDD" string must still meet the vendor's
    print on the same key. Anything that does not name an ISO day — an empty,
    missing, impossible or NaT value — is None, and the caller refuses rather
    than guess.
    """
    if isinstance(day, str):
        text = day
    else:
        try:
            text = day.isoformat()
        except AttributeError:
            if not isinstance(day, np.datetime64):
                return None
            text = pd.Timestamp(day).isoformat()
    if not isinstance(text, str):
        return None
    if len(text) == 8 and text.isdigit():
        # Basic ISO 8601, which date.fromisoformat rejects before Python 3.11.
        try:
            return datetime.strptime(text, "%Y%m%d").date().isoformat()
        except ValueError:
            return None
    if len(text) < 10:
        return None
    candidate = text[:10]
    try:
        date.fromisoformat(candidate)
    except (TypeError, ValueError):
        return None
    return candidate


def first_disagreement(held: pd.DataFrame | None,
                       fetched: pd.DataFrame) -> tuple[str, float, float] | None:
    """(session, held close, vendor close) for the first held session the vendor
    now prints differently, or None when every overlapping session agrees."""
    if held is None:
        return None
    known = {}
    for day, close in zip(held["trade_date"], held["close"]):
        key = _session_key(day)
        if key is not None:
            known[key] = close
    for day, price in zip(fetched["trade_date"], fetched["close"]):
        key = _session_key(day)
        if key is None or key not in known:
            continue
        held_price = round(float(known[key]), _CLOSE_DP)
        if held_price != price:
            return key, held_price, price
    return None


def merge(held: pd.DataFrame | None, fetched: pd.DataFrame, *, first_seen: str) -> pd.DataFrame | None:
    """Keep every held row; add new sessions. None if any held session disagrees."""
    if first_disagreement(held, fetched) is not None:
        return None
    held_rows = None
    if held is not None and not held.empty:
        keys: list[str] = []
        for day in held["trade_date"]:
            key = _session_key(day)
            if key is None:
                return None
            keys.append(key)
        held_rows = held.copy()
        held_rows["trade_date"] = keys
    known = {} if held_rows is None else dict(zip(held_rows["trade_date"], held_rows["close"]))
    anchor = ANCHOR.isoformat()
    fresh = []
    for day, price in zip(fetched["trade_date"], fetched["close"]):
        key = _session_key(day)
        if key is None:
            return None
        # The replay is anchored; a vendor row dated before the anchor is not held.
        if key in known or key < anchor:
            continue
        fresh.append({"ticker": TICKER, "trade_date": key, "close": price,
                      "first_seen": first_seen})
    frames = [f for f in (held_rows, pd.DataFrame(fresh, columns=list(COLUMNS))) if f is not None and not f.empty]
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("trade_date", kind="stable").reset_index(drop=True)


def refresh(*, today: date | None = None, now: datetime | None = None) -> int:
    if not tc.enabled():
        return 0
    from lib import cn_calendar

    if now is None:
        # A given ``today`` is a whole past day: its close has settled.
        now = (datetime.combine(today, time(23, 59), tzinfo=cn_calendar.CST)
               if today is not None else datetime.now(timezone.utc))
    today = today or now.date()
    settled = cn_calendar.expected_last_session(now).isoformat()
    held = _held()
    start = ANCHOR
    if held is not None:
        # The store may hold typed stamps rather than the contracted ISO
        # strings, so read the last session back through the same key the
        # overlap is compared on. A value that names no ISO day (NaT/None)
        # takes the empty-store path instead of raising mid-run.
        last = _session_key(held["trade_date"].max())
        if last is not None:
            start = max(ANCHOR, date.fromisoformat(last) - timedelta(days=OVERLAP_DAYS))
    fetched = normalize(tc.query("index_daily", fields=_FIELDS, ts_code=TS_CODE,
                                 start_date=start.strftime("%Y%m%d"),
                                 end_date=today.strftime("%Y%m%d")))
    if fetched is not None:
        fetched = fetched[fetched["trade_date"] <= settled].reset_index(drop=True)
        fetched = fetched if not fetched.empty else None
    if fetched is None:
        log.warning("tushare index_daily: no admissible %s closes; last-good store retained", TICKER)
        return 0
    clash = first_disagreement(held, fetched)
    if clash is not None:
        day, kept, revised = clash
        # Bare line-start print: a logger prefix would drop the annotation, and a
        # refusal that only logs leaves the store frozen with nobody told why.
        print("::warning title=China index store refused a revised close::"
              f"{OUT.name} holds {kept} for {TICKER} session {day}; the vendor now "
              f"prints {revised}. The last-good store is kept and no new session is "
              "added, so the China pullback section goes unavailable as the store "
              f"ages. To accept the revision, delete data/tushare/{OUT.name} in a "
              f"reviewed commit; the next asia-close run rebuilds it from {ANCHOR}.",
              flush=True)
        return 0
    out = merge(held, fetched, first_seen=datetime.now(timezone.utc).isoformat())
    if out is None:
        log.warning("tushare index_daily: nothing admissible to merge; last-good store retained")
        return 0
    added = len(out) - (0 if held is None else len(held))
    if added == 0:
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".parquet.tmp")
    out.to_parquet(tmp, index=False)
    tmp.replace(OUT)
    log.info("tushare index_daily: +%d sessions -> %s (through %s)", added, OUT,
             out["trade_date"].iloc[-1])
    return added


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    refresh()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
