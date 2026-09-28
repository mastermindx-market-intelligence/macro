# Crypto science R4 — executable breakdown/reclaim comparison

Date: 2026-09-28. Parent WS:CRYPTO-INTELLIGENCE / Macro Draft PR #8050; operation crypto-vector-r2-20260926-sol-001. Protocol committed before outcome calculations at `c458e016b094bbf28f6e4d89f5e622a56e92e697`. Initial research implementation `03f5b5c02d12745ee8098102fc9e03d398b3fd1a`; terminal-open correction and replay-evidence candidate `f83e37e95d788f449ef3aa05d7f4e3b3e452671b`. Baseline source `017d3866eace58c4587bd7d2dc07a9320450bd77`. These are research candidates, not a merged or deployed policy.

## Executive disposition

Neither tested rule earns promotion. Adding an hourly volatility-shock filter modestly increases the descriptive fraction of breakdown events followed by a specified downside-first move, but the prescribed24h cash overlay does not establish positive net marginal value against the corrected incumbent. The specified washout/reclaim confirmation sequence performs worse, on average, than immediate entry on the matched 14-day parent windows and loses against the exposure-duration diagnostic as well.

This does NOT imply immediate entry after a washout is safe, every confirmation method fails, or reducing risk lacks value. It rejects a particular plausible-looking confirmation sequence and withholds promotion from one coarse protective policy. Cash reduces within-event drawdown by design, but that protection has an opportunity cost. A probability model, a pre-crash detector and an investor-specific risk-utility optimum have not been established.

The experiment advances beyond R1–R3 integrity audits: it evaluates new observable sequences, delayed executable-price references, first-passage competition and paired costed decisions. Its negative findings are retained without retuning thresholds, selecting the best delay or changing the outcome to rescue a candidate.

## 1. Frozen definitions and timing

### Downside

D0: completed hourly close breaks the minimum low of the preceding 72 hourly bars, excluding the current bar.

D1: D0 plus a current hourly return at or below minus 2 times the sample standard deviation of the previous 24 hourly returns. Both use the same complete 74-hour observation requirement and no source interpolation.

Only observed False→True onsets are selected, with more than 24h between selected onsets. First-observed positive after a data gap is not treated as a fresh onset. The two rules are selected independently: their event sets overlap, but are not identical or independently randomized.

A candle indexed t is a bucket starting at t. The condition is issued at t+1h. Execution is at the exact stored opening price issue + 1h (primary) or issue + 6h (sensitivity), not the signal close. The24h target is a5% decline before a3% rise. Prior damage is not credited as a future prediction. Opening gaps establish order; when both barriers occur in the same hourly bar without known order, the label is AMBIGUOUS and receives no conservative success credit.

### Recovery

The parent is an observed transition into a daily5-day decline of at least10%, with more than 14days between selected parents. U0 enters after that completed daily bar plus the execution delay.

U1 waits at most7 completed days for the first simultaneous occurrence of two nonlower lows, a close above the previous day's high and a close above the five-day mean. Missing intervening observations make confirmation unknown; no subsequent favorable date is searched past that gap. No confirmation means NO_ENTRY, not removal of the parent.

Conditional entry labels use a5% rise before a3% decline during the next 168h. Economic comparison uses a COMMON endpoint14days after the parent's initial executable entry. All paths begin in cash and liquidate at that endpoint. The waiting path retains cash in no-entry parents. This separates conditional appearance of successful entries from actual cost of waiting or staying out.

All observations are from the existing stored Coinbase BTC-USD daily/hourly histories for new price features. The corrected incumbent is recomputed once through existing source on cached, hash-pinned stored inputs; its daily target becomes usable only after daily completion plus the scenario delay and expires after24h. This does not certify historical provider publication or override-receipt vintages.

Official Coinbase candle documentation was checked: bucket time is its start; the opening trade, closing trade and extrema have distinct timing; historical gaps may occur. Reference: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles . No exchange metric endpoint, account, order or provider collector was invoked.

## 2. Sample and what the counts mean

The hourly source has 94,063 rows from 2016-01-01 to 2026-09-26 13:00. There are 92,457 known candidate decision hours under the complete-lookback requirement. D0 produces 588 selected onsets; D1 produces 483, with 419 shared exact anchors. The daily washout sequence has 59 parent episodes.

There are 2,378 scenario-event rows and 6,738 scenario-account rows, summarized in 104 fixed family/period/delay/cost cells. These are NOT 9,116 independent market events: delays, costs and candidate overlap repeatedly reuse underlying observations. All rows are preserved.

We report the full period plus 2016–2019,2020–2023 and the already-used2024+ period. Outcomes crossing a slice's end are not scored for that slice. None of these periods is a newly untouched holdout; no fitted model or parameter sweep was performed.

## 3. Downside findings

### One-hour assumed action delay, next 24h, downside5% before upside3%

| Cohort | Rule | Mature entries | Downside first | Upside first | Neither | Ambiguous |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Full | D0 breakdown | 586 | 97 (16.6%) | 165 | 323 | 1 |
| Full | D1 breakdown + shock | 482 | 89 (18.5%) | 128 | 264 | 1 |
| Reused 2024+ | D0 | 165 | 15 (9.1%) | 35 | 115 | 0 |
| Reused 2024+ | D1 | 132 | 15 (11.4%) | 24 | 93 | 0 |

The descriptive D1 fraction is higher, but this is a filtering/onset-selection comparison, not proof of incremental predictive accuracy. Full-period 90-day-block resampling gives approximately14.8–22.5% for D1 versus13.1–20.5% for D0. These are overlapping retrospective ranges, not current crash probabilities or a formal paired treatment test.

The median prior24h move at D1 issue is about−3.30% in full history and−2.60% in reused 2024+. This is expressly a test of continuation AFTER observable damage. It is not proof that the model predicted the initiating shock.

### Marginal24h cash policy versus following the incumbent

Both paths start with the same incumbent risk allocation. The candidate sells to cash, holds24h and restores the incumbent's terminal target; the reference follows the corrected incumbent's subsequent target changes. Cash yield is 0. Proportional one-way cost 10 bp is charged on turnover, with unchanged weights allowed to drift between target changes. These are paired event accounts, not a compound strategy backtest or exchange-fill receipt.

| Cohort | Rule | Comparable parents | Mean candidate minus incumbent, percentage points of starting event equity |
| --- | --- | ---: | ---: |
| Full | D0 | 586 | −0.1481 |
| Full | D1 | 482 | −0.0844 |
| Reused 2024+ | D0 | 165 | −0.1681 |
| Reused 2024+ | D1 | 132 | −0.1716 |

For full-period D1, the approximate block95 interval is−0.2778 to+0.0709 percentage points. This does not establish a reliable positive benefit. The full-period mean is−0.0054 pp at zero costs and−0.2029 pp at 25 bp: it is not a strong gross edge merely obscured by one inconvenient fee assumption. The 6h-delay full-period mean is−0.0985 pp at 10 bp. All three cost assumptions and both delays remain in the result, including the 2020–2023 D1 positive mean(+0.1152 pp at 1h/10 bp) with its wide interval; that favorable period is not selected as the result.

Protection and expected return are different objectives. Full-period D1 reduces median within-event marked account drawdown from roughly0.771% under the incumbent to0.066% while cash/fees are held. But its best observed marginal gain and worst observed opportunity cost are approximately+7.91pp and−16.67pp. These extrema are descriptive, not chosen demonstrations of predictive skill. No risk-aversion parameter was fitted after seeing them, and we do not conclude that a risk-averse investor could never value temporary protection.

The specific rule therefore remains a research baseline, NOT an authorized emergency exit. The next predictor must distinguish a break that keeps propagating from one being absorbed or already reversing, rather than interpreting every large negative bar as an instruction to sell.

## 4. Recovery findings

### Conditional first-passage result

At1h assumed action delay, immediate entry has 17 upper-first outcomes among 56 complete7-day windows(30.4%). The waiting rule confirms 30 of 59 parents;29 confirmed entries have complete7-day windows, with 6 upper-first outcomes(20.7%) and 23 lower-first outcomes. There are 29 no-entry parents. These conditional cohorts are different and cannot alone establish a causal benefit or harm from waiting.

In reused 2024+, immediate entry has 2/8 upper-first outcomes. Confirmation occurs in 4/8 parents, with 1/4 upper-first. The small counts forbid a confident modern-regime probability claim.

### Paired common14-day endpoint, including no-entry cases

Fifty-four parents have the complete common price path. Twenty-nine lead to an entry and 25 remain in cash. Among confirmed entries the median delay is 120h (5 days), with a range of 24–168h. A five-day wait is a material part of the tradeoff, not free confirmation.

At1h action delay and 10 bp one-way costs, over ALL 54 comparable parents:

| Reference/result | Mean event return or mean paired difference |
| --- | ---: |
| Waiting sequence's return | −2.4599% |
| Immediate full-BTC entry return | −0.5928% |
| Waiting minus immediate | −1.8671 percentage points |
| Waiting minus corrected incumbent | −2.7178 percentage points |
| Waiting minus exposure-duration-matched diagnostic | −3.1753 percentage points |

The wait-minus-immediate block95 range is approximately−3.7682 to+0.0755pp: negative average, substantial uncertainty. The mean remains negative when each calendar year is omitted one at a time, but those are sensitivity checks, not independent replications. Reused 2024+ has only 7 comparable common endpoints and a very wide interval; it cannot rescue or conclusively condemn the method by itself.

The exposure-duration reference allocates a constant initial fraction equal to the later realized time in the market. It deliberately uses ex-post waiting information and is NOT an implementable strategy available at the parent timestamp. Its purpose is a diagnostic control for spending less time at risk. The negative comparison suggests this exact rule's entry timing has not earned credit merely for being selective; it does not prove that a feasible lower-exposure strategy would deliver that reference return.

Higher assumed costs modestly narrow wait-minus-immediate loss because no-entry cases avoid trading fees; they do not make the sequence superior. Full-period differences are−1.9636 pp at 0 bp,−1.8671 pp at 10 bp and−1.7226 pp at 25 bp. Six-hour action delay likewise leaves the full mean negative(−1.9347 pp at 10 bp). No delay or cost is optimized.

**Disposition:** do not promote this specified daily confirmation rule. Do not infer that blindly buying washouts is acceptable: immediate entry itself has frequent adverse-first moves. A future recovery hypothesis needs a more discriminating measure of selling exhaustion and persistence, tested on the same parent/opportunity framework rather than replacing the evaluation target until it wins.

## 5. Missing data, implementation correction and evidence quality

Five recovery parents lack complete 14-day hourly paths: 2017-09-13,2018-01-25,2018-08-04,2020-09-03 and 2025-10-11. They are retained as incomplete, not silently discarded. At the 1h downside setting D0 has incomplete paths for 2018-12-25 03:00 and 2019-04-11 09:00; D1 shares the latter. Missingness around stress can be informative, so complete-case results may not generalize to exchange outages. We did not fill these gaps or count them as safe outcomes.

One implementation correction was made after the first run and before accepting the evidence. The original helper unnecessarily demanded the terminal bar's later high/low/close when only its opening price belongs to the declared holding period. A failing synthetic test reproduced that over-censoring. The fix preserves all held-hour validation and requires only a finite positive terminal open. Initial source/output/log are retained in r4/initial. After rerun, All three event/account CSVs are byte-identical and all 104 summaries equal the initial outputs. The correction therefore improves the timing contract without changing any market result in this snapshot. No parameter or hypothesis was changed.

Independent arithmetic code rechecks every summary, 2,308 mature first-passage paths and 6,738 cash/coin accounts using a separate inventory/wealth implementation rather than the research weight recurrence. All agree. That is independent arithmetic, NOT review by a separate person or model. The baseline sidecar is an immutable replay artifact, not a second live target store or issued forecast ledger.

The 54 input identities, 18 existing gates and 31 recorded earlier R2/R3 artifact hashes remain unchanged, as do the principal source/config hashes during computation. R1 evidence remains unchanged in git. The current engine's DataFrame-fragmentation warning is recorded; no performance refactor was mixed into the experiment.

## 6. Product implications and next scientific decision

The useful distinction is not simply red/green or oversold/not oversold. This experiment exposes two difficult transitions: whether selling at a broken level is still moving price efficiently, and whether a rebound has obtained durable demand rather than only looking better after several days.

The dashboard should not promote either new rule to a risk-on/off instruction. A future qualified warning must state whether it is detecting an ongoing break or forecasting additional damage, its executable horizon and its expected false-exit cost. A recovery state must not claim that confirmation is inherently safer simply because more boxes are checked. These results change the research direction, not current allocation authority.

Next substantive phase: freeze an incremental confirmation experiment that measures price impact/absorption and follow-through with actual spot participation or genuine aggressor data only where source/venue/time coverage supports it. Preserve the same action-time, common-parent, ambiguity, cost and incumbent comparisons so improved evidence cannot come from relabeling the objective. A long-history price/spot-volume baseline must remain distinct from the shorter true-flow extension; no candle-signed volume may impersonate aggressor history. Explicitly test failed reclaims, not only successful bottoms. No new R5 thresholds or outcomes were searched in this batch.

Historical publication qualification, legacy funding semantics, external code/science review, exact-head CI/merge conflict resolution, live release and forward-issued evidence remain open. The current branch remains draft; no model parameters, engine defaults, gate artifact, subscription, saved review, trade or production deployment changed. The broader predictive moat is still an open mission, now with concrete executable baselines and rejected simplistic candidates rather than untested visual narratives.

## 7. Final verification receipt

The current combined Vector/Crypto/science regression pack completed with **256 passed, 25 warnings**. The exact invocation comes from the existing `unrun-vector-dsr` CI step plus all existing Crypto suites; R4 tests are appended to the already-invoked impulse falsifier suite, not a new job. Python compilation, the source-scope affirmative-claim checker, `git diff --check`, final input/source/gate hashes and initial/amended-result equality checks all completed with exit 0. See `research/crypto_science/r4/verification_final.txt`.

Nine R4 core tests cover completed-bar causality, calendar gaps, unknown onsets, exact execution delay, competing-barrier ambiguity, first reclaim/no-entry, drifting holdings/costs, incumbent publication timing, block uncertainty, pre-entry damage and terminal-open-only qualification. The original six tests failed before implementation; subsequent coverage additions and the separate terminal-open RED/GREEN cycle are labeled accurately in the retained logs. Independent arithmetic verification completed separately, without claiming an independent reviewer. Local checks are not exact-head CI, merge acceptance or live-route proof.
