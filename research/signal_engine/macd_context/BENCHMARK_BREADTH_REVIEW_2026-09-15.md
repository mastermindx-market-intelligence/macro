# MACD benchmark, breadth and comparison review

Date: 2026-09-15 America/New_York; execution receipts cross into September 16 UTC.
State: **PARTIAL research; exposed development evidence; zero production authority.**

## Mission and ruling

Chairman identified a potential cap-weight/equal-weight divergence: SPY can remain resilient while the broader constituent population deteriorates. The research must distinguish benchmark suitability, contemporaneous market state, actual capital flows and predictive correction risk. They are not the same claim.

Keep SPY as the broad large-cap opportunity-cost reference, but not the sole market-health or stock-selection yardstick. Add disclosed equal-weight, size/style and appropriate sector/peer comparisons without choosing whichever benchmark makes a signal look best. Preserve the existing SPY-defined hit field and frozen outcomes; no silent relabelling is authorized.

The benchmark overlay completed on all 126,440 original crossover events without recomputing stock returns. All five comparators are available for every originally matured observation: 125,708 at 21 sessions and 124,197 at 63 sessions. A separate previously declared 48-row input/memory uncertainty analysis also completed. Neither result is a new untouched holdout, an actual Prophet-admission replay, or an accepted trading policy.

## Source identity and freshness

Protected Skillpack: Mastermind@7642aea155d2817219135b24246b55c1d7611c66, compatible schema1/version1.0.1/bootstrap1. Macro source-review pin: 7c3b2e19c0bffe8aca9a7bfa91e610c1ca3b7149. Existing publication carrier remains draft PR7177 / sol/macd-cycle-research-20260915-c3. Research operation remains macd-context-cycle-attribution-20260915-c3, on the same Remote Desktop Commander/Mac Studio device3f5ce987-e3eb-40a3-af9f-4b0ae54919cc. No worker, watcher or new control plane was created.

Local historical ETF caches: SPY/RSP/IWM/QQQ end September4,2026; MDY ends August26,2026. The numerical research below cuts all benchmark outcomes at December31,2025, matching the original equity sample. The caches therefore do NOT verify the user's September15 current-chart observation. Public primary sources verify the index construction, not the specific claimed imminent breakdown or mega-cap flow. No fresh, synchronized current SPY/RSP technical-state calculation or flow measurement was completed here.

## 1. What the index difference can and cannot establish

State Street identifies SPY's benchmark as float-adjusted market-cap weighted. S&P identifies its equal-weight index as using the same S&P500 constituents, assigning each company equal weight at quarterly rebalances; RSP is a listed linked product. Actual weights drift between rebalances. RSP is not an equal-weight portfolio of the entire U.S. market, a small-cap index, or a direct count of advancing stocks.

For a common one-period constituent set, before expenses and tracking effects:

`R_cap - R_equal = sum_i [(w_cap,i - w_equal,i) * r_i]`.

Thus aggregate cap-weight performance and average constituent experience can diverge mechanically. The difference can reflect sector allocation as well as concentration within sectors. A weak RSP/SPY ratio can arise when both rise but SPY rises faster, when RSP falls while SPY rises, or when both fall at different speeds. Absolute and relative states must both be retained.

Prices alone do not establish net fund flows. ICI distinguishes ETF primary-market creations/redemptions from secondary trading in existing shares. Shares-outstanding/NAV and actual creation/redemption data can support flow claims; a rising index or relative-price ratio cannot substitute for those observations. Even observed ETF flows would not, by themselves, prove the cause of an ensuing correction.

## 2. Five-benchmark measurement contract

Declared before the new outcome overlay: SPY, RSP, MDY, IWM and QQQ. They are diagnostic comparators, not five equally appropriate mandatory benchmarks for every stock. Entry and exit are each original event's exact next-session-close entry and 21/63-session endpoint. Use adjusted `close`, never raw `close_price`; missing exact endpoints remain unknown, never forward-filled. SPY is taken from the original frozen snapshot to preserve the original definition.

All five benchmarks share the same matured denominator. Original SPY excess is reproduced at rtol0/atol1e-10. All original-event inputs and output digests were verified. Original stock signals and stock returns were not rerun or changed.

### All 3D bullish crosses, 21-session outcomes

| Indicator | n | Positive stock return | Beat SPY | Beat RSP | Beat MDY | Beat IWM | Beat QQQ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Price MACD12/26/9 | 12,469 | 60.77% | 51.88% | 52.55% | 52.72% | 52.91% | 49.01% |
| Incumbent RSI-MACD | 15,122 | 59.61% | 51.71% | 52.69% | 52.82% | 52.65% | 48.34% |

Across all original events, SPY versus RSP changes the beat-benchmark label on **6.6145%** of matured21-session observations and **6.2932%** at63sessions. Aggregate hit-rate changes are smaller because changes occur in both directions. This is a measurement difference, not an improvement in realized profits.

For identical entries and exits:

`excess_RSP = excess_SPY + return_SPY - return_RSP`.

For two stocks on those same dates, subtracting a common benchmark leaves their return difference and rank unchanged. Changing the benchmark can alter the threshold hit and pooled cross-date comparisons, but it cannot manufacture same-date stock-selection skill. Beta-adjusted or stock-specific peer comparisons are different estimands and must be named explicitly.

### The original selected repair context remains much less impressive as a relative hit

The old repair predicate combines stock3D deep-negative state, completed weekly stock histogram negative but easing, and SPY below its200-session average. It is NOT a validated market-regime-transition detector.

| Price-MACD repair observation,21sessions | n | Positive stock return | Beat SPY | Beat RSP | Mean gross return | Mean SPY excess | Mean RSP excess |
|---|---:|---:|---:|---:|---:|---:|---:|
| Crossover | 636 | 75.79% | 59.28% | 58.02% | 6.05% | 2.10% | 1.73% |
| Same coarse repair context, no cross | 5,224 | 72.47% | 58.56% | 57.47% | 6.11% | 2.17% | 1.84% |

Changing from SPY to RSP does not rescue an incremental mean-return advantage for the price crossover in this pooled comparison. The non-cross observations are repeated context dates, not independently matched alternative trades. The same-date/risk/sector/episode limitations from the prior attribution remain.

## 3. Breadth disagreement has to be defined at a particular horizon

Two simple state families were fixed before this overlay. These states are explanatory research strata, not new live gates. All state inputs are known at the signal close, and warmup/missing prices remain unknown.

- **Trailing21-session direction:** signs of SPY and RSP returns. Code treats an exactly flat return as nonnegative.
- **200-session location:** each ETF compared to its own trailing200-session average, with equality treated as above/nonnegative.

### All 3D crosses, subsequent21-session outcomes

| Context at signal close | Price-MACD n / dates | Price positive rate | RSI-MACD n / dates | RSI positive rate |
|---|---:|---:|---:|---:|
| Both SPY/RSP nonnegative over prior21sessions | 9,188 / 827 | 59.81% | 10,461 / 828 | 58.83% |
| SPY nonnegative, RSP negative over prior21sessions | 692 / 79 | 58.24% | 847 / 78 | 53.72% |
| Both SPY/RSP at or above own200-session average | 9,751 / 1,025 | 58.60% | 11,824 / 1,037 | 58.10% |
| SPY at/above own200 average, RSP below its own | 425 / 53 | 64.94% | 555 / 53 | 65.95% |

In the trailing21 divergence state, incumbent RSI-MACD beats SPY on46.99% and RSP on47.46% of observations; mean excess is approximately-0.055 and-0.018 percentage points. This is directionally consistent with a less favorable short-swing environment, but the comparison is not risk-matched, independent-episode tested or multiplicity-adjusted.

The200-average split gives a different apparent result. A broad label such as 'weak breadth' would conceal this distinction. Do not pick the more attractive definition after seeing results or turn either row into a hard gate. The indicators, states and horizons are correlated descriptions of shared history.

Historical market-date census2010–2025: SPY at/above200 and RSP below200 occurs on161 of4,024 sessions; SPY nonnegative/RSP negative over prior21 occurs on228 sessions. These are dates, not independent episodes. The experiment did NOT label subsequent index corrections, drawdown hazards or market tops. Therefore it does not establish that either condition predicts an imminent correction.

## 4. The previously blocked input/memory uncertainty analysis now completed

The exact unfinished output/CLI append succeeded through the same native carrier. No permission, provider, device, encoding or authentication workaround was used. The frozen four contrasts, two depth predicates, two horizons and three outcomes were retained:48rows. No original equity replay was repeated.

Joint calendar-year bootstrap uses5,000 draws across2010–2025. Intervals are pointwise descriptive intervals on exposed research, NOT adjusted across the research family. Shared-date comparisons equal-weight only dates where both arms have observations; they do not match tickers, risks or complete opportunity sets. A zero-containing interval does not prove equivalence.

### Own-indicator deep-negative state,21-session positive-rate differences

| A minus B | Pooled difference | Descriptive95% interval | Shared dates | Shared-date difference | Shared-date95% interval |
|---|---:|---|---:|---:|---|
| Price-fast3D minus RSI-fast3D | +9.01pp | [+2.48,+15.98]pp |333| +3.06pp |[-1.32,+7.66]pp |
| Price-slow3D minus RSI-slow3D | +4.00pp |[-1.88,+9.50]pp |354| +2.33pp |[-3.44,+8.41]pp |
| Price3D minus memory-matched price2D | +1.87pp |[-0.65,+4.11]pp |152| +0.93pp |[-2.62,+4.66]pp |
| RSI3D minus memory-matched RSI2D | +0.38pp |[-0.85,+1.51]pp |341| +1.19pp |[-1.28,+4.04]pp |

Do not hide the different answer under the common-price-state comparison: fast-price3D versus fast-RSI3D has a shared-date positive-rate difference of+4.42pp, interval[+0.72,+9.16]pp over304dates. Its shared-date mean-return difference is+0.442pp, interval[-0.339,+1.446]pp. Thus some sign-frequency evidence is positive while incremental payoff remains uncertain.

Other declared alternatives matter too. At63sessions in own-indicator depth, price3D minus memory-matched2D has a shared-date positive difference of-3.31pp, interval[-6.43,-0.60]pp, and mean-return difference-1.108pp, interval[-2.234,-0.043]pp. In common-price-depth at21sessions, RSI3D minus memory-matched2D has positive shared-date sign and mean-return intervals while its pooled sign interval includes zero. These are not grounds to switch champions between cells. They show why a headline-only superiority claim is not robust to population, horizon and weighting definitions. All48rows remain in the result artifact, including unfavorable and null alternatives.

## 5. What should change in the next scientific and product contract

**Benchmark:** retain absolute/net profitability and SPY opportunity cost; add RSP constituent-breadth comparison, an economically appropriate preassigned sector/size/style peer, and the incumbent policy on the same opportunity when available. A benchmark cannot be selected retrospectively per name or result. Existing `hit=excess_spy>0` remains unchanged; new benchmark semantics need explicit identifiers under existing owners.

**Context:** preserve absolute market trend, cap/equal relative participation, constituent-count breadth, sector dispersion and source freshness separately. The same-name index spread should be decomposed into sector-weight and within-sector contributions before attributing it purely to mega-cap crowding. Historical constituents, weights and sectors must be point-in-time, not today's membership reconstructed backward.

**Mechanism:** distinguish a persistent narrow advance, a countertrend repair, and a state change that subsequently fails. Direct flow evidence is separate from price leadership. Any correction-prediction test must declare its index, drawdown threshold, horizon and event onset before outcomes, retain false alarms and broadening-without-correction alternatives, and use episode-level chronological validation.

**MACD integration:** compare context-only, trigger-only, combined context/trigger and actual early/confirmed trade policies. Keep signals that never receive later confirmation. New-entry timing, structural holding and portfolio risk remain separate jobs; multiple correlated index/indicator confirmations are not independent votes.

**Existing owners:** `engine/etf_pulse.py` already defines display-only RSP/SPY, IWM/SPY and other ratios at1/5/20/60sessions. Its source explicitly disclaims forward authority; `engine.sectors.rs_table` owns the reused sector-relative-strength context. This is code evidence, not a fresh browser/production proof. Extend accepted consumers only after appropriate validation; do not build another breadth score, flow plane, event store, grader or publication authority.

The intended customer experience is a concise explanation of cap-weight support, breadth deterioration/recovery, the candidate's own evidence and supported horizon. A numerical crash probability or hero buy/sell gate is not authorized by these results.

## 6. Reproducibility, tests and current limitations

Root: `/Volumes/Mastermind/Mastermind/artifacts/macd-context-first-look-20260915-c3/cycle_extension_v2/`.

- Benchmark declaration: `BENCHMARK_AMENDMENT_20260915.md`, SHA2562a91976a92d1a36e25f05db5a1423a2543ab2cac99b315bb7d310935b62b5340.
- Measured overlay source: `benchmark_overlay.py`, SHA256aa5ea72082e34270f36fa0021547ec213669dbfb140e8824fa07fa486f5ca60f.
- Overlay evidence: `benchmark_overlay_20260915_r1/receipt.json`, PASS_EXPLORATORY_BENCHMARK_OVERLAY; process4675 exited0. Eight summary tables contain213rows including coverage/census; they are not213 independent tests. Exact benchmark closes are frozen in that directory and remain on the authorized host.
- Core endpoint/identity tests were observed RED before implementation, then GREEN. Additional state tests cover warmup unknowns, future-prefix invariance and missing-current-price unknowns. Process20594 exited0 with2+3tests passing.
- Completed contrast source: `review_comparisons.py`, SHA256f9ab78c77703b83704974df57d012fb270f846fcebaae38875ce3628055eda23.
- Contrast evidence: `comparison_review_20260915_r1/receipt.json`; PASS_DESCRIPTIVE_CONTRASTS_ONLY; process48135 exited0, two synthetic tests passed,48contrasts. CSV SHA256983414d0c7a9a718d73ba733dd127d1d32a0c5986aa43fddd3f54d1b0fcc3b9d.
- Original126440-event file hash9db1b4f87dda46f177906fcb979e297cbccdd0cbf415f16c67ea4c215ee5f62c remains unchanged. Expanded replay input hash69bd2215ddeece7711625387c1cfd4a5baa4cc59d09df6b4658726b255f5e203 matches its original receipt.
- Additional source dependencies, verified on inspection: original calendar SHA2560e5ee68204bb25fda56aa3371266313c484178f4638ee8ecaa910c287eb35cdf; original repair observations SHA2561c284e1a50bd922905333be65cb40ccb07d01d551d1c1886fe9ca60892901d07. The overlay receipt's input map did not list these two dependencies; this explicit supplement preserves them rather than silently rewriting the completed receipt.

Current-universe survivorship, retrospective adjustments, overlapping observations, close-only execution, selected contexts and repeated research looks remain. No new independent holdout, prospective validation, stock-specific causal edge or production proof is claimed. The prior current-Prophet-frame qualification and canonical TrialLedger application remain unfinished; these completed diagnostics do not bypass either.

The old6,235-cell accounting proposal is now stale as an inventory of generated views: this turn adds213overlay rows and48contrast rows, bringing the mechanically counted total to6,496. This is NOT a certified independent-test count or automatically accepted budget. The existing TrialLedger owner must adjudicate the family, full historical exposure and appropriate accounting; the old patch was not applied or represented as complete. No new ledger was created.

## Primary external sources

- State Street SPY fund page, benchmark description: https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy
- S&P500 Equal Weight Index description and linked products: https://www.spglobal.com/spdji/en/indices/equity/sp-500-equal-weight-index/
- Investment Company Institute, ETF Basics and Structure FAQs, primary versus secondary market activity: https://www.ici.org/faqs/faqs_etfs

## Exact next action

Qualify the actual point-in-time Prophet candidate/version frame and preassigned benchmark/context joins under the existing label, snapshot, sector and breadth owners; reconcile all exposed looks under TrialLedger and obtain independent source/scientific review before a promotion-bearing matched-opportunity test. The benchmark and48-contrast runs are complete and should not be rerun without a material invalidator. No live trade, rank, availability, size, plan, or hero probability was modified.
