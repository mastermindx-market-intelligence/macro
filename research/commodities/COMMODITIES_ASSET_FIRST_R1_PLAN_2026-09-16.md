# Commodity asset-first safety — R1 implementation and acceptance

Operation: `commodities-asset-first-safety-r1-20260916-sol-001`.
Chairman approved the staged asset-first design and continued implementation.
Procedure pin: Mastermind `0fe8074ff953b2ced9025ed40f0f66019c759967`, Skillpack 1.0.1.
Source base: macro `bb02c526c4809564338f2a7208e063dbe86bc476`.
Existing branch: `claude/commodities-asset-first-safety-r1-20260916-sol-001`.

## Outcome and boundary

An investor must not infer permission to enter gold/silver from an unrelated
whole-complex breadth headline. The machine output must distinguish descriptive
breadth, observable timeframe disagreement, missing evidence, and asset policy.
This is the first safety slice of the approved broader commodity upgrade, not
acceptance of the complete asset decision matrix or a new trading model.

R1 changes only display decisions and evidence interpretation. Preserve numeric
short/mid/long votes, driver/trend leans, conviction computation and allocation
rules. Keep FX alias behavior unchanged. No new datasets, exports, live-capital
effects, provider calls, lifecycle objects or parallel decision stores.

## Implementation order

1. Pin failing cases against existing pure functions and the Jinja shock fragment.
   The initial baseline was 4 passing and 32 failing cases. Extend boundary tests
   for index-only versus member-wide warnings and persistent negative MACD states.
2. Replace whole-sector imperatives with descriptive conditions. Validate counts,
   recognized member identities, and confluence coverage; do not treat unknown
   evidence as positive clearance. Keep existing warning thresholds descriptive.
3. Guard commodity MTF wording against the actual displayed timeframe evidence.
   A positive ladder cannot establish alignment if daily/3D readings disagree;
   a pullback does not establish entry permission. Missing frames remain unknown.
4. Scope the dollar/copper-gold quadrant as price-derived context, not measured
   inflation. Missing/unknown index shock cannot render as Calm. Mixed/bottoming
   headline colors use existing warning tokens, preserving dark/light treatment.
5. Place new regressions in the already-registered W6 suite; update superseded
   old copy assertions explicitly. Preserve independent heat-grid, scope, counts,
   locale and numerical-policy controls. Do not add a parallel CI job.
6. Run complete pytest suites and source-diff checks. Review actual fixture pixels
   in dark/light, EN/ZH, 1440/390. Obtain independent exact-head review, then use
   the existing release owner and verify served browser/data behavior.

## Test and publication evidence

Run:
`python -m pytest tests/test_commodities_w6_truth.py tests/test_commodity_mtf_verdict_honesty.py tests/test_commodities_ignition_copy.py tests/test_commodity_signals.py tests/test_commodity_confluence.py -q`

The in-memory focused harness is preliminary behavioral evidence, not full pytest,
point-in-time backtesting, or production proof. No forecast performance is claimed.
The index-only warning must never be mislabeled as widespread constituent stress.
A failed render, unmerged candidate or green local test is not production acceptance.
The known release failures include the HK dead link (existing PR #7163) and the
macro market-state parser mismatch. Do not duplicate that repair or weaken guards.

## Execution ownership and continuity

Sol retains this bounded repair because the horizon/authority contradiction still
requires principal judgment. Source publication stays on the original GitHub branch
through the same Remote Desktop/gh carrier. No shared host checkout is modified,
no raw worktree is created and no Executive dispatch is claimed. Source inspection
and isolated verification are not an alternative publication path.

Stop at an actual permission/effect boundary; reconcile the same branch before any
repeat. On interruption, record exact candidate revision, tests, remaining review
and release obligations in the existing Agent OS discovery and checkpoint. The
broader program remains open until asset-first decisions are coherent in production.
