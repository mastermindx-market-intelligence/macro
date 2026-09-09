---
workstream: WS:REGIME-HISTORY-HONESTY
session: claude/hmm-regime-research-20260909
model: sol
ended_because: ci_handoff
mission: Continue HMM research into the first owner-preserving temporal-honesty vertical slice.
state_before: >
  Research-only commit91fe14e existed without a PR or Agent OS discovery. Historical forward-filtered
  probabilities were reconstructed with later-fitted parameters but described as causal history.
changed:
  - path: engine/regime_one.py
    what: Historical-basis metadata; exact-date read-only saved-prediction reader; guarded existing-ledger append.
  - path: engine/quad_vector.py
    what: Preserve numeric probabilities and momentum while exposing reconstruction and heuristic-confidence basis.
  - path: scripts/validate_regime_fwd.py
    what: Early read-only --inspect-hmm-asof mode, mutually exclusive with --accrue.
  - path: research/HMM_REGIME_INTELLIGENCE_RESEARCH_2026-09-09.md
    what: Correct HMM baseline to the explicit0.25 caller, versus helper/axis-sign default0.5.
verified:
  - claim: Existing and added model, reader, CLI, and append tests pass.
    command: python3 -B -m pytest tests/test_regime_one.py tests/test_regime_hmm.py tests/test_validate_regime_fwd.py tests/test_perception_contracts.py -q
    result: 87 passed after overflow repair, four rounding-boundary cases and RED-to-GREEN real-CI registration; numerical thread counts1; sparse-checkout data guard retained.
  - claim: Actual CLI reads committed legacy records and refuses missing dates without writing.
    command: Existing validator main/parser over a temporary mount of the exact477b9c3 ledger; source and before/after hashes in recorded_input_cli_proof.json.
    result: 40 source rows; first/last inspections exit0 as legacy_record, missing date exit1; bytes unchanged and no output files created.
  - claim: Named HMM source paths did not move between research and current main pins.
    command: git diff c3d7f1d4149176e35abf6077c18c96513abe6600 477b9c3f449e451063634f1078fc6ce47e209648 -- engine/regime_one.py engine/quad_vector.py scripts/validate_regime_fwd.py
    result: Empty delta on those paths.
prs: [7015]
unverified:
  - claim: Review of the CI-registration/test/evidence delta and concluded hosted integration checks.
    what_would_verify: Reviewer return plus current candidate CI and source-continuity receipts on the same PR.
  - claim: Natural production adoption of the new row metadata and consumer.
    what_would_verify: Normal nightly writer at accepted source plus production read-only inspection of its saved row; no manual accrual.
  - claim: Source-vintage correctness and calibrated forecasting/portfolio improvement.
    what_would_verify: Existing-owner PIT replay and preregistered forward evaluation; timestamps alone do not establish either.
discoveries: ["DSC:REGIME-FILTERED-HISTORY-USES-LATER-FIT", "DSC:REGIME-TESTS-WERE-GRANDFATHERED-CI-DARK"]
unresolved:
  - Source is not yet a production acceptance; full neural-web integration remains a separate continuation.
  - Broad GraphQL open-PR file census failed; do not describe a complete estate-wide collision clearance.
next_actions:
  - Review the exact source candidate and current main changes; retain this branch/PR as the single carrier.
  - Conclude applicable CI and normal release checks without bypass or unrelated main fixes.
  - After accepted delivery, inspect one naturally emitted production record through the existing reader.
  - Then ratify the source-audited W1 briefing contract; preserve intentional prior-run context, actual source clocks and existing consumer ownership.
do_not_redo:
  - No replacement HMM, probability store, memory plane, event plane, or risk scorecard.
  - No historical reissuance, source-vintage certification, or grading-threshold change in W0.
  - Do not touch held regime UI PR6685, policy-transition PR6788, or the disjoint macro_workspace publication-prior PR6984.
danger_areas:
  - Forward recursion does not make later-fitted historical parameters point-in-time.
  - Preserve four-decimal probability rounding; valid stored sums may differ from1 by0.0001.
  - Legacy saved predictions lack issuance/model metadata; keep them legible but explicitly uncertified.
  - Single nightly writer is an existing assumption; W0 does not add or certify concurrent-writer safety.
---

This is a recoverable CI/review checkpoint, not a claim the program is finished or a runtime liveness record.
Protected procedure: Mastermind686af274d8ae1558f3f3ae35e0b3aae68be80a01, Skillpack1.0.1/bootstrap1.
Finite read-only technical reviews were attempted: Astra failed with unsupported-client400; two Sonnet calls returned empty results; Terra returned one actionable overflow finding. All those processes exited and no watcher or Executive Job was created. The finding was reproduced with two failing tests and repaired. A subsequent finite Terra read-only review of exact e4d6bf3 passed with no blocker; full result and scoped limits are in independent_review_r2.md. All review processes exited; no watcher was created. The later CI-registration/test/docs delta still requires review before release.

Release audit discovered the four suites were grandfathered CI-dark. One existing macro job now names
all four, its HMM dependency is declared, and exactly four baseline entries were removed. The new
registration regression failed before the manifest repair and passed after it. Planner validates210
existing jobs; this is not remote execution proof. Receipt: review_and_ci_registration.json.
