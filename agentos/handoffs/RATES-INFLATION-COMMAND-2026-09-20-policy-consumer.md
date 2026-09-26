---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-policy-consumer-integration-20260920-sol-010
model: sol
ended_because: ci_handoff
mission: >
  Preserve qualified policy-path evidence through fed_path, Rates & Inflation
  Command, and fed_stance without rounding away partial pricing or conflating
  ZQ/EFFR with SR3/SOFR.
state_before: >
  Nominal observation-origin work had merged, while the policy path still lost
  source dates/basis distinctions and downstream stance could convert fractional
  pricing into a rounded no-change read. Recovery has a separate owner in #7029.
changed:
  - path: engine/fed_path.py
    what: Preserve source/basis clocks, separate ZQ and SOFR, refuse unsupported extrapolation, and expose validated continuous pricing.
  - path: engine/rates_inflation_command.py
    what: Normalize versioned pricing at board ingress and render only reconciled numeric/prose assertions.
  - path: engine/fed_stance.py
    what: Consume qualified continuous equivalents while preserving existing stance thresholds and independent guidance.
  - path: tests/test_fed_path.py
    what: Add policy-date, basis, integrity, RIC and stance regression coverage.
  - path: research/RATES_POLICY_CONSUMER_INTEGRATION_2026-09-20.md
    what: Record capability boundary, verification, collision ownership and next product dependency.
verified:
  - claim: Selected policy/RIC/stance/recovery and downstream intelligence consumers pass together.
    command: python3 -m pytest -q --disable-warnings tests/test_fed_path.py tests/test_rates_command.py tests/test_risk_radar_recovery.py tests/test_master_brain.py tests/test_world_state.py tests/test_macro_workspace_monetary_policy.py tests/test_intl_recovery_quality.py tests/test_macro_monetary_hub.py
    result: 268 passed, 1 skipped, exit 0; exact tracked validation allowlist was temporarily materialized because sparse checkout omits data/.
  - claim: Candidate production/test modules compile and the diff has no whitespace errors.
    command: python3 -m py_compile engine/fed_path.py engine/fed_stance.py engine/rates_inflation_command.py tests/test_fed_path.py && git diff --check
    result: exit 0.
  - claim: Candidate-owned base blobs are unchanged on current origin/main despite ancestry movement.
    command: git rev-parse HEAD:<path> and git rev-parse origin/main:<path> for the four owned paths
    result: identical blobs for fed_path, fed_stance, rates_inflation_command and test_fed_path.
unverified:
  - claim: Risk Radar recovery consumes versioned policy without stale cached stance resurrection.
    what_would_verify: Reconcile and integrate the already-proven overlay with current #7029 owner/base, then run its full consumer suite.
  - claim: Deployed application/browser/SDK path uses the qualified pricing contract.
    what_would_verify: Lawful merge/release followed by current production input-to-user/machine consumer proof.
  - claim: Policy evidence improves leader-pullback entry economics.
    what_would_verify: Existing Evaluation owner admits and runs the pre-nominated common-endpoint experiment with qualified PIT inputs.
unresolved:
  - Open PR #7029 owns engine/risk_radar_recovery.py and its safety changes; this branch intentionally does not touch that file.
  - Rolling m12 changes still mix fixed-contract repricing with calendar/weight roll unless the existing collector preserves contract-period/weight evidence.
  - Daily real-yield five-session evidence still lacks qualified historical receipt timing for retrospective entry claims.
next_actions:
  - Open this collision-free policy/RIC/stance slice for independent review without merging or rewriting #7029.
  - Reconcile the previously tested recovery overlay with #7029's current owner/base after its source gate permits composition.
  - Continue PIT real-yield qualification and the pre-nominated leader-pullback evaluation through existing owners.
do_not_redo:
  - Do not rebuild merged #7291 nominal observation-origin work.
  - Do not rerun A V4, B Round2, or C HardenedV2 without a material invalidator.
  - Do not overwrite or whole-file replace #7029 recovery safeguards.
  - Do not create another policy collector, evaluator, episode store, score or trade authority.
danger_areas:
  - Source dates are not publication/receipt timestamps and cannot certify historical availability.
  - Rolling horizons are moving targets; a rolling delta is not automatically fixed-period policy repricing.
  - Legacy compatibility fields may be rounded; versioned consumers must use validated_pricing_view before making affirmative claims.
---

This handoff records a built source candidate, not deployment, trading promotion,
or parent-program completion. The user job remains leader selection plus
anticipatory/confirmed entries under qualified rates, real-rates, options and
company evidence. This slice only fixes policy evidence integrity on that path.
