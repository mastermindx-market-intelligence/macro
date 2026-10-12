# R10 source qualification evidence

Existing Crypto/Vector science workstream and draft PR8050. This directory is derived research evidence, not a live source registry, collector, alert, data subscription, allocation policy or promotion receipt.

## Identity and execution order

- Baseline R9: d636e9c405c0283209eb75b09d477d32003ff827.
- Source-qualification protocol committed before full numerical census:38b8f6d2f2580730993e81de95ef1b7fa34e2a14.
- Initial tested implementation committed before audit:342cb1454d0aee29028f53df9019fbc7a568c5b3.
- Technical synthetic-boundary amendment:90adead20f7797b10446c54d0ca0bf0779bacd19. The earlier implementation/test/result and CSVs remain under initial/. A declared single diagnostic rerun produced identical real-data findings and three byte-identical derived CSVs.
- Plan:research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_PLAN_2026-09-29.md.
- Findings:research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_RESULTS_2026-09-29.md.

## Verification

```bash
python3 research/crypto_science/r10/verify_evidence.py
```

The generator refuses to overwrite an existing result. Do not replay after a tool/network interruption: first reconcile source/output identities. No provider data or account request is needed to verify the saved results against the same local input hashes. The verification uses direct timestamp membership and scalar aggregation instead of the generator's rolling-grid expressions. It is same-session independent arithmetic, NOT independent scientist review.

- Initial12tests RED then GREEN; one additional receipt-before-completion test RED then GREEN.
- Final combined Crypto/Vector/science invocation:306passed,49warnings; compile/source-claim/diff checks passed.
- Five source frames,5,914window rows,125,488clock-convention masks and funding/old-display arithmetic verified.
-57input identities,18gates,137prior evidence artifacts and inherited sources unchanged.
- verification_units_failure.txt retains a verifier-only mistake that divided native timestamp integers as though always nanoseconds. The corrected verifier uses timestamp elapsed seconds. No generating result or source data changed for that repair.

## Files

results.json records census, scope/qualification, sensitivity counts, synthetic demonstrations and hash fences. flow_gaps.csv and flow_window_validity.csv retain the exact elapsed-window observations; r9_clock_coverage.csv contains only time/status/coverage fields, not target associations or fitted forecasts. provider_contract_observations.json holds bounded official-document interpretations and body hashes, not full copied documentation. initial/ preserves the original diagnostic. Test/verification logs retain failures and warnings. MANIFEST.json binds exact artifacts; it is not a second current-state owner.

## Main findings and limits

The current source has2,957hourly flow rows with9missing hours in one gap. One24-row window spans33hours and one72-row window spans81hours; the latest windows are complete. The original CVD only detects gaps>720hours, so shorter-gap truth remains a consumer repair. Scope is OKX aggregate BTC CONTRACTS, not Coinbase spot or observed net capital inflow.

Only364original R9forecast-qualified clock observations overlap complete24/72hflow windows under either tested label convention and0/1hadditional assumed delay. This does not resolve the timestamp convention or historical publication; none has the full recorded metadata/vintage required by the strict research gate. Even hypothetical qualification remains below R9's frozen1,000training minimum. No alpha/PnL/outcome association was fitted.

The secondary OKX funding collector keeps predicted fundingRate and discards realizedRate, settlement-time detail and formula/method in a daily mean. This is separate from the active BGeometrics model input. The BGeometrics old/current columns have1,089/80values and only one equal overlapping date; no unproven splice was made. Its generic parser discards unixTs and time-of-day, while the actual stored frame does not contain delay-receipt history.

Next is an existing-owner recording/elapsed-window repair with backward compatibility and real receipt tests, followed by source-specific semantic qualification and adequate observation history. Do not create a duplicate data/forecast/control plane, silently relabel units, infer earlier receipt times or claim a new trade signal from this audit.
