"""Descriptive reproduction (sector calls only) of the Sector Central grader v2
conditional directional hit rate, from tracked inputs:
  data/sector_central/calls.parquet + data/yahoo/{XL*,SPY}.parquet (close = TR).
Next-bar fill (entry = close of the bar after the call date), H sessions after the
fill; conditional rate = correct up/down calls / directional calls; SE clustered
by call date.  usage: python3 grader_sector_subset.py <calls.parquet> <tape_dir>
"""
import math
import sys
from pathlib import Path

import pandas as pd

calls = pd.read_parquet(sys.argv[1])
tapes = Path(sys.argv[2])
calls = calls[calls["kind"] == "sector"].copy()
calls["date"] = pd.to_datetime(calls["date"]).dt.normalize()
spy = pd.read_parquet(tapes / "SPY.parquet")
sess = pd.DatetimeIndex(spy.index).normalize()
closes = {}
for t in calls["ticker"].dropna().unique():
    f = tapes / f"{t}.parquet"
    if f.exists():
        d = pd.read_parquet(f)
        s = d["close"].copy()
        s.index = pd.DatetimeIndex(s.index).normalize()
        closes[t] = s.reindex(sess)
for H in (21, 63, 126):
    rows = []
    for _, r in calls.iterrows():
        s = closes.get(r["ticker"])
        if s is None:
            continue
        after = sess[sess > r["date"]]
        if len(after) == 0:
            continue
        i = sess.get_loc(after[0])
        if i + H >= len(sess):
            continue
        e, x = s.iloc[i], s.iloc[i + H]
        if pd.isna(e) or pd.isna(x):
            continue
        rows.append((r["date"], r["dir"], x / e - 1.0))
    g = pd.DataFrame(rows, columns=["date", "dir", "fwd"])
    d = g[g["dir"].isin(["up", "down"])].copy()
    if d.empty:
        print(H, "matured", len(g), "directional 0 -> ACCRUING")
        continue
    d["hit"] = ((d["dir"] == "up") & (d["fwd"] > 0)) | ((d["dir"] == "down") & (d["fwd"] < 0))
    p = d["hit"].mean()
    n = len(d)
    G = d["date"].nunique()
    resid = d.groupby("date")["hit"].apply(lambda h: (h - p).sum())
    se = math.sqrt(G / (G - 1) * (resid ** 2).sum()) / n if G > 1 else float("nan")
    print(H, "matured", len(g), "directional", n, "dates", G,
          "cond_hit", round(p, 4), "se", round(se, 4),
          "ci95", (round(p - 1.96 * se, 4), round(p + 1.96 * se, 4)),
          "n_up", int((d["dir"] == "up").sum()), "n_down", int((d["dir"] == "down").sum()))
