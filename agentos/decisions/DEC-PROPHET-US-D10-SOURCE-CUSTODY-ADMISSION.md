---
key: PROPHET-US-D10-SOURCE-CUSTODY-ADMISSION
question: >
  Which installed fabric interface admits Prophet US R6 program work, how is each unit
  bound to one source-authoritative carrier, which routes may carry labor and review, who
  is an independent reviewer, and what is the durable return path? (R6 decision D10,
  ruling R6-D10-01)
answer: >
  D10 is resolved by recording the runtime as found, not a named architecture. The admitted
  interface is the Meta-CEO B kit: `remote_lane_v8.sh` lanes (one fix engine + one review
  engine over one branch/PR, bounded rounds and timeouts), `host_queue.sh` daemons draining
  one label at a time under load/active/disk/AC gates, `lease_broker.py` provider leases and
  `hosts.json` ceilings and windows (m1 only 02:00–11:00Z weekdays plus weekends). Custody:
  one unit = one `claude/<task>` branch, one PR, one lane label; a repair round is a new
  label on the same carrier; incumbents (#7180 for B01, #7572 for B03) stay with their
  writers; START is a non-empty `started pid=` only; PRESTART_REBIND only on positive
  no-START evidence copied out of the kit's overwritable files AND a dead prior wrapper
  (`kill -0` fails) — the 2026-09-23 dspr0a rebind violated this (the signalled wrapper
  survived its trap and wrote a duplicate ledger row, now VOID); timeouts reconcile on the
  same carrier. Placement: labor external-only (GLM first, MiniMax mechanical, Cursor
  fallback, Grok where signed in, bailian/qwen offpeak); m1/bm1 lanes ONLY through
  host_queue (window-gated) — every seat m1 lane on Wednesday 2026-09-23 was a direct
  launch outside the Chairman's 02:00–11:00Z window, a breach disclosed to the Chairman on
  #6805 and not ratified; Fable and Opus native children only as read-only auditors or
  bounded sub-orchestrators; direct seat execution only as the bounded principal
  exception. Independence, as it is: the lane review is a separate process but is anchored
  on the fixer's report and read-only by prompt only, so it is the FIRST slot for every
  unit; the second slot is the seat's reading of the diff plus, for judgment-bearing
  artifacts, a cross-family read-only Opus review recorded as `reviews/RV_*` (gaps for
  #7842/#7845 recorded; reviews of the pre-registration and the B04 contract commissioned
  before consumption). Return path: LANE_DONE →
  DRAFT PR → seat ruling/ratification → ready + merge-on-green → squash-merge on concluded
  green → production proof → checkpoint on #6805. Identity: the shared Chairman GitHub token,
  `Sol CEO` commit author, seat session 48cdfd56 named in every seat comment. Creates no
  authority; releases B00–B06, B20, B25, B26 from the D10 blocker only.
rationale: >
  D10's completion rule is runtime evidence with exact operator identity and an
  independent reviewer — documents alone grant no execution. Every rule in the ruling is
  backed by a lane log line, a queue-daemon launch, a lease id, a refusal code or a merged
  PR from 2026-09-23 — including the evidence that the seat broke two rules (a surviving
  wrapper with a duplicate ledger row; m1 lanes outside the Chairman window), which the
  Opus read-only audit (reviews/RV_D10_RULING_DRAFT_OPUS_2026-09-23.md, REJECT on v1)
  surfaced and v2 records rather than hides. Its falsifiers (a START without a lease line
  or without a pid, a duplicate ledger row or surviving wrapper, an out-of-window or
  non-queued m1 lane, a self-reviewed merge, a judgment unit without a cross-family review
  or recorded gap, a second lane on an incumbent's branch, a relaunch without the
  same-carrier read, a native child used as labor) are observable.
alternatives:
  - option: Cite the Executive OS operation/Attempt architecture from the package as the admission plane.
    why_not: It was not found as a callable runtime on this fleet; naming it would be a plan mistaken for a dispatch.
  - option: Let the seat take custody of #7180 to finish B01 faster.
    why_not: The writer is active on its carrier; a second writer replaces a STARTed effect, the D10 forbidden shortcut.
  - option: Admit same-vendor fix+review for rulings and design packets too.
    why_not: Judgment-bearing artifacts need a cross-family reviewer; the Opus read-only RV records exist for exactly this.
evidence:
  - research/prophet_v4/r6_program/rulings/R6-D10-01_SOURCE_CUSTODY_ADMISSION_2026-09-23.md
  - research/prophet_v4/r6_program/reviews/RV_D10_RULING_DRAFT_OPUS_2026-09-23.md
  - research/prophet_v4/r6_program/wave0/B_CARRIER_RECONCILIATION_7180_7572_2026-09-23.md
  - research/prophet_v4/r6_program/wave1/RV_7180_a991d4d22a93_2026-09-23.md
  - research/prophet_v4/r6_program/wave1/RV_7572_5e43db462b5f_2026-09-23.md
  - Macro PR 7855 (ruling), lane logs under the kit's ext/ directory named in the ruling
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: medium
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Program-scoped placement law for Prophet US R6. It records the kit as the admission
runtime and binds custody, placement, independence, return path and identity for every
unit the seat commissions. The Opus read-only audit rejected v1 on two evidence blockers; v2 folds
all findings and discloses the seat's own breaches.

## What this decision does not do

It creates no authority, widens no credential, grants no provider permission, changes no
fleet law in `CLAUDE.md`/`AGENTS.md`, and does not move B01 off its incumbent carrier. If
Mastermind's Executive/Capacity runtime becomes callable from this fleet, a successor
record re-maps the interface section only.
