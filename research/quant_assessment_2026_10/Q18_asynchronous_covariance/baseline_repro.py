from __future__ import annotations

"""Q18 baseline reproduction (pre-freeze; synthetic + TRAINING-period data only).

Reproduces the incumbent complete-case Pearson seam
``engine.neuralweb.covariance_spine._build_factors_block`` (date-label join,
pct-change, rows where every series is finite, trailing <= 252 rows) by feeding
it a factor_series.json written into --workdir, and recovers its implied pairwise
correlation from the 2-factor dominant share: |rho| = 2*share - 1.

(a) synthetic asynchronous pair with known rho -> incumbent value equals the
    naive same-label Pearson and is attenuated;
(b) real 510300.SS (SSE clock) vs SPY (NYSE clock), US dates < 2020-01-01 only.

Never reads holdout (>= 2020-01-01) rows. Appends one record to RUNS.log.
"""

import argparse
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
INPUTS = {"510300": DATA / "china" / "510300.SS.parquet", "SPY": DATA / "yahoo" / "SPY.parquet"}
TRAIN_END = "2020-01-01"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _incumbent_on(workdir: Path, dates: list[str], a: list, b: list) -> dict:
    import importlib

    root = workdir / "incumbent_root"
    (root / "site" / "factordata").mkdir(parents=True, exist_ok=True)
    payload = {"factors": ["fa", "fb", "composite"],
               "chart_data": {"dates": dates, "spread": {"fa": a, "fb": b}}}
    (root / "site" / "factordata" / "factor_series.json").write_text(json.dumps(payload))
    spine = importlib.import_module("engine.neuralweb.covariance_spine")
    missing: list[str] = []
    out = spine._build_factors_block(root, missing)
    return {"out": out, "missing": missing}


def main(argv: list[str]) -> int:
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(REPO))
    from engine import async_session_covariance as asc

    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args(argv)
    workdir = Path(args.workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    res: dict = {"study": "Q18", "kind": "baseline_reproduction",
                 "incumbent": "engine/neuralweb/covariance_spine.py::_build_factors_block"}

    # (a) synthetic
    sim = asc.simulate_async_pair(400, 0.6, 0.29, 0.83, seed=181)
    ra, rb = sim["a"]["ret"], sim["b"]["ret"]
    la = np.concatenate([[1.0], np.exp(np.cumsum(ra))])
    lb = np.concatenate([[1.0], np.exp(np.cumsum(rb))])
    dates = [f"d{i:04d}" for i in range(len(la))]
    inc = _incumbent_on(workdir / "synthetic", dates, la.tolist(), lb.tolist())
    share = inc["out"]["dominant_factor_pc_share"]
    pa, pb = la[1:] / la[:-1] - 1, lb[1:] / lb[:-1] - 1
    pa, pb = pa[-252:], pb[-252:]
    pear = float(np.corrcoef(pa, pb)[0, 1])
    hy = asc.hayashi_yoshida(ra, sim["a"]["start"], sim["a"]["end"], rb,
                             sim["b"]["start"], sim["b"]["end"])
    res["synthetic"] = {"true_rho": 0.6, "incumbent_share": share,
                        "incumbent_implied_abs_rho": round(2 * share - 1, 4),
                        "independent_pearson_trailing252": round(pear, 4),
                        "reproduced": abs((2 * share - 1) - abs(pear)) <= 2e-4 + 1e-9,
                        "hy_corr_full": round(hy["corr"], 4), "n_obs_used": inc["out"]["n_obs_used"]}

    # (b) real, training period only
    s_a = pd.read_parquet(INPUTS["510300"])["close"]
    s_b = pd.read_parquet(INPUTS["SPY"])["close"]
    s_a = s_a[s_a.index < TRAIN_END]
    s_b = s_b[s_b.index < TRAIN_END]
    grid = s_a.index.union(s_b.index)
    ga, gb = s_a.reindex(grid), s_b.reindex(grid)
    to_list = lambda s: [None if not np.isfinite(v) else float(v) for v in s.to_numpy()]
    inc_r = _incumbent_on(workdir / "real", [d.strftime("%Y-%m-%d") for d in grid],
                          to_list(ga), to_list(gb))
    share_r = inc_r["out"]["dominant_factor_pc_share"]
    xa, xb = ga.to_numpy(), gb.to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        rra, rrb = xa[1:] / xa[:-1] - 1, xb[1:] / xb[:-1] - 1
    ok = np.isfinite(rra) & np.isfinite(rrb)
    idx = np.where(ok)[0][-252:]
    pear_r = float(np.corrcoef(rra[idx], rrb[idx])[0, 1])
    win_dates = grid[1:][idx]
    # HY and lag-1 on the same calendar window (descriptive, training only)
    lo, hi = win_dates[0], win_dates[-1]
    wa, wb = s_a[(s_a.index >= lo - pd.Timedelta(days=10)) & (s_a.index <= hi)], s_b[(s_b.index >= lo - pd.Timedelta(days=10)) & (s_b.index <= hi)]
    iva = asc.return_intervals(wa.index, wa.to_numpy(), asc.SSE)
    ivb = asc.return_intervals(wb.index, wb.to_numpy(), asc.NYSE)
    iva, ivb = iva[iva["date"] >= lo], ivb[ivb["date"] >= lo]
    q = asc.qualify_pair(iva, ivb)
    lag1 = asc.lag_aligned(iva["date"], iva["ret"].to_numpy(), ivb["date"], ivb["ret"].to_numpy(), lag=1)
    naive = asc.naive_same_label(iva["date"], iva["ret"].to_numpy(), ivb["date"], ivb["ret"].to_numpy())
    res["real_training"] = {
        "pair": "510300.SS (SSE 15:00 Asia/Shanghai) vs SPY (NYSE 16:00 America/New_York)",
        "window": [str(lo.date()), str(hi.date())],
        "incumbent_share": share_r, "incumbent_implied_abs_rho": round(2 * share_r - 1, 4),
        "independent_pearson_complete_case_trailing252": round(pear_r, 4),
        "reproduced": abs((2 * share_r - 1) - abs(pear_r)) <= 2e-4 + 1e-9,
        "n_obs_used": inc_r["out"]["n_obs_used"],
        "descriptive_same_window": {"naive_same_label_uncentered": round(naive["corr"], 4),
                                    "lag1_uncentered": round(lag1["corr"], 4),
                                    "hy_corr": round(q["hy"]["corr"], 4),
                                    "hy_pairs": q["hy"]["n_pairs"]},
        "incumbent_missing_inputs": inc_r["missing"],
    }
    res["incumbent_on_real_input"] = ("not runnable: staging copy is sparse (site/ absent) — "
                                      "site/factordata/factor_series.json does not exist; the seam "
                                      "was exercised on files written into --workdir instead")
    res["input_sha256"] = {k: _sha(v) for k, v in INPUTS.items()}
    out = HERE / "results" / "baseline_reproduction.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("synthetic", "real_training")}, indent=1))
    return 0 if res["synthetic"]["reproduced"] and res["real_training"]["reproduced"] else 3


if __name__ == "__main__":
    argv = sys.argv[1:]
    try:
        rc = main(argv)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        rc = 1
    rec = {"script": "baseline_repro.py", "command": "python3.12 " + " ".join([str(Path(__file__).resolve())] + argv),
           "exit_code": rc,
           "input_sha256": {k: _sha(v) for k, v in INPUTS.items() if v.exists()}}
    outp = HERE / "results" / "baseline_reproduction.json"
    if outp.exists():
        rec["output_sha256"] = {"results/baseline_reproduction.json": _sha(outp)}
    with open(HERE / "RUNS.log", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    sys.exit(rc)
