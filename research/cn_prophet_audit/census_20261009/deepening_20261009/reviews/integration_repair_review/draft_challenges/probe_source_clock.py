#!/usr/bin/env python3
"""Independent source/pack knowledge-time challenges to one retained draft."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from review_support import capture, hash_file, load_native, load_subject, read

DRAFT_SHA = "a0c26607448a7f57f296393508f3b0a92c8a1eea9ee44bf4a053464dcb76a335"
ADAPTER_SHA = "bd8bfd85bf4ff1279d564220b7f3f8b8b4e5f7263323252ae6489ed5163d1074"


def main():
    assert hash_file(HERE / "challenged_contract.py") == DRAFT_SHA
    B = load_subject(HERE / "challenged_contract.py")
    modules, source_ids = load_native()
    R2 = modules["engine/prophet_live/r2io.py"]
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    LS = modules["engine/prophet_live/live_states.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    calendar = modules["lib/cn_calendar.py"]
    adapter = HERE.parents[2] / "repairs/integration_contract/pinned_quote_adapter.py"
    assert hash_file(adapter) == ADAPTER_SHA
    resolver = B.SyntheticQuoteResolver(adapter.read_bytes())
    fixture = read(HERE / "source_clock_input.json")
    base, settlement = fixture["base_pack"], fixture["settlement_pack"]
    original_doc = fixture["event_envelope"]
    now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)

    def ingest(pack, doc):
        store = B.MemoryR2()
        store.put(B.pack_key(pack, R2), pack)
        store.put(B.pack_key(settlement, R2), settlement)
        store.put(B.spool_key(doc, R2), doc)
        return B.consume(store, R2, CR, clock, calendar, LS, session="2026-10-12",
                         now=now, existing=[], settlement_pack=settlement,
                         canonical_board=None, canonical_board_raw=None,
                         quote_resolver=resolver)

    rows, _ = ingest(base, original_doc)
    event = original_doc["events"][0]
    assert rows[0]["first_ts"] == "2026-10-12T02:00:00Z"
    assert B.stamp(event["source_evidence"]["recorded_at"]) > B.stamp(event["ts"])
    positive = deepcopy(original_doc)
    ev = positive["events"][0]
    ev["ts"] = fixture["native_event_ts"]
    ev.pop("event_id")
    ev["event_id"] = B.digest({"pack_id": base["pack_id"], **ev})
    positive_rows, _ = ingest(base, positive)
    assert positive_rows[0]["first_ts"] == fixture["native_event_ts"]

    # Isolate the other authority: the source receipt is now available at the
    # event, but the archived generation is built one minute after the event.
    future_pack = deepcopy(base)
    future_pack["built_at"] = "2026-10-12T02:01:00Z"
    future_pack.pop("pack_id")
    future_pack["pack_id"] = B.digest(future_pack)
    late_doc = deepcopy(original_doc)
    late_doc["pack_id"] = future_pack["pack_id"]
    ev = late_doc["events"][0]
    payload_raw = ev["source_evidence"]["payload_utf8"].encode("utf-8")
    at_event = datetime(2026, 10, 12, 2, 0, tzinfo=timezone.utc)
    quotes = resolver.quotes(payload_raw, recorded_at=at_event)
    ev["source_evidence"] = quotes[ev["ticker"]]["source_evidence"]
    ev["quote_age_min"] = 0.0
    ev.pop("event_id")
    ev["event_id"] = B.digest({"pack_id": future_pack["pack_id"], **ev})
    late_rows, _ = ingest(future_pack, late_doc)
    assert B.stamp(future_pack["built_at"]) > B.stamp(ev["ts"])
    assert B.stamp(ev["source_evidence"]["recorded_at"]) == B.stamp(ev["ts"])
    assert late_rows[0]["first_ts"] == "2026-10-12T02:00:00Z"

    cases = [
        {"id": "R-C1", "name": "source receipt after event",
         "pack": base, "envelope": original_doc,
         "returned_first_observation": B.first_observation(rows[0]),
         "source_recorded_at": event["source_evidence"]["recorded_at"],
         "first_ts": rows[0]["first_ts"], "outcome": "accepted"},
        {"id": "R-C2", "name": "archived generation built after event",
         "pack": future_pack, "envelope": late_doc,
         "returned_first_observation": B.first_observation(late_rows[0]),
         "source_recorded_at": ev["source_evidence"]["recorded_at"],
         "pack_built_at": future_pack["built_at"],
         "first_ts": late_rows[0]["first_ts"], "outcome": "accepted"},
    ]
    result = {
        "status": "TWO_EVENT_TIME_AUTHORITY_GAPS_CONFIRMED",
        "draft_sha256": DRAFT_SHA, "probe_sha256": hash_file(Path(__file__)),
        "native_source_sha256": source_ids, "quote_adapter_sha256": ADAPTER_SHA,
        "cases": cases,
        "positive_native_timestamp_replay": {"outcome": "accepted",
            "first_ts": positive_rows[0]["first_ts"], "event_count": len(positive_rows)},
        "required": "Both exact source receipt and archived generation must be available by event time, not merely envelope publication time.",
        "limits": ["The normal native evaluator emitted 02:01; the early 02:00 timestamp is an explicit synthetic persisted-event mutation.",
                   "The second case reseals a synthetic later-built pack to isolate the independent pack-availability check.",
                   "No natural production occurrence, market execution, collector or vendor request is claimed."],
    }
    path = HERE / "CLOCK_EVIDENCE.json"
    path.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "cases": len(cases), "evidence_sha256": hash_file(path)}))


if __name__ == "__main__":
    main()
