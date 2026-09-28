# R2 findings — source qualification and a falsified conditional baseline

Operation: `risk-regime-mechanism-research-20260927-sol-001`. Existing Grey Deer / MAS-258; issue #8128; research PR #8133. **MISSION_COMPLETE: false. No production, forecast or capital-policy promotion.**

## Executive adjudication

R2 materially advanced from a research design to a verified source audit and a preregistered empirical test. The source audit found actual historical-parameter leakage in the purportedly causal regime history. Separately collected full macro vintages enabled a bounded supplementary test without using that history.

The specific seventeen-feature logistic model plus four rates/credit/macro interactions **did not earn promotion**. It made primary equity-loss probability estimates worse, failed badly in the 2021 rebound, and missed severe developing stress in March 2020. A modest joint stock/bond-loss improvement over the additive model was uncertain and still inferior to the base-rate comparator. Do not tune this inspected construction until it appears successful. This rejects a particular construction, not regime-aware risk intelligence.

The useful conclusion is that a world-class system needs correct information timing, explicit mechanism and episode stage, distinction between observed damage and future loss, and recognition of unfamiliar environments. Simply adding interactions to slow macro inputs is not that system.

## 1. Exact research identity

- Macro source/data pin: `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`.
- R2-D1 preregistration, committed before outcome construction: `1d0d0e2c6861e680fe4e0de73f90e74b302752a7`.
- Tested and executed source commit: `a250295cc44fa6a1cf7c13f2f9284e29e0554ced`.
- Source SHA-256: `953951dc8c9410b4d1218985f0393dc43402ceb883aef146e68f126404b1dd8a`.
- Published tests commit: `3648c9a7b80f0df7d231894b473053c7c699f20f`.
- Tests SHA-256: `54fc1296f7d9895bdc42ffa79151c6646b853bc1d7d01f5088584c681c4d3c14`.
- Full results SHA-256: `d94f6a91cc5a8032f180aab7a66a575d4d4a897773b9d8f79e8f5e4597068672`.

R2-D1 is explicitly supplementary. **The original R2 exact-incumbent B1/B2/C1 comparison remains unrun.** The payroll/CPI construction is not silently relabeled as the existing production regime.

## 2. A causal recursion can still have historical lookahead

Actual source `engine/regime_one.py` at the pin has SHA-256 `7671e86ae2cce28f83a83054ad76c4920638f68a28a92af074dbf28c054d95eb`.

`_causal_filtered_pquad`, lines 261–339, estimates emission means/covariances, transitions and initial probabilities using the entire supplied score frame. Only afterwards does it execute forward filtering. Therefore observations after an old date can change the parameters used to infer that old date, even though the recursion is not a forward-backward smoother.

A source-isolated probe executed the actual function and `_logsumexp` on the actual pinned regime history. Because hmmlearn was unavailable in the execution runtime, only its Gaussian emission log-density was replaced with a scipy Gaussian reference. The fitting and forward-recursion source was unchanged. This is an actual-source dependency-isolated probe, not a full production execution.

Comparing a supplied history ending June 30, 2026 with one ending September 25, 2026:

| Check | Result |
|---|---:|
| Common retained historical dates | 189 |
| Dates whose probability vector changed | 172 |
| Dates whose modal category changed | 1 |
| Maximum absolute probability change | 0.0282, or 2.82 percentage points |
| Mean absolute cell change | 0.00108439 |

The modal change occurred on October 9, 2025: Q4 became Q1 after future observations were included. The June 30 endpoint happened to remain equal in this particular comparison. Do not overstate this as proof that every current endpoint is wrong.

Input history SHA-256: `5003f8c9a75fe3a9ae47a50384d72377ef187c4d6fc69eeb8ff7246de25558d3`.

A second source-path finding matters: `compute`, lines 780–859, sends the separate release-aware axis row to the macro display, but sends the original `full_regime` frame to `_forward_read`. A release-aware display row therefore does not establish release-aware HMM inputs.

**Research ruling:** reject this generated historical probability series as a then-known predictor until both input vintages and parameter-fit dates are qualified. Preserve the existing production source; no repair or authority change was performed in this wave.

## 3. What data actually exist

The main first-release archive is `data/fred_vintage/vintages.parquet`: 16,480 rows, five fields and no duplicate series/period pairs. PAYEMS and INDPRO initial-release history begins in 1997, while the inspected WEI initial-release coverage begins in 2020 and sticky-CPI coverage in 2014. Its companion accessor can also fall back to modelled release dates over revised finals. Neither a file called vintage nor a flag called release guarantees complete historical knowledge.

A separate bounded census found **already-collected full-vintage stores** under `data/fred_vintage/release_targets/`. These must not be overlooked or described as absent:

| Source | Rows | Distinct archived dates | SHA-256 |
|---|---:|---:|---|
| PAYEMS full vintages | 314,191 | 360 | `5fe02dde232efad7799d14b5331bd83d4ba2f849dc82e687bd49ade357debaee` |
| CPIAUCSL full vintages | 292,553 | 376 | `abc6b65a873a3d6de63d85379c86b61f71f99480354f46915c391d506970718b` |

Both have zero duplicate period/vintage pairs and no missing schema fields at the pin. Their bytes match the existing collector manifest. They contain output-type-2 histories, not just first-published values. ALFRED distinguishes historical vintages from the currently revised series; that distinction is central to the experiment. [E1]

The frozen daily inputs are SPY, TLT, MOVE, VIX, two- and ten-year nominal yields, ten-year real yield and high-yield OAS. `collectors/yahoo.py` maps dividend-adjusted Close into `close`, and split-only Close into `close_price`; the actual data contain the expected historical differences. SPY/TLT outcomes use `close`, the total-return convention.

Daily market stores do **not** carry full vendor historical publication/vintage metadata. This test is **archived macro vintages plus conservatively date-lagged current market snapshots**, not wholly vendor-vintage point-in-time evidence. Raw hashes, paths and conventions are frozen in `R2_D1_PREREGISTRATION.md` and the executed source.

Of 4,964 calendar sessions from 2007 through the fixed September 25, 2026 cutoff, 4,916 have all mandatory features. Excluded runs are explicit:

| Dates | Sessions | Missing features |
|---|---:|---|
| March 21–April 24, 2013 | 24 | MOVE percentile/acceleration |
| November 5–20, 2025 | 12 | Payroll vintage features |
| December 8–18, 2025 | 9 | Payroll and/or CPI vintage features |
| March 9–11, 2026 | 3 | CPI vintage features |

No absent source becomes calm, and no excluded row is silently inserted into an alternative comparison sample.

## 4. The experiment that was actually executed

D0 is the expanding, training-only base event frequency. D1 is the ridge-logistic additive model with seventeen frozen features. D2 adds exactly four prespecified interactions: real-yield change × CPI acceleration; credit-spread change × negative payroll acceleration; MOVE acceleration × credit-spread change; real-yield change × current drawdown magnitude.

PAYEMS/CPI year-over-year growth and its three-month acceleration use observation history from the **same archived vintage**. Date-only releases enter strictly after their publication date. Markets also use strictly earlier source dates. This conservatively avoids pretending a later close was available at an earlier assessment, but does not manufacture vendor timestamp proof.

Annual historical test folds run from 2015 through the eligible 2026 portion, with training beginning in 2007. Training and inner-validation fits respect a 63-session purge. Scaling and regularization selection are past-only. A pre-outcome failing test caught an inner-validation tail that would have used labels unavailable at the outer fold cutoff; it was repaired before the published source ran any real outcomes. Numerical convergence is checked rather than assumed.

Historical crises informed the research design, so these are chronological out-of-sample-style diagnostics, not pristine untouched or prospective validation. The first experiment deliberately establishes whether a modest conditional extension helps; it does not claim to implement the full mechanism architecture.

## 5. Results: conditional complexity did not pass

Brier score is mean squared probability error; lower is better.

| Outcome | Eligible test dates | Events | D0 base rate | D1 additive | D2 interactions |
|---|---:|---:|---:|---:|---:|
| At least 5% SPY decline within 21 sessions | 2,905 | 444 | **0.133287** | 0.145512 | 0.155417 |
| At least 10% SPY decline within 63 sessions | 2,863 | 395 | **0.120857** | 0.165313 | 0.181003 |
| SPY and TLT both negative over 21 sessions | 2,905 | 504 | **0.147769** | 0.181019 | 0.177547 |

The primary/joint targets run January 2, 2015–August 26, 2026. The 63-session target ends June 26, 2026. Later decision rows remain ungraded when the full future window is not observed.

Paired D2-minus-D1 Brier differences, with 2,000 moving-block resamples at a 63-session block length:

| Outcome | Difference | 95% interval | Interpretation |
|---|---:|---|---|
| 5% / 21 sessions | +0.009905 | −0.006285 to +0.034246 | Worse point estimate; no demonstrated gain |
| 10% / 63 sessions | +0.015690 | +0.002445 to +0.036591 | Adverse in this diagnostic |
| Joint stock/bond loss | −0.003472 | −0.009507 to +0.001796 | Small uncertain improvement over D1; still worse than D0 |

Block lengths 21 and 126 give the same qualitative adjudication. These intervals describe this fitted historical sequence, not uncertainty across every possible future policy or crisis. Recorded seeds use the base 20260927 plus block length to give deterministic separate resamples; this is the executable seed convention.

Primary AUC also deteriorates from D1 0.5729 to D2 0.5497. D1's probability ordering is not the same thing as useful calibrated warnings: D1 itself has worse Brier error than D0. None of these numbers is a current-market forecast.

## 6. First-warning performance is not daily-window performance

At the threshold targeting 10% of training dates:

| Measure | D1 | D2 |
|---|---:|---:|
| Actual test warning burden | 13.18% | 13.05% |
| Flagged test dates | 383 | 379 |
| Daily-window precision | 31.85% | 32.19% |
| Daily-window recall | 27.48% | 27.48% |
| First-warning episode anchors | 4 | 5 |
| Anchors followed by the defined next-21-session decline | 0 | 0 |

The small daily precision difference is not evidence of better early warning. The derived research episode view requires 21 eligible, known quiet sessions to rearm. It is not a new live ledger or a new canonical episode rule.

An independent implementation over saved predictions and thresholds reproduced the exact counts and hits. D2 first-warning dates were June 4, 2020; May 10, 2021; December 6, 2021; October 19, 2023; and June 8, 2026. The defined next-month event did not occur after any of these five anchors. That does not imply there was no subsequent loss at every longer horizon, or that the market was otherwise safe.

Other requested training budgets are retained in the full output. Their realized test burdens differ from the target training quantiles; no exact matched-test-burden claim is made.

## 7. What the failures teach us about the environment

This section is **post-result explanatory diagnosis**, not a new confirmation test or permission to tune.

### 2021: unusual rebound data became false precision

In the 2021 test fold, D2's mean probability was 33.68% against a 3.97% realized frequency of the defined next-month decline. It predicted above 50% on 63 dates. Payroll acceleration reached 9.60 standard deviations relative to its training distribution; 63 test rows had at least one standardized feature above five in absolute value.

On May 10, 2021, the correctly archived payroll data showed 10.87% year-over-year growth and 17.11 percentage points of acceleration. D2 issued 91.13%, but the defined next-month decline did not occur. On June 30 it issued 85.88%, also without that outcome. The Federal Reserve's retrospective 2021 report explicitly discusses pandemic comparisons and base effects, while BLS describes the substantial but incomplete labour-market recovery. [E2,E3]

These observations support an **extrapolation/support failure hypothesis**, not a proof that one feature alone caused all errors. Mean logit decomposition also implicates CPI level, real yield and payroll acceleration. No winsorization, threshold or coefficient was changed to rescue this wave. Five standard deviations is a diagnostic description here, not a calibrated deployment gate.

### March 2020: slow macro confirmation arrived after acute market damage

On March 9, 2020, the then-eligible payroll vintage still showed positive year-over-year growth of 1.60% and positive acceleration. Meanwhile prior-date HY OAS was 5.64%, up 189 basis points over 21 SPY sessions, and the current SPY drawdown from its trailing-252-session high was 18.95%. D2's next-month decline estimate was only 0.76%; the defined event followed.

By March 23, the drawdown was 33.72% and prior-date OAS was 10.09%, while payroll acceleration was still positive. By April 6 the new payroll release showed negative acceleration, but much market damage had already occurred. Treasury-market studies document the distinct market-functioning and cash-demand disruption during this interval. [E4,E5]

The inference is not that every macro series is useless. It is that a slow backdrop must not suppress directly measured acute stress, and the detector must distinguish shock initiation, liquidation and later confirmation. Falling real yields early in this path did not guarantee equity safety; subsequent real-yield repricing inside the disruption should not automatically be labeled an inflation regime.

### 2022 and 2023: existing damage is not the same as additional broad-index loss

D2 did slightly better than D1 on 2022 Y21 Brier, but not well enough to establish the model. Selected dated reads illustrate why stage matters: on October 14, 2022, SPY was 24.27% below its trailing-252-session high, the 21-session real-yield change was +68 basis points and D2 read 88.42%. The defined *additional* next-month decline did not occur. The visible damage was real; treating it as a successful forecast would count losses already realized.

Likewise, the March 2023 bank event should be evaluated with bank/funding/recipient outcomes, not declared harmless because the specific SPY barrier was not crossed. R2-D1 has no bank-outflow, collateral or issuer-exposure data and cannot adjudicate those mechanisms. The correct response is a separate target and exposure study, not changing Y21 after results.

Eighteen dated case-path snapshots are preserved in `posthoc_case_paths.json`, SHA-256 `2888b984202279566bf4de4de3fbe063164aa8b13f0a1dc79dae9ed40ad1d975`, under the original run root. They are descriptive examples selected after the model test, not an independent backtest.

## 8. Revisions can change the assigned backdrop

A post-result source-only comparison recalculated the same acceleration at each historical observation period using the final 2026 vintage rather than its then-available vintage. Payroll acceleration changed sign on **25 of 237** release dates; CPI acceleration changed sign on **3 of 251**. Maximum absolute differences were approximately 0.5632 and 0.1802 percentage points respectively.

For example, payroll acceleration at the July 6, 2007 release was +0.04977 percentage points in the archived vintage but −0.01235 using final history. A hard sign classifier would reverse that input's backdrop designation. Many differences lie near zero, strengthening the need to study uncertainty around boundaries rather than assume exact classification.

This is an input-vintage sensitivity diagnostic, not evidence that a new neutral band or probabilistic classifier improves prediction. No boundary was optimized. Preserve both real-time and retrospective interpretations where appropriate; only real-time information belongs in a forecast feature.

## 9. Engineering and scientific requirements carried forward

The next research version must keep these separations explicit:

1. **Then-known reconstruction:** input release, model-fit cutoff and filtered state must all precede the assessment. Extending future inputs must not change an issued historical read. The endpoint and historical path are separate contracts.
2. **Economic level, change and unusual base effects:** a large year-over-year acceleration is not automatically a novel boom or new crisis. Study level relative to a meaningful prior path and short-run change as separate descriptors, without retroactively changing this experiment.
3. **Observed severity versus forecast uncertainty:** untrusted predictive extrapolation cannot erase independently qualified observed credit/funding/price stress. Conversely, observed drawdown does not manufacture probability of another drawdown.
4. **Support and novelty:** report how much relevant historical evidence exists around an assessment, distinguish sparse cells from familiar episodes, and allow unknown/low-support interpretation. Similarity is not probability. New support rules require their own preregistered evaluation.
5. **Mechanism and stage:** distinguish initiation, propagation, liquidation, containment and repair. Indicators may change interpretation as the episode progresses. Bank and collateral risks need their own recipients and outcomes.
6. **Dependence and country exposure:** repeated global inputs remain one shock; country/sector sensitivity comes from qualified exposures, not eleven copies of the same signal.

The immediate next unit is a source-native, vintage-aware reconstruction contract and discriminating prefix tests for the existing regime path, followed by the exact-incumbent common-sample comparison originally owed in R2. The wider next research lanes remain bank/funding, energy, propagation and repair; this failed baseline must not reduce the mission to tweaking a pooled rates model.

## 10. Verification and remaining gates

- Local research suite: **20 passed**.
- Exact published source SHA matched before native execution.
- Exact published tests mirrored and executed natively: **20 passed in 2.06 seconds**.
- Initial native run completed exit 0; full independent rerun produced all six output hashes byte-for-byte identically.
- A separate loop-based outcome oracle found **zero Y21 and Y63 label mismatches** across the full source calendar, including maturity/null boundaries.
- Independent first-warning accounting reproduced the published primary 10% threshold anchors and hits.
- Final-fit gradient-infinity maxima: Y21 0.0004052; Y63 0.0005750; JOINT21 0.0002400, below the prespecified 0.001 refusal boundary.

These checks do not constitute independent scientific review, complete repository CI, production tests, country replication, full vendor-vintage PIT, or a comparison with the exact incumbent Radar. True leave-one-crisis-out refits, policy P&L/opportunity-cost studies and prospective qualification are unperformed. Reported crisis omissions only remove held-out dates from aggregation; 2007–09 and 2011 are training-era episodes and are not tested as unseen crises here.

## 11. Durable artifacts and reproduction

Native run root:
`/Volumes/Mastermind/research/risk-regime-mechanism-research-20260927-sol-001/r2-d1-a250295c`

Run command:
`python3.12 r2_d1.py --repo-root /Users/chriswong/Documents/Cluade/macro-main --out <new-isolated-output-directory>`

The executable reads pinned git blobs and verifies all ten input hashes. Do not overwrite the original outputs when reproducing.

| Output | SHA-256 |
|---|---|
| `outputs/results.json` | `d94f6a91cc5a8032f180aab7a66a575d4d4a897773b9d8f79e8f5e4597068672` |
| `outputs/Y21_predictions.csv` | `118140f9400b0ec987c8abe96ea128fe508cf9b560259c30021d4b57dea83d33` |
| `outputs/Y63_predictions.csv` | `d0c5ed36791d68dced69da1ad1d0b4353b9a1cb983def04930518e32d4cfbf23` |
| `outputs/JOINT21_predictions.csv` | `fc8bf48f1e76f2973a624cfb153842f9f70fdb240ac76b9a77d351cfe5c39759` |
| `outputs/research_panel.csv` | `d331623ffb61a22db6967accfd1d7349dc6d1bd2bd5eac7c76e5f4db27fc7566` |
| `outputs/source_date_lineage.csv` | `5a4592781fb1b579c5641e792423028138babb8d04602789f42563a12d544d32` |
| `verified_summary.json` | `26685bfc3fc765bcf8fea8c0fd110a60cc9c1bd6d4c07d5bc17e9db63ea5a21f` |
| `delivery_summary.json` | `4fb6d80cc7aada8befb68146d4260620876bc4f2699a32dd6715bc6b8cfce134` |

The 2,621-byte delivery summary was transferred to the conversation artifact runtime and its exact SHA verified. The large raw panel, lineage and prediction CSVs remain on the original authorized host; the downloadable companion must not be described as containing them. The source/tests and verified compact evidence make the study reproducible against the immutable repo pin.

No production engine, template, data store, ledger, score, capital policy or deployment was modified. Existing Grey Deer, Chronicle, Reflex Registry and Evaluation OS ownership remains unchanged. The exact denied prior MOVE integration effects remain unretried; no worker was dispatched to obtain them. PR #8133 stays Draft/HOLD. No worker, job or watcher is left running.

## External references used in this interpretation

E1. St Louis Fed ALFRED Help: https://alfred.stlouisfed.org/help — current versus archived vintages.
E2. Federal Reserve, 2021 Monetary Policy and Economic Developments: https://www.federalreserve.gov/publications/2021-ar-monetary-policy.htm — recovery and base-effect discussion; retrospective context, not then-known feature.
E3. BLS, U.S. labor market shows improvement in 2021: https://www.bls.gov/opub/mlr/2022/article/us-labor-market-shows-improvement-in-2021-but-the-covid-19-pandemic-continues-to-weigh-on-the-economy.htm — retrospective labour-market context.
E4. New York Fed, Treasury Market Liquidity during the COVID-19 Crisis, April 17, 2020: https://libertystreeteconomics.newyorkfed.org/2020/04/treasury-market-liquidity-during-the-covid-19-crisis/ — market-functioning evidence, not a pre-event predictor.
E5. New York Fed, The Federal Reserve's Recent Actions to Support the Flow of Credit, April 14, 2020: https://www.newyorkfed.org/newsevents/speeches/2020/log200414 — cash demand and intermediation context.

All new numerical results above are this experiment's calculations, with the source and limitations specified. External research does not validate the model.