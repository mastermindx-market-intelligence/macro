from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "runner-host" / "pc" / "mastermind_ci_cache_update.sh"
SERVICE = ROOT / "ops" / "runner-host" / "pc" / "mastermind-ci-cache-update.service"
TIMER = ROOT / "ops" / "runner-host" / "pc" / "mastermind-ci-cache-update.timer"
VALIDATED_REF = "refs/mastermind/cache-validated-main"
CANDIDATE_REF = "refs/mastermind/cache-update-candidate"


def git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise AssertionError(
            f"git {' '.join(args)} failed ({result.returncode}):\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result.stdout.strip()


def commit(source: Path, message: str, contents: str) -> str:
    (source / "tracked.txt").write_text(contents, encoding="utf-8")
    git(source, "add", "tracked.txt")
    git(source, "commit", "-m", message)
    return git(source, "rev-parse", "HEAD")


def cache_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Cache Test")
    git(source, "config", "user.email", "cache@example.invalid")
    first = commit(source, "seed", "seed\n")

    cache = tmp_path / "cache.git"
    subprocess.run(
        ["git", "clone", "--bare", str(source), str(cache)],
        text=True,
        capture_output=True,
        check=True,
    )
    git(cache, "remote", "set-url", "origin", str(source))
    # Production keeps the normal remote-tracking refmap. The updater's staging
    # fetch must explicitly suppress it or `origin/main` moves before validation.
    git(cache, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
    git(cache, "update-ref", "refs/remotes/origin/main", first)
    (cache / ".mastermind-cache-identity.json").write_text(
        '{"schema":"mastermind.ci_git_cache.v1",'
        '"repository":"mastermindx-market-intelligence/macro"}\n',
        encoding="utf-8",
    )
    return source, cache, first


def tool_path(
    tmp_path: Path,
    *,
    log: Path | None = None,
    fail_batch_check: bool = False,
    drift_before_transaction: bool = False,
) -> Path:
    """Supply deterministic `flock` and an optional logging Git wrapper on macOS."""
    tools = tmp_path / "tools"
    tools.mkdir(exist_ok=True)
    flock = tools / "flock"
    flock.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    flock.chmod(flock.stat().st_mode | stat.S_IXUSR)

    if log is not None or fail_batch_check or drift_before_transaction:
        real_git = shutil.which("git")
        assert real_git
        wrapper = tools / "git"
        wrapper.write_text(
            "#!/bin/sh\n"
            'if [ -n "${GIT_COMMAND_LOG:-}" ]; then\n'
            '  printf "%s\\n" "$*" >> "$GIT_COMMAND_LOG"\n'
            "fi\n"
            'case " $* " in\n'
            '  *" cat-file --batch-check "*)\n'
            '    if [ "${FAIL_BATCH_CHECK:-0}" = 1 ]; then\n'
            '      IFS= read -r first || exit 1\n'
            '      cat >/dev/null\n'
            '      printf "%s missing\\n" "$first"\n'
            '      exit 0\n'
            '    fi\n'
            '    ;;\n'
            '  *" update-ref --stdin "*)\n'
            '    if [ "${DRIFT_BEFORE_TRANSACTION:-0}" = 1 ]; then\n'
            '      git_dir=\n'
            '      for arg in "$@"; do\n'
            '        case "$arg" in --git-dir=*) git_dir=${arg#--git-dir=} ;; esac\n'
            '      done\n'
            '      [ -n "$git_dir" ] || exit 97\n'
            f'      {shlex.quote(real_git)} --git-dir="$git_dir" update-ref refs/remotes/origin/main "$DRIFT_OID"\n'
            '    fi\n'
            '    ;;\n'
            'esac\n'
            f"exec {shlex.quote(real_git)} \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    return tools


def run_update(
    tmp_path: Path,
    cache: Path,
    *,
    log: Path | None = None,
    fail_batch_check: bool = False,
    drift_oid: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = str(
        tool_path(
            tmp_path,
            log=log,
            fail_batch_check=fail_batch_check,
            drift_before_transaction=drift_oid is not None,
        )
    ) + os.pathsep + env["PATH"]
    if log is not None:
        env["GIT_COMMAND_LOG"] = str(log)
    if fail_batch_check:
        env["FAIL_BATCH_CHECK"] = "1"
    if drift_oid is not None:
        env["DRIFT_BEFORE_TRANSACTION"] = "1"
        env["DRIFT_OID"] = drift_oid
    return subprocess.run(
        [str(SCRIPT), str(cache), str(tmp_path / "cache-update.lock")],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def ref(cache: Path, name: str) -> str | None:
    result = subprocess.run(
        ["git", "--git-dir", str(cache), "show-ref", "--verify", "--hash", name],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def mark_legacy_validation(cache: Path) -> None:
    (cache / ".last-update-ok").touch()


def test_legacy_success_marker_alone_never_mints_a_validation_boundary(tmp_path: Path) -> None:
    _, cache, first = cache_fixture(tmp_path)
    mark_legacy_validation(cache)

    result = run_update(tmp_path, cache)

    assert result.returncode != 0
    assert "validation boundary" in (result.stdout + result.stderr).lower()
    assert ref(cache, VALIDATED_REF) is None
    assert ref(cache, "refs/heads/main") == first
    assert ref(cache, "refs/remotes/origin/main") == first
    assert ref(cache, CANDIDATE_REF) is None


def test_explicit_validated_ref_bootstraps_without_a_legacy_marker(tmp_path: Path) -> None:
    _, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)

    result = run_update(tmp_path, cache)

    assert result.returncode == 0, result.stdout + result.stderr
    assert ref(cache, VALIDATED_REF) == first
    assert (cache / ".last-update-ok").is_file()


def test_fast_forward_delta_is_validated_then_all_publication_refs_advance(
    tmp_path: Path,
) -> None:
    source, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)
    second = commit(source, "advance", "second\n")

    result = run_update(tmp_path, cache)

    assert result.returncode == 0, result.stdout + result.stderr
    assert ref(cache, "refs/heads/main") == second
    assert ref(cache, "refs/remotes/origin/main") == second
    assert ref(cache, VALIDATED_REF) == second
    assert ref(cache, CANDIDATE_REF) is None
    assert git(cache, "merge-base", "--is-ancestor", first, second) == ""


def test_missing_validation_boundary_refuses_without_advancing_main(tmp_path: Path) -> None:
    source, cache, first = cache_fixture(tmp_path)
    second = commit(source, "untrusted advance", "second\n")
    assert second != first

    result = run_update(tmp_path, cache)

    assert result.returncode != 0
    assert "validation boundary" in (result.stdout + result.stderr).lower()
    assert ref(cache, "refs/heads/main") == first
    assert ref(cache, VALIDATED_REF) is None
    assert ref(cache, CANDIDATE_REF) is None


def test_missing_candidate_object_refuses_and_leaves_publication_refs_unchanged(
    tmp_path: Path,
) -> None:
    source, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)
    commit(source, "candidate with missing object", "second\n")

    result = run_update(tmp_path, cache, fail_batch_check=True)

    assert result.returncode != 0
    assert "missing objects" in (result.stdout + result.stderr).lower()
    assert ref(cache, "refs/heads/main") == first
    assert ref(cache, "refs/remotes/origin/main") == first
    assert ref(cache, VALIDATED_REF) == first
    assert ref(cache, CANDIDATE_REF) is None
    assert not (cache / ".last-update-ok").exists()


def test_validation_ref_drift_refuses_before_fetching_or_publishing(tmp_path: Path) -> None:
    source, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)
    second = commit(source, "manual drift", "second\n")
    git(
        cache,
        "fetch",
        "--refmap=",
        "origin",
        f"+{second}:refs/mastermind/manual-drift",
    )
    git(cache, "update-ref", "refs/heads/main", second, first)
    git(cache, "update-ref", "refs/remotes/origin/main", second, first)

    result = run_update(tmp_path, cache)

    assert result.returncode != 0
    assert "validation boundary" in (result.stdout + result.stderr).lower()
    assert ref(cache, "refs/heads/main") == second
    assert ref(cache, "refs/remotes/origin/main") == second
    assert ref(cache, VALIDATED_REF) == first
    assert ref(cache, CANDIDATE_REF) is None


def test_atomic_publication_refuses_a_concurrent_ref_change(tmp_path: Path) -> None:
    source, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)
    second = commit(source, "candidate for publication race", "second\n")

    result = run_update(tmp_path, cache, drift_oid=second)

    assert result.returncode != 0
    assert "cannot lock ref" in (result.stdout + result.stderr).lower()
    assert ref(cache, "refs/heads/main") == first
    assert ref(cache, "refs/remotes/origin/main") == second
    assert ref(cache, VALIDATED_REF) == first
    assert ref(cache, CANDIDATE_REF) is None
    assert not (cache / ".last-update-ok").exists()


def test_non_fast_forward_candidate_refuses_without_moving_active_refs(
    tmp_path: Path,
) -> None:
    source, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)

    git(source, "checkout", "--orphan", "replacement")
    git(source, "rm", "-rf", ".")
    replacement = commit(source, "replacement root", "replacement\n")
    git(source, "branch", "-M", "main")
    assert replacement != first

    result = run_update(tmp_path, cache)

    assert result.returncode != 0
    assert "non-fast-forward" in (result.stdout + result.stderr).lower()
    assert ref(cache, "refs/heads/main") == first
    assert ref(cache, "refs/remotes/origin/main") == first
    assert ref(cache, VALIDATED_REF) == first
    assert ref(cache, CANDIDATE_REF) is None


def test_unchanged_main_skips_reachable_estate_enumeration(tmp_path: Path) -> None:
    _, cache, first = cache_fixture(tmp_path)
    git(cache, "update-ref", VALIDATED_REF, first)
    log = tmp_path / "git-commands.log"

    result = run_update(tmp_path, cache, log=log)

    assert result.returncode == 0, result.stdout + result.stderr
    commands = log.read_text(encoding="utf-8")
    assert "rev-list --objects" not in commands
    assert "cat-file --batch-check" not in commands


def test_cache_update_disables_automatic_git_maintenance() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "fetch --no-auto-maintenance" in script
    assert "config gc.auto 0" in script
    assert "config maintenance.auto false" in script
    assert "git gc" not in script
    assert "git repack" not in script
    assert "git prune" not in script


def test_cache_update_service_is_bounded_below_runner_and_render_capacity() -> None:
    unit = SERVICE.read_text(encoding="utf-8")
    assert "Nice=10" in unit
    assert "IOSchedulingClass=idle" in unit
    assert "IOSchedulingPriority=7" in unit
    assert "CPUQuota=100%" in unit
    assert "MemoryHigh=2G" in unit
    assert "MemoryMax=4G" in unit
    assert "TimeoutStartSec=5min" in unit
    assert "Slice=mastermind-ci.slice" not in unit


def test_cache_update_timer_spaces_runs_from_service_completion() -> None:
    timer = TIMER.read_text(encoding="utf-8")
    assert "OnUnitInactiveSec=3min" in timer
    assert "OnUnitActiveSec" not in timer
    assert "RandomizedDelaySec=30s" in timer
