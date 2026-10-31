"""Entry Timing W2 — T1 feasibility census. Dates, tickers and lane flags ONLY.

Reads no price, grade, outcome, excess or paired-race column or file. Two bases:

* default: `payload.opened_session` as the t_disc stand-in and a plain ticker join
  (the revision-2 screening table);
* ``--receipt-sessions <json>`` (freeze basis): t_disc = the W1 r2 receipt-recovered
  document ``data_session`` of each OPENED row's ``source_receipt`` (the JSON written by
  ``scripts/report_us_candidate_episode_waterfall.py`` ``turn_watch_receipt_sessions``),
  and every candidate stamp joins the episode only when
  ``VendorAliasTable.resolve("membership", ticker, on=stamp_date)`` returns the
  episode's ``security_id`` (registration §2).  ``--k`` is the admission wait cap and
  ``--lane-coverage-end`` the last stamp date whose ``lane`` column is populated.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("data/us_prophet_rank")
GEN = ROOT / "episodes/generations/peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9"
COLS = ["stamp_date", "ticker", "tier", "lane", "eligible", "buyable", "featured",
        "pool_in_buy_lane", "signal_asof"]


def _stamps() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(ROOT / "candidates" / "2026-*.parquet"))):
        d = pd.read_parquet(f)
        frames.append(d[[c for c in COLS if c in d.columns]].copy())
    c = pd.concat(frames, ignore_index=True)
    c["stamp_date"] = pd.to_datetime(c["stamp_date"]).dt.strftime("%Y-%m-%d")
    return c


def _opened() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(GEN / "events" / "*.jsonl"))):
        for line in open(f):
            e = json.loads(line)
            if e.get("event_type") == "OPENED":
                p = e.get("payload", {})
                out.append({"episode_id": e.get("episode_id"), "receipt": e.get("source_receipt"),
                            "ticker": p.get("ticker_at_observation"), "opened_session": p.get("opened_session"),
                            "security_id": p.get("security_id")})
    return out


def _busdays(a: str, b: str) -> int:
    return int(np.busday_count(np.datetime64(a), np.datetime64(b)))


def screening(c: pd.DataFrame, opened: list[dict]) -> dict:
    cov = c.groupby("stamp_date").agg(
        tier_curated=("tier", lambda s: int((s == "curated").sum())),
        lane_buy=("lane", lambda s: int((s == "buy").sum())),
        featured=("featured", lambda s: int((s == True).sum())),
        buyable=("buyable", lambda s: int((s == True).sum())),
        eligible=("eligible", lambda s: int((s == True).sum())))
    grid = sorted(cov.index)
    gi = {d: i for i, d in enumerate(grid)}
    sa = pd.to_datetime(c["signal_asof"], errors="coerce").dt.strftime("%Y-%m-%d")
    out = {"stamp_dates": len(grid), "first_last_stamp": [grid[0], grid[-1]],
           "dates_with": {k: int((cov[k] > 0).sum()) for k in cov.columns},
           "last_date_with": {k: str(cov[cov[k] > 0].index[-1]) for k in cov.columns if (cov[k] > 0).any()},
           "median_rows_per_date": {k: float(cov[cov[k] > 0][k].median()) for k in cov.columns},
           "signal_asof_after_stamp_rows": int((sa > c["stamp_date"]).sum()), "opened": len(opened)}
    defs = {"curated": c.tier == "curated", "lane_buy": c.lane == "buy", "buyable": c.buyable == True,
            "featured": c.featured == True, "eligible": c.eligible == True}
    res = {}
    for name, mask in defs.items():
        by = c[mask].groupby("ticker")["stamp_date"].apply(sorted).to_dict()
        lags, never, prior = [], 0, 0
        for o in opened:
            s = o["opened_session"]
            ds = by.get(o["ticker"], [])
            prior += any(d < s for d in ds)
            later = [d for d in ds if d >= s]
            if not later:
                never += 1
                continue
            gs = [d for d in grid if d >= s]
            lags.append(gi[later[0]] - gi[gs[0]])
        ser = pd.Series(lags, dtype=float)
        res[name] = {"with_stamp": len(lags), "never": never, "already_before": int(prior),
                     "zero_lag_share": round(float((ser == 0).mean()), 3) if len(ser) else None,
                     "median_lag_grid": float(ser.median()) if len(ser) else None,
                     "iqr_grid": [float(ser.quantile(.25)), float(ser.quantile(.75))] if len(ser) else None,
                     "lag_le_10_grid": int((ser <= 10).sum())}
    out["t1_defs"] = res
    return out


def freeze_basis(c: pd.DataFrame, opened: list[dict], receipt_sessions: dict, *, k: int,
                 lane_end: str, r_from: str, r_to: str) -> dict:
    sys.path.insert(0, ".")
    from engine.us_candidate_episode_intake import _records_snapshot  # noqa: E402
    from lib.dataos.identity import VendorAliasTable  # noqa: E402
    rows, receipt = _records_snapshot(Path("data/reference/vendor_aliases.parquet"))
    aliases = VendorAliasTable.from_records(rows)
    buy = c[c.lane == "buy"].groupby("ticker")["stamp_date"].apply(sorted).to_dict()
    lane_dates = sorted(set(c[c.lane.notna()]["stamp_date"]))
    sa_bad = set(map(tuple, c[pd.to_datetime(c["signal_asof"], errors="coerce").dt.strftime("%Y-%m-%d") > c["stamp_date"]][["stamp_date", "ticker"]].values.tolist()))
    counts = {"opened": len(opened), "t_disc_recovered": 0, "t_disc_unrecovered": 0, "in_R": 0,
              "t1_identified": 0, "t1_cash_window_covered": 0, "t1_censored_coverage": 0,
              "t1_unknown_identity_stamps": 0, "t1_unknown_signal_asof_stamps": 0, "already_before_t_disc": 0,
              "zero_lag": 0}
    lags_bd, lags_grid, by_month = [], [], {}
    grid = sorted(set(c["stamp_date"]))
    gi = {d: i for i, d in enumerate(grid)}
    for o in opened:
        s = receipt_sessions.get(o["receipt"])
        if not s:
            counts["t_disc_unrecovered"] += 1
            continue
        counts["t_disc_recovered"] += 1
        if not (r_from <= s <= r_to):
            continue
        counts["in_R"] += 1
        ds = buy.get(o["ticker"], [])
        counts["already_before_t_disc"] += any(d < s for d in ds)
        window_end_bd = np.busday_offset(np.datetime64(s), k, roll="forward")
        window_end = str(window_end_bd)
        t_cur = None
        for d in ds:
            if d < s or d > window_end:
                continue
            if (d, o["ticker"]) in sa_bad:
                counts["t1_unknown_signal_asof_stamps"] += 1
                continue
            sid = aliases.resolve("membership", o["ticker"], on=date.fromisoformat(d))
            if sid != o["security_id"]:
                counts["t1_unknown_identity_stamps"] += 1
                continue
            t_cur = d
            break
        if t_cur is not None:
            counts["t1_identified"] += 1
            lag_bd = _busdays(s, t_cur)
            lags_bd.append(lag_bd)
            gs = [d for d in grid if d >= s]
            lags_grid.append(gi[t_cur] - gi[gs[0]] if gs else None)
            counts["zero_lag"] += lag_bd == 0
            by_month[s[:7]] = by_month.get(s[:7], 0) + 1
        elif window_end > lane_end:
            counts["t1_censored_coverage"] += 1
        else:
            counts["t1_cash_window_covered"] += 1
    ser = pd.Series(lags_bd, dtype=float)
    return {"basis": "W1 receipt-recovered data_session + VendorAliasTable membership join",
            "alias_receipt": receipt, "k_sessions": k, "lane_coverage_end": lane_end,
            "R": [r_from, r_to], "counts": counts,
            "identified_pairs_by_t_disc_month": by_month,
            "lag_busdays": {"median": float(ser.median()) if len(ser) else None,
                            "iqr": [float(ser.quantile(.25)), float(ser.quantile(.75))] if len(ser) else None,
                            "k_star_candidate": float(ser.median()) if len(ser) else None},
            "lag_grid_median": float(pd.Series([l for l in lags_grid if l is not None]).median()) if lags_grid else None,
            "primary_pairs_itt": counts["t1_identified"] + counts["t1_cash_window_covered"],
            "floor_30_met": (counts["t1_identified"] + counts["t1_cash_window_covered"]) >= 30}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt-sessions", type=Path, help="W1 turn_watch receipt->data_session JSON")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--lane-coverage-end", default="2026-10-19")
    ap.add_argument("--r-from", default="2026-08-26")
    ap.add_argument("--r-to", default="2026-10-23")
    a = ap.parse_args()
    c, opened = _stamps(), _opened()
    out = {"screening": screening(c, opened)}
    if a.receipt_sessions:
        raw = json.loads(a.receipt_sessions.read_text())
        out["freeze_basis"] = freeze_basis(c, opened, raw.get("sessions", raw), k=a.k,
                                           lane_end=a.lane_coverage_end, r_from=a.r_from, r_to=a.r_to)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
