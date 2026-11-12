"""Build the reconstructed group-breadth history (off the render path).

Runs the SAME functions as the nightly ledger (``engine.group_breadth_history``)
over a stored closes matrix and writes, per basis:

  <out>/group_breadth_daily_<basis_tag>.parquet    (date, group) levels/changes/ranks/states
  <out>/group_breadth_weekly_<basis_tag>.parquet   weekly fixed-set 13w/26w change
  <out>/group_breadth_<basis_tag>.meta.json        protocol §4.4 sidecar

Bases (Historical Reconstruction Protocol §4.4):
  current  -> ``reconstructed_current_membership``: today's members and labels
              applied to every past session (``constituents.parquet``).
  dated    -> ``reconstructed_dated_membership``: S&P 1500 dated membership
              (``sp1500_pit_membership.parquet``, rows with src == sp500 unless
              --src all) with as-of-now sector labels (``sp1500_pit_sectors``);
              labels are NOT era-correct, and a member without a stored close
              is missing.

No forward returns, no outcome relation, no threshold. Heavy compute: never call
this from the nightly render.

Usage:
  python -m scripts.build_group_breadth_history --closes data/breadth/_closes_cache.parquet \
      --breadth-dir data/breadth --basis current --out data/breadth/history
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engine import group_breadth_history as gbh

BASIS = {
    "current": "reconstructed_current_membership",
    "dated": "reconstructed_dated_membership",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def membership_current(breadth_dir: Path) -> pd.DataFrame:
    cons = pd.read_parquet(breadth_dir / "constituents.parquet").reset_index()
    sym = "symbol" if "symbol" in cons.columns else cons.columns[0]
    return cons.rename(columns={sym: "ticker", "sector": "group"})[["ticker", "group"]]


def membership_dated(breadth_dir: Path, src: str) -> pd.DataFrame:
    m = pd.read_parquet(breadth_dir / "sp1500_pit_membership.parquet")
    if src != "all":
        m = m[m["src"] == src]
    lab = pd.read_parquet(breadth_dir / "sp1500_pit_sectors.parquet")[["ticker", "sector"]]
    lab = lab.dropna().drop_duplicates("ticker")
    out = m.merge(lab, on="ticker", how="left").rename(columns={"sector": "group"})
    return out[["ticker", "group", "start_date", "end_date"]]


def unpriced_in_window(closes: pd.DataFrame, mem: pd.DataFrame) -> pd.DataFrame:
    """Membership rows with NO close inside their own [start_date, end_date) window.

    The engine already counts a member only on sessions inside its window, so a
    reused ticker whose stored history belongs to a later company (prices only
    after the old member left) contributes nothing. This lists those rows so the
    report can count them by year and the sidecar can name them.
    """
    idx = closes.index
    rows = []
    for r in mem.itertuples(index=False):
        s = pd.Timestamp(r.start_date) if "start_date" in mem.columns and pd.notna(r.start_date) else idx.min()
        e = pd.Timestamp(r.end_date) if "end_date" in mem.columns and pd.notna(r.end_date) else idx.max() + pd.Timedelta(days=1)
        if r.ticker in closes.columns:
            win = closes[r.ticker][(idx >= s) & (idx < e)]
            if win.notna().any():
                continue
        rows.append({"ticker": r.ticker, "group": r.group, "start_date": s, "end_date": e,
                     "ticker_in_store": r.ticker in closes.columns})
    return pd.DataFrame(rows, columns=["ticker", "group", "start_date", "end_date", "ticker_in_store"])


def missing_sentence(closes: pd.DataFrame, mem: pd.DataFrame, basis: str) -> tuple[str, dict]:
    tickers = set(closes.columns)
    ever = set(mem["ticker"])
    unpriced = sorted(ever - tickers)
    unlabeled = int(mem["group"].isna().sum())
    stats = {"members_in_map": len(ever), "members_priced": len(ever & tickers),
             "members_unpriced": len(unpriced), "membership_rows_unlabeled": unlabeled,
             "unpriced_sample": unpriced[:25]}
    if basis == "current":
        s = (f"Only today's members are present: every name that left the index before "
             f"{closes.index.max().date()} is absent from every past session, and today's "
             f"sector labels are applied to the whole span.")
    else:
        gone = unpriced_in_window(closes, mem)
        stats["rows_unpriced_in_own_window"] = len(gone)
        stats["rows_unpriced_in_own_window_ticker_present"] = int(gone["ticker_in_store"].sum())
        stats["unpriced_in_window_by_start_year"] = {
            str(k): int(v) for k, v in gone["start_date"].dt.year.value_counts().sort_index().items()}
        stats["unpriced_in_window_sample"] = sorted(gone["ticker"].unique())[:25]
        s = (f"{len(gone)} dated membership rows have no stored close inside their own membership "
             f"window and are absent (of these, {stats['rows_unpriced_in_own_window_ticker_present']} "
             f"tickers exist in the store only outside the window, a likely ticker reuse); "
             f"{unlabeled} membership rows carry no sector label and are absent from every sector; "
             f"labels are as of now, not era-correct.")
    return s, stats


def build(closes_path: Path, breadth_dir: Path, basis: str, out: Path, src: str = "sp500") -> dict:
    closes = pd.read_parquet(closes_path).sort_index()
    mem = membership_current(breadth_dir) if basis == "current" else membership_dated(breadth_dir, src)
    daily = gbh.daily_group_breadth(closes, mem)
    weekly = gbh.weekly_fixed_set(closes, mem, include_last_partial_week=False)
    tag = basis if basis == "current" else f"dated_{src}"
    out.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out / f"group_breadth_daily_{tag}.parquet", index=False)
    weekly.to_parquet(out / f"group_breadth_weekly_{tag}.parquet", index=False)
    sentence, stats = missing_sentence(closes, mem, basis)
    valid = daily.dropna(subset=["pct_above_200"])
    inputs = [closes_path] + ([breadth_dir / "constituents.parquet"] if basis == "current" else
                              [breadth_dir / "sp1500_pit_membership.parquet",
                               breadth_dir / "sp1500_pit_sectors.parquet"])
    meta = {
        "basis": BASIS[basis],
        "price_note": ("Adjusted closes are today's restated values (split and dividend "
                       "adjustment as of the store's capture), not the prices printed at the time. "
                       "The nightly member ledger reads the collector's closes; this history reads "
                       "the closes file named in inputs. Same functions, two stores; their overlap "
                       "is recorded in research/breadth_history/OVERLAP_CHECK.md."),
        "redistribution_note": ("Group-level shares and counts only; no member prices. The "
                                "Tiingo research reader marks raw views redistribution_admitted=false; "
                                "member-level history stays off git."),
        "span": {"closes_start": str(closes.index.min().date()),
                 "closes_end": str(closes.index.max().date()),
                 "first_valid_pct_above_200": str(valid["date"].min().date()) if len(valid) else None},
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_version": _code_version(),
        "engine": "engine/group_breadth_history.py",
        "inputs": [{"path": str(p), "sha256_16": _sha(p)} for p in inputs],
        "missing": sentence,
        "coverage": stats,
        "rules": {"windows": list(gbh.WINDOWS), "horizons_sessions": list(gbh.HORIZONS),
                  "horizons_weeks": list(gbh.WEEKLY_HORIZONS), "min_members": gbh.MIN_MEMBERS,
                  "headline": gbh.HEADLINE},
        "rows": {"daily": len(daily), "weekly": len(weekly)},
        "not_an_outcome_claim": "Data only. No forward return, hit rate or backtest is attached.",
    }
    (out / f"group_breadth_{tag}.meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--breadth-dir", type=Path, default=Path("data/breadth"))
    ap.add_argument("--basis", choices=sorted(BASIS), required=True)
    ap.add_argument("--src", default="sp500", help="dated basis: sp500|sp400|sp600|all")
    ap.add_argument("--out", type=Path, default=Path("data/breadth/history"))
    a = ap.parse_args()
    meta = build(a.closes, a.breadth_dir, a.basis, a.out, a.src)
    print(json.dumps({k: meta[k] for k in ("basis", "span", "rows", "missing")}, indent=2))


if __name__ == "__main__":
    main()
