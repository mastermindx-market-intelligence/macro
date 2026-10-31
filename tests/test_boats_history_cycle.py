from datetime import datetime, timezone
import hashlib
import json
import plistlib
from pathlib import Path

import pytest

from scripts.run_boats_history_cycle import CycleConfig, build_bundle, run_cycle

NOW = datetime(2026, 10, 19, 9, 10, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def bounded_fixture_space(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_boats_history_cycle as cycle
    monkeypatch.setattr(cycle.shutil, "disk_usage", lambda p: SimpleNamespace(free=1024**4))


def fixture(tmp_path):
    state, prior = tmp_path/"state", tmp_path/"prior"
    state.mkdir(mode=0o700)
    prior.mkdir(mode=0o700)
    body = b'{"bars":[[1792396800,1,1,1,1,1]]}\n'
    (prior/"AAPL.json").write_bytes(body)
    row = {"name":"AAPL.json", "bytes":len(body), "bars":1, "sha256":hashlib.sha256(body).hexdigest()}
    baseline = {"schema":"terminal.private_boats_delivery.v1", "complete_history":False,
        "directory":"/mnt/terminal_storage/boats-history/prior", "local_directory":str(prior),
        "files":[row], "bars":1, "bytes":len(body), "vendor_empty_symbols":["EMPTY"],
        "vendor_unavailable_symbols":[{"symbol":"HELD", "reason":"vendor_404"}], "requested_symbols":3}
    mp = tmp_path/"baseline.json"
    mp.write_text(json.dumps(baseline))
    (state/"current.json").write_text(json.dumps({"manifest_path":str(mp)}))
    cfg = CycleConfig(state, tmp_path/"archive", "root@example.test", tmp_path/"inert-key", 2, 1024**2)
    cfg.ssh_key.write_bytes(b"inert test key; no transport")
    cfg.ssh_key.chmod(0o600)
    calls = []
    def refresh(config, deps):
        calls.append(config)
        assert config.symbols_path.read_text() == "AAPL\nEMPTY\n"
        assert config.max_requests == 2 and config.capture
        config.output_dir.mkdir(mode=0o700)
        (config.output_dir/"AAPL.json").write_bytes(body)
        return {"status":"complete", "symbols":["AAPL", "EMPTY"], "outputs":[]}, 0
    def assemble(base, updated):
        return {**base, "files":[{**row, "origin":"refresh" if updated["symbols"] else "baseline"}]}
    return cfg, baseline, refresh, assemble, calls


def run(args, publish, **kwargs):
    cfg, _, refresh, assemble, _ = args
    return run_cycle(cfg, now=NOW, refresh=refresh, assemble=assemble, publish=publish,
        host_check=lambda now: None, session_check=lambda day: True, **kwargs)


def test_cycle_advances_local_selection_only_after_exact_remote_selection(tmp_path):
    args = fixture(tmp_path)
    cfg = args[0]
    old = (cfg.state_dir/"current.json").read_bytes()
    def publish(mp, ap, evidence, version, predecessor, target, key):
        assert (cfg.state_dir/"current.json").read_bytes() == old
        assert predecessor == "prior" and version == "session-2026-10-19"
        assert ap.stat().st_size > 0 and evidence.name == version
        manifest = json.loads(mp.read_text())
        assert Path(manifest["local_directory"], "AAPL.json").read_bytes().endswith(b"\n")
        return {"selected_version":version}
    result = run(args, publish)
    assert result["status"] == "selected"
    assert json.loads((cfg.state_dir/"current.json").read_text())["manifest_path"] == result["manifest_path"]
    with pytest.raises(FileExistsError): run(args, publish)
    assert len(args[-1]) == 1


def test_unknown_publication_holds_original_local_selection_and_no_capture_replay(tmp_path):
    args = fixture(tmp_path)
    old = (args[0].state_dir/"current.json").read_bytes()
    def unknown(*a): raise RuntimeError("delivery unknown")
    with pytest.raises(RuntimeError, match="unknown"): run(args, unknown)
    assert (args[0].state_dir/"current.json").read_bytes() == old
    with pytest.raises(FileExistsError): run(args, unknown)
    assert len(args[-1]) == 1


def test_partial_capture_never_publishes_or_changes_selection(tmp_path):
    args = fixture(tmp_path)
    cfg, _, _, assemble, _ = args
    def partial(*a): return {"status":"partial"}, 3
    with pytest.raises(RuntimeError, match="capture incomplete"):
        run_cycle(cfg, now=NOW, refresh=partial, assemble=assemble,
            publish=lambda *a: pytest.fail("published partial capture"),
            host_check=lambda now:None, session_check=lambda day:True)
    assert (cfg.state_dir/"session-2026-10-19"/"cycle-start.json").is_file()
    assert "baseline.json" in (cfg.state_dir/"current.json").read_text()


def test_calendar_and_closed_window_are_checked_before_filesystem_or_provider(tmp_path):
    cfg = CycleConfig(tmp_path/"not-provisioned", tmp_path, "root@example.test", tmp_path/"key", 1, 1)
    result = run_cycle(cfg, now=NOW, host_check=lambda now:None, session_check=lambda day:False)
    assert result["provider_requests"] == 0
    with pytest.raises(ValueError, match="post-close"):
        run_cycle(cfg, now=NOW.replace(hour=5), host_check=lambda now:None, session_check=lambda day:True)
    assert not cfg.state_dir.exists()


def test_bundle_rejects_changed_source_before_any_transport(tmp_path):
    _, base, _, _, _ = fixture(tmp_path)
    prior = Path(base["local_directory"])
    (prior/"AAPL.json").write_bytes(b"changed")
    out = tmp_path/"bundle"
    out.mkdir(mode=0o700)
    manifest = {**base, "files":[{**base["files"][0], "origin":"baseline"}]}
    with pytest.raises(ValueError, match="differs"):
        build_bundle(manifest, prior, prior, out)
    assert not (out/"history.tar").exists()


def test_daily_calendar_is_one_postclose_fire_without_restart_loop():
    source = Path(__file__).resolve().parents[1]/"ops/launchd/com.macro.boats-history.plist"
    job = plistlib.loads(source.read_bytes())
    assert job["StartCalendarInterval"] == [
        {"Weekday": day, "Hour": hour, "Minute": 10} for day in range(1, 6) for hour in (1,2)]
    assert job["RunAtLoad"] is False and job["KeepAlive"] is False and "StartInterval" not in job
    assert job["ProgramArguments"][:3] == ["/usr/bin/caffeinate", "-i", "-s"]
    assert job["WorkingDirectory"].startswith("/Volumes/Mastermind/")
    assert "--execute" in job["ProgramArguments"] and "--scheduled" in job["ProgramArguments"]


@pytest.mark.parametrize("fault", ["key-missing", "key-public", "key-link", "target", "low-space"])
def test_delivery_preflight_fails_before_permanent_session_or_capture(tmp_path, monkeypatch, fault):
    from dataclasses import replace
    from types import SimpleNamespace
    from scripts import run_boats_history_cycle as cycle
    args = list(fixture(tmp_path))
    cfg = args[0]
    if fault == "key-missing": cfg.ssh_key.unlink()
    elif fault == "key-public": cfg.ssh_key.chmod(0o644)
    elif fault == "key-link":
        target = tmp_path / "other-key"
        cfg.ssh_key.rename(target)
        cfg.ssh_key.symlink_to(target)
    elif fault == "target": args[0] = replace(cfg, ssh_target="-o ProxyCommand=bad")
    else: monkeypatch.setattr(cycle.shutil, "disk_usage", lambda p: SimpleNamespace(free=1))
    old = (cfg.state_dir / "current.json").read_bytes()
    with pytest.raises((ValueError, FileNotFoundError)):
        run(args, lambda *a: pytest.fail("transport started"))
    assert args[-1] == []
    assert not (cfg.state_dir / "session-2026-10-19").exists()
    assert (cfg.state_dir / "current.json").read_bytes() == old


def test_cycle_uses_real_assembler_with_producer_manifest(tmp_path):
    cfg, baseline, _, _, _ = fixture(tmp_path)
    body = b'{"bars":[]}\n'
    def refresh(config, dependencies):
        config.output_dir.mkdir(mode=0o700)
        (config.output_dir/"AAPL.json").write_bytes(body)
        return {"status":"complete", "symbols":["AAPL", "EMPTY"],
            "unavailable":[], "not_requested":[], "outputs":[
                {"symbol":"AAPL", "file":"AAPL.json", "status":"refreshed_empty_window",
                 "bars":0, "bytes":len(body), "sha256":hashlib.sha256(body).hexdigest(), "new_receipt":"a"*64},
                {"symbol":"EMPTY", "status":"vendor_empty", "bars":0, "new_receipt":"b"*64}]}, 0
    def publish(mp, *args):
        result = json.loads(mp.read_text())
        assert result["requested_symbols"] == 3 and result["bars"] == 0
        assert result["vendor_unavailable_symbols"] == baseline["vendor_unavailable_symbols"]
        assert result["vendor_empty_symbols"] == ["EMPTY"]
        assert len(result["files"]) == 1
        return {"selected_version":"session-2026-10-19"}
    result = run_cycle(cfg, now=NOW, refresh=refresh, publish=publish,
        host_check=lambda now:None, session_check=lambda day:True)
    assert result["status"] == "selected"


@pytest.mark.parametrize("day,host_offset,expected_hour", [
    ("2026-10-19", -7, 1), ("2026-11-02", -7, 2), ("2026-11-02", -8, 1),
    ("2027-01-05", -7, 2), ("2027-01-05", -8, 1)])
def test_daily_candidates_select_exactly_one_postclose_hour(tmp_path, day, host_offset, expected_hour):
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    due = []
    cfg = CycleConfig(tmp_path/"not-provisioned", tmp_path, "root@example.test", tmp_path/"key", 1, 1,
        scheduled=True)
    for hour in (1,2):
        now = datetime.fromisoformat(day).replace(hour=hour, minute=10,
            tzinfo=timezone(timedelta(hours=host_offset)))
        if now.astimezone(ZoneInfo("America/New_York")).hour == 4:
            due.append(hour)
        else:
            result = run_cycle(cfg, now=now, host_check=lambda now:None, session_check=lambda date:True)
            assert result["status"] == "scheduled_candidate_not_due" and result["provider_requests"] == 0
            assert not cfg.state_dir.exists()
    assert due == [expected_hour]
