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
