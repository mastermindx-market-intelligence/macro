---
# Metadata normalization by session01a1a7fb: the source did not record confidence or alternatives.
# Low confidence is a conservative normalization assessment, not a new ruling or authority grant.
key: MERGE-ARM-EXPIRY-14D-20261109
question: How should merge arms with more than 14 days without a PR update be handled?
answer: A merge-on-green auto-merge arm EXPIRES after 14 days without a PR update. An expired arm is disarmed
  (never a PR close); one tracking comment linking this DEC is posted; re-arming is the author's explicit
  act after refreshing the branch onto current main.
rationale: 'Measured on macro (2026-11-09): ~200 armed PRs against ~2-4 merges/hr; the oldest arm dated
  2026-09-22 (48 days). Stale arms hold queue position against fresh green work — the #10873 case (12/12
  shards green, blocked behind stale proofs) is the canonical symptom. The controller is healthy; this
  is arm hygiene.'
alternatives:
- option: (alternatives not recorded)
  why_not: The accepted ruling records its decision and rationale but does not document considered alternatives;
    this schema repair does not invent that history.
evidence:
- https://github.com/mastermindx-market-intelligence/macro/blob/15364780e3f3a1caac5f0c5f8abdc4f2af23967d/agentos/decisions/DEC-MERGE-ARM-EXPIRY-14D-20261109.md
- https://github.com/mastermindx-market-intelligence/macro/pull/10873
affects:
- .github/workflows/merge-on-green.yml
- scripts/merge_on_green.py
- docs/agent_guides/CODEX_DELIVERY.md
confidence: low
reversibility: easy
decided_by: Meta-CEO ruling, card t_b5022936; executed by mastermind-ceo (delivery owner), as recorded
  in the preserved source
decided_at: '2026-11-09'
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
