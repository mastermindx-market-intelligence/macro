from __future__ import annotations

"""Q15 evaluation driver: frozen preregistration -> baseline / synthetic / confirmatory.

Usage (from anywhere; paths are absolute or derived from this file):
    python evaluate.py baseline     [--stamp "<date -u output>"]
    python evaluate.py synthetic    [--stamp ...]
    python evaluate.py confirmatory [--stamp ...] [--rerun-reason "<amendment ref>"]

Guards:
* Refuses to run (exit 3) unless sha256(PREREG.md) equals the hash recorded in FREEZE.log.
* Refuses to run (exit 4) if an admitted input's sha256 differs from PREREG section 5.
* Confirmatory runs once; a second run needs --rerun-reason naming PREREG_AMENDMENT.md (exit 5).
* Every invocation (including refusals) appends one JSON line to RUNS.log with the command,
  exit code, and input and output sha256s.

Research only: reads the admitted read-only data directory, writes only into this directory.
No network, no wall-clock reads (an optional --stamp passes `date -u` text through).
"""

import argparse
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

DATA = "/Users/chriswong/Documents/Cluade/macro-main/data"
HOURLY = os.path.join(DATA, "coinbase", "btc_hourly.parquet")
DAILY = os.path.join(DATA, "coinbase", "btc_daily.parquet")
EXPECTED = {
    HOURLY: "1c1b02fd8cd6b0b7d2aec6563abe896694b27659dcb6fed17cf84bf6b450a34d",
    DAILY: "4ddd11111becf7540788f39934377418dde69e73a4ddfa6eca99828b3a5cfc95",
}
PREREG = os.path.join(HERE, "PREREG.md")
FREEZE = os.path.join(HERE, "FREEZE.log")
RUNS = os.path.join(HERE, "RUNS.log")
MODULE = os.path.join(REPO, "engine", "vol_noise_robust_realized.py")
BASELINE_CODE = os.path.join(REPO, "engine", "vol_forecast.py")

# ---- frozen design constants (PREREG sections 4-14) --------------------------------
TRAIN_FIRST = "2016-01-04"
TRAIN_LAST = "2021-12-27"
HOLD_FIRST = "2022-01-03"
HOLD_LAST = "2026-09-28"
MIN_CANDLES = 152
MAX_GAP_H = 6
SPARSE_STEP = 6
CSTAR = 3.5134
BAR = 0.05
BLOCK = 8
REPS = 2000
SEED = 1515
MIN_HOLD_WEEKS = 104
MIN_BLOCKS = 13


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str | None:
    if not os.path.exists(FREEZE):
        return None
    with open(FREEZE, encoding="utf-8") as fh:
        for line in fh:
            if "sha256=" in line and "PREREG.md" in line:
                return line.split("sha256=")[1].split()[0].strip()
    return None


def append_run(record: dict) -> None:
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def prior_confirmatory_ok() -> bool:
    if not os.path.exists(RUNS):
        return False
    with open(RUNS, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("stage") == "confirmatory" and rec.get("exit_code") == 0:
                return True
    return False


# ---- data preparation ---------------------------------------------------------------
def load_hourly():
    import numpy as np
    import pandas as pd

    df = pd.read_parquet(HOURLY)
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    s = pd.Series(df["close"].to_numpy(dtype=float), index=idx).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s[np.isfinite(s.to_numpy()) & (s.to_numpy() > 0)]
    return s


def weekly_table(close_h):
    """One row per UTC week (Monday 00:00 candle start), all labels and eligibility."""
    import numpy as np
    import pandas as pd

    from engine import vol_noise_robust_realized as m

    t = close_h.index
    lp = np.log(close_h.to_numpy())
    hours = ((t - pd.Timestamp("1970-01-01")) // pd.Timedelta(hours=1)).to_numpy().astype(np.int64)
    # Returns between consecutive available candles; assigned to the later candle.
    dh = np.diff(hours)
    rets = np.diff(lp)
    ret_t = t[1:]
    week_of = (ret_t - pd.to_timedelta(ret_t.dayofweek, unit="D")).normalize()
    cand_week = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize()
    close_by_hour = dict(zip(hours.tolist(), lp.tolist()))

    weeks = pd.date_range(pd.Timestamp(TRAIN_FIRST), pd.Timestamp(HOLD_LAST), freq="7D")
    ret_week_codes = pd.Index(week_of)
    rows = []
    for w in weeks:
        mask = ret_week_codes == w
        r = rets[mask]
        gaps = dh[mask]
        # log-price sequence for the week: start point (previous available close) + week closes
        pos = np.nonzero(mask)[0]
        n_candles = int((cand_week == w).sum())
        reasons = []
        if n_candles < MIN_CANDLES:
            reasons.append("coverage")
        if gaps.size and int(gaps.max()) > MAX_GAP_H:
            reasons.append("gap")
        if r.size < 2:
            reasons.append("no_returns")
        w_h = int((w - pd.Timestamp("1970-01-01")) // pd.Timedelta(hours=1))
        daily_hours = [w_h - 1 + 24 * k for k in range(8)]  # prev Sunday 23:00 .. Sunday 23:00
        dcl = [close_by_hour.get(hh) for hh in daily_hours]
        if any(v is None for v in dcl):
            reasons.append("daily_close_missing")
        row = {"week_start": w.strftime("%Y-%m-%d"),
               "split": "train" if w <= pd.Timestamp(TRAIN_LAST) else "holdout",
               "n_candles": n_candles, "n_returns": int(r.size),
               "max_gap_h": int(gaps.max()) if gaps.size else None,
               "L0_daily": float("nan"), "L1_rv1h": float("nan"), "RV6_sub": float("nan"),
               "omega2_hat": float("nan"), "xi2_week": float("nan"),
               "lag1_ret_autocorr": float("nan")}
        if r.size >= 2:
            p = np.concatenate([[lp[pos[0]]], lp[pos + 1]])
            rv1 = m.realized_variance(r)
            rv6 = m.sparse_realized_variance(p, SPARSE_STEP)
            om2 = max(rv1 - rv6, 0.0) / (2.0 * r.size)
            row.update({"L1_rv1h": rv1, "RV6_sub": rv6, "omega2_hat": om2,
                        "xi2_week": om2 / rv6 if rv6 > 0 else float("nan"),
                        "lag1_ret_autocorr": float(np.corrcoef(r[1:], r[:-1])[0, 1])
                        if r.size > 3 else float("nan")})
            row["_r"] = r
            row["_p"] = p
        if not any(v is None for v in dcl):
            row["L0_daily"] = float(np.sum(np.diff(np.asarray(dcl)) ** 2))
        row["eligible"] = not reasons
        row["ineligible_reason"] = "+".join(reasons)
        rows.append(row)
    return rows


def pearson(a, b):
    import numpy as np

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def pairs_index(elig):
    """(i-1, i) index pairs of consecutive weeks both eligible."""
    return [(i - 1, i) for i in range(1, len(elig)) if elig[i] and elig[i - 1]]


def rho1(vals, pairs):
    return pearson([vals[i] for i, _ in pairs], [vals[j] for _, j in pairs])


def block_bootstrap_delta(la, lb, elig, block, reps, seed):
    """Moving block bootstrap of rho1(la) - rho1(lb); pairs only within a drawn block."""
    import numpy as np

    n = len(elig)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    starts_max = n - block
    out = []
    for _ in range(reps):
        st = rng.integers(0, starts_max + 1, size=nb)
        xa, ya, xb, yb = [], [], [], []
        for s in st:
            for j in range(s + 1, s + block):
                if elig[j] and elig[j - 1]:
                    xa.append(la[j - 1]); ya.append(la[j])
                    xb.append(lb[j - 1]); yb.append(lb[j])
        out.append(pearson(xa, ya) - pearson(xb, yb))
    arr = np.asarray(out)
    arr = arr[np.isfinite(arr)]
    return {"reps_finite": int(arr.size), "ci95": [float(np.percentile(arr, 2.5)),
                                                    float(np.percentile(arr, 97.5))],
            "boot_sd": float(arr.std(ddof=1))}


# ---- stages ---------------------------------------------------------------------------
def stage_baseline() -> list[str]:
    import numpy as np
    import pandas as pd

    from engine import vol_forecast as vf

    d = pd.read_parquet(DAILY)
    didx = pd.DatetimeIndex(d.index)
    if didx.tz is not None:
        didx = didx.tz_convert("UTC").tz_localize(None)
    close_d = pd.Series(d["close"].to_numpy(dtype=float), index=didx).sort_index()
    close_d = close_d[~close_d.index.duplicated(keep="last")]
    rv22 = vf.realized_vol(close_d, 22)
    har = vf.har_vol(close_d)
    cone = vf.cone_vol_ann(close_d)
    fwd = vf.forward_vol_ann(close_d, 22)
    close_h = load_hourly()
    # Hourly-derived daily close = close of the 23:00 candle; compare to daily candle close
    # under both index conventions (day-start D, and D labelled at its end).
    h23 = close_h[close_h.index.hour == 23]
    h23.index = h23.index.normalize()
    out = {"stage": "baseline", "daily_rows": int(close_d.size),
           "daily_first": str(close_d.index[0].date()), "daily_last": str(close_d.index[-1].date()),
           "hourly_rows": int(close_h.size),
           "vol_forecast_HAR_LAGS": list(vf.HAR_LAGS),
           "realized_vol22_nonnull": int(rv22.notna().sum()),
           "har_vol_nonnull": int(har.notna().sum()),
           "cone_vol_ann_nonnull": int(cone.notna().sum()),
           "forward_vol_ann22_nonnull_label_only": int(fwd.notna().sum()),
           "cone_vol_ann_median": float(cone.median()),
           "cone_vol_ann_last": float(cone.dropna().iloc[-1]),
           "realized_vol22_last_daily_units": float(rv22.dropna().iloc[-1])}
    for name, shift in (("same_day", 0), ("prev_day", -1)):
        dd = close_d.copy()
        dd.index = dd.index + pd.Timedelta(days=shift)
        j = pd.concat([dd.rename("daily"), h23.rename("h23")], axis=1).dropna()
        diff = np.abs(np.log(j["daily"]) - np.log(j["h23"]))
        out[f"consistency_{name}"] = {"n": int(j.shape[0]),
                                      "median_abs_logdiff": float(diff.median()),
                                      "share_within_1bp": float((diff < 1e-4).mean())}
    path = os.path.join(HERE, "baseline_reproduction.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print(json.dumps(out, indent=2, sort_keys=True))
    return [path]


def stage_synthetic() -> list[str]:
    from engine import vol_noise_robust_realized as m

    res = {"stage": "synthetic", "n": 4680, "iv": 1e-4, "reps": 500, "sparse_step": 60,
           "noise_regimes_xi2": m.NOISE_REGIMES, "noise_kind": "roll", "tables": {}}
    for sv in (False, True):
        key = "stochastic_vol" if sv else "u_shape_vol"
        res["tables"][key] = m.monte_carlo_bias_table(n=4680, iv=1e-4, reps=500, seed=15,
                                                      sparse_step=60, stochastic_vol=sv)
    checks = {}
    for key, rows in res["tables"].items():
        t = {(r["regime"], r["estimator"]): r for r in rows}
        checks[key] = {
            "zero_noise_tick_bias_lt_3pct": abs(t[("none", "tick_rv")]["rel_bias"]) < 0.03,
            "zero_noise_rk_bias_lt_3pct": abs(t[("none", "realized_kernel")]["rel_bias"]) < 0.03,
            "rk_rmse_lt_tick_and_sparse_xi2_ge_1e-4": all(
                t[(g, "realized_kernel")]["rel_rmse"] < min(t[(g, "tick_rv")]["rel_rmse"],
                                                           t[(g, "sparse_rv")]["rel_rmse"])
                for g in ("medium", "high")),
            "zero_noise_tick_rmse_le_rk": t[("none", "tick_rv")]["rel_rmse"]
            <= t[("none", "realized_kernel")]["rel_rmse"],
        }
    res["pass_criteria"] = checks
    res["all_pass"] = all(all(v.values()) for v in checks.values())
    path = os.path.join(HERE, "mc_bias_table.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps(res["pass_criteria"], indent=2), "all_pass", res["all_pass"])
    return [path]


def stage_confirmatory(prereg_sha: str, input_shas: dict) -> list[str]:
    import numpy as np

    from engine import vol_noise_robust_realized as m

    close_h = load_hourly()
    rows = weekly_table(close_h)
    train = [r for r in rows if r["split"] == "train"]
    hold = [r for r in rows if r["split"] == "holdout"]

    # Hyperparameter fixed inside training only.
    tr_xi = [r["xi2_week"] for r in train if r["eligible"] and math.isfinite(r["xi2_week"])]
    xi2_train = float(np.median(tr_xi)) if tr_xi else float("nan")
    tr_share = [2 * r["n_returns"] * r["omega2_hat"] / r["L1_rv1h"] for r in train
                if r["eligible"] and r["L1_rv1h"] > 0]
    noise_share_train_median = float(np.median(tr_share)) if tr_share else float("nan")

    for r in rows:
        if "_r" in r:
            n = r["n_returns"]
            h = max(1, int(math.ceil(CSTAR * max(xi2_train, 0.0) ** 0.4 * n ** 0.6)))
            r["H"] = h
            r["L2_rk"] = m.realized_kernel(r["_r"], h)
            xw = r["xi2_week"] if math.isfinite(r["xi2_week"]) else 0.0
            hw = max(1, int(math.ceil(CSTAR * max(xw, 0.0) ** 0.4 * n ** 0.6)))
            r["H_week_feasible"] = hw
            r["L2_rk_week_feasible"] = m.realized_kernel(r["_r"], hw)
        else:
            r["H"] = None
            r["L2_rk"] = float("nan")
            r["H_week_feasible"] = None
            r["L2_rk_week_feasible"] = float("nan")
        # Non-positive labels cannot be logged: declared as attrition, never imputed.
        if r["eligible"] and not all(
                (r[k] > 0) for k in ("L0_daily", "L1_rv1h", "L2_rk", "L2_rk_week_feasible")):
            r["eligible"] = False
            r["ineligible_reason"] = "nonpositive_label"

    def logs(rs, key):
        return [math.log(r[key]) if r["eligible"] else float("nan") for r in rs]

    def contrast(rs, key_a, key_b, block=BLOCK, boot=True):
        elig = [r["eligible"] for r in rs]
        la, lb = logs(rs, key_a), logs(rs, key_b)
        pr = pairs_index(elig)
        out = {"rho1_a": rho1(la, pr), "rho1_b": rho1(lb, pr), "n_pairs": len(pr)}
        out["delta"] = out["rho1_a"] - out["rho1_b"]
        if boot:
            out.update(block_bootstrap_delta(la, lb, elig, block, REPS, SEED))
        return out

    elig_h = [r["eligible"] for r in hold]
    n_hold_weeks = len(hold)
    n_hold_elig = int(sum(elig_h))
    blocks_with_pairs = 0
    for b in range(n_hold_weeks // BLOCK):
        seg = range(b * BLOCK + 1, (b + 1) * BLOCK)
        if any(elig_h[j] and elig_h[j - 1] for j in seg):
            blocks_with_pairs += 1

    attrition = {}
    for split, rs in (("train", train), ("holdout", hold)):
        cnt = {}
        for r in rs:
            key = r["ineligible_reason"] or "eligible"
            cnt[key] = cnt.get(key, 0) + 1
        attrition[split] = {"calendar_weeks": len(rs), "by_reason": cnt}

    support_ok = n_hold_elig >= MIN_HOLD_WEEKS and blocks_with_pairs >= MIN_BLOCKS
    primary = contrast(hold, "L2_rk", "L1_rv1h")
    if not support_ok:
        verdict, label = "INSUFFICIENT_DATA", "support below PREREG section 14 minimum"
    elif (primary["delta"] >= BAR and primary["ci95"][0] > 0 and xi2_train > 0):
        verdict, label = "KEEP", "noise-aware label admissible as separately versioned research label"
    else:
        verdict = "REJECT"
        label = "REJECT (clear)" if primary["ci95"][1] < BAR else "REJECT (inconclusive)"
    falsifier = {"keep_rule_met": verdict == "KEEP",
                 "xi2_train": xi2_train,
                 "noise_share_train_median": noise_share_train_median,
                 "noise_share_below_1pct": (noise_share_train_median < 0.01)
                 if math.isfinite(noise_share_train_median) else None,
                 "fired": verdict != "KEEP"}

    # ---- descriptive (cannot change the verdict) ----
    desc = {}
    desc["holdout_rho1_L1_minus_L0"] = contrast(hold, "L1_rv1h", "L0_daily")
    desc["holdout_week_feasible_H_vs_L1"] = contrast(hold, "L2_rk_week_feasible", "L1_rv1h")
    desc["training_L2_vs_L1"] = contrast(train, "L2_rk", "L1_rv1h", boot=False)
    desc["block_len_4"] = contrast(hold, "L2_rk", "L1_rv1h", block=4)
    desc["block_len_13"] = contrast(hold, "L2_rk", "L1_rv1h", block=13)
    half = n_hold_weeks // 2
    desc["holdout_first_half"] = contrast(hold[:half], "L2_rk", "L1_rv1h", boot=False)
    desc["holdout_second_half"] = contrast(hold[half:], "L2_rk", "L1_rv1h", boot=False)
    he = [r for r in hold if r["eligible"]]
    desc["holdout_mean_log_L2_over_L1"] = float(np.mean([math.log(r["L2_rk"] / r["L1_rv1h"])
                                                        for r in he])) if he else None
    desc["holdout_mean_log_L1_over_L0"] = float(np.mean([math.log(r["L1_rv1h"] / r["L0_daily"])
                                                        for r in he])) if he else None
    desc["H_holdout_distribution"] = {str(k): int(v) for k, v in zip(
        *np.unique([r["H"] for r in he], return_counts=True))} if he else {}
    sig = {}
    for split, rs in (("train", train), ("holdout", hold)):
        ratios = {s: [] for s in (1, 2, 4, 6, 12, 24)}
        for r in rs:
            if not r["eligible"]:
                continue
            c = m.signature_curve(r["_p"], [1, 2, 4, 6, 12, 24])
            base = c[1]["rv"]
            for s in ratios:
                if base > 0:
                    ratios[s].append(c[s]["rv"] / base)
        sig[split] = {f"{s}h": {"median_rv_ratio_to_1h": float(np.median(v)) if v else None,
                                "mean_rv_ratio_to_1h": float(np.mean(v)) if v else None}
                      for s, v in ratios.items()}
    desc["signature_curve"] = sig
    by_year = {}
    for r in rows:
        if not r["eligible"]:
            continue
        y = r["week_start"][:4]
        d = by_year.setdefault(y, {"share": [], "ac": [], "n": 0})
        d["share"].append(2 * r["n_returns"] * r["omega2_hat"] / r["L1_rv1h"])
        if math.isfinite(r["lag1_ret_autocorr"]):
            d["ac"].append(r["lag1_ret_autocorr"])
        d["n"] += 1
    desc["noise_by_year"] = {y: {"eligible_weeks": d["n"],
                                 "median_noise_share": float(np.median(d["share"])),
                                 "share_weeks_noise_share_gt_10pct":
                                     float(np.mean(np.asarray(d["share"]) > 0.10)),
                                 "median_week_lag1_autocorr": float(np.median(d["ac"])),
                                 "lag1_flag_threshold_minus2_over_sqrt168": -2 / math.sqrt(168)}
                             for y, d in sorted(by_year.items())}

    spec = {"estimator_L2": "parzen_realized_kernel_non_flat_top_no_jitter",
            "cstar": CSTAR, "xi2_train": xi2_train, "sparse_step": SPARSE_STEP,
            "max_gap_h": MAX_GAP_H, "min_candles": MIN_CANDLES,
            "qv_convention": m.QV_CONVENTION, "label_schema": m.LABEL_SCHEMA}
    version = hashlib.sha256(json.dumps({"inputs": input_shas, "prereg": prereg_sha,
                                         "spec": spec}, sort_keys=True).encode()).hexdigest()

    # ---- outputs ----
    cols = ["week_start", "split", "eligible", "ineligible_reason", "n_candles", "n_returns",
            "max_gap_h", "L0_daily", "L1_rv1h", "L2_rk", "H", "RV6_sub", "omega2_hat",
            "xi2_week", "H_week_feasible", "L2_rk_week_feasible", "lag1_ret_autocorr"]
    csv_path = os.path.join(HERE, "labels_weekly.csv")
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write(",".join(cols + ["label_version", "research_only", "accepted_label"]) + "\n")
        for r in rows:
            vals = []
            for c in cols:
                v = r.get(c)
                if isinstance(v, float):
                    vals.append("" if not math.isfinite(v) else repr(v))
                elif v is None:
                    vals.append("")
                else:
                    vals.append(str(v))
            fh.write(",".join(vals + [version, "True", "False"]) + "\n")

    result = {"stage": "confirmatory", "trial": "Q15-T1", "verdict": verdict,
              "verdict_label": label, "label_version": version, "prereg_sha256": prereg_sha,
              "inputs_sha256": input_shas, "spec": spec,
              "primary_L2_vs_L1_holdout": primary, "practical_bar": BAR,
              "honest_n": {"holdout_calendar_weeks": n_hold_weeks,
                           "holdout_eligible_weeks": n_hold_elig,
                           "holdout_eligible_pairs": primary["n_pairs"],
                           "nonoverlapping_8w_blocks_with_pairs": blocks_with_pairs,
                           "nonoverlapping_8w_blocks_calendar": n_hold_weeks // BLOCK},
              "support_ok": support_ok, "attrition": attrition, "falsifier": falsifier,
              "descriptive_not_decision_bearing": desc,
              "research_only": True, "accepted_label": False}
    res_path = os.path.join(HERE, "result_confirmatory.json")
    with open(res_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    print(json.dumps({k: result[k] for k in ("verdict", "verdict_label", "primary_L2_vs_L1_holdout",
                                             "honest_n", "falsifier", "attrition")},
                     indent=1, sort_keys=True))
    return [csv_path, res_path]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["baseline", "synthetic", "confirmatory"])
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--rerun-reason", default=None)
    args = ap.parse_args(argv)
    record = {"command": "python " + " ".join([os.path.relpath(__file__, REPO)] + argv),
              "stage": args.stage, "stamp_utc_from_date_u": args.stamp,
              "rerun_reason": args.rerun_reason}
    inputs = {"PREREG.md": PREREG, "FREEZE.log": FREEZE, "evaluate.py": os.path.abspath(__file__),
              "engine/vol_noise_robust_realized.py": MODULE,
              "engine/vol_forecast.py": BASELINE_CODE}
    if args.stage in ("baseline", "confirmatory"):
        inputs["data/coinbase/btc_hourly.parquet"] = HOURLY
    if args.stage == "baseline":
        inputs["data/coinbase/btc_daily.parquet"] = DAILY
    input_shas = {k: sha256_file(v) for k, v in inputs.items() if os.path.exists(v)}
    record["inputs_sha256"] = input_shas
    outputs: list[str] = []
    code = 0
    try:
        fz = frozen_hash()
        if fz is None or fz != input_shas.get("PREREG.md"):
            print("REFUSED: sha256(PREREG.md) does not match FREEZE.log", file=sys.stderr)
            code = 3
        else:
            bad = [p for p, h in EXPECTED.items() if p in inputs.values() and sha256_file(p) != h]
            if bad:
                print(f"REFUSED: input hash mismatch {bad}", file=sys.stderr)
                code = 4
            elif args.stage == "confirmatory" and prior_confirmatory_ok() and not (
                    args.rerun_reason and "PREREG_AMENDMENT" in args.rerun_reason):
                print("REFUSED: confirmatory already ran; rerun needs PREREG_AMENDMENT reason",
                      file=sys.stderr)
                code = 5
            elif args.stage == "baseline":
                outputs = stage_baseline()
            elif args.stage == "synthetic":
                outputs = stage_synthetic()
            else:
                outputs = stage_confirmatory(input_shas["PREREG.md"],
                                             {k: v for k, v in input_shas.items()
                                              if k.startswith("data/") or k.startswith("engine/")})
    except Exception as exc:  # crash is logged, never hidden
        print(f"CRASH: {type(exc).__name__}: {exc}", file=sys.stderr)
        code = 1
    record["exit_code"] = code
    record["outputs_sha256"] = {os.path.basename(p): sha256_file(p) for p in outputs}
    append_run(record)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
