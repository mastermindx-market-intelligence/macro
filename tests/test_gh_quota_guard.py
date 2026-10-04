"""Tests for .claude/hooks/gh_quota_guard.py (PreToolUse shared-quota guard).

THE INCIDENT THIS ENCODES (2026-07-26). `gh` authenticates as ONE account token,
so REST's 5,000/hr `core` pool is a single bucket shared by every parallel
session, the babysitter lane, and the hooks. A session ran three 10-minute
`gh run watch` windows (gh's default interval is 3s, and each poll fetches the
run AND its ~130 jobs) on top of a background chain already polling the same run
every 45s, and emptied the pool — 403ing every other session for ~5 minutes,
including ship_loop_guard.py, which spends up to four REST calls per Stop and
FAILS CLOSED when rate-limited.

A memory note describing exactly this already existed; a second session hit it an
hour later anyway. Hence a hook: the deny matrix below IS the contract.

Runs the hook as a subprocess exactly as the harness does (JSON payload on
stdin). Contract: exit 0 always; a DENY prints hookSpecificOutput with
permissionDecision == "deny"; an ALLOW prints nothing.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "gh_quota_guard.py"
CODEX_HOOKS = ROOT / ".codex" / "hooks.json"


def test_trusted_codex_project_bash_pretooluse_is_bound_to_the_same_quota_guard():
    """Trusted Codex project layers carry the same repository CI-wait guard.

    The 2026-10-03 incident included a Codex principal spending 1,282 seconds in
    one foreground `gh run watch`. Prose cannot prevent that shape. This pins the
    checked-in defense-in-depth hook; Codex intentionally skips project-local hooks
    when the worktree/project layer is untrusted, so machine-wide coverage is a
    separate user-hook responsibility rather than something this test can claim.
    """
    config = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
    groups = config["hooks"]["PreToolUse"]
    bash_groups = [group for group in groups if group.get("matcher") == "^Bash$"]
    assert len(bash_groups) == 1
    handlers = bash_groups[0]["hooks"]
    matching = [
        handler for handler in handlers
        if ".claude/hooks/gh_quota_guard.py" in str(handler.get("command") or "")
    ]
    assert len(matching) == 1
    assert matching[0]["type"] == "command"
    assert int(matching[0]["timeout"]) <= 30


# In-process handle on the same file, for the ONE thing a subprocess cannot pin:
# that a command outside the guard's business spawns no probe at all. Everything
# else in this file still goes through the real stdin/stdout hook boundary.
_HOOK_SPEC = importlib.util.spec_from_file_location("gh_quota_guard", HOOK)
assert _HOOK_SPEC and _HOOK_SPEC.loader
GUARD = importlib.util.module_from_spec(_HOOK_SPEC)
_HOOK_SPEC.loader.exec_module(GUARD)

# ─────────────────────────────────────────────────────────────────────────────
# No test in this file may reach api.github.com
# ─────────────────────────────────────────────────────────────────────────────
#
# Deny shape 4 (2026-08-09) PROBES: the guard shells out to `gh run list` before
# it can judge a `gh workflow run ci.yml --ref main`. Left unstubbed that is a real
# REST call from the test suite — against the very shared pool this hook protects —
# and it would make the verdict depend on whether main happened to have a run in
# flight while CI was running. So `gh` itself is replaced on PATH, at the process
# boundary the hook actually uses. The default payload is "no runs at all", which is
# the pre-2026-08-09 behaviour: every older test in this file keeps its old answer.

_SHIM = """#!{python}
import os, sys
code = int(os.environ.get("GH_SHIM_EXIT", "0"))
if code:
    sys.stderr.write(os.environ.get("GH_SHIM_STDERR", "HTTP 403: rate limit exceeded"))
    sys.exit(code)
sys.stdout.write(os.environ.get("GH_SHIM_PAYLOAD", "[]"))
"""


@pytest.fixture(autouse=True)
def _gh_shim(tmp_path_factory, monkeypatch):
    shim_dir = tmp_path_factory.mktemp("ghshim")
    gh = shim_dir / "gh"
    gh.write_text(_SHIM.format(python=sys.executable), encoding="utf-8")
    gh.chmod(0o755)
    # Prepending to os.environ is what reaches the hook: the guard runs as a
    # subprocess and inherits this PATH.
    monkeypatch.setenv("PATH", f"{shim_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.delenv("GH_SHIM_EXIT", raising=False)
    monkeypatch.setenv("GH_SHIM_PAYLOAD", "[]")


def _stamp(minutes_ago: float) -> str:
    """RELATIVE to the wall clock on purpose — a frozen literal would age past the
    40-minute orphan bound and silently flip these tests at some future date."""
    when = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _runs(monkeypatch, *runs: dict) -> None:
    monkeypatch.setenv("GH_SHIM_PAYLOAD", json.dumps(list(runs)))


def _run_row(status: str, minutes_ago: float = 2, run_id: int = 31309720615) -> dict:
    return {
        "status": status,
        "createdAt": _stamp(minutes_ago),
        "databaseId": run_id,
        "url": f"https://example.test/run/{run_id}",
    }


def _raw(
    cmd: str,
    tool: str = "Bash",
    cwd=None,
    *,
    run_in_background: bool | None = None,
) -> subprocess.CompletedProcess:
    payload: dict = {"tool_name": tool, "tool_input": {"command": cmd}}
    if run_in_background is not None:
        payload["tool_input"]["run_in_background"] = run_in_background
    if cwd is not None:
        payload["cwd"] = str(cwd)          # the harness names the invoking checkout
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=30,
    )


def _run(
    cmd: str,
    tool: str = "Bash",
    cwd=None,
    *,
    run_in_background: bool | None = None,
) -> dict | None:
    proc = _raw(cmd, tool, cwd, run_in_background=run_in_background)
    assert proc.returncode == 0, "the guard must never brick the harness"
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    if not out:
        return None
    return json.loads(out).get("hookSpecificOutput")


def _denied(cmd: str, cwd=None, *, run_in_background: bool | None = None) -> bool:
    d = _run(cmd, cwd=cwd, run_in_background=run_in_background)
    return bool(d and d.get("permissionDecision") == "deny")


# ─────────────────────────────────────────────────────────────────────────────
# The burn, verbatim
# ─────────────────────────────────────────────────────────────────────────────

def test_the_exact_command_that_emptied_the_pool_is_denied():
    """Run three of these and the shared 5,000/hr core pool is gone."""
    assert _denied("gh run watch 30218680958 --exit-status --compact")


def test_gh_run_watch_default_interval_is_the_trap():
    """gh's default is --interval 3. Nothing in the command line says so, which
    is exactly why it slipped through review."""
    assert _denied("gh run watch 302186")
    assert _denied("gh run watch 302186 -i 3")
    assert _denied("gh run watch 302186 --interval 30")
    assert _denied("gh run view 302186 --watch")


def test_a_slow_explicit_interval_still_requires_background_execution():
    """Throttle and principal occupancy are separate gates."""
    for cmd in (
        "gh run watch 302186 --interval 60",
        "gh run watch 302186 --interval 150",
        "gh run watch 302186 -i 300",
    ):
        assert _denied(cmd)
        assert not _denied(cmd, run_in_background=True)


# ─────────────────────────────────────────────────────────────────────────────
# Poll loops
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sleep_s", [5, 30, 40, 45, 60, 89])
def test_gh_poll_loops_under_the_floor_are_denied(sleep_s):
    """Two watchers on one endpoint at 45s took 4,488 -> 0 in under an hour."""
    assert _denied(
        f"until [ x = y ]; do gh api repos/o/r/actions/runs/1; sleep {sleep_s}; done")


@pytest.mark.parametrize("sleep_s", [90, 150, 300])
def test_foreground_ci_poll_loops_are_denied_even_at_safe_quota_cadence(sleep_s):
    """A polite cadence still occupies the principal turn for the external wait."""
    cmd = f"until [ x = y ]; do gh api repos/o/r/actions/runs/1; sleep {sleep_s}; done"
    d = _run(cmd)
    assert d and d.get("permissionDecision") == "deny"
    assert "CI WAIT LOOP MUST BE ASYNC" in d["permissionDecisionReason"]
    assert not _denied(cmd, run_in_background=True)


def test_background_ci_poll_loop_returns_continue_work_context():
    d = _run(
        "for i in 1 2 3; do gh pr checks 4242; sleep 150; done",
        run_in_background=True,
    )
    assert d and d.get("permissionDecision") != "deny"
    context = d.get("additionalContext") or ""
    assert "CI WATCHER ARMED ASYNC" in context
    assert "Immediately start the next highest-value independent authorized project lane" in context


def test_slow_non_ci_gh_loop_remains_allowed():
    """The occupancy gate is CI-scoped; unrelated GitHub reads keep quota-only behavior."""
    assert not _denied("for i in 1 2 3; do gh api rate_limit; sleep 150; done")


def test_a_loop_with_no_sleep_at_all_is_denied():
    assert _denied("while true; do gh api rate_limit; done")


def test_a_loop_without_gh_is_none_of_the_guards_business():
    assert not _denied("for f in a b c; do echo $f; sleep 1; done")
    assert not _denied("until [ -s out.txt ]; do sleep 5; done")


# ─────────────────────────────────────────────────────────────────────────────
# --paginate over check-runs
# ─────────────────────────────────────────────────────────────────────────────

def test_paginate_over_check_runs_is_denied_either_argument_order():
    assert _denied('gh api "repos/o/r/commits/$SHA/check-runs?per_page=100" --paginate')
    assert _denied('gh api --paginate "repos/o/r/actions/runs/1/jobs"')


def test_a_single_page_of_jobs_is_allowed():
    """One page already answers 'is it still running'."""
    assert not _denied('gh api "repos/o/r/actions/runs/1/jobs?per_page=60"')


# ─────────────────────────────────────────────────────────────────────────────
# Ordinary work must not be impeded
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cmd", [
    "gh pr view 3748 --json state,mergedAt",
    "gh pr merge 3748 --squash --delete-branch",
    "gh pr create --title x --body y",
    "gh workflow run ci.yml --ref main",
    "gh api rate_limit --jq '.resources.core.remaining'",
    "gh api repos/o/r/actions/runs/1 --jq '.status'",
    "gh run rerun --failed 302186",
    "git log --oneline -3",
    "python -m pytest tests/ -q",
])
def test_ordinary_commands_pass(cmd):
    assert not _denied(cmd)


def test_non_bash_tools_are_ignored():
    assert _denied("gh run watch 1"), "control: this command IS denied on Bash"
    d = _run("gh run watch 1", tool="Edit")
    assert d is None, "the guard only inspects Bash"


def test_the_denial_explains_shared_cost_and_async_countermeasure():
    """A guard that only says no teaches nothing — name the non-blocking replacement."""
    d = _run("gh run watch 302186")
    reason = (d or {}).get("permissionDecisionReason", "")
    assert "shared" in reason.lower() or "every session" in reason.lower()
    assert "run_in_background=true" in reason
    assert "independent authorized project lane" in reason
    assert "watcher notification is the next CI event" in reason


def test_guard_fails_open_on_garbage_input():
    """A guard that bricks the harness is worse than a missed warning."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input=b"not json at all",
        capture_output=True, timeout=10)
    assert proc.returncode == 0
    assert proc.stdout.decode().strip() == ""


# ─────────────────────────────────────────────────────────────────────────────
# Writing ABOUT the trap must stay legal
# ─────────────────────────────────────────────────────────────────────────────
#
# Caught in production the first minute this hook was live: it denied the very
# commit that introduced it, because the commit message documents `gh run watch`.
# A guard that blocks its own postmortem is worse than no guard.

def test_a_commit_message_documenting_the_trap_is_not_denied():
    cmd = (
        "git commit -q -F - <<'MSG'\n"
        "fix(hooks): guard the shared GitHub quota\n\n"
        "A session ran three 10-minute `gh run watch` windows on top of a chain\n"
        "already polling every 45s. gh run watch defaults to --interval 3.\n"
        "MSG\n"
        "git push -q -u origin HEAD"
    )
    assert not _denied(cmd)


def test_prose_and_comments_mentioning_gh_run_watch_are_not_invocations():
    assert not _denied("echo 'never use gh run watch here'")
    assert not _denied("# gh run watch is banned; use a 150s loop")
    assert not _denied('git commit -m "drop gh run watch from the babysitter"')


def test_a_real_invocation_after_a_heredoc_is_still_caught():
    """Stripping heredocs must not blind the guard to the command beside them."""
    cmd = ("git commit -F - <<'MSG'\nsome message body\nMSG\n"
           "gh run watch 302186")
    assert _denied(cmd)


def test_heredoc_stripping_survives_two_heredocs():
    cmd = ("cat <<'A'\ngh run watch 1\nA\ncat <<'B'\ngh run watch 2\nB\necho done")
    assert not _denied(cmd)


# ─────────────────────────────────────────────────────────────────────────────
# A loop must actually CONTAIN the gh call
# ─────────────────────────────────────────────────────────────────────────────
#
# Second production false positive, minutes after the first: a verification
# command with `python3 -c "for m in ...: print(...)"` and an unrelated
# `gh api rate_limit` on the same line was denied as a "poll loop". Co-presence
# of a loop keyword and a gh call is not polling.

def test_a_python_for_loop_beside_an_unrelated_gh_call_is_not_a_poll_loop():
    cmd = (
        "git show origin/main:.claude/settings.json | python3 -c \""
        "import json,sys\n"
        "d=json.load(sys.stdin)\n"
        "for m in d['hooks']['PreToolUse']:\n"
        "    for h in m['hooks']: print(h)\n"
        "\"; gh api rate_limit --jq '.resources.core.remaining'"
    )
    assert not _denied(cmd)


def test_a_list_comprehension_beside_a_gh_call_is_not_a_poll_loop():
    assert not _denied(
        """python3 -c "print([x for x in range(3)])" && gh pr view 3797 --json state""")


def test_a_real_shell_loop_around_gh_is_still_caught():
    """The narrowing must not blind the guard to actual polling."""
    assert _denied("while true; do gh api repos/o/r/actions/runs/1; sleep 20; done")
    assert _denied("for i in $(seq 1 40); do gh pr checks 1; sleep 30; done")


def test_a_shell_loop_whose_body_has_no_gh_is_ignored_even_beside_gh():
    cmd = ("for f in a b c; do echo $f; sleep 1; done; "
           "gh api rate_limit --jq '.resources.core.remaining'")
    assert not _denied(cmd)


# ─────────────────────────────────────────────────────────────────────────────
# Shape 4: dispatching a main proof over one already in flight (2026-08-09)
# ─────────────────────────────────────────────────────────────────────────────
#
# THE LIVELOCK THIS ENCODES. ci.yml has no `push` trigger, so main is proven only
# by a workflow_dispatch, and every main-ref dispatch shares `ci-refs/heads/main`.
# With the flat `cancel-in-progress: true` that group had until this change, each
# pinned session re-firing the documented recovery lever KILLED the proof already
# running: run 31309720615 was cancelled 44 minutes in by dispatch 31311537537,
# itself cancelled 4 minutes later by 31311693575. No proof concluded, the
# sweeper's base-inherited-red refresh stayed closed, and 12 merge-blocked + 56
# cap-deferred pull requests could not drain (sweep run 31311549150).
#
# The workflows are fenced now, so a race is waste rather than destruction — but
# the reflex is what opened the wound, and waste on a 4-job 30-34 minute run is
# worth one REST call to prevent.

@pytest.mark.parametrize("workflow", ["ci.yml", "fences.yml", "integration-baseline.yml"])
def test_dispatching_a_proof_over_a_live_one_is_denied(monkeypatch, workflow):
    _runs(monkeypatch, _run_row("in_progress"))
    assert _denied(f"gh workflow run {workflow} --ref main")


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "requested"])
def test_every_non_completed_status_counts_as_in_flight(monkeypatch, status):
    """`status != completed` is the test, not a list of the two statuses someone
    remembered — `waiting` and `requested` are exactly what an earlier revision of
    merge_on_green's anti-stampede query missed."""
    _runs(monkeypatch, _run_row(status, minutes_ago=3))
    assert _denied("gh workflow run ci.yml --ref main")


def test_a_dispatch_with_no_live_run_is_the_documented_recovery_lever(monkeypatch):
    """The guard must not stand between a stale main and its fix."""
    _runs(monkeypatch,
          _run_row("completed", minutes_ago=30),
          _run_row("completed", minutes_ago=90, run_id=31148430602))
    assert not _denied("gh workflow run ci.yml --ref main")
    assert not _denied("gh workflow run ci.yml")          # no --ref: gh defaults to main


def test_no_runs_at_all_is_allowed(monkeypatch):
    _runs(monkeypatch)
    assert not _denied("gh workflow run ci.yml --ref main")


def test_an_orphaned_queued_run_may_be_dispatched_over(monkeypatch):
    """A queued run that never starts would otherwise block the lever forever."""
    _runs(monkeypatch, _run_row("queued", minutes_ago=95))
    assert not _denied("gh workflow run ci.yml --ref main")


def test_a_freshly_queued_run_is_not_an_orphan(monkeypatch):
    """Control for the mercy kill: the escape valve must not swallow the rule."""
    _runs(monkeypatch, _run_row("queued", minutes_ago=5))
    assert _denied("gh workflow run ci.yml --ref main")


def test_a_long_running_run_is_not_an_orphan(monkeypatch):
    """Only `queued` ages out. A run holding a runner for 95 minutes is the
    evidence being waited on — killing it is the livelock itself."""
    _runs(monkeypatch, _run_row("in_progress", minutes_ago=95))
    assert _denied("gh workflow run ci.yml --ref main")


def test_the_newest_in_flight_run_decides(monkeypatch):
    """An old completed run beside a live one must not read as 'free'."""
    _runs(monkeypatch,
          _run_row("in_progress", minutes_ago=4, run_id=31311537537),
          _run_row("completed", minutes_ago=200))
    d = _run("gh workflow run ci.yml --ref main")
    assert d and d.get("permissionDecision") == "deny"
    assert "31311537537" in d["permissionDecisionReason"], "must name the live run"


def test_an_off_main_dispatch_is_not_the_livelock(monkeypatch):
    """The group is per-ref; a branch dispatch cannot touch main's proof."""
    _runs(monkeypatch, _run_row("in_progress"))
    assert not _denied("gh workflow run ci.yml --ref claude/some-branch")
    assert not _denied("gh workflow run ci.yml --ref refs/heads/feature")


def test_a_workflow_that_is_not_a_main_proof_is_never_probed(monkeypatch):
    """render/daily dispatches are ordinary work and must stay free."""
    _runs(monkeypatch, _run_row("in_progress"))
    assert not _denied("gh workflow run render.yml --ref main")
    assert not _denied("gh workflow run daily.yml --ref main")


def test_flags_before_the_workflow_name_still_resolve(monkeypatch):
    """`--ref main ci.yml` must not read `main` as the workflow."""
    _runs(monkeypatch, _run_row("in_progress"))
    assert _denied("gh workflow run --ref main ci.yml")
    assert _denied("gh workflow run -R owner/repo ci.yml --ref main")
    assert _denied("gh workflow run .github/workflows/ci.yml --ref main")


def test_the_probe_failing_fails_open_and_says_so(monkeypatch):
    """ANTI-WASTE, NOT A SAFETY GATE. A fail-closed deny here would wedge the very
    recovery lever the guard protects — the exact shape of the livelock, one layer
    up. Rate limiting is the likeliest failure, and it is likeliest precisely when
    main is in trouble."""
    monkeypatch.setenv("GH_SHIM_EXIT", "1")
    proc = _raw("gh workflow run ci.yml --ref main")
    assert proc.returncode == 0
    assert proc.stdout.decode().strip() == "", "fail-open must ALLOW (stdout stays empty)"
    err = proc.stderr.decode()
    assert "fail-open" in err.lower(), f"the warning must be loud, got: {err!r}"
    assert "ci.yml" in err


def test_unparseable_probe_output_fails_open(monkeypatch):
    monkeypatch.setenv("GH_SHIM_PAYLOAD", "not json at all")
    assert not _denied("gh workflow run ci.yml --ref main")


def test_the_denial_teaches_livelock_and_requires_async_watch(monkeypatch):
    """A guard that only says no teaches nothing; it must name the async continuation."""
    _runs(monkeypatch, _run_row("in_progress", run_id=31309720615))
    d = _run("gh workflow run ci.yml --ref main")
    reason = (d or {}).get("permissionDecisionReason", "")
    assert "cancel" in reason.lower(), "must quote the livelock: a re-dispatch cancels"
    assert "31309720615" in reason, "must name the run already executing"
    assert "gh run watch 31309720615 --interval 150" in reason
    assert "run_in_background=true" in reason
    assert "continue another independent project lane" in reason
    assert "30-34" in reason


def test_foreground_watch_is_denied_even_at_a_polite_interval():
    """A 150s poll interval still wastes 30-45 minutes if the principal blocks on it."""
    d = _run("gh run watch 31309720615 --interval 150")
    assert d and d.get("permissionDecision") == "deny"
    assert "CI WATCH MUST BE ASYNC" in d["permissionDecisionReason"]


def test_exact_codex_incident_watch_is_denied():
    """The 2026-10-03 Codex principal spent 1,282s blocked on this exact shape."""
    cmd = (
        "gh run watch 37180044700 --repo mastermindx-market-intelligence/macro "
        "--interval 60 --exit-status"
    )
    d = _run(cmd)
    assert d and d.get("permissionDecision") == "deny"
    reason = d.get("permissionDecisionReason", "")
    assert "CI WATCH MUST BE ASYNC" in reason
    assert "run_in_background=true" in reason
    assert "continue the next independent authorized project lane" in reason


def test_background_watch_is_allowed_at_the_same_interval():
    """The exact watcher becomes legal when it cannot pin the principal turn."""
    assert not _denied(
        "gh run watch 31309720615 --interval 150",
        run_in_background=True,
    )


def test_background_flag_does_not_excuse_a_hot_three_second_watcher():
    """Asynchronous is not permission to burn the shared REST pool."""
    assert _denied("gh run watch 31309720615", run_in_background=True)
    assert _denied("gh run watch 31309720615 --interval 30", run_in_background=True)


def test_explicit_shell_detach_is_also_nonblocking():
    assert not _denied("gh run watch 31309720615 --interval 150 &")


def test_shell_and_and_is_not_mistaken_for_a_detach_marker():
    d = _run("gh run watch 31309720615 --interval 150 && echo finished")
    assert d and d.get("permissionDecision") == "deny"
    assert "CI WATCH MUST BE ASYNC" in d["permissionDecisionReason"]


def test_explicitly_detached_slow_ci_poll_loop_is_nonblocking():
    cmd = "for i in 1 2 3; do gh pr checks 4242; sleep 150; done &"
    assert not _denied(cmd)


def test_prose_about_the_dispatch_is_not_a_dispatch(monkeypatch):
    _runs(monkeypatch, _run_row("in_progress"))
    assert not _denied("echo 'never run gh workflow run ci.yml --ref main while one is live'")
    assert not _denied('git commit -m "guard gh workflow run ci.yml re-dispatches"')


# ─────────────────────────────────────────────────────────────────────────────
# CI evidence remains available; CI waiting is asynchronous (Chairman 2026-10-03)
# ─────────────────────────────────────────────────────────────────────────────
#
# The old shape-5 failure hid CI entirely after handoff. That remains forbidden:
# initial diagnosis and repair evidence must stay readable. The new rule is narrower:
# never spend a principal turn blocking on a watch process, and never re-read the
# same unchanged status inside the cooldown. Ownership is accountability, not idle time.

@pytest.mark.parametrize("cmd", [
    "gh pr checks 4242",
    "gh run view 31309720615",
    "gh run view 31309720615 --log-failed",
    'gh api "repos/acme/widgets/commits/$SHA/check-runs?per_page=100"',
    "gh api repos/acme/widgets/actions/runs/31309720615 --jq '.status'",
    "gh api repos/acme/widgets/actions/runs/1/jobs",
])
def test_initial_ci_observation_remains_legal(cmd):
    """One bounded diagnosis is legal; sleep/poll loops are watcher work, not diagnosis."""
    assert not _denied(cmd)


@pytest.mark.parametrize("cmd", [
    "gh run watch 31309720615 --interval 60",
    "gh run watch 31309720615 --interval 150",
    "gh run view 31309720615 --watch --interval 150",
    "gh pr checks 4242 --watch --interval 150",
])
def test_foreground_ci_watch_is_denied_regardless_of_interval(cmd):
    """Interval controls quota; background execution controls principal occupancy."""
    assert _denied(cmd)


@pytest.mark.parametrize("cmd", [
    "gh run watch 31309720615 --interval 60",
    "gh run watch 31309720615 --interval 150",
    "gh run view 31309720615 --watch --interval 150",
    "gh pr checks 4242 --watch --interval 150",
])
def test_background_ci_watch_is_legal_at_a_safe_interval(cmd):
    assert not _denied(cmd, run_in_background=True)


def test_no_gh_command_is_denied_merely_because_a_pull_request_is_armed():
    """The words that used to end a worker's life must not appear in any deny.

    A grep-level pin. The retired shape denied with "CI HANDOFF IN EFFECT" and
    told the session to print a terminal marker instead of finishing; it resolved
    that state through a now-deleted contract module loaded by file path. One
    lowercase substring covers the rule, its deny text, its marker, and its
    module, in every casing anyone would reintroduce them in.
    """
    assert "handoff" not in HOOK.read_text(encoding="utf-8").lower()


class _ExplodingSubprocess:
    """Any use at all is the failure — this records nothing, it just refuses."""

    def __init__(self):
        self.calls = []

    def run(self, *args, **kwargs):
        self.calls.append(args)
        raise AssertionError(f"a command outside shape 4 must spawn no subprocess: {args!r}")


@pytest.mark.parametrize("cmd", [
    "gh pr comment 4242 --body hi",
    "gh pr edit 4242 --add-label merge-on-green",
    "gh issue list",
    "gh api rate_limit --jq '.resources.core.remaining'",
    "gh pr create --title x --body y",
    "gh pr merge 4242 --squash",
    "gh pr view 4242 --json state",
    "gh run rerun --failed 302186",
    "gh run watch 302186 --interval 60",
    "gh pr checks 4242",
])
def test_a_command_outside_shape_four_costs_no_subprocess(monkeypatch, cmd):
    """ORDER IS THE CONTRACT: cheap regex first, subprocesses only after a match.

    Shape 4's probe is one REST call against the pool this hook exists to protect,
    so it may only ever be spent on an exact `gh workflow run <proof>` match.
    Pinned at the seam rather than by inspection.
    """
    exploding = _ExplodingSubprocess()
    monkeypatch.setattr(GUARD, "subprocess", exploding)
    assert GUARD.check(cmd, "/some/checkout") is None
    assert exploding.calls == []


def test_the_probe_gate_is_not_vacuous(monkeypatch):
    """Control for the test above: a real proof dispatch MUST reach the probe, or
    the no-subprocess pin would pass by matching nothing at all."""
    seen = []
    monkeypatch.setattr(GUARD, "live_proof_reason", lambda workflow: seen.append(workflow))
    assert GUARD.check("gh workflow run ci.yml --ref main", "/some/checkout") is None
    assert seen == ["ci.yml"], "the probe runs, and is told which workflow to look at"


def test_prose_about_the_quota_traps_is_not_an_invocation():
    """Writing ABOUT the trap stays legal — the lesson shape 1 learned in production
    the first minute it was live, when it blocked its own commit message."""
    assert not _denied("echo 'do not gh run watch at the default interval'")
    assert not _denied('git commit -m "deny gh pr checks in a tight loop"')


# ─────────────────────────────────────────────────────────────────────────────
# Shape 6 — production lanes a session may not stop
# ─────────────────────────────────────────────────────────────────────────────
#
# Prose forbade this from 2026-08-12 and did not bind: a live fleet session
# force-cancelled the US nightly's recovery dispatches SIX times (receipt: POST
# /actions/runs/31583415065/force-cancel), and stacked on the #5362 workflow-size
# strand the night before, Prophet US served Aug-10 picks for two full sessions.
#
# The 2026-08-14 addition is the WATCHDOG half. daily.yml and the render lanes are
# protected because killing one destroys data; nightly-liveness.yml and
# prophet-rescue.yml are protected because killing one destroys the only thing that
# would have NOTICED. That is the strictly worse outcome: a silenced alarm and a
# healthy night leave the same trace, which is the equivalence the whole outage
# turned on.

KILL_RECEIPT = "31583415065"          # the real run id from the 2026-08-12 receipt


def _lane(monkeypatch, workflow: str) -> None:
    """Make the guard's one `gh api … --jq .path` probe answer for `workflow`."""
    monkeypatch.setenv("GH_SHIM_PAYLOAD", f".github/workflows/{workflow}\n")


@pytest.mark.parametrize("workflow", sorted(GUARD.PROTECTED_LANES))
def test_no_protected_lane_may_be_stopped(monkeypatch, workflow):
    _lane(monkeypatch, workflow)
    assert _denied(f"gh run cancel {KILL_RECEIPT}"), workflow


@pytest.mark.parametrize("workflow", ["nightly-liveness.yml", "prophet-rescue.yml"])
def test_the_prophet_watchdog_lanes_are_protected(monkeypatch, workflow):
    """Named rather than only swept by the parametrize above: removing either entry
    from PROTECTED_LANES must red a test that says WHY it was there."""
    assert workflow in GUARD.PROTECTED_LANES
    _lane(monkeypatch, workflow)
    reason = GUARD.protected_cancel_reason(KILL_RECEIPT)
    assert reason and workflow in reason
    assert _denied(f"gh run cancel {KILL_RECEIPT}")


@pytest.mark.parametrize("cmd", [
    f"gh api -X POST repos/o/r/actions/runs/{KILL_RECEIPT}/cancel",
    f"gh api --method POST /repos/o/r/actions/runs/{KILL_RECEIPT}/force-cancel",
])
def test_both_rest_spellings_are_denied_for_a_watchdog_lane(monkeypatch, cmd):
    """The force-cancel spelling IS the 2026-08-12 receipt, so it is pinned by
    example rather than by inference."""
    _lane(monkeypatch, "prophet-rescue.yml")
    assert _denied(cmd)


def test_an_unprotected_lane_may_still_be_stopped(monkeypatch):
    """Control: without this, every test above could pass by denying everything."""
    _lane(monkeypatch, "ci.yml")
    assert not _denied(f"gh run cancel {KILL_RECEIPT}")


def test_an_unresolvable_run_fails_open(monkeypatch):
    """Fail-open like every other rule in this guard: if the probe cannot say which
    workflow a run belongs to, the guard must not brick the harness."""
    monkeypatch.setenv("GH_SHIM_EXIT", "1")
    assert not _denied(f"gh run cancel {KILL_RECEIPT}")


# ─────────────────────────────────────────────────────────────────────────────
# Shape 7 — re-reading the same status faster than it can change (2026-08-27,
# binding after Chairman ruling 2026-10-03)
#
# The measured failure was a background watcher ALREADY armed while the session
# still polled ~25 Stop cycles. The first read stays free; the immediate repeat
# is now denied so the session must consume the watcher and continue other work.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _poll_state(tmp_path, monkeypatch):
    """Isolate the cooldown ledger for subprocess and in-process checks."""
    monkeypatch.setenv("MACRO_GH_POLL_STATE_DIR", str(tmp_path / "cooldown"))
    monkeypatch.setattr(GUARD, "POLL_STATE_DIR", str(tmp_path / "cooldown"))
    return tmp_path


def test_first_read_of_a_status_shape_always_passes(_poll_state):
    """Initial diagnosis is never the waste; unchanged rereads are."""
    assert not _denied("gh pr checks 6555 --json name,bucket")


def test_immediate_reread_of_the_same_shape_is_denied(_poll_state):
    """The exact measured Stop-loop burn is mechanically closed."""
    assert not _denied("gh pr checks 6555 --json name,bucket")
    d = _run("gh pr checks 6555 --json name,bucket")
    assert d and d.get("permissionDecision") == "deny"
    reason = d.get("permissionDecisionReason", "")
    assert "REDUNDANT POLL" in reason
    assert "blocked" in reason
    assert "watcher" in reason
    assert "continue another authorized project lane" in reason
    assert "Stop hook" in reason


def test_a_different_run_or_pr_is_a_different_shape(_poll_state):
    """Polling one PR must never blind a session to another one."""
    assert not _denied("gh pr checks 6555")
    assert not _denied("gh pr checks 6554")
    assert not _denied("gh api repos/o/r/actions/runs/33129766342")


def test_the_window_self_clears(_poll_state):
    """Time-based only: the binding denial expires without a manual reset."""
    key = "pr-checks:6555"
    assert GUARD.poll_cooldown_nudge(key, now=1000.0) is None
    denied = GUARD.poll_cooldown_nudge(key, now=1001.0)
    assert denied and "REDUNDANT POLL" in denied
    assert GUARD.poll_cooldown_nudge(
        key, now=1000.0 + GUARD.POLL_COOLDOWN_S + 1
    ) is None


@pytest.mark.parametrize("cmd", [
    "gh pr edit 6555 --add-label merge-on-green",
    "gh pr merge 6555 --squash",
    "gh pr comment 6555 --body hi",
    "gh pr create --title x --body y",
])
def test_mutations_are_never_polls(_poll_state, cmd):
    """Repeating a mutation is a different mistake with a different remedy; this
    shape must not silently rate-limit the ship loop's own write path."""
    assert not _denied(cmd)
    assert not _denied(cmd)


def test_unwritable_state_fails_open(_poll_state, monkeypatch):
    """Unreadable cooldown state is not proof that a poll just happened."""
    monkeypatch.setenv("MACRO_GH_POLL_STATE_DIR", "/proc/nonexistent/cannot-create")
    assert not _denied("gh pr checks 6555")
    assert not _denied("gh pr checks 6555")


def test_a_command_denied_by_another_shape_does_not_start_the_cooldown(_poll_state):
    """Shape 7 runs LAST. If it recorded first, a denial would start a cooldown
    for a read that never reached GitHub, and the session would then be told to
    wait for a poll it never got to make."""
    hot = "gh run watch 123"                     # shape 1 denies this
    assert _denied(hot)
    # a denied command is not a poll, so an unrelated first read remains legal
    assert not _denied("gh pr checks 6555")


def test_a_heredoc_that_merely_mentions_polling_is_not_a_poll(_poll_state):
    """The trap this file was built around, one shape later: a heredoc body is
    DATA. Shape 1 once blocked its own introducing commit; shape 7 flagged the
    very edit that documents it, because main() passed the RAW command."""
    doc = (
        "python3 - <<'PY'\n"
        "text = 'one `gh pr checks <n>` per Stop-hook cycle while a 30-45 minute run finishes'\n"
        "PY"
    )
    assert not _denied(doc)
    assert not _denied(doc)
