---
key: COMMODITY-ASSET-READ-QUALIFICATION
claim: >-
  R2 asset-read source 306834682e15121c636db1091a1de8f242c3608e rejects the scoped malformed-input cases
  and shares dated asset evidence across cards, detail, JSON and hub. Combined
  with R1 0b249399, 450 tests and 24 whole-page synthetic browser states pass.
  This remains an unmerged, independently unreviewed candidate, not production.
falsifier: >-
  Run python3 -m pytest tests/test_commodity_asset_read.py -q at #7224 and
  rerun the recorded ten-suite and --full-page captures on the exact source pair;
  supply a scoped counterexample where invalid input becomes positive clearance,
  a nonnumeric price advances price_asof, or card/detail state diverges.
so_what: >-
  Resume #7224 at independent review, CI and production release, not the old
  host disconnect or malformed-input editing blocker. Preserve the existing
  numerical models and distinguish fixture proof from served acceptance.
kind: landmine
verified_at: 2026-09-16
verified_by: >-
  COMMODITIES_QUALIFIED_R1_R2_RELEASE_PROOF_2026-09-16.json; exact source-pair
  pytest 450 passed, 2 pre-existing warnings in 27.14s; 24 canonical Chromium
  full-page fixture cells, 96 selections; evidence validator no findings.
scope: [macro, scripts/commodity_asset_read.py, scripts/build_commodities.py, scripts/build_vector.py]
confidence: verified
---

# Commodity R2 — qualified candidate, not a live trading improvement

Operation: commodities-asset-read-r2-20260916-sol-001. PR #7224 remains DRAFT/HOLD.
R1 #7198, parser #7215 and existing HK #7163 are separate dependencies. Sol keeps
source custody and acceptance. No independent reviewer ACK/START is asserted.

The 99 input-focused cases include 110 malformed scalar combinations and an
existing 1,458 nominal policy grid. Two capture-mode tests make 101 focused cases;
these overlap the 450 integrated tests and must not be added together. Prices
that are infinity, bool or numeric text cannot advance the observation date;
finite zero/negative prices are not filtered away. Values and policy targets are
not changed to force a risk-off result. New-entry permission stays null.

The requested-width guard prevents mobile viewport expansion from looking like
valid fit. Whole-page fixtures use actual combined source, touch contexts,
overlay checks and existing semantic controls; navigation/auth/live data are
explicitly omitted. The actual live.js packet-isolation test is separate and
uses synthetic responses. Neither is a production update or current trade advice.

The latest review packet must bind this semantic source and its evidence head.
After candidate acceptance, merge through the existing release owners and verify
served page/JSON/hub state. Do not rebuild the completed asset projection, source
merges, input qualification or capture owner. Do not make a second calendar,
publication store, retry mechanism, reviewer lifecycle or model authority.
