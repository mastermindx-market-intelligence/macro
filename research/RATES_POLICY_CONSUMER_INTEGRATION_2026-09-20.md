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
