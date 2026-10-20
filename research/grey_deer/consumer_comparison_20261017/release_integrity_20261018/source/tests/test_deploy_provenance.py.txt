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
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    remote = tmp_path / "remote"
    (remote / "app").mkdir(parents=True)
    live_data = tmp_path / "live-data"
    live_data.mkdir()
    autonomous = live_data / "portfolios" / "autonomous"
    autonomous.mkdir(parents=True)
    (autonomous / "account.json").write_text('{"cash":1000000}\n', encoding="utf-8")
    (autonomous / "fills.jsonl").write_text(
        '{"date":"2026-08-11","ticker":"AAPL","side":"buy"}\n', encoding="utf-8"
    )
    (remote / "app" / "old.py").write_text("old\n", encoding="utf-8")
    source = tmp_path / "source"
    source.mkdir()
    key = tmp_path / "deploy_key"
    key.write_text("fixture-only\n", encoding="utf-8")
    events = tmp_path / "restart_events"
    old_sha = "1" * 40
    new_sha = "2" * 40
    (remote / ".deployed_git_sha").write_text(f"{old_sha}\n", encoding="utf-8")

    _write_executable(
        fake_bin / "ssh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cmd=\"${!#}\"\n"
        "if [[ \"${FAKE_FAIL_MARKER:-0}\" == 1 && \"$cmd\" == *\"printf '%s\\n'\"* "
        "&& \"$cmd\" == *\".deployed_git_sha\"* ]]; then exit 31; fi\n"
        "exec bash -c \"$cmd\"\n",
    )
    _write_executable(
        fake_bin / "python3",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "[[ \"${1:-}\" == -m && \"${2:-}\" == portfolio.forward_evaluation ]] || exit 97\n"
        "command=${3:-}\n"
        "marker=\"$FAKE_LIVE_DATA/portfolio_forward_evaluation/start.json\"\n"
        "case \"$command\" in\n"
        "  init)\n"
        "    printf 'init\\n' >>\"$FAKE_GATE_EVENTS\"\n"
        "    mkdir -p \"$(dirname \"$marker\")\"\n"
        "    if [[ -e \"$marker\" ]]; then\n"
        "      printf '{\"initialized\": false, \"release_state\": \"pending_health\"}\\n'\n"
        "    else\n"
        "      printf '{\"release_state\": \"pending_health\"}\\n' >\"$marker\"\n"
        "      printf '{\"initialized\": true, \"release_state\": \"pending_health\"}\\n'\n"
        "    fi ;;\n"
        "  finalize)\n"
        "    printf 'finalize\\n' >>\"$FAKE_GATE_EVENTS\"\n"
        "    [[ -e \"$marker\" ]] || exit 2\n"
        "    printf '{\"release_state\": \"active\"}\\n' >\"$marker\" ;;\n"
        "  status)\n"
        "    printf 'status\\n' >>\"$FAKE_GATE_EVENTS\"\n"
        "    grep -q '\"release_state\": \"active\"' \"$marker\" 2>/dev/null ;;\n"
        "  *) exit 98 ;;\n"
        "esac\n",
    )
    _write_executable(
        fake_bin / "flock",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'flock:%s\\n' \"$*\" >>\"$FAKE_GATE_EVENTS\"\n",
    )
    _write_executable(
        fake_bin / "rsync",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \" $* \" == *\" -azn \"* ]]; then printf 'app/main.py\\n'; exit 0; fi\n"
        "if [[ \"${FAKE_RSYNC_PARTIAL:-0}\" == 1 ]]; then "
        "printf 'partial-new\\n' >\"$FAKE_REMOTE/app/old.py\"; exit 23; fi\n",
    )
    _write_executable(
        fake_bin / "curl",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "sha=$(cat \"$FAKE_REMOTE/.deployed_git_sha\" 2>/dev/null || true)\n"
        "policy=true\n"
        "if [[ \"${FAKE_FAIL_NEW:-0}\" == 1 && \"$sha\" == \"$FAKE_EXPECTED\" ]]; "
        "then policy=false; fi\n"
        "scheduler_ok=${FAKE_SCHEDULER_OK:-true}\n"
        "printf '{\"reasoning_policy_ok\":%s,\"scheduled_runtime_ok\":%s,"
        "\"commit\":\"%s\"}' \"$policy\" \"$scheduler_ok\" \"$sha\"\n",
    )
    _write_executable(
        fake_bin / "systemctl",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cmd=\"$*\"\n"
        "if [[ \"$cmd\" == stop\ * ]]; then printf 'stop\\n' >>\"$FAKE_GATE_EVENTS\"; exit 0; fi\n"
        "printf 'restart\\n' >>\"$FAKE_GATE_EVENTS\"\n"
        "cat \"$FAKE_REMOTE/.deployed_git_sha\" 2>/dev/null >>\"$FAKE_EVENTS\" || "
        "printf 'missing\\n' >>\"$FAKE_EVENTS\"\n"
        "if [[ \"${FAKE_MUTATE_ACCOUNT_ON_RESTART:-0}\" == 1 "
        "&& ! -e \"$FAKE_AUTHORITY_MUTATION_STATE\" ]]; then\n"
        "  printf 'mutated\\n' >>\"$FAKE_LIVE_DATA/portfolios/autonomous/account.json\"\n"
        "  : >\"$FAKE_AUTHORITY_MUTATION_STATE\"\n"
        "fi\n"
        "if [[ \"${FAKE_MUTATE_FILLS_ON_RESTART:-0}\" == 1 "
        "&& ! -e \"$FAKE_AUTHORITY_MUTATION_STATE\" ]]; then\n"
        "  printf '{\"mutated\":true}\\n' >>\"$FAKE_LIVE_DATA/portfolios/autonomous/fills.jsonl\"\n"
        "  : >\"$FAKE_AUTHORITY_MUTATION_STATE\"\n"
        "fi\n"
        "if [[ \"${FAKE_REMOVE_AUTHORITY_ON_RESTART:-}\" == account "
        "&& ! -e \"$FAKE_AUTHORITY_MUTATION_STATE\" ]]; then\n"
        "  rm -f \"$FAKE_LIVE_DATA/portfolios/autonomous/account.json\"\n"
        "  : >\"$FAKE_AUTHORITY_MUTATION_STATE\"\n"
        "fi\n"
        "if [[ \"${FAKE_REMOVE_AUTHORITY_ON_RESTART:-}\" == fills "
        "&& ! -e \"$FAKE_AUTHORITY_MUTATION_STATE\" ]]; then\n"
        "  rm -f \"$FAKE_LIVE_DATA/portfolios/autonomous/fills.jsonl\"\n"
        "  : >\"$FAKE_AUTHORITY_MUTATION_STATE\"\n"
        "fi\n"
        "if [[ \"${FAKE_FAIL_RESTART_ONCE:-0}\" == 1 && ! -e \"$FAKE_RESTART_STATE\" ]]; "
        "then : >\"$FAKE_RESTART_STATE\"; exit 32; fi\n",
    )
    _write_executable(fake_bin / "sleep", "#!/usr/bin/env bash\nexit 0\n")

    env = dict(os.environ)
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "MASTERMIND_DEPLOY_SOURCE": f"{source}/",
            "MASTERMIND_DEPLOY_EXPECT_SHA": new_sha,
            "MASTERMIND_VPS_HOST": "fixture-host",
            "MASTERMIND_VPS_PATH": str(remote),
            "MASTERMIND_VPS_LIVE_DATA_PATH": str(live_data),
            "MASTERMIND_VPS_KEY": str(key),
            "MASTERMIND_VPS_SERVICE": "fixture.service",
            "MASTERMIND_VPS_HEALTH": "http://fixture.invalid/health",
            "MASTERMIND_DEPLOY_LOG": str(tmp_path / "deploy.log"),
            "FAKE_REMOTE": str(remote),
            "FAKE_LIVE_DATA": str(live_data),
            "FAKE_EVENTS": str(events),
            "FAKE_GATE_EVENTS": str(tmp_path / "activation_events"),
            "FAKE_EXPECTED": new_sha,
            "FAKE_FAIL_NEW": "1" if fail_new_release else "0",
            "FAKE_FAIL_MARKER": "0",
            "FAKE_RSYNC_PARTIAL": "0",
            "FAKE_FAIL_RESTART_ONCE": "0",
            "FAKE_RESTART_STATE": str(tmp_path / "restart_failed_once"),
            "FAKE_AUTHORITY_MUTATION_STATE": str(tmp_path / "authority_mutated_once"),
            "FAKE_MUTATE_ACCOUNT_ON_RESTART": "0",
            "FAKE_MUTATE_FILLS_ON_RESTART": "0",
            "FAKE_REMOVE_AUTHORITY_ON_RESTART": "",
            "FAKE_SCHEDULER_OK": "true",
        }
    )
    return env, events, old_sha, new_sha


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
    assert not (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()


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


def test_failed_deploy_restores_marker_before_rollback_restart(tmp_path):
    env, events, old_sha, new_sha = _fake_transport(tmp_path, fail_new_release=True)
    result = subprocess.run(
        ["bash", str(DEPLOY_SCRIPT)], env=env, text=True, capture_output=True, check=False
    )

    assert result.returncode == 1
    assert events.read_text(encoding="utf-8").splitlines() == [new_sha, old_sha]
    assert (tmp_path / "remote" / ".deployed_git_sha").read_text().strip() == old_sha
    assert not (tmp_path / "live-data" / "portfolio_forward_evaluation" / "start.json").exists()
    assert "rollback complete; health returned 200" in result.stdout


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
    env["FAKE_PACKAGE_NAME"] = package
    _write_executable(
        tmp_path / "bin" / "rsync",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "if [[ \" $* \" == *\" -azn \"* ]]; then printf '%s/module.py\\n' \"$FAKE_PACKAGE_NAME\"; exit 0; fi\n"
        "mkdir -p \"$FAKE_REMOTE/$FAKE_PACKAGE_NAME\"\n"
        "printf 'new-package\\n' >\"$FAKE_REMOTE/$FAKE_PACKAGE_NAME/module.py\"\n"
        "printf 'new-only\\n' >\"$FAKE_REMOTE/$FAKE_PACKAGE_NAME/introduced.py\"\n"
        "exit 23\n",
    )
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
