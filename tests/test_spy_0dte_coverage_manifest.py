import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
RESEARCH = ROOT / "scripts" / "research"
sys.path.insert(0, str(RESEARCH))
path = RESEARCH / "spy_0dte_coverage_manifest.py"
spec = importlib.util.spec_from_file_location("coverage", path)
coverage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = coverage
spec.loader.exec_module(coverage)


def row(
    ts,
    bid,
    ask,
    bid_size=10,
    ask_size=10,
    bid_exchange=6,
    ask_exchange=65,
    condition=50,
):
    return {
        "timestamp": ts,
        "bid": bid,
        "ask": ask,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid_exchange": bid_exchange,
        "ask_exchange": ask_exchange,
        "bid_condition": condition,
        "ask_condition": condition,
    }


def group(right, strike, rows, date="2025-07-01"):
    return {
        "contract": {
            "symbol": "SPY",
            "expiration": date,
            "strike": strike,
            "right": right,
        },
        "data": rows,
    }


def test_clock_coverage_finds_side_correct_two_dollar_spreads():
    date = "2025-07-01"
    clock = date + "T09:35:00.000"
    payload = {
        "response": [
            group("PUT", 600, [row(clock, 0.23, 0.24)], date),
            group("PUT", 598, [row(clock, 0.10, 0.11)], date),
            group("CALL", 610, [row(clock, 0.24, 0.25)], date),
            group("CALL", 612, [row(clock, 0.11, 0.12)], date),
        ]
    }
    out = coverage.option_clock_coverage(payload, date)
    assert out["09:35:00.000"]["bull_credit_band"] == 1
    assert out["09:35:00.000"]["bear_credit_band"] == 1
    assert out["09:35:00.000"]["valid_two_sided"] == 4


def test_bad_selected_side_does_not_create_candidate():
    date = "2025-07-01"
    clock = date + "T09:35:00.000"
    payload = {
        "response": [
            group("PUT", 600, [row(clock, 0.23, 0.24, bid_size=0)], date),
            group("PUT", 598, [row(clock, 0.10, 0.11)], date),
        ]
    }
    out = coverage.option_clock_coverage(payload, date)
    assert out["09:35:00.000"]["bull_credit_band"] == 0


def test_wrong_expiration_fails_closed():
    date = "2025-07-01"
    payload = {"response": [group("PUT", 600, [], "2025-07-02")]}
    try:
        coverage.option_clock_coverage(payload, date)
    except coverage.CoverageError as exc:
        assert "non-0DTE" in str(exc)
    else:
        raise AssertionError("wrong expiration was accepted")


def test_frozen_partition_boundaries_are_exact():
    assert coverage.partition_for_date("2024-06-28") == "development"
    assert coverage.partition_for_date("2024-07-01") == "validation"
    assert coverage.partition_for_date("2025-07-01") == "holdout"
    assert coverage.partition_for_date("2026-07-15") == "forensic_quarantine"


def test_summary_is_availability_only():
    rows = [
        {
            "date": "2023-01-03",
            "error": None,
            **{
                clock: {
                    "valid_two_sided": 2,
                    "bull_credit_band": 1,
                    "bear_credit_band": 0,
                }
                for clock in coverage.CLOCKS
            },
        },
        {"date": "2024-07-01", "error": "TimeoutError"},
    ]
    summary = coverage.summarize(
        rows, {"2023-01-03": 31, "2024-07-01": 30}
    )
    assert summary["development"]["09:35_any_valid_contract"] == 1
    assert summary["development"]["09:35_either_credit_band"] == 1
    assert summary["validation"]["option_errors"] == 1
    assert all(
        "pnl" not in str(key).lower()
        for part in summary.values()
        for key in part
    )
