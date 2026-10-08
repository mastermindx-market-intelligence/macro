# Free options source access — implementation and custody (2026-10-08)

Status: private evaluation data ACQUIRED; parser implementation candidate; NO public product or predictive signal admission.

## Current measured result
- Official free Cboe Open-Close sample: https://datashop.cboe.com/download/sample/218
- A bounded HTTP download on M2 succeeded. Outer ZIP SHA-256: 445cd9d658dc06028c286e09d4ac4818bd5884d7da8addd7509f3a0fa4840552.
- Nested 2025-03-28 C1 EOD sample is vendor-labeled 20%, NOT market-representative. CSV: 86 columns; 23,179 rows; 1,553 underlying symbols.
- Exact durable PRIVATE bytes and receipt: /Users/chriswong/.mastermind_private/options_free_trials_20261008/ (0700 root, two 0600 files). NEVER copy source bytes into Git, R2, website, issue, CI log, or Slack.
- OCC public Volume Query verified via one October 7, 2026 SPY request: HTTP 200, eight-column CSV with quantity, underlying, option root, C/F/M account type, C/P right, exchange and dated rows.
- The historical data has NO demonstrated original decision-time availability and cannot populate a prospective signal backtest.

## Operational usage (on M2, INSIDE macro repo root)

    python3 -m scripts.qualify_options_free_samples \
      --private-root /Users/chriswong/.mastermind_private/options_free_trials_20261008 \
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
