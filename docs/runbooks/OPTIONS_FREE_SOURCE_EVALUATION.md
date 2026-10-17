# Free options source access — implementation and custody (2026-10-08)

Status: private evaluation data ACQUIRED; parser implementation candidate; NO public product or predictive signal admission.

## Current measured result
- Official free Cboe Open-Close sample: https://datashop.cboe.com/download/sample/218
- A bounded HTTP download on M2 succeeded. Outer ZIP SHA-256: 445cd9d658dc06028c286e09d4ac4818bd5884d7da8addd7509f3a0fa4840552.
- Nested 2025-03-28 C1 EOD sample is vendor-labeled 20%, NOT market-representative. Source row/underlying coverage statistics reside only in the host-private inventory.
- Exact durable PRIVATE bytes and receipt: /Volumes/Mastermind/.mastermind_private/options_free_trials_20261008/ (0700 root, two 0600 files). NEVER copy source bytes into Git, R2, website, issue, CI log, or Slack.
- OCC public Volume Query verified via one October 7, 2026 SPY request: HTTP 200, eight-column CSV with quantity, underlying, option root, C/F/M account type, C/P right, exchange and dated rows.
- The historical data has NO demonstrated original decision-time availability and cannot populate a prospective signal backtest.

## Operational usage (on M2, INSIDE macro repo root)

    python3 -m scripts.qualify_options_free_samples \
      --private-root /Volumes/Mastermind/.mastermind_private/options_free_trials_20261008 \
      --persist-private

The script reads only that acquisition, validates exact SHA + one historical session and ZIP/CSV schema, and writes one immutable private qualification summary. Safe readback/idempotence checks compare existing bytes. No fresh network access, periodic job, external publication, Signal Commons promotion, GEX change, Prophet rank, alert, recommendation, size or execution authority is added.

## Interpretations and rights
- Cboe: Open/close and buy/sell are participant-side classifications for one exchange and an intentionally partial sample; not dealer inventory, portfolio ownership, hedge motive, nationwide intent or a causal forecast. Standard series are counted separately from nonstandard.
- Cboe source license explicitly restricts raw external redistribution; derived external release needs paid licensing and approval. Treat the free demo as internal evaluation only. Details: https://datashop.cboe.com/cboe-options-open-close-volume-summary .
- OCC public Volume Query does NOT disclose open/close or buy/sell. The account-side C/F/M quantities may show both sides of transactions; NEVER sum them into unique market volume. Official endpoint spec: https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/volume-query-batch-processing .
- OCC website Terms (February 2025) restrict exploiting data for commercial purposes. Until written rights are obtained, **do not activate commercial ingestion, derived display, or redistribution**: https://www.theocc.com/specialpages/legal/terms-and-conditions .
- BOX EOD Open-Close trial is three months for qualifying first-time subscribers; requires direct Market Data Agreement and signed request plus SFTP. Official form: https://boxexchange.com/assets/Open-Close-Data-Report-Request-8.14.2024.pdf . Do not activate an automatically billable subscription without the authorized signer and expiration/discontinuance conditions in writing.
- Before any quantitative comparison: secure a license, ordinary daily venue coverage, same-delta and same-tenor joins, PIT available_at/receiver clocks, product/contract identity, stratified venue share, and independent holdouts. Existing ThetaData trade/quote entitlement was observed in July, but October account/rights state remains unverified. Use existing Macro collectors/storage/consumer owners, not a new lifecycle, scoring or data authority.

## Exact next critical path
1. Verify this branch's source tests and run the offline qualification on M2; reconcile the private artifact hash.
2. Obtain written BOX three-month trial terms, company legal signature, SFTP and pre-expiry cancellation requirements; avoid business/account auto-charge.
3. Reconfirm ThetaData current trade+quote and commercial rights through incumbent authorized collector owner; do not duplicate the live poller.
4. Only once rights and event availability are proven, integrate a classified volume source via the existing Options Intelligence admission seam, keeping coverage and nulls truthful.


## Second public demonstration asset: Cboe C1 TBT, 3% sample
- Official URL: https://datashop.cboe.com/download/sample/289 . Cboe TBT execution sample dated 2025-03-28; not a usable current exchange feed.
- Source is 3,807,739 byte outer ZIP; raw SHA256 6c99e69e43d259e81bc31334574579cf9c623f5e77ff596cacf268712cd3262c.
- M2 private source and receipt: same existing 0700 root, files cboe_c1_tbt_public_eval_2025-03-28_outer.zip and cboe_tbt_receipt.json (both 0600).
- Inner CSV contains published participant-side execution fields. The row/underlying counts reside only in the host-private inventory. The packaged sample references TBT specification v1.0; online current official spec v1.1 must be qualified separately before any real feed adapter.
- Qualification script: python3 -m scripts.qualify_options_free_tbt --private-root /Volumes/Mastermind/.mastermind_private/options_free_trials_20261008 --persist-private
- Parsed private research result: qualified_cboe_c1_tbt_sample.json, 0600, SHA256 c8622403caea9f2cbc428b23e2ebe039a2472de16b47c9302099447adb50496d.
- Real-source classification and missing-field census is retained in the private inventory. Categories of exclusions overlap. There is no market-wide denominator; quote-price presence does NOT establish quote-age eligibility because original independent NBBO event timestamps are unavailable.
- The source includes complex-execution IDs, but package membership and complete economic interpretation are NOT established. Rows with field-level classifications are not automatically trade-condition, correction, clock, or prospective-admission eligible.
- TBT stores participant SIDE, not observed aggressor. Execution IDs can connect opposite sides, which must not be counted as separate unique executions without validated deduplication.
- TBT historical original availability clock, network receiver clock, independent NBBO quote time, delta, matured forward-response labels, capacity rights and venue-wide sample completeness remain unknown. Keep them explicit null/false. Preserve raw private bytes for future licensed, fixed-rule assessment; do NOT auto-publish, score or trade.

Verification: 16 hermetic synthetic tests passed on M2 after the real-sample unknown-option-right repair, and both sample qualification scripts were executed successfully. This proves local schema handling only, not production or signal validity.


## Storage cutover and private research discovery — 2026-10-08 (verified)

**Physical custody has changed**: the original 28 files (9,082,019 bytes) were copied with per-file SHA-256 to the exact mounted external **4.0 TB** APFS volume \`/Volumes/Mastermind\` (UUID \`7EE5D196-8BB6-4E6D-B1D7-AFEA5DEB172A\`), verified, and then removed from the internal SSD. The legacy internal directory is now only a filesystem symlink to the external location. The filesystem device IDs differed and the actual external target verified; no raw dataset is retained under the internal home path. Copy receipt \`external_storage_receipt.json\` SHA-256 \`63bc58b58c6ff7a81f36eb735b4c3394e0dd9e6860c915d25ebd2aeae7fe16bd\`; immutable cutover receipt \`cutover_receipt.json\` SHA-256 \`4b52d66f5d8e3f439431b299d6318c1fa649087dff30b35d55d2ee334b9b89dd\`.

**External volume is APFS but not encrypted.** Folder mode \`0700\`, primary source/evidence/metadata files \`0600\`; do not treat this as equivalent to full-disk encryption or a commercial exchange data-security attestation. No credentials, private trading accounts or live market-feed secrets were migrated.

The sample qualifier now pins exact mount path, UUID and 4 TB size, requires a filesystem distinct from \`/\`, and denies any internal-SSD fallback. Even the legacy path alias resolves to this external target; unplugging the disk means the qualifiers refuse service rather than create new data on the SSD.

Research-only machine-readable access inventory (on the external drive):
\`private_research_source_inventory.json\` SHA-256 \`0623f0ea71e26c851508e1c2b5ffcb639d7c59a1638b0fbbdb1c04ac1d5f4702\` (mode \`0600\`). Rebuild/check via:

    python3 -B -m scripts.options_free_source_inventory \
      --private-root /Volumes/Mastermind/.mastermind_private/options_free_trials_20261008 \
      --persist-private

The operation validates mount, acquisition/source/qualification SHA lineage and immutable cutover evidence; it emits **only** a small status line. The full internal inventory is not committed or mirrored to any external publication. It explicitly records the entitlement/rights state for OCC, BOX and ThetaData as unactivated or unknown, not qualified.

### Which options uses are allowed now?

1. **Immediate internal research and implementation calibration**: validate normalizers against actual Cboe C1 opening/closing, participant-capacity, complex-execution and unknown-condition shapes; hold source/sample/denominator identity and separate observation from inferred trade aggressor. Connect this *offline* through existing Macro options research and source-admission references, not a new pipeline.
2. **Coverage and feasibility assessment**: the historical EOD vendor-labeled 20% sample and independent TBT vendor-labeled 3% sample are held privately. Exact row counts and classification coverage reside only on M2's offline inventory. These are *not* equal-universe panels; never join totals or turn absent sampled rows into zero actual options activity.
3. **Tech versus defensives research design**: an illustrative, noncanonical ETF sample census on the external disk shows strongly uneven sampled technology-versus-defensives coverage; exact sector/symbol counts remain private. This does NOT support a current sector rotation verdict: single March 2025 partial day, highly uneven sample support, no original quote age, no underlying-time-aligned delta, no matched tenor/delta population, no prospective labels.
4. **Not authorized**: no Prophet/Opportunity rank or veto, no Macro GEX inventory inference, no live flow or user Terminal display, no public API, no training/backtest label from a reconstructed 2025 decision-time snapshot, no paid/free-trial enrollment, no product redistribution.

Future licensed Cboe/BOX observations must enter the existing **Advanced Data Options** settled-coverage owner; qualified live tape remains with **Intraday Flow**, and forward predictive evaluation remains with **Options Alpha** under C0. Exact event/receiver/availability clocks, correction conditions, venue denominator and standard/multiplier rights must be accepted before the upstream source can cross into the current consumers. Independent predictive holdout is a later and separate promotion gate.

**Verification**: 28 hermetic parser/storage/inventory unit tests passed on M2 (there were unrelated Pytest warnings from stale global temp cleanup); natural EOD/TBT re-qualification succeeded from the 4 TB volume; the private machine-readable inventory was created and hash-verified. Full PR CI and product release remain separate.
