from __future__ import annotations

"""Pre-freeze SUPPORT census for Q10 (counts only; reads no evaluation outcome).

Reports cohort size, date coverage, invalid-ratio counts and split-break counts so the
preregistration can name its cohort and attrition honestly. It computes no interval,
coverage, score or comparison of any kind.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
OUT = Path(__file__).resolve().parent / "support_census.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from engine.darkpool_signals import share_break_index  # incumbent rule

    deep = DATA / "finra_short_volume" / "panel_deep.parquet"
    coll = DATA / "finra_short_volume" / "panel.parquet"
    d = pd.read_parquet(deep)
    c = pd.read_parquet(coll)
    universe = sorted(d["ticker"].astype(str).unique())
    df = pd.concat([d, c], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["date", "ticker"], keep="last")
    df = df[df["ticker"].isin(universe)]
    out = {"n_universe": len(universe), "with_yahoo": 0, "rows_joined": 0,
           "rows_invalid_ratio_gt1": 0, "rows_zero_denominator": 0,
           "rows_p_eq_0": 0, "rows_p_eq_1": 0, "issuers_with_break": [],
           "dates_min": str(df["date"].min().date()), "dates_max": str(df["date"].max().date()),
           "n_dates": int(df["date"].nunique()), "inputs": {str(deep): sha(deep), str(coll): sha(coll)}}
    for tk in universe:
        yp = DATA / "yahoo" / f"{tk}.parquet"
        if not yp.exists():
            continue
        y = pd.read_parquet(yp)
        y.index = pd.to_datetime(y.index).normalize()
        if "volume" not in y.columns:
            continue
        out["with_yahoo"] += 1
        f = df[df["ticker"] == tk].set_index("date").sort_index()
        j = f[["total_vol"]].join(y["volume"].rename("cons"), how="inner").dropna()
        out["rows_joined"] += len(j)
        out["rows_zero_denominator"] += int((j["cons"] <= 0).sum())
        jj = j[j["cons"] > 0]
        p = jj["total_vol"] / jj["cons"]
        out["rows_invalid_ratio_gt1"] += int((p > 1).sum())
        out["rows_p_eq_0"] += int((p == 0).sum())
        out["rows_p_eq_1"] += int((p == 1).sum())
        pv = p[(p >= 0) & (p <= 1)]
        b = share_break_index(pv)
        if b is not None:
            out["issuers_with_break"].append([tk, str(pv.index[b].date())])
    out["n_issuers_with_break"] = len(out["issuers_with_break"])
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "issuers_with_break"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
