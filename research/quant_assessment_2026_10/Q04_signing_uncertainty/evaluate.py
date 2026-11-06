"""Q04 evaluator: identified-set width of the options-flow trade sign (PREREG E2/H1).

Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log.
Appends every invocation (command, exit code, input and output sha256s) to RUNS.log.

Modes:
  --mode baseline   prove absence/presence of the incumbent raw cache and record the
                    incumbent signing_gate.json baseline figures (no recomputation possible
                    without the raw cache).
  --mode evaluate   the single preregistered empirical comparison (default).

Research only. Reads licensed retained local data read-only; writes only inside this directory.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q04_ROOT = HERE.parents[2]
DATA = Path(os.environ.get("Q04_DATA_ROOT", "/Users/chriswong/Documents/Cluade/macro-main/data"))
PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"

LEDGER = DATA / "flow_signals" / "ledger.parquet"
GATE = DATA / "options_flow" / "signing_gate.json"
TAPE_SESSIONS = DATA / "options_flow" / "tape_signing_sessions.jsonl"
RAW_CACHE = DATA / "options_flow" / "_dbento_sample.parquet"

COHORT_SCHEMA = "options.trade_nbbo_microstructure/v1"
K_GRID = (0.0, 5.0, 20.0, 80.0, 320.0)
N_BOOT = 2000
SEED = 4041
TRAIN_FRAC = 0.6
MIN_TRAIN_SESSIONS = 4
MIN_TEST_SESSIONS = 5
SKILL_BAR = 0.05
TIME_SUPPORT_MAX_OUTSIDE = 0.05


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash() -> str | None:
    if not FREEZE.exists():
        return None
    m = None
    for line in FREEZE.read_text().splitlines():
        mm = re.search(r"sha256=([0-9a-f]{64})", line)
        if mm and "PREREG.md" in line:
            m = mm.group(1)
    return m


def code_identity() -> dict:
    """sha256 of the code that produces results (finisher fix: code identity per RUN entry)."""
    out = {}
    for rel in ("engine/flow_sign_uncertainty.py",
                "research/quant_assessment_2026_10/Q04_signing_uncertainty/evaluate.py",
                "research/quant_assessment_2026_10/Q04_signing_uncertainty/PREREG_AMENDMENT.md"):
        p = Q04_ROOT / rel
        if p.exists():
            out[rel] = sha256_file(p)
    return out


def append_run(command: str, exit_code: int, inputs: dict, outputs: dict, note: str,
               flags: dict | None = None) -> None:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # log metadata only
    lines = [f"RUN {stamp} exit={exit_code} cmd={command}"]
    for k, v in code_identity().items():
        lines.append(f"  code {k} sha256={v}")
    for k, v in inputs.items():
        lines.append(f"  input {k} sha256={v}")
    for k, v in (flags or {}).items():
        lines.append(f"  flag {k}={v}")
    for k, v in outputs.items():
        lines.append(f"  output {k} sha256={v}")
    lines.append(f"  note {note}")
    with open(RUNS, "a") as f:
        f.write("\n".join(lines) + "\n")


def _r(x, nd=10):
    if x is None:
        return None
    if isinstance(x, float):
        if not math.isfinite(x):
            return None
        return round(x, nd)
    return x


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    try:
        import numpy as np
        if isinstance(obj, np.generic):
            obj = obj.item()
    except Exception:  # pragma: no cover
        pass
    return _r(obj)


def write_json(p: Path, obj) -> str:
    p.write_text(json.dumps(_clean(obj), indent=2, sort_keys=True) + "\n")
    return sha256_file(p)


# ── baseline mode ─────────────────────────────────────────────────────────────

def run_baseline() -> tuple[dict, dict, str]:
    inputs = {}
    for p in (GATE, TAPE_SESSIONS):
        inputs[str(p.relative_to(DATA.parent))] = sha256_file(p)
    present = RAW_CACHE.exists()
    gate = json.loads(GATE.read_text())
    sessions = [json.loads(l) for l in TAPE_SESSIONS.read_text().splitlines() if l.strip()]
    out = {
        "incumbent_raw_cache": str(RAW_CACHE.relative_to(DATA.parent)),
        "incumbent_raw_cache_present": present,
        "incumbent_rerun_possible": present,
        "incumbent_gate_record": {
            "per_trade_agreement_tick_vs_quote": gate.get("per_trade_agreement"),
            "per_trade_size_weighted": gate.get("per_trade_size_weighted"),
            "net_sign_recovery": gate.get("net_sign_recovery"),
            "n_trades": gate.get("n_trades"),
            "direction_reliable": gate.get("direction_reliable"),
            "scored": gate.get("scored"),
            "delta_adjusted": gate.get("delta_adjusted"),
            "metric_kind": "self_consistency (tick rule vs quote rule; no independent aggressor label)",
        },
        "tape_sessions": [
            {"per_trade_agreement": s.get("per_trade_agreement"),
             "net_sign_recovery": s.get("net_sign_recovery"),
             "n_trades": s.get("n_trades"),
             "agreement_method": s.get("agreement_method")}
            for s in sessions
        ],
    }
    RESULTS.mkdir(exist_ok=True)
    outputs = {"results/baseline.json": write_json(RESULTS / "baseline.json", out)}
    note = ("incumbent raw tcbbo cache ABSENT: calibrate_flow_signing cannot be rerun; recorded gate "
            "figures are tick-vs-quote self-consistency" if not present else
            "incumbent raw cache present (unexpected; E1 would need re-assessment)")
    return inputs, outputs, note


# ── evaluate mode ─────────────────────────────────────────────────────────────

def run_evaluate() -> tuple[dict, dict, str]:
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(Q04_ROOT))
    import engine.flow_sign_uncertainty as fsu  # noqa: E402

    inputs = {str(LEDGER.relative_to(DATA.parent)): sha256_file(LEDGER)}
    cols = ["event_id", "session_date", "ts", "root", "right", "exp", "strike", "side", "premium",
            "nbbo_premium_coverage", "at_ask_share", "at_bid_share", "spread_median_pct",
            "quote_age_median_ms", "quote_age_max_ms", "ingested_at", "microstructure_schema"]
    df = pd.read_parquet(LEDGER, columns=cols)
    n_total = int(len(df))
    coh = df[df["microstructure_schema"] == COHORT_SCHEMA].copy()
    coh = coh.sort_values(["session_date", "ts", "event_id"], kind="mergesort").reset_index(drop=True)
    attrition = {
        "ledger_rows": n_total,
        "ledger_sessions": int(df["session_date"].nunique()),
        "rows_without_microstructure_v1": n_total - int(len(coh)),
        "cohort_rows": int(len(coh)),
        "cohort_sessions": int(coh["session_date"].nunique()),
        "cohort_null_coverage": int(coh["nbbo_premium_coverage"].isna().sum()),
        "cohort_null_at_ask_share": int(coh["at_ask_share"].isna().sum()),
        "cohort_null_at_bid_share": int(coh["at_bid_share"].isna().sum()),
        "cohort_null_spread": int(coh["spread_median_pct"].isna().sum()),
        "cohort_nonpositive_or_null_premium": int((~(pd.to_numeric(coh["premium"], errors="coerce") > 0)).sum()),
    }

    b = fsu.event_bounds_arrays(coh["nbbo_premium_coverage"], coh["at_ask_share"], coh["at_bid_share"])
    coh["U"] = b["unidentified"]
    coh["lower"] = b["lower"]
    coh["upper"] = b["upper"]
    coh["premium_f"] = pd.to_numeric(coh["premium"], errors="coerce")
    ident = [fsu.label_is_identified(s, lo, hi) for s, lo, hi in zip(coh["side"], coh["lower"], coh["upper"])]
    coh["label_identified"] = ident

    # time support check (PREREG §3)
    ts = coh["ts"].astype(str)
    minutes = pd.to_numeric(ts.str.slice(11, 13), errors="coerce") * 60 + pd.to_numeric(ts.str.slice(14, 16), errors="coerce")
    outside = ~((minutes >= 570) & (minutes <= 975))
    frac_outside = float(outside.mean())
    time_identified = frac_outside <= TIME_SUPPORT_MAX_OUTSIDE
    coh["tseg"] = fsu.time_segment(minutes.to_numpy()) if time_identified else "all"
    time_support = {"frac_outside_0930_1615": frac_outside, "threshold": TIME_SUPPORT_MAX_OUTSIDE,
                    "time_segments_identified": bool(time_identified),
                    "ts_offset_note": "recorded ts carries +00:00 while values sit in exchange hours; wall-clock HH:MM used"}

    # split (PREREG §5)
    tr_s, te_s = fsu.chronological_split(coh["session_date"], TRAIN_FRAC)
    is_tr = coh["session_date"].isin(tr_s).to_numpy()
    is_te = coh["session_date"].isin(te_s).to_numpy()
    key = list(zip(coh["root"].astype(str), coh["right"].astype(str), coh["exp"].astype(str),
                   coh["strike"].astype(str)))
    keys_tr = [k for k, t in zip(key, is_tr) if t]
    keys_te = [k for k, t in zip(key, is_te) if t]
    disj = np.zeros(len(coh), dtype=bool)
    disj[is_te] = fsu.contract_disjoint_mask(keys_tr, keys_te)

    edges = fsu.liquidity_edges(coh.loc[is_tr, "spread_median_pct"].to_numpy(dtype=float))
    coh["liq"] = fsu.assign_liquidity(coh["spread_median_pct"].to_numpy(dtype=float), edges)
    coh["cell"] = coh["liq"].astype(str) + "|" + coh["tseg"].astype(str)

    y = coh["U"].to_numpy(dtype=float)
    sess = coh["session_date"].astype(str).to_numpy(dtype=object)
    cells_full = coh["cell"].to_numpy(dtype=object)
    cells_liq = coh["liq"].to_numpy(dtype=object)

    k_m, scores_m = fsu.choose_k_loso(y[is_tr], cells_full[is_tr], sess[is_tr], K_GRID)
    k_b2, scores_b2 = fsu.choose_k_loso(y[is_tr], cells_liq[is_tr], sess[is_tr], K_GRID)
    model_m = fsu.fit_cell_means(y[is_tr], cells_full[is_tr], k_m)
    model_b2 = fsu.fit_cell_means(y[is_tr], cells_liq[is_tr], k_b2)
    base = float(y[is_tr].mean())
    pred_m = fsu.predict_cells(model_m, cells_full)
    pred_b2 = fsu.predict_cells(model_b2, cells_liq)

    def compare(mask, label):
        se_m = (y[mask] - pred_m[mask]) ** 2
        se_b0 = (y[mask] - base) ** 2
        se_b1 = (y[mask] - 0.0) ** 2
        se_b2 = (y[mask] - pred_b2[mask]) ** 2
        s = sess[mask]
        out = {"cohort": label, "n_events": int(mask.sum()), "n_sessions": fsu.effective_n(s)}
        if mask.sum() == 0:
            return out
        out["mse_M"] = float(se_m.mean())
        out["mse_B0"] = float(se_b0.mean())
        out["mse_B1_zero_uncertainty"] = float(se_b1.mean())
        out["mse_B2_liquidity_only"] = float(se_b2.mean())
        out["skill_M_vs_B0"] = fsu.session_block_bootstrap_skill(s, se_m, se_b0, n_boot=N_BOOT, seed=SEED)
        out["skill_B2_vs_B0"] = fsu.session_block_bootstrap_skill(s, se_b2, se_b0, n_boot=N_BOOT, seed=SEED)
        out["skill_M_vs_B1"] = fsu.session_block_bootstrap_skill(s, se_m, se_b1, n_boot=N_BOOT, seed=SEED)
        return out

    dec = compare(disj, "decision: test events, contract-disjoint from training")
    sens = compare(is_te, "sensitivity: all test events")
    test_sessions_with_decision = int(len(set(sess[disj].tolist())))
    powered = len(tr_s) >= MIN_TRAIN_SESSIONS and test_sessions_with_decision >= MIN_TEST_SESSIONS
    sk = dec.get("skill_M_vs_B0", {})
    bar_met = bool(sk) and sk.get("skill", -1) >= SKILL_BAR and sk.get("ci_lo", -1) > 0
    if not powered:
        sidecar = "SIDECAR_INSUFFICIENT_DATA"
    else:
        sidecar = "SIDECAR_KEEP" if bar_met else "SIDECAR_REJECT"

    h1 = {
        "train_sessions": tr_s, "test_sessions": te_s,
        "n_train_events": int(is_tr.sum()), "n_test_events": int(is_te.sum()),
        "contract_disjoint_test_events": int(disj.sum()),
        "contract_filter_attrition": int(is_te.sum() - disj.sum()),
        "test_sessions_with_decision_events": test_sessions_with_decision,
        "liquidity_edges_train": list(edges),
        "k_M": k_m, "loso_mse_M": {str(k): v for k, v in scores_m.items()},
        "k_B2": k_b2, "loso_mse_B2": {str(k): v for k, v in scores_b2.items()},
        "train_mean_U_B0": base,
        "decision": dec, "sensitivity": sens,
        "min_honest_n": {"train": MIN_TRAIN_SESSIONS, "test": MIN_TEST_SESSIONS},
        "powered": bool(powered), "bar": {"skill_min": SKILL_BAR, "ci_lo_gt": 0.0},
        "bar_met_numerically": bool(bar_met), "sidecar_verdict": sidecar,
    }

    # descriptive tables (PREREG §7), session-block bootstrap over all cohort sessions
    labeled = coh["side"].isin(["~buy", "~sell"]).to_numpy()
    nonrobust = np.array([0.0 if v is True else (1.0 if v is False else np.nan) for v in ident])
    rows = []
    groups = [("POOLED", np.ones(len(coh), dtype=bool))]
    for c in sorted(set(cells_full.tolist())):
        groups.append((c, cells_full == c))
    prem = coh["premium_f"].to_numpy(dtype=float)
    for name, m in groups:
        mb = fsu.session_block_bootstrap_mean(sess[m], y[m], n_boot=N_BOOT, seed=SEED)
        mw = fsu.session_block_bootstrap_mean(sess[m], y[m], prem[m], n_boot=N_BOOT, seed=SEED)
        ml = m & labeled
        nr = fsu.session_block_bootstrap_mean(sess[ml], nonrobust[ml], prem[ml], n_boot=N_BOOT, seed=SEED)
        nr_ev = fsu.session_block_bootstrap_mean(sess[ml], nonrobust[ml], n_boot=N_BOOT, seed=SEED)
        rows.append({
            "cell": name, "events": int(m.sum()), "sessions": fsu.effective_n(sess[m]),
            "gross_premium": float(np.nansum(prem[m])),
            "mean_U": mb["mean"], "mean_U_ci_lo": mb["ci_lo"], "mean_U_ci_hi": mb["ci_hi"],
            "premw_U": mw["mean"], "premw_U_ci_lo": mw["ci_lo"], "premw_U_ci_hi": mw["ci_hi"],
            "labeled_events": int(ml.sum()),
            "nonrobust_labeled_premium_share": nr["mean"],
            "nonrobust_prem_ci_lo": nr["ci_lo"], "nonrobust_prem_ci_hi": nr["ci_hi"],
            "nonrobust_labeled_event_share": nr_ev["mean"],
            "nonrobust_event_ci_lo": nr_ev["ci_lo"], "nonrobust_event_ci_hi": nr_ev["ci_hi"],
        })
    table = pd.DataFrame(rows)

    def q(series):
        v = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            return {"n": 0}
        qs = np.quantile(v, [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0])
        return {"n": int(v.size), "q": dict(zip(["min", "p10", "p25", "p50", "p75", "p90", "p99", "max"], qs.tolist()))}

    t_ts = pd.to_datetime(coh["ts"], utc=True, errors="coerce")
    t_in = pd.to_datetime(coh["ingested_at"], utc=True, errors="coerce")
    lag_s = (t_in - t_ts).dt.total_seconds()
    dists = {
        "quote_age_median_ms": q(coh["quote_age_median_ms"]),
        "quote_age_max_ms": q(coh["quote_age_max_ms"]),
        "ingest_lag_seconds_as_recorded": q(lag_s),
        "ingest_lag_note": "ingested_at minus ts as recorded; ts offset ambiguous (+00:00 tag on exchange-hours values); no lag constant applied",
        "label_counts": {str(k): int(v) for k, v in coh["side"].value_counts().items()},
        "labeled_identified_robust": int(sum(1 for v in ident if v is True)),
        "labeled_not_identified": int(sum(1 for v in ident if v is False)),
    }

    summary = {
        "brief": "Q04", "estimand": "E2 identified-set width of the trade sign",
        "E1": {"verdict": "INSUFFICIENT_DATA", "missing_input": fsu.MISSING_INPUT,
               "raw_cache_present": RAW_CACHE.exists()},
        "attrition": attrition, "time_support": time_support, "H1": h1,
        "distributions": dists,
        "overall_verdict": "INSUFFICIENT_DATA",
    }
    RESULTS.mkdir(exist_ok=True)
    outputs = {"results/e2_summary.json": write_json(RESULTS / "e2_summary.json", summary)}
    tp = RESULTS / "cell_table.csv"
    table.round(10).to_csv(tp, index=False, float_format="%.10g")
    outputs["results/cell_table.csv"] = sha256_file(tp)
    note = f"overall=INSUFFICIENT_DATA sidecar={sidecar} powered={powered} decision_skill={sk.get('skill')} ci=[{sk.get('ci_lo')},{sk.get('ci_hi')}]"
    return inputs, outputs, note


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("baseline", "evaluate"), default="evaluate")
    args = ap.parse_args(argv)
    command = "python3.12 " + str(Path(__file__)) + " --mode " + args.mode
    want = frozen_hash()
    have = sha256_file(PREREG) if PREREG.exists() else None
    if want is None or have != want:
        append_run(command, 2, {"PREREG.md": str(have)}, {},
                   f"REFUSED: PREREG.md sha256 {have} != FREEZE.log {want}")
        print(f"REFUSED: PREREG.md sha256 {have} != frozen {want}", file=sys.stderr)
        return 2
    try:
        if args.mode == "baseline":
            inputs, outputs, note = run_baseline()
        else:
            inputs, outputs, note = run_evaluate()
    except Exception as exc:  # record the failure, then re-raise exit code
        append_run(command, 1, {"PREREG.md": have}, {}, f"FAILED: {type(exc).__name__}: {exc}")
        raise
    inputs = {"PREREG.md": have, **inputs}
    flags = {"raw_cache_present": RAW_CACHE.exists()} if args.mode == "evaluate" else None
    append_run(command, 0, inputs, outputs, note, flags)
    print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
