"""Catalogue read v2: the five Risk Radar -v2 sets, scored under the r1g conventions.

Bounded research worker. Paper-only: nothing sizes, ranks or executes.

    python3 run_read_v2.py --desk <path to the read-only desk v4>
    ROTATION_DESK=<path> python3 run_read_v2.py

Reads (never writes) the desk. The desk path is a required argument or environment
variable; no absolute path is baked into this file.

Sets (spec = the five ledger rows whose ids end in -v2):
    R-off {incumbent, confluence_k4};  R-on {incumbent, confluence_k4, exit_v1}
Each is scored SHIFTED (t+1 on the full alert series before windowing, as r1g) and also
UNSHIFTED as a secondary row that cannot pass. Components (k = 1..12 and each of the 12
legs alone, both families, shifted, 500 draws) are descriptive only.

Scorer: mirrors reads/r1g/code/r1lib.run_job -- desk swing episodes built with
adapter.build_episodes_for_series(..., episode_rule="swing"), the desk pass line with
require_activity=True, and pivots.score_pivots_multi for detail.

Alerts come from the Macro engine (whose inputs carry the prereg-addendum-3 point-in-time
FRED replay); scoring comes from the desk's vendored kit. `engine` is a package name in both
trees, so the two phases are loaded in sequence with an explicit module purge and an
assertion on each resolved file.

The k=3 follow-up row (rr-roff-confluence-k3-followup) is deliberately NOT scored: it is a
PRE-block decisive read gated on bm_ref, and the brief forbids reading it on any block.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(_ROOT))

import numpy as np                                                   # noqa: E402
import pandas as pd                                                  # noqa: E402

ADAPTER_PIN = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"
HERE = Path(__file__).resolve().parent

START_D = pd.Timestamp("2020-01-02")
END_D = pd.Timestamp("2023-12-29")
BUILD_START = pd.Timestamp("2019-06-03")
SEED = 20261112
PRE = 21
MIN_OFF = 10
N_DRAWS = 2000          # the five sets and their unshifted controls
N_DRAWS_COMP = 500      # component reads (k-curve, single legs) -- descriptive only
TOL = 0.01
LOUD = ("elevated", "risk-off")
GATE_BREADTH = 0.40
POSTS = (5, 10, 21)
PRIMARY_POST = {"R-off": 5, "R-on": 10}
DIRECTION = {"R-off": "top", "R-on": "bottom"}
CATCH_TARGET = 0.75
FALSE_TARGET = 2.0

LEGS = ["credit_oas_roc", "credit_hyg_tlt", "rates_move", "rates_realrate", "bubble_ext",
        "bubble_leadership", "growth_defensives", "growth_cyc_def", "vol_term",
        "global_breadth", "jpy_carry", "corr_floor_break"]

NO_VERDICT = ("No set-level verdict: the budget-matched reference (bm_ref) does not exist yet "
              "(Principal ruling 2026-11-12 10:25Z).")

COLS = ["family", "set", "direction", "role", "primary_post", "n_draws", "seed",
        "turns_scored", "turns_flagged", "turn_share", "turn_lo90", "turn_hi90",
        "clusters_scored", "clusters_flagged", "cluster_share", "cluster_lo90", "cluster_hi90",
        "median_delay_sessions", "false_col", "false_per_asset_year", "alert_on_share",
        "sessions_in_episode", "spans", "open_spans", "false_calls", "false_in_rebound",
        "assets", "assets_pass", "assets_no_calls", "clusters_pass_all_assets",
        "clusters_pass_any_asset", "catch_target_75", "catch_gap_pp", "false_target_2",
        "censored"]


# --------------------------------------------------------------------- desk + module paths
def setup_desk(desk: Path) -> None:
    for p in (desk / "reads" / "r1g" / "code", desk, desk / "catalogue", desk / "pivot"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def adapter_sha(desk: Path) -> str:
    return hashlib.sha256((desk / "catalogue" / "adapter.py").read_bytes()).hexdigest()


def purge_engine() -> None:
    for m in [m for m in sys.modules if m == "engine" or m.startswith("engine.")]:
        del sys.modules[m]


def load_macro_engine() -> None:
    """Macro's engine (point-in-time FRED replay) must win for the alert phase."""
    sys.path.insert(0, str(_ROOT))
    purge_engine()
    import engine.risk_radar_eval.inputs as I                      # noqa: F401
    if _ROOT not in Path(I.__file__).resolve().parents:
        raise SystemExit(f"engine.inputs resolved outside the worktree: {I.__file__}")


def load_desk_kit(desk: Path):
    """The desk's vendored scorer must win for the scoring phase.

    Both trees expose a top-level package named `engine`, and the Macro root (plus the cwd or
    script dir) is on sys.path from the alert phase. Drop those ahead of the desk's
    `pivot/radar_eval` root, then assert the resolved files really are the desk's.
    """
    sys.path[:] = [p for p in sys.path if p not in ("", ".", str(_ROOT))]
    sys.path.insert(0, str(desk / "pivot" / "radar_eval"))
    purge_engine()
    from catalogue import adapter as A
    pv, L = A.load_radar_kit()
    if desk not in Path(pv.__file__).resolve().parents:
        raise SystemExit(f"desk kit resolved outside the desk: {pv.__file__}")
    return A, pv, L


# --------------------------------------------------------------------- alerts (Macro engine)
def build_alerts(ledger_legs: dict[str, float]) -> dict[str, pd.Series]:
    from engine import risk_radar as rr
    from engine.risk_radar_eval import inputs as I
    from engine.risk_radar_eval import walkforward as W
    from engine.risk_radar_eval import availability as AV
    from engine.risk_radar_eval import labels as L
    from lib import store

    sigs = I.incumbent_signals()
    calib = rr._calib()
    subs = rr.subscore_series(sigs, calib)
    gate = I.gate_series(I.gate_components(subs.index), GATE_BREADTH)
    states = W.states_for(subs, sigs, calib, gate, 0)
    loud = states.isin(LOUD)

    win = (loud.index >= BUILD_START) & (loud.index <= END_D)
    loud_w = loud[win]
    sess = loud_w.index
    out: dict[str, pd.Series] = {"incumbent": loud_w.astype(bool)}

    n_on = pd.Series(0, index=sigs.index, dtype=int)
    for leg, thr in ledger_legs.items():
        on = (sigs[leg] >= thr).fillna(False).astype(bool)
        out[f"leg__{leg}"] = on[win].astype(bool)
        n_on = n_on + on.astype(int)
    for k in range(1, len(ledger_legs) + 1):
        out[f"confluence_k{k}"] = (n_on >= k)[win].astype(bool)

    spy = L.spy_total_return()
    spy.index = pd.to_datetime(spy.index)
    hy = store.read("fred", "BAMLH0A0HYM2")["hy_oas"].astype(float).dropna()
    hy.index = pd.to_datetime(hy.index)
    known = AV.known_at(hy, "BAMLH0A0HYM2", sess)
    hy_val = pd.Series(np.nan, index=sess, dtype=float)
    ok = known.notna()
    hy_val[ok] = hy.reindex(known[ok].values).values

    spy_s = spy.reindex(sess).ffill()
    loud_a = loud_w.to_numpy(dtype=bool)
    spy_a = spy_s.to_numpy(dtype=float)
    hy_a = hy_val.to_numpy(dtype=float)
    n = len(sess)
    alert = np.zeros(n, dtype=bool)
    armed, low, quiet = False, np.inf, 0
    for i in range(n):
        if loud_a[i]:
            if not armed:
                armed, low = True, spy_a[i]
            else:
                low = min(low, spy_a[i])
            alert[i], quiet = True, 0
            continue
        quiet += 1
        if not armed:
            continue
        low = min(low, spy_a[i])
        cond1 = quiet >= 5
        cond2 = (i >= 10 and np.isfinite(hy_a[i]) and np.isfinite(hy_a[i - 10])
                 and hy_a[i] <= hy_a[i - 10])
        cond3 = np.isfinite(spy_a[i]) and np.isfinite(low) and spy_a[i] >= 1.03 * low
        if cond1 and cond2 and cond3:
            armed = False
        else:
            alert[i] = True
    out["exit_v1"] = pd.Series(alert, index=sess, dtype=bool)
    return out


def consistency_check(loud: pd.Series) -> dict:
    p = _ROOT / "data" / "risk_radar" / "walkforward_alert_series.csv"
    csv = pd.read_csv(p, comment="#", parse_dates=["date"]).set_index("date")["loud"].astype(bool)
    win = csv.index[(csv.index >= pd.Timestamp("2022-01-03")) & (csv.index <= END_D)]
    ours = loud.reindex(win)
    mism = int((ours.fillna(False).astype(bool) != csv.reindex(win)).sum())
    return {"window": [str(win.min().date()), str(win.max().date())],
            "n_sessions": int(len(win)), "missing_in_ours": int(ours.isna().sum()),
            "mismatches": mism,
            "shipped_loud_share": float(csv.reindex(win).mean()),
            "ours_loud_share": float(ours.fillna(False).mean())}


# --------------------------------------------------------------------- windowing (r1g)
def window_alert(alert: pd.Series, lvl: pd.Series, shift: bool):
    """Shift on the full series, then window D-start minus PRE through 2023-12-29 (r1g)."""
    full = alert.astype(bool)
    if shift:
        full = full.shift(1, fill_value=False).astype(bool)
    idx = lvl.index
    lo = max(0, int(idx.searchsorted(START_D)) - PRE)
    a_idx = idx[lo:]
    a_idx = a_idx[a_idx <= END_D]
    a = full.reindex(a_idx, method="ffill")
    if a.isna().any():
        raise ValueError("alert has NaN after reindex")
    return lvl.reindex(a_idx), a.astype(bool)


def episode_coverage(spec, asset_eps) -> float | None:
    s = spec.series.astype(float).sort_index()
    idx = s.index[(s.index >= START_D) & (s.index <= END_D)]
    if len(idx) == 0:
        return None
    mask = np.zeros(len(idx), dtype=bool)
    for e in asset_eps:
        lo = max(e.onset, START_D)
        hi = min(e.recovery if e.recovery is not None else END_D, END_D)
        if hi < lo:
            continue
        mask |= (idx >= lo) & (idx <= hi)
    return float(mask.mean())


def false_and_rebound(pv, alert: pd.Series, asset_turns: list, eps: list, direction: str,
                      post: int, premature_all_clear: int):
    """r1g collect.kit_false_and_rebound, using the scorer's own per-asset turn rows."""
    if direction != "top":
        return int(premature_all_clear), None, 0
    aidx = alert.index
    starts, _ends, _flick = pv._calls(alert, MIN_OFF)
    used: set[int] = set()
    for t in asset_turns:
        if t.get("status") != "scored" or not t.get("flagged"):
            continue
        p = int(aidx.searchsorted(pd.Timestamp(t["date"])))
        if p >= len(aidx) or aidx[p] != pd.Timestamp(t["date"]):
            continue
        used |= {c for c in starts if p - PRE <= c <= p + post}

    def in_span(i: int) -> bool:
        for e in eps:
            if e.onset is None:
                continue
            h = aidx.max() if e.recovery is None else pd.Timestamp(e.recovery)
            if pd.Timestamp(e.onset) <= aidx[i] <= h:
                return True
        return False

    false = [i for i in starts if i not in used and not in_span(i)]
    phases = []
    for k, e in enumerate(eps):
        if e.trough is None:
            continue
        hi = eps[k + 1].peak if k + 1 < len(eps) else aidx.max()
        phases.append((pd.Timestamp(e.trough), pd.Timestamp(hi)))
    reb = sum(1 for i in false if any(l < aidx[i] <= h for l, h in phases))
    return len(false), reb, 0


# --------------------------------------------------------------------- one job
_G: dict = {}


def _init(alerts, specs, df, pv, turns_by_fam, rows_by_fam, episodes_by_fam) -> None:
    _G.update(alerts=alerts, specs=specs, df=df, pv=pv, turns=turns_by_fam,
              rows=rows_by_fam, episodes=episodes_by_fam)


def run_one(family: str, setname: str, alert_key: str, n_draws: int, shift: bool,
            role: str) -> dict:
    import r1lib as R
    from catalogue import adapter as A
    direction = DIRECTION[family]
    specs, pv = _G["specs"], _G["pv"]
    src = _G["alerts"][alert_key]
    turns = _G["turns"][family]
    episodes = _G["episodes"][family]
    series = sorted(_G["rows"][family]["series"].unique())

    px, alerts, on_start = {}, {}, {}
    for name in series:
        lvl = R.level_series(specs[name])
        p_, a_ = window_alert(src, lvl, shift)
        px[name], alerts[name] = p_, a_
        on_start[name] = bool(a_.iloc[0]) if len(a_) else None

    pl = A.run_pass_line(turns, alerts, episodes, px, outcomes_through=END_D,
                         posts=POSTS, n_draws=n_draws, tol=TOL, seed=SEED,
                         min_off=MIN_OFF, pre=PRE, require_activity=True)
    det = pv.score_pivots_multi(turns, alerts, episodes, outcomes_through=END_D,
                                posts=POSTS, pre=PRE, min_off=MIN_OFF)

    covs = [episode_coverage(specs[a], episodes.get(a, [])) for a in series]
    covs = [c for c in covs if c is not None]
    cov = float(np.mean(covs)) if covs else None
    n_eps = sum(len(episodes.get(a, [])) for a in series)
    n_open = sum(1 for a in series for e in episodes.get(a, []) if e.trough is None)

    out = {"family": family, "set": setname, "alert_key": alert_key, "direction": direction,
           "role": role, "shifted": bool(shift), "post": PRIMARY_POST[family],
           "posts": list(POSTS), "n_draws": n_draws, "seed": SEED, "tol": TOL,
           "tier": "major", "pre": PRE, "min_off": MIN_OFF,
           "outcomes_through": str(END_D.date()), "n_turns": len(turns), "series": series,
           "episodes": {a: len(v) for a, v in episodes.items()},
           "sessions_in_episode": None if cov is None else round(cov, 3),
           "spans": n_eps, "open_spans": n_open,
           "alert_on_at_pre_window_start": on_start, "by_post": {}}

    for pp in POSTS:
        key = f"post{pp}"
        k = direction
        s, plk = det["by_post"][key][k], pl["by_post"][key][k]
        fk = ("false_risk_off_per_asset_year" if k == "top"
              else "premature_all_clear_per_asset_year")
        prow = []
        for a, v in det["by_post"][key]["by_asset"].items():
            for t in v["turns"]:
                prow.append({"asset": a, "date": t["date"], "kind": t["kind"],
                             "status": t["status"], "flagged": t.get("flagged"),
                             "delay": t.get("delay"), "on_at_turn": t.get("on_at_turn"),
                             "cluster_id": t.get("cluster_id")})
        out["by_post"][key] = {
            "post": pp,
            "turns_scored": s["n_turns"], "turns_flagged": s["flagged"],
            "turn_share": s["share_flagged"], "turn_share_ci90": s["share_ci90"],
            "clusters_scored": s["n_clusters"], "clusters_flagged": s["clusters_flagged"],
            "cluster_share": s["cluster_share_flagged"],
            "cluster_share_ci90": s["cluster_share_ci90"],
            "median_delay": s["median_delay"], "censored": s["censored"],
            "false_per_asset_year": det["by_post"][key][fk],
            "pass_line": {kk: plk.get(kk) for kk in
                          ("assets", "assets_pass", "assets_no_calls", "assets_fail",
                           "clusters", "clusters_pass_all_assets",
                           "clusters_pass_any_asset")},
            "by_asset": {a: plk["by_asset"].get(a) for a in det["by_post"][key]["by_asset"]},
            "turn_rows": prow,
            "alert_budget": float(np.mean([alerts[a].mean() for a in series])) if series else None,
        }

    # false / rebound at the primary post only (r1g collect)
    key = f"post{PRIMARY_POST[family]}"
    n_false = n_reb = 0
    kit_false = 0
    for a in series:
        ba = det["by_post"][key]["by_asset"].get(a, {})
        kit_false += int(ba.get("false_risk_off" if direction == "top"
                                else "premature_all_clear", 0) or 0)
        f, r, _m = false_and_rebound(pv, alerts[a], ba.get("turns", []), episodes.get(a, []),
                                     direction, PRIMARY_POST[family],
                                     ba.get("premature_all_clear", 0))
        n_false += f
        n_reb += (r or 0)
    out["false_calls"] = n_false
    out["false_in_rebound"] = n_reb if direction == "top" else None
    # our re-derivation must equal the kit's own false-series count (r1g collect asserts this)
    out["false_count_matches_kit"] = (n_false == kit_false)
    out["kit_false_count"] = kit_false
    return out


def _safe(args):
    family, setname, key, nd, shift, role = args
    t0 = time.time()
    try:
        r = run_one(family, setname, key, nd, shift, role)
        r["runtime_s"] = round(time.time() - t0, 1)
        return r
    except Exception as exc:                                        # noqa: BLE001
        import traceback
        return {"family": family, "set": setname, "alert_key": key, "error": str(exc),
                "traceback": traceback.format_exc(), "runtime_s": round(time.time() - t0, 1)}


def jobs() -> list:
    j = []
    sets = {"R-off": ["incumbent", "confluence_k4"],
            "R-on": ["incumbent", "confluence_k4", "exit_v1"]}
    for fam, names in sets.items():
        for nm in names:
            j.append((fam, nm, nm, N_DRAWS, True, "set"))
            j.append((fam, nm, nm, N_DRAWS, False, "control (unshifted; cannot pass)"))
    for fam in ("R-off", "R-on"):
        for k in range(1, 13):
            j.append((fam, f"component_k{k}", f"confluence_k{k}", N_DRAWS_COMP, True,
                      "component (cannot pass; descriptive only)"))
        for leg in LEGS:
            j.append((fam, f"leg_{leg}", f"leg__{leg}", N_DRAWS_COMP, True,
                      "component (cannot pass; descriptive only)"))
    return j


def jid(family: str, setname: str, shift: bool) -> str:
    d = DIRECTION[family]
    if setname.startswith(("component_", "leg_")):
        return f"{family}__{setname}__{d}"
    return f"{family}__{setname}__{d}{'' if shift else '__unshifted'}"


# --------------------------------------------------------------------- table rows (r1g columns)
def row_of(d: dict) -> dict:
    bp = d["by_post"][f"post{d['post']}"]
    pl = bp["pass_line"]
    ts = bp["turn_share"] or 0
    return {"family": d["family"], "set": d["set"], "direction": d["direction"],
            "role": d["role"], "primary_post": d["post"], "n_draws": d["n_draws"],
            "seed": d["seed"],
            "turns_scored": bp["turns_scored"], "turns_flagged": bp["turns_flagged"],
            "turn_share": bp["turn_share"],
            "turn_lo90": (bp["turn_share_ci90"] or [None, None])[0],
            "turn_hi90": (bp["turn_share_ci90"] or [None, None])[1],
            "clusters_scored": bp["clusters_scored"],
            "clusters_flagged": bp["clusters_flagged"],
            "cluster_share": bp["cluster_share"],
            "cluster_lo90": (bp["cluster_share_ci90"] or [None, None])[0],
            "cluster_hi90": (bp["cluster_share_ci90"] or [None, None])[1],
            "median_delay_sessions": bp["median_delay"],
            "false_col": ("false_risk_off_per_asset_year" if d["direction"] == "top"
                          else "premature_all_clear_per_asset_year"),
            "false_per_asset_year": bp["false_per_asset_year"],
            "alert_on_share": round(bp["alert_budget"], 3),
            "sessions_in_episode": d.get("sessions_in_episode"),
            "spans": d.get("spans"), "open_spans": d.get("open_spans"),
            "false_calls": d.get("false_calls"),
            "false_in_rebound": d.get("false_in_rebound"),
            "assets": pl["assets"], "assets_pass": pl["assets_pass"],
            "assets_no_calls": pl["assets_no_calls"],
            "clusters_pass_all_assets": pl["clusters_pass_all_assets"],
            "clusters_pass_any_asset": pl["clusters_pass_any_asset"],
            "catch_target_75": "met" if ts >= CATCH_TARGET else "not met",
            "catch_gap_pp": round(100 * (ts - CATCH_TARGET), 1),
            "false_target_2": "met" if (bp["false_per_asset_year"] or 0) <= FALSE_TARGET
                              else "not met",
            "censored": bp["censored"]}


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float) and np.isnan(v):
                cells.append("")
            elif isinstance(v, float):
                cells.append(f"{v:.4g}")
            else:
                cells.append("" if v is None else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ap.add_argument("--summarize-only", action="store_true",
                    help="rebuild RESULTS/SUMMARY from the JSONs already on disk; score nothing")
    ns = ap.parse_args()
    if not ns.desk:
        raise SystemExit("desk path required: --desk <path> or ROTATION_DESK")
    desk = Path(ns.desk).resolve()
    HERE.mkdir(parents=True, exist_ok=True)
    if ns.summarize_only:
        return summarize_only(desk)

    got = adapter_sha(desk)
    (HERE / "RUN_LOG.txt").write_text(f"desk {desk}\nadapter sha (start) {got}\n")
    if got != ADAPTER_PIN:
        raise SystemExit(f"adapter sha {got} != pinned {ADAPTER_PIN}; STOP")
    print(f"adapter sha {got} == pin", flush=True)

    setup_desk(desk)
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("rr_ledger_rows", str(HERE.parent / "ledger_rows.py"))
    LR = _iu.module_from_spec(_s)
    _s.loader.exec_module(LR)
    assert set(LEGS) == set(LR.LEGS), (set(LEGS) ^ set(LR.LEGS))

    t0 = time.time()
    load_macro_engine()
    alerts = build_alerts(dict(LR.LEGS))
    print(f"alerts built in {time.time()-t0:.1f}s", flush=True)

    cc = consistency_check(alerts["incumbent"])
    (HERE / "consistency.json").write_text(json.dumps(cc, indent=1))
    print(f"CONSISTENCY {cc}", flush=True)

    A, pv, _L = load_desk_kit(desk)
    print(f"scorer {pv.__file__}", flush=True)
    import r1lib as R
    specs = R.load_specs()
    df = A.load_pivots()

    rows_by_fam, turns_by_fam, episodes_by_fam = {}, {}, {}
    for fam in ("R-off", "R-on"):
        rows = R.family_rows(df, fam)
        rd = rows[[R.direction_of(r) == DIRECTION[fam] for _, r in rows.iterrows()]].copy()
        rows_by_fam[fam] = rd
        series = sorted(rd["series"].unique())
        levels = {n: R.level_series(specs[n]) for n in series}
        episodes_by_fam[fam] = A.build_episodes_for_series(
            df, series, tier="major", calendar=None, levels=levels, episode_rule="swing")
        turns_by_fam[fam] = R.build_turns(rd, episodes_by_fam[fam])

    js = jobs()
    print(f"{len(js)} jobs", flush=True)

    results = {}
    with ProcessPoolExecutor(max_workers=min(20, len(js)), initializer=_init,
                             initargs=(alerts, specs, df, pv, turns_by_fam,
                                       rows_by_fam, episodes_by_fam)) as ex:
        futs = {ex.submit(_safe, a): a for a in js}
        for fut in as_completed(futs):
            fam, setname, key, nd, shift, role = futs[fut]
            r = fut.result()
            j = jid(fam, setname, shift)
            (HERE / f"{j}.json").write_text(json.dumps(r, indent=1))
            results[j] = r
            if "error" in r:
                print(f"ERROR {j}: {r['error']}", flush=True)
            else:
                bp = r["by_post"][f"post{r['post']}"]
                print(f"{j:46s} turns {bp['turns_scored']:3d} clus {bp['clusters_scored']:3d} "
                      f"share {bp['cluster_share']} false {bp['false_per_asset_year']} "
                      f"[{time.time()-t0:.0f}s]", flush=True)

    rows = [row_of(r) for r in results.values() if "error" not in r]
    tab = pd.DataFrame(rows)
    tab = tab.sort_values(["family", "role", "set"]).reset_index(drop=True)
    tab[COLS].to_csv(HERE / "results.csv", index=False)

    (HERE / "_run_index.json").write_text(json.dumps(
        {k: {"runtime_s": v.get("runtime_s"), "error": v.get("error")}
         for k, v in sorted(results.items())}, indent=1))

    end = adapter_sha(desk)
    wall = time.time() - t0
    (HERE / "RUN_LOG.txt").write_text(
        f"desk {desk}\n"
        f"adapter sha (start) {got}\n"
        f"adapter sha (end)   {end}\n"
        f"adapter sha matches pin at start and end: {got == end == ADAPTER_PIN}\n"
        f"consistency: {json.dumps(cc)}\n"
        f"jobs: {len(results)}; errors: {sum(1 for r in results.values() if 'error' in r)}; "
        f"wall: {wall:.0f}s\n")
    print(f"done {len(results)} jobs in {wall:.0f}s; sha end {end} (match {end == ADAPTER_PIN})",
          flush=True)

    write_summary(desk, tab, results, cc, got, end, wall)


# --------------------------------------------------------------------- summarize from disk
def summarize_only(desk: Path) -> None:
    """Rebuild results.csv and SUMMARY.md from the JSONs already written; scores nothing."""
    got = adapter_sha(desk)
    if got != ADAPTER_PIN:
        raise SystemExit(f"adapter sha {got} != pinned {ADAPTER_PIN}; STOP")
    cc = json.loads((HERE / "consistency.json").read_text())
    results = {}
    for p in HERE.glob("*.json"):
        if p.name in ("consistency.json", "_run_index.json", "ledger_rows_check.json"):
            continue
        d = json.loads(p.read_text())
        if "error" in d or "by_post" not in d:
            continue
        d["_id"] = p.stem
        results[p.stem] = d
    tab = pd.DataFrame([row_of(d) for d in results.values()])
    tab = tab.sort_values(["family", "role", "set"]).reset_index(drop=True)
    tab[COLS].to_csv(HERE / "results.csv", index=False)
    log = (HERE / "RUN_LOG.txt").read_text()
    wall = float(log.split("wall: ")[-1].split("s")[0]) if "wall: " in log else 0.0
    write_summary(desk, tab, results, cc, got, got, wall)


# --------------------------------------------------------------------- SUMMARY.md
def write_summary(desk: Path, tab: pd.DataFrame, results: dict, cc: dict,
                  sha_start: str, sha_end: str, wall: float) -> None:
    ref = pd.read_csv(desk / "reads" / "r1g" / "results.csv")
    ref = ref[ref["family"].isin(["R-off", "R-on"])
              & ref["set"].isin(["mech_dd_ge_5pct", "mech_near_high_1pct", "trend_200"])]
    ref = ref[COLS].copy()

    out = ["# Catalogue read v2 — the five Risk Radar -v2 sets (r1g conventions)", "",
           "Bounded research worker. Paper-only: nothing sizes, ranks or executes. "
           "No set-level verdict is issued (see §4).", "",
           "## 1. Adapter pin and consistency", "",
           f"- adapter sha256 at start: `{sha_start}`",
           f"- adapter sha256 at end: `{sha_end}`",
           f"- matches the pin `{ADAPTER_PIN}` at both ends: "
           f"**{sha_start == sha_end == ADAPTER_PIN}**",
           f"- consistency vs `data/risk_radar/walkforward_alert_series.csv` on "
           f"{cc['window'][0]}..{cc['window'][1]}: **{cc['mismatches']} of "
           f"{cc['n_sessions']} sessions differ** (missing in ours {cc['missing_in_ours']}; "
           f"shipped loud share {cc['shipped_loud_share']:.4f}, ours "
           f"{cc['ours_loud_share']:.4f})", "",
           "Alerts are built causally on the full history from 2019-06-03 by the Macro engine "
           "(`engine.risk_radar_eval.inputs.incumbent_signals()`, which carries the "
           "prereg-addendum-3 point-in-time FRED replay), then shifted one session on the full "
           "series before windowing, exactly as r1g. Scoring uses the desk's vendored kit "
           "(`catalogue/adapter.py` + `pivot/radar_eval`).", "",
           "## 2. Primary tables (r1g results.csv columns)", ""]

    for fam in ("R-off", "R-on"):
        out.append(f"### {fam} ({DIRECTION[fam]})")
        out.append("")
        # primary rows = the sets and their unshifted controls; components are §3 only
        mine = tab[(tab["family"] == fam)
                   & (tab["role"].str.startswith(("set", "control")))].copy()
        mine["_o"] = mine["role"].map({"set": 0}).fillna(
            mine["role"].str.startswith("control").map({True: 1, False: 2}))
        mine = mine.sort_values(["_o", "set"]).drop(columns="_o")
        r = ref[ref["family"] == fam].copy()
        r["role"] = "reference (R1g)"
        block = pd.concat([mine[COLS], r[COLS]], ignore_index=True)
        out.append(md_table(block))
        out.append("")

    out += ["## 3. Components — descriptive only", "",
            "These are not sets and cannot pass. Shifted, 500 draws.", "",
            "### k-curve (confluence k of 12)", ""]
    krows = []
    for fam in ("R-off", "R-on"):
        for k in range(1, 13):
            d = results.get(f"{fam}__component_k{k}__{DIRECTION[fam]}")
            if not d or "error" in d:
                continue
            bp = d["by_post"][f"post{d['post']}"]
            krows.append({"family": fam, "k": k,
                          "alert_on_share": round(bp["alert_budget"], 3),
                          "cluster_catch": bp["cluster_share"],
                          "turn_catch": bp["turn_share"],
                          "false_per_asset_year": bp["false_per_asset_year"]})
    out.append(md_table(pd.DataFrame(krows)))
    out += ["", "### Single legs (each of the 12 alone)", ""]
    lrows = []
    for fam in ("R-off", "R-on"):
        for leg in LEGS:
            d = results.get(f"{fam}__leg_{leg}__{DIRECTION[fam]}")
            if not d or "error" in d:
                continue
            bp = d["by_post"][f"post{d['post']}"]
            lrows.append({"family": fam, "leg": leg,
                          "alert_on_share": round(bp["alert_budget"], 3),
                          "cluster_catch": bp["cluster_share"],
                          "turn_catch": bp["turn_share"],
                          "false_per_asset_year": bp["false_per_asset_year"]})
    out.append(md_table(pd.DataFrame(lrows)))

    out += ["", "## 4. Sets read and alert ON share", "",
            "Five sets read (R-off incumbent, R-off confluence_k4, R-on incumbent, "
            "R-on confluence_k4, R-on exit_v1), each with an unshifted control that cannot pass.",
            ""]
    srows = []
    for fam in ("R-off", "R-on"):
        for nm in (["incumbent", "confluence_k4"] if fam == "R-off"
                   else ["incumbent", "confluence_k4", "exit_v1"]):
            d = results.get(f"{fam}__{nm}__{DIRECTION[fam]}")
            if not d or "error" in d:
                continue
            bp = d["by_post"][f"post{d['post']}"]
            srows.append({"family": fam, "set": nm,
                          "alert_on_share": round(bp["alert_budget"], 3),
                          "cluster_catch": bp["cluster_share"],
                          "false_per_asset_year": bp["false_per_asset_year"],
                          "assets_pass": bp["pass_line"]["assets_pass"],
                          "clusters_pass_all_assets":
                              bp["pass_line"]["clusters_pass_all_assets"]})
    out.append(md_table(pd.DataFrame(srows)))
    out += ["", NO_VERDICT, "",
            "Per-asset pass and pass-all columns above are description only.", "",
            "## 5. Deviations and notes", "",
            "- The k=3 follow-up row (`rr-roff-confluence-k3-followup`) was **not** scored on "
            "any block, per the brief; no alert-vs-turn relation was computed for it.",
            "- The desk kit's `pivots.py` is a strict prefix of the worktree copy (identical "
            "scoring bytes; the worktree appends an unused `beyond_reference`), so scoring is "
            "byte-equivalent. The desk kit lacks `availability.py`/`walkforward.py` and its "
            "`inputs.py` has no point-in-time replay, so alerts come from the Macro engine.",
            f"- Runtime: {wall:.0f}s wall for {len(results)} jobs.", ""]

    (HERE / "SUMMARY.md").write_text("\n".join(out))
    print("wrote SUMMARY.md", flush=True)


if __name__ == "__main__":
    main()
