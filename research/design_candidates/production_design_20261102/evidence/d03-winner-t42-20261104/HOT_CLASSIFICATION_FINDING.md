# T42 additional finding — widened-cohort hot leg does not count

## Verified discrepancy at the frozen source

At baseline `ffda5424b75bbbb26e33a4d328043bbfb480e6ff`, the actual producer can emit a readable widened-cohort row with `fired=["running_hot"]` and `state="extended_healthy"`.

The initial synthetic fixture did exactly that for AAA on both r63 and atrz. The primary row had no fired legs and was correctly healthy. The failed initial assertion was a hypothesis falsified by execution; the output was never edited into a passing fixture.

| Cohort | Evaluated / counting checks | Fired | Actual state | Contract state |
| --- | --- | --- | --- | --- |
| primary |7/9|none|extended_healthy|extended_healthy|
| r63 |8/10|running_hot|extended_healthy|extended_watch|
| atrz |8/10|running_hot|extended_healthy|extended_watch|

The exact input archive, unmodified producer context, diagnostics, line trace, executed driver and failure log live in `diagnostics/initial-hot-only`. This completed one real producer run and did not reach its consumer build. The separate qualified fixture retains hot-only atrz rows, so no global corrected-state claim is made.

## Contract and causal path

[W2b §5 at the exact baseline](https://github.com/mastermindx-market-intelligence/macro/blob/ffda5424b75bbbb26e33a4d328043bbfb480e6ff/research/top_anatomy/W2B_SURFACE_DESIGN_SPEC.md) explicitly counts “hotter than most like it” for r63/atrz and excludes it from the frozen primary tier. One counting leg means “Showing wear”; three mean “Thinning out.” Episode age is separately context only.

Actual [engine source at the same baseline](https://github.com/mastermindx-market-intelligence/macro/blob/ffda5424b75bbbb26e33a4d328043bbfb480e6ff/engine/top_maturation.py):

1. `tier_counting_legs(tier)` includes the hot leg on widened cohorts.
2. `_checks_evaluated` uses that tier-specific set.
3. `_fire_legs(..., hot=True)` includes the hot leg in both visible legs and `fired`.
4. `classify(fired)` intersects with frozen `COUNTING_LEGS`, which excludes the hot leg.
5. `_build_tier` calls that classifier without supplying its tier-specific counting set.

The saved trace observes the real classification call and its following state. No classifier wrapper, fabricated output state, membership stub, or engine change produced this result.

The relevant existing W2b tests check additional counting-set membership, hot-only emission gating and provenance; they do not connect the hot-only input to its resulting state. This is a bounded test-gap observation, not a repository-wide absence claim.

## Scope and disposition

This is a descriptive grouping discrepancy. It establishes no forecast, model performance, trade authority or numerical market impact. The frozen primary board must remain unchanged. No new threshold, research reopening or calibration is justified by this evidence.

Existing [WS:TOP-ANATOMY](https://github.com/mastermindx-market-intelligence/macro/blob/ffda5424b75bbbb26e33a4d328043bbfb480e6ff/agentos/workstreams/WS-TOP-ANATOMY.md) names `coo-fable` and includes engine/top_maturation.py in its owned paths. That organizational owner is not proof of a current running lease. Held #7073 at `aca80371b6a2355352bb2ba103f9565edb7a0ab0` overlaps the engine file; preserve its source/hold. Active W07 concerns loader/template work and is not proof of a classifier repair.

A bounded publication search found no specific hot-classification repair carrier. That search result does not clear runtime custody. Before any separate repair phase, reconcile actual current ownership and held effects, bind an isolated writer and exact source head, and preserve the primary default, structural terminal rule, readability floor, per-tier cuts and primary-only ledger.

The present #10732 lane contains evidence only. No engine, production threshold, state rule, live ledger or existing owner branch was changed. No worker or external notification was dispatched.

## Source receipts

- W2b contract SHA256: `44f7295bcdf40e17d370716b562c80166307d9d32385e2fc4157a1f3041057d0`.
- Engine SHA256: `86497282e630d55dcc6ac32e0d5b8439cc032a3ccb6a8216603f8b9ade7bf095`.
- Workstream owner record SHA256: `64831c56022467cecad44c08d326b5a9e649b0aa343bbb5a5063916b65db46cc`.
- Initial executed driver SHA256: `ce3169864241591153982a56f1589013fa992040e8612179ff26fc3e8c106d99`.
- Qualified follow-up producer and browser reports retain their own separate hashes in README.md.

**Finding: CONFIRMED_SOURCE_CONTRACT_DISCREPANCY. Overall Winner/D03 acceptance remains open. Draft/HOLD release restrictions remain.**
