"""Pressure Watch incident regressions: source truth, stale reads and warm runners."""
import ast
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest
import yaml
from engine import stocks_hub
from lib.nyse_calendar import expected_last_session

ROOT = Path(__file__).resolve().parents[1]


def payload(asof="2026-09-11", broad=False):
    data = json.loads((ROOT / "tests/fixtures/price_pressure_latest.json").read_text())
    data["asof"] = asof
    data["day"] = {"asof": asof, "broad_selloff": broad, "panel_shock_count": 10,
                   "banner": "Today's pressure is name-by-name, not market-wide."}
    data["open_events"][0].update(date=asof, state="SHOCK")
    return data


def test_false_broad_selloff_is_not_inverted_by_a_truthy_string():
    band = stocks_hub.pressure_band(payload(), board_asof="2026-09-11")
    assert band["banner"]["en"] == "Pressure was name-by-name, not market-wide."
    assert "个股" in band["banner"]["zh"]
    assert band["demoted"] is False


@pytest.mark.parametrize("reference", ["2026-09-14", "2026-09-15", "2026-09-30"])
def test_a_missed_session_is_delayed_not_warmup_or_current(reference):
    band = stocks_hub.pressure_band(payload(), board_asof=reference)
    assert band.get("stale") is True
    assert band["asof"] == "2026-09-11", "never relabel old observations"
    assert band["mode"] == "live" and band["base"] and band["resolved"]
    assert "Update delayed" in band["banner"]["en"]
    assert "更新延迟" in band["banner"]["zh"]
    assert "today" not in json.dumps(band["open"])
    assert "今日新发生" not in json.dumps(band["open"], ensure_ascii=False)


def test_a_shared_freeze_cannot_pass_by_comparing_two_stale_sources():
    expected = expected_last_session(datetime(2026, 9, 16, 2, tzinfo=timezone.utc))
    band = stocks_hub.pressure_band(payload(), board_asof="2026-09-11",
                                    expected_asof=expected.isoformat())
    assert band.get("stale") is True


@pytest.mark.parametrize("asof,expected", [("2026-09-11", "2026-09-13"),
                                           ("2026-09-04", "2026-09-07")])
def test_weekends_and_exchange_holidays_do_not_create_missing_sessions(asof, expected):
    band = stocks_hub.pressure_band(payload(asof), board_asof=expected)
    assert band.get("stale") is False


def test_undated_or_malformed_record_is_not_silently_current():
    for stamp in (None, "bad-date"):
        band = stocks_hub.pressure_band(payload(stamp), board_asof="2026-09-15")
        assert band.get("stale") is True
        assert "Update delayed" in band["banner"]["en"]


def test_index_supplies_an_independent_exchange_session_reference():
    tree = ast.parse((ROOT / "scripts/build_ticker_pages.py").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "pressure_band"
             and any(k.arg == "board_asof" for k in node.keywords)]
    assert len(calls) == 1
    expected = next((k.value for k in calls[0].keywords if k.arg == "expected_asof"), None)
    assert expected is not None, "the wall-clock calendar reference must reach the consumer"
    assert "expected_source_session" in ast.unparse(expected)


def pressure_step():
    workflow = yaml.safe_load((ROOT / ".github/workflows/daily.yml").read_text())
    return next(step for step in workflow["jobs"]["engine"]["steps"]
                if step.get("name", "").startswith("Price Pressure lobe"))["run"]


@pytest.mark.parametrize("fail_store", [False, True])
def test_warm_runner_syncs_current_bars_and_failed_restore_cannot_publish(tmp_path, fail_store):
    store = tmp_path / "data/massive_stock_day"
    store.mkdir(parents=True)
    (store / "SPY.parquet").write_bytes(b"existing stale runner file")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python"
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
                      'if [ "$FAIL_STORE" = 1 ] && [ "$2" = scripts.fetch_r2 ] && '
                      '[ "$4" = massive_stock_day ]; then exit 1; fi\n'
                      'if [ "$2" = scripts.build_price_pressure ]; then mkdir -p data/price_pressure; '
                      'printf "completed-record\\n" > data/price_pressure/latest.json; fi\n')
    python.chmod(0o755)
    calls = tmp_path / "calls"
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
           "CALL_LOG": str(calls), "FAIL_STORE": str(int(fail_store))}
    result = subprocess.run(["/bin/bash", "-e", "-c", pressure_step()],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    invoked = calls.read_text()
    assert "scripts.fetch_r2 --dirs massive_stock_day" in invoked
    if fail_store:
        assert "scripts.build_price_pressure" not in invoked
        assert "scripts.publish_r2" not in invoked
    else:
        assert "scripts.build_price_pressure" in invoked
        assert "scripts.publish_r2 --dirs price_pressure" in invoked


@pytest.mark.parametrize("now,expected", [
    ("2026-09-16T14:59:00+00:00", "2026-09-14"),
    ("2026-09-16T15:00:00+00:00", "2026-09-15"),
    ("2026-09-12T14:59:00+00:00", "2026-09-10"),
    ("2026-09-12T15:00:00+00:00", "2026-09-11"),
    ("2026-09-08T15:00:00+00:00", "2026-09-04"),
    ("2026-01-06T15:59:00+00:00", "2026-01-02"),
    ("2026-01-06T16:00:00+00:00", "2026-01-05"),
])
def test_flatfile_reference_obeys_vendor_t_plus_one_and_dst(now, expected):
    from engine.price_pressure.freshness import expected_source_session
    assert expected_source_session(datetime.fromisoformat(now)).isoformat() == expected


def test_quiet_day_is_evaluated_even_without_a_new_event():
    data = payload()
    data["evaluated_through"] = "2026-09-14"
    data["day"].update(asof="2026-09-14", banner=None, broad_selloff=None)
    band = stocks_hub.pressure_band(data, board_asof="2026-09-14",
                                    source_asof="2026-09-14", expected_asof="2026-09-14")
    assert band["asof"] == "2026-09-14"
    assert data["asof"] == "2026-09-11", "event-date restore fence stays unchanged"
    assert band["stale"] is False
    assert band["banner"] is None
    assert "today" not in json.dumps(band["open"])


def test_up_to_date_source_can_await_next_file_without_being_an_outage():
    data = payload("2026-09-14")
    data["evaluated_through"] = "2026-09-14"
    band = stocks_hub.pressure_band(data, board_asof="2026-09-15",
                                    source_asof="2026-09-14", expected_asof="2026-09-14")
    assert band["stale"] is False
    assert band["freshness_status"] == "awaiting_source"
    assert "next data file" in band["banner"]["en"]


def test_missing_expected_file_is_distinct_from_processing_lag():
    data = payload("2026-09-14")
    data["evaluated_through"] = "2026-09-14"
    band = stocks_hub.pressure_band(data, board_asof="2026-09-15",
                                    source_asof="2026-09-14", expected_asof="2026-09-15")
    assert band["freshness_status"] == "source_delayed"
    assert band["stale"] is True


def test_calendar_future_date_does_not_manufacture_freshness():
    data = payload("2026-09-18")
    data["evaluated_through"] = "2026-09-18"
    band = stocks_hub.pressure_band(data, board_asof="2026-09-15",
                                    source_asof="2026-09-14", expected_asof="2026-09-14")
    assert band["stale"] is True


@pytest.mark.parametrize("stamp", ["2026-09-12", "9999-12-31", "0001-01-01"])
def test_invalid_session_or_extreme_date_cannot_crash_or_claim_current(stamp):
    from engine.price_pressure.freshness import assess
    result = assess({"asof": stamp, "evaluated_through": stamp},
                    expected_asof="2026-09-14", source_asof="2026-09-14",
                    board_asof="2026-09-15")
    assert result["status"] == "unknown"
    assert result["stale"] is True
    assert result["expires_utc"] is None


def test_explicit_missing_evaluation_does_not_fall_back_to_event_date():
    from engine.price_pressure.freshness import assess
    result = assess({"asof": "2026-09-14", "evaluated_through": None},
                    expected_asof="2026-09-14")
    assert result["status"] == "unknown"
    assert result["evaluated_through"] is None


@pytest.mark.parametrize("field,stamp", [
    ("expected_asof", "0001-01-01"),
    ("expected_asof", "9999-12-31"),
    ("source_asof", "2026-09-12"),
    ("board_asof", "bad-date"),
])
def test_bad_reference_dates_remain_unknown_without_a_deadline(field, stamp):
    from engine.price_pressure.freshness import assess
    references = dict(expected_asof="2026-09-14", source_asof="2026-09-14",
                      board_asof="2026-09-15")
    references[field] = stamp
    result = assess({"asof": "2026-09-14", "evaluated_through": "2026-09-14"},
                    **references)
    assert result["status"] == "unknown"
    assert result["stale"] is True
    assert result["expires_utc"] is None


def test_pressure_producer_and_consumer_regressions_run_in_code_ci():
    """Registration in a data-only owner cannot qualify an ordinary code PR."""
    workflow = yaml.safe_load((ROOT / '.github/ci/legacy-jobs.yml').read_text())
    required = {'tests/test_price_pressure.py',
                'tests/test_pressure_watch_freshness.py',
                'tests/test_pressure_watch_refresh.py'}
    covered = set()
    for job in workflow['jobs'].values():
        if job.get('gate') != 'code':
            continue
        for step in job.get('steps', []):
            covered.update(required.intersection(step.get('run', '').split()))
    assert covered == required, f'Pressure Watch suites absent from code CI: {required - covered}'
