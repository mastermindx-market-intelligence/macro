---
key: COMMODITY-ASSET-READ-QUALIFICATION
claim: >-
  R2 b5b38cc0b2aa78778cb00e85c25f278b3100fc59 discloses the actual calibration source without changing model
  outputs. Its exact composition with R1 0b2493990358d44dee5b625176c5289eab9a04e4 passes 483 tests,
  32 full commodity-page fixture states and 8 hub-component navigation states.
  It remains an unmerged, independently unreviewed candidate, not production.
falsifier: >-
  Run python3 -m pytest tests/test_commodity_asset_read.py -q at #7224;
  supply a case where the disclosed calibration differs from the scorer object,
  a missing/foreign receipt looks measured, or a source-only change alters a score.
so_what: >-
  Continue with independent review and existing release dependencies, not the
  superseded blocked calibration edit. Preserve the candidate and exact proof.
kind: landmine
verified_at: 2026-09-17
verified_by: >-
  COMMODITIES_CALIBRATION_ORIGIN_PROOF_2026-09-17.json: 483 passed, two existing
  NumPy warnings; 5/5 deliberate regressions detected; 8/8 identical-input
  before/after cases preserve original conviction fields and exposure targets.
scope: [macro, scripts/commodity_asset_read.py, scripts/build_commodities.py, scripts/build_vector.py]
confidence: verified
---

# Commodity R2: calibration disclosed, not a validated trading improvement

Same operation commodities-asset-read-r2-20260916-sol-001, PR #7224. Sol remains
source writer and acceptance owner; no reviewer pickup or START is claimed.
R1 #7198, parser #7215, test repair #7242 and existing HK #7163 remain separate.
The old refused-write state and missing helper tests are explicitly superseded by
this accepted same-carrier source change. No provider or permission gate was bypassed.

The label distinguishes stored, weak, unrated, default and unavailable evidence.
The exact parameter object is resolved once for scorer and projection. Stored
horizons are declared historical bars, not a current-entry guarantee or probability.
Metadata never changes scores, confidence, model labels, posture or exposure.
Malformed identities/schemas are qualified before comparison. Caller-written
marketing labels are not forwarded. New-entry permission remains null.

Tests and fixture counts overlap earlier results; do not add them into a total.
The whole-page fixtures omit global navigation/auth/live data. The eight hub
component journeys use actual owner markup/styles and links, not complete hub proof.
The numerical replay hashes both arms' input frames/drivers/extras and uses dated
archived observations; it is not current market data or validated trading edge.

Next: review the exact semantic source and its evidence, reconcile current CI and
source-base compatibility, then publish through the existing static path and verify
served page, JSON and hub together. Do not redo the completed projection, typed-input,
price-clock, quote-isolation, responsive or calibration work. Do not create a second
calibration engine, publication store, retry system, worker lifecycle or trade policy.
