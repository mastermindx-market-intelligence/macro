"""Write the three Risk Radar bm_ref-rev1 ledger rows (Principal 14:55Z / 15:00Z, RD 14:58Z + 15:24Z) BEFORE
any rev1 read.

  rr-roff-confluence-k3-followup-rev1-repro   (a) the frozen k3 follow-up re-read on PRE through rev1
                                              (decisive; makes the 'no nomination' result final)
  rr-roff-confluence-k3-followup-rule2b-desc  (b) ONE descriptive re-read under rule 2b, labelled
                                              "rule clarified after its result was seen"; never a nomination
  rr-roff-leg-rates-realrate-pre-desc         (c) rates_realrate alone on PRE, description only;
                                              forward candidate only (seen on D and as k3's best leg on PRE)

Usage: python3 ledger_rows_rev1.py <trials.jsonl> <catalogue/adapter.py> <catalogue/bm_ref.py>
Refuses if either sha differs from the pin or any of the three ids already exists. Append-only.
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

import ledger_rows as V1  # noqa: E402

ADAPTER_SHA = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"
BM_REF_SHA = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"  # row bm-ref-rev1-pin
K3_ROW = "rr-roff-confluence-k3-followup"
K3_ROW_SHA = "1f3bfcd49c197c65fea04ffe13c3efe4e37079cf07862b63f47b14b79a2988b6"
IDS = ("rr-roff-confluence-k3-followup-rev1-repro", "rr-roff-confluence-k3-followup-rule2b-desc",
       "rr-roff-leg-rates-realrate-pre-desc")
WINDOW = {"window": "PRE", "start_d": "2006-01-03", "end_d": "2019-12-31",
          "outcomes_through": "2019-12-31"}
CALL = ("bm_ref rev1: build_context(start_d, end_d) and reference_result(start_d, end_d); "
        "score_alerts and cluster_placebo_p90 with outcomes_through=end_d; candidate alerts cut at end_d; "
        "seed 20261112, 2000 draws, tol 0.01, post 5, t+1 shift on the full series before windowing")


def utc_now() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                          check=True).stdout.strip()


def _sha(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: ledger_rows_rev1.py <trials.jsonl> <catalogue/adapter.py> <catalogue/bm_ref.py>")
    ledger, adapter, bm = (Path(a) for a in sys.argv[1:])
    if _file_sha(adapter) != ADAPTER_SHA:
        raise SystemExit("adapter sha differs from the pin; refusing")
    if _file_sha(bm) != BM_REF_SHA:
        raise SystemExit("bm_ref sha differs from the rev1 pin; refusing")
    txt = ledger.read_text()
    if f'"id": "{K3_ROW}"' not in txt:
        raise SystemExit("frozen k3 row missing; refusing")
    for i in IDS:
        if f'"id": "{i}"' in txt:
            raise SystemExit(f"{i} already exists; append-only, not re-run")
    stamp = utc_now()
    pins = {"adapter_sha256": ADAPTER_SHA, "bm_ref_sha256": BM_REF_SHA, "bm_ref_pin_row": "bm-ref-rev1-pin",
            "episode_rule": "swing", "require_activity": True, "alert_shift_sessions": 1}
    base = {"author": V1.AUTHOR, "author_read_july_reports": False, "grid_size": 1, "window": "PRE",
            "utc": stamp, "family": "R-off",
            "label": "pivot catalogue major-tier risk_off turns, PRE 2006-01-03..2019-12-31"}

    a_spec = {"direction": "top", "primary_post": 5, "role": "candidate-reproduction", **pins, **WINDOW,
              "reproduces": K3_ROW, "reproduces_spec_sha256": K3_ROW_SHA, "call": CALL,
              "set_rule": "set_level_pass (Principal 10:25Z; (c) = best single part by catch), as frozen",
              "hand_built_reference": "followup_pre/result.json (Macro harness, bm_ref c5130e9e): "
                                      "cs .449, false 2.926, p90 .370, near .323/2.951, rates_realrate "
                                      ".795/4.97; a T b T c F",
              "difference_rule": "any difference is explained (e.g. the outcomes_through cut), never adjusted",
              "decisive": True, "verdict_role": "makes the frozen k3 'no nomination' result final"}
    b_spec = {"direction": "top", "primary_post": 5, "role": "description", **pins, **WINDOW,
              "rereads": K3_ROW, "reproduces_spec_sha256": K3_ROW_SHA, "call": CALL,
              "set_rule": "rule 2b (Principal 14:55Z): each of the 12 legs via part_at_matched_share at the "
                          "set's realised alert share, then set_level_pass_matched",
              "label_required": "rule clarified after its result was seen",
              "nomination_possible": False, "decisive": False}
    c_spec = {"direction": "top", "primary_post": 5, "role": "description", **pins, **WINDOW,
              "leg": "rates_realrate", "leg_rule": "engine trailing-504 percentile >= 0.90 (as in V1.CONF), "
              "PIT DFII10, t+1 shift", "call": CALL,
              "report": "alert share (pooled + by year), cluster share, false/asset-yr, its own cluster "
                        "placebo p90, and the better same-budget reference (dd and near via reference_result)",
              "seen_before": "D single-leg .822/4.71 (v2_bmref) and PRE .795/4.97 as k3's best part",
              "forward_candidate_only": True, "nomination_possible": False, "decisive": False}
    rows = []
    for rid, spec, card, extra in (
        (IDS[0], a_spec, "Risk Radar k3 follow-up reproduction through bm_ref rev1 (PRE)", {}),
        (IDS[1], b_spec, "Risk Radar k3 follow-up rule-2b re-read (rule clarified after its result was seen)",
         {"nomination_possible": False}),
        (IDS[2], c_spec, "Risk Radar rates_realrate leg alone on PRE (forward candidate only)",
         {"nomination_possible": False, "forward_candidate_only": True}),
    ):
        rows.append({"id": rid, "card": card, **base, "role": spec["role"],
                     "features": sorted(V1.LEGS) if rid != IDS[2] else ["rates_realrate"],
                     "model_class": "fixed rule as declared (not fitted)", **extra,
                     "primary_spec": spec, "spec_sha256": _sha(spec)})
    with ledger.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    for r in rows:
        print(r["id"], r["spec_sha256"])


if __name__ == "__main__":
    main()
