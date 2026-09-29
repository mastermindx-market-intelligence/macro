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
blocked_by:
  - "OPERATOR RATIFICATION — the `human_driven_roots` deny-list. FIRST because it is purely
     protective and can delete nothing. Today the 527 human-driven SSD checkouts (`sol/`,
     `review/`, all of `/Volumes/Mastermind/worktrees`) are protected by a path-naming heuristic
     nobody chose, and the obvious repair that makes a wider `roots` work is the same commit that
     would silently delete them."
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
    status: awaiting_ci
    pr: 8170
    depends_on:
      - W5
next_action: >
  Put the `needs_ceo` options to the operator, re-ranked by W6's measurement: the CI runner git
  stores (177.26 GiB, 87% `.git`) are now clearly the largest real lever, and the Full Disk Access
  grant is worth asking for on the broken safety net rather than on bytes — it frees 1.81 GiB.
  Ratify the `human_driven_roots` deny-list first regardless; it is purely protective and can delete
  nothing.
artifacts:
  - research/WORKTREE_GC_POLICY.md
  - scripts/worktree_gc.py
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

 The ENOSPC remediation aimed at agent
working trees; the operator-data volumes turned out to be operator data (93.5% and 84%), the
scratchpad pool turned out to be 64.8% live, and the one pool with a real lever — 177.26 GiB of CI
runner git stores — is the one nobody calls a worktree. Attribute the target volume, state the
instrument's REACH, and report the reclaimable SHARE beside the pool size, before proposing any
further storage work.
