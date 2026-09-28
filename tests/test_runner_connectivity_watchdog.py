from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "runner-host" / "m2" / "runner_connectivity_watchdog.py"
SPEC = importlib.util.spec_from_file_location("runner_connectivity_watchdog", SCRIPT)
assert SPEC and SPEC.loader
watchdog = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = watchdog
SPEC.loader.exec_module(watchdog)


def _spec():
    return watchdog.RunnerSpec(
        "mac-builder-3",
        "actions.runner.example.mac-builder-3",
        Path("/tmp/actions-runner-3"),
    )


def _pick(row, *, loaded=True, worker=False):
    spec = _spec()
    return watchdog.restart_candidates(
        {spec.name: row},
        (spec,),
        loaded={spec.name: loaded},
        workers={spec.name: worker},
    )


def test_only_offline_loaded_idle_workerless_runner_is_restartable():
    assert _pick({"status": "offline", "busy": False}) == [_spec()]


def test_online_runner_is_never_restarted():
    assert _pick({"status": "online", "busy": False}) == []


def test_busy_runner_is_never_restarted():
    assert _pick({"status": "offline", "busy": True}) == []


def test_unloaded_service_is_maintenance_and_is_never_restarted():
    assert _pick({"status": "offline", "busy": False}, loaded=False) == []


def test_live_worker_suppresses_restart():
    assert _pick({"status": "offline", "busy": False}, worker=True) == []


def test_missing_api_row_is_blind_and_is_never_restarted():
    spec = _spec()
    assert watchdog.restart_candidates(
        {},
        (spec,),
        loaded={spec.name: True},
        workers={spec.name: False},
    ) == []


def test_m2_default_mapping_is_unique_and_complete():
    specs = watchdog.default_specs(Path("/Users/operator"))
    assert {s.name for s in specs} == {
        "mac-builder-3",
        "mac-builder-4",
        "mac-builder-5",
        "mac-builder-light",
    }
    assert len({s.service for s in specs}) == len(specs)
    assert len({s.root for s in specs}) == len(specs)
