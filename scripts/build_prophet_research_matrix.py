#!/usr/bin/env python3
"""Print a read-only Prophet RQ1 PIT matrix from the canonical B1 store."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.entry_radar.entry_events import EntryEventStore  # noqa: E402
from engine.prophet_research_matrix import build_pit_research_matrix_from_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-store", type=Path, required=True)
    parser.add_argument("--decision-at", required=True, help="RFC3339 UTC timestamp")
    parser.add_argument(
        "--radar-event-jsonl",
        type=Path,
        help="optional existing mastermind.entry_event.v1 JSONL store; never modified",
    )
    args = parser.parse_args()
    radar = {}
    if args.radar_event_jsonl is not None:
        store = EntryEventStore.from_jsonl(args.radar_event_jsonl.read_text(encoding="utf-8"))
        radar = {str(event.event_id): event for event in store.events()}
    matrix = build_pit_research_matrix_from_store(
        args.candidate_store,
        decision_at=args.decision_at,
        radar_events=radar,
    )
    print(json.dumps(matrix, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
