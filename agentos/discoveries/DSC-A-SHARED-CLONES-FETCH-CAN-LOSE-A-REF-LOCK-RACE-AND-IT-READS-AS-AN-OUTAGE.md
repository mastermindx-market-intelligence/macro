---
key: A-SHARED-CLONES-FETCH-CAN-LOSE-A-REF-LOCK-RACE-AND-IT-READS-AS-AN-OUTAGE
claim: >
  The fleet worktree GC's `git fetch --prune` failed on 2026-09-28 with `error: cannot lock
  ref 'refs/remotes/origin/main': is at fd072295de2e9be1fcd8ed81284676187054e4a7 but expected
  dd8aa9f28bcc8cc9074b3df9a01e0ece09484e0b`. That is a **compare-and-swap loss, not an
  outage**: the sweeper fetches into the shared primary clone
  (`/Users/chriswong/Documents/Cluade/Macro Dashboard`), which is the registry owner the whole
  fleet also fetches, and another process advanced `refs/remotes/origin/main` between this
  fetch's read and its write. It is the FIRST failure of this class recorded for the job — the
  only other fetch failure in the log is one `TimeoutExpired` at the 600 s git cap. Two
  consequences that are easy to get backwards. (1) **git updates refs individually**, so a
  single ref losing its lock leaves every other ref updated; the run was behind on
  `origin/main` alone, while `fetch_origin` at `scripts/worktree_gc.py:473-479` logs the
  whole-world phrase "continuing with stale refs" and returns False on any nonzero rc, with no
  retry. (2) The effect on that run was **conservative, not dangerous**: staler refs mean
  fewer `SAFE_REMOTE` and fewer ancestry proofs, so the sweep deletes less. Expect recurrence
  — a clone fetched by ~50 concurrent sessions is where CAS races live.
falsifier: >
  `grep -c "cannot lock ref" ~/Library/Logs/macro_worktree_gc/launchd.err.log` = 1, and
  `grep "git fetch --prune failed" …` returns exactly two lines whose reasons are this ref-lock
  error and one `TimeoutExpired`. `scripts/worktree_gc.py:473-479` is `fetch_origin`, which has
  no retry and one warning string. If a future occurrence shows refs OTHER than the contended
  one also un-updated, the "one ref only" half is false and the message is right. If the
  contended sha pair ever fails to correspond to two real `origin/main` commits minutes apart,
  the concurrency reading is wrong and some other writer is at fault.
so_what: >
  Do not triage this line as a network outage, a TCC refusal, or a broken remote — all three
  were the recorded fetch-failure classes before it, and none of them applies. The repair
  direction is a single retry in `fetch_origin` plus a message naming the ONE contended ref
  instead of "stale refs", but that is a code change to an armed deleter's fetch path and it
  is NOT taken here: it needs its own ratification. Until then, read this warning as "this run
  was one commit behind on main and therefore slightly more conservative", which is the safe
  direction. The general form worth carrying: **a lock contention loss and an unavailable
  remote produce the same log line at the call site, and only the error TEXT distinguishes
  them** — so a fetch wrapper that flattens git's per-ref outcome into one boolean throws away
  the only evidence that says which failure you are looking at.
kind: runtime
verified_at: 2026-09-29
verified_by: >
  `~/Library/Logs/macro_worktree_gc/launchd.err.log` — the warning line quoted above, immediately
  preceding the 09-28 run's `subprocess.TimeoutExpired` traceback; `grep -c "cannot lock ref"` = 1
  over that file; the two `git fetch --prune failed` reasons enumerated with
  `grep -oE … | sort | uniq -c`; `sed -n '462,485p' scripts/worktree_gc.py` for `fetch_origin`'s
  no-retry single-warning shape.
scope:
  - macro
  - scripts/worktree_gc.py
  - research/WORKTREE_GC_POLICY.md
confidence: verified
---

## Why the message is the misleading part

`fetch_origin` collapses every failure into one sentence:

```
log.warning("git fetch --prune failed (continuing with stale refs): %s", err.strip()[:200])
```

"stale refs", plural and unqualified, describes a fetch that accomplished nothing. What actually
happened is that one ref out of several hundred lost a compare-and-swap and every other ref
updated normally. A reader triaging the line looks for a network fault, a TCC refusal, or a dead
remote — the three classes this job had previously produced — finds all three healthy, and has no
reason to suspect the real cause, which is the fleet's own concurrency on the clone the sweeper
was told to use as its vantage point.

The 200-character truncation is what saves it: the git error text survives, and the text is the
only thing that distinguishes contention from unavailability.

## Why it was harmless this time, and why that is not luck

Staler refs make every landedness proof harder to satisfy, never easier:
`SAFE_REMOTE` needs `HEAD` contained in `origin/<branch>`, and the ancestry proof needs
`origin/main` to have advanced. A sweeper one commit behind therefore verdicts FEWER trees safe.
The failure direction is the same fail-closed direction every other gate in `worktree_gc.py`
takes, which is why a race on the deleter's own fetch is a robustness and observability problem
rather than a safety one.

Related: `DSC:THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH` (the other class
of thing this job's own instruments cannot report about themselves).
