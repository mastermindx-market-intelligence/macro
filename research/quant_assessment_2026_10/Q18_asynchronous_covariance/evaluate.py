from __future__ import annotations

"""Q18 frozen evaluation: Hayashi–Yoshida (E2) vs naive same-label (E0) and
fixed lag-1 (E1) for Asia-close vs US-close index pairs, scored against a
synchronous US-clock proxy target, per US calendar quarter.

Contract (PREREG.md, frozen in FREEZE.log):
* refuses to run unless sha256(PREREG.md) equals FREEZE.log PREREG_SHA256;
* refuses on an input whose sha256 differs from the PREREG table; a missing
  input yields verdict INSUFFICIENT_DATA naming it;
* winsor bounds fitted on training rows (< 2020-01-01) only;
* holdout 2020Q1..2026Q3, one run; moving-block bootstrap over quarters
  (block 4, B=5000, seed 18, pairs resampled jointly) + Newey–West lag 3;
* appends every run (including refused runs) to RUNS.log with command, exit
  code, input and output sha256s.
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
DEFAULT_DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")

INPUTS = {
    "510300": ("china/510300.SS.parquet", "604ad25485220ea33728fdbf42cd1f807a5f950117418e6f56a36429170a7579"),
    "ASHR": ("yahoo/ASHR.parquet", "fa33964262ceb6e9c6bc9b96aff323deaeba595b40560ce8b0858d933d86d639"),
    "_HSCE": ("hk/_HSCE.parquet", "4a77aeb03b2a21612e2a6f773b2b75648c3a34f6bff98216fa9e47d7288cdde7"),
    "FXI": ("yahoo/FXI.parquet", "041b038b12a8db06534b713ca3511c03bb15872cb87a8ecfdd1959905ce934e5"),
    "SPY": ("yahoo/SPY.parquet", "6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152"),
}
PAIRS = {  # name: (asia key, asia spec attr, proxy key)
    "PAIR_CSI300": ("510300", "SSE", "ASHR"),
    "PAIR_HSCEI": ("_HSCE", "HKEX_INDEX", "FXI"),
}
TRAIN_END = "2020-01-01"
HOLDOUT_FIRST, HOLDOUT_LAST = "2020Q1", "2026Q3"
MIN_N = 40
WINSOR_Q = (0.001, 0.999)
BAR = 0.05
MBB_BLOCK, MBB_B, MBB_SEED = 4, 5000, 18
NW_LAGS = 3
MIN_QUARTERS, MIN_PER_PAIR = 16, 12

OUT_JSON = HERE / "results" / "primary_results.json"
OUT_CSV = HERE / "results" / "per_block.csv"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _frozen_hash() -> str | None:
    fl = HERE / "FREEZE.log"
    if not fl.exists():
        return None
    for line in fl.read_text().splitlines():
        if line.startswith("PREREG_SHA256="):
            return line.split("=", 1)[1].strip()
    return None


def check_freeze() -> tuple[bool, str]:
    want = _frozen_hash()
    pre = HERE / "PREREG.md"
    if want is None or not pre.exists():
        return False, "FREEZE.log or PREREG.md missing"
    got = _sha(pre)
    if got != want:
        return False, f"PREREG.md sha256 {got} != frozen {want}"
    return True, got


def _winsor_bounds(iv, np):
    tr = iv.loc[iv["date"] < TRAIN_END, "ret"].to_numpy()
    if len(tr) < 100:
        raise RuntimeError("too few training returns for winsor bounds")
    lo, hi = np.quantile(tr, WINSOR_Q)
    return float(lo), float(hi)


def _block_metrics(asc, np, pd, a_q, s_all, p_q, s_q):
    """All estimators for one (pair, quarter). a_q / p_q / s_q are the block's
    MEASURED intervals (by end-date label); s_all is the S series around it."""
    e0 = asc.naive_same_label(a_q["date"], a_q["ret"].to_numpy(), s_all["date"], s_all["ret"].to_numpy())
    e1 = asc.lag_aligned(a_q["date"], a_q["ret"].to_numpy(), s_all["date"], s_all["ret"].to_numpy(), lag=1)
    hy = asc.hayashi_yoshida(a_q["ret"].to_numpy(), a_q["start_utc"].to_numpy(np.int64),
                             a_q["end_utc"].to_numpy(np.int64), s_all["ret"].to_numpy(),
                             s_all["start_utc"].to_numpy(np.int64), s_all["end_utc"].to_numpy(np.int64),
                             min_pairs=MIN_N)
    tgt = asc.naive_same_label(p_q["date"], p_q["ret"].to_numpy(), s_all["date"], s_all["ret"].to_numpy())
    wk = lambda d: (pd.DatetimeIndex(d).isocalendar()["year"] * 100
                    + pd.DatetimeIndex(d).isocalendar()["week"]).to_numpy()
    e3 = asc.bucket_sum_corr(wk(a_q["date"]), a_q["ret"].to_numpy(), wk(s_q["date"]), s_q["ret"].to_numpy())
    reasons = []
    if tgt["n_matched"] < MIN_N or tgt["state"] != asc.MEASURED:
        reasons.append(f"target_n={tgt['n_matched']}")
    if e0["n_matched"] < MIN_N or e0["state"] != asc.MEASURED:
        reasons.append(f"e0_n={e0['n_matched']}")
    if e1["n_matched"] < MIN_N or e1["state"] != asc.MEASURED:
        reasons.append(f"e1_n={e1['n_matched']}")
    if hy["state"] != asc.MEASURED:
        reasons.append(f"hy_state={hy['state']}/pairs={hy['n_pairs']}")
    row = {
        "n_a": int(len(a_q)), "n_target": tgt["n_matched"], "n_e0": e0["n_matched"],
        "n_e1": e1["n_matched"], "hy_pairs": hy["n_pairs"], "n_e3_weeks": e3["n_buckets"],
        "T": tgt["corr"], "E0": e0["corr"], "E1": e1["corr"], "E2": hy["corr"], "E3": e3["corr"],
        "hy_out_of_bounds": bool(hy["corr_out_of_bounds"]),
        "a_holiday_gaps": int(a_q["holiday_gap"].sum()), "a_zero_returns": int(a_q["zero_return"].sum()),
        "a_bridged_invalid": int(a_q["bridged_invalid"].sum()),
        "eligible": not reasons, "drop_reason": ";".join(reasons),
    }
    if not reasons:
        row["d0"] = abs(row["E0"] - row["T"]) - abs(row["E2"] - row["T"])
        row["d1"] = abs(row["E1"] - row["T"]) - abs(row["E2"] - row["T"])
    else:
        row["d0"] = row["d1"] = float("nan")
    return row


def _synthetic_witness(asc, np):
    # SSE 07:00 UTC and NYSE 20:00 UTC as day fractions; outside the trial family.
    sim = asc.simulate_async_pair(62 * 27, 0.5, 7 / 24, 20 / 24, steps_per_day=24, seed=1818)
    a, b = sim["a"], sim["b"]
    hy = asc.hayashi_yoshida(a["ret"], a["start"], a["end"], b["ret"], b["start"], b["end"])
    lab = lambda d: np.datetime64("2000-01-03") + d.astype("timedelta64[D]")
    nv = asc.naive_same_label(lab(a["day"]), a["ret"], lab(b["day"]), b["ret"])
    return {"true_rho": 0.5, "n_days": 62 * 27, "hy_corr": round(hy["corr"], 4),
            "naive_corr": round(nv["corr"], 4),
            "expected_naive_under_attenuation": round(0.5 * (1 - (20 - 7) / 24), 4)}


def run(data_root: Path) -> tuple[int, dict]:
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(REPO))
    from engine import async_session_covariance as asc

    res: dict = {"study": "Q18", "prereg_sha256": _frozen_hash(), "bar": BAR,
                 "holdout": [HOLDOUT_FIRST, HOLDOUT_LAST], "train_end_exclusive": TRAIN_END}
    paths = {k: data_root / rel for k, (rel, _) in INPUTS.items()}
    missing = [str(paths[k]) for k in INPUTS if not paths[k].exists()]
    if missing:
        res.update(verdict="INSUFFICIENT_DATA", missing_inputs=missing)
        return 0, res
    hashes = {k: _sha(paths[k]) for k in INPUTS}
    bad = {k: hashes[k] for k in INPUTS if hashes[k] != INPUTS[k][1]}
    if bad:
        raise RuntimeError(f"input sha256 differs from PREREG table: {bad}")
    res["input_sha256"] = {INPUTS[k][0]: hashes[k] for k in INPUTS}

    series, ivs, bounds, attr = {}, {}, {}, {}
    spec_of = {"510300": asc.SSE, "_HSCE": asc.HKEX_INDEX, "ASHR": asc.NYSE, "FXI": asc.NYSE, "SPY": asc.NYSE}
    for k in INPUTS:
        s = pd.read_parquet(paths[k])["close"]
        s.index = pd.DatetimeIndex(s.index).normalize()
        series[k] = s
        iv = asc.return_intervals(s.index, s.to_numpy(), spec_of[k])
        iv = iv[iv["state"] == asc.MEASURED].reset_index(drop=True)
        lo, hi = _winsor_bounds(iv, np)
        bounds[k] = [lo, hi]
        n_clip = int(((iv["ret"] < lo) | (iv["ret"] > hi)).sum())
        iv["ret"] = iv["ret"].clip(lo, hi)
        iv["q"] = pd.DatetimeIndex(iv["date"]).to_period("Q")
        ivs[k] = iv
        ho = iv[iv["date"] >= TRAIN_END]
        attr[k] = {"rows_in": int(len(s)), "first": str(s.index[0].date()), "last": str(s.index[-1].date()),
                   "invalid_prices": int(iv.attrs.get("n_invalid_prices", 0)),
                   "intervals_measured": int(len(iv)), "winsor_clipped_all": n_clip,
                   "holdout_intervals": int(len(ho)),
                   "holdout_zero_returns": int(ho["zero_return"].sum()),
                   "holdout_holiday_gaps": int(ho["holiday_gap"].sum()),
                   "holdout_bridged_invalid": int(ho["bridged_invalid"].sum()),
                   "holdout_dst_shift_share": round(float(ho["dst_shift"].mean()), 4) if len(ho) else None}
    res["winsor_bounds_train"] = bounds
    res["attrition"] = attr

    quarters = pd.period_range(HOLDOUT_FIRST, HOLDOUT_LAST, freq="Q")
    train_q = pd.period_range("2005Q1", "2019Q4", freq="Q")
    rows = []
    S = ivs["SPY"]
    for pname, (ak, _spec, pk) in PAIRS.items():
        A, P = ivs[ak], ivs[pk]
        for split, qs in (("train", train_q), ("holdout", quarters)):
            for q in qs:
                a_q = A[A["q"] == q]
                p_q = P[P["q"] == q]
                s_q = S[S["q"] == q]
                if len(a_q) == 0 and len(p_q) == 0:
                    rows.append({"pair": pname, "split": split, "quarter": str(q), "eligible": False,
                                 "drop_reason": "no_data", "d0": float("nan"), "d1": float("nan")})
                    continue
                lo_t = q.start_time - pd.Timedelta(days=14)
                hi_t = q.end_time + pd.Timedelta(days=14)
                s_all = S[(S["date"] >= lo_t) & (S["date"] <= hi_t)]
                if len(a_q) == 0 or len(p_q) == 0:
                    rows.append({"pair": pname, "split": split, "quarter": str(q), "eligible": False,
                                 "drop_reason": f"n_a={len(a_q)};n_p={len(p_q)}",
                                 "d0": float("nan"), "d1": float("nan")})
                    continue
                r = _block_metrics(asc, np, pd, a_q, s_all, p_q, s_q)
                rows.append({"pair": pname, "split": split, "quarter": str(q), **r})
    df = pd.DataFrame(rows)

    ho = df[df["split"] == "holdout"]
    D0 = ho.pivot(index="quarter", columns="pair", values="d0").reindex([str(q) for q in quarters])
    D1 = ho.pivot(index="quarter", columns="pair", values="d1").reindex([str(q) for q in quarters])
    n_q = int(np.isfinite(D0.to_numpy()).any(axis=1).sum())
    per_pair_n = {p: int(np.isfinite(D0[p].to_numpy()).sum()) for p in PAIRS}
    res["honest_n"] = {"eligible_holdout_quarters": n_q, "eligible_pair_blocks": int(np.isfinite(D0.to_numpy()).sum()),
                       "per_pair_blocks": per_pair_n, "holdout_quarters_planned": len(quarters)}
    res["dropped_holdout_blocks"] = ho.loc[~ho["eligible"].astype(bool), ["pair", "quarter", "drop_reason"]].to_dict("records")

    m0 = asc.moving_block_bootstrap_mean(D0.to_numpy(), MBB_BLOCK, MBB_B, seed=MBB_SEED)
    m1 = asc.moving_block_bootstrap_mean(D1.to_numpy(), MBB_BLOCK, MBB_B, seed=MBB_SEED)
    nw0 = asc.newey_west_se(np.nanmean(D0.to_numpy(), axis=1), NW_LAGS)
    nw1 = asc.newey_west_se(np.nanmean(D1.to_numpy(), axis=1), NW_LAGS)
    pair_mean_d0 = {p: float(np.nanmean(D0[p].to_numpy())) for p in PAIRS}
    pair_mean_d1 = {p: float(np.nanmean(D1[p].to_numpy())) for p in PAIRS}
    elig = ho[ho["eligible"].astype(bool)]
    desc = {}
    for p in PAIRS:
        e = elig[elig["pair"] == p]
        desc[p] = {k: round(float(e[k].mean()), 4) for k in ("T", "E0", "E1", "E2", "E3")}
        desc[p].update({f"mae_{k}": round(float((e[k] - e["T"]).abs().mean()), 4) for k in ("E0", "E1", "E2", "E3")})
    tr = df[(df["split"] == "train") & (df["eligible"] == True)]  # noqa: E712
    res["train_descriptive"] = {p: {"n_blocks": int((tr["pair"] == p).sum()),
                                    "mean_d0": round(float(tr.loc[tr["pair"] == p, "d0"].mean()), 4) if (tr["pair"] == p).any() else None,
                                    "mean_d1": round(float(tr.loc[tr["pair"] == p, "d1"].mean()), 4) if (tr["pair"] == p).any() else None}
                                for p in PAIRS}
    res["holdout_block_means"] = desc
    res["H1"] = {"mean_d0": m0["mean"], "mbb_ci95": [m0["ci_lo"], m0["ci_hi"]], "mbb_se": m0["se"],
                 "mbb_state": m0["state"], "n_time_blocks": m0["n_time_blocks"],
                 "nw_lag3_mean_of_quarter_means": nw0["mean"], "nw_lag3_se": nw0["se"],
                 "per_pair_mean_d0": pair_mean_d0}
    res["H2"] = {"mean_d1": m1["mean"], "mbb_ci95": [m1["ci_lo"], m1["ci_hi"]], "mbb_se": m1["se"],
                 "nw_lag3_se": nw1["se"], "per_pair_mean_d1": pair_mean_d1}
    res["hy_out_of_bounds_blocks"] = int(elig["hy_out_of_bounds"].astype(bool).sum())

    # Descriptive PSD report (never repaired): holdout HY matrix of 510300, _HSCE, SPY.
    keys = ["510300", "_HSCE", "SPY"]
    hm = {k: ivs[k][ivs[k]["date"] >= TRAIN_END] for k in keys}
    M = np.eye(3)
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = hm[keys[i]], hm[keys[j]]
            h = asc.hayashi_yoshida(a["ret"].to_numpy(), a["start_utc"].to_numpy(np.int64), a["end_utc"].to_numpy(np.int64),
                                    b["ret"].to_numpy(), b["start_utc"].to_numpy(np.int64), b["end_utc"].to_numpy(np.int64))
            M[i, j] = M[j, i] = h["corr"]
    res["psd_report_holdout_hy_matrix"] = {"order": keys, "matrix": M.round(4).tolist(), **asc.psd_report(M)}
    res["synthetic_witness"] = _synthetic_witness(asc, np)

    insufficient = n_q < MIN_QUARTERS or any(v < MIN_PER_PAIR for v in per_pair_n.values())
    h1 = (m0["state"] == asc.MEASURED and m0["mean"] >= BAR and m0["ci_lo"] > 0
          and all(v > 0 for v in pair_mean_d0.values()))
    h2 = m1["mean"] is not None and m1["mean"] >= 0
    res["H1"]["pass"], res["H2"]["pass"] = bool(h1), bool(h2)
    if insufficient:
        res["verdict"] = "INSUFFICIENT_DATA"
        res["insufficient_reason"] = f"eligible quarters {n_q} (<{MIN_QUARTERS}) or per-pair {per_pair_n} (<{MIN_PER_PAIR})"
    else:
        res["verdict"] = "KEEP" if (h1 and h2) else "REJECT"

    OUT_CSV.parent.mkdir(exist_ok=True)
    cols = ["pair", "split", "quarter", "eligible", "drop_reason", "n_a", "n_target", "n_e0", "n_e1", "hy_pairs",
            "n_e3_weeks", "T", "E0", "E1", "E2", "E3", "d0", "d1", "hy_out_of_bounds", "a_holiday_gaps",
            "a_zero_returns", "a_bridged_invalid"]
    df.reindex(columns=cols).to_csv(OUT_CSV, index=False, float_format="%.6f")
    return 0, res


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(DEFAULT_DATA))
    args = ap.parse_args(argv)
    ok, msg = check_freeze()
    if not ok:
        print("REFUSED:", msg, file=sys.stderr)
        return 2
    rc, res = run(Path(args.data_root))
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: res.get(k) for k in ("verdict", "honest_n", "H1", "H2")}, indent=1, default=str))
    return rc


if __name__ == "__main__":
    argv = sys.argv[1:]
    try:
        rc = main(argv)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        rc = 1
    root = DEFAULT_DATA
    if "--data-root" in argv and argv.index("--data-root") + 1 < len(argv):
        root = Path(argv[argv.index("--data-root") + 1])
    rec = {"script": "evaluate.py", "command": "python3.12 " + " ".join([str(Path(__file__).resolve())] + argv),
           "exit_code": rc, "prereg_sha256": _sha(HERE / "PREREG.md") if (HERE / "PREREG.md").exists() else None,
           "input_sha256": {rel: _sha(root / rel) for rel, _ in INPUTS.values() if (root / rel).exists()},
           # provenance only (PREREG_AMENDMENT.md A1): code identity of this run
           "script_sha256": _sha(Path(__file__).resolve()),
           "module_sha256": (_sha(REPO / "engine" / "async_session_covariance.py")
                             if (REPO / "engine" / "async_session_covariance.py").exists() else None)}
    if rc == 0:
        rec["output_sha256"] = {f"results/{p.name}": _sha(p) for p in (OUT_JSON, OUT_CSV) if p.exists()}
    with open(HERE / "RUNS.log", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    sys.exit(rc)
