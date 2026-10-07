"""Decode retained Terminal minutes using the existing research input owner.

The producer's HTTP receipt is provenance, never Radar availability. Only an
actual bounded owner file read can supply known_at. Serialized read receipts
belong in the existing RS input bundle; this module creates no persistent ledger,
selects no winning revision, and grants no admission or trading authority.

Receipt hashes detect inconsistent bytes/bindings. They are not signatures or
remote attestations: the caller remains responsible for custody of owner-created
receipts. Old receipts bind immutable capture prefixes; the complete historical
file hash is diagnostic and cannot be reconstructed from a later display file.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine.entry_radar.contracts import AUTHORITY_BLOCK
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError

CAPTURE_SCHEMA = "mastermind.intraday_minute_capture.v1"
READ_RECEIPT_SCHEMA = "mastermind.entry_radar.terminal_minute_read.v1"
DECODE_SCHEMA = "mastermind.entry_radar.terminal_minute_observations.v1"
OBSERVER_ID = "terminal.backfill_intraday"
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_CAPTURES = 4096
MAX_READ_RECEIPTS = 8192
MAX_PAGES = 16
MAX_PAGE_BYTES = 8 * 1024 * 1024
ZERO_SHA256 = "0" * 64
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_CAPTURE_KEYS = {
    "sequence", "capture_id", "previous_capture_sha256", "payload_sha256",
    "payload", "capture_sha256",
}
_RECEIPT_KEYS = {
    "schema", "read_id", "reader_identity", "read_method", "file_sha256",
    "file_bytes", "capture_observer_id", "capture_sequence",
    "capture_prefix_sha256", "read_started_at_utc_ns",
    "read_completed_at_utc_ns", "receipt_sha256",
}
_COUNTS = {
    "rows_received", "finalized_rows", "forming_skipped",
    "unchanged_suppressed", "observations_retained",
}


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise InputContractError("capture/receipt must be canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() \
            or len(value) > 256:
        raise InputContractError(f"{name} must be an explicit nonempty owner label")
    return value


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise InputContractError(f"{name} must be an integer >= {minimum}")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputContractError("duplicate JSON object key")
        result[key] = value
    return result


def _json(text: str | bytes) -> Any:
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: _invalid_json_constant())
    except (UnicodeError, TypeError, ValueError, RecursionError) as exc:
        raise InputContractError("malformed UTF-8 capture/receipt JSON") from exc


def _invalid_json_constant() -> None:
    raise InputContractError("non-finite JSON constant")


def _known_at(nanoseconds: int) -> str:
    """Ceil, never truncate, to the existing selector's microsecond precision."""
    try:
        instant = _EPOCH + timedelta(microseconds=(nanoseconds + 999) // 1000)
    except (OverflowError, TypeError) as exc:
        raise InputContractError("owner read clock is outside supported UTC range") from exc
    return instant.isoformat().replace("+00:00", "Z")


def _cutoff_ns(value: str) -> int:
    if value is None:
        raise InputContractError("an explicit non-null decision cutoff is required")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("naive cutoff")
        delta = instant.astimezone(timezone.utc) - _EPOCH
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise InputContractError("cutoff must be an aware ISO-8601 instant") from exc
    return ((delta.days * 86400 + delta.seconds) * 1_000_000
            + delta.microseconds) * 1000


def _captures(raw: bytes) -> list[dict[str, Any]]:
    """Verify structural seals without parsing future event/value semantics."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FILE_BYTES:
        raise InputContractError("snapshot is empty or exceeds the bounded file size")
    document = _json(raw)
    envelope = document.get("minute_capture") if isinstance(document, dict) else None
    if not isinstance(envelope, dict) or envelope.get("schema") != CAPTURE_SCHEMA:
        raise InputContractError("versioned minute_capture is absent or unsupported")
    if envelope.get("observer_id") != OBSERVER_ID:
        raise InputContractError("unrecognized capture observer")
    authority = envelope.get("authority")
    if not isinstance(authority, dict) or set(authority) != {
        "research_admitted", "trading_authority"
    } or any(value is not False for value in authority.values()):
        raise InputContractError("capture may not assert research or trading authority")
    records = envelope.get("captures")
    if not isinstance(records, list) or len(records) > MAX_CAPTURES:
        raise InputContractError("capture sequence is absent or exceeds its bound")
    previous, seen = ZERO_SHA256, set()
    for sequence, record in enumerate(records, 1):
        if not isinstance(record, dict) or set(record) != _CAPTURE_KEYS:
            raise InputContractError("invalid sealed capture record")
        if type(record["sequence"]) is not int or record["sequence"] != sequence:
            raise InputContractError("capture sequence must be contiguous and one-based")
        identifier = record["capture_id"]
        if not isinstance(identifier, str) or re.fullmatch(r"[0-9a-f]{32}", identifier) is None \
                or identifier in seen:
            raise InputContractError("capture ID is invalid or reused")
        seen.add(identifier)
        if record["previous_capture_sha256"] != previous:
            raise InputContractError("capture prefix chain mismatch")
        if not isinstance(record["payload"], dict) or not _sha(record["payload_sha256"]) \
                or _digest(record["payload"]) != record["payload_sha256"]:
            raise InputContractError("capture payload seal mismatch")
        sealed = {key: value for key, value in record.items() if key != "capture_sha256"}
        if not _sha(record["capture_sha256"]) or _digest(sealed) != record["capture_sha256"]:
            raise InputContractError("capture record seal mismatch")
        previous = record["capture_sha256"]
    if envelope.get("prefix_sha256") != previous:
        raise InputContractError("capture envelope prefix seal mismatch")
    return records


@dataclass(frozen=True)
class TerminalMinuteSnapshot:
    """Exact one-read bytes and their immutable, serializable owner receipt."""

    raw_bytes: bytes
    receipt_json: str

    @property
    def receipt(self) -> dict[str, Any]:
        """Return a copy for the existing input bundle, never a mutable alias."""
        return _json(self.receipt_json)


def read_terminal_minute_snapshot(
    path: str | Path, *, reader_identity: str, max_bytes: int = MAX_FILE_BYTES,
) -> TerminalMinuteSnapshot:
    """Read one descriptor once, hash those bytes, and measure read completion.

    The public API has no caller-supplied timestamp or backdating option. Tests
    may patch the internal clock. This is read-only: neither the file nor a
    receipt sidecar is written. OSError preserves missing/unreadable-file errors.
    """
    reader_identity = _identifier(reader_identity, "reader_identity")
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_FILE_BYTES:
        raise InputContractError("max_bytes must be within the bounded file limit")
    started = time.time_ns()
    with Path(path).open("rb") as handle:
        raw = handle.read(max_bytes + 1)
        completed = time.time_ns()
    if len(raw) > max_bytes:
        raise InputContractError("minute snapshot exceeds max_bytes")
    _integer(started, "read start", 1)
    _integer(completed, "read completion", started)
    _known_at(completed)
    records = _captures(raw)
    receipt = {
        "schema": READ_RECEIPT_SCHEMA,
        "read_id": uuid.uuid4().hex,
        "reader_identity": reader_identity,
        "read_method": "single_open_bounded_read",
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "file_bytes": len(raw),
        "capture_observer_id": OBSERVER_ID,
        "capture_sequence": len(records),
        "capture_prefix_sha256": records[-1]["capture_sha256"] if records else ZERO_SHA256,
        "read_started_at_utc_ns": started,
        "read_completed_at_utc_ns": completed,
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return TerminalMinuteSnapshot(raw, _canonical(receipt))


def _receipt(
    value: Mapping[str, Any], records: list[dict[str, Any]], reader_identity: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
        raise InputContractError("invalid owner read receipt")
    result = dict(value)
    if result["schema"] != READ_RECEIPT_SCHEMA \
            or result["read_method"] != "single_open_bounded_read" \
            or result["reader_identity"] != reader_identity \
            or result["capture_observer_id"] != OBSERVER_ID:
        raise InputContractError("owner read receipt identity/method mismatch")
    if not isinstance(result["read_id"], str) \
            or re.fullmatch(r"[0-9a-f]{32}", result["read_id"]) is None:
        raise InputContractError("invalid owner read ID")
    seal = {key: item for key, item in result.items() if key != "receipt_sha256"}
    if not _sha(result["receipt_sha256"]) or _digest(seal) != result["receipt_sha256"]:
        raise InputContractError("owner read receipt seal mismatch")
    if not _sha(result["file_sha256"]) \
            or _integer(result["file_bytes"], "receipt file bytes", 1) > MAX_FILE_BYTES:
        raise InputContractError("invalid owner file byte binding")
    sequence = _integer(result["capture_sequence"], "receipt prefix sequence")
    if sequence > len(records):
        raise InputContractError("read receipt covers a prefix absent from this snapshot")
    prefix = records[sequence - 1]["capture_sha256"] if sequence else ZERO_SHA256
    if result["capture_prefix_sha256"] != prefix:
        raise InputContractError("read receipt capture prefix mismatch")
    started = _integer(result["read_started_at_utc_ns"], "receipt read start", 1)
    completed = _integer(result["read_completed_at_utc_ns"], "receipt read completion", started)
    _known_at(completed)
    return result


def _coverage(
    records: list[dict[str, Any]], receipts: Sequence[Mapping[str, Any]],
    reader_identity: str, own: dict[str, Any], cutoff_ns: int,
) -> list[dict[str, Any] | None]:
    if not isinstance(receipts, (list, tuple)) or len(receipts) > MAX_READ_RECEIPTS:
        raise InputContractError("owner receipt list is absent or exceeds its bound")
    by_sequence: dict[int, dict[str, Any]] = {}
    by_id = {own["read_id"]: own}
    for value in receipts:
        receipt = _receipt(value, records, reader_identity)
        previous = by_id.get(receipt["read_id"])
        if previous is not None and previous != receipt:
            raise InputContractError("conflicting payload under an owner read ID")
        by_id[receipt["read_id"]] = receipt
        completed = receipt["read_completed_at_utc_ns"]
        if ((completed + 999) // 1000) * 1000 > cutoff_ns:
            continue
        sequence = receipt["capture_sequence"]
        if sequence not in by_sequence \
                or completed < by_sequence[sequence]["read_completed_at_utc_ns"]:
            by_sequence[sequence] = receipt
    # Suffix minima: one read observes every retained capture in its exact prefix.
    coverage: list[dict[str, Any] | None] = [None] * (len(records) + 1)
    earliest = None
    for sequence in range(len(records), 0, -1):
        candidate = by_sequence.get(sequence)
        if candidate is not None and (earliest is None or
                candidate["read_completed_at_utc_ns"] < earliest["read_completed_at_utc_ns"]):
            earliest = candidate
        coverage[sequence] = earliest
    return coverage


def _eligible_payload(
    record: dict[str, Any], receipt: dict[str, Any], symbol: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = record["payload"]
    if payload.get("symbol") != symbol or payload.get("timeframe") != "1m" \
            or payload.get("source") != "polygon":
        raise InputContractError("capture symbol/source/timeframe mismatch")
    started = _integer(payload.get("started_at_utc_ns"), "capture start", 1)
    completed = _integer(payload.get("completed_at_utc_ns"), "capture completion", started)
    if completed > receipt["read_completed_at_utc_ns"]:
        raise InputContractError("owner receipt precedes capture completion")
    status = payload.get("status")
    if status not in {"complete", "partial", "failed"}:
        raise InputContractError("unknown capture outcome")
    if status != "complete":
        return payload, []
    if payload.get("failure_kind") is not None:
        raise InputContractError("complete capture has a failure kind")
    reference = _integer(payload.get("finality_reference_utc_ns"), "finality reference", 1)
    if reference > completed or type(payload.get("finality_lag_s")) is not int \
            or payload["finality_lag_s"] != 900:
        raise InputContractError("capture finality declaration mismatch")
    request = payload.get("request")
    if not isinstance(request, dict) or request.get("multiplier") != 1 \
            or type(request.get("multiplier")) is not int \
            or request.get("timespan") != "minute" or request.get("adjusted") is not True:
        raise InputContractError("capture is not the declared adjusted one-minute request")
    pages = payload.get("pages")
    observations = payload.get("observations")
    counts = payload.get("counts")
    if not isinstance(pages, list) or not 0 < len(pages) <= MAX_PAGES \
            or not isinstance(observations, list) or not isinstance(counts, dict) \
            or set(counts) != _COUNTS:
        raise InputContractError("complete capture has invalid pages/observations/counts")
    for name in _COUNTS:
        _integer(counts[name], "capture count " + name)
    if counts["observations_retained"] != len(observations) \
            or counts["observations_retained"] + counts["unchanged_suppressed"] != counts["finalized_rows"] \
            or counts["finalized_rows"] + counts["forming_skipped"] != counts["rows_received"]:
        raise InputContractError("capture row accounting mismatch")
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or type(page.get("page_index")) is not int \
                or page["page_index"] != index or page.get("status") not in {"OK", "DELAYED"}:
            raise InputContractError("invalid complete capture page")
        requested = _integer(page.get("request_started_at_utc_ns"), "page request", started)
        received = _integer(page.get("response_received_at_utc_ns"), "page response", requested)
        if received > completed or not _sha(page.get("response_sha256")) \
                or _integer(page.get("response_bytes"), "page bytes", 1) > MAX_PAGE_BYTES:
            raise InputContractError("invalid page response binding")
        for name in ("rows_received", "finalized_rows", "forming_skipped"):
            _integer(page.get(name), "page count " + name)
        if page["finalized_rows"] + page["forming_skipped"] != page["rows_received"]:
            raise InputContractError("page row accounting mismatch")
    if any(sum(page[name] for page in pages) != counts[name]
           for name in ("rows_received", "finalized_rows", "forming_skipped")):
        raise InputContractError("capture/page row accounting mismatch")
    return payload, observations


def decode_terminal_minute_observations(
    snapshot: TerminalMinuteSnapshot,
    read_receipts: Sequence[Mapping[str, Any]],
    *,
    reader_identity: str,
    symbol: str,
    stream: str,
    stream_metadata: Mapping[str, Any] | None = None,
    cutoff: str,
) -> dict[str, Any]:
    """Emit decision-scoped inputs; the existing RS selector resolves revisions.

    An explicit non-null decision cutoff is required. Decode separately for each
    model decision: a later capture must not be parsed while preparing an earlier
    frame. The raw snapshot reader remains independent of any decision cutoff.

    Caller metadata supplies labels from the existing identity/basis owner. This
    decoder neither creates those receipts nor treats the source adjusted flag
    as proof. Missing metadata stays missing. An empty receipt list deliberately
    means unavailable; the snapshot's own receipt is not silently enrolled.

    Every capture read for the first time together has the same known_at. A late
    first read of A/B/A therefore remains a same-clock conflict downstream.
    """
    reader_identity = _identifier(reader_identity, "reader_identity")
    symbol, stream = _identifier(symbol, "symbol"), _identifier(stream, "stream")
    cutoff_ns = _cutoff_ns(cutoff)
    if not isinstance(snapshot, TerminalMinuteSnapshot):
        raise InputContractError("a bounded file-read snapshot is required")
    records = _captures(snapshot.raw_bytes)
    own = _receipt(snapshot.receipt, records, reader_identity)
    expected_prefix = records[-1]["capture_sha256"] if records else ZERO_SHA256
    if own["file_sha256"] != hashlib.sha256(snapshot.raw_bytes).hexdigest() \
            or own["file_bytes"] != len(snapshot.raw_bytes) \
            or own["capture_sequence"] != len(records) \
            or own["capture_prefix_sha256"] != expected_prefix:
        raise InputContractError("snapshot bytes do not match their owner read receipt")
    coverage = _coverage(records, read_receipts, reader_identity, own, cutoff_ns)
    meta = stream_metadata if isinstance(stream_metadata, Mapping) else {}
    basis = meta.get("basis") if isinstance(meta.get("basis"), Mapping) else {}
    security_id, basis_id = meta.get("security_id"), basis.get("basis_id")
    if security_id is not None:
        _identifier(security_id, "owner security_id")
    if basis_id is not None:
        _identifier(basis_id, "owner basis_id")
    minutes = []
    diagnostics: dict[str, Any] = {
        "snapshot_file_sha256": own["file_sha256"], "snapshot_file_bytes": own["file_bytes"],
        "snapshot_prefix_sha256": expected_prefix, "snapshot_capture_count": len(records),
        "captures_without_visible_owner_receipt": 0,
        "visible_capture_outcomes": {"complete": 0, "partial": 0, "failed": 0},
        "complete_captures_with_no_retained_observations": 0,
    }
    for record in records:
        receipt = coverage[record["sequence"]]
        if receipt is None:
            diagnostics["captures_without_visible_owner_receipt"] += 1
            continue
        # Visibility is resolved before event or OHLCV parsing. Later corrupt
        # semantic payloads cannot affect the earlier visible model prefix.
        payload, observations = _eligible_payload(record, receipt, symbol)
        diagnostics["visible_capture_outcomes"][payload["status"]] += 1
        if payload["status"] != "complete":
            continue
        if not observations:
            diagnostics["complete_captures_with_no_retained_observations"] += 1
        seen = set()
        for observation in observations:
            if not isinstance(observation, dict):
                raise InputContractError("invalid retained minute observation")
            page_index = _integer(observation.get("page_index"), "observation page index")
            row_index = _integer(observation.get("row_index"), "observation row index")
            if page_index >= len(payload["pages"]):
                raise InputContractError("observation page is absent")
            page = payload["pages"][page_index]
            if row_index >= page["rows_received"] or (page_index, row_index) in seen:
                raise InputContractError("observation row is absent or duplicated")
            seen.add((page_index, row_index))
            start = _integer(observation.get("event_start_utc_ms"), "event start", 1)
            end = _integer(observation.get("event_end_utc_ms"), "event end", 1)
            raw = observation.get("raw")
            if not isinstance(raw, dict) or not {"t", "o", "h", "l", "c"} <= set(raw) \
                    or not set(raw) <= {"t", "o", "h", "l", "c", "v"} \
                    or type(raw["t"]) is not int or raw["t"] != start \
                    or start % 60000 or end != start + 60000:
                raise InputContractError("retained minute lacks true UTC event identity")
            if end * 1_000_000 > payload["finality_reference_utc_ns"] - 900 * 1_000_000_000 \
                    or end * 1_000_000 > page["response_received_at_utc_ns"]:
                raise InputContractError("retained minute violates the producer finality bound")
            completed = receipt["read_completed_at_utc_ns"]
            row = {
                "stream": stream, "security_id": security_id, "basis_id": basis_id,
                "revision_id": f"{record['capture_id']}:{page_index}:{row_index}",
                "start": _known_at(start * 1_000_000), "end": _known_at(end * 1_000_000),
                "known_at": _known_at(completed),
                "open": raw["o"], "high": raw["h"], "low": raw["l"], "close": raw["c"],
                "volume": raw.get("v"),
                "source_ref": f"terminal-minute-capture:{record['capture_sha256']}:{page_index}:{row_index}",
                "source_observation": {
                    "observer_id": OBSERVER_ID, "capture_id": record["capture_id"],
                    "capture_sequence": record["sequence"],
                    "capture_sha256": record["capture_sha256"],
                    "source_received_at_utc_ns": page["response_received_at_utc_ns"],
                    "source_response_sha256": page["response_sha256"],
                    "owner_reader_identity": reader_identity,
                    "owner_read_completed_at_utc_ns": completed,
                    "request_adjusted": True,
                    "volume_state": "missing" if "v" not in raw else
                                    "null" if raw["v"] is None else "observed",
                },
            }
            row["receipt_sha256"] = _digest(row)
            minutes.append(row)
    return {
        "schema": DECODE_SCHEMA,
        "status": "REVISION_INPUTS_BUILT_NOT_ADMITTED" if minutes else "UNAVAILABLE",
        "minutes": minutes, "diagnostics": diagnostics,
        "unproven_owner_requirements": [
            "stable_security_identity", "price_volume_corporate_action_basis",
            "calendar_and_exceptional_sessions", "complete_pilot_population",
        ],
        "authority": dict(AUTHORITY_BLOCK),
        "scientific_claims": {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"},
        "revision_selection_owner": "engine.entry_radar.replay.rs_pullback_launch_data",
        "detector_registered": False, "outcomes_computed": False,
    }
