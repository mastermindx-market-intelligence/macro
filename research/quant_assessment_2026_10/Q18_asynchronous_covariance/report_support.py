from __future__ import annotations

"""Q18 reporting-only support artifact (PREREG_AMENDMENT.md A2).

Writes ``results/support_report.json``:

* the close-clock class of every studied clock pairing over every weekday of the
  frozen holdout period (depends only on declared clocks and dates; no prices read);
* the effective moving-block-bootstrap block count, read from the existing
  ``results/primary_results.json`` (H1 ``n_time_blocks`` / frozen block length).

It selects nothing, changes no estimate, bar or verdict rule, and appends its own
record to RUNS.log (script sha256, exit code, output sha256).
"""

import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "results" / "support_report.json"
PRIMARY = HERE / "results" / "primary_results.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_evaluate():
    spec = importlib.util.spec_from_file_location("q18_evaluate_constants", HERE / "evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # __main__ block is guarded; nothing runs
    return mod


def build() -> dict:
    import pandas as pd

    sys.path.insert(0, str(REPO))
    from engine import async_session_covariance as asc

    ev = _load_evaluate()
    first = pd.Period(ev.HOLDOUT_FIRST, freq="Q").start_time
    last = pd.Period(ev.HOLDOUT_LAST, freq="Q").end_time.normalize()
    days = list(pd.bdate_range(first, last))
    pairings = {
        "SSE_vs_NYSE (510300.SS vs SPY)": (asc.SSE, asc.NYSE),
        "HKEX_INDEX_vs_NYSE (_HSCE vs SPY)": (asc.HKEX_INDEX, asc.NYSE),
        "NYSE_vs_NYSE (ASHR/FXI proxy target vs SPY)": (asc.NYSE, asc.NYSE),
        "SSE_vs_HKEX_INDEX (510300.SS vs _HSCE)": (asc.SSE, asc.HKEX_INDEX),
    }
    clocks = {}
    for name, (a, b) in pairings.items():
        c = asc.classify_pair_clock(a, b, days)
        clocks[name] = {"clock": c["clock"], "distinct_lag_seconds": c["lag_seconds"]}

    prim = json.loads(PRIMARY.read_text())
    n_blocks = int(prim["H1"]["n_time_blocks"])
    return {
        "study": "Q18",
        "kind": "reporting_only (PREREG_AMENDMENT.md A2)",
        "clock_class_basis": {"dates": "every weekday of the frozen holdout period",
                              "first": str(first.date()), "last": str(last.date()), "n_dates": len(days)},
        "clock_class": clocks,
        "bootstrap_support": {"n_time_blocks": n_blocks, "block_len": ev.MBB_BLOCK,
                              "effective_blocks": round(n_blocks / ev.MBB_BLOCK, 4),
                              "n_boot": ev.MBB_B, "seed": ev.MBB_SEED, "nw_lags": ev.NW_LAGS,
                              "note": "pairs resampled jointly; quarters are the time unit"},
        "primary_results_sha256": _sha(PRIMARY),
    }


if __name__ == "__main__":
    rc = 0
    try:
        rep = build()
        OUT.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
        print(json.dumps(rep, indent=1))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        rc = 1
    rec = {"script": "report_support.py", "kind": "reporting_only",
           "command": "python3.12 " + str(Path(__file__).resolve()), "exit_code": rc,
           "script_sha256": _sha(Path(__file__).resolve()),
           "module_sha256": _sha(REPO / "engine" / "async_session_covariance.py"),
           "input_sha256": {"results/primary_results.json": _sha(PRIMARY)}}
    if rc == 0:
        rec["output_sha256"] = {"results/support_report.json": _sha(OUT)}
    with open(HERE / "RUNS.log", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    sys.exit(rc)
