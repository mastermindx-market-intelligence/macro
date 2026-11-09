from __future__ import annotations

"""Q07 frozen evaluation: fitted log-HAR challenger vs simple controls (research only).

Modes:
  --mode reproduce-baseline   equality of the module's incumbent with engine.vol_forecast.har_vol
  --mode evaluate             the single pre-registered comparison (PREREG.md §4–§9)

Refuses to run unless sha256(PREREG.md) equals the hash in FREEZE.log, and unless every
input file matches its pre-registered sha256. Every run (including refusals) is appended to
RUNS.log with command, exit code, input and output sha256s.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from engine import vol_fitted_har as M  # noqa: E402

PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"
DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data/yahoo")
VOL_FORECAST = ROOT / "engine" / "vol_forecast.py"
MODULE = ROOT / "engine" / "vol_fitted_har.py"

EXPECTED_SHA = {
    "SPY": "6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152",
    "QQQ": "5e851c16c54a1bfe190cdc454cf88b17b2a23601d6e15897f74be2ad19bebf0c",
    "XLB": "cd763ad4b83cc832a5a58a62959eb0ff547c46d3ef103a83b06c977ef9407ab3",
    "XLC": "b3d5e72afd435545b7aa894c7dfeaf9edb5d41a26fb37711a45ad13a26c911b7",
    "XLE": "eab5678e5a69f8b3bb1af61ecf469c3ecd235544e054b00a65bbecbaae1ad17e",
    "XLF": "f6a5a43d2b1c2124c6d80067f7effd612273864d6ce40813e1196b003be0b707",
    "XLI": "d8a4fdf3405fe8c2538d5c19c3567c7284f26181c066b5fb4f616f9cf73f507a",
    "XLK": "3e24eab5f93be8a5de354bf25e5fe3142328a62c37ab47f0c8445f218de7ad33",
    "XLP": "d765ac7968609bb6fc0f0d8ec5b14594cd03f07e6ebc592cef7915247186fde5",
    "XLRE": "2a4eaef85fd4af868fd2b70ce5d04e0828cb0df1d9e255ba14be3c39bd7b7581",
    "XLU": "d2eb4a95c202b2982af2ce6ebf3ca47c9bc24b03c80445bfea46e7bec7a93f41",
    "XLV": "57b5a45c1c91754dc03d78ab44b6df7317de2ad86c73f513520278c4cfe0a07c",
    "XLY": "1f7c6916dbc04436b5bbfebdd4fa00a66d6f8e26982c789881fd0094f1fb1514",
}
ASSETS = list(EXPECTED_SHA)
BALANCED = [a for a in ASSETS if a not in ("XLC", "XLRE")]
HOLDOUT_START = pd.Timestamp("2008-01-02")  # frozen in PREREG §5
H_PRIMARY = 21
BAR = 0.03
MIN_BLOCKS = 30
MIN_ASSETS = 5
N_BOOT = 2000
SEED = 20261008
ROLL_WINDOW = 1260
CONTROLS = ("C0", "C1", "C2", "C3")
MODELS = ("H",) + CONTROLS


class Refusal(RuntimeError):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str:
    for line in FREEZE.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        for tok in line.split():
            if tok.startswith("sha256="):
                return tok.split("=", 1)[1]
    raise Refusal("FREEZE.log carries no sha256= line")


def check_freeze() -> str:
    want = frozen_hash()
    got = sha256_file(PREREG)
    if got != want:
        raise Refusal(f"PREREG.md sha256 {got} != frozen {want}; refusing to run")
    return got


def load_close(asset: str) -> pd.Series:
    p = DATA / f"{asset}.parquet"
    got = sha256_file(p)
    if got != EXPECTED_SHA[asset]:
        raise Refusal(f"{p} sha256 {got} != pre-registered {EXPECTED_SHA[asset]}")
    s = pd.read_parquet(p, columns=["close"])["close"].astype(float)
    s = s[~s.index.duplicated(keep="last")].sort_index().dropna()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    return s


# ------------------------------------------------------------------ baseline reproduction
def reproduce_baseline() -> dict:
    from engine import vol_forecast as VF

    out = {"assets": {}, "max_abs_diff": 0.0, "nan_pattern_equal": True}
    for a in ASSETS:
        c = load_close(a)
        mine = M.incumbent_blend_vol(c)
        ref = VF.har_vol(c)
        same_nan = bool((mine.isna() == ref.isna()).all())
        diff = float(np.nanmax(np.abs(mine.to_numpy() - ref.to_numpy())))
        out["assets"][a] = {"rows": int(len(c)), "first": str(c.index[0].date()),
                            "last": str(c.index[-1].date()), "max_abs_diff": diff,
                            "nan_pattern_equal": same_nan, "n_nan": int(ref.isna().sum())}
        out["max_abs_diff"] = max(out["max_abs_diff"], diff)
        out["nan_pattern_equal"] &= same_nan
    out["reproduced"] = bool(out["max_abs_diff"] <= 1e-12 and out["nan_pattern_equal"])
    if not out["reproduced"]:
        raise Refusal(f"baseline not reproduced: {out['max_abs_diff']}")
    return out


# ------------------------------------------------------------------ panel construction
def asset_frame(close: pd.Series, h: int, floor: float, window: int | None = None,
                with_intervals: bool = False) -> pd.DataFrame:
    r = M.log_returns(close)
    tgt = M.forward_target(r, h)
    y = M.require_label(tgt)
    har = M.har_forecast_path(r, h, floor=floor, window=window)
    c0 = M.incumbent_blend_vol(close) ** 2
    df = pd.DataFrame({
        "y": y,
        "H": har["forecast"],
        "C0": c0,
        "C1": M.trailing_msr(r, M.PERSISTENCE_WINDOW),
        "C2": M.ewma_variance(r),
        "C3": M.scaled_forecast_path(c0, tgt, h),
        "n_train": har["n_train"],
    })
    if with_intervals:
        for mdl in MODELS:
            iv = M.empirical_interval_path(df[mdl], tgt, h, floor=floor)
            df[f"{mdl}_lo"] = iv["lo"]
            df[f"{mdl}_hi"] = iv["hi"]
    return df


def build_panel(closes: dict[str, pd.Series], h: int, floor: float, window: int | None = None,
                with_intervals: bool = False) -> tuple[dict[str, pd.DataFrame], dict]:
    frames, support = {}, {}
    for a, c in closes.items():
        df = asset_frame(c, h, floor, window, with_intervals)
        hold = df[df.index >= HOLDOUT_START]
        ymask = hold["y"].notna()
        fin = hold[list(MODELS)].notna().all(axis=1)
        support[a] = {
            "holdout_origins": int(len(hold)),
            "drop_target_not_matured": int((~ymask).sum()),
            "drop_incomplete_model": int((ymask & ~fin).sum()),
            "drop_no_har_fit": int((ymask & hold["H"].isna()).sum()),
            "kept": int((ymask & fin).sum()),
            "first_kept": str(hold.index[(ymask & fin).to_numpy()][0].date()) if (ymask & fin).any() else None,
        }
        frames[a] = hold[ymask & fin]
    return frames, support


def daily_loss(frames: dict[str, pd.DataFrame], model: str, loss: str, floor: float,
               assets: list[str] | None = None) -> pd.Series:
    cols = {}
    for a, df in frames.items():
        if assets is not None and a not in assets:
            continue
        if loss == "qlike":
            v = M.qlike(df["y"], df[model], floor)
        elif loss == "log":
            v = M.log_loss(df["y"], df[model], floor)
        else:
            v = M.abs_vol_loss(df["y"], df[model])
        cols[a] = pd.Series(np.asarray(v, dtype=float), index=df.index)
    return pd.DataFrame(cols).sort_index().mean(axis=1)


def compare(frames, floor, h, assets=None, loss="qlike") -> dict:
    block = max(63, 6 * h)
    lh = daily_loss(frames, "H", loss, floor, assets)
    res = {}
    for ctrl in CONTROLS:
        lc = daily_loss(frames, ctrl, loss, floor, assets)
        j = pd.concat([lc, lh], axis=1).dropna()
        bs = M.paired_block_bootstrap(j.iloc[:, 0].to_numpy(), j.iloc[:, 1].to_numpy(),
                                      block_len=block, n_boot=N_BOOT, seed=SEED)
        bs["hac_t"] = M.newey_west_tstat((j.iloc[:, 0] - j.iloc[:, 1]).to_numpy(), lag=2 * h)
        bs["n_target_windows_nonoverlap"] = int(len(j) // h)
        res[ctrl] = bs
    return res


def n_assets(frames) -> int:
    return int(sum(1 for df in frames.values() if len(df) > 0))


def honest_blocks(frames, h) -> int:
    dates = sorted(set().union(*[set(df.index) for df in frames.values()]))
    return int(len(dates) // max(63, 6 * h))


# ------------------------------------------------------------------ evaluation
def evaluate() -> dict:
    closes = {a: load_close(a) for a in ASSETS}
    RESULTS.mkdir(exist_ok=True)

    # primary confirmatory trial at every declared floor (requirement 4)
    by_floor = {}
    primary_frames = None
    primary_support = None
    for fl in M.FLOOR_SENSITIVITY:
        frames, support = build_panel(closes, H_PRIMARY, fl, with_intervals=(fl == M.DEFAULT_FLOOR))
        comp = compare(frames, fl, H_PRIMARY)
        nb, na = honest_blocks(frames, H_PRIMARY), n_assets(frames)
        dec = M.decide(comp, BAR, nb, MIN_BLOCKS, na, MIN_ASSETS, floor_flip=False)
        n_below = int(sum(int((df["y"] < fl).sum()) for df in frames.values()))
        by_floor[repr(fl)] = {"decision_at_floor": dec, "comparisons": comp, "honest_n_blocks": nb,
                              "n_assets": na, "holdout_targets_below_floor": n_below,
                              "mean_qlike": {m_: float(daily_loss(frames, m_, "qlike", fl).mean()) for m_ in MODELS}}
        if fl == M.DEFAULT_FLOOR:
            primary_frames, primary_support = frames, support

    prim = by_floor[repr(M.DEFAULT_FLOOR)]
    floor_flip = len({v["decision_at_floor"] for v in by_floor.values()}) > 1
    verdict = M.decide(prim["comparisons"], BAR, prim["honest_n_blocks"], MIN_BLOCKS,
                       prim["n_assets"], MIN_ASSETS, floor_flip=floor_flip)

    fl = M.DEFAULT_FLOOR
    # per-asset and per-year descriptive tables
    rows = []
    for a, df in primary_frames.items():
        row = {"asset": a, "n": int(len(df))}
        for m_ in MODELS:
            row[f"qlike_{m_}"] = float(np.mean(M.qlike(df["y"], df[m_], fl)))
        for c in CONTROLS:
            row[f"rel_vs_{c}"] = 1.0 - row["qlike_H"] / row[f"qlike_{c}"]
        rows.append(row)
    per_asset = pd.DataFrame(rows)
    per_asset.to_csv(RESULTS / "per_asset.csv", index=False, float_format="%.6g")

    dl = pd.DataFrame({m_: daily_loss(primary_frames, m_, "qlike", fl) for m_ in MODELS}).dropna()
    per_year = dl.groupby(dl.index.year).mean()
    per_year["n_sessions"] = dl.groupby(dl.index.year).size()
    for c in CONTROLS:
        per_year[f"rel_vs_{c}"] = 1.0 - per_year["H"] / per_year[c]
    per_year.index.name = "year"
    per_year.to_csv(RESULTS / "per_year.csv", float_format="%.6g")
    years_won = {c: int((per_year[f"rel_vs_{c}"] > 0).sum()) for c in CONTROLS}

    # coverage of 80% variance-scale intervals (descriptive)
    cov = {}
    for m_ in MODELS:
        hit, tot = 0, 0
        for df in primary_frames.values():
            ok = df[f"{m_}_lo"].notna() & df[f"{m_}_hi"].notna()
            d = df[ok]
            hit += int(((d["y"] >= d[f"{m_}_lo"]) & (d["y"] <= d[f"{m_}_hi"])).sum())
            tot += int(len(d))
        cov[m_] = {"nominal": 0.8, "coverage": hit / tot if tot else math.nan, "n": tot}

    # secondary descriptive diagnostics (cannot change the verdict)
    secondary = {
        "secondary_losses_h21": {
            loss: {c: {k: v for k, v in r_.items() if k in ("rel_improvement", "rel_ci", "diff_ci")}
                   for c, r_ in compare(primary_frames, fl, H_PRIMARY, loss=loss).items()}
            for loss in ("log", "absvol")
        },
        "balanced_panel_h21": {c: {k: r_[k] for k in ("rel_improvement", "rel_ci", "diff_ci", "honest_n_blocks")}
                               for c, r_ in compare(primary_frames, fl, H_PRIMARY, assets=BALANCED).items()},
    }
    rf, _ = build_panel(closes, H_PRIMARY, fl, window=ROLL_WINDOW)
    secondary["rolling_1260_har_h21"] = {c: {k: r_[k] for k in ("rel_improvement", "rel_ci", "diff_ci")}
                                         for c, r_ in compare(rf, fl, H_PRIMARY).items()}
    for hh in (5, 63):
        fr, _ = build_panel(closes, hh, fl)
        secondary[f"h{hh}"] = {c: {k: r_[k] for k in ("rel_improvement", "rel_ci", "diff_ci", "honest_n_blocks", "hac_t")}
                               for c, r_ in compare(fr, fl, hh).items()}

    # HAR coefficient snapshot at the last refit (descriptive)
    coef = {}
    for a, c in closes.items():
        r = M.log_returns(c)
        X = M.har_features(r).to_numpy()
        y = M.forward_target(r, H_PRIMARY).values.to_numpy()
        last_c = int(M.cutoff_grid(len(r))[-1])
        fit = M.fit_log_har(X, y, last_c, H_PRIMARY)
        coef[a] = None if fit is None else {"coef": [round(x, 4) for x in fit.coef],
                                            "smear": round(fit.smear, 4), "n_train": fit.n_train}

    primary = {
        "study": "Q07 fitted log-HAR vs simple controls",
        "label": M.LABEL_DAILY_CC,
        "horizon": H_PRIMARY,
        "holdout_start": str(HOLDOUT_START.date()),
        "last_origin": str(max(df.index.max() for df in primary_frames.values()).date()),
        "bar": BAR,
        "verdict": verdict,
        "floor_flip": floor_flip,
        "by_floor": by_floor,
        "years_won_by_H": years_won,
        "n_years": int(len(per_year)),
        "coverage_80": cov,
        "support": primary_support,
        "sessions_total": int(len(dl)),
        "sessions_with_fewer_than_13_assets": int(
            (pd.DataFrame({a: pd.Series(1, index=df.index) for a, df in primary_frames.items()})
             .sort_index().notna().sum(axis=1) < len(ASSETS)).sum()),
        "complexity": {"H": "4 coef + 1 smear per asset per 21-session refit",
                       "C0": 0, "C1": 0, "C2": "0 (lambda fixed 0.94)", "C3": "1 level factor per refit"},
        "har_last_refit": coef,
        "production_effects": M.production_effects(verdict),
    }
    (RESULTS / "primary_results.json").write_text(json.dumps(primary, indent=1, sort_keys=True))
    (RESULTS / "secondary_results.json").write_text(json.dumps(secondary, indent=1, sort_keys=True))
    return primary


# ------------------------------------------------------------------ run log
def append_run(cmd: str, code: int, outputs: list[Path], note: str) -> None:
    inputs = {str(PREREG.name): sha256_file(PREREG), str(FREEZE.name): sha256_file(FREEZE),
              "evaluate.py": sha256_file(Path(__file__)), "engine/vol_fitted_har.py": sha256_file(MODULE),
              "engine/vol_forecast.py": sha256_file(VOL_FORECAST)}
    for a in ASSETS:
        p = DATA / f"{a}.parquet"
        inputs[f"data/yahoo/{a}.parquet"] = sha256_file(p) if p.exists() else None
    outs = {str(p.relative_to(HERE)): sha256_file(p) for p in outputs if p.exists()}
    prior = 0
    if RUNS.exists():
        prior = sum(1 for ln in RUNS.read_text().splitlines() if ln.startswith("{"))
    entry = {"run": prior + 1, "command": cmd, "exit_code": code, "note": note,
             "inputs": inputs, "outputs": outs}
    with open(RUNS, "a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("reproduce-baseline", "evaluate"), required=True)
    args = ap.parse_args()
    cmd = " ".join([sys.executable] + sys.argv)
    outputs: list[Path] = []
    code, note = 0, ""
    try:
        check_freeze()
        if args.mode == "reproduce-baseline":
            RESULTS.mkdir(exist_ok=True)
            res = reproduce_baseline()
            p = RESULTS / "baseline_reproduction.json"
            p.write_text(json.dumps(res, indent=1, sort_keys=True))
            outputs = [p]
            note = f"baseline reproduced max_abs_diff={res['max_abs_diff']:.3g}"
        else:
            res = evaluate()
            outputs = [RESULTS / n for n in ("primary_results.json", "secondary_results.json",
                                             "per_asset.csv", "per_year.csv")]
            note = f"verdict={res['verdict']}"
        print(note)
    except Refusal as exc:
        code, note = 3, f"REFUSED: {exc}"
        print(note, file=sys.stderr)
    except Exception as exc:  # recorded, then re-signalled through the exit code
        code, note = 1, f"ERROR: {type(exc).__name__}: {exc}"
        print(note, file=sys.stderr)
    append_run(cmd, code, outputs, note)
    return code


if __name__ == "__main__":
    sys.exit(main())
