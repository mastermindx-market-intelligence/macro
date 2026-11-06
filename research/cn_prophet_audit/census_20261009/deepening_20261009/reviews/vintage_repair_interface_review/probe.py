#!/usr/bin/env python3
"""Two independent, pre-seal interface falsifiers for the vintage repair.

The reviewed draft is retained byte for byte. This script never imports the
producer's mutable repair, a collector, or a production source tree.
"""
from pathlib import Path
from types import ModuleType
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
EXPECTED = "ad90cf372a95ae7ca05691681d95ea9a18e784a1379066e19e15fa05b0ef6b7d"


def main():
    raw_code = (HERE / "challenged_contract.py").read_bytes()
    assert hashlib.sha256(raw_code).hexdigest() == EXPECTED
    C = ModuleType("independently_challenged_vintage_draft")
    C.__file__ = str(HERE / "challenged_contract.py")
    exec(compile(raw_code, C.__file__, "exec"), C.__dict__)
    sessions = {day: {"session_open": day + "T09:30:00+08:00",
                      "session_close": day + "T15:00:00+08:00"}
                for day in ("2026-09-16", "2026-10-12")}
    calendar = C.CalendarFixture(sessions)
    source = {
        "schema": "research.price_fixture.v2", "fixture_only": True,
        "ticker": "000001.SZ", "provider_id": "synthetic-review-only",
        "basis_id": "fixture-v1", "price_adjustment": "unadjusted",
        "clock_kind": "producer_available_at",
        "available_at": "2026-09-16T08:00:00Z",
        "rows": [{"session": "2026-09-16", "bar": {"close": 100}},
                 {"session": "2026-10-12", "bar": {"close": 110}}],
    }
    raw = C.canonical_bytes(source)
    key = hashlib.sha256(raw).hexdigest()
    resolver = {key: raw}.__getitem__
    mark = C.mark_from_source(ticker="000001.SZ", session="2026-09-16",
                             anchor="session_close", source_sha256=key,
                             resolve_source=resolver, calendar=calendar)
    observed = C.validate_mark(mark, "2026-09-16T08:01:00Z",
                               resolve_source=resolver, calendar=calendar)
    assert observed["session"] == "2026-09-16"
    # A selected future row does trigger the old guard; the flaw is the other
    # finalized row in a blob whose one declared clock applies to all bytes.
    try:
        C.mark_from_source(ticker="000001.SZ", session="2026-10-12",
                           anchor="session_close", source_sha256=key,
                           resolve_source=resolver, calendar=calendar)
    except C.EvidenceError as exc:
        selected_future_reason = str(exc)
    else:
        raise AssertionError("selected future control unexpectedly accepted")
    assert selected_future_reason == "SOURCE_PRECEDES_FINALIZED_BAR"

    body = {"kind": "original_entry", "decision_id": "review-only",
            "ticker": "000001.SZ", "entry_session": "2026-09-16",
            "price": 100, "basis": "t1_open",
            "recorded_at": "2026-09-16T08:00:00Z"}
    original = C.seal_event(body)
    correction = C.seal_event({**body, "kind": "entry_correction", "price": 99,
                               "correction_of": original["event_id"],
                               "reason": "same-clock counterexample"})
    ledger = C.append_event([original], correction)
    assert ledger == [original, correction]
    assert original["recorded_at"] == correction["recorded_at"]
    result = {
        "status": "TWO_PRESEAL_BOUNDARY_GAPS_CONFIRMED",
        "challenged_contract_sha256": EXPECTED,
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "calendar_fixture": sessions,
        "findings": [
            {"id": "V-R1", "subject": "blob-wide availability",
             "source_fixture": source, "source_sha256": key,
             "selected_mark": observed, "graded_at": "2026-09-16T08:01:00Z",
             "outcome": "accepted",
             "selected_future_control_refusal": selected_future_reason,
             "required": "Validate every finalized row against the single blob availability clock."},
            {"id": "V-R2", "subject": "strict correction ordering",
             "input_ledger": [original], "proposed_correction": correction,
             "output_ledger": ledger, "outcome": "accepted",
             "required": "If the contract says later, require a strictly later correction timestamp."},
        ],
        "limits": [
            "These are synthetic inputs to a draft research contract, not evidence of natural production occurrences.",
            "The source codec and calendar are test adapters; declared clocks do not establish actual vendor availability.",
            "This pre-seal challenge is not acceptance of the subsequently repaired candidate.",
        ],
    }
    destination = HERE / "EVIDENCE.json"
    destination.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "findings": len(result["findings"]),
                      "result_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
