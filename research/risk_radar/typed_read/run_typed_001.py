"""Typed read rr-typed-read-flags-001 (RD-signed joint row; description only; chance account 14).

For each of the 12 legs (alone at its engine thr_pct as coded) plus the Radar loud state
("incumbent (object scored, not a feature)"), on PRE 2006-01-03..2019-12-31 and D 2020-01-02..
2023-12-29: bm_ref rev1 scores the alert (R-off major tops, 21 desk series, swing episodes, post 5,
t+1 shift on the full series before windowing). This runner then only PARTITIONS the scorer's
per-turn rows and false-call starts by the RD's flag state:
  - a cluster takes the state of its earliest turn's session (ruling 4); multi-state clusters counted;
  - a false call takes the state of its alert-start session.
Partition totals are asserted equal to bm_ref score_alerts' totals. No placebo, no reference, no
per-cell gate. Under 8 clusters: counts only. Nothing on or after 2024-01-02 is loaded.

Usage: python3 run_typed_001.py --desk <desk-root>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import typed_read as TR  # noqa: E402

ROW_ID = "rr-typed-read-flags-001"
ROW_SHA = "72eeafb6a07eb736c880dc1d6fc924ab480a8ea9d7a5e45246defac1ff376680"
PIN_TYPES = "d6e77b7cce550f9b295009decdb9f2c5f22637af4b64565d8c323812113bddc5"
PIN_BM = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"
SEAL = pd.Timestamp("2024-01-02")
ERAS = {"PRE": (pd.Timestamp("2006-01-03"), pd.Timestamp("2019-12-31")),
        "D": (pd.Timestamp("2020-01-02"), pd.Timestamp("2023-12-29"))}
PRE_W, POST, MIN_OFF, SEED, TOL = 21, 5, 10, 20261112, 0.01
LEGS = {"credit_oas_roc": 0.90, "credit_hyg_tlt": 0.90, "rates_move": 0.90, "rates_realrate": 0.90,
        "bubble_ext": 0.90, "bubble_leadership": 0.90, "growth_defensives": 0.90,
        "growth_cyc_def": 0.90, "vol_term": 0.90, "global_breadth": 0.70, "jpy_carry": 0.85,
        "corr_floor_break": 0.85}
INCUMBENT = "incumbent (object scored, not a feature)"
COND = {"PRE": ["flag_rate", "flag_easing"],
        "D": ["flag_rate", "flag_easing", "flag_real_rate", "flag_credit", "flag_credit_level",
              "flag_dollar"]}
PRE_DESC_GROUP = ["flag_real_rate", "flag_credit", "flag_credit_level", "flag_dollar"]
PRE_DESC_LABEL = "description; fails the coverage line in PRE (Addendum A §2)"
RD_NAME = {"flag_credit": "flag_credit_pressure"}
VERBATIM = ["An idea first seen in a D cell is forward-only.",
            "The plain type table found flag-present days do not concentrate turns strongly (rate ratio "
            "1.17–1.38 PRE, 0.88–1.11 D); this read asks a different question (catch and false calls by "
            "flag) and is description."]
OUT = HERE / "out_001"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ phase 1: Macro alerts
def build_alerts_full() -> dict[str, pd.Series]:
    from engine import risk_radar as rr
    from engine.risk_radar_eval import availability as AV
    from engine.risk_radar_eval import inputs as I
    from engine.risk_radar_eval import walkforward as W
    sigs = AV.pit_signals(rr.leading_signals(), start="2006-01-03")
    sigs = sigs[sigs.index < SEAL]
    out = {}
    for leg, thr in LEGS.items():
        out[leg] = (sigs[leg] >= thr).fillna(False).astype(bool).shift(1, fill_value=False)
    calib = rr._calib()
    subs = rr.subscore_series(sigs, calib)
    gate = I.gate_series(I.gate_components(subs.index), 0.40)
    states = W.states_for(subs, sigs, calib, gate, 0)
    loud = states.isin({"elevated", "risk-off"}).astype(bool)
    out[INCUMBENT] = loud.shift(1, fill_value=False).astype(bool)
    return out


# ------------------------------------------------------------------ phase 2: desk kit
def load_desk(desk: Path):
    sys.path[:] = [p for p in sys.path if p not in ("", ".", str(_ROOT), os.getcwd())]
    for m in [m for m in sys.modules if m == "engine" or m.startswith("engine.")]:
        del sys.modules[m]
    for p in (desk, desk / "catalogue", desk / "pivot"):
        sys.path.insert(0, str(p))
    from catalogue import adapter as A
    from catalogue import bm_ref as BM
    pv, _ = A.load_radar_kit()
    if desk.resolve() not in Path(pv.__file__).resolve().parents:
        raise SystemExit("scorer resolved outside the desk")
    return A, BM, pv


def window(full: pd.Series, level: pd.Series, start, end) -> pd.Series:
    idx = level.index
    lo = max(0, int(idx.searchsorted(start)) - PRE_W)
    ai = idx[lo:]
    ai = ai[ai <= end]
    a = full.reindex(ai, method="ffill")
    if a.isna().any():
        raise SystemExit("alert NaN after reindex")
    return a.astype(bool)


def false_starts(pv, alert: pd.Series, rows: list, episodes: list) -> list:
    """Reproduce score_pivots' false-call set (starts not used by a flagged turn, outside every
    onset..recovery span) so each false call can carry its start date. Count asserted equal."""
    starts, _e, _f = pv._calls(alert, MIN_OFF)
    idx = alert.index
    used = set()
    pos = {d: i for i, d in enumerate(idx)}
    for r in rows:
        if r["kind"] == "top" and r.get("status") == "scored" and r.get("flagged"):
            p = pos[pd.Timestamp(r["date"])]
            used.update(c for c in starts if p - PRE_W <= c <= p + POST)

    def in_span(i):
        d = idx[i]
        for e in episodes:
            hi = e.recovery if e.recovery is not None else idx.max()
            if e.onset <= d <= hi:
                return True
        return False
    return [idx[s] for s in starts if s not in used and not in_span(s)]


def state_at(col: pd.Series, dates) -> list:
    pos = col.index.searchsorted(pd.DatetimeIndex(dates), side="right") - 1
    return [col.iloc[p] if p >= 0 else "unavailable" for p in pos]


def partition(per_asset: dict, alerts: dict, types: pd.DataFrame, dim: str, era_rng) -> dict:
    col = types[dim]
    lo, hi = era_rng
    states = sorted(set(col[(col.index >= lo) & (col.index <= hi)]))
    sc = []                               # scored top turns with cluster key
    for a, r in per_asset.items():
        for i, row in enumerate(r["turns"]):
            if row["kind"] == "top" and row["status"] == "scored":
                sc.append({**row, "_key": row.get("cluster_id") or f"__{a}_{row['date']}_{i}"})
    clusters: dict = {}
    for row in sc:
        clusters.setdefault(row["_key"], []).append(row)
    cl_state, multi = {}, 0
    for k, rows in clusters.items():
        ds = sorted(pd.Timestamp(r["date"]) for r in rows)
        sts = set(state_at(col, ds))
        multi += len(sts) > 1
        cl_state[k] = state_at(col, [ds[0]])[0]
    cells = {}
    era_sess = col[(col.index >= lo) & (col.index <= hi)]
    for v in states:
        ks = [k for k in clusters if cl_state[k] == v]
        caught = sum(any(r["flagged"] for r in clusters[k]) for k in ks)
        fc, on, n = 0, 0, 0
        for a, alert in alerts.items():
            st = pd.Series(state_at(col, alert.index), index=alert.index)
            m = st.eq(v)
            n += int(m.sum())
            on += int((alert & m).sum())
            fc += sum(1 for d in per_asset[a]["_false_dates"] if st.loc[d] == v)
        small = len(ks) < TR.MIN_CLUSTERS
        cells[v] = {"clusters": len(ks), "caught": caught,
                    "catch_share": None if small or not ks else round(caught / len(ks), 3),
                    "false_calls": fc,
                    "false_per_asset_year": None if small or not n else round(fc / (n / 252), 2),
                    "alert_share_in_state": None if small or not n else round(on / n, 3),
                    "share_of_era_sessions": round(float(era_sess.eq(v).mean()), 4),
                    "counts_only": small}
    return {"cells": cells, "multi_state_clusters": multi, "n_clusters": len(clusters)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", required=True)
    desk = Path(ap.parse_args().desk).resolve()
    ledger = desk / "trials.jsonl"
    TR.check_guard(ledger_path=ledger, row_id=ROW_ID)
    row = [json.loads(l) for l in ledger.open() if f'"id": "{ROW_ID}"' in l][0]
    if row["spec_sha256"] != ROW_SHA:
        raise SystemExit("joint row spec sha differs; refusing")
    pins = {"types": sha(desk / "regime/types/out/type_history_v1.parquet"),
            "bm_ref": sha(desk / "catalogue/bm_ref.py"), "adapter": sha(desk / "catalogue/adapter.py")}
    if (pins["types"], pins["bm_ref"], pins["adapter"]) != (PIN_TYPES, PIN_BM, PIN_AD):
        raise SystemExit(f"pin mismatch {pins}")
    types = TR.load_types(desk / "regime/types/out/type_history_v1.parquet", TR.RD_V1_COLUMNS,
                          expect_sha256=PIN_TYPES)
    src = pd.read_parquet(desk / "regime/types/out/type_history_v1.parquet", columns=["src_b"])

    t0 = time.time()
    full = build_alerts_full()
    print(f"alerts built {time.time()-t0:.0f}s", flush=True)
    A, BM, pv = load_desk(desk)

    result = {"row_id": ROW_ID, "row_spec_sha256": ROW_SHA, "pins": pins,
              "harness_sha256": sha(HERE / "typed_read.py"), "runner_sha256": sha(__file__),
              "verbatim": VERBATIM, "eras": {}}
    for era, (lo, hi) in ERAS.items():
        ctx = BM.build_context("R-off", "top", start_d=lo, end_d=hi)
        series, turns, levels, episodes = ctx["series"], ctx["turns"], ctx["levels"], ctx["episodes"]
        assert max(pd.Timestamp(t.date) for t in turns) <= hi
        by_asset: dict = {}
        for t in turns:
            by_asset.setdefault(t.asset, []).append(t)
        tsub = types[(types.index <= hi)]
        dims = COND[era] + (PRE_DESC_GROUP if era == "PRE" else []) + ["core_label"]
        e_out = {"series": len(series), "turns": len(turns), "objects": {}}
        u = tsub[(tsub.index >= lo)]["core_label"]
        e_out["core_label_u_share"] = round(float(u.eq("U").mean()), 4)
        e_out["source_era_src_b"] = src[(src.index >= lo) & (src.index <= hi)]["src_b"].value_counts().to_dict()
        for name, f in full.items():
            alerts = {n: window(f, levels[n], lo, hi) for n in series}
            tot = BM.score_alerts(turns, alerts, episodes, {n: levels[n].reindex(alerts[n].index)
                                                           for n in series},
                                  direction="top", post=POST, include_passes=False,
                                  outcomes_through=hi)
            per = {}
            fsum = 0
            for a, ts in by_asset.items():
                if a not in alerts:
                    continue
                r = pv.score_pivots(alerts[a], turns=ts, episodes=episodes.get(a, []),
                                    outcomes_through=hi, pre=PRE_W, post=POST, min_off=MIN_OFF)
                fd = false_starts(pv, alerts[a], r["turns"], episodes.get(a, []))
                if len(fd) != r["false_risk_off"]:
                    raise SystemExit(f"false-call reproduction mismatch {name} {a}")
                r["_false_dates"] = fd
                per[a] = r
                fsum += len(fd)
            o = {"total": {k: tot[k] for k in ("clusters_scored", "clusters_flagged", "cluster_share",
                                               "false_per_asset_year", "alert_budget")},
                 "false_calls_total": fsum, "by_flag": {}}
            for dim in dims:
                p = partition(per, alerts, tsub, dim, (lo, hi))
                assert sum(c["clusters"] for c in p["cells"].values()) == tot["clusters_scored"], (name, dim)
                assert sum(c["caught"] for c in p["cells"].values()) == tot["clusters_flagged"], (name, dim)
                assert sum(c["false_calls"] for c in p["cells"].values()) == fsum, (name, dim)
                p["group"] = ("description only (core label fails the coverage line in every era)"
                              if dim == "core_label" else
                              PRE_DESC_LABEL if (era == "PRE" and dim in PRE_DESC_GROUP) else "conditioning")
                o["by_flag"][RD_NAME.get(dim, dim)] = p
            e_out["objects"][name] = o
            print(f"{era} {name}: {o['total']}", flush=True)
        e_out["sensitivity"] = ("edge-turns line: PENDING (SA-1 2c not landed)" if era == "D" else
                                "SA-1 2c PRE-differing turns removed: PENDING (SA-1 2c not landed)")
        result["eras"][era] = e_out
    OUT.mkdir(exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=1, default=str))
    print("wrote", OUT / "result.json", sha(OUT / "result.json"), f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
