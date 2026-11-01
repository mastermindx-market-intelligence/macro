"""Q11 evaluation: explicit-duration filter vs incumbent streak (PREREG.md, frozen).

Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log. It also refuses
unless the incumbent engine/darkpool_signals.py equals its PREREG §5 pin and the candidate
module either equals its PREREG §5 pin or passes the amendment-A1 docstring-only check: the
docstring-free AST of the module's evaluation path equals the eval_path_ast_sha256 pinned in a
PREREG_AMENDMENT.md whose own sha256 is witnessed in FREEZE.log. The decision is logged to
RUNS.log as ``module_check``. Appends every
run (including refusals and failures) to RUNS.log with command, exit code and input/output
sha256s. Result files carry no timestamps or code hashes, so a deterministic re-run is
byte-identical; those live in RUNS.log only.

Usage:
    OMP_NUM_THREADS=2 ... nice -n 10 python3.12 evaluate.py
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
Q11_ROOT = HERE.parents[2]
sys.path.insert(0, str(Q11_ROOT))

from engine.darkpool_episode_duration import (  # noqa: E402
    DurationFilterParams,
    episodes_from_path,
    filter_path,
    fit_emission_params,
    robust_activity_z,
)
from engine.darkpool_signals import share_break_index, streak_above_norm  # noqa: E402

DATA = Path("/Users/chriswong/Documents/Cluade/macro-main/data")
PANEL = DATA / "finra_short_volume" / "panel.parquet"
PANEL_DEEP = DATA / "finra_short_volume" / "panel_deep.parquet"
YAHOO = DATA / "yahoo"
CAL_REF = YAHOO / "SPY.parquet"

# ---- frozen design constants (PREREG.md §4, §7, §10, §12, §13) -------------------------
TRAIN_END = "2025-06-30"
MIN_TRAIN_OBS, MIN_TEST_OBS = 300, 150
STREAK_K = 5
K_CURVE = (3, 4, 6, 8)
STREAK_WINDOW = 60
EVAL_MIN_PRIOR = 60
TAU_GRID = tuple(round(0.30 + 0.05 * i, 2) for i in range(14))  # 0.30..0.95
STEP_LEN = 40
WIN_D10 = 10
DELAY_CENSOR = 40
FRAG_WIN = STEP_LEN + 5
POS_OFFSET, POS_SPACING, POS_N, POS_TAIL = 20, 60, 5, 50
INJECTIONS = {"step125": ("step", 1.25), "step150": ("step", 1.50), "spike300": ("spike", 3.0)}
BLOCK = 20
B_BOOT = 2000
SEED = 1101
MIN_NAMES, MIN_REPS = 50, 200
BAR_D10, BAR_DELAY, BAR_SPIKE, BAR_RATE = 0.10, -1.0, 0.02, 1.20


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_stamp() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True,
                          text=True, check=True).stdout.strip()


def frozen_hash() -> str | None:
    p = HERE / "FREEZE.log"
    if not p.exists():
        return None
    found = re.findall(r"PREREG\.md sha256=([0-9a-f]{64})", p.read_text())
    return found[0] if found else None


def append_run(entry: dict) -> None:
    entry = {"utc": utc_stamp(), **entry}
    with open(HERE / "RUNS.log", "a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


# ---- code-integrity guard (PREREG.md §5 pins; PREREG_AMENDMENT.md A1) ---------------------
# The candidate module is accepted only if its sha256 equals the PREREG §5 pin, or, under
# amendment A1, if the evaluation-path AST digest (below) equals the digest pinned in a
# FREEZE.log-witnessed PREREG_AMENDMENT.md. The incumbent must match its PREREG §5 pin exactly.
MODULE_PIN_PREREG = "f3a3134d2abd97b38c79956ba87f8d5978111913351fed744fff98f3701d1189"
INCUMBENT_PIN_PREREG = "4483200a3c09456bb1f26b76850c5f216925d2b0b2e681cc8698608bcb1e95ec"
# Top-level module definitions evaluate.py executes (directly or transitively).
EVAL_PATH_DEFS = frozenset({
    "robust_activity_z", "DurationFilterParams", "exit_hazards", "_t_logpdf", "FilterPath",
    "filter_path", "Episode", "episodes_from_path", "fit_emission_params",
})
EVAL_PATH_CONSTS = frozenset({"MAX_SERIES_LEN", "MAD_SCALE", "_LOG_2PI"})


def _strip_docstrings(node: ast.AST) -> None:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = sub.body
            if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                sub.body = body[1:] or [ast.Pass()]


def eval_path_ast_digest(path: Path) -> str:
    """sha256 of the docstring-free AST of the imports, constants and definitions on the
    evaluation path. Docstrings and definitions evaluate.py never executes do not enter it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    keep: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            keep.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in EVAL_PATH_DEFS:
            keep.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if names and names <= EVAL_PATH_CONSTS:
                keep.append(node)
    mod = ast.Module(body=keep, type_ignores=[])
    _strip_docstrings(mod)
    return hashlib.sha256(ast.dump(mod, include_attributes=False).encode("utf-8")).hexdigest()


def amendment_pin() -> tuple[str | None, str]:
    """(pinned eval-path digest or None, reason). The amendment counts only when its sha256 is
    witnessed in FREEZE.log."""
    amd, frz = HERE / "PREREG_AMENDMENT.md", HERE / "FREEZE.log"
    if not amd.exists():
        return None, "no PREREG_AMENDMENT.md"
    have = sha256_file(amd)
    witnessed = re.findall(r"PREREG_AMENDMENT\.md sha256=([0-9a-f]{64})", frz.read_text()) if frz.exists() else []
    if have not in witnessed:
        return None, f"PREREG_AMENDMENT.md sha256={have} not witnessed in FREEZE.log"
    pins = re.findall(r"eval_path_ast_sha256=([0-9a-f]{64})", amd.read_text())
    if len(pins) != 1:
        return None, "PREREG_AMENDMENT.md must pin exactly one eval_path_ast_sha256"
    return pins[0], f"amendment sha256={have}"


def module_check(code: dict) -> dict:
    mod_path = Q11_ROOT / "engine" / "darkpool_episode_duration.py"
    out = {"module_sha256": code["engine/darkpool_episode_duration.py"],
           "module_pin_prereg": MODULE_PIN_PREREG,
           "incumbent_ok": code["engine/darkpool_signals.py"] == INCUMBENT_PIN_PREREG}
    if out["module_sha256"] == MODULE_PIN_PREREG:
        out.update(module_ok=True, basis="exact PREREG §5 pin")
    else:
        digest = eval_path_ast_digest(mod_path)
        pin, why = amendment_pin()
        out.update(eval_path_ast_sha256=digest, amendment=why, eval_path_ast_pin=pin,
                   module_ok=bool(pin) and digest == pin,
                   basis="eval-path AST equal to amendment A1 pin" if (pin and digest == pin)
                   else "module differs from PREREG pin and no witnessed matching amendment pin")
    out["ok"] = bool(out["module_ok"] and out["incumbent_ok"])
    return out


# ---- data -------------------------------------------------------------------------------

def load_panel() -> pd.DataFrame:
    deep = pd.read_parquet(PANEL_DEEP)
    coll = pd.read_parquet(PANEL)
    for d in (deep, coll):
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    df = pd.concat([deep, coll], ignore_index=True).drop_duplicates(subset=["date", "ticker"], keep="last")
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def load_yahoo_vol(tk: str) -> pd.Series | None:
    p = YAHOO / f"{tk}.parquet"
    if not p.exists():
        return None
    y = pd.read_parquet(p, columns=None)
    if "volume" not in y.columns:
        return None
    s = y["volume"].copy()
    s.index = pd.to_datetime(s.index).normalize()
    return s[~s.index.duplicated(keep="last")].dropna()


def participation(f: pd.DataFrame, cons: pd.Series) -> pd.Series:
    j = f.set_index("date")[["total_vol"]].join(cons.rename("cons"), how="inner")
    j = j[j["cons"] > 0]
    return (j["total_vol"] / j["cons"]).dropna()


# ---- incumbent streak (incremental, exact) -----------------------------------------------

def streak_path(p_cal: np.ndarray) -> np.ndarray:
    """Streak at each calendar index (NaN on missing sessions). Observed-only, as the incumbent."""
    obs = np.flatnonzero(np.isfinite(p_cal))
    ov = p_cal[obs]
    n = len(ov)
    above = np.zeros(n, dtype=bool)
    for j in range(5, min(STREAK_WINDOW, n)):
        above[j] = ov[j] > np.median(ov[:j])
    if n > STREAK_WINDOW:
        win = np.lib.stride_tricks.sliding_window_view(ov[:-1], STREAK_WINDOW)
        above[STREAK_WINDOW:] = ov[STREAK_WINDOW:] > np.median(win, axis=1)
    st = np.zeros(n)
    run = 0
    for j in range(n):
        run = run + 1 if above[j] else 0
        st[j] = run
    out = np.full(len(p_cal), np.nan)
    out[obs] = st
    return out


def streak_detections(st: np.ndarray, k: int) -> np.ndarray:
    """Calendar indexes where the streak first reaches k (a new episode)."""
    return np.flatnonzero(st == k)


def streak_alarm(st: np.ndarray, k: int) -> np.ndarray:
    """Alarm state on every calendar index; missing sessions carry the last observed state."""
    s = pd.Series(st).ffill().fillna(0.0).to_numpy()
    return s >= k


def filter_detections_and_alarm(path, tau: float) -> tuple[np.ndarray, np.ndarray, list]:
    eps = episodes_from_path(path, tau_on=tau)
    n = len(path.p_elevated)
    on = np.zeros(n, dtype=bool)
    for e in eps:
        on[e.detected_at:(e.end_at if e.end_at is not None else n)] = True
    return np.array([e.detected_at for e in eps], dtype=int), on, eps


def first_in(dets: np.ndarray, lo: int, hi: int) -> int | None:
    sel = dets[(dets >= lo) & (dets < hi)]
    return int(sel[0]) if len(sel) else None


# ---- bootstrap ----------------------------------------------------------------------------

def boot_weights(n_names: int, n_blocks: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    cn = np.empty((B_BOOT, n_names))
    cb = np.empty((B_BOOT, n_blocks))
    for b in range(B_BOOT):
        cn[b] = np.bincount(rng.integers(0, n_names, n_names), minlength=n_names)
        cb[b] = np.bincount(rng.integers(0, n_blocks, n_blocks), minlength=n_blocks)
    return cn, cb


def boot_mean(d: np.ndarray, name_i: np.ndarray, block_i: np.ndarray, cn, cb) -> dict:
    w = cn[:, name_i] * cb[:, block_i]
    tot = w.sum(axis=1)
    ok = tot > 0
    stats = (w[ok] @ d) / tot[ok]
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return {"estimate": float(d.mean()), "ci95": [float(lo), float(hi)], "n": int(len(d)),
            "boot_valid": int(ok.sum())}


def boot_ratio(num_a, num_b, den, name_i, block_i, cn, cb) -> dict:
    w = cn[:, name_i] * cb[:, block_i]
    ra = (w @ num_a) / np.maximum(w @ den, 1e-12)
    rb = (w @ num_b) / np.maximum(w @ den, 1e-12)
    ok = rb > 0
    ratio = ra[ok] / rb[ok]
    lo, hi = np.percentile(ratio, [2.5, 97.5])
    point = (num_a.sum() / den.sum()) / (num_b.sum() / den.sum())
    return {"estimate": float(point), "ci95": [float(lo), float(hi)],
            "rate_filter_per_1000": float(1000 * num_a.sum() / den.sum()),
            "rate_streak_per_1000": float(1000 * num_b.sum() / den.sum()),
            "n_units": int(len(den)), "boot_valid": int(ok.sum())}


def r6(x):
    return None if x is None else (round(float(x), 6) if isinstance(x, (float, np.floating)) else x)


# ---- main ---------------------------------------------------------------------------------

def run() -> tuple[int, dict, dict]:
    inputs = {"panel.parquet": sha256_file(PANEL), "panel_deep.parquet": sha256_file(PANEL_DEEP),
              "yahoo/SPY.parquet": sha256_file(CAL_REF)}
    df = load_panel()
    cal = load_yahoo_vol("SPY")
    lo, hi = df["date"].min(), df["date"].max()
    cal_dates = cal.index[(cal.index >= lo) & (cal.index <= hi)]
    T = len(cal_dates)
    train_end_idx = int((cal_dates <= pd.Timestamp(TRAIN_END)).sum()) - 1
    test_start = train_end_idx + 1
    cal_pos = pd.Series(np.arange(T), index=cal_dates)

    # cohort (same rule as baseline_repro.py / PREREG §4)
    deep_names = sorted(pd.read_parquet(PANEL_DEEP, columns=["ticker"])["ticker"].unique())
    series: dict[str, np.ndarray] = {}
    yahoo_hashes: dict[str, str] = {}
    for tk in deep_names:
        cons = load_yahoo_vol(tk)
        if cons is None:
            continue
        part = participation(df[df["ticker"] == tk], cons)
        part = part[part.index.isin(cal_dates)]
        if share_break_index(part) is not None:
            continue
        n_tr = int((part.index <= TRAIN_END).sum())
        n_te = int((part.index > TRAIN_END).sum())
        if n_tr < MIN_TRAIN_OBS or n_te < MIN_TEST_OBS:
            continue
        a = np.full(T, np.nan)
        a[cal_pos.loc[part.index].to_numpy()] = part.to_numpy()
        series[tk] = a
        yahoo_hashes[tk] = sha256_file(YAHOO / f"{tk}.parquet")
    names = sorted(series)
    base_manifest = json.loads((HERE / "results" / "baseline_inputs_sha256.json").read_text())
    yahoo_mismatch = [tk for tk in names if base_manifest.get(f"yahoo/{tk}.parquet") != yahoo_hashes[tk]]
    inputs["yahoo_eligible_manifest_sha256"] = hashlib.sha256(
        json.dumps(yahoo_hashes, sort_keys=True).encode()).hexdigest()
    inputs["n_yahoo_files"] = len(yahoo_hashes)

    summary: dict = {"design": {"train_end": TRAIN_END, "streak_k": STREAK_K, "tau_grid": list(TAU_GRID),
                                "step_len": STEP_LEN, "win_d10": WIN_D10, "delay_censor": DELAY_CENSOR,
                                "injections": {k: list(v) for k, v in INJECTIONS.items()},
                                "block": BLOCK, "B": B_BOOT, "seed": SEED},
                     "calendar": {"n_sessions": T, "first": str(cal_dates[0].date()),
                                  "last": str(cal_dates[-1].date()), "train_end_index": train_end_idx},
                     "cohort": {"n_eligible": len(names), "yahoo_hash_mismatch_vs_baseline": yahoo_mismatch}}
    if len(names) < MIN_NAMES:
        summary["verdict"] = "INSUFFICIENT_DATA"
        summary["insufficient"] = f"eligible names {len(names)} < {MIN_NAMES}"
        return 0, summary, inputs

    # per-name base quantities
    z, st, evalm, obs_idx_last = {}, {}, {}, {}
    equiv_checked = equiv_mismatch = 0
    for tk in names:
        a = series[tk]
        z[tk] = robust_activity_z(a)
        st[tk] = streak_path(a)
        obs = np.isfinite(a)
        cnt_prior = np.concatenate([[0], np.cumsum(obs)[:-1]])
        evalm[tk] = obs & (cnt_prior >= EVAL_MIN_PRIOR)
        oi = np.flatnonzero(obs)
        obs_idx_last[tk] = int(oi[-1])
        # exact equivalence with the incumbent function at sampled observed sessions
        ov = a[oi]
        for j in sorted(set(np.linspace(0, len(oi) - 1, 6).astype(int).tolist())):
            equiv_checked += 1
            if int(streak_above_norm(pd.Series(ov[: j + 1]))) != int(st[tk][oi[j]]):
                equiv_mismatch += 1
    summary["streak_equivalence"] = {"checked": equiv_checked, "mismatch": equiv_mismatch}
    if equiv_mismatch:
        raise RuntimeError(f"incremental streak differs from incumbent at {equiv_mismatch} points")

    # training fit (train-session z only)
    ztr = np.concatenate([z[tk][: train_end_idx + 1] for tk in names])
    ztr = ztr[np.isfinite(ztr)]
    nu, scale = fit_emission_params(ztr)
    params = DurationFilterParams(nu=nu, scale=scale)
    summary["fit"] = {"nu": r6(nu), "scale": r6(scale), "n_train_z": int(len(ztr))}

    # base filter paths + tau calibration on train
    paths = {tk: filter_path(z[tk], params) for tk in names}
    tr_den = sum(int(evalm[tk][: train_end_idx + 1].sum()) for tk in names)
    tr_streak = sum(int(evalm[tk][d]) for tk in names for d in streak_detections(st[tk], STREAK_K)
                    if d <= train_end_idx)
    rate_streak_tr = 1000.0 * tr_streak / tr_den
    grid_rates = {}
    for tau in TAU_GRID:
        c = 0
        for tk in names:
            dets, _, _ = filter_detections_and_alarm(paths[tk], tau)
            c += int(sum(evalm[tk][d] for d in dets if d <= train_end_idx))
        grid_rates[tau] = 1000.0 * c / tr_den
    qual = [t for t in TAU_GRID if grid_rates[t] <= rate_streak_tr]
    tau = qual[0] if qual else TAU_GRID[-1]
    summary["calibration"] = {"train_evaluable_sessions": tr_den, "streak_k5_train_rate_per_1000": r6(rate_streak_tr),
                              "filter_train_rate_per_1000_by_tau": {str(k): r6(v) for k, v in grid_rates.items()},
                              "tau_on": tau, "tau_off": tau / 2, "grid_fallback": not qual}

    # base detections on test
    base = {}
    for tk in names:
        fd, fon, _ = filter_detections_and_alarm(paths[tk], tau)
        base[tk] = {"fd": fd, "fon": fon,
                    "sd": {k: streak_detections(st[tk], k) for k in (STREAK_K,) + K_CURVE},
                    "son": streak_alarm(st[tk], STREAK_K)}

    # P3 untouched held-out rate, unit = (name, 20-session calendar block)
    blocks_all = sorted(set(range(test_start // BLOCK, (T - 1) // BLOCK + 1)))
    block_code = {b: i for i, b in enumerate(blocks_all)}
    name_code = {tk: i for i, tk in enumerate(names)}
    u_name, u_block, u_f, u_s, u_den = [], [], [], [], []
    for tk in names:
        em = evalm[tk]
        fset = np.zeros(T, dtype=bool)
        fset[base[tk]["fd"]] = True
        sset = np.zeros(T, dtype=bool)
        sset[base[tk]["sd"][STREAK_K]] = True
        for b in blocks_all:
            lo_i, hi_i = max(b * BLOCK, test_start), min((b + 1) * BLOCK, T)
            den = int(em[lo_i:hi_i].sum())
            if den == 0:
                continue
            u_name.append(name_code[tk]); u_block.append(block_code[b]); u_den.append(den)
            u_f.append(int((fset & em)[lo_i:hi_i].sum())); u_s.append(int((sset & em)[lo_i:hi_i].sum()))

    # injections
    rows = []
    attr = {k: {"positions": 0, "excluded_filter_on": 0, "excluded_streak_on": 0, "excluded_both_on": 0,
                "excluded_missing_at_s": 0, "kept": 0} for k in INJECTIONS}
    for tk in names:
        shift = int(hashlib.sha256(tk.encode()).hexdigest()[:8], 16) % 30
        a = series[tk]
        for j in range(POS_N):
            s = test_start + POS_OFFSET + shift + POS_SPACING * j
            if s + POS_TAIL > obs_idx_last[tk]:
                continue
            f_on, s_on = bool(base[tk]["fon"][s - 1]), bool(base[tk]["son"][s - 1])
            for itype, (kind, mag) in INJECTIONS.items():
                at = attr[itype]
                at["positions"] += 1
                if f_on or s_on:
                    at["excluded_both_on" if (f_on and s_on) else
                       ("excluded_filter_on" if f_on else "excluded_streak_on")] += 1
                    continue
                if kind == "spike" and not np.isfinite(a[s]):
                    at["excluded_missing_at_s"] += 1
                    continue
                a2 = a.copy()
                if kind == "step":
                    a2[s:s + STEP_LEN] *= mag
                else:
                    a2[s] *= mag
                p2 = filter_path(robust_activity_z(a2), params)
                fd2, _, eps2 = filter_detections_and_alarm(p2, tau)
                st2 = streak_path(a2)
                f_first = first_in(fd2, s, s + DELAY_CENSOR)
                s_first = first_in(streak_detections(st2, STREAK_K), s, s + DELAY_CENSOR)
                row = {"ticker": tk, "type": itype, "s": s, "block": s // BLOCK,
                       "f_hit10": int(f_first is not None and f_first < s + WIN_D10),
                       "f_hit10_base": int(first_in(base[tk]["fd"], s, s + WIN_D10) is not None),
                       "s_hit10": int(s_first is not None and s_first < s + WIN_D10),
                       "s_hit10_base": int(first_in(base[tk]["sd"][STREAK_K], s, s + WIN_D10) is not None),
                       "f_delay": (f_first - s) if f_first is not None else DELAY_CENSOR,
                       "s_delay": (s_first - s) if s_first is not None else DELAY_CENSOR,
                       "f_frag": int(((fd2 >= s) & (fd2 < s + FRAG_WIN)).sum()),
                       "s_frag": int(((streak_detections(st2, STREAK_K) >= s) &
                                      (streak_detections(st2, STREAK_K) < s + FRAG_WIN)).sum()),
                       "f_retro_gap": None}
                if f_first is not None:
                    e = next(e for e in eps2 if e.detected_at == f_first)
                    row["f_retro_gap"] = int(e.detected_at - e.retro_onset_at_detection)
                for k in K_CURVE:
                    dk = streak_detections(st2, k)
                    fk = first_in(dk, s, s + DELAY_CENSOR)
                    row[f"k{k}_hit10"] = int(fk is not None and fk < s + WIN_D10)
                    row[f"k{k}_hit10_base"] = int(first_in(base[tk]["sd"][k], s, s + WIN_D10) is not None)
                    row[f"k{k}_delay"] = (fk - s) if fk is not None else DELAY_CENSOR
                at["kept"] += 1
                rows.append(row)
    rep = pd.DataFrame(rows)
    summary["attrition"] = attr

    cn, cb = boot_weights(len(names), len(blocks_all))
    ni = rep["ticker"].map(name_code).to_numpy()
    bi = rep["block"].map(block_code).to_numpy()

    def sel(mask):
        return mask.to_numpy()

    steps = sel(rep["type"].str.startswith("step"))
    spike = sel(rep["type"] == "spike300")
    ex_f = (rep["f_hit10"] - rep["f_hit10_base"]).to_numpy(dtype=float)
    ex_s = (rep["s_hit10"] - rep["s_hit10_base"]).to_numpy(dtype=float)
    dly = (rep["f_delay"] - rep["s_delay"]).to_numpy(dtype=float)

    prim = {}
    prim["P1a_excess_d10_diff_steps"] = boot_mean((ex_f - ex_s)[steps], ni[steps], bi[steps], cn, cb)
    prim["P1a_filter_excess_d10_steps"] = boot_mean(ex_f[steps], ni[steps], bi[steps], cn, cb)
    prim["P1a_streak_excess_d10_steps"] = boot_mean(ex_s[steps], ni[steps], bi[steps], cn, cb)
    prim["P1b_delay_diff_steps"] = boot_mean(dly[steps], ni[steps], bi[steps], cn, cb)
    prim["P1b_filter_delay_steps"] = boot_mean(rep["f_delay"].to_numpy(float)[steps], ni[steps], bi[steps], cn, cb)
    prim["P1b_streak_delay_steps"] = boot_mean(rep["s_delay"].to_numpy(float)[steps], ni[steps], bi[steps], cn, cb)
    prim["P2_spike_excess_diff"] = boot_mean((ex_f - ex_s)[spike], ni[spike], bi[spike], cn, cb)
    prim["P2_filter_spike_excess"] = boot_mean(ex_f[spike], ni[spike], bi[spike], cn, cb)
    prim["P2_streak_spike_excess"] = boot_mean(ex_s[spike], ni[spike], bi[spike], cn, cb)
    prim["P3_untouched_rate_ratio"] = boot_ratio(np.array(u_f, float), np.array(u_s, float), np.array(u_den, float),
                                                 np.array(u_name), np.array(u_block), cn, cb)
    sec = {}
    for itype in ("step125", "step150"):
        m = sel(rep["type"] == itype)
        sec[f"{itype}_excess_d10_diff"] = boot_mean((ex_f - ex_s)[m], ni[m], bi[m], cn, cb)
        sec[f"{itype}_delay_diff"] = boot_mean(dly[m], ni[m], bi[m], cn, cb)
        sec[f"{itype}_filter_d10_raw"] = float(rep.loc[m, "f_hit10"].mean())
        sec[f"{itype}_streak_d10_raw"] = float(rep.loc[m, "s_hit10"].mean())
    sec["P4_fragmentation_steps"] = {"filter_mean": float(rep.loc[steps, "f_frag"].mean()),
                                     "streak_mean": float(rep.loc[steps, "s_frag"].mean())}
    g = rep.loc[steps, "f_retro_gap"].dropna()
    sec["filter_detection_minus_retro_onset_steps"] = {"n": int(len(g)), "median": float(g.median()) if len(g) else None,
                                                       "mean": float(g.mean()) if len(g) else None}
    kc = {}
    for k in K_CURVE:
        exk = (rep[f"k{k}_hit10"] - rep[f"k{k}_hit10_base"]).to_numpy(float)
        ur = sum(int(evalm[tk][d]) for tk in names for d in base[tk]["sd"][k] if d >= test_start)
        kc[str(k)] = {"excess_d10_steps": float(exk[steps].mean()),
                      "delay_steps": float(rep.loc[steps, f"k{k}_delay"].mean()),
                      "spike_excess": float(exk[spike].mean()),
                      "untouched_rate_per_1000": float(1000 * ur / sum(u_den))}
    sec["streak_k_curve_descriptive"] = kc
    for k, v in prim.items():
        if isinstance(v, dict):
            prim[k] = {kk: (r6(vv) if not isinstance(vv, list) else [r6(x) for x in vv]) for kk, vv in v.items()}

    honest = {"names": len(names), "names_with_replicates": int(rep["ticker"].nunique()),
              "blocks": int(rep["block"].nunique()),
              "replicates_by_type": {k: int((rep["type"] == k).sum()) for k in INJECTIONS},
              "untouched_units": len(u_den), "untouched_evaluable_sessions": int(sum(u_den))}
    summary["honest_n"] = honest
    summary["primary"] = prim
    summary["secondary"] = sec

    n_steps, n_spike = int(steps.sum()), int(spike.sum())
    if n_steps < MIN_REPS or n_spike < MIN_REPS:
        summary["verdict"] = "INSUFFICIENT_DATA"
        summary["insufficient"] = f"replicates steps={n_steps} spike={n_spike} < {MIN_REPS}"
    else:
        d10 = prim["P1a_excess_d10_diff_steps"]
        dl = prim["P1b_delay_diff_steps"]
        h1 = (d10["estimate"] >= BAR_D10 and d10["ci95"][0] > 0) or (dl["estimate"] <= BAR_DELAY and dl["ci95"][1] < 0)
        h2 = prim["P2_spike_excess_diff"]["ci95"][1] <= BAR_SPIKE
        h3 = prim["P3_untouched_rate_ratio"]["estimate"] <= BAR_RATE
        summary["hypotheses"] = {"H1_sensitivity": bool(h1), "H2_spike_robustness": bool(h2),
                                 "H3_false_alarm_parity": bool(h3)}
        summary["verdict"] = "KEEP" if (h1 and h2 and h3) else "REJECT"

    # small result files (no timestamps, no code hashes -> byte-identical on re-run)
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    (res / "eval_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    buf = io.StringIO()
    cols = list(rep.columns)
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rep.itertuples(index=False):
        w.writerow(["" if (isinstance(v, float) and np.isnan(v)) else v for v in r])
    (res / "eval_replicates.csv").write_text(buf.getvalue())
    return 0, summary, inputs


def main() -> int:
    cmd = " ".join([sys.executable] + sys.argv)
    prereg = HERE / "PREREG.md"
    want, have = frozen_hash(), sha256_file(prereg) if prereg.exists() else None
    code = {"PREREG.md": have, "evaluate.py": sha256_file(Path(__file__)),
            "engine/darkpool_episode_duration.py": sha256_file(Q11_ROOT / "engine" / "darkpool_episode_duration.py"),
            "engine/darkpool_signals.py": sha256_file(Q11_ROOT / "engine" / "darkpool_signals.py")}
    if want is None or have != want:
        print(f"REFUSED: sha256(PREREG.md)={have} != FREEZE.log {want}", file=sys.stderr)
        append_run({"script": "evaluate.py", "command": cmd, "exit_code": 2, "refused": True,
                    "prereg_sha256": have, "freeze_sha256": want, "code": code})
        return 2
    mchk = module_check(code)
    if not mchk["ok"]:
        print(f"REFUSED: code integrity check failed: {json.dumps(mchk, sort_keys=True)}", file=sys.stderr)
        append_run({"script": "evaluate.py", "command": cmd, "exit_code": 2, "refused": True,
                    "prereg_sha256": have, "code": code, "module_check": mchk})
        return 2
    try:
        rc, summary, inputs = run()
    except Exception:  # noqa: BLE001 - every failure is logged, then re-raised as rc=1
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        append_run({"script": "evaluate.py", "command": cmd, "exit_code": 1, "error": tb.strip().splitlines()[-1],
                    "code": code, "module_check": mchk})
        return 1
    outs = {}
    for f in ("results/eval_summary.json", "results/eval_replicates.csv"):
        p = HERE / f
        if p.exists():
            outs[f] = sha256_file(p)
    append_run({"script": "evaluate.py", "command": cmd, "exit_code": rc, "verdict": summary.get("verdict"),
                "prereg_sha256": have, "code": code, "module_check": mchk, "inputs": inputs, "outputs": outs})
    print(json.dumps({"verdict": summary.get("verdict"), "hypotheses": summary.get("hypotheses"),
                      "fit": summary.get("fit"), "tau": summary.get("calibration", {}).get("tau_on"),
                      "honest_n": summary.get("honest_n"), "primary": summary.get("primary")}, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
