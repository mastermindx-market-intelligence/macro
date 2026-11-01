"""FINRA daily short-VOLUME collector — the fresher cousin of the bi-monthly
short-INTEREST feed (collectors/finra.py).

FINRA publishes a keyless flat file of consolidated daily short-sale volume,
one per trading day, posted by ~6pm ET:

    https://cdn.finra.org/equity/regsho/daily/CNMSshvol<YYYYMMDD>.txt
    Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market

`short_ratio = ShortVolume / TotalVolume` is the fraction of that day's
consolidated tape that printed on a short-sale order. Unlike bi-monthly short
*interest* (outstanding positions, ~2-week lag) this is *daily* — so a rising
short_ratio surfaces building bearish flow days/weeks before it shows up in the
settlement report. It is NOISY and the academic edge is modest/contested, so it
feeds the stock page as a CONTEXT confirmer (engine/short_volume.py), never a
scored alpha factor.

Append-only, deduped on (date, ticker), written to
data/finra_short_volume/panel.parquet. We backfill a rolling window each run
(cheap, self-healing); the merge keeps only genuinely new (date, ticker) rows.
Keyless — degrades to 'failed' only if FINRA's CDN is unreachable.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from collectors.base import Adapter, is_connection_error
from lib import config, nyse_calendar

log = logging.getLogger(__name__)

BASE = "https://cdn.finra.org/equity/regsho/daily"
LOOKBACK_DAYS = 30          # calendar days backfilled per run (dedup-merged)
GROUP = "finra_short_volume"
FINRA_AVAILABLE_ET = time(18, 30)


def expected_available_session(now: datetime | None = None) -> date:
    """Return the newest FINRA daily file the desk may require at ``now``.

    FINRA owns a later release clock than ordinary settled-price surfaces.  On
    an NYSE session day the current file becomes due at 18:30 ET; before then,
    and on weekends/holidays, the prior session remains the honest expectation.
    Naive datetimes follow the repository convention and are interpreted as UTC.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_et = now.astimezone(nyse_calendar.ET)
    today = now_et.date()
    if nyse_calendar.is_session(today) and now_et.time() >= FINRA_AVAILABLE_ET:
        return today
    return nyse_calendar.last_session_on_or_before(today - timedelta(days=1))


def _panel_path():
    return config.data_dir() / GROUP / "panel.parquet"


def _superseded_path():
    """Restatement witness (C19 WP24 DQ1-1): the original row of every
    (date, ticker) whose values a later re-fetch replaced. Change-only, so it
    stays empty unless FINRA really restates. Internal evidence only (DQ1-6)."""
    return _panel_path().parent / "superseded.parquet"


_VALUE_COLS = ["short_vol", "short_exempt", "total_vol", "short_ratio"]


def _universe_tickers() -> set[str]:
    """Our covered names, read from the breadth close-caches — keeps the panel
    lean (~1.5k names) vs FINRA's ~8k symbols. Empty set -> keep everything."""
    out: set[str] = set()
    for grp in ("breadth", "smallcap_breadth", "midcap_breadth"):
        p = config.data_dir() / grp / "_closes_cache.parquet"
        if p.exists():
            try:
                out.update(str(c) for c in pd.read_parquet(p).columns)
            except Exception:  # noqa: BLE001 — best-effort filter
                continue
    return out


def _business_days(n_calendar: int) -> list[date]:
    """Recent business days (Mon-Fri), newest-first, over the lookback window."""
    today = datetime.now(timezone.utc).date()
    out: list[date] = []
    for i in range(n_calendar):
        d = today - timedelta(days=i)
        if d.weekday() < 5:
            out.append(d)
    return out


def _parse(text: str) -> pd.DataFrame:
    """Parse one CNMSshvol file into normalized rows. Tolerates the trailing
    footer line FINRA appends (e.g. 'Total Records ...')."""
    rows: list[dict] = []
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) < 5 or parts[0] in ("Date", "") or not parts[0].isdigit():
            continue
        try:
            short_v = float(parts[2])
            total_v = float(parts[4])
        except (ValueError, IndexError):
            continue
        if total_v <= 0:
            continue
        raw = parts[1].strip()
        rows.append({
            "date": pd.Timestamp(parts[0]),
            "ticker": raw.upper(),
            "short_vol": short_v,
            "short_exempt": float(parts[3]) if parts[3].replace(".", "", 1).isdigit() else 0.0,
            "total_vol": total_v,
            "short_ratio": round(short_v / total_v, 4),
            "_upper": raw == raw.upper(),
        })
    return _resolve_case_collisions(pd.DataFrame(rows))


def _resolve_case_collisions(df: pd.DataFrame) -> pd.DataFrame:
    """C19 WP24 DQ1-4: FINRA lists distinct securities whose raw symbols differ
    only by case (e.g. BCPC common vs BCpC preferred). Folding to upper case
    makes them collide on (date, ticker). The raw symbol that is already
    all-uppercase wins regardless of line order; if none or several are, the
    last line in file order wins (the prior keep="last" behaviour)."""
    if df.empty:
        return df
    df = df.reset_index(drop=True)
    dup = df.duplicated(["date", "ticker"], keep=False)
    if dup.any():
        sub = df[dup].assign(_pos=df.index[dup])
        winners = (sub.sort_values(["_upper", "_pos"], kind="mergesort")
                      .drop_duplicates(["date", "ticker"], keep="last")["_pos"])
        log.info("finra_short_volume: %d case-fold collision row(s) dropped "
                 "(all-uppercase symbol kept)", int(dup.sum()) - len(winners))
        df = df[~dup | df.index.isin(winners)]
    return df.drop(columns=["_upper"]).reset_index(drop=True)


def _witness_superseded(prev: pd.DataFrame, fresh: pd.DataFrame) -> int:
    """C19 WP24 DQ1-1: append to the sidecar every prior panel row that this
    run's re-fetch replaces with different values. Returns the count. An
    identical re-read appends nothing."""
    if prev.empty or fresh.empty:
        return 0
    old = prev.drop_duplicates(["date", "ticker"], keep="last").copy()
    new = fresh.drop_duplicates(["date", "ticker"], keep="last").copy()
    old["date"] = pd.to_datetime(old["date"])
    new["date"] = pd.to_datetime(new["date"])
    both = old.merge(new[["date", "ticker", *_VALUE_COLS]], on=["date", "ticker"],
                     how="inner", suffixes=("", "__new"))
    if both.empty:
        return 0
    changed = pd.Series(False, index=both.index)
    for c in _VALUE_COLS:
        a, b = both[c], both[f"{c}__new"]
        changed |= (a != b) & ~(a.isna() & b.isna())
    if not changed.any():
        return 0
    gone = both.loc[changed, list(old.columns)].copy()
    gone["superseded_at_utc"] = pd.Timestamp.now("UTC")
    sp = _superseded_path()
    if sp.exists():
        gone = pd.concat([pd.read_parquet(sp), gone], ignore_index=True)
    gone.reset_index(drop=True).to_parquet(sp)
    return int(changed.sum())


class FinraShortVolumeAdapter(Adapter):
    name = "finra_short_volume"
    group = GROUP
    stale_after_days = 4          # daily feed, but tolerate weekends/holidays

    def _have_dates(self) -> set[pd.Timestamp]:
        p = _panel_path()
        if not p.exists():
            return set()
        try:
            return set(pd.read_parquet(p, columns=["date"])["date"].unique())
        except Exception:  # noqa: BLE001
            return set()

    def fetch(self, full_history: bool = False) -> dict[str, pd.DataFrame]:
        universe = _universe_tickers()
        have = self._have_dates()
        # Always re-fetch the newest 2 sessions, and any window date we don't yet
        # have. Whether FINRA restates a posted daily file is UNKNOWN (C19 WP24
        # DQ1-1); a replaced row is witnessed by superseded.parquet.
        wanted = _business_days(LOOKBACK_DAYS if not full_history else 120)
        new_frames: list[pd.DataFrame] = []
        fetched = skipped = 0
        for i, d in enumerate(wanted):
            ts = pd.Timestamp(d)
            if ts in have and i >= 2:
                continue
            url = f"{BASE}/CNMSshvol{d.strftime('%Y%m%d')}.txt"
            try:
                r = self.http_get(url, retries=2, timeout=30)
            except Exception as e:  # noqa: BLE001
                if is_connection_error(e):
                    if fetched == 0:
                        raise            # CDN down -> let runner mark failed
                    break                # partial run is fine; keep what we got
                skipped += 1             # 404 = holiday/not-yet-posted
                continue
            df = _parse(r.text)
            if df.empty:
                continue
            if universe:
                df = df[df["ticker"].isin(universe)]
            new_frames.append(df)
            fetched += 1

        if not new_frames:
            # Nothing new to add (cache already current) — emit a heartbeat so the
            # runner sees a successful, fresh run rather than a failure.
            if have:
                hb = pd.DataFrame({"new_rows": [0], "fetched": [0]},
                                  index=[pd.Timestamp(max(have))])
                return {"finra_short_volume__ingest": hb}
            raise RuntimeError(f"finra_short_volume: no data (fetched=0 skipped={skipped})")

        fresh = pd.concat(new_frames, ignore_index=True)
        path = _panel_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        superseded = 0
        if path.exists():
            prev = pd.read_parquet(path)
            superseded = _witness_superseded(prev, fresh)
            combined = pd.concat([prev, fresh], ignore_index=True)
        else:
            combined = fresh
        combined = (combined.drop_duplicates(subset=["date", "ticker"], keep="last")
                            .sort_values(["date", "ticker"]).reset_index(drop=True))
        combined.to_parquet(path)

        last = fresh["date"].max()
        log.info("finra_short_volume: +%d rows across %d sessions (%d skipped), panel=%d, "
                 "superseded=%d, latest %s",
                 len(fresh), fetched, skipped, len(combined), superseded, last.date())
        hb = pd.DataFrame({"new_rows": [len(fresh)], "fetched": [fetched]}, index=[last])
        return {"finra_short_volume__ingest": hb}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    FinraShortVolumeAdapter().fetch()
