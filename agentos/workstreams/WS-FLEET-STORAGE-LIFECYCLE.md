---
key: FLEET-STORAGE-LIFECYCLE
title: Fleet storage lifecycle — pool attribution, reclaim gates, and what only the operator may decide
objective: >
  Every storage pool the fleet touches is byte-attributed with its REACH stated, each one's
  reclaimable share is recorded rather than its size alone, and the acts that would actually free
  space are sitting in front of the operator as bounded reversible choices. Done is observable:
  `research/WORKTREE_GC_POLICY.md` §9 names every measured pool with its reclaimable figure, no
  session re-measures a pool already recorded null, and no automated deleter is armed over a
  population protected only by a naming accident.
status: blocked
program: executive-os
repos:
  - macro
owner: claude storage-worktree-lifecycle-law seat
class: research
blast_radius: irreversible
ambiguity: open
p0: null
owns_paths:
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
  - config/worktree_gc.json
  - config/sparse_worktree.json
  - scripts/worktree_gc_launchd.py
  - tests/test_worktree_gc_launchd.py
blocked_by:
  - "DONE 2026-09-29 (#8175, squash `43f81e98d0ea`) — the `human_driven_roots` deny-list, now
     live. Kept in this list rather than deleted so that the gate numbering used by
     `research/WORKTREE_GC_POLICY.md` §9 and by both handoffs still resolves: gate (1) of four is
     closed, the three below are not. It shipped FIRST because it is purely protective and can
     delete nothing, and because the obvious repair that makes a wider `roots` work is the same
     commit that would otherwise silently delete the 527 human-driven SSD checkouts."
  - "OPERATOR RATIFICATION — widening `roots` by SUBTREE (`…/agent-workspaces/claude` and
     `…/agent-workspaces/tmp` only; never `/Volumes/Mastermind/worktrees`, `…/agent-workspaces`
     itself, `…/sol` or `…/review`). Inert without a companion code change: measured over 804
     registrations it moves `in_scope` 225→721 but belt-reachable 225→226."
  - "OPERATOR RATIFICATION — the lock-stamp fix in `scripts/worktree_gc.py:501`, which
     short-circuits on ANY lock so landedness is never computed; 285 of 364 LOCKED trees carry
     only the SSD helper's content-free stamp."
  - "OPERATOR DECISION — the four reclaim/relocation questions in `needs_ceo` below."
decisions:
  - DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM
discoveries:
  - DSC:A-SECOND-EXTERNAL-VOLUME-HOSTS-FLEET-WORKTREES-UNGOVERNED
  - DSC:TRANSFERS-HOLDS-A-195-GIB-OPERATOR-PHOTO-BACKUP-NOT-THE-ONLY-COPY
  - DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-WHILE-ITS-SESSION-IS-LIVE
  - DSC:A-RUNNER-CHECKOUT-IS-87-PERCENT-GIT-STORE-SO-SPARSENESS-CANNOT-REACH-IT
  - DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT
  - DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS
  - DSC:A-GUARDS-CORRECT-TOLERANCE-FOR-AN-ABSENT-SUBJECT-STILL-LIES-IN-ITS-VERDICT
  - DSC:TWO-INDEPENDENT-GATES-MAKE-A-REGRESSION-IN-EITHER-ONE-INVISIBLE
  - DSC:A-DANGLING-CITATION-IS-FAIL-OPEN-TO-THE-COMPILER-AND-FAIL-CLOSED-TO-THE-VALIDATOR
  - DSC:EDITING-A-PR-BODY-IS-A-CI-TRIGGER-THAT-CAN-CANCEL-ITS-OWN-PROOF
  - DSC:THE-HUMAN-DRIVEN-POPULATION-IS-NOT-ROOT-CONTAINED
  - DSC:GC-DISABLED-RUNNER-STORES-ACCUMULATE-EVERY-TRANSFER-PATHOLOGY-FOREVER
  - DSC:THE-SWEEPERS-FOUR-DAY-NON-START-WAS-AN-UNLOADED-AGENT-NOT-A-CRASH
  - DSC:THE-SSD-TMP-POOLS-PROVEN-RECLAIM-IS-UNREACHABLE-BY-THIS-SWEEPER
landmines:
  - "`/Volumes/Worktrees/Documents/Photos Library.photoslibrary` (247 GB, the LIVE library) and
     `/Volumes/Mastermind/transfers/runner-fleet-resilience-worktrees-photoslib-20260924.tar`
     (195.28 GiB, its backup). Neither is on a backup device. The tar's name begins with three
     fleet-infrastructure words, so a sweeper deleting stale transfer artifacts destroys it."
  - "GoLogin / AdsPower / MultiLogin data is never deletable. `.ADSPOWER_GLOBAL` on
     /Volumes/Worktrees measures 0.00 GiB — a marker, not a payload — and the veto stands
     regardless of size."
  - "`Macro Dashboard/.git` owns every worktree's registry; deleting that folder destroys
     `macro-main` and every sibling worktree at once. Workspace rule, not a cleanup target."
  - "Session scratchpad keys are an INVERTED liveness signal — the keyed checkout being gone does
     not mean the session is (81.24 GiB live seat, `DSC:A-SCRATCHPADS-KEYED-CHECKOUT-CAN-BE-GONE-
     WHILE-ITS-SESSION-IS-LIVE`). Scratchpads have no lock, no registry entry and no `git status`
     to refuse on."
  - "A push to a PR already carrying `merge-on-green` can land AFTER the sweeper's merge, and
     rc=0, `state=MERGED`, `mergedAt`, `mergeCommit` and `headRefOid` are all identical to success —
     only the merged commit's FILE LIST differs. This workstream's own record was orphaned that way
     (`DSC:A-PUSH-TO-AN-ARMED-PR-CAN-LAND-AFTER-ITS-MERGE-AND-NOTHING-ERRORS`). Arm last."
  - "Web/ChatGPT session roots are never auto-reclaimed: a resumable browser conversation has no
     process, no shell and no reflog, so its attachment is undetectable."
  - "`scripts/worktree_gc_launchd.py` is the ONE file in this workstream that is not re-read from
     `origin/main` at run time — it has to live somewhere stable — so it is the one file that
     drifts and no merge can reach it. Only `scripts/install_worktree_gc_launchd.sh` reconciles
     the installed copy, and that is a host act outside the ship chain which changes an ARMED
     deleter's behaviour. It has no operator yes and no session may run it without one."
  - "`~/Library/Logs/macro_worktree_gc/last_attempt.json` is written BY the wrapper, so it can
     only ever describe a run that STARTED. A healthy receipt is not evidence that the schedule
     fired — the four-day non-start window (09-18 → 09-21) is invisible to it. Detecting a
     never-started run needs an EXTERNAL age-based check that does not exist yet."
  - "Do NOT 'fix' the runner git stores by restoring `filter: blob:none` to the pack checkout.
     That filter was removed deliberately on 2026-09-23 (`DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`)
     after three production runs died at 65-67 min (35876013221, 35885173966, 35886408213). The
     storage cost is the ACCEPTED PRICE of a correctness fix; the defect is that `gc.auto = 0` plus
     no maintenance lane charges that price on every checkout forever. The lever is CONSOLIDATION.
     General form: a config difference that correlates perfectly with a cost difference is not
     thereby a misconfiguration — here the cheap clones are cheap partly because they have served
     fewer CORRECT checkouts."
  - "A PROTECTIVE config key inverts the wrapper's staleness argument. For `armed` and `roots`,
     older policy is narrower is safer; for `human_driven_roots`, older policy means LESS
     protection. Exposure is bounded because refs only advance, but the protective half of any
     future pair must land in the EARLIER commit."
do_not_redo:
  - "Do NOT re-measure the seven null pools. Attributed and recorded: `/Volumes/Worktrees`
     (93.5% operator data, whole fleet 51.85 GiB / 6.5%, at most ~5.4 GiB agent-reclaimable on
     931 GiB); `transfers` (233.2 GiB, zero reclaimable, 84% is the operator photo tar); the
     non-git bucket (20.19 GiB, no landedness question to ask); `/private/tmp/claude-501`
     (160.43 GiB, 0.02 GiB provably dead, 64.8% live within 2h)."
  - "Do NOT propose retrofit-to-sparse as an ongoing lever. Correctly gated it yields 0.0 GiB
     across the 27 remaining FULL trees; it was a one-time backlog drain."
  - "Do NOT propose sparseness for the runner stores. 87% of a runner checkout is `.git`; the
     sparse omit-set reaches 12% (8.02 of 66.34 GiB)."
  - "Do NOT re-derive the abandonment rate from ancestry. A squash rewrites the commit, so a
     cleanly merged branch's tip is not an ancestor of main; under PR state real abandonment is
     8–14%, not the 79% the ancestry census reported."
  - "Do NOT re-litigate whether a wider `roots` alone frees space. Measured: +496 trees of
     REPORTING, +1 of deletion. The host-checkout belt is the binding constraint."
  - "Do NOT propose `/Volumes/Mastermind/tmp` as a roots widening to capture the 44.19 GiB §9
     proved landed+clean+unattached there. It frees zero bytes for two independent reasons:
     both proven candidates are STANDALONE CLONES (`.git` is a directory, so they are in no
     `git worktree list` and `scan_orphans` skips the root at `worktree_gc.py:682`), and all 17
     registrations under it (~41 GiB) are DETACHED HEAD, which satisfies none of
     `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`'s three proofs. Reclaiming those two clones is a
     DIFFERENT act needing a different tool and its own operator decision."
  - "Do NOT re-ratify gate (1). The `human_driven_roots` deny-list landed in #8175 and is live."
  - "Do NOT re-measure the launchd run history. 45 runs 2026-08-13 → 09-28: 30 completions, 13
     crashes (9 at the 3000 s sweep cap, 4 at the 120 s git cap, one exception class), 2 clean
     fail-closed refusals on EINTR, and 4 days with no run at all. §11."
  - "Do NOT classify a run as crashed because it lacks a `done rc=` line, and do NOT count
     tracebacks by occurrences of the timeout VALUE. The refusal path returns before printing a
     completion line, and `timed out after 120 seconds` also matches the value echoed inside the
     exception's own command repr — the two traps inflated 13 crashes to 15 and the git class
     from 4 to 10. Count terminal `^subprocess.TimeoutExpired: Command` lines."
  - "Do NOT attribute the operator's `sweeper BLIND: Operation not permitted:
     '/Users/chriswong/Documents'` notification to the worktree GC. It belongs to
     `storage_floor_guard.py`. This job reads the primary fine and deleted nine trees cleanly on
     09-27, and the Full Disk Access ask is therefore about the other principal."
  - "Do NOT reason about the launchd job as running the repo's script against the primary
     checkout's config. It runs an installed wrapper that re-extracts BOTH tool and config from
     `origin/main` every run; the primary is only the git vantage point."
  - "Do NOT cite the unified log about this job. `log show` has zero rows for
     `com.macro.worktree-gc` even on days it demonstrably ran, so its silence carries no signal."
needs_ceo:
  question: >
    Four storage acts are fully measured and blocked only on a decision, not on evidence. Which,
    if any, should proceed?
  options: >
    (1) Clear `/Volumes/Mastermind/tmp/pr979-macro-88804-proof` (41.76 GiB) plus
    `prophet-7187-proof-clone-20260920` (2.43 GiB) = 44.19 GiB. Fully proven landed, nothing
    attached; blocked only by the configured-root clause of
    `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM`.
    (2) Clear `/Volumes/Mastermind/worktrees/sol-flow-velocity-recovery-proof-20260920` (7.2 GiB) —
    landedness unprovable, and it sits in the web/Sol mint root, so this is a judgement call, not a
    gate.
    (3) Repack or re-clone the CI runner stores (177.26 GiB, 87% `.git`; runner-2 holds two
    base-size packs, 31.63 + 28.61 GiB). Bounded and fully reversible — a runner store is 100%
    re-fetchable from `origin` — but it must be done on a drained listener, never mid-job, and an
    aggressive repack on a 4-core box contends with the nightly's ~67-minute render budget.
    (4) Relocate the operator photo data. Neither the 247 GB live library nor its 195.28 GiB tar is
    on a backup device, and the live copy shares an 87%-full volume with fleet worktrees.
  recommendation: >
    Option 3 first: it is the only pool in the whole triage with a real lever, it is the largest
    single reclaim available, and it is the only one that is fully reversible. Then option 4, which
    is a data-safety question rather than a space question and is the one with genuine downside if
    deferred. Options 1 and 2 are small and can wait for the `human_driven_roots` deny-list to land
    first.
  by_when: null
waves:
  - id: W1
    title: Pool census, landedness correction, and the roots/belt measurement
    status: done
  - id: W2
    title: The non-git bucket and the transfers pool (195 GiB landmine)
    status: done
    pr: 8158
  - id: W3
    title: /Volumes/Worktrees by bytes — eighth pool, fleet is 6.5%
    status: done
    pr: 8162
  - id: W4
    title: The internal disk — ninth and tenth pools, the only real lever
    status: done
    pr: 8163
    depends_on:
      - W3
  - id: W5
    title: This workstream record and its handoff, replayed after a sweeper race
    status: done
    pr: 8166
    depends_on:
      - W4
  - id: W6
    title: >
      The eleventh pool (TCC-blind sweeper), and the measurement that corrected its own payoff
      claim from 201 GiB to 1.81
    status: done
    pr: 8169
    depends_on:
      - W4
  - id: W7
    title: >
      Arm-LAST fleet law, then the fetch-first fix its own verifier proved it needed
    status: done
    pr: 8170
    depends_on:
      - W5
  - id: W8
    title: >
      The verifier's real failure mechanism — the merge's own success (deleting the head branch)
      is what breaks the check that verifies the merge
    status: done
    pr: 8171
    depends_on:
      - W7
  - id: W9
    title: >
      The sweeper states its REACH and prints its refusals — measured 224 of 789, 28.4%
    status: done
    pr: 8172
    depends_on:
      - W4
  - id: W10
    title: >
      The same reach law in the CI guards — two that printed a PASS having examined zero
      subjects, one of them asserting that an absent file passed 5 invariants
    status: done
    pr: 8174
    depends_on:
      - W9
  - id: W11
    title: >
      Gate (1) ratified and shipped — `human_driven_roots`, the purely protective deny-list that
      makes the 527 human-driven checkouts' protection deliberate instead of a naming accident
    status: done
    pr: 8175
    depends_on:
      - W1
  - id: W12
    title: >
      The second bound on the programme's yield — AVAILABILITY. The armed sweeper's launchd job
      crashed on 13 of 45 runs and never started on 4 further days; the timeouts were uncaught
      and recorded nowhere. DONE 2026-09-29, squash `a0a1c6fdabcf`; its 4-git-timeout claim was
      re-verified independently against the live log on the same day
    status: done
    pr: 8176
    depends_on:
      - W11
  - id: W13
    title: >
      This record and the handoff for W11/W12, deliberately held out of both of their PRs to
      keep them off a shared file. DONE 2026-09-29, squash `27623a56622a`
    status: done
    pr: 8177
    depends_on:
      - W12
  - id: W14
    title: >
      The protective-key default and the policy-source line — a `human_driven_roots` absent from
      an older config must deny, not permit, and the policy file must say where the runtime list
      actually comes from. DONE 2026-09-29, squash `8e5529028f89`
    status: done
    pr: 8178
    depends_on:
      - W13
  - id: W15
    title: >
      This record, the handoff and the §9 refinement for W12-W14, plus the four discovery records
      the triage produced (the PR-body CI trigger, the root-containment correction, the runner
      git stores, and the four-day non-start cause). DONE 2026-09-29, squash `aeb754133a52`
    status: done
    pr: 8179
    depends_on:
      - W14
  - id: W16
    title: >
      The SSD `tmp` pool's reach correction — §9 said the 44.19 GiB proven reclaim "lacks only
      authorization", which named a roots widening as the remedy; measured, that widening frees
      zero bytes because the two candidates are standalone clones the registry cannot see and all
      17 registrations there are detached. Withdraws a ratification ask before it is made
    status: awaiting_ci
    depends_on:
      - W15
next_action: >
  Put the `needs_ceo` options to the operator. SUPERSEDED TEXT, quoted so a reader who remembers it
  can see what replaced it: "the CI runner git stores (177.26 GiB, 87% `.git`) are the largest real
  lever and the only fully reversible one". 177.26 GiB is the WORKSPACE figure and the 87% was
  measured on one checkout; measured 2026-09-29 across all four clones, the pack data is **141
  GiB**, **130 GiB of it in two of the four**, and the remedy is CONSOLIDATION, not re-cloning —
  re-cloning would restore a filter removed deliberately by `DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`
  (`DSC:GC-DISABLED-RUNNER-STORES-ACCUMULATE-EVERY-TRANSFER-PATHOLOGY-FOREVER`). The Full Disk
  Access grant is still worth asking for on the broken safety net rather than on bytes — it frees
  1.81 GiB, and the principal that needs it is `storage_floor_guard.py`, not this sweeper.
  Gate (1) is closed: W11 landed `human_driven_roots`. The next ratification is (2) widening
  `roots` by SUBTREE — `…/agent-workspaces/claude` ONLY; `…/agent-workspaces/tmp` is dropped from
  the proposal because it holds 0 registrations and `scan_orphans` skips any root not under a host
  checkout, so it is inert — then (3) the lock-stamp fix at `scripts/worktree_gc.py:501`, then
  gate 3, which the deny-list now guards. A THIRD widening candidate is withdrawn by W16 rather
  than put to the operator: `/Volumes/Mastermind/tmp` holds the only proven reclaim on the volume
  and a roots entry reaches none of it, because `roots` governs which paths the sweeper may ACT
  on and never which objects it can SEE. Also awaiting an explicit operator yes, and deliberately
  NOT done: running `scripts/install_worktree_gc_launchd.sh`. Until it runs, W12's availability fix
  is in the repo and not on the host, because the wrapper is the one file no merge reaches —
  measured 2026-09-29, the installed copy is 4,611 bytes dated 2026-08-12 against 10,957 on
  `origin/main`. NEWLY OWED and not built: an EXTERNAL check comparing expected daily sweeper
  starts against actual ones, because W14's census found the four-day gap was an UNLOADED AGENT
  and no wrapper-side receipt can witness its own absence. W9 through W15 make the programme's
  bounds legible and free zero bytes; legibility is a precondition for ratifying the acts above,
  never a substitute for it.
artifacts:
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
  - scripts/worktree_gc_launchd.py
  - config/worktree_gc.json
---

## Why this workstream exists at all

Storage lifecycle has been worked repeatedly — the 2026-08-13 ENOSPC incident and the R8 sparse
program, the 2026-09-26 sparse-sweep incident that killed ~34 web-review sessions, the 09-27
landedness correction, and this triage — and until now it had **no `WS-` record and no handoff**.
`grep -rl 'WORKTREE_GC_POLICY\|worktree_gc' agentos/workstreams/` returned nothing. That is why the
same pools keep being re-measured and why `do_not_redo` above is the most valuable field here.

## The standing lesson of ten pools

**The bytes were never where the program was looking, and the pools are not full of garbage.**
Wave 6 measured the largest of them: of 201.13 GiB across 207 registrations, **3 trees / 1.81 GiB
classify reclaimable** — 0.9%. 61% is content not reproducible from `origin/main` and 50% is
HUMAN-class. So a reach repair is worth making for the sake of a working safety net, not for a
payoff; say which of the two you are claiming.

**And the law generalizes past storage.** W10 applied it to the CI guards and found the
eleventh instance in `check_board_contradictions.py`, which printed that an ABSENT file "passes
all 5 board invariants" — a case where the tolerant predicate was correct and the reporter was
not. Two rules came out of it that the storage work had not yet articulated: an exit-code test
cannot pin a verdict SENTENCE (the mutation restoring that false claim left every parametrized
refusal case green), and a lexical scan cannot answer a semantic question (three regex passes
returned 177, then 57, then a set including guards that already print their count — the cheap
discriminator was a positive control, running each instrument against an empty subject set).

## The bound nobody had measured until 2026-09-29: availability

Waves 1-10 argued about SCOPE — which trees the sweeper may see. W12 measured whether it RUNS. Of
45 scheduled firings between 2026-08-13 and 09-28 it crashed on **13 (29 %)**, every one an uncaught
`subprocess.TimeoutExpired`, and it never started at all on four further days whose host was proven
up. So on roughly a third of days the trees it could already reach were not swept either, which
means **an armed deleter failing a third of the time cannot be judged on its scope at all.**

Two properties of that finding matter more than the number. First, it was recorded NOWHERE: the
receipt the job wrote (`last_run.json`) described only successful sweeps, so a crash left a healthy
file behind — the fix adds `last_attempt.json`, written on every exit path. Second, the receipt
still cannot see the four-day gap, because a file written BY the subject cannot report the
subject's absence; that needs an external age-based check, and it does not exist yet. And the fix
is in the repo, not on the host: the wrapper is the one file not re-read from `origin/main`, so only
an operator-authorised `install_worktree_gc_launchd.sh` reconciles it.

Fixing availability frees **zero bytes**, and saying so is the point — the same discipline §9's
reach work demanded. The ENOSPC remediation aimed at agent
working trees; the operator-data volumes turned out to be operator data (93.5% and 84%), the
scratchpad pool turned out to be 64.8% live, and the one pool with a real lever — 177.26 GiB of CI
runner git stores — is the one nobody calls a worktree. Attribute the target volume, state the
instrument's REACH, and report the reclaimable SHARE beside the pool size, before proposing any
further storage work.

## The one lever, re-measured — and why the obvious remedy was wrong

W15 opened the runner stores instead of citing their size, and the number that had been carried
since W4 moved. The **177.26 GiB** above is the WORKSPACE figure and the 87%-is-`.git` share was
measured on a single checkout; across all four `actions-runner*/_work/macro/macro` clones the pack
data is **141 GiB, 130 GiB of it in two of the four**, in two pathologies that share one cause and
have nothing else to do with each other:

| clone | `partialclonefilter` | packs | `.promisor` | pack bytes |
|---|---|---:|---:|---:|
| `actions-runner`   | `blob:none` | **36,271** | 36,271 | 5.3 GiB |
| `actions-runner-2` | absent | 35 | 0 | **72 GiB** |
| `actions-runner-3` | absent | 139 | 0 | **58 GiB** |
| `actions-runner-4` | `blob:none` | 47 | 46 | 5.7 GiB |

The filter column looks like the diagnosis and is not, and this is the part worth carrying forward.
The two expensive clones lack `filter: blob:none` because it was **deliberately removed** on
2026-09-23 after three production runs died at 65-67 minutes on an unretried promisor fetch
(`DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION`). Restoring it — the remedy the correlation invites, and
the one this session drafted before reading `ci.yml`'s own comment block — would have reverted a
correctness fix with three named failures behind it. A partial-clone filter also applies at
clone/fetch time, never retroactively: runner-4 *has* the filter and still wrote 4.53 GiB in one
burst, because an explicitly unfiltered fetch into a filter-configured workspace transfers
everything. What actually separates the columns is how many unfiltered pack checkouts each has
served. All four carry `gc.auto = 0` and **no workflow and no script in this repository performs
any git maintenance on them**, so every era's transfer behaviour accumulates permanently. The lever
is CONSOLIDATION of 35-139 near-identical whole-tree snapshots, not re-filtering, and it is an
operator decision because it touches live CI machines.

## The four-day gap had a second, quieter cause

W12 shipped the timeout fix and this session closed the other half of the question. The window is
**2026-09-18 → 09-21** and the cause is that the LaunchAgent was **not loaded** — not a crash, not
a slow sweep, not a powered-off host. `launchctl` reports `runs = 7` against exactly 7 logged
starts since 09-22; the counter resets on re-bootstrap, the plist's mtime is 2026-08-12 (so it was
re-LOADED, not re-installed), and `last reboot` shows continuous uptime since 2026-08-29. Full
census: **45 starts, 30 completions, 15 that started and never completed** — 13 of them uncaught
`subprocess.TimeoutExpired`, 9 at `RUN_TIMEOUT_S` and 4 at `GIT_TIMEOUT_S` — **plus 4 days with no
start at all.** #8176 addresses only the first mode, and structurally cannot address the second:
every instrument this programme owns is written BY the wrapper, and the wrapper did not run. A
deletion ledger cannot answer an availability question either — it records one row per deleted
worktree, so its gaps cannot distinguish "did not run" from "ran and found nothing". Detecting a
never-started run needs an EXTERNAL expectation, and that check does not exist yet.

## Scope is not sight — a second ratification ask withdrawn before it was made

W11 withdrew one operator ask (`…/agent-workspaces/tmp`, 0 registrations). W16 withdraws another,
and this one is more expensive to get wrong because it sits on the largest **proven** reclaim any
census in this programme has produced: 44.19 GiB in `/Volumes/Mastermind/tmp`, landed, clean, and
with nothing attached. §9 explained its non-reclaim as a missing configured root, which reads as
an invitation to widen `roots` — so the obvious next ask would have spent an operator decision on
a change measured to free **zero bytes**.

Two independent refusals, neither about permission:

| candidate | bytes | why the sweeper cannot take it |
|---|---:|---|
| `pr979-macro-88804-proof` | 41.76 GiB | standalone clone (`.git` is a directory) — in no `git worktree list`; `scan_orphans` skips the root at `worktree_gc.py:682` |
| `prophet-7187-proof-clone-20260920` | 2.43 GiB | same |
| the 17 registrations there | ~41 GiB | all DETACHED HEAD — no proof shape in `DEC:COMPLETION-SIGNAL-AUTHORIZES-RECLAIM` a detached HEAD can satisfy |

The reusable sentence is one level out from `DSC:A-HOST-CHECKOUT-BELT-MAKES-A-WIDER-ROOTS-LIST-INERT`:
**`roots` governs which paths a sweeper may ACT on, never which objects it can SEE.** A registry-based
tool has no handle on a standalone clone at any configuration, and the completion-signal law has
nothing to say about a detached HEAD however reachable it is. Before asking for a scope ratification,
ask what the tool's subject set actually contains. Reclaiming those two clones remains available to
the operator — as a DIFFERENT act, with a different tool and its own decision.

## Fleet census at the close of this wave

Registrations **789** (804/807 on 09-27/28): 292 `…/agent-workspaces/claude`, 232
`/Users/chriswong/Documents/Cluade`, 140 `/Volumes/Mastermind/worktrees`, 29 `…/sol`, 17
`/Volumes/Mastermind/tmp`, 16 `…/review`. The fleet is not growing right now.

Internal `/System/Volumes/Data` moved from 312 GiB free @83% to **360 GiB @81%** across this
session. **That was not this programme.** No wave here has deleted anything — every candidate sits
behind a standing decline or an unratified gate — so something else on the host released it, and
recording it as progress would attribute a reclaim to work that freed nothing. W9 through W16 buy
legibility, which is a precondition for ratifying the acts in `needs_ceo`, never a substitute.
