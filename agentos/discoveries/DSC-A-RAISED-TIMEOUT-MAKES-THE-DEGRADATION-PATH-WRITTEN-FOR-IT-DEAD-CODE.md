---
key: A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-DEAD-CODE
claim: >
  A `subprocess.run(..., timeout=T)` that is allowed to raise makes every downstream
  `returncode` check dead code. The degradation the author wrote for exactly that failure —
  "the fetch failed, proceed on the last-known ref", "the policy is unreadable, refuse
  fail-closed" — reviews as present, is reached in tests that never time out, and in production
  is replaced by a traceback. The fix is not in the fallback (which was already correct) but at
  the seam: catch the timeout and return it AS a returncode, which makes every pre-existing error
  path reachable at once without editing any of them. The field tell is a MONOCULTURE in the
  error log — one exception class and no others — because the one class that escapes is the only
  outcome the code never converted into a decision.
falsifier: >
  Run `python3 -m pytest tests/test_worktree_gc_launchd.py -q` (14 passed) with
  `scripts/worktree_gc_launchd.py:94` deleted so `_git` raises again:
  `test_a_git_timeout_returns_124_instead_of_raising` and
  `test_a_fetch_timeout_no_longer_kills_the_run` both fail, the latter by raising
  TimeoutExpired out of `main()` — which is precisely what production did. If a future refactor
  can restore the raising form and the suite stays green, this claim has rotted. The claim is
  also refuted for any caller that genuinely has no error path to reach: the value here comes
  from the fallbacks ALREADY existing, not from catching for its own sake.
so_what: >
  Measured on the armed fleet worktree sweeper's launchd job (`~/Library/Logs/macro_worktree_gc/`,
  45 runs, 2026-08-13 → 09-28): 15 runs (33 %) died mid-run, all 13 tracebacks were
  `TimeoutExpired` (9 at the sweep cap, 4 at the git cap), and on every one of those days a
  ratified deleter removed nothing while `launchctl list` showed a bare `1` and `last_run.json`
  still described the last SUCCESSFUL sweep from days earlier. The storage programme had been
  attributing the sweeper's low yield entirely to SCOPE (72 % of trees outside `roots`,
  WS:FLEET-STORAGE-LIFECYCLE) — a second, independent bound was AVAILABILITY, and it was
  invisible because the same log records both success and failure. Before blaming a scheduled
  tool's judgement, check whether it finished: count its completion lines, not its runs.
kind: landmine
verified_at: 2026-09-29
verified_by: "python3 -m pytest tests/test_worktree_gc_launchd.py -q — 14 passed; seams at scripts/worktree_gc_launchd.py:94 and scripts/worktree_gc_launchd.py:177"
scope: [macro]
confidence: verified
---

## How it was found

By reading a plist, not by suspecting a bug. Checking which principal actually runs the sweeper —
after a same-day correction had already named the wrong one twice — showed `launchctl list`
reporting `com.macro.worktree-gc` with last exit status **1**. The natural reading was the macOS TCC
wall, since the operator had recently seen a `sweeper BLIND: Operation not permitted:
'/Users/chriswong/Documents'` notification and the repo does live under `~/Documents`. That reading
was wrong: the notification belongs to `storage_floor_guard.py`, a different instrument, and this
job reads the primary fine — it had deleted nine trees cleanly the previous day.

The log said what the exit code could not. 15 of 45 runs had no completion line, and the error log
contained exactly one exception class across all 13 tracebacks. A single class is a strong signal on
its own: a tool failing for varied reasons produces varied errors, while a tool failing for one
structural reason produces one. Here that class was the only failure the code never turned into a
returncode — so it was also the only failure whose handler could not run.

## Why the fallbacks existed and still never ran

The wrapper is careful code. It re-extracts policy from `origin/main` every run so a stale checkout
cannot silently narrow an armed deleter; it refuses outright when it cannot read that policy
("blind means stop"); it tolerates a failed fetch by proceeding on the last-known ref. All three
behaviours are written as `returncode` checks. All three were unreachable through the timeout path,
because `_git` raised before any of them was consulted.

This is the same shape as `DSC:TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE`,
seen from the other side. There, two live gates made a dead one invisible. Here, one raised
exception made three live handlers dead. In both cases the code READS as defended and the
defence is not in the path the failure actually takes — and in both cases an outcome-shaped test
cannot tell the difference, because no honest test arranges the timeout that is the only way in.

## What was deliberately not changed

The timeouts themselves. A successful sweep finishes in ~9 minutes and the failing ones exceed 50,
so they are ~5× slower rather than marginally over; raising the cap would let them finish without
explaining them. What was missing was not headroom but a record: every exit path now writes
`last_attempt.json` with stage, status, elapsed and the caps it was judged against, so the next
timeout is diagnosable rather than merely repeated. `research/WORKTREE_GC_POLICY.md` §11 carries
the measurements.

## The part a merge cannot fix

The wrapper lives at `~/Library/Application Support/macro-worktree-gc/` and is installed by
`scripts/install_worktree_gc_launchd.sh`. The config and the tool are re-read from `origin/main`
every run; the wrapper is not, because it is the one file that must sit somewhere stable. So it is
the one file that drifts, and this fix is inert until the installer runs — a host act, outside the
ship chain. The component built to defeat staleness everywhere else is the stalest thing in the
system.
