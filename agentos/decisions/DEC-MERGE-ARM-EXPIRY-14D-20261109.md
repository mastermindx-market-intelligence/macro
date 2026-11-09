---
key: "MERGE-ARM-EXPIRY-14D-20261109"
question: "What expiry rule does this record establish for a merge arm after fourteen days without a PR update?"
answer: "A merge-on-green auto-merge arm EXPIRES after 14 days without a PR update. An expired arm is disarmed (never a PR close); one tracking comment linking this DEC is posted; re-arming is the author's explicit act after refreshing the branch onto current main."
rationale: "The original ruling attributes queue delay to stale armed PRs and cites #10873. Its reported counts and throughput remain historical claims of that source; this schema repair does not independently reproduce them or establish a controller change."
alternatives:
  - option: "(not recorded)"
    why_not: "The original ruling does not record rejected alternatives. This metadata repair does not reconstruct an unrecorded decision history."
evidence:
  - "Original authored ruling: https://github.com/mastermindx-market-intelligence/Macro/blob/6e21083a349da8750ff738cb8d701c92743b5cd6/agentos/decisions/DEC-MERGE-ARM-EXPIRY-14D-20261109.md ; blob bccd707f939993af9e9b1ae641648a75f9149c10"
  - "Original authority attribution: Meta-CEO ruling, card t_b5022936; executed by mastermind-ceo (delivery owner)"
  - "Observed missing-frontmatter failure: https://github.com/mastermindx-market-intelligence/Macro/actions/runs/42574058849/job/129017692345"
  - "Metadata-only repair and limitations: https://github.com/mastermindx-market-intelligence/Macro/pull/7254#issuecomment-6731531428"
affects:
  - ".github/workflows/merge-on-green.yml"
confidence: "low"
reversibility: "easy"
decided_by: "Meta-CEO ruling, card t_b5022936; executed by mastermind-ceo (delivery owner)"
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
