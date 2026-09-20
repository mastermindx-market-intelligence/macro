---
workstream: "WS:GMI-THEME-GRAPH"
session: web/theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Build and independently harden the disjoint Lane F incident/adversarial acceptance
  harness, reproduce the two current Theme Intelligence semantic defects from one
  immutable production generation, verify returned sibling exact heads, and return
  compact evidence to Lane A without editing A-E production sources or self-authorizing
  release.
state_before: >
  PR #7453 head b0129d26307f54e1cfd6cf88c3115c3e0393a806 had the first evaluator and Lane C
  exact-head rejection, but independent review proved its clean-PRECIPICE check could
  false-green a synthetic fixture without traversing the real Medical Devices renderer
  inputs. It also omitted active stale/null artifact-health enforcement, mislabeled a
  frozen-subject receipt as current-main, and could call a repaired candidate acceptable
  while Lane A's RE-RATING interpretation remained unresolved.
changed:
  - path: research/theme_intelligence_acceptance/PREREGISTRATION.md
    what: "Preserved the zero-fit freeze and added the independent-review hardening amendment: real Medical Devices path, native clocks, stale/null preservation, mixed-generation refusal, and the open RE-RATING contract gate."
  - path: research/theme_intelligence_acceptance/incident_cases.v1.json
    what: "Added the immutable Medical Devices PRECIPICE case, artifact-health cases, and explicit Lane A RE-RATING adjudication gate while preserving the original ten-case priority matrix."
  - path: research/theme_intelligence_acceptance/harness.py
    what: "Expanded the evaluator to ten immutable inputs, the actual ThemeState/asymmetry renderer path, typed clock and stale/null checks, data/site generation equality, eleven discriminators, cached immutable Git reads, and a contract-held repair-candidate verdict."
  - path: research/theme_intelligence_acceptance/acceptance_spec.py
    what: "Upgraded the executable specification to require the real Medical Devices failure, artifact-health PASS, ten-input manifest, three failed checks representing two defects, eleven killed mutations, and an unresolved RE-RATING gate."
  - path: research/theme_intelligence_acceptance/frozen_subject_result.json
    what: "Renamed the misleading current-main receipt and recorded the deterministic v2 frozen-subject rejection with exact real-path and artifact-health evidence."
  - path: research/theme_intelligence_acceptance/mutation_results.json
    what: "Recorded eleven of eleven false-green mutations/discriminators killed."
  - path: research/theme_intelligence_acceptance/acceptance_spec_result.json
    what: "Recorded the v2 executable-specification PASS receipt and open contract gate."
  - path: research/theme_intelligence_acceptance/lane_c_cases.v1.json
    what: "Preserved the previously frozen Lane C exact-head controls and blockers."
  - path: research/theme_intelligence_acceptance/lane_c_acceptance.py
    what: "Preserved the read-only Lane C exact-head evaluator."
  - path: research/theme_intelligence_acceptance/lane_c_exact_head_result.json
    what: "Preserved the Lane C REJECTED_FOR_REPAIR receipt."
  - path: research/theme_intelligence_acceptance/LANE_C_EXACT_HEAD_ASSESSMENT.md
    what: "Preserved the Lane C repair return to Lane A."
  - path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-19-theme-intelligence-lane-f.md
    what: "Replaced the stale seven-mutation checkpoint with this review-hardened Lane F return."
verified:
  - claim: "Protected procedure was refreshed before modification."
    command: "Read Mastermind protected master docs/sol_skills/INDEX.md plus COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE, and REVIEW_RETURN from b75a491db408892dfe6fe7c4bb9d40cfad8efcb3."
    result: "PASS: mastermind.sol_skillpack.v1 / 1.0.1 / bootstrap-major 1; all procedure reads came from the same protected commit."
  - claim: "The review-hardening assertions were proven RED before implementation."
    command: "python3 research/theme_intelligence_acceptance/acceptance_spec.py after cases/spec amendment and before harness amendment"
    result: "EXPECTED RED: exit 1; baseline still exposed only watch_invalidation and lane_matrix, so the required real_precipice_path check was absent."
  - claim: "The v2 executable specification passes against the immutable frozen subject."
    command: "python3 research/theme_intelligence_acceptance/acceptance_spec.py"
    result: "PASS: REJECTED_CURRENT_SOURCE; three failed checks map to two defects; artifact health passes; 11/11 mutations killed; RE-RATING remains LANE_A_ADJUDICATION_REQUIRED."
  - claim: "The evaluator now reads ten exact Git-object inputs and the renderer's actual state/asymmetry path."
    command: "jq '{inputs:(.inputs|keys),real_precipice:.checks.real_precipice_path,artifact_health:.checks.artifact_health}' research/theme_intelligence_acceptance/frozen_subject_result.json"
    result: "PASS: data and served ThemeState bytes match; Medical Devices is PRECIPICE, no fired falsifier, crowding=med, divergence=null, and production classifier/artifact/card all consistently but incorrectly emit caution instead of early."
  - claim: "Native clocks and typed stale/null evidence are enforced."
    command: "jq '.checks.artifact_health' research/theme_intelligence_acceptance/frozen_subject_result.json"
    result: "PASS: Foresight asof, ThemeState/thesis/asymmetry as_of+generated_at, typed stale_legs, and ag_fertilizer stale/null bottleneck leg are preserved; null is not numeric zero."
  - claim: "The mutation suite kills synthetic-only repair, clock loss, null coercion, and mixed generations in addition to the original attacks."
    command: "python3 research/theme_intelligence_acceptance/harness.py --mutations"
    result: "PASS: 11/11 killed; the full known-defect repair candidate clears source checks but remains SOURCE_DEFECTS_CLEARED_CONTRACT_GATE_OPEN."
  - claim: "Committed receipts reproduce byte-for-byte."
    command: "Regenerate frozen subject, mutations, and executable-spec receipts to /tmp and cmp each against the committed file."
    result: "PASS: SHA-256 frozen_subject=b560a710ffef04065a7929bc62389b35636e1afddce3ea3869c693b78369784c, mutations=d4e6e7f887fd343ecd26fe4b1d53fe625bfcc5c76e91c7fd5461c3925201cc21, spec=8f22890429420c24380b00f1e1112fa019e168993be109a5c6db2079a7aff79c."
  - claim: "The product-pass gate still rejects the frozen source."
    command: "python3 research/theme_intelligence_acceptance/harness.py --require-product-pass"
    result: "PASS: exit 1 as required; evaluator success is not product acceptance."
  - claim: "No parallel testing/control plane or dark suite was introduced."
    command: "python3 scripts/check_trial_registration.py && python3 scripts/audit_unrun_tests.py"
    result: "PASS: no new unregistered multiple-testing harness and zero strictly dark suites; inherited stale-baseline warnings remain outside this lane."
  - claim: "Changed Python and repository diff are syntactically clean."
    command: "python3 -m compileall -q research/theme_intelligence_acceptance && git diff --check"
    result: "PASS."
  - claim: "The carrier still changes no A-E production source or generated product data."
    command: "git diff --name-only b0129d26307f54e1cfd6cf88c3115c3e0393a806"
    result: "PASS: only Lane F research/evidence plus this Agent OS handoff; current_main_result is renamed, not replaced by a second result plane."
  - claim: "Lane C exact head remains independently rejected without source-carrier mutation."
    command: "Inspect preserved lane_c_exact_head_result.json and LANE_C_EXACT_HEAD_ASSESSMENT.md."
    result: "PASS as continuity: exact head 48156a43dfe0166ab658a99625f5b72dbd029eb4 remains REJECTED_FOR_REPAIR on eight blockers."
unverified:
  - claim: "The review-hardened final PR head has an independent external code-review PASS."
    what_would_verify: "A reviewer who did not author this repair must inspect the pushed exact head and return PASS or REQUEST_CHANGES. The earlier external review was consumed as repair input, not recycled as acceptance of new bytes."
  - claim: "Hosted CI executes the Lane F package command."
    what_would_verify: "Lane A or the incumbent CI owner admits one coordinated package-level wiring change and a hosted run proves the pushed exact head."
  - claim: "A, B, D, and E returned implementations satisfy the full mandatory discriminator matrix."
    what_would_verify: "Each sibling returns a pushed exact head and Lane F runs the applicable real-path/mutation checks."
  - claim: "The two production defects are repaired, merged, published, or correct in a deployed browser."
    what_would_verify: "Incumbent source-owner repair, exact-head acceptance, lawful merge, natural publication, served-byte/browser proof, and Lane A release adjudication."
  - claim: "Prospective detection or return outcomes are mature."
    what_would_verify: "Forward accrual under preregistered clocks and the existing Evaluation/promotion owner."
unresolved:
  - "PR #7453 remains Draft/HOLD; Lane F does not Ready, merge, deploy, or self-accept it."
  - "Frozen subject 68f80a8edf78966a3a89e1294038654944e9c217 remains REJECTED_CURRENT_SOURCE on two defects represented by three checks."
  - "RE-RATING lane interpretation remains LANE_A_ADJUDICATION_REQUIRED; a clean mutation candidate is held rather than labeled acceptable."
  - "Lane C exact head remains REJECTED_FOR_REPAIR; A, B, D, and E remain NOT_YET_PROVEN."
  - "Hosted CI, independent review of the repaired exact head, deployment, browser proof, and prospective outcomes remain separate gates."
next_actions:
  - "Lane A: consume the v2 receipts and adjudicate whether RE-RATING 'working' means thesis health only; preserve a separate late/extended entry posture and no entry permission."
  - "Incumbent production owners: repair temporal stage-regression evidence and PRECIPICE classification on their own carriers; return pushed exact heads for reacceptance."
  - "Lawful independent reviewer: review the final pushed PR #7453 head, including the real Medical Devices and artifact-health discriminators."
  - "Lane A/incumbent CI owner: add or decline one package-level command wiring; do not create six competing CI edits."
  - "Lane F successor: re-pin each returned A-E head, run applicable mandatory discriminators, and report accepted/rejected/not-proven separately."
do_not_redo:
  - "Do not rerun or reinterpret held #7064/#7095 as expected-return evidence."
  - "Do not edit A-E production sources from this evaluator carrier."
  - "Do not replace GMI, ThemeState, MarketOntology, Evaluation, forward graders, or existing ledgers with a reviewer-built store or engine."
  - "Do not restore the misleading current_main_result filename; this receipt evaluates a frozen subject."
  - "Do not convert REJECTED_CURRENT_SOURCE or the product-gate exit 1 into a harness failure."
  - "Do not claim deployment, browser parity, prospective edge, merge, or acceptance from committed-byte reproduction."
danger_areas:
  - "A repair that returns ARMED for WATCH without distinct prior-stage evidence remains a false green."
  - "A synthetic-only PRECIPICE repair can leave the real medium-crowding/no-divergence Medical Devices path quiet; the v2 harness kills that mutation."
  - "Foresight uses source-native asof; dropping it or collapsing clocks is release-blocking."
  - "Stale/null evidence must not become zero/low/confirmation, and data/site ThemeState generations must not diverge."
  - "A shared artifact/card mismatch or any authority escalation remains release-blocking."
---

# Theme Intelligence Lane F — review-hardened return

## Lifecycle and carrier

- Delivery and pickup: complete under the Chairman's live assignment.
- Original frozen source: Macro `68f80a8edf78966a3a89e1294038654944e9c217` / tree `43d6f5a79c1c5654abd3380951f0c11072d2b83b`.
- Preregistration freeze: `7e3b2353e73494cbb23412b16e6edb1ac546667a`.
- Review-hardening pickup head: `b0129d26307f54e1cfd6cf88c3115c3e0393a806` / tree `dc18742f186ca812c64d7d1529c30180c25e04f7`.
- Shared carrier: Draft/HOLD Macro PR #7453.
- Merge, deployment, publication, browser proof, and product acceptance: not performed.

## Capability delta

Lane F now binds the two known defects to real production functions and the actual renderer inputs, not only a copied or synthetic matrix. The evaluator reads ten immutable Git-object inputs, proves the AI Semiconductors WATCH false invalidation, proves Medical Devices traverses `PRECIPICE + no fired falsifier + medium crowding + no divergence` to the incorrect `caution` card, preserves native clocks and typed stale/null evidence, refuses mixed ThemeState generations, and kills eleven false-green mutations.

The executable evaluator is accepted as a bounded research capability. The product source is not accepted.

## Current exact verdict

The frozen subject remains `REJECTED_CURRENT_SOURCE`:

1. `ai_semi_f2` fires from current `WATCH` without prior-stage/transition evidence.
2. clean `PRECIPICE` is forced to `caution` in the closed matrix.
3. the actual Medical Devices classifier, lane artifact, and served card consistently reproduce that same defect as `caution` rather than `early`.

Artifact health and all authority invariants pass. A fully repaired in-memory candidate clears the known checks but remains `SOURCE_DEFECTS_CLEARED_CONTRACT_GATE_OPEN` until Lane A resolves the RE-RATING product interpretation.

## Return to Lane A

Use PR #7453 as Lane F's single evidence carrier. Route the two production repairs through incumbent owners, adjudicate RE-RATING without collapsing thesis health into entry permission, obtain one coordinated CI admission and a fresh independent review of the pushed exact head, and retain Draft/HOLD until all separate release gates are proven.

## Lane C continuity

Lane C exact head `48156a43dfe0166ab658a99625f5b72dbd029eb4` remains `REJECTED_FOR_REPAIR`. Its previously reproduced positive controls and eight blockers are unchanged; correction/history, duplicate-family, corporate-action, deployed-byte, and prospective gates remain not proven.
