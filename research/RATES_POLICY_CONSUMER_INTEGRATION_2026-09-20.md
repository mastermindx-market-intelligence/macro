# Rates policy consumer integration — 2026-09-20

Operation: `rates-policy-consumer-integration-20260920-sol-010`.
Parent: Macro #7088 / `WS:RATES-INFLATION-COMMAND`.
Procedure pin: Mastermind `bceb5e1593b1dd7e9e34c3bccbceb02e6ccd5a26`,
Skillpack 1.0.1 / bootstrap 1.

## Outcome

This candidate keeps policy-path evidence coherent through the existing
`fed_path -> RIC -> fed_stance` path. It does not introduce another collector,
policy service, score, evaluator, episode store, or trading authority.

The policy producer preserves source dates and rate-family/basis identity,
keeps ZQ/EFFR and SR3/SOFR separate, refuses unsupported extrapolation, and
retains continuous basis-point / 25bp-equivalent pricing without replacing it
with rounded meeting counts. Versioned consumers use
`fed_path.validated_pricing_view` so inconsistent or stale assertions cannot
regain affirmative numbers or prose downstream.

RIC normalizes versioned policy evidence at board ingress and renders qualified
continuous pricing. Fed stance consumes the qualified continuous equivalent
while preserving existing stance thresholds and independent statement guidance.
## Verification

Fresh direct policy/RIC/stance plus current recovery tests:
`python3 -m pytest -q --disable-warnings tests/test_fed_path.py tests/test_rates_command.py tests/test_risk_radar_recovery.py`
=> **105 passed**, exit 0.

Fresh downstream compatibility:
`tests/test_master_brain.py tests/test_world_state.py
tests/test_macro_workspace_monetary_policy.py tests/test_intl_recovery_quality.py
tests/test_macro_monetary_hub.py`
=> **163 passed, 1 skipped**, exit 0 after restoring the exact tracked validation
allowlist omitted by the sparse checkout. The first run's sole failure was that
missing-file checkout fault; its blob matched `origin/main` exactly when
temporarily materialized, and `git sparse-checkout reapply` restored the sparse
state without a data diff.

Current `origin/main` is hundreds of commits ahead of this worktree base, but
the four candidate-owned blobs on main are byte-identical to the base:
`engine/fed_path.py`, `engine/fed_stance.py`,
`engine/rates_inflation_command.py`, and `tests/test_fed_path.py`.
No source rebase/reset is required merely to erase ancestry distance.

## Collision and ownership boundary

Open-PR search found no current PR touching fed_path, fed_stance, or RIC.
Related rates worktrees were inspected and do not modify these paths.
Risk Radar recovery remains owned by open PR #7029 at
`77bbc21467302e9ef73818df29bc8aca34b3a609`; this candidate deliberately
does **not** edit `engine/risk_radar_recovery.py` or its tests.
## Remaining limits

The existing recovery consumer can still prefer separately cached stance
evidence. The previously executed private full-consumer fixture demonstrated
that risk and also proved a composition with #7029, but installing that overlay
belongs with the #7029 owner/current base after its own reconciliation.

The rolling m12 policy path is a moving-horizon measurement. Prior synthetic
decomposition proved that contract/weight/calendar roll can dominate or reverse
the apparent rolling change. Do not call the full rolling delta fixed-period
policy repricing until the existing collector preserves the required
contract/period/weight evidence.

Source dates are not publication or receipt timestamps. This implementation
does not certify historical availability, causal policy shocks, real-rate
turning points, entry timing, alpha, or profitability. It is context/display
infrastructure only and preserves existing score/rank/size/gate/trade ceilings.

## Next product step

After source review and release of this collision-free slice, reconcile the
recovery overlay with #7029 rather than duplicating its safety work. In parallel,
continue qualified real-yield/PIT receipt work and the pre-nominated
leader-pullback experiment under existing Evaluation owners and common-endpoint
rules. A later entry must never move the evaluation endpoint, and no-trigger /
no-fill opportunities remain in the denominator.

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
