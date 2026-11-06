from __future__ import annotations

"""Q17 single pre-registered evaluation (see PREREG.md; frozen hash in FREEZE.log).

Refuses to run unless sha256(PREREG.md) equals the FREEZE.log hash, every input matches
the sha256 table frozen in PREREG.md, and the challenger module matches its frozen
(normalized) hash.  Computes the incumbent vs challenger comparison exactly as
pre-registered, writes small result files under results/, and appends one record
(command, exit code, PREREG hash, input and output sha256s) to RUNS.log.

Research tooling only; nothing in the product imports this file.
"""

import contextlib
import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q17_env as env  # noqa: E402

env.install_config_stub()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PREREG = env.HERE / "PREREG.md"
FREEZE = env.HERE / "FREEZE.log"
AMENDMENT = env.HERE / "PREREG_AMENDMENT.md"
RESULTS = env.HERE / "results"
OUT_PRIMARY = RESULTS / "primary_results.json"
OUT_MONTH = RESULTS / "per_month.csv"
OUT_PAIR = RESULTS / "per_pair.csv"

FACTOR_LABELS = ["value", "profitability", "quality", "investment", "payout", "low_vol",
                 "low_beta", "short_interest", "accruals", "sue"]
TRAIN_FRACTION = 0.4
LEG_COVERAGE_MIN = 0.50
BLOCK_LEN = 3
N_REPS = 2000
BOOT_SEED = 17
M5_NBOOT = 50
R_BAR = 0.80
R_CI_UPPER_BAR = 1.00
M1_TOLERANCE = 0.01
COVERAGE_TOLERANCE = 0.05
MIN_VALID_PAIRS = 12
MAX_FALLBACK_SHARE = 0.20
MODULE_REL = "engine/factor_stable_whitening.py"
VERDICT_TOKEN = re.compile(r"\(recorded verdict: [A-Z_]+\)")


class RefusedToRun(RuntimeError):
    pass


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_prereg_hash() -> str:
    m = re.search(r"PREREG\.md sha256=([0-9a-f]{64})", FREEZE.read_text())
    if not m:
        raise RefusedToRun("FREEZE.log carries no PREREG.md sha256")
    return m.group(1)


def frozen_input_table() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in PREREG.read_text().splitlines():
        m = re.match(r"^\| ([^|]+?) \| ([0-9a-f]{64}) \|$", line.strip())
        if m:
            key = m.group(1).replace(" (normalized)", "").strip()
            out[key] = m.group(2)
    return out


def amended_table() -> dict[str, str]:
    """Rows of PREREG_AMENDMENT.md, admitted only when its sha256 matches FREEZE.log.

    A FREEZE.log amendment line without the file (or the reverse) refuses to run."""
    m = re.search(r"PREREG_AMENDMENT\.md sha256=([0-9a-f]{64})", FREEZE.read_text())
    if not AMENDMENT.exists() and not m:
        return {}
    if not AMENDMENT.exists() or not m:
        raise RefusedToRun("PREREG_AMENDMENT.md and its FREEZE.log line must both exist")
    actual = env.sha256(AMENDMENT)
    if actual != m.group(1):
        raise RefusedToRun(f"PREREG_AMENDMENT.md sha256 {actual} != FREEZE.log {m.group(1)}")
    out: dict[str, str] = {}
    for line in AMENDMENT.read_text().splitlines():
        r = re.match(r"^\| ([^|]+?) \| ([0-9a-f]{64}) \|$", line.strip())
        if r:
            out[r.group(1).replace(" (normalized)", "").strip()] = r.group(2)
    return out


def normalized_module_hash() -> str:
    text = (env.Q / MODULE_REL).read_text()
    return _sha_text(VERDICT_TOKEN.sub("(recorded verdict: __VERDICT__)", text))


def guard() -> tuple[str, dict[str, str]]:
    actual = env.sha256(PREREG)
    expected = frozen_prereg_hash()
    if actual != expected:
        raise RefusedToRun(f"PREREG.md sha256 {actual} != FREEZE.log {expected}")
    table = frozen_input_table()
    amended = amended_table()
    unknown = set(amended) - set(table)
    if unknown:
        raise RefusedToRun(f"amendment names rows absent from the frozen table: {sorted(unknown)}")
    table.update(amended)
    now = env.input_hashes()
    now[MODULE_REL] = normalized_module_hash()
    bad = {k: (v, now.get(k)) for k, v in table.items() if now.get(k) != v}
    if bad or len(table) < 18:
        raise RefusedToRun(f"input hashes differ from the frozen table: {bad} (n={len(table)})")
    return actual, now


# ---------------------------------------------------------------------------
def moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    k = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=k)
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def inc_fit(fsw, Zn: np.ndarray):
    p = Zn.shape[1]
    Zc = Zn[~np.isnan(Zn).any(axis=1)]
    if p < 2 or len(Zc) < fsw.support_rule(p):
        return None, {"status": "fallback", "complete_rows": int(len(Zc))}
    C = np.corrcoef(Zc, rowvar=False)
    lam = np.linalg.eigvalsh((C + C.T) / 2.0)
    W = fsw.incumbent_weights(Zc)
    return W, {"status": "transformed", "complete_rows": int(len(Zc)),
               "raw_min_eig": float(lam.min()),
               "applied_max_amplification": float(1.0 / math.sqrt(max(lam.min(), 1e-6)))}


def stb_fit(fsw, Zn: np.ndarray):
    p = Zn.shape[1]
    Mf = (~np.isnan(Zn)).astype(float)
    counts = Mf.T @ Mf
    if p < 2 or counts.min() < fsw.support_rule(p):
        return None, {"status": "fallback", "min_pair_count": int(counts.min()) if p else 0}
    est = fsw.estimate_correlation(Zn)
    W = fsw.whitening_matrix(est.corr_used)
    d = est.diagnostics
    return W, {"status": "transformed", "min_pair_count": d["min_pair_count"],
               "raw_min_eig": d["raw_min_eig"], "shrinkage": d["shrinkage"],
               "floor_binding": d["floor_binding"], "unstable": d["unstable"],
               "applied_max_amplification": d["applied_max_amplification"]}


def oot_error(fsw, W: np.ndarray, Zn_next: np.ndarray) -> tuple[float, int]:
    Zc = Zn_next[~np.isnan(Zn_next).any(axis=1)]
    p = Zn_next.shape[1]
    return (fsw.mean_abs_offdiag(Zc @ W) - fsw.independent_noise_floor(len(Zc), p),
            int(len(Zc)))


def evaluate(ef, fo, fsw, br) -> dict:
    closes, saved = br.patch_incumbent(ef)
    try:
        mes = br.month_ends(pd.DatetimeIndex(closes.index))
        tip = closes.index.max()
        if mes and mes[-1] == tip and (tip + pd.Timedelta(days=1)).month == tip.month \
                and (tip + pd.offsets.BDay(1)).month == tip.month:
            mes = mes[:-1]
        frames: list[pd.DataFrame | None] = []
        for d in mes:
            tab = br.table_frame(ef.compute_factors(asof=d.date(), universe="broad"))
            if tab is None:
                frames.append(None)
                continue
            legs = [c for c in FACTOR_LABELS if c in tab.columns]
            frames.append(tab[legs].astype(float))
    finally:
        br.unpatch_incumbent(ef, saved)

    n_dates = len(mes)
    n_train = int(math.floor(TRAIN_FRACTION * n_dates))
    train_idx = list(range(n_train))
    test_idx = list(range(n_train, n_dates))

    # leg set: training dates only
    legset = []
    for leg in FACTOR_LABELS:
        ok = True
        for i in train_idx:
            F = frames[i]
            if F is None or leg not in F.columns or float(F[leg].notna().mean()) < LEG_COVERAGE_MIN:
                ok = False
                break
        if ok:
            legset.append(leg)
    p = len(legset)
    base = {"n_dates": n_dates, "first_date": str(mes[0].date()), "last_date": str(mes[-1].date()),
            "n_train": n_train, "train_dates": [str(mes[0].date()), str(mes[n_train - 1].date())],
            "test_dates": [str(mes[n_train].date()), str(mes[-1].date())],
            "n_test_months": len(test_idx), "legset": legset, "p": p}
    if p < 2:
        return dict(base, verdict="INSUFFICIENT_DATA",
                    missing_input="fewer than two legs with >=50% coverage on every training date")

    months: dict[int, dict] = {}
    for i in test_idx:
        F = frames[i]
        if F is None:
            months[i] = {"asof": str(mes[i].date()), "status": "no_table"}
            continue
        Fp = F.reindex(columns=legset)
        cohort = Fp.notna().any(axis=1)
        Fp = Fp[cohort]
        Zn = fsw.standardize(Fp).to_numpy()
        n_meas = Fp.notna().sum(axis=1).to_numpy()
        partial = (n_meas >= 1) & (n_meas < p)
        W_inc, d_inc = inc_fit(fsw, Zn)
        W_stb, d_stb = stb_fit(fsw, Zn)
        inc_out = fo.orthogonalize(Fp)
        restate = fsw.incumbent_reference_transform(Fp)
        restate_diff = float(np.nanmax(np.abs(inc_out.to_numpy() - restate.to_numpy())))
        if restate_diff > 1e-9:
            raise AssertionError(f"incumbent restatement drift {restate_diff} at {mes[i].date()}")
        res = fsw.stable_whiten(Fp)
        inc_full = np.isfinite(inc_out.to_numpy()).all(axis=1) if d_inc["status"] == "transformed" \
            else np.zeros(len(Fp), bool)
        stb_full = np.isfinite(res.values.to_numpy()).all(axis=1) if res.whitened \
            else np.zeros(len(Fp), bool)
        row_full_label = (res.row_status.to_numpy() == fsw.ROW_FULL)
        nul_n = int((~np.isnan(Zn).any(axis=1)).sum())
        rec = {
            "asof": str(mes[i].date()), "status": "ok", "n_rows": int(len(Fp)),
            "complete_rows": nul_n, "partial_rows": int(partial.sum()),
            "coverage_per_leg": {c: round(float(Fp[c].notna().mean()), 4) for c in legset},
            "inc": d_inc, "stb": dict(d_stb, method_status=res.status),
            "inc_coverage_all_legs": float(inc_full.mean()),
            "stb_coverage_all_legs": float(stb_full.mean()),
            "inc_partial_presented_complete": int((partial & inc_full).sum()),
            "stb_partial_presented_complete": int((partial & stb_full & row_full_label).sum()),
            "stb_partial_labelled": int((res.row_status.to_numpy() == fsw.ROW_PARTIAL).sum()),
            "restatement_max_abs_diff": restate_diff,
            "inc_insample_offdiag_excess": (fsw.mean_abs_offdiag(inc_out.to_numpy())
                                            - fsw.independent_noise_floor(len(Fp), p)),
            "stb_insample_offdiag_excess": (fsw.mean_abs_offdiag(res.values.to_numpy())
                                            - fsw.independent_noise_floor(len(Fp), p)),
        }
        for m in ("incumbent", "stable"):
            b = fsw.bootstrap_instability(Fp, method=m, n_boot=M5_NBOOT, seed=i)
            rec["m5_" + m] = {k: b.get(k) for k in ("status", "n_boot", "output_rel_change_median",
                                                    "transform_rel_change_median",
                                                    "output_unstable")}
        months[i] = {"rec": rec, "Zn": Zn, "W_inc": W_inc, "W_stb": W_stb}

    pairs = []
    for a, b in zip(test_idx[:-1], test_idx[1:]):
        ma, mb = months.get(a, {}), months.get(b, {})
        if not ("rec" in ma and "rec" in mb):
            continue
        if any(x is None for x in (ma["W_inc"], ma["W_stb"], mb["W_inc"], mb["W_stb"])):
            continue
        e_inc, n_c = oot_error(fsw, ma["W_inc"], mb["Zn"])
        e_stb, _ = oot_error(fsw, ma["W_stb"], mb["Zn"])
        pairs.append({"t": str(mes[a].date()), "t1": str(mes[b].date()),
                      "drift_inc": fsw.transform_drift(ma["W_inc"], mb["W_inc"]),
                      "drift_stb": fsw.transform_drift(ma["W_stb"], mb["W_stb"]),
                      "m1_excess_inc": e_inc, "m1_excess_stb": e_stb, "n_complete_t1": n_c})

    month_recs = [m["rec"] if "rec" in m else m for m in (months[i] for i in test_idx)]
    fb_inc = sum(1 for r in month_recs if r.get("status") != "ok" or r["inc"]["status"] != "transformed")
    fb_stb = sum(1 for r in month_recs if r.get("status") != "ok" or r["stb"]["status"] != "transformed")
    n_valid = len(pairs)
    attr = {"test_months": len(test_idx), "fallback_or_missing_inc": fb_inc,
            "fallback_or_missing_stb": fb_stb, "valid_pairs": n_valid,
            "possible_pairs": max(len(test_idx) - 1, 0)}
    if n_valid < MIN_VALID_PAIRS or fb_inc > MAX_FALLBACK_SHARE * len(test_idx) \
            or fb_stb > MAX_FALLBACK_SHARE * len(test_idx):
        return dict(base, verdict="INSUFFICIENT_DATA", attrition=attr, per_month=month_recs,
                    per_pair=pairs, missing_input="valid test pairs/support below the PREREG minimum")

    D_inc = np.array([q["drift_inc"] for q in pairs])
    D_stb = np.array([q["drift_stb"] for q in pairs])
    E_dif = np.array([q["m1_excess_stb"] - q["m1_excess_inc"] for q in pairs])
    R = float(D_stb.mean() / D_inc.mean())
    m1_diff = float(E_dif.mean())
    rng = np.random.default_rng(BOOT_SEED)
    Rb, Mb = [], []
    for _ in range(N_REPS):
        idx = moving_block_indices(n_valid, BLOCK_LEN, rng)
        Rb.append(D_stb[idx].mean() / D_inc[idx].mean())
        Mb.append(E_dif[idx].mean())
    R_ci = [float(np.quantile(Rb, 0.025)), float(np.quantile(Rb, 0.975))]
    M_ci = [float(np.quantile(Mb, 0.025)), float(np.quantile(Mb, 0.975))]
    cov_inc = float(np.mean([r["inc_coverage_all_legs"] for r in month_recs]))
    cov_stb = float(np.mean([r["stb_coverage_all_legs"] for r in month_recs]))
    c1 = bool(R <= R_BAR and R_ci[1] < R_CI_UPPER_BAR)
    c2 = bool(m1_diff <= M1_TOLERANCE)
    c3 = bool(cov_stb >= cov_inc - COVERAGE_TOLERANCE)
    verdict = "KEEP" if (c1 and c2 and c3) else "REJECT"

    def med(key, sub):
        v = [r[sub][key] for r in month_recs if r[sub].get(key) is not None]
        return float(np.median(v)) if v else None

    return dict(
        base, verdict=verdict, attrition=attr,
        honest_n={"test_pairs": n_valid, "non_overlapping_blocks": n_valid // BLOCK_LEN,
                  "block_len": BLOCK_LEN, "reps": N_REPS, "seed": BOOT_SEED},
        primary={"R_mean_drift_ratio": R, "R_ci95": R_ci, "mean_drift_inc": float(D_inc.mean()),
                 "mean_drift_stb": float(D_stb.mean()), "median_pair_ratio":
                 float(np.median(D_stb / D_inc)), "condition_1_drift": c1},
        guardrails={"m1_excess_diff_mean_stb_minus_inc": m1_diff, "m1_diff_ci95": M_ci,
                    "m1_excess_inc_mean": float(np.mean([q["m1_excess_inc"] for q in pairs])),
                    "m1_excess_stb_mean": float(np.mean([q["m1_excess_stb"] for q in pairs])),
                    "condition_2_m1": c2, "coverage_inc_mean": cov_inc,
                    "coverage_stb_mean": cov_stb, "condition_3_coverage": c3},
        descriptive={
            "inc_raw_min_eig_median": med("raw_min_eig", "inc"),
            "inc_amplification_median": med("applied_max_amplification", "inc"),
            "stb_amplification_median": med("applied_max_amplification", "stb"),
            "stb_shrinkage_median": med("shrinkage", "stb"),
            "stb_floor_binding_months": int(sum(1 for r in month_recs if r["stb"].get("floor_binding"))),
            "stb_unstable_months": int(sum(1 for r in month_recs if r["stb"].get("unstable"))),
            "inc_partial_presented_complete_total": int(sum(r["inc_partial_presented_complete"]
                                                            for r in month_recs)),
            "stb_partial_presented_complete_total": int(sum(r["stb_partial_presented_complete"]
                                                            for r in month_recs)),
            "m5_inc_output_rel_change_median": med("output_rel_change_median", "m5_incumbent"),
            "m5_stb_output_rel_change_median": med("output_rel_change_median", "m5_stable"),
            "m5_inc_unstable_months": int(sum(1 for r in month_recs
                                              if r["m5_incumbent"].get("output_unstable"))),
            "m5_stb_unstable_months": int(sum(1 for r in month_recs
                                              if r["m5_stable"].get("output_unstable"))),
            "inc_insample_offdiag_excess_median": float(np.median(
                [r["inc_insample_offdiag_excess"] for r in month_recs])),
            "stb_insample_offdiag_excess_median": float(np.median(
                [r["stb_insample_offdiag_excess"] for r in month_recs])),
            "restatement_max_abs_diff": float(max(r["restatement_max_abs_diff"] for r in month_recs)),
            "identity_transform_drift": 0.0,
        },
        per_month=month_recs, per_pair=pairs)


def _json_default(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(f"not serializable: {type(o)}")


def write_outputs(payload: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    per_month = payload.pop("per_month", [])
    per_pair = payload.pop("per_pair", [])
    OUT_PRIMARY.write_text(json.dumps(payload, indent=1, sort_keys=True, default=_json_default) + "\n")
    cols = ["asof", "n_rows", "complete_rows", "partial_rows", "inc_status", "inc_raw_min_eig",
            "inc_amp", "stb_status", "stb_method_status", "stb_min_pair_count", "stb_raw_min_eig",
            "stb_shrinkage", "stb_floor_binding", "stb_amp", "inc_cov", "stb_cov",
            "inc_partial_presented_complete", "stb_partial_labelled", "inc_insample_excess",
            "stb_insample_excess", "m5_inc_out_change", "m5_stb_out_change"] + \
        ["cov_" + c for c in payload.get("legset", [])]
    with open(OUT_MONTH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in per_month:
            if r.get("status") != "ok":
                w.writerow([r.get("asof")] + [""] * (len(cols) - 1))
                continue
            w.writerow([r["asof"], r["n_rows"], r["complete_rows"], r["partial_rows"],
                        r["inc"]["status"], r["inc"].get("raw_min_eig"),
                        r["inc"].get("applied_max_amplification"), r["stb"]["status"],
                        r["stb"]["method_status"], r["stb"].get("min_pair_count"),
                        r["stb"].get("raw_min_eig"), r["stb"].get("shrinkage"),
                        r["stb"].get("floor_binding"), r["stb"].get("applied_max_amplification"),
                        r["inc_coverage_all_legs"], r["stb_coverage_all_legs"],
                        r["inc_partial_presented_complete"], r["stb_partial_labelled"],
                        r["inc_insample_offdiag_excess"], r["stb_insample_offdiag_excess"],
                        r["m5_incumbent"]["output_rel_change_median"],
                        r["m5_stable"]["output_rel_change_median"]] +
                       [r["coverage_per_leg"][c] for c in payload.get("legset", [])])
    with open(OUT_PAIR, "w", newline="") as f:
        keys = ["t", "t1", "drift_inc", "drift_stb", "m1_excess_inc", "m1_excess_stb", "n_complete_t1"]
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for q in per_pair:
            w.writerow(q)


def main() -> tuple[int, str, dict]:
    prereg_sha, before = guard()
    listing_before = env.dir_listing()
    import engine.factor_orthogonal as fo  # noqa: PLC0415
    import engine.factor_stable_whitening as fsw  # noqa: PLC0415
    import engine.equity_factors as ef  # noqa: PLC0415
    import baseline_repro as br  # noqa: PLC0415

    t0 = time.perf_counter()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        payload = evaluate(ef, fo, fsw, br)
    after = env.input_hashes()
    after[MODULE_REL] = normalized_module_hash()
    if before != after or listing_before != env.dir_listing():
        raise RuntimeError("input bytes or watched data listing changed during the run")
    payload["runtime_seconds"] = round(time.perf_counter() - t0, 1)
    payload["prereg_sha256"] = prereg_sha
    payload["prereg_amendment_sha256"] = env.sha256(AMENDMENT) if AMENDMENT.exists() else None
    payload["inputs_sha256"] = before
    payload["incumbent_stdout_lines"] = len(buf.getvalue().splitlines())
    write_outputs(payload)
    summary = {k: payload.get(k) for k in ("verdict", "legset", "primary", "guardrails", "attrition",
                                           "honest_n")}
    print(json.dumps(summary, indent=1, default=_json_default))
    return 0, prereg_sha, before


if __name__ == "__main__":
    code, err, pre, prereg_sha = 1, None, {}, None
    try:
        code, prereg_sha, pre = main()
    except RefusedToRun as exc:
        err, code = f"REFUSED: {exc}", 2
    except Exception:  # noqa: BLE001
        err, code = traceback.format_exc(limit=8), 1
    outs = {str(p.relative_to(env.Q)): env.sha256(p)
            for p in (OUT_PRIMARY, OUT_MONTH, OUT_PAIR) if p.exists() and code == 0}
    env.append_run({"script": "evaluate.py", "exit_code": code,
                    "prereg_sha256": prereg_sha or (env.sha256(PREREG) if PREREG.exists() else None),
                    "prereg_amendment_sha256": env.sha256(AMENDMENT) if AMENDMENT.exists() else None,
                    "inputs_sha256": pre, "outputs_sha256": outs, "error": err})
    if err:
        sys.stderr.write(err + "\n")
    sys.exit(code)
