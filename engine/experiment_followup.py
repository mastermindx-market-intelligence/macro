"""Pure follow-up projection shared by the registry and admin consumer.

No storage, scheduling, grading, promotion or dispatch. A due date is not a result.
"""
from __future__ import annotations
from datetime import date

SCHEMA = "experiment_followup.v1"
CONCLUDED = frozenset({"validated", "proven", "gate_open", "no_go", "closed",
                      "closed_no_go", "complete", "completed", "shipped", "retired",
                      "cancelled", "rejected", "decided", "confirmed", "frozen-historical"})
READERS = frozenset({"observed", "unavailable", "unwired", "error", "legacy_unknown"})


def project_followup(record: dict, today: date) -> dict:
    """Recompute reminder timing without converting legacy ready into evidence."""
    raw = record.get("come_back_on")
    try:
        due = date.fromisoformat(raw) if isinstance(raw, str) else None
    except ValueError:
        due = None
    days = (due - today).days if due is not None else None
    current = record.get("readiness_schema") == SCHEMA
    reader = record.get("reader_status") if current else "legacy_unknown"
    if reader not in READERS:
        reader = "legacy_unknown"
    result = current and reader == "observed" and record.get("result_ready") is True
    closed = str(record.get("status") or "").strip().lower() in CONCLUDED
    review_due = days is not None and days <= 0 and not closed
    reason = ("reader_result" if result else "closed" if closed else
              "review_due" if review_due else "scheduled" if days is not None else "unscheduled")
    return {**record, "readiness_schema": SCHEMA, "reader_status": reader,
            "days_until": days, "result_ready": result, "ready": result,
            "review_due": review_due, "attention_required": result or review_due,
            "readiness_reason": reason}


def followup_counts(records: list[dict]) -> dict:
    """The union avoids counting one experiment twice when both reasons apply."""
    results = sum(e.get("result_ready") is True for e in records)
    return {"ready_count": results, "result_ready_count": results,
            "review_due_count": sum(e.get("review_due") is True for e in records),
            "attention_count": sum(e.get("attention_required") is True for e in records),
            "result_status_unknown_count": sum(e.get("reader_status") == "legacy_unknown" for e in records)}
