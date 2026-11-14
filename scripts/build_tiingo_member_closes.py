"""Assemble a wide closes matrix for S&P 1500 ever-members from the Tiingo archive.

Off the render path, local only. Input for ``scripts/build_group_breadth_history.py``.
The output is MEMBER-LEVEL price history: it stays off git (R2 rules; the Tiingo
research reader marks raw views ``redistribution_admitted=false``).

Reads the normalized end-of-day store directly (one parquet per ticker history
per capture day): ``<root>/normalized/eod-bars/<capture-day>/<sha>.parquet``.
A ticker present on several capture days is the union of its files, the later
capture winning on a duplicate date. Values are ``close_tradj`` (total-return
adjusted, today's restated values), the same convention as the yfinance
auto-adjusted closes the nightly collector uses.

Ticker match: exact, then upper-case and dot/dash variants (BRK.B / BRK-B). The
matrix column carries the membership spelling. A file whose ``ticker_vendor``
disagrees with the requested ticker is skipped and counted.

Usage:
  python -m scripts.build_tiingo_member_closes \
      --root /Volumes/Mastermind/market-data/tiingo --breadth-dir data/breadth \
      --out /path/off-git/sp1500_closes_tradj.parquet
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

COLS = ["ticker_vendor", "market_date", "close_tradj"]


def variants(t: str) -> list[str]:
    out: list[str] = []
    for c in (t, t.upper(), t.replace(".", "-"), t.replace(".", "-").upper(),
              t.replace("-", "."), t.replace("-", ".").upper()):
        if c not in out:
            out.append(c)
    return out


def index_store(root: Path, workers: int) -> pd.DataFrame:
    files = sorted((root / "normalized" / "eod-bars").glob("*/*.parquet"))

    def one(p: Path):
        try:
            tv = pq.read_table(p, columns=["ticker_vendor"]).column(0)
            return {"ticker": tv[0].as_py() if len(tv) else None, "capture_day": p.parent.name,
                    "path": str(p), "rows": len(tv)}
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = [r for r in ex.map(one, files) if r and r["ticker"]]
    return pd.DataFrame(rows)


def wanted_tickers(breadth_dir: Path) -> list[str]:
    mem = pd.read_parquet(breadth_dir / "sp1500_pit_membership.parquet")
    cons = pd.read_parquet(breadth_dir / "constituents.parquet")
    have = set(mem["ticker"])
    seen = {v for t in have for v in variants(t)}
    extra = sorted(s for s in cons.index if s not in seen)
    return sorted(have) + extra


def build(root: Path, breadth_dir: Path, out: Path, workers: int = 16) -> dict:
    idx = index_store(root, workers).sort_values(["ticker", "capture_day", "rows"])
    by_t = {t: list(g["path"]) for t, g in idx.groupby("ticker", sort=False)}
    want = wanted_tickers(breadth_dir)
    match = {}
    for w in want:
        hit = next((c for c in variants(w) if c in by_t), None)
        if hit:
            match[w] = hit

    def load(w: str):
        parts = []
        for p in by_t[match[w]]:
            d = pq.read_table(p, columns=COLS).to_pandas()
            if set(d["ticker_vendor"].unique()) != {match[w]}:
                return w, None
            parts.append(d)
        d = pd.concat(parts, ignore_index=True)
        d["date"] = pd.to_datetime(d["market_date"]).dt.normalize()
        s = d.drop_duplicates("date", keep="last").set_index("date")["close_tradj"]
        return w, s.sort_index().astype("float64")

    series, mismatched = {}, []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for w, s in ex.map(load, list(match)):
            if s is None:
                mismatched.append(w)
            else:
                series[w] = s
    mat = pd.DataFrame(series).sort_index()
    mat.index.name = "market_date"
    out.parent.mkdir(parents=True, exist_ok=True)
    mat.to_parquet(out)
    return {"files_indexed": len(idx), "wanted": len(want), "matched": len(match),
            "loaded": len(series), "vendor_mismatch": len(mismatched),
            "not_found_sample": sorted(set(want) - set(match))[:40],
            "shape": list(mat.shape), "span": [str(mat.index.min().date()), str(mat.index.max().date())]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("/Volumes/Mastermind/market-data/tiingo"))
    ap.add_argument("--breadth-dir", type=Path, default=Path("data/breadth"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 4))
    a = ap.parse_args()
    print(json.dumps(build(a.root, a.breadth_dir, a.out, a.workers), indent=2))


if __name__ == "__main__":
    main()
