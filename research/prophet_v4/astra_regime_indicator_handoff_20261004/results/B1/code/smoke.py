"""Smoke test: run a few names through the pipeline.

Calls `_per_name_full` (the canonical pipeline entry point) on AAPL/MSFT/ZTS and
checks the keyed columns so we catch column-name / dtype regressions before
launching the full fleet pool.
"""
from __future__ import annotations
import sys
from pathlib import Path
import time

_THIS_FILE = Path(__file__).resolve()
CODE_DIR = _THIS_FILE.parent
RESULTS_DIR = CODE_DIR.parent
REPO = RESULTS_DIR.parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(CODE_DIR))

import pandas as pd
import numpy as np

import run  # noqa: E402
from engine import session_anchor  # noqa: E402

t0 = time.time()
spy = pd.read_parquet(REPO / "data/yahoo/SPY.parquet")
if "close" not in spy.columns:
    spy = spy.rename(columns={"close_price": "close"})
spy_close = spy["close"].astype(float).dropna()
spy_index = spy_close.index
spy_pos = session_anchor.session_positions(spy_index, market="US")

ohlcv_dir = REPO / "data/baskets/ohlcv"
test_files = ["AAPL.parquet", "MSFT.parquet", "ZTS.parquet"]
results = []
for f in test_files:
    p = ohlcv_dir / f
    if not p.exists():
        print(f"  SKIP {f} (not in basket dir)")
        continue
    df = pd.read_parquet(p)
    res = run._per_name_full(f[:-len(".parquet")], df, spy_index, spy_close, spy_pos)
    results.append((f, res))
    print(f"{f}: events={len(res['events'])}, confirms={len(res['confirms'])}, "
          f"excluded_short={res.get('excluded_short', 0)}, "
          f"excluded_gaps={res.get('excluded_gaps', 0)}, drops={res.get('drops')}")

print(f"\nelapsed: {time.time()-t0:.1f}s")
if results:
    f, res = results[0]
    if res['events']:
        ev_df = pd.DataFrame(res['events'])
        print(f"\n{f} sample events:")
        print(ev_df.head(5).to_string())
        first = ev_df.iloc[0]
        print(f"\nfirst entry_date: {first['entry_date']}, "
              f"h10_net={first['excess_h10_net']:.4f}, h21_net={first['excess_h21_net']:.4f}, "
              f"mfe21={first['mfe21']:.4f}, mae21={first['mae21']:.4f}")
        print(f"  by variant: {ev_df['variant'].value_counts().to_dict()}")
    if res['confirms']:
        cf_df = pd.DataFrame(res['confirms'])
        print(f"\n{f} sample confirms:")
        print(cf_df.head(5).to_string())
        print(f"  confirms columns: {list(cf_df.columns)}")