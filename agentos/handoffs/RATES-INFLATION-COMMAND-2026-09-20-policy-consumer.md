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

## Current-main source repair — 2026-11-09

This section records the current oldest-first maintenance composition under
`macro-backlog-oldest-first-20261105-c3` and
[Mastermind #2028](https://github.com/mastermindx-market-intelligence/Mastermind/issues/2028).
The September verification and collision statements above remain historical
evidence for original head `8da98209ad4a34450745780666c48b6999f2bfb2`.
They are not current execution receipts. The protected procedure pin for this
repair is `42f844017ec27554709282e72228c53b4c9ef8df` (bootstrap 1).

The current source is composed from main
`f92353edd85904b291d158e685c9c62d793587dd`.
The original patch cannot replace current `fed_path` or RIC wholesale:
main now owns D0 source provenance, D1 identification, cutoff and basis guards,
curve accounting and policy repricing.

### Preserved and repaired contracts

- The complete module-level legacy `fed_path.compute` signature and body remain
  byte-identical to current main. Its existing source pin remains
  `da05ae6617a54c0eb166e9e340cb74034d78c37c61a313d46ebe402239f39a35`.
  Existing D0/D1 helpers and the entire current test-file prefix are retained.
- The original dated pricing formula is an explicit
  `compute_qualified_pricing` projection in the same producer. The live snapshot
  captures each futures strip once, selects one eligible complete dated row,
  keeps the legacy envelope and adds `qualified_pricing`.
- RIC and stance share `consumer_pricing_view`. Typed evidence with a missing,
  unknown or inconsistent version cannot fall back to rounded legacy numbers.
  Bare legacy inputs, including existing untyped rights-only annotations, retain
  their compatibility contract.
- Qualified ZQ/EFFR pricing remains distinct from SR3/SOFR and front-quote
  context. Fractional 25bp equivalents remain continuous. Daily observation
  dates do not become publication or receipt clocks.
- Current D0 refusals and consumer cutoffs remain binding. Original D0/D1
  metadata is copied without restamping unknown clocks. RIC passes the raw
  envelope to its existing C0/D1 guards and preserves curve accounting and
  policy-repricing ownership.
- Stance retains its existing thresholds, closed enum and independent statement
  guidance. Every versioned pricing view remains display-only with no scoring,
  ranking, gating, sizing or trading authority.

### Verification state

The source composition, complete legacy `compute` pin, unchanged current
function bodies outside the named adapters, and retained test-file prefix were
checked directly from immutable source bytes. Twelve original feature test
definitions are adapted to the explicit projection; twelve additional test
definitions cover malformed evidence, date/rate-family mismatches, cutoff and
D0 refusal propagation, unknown clocks, legacy rights compatibility and an
offline snapshot-to-board-to-stance fixture. Parameterized cases are not counted
as executed tests.

**Fresh local tests, compilation and the newly authored offline fixture have
not been run in this session.** Historical 268-pass/1-skip and September CI
results are not reused as fresh execution evidence. Current natural CI and any
subsequent exact-head release disposition belong to the PR's source-linked
receipts. This document does not grant Ready, merge or production acceptance.

### Scope that remains separate

Risk Radar recovery source and safety work remain with #7029. Policy Monitor
#10493 retains its original uncertain execution and live design/browser/release
custody. This repair does not install their historical unpublished overlays,
create a new collector or evaluation owner, or change scientific and production
acceptance. Rolling horizons remain moving targets; fixed-period repricing,
historical availability, causal effects and entry economics require their
existing evidence and owners.

### Existing CI ownership

The [parent scope decision](https://github.com/mastermindx-market-intelligence/Macro/pull/7521#issuecomment-6738872035)
adds `engine/fed_path.py` and `engine/bonds.py` to each existing exclusive
`washout-turn-organ` and `unrun-picks-boards` owner. Their named tests reach RIC
through the dashboard helper; the new producer import reaches the existing
bonds dependency. The latter owner remains DATA. All 400 owner identities,
commands, installed dependencies, gates, timeouts and packing limits are
unchanged; all 398 other owner blocks remain byte-identical. Ordinary owners
retain their existing inferred scopes. No analyzer or packing result is
claimed for this prepared composition.
