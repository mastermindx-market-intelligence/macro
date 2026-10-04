#!/usr/bin/env python3
"""PreToolUse guard: keep one session from eating the shared GitHub REST quota.

WHY THIS EXISTS (2026-07-26, twice in one day, two different sessions).
`gh` authenticates as ONE account token, so REST's 5,000/hr `core` pool is a
single bucket shared by every parallel Claude session, the babysitter lane, and
the hooks themselves. Burning it does not slow one session down, it 403s all of
them for up to an hour.

The sharpest bite is self-inflicted: `.claude/hooks/ship_loop_guard.py` spends up
to four REST calls per Stop evaluation and FAILS CLOSED on rate limiting. So
polling hard to watch CI blocks the very Stop the watching was meant to reach.

A memory note (`ci-poll-quota-and-false-settle`) already described all of this,
and a session walked into it an hour after another session wrote it down. Notes
do not bind; a hook does. This denies only the three shapes that provably burned
the pool, and fails OPEN on everything else — a guard that bricks the harness is
worse than a missed warning.

  1. Any foreground `gh run watch` / `gh run view --watch`. Even a polite
     interval pins the principal Bash turn for a 30-45 minute external wait.
     Exactly one watcher must run asynchronously (tool `run_in_background=true`
     or an explicitly detached shell); its notification is the next CI event.
     The old default-3s variant also exhausted the shared REST pool.
  2. A foreground CI-status sleep/poll loop at ANY cadence, plus any `gh` poll
     loop sleeping under 90s. A 150s loop is gentle on quota but still pins the
     principal turn for 30-45 minutes; two watchers on one endpoint at 45s took
     4,488 -> 0 in under an hour. Async/background loops remain eligible at the
     quota floor because they do not occupy principal reasoning capacity.
  3. `--paginate` against check-runs/jobs. ~130 checks is several pages per poll,
     and one page already answers "is it still running".
  4. Re-dispatching a main PROOF workflow (ci.yml / fences.yml /
     integration-baseline.yml) while one is already in flight on main
     (2026-08-09). This one is not about request count, it is about the same
     reflex: a pinned session re-firing the documented recovery lever. Until
     that day every main dispatch of ci.yml landed in `ci-refs/heads/main` with
     a flat `cancel-in-progress: true`, so the second dispatch did not queue —
     it KILLED the first. Measured: run 31309720615 was cancelled 44 minutes in
     by dispatch 31311537537, itself cancelled 4 minutes later by 31311693575,
     while 12 merge-blocked + 56 cap-deferred pull requests waited on a proof
     that could therefore never conclude. The workflows are fixed (the flag is
     event-conditional as of the same day), so a race is now merely wasteful
     rather than destructive — but the reflex is what opened the wound, and a
     run already holding a runner is the fastest proof available. Allowed when
     the in-flight run is an orphan (queued > 40 min), and fail-OPEN on any
     probe error: this guard is anti-waste, and a fail-closed deny would wedge
     the very recovery lever it protects.
  6. CANCELLING A PRODUCTION LANE (2026-08-12). Not a quota shape at all — the
     same reflex, one step further. A live fleet session force-cancelled the US
     nightly's recovery dispatches six times (receipt: POST
     /actions/runs/31583415065/force-cancel); stacked on the #5362 workflow-size
     strand the night before, Prophet US served Aug-10 picks for two full
     sessions and the operator found it by looking at the site. A cancel is
     invisible to every staleness instrument we own, because a killed bake and a
     bake that never fired leave the same trace: nothing. CLAUDE.md already
     forbade this in prose ("never cancel or manually re-run an in-progress
     render, engine-render or daily merely to unblock this session"); prose did
     not bind. Denies a cancel aimed at a data-advancing or publishing lane and
     fails OPEN when the run cannot be resolved — an operator can still kill a
     genuinely wedged run, that is just no longer something a session does on
     its own initiative.

  7. RE-READING THE SAME CI STATUS FASTER THAN IT CAN CHANGE (2026-08-27, the
     SECOND time an operator has had to say it). Not a loop and not a hot
     `--interval`, so shapes 1-2 never saw it: a session answers each Stop-hook
     block with one more single `gh pr checks <n>`. Measured that day: ~25
     consecutive Stop cycles, each one poll, while 12 ci-packs ran — and the
     session already had a background watcher armed at 150s that was reporting
     every transition for free. The operator: "how come u check it so often...
     literally u can just check every 5 mins or something, not every 20
     seconds". A ci.yml run here takes 30-45 minutes, so a read 20 seconds after
     the last one cannot return a different answer; it is pure shared-pool spend
     plus a full context re-read every turn.
     The mechanism that defeats prose here is worth naming, because it is not
     laziness: the Stop hook fires on EVERY turn and escalates to "If the same
     genuine blocker persists after another attempt, finish with SHIP LOOP
     BLOCKED", which reads as a demand to demonstrate a fresh attempt. It is
     not. While independent authorized work remains, a blocked Stop means
     continue that work immediately; only when the watched wait is the sole
     remaining lane does the existing external-wait boundary become relevant.
     A memory note (`never-poll-ci-with-short-cycle-checks`) said all of this after the first
     operator order on 2026-08-24 and did not bind, which is the same reason
     shapes 1 and 6 exist as code.
     The 2026-10-03 Chairman ruling closes the advisory loophole: a REPEAT of
     the same status shape inside POLL_COOLDOWN_S is denied. The first read of a
     shape is still free, a different run/PR is a different shape, writes are
     never polls, and the window self-clears. This is deliberately narrow: it
     prevents no initial diagnosis and no repair mutation; it prevents spending
     another principal reasoning turn on unchanged external state.

A session remains accountable for its pull request through merge/live verification,
but accountability is not foreground occupation. Exactly one asynchronous watcher
owns each pending CI wait while the session advances another authorized lane.
Initial diagnosis and terminal-event investigation remain available; repeated
unchanged reads and foreground watch processes are denied. Empty/403 is UNKNOWN,
never settled.
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

MIN_SLEEP = 90       # seconds between gh polls in a loop
MIN_WATCH_INTERVAL = 60
#: A queued run older than this is presumed orphaned (GitHub has scheduled runs that
#: never start — see the "queued run can be ORPHANED" note). Re-dispatching over one
#: is the mercy kill, so the guard must not stand in its way. Well above a run's own
#: 30-34 minute duration, so a healthy in-flight proof never trips it.
ORPHANED_QUEUE_MINUTES = 40
#: One `gh run list` call. Bounded so a hung probe cannot hang the harness.
PROBE_TIMEOUT_S = 20
#: The workflows whose runs on main ARE main's proof (merge_on_green.MAIN_PROOF_WORKFLOWS
#: plus the circuit breaker's baseline). Dispatching any of them over a live one is the
#: shape this guard exists to stop.
PROOF_WORKFLOWS = ("ci.yml", "fences.yml", "integration-baseline.yml")

#: Lanes whose runs a session may NOT cancel (shape 6). These are the lanes that
#: advance data or publish the site: killing one costs a session of ledger the next
#: night cannot re-derive, and the loss is invisible to every staleness instrument
#: because a cancelled run looks exactly like a bake that never fired.
#: The second family (2026-08-14) is the WATCHDOGS over those lanes. They advance
#: no data, so the first rationale does not reach them — but killing one is strictly
#: worse than killing a bake: it removes the only thing that would have noticed. A
#: silenced alarm and a healthy night are the same trace, which is the exact
#: equivalence that let Prophet US serve Aug-10 picks for two sessions.
PROTECTED_LANES = frozenset({
    "daily.yml",            # Build B — the sole authoritative, ledger-advancing bake
    "closing-bell.yml",     # Build A — the provisional close render
    "asia-close.yml",       # the CN/HK bake
    "render.yml",
    "engine-render.yml",
    "weekly.yml",
    "nightly-liveness.yml",  # dead-man switch over daily.yml (detects)
    "prophet-rescue.yml",    # bounded self-heal over daily.yml (responds)
})

#: Shape 7. The operator's own number ("every 5 mins or something"), and comfortably
#: shorter than the 30-45 minute ci.yml run any repeat read is waiting on, so honouring
#: it can never cost a session real information.
POLL_COOLDOWN_S = 300
#: Cheap read-only status shapes that a waiting session repeats. Deliberately narrow:
#: mutations (`gh pr edit`, `gh pr merge`, `gh pr comment`) and one-shot creates are not
#: here, and never become "polls" no matter how often they run.
POLL_SHAPES = (
    (re.compile(r"\bgh\s+pr\s+checks\b[^|;&]*?(?P<id>\d+)"), "pr-checks"),
    (re.compile(r"\bgh\s+pr\s+view\b[^|;&]*?(?P<id>\d+)[^|;&]*?--json"), "pr-view"),
    (re.compile(r"\bgh\s+run\s+view\b[^|;&]*?(?P<id>\d+)"), "run-view"),
    (re.compile(r"\bgh\s+api\b[^|;&]*?/actions/runs/(?P<id>\d+)(?![^|;&]*?(?:/cancel|/force-cancel|/rerun))"), "run-api"),
)
#: A write is never a poll, however often it repeats. `gh api ... --method POST` and
#: the cancel/rerun paths are mutations that other shapes already govern.
POLL_WRITE_RE = re.compile(r"(?:--method|-X)\s+(?:POST|PATCH|PUT|DELETE)\b|/cancel\b|/force-cancel\b|/rerun\b", re.I)
#: Material self-mutations invalidate a prior status observation. Shape 7 is an
#: anti-babysitting fence, never a claim that state cannot change after we push/edit.
PR_MUTATION_RE = re.compile(
    r"\bgh\s+pr\s+(?:edit|ready|merge|close|reopen|review|comment)\b[^|;&]*?(?P<id>\d+)",
    re.I,
)
RUN_MUTATION_RE = re.compile(
    r"\bgh\s+run\s+(?:rerun|cancel)\b[^|;&]*?(?P<id>\d+)"
    r"|\bgh\s+api\b[^|;&]*/actions/runs/(?P<api_id>\d+)/(?:rerun|cancel|force-cancel)",
    re.I,
)
RUN_WATCH_ID_RE = re.compile(r"\bgh\s+run\s+watch\s+(?P<id>\d+)\b", re.I)
PR_WATCH_ID_RE = re.compile(
    r"\bgh\s+pr\s+checks\s+(?P<id>\d+)\b[^|;&\n]*--watch\b", re.I
)
#: Shared across every worktree of this clone on purpose: the REST pool they are
#: spending is one bucket, so two sibling sessions polling the same run alternately
#: is the same waste as one session polling twice as fast.
POLL_STATE_DIR = os.environ.get("MACRO_GH_POLL_STATE_DIR") or os.path.join(
    tempfile.gettempdir(), "macro-gh-poll-cooldown"
)


def poll_shape(cmd: str):
    """Return a stable key for a repeatable status read, or None."""
    if POLL_WRITE_RE.search(cmd):
        return None
    for rx, name in POLL_SHAPES:
        m = rx.search(cmd)
        if m:
            return f"{name}:{m.group('id')}"
    return None


def _poll_state_path(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(POLL_STATE_DIR, f"{digest}.json")


def clear_poll_cooldown_for_mutation(cmd: str):
    """Forget only observations that an explicit GitHub mutation invalidates.

    Shape 7 is shared across worktrees because the REST quota is shared. Do NOT clear
    the whole fleet ledger on an unrelated git push: that would turn normal fleet
    activity into a polling bypass. PR metadata mutations reopen one PR-view; run
    mutations reopen one run read. Check-status observation stays with the watcher.
    Fail open: this ledger is an efficiency fence, never lifecycle or authority state.
    """
    try:
        keys = set()
        for match in PR_MUTATION_RE.finditer(cmd):
            pr = match.group("id")
            keys.add(f"pr-view:{pr}")
        for match in RUN_MUTATION_RE.finditer(cmd):
            run_id = match.group("id") or match.group("api_id")
            if run_id:
                keys.update((f"run-view:{run_id}", f"run-api:{run_id}"))
        for key in keys:
            try:
                os.unlink(_poll_state_path(key))
            except FileNotFoundError:
                pass
    except Exception:
        return


def record_poll_observation(key: str, now: float | None = None):
    """Record `key` as observed without treating an existing record as an error."""
    now = time.time() if now is None else now
    try:
        os.makedirs(POLL_STATE_DIR, exist_ok=True)
        with open(_poll_state_path(key), "w", encoding="utf-8") as fh:
            json.dump({"at": now, "key": key}, fh)
    except Exception:
        return


def poll_cooldown_nudge(key: str, now: float | None = None):
    """Deny reason for a repeat of `key` inside the cooldown, or None.

    The first read remains free, a different PR/run remains a different shape, and
    writes are never polls. A material self-mutation clears the affected stale-read
    fence before this check. The Chairman's 2026-10-03 ruling closes the old advisory
    loophole after repeated sessions burned full reasoning turns re-reading unchanged
    CI while a watcher was already armed. State failure still fails open."""
    now = time.time() if now is None else now
    try:
        os.makedirs(POLL_STATE_DIR, exist_ok=True)
        path = _poll_state_path(key)
        last = 0.0
        try:
            with open(path, encoding="utf-8") as fh:
                last = float((json.load(fh) or {}).get("at") or 0.0)
        except FileNotFoundError:
            last = 0.0
        except Exception:
            last = 0.0          # unreadable state is not evidence of a recent poll
        waited = now - last
        if 0 < waited < POLL_COOLDOWN_S:
            return (
                f"SHARED GITHUB QUOTA - REDUNDANT POLL: you already read `{key}` "
                f"{int(waited)}s ago. "
                f"A ci.yml run here takes 30-45 minutes, so re-reading it inside "
                f"{POLL_COOLDOWN_S}s cannot return a different answer - it just spends "
                f"the pool every session shares and re-reads your whole context.\n\n"
                f"This repeat is blocked for another {POLL_COOLDOWN_S - int(waited)}s. "
                f"Do not spend a reasoning cycle waiting for the timer.\n\n"
                f"If a background/native watcher is already armed, its notification IS "
                f"the next CI event; immediately continue another authorized project lane. "
                f"If one is not armed, arm exactly one asynchronously, then move on.\n\n"
                f"The Stop hook firing every turn is NOT a demand for a fresh poll. "
                f"Pending CI freezes the PR release lane, not the whole mission."
            )
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"at": now, "key": key}, fh)
    except Exception:
        return None             # fail open, always
    return None


REMEDY = (
    "Arm exactly one asynchronous watcher instead of waiting in the principal turn:\n"
    "  gh run watch $RUN --interval 150\n"
    "Launch that Bash call with run_in_background=true (or explicitly detach it), "
    "then immediately continue another independent authorized project lane. "
    "The watcher notification is the next CI observation. A direct status read is "
    "for initial diagnosis or watcher recovery, not a second watcher. An empty/403 "
    "response is UNKNOWN, never green."
)

# Heredoc bodies are DATA, not commands. Caught in production the first minute
# this hook was live: it blocked the very commit that introduced it, because the
# commit message documents `gh run watch`. A guard that forbids writing ABOUT the
# trap is worse than useless — it stops the fix and the postmortem.
HEREDOC_RE = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*\2\s*$",
    re.S | re.M,
)


def strip_heredocs(cmd: str) -> str:
    """Remove heredoc bodies so prose about gh is not read as gh invocations."""
    prev = None
    out = cmd
    while prev != out:                     # nested / successive heredocs
        prev = out
        out = HEREDOC_RE.sub("<<HEREDOC", out)
    return out


# A gh call only counts at a COMMAND position: start, or after a separator
# (; && || | & newline) or a loop keyword. Keeps "# never use gh run watch" and
# `-m "...gh run watch..."` prose from reading as an invocation.
CMD_POS = r"(?:^|[;&|\n(]|\b(?:do|then|else)\s)\s*"
# Native blocking watch forms: `gh run watch`, `gh run view --watch`,
# and `gh pr checks --watch`.
WATCH_RE = re.compile(
    CMD_POS
    + r"gh\s+(?:run\s+(?:watch\b|view\b[^|;&\n]*--watch\b)"
      r"|pr\s+checks\b[^|;&\n]*--watch\b)"
)
# Shell detach detection must bind to the thing being watched. A random later
# background command must not launder a foreground watch, and the second '&' in
# '&&' is never a detach marker.
WATCH_DETACHED_RE = re.compile(
    WATCH_RE.pattern + r"[^;\n]*?(?<!&)&(?!&)\s*(?:;|\n|$)"
)
LOOP_DETACHED_RE = re.compile(r"\bdone\s*(?<!&)&(?!&)\s*(?:;|\n|$)", re.I)
COMMAND_DETACHED_RE = re.compile(r"(?<!&)&(?!&)\s*$")

#: Shape 6. `gh run cancel <id>` plus both REST spellings the fleet has actually
#: used — the force-cancel receipt from 2026-08-12 is the second form.
CANCEL_RE = re.compile(
    CMD_POS + r"gh\s+run\s+cancel\b[^;&|\n]*?(?<![\w-])(?P<id>\d{6,})\b"
)
CANCEL_API_RE = re.compile(r"/actions/runs/(?P<id>\d{6,})/(?:force-)?cancel\b")
INTERVAL_RE = re.compile(r"(?:--interval|(?<!\w)-i)[=\s]+(\d+)")
# any gh subcommand that hits the API (gh auth/help/version are free)
GH_API_RE = re.compile(CMD_POS + r"gh\s+(?:api|run|pr|workflow|search|repo|issue|release)\b")
# CI/release status reads whose repeated sleep/poll form must never occupy the
# principal turn. Keep this narrower than GH_API_RE so a slow loop over some
# unrelated GitHub data is governed only by the shared-quota floor.
CI_READ_RE = re.compile(
    CMD_POS
    + r"gh\s+(?:pr\s+(?:view|checks|status)\b"
      r"|run\s+(?:view|list|watch)\b"
      r"|api\b[^;&|\n]*(?:actions/runs|check-runs))",
    re.I,
)
SLEEP_RE = re.compile(r"\bsleep\s+(\d+)")
# A shell loop BODY, i.e. the span between `do` and `done`. Co-presence of a
# loop keyword and a gh call is NOT enough: the second production false positive
# was `python3 -c "for m in ...: print(...)"` in the same command line as an
# unrelated `gh api rate_limit`. A Python `for` has no `do`/`done`, so requiring
# the real construct — and requiring the gh call to sit INSIDE it — distinguishes
# "polling in a loop" from "a loop and a gh call happen to share a line".
DO_DONE_RE = re.compile(r"(?:^|[;&|\n)])\s*do\b(.*?)\bdone\b", re.S)


def loop_bodies(cmd: str) -> list[str]:
    return [m.group(1) for m in DO_DONE_RE.finditer(cmd)]
PAGINATE_RE = re.compile(CMD_POS + r"gh\s+api\b[^|;&]*--paginate\b[^|;&]*"
                         r"(?:check-runs|/jobs|check_runs)")
# same, other argument order
PAGINATE_RE2 = re.compile(CMD_POS + r"gh\s+api\b[^|;&]*(?:check-runs|/jobs|check_runs)"
                          r"[^|;&]*--paginate\b")
# `gh workflow run <workflow> [--ref <ref>]` — the main-proof dispatch (shape 4).
WORKFLOW_RUN_RE = re.compile(CMD_POS + r"gh\s+workflow\s+run\b(?P<args>[^;&|\n]*)")
REF_RE = re.compile(r"(?:--ref|(?<!\w)-r)[=\s]+(\S+)")
# gh flags that consume the NEXT token, so it is not mistaken for the workflow name.
VALUE_FLAGS = {"--ref", "-r", "--repo", "-R", "--field", "-f", "--raw-field", "-F",
               "--json", "--jq", "-q", "--template", "-t", "--input"}
MAIN_REFS = {"main", "refs/heads/main", "origin/main"}


def dispatch_target(args: str):
    """(workflow basename, ref or None) for a `gh workflow run` argument string."""
    ref_m = REF_RE.search(args)
    ref = ref_m.group(1).strip("\"'") if ref_m else None
    tokens = args.split()
    skip = False
    workflow = None
    for tok in tokens:
        if skip:
            skip = False
            continue
        if tok.startswith("-"):
            if "=" not in tok and tok in VALUE_FLAGS:
                skip = True
            continue
        workflow = os.path.basename(tok.strip("\"'"))
        break
    return workflow, ref


def warn(msg: str):
    """Loud, but never a deny. Stdout is the harness's decision channel — an ALLOW
    must print nothing there — so the fail-open notice goes to stderr."""
    print(f"GH QUOTA GUARD (fail-open): {msg}", file=sys.stderr, flush=True)


def run_workflow_path(run_id: str):
    """The workflow file a run belongs to, or None when the probe cannot answer.

    ONE REST call, spent only after the command has already matched a cancel of a
    specific run id. None means "unknown" -> allow, never deny.
    """
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
             "--jq", ".path"],
            capture_output=True, timeout=PROBE_TIMEOUT_S,
        )
    except Exception as exc:
        warn(f"could not resolve run {run_id} ({exc.__class__.__name__})")
        return None
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()[:200]
        warn(f"`gh api` failed for run {run_id} (exit {proc.returncode}): {detail}")
        return None
    path = proc.stdout.decode("utf-8", errors="replace").strip()
    return path.rsplit("/", 1)[-1] if path else None


def protected_cancel_reason(run_id: str):
    """Deny a cancel aimed at a production lane. See shape 6 in the docstring."""
    workflow = run_workflow_path(run_id)
    if workflow is None or workflow not in PROTECTED_LANES:
        return None
    return (
        f"PRODUCTION LANE: run {run_id} belongs to `{workflow}`, which this session "
        "may not cancel.\n\n"
        "On 2026-08-12 a live fleet session force-cancelled the US nightly's recovery "
        "dispatches SIX times (receipt: POST /actions/runs/31583415065/force-cancel). "
        "Combined with the #5362 workflow-size strand the night before, Prophet US "
        "shipped Aug-10 picks for two full sessions and the operator found it by "
        "looking at the site. A cancel is invisible to every data-staleness "
        "instrument we own — it just looks like the bake never happened.\n\n"
        "CLAUDE.md already says it: never cancel or re-run an in-progress `render`, "
        "`engine-render` or `daily` merely to unblock this session; a long job inside "
        "its timeout is not evidence that it is wedged. That note did not bind, so "
        "this hook does.\n\n"
        "If the run is genuinely wedged (past its timeout-minutes, or provably "
        "orphaned), that is an OPERATOR call — say so and hand it over. Cancelling a "
        "healthy bake costs a whole session of data that only the next night, or a "
        "force-majeure backfill, can recover."
    )


def main_runs(workflow: str):
    """Newest runs of `workflow` on main, or None when the probe cannot answer.

    ONE REST call. None means "unknown", which the caller turns into an allow —
    never into a deny (see the fail-open note in the module docstring).
    """
    try:
        proc = subprocess.run(
            ["gh", "run", "list", "--workflow", workflow, "--branch", "main",
             "--limit", "20", "--json", "status,createdAt,databaseId,url"],
            capture_output=True, timeout=PROBE_TIMEOUT_S,
        )
    except Exception as exc:                      # gh missing, timeout, anything
        warn(f"could not probe {workflow} runs on main ({exc.__class__.__name__})")
        return None
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()[:200]
        warn(f"`gh run list` failed for {workflow} (exit {proc.returncode}): {detail}")
        return None
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace") or "[]")
    except Exception:
        warn(f"unparseable `gh run list` output for {workflow}")
        return None
    return data if isinstance(data, list) else None


def age_minutes(stamp):
    try:
        when = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except Exception:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - when).total_seconds() / 60.0


def live_proof_reason(workflow: str):
    """Deny reason when a proof run of `workflow` is already live on main."""
    runs = main_runs(workflow)
    if runs is None:
        return None                               # unknown -> allow
    in_flight = [r for r in runs
                 if isinstance(r, dict) and (r.get("status") or "") != "completed"]
    if not in_flight:
        return None
    newest = max(in_flight, key=lambda r: str(r.get("createdAt") or ""))
    status = newest.get("status") or "?"
    age = age_minutes(newest.get("createdAt"))
    if status == "queued" and age is not None and age > ORPHANED_QUEUE_MINUTES:
        return None                               # orphaned-queue mercy kill
    run_id = newest.get("databaseId") or "<id>"
    url = newest.get("url") or ""
    aged = f"{age:.0f} min" if age is not None else "unknown age"
    return (
        f"MAIN PROOF ALREADY IN FLIGHT: {workflow} run {run_id} is {status} on main "
        f"({aged}). {url}\n\n"
        "Do not re-dispatch it. This is the 2026-08-09 livelock: main-ref dispatches "
        "share one concurrency group, and a re-dispatch USED TO CANCEL the in-flight "
        "proof — run 31309720615 died at 44 minutes to dispatch 31311537537, which "
        "died 4 minutes later to 31311693575, so no proof ever concluded and 12 "
        "merge-blocked + 56 cap-deferred pull requests could not drain. The workflows "
        "now fence dispatches out of the cancel path, so a second dispatch no longer "
        "kills the first — it is simply waste, and the run already holding a runner is "
        "the fastest proof you can get.\n\n"
        f"Bind one asynchronous watcher to the run already executing:\n"
        f"  gh run watch {run_id} --interval 150   # launch with run_in_background=true\n"
        f"Then continue another independent project lane; do not foreground-wait. "
        f"A ci.yml run here takes 30-34 minutes. Re-dispatch only after it CONCLUDES, "
        f"or if it has sat `queued` more than {ORPHANED_QUEUE_MINUTES} minutes (an "
        "orphaned queue slot, which this guard already lets through)."
    )


def allow(context: str | None = None):
    """Exit ALLOW. With `context`, attach it so the session actually reads it.

    stdout is the harness's decision channel, so a bare allow must print nothing
    there. `additionalContext` is the one field that reaches the model in-band on
    an allow; `warn()` only reaches stderr, which is where the first version of
    shape 7 would have died unread.
    """
    if context:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": context,
            }
        }))
    sys.exit(0)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def check(raw: str, cwd=None):
    """Return a deny reason, or None to allow.

    `cwd` is the invoking checkout as the harness reports it. No rule here reads
    it today — every shape is decided from the command string plus, for shape 4,
    one bounded `gh run list` probe — but the parameter is part of the hook's
    call signature and is kept so a future checkout-scoped rule needs no change
    at the `main()` seam.
    """
    cmd = strip_heredocs(raw)

    # 1. gh run watch at a hot interval
    m = WATCH_RE.search(cmd)
    if m:
        tail = cmd[m.start():]
        iv = INTERVAL_RE.search(tail)
        secs = int(iv.group(1)) if iv else 3      # gh's documented default
        if secs < MIN_WATCH_INTERVAL:
            return (
                f"SHARED GITHUB QUOTA: `gh run watch` polls every {secs}s "
                f"(gh's default is 3s), fetching the run AND its jobs each time. "
                f"REST's 5,000/hr is ONE bucket for every session, the babysitter, "
                f"and ship_loop_guard.py (which fails closed when rate-limited). "
                f"Three 10-minute windows of this emptied it on 2026-07-26.\n\n"
                f"Use --interval {MIN_WATCH_INTERVAL} or higher, or better:\n\n{REMEDY}"
            )

    # 2. gh inside a tight poll loop — the gh call must be INSIDE the loop body,
    # not merely somewhere in the same command line.
    polling = [b for b in loop_bodies(cmd) if GH_API_RE.search(b)]
    if polling:
        body = "\n".join(polling)
        sleeps = [int(s) for s in SLEEP_RE.findall(body)]
        if sleeps and min(sleeps) < MIN_SLEEP:
            return (
                f"SHARED GITHUB QUOTA: gh poll loop sleeping {min(sleeps)}s "
                f"(floor is {MIN_SLEEP}s). REST's 5,000/hr is shared across every "
                f"session and the hooks; two watchers on one endpoint at 45s went "
                f"4,488 -> 0 in under an hour, 403ing everyone.\n\n{REMEDY}"
            )
        if not sleeps:
            return (
                "SHARED GITHUB QUOTA: gh call in a loop with no sleep — that is an "
                f"unthrottled hammer on a pool shared with every other session.\n\n{REMEDY}"
            )

    # 3. --paginate over check-runs/jobs
    if PAGINATE_RE.search(cmd) or PAGINATE_RE2.search(cmd):
        return (
            "SHARED GITHUB QUOTA: `--paginate` over check-runs/jobs. This repo runs "
            "~130 checks per PR, so each poll spends several requests where one page "
            "already answers 'is it still running'. Drop --paginate, or ask the run "
            "endpoint for a single status.\n\n" + REMEDY
        )

    # 4. dispatching a main proof workflow over one that is already in flight.
    # Probed LAST and only on an exact match, so the one REST call this guard
    # spends is never spent on an unrelated command line.
    for m in WORKFLOW_RUN_RE.finditer(cmd):
        workflow, ref = dispatch_target(m.group("args"))
        if workflow not in PROOF_WORKFLOWS:
            continue
        # No --ref means gh targets the default branch, which is main here.
        if ref is not None and ref not in MAIN_REFS:
            continue
        reason = live_proof_reason(workflow)
        if reason:
            return reason

    # 6. cancelling a production lane. Probed LAST and only on an exact run-id
    # match, so the one REST call is never spent on an unrelated command line.
    seen: set[str] = set()
    for m in list(CANCEL_RE.finditer(cmd)) + list(CANCEL_API_RE.finditer(cmd)):
        run_id = m.group("id")
        if run_id in seen:
            continue
        seen.add(run_id)
        reason = protected_cancel_reason(run_id)
        if reason:
            return reason

    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        allow()
    if (payload.get("tool_name") or "") != "Bash":
        allow()
    ti = payload.get("tool_input") or {}
    if not isinstance(ti, dict):
        allow()
    cmd = str(ti.get("command") or "")
    clean_cmd = strip_heredocs(cmd)

    # Shape 7 is about unchanged external state, not an arbitrary timer. A material
    # self-mutation makes the previous observation stale and re-opens one bounded read.
    clear_poll_cooldown_for_mutation(clean_cmd)
    if "gh " not in clean_cmd:
        allow()

    # Native blocking watches and hand-written CI sleep/poll loops are the same
    # orchestration failure: they occupy the principal Bash turn for an external
    # 30-45 minute wait. The principal must launch exactly one async observer and
    # continue another lane. Tool-level background mode is preferred; a real single
    # shell '&' detach is also nonblocking (but '&&' is not).
    background = ti.get("run_in_background") is True
    # Codex unified Bash does not expose Claude's run_in_background field. Long
    # shell calls are handed back as native background-terminal/session handles while
    # the model can continue; Codex PreToolUse carries a turn_id and no Claude
    # transcript_path. Treat ONLY a native watch as async on that surface. Hand-written
    # sleep/poll loops remain denied because they waste quota even if the terminal
    # itself backgrounds.
    codex_native = bool(payload.get("turn_id")) and payload.get("transcript_path") is None
    watch_match = WATCH_RE.search(clean_cmd)
    watch_detached = bool(WATCH_DETACHED_RE.search(clean_cmd))
    if watch_match and not background and not watch_detached and not codex_native:
        deny(
            "CI WATCH MUST BE ASYNC: a foreground `gh run watch` / `--watch` "
            "would pin this orchestrator until CI concludes and burn the GitHub "
            "quota shared with every session. Re-run it with the "
            "Bash tool's run_in_background=true (or an explicitly detached shell "
            "watcher), bind it to this PR/run, then immediately continue the next "
            "independent authorized project lane. The watcher notification is the "
            "next CI event; do not foreground-wait for it."
        )

    ci_sleep_poll = CI_READ_RE.search(clean_cmd) and SLEEP_RE.search(clean_cmd)
    loop_ci_poll = any(
        CI_READ_RE.search(body) and SLEEP_RE.search(body)
        for body in loop_bodies(clean_cmd)
    )
    poll_detached = bool(
        (loop_ci_poll and LOOP_DETACHED_RE.search(clean_cmd))
        or (
            ci_sleep_poll
            and not loop_ci_poll
            and COMMAND_DETACHED_RE.search(clean_cmd)
        )
    )
    if (ci_sleep_poll or loop_ci_poll) and not background and not poll_detached:
        deny(
            "CI WAIT LOOP MUST BE ASYNC: a foreground CI status + sleep/poll command "
            "would occupy this orchestrator for external wait time even at a safe "
            "GitHub cadence. Perform one bounded state read, then bind exactly one "
            "background/native watcher (or use the existing merge sweeper) and "
            "immediately continue another independent authorized project lane."
        )
    # The harness names the invoking checkout. `check` does not consult it today,
    # but passing it through keeps this seam stable for a checkout-scoped rule.
    cwd = payload.get("cwd")
    try:
        reason = check(cmd, str(cwd) if cwd else None)
    except Exception:
        allow()          # fail open
    if reason:
        deny(reason)
    # Shape 7 is resolved AFTER every other deny shape, so a command that never
    # reached GitHub is not recorded as a poll. The Chairman's 2026-10-03 ruling
    # makes the cooldown binding: a repeat read inside the 5-minute window is
    # principal-capacity waste, especially once a watcher is armed.
    repeat_reason = None
    try:
        # strip_heredocs FIRST: a heredoc body is DATA, not a command.
        key = poll_shape(clean_cmd)
        if key:
            repeat_reason = poll_cooldown_nudge(key)
    except Exception:
        repeat_reason = None     # state failure is not proof of a recent poll
    if repeat_reason:
        deny(repeat_reason)

    async_wait = (
        background
        or watch_detached
        or poll_detached
        or (codex_native and bool(watch_match))
    )
    if async_wait and (watch_match or ci_sleep_poll or loop_ci_poll):
        # Arming an asynchronous native/detached watcher is itself the observation
        # transfer. Fence an immediate direct run-view even when no diagnostic read
        # preceded the watcher, and tell the principal to spend the freed turn on work.
        run_watch = RUN_WATCH_ID_RE.search(clean_cmd)
        if run_watch:
            record_poll_observation(f"run-view:{run_watch.group('id')}")
        pr_watch = PR_WATCH_ID_RE.search(clean_cmd)
        if pr_watch:
            record_poll_observation(f"pr-checks:{pr_watch.group('id')}")
        surface = (
            "Codex native background-terminal handoff"
            if codex_native and not background and not watch_detached
            else "background/detached task"
        )
        allow(
            f"CI WATCHER ARMED ASYNC via {surface}: this task is now the CI observation "
            "owner. Do not tail its process/session handle, poll GitHub, or spend a "
            "reasoning cycle waiting for it. Immediately start the next highest-value "
            "independent authorized project lane. Return to this PR only on watcher "
            "completion/event, genuine red, merge/conflict transition, or watcher "
            "failure/staleness."
        )
    allow()


if __name__ == "__main__":
    main()
