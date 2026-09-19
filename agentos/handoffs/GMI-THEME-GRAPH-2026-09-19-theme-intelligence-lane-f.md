---
workstream: "WS:GMI-THEME-GRAPH"
session: web/theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Build the disjoint Lane F incident and adversarial acceptance harness, freeze its
  evaluation registration before implementation, reproduce the two current semantic
  defects from immutable real-path source/artifact bytes, and return exact evidence to
  Lane A without editing A-E production sources or self-authorizing release.
state_before: >
  The Chairman-delivered Lane F packet was prepared but unassigned. Protected Macro
  source had the PRECIPICE-to-caution classifier and the ai_semi_f2 current-WATCH
  false-invalidation path; no Lane F branch, PR, harness, registration, or execution
  receipt existed. A-C had live dirty worktrees; E appeared later; no sibling had
  returned a remote exact head for independent acceptance.
changed:
  - path: research/theme_intelligence_acceptance/PREREGISTRATION.md
    what: "Frozen the zero-fit source-acceptance design, metrics separation, false-alert budget, mandatory discriminators, and release boundaries before implementation."
  - path: research/theme_intelligence_acceptance/incident_cases.v1.json
    what: "Registered the WATCH/invalidation case, ten-case mixed-state lane matrix, and authority expectations."
  - path: research/theme_intelligence_acceptance/harness.py
    what: "Implemented immutable Git-subject loading, real production-function invocation, input-to-served-card checks, authority checks, deterministic receipts, and mutation execution."
  - path: research/theme_intelligence_acceptance/acceptance_spec.py
    what: "Implemented the executable specification and seven adversarial/positive discriminators without creating a dark pytest suite or shared CI edit."
  - path: research/theme_intelligence_acceptance/current_main_result.json
    what: "Recorded the deterministic frozen-source verdict and exact input manifests."
  - path: research/theme_intelligence_acceptance/mutation_results.json
    what: "Recorded seven of seven mutations/discriminators killed."
  - path: research/theme_intelligence_acceptance/acceptance_spec_result.json
    what: "Recorded the executable-specification PASS receipt."
  - path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-19-theme-intelligence-lane-f.md
    what: "Returned Lane F state and exact gates to Lane A."
verified:
  - claim: "The preregistration was committed before evaluator implementation."
    command: "git log --oneline 68f80a8edf78966a3a89e1294038654944e9c217..800cdcfe159a4deb0eac109420b0878eeadf45f8"
    result: "PASS: preregistration 7e3b2353e73494cbb23412b16e6edb1ac546667a precedes implementation 800cdcfe159a4deb0eac109420b0878eeadf45f8."
  - claim: "The evaluator reads the real production functions and eight immutable source/artifact/card inputs from one Git subject."
    command: "python3 research/theme_intelligence_acceptance/acceptance_spec.py"
    result: "PASS: subject 68f80a8edf78966a3a89e1294038654944e9c217; eight input blob/SHA-256 manifests; checkout production modules byte-match the subject."
  - claim: "Current source is rejected on exactly the two preregistered semantic defects."
    command: "jq '{failed_checks,product_verdict,checks}' research/theme_intelligence_acceptance/current_main_result.json"
    result: "PASS: REJECTED_CURRENT_SOURCE; WATCH without transition evidence fired ai_semi_f2, and clean PRECIPICE alone mapped to caution; 9/10 remaining lane cases pass."
  - claim: "The current real path reproduces from Foresight input through production semantics, shared artifacts, and the served card."
    command: "jq '.checks.published_path_consistency' research/theme_intelligence_acceptance/current_main_result.json"
    result: "PASS: WATCH -> FIRED -> review in production result, theme_thesis projection, theme_lanes projection, classifier, and committed state_of_themes card. This is committed-byte proof, not deployed-browser proof."
  - claim: "Authority remained context/display only."
    command: "jq '.checks.authority_invariance' research/theme_intelligence_acceptance/current_main_result.json"
    result: "PASS: source and published may_rank/may_gate/may_size/may_escalate remain false."
  - claim: "The adversarial harness discriminates false greens and the bounded intended repair."
    command: "python3 research/theme_intelligence_acceptance/harness.py --mutations"
    result: "PASS: 7/7 discriminated, including missing transition basis, fired/crowding priority removal, artifact/card mismatch, published state/fired mismatch, authority escalation, and clean-PRECIPICE repair."
  - claim: "Committed result artifacts reproduce byte-for-byte."
    command: "Regenerate all three receipts to a temporary directory and cmp each against the committed file."
    result: "PASS; SHA-256 current_main=db260d359455d08ae72f69573770196b8a435154f83f6165f51cf765e5744a12, mutations=33338c39d337388ca704922b98dd684963b58239fcd48f3c53ac85fa441d4cc4, spec=055106eba35f3ee49818282c514438fdd2c9ca9741a2664cad02d381f1fb113c."
  - claim: "The product-pass gate fails honestly on the rejected subject while harness execution itself succeeds."
    command: "python3 research/theme_intelligence_acceptance/harness.py --require-product-pass"
    result: "PASS: exit 1 as intended for REJECTED_CURRENT_SOURCE."
  - claim: "No new unregistered multiple-testing harness or dark test suite was introduced."
    command: "python3 scripts/check_trial_registration.py && python3 scripts/audit_unrun_tests.py"
    result: "PASS: no new unregistered harness; unrun-test census exits 0. Lane A still owns the one shared CI-wiring decision."
  - claim: "The carrier changes no production source or generated product data."
    command: "git diff --name-only 68f80a8edf78966a3a89e1294038654944e9c217..800cdcfe159a4deb0eac109420b0878eeadf45f8"
    result: "PASS: only research/theme_intelligence_acceptance paths."
unverified:
  - claim: "A-E returned implementations satisfy the full mandatory discriminator matrix."
    what_would_verify: "Each sibling must return a pushed exact head; Lane F must run exact-head real-path and mutation checks on that head. No sibling remote exact head existed at this return checkpoint."
  - claim: "The evaluator implementation has an independent external code-review PASS."
    what_would_verify: "A read-only reviewer must review the final exact head; current evidence is executable specification plus adversarial self-tests, not independent reviewer identity."
  - claim: "Hosted CI executes the Lane F command."
    what_would_verify: "Lane A/incumbent CI owner admits one package-level wiring change and a hosted run tests the exact head."
  - claim: "The source repair is merged, deployed, or correct in the live browser."
    what_would_verify: "Lawful merge, natural publication, served-byte/browser proof, and independent acceptance after repair."
  - claim: "Prospective detection or return outcomes are mature."
    what_would_verify: "Forward accrual under the preregistered clocks and existing Evaluation/promotion owner."
unresolved:
  - "PR #7453 remains Draft/HOLD and must not be readied or merged by Lane F."
  - "Current frozen subject verdict is REJECTED_CURRENT_SOURCE; repair disposition belongs to Lane A and incumbent source owners."
  - "Full mandatory discriminator coverage remains NOT_YET_PROVEN until A-E return exact heads and their real-path interfaces."
  - "Hosted CI wiring and independent external review remain open gates."
next_actions:
  - "Lane A: consume PR #7453 and its three exact receipts; route the two actionable repair findings through existing source owners without copying Lane F into production."
  - "Lane A/incumbent CI owner: add or decline the single package-level command wiring; do not create six competing manifest edits."
  - "Lane F successor: when each A-E remote exact head exists, re-pin it, run the relevant mandatory discriminators and real input -> producer -> shared consumer -> served route checks, and return accepted/rejected/not-proven per lane."
  - "Lawful reviewer: independently review the final Lane F exact head before any merge adjudication."
do_not_redo:
  - "Do not rerun or reinterpret held #7064/#7095 as expected-return evidence."
  - "Do not edit A-E production sources from this evaluator carrier."
  - "Do not replace GMI, ThemeState, MarketOntology, Evaluation, forward graders, or existing ledgers with a reviewer-built store or engine."
  - "Do not convert REJECTED_CURRENT_SOURCE into a claim that the harness failed; the explicit product-pass gate is supposed to exit 1."
  - "Do not claim deployment, browser parity, prospective edge, merge, or acceptance from committed-byte reproduction."
danger_areas:
  - "A repair that merely returns ARMED for WATCH but still lacks temporal transition evidence is a false green and is killed by the harness."
  - "A clean-PRECIPICE repair must preserve fired-falsifier and independently high-crowding priority."
  - "Repeated renders must not be counted as distinct observations when later lanes add first-seen history."
  - "A shared artifact/card mismatch or any authority escalation must remain release-blocking."
---

# Theme Intelligence Lane F — Evaluation and Independent Acceptance return

## Lifecycle and carrier

- Delivery: Chairman supplied the Lane F packet to this concrete Web CEO session.
- Pickup: complete.
- START: exact Macro base `68f80a8edf78966a3a89e1294038654944e9c217` / tree `43d6f5a79c1c5654abd3380951f0c11072d2b83b`.
- Preregistration freeze: `7e3b2353e73494cbb23412b16e6edb1ac546667a` / tree `dd564a8e185b65afe2d81e59f37d71372b797679`.
- Implementation: `800cdcfe159a4deb0eac109420b0878eeadf45f8` / tree `92e01f6c394f5a90832518a420319b0794e112b8`.
- Shared carrier: Draft/HOLD PR #7453.
- Merge: not performed.
- Deployment/publication: not performed.
- Browser proof: not performed.
- Product acceptance: current subject rejected; A-E not yet proven.

## Capability delta

Lane F now has a deterministic, source-independent acceptance capability that binds one immutable Git subject, calls the real production falsifier and lane classifier, verifies eight committed input/artifact/card blobs, and separates evaluator success from product acceptance. It emits reproducible evidence and tests seven false-green/adversarial cases while preserving all production and authority boundaries.

## Current exact verdict

The frozen subject is internally reproducible but semantically rejected:

1. `ai_semi_f2` fires on current `WATCH` even though the check has no prior-stage/history input proving degradation from `RE-RATING`.
2. clean `PRECIPICE` maps to `caution`; the other nine preregistered lane-priority cases pass.
3. the real published path consistently carries the first defect through `theme_thesis`, `theme_lanes`, and the committed `state_of_themes.html` card as `review`.
4. rank/gate/size/escalate authority remains false.

This proves the incident and the evaluator, not a production repair or predictive edge.

## Return to Lane A

Lane A should use PR #7453 as the Lane F evidence carrier, reconcile the two repair findings with its own source ownership, and retain the current holds until exact-head checks, one coordinated CI admission, external review, lawful merge/publication, and browser proof are complete. Lane F should resume exact-head acceptance as sibling carriers return; no sibling had a pushed exact head at this checkpoint.
