---
key: MERGE-ARM-EXPIRY-14D-20261109
question: "How should stale merge-on-green arms be retired without closing their pull requests?"
answer: >-
  Disarm open auto-merge requests that have had no PR update for more than
  14 days and whose heads are behind or conflicting. Preserve the PR, add
  one tracking comment linked to this decision, and require the author to
  refresh the branch onto current main before explicitly re-arming.
rationale: >-
  The original Meta-CEO ruling reports about 200 armed PRs, a throughput
  of about 2-4 merges per hour, and an oldest arm of 48 days. It identifies
  stale arms holding queue position as an arm-hygiene problem. This
  frontmatter repair records that published rationale without independently
  re-verifying those measurements or changing the sweep procedure.
alternatives:
  - option: "(not recorded)"
    why_not: >-
      The original published ruling does not document an alternatives
      comparison; this schema repair does not infer one.
evidence:
  - "https://github.com/mastermindx-market-intelligence/macro/commit/6e21083a349da8750ff738cb8d701c92743b5cd6"
  - "Original ruling: Meta-CEO card t_b5022936"
affects:
  - "WS:CI-MERGE-CONTROL-PLANE"
# These two metadata judgments are recorded by the H4 schema-repair owner.
# They were not specified in the original published ruling.
confidence: medium
reversibility: easy
decided_by: meta-ceo
decided_at: 2026-11-09
---

# Merge-Arm Expiry Policy (14 Days)

**Decision ID:** DEC-MERGE-ARM-EXPIRY-14D-20261109
**Date:** 2026-11-09
**Authority:** Meta-CEO ruling, card t_b5022936; executed by mastermind-ceo (delivery owner)
**Status:** Active

## Ruling

A merge-on-green auto-merge arm EXPIRES after 14 days without a PR update. An expired arm is disarmed (never a PR close); one tracking comment linking this DEC is posted; re-arming is the author's explicit act after refreshing the branch onto current main.

## Rationale

Measured on macro (2026-11-09): ~200 armed PRs against ~2-4 merges/hr; the oldest arm dated 2026-09-22 (48 days). Stale arms hold queue position against fresh green work — the #10873 case (12/12 shards green, blocked behind stale proofs) is the canonical symptom. The controller is healthy; this is arm hygiene.

## Sweep Procedure (recurring as needed)

1. Criteria: OPEN + autoMergeRequest enabled + updatedAt > 14 days + head BEHIND/CONFLICTING (needs refresh).
2. `gh pr merge <n> --undo-auto` (fallback: GraphQL disablePullRequestAutoMerge) — verify autoMergeRequest null.
3. Post the uniform tracking comment naming this DEC.
4. Never close, never merge, never push in a sweep.
5. Measure merges/hr for 24h after each sweep vs the 2-4 baseline; report delta + disarm count.

## Companion Measures

- Sweep ordering prefers already-green heads over stale-proof arms where the sweeper allows ordering.
- CI workload cap review (8 -> 16) is conditional on measured runner utilization; no change without it.
