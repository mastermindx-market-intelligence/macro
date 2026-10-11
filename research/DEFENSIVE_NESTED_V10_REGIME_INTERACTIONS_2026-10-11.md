# Defensive nested washouts V10 — regime interactions and issuer counterexamples

**October 11, 2026. MISSION_COMPLETE: false.** Source-grounded research assessment and a proposed narrower experiment are complete. The exact real-stock W+2W StochRSI / lower native RSI-MACD strategy remains unvalidated. No new equity-price backtest, synthetic performance run, live classification, allocation, trade, alert, deployment or production-code change.

## Mission, authority and effects

Current continuation follows the Chairman's question about regime dependence and user-selected Pro mode. Preserve the original method: weekly/two-week StochRSI washout followed by shorter RSI-MACD bullish recovery, not the earlier price-MACD proxy. User chart species and candle phase remain unresolved; 14/60/5-on-RSI and 12/26/9-on-RSI must be selected by chart parity, not their returns.

Protected Mastermind master was freshly resolved to `11e8c7d930bdf3f98d20b76a42477f427b8cac20`; compatible INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and CLOSEOUT were read from that commit. Relevant source/report reads were pinned to macro `f191b7f1bd5eb11f6fe99a6426ce9789f8f6ad8f`. Research branch predecessor was reverified immediately before writing at `f61f7f399f1c82cc833037ef89d0d095ace69634`.

Direct source adjudication and economic synthesis were retained as PRINCIPAL_JUDGMENT. No child was dispatched. Previous V3 result-read and V4 compound raw-equity acquisition denials remain in place: no retry, rephrasing, replacement acquisition/export, alternate carrier, or equivalent blocked computation. Public issuer disclosures and separately available existing repository reports were read; no raw historical price dataset was accessed. Pro selection is not permission or served-model proof.

## 1. Main change: condition on repair, not merely bull/bear labels

A slow washout can coincide with high but improving stress, low but worsening stress, an intact business or continuing impairment. These are not interchangeable. The proposed question is whether the same observable technical entry has better outcomes when incremental economic/market damage is diminishing. A future bull market must not be backdated as the entry's regime.

Withdraw the earlier generic suggestion that bear-market entries necessarily need tighter stops. Stop distance, position size, intended risk budget and predictive edge are distinct. A wider stop at the same capital exposure changes risk; a fixed intended stop-loss budget implies a different position size. No optimal stop is inferred. Likewise, low volatility, above-200SMA status, positive traffic, or positive slow momentum should not be universal prerequisite gates for an early reversal.

The existing July higher-timeframe adjudication already reports failed calm-base and hard-context gates. These are evidence about those exact tests, not universal laws. Daniel/Moskowitz's Momentum Crashes abstract concerns a different cross-sectional strategy but supplies contrary context to a blanket high-volatility veto: panic states can accompany large reversals. It does not validate this nested long-only method.

## 2. Existing cohort evidence — retain its exact limits

`research/entry_timing/WAVE2_REPORT.md` describes a related 2D RSI-MACD / 3D StochRSI trigger and sector washout condition, not the requested W+2W construction. Its reported cohort versus other-washout clean15 rates are 38.70% vs 31.16%, with close-based stop5 rates 40.22% vs 45.86%.

The reported stock-panel fold spreads are:

| Period | Clean15 cohort-minus-other spread | Stop5 spread |
|---|---:|---:|
| 2012-01 to 2015-03 | -2.76pp | +2.53pp |
| 2015-08 to 2017-12 | +13.96pp | -9.30pp |
| 2018-06 to 2020-09 | +12.25pp | -8.49pp |
| 2021-03 to 2023-05 | +8.70pp | -10.34pp |
| 2023-11 to 2025-12 | +8.75pp | -6.55pp |

These windows are not identified causal regimes. The first negative fold prevents a constant pooled-effect interpretation. Reported durable-bottom recall is 59.71% for all trigger fires versus 7.35% for the cohort subset: a compulsory cohort gate would remove about 87.7% of that original recall. Better selected outcomes are not enough when missed winners grow.

Reported event counts include overlapping horizons/common shocks and current-membership bias. Same-universe comparisons do not guarantee survivor bias cancels, nor does a close-based barrier error necessarily affect both groups equally. No new p-value, account return or claim of replication is supplied here.

## 3. Failed-fire effect changes with context; new source-report discrepancy

`research/species/W1_S6_REPORT.md` reports the following for its m2d_s3d variant:

| Population | Repeated-failure stop5 | No-repeated-failure stop5 | Difference |
|---|---:|---:|---:|
| Within sector-cohort washout | 35.66% | 40.58% | -4.92pp |
| All fires, including that subset | 45.97% | 43.52% | +2.45pp |

The second row is not the non-cohort complement. Do not infer a clean inside/outside experiment from it. It still shows the reported conditional/unconditional association can have opposite signs. The original report kept the effect below promotion status and disclosed thin per-name majorities and survivorship issues.

**New source audit:** the report describes 180 calendar days, but `research/entry_timing/wave1.py` sets `H5_FAILED_WINDOW = 180` (lines90–94) and uses `lag = i - fill_idx` (lines721–735), which is 180 data bars. The code does require `resolution_idx < i`, preventing a not-yet-realized failure from being counted. The window-unit discrepancy is not repaired. The actual historical executable revision needs reconciliation before assigning precise reproduction status to the report.

Repeated-failure context is not unlimited retry authority. Every incurred loss remains in the account; risk exhaustion can prohibit another attempt even where a statistical state is interesting.

## 4. Historical issuer counterexamples to universal regime rules

Official dated examples constrain the proposed filters; none establishes stock-entry performance:

- **WMT, August18 2020:** US comparable sales +9.3%, transactions -14.0%, average ticket +27.0%. A universal positive-traffic gate would misread the business environment. **July25 2022:** higher food/consumables mix and markdowns harmed profit expectations despite stronger comparable sales. Recurring cash consequences, not one demand metric, matter.
- **MCD, July28 2020:** global quarterly comps -23.9%, while US monthly declines narrowed from -19.2% in April to -5.1% in May and -2.3% in June. Weak level and improving trajectory differ. Those figures are not entry-date facts before their source publication without earlier evidence. **October27 2022:** pricing and positive US guest counts coexisted with currency effects in reported results.
- **WM, July30 2020:** company volumes -10.3%; essential operations did not mean invariant economic demand. **January31 2023 report of 2022:** collection/disposal pricing and efficiencies offset inflation, while recycling commodity exposure differed. The 2022 year-end figures were not available to early-2022 entries.
- **COST, September22 2022:** Q4 reported comps +13.7% versus +10.4% excluding gas/FX. Normalize operating data; intact economics still do not prove valuation safety.
- **PG, October19 2022:** organic sales +7% included roughly +9% pricing/+1% mix and -3% shipment volume. Demand, effective costs and currency require separate interpretation; macro support does not repair unresolved exit-policy evidence.

Rates need at least real-yield/credit direction and issuer exposure. Falling yields with widening credit can mean deteriorating growth, unlike benign discount relief. Rising yields alongside better earning power can differ from pure valuation pressure. New York Fed term premia are model estimates; expected-short-rate/term-premium and real-yield/inflation decompositions are different lenses, not additive independent signals.

## 5. Proposed focused experiment, not a new control plane

Keep fixed master washout episodes and compare:

1. Shared peer washout × observable repair.
2. Real-yield pressure × valuation/earning-power vulnerability.
3. Stress level × stress direction.
4. Source-known issuer deterioration × technical recovery.

No weighted confidence score or allocation is generated. Separate gate-the-same-first-cross from wait-for-first-eligible-cross. Preserve rejected and incomplete episodes. Compare entry-only filtering, exit-only adaptation and their combination separately; otherwise a good joint result cannot be attributed to entry quality.

Use fixed-endpoint incremental outcomes against arm-immediate entry and report actual single-position account paths alongside event statistics. Compare cash, stock holding and relevant market/sector exposure. Keep fast lower exits, completed weekly exits and fresh post-entry slow-cycle completion as distinct hypotheses. Stops/gaps, maximum holding and bounded retries are separate risk controls. Neither timeframe nor exit may be selected from the strongest recent result.

Assess gains/losses, adverse excursion, dead money, missed winners, delay, exposure and cluster risk rather than hit rate alone. Regime-dependent score signs are hypotheses; no unique best per-stock settings are established.

Time safeguards: use release-time/vintage macro and issuer information, not latest revised history; do not use final NBER recession labels as real-time entry features. Use filtered rather than future-smoothed latent-state probabilities. Preserve common shock episodes in train/test grouping, horizon-appropriate purging and a genuinely later prospective segment. Recent history has already been examined.

## 6. Delivery and verified frontier

Created a 3,881-word report including sources, an evidence crosswalk, proposed protocol and README. Verified 10 document/metadata consistency checks and arithmetic, JSON structure, ZIP CRC and five manifest-member SHA digests. **These are document checks, not new strategy tests.** No synthetic performance run and no new real-stock backtest occurred.

- Report: `/mnt/data/defensive_regime_v10/REGIME_CONDITIONING_REVIEW.md`, SHA256 `831d3bdbd33302120120f662e9c08a256dbe2bcb07dbf89037175af60c2d7781`.
- Six-member ZIP: `/mnt/data/Defensive_Regime_Interactions_V10_2026-10-11.zip`, SHA256 `6045d83edddacd99cb8b674e542868f2701bdb7cdbe2dfd886ea15ec2f8b0632`.

Before: broad regime suggestions risked becoming unsupported universal gates. After: recovered actual related interaction evidence, identified a source/report window mismatch, used issuer counterexamples to refine covariates, and narrowed the conditional test without changing production rules.

**Remaining:** legitimately permitted native-price replay; actual chart/species parity; timestamped macro/issuer coverage; statistical validation of incremental benefit and portfolio risk. Do not retry the refused V3/V4 operations or obtain their effects through another carrier. Do not promote historical report rates to the new strategy. No worker, watcher, open order, unresolved write or automated return is claimed.

The scoped source/causal assessment is complete. The broader empirical mission is partial and its decisive data-dependent lane remains blocked; no finished-strategy claim is permitted. Preserve this report rather than repeating accepted synthetic/source work without a relevant invalidator.

## Primary references

Repository paths are at macro `f191b7f1bd5eb11f6fe99a6426ce9789f8f6ad8f`:
- `research/entry_timing/WAVE2_REPORT.md` (lines36–105,190–290)
- `research/species/W1_S6_REPORT.md` (lines1–85)
- `research/entry_timing/wave1.py` (lines85–98,701–748)
- `research/signal_engine/HTF_SUPER_TIERS_ADJUDICATION_AND_PREREG.md` (lines14–35)

Public sources, all linked with claim-specific attribution in the delivered report:
- https://www.federalreserve.gov/econres/feds/the-effect-of-the-federal-reserve-on-the-stock-market-magnitudes-channels-and-shocks.htm
- https://www.nber.org/papers/w20439
- https://www.nber.org/research/business-cycle-dating/business-cycle-dating-procedure-frequently-asked-questions
- https://alfred.stlouisfed.org/help
- https://www.newyorkfed.org/research/data_indicators/term-premia-tabs
- https://corporate.walmart.com/news/2022/07/25/walmart-inc-provides-update-for-second-quarter-and-fiscal-year-2023
- https://www.sec.gov/Archives/edgar/data/104169/000010416920000037/earningsrelease-7312020.htm
- https://investors.wm.com/news-releases/news-release-details/wm-announces-fourth-quarter-and-full-year-2022-earnings
- https://investors.wm.com/news-releases/news-release-details/waste-management-announces-second-quarter-earnings-7/
- https://corporate.mcdonalds.com/corpmcd/our-stories/article/q2-2020-results.html
- https://corporate.mcdonalds.com/corpmcd/our-stories/article/Q3-2022-results.html
- https://www.sec.gov/Archives/edgar/data/80424/000008042422000097/fy2223q1jas8-kexhibit991.htm
- https://investor.costco.com/news/news-details/2022/Costco-Wholesale-Corporation-Reports-Fourth-Quarter-And-Fiscal-Year-2022-Operating-Results-09-22-2022/default.aspx
