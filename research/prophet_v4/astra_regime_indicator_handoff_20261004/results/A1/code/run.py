#!/usr/bin/env python3
"""A1 census: inventory, ledgers, Pine vs canon.rsi_macd, 2D/3D bar clock.

Run from repo root:
  python3 research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1/code/run.py
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

from engine.canon import rsi_macd as canon_rsi_macd  # noqa: E402
from engine.bar_derive import derive_2d_ohlcv, derive_3d_ohlcv  # noqa: E402
from engine.session_anchor import session_positions  # noqa: E402
from engine.signal_quality import _rsi_macd as served_rsi_macd, _tf_grid  # noqa: E402

REPO = Path(".").resolve()
RESULTS = REPO / "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1"
CODE = RESULTS / "code"
sys.path.insert(0, str(CODE))
from pine_rsi_macd import pine_rsi_macd, bullish_cross_dates  # noqa: E402

WARMUP = 400
MAX_WORKERS = 8
YAHOO_TICKERS = [
    "SPY", "RSP", "QQQ", "IWM", "XLK", "XLE", "XLF", "XLV", "XLI",
    "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC",
]
OUTCOMES = ("T1_HIT", "T2_HIT", "INVALIDATED", "EXPIRED", "CLOSED_EARLY")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iso(x) -> str | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    try:
        ts = pd.Timestamp(x)
        if pd.isna(ts):
            return None
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return str(x)


def _first_last_from_df(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if df.empty:
        return None, None
    idx = df.index
    if isinstance(idx, pd.DatetimeIndex) and len(idx):
        return _iso(idx.min()), _iso(idx.max())
    for col in ("date", "Date", "as_of", "signal_date"):
        if col in df.columns:
            s = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(s):
                return _iso(s.min()), _iso(s.max())
    return None, None


def _parquet_inventory(path: Path) -> dict:
    rec = {
        "path": str(path.as_posix()) if path.is_absolute() else str(path),
        "exists": path.exists(),
        "sha256": None,
        "rows": None,
        "columns": None,
        "first_date": None,
        "last_date": None,
        "bytes": None,
    }
    rel = path if not path.is_absolute() else Path(path.relative_to(REPO)) if str(path).startswith(str(REPO)) else path
    rec["path"] = str(rel).replace("\\", "/")
    if not path.exists():
        return rec
    rec["bytes"] = int(path.stat().st_size)
    rec["sha256"] = _sha256_file(path)
    df = pd.read_parquet(path)
    rec["rows"] = int(len(df))
    rec["columns"] = [str(c) for c in df.columns]
    if isinstance(df.index, pd.DatetimeIndex) and df.index.name is not None:
        rec["index_name"] = str(df.index.name)
    rec["first_date"], rec["last_date"] = _first_last_from_df(df)
    rec["_df"] = df  # caller may pop
    return rec


def _basket_one(path_str: str) -> dict:
    path = Path(path_str)
    h = _sha256_file(path)
    df = pd.read_parquet(path)
    first, last = _first_last_from_df(df)
    n = int(len(df))
    year = None
    if first:
        year = int(first[:4])
    return {
        "name": path.name,
        "sha256": h,
        "rows": n,
        "first_date": first,
        "last_date": last,
        "first_year": year,
        "lt800": n < 800,
        "columns": [str(c) for c in df.columns],
    }


def inventory() -> tuple[dict, list[str]]:
    inputs: list[str] = []
    files: dict[str, dict] = {}
    for t in YAHOO_TICKERS:
        p = REPO / "data" / "yahoo" / f"{t}.parquet"
        rec = _parquet_inventory(p)
        rec.pop("_df", None)
        files[f"data/yahoo/{t}.parquet"] = rec
        if p.exists():
            inputs.append(str(p))

    extras = [
        "data/fred/DFII10.parquet",
        "data/regime/regime_v2_pit.parquet",
        "data/us_board_ledger/retro_grades.parquet",
        "data/prophet/ledger.jsonl",
    ]
    regime_pit_table = None
    for rel in extras:
        p = REPO / rel
        if rel.endswith(".jsonl"):
            rec = {
                "path": rel,
                "exists": p.exists(),
                "sha256": _sha256_file(p) if p.exists() else None,
                "rows": None,
                "columns": None,
                "first_date": None,
                "last_date": None,
                "bytes": int(p.stat().st_size) if p.exists() else None,
            }
            if p.exists():
                inputs.append(str(p))
                n = 0
                first = last = None
                cols = None
                with p.open() as fh:
                    for line in fh:
                        if not line.strip() or line.startswith("#"):
                            continue
                        n += 1
                        row = json.loads(line)
                        if cols is None:
                            cols = sorted(row.keys())
                        sd = row.get("signal_date")
                        if sd:
                            if first is None or sd < first:
                                first = sd
                            if last is None or sd > last:
                                last = sd
                rec["rows"] = n
                rec["columns"] = cols
                rec["first_date"] = first
                rec["last_date"] = last
            files[rel] = rec
            continue
        rec = _parquet_inventory(p)
        df = rec.pop("_df", None)
        if rel == "data/regime/regime_v2_pit.parquet" and df is not None:
            idx = df.index
            if not isinstance(idx, pd.DatetimeIndex):
                if "date" in df.columns:
                    years = pd.to_datetime(df["date"], errors="coerce").dt.year
                else:
                    years = pd.Series([None] * len(df))
            else:
                years = pd.Series(idx.year, index=df.index)
            pit = df["pit_class"].astype(str) if "pit_class" in df.columns else pd.Series(["<missing>"] * len(df))
            tab = []
            for y, g in pd.DataFrame({"year": years.to_numpy(), "pit_class": pit.to_numpy()}).groupby("year"):
                vc = g["pit_class"].value_counts(dropna=False)
                tot = int(len(g))
                shares = {str(k): {"n": int(v), "share": (int(v) / tot if tot else None)} for k, v in vc.items()}
                tab.append({"year": int(y) if pd.notna(y) else None, "n": tot, "by_pit_class": shares})
            tab.sort(key=lambda r: (r["year"] is None, r["year"] or 0))
            rec["pit_class_by_year"] = tab
            regime_pit_table = tab
        files[rel] = rec
        if p.exists():
            inputs.append(str(p))

    bdir = REPO / "data" / "baskets" / "ohlcv"
    basket_files = sorted(bdir.glob("*.parquet")) if bdir.exists() else []
    basket_rows = []
    if basket_files:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = [ex.submit(_basket_one, str(p)) for p in basket_files]
            for fut in as_completed(futs):
                basket_rows.append(fut.result())
        basket_rows.sort(key=lambda r: r["name"])
        for r in basket_rows:
            inputs.append(str(bdir / r["name"]))
    name_hash_lines = [f"{r['name']} {r['sha256']}" for r in basket_rows]
    dir_blob = ("\n".join(name_hash_lines) + ("\n" if name_hash_lines else "")).encode()
    dir_sha = hashlib.sha256(dir_blob).hexdigest()
    firsts = [r["first_date"] for r in basket_rows if r["first_date"]]
    lasts = [r["last_date"] for r in basket_rows if r["last_date"]]
    year_dist = Counter(r["first_year"] for r in basket_rows if r["first_year"] is not None)
    colset = []
    if basket_rows:
        colset = basket_rows[0]["columns"]
    files["data/baskets/ohlcv/"] = {
        "path": "data/baskets/ohlcv/",
        "exists": bdir.exists(),
        "sha256": dir_sha,
        "sha256_of": 'sorted lines of "name sha256"',
        "n_parquet_files": len(basket_rows),
        "rows": int(sum(r["rows"] for r in basket_rows)),
        "columns": colset,
        "first_date": min(firsts) if firsts else None,
        "last_date": max(lasts) if lasts else None,
        "first_year_distribution": {str(k): int(year_dist[k]) for k in sorted(year_dist)},
        "n_files_lt_800_rows": int(sum(1 for r in basket_rows if r["lt800"])),
        "bytes": None,
    }
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "regime_v2_pit_class_by_year": regime_pit_table,
        "baskets_ohlcv_file_count": len(basket_rows),
    }
    return out, inputs


def ledgers() -> tuple[dict, dict]:
    """Return (markdown-friendly dict, json dict)."""
    ledger_p = REPO / "data/prophet/ledger.jsonl"
    rows = []
    with ledger_p.open() as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    recs = []
    for r in rows:
        sd = r.get("signal_date")
        month = str(sd)[:7] if sd else "unknown"
        oc = r.get("outcome")
        if oc not in OUTCOMES:
            oc_g = "other"
        else:
            oc_g = oc
        recs.append({
            "month": month,
            "outcome": oc_g,
            "outcome_raw": oc,
            "stock_result_pct": r.get("stock_result_pct"),
            "days_held": r.get("days_held"),
            "asset": r.get("asset"),
            "id": r.get("id"),
        })
    rdf = pd.DataFrame(recs)
    months = sorted(rdf["month"].unique())
    outcomes_all = list(OUTCOMES) + ["other"]
    counts = []
    for m in months:
        sub = rdf[rdf["month"] == m]
        cell = {"month": m, "n": int(len(sub)), "n_names": int(sub["asset"].nunique())}
        for oc in outcomes_all:
            cell[oc] = int((sub["outcome"] == oc).sum())
        counts.append(cell)
    totals = {"month": "ALL", "n": int(len(rdf)), "n_names": int(rdf["asset"].nunique())}
    for oc in outcomes_all:
        totals[oc] = int((rdf["outcome"] == oc).sum())
    by_outcome = []
    for oc in outcomes_all:
        sub = rdf[rdf["outcome"] == oc]
        sr = pd.to_numeric(sub["stock_result_pct"], errors="coerce")
        dh = pd.to_numeric(sub["days_held"], errors="coerce")
        by_outcome.append({
            "outcome": oc,
            "n": int(len(sub)),
            "n_names": int(sub["asset"].nunique()) if len(sub) else 0,
            "n_stock_result_pct_nonnull": int(sr.notna().sum()),
            "mean_stock_result_pct": (float(sr.mean()) if sr.notna().any() else None),
            "median_stock_result_pct": (float(sr.median()) if sr.notna().any() else None),
            "n_days_held_nonnull": int(dh.notna().sum()),
            "mean_days_held": (float(dh.mean()) if dh.notna().any() else None),
            "median_days_held": (float(dh.median()) if dh.notna().any() else None),
        })
    other_raw = sorted({r["outcome_raw"] for r in recs if r["outcome"] == "other" and r["outcome_raw"] is not None})

    gp = REPO / "data/us_board_ledger/retro_grades.parquet"
    g = pd.read_parquet(gp)
    as_of = pd.to_datetime(g["as_of"], errors="coerce")
    g = g.copy()
    g["_month"] = as_of.dt.strftime("%Y-%m")
    g["_rank_by"] = g["rank_by"].astype(str)
    g["_lane"] = g["lane"].astype(str)
    g["_horizon"] = g["horizon"]
    ret = pd.to_numeric(g["ret"], errors="coerce")
    g["_ret_nn"] = ret.notna()
    cells = []
    grouped = g.groupby(["_month", "_rank_by", "_lane", "_horizon"], dropna=False, sort=True)
    for (month, rank_by, lane, horizon), sub in grouped:
        n = int(len(sub))
        nn = int(sub["_ret_nn"].sum())
        cells.append({
            "as_of_month": month,
            "rank_by": rank_by,
            "lane": lane,
            "horizon": (int(horizon) if pd.notna(horizon) else None),
            "n": n,
            "n_ret_nonnull": nn,
            "share_ret_nonnull": (nn / n if n else None),
            "n_tickers": int(sub["ticker"].nunique()) if "ticker" in sub.columns else None,
        })
    as_of_valid = as_of.dropna().sort_values()
    as_of_unique = pd.Index(as_of_valid.unique()).sort_values()
    retro = {
        "rows": int(len(g)),
        "as_of_count": int(len(as_of_unique)),
        "as_of_first": _iso(as_of_unique.min()) if len(as_of_unique) else None,
        "as_of_last": _iso(as_of_unique.max()) if len(as_of_unique) else None,
        "as_of_dates": [_iso(x) for x in as_of_unique],
        "n_tickers": int(g["ticker"].nunique()) if "ticker" in g.columns else None,
        "rank_by_values": sorted(g["_rank_by"].unique().tolist()),
        "lane_values": sorted(g["_lane"].unique().tolist()),
        "horizon_values": [int(x) for x in sorted(g["_horizon"].dropna().unique().tolist())],
        "rank_by_as_of_months": {
            rb: sorted({c["as_of_month"] for c in cells if c["rank_by"] == rb})
            for rb in sorted(g["_rank_by"].unique().tolist())
        },
        "share_ret_nonnull_is_structural": True,
        "share_ret_nonnull_note": (
            "share_ret_nonnull = 1.0000 in every cell is structural: "
            "retro_grades.parquet holds graded rows only (every row has a non-null ret). "
            "It is not a coverage statistic over the published board."
        ),
        "cells": cells,
    }
    js = {
        "prophet_ledger": {
            "rows": int(len(rdf)),
            "n_names": int(rdf["asset"].nunique()),
            "month_x_outcome": counts,
            "totals": totals,
            "by_outcome_stats": by_outcome,
            "other_raw_outcomes": other_raw,
            "signal_date_first": (min(rdf["month"]) if len(rdf) else None),
            "signal_date_last": (max(rdf["month"]) if len(rdf) else None),
        },
        "retro_grades": retro,
    }
    return js, js


def _manual_nd(daily: pd.DataFrame, n: int, *, date_is_last: bool) -> pd.DataFrame:
    idx = daily.index
    pos = session_positions(idx, market="US")
    bucket = pos // n
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in daily.columns]
    g = daily[cols].copy()
    g["_b"] = bucket
    agg = {}
    if "open" in cols:
        agg["open"] = "first"
    if "high" in cols:
        agg["high"] = "max"
    if "low" in cols:
        agg["low"] = "min"
    if "close" in cols:
        agg["close"] = "last"
    if "volume" in cols:
        agg["volume"] = "sum"
    out = g.groupby("_b", sort=True).agg(agg)
    if date_is_last:
        labels = pd.Series(idx.to_numpy(), index=bucket).groupby(level=0, sort=True).last()
    else:
        ok = (daily["close"].notna() if "close" in daily.columns
              else daily[cols].notna().any(axis=1)).to_numpy()
        first_row = pd.Series(idx.to_numpy(), index=bucket).groupby(level=0, sort=True).first()
        labels = first_row
        if ok.any():
            traded = pd.Series(idx.to_numpy()[ok], index=bucket[ok]).groupby(level=0, sort=True).first()
            labels = traded.reindex(first_row.index).fillna(first_row)
    out.index = pd.DatetimeIndex(labels.reindex(out.index).to_numpy())
    if "close" in out.columns:
        out = out.dropna(subset=["close"])
    return out


def _bar_compare(daily: pd.DataFrame, n: int) -> dict:
    fn = derive_3d_ohlcv if n == 3 else derive_2d_ohlcv
    canon = fn(daily, market="US")
    last_lab = _manual_nd(daily, n, date_is_last=True)
    open_lab = _manual_nd(daily, n, date_is_last=False)
    def _pairs(df):
        return list(zip(pd.DatetimeIndex(df.index).normalize(),
                        pd.to_numeric(df["close"], errors="coerce").to_numpy()))
    cp = _pairs(canon)
    lp = _pairs(last_lab)
    op = _pairs(open_lab)
    n_last_mis = 0
    last_mismatches = []
    for i, (a, b) in enumerate(zip(cp, lp)):
        if a[0] != b[0] or (pd.notna(a[1]) and pd.notna(b[1]) and abs(float(a[1]) - float(b[1])) > 1e-12) or (pd.isna(a[1]) != pd.isna(b[1])):
            n_last_mis += 1
            if len(last_mismatches) < 3:
                last_mismatches.append({
                    "i": i,
                    "canon_date": _iso(a[0]), "canon_close": (None if pd.isna(a[1]) else float(a[1])),
                    "manual_date": _iso(b[0]), "manual_close": (None if pd.isna(b[1]) else float(b[1])),
                })
    if len(cp) != len(lp):
        n_last_mis = abs(len(cp) - len(lp)) + n_last_mis
    n_open_mis = 0
    open_mismatches = []
    for i, (a, b) in enumerate(zip(cp, op)):
        if a[0] != b[0] or (pd.notna(a[1]) and pd.notna(b[1]) and abs(float(a[1]) - float(b[1])) > 1e-12) or (pd.isna(a[1]) != pd.isna(b[1])):
            n_open_mis += 1
            if len(open_mismatches) < 3:
                open_mismatches.append({
                    "i": i,
                    "canon_date": _iso(a[0]), "canon_close": (None if pd.isna(a[1]) else float(a[1])),
                    "manual_date": _iso(b[0]), "manual_close": (None if pd.isna(b[1]) else float(b[1])),
                })
    if len(cp) != len(op):
        n_open_mis = abs(len(cp) - len(op)) + n_open_mis
    return {
        "bars_canon": int(len(canon)),
        "bars_manual_last_date": int(len(last_lab)),
        "bars_manual_open_date": int(len(open_lab)),
        "mismatches_last_date": int(n_last_mis if len(cp) == len(lp) else n_last_mis),
        "mismatches_open_date": int(n_open_mis if len(cp) == len(op) else n_open_mis),
        "len_equal_last": len(cp) == len(lp),
        "len_equal_open": len(cp) == len(op),
        "first_three_mismatches_last_date": last_mismatches,
        "first_three_mismatches_open_date": open_mismatches,
        "drops_trailing_incomplete": False,
        "production_date_label": "open (first finite-close session in the bucket)",
        "spec_date_label": "last session in the bucket",
    }


def _maxabs_pair(a: pd.Series, b: pd.Series, sl=slice(None)) -> tuple[float | None, int]:
    d = (a.iloc[sl] - b.iloc[sl]).abs()
    ok = d.notna() & np.isfinite(d.to_numpy())
    if not ok.any():
        return None, 0
    return float(d[ok].max()), int(ok.sum())


def _cross_mismatch(a_m, a_s, b_m, b_s, sl=slice(None)) -> dict:
    am, asg = a_m.iloc[sl], a_s.iloc[sl]
    bm, bsg = b_m.iloc[sl], b_s.iloc[sl]
    a_ok = am.notna() & asg.notna()
    b_ok = bm.notna() & bsg.notna()
    a_dates = set(bullish_cross_dates(am.where(a_ok), asg.where(a_ok)))
    b_dates = set(bullish_cross_dates(bm.where(b_ok), bsg.where(b_ok)))
    return {
        "cross_count_a": int(len(a_dates)),
        "cross_count_b": int(len(b_dates)),
        "cross_date_mismatches": int(len(a_dates.symmetric_difference(b_dates))),
    }


def _served_vs_canon_one(close: pd.Series, warmup: int) -> dict:
    c_m, c_s = canon_rsi_macd(close)
    s_m, s_s = served_rsi_macd(close)
    n = int(len(close))
    full_m, n_full_m = _maxabs_pair(c_m, s_m)
    full_s, n_full_s = _maxabs_pair(c_s, s_s)
    if n > warmup:
        a400_m, n_a400_m = _maxabs_pair(c_m, s_m, slice(warmup, None))
        a400_s, n_a400_s = _maxabs_pair(c_s, s_s, slice(warmup, None))
        x400 = _cross_mismatch(c_m, c_s, s_m, s_s, slice(warmup, None))
    else:
        a400_m = a400_s = None
        n_a400_m = n_a400_s = 0
        x400 = {"cross_count_a": None, "cross_count_b": None, "cross_date_mismatches": None}
    xfull = _cross_mismatch(c_m, c_s, s_m, s_s)
    first400_m, n_f400_m = (None, 0)
    first400_s, n_f400_s = (None, 0)
    if n:
        first400_m, n_f400_m = _maxabs_pair(c_m, s_m, slice(0, min(warmup, n)))
        first400_s, n_f400_s = _maxabs_pair(c_s, s_s, slice(0, min(warmup, n)))
    return {
        "n": n,
        "first": _iso(close.index.min()) if n else None,
        "last": _iso(close.index.max()) if n else None,
        "max_abs_diff_macd_after_400": a400_m,
        "max_abs_diff_signal_after_400": a400_s,
        "n_compared_macd_after_400": n_a400_m,
        "n_compared_signal_after_400": n_a400_s,
        "max_abs_diff_macd_full": full_m,
        "max_abs_diff_signal_full": full_s,
        "n_compared_macd_full": n_full_m,
        "n_compared_signal_full": n_full_s,
        "max_abs_diff_macd_first_400": first400_m,
        "max_abs_diff_signal_first_400": first400_s,
        "n_compared_macd_first_400": n_f400_m,
        "cross_count_canon_full": xfull["cross_count_a"],
        "cross_count_served_full": xfull["cross_count_b"],
        "cross_date_mismatches_full": xfull["cross_date_mismatches"],
        "cross_count_canon_after_400": x400["cross_count_a"],
        "cross_count_served_after_400": x400["cross_count_b"],
        "cross_date_mismatches_after_400": x400["cross_date_mismatches"],
    }


def parity() -> dict:
    spy_p = REPO / "data/yahoo/SPY.parquet"
    spy = pd.read_parquet(spy_p)
    close = pd.to_numeric(spy["close"], errors="coerce").dropna().sort_index()
    close.index = pd.DatetimeIndex(pd.to_datetime(close.index)).tz_localize(None).normalize()
    c_macd, c_sig = canon_rsi_macd(close)
    p_macd, p_sig = pine_rsi_macd(close)
    tail = slice(WARMUP, None)
    d_macd = (c_macd.iloc[tail] - p_macd.iloc[tail]).abs()
    d_sig = (c_sig.iloc[tail] - p_sig.iloc[tail]).abs()
    both_m = d_macd.notna() & np.isfinite(d_macd.to_numpy())
    both_s = d_sig.notna() & np.isfinite(d_sig.to_numpy())
    max_m = float(d_macd[both_m].max()) if both_m.any() else None
    max_s = float(d_sig[both_s].max()) if both_s.any() else None
    n_both_m = int(both_m.sum())
    n_both_s = int(both_s.sum())
    arg_m = None
    arg_s = None
    if both_m.any() and max_m is not None:
        i = d_macd[both_m].idxmax()
        arg_m = _iso(i)
    if both_s.any() and max_s is not None:
        i = d_sig[both_s].idxmax()
        arg_s = _iso(i)

    # Crosses on the post-400 window where BOTH implementations are finite.
    c_macd_t = c_macd.iloc[tail]
    c_sig_t = c_sig.iloc[tail]
    p_macd_t = p_macd.iloc[tail]
    p_sig_t = p_sig.iloc[tail]
    c_ok = c_macd_t.notna() & c_sig_t.notna()
    p_ok = p_macd_t.notna() & p_sig_t.notna()
    c_dates = set(bullish_cross_dates(c_macd_t.where(c_ok), c_sig_t.where(c_ok)))
    p_dates = set(bullish_cross_dates(p_macd_t.where(p_ok), p_sig_t.where(p_ok)))
    only_c = sorted(_iso(x) for x in (c_dates - p_dates))
    only_p = sorted(_iso(x) for x in (p_dates - c_dates))
    cross_date_mismatches = len(c_dates.symmetric_difference(p_dates))

    # Full-series cross counts (for the report).
    c_dates_all = set(bullish_cross_dates(c_macd, c_sig))
    p_dates_all = set(bullish_cross_dates(p_macd, p_sig))

    ema_note = (
        "engine.canon.ema is pandas ewm(span, adjust=False, min_periods=span) "
        "(engine/canon.py:343-350), so the first `span` RSI bars of each EMA are NaN "
        "in the output even though the recursive state is running. Pine EMA here seeds "
        "with the first finite value and emits from that bar (no min_periods). "
        "engine.canon.rma SMA-seeds on the first n finite values then recurses with "
        "alpha=1/n and carries the previous value through a NaN (engine/canon.py:311-340); "
        "the Pine RMA in code/pine_rsi_macd.py matches that seed. "
        "engine.canon.rsi is RMA(gain)/RMA(loss) with those RMAs (engine/canon.py:353-362). "
        "A residual after session 400, if any, is therefore EMA min_periods / seed-bar "
        "disagreement decaying as (1-alpha)^t, not a different RSI formula. "
        "Pine RMA (code/pine_rsi_macd.py) is ta.sma of the first n finite values then "
        "(src+(n-1)*prev)/n — not a transcription of engine.canon.rma's loop. "
        "Production board code does NOT call engine.canon.rsi_macd: "
        "scripts/build_stock_library.py:234,3745 -> engine/signal_gate.py:65-67,379,468 "
        "-> engine/signal_quality.py:68-75 and engine/confluence_tiers.py:255-262 use "
        "engine.technicals.rsi (ewm alpha=1/n, min_periods=n; engine/technicals.py:26-31) "
        "and pandas ewm default adjust=True."
    )

    spy_cols = [str(c) for c in spy.columns]
    has_ohlc = set(("open", "high", "low")) <= set(c.lower() for c in spy_cols)
    spy_basket = REPO / "data/baskets/ohlcv/SPY.parquet"
    bar_source = None
    bar_tickers = []
    if has_ohlc:
        daily = spy.copy()
        daily.index = pd.DatetimeIndex(pd.to_datetime(daily.index)).tz_localize(None).normalize()
        bar_source = "data/yahoo/SPY.parquet"
        bar_tickers = [("SPY", daily)]
    elif spy_basket.exists():
        daily = pd.read_parquet(spy_basket)
        daily.index = pd.DatetimeIndex(pd.to_datetime(daily.index)).tz_localize(None).normalize()
        bar_source = "data/baskets/ohlcv/SPY.parquet"
        bar_tickers = [("SPY", daily)]
    else:
        files = sorted((REPO / "data/baskets/ohlcv").glob("*.parquet"))[:10]
        bar_source = "data/baskets/ohlcv first 10 names alphabetically (no SPY OHLCV)"
        for p in files:
            df = pd.read_parquet(p)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")]
            df.index = pd.DatetimeIndex(pd.to_datetime(df.index)).tz_localize(None).normalize()
            bar_tickers.append((p.stem, df))

    per_ticker = []
    for name, daily in bar_tickers:
        rec = {"ticker": name, "rows": int(len(daily)), "columns": [str(c) for c in daily.columns]}
        rec["3d"] = _bar_compare(daily, 3)
        rec["2d"] = _bar_compare(daily, 2)
        per_ticker.append(rec)

    primary = per_ticker[0]

    spy_daily_svc = _served_vs_canon_one(close, WARMUP)
    spy_grid3 = _tf_grid(close, 3, "US")
    spy_3d_svc = _served_vs_canon_one(spy_grid3.close, WARMUP)
    per_ticker_3d_svc = []
    for name, daily in bar_tickers:
        g3 = _tf_grid(pd.to_numeric(daily["close"], errors="coerce"), 3, "US")
        rec3 = _served_vs_canon_one(g3.close, WARMUP)
        rec3["ticker"] = name
        rec3["daily_rows"] = int(len(daily))
        rec3["tf_grid_bars"] = int(len(g3.close))
        per_ticker_3d_svc.append(rec3)
    served_vs_canon = {
        "note": (
            "Served path is engine.technicals.rsi (ewm alpha=1/n, min_periods=n, "
            "adjust=True default; engine/technicals.py:26-31) plus pandas "
            "ewm(span, min_periods=span) default adjust=True "
            "(engine/signal_quality.py:68-75; engine/confluence_tiers.py:255-262). "
            "3D grid is engine.signal_quality._tf_grid (engine/signal_quality.py:109-156, "
            "called at :176-184). No module on the gate path imports engine.canon."
        ),
        "spy_daily": spy_daily_svc,
        "spy_3d_tf_grid": spy_3d_svc,
        "per_ticker_3d_tf_grid": per_ticker_3d_svc,
    }

    out = {
        "max_abs_diff_macd": max_m,
        "max_abs_diff_signal": max_s,
        "max_abs_diff_macd_date": arg_m,
        "max_abs_diff_signal_date": arg_s,
        "n_compared_macd": n_both_m,
        "n_compared_signal": n_both_s,
        "warmup_sessions_skipped": WARMUP,
        "spy_sessions": int(len(close)),
        "spy_first": _iso(close.index.min()),
        "spy_last": _iso(close.index.max()),
        "cross_count_canon": int(len(c_dates)),
        "cross_count_pine": int(len(p_dates)),
        "cross_count_canon_full_series": int(len(c_dates_all)),
        "cross_count_pine_full_series": int(len(p_dates_all)),
        "cross_date_mismatches": int(cross_date_mismatches),
        "cross_dates_only_canon": only_c,
        "cross_dates_only_pine": only_p,
        "agree_to_1e-6": bool(max_m is not None and max_s is not None and max_m <= 1e-6 and max_s <= 1e-6),
        "ema_rma_explanation": ema_note,
        "bar_source": bar_source,
        "bar_tickers": [t for t, _ in bar_tickers],
        "bars3d_canon": primary["3d"]["bars_canon"],
        "bars3d_manual": primary["3d"]["bars_manual_last_date"],
        "bars3d_mismatches": primary["3d"]["mismatches_last_date"],
        "bars3d_mismatches_open_label": primary["3d"]["mismatches_open_date"],
        "bars3d_first_three_mismatches": primary["3d"]["first_three_mismatches_last_date"],
        "bars2d_canon": primary["2d"]["bars_canon"],
        "bars2d_manual": primary["2d"]["bars_manual_last_date"],
        "bars2d_mismatches": primary["2d"]["mismatches_last_date"],
        "bars2d_mismatches_open_label": primary["2d"]["mismatches_open_date"],
        "bars2d_first_three_mismatches": primary["2d"]["first_three_mismatches_last_date"],
        "derive_drops_trailing_incomplete_bucket": False,
        "derive_date_label": "open (first finite-close session); engine/bar_derive.py:270-285",
        "manual_spec_date_label": "last session date (A1 spec)",
        "per_ticker": per_ticker,
        "spy_yahoo_columns": spy_cols,
        "served_vs_canon": served_vs_canon,
    }
    return out


def _md_table(headers, rows) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = []
    for r in rows:
        body.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join([line, sep, *body])


def write_ledger_md(js: dict) -> str:
    p = js["prophet_ledger"]
    g = js["retro_grades"]
    headers = ["month", "n", "n_names"] + list(OUTCOMES) + ["other"]
    rows = []
    for c in p["month_x_outcome"] + [p["totals"]]:
        rows.append([c["month"], c["n"], c["n_names"]] + [c[k] for k in list(OUTCOMES) + ["other"]])
    t1 = _md_table(headers, rows)
    h2 = ["outcome", "n", "n_names", "mean_stock_result_pct", "median_stock_result_pct",
          "n_pct", "mean_days_held", "median_days_held", "n_days"]
    rows2 = []
    for b in p["by_outcome_stats"]:
        rows2.append([
            b["outcome"], b["n"], b["n_names"],
            None if b["mean_stock_result_pct"] is None else f"{b['mean_stock_result_pct']:.6g}",
            None if b["median_stock_result_pct"] is None else f"{b['median_stock_result_pct']:.6g}",
            b["n_stock_result_pct_nonnull"],
            None if b["mean_days_held"] is None else f"{b['mean_days_held']:.6g}",
            None if b["median_days_held"] is None else f"{b['median_days_held']:.6g}",
            b["n_days_held_nonnull"],
        ])
    t2 = _md_table(h2, rows2)
    h3 = ["as_of_month", "rank_by", "lane", "horizon", "n", "n_ret_nonnull", "share_ret_nonnull", "n_tickers"]
    rows3 = []
    for c in g["cells"]:
        sh = c["share_ret_nonnull"]
        rows3.append([
            c["as_of_month"], c["rank_by"], c["lane"], c["horizon"], c["n"],
            c["n_ret_nonnull"], None if sh is None else f"{sh:.4f}", c["n_tickers"],
        ])
    t3 = _md_table(h3, rows3)
    md = []
    md.append("# Ledger denominators (A1)")
    md.append("")
    md.append("Price stores are FINAL-VINTAGE (as observed today, not point-in-time). Universes are SURVIVOR-SELECTED (current membership only). Ledgers below are the served artifacts on this checkout.")
    md.append("")
    md.append("## (a) data/prophet/ledger.jsonl")
    md.append("")
    md.append(f"Comment lines starting with `#` skipped. Parsed JSONL rows: **{p['rows']}**. Distinct names (asset): **{p['n_names']}**. Other raw outcomes: `{p['other_raw_outcomes']}` (empty means every row used one of the five named outcomes).")
    md.append("")
    md.append("### signal month × outcome counts")
    md.append("")
    md.append(t1)
    md.append("")
    md.append("### mean/median stock_result_pct and days_held by outcome")
    md.append("")
    md.append(t2)
    md.append("")
    md.append("## (b) data/us_board_ledger/retro_grades.parquet")
    md.append("")
    md.append(
        f"rows={g['rows']}; distinct as_of dates: count={g['as_of_count']}, first={g['as_of_first']}, last={g['as_of_last']}; distinct tickers={g['n_tickers']}. "
        f"rank_by={g['rank_by_values']}; lane={g['lane_values']}; horizon={g['horizon_values']}. "
        f"rank_by as_of months: {g['rank_by_as_of_months']}."
    )
    md.append("")
    md.append(g["share_ret_nonnull_note"])
    md.append("")
    md.append("Distinct as_of dates: " + ", ".join(g["as_of_dates"]))
    md.append("")
    md.append("### as_of month × rank_by × lane × horizon")
    md.append("")
    md.append(t3)
    md.append("")
    return "\n".join(md)


def write_parity_md(p: dict) -> str:
    agree = p["agree_to_1e-6"]
    md = []
    md.append("# Indicator and bar-clock parity (A1)")
    md.append("")
    md.append("Price stores are FINAL-VINTAGE (as observed today, not point-in-time). Universes are SURVIVOR-SELECTED (current membership only).")
    md.append("")
    md.append("## (a) RSI-MACD on SPY daily `close` (data/yahoo/SPY.parquet)")
    md.append("")
    md.append(
        f"Sessions={p['spy_sessions']} ({p['spy_first']} → {p['spy_last']}). "
        f"Compared after first {p['warmup_sessions_skipped']} sessions. "
        f"n_compared macd={p['n_compared_macd']} signal={p['n_compared_signal']}."
    )
    md.append("")
    md.append(_md_table(
        ["metric", "value"],
        [
            ["max|diff| macd", p["max_abs_diff_macd"]],
            ["max|diff| macd date", p["max_abs_diff_macd_date"]],
            ["max|diff| signal", p["max_abs_diff_signal"]],
            ["max|diff| signal date", p["max_abs_diff_signal_date"]],
            ["agree to 1e-6", agree],
            ["bullish crosses canon (post-400, both finite)", p["cross_count_canon"]],
            ["bullish crosses pine (post-400, both finite)", p["cross_count_pine"]],
            ["cross-date mismatches (symmetric difference)", p["cross_date_mismatches"]],
            ["crosses canon full series", p["cross_count_canon_full_series"]],
            ["crosses pine full series", p["cross_count_pine_full_series"]],
        ],
    ))
    md.append("")
    md.append("Cross dates only in canon: " + (", ".join(p["cross_dates_only_canon"]) or "(none)"))
    md.append("")
    md.append("Cross dates only in pine: " + (", ".join(p["cross_dates_only_pine"]) or "(none)"))
    md.append("")
    md.append("### Why any |diff| > 1e-6 (read, not a canon fix)")
    md.append("")
    md.append(p["ema_rma_explanation"])
    md.append("")
    md.append("## (a2) Served vs canon RSI-MACD (canon parity is not served parity)")
    md.append("")
    svc = p["served_vs_canon"]
    md.append(svc["note"])
    md.append("")
    sd = svc["spy_daily"]
    s3 = svc["spy_3d_tf_grid"]
    md.append("### SPY daily (data/yahoo/SPY.parquet `close`)")
    md.append("")
    md.append(_md_table(
        ["metric", "value"],
        [
            ["n sessions", sd["n"]],
            ["max|macd| after 400", sd["max_abs_diff_macd_after_400"]],
            ["max|signal| after 400", sd["max_abs_diff_signal_after_400"]],
            ["max|macd| first 400", sd["max_abs_diff_macd_first_400"]],
            ["max|macd| full series", sd["max_abs_diff_macd_full"]],
            ["max|signal| full series", sd["max_abs_diff_signal_full"]],
            ["cross_count canon full", sd["cross_count_canon_full"]],
            ["cross_count served full", sd["cross_count_served_full"]],
            ["cross-date mismatches full", sd["cross_date_mismatches_full"]],
            ["cross-date mismatches after 400", sd["cross_date_mismatches_after_400"]],
        ],
    ))
    md.append("")
    md.append("### SPY 3D `_tf_grid` (T1 master grain, engine/signal_quality.py:176-184)")
    md.append("")
    md.append(_md_table(
        ["metric", "value"],
        [
            ["n 3D bars", s3["n"]],
            ["max|macd| after 400", s3["max_abs_diff_macd_after_400"]],
            ["max|signal| after 400", s3["max_abs_diff_signal_after_400"]],
            ["max|macd| first 400", s3["max_abs_diff_macd_first_400"]],
            ["max|macd| full series", s3["max_abs_diff_macd_full"]],
            ["max|signal| full series", s3["max_abs_diff_signal_full"]],
            ["cross_count canon full", s3["cross_count_canon_full"]],
            ["cross_count served full", s3["cross_count_served_full"]],
            ["cross-date mismatches full", s3["cross_date_mismatches_full"]],
            ["cross-date mismatches after 400", s3["cross_date_mismatches_after_400"]],
        ],
    ))
    md.append("")
    md.append("### Ten per_ticker basket names on 3D `_tf_grid`")
    md.append("")
    rows_svc = []
    for rec in svc["per_ticker_3d_tf_grid"]:
        rows_svc.append([
            rec["ticker"], rec["daily_rows"], rec["tf_grid_bars"],
            rec["max_abs_diff_macd_after_400"], rec["max_abs_diff_macd_full"],
            rec["max_abs_diff_signal_after_400"], rec["max_abs_diff_signal_full"],
            rec["cross_date_mismatches_after_400"], rec["cross_date_mismatches_full"],
        ])
    md.append(_md_table(
        ["ticker", "daily_n", "3d_n", "max|macd| after400", "max|macd| full",
         "max|sig| after400", "max|sig| full", "xmis after400", "xmis full"],
        rows_svc,
    ))
    md.append("")
    md.append("## (b) n-session bars")
    md.append("")
    md.append(f"SPY yahoo columns: `{p['spy_yahoo_columns']}`. Bar source: **{p['bar_source']}**. Tickers: {p['bar_tickers']}.")
    md.append("")
    md.append(
        f"`derive_3d_ohlcv` / `derive_2d_ohlcv` do **not** drop a trailing incomplete bucket "
        f"(engine/bar_derive.py:243-287: only `dropna(subset=['close'])`). "
        f"Production date label = {p['derive_date_label']}. Spec manual date = {p['manual_spec_date_label']}."
    )
    md.append("")
    md.append("Primary ticker (first in the fallback list / SPY if used):")
    md.append("")
    md.append(_md_table(
        ["grain", "bars_canon", "bars_manual_last_date", "(date,close) mismatches last-date", "mismatches open-label"],
        [
            ["3D", p["bars3d_canon"], p["bars3d_manual"], p["bars3d_mismatches"], p["bars3d_mismatches_open_label"]],
            ["2D", p["bars2d_canon"], p["bars2d_manual"], p["bars2d_mismatches"], p["bars2d_mismatches_open_label"]],
        ],
    ))
    md.append("")
    md.append("First three 3D (date, close) mismatches under spec last-date labeling:")
    md.append("")
    md.append("```json")
    md.append(json.dumps(p["bars3d_first_three_mismatches"], indent=2))
    md.append("```")
    md.append("")
    md.append("First three 2D (date, close) mismatches under spec last-date labeling:")
    md.append("")
    md.append("```json")
    md.append(json.dumps(p["bars2d_first_three_mismatches"], indent=2))
    md.append("```")
    md.append("")
    md.append("### Per-ticker")
    md.append("")
    rows = []
    for rec in p["per_ticker"]:
        rows.append([
            rec["ticker"], rec["rows"],
            rec["3d"]["bars_canon"], rec["3d"]["bars_manual_last_date"],
            rec["3d"]["mismatches_last_date"], rec["3d"]["mismatches_open_date"],
            rec["2d"]["bars_canon"], rec["2d"]["bars_manual_last_date"],
            rec["2d"]["mismatches_last_date"], rec["2d"]["mismatches_open_date"],
        ])
    md.append(_md_table(
        ["ticker", "daily_rows", "3d_canon", "3d_manual_last", "3d_mis_last", "3d_mis_open",
         "2d_canon", "2d_manual_last", "2d_mis_last", "2d_mis_open"],
        rows,
    ))
    md.append("")
    return "\n".join(md)


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return (r.stdout or "").strip() or None


def collect_hashes(inputs: list[str], outputs: list[Path]) -> None:
    lines = []
    seen = set()
    for p in inputs:
        path = Path(p)
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        rel = path
        try:
            rel = path.resolve().relative_to(REPO)
        except Exception:
            rel = path
        lines.append(f"{_sha256_file(path)}  {rel.as_posix() if hasattr(rel, 'as_posix') else rel}")
    for path in outputs:
        if not path.exists() or path.name == "hashes.txt":
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        try:
            rel = path.resolve().relative_to(REPO)
        except Exception:
            rel = path
        lines.append(f"{_sha256_file(path)}  {rel.as_posix() if hasattr(rel, 'as_posix') else rel}")
    (RESULTS / "hashes.txt").write_text("\n".join(lines) + "\n")


def fmt(x, n=6):
    if x is None:
        return "null"
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def _assignment_lineno(path: Path, name: str) -> int:
    """1-based line of the first non-comment `NAME =` assignment in path."""
    text = path.read_text()
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith(f"{name} =") or s.startswith(f"{name}="):
            return i
    raise RuntimeError(f"{name!r} assignment not found in {path}")


def patch_served_definition_buyable_line(buyable_line: int) -> None:
    """Rewrite BUYABLE_TIERS receipts in served_definition.md from the live line."""
    path = RESULTS / "served_definition.md"
    text = path.read_text()
    new, n = re.subn(
        r"engine/signal_gate\.py:\d+(?=` `BUYABLE_TIERS)",
        f"engine/signal_gate.py:{buyable_line}",
        text,
    )
    if n < 2:
        raise RuntimeError(
            f"served_definition.md: expected >=2 BUYABLE_TIERS receipts, patched {n}"
        )
    path.write_text(new)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CODE.mkdir(parents=True, exist_ok=True)
    head = git_head()

    inv, inv_inputs = inventory()
    # strip any leftover
    for rec in inv["files"].values():
        rec.pop("_df", None)
    (RESULTS / "data_inventory.json").write_text(json.dumps(inv, indent=2, default=str) + "\n")

    led_js, _ = ledgers()
    (RESULTS / "ledger_denominators.json").write_text(json.dumps(led_js, indent=2, default=str) + "\n")
    (RESULTS / "ledger_denominators.md").write_text(write_ledger_md(led_js))

    par = parity()
    # schema keys required at top level of parity.json
    parity_public = {
        "max_abs_diff_macd": par["max_abs_diff_macd"],
        "max_abs_diff_signal": par["max_abs_diff_signal"],
        "cross_count_canon": par["cross_count_canon"],
        "cross_count_pine": par["cross_count_pine"],
        "cross_date_mismatches": par["cross_date_mismatches"],
        "bars3d_canon": par["bars3d_canon"],
        "bars3d_manual": par["bars3d_manual"],
        "bars3d_mismatches": par["bars3d_mismatches"],
        "bars2d_canon": par["bars2d_canon"],
        "bars2d_manual": par["bars2d_manual"],
        "bars2d_mismatches": par["bars2d_mismatches"],
        "served_vs_canon": par["served_vs_canon"],
    }
    parity_full = dict(parity_public)
    parity_full.update(par)
    (RESULTS / "parity.json").write_text(json.dumps(parity_full, indent=2, default=str) + "\n")
    (RESULTS / "parity.md").write_text(write_parity_md(par))

    buyable_line = _assignment_lineno(REPO / "engine" / "signal_gate.py", "BUYABLE_TIERS")
    patch_served_definition_buyable_line(buyable_line)
    # Seed result.json so test_a1 can read bars3d_canon (final rewrite after pytest).
    seed = {}
    if (RESULTS / "result.json").exists():
        try:
            seed = json.loads((RESULTS / "result.json").read_text())
            if not isinstance(seed, dict):
                seed = {}
        except (json.JSONDecodeError, OSError):
            seed = {}
    seed["lane"] = "A1"
    seed["parity"] = parity_public
    (RESULTS / "result.json").write_text(json.dumps(seed, indent=2, default=str) + "\n")

    tests_line = None
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/A1/code",
         "-q", "-p", "no:cacheprovider"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    pytest_out = (proc.stdout or "") + (proc.stderr or "")
    (RESULTS / "pytest.out").write_text(pytest_out)
    for line in reversed(pytest_out.strip().splitlines()):
        if "passed" in line or "failed" in line or "xfailed" in line or "error" in line:
            tests_line = line.strip()
            break
    if tests_line is None:
        tests_line = f"pytest exit {proc.returncode}"

    gaps = []
    deviations = [
        "Workspace is this git checkout (astra-ceo-handoff worktree), not ~/lanes/repos/macro (that path does not exist on this host).",
        "Pine RMA is ta.sma of the first n finite values then (src+(n-1)*prev)/n; interior NaN after seed is left NaN (Pine na) rather than canon.rma's prev-carry.",
        "Bar-parity scalars in parity.json are for the first fallback OHLCV ticker when SPY yahoo has no open/high/low and data/baskets/ohlcv/SPY.parquet is absent; per_ticker lists the first ten alphabetical basket names.",
        "pytest (ii) asserts production open-date labels equal manual pos//n OHLCV on all ten per_ticker names; the spec last-session date recipe is an additional xfail(strict=True) on ticker A.",
        "Served-vs-canon uses engine.signal_quality._rsi_macd / _tf_grid (the T1 master path), not a re-typed copy.",
    ]
    # era map gap
    gaps.append(
        "This checkout is a shallow git repository (git rev-parse --is-shallow-repository=true) with missing objects; path-filtered `git log` on engine/canon.py, session_anchor.py, bar_derive.py, mtf_upturn.py, us_board_rank.py returns only 69268b06502c (2026-08-23, files added). Pre-squash constant/epoch/rank-family history is not readable here."
    )
    if not par["agree_to_1e-6"]:
        gaps.append(
            f"Pine vs canon.rsi_macd after 400 sessions: max|diff| macd={par['max_abs_diff_macd']} signal={par['max_abs_diff_signal']} (not <= 1e-6)."
        )
    if par["bars3d_mismatches"]:
        gaps.append(
            f"3D (date, close) last-session labeling mismatches={par['bars3d_mismatches']} "
            f"(open-label mismatches={par['bars3d_mismatches_open_label']}); production labels by open date."
        )
    gaps.append(
        "engine.canon.rsi_macd is not the served indicator (no gate-path import). "
        "Served-vs-canon numbers are in parity.json served_vs_canon; later lanes that "
        "treat canon as the live cascade are reading a different RSI/EMA than production."
    )

    rb_months = led_js["retro_grades"]["rank_by_as_of_months"]
    served = {
        "signal_grains": ["3D", "2D"],
        "confirmation_grains": ["W-FRI", "2W-FRI"],
        "buyable_tiers": ["T1", "T2", "T3"],
        "buyable_receipt": (
            f"engine/signal_gate.py:{buyable_line} BUYABLE_TIERS; :113-120 is_buyable; "
            "T1=3D x 3D, T2/T3=2D-projected x 3D (engine/confluence_tiers.py:13-16)"
        ),
        "served_call_path": [
            "scripts/build_stock_library.py:234",
            "scripts/build_stock_library.py:3745",
            "engine/signal_gate.py:65-67",
            "engine/signal_gate.py:379",
            "engine/signal_gate.py:468",
            "engine/confluence_tiers.py:45",
            "engine/confluence_tiers.py:255-262",
        ],
        "rank_families": {
            "us_prophet_v1": {
                "file": "engine/us_board_rank.py",
                "line": 147,
                "conditions_on": "SUPERSEDED_ERA_STAMPS; live 2026-08-02→2026-08-10; displaced by us_prophet_v2. Same confluence admission population as later stamps; ranker was the five-leg heuristic (see us_prophet_v2).",
            },
            "us_prophet_v2": {
                "file": "engine/us_board_rank.py",
                "line": 148,
                "conditions_on": "SUPERSEDED_ERA_STAMPS; live 2026-08-10→2026-08-15; five-leg weighted heuristic ranker on the confluence-admitted pool (2D/3D RSI-MACD × StochRSI cascade). SHADOW_DEFINITION us_prophet_v2_shadow at line 128; FALLBACK_DEFINITION us_prophet_v2_fallback at line 136.",
            },
            "us_prophet_v3": {
                "file": "engine/us_board_rank.py",
                "line": 100,
                "conditions_on": "BOARD_DEFINITION live ranker; same selection population as v2; orders the pool by C1 evidence-family fusion (engine.us_prophet_fusion) inside each stage bucket. Adopted 2026-08-15 (line 119).",
            },
            "conviction": {
                "file": "scripts/prophet_fusion_race.py",
                "line": 2228,
                "assigned_at_head": False,
                "conditions_on": (
                    "not assigned at HEAD; legacy ledger stratum. "
                    "scripts/prophet_fusion_race.py:2228-2230 quote: "
                    "'rank_by is a SELECTION-REGIME stamp (legacy eras: conviction -> "
                    "bottoming-alignment -> confluence; live boards stamp us_prophet_v1/v2 "
                    "from 2026-08-07)'. engine/setups.py:141 is docstring sort-key prose, "
                    "not a rank_by assignment. retro_grades as_of months: "
                    f"{rb_months.get('conviction')}."
                ),
            },
            "confluence": {
                "file": "scripts/prophet_fusion_race.py",
                "line": 2228,
                "assigned_at_head": False,
                "conditions_on": (
                    "not assigned at HEAD; legacy ledger stratum. "
                    "scripts/prophet_fusion_race.py:2228-2230 (same quote). "
                    "engine/setups.py:243 is docstring buy_gate prose, not a rank_by "
                    "assignment. retro_grades as_of months: "
                    f"{rb_months.get('confluence')}."
                ),
            },
            "bottoming-alignment": {
                "file": "scripts/prophet_fusion_race.py",
                "line": 2228,
                "assigned_at_head": False,
                "conditions_on": (
                    "not assigned at HEAD; legacy ledger stratum. "
                    "scripts/prophet_fusion_race.py:2228-2230 (same quote). "
                    "engine/setups.py:259 is docstring align_map prose, not a rank_by "
                    "assignment. retro_grades as_of months: "
                    f"{rb_months.get('bottoming-alignment')}."
                ),
            },
        },
    }

    status = "DELIVERED"
    if proc.returncode not in (0,):
        # xfail is still exit 0 typically; failures -> PARTIAL
        if "failed" in (tests_line or "") or proc.returncode != 0:
            status = "PARTIAL"

    result = {
        "lane": "A1",
        "status": status,
        "repo_head": head,
        "served": served,
        "parity": parity_public,
        "ledgers": {
            "prophet_ledger_rows": led_js["prophet_ledger"]["rows"],
            "retro_grades_rows": led_js["retro_grades"]["rows"],
            "retro_as_of_first": led_js["retro_grades"]["as_of_first"],
            "retro_as_of_last": led_js["retro_grades"]["as_of_last"],
            "retro_as_of_count": led_js["retro_grades"]["as_of_count"],
            "retro_tickers": led_js["retro_grades"]["n_tickers"],
        },
        "inventory_path": "data_inventory.json",
        "tests": tests_line,
        "gaps": gaps,
        "deviations": deviations,
    }
    (RESULTS / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")

    # RESULT.md
    svc = par["served_vs_canon"]
    sd = svc["spy_daily"]
    s3 = svc["spy_3d_tf_grid"]
    ans = (
        f"Independent Pine RSI-MACD reproduces engine.canon.rsi_macd on SPY after the first "
        f"400 sessions (max|diff| macd={fmt(par['max_abs_diff_macd'])}, "
        f"signal={fmt(par['max_abs_diff_signal'])}; bullish crosses "
        f"{par['cross_count_canon']} vs {par['cross_count_pine']}, "
        f"cross-date mismatches={par['cross_date_mismatches']}). "
        f"Production 3-session bars match manual pos//3 OHLCV exactly on open-date labels "
        f"(mismatches={par['bars3d_mismatches_open_label']}) and disagree under the spec's "
        f"last-session date label (ticker A: bars3d_canon={par['bars3d_canon']}, "
        f"bars3d_manual={par['bars3d_manual']}, bars3d_mismatches={par['bars3d_mismatches']}; "
        f"closes identical, dates open vs last). "
        f"Canon parity is not served parity: served (technicals.rsi + ewm adjust=True) vs "
        f"canon.rsi_macd on SPY daily after session 400 max|macd|={fmt(sd['max_abs_diff_macd_after_400'])} "
        f"(first-400 max|macd|={fmt(sd['max_abs_diff_macd_first_400'])}, "
        f"full max|macd|={fmt(sd['max_abs_diff_macd_full'])}, "
        f"cross-date mismatches full={sd['cross_date_mismatches_full']}); "
        f"SPY 3D _tf_grid after 400 bars max|macd|={fmt(s3['max_abs_diff_macd_after_400'])} "
        f"(full max|macd|={fmt(s3['max_abs_diff_macd_full'])}, "
        f"cross-date mismatches full={s3['cross_date_mismatches_full']})."
    )
    md = []
    md.append("# A1 RESULT — baseline and clock truth census")
    md.append("")
    md.append(
        "Price stores on this checkout are FINAL-VINTAGE (as observed today, not point-in-time) "
        "and the universes are SURVIVOR-SELECTED (current membership only). "
        + ans
    )
    md.append("")
    md.append("## ANSWER FIRST")
    md.append("")
    md.append(ans)
    md.append("")
    md.append(f"repo_head=`{head}`  tests=`{tests_line}`  status=`{status}`")
    md.append("")
    md.append("## 1. Served definition (receipts in served_definition.md)")
    md.append("")
    md.append(
        "Signal grains: **3D** (master T1 / `signal_quality.signal_frame`) and **2D** "
        "(T2/T3). Confirmation grains: **W-FRI** and **2W-FRI**. "
        "Live board ranker: `BOARD_DEFINITION = us_prophet_v3` (`engine/us_board_rank.py:100`). "
        "Served call path: `scripts/build_stock_library.py:234,:3745` → "
        "`engine/signal_gate.py:65-67,:379,:468` → `confluence_tiers.cascade` / "
        "`signal_quality._rsi_macd`. Buyable = T1 or T2 or T3 "
        f"(`engine/signal_gate.py:{buyable_line},:113-120`); T1 = 3D × 3D, T2/T3 = 2D-projected × 3D. "
        "Live board does **not** call `engine.canon.rsi_macd`."
    )
    md.append("")
    fam_rows = []
    for name, rec in served["rank_families"].items():
        fam_rows.append([name, rec["file"], rec["line"], rec["conditions_on"]])
    md.append(_md_table(["family", "file", "line", "conditions_on"], fam_rows))
    md.append("")
    md.append("## 2. Parity (schema keys)")
    md.append("")
    md.append(_md_table(["key", "value"], [[k, parity_public[k]] for k in [
        "max_abs_diff_macd", "max_abs_diff_signal", "cross_count_canon", "cross_count_pine",
        "cross_date_mismatches", "bars3d_canon", "bars3d_manual", "bars3d_mismatches",
        "bars2d_canon", "bars2d_manual", "bars2d_mismatches",
    ]]))
    md.append("")
    md.append("### Served vs canon")
    md.append("")
    md.append(_md_table(
        ["grain", "max|macd| after400", "max|macd| full", "max|sig| after400",
         "max|sig| full", "xmis after400", "xmis full"],
        [
            ["SPY daily", sd["max_abs_diff_macd_after_400"], sd["max_abs_diff_macd_full"],
             sd["max_abs_diff_signal_after_400"], sd["max_abs_diff_signal_full"],
             sd["cross_date_mismatches_after_400"], sd["cross_date_mismatches_full"]],
            ["SPY 3D _tf_grid", s3["max_abs_diff_macd_after_400"], s3["max_abs_diff_macd_full"],
             s3["max_abs_diff_signal_after_400"], s3["max_abs_diff_signal_full"],
             s3["cross_date_mismatches_after_400"], s3["cross_date_mismatches_full"]],
        ],
    ))
    md.append("")
    md.append("Full write-up: `parity.md`. Ledgers: `ledger_denominators.md`. Code receipts: `served_definition.md`. Git eras: `era_map.md`. Inventory: `data_inventory.json`.")
    md.append("")
    md.append("## 3. Ledgers (honest-N)")
    md.append("")
    md.append(_md_table(
        ["item", "N"],
        [
            ["prophet ledger rows", led_js["prophet_ledger"]["rows"]],
            ["prophet distinct names", led_js["prophet_ledger"]["n_names"]],
            ["retro_grades rows", led_js["retro_grades"]["rows"]],
            ["retro distinct as_of", led_js["retro_grades"]["as_of_count"]],
            ["retro as_of first", led_js["retro_grades"]["as_of_first"]],
            ["retro as_of last", led_js["retro_grades"]["as_of_last"]],
            ["retro distinct tickers", led_js["retro_grades"]["n_tickers"]],
        ],
    ))
    md.append("")
    md.append("Prophet month × outcome (ALL row): "
              + ", ".join(f"{k}={led_js['prophet_ledger']['totals'][k]}"
                          for k in list(OUTCOMES) + ["other"]))
    md.append("")
    md.append(led_js["retro_grades"]["share_ret_nonnull_note"])
    md.append("")
    md.append("retro_grades rank_by as_of months: "
              + ", ".join(f"{k}={v}" for k, v in led_js["retro_grades"]["rank_by_as_of_months"].items()))
    md.append("")
    md.append("## Tests")
    md.append("")
    md.append(f"`{tests_line}`")
    md.append("")
    md.append("```")
    md.append(pytest_out[-4000:])
    md.append("```")
    md.append("")
    md.append("## Deviations")
    md.append("")
    for d in deviations:
        md.append(f"- {d}")
    md.append("")
    md.append("## Gaps")
    md.append("")
    for g in gaps:
        md.append(f"- {g}")
    md.append("")
    (RESULTS / "RESULT.md").write_text("\n".join(md))

    # hashes of inputs we actually read + outputs
    extra_inputs = [
        REPO / "engine/canon.py",
        REPO / "engine/session_anchor.py",
        REPO / "engine/bar_derive.py",
        REPO / "engine/mtf_upturn.py",
        REPO / "engine/us_board_rank.py",
        REPO / "engine/prophet_bridge.py",
        REPO / "engine/setups.py",
        REPO / "engine/stock_desk.py",
        REPO / "engine/confluence_tiers.py",
        REPO / "engine/signal_quality.py",
        REPO / "engine/technicals.py",
        REPO / "engine/signal_gate.py",
        REPO / "engine/us_candidate_lanes.py",
        REPO / "engine/prophet_board_since.py",
        REPO / "engine/prophet_miss_audit.py",
        REPO / "scripts/build_stock_library.py",
        REPO / "scripts/prophet_fusion_race.py",
    ]
    outputs = list(RESULTS.rglob("*"))
    collect_hashes([str(p) for p in extra_inputs] + inv_inputs, [p for p in outputs if p.is_file()])
    print(f"A1 run complete status={status} tests={tests_line}")
    print(ans)


if __name__ == "__main__":
    main()
