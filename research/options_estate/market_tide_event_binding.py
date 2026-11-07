"""Read-only research consumer of documented advance notices.

Uses the existing calendar constructor and Data OS time semantics. It does not
fetch data, create an event store, resolve a canonical revision chain, assert
schedule completeness, or qualify a C1 model. A notice is a documented PLAN,
not proof that the plan remained unchanged or that our system saw it then.

Repository invocation:
  python -m research.options_estate.market_tide_event_binding \
    --input reviewed_notices.json --decision-at OFFSET_TIMESTAMP \
    --window-end OFFSET_TIMESTAMP
Only supplied JSON is read; only the resulting research packet goes to stdout.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from engine.event_calendar import _event
from lib.dataos.temporal import TemporalProfile, as_of_filter, utc

_TYPES = ("CPI", "NFP", "FOMC")
_ET = ZoneInfo("America/New_York")
_REQUIRED_TEXT = ("notice_id", "event_ref", "type", "event_date", "source_ref", "source_locator")


def _validate(row: Mapping[str, Any]) -> None:
    for key in _REQUIRED_TEXT:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"missing or invalid {key}")
    if row["type"] not in _TYPES:
        raise ValueError("unsupported event type")
    event_date = date.fromisoformat(row["event_date"])
    if event_date.isoformat() != row["event_date"]:
        raise ValueError("event date must use YYYY-MM-DD")
    if row.get("precision") not in ("instant", "date"):
        raise ValueError("unsupported event precision")
    published = utc(row["published_at"])
    if row.get("ingested_at") is not None:
        utc(row["ingested_at"])
    if row["precision"] == "date":
        if row.get("event_at") is not None:
            raise ValueError("date-only evidence cannot carry a fabricated event instant")
        if published.astimezone(_ET).date() >= event_date:
            raise ValueError("date-only notice is not demonstrably earlier")
    else:
        event_at = utc(row.get("event_at"))
        if event_at.astimezone(_ET).date() != event_date:
            raise ValueError("instant and New York event date disagree")
        if published >= event_at:
            raise ValueError("publication is not earlier than event")
    ref = row.get("reference_period")
    if ref is not None and (not isinstance(ref, str) or not ref.strip()):
        raise ValueError("invalid reference period")


def bind_notices(notices: Sequence[Mapping[str, Any]], *, decision_at: str,
                 window_end: str) -> dict[str, Any]:
    """Project known documentary claims into owner-shaped context rows.

    All C1 feature flags remain null: this bounded consumer has no evidence that
    schedule updates and negative-event coverage are complete. It deliberately
    has no caller switch to turn that unresolved condition into qualification.
    Multiple visible versions of one event are surfaced for the existing source
    owner to resolve, rather than introducing another revision-resolution plane.
    """
    decision, end = utc(decision_at), utc(window_end)
    if end <= decision:
        raise ValueError("window_end must be after decision_at")
    if isinstance(notices, (str, bytes)) or not isinstance(notices, Sequence):
        raise ValueError("notices must be a sequence of mappings")
    rows = copy.deepcopy(list(notices))
    excluded: list[dict[str, Any]] = []
    visible: list[dict[str, Any]] = []
    seen: dict[str, dict] = {}
    conflicting_ids: set[str] = set()
    conflicting_events: set[str] = set()
    duplicates = 0

    def reject(row: Any, reason: str) -> None:
        excluded.append({"notice_id": row.get("notice_id") if isinstance(row, Mapping) else None,
                         "reason": reason})

    for row in rows:
        if not isinstance(row, Mapping):
            reject(row, "invalid_notice"); continue
        if row.get("evidence_role") != "advance_schedule":
            reject(row, "not_advance_schedule"); continue
        if row.get("published_at") is None:
            reject(row, "publication_clock_unavailable"); continue
        try:
            # Filter before version grouping: a later correction cannot rewrite
            # what was publicly documented at this historical origin.
            if not as_of_filter([row], decision, TemporalProfile.EVENT):
                reject(row, "not_public_at_decision"); continue
            _validate(row)
        except (ValueError, TypeError, KeyError):
            reject(row, "invalid_notice"); continue
        identity = row["notice_id"]
        if identity in seen:
            if dict(row) == seen[identity]:
                duplicates += 1
            else:
                conflicting_ids.add(identity)
                # A conflicting identity contaminates every event it references.
                # Dropping just that notice could resurrect an older plan.
                conflicting_events.update((seen[identity]["event_ref"], row["event_ref"]))
            continue
        seen[identity] = dict(row)

    for identity, row in seen.items():
        if identity in conflicting_ids:
            reject(row, "conflicting_notice_id")
        else:
            visible.append(row)
    by_event: dict[str, list[dict]] = defaultdict(list)
    for row in visible:
        by_event[row["event_ref"]].append(row)
    projected: list[dict[str, Any]] = []
    for event_ref, versions in by_event.items():
        if event_ref in conflicting_events or len(versions) != 1:
            for row in versions: reject(row, "unresolved_notice_versions")
            continue
        row = versions[0]
        # Keep visible cancelled versions in the group above: dropping them
        # earlier would resurrect the older active plan. No resolver is invented.
        if row.get("plan_status") not in ("scheduled", "tentative"):
            reject(row, "not_active_plan"); continue
        d = date.fromisoformat(row["event_date"])
        instant = utc(row["event_at"]) if row["precision"] == "instant" else None
        if instant is not None:
            in_window = decision < instant <= end
            if not in_window:
                reject(row, "outside_window"); continue
            time_et = instant.astimezone(_ET).strftime("%H:%M")
        else:
            if not decision.astimezone(_ET).date() <= d <= end.astimezone(_ET).date():
                reject(row, "outside_window"); continue
            in_window, time_et = None, ""
        ev = _event(row["type"], d, time_et=time_et, source="documented_advance_notice")
        ev["research_evidence"] = {
            "notice_id": row["notice_id"], "event_ref": event_ref,
            "reference_period": row.get("reference_period"),
            "published_at": utc(row["published_at"]).isoformat(),
            "ingested_at": row.get("ingested_at"),
            "retrieved_on": row.get("retrieved_on"),
            "event_at": instant.isoformat() if instant is not None else None,
            "precision": row["precision"], "plan_status": row["plan_status"],
            "source_ref": row["source_ref"],
            "source_locator": row["source_locator"],
            "raw_document_sha256": row.get("raw_document_sha256"),
            "documented_plan_in_window": in_window,
            "updates_complete": None,
        }
        projected.append(ev)
    projected.sort(key=lambda ev: (ev["date"], ev["time_et"] == "", ev["time_et"], ev["type"], ev["research_evidence"]["notice_id"]))
    excluded.sort(key=lambda item: (str(item["notice_id"]), item["reason"]))
    return {
        "research_only": True, "knowledge_basis": "publisher_documentary",
        "decision_at": decision.isoformat(), "window_end": end.isoformat(),
        "source_row_count": len(rows), "duplicate_rows": duplicates,
        "events": projected, "excluded": excluded,
        "ordering": "date_then_known_time_unknown_times_last_not_actual_event_sequence",
        "exclusion_counts": dict(sorted(Counter(item["reason"] for item in excluded).items())),
        "c1_event_features": {"E_" + kind: None for kind in _TYPES},
        "primary_cohort_eligible": False,
        "eligibility_reason": "schedule_update_and_negative_coverage_unverified",
        "system_replay": False, "can_publish_forecast": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--decision-at", required=True)
    parser.add_argument("--window-end", required=True)
    args = parser.parse_args()
    try:
        packet = json.loads(args.input.read_text(encoding="utf-8"))
        out = bind_notices(packet["notices"], decision_at=args.decision_at, window_end=args.window_end)
        print(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Event evidence unavailable: {exc}\n")


if __name__ == "__main__":
    main()
