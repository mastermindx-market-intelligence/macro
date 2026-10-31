"""Synthetic conformance for the owner-inert RS daily onset consumer.

These tests do not provide market-data admission, predictive calibration or
historical first-seen receipts.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import math

import pytest

from engine.entry_radar.replay.rs_onset_features import (
    DEFINITION_ID, INPUT_SCHEMA, SCHEMA, describe_onset_features,
)
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def fixture(count: int = 70):
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    days = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current.date().isoformat())
        current += timedelta(days=1)
    stock_id, bench_id = "SYNTH:security", "SYNTH:market"
    rows = []
    for i, day in enumerate(days):
        close_time = datetime.fromisoformat(day).replace(tzinfo=timezone.utc, hour=20)
        for role, sec, close in (("stock", stock_id, 100.0 + i),
                                 ("benchmark", bench_id, 100.0 + 0.3 * i)):
            rows.append({
                "stream": role, "session": day, "security_id": sec,
                "basis_id": "fixture-total-return", "revision_id": f"{role}-{i}-v1",
                "period_end": iso(close_time), "known_at": iso(close_time + timedelta(minutes=1)),
                "close": close, "source_ref": "SYNTHETIC_CONFORMANCE",
            })
    return {
        "schema": INPUT_SCHEMA, "input_kind": "SYNTHETIC_CONFORMANCE",
        "asof_session": days[-1],
        "decision_at": iso(datetime.fromisoformat(days[-1]).replace(
            tzinfo=timezone.utc, hour=20, minute=5)),
        "calendar": {"known_at": iso(start - timedelta(days=1)), "sessions": days},
        "streams": {
            "stock": {"security_id": stock_id, "basis_id": "fixture-total-return",
                      "basis_kind": "total_return", "identity_known_at": iso(start - timedelta(days=1)),
                      "basis_known_at": iso(start - timedelta(days=1))},
            "benchmark": {"security_id": bench_id, "basis_id": "fixture-total-return",
                          "basis_kind": "total_return", "identity_known_at": iso(start - timedelta(days=1)),
                          "basis_known_at": iso(start - timedelta(days=1))},
        },
        "rows": rows,
    }


def lookup(b, role, day):
    return next(row for row in b["rows"] if row["stream"] == role and row["session"] == day)


def assert_sealed(r):
    assert r["schema"] == SCHEMA
    assert r["definition_id"] == DEFINITION_ID
    assert r["source_admitted"] is False
    assert r["ranking_authority"] is False
    assert r["detector_registered"] is False
    assert r["outcomes_computed"] is False
    assert r["actual_issuance_proven"] is False
    assert r["issued_at"] is None
    assert all(x is False for x in r["authority"].values())
    assert r["descriptor_sha256"] == digest({
        k: v for k, v in r.items() if k != "descriptor_sha256"
    })


def test_complete_horizons_and_relative_wealth_formula():
    b = fixture()
    r = describe_onset_features(b)
    assert_sealed(r)
    assert r["state"] == "RESEARCH_METRICS_AVAILABLE"
    for h in (1, 3, 5, 10, 20, 63):
        m = r["windows"][str(h)]
        assert m["status"] == "measured"
        expected = ((100 + 69) / (100 + 69 - h)) / (
            (100 + 0.3 * 69) / (100 + 0.3 * (69 - h))) - 1
        assert m["value"] == pytest.approx(expected, abs=1e-12)
        assert m["end_session"] == b["asof_session"]
    assert r["acceleration_5"]["status"] == "measured"
    assert r["down_market_resilience_20"]["reason"] == "too_few_down_benchmark_sessions"


def test_early_session_is_partial_not_zero_filled():
    r = describe_onset_features(fixture(4))
    assert r["windows"]["1"]["status"] == "measured"
    assert r["windows"]["3"]["status"] == "measured"
    assert r["windows"]["5"]["reason"] == "insufficient_completed_sessions"
    assert r["acceleration_5"]["status"] == "unmeasured"
    assert_sealed(r)


def test_missing_middle_session_abstains_for_affected_windows_only():
    b = fixture()
    missing = b["calendar"]["sessions"][-4]
    b["rows"].remove(lookup(b, "stock", missing))
    r = describe_onset_features(b)
    assert r["windows"]["1"]["status"] == "measured"
    assert r["windows"]["5"]["reason"] == "missing_or_future_known_daily_observation"
    assert r["windows"]["20"]["status"] == "unmeasured"
    assert r["down_market_resilience_20"]["status"] == "unmeasured"


def test_future_revision_cannot_rewrite_original_view_or_digest():
    b = fixture()
    original = describe_onset_features(b)
    latest = copy.deepcopy(lookup(b, "stock", b["asof_session"]))
    latest.update(close=9999.0, revision_id="stock-late-correction",
                  known_at=iso(datetime.fromisoformat(b["asof_session"]).replace(
                      tzinfo=timezone.utc, hour=21)))
    b["rows"].append(latest)
    assert describe_onset_features(b) == original
    b["decision_at"] = latest["known_at"]
    corrected_now = describe_onset_features(b)
    assert corrected_now["windows"]["1"]["value"] != original["windows"]["1"]["value"]
    assert corrected_now["visible_input_sha256"] != original["visible_input_sha256"]


def test_future_session_addition_is_not_same_decision_evidence():
    b = fixture()
    old = describe_onset_features(b)
    later = copy.deepcopy(lookup(b, "stock", b["asof_session"]))
    later["session"] = "2027-01-03"
    later["revision_id"] = "future-only"
    b["rows"].append(later)
    b["calendar"]["sessions"].append("2027-01-03")
    assert describe_onset_features(b) == old


def test_current_future_known_row_never_qualifies_as_nonfire():
    b = fixture()
    lookup(b, "stock", b["asof_session"])["known_at"] = "2026-12-01T00:00:00Z"
    r = describe_onset_features(b)
    assert r["state"] == "UNAVAILABLE"
    assert r["windows"]["1"]["reason"] == "missing_or_future_known_daily_observation"


def test_calendar_and_identity_known_after_cutoff_refuse():
    b = fixture()
    b["calendar"]["known_at"] = "2026-12-01T00:00:00Z"
    r = describe_onset_features(b)
    assert r["state"] == "UNAVAILABLE"
    assert "CALENDAR_NOT_KNOWN_AT_DECISION" in r["refusals"]
    b = fixture()
    b["streams"]["stock"]["identity_known_at"] = "2026-12-01T00:00:00Z"
    assert "IDENTITY_OR_BASIS_NOT_KNOWN_AT_DECISION" in describe_onset_features(b)["refusals"]


def test_mixed_basis_returns_unavailable_not_low_rs():
    b = fixture()
    b["streams"]["benchmark"]["basis_kind"] = "unadjusted_close"
    r = describe_onset_features(b)
    assert r["state"] == "UNAVAILABLE"
    assert "MIXED_RETURN_BASIS" in r["refusals"]
    assert all(v["status"] == "unmeasured" for v in r["windows"].values())


def test_security_and_basis_mismatch_refused():
    b = fixture()
    lookup(b, "stock", b["asof_session"])["security_id"] = "SYNTH:other"
    with pytest.raises(InputContractError):
        describe_onset_features(b)
    b = fixture()
    lookup(b, "stock", b["asof_session"])["basis_id"] = "other"
    with pytest.raises(InputContractError):
        describe_onset_features(b)


def test_duplicate_visible_revision_or_same_clock_conflict_refused():
    b = fixture()
    b["rows"].append(copy.deepcopy(lookup(b, "stock", b["asof_session"])))
    with pytest.raises(InputContractError):
        describe_onset_features(b)
    b = fixture()
    row = copy.deepcopy(lookup(b, "stock", b["asof_session"]))
    row["revision_id"] = "same-time-different"
    b["rows"].append(row)
    with pytest.raises(InputContractError):
        describe_onset_features(b)


def test_negative_benchmark_days_make_explicit_resilience_measure():
    b = fixture()
    tail = b["calendar"]["sessions"][-21:]
    price = lookup(b, "benchmark", tail[0])["close"]
    for i, day in enumerate(tail[1:]):
        price *= 0.99 if i % 3 == 0 else 1.005
        lookup(b, "benchmark", day)["close"] = price
    r = describe_onset_features(b)
    m = r["down_market_resilience_20"]
    assert m["status"] == "measured"
    assert m["down_sessions"] >= 3
    assert m["value"] > 0
    assert m["definition"] == "median_simple_return_excess_on_down_benchmark_sessions"


def test_complete_window_with_only_two_down_days_abstains():
    b = fixture()
    tail = b["calendar"]["sessions"][-21:]
    price = lookup(b, "benchmark", tail[0])["close"]
    for i, day in enumerate(tail[1:]):
        price *= 0.99 if i in (2, 10) else 1.005
        lookup(b, "benchmark", day)["close"] = price
    assert describe_onset_features(b)["down_market_resilience_20"] == {
        "status": "unmeasured", "reason": "too_few_down_benchmark_sessions",
    }


@pytest.mark.parametrize("bad_price", [0, -1, float("nan"), float("inf"), True, "100"])
def test_invalid_visible_price_fails_closed(bad_price):
    b = fixture()
    lookup(b, "stock", b["asof_session"])["close"] = bad_price
    with pytest.raises(InputContractError):
        describe_onset_features(b)


def test_period_end_cannot_be_after_known_at():
    b = fixture()
    lookup(b, "stock", b["asof_session"])["period_end"] = "2027-01-01T00:00:00Z"
    with pytest.raises(InputContractError):
        describe_onset_features(b)


def test_naive_clock_duplicate_session_and_self_benchmark_refuse():
    b = fixture()
    b["decision_at"] = b["decision_at"].replace("Z", "")
    with pytest.raises(InputContractError):
        describe_onset_features(b)
    b = fixture()
    b["calendar"]["sessions"].append(b["asof_session"])
    with pytest.raises(InputContractError):
        describe_onset_features(b)
    b = fixture()
    b["streams"]["benchmark"]["security_id"] = b["streams"]["stock"]["security_id"]
    with pytest.raises(InputContractError):
        describe_onset_features(b)


def test_caller_supplied_market_kind_cannot_admit_publish_or_rank():
    b = fixture()
    b["input_kind"] = "OBSERVED_MARKET"
    b["source_admitted"] = True
    b["authority"] = {"can_rank": True}
    r = describe_onset_features(b)
    assert r["evidence_status"] == "DESCRIPTOR_BUILT_NOT_ADMITTED"
    assert_sealed(r)


def test_inputs_unchanged_and_digest_deterministic():
    b = fixture()
    frozen = copy.deepcopy(b)
    a, c = describe_onset_features(b), describe_onset_features(b)
    assert a == c
    assert b == frozen
    assert_sealed(a)
