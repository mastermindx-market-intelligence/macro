from __future__ import annotations

"""Q10 evaluation harness — the single preregistered held-out comparison.

Usage (absolute paths, run once):
    python3.12 evaluate.py reproduce --stamp <date -u>   # baseline reproduction only
    python3.12 evaluate.py evaluate  --stamp <date -u>   # the one holdout evaluation

Refuses to run unless sha256(PREREG.md) equals the hash in FREEZE.log and the three
input hashes equal the preregistered values. Appends every invocation (command, exit
code, input and output sha256s) to RUNS.log. Reads licensed data read-only.
"""

import hashlib
import json
import re
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # the Q10 staging repository root
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
DEEP = DATA / "finra_short_volume" / "panel_deep.parquet"
COLL = DATA / "finra_short_volume" / "panel.parquet"
YAHOO = DATA / "yahoo"
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
MODULE = ROOT / "engine" / "offexchange_conditional_residual.py"
INCUMBENT = ROOT / "engine" / "darkpool_signals.py"

EXPECTED = {
    "panel_deep": "12cc30a28547c30d7effd0991c6dab773b419f36b2fc4cc2133069fc444d5d9f",
    "panel": "63c69080d88baf4bbc039d1906995e37fa7c5078f6370cac46d1a03a7df4f6f4",
    "yahoo_aggregate": "4bed622113b18ee0050db4dc436a29aec75c928b6638568a9062149ec0d6c648",
}
TRAIN_END = pd.Timestamp("2025-06-30")
TEST_START = pd.Timestamp("2025-07-01")
TEST_END = pd.Timestamp("2026-10-08")
BLOCK = 20
BLOCK_SENS = (10, 40)
REPS = 2000
SEED = 20261008
BAR = 0.05
COV_TOL = 0.03
Z = {0.10: 1.6448536269514722, 0.02: 2.3263478740408408, 0.50: 0.6744897501960817}
HEAVY_Z = 1.5


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def frozen_hash() -> str | None:
    if not FREEZE.exists():
        return None
    m = re.search(r"PREREG\.md sha256=([0-9a-f]{64})", FREEZE.read_text())
    return m.group(1) if m else None


def log_run(cmd: str, stamp: str, code: int, inputs: dict, outputs: dict, note: str) -> None:
    rec = {"stamp_utc": stamp, "command": cmd, "exit_code": code, "inputs_sha256": inputs,
           "outputs_sha256": outputs, "note": note}
    with RUNS.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def universe() -> list[str]:
    return sorted(pd.read_parquet(DEEP, columns=["ticker"])["ticker"].astype(str).unique())


def input_hashes() -> dict:
    lines = [f"{tk} {sha_file(YAHOO / f'{tk}.parquet')}" for tk in universe()]
    return {"panel_deep": sha_file(DEEP), "panel": sha_file(COLL),
            "yahoo_aggregate": sha_bytes("\n".join(lines).encode()),
            "prereg": sha_file(PREREG), "module": sha_file(MODULE),
            "incumbent_darkpool_signals": sha_file(INCUMBENT),
            "evaluate": sha_file(Path(__file__).resolve())}


def load_panel() -> pd.DataFrame:
    uni = universe()
    d = pd.read_parquet(DEEP)
    c = pd.read_parquet(COLL)
    f = pd.concat([d, c], ignore_index=True)
    f["date"] = pd.to_datetime(f["date"]).dt.normalize()
    f["ticker"] = f["ticker"].astype(str)
    f = f.drop_duplicates(["date", "ticker"], keep="last")
    f = f[f["ticker"].isin(uni)]
    parts = []
    for tk in uni:
        y = pd.read_parquet(YAHOO / f"{tk}.parquet")
        if "volume" not in y.columns:
            continue
        y.index = pd.to_datetime(y.index).normalize()
        y = y[~y.index.duplicated(keep="last")]
        ft = f[f["ticker"] == tk].set_index("date")[["total_vol"]]
        j = ft.join(y["volume"].rename("cons"), how="inner").dropna()
        j = j.reset_index().rename(columns={"index": "date"})
        j["issuer"] = tk
        parts.append(j)
    p = pd.concat(parts, ignore_index=True)
    p = p.rename(columns={"total_vol": "offex_shares", "cons": "cons_shares"})
    p = p[p["date"] <= TEST_END]
    return p[["date", "issuer", "offex_shares", "cons_shares"]].sort_values(
        ["issuer", "date"], kind="mergesort").reset_index(drop=True)


def split_mask(panel: pd.DataFrame, mod) -> np.ndarray:
    """EXCLUDED_SPLIT mask from the incumbent break rule on each full-vintage valid series."""
    p, status = mod.classify_participation(panel["offex_shares"].to_numpy(), panel["cons_shares"].to_numpy())
    excl = np.zeros(len(panel), dtype=bool)
    for _, idx in panel.groupby("issuer", sort=False).indices.items():
        pv = np.where(status[idx] == mod.VALID, p[idx], np.nan)
        excl[idx] = ~mod.unit_consistent_mask(pv)
    return excl


def baseline_arrays(panel: pd.DataFrame, excl: np.ndarray, mod):
    p, status = mod.classify_participation(panel["offex_shares"].to_numpy(), panel["cons_shares"].to_numpy())
    usable = (status == mod.VALID) & ~excl
    center = np.full(len(panel), np.nan)
    scale = np.full(len(panel), np.nan)
    for _, idx in panel.groupby("issuer", sort=False).indices.items():
        pv = np.where(usable[idx], p[idx], np.nan)
        c, s, _n = mod.incumbent_baseline(pv)
        center[idx] = c
        scale[idx] = s
    return p, usable, center, scale


# ── mode 1: baseline reproduction against the incumbent functions ─────────────

def reproduce(mod) -> dict:
    sys.path.insert(0, str(ROOT))
    from engine.darkpool_signals import trailing_z, usable_history, share_break_index
    panel = load_panel()
    excl = split_mask(panel, mod)
    p, usable, center, scale = baseline_arrays(panel, excl, mod)
    panel = panel.assign(p=p, usable=usable, center=center, scale=scale)
    rng = np.random.default_rng(SEED)
    n_cmp = n_match = n_none_agree = 0
    break_agree = 0
    max_abs = 0.0
    issuers = panel["issuer"].unique()
    for tk in issuers:
        g = panel[panel["issuer"] == tk]
        valid = g[g["p"].notna()]
        b_inc = share_break_index(pd.Series(valid["p"].to_numpy()))
        b_mod = mod.last_level_break(valid["p"].to_numpy())
        break_agree += int(b_inc == b_mod)
        series = pd.Series(valid["p"].to_numpy(), index=valid["date"].to_numpy())
        uh = usable_history(series)
        # pick the last session and two random sessions inside the usable history
        pos = [len(uh) - 1] + list(rng.integers(0, len(uh), size=2)) if len(uh) else []
        for k in pos:
            dt = uh.index[k]
            z_inc = trailing_z(uh.iloc[: k + 1])
            row = g[g["date"] == dt].iloc[0]
            if np.isfinite(row["scale"]):
                z_mod = round(float((row["p"] - row["center"]) / row["scale"]), 2)
            else:
                z_mod = None
            n_cmp += 1
            if z_inc is None and z_mod is None:
                n_none_agree += 1
                n_match += 1
            elif z_inc is not None and z_mod is not None:
                d = abs(z_inc - z_mod)
                max_abs = max(max_abs, d)
                n_match += int(d <= 0.011)
    return {"issuers": int(len(issuers)), "comparisons": n_cmp, "matches": n_match,
            "both_none": n_none_agree, "max_abs_z_diff": max_abs,
            "break_index_agree": break_agree, "rows": int(len(panel)),
            "rows_split_excluded_valid": int((excl & np.isfinite(p)).sum())}


# ── mode 2: the one holdout evaluation ─────────────────────────────────────────

def iscore(lo, hi, y, a):
    return (hi - lo) + (2 / a) * np.maximum(lo - y, 0) + (2 / a) * np.maximum(y - hi, 0)


def evaluate(mod) -> dict:
    panel = load_panel()
    excl = split_mask(panel, mod)
    p, usable, center, scale = baseline_arrays(panel, excl, mod)
    train_rows = (panel["date"] <= TRAIN_END).to_numpy()
    params = mod.fit_conditional_model(panel[train_rows].reset_index(drop=True),
                                       excluded=excl[train_rows])
    params_nm = mod.fit_conditional_model(panel[train_rows].reset_index(drop=True),
                                          excluded=excl[train_rows], use_market=False)
    out = mod.score_panel(panel, params, excluded=excl)
    out_nm = mod.score_panel(panel, params_nm, excluded=excl)
    # both outputs are issuer/date sorted like `panel` (same sort keys, unique rows)
    assert (out["issuer"].to_numpy() == panel["issuer"].to_numpy()).all()
    assert (out["date"].to_numpy() == panel["date"].to_numpy()).all()
    date = panel["date"].to_numpy()
    is_test = (date >= TEST_START.to_datetime64()) & (date <= TEST_END.to_datetime64())
    is_train = date <= TRAIN_END.to_datetime64()
    st = out["status"].to_numpy()
    b_ok = np.isfinite(scale) & usable
    zb = np.where(b_ok, (p - center) / np.where(b_ok, scale, 1.0), np.nan)
    full = st == mod.SCORED_FULL
    common_train = is_train & full & b_ok
    common = is_test & full & b_ok
    # B1 recalibration quantiles from training common support
    qb = {a: (np.quantile(zb[common_train], a / 2), np.quantile(zb[common_train], 1 - a / 2))
          for a in Z}

    def b0(a):
        return (np.clip(center - Z[a] * scale, 0, 1), np.clip(center + Z[a] * scale, 0, 1))

    def b1(a):
        return (np.clip(center + qb[a][0] * scale, 0, 1), np.clip(center + qb[a][1] * scale, 0, 1))

    lab = {0.10: "90", 0.02: "98", 0.50: "50"}

    def mdl(a, o=out):
        return o["lo" + lab[a]].to_numpy(), o["hi" + lab[a]].to_numpy()

    def cov(lo, hi, m):
        return float(np.mean((p[m] >= lo[m]) & (p[m] <= hi[m]))) if m.any() else None

    # attrition
    attr = {k: int(v) for k, v in pd.Series(st[is_test]).value_counts().items()}
    attr_all = {k: int(v) for k, v in pd.Series(st).value_counts().items()}

    # primary: per-session means on common support
    a = 0.10
    lo_m, hi_m = mdl(a)
    lo_0, hi_0 = b0(a)
    lo_1, hi_1 = b1(a)
    sm = iscore(lo_m, hi_m, p, a)
    s0 = iscore(lo_0, hi_0, p, a)
    s1 = iscore(lo_1, hi_1, p, a)
    hit_m = ((p >= lo_m) & (p <= hi_m)).astype(float)
    cdf = pd.DataFrame({"date": date[common], "sm": sm[common], "s0": s0[common], "s1": s1[common],
                        "hit": hit_m[common], "one": 1.0})
    per = cdf.groupby("date").agg(sm=("sm", "mean"), s0=("s0", "mean"), s1=("s1", "mean"),
                                  hit=("hit", "sum"), n=("one", "sum")).sort_index()
    issuers_per_session = cdf.groupby("date").size()
    A, B0, B1 = per["sm"].to_numpy(), per["s0"].to_numpy(), per["s1"].to_numpy()
    H, Nn = per["hit"].to_numpy(), per["n"].to_numpy()

    def red(x, y):
        return 1.0 - x.sum() / y.sum()

    res = {}
    for name, comp in (("H1_vs_B0", B0), ("H2_vs_B1", B1)):
        point = red(A, comp)
        cis = {}
        for blk in (BLOCK,) + BLOCK_SENS:
            bs = mod.moving_block_bootstrap([A, comp], block=blk, reps=REPS, seed=SEED,
                                            stat=lambda s: red(s[0], s[1]))
            cis[str(blk)] = [float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))]
        res[name] = {"relative_reduction": float(point), "ci95_by_block": cis,
                     "mean_is_model": float(A.mean()), "mean_is_competitor": float(comp.mean())}
    cov90 = float(H.sum() / Nn.sum())
    bs_cov = mod.moving_block_bootstrap([H, Nn], block=BLOCK, reps=REPS, seed=SEED,
                                        stat=lambda s: s[0].sum() / s[1].sum())
    cov_ok = abs(cov90 - 0.90) <= COV_TOL
    for name in res:
        lo_ci = res[name]["ci95_by_block"][str(BLOCK)][0]
        res[name]["pass"] = bool(res[name]["relative_reduction"] >= BAR and lo_ci > 0 and cov_ok)
    n_sessions = int(len(per))
    med_issuers = float(issuers_per_session.median()) if n_sessions else 0.0
    if n_sessions < 100 or med_issuers < 50:
        verdict = "INSUFFICIENT_DATA"
    elif res["H1_vs_B0"]["pass"] and res["H2_vs_B1"]["pass"]:
        verdict = "KEEP"
    else:
        verdict = "REJECT"

    # secondary: coverage table
    covtab = {}
    for aa in Z:
        covtab[lab[aa]] = {"model": cov(*mdl(aa), common), "B0": cov(*b0(aa), common),
                           "B1": cov(*b1(aa), common)}
    thin = is_test & (st == mod.SCORED_POOLED)
    thin_tab = {lab[aa]: cov(*mdl(aa), thin) for aa in Z}
    thin_b0_defined = int((thin & b_ok).sum())

    # secondary: flags and market-shift sessions
    dev = out["deviation"].to_numpy()
    nlev = out["n_level"].to_numpy()
    contrib = np.isfinite(dev) & (nlev >= mod.FULL_SUPPORT_OBS)
    sess = pd.DataFrame({"date": date[contrib], "d": dev[contrib]}).groupby("date")["d"].agg(["median", "size"])
    sess = sess[sess["size"] >= mod.MARKET_MIN_ISSUERS]
    tr_sess = sess[sess.index <= TRAIN_END]
    thr = float(np.quantile(np.abs(tr_sess["median"].to_numpy()), 0.95))
    shift_days = set(sess.index[np.abs(sess["median"].to_numpy()) >= thr])
    is_shift = pd.Index(date).isin(list(shift_days))
    pit = out["pit"].to_numpy()
    f_m = common & (pit >= 0.95)
    f_0 = common & (zb >= Z[0.10])
    f_h = common & (zb >= HEAVY_Z)

    def share_shift(f):
        return float(is_shift[f].mean()) if f.any() else None

    flags = {
        "rows_common": int(common.sum()),
        "rate_model_pit_ge_0.95": float(f_m.sum() / common.sum()),
        "rate_B0_z_ge_1.645": float(f_0.sum() / common.sum()),
        "rate_incumbent_heavy_z_ge_1.5": float(f_h.sum() / common.sum()),
        "share_on_shift_sessions_model": share_shift(f_m),
        "share_on_shift_sessions_B0": share_shift(f_0),
        "share_on_shift_sessions_heavy": share_shift(f_h),
        "share_common_rows_on_shift_sessions": float(is_shift[common].mean()),
        "heavy_flags_model_pit_below_0.95": float(np.mean(pit[f_h] < 0.95)) if f_h.any() else None,
        "heavy_flags_on_shift_sessions_model_pit_below_0.95":
            float(np.mean(pit[f_h & is_shift] < 0.95)) if (f_h & is_shift).any() else None,
        "shift_threshold_abs_session_median_d": thr,
        "n_test_shift_sessions": int(sum(1 for d in shift_days if TEST_START <= d <= TEST_END)),
    }

    # secondary: no-market-factor ablation on the same common support (where it scored)
    st_nm = out_nm["status"].to_numpy()
    cm2 = common & (st_nm == mod.SCORED_FULL)
    lo_n, hi_n = out_nm["lo90"].to_numpy(), out_nm["hi90"].to_numpy()
    sn = iscore(lo_n, hi_n, p, 0.10)
    abl = {"rows": int(cm2.sum()), "mean_is_model": float(sm[cm2].mean()),
           "mean_is_no_market": float(sn[cm2].mean()),
           "relative_reduction_model_vs_no_market": float(1 - sm[cm2].sum() / sn[cm2].sum()),
           "cov90_no_market": cov(lo_n, hi_n, cm2), "coef_no_market": list(params_nm.coef)}

    return {
        "verdict": verdict,
        "primary": res,
        "cov90_model_common": cov90,
        "cov90_model_ci95_block20": [float(np.quantile(bs_cov, 0.025)), float(np.quantile(bs_cov, 0.975))],
        "coverage_within_tol": bool(cov_ok),
        "honest_n": {"test_sessions": n_sessions,
                     "nonoverlapping_blocks_20": int(np.ceil(n_sessions / BLOCK)),
                     "issuers_common": int(pd.Series(panel["issuer"].to_numpy()[common]).nunique()),
                     "median_issuers_per_session": med_issuers,
                     "rows_common": int(common.sum())},
        "coverage": covtab,
        "thin_tier": {"rows": int(thin.sum()),
                      "issuers": int(pd.Series(panel["issuer"].to_numpy()[thin]).nunique()),
                      "coverage": thin_tab, "rows_where_B0_defined": thin_b0_defined},
        "attrition_test": attr,
        "attrition_all": attr_all,
        "rows_total": int(len(panel)),
        "rows_invalid_ratio": int((st == mod.INVALID_RATIO).sum()),
        "rows_invalid_denominator": int((st == mod.INVALID_DENOMINATOR).sum()),
        "rows_split_excluded": int((st == mod.EXCLUDED_SPLIT).sum()),
        "rows_valid_p_eq_0": int(np.sum(p == 0)),
        "rows_valid_p_eq_1": int(np.sum(p == 1)),
        "flags": flags,
        "ablation_no_market": abl,
        "coef": {"names": ["intercept", "market", "rel_volume", "rel_volume_pos"],
                 "values": list(params.coef)},
        "train_quantiles_u": dict(zip([str(x) for x in mod.QUANTILE_LEVELS], params.quantiles)),
        "B1_train_quantiles_z": {lab[k]: [float(v[0]), float(v[1])] for k, v in qb.items()},
        "n_train_rows_full": params.n_train_rows,
        "split": {"train_end": str(TRAIN_END.date()), "test": [str(TEST_START.date()), str(TEST_END.date())]},
        "bootstrap": {"block": BLOCK, "sensitivity": list(BLOCK_SENS), "reps": REPS, "seed": SEED},
    }


def main(argv: list[str]) -> int:
    cmd = " ".join(["evaluate.py"] + argv)
    stamp = argv[argv.index("--stamp") + 1] if "--stamp" in argv else "unstamped"
    mode = argv[0] if argv else ""
    inputs: dict = {}
    try:
        fz = frozen_hash()
        cur = sha_file(PREREG)
        if fz is None or fz != cur:
            log_run(cmd, stamp, 2, {"prereg": cur, "frozen": fz}, {}, "REFUSED: PREREG hash != FREEZE.log")
            print("REFUSED: PREREG.md sha256 does not match FREEZE.log", file=sys.stderr)
            return 2
        inputs = input_hashes()
        bad = [k for k, v in EXPECTED.items() if inputs[k] != v]
        if bad:
            log_run(cmd, stamp, 3, inputs, {}, f"REFUSED: input hash mismatch {bad}")
            print(f"REFUSED: input hash mismatch {bad}", file=sys.stderr)
            return 3
        sys.path.insert(0, str(ROOT))
        import engine.offexchange_conditional_residual as mod
        if mode == "reproduce":
            r = reproduce(mod)
            path = HERE / "baseline_repro.json"
        elif mode == "evaluate":
            r = evaluate(mod)
            path = HERE / "results.json"
        else:
            print("usage: evaluate.py {reproduce|evaluate} --stamp <utc>", file=sys.stderr)
            return 64
        body = json.dumps(r, indent=1, sort_keys=True, default=float).encode()
        path.write_bytes(body)
        log_run(cmd, stamp, 0, inputs, {path.name: sha_bytes(body)}, "ok")
        print(json.dumps({"wrote": str(path), "sha256": sha_bytes(body)}))
        return 0
    except Exception as exc:  # logged, then re-signalled through the exit code
        traceback.print_exc()
        log_run(cmd, stamp, 1, inputs, {}, f"ERROR: {type(exc).__name__}: {exc}"[:500])
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
