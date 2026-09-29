"""tests/test_worktree_gc_launchd.py — the launchd wrapper must FAIL LOUDLY, never silently.

WHY THIS SUITE EXISTS (measured 2026-09-29 from the job's own logs, not from reasoning).
`~/Library/Logs/macro_worktree_gc/launchd.out.log` records 45 runs of the armed fleet sweeper.
**15 of them never reached a completion line** — they died mid-run — and every one of the 13
tracebacks in the sibling `launchd.err.log` is a `subprocess.TimeoutExpired`: **9 at
`RUN_TIMEOUT_S=3000` and 4 at `GIT_TIMEOUT_S=120`** (counted from the tracebacks' terminal
lines — counting every occurrence of the value also matches the exception's own command
repr, which inflates the git class). On each of those days the ratified
deleter removed nothing, and the only evidence anywhere was a traceback in a log nobody reads,
`launchctl list` showing a bare `1`, and `last_run.json` still cheerfully describing the last
SUCCESSFUL sweep from days earlier.

Two distinct defects, and the first is the interesting one:

  A. **The wrapper's graceful error handling was UNREACHABLE.** Its fetch fallback
     ("proceeding on last-known origin/main") and its fail-closed refusal on an unreadable
     policy file were both written correctly and neither could ever run, because a timeout
     RAISED out of `main()` before any returncode was consulted. Code that reviews as careful
     degradation, and in production is a traceback.
  B. **A failure was recorded nowhere a reader looks.** `last_run.json` is written by the tool
     and only on a completed sweep, so its name is a liar by omission.

COVERAGE
  1. `_git` returns rc=124 on timeout instead of raising (the fix that makes A reachable)
  2. a FETCH timeout no longer kills the run — the sweep still executes (A, end to end)
  3. an unreadable primary refuses, explains the TCC wall, and files a receipt
  4. a primary-read TIMEOUT is explained rather than traced, and refuses
  5. a policy file unreadable from origin/main refuses AND never starts the sweep
  6. a sweep timeout returns 3, states that nothing is half-applied, files a receipt
  7. the failure receipt is a DIFFERENT file from `last_run.json` (B — never clobbers it)
  8. a SUCCESSFUL run files a receipt too, so "no receipt" and "stale receipt" differ
  9. raising either timeout is a policy change that must re-justify itself in the source
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import worktree_gc_launchd as wrapper

CP = subprocess.CompletedProcess


def _git_ok(args, kw):
    """A primary that answers everything: rev-parse, fetch, and both policy blobs."""
    if args[1] == "show" or "show" in args:
        return CP(args, 0, b"# extracted policy bytes\n", b"")
    return CP(args, 0, b".git\n", b"")


def _install(monkeypatch, tmp_path, git=_git_ok, sweep=None):
    """Replace subprocess.run for both the git reads and the sweep; redirect the receipt.

    Both the wrapper's git calls and its sweep go through `subprocess.run`, so one seam covers
    the whole wrapper. Every call is recorded: several assertions below are about what the
    wrapper did NOT do (start a sweep it had no policy for), which a return value cannot show.
    """
    seen: list[tuple] = []

    def fake_run(args, **kw):
        args = tuple(str(a) for a in args)
        seen.append(args)
        if args[0] == "git":
            return git(args, kw)
        if sweep is not None:
            return sweep(args, kw)
        return CP(args, 0, b"", b"")

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    monkeypatch.setattr(wrapper, "RECEIPT", tmp_path / "last_attempt.json")
    return seen


def _sweeps(seen):
    return [a for a in seen if "--apply" in a]


def _receipt(tmp_path):
    p = tmp_path / "last_attempt.json"
    assert p.exists(), "no receipt was written — a failure recorded nowhere is the defect itself"
    return json.loads(p.read_text())


# ── 1. the fix itself ────────────────────────────────────────────────────────

def test_a_git_timeout_returns_124_instead_of_raising(monkeypatch, tmp_path):
    """The one-line root cause. `_git` raising is what made every downstream path dead code."""
    def boom(args, kw):
        raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.GIT_TIMEOUT_S)

    _install(monkeypatch, tmp_path, git=boom)
    got = wrapper._git("rev-parse", "--git-dir")     # must NOT raise
    assert got.returncode == 124, "a timeout must surface as a returncode, not an exception"
    assert b"timed out" in got.stderr, "the reason has to travel with the code"


def test_a_fetch_timeout_no_longer_kills_the_run(monkeypatch, tmp_path, capsys):
    """The wrapper ALREADY intended to survive a failed fetch. Now it can.

    This is the end-to-end proof for defect A: the fallback branch the author wrote
    (`proceeding on last-known origin/main`) is only reachable once a timeout is a returncode,
    and the run must go on to actually sweep. Before the fix this test raised TimeoutExpired.
    """
    def git(args, kw):
        if "fetch" in args:
            raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.GIT_TIMEOUT_S)
        return _git_ok(args, kw)

    seen = _install(monkeypatch, tmp_path, git=git)
    assert wrapper.main() == 0
    assert _sweeps(seen), "a fetch timeout must not stop the sweep — stale policy is still policy"
    assert "proceeding on last-known" in capsys.readouterr().out


# ── 2. every refusal is legible and receipted ────────────────────────────────

def test_an_unreadable_primary_refuses_explains_tcc_and_files_a_receipt(monkeypatch, tmp_path):
    def git(args, kw):
        return CP(args, 128, b"", b"fatal: Operation not permitted: '/Users/x/Documents'")

    seen = _install(monkeypatch, tmp_path, git=git)
    assert wrapper.main() == 1
    assert not _sweeps(seen), "a deleter that cannot read its vantage point must not sweep"
    rec = _receipt(tmp_path)
    assert rec["stage"] == "read-primary" and rec["status"] == "refused"
    assert "not permitted" in rec["detail"].lower()


def test_a_primary_read_timeout_is_explained_rather_than_traced(monkeypatch, tmp_path, capsys):
    """4 of the 13 recorded tracebacks are this, and it used to produce ONLY a traceback."""
    def boom(args, kw):
        raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.GIT_TIMEOUT_S)

    seen = _install(monkeypatch, tmp_path, git=boom)
    assert wrapper.main() == 1                       # reasoned refusal, not an exception
    assert not _sweeps(seen)
    out = capsys.readouterr().out
    assert "GIT_TIMEOUT_S" in out, "the refusal must name the limit it hit"
    assert "promisor" in out, "and why a git read here can be a network operation at all"
    rec = _receipt(tmp_path)
    assert rec["stage"] == "read-primary" and "timed out" in rec["detail"]


def test_policy_unreadable_from_main_refuses_and_never_starts_the_sweep(monkeypatch, tmp_path):
    """Fail-closed on policy is the whole reason the wrapper re-reads origin/main every run."""
    def git(args, kw):
        if "show" in args:
            return CP(args, 128, b"", b"fatal: path does not exist in 'origin/main'")
        return CP(args, 0, b".git\n", b"")

    seen = _install(monkeypatch, tmp_path, git=git)
    assert wrapper.main() == 1
    assert not _sweeps(seen), "no policy means no sweep — blind must mean stop, for a deleter"
    rec = _receipt(tmp_path)
    assert rec["stage"] == "extract-policy" and rec["status"] == "refused"


# ── 3. the sweep's own cap ───────────────────────────────────────────────────

def test_a_sweep_timeout_returns_3_and_states_nothing_is_half_applied(monkeypatch, tmp_path,
                                                                     capsys):
    def sweep(args, kw):
        raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.RUN_TIMEOUT_S)

    _install(monkeypatch, tmp_path, sweep=sweep)
    assert wrapper.main() == 3, "a timeout needs its OWN code — `1` cannot be told from a refusal"
    out = capsys.readouterr().out
    assert "TIMED OUT" in out and "half-applied" in out
    rec = _receipt(tmp_path)
    assert rec["stage"] == "sweep" and rec["status"] == "timeout"
    assert rec["elapsed_s"] >= 0 and rec["run_timeout_s"] == wrapper.RUN_TIMEOUT_S


def test_the_receipt_is_a_different_file_from_last_run_json(monkeypatch, tmp_path):
    """Defect B, pinned structurally rather than by hoping.

    `last_run.json` means "the last COMPLETED sweep" and other tooling reads it that way, so the
    failure path must not overwrite it — while ALSO not being silent. Two files, two meanings.
    """
    def sweep(args, kw):
        raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.RUN_TIMEOUT_S)

    seen = _install(monkeypatch, tmp_path, sweep=sweep)
    assert wrapper.main() == 3
    argv = _sweeps(seen)[0]
    json_out = Path(argv[argv.index("--json-out") + 1])
    assert json_out.name == "last_run.json"
    assert wrapper.RECEIPT != json_out, "the failure receipt must not be the success record"

    # Deliberately structural rather than filesystem-observed: `last_run.json` is a REAL file on
    # the host running this suite, so asserting on its contents would make the test depend on
    # whether that host's sweeper happened to succeed recently. The guarantee that matters is
    # that the wrapper writes exactly one path of its own, and `last_run.json` reaches it only
    # as an argument handed to the tool.
    src = Path(wrapper.__file__).with_suffix(".py").read_text()
    assert src.count(".write_text(") == 1 and "RECEIPT.write_text(" in src, \
        "the wrapper must write exactly one file of its own, and it must be the receipt"
    assert src.count(".write_bytes(") == 1 and "target.write_bytes(" in src, \
        "its only other write is the extracted policy, into the run's own temp dir"


def test_a_successful_run_files_a_receipt_too(monkeypatch, tmp_path):
    """Without this, a monitor cannot distinguish "never ran" from "ran and failed days ago"."""
    _install(monkeypatch, tmp_path)
    assert wrapper.main() == 0
    rec = _receipt(tmp_path)
    assert rec["stage"] == "sweep" and rec["status"] == "completed"
    assert "started" in rec and rec["elapsed_s"] >= 0


def test_a_nonzero_tool_exit_is_recorded_as_such_not_as_completed(monkeypatch, tmp_path):
    """armed:false self-gates to exit 2; that is a real outcome and must not read as success."""
    _install(monkeypatch, tmp_path, sweep=lambda args, kw: CP(args, 2, b"", b""))
    assert wrapper.main() == 2
    assert _receipt(tmp_path)["status"] == "tool-nonzero"


# ── 4. the tempting wrong fix ────────────────────────────────────────────────

def test_raising_a_timeout_is_a_policy_change_that_must_re_justify_itself():
    """A bigger number is the obvious fix and it is the wrong one.

    A successful sweep here finishes in about 9 minutes; the failing runs exceed 50. They are
    5x slower, not marginally over, so a larger cap hides the cause instead of addressing it.
    Whoever does raise it should have a measurement — and this test makes them edit the
    paragraph that states the reasoning in the same act, which is the only enforcement a
    constant can really carry.
    """
    src = Path(wrapper.__file__).with_suffix(".py").read_text()
    assert "DELIBERATELY NOT RAISED" in src, \
        "the reasoning paragraph beside the constants is load-bearing; do not delete it"
    assert wrapper.GIT_TIMEOUT_S == 120
    assert wrapper.RUN_TIMEOUT_S == 3000


def test_the_receipt_never_becomes_a_gate(monkeypatch, tmp_path, capsys):
    """Diagnostics must not be able to stop a deleter from refusing."""
    _install(monkeypatch, tmp_path)
    monkeypatch.setattr(wrapper, "RECEIPT", tmp_path / "nope" / "x" / "last_attempt.json")

    def no_mkdir(*a, **kw):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(wrapper.Path, "mkdir", no_mkdir)
    assert wrapper.main() == 0, "an unwritable receipt must not change the run's outcome"
    assert "could not write" in capsys.readouterr().out


@pytest.mark.parametrize("stage", ["read-primary", "extract-policy", "sweep"])
def test_every_receipt_carries_the_limits_it_was_judged_against(monkeypatch, tmp_path, stage):
    """An elapsed time means nothing without the cap it was measured against."""
    def git(args, kw):
        if stage == "read-primary":
            return CP(args, 128, b"", b"fatal: nope")
        if stage == "extract-policy" and "show" in args:
            return CP(args, 128, b"", b"fatal: nope")
        return _git_ok(args, kw)

    def sweep(args, kw):
        if stage == "sweep":
            raise subprocess.TimeoutExpired(cmd=args, timeout=wrapper.RUN_TIMEOUT_S)
        return CP(args, 0, b"", b"")

    _install(monkeypatch, tmp_path, git=git, sweep=sweep)
    wrapper.main()
    rec = _receipt(tmp_path)
    assert rec["stage"] == stage
    assert rec["git_timeout_s"] == wrapper.GIT_TIMEOUT_S
    assert rec["run_timeout_s"] == wrapper.RUN_TIMEOUT_S
