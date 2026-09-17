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
        "entry_timestamp": "2023-01-03T09:35:00.050",
        "entry_delay_seconds": 0.05,
        "entry_leg_age_seconds": 0.05,
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
    assert out["primary_entry_ready"] is True
    assert out["primary_time_close_ready"] is True
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


def test_primary_time_close_freshness_is_separate_from_one_second_leg_synchrony():
    short_payload = group("call", 389.0, [
        row("2023-01-03T09:35:00.000", .04, .05),
        row("2023-01-03T15:54:56.900", .04, .05),
    ])
    long_payload = group("call", 391.0, [
        row("2023-01-03T09:35:00.050", .01, .02),
        row("2023-01-03T15:54:57.000", .01, .02),
    ])
    out = coverage.candidate_path_availability(
        candidate(), short_payload, long_payload, end_clock="15:55:00.000"
    )
    primary = out["synchrony"]["1"]
    assert primary["end_lag_seconds"] == 3.0
    assert primary["end_boundary_ready"] is False
    assert out["primary_time_close_ready"] is True


def test_primary_entry_boundary_comes_from_exact_tick_candidate_evidence():
    bad_candidate = candidate()
    bad_candidate["entry_delay_seconds"] = 1.2
    short_payload = group("call", 389.0, [row("2023-01-03T09:35:00.000", .04, .05)])
    long_payload = group("call", 391.0, [row("2023-01-03T09:35:00.050", .01, .02)])
    out = coverage.candidate_path_availability(
        bad_candidate, short_payload, long_payload, end_clock="09:35:00.050"
    )
    assert out["primary_entry_ready"] is False




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
        "entry_window_errors": {},
        "entry_coverage": {"09:35:00.000": {
            "valid_two_sided": 4, "bull_credit_band": 1, "bear_credit_band": 0
        }},
        "candidate_paths": [{
            "decision_clock": "09:35:00.000",
            "synchrony": sync,
            "primary_entry_ready": True,
            "primary_time_close_ready": True,
        }],
    }]
    out = coverage.summarize(rows)
    clock = out["development"]["by_clock"]["09:35:00.000"]
    assert clock["candidate_paths"] == 1
    assert clock["grid"]["1"]["end_boundary_ready"] == 1
    assert clock["primary_entry_ready"] == 1
    assert clock["primary_time_close_ready"] == 1
    assert clock["time_close_max_package_age_seconds"] == 5.0
    assert clock["sessions_any_valid_contract"] == 1
    assert clock["sessions_bull_credit_band"] == 1
    assert clock["sessions_bear_credit_band"] == 0
    assert clock["sessions_either_credit_band"] == 1
    forbidden = ("pnl", "profit", "outcome", "label", "target", "stop", "debit")
    text = str(out).lower()
    assert not any(token in text for token in forbidden)


def test_minute_presence_classifies_normal_zero_bid_and_unknown_without_synchrony():
    short_payload = group("call", 389.0, [
        row("2023-01-03T09:35:00.000", .04, .05),
        row("2023-01-03T09:36:00.000", .04, .05),
        row("2023-01-03T09:37:00.000", .04, .05),
    ])
    long_payload = group("call", 391.0, [
        row("2023-01-03T09:35:00.000", .01, .02),
        row("2023-01-03T09:36:00.000", 0, .01, bid_size=0),
    ])
    out = coverage.candidate_minute_presence(
        candidate(), short_payload, long_payload, end_clock="09:37:00.000"
    )
    assert out["expected_minutes"] == 3
    assert out["normal_package_minutes"] == 1
    assert out["zero_bid_carry_minutes"] == 1
    assert out["unknown_minutes"] == 1
    assert out["first_unknown"] == "2023-01-03T09:37:00"
    assert out["full_minute_presence"] is False
    assert out["synchrony_proven"] is False


def test_minute_presence_summary_cannot_claim_tick_synchrony_or_economics():
    rows = [{
        "date": "2023-01-03",
        "partition": "development",
        "entry_error": None,
        "entry_window_errors": {},
        "entry_coverage": {"09:35:00.000": {
            "valid_two_sided": 4, "bull_credit_band": 1, "bear_credit_band": 1
        }},
        "candidate_paths": [{
            "decision_clock": "09:35:00.000",
            "full_minute_presence": True,
            "zero_bid_carry_minutes": 2,
            "unknown_minutes": 0,
            "synchrony_proven": False,
        }],
    }]
    out = coverage.summarize(rows, mode="minute_presence")
    clock = out["development"]["by_clock"]["09:35:00.000"]
    assert clock["full_minute_presence"] == 1
    assert clock["paths_with_zero_bid_carry"] == 1
    assert clock["paths_with_unknown_minutes"] == 0
    assert clock["synchrony_proven"] is False
    assert clock["sessions_any_valid_contract"] == 1
    assert clock["sessions_bull_credit_band"] == 1
    assert clock["sessions_bear_credit_band"] == 1
    assert clock["sessions_either_credit_band"] == 1
    forbidden = ("pnl", "profit", "outcome", "label", "target", "stop", "debit")
    assert not any(token in str(out).lower() for token in forbidden)


def test_close_path_mode_is_closed():
    try:
        coverage.summarize([], mode="midpoint_fantasy")
    except coverage.ClosePathCoverageError as exc:
        assert "mode" in str(exc)
    else:
        raise AssertionError("unfrozen close-path mode accepted")


def test_audit_day_keeps_boundary_snapshot_diagnostic_but_uses_exact_tick_candidates(monkeypatch):
    ep = {"response": []}
    monkeypatch.setattr(coverage, "_fetch_entry_payload", lambda *args: ep)
    monkeypatch.setattr(coverage, "_fetch_entry_window_payload", lambda *args: {"response": []})
    clock_state = {
        "contracts": 8, "valid_two_sided": 6,
        "bull_credit_band": 1, "bear_credit_band": 1,
    }
    monkeypatch.setattr(coverage.entry, "option_clock_coverage", lambda payload, date: {
        clock: dict(clock_state) for clock in coverage.entry.CLOCKS
    })
    exact = candidate()
    monkeypatch.setattr(
        coverage.entry, "eligible_candidates_from_tick_window",
        lambda payload, date, clock: [dict(exact, decision_clock=clock)] if clock == "09:35:00.000" else [],
    )
    monkeypatch.setattr(coverage, "_fetch_contract_path", lambda *args, **kwargs: {"response": []})
    out = coverage.audit_day("http://127.0.0.1:25503/v3", "2023-01-03", 1, mode="minute_presence")
    assert out["entry_error"] is None
    assert out["entry_window_errors"] == {}
    assert out["entry_coverage"]["09:35:00.000"] == clock_state
    assert len(out["candidate_paths"]) == 1


def test_boundary_snapshot_failure_does_not_erase_exact_tick_candidate_universe(monkeypatch):
    def bad_snapshot(*args):
        raise TimeoutError
    monkeypatch.setattr(coverage, "_fetch_entry_payload", bad_snapshot)
    monkeypatch.setattr(coverage, "_fetch_entry_window_payload", lambda *args: {"response": []})
    exact = candidate()
    monkeypatch.setattr(
        coverage.entry, "eligible_candidates_from_tick_window",
        lambda payload, date, clock: [dict(exact, decision_clock=clock)] if clock == "09:35:00.000" else [],
    )
    monkeypatch.setattr(coverage, "_fetch_contract_path", lambda *args, **kwargs: {"response": []})
    out = coverage.audit_day("http://127.0.0.1:25503/v3", "2023-01-03", 1, mode="minute_presence")
    assert out["entry_error"] == "TimeoutError"
    assert out["entry_coverage"] is None
    assert len(out["candidate_paths"]) == 1




def test_minute_presence_receipt_does_not_advertise_tick_grid(monkeypatch):
    monkeypatch.setattr(coverage.entry, "_list_dates", lambda *args: ([], []))
    out = coverage.run_live(
        "http://127.0.0.1:25503/v3", 1, 1,
        "2023-01-03", "2023-01-03", "minute_presence",
    )
    assert out["mode"] == "minute_presence"
    assert out["interval"] == "1m"
    assert out["synchrony_grid_seconds"] == []


def test_tick_receipt_advertises_only_frozen_synchrony_grid(monkeypatch):
    monkeypatch.setattr(coverage.entry, "_list_dates", lambda *args: ([], []))
    out = coverage.run_live(
        "http://127.0.0.1:25503/v3", 1, 1,
        "2023-01-03", "2023-01-03", "tick_synchrony",
    )
    assert out["synchrony_grid_seconds"] == ["0.1", "1", "5", "10"]
