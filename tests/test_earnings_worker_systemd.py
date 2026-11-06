import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "ops/systemd/mastermind-earnings-worker.service"
TIMER = ROOT / "ops/systemd/mastermind-earnings-worker.timer"
BOOTSTRAP = ROOT / "ops/bootstrap_earnings_worker_linux.sh"


def test_linux_service_reuses_existing_worker_and_inference_owner():
    text = SERVICE.read_text()
    for required in (
        "User=longr",
        "WorkingDirectory=/opt/mastermind-earnings/macro",
        "Slice=mastermind-inference.slice",
        "CPUWeight=10",
        "IOWeight=10",
        "Nice=10",
        "IOSchedulingClass=idle",
        "After=network-online.target mastermind-inference-guard.service",
        "run_with_env.sh /etc/mastermind/earnings-worker.env",
        "run_earnings_worker.sh",
        "ProtectSystem=strict",
        "NoNewPrivileges=true",
        "ReadWritePaths=/opt/mastermind-earnings/macro /var/lib/mastermind-earnings /run/lock",
    ):
        assert required in text


def test_linux_timer_is_primary_ten_minutes_before_mac_fallback():
    text = TIMER.read_text()
    for when in ("17:35:00", "20:35:00", "23:35:00"):
        assert f"OnCalendar=*-*-* {when}" in text
    assert text.count("OnCalendar=") == 3
    assert "Persistent=true" in text
    assert "Unit=mastermind-earnings-worker.service" in text


def test_bootstrap_reuses_plane_without_embedding_secrets():
    text = BOOTSTRAP.read_text()
    for required in (
        "/etc/mastermind/earnings-worker.env",
        "ops/launchd/run_earnings_worker.sh",
        "ops/launchd/run_with_env.sh",
        "ops/earnings_worker_requirements.txt",
        "mastermind-inference-guard.service",
        "systemctl enable --now",
        "--ff-only",
    ):
        assert required in text
    assert "git push" not in text
    assert "git commit" not in text


def test_units_contain_no_secret_values_or_second_router():
    combined = SERVICE.read_text() + TIMER.read_text()
    for token in ("R2_SECRET_ACCESS_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "MOONSHOT_API_KEY"):
        assert token not in combined
    assert "ollama serve" not in combined
    assert "11434" not in combined
    assert "11435" not in combined


def _reject_unsupported_configuration(overrides=None, *, user="longr", group="longr"):
    """Run the real preflight with every effectful external command fenced."""
    with tempfile.TemporaryDirectory(prefix="earnings-bootstrap-preflight-") as raw:
        root = Path(raw)
        calls = root / "unexpected-effects"
        stub = root / "bin"
        stub.mkdir()
        (stub / "id").write_text(
            '#!/bin/bash\ncase "$1" in\n'
            '  -un) printf "%s\\n" "$MMX_BOOTSTRAP_TEST_USER" ;;\n'
            '  -gn) printf "%s\\n" "$MMX_BOOTSTRAP_TEST_GROUP" ;;\n'
            '  *) exit 91 ;;\nesac\n'
        )
        (stub / "id").chmod(0o755)
        for name in ("sudo", "git", "python3", "systemctl"):
            target = stub / name
            target.write_text(
                '#!/bin/bash\nprintf "%s\\n" "$0" >> "$MMX_BOOTSTRAP_TEST_CALLS"\nexit 91\n'
            )
            target.chmod(0o755)
        environment = {
            "PATH": str(stub) + os.pathsep + os.defpath,
            "MMX_BOOTSTRAP_TEST_USER": user,
            "MMX_BOOTSTRAP_TEST_GROUP": group,
            "MMX_BOOTSTRAP_TEST_CALLS": str(calls),
        }
        environment.update(overrides or {})
        result = subprocess.run(
            ["/bin/bash", str(BOOTSTRAP)],
            env=environment, text=True, capture_output=True, timeout=10,
        )
        assert result.returncode == 1, (result.returncode, result.stderr)
        assert "fixed earnings service requires" in result.stderr
        assert not calls.exists(), "An installation effect preceded configuration rejection"


def test_bootstrap_rejects_noncanonical_paths_and_identity_before_effects():
    for variable in (
        "EARNINGS_OPS_ROOT", "EARNINGS_VENV_ROOT",
        "EARNINGS_RUNTIME_ROOT", "EARNINGS_ENV_FILE",
    ):
        _reject_unsupported_configuration({variable: "/tmp/unsupported-earnings-layout"})
    _reject_unsupported_configuration(user="different-user")
    _reject_unsupported_configuration(group="different-group")


# All filesystem predicates for the fixed installation and all external effect
# commands are simulated. The only real files read are this PR's source files.
# No host clone, package, credential, provider, unit, or timer is touched.
_SIMULATED_COMMANDS = r"""
record() { printf 'MMX_TRACE:%s\n' "$*"; }
id() {
  case "$1" in -un|-gn) printf 'longr\n' ;; *) return 91 ;; esac
}
function [() {
  case "$1:$2" in
    -d:/opt/mastermind-earnings/*|-f:/opt/mastermind-earnings/*|-x:/opt/mastermind-earnings/*)
      return 0 ;;
    -f:/etc/mastermind/earnings-worker.env) return 0 ;;
    *) builtin [ "$@" ;;
  esac
}
git() {
  case "$*" in
    *' rev-parse --show-toplevel') printf '/opt/mastermind-earnings/macro\n' ;;
    *' symbolic-ref --quiet --short HEAD') printf 'main\n' ;;
    *' remote get-url origin') printf 'https://github.com/mastermindx-market-intelligence/macro.git\n' ;;
    *' status --porcelain --untracked-files=all') return 0 ;;
    *' rev-parse HEAD'|*' rev-parse origin/main') printf 'fixture-commit\n' ;;
    clone*|*' fetch origin main --quiet'|*' merge --ff-only --quiet origin/main'|*' sparse-checkout set engine lib scripts tools/earnings_worker config ops')
      record source-refresh ;;
    *) return 91 ;;
  esac
}
awk() {
  if [[ "$1" == -F= ]]; then
    printf '%s\n' R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET \
      EARNINGS_LLM_BASE_URL EARNINGS_LLM_MODEL
  else
    command awk "$@"
  fi
}
sha256sum() { printf 'fixture-hash %s\n' "$1"; }
cat() {
  if [[ "$1" == /opt/mastermind-earnings/venv/.earnings-requirements.sha256 ]]; then
    printf 'fixture-hash\n'
  else
    return 91
  fi
}
python3() { return 91; }
function /opt/mastermind-earnings/venv/bin/python() {
  record dependency-imports
  if [[ "$MMX_BOOTSTRAP_TEST_FAILURE" == imports ]]; then return 23; fi
}
cmp() {
  record unit-compare
  if [[ "$MMX_BOOTSTRAP_TEST_FAILURE" == unit ]]; then return 25; fi
}
env() {
  case "$*" in *' --check-env') ;; *) return 91 ;; esac
  record worker-environment
  if [[ "$MMX_BOOTSTRAP_TEST_FAILURE" == environment ]]; then return 24; fi
}
systemctl() {
  case "$1" in
    is-active|is-enabled) record timer-or-guard-readback ;;
    daemon-reload) record daemon-reload ;;
    enable) [[ "$2" == --now ]] || return 91; record activate-timer ;;
    start) record start-worker ;;
    show) printf 'success\n' ;;
    *) return 91 ;;
  esac
}
sudo() {
  case "$1" in
    install) record install ;;
    systemctl) shift; systemctl "$@" ;;
    *) return 91 ;;
  esac
}
"""


def _simulate_bootstrap(*arguments, failure="none"):
    command = _SIMULATED_COMMANDS + '\nrunner_source="$1"\nshift\nsource "$runner_source" "$@"\n'
    result = subprocess.run(
        ["/bin/bash", "-c", command, "fixture", str(BOOTSTRAP), *arguments],
        env={"PATH": os.defpath, "MMX_BOOTSTRAP_TEST_FAILURE": failure},
        text=True, capture_output=True, timeout=10,
    )
    events = [
        line.removeprefix("MMX_TRACE:")
        for line in result.stdout.splitlines() if line.startswith("MMX_TRACE:")
    ]
    return result, events


def test_bootstrap_validation_failures_never_activate_timer():
    for failure, code, check in (
        ("imports", 23, "dependency-imports"),
        ("unit", 25, "unit-compare"),
        ("environment", 24, "worker-environment"),
    ):
        result, events = _simulate_bootstrap(failure=failure)
        assert result.returncode == code, (failure, result.stderr, events)
        assert check in events
        assert "activate-timer" not in events
        assert "start-worker" not in events


def test_bootstrap_check_mode_performs_no_install_or_activation():
    result, events = _simulate_bootstrap("--check")
    assert result.returncode == 0, (result.stderr, events)
    assert {"dependency-imports", "unit-compare", "worker-environment"} <= set(events)
    assert not {"install", "source-refresh", "daemon-reload", "activate-timer", "start-worker"} & set(events)


def test_bootstrap_activates_only_after_validation_and_runs_explicitly_last():
    result, events = _simulate_bootstrap("--run-now")
    assert result.returncode == 0, (result.stderr, events)
    assert events.count("activate-timer") == 1
    for check in ("dependency-imports", "unit-compare", "worker-environment"):
        assert events.index(check) < events.index("activate-timer")
    assert events.index("activate-timer") < events.index("start-worker")
