"""Causal refusal controls: no account, profile, browser, factory or process effect."""
from __future__ import annotations

import builtins
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.xguerrilla import cli, gate, lease, pilot_sim, profiles, selector_shadow, supervisor
from tools.xguerrilla.drivers import cdp, peekaboo

choose_mod = importlib.import_module("tools.xguerrilla.drivers.choose")

try:
    from tools.xguerrilla.runtime_boundary import RuntimeBindingUnavailable
except ImportError:  # the same controls are also run against the original source
    RuntimeBindingUnavailable = RuntimeError


def _trip(events, name):
    def called(*args, **kwargs):
        events.append(name)
        raise AssertionError("unexpected effect boundary: " + name)
    return called


def _capture(call):
    try:
        call()
    except Exception as exc:
        return exc
    return None


def _assert_refusal(exc, events):
    assert isinstance(exc, RuntimeBindingUnavailable), repr(exc)
    assert "runtime_binding_unavailable" in str(exc)
    assert events == []


@pytest.mark.parametrize("factory", [lease.LeaseStore, supervisor.Supervisor,
                                    profiles.Store, profiles.ProfileStore])
def test_public_state_constructors_refuse_before_path_or_database_access(factory, monkeypatch):
    events = []
    class UntouchedPath:
        def __str__(self):
            return _trip(events, "path conversion")()
        def __fspath__(self):
            return _trip(events, "path conversion")()
    with monkeypatch.context() as m:
        m.setattr(lease.sqlite3, "connect", _trip(events, "sqlite"))
        exc = _capture(lambda: factory(UntouchedPath()))
    _assert_refusal(exc, events)


@pytest.mark.parametrize("name", ["init", "snapshot", "restore", "verify", "needs_login", "describe"])
def test_profile_wrappers_cannot_reach_a_local_store(name, tmp_path, monkeypatch):
    events = []
    root = tmp_path / "profiles"
    calls = {
        "init": lambda: profiles.init("synthetic", base_dir=root),
        "snapshot": lambda: profiles.snapshot("synthetic", base_dir=root),
        "restore": lambda: profiles.restore("synthetic", "absent.tar.gz", base_dir=root),
        "verify": lambda: profiles.verify("synthetic", base_dir=root),
        "needs_login": lambda: profiles.needs_login("synthetic", None),
        "describe": lambda: profiles.describe("synthetic", base_dir=root),
    }
    with monkeypatch.context() as m:
        m.setattr(Path, "mkdir", _trip(events, "mkdir"))
        m.setattr(Path, "exists", _trip(events, "exists"))
        m.setattr(builtins, "open", _trip(events, "open"))
        exc = _capture(calls[name])
    _assert_refusal(exc, events)
    assert not root.exists()


@pytest.mark.parametrize("command", ["status", "degrade", "recover", "snapshot",
                                     "restore", "verify", "shadow"])
def test_cli_refuses_before_state_steps_or_factory_access(command, tmp_path, monkeypatch, capsys):
    root = tmp_path / "never-created"
    if command in {"status", "degrade", "recover"}:
        args = [command, "--db", str(root / "state.db"),
                "--store", str(root / "profiles"), "--personas", str(root / "personas")]
    elif command == "restore":
        args = [command, "synthetic", str(root / "missing.tar.gz"), "--store", str(root)]
    elif command == "shadow":
        args = [command, "--handle", "synthetic", "--steps", str(root / "steps.json"),
                "--screenshots", str(root / "shots"), "--driver", "never_imported:factory"]
    else:
        args = [command, "synthetic", "--store", str(root)]
    events = []
    with monkeypatch.context() as m:
        m.setattr(lease.sqlite3, "connect", _trip(events, "sqlite"))
        m.setattr(Path, "mkdir", _trip(events, "mkdir"))
        m.setattr(Path, "read_text", _trip(events, "step/profile read"))
        m.setattr(importlib, "import_module", _trip(events, "factory import"))
        code = cli.main(args)
    doc = json.loads(capsys.readouterr().out)
    assert code == 3
    assert doc["ok"] is False
    assert doc["status"] == "runtime_binding_unavailable"
    assert doc["runtime_binding_available"] is False
    assert events == []
    assert not root.exists()


def test_dry_shadow_remains_descriptive_and_never_imports_a_factory(tmp_path, monkeypatch, capsys):
    steps = tmp_path / "steps.json"
    steps.write_text(json.dumps([{"name": "synthetic", "locate": {"id": "fake"}}]))
    events = []
    with monkeypatch.context() as m:
        m.setattr(importlib, "import_module", _trip(events, "factory import"))
        code = cli.main(["shadow", "--handle", "synthetic", "--steps", str(steps),
                         "--driver", "never_imported:factory", "--dry-run"])
    doc = json.loads(capsys.readouterr().out)
    assert code == 0 and doc["dry_run"] is True and doc["checked"] == 0
    assert doc["runtime_binding_available"] is False
    assert events == []


@pytest.mark.parametrize("driver_type", [cdp.CdpDriver, peekaboo.PeekabooDriver])
@pytest.mark.parametrize("headless", [False, True])
def test_real_driver_start_refuses_before_import_probe_launch_or_cleanup(
        driver_type, headless, tmp_path, monkeypatch):
    driver = driver_type()
    driver._started = True  # a stale flag must not authorize cleanup
    driver.profile_dir = str(tmp_path / "existing-owner")
    events = []
    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name.startswith("playwright"):
            return _trip(events, "playwright import")()
        return original_import(name, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(builtins, "__import__", guarded_import)
        m.setattr(cdp.os, "makedirs", _trip(events, "mkdir"))
        m.setattr(peekaboo.subprocess, "run", _trip(events, "process/pkill"))
        m.setattr(peekaboo.PeekabooDriver, "_binary_available", _trip(events, "PATH probe"))
        m.setattr(driver, "stop", _trip(events, "cleanup"))
        exc = _capture(lambda: driver.start(str(tmp_path / "new-profile"),
                                            "http://synthetic.invalid:8000", headless))
    _assert_refusal(exc, events)
    assert not (tmp_path / "new-profile").exists()


@pytest.mark.parametrize("driver_type", [cdp.CdpDriver, peekaboo.PeekabooDriver])
def test_unbound_stop_cannot_close_or_kill_an_original_owner(driver_type, tmp_path, monkeypatch):
    driver = driver_type()
    driver.profile_dir = str(tmp_path / "unowned-profile")
    driver._started = True
    events = []
    driver._ctx = SimpleNamespace(close=_trip(events, "context close"))
    driver._pw = SimpleNamespace(stop=_trip(events, "playwright stop"))
    driver._cdp = SimpleNamespace(detach=_trip(events, "cdp detach"))
    with monkeypatch.context() as m:
        m.setattr(peekaboo.subprocess, "run", _trip(events, "pkill"))
        exc = _capture(driver.stop)
    _assert_refusal(exc, events)


@pytest.mark.parametrize("backend,headless", [("auto", False), ("auto", True),
                                               ("peekaboo", False), ("cdp", False)])
def test_choose_refuses_before_backend_selection_or_fallback(backend, headless, monkeypatch):
    events = []
    with monkeypatch.context() as m:
        m.setattr(choose_mod, "resolve", _trip(events, "backend selection"))
        exc = _capture(lambda: choose_mod.choose(backend, headless))
    _assert_refusal(exc, events)


def test_direct_shadow_refuses_before_any_driver_observation_or_capture(tmp_path):
    events = []
    driver = SimpleNamespace(locate=_trip(events, "locate"), screenshot=_trip(events, "capture"))
    exc = _capture(lambda: selector_shadow.check(
        driver, [selector_shadow.Step("fake", {"id": "fake"})], tmp_path / "shots"))
    _assert_refusal(exc, events)
    assert not (tmp_path / "shots").exists()


@pytest.mark.parametrize("name", ["quarantine", "is_quarantined", "quarantined_steps"])
def test_direct_quarantine_interfaces_refuse_without_a_local_ledger(name, tmp_path, monkeypatch):
    events = []
    root = tmp_path / "ledger"
    calls = {
        "quarantine": lambda: selector_shadow.quarantine(root, "fake", "fake", "synthetic"),
        "is_quarantined": lambda: selector_shadow.is_quarantined(root, "fake", "fake"),
        "quarantined_steps": lambda: selector_shadow.quarantined_steps(root, "fake"),
    }
    with monkeypatch.context() as m:
        m.setattr(Path, "mkdir", _trip(events, "mkdir"))
        m.setattr(Path, "exists", _trip(events, "ledger stat"))
        m.setattr(builtins, "open", _trip(events, "ledger open"))
        exc = _capture(calls[name])
    _assert_refusal(exc, events)
    assert not root.exists()


def test_simulated_report_cannot_claim_a_live_gate():
    report = pilot_sim.Report(ok=True, days=14, posts=100)
    doc = report.to_dict()
    assert doc["ok"] is True  # model success remains separately useful
    assert doc["evidence_scope"] == "synthetic_model"
    assert doc["runtime_binding_available"] is False
    assert doc["live_gate_satisfied"] is False


def test_gate_emission_cannot_promote_even_a_green_model(capsys):
    gate._emit({"ok": True, "live_gate_satisfied": True, "runtime_binding_available": True})
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True
    assert doc["evidence_scope"] == "synthetic_model"
    assert doc["runtime_binding_available"] is False
    assert doc["live_gate_satisfied"] is False
