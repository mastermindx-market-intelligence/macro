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
