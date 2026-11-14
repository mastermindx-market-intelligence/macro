"""Write the Risk Radar v2 ledger rows (RD R1g message + Principal rulings 2026-11-12 10:25Z) BEFORE
any v2 read.

Five rr-...-v2 rows supersede the five rr- rows (scorer change: desk adapter swing episodes + activity
term, t+1 shift on the full series before windowing, as reads/r1g). One frozen follow-up row
rr-roff-confluence-k3-followup (selected after seeing D; decisive read on PRE after BM-REF).

Usage: python3 ledger_rows_v2.py <path-to-desk-trials.jsonl> <path-to-desk-catalogue/adapter.py>
Refuses to run if any rr-...-v2 or follow-up row exists, or if the adapter sha differs from the pin.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import ledger_rows as V1  # noqa: E402  (v1 constants: LEGS, EXCLUDED, COMMON, CONF, EXIT)

ADAPTER_SHA = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"
SCORER_CHANGE = ("desk adapter episode_rule='swing' + require_activity pass line (R1f, ratified "
                 "2026-11-12 10:25Z); declared t+1 shift applied to the FULL alert series before "
                 "windowing (as reads/r1g build_alerts); supersedes the R1/R1b scorer path")
SEEN_NOTE = ("this set's D numbers were seen (superseded R1 and R1b scorers) before the set-level "
             "pass definition of 2026-11-12 10:25Z; reported without a pass/fail verdict until the "
             "budget-matched reference (bm_ref) exists")
SCORER = {"adapter_sha256": ADAPTER_SHA, "episode_rule": "swing", "require_activity": True,
          "alert_shift_sessions": 1, "alert_shift_applied": "full series before windowing",
          "scorer": "r1g-conventions"}
SET_PASS = ("Principal 2026-11-12 10:25Z: (a) cluster catch share > near-turn placebo p90; (b) cluster "
            "catch > budget-matched mechanical reference with false/asset-yr <= that reference's; (c) a "
            "confluence set also beats its best single leg at <= false rate. Per-asset pass and "
            "pass-all are description only")


def utc_now() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                          check=True).stdout.strip()


def _sha(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: ledger_rows_v2.py <trials.jsonl> <catalogue/adapter.py>")
    ledger, adapter = Path(sys.argv[1]), Path(sys.argv[2])
    got = hashlib.sha256(adapter.read_bytes()).hexdigest()
    if got != ADAPTER_SHA:
        raise SystemExit(f"adapter sha {got} != pinned {ADAPTER_SHA}; refusing")
    txt = ledger.read_text()
    if "-v2\"" in txt and '"rr-' in txt and ('"id": "rr-roff-incumbent-v2"' in txt):
        raise SystemExit("rr-...-v2 rows already exist; append-only, not re-run")
    if '"id": "rr-roff-confluence-k3-followup"' in txt:
        raise SystemExit("follow-up row already exists")
    stamp = utc_now()
    common = {k: v for k, v in V1.COMMON.items() if k != "pass_line"}
    common.update(SCORER)
    common["set_pass"] = SET_PASS
    v2 = [
        ("rr-roff-incumbent", "R-off", "top", 5, "incumbent",
         {"alert": "Radar loud (state in {elevated, risk-off})"}),
        ("rr-ron-incumbent", "R-on", "bottom", 10, "incumbent",
         {"alert": "Radar loud (state in {elevated, risk-off}); a bottom is flagged by the loud state "
                   "ending (all-clear)"}),
        ("rr-roff-confluence-k4", "R-off", "top", 5, "candidate", {"confluence": V1.CONF}),
        ("rr-ron-confluence-k4", "R-on", "bottom", 10, "candidate", {"confluence": V1.CONF}),
        ("rr-ron-exit-v1", "R-on", "bottom", 10, "candidate", {"exit": V1.EXIT}),
    ]
    rows = []
    for old, fam, direction, post, role, extra in v2:
        spec = {"family": fam, "direction": direction, "primary_post": post, "role": role,
                **common, **extra, "seen_before_set_pass": SEEN_NOTE}
        rows.append({"id": f"{old}-v2", "supersedes": old, "scorer_change": SCORER_CHANGE,
                     "card": f"Risk Radar {role} {fam} / {old}-v2", "author": V1.AUTHOR,
                     "author_read_july_reports": False,
                     "features": sorted(V1.LEGS) if "confluence" in extra else ["risk_radar_state"],
                     "label": "pivot catalogue major-tier turns, block D 2020-01-02..2023-12-29",
                     "model_class": "fixed rule as coded / written from reasoning (not fitted)",
                     "grid_size": 1, "window": "D", "utc": stamp, "family": fam, "role": role,
                     "primary_spec": spec, "spec_sha256": _sha(spec)})
    # frozen follow-up (FOLLOWUP_DECLARATION.md, declared 2026-11-12T10:22Z)
    conf3 = dict(V1.CONF)
    conf3.update({"primary_k": 3, "primary_k_rule": "frozen follow-up k=3, selected after seeing D "
                  "(FOLLOWUP_DECLARATION.md 10:22Z): k=2 is a background state (~46% on), the "
                  "real-rate leg is one channel carried by the 2022 rate shock; k=3 keeps the "
                  "multi-channel premise at ~26% alert share",
                  "missing_leg_rule": "a leg with no value counts as off: effective threshold is 3 of "
                  "the available legs - 10 legs 2006-01-03..2008-05-06, 11 until 2011-12-29 "
                  "(vol_term), then 12",
                  "percentiles": "engine's own trailing 504-session causal percentiles "
                  "(leading_signals); no full-sample percentile or threshold fit",
                  "fred_pit": "availability.pit_signals(sigs, start='2006-01-03'): ALFRED first-release "
                  "dates where present, release rules elsewhere"})
    fspec = {"family": "R-off", "direction": "top", "primary_post": 5, "role": "candidate",
             **{k: v for k, v in common.items() if k not in ("block", "window", "outcomes_through")},
             "window": "PRE", "block": "2006-01-03..end of PRE (2019-12-31)",
             "outcomes_through": "2019-12-31", "confluence": conf3,
             "selected_after_seeing_D": True,
             "decisive_read": "PRE, only after the RD sends the bm_ref sha; then the desk attack seat; "
                              "no hold-out (Radar family touched 2024+); forward candidate only",
             "report_also": "alert share by year on PRE (description)"}
    rows.append({"id": "rr-roff-confluence-k3-followup", "card": "Risk Radar follow-up R-off / "
                 "confluence k=3 (selected after seeing D)", "author": V1.AUTHOR,
                 "author_read_july_reports": False, "features": sorted(V1.LEGS),
                 "label": "pivot catalogue major-tier risk_off turns, block PRE from 2006-01-03",
                 "model_class": "fixed equal-vote rule (not fitted)", "grid_size": 1, "window": "PRE",
                 "utc": stamp, "family": "R-off", "role": "candidate",
                 "selected_after_seeing_D": True, "primary_spec": fspec, "spec_sha256": _sha(fspec)})
    with ledger.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    for r in rows:
        print(r["id"], r["spec_sha256"])


if __name__ == "__main__":
    main()
