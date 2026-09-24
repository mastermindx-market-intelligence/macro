# Finance R10B — historical market and valuation measurement

Research batch: 2026-09-23. Observation clock: 2026-09-24 UTC.
Operation: `gmi-finance-sector-research-20260923-sol-001`.
Carrier: Macro PR #7786 / `sol/finance-sector-research-20260923`.
Research parent: `acedb9912a62aa5d2d61362af7fcb8f1b3196795`.
Protected procedure: `Mastermind@4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, Skillpack 1.0.1/bootstrap 1.
State: research measurements, not source admission, production implementation, basket membership, ranking, trading, causal identification or final Fable handoff. Mission incomplete. Direct principal reason: PRINCIPAL_JUDGMENT.

## 1. New result and interpretation boundary

This is a new market-data and valuation measurement exercise. It is not publication of the separately refused R10A operating-findings report, which remains held.

Four previously unmaterialized historical price paths are now measured from incumbent stores. Two issuers have source-backed, contemporaneously available accounting-denominator decompositions. These close a measurement gap, not the causal or predictive-evaluation gate.

Retain the twelve original case IDs and windows. The R10 event-clock/retrospective-design amendment remains controlling. The sample is purposive and retrospective. Original causal outcomes remain UNMEASURED; the additional market state is MEASURED_DESCRIPTIVE_RESEARCH_CANDIDATE. No backtest performance, trading strategy or investment recommendation is asserted.

## 2. Incumbent coverage and source identity

Read-only host checkout: `20c950b081773cd5ecc04815275c28b32e49b879`. This is a data-inspection revision, not the Finance PR head or a production release.

| Input | Coverage inspected | SHA-256 |
|---|---|---|
| `data/intl_search/closes.parquet` | 1,365 rows x 994 columns; 2021-06-15 to 2026-09-04 | `aaa54dea16163214e713131b584a7ee3b828b9079051c2c2e2ff9b1f4f2afae4` |
| `data/hk_stocks/0388.HK.parquet` | 6,380 rows; 2000-06-27 to 2026-09-04 | `dc69db5f993554ee2cc543cdf617c24e363ba221f0fa9cb350b63d3d275d70a9` |
| `data/leader_radar/revisions_history.parquet` | 12,221 rows; asof 2026-06-16 to 2026-09-06; zero rows for the four witnesses/checked aliases | `4e0bf6b63f98db1d8e9568012ab4c93e5d9e60cf29338b45c8658ec428451b44` |
| `collectors/intl_universe.py` | inspected `auto_adjust=True` at line 211 | `97cc2af2f9ec562677b4bf5086ea6f0880ee101129ad0835e99402e7829f87ff` |

The revisions archive inspected cannot provide 2022/2024 consensus for these witnesses. This is not proof that every company entitlement or every other historical source lacks coverage. Current recommendations, management targets and analyst-name lists are not historical aggregate consensus.

The international metadata currently labels PAYTM.NS as `One Communications Ltd`. Preserve the source-native label and require legal-issuer/security resolution before admission; do not silently treat a label as validated identity.

No source checkout, collector, dataset or production store was edited. The three data-file hashes were rechecked unchanged after analysis. Temporary source-table renderings were made outside the checkout for visual verification.

## 3. Measurement convention

Let A be the vendor-adjusted close. Offset 0 is the anchor-date observation; offset k is the kth non-null price observation after it. Main return is `A[k]/A[-1]-1`; alternate return from anchor close is retained in the analytical receipt. Thus the main [0,k] interval includes the anchor-day return. No price was forward filled.

Observed dates are not an independently certified exchange-calendar reconstruction. Exact endpoint dates are supplied; 252 observations is not exactly one calendar year. Tokyo March 20, 2024 and Hong Kong July 1, 2022 are absent from the corresponding observed series. Further formal calendar reconciliation remains open.

Adjusted-close performance is not nominal quote-price appreciation. Do not divide dividend-adjusted historical prices by unadjusted accounting EPS/book per share to infer historical valuation, and do not add dividends again to adjusted-close returns.

Current vendor history can incorporate subsequent corporate actions. A fresh comparison with the same vendor tests cache consistency, not independent-vendor correctness or the vintage of the data that existed at the historical date.

## 4. Measured return paths

Percent change in the cached adjusted-close proxy from the prior observed close:

| Witness | Event anchor | Prior close date | Offset 0 | +5 | +20 | +60 | +120 | +252 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| ING, INGA.AS | 2022-07-21 | 2022-07-20 | 0.03 | 1.53 | 2.92 | 0.80 | 36.73 | 48.78 |
| MUFG, 8306.T | 2024-03-19 | 2024-03-18 | -0.39 | 2.45 | -1.39 | 2.05 | -5.68 | 36.45 |
| HKEX, 0388.HK | 2022-07-04 | 2022-06-30 | -3.11 | -5.08 | -6.11 | -26.46 | -14.16 | -24.22 |
| One97/Paytm, PAYTM.NS | 2024-01-31 | 2024-01-30 | 0.01 | -34.80 | -46.63 | -51.10 | -34.71 | 5.51 |

The +252 endpoints are respectively 2023-07-14, 2025-04-01, 2023-07-11 and 2025-02-05. The complete 28 dated endpoints and both return conventions are in the research receipt and CSV.

Paytm's January 31 close barely changed; February 1 fell about 19.99% from January 31. Exact first-public-release time remains unverified here. Preserve the frozen January 31 anchor and distinguish the first subsequent observation; do not silently rewrite the event clock.

### Path risk is not the terminal return

| Witness | Lowest value relative to starting close | Date | Maximum peak-to-trough drawdown within window |
|---|---:|---|---:|
| ING | -5.66% | 2022-09-05 | -23.08% |
| MUFG | -17.71% | 2024-08-05 | -31.85% |
| HKEX | -45.27% | 2022-10-31 | -45.27% |
| Paytm | -58.33% | 2024-05-08 | -58.34% |

These are observed passive price-path descriptions, not a feasible entry/exit strategy or a prediction. A favourable terminal endpoint does not erase an intervening loss or establish investability.

## 5. Quote prices and adjustment effects

Separate quote-price endpoints from adjusted-close performance:

| Witness | Quote start | Quote end | Quote-price change | Adjusted-close change |
|---|---:|---:|---:|---:|
| ING, EUR | 9.1750 | 12.8660 | 40.23% | 48.78% |
| MUFG, JPY | 1,533.5 | 1,994.0 | 30.03% | 36.45% |
| HKEX, HKD | 386.0 | 286.2 | -25.85% | -24.22% |
| Paytm, INR | 761.10 | 803.00 | 5.51% | 5.51% |

Ordinary historical quote closes and separate adjusted-close series were read through the incumbent vendor's standard chart endpoint. No within-window splits were returned. Cash distributions, entitlement, payment dates, taxes and reinvestment still need separate treatment for an accepted investor-level return.

A concrete information-set trap: the current MUFG dividend history assigns the eventual JPY39 final dividend to the March 28, 2025 ex-date, while the February 12 disclosure still forecast JPY35 final. The eventual amount is not evidence that JPY39 was known at the earlier forecast date or paid in cash by April 1.

Fresh vendor versus cache normalized-level differences were below 0.004 basis points for all four series in the inspected overlap. The tolerance checked was 0.01 basis points. This establishes same-provider consistency only.

## 6. MUFG: a measurable price-to-book expansion

The valuation measure is price divided by the latest disclosed JGAAP common accounting book per share, including other comprehensive income. It is not tangible book, regulatory capital, normalized equity or estimated intrinsic value.

Pre-event source: February 5, 2024 report, book as of December 31, 2023. Post-window source: February 12, 2025 version, book as of December 31, 2024. The latter says the February 4 numbers were unchanged. Both document versions predate their paired quote-price endpoints.

| Input | Before | After |
|---|---:|---:|
| Common equity, JPY millions | 18,888,090 | 20,381,805 |
| Issued shares | 12,337,710,920 | 12,067,710,920 |
| Treasury shares | 457,337,373 | 467,199,238 |
| Derived shares excluding treasury | 11,880,373,547 | 11,600,511,682 |
| Derived book per share, JPY | 1,589.8566 | 1,756.9747 |
| Quote price, JPY | 1,533.5 | 1,994.0 |
| Price / disclosed book | 0.96455x | 1.13491x |

Book per share increased 10.5115%; the measured multiple increased 17.6613%; quote price increased 30.0293%.

`1.300293 = 1.105115 x 1.176613` within displayed rounding.

This is an accounting valuation decomposition, not proof that the BOJ caused the increase. Book dates lag quote dates, OCI and capital actions remain in the denominator, and accounting comparability is not economically normalized. The path also includes the August 2024 drawdown and later macro/company developments.

## 7. HKEX: denominator choice changes measured compression

Quote price fell 25.8549% from June 30, 2022 to July 11, 2023.

### A. Last reported full-year basic EPS

FY2021 basic EPS was HKD9.91, published February 24, 2022; FY2022 was HKD7.96, published February 23, 2023.

- EPS change: -19.6771%.
- P/E: 38.95055x to 35.95478x.
- Multiple change: -7.6912%.

### B. Rolling reported-EPS proxy

The latest public quarter reports give Q1 2021/2022/2023 basic EPS of 3.03/2.11/2.69. An illustrative rolling sum is:

- Before: `9.91 - 3.03 + 2.11 = 8.99`.
- After: `7.96 - 2.11 + 2.69 = 8.54`.
- EPS-proxy change: -5.0056%.
- P/E proxy: 42.93660x to 33.51288x.
- Multiple-proxy change: -21.9480%.

The reported-EPS sum is a proxy, because reported periods have rounded EPS and potentially different weighted-average share denominators. It is not exact aggregate-earnings TTM EPS, normalized EPS or forward analyst-consensus EPS.

Both definitions identify compression, but they assign very different portions of the same price decline to earnings versus valuation. Therefore every product claim of a rerating must state the denominator, fiscal horizon, publication clock and calculation method.

## 8. Same-currency peer context, not causal controls

Posthoc descriptive peers were drawn from already inspected same-currency series. The calculation is equal-initial-weight buy-and-hold, not a new approved basket and not a market-model alpha estimate.

| Witness | +252 adjusted proxy | Peer proxy | Difference, percentage points | Relative wealth |
|---|---:|---:|---:|---:|
| ING vs BNP/Santander/Deutsche Bank | 48.7843% | 33.5396% | 15.2447 | 11.4159% |
| MUFG vs SMFG/Mizuho | 36.4527% | 40.3011% | -3.8484 | -2.7429% |

These banks share policy treatment and differ in business exposure. They are not untreated controls. Selection occurred after some outcomes were observed. Do not call these differences alpha or a causal ECB/BOJ response. USD country ETFs were not substituted for local-currency market benchmarks.

## 9. Source receipts

MUFG pre-book report, PDF pages 1–2:
https://www.mufg.jp/dam/ir/fs/2023/pdf/summary2312_en.pdf
SHA-256 `48018b628ec1e64bb07aabfdf4a0f0b1a7aeda2933b2dedb269aefdac970a143`.

MUFG post-book report, PDF pages 2–3:
https://www.mufg.jp/dam/ir/fs/2024/pdf/summary2412_en.pdf
SHA-256 `97d90f11674481194e7f5412f2539d01e69cbbc27c6c4059cf5f7ed4eba605d8`.

HKEX FY2021, PDF page 3:
https://www.hkexgroup.com/-/media/HKEX-Group-Site/ssd/Investor-Relations/annouce/documents/2022/220224_final_e.pdf

HKEX FY2022, PDF page 3:
https://www1.hkexnews.hk/listedco/listconews/sehk/2023/0223/2023022300153.pdf

HKEX Q1 2022, PDF page 3:
https://www.hkexgroup.com/-/media/HKEX-Group-Site/ssd/Investor-Relations/annouce/documents/2022/220427_1qtr_e.pdf
SHA-256 `4913d439469bfd25fe969eb7b250664db9c215f08ab1513d85bdbd5d10d9b34e`.

HKEX Q1 2023, PDF page 3:
https://www1.hkexnews.hk/listedco/listconews/sehk/2023/0426/2023042600309.pdf
SHA-256 `31a704830a00701aeda9a0006006d77503c78da26ae1f7dfbbedbeed5da70103`.

The numerical source tables were visually inspected. Where web PDF screenshots failed, remote PDF renderings were inspected without OCR. This is source-table inspection, not application browser proof.

The analytical JSON receipt carries each standard vendor chart URL, response hash, date/currency/timezone and corporate-action limitations. Raw vendor responses were hashed in memory; immutable owner admission/retention is not claimed.

## 10. Verification and product consequences

Twenty-five remote research checks passed: source hashes unchanged, positive/unique observations, cache dates in fresh vendor history, no returned window splits, valuation identities, normalized cache comparison, observed holiday gaps and revision-coverage limits. Twenty-five separate local recalculation/preservation checks passed. These are not fifty independent validations of a thesis, nor production CI or independent review.

The source-derived and locally transcribed numerical projections have identical SHA-256:
`8909d31c0ab41f9744c9e7d572b12fc2321a5d2a63381ce69b59b4e8d0ae206c`.
The projection covers the four ticker/anchor/base records and all 28 dated endpoint adjusted closes. It does not attest byte equality of every source document.

Named product requirements unlocked by these cases:

1. Show quote-price, adjusted-return and valuation basis separately.
2. Pair terminal outcomes with drawdown and the timing of recognition.
3. Print denominator/horizon beside every valuation change.
4. Keep raw appreciation, peer-relative results and causal alpha distinct.
5. Display exact consensus coverage; never fill missing historical consensus with current estimates or guidance.
6. Separate announcement, operative date, first price response, dividend declaration/revision, ex-date and cash payment.
7. Preserve source/native definitions and explicit nulls before accepting a comparison.

## 11. Remaining gates and next bounded work

R10 remains incomplete. The remaining eight event cases, independently reconciled calendars, point-in-time eligible cohorts, local benchmark/factor controls, historical analyst-consensus versions, causal attribution, source rights/retention and canonical issuer/security admission remain open. These measurements do not satisfy those gates by implication.

Next principal research unit: use the corrected event clocks to materialize a bounded capital/regulatory case pair from the remaining cases; fix scope and comparable valuation denominator before inspecting outcome endpoints. Do not restart R1–R9. R11 basket/visualization freeze and the final Fable implementation handoff remain downstream. The separate R10A publication refusal remains held.
