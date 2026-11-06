from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "research" / "cross_session_source_census.py"
SPEC = importlib.util.spec_from_file_location("cross_session_source_census", MODULE)
assert SPEC is not None and SPEC.loader is not None
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)

RAW = ROOT / "research" / "CROSS_SESSION_SOURCE_TIMING_CENSUS_RAW_V0_2026-09-25.json"


def _raw() -> dict:
    return json.loads(RAW.read_text(encoding="utf-8"))


def _complete(rows: list[dict]) -> dict:
    return {
        "schema": c.CENSUS_SCHEMA,
        "census_window": {
            "start": "2026-06-14T00:00:00Z",
            "end": "2026-09-24T23:59:59Z",
        },
        "coverage": {
            "status": "complete",
            "primary_timing_frequency_test_allowed": True,
        },
        "counts": {"recovered_unique_clusters": len(rows)},
        "outcome_firewall": {
            "timing_frequency_not_computed": True,
            "prospective_holdout_not_opened": True,
        },
        "rows": rows,
    }


def _row(event_id: str, at: str, direction: str) -> dict:
    return {
        "event_id": event_id,
        "available_at": at,
        "direction": direction,
        "timing_primary_eligible": True,
        "outcome_context_exposed": False,
    }


def test_current_raw_census_validates_but_remains_inference_blocked():
    out = c.validate_census(_raw())
    assert out["rows"] == 35
    assert out["unique_event_ids"] == 35
    assert out["coverage_status"] == "retrieval_incomplete"
    assert out["primary_timing_frequency_test_allowed"] is False
    assert out["directions"]["relief"] == 22
    assert out["directions"]["mixed_conflict"] == 4


def test_timing_frequency_refuses_current_incomplete_census():
    with pytest.raises(c.CensusContractError, match="coverage is not complete"):
        c.timing_frequency_summary(_raw(), after_asia_close={})


def test_incomplete_census_cannot_claim_primary_test_allowed():
    doc = _raw()
    doc["coverage"]["primary_timing_frequency_test_allowed"] = True
    with pytest.raises(c.CensusContractError, match="incomplete coverage"):
        c.validate_census(doc)


def test_complete_census_uses_only_caller_supplied_session_labels():
    doc = _complete(
        [
            _row("r1", "2026-08-04T11:43:00Z", "relief"),
            _row("r2", "2026-08-05T19:54:00Z", "implementation_relief"),
            _row("c1", "2026-08-14T09:07:00Z", "escalation"),
            _row("c2", "2026-08-26T11:27:00Z", "mixed_conflict"),
        ]
    )
    out = c.timing_frequency_summary(
        doc,
        after_asia_close={"r1": True, "r2": False, "c1": True, "c2": None},
    )
    assert out["counts"]["relief"] == {
        "after_asia_close": 1,
        "other": 1,
        "missing": 0,
    }
    assert out["counts"]["control"] == {
        "after_asia_close": 1,
        "other": 0,
        "missing": 1,
    }
    assert out["relief_after_asia_close_rate"] == 0.5
    assert out["control_after_asia_close_rate"] == 1.0
    assert out["difference_in_rates"] == -0.5


def test_session_classifier_uses_authoritative_intervals_not_weekday_rules():
    sessions = [
        {
            "open_at": "2026-09-24T01:30:00Z",
            "close_at": "2026-09-24T04:00:00Z",
        },
        {
            "open_at": "2026-09-24T05:00:00Z",
            "close_at": "2026-09-24T08:00:00Z",
        },
    ]
    lunch = c.classify_from_authoritative_intervals(
        "2026-09-24T04:30:00Z",
        cash_sessions=sessions,
    )
    assert lunch["cash_open"] is False
    assert lunch["minutes_since_previous_close"] == 30.0
    assert lunch["minutes_until_next_open"] == 30.0

    afternoon = c.classify_from_authoritative_intervals(
        "2026-09-24T06:00:00Z",
        cash_sessions=sessions,
    )
    assert afternoon["cash_open"] is True
    assert afternoon["calendar_source"] == "caller_supplied_authoritative_intervals"


def test_overlapping_authoritative_sessions_are_refused():
    with pytest.raises(c.CensusContractError, match="cannot overlap"):
        c.classify_from_authoritative_intervals(
            "2026-09-24T03:00:00Z",
            cash_sessions=[
                {
                    "open_at": "2026-09-24T01:30:00Z",
                    "close_at": "2026-09-24T04:00:00Z",
                },
                {
                    "open_at": "2026-09-24T03:30:00Z",
                    "close_at": "2026-09-24T08:00:00Z",
                },
            ],
        )


def test_duplicate_event_id_and_out_of_window_are_refused():
    doc = _complete(
        [
            _row("dup", "2026-08-04T11:43:00Z", "relief"),
            _row("dup", "2026-08-05T19:54:00Z", "escalation"),
        ]
    )
    with pytest.raises(c.CensusContractError, match="duplicate event_id"):
        c.validate_census(doc)

    doc = _complete(
        [_row("late", "2026-09-25T00:00:00Z", "relief")]
    )
    with pytest.raises(c.CensusContractError, match="outside the frozen census window"):
        c.validate_census(doc)
