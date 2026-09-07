"""Stale-lock self-heal + loud failure for scripts/worktree_sparse.py — MO-B PLAT-6.

WHY THIS EXISTS
---------------
Census 2026-09-06 (agentos/discoveries/DSC-SPARSE-MINT-FAILS-SILENTLY-ON-
STALE-LOCKS.md): 97 of 267 `.claude/worktrees/` session trees were FULL
(~6.5 GiB) instead of sparse (~0.4 GiB). `refuse_if_locked` refuses whenever
`index.lock`/`info/sparse-checkout.lock` exists, with no notion of staleness
— but under fleet lock contention those locks are frequently left behind by a
killed sibling process (measured ages 600-3,500 minutes, no live holder), and
the refusal was swallowed upstream: the harness reported the worktree as
created and the session proceeded on a full tree.

This suite pins three additive behaviors, all fail-closed by default:

  (1) A lock older than `STALE_LOCK_MIN_AGE_S` (600s) with NO live process
      holding the worktree/git-dir (per an injectable `gather_live_processes`
      probe) is removed automatically, with a line-starting `::warning`
      naming the lock, its age, and the tree — see `lock_is_stale` (a pure
      predicate over an injected process list, so no real process spawning is
      needed here) and `_clear_stale_locks`.
  (2) A lock that is either young OR still held by a live process (or whose
      liveness could not be confirmed at all — `gather_live_processes`
      returning `None`) still refuses with a line-starting `::error` and a
      non-zero exit, exactly as before — this suite proves the new staleness
      path never weakens that refusal.
  (3) A post-condition check after `apply_profile` succeeds: `git
      sparse-checkout list` must match the requested include set, and every
      excluded directory must be an empty husk on disk — never a partially
      materialized tree. A mismatch fails loud (non-zero, `::error`) instead
      of reporting the success message.
  (4) `status --json` returns a machine-readable
      `{sparse, missing_dirs, stale_locks_removed, full_bytes_estimate}` shape
      for fleet census scripts.

Run: python3 -m pytest tests/test_worktree_sparse.py -q
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import platform
import subprocess
import time
from pathlib import Path

import pytest

from scripts import worktree_sparse as WS

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "worktree_create_sparse.py"

_BIG_CONTENT = b'{"ticker": "ABC", "series": [1, 2, 3, 4, 5]}\n' * 40


def _load_hook():
    spec = importlib.util.spec_from_file_location("worktree_create_sparse_pt6", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(("git", "-C", str(repo)) + args,
                           capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _real_git_dir(repo: Path) -> Path:
    return Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-dir"))


def _backdate(path: Path, age_s: float) -> None:
    """Set ``path``'s mtime (and atime) to ``age_s`` seconds in the past."""
    ts = time.time() - age_s
    os.utime(path, (ts, ts))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed repo, sparsed to include only `scripts/` — `big/` starts
    tracked, excluded, and (because cone sparse-checkout physically removes
    what it excludes) empty on disk, the same shape as a session worktree
    under policy R8."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    (r / "scripts").mkdir()
    (r / "scripts" / "keep.txt").write_text("keep\n", encoding="utf-8")
    big = r / "big"
    big.mkdir()
    (big / "data.json").write_bytes(_BIG_CONTENT)
    (big / "other.txt").write_text("unrelated tracked file\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    _git(r, "sparse-checkout", "init", "--cone")
    _git(r, "sparse-checkout", "set", "--cone", "--", "scripts")
    assert WS.missing_dirs(r) == ["big"], "fixture precondition: big/ starts omitted"
    return r


# ── (1) a confirmed-stale lock is removed, loudly, and the op proceeds ──────

def test_stale_lock_is_removed_with_warning_and_operation_proceeds(repo, monkeypatch, capsys):
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 60)
    monkeypatch.setattr(WS, "gather_live_processes", lambda *a, **k: [])

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc == 0, f"a confirmed-stale lock must not block the operation:\n{blob}"
    assert not lock.exists(), "a confirmed-stale lock must be removed"
    warning_lines = [ln for ln in blob.splitlines() if "::warning" in ln]
    assert warning_lines, f"no ::warning emitted for the removed stale lock:\n{blob}"
    assert any(ln.startswith("::warning") for ln in warning_lines), (
        f"annotation did not open the line, so GitHub will drop it: {warning_lines}")
    assert str(lock) in blob, f"warning did not name the lock path:\n{blob}"


def test_stale_lock_removal_also_applies_to_the_sparse_checkout_lock(repo, monkeypatch, capsys):
    gitdir = _real_git_dir(repo)
    lock = gitdir / "info" / "sparse-checkout.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 120)
    monkeypatch.setattr(WS, "gather_live_processes", lambda *a, **k: [])

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc == 0, f"a confirmed-stale sparse-checkout.lock must not block the op:\n{blob}"
    assert not lock.exists()
    assert "::warning" in blob and str(lock) in blob


# ── Minor (round-3 review of macro #6971): `_clear_stale_locks`'s own
#    git-dir re-probe must fail CLOSED, not silently skip half the liveness
#    check (the script-side twin of the hook's `_lock_candidates` fix) ──────

def test_clear_stale_locks_fails_closed_when_gitdir_reprobe_fails(repo, monkeypatch):
    """`_clear_stale_locks` re-probes `git rev-parse --git-dir` (separately
    from `index_lock_path`/`sparse_checkout_lock_path`, which already
    succeeded to produce ``locks``) to scope `gather_live_processes`. RED-
    first: before this fix, a failure on that SECOND probe set
    ``git_dir = None`` and called `gather_live_processes(root, None)` anyway
    — the Darwin/Linux probes both read `git_dir=None` as "no git-dir check
    needed" and skip that half silently, so a lock a live process holds only
    via an open file (not cwd) could be reported confirmed-empty and
    removed. This lock must instead be left `still_locked` (fail closed),
    and `gather_live_processes` must never even be called with an unknown
    git_dir."""
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 60)

    real_git = WS._git
    calls = {"git_dir_probes": 0}

    def flaky_git(root, *args, **kwargs):
        if args == ("rev-parse", "--path-format=absolute", "--git-dir"):
            calls["git_dir_probes"] += 1
            if calls["git_dir_probes"] > 2:  # the two lock-path helpers go first
                return None
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(WS, "_git", flaky_git)

    def must_not_be_called(*_a, **_k):
        raise AssertionError(
            "gather_live_processes must never be called with an unknown "
            "git_dir — that silently downgrades the two-check probe to a "
            "cwd-only one")

    monkeypatch.setattr(WS, "gather_live_processes", must_not_be_called)

    removed, still_locked = WS._clear_stale_locks(repo)

    assert removed == []
    assert still_locked == [lock], (
        "a lock must fail closed when its own git-dir cannot be determined, "
        "never silently proceed with a partial liveness check")


# ── (2) a young lock, a live-held lock, and an unconfirmed probe all refuse ─

def test_old_lock_with_live_process_still_refuses(repo, monkeypatch, capsys):
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 60)
    monkeypatch.setattr(
        WS, "gather_live_processes",
        lambda *a, **k: [{"pid": 999, "cwd": str(repo), "open_files": []}],
    )

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc != 0, "a lock with a live process must still refuse even when old"
    assert lock.exists(), "a live-held lock must never be auto-deleted"
    error_lines = [ln for ln in blob.splitlines() if "::error" in ln]
    assert error_lines and any(ln.startswith("::error") for ln in error_lines), (
        f"no line-starting ::error for a still-locked refusal:\n{blob}")


def test_old_lock_with_unconfirmed_probe_fails_closed(repo, monkeypatch, capsys):
    """`gather_live_processes` returning None (probe untrustworthy — lsof
    missing, /proc unreadable, unsupported platform) must NEVER be read as
    'nothing is alive'. The lock stays and the operation still refuses."""
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 60)
    monkeypatch.setattr(WS, "gather_live_processes", lambda *a, **k: None)

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc != 0, f"an unconfirmed liveness probe must fail closed:\n{blob}"
    assert lock.exists()
    assert "::error" in blob


def test_young_lock_refuses_even_with_no_live_process(repo, monkeypatch, capsys):
    """A lock created moments ago (age < STALE_LOCK_MIN_AGE_S) must refuse
    regardless of process state — age is a hard floor, not just a hint."""
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")  # fresh; no backdating

    probe_called = []

    def spy_probe(*a, **k):
        probe_called.append(True)
        return []

    monkeypatch.setattr(WS, "gather_live_processes", spy_probe)

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc != 0
    assert lock.exists(), "a lock younger than the threshold must never be auto-deleted"
    assert not probe_called, (
        "the live-process probe should not even run for a lock too young to "
        "qualify — it is a real subprocess call and the age check is free")
    assert "::error" in blob


# ── `gather_live_processes` — the real per-platform probe (round-2 verify) ──
# (round 1/2 review: "attack the liveness probe — a process whose cwd is a
# SUBDIRECTORY of the worktree; a process with the gitdir open but cwd
# elsewhere; lsof timing out". The subdirectory-cwd case already worked (lsof
# `+D` recurses), but two real gaps existed: (a) on Darwin, if only ONE of the
# two required lsof calls failed/timed out, the probe still returned a
# confirmed (partial) result instead of None, silently dropping exactly the
# half that might have found the holder; (b) on Linux, the git-dir
# "open file, cwd elsewhere" case was never checked at all — only cwd was.)

def test_gather_live_processes_darwin_partial_probe_failure_is_unconfirmed(
    monkeypatch, tmp_path,
):
    """If the cwd-scoped lsof call succeeds but the git-dir-scoped one
    fails/times out (or vice versa), the whole probe must come back
    unconfirmed (None) — a probe that only half-answered is not proof nothing
    holds the lock."""
    monkeypatch.setattr(WS.platform, "system", lambda: "Darwin")

    def cwd_ok_gitdir_fails(args):
        if "-d" in args:  # the cwd-scoped probe
            return "p123\nfcwd\n/somewhere\n"
        return None  # the git-dir open-file probe "timed out"

    monkeypatch.setattr(WS, "_run_lsof", cwd_ok_gitdir_fails)
    assert WS.gather_live_processes(tmp_path / "wt", tmp_path / "gitdir") is None

    def gitdir_ok_cwd_fails(args):
        if "-d" in args:
            return None  # the cwd-scoped probe "timed out"
        return "p456\nfcwd\n/other\n"

    monkeypatch.setattr(WS, "_run_lsof", gitdir_ok_cwd_fails)
    assert WS.gather_live_processes(tmp_path / "wt", tmp_path / "gitdir") is None


def test_gather_live_processes_linux_detects_gitdir_open_file_when_cwd_elsewhere(
    monkeypatch, tmp_path,
):
    """A process with the lock file open via an fd, but whose cwd is
    elsewhere, must still be detected on Linux — the same coverage the
    macOS `lsof -F pn +D <git_dir>` call already provides."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    gitdir = tmp_path / "gitdir"
    gitdir.mkdir()
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    lockfile = gitdir / "index.lock"
    lockfile.write_bytes(b"")

    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "4242"
    pid_dir.mkdir(parents=True)
    os.symlink(other_cwd, pid_dir / "cwd")
    fd_dir = pid_dir / "fd"
    fd_dir.mkdir()
    os.symlink(lockfile, fd_dir / "9")

    monkeypatch.setattr(WS.platform, "system", lambda: "Linux")

    procs = WS.gather_live_processes(worktree, gitdir, proc_root=proc_root)

    assert procs is not None
    assert any(p["pid"] == 4242 for p in procs), f"missed gitdir-open-file holder: {procs}"


def test_gather_live_processes_linux_still_detects_cwd_under_worktree(monkeypatch, tmp_path):
    """Regression guard: adding the fd/git-dir check must not break the
    existing cwd-under-worktree detection."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    sub = worktree / "sub"
    sub.mkdir()

    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "777"
    pid_dir.mkdir(parents=True)
    os.symlink(sub, pid_dir / "cwd")

    monkeypatch.setattr(WS.platform, "system", lambda: "Linux")

    procs = WS.gather_live_processes(worktree, None, proc_root=proc_root)

    assert procs is not None
    assert any(p["pid"] == 777 for p in procs)


# ── `lock_is_stale` — pure predicate, no real processes ─────────────────────

def test_lock_is_stale_pure_predicate(tmp_path):
    lock = tmp_path / "index.lock"
    lock.write_bytes(b"")
    now = time.time()
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 1)

    assert WS.lock_is_stale(lock, now, []) is True
    assert WS.lock_is_stale(lock, now, [{"pid": 1, "cwd": None, "open_files": []}]) is False
    assert WS.lock_is_stale(lock, now, None) is False, "an unconfirmed probe is never stale"

    _backdate(lock, 5)  # too young, even with an empty (confirmed-clear) process list
    assert WS.lock_is_stale(lock, now, []) is False


def test_lock_is_stale_returns_false_on_unreadable_lock(tmp_path):
    missing = tmp_path / "does-not-exist.lock"
    assert WS.lock_is_stale(missing, time.time(), []) is False


# ── (3) post-condition check ─────────────────────────────────────────────────

def test_verify_sparse_postcondition_passes_when_matched(repo):
    assert WS.verify_sparse_postcondition(repo, ["scripts"], ["big"]) is None


def test_verify_sparse_postcondition_fails_on_a_tracked_file_re_materialized(repo):
    """MAJOR-2 (Meta-CEO B ruling r2 on macro #6971): a TRACKED file
    physically reappearing in an excluded dir — the partial-materialization
    failure mode this postcondition exists to catch — must still fail loud.
    `big/other.txt` is committed in the `repo` fixture, so this is genuinely
    tracked content, not stray junk."""
    (repo / "big").mkdir(exist_ok=True)
    (repo / "big" / "other.txt").write_text("reappeared\n", encoding="utf-8")

    problem = WS.verify_sparse_postcondition(repo, ["scripts"], ["big"])

    assert problem is not None
    assert "big" in problem and "TRACKED" in problem


def test_verify_sparse_postcondition_ignores_untracked_survivor(repo):
    """MAJOR-2 (ruling r2, amending the frozen spec): surviving UNTRACKED
    content is NOT a postcondition failure — `git sparse-checkout set` never
    touches untracked content, so an otherwise-correct sparsify must not be
    reported as failed over it. RED-first: before this ruling, ANY entry in
    an excluded dir (tracked or not) failed the postcondition."""
    (repo / "big").mkdir(exist_ok=True)
    (repo / "big" / "stray.txt").write_text("oops\n", encoding="utf-8")

    problem = WS.verify_sparse_postcondition(repo, ["scripts"], ["big"])

    assert problem is None, (
        f"an untracked-only survivor must not fail the postcondition: {problem}")


def test_verify_sparse_postcondition_detects_include_set_mismatch(repo):
    problem = WS.verify_sparse_postcondition(repo, ["scripts", "big"], [])
    assert problem is not None
    assert "mismatch" in problem.lower()


# ── Minor (round-3 review of macro #6971): _tracked_entries_present must ────
#    fail CLOSED on its own probe failure, never silently as "nothing tracked"

def test_tracked_entries_present_raises_on_a_failed_ls_tree(repo, monkeypatch):
    """A failed `git ls-tree` (``_git`` returning ``None``) must propagate as
    ``RuntimeError``, never be swallowed into ``[]`` — an empty list here is
    indistinguishable from a genuinely empty tree to every caller, which
    would let a broken git invocation silently pass the postcondition it
    exists to enforce."""
    monkeypatch.setattr(WS, "_git", lambda *a, **k: None)
    with pytest.raises(RuntimeError):
        WS._tracked_entries_present(repo, "big")


def test_verify_sparse_postcondition_fails_loud_when_tracked_probe_fails(repo, monkeypatch):
    """The postcondition must not read a failed tracked-entries probe as a
    clean pass. RED-first: before this fix, `_tracked_entries_present`
    caught the `_git` failure and returned `[]`, so this returned `None`
    (success) even though the check never actually ran."""
    real_git = WS._git

    def flaky_git(root, *args, **kwargs):
        if args[:1] == ("ls-tree",):
            return None
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(WS, "_git", flaky_git)

    problem = WS.verify_sparse_postcondition(repo, ["scripts"], ["big"])

    assert problem is not None, (
        "a failed tracked-entries probe must fail the postcondition, not pass silently")


def test_untracked_entries_present_degrades_to_zero_on_a_failed_probe(repo, monkeypatch):
    """The untracked-survivor count is best-effort and non-blocking, so a
    `_tracked_entries_present` failure here must degrade to 0 (skip the
    warning) rather than crash `apply_profile` after the (real) blocking
    check already succeeded."""
    (repo / "big").mkdir(exist_ok=True)
    (repo / "big" / "stray.txt").write_text("oops\n", encoding="utf-8")
    monkeypatch.setattr(WS, "_git", lambda *a, **k: None)

    assert WS._untracked_entries_present(repo, "big") == 0


def test_postcondition_mismatch_fails_apply_profile_loudly(repo, monkeypatch, capsys):
    """Even though `git sparse-checkout set` itself succeeds, a post-apply
    verification mismatch must fail the whole call — never report the
    success message over a state that does not match what was requested."""
    monkeypatch.setattr(WS, "_cone_included", lambda root: ["scripts", "unexpected"])

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc != 0, f"a postcondition mismatch must fail loud:\n{blob}"
    assert "::error" in blob and "worktree-sparse-postcondition-failed" in blob
    assert any(ln.startswith("::error") for ln in blob.splitlines())
    assert "profile applied" not in blob, (
        "the success message must never print alongside a failed postcondition")


def test_apply_profile_warns_on_untracked_survivor_but_still_succeeds(repo, capsys):
    """MAJOR-2 (ruling r2): an untracked stray file left in the excluded dir
    must not fail `apply_profile` — it emits a line-starting ::warning naming
    the dir and count, and the success message still prints."""
    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    assert rc == 0
    capsys.readouterr()  # drain the first apply's output

    (repo / "big").mkdir(exist_ok=True)
    (repo / "big" / "stray.txt").write_text("oops\n", encoding="utf-8")

    rc = WS.apply_profile(repo, exclude_dirs=["big"])
    blob = "".join(capsys.readouterr())

    assert rc == 0, f"an untracked survivor must not fail apply_profile:\n{blob}"
    warning_lines = [ln for ln in blob.splitlines() if "::warning" in ln]
    assert warning_lines, f"no ::warning emitted for the untracked survivor:\n{blob}"
    assert any(ln.startswith("::warning") for ln in warning_lines), (
        f"annotation did not open the line, so GitHub will drop it: {warning_lines}")
    assert "big" in blob and "1 untracked file" in blob
    assert "profile applied" in blob, "success message must still print"


def test_add_dirs_postcondition_catches_a_falsely_successful_materialize(repo, monkeypatch, capsys):
    """`git sparse-checkout add` can exit 0 (per `_run_git_timed`) without
    actually materializing the requested directory on disk (e.g. a race).
    `add_dirs` must not report success in that case."""
    real_popen = subprocess.Popen

    class _FakeSuccessProc:
        def __init__(self):
            self.returncode = 0

        def communicate(self, timeout=None):
            return "", ""  # reports success; deliberately writes nothing to disk

    def fake_popen(cmd, *a, **k):
        if (isinstance(cmd, (list, tuple)) and len(cmd) >= 5
                and cmd[0] == "git" and cmd[3] == "sparse-checkout" and cmd[4] == "add"):
            return _FakeSuccessProc()
        return real_popen(cmd, *a, **k)

    monkeypatch.setattr(WS.subprocess, "Popen", fake_popen)

    rc = WS.add_dirs(["big"], root=repo)
    blob = "".join(capsys.readouterr())

    assert rc != 0, f"a falsely-successful add must still fail on the postcondition:\n{blob}"
    assert "::error" in blob and "worktree-sparse-add-postcondition-failed" in blob
    assert any(ln.startswith("::error") for ln in blob.splitlines())


# ── (4) status --json ────────────────────────────────────────────────────────

def test_status_json_shape(repo):
    out = WS.status_json(repo)

    assert set(out.keys()) == {
        "sparse", "missing_dirs", "stale_locks_removed", "full_bytes_estimate",
        "untracked_survivors",
    }
    assert out["sparse"] is True
    assert out["missing_dirs"] == ["big"]
    assert out["stale_locks_removed"] == []
    assert isinstance(out["full_bytes_estimate"], int)
    assert out["full_bytes_estimate"] >= len(_BIG_CONTENT), (
        "full_bytes_estimate should at least cover big/data.json's committed size")
    assert out["untracked_survivors"] == {}


def test_status_json_reports_untracked_survivors(repo):
    """MAJOR-2 (ruling r2): status --json lists a currently-excluded dir's
    untracked survivor count — the same non-blocking signal apply_profile
    warns on — so a census over many worktrees can see it without applying."""
    (repo / "big").mkdir(exist_ok=True)
    (repo / "big" / "stray1.txt").write_text("a\n", encoding="utf-8")
    (repo / "big" / "stray2.txt").write_text("b\n", encoding="utf-8")

    out = WS.status_json(repo)

    assert out["untracked_survivors"] == {"big": 2}


def test_status_json_no_heal_skips_lock_clearing(repo, monkeypatch):
    """Minor-5 (ruling): `heal=False` keeps the census read-only — it must
    never delete a stale lock as a side effect."""
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 30)
    monkeypatch.setattr(WS, "gather_live_processes", lambda *a, **k: [])

    out = WS.status_json(repo, heal=False)

    assert out["stale_locks_removed"] == []
    assert lock.exists(), "heal=False must never delete a lock as a side effect"


def test_status_json_reports_and_clears_a_stale_lock(repo, monkeypatch):
    gitdir = _real_git_dir(repo)
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, WS.STALE_LOCK_MIN_AGE_S + 30)
    monkeypatch.setattr(WS, "gather_live_processes", lambda *a, **k: [])

    out = WS.status_json(repo)

    assert out["stale_locks_removed"] == [str(lock)]
    assert not lock.exists()


def test_status_json_full_checkout_shape(repo):
    assert WS.disable_profile(root=repo) == 0
    out = WS.status_json(repo)
    assert out["sparse"] is False
    assert out["missing_dirs"] == []
    assert out["full_bytes_estimate"] == 0


def test_main_status_json_flag_prints_valid_json(monkeypatch, capsys):
    fake = {
        "sparse": False, "missing_dirs": [], "stale_locks_removed": [],
        "full_bytes_estimate": 0, "untracked_survivors": {},
    }
    monkeypatch.setattr(WS, "status_json", lambda heal=True: fake)

    rc = WS.main(["status", "--json"])
    out = capsys.readouterr().out.strip()

    assert rc == 0
    assert json.loads(out) == fake


def test_main_status_json_no_heal_flag_passes_heal_false(monkeypatch):
    """Minor-5 (ruling): `status --json --no-heal` on the CLI must reach
    `status_json` as `heal=False`; the bare `--json` flag keeps `heal=True`."""
    seen: dict = {}

    def fake_status_json(heal=True):
        seen["heal"] = heal
        return {"sparse": False, "missing_dirs": [], "stale_locks_removed": [],
                "full_bytes_estimate": 0, "untracked_survivors": {}}

    monkeypatch.setattr(WS, "status_json", fake_status_json)

    assert WS.main(["status", "--json", "--no-heal"]) == 0
    assert seen["heal"] is False

    assert WS.main(["status", "--json"]) == 0
    assert seen["heal"] is True


# ── the WorktreeCreate hook duplicates its own stale-lock check ─────────────
# (deliberately: it must not depend on scripts/ import surface being intact —
# see load_profile's docstring in the hook itself). This section pins the
# duplicate constant and behavior in step with the script above.

def test_hook_stale_lock_constant_matches_the_script():
    hook = _load_hook()
    assert hook.STALE_LOCK_MIN_AGE_S == WS.STALE_LOCK_MIN_AGE_S


@pytest.fixture
def hook_worktree(tmp_path: Path):
    """A registered linked worktree of a fresh synthetic repo — the shape
    ``dest`` has by the time ``apply_sparse`` runs in the real hook (created
    via ``git worktree add --no-checkout`` before sparse-checkout is ever
    applied)."""
    donor = tmp_path / "donor"
    donor.mkdir()
    _git(donor, "init", "-q")
    _git(donor, "config", "user.email", "t@example.com")
    _git(donor, "config", "user.name", "t")
    (donor / "scripts").mkdir()
    (donor / "scripts" / "keep.txt").write_text("keep\n", encoding="utf-8")
    big = donor / "big"
    big.mkdir()
    (big / "data.json").write_bytes(_BIG_CONTENT)
    _git(donor, "add", "-A")
    _git(donor, "commit", "-qm", "base")

    dest = tmp_path / "dest"
    _git(donor, "worktree", "add", "--no-checkout", "-b", "wt", str(dest))
    return dest


def test_hook_removes_a_confirmed_stale_lock_with_warning(hook_worktree, monkeypatch, capsys):
    hook = _load_hook()
    gitdir = Path(_git(hook_worktree, "rev-parse", "--path-format=absolute", "--git-dir"))
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, hook.STALE_LOCK_MIN_AGE_S + 60)
    monkeypatch.setattr(hook, "_live_pids_holding", lambda *a, **k: set())

    hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    blob = "".join(capsys.readouterr())

    assert not lock.exists(), "a confirmed-stale lock must be removed"
    warning_lines = [ln for ln in blob.splitlines() if "::warning" in ln]
    assert warning_lines and any(ln.startswith("::warning") for ln in warning_lines), (
        f"no line-starting ::warning for the removed stale lock:\n{blob}")
    assert str(lock) in blob


def test_hook_refuses_on_a_live_held_lock_even_when_old(hook_worktree, monkeypatch, capsys):
    hook = _load_hook()
    gitdir = Path(_git(hook_worktree, "rev-parse", "--path-format=absolute", "--git-dir"))
    lock = gitdir / "index.lock"
    lock.write_bytes(b"")
    _backdate(lock, hook.STALE_LOCK_MIN_AGE_S + 60)
    monkeypatch.setattr(hook, "_live_pids_holding", lambda *a, **k: {12345})

    with pytest.raises(RuntimeError, match="refusing to run"):
        hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    assert lock.exists(), "a live-held lock must never be auto-deleted"

    # Frozen spec item 2: "a live/young/unconfirmed lock refuses with a bare
    # `::error` line starting the line". round-1 verify (9df97a50) fixed the
    # liveness probe's fail-open gap but left this refusal going out only
    # through log()/fail(), which prints "WorktreeCreate: refusing to run
    # ..." — no ::error token at all, and any token behind that prefix would
    # not start the line either way (house law: GitHub annotations must
    # START the line). This RED-first-failed before the fix in apply_sparse.
    blob = "".join(capsys.readouterr())
    error_lines = [ln for ln in blob.splitlines() if "::error" in ln]
    assert error_lines, f"no ::error annotation emitted for a refused lock:\n{blob}"
    assert any(ln.startswith("::error") for ln in error_lines), (
        f"::error annotation does not start its line:\n{blob}")


def test_hook_live_pids_holding_fails_closed_when_cwd_probe_is_untrustworthy(monkeypatch):
    """Frozen spec item 1: an unconfirmed probe is treated as LIVE (fail
    closed). round-1 verify (9df97a50) fixed this in
    scripts.worktree_sparse.gather_live_processes but left the hook's
    duplicate `_live_pids_holding` returning a confirmed (partial) result
    whenever the OTHER lsof call succeeded — dropping exactly the half that
    might have found the holder. This directly exercises the hook's own
    `_run_lsof` failure handling (the reviewer's exact gap: the existing
    suite only ever monkeypatched `_live_pids_holding` wholesale)."""
    hook = _load_hook()

    def fake_lsof(args):
        # cwd-scoped call (`-a -d cwd ...`) times out / is untrustworthy;
        # git-dir-scoped call succeeds with an empty (trustworthy) answer.
        return None if "cwd" in args else ""

    monkeypatch.setattr(hook, "_run_lsof", fake_lsof)
    monkeypatch.setattr(hook.platform, "system", lambda: "Darwin")

    result = hook._live_pids_holding(Path("/tmp/some-worktree"), Path("/tmp/some-worktree/.git"))

    assert result is None, (
        "a partially-failed lsof probe must return None (unconfirmed), not a "
        "confirmed-empty/partial pid set")


def test_hook_live_pids_holding_fails_closed_when_gitdir_probe_is_untrustworthy(monkeypatch):
    """Same gap, the other order: cwd probe succeeds, git-dir probe fails."""
    hook = _load_hook()

    def fake_lsof(args):
        return None if "cwd" not in args else ""

    monkeypatch.setattr(hook, "_run_lsof", fake_lsof)
    monkeypatch.setattr(hook.platform, "system", lambda: "Darwin")

    result = hook._live_pids_holding(Path("/tmp/some-worktree"), Path("/tmp/some-worktree/.git"))

    assert result is None


def test_hook_apply_sparse_no_longer_verifies_before_populate(hook_worktree):
    """MAJOR-1 (2026-09-07 round-2 review of macro #6971): `apply_sparse`
    itself must not verify the postcondition any more — `dest` is a freshly
    created `--no-checkout` worktree at this point, so nothing is physically
    present on disk yet regardless of what was selected. A tracked file
    re-materialized in the excluded dir BEFORE `apply_sparse` runs is
    therefore invisible to `apply_sparse` alone (it never inspects the
    filesystem for `big/`, only `git sparse-checkout set`'s own state) —
    demonstrating why the check had to move to `_verify_after_populate`,
    called only once `git read-tree -mu HEAD` has actually populated the
    tree (see the next two tests)."""
    hook = _load_hook()
    (hook_worktree / "big").mkdir(exist_ok=True)
    (hook_worktree / "big" / "data.json").write_bytes(_BIG_CONTENT)

    include, omitted = hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})

    assert omitted == ["big"]
    assert include == ["scripts"]


def test_hook_postcondition_after_populate_catches_a_tracked_file_reappearing(hook_worktree):
    """MAJOR-1 fix, RED-first against the real production call order: this
    drives the hook's actual sequence — `apply_sparse` (sparse-checkout
    set), then `git read-tree -mu HEAD` (exactly as `main()` does it) — and
    only THEN re-creates a tracked file (`big/data.json`, committed in the
    `hook_worktree` fixture) in the excluded dir, the shape a partial or
    interrupted prior materialize attempt would leave. Before the MAJOR-1
    fix, the postcondition ran inside `apply_sparse`, before `read-tree`
    populated anything, and could not see this at all — see
    `test_hook_apply_sparse_no_longer_verifies_before_populate` above, and
    `test_hook_postcondition_pre_populate_cannot_see_reintroduced_content`
    below, which pins that blind spot directly."""
    hook = _load_hook()
    include, omitted = hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    _git(hook_worktree, "read-tree", "-mu", "HEAD")
    assert not (hook_worktree / "big").exists(), (
        "fixture precondition: big/ is a clean husk immediately after read-tree")

    (hook_worktree / "big").mkdir(exist_ok=True)
    (hook_worktree / "big" / "data.json").write_bytes(_BIG_CONTENT)

    with pytest.raises(RuntimeError, match="sparse postcondition failed"):
        hook._verify_after_populate(hook_worktree, include, omitted)


def test_hook_postcondition_pre_populate_cannot_see_reintroduced_content(hook_worktree):
    """Pins the exact blind spot MAJOR-1 fixed: calling the raw postcondition
    predicate BEFORE `read-tree` (the old call order, when the check lived
    inside `apply_sparse`) cannot detect a tracked file that is about to
    reappear, because `_tracked_entries_present` only looks at what is
    physically on disk RIGHT NOW, and at this point in the sequence nothing
    is materialized yet — the same file that
    `test_hook_postcondition_after_populate_catches_a_tracked_file_reappearing`
    proves is caught once the check runs at the correct, post-`read-tree`
    point."""
    hook = _load_hook()
    include, omitted = hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    # Deliberately do NOT read-tree yet — this is the pre-fix call order.
    problem = hook._verify_sparse_postcondition(hook_worktree, include, omitted)
    assert problem is None, (
        f"pre-populate, the postcondition is structurally blind to any "
        f"re-materialized content — got a problem anyway: {problem!r}")


def test_hook_postcondition_ignores_untracked_survivor_but_warns(hook_worktree, capsys):
    """MAJOR-2 (ruling r2, amending the frozen spec): `big/` holds a stray
    (untracked) file after sparsify — `git sparse-checkout set` never
    touches untracked content outside the index, so it survives, and the
    excluded dir is no longer a husk — but this must only warn, never fail.
    RED-first: before this ruling, ANY entry in an excluded dir failed the
    postcondition here too. Drives the real call order: apply_sparse then
    read-tree then _verify_after_populate, exactly as `main()` does."""
    hook = _load_hook()
    include, omitted = hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    _git(hook_worktree, "read-tree", "-mu", "HEAD")
    (hook_worktree / "big").mkdir(exist_ok=True)
    (hook_worktree / "big" / "stray.txt").write_text("oops\n", encoding="utf-8")

    hook._verify_after_populate(hook_worktree, include, omitted)  # must not raise

    blob = "".join(capsys.readouterr())
    warning_lines = [ln for ln in blob.splitlines() if "::warning" in ln]
    assert any("untracked-survivor" in ln for ln in warning_lines), (
        f"no untracked-survivor ::warning emitted:\n{blob}")
    assert any(ln.startswith("::warning") for ln in warning_lines), (
        f"annotation did not open the line:\n{blob}")


def test_hook_main_verifies_postcondition_after_read_tree_not_before(tmp_path, monkeypatch):
    """MAJOR-1: pins the call ORDER inside the hook's real `main()` sequence
    directly (independent of any specific postcondition scenario) — the
    postcondition check must fire strictly after `git read-tree -mu HEAD`,
    never before."""
    hook = _load_hook()
    donor = tmp_path / "donor"
    donor.mkdir()
    _git(donor, "init", "-q", "-b", "main")
    _git(donor, "config", "user.email", "t@example.com")
    _git(donor, "config", "user.name", "t")
    (donor / "scripts").mkdir()
    (donor / "scripts" / "keep.txt").write_text("keep\n", encoding="utf-8")
    (donor / "big").mkdir()
    (donor / "big" / "data.json").write_bytes(_BIG_CONTENT)
    _git(donor, "add", "-A")
    _git(donor, "commit", "-qm", "base")
    _git(donor, "remote", "add", "origin", str(donor))  # self-remote: main() fetches origin/main

    monkeypatch.setattr(
        hook, "resolve_host", lambda toplevel, common, primary: donor,
    )
    monkeypatch.setattr(hook, "load_profile", lambda repo_root: {
        "enabled": True, "exclude_dirs": ["big"],
    })

    calls: list[str] = []
    real_git = hook.git

    def tracking_git(root, *args, **kwargs):
        if args and args[0] == "read-tree":
            calls.append("read-tree")
        return real_git(root, *args, **kwargs)

    real_verify = hook._verify_sparse_postcondition

    def tracking_verify(*a, **k):
        calls.append("verify")
        return real_verify(*a, **k)

    monkeypatch.setattr(hook, "git", tracking_git)
    monkeypatch.setattr(hook, "_verify_sparse_postcondition", tracking_verify)
    monkeypatch.setattr(
        hook.sys, "stdin",
        io.StringIO(json.dumps({"name": "pt6-order", "cwd": str(donor)})),
    )

    rc = hook.main()

    assert rc == 0, f"mint must succeed: calls so far {calls}"
    assert calls == ["read-tree", "verify"], (
        f"postcondition must run strictly after read-tree, got order {calls}")


# ── Minor (round-3 review of macro #6971): the hook's `_tracked_entries_present`
#    twin must also fail CLOSED on its own probe failure ────────────────────

def test_hook_tracked_entries_present_raises_on_a_failed_ls_tree(hook_worktree, monkeypatch):
    """Same fail-closed requirement as the script's copy: a failed
    `git ls-tree` must propagate, never be swallowed into `[]`."""
    hook = _load_hook()
    real_git = hook.git

    def flaky_git(root, *args, **kwargs):
        if args and args[0] == "ls-tree":
            raise RuntimeError("git ls-tree failed: boom")
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(hook, "git", flaky_git)

    with pytest.raises(RuntimeError):
        hook._tracked_entries_present(hook_worktree, "big")


def test_hook_postcondition_fails_loud_when_tracked_probe_fails(hook_worktree, monkeypatch):
    """RED-first: before this fix, the hook's `_tracked_entries_present`
    caught the `git` failure and returned `[]`, so `_verify_after_populate`
    read that as a clean pass instead of failing loud on a broken probe."""
    hook = _load_hook()
    include, omitted = hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})
    _git(hook_worktree, "read-tree", "-mu", "HEAD")

    real_git = hook.git

    def flaky_git(root, *args, **kwargs):
        if args and args[0] == "ls-tree":
            raise RuntimeError("git ls-tree failed: boom")
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(hook, "git", flaky_git)

    with pytest.raises(RuntimeError, match="sparse postcondition failed"):
        hook._verify_after_populate(hook_worktree, include, omitted)


def test_hook_reuse_warns_but_never_blocks_on_a_full_looking_worktree(
    hook_worktree, monkeypatch, capsys,
):
    """Idempotency contract: reuse must never fail the spawn, even when the
    reused tree looks unexpectedly FULL — it only warns loudly."""
    hook = _load_hook()
    monkeypatch.setattr(
        hook, "load_profile", lambda repo_root: {"enabled": True, "exclude_dirs": ["big"]},
    )
    (hook_worktree / "big").mkdir(exist_ok=True)
    (hook_worktree / "big" / "data.json").write_bytes(_BIG_CONTENT)

    hook._warn_if_reused_worktree_looks_full(hook_worktree, hook_worktree)
    blob = "".join(capsys.readouterr())

    assert "::warning" in blob and "worktree-sparse-reuse-full" in blob
    assert any(ln.startswith("::warning") for ln in blob.splitlines())


def test_hook_reuse_warning_never_raises_even_on_internal_error(hook_worktree, monkeypatch):
    hook = _load_hook()
    monkeypatch.setattr(
        hook, "load_profile", lambda repo_root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    hook._warn_if_reused_worktree_looks_full(hook_worktree, hook_worktree)  # must not raise


# ── Minor-1 (ruling r2): hook/script probe behavioural parity ──────────────

def test_hook_and_script_probe_fail_closed_identically_on_partial_lsof(monkeypatch):
    """The same partial-lsof scenarios must fail closed IDENTICALLY through
    both copies of the live-process probe — the script's
    `gather_live_processes` and the hook's duplicated `_live_pids_holding` —
    not just each pinned separately against its own expectation. Linux's
    `/proc` fallback is script-only (the hook is Darwin-only by design, per
    its own docstring/early return) and is deliberately not exercised here."""
    hook = _load_hook()
    monkeypatch.setattr(WS.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(hook.platform, "system", lambda: "Darwin")

    worktree_root = Path("/tmp/some-worktree")
    git_dir = Path("/tmp/some-worktree/.git")

    scenarios = {
        "cwd probe untrustworthy, gitdir probe clean":
            lambda args: (None if "cwd" in args else ""),
        "cwd probe clean, gitdir probe untrustworthy":
            lambda args: ("" if "cwd" in args else None),
        "both probes untrustworthy":
            lambda args: None,
    }

    for label, fake_lsof in scenarios.items():
        monkeypatch.setattr(WS, "_run_lsof", fake_lsof)
        monkeypatch.setattr(hook, "_run_lsof", fake_lsof)

        script_result = WS.gather_live_processes(worktree_root, git_dir)
        hook_result = hook._live_pids_holding(worktree_root, git_dir)

        assert script_result is None, (
            f"{label}: script must fail closed (None), got {script_result}")
        assert hook_result is None, (
            f"{label}: hook must fail closed (None), got {hook_result}")


# ── Minor-2 (ruling r2): a failed lock probe must fail closed, never proceed
#    with no lock check at all ────────────────────────────────────────────

def test_hook_lock_probe_failure_refuses_with_error_never_proceeds_unchecked(
    hook_worktree, monkeypatch, capsys,
):
    """`_lock_candidates` used to swallow a `git rev-parse --git-dir` failure
    into `[]`, which `_clear_stale_locks` cannot tell apart from "no lock
    files exist" — so `apply_sparse` proceeded straight into
    `git sparse-checkout` with NO lock check at all. It must instead refuse
    with a line-starting ::error, exactly like a live/young/unconfirmed
    lock."""
    hook = _load_hook()
    real_git = hook.git

    def selective_fake_git(root, *args, **kwargs):
        if args and args[0] == "rev-parse" and "--git-dir" in args:
            raise RuntimeError("git rev-parse --git-dir failed: boom")
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(hook, "git", selective_fake_git)

    with pytest.raises(RuntimeError, match="refusing to run"):
        hook.apply_sparse(hook_worktree, hook_worktree, "HEAD", {"big"})

    blob = "".join(capsys.readouterr())
    error_lines = [ln for ln in blob.splitlines() if "::error" in ln]
    assert error_lines, f"a failed lock probe must emit a ::error annotation:\n{blob}"
    assert any(ln.startswith("::error") for ln in error_lines), (
        f"::error annotation does not start its line:\n{blob}")
    assert "lock-probe-failed" in blob
