"""Pure retained-input envelopes for the incumbent Options Lab adapter.

Callers supply already captured bytes through IdentityArtifactRead. This module
does no discovery, acquisition, storage, identity minting, persistence or I/O.
Capture authentication and permission remain the assigning reader's obligation.
These envelopes are known-input selections, never a complete historical catalog,
point-in-time dataset, package reconstruction or runtime-admission receipt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from engine.intelligence_workspace.entity import IdentityArtifactRead, _identity_read
from engine.options_matrix_retention import (
    SnapshotReference,
    _decode_exact_numbers,
    matrix_coordinate_tokens,
    matrix_observed_side_tokens,
    validate_root,
)
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
