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

DISPLAY/CONTEXT-ONLY — an observation of closes that already settled; no score,
forecast or sizing reads it.
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone

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


def first_disagreement(held: pd.DataFrame | None,
                       fetched: pd.DataFrame) -> tuple[str, float, float] | None:
    """(session, held close, vendor close) for the first held session the vendor
    now prints differently, or None when every overlapping session agrees."""
    if held is None:
        return None
    known = dict(zip(held["trade_date"], held["close"]))
    for day, price in zip(fetched["trade_date"], fetched["close"]):
        if day in known and round(float(known[day]), _CLOSE_DP) != price:
            return day, round(float(known[day]), _CLOSE_DP), price
    return None


def merge(held: pd.DataFrame | None, fetched: pd.DataFrame, *, first_seen: str) -> pd.DataFrame | None:
    """Keep every held row; add new sessions. None if any held session disagrees."""
    if first_disagreement(held, fetched) is not None:
        return None
    known = {} if held is None else dict(zip(held["trade_date"], held["close"]))
    fresh = []
    for day, price in zip(fetched["trade_date"], fetched["close"]):
        if day in known:
            continue
        fresh.append({"ticker": TICKER, "trade_date": day, "close": price,
                      "first_seen": first_seen})
    frames = [f for f in (held, pd.DataFrame(fresh, columns=list(COLUMNS))) if f is not None and not f.empty]
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("trade_date", kind="stable").reset_index(drop=True)


def refresh(*, today: date | None = None) -> int:
    if not tc.enabled():
        return 0
    today = today or datetime.now(timezone.utc).date()
    held = _held()
    start = ANCHOR
    if held is not None:
        start = max(ANCHOR, date.fromisoformat(str(held["trade_date"].max())) - timedelta(days=OVERLAP_DAYS))
    fetched = normalize(tc.query("index_daily", fields=_FIELDS, ts_code=TS_CODE,
                                 start_date=start.strftime("%Y%m%d"),
                                 end_date=today.strftime("%Y%m%d")))
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
