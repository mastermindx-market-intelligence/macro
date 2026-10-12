# R7 calibration/protection evidence

This is retrospective research in existing WS:CRYPTO-INTELLIGENCE / draft PR8050. It is not a live model, notification, trade or new source of portfolio authority.

## Frozen order

- Recovered R6 baseline: b445029abd6c84a66cadc572929e0beb702be4b7. Recovery found the completed run already published; it was not repeated.
- R7 preregistration: 2e8709464b643a33a5bca53b53999f53ad4756f5, before new R7 calculations.
- Tested implementation: 01a2b9c1ad89bfaae9200f581c5ef3ffa6cf29e1, before study execution.
- Exact plan: research/CRYPTO_SCIENCE_R7_CALIBRATION_PREREG_2026-09-29.md.
- Interpretation: research/CRYPTO_SCIENCE_R7_CALIBRATION_RESULTS_2026-09-29.md.

## Reproduction

The existing generator refuses to overwrite an existing results.json. Preserve results; do not blindly replay after a network interruption. Reproduction on a separately authorized research copy requires the source/input identities in results.json. No collector/backfill/account calls are needed.

Read-only verification of these saved results:

```bash
python3 research/crypto_science/r7/verify_evidence.py
```

The verifier independently expresses inventory accounting, eligibility/weights, root-gradient and forecast/decision arithmetic. A pass does not constitute independent scientific review or strategy acceptance. Final verification log is verification_arithmetic.txt; the broader existing suite and syntax/claim checks are in verification_final.txt.

## Files and outcomes

- predictions.csv: 1,012 candidate rows across two execution-delay assumptions; no-calibration/no-feature cases remain visible.
- accounts.csv: 3,528 paired-account scenario rows; 3,519 complete incumbent/delayed-cash pairs.
- policies.csv: 37,611 model/cost/risk-penalty scenario rows, not independent market episodes.
- results.json: all70quarter fits and their prior-only weights/offsets/mappings, forecasts/decompositions,504utility summaries and hash fences.
- red_tests.txt: actual eight failures before the R7 module existed; green_core.txt and green_research.txt retain subsequent outcomes and warnings.
- verification_arithmetic.txt: 7,038 cash/coin paths,70training snapshots,1,012prediction rows and37,611policy rows verified, with score/utility intervals.
- verification_final.txt: 276tests passed,27warnings; compile, source-claim and diff checks passed.

No recalibrated forecast or protection policy earns promotion. The recent-period calibrated-price Brier score is nearly equal to a simple recent event-rate estimate. The primary calibrated-price policy has negative mean protection utility; a modest positive calibrated-volume cell is fragile, uncertain and negative in the reused recent period. Five-percent drawdown allowance and twenty-basis-point expected-sacrifice floor are experimental objectives, not hard capital guarantees or user risk consent.

All55input identities,18gates and87prior evidence files are unchanged. The complete old scientific test file is retained as a byte prefix of the appended R7 tests. MANIFEST.json records the exact derived evidence and code/report digests; it does not claim raw market-data availability, independent review, live issuance, deployment or production acceptance.
