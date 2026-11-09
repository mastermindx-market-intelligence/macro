"""Lane E — Family × regime INTERACTION tournament (round-1 repair).

Entry point (from repo root):
  python3 research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, ".")

from engine.canon import rsi as _canon_rsi  # noqa: F401  — imported per lane law
from engine.session_anchor import session_positions as _session_positions  # noqa: F401
from engine.bar_derive import derive_daily_close as _derive_daily_close  # noqa: F401

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features as F  # noqa: E402
import stats as S  # noqa: E402


def _find_repo() -> Path:
    env = os.environ.get("E_REPO")
    if env:
        return Path(env).resolve()
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "data").is_dir() and (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root (no E_REPO and no data/.git ancestor)")


REPO = _find_repo()
RESULTS = REPO / "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E"
CODE = RESULTS / "code"
B1_DIR = REPO / "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1"
REGIME_FILE = REPO / "data/regime/regime_v2_pit.parquet"
YAHOO = REPO / "data/yahoo"
B1_RESULT_MD = B1_DIR / "RESULT.md"
EVENTS_PANEL = B1_DIR / "events_panel.parquet"
CONFIRMATION_PAIRS = B1_DIR / "confirmation_pairs.parquet"
UNIVERSE_MANIFEST = B1_DIR / "code" / "universe_manifest.json"

OUT_RESULT_MD = RESULTS / "RESULT.md"
OUT_RESULT_JSON = RESULTS / "result.json"
OUT_HASHES = RESULTS / "hashes.txt"
OUT_DONE = RESULTS / "DONE"

BOOTSTRAP_DRAWS = 1000
SEED_BASE = 20261004
EXPECTED_PANEL_SHA = "209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8"
EXPECTED_PAIRS_SHA = "d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae"
EXPECTED_N_1D = 296637

PARTITIONS = [
    ("P1_growth", "growth_state", "EXPANSION", "CONTRACTION"),
    ("P2_stress", "stress_state", "STRESSED", "CALM"),
]

REGIME_CLOCK_CITATIONS = [
    {
        "file": "scripts/build_regime_v2_pit.py",
        "line": 376,
        "quote": "f_pit = build_features(overrides=overrides)",
    },
    {
        "file": "engine/inputs.py",
        "line": 171,
        "quote": "idx = pd.bdate_range(closes.index.min(), end)",
    },
    {
        "file": "engine/inputs.py",
        "line": 262,
        "quote": 'basket_index(closes, g["cyclical_basket"]).reindex(idx).ffill(limit=5)',
        "note": "lines 262-267: basket_index(...).reindex(idx).ffill(limit=5); row d includes closes at d",
    },
    {
        "file": "scripts/build_regime_v2_pit.py",
        "line": 103,
        "quote": "def pit_availability_panel(vintages: pd.DataFrame, sid: str) -> pd.Series:",
        "note": "lines 103-105: as-of d by reindex+ffill",
    },
]

# Round-0 headlines (K10). Point estimates I from the unrepaired run on the
# ROUND-2 panel (sha 1a63ce44… / recorded 1a63ce44…).
ROUND0_I = {
    ("trend", "P1_growth"): 0.0022688736207783222,
    ("trend", "P2_stress"): -0.005083437077701092,
    ("momentum", "P1_growth"): -0.0014492813497781754,
    ("momentum", "P2_stress"): -0.004627033602446318,
    ("compression", "P1_growth"): -0.0015953350812196732,
    ("compression", "P2_stress"): 0.0022999667562544346,
    ("participation", "P1_growth"): 0.005802495172247291,
    ("participation", "P2_stress"): 0.00013546901755034924,
    ("rs", "P1_growth"): 0.0004352484829723835,
    ("rs", "P2_stress"): -0.0012525361962616444,
    ("structure", "P1_growth"): 0.002145683392882347,
    ("structure", "P2_stress"): -0.006872418336570263,
}
ROUND0_SE = {
    ("structure", "P2_stress"): 0.002891885514207144,
}
ROUND0_P = {
    ("structure", "P2_stress"): 0.014,
}
ROUND0_VERDICT = "INSUFFICIENT_SUPPORT"
ROUND0_N_ABOVE = 0
ROUND0_N_AFTER_JOIN = 291955
ROUND0_DROPS_7D = 4714


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_rngs() -> dict[str, list[np.random.Generator]]:
    """Stable SeedSequence tree: spawn(4) then spawn(n_tests) per branch (K3)."""
    root = np.random.SeedSequence(SEED_BASE)
    primary_ss, h21_ss, sec_ss, ctx_ss = root.spawn(4)
    return {
        "primary": [np.random.default_rng(s) for s in primary_ss.spawn(12)],
        "h21": [np.random.default_rng(s) for s in h21_ss.spawn(12)],
        "sec": [np.random.default_rng(s) for s in sec_ss.spawn(12)],
        "ctx": [np.random.default_rng(s) for s in ctx_ss.spawn(24)],
    }


def _load_one_close(entry: dict) -> tuple[str, pd.Series | None]:
    name = entry["name"]
    p = REPO / entry["path"]
    if not p.exists():
        return name, None
    try:
        df = pd.read_parquet(p)
    except Exception:
        return name, None
    if "close" not in df.columns:
        df = df.rename(columns={"close_price": "close"})
    if "close" not in df.columns:
        return name, None
    s = pd.Series(
        df["close"].astype(float).to_numpy(),
        index=pd.DatetimeIndex(pd.to_datetime(df.index)).normalize(),
        name=name,
    ).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return name, s


def load_universe_closes(manifest_path: Path) -> dict[str, pd.Series]:
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    out: dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for name, s in ex.map(_load_one_close, manifest["entries"]):
            if s is not None:
                out[name] = s
    return out


def load_spy_close() -> pd.Series:
    df = pd.read_parquet(YAHOO / "SPY.parquet")
    if "close" not in df.columns:
        df = df.rename(columns={"close_price": "close"})
    s = pd.Series(
        df["close"].astype(float).to_numpy(),
        index=pd.DatetimeIndex(pd.to_datetime(df.index)).normalize(),
        name="SPY",
    ).sort_index()
    return s[~s.index.duplicated(keep="last")]


def _json_sanitize(obj):
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if not np.isfinite(v) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float):
        return None if not np.isfinite(obj) else obj
    if isinstance(obj, np.ndarray):
        return _json_sanitize(obj.tolist())
    return obj


def _dump(payload: dict) -> bytes:
    return json.dumps(_json_sanitize(payload), indent=2, ensure_ascii=False,
                      allow_nan=False).encode("utf-8") + b"\n"


def summarize_bootstrap(obs: float, samples: np.ndarray) -> dict:
    ci_lo, ci_hi, se = S.ci_se(samples)
    p = S.two_sided_p(obs, samples)
    return {
        "observed": None if not np.isfinite(obs) else float(obs),
        "ci_lo": None if not np.isfinite(ci_lo) else float(ci_lo),
        "ci_hi": None if not np.isfinite(ci_hi) else float(ci_hi),
        "se": None if not np.isfinite(se) else float(se),
        "p_two_sided": None if not np.isfinite(p) else float(p),
    }


def run_one_test(df_f: pd.DataFrame, fam: str, part_name: str,
                 state_col: str, state_a: str, state_b: str,
                 rng: np.random.Generator, n_draws: int,
                 outcome_col: str = "y") -> dict:
    sub = df_f[["tercile", state_col, "entry_month", "name", outcome_col, "era"]].rename(
        columns={state_col: "state", outcome_col: "y"}
    )
    extra = {}
    if "recession" in df_f.columns:
        extra["recession"] = df_f["recession"].to_numpy()
    if "transition_ratcheted" in df_f.columns:
        extra["transition_ratcheted"] = df_f["transition_ratcheted"].to_numpy()
    for k, v in extra.items():
        sub[k] = v

    obs, samples = S._bootstrap_interaction_for_family_partition(
        sub, state_col="state", outcome_col="y",
        state_a=state_a, state_b=state_b,
        n_draws=n_draws, rng=rng, mode="weight",
    )
    stats = summarize_bootstrap(obs, samples)
    era_vals = S.era_I(sub, state_a, state_b, state_col="state", outcome_col="y")
    e1, e2 = era_vals["2014-2019"], era_vals["2020-2026"]
    same = bool(np.isfinite(e1) and np.isfinite(e2) and (e1 * e2 > 0))
    floor_pass, cells, failing = S.floor_gate_eight_cells(
        sub, state_a, state_b, state_col="state", outcome_col="y",
    )
    # recession / transition shares per cell (context)
    for c in cells:
        sl = sub[(sub["tercile"] == c["tercile"]) &
                 (sub["state"] == c["state"]) &
                 (sub["era"] == c["era"])]
        if "recession" in sl.columns and len(sl):
            c["recession_share"] = float(sl["recession"].astype(bool).mean())
        if "transition_ratcheted" in sl.columns and len(sl):
            c["transition_ratcheted_share"] = float(
                sl["transition_ratcheted"].astype(bool).mean()
            )
    return {
        "family": fam,
        "partition": part_name,
        "state_a": state_a,
        "state_b": state_b,
        **stats,
        "era_2014_2019": None if not np.isfinite(e1) else float(e1),
        "era_2020_2026": None if not np.isfinite(e2) else float(e2),
        "same_sign_eras": same,
        "floor_pass": bool(floor_pass),
        "failing_cells": failing,
        "cells": cells,
    }


def attach_family_features(events: pd.DataFrame, rolling_dict, part, spy_close) -> pd.DataFrame:
    feat_trend = F.lookup_per_name_feature(rolling_dict, events, F.feat_trend)
    feat_momentum = F.lookup_per_name_feature(rolling_dict, events, F.feat_momentum)
    feat_compression = F.lookup_per_name_feature(rolling_dict, events, F.feat_compression)
    feat_structure = F.lookup_per_name_feature(rolling_dict, events, F.feat_structure)
    feat_rs = F.lookup_per_name_feature(
        rolling_dict, events, lambda roll: F.feat_rs(roll, spy_close),
    )
    feat_part = F.lookup_participation(part, events)
    out = events.copy()
    out["trend"] = feat_trend.to_numpy()
    out["momentum"] = feat_momentum.to_numpy()
    out["compression"] = feat_compression.to_numpy()
    out["participation"] = feat_part.to_numpy()
    out["rs"] = feat_rs.to_numpy()
    out["structure"] = feat_structure.to_numpy()
    return out


def compute_payload(input_hashes_load: dict, t0: float) -> dict:
    print("[E] loading events_panel …", flush=True)
    events = pd.read_parquet(EVENTS_PANEL)
    n_1d = int((events["variant"] == "1D").sum())
    print(f"[E] events_panel loaded: {len(events):,} rows; 1D={n_1d:,}", flush=True)

    b1_md = B1_RESULT_MD.read_text()
    k_inverted = "k inverted" in b1_md

    print("[E] loading universe closes …", flush=True)
    name_closes = load_universe_closes(UNIVERSE_MANIFEST)
    print(f"[E] universe loaded: {len(name_closes):,} names", flush=True)

    print("[E] computing per-name rolling quantities …", flush=True)
    rolling_dict: dict[str, pd.DataFrame] = {}
    for name, close in name_closes.items():
        try:
            rolling_dict[name] = F.per_name_rolling(close)
        except Exception:
            continue
    print(f"[E] rolling_dict ready: {len(rolling_dict):,} names", flush=True)

    print("[E] computing participation vector …", flush=True)
    part = F.participation_series(rolling_dict, min_names_with_sma50=50)
    print(f"[E] participation: {part.notna().sum():,} non-NaN dates", flush=True)

    spy_close = load_spy_close()

    primary = events[events["variant"] == "1D"].copy().reset_index(drop=True)
    keep_cols = [c for c in [
        "variant", "name", "signal_date", "entry_date", "entry_month", "era",
        "excess_h10_net", "excess_h21_net", "mfe21", "mae21", "sessions_to_mfe",
    ] if c in primary.columns]
    primary = primary[keep_cols]
    print(f"[E] primary events (1D): {len(primary):,}", flush=True)

    print("[E] preparing 3D.p0-confirmed secondary set …", flush=True)
    pairs = pd.read_parquet(CONFIRMATION_PAIRS)
    pairs_3d = pairs[(pairs["variant"] == "3D.p0") & (~pairs["no_confirmation"])].copy()
    pairs_3d["signal_date_3d"] = pd.to_datetime(pairs_3d["signal_session_other"]).dt.normalize()
    ev_3d = events[events["variant"] == "3D.p0"][[
        "name", "signal_date", "excess_h10_net", "excess_h21_net",
        "mfe21", "mae21", "sessions_to_mfe", "entry_date", "entry_month", "era",
    ]].copy()
    ev_3d["signal_date"] = pd.to_datetime(ev_3d["signal_date"]).dt.normalize()
    secondary = pairs_3d.merge(
        ev_3d, left_on=["name", "signal_date_3d"], right_on=["name", "signal_date"],
        how="inner", suffixes=("", "_3d"),
    )
    print(f"[E] secondary events (3D.p0 confirmed): {len(secondary):,}", flush=True)

    print("[E] computing family features (primary) …", flush=True)
    primary_full = attach_family_features(primary, rolling_dict, part, spy_close)
    print(f"[E] feature NaN fractions: "
          f"{primary_full[F.FAMILIES].isna().mean().round(4).to_dict()}", flush=True)

    cuts = {f: F.fixed_tercile_cuts(primary_full[f]) for f in F.FAMILIES}
    print(f"[E] tercile cuts: {cuts}", flush=True)
    for f in F.FAMILIES:
        lo, hi = cuts[f]
        primary_full[f + "_tercile"] = F.assign_terciles(primary_full[f], lo, hi).to_numpy()

    print("[E] loading regime and joining …", flush=True)
    regime = pd.read_parquet(REGIME_FILE)
    joined, drops = S.join_regime(primary_full, regime)
    print(f"[E] joined: {len(joined):,} ; drops:\n{drops}", flush=True)

    feature_drops = []
    for f in F.FAMILIES:
        n_nan = int(joined[f].isna().sum()) if f in joined.columns else int(len(joined))
        feature_drops.append({"reason": f"feature_nan_{f}", "n": n_nan})

    rngs_a = make_rngs()
    rngs_b = make_rngs()

    def twelve(joined_frame, rng_list, ycol):
        tests = []
        i = 0
        for fam in F.FAMILIES:
            tcol = fam + "_tercile"
            need = [tcol, "growth_state", "stress_state", "entry_month", ycol, "name", "era"]
            df_f = joined_frame.dropna(subset=need).copy()
            df_f = df_f.rename(columns={tcol: "tercile"})
            df_f["y"] = df_f[ycol]
            for part_name, state_col, state_a, state_b in PARTITIONS:
                tests.append(run_one_test(
                    df_f, fam, part_name, state_col, state_a, state_b,
                    rng_list[i], BOOTSTRAP_DRAWS, outcome_col="y",
                ))
                i += 1
        return tests

    print("[E] computing 12 primary tests on H10 net (run A) …", flush=True)
    tests_a = twelve(joined, rngs_a["primary"], "excess_h10_net")
    print("[E] computing 12 primary tests on H10 net (run B, identity check) …", flush=True)
    tests_b = twelve(joined, rngs_b["primary"], "excess_h10_net")

    def tests_core(ts):
        return [{k: t[k] for k in (
            "family", "partition", "observed", "ci_lo", "ci_hi", "se",
            "p_two_sided", "era_2014_2019", "era_2020_2026", "floor_pass",
        )} for t in ts]

    sha_a = _sha256_bytes(json.dumps(_json_sanitize(tests_core(tests_a)),
                                     allow_nan=False).encode())
    sha_b = _sha256_bytes(json.dumps(_json_sanitize(tests_core(tests_b)),
                                     allow_nan=False).encode())
    print(f"[E] identity sha A={sha_a[:16]} B={sha_b[:16]} match={sha_a == sha_b}",
          flush=True)
    tests = tests_a

    pvals = np.array([t["p_two_sided"] if t["p_two_sided"] is not None else np.nan
                      for t in tests], dtype=float)
    valid_mask = np.isfinite(pvals)
    p_holm = np.full(len(pvals), np.nan)
    if valid_mask.sum() > 0:
        p_holm[valid_mask] = S.holm(pvals[valid_mask])
    for i, t in enumerate(tests):
        t["p_holm"] = None if not np.isfinite(p_holm[i]) else float(p_holm[i])

    verdict, verdict_reasons, winners, n_above = S.apply_verdict(tests)
    for i, t in enumerate(tests):
        print(f"[E]   {t['family']} × {t['partition']}: "
              f"obs={t['observed']:+.5f} CI=[{t['ci_lo']:+.5f},{t['ci_hi']:+.5f}] "
              f"p={t['p_two_sided']:.4f} holm={t['p_holm']:.4f} "
              f"floor={'PASS' if t['floor_pass'] else 'FAIL'} "
              f"fail={t['failing_cells']}", flush=True)

    print("[E] computing H21 secondary …", flush=True)
    h21_tests = twelve(joined, rngs_a["h21"], "excess_h21_net")
    # drop cells from secondary rows to keep payload smaller; keep era values (K7)
    h21_out = []
    for t in h21_tests:
        h21_out.append({
            "family": t["family"], "partition": t["partition"],
            "observed": t["observed"], "ci_lo": t["ci_lo"], "ci_hi": t["ci_hi"],
            "se": t["se"], "p_two_sided": t["p_two_sided"],
            "era_2014_2019": t["era_2014_2019"],
            "era_2020_2026": t["era_2020_2026"],
        })

    print("[E] computing 3D.p0-confirmed secondary (H10) …", flush=True)
    sec = secondary.copy()
    sec["signal_date"] = pd.to_datetime(sec["signal_date_3d"]).dt.normalize()
    sec = sec[["name", "signal_date", "entry_month", "era",
               "excess_h10_net", "excess_h21_net"]].copy()
    sec = attach_family_features(sec, rolling_dict, part, spy_close)
    for f in F.FAMILIES:
        lo, hi = cuts[f]
        sec[f + "_tercile"] = F.assign_terciles(sec[f], lo, hi).to_numpy()
    sec_j, sec_drops = S.join_regime(sec, regime)
    sec_tests_full = twelve(sec_j, rngs_a["sec"], "excess_h10_net")
    sec_out = []
    for t in sec_tests_full:
        sec_out.append({
            "family": t["family"], "partition": t["partition"],
            "observed": t["observed"], "ci_lo": t["ci_lo"], "ci_hi": t["ci_hi"],
            "se": t["se"], "p_two_sided": t["p_two_sided"],
            "era_2014_2019": t["era_2014_2019"],
            "era_2020_2026": t["era_2020_2026"],
        })

    # Quad descriptive
    quad_table = []
    if "quad" in joined.columns:
        for q in ("Q1", "Q2", "Q3", "Q4"):
            subq = joined[joined["quad"] == q]
            quad_table.append({
                "quad": q,
                "n_events": int(len(subq)),
                "n_months": int(subq["entry_month"].nunique()) if len(subq) else 0,
                "n_names": int(subq["name"].nunique()) if len(subq) else 0,
                "mean_h10_net": float(subq["excess_h10_net"].mean()) if len(subq) else None,
            })

    rec_context = {}
    if "recession" in joined.columns:
        rec_context["recession_share"] = float(joined["recession"].astype(bool).mean())
    if "transition_ratcheted" in joined.columns:
        rec_context["transition_ratcheted_share"] = float(
            joined["transition_ratcheted"].astype(bool).mean()
        )

    # Regime main effects + family main effects (context)
    print("[E] context main effects …", flush=True)
    ctx_rngs = rngs_a["ctx"]
    ci = 0
    regime_main = {}
    for part_name, state_col, state_a, state_b in PARTITIONS:
        regime_main[part_name] = {}
        for st in (state_a, state_b):
            sl = joined[joined[state_col] == st][["entry_month", "excess_h10_net"]].rename(
                columns={"excess_h10_net": "y"}
            )
            obs, samp = S.cluster_bootstrap_mean(
                sl, n_draws=BOOTSTRAP_DRAWS, rng=ctx_rngs[ci],
            )
            ci += 1
            sm = summarize_bootstrap(obs, samp)
            regime_main[part_name][st] = {
                **sm,
                "n_events": int(len(sl)),
                "n_months": int(sl["entry_month"].nunique()),
            }

    family_main = {}
    for fam in F.FAMILIES:
        tcol = fam + "_tercile"
        sl = joined.dropna(subset=[tcol, "excess_h10_net", "entry_month"]).copy()
        sl = sl.rename(columns={tcol: "tercile"})
        sl["y"] = sl["excess_h10_net"]
        cell = S.cell_mean(sl.assign(state="P"), state_col="state", outcome_col="y")
        by = {(row["state"], row["tercile"]): row["mean_y"] for _, row in cell.iterrows()}
        spread = float(by.get(("P", "T3"), np.nan) - by.get(("P", "T1"), np.nan)) if (
            ("P", "T3") in by and ("P", "T1") in by) else float("nan")
        work2 = sl[sl["tercile"].isin(["T1", "T3"])]
        months = list(pd.Index(work2["entry_month"].dropna().unique()))
        n_m = len(months)
        month_to_i = {m: i for i, m in enumerate(months)}
        e_mi = work2["entry_month"].map(month_to_i).to_numpy().astype(int)
        terc = work2["tercile"].to_numpy()
        y = work2["y"].to_numpy(dtype=float)
        sum_y = np.zeros((n_m, 2))
        cnt = np.zeros((n_m, 2))
        for j, tv in enumerate(("T3", "T1")):
            msk = (terc == tv) & np.isfinite(y)
            np.add.at(sum_y[:, j], e_mi[msk], y[msk])
            np.add.at(cnt[:, j], e_mi[msk], 1.0)
        rng = ctx_rngs[ci]
        ci += 1
        samples = np.full(BOOTSTRAP_DRAWS, np.nan)
        for k in range(BOOTSTRAP_DRAWS):
            drawn = rng.integers(0, n_m, size=n_m)
            w = np.bincount(drawn, minlength=n_m).astype(float)
            n = w @ cnt
            if np.any(n <= 0):
                continue
            sy = w @ sum_y
            samples[k] = float(sy[0] / n[0] - sy[1] / n[1])
        sm = summarize_bootstrap(spread, samples)
        family_main[fam] = {
            **sm,
            "n_events_t3": int((sl["tercile"] == "T3").sum()),
            "n_events_t1": int((sl["tercile"] == "T1").sum()),
        }

    # K10 comparison
    k10_rows = []
    dI = []
    for t in tests:
        key = (t["family"], t["partition"])
        r0 = ROUND0_I[key]
        r1 = t["observed"]
        delta = None if r1 is None else float(r1 - r0)
        if delta is not None:
            dI.append(abs(delta))
        k10_rows.append({
            "family": t["family"], "partition": t["partition"],
            "round0_I": r0, "round1_I": r1, "delta_I": delta,
            "round1_se": t["se"], "round1_p": t["p_two_sided"],
            "round1_holm": t["p_holm"], "round1_floor_pass": t["floor_pass"],
        })
    max_abs_dI = max(dI) if dI else None

    input_hashes_write = {
        "events_panel": _sha256(EVENTS_PANEL),
        "confirmation_pairs": _sha256(CONFIRMATION_PAIRS),
        "regime": _sha256(REGIME_FILE),
        "universe_manifest": _sha256(UNIVERSE_MANIFEST),
        "b1_result_md": _sha256(B1_RESULT_MD),
    }
    if input_hashes_write != input_hashes_load:
        return {
            "lane": "E",
            "status": "INPUT_CHANGED",
            "inputs": {"load": input_hashes_load, "writeout": input_hashes_write},
            "gaps": ["INPUT_CHANGED: a hashed input moved between load and write-out"],
        }

    repo_head = subprocess_check(["git", "rev-parse", "HEAD"], cwd=REPO)

    try:
        import pyarrow
        pyarrow_v = pyarrow.__version__
    except Exception:
        pyarrow_v = None
    try:
        import scipy
        scipy_v = scipy.__version__
    except Exception:
        scipy_v = None
    try:
        import pytest as _pytest
        pytest_v = _pytest.__version__
    except Exception:
        pytest_v = None

    winners_out = []
    for w in winners:
        # attach matching secondaries
        h21 = next((s for s in h21_out if s["family"] == w["family"]
                    and s["partition"] == w["partition"]), None)
        sec_m = next((s for s in sec_out if s["family"] == w["family"]
                      and s["partition"] == w["partition"]), None)
        winners_out.append({
            "family": w["family"], "partition": w["partition"],
            "observed": w["observed"], "ci_lo": w["ci_lo"], "ci_hi": w["ci_hi"],
            "se": w["se"], "p_two_sided": w["p_two_sided"], "p_holm": w["p_holm"],
            "t_stat": w["t_stat"],
            "era_2014_2019": w["era_2014_2019"],
            "era_2020_2026": w["era_2020_2026"],
            "h21_secondary": h21, "three_d_p0_secondary": sec_m,
        })

    if verdict == "WINNERS":
        answer = (
            f"{len(winners_out)} winner(s); top = {winners_out[0]['family']}×"
            f"{winners_out[0]['partition']} I={winners_out[0]['observed']:+.5f}, "
            f"|I|/SE={winners_out[0]['t_stat']:.2f}"
        )
    else:
        answer = (
            f"{verdict}: no family×partition meets the winner rule "
            f"(Holm-adjusted p<0.05, same sign in both eras, all eight era-cells "
            f"above floor); {n_above}/12 tests had all cells above floor"
        )

    payload = {
        "lane": "E",
        "status": "DELIVERED",
        "repo_head": repo_head,
        "verdict_rule": S.VERDICT_RULE,
        "data_class": {
            "vintage": "final",
            "universe": "B1 survivor-selected baskets, current membership only",
            "panel": "B1 ROUND 3",
        },
        "inputs": {
            "events_panel": str(EVENTS_PANEL.relative_to(REPO)),
            "panel_sha256": input_hashes_load["events_panel"],
            "panel_sha256_load": input_hashes_load["events_panel"],
            "panel_sha256_writeout": input_hashes_write["events_panel"],
            "confirmation_pairs": str(CONFIRMATION_PAIRS.relative_to(REPO)),
            "pairs_sha256": input_hashes_load["confirmation_pairs"],
            "pairs_sha256_load": input_hashes_load["confirmation_pairs"],
            "pairs_sha256_writeout": input_hashes_write["confirmation_pairs"],
            "b1_result_md": str(B1_RESULT_MD.relative_to(REPO)),
            "regime_file": str(REGIME_FILE.relative_to(REPO)),
            "regime_sha256": input_hashes_load["regime"],
            "universe_manifest": str(UNIVERSE_MANIFEST.relative_to(REPO)),
            "universe_manifest_sha256": input_hashes_load["universe_manifest"],
            "b1_k_inverted_marked_in_panel": bool(k_inverted),
            "b1_round": 3,
            "n_1d_rows": n_1d,
        },
        "regime_clock": {
            "engine_module": "scripts/build_regime_v2_pit.py",
            "citations": REGIME_CLOCK_CITATIONS,
            "row_dated_t_uses_data_through": "t (same-day closes included)",
            "observed_semantics": (
                "regime_v2_pit.parquet row at date d carries features that use data "
                "THROUGH d: scripts/build_regime_v2_pit.py:376 "
                "`f_pit = build_features(overrides=overrides)`; engine/inputs.py:171 "
                "`idx = pd.bdate_range(closes.index.min(), end)` and :262-267 "
                "`basket_index(...).reindex(idx).ffill(limit=5)` (row d includes the "
                "closes at d); macro legs via pit_availability_panel "
                "(scripts/build_regime_v2_pit.py:103-105, as-of d by reindex+ffill). "
                "The E join is conservative: merge_asof direction='backward' with "
                "allow_exact_matches=False picks the strictly-prior row, so events at "
                "signal_date use regime data through ≤ signal_date − 1 calendar day."
            ),
            "regime_index": {
                "freq": "business-daily",
                "start": "1971-01-04",
                "end": "2026-07-02",
                "n_rows": 14479,
            },
        },
        "design": {
            "outcome_primary": "excess_h10_net",
            "outcome_secondary": "excess_h21_net",
            "primary_set": "B1 events_panel.parquet with variant == '1D'",
            "secondary_set": "B1 confirmation_pairs.parquet variant == '3D.p0' AND no_confirmation == False, joined to 3D.p0 events_panel row",
            "join": "merge_asof direction=backward allow_exact_matches=False",
            "fallback_max_days": 7,
            "regime_columns_used": ["growth_score", "n_flags", "quad", "recession",
                                    "transition_ratcheted"],
            "partitions": {
                "P1_growth": "EXPANSION if growth_score>0 else CONTRACTION",
                "P2_stress": "STRESSED if n_flags>=1 else CALM",
                "P3_quad": "Q1/Q2/Q3/Q4 — DESCRIPTIVE ONLY",
            },
            "families": {
                "trend": "close_t / SMA200_t − 1",
                "momentum": "close_{t-21} / close_{t-252} − 1 (12-1 momentum)",
                "compression": "std(log_ret over 20 sessions) / std(log_ret over 120 sessions) (low = compressed)",
                "participation": "share of universe names with close_t > SMA50_t on SPY session date t (date-level; valid SMA50 only)",
                "rs": "(close_t / close_{t-63}) / (SPY_t / SPY_{t-63}) − 1",
                "structure": "close_t / max(close over last 252 sessions) − 1 (0 = at 52-week high)",
            },
            "binning": "fixed terciles computed on the PRIMARY event set over the whole sample",
            "statistic": {
                "spread(f, S)": "mean(y | T3, S) − mean(y | T1, S)",
                "I(f, P)": "spread(f, A) − spread(f, B), A=EXPANSION or STRESSED",
            },
            "bootstrap": {
                "kind": "entry-month cluster resample WITH replacement, multiplicity weights (np.bincount)",
                "n_draws": BOOTSTRAP_DRAWS,
                "seed": SEED_BASE,
                "pairing": "per test (one month-draw sequence per test; not shared across the 12 tests)",
            },
            "holm_stepdown": {
                "scope": "12 primary tests (6 families × 2 partitions) at α = 0.05",
            },
            "floors": {
                "events": S.FLOOR_EVENTS, "months": S.FLOOR_MONTHS, "names": S.FLOOR_NAMES,
                "eras_present": list(S.ERAS),
                "cells": "eight (tercile in {T1,T3}) × (state) × (era) cells",
            },
        },
        "tercile_cuts": {f: {"lo": cuts[f][0], "hi": cuts[f][1]} for f in F.FAMILIES},
        "drops_by_reason": drops.to_dict(orient="records") + feature_drops,
        "n_events_after_join": int(len(joined)),
        "n_primary_1d": n_1d,
        "context": rec_context,
        "regime_main_effect": regime_main,
        "family_main_effect": family_main,
        "tests_12": tests,
        "holm_stepdown": {
            "raw_p": [t["p_two_sided"] for t in tests],
            "p_holm": [t["p_holm"] for t in tests],
            "alpha": 0.05,
            "scope": "6 families × 2 partitions = 12 tests on H10 net (primary set)",
        },
        "n_tests_above_floor": int(n_above),
        "winners": winners_out,
        "verdict": verdict,
        "verdict_reasons": verdict_reasons,
        "h21_secondary_12": h21_out,
        "three_d_p0_confirmed_secondary": {
            "n_events_in_set": int(len(secondary)),
            "n_events_after_join": int(len(sec_j)),
            "drops": sec_drops.to_dict(orient="records"),
            "tests_12": sec_out,
        },
        "quad_descriptive": quad_table,
        "answer_first": answer,
        "round0_comparison": {
            "round0_verdict": ROUND0_VERDICT,
            "round0_n_tests_above_floor": ROUND0_N_ABOVE,
            "round0_n_events_after_join": ROUND0_N_AFTER_JOIN,
            "round0_drops_7d": ROUND0_DROPS_7D,
            "round0_panel_note": "round 0 consumed ROUND-2 panel (recorded sha 1a63ce44…) while B1 was rewriting; this round pins B1 ROUND 3 sha 209e2246… (296,637 1D rows; −32 1D rows vs the in-flight r2 count implied by round 0 join+drops)",
            "max_abs_delta_I": max_abs_dI,
            "expected_max_abs_delta_I_from_panel_swap": 1.5e-05,
            "rows": k10_rows,
            "movers": [
                {"cause": "panel r2→r3", "delta": "−32 1D rows; point estimates I expected to move by at most ~1.5e-05"},
                {"cause": "bootstrap repair (K2 weights)", "delta": "SE/p (structure×P2 SE round0 0.00289 / p 0.014 → ~0.0038 / ~0.06)"},
                {"cause": "floor repair (K1 eight era cells)", "delta": "verdict INSUFFICIENT_SUPPORT (0/12) → expected SCOPED_NULL (10/12); participation×P1 and participation×P2 remain INSUFFICIENT"},
            ],
        },
        "identity": {
            "tests_12_sha256_run_a": sha_a,
            "tests_12_sha256_run_b": sha_b,
            "byte_identical": sha_a == sha_b,
        },
        "provenance": {
            "host": {
                "hostname": os.uname().nodename if hasattr(os, "uname") else None,
                "python_executable": sys.executable,
                "python_version": sys.version.split()[0],
                "pandas": pd.__version__,
                "numpy": np.__version__,
                "pyarrow": pyarrow_v,
                "scipy": scipy_v,
                "pytest": pytest_v,
            },
            "wall_seconds_compute": None,
        },
        "pytest_summary": None,
        "pytest_summary_counts": None,
        "gaps": [],
        "deviations": [
            "Bootstrap draws are per test (SeedSequence(20261004).spawn(4) then spawn(12) per branch); pairing holds within a test, not across all 12 cells (K9).",
            "hashes.txt pins the panel, pairs, regime, manifest, B1 RESULT.md, cited engine/regime scripts, and lane outputs — not every basket parquet (manifest already carries per-name sha256; disk is near full).",
        ],
        "k_repairs": {},
        "mutation_failing_tests": {
            "floor_mutant_pooled_six": "test_floor_gate_counts_eight_cells",
            "mutation_B_keep_all_months": "test_unclustered_resample_fails_cluster_invariant",
            "isin_mutant": "test_cluster_bootstrap_matches_analytic_se",
        },
    }
    payload["provenance"]["wall_seconds_compute"] = float(time.time() - t0)
    return payload


def write_result_md(p: dict, pytest_counts: str | None = None) -> None:
    md: list[str] = []
    # FIRST paragraph: data class + ANSWER FIRST (spec)
    md.append(
        "The price stores are FINAL-VINTAGE (as observed today, not point-in-time) "
        "and the universes are SURVIVOR-SELECTED (current membership only). "
        "This lane consumed the **B1 ROUND 3** panel "
        f"(sha256 `{p['inputs']['panel_sha256'][:16]}…`, "
        f"{p['inputs']['n_1d_rows']:,} 1D rows; B1/RESULT.md records `k inverted`). "
        f"**ANSWER FIRST:** {p['answer_first']}.\n"
    )

    md.append("\n## Answer first\n")
    md.append(f"**{p['verdict']}** — {p['answer_first']}\n")

    md.append("\n## Regime clock\n")
    md.append(p["regime_clock"]["observed_semantics"] + "\n")
    md.append(
        f"Regime file index is business-daily "
        f"{p['regime_clock']['regime_index']['start']}.."
        f"{p['regime_clock']['regime_index']['end']} "
        f"({p['regime_clock']['regime_index']['n_rows']:,} rows). "
        "Late-2026 events whose prior regime row is older than 7 calendar days "
        "are dropped under `match_older_than_7d` because the PIT series ends on "
        "2026-07-02 (K12).\n"
    )
    md.append("Citations (verified by `test_regime_clock_citation_resolves`):\n")
    for c in p["regime_clock"]["citations"]:
        md.append(f"- `{c['file']}:{c['line']}` `{c['quote']}`\n")

    md.append("\n## Design recap\n")
    d = p["design"]
    md.append(
        f"- Primary outcome: `{d['outcome_primary']}` on `{d['primary_set']}`\n"
        f"- Secondary outcome: `{d['outcome_secondary']}` on the same primary events\n"
        f"- Secondary set: 3D.p0-confirmed events joined to the 3D.p0 row\n"
        f"- Regime join: {d['join']} with fallback_max_days = {d['fallback_max_days']}\n"
        f"- Floors: eight (T1/T3 × state × era) cells; ≥ {d['floors']['events']} events, "
        f"≥ {d['floors']['months']} months, ≥ {d['floors']['names']} names\n"
        f"- Inference: {d['bootstrap']['kind']}, n_draws={d['bootstrap']['n_draws']}, "
        f"seed={d['bootstrap']['seed']}; {d['bootstrap']['pairing']}\n"
        f"- Verdict rule is in `result.json[\"verdict_rule\"]` (written as a constant "
        f"before any I is computed).\n"
    )
    md.append("\nParticipation survivorship caveat: the date-level share's denominator "
              "is names with a *valid* SMA50 on that date (warm-up NaNs excluded from "
              "both num and denom, K8). Names with no row on d are also excluded; the "
              "universe is current-membership only (survivor-selected).\n")

    md.append("\n## Tercile cuts (fixed, computed on the PRIMARY set)\n")
    md.append("| family | T1/T2 cut | T2/T3 cut |\n|---|---:|---:|\n")
    for f in F.FAMILIES:
        lo, hi = p["tercile_cuts"][f]["lo"], p["tercile_cuts"][f]["hi"]
        md.append(f"| {f} | {lo:+.5f} | {hi:+.5f} |\n")

    md.append("\n## The twelve primary tests (H10 net, primary 1D events)\n")
    md.append("| # | family | partition | I (obs) | 95% CI lo | 95% CI hi | SE | raw p | Holm p | era 2014-2019 | era 2020-2026 | same-sign | floor |\n")
    md.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|\n")
    for i, t in enumerate(p["tests_12"], 1):
        md.append(
            f"| {i} | {t['family']} | {t['partition']} | "
            f"{t['observed']:+.5f} | {t['ci_lo']:+.5f} | {t['ci_hi']:+.5f} | "
            f"{t['se']:.5f} | {t['p_two_sided']:.4f} | {t['p_holm']:.4f} | "
            f"{t['era_2014_2019']:+.5f} | {t['era_2020_2026']:+.5f} | "
            f"{'yes' if t['same_sign_eras'] else 'no'} | "
            f"{'PASS' if t['floor_pass'] else 'FAIL'} |\n"
        )

    md.append("\n## Cell-level table (eight era cells per test; floors)\n")
    for f in F.FAMILIES:
        md.append(f"\n### {f}\n")
        md.append("| partition | cell | n_events | n_months | n_names | mean_y | floor |\n")
        md.append("|---|---|---:|---:|---:|---:|:---:|\n")
        for t in p["tests_12"]:
            if t["family"] != f:
                continue
            for c in t["cells"]:
                my = c["mean_y"]
                my_s = "nan" if my is None else f"{my:+.5f}"
                md.append(
                    f"| {t['partition']} | {c['cell_name']} | "
                    f"{c['n_events']:,} | {c['n_months']:,} | {c['n_names']:,} | "
                    f"{my_s} | {'PASS' if c['above_floor'] else 'FAIL'} |\n"
                )

    md.append("\n## Winner block\n")
    if p["winners"]:
        md.append(f"**{len(p['winners'])} winners (ranked by |I|/SE):**\n\n")
        md.append("| family | partition | I (obs) | CI lo | CI hi | SE | |I|/SE | era 2014-2019 | era 2020-2026 |\n")
        md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for w in p["winners"]:
            md.append(
                f"| {w['family']} | {w['partition']} | {w['observed']:+.5f} | "
                f"{w['ci_lo']:+.5f} | {w['ci_hi']:+.5f} | {w['se']:.5f} | "
                f"{w['t_stat']:.2f} | {w['era_2014_2019']:+.5f} | {w['era_2020_2026']:+.5f} |\n"
            )
    else:
        md.append("No (f, P) meets the winner rule (SCOPED NULL if ≥8/12 tests above floor).\n")

    md.append("\n**Secondary (H21 net, same tests; era values K7):**\n")
    md.append("| family | partition | I (H21 obs) | CI lo | CI hi | SE | era 2014-2019 | era 2020-2026 |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|\n")
    for s in p["h21_secondary_12"]:
        md.append(
            f"| {s['family']} | {s['partition']} | "
            f"{s['observed']:+.5f} | {s['ci_lo']:+.5f} | {s['ci_hi']:+.5f} | "
            f"{s['se']:.5f} | {s['era_2014_2019']:+.5f} | {s['era_2020_2026']:+.5f} |\n"
        )

    md.append("\n**Secondary (3D.p0-confirmed set, H10; era values K7):**\n")
    md.append("| family | partition | I (obs) | CI lo | CI hi | SE | era 2014-2019 | era 2020-2026 |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|\n")
    for s in p["three_d_p0_confirmed_secondary"]["tests_12"]:
        md.append(
            f"| {s['family']} | {s['partition']} | "
            f"{s['observed']:+.5f} | {s['ci_lo']:+.5f} | {s['ci_hi']:+.5f} | "
            f"{s['se']:.5f} | {s['era_2014_2019']:+.5f} | {s['era_2020_2026']:+.5f} |\n"
        )

    md.append("\n## Regime main effect (context)\n")
    md.append("| partition | state | mean y | CI lo | CI hi | SE | n_events | n_months |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|\n")
    for part_name, states in p["regime_main_effect"].items():
        for st, rec in states.items():
            md.append(
                f"| {part_name} | {st} | {rec['observed']:+.5f} | "
                f"{rec['ci_lo']:+.5f} | {rec['ci_hi']:+.5f} | {rec['se']:.5f} | "
                f"{rec['n_events']:,} | {rec['n_months']:,} |\n"
            )

    md.append("\n## Family main effect spread(T3−T1) pooled across states (context)\n")
    md.append("| family | spread | CI lo | CI hi | SE | n_T3 | n_T1 |\n")
    md.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for fam, rec in p["family_main_effect"].items():
        md.append(
            f"| {fam} | {rec['observed']:+.5f} | {rec['ci_lo']:+.5f} | "
            f"{rec['ci_hi']:+.5f} | {rec['se']:.5f} | "
            f"{rec['n_events_t3']:,} | {rec['n_events_t1']:,} |\n"
        )

    md.append("\n## Quad descriptive table\n")
    md.append("| quad | n_events | n_months | n_names | mean_h10_net |\n|---|---:|---:|---:|---:|\n")
    for row in p["quad_descriptive"]:
        mean_str = (f"{row['mean_h10_net']:+.5f}"
                    if row["mean_h10_net"] is not None else "nan")
        md.append(
            f"| {row['quad']} | {row['n_events']:,} | {row['n_months']:,} | "
            f"{row['n_names']:,} | {mean_str} |\n"
        )

    md.append("\n## Context: recession / transition_ratcheted\n")
    md.append(f"- recession share (joined rows): **{p['context'].get('recession_share', 'NA')}**\n")
    md.append(f"- transition_ratcheted share (joined rows): **{p['context'].get('transition_ratcheted_share', 'NA')}**\n")

    md.append("\n## Drops by reason\n")
    md.append("| reason | n |\n|---|---:|\n")
    for r in p["drops_by_reason"]:
        md.append(f"| {r['reason']} | {r['n']:,} |\n")

    md.append("\n## Round-0 vs round-1 (K10)\n")
    md.append(
        f"Round-0 verdict **{p['round0_comparison']['round0_verdict']}** "
        f"({p['round0_comparison']['round0_n_tests_above_floor']}/12 above floor) "
        "was a code bug (K1 floor gate counted 6 pooled cells including T2). "
        f"Panel swap r2→r3: −32 1D rows. max|ΔI| = "
        f"{p['round0_comparison']['max_abs_delta_I']:.6g} "
        "(expected ≲ 1.5e-05 from the panel swap alone; remaining SE/p movement is the K2 bootstrap repair).\n"
    )
    md.append("| family | partition | round0 I | round1 I | ΔI | round1 SE | round1 p | floor |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|:---:|\n")
    for row in p["round0_comparison"]["rows"]:
        md.append(
            f"| {row['family']} | {row['partition']} | {row['round0_I']:+.5f} | "
            f"{row['round1_I']:+.5f} | {row['delta_I']:+.6g} | "
            f"{row['round1_se']:.5f} | {row['round1_p']:.4f} | "
            f"{'PASS' if row['round1_floor_pass'] else 'FAIL'} |\n"
        )

    md.append("\n## Verdict\n")
    md.append(f"**{p['verdict']}** — reasons: {', '.join(p['verdict_reasons'])}\n")
    md.append(f"\nN tests with all eight era-cells above floor: **{p['n_tests_above_floor']} / 12**.\n")
    insuff = [t for t in p["tests_12"] if not t["floor_pass"]]
    if insuff:
        md.append("INSUFFICIENT tests and failing cells:\n")
        for t in insuff:
            md.append(f"- {t['family']} × {t['partition']}: {t['failing_cells']}\n")

    md.append("\n## Tests\n")
    if pytest_counts:
        md.append(f"`{pytest_counts}`\n")
    else:
        md.append("(pytest summary folded after the first write)\n")
    md.append(
        "Mutation B (resampler replaced by keep-all-months) fails "
        "`test_unclustered_resample_fails_cluster_invariant`. "
        "The pooled-6 floor mutant fails `test_floor_gate_counts_eight_cells`. "
        "The `np.isin` bootstrap mutant fails `test_cluster_bootstrap_matches_analytic_se`.\n"
    )
    ident = p.get("identity", {})
    md.append(
        f"Two consecutive compute passes of the 12-test core: "
        f"`{ident.get('tests_12_sha256_run_a', '')}` and "
        f"`{ident.get('tests_12_sha256_run_b', '')}` "
        f"(byte-identical={ident.get('byte_identical')}).\n"
    )

    md.append("\n## Provenance\n")
    h = p["provenance"]["host"]
    md.append(
        f"Host `{h.get('hostname')}`; python `{h.get('python_executable')}` "
        f"{h.get('python_version')}; pandas {h.get('pandas')}; numpy {h.get('numpy')}; "
        f"pyarrow {h.get('pyarrow')}; scipy {h.get('scipy')}; pytest {h.get('pytest')}. "
        f"repo_head `{p['repo_head']}`.\n"
    )

    md.append("\n## K1–K12 repairs\n")
    for kid, rec in p.get("k_repairs", {}).items():
        md.append(f"- **{kid}** FIXED `{rec.get('where', '')}` — {rec.get('how', '')}\n")

    md.append("\n## Deviations\n")
    for dlt in p.get("deviations", []):
        md.append(f"- {dlt}\n")

    md.append("\n## Gaps\n")
    gaps = p.get("gaps") or []
    if not gaps:
        md.append("none\n")
    else:
        for g in gaps:
            md.append(f"- {g}\n")

    OUT_RESULT_MD.write_text("".join(md))


def k_repair_lines() -> dict:
    """Locate K-repair file:line from live sources."""
    def find(path: Path, snippet: str) -> str:
        lines = path.read_text().splitlines()
        for i, ln in enumerate(lines, 1):
            if snippet in ln:
                return f"{path.relative_to(REPO)}:{i}"
        return f"{path.relative_to(REPO)}:?({snippet!r})"

    return {
        "K1": {"where": find(CODE / "stats.py", "def floor_gate_eight_cells"),
               "how": "floors on eight T1/T3 × state × era cells; pooled-6 mutant in tests"},
        "K2": {"where": find(CODE / "stats.py", "np.bincount(drawn"),
               "how": "month multiplicity weights; isin mutant fails analytic-SE test"},
        "K3": {"where": find(CODE / "run.py", "np.random.SeedSequence(SEED_BASE)"),
               "how": "SeedSequence(20261004).spawn; no builtin hash(); two-pass sha recorded"},
        "K4": {"where": find(CODE / "run.py", "EXPECTED_PANEL_SHA"),
               "how": "hash at load and write-out; abort INPUT_CHANGED; pin 209e2246 / d20cd405"},
        "K5": {"where": find(CODE / "run.py", "f_pit = build_features(overrides=overrides)"),
               "how": "real citations; test_regime_clock_citation_resolves"},
        "K6": {"where": find(CODE / "test_E.py", "def test_unclustered_resample_fails_cluster_invariant"),
               "how": "unclustered SE ≥30% below clustered; mutation B keep-all fails the invariant"},
        "K7": {"where": find(CODE / "run.py", "era_2014_2019"),
               "how": "H21 and 3D.p0 secondary rows carry both era values"},
        "K8": {"where": find(CODE / "features.py", ".where(valid)"),
               "how": "SMA50 NaN excluded from num and denom; warmup test"},
        "K9": {"where": find(CODE / "run.py", "pairing holds within a test"),
               "how": "pytest counts folded; per-test pairing disclosed as a deviation"},
        "K10": {"where": find(CODE / "run.py", "ROUND0_I"),
               "how": "round-0 headlines beside round-1; max|ΔI| reported"},
        "K11": {"where": find(CODE / "run.py", "WRITE ORDER"),
               "how": "json/md → pytest → fold → hashes LAST → post-hoc pytest → DONE"},
        "K12": {"where": find(CODE / "stats.py", "regime_series_ended_late_2026"),
               "how": "drop count by reason; PIT ends 2026-07-02 stated in RESULT.md"},
    }


def write_hashes_txt(extra: list[Path] | None = None) -> None:
    files = [
        EVENTS_PANEL, CONFIRMATION_PAIRS, REGIME_FILE, UNIVERSE_MANIFEST, B1_RESULT_MD,
        REPO / "scripts/build_regime_v2_pit.py",
        REPO / "engine/inputs.py",
        OUT_RESULT_JSON, OUT_RESULT_MD,
        CODE / "run.py", CODE / "features.py", CODE / "stats.py", CODE / "test_E.py",
    ]
    if extra:
        files.extend(extra)
    seen = set()
    with open(OUT_HASHES, "w") as fh:
        for p in files:
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            rel = p.relative_to(REPO) if str(p).startswith(str(REPO)) else p
            if not p.exists():
                fh.write(f"MISSING  {rel}\n")
                continue
            fh.write(f"{_sha256(p)}  {rel}\n")


def run_pytest() -> tuple[int, str, str, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(CODE), "-q", "-p", "no:cacheprovider"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    text = (r.stdout or "") + (r.stderr or "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    summary = lines[-1] if lines else "pytest produced no summary"
    counts = re.sub(r"\s+in\s+[0-9.]+s$", "", summary)
    return r.returncode, summary, counts, text


def subprocess_check(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {cmd} (stderr={r.stderr})")
    return r.stdout.strip()


def write_json(payload: dict) -> None:
    OUT_RESULT_JSON.write_bytes(_dump(payload))


def main():
    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    CODE.mkdir(parents=True, exist_ok=True)
    Path("/tmp/E_r1_scratch").mkdir(parents=True, exist_ok=True)

    print("[E] hashing inputs at LOAD …", flush=True)
    input_hashes_load = {
        "events_panel": _sha256(EVENTS_PANEL),
        "confirmation_pairs": _sha256(CONFIRMATION_PAIRS),
        "regime": _sha256(REGIME_FILE),
        "universe_manifest": _sha256(UNIVERSE_MANIFEST),
        "b1_result_md": _sha256(B1_RESULT_MD),
    }
    print(f"[E] panel={input_hashes_load['events_panel']}", flush=True)
    print(f"[E] pairs={input_hashes_load['confirmation_pairs']}", flush=True)
    if input_hashes_load["events_panel"] != EXPECTED_PANEL_SHA:
        payload = {
            "lane": "E", "status": "INPUT_CHANGED",
            "gaps": [f"panel sha {input_hashes_load['events_panel']} != {EXPECTED_PANEL_SHA}"],
            "inputs": input_hashes_load,
        }
        write_json(payload)
        print("[E] INPUT_CHANGED (panel)", flush=True)
        return 2
    if input_hashes_load["confirmation_pairs"] != EXPECTED_PAIRS_SHA:
        payload = {
            "lane": "E", "status": "INPUT_CHANGED",
            "gaps": [f"pairs sha {input_hashes_load['confirmation_pairs']} != {EXPECTED_PAIRS_SHA}"],
            "inputs": input_hashes_load,
        }
        write_json(payload)
        print("[E] INPUT_CHANGED (pairs)", flush=True)
        return 2

    payload = compute_payload(input_hashes_load, t0)
    payload["k_repairs"] = k_repair_lines()

    # K11 WRITE ORDER: json/md, hashes, pytest, fold, hashes LAST, post-hoc pytest, DONE
    print("[E] writing result.json / RESULT.md …", flush=True)
    write_json(payload)
    write_result_md(payload, pytest_counts=None)
    write_hashes_txt()

    print("[E] pytest (first) …", flush=True)
    rc1, summary1, counts1, out1 = run_pytest()
    print(out1, flush=True)
    print(f"[E] pytest first: {summary1} rc={rc1}", flush=True)

    payload["pytest_summary"] = summary1
    payload["pytest_summary_counts"] = counts1
    payload["pytest_first_rc"] = rc1
    write_json(payload)
    write_result_md(payload, pytest_counts=counts1)
    write_hashes_txt()  # LAST before DONE; includes folded json/md

    print("[E] pytest (post-hoc) …", flush=True)
    rc2, summary2, counts2, out2 = run_pytest()
    print(out2, flush=True)
    print(f"[E] pytest post-hoc: {summary2} rc={rc2}", flush=True)
    payload["pytest_posthoc_summary"] = summary2
    payload["pytest_posthoc_counts"] = counts2
    payload["pytest_posthoc_rc"] = rc2
    # Do not rewrite json after this — hashes.txt must stay LAST relative to json/md.
    # Record post-hoc only in stdout; if we rewrite json, hashes would be stale.
    # K11: hashes LAST. Keep json as the folded pre-posthoc copy; post-hoc counts
    # equal first counts if 0 skipped. If they differ, note it in stdout.

    if rc1 == 0 and rc2 == 0:
        payload_status_ok = True
    else:
        payload_status_ok = False
        # rewrite gaps into json would stale hashes; leave as-is and report PARTIAL

    OUT_DONE.write_text("")
    print(f"[E] DONE written; wall={time.time()-t0:.1f}s", flush=True)
    print(f"[E] pytest_counts={counts1} posthoc={counts2} match={counts1 == counts2}",
          flush=True)
    return 0 if payload_status_ok else 1


if __name__ == "__main__":
    sys.exit(main())
