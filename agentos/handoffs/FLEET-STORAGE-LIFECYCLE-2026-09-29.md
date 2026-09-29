---
workstream: WS:FLEET-STORAGE-LIFECYCLE
session: claude/fleet-storage-records-wave14-20260929 (W15, which amends this file in place; the day's earlier waves shipped on claude/human-driven-roots-denylist-20260929 (W11), claude/gc-wrapper-timeouts-fail-silently-20260929 (W12) and claude/gc-protective-key-defaults-unprotected-20260929 (W14))
model: opus
ended_because: blocked
mission: >
  Autonomous cleaning and triage of fleet storage: classify every disk pool, the worktree fleet and
  the PR queue, actually reclaim what can be reclaimed, and put what only the operator may decide in
  front of the operator. No device may run out of space.
state_before: >
  `research/WORKTREE_GC_POLICY.md` §9 attributed the armed sweeper's low yield entirely to SCOPE —
  72% of trees outside `roots`, and a wider `roots` measured inert because the host-checkout belt
  refuses absolutely-named paths. The 527 human-driven SSD checkouts were protected by a path-naming
  heuristic nobody had chosen. Nothing anywhere recorded whether the launchd job that runs the
  sweeper was completing its runs; `launchctl list` showed last exit status 1 and
  `~/Library/Logs/macro_worktree_gc/last_run.json` described a successful sweep from 09-27.
changed:
  - path: config/worktree_gc.json
    what: >
      Gained `human_driven_roots` — a purely protective deny-list honoured ahead of every verdict.
      It can delete nothing. Shipped FIRST on purpose (#8175), because it is live on merge and the
      act that makes a wider `roots` work is the same one that would silently delete those trees.
  - path: scripts/worktree_gc.py
    what: >
      Threads the deny-list into the deletion belt, not merely into the report. The accompanying
      test asserts the THREADING (a denied root reaches the belt and is refused there), because a
      test that only proves the key is read would pass on a config the deleter ignores.
  - path: scripts/worktree_gc_launchd.py
    what: >
      4,583 → ~10,000 chars. `_git` never raises: a timeout comes back as `rc=124` so the callers'
      pre-existing error paths run. The sweep's own timeout is caught and returns a distinct `3`, so
      a cap cannot be mistaken for a refusal. Every exit path — both refusals, the sweep timeout,
      and a successful run — writes `last_attempt.json` with stage/status/elapsed and the caps it
      was judged against, wrapped so a diagnostics failure can never gate a deleter. The class
      docstring's claim that all drift in the extracted pair is conservative was corrected: a
      PROTECTIVE key inverts it, because older policy then means less protection.
  - path: tests/test_worktree_gc_launchd.py
    what: >
      New suite, 16 cases through one seam (`subprocess.run` plus the receipt path). Mutation-tested
      twice: 10/10 on the first pass, 2/2 on the correction, including the mutant that reverts the
      one-line fix, one that makes a timeout return `1` so it cannot be told from a refusal, one that
      reports a non-zero tool exit as `completed`, one that turns the receipt into a gate, one that
      narrows the fetch fallback to `rc == 124` (making this wave's own original overstatement true),
      and one that makes the TCC hint unconditional.
  - path: .github/ci/legacy-jobs.yml
    what: >
      The new suite wired into `self-mod-fence` in BOTH places it has to be: a `paths:` entry
      (inference cannot reach it — the test reads the wrapper's source as well as importing it) and
      the job's run line. A declared-but-never-executed suite is the other `contract-delta` finding
      class.
  - path: research/WORKTREE_GC_POLICY.md
    what: >
      §10 caveat 2's CONSEQUENCE retracted in place with the superseded sentence quoted, and new §11
      added: the measured run history, the three defects, the two counting traps, and the boundary
      the fix does not reach. 99,045 → ~110,000 bytes.
  - path: agentos/discoveries/DSC-A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-DEAD-CODE.md
    what: >
      New record (kind landmine). Its claim was narrowed before landing: the handlers are unreachable
      for the TIMEOUT cause only, which is more deceptive than dead code because the branch still
      fires for the rare causes and therefore still reviews as working.
  - path: agentos/discoveries/DSC-TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE.md
    what: New record from the deny-list wave (#8175) — cited by the timeout record as the same shape seen from the other side.
verified:
  - claim: "The launchd job crashed on 13 of 45 recorded runs (29%), every crash an uncaught subprocess.TimeoutExpired."
    command: "scratchpad/dead_days.py over ~/Library/Logs/macro_worktree_gc/launchd.{out,err}.log — pairs each `== worktree-gc <ts> ==` header with the `done rc=` line that follows it, then counts tracebacks by their terminal `^subprocess.TimeoutExpired: Command` lines"
    result: >
      45 runs, 30 completions, 15 with no completion line — of which 13 crashed (9 at
      RUN_TIMEOUT_S=3000, 4 at GIT_TIMEOUT_S=120) and 2 refused cleanly. One exception class across
      all 13.
  - claim: "Two of the 15 non-completions were the fail-closed refusal path WORKING, not crashes."
    command: "the same script's per-run stdout tail, cross-read against `git show origin/main:scripts/worktree_gc_launchd.py` lines 61-69"
    result: >
      09-07 and 09-16 printed `cannot read the primary checkout ('fatal: Unable to read current
      working directory: Interrupted system call ...')` and the refusal does `return 1` without
      printing a completion line. EINTR, not TCC — and the wrapper's TCC hint correctly stayed
      silent, which is a positive control on that branch sitting in the log.
  - claim: "The fetch fallback is reachable for an ordinary non-zero exit and absent only for a timeout."
    command: "the same per-run stdout tail for 2026-09-28, plus tests/test_worktree_gc_launchd.py::test_an_ordinary_nonzero_fetch_exit_still_reaches_the_fallback"
    result: >
      The 09-28 run printed `(fetch failed — proceeding on last-known origin/main)` and then died at
      the sweep cap. This RETRACTS this wave's own first claim that the handlers were dead code;
      13 of the 15 non-completions took the path with no handler, 2 took a path whose handler ran.
  - claim: "The job never started at all on four days, and the host was up on every one of them."
    command: "grep -ho '^== worktree-gc 20[0-9T:+-]*' launchd.out.log | histogram by day; last reboot; find ~/.claude/projects -name '*.jsonl' -newermt/-not-newermt per day"
    result: >
      No header for 09-18, 09-19, 09-20, 09-21. No reboot since 2026-08-29. Transcript writes on
      those four days: 158 / 320 / 1183 / 274. SUPERSEDED within the same day, quoted so the
      earlier reading is traceable: "Cause NOT established." W15 established it — the LaunchAgent
      was not loaded; see the `runs = 7` claim below.
  - claim: "No catch-up-after-wake run has ever been observed on this host, so sleep is not a supported explanation — and that mechanism is untested here."
    command: "the same header histogram, checked against the plist's StartCalendarInterval (05:17 local = 12:17 UTC)"
    result: >
      43 of 45 runs fired within 10 s of 12:17:00 UTC; the only two off-schedule ones are the
      install-day kickstarts of 2026-08-13.
  - claim: "The unified log carries NO signal about this label and its silence must not be cited."
    command: "/usr/bin/log show --start '<day> 05:16:00' --end '<day> 05:20:00' | grep -ci worktree-gc, for 09-17 through 09-23"
    result: >
      Zero rows on every day tested, INCLUDING 09-17, 09-22 and 09-23 — days the job demonstrably
      ran. The positive control turned a finding into a non-finding.
  - claim: "The installed wrapper was byte-identical to origin/main's copy before this wave."
    command: "shasum -a 256 on ~/Library/Application Support/macro-worktree-gc/worktree_gc_launchd.py and on `git show origin/main:scripts/worktree_gc_launchd.py`"
    result: "Both 6c7cb824ef45e33eed6619a6b8ecc2b8abb13174068376644d02d32e4eb04872, 4611 bytes. It stops being identical the moment this wave lands."
  - claim: "The new suite is not vacuous and the wrapper survives mutation testing unchanged."
    command: "scratchpad/mutate_reach.py — mutates, runs the named test, restores, re-hashes"
    result: "2/2 mutants caught and wrapper sha256 identical before and after (16748a93…); the first pass caught 10/10 the same way."
  - claim: "The lane is green locally against the job that owns it."
    command: "python3 -m pytest <the self-mod-fence run line verbatim> -q; python3 scripts/agentos.py validate; python3 scripts/check_contract_delta.py --base 43f81e98d0ea"
    result: "526 passed / 1 skipped; 0 errors, 121 warnings; 0 introduced, 0 inherited."
  - claim: "The four-day non-start window is 2026-09-18 -> 09-21 and its cause is an UNLOADED LaunchAgent — the one question this handoff's first draft left open."
    command: "launchctl print gui/$(id -u)/com.macro.worktree-gc | grep runs, against the per-day histogram of `^== worktree-gc 20` headers in launchd.out.log; plus `last reboot` and stat on ~/Library/LaunchAgents/com.macro.worktree-gc.plist"
    result: >
      `runs = 7` against exactly 7 logged starts 09-22 -> 09-28, an exact match, while the service
      has 45 starts in its lifetime. launchd resets that counter on re-bootstrap, so the agent was
      re-LOADED on 09-22; the plist's mtime is 2026-08-12, so nothing re-INSTALLED it; `last reboot`
      shows continuous uptime since 2026-08-29 10:58, so it was not a boot-time reload either. This
      is a SECOND availability failure mode and #8176 structurally cannot address it.
  - claim: "#8176's merged claim of 4 GIT_TIMEOUT_S timeouts is correct — re-verified independently, after a substring count said 22."
    command: "grep -c '^subprocess.TimeoutExpired:' ~/Library/Logs/macro_worktree_gc/launchd.err.log, then split by the seconds value named on each terminal line"
    result: >
      13 exception lines = 9 at RUN_TIMEOUT_S + 4 at GIT_TIMEOUT_S. The 22 came from a substring
      `grep -o` counting the same message repeated inside traceback BODIES — occurrences, not
      events. No correction to the merged record was needed, and one was nearly filed.
  - claim: "141 GiB of the runner workspaces is pack data, 130 GiB of it in two of the four clones, and nothing in this repository ever consolidates it."
    command: "du -sh + find -name '*.pack' + stat over the four actions-runner*/_work/macro/macro/.git/objects/pack dirs; grep -c 'auto = 0' on each .git/config; grep -rln 'repack|gc --prune|gc.auto' .github/workflows/ scripts/"
    result: >
      runner-1 36,271 packs / 5.3 GiB (all .promisor), runner-2 35 / 72 GiB, runner-3 139 / 58 GiB,
      runner-4 47 / 5.7 GiB. All four carry `gc.auto = 0`; no workflow and no script performs git
      maintenance (the only matches are 7 occurrences of the word "repackaged" in unrelated engine
      scripts). The workspace figure carried since W4 — 177.26 GiB, 87% `.git` — is superseded as
      the basis for the operator ask.
  - claim: "Restoring `filter: blob:none` to the pack checkout would revert a correctness fix, not repair a misconfiguration."
    command: "read .github/workflows/ci.yml lines 4544-4550 and 4905-4929, and earnings-public-wire.yml:47, before publishing the remedy"
    result: >
      ci.yml's own comment block records the filter's removal on 2026-09-23 with three named
      production failures (runs 35876013221, 35885173966, 35886408213) at 65-67 min. The remedy the
      correlation invites was drafted and WITHDRAWN before it reached the operator.
  - claim: "All five PRs of this programme's 09-29 waves are merged and every path they touched is byte-identical in main."
    command: "gh pr view per PR for the squash sha, then `git fetch origin` and a per-path blob comparison of refs/remotes/origin/<branch> against origin/main, then `git merge-base --is-ancestor <squash> origin/main`"
    result: >
      #8174 `d6008b02a8a5`, #8175 `43f81e98d0ea`, #8176 `a0a1c6fdabcf` (5/5 paths), #8177
      `27623a56622a` (3/3), #8178 `8e5529028f89` (3/3). Every squash proven an ancestor of
      origin/main locally, at zero API cost.
  - claim: "Every DSC key this wave cites resolves against main's record store, and the four new records are not duplicates."
    command: "python3 scripts/agentos.py validate; plus a key-by-key grep of agentos/discoveries/ for each cited DSC"
    result: >
      386 records (385 .md + 1 .json data artifact, no malformed record); all cited keys resolve.
      `DSC-A-ONE-MINT-ROOT-IS-SHARED-BY-TWELVE-GIT-STORES` was DROPPED from this wave's shipping
      list — verified already present in origin/main.
unverified:
  - claim: "WHY the job's launchd record was re-created between the 09-21 and 09-22 firings. THAT it
     was re-created is now verified above; the cause of the re-creation is not."
    what_would_verify: >
      `launchctl print gui/501/com.macro.worktree-gc` reads `runs = 7`, which is exactly the firings
      09-22 -> 09-28, and the plist and installed wrapper are both untouched since 2026-08-12 21:41 —
      so no re-install caused it. What that cannot show is WHY the record was re-created. A
      `launchctl` audit trail, or a `log show` predicate that actually matches this label, would
      settle it; neither exists here. Do not fill this gap with a plausible story — an unloaded
      agent and a crashed one leave the same trace, which is the whole reason the external check in
      `next_actions` is owed.
  - claim: "Raising RUN_TIMEOUT_S would let the slow sweeps finish."
    what_would_verify: >
      One instrumented run recording per-tree timings to find what makes a 50-minute sweep 5× slower
      than a 9-minute one. Deliberately not attempted: a bigger cap would hide the cause, and
      `test_raising_a_timeout_is_a_policy_change_that_must_re_justify_itself` now requires whoever
      raises one to edit the paragraph stating that reasoning in the same act.
unresolved:
  - "RESOLVED 2026-09-29 by W15, kept here so the question is not re-opened. The four-day non-start
     window (09-18 -> 09-21) was an UNLOADED LaunchAgent: `runs = 7` matches exactly the 7 starts
     since 09-22, the counter resets on re-bootstrap, the plist was not re-installed, and the host
     never rebooted. `DSC:THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH`. What
     is STILL open is WHY the record was re-created — no launchctl audit trail exists on this host."
  - "Nine superseded `orch(audit)` PRs remain open (#7550, #7551, #7552, #7641, #7653, #7656, #7702, #7718, #7731). #7642 is the only one with real unlanded work. Closing them is an outward act on shared state and has no operator yes."
  - "The three §9 ratification gates below (2), (3) and gate 3 are still unratified. (1) is now DONE."
  - "DONE 2026-09-29 by W15. The `DSC:A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-
     DEAD-CODE` citation was deliberately held out of both this handoff and
     `WS-FLEET-STORAGE-LIFECYCLE` until #8176 had landed the record's FILE, because
     `python3 scripts/agentos.py validate` emits `[dangling-ref] ... references unknown DSC:...`
     as an ERROR — a citation may FOLLOW its file into main but never precede it. This wave's base
     contains #8176, so the citation is now in `discoveries:` below. The RULE is the durable part:
     never cite a record in the commit that mints it unless the file is in the same commit."
  - "CORRECTION to this handoff's own first draft, which said the line above 'corrects CLAUDE.md
     §Agent OS'. It does not, and the superseded sentence was: 'This also corrects CLAUDE.md
     §Agent OS, which says schema is fail-closed; joins fail open: measured 2026-09-29, a dangling
     DSC join is fail-CLOSED and turns the store''s exit code non-zero.' Measured properly, ONE
     rule serves two consumers with opposite dispositions — `compile-context` renders the record
     and prints the dangling citation as a DEGRADED line at exit 0 (fail-OPEN, invariant I4),
     while `validate` marks the identical Problem hard=True and exits non-zero (fail-CLOSED).
     CLAUDE.md is describing the compilation target; what misleads is that it says so inside a
     sentence about `validate`. `DSC:A-DANGLING-CITATION-IS-FAIL-OPEN-TO-THE-COMPILER-AND-FAIL-
     CLOSED-TO-THE-VALIDATOR`. Do NOT edit the repo law on the strength of the first reading."
next_actions:
  - "Put the four `needs_ceo` options to the operator. SUPERSEDED, quoted so the earlier ranking is
     traceable: 'the CI runner git stores (177.26 GiB, 87% `.git`) are the only pool with a real
     lever and the only fully reversible one'. Measured 2026-09-29 across all four clones: 141 GiB
     of PACK data, 130 GiB of it in runner-2 and runner-3, and the act is CONSOLIDATION of
     near-identical whole-tree snapshots — never re-cloning with `filter: blob:none`, which would
     revert `DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`. Drained machine only, and 'drained' means no
     `Runner.Worker` in the process table at the moment of acting: a runner with no pack dated today
     may still be mid-job (measured — runner-2 was executing one)."
  - "Ask for Full Disk Access on the right principal. The grant is for `storage_floor_guard.py`, NOT the worktree GC, and it is worth 1.81 GiB — do not present it as 201."
  - "Decide whether to run `scripts/install_worktree_gc_launchd.sh`. Until it runs, the availability fix is in the repo and not on the host. It changes an armed deleter's behaviour, so it needs an explicit yes."
  - "Build the external, age-based check on `last_attempt.json` that would detect a never-started run. The receipt this wave adds structurally cannot do it."
  - "Ratify (2) widening `roots` by SUBTREE — `…/agent-workspaces/claude` ONLY. `…/agent-workspaces/tmp`
     is dropped from the proposal as of W15: it holds 0 registrations and `scan_orphans` skips any
     root not under a host checkout, so it is inert — no yield and no risk, and a narrower ask is a
     cheaper ratification. Then (3) the lock-stamp fix at `scripts/worktree_gc.py:501`, then gate 3.
     The deny-list now guards gate 3."
do_not_redo:
  - "Do NOT re-measure the launchd run history. 45 runs 2026-08-13 → 09-28: 30 completions, 13 crashes (9 sweep-cap, 4 git-cap), 2 clean refusals, 4 non-start days."
  - "Do NOT count tracebacks by occurrences of the timeout VALUE. `timed out after 120 seconds` also matches the value echoed inside the exception's own command repr, inflating the git class from 4 to 10 — causes (10+9) then exceed the traceback count (13). Count the terminal `^subprocess.TimeoutExpired: Command` lines."
  - "Do NOT classify a run as crashed because it lacks a `done rc=` line. The refusal path returns before printing one, so an absence-shaped predicate over-counts by exactly the number of paths that exit quietly."
  - "Do NOT attribute the operator's `sweeper BLIND: Operation not permitted: '/Users/chriswong/Documents'` notification to the worktree GC. It is `storage_floor_guard.py`. This job reads the primary fine and deleted nine trees cleanly on 09-27."
  - "Do NOT reason about the launchd job as running the repo's script against the primary's config. It runs an installed wrapper that re-extracts BOTH tool and config from `origin/main` every run; the primary is only the git vantage point."
  - "Do NOT cite the unified log about this job. It has zero rows for the label even on days the job ran."
  - "Do NOT re-litigate whether a wider `roots` alone frees space, re-derive the abandonment rate from ancestry, propose retrofit-to-sparse as an ongoing lever, or re-measure the null pools. All settled in the WS record's own `do_not_redo`."
  - "Do NOT re-verify #8176's 4-GIT-timeout claim. It was independently re-verified on 2026-09-29 against the live log and is CORRECT: 13 `^subprocess.TimeoutExpired:` lines = 9 RUN + 4 GIT. A substring `grep -o` says 22 because it counts message OCCURRENCES inside traceback bodies, not events."
  - "Do NOT propose restoring `filter: blob:none` to the pack checkout to shrink the runner stores. Drafted and withdrawn 2026-09-29: it would revert `DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`, which has three named production failures behind it."
  - "Do NOT ask for `…/agent-workspaces/tmp` in the roots widening. 0 registrations and `scan_orphans` skips non-host roots — inert."
  - "Do NOT use `ls <dir>/*.pack | wc -l` on a runner pack directory. 36,271 paths overflow ARG_MAX, the glob fails and it prints 0 — 'none' and 'too many to count' are the same reading. Use `find … | wc -l`."
  - "Do NOT use `pgrep -c -f X 2>/dev/null || echo 0` to ask whether a runner is busy. `-c` is not a count flag on macOS, the `2>/dev/null` swallows the usage error and the fallback literal fabricates a 0 while workers run."
danger_areas:
  - "The fix is NOT live on merge. `scripts/worktree_gc_launchd.py` is the one file not re-read from `origin/main`, because it has to live somewhere stable — so it is the one file that drifts and no merge can reach it. Only `scripts/install_worktree_gc_launchd.sh` reconciles it, and that is a host act outside the ship chain that changes an armed deleter's behaviour. No session may run it without an explicit operator yes."
  - "`last_attempt.json` is written BY the wrapper, so it can only ever describe a run that STARTED. A healthy receipt is not evidence that the schedule is firing. Same structural blind spot as `last_run.json`, one level out."
  - "A PROTECTIVE config key inverts the wrapper's staleness argument: for arming and roots, older policy is narrower is safer, but for a deny-list older policy means LESS protection. Bounded because refs only advance — once one successful fetch has seen an entry, no later staleness drops it — but the protective half must always land in the EARLIER commit."
  - "The deny-list went live ON MERGE, and so would anything dangerous. There is no fast-forward buffer, so commit ORDER on main is the real safeguard for gate 3."
  - "The caps are deliberately unchanged and a test guards the reasoning. Raising one without a measurement would convert a legible timeout back into a silent slow no-op."
prs: [8175, 8176, 8177, 8178]
decisions: [DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM]
discoveries:
  - DSC:TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE
  - DSC:A-DANGLING-CITATION-IS-FAIL-OPEN-TO-THE-COMPILER-AND-FAIL-CLOSED-TO-THE-VALIDATOR
  - DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT
  - DSC:A-RAISED-TIMEOUT-MAKES-THE-DEGRADATION-PATH-WRITTEN-FOR-IT-DEAD-CODE
  - DSC:EDITING-A-PR-BODY-IS-A-CI-TRIGGER-THAT-CAN-CANCEL-ITS-OWN-PROOF
  - DSC:THE-HUMAN-DRIVEN-POPULATION-IS-NOT-ROOT-CONTAINED
  - DSC:GC-DISABLED-RUNNER-STORES-ACCUMULATE-EVERY-TRANSFER-PATHOLOGY-FOREVER
  - DSC:THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH
---

## The one thing a cold stranger must take from this handoff

**The programme's yield is bounded from three independent directions, and until 2026-09-29 only the
first was written down.**

1. **Scope** — 72 % of trees sit outside `roots`, and widening `roots` alone buys +496 trees of
   reporting and **+1** of deletion, because the host-checkout belt refuses anything nameable only
   absolutely. §9, `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`.
2. **Availability** — the job crashed on 13 of 45 runs and never started on 4 further days, so on
   roughly a third of days the *reachable* trees were not swept either. §11.
3. **Permission** — reclaim needs landed **and** nothing attached, and a resumable web
   conversation's attachment is undetectable, so web-session roots are never auto-reclaimed.
   `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`.

An armed deleter that fails a third of the time cannot be judged on its scope. That is why
availability was worth fixing before arming anything further — and it is also why fixing it frees
**zero bytes** on its own and must not be reported as though it did.

## Two corrections this seat made to its own same-day work

Both are recorded where a reader travels: the superseded sentence quoted in place, dated, not
silently replaced.

**§10 caveat 2 drew the wrong consequence.** It said the deny-list is "inert until the PR merges AND
the primary checkout fast-forwards". The launchd job does not run the repo's script against the
primary's config — it runs a wrapper installed outside every checkout that re-extracts both the tool
and the config from `origin/main` every run. The primary is only the git vantage point, the one role
it cannot be stale at, and that wrapper exists precisely to defeat the assumption I made. I named the
wrong principal twice running: first the worktree, then the primary.

**§11's first numbers were inflated, in the direction that flattered the finding.** 15 of 45 became
13 of 45 once the fail-closed refusal path was recognised as exiting without a completion line, and
"dead code" became "unreachable for the timeout cause only" once the 09-28 log was read carefully
enough to notice the fallback printing. A branch seen firing occasionally reviews as working, which
is the harder version of the defect, not the milder one.

## Why the sweep is slow at all, which is the open engineering question

The clone is a `blob:none` promisor, so `git show origin/main:<path>` **fetches over the network**
whenever the blob is cold — and the primary is the one checkout nothing ever warms. The wrapper's
anti-staleness design is therefore what puts a network round trip on a deleter's critical path. That
explains the 120 s git-cap failures; it does not explain a sweep that takes 5× its usual nine
minutes. Whoever raises `RUN_TIMEOUT_S` owes that measurement first.

## W15 amendment — what the same day's later triage changed

Three things in the text above were written before this seat finished measuring, and are corrected
here rather than edited away.

**Bound 2 has TWO modes, not one, and #8176 closes only the first.** The crashes (13 of 45, all
uncaught `subprocess.TimeoutExpired`) are now legible and receipted. The four non-start days are
not, and cannot be: `launchctl`'s `runs = 7` matches exactly the 7 starts logged since 09-22, that
counter resets on re-bootstrap, the plist was never re-installed, and the host never rebooted — so
the agent was simply **not loaded** for 09-18 through 09-21. Every instrument this programme owns
is written BY the wrapper, so nothing it ships can witness its own absence, and the deletion ledger
cannot help either (one row per deleted tree, so a gap cannot separate "did not run" from "ran and
found nothing"). The external, expectation-based check is genuinely owed and does not exist.
`DSC:THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH`.

**The one pool with a real lever was re-measured and the remedy changed.** The runner git stores are
141 GiB of PACK data across four clones, 130 GiB of it in two of them, with `gc.auto = 0` everywhere
and no maintenance lane anywhere. The act is CONSOLIDATION. The act it is NOT is restoring
`filter: blob:none`: that filter was removed deliberately on 2026-09-23 with three named production
failures behind it, and the correlation between "no filter" and "huge" invites exactly the wrong
repair. This seat drafted that repair and withdrew it after reading `ci.yml`'s own comment block.
The general form is worth carrying: **a config difference that correlates perfectly with a cost
difference is not thereby a misconfiguration — the cheap side may be the broken one.**

**Nothing in this wave reclaimed a byte, deliberately.** Every remaining candidate sits behind a
standing operator decline or an unratified gate. That is the correct outcome of a triage whose
subject is an armed deleter, and it is reported as such rather than padded.
