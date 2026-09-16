---
key: COMMODITY-SAFETY-R1-REPRODUCED-GUIDANCE-CONFLICTS
claim: >-
  Commodity safety R1 is implemented on draft PR #7198 at semantic source
  1c0e7f85388be15f102adf1a3e8a7156a1fe91f1. Nine relevant suites pass 336 tests;
  32 synthetic browser cells pass theme, locale and document-fit checks.
  Independent review, merge and production acceptance are not established.
falsifier: >-
  Run python3 -m pytest tests/test_commodities_w6_truth.py
  tests/test_commodity_mtf_verdict_honesty.py tests/test_commodities_ignition_copy.py
  tests/test_commodity_signals.py tests/test_commodity_confluence.py tests/test_forex.py
  tests/test_commodity_index.py tests/test_commodity_conviction.py tests/test_commodity_alerts.py
  -q -p no:cacheprovider at the exact source; inspect #7198 and its committed
  browser manifest. A later production claim requires served browser evidence.
so_what: >-
  Resume this same PR/branch at review and release, not the old editing blocker.
  Do not redo the completed guidance, mobile warning or fixture repairs. Do not
  convert passing fixtures into production or numerical trading authority.
kind: landmine
verified_at: 2026-09-16
verified_by: >-
  #7198; nine-suite python3 -m pytest result at
  1c0e7f85388be15f102adf1a3e8a7156a1fe91f1: 336 passed, 0 failed, 2 existing
  NumPy warnings in 38.46s; scripts/check_ui_visual_evidence.py exit 0;
  scripts/check_design_system.py --mode enforce-added: 0 blocking findings;
  mockups/evidence/commodities-asset-first-r1/manifest.json.
scope: [macro, scripts/build_commodities.py, engine/commodity_mtf.py, templates/commodities.html.j2]
confidence: verified
---

# Commodity safety R1 — tested candidate, not production acceptance

Operation: `commodities-asset-first-safety-r1-20260916-sol-001`.
Branch: `claude/commodities-asset-first-safety-r1-20260916-sol-001`.
PR: #7198, DRAFT / HOLD-FOR-SOL. No auto-merge or merge-on-green.
Current procedure: Mastermind `8ba7deedde164c90298d3e88785d98e02fa5e2d2`, compatible Skillpack 1.0.1.

## Delivered to the candidate

Whole-sector instructions are descriptive conditions; missing evidence stays
incomplete. The index warning cannot imply constituent-wide stress. Commodity
MTF wording respects bearish daily/3D evidence and does not automatically call
pullbacks healthy or buyable. Numerical signs, weights and allocation rules and
FX alias behavior remain unchanged. Price proxies are not measured inflation.

The old mobile screenshots were rejected: a 390px page scrolled to 517px in EN
and 415px in ZH. Commit 8710b19b9a49e180f1fb8e24fe9c2017e3aba96a puts warning
reasons below the name/score and makes capture reject page overflow.
Commit 1c0e7f85388be15f102adf1a3e8a7156a1fe91f1 adds reproducible synthetic R1
states to the existing capture owner, using actual producer functions.

## Evidence and limits

The nine-suite run has 336 passes and no failures. Two pre-existing NumPy divide
warnings remain visible. The read-only source archive uses committed same-revision
FRED/Yahoo/COT data; other declared store groups are explicitly empty fixtures.
This is not complete live-data replay, backtest validation or production proof.

The 32-cell corpus covers mixed/incomplete headlines, gold timeframe disagreement,
and the risk board in both themes/locales and at 1440/390. Every cell fits its
viewport. Fixture omissions remain disclosed in the manifest. No live-price,
provider-session, navigation, entitlement or served-release proof is inferred.

## Next action and frozen boundaries

Obtain independent review of the exact semantic source and committed corpus;
resolve applicable current-head CI/security and existing release failures; then
verify the real served commodity page and its data. The known HK dead route
already has #7163; do not duplicate it. No release guard may be weakened.

After R1 acceptance, advance the approved asset decision matrix and coherent
publication bundle, then independently validated numerical challengers. No new
runtime, queue, workstream, provider call or capital operation was created.
DSC:COMMODITY-AND-FX-PRICE-SPINE-YAHOO-VENDOR-TERMS-ARE-RECORDED-ADVERSE still
holds any widening of Yahoo-derived redistribution. The checkpoint JSON retains
exact historic commits rather than duplicating the old transcript or red log.
