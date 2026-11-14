"""Write the Risk Radar catalogue-read ledger rows (Principal rulings 3a/3b/3c) BEFORE any read.

Desk ledger: the desk's v4/trials.jsonl, passed as the required argument (append-only; DESK_RULES,
APPROVAL_v2 A3). Usage: python3 ledger_rows.py <path-to-trials.jsonl>
Five primary sets: R-off {incumbent, confluence}; R-on {incumbent, confluence, exit-v1}.
Refuses to run if any rr- row already exists.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

AUTHOR = "risk-radar-lead/claude-opus-5-5 (Macro fable/risk-radar-masterplan-20261112)"
SERIES = ['BAA_10Y', 'CYC/DEF', 'DIA', 'EEM/SPY', 'HYG/IEF', 'HY_OAS', 'IGV/EWDEF', 'IWM',
          'IWM/SPY', 'MDY', 'QQQ', 'QQQ/EWDEF', 'RSP', 'RSP/SPY', 'RSPT/EWDEF', 'SMH/EWDEF',
          'SPHB/SPLV', 'SPY', 'SPY/GLD', 'SPY/TLT', 'XLK/EWDEF']   # = r1-roff/r1-ron reference rows
LEGS = {  # leg -> 'on' threshold: the engine's own strict-bar thr_pct as coded (_LEG_CALIB), not fitted
    "credit_oas_roc": 0.90, "credit_hyg_tlt": 0.90, "rates_move": 0.90, "rates_realrate": 0.90,
    "bubble_ext": 0.90, "bubble_leadership": 0.90, "growth_defensives": 0.90,
    "growth_cyc_def": 0.90, "vol_term": 0.90, "global_breadth": 0.70, "jpy_carry": 0.85,
    "corr_floor_break": 0.85}
EXCLUDED = {"nh_contraction": "41% coverage on D (NaN before its breadth store)",
            "ai_breadth_divergence": "no history on D", "vol_putcall": "absent (slice 1b)",
            "vol_gex": "absent (slice 1b)"}
INPUTS = ("Macro engine.risk_radar_eval.inputs.incumbent_signals() = engine.risk_radar.leading_signals() "
          "with FRED legs replaced by their point-in-time replay (prereg v1 addendum 3); state by "
          "engine.risk_radar._resolve_state_row via walkforward.states_for, gate breadth 0.40, delta 0 "
          "(every walk-forward fold retained this default)")
COMMON = {"universes": ["U1", "U5", "U6", "U7"], "series": SERIES, "tier": "major", "window": "D",
          "block": "2020-01-02..2023-12-29", "pre": 21, "min_off": 10, "n_draws": 2000, "tol": 0.01,
          "seed": 20261112, "alert_shift_sessions": 1, "inputs": INPUTS,
          "same_alert_all_series": True, "outcomes_through": "2023-12-29",
          "pass_line": "APPROVAL_v2 / adapter.run_pass_line: per asset share >= near placebo p90 AND "
                       "false calls/yr <= placebo median; clusters pass when every scored asset passes",
          "label_honesty": "nomination only: the Radar and its legs were built knowing 2020+; the "
                           "Radar family is confirmed forward only (APPROVAL_v2 F14)"}

CONF = {"rule": "equal-vote count of legs on, leg on when its causal 504d percentile >= its thr_pct",
        "legs": LEGS, "excluded_legs": EXCLUDED, "n": len(LEGS), "primary_k": 4,
        "primary_k_rule": "smallest k whose share of D sessions with >=k legs on is <= 0.20 (the Radar's "
                          "walk-forward loud budget 0.193, rounded); outcome-free, computed from "
                          "firing counts only (k=3 0.270, k=4 0.141)",
        "secondary": "every k in 1..n and each leg alone are reported as component reads; they are "
                     "not sets and cannot pass",
        "expected_direction": "catch share and false calls both fall as k rises; precision "
                              "(catch per false call) rises with k",
        "must_beat": "its best single leg and the mechanical reference at the same or lower false rate "
                     "(APPROVAL_v2 C8)"}

EXIT = {"rule": "R-on risk-off state: ON from the first session the Radar is loud (elevated or "
                "risk-off); turns OFF (all-clear) on the first session where ALL hold: (i) the Radar "
                "has not been loud for 5 consecutive sessions; (ii) HY OAS as known at d (PIT) <= its "
                "value as known 10 sessions earlier; (iii) SPY close >= 1.03 x its lowest close since "
                "the state armed. Re-arms on the next loud session.",
        "reasoning": "the live loud state ends when its scores decay, which can happen while the "
                     "decline is still running (premature all-clears 1.45/yr OOS). An all-clear should "
                     "require that the score has stayed quiet, credit has stopped widening, and price "
                     "has lifted off its low. Thresholds 5 / 10 / 3% written from reasoning, not "
                     "searched; tested through 2023-12-29 only, beside the live state",
        "role": "candidate"}


def utc_now() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                          check=True).stdout.strip()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: ledger_rows.py <path-to-desk-trials.jsonl>")
    ledger = Path(sys.argv[1])
    txt = ledger.read_text()
    if '"id": "rr-' in txt or '"id":"rr-' in txt:
        raise SystemExit("rr- rows already exist; the ledger is append-only, not re-run")
    stamp = utc_now()
    sets = [
        ("rr-roff-incumbent", "R-off", "top", 5, "incumbent",
         {"alert": "Radar loud (state in {elevated, risk-off})"}),
        ("rr-ron-incumbent", "R-on", "bottom", 10, "incumbent",
         {"alert": "Radar loud (state in {elevated, risk-off}); a bottom is flagged by the loud state "
                   "ending (all-clear)"}),
        ("rr-roff-confluence-k4", "R-off", "top", 5, "candidate", {"confluence": CONF}),
        ("rr-ron-confluence-k4", "R-on", "bottom", 10, "candidate", {"confluence": CONF}),
        ("rr-ron-exit-v1", "R-on", "bottom", 10, "candidate", {"exit": EXIT}),
    ]
    rows = []
    for rid, fam, direction, post, role, extra in sets:
        spec = {"family": fam, "direction": direction, "primary_post": post, "role": role,
                **COMMON, **extra}
        sha = hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        rows.append({"id": rid, "card": f"Risk Radar {role} {fam} / {rid}", "author": AUTHOR,
                     "author_read_july_reports": False,
                     "features": sorted(LEGS) if "confluence" in extra else ["risk_radar_state"],
                     "label": "pivot catalogue major-tier turns, block D 2020-01-02..2023-12-29",
                     "model_class": "fixed rule as coded / written from reasoning (not fitted)",
                     "grid_size": 1, "window": "D", "utc": stamp, "family": fam, "role": role,
                     "primary_spec": spec, "spec_sha256": sha})
    with ledger.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    for r in rows:
        print(r["id"], r["spec_sha256"])


if __name__ == "__main__":
    main()
