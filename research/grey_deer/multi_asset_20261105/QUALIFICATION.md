# MA-1 source qualification and release boundary

**Operation:** `multiasset-risk-20261105-sol` | **Parent:** WS:GREY-DEER-RISK-INTELLIGENCE / MAS-258 | **Date:** 2026-11-05 America/Vancouver

**Status:** IMPLEMENTED_SOURCE / BUILT_NOT_PROVEN; parent program INCOMPLETE. This qualification records what a source slice does and does not prove; it is not market forecast approval, capital-policy authority, a deployment receipt or user acceptance.

## Candidate and custody

- Source carrier: Macro operation branch `sol/web-multiasset-risk-20261105-sol`; initial published integration head `0111df4dba3d6a767097f5934de5d345e4bb95e3` based on `20959c5e8183f44678df4dbfc26ac246665ba2bf`.
- Governing protected Skillpack pin reverified at Mastermind `6fa7838d811e305c10035f6531e75d8e547d9d03` (schema mastermind.sol_skillpack.v1, version 1.0.1, bootstrap major 1). Earlier implementation used compatible `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.
- No competing author may overwrite this operation's dirty worktree. Previous Fabric child `multiasset-core-20261105-a` is terminal, native rc=75 / host_temperature_at_or_above_limit; no usable code/result accepted and no replay is authorized or attempted.
- Other in-flight Grey Deer publication and warning repairs remain on their incumbent carriers; this increment does not relabel or merge them.

## What is implemented

1. Strict `engine/multi_asset_context.py` qualifies explicit timestamped, currency-labelled, revision/source/evidence-family-aware measured returns, composes deterministic same-window relative wealth and safely abstains on missing, malformed or stale evidence. Currency conversion is an explicit two-leg compound calculation with source ancestry; no assumed FX sign, no rank/gate/size/trade authority.
2. `engine/multi_asset_daily.py` and `scripts/risk_envelope_multi_asset.py` provide an **observational** same-US-cash-session snapshot of existing adjusted Yahoo ETF closes. The source is an index/market proxy in USD, not proof of offshore same-clock trading, realtime capital flows, first-known intraday quote availability, actual holdings, jurisdictional eligibility or executable bond/futures/commodity returns.
3. The existing Risk Envelope accepts this data as an additive non-voting context, preserves state/hazard/repair/policy separation, and carries it into the existing Radar template, retaining old behavior when absent. Machine-readable contract and enrolled tests cover the new section.
4. Existing dated capture in `evidence/context.json`: requested 11, observed 10, comparable 9, expected US cash session 2026-11-05 but last complete comparable end session 2026-11-04; visibly **STALE**, never a live November-5 signal. Captured-at is a collection clock, not a historical first-known quote clock.
5. Existing `lib/store.py` source documents `yahoo` adjusted `Adj Close` total-return basis; this is a **vendor-adjusted proxy**, not an executable transaction price or a replacement for the qualified house total-return/accounting owners.

## Verification / scientific limits

- Recovery-run local command: `python3 -m pytest -q tests/test_multi_asset_context.py tests/test_multi_asset_daily.py tests/test_multi_asset_radar_ui.py --disable-warnings --maxfail=1` — **132 passed, 6 warnings, 51 subtests passed**, exit 0.
- Additional owner/risk/legacy receipt tests: pending at this record's creation; final outcome must be appended with original command/receipt, not inferred from partial dots.
- Earlier browser harness receipt describes **16 synthetic browser cases / four representative captures**, but not authenticated production. Existing EW-P4 visual source receipt was invalidated by the additive template change; the exact-source screenshot recapture is locally present but must pass the named receipt-integrity test before it is treated as qualified evidence.
- Tested user-facing truth here is *descriptive return comparison*. No foreign exchange local-market integration, live quotes, high-frequency pressure forecast, prospective prediction/calibration, account-specific optimization, shadow trade policy or notification delivery is qualified.

## Immediate completion gates

1. Adjudicate broader tests, updated visual receipt and source-diff quality; preserve truthful failed/held results and existing historical evidence.
2. Commit/push only qualified edits on this original workspace publisher and open/reuse its original source PR; run exact-head hosted CI/required security checks and resolve concrete failures.
3. Advance through actual protected release where lawful; verify installed real source -> Risk Radar consumer and stale/unavailable negatives. Separately reconcile Terminal/Mastermind consumers and original book owner.
4. Continue MA-2 fast pressure, MA-3 preregistered validation, MA-4 shadow portfolio alternatives, MA-5 cross-product alert integration and MA-6 controlled activation under the parent; each maintains separate scientific and policy gates.

**Never** promote relative outperformance to positive absolute return, qualitative evidence to a crash probability, a refreshed cache to contemporaneous quote information, or a code/PR merge to actual portfolio control.

## Recovery qualification update: November 5, 2026

The complete local Risk Envelope / Radar / legacy-screen test command `python3 -m pytest -q tests/test_risk_envelope_multi_asset.py tests/test_risk_envelope.py tests/test_risk_envelope_radar_integration.py tests/test_ew_p4_descriptive_ui.py --disable-warnings --maxfail=1` finished **304 passed, 3 skipped, 6 warnings**, exit 0. The visual receipt source-and-screenshot guard therefore passes for the regenerated 68-case EW-P4 screenshot record. This recapture was required because the risk-envelope band template acquired the new additive content; it is not authenticated production UI acceptance. Earlier captured receipt versions remain available from Git history.

`git diff --check 20959c5e8183f44678df4dbfc26ac246665ba2bf` exited 0. The actual candidate unified diff piped into `scripts/check_design_system.py --mode enforce-added --diff-file -` returned **0 blocking findings**, exit 0 (25,320 pre-existing nonblocking estate findings are explicitly not this candidate's acceptance). The new `engine/multi_asset_context.py` malformed-Unicode safe-hash fix and two adversarial tests are included in the 132-test pass. A separate exploratory invocation targeting a nonexistent specific pytest node collected no tests; no result is inferred from that invocation.

At this verification boundary current Macro main was observed at `2dc4765c0a0ae2ef33ce773f990b4bbda842b925`, newer than the original implementation base. The relevant `.github/ci/legacy-jobs.yml` upstream change is in a different hunk from this candidate's CI enrollment; this comparison is not a native merge-group or integrated-release proof. Exact PR/head CI, native review rules, mergeability and production must be established separately.

The 73 regenerated legacy screenshots are source-associated test artifacts, not changes to allocation semantics. Preserve the branch's earlier committed screenshots in Git history and retain the new receipt/hash cohort only with its passing integrity test; avoid claiming a production capture.
