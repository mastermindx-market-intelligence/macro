from datetime import datetime
from decimal import Decimal
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts" / "research"
sys.path.insert(0, str(SCRIPTS))
PATH = SCRIPTS / "spy_0dte_close_path_coverage.py"
SPEC = importlib.util.spec_from_file_location("spy_0dte_close_path_coverage", PATH)
coverage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = coverage
SPEC.loader.exec_module(coverage)


def group(right, strike, rows, date="2023-01-03"):
    return {"response": [{
        "contract": {"symbol": "SPY", "expiration": date, "strike": strike, "right": right},
        "data": rows,
    }]}


def row(ts, bid, ask, *, bid_size=10, ask_size=10):
    return {
        "timestamp": ts,
        "bid": bid,
        "ask": ask,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid_exchange": 6 if bid_size else 0,
        "ask_exchange": 6 if ask_size else 0,
        "bid_condition": 50 if bid_size else 0,
        "ask_condition": 50 if ask_size else 0,
    }


def candidate():
    return {
        "session_date": "2023-01-03",
        "decision_clock": "09:35:00.000",
        "family": "bear_call",
        "short_right": "C",
        "short_strike": 389.0,
        "long_strike": 391.0,
    }


def test_tick_path_reports_synchrony_and_zero_bid_without_economics():
    short_payload = group("call", 389.0, [
        row("2023-01-03T09:35:00.000", .04, .05),
        row("2023-01-03T09:35:01.000", .04, .05),
        row("2023-01-03T09:35:02.000", .04, .05),
    ])
    long_payload = group("call", 391.0, [
        row("2023-01-03T09:35:00.050", .01, .02),
        row("2023-01-03T09:35:01.050", 0, .01, bid_size=0),
        row("2023-01-03T09:35:02.050", 0, .01, bid_size=0),
    ])
    out = coverage.candidate_path_availability(
        candidate(), short_payload, long_payload, end_clock="09:35:02.050"
    )
    fast = out["synchrony"]["0.1"]
    assert fast["ready_events"] == 3
    assert fast["normal_ready_events"] == 1
    assert fast["zero_bid_carry_ready_events"] == 2
    assert fast["decision_boundary_ready"] is True
    assert fast["end_boundary_ready"] is True
    assert out["long_zero_bid_rows"] == 2
    forbidden = ("debit", "pnl", "profit", "outcome", "label", "target", "stop")
    assert not any(any(token in key.lower() for token in forbidden) for key in out)


def test_tighter_grid_refuses_stale_other_leg_but_looser_grid_reports_it():
    short_payload = group("call", 389.0, [row("2023-01-03T09:35:00.000", .04, .05)])
    long_payload = group("call", 391.0, [row("2023-01-03T09:35:00.500", .01, .02)])
    out = coverage.candidate_path_availability(
        candidate(), short_payload, long_payload, end_clock="09:35:00.500"
    )
    assert out["synchrony"]["0.1"]["ready_events"] == 0
    assert out["synchrony"]["1"]["ready_events"] == 1


def test_zero_bid_without_firm_positive_ask_is_not_exit_row():
    short_payload = group("call", 389.0, [row("2023-01-03T09:35:00.000", .04, .05)])
    long_payload = group("call", 391.0, [
        row("2023-01-03T09:35:00.050", 0, .01, bid_size=0, ask_size=0)
    ])
    out = coverage.candidate_path_availability(
        candidate(), short_payload, long_payload, end_clock="09:35:00.050"
    )
    assert out["long_exit_rows"] == 0
    assert all(state["ready_events"] == 0 for state in out["synchrony"].values())


def test_ready_summary_reports_end_boundary_without_values():
    replay = coverage.replay
    short = [replay.Quote(datetime.fromisoformat("2023-01-03T15:54:59.800"), Decimal(".04"), Decimal(".05"), 1, 1, 6, 6, 50, 50)]
    long = [replay.Quote(datetime.fromisoformat("2023-01-03T15:54:59.900"), Decimal("0"), Decimal(".01"), 0, 1, 0, 6, 0, 50)]
    out = coverage._ready_summary(
        short, long,
        decision_at=datetime.fromisoformat("2023-01-03T15:54:59.000"),
        end_at=datetime.fromisoformat("2023-01-03T15:55:00.000"),
        max_leg_age_seconds=Decimal("1"),
    )
    assert out["ready_events"] == 1
    assert out["zero_bid_carry_ready_events"] == 1
    assert out["end_lag_seconds"] == 0.1
    assert out["end_boundary_ready"] is True


def test_close_path_refuses_unfrozen_clock():
    bad = candidate()
    bad["decision_clock"] = "09:40:00.000"
    try:
        coverage.candidate_path_availability(bad, {}, {}, end_clock="09:40:00.000")
    except coverage.ClosePathCoverageError as exc:
        assert "frozen" in str(exc)
    else:
        raise AssertionError("unfrozen clock accepted")


def test_summary_stays_coverage_only():
    sync = {
        key: {
            "ready_events": 3,
            "normal_ready_events": 2,
            "zero_bid_carry_ready_events": 1,
            "first_ready": "2023-01-03T09:35:00",
            "last_ready": "2023-01-03T15:54:59.9",
            "decision_lag_seconds": 0.0,
            "end_lag_seconds": 0.1,
            "max_ready_gap_seconds": 10.0,
            "decision_boundary_ready": True,
            "end_boundary_ready": True,
        }
        for key in ("0.1", "1", "5", "10")
    }
    rows = [{
        "date": "2023-01-03",
        "partition": "development",
        "entry_error": None,
        "candidate_paths": [{"decision_clock": "09:35:00.000", "synchrony": sync}],
    }]
    out = coverage.summarize(rows)
    clock = out["development"]["by_clock"]["09:35:00.000"]
    assert clock["candidate_paths"] == 1
    assert clock["grid"]["1"]["end_boundary_ready"] == 1
    forbidden = ("pnl", "profit", "outcome", "label", "target", "stop", "debit")
    text = str(out).lower()
    assert not any(token in text for token in forbidden)
