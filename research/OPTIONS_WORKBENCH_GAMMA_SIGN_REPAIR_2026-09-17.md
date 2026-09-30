# Options Workbench: local gamma-sign correction

Goal: the existing compute_gex payload reports a modeled gamma regime consistent with its own net exposure on either orientation of a zero crossing.

Authority: Chairman's Options Workbench recovery and current continuation; parent Terminal #603. This is a path-disjoint numerical correction, not the blocked Terminal replay-provider edit. No worker, provider purchase, deployment or signal promotion is implied.

Base: b337352ceadcae29c5247e4ef26e3a26358f7971.
Skillpack: Mastermind 7a191cc11039199843d4734c7df8d5523280e09c, 1.0.1/bootstrap 1.
Carrier: claude/options-workbench-r0-gamma-sign-20260917-sol-001.

Architecture: retain gamma_profile, its grid, nearest-crossing choice, distance convention and compute_gex consumer. Reuse that curve evaluated at current spot to select long/short. Do not add a parallel formula, estimator, model or classifier.

Closed scope: engine/gex_engine.py::_gamma_flip; tests/test_gex_regime_curve_sign.py; this evidence/continuation record. No inventory assumptions, field names, profile grid, exposure units, flags or ranking changes. The regime passport remains assumption/display-only.

Execution order: run existing engine tests; run the new actual-chain and compute_gex regression tests on original source; correct only the local-sign selection and misleading docstring; run focused engine/consumer regression suites and restore the original body temporarily to verify test discrimination; restore and byte-check the candidate. Publish a draft pending independent numerical review, current-head CI and required production proof.

Direct reason: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD. The source-bound counterexample is small and inseparable from the numerical interpretation; no admitted worker is carrying this operation.

Initial observation: at synthetic spot 99, the existing curve and net exposure are positive but the wrapper says short; at spot 101, exposure is negative but the wrapper says long. A crossing near 99.90 is descending. Actual market positions are not established by this fixture.

Do not redo the Terminal competitor study, source no-effect reconciliation or retained geometry tests. Do not reroute the held replay integration through this carrier. Parent parity remains incomplete.

## Verification and continuation

The local-sign correction is applied; profile grid, values, crossings, nearest-crossing selection, signed distance, units, inventory assumptions and display-only passport are unchanged. The actual compute_gex output now agrees with its own positive/negative exposure on both sides of descending crossings.

Fresh tests: 15 existing engine baseline pass. New regression suite on original source: five fail and five controls pass. Candidate focused family: 144 pass. Restoring original engine again reproduces the same five failures; candidate restored in finally and hash-checked. Expanded engine/state/hub/matrix family initially had 331 pass and two missing-file errors because sparse checkout omitted tracked site fixtures. The existing worktree_sparse add site command materialized those fixtures; rerunning the same full selected set yields 333 pass, zero failures/skips. No test or product condition was relaxed.

Exact consumer examples, commands/logs and hashes are in research/evidence/options-workbench-gamma-sign-20260917/. Evidence is synthetic, not market accuracy, live data or trading profitability. The parent forward-time field, expiry clock, adaptive profile resolution and Terminal timeline integration remain separate and unfinished.

Release requires independent numerical review of the exact head, applicable current-head checks and production verification through existing source/consumer owners. No worker is running and no GitHub approval, merge or deployment is asserted. This numerical carrier must never be used as an alternate route for the blocked Terminal replay edit.
