from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.provider_codex_reset_economics import (
    AccountObservation, BankedReset, TaskQuote, Window, preview_codex_resets,
)
from scripts.preview_codex_reset_economics import (
    MAX_INPUT_BYTES, REQUEST_SCHEMA, load_request, main, parse_request,
)

NOW = 1790899200


def request():
    a = AccountObservation("synthetic-account", "synthetic-resource", "gpt-6.1-sol", "standard",
        "synthetic-observation", "synthetic-costs", NOW, NOW + 600,
        Window(100, 0, 0, NOW + 18000, 18000),
        Window(100, 0, 0, NOW + 300000, 604800),
        (BankedReset("synthetic-reset", NOW + 900),),
        (TaskQuote("synthetic-task", NOW, NOW + 600, 60, 10, 10),),
        True, True, 0, "CLEAR", "provider_reported", "first_use_after_reset")
    return json.loads(json.dumps({"schema": REQUEST_SCHEMA, "now": NOW,
        "first_lawful_tier": "standard", "observations": [asdict(a)]}))


def test_round_trip_preserves_the_pure_owner_decision():
    parsed = parse_request(request())
    out = preview_codex_resets(**parsed)
    assert out["selected_account_id"] == "synthetic-account"
    assert out["proposed_action"] == "PROPOSE_BANKED_RESET_THEN_RUN"


@pytest.mark.parametrize("mode", ["json", "text"])
def test_actual_cli_entrypoint_in_a_fresh_process(tmp_path, mode):
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(request()))
    command = [sys.executable, str(Path(__file__).parents[1] / "scripts/preview_codex_reset_economics.py"), str(path), "--format", mode]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "synthetic-account" in result.stdout
    if mode == "json":
        assert json.loads(result.stdout)["live_admission"] is False
    else:
        assert "Supplied observations only" in result.stdout
        assert "No reset execution is authorized" in result.stdout


@pytest.mark.parametrize("change", ["top_secret", "nested_secret", "wrong_schema", "bad_boolean", "bad_record"])
def test_untrusted_input_does_not_leak_or_bypass_gates(tmp_path, capsys, change):
    raw = request()
    if change == "top_secret": raw["api_key"] = "secret-do-not-echo"
    elif change == "nested_secret": raw["observations"][0]["access_token"] = "secret-do-not-echo"
    elif change == "wrong_schema": raw["schema"] = "unsupported"
    elif change == "bad_boolean": raw["observations"][0]["weekly"]["capacity"] = True
    elif change == "bad_record": raw["observations"][0]["tasks"][0] = "secret-do-not-echo"
    path = tmp_path / "input.json"
    path.write_text(json.dumps(raw))
    assert main([str(path)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "Invalid or unavailable reset-preview evidence.\n"


def test_duplicate_json_keys_are_refused(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"now": 1, "now": 2}')
    with pytest.raises(ValueError, match="duplicate"):
        load_request(path)


def test_input_is_bounded(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="bounded"):
        load_request(path)


def test_no_eligible_account_is_a_valid_report_not_authorization(tmp_path, capsys):
    raw = request()
    raw["observations"][0]["eligible"] = False
    path = tmp_path / "input.json"
    path.write_text(json.dumps(raw))
    assert main([str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "NO_ELIGIBLE_CANDIDATE"
    assert result["proposed_action"] == "NONE"


@pytest.mark.parametrize("absent", ["short", "weekly"])
@pytest.mark.parametrize("mode", ["json", "text"])
def test_real_cli_preserves_explicit_native_window_absence(tmp_path, absent, mode):
    raw = request()
    row = raw["observations"][0]
    active = "weekly" if absent == "short" else "short"
    row[absent] = None
    row["tasks"][0][absent + "_cost"] = None
    row[active]["remaining"] = row[active]["capacity"]
    path = tmp_path / "one-window.json"
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    command = [sys.executable, str(Path(__file__).parents[1] / "scripts/preview_codex_reset_economics.py"),
               str(path), "--format", mode]
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert not result.stderr
    assert path.read_bytes() == before
    if mode == "json":
        report = json.loads(result.stdout)
        assert report["proposed_action"] == "RUN_CANDIDATE"
        assert report["candidates"][0][absent + "_remaining"] is None
        assert report["candidates"][0]["banked_resets_spent_forecast"] == 0
        assert report["live_admission"] is False
    else:
        assert "not applicable" in result.stdout
        assert "None/None" not in result.stdout
        assert "No reset execution is authorized" in result.stdout


@pytest.mark.parametrize("missing", ["short", "weekly"])
def test_missing_native_window_key_is_not_explicit_not_applicable(missing):
    raw = request()
    del raw["observations"][0][missing]
    with pytest.raises(ValueError):
        parse_request(raw)


def test_null_window_with_fabricated_cost_stays_a_closed_cli_error(tmp_path, capsys):
    raw = request()
    raw["observations"][0]["short"] = None
    path = tmp_path / "inconsistent.json"
    path.write_text(json.dumps(raw))
    assert main([str(path)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "Invalid or unavailable reset-preview evidence.\n"
