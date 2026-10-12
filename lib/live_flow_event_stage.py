"""Pure reader for append-only ``live_flow.event_stage/v1`` receipts.

The stage is an ordered, byte-addressed evidence log.  ``stage_digest`` is
intentionally retained for the episode checkpoint's semantic (reserialised)
digest; it is not a transport receipt.  ``parse_stage_bytes`` is the sole
reader that exposes a raw prefix receipt for FS-5 consumers.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from engine.options_signal_episode import ContractError
from engine.session_digest import ET
from lib import nyse_calendar

EVENT_STAGE_SCHEMA = "live_flow.event_stage/v1"


def _reject_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key {key!r}")
        out[key] = value
    return out


def strict_json_loads(value: bytes | str) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_reject_duplicate_object_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-standard JSON constant {token}")
        ),
    )


def _utc_stamp(value: object, *, field: str, lineno: int) -> tuple[str, datetime]:
    """Accept an aware UTC ISO-8601 value and return its canonical ``...Z`` form."""
    if type(value) is not str or not value:
        raise ContractError(f"invalid {field} at line {lineno}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"invalid {field} at line {lineno}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ContractError(f"{field} is not UTC at line {lineno}")
    canonical = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    # ``+00:00`` is a semantically valid legacy spelling accepted by the
    # incumbent episode reader.  The returned provenance clock is canonical,
    # while the raw receipt hash remains over the untouched input bytes.
    return canonical, parsed


def _validate_context_capture(binding: object, *, lineno: int) -> None:
    if binding is None:
        return
    if not isinstance(binding, dict):
        raise ContractError(f"invalid context capture binding at line {lineno}")
    if binding.get("status") == "prepared":
        if (
            set(binding) != {"status", "request_id", "request_sha256"}
            or not re.fullmatch(
                r"mmoptrequest_[a-f0-9]{64}", str(binding.get("request_id") or "")
            )
            or not re.fullmatch(
                r"[a-f0-9]{64}", str(binding.get("request_sha256") or "")
            )
        ):
            raise ContractError(
                f"invalid prepared context capture binding at line {lineno}"
            )
    elif binding.get("status") == "abstained":
        if set(binding) != {"status", "reason"} or binding.get("reason") not in {
            "capture_not_armed",
            "outside_predeclared_canary",
            "precommit_not_proven",
            "legacy_unbound",
        }:
            raise ContractError(f"invalid context capture abstention at line {lineno}")
    else:
        raise ContractError(f"unknown context capture state at line {lineno}")


def _parse_stage_bytes(
    raw: bytes,
    *,
    expected_session_date: str,
    source_stage_key: str,
    require_receipt_clocks: bool,
) -> list[dict[str, Any]]:
    """Validate complete paired stage records and return each immutable raw receipt.

    ``source_stage_prefix_sha256`` hashes the exact original bytes ending in the
    event's availability newline.  It therefore remains stable when later
    records are appended.  All validation finishes before any result is returned.
    """
    try:
        session = datetime.strptime(expected_session_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ContractError("event-stage key session is invalid") from exc
    if session.isoformat() != expected_session_date or not nyse_calendar.is_session(
        session
    ):
        raise ContractError("event-stage key session is not an NYSE session")
    if source_stage_key != f"live_flow/events/{expected_session_date}.jsonl":
        raise ContractError("event-stage key does not match its declared session")
    if raw and not raw.endswith(b"\n"):
        raise ContractError("dated event stage has a torn final line")
    if not raw:
        raise ContractError("empty dated event stage")

    decisions: dict[str, tuple[dict[str, Any], str, datetime]] = {}
    seen_decisions: set[str] = set()
    paired: list[dict[str, Any]] = []
    # Incremental state makes each availability receipt O(its own line), rather
    # than copying an ever-growing prefix for every staged event.
    prefix_hasher = hashlib.sha256()
    for lineno, line in enumerate(raw.splitlines(keepends=True), start=1):
        prefix_hasher.update(line)
        try:
            record = strict_json_loads(line)
        except Exception as exc:  # noqa: BLE001
            raise ContractError(
                f"dated event stage malformed at line {lineno}"
            ) from exc
        if not isinstance(record, dict) or record.get("schema") != EVENT_STAGE_SCHEMA:
            raise ContractError(f"wrong dated event-stage schema at line {lineno}")
        event_id = record.get("event_id")
        if type(event_id) is not str or not event_id or event_id != event_id.strip():
            raise ContractError(f"invalid event id at line {lineno}")
        if record.get("kind") == "decision":
            if set(record) != {"schema", "kind", "event_id", "event"}:
                raise ContractError(f"invalid decision receipt shape at line {lineno}")
            if event_id in seen_decisions:
                raise ContractError(f"duplicate staged decision {event_id}")
            event = record.get("event")
            if not isinstance(event, dict) or event.get("id") != event_id:
                raise ContractError(f"invalid decision receipt at line {lineno}")
            if {
                "available_at",
                "published_at",
                "source_snapshot_asof",
                "anchor_strategy",
            }.intersection(event):
                raise ContractError(
                    f"decision receipt contains non-durable fields at line {lineno}"
                )
            if require_receipt_clocks:
                _event_ts, event_dt = _utc_stamp(
                    event.get("ts"), field="event timestamp", lineno=lineno
                )
                _observed, observed_dt = _utc_stamp(
                    event.get("observed_at"), field="observed_at", lineno=lineno
                )
                decision_at, decision_dt = _utc_stamp(
                    event.get("decision_at"), field="decision_at", lineno=lineno
                )
                if not (event_dt <= observed_dt <= decision_dt):
                    raise ContractError(
                        f"decision causal clocks are out of order at line {lineno}"
                    )
                if any(
                    value.astimezone(ET).date().isoformat() != expected_session_date
                    for value in (event_dt, observed_dt, decision_dt)
                ):
                    raise ContractError(
                        f"event-stage key/session mismatch at line {lineno}"
                    )
            else:
                try:
                    event_dt = datetime.fromisoformat(
                        str(event.get("ts") or "").replace("Z", "+00:00")
                    )
                except (TypeError, ValueError) as exc:
                    raise ContractError(
                        f"invalid event timestamp at line {lineno}"
                    ) from exc
                if event_dt.tzinfo is None:
                    raise ContractError(
                        f"event timestamp lacks timezone at line {lineno}"
                    )
                event_session = event_dt.astimezone(ET).date().isoformat()
                if event_session != expected_session_date:
                    raise ContractError(
                        f"event-stage key/session mismatch at line {lineno}: "
                        f"key={expected_session_date} event={event_session}"
                    )
                decision_at = ""
                decision_dt = event_dt
            decisions[event_id] = (event, decision_at, decision_dt)
            seen_decisions.add(event_id)
        elif record.get("kind") == "availability":
            if set(record) not in (
                {"schema", "kind", "event_id", "available_at"},
                {"schema", "kind", "event_id", "available_at", "context_capture"},
            ):
                raise ContractError(
                    f"invalid availability receipt shape at line {lineno}"
                )
            if event_id not in decisions:
                raise ContractError(
                    f"availability receipt precedes its decision at line {lineno}"
                )
            _validate_context_capture(record.get("context_capture"), lineno=lineno)
            if require_receipt_clocks:
                available_at, available_dt = _utc_stamp(
                    record.get("available_at"), field="available_at", lineno=lineno
                )
            else:
                available_at = str(record.get("available_at") or "")
                if not available_at:
                    raise ContractError(f"invalid availability receipt at line {lineno}")
                available_dt = None
            event, decision_at, decision_dt = decisions.pop(event_id)
            if require_receipt_clocks and (
                available_dt < decision_dt
                or available_dt.astimezone(ET).date().isoformat()
                != expected_session_date
            ):
                raise ContractError(
                    f"availability clock violates stage session/order at line {lineno}"
                )
            enriched = dict(event)
            enriched.update(
                {
                    "available_at": available_at,
                    "published_at": None,
                    "source_snapshot_asof": available_at,
                    "anchor_strategy": "durable_available_at",
                }
            )
            paired.append(
                {
                    "event": enriched,
                    "decision_at": decision_at,
                    "available_at": available_at,
                    "source_stage_key": source_stage_key,
                    "source_stage_schema": EVENT_STAGE_SCHEMA,
                    "source_stage_prefix_records": lineno,
                    "source_stage_prefix_sha256": prefix_hasher.hexdigest(),
                }
            )
        else:
            raise ContractError(f"unknown event-stage receipt at line {lineno}")
    if decisions:
        raise ContractError(
            f"decision receipts lack durable availability: {sorted(decisions)}"
        )
    return paired


def parse_stage_bytes(
    raw: bytes, *, expected_session_date: str, source_stage_key: str
) -> list[dict[str, Any]]:
    """Validate raw FS-5 receipts and return immutable original-byte provenance."""
    return _parse_stage_bytes(
        raw,
        expected_session_date=expected_session_date,
        source_stage_key=source_stage_key,
        require_receipt_clocks=True,
    )


def events_from_records(
    records: list[dict[str, Any]], *, expected_session_date: str
) -> list[dict[str, Any]]:
    """Compatibility adapter for episode callers with decoded JSON rows.

    This retains their historical semantic validation and output; it deliberately
    does not claim an original-byte receipt.
    """
    try:
        raw = b"".join(
            json.dumps(
                row, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
            + b"\n"
            for row in records
        )
    except (TypeError, ValueError) as exc:
        raise ContractError("dated event stage contains non-finite JSON") from exc
    parsed = _parse_stage_bytes(
        raw,
        expected_session_date=expected_session_date,
        source_stage_key=f"live_flow/events/{expected_session_date}.jsonl",
        require_receipt_clocks=False,
    )
    # Preserve the episode builder's existing decoded-record semantics: it has
    # historically retained the exact valid availability spelling from the
    # record.  FS-5 consumers use ``parse_stage_bytes`` and receive canonical
    # clocks plus the original-byte digest instead.
    original_available = {
        row.get("event_id"): str(row.get("available_at") or "")
        for row in records
        if isinstance(row, dict) and row.get("kind") == "availability"
    }
    events: list[dict[str, Any]] = []
    for item in parsed:
        event = dict(item["event"])
        stamp = original_available[event["id"]]
        event["available_at"] = stamp
        event["source_snapshot_asof"] = stamp
        events.append(event)
    return events


def stage_digest(records: list[dict[str, Any]], count: int | None = None) -> str:
    """Existing semantic checkpoint digest; not an original-byte stage receipt."""
    subset = records if count is None else records[:count]
    try:
        raw = b"".join(
            json.dumps(
                row, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
            + b"\n"
            for row in subset
        )
    except (TypeError, ValueError) as exc:
        raise ContractError("dated event stage contains non-finite JSON") from exc
    return hashlib.sha256(raw).hexdigest()
