---
key: FINANCE-IMPL-CARRIER-IS-SEAT-PR-TASKS-SHIP-OFF-MAIN
question: >
  The Finance handoff says "preserve one implementation carrier" while Macro ship law says
  every change branches off fresh origin/main and squash-merges the same day. Does the
  Finance programme integrate task work on one long-lived carrier branch, or ship each task
  as its own PR off main?
answer: >
  The seat records PR (#7887, claude/finance-intelligence-implementation-20260924) is the
  OPERATION carrier identity — it holds Agent OS records, checkpoints, receipts and
  integration rulings, and it MERGES at each wave boundary (Wave 0 lands as soon as pickup,
  reconciliation and START are recorded); later checkpoints ride fresh records PRs that cite
  the operation key and #7887, because a squash-merged branch is never reused. Task
  work ships as fabric-built PRs off fresh origin/main in dependency order (Wave 1: contract →
  projection/overlap/private; Wave 2: evidence + API; Wave 3: UI + entries), each armed
  merge-on-green and merged by the seat on concluded green. Every task PR is recorded on the
  carrier by number/head.
rationale: >
  The Mastermind "one carrier" rule is a source-continuity rule (one operation identity, one
  place to reconcile START/effects), not a Git-topology rule. A long-lived integration branch
  would violate the house ship law, age out against main's ~1/min push cadence, and make every
  task inherit the previous task's unproven CI. The CDV-1 (#7792/#7880) and Semiconductor B
  (#7780/#7870) Fable seats already run exactly this shape.
alternatives:
  - option: "Lanes push sequentially onto the carrier branch; carrier merges once per wave"
    why_not: "Serialises path-disjoint lanes, forfeits per-task CI proof, and a wave-sized PR is the shape the merge sweeper and contract-delta handle worst."
  - option: "Lanes open task PRs whose base is the carrier branch"
    why_not: "A stacked integration branch off an aging base; house law forbids reusing a squash-merged branch and requires fresh-main ancestry per PR."
evidence:
  - "CLAUDE.md §Shared workspace + completion (fresh origin/main; same-day squash-merge)."
  - "research/finance/FINANCE_R12_CURRENT_MAIN_ARCHITECTURE_COLLISION_AND_CUSTODY_REVIEW_2026-09-24.md §9 (one implementation carrier; PICKUP/START recorded separately) at #7786 @615f1050."
  - "Precedent: memory consumer-defensive-cdv1-fable-meta-ceo-program (seat records PR #7880 + task PRs); #7870 semiconductor carrier with lane PRs."
affects:
  - "WS:GMI-FINANCE-INTELLIGENCE"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-24
---

# Carrier topology for the Finance implementation programme

The carrier PR is the place where START, checkpoints, dependency reconciliation and the
completion ruling live. Product code lands through ordinary task PRs so each task carries its
own concluded-green proof and the merge sweeper can act on it.
