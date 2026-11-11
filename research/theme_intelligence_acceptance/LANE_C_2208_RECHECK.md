# Lane C 2208 Exact-Head Independent Reacceptance

**Lane F operation:** `theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001`  
**Candidate operation:** `theme-intelligence-c-early-leadership-and-subthemes-20260919-sol-001`  
**Carrier reviewed:** Macro Draft/HOLD PR #7455  
**Candidate head:** `2208fe40039d356929fac0f96b626edc33d42288`  
**Candidate tree:** `29a774e0254d3224526466cbf0bf216fb5718b4a`  
**Verdict:** `REJECTED_FOR_REPAIR`  
**Evaluator:** `PASS`

## Capability delta accepted

The repair closes the previously reproduced stale-reclaim leak. A stale member now contributes zero
current reclaim/volume evidence, with null shares rather than fabricated numeric confirmation. The
candidate also moves completed-session selection onto the incumbent NYSE calendar owner, including
the 17:00 ET settle boundary and holiday filtering, and preserves internal missing bars as null rather
than forward-filling them into return chains.

The exact-head suites passed: **103 passed / 3 skipped** across `tests/test_subsector*.py`,
**45 passed / 3 skipped** across ThemeState/receipt/builder coverage, and **20 passed** for the sector
page. Agent OS validates with zero errors. Parent/subtheme separation and all authority flags remain
unchanged and false.

## Six remaining blockers

1. `STALE_LEADERSHIP_OBSERVATION_NOT_PROPAGATED` — stale embedded leadership can remain measured.
2. `UNAVAILABLE_PRODUCER_RECEIPT_LOST_AT_SHARED_CONSUMER` — producer unavailable state is lost.
3. `PRODUCER_FAILURE_REASON_NOT_PROPAGATED_TO_HEALTH` — `OWNER_INPUT_LOAD_FAILED` is lost downstream.
4. `NEW_TEST_SUITES_UNWIRED` — the three Lane C suites remain absent from hosted CI ownership.
5. `DIFF_CHECK_FAILURE` — eight trailing-whitespace errors remain in the Lane C handoff.
6. `REAL_PRICE_PROOF_NOT_REPRODUCIBLE_FROM_CARRIER` — exact 47-record proof bytes remain uncommitted.

Hosted run `35499134338` executed all twelve semantic packs successfully. Its overall CI failure is
contract-delta: the three Lane C suites above plus unrelated `tests/test_unified_dashboard_b1.py`
are unregistered. The unrelated dashboard suite is not counted as a Lane C repair blocker.

## Corporate-action basis follow-up

A subsequent deterministic Lane F audit against the same immutable `2208fe` subject resolves the
US first vertical's adjusted price basis. `data/baskets/ohlcv`, `data/stocks`, and `data/yahoo`
agree through NVDA 2024-06-10 and AVGO 2024-07-15 split boundaries with continuous adjusted
returns and identical volume. AAPL 2024-05-10 and XOM 2025-08-15 show the expected divergence
between dividend-adjusted `close` and dividend-unadjusted `close_price`, while the `stocks`
fallback matches the adjusted Yahoo close and volume.

Receipt: `corporate_action_basis_result.json`, SHA-256
`514fc26661b79a8ccc8a3473c6bfbec4449da40e1468a8f63067ee5022c139ac`, verdict
`US_FIRST_VERTICAL_ADJUSTED_BASIS_PROVEN`.

This closes the generic split/dividend-basis uncertainty for the current US first vertical.
It does not prove every historical corporate action, future basis stability, or predictive edge.

## Still not proven

Correction-safe first-seen/first-visible history, distinct observations versus repeat renders,
duplicate evidence-family identity, universal historical corporate-action correctness beyond the
representative immutable witnesses, deployed-byte/browser parity, and prospective predictive
outcomes remain unproven.

## Exact continuation

Preserve Lane C writer custody. The source worktree is already advancing the shared-consumer health
path after `2208fe`; Lane F must not overwrite those dirty bytes. When the existing writer pushes the
next exact head, re-pin and rerun this evaluator. Lane A/incumbent CI ownership continues to own the
single shared test-admission edit.