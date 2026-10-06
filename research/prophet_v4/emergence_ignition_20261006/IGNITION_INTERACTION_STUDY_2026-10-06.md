# Frozen ignition-convergence interaction study

**Date:** 2026-10-06  
**Disposition:** suggestive historical diagnostic; strict registered effect **NOT ESTIMABLE**; no promotion, production, ranking, entry, sizing, alert or trading authority.  
**Scope:** the frozen T2 × at-least-two-family hypothesis. No threshold retuning, horizon substitution, champion search, production module execution or live market collection occurred.

## 1. Findings that change the research conclusion

The small historical H5 pattern survives replication, issuer deduplication and several contemporaneous control comparisons. It remains worth a properly clocked prospective test. It does **not** yet establish an independent, point-in-time-valid rerating interaction, a calibrated win probability or an executable strategy.

Five material corrections are required.

1. **The first-ticker denominator is 143, not 111.** The pinned v3 H5 buy-lane T2 ledger contains 327 nightly observations and 143 distinct tickers: 118 with zero flags, 20 with one, and five with two at their first T2 observation. The parent report's §13.2 table, 89 + 17 + 5, is stale or differently filtered. Its later 5-versus-138 Fisher denominator agrees with the immutable ledger. The five exposed names and their H5 outcomes reproduce.
2. **Five names do not mean five independent evidence shocks.** They occupy four first-observation dates, five sectors and only three selected ownership disclosures. Every one carries the ownership flag. The evidence-census lane established that the selected holdings descend from three August 14 Q2 filings: D1 for TSLA/ISRG, Soros for ADM/PRIM, and Coatue for INTC. There is no observed two-family exposure without ownership in this five-name set.
3. **The primary prospective exposure is not established by these booleans.** Legacy SUE has no complete value-to-filing clock lineage; news chips omit underlying event identities and article clocks; ownership must carry the registered age rule and its receipt. Raw T2 event clocks improve the reconstruction but do not repair those missing joints. “Zero proven eligible” means eligibility was not established, not that no qualifying episodes existed.
4. **The H5-to-H10 persistence headline contains inherited return.** The accepted 35/55 cumulative retention result reproduces. In the separate, non-overlapping H5→H10 interval, only 24/55 H5 responders outperform SPY, with mean incremental excess **−0.883%**. Keeping an accumulated lead is different from generating a fresh positive return edge.
5. **Execution clocks and price vintages remain load-bearing.** Three of the five first observations were `bounce_wait` or `blocked`. ISRG's preserved board first appears after the ledger's assumed entry session. PRIM's attention flag changes between first and latest versions of the same board date. Of 335 paired issuer/horizon ledger observations, 67 differ by more than one basis point from the current frozen-price reconstruction; the largest absolute-return difference is 6.693 percentage points. The original outcomes remain untouched, and the newer-price calculations are separately labelled sensitivities.

## 2. Sources, units and outcome clocks

The primary diagnostic is `data/us_board_ledger/retro_grades.parquet` at macro commit `770918cb266b5d884978e31d61670b4efd789eaf`, Git blob `b0ee089e86269854b699f4667b47dd10a469374c`, SHA256 `61bb8cc6ff0f1cfd14f33ba50fc5ce17db4c93e800f74e307c70c5606ae4f9d7`. It contains 13,563 rows and 87 columns, with decision dates June 15–September 17. Its recorded horizons are H5, H10 and H21. The complete source-object manifest records 592 immutable object digests used for the price and covariate work. [S1]

The diagnostic exposure is unchanged: `news_burst + sue_fresh + smartmoney_add >= 2`, within `rank_by=us_prophet_v3`, `lane=buy`, `tier_cascade=T2`. Missing flags stay unknown. All three flags are recorded on the v3 diagnostic rows, although recorded `False` does not prove that upstream collection was complete.

The conservative issuer sensitivity selects the first H5 T2 observation for each ticker **before** looking at its evidence-count group. That exact ticker/date is held fixed when joining H10 and H21. Direct source verification finds zero mismatches in technical tier, all three flags, entry date or entry state across the 134 H5/H10 and 58 H5/H21 pairs; the reproduction now asserts that invariant. Selecting a fresh first row independently at each horizon would change the population as later observations mature. Ticker deduplication is a sensitivity, not a replacement for canonical issuer identity or the existing candidate-episode owner.

The inherited grading convention fills at the **next session's close** and measures H further sessions after that fill. H5 therefore is not the return from the decision close to its fifth subsequent close. The separate price reconstruction uses the SPY session calendar, requires every issuer close in its window, and labels conditional next-session-open returns separately. The frozen preregistration instead specifies its primary five-session horizon **after the episode decision cut**. The prospective evaluation owner must pin that decision cut's session boundary and corresponding entry/end observations before accrual; the historical grader's extra session cannot silently become the prospective primary clock. No public-delivery timestamp, order admission, fee, spread, actual fill, stop execution or management exit is inferred. [S1–S2]

All inspected data through October 6 is discovery data, including any observation later than the original report's September 17 grading boundary. None is a future confirmation set.

## 3. Primary historical comparison

### Fixed first-T2-per-ticker cohort

| H5 outcome | Legacy convergence, n=5 | Other first T2, n=138 |
|---|---:|---:|
| Positive absolute return | 4/5, 80.0% | 58/138, 42.0% |
| Mean absolute return | +3.705% | −0.168% |
| Positive SPY excess | 5/5, 100.0% | 56/138, 40.6% |
| Mean SPY excess | +3.663% | −0.127% |
| Positive sector excess | 5/5, 100.0% | 68/138, 49.3% |
| Mean sector excess | +4.361% | +0.542% |
| Terminal absolute loss at least 5% | 0/5 | 23/138 |
| Terminal absolute loss at least 10% | 0/5 | 4/138 |

The five names are not five profitable trades. PRIM has negative absolute H5 return despite positive SPY and sector excess, and the availability states restrict three names at their first observation.

| First observed T2 date | Ticker | Legacy family combination | Entry state | H5 absolute | H5 SPY excess | H5 sector excess |
|---|---|---|---|---:|---:|---:|
| Aug 21 | TSLA | Attention + ownership | `bounce_wait` | +5.445% | +4.976% | +6.890% |
| Sep 03 | ADM | SUE + ownership | `buy_now` | +2.163% | +3.372% | +2.352% |
| Sep 03 | PRIM | Attention + ownership | `blocked` | −0.349% | +0.859% | +2.697% |
| Sep 10 | INTC | Attention + ownership | `bounce_wait` | +5.445% | +5.666% | +5.237% |
| Sep 14 | ISRG | SUE + ownership | `buy_now` | +5.821% | +3.440% | +4.630% |

The nominal Wilson 95% interval for 5/5 SPY-positive outcomes is **56.6–100%**; for 4/5 absolute-positive it is **37.6–96.4%**. These are ordinary descriptive binomial intervals. They do not correct post-selection, overlapping windows, source clustering, correlated issuers or missing eligibility. Reporting them as forecast confidence would be misleading.

### Same-date controls and concentration

Using first T2 observations on both sides, the issuer-weighted H5 SPY-excess advantage is **+4.248 percentage points**. The four equal-weight date differences are +5.770 pp on August 21, +2.281 pp on September 3, +7.697 pp on September 10, and +3.211 pp on September 14. Their mean is **+4.740 pp**.

The ordinary date-level t interval is +0.821 to +8.658 pp; a seeded 20,000-resample date bootstrap gives +2.746 to +6.734 pp. With only four positive date differences, a one-sided sign calculation is 0.0625. None of these values supplies confirmation: the exposure was selected after outcome inspection, and date blocking does not remove common ownership disclosures or every overlapping-return dependency.

The parent nightly calculation also reproduces: 12 exposed rows, seven dates, equal-date gap **+4.188 pp**. Its much tighter apparent uncertainty is not twelve independent opportunities. The fixed first-ticker calculation is the more honest independent-unit sensitivity.

Same-date/sector matching retains only four treated names across three dates. The issuer-weighted gap is +4.871 pp, but the equal-date t interval spans approximately **−0.402 to +11.519 pp**. The lack of a comparable first-T2 same-date health-care control leaves ISRG unmatched. Same-date/Entry Availability matching retains four names and does not restore executable status to restricted observations.

Leaving out any one exposed ticker leaves H5 mean SPY excess between **+3.162% and +4.364%**. Because each exposed ticker has a different sector, exposed-cohort leave-one-sector results are numerically the same sensitivity. The result is not wholly one-ticker-driven at H5, but five sectors do not cure four-date and three-disclosure dependence.

## 4. Covariate controls and negative controls

The replay produced 2,338 trailing-price covariate rows: 2,290 observed and 48 without the decision session in the admitted frozen price cut. All 143 first-T2 cases have the controls used here. These are **final-vintage adjusted-price sensitivities**, not reconstructed decision-time adjustment vintages.

The exposed cohort is not simply stronger on every pre-existing price measure. Its mean trailing five-session return is +4.55% versus +6.47% in controls; its mean trailing 21-session return is +1.61% versus +4.26%; its mean 21-session SPY relative return is +1.46% versus +2.26%. It sits farther below its recorded high: mean `off_high` −30.66% versus −20.12%. This weakens a simple “these were already the strongest momentum names” explanation, while neither establishing causal independence nor proving common support.

The predetermined nearest-control sensitivity uses same date and sector, standardizes alpha, off-high, conviction-composite, and prior five/21-session momentum, and uses one nearest control with lexical ticker tie-breaking. Its scale estimates pool all 143 first-issuer observations retrospectively; they are not an earlier-data-only or PIT-admitted matching fit. It matches TSLA→CPNG, ADM→PG, PRIM→ACM and INTC→KEYS; all four H5 excess differences are positive. ISRG remains unmatched. Some covariate distances are large, so a four-pair result is not a fully adjusted causal effect. A multivariable coefficient with five treated cases and four dates would manufacture precision. Also, 21-session momentum and 21-session SPY relative strength are algebraically collinear after date effects.

**The ledger's `composite_z` is not the incumbent C1 rank.** An additional raw-board control uses actual `prophet.score`, within each preserved board date. Top-decile C1 cases with zero evidence flags, deduplicated by first qualifying ticker, show 8/26 H5 SPY-positive outcomes and mean −2.020% using first-preserved boards; latest-per-date boards give 8/25 and −1.908%. This is a separate descriptive control with its own raw-board coverage, not an equivalent randomized population.

| Frozen diagnostic negative control | First-ticker n | H5 SPY-positive | Mean SPY excess |
|---|---:|---:|---:|
| T1 plus convergence | 3 | 1/3 | −1.296% |
| T1 without convergence | 137 | 60/137 | −1.297% |
| Non-T2 buy lane plus convergence | 7 | 3/7 | −2.444% |
| Non-T2 buy lane without convergence | 326 | 121/326 | −1.126% |
| First observed watch row plus convergence | 4 | 2/4 | +0.025% |
| T2, SUE flag only | 3 | 0/3 | −5.633% |
| T2, ownership flag only | 15 | 4/15 | −1.021% |
| T2, attention flag only | 2 | 2/2 | +7.033% |

These denominators deliberately select the first observation in each technical/lane population before grouping by flags. They must not be conflated with “first time an issuer ever becomes converged,” which is a different emergence estimand.

The attention-only result prevents a claim that the multi-family interaction is already proved superior to every single leg. It consists of PG and RKLB, both `bounce_wait`; RKLB supplies most of the mean. Conversely, the two SUE+ownership cases are both H5-positive without attention. The tiny factorial cells cannot distinguish a stable interaction from chance, issuer selection, ownership conditioning or species-specific behavior.

July also cannot serve as a clean external replication: the `confluence` era has only five legacy T2-plus-convergence nightly rows with mean −1.084% SPY excess; v1 has four on one board date with mean +0.188%; v2 has none. Earlier product eras differ in selection and source semantics. Null flags in older eras are not measured absences, and non-null later flags are not a source-coverage certificate. The separate evidence-maturity census adjudicates that distinction.

## 5. H3/H10/H21, risk and missingness

The original fixed-cohort ledger has five exposed H5 cases, four H10 cases and one H21 case. H10 is 3/4 SPY-positive, mean +6.409%, with INTC contributing +19.938%. Removing INTC leaves +1.900% mean excess among three; that is weaker concentration but does **not** reproduce the negative “remove INTC” result from the different T2-plus-news cohort. Those hypotheses must stay separate.

The independent October-2 price reconstruction gives:

| Horizon | Exposed observed / initial | Absolute-positive | SPY-positive | Sector-positive | Mean absolute | Mean SPY excess | Mean sector excess |
|---|---:|---:|---:|---:|---:|---:|---:|
| H3 | 5/5 | 3/5 | 3/5 | 5/5 | +0.977% | +1.524% | +2.589% |
| H5 | 5/5 | 4/5 | 5/5 | 5/5 | +3.873% | +3.809% | +4.260% |
| H10 | 5/5 | 4/5 | 4/5 | 5/5 | +7.231% | +6.429% | +7.628% |
| H21 | 1/5 | 1/1 | 1/1 | 1/1 | +8.933% | +8.114% | +15.193% |

H3 is an added secondary diagnostic, not a replacement primary. H21 has four right-censored exposed cases and supports no durable-leadership claim. The reconstruction can mature a horizon missing from the older ledger, but that is a separately dated calculation; the accepted ledger is not silently backfilled.

Conditional next-session-open absolute returns can be reconstructed where coherent issuer OHLC exists, but **next-open SPY excess is not estimable**: the pinned SPY source is close-only, and this bounded audit admitted no independent SPY-open lineage. The close-based SPY comparison cannot substitute for the missing opening benchmark. Issuer opening prices are adjusted-price opportunity diagnostics, with execution still unproved.

**Risk is not captured by terminal win rate.** Across the five H5 reconstructed cases, mean close-path MFE is +4.367%, mean close-path MAE −1.725%, mean close-path maximum drawdown −2.234%, mean intraday MFE +5.943%, and mean intraday MAE −2.993%. INTC experiences **−8.180%** intraday MAE and −5.634% close-path MAE despite ending with positive H5 excess. No stop hit, fill or management rule is inferred from those extrema. Complete intraday OHLC exists for all five exposures but only 105 of 138 controls; raw intraday group comparisons must preserve that missingness.

The terminal-loss thresholds of −5% and −10% were specified as descriptive reporting cuts before these distributions were read. They were not optimized as strategy thresholds. Zero terminal large losses among five cases does not certify a low future loss probability.

There are **335 paired original/reconstructed observations**: 143 H5 + 134 H10 + 58 H21. Sixty-seven absolute returns and 67 SPY-excess returns differ by more than one basis point; 66 sector-excess values do. The maximum absolute-return discrepancy is CLSK September 10 H5: original −0.841% versus reconstructed +5.852%, a +6.693 pp difference. The same ticker/source-path and entry-date labels are insufficient to identify which historical price/calendar vintage created the frozen grade. This is an unresolved replay-provenance limitation, not permission to overwrite it with a preferred result. [S1–S2]

## 6. Durability: separate the initial cushion from the new interval

The paired 134-name historical cohort contains 55 H5 SPY-positive and 79 H5 non-positive cases. The inherited cumulative retention statistics reproduce:

| H5 state | Still cumulative SPY-positive at H10 | Positive SPY excess in H5→H10 only | Mean incremental SPY excess |
|---|---:|---:|---:|
| Positive, n=55 | 35/55, 63.6% | 24/55, 43.6% | −0.883% |
| Non-positive, n=79 | 9/79, 11.4% | 19/79, 24.1% | −2.268% |

For the 58 cases with H21 grades, 27 were H5-positive. Thirteen of those 27 remain cumulative SPY-positive at H21, but only **7/27** have positive incremental H5→H21 excess; its mean is **−2.057%**.

H5 success remains associated with less-bad subsequent performance than H5 failure. The data nevertheless does not support interpreting a retained cumulative lead as positive continuation alpha. A durability head must evaluate incremental returns, drawdown from a post-ignition peak, lead-loss hazards and genuinely new evidence, alongside cumulative lead retention. Reconditioning on H5 must carry its selection clock and compare H5 responders with appropriate H5-state controls. No reconstructed management exits or hindsight optimal stopping are supplied here.

## 7. Raw board and publication reconciliation

The companion analysis uses 394 raw-board variants across 36 as-of dates, including 30 v3 dates, from the emergence lane's immutable-history extraction of `site/factordata/us_standouts.json`. It directly verifies seven original Git blobs covering the five first cases. First-preserved extraction SHA256 is `060d56804c96601ac8f86f4f5c826105a2509c7e584673b5b0b4dbddc3240289`; latest-per-date extraction is `599a96d4ba23e2aabe81caa9fb434fabd2652d700d0c48093ffee12c3478d889`. [S3]

The first-board join covers 1,092/1,098 v3 H5 buy observations, with zero tier mismatches, eight news-flag mismatches, three SUE mismatches, and three convergence mismatches. The latest-board join covers 1,024/1,098, with 14 tier mismatches and one convergence mismatch. A board date is therefore not enough to identify a decision record.

Two separately labelled analysis keys disclose the identity sensitivity. The **coarser key** uses ticker, technical event date, signal anchor era, board definition and selection era; it omits `tier_observed_date` and produces 170 first-preserved key observations with four converged cases, versus 171 latest-preserved observations with five. The first-versus-latest exposed difference is driven by PRIM's later attention arrival. The **full prereg-shaped key** adds `tier_observed_date` without changing any flag or horizon. Its results are:

| Board variant / key | Key observations | Distinct tickers | Zero flags | One flag | Two flags | Three flags | ≥2 flag observations / tickers / dates |
|---|---:|---:|---:|---:|---:|---:|---:|
| First-preserved / coarser | 170 | 142 | 140 | 26 | 4 | 0 | 4 / 4 / 4 |
| Latest-per-date / coarser | 171 | 144 | 142 | 24 | 5 | 0 | 5 / 5 / 4 |
| First-preserved / full prereg-shaped | 289 | 142 | 236 | 43 | 10 | 0 | 10 / 5 / 6 |
| Latest-per-date / full prereg-shaped | 292 | 144 | 240 | 42 | 9 | 1 | 10 / 5 / 6 |

The full-key samples contain respectively 7/11/45 and 9/11/43 attention/SUE/ownership flags. Both ten-observation exposed groups have nine positive H5 SPY-excess outcomes, with means +2.959% first-preserved and +2.764% latest-per-date. These remain correlated observations from five names. The 326 first-preserved and 315 latest-per-date raw T2 rows in the ledger overlap have **zero missing components** in either key and all record `tier_observation_provisional=false`; no provisional or unknown flags are excluded silently. These completeness counts apply to the covered overlap, not the missing boards. Adding the observed date splits many otherwise identical technical-event keys, so a complete six-part key alone does not certify a fresh event transition. Neither sensitivity supplies canonical B1 identity, a reconstructed first eligible decision cut, independent evidence lineage or the strict registered denominator.

| Ticker | Technical event / observed dates | Earliest preserved source timing | Consequence |
|---|---|---|---|
| TSLA | Aug 17 / Aug 21 | Emit Aug 22 02:47Z; Git Aug 22 05:50Z | First later regular open is Aug 24 at adjusted $361.41. State remains `bounce_wait`; buy-zone high is $340.90. |
| ADM | Sep 02 / Sep 03 | Emit Sep 04 00:52Z; Git Sep 04 02:12Z | Sep 04 open $83.67 is within the quoted $82.33–$84.38 zone, conditional on comparable prices and actual delivery. |
| PRIM | Sep 02 / Sep 03 | First emit Sep 04 00:52Z has no burst; later emit Sep 04 09:54Z has three negative news items | Attention remains direction-neutral. The later revision changes the two-family indicator before the opening session; it cannot be attributed to the first preserved cut. State is `blocked`. |
| INTC | Sep 04 / Sep 09 | First emit Sep 11 04:04Z; Git Sep 11 05:19Z | A source-date/observation-date distinction exists before the assumed Sep 11 fill. The board's price is about 5.90% above the pinned Sep 10 adjusted close; price geometry requires vintage reconciliation. State is `bounce_wait`. |
| ISRG | Sep 14 / Sep 14 | First emit Sep 16 05:44Z; Git Sep 16 09:45Z | The ledger's Sep 15 entry precedes this preserved board. First subsequent open is Sep 16 at $378.00, just above its $377.90 zone high and below $381.30 no-chase; no claim that the opportunity was entirely lost is made. |

Git first appearance bounds preserved repository visibility. It does not prove when a user saw the board, when a live origin served that revision, or whether an order could be entered. Latest-per-date data may have arrived after the assumed entry; first-per-date data may lack evidence added before an actual decision. Both restrictions are explicit in the companion CSV.

A bounded NVDA publication check, requested by the integration owner, uses current pinned macro commit `731a23fb64b9f6f1a321c77618f927f1a58d2d41`, NVDA OHLC blob `0e95a8c062c22f663fe7a80c9a76188bb444709e`. After the final plan's September 26 Git publication, the first regular open is September 28 at $229.75. Across September 28–October 5 the minimum regular-session low is $227.03, above the fixed $226.90 no-chase level and $225.10 accumulation high. This extends the accepted publication-opportunity diagnostic without making a fill or extended-hours claim. [S4]

## 8. Scientific ruling and smallest useful next accrual

**Historical interaction:** suggestive and reasonably robust within this selected diagnostic, with explicit small-sample, source and execution limitations.  
**Strict PIT/independent interaction:** not estimable from the qualified evidence currently assembled.  
**Future expected hit rate:** not calibrated; neither 100% nor the parent 90.9% headline is an admissible estimate.  
**Durable leadership:** unproved; cumulative retention must be separated from incremental continuation.  
**Production promotion:** unsupported.

The next useful accrual belongs to the existing Conditional Fusion/evaluation and B1/B03/B04 interfaces. Each future first T2 episode needs one immutable decision cut, technical event and observation clocks, canonical identity where one exists, source-native evidence-event IDs, capture and known-at clocks, a registered ownership-age allowance, family dependence/duplication markers, actual C1 rank, deterministic availability, first board/plan publication receipts and same-basis executable-price observations. Unanchored candidates remain visible through the existing all-candidate surface with honest identity status; this study creates no new episode plane.

Keep the registered H5 comparison and families fixed. Accrue contemporaneous 0/1-family T2 controls with the same source-coverage rules, and retain the preregistered single-leg, T1, stale/neutral and non-T2 comparisons. Design future inference around distinct decision blocks, issuers and upstream disclosures. Future eligibility must be settled before outcomes are read. This study supplies a reproducible measurement harness and evidence requirements, not a live collector, operational queue, fitted score or approval to change Prophet behavior.

## 9. Reproduction and deliverables

`reproduce_ignition_study.py` reads only the pinned Git objects and writes to an isolated `--out` directory outside the source checkout. It requires Python, pandas, NumPy, SciPy and a parquet backend. It verifies the ledger blob, refuses duplicate economic keys, preserves the first-ticker cohort across horizons, checks the 327/143/5 denominator, and checks that the same-date primary retains five treated observations. A scalar-grouping compatibility error discovered during implementation was corrected before these final results were assembled. No scientific threshold changed.

Example:

```bash
python3 reproduce_ignition_study.py --repo /path/to/macro --out /tmp/ignition-new-run
```

The optional `--control-keys` CSV adds sibling-study `(as_of,ticker)` covariates; it does not change the ignition cohort. `reconcile_ignition_board_clocks.py` consumes the first/latest raw-board extraction and verifies selected original blobs through `--history-repo`. The integration owner should retain the emergence extraction manifest with this report. No accepted production or grading artifact is rewritten.

Key files are `IGNITION_RESULTS_2026-10-06.json`, `ignition_summary_2026-10-06.csv`, `first_t2_issuer_cohort_2026-10-06.csv`, `first_t2_reconstructed_outcomes_2026-10-06.csv`, `matched_control_differences_2026-10-06.csv`, `price_controls_2026-10-06.csv`, `IGNITION_BOARD_CLOCKS_2026-10-06.json`, `five_exposure_publication_clocks_2026-10-06.csv`, and `SOURCE_MANIFEST_2026-10-06.json`. The report is complete for this bounded research lane; the integration owner retains publication and prospective-study disposition.

### Immutable source anchors

- **S1:** [Frozen grading ledger](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/data/us_board_ledger/retro_grades.parquet), [parent re-audit](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/research/prophet_v4/PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md), and [frozen ignition preregistration](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/research/prophet_v4/PROPHET_IGNITION_CONVERGENCE_PREREG_2026-10-06.md).
- **S2:** [US board grader](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/scripts/grade_us_board.py), [shared grading convention](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/engine/grading.py), and [price-basis coverage contract](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/data/us_board_ledger/README.md). Frozen OHLC paths and their hashes are enumerated in the accompanying source manifest.
- **S3:** First TSLA [board commit f1e356f](https://github.com/mastermindx-market-intelligence/macro/blob/f1e356f684ec988925718ceb3970a4fafaae3eb9/site/factordata/us_standouts.json); first ADM/PRIM [39d85b7f](https://github.com/mastermindx-market-intelligence/macro/blob/39d85b7ffbb9ea264538d122e8aa8f8f57f80fdd/site/factordata/us_standouts.json); later ADM/PRIM [297b3e6f](https://github.com/mastermindx-market-intelligence/macro/blob/297b3e6f16a20fb9ec090847de4ba53bbeda80be/site/factordata/us_standouts.json); first INTC [5d675b38](https://github.com/mastermindx-market-intelligence/macro/blob/5d675b38c3cf0418065c300b76d0377615a06fce/site/factordata/us_standouts.json); first ISRG [4347812e](https://github.com/mastermindx-market-intelligence/macro/blob/4347812e120f5c2dc84190a740eb395651d351e1/site/factordata/us_standouts.json). The evidence-census lane's `evidence_source_census.json` carries the three original 13F disclosure receipts.
- **S4:** [NVDA OHLC through October 5](https://github.com/mastermindx-market-intelligence/macro/blob/731a23fb64b9f6f1a321c77618f927f1a58d2d41/data/baskets/ohlcv/NVDA.parquet), Git blob `0e95a8c062c22f663fe7a80c9a76188bb444709e`, SHA256 `e28878d447358938ef4280a807dd6ea9c23e176943f2e70eedf00e9fc82def58`. Exact six-session prices are preserved in `NVDA_PUBLICATION_PRICE_CONTEXT_2026-10-06.json`.
