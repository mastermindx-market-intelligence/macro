from __future__ import annotations

# Q08 frozen evaluation — regularized correlation vs the incumbent sample estimator.
#
# Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log,
# and unless sha256(--data) equals the preregistered data vintage.
# Appends every run (command, exit code, input and output sha256s) to RUNS.log.
#
# Usage (repo root of the staging tree on PYTHONPATH):
#     python evaluate.py --mode baseline   # incumbent reproduction only
#     python evaluate.py --mode evaluate   # the single preregistered evaluation
#     optional: --data /path/to/_factor_legs.parquet (sha256-guarded; default below)

import argparse
import hashlib
import json
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[2]
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
DEFAULT_DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data/breadth/_factor_legs.parquet")
DATA = DEFAULT_DATA  # rebound from --data in main(); the sha256 guard applies either way
EXPECTED_DATA_SHA = "cc3476e61b50e8eda312b11393fa2231fde587a821d011a8dd58d32987fe94bd"
COLUMNS = ["low_vol", "quality", "size", "value"]  # sorted, fixed cohort

TRAIN = 252
TRAIN_SENS = 60
HORIZON = 21
FIRST_ORIGIN = 252
SEED = 20261008
B_DIFF = 10000
MBB_BLOCK = 3
ALPHA_FAMILY = 0.05
N_CHALLENGERS = 3
BAR = 0.005
HAC_LAG = 3
PR_B_ORIGIN = 200
PR_B_FINAL = 1000
PR_MEAN_BLOCK = 10.0
PR_LEVEL = 0.90
MIN_BLOCKS = 12
MAX_UNAVAILABLE_BLOCKS = 2


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str:
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        if line.startswith("PREREG_SHA256="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("FREEZE.log has no PREREG_SHA256 line")


def append_run(cmd: str, code: int, inputs: dict, outputs: dict, note: str) -> None:
    rec = {
        "command": cmd,
        "exit_code": code,
        "inputs_sha256": inputs,
        "outputs_sha256": outputs,
        "note": note,
    }
    with open(RUNS, "a", encoding="utf-8") as fh:
        fh.write("RUN " + json.dumps(rec, sort_keys=True) + "\n")


def load_panel():
    import pandas as pd

    df = pd.read_parquet(DATA)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"INSUFFICIENT_DATA: missing columns {missing}")
    df = df.sort_index()
    return df[COLUMNS]


def reproduce_incumbent(df) -> dict:
    """Run the REAL incumbent _build_factors_block on a factor_series.json-shaped
    document built from the legs, and compare with the module replica."""
    from engine import covariance_shrinkage_diagnostics as csd
    from engine.neuralweb import covariance_spine as spine

    dates = [str(d)[:10] for d in df.index]
    spread = {}
    for col in COLUMNS:
        r = df[col].to_numpy(dtype=float)
        fin = np.flatnonzero(np.isfinite(r))
        nav: list = [None] * len(r)
        first = int(fin[0])
        level = 1.0
        if first > 0:
            nav[first - 1] = 1.0
        for i in range(first, len(r)):
            if not np.isfinite(r[i]):
                raise SystemExit(f"interior gap in {col} at row {i}")
            level *= 1.0 + r[i]
            nav[i] = level
        spread[col] = nav
    doc = {"factors": list(COLUMNS) + ["composite"],
           "chart_data": {"dates": dates, "spread": spread}}
    scratch = Path(tempfile.mkdtemp(prefix="q08_scratch_incumbent_"))  # system temp, outside the package
    try:
        target = scratch / "site" / "factordata"
        target.mkdir(parents=True)
        (target / "factor_series.json").write_text(json.dumps(doc), encoding="utf-8")
        missing: list[str] = []
        inc = spine._build_factors_block(scratch, missing)
    finally:
        shutil.rmtree(scratch)
    X = df.dropna().to_numpy(dtype=float)[-TRAIN:]
    rep = csd.incumbent_algorithm_pr(X)
    R, _ = csd.sample_correlation(X)
    return {
        "incumbent_output": inc,
        "incumbent_missing_inputs": missing,
        "module_replica": rep,
        "module_sample_pr_4dp": round(csd.participation_ratio(R), 4),
        "module_sample_share_4dp": round(csd.dominant_share(R), 4),
        "exact_match_pr": inc is not None
        and inc.get("effective_factor_bets_pr") == rep["effective_factor_bets_pr"],
        "exact_match_share": inc is not None
        and inc.get("dominant_factor_pc_share") == rep["dominant_factor_pc_share"],
        "n_obs_used": None if inc is None else inc.get("n_obs_used"),
    }


def contrast_stats(d: np.ndarray, seed: int) -> dict:
    from engine import covariance_shrinkage_diagnostics as csd
    from engine.validation import newey_west_tstat

    level = 1.0 - ALPHA_FAMILY / N_CHALLENGERS
    ci = csd.block_bootstrap_mean_ci(d, block_len=MBB_BLOCK, B=B_DIFF, seed=seed, level=level)
    hac = newey_west_tstat(d, lags=HAC_LAG)
    return {
        "mean": ci["mean"],
        "bonferroni_level": level,
        "lo": ci["lo"],
        "hi": ci["hi"],
        "share_boot_le_0": ci.get("share_boot_le_0"),
        "n_blocks_honest": ci["n_blocks_honest"],
        "hac_t": None if hac is None else hac.get("t"),
        "hac_p": None if hac is None else hac.get("p"),
        "hac_se": None if hac is None else hac.get("se"),
        "hac_lags": HAC_LAG,
    }


def contest(X: np.ndarray, train: int) -> dict:
    from engine import covariance_shrinkage_diagnostics as csd

    rows = csd.rolling_origin_losses(X, train=train, horizon=HORIZON, first_origin=FIRST_ORIGIN)
    names = list(csd.ESTIMATORS)
    unavailable = {n: sum(1 for r in rows if r[n]["status"] != "ok") for n in names}
    ok_rows = [r for r in rows if all(r[n]["status"] == "ok" for n in names)]
    per_block = []
    for r in rows:
        rec = {"block": r["block"], "eval_rows": r["eval_rows"]}
        for n in names:
            rec[n] = {k: r[n].get(k) for k in ("status", "stein", "frobenius", "pr", "intensity", "reason")}
        per_block.append(rec)
    out = {"train": train, "K_total": len(rows), "K_evaluable": len(ok_rows),
           "unavailable_by_estimator": unavailable, "per_block": per_block, "challengers": {}}
    base_stein = np.array([r["sample"]["stein"] for r in ok_rows])
    base_frob = np.array([r["sample"]["frobenius"] for r in ok_rows])
    out["baseline_mean_stein"] = float(base_stein.mean()) if ok_rows else None
    for i, n in enumerate(names[1:]):
        st = np.array([r[n]["stein"] for r in ok_rows])
        fr = np.array([r[n]["frobenius"] for r in ok_rows])
        d = base_stein - st
        s = contrast_stats(d, SEED + i)
        s["mean_frobenius_contrast"] = float(np.mean(base_frob - fr))
        s["mean_intensity"] = (
            None if ok_rows[0][n].get("intensity") is None
            else float(np.mean([r[n]["intensity"] for r in ok_rows]))
        )
        s["blocks_won"] = int(np.sum(d > 0))
        s["passes_bar"] = bool(s["mean"] >= BAR)
        s["passes_ci"] = bool(s["lo"] is not None and s["lo"] > 0)
        s["frobenius_not_worse"] = bool(s["mean_frobenius_contrast"] >= 0)
        s["qualifies"] = s["passes_bar"] and s["passes_ci"] and s["frobenius_not_worse"]
        out["challengers"][n] = s
    return out


def pr_uncertainty(X: np.ndarray) -> dict:
    from engine import covariance_shrinkage_diagnostics as csd

    names = list(csd.ESTIMATORS)
    per_origin = {n: [] for n in names}
    t = FIRST_ORIGIN
    k = 0
    while t + HORIZON <= X.shape[0]:
        Xtr = X[t - TRAIN:t]
        for j, n in enumerate(names):
            iv = csd.bootstrap_pr_interval(Xtr, n, B=PR_B_ORIGIN, mean_block=PR_MEAN_BLOCK,
                                           seed=SEED + 100 * k + j, level=PR_LEVEL)
            per_origin[n].append({kk: iv[kk] for kk in ("point", "lo", "hi", "width", "n_failed")})
        t += HORIZON
        k += 1
    final = {}
    Xf = X[-TRAIN:]
    for j, n in enumerate(names):
        iv = csd.bootstrap_pr_interval(Xf, n, B=PR_B_FINAL, mean_block=PR_MEAN_BLOCK,
                                       seed=SEED + 7 + j, level=PR_LEVEL)
        R, meta = csd.ESTIMATORS[n](Xf)
        final[n] = {**iv, "matrix": np.round(R, 4).tolist(), "intensity": meta.get("intensity"),
                    "dominant_share": csd.dominant_share(R)}
    summary = {}
    for n in names:
        pts = np.array([r["point"] for r in per_origin[n]])
        wid = np.array([r["width"] for r in per_origin[n]])
        summary[n] = {"point_min": float(pts.min()), "point_max": float(pts.max()),
                      "point_std": float(pts.std(ddof=1)), "median_width": float(np.median(wid)),
                      "n_failed_total": int(sum(r["n_failed"] for r in per_origin[n]))}
    return {"level": PR_LEVEL, "mean_block": PR_MEAN_BLOCK, "B_origin": PR_B_ORIGIN,
            "B_final": PR_B_FINAL, "bounds": [1.0, float(X.shape[1])],
            "final_origin": final, "across_origins": summary, "per_origin": per_origin}


def decide(primary: dict) -> dict:
    unav = max(primary["unavailable_by_estimator"].values())
    if primary["K_evaluable"] < MIN_BLOCKS or unav > MAX_UNAVAILABLE_BLOCKS:
        return {"verdict": "INSUFFICIENT_DATA", "winner": None}
    qual = {n: s for n, s in primary["challengers"].items() if s["qualifies"]}
    if not qual:
        return {"verdict": "REJECT", "winner": None}
    win = max(qual, key=lambda n: qual[n]["mean"])
    return {"verdict": "KEEP", "winner": win}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("baseline", "evaluate"), required=True)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA,
                    help="factor-legs parquet; refused unless its sha256 equals the preregistered vintage")
    args = ap.parse_args()
    global DATA
    DATA = args.data.resolve()
    cmd = " ".join(shlex.quote(a) for a in [sys.executable] + sys.argv)
    module = STAGE / "engine" / "covariance_shrinkage_diagnostics.py"
    inputs = {}
    outputs: dict = {}
    code = 1
    note = ""
    try:
        got, want = sha256(PREREG), frozen_hash()
        inputs["PREREG.md"] = got
        if got != want:
            note = f"REFUSED: PREREG.md sha256 {got} != FREEZE.log {want}"
            print(note, file=sys.stderr)
            code = 3
            return code
        inputs["data/breadth/_factor_legs.parquet"] = sha256(DATA)
        if inputs["data/breadth/_factor_legs.parquet"] != EXPECTED_DATA_SHA:
            note = "REFUSED: input data sha256 differs from the preregistered vintage"
            print(note, file=sys.stderr)
            code = 4
            return code
        inputs["engine/covariance_shrinkage_diagnostics.py"] = sha256(module)
        inputs["engine/neuralweb/covariance_spine.py"] = sha256(STAGE / "engine/neuralweb/covariance_spine.py")
        inputs["engine/validation.py"] = sha256(STAGE / "engine/validation.py")
        inputs["evaluate.py"] = sha256(Path(__file__).resolve())
        amendment = HERE / "PREREG_AMENDMENT.md"
        if amendment.is_file():
            inputs["PREREG_AMENDMENT.md"] = sha256(amendment)

        df = load_panel()
        if args.mode == "baseline":
            rep = reproduce_incumbent(df)
            out = HERE / "baseline_reproduction.json"
            out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            outputs[out.name] = sha256(out)
            note = f"baseline reproduction exact_match_pr={rep['exact_match_pr']} exact_match_share={rep['exact_match_share']}"
            print(json.dumps(rep, indent=1, sort_keys=True))
            code = 0 if (rep["exact_match_pr"] and rep["exact_match_share"]) else 2
            return code

        from engine import covariance_shrinkage_diagnostics as csd

        values = {c: list(df[c].to_numpy(dtype=float)) for c in COLUMNS}
        specs = {c: csd.SeriesSpec(c, "long_short", "decimal_return", "daily_close") for c in COLUMNS}
        panel = csd.prepare_panel(values, specs, min_obs=TRAIN + MIN_BLOCKS * HORIZON, max_obs=None)
        if panel["status"] != "ok":
            res = {"verdict": "INSUFFICIENT_DATA", "reason": panel["reason"]}
        else:
            X = panel["X"]
            complete_dates = [str(d)[:10] for d, ok in zip(df.index, df.notna().all(axis=1)) if ok]
            primary = contest(X, TRAIN)
            sens = contest(X, TRAIN_SENS)
            pru = pr_uncertainty(X)
            dec = decide(primary)
            res = {
                "schema": "research.q08.evaluation.v1",
                "verdict": dec["verdict"],
                "winner": dec["winner"],
                "bar_nats_per_day": BAR,
                "attrition": panel["attrition"],
                "complete_case_span": [complete_dates[0], complete_dates[-1]],
                "eval_span": [complete_dates[FIRST_ORIGIN],
                              complete_dates[FIRST_ORIGIN + primary["K_total"] * HORIZON - 1]],
                "honest_n_blocks": primary["K_evaluable"],
                "primary": {k: v for k, v in primary.items() if k != "per_block"},
                "sensitivity_train60": {k: v for k, v in sens.items() if k != "per_block"},
                "pr_uncertainty": {k: v for k, v in pru.items() if k != "per_origin"},
            }
            detail = {"primary_per_block": primary["per_block"],
                      "sensitivity_per_block": sens["per_block"],
                      "pr_per_origin": pru["per_origin"]}
            dout = HERE / "results_detail.json"
            dout.write_text(json.dumps(detail, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            outputs[dout.name] = sha256(dout)
        out = HERE / "results.json"
        out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        outputs[out.name] = sha256(out)
        note = f"evaluation verdict={res['verdict']} winner={res.get('winner')}"
        print(json.dumps({k: res[k] for k in ("verdict", "winner") if k in res}))
        code = 0
        return code
    except SystemExit as exc:
        note = note or f"SystemExit: {exc}"
        code = exc.code if isinstance(exc.code, int) else 1
        return code
    except Exception as exc:  # noqa: BLE001 - logged, then re-raised exit code
        note = f"CRASH: {type(exc).__name__}: {exc}"
        print(note, file=sys.stderr)
        code = 1
        return code
    finally:
        append_run(cmd, code, inputs, outputs, note)


if __name__ == "__main__":
    sys.exit(main())
