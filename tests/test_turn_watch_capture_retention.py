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
