"""Pure retained-input envelopes for the incumbent Options Lab adapter.

Callers supply already captured bytes through IdentityArtifactRead. This module
does no discovery, acquisition, storage, identity minting, persistence or I/O.
Capture authentication and permission remain the assigning reader's obligation.
These envelopes are known-input selections, never a complete historical catalog,
point-in-time dataset, package reconstruction or runtime-admission receipt.
"""
from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from engine.intelligence_workspace.entity import IdentityArtifactRead, _identity_read
from engine.options_matrix_retention import (
    SnapshotReference,
    _decode_exact_numbers,
    matrix_coordinate_tokens,
    matrix_observed_side_tokens,
    parse_reference,
    validate_root,
)
from engine.options_occ_contract_terms import _canonical as _canonical_decimal
from lib.dataos.identity import _aware_utc
from lib.live_flow_event_stage import parse_stage_bytes, strict_json_loads

Side = Literal["call", "put"]


@dataclass(frozen=True)
class RetainedMatrixRow:
    expiry: str
    strike: str
    side: Side
    cell_index: int
    # Only supplied own-side metrics. Absent keys, null and numeric zero differ.
    # Shared GEX/VEX/levels remain in document, never allocated to either side.
    metrics: dict[str, Any]


@dataclass(frozen=True)
class RetainedMatrixSelection:
    reference: SnapshotReference
    capture: IdentityArtifactRead
    read_observed_at: datetime
    decision_at: datetime
    expiry: str
    side: Literal["all", "call", "put"]
    rows: tuple[RetainedMatrixRow, ...]
    # Exact-number decoded original document, including ALL supplied metadata.
    # Decimal values must not be reserialized through float. capture.body is the
    # authority for byte identity; document is a detached consumer projection.
    document: dict[str, Any]
    row_status: Literal["supplied_observations", "no_supplied_observations"]
    selection_mode: Literal["known_snapshot_only"] = field(default="known_snapshot_only", init=False)
    # This schema supplies neither an authoritative catalog nor first retention
    # clock. An asof/build/read clock or digest is never promoted into either.
    first_available_at: None = field(default=None, init=False)
    history_order: None = field(default=None, init=False)
    correction_order: None = field(default=None, init=False)
    universe_coverage: None = field(default=None, init=False)
    gap_interpretation: Literal["missing_is_unknown"] = field(default="missing_is_unknown", init=False)


@dataclass(frozen=True)
class RetainedEventSelection:
    session: str
    root: str
    source_stage_key: str
    capture: IdentityArtifactRead
    read_observed_at: datetime
    decision_at: datetime
    # Incumbent raw-prefix receipts in ledger order, NOT market-time order.
    # Each event retains original event/observed/decision/OI fields alongside
    # the parser's separately derived durable-availability receipt.
    records: tuple[dict[str, Any], ...]
    population: Literal["individual_aggregate_events"] = field(default="individual_aggregate_events", init=False)
    package_support: Literal["no_sourced_membership"] = field(default="no_sourced_membership", init=False)
    universe_coverage: None = field(default=None, init=False)
    correction_order: None = field(default=None, init=False)


def _date(value: str) -> str:
    if type(value) is not str or date.fromisoformat(value).isoformat() != value:
        raise ValueError("selection requires an exact Gregorian date")
    return value


def select_retained_matrix(
    reference: SnapshotReference,
    capture: IdentityArtifactRead,
    *,
    decision_at: datetime | str,
    expiry: str,
    side: Literal["all", "call", "put"],
) -> RetainedMatrixSelection:
    """Select supplied contract-side rows from ONE explicit immutable snapshot.

    No mutable-head fallback or calendar expansion. Membership uses the incumbent
    own-side nonnull OI/volume rule, including zero. A null/absent side is not a
    known zero; a missing expiry returns an explicitly empty observed population.
    Supplied coverage/correction/gap/availability metadata stays untouched in
    document. This function does not certify its semantics or invent order.
    """
    cutoff = _aware_utc(decision_at, "decision_at")
    observed = _identity_read(capture, cutoff)
    expiry = _date(expiry)
    if side not in ("all", "call", "put"):
        raise ValueError("selection side must be all, call or put")
    # Both helpers bind exact reference/length/digest/root/session and reject
    # duplicate or invalid coordinates/counts, including outside the view.
    coordinates = matrix_coordinate_tokens(reference, capture.body)
    observed_sides = set(matrix_observed_side_tokens(reference, capture.body))
    document = _decode_exact_numbers(capture.body)
    rows = []
    for index, ((cell_expiry, strike), cell) in enumerate(zip(coordinates, document["cells"], strict=True)):
        if cell_expiry != expiry:
            continue
        for own_side in ("call", "put"):
            if side not in ("all", own_side) or (expiry, strike, own_side) not in observed_sides:
                continue
            metrics = {}
            for source, target in ((f"{own_side}_oi", "open_interest"), (f"{own_side}_vol", "volume")):
                if source in cell:
                    metrics[target] = cell[source]
            for source in ("delta_oi", "unusual"):
                if isinstance(cell.get(source), dict) and own_side in cell[source]:
                    metrics[source] = cell[source][own_side]
            rows.append(RetainedMatrixRow(expiry, strike, own_side, index, metrics))
    return RetainedMatrixSelection(reference, capture, observed, cutoff, expiry, side,
                                   tuple(rows), document,
                                   "supplied_observations" if rows else "no_supplied_observations")


def select_retained_events(
    capture: IdentityArtifactRead,
    *,
    session: str,
    root: str,
    decision_at: datetime | str,
    event_ids: tuple[str, ...] | None = None,
) -> RetainedEventSelection:
    """Select an exact root/optional known IDs from the captured dated stage.

    Reuses the sole raw-byte stage reader, including complete paired receipts,
    causal clock/session validation and append-stable original-prefix digests.
    No dates-index lookup, feed fallback, grouping, multiplier inference or sort.
    Input capture time is NOT event receipt time or durable availability.
    Package-looking fields are retained as source payload, never admitted as
    leg/member/quantity/deliverable/correction evidence by this contract.
    """
    cutoff = _aware_utc(decision_at, "decision_at")
    observed = _identity_read(capture, cutoff)
    root = validate_root(root)
    session = _date(session)
    key = f"live_flow/events/{session}.jsonl"
    records = parse_stage_bytes(capture.body, expected_session_date=session, source_stage_key=key)
    lines = capture.body.splitlines(keepends=True)
    for item in records:
        # The incumbent parser canonicalizes to datetime microseconds. Retain
        # the exact validated availability line and spelling for downstream
        # provenance, and use the shared conservative clock parser on that
        # original spelling so nanoseconds cannot round behind read_at.
        receipt_line = lines[item["source_stage_prefix_records"] - 1]
        source_available = strict_json_loads(receipt_line)["available_at"]
        if _aware_utc(source_available, "known_at") > observed:
            raise ValueError("durable availability is after captured read")
        item["source_available_at"] = source_available
        item["source_availability_receipt"] = receipt_line
    selected = [item for item in records if item["event"].get("root") == root]
    if event_ids is not None:
        if (type(event_ids) is not tuple or not event_ids or len(event_ids) > 200_000
                or any(type(i) is not str or not i or i != i.strip() for i in event_ids)
                or len(set(event_ids)) != len(event_ids)):
            raise ValueError("event IDs must be a nonempty bounded unique tuple")
        wanted = set(event_ids)
        selected = [item for item in selected if item["event"]["id"] in wanted]
        if {item["event"]["id"] for item in selected} != wanted:
            raise ValueError("selected event is absent from captured root/session")
    return RetainedEventSelection(session, root, key, capture, observed, cutoff, tuple(selected))


WIRE_SCHEMA = "options.retained_selection.wire/v1"
MAX_SELECTION_WIRE_BYTES = 64 * 1024 * 1024
MAX_SELECTION_WIRE_NODES = 2_000_000
MAX_SELECTION_SOURCE_DEPTH = 24
MAX_SELECTION_WIRE_DEPTH = 64
MAX_SELECTION_DECIMAL_CHARS = 128
_MAX_CAPTURE_BYTES = 16 * 1024 * 1024  # incumbent IdentityArtifactRead bound


def _exact_wire_tree(value: Any, *, depth: int = 0, budget: list[int] | None = None) -> Any:
    """A tagged lossless JSON tree; source strings never masquerade as numbers.

    Objects and arrays are tagged too, so a supplied {"decimal":"12"} is an
    object containing a string, not an admitted decimal token. No float input.
    """
    if budget is None:
        budget = [MAX_SELECTION_WIRE_NODES]
    budget[0] -= 1
    if budget[0] < 0 or depth > MAX_SELECTION_SOURCE_DEPTH:
        raise ValueError("retained source projection exceeds tree bound")
    if value is None or type(value) in (bool, str):
        return value
    if isinstance(value, Decimal) or type(value) is int:
        decimal = value if isinstance(value, Decimal) else Decimal(value)
        if not decimal.is_finite():
            raise ValueError("wire decimal must be finite")
        if decimal != 0:
            sign, digits, exponent = decimal.as_tuple()
            # Bound before calling the incumbent plain formatter: no huge
            # exponent allocation, context normalization or float roundtrip.
            width = max(len(digits) + exponent, 1) + max(-exponent, 0) + sign + (exponent < 0)
            if width > MAX_SELECTION_DECIMAL_CHARS:
                raise ValueError("wire decimal exceeds canonical token bound")
        return {"decimal": _canonical_decimal(decimal)}
    if type(value) is list:
        return {"array": [_exact_wire_tree(item, depth=depth + 1, budget=budget) for item in value]}
    if type(value) is dict and all(type(key) is str for key in value):
        return {"object": {key: _exact_wire_tree(item, depth=depth + 1, budget=budget)
                           for key, item in value.items()}}
    raise ValueError("unsupported retained source value; floats are not a wire source")


def _bounded_wire_tree(value: Any) -> None:
    # Iterative even for malformed input; do not recurse on an untrusted wire.
    pending = [(value, 0)]
    count = 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_SELECTION_WIRE_NODES or depth > MAX_SELECTION_WIRE_DEPTH:
            raise ValueError("selection wire exceeds tree bound")
        if type(node) is dict:
            pending.extend((item, depth + 1) for item in node.values())
        elif type(node) is list:
            pending.extend((item, depth + 1) for item in node)
        elif node is not None and type(node) not in (str, bool, int):
            raise ValueError("wire contains a float or unsupported JSON value")


def _wire_bytes(wire: dict[str, Any]) -> bytes:
    _bounded_wire_tree(wire)
    raw = json.dumps(wire, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_SELECTION_WIRE_BYTES:
        raise ValueError("selection wire exceeds byte bound")
    return raw


def _source_clock(value: datetime | str) -> str:
    return value.isoformat() if isinstance(value, datetime) else value


def _wire_common(kind: str, selection: RetainedMatrixSelection | RetainedEventSelection,
                 decision_at: datetime | str) -> dict[str, Any]:
    capture = selection.capture
    return {
        "schema": WIRE_SCHEMA, "kind": kind,
        "capture": {"encoding": "base64", "body_base64": base64.b64encode(capture.body).decode("ascii"),
                    "sha256": capture.sha256, "byte_length": len(capture.body),
                    "read_at": _source_clock(capture.read_at)},
        # Preserve original cutoff spelling/precision, alongside the incumbent
        # normalized conservative cutoff/read values; none is first availability.
        "decision_at": _source_clock(decision_at),
        "cutoff_utc": selection.decision_at.isoformat(),
        "read_observed_at": selection.read_observed_at.isoformat(),
    }


def encode_retained_matrix(reference: SnapshotReference, capture: IdentityArtifactRead, *,
                           decision_at: datetime | str, expiry: str,
                           side: Literal["all", "call", "put"]) -> bytes:
    """Encode the explicit selected snapshot as bounded lossless UTF-8 JSON."""
    selection = select_retained_matrix(reference, capture, decision_at=decision_at, expiry=expiry, side=side)
    wire = _wire_common("matrix", selection, decision_at)
    wire.update({
        "selector": {"expiry": expiry, "side": side},
        "snapshot": {"root": reference.root, "session": reference.session, "sha256": reference.sha256,
                     "byte_length": reference.byte_length, "version_ref": reference.version_ref, "key": reference.key},
        "rows": [{"expiry": row.expiry, "strike": row.strike, "side": row.side, "cell_index": row.cell_index,
                  "metrics": {key: _exact_wire_tree(value) for key, value in row.metrics.items()}}
                 for row in selection.rows],
        "document": _exact_wire_tree(selection.document),
        "state": {"selection_mode": selection.selection_mode, "row_status": selection.row_status,
                  "first_available_at": None, "history_order": None, "correction_order": None,
                  "universe_coverage": None, "gap_interpretation": selection.gap_interpretation},
    })
    return _wire_bytes(wire)


def encode_retained_events(capture: IdentityArtifactRead, *, session: str, root: str,
                           decision_at: datetime | str, event_ids: tuple[str, ...] | None = None) -> bytes:
    """Encode validated stage receipts without using the reader's float payload."""
    selection = select_retained_events(capture, session=session, root=root,
                                       decision_at=decision_at, event_ids=event_ids)
    # The incumbent reader validates original bytes and provenance, but its JSON
    # decoder uses floats. Read the *same already validated decision bytes* with
    # the incumbent exact-number decoder before projecting numeric source facts.
    decisions = {}
    for line in capture.body.splitlines(keepends=True):
        record = _decode_exact_numbers(line)
        if record["kind"] == "decision":
            decisions[record["event_id"]] = record["event"]
    rows = []
    for item in selection.records:
        row = {key: value for key, value in item.items() if key not in ("event", "source_availability_receipt")}
        row["event"] = _exact_wire_tree(decisions[item["event"]["id"]])
        row["source_availability_receipt_base64"] = base64.b64encode(item["source_availability_receipt"]).decode("ascii")
        rows.append(row)
    wire = _wire_common("events", selection, decision_at)
    wire.update({"selector": {"session": session, "root": root,
                              "event_ids": list(event_ids) if event_ids is not None else None},
                 "source_stage_key": selection.source_stage_key, "records": rows,
                 "state": {"population": selection.population, "package_support": selection.package_support,
                           "universe_coverage": None, "correction_order": None}})
    return _wire_bytes(wire)


def decode_retained_selection_wire(raw: bytes) -> dict[str, Any]:
    """Validate a complete wire, reconstructing it from its captured authority.

    Returns JSON-safe values with decimal STRING leaves, never decoded floats or
    new input reads. Byte authentication still belongs to the assigning reader.
    Every redundant row/metadata/clock/state/reference must match the captured
    source projection. Extra fields and type-coercion tricks fail closed.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_SELECTION_WIRE_BYTES:
        raise ValueError("selection wire requires bounded UTF-8 bytes")
    try:
        wire = strict_json_loads(raw.decode("utf-8"))
        _bounded_wire_tree(wire)
        if type(wire) is not dict or wire.get("schema") != WIRE_SCHEMA:
            raise ValueError("unsupported retained selection wire schema")
        source = wire["capture"]
        if type(source) is not dict or set(source) != {"encoding", "body_base64", "sha256", "byte_length", "read_at"}:
            raise ValueError("invalid captured-byte envelope")
        size = source["byte_length"]
        body64 = source["body_base64"]
        if (source["encoding"] != "base64" or type(size) is not int or not 0 < size <= _MAX_CAPTURE_BYTES
                or type(body64) is not str or len(body64) > 4 * ((_MAX_CAPTURE_BYTES + 2) // 3)
                or type(source["read_at"]) is not str or type(wire["decision_at"]) is not str):
            raise ValueError("invalid capture encoding, bound or clock")
        body = base64.b64decode(body64, validate=True)
        if len(body) != size or base64.b64encode(body).decode("ascii") != body64:
            raise ValueError("capture length or noncanonical base64")
        capture = IdentityArtifactRead(body, source["sha256"], source["read_at"])
        selector = wire["selector"]
        if wire["kind"] == "matrix":
            snapshot = wire["snapshot"]
            reference = parse_reference(snapshot["root"], snapshot["version_ref"], snapshot["sha256"])
            expected = encode_retained_matrix(reference, capture, decision_at=wire["decision_at"],
                                               expiry=selector["expiry"], side=selector["side"])
        elif wire["kind"] == "events":
            ids = selector["event_ids"]
            if ids is not None and type(ids) is not list:
                raise ValueError("wire event_ids must be array or null")
            expected = encode_retained_events(capture, session=selector["session"], root=selector["root"],
                                               decision_at=wire["decision_at"], event_ids=tuple(ids) if ids is not None else None)
        else:
            raise ValueError("unsupported retained selection kind")
        # Compare canonical JSON bytes, not Python equality (where True == 1).
        if _wire_bytes(wire) != expected:
            raise ValueError("wire projection differs from captured authority")
        return wire
    except (KeyError, TypeError, AttributeError, UnicodeError, binascii.Error, RecursionError) as exc:
        raise ValueError("malformed retained selection wire") from exc
