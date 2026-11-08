"""Consumer contracts over captured bytes; no acquisition, store or UI fixtures."""
from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import replace
from decimal import Decimal

import pytest

from engine.intelligence_workspace.entity import IdentityArtifactRead
from engine.options_matrix_retention import reference_for_bytes


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("retained selection must not acquire data")
    monkeypatch.setattr(socket, "create_connection", refused)
    monkeypatch.setattr(socket.socket, "connect", refused)


def captured(raw, at="2026-10-20T15:00:00Z"):
    return IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), at)


def matrix():
    return {
        "schema": "options_structure.matrix/v1", "root": "SPY",
        "session": "2026-10-19", "asof": "2026-10-20T12:00:00Z",
        "_build_meta": {"asof_date": "2026-10-19", "source_dates": {
            "oi_publication": "2026-10-19", "previous_oi_publication": "2026-10-16"}},
        "coverage": {"status": "partial", "missing_expiries": ["2026-11-06"]},
        "correction": {"status": "unspecified"}, "gaps": None,
        "cells": [
            {"expiry": "2026-10-30", "strike": 103, "call_oi": 0,
             "call_vol": None, "put_vol": 7, "delta_oi": {"call": 0, "put": None}, "gex": 9},
            {"expiry": "2026-10-30", "strike": 104, "call_oi": None, "put_oi": None},
            {"expiry": "2026-11-20", "strike": 103, "call_vol": 5},
        ],
    }


def select_matrix(doc=None, **kwargs):
    from engine.options_retained_selection import select_retained_matrix
    raw = json.dumps(matrix() if doc is None else doc).encode()
    return select_retained_matrix(reference_for_bytes("SPY", raw), captured(raw),
                                  decision_at="2026-10-20T16:00:00Z",
                                  expiry="2026-10-30", side="all", **kwargs)


def test_exact_side_rows_preserve_zero_null_missing_and_unallocated_aggregate():
    result = select_matrix()
    assert [(r.expiry, r.strike, r.side) for r in result.rows] == [
        ("2026-10-30", "103", "call"), ("2026-10-30", "103", "put")]
    assert result.rows[0].metrics == {"open_interest": 0, "volume": None, "delta_oi": 0}
    assert result.rows[1].metrics == {"volume": 7, "delta_oi": None}
    assert result.document["cells"][0]["gex"] == 9  # no invented per-side GEX
    assert len(result.document["cells"]) == 3  # selection does not destroy other rows
    assert result.reference.session == "2026-10-19"
    assert result.selection_mode == "known_snapshot_only"
    assert result.first_available_at is None and result.history_order is None
    assert result.document["coverage"] == {"status": "partial", "missing_expiries": ["2026-11-06"]}
    assert result.document["gaps"] is None
    assert result.document["_build_meta"]["source_dates"]["oi_publication"] == "2026-10-19"


def test_read_observation_never_becomes_build_or_first_availability():
    result = select_matrix()
    assert result.read_observed_at.isoformat() == "2026-10-20T15:00:00+00:00"
    assert result.document["asof"] == "2026-10-20T12:00:00Z"
    assert result.first_available_at is None


def test_decimal_coordinates_survive_without_float_roundtrip():
    from engine.options_retained_selection import select_retained_matrix
    raw = b'{"schema":"options_structure.matrix/v1","root":"SPY","session":"2026-10-19","cells":[{"expiry":"2026-10-30","strike":123456789012.12345678,"call_oi":9007199254740993}]}'
    result = select_retained_matrix(reference_for_bytes("SPY", raw), captured(raw),
                                   decision_at="2026-10-20T16:00:00Z", expiry="2026-10-30", side="call")
    assert result.rows[0].strike == "123456789012.12345678"
    assert result.rows[0].metrics["open_interest"] == Decimal("9007199254740993")
    assert result.capture.body == raw


@pytest.mark.parametrize("fault", ["digest", "length", "session", "capture_digest", "future_read", "naive_cutoff", "side", "expiry"])
def test_matrix_refuses_wrong_identity_or_selection_before_return(fault):
    from engine.options_retained_selection import select_retained_matrix
    raw = json.dumps(matrix()).encode(); ref = reference_for_bytes("SPY", raw); read = captured(raw)
    cutoff, side, expiry = "2026-10-20T16:00:00Z", "call", "2026-10-30"
    if fault == "digest": ref = replace(ref, sha256="0" * 64)
    if fault == "length": ref = replace(ref, byte_length=len(raw) + 1)
    if fault == "session": ref = replace(ref, session="2026-10-16")
    if fault == "capture_digest": read = replace(read, sha256="0" * 64)
    if fault == "future_read": read = captured(raw, "2026-10-20T17:00:00Z")
    if fault == "naive_cutoff": cutoff = "2026-10-20T16:00:00"
    if fault == "side": side = "C"
    if fault == "expiry": expiry = "2026-02-30"
    with pytest.raises(ValueError):
        select_retained_matrix(ref, read, decision_at=cutoff, expiry=expiry, side=side)


def test_absent_expiry_is_empty_with_no_zero_filling_or_current_fallback():
    from engine.options_retained_selection import select_retained_matrix
    raw = json.dumps(matrix()).encode()
    result = select_retained_matrix(reference_for_bytes("SPY", raw), captured(raw),
                                   decision_at="2026-10-20T16:00:00Z", expiry="2027-01-15", side="call")
    assert result.rows == ()
    assert result.row_status == "no_supplied_observations"
    assert result.capture.body == raw


def stage(event_id="one", *, available="2026-10-19T14:33:00Z", **extra):
    event = {"id": event_id, "root": "SPY", "exp": "2026-10-30", "right": "C", "strike": 103,
             "ts": "2026-10-19T14:30:00Z", "observed_at": "2026-10-19T14:31:00Z",
             "decision_at": "2026-10-19T14:32:00Z", "oi_asof": "2026-10-16", "open_interest": 0,
             "n_prints": 12, "swept": True, **extra}
    records = [{"schema": "live_flow.event_stage/v1", "kind": "decision", "event_id": event_id, "event": event},
               {"schema": "live_flow.event_stage/v1", "kind": "availability", "event_id": event_id, "available_at": available}]
    return b"".join(json.dumps(r).encode() + b"\n" for r in records)


def select_events(raw=None, **kwargs):
    from engine.options_retained_selection import select_retained_events
    return select_retained_events(captured(stage() if raw is None else raw), session="2026-10-19",
                                  root="SPY", decision_at="2026-10-20T16:00:00Z", **kwargs)


def test_events_keep_durable_receipt_and_all_causal_and_oi_facts():
    result = select_events()
    row = result.records[0]; event = row["event"]
    assert [event[k] for k in ["ts", "observed_at", "decision_at", "available_at"]] == [
        "2026-10-19T14:30:00Z", "2026-10-19T14:31:00Z", "2026-10-19T14:32:00Z", "2026-10-19T14:33:00Z"]
    assert event["oi_asof"] == "2026-10-16" and event["open_interest"] == 0
    assert row["source_stage_key"] == "live_flow/events/2026-10-19.jsonl"
    assert row["source_stage_prefix_records"] == 2
    assert row["source_stage_prefix_sha256"] == hashlib.sha256(stage()).hexdigest()
    assert result.package_support == "no_sourced_membership"
    assert result.population == "individual_aggregate_events"


def test_badges_and_caller_package_labels_do_not_create_membership():
    result = select_events(stage(package_id="claimed", legs=["one", "two"], multiplier=100))
    assert result.package_support == "no_sourced_membership"
    assert result.records[0]["event"]["package_id"] == "claimed"  # retained, never admitted


def test_known_event_selection_keeps_prefix_identity_after_append():
    first = select_events(event_ids=("one",))
    appended = select_events(stage() + stage("two"), event_ids=("one",))
    assert appended.records == first.records
    assert appended.capture.sha256 != first.capture.sha256
    with pytest.raises(ValueError): select_events(event_ids=("missing",))


def test_availability_receipt_preserves_nanoseconds_and_original_spelling():
    raw = stage(available="2026-10-19T14:33:00.123456789+00:00")
    result = select_events(raw)
    assert result.records[0]["source_available_at"] == "2026-10-19T14:33:00.123456789+00:00"
    assert result.records[0]["source_availability_receipt"] == raw.splitlines(keepends=True)[1]


def test_submicrosecond_availability_after_read_is_not_rounded_backwards():
    from engine.options_retained_selection import select_retained_events
    raw = stage(available="2026-10-19T14:33:00.123456789Z")
    with pytest.raises(ValueError):
        select_retained_events(captured(raw, "2026-10-19T14:33:00.123456Z"),
                               session="2026-10-19", root="SPY", decision_at="2026-10-20T16:00:00Z")


def test_unobserved_supplied_metadata_stays_raw_and_does_not_create_a_catalog():
    doc = matrix()
    doc.update({"available_at": "caller-looking-clock", "first_available_at": None,
                "correction": {"supersedes": "claim"}})
    result = select_matrix(doc)
    assert result.document["available_at"] == "caller-looking-clock"
    assert result.document["correction"] == {"supersedes": "claim"}
    assert result.first_available_at is None and result.correction_order is None


def test_invalid_out_of_view_side_is_not_hidden_by_selection():
    doc = matrix()
    doc["cells"][2]["put_oi"] = -1
    with pytest.raises(ValueError): select_matrix(doc)


@pytest.mark.parametrize("fault", ["torn", "missing_availability", "wrong_session", "causal_order", "availability_after_read"])
def test_events_refuse_unpaired_or_incoherent_captured_stage(fault):
    raw = stage()
    if fault == "torn": raw = raw[:-1]
    if fault == "missing_availability": raw = raw.splitlines(keepends=True)[0]
    if fault == "wrong_session": raw = raw.replace(b"2026-10-19T", b"2026-10-16T")
    if fault == "causal_order": raw = stage(observed_at="2026-10-19T14:29:00Z")
    if fault == "availability_after_read":
        from engine.options_retained_selection import select_retained_events
        with pytest.raises(ValueError):
            select_retained_events(captured(raw, "2026-10-19T14:32:30Z"), session="2026-10-19", root="SPY", decision_at="2026-10-20T16:00:00Z")
        return
    with pytest.raises(ValueError): select_events(raw)


def test_event_root_and_requested_ids_cannot_leak_another_root():
    raw = stage() + stage("foreign", root="QQQ")
    result = select_events(raw)
    assert [r["event"]["id"] for r in result.records] == ["one"]
    with pytest.raises(ValueError): select_events(raw, event_ids=("foreign",))


@pytest.mark.parametrize("ids", [(), ("one", "one"), (" one",), ["one"]])
def test_bad_event_selection_is_refused(ids):
    with pytest.raises(ValueError): select_events(event_ids=ids)


def test_damaged_event_capture_cannot_reuse_unchanged_digest():
    from engine.options_retained_selection import select_retained_events
    read = captured(stage())
    with pytest.raises(ValueError):
        select_retained_events(replace(read, body=read.body + b"\n"), session="2026-10-19", root="SPY",
                               decision_at="2026-10-20T16:00:00Z")


# Wire expectations are hand-derived, not computed by an inverse producer helper.
def wire_matrix_raw():
    return b'{"schema":"options_structure.matrix/v1","root":"SPY","session":"2026-10-19","coverage":null,"label":"9007199254740993","cells":[{"expiry":"2026-10-30","strike":123456789012.12345678,"call_oi":9007199254740993,"call_vol":null,"delta_oi":{"call":-2.5000},"unusual":{"call":{"ratio":3.0,"status":"unusual"}}}]}'


def encoded_matrix_wire(raw=None):
    from engine.options_retained_selection import encode_retained_matrix
    raw = wire_matrix_raw() if raw is None else raw
    return encode_retained_matrix(reference_for_bytes("SPY", raw), captured(raw),
                                  decision_at="2026-10-20T16:00:00.123456789+00:00",
                                  expiry="2026-10-30", side="call")


def test_matrix_wire_is_lossless_json_with_explicit_original_byte_authority():
    import base64
    from engine.options_retained_selection import decode_retained_selection_wire
    raw = encoded_matrix_wire()
    wire = decode_retained_selection_wire(raw)
    assert wire["schema"] == "options.retained_selection.wire/v1"
    assert wire["kind"] == "matrix"
    row = wire["rows"][0]
    assert row["strike"] == "123456789012.12345678"
    assert row["metrics"]["open_interest"] == {"decimal": "9007199254740993"}
    assert row["metrics"]["delta_oi"] == {"decimal": "-2.5"}
    assert row["metrics"]["volume"] is None
    assert wire["document"]["object"]["label"] == "9007199254740993"
    assert wire["document"]["object"]["coverage"] is None
    assert "available_at" not in wire["document"]["object"]
    assert base64.b64decode(wire["capture"]["body_base64"], validate=True) == wire_matrix_raw()
    assert wire["capture"]["sha256"] == hashlib.sha256(wire_matrix_raw()).hexdigest()
    assert wire["capture"]["byte_length"] == len(wire_matrix_raw())
    assert wire["snapshot"]["version_ref"].endswith(f':bytes:{len(wire_matrix_raw())}:session:2026-10-19')
    assert wire["decision_at"] == "2026-10-20T16:00:00.123456789+00:00"
    assert wire["state"]["selection_mode"] == "known_snapshot_only"
    assert wire["state"]["first_available_at"] is None
    assert wire["state"]["history_order"] is None
    assert wire["state"]["correction_order"] is None
    assert decode_retained_selection_wire(json.dumps(wire).encode()) == wire


def test_wire_tree_distinguishes_source_object_array_string_boolean_and_decimal():
    from engine.options_retained_selection import decode_retained_selection_wire
    doc = matrix(); doc["metadata"] = [{"decimal": "12"}, 12.0, "12", True, None]
    wire = decode_retained_selection_wire(encoded_matrix_wire(json.dumps(doc).encode()))
    assert wire["document"]["object"]["metadata"] == {"array": [
        {"object": {"decimal": "12"}}, {"decimal": "12"}, "12", True, None]}


def test_event_wire_never_projects_through_incumbent_float_values():
    import base64
    from engine.options_retained_selection import encode_retained_events, decode_retained_selection_wire
    raw = stage(available="2026-10-19T14:33:00.123456789+00:00", size=9007199254740993)
    raw = raw.replace(b'"strike": 103', b'"strike": 123456789012.12345678')
    wire = decode_retained_selection_wire(encode_retained_events(captured(raw), session="2026-10-19", root="SPY",
                                        decision_at="2026-10-20T16:00:00Z", event_ids=("one",)))
    row = wire["records"][0]
    assert row["event"]["object"]["strike"] == {"decimal": "123456789012.12345678"}
    assert row["event"]["object"]["size"] == {"decimal": "9007199254740993"}
    assert row["event"]["object"]["open_interest"] == {"decimal": "0"}
    assert row["event"]["object"]["oi_asof"] == "2026-10-16"
    assert row["source_available_at"] == "2026-10-19T14:33:00.123456789+00:00"
    assert base64.b64decode(row["source_availability_receipt_base64"], validate=True) == raw.splitlines(keepends=True)[1]
    assert row["source_stage_prefix_sha256"] == hashlib.sha256(raw).hexdigest()
    assert wire["state"]["package_support"] == "no_sourced_membership"
    assert wire["state"]["population"] == "individual_aggregate_events"


@pytest.mark.parametrize("fault", ["schema", "kind", "extra", "body", "hash", "length", "bool_length", "read_clock",
                                  "cutoff", "snapshot", "metric_float", "metric_rounding", "noncanonical_decimal",
                                  "missing_null", "state", "deep", "duplicate"])
def test_wire_decode_rejects_tampered_or_ambiguous_projection(fault):
    from engine.options_retained_selection import decode_retained_selection_wire
    wire = json.loads(encoded_matrix_wire())
    if fault == "schema": wire["schema"] = "options.retained_selection.wire/v2"
    if fault == "kind": wire["kind"] = "packages"
    if fault == "extra": wire["catalog"] = []
    if fault == "body": wire["capture"]["body_base64"] = "%%%"
    if fault == "hash": wire["capture"]["sha256"] = "0" * 64
    if fault == "length": wire["capture"]["byte_length"] += 1
    if fault == "bool_length": wire["capture"]["byte_length"] = True
    if fault == "read_clock": wire["capture"]["read_at"] = "2026-10-21T15:00:00Z"
    if fault == "cutoff": wire["decision_at"] = "2026-10-19T15:00:00Z"
    if fault == "snapshot": wire["snapshot"]["key"] = "current.json"
    if fault == "metric_float": wire["rows"][0]["metrics"]["open_interest"] = 9007199254740992.0
    if fault == "metric_rounding": wire["rows"][0]["metrics"]["open_interest"] = {"decimal": "9007199254740992"}
    if fault == "noncanonical_decimal": wire["rows"][0]["metrics"]["delta_oi"] = {"decimal": "-2.500"}
    if fault == "missing_null": del wire["rows"][0]["metrics"]["volume"]
    if fault == "state": wire["state"]["history_order"] = ["first"]
    if fault == "deep":
        for _ in range(70): wire = {"object": wire}
    raw = json.dumps(wire).encode()
    if fault == "duplicate": raw = raw.replace(b'{', b'{"schema":"duplicate",', 1)
    with pytest.raises(ValueError): decode_retained_selection_wire(raw)


def test_wire_limits_are_checked_before_decoding_capture(monkeypatch):
    from engine import options_retained_selection as selection
    raw = encoded_matrix_wire()
    monkeypatch.setattr(selection, "MAX_SELECTION_WIRE_BYTES", len(raw) - 1)
    with pytest.raises(ValueError): selection.decode_retained_selection_wire(raw)


def test_wire_decimal_bound_refuses_exponent_expansion_without_float_or_context_rounding():
    from engine.options_retained_selection import decode_retained_selection_wire
    raw = wire_matrix_raw().replace(b'9007199254740993,"call_vol"', b'1e1000000,"call_vol"')
    with pytest.raises(ValueError): encoded_matrix_wire(raw)
    wire = decode_retained_selection_wire(encoded_matrix_wire())
    assert wire["rows"][0]["metrics"]["open_interest"]["decimal"] == "9007199254740993"


def test_wire_exact_tokens_are_independent_of_callers_decimal_precision():
    from decimal import localcontext
    from engine.options_retained_selection import decode_retained_selection_wire
    with localcontext() as context:
        context.prec = 2
        flags = dict(context.flags)
        wire = decode_retained_selection_wire(encoded_matrix_wire())
        assert wire["rows"][0]["strike"] == "123456789012.12345678"
        assert wire["rows"][0]["metrics"]["open_interest"] == {"decimal": "9007199254740993"}
        assert dict(context.flags) == flags


def test_event_wire_roundtrip_never_infers_packages_or_changes_causal_clock_roles():
    from engine.options_retained_selection import encode_retained_events, decode_retained_selection_wire
    raw = stage(package_id="not-evidence", multiplier=100)
    wire = decode_retained_selection_wire(encode_retained_events(captured(raw, "2026-10-20T15:00:00.000000123+00:00"),
                                         session="2026-10-19", root="SPY", decision_at="2026-10-20T16:00:00Z"))
    assert wire["capture"]["read_at"] == "2026-10-20T15:00:00.000000123+00:00"
    assert wire["read_observed_at"] == "2026-10-20T15:00:00.000001+00:00"
    event = wire["records"][0]["event"]["object"]
    assert [event[k] for k in ["ts", "observed_at", "decision_at"]] == [
        "2026-10-19T14:30:00Z", "2026-10-19T14:31:00Z", "2026-10-19T14:32:00Z"]
    assert "available_at" not in event
    assert event["package_id"] == "not-evidence"
    assert event["multiplier"] == {"decimal": "100"}
    assert wire["state"]["package_support"] == "no_sourced_membership"
    assert decode_retained_selection_wire(json.dumps(wire).encode()) == wire


def test_extra_base64_padding_and_float_structural_count_refuse():
    from engine.options_retained_selection import decode_retained_selection_wire
    for field, replacement in [("body_base64", "padding"), ("byte_length", "float")]:
        wire = json.loads(encoded_matrix_wire())
        if replacement == "padding": wire["capture"][field] += "="
        else: wire["capture"][field] = float(wire["capture"][field])
        with pytest.raises(ValueError): decode_retained_selection_wire(json.dumps(wire).encode())
