from __future__ import annotations

import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_code_to_vps.sh"


def test_deployed_sha_prefers_valid_marker(tmp_path, monkeypatch):
    from app import main

    expected = "a" * 40
    (tmp_path / ".deployed_git_sha").write_text(f"{expected}\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: pytest.fail("valid release marker must avoid Git fallback"),
    )

    assert main._resolve_deployed_git_sha(tmp_path) == expected


def test_deployed_sha_rejects_marker_and_uses_full_local_head(tmp_path, monkeypatch):
    from app import main

    expected = "b" * 40
    (tmp_path / ".deployed_git_sha").write_text("not-a-git-sha\n", encoding="utf-8")

    def fake_check_output(argv, **kwargs):
        assert argv == ["git", "rev-parse", "HEAD"]
        assert kwargs["cwd"] == tmp_path
        return f"{expected}\n"

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    assert main._resolve_deployed_git_sha(tmp_path) == expected


def test_deployed_sha_fails_closed_when_both_sources_are_invalid(tmp_path, monkeypatch):
    from app import main

    (tmp_path / ".deployed_git_sha").write_text("1234567\n", encoding="utf-8")
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "also-invalid\n")
    assert main._resolve_deployed_git_sha(tmp_path) is None


def test_health_exposes_exact_full_commit(monkeypatch):
    from app import main
    from brain import client, codex_bridge

    expected = "c" * 40
    monkeypatch.setattr(main, "_git_sha", expected)
    monkeypatch.setattr(client, "backend", lambda: "waterfall")
    monkeypatch.setattr(client, "available", lambda: True)
    monkeypatch.setattr(codex_bridge, "available", lambda: True)
    monkeypatch.setattr(main.app.state, "scheduler", SimpleNamespace(running=True), raising=False)

    health = main.health()
    assert health["commit"] == expected
    assert health["version"] == expected
    assert health["reasoning_policy_ok"] is True
    assert health["scheduled_runtime_ok"] is True
    assert health["scheduler_running"] is True


def test_non_serve_only_startup_fails_when_scheduler_is_unavailable(monkeypatch):
    from app import main, scheduler
    from app import auth

    monkeypatch.setattr(auth, "serve_only", lambda: False)
    monkeypatch.setattr(scheduler, "start", lambda: None)

    with pytest.raises(RuntimeError, match="scheduler failed to start"):
        main._start_scheduler()


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _fake_transport(
    tmp_path: Path, *, fail_new_release: bool
) -> tuple[dict[str, str], Path, str, str]:
    """Run shell orchestration only, with real rsync confined to fixture trees.

    App/forward imports, SSH, curl and systemd are never delegated to real tools.
    The fake service's booted SHA is independent of the on-disk marker.
    """
    import shutil
    import sys

    real_rsync = shutil.which("rsync")
    if real_rsync is None:
        pytest.skip("local rsync is required to verify deletion/filter semantics")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    rsync_peer_bin = tmp_path / "rsync-peer-bin"
    rsync_peer_bin.mkdir()
    (rsync_peer_bin / "rsync").symlink_to(Path(real_rsync).resolve())
    remote, source, live_data = (tmp_path / name for name in ("remote", "source", "live-data"))
    for root in (remote, source):
        (root / "app").mkdir(parents=True)
    autonomous = live_data / "portfolios/autonomous"
    autonomous.mkdir(parents=True)
    (autonomous / "account.json").write_text('{"cash":1000000}\n')
    (autonomous / "fills.jsonl").write_text('{"date":"2026-08-11","ticker":"AAPL","side":"buy"}\n')
    (remote / "app/old.py").write_text("old\n")
    (source / "app/old.py").write_text("new-release\n")
    (source / "app/main.py").write_text("fixture; never imported\n")
    old_sha, new_sha = "1" * 40, "2" * 40
    (remote / ".deployed_git_sha").write_text(old_sha + "\n")
    key = tmp_path / "deploy_key"
    key.write_text("fixture-only\n")
    events = tmp_path / "restart_events"
    (tmp_path / "service_state").write_text("active")
    (tmp_path / "booted_sha").write_text(old_sha)
    shim = fake_bin / "transport.py"
    _write_executable(shim, "#!" + sys.executable + "\n" + r'''
import hashlib, json, os, pathlib, signal, subprocess, sys

root = pathlib.Path(os.environ["FAKE_ROOT"]).resolve()
remote, source, data = (root / name for name in ("remote", "source", "live-data"))
state_path, boot_path = root / "service_state", root / "booted_sha"
marker = data / "portfolio_forward_evaluation/start.json"
name, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
def flag(name): return os.environ.get(name, "0") == "1"
def gate(value):
    with (root / "activation_events").open("a") as stream: stream.write(value + "\n")
def event(value):
    with (root / "transport_events.jsonl").open("a") as stream:
        stream.write(json.dumps({"event": value, "service": state_path.read_text()}) + "\n")
def inside(path):
    value = pathlib.Path(path).absolute()
    if not value.is_relative_to(root): raise RuntimeError("fixture path escape: " + str(value))
    return value
def output(value): print(json.dumps(value, sort_keys=True))

if name == "ssh":
    # Only the one fake host is admitted; no real ssh executable is reachable here.
    if len(args) != 8 or args[:1] != ["-i"] or args[2:6] != ["-o", "BatchMode=yes", "-o", "ConnectTimeout=20"] or args[6] != "fixture-host":
        raise RuntimeError("unexpected fake SSH invocation")
    inside(args[1])
    cmd = args[7].replace("/etc/systemd/system", str(root / "systemd"))
    if "/opt/mastermind" in cmd or "146.190.142.17" in cmd or "/Users/" in cmd:
        raise RuntimeError("production path escaped fixture overrides")
    if flag("FAKE_FAIL_MARKER") and ".deployed_git_sha" in cmd and "printf '%s\\n'" in cmd and os.environ["FAKE_EXPECTED"] in cmd:
        sys.exit(31)
    sys.exit(subprocess.call(["/bin/bash", "-c", cmd], env=os.environ))
elif name == "rsync":
    clean, i = [], 0
    while i < len(args):
        if args[i] == "-e":
            i += 2
            continue
        clean.append(args[i]); i += 1
    src, dst = clean[-2:]
    if ":" in dst:
        if not dst.startswith("fixture-host:"): raise RuntimeError("unexpected rsync host")
        dst = dst[len("fixture-host:"):]
    src_path, dst_path = inside(src), inside(dst)
    dry = any(arg.startswith("-") and not arg.startswith("--") and "n" in arg[1:] for arg in clean[:-2])
    kind = "forward" if src_path == source else ("snapshot" if src_path == remote else "restore")
    if not dry: event(kind)
    if kind == "snapshot" and flag("FAKE_FAIL_SNAPSHOT") and not dry:
        (root / "snapshot_failed").touch(); sys.exit(18)
    if kind == "restore" and flag("FAKE_FAIL_RESTORE") and not dry:
        (remote / "app/old.py").write_text("partial-restore\n"); sys.exit(18)
    # Apple rsync finds its local peer on PATH. Only this already-confined
    # transfer bypasses the rsync shim; SSH and every other shim stay in place.
    peer_bin = inside(os.environ["FAKE_RSYNC_PEER_BIN"])
    rsync_env = dict(os.environ, PATH=str(peer_bin) + os.pathsep + os.environ["PATH"])
    result = subprocess.call([os.environ["FAKE_REAL_RSYNC"], *clean[:-2], str(src_path) + "/", str(dst_path) + "/"], env=rsync_env)
    if result: sys.exit(result)
    if kind == "forward" and not dry and flag("FAKE_REMOVE_ACTIVE_ON_FORWARD"):
        marker.unlink()
    if kind == "forward" and not dry and flag("FAKE_TERM_DURING_FORWARD"):
        os.kill(os.getppid(), signal.SIGTERM)
    if kind == "forward" and not dry and flag("FAKE_RSYNC_PARTIAL"):
        if flag("FAKE_CHANGE_EXCLUDED"):
            (remote / "app/.env").write_text("newer-protected-value\n")
        sys.exit(23)
    sys.exit(0)
elif name == "cp":
    paths = [arg for arg in args if not arg.startswith("-")]
    for path in paths: inside(pathlib.Path.cwd() / path if not pathlib.Path(path).is_absolute() else path)
    if flag("FAKE_FAIL_SNAPSHOT") and any(".deploy_prev" in arg for arg in args) and not (root / "snapshot_failed").exists():
        (root / "snapshot_failed").touch(); sys.exit(18)
    sys.exit(subprocess.call([os.environ["FAKE_REAL_CP"], *args]))
elif name == "systemctl":
    if args[:1] == ["stop"]:
        gate("stop"); event("stop")
        if flag("FAKE_STOP_FAIL") or (flag("FAKE_ROLLBACK_STOP_FAIL") and boot_path.read_text() == os.environ["FAKE_EXPECTED"]): sys.exit(5)
        if not flag("FAKE_STOP_STAYS_ACTIVE"): state_path.write_text("inactive")
        sys.exit(0)
    if args[:1] == ["show"]:
        if "--value" in args: print(state_path.read_text())
        else: print("ActiveState=" + state_path.read_text() + "\nSubState=" + ("dead" if state_path.read_text() == "inactive" else "running") + "\nMainPID=" + ("0" if state_path.read_text() == "inactive" else "42"))
        sys.exit(0)
    if args[:1] == ["is-active"]:
        if "--quiet" not in args: print(state_path.read_text())
        sys.exit(0 if state_path.read_text() == "active" else 3)
    if args[:1] == ["daemon-reload"]: event("daemon-reload"); sys.exit(0)
    if args[:1] != ["restart"]: raise RuntimeError("unexpected systemctl command")
    gate("restart"); event("restart")
    sha = (remote / ".deployed_git_sha").read_text().strip() if (remote / ".deployed_git_sha").exists() else "missing"
    with (root / "restart_events").open("a") as stream: stream.write(sha + "\n")
    state_path.write_text("active"); boot_path.write_text(sha)
    if sha == os.environ["FAKE_EXPECTED"] and flag("FAKE_CREATE_EXCLUDED_CACHE_ON_RESTART"):
        cache = remote / "new_package/__pycache__/x.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"protected startup cache\n")
    mutated = root / "authority_mutated_once"
    if not mutated.exists():
        for field, filename in (("ACCOUNT", "account.json"), ("FILLS", "fills.jsonl")):
            path = data / "portfolios/autonomous" / filename
            if flag("FAKE_MUTATE_" + field + "_ON_RESTART"):
                with path.open("a") as stream: stream.write("mutated\n")
                mutated.touch()
            if os.environ.get("FAKE_REMOVE_AUTHORITY_ON_RESTART") == field.lower():
                path.unlink(); mutated.touch()
    if flag("FAKE_FAIL_RESTART_ONCE") and not (root / "restart_failed_once").exists():
        (root / "restart_failed_once").touch(); sys.exit(32)
    sys.exit(0)
elif name == "curl":
    if args[-1:] != ["http://fixture.invalid/health"]: raise RuntimeError("unexpected health URL")
    if state_path.read_text() != "active": sys.exit(22)
    sha = boot_path.read_text()
    if sha != os.environ["FAKE_EXPECTED"] and flag("FAKE_FAIL_OLD_HEALTH"): sys.exit(22)
    output({"reasoning_policy_ok": not (flag("FAKE_FAIL_NEW") and sha == os.environ["FAKE_EXPECTED"]), "scheduled_runtime_ok": os.environ.get("FAKE_SCHEDULER_OK", "true") == "true", "commit": sha})
elif name == "python3":
    if args[:2] != ["-m", "portfolio.forward_evaluation"] or len(args) < 3:
        raise RuntimeError("only the fake forward CLI is admitted; no app import")
    command = args[2]; gate(command)
    expected = os.environ["FAKE_EXPECTED"]
    if command == "init":
        marker.parent.mkdir(parents=True, exist_ok=True)
        if flag("FAKE_FOREIGN_INIT"):
            marker.write_text(json.dumps({"release_state": "pending_health", "deployment_sha": os.environ.get("FAKE_FOREIGN_SHA", "3" * 40), "foreign": True}) + "\n")
            sys.exit(1)
        if marker.exists():
            payload = json.loads(marker.read_text())
            output({**payload, "initialized": False})
        else:
            payload = {"release_state": "pending_health", "deployment_sha": expected, "evaluation_start": "2026-08-11"}
            marker.write_text(json.dumps(payload, sort_keys=True) + "\n")
            if flag("FAKE_LOST_INIT_REPLY"): sys.exit(255)
            output({**payload, "initialized": True})
    elif command == "finalize":
        if not marker.exists(): sys.exit(2)
        payload = json.loads(marker.read_text())
        if payload.get("release_state") != "active":
            payload.update(release_state="active", health_verified_sha=expected)
            marker.write_text(json.dumps(payload, sort_keys=True) + "\n")
        if flag("FAKE_LOST_FINALIZE_REPLY"): sys.exit(255)
        output(payload)
    elif command == "status":
        if flag("FAKE_FAIL_STATUS"): sys.exit(2)
        payload = json.loads(marker.read_text()) if marker.exists() else {}
        active = payload.get("release_state") == "active"
        output({**payload, "status": "started" if active else "not_started"})
        sys.exit(0 if active else 2)
    else: raise RuntimeError("unknown forward CLI command")
elif name == "sha256sum":
    for arg in args:
        if arg == "--": continue
        path = inside(arg)
        print(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path))
elif name == "find":
    if flag("FAKE_SILENT_RECEIPT_SCAN_FAILURE"): sys.exit(1)
    for arg in args:
        if arg.startswith("/"): inside(arg)
    sys.exit(subprocess.call([os.environ["FAKE_REAL_FIND"], *args]))
elif name == "flock":
    gate("flock:" + " ".join(args)); sys.exit(1 if flag("FAKE_LOCK_FAIL") else 0)
elif name == "sleep":
    sys.exit(0)
else:
    raise RuntimeError("unadmitted fake command: " + name)
''')
    for command in ("ssh", "rsync", "systemctl", "curl", "python3", "flock", "sleep", "cp", "sha256sum", "find"):
        (fake_bin / command).symlink_to(shim)
    env = {key: value for key, value in os.environ.items() if not key.startswith(("MASTERMIND_", "FAKE_")) and key != "PYTHONPATH"}
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "MASTERMIND_DEPLOY_SOURCE": str(source) + "/", "MASTERMIND_DEPLOY_EXPECT_SHA": new_sha,
        "MASTERMIND_VPS_HOST": "fixture-host", "MASTERMIND_VPS_PATH": str(remote),
        "MASTERMIND_VPS_LIVE_DATA_PATH": str(live_data), "MASTERMIND_VPS_KEY": str(key),
        "MASTERMIND_VPS_SERVICE": "fixture.service", "MASTERMIND_VPS_HEALTH": "http://fixture.invalid/health",
        "MASTERMIND_DEPLOY_LOG": str(tmp_path / "deploy.log"), "FAKE_ROOT": str(tmp_path),
        "FAKE_REMOTE": str(remote), "FAKE_LIVE_DATA": str(live_data), "FAKE_EVENTS": str(events),
        "FAKE_GATE_EVENTS": str(tmp_path / "activation_events"), "FAKE_EXPECTED": new_sha,
        "FAKE_REAL_RSYNC": real_rsync, "FAKE_REAL_CP": shutil.which("cp") or "/bin/cp",
        "FAKE_RSYNC_PEER_BIN": str(rsync_peer_bin),
        "FAKE_REAL_FIND": shutil.which("find") or "/usr/bin/find",
        "FAKE_FAIL_NEW": "1" if fail_new_release else "0",
    })
    return env, events, old_sha, new_sha


def _run_deploy(env):
    return subprocess.run(["bash", str(DEPLOY_SCRIPT)], env=env, text=True,
                          capture_output=True, check=False, timeout=45)


def _transport_events(tmp_path):
    import json
    path = tmp_path / "transport_events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_integrity_stops_service_before_source_copy(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    result = _run_deploy(env)
    assert result.returncode == 0, result.stdout + result.stderr
    copies = [item for item in _transport_events(tmp_path) if item["event"] in {"forward", "snapshot", "restore"}]
    assert copies and all(item["service"] == "inactive" for item in copies), copies


def test_integrity_restores_unlisted_and_receiver_deleted_paths(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    remote, source = tmp_path / "remote", tmp_path / "source"
    (remote / "docs").mkdir(); (remote / "docs/obsolete.md").write_text("receiver-only-old\n")
    (remote / "CLAUDE.md").write_text("old-instructions\n")
    (source / "CLAUDE.md").write_text("new-instructions\n")
    (source / "research").mkdir(); (source / "research/new.md").write_text("new-only\n")
    env["FAKE_RSYNC_PARTIAL"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert (remote / "docs/obsolete.md").read_text() == "receiver-only-old\n"
    assert (remote / "CLAUDE.md").read_text() == "old-instructions\n"
    assert not (remote / "research/new.md").exists()


def test_integrity_snapshot_failure_cannot_authorize_source_mutation(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_FAIL_SNAPSHOT"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not any(item["event"] == "forward" for item in _transport_events(tmp_path))
    assert (tmp_path / "remote/app/old.py").read_text() == "old\n"


def test_integrity_failed_restored_health_is_not_complete(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=True)
    env["FAKE_FAIL_OLD_HEALTH"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    assert "rollback complete" not in result.stdout
    assert "recovery incomplete" in result.stdout


def test_integrity_refused_init_preserves_foreign_marker(tmp_path):
    import json
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_FOREIGN_INIT"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    marker = tmp_path / "live-data/portfolio_forward_evaluation/start.json"
    assert marker.exists(), result.stdout + result.stderr
    assert json.loads(marker.read_text())["foreign"] is True
    assert "reconciliation required" in result.stdout


def test_integrity_excluded_descendants_survive_rollback(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    (tmp_path / "remote/app/.env").write_text("old-protected-value\n")
    env.update(FAKE_RSYNC_PARTIAL="1", FAKE_CHANGE_EXCLUDED="1")
    result = _run_deploy(env)
    assert result.returncode == 1
    assert (tmp_path / "remote/app/.env").read_text() == "newer-protected-value\n"


@pytest.mark.parametrize("flag", ["FAKE_STOP_FAIL", "FAKE_STOP_STAYS_ACTIVE"])
def test_integrity_unverified_stop_never_copies_source(tmp_path, flag):
    env, events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env[flag] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not any(item["event"] in {"forward", "snapshot", "restore"} for item in _transport_events(tmp_path))
    assert not events.exists()
    assert (tmp_path / "remote/app/old.py").read_text() == "old\n"
    assert "service stop is unverified" in result.stdout


def test_integrity_failed_snapshot_preserves_previous_backup_and_availability(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    prior = tmp_path / "remote/.deploy_prev/prior-complete/artifact"
    prior.parent.mkdir(parents=True)
    prior.write_bytes(b"prior verified snapshot\n")
    env["FAKE_FAIL_SNAPSHOT"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    assert prior.read_bytes() == b"prior verified snapshot\n"
    assert events.read_text().splitlines() == [old_sha]
    assert "incomplete snapshots are not used" in result.stdout
    assert not any(item["event"] == "restore" for item in _transport_events(tmp_path))


@pytest.mark.parametrize("failure", ["copy", "health"])
def test_integrity_failed_restore_never_restarts_partial_tree(tmp_path, failure):
    env, events, _old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=failure == "health")
    env["FAKE_FAIL_RESTORE"] = "1"
    if failure == "copy":
        env["FAKE_RSYNC_PARTIAL"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    assert (tmp_path / "remote/app/old.py").read_text() == "partial-restore\n"
    assert (tmp_path / "service_state").read_text() == "inactive"
    assert (events.read_text().splitlines() if events.exists() else []) == ([new_sha] if failure == "health" else [])
    assert "leaving service stopped" in result.stdout
    assert "rollback complete" not in result.stdout


def test_integrity_checksum_restores_same_size_and_mtime_content(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    old = tmp_path / "remote/app/old.py"
    new = tmp_path / "source/app/old.py"
    old.write_text("old\n"); new.write_text("NEW\n")
    os.utime(old, (1700000000, 1700000000))
    os.utime(new, (1700000000, 1700000000))
    assert old.stat().st_size == new.stat().st_size and old.stat().st_mtime_ns == new.stat().st_mtime_ns
    env["FAKE_RSYNC_PARTIAL"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert old.read_bytes() == b"old\n"
    assert events.read_text().splitlines() == [old_sha]


def _established_marker(tmp_path):
    import json
    path = tmp_path / "live-data/portfolio_forward_evaluation/start.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"release_state": "active", "deployment_sha": "3" * 40,
                               "health_verified_sha": "3" * 40, "evaluation_start": "2026-08-11",
                               "historical_baseline": "preserve exactly"}, sort_keys=True) + "\n")
    return path


def test_integrity_active_cohort_is_preserved_across_upgrade_and_noop(tmp_path):
    env, events, _old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    marker = _established_marker(tmp_path)
    original = marker.read_bytes()
    result = _run_deploy(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_bytes() == original
    assert events.read_text().splitlines() == [new_sha]
    gate_events = (tmp_path / "activation_events").read_text().splitlines()
    assert "init" not in gate_events and "finalize" not in gate_events
    before = list(_transport_events(tmp_path))
    repeated = _run_deploy(env)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert "deploy no-op" in repeated.stdout
    assert _transport_events(tmp_path) == before
    assert marker.read_bytes() == original


@pytest.mark.parametrize("field", ["account.json", "fills.jsonl"])
def test_integrity_active_cohort_authority_mutation_requires_reconciliation(tmp_path, field):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    marker = _established_marker(tmp_path)
    original_marker = marker.read_bytes()
    authority = tmp_path / "live-data/portfolios/autonomous" / field
    original_authority = authority.read_bytes()
    env["FAKE_MUTATE_" + ("ACCOUNT" if field == "account.json" else "FILLS") + "_ON_RESTART"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert events.read_text().splitlines() == [new_sha, old_sha]
    assert (tmp_path / "remote/app/old.py").read_text() == "old\n"
    assert marker.read_bytes() == original_marker
    assert authority.read_bytes() == original_authority + b"mutated\n"
    assert "authority bytes changed, missing, unreadable, or lock verification failed" in result.stdout
    assert "recovery incomplete" in result.stdout, result.stdout + result.stderr
    assert "authority/state reconciliation required" in result.stdout
    assert "rollback complete" not in result.stdout


def test_integrity_disappearing_active_cohort_is_not_reinitialized(tmp_path):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    marker = _established_marker(tmp_path)
    env["FAKE_REMOVE_ACTIVE_ON_FORWARD"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not marker.exists()
    assert "init" not in (tmp_path / "activation_events").read_text().splitlines()
    assert "established forward evaluation marker changed" in result.stdout
    assert "reconciliation required" in result.stdout


@pytest.mark.parametrize("failure", ["FAKE_LOST_INIT_REPLY", "FAKE_LOST_FINALIZE_REPLY", "FAKE_FAIL_STATUS"])
def test_integrity_unknown_cohort_effects_are_retained(tmp_path, failure):
    env, _events, _old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env[failure] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    marker = tmp_path / "live-data/portfolio_forward_evaluation/start.json"
    assert marker.exists(), result.stdout + result.stderr
    assert "reconciliation required" in result.stdout
    assert "rollback complete" not in result.stdout


@pytest.mark.parametrize("preexisting", [False, True])
def test_integrity_failed_tag_refresh_restores_exact_preimage(tmp_path, preexisting):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    dropin = tmp_path / "systemd/fixture.service.d"
    dropin.mkdir(parents=True)
    (dropin / "80-datadog.conf").write_text("fixture enabled\n")
    version = dropin / "81-datadog-version.conf"
    prior = b"[Service]\n# preserve custom prior bytes\nEnvironment=DD_VERSION=prior-special\n"
    if preexisting:
        version.write_bytes(prior)
    scripts = tmp_path / "source/scripts"
    scripts.mkdir()
    _write_executable(scripts / "refresh_datadog_release_tag.sh", '''#!/usr/bin/env bash
set -euo pipefail
[[ "$MASTERMIND_SERVICE" == fixture.service ]]
printf '[Service]\\nEnvironment=DD_VERSION=failed-new\\n' >"$FAKE_ROOT/systemd/$MASTERMIND_SERVICE.d/81-datadog-version.conf"
exit 33
''')
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert events.read_text().splitlines() == [old_sha]
    if preexisting:
        assert version.read_bytes() == prior
    else:
        assert not version.exists()
    assert "Datadog release tag refresh failed" in result.stdout


def test_integrity_sigterm_after_copy_restores_once(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_TERM_DURING_FORWARD"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 143, result.stdout + result.stderr
    assert events.read_text().splitlines() == [old_sha]
    assert (tmp_path / "remote/app/old.py").read_text() == "old\n"
    assert sum(item["event"] == "restore" for item in _transport_events(tmp_path)) == 1
    assert "interrupted by SIGTERM" in result.stdout


def test_integrity_symlinked_snapshot_root_is_refused(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    other = tmp_path / "outside-backup"
    other.mkdir()
    sentinel = other / "sentinel"
    sentinel.write_text("unchanged\n")
    (tmp_path / "remote/.deploy_prev").symlink_to(other, target_is_directory=True)
    result = _run_deploy(env)
    assert result.returncode == 1
    assert list(other.iterdir()) == [sentinel]
    assert sentinel.read_text() == "unchanged\n"
    assert events.read_text().splitlines() == [old_sha]
    assert not any(item["event"] == "forward" for item in _transport_events(tmp_path))


def test_integrity_failed_target_stop_prevents_rollback_copy(tmp_path):
    env, events, _old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=True)
    env["FAKE_ROLLBACK_STOP_FAIL"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1
    assert (tmp_path / "service_state").read_text() == "active"
    assert (tmp_path / "remote/app/old.py").read_text() == "new-release\n"
    assert events.read_text().splitlines() == [new_sha]
    assert not any(item["event"] == "restore" for item in _transport_events(tmp_path))
    assert "service stop is unverified; source was not restored" in result.stdout


@pytest.mark.parametrize("entry_kind", ["directory", "dangling_symlink"])
def test_integrity_receipt_glob_entries_cannot_masquerade_as_empty(tmp_path, entry_kind):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    receipt = tmp_path / "live-data/portfolios/hk/settlement_receipts/unreadable.json"
    receipt.parent.mkdir(parents=True)
    if entry_kind == "directory":
        receipt.mkdir()
    else:
        receipt.symlink_to(receipt.parent / "missing-target")
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert events.read_text().splitlines() == [old_sha]
    assert "unresolved paper settlement state" in result.stdout
    assert not any(item["event"] == "forward" for item in _transport_events(tmp_path))


def test_integrity_silent_receipt_scan_failure_never_authorizes_copy(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    receipts = tmp_path / "live-data/portfolios/china/settlement_receipts"
    receipts.mkdir(parents=True)
    env["FAKE_SILENT_RECEIPT_SCAN_FAILURE"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert events.read_text().splitlines() == [old_sha]
    assert "unresolved paper settlement state" in result.stdout
    assert not any(item["event"] == "forward" for item in _transport_events(tmp_path))


def test_integrity_new_package_with_excluded_cache_fails_restore_closed(tmp_path):
    env, events, _old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=True)
    source_package = tmp_path / "source/new_package"
    source_package.mkdir()
    (source_package / "module.py").write_text("new-package\n")
    env["FAKE_CREATE_EXCLUDED_CACHE_ON_RESTART"] = "1"
    result = _run_deploy(env)
    assert result.returncode == 1, result.stdout + result.stderr
    remote_package = tmp_path / "remote/new_package"
    assert not (remote_package / "module.py").exists()
    assert (remote_package / "__pycache__/x.pyc").read_bytes() == b"protected startup cache\n"
    assert (tmp_path / "remote/app/old.py").read_text() == "old\n"
    # The protected descendant prevents deleting its newly introduced container.
    # That filtered-tree difference cannot be called a verified exact rollback.
    assert "restoration failed verification; leaving service stopped" in result.stdout
    assert (tmp_path / "service_state").read_text() == "inactive"
    assert events.read_text().splitlines() == [new_sha]
    assert "rollback complete" not in result.stdout



def test_deploy_writes_expected_marker_before_restart(tmp_path):
    env, events, _old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha]
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == new_sha
    assert (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()
    assert not (tmp_path / "remote" / "data" / "portfolio_forward_evaluation").exists()
    assert (tmp_path / "activation_events").read_text(encoding="utf-8").splitlines() == [
        "stop", "init", "restart", "flock:-x -w 30 9", "finalize", "status",
    ]


def test_activation_gate_order_and_canonical_lock_are_explicit():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    stop = script.index("systemctl stop '$SVC'")
    baseline = script.index("FORWARD_BASELINE_HASHES=", stop)
    restart = script.index("systemctl restart '$SVC'", baseline)
    lock = script.index("lock_path='$LIVE_DATA_PATH/locks/book:autonomous.lock'", restart)
    compare_account = script.index(r"[ \"\$account_sha\" = '$FORWARD_ACCOUNT_SHA' ]", lock)
    compare_fills = script.index(r"[ \"\$fills_sha\" = '$FORWARD_FILLS_SHA' ]", lock)
    finalize = script.index("portfolio.forward_evaluation finalize", compare_fills)
    status = script.index("portfolio.forward_evaluation status", finalize)
    assert stop < baseline < restart < lock < compare_account < compare_fills < finalize < status
    assert r'exec 9>>\"\$lock_path\"' in script
    assert "flock -x -w 30 9" in script


@pytest.mark.parametrize("artifact", ["paper_transaction.json", "settlement_receipts/old.json"])
def test_deploy_refuses_unresolved_pre_v2_settlement_state(tmp_path, artifact):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    path = tmp_path / "live-data" / "portfolios" / "china" / artifact
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    # The service is stopped before the runtime-state gate and only the bounded rollback restart
    # occurs; the incompatible release is never started.
    assert events.read_text(encoding="utf-8").splitlines() == [old_sha]
    assert "unresolved paper settlement state blocks receipt-schema upgrade" in result.stdout
    assert not (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()


@pytest.mark.parametrize("mutation_flag", [
    "FAKE_MUTATE_ACCOUNT_ON_RESTART",
    "FAKE_MUTATE_FILLS_ON_RESTART",
])
def test_activation_rejects_account_or_fills_byte_mutation(tmp_path, mutation_flag):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env[mutation_flag] = "1"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert "authority bytes changed, missing, unreadable, or lock verification failed" in result.stdout
    gate_events = (tmp_path / "activation_events").read_text(encoding="utf-8").splitlines()
    assert "flock:-x -w 30 9" in gate_events
    assert "finalize" not in gate_events
    assert (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()
    assert "reconciliation required" in result.stdout


def test_activation_rejects_missing_authority_file(tmp_path):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_REMOVE_AUTHORITY_ON_RESTART"] = "fills"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert "authority bytes changed, missing, unreadable, or lock verification failed" in result.stdout
    gate_events = (tmp_path / "activation_events").read_text(encoding="utf-8").splitlines()
    assert "flock:-x -w 30 9" in gate_events
    assert "finalize" not in gate_events


def test_failed_deploy_restores_code_marker_and_retains_pending_cohort(tmp_path):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=True)
    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()
    assert "code health restored" in result.stdout
    assert "reconciliation required" in result.stdout
    assert "rollback complete" not in result.stdout


def test_partial_rsync_failure_restores_old_tree_and_restarts(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_RSYNC_PARTIAL"] = "1"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert (tmp_path / "remote" / "app" / "old.py").read_text() == "old\n"
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert events.read_text(encoding="utf-8").splitlines() == [old_sha]
    assert "rsync did not complete; rolling back" in result.stdout


def test_marker_write_failure_uses_post_backup_rollback(tmp_path):
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_FAIL_MARKER"] = "1"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert events.read_text(encoding="utf-8").splitlines() == [old_sha]
    assert "release marker write failed; rolling back" in result.stdout


def test_restart_failure_restores_marker_and_attempts_rollback_restart(tmp_path):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_FAIL_RESTART_ONCE"] = "1"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert "service restart failed; rolling back" in result.stdout


def test_deploy_rejects_health_when_scheduler_is_not_running(tmp_path):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=False)
    env["FAKE_SCHEDULER_OK"] = "false"

    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert "health check returned 503; rolling back" in result.stdout


@pytest.mark.parametrize("package", ["common", "integrations"])
@pytest.mark.parametrize("preexisting", [False, True])
def test_partial_copy_rolls_back_shared_runtime_packages(tmp_path, package, preexisting):
    """Whole-source rsync ships these packages; rollback must cover them too."""
    env, events, old_sha, _new_sha = _fake_transport(tmp_path, fail_new_release=False)
    remote = tmp_path / "remote"
    package_dir = remote / package
    if preexisting:
        package_dir.mkdir()
        (package_dir / "module.py").write_text("old-package\n", encoding="utf-8")
    source_package = tmp_path / "source" / package
    source_package.mkdir()
    (source_package / "module.py").write_text("new-package\n")
    (source_package / "introduced.py").write_text("new-only\n")
    env["FAKE_RSYNC_PARTIAL"] = "1"
    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "rsync did not complete" in result.stdout
    assert events.read_text().splitlines() == [old_sha]
    assert (remote / ".deployed_git_sha").read_text().strip() == old_sha
    if preexisting:
        assert (package_dir / "module.py").read_text() == "old-package\n"
        assert not (package_dir / "introduced.py").exists()
    else:
        assert not package_dir.exists()
    # The failure must not touch the separate authoritative book data.
    assert (tmp_path / "live-data/portfolios/autonomous/account.json").read_text() == '{"cash":1000000}\n'
