"""Synthetic UTC availability boundaries; no artifact or provider reads."""
from datetime import date, datetime

import pytest

from engine.capital_need import assemble_capital_need


def _blocks():
    period = {"accn": "synthetic", "end": "2024-12-31", "filed": "2025-02-28",
              "form": "10-K", "fp": "FY", "fy": 2024}
    debt = {"schema": "debt_maturity.v1", "status": "reported", "cik": "123456",
            "as_of": "2025-03-01", "period": dict(period),
            "buckets": [{"key": k, "reported": True, "usd": 10, "drop_reason": None}
                        for k in ("y1", "y2", "y3", "y4", "y5", "after5")],
            "total_reported_usd": 60}
    cash = {"schema": "cash_runway.v1", "status": "reported", "cik": "123456",
            "as_of": "2025-03-01", "period": {**period, "start": "2024-01-01"},
            "cash_usd": 50, "ocf_usd": -20, "capex_usd": 10}
    return debt, cash


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("timestamp,accepted", [
    ("2025-03-01T23:30:00-02:00", False),  # UTC is after cutoff
    ("2025-02-28T00:30:00+02:00", False),  # UTC is before filing
    ("2025-03-02T00:30:00+02:00", True),   # UTC remains within cutoff
    ("2025-02-27T23:30:00-02:00", True),   # UTC is on filing day
    ("2025-03-01T12:00:00+00:00", True),
    ("2025-03-01T12:00:00", False),        # no timezone is not a UTC clock
])
def test_timestamp_representations_have_identical_admission(side, timestamp, accepted):
    results = []
    for value in (timestamp, datetime.fromisoformat(timestamp)):
        blocks = _blocks()
        blocks[side]["source_available_at"] = value
        result = assemble_capital_need(*blocks, as_of=date(2025, 3, 1))
        assert (result["status"] == "complete") is accepted
        if not accepted:
            assert result["derived"]["near_term_cash_cover"] is None
        results.append(result)
    assert results[0] == results[1]


@pytest.mark.parametrize("value", ["2025-02-28", date(2025, 2, 28), "2025-03-01", date(2025, 3, 1)])
def test_existing_calendar_dates_remain_supported(value):
    blocks = _blocks()
    for block in blocks:
        block["source_available_at"] = value
    assert assemble_capital_need(*blocks, as_of=date(2025, 3, 1))["status"] == "complete"


@pytest.mark.parametrize("value", [None, "bad", {}, [],
    "0001-01-01T00:00:00+14:00", datetime.fromisoformat("0001-01-01T00:00:00+14:00"),
    "9999-12-31T23:00:00-12:00", datetime.fromisoformat("9999-12-31T23:00:00-12:00"),
])
def test_invalid_or_unrepresentable_availability_fails_closed(value):
    blocks = _blocks()
    for block in blocks:
        block["source_available_at"] = value
    result = assemble_capital_need(*blocks, as_of=date(2025, 3, 1))
    assert result["status"] == "unknown"
    assert result["derived"]["near_term_cash_cover"] is None
