"""Independent local analysis of committed bars, never a protected-API replay.

Prints a reproducibility receipt to stdout. Keep the result outside public Git
until the input producer's derived-publication rights are qualified. No fetcher,
provider, planner, stage writer or publication function is called.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from engine.stock_technicals import snapshot

CODE = (
    "engine/stock_technicals.py", "engine/technicals.py", "engine/indicators.py",
    "collectors/sector_holdings.py",
)


def blob(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def replay(revision: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("An exact full source commit is required")
    code = {}
    for path in CODE:
        bound = blob(revision, path)
        if (ROOT / path).read_bytes() != bound:
            raise ValueError(f"Working source differs from bound revision: {path}")
        code[path] = hashlib.sha256(bound).hexdigest()
    path = "data/stocks/NVDA.parquet"
    raw = blob(revision, path)
    frame = pd.read_parquet(io.BytesIO(raw))
    required = ["close", "high", "low", "volume"]
    if (not isinstance(frame.index, pd.DatetimeIndex)
            or not frame.index.is_unique or not frame.index.is_monotonic_increasing
            or frame.index.hasnans or len(frame) < 300):
        raise ValueError("Insufficient or ambiguous bar index")
    numeric = frame[required].astype(float)
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Nonfinite input bars")
    if (numeric[["close", "high", "low"]] <= 0).any().any():
        raise ValueError("Nonpositive prices")
    if (numeric.volume < 0).any() or (numeric.high < numeric.low).any():
        raise ValueError("Invalid range or volume")
    if ((numeric.close < numeric.low - 0.001)
            | (numeric.close > numeric.high + 0.001)).any():
        raise ValueError("Input close/range basis is inconsistent")

    values = snapshot(numeric.close, numeric.high, numeric.low, numeric.volume)
    selected = {key: values[key] for key in (
        "pct_vs_50dma", "pct_vs_200dma", "rsi14", "adx14", "hv_pctile", "hv20",
    )}
    if any(v is None or not np.isfinite(v) for v in selected.values()):
        raise ValueError("Requested analytical coverage is incomplete")
    for key in ("rsi14", "adx14", "hv_pctile"):
        if not 0 <= selected[key] <= 100:
            raise ValueError(f"Indicator outside its mathematical range: {key}")
    # Independent arithmetic checks for two receipt-bearing calculations.
    checks = {}
    for window in (50, 200):
        expected = round((float(numeric.close.iloc[-1])
                          / statistics.fmean(numeric.close.tail(window)) - 1) * 100, 1)
        key = f"pct_vs_{window}dma"
        if selected[key] != expected:
            raise ValueError(f"Independent moving-average calculation differs: {key}")
        checks[key] = "matches independent statistics.fmean calculation"

    return {
        "kind": "independent_local_technical_replay/v1",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": revision,
        "input": {
            "path": path, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "rows": len(frame), "columns": required,
            "first_bar_date": str(frame.index[0].date()),
            "last_bar_date": str(frame.index[-1].date()),
            "bar_frequency": "daily, incumbent StockPriceAdapter store",
            "clock_scope": "Stored date labels; no intraday UTC timestamps supplied",
            "cleaning": "No rows dropped, rescaled, filled or replaced",
            "basis": "Incumbent adjusted store; no independent vendor adjustment audit",
            "producer_provenance": "StockPriceAdapter uses Yahoo auto_adjust=True; raw market observations are external",
        },
        "engine": {"entrypoint": "engine.stock_technicals.snapshot",
                   "parameters": "Full retained OHLCV history, default windows, no benchmark",
                   "source_sha256": code},
        "runtime": {"python": platform.python_version(), **{
            package: importlib.metadata.version(package)
            for package in ("numpy", "pandas", "pyarrow")}},
        "analytical_results": selected,
        "checks": {"ordered_unique_complete_finite_bars": True,
                   "positive_prices_and_coherent_ranges": True,
                   "bounded_oscillators_and_percentile": True, **checks},
        "replay_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "New local calculations on the stated input date, not protected endpoint or deployed-output parity, new live observations, causal event attribution, or trading advice",
        "rights_status": "underlying_market_data_derived_publication_unqualified",
        "allow_stage": False, "allow_emit": False,
        "protected_endpoint_accessed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(replay(args.source_revision), indent=2, allow_nan=False))
