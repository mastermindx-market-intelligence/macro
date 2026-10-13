"""Q16 shared research helpers: input loading, hashing and RUNS.log appends.

Research-only. Reads licensed local price files read-only; writes only inside this
directory. Not imported by any production path.
"""
from __future__ import annotations

import hashlib
import json
import shlex
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STAGING = HERE.parents[2]
if str(STAGING) not in sys.path:
    sys.path.insert(0, str(STAGING))

from engine import vol_forecast  # noqa: E402  (incumbent base predictor, unchanged)

DATA_ROOT = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
DATA_VINTAGE = "cdab62686e79c76b6d431b02dec49c41a290f4c2"
ASSETS = ("SPY", "QQQ", "IWM", "TLT", "GLD")
HORIZON = 22
ALPHA = 0.2
TRAIN_END_DATE = "2014-12-31"
RUNS_LOG = HERE / "RUNS.log"
VOL_FORECAST_PATH = STAGING / "engine" / "vol_forecast.py"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_paths() -> dict[str, Path]:
    out = {a: DATA_ROOT / "yahoo" / f"{a}.parquet" for a in ASSETS}
    out["engine/vol_forecast.py"] = VOL_FORECAST_PATH
    return out


def input_hashes() -> dict[str, str]:
    return {k: sha256_file(p) for k, p in input_paths().items()}


def load_panel() -> dict[str, pd.Series]:
    """Adjusted closes per asset, restricted to the common date axis."""
    closes = {}
    for a in ASSETS:
        df = pd.read_parquet(DATA_ROOT / "yahoo" / f"{a}.parquet")
        s = df["close"].astype(float)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        closes[a] = s
    start = max(s.index[0] for s in closes.values())
    end = min(s.index[-1] for s in closes.values())
    common = None
    for s in closes.values():
        ix = s.loc[start:end].index
        common = ix if common is None else common.intersection(ix)
    return {a: closes[a].reindex(common) for a in ASSETS}


def asset_frame(close: pd.Series, horizon: int = HORIZON) -> pd.DataFrame:
    """Incumbent forecast scale, label and regime at each origin (positional axis).

    sigma_h  = vol_forecast.har_vol (daily units) * sqrt(h)   [emitted at close t]
    y        = log(C_{t+h} / C_t)                              [matures at close t+h]
    regime   = tercile of vol_forecast.vol_regime at t          [known at t]
    """
    hv = vol_forecast.har_vol(close)
    sig = hv * np.sqrt(horizon)
    logc = np.log(close)
    y = logc.shift(-horizon) - logc
    vr = vol_forecast.vol_regime(close, 252)
    reg = pd.Series(np.where(vr.isna(), "unknown",
                             np.where(vr < 1 / 3, "low", np.where(vr < 2 / 3, "mid", "high"))),
                    index=close.index)
    return pd.DataFrame({"sigma_h": sig, "y": y, "regime": reg, "cone_vol_ann":
                         vol_forecast.cone_vol_ann(close)})


def append_run(command: list[str], rc: int, inputs: dict[str, str],
               outputs: dict[str, str], note: str = "") -> None:
    rec = {"command": " ".join(shlex.quote(c) for c in command), "exit_code": int(rc),
           "inputs_sha256": inputs, "outputs_sha256": outputs, "note": note}
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
