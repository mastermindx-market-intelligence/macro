from __future__ import annotations

__doc__ = """Q14-T1 evaluator: horizon-matched variance premium vs IV/RV controls.

Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log.
Appends every invocation (command, exit code, input and output sha256s) to RUNS.log.

Modes:
  baseline  descriptive incumbent reproduction (not decision-bearing)
  compare   the single pre-registered comparison (decision-bearing)

Research only: writes small JSON receipts beside this file; wires nothing.
"""

import argparse
import hashlib
import json
import math
import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../Q14
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
INPUTS = {
    "gspc": DATA / "yahoo" / "_GSPC.parquet",
    "vixcls": DATA / "fred" / "VIXCLS.parquet",
    "vix_yahoo": DATA / "yahoo" / "_VIX.parquet",
}
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"

H = 30
TRAIN_END = "2011-12-31"
EMBARGO_DAYS = 31
BLOCK = 63
N_BOOT = 2000
SEED = 14
HAC_LAGS = 42
BAR = 0.05
MIN_WINDOWS_HOLDOUT = 36
MIN_WINDOWS_TRAIN = 60


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_run(cmd: str, code: int, inputs: dict, outputs: dict, note: str = "") -> None:
    rec = {"command": cmd, "exit_code": code, "inputs_sha256": inputs,
           "outputs_sha256": outputs, "note": note}
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def frozen_hash() -> str | None:
    if not FREEZE.exists():
        return None
    m = re.search(r"PREREG\.md sha256=([0-9a-f]{64})", FREEZE.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def load_series():
    import numpy as np
    import pandas as pd

    def as_dated(df: pd.DataFrame, col: str) -> pd.Series:
        if isinstance(df.index, pd.DatetimeIndex):
            idx = df.index
        elif "date" in df.columns:
            idx = pd.DatetimeIndex(pd.to_datetime(df["date"]))
        else:
            raise SystemExit("REFUSED: no date index in input")
        s = pd.Series(df[col].to_numpy(dtype=float), index=idx.tz_localize(None) if idx.tz else idx)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        return s

    g = pd.read_parquet(INPUTS["gspc"])
    close = as_dated(g, "close")
    close_price = as_dated(g, "close_price") if "close_price" in g.columns else None
    v = as_dated(pd.read_parquet(INPUTS["vixcls"]), "vix_close")
    vy = as_dated(pd.read_parquet(INPUTS["vix_yahoo"]), "close")
    close = close[np.isfinite(close.to_numpy())]
    return close, close_price, v, vy


def build_frame():
    """All features/labels per pre-registration. Returns (frame, attrition)."""
    import numpy as np
    import pandas as pd
    sys.path.insert(0, str(ROOT))
    from engine import vol_forecast as vf
    from engine import vol_horizon_variance_premium as vp

    close, close_price, vix, vix_y = load_series()
    day = (close.index.normalize() - pd.Timestamp("1970-01-01")).days.to_numpy().astype(np.int64)
    r = vp.daily_log_returns(close.to_numpy())
    rv_fwd = vp.forward_realized_variance(r, day, H)
    rv_tr = vp.trailing_realized_variance(r, day, H)
    har = vf.har_vol(close).to_numpy()
    f_h = vp.daily_variance_to_horizon_variance(har ** 2, H)
    cone = vf.cone_vol_ann(close).to_numpy()
    fwd21 = vf.forward_vol_ann(close, 21).to_numpy()
    df = pd.DataFrame({"day": day, "close": close.to_numpy(), "rv_fwd": rv_fwd, "rv_trail": rv_tr,
                       "f_h": f_h, "cone_vol_ann": cone, "fwd_vol_ann_21": fwd21}, index=close.index)
    df["vix"] = vix.reindex(df.index)
    df["vix_yahoo"] = vix_y.reindex(df.index)
    att = {}
    df = df[df.index >= pd.Timestamp("1990-01-02")]
    att["gspc_days_from_1990"] = int(len(df))
    m_vix = np.isfinite(df["vix"].to_numpy())
    att["dropped_vix_missing"] = int((~m_vix).sum())
    df = df[m_vix]
    m_tr = np.isfinite(df["rv_trail"].to_numpy())
    att["dropped_trailing_incomplete"] = int((~m_tr).sum())
    df = df[m_tr]
    m_lab = np.isfinite(df["rv_fwd"].to_numpy())
    att["dropped_label_incomplete"] = int((~m_lab).sum())
    df = df[m_lab]
    m_har = np.isfinite(df["f_h"].to_numpy())
    att["dropped_har_nan"] = int((~m_har).sum())
    df = df[m_har].copy()
    att["cohort_rows"] = int(len(df))
    df["iv2_h"] = vp.vol_index_to_horizon_variance(df["vix"].to_numpy(), H)
    if close_price is not None:
        cp = close_price.reindex(df.index).to_numpy()
        agree = np.isfinite(cp) & (np.abs(cp / df["close"].to_numpy() - 1.0) <= 1e-6)
        att["close_vs_close_price_rows_agreeing_rel_1e-6"] = int(agree.sum())
        att["close_vs_close_price_rows_compared"] = int(np.isfinite(cp).sum())
    return df, att, vp


def honest_windows(day, h: int = H) -> int:
    n, nxt = 0, None
    for d in day:
        if nxt is None or d >= nxt:
            n += 1
            nxt = d + h + 1
    return n


def run_baseline(df, att, vp) -> dict:
    import numpy as np
    vrp_pts = df["vix"].to_numpy() - df["cone_vol_ann"].to_numpy() * 100.0
    prem_hv = df["iv2_h"].to_numpy() - df["f_h"].to_numpy()
    cone, fwd = df["cone_vol_ann"].to_numpy(), df["fwd_vol_ann_21"].to_numpy()
    m = np.isfinite(cone) & np.isfinite(fwd)
    r2 = float(np.corrcoef(cone[m], fwd[m])[0, 1] ** 2)
    vy = df["vix_yahoo"].to_numpy()
    mv = np.isfinite(vy)
    diff = np.abs(vy[mv] - df["vix"].to_numpy()[mv])
    return {
        "mode": "baseline", "decision_bearing": False, "authority": "none",
        "cohort_first": str(df.index[0].date()), "cohort_last": str(df.index[-1].date()),
        "attrition": att,
        "incumbent_vrp_vol_points": {
            "definition": "VIX - cone_vol_ann*100 (engine/vol_regime.py), volatility points",
            "mean": float(np.mean(vrp_pts)), "median": float(np.median(vrp_pts)),
            "frac_positive": float(np.mean(vrp_pts > 0)), "n_rows": int(vrp_pts.size)},
        "incumbent_cone_vs_forward_vol_21_r2": {"r2": r2, "n_rows": int(m.sum()),
                                                 "note": "squared Pearson corr, full cohort, descriptive"},
        "unit_mismatch_receipt": {
            "corr_volpts_vs_horizon_variance_premium": float(np.corrcoef(vrp_pts, prem_hv)[0, 1]),
            "sign_disagreement_rate": float(np.mean(np.sign(vrp_pts) != np.sign(prem_hv))),
            "rate_volpts_positive_and_hv_premium_negative": float(np.mean((vrp_pts > 0) & (prem_hv < 0))),
            "rate_volpts_negative_and_hv_premium_positive": float(np.mean((vrp_pts < 0) & (prem_hv > 0))),
        },
        "vixcls_vs_yahoo_vix": {"rows_compared": int(mv.sum()), "max_abs_diff": float(diff.max()),
                                 "rows_abs_diff_gt_0p05": int((diff > 0.05).sum())},
    }


def run_compare(df, att, vp) -> dict:
    import numpy as np
    import pandas as pd
    basis_i = vp.HorizonBasis(H, "calendar365", session_close="cboe_1615_et")
    basis_p = vp.HorizonBasis(H, "calendar365", session_close="nyse_1600_et")
    cov_i = {"tail_strikes": "strip_truncated",
             "overnight": "risk_neutral_horizon_includes_overnight",
             "source": "FRED VIXCLS (CBOE 30cd strip, vendor-computed)", "jump_correction": "none"}
    cov_p = vp.realized_coverage("close_to_close")  # label leg: sum sq log returns, not demeaned
    # Forecast leg receipt (amendment A1 / audit M3): har_vol is a rolling std (ddof=0) of
    # simple pct returns, i.e. demeaned within each window, scaled x252x30/365.
    cov_f = dict(cov_p, demeaned=True, returns="simple_pct",
                 estimator="rolling std ddof=0 of pct returns, equal-weight HAR lags (2,5,22,66), x252x30/365")
    recs_ante, recs_post = [], []
    for d, iv2, f, y in zip(df["day"].to_numpy(), df["iv2_h"].to_numpy(),
                            df["f_h"].to_numpy(), df["rv_fwd"].to_numpy()):
        il = vp.ImpliedLeg(float(iv2), basis_i, "strip", int(d), cov_i)
        fl = vp.PhysicalLeg(float(f), basis_p, "forecast", int(d), int(d), cov_f,
                            method="incumbent engine.vol_forecast.har_vol lags (2,5,22,66), equal weight")
        ll = vp.PhysicalLeg(float(y), basis_p, "forward_label", int(d), int(d) + H, cov_p,
                            method="sum sq log returns (t, t+30cd]")
        recs_ante.append(vp.build_premium(il, fl, acknowledge_session_offset=True))
        recs_post.append(vp.ex_post_premium(il, ll, acknowledge_session_offset=True))
    vp.assemble_history(recs_ante)
    vp.assemble_history(recs_post)
    prem_hat = np.array([r.premium_variance for r in recs_ante])
    prem_post = np.array([r.premium_variance for r in recs_post])

    idx = df.index
    train = idx <= pd.Timestamp(TRAIN_END)
    last_train_day = int(df["day"].to_numpy()[train][-1])
    test = df["day"].to_numpy() >= last_train_day + EMBARGO_DAYS
    att = dict(att)
    att["dropped_embargo_gap"] = int((~train & ~test).sum())
    att["train_rows"] = int(train.sum())
    att["holdout_rows"] = int(test.sum())

    y = df["rv_fwd"].to_numpy()
    iv2, rvt, f = df["iv2_h"].to_numpy(), df["rv_trail"].to_numpy(), df["f_h"].to_numpy()
    xc = np.column_stack([iv2, rvt])
    xa = np.column_stack([iv2, rvt, prem_hat])
    day = df["day"].to_numpy()
    support = {
        "train_first": str(idx[train][0].date()), "train_last": str(idx[train][-1].date()),
        "holdout_first": str(idx[test][0].date()), "holdout_last": str(idx[test][-1].date()),
        "train_nonoverlap_30cd_windows": honest_windows(day[train]),
        "holdout_nonoverlap_30cd_windows": honest_windows(day[test]),
        "train_63d_blocks": int(math.floor(train.sum() / BLOCK)),
        "holdout_63d_blocks": int(math.floor(test.sum() / BLOCK)),
    }
    if (support["holdout_nonoverlap_30cd_windows"] < MIN_WINDOWS_HOLDOUT
            or support["train_nonoverlap_30cd_windows"] < MIN_WINDOWS_TRAIN):
        return {"mode": "compare", "verdict": "INSUFFICIENT_DATA", "support": support, "attrition": att,
                "authority": "none"}

    res = vp.incremental_comparison(y[train], xc[train], xa[train], y[test], xc[test], xa[test],
                                    block=BLOCK, n_boot=N_BOOT, seed=SEED, hac_lags=HAC_LAGS,
                                    practical_bar=BAR, n_segments=3)
    beta_c = np.array(res["beta_controls"])
    beta_a = np.array(res["beta_augmented"])
    fc = vp.ols_predict(beta_c, xc[test])
    fa = vp.ols_predict(beta_a, xa[test])

    diag = {}
    for name, cols in (("iv2_only", [iv2]), ("rv_trail_only", [rvt]), ("f_only", [f])):
        x = np.column_stack(cols)
        b = vp.ols_fit(x[train], y[train])
        p = vp.ols_predict(b, x[test])
        diag[name] = {"beta": [float(v) for v in b], "holdout_mse": float(np.mean((y[test] - p) ** 2))}
    diag["nonpositive_forecasts_controls"] = int(np.sum(fc <= 0))
    diag["nonpositive_forecasts_augmented"] = int(np.sum(fa <= 0))

    def decomp(mask):
        return {"mean_iv2_h": float(iv2[mask].mean()), "mean_f_h": float(f[mask].mean()),
                "mean_rv_fwd": float(y[mask].mean()),
                "mean_premium_hat": float(prem_hat[mask].mean()),
                "mean_premium_ex_post": float(prem_post[mask].mean()),
                "median_premium_ex_post": float(np.median(prem_post[mask])),
                "frac_premium_ex_post_negative": float(np.mean(prem_post[mask] < 0)),
                "mean_premium_ex_post_ann_variance": float(prem_post[mask].mean() * 365.0 / H)}

    verdict = "KEEP" if res["keep_predictive_upgrade"] else "REJECT"
    out = {
        "mode": "compare", "trial": "Q14-T1", "decision_bearing": True, "authority": "none",
        "verdict_predictive_upgrade": verdict,
        "verdict_measurement": "retained as research-only measurement (horizon-matched receipts)",
        "spec": {"h": H, "train_end": TRAIN_END, "embargo_days": EMBARGO_DAYS, "block": BLOCK,
                 "n_boot": N_BOOT, "seed": SEED, "hac_lags": HAC_LAGS, "bar": BAR,
                 "controls": ["1", "iv2_h", "rv_trail"],
                 "augmented": ["1", "iv2_h", "rv_trail", "premium_hat"]},
        "support": support, "attrition": att, "result": res, "diagnostics": diag,
        "decomposition": {"train": decomp(train), "holdout": decomp(test)},
        "receipt_example_last_holdout_row": recs_ante[int(np.flatnonzero(test)[-1])].to_dict(),
    }
    vp.assert_no_authority(out)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("baseline", "compare"), required=True)
    a = ap.parse_args(argv)
    cmd = "python3 evaluate.py " + " ".join(shlex.quote(x) for x in (argv if argv is not None else sys.argv[1:]))
    pre = sha256_file(PREREG) if PREREG.exists() else None
    fz = frozen_hash()
    inputs = {"PREREG.md": pre, "evaluate.py": sha256_file(Path(__file__).resolve())}
    if pre is None or fz is None or pre != fz:
        print(f"REFUSED: PREREG.md sha256 {pre} != FREEZE.log {fz}", file=sys.stderr)
        append_run(cmd, 2, inputs, {}, "refused: prereg hash mismatch")
        return 2
    for k, p in INPUTS.items():
        inputs[str(p.relative_to(DATA))] = sha256_file(p)
    inputs["engine/vol_horizon_variance_premium.py"] = sha256_file(ROOT / "engine" / "vol_horizon_variance_premium.py")
    inputs["engine/vol_forecast.py"] = sha256_file(ROOT / "engine" / "vol_forecast.py")
    try:
        df, att, vp = build_frame()
        out = run_baseline(df, att, vp) if a.mode == "baseline" else run_compare(df, att, vp)
    except Exception as exc:  # crash before outcomes: logged, nonzero
        append_run(cmd, 1, inputs, {}, f"crash: {type(exc).__name__}: {exc}")
        raise
    out["inputs_sha256"] = inputs
    dest = HERE / f"result_{a.mode}.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_run(cmd, 0, inputs, {dest.name: sha256_file(dest)})
    print(json.dumps({k: out[k] for k in out if k not in ("receipt_example_last_holdout_row",)},
                     indent=1, sort_keys=True)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
