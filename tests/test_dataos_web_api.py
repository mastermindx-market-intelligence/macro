"""Transport validation, real materialization, and bounded process-contract tests."""
from __future__ import annotations

import datetime as dt
import json
import signal
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lib.dataos import web_api, web_lab, web_lab_worker
from lib.dataos.web_workspace import DataWorkspace, RootBinding, WorkspaceError


@pytest.fixture
def case(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    registry = tmp_path / "registry.yml"
    registry.write_text("schema: dataset_registry.v1\ndatasets: []\n")
    source = root / "prices.parquet"
    pq.write_table(pa.table({
        "Session": [dt.date(2026, 10, n) for n in [5, 6, 7, 8]],
        "ClosePx": [100.0, 101.0, 102.0, 103.0],
        "HighPx": [101.0, 102.0, 103.0, 104.0],
        "LowPx": [99.0, 100.0, 101.0, 102.0],
        "Shares": [1000, 1100, 1200, 1300],
    }), source, row_group_size=2)
    ws = DataWorkspace((RootBinding("fixture", root, "research_capture"),), registry,
                       source_revision="d" * 40)
    runs = tmp_path / "runs"
    config = tmp_path / "host.json"
    config.write_text(json.dumps({
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": str(registry),
        "roots": [{"alias": "fixture", "path": str(root)}],
        "test_workspace": {"path": str(runs), "required_mount": "/"},
    }))
    return SimpleNamespace(ws=ws, root=root, source=source, config=config, runs=runs)


def _execution(**changes):
    value = {
        "request": {
            "signal_id": "golden_cross_7_35", "refs": ["fixture:prices.parquet"],
            "horizon_bars": 9, "cost_bps": 3.5, "n_configs_searched": 17,
        },
        "time_column": "Session",
        "bar_frequency": "daily",
        "column_map": {"close": "ClosePx", "high": "HighPx", "low": "LowPx", "volume": "Shares"},
    }
    value.update(changes)
    return value


def test_dispatch_exposes_real_rows_and_provenance(case):
    described = web_api.dispatch(case.ws, {"action": "describe", "ref": "fixture:prices.parquet"},
                                 config_path=case.config)
    result = web_api.dispatch(case.ws, {
        "action": "read", "ref": "fixture:prices.parquet", "columns": ["Session", "ClosePx"],
        "expected_version": described["source"]["file_version"], "offset": 1, "limit": 2,
    }, config_path=case.config)
    assert result["result"]["rows"] == [
        {"Session": "2026-10-06", "ClosePx": 101.0},
        {"Session": "2026-10-07", "ClosePx": 102.0},
    ]
    assert result["implementation_revision"] == "d" * 40
    assert result["source"]["ref"] == "fixture:prices.parquet"
    assert not case.runs.exists()


def test_dispatch_plan_does_not_start_worker_or_create_artifacts(case):
    result = web_api.dispatch(case.ws, {
        "action": "lab_plan", "signal_id": "golden_cross_7_35",
        "refs": ["fixture:prices.parquet"],
    }, config_path=case.config)
    assert result["read_only"] and not result["execution_ready"]
    assert result["missing_fields"] == ["n_configs_searched"]
    assert result["request"]["horizon_bars"] == 21
    assert not case.runs.exists()


@pytest.mark.parametrize("api_request", [
    {"action": "search", "command": "arbitrary"},
    {"action": "browse", "root": "fixture", "recursive": True},
    {"action": "describe", "ref": "fixture:prices.parquet", "include_secrets": True},
    {"action": "read", "ref": "fixture:prices.parquet", "mode": "write"},
    {"action": "lab_signals", "module": "arbitrary"},
    {"action": "lab_plan", "signal_id": "golden_cross_7_35", "refs": ["fixture:prices.parquet"],
     "kwargs": {"window": 2}},
    {"action": "capabilities", "extra": True},
    {"action": "browse"},
    {"action": "read"},
])
def test_dispatch_rejects_unknown_or_missing_action_fields(case, api_request):
    with pytest.raises(WorkspaceError) as error:
        web_api.dispatch(case.ws, api_request, config_path=case.config)
    assert error.value.code == "INVALID_REQUEST_FIELDS"
    assert not case.runs.exists()


@pytest.mark.parametrize("api_request", [None, [], "read", {}, {"action": 1}])
def test_request_envelope_must_be_a_typed_object(case, api_request):
    with pytest.raises(WorkspaceError) as error:
        web_api.dispatch(case.ws, api_request, config_path=case.config)
    assert error.value.code == "INVALID_REQUEST"


def test_unknown_action_and_oversized_request_have_closed_errors(case):
    with pytest.raises(WorkspaceError) as error:
        web_api.dispatch(case.ws, {"action": "shell"}, config_path=case.config)
    assert error.value.code == "UNKNOWN_ACTION"
    with pytest.raises(WorkspaceError) as error:
        web_api.validate_request({"action": "search", "query": "x" * (web_api.MAX_REQUEST_BYTES + 1)})
    assert error.value.code == "REQUEST_TOO_LARGE"


@pytest.mark.parametrize("api_request", [
    {"action": "browse", "root": []},
    {"action": "browse", "root": {}},
    {"action": "browse", "root": "fixture", "path": []},
    {"action": "describe", "ref": {}},
    {"action": "read", "ref": "fixture:prices.parquet", "expected_version": 123},
    {"action": "search", "query": {}},
])
def test_invalid_field_types_do_not_escape_as_python_type_errors(case, api_request):
    with pytest.raises(WorkspaceError):
        web_api.dispatch(case.ws, api_request, config_path=case.config)
    assert not case.runs.exists()


def test_materialize_binds_actual_parquet_columns_and_clock_without_rebasing(case):
    version = case.ws.describe("fixture:prices.parquet")["source"]["file_version"]
    execution = web_api._lab_execution_request(_execution(
        expected_versions={"fixture:prices.parquet": version}, start="2026-10-06", end="2026-10-08"
    ))
    universe, sources = web_lab_worker._materialize(case.ws, execution)
    frame = universe["fixture:prices.parquet"]
    assert list(frame) == ["close", "high", "low", "volume"]
    assert frame["close"].tolist() == [101.0, 102.0, 103.0]
    assert frame.index.name == "Session"
    assert frame.index.is_unique and frame.index.is_monotonic_increasing
    assert sources[0]["file_version"] == version
    assert sources[0]["loaded_rows"] == 3
    assert sources[0]["first_stored_time"].startswith("2026-10-06")
    assert sources[0]["last_stored_time"].startswith("2026-10-08")
    assert sources[0]["column_map"] == execution["column_map"]
    assert "no rebasing" in sources[0]["price_basis"]
    assert not case.runs.exists()


@pytest.mark.parametrize("mapping", [
    {}, {"high": "HighPx"}, {"Close": "ClosePx"},
    {"close": "ClosePx", "adjusted": "ClosePx"},
    {"close": "ClosePx", "high": "ClosePx"},
    {"close": "Session"}, {"close": 4}, ["ClosePx"],
])
def test_lab_column_map_is_explicit_unique_and_closed(mapping):
    with pytest.raises(WorkspaceError) as error:
        web_api._lab_execution_request(_execution(column_map=mapping))
    assert error.value.code == "INVALID_OHLCV_COLUMN_MAP"


@pytest.mark.parametrize("versions", [
    [], {"different:ref": "statv1:" + "1" * 64},
    {"fixture:prices.parquet": "unknown"},
    {"fixture:prices.parquet": 1},
])
def test_lab_source_versions_are_validated_before_execution(versions):
    with pytest.raises(WorkspaceError) as error:
        web_api._lab_execution_request(_execution(expected_versions=versions))
    assert error.value.code == "INVALID_SOURCE_VERSIONS"


def test_lab_budget_and_arbitrary_calculation_fields_fail_before_run_artifacts(case):
    no_budget = _execution()
    no_budget["request"]["n_configs_searched"] = None
    with pytest.raises(WorkspaceError) as error:
        web_api.run_lab(case.ws, case.config, no_budget)
    assert error.value.code == "LAB_PLAN_NOT_EXECUTABLE"
    override = _execution()
    override["request"]["code"] = "arbitrary"
    with pytest.raises(WorkspaceError) as error:
        web_api.run_lab(case.ws, case.config, override)
    assert error.value.code == "INVALID_REQUEST_FIELDS"
    assert not case.runs.exists()


@pytest.mark.parametrize("times,prices,expected", [
    (["2026-10-05", "2026-10-05"], [1, 2], "LAB_DATE_INDEX_MUST_BE_UNIQUE_AND_ASCENDING"),
    (["2026-10-06", "2026-10-05"], [1, 2], "LAB_DATE_INDEX_MUST_BE_UNIQUE_AND_ASCENDING"),
    ([1791158400, 1791244800], [1, 2], "LAB_TIME_COLUMN_REQUIRES_ISO_DATES"),
    (["2026-10-05", "2026-10-06T00:00:00Z"], [1, 2], "LAB_MIXED_TIME_ENCODING"),
    (["2026-10-05T10:00:00Z", "2026-10-05T11:00:00Z"], [1, 2], "LAB_DAILY_BARS_REQUIRED"),
    (["2026-10-05", "2026-10-06"], ["bad", "data"], "LAB_NON_NUMERIC_OHLCV"),
])
def test_materialize_refuses_ambiguous_clock_or_numeric_inputs(case, times, prices, expected):
    path = case.root / "bad.parquet"
    pq.write_table(pa.table({"Session": times, "ClosePx": prices}), path)
    raw = _execution(column_map={"close": "ClosePx"})
    raw["request"]["refs"] = ["fixture:bad.parquet"]
    with pytest.raises(WorkspaceError) as error:
        web_lab_worker._materialize(case.ws, web_api._lab_execution_request(raw))
    assert error.value.code == expected


def test_materialize_refuses_source_version_mismatch(case):
    raw = _execution(expected_versions={"fixture:prices.parquet": "statv1:" + "f" * 64})
    with pytest.raises(WorkspaceError) as error:
        web_lab_worker._materialize(case.ws, web_api._lab_execution_request(raw))
    assert error.value.code == "SOURCE_VERSION_MISMATCH"


def test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result(case, monkeypatch):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)
    monkeypatch.setenv("WEB_TEST_SECRET_SENTINEL", "must-not-be-inherited")
    captured = {}

    class Process:
        returncode = 0
        pid = 444444

        def __init__(self, command, **kwargs):
            captured.update(command=command, kwargs=kwargs)

        def communicate(self, data, timeout):
            captured["execution"] = json.loads(data)
            captured["timeout"] = timeout
            run = captured["kwargs"]["cwd"]
            (run / "result.json").write_text(json.dumps({
                "research_only": True, "read_only": False, "trial": {"verdict": "NO-EDGE"},
            }))

    monkeypatch.setattr(web_api.subprocess, "Popen", Process)
    result = web_api.run_lab(case.ws, case.config, _execution())
    kwargs = captured["kwargs"]
    assert kwargs["start_new_session"] is True
    assert captured["timeout"] == web_api.MAX_LAB_WALL_SECONDS
    assert "WEB_TEST_SECRET_SENTINEL" not in kwargs["env"]
    assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert all(kwargs["env"][name] == str(kwargs["cwd"]) for name in ["TMPDIR", "TMP", "TEMP"])
    assert kwargs["cwd"].parent == case.runs
    assert "--lab-worker" in captured["command"]
    assert captured["execution"]["request"]["n_configs_searched"] == 17
    assert result["run"]["state"] == "SUCCEEDED"
    assert result["result"]["trial"]["verdict"] == "NO-EDGE"
    assert result["result"]["read_only"] is False
    assert (kwargs["cwd"] / "request.json").is_file()
    status = json.loads((kwargs["cwd"] / "status.json").read_text())
    assert "result.json" in status["artifact_files"]
    assert status["production_ledger_written"] is False


def test_timed_out_worker_is_stopped_and_sealed_without_claiming_success(case, monkeypatch):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)
    stopped = []

    class Process:
        pid = 444444
        returncode = -9

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self, data=None, timeout=None):
            if data is not None:
                raise subprocess.TimeoutExpired("fixture-worker", timeout)

    monkeypatch.setattr(web_api.subprocess, "Popen", Process)
    monkeypatch.setattr(web_api.os, "killpg", lambda pid, sig: stopped.append((pid, sig)))
    result = web_api.run_lab(case.ws, case.config, _execution())
    assert stopped == [(444444, signal.SIGKILL)]
    assert result["run"]["state"] == "TIMED_OUT"
    assert result["result"]["error"] == "LAB_RESULT_UNAVAILABLE"
    assert len(list(case.runs.glob("run-*/status.json"))) == 1


@pytest.mark.parametrize("binding", [
    None, "unbound", {"path": "/somewhere", "required_mount": "/", "extra": True},
    {"path": "relative", "required_mount": "/"},
    {"path": "/", "required_mount": "/"},
])
def test_test_workspace_binding_is_strict_before_any_process(case, binding):
    payload = json.loads(case.config.read_text())
    payload["test_workspace"] = binding
    case.config.write_text(json.dumps(payload))
    with pytest.raises(WorkspaceError):
        web_api._host_test_root(case.config)
    assert not case.runs.exists()


@pytest.mark.parametrize("frequency", ["intraday", "weekly", None, 1, {}, []])
def test_lab_run_requires_declared_daily_bars_before_artifacts(case, frequency):
    with pytest.raises(WorkspaceError) as error:
        web_api.run_lab(case.ws, case.config, _execution(bar_frequency=frequency))
    assert error.value.code == "LAB_DAILY_BARS_REQUIRED"
    assert not case.runs.exists()


def test_lab_run_requires_explicit_bar_frequency(case):
    execution = _execution()
    del execution["bar_frequency"]
    with pytest.raises(WorkspaceError) as error:
        web_api.run_lab(case.ws, case.config, execution)
    assert error.value.code == "INVALID_REQUEST_FIELDS"
    assert not case.runs.exists()


def test_launch_failure_retains_reviewable_run_and_seals_status(case, monkeypatch):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)

    def fail_launch(*_args, **_kwargs):
        raise OSError("sensitive-host-path-must-not-escape")

    monkeypatch.setattr(web_api.subprocess, "Popen", fail_launch)
    response = web_api.run_lab(case.ws, case.config, _execution())
    run = response["run"]
    assert run["state"] == "FAILED"
    assert run["failure_code"] == "LAB_PROCESS_LAUNCH_FAILED"
    assert run["process_id"] is None and run["exit_code"] is None
    assert response["result"] == {"error": "LAB_PROCESS_LAUNCH_FAILED"}
    run_dir = case.runs / run["run_id"]
    assert json.loads((run_dir / "status.json").read_text()) == run
    request = json.loads((run_dir / "request.json").read_text())
    assert request["run_id"] == run["run_id"]
    assert request["request_sha256"] == run["request_sha256"]
    assert "sensitive-host-path-must-not-escape" not in json.dumps(response)


def test_timeout_exit_race_is_reaped_and_keeps_timeout_state(case, monkeypatch):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)
    waits = []

    class Process:
        pid = 444445
        returncode = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self, data=None, timeout=None):
            waits.append(timeout)
            if data is not None:
                raise subprocess.TimeoutExpired("fixture-worker", timeout)

    def exit_race(pid, sig):
        assert (pid, sig) == (444445, signal.SIGKILL)
        raise ProcessLookupError("already exited")

    monkeypatch.setattr(web_api.subprocess, "Popen", Process)
    monkeypatch.setattr(web_api.os, "killpg", exit_race)
    response = web_api.run_lab(case.ws, case.config, _execution())
    assert waits == [web_api.MAX_LAB_WALL_SECONDS, 5]
    assert response["run"]["state"] == "TIMED_OUT"
    status = case.runs / response["run"]["run_id"] / "status.json"
    assert json.loads(status.read_text())["state"] == "TIMED_OUT"


@pytest.mark.parametrize("worker_output,expected_error", [
    (None, "LAB_RESULT_UNAVAILABLE"),
    ("not-json", "LAB_RESULT_INVALID"),
    ("[]", "LAB_RESULT_INVALID"),
])
def test_zero_exit_requires_valid_result_before_success(case, monkeypatch, worker_output, expected_error):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)

    class Process:
        pid = 444446
        returncode = 0

        def __init__(self, *_args, **kwargs):
            self.run_dir = kwargs["cwd"]

        def communicate(self, _data, timeout):
            if worker_output is not None:
                (self.run_dir / "result.json").write_text(worker_output)

    monkeypatch.setattr(web_api.subprocess, "Popen", Process)
    response = web_api.run_lab(case.ws, case.config, _execution())
    assert response["run"]["state"] == "FAILED"
    assert response["run"]["failure_code"] == expected_error
    assert response["result"]["error"] == expected_error
    status = case.runs / response["run"]["run_id"] / "status.json"
    assert json.loads(status.read_text())["state"] == "FAILED"


def test_unreaped_timeout_reports_reconciliation_required(case, monkeypatch):
    case.runs.mkdir()
    monkeypatch.setattr(web_api, "_host_test_root", lambda _path: case.runs)
    waits = []

    class Process:
        pid = 444447
        returncode = None

        def __init__(self, *_args, **_kwargs):
            pass

        def communicate(self, data=None, timeout=None):
            waits.append(timeout)
            raise subprocess.TimeoutExpired("fixture-worker", timeout)

    monkeypatch.setattr(web_api.subprocess, "Popen", Process)
    monkeypatch.setattr(web_api.os, "killpg", lambda _pid, _sig: None)
    response = web_api.run_lab(case.ws, case.config, _execution())
    assert waits == [web_api.MAX_LAB_WALL_SECONDS, 5]
    assert response["run"]["state"] == "TERMINATION_UNCONFIRMED"
    assert response["run"]["process_id"] == 444447
    assert response["run"]["exit_code"] is None
    assert response["run"]["failure_code"] == "LAB_PROCESS_RECONCILIATION_REQUIRED"
    status = case.runs / response["run"]["run_id"] / "status.json"
    assert json.loads(status.read_text()) == response["run"]
