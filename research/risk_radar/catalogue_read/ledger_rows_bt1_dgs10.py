"""Write ledger row rr-bt1-rate-response-pre-dgs10-desc BEFORE its read (Principal release condition 2,
RELEASE_RADAR_EARLY_BLOCK.md): the frozen BT1 rule (rr-bt1-rate-response-pre-desc) run once on PRE 2006-2019 with
FRED DGS10 in place of DFII10, as description, so an early-block result can be told apart from the substitute.

Usage: python3 ledger_rows_bt1_dgs10.py <trials.jsonl> <catalogue/adapter.py> <catalogue/bm_ref.py>
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
import ledger_rows_bt1 as BT1  # noqa: E402

RID = "rr-bt1-rate-response-pre-dgs10-desc"
PARENT = "rr-bt1-rate-response-pre-desc"
PARENT_SHA = "d80306439c57cdc945d27055551647b329bce5e1987ea6e623d7b1effc4f276a"


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: ledger_rows_bt1_dgs10.py <trials.jsonl> <adapter.py> <bm_ref.py>")
    ledger, adapter, bm = (Path(a) for a in sys.argv[1:])
    if hashlib.sha256(adapter.read_bytes()).hexdigest() != BT1.ADAPTER_SHA:
        raise SystemExit("adapter pin mismatch")
    if hashlib.sha256(bm.read_bytes()).hexdigest() != BT1.BM_REF_SHA:
        raise SystemExit("bm_ref pin mismatch")
    txt = ledger.read_text()
    if f'"id": "{PARENT}"' not in txt:
        raise SystemExit("parent row missing")
    if f'"id": "{RID}"' in txt:
        raise SystemExit("row exists; append-only")
    stamp = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True,
                           check=True).stdout.strip()
    spec = {"family": "R-off", "direction": "top", "primary_post": 5, "role": "description",
            "variant_of": PARENT, "variant_of_spec_sha256": PARENT_SHA,
            "substitution": "qR and dy5 built from FRED DGS10 (nominal 10y) instead of DFII10: dy5 = DGS10.diff(5), "
                            "qR = engine trailing-504-session causal percentile of dy5 (pct_rank_window as coded), "
                            "next-business-day availability (observation t usable from t+1 session); "
                            "every other element of the frozen rule unchanged (Rplus, .90, B20_SPY, B20_QQQ, parts, "
                            "control, seeds)",
            "purpose": "Principal release condition 2 (RELEASE_RADAR_EARLY_BLOCK.md): tell an early-block result apart "
                       "from an effect of the substitute; changes nothing in the rule",
            "adapter_sha256": BT1.ADAPTER_SHA, "bm_ref_sha256": BT1.BM_REF_SHA, "answer_sha256": BT1.ANSWER_SHA,
            "window": "PRE", "start_d": "2006-01-03", "end_d": "2019-12-31", "outcomes_through": "2019-12-31",
            "nomination_possible": False, "counts_in_chance_account": True}
    row = {"id": RID, "card": "Risk Radar BT1-RATE-RESPONSE on PRE with DGS10 substitute (description only)",
           "author": V1.AUTHOR, "author_read_july_reports": False, "family": "R-off", "role": "description",
           "window": "PRE", "label": BT1.LABEL + "; DGS10 substitute line for the early-block release",
           "features": ["DGS10 dy5 (signed)", "SPY B20", "QQQ B20"],
           "model_class": "fixed rule as frozen (not fitted)", "grid_size": 1, "nomination_possible": False,
           "counts_in_chance_account": True, "utc": stamp, "primary_spec": spec,
           "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    with ledger.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(RID, row["spec_sha256"], stamp)


if __name__ == "__main__":
    main()
