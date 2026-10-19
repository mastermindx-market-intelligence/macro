# Entry comparison basis repair (R3)

## Problem and change

A stale, unhealthy, or incomparable quote could be compared with entry geometry before its basis was qualified. That could expose a stop breach, chase conclusion, or distance/risk metric unsupported by the available evidence.

B4 now collects quote freshness, source health, and corporate-action basis blockers before price-dependent arithmetic. With any recognized comparison blocker, all five existing metrics are null and chase_state is unknown. Numeric stop and chase conclusions are withheld.

Independent owner invalidation remains valid for a terminal B3 lifecycle, a retracted event, or an explicitly breached structural state. Those cases preserve their invalidation and every observed comparison blocker while withholding price-dependent diagnostics.

The validator rejects internally inconsistent retained encodings, including rehashed packets that carry comparison blockers with numeric diagnostics or a price-dependent state. This verifies internal consistency, not source authenticity. General malformed-list refusal remains with the existing Daily Brief consumer.

Qualified formulas, strategy definition, horizon, and output schema are unchanged. Existing artifacts are not rewritten.

## Verification

Root executed the strategy-definition/B4 and Daily Brief suites: **319 passed**, with two inherited pytest temporary-directory cleanup warnings. Thirty-seven new regression cases cover blocked comparisons below, at, and above relevant price levels; independent invalidation; inconsistent and nonfinite diagnostics; and a retained unsafe Daily Brief input.

Six representative qualified outputs were byte-identical before and after: open, numeric stop, chase, pullback, approaching, and retracted. Their combined canonical SHA-256 is in verification.json. git diff --check passed.

A separate C3 source review accepted this bounded repair and regression design. Test execution is root's separate evidence.

## Scope

This creates no native entry geometry, ATR/anchor provenance, execution gate, trading authorization, ranking, or best-entry qualification. The native reader still returns no B4 availability projection. Geometry and metric owner inputs remain a native integration dependency.

Base: ff1b80af0f5efa5982656a59d63a0c623d5cd531.

Disposition: **DRAFT / HOLD**. Source review and test success are not a merge, activation, or scientific-qualification decision. Existing program holds remain in force.
