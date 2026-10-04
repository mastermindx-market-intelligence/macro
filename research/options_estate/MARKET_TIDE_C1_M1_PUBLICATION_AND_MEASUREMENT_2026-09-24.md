# Market Tide C1-M1 — advance publication proof and measurement repair

Operation: `market-tide-research-20260924-sol-001`; parent Macro #7925; same Draft/HOLD PR #7929 and records branch. Sol retains the live Chairman research-to-product commission. This is a pre-market-run research amendment, not a new programme, trial ledger, forecast, sizing rule or operational calendar.

Procedure reverified: protected Mastermind `1a7d400294b0d37c460b963b8865b40a23173b58`, Skillpack 1.0.1/bootstrap 1; current INDEX and the previously loaded same-revision companion blobs matched. Current source contract inspected: Macro `95af6934f523394149c430b6903eaddb8b767151`, `lib/dataos/temporal.py`, blob `094b149a8b9158f19cb99c4005568c12db96ed41`.

## 1. What became known

Two gaps were resolved without accessing either previously refused data operation:

1. Dated official BLS reports contain forward-looking notices of the NEXT release. A historical event need not be inferred solely from today's calendar or its eventual occurrence. Four such publication-to-next-event links were directly checked below. A dated Fed announcement separately establishes advance knowledge of the 2017 scheduled meeting dates.
2. The original C1 fitted a squared-error conditional-mean benchmark but selected it using absolute error and a median reference. That score targets a different functional. An exact synthetic counterexample demonstrates an economically important failure: the median can be zero while expected downside is positive. C1-M1 repairs this before any C1 market panel/model result has been inspected or produced.

The price/corpus gate is NOT closed. No historical event panel has been operationally admitted; no complete non-event coverage or schedule-revision census has been performed. No market price acquisition, new empirical return result, fitted benchmark, page, prospective forecast or trade was produced.

## 2. Primary-source advance-notice receipts

These are manually verified research evidence rows, not an installed calendar or a comprehensive historical dataset. The public-document release timestamp is what the publisher states, not a fabricated historical system-ingestion timestamp. The documents were inspected through public web reads on September 24, 2026; exact raw-document byte hashes and original system first-seen receipts were not obtained.

| Event/reference period | Dated source and stated publication time | Next event announced in that source | Evidence location |
|---|---|---|---|
| CPI / January 2017 | National CPI release dated January 18, 2017, 08:30 EST | February 15, 2017, 08:30 EST | Source A header and next-release sentence |
| CPI / February 2017 | National CPI release dated February 15, 2017, 08:30 EST | March 15, 2017, 08:30 EDT | Source B header and next-release sentence |
| Employment / January 2017 | Employment Situation dated January 6, 2017, 08:30 EST | February 3, 2017, 08:30 EST | Source C header and next-release sentence |
| Employment / February 2017 | Employment Situation dated February 3, 2017, 08:30 EST | March 10, 2017, 08:30 EST | Source D header and next-release sentence |

Primary URLs:
- A: https://www.bls.gov/news.release/archives/cpi_01182017.htm
- B: https://www.bls.gov/news.release/archives/cpi_02152017.htm
- C: https://www.bls.gov/news.release/archives/empsit_01062017.htm
- D: https://www.bls.gov/news.release/archives/empsit_02032017.htm

Date/time conversion follows the offset actually stated: 08:30 EST is 13:30 UTC; 08:30 EDT is 12:30 UTC. Do not impose one fixed UTC time across the year. These rows distinguish the report's reference month from the publication month. The actual CPI/payroll values in those documents are outside this schedule-only extraction and cannot enter a pre-release predictor for the next event.

The Fed's June 28, 2016 announcement, released at 14:00 EDT, lists the eight scheduled 2017 meetings: January31-February1; March14-15; May2-3; June13-14; July25-26; September19-20; October31-November1; December12-13. It calls the schedule tentative and names quarterly conferences after March/June/September/December meetings. Source: https://www.federalreserve.gov/newsevents/pressreleases/monetary20160628a.htm . This source establishes advance meeting DATES, not the exact release time of every later statement. Its own 14:00 publication time must NOT be copied into each future event.

The March 15, 2017 statement independently records an actual 14:00 EDT release: https://www.federalreserve.gov/newsevents/pressreleases/monetary20170315a.htm . It is occurrence evidence, not by itself proof that the exact time was known before that day. Together with Source B, it illustrates a real same-day CPI/FOMC sequence, not an estimated trading effect.

### Admission implications

- A dated forward notice can support historical PUBLIC availability of the scheduled date/time. It does not prove that Mastermind collected it then or emitted a forecast then. Use existing Data OS `published_at` and `ingested_at` semantics; do not introduce another time model.
- The inspected temporal owner coalesces published_at/ingested_at for EVENT and BARS, uses served_at for INTELLIGENCE, rejects timezone-naive instants, and distinguishes current-rule recomputation from actual system replay. This amendment does not alter that code or any profile's authority.
- A retrieved archived page is publisher documentary evidence, not a cryptographic original-byte attestation. Preserve source provenance and that limitation. A new retrieval timestamp cannot be backdated into an ingestion receipt.
- A next-release notice proves a positive planned event. It does not certify that all intervening updates, postponements or other event classes were captured. Missing coverage cannot become event=0. A primary C1 cohort still needs all three event indicators to be determinable at each origin.
- Preserve schedule revisions as known at each decision time, including cancellations. Do not replace an originally expected event with the eventual realized date and retrospectively claim advance knowledge.
- Unscheduled policy actions must not acquire advance schedule flags from their outcome dates. For example the March3,2020 FOMC statement documents a 10:00 EST release, not a prior day's advance notice: https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm . No advance-notice status is inferred from that document alone.
- A date-only FOMC notice remains date precision until an accepted source/method provides the required event-time bound. Do not invent a midnight or universal 14:00 timestamp merely to pass C1's next-session window.

## 3. C1-M1: exact supersession of the scoring mismatch

Original specification: `research/options_estate/MARKET_TIDE_R1_SOURCE_AND_EVENT_SEQUENCE_2026-09-24.md`, first commit `458023f18beb132c869397e6fe9788b096e3f6be`, blob `f7abf209ee811290c257335a37228b9eb47a7924`. It remains preserved unchanged. This amendment replaces only the functional/score/reference clauses below and their associated primary-comparison terminology. It does not erase the original design or rewrite a result.

### Counterexample and root cause

Construct an exact distribution with Y=0 in nine equally weighted cases and Y=10 in one. These are arbitrary dimensionless risk units, not market returns. Its mean is1 and median is0.

| Constant forecast | Mean absolute error | Mean squared error |
|---|---:|---:|
| 0, the median | 1.0 | 10.0 |
| 1, the mean | 1.8 | 9.0 |

The original expectation that the true mean should win under the primary absolute-error score fails. This is not evidence that MAE is intrinsically wrong: it is consistent for a median, not a conditional mean. Under squared error, E[(Y-a)^2] = Var(Y) + (a-E[Y])^2, so the mean is the minimizer. A framework concerned with expected downside must not confuse low typical downside with low expected downside or absence of a tail.

Primary methodological reference: Gneiting, *Making and Evaluating Point Forecasts*, JASA106(494),746-762, DOI10.1198/jasa.2011.r10138; https://www.tandfonline.com/doi/abs/10.1198/jasa.2011.r10138 and author manuscript https://arxiv.org/abs/0912.0902 . The inspected abstract emphasizes matching the requested functional and its scoring rule. No new full-paper replication is claimed.

### Minimal repair, fixed before market evaluation

1. C1's point estimand is explicitly the **conditional mean of the original normalized five-session downside Y5**, not its median, a quantile, expected shortfall or probability.
2. N uses the mean of the same eligible prior training cohort, replacing its median. P/PE/PEI retain their originally specified squared-error ridge fitting, fixed0.01 penalty, training-only standardization, intercept treatment, clipping and features.
3. Primary score is **mean squared error of Y5 predictions**, replacing MAE. The two confirmatory comparisons remain PEI versus P and PEI versus PE. The original 5% materiality hurdle applies to relative MSE reduction versus P. MAE is retained only as a labeled secondary diagnostic, never as a second route to promotion.
4. Preserve the original study dates, target formula, horizons, event definitions, two interactions, monthly chronological fits, maturity/purge rules, event-count feasibility floors, common cohorts, 63-session paired block bootstrap,10000 draws,seed20260924,97.5% two-sided intervals and21/126-session sensitivities. Corresponding interval calculations use paired squared-error differences and relative MSE reductions. A zero baseline MSE makes a relative improvement undefined; emit null and no relative-hurdle pass rather than divide by zero.
5. The mean-risk result remains a prediction-research result. Calibration, tail-event probabilities, warning thresholds, costs, missed upside, cash carry, re-entry and actual exposure-policy value remain separate later gates. MSE can be sensitive to extreme episodes; retain the frozen era and leave-one-year influence checks. Do not cap tails or change score again because a market result disappoints.

C1-M1 is a **pre-results measurement amendment within the existing operation**, not a failed-model retune or a new trial allowance. The original C1 has not run on market data. R0's calendar-only preregistration, MAS-260's rejected experiments and every live sizing/forecast authority remain unchanged.

## 4. Price-adjustment invariance: narrow proof, not a data waiver

The existing R1 correctly requires source basis, identity, vintage and availability. But a later rescaling is not automatically evidence of look-ahead in EVERY possible feature.

For positive constant c, log(c*P_t/(c*P_s)) = log(P_t/P_s). Therefore a uniform rescaling over each relevant within-basis window leaves C1's trend63, momentum5, trailing20-session RMS log-return volatility and normalized close-path Y5 unchanged. The structure and total-return series can each have their own positive constant; C1 uses ratios within each basis. A constructed nonuniform revision changes the target, providing a negative control.

This proves only a sufficient invariance condition. It does not prove that the actual Yahoo file differs from historical vintages only by uniform factors. It does not cure missing bars, nonuniform corrections, wrong basis, first-seen clocks, incomplete event coverage, execution-price errors or missing provenance. No inspected market corpus is admitted by this argument. Preserve basis/vintage receipts and use their actual revision properties, not a blanket claim that all revised data are either safe or unusable.

## 5. Executed reproducible evidence

Standalone artifact: `research/options_estate/market_tide_measurement_checks.py` at commit `8d8c7ea4fcf19f67c65884f019a326f59c4e3985`.

- Source SHA-256: `faf7b3b33011cd062f1fd9df1e75c7f913d1c7de565d900bbc4b00842cfd6625`.
- Git blob verified against the executed bytes: `8dfa98c5338e779df11d005af43c1ae07c66344f`.
- Command: `python -S research/options_estate/market_tide_measurement_checks.py` (executed against the identical sandbox reproduction copy).
- Final execution: exit0, empty stderr, **16 named checks passed**. The check that the original absolute-error rule favors the median is retained, not suppressed.
- Stdout result SHA-256: `9df4d70dfc082d8498a0520e9c65771624433db6b8dac76bd3852af57c485b48`.
- A preliminary one-off discriminator expecting the mean to win under MAE failed as expected before the amendment. The final script checks both that original failure mode and the corrected MSE ordering.
- An initial ordinary-Python invocation completed the earlier15-check version but emitted an unrelated environment spreadsheet-startup warning. Final stdlib-only `-S` execution avoids site startup and is the16-check evidence reported here.

These are mathematical/synthetic checks, not a repository-wide pytest suite, empirical market validation or hosted CI acceptance. The script has no external inputs, network calls, source-store reads, publication API, artifact writer or runtime effects; it prints its result. It is a research reproduction attachment, not a new canonical production scorer or simulator.

## 6. Useful product consequences and next unit

The page should distinguish **typical downside**, **expected downside**, **probability of a specified loss**, **tail severity**, and **decision value** when those quantities are separately qualified. A zero median cannot become a green 'safe' badge. No such forecast currently exists in Market Tide.

An event timeline should distinguish advance-planned events, date-only schedules, complete versus incomplete coverage, actual release/absorption and unscheduled actions. The public-availability clock and our own first-seen/emission clocks stay visible. Reuse existing Event Intelligence and Market Memory owners; no new calendar, first-seen store, state machine or forecast ledger.

Next principal action: bind the four reviewed advance notices and the date-precision Fed notice to the incumbent event source's evidence interface, determine coverage/update completeness for a bounded historical block, and resolve the remaining price basis/availability receipts through existing owners. Do not reopen the completed broad source census. A qualified supplied-input cohort then permits implementation/evaluation of **C1-M1**, not the superseded MAE design. If only retrospective public-information research is supportable, label it separately from actual system replay and prospective forecasts. Do not run either previously refused native operation or duplicate R0 acquisition.

## 7. Continuity and held effects

The source script is a verified new research artifact on the SAME GitHub branch. The new report and cumulative Agent OS record must be read back before the checkpoint advances. No native repository workspace or incumbent #7328 source was modified. There are no active children, newly submitted workers or automatic wakes. Principal retention: PRINCIPAL_JUDGMENT for measurement/admission adjudication; no routine model fan-out.

Original R0 download/write and R1 metadata/hash refusals remain TOOL_DEGRADED/EFFECT_NONE, never retried, routed around or delegated. No unresolved modifying effect is observed in this continuation. Existing draft hold, source review/CI, data admission and production-proof obligations remain. Mission complete: false. No acceptance or release follows from the16-check result.
