"""Focused FS-5 tests for stage receipt immutability and label endpoints."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone

import pandas as pd
import pytest


def _event(event_id: str = "evt1") -> dict:
    return {
        "id": event_id,
        "ts": "2026-07-13T14:30:00Z",
        "observed_at": "2026-07-13T14:31:00Z",
        "decision_at": "2026-07-13T14:32:00Z",
        "root": "AAPL",
        "group": "Technology",
        "group_zh": "",
        "right": "C",
        "exp": "2026-07-17",
        "strike": 200.0,
        "dte": 4,
        "dte_bucket": "1_7d",
        "mny_bucket": "atm",
        "side": "~buy",
        "n_prints": 1,
        "size": 1,
        "avg_price": 1.0,
        "premium": 1.0,
        "premium_z": 3.0,
        "baseline_source": "test",
        "vol_gt_oi": False,
        "repeated": False,
        "zerodte": False,
        "signing_source": "tape",
        "swept": False,
    }


def _line(row: dict) -> bytes:
    return (
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        + b"\n"
    )


def _stage(event_id: str = "evt1") -> bytes:
    return b"".join(
        (
            _line(
                {
                    "schema": "live_flow.event_stage/v1",
                    "kind": "decision",
                    "event_id": event_id,
                    "event": _event(event_id),
                }
            ),
            _line(
                {
                    "schema": "live_flow.event_stage/v1",
                    "kind": "availability",
                    "event_id": event_id,
                    "available_at": "2026-07-13T14:33:00Z",
                }
            ),
        )
    )


def test_raw_prefix_receipt_is_stable_after_later_append() -> None:
    from lib.live_flow_event_stage import parse_stage_bytes

    # Whitespace and CRLF are legal JSONL bytes.  The receipt must bind these
    # original bytes rather than a reserialised semantic equivalent.
    initial = _stage().replace(b"{", b"{ ", 2).replace(b"\n", b"\r\n")
    first = parse_stage_bytes(
        initial,
        expected_session_date="2026-07-13",
        source_stage_key="live_flow/events/2026-07-13.jsonl",
    )[0]
    later = initial + _stage("evt2")
    second = parse_stage_bytes(
        later,
        expected_session_date="2026-07-13",
        source_stage_key="live_flow/events/2026-07-13.jsonl",
    )[0]
    assert first["source_stage_prefix_records"] == 2
    assert first["source_stage_prefix_sha256"] == hashlib.sha256(initial).hexdigest()
    assert second["source_stage_prefix_sha256"] == first["source_stage_prefix_sha256"]
    mutated = initial.replace(b"AAPL", b"MSFT", 1)
    changed = parse_stage_bytes(
        mutated,
        expected_session_date="2026-07-13",
        source_stage_key="live_flow/events/2026-07-13.jsonl",
    )[0]
    assert changed["source_stage_prefix_sha256"] == hashlib.sha256(mutated).hexdigest()
    assert changed["source_stage_prefix_sha256"] != first["source_stage_prefix_sha256"]


def test_stage_rejects_noncanonical_or_reordered_clocks() -> None:
    from engine.options_signal_episode import ContractError
    from lib.live_flow_event_stage import parse_stage_bytes

    raw = _stage().replace(b"2026-07-13T14:33:00Z", b"2026-07-13T14:31:00Z")
    with pytest.raises(ContractError, match="order"):
        parse_stage_bytes(
            raw,
            expected_session_date="2026-07-13",
            source_stage_key="live_flow/events/2026-07-13.jsonl",
        )


def test_stage_key_must_bind_exactly_to_its_session() -> None:
    from engine.options_signal_episode import ContractError
    from lib.live_flow_event_stage import parse_stage_bytes

    with pytest.raises(ContractError, match="does not match"):
        parse_stage_bytes(
            _stage(),
            expected_session_date="2026-07-13",
            source_stage_key="live_flow/events/2026-07-14.jsonl",
        )


def test_legacy_utc_offset_spelling_is_accepted_without_rehashing() -> None:
    from lib.live_flow_event_stage import events_from_records, parse_stage_bytes

    raw = _stage().replace(b"2026-07-13T14:33:00Z", b"2026-07-13T14:33:00+00:00")
    parsed = parse_stage_bytes(
        raw,
        expected_session_date="2026-07-13",
        source_stage_key="live_flow/events/2026-07-13.jsonl",
    )
    assert parsed[0]["available_at"] == "2026-07-13T14:33:00Z"
    records = [json.loads(line) for line in raw.splitlines()]
    assert events_from_records(records, expected_session_date="2026-07-13")[0][
        "available_at"
    ].endswith("+00:00")


def test_collector_binds_receipt_and_fetch_observation(monkeypatch) -> None:
    from collectors import flow_signals

    order: list[str] = []

    class _Body:
        def read(self):
            order.append("read")
            return _stage()

    class _S3:
        def get_object(self, **_kwargs):
            return {"Body": _Body()}

    monkeypatch.setattr(
        flow_signals,
        "_utc_now_iso",
        lambda: (order.append("clock"), "2026-07-13T20:00:00Z")[1],
    )
    rows = flow_signals._fetch_staged_rows(
        _S3(), "bucket", "live_flow/events/2026-07-13.jsonl"
    )
    assert rows and rows[0]["available_at"] == "2026-07-13T14:33:00Z"
    assert rows[0]["source_stage_observed_at"] == "2026-07-13T20:00:00Z"
    assert order == ["read", "clock"]
    assert rows[0]["source_stage_prefix_records"] == 2
    assert (
        rows[0]["source_stage_prefix_sha256"]
        and len(rows[0]["source_stage_prefix_sha256"]) == 64
    )


def test_malformed_stage_fetch_yields_no_receipt_bearing_rows() -> None:
    from collectors import flow_signals

    class _Body:
        def read(self):
            return b'{"schema":"live_flow.event_stage/v1"}\n'

    class _S3:
        def get_object(self, **_kwargs):
            return {"Body": _Body()}

    assert (
        flow_signals._fetch_staged_rows(
            _S3(), "bucket", "live_flow/events/2026-07-13.jsonl"
        )
        is None
    )


def test_stage_listing_excludes_future_dated_keys() -> None:
    from collectors.flow_signals import _event_stage_keys_within_window

    class _S3:
        def list_objects_v2(self, **_kwargs):
            return {
                "Contents": [
                    {"Key": "live_flow/events/2026-07-12.jsonl"},
                    {"Key": "live_flow/events/2026-07-13.jsonl"},
                    {"Key": "live_flow/events/2026-07-14.jsonl"},
                ],
                "IsTruncated": False,
            }

    assert _event_stage_keys_within_window(
        _S3(),
        "bucket",
        window_hours=48,
        now=datetime(2026, 7, 13, 20, tzinfo=timezone.utc),
    ) == ["live_flow/events/2026-07-12.jsonl", "live_flow/events/2026-07-13.jsonl"]


def test_archive_fallback_has_no_stage_receipt() -> None:
    from collectors.flow_signals import _events_from_blob

    row = _events_from_blob({"session_date": "2026-07-13", "events": [_event()]})[0]
    assert row.get("available_at") is None
    assert row.get("source_stage_prefix_sha256") is None


def test_keep_first_legacy_row_is_never_upgraded(tmp_path, monkeypatch) -> None:
    from collectors import flow_signals

    legacy = flow_signals._events_from_blob(
        {"session_date": "2026-07-13", "events": [_event()]}
    )
    ledger = tmp_path / "ledger.parquet"
    assert flow_signals._append_rows(ledger, legacy) == 1

    class _Body:
        def read(self):
            return _stage()

    class _S3:
        def get_object(self, **_kwargs):
            return {"Body": _Body()}

    monkeypatch.setattr(flow_signals, "_utc_now_iso", lambda: "2026-07-13T20:00:00Z")
    staged = flow_signals._fetch_staged_rows(
        _S3(), "bucket", "live_flow/events/2026-07-13.jsonl"
    )
    existing = flow_signals._load_existing_ids(ledger)
    assert (
        flow_signals._append_rows(
            ledger, [row for row in staged if row["event_id"] not in existing]
        )
        == 0
    )
    stored = pd.read_parquet(ledger).iloc[0]
    assert pd.isna(stored["source_stage_prefix_sha256"])


def test_decoded_episode_adapter_preserves_valid_event_shape() -> None:
    from lib.live_flow_event_stage import events_from_records

    records = [json.loads(line) for line in _stage().splitlines()]
    event = events_from_records(records, expected_session_date="2026-07-13")[0]
    assert event["id"] == "evt1"
    assert event["available_at"] == "2026-07-13T14:33:00Z"
    assert event["anchor_strategy"] == "durable_available_at"


def test_decoded_episode_adapter_accepts_legacy_rows_without_decision_clock() -> None:
    from lib.live_flow_event_stage import events_from_records

    records = [json.loads(line) for line in _stage().splitlines()]
    records[0]["event"].pop("decision_at")
    event = events_from_records(records, expected_session_date="2026-07-13")[0]
    assert event["id"] == "evt1"
    assert event["available_at"] == "2026-07-13T14:33:00Z"
    assert "decision_at" not in event
    assert "source_stage_prefix_sha256" not in event


def test_raw_stage_without_decision_clock_remains_rejected() -> None:
    from engine.options_signal_episode import ContractError
    from lib.live_flow_event_stage import parse_stage_bytes

    records = [json.loads(line) for line in _stage().splitlines()]
    records[0]["event"].pop("decision_at")
    raw = b"".join(_line(row) for row in records)
    with pytest.raises(ContractError, match="invalid decision_at"):
        parse_stage_bytes(
            raw,
            expected_session_date="2026-07-13",
            source_stage_key="live_flow/events/2026-07-13.jsonl",
        )


def test_grader_records_only_spy_comparable_native_endpoint() -> None:
    from engine.flow_signals_grade import _grade_event

    dates = pd.date_range("2026-07-10", periods=9, freq="B")
    close = pd.Series([100.0] * 9, index=dates)
    compatible = _grade_event("x", "AAPL", "2026-07-13", "1_7d", close, close)
    assert compatible["outcome_end_session_5"] == dates[7].date().isoformat()

    # A shifted SPY calendar makes both the comparison and endpoint unavailable.
    shifted = pd.Series(
        [100.0] * 9,
        index=dates.delete(3).append(pd.DatetimeIndex([pd.Timestamp("2026-07-23")])),
    )
    mismatch = _grade_event("y", "AAPL", "2026-07-13", "1_7d", close, shifted)
    assert mismatch["spy_excess_5"] is None
    assert mismatch["outcome_end_session_5"] is None
