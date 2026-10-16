#!/usr/bin/env python3
"""Reproduce the producer-found precision problem through real native code.

No event is backdated in this control. The d633 draft itself inherits native
second truncation, which makes a valid fractional receipt appear unavailable.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REVIEW = HERE.parents[1]
sys.path.insert(0, str(REVIEW))
from review_support import capture, hash_file, load_native, load_subject, read


def main():
    expected = "d633f0baeb8d506053387c15f5712ebd49c4b6b9b392a43e8e143e3c3226ee4f"
    assert hash_file(HERE / "contract_prototype.py") == expected
    B = load_subject(HERE / "contract_prototype.py")
    modules, native_ids = load_native()
    R2 = modules["engine/prophet_live/r2io.py"]
    LS = modules["engine/prophet_live/live_states.py"]
    CS = modules["engine/prophet_live/cn_states.py"]
    CR = modules["engine/prophet_live/cn_reconcile.py"]
    clock = modules["engine/prophet_live/cn_clock.py"]
    calendar = modules["lib/cn_calendar.py"]
    fixture = read(HERE / "independent_fixture.json")
    pack = fixture["base_pack"]
    resolver = B.SyntheticQuoteResolver((HERE / "pinned_quote_adapter.py").read_bytes())
    observed = datetime(2026, 10, 12, 2, 0, 0, 250000, tzinfo=timezone.utc)
    payload = {"spark": {"result": [
        {"symbol": ticker, "response": [{"meta": {
            "regularMarketPrice": fixture["prices"][ticker],
            "previousClose": entry["as_of_close"],
            "regularMarketTime": int(observed.timestamp()), "currency": "CNY"}}]}
        for ticker, entry in sorted(pack["names"].items())]}}
    quotes = resolver.quotes(B.encoded(payload), recorded_at=observed)
    art = B.evaluate_checked(CS.evaluate, LS, clock, pack, quotes, None,
                             now=observed, cfg=LS.live_cfg({"live": {"delayed_min": 0}}),
                             delay_min=0, quote_resolver=resolver)
    assert len(art["events"]) == 3
    doc = B.envelope(art, art["events"], pack)
    store = B.MemoryR2()
    store.put(B.pack_key(pack, R2), pack)
    store.put(B.spool_key(doc, R2), doc)
    got = capture(lambda: B.consume(store, R2, CR, clock, calendar, LS,
        session="2026-10-12", now=datetime(2026, 10, 12, 12, tzinfo=timezone.utc),
        existing=[], settlement_pack=fixture["settlement_pack"],
        canonical_board=fixture["canonical_board"],
        canonical_board_raw=fixture["canonical_board_utf8"].encode(), quote_resolver=resolver))
    assert got.get("exception_class") == "Refused" and got.get("reason") == "future_quote_source_receipt"
    assert all(B.stamp(event["ts"]) < observed for event in art["events"])
    result = {"status": "NORMAL_NATIVE_PRECISION_REGRESSION_CONFIRMED",
              "contract_sha256": expected, "script_sha256": hash_file(Path(__file__)),
              "source_sha256": native_ids, "supplied_observation_at": observed.isoformat(),
              "artifact_built_at": art["built_at"], "event_timestamps": [e["ts"] for e in art["events"]],
              "unchanged_native_event_envelope": doc, "ingestion_result": got,
              "required": "Retain the supplied evaluation instant in event/envelope timestamps; keep strict source-before-event validation.",
              "limits": ["This uses realistic fractional time through the normal native evaluator, with explicitly synthetic quote bytes.",
                         "No event or envelope timestamp was mutated by this probe.",
                         "No natural production occurrence, genuine vendor source or market execution is certified."]}
    destination = HERE / "PRECISION_EVIDENCE.json"
    destination.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "evidence_sha256": hash_file(destination)}))


if __name__ == "__main__":
    main()
