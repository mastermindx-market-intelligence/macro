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

## Published preparation and refusal-side-effect follow-up

Existing source carrier is now draft **PR #7227**. The original publication was `1a82b838994e1222e5a6f9119575858527127f32`, not production adoption. A subsequent real-builder probe found upgrade/downgrade/backdate refusals could still replace the public deck before returning failure. The smallest source correction shares one transition validator between non-writing builder preflight and the sidecar writer; it does not duplicate policy or change successful v1 emission order. Three new cases were RED on the predecessor; the current five-suite battery is **204 passed in 98.41s**. See `refused-transition-proof.json` for exact changed-code digests.

Capacity request `C0BSBM78V1N/1789587618.242409` has been consumed by its capacity owner, who returned WAITING_CAPACITY / needs_placement / EFFECT_NONE. An eligible native delivery path was unavailable; no reviewer is assigned or STARTed. Its latest Sol ruling already says CONTINUE only on a material placement change. Do not duplicate that request or project an active reviewer. #7200 remains a separately frozen implementation.

## Independent-review return: canonical NYSE session fence

Review on parent `0e57dc01e494475802c62fc664924236544abb90` correctly found that v2 accepted weekend and holiday dates as canonical sessions. The incumbent #7227 carrier now reuses `lib.nyse_calendar.is_session` at producer preflight and v2 intake. TDD evidence is exact: four intended non-session cases failed on the parent; the focused repair set is 5 passed; the five-suite owner battery is 209 passed; the calendar/session-digest battery is 172 passed with one unchanged skip. Thanksgiving 2026-11-26 and Saturday 2026-11-28 are nonmutating producer refusals and `MALFORMED_SOURCE` at intake; the real 2026-11-27 early close remains 18:00Z; the existing 2026-11-30 later-session transition remains accepted.

Procedure is re-pinned to protected Mastermind `ac6180d0ca9107daae54f9eea6bd4b8aef92d630` (Skillpack 1.0.1 / bootstrap 1). Evidence: `research/us_prophet_availability/2026-09-16-turn-watch-v2/session-calendar-proof.json`. Preserve DRAFT/HOLD/PREPARATION_ONLY. The modifying seat must not self-approve; an independent exact-head re-review is required. Do not activate the registry, rewrite v1 history, dispatch production, merge, or claim current/served proof from this source correction.

## Current-base CI ownership reconciliation

A current-base merge probe found the candidate CI job duplicated the existing `prophet-us-context-and-grades` ownership of the intake and reconciler suites. A discriminating wiring test failed with both duplicate owner lists before repair. The candidate-only job is removed; the incumbent owner remains the sole owner of all four B1 suites, the new fence passes, and the five-suite owner battery is 210 passed. Current-main composition at `53efe6f47e9efcdde45a12bce483d7ec33f0bb8d` is conflict-free with no overlapping changed paths. Do not restore the removed job or treat CI infrastructure as the product capability.
