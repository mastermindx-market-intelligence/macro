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
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402

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


_CODE = ["engine/group_breadth_history.py", "scripts/build_group_breadth_history.py"]


def _code_version() -> str:
    """HEAD, suffixed ``+dirty`` when the engine or this builder differ from HEAD."""
    try:
        head = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", *_CODE],
                               capture_output=True, text=True, check=True).stdout.strip()
        return head + ("+dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def membership_current(breadth_dir: Path) -> pd.DataFrame:
    cons = pd.read_parquet(breadth_dir / "constituents.parquet").reset_index()
    sym = "symbol" if "symbol" in cons.columns else cons.columns[0]
    return cons.rename(columns={sym: "ticker", "sector": "group"})[["ticker", "group"]]


SIC_FILL = "sp1500_pit_sectors_sic_fill.parquet"


def membership_dated(breadth_dir: Path, src: str) -> pd.DataFrame:
    """Dated members with as-of-now labels; the free SIC fill overlay (when
    present) labels only tickers the substrate leaves unlabeled."""
    m = pd.read_parquet(breadth_dir / "sp1500_pit_membership.parquet")
    if src != "all":
        m = m[m["src"] == src]
    lab = pd.read_parquet(breadth_dir / "sp1500_pit_sectors.parquet")[["ticker", "sector"]]
    lab = lab.dropna().drop_duplicates("ticker")
    fill_path = breadth_dir / SIC_FILL
    if fill_path.exists():
        fill = pd.read_parquet(fill_path)[["ticker", "sector"]].dropna()
        lab = pd.concat([lab, fill[~fill["ticker"].isin(lab["ticker"])]], ignore_index=True)
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
             f"labels are as of now, not era-correct (current GICS, current SEC SIC, and the free SIC fill overlay marked sic_derived_fill).")
    return s, stats


def duplicate_series_pairs(closes: pd.DataFrame, mem: pd.DataFrame, min_sessions: int = 60,
                           min_share: float = 0.95) -> pd.DataFrame:
    """Pairs of distinct member tickers carrying the same price series (detection only).

    A store can hold another company's prices under a ticker (a verbatim copy).
    Candidates are found by hashing each ticker's daily returns month by month;
    a pair is flagged when at least ``min_sessions`` overlapping returns are
    identical and identical returns make up at least ``min_share`` of the overlap
    between the first and last identical session. ``ratio_cv`` is the coefficient
    of variation of the close ratio over that span (0 = constant ratio). Flat
    months are not hashed. Nothing is repaired.
    """
    used = sorted(set(mem["ticker"]) & set(closes.columns))
    c = closes[used]
    r = c.pct_change(fill_method=None).round(8)
    cand: set[tuple[str, str]] = set()
    for _, block in r.groupby(r.index.to_period("M")):
        b = block.loc[:, (block.notna().sum() >= 15) & ((block.fillna(0) != 0).sum() >= 5)]
        if b.shape[1] < 2:
            continue
        h = pd.util.hash_pandas_object(b.T.fillna(-9.0), index=False)
        h.index = b.columns
        for _, grp in h.groupby(h):
            names = sorted(grp.index)
            cand.update((x, y) for i, x in enumerate(names) for y in names[i + 1:])
    groups = mem.dropna(subset=["group"]).groupby("ticker")["group"].agg(lambda s: "|".join(sorted(set(s))))
    out = []
    for a, b in sorted(cand):
        ra, rb = r[a], r[b]
        both = ra.notna() & rb.notna()
        same = both & ((ra - rb).abs() < 1e-9)
        if same.sum() < min_sessions:
            continue
        lo, hi = same[same].index.min(), same[same].index.max()
        span = both.loc[lo:hi]
        share = same.loc[lo:hi].sum() / span.sum()
        if share < min_share:
            continue
        ratio = (c[a] / c[b]).loc[lo:hi][span]
        out.append({"ticker_a": a, "ticker_b": b, "group_a": groups.get(a), "group_b": groups.get(b),
                    "overlap_returns": int(both.sum()), "identical_returns": int(same.sum()),
                    "identical_share_in_span": round(float(share), 4),
                    "identical_from": str(lo.date()), "identical_to": str(hi.date()),
                    "ratio_cv": round(float(ratio.std() / ratio.mean()), 6) if len(ratio) > 1 else None})
    return pd.DataFrame(out, columns=["ticker_a", "ticker_b", "group_a", "group_b", "overlap_returns",
                                      "identical_returns", "identical_share_in_span", "identical_from",
                                      "identical_to", "ratio_cv"])


def count_duplicates_once(closes: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Blank ``ticker_b``'s closes over each flagged identical span (labelling, not repair).

    Which side is the genuine company cannot be told from prices alone; the
    sort-order second ticker is the one not counted. The store is untouched.
    """
    out = closes.copy()
    for p in pairs.itertuples(index=False):
        out.loc[p.identical_from:p.identical_to, p.ticker_b] = float("nan")
    return out


def drop_partial_rows(closes: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Drop rows priced for fewer than half the names priced on neighbouring rows.

    Note: the centred median looks up to 10 rows ahead, so WHICH vendor rows
    count as sessions depends on nearby later rows. No price, average or share
    uses later data; the nightly ledger path does not use this filter (it uses
    the collector's trailing 80% rule).

    Data cleaning, not a signal rule: a vendor row on a market holiday or a
    partial last capture otherwise becomes a 'session' and shifts every
    session-count horizon by one. The local reference is the centred 21-row
    median of the priced-name count. Dropped dates are listed in the sidecar.
    """
    n = closes.notna().sum(axis=1)
    ref = n.rolling(21, center=True, min_periods=1).median()
    bad = n < 0.5 * ref
    return closes[~bad], [str(d.date()) for d in closes.index[bad]]


def build(closes_path: Path, breadth_dir: Path, basis: str, out: Path, src: str = "sp500",
          closes_label: str | None = None) -> dict:
    closes, dropped_rows = drop_partial_rows(pd.read_parquet(closes_path).sort_index())
    mem = membership_current(breadth_dir) if basis == "current" else membership_dated(breadth_dir, src)
    dup_pairs = duplicate_series_pairs(closes, mem)
    closes = count_duplicates_once(closes, dup_pairs)
    daily = gbh.daily_group_breadth(closes, mem)
    weekly = gbh.weekly_fixed_set(closes, mem, include_last_partial_week=False)
    tag = basis if basis == "current" else f"dated_{src}"
    out.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out / f"group_breadth_daily_{tag}.parquet", index=False, compression="zstd")
    weekly.to_parquet(out / f"group_breadth_weekly_{tag}.parquet", index=False, compression="zstd")
    sentence, stats = missing_sentence(closes, mem, basis)
    if len(dup_pairs):
        named = "; ".join(f"{p.ticker_a}={p.ticker_b} {p.identical_from}..{p.identical_to}"
                          for p in dup_pairs.itertuples(index=False))
        sentence += (f" {len(dup_pairs)} ticker pair(s) carry the same price series and are "
                     f"counted once (the second ticker is not counted over the span): {named}.")
    else:
        sentence += (" Duplicate-series scan: no two member tickers carry the same price series "
                     "(identical daily returns or a constant price ratio).")
    valid = daily.dropna(subset=["pct_above_200"])
    inputs = [closes_path] + ([breadth_dir / "constituents.parquet"] if basis == "current" else
                              [breadth_dir / "sp1500_pit_membership.parquet",
                               breadth_dir / "sp1500_pit_sectors.parquet"]
                              + ([breadth_dir / SIC_FILL] if (breadth_dir / SIC_FILL).exists() else []))
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
        "closes_store": closes_label or str(closes_path),
        "missing": sentence,
        "coverage": stats,
        "dropped_partial_rows": dropped_rows,
        "duplicate_series_pairs": dup_pairs.to_dict("records"),
        "duplicate_series_rule": ("month-by-month hash of daily returns, then pairwise check: >=60 "
                                  "identical returns and >=95% identical between the first and last "
                                  "identical session. Detection and labelling only; no store repaired."),
        "dropped_partial_rows_rule": ("centred 21-row median of priced names; a row under half is "
                                      "dropped. Looks ahead up to 10 rows to decide which rows are "
                                      "sessions; values themselves use only data on or before their date."),
        "members_counted_at_year_end": {
            str(y): int(g.loc[g["date"] == g["date"].max(), "n_members"].sum())
            for y, g in daily.groupby(daily["date"].dt.year)},
        "members_counted_note": ("Sum across sectors of labelled, priced members on the year's last "
                                 "session. Compare with about 500 index members to read the "
                                 "survivorship lean of early years."),
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
    ap.add_argument("--closes-label", default=None,
                    help="how to name the closes store in the sidecar (e.g. the Tiingo archive and builder)")
    a = ap.parse_args()
    meta = build(a.closes, a.breadth_dir, a.basis, a.out, a.src, a.closes_label)
    print(json.dumps({k: meta[k] for k in ("basis", "span", "rows", "missing")}, indent=2))


if __name__ == "__main__":
    main()
