"""Write two ledger rows BEFORE any BT1 read (Principal 18:40Z; RD-signed wording):

  rr-bt1-rate-response-pre-desc   BREAKTHROUGH-1 approach #1, frozen, read on PRE 2006-2019 through bm_ref rev1
                                  as DESCRIPTION ONLY (never a nomination; one set read in the chance account)
  rr-followup-declaration-erratum FOLLOWUP_DECLARATION.md lines 19-20 ("at least 11 of the 12 legs") vs lines
                                  40-46 (accepted condition: 10 legs before 2008-05-07); no result changes

Usage: python3 ledger_rows_bt1.py <trials.jsonl> <catalogue/adapter.py> <catalogue/bm_ref.py> <BREAKTHROUGH_1_ANSWER.md>
Refuses on any pin mismatch or if either id exists. Append-only.
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
BM_REF_SHA = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"
ANSWER_SHA = "2cfaef73a7af48d5c12a55259d602367e10cb73df80324bdff61f138cb7e9abf"  # macro#11104 comment 6831594191
IDS = ("rr-bt1-rate-response-pre-desc", "rr-followup-declaration-erratum")

LABEL = ("BT1 approach #1; selected after seeing rates_realrate on PRE and D; PRE 2006–2019 read is description "
         "only; never a nomination; counts as one set read in the cumulative chance account")

DEFINITION = {
    "source": "PRO-RUN BREAKTHROUGH-1, macro#11104 comment 6831594191, sha256 " + ANSWER_SHA + "; rule as stated there",
    "primitives": {
        "B20_X(t)": "log(min(X[t-20..t-1]) / X[t]); > 0 means a new closing low vs the preceding 20 sessions",
        "qR(t)": "engine rates_realrate as coded: trailing-504-session causal percentile of DFII10.diff(5), "
                 "point-in-time (availability.pit_signals, ALFRED first-release dates)",
        "dy5(t)": "DFII10.diff(5), the signed raw change behind qR, same PIT availability",
        "X": "desk level series SPY (catalogue spec) and QQQ (catalogue spec), adjusted closes",
    },
    "Rplus(t)": "max qR(s) over s in {t-5..t-1} with dy5(s) > 0; 0 if all five observations valid and none has "
                "dy5 > 0; undefined (not alerting) otherwise",
    "A_R(t)": "[Rplus(t) >= .90] AND [B20_SPY(t) > 0] AND [B20_QQQ(t) > 0]",
    "constants": "0, .90, 5, 20 fixed as stated; no sweep, neighbour search or fallback threshold; "
                 "not revised after any figure is seen; a weak description closes the rule",
    "alert_convention": "one market-level alert broadcast to every panel series (as the k3 follow-up), "
                        "t+1 shift on the full series before windowing",
}
PARTS = {
    "rule_2b_parts_at_matched_share": ["Rplus", "B20_SPY", "B20_QQQ",
                                       "response-only min(B20_SPY, B20_QQQ) (benchmark encoding only)"],
    "ablation_adversaries_at_matched_share": {
        "D5": "max dy5[t-5..t-1] (signed-change-only clock)",
        "Q5": "max qR[t-5..t-1] (sign-unrestricted clock; the unsigned rate comparator at equal alert share)",
    },
    "native_leg": "recorded .795 / 4.97 (rr-roff-confluence-k3-followup-rev1-repro); NOT re-read",
    "principal_diagnosis": "state whether the sign gate (Rplus vs Q5) and the response condition (A_R vs Rplus) "
                           "each lower false calls at equal alert share",
}
CONTROL = ("displaced-clock control (description line, not a gate on this read): within each PRE calendar year "
           "circularly shift the constructed Rplus by an integer uniform in 27..(n_year-27), the same shift for "
           "every asset; re-form A_R with unchanged price predicates; after the t+1 shift and window cut keep draws "
           "whose ON-day and start counts match the observed within one; up to 200,000 offset vectors, seed "
           "20261113, first 2,000 qualifying draws (fewer = NOT_ESTIMABLE); report the p10 of catch differences "
           "and the p90 of false-rate differences (observed minus displaced), plus draw counts and run lengths. "
           "Also report the fragmentation diagnostic (first start per shock episode) and whether either equity "
           "break was already true in the five sessions before each shock episode.")


def utc_now() -> str:
    return subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                          check=True).stdout.strip()


def _sha(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: ledger_rows_bt1.py <trials.jsonl> <adapter.py> <bm_ref.py> <BREAKTHROUGH_1_ANSWER.md>")
    ledger, adapter, bm, answer = (Path(a) for a in sys.argv[1:])
    for p, want, name in ((adapter, ADAPTER_SHA, "adapter"), (bm, BM_REF_SHA, "bm_ref"),
                          (answer, ANSWER_SHA, "answer")):
        if _file_sha(p) != want:
            raise SystemExit(f"{name} sha differs from the pin; refusing")
    txt = ledger.read_text()
    for i in IDS:
        if f'"id": "{i}"' in txt:
            raise SystemExit(f"{i} already exists; append-only")
    stamp = utc_now()
    spec = {"family": "R-off", "direction": "top", "primary_post": 5, "role": "description",
            "label": LABEL, "definition": DEFINITION, "parts": PARTS, "displaced_clock_control": CONTROL,
            "adapter_sha256": ADAPTER_SHA, "bm_ref_sha256": BM_REF_SHA, "answer_sha256": ANSWER_SHA,
            "window": "PRE", "start_d": "2006-01-03", "end_d": "2019-12-31",
            "outcomes_through": "2019-12-31", "episode_rule": "swing", "require_activity": True,
            "alert_shift_sessions": 1, "seed": 20261112, "n_draws": 2000, "tol": 0.01,
            "set_rule": "set_level_pass_matched (rule 2b) reported as description",
            "nomination_possible": False, "counts_in_chance_account": True,
            "approved": "Principal 2026-11-12T18:40Z; row wording signed by the RD"}
    rows = [
        {"id": IDS[0], "card": "Risk Radar BT1-RATE-RESPONSE on PRE (description only)", "author": V1.AUTHOR,
         "author_read_july_reports": False, "family": "R-off", "role": "description", "window": "PRE",
         "label": LABEL, "features": ["rates_realrate(signed)", "SPY B20", "QQQ B20"],
         "model_class": "fixed rule as stated by BREAKTHROUGH-1 (not fitted)", "grid_size": 1,
         "nomination_possible": False, "counts_in_chance_account": True, "utc": stamp,
         "primary_spec": spec, "spec_sha256": _sha(spec)},
        {"id": IDS[1], "role": "erratum", "author": V1.AUTHOR, "written_utc": stamp,
         "amends": "rr-roff-confluence-k3-followup",
         "file": "research/risk_radar/catalogue_read/FOLLOWUP_DECLARATION.md",
         "was": "lines 19-20: PRE starts at 'the first date with at least 11 of the 12 legs present'",
         "now": "lines 40-46 (RD-accepted condition) govern: 10 legs before 2008-05-07, 11 until 2011-12-30, then "
                "12; the read and the rev1 reproduction followed lines 40-46",
         "result_change": "no result changes",
         "found_by": "BREAKTHROUGH-1 answer (comment 6831594191), confirmed by the Radar leader; RD accepted"},
    ]
    with ledger.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    print(IDS[0], rows[0]["spec_sha256"])
    print(IDS[1], "erratum written", stamp)


if __name__ == "__main__":
    main()
