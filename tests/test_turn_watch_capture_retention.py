"""Native two-runner Git races for the existing engine's capture retention fence."""
from pathlib import Path
import subprocess

import pytest

from scripts.ci import turn_watch_capture_retention as retention

CAPTURE = retention.CAPTURE_ROOT + "/" + "a" * 64 + ".json"
OTHER_CAPTURE = retention.CAPTURE_ROOT + "/" + "b" * 64 + ".json"
FIRST = b'{"producer_captured_at":"2026-10-18T01:00:00Z"}\n'
SECOND = b'{"producer_captured_at":"2026-10-18T02:00:00Z"}\n'


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=check)


def write(repo, path, raw):
    out = repo / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)


def commit(repo, message):
    git(repo, "add", "--all")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip().decode()


@pytest.fixture
def runners(tmp_path, monkeypatch):
    # Real source and locked wrapper; all Git refs and publication are temporary.
    monkeypatch.setenv("GITHUB_WORKSPACE", str(retention.REPO_ROOT))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GIT_OPTIONAL_LOCKS", "0")
    monkeypatch.delenv("GIT_INDEX_FILE", raising=False)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
    first = tmp_path / "first"
    git(tmp_path, "clone", str(remote), str(first))
    for key, val in [("user.name", "Capture test"), ("user.email", "capture@example.invalid")]:
        git(first, "config", key, val)
    write(first, "seed", b"initial\n")
    commit(first, "initial")
    git(first, "push", "origin", "main")
    second = tmp_path / "second"
    git(tmp_path, "clone", str(remote), str(second))
    for key, val in [("user.name", "Capture test"), ("user.email", "capture@example.invalid")]:
        git(second, "config", key, val)
    return remote, first, second


def overlap(runners):
    remote, first, second = runners
    write(first, CAPTURE, FIRST)
    commit(first, "first producer")
    git(first, "push", "origin", "main")
    write(second, CAPTURE, SECOND)
    write(second, "data/other_engine_output.json", b'{"retain_me":true}\n')
    commit(second, "overlapping producer")
    git(second, "fetch", "origin", "main")
    git(second, "rebase", "--autostash", "-X", "theirs", "origin/main")
    assert (second / CAPTURE).read_bytes() == SECOND
    return remote, first, second


def state(repo):
    return (git(repo, "rev-parse", "HEAD").stdout,
            (repo / ".git/index").read_bytes(),
            (repo / CAPTURE).read_bytes(),
            git(repo, "status", "--porcelain=v1", "-z").stdout)


def test_overlapping_runners_preserve_first_remote_capture_and_other_outputs(runners):
    remote, _, second = overlap(runners)
    before = git(second, "rev-parse", "HEAD").stdout.strip().decode()
    with pytest.raises(ValueError, match="changes 1 retained"):
        retention.check_retained(second)
    result = retention.preserve_retained(second)
    assert result["restored_count"] == 1
    # The published commit retains main's immutable capture. A conflicting
    # local working file is left intact, never destroyed to prepare that commit.
    assert git(second, "show", "HEAD:" + CAPTURE).stdout == FIRST
    assert (second / CAPTURE).read_bytes() == SECOND
    assert git(second, "diff", "--", CAPTURE).stdout
    assert not git(second, "diff", "--cached", "--", CAPTURE).stdout
    assert git(second, "diff", "--name-only", before, "HEAD").stdout.decode().splitlines() == [CAPTURE]
    assert (second / "data/other_engine_output.json").read_bytes() == b'{"retain_me":true}\n'
    assert retention.check_retained(second)["state"] == "PRESERVED"
    git(second, "push", "origin", "HEAD:refs/heads/main")
    assert git(remote, "show", "main:" + CAPTURE).stdout == FIRST
    # Stable repeated preservation creates no commit and changes no index bytes.
    before_state = state(second)
    assert retention.preserve_retained(second)["restored_count"] == 0
    assert state(second) == before_state


def test_remote_moves_after_guard_native_push_refuses_then_retry_rechecks(runners):
    remote, first, second = overlap(runners)
    retention.preserve_retained(second)
    git(second, "push", "origin", "main")
    write(second, OTHER_CAPTURE, SECOND)
    # A later producer must not blanket-stage retained worktree conflict bytes.
    git(second, "add", "--", OTHER_CAPTURE)
    git(second, "commit", "-m", "second next capture")
    retention.check_retained(second)
    git(first, "pull", "--ff-only", "origin", "main")
    write(first, OTHER_CAPTURE, FIRST)
    commit(first, "racing first next capture")
    git(first, "push", "origin", "main")
    assert git(second, "push", "origin", "main", check=False).returncode != 0
    git(second, "fetch", "origin", "main")
    git(second, "rebase", "--autostash", "-X", "theirs", "origin/main")
    assert (second / OTHER_CAPTURE).read_bytes() == SECOND
    assert retention.preserve_retained(second)["restored_count"] == 1
    git(second, "push", "origin", "main")
    assert git(remote, "show", "main:" + OTHER_CAPTURE).stdout == FIRST
    assert git(remote, "show", "main:" + CAPTURE).stdout == FIRST


@pytest.mark.parametrize("pending", ["foreign_index", "receipt_worktree", "index_lock"])
def test_ambiguous_pending_work_is_preserved_and_push_withheld(runners, pending):
    _, _, second = overlap(runners)
    if pending == "foreign_index":
        write(second, "unowned", b"keep staged\n")
        git(second, "add", "unowned")
    elif pending == "receipt_worktree":
        write(second, CAPTURE, b"uncommitted owner bytes\n")
    else:
        (second / ".git/index.lock").write_bytes(b"existing owner lock\n")
    before = state(second)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        retention.preserve_retained(second)
    assert state(second) == before
    if pending == "index_lock":
        assert (second / ".git/index.lock").read_bytes() == b"existing owner lock\n"


def test_retained_deletion_is_restored_and_new_receipt_is_not_removed(runners):
    _, _, second = overlap(runners)
    (second / CAPTURE).unlink()
    write(second, OTHER_CAPTURE, SECOND)
    commit(second, "candidate deleted old receipt")
    assert retention.preserve_retained(second)["restored_count"] == 1
    assert git(second, "show", "HEAD:" + CAPTURE).stdout == FIRST
    assert not (second / CAPTURE).exists()  # deletion retained as local dirt
    assert (second / OTHER_CAPTURE).read_bytes() == SECOND


def test_invalid_remote_clock_bytes_are_retained_without_promoting_them(runners):
    _, first, second = runners
    write(first, CAPTURE, b"invalid retained metadata\n")
    commit(first, "invalid retained receipt")
    git(first, "push", "origin", "main")
    write(second, CAPTURE, SECOND)
    commit(second, "different local claim")
    git(second, "fetch", "origin", "main")
    git(second, "rebase", "-X", "theirs", "origin/main")
    retention.preserve_retained(second)
    assert git(second, "show", "HEAD:" + CAPTURE).stdout == b"invalid retained metadata\n"
    assert (second / CAPTURE).read_bytes() == SECOND
    assert retention.check_retained(second)["state"] == "PRESERVED"


@pytest.mark.parametrize("fault", ["missing_target", "wrong_branch", "unexpected_mode"])
def test_unreadable_or_unexpected_boundary_fails_without_mutation(runners, fault):
    _, _, second = overlap(runners)
    onto = "origin/main"
    if fault == "missing_target":
        onto = "missing-target"
    elif fault == "wrong_branch":
        git(second, "checkout", "-b", "wrong-owner")
    else:
        (second / CAPTURE).chmod(0o755)
        commit(second, "unexpected executable receipt")
    before = state(second)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        retention.preserve_retained(second, onto)
    assert state(second) == before


def test_final_check_binds_the_exact_candidate_that_will_be_pushed(runners):
    _, _, second = overlap(runners)
    unretained_candidate = git(second, "rev-parse", "HEAD").stdout.strip().decode()
    retention.preserve_retained(second)
    assert retention.check_retained(second)["state"] == "PRESERVED"
    with pytest.raises(ValueError, match="changes 1 retained"):
        retention.check_retained(second, candidate_ref=unretained_candidate)


def test_engine_publisher_corrects_each_rebase_then_checks_final_push_candidate():
    source = (retention.REPO_ROOT / "scripts/ci/daily_engine_commit_outputs.sh").read_text()
    loop = source[source.index('push_retry_init "engine outputs"'):]
    assert loop.index("push_fetch_main_for_rebase") < loop.index("git rebase --autostash")
    assert loop.index("push_autostash_ok") < loop.index("turn_watch_capture_retention.py preserve")
    assert loop.index("turn_watch_capture_retention.py preserve") < loop.index("python -m scripts.inject_data_base")
    assert loop.index("qledger_push_candidate=$(git rev-parse") < loop.index("turn_watch_capture_retention.py check")
    assert 'check --candidate "$qledger_push_candidate" || exit $?' in loop
    assert loop.index("turn_watch_capture_retention.py check") < loop.index('push_do origin "$qledger_push_candidate:refs/heads/main"')


@pytest.mark.parametrize("late_stage", [False, True], ids=["worktree", "staged"])
def test_late_independent_receipt_writer_survives_preflight_race(runners, monkeypatch, late_stage):
    _, _, second = overlap(runners)
    prior_head = git(second, "rev-parse", "HEAD").stdout
    real = retention._git
    observed_target_reads = 0
    foreign = b"foreign writer after preflight\n"

    def interleave(repo, *args):
        nonlocal observed_target_reads
        result = real(repo, *args)
        # Second target resolution is precisely after the prior unlocked
        # clean-index/receipt checks. Old git-restore then lost these bytes.
        if args == ("rev-parse", "--verify", "--end-of-options", "origin/main^{commit}"):
            observed_target_reads += 1
            if observed_target_reads == 2:
                write(second, CAPTURE, foreign)
                if late_stage:
                    git(second, "add", "--", CAPTURE)
        return result

    monkeypatch.setattr(retention, "_git", interleave)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        retention.preserve_retained(second)
    assert observed_target_reads == 2
    assert git(second, "rev-parse", "HEAD").stdout == prior_head
    assert (second / CAPTURE).read_bytes() == foreign
    assert git(second, "show", ":" + CAPTURE).stdout == (foreign if late_stage else SECOND)
    assert (second / "data/other_engine_output.json").read_bytes() == b'{"retain_me":true}\n'
    assert not (second / ".git/index.lock").exists()


@pytest.mark.parametrize("race", ["index_lock", "head_move"])
def test_late_lock_or_parent_movement_withholds_without_losing_preimage(runners, monkeypatch, race):
    _, _, second = overlap(runners)
    real = retention._git
    observations = 0

    def interleave(repo, *args):
        nonlocal observations
        result = real(repo, *args)
        if args == ("rev-parse", "--verify", "--end-of-options", "origin/main^{commit}"):
            observations += 1
            if observations == 2:
                if race == "index_lock":
                    (second / ".git/index.lock").write_bytes(b"foreign lock\n")
                else:
                    git(second, "commit", "--allow-empty", "-m", "concurrent new parent")
        return result

    monkeypatch.setattr(retention, "_git", interleave)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        retention.preserve_retained(second)
    assert observations == 2
    assert (second / CAPTURE).read_bytes() == SECOND
    assert git(second, "show", ":" + CAPTURE).stdout == SECOND
    if race == "index_lock":
        assert (second / ".git/index.lock").read_bytes() == b"foreign lock\n"
    else:
        assert git(second, "log", "-1", "--format=%s").stdout.strip() == b"concurrent new parent"
        assert not (second / ".git/index.lock").exists()


def test_identical_digest_rerun_needs_no_correction_or_worktree_change(runners):
    _, first, second = runners
    write(first, CAPTURE, FIRST)
    commit(first, "first producer")
    git(first, "push", "origin", "main")
    write(second, CAPTURE, FIRST)
    commit(second, "same exact capture")
    git(second, "fetch", "origin", "main")
    git(second, "rebase", "--autostash", "-X", "theirs", "origin/main")
    before = state(second)
    assert retention.preserve_retained(second)["restored_count"] == 0
    assert state(second) == before


@pytest.mark.parametrize("pending", ["capture", "unrelated"])
@pytest.mark.parametrize("copy_failure", [False, True], ids=["normal-copy", "failed-copy"])
def test_late_staged_preimage_survives_snapshot_failure(runners, monkeypatch, pending, copy_failure):
    _, _, repo = overlap(runners)
    late_path = CAPTURE if pending == "capture" else "unrelated-owner.txt"
    foreign = b"independent writer staged after preflight\n"
    real_git = retention._git
    real_run = subprocess.run
    count = 0
    before = {}

    def interleave(where, *args):
        nonlocal count
        out = real_git(where, *args)
        if args == ("rev-parse", "--verify", "--end-of-options", "origin/main^{commit}"):
            count += 1
            if count == 2:
                write(repo, late_path, foreign)
                git(repo, "add", "--", late_path)
                before["head"] = git(repo, "rev-parse", "HEAD").stdout
                before["index"] = (repo / ".git/index").read_bytes()
        return out

    fault = '''cp() {
  local arg
  for arg in "$@"; do
    case "$arg" in */oip-locked-index.*)
      printf 'INJECTED: private index snapshot copy failure\\n' >&2
      return 73 ;;
    esac
  done
  command cp "$@"
}
'''
    def fail_snapshot(argv, *args, **kwargs):
        if copy_failure and isinstance(argv, list) and argv[:2] == ["bash", "-c"] and "oip_commit_locked_roots" in argv[2]:
            argv = [*argv[:2], fault + argv[2], *argv[3:]]
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(retention, "_git", interleave)
    monkeypatch.setattr(subprocess, "run", fail_snapshot)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        retention.preserve_retained(repo)
    staged = git(repo, "show", ":" + late_path, check=False)
    observed = {
        "pending": pending, "copy_failure": copy_failure,
        "injected_once": count == 2,
        "head_preserved": git(repo, "rev-parse", "HEAD").stdout == before["head"],
        "working_bytes_preserved": (repo / late_path).read_bytes() == foreign,
        "index_bytes_preserved": (repo / ".git/index").read_bytes() == before["index"],
        "staged_bytes_preserved": staged.returncode == 0 and staged.stdout == foreign,
        "lock_left": (repo / ".git/index.lock").exists(),
    }
    assert observed["injected_once"] and observed["head_preserved"] and observed["working_bytes_preserved"]
    assert observed["staged_bytes_preserved"], observed
    assert observed["index_bytes_preserved"], observed


def _inject_locked_snapshot_hook(monkeypatch, hook):
    """Use the incumbent shell's existing race hook; never alter its source."""
    real_run = subprocess.run

    def inject(argv, *args, **kwargs):
        if isinstance(argv, list) and argv[:2] == ["bash", "-c"] and "oip_commit_locked_roots" in argv[2]:
            argv = [*argv[:2], hook + "\n" + argv[2], *argv[3:]]
        return real_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", inject)


@pytest.mark.parametrize("kind", ["modified", "different-inode", "symlink", "fifo"])
def test_retention_failure_preserves_changed_owned_lock(runners, monkeypatch, kind):
    _, _, repo = overlap(runners)
    write(repo, "untracked-owner.txt", b"untracked owner bytes\n")
    before = state(repo)
    if kind == "modified":
        mutation = "printf 'foreign lock bytes' > .git/index.lock"
    else:
        mutation = "mv .git/index.lock .git/index.lock.original\n"
        mutation += {
            "different-inode": ": > .git/index.lock",
            "symlink": "ln -s ../untracked-owner.txt .git/index.lock",
            "fifo": "mkfifo .git/index.lock",
        }[kind]
    hook = "oip_after_locked_tree_snapshot() {\n" + mutation + "\nreturn 74\n}\n"
    _inject_locked_snapshot_hook(monkeypatch, hook)
    with pytest.raises(subprocess.CalledProcessError) as exc:
        retention.preserve_retained(repo)
    assert exc.value.returncode == 74
    assert state(repo) == before
    lock = repo / ".git/index.lock"
    if kind == "modified":
        assert lock.read_bytes() == b"foreign lock bytes"
    elif kind == "different-inode":
        assert lock.is_file() and lock.stat().st_size == 0
        assert lock.stat().st_ino != (repo / ".git/index.lock.original").stat().st_ino
    elif kind == "symlink":
        assert lock.is_symlink()
    else:
        assert lock.is_fifo()
    assert (repo / "untracked-owner.txt").read_bytes() == b"untracked owner bytes\n"


def _inject_bounded_owned_lock_hook(monkeypatch, hook):
    """Bound non-regular lock probes, including all descendant shell processes."""
    import os
    import signal

    real_run = subprocess.run

    def inject(argv, *args, **kwargs):
        if not (isinstance(argv, list) and argv[:2] == ["bash", "-c"]
                and "oip_commit_locked_roots" in argv[2]):
            return real_run(argv, *args, **kwargs)
        argv = [*argv[:2], hook + "\n" + argv[2], *argv[3:]]
        options = dict(kwargs)
        check = options.pop("check", False)
        assert options.pop("capture_output", False)
        with subprocess.Popen(
            argv, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, **options,
        ) as process:
            try:
                stdout, stderr = process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                pytest.fail("owned-lock transaction hung on a bounded lock probe")
            result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result

    monkeypatch.setattr(subprocess, "run", inject)


@pytest.mark.parametrize("kind", ["modified", "different-inode", "symlink", "fifo"])
@pytest.mark.parametrize("boundary", ["snapshot", "prepared", "install"])
def test_successful_transaction_preserves_changed_owned_lock(
    runners, monkeypatch, kind, boundary,
):
    _, _, repo = overlap(runners)
    write(repo, "untracked-owner.txt", b"untracked owner bytes\n")
    before = state(repo)
    if kind == "modified":
        mutation = "printf 'foreign lock bytes' > .git/index.lock"
    else:
        mutation = "mv .git/index.lock .git/index.lock.original\n"
        mutation += {
            "different-inode": ": > .git/index.lock",
            "symlink": "ln -s ../untracked-owner.txt .git/index.lock",
            "fifo": "mkfifo .git/index.lock",
        }[kind]
    hook_name = {
        "snapshot": "oip_after_locked_tree_snapshot",
        "prepared": "oip_after_locked_index_prepare",
        "install": "oip_before_locked_index_install",
    }[boundary]
    hook = hook_name + "() {\n" + mutation + "\nreturn 0\n}\n"
    _inject_bounded_owned_lock_hook(monkeypatch, hook)
    with pytest.raises(subprocess.CalledProcessError):
        retention.preserve_retained(repo)
    assert not (repo / ".git/index").is_symlink()
    assert state(repo) == before
    lock = repo / ".git/index.lock"
    if kind == "modified":
        assert lock.read_bytes() == b"foreign lock bytes"
    elif kind == "different-inode":
        assert lock.is_file() and lock.stat().st_size == 0
        assert lock.stat().st_ino != (repo / ".git/index.lock.original").stat().st_ino
    elif kind == "symlink":
        assert lock.is_symlink()
    else:
        assert lock.is_fifo()
    assert (repo / "untracked-owner.txt").read_bytes() == b"untracked owner bytes\n"


def test_install_refusal_never_rolls_back_a_newer_ref(runners, monkeypatch):
    _, _, repo = overlap(runners)
    before = state(repo)
    hook = """oip_before_locked_index_install() {
  mv .git/index.lock .git/index.lock.original
  printf 'foreign lock bytes' > .git/index.lock
  third=$(printf 'independent ref winner\\n' | git commit-tree "$parent_tree" -p "$candidate")
  git update-ref refs/heads/main "$third" "$candidate"
  printf '%s' "$third" > .git/ref-race-winner
  return 0
}
"""
    _inject_bounded_owned_lock_hook(monkeypatch, hook)
    with pytest.raises(subprocess.CalledProcessError) as exc:
        retention.preserve_retained(repo)
    assert b"rollback unresolved" in exc.value.stderr
    assert git(repo, "rev-parse", "HEAD").stdout.strip().decode() == (
        repo / ".git/ref-race-winner"
    ).read_text()
    assert (repo / ".git/index").read_bytes() == before[1]
    assert (repo / CAPTURE).read_bytes() == before[2]
    assert (repo / ".git/index.lock").read_bytes() == b"foreign lock bytes"


def test_unconfirmed_install_ack_does_not_blindly_roll_back(runners, monkeypatch):
    _, _, repo = overlap(runners)
    before = state(repo)
    hook = """oip_before_locked_index_install() {
  python3() {
    if [ "$2" = install ]; then
      command python3 "$@" || return $?
      # Lose only the successful helper's completion status, after its rename.
      return 75
    fi
    command python3 "$@"
  }
  return 0
}
"""
    _inject_bounded_owned_lock_hook(monkeypatch, hook)
    with pytest.raises(subprocess.CalledProcessError) as exc:
        retention.preserve_retained(repo)
    assert b"installation outcome unknown" in exc.value.stderr
    assert git(repo, "rev-parse", "HEAD").stdout != before[0]
    assert git(repo, "show", "HEAD:" + CAPTURE).stdout == FIRST
    assert git(repo, "show", ":" + CAPTURE).stdout == FIRST
    assert (repo / CAPTURE).read_bytes() == SECOND
    assert not (repo / ".git/index.lock").exists()


@pytest.mark.parametrize("foreign", [False, True], ids=["clean-restore", "foreign-lock"])
def test_broad_failure_restoration_obeys_owned_content(runners, monkeypatch, foreign):
    _, _, repo = overlap(runners)
    write(repo, "data/broad-pending.json", b"pending broad output\n")
    git(repo, "add", "--", "data/broad-pending.json")
    before = state(repo)
    mutation = "printf 'foreign lock bytes' > .git/index.lock\n" if foreign else ""
    hook = "oip_after_locked_tree_snapshot() {\n" + mutation + "return 74\n}\n"
    _inject_bounded_owned_lock_hook(monkeypatch, hook)
    result = subprocess.run(
        ["bash", "-c",
         'source "$1"\noip_commit_locked_roots "rejected broad output" true data',
         "broad-restore-test",
         str(retention.REPO_ROOT / "scripts/ci/options_signal_nightly.sh")],
        cwd=repo, check=False, capture_output=True,
    )
    assert result.returncode == 74
    assert git(repo, "rev-parse", "HEAD").stdout == before[0]
    assert (repo / CAPTURE).read_bytes() == before[2]
    assert (repo / "data/broad-pending.json").read_bytes() == b"pending broad output\n"
    if foreign:
        assert state(repo) == before
        assert (repo / ".git/index.lock").read_bytes() == b"foreign lock bytes"
    else:
        assert not git(repo, "diff", "--cached", "--name-only").stdout
        assert not (repo / ".git/index.lock").exists()


def test_working_writer_after_private_snapshot_survives_success(runners, monkeypatch):
    _, _, repo = overlap(runners)
    hook = "oip_after_locked_tree_snapshot() {\nprintf 'late working writer\\n' > '" + CAPTURE + "'\n}\n"
    _inject_locked_snapshot_hook(monkeypatch, hook)
    result = retention.preserve_retained(repo)
    assert result["restored_count"] == 1
    assert git(repo, "show", "HEAD:" + CAPTURE).stdout == FIRST
    assert git(repo, "show", ":" + CAPTURE).stdout == FIRST
    assert (repo / CAPTURE).read_bytes() == b"late working writer\n"
    assert (repo / "data/other_engine_output.json").read_bytes() == b'{"retain_me":true}\n'
    assert not (repo / ".git/index.lock").exists()
