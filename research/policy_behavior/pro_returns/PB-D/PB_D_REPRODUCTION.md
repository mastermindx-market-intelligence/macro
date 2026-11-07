# PB-D — T2 × event quality: reproduction and adjudication

Date: 2026-10-07. Operation: `PB-D-T2-EVENT-QUALITY-20261007`.

**Verdict: the requested historical numerical pattern reproduces; independent economic-evidence validity remains untested.** The strongest surviving discovery is a short-horizon, selected T2 interaction with at least two **legacy feature categories**. It survives first-issuer selection and several control/omission checks, but the sample has five treated issuers, overlapping windows, post-hoc selection and incomplete source clocks. This is sufficient to justify a carefully frozen prospective research test; it grants zero live signal authority.

The claim that those categories are already “independent evidence legs” is not supported by the stored fields. Historical audited materiality, independent-root and expectation-change labels remain unknown. The research cannot estimate their incremental value merely by renaming the old features.

## 1. Sources, execution and observation unit

The commission was recovered from [PR8560's packet at its read head](https://github.com/mastermindx-market-intelligence/macro/blob/7abc3dc596c5a6463effb37422bf9bd34bbdf1ba/research/policy_behavior/handoffs/PB_D_T2_EVENT_QUALITY_PRO.md). The original findings and script were read at [PR8495's frozen head](https://github.com/mastermindx-market-intelligence/macro/tree/770918cb266b5d884978e31d61670b4efd789eaf/research/prophet_v4). Event semantics were reconciled with [PR8533's masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/cde0219b1040c66cbc8647f86352a25794488528/research/prophet_v4/news_to_business_impact_20261006/package/MASTERPLAN.md) and [the policy-behavior source packet](https://github.com/mastermindx-market-intelligence/macro/blob/ee86db2c832c73a36837c1240df871700340d6da/research/policy_behavior/POLICY_BEHAVIOR_REVEALED_PREFERENCE_MASTERPLAN_2026-10-07.md). Those PRs were not modified.

Frozen input: [`data/us_board_ledger/retro_grades.parquet`](https://github.com/mastermindx-market-intelligence/macro/blob/2f2feec4851b45636f63a48ec61e6f0b02b8118a/data/us_board_ledger/retro_grades.parquet).

| Identity | Value |
|---|---|
| Source commit | `2f2feec4851b45636f63a48ec61e6f0b02b8118a` |
| Git blob | `b0ee089e86269854b699f4667b47dd10a469374c` |
| SHA-256 | `61bb8cc6ff0f1cfd14f33ba50fc5ce17db4c93e800f74e307c70c5606ae4f9d7` |
| Size and shape | 1,070,132 bytes; 13,563 rows × 87 columns |
| Economic key | `(as_of, lane, ticker, horizon)`; no duplicates |
| Primary discovery selector | `rank_by == us_prophet_v3` and `lane == buy`; then horizon and observed `tier_cascade == T2` |

The upstream reproduction script was executed against the frozen input. A separately written PB-D script then reproduced counts, returns, matching, omissions, pairwise horizon maturity and power calculations. Independent review also recomputed discriminating aggregates directly from PyArrow record dictionaries, without calling PB-D's pandas analysis functions. All ten numeric checks pass. A separate hash-verified archive script reproduces NVDA's 6/0/0 item counts and six underlying null sentiment fields. The JSON outputs contain full row details, definitions and uncertainty qualifications; returns are decimals, multiplied by 100 in this report.

| Horizon | v3 buy rows | Signal dates | Date range | T2 rows |
|---|---:|---:|---|---:|
| H5 | 1,098 | 20 | Aug17–Sep17, 2026 | 327 |
| H10 | 923 | 16 | Aug17–Sep10 | 296 |
| H21 | 407 | 7 | Aug17–Aug25 | 114 |

There are no H1 rows in this input. NVDA's Sep25 example is outside the graded sample, which ends Sep17. All H5 v3 rows are marked adjusted; 876 identify `baskets_ohlcv` and 222 `yahoo`. These metadata do not independently certify every vendor price or corporate-action adjustment. Legacy leg booleans and selected returns are complete in this v3 sample, but **430/1,098 H5 rows have missing tier labels**. “Outside T2” outputs include those unclassified rows and must not be described as certified non-T2 controls.

## 2. Requested numerical claims

Positive means strictly greater than zero. SPY/sector outcomes subtract the benchmark simple return over the same entry/exit dates. `≥2 legacy categories` means at least two explicit true values among news burst, fresh SUE and smart-money addition; it is not a root-independence certificate.

| H5 sample | n | Absolute positive | SPY positive | Sector positive | Mean SPY excess |
|---|---:|---:|---:|---:|---:|
| T2 + news burst | 11 | **8/11** | **10/11** | 9/11 | **+3.5813%** |
| First qualifying T2+news observation per issuer | 7 | **4/7** | **6/7** | 5/7 | +3.8188% |
| First T2 per issuer, then require news | 5 | 3/5 | 5/5 | 4/5 | +5.1136% |
| T2 + ≥2 legacy categories, repeated rows | 12 | 9/12 | **10/12** | 10/12 | **+2.6855%** |
| First T2 per issuer, then ≥2 categories | 5 | **4/5** | **5/5** | **5/5** | **+3.6627%** |
| T2 + news=false | 316 | 117/316 | 114/316 | 153/316 | −0.7166% |
| T2 + fewer than 2 categories | 315 | 116/315 | 114/315 | 152/315 | −0.6961% |

All requested count claims above reproduce. “First observation per issuer” in the 6/7 news claim specifically means first **qualifying T2+news** observation; it is a different selector from first T2 then require news. The future study freezes first T2 regardless of later news availability to avoid selecting an issuer's first favorable evidence conjunction.

The five first-T2 multi-category observations are:

| Signal date | Entry close date | Issuer | Legacy categories | Absolute H5 | SPY H5 | Sector H5 |
|---|---|---|---|---:|---:|---:|
| Aug21 | Aug24 | TSLA | News + ownership | +5.4449% | +4.9760% | +6.8904% |
| Sep03 | Sep04 | ADM | SUE + ownership | +2.1629% | +3.3717% | +2.3520% |
| Sep03 | Sep04 | PRIM | News + ownership | −0.3493% | +0.8595% | +2.6974% |
| Sep10 | Sep11 | INTC | News + ownership | +5.4449% | +5.6660% | +5.2371% |
| Sep14 | Sep15 | ISRG | SUE + ownership | +5.8211% | +3.4405% | +4.6301% |

These are benchmark-relative successes, not five universally profitable trades: PRIM is absolute-negative. Nor were all discovery rows entry-authorized. Among H5 news rows, only two have `buy_now` or `partial`, with one SPY-positive and mean +0.5817%; among multi-category rows, five have those statuses, four SPY-positive and mean +2.1251%. At H10 the corresponding action subsets are 0/2 and 0/4 SPY-positive. Conditioning on entry status is a sensitivity, not a claim that the board observations were executable entries.

## 3. Material population mismatch in the original report

The source's Section 13.2 labels a table “first T2 per ticker” while reporting leg-bin counts 89/17/5. Those counts reproduce by selecting each ticker's **first observation across all tiers, then retaining T2**. Actual first-T2 selection produces 118/20/5. The treated five happen to coincide, while controls differ.

| Selector | 0 categories | 1 category | 2 categories | Control SPY positives / n |
|---|---:|---:|---:|---:|
| First-any-tier, then T2 | 89 | 17 | 5 | 43/106 |
| Filter T2, then first per issuer | 118 | 20 | 5 | 56/138 |

The reported Fisher denominator corresponds to the **second** population, table `[[5,0],[56,82]]`, with one-sided p=0.0128129643 under an IID, fixed-rule interpretation. It must not be combined with the first population's 89/17/5 table. This is a population-label mismatch; it does not falsify the treated 5/5 count. The PB-D script derives both selectors and both T1 variants explicitly.

The unclassified-tier problem is separate: H5 outside-T2 news contains 7 signal rows, three missing tier, and 764 controls, 427 missing tier. Outside-T2 multi-category contains 11 signals, six missing tier, and 760 controls, 424 missing tier. A valid specificity comparison requires explicit T1 classification, not the complement of T2.

## 4. Matching, concentration and uncertainty

### Same-date controls reproduce the +4.19-pp claim

The historical matching groups by signal `as_of`; in this input each signal date maps to one deterministic next-entry date. Lower-category T2 controls perform worse on all seven multi-category signal dates:

| Signal date | Treated rows | Control rows | Mean SPY excess gap |
|---|---:|---:|---:|
| Aug21 | 1 | 19 | +5.12490 pp |
| Sep03 | 2 | 24 | +2.66319 pp |
| Sep04 | 1 | 21 | +3.62031 pp |
| Sep08 | 2 | 23 | +3.73236 pp |
| Sep09 | 2 | 14 | +4.54797 pp |
| Sep10 | 3 | 19 | +4.85250 pp |
| Sep14 | 1 | 7 | +4.77436 pp |

Equal-date mean gap is **+4.1879429 pp**, reproducing approximately +4.19. Equal-treated-row weighting gives +4.1636772 pp. These are different estimands. For news, the distinction is larger: +5.7828235 pp equal-date versus +4.5350787 pp equal-row.

| H5 matching | Multi-category supported rows | Positive row gaps | Mean row-weighted gap | News supported rows | News mean row-weighted gap |
|---|---:|---:|---:|---:|---:|
| Same date | 12 | 12 | +4.1637 pp | 11 | +4.5351 pp |
| Same date and sector | 10 | 9 | +3.6377 pp | 8 | +4.1813 pp |
| Same date, sector and entry status | 2 | 2 | +6.4235 pp | 2 | +6.4235 pp |

Date/sector matching retains a positive discovery difference. The strict entry-status comparison has only two supported rows, so the apparently larger effect does not establish robust technical-state control. The frozen archive lacks an independent native-age-matched economic-quality study. All observations already condition on T2; that is not equivalent to matching every technical input.

Within exact entry/exit-date pairs, subtracting the shared SPY return cancels in the difference. With sector matching, the sector benchmark also cancels. Mean benchmark-relative gaps cannot therefore be counted as independent confirmation of the same matched absolute-return difference. Individual benchmark win counts still differ.

### Dependence is substantial but not reducible to a single issuer

ADM contributes five and PRIM four of the 12 multi-category rows: **75% from two issuers**, five distinct issuers in total. The issuer-weight concentration equivalent is 12²/(5²+4²+1²+1²+1²)=3.27. This is a concentration diagnostic, **not an effective independent sample size**. News contains seven issuers, with PRIM and PG contributing 6/11 rows. Adjacent H5 windows share trading sessions; several issuers share dates and economic drivers. Seven positive dates are not seven independent Bernoulli trials.

Removing each treated issuer from both signal and control pools leaves multi-category H5 date-mean gaps positive, from **+3.7691 pp to +5.0912 pp**. Removing INTC yields a +3.9337-pp date gap; removing ADM and PRIM leaves three treated rows, all SPY-positive, with mean +4.6942%. Thus “one name creates the entire H5 pattern” is too strong. Conversely, those tiny remnants do not solve dependence or postselection. News leave-one-issuer date gaps also remain positive, approximately +4.4003 to +6.0191 pp.

Conditional IID exact 95% binomial intervals are wide even before those issues:

| Observation | Exact 95% interval for the success probability |
|---|---|
| 10/11 news SPY wins | 58.72%–99.77% |
| 8/11 news absolute wins | 39.03%–93.98% |
| 6/7 first-qualifying news SPY wins | 42.13%–99.64% |
| 4/7 first-qualifying news absolute wins | 18.41%–90.10% |
| 10/12 multi-category SPY wins | 51.59%–97.91% |
| 5/5 first-T2 SPY wins | 47.82%–100% |

These [exact-binomial](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm) intervals are fixed-rule IID illustrations; they are not selection-corrected or cluster-robust confidence in the discovered rule. The observed search over tiers, categories, issuer selectors, horizons and examples prevents treating a nominal Fisher/binomial p-value as a clean confirmatory result. Small-cluster inference cannot be repaired simply by resampling the same five issuers; see `PB_D_POWER_AND_LIMITATIONS.md` and [Cameron–Miller](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf).

## 5. Horizon deterioration, persistence and path limits

| Sample | H5 SPY wins / mean | H10 SPY wins / mean | H10 mean excluding INTC |
|---|---|---|---:|
| News + T2 | 10/11; +3.5813% | 5/10; +0.8440% | **−1.2776%** (n=9) |
| ≥2 categories + T2 | 10/12; +2.6855% | 4/11; **−0.3871%** | **−2.4196%** (n=10) |

The H10 signal mean and hit rate weaken materially; INTC is influential. But the same-date **control-relative gaps remain positive**: news +5.5180 pp and multi-category +3.8151 pp, because controls perform worse. Even after excluding INTC, those date gaps remain +3.2574 and +2.3283 pp. “The effect disappears at H10” is therefore too imprecise: positive mean SPY performance deteriorates while the selected control-relative comparison survives.

To avoid comparing different maturity populations, pair the H5 and H10 records. News has ten pairs: paired H5 mean +2.6325%, H10 +0.8440%, with five of nine paired H5 responders still positive. Multi-category has eleven pairs: paired H5 mean +2.6169%, H10 −0.3871%, with four of nine H5 responders still positive. Absolute terminal returns worsen between H5 and H10 for six news pairs and eight multi-category pairs.

H21 contains only one qualifying observation, TSLA, with SPY excess +8.2855%. The remaining ten news and eleven multi-category H21 outcomes are unavailable at this frozen vintage. They are not observed failures. This sample cannot establish H21 persistence or decay, and no H1 result can be supplied from it.

Existing path fields give partial support for a cleaner **close-based** path:

| H5 group | Mean close MFE | Controls | Mean SPY-relative close MAE | Controls |
|---|---:|---:|---:|---:|
| News + T2 | +3.8126% | +2.4970% | −1.3598% | −3.0805% |
| ≥2 categories + T2 | +3.3129% | +2.5118% | −0.9495% | −3.1016% |

The [frozen grader](https://github.com/mastermindx-market-intelligence/macro/blob/2f2feec4851b45636f63a48ec61e6f0b02b8118a/engine/grading.py) enters at the next bar's close and measures future closes through entry index +H. Its MFE is close-based, not intraday high-based. Its minimum return from entry is not a running peak-to-trough drawdown. The stored sample does not provide a full aligned OHLC sequence, frozen breakout level or barrier ordering. Consequently clean liftoff, failed breakout and complete reversal/drawdown behavior are **not historically established**. The prospective protocol supplies explicit, separate definitions.

## 6. Strongest false lead and July comparability

Generic “more categories is always better” is the strongest apparent false lead. First-any-tier multi-category selection gives 7/11 H5 SPY wins but mean SPY excess only **+0.00146%**, effectively zero at this precision, with mean absolute return −0.00599%. Wins alone conceal the size of losses.

For T1 + ≥2 categories, repeated rows give **2/5 SPY wins**, mean **−1.1786%**. First-any-tier then T1 gives **0/2**, mean **−2.5375%**. Actual first-T1 then multi-category gives **1/3**, mean **−1.2959%**; the extra record is TSLA Aug27. Thus the direction of the T1 null survives correcting the selector, but the literal 0/2 does not describe first-T1 selection. These are small adverse discoveries, not definitive evidence that all T1 interactions fail.

The July confluence-era T2+news sample has five rows from AMZN, MSFT, PFE and WMT: **1/5 SPY wins**, mean **−1.0841%**. It has 3/5 absolute and sector wins. None of those issuers is a semiconductor company, so a semiconductor-specific story does not explain this sample's composition. Keep it as adverse context.

Do not blindly pool July with v3. Source coverage, selection/ranking/sector caps, absolute session anchors and adjusted-price handling changed across the documented eras. The [upstream reaudit](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/research/prophet_v4/PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md) and this script preserve era-specific denominators. July is neither ignorable because it is inconvenient nor a clean identical-protocol negative replication.

## 7. News is attention; source roots and economic quality are unmeasured

The [historical news code](https://github.com/mastermindx-market-intelligence/macro/blob/74e8f45060e815a2cb7c515ae09f258919ab9da2/engine/financial_news.py) builds a retained-item count, capped at six items, and the downstream burst flag is `n_recent >= 3`. Compact output shows only the top four. This is a breadth/count threshold after upstream filtering, not necessarily a statistically abnormal arrival rate and not independent-root count. Sentiment is separate; source, timestamp precision, root and novelty lineage can be lost in the compact representation. Provider/ticker absence is not a verified lack of events.

### NVDA 6/0/0 reproduces, with an important missingness distinction

At [snapshot 74e8f45](https://github.com/mastermindx-market-intelligence/macro/blob/74e8f45060e815a2cb7c515ae09f258919ab9da2/site/news/by_ticker.json), `$.tickers.NVDA` has six recent items, zero positive, zero negative, neutral aggregate lean and zero strength. The [full archive](https://github.com/mastermindx-market-intelligence/macro/blob/74e8f45060e815a2cb7c515ae09f258919ab9da2/site/news/financial.json) has as-of Sep25 and fetch time Sep26 05:36:12Z. All six underlying sentiment fields are **null**, all summaries empty, all event fields null and all centrality fields incidental. Sources are two Barron's and four Investor's Business Daily entries.

Therefore 0/0 means **zero classified positive/negative items**, not six confidently neutral articles. The archived topics mix issuer news, technical/political context, another company's business and a broad roundup. These archive descriptions do not independently verify the underlying corporate claims. The after-hours fetch and compact Sep26 stamp cannot be substituted for a Sep25 intraday availability receipt.

### Decision-changing archive probes

The [Sep10 news snapshot](https://github.com/mastermindx-market-intelligence/macro/blob/3119171478a7cd9cd851687cf24e8bf0c271cdc4/site/news/financial.json), fetched 07:23:01Z, records a healthier old feed retained when the replacement covered only 15 rather than 1,027 tickers. A refreshed wrapper date therefore does not ensure fresh contents.

- INTC has three items: an industry market-size promotion, a Super Micro-centered recommendation, and Nvidia-focused commentary with a backdating flag. These can create an attention count without proving a new Intel economic fact.
- PRIM has five items: two Primoris lawsuit-deadline notices, a Bloom Energy-centered multi-company notice, and two Argan discussions. Those are mixed issuer relevance and potentially repeated roots. The audit does not infer new litigation materiality or the truth of allegations without filings and exact-cut source evidence.

These are one-date archival probes, not outcome-selected relabeling of all prior observations. Exact item locators, archive URLs, clocks and flags are reproducible in `PB_D_SOURCE_AUDIT.json`. Historical economic/root labels stay unknown.

The smart-money archive also demonstrates a revision risk. Between the [Sep10 snapshot](https://github.com/mastermindx-market-intelligence/macro/blob/3119171478a7cd9cd851687cf24e8bf0c271cdc4/site/factordata/smartmoney.json) and [Oct5-built snapshot](https://github.com/mastermindx-market-intelligence/macro/blob/2f2feec4851b45636f63a48ec61e6f0b02b8118a/site/factordata/smartmoney.json), identical TSLA holdings receive changed manager grades: D1 A→B and Polen B→C. Polen crosses the A/B eligibility boundary; D1 remains eligible. This proves constituent historical quality can change under later reconstruction; it does **not** prove the overall TSLA boolean flips or authorize backdating Sep10 grades to Aug21.

Legacy SUE construction additionally has a truthiness/sign issue and synthetic `period_end + 60` availability fallback; the compact ownership boolean loses detailed filing/availability clocks, as documented in Sections 6 and 17.1 of the [pinned source reaudit](https://github.com/mastermindx-market-intelligence/macro/blob/770918cb266b5d884978e31d61670b4efd789eaf/research/prophet_v4/PROPHET_NVDA_PRO_REAUDIT_2026-10-06.md). The [grade reconstruction](https://github.com/mastermindx-market-intelligence/macro/blob/2f2feec4851b45636f63a48ec61e6f0b02b8118a/scripts/grade_us_board.py) can select a later snapshot for a board as-of date. These are concrete reasons to distinguish economic occurrence, publication, local observation, annotation and board-generation times. New research requires exact-cut source/claim snapshots rather than today's richer reconstruction.

## 8. Answers to the ten research questions

| Question | Adjudication |
|---|---|
| Attention or sentiment? | The feature is a retained-item count. NVDA has six null sentiments; sentiment is not required. Information novelty is not certified. |
| Does economic quality add value? | Unknown: no audited historical labels or admissible expectation/root joins support that estimate. |
| Does independence matter? | Unknown empirically; current three category booleans do not measure it. Freeze originating-root semantics prospectively. |
| Survives issuer deduplication? | Counts do: news first qualifying 6/7; first-T2 multi-category 5/5. Precision and selection remain weak. |
| Survives controls? | Positive date and date/sector gaps; strict entry-status support falls to two rows. Full technical/source-quality control is untested. |
| Is H5 special? | H10 mean/hit-rate weaken; H10 control-relative gaps remain positive. H21 n=1 and H1 absent prevent broader claims. |
| One or two names? | ADM/PRIM dominate rows, but H5 does not collapse under any one-issuer omission. H10 is sensitive to INTC. |
| Is T2 the right state? | Plausible fresh-acceptance mechanism and adverse T1/generic discoveries. No adequately powered head-to-head establishes unique T2 superiority. |
| Cleaner liftoff? | Favorable descriptive close-MFE/relative-close-MAE; intraday liftoff, failed breakout and full drawdown are unmeasured. |
| How much future evidence? | Hundreds of independently identified, source-qualified events under a fixed prospective protocol; see the power and prereg files. |

The bounded commission is complete as reproduction, bias audit and frozen zero-authority design. PB-G should next make existing owners' clock/root/claim receipts reviewable. It should not build a bullishness score, rescore Prophet, alter T2/entry, create a second event store, or claim validated “independent evidence” from these legacy booleans.
