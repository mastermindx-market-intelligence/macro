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

Same engine as the history (``engine.group_breadth_history``): no new metric,
threshold or signal. Nothing here relates breadth to forward returns or
outcomes. Never call this from the nightly render.

Usage:
  python scripts/extend_group_breadth_weekly.py --breadth-dir data/breadth --out data/breadth/history
"""
from __future__ import annotations

import argparse
import json
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
from scripts.build_group_breadth_history import membership_current  # noqa: E402

LIVE_NAME = "group_breadth_weekly_current_live"
ARCHIVE_NAME = "group_breadth_weekly_current.parquet"
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


def comparison_vs_archive(live: pd.DataFrame, archive: pd.DataFrame | None) -> dict:
    """Largest |difference| of the headline per sector over common weeks. Recorded, never a gate."""
    if archive is None or not len(archive):
        return {"common_weeks": 0, "note": "archive weekly file not found"}
    m = archive.merge(live, on=["date", "group"], suffixes=("_a", "_l"))
    m = m.dropna(subset=[f"{HEADLINE}_a", f"{HEADLINE}_l"])
    if not len(m):
        return {"common_weeks": 0}
    m["d"] = (m[f"{HEADLINE}_a"] - m[f"{HEADLINE}_l"]).abs()
    worst = m.loc[m["d"].idxmax()]
    return {
        "metric": HEADLINE,
        "common_weeks": int(m["date"].nunique()),
        "common_span": [str(m["date"].min().date()), str(m["date"].max().date())],
        "max_abs_diff_by_sector": {g: round(float(v), 4) for g, v in m.groupby("group")["d"].max().items()},
        "max_abs_diff": round(float(worst["d"]), 4),
        "max_at": {"group": str(worst["group"]), "date": str(pd.Timestamp(worst["date"]).date())},
        "expectation": ("about 4.76 points at most on the members priced in both stores (ruling 27 "
                        "section 3 test). This comparison uses each file's own members: the live "
                        "file prices members the archive capture lacks, which widens the gap"),
        "is_gate": False,
    }


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


def build(breadth_dir: Path, out: Path, downloader: Downloader = yf_download,
          scratch: Path | None = None, now: datetime | None = None) -> dict:
    mem = membership_current(breadth_dir)
    tickers = sorted(set(mem["ticker"]))
    vintage = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    closes = download_members(tickers, downloader)
    scratch = scratch or Path(tempfile.mkdtemp(prefix="breadth_live_"))
    scratch.mkdir(parents=True, exist_ok=True)
    closes.to_parquet(scratch / "live_download.parquet")  # scratch only; never the collector's cache
    closes = gbh.through_last_complete_row(closes.sort_index())
    weekly = gbh.weekly_fixed_set(closes, mem, include_last_partial_week=False)

    out.mkdir(parents=True, exist_ok=True)
    pq_path, meta_path = out / f"{LIVE_NAME}.parquet", out / f"{LIVE_NAME}.meta.json"
    if pq_path.exists() and _same(pd.read_parquet(pq_path), weekly):
        print("unchanged")
        return {"status": "unchanged", "rows": len(weekly)}

    priced = [t for t in tickers if t in closes and closes[t].notna().any()]
    unpriced = sorted(set(tickers) - set(priced))
    last = weekly["date"].max() if len(weekly) else None
    lastrows = weekly[weekly["date"] == last] if last is not None else weekly
    unpriced_by_group = mem[mem["ticker"].isin(unpriced)].groupby("group")["ticker"].apply(sorted).to_dict()
    arch_path = out / ARCHIVE_NAME
    archive = pd.read_parquet(arch_path) if arch_path.exists() else None

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
        "n_members_last_week": {str(r.group): int(r.n_members) for r in lastrows.itertuples()},
        "comparison_vs_archive": comparison_vs_archive(weekly, archive),
        "engine": "engine/group_breadth_history.py",
        "rows": len(weekly),
    }
    weekly.to_parquet(pq_path, index=False, compression="zstd")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return {"status": "written", **meta}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--breadth-dir", type=Path, default=_ROOT / "data" / "breadth")
    ap.add_argument("--out", type=Path, default=_ROOT / "data" / "breadth" / "history")
    ap.add_argument("--scratch", type=Path, default=None)
    a = ap.parse_args()
    r = build(a.breadth_dir, a.out, scratch=a.scratch)
    keep = ("status", "as_of_week", "price_vintage", "comparison_vs_archive", "members")
    print(json.dumps({k: r[k] for k in keep if k in r}, indent=2, default=str))


if __name__ == "__main__":
    main()
