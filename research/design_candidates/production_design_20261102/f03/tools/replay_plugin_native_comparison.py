#!/usr/bin/env python3
"""Offline replay of original-carrier reads through the owning Paper guard.

No Paper network call, mutation or plugin installation is performed. Run with
the exact qualified Mastermind source checked out separately. The result
identifies the actual source bytes and every recorded read it consumed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


def replay(raw_path: Path, guard_path: Path) -> dict:
    raw_bytes = raw_path.read_bytes()
    spec = importlib.util.spec_from_file_location("f03_paper_read_guard", guard_path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    recorded = guard.bridge.load_json(raw_bytes)
    if recorded.get("kind") != "F03_native_comparison_raw_read_sequence_v1":
        raise ValueError("unexpected readback format")
    if recorded.get("paper_mutations") != 0 or recorded.get("installed_guard_execution") is not False:
        raise ValueError("incorrect evidence scope")
    reads = recorded["reads"]
    source_id = reads[0]["request"]["arguments"]["fileId"]
    candidate_id = reads[1]["request"]["arguments"]["fileId"]
    page_id = reads[2]["request"]["arguments"]["pageId"]
    node_id = reads[4]["request"]["arguments"]["nodeId"]
    cursor = 0

    def recorded_read(action, *, tool, arguments):
        nonlocal cursor
        if action != "read" or cursor >= len(reads):
            raise ValueError("unrecorded or modifying action refused")
        row = reads[cursor]
        if row["request"] != {"tool": tool, "arguments": arguments}:
            raise ValueError(f"read order/identity mismatch at {cursor}")
        if row.get("transport_error") is not None or row["response"]["state"] != "OBSERVED":
            raise ValueError("unsuccessful native read")
        if row["started_at"] > row["finished_at"]:
            raise ValueError("invalid capture interval")
        if cursor and reads[cursor - 1]["finished_at"] > row["started_at"]:
            raise ValueError("capture sequence not chronological")
        cursor += 1
        return row["response"]

    with patch.object(guard.bridge, "execute", side_effect=recorded_read):
        result = guard.compare_file_pair(source_id, candidate_id,
                                         page_ids=[page_id], evidence_node_ids=[node_id])
    if cursor != len(reads):
        raise ValueError("unconsumed recorded reads")
    return {
        "kind": "F03_native_plugin_guard_offline_replay_v1",
        "raw_readback_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "guard_source_sha256": hashlib.sha256(guard_path.read_bytes()).hexdigest(),
        "reads_consumed": cursor,
        "read_started_at": reads[0]["started_at"],
        "read_finished_at": reads[-1]["finished_at"],
        "installed_guard_execution": False,
        "replays_recorded_original_carrier_reads": True,
        "native_transport_reexecuted_by_replay": False,
        "paper_mutations": 0,
        "comparison": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("readback", type=Path)
    parser.add_argument("--guard-source", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.readback, args.guard_source)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    state = result["comparison"]["state"]
    codes = {"OBSERVED_SCOPE_PARITY": 0, "OBSERVED_SCOPE_DIVERGENCE": 3,
             "OBSERVED_SCOPE_INCOMPLETE": 4}
    if state not in codes:
        raise ValueError("unknown comparison state; no successful replay claim")
    return codes[state]


if __name__ == "__main__":
    raise SystemExit(main())
