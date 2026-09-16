---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/prophet-turn-watch-row-evidence-v2-20260916
model: sol
ended_because: ci_handoff
mission: >
  Prepare safe TURN WATCH retry evidence through the existing producer and B1
  intake while preserving deployed v1, all immutable history and source ownership.
state_before: >
  V1 binds unchanged session-row identities to mutable whole-document receipts;
  runtime-only and sibling changes can therefore stop canonical reconciliation.
changed:
  - path: engine/us_candidate_episode_intake.py
    what: Add closed-envelope v2 semantic row receipts while retaining exact file lineage.
  - path: scripts/build_turn_watch.py
    what: Add explicit staged version selection with new-session transition fences; default v1.
  - path: .github/ci/legacy-jobs.yml
    what: Register existing intake and reconciler suites under a bounded code-gate owner.
verified:
  - claim: Existing and v2 contracts pass on exact semantic head ea961c7998687952ec5539e4909df4236e7b081e.
    command: python -m pytest -q tests/test_us_candidate_episode_intake.py tests/test_us_candidate_episode.py tests/test_us_candidate_episode_reconciler.py tests/test_us_candidate_episode_wiring.py tests/test_us_turn_watch.py
    result: 201 passed; source archive unchanged; two forbidden runtime mutations detected.
  - claim: Previously accepted real v1 inputs and history remain reproducible.
    command: python -m scripts.reconcile_us_candidate_episodes --replay --repo-root ACCEPTED_INPUT_COPY --recorded-at 2026-09-16T10:43:43Z
    result: Zero appended events; identical ledger, projection and source hashes; no durable write.
unverified:
  - claim: The staged v2 protocol is adopted and deployed.
    what_would_verify: Independent review, exact-head checks, V4 acceptance and explicit new-session registry/cutover followed by real production proof.
unresolved:
  - Daily Yahoo archive freshness remains a distinct existing-producer dependency.
  - Existing independent review and CI gates must conclude before any release.
  - Rescue 35098112021 must be reconciled before any additional production effect.
next_actions:
  - Review this same staged source; preserve default v1 and current registry until the V4 owner accepts the bounded transition.
  - Complete the existing real-data freshness dependency and prove nonwriting reconciliation before one authorized publication.
do_not_redo:
  - Do not recreate the recovered prototype or rewrite old v1 events, receipts or generation files.
  - Do not duplicate the #7200, #7206, #7187 source owners or the independent review request.
danger_areas:
  - Runtime and sibling changes are not row semantic changes; semantic definitions remain binding.
  - A passing staged protocol is not current Yahoo coverage or a production repair.
prs: [7180, 7200, 7206, 7187]
discoveries: []
---

Current Chairman direction is continuation of end-to-end US Prophet recovery without clashing with parallel sessions. Procedure re-pinned at Mastermind `5ee11ab1e993616f3568cfca4069cb21fa61fd8f`; compatible required skills were fetched at that exact commit. Existing B1 law and core remain unchanged. This exact unpublished source was recovered from an interrupted turn; all six owned files matched its commit and no active process had the worktree as its cwd at the custody observation. No source branch or production run is replaced.

Evidence: `research/us_prophet_availability/2026-09-16-turn-watch-v2/verification.json`. Direct work reason: PRINCIPAL_JUDGMENT at the immutable identity/provenance boundary; the resulting preparation is bounded for independent technical review. Capability is BUILT_NOT_PROVEN / PREPARATION_ONLY. GitHub remains implementation evidence; this record does not originate an Executive Job or grant a reviewer production authority.
