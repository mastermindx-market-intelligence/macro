# PB-A — Policy behavior baseline: method and findings

**Research date:** October 7, 2026  
**Operation:** `PB-A-POLICY-BEHAVIOR-BASELINE-20261007`  
**Status:** Bounded PB-A research return complete; retrospective feasibility pilot; research authority only.  
**Parent:** [Macro PR #8560](https://github.com/mastermindx-market-intelligence/macro/pull/8560). The broader W1 program and PB-G integration remain incomplete.

## 1. Finding and decision

This casebook supports disciplined interpretation of policy instruments, but it does **not establish incremental forecasting value from revealed-preference inference**. The literal model and the deliberately minimal action-and-constraint model make identical predictions on all eight primary episodes where both forecast. Their matched accuracies are 4/8 at one month, 7/8 at three months and 5/8 at six months. Differences between their headline accuracies come from different coverage, not superior predictions on the same episodes.

Mechanical inversion is a poor default on the covered sample: it is correct on 0/5 episodes at each horizon. Those five cases all contain upward rate guidance; the result does not estimate the usefulness of inversion across a representative mix of hawkish and dovish communication. At one month, four of those five outcomes are unchanged rates, so the literal forecast also performs poorly. A no-change comparator is essential.

The action-persistence model is horizon dependent. On its eleven primary episodes, the always-HOLD comparator beats it 10/11 to 6/11 at one month. Action persistence with a conventional-floor constraint wins 10/11 to 6/11 at three months and 7/11 to 3/11 at six months. These are small, selected historical comparisons. They establish neither a trading edge nor a general reaction function.

An explicitly separate challenge case, the June 14, 2023 FOMC pause, shows why action and forward guidance must remain separate: persistence predicts HOLD, whereas literal guidance predicts UP. HOLD is correct at one month; UP is correct at three and six months. The challenge was deliberately selected to seek a failure of persistence, before this pilot was scored, and is excluded from every primary result.

**The full commissioned M2 remains untested.** Here `M2` in the machine-readable pilot means **M2-min**, a narrow proxy using a new rate decision and one conventional-floor assumption. The commission's richer M2 includes repeated choices after visible costs, feasible alternatives, selective relief and contemporary market pricing. A synchronized archived pricing panel and a comparable adverse-cost/repeated-choice panel were not reconstructed. Qualitative evidence for these mechanisms is recorded, but it is not converted into probabilities after seeing outcomes. The data-deficiency branch of the PB-A stop condition is therefore explicit for the full model and for the unscored market targets.

**Recommendation for PB-G:** receive the casebook as research context and a source/action audit reference. Keep forecasting promotion pending a separately frozen, broader evaluation in which rich M2 must beat literal guidance, institutional baselines and action-only ablations on the same cases. This return makes no change to Policy Watch, Policy Intel, RIC, rank, gate, size or a live consumer.

All counts and scores in this report are computed from [PB_A_BASELINE_PILOT.json](PB_A_BASELINE_PILOT.json), with per-episode outcomes in [PB_A_OUTCOMES.json](PB_A_OUTCOMES.json). The [casebook](PB_A_CASEBOOK.json) contains source-level support and competing explanations.

## 2. Commission, scope and immutable design

The direct commission is [PB_A_POLICY_BEHAVIOR_BASELINE_PRO.md](https://github.com/mastermindx-market-intelligence/macro/blob/7abc3dc596c5a6463effb37422bf9bd34bbdf1ba/research/policy_behavior/handoffs/PB_A_POLICY_BEHAVIOR_BASELINE_PRO.md). Protected procedure was read at Mastermind commit `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`; the parent research packet was read at Macro commit `ee86db2c832c73a36837c1240df871700340d6da`. The specific handoff requests at least twenty U.S. Fed/Treasury episodes and a bounded baseline pilot. The parent W1 preregistration asks for forty to sixty cross-family episodes and reconstructed expectations before full W1 completion. This return satisfies the narrower research-return boundary; it does not certify completion of W1 or silently replace its wider design.

The research branch began from the observed current Macro main, `309f88c6c209bdc9fb611de0018fb619d9351b37`, and writes only under `research/policy_behavior/pro_returns/PB-A/`. All code here is local research analysis; no application or production implementation is introduced. Repository publication is a draft research return, not a merge or integration receipt.

The methodological sequence is recoverable from immutable commits:

1. [Protocol commit `99253212652ba7d1248a587c249da44ec6e3b9b6`](https://github.com/mastermindx-market-intelligence/macro/commit/99253212652ba7d1248a587c249da44ec6e3b9b6) freezes the 24-event selection and model/target rules. Protocol timestamp: `2026-10-07T02:50:36Z`.
2. Implementation clarifications at `2026-10-07T02:57:53Z` resolve month arithmetic, source precision, current-stance versus future-guidance coding, anchor semantics and comparisons without changing the protocol's model families. The actual decision coding was frozen at `2026-10-07T03:05:11Z`.
3. [Forecast commit `8799d065178b7637bc91a0e69696df8b9ef763f6`](https://github.com/mastermindx-market-intelligence/macro/commit/8799d065178b7637bc91a0e69696df8b9ef763f6) contains the decision-only casebook, strict input file, model code and frozen forecasts. The four design/code files and forecast file were read back exactly from that commit before the outcome join was run.
4. Outcomes were then joined. Later changes to the casebook add outcomes, explicit schema aliases, missing-control disclosures, a corrected joint-agency lineage and a BTFP quarantine explanation. The decision inputs, scorer, protocol, clarifications and forecast artifact remain byte-identical to the forecast commit. A subsequent endpoint sensitivity is plainly labeled post-score exploratory.

This sequence prevents the scoring process from rewriting forecasts. It does **not** make the exercise prospectively preregistered or historically outcome-blind. The researchers know the history; source selection and semantic coding can still carry retrospective judgment.

## 3. Acceptance and source-time coverage

| Requirement | Result | Scope of the result |
|---|---:|---|
| At least 20 U.S. episodes | 24 primary, plus 1 separate challenge | Fixed purposive selection; no prevalence claim |
| At least 5 alignment cases | 17 | Includes alignment on current rate stance or announced operational plan |
| At least 5 divergence/tension cases | 10 | Often different instruments, magnitudes or horizons; not deception labels |
| At least 5 unresolved-intent cases | 24 | Private motive is never a known predictor input |
| At least 5 strong institutional explanations | 24 | An institutional explanation competes; it is not proven to be the exclusive motive |
| Source clock precision | 17 minute, 7 date-only primary headlines | Minute means documentary release minute, not observed server timing |
| Episode cut precision | 15 intraday cuts, 9 next-local-midnight cuts | Conservative date bounds retained where needed |
| Registered source records | 84 distinct URL records | Includes attachments, clock archaeology, prior context and excluded material |
| Admitted primary source records | 56 | Only the case-specific admitted sources enter certified decision narratives |
| Frozen comparisons | M0, M1, M2-min, C0, C1 | Rich M2 and market prediction have named deficiencies |
| Adverse comparison | June 2023 challenge | M0 beats M2-min at 3m and 6m; challenge never pooled |
| Outcome isolation | Verified | Four-key predictor, source-time validation and immutable hash/content checks |

The category counts overlap by design. For example, the May 2024 FOMC rate hold aligns with near-term rate guidance while a slower balance-sheet runoff creates a distinct cross-instrument tension. It would be wrong to force those observations into one honesty label.

### What “PIT-certified” means here

Each row has `pit_certified=true` with an explicit **historical documentary source-time** certificate. It certifies that the reviewed official document states the relevant fact at a supported historical date/minute before the declared cut, subject to retained version and publication caveats. It does not certify original historical served bytes, exact first server availability, actual loan settlement, market expectations, exclusive intent or a causal effect.

Minute-only evidence is conservatively bounded at the end of the displayed minute. Date-only evidence has a New York civil-day interval and is admitted at the next midnight. The timestamp `00` seconds represents normalization, not measured precision. A date-only headline has a null exact `first_public_evidence_utc` plus an explicit interval. The overnight cut remains a modeling choice, including its additional same-day public information; it is not a claim that the release first appeared at midnight.

The source register preserves original helper annotations and adds canonical clock/role fields. Canonical fields govern admission. A registered document is not automatically a decision input. The Federal Reserve System, Treasury and the FDIC are institutional umbrella origins; the March 2023 joint statement has all three origins and remains one joint document, not three independent observations. Separate official documents from the same institution, different formats and linked attachments are correlated evidence. There is no syndication-count multiplier.

### Material source repairs

- **October 11, 2019 reserve operations:** the original [timed PDF](https://www.federalreserve.gov/monetarypolicy/files/monetary20191011a1.pdf) supports the 11 a.m. EDT clock. A later-updated HTML page and a date-only New York Fed operating detail cannot create extra intraday information. A maintenance directive preserving the existing target is not a new rate hold decision.
- **March 3, 2020 emergency cut:** a conflicting historical index label is retained as archaeology. The original timed statement independently supports the decision clock. The current [Fed policy history](https://www.federalreserve.gov/monetarypolicy/openmarket.htm) notes a later correction of the effective date to March 4; that correction belongs in the outcome/effective-date ledger, not in historical predictive information.
- **March 23, 2020 facility terms, August 2020 framework attachment and March 2023 BTFP terms:** five parent-linked attachments are quarantined from the certified decision block. Their headline claims survive through independently timed official releases. Detailed credit-rating, haircut, covenant, loan-pricing, recourse, eligibility and deadline claims are not given invented clocks.
- **August 2020 strategy:** the dated [2020 framework PDF](https://www.federalreserve.gov/monetarypolicy/files/FOMC_LongerRunGoals_202008.pdf) is retained for version identity; the generic mutable strategy file currently resolves to later text and is not used as 2020 evidence.
- **Jackson Hole 2022:** the prepared speech's release-on-delivery instruction supports a documentary release minute. It does not prove that every passage had been spoken by the cut.
- **November 2020 facility letter:** Powell's November 20 reply remains outside the November 19 decision block. It cannot explain what was knowable at the earlier cut.
- **May 2024 Treasury buybacks:** the tentative schedule explicitly dates publication to May 1. The result PDF explicitly dates immediate release to May 29. The `174000` filename component is an operation-time association, not a publication clock. Accepted offers are an executed allocation; completed cash settlement is not proved.

## 4. Episode inventory

Forecasts below are decision-time codes; outcomes appear afterward. HOLD means unchanged target at the specified endpoint, not “nothing happened.” ABSTAIN has no probability vector. Every full ID, clock interval, action status, source reference, beneficiary, alternative and competing hypothesis is in the JSON.

| Event date | Episode and focal official source | Cut UTC | First-public clock | M0 / M1 / M2-min | Later net direction, 1m / 3m / 6m |
|---|---|---|---|---|---|
| 2018-12-19 | [December rate hike](https://www.federalreserve.gov/newsevents/pressreleases/monetary20181219a.htm) | 2018-12-19 19:05:00Z | 2018-12-19 19:00Z | UP / DOWN / UP | HOLD / HOLD / HOLD |
| 2019-01-30 | [Patience and normalization flexibility](https://www.federalreserve.gov/newsevents/pressreleases/monetary20190130a.htm) | 2019-01-30 19:05:00Z | 2019-01-30 19:00Z | HOLD / ABSTAIN / HOLD | HOLD / HOLD / HOLD |
| 2019-07-31 | [July rate cut](https://www.federalreserve.gov/newsevents/pressreleases/monetary20190731a.htm) | 2019-07-31 18:05:00Z | 2019-07-31 18:00Z | ABSTAIN / ABSTAIN / DOWN | HOLD / DOWN / DOWN |
| 2019-10-11 | [Reserve-management purchases](https://www.federalreserve.gov/monetarypolicy/files/monetary20191011a1.pdf) | 2019-10-11 15:05:00Z | 2019-10-11 15:00Z | ABSTAIN / ABSTAIN / ABSTAIN | DOWN / DOWN / DOWN |
| 2020-03-03 | [Emergency 50bp cut](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm) | 2020-03-03 15:05:00Z | 2020-03-03 15:00Z | ABSTAIN / ABSTAIN / DOWN | DOWN / DOWN / DOWN |
| 2020-03-15 | [Cut to conventional floor](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm) | 2020-03-15 21:05:00Z | 2020-03-15 21:00Z | HOLD / ABSTAIN / HOLD | HOLD / HOLD / HOLD |
| 2020-03-23 | [Purchases and credit facilities](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323b.htm) | 2020-03-23 12:05:00Z | 2020-03-23 12:00Z | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2020-04-09 | [Emergency-credit expansion](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200409a.htm) | 2020-04-10 04:00:00Z | 2020-04-09 12:30Z | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2020-08-27 | [Average-inflation framework](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200827a.htm) | 2020-08-27 13:15:00Z | 2020-08-27 13:10Z | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2020-11-19 | [Treasury facility-expiry letter](https://home.treasury.gov/news/press-releases/sm1190) | 2020-11-20 05:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2021-11-03 | [Purchase taper](https://www.federalreserve.gov/newsevents/pressreleases/monetary20211103a.htm) | 2021-11-03 18:01:00Z | 2021-11-03 18:00Z | HOLD / ABSTAIN / HOLD | HOLD / HOLD / UP |
| 2021-12-15 | [Accelerated taper](https://www.federalreserve.gov/newsevents/pressreleases/monetary20211215a.htm) | 2021-12-15 19:01:00Z | 2021-12-15 19:00Z | ABSTAIN / ABSTAIN / HOLD | HOLD / HOLD / UP |
| 2022-03-16 | [Rate liftoff](https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm) | 2022-03-16 18:01:00Z | 2022-03-16 18:00Z | UP / DOWN / UP | HOLD / UP / UP |
| 2022-06-15 | [75bp rate hike](https://www.federalreserve.gov/newsevents/pressreleases/monetary20220615a.htm) | 2022-06-15 18:01:00Z | 2022-06-15 18:00Z | UP / DOWN / UP | HOLD / UP / UP |
| 2022-08-26 | [Jackson Hole guidance](https://www.federalreserve.gov/newsevents/speech/powell20220826a.htm) | 2022-08-26 14:01:00Z | 2022-08-26 14:00Z | UP / DOWN / ABSTAIN | UP / UP / UP |
| 2023-03-12 | [BTFP and depositor protection](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230312a.htm) | 2023-03-13 04:00:00Z | 2023-03-12 22:15Z | ABSTAIN / ABSTAIN / ABSTAIN | UP / UP / UP |
| 2023-03-22 | [Bank-stress rate hike](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a.htm) | 2023-03-22 18:01:00Z | 2023-03-22 18:00Z | UP / DOWN / UP | HOLD / UP / UP |
| 2023-05-03 | [Treasury buyback planning](https://home.treasury.gov/news/press-releases/jy1460) | 2023-05-04 04:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / UP / UP |
| 2023-06-14 | [June pause challenge (separate)](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230614a.htm) | 2023-06-14 18:01:00Z | 2023-06-14 18:00Z | UP / DOWN / HOLD | HOLD / UP / UP |
| 2023-08-02 | [Coupon issuance increases](https://home.treasury.gov/news/press-releases/jy1671) | 2023-08-03 04:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2023-11-01 | [Slower long-coupon increases](https://home.treasury.gov/news/press-releases/jy1864) | 2023-11-02 04:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2024-01-31 | [Coupon plateau guidance](https://home.treasury.gov/news/press-releases/jy2062) | 2024-02-01 05:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / HOLD |
| 2024-05-01 | [FOMC QT slowdown](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240501a.htm) | 2024-05-01 18:01:00Z | 2024-05-01 18:00Z | HOLD / ABSTAIN / HOLD | HOLD / HOLD / DOWN |
| 2024-05-01 | [Treasury buyback launch plan](https://home.treasury.gov/news/press-releases/jy2315) | 2024-05-02 04:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / DOWN |
| 2024-05-29 | [First buyback allocation](https://www.treasurydirect.gov/instit/annceresult/press/preanre/2024/BBR_20240529174000.pdf) | 2024-05-30 04:00:00Z | Date only; interval in JSON | ABSTAIN / ABSTAIN / ABSTAIN | HOLD / HOLD / DOWN |

The first-public clock and the decision cut differ intentionally. In particular, the May 3, 2023 Treasury row uses a May 4 midnight local cut. The FOMC hike announced on May 3 is already known at that cut, so the anchor is 5.00–5.25%, although the change becomes effective May 4. The Treasury announcement itself still has `has_new_rate_decision=false`.

## 5. Frozen baseline rules and outcome definitions

### Models

| Model | Frozen rule | Material limit |
|---|---|---|
| M0 literal | Code a clean focal forward rate implication UP, DOWN or HOLD; otherwise abstain | Conditional and vague language is not an unconditional timed promise |
| M1 inversion | Exchange UP and DOWN from M0; abstain on HOLD or ABSTAIN | HOLD has two possible opposites, so no arbitrary inverse is chosen |
| M2-min | Persist the direction of a new focal rate decision; a formal hold predicts HOLD; a cut to 0–0.25% predicts HOLD under a conventional-floor assumption | This is a minimal action-plus-one-constraint proxy, not the full revealed-preference model |
| C0 no change | Always HOLD when a valid public rate anchor can be reconstructed | Reports the substantial short-horizon hold base rate |
| C1 action only | Same rate-decision persistence as M2-min without the floor exception | Isolates the sole constraint added to the quantitative model |

The pure predictor accepts exactly four scalar fields: focal rhetorical direction, whether there is a new focal rate decision, its direction, and the newly decided upper target bound. It cannot read the outcome file, market history, qualitative hypotheses, beneficiary text, cost annotations or the full casebook. The broader source list accompanies the input for audit and clock validation, not as a hidden text-model input.

M0 uses focal communication. A prior rate forecast does not silently become new rate guidance in a facility announcement or Treasury refunding. An inflation objective is not an inflation forecast or a rate cut. “Patient” and conditional no-cut language receive a stated near-term HOLD interpretation, with semantic uncertainty retained. December 2021's conditional rate hold and annual projected increases have different horizons, so the mixed rate-path packet is ABSTAIN. October 2019's no-change-in-current-stance statement is also ABSTAIN for a future-rate target. No direction was chosen from subsequent market returns.

A clean coded path is applied mechanically to 1m, 3m and 6m. This deliberately simple extrapolation is a baseline assumption. It does not mean an official made three calendar promises. Negative rates are not treated as legally impossible; M2-min's zero-range exception is an explicit conventional operating assumption. No liquidity facility, QT slowdown, Treasury buyback or speech is automatically converted into a Fed rate decision.

### Policy targets

**Primary:** direction of the effective target midpoint at the end of the horizon date relative to the most recently **decided and publicly known** target at the cut. This absorbs an already-announced decision even when its effective date is tomorrow. Seven primary cases have an already-public latest target change before its effective date; the independent audit reconciles all anchors.

**Secondary:** the first nonzero target change publicly decided strictly after the cut and effective by the horizon, or HOLD if no such change occurs. This is the first subsequent **change**, not the first FOMC meeting. Net movement and first change could diverge after a reversal. They happen to agree in all 72 primary episode/horizon observations here, and are not counted as independent validation.

Horizon arithmetic uses the cut's New York calendar date plus one, three or six months, clamping to the last valid day of the destination month. An overnight cut therefore uses the next civil date. Endpoints are the effective daily range at the end of that date. Missing exact policy dates are not silently carried or replaced by zero.

The outcome sources are FRED's daily [DFEDTARL](https://fred.stlouisfed.org/series/DFEDTARL) and [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU), reconciled with 23 official decision/effective-date changes during 2018–2024. The downloaded window is 2018-01-01 through 2025-01-10. Data are outcome-time historical measurements retrieved in 2026, not claimed historical input vintages. Public URLs, retrieval records and SHA-256 identities are retained under `outcome_inputs/`.

### Probabilities and score interpretation

Every non-abstaining forecast assigns probability 0.6 to its coded class and 0.2 to each alternative, in DOWN/HOLD/UP order. This is a fixed research convention, not estimated confidence. Brier is the sum of three squared errors, range 0–2; log loss is negative natural log probability of the outcome. Proper scoring rules are useful when probabilities have meaning; the general rationale is described by [Gneiting and Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).

For accuracy `a` in this fixed-confidence pilot, Brier = `1.04 − 0.8a` and negative log loss = `log(5) − a log(3)`. These are algebraically linked summaries, not three independent confirmations. The 0.4/0.6/0.8 probability sweep changes score magnitudes but cannot change the ranking of fixed directions on a fixed intersection. Reliability buckets are reported; a calibration slope is unavailable and no fitted calibration is claimed.

## 6. Quantitative results

### Coverage and own-sample accuracy

The following table is descriptive. Different rows have different samples and cannot be read as a league table.

| Model | Covered per horizon | Coverage | 1 month correct | 3 months correct | 6 months correct |
|---|---:|---:|---:|---:|---:|
| M0 literal | 9/24 | 37.5% | 5/9 (55.6%) | 8/9 (88.9%) | 6/9 (66.7%) |
| M1 inversion | 5/24 | 20.8% | 0/5 (0.0%) | 0/5 (0.0%) | 0/5 (0.0%) |
| M2-min actions + floor | 11/24 | 45.8% | 6/11 (54.5%) | 10/11 (90.9%) | 7/11 (63.6%) |
| C0 always HOLD | 24/24 | 100.0% | 20/24 (83.3%) | 15/24 (62.5%) | 10/24 (41.7%) |
| C1 action only | 11/24 | 45.8% | 5/11 (45.5%) | 9/11 (81.8%) | 6/11 (54.5%) |

At 1m, the 24 primary outcomes comprise 20 HOLD, 2 UP and 2 DOWN. At 3m they comprise 15 HOLD, 6 UP and 3 DOWN. At 6m they comprise 10 HOLD, 8 UP and 6 DOWN. All eleven M2-min inputs are new focal rate decisions; its other thirteen primary episodes abstain. M0 has four HOLD and five UP signals; none is a clean focal DOWN signal in this selection. M1 therefore predicts DOWN in every one of its five covered cases.

### Comparisons on the same episodes

| Matched comparison | Same episodes per horizon | 1m correct, left vs right | 3m correct, left vs right | 6m correct, left vs right |
|---|---:|---:|---:|---:|
| M0 literal vs M1 inversion | 5 | 1/5 vs 0/5 | 4/5 vs 0/5 | 4/5 vs 0/5 |
| M0 literal vs M2-min actions + floor | 8 | 4/8 vs 4/8 | 7/8 vs 7/8 | 5/8 vs 5/8 |
| M2-min actions + floor vs C0 always HOLD | 11 | 6/11 vs 10/11 | 10/11 vs 6/11 | 7/11 vs 3/11 |
| M2-min actions + floor vs C1 action only | 11 | 6/11 vs 5/11 | 10/11 vs 9/11 | 7/11 vs 6/11 |

The M0–M2-min equality is structural in this casebook: their directions coincide on the entire eight-case intersection, at every horizon. Neither the score type nor a probability adjustment can reveal an incremental M2 advantage there. M2-min's additional primary coverage is July 2019, March 3, 2020 and December 2021. M0's additional primary coverage is Jackson Hole 2022. The 90.9% versus 88.9% three-month own-sample accuracies do not compare equivalent populations.

The common intersection of M0, M1 and M2-min contains only four episodes: December 2018, March 2022, June 2022 and March 2023. At 1m all four truths are HOLD and all three models score 0/4. At 3m and 6m, the truths are one HOLD and three UP: M0 and M2-min score 3/4 and M1 scores 0/4. Requiring all models to speak therefore selects a particular subset of communication; it does not solve selection bias by itself.

The only difference between M2-min and C1 is March 15, 2020. The conventional-floor assumption avoids mechanically forecasting another cut after the target reaches 0–0.25%. It adds exactly one correct case at each horizon, or 9.1 percentage points on eleven cases. Dropping the pandemic regime removes that entire advantage. Literal state-contingent hold guidance already captures the same case.

### Probabilistic score summaries

The denominators are each model's own covered cases above. Use the exact pairwise sections of the JSON for matched score comparisons.

| Model | Horizon | Brier, lower is better | Negative log loss, lower is better |
|---|---:|---:|---:|
| M0 literal | 1m | 0.5956 | 0.9991 |
| M0 literal | 3m | 0.3289 | 0.6329 |
| M0 literal | 6m | 0.5067 | 0.8770 |
| M1 inversion | 1m | 1.0400 | 1.6094 |
| M1 inversion | 3m | 1.0400 | 1.6094 |
| M1 inversion | 6m | 1.0400 | 1.6094 |
| M2-min actions + floor | 1m | 0.6036 | 1.0102 |
| M2-min actions + floor | 3m | 0.3127 | 0.6107 |
| M2-min actions + floor | 6m | 0.5309 | 0.9103 |
| C0 always HOLD | 1m | 0.3733 | 0.6939 |
| C0 always HOLD | 3m | 0.5400 | 0.9228 |
| C0 always HOLD | 6m | 0.7067 | 1.1517 |
| C1 action only | 1m | 0.6764 | 1.1101 |
| C1 action only | 3m | 0.3855 | 0.7106 |
| C1 action only | 6m | 0.6036 | 1.0102 |

### Chronological reporting and dependence

| Reporting slice | Model | Covered | 1m correct | 3m correct | 6m correct |
|---|---|---:|---:|---:|---:|
| DEVELOPMENT | M0 literal | 7/15 | 4/7 (57.1%) | 6/7 (85.7%) | 5/7 (71.4%) |
| DEVELOPMENT | M1 inversion | 4/15 | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) |
| DEVELOPMENT | M2-min actions + floor | 9/15 | 5/9 (55.6%) | 8/9 (88.9%) | 6/9 (66.7%) |
| CHRONOLOGICAL_REPORT | M0 literal | 2/9 | 1/2 (50.0%) | 2/2 (100.0%) | 1/2 (50.0%) |
| CHRONOLOGICAL_REPORT | M1 inversion | 1/9 | 0/1 (0.0%) | 0/1 (0.0%) | 0/1 (0.0%) |
| CHRONOLOGICAL_REPORT | M2-min actions + floor | 2/9 | 1/2 (50.0%) | 2/2 (100.0%) | 1/2 (50.0%) |

The pre-2023 development slice has fifteen primary events. The 2023–2024 reporting slice has nine, but only two are covered by M2-min and only one by M1. No training optimization is performed, and the later slice is retrospectively reconstructed rather than an unseen holdout. Its nominal 100% three-month M2-min accuracy is two successes, not a validation result.

Uncertainty is clustered by four frozen historical regimes: 2018–2019 normalization, 2020 pandemic, 2021–2022 inflation and 2023–2024 restrictive policy/liquidity. For each matched contrast the script enumerates every `K^K` whole-regime draw with replacement, up to 256 draws, and reports central 95% descriptive intervals and leave-one-regime-out results. The intervals below are **not population confidence intervals**.

| Matched contrast (accuracy, percentage points) | Regimes | 1m difference [descriptive 95% interval] | 3m | 6m |
|---|---:|---:|---:|---:|
| M0 minus M1 | 3 | +20.0 [+0.0, +30.2] | +80.0 [+21.7, +100.0] | +80.0 [+21.7, +100.0] |
| M0 minus M2 | 4 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| M2 minus C0 | 4 | -36.4 [-61.5, +11.1] | +36.4 [+9.1, +50.0] | +36.4 [+9.1, +50.0] |
| M2 minus C1 | 4 | +9.1 [+0.0, +33.3] | +9.1 [+0.0, +33.3] | +9.1 [+0.0, +33.3] |

M0–M2-min remains zero under every regime deletion because the predictions are identical. M2-min minus C0 is negative at 1m under every single-regime deletion and positive at 3m/6m; the full draw interval at 1m still crosses zero. That pattern describes this selected set, not generalizable significance. M0–M1 uses only three represented regimes. Events share policy cycles, pandemic shocks and market horizons; the two May 1, 2024 rows and the May 29 buyback row are especially dependent. Seventy-two episode/horizon rows are not seventy-two independent experiments, and horizons are never pooled.

### Post-score calendar sensitivity

An independent diagnostic held forecasts, sample, cuts, anchors and probabilities fixed and shifted the policy endpoints by minus or plus seven calendar days. It is clearly marked `POST_SCORE_EXPLORATORY`, excluded from the primary score and not presented as additional validation. Three truth labels change:

| Episode | Horizon and shift | Original endpoint → shifted endpoint | Change in truth |
|---|---|---|---|
| January 30, 2019 FOMC | 6m, +7d | July 30 → August 6 | HOLD → DOWN |
| December 15, 2021 taper | 3m, +7d | March 15 → March 22, 2022 | HOLD → UP |
| August 26, 2022 Jackson Hole | 1m, −7d | September 26 → September 19 | UP → HOLD |

M0–M2-min remains tied under every shift at every horizon. Their matched correct counts fall together from 5/8 to 4/8 at 6m under +7 days. M2-min minus C0 remains minus four correct cases at 1m and plus four at 3m/6m. The one-case M0 advantage over M1 at 1m disappears under −7 days. Nine other shifted endpoints cross rate changes that alter magnitude but retain the same direction. This check quantifies calendar sensitivity; it does not validate alternative wording, cuts, event selection or meeting-aligned targets. See [PB_A_ENDPOINT_SENSITIVITY.json](PB_A_ENDPOINT_SENSITIVITY.json).

## 7. What the cases explain, and what they leave open

### Policy-rate direction and instrument choice are separate

The [October 2019 reserve-management statement](https://www.federalreserve.gov/monetarypolicy/files/monetary20191011a1.pdf) explicitly connects bill purchases and repo operations to reserve control. Its existing target-range directive is not a new rate hold. The appropriate inference is an operating-framework choice with an institutional explanation. Treating any balance-sheet expansion as a clean future rate cut would require an extra transmission rule, which was not frozen here.

On [May 1, 2024](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240501a.htm), the FOMC held the target at 5.25–5.50% and announced a future reduction of the Treasury runoff cap from $60 billion to $25 billion per month. A lower ceiling on future runoff is neither a $35 billion executed injection nor a policy-rate cut. Rate guidance and balance-sheet implementation can point to different marginal changes without being contradictory. The later six-month cut is recorded as an outcome, not used to rename the May decision.

The relevant falsifier for the instrument-separation interpretation would be contemporary evidence that broad rate easing was an explicitly necessary component of the liquidity/operational action, or a reproducible rule showing that the separate instrument reliably changes the future policy path beyond what guidance and the public policy state already predict. Later asset gains alone are insufficient.

### Selective relief can coexist with aggregate restraint

The [March 12, 2023 BTFP announcement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230312a.htm) offered loans up to one year against qualifying assets valued at par and described up to $25 billion of Treasury backstop availability. Its [joint resolution statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230312b.htm) distinguished protected depositors from unprotected shareholders and certain unsecured creditors, with a banking-industry assessment for deposit-insurance losses. These choices make distribution and institutional responsibility observable. They do not prove a favored-sector motive or a realized $25 billion expenditure.

The existing restrictive rate policy was not reversed by that announcement, and the [March 22 FOMC statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a.htm) paired a further rate increase with concern about tighter credit conditions. That is compatible with willingness to contain a banking disruption while retaining aggregate inflation restraint. It is also strongly explained by distinct lender-of-last-resort, resolution and monetary-policy functions. The casebook preserves both hypotheses. A causal claim that selective relief enabled a higher policy path needs archived expectations, credit-condition controls and a credible counterfactual; those are absent.

### Authorized capacity is not executed lending

The March and [April 2020 facilities](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200409a.htm) establish prospective credit capacity, instrument coverage and approvals. They do not establish that the headline amounts were immediately lent, lost or transferred. Beneficiaries are eligible classes and intended transmission channels, not measured recipients of those headline amounts. Fine attachment-only March 23 terms have been excluded from the certified intraday block.

The [November 19, 2020 Treasury letter](https://home.treasury.gov/news/press-releases/sm1190) states a position on selected facility expirations and a different extension request for other programs. Its operational/legal claims compete with strategic interpretations of withdrawing support. An inference about conflict based on the next day's Fed response is later context, not a November 19 predictor. Actual cash returns or final lending changes need execution evidence and are not inferred from the letter.

### Treasury plans and allocations can be more directly checkable than motives

The May 2023 refunding statement, the 2023 coupon-sizing sequence, January 2024 guidance and [May 2024 launch plan](https://home.treasury.gov/news/press-releases/jy2315) form a documented sequence of borrowing plans and liquidity-management choices. Slower increases in long-coupon issuance are not the same as net issuance cuts. A plan to stabilize nominal auction sizes is conditional on financing needs; it is not a forecast of total bond yields.

The [May 29 buyback result](https://www.treasurydirect.gov/instit/annceresult/press/preanre/2024/BBR_20240529174000.pdf) reports $2 billion par accepted from $16.524 billion offered, with twenty eligible securities and nine accepted. The May 1 plan had described temporary settlement-process limits on CUSIP count. This is concrete operational evidence for an institutional constraint and for plan-to-allocation follow-through. Settlement was scheduled for May 30; the result alone does not prove its completion. These observations support a direct implementation audit more strongly than they support a directional rate, dollar or hidden-intent forecast.

### Forward guidance can fail without its opposite being right

December 2018's further-increases guidance and current hike both imply UP under the frozen rules. The target is unchanged at all three subsequent endpoints. Neither literal continuation nor mechanical inversion is correct. A HOLD outcome is a substantive third class, and it explains why “the message failed” cannot automatically be converted into “the opposite won.”

The [June 2023 pause](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230614a.htm) is the opposite challenge for persistence. The accompanying [projections](https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20230614.htm) and statement imply possible further firming, while the observed current action is a hold. M0 beats M2-min at 3m and 6m; M2-min beats M0 at 1m. The later path does not imply that every projection magnitude was realized or that the statement promised the exact scored horizon.

## 8. Separate market targets and deficiencies

| Target | Outcome data in this return | M0/M1/M2-min forecast coverage | Interpretation |
|---|---|---:|---|
| Net policy-rate direction | 24 primary episodes at each of 1m/3m/6m | 9 / 5 / 11 | Scored separately by horizon |
| First subsequent rate change | 24 primary episodes at each horizon | 9 / 5 / 11 | Separate target; coincides with net direction here |
| Policy surprise against pre-cut pricing | No archived futures/OIS panel | 0 / 0 / 0 | Missing expectations, not zero surprise |
| U.S. 2y and 10y yields | Daily drift for all 24 at each horizon | 0 / 0 / 0 | Observed drift only |
| 10y real yield and breakeven | Daily drift for all 24 at each horizon | 0 / 0 / 0 | Decomposition retained; not a pure expectations measure |
| DXY | No admitted series | 0 / 0 / 0 | No substitute broad-dollar index |
| Growth and inflation expectations | No harmonized expectation-vintage panel | 0 / 0 / 0 | Official goals, forecasts and market expectations remain separate |
| Strategic-sector relative response | No frozen exposure map or matched controls | 0 / 0 / 0 | No sector selection from later performance |

Yield data are [DGS2](https://fred.stlouisfed.org/series/DGS2), [DGS10](https://fred.stlouisfed.org/series/DGS10), [DFII10](https://fred.stlouisfed.org/series/DFII10) and [T10YIE](https://fred.stlouisfed.org/series/T10YIE). The start observation is the latest valid daily value strictly before the cut's New York civil date; the endpoint is the latest valid value on or before the horizon date, with no more than seven calendar days of staleness. The actual observation dates are retained. For midnight cuts, the event day's daily yield can be the start observation; this is a documented cut-relative drift, not an announcement-window return.

There are 288 primary series/horizon drift observations across four series and three horizons. No one is treated as a market forecast success. Nominal ten-year drift is decomposed into TIPS real-yield drift and breakeven drift only when dates align, retaining rounding residuals. Breakeven includes compensation for inflation and market premia; it is not a clean observation of expected inflation. The return does not estimate causal announcement effects, abnormal sector returns, rank correlations or market forecast errors without a frozen forecast and appropriate controls.

## 9. Answers to the commission's seven questions

| Research question | Answer supported by this return | What would resolve the remaining question |
|---|---|---|
| Does M2 beat literal rhetoric or inversion? | M2-min ties M0 on eight shared primary cases and beats M1 on three/six-month common cases. Full M2 is untested. | Rich M2 specified before outcomes, market pricing and matched coverage against institutional/action baselines |
| Which statement types mislead when treated as forecasts? | Goals, justifications, current-stance descriptions, capacity announcements and conditional annual projections do not automatically imply a 1m/3m/6m rate or return sign. | Larger independently coded statement-type sample with horizon-specific labels |
| Which actions are more informative than speech? | Current rate decisions plus a floor produce additional coverage; buyback allocation directly proves an allocation stage. No broad action-over-speech ranking follows. | Comparable target-specific mappings, including cases where speech adds information to a pause |
| Does persistence after visible cost improve inference? | Not estimated. Costs and alternatives are described, but the common adverse-cost/repeated-choice panel is missing. | Predefined cost visibility, timing, persistence and lower-cost feasible-alternative variables |
| Does selective relief show tolerance of aggregate restriction? | BTFP plus unchanged macro policy and subsequent tightening is compatible with that interpretation. | Evidence separating this mechanism from ordinary monetary, liquidity and resolution mandates |
| Can institutions explain apparent revealed preference? | Yes, strongly as a competing explanation in all 24 cases; the single quantitative constraint gain is the conventional-floor case. | Rich M2 must beat a sufficiently strong institutional explanation, not only naive inversion |
| What can be forecast without private motive? | Baseline action persistence, state-contingent guidance and direct plan/implementation milestones can be specified mechanically. | Prospective implementation and forecast evaluation; no motive feature is necessary to begin |

## 10. Surviving thesis, rejected thesis and next gate

**Strongest surviving thesis:** instrument choice, legal/operational constraints and distribution matter for describing what policy does. Recording them prevents category mistakes and supplies falsifiable hypotheses. The quantitative evidence supports a narrow conventional-floor adjustment to action persistence and horizon-specific comparison with a HOLD baseline. It does not support an inferred hidden-intent probability or incremental forecasting skill over literal guidance on the primary common sample.

**Strongest rejected thesis:** treating the clean opposite of public policy guidance as a dependable default. On the five selected upward-guidance cases, inversion is never correct at the three frozen horizons. The bounded falsification is of that rule on this sample; it is not an estimate of universal government truthfulness, a proof that rhetoric always works, or a representative test of dovish-message inversion. The stronger claim that actions always dominate words also has a concrete counterexample in the segregated June 2023 pause challenge.

| Unresolved item | Why it matters | Next evidence and owner |
|---|---|---|
| Full M2 comparison | The rich model was not operationalized from pricing and repeated choices | PB-G research/integration owner commissions a frozen specification and genuinely later evaluation |
| Archived pre-cut futures/OIS | Required to distinguish a predictable decision from a surprise | The next research/data owner reconstructs instrument, contract, quote time, source rights and expected meeting path |
| Comparable adverse-cost and alternatives panel | Required to test persistence after visible costs | The next research owner defines cost timing, feasible sets and lower-cost alternatives before outcome coding |
| Original historical served bytes and weak attachment clocks | Documentary certification is narrower than archived availability | Source owner obtains stable snapshots or publication receipts; until then retain the quarantine |
| Market/sector transmission and DXY | A rate decision does not determine all asset prices | Rates/FX research owners supply separate target mappings and admissible series; no proxy substitution |
| Representative sampling and coding agreement | Purposive historical selection and semantic coding can bias coverage | Broader preregistered census, independent coding, disagreements recorded and prospective cases |
| Integration authority | A research result is not a live consumer receipt | PB-G evaluates context-only incorporation through existing Policy Watch ownership under the parent's gates |

The primary continuation action is **PB-G review of this immutable research return**, with a gate against promoting rich M2 until the named pricing/cost data and matched prospective comparison exist. The bounded PB-A research commission is complete at this return boundary; parent W1 and PB-G work remain open. No external execution, merged change, live signal, watcher or automatic continuation is claimed.

## 11. Reproduction and audit files

Run the instructions in [PB_A_REPRODUCTION.md](PB_A_REPRODUCTION.md). They reproduce the frozen forecast and the policy/market outcome join using Python's standard library and the included public data. They also verify the received file hashes and compare regenerated JSON content even where a large published JSON file has been compacted for transfer.

The source packets preserve reviewed paraphrases, clock evidence, URLs and unresolveds; they are not complete archived webpage copies. Canonical normalized fields in the casebook take precedence over weaker provisional helper wording. Review notes under `audit/` document the source-clock checks, the independent scorer review and the BTFP/lineage corrections. [PB_A_COMPLETION.json](PB_A_COMPLETION.json) provides the bounded capability state, deficiencies, supersession rules and next gate for a fresh session.
