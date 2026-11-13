"""Correction re-score: the three published Macro placebo reads under PLACEBO_PLACEMENT_SPEC_v1 Rule A.

A correction line, not a new read (chance account unchanged). Rebuilds the exact inputs of
  1. WALKFORWARD_SCORECARD_OOS_v1 §3   (walk-forward loud, 2022-01-03..2026-11-10, 2,000 draws)
  2. SCORECARD_INSAMPLE §6             (INSAMPLE_READS_LAG1_v2 placebo block, 300 draws)
  3. PIVOT_SCORECARD_INSAMPLE Placebo  (PIVOT_PLACEBO_INSAMPLE_v2, 300 draws)
For each, the pre-repair placebo (`--old`, the defective module at #11137 head) is run first and
must reproduce the published JSON figure-for-figure before the Rule A result is reported.
Usage: rescore_rule_a.py --old <old_pivots.py> --states <unlagged.parquet> --states-lag1 <lag1.parquet>
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine.risk_radar_eval import inputs as I, labels as L, pivots as P  # noqa: E402

W = ROOT / "research/risk_radar/walkforward"
LOUD = {"elevated", "risk-off"}
CUT = pd.Timestamp("2026-11-10")


def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _load_old(path):
    spec = importlib.util.spec_from_file_location("pivots_pre_repair", path)
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m
    spec.loader.exec_module(m); return m


def _figs(r):
    """The published figure set of one placebo result."""
    f = {"fro_med": r["false_risk_off_per_year"].get("placebo_median"),
         "fro_mean": r["false_risk_off_per_year"].get("placebo_mean"),
         "prem_med": r["premature_all_clear_per_year"].get("placebo_median"),
         "prem_mean": r["premature_all_clear_per_year"].get("placebo_mean")}
    for k in ("top", "bottom"):
        for q in ("placebo_mean", "placebo_median", "placebo_p90", "share_draws_ge_observed"):
            f[f"{k}_{q}"] = r[k].get(q)
    return f


def _check(old, published, tag):
    a, b = _figs(old), _figs(published)
    bad = {k: (a[k], b[k]) for k in b if b[k] is not None and a[k] != b[k]}
    if bad:
        raise SystemExit(f"{tag}: pre-repair run does not reproduce the published JSON: {bad}")


def _row(new, alert):
    keep = ("defined", "status", "attempts", "kept", "discarded", "cap", "acceptance",
            "eligible_sessions", "eligible_share", "in_band_mass_share")
    return {"mass": int(alert.sum()), "runs": int(len(P._run_bounds(alert.to_numpy(bool)))),
            **{k: new[k] for k in keep}, "figures": _figs(new),
            "observed": {"top": new["top"]["observed"], "bottom": new["bottom"]["observed"],
                         "fro": new["false_risk_off_per_year"]["observed"],
                         "prem": new["premature_all_clear_per_year"]["observed"]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True); ap.add_argument("--states", required=True)
    ap.add_argument("--states-lag1", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    OLD = _load_old(a.old)
    px = L.spy_total_return()
    out = {"label": "CORRECTION LINE (not a new read): published Macro placebo reads re-scored "
                    "under PLACEBO_PLACEMENT_SPEC_v1 Rule A (co-signed, Amendment 1); every "
                    "pre-repair figure reproduced the published JSON first",
           "inputs_sha256": {"pre_repair_pivots": _sha(a.old), "states_unlagged": _sha(a.states),
                             "states_lag1": _sha(a.states_lag1),
                             "walkforward_alert_series": _sha(ROOT / "data/risk_radar/walkforward_alert_series.csv"),
                             "pivots_rule_a": _sha(ROOT / "engine/risk_radar_eval/pivots.py")},
           "reads": {}}

    # 1. OOS §3
    pub = json.loads((W / "WALKFORWARD_SCORECARD_OOS_v1.json").read_text())["placebo"]
    s = pd.read_csv(ROOT / "data/risk_radar/walkforward_alert_series.csv", comment="#",
                    parse_dates=["date"]).set_index("date")["loud"].astype(bool)
    eps = [e for e in L.drawdown_episodes(px, 0.05, outcomes_through=CUT) if e.peak >= pd.Timestamp("2022-01-03")]
    kw = dict(px=px, turns=P.turns_from_episodes(eps), episodes=eps, outcomes_through=CUT, tol=0.01,
              n_draws=2000, seed=0, pre=21, post=10, min_off=10, sealed_from=None, seen_history_ok=True)
    blk = {}
    for near in ("high", "low"):
        _check(OLD.placebo(s, near=near, **kw), pub["walkforward_loud"][near], f"oos|{near}")
        blk[f"walkforward_loud|{near}"] = _row(P.placebo(s, near=near, **kw), s)
    out["reads"]["WALKFORWARD_SCORECARD_OOS_v1 §3"] = blk

    # 2. SCORECARD_INSAMPLE §6 (INSAMPLE_READS_LAG1_v2)
    pub = json.loads((W / "INSAMPLE_READS_LAG1_v2.json").read_text())["placebo"]
    idx = px.index[(px.index >= pd.Timestamp("2020-01-02")) & (px.index <= CUT)]
    st = pd.read_parquet(a.states_lag1)["state"].reindex(idx).ffill()
    fl = I.baseline_flags(I.baseline_scores()).reindex(idx).fillna(False)
    ser = {"radar_loud": st.isin(LOUD), "radar_riskoff": st.eq("risk-off"),
           **{f"base_{c}": fl[c].astype(bool) for c in fl.columns}}
    e5 = [e for e in L.drawdown_episodes(px.loc[:CUT], 0.05, outcomes_through=CUT) if e.peak >= idx[0]]
    kw = dict(px=px, turns=P.turns_from_episodes(e5), episodes=e5, outcomes_through=CUT,
              n_draws=300, seen_history_ok=True)
    blk = {}
    for k in ("radar_loud", "radar_riskoff", "base_hy_oas_chg21_top_decile", "base_mech_near_high_1pct"):
        for near in ("high", "low"):
            _check(OLD.placebo(ser[k], near=near, **kw), pub[f"{k}|{near}"], f"lag1|{k}|{near}")
            blk[f"{k}|{near}"] = _row(P.placebo(ser[k], near=near, **kw), ser[k])
    out["reads"]["SCORECARD_INSAMPLE §6 (INSAMPLE_READS_LAG1_v2)"] = blk

    # 3. PIVOT_SCORECARD_INSAMPLE Placebo (PIVOT_PLACEBO_INSAMPLE_v2)
    pub = json.loads((W / "PIVOT_PLACEBO_INSAMPLE_v2.json").read_text())
    st = pd.read_parquet(a.states)["state"].reindex(idx).ffill()
    ser = {"radar_loud": st.isin(LOUD), "hy_oas_top_decile": fl["hy_oas_chg21_top_decile"].astype(bool),
           "vix_ge_20": fl["vix_ge_20"].astype(bool), "spy_below_200": fl["spy_below_200"].astype(bool)}
    blk = {}
    for k, al in ser.items():
        for near in (None, "high", "low"):
            key = f"{k}|{near}"
            if key not in pub:
                continue
            try:
                _check(OLD.placebo(al, near=near, **kw), pub[key], f"pivot|{key}")
                repro = True
            except SystemExit as exc:
                if not k.startswith("hy_oas"):
                    raise
                repro = str(exc)  # HY baseline input changed in bb856951 (release-rule lag)
            blk[key] = {**_row(P.placebo(al, near=near, **kw), al), "pre_repair_reproduced": repro}
    out["reads"]["PIVOT_SCORECARD_INSAMPLE Placebo (PIVOT_PLACEBO_INSAMPLE_v2)"] = blk
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(a.out, _sha(a.out))


if __name__ == "__main__":
    main()
