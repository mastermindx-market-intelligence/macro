"""Synthetic transport/receipt conformance; no market admission or outcomes."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from engine.entry_radar.replay import terminal_minute_observations as bridge
from engine.entry_radar.replay.rs_pullback_launch_data import (
    INPUT_SCHEMA,
    InputContractError,
    build_input_panel,
)

READER = "entry_radar.rs_pullback.synthetic_owner"
SYMBOL = "AAPL"
SHA = "a" * 64
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def ns(value):
    delta = datetime.fromisoformat(value.replace("Z", "+00:00")) - EPOCH
    return ((delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds) * 1000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def raw_rows():
    start = ns("2026-10-06T13:30:00Z") // 1_000_000
    return [{"t": start + i * 60000, "o": 100, "h": 101, "l": 99,
             "c": 100, "v": 1.5} for i in range(30)]


def envelope():
    return {
        "schema": bridge.CAPTURE_SCHEMA,
        "observer_id": bridge.OBSERVER_ID,
        "authority": {"research_admitted": False, "trading_authority": False},
        "captures": [], "prefix_sha256": bridge.ZERO_SHA256,
    }


def append_capture(prior, rows=None, *, source_at="2026-10-06T14:15:00Z", status="complete"):
    """Independent wire fixture, with typed raw fields and exactly hashed bytes."""
    result = copy.deepcopy(prior)
    rows = raw_rows() if rows is None else copy.deepcopy(rows)
    start = ns(source_at)
    response = canonical({"status": "OK", "results": rows}).encode()
    payload = {
        "symbol": SYMBOL, "timeframe": "1m", "source": "polygon",
        "status": status, "failure_kind": None if status == "complete" else "http_error",
        "started_at_utc_ns": start,
        "completed_at_utc_ns": start + 4_000_000_000,
        "finality_reference_utc_ns": start,
        "finality_lag_s": 900,
        "request": {"multiplier": 1, "timespan": "minute", "from_date": "2026-10-06",
                    "to_date": "2026-10-06", "adjusted": True, "sort": "asc", "limit": 50000},
        "pages": [{
            "page_index": 0, "request_started_at_utc_ns": start + 1_000_000_000,
            "response_received_at_utc_ns": start + 3_000_000_000,
            "response_sha256": hashlib.sha256(response).hexdigest(),
            "response_bytes": len(response), "status": "OK", "rows_received": len(rows),
            "finalized_rows": len(rows), "forming_skipped": 0,
        }],
        "observations": [
            {"page_index": 0, "row_index": i, "event_start_utc_ms": row["t"],
             "event_end_utc_ms": row["t"] + 60000, "raw": row}
            for i, row in enumerate(rows)
        ],
        "counts": {"rows_received": len(rows), "finalized_rows": len(rows),
                   "forming_skipped": 0, "unchanged_suppressed": 0,
                   "observations_retained": len(rows)},
    }
    sequence = len(result["captures"]) + 1
    record = {
        "sequence": sequence, "capture_id": f"{sequence:032x}",
        "previous_capture_sha256": result["prefix_sha256"],
        "payload_sha256": digest(payload), "payload": payload,
    }
    record["capture_sha256"] = digest(record)
    result["captures"].append(record)
    result["prefix_sha256"] = record["capture_sha256"]
    return result


def reseal(envelope_value):
    """Keep malformed semantic mutations structurally well sealed for isolation tests."""
    previous = bridge.ZERO_SHA256
    for record in envelope_value["captures"]:
        record["previous_capture_sha256"] = previous
        record["payload_sha256"] = digest(record["payload"])
        record["capture_sha256"] = digest(
            {key: value for key, value in record.items() if key != "capture_sha256"})
        previous = record["capture_sha256"]
    envelope_value["prefix_sha256"] = previous


def reseal_receipt(value):
    value["receipt_sha256"] = digest(
        {key: item for key, item in value.items() if key != "receipt_sha256"})


def atomic_fixture(path, capture):
    raw = json.dumps({
        "t": SYMBOL, "tf": "1m", "asof": 1,
        # Deliberately unusable display data: the bridge may only read raw captures.
        "bars": [{"t": 1, "o": 9999, "h": 9999, "l": 9999, "c": 9999, "v": 0}],
        "minute_capture": capture,
    }, indent=2, allow_nan=False).encode()
    stage = path.with_suffix(".writing")
    with stage.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(stage, path)
    return raw


def read_at(path, instant):
    instant = ns(instant) if isinstance(instant, str) else instant
    with patch.object(bridge.time, "time_ns", side_effect=[instant - 1, instant]):
        return bridge.read_terminal_minute_snapshot(path, reader_identity=READER)


def metadata(security_id="SYNTHETIC:AAPL"):
    ref = {"source_ref": "SYNTHETIC_CONFORMANCE:owner", "receipt_sha256": SHA}
    return {
        "security_id": security_id, "availability_basis": "observed_first_seen",
        "identity": {**ref, "security_id": security_id, "known_at": "2026-10-05T00:00:00Z",
                     "valid_from": "2026-10-05"},
        "basis": {**ref, "known_at": "2026-10-05T00:00:00Z", "basis_id": "synthetic-basis",
                  "price_adjustment": "synthetic", "volume_adjustment": "synthetic",
                  "corporate_actions_sha256": SHA},
    }


def decode(snapshot, receipts, *, cutoff, stream_metadata=None):
    return bridge.decode_terminal_minute_observations(
        snapshot, receipts, reader_identity=READER, symbol=SYMBOL, stream="stock",
        stream_metadata=metadata() if stream_metadata is None else stream_metadata,
        cutoff=cutoff,
    )


def bundle(minutes, *, cutoffs=("2026-10-06T14:16:00Z",), receipts=()):
    ref = {"source_ref": "SYNTHETIC_CONFORMANCE:fixture", "receipt_sha256": SHA}
    roles = ("stock", "spy", "qqq", "sector")
    streams = {role: metadata("SYNTHETIC:AAPL" if role == "stock" else "SYNTHETIC:" + role)
               for role in roles}
    all_minutes = copy.deepcopy(minutes)
    for role in roles[1:]:
        for raw in raw_rows():
            start = EPOCH + timedelta(milliseconds=raw["t"])
            end = start + timedelta(minutes=1)
            all_minutes.append({
                **ref, "stream": role, "security_id": streams[role]["security_id"],
                "basis_id": "synthetic-basis", "revision_id": f"synthetic-{role}-{raw['t']}",
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
                "known_at": end.isoformat().replace("+00:00", "Z"),
                "open": raw["o"], "high": raw["h"], "low": raw["l"],
                "close": raw["c"], "volume": raw["v"],
            })
    return {
        "schema": INPUT_SCHEMA, "input_kind": "SYNTHETIC_CONFORMANCE",
        "calendar": {**ref, "known_at": "2026-10-05T00:00:00Z", "sessions": {
            "2026-10-05": {"open": "2026-10-05T13:30:00Z", "close": "2026-10-05T20:00:00Z"},
            "2026-10-06": {"open": "2026-10-06T13:30:00Z", "close": "2026-10-06T20:00:00Z",
                           "previous_session": "2026-10-05"},
        }},
        "streams": streams, "minutes": all_minutes,
        "terminal_minute_read_receipts": list(receipts),
        "contexts": [
            {**ref, "kind": "daily", "security_id": "SYNTHETIC:AAPL",
             "known_at": "2026-10-05T20:01:00Z", "asof_session": "2026-10-05",
             "payload": {"is_leader": True, "controlled_pullback": True}},
            {**ref, "kind": "incumbent", "security_id": "SYNTHETIC:AAPL",
             "known_at": "2026-10-06T13:30:00Z", "asof_session": "2026-10-06",
             "valid_until": "2026-10-06T20:00:00Z",
             "payload": {"owner": "engine.entry_signal.assess", "buyable_input": True,
                         "inputs_sha256": SHA, "code_sha": "b" * 40,
                         "assessment": {"synthetic_conformance_only": True}}},
        ],
        "candidates": [{"candidate_id": f"candidate-{i}", "decision_at": cutoff,
                        "session": "2026-10-06", "streams": {role: role for role in roles}}
                       for i, cutoff in enumerate(cutoffs)],
    }


@pytest.fixture
def captured(tmp_path):
    path = tmp_path / "AAPL.1m.json"
    capture = append_capture(envelope())
    raw = atomic_fixture(path, capture)
    return path, capture, raw, read_at(path, "2026-10-06T14:16:00Z")


def test_actual_read_hashes_exact_bytes_and_receipt_is_a_copy(captured):
    path, capture, raw, snapshot = captured
    receipt = snapshot.receipt
    assert snapshot.raw_bytes == raw == path.read_bytes()
    assert receipt["file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["file_bytes"] == len(raw)
    assert receipt["capture_sequence"] == 1
    assert receipt["capture_prefix_sha256"] == capture["prefix_sha256"]
    assert receipt["read_completed_at_utc_ns"] == ns("2026-10-06T14:16:00Z")
    receipt["file_sha256"] = "f" * 64
    assert snapshot.receipt["file_sha256"] == hashlib.sha256(raw).hexdigest()


def test_public_read_has_no_timestamp_override(captured):
    path = captured[0]
    with pytest.raises(TypeError):
        bridge.read_terminal_minute_snapshot(path, reader_identity=READER, now_ns=1)


def test_model_input_decode_refuses_omitted_decision_cutoff(captured):
    snapshot = captured[3]
    with pytest.raises(TypeError, match="cutoff"):
        bridge.decode_terminal_minute_observations(
            snapshot, [snapshot.receipt], reader_identity=READER, symbol=SYMBOL,
            stream="stock", stream_metadata=metadata(),
        )


def test_model_input_decode_refuses_explicit_null_decision_cutoff(captured):
    snapshot = captured[3]
    with pytest.raises(InputContractError, match="non-null decision cutoff"):
        bridge.decode_terminal_minute_observations(
            snapshot, [snapshot.receipt], reader_identity=READER, symbol=SYMBOL,
            stream="stock", stream_metadata=metadata(), cutoff=None,
        )


def test_bounded_read_missing_file_and_invalid_limit(tmp_path, captured):
    with pytest.raises(FileNotFoundError):
        bridge.read_terminal_minute_snapshot(tmp_path / "missing.json", reader_identity=READER)
    with pytest.raises(InputContractError, match="max_bytes"):
        bridge.read_terminal_minute_snapshot(captured[0], reader_identity=READER, max_bytes=32)
    for value in (False, 0, bridge.MAX_FILE_BYTES + 1):
        with pytest.raises(InputContractError):
            bridge.read_terminal_minute_snapshot(captured[0], reader_identity=READER, max_bytes=value)


def test_file_read_is_once_and_does_not_reopen_for_hash(captured):
    path = captured[0]
    original_open = type(path).open
    count = []

    def counted(instance, *args, **kwargs):
        count.append((instance, args))
        return original_open(instance, *args, **kwargs)

    with patch.object(type(path), "open", counted):
        snapshot = read_at(path, "2026-10-06T14:16:00Z")
    assert count == [(path, ("rb",))]
    assert snapshot.receipt["file_sha256"] == hashlib.sha256(snapshot.raw_bytes).hexdigest()


def test_legacy_file_mtime_and_asof_cannot_supply_availability(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps({"t": SYMBOL, "tf": "1m", "asof": 9999999999, "bars": raw_rows()}))
    with pytest.raises(InputContractError, match="minute_capture"):
        read_at(path, "2026-10-06T14:16:00Z")


@pytest.mark.parametrize("mutation", ("payload", "sequence", "duplicate_id", "authority"))
def test_capture_seals_identity_sequence_and_authority_are_fail_closed(captured, mutation):
    path, capture, _, _ = captured
    bad = append_capture(capture, rows=[], source_at="2026-10-06T14:17:00Z")
    if mutation == "payload":
        bad["captures"][0]["payload"]["observations"][0]["raw"]["c"] = 500
    elif mutation == "sequence":
        bad["captures"][1]["sequence"] = 3
        reseal(bad)
    elif mutation == "duplicate_id":
        bad["captures"][1]["capture_id"] = bad["captures"][0]["capture_id"]
        reseal(bad)
    else:
        bad["authority"]["trading_authority"] = 0
    atomic_fixture(path, bad)
    with pytest.raises(InputContractError):
        read_at(path, "2026-10-06T14:18:00Z")


def test_duplicate_json_keys_are_refused(captured):
    path = captured[0]
    path.write_bytes(b'{"minute_capture":null,"minute_capture":{}}')
    with pytest.raises(InputContractError):
        read_at(path, "2026-10-06T14:16:00Z")


def test_owner_receipt_must_be_explicit_and_cannot_fallback_to_http_clock(captured):
    snapshot = captured[3]
    missing = decode(snapshot, [], cutoff="2026-10-06T14:16:00Z")
    early = decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:15:30Z")
    assert missing["status"] == early["status"] == "UNAVAILABLE"
    assert missing["minutes"] == early["minutes"] == []
    assert missing["diagnostics"]["captures_without_visible_owner_receipt"] == 1
    observed = decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")
    assert {row["known_at"] for row in observed["minutes"]} == {"2026-10-06T14:16:00Z"}
    assert observed["minutes"][0]["source_observation"]["source_received_at_utc_ns"] \
        < snapshot.receipt["read_completed_at_utc_ns"]


def test_missing_identity_basis_and_typed_volume_remain_explicit(captured):
    path, _, _, _ = captured
    rows = raw_rows()
    rows[0].pop("v")
    rows[1]["v"] = None
    rows[2]["v"] = 12.75
    atomic_fixture(path, append_capture(envelope(), rows))
    snapshot = read_at(path, "2026-10-06T14:16:00Z")
    result = decode(snapshot, [snapshot.receipt], stream_metadata={}, cutoff="2026-10-06T14:16:00Z")
    first = result["minutes"][:3]
    assert [row["volume"] for row in first] == [None, None, 12.75]
    assert [row["source_observation"]["volume_state"] for row in first] == [
        "missing", "null", "observed"]
    assert all(row["security_id"] is None and row["basis_id"] is None for row in first)
    assert "price_volume_corporate_action_basis" in result["unproven_owner_requirements"]
    assert result["scientific_claims"] == {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"}
    assert not any(result["authority"].values())
    complete = decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")
    frame = build_input_panel(bundle(complete["minutes"]))["frames"][0]
    assert "INVALID_OHLCV" in frame["bars"]["stock"]["30"]["refusals"]


@pytest.mark.parametrize("field,value", [
    ("file_sha256", "f" * 64),
    ("read_completed_at_utc_ns", 1),
    ("capture_prefix_sha256", "f" * 64),
])
def test_receipt_tampering_is_refused(captured, field, value):
    snapshot = captured[3]
    receipt = snapshot.receipt
    receipt[field] = value
    with pytest.raises(InputContractError):
        decode(snapshot, [receipt], cutoff="2026-10-06T14:16:00Z")


def test_resealed_wrong_prefix_or_reader_and_conflicting_read_id_are_refused(captured):
    snapshot = captured[3]
    for field, value in (("capture_prefix_sha256", "f" * 64), ("reader_identity", "another.owner")):
        bad = snapshot.receipt
        bad[field] = value
        reseal_receipt(bad)
        with pytest.raises(InputContractError):
            decode(snapshot, [bad], cutoff="2026-10-06T14:16:00Z")
    bad = snapshot.receipt
    bad["read_completed_at_utc_ns"] += 1_000_000
    reseal_receipt(bad)
    with pytest.raises(InputContractError, match="conflicting"):
        decode(snapshot, [snapshot.receipt, bad], cutoff="2026-10-06T14:16:00Z")
    # Exact duplicate enrollment is idempotent.
    assert decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")["minutes"] == \
        decode(snapshot, [snapshot.receipt, snapshot.receipt], cutoff="2026-10-06T14:16:00Z")["minutes"]


def test_snapshot_byte_binding_cannot_be_swapped(captured):
    snapshot = captured[3]
    changed = bridge.TerminalMinuteSnapshot(snapshot.raw_bytes + b" ", snapshot.receipt_json)
    with pytest.raises(InputContractError, match="snapshot bytes"):
        decode(changed, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")


def test_receipt_from_a_forked_prefix_is_refused(captured):
    path, _, _, original = captured
    rows = raw_rows()
    rows[0]["h"] = 500
    atomic_fixture(path, append_capture(envelope(), rows))
    fork = read_at(path, "2026-10-06T14:17:00Z")
    with pytest.raises(InputContractError, match="prefix"):
        decode(fork, [original.receipt, fork.receipt], cutoff="2026-10-06T14:17:00Z")


def test_owner_read_before_capture_completion_is_refused(captured):
    path = captured[0]
    impossible = read_at(path, "2026-10-06T14:15:02Z")
    with pytest.raises(InputContractError, match="precedes capture completion"):
        decode(impossible, [impossible.receipt], cutoff="2026-10-06T14:16:00Z")


@pytest.mark.parametrize("status", ("partial", "failed"))
def test_incomplete_capture_observations_are_excluded(captured, status):
    path, capture, _, initial = captured
    correction = {**raw_rows()[-1], "h": 500, "c": 499}
    changed = append_capture(capture, [correction], source_at="2026-10-06T14:17:00Z", status=status)
    atomic_fixture(path, changed)
    snapshot = read_at(path, "2026-10-06T14:18:00Z")
    result = decode(snapshot, [initial.receipt, snapshot.receipt], cutoff="2026-10-06T14:18:00Z")
    assert len(result["minutes"]) == 30
    assert result["diagnostics"]["visible_capture_outcomes"][status] == 1
    assert all(row["close"] == 100 for row in result["minutes"])


def test_empty_complete_capture_is_distinct_from_missing_and_failure(tmp_path):
    path = tmp_path / "AAPL.1m.json"
    atomic_fixture(path, append_capture(envelope(), []))
    snapshot = read_at(path, "2026-10-06T14:16:00Z")
    result = decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")
    assert result["status"] == "UNAVAILABLE"
    assert result["minutes"] == []
    assert result["diagnostics"]["visible_capture_outcomes"] == {
        "complete": 1, "partial": 0, "failed": 0}
    assert result["diagnostics"]["complete_captures_with_no_retained_observations"] == 1
    assert result["diagnostics"]["captures_without_visible_owner_receipt"] == 0


def test_successive_actual_reads_preserve_correction_and_reversion_in_existing_selector(captured):
    path, capture, _, first = captured
    changed = append_capture(capture, [{**raw_rows()[-1], "h": 120, "c": 119}],
                             source_at="2026-10-06T14:17:00Z")
    atomic_fixture(path, changed)
    second = read_at(path, "2026-10-06T14:18:00Z")
    reverted = append_capture(changed, [raw_rows()[-1]], source_at="2026-10-06T14:19:00Z")
    atomic_fixture(path, reverted)
    third = read_at(path, "2026-10-06T14:20:00Z")
    receipts = [first.receipt, second.receipt, third.receipt]
    frames, visible_counts = [], []
    for cutoff in ("2026-10-06T14:16:00Z", "2026-10-06T14:18:00Z", "2026-10-06T14:20:00Z"):
        decoded = decode(third, receipts, cutoff=cutoff)
        visible_counts.append(len(decoded["minutes"]))
        panel = build_input_panel(bundle(decoded["minutes"], cutoffs=(cutoff,), receipts=receipts))
        frames.append(panel["frames"][0])
        # The unchanged finality lag still withholds contemporaneous latest 15m inputs.
        assert panel["available_count"] == 0
        assert not any(panel["authority"].values())
    assert visible_counts == [30, 31, 32]
    assert [row["close"] for row in decoded["minutes"][-3:]] == [100, 119, 100]
    bars = [frame["bars"]["stock"]["30"] for frame in frames]
    assert all(bar["availability"] == "available" for bar in bars)
    assert [bar["ohlcv"]["close"] for bar in bars] == [100, 119, 100]
    assert [bar["ohlcv"]["high"] for bar in bars] == [101, 120, 101]
    assert len({bar["input_revision_sha256"] for bar in bars}) == 3


def test_one_late_first_read_of_a_b_a_remains_same_clock_conflict(captured):
    path, capture, _, _ = captured
    changed = append_capture(capture, [{**raw_rows()[-1], "h": 120, "c": 119}],
                             source_at="2026-10-06T14:17:00Z")
    reverted = append_capture(changed, [raw_rows()[-1]], source_at="2026-10-06T14:19:00Z")
    atomic_fixture(path, reverted)
    late = read_at(path, "2026-10-06T14:20:00Z")
    result = decode(late, [late.receipt], cutoff="2026-10-06T14:20:00Z")
    assert len(result["minutes"]) == 32
    assert {row["known_at"] for row in result["minutes"]} == {"2026-10-06T14:20:00Z"}
    frame = build_input_panel(bundle(result["minutes"],
                                    cutoffs=("2026-10-06T14:20:00Z",)))["frames"][0]
    assert "CONFLICTING_MINUTE_REVISION" in frame["bars"]["stock"]["30"]["refusals"]


@pytest.mark.parametrize("malformed", ("value", "event"))
def test_future_semantic_mutation_cannot_change_complete_earlier_frame(captured, malformed):
    path, capture, _, earlier = captured
    prior = decode(earlier, [earlier.receipt], cutoff="2026-10-06T14:16:00Z")
    before = build_input_panel(bundle(prior["minutes"], receipts=[earlier.receipt]))
    changed = append_capture(capture, [raw_rows()[-1]], source_at="2026-10-06T14:17:00Z")
    observation = changed["captures"][-1]["payload"]["observations"][0]
    if malformed == "value":
        observation["raw"]["c"] = "future-invalid"
    else:
        observation["event_start_utc_ms"] = "future-invalid"
    reseal(changed)
    atomic_fixture(path, changed)
    later = read_at(path, "2026-10-06T14:18:00Z")
    receipts = [earlier.receipt, later.receipt]
    visible = decode(later, receipts, cutoff="2026-10-06T14:16:00Z")
    assert visible["minutes"] == prior["minutes"]
    assert visible["diagnostics"]["snapshot_file_sha256"] != prior["diagnostics"]["snapshot_file_sha256"]
    after = build_input_panel(bundle(visible["minutes"], receipts=receipts))
    assert canonical(before["frames"][0]) == canonical(after["frames"][0])
    assert before["input_bundle_sha256"] != after["input_bundle_sha256"]
    if malformed == "event":
        with pytest.raises(InputContractError):
            decode(later, receipts, cutoff="2026-10-06T14:18:00Z")
    else:
        future = decode(later, receipts, cutoff="2026-10-06T14:18:00Z")
        frame = build_input_panel(bundle(future["minutes"],
                                        cutoffs=("2026-10-06T14:18:00Z",)))["frames"][0]
        assert "INVALID_OHLCV" in frame["bars"]["stock"]["30"]["refusals"]


def test_ns_availability_ceil_never_backdates_into_earlier_microsecond(captured):
    path = captured[0]
    instant = ns("2026-10-06T14:16:00Z") + 1
    snapshot = read_at(path, instant)
    assert decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")["minutes"] == []
    visible = decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00.000001Z")
    assert {row["known_at"] for row in visible["minutes"]} == {"2026-10-06T14:16:00.000001Z"}
    assert snapshot.receipt["read_completed_at_utc_ns"] == instant


def test_distinct_ns_reads_in_same_microsecond_keep_a_conflict(captured):
    path, capture, _, _ = captured
    instant = ns("2026-10-06T14:16:00Z")
    first = read_at(path, instant + 1)
    changed = append_capture(capture, [{**raw_rows()[-1], "h": 120, "c": 119}])
    atomic_fixture(path, changed)
    second = read_at(path, instant + 999)
    result = decode(second, [first.receipt, second.receipt], cutoff="2026-10-06T14:16:00.000001Z")
    assert {row["known_at"] for row in result["minutes"]} == {"2026-10-06T14:16:00.000001Z"}
    frame = build_input_panel(bundle(result["minutes"],
                                    cutoffs=("2026-10-06T14:16:00.000001Z",)))["frames"][0]
    assert "CONFLICTING_MINUTE_REVISION" in frame["bars"]["stock"]["30"]["refusals"]


@pytest.mark.parametrize("mutation", ("lag", "event_end", "page_clock", "request", "accounting"))
def test_visible_source_clock_finality_and_page_bindings_are_enforced(captured, mutation):
    path, capture, _, _ = captured
    payload = capture["captures"][0]["payload"]
    if mutation == "lag":
        payload["finality_lag_s"] = 0
    elif mutation == "event_end":
        payload["observations"][-1]["event_end_utc_ms"] += 1
    elif mutation == "page_clock":
        payload["pages"][0]["response_received_at_utc_ns"] = payload["completed_at_utc_ns"] + 1
    elif mutation == "request":
        payload["request"]["adjusted"] = False
    else:
        payload["counts"]["unchanged_suppressed"] += 1
    reseal(capture)
    atomic_fixture(path, capture)
    snapshot = read_at(path, "2026-10-06T14:16:00Z")
    with pytest.raises(InputContractError):
        decode(snapshot, [snapshot.receipt], cutoff="2026-10-06T14:16:00Z")


def test_receipt_capacity_is_explicit_no_silent_pruning(captured):
    snapshot = captured[3]
    with pytest.raises(InputContractError, match="bound"):
        decode(snapshot, [snapshot.receipt] * (bridge.MAX_READ_RECEIPTS + 1), cutoff="2026-10-06T14:16:00Z")
