"""Keep a live weekly sector-breadth series current from a single-vintage download (off the render path).

Despite the name, every run REBUILDS the whole file. It does not append. One
full-window download is taken per run, and every week in the output is
recomputed from that one download, so the file never mixes price-adjustment
vintages. The collector's closes cache does mix them (issue #11124: a nightly
one-month refresh merged over older rows leaves a dividend staircase). This
script therefore never reads that cache and never writes into it. The download
stays in memory or under ``--scratch``.

Output (``--out``, default ``data/breadth/history``):

  group_breadth_weekly_current_live.parquet   same columns as group_breadth_weekly_current.parquet
  group_breadth_weekly_current_live.meta.json  basis, price source and vintage, as-of week,
                                               member counts, aliases, recorded comparison

This file and the long history (``group_breadth_weekly_current.parquet``, built
from the Tiingo archive) sit on different price sources. They are compared, not
joined. The comparison is recorded in the meta and is not a gate.

Ticker aliases (``PRICE_ALIASES``): today's membership list carries two
symbols the price source no longer serves. Each alias is downloaded and renamed
back to the member ticker. Each was checked to be the same issuer: over 478
common sessions, its closes match the archive's series for that company (close
ratio 0.9996-1.0000, daily-return correlation 1.00000). The membership list
itself is the list owner's to fix (#11124).

House baskets (ruling 108). The same run also downloads the names of the US
house baskets (``data/baskets/membership.json``, today's active roster) that
are not already sector members, in a SECOND call made after the sector
download, and writes one more pair:

  basket_breadth_weekly_current_live.parquet   same columns as basket_breadth_weekly_current.parquet
  basket_breadth_weekly_current_live.meta.json  per-basket listed / priced / absent counts,
                                                where the history starts, price vintage

The sector file is computed from the sector download alone, exactly as before,
so it does not change when the extra names fail (a failed or partial basket
download leaves the sector file byte-identical). A bad night writes NO basket
file and the previous one stays in place: the basket pair is written only
when the basket download succeeded and passes the coverage floor below, and
each file is written to a temporary name and moved into place.

Coverage floor: ``BASKET_COVERAGE_FLOOR`` = 0.90 of the roster's distinct names
must carry a close on the last kept session. It is a data-quality floor only
(it decides whether this night's basket file is written at all; it is not a
signal, and the engine's per-group ``MIN_MEMBERS`` rule, and so the rotation
read's ``too_few_members``, is unchanged). The reason for 0.90: the archive
basket history priced 664 of the 702 roster names (94.6%), so a night below
90% has lost a large block of the download (a rate limit or an outage), and
basket shares built from it would move for reasons that are not the market.
Measured once on the real roster with this script's own download (2026-11-13):
698 of 702 names priced on the last kept session, 0.994, so the floor has room
on a normal night. A night that falls below it prints a ``::warning::`` line so
the skipped basket file is visible in the run log.

Duplicate series: the archive builder drops a name whose series duplicates
another roster name (an alias pair in a stale price store). This file is one
fresh download per run, keyed by the roster's own symbols, so that store-level
duplication does not arise; no such step is applied here.

The temporary files end in ``.tmp`` under ``data/`` and are ignored by git
(``data/**/*.tmp``). The meta is moved into place after the parquet; a kill
between the two moves can leave a new parquet beside the previous meta until
the next run rewrites both.

The basket history in this file starts where the download window starts
(``PERIOD``), recorded in its meta as ``history_start``; fields that need a
longer history read as unavailable downstream. It is never spliced onto the
archive basket file.

Same engine as the history (``engine.group_breadth_history``): no new metric,
threshold or signal. Nothing here relates breadth to forward returns or
outcomes. Never call this from the nightly render.

Usage:
  python scripts/extend_group_breadth_weekly.py --breadth-dir data/breadth --out data/breadth/history
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from scripts.build_basket_breadth_history import expand_multi, membership_baskets  # noqa: E402
from scripts.build_group_breadth_history import membership_current  # noqa: E402

LIVE_NAME = "group_breadth_weekly_current_live"
BASKET_LIVE_NAME = "basket_breadth_weekly_current_live"
BASKET_COVERAGE_FLOOR = 0.90
ARCHIVE_NAME = "group_breadth_weekly_current.parquet"
ARCHIVE_META = "group_breadth_current.meta.json"
PRICE_ALIASES = {"MMC": "MRSH", "FI": "FISV"}
PERIOD = "2y"  # a 200-session average plus 26 weeks, with room
BATCH = 100
HEADLINE = gbh.HEADLINE
SEPARATE_SOURCES = ("This file and the long history (group_breadth_weekly_current.parquet, "
                    "Tiingo archive) sit on different price sources. They are compared, not joined.")

Downloader = Callable[[list[str], str], pd.DataFrame]


def yf_download(tickers: list[str], period: str) -> pd.DataFrame:
    """Same call shape as collectors/breadth.py::_download_closes (auto_adjust=True)."""
    import yfinance as yf

    parts: list[pd.DataFrame] = []
    for i in range(0, len(tickers), BATCH):
        batch = tickers[i:i + BATCH]
        for attempt in range(3):
            try:
                df = yf.download(batch, period=period, auto_adjust=True, progress=False,
                                 group_by="column", threads=True)
                lvl0 = (df.columns.get_level_values(0)
                        if isinstance(df.columns, pd.MultiIndex) else df.columns)
                parts.append(df["Close"] if "Close" in lvl0 else df)
                break
            except Exception as e:  # noqa: BLE001
                print(f"batch {i // BATCH} failed ({e}); retry", file=sys.stderr)
                time.sleep(5 * 2 ** attempt)
        time.sleep(1)
    if not parts:
        raise RuntimeError("no closes downloaded")
    w = pd.concat(parts, axis=1)
    w = w.loc[:, ~w.columns.duplicated()].sort_index()
    w.index = pd.DatetimeIndex(w.index).tz_localize(None)
    return w


def download_members(tickers: list[str], downloader: Downloader, period: str = PERIOD) -> pd.DataFrame:
    """Download every member once (aliases fetched under their alias, renamed back)."""
    fetch = [PRICE_ALIASES.get(t, t) for t in tickers]
    raw = downloader(sorted(set(fetch)), period)
    back = {v: k for k, v in PRICE_ALIASES.items() if k in tickers}
    raw = raw.rename(columns=back)
    return raw.reindex(columns=sorted(set(tickers)))


def _max_diff(live: pd.DataFrame, archive: pd.DataFrame) -> dict:
    m = archive.merge(live, on=["date", "group"], suffixes=("_a", "_l"))
    m = m.dropna(subset=[f"{HEADLINE}_a", f"{HEADLINE}_l"])
    if not len(m):
        return {"common_weeks": 0}
    m["d"] = (m[f"{HEADLINE}_a"] - m[f"{HEADLINE}_l"]).abs()
    worst = m.loc[m["d"].idxmax()]
    return {
        "common_weeks": int(m["date"].nunique()),
        "common_span": [str(m["date"].min().date()), str(m["date"].max().date())],
        "max_abs_diff_by_sector": {g: round(float(v), 4) for g, v in m.groupby("group")["d"].max().items()},
        "max_abs_diff": round(float(worst["d"]), 4),
        "max_at": {"group": str(worst["group"]), "date": str(pd.Timestamp(worst["date"]).date())},
    }


def comparison_vs_archive(live: pd.DataFrame, archive: pd.DataFrame | None,
                          live_common: pd.DataFrame | None = None,
                          live_only: list[str] | None = None) -> dict:
    """Largest |difference| of the headline per sector over common weeks. Recorded, never a gate.

    Two numbers, so the price-source part and the member-set part stay apart:
    ``each_file_own_members`` compares the live file as published; ``common_members_only``
    recomputes the live side on the members the archive file also prices.
    """
    if archive is None or not len(archive):
        return {"common_weeks": 0, "note": "archive weekly file not found", "is_gate": False}
    out = {
        "metric": HEADLINE,
        "each_file_own_members": _max_diff(live, archive),
        "expectation": "about 4.76 points at most on the common members (ruling 27 section 3 test)",
        "is_gate": False,
    }
    if live_common is not None:
        out["common_members_only"] = _max_diff(live_common, archive)
        out["members_priced_only_in_live"] = {"count": len(live_only or []), "tickers": sorted(live_only or [])}
    return out


def archive_unpriced(meta_path: Path) -> set[str] | None:
    """Members the archive history could not price, from its own sidecar (None if not complete)."""
    if not meta_path.exists():
        return None
    cov = json.loads(meta_path.read_text()).get("coverage", {})
    names = cov.get("unpriced_sample")
    if names is None or len(names) != cov.get("members_unpriced"):
        return None  # a truncated sample cannot define the common set
    return set(names)


def _same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return False
    for c in a.columns:
        x, y = a[c].reset_index(drop=True), b[c].reset_index(drop=True)
        if pd.api.types.is_float_dtype(x) and pd.api.types.is_float_dtype(y):
            if not np.allclose(x.to_numpy(), y.to_numpy(), rtol=0, atol=1e-12, equal_nan=True):
                return False
        elif not x.astype(str).equals(y.astype(str)):
            return False
    return True


def _write_atomic(df: pd.DataFrame, meta: dict, pq_path: Path, meta_path: Path) -> None:
    """Both files go to temporary names first, then move into place (no partial file)."""
    tmp_pq = pq_path.with_name(pq_path.name + ".tmp")
    tmp_meta = meta_path.with_name(meta_path.name + ".tmp")
    try:
        df.to_parquet(tmp_pq, index=False, compression="zstd")
        tmp_meta.write_text(json.dumps(meta, indent=2, default=str) + "\n")
        os.replace(tmp_pq, pq_path)
        os.replace(tmp_meta, meta_path)
    finally:
        tmp_pq.unlink(missing_ok=True)
        tmp_meta.unlink(missing_ok=True)


def build_baskets(sector_closes: pd.DataFrame, membership_path: Path, out: Path,
                  downloader: Downloader, scratch: Path, vintage: str) -> dict:
    """The house-basket live file from the sector download plus one extra call.

    Never raises: every failure is a status, the basket pair is not written, and
    the previous pair stays. The sector file was already written from
    ``sector_closes`` before this runs, so nothing here can change it.
    """
    pq_path, meta_path = out / f"{BASKET_LIVE_NAME}.parquet", out / f"{BASKET_LIVE_NAME}.meta.json"
    try:
        mem = membership_baskets(membership_path)
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_written", "reason": f"house basket roster unreadable: {exc}"}
    names = sorted(set(mem["ticker"]))
    extra = [t for t in names if t not in sector_closes.columns]
    try:
        extra_closes = download_members(extra, downloader) if extra else pd.DataFrame(index=sector_closes.index)
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_written", "reason": f"basket download failed: {exc}"}
    extra_closes.to_parquet(scratch / "live_download_baskets.parquet")  # scratch only
    have = [t for t in names if t in sector_closes.columns]
    closes = pd.concat([sector_closes[have], extra_closes], axis=1).sort_index()
    closes = closes.loc[:, ~closes.columns.duplicated()].reindex(columns=names)
    closes = gbh.through_last_complete_row(closes)
    if not len(closes):
        return {"status": "not_written", "reason": "basket download has no complete session"}

    last_row = closes.iloc[-1]
    priced_last = {t for t in names if pd.notna(last_row.get(t))}
    coverage = len(priced_last) / len(names) if names else 0.0
    if coverage < BASKET_COVERAGE_FLOOR:
        return {"status": "not_written",
                "reason": (f"coverage {len(priced_last)}/{len(names)} = {coverage:.3f} below the "
                           f"data-quality floor {BASKET_COVERAGE_FLOOR}")}

    wide, emem = expand_multi(closes, mem)
    groups = sorted(mem["group"].unique())
    weekly = gbh.weekly_fixed_set(wide, emem, groups=groups, include_last_partial_week=False)
    if not len(weekly):
        return {"status": "not_written", "reason": "no weekly row"}
    if pq_path.exists():
        try:
            if _same(pd.read_parquet(pq_path), weekly):
                return {"status": "unchanged", "rows": len(weekly)}
        except Exception:  # noqa: BLE001 - an unreadable previous file is replaced
            pass

    per_basket = {}
    for g in groups:
        listed = sorted(set(mem.loc[mem["group"] == g, "ticker"]))
        priced = [t for t in listed if t in priced_last]
        per_basket[g] = {"listed": len(listed), "priced": len(priced),
                         "absent": len(listed) - len(priced)}
    last = weekly["date"].max()
    meta = {
        "basis": "reconstructed_current_membership",
        "basis_note": "today's active basket roster applied to the past; not point-in-time; survivors only",
        "members_from": "data/baskets/membership.json (house definitions on main), active members only",
        "separate_sources": ("This file and the archive basket history (basket_breadth_weekly_current.parquet) "
                             "sit on different price sources. One of the two is read per build; they are "
                             "never joined."),
        "price_source": ("full-window download (period " f"{PERIOD}), one vintage per run, "
                         "auto-adjusted closes; never the collector's cache (#11124)"),
        "price_vintage": vintage,
        "as_of_week": str(pd.Timestamp(last).date()),
        "history_start": str(closes.index.min().date()),
        "history_note": ("The history starts at the download window's first session. A 200-session "
                         "average and its 13- and 26-week changes need that much history first; earlier "
                         "weeks read missing. Fields needing more history read as unavailable downstream."),
        "span": {"closes_start": str(closes.index.min().date()), "closes_end": str(closes.index.max().date())},
        "refresh": "every run rebuilds the whole file from one download; nothing is appended across vintages",
        "coverage_floor": {"value": BASKET_COVERAGE_FLOOR,
                           "measured": round(coverage, 4),
                           "rule": ("share of the roster's distinct names with a close on the last kept "
                                    "session; below it the night writes no basket file (data quality only)")},
        "counts": {"definitions": {"listed": "active members of the basket on today's roster",
                                   "priced": "listed members with a close on the last kept session",
                                   "absent": "listed minus priced"},
                   "names": {"listed": len(names), "priced": len(priced_last),
                             "absent": len(names) - len(priced_last)},
                   "by_basket": per_basket},
        "engine": "engine/group_breadth_history.py",
        "rules": {"min_members": gbh.MIN_MEMBERS, "headline": HEADLINE},
        "rows": len(weekly),
        "not_an_outcome_claim": "Data only. No forward return, hit rate or backtest is attached.",
    }
    try:
        _write_atomic(weekly, meta, pq_path, meta_path)
    except OSError as exc:
        return {"status": "not_written", "reason": f"write failed: {exc}"}
    return {"status": "written", "as_of_week": meta["as_of_week"], "counts": meta["counts"]["names"]}


def build(breadth_dir: Path, out: Path, downloader: Downloader = yf_download,
          scratch: Path | None = None, now: datetime | None = None,
          membership_path: Path | None = None) -> dict:
    """Sector live file first (unchanged contract), then the house-basket live file."""
    vintage = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    scratch = scratch or Path(tempfile.mkdtemp(prefix="breadth_live_"))
    scratch.mkdir(parents=True, exist_ok=True)
    result, sector_closes = build_sectors(breadth_dir, out, downloader, scratch, vintage)
    if membership_path is not None:
        try:
            result["baskets"] = build_baskets(sector_closes, membership_path, out, downloader,
                                              scratch, vintage)
        except Exception as exc:  # noqa: BLE001 - the basket file never fails the sector file
            result["baskets"] = {"status": "not_written", "reason": f"basket build failed: {exc}"}
    return result


def build_sectors(breadth_dir: Path, out: Path, downloader: Downloader,
                  scratch: Path, vintage: str) -> tuple[dict, pd.DataFrame]:
    """The sector live file, computed from the sector download only (as before)."""
    mem = membership_current(breadth_dir)
    tickers = sorted(set(mem["ticker"]))
    raw = download_members(tickers, downloader)
    raw.to_parquet(scratch / "live_download.parquet")  # scratch only; never the collector's cache
    closes = gbh.through_last_complete_row(raw.sort_index())
    weekly = gbh.weekly_fixed_set(closes, mem, include_last_partial_week=False)

    out.mkdir(parents=True, exist_ok=True)
    pq_path, meta_path = out / f"{LIVE_NAME}.parquet", out / f"{LIVE_NAME}.meta.json"
    if pq_path.exists() and _same(pd.read_parquet(pq_path), weekly):
        print("unchanged")
        return {"status": "unchanged", "rows": len(weekly)}, raw

    priced = [t for t in tickers if t in closes and closes[t].notna().any()]
    unpriced = sorted(set(tickers) - set(priced))
    last = weekly["date"].max() if len(weekly) else None
    lastrows = weekly[weekly["date"] == last] if last is not None else weekly
    unpriced_by_group = mem[mem["ticker"].isin(unpriced)].groupby("group")["ticker"].apply(sorted).to_dict()
    arch_path = out / ARCHIVE_NAME
    archive = pd.read_parquet(arch_path) if arch_path.exists() else None
    live_common, live_only = None, None
    arch_unpriced = archive_unpriced(out / ARCHIVE_META)
    if archive is not None and arch_unpriced is not None:
        live_only = sorted(set(priced) & arch_unpriced)
        keep = [t for t in closes.columns if t not in arch_unpriced]
        live_common = gbh.weekly_fixed_set(closes[keep], mem[mem["ticker"].isin(keep)],
                                           include_last_partial_week=False)

    meta = {
        "basis": "reconstructed_current_membership",
        "basis_note": "today's members applied to the past; not point-in-time; survivors only",
        "separate_sources": SEPARATE_SOURCES,
        "price_source": ("yfinance auto_adjust=True full-window download (period "
                         f"{PERIOD}), one vintage per run; never the collector's cache (#11124)"),
        "price_vintage": vintage,
        "as_of_week": str(pd.Timestamp(last).date()) if last is not None else None,
        "span": {"closes_start": str(closes.index.min().date()), "closes_end": str(closes.index.max().date())},
        "refresh": "every run rebuilds the whole file from one download; nothing is appended across vintages",
        "stale_rule": "label stale at two or more completed weekly closes behind the latest session",
        "members": {"in_map": len(tickers), "priced": len(priced), "unpriced": unpriced,
                    "unpriced_by_group": unpriced_by_group},
        "aliases": {k: {"downloaded_as": v,
                        "evidence": "same issuer: closes match the archive's series for the company over 478 sessions"}
                    for k, v in PRICE_ALIASES.items()},
        "counts_last_week": {
            "definitions": {
                "in_map": "members of the sector on today's list",
                "n_members": "members with a close that week",
                "n_has_200": "members with a defined 200-session average that week (the share's denominator)",
                "n_fixed_200_13w": ("members counted in the 13-week like-for-like change: a defined "
                                    "200-session average both that week and 13 weeks earlier (the headline's set)"),
            },
            "by_sector": {str(r.group): {"in_map": int((mem["group"] == r.group).sum()),
                                         "n_members": int(r.n_members), "n_has_200": int(r.n_has_200),
                                         "n_fixed_200_13w": int(r.n_fixed_200_13w)}
                          for r in lastrows.itertuples()},
        },
        "comparison_vs_archive": comparison_vs_archive(weekly, archive, live_common, live_only),
        "engine": "engine/group_breadth_history.py",
        "rows": len(weekly),
    }
    weekly.to_parquet(pq_path, index=False, compression="zstd")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return {"status": "written", **meta}, raw


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--breadth-dir", type=Path, default=_ROOT / "data" / "breadth")
    ap.add_argument("--out", type=Path, default=_ROOT / "data" / "breadth" / "history")
    ap.add_argument("--scratch", type=Path, default=None)
    ap.add_argument("--membership", type=Path, default=_ROOT / "data" / "baskets" / "membership.json",
                    help="house basket roster for the basket live file")
    a = ap.parse_args()
    t0 = time.monotonic()
    r = build(a.breadth_dir, a.out, scratch=a.scratch, membership_path=a.membership)
    r["run_seconds"] = round(time.monotonic() - t0, 1)
    b = r.get("baskets") or {}
    if b.get("status") == "not_written":
        print(f"::warning::house basket file not written tonight: {b.get('reason')}")
    keep = ("status", "as_of_week", "price_vintage", "comparison_vs_archive", "members",
            "baskets", "run_seconds")
    print(json.dumps({k: r[k] for k in keep if k in r}, indent=2, default=str))


if __name__ == "__main__":
    main()
