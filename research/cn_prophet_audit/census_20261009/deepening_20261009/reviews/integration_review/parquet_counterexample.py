#!/usr/bin/env python3
"""Run the duplicate-key counterexample with a real installed Parquet engine.

Uses an existing isolated native-source export, checks every imported subject
against immutable recorded hashes, and writes only to the requested review dir.
No source worktree import, collector, credential request, or network call.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--lab-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source, lab, out = [Path(x).resolve() for x in (args.source_root, args.lab_root, args.out)]
    temp_root = Path("/tmp").resolve()
    assert source.is_relative_to(temp_root) and any(p.startswith("mmx-cn-integration-lab-") for p in source.parts)
    assert out.is_relative_to(temp_root) and any(p.startswith("mmx-cn-integration-review-") for p in out.parts)
    assert source != out and lab != out and not out.is_relative_to(source) and not out.is_relative_to(lab)
    out.mkdir(parents=True, exist_ok=True)
    expected = {
        "contract_prototype.py": "df11434734c550715df92596f70cd0a0da1b0e042865c5737c6aa5adc6ecebd0",
        "results/integration_fixture.json": "fe7e1123269eac895eb324cbe3510ec3de9cfbfce10c44518c593d550d34a545",
        "results/integration_results.json": "58ab978836c10cc9f6cc6b508e7f93c8aaa68f448e56a39137acb0caace69128",
    }
    for path, digest in expected.items():
        assert sha(lab / path) == digest, path
    retained = json.loads((lab / "results/integration_results.json").read_text())
    native_paths = ["lib/exchange_holidays.py", "lib/cn_calendar.py", "engine/prophet_live/interval.py",
                    "engine/prophet_live/live_states.py", "engine/prophet_live/cn_clock.py",
                    "engine/prophet_live/cn_reconcile.py", "engine/prophet_live/r2io.py", "scripts/reconcile_cn_live.py"]
    native_hashes = {path: sha(source / path) for path in native_paths}
    assert all(value == retained["source_manifest"][path]["sha256"] for path, value in native_hashes.items())
    sys.path[:0] = [str(lab), str(source)]
    import contract_prototype as B
    from engine.prophet_live import cn_clock as clock, cn_reconcile as CR, live_states as LS, r2io as R2
    from lib import cn_calendar as calendar
    from scripts import reconcile_cn_live as RD
    import pandas as pd
    fixture = json.loads((lab / "results/integration_fixture.json").read_text())
    base, settlement = fixture["base_pack"], fixture["settlement_pack"]
    store = B.MemoryR2()
    for key, doc in fixture["events"].items():
        store.put(key, doc)
    store.put(B.pack_key(base, R2), base)
    store.put(R2.CN_PACK_KEY, settlement)

    def ingest(prior):
        return B.consume(store, R2, CR, clock, calendar, LS, session="2026-10-12",
            now=datetime(2026, 10, 12, 12, tzinfo=timezone.utc), existing=prior,
            settlement_pack=settlement, canonical_board=None, canonical_board_raw=None)

    baseline, _ = ingest([])
    assert B.encoded(baseline) == B.encoded(fixture["ledger"])
    duplicate = deepcopy(baseline[0])
    duplicate["event_ids"].append("d" * 64)
    duplicate["occurrences"] += 1
    duplicate["last_ts"] = "2026-10-12T02:01:00Z"
    existing = deepcopy(baseline) + [duplicate]
    path = out / "duplicate_daily_keys.parquet"
    pd.DataFrame(existing).to_parquet(path, index=False)
    before = path.read_bytes()
    (out / "duplicate_daily_keys.before.parquet").write_bytes(before)
    assert len(pd.read_parquet(path)) == 5
    writes = []

    def writer(dest, rows):
        writes.append(len(rows))
        RD._write_parquet(dest, rows)

    merged, receipt = B.reconcile_file(path, read_frame=pd.read_parquet,
        write_rows=writer, reconcile=ingest)
    assert len(merged) == len(pd.read_parquet(path)) == 4 and writes == [4]
    assert "d" * 64 not in {event for row in merged for event in row["event_ids"]}
    try:
        ingest([duplicate] + deepcopy(baseline))
    except B.Refused as exc:
        reversed_reason = exc.reason
    else:
        raise AssertionError("Reversed duplicate should trigger the existing partial-regression check")
    assert reversed_reason == "spool_regression"
    assert all(sha(lab / path) == digest for path, digest in expected.items())
    assert all(sha(source / path) == digest for path, digest in native_hashes.items())
    result = {"schema": "cn_integration_native_parquet_review_v1", "status": "CONFIRMED_DATA_LOSS_COUNTEREXAMPLE",
        "study_source_sha": retained["study_source_sha"], "script_sha256": sha(Path(__file__)),
        "subject_inputs_sha256": expected, "native_source_sha256": native_hashes,
        "evidence": {"input_row_n": 5, "output_row_n": 4, "lost_event_id": "d" * 64,
                     "lost_event_present_after_write": False, "native_writer_row_counts": writes,
                     "reverse_order_refusal": reversed_reason,
                     "before_sha256": sha256(before).hexdigest(), "after_sha256": sha(path)},
        "execution": {"python": sys.version, "pandas": pd.__version__, "out": str(out),
                      "source_root": str(source), "lab_root": str(lab)},
        "source_and_original_lab_unchanged": True, "synthetic_fixture_only": True,
        "network_disabled": True}
    (out / "parquet_review_receipt.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "receipt_sha256": sha(out / "parquet_review_receipt.json"),
                      "input_rows": 5, "output_rows": 4, "writer_calls": len(writes), "out": str(out)}))


if __name__ == "__main__":
    def blocked(*args, **kwargs):
        raise RuntimeError("Network disabled in native Parquet counterexample")
    with patch.object(socket.socket, "connect", blocked), patch.object(socket, "create_connection", blocked):
        main()
