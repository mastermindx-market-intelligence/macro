# Market Tide — tail-predictor evidence and replication boundaries

Operation `market-tide-research-20260924-sol-001`; Sol retains the live Chairman research-to-product commission. Parent #7925; existing Draft/HOLD #7929 and branch `claude/market-tide-research-20260924-sol-001`. Procedure freshly pinned to protected Mastermind `819abc8c23609cdded2b33f6e1bfc7854bd5c847`, compatible Skillpack 1.0.1/bootstrap 1; INDEX and required same-revision companions match their already-read full blobs. This is research evidence, not a new forecast, calendar, experiment registry, worker assignment or production component.

## Decision

The missing Jacobs–Ke–Pan appendix has been recovered and its Table A4 inspected in both parsed text and a rendered page. The candidate is now **METHODS_REVIEWED_WITH_IMPLEMENTATION_GAPS**, not merely abstract-reviewed and not independently replicated. Its limited historical forecast evidence merits a bounded reproduction once inputs and implementation details qualify. It does not authorize pre-FOMC exits, automatic post-FOMC entries, or a fixed holding period. C1-M1 remains the unchanged primary event/price downside experiment; the tail-return question is a distinct candidate, not a replacement for that experiment or a revival of rejected GEX recipes.

The current Market Memory raw-price profiles are not substitutes for the dual-basis C1 input. Existing-owner reference inquiries have been posted to MAS-204 and MAS-94; they are not worker STARTs or proof of a response.

## 1. Verified documentary facts

Jacobs, Ke and Pan, *Tail Risk Around FOMC Announcements*, DOI `10.1017/S0022109025101828`, JFQA 61(2), 640–672. Main source [S1]; online appendix dated May 15, 2025 [S2].

A4 evaluates January 2014–December 2021 using recursively estimated regressions beginning January 1996 and a historical-average benchmark, both estimated through the preceding period. Its reported out-of-sample R-squared percentages are:

| Predictor | R(1,2) | R(1,3) | R(1,4) | R(1,5) | R(1,6) | R(1,7) |
|---|---:|---:|---:|---:|---:|---:|
| Abnormal volatility | 0.65 | -2.48 | -3.63 | 0.84 | -0.08 | -0.12 |
| Abnormal skewness | 4.82 | 2.19 | 5.99 | 2.88 | 0.02 | 0.48 |
| Abnormal kurtosis | 3.76 | 1.92 | 4.76 | 1.94 | -0.11 | 0.23 |

Inspection: S2 PDF page index 10, printed page 11. A4 reports point estimates, not confidence intervals or cost-adjusted portfolio results. These percentages are NOT investment returns.

S1 Section III.B, printed page 652, defines R(1,s) as cumulative S&P 500 excess returns from the first day after the announcement through day s. Predictors use seven-day option-implied moments measured two days before the event relative to their trailing median over t-15 through t-8. Exact aggregation, pricing endpoints and implementable fills still require executable-source/measurement reconciliation.

S1 Section V.B and footnote 14 explicitly use statements AND minutes for an explanatory tone partition and acknowledge the minutes' later release. S1's full-sample uncertainty partition also is not a training-only live threshold. S2 Table A14 supplies in-sample standardized-moment sensitivity; it is not A4 out-of-sample confirmation.

## 2. What follows, and what does not

The largest reported A4 point estimate occurs at R(1,4); the reported skewness improvements near days six/seven are small. This is a reason to inspect horizon dependence, NOT to select day four after seeing the best result. The six overlapping horizons and three related predictors are not independent replications. A historical-average comparison also does not establish incremental value over Market Tide's price/volatility/event baselines or show that the options signal survives transaction costs and re-entry delays.

A reproduced published table would establish computational reproducibility on the same sample. It would not create a newly untouched holdout: we have already seen these published results. Any later 2022+ evaluation must be honestly designated relative to prior research exposure, frozen before its outcomes are inspected, and must preserve data/era/contract changes. Do not label a re-run of 2014–2021 as new prospective evidence.

A4 alone cannot adjudicate conditional loss probabilities, expected downside, risk-neutral versus real-world probabilities, or an exposure action. It concerns a return forecast at different endpoints from C1-M1's downside-path target. Do not transfer its score, sample or claimed efficacy between those outputs.

## 3. An important causal-time restriction on the explanatory results

The Fed released the March 14–15, 2017 meeting minutes on **April 5, 2017 at 14:00 EDT** [S3]. That is after the post-meeting horizon being studied. The paper expressly acknowledges delayed minutes in its explanatory analysis; this is NOT an allegation that its pre-event A4 predictor used minutes.

Our implementation consequence is stricter than a narrative summary: a tone label using those minutes cannot become a feature in a March 16 decision or an immediate post-announcement re-entry rule. Explanatory partitions and implementable predictors are different. At each decision, use only the statement, conference material, prices and other evidence actually available by that decision time. Treat a later minutes release as a separate information arrival through the existing event/time owner.

The same rule applies to realized policy surprises. An event-window shock may help a properly timestamped post-event assessment, but not a pre-event warning. Likewise, full-sample regime thresholds are descriptive until replaced in a separately frozen implementation by past-only estimates. Do not quietly modify the published replication to hide these differences: first reproduce the stated research, then separately evaluate the causal implementation.

## 4. Scoring notation needs implementation reconciliation

The rendered A4 formula prints residual sums without squared terms, while its prose describes mean-squared prediction error and cites Campbell–Thompson. This is an observed notation inconsistency. It does NOT establish that the authors' code used unsquared residuals. Their executable score implementation has not been inspected.

The mean-squared out-of-sample comparator required for our future implementation is:

`R2_OOS = 1 - sum((actual - prediction)^2) / sum((actual - prior_only_reference)^2)`.

A zero reference sum of squared errors makes the relative score undefined; preserve null rather than an infinite success. Positive R2_OOS means lower squared error relative to that specified reference, not a significance test or positive portfolio alpha.

An original mathematical discriminator executed in this session used outcomes `[1, -1]`, predictions `[0.5, -0.5]`, and reference `[0, 0]`. Both signed residual sums are zero, so the printed unsquared ratio would be 0/0. The squared-error comparison remains well-defined: reference SSE=2, model SSE=0.5, R2_OOS=0.75. These are arbitrary synthetic units, not market returns.

Separately, a reported 5.99% MSE improvement implies `100 * (1 - sqrt(1 - 0.0599)) = 3.0412458826%` lower RMSE under the same cohort/reference. This is arithmetic interpretation, not our empirical reproduction of A4.

## 5. Separate distribution scale from shape

For a random variable with third and fourth central moments m3 and m4, and positive scale a:

`m3(aX)=a^3*m3(X)`; `m4(aX)=a^4*m4(X)`.

Standardized skewness and kurtosis are unchanged by that rescaling. Thus raw higher moments can rise in magnitude because the distribution becomes more volatile even when its standardized shape does not change. That does not make raw moments useless: absolute downside risk can genuinely increase with scale. It prevents us from attributing all raw-moment variation to changing asymmetry or relative tail thickness.

A second original discriminator used five equally weighted synthetic values `[-3,-1,1,1,2]` and their doubles. Variance changed 3.2→12.8, third central moment -3.6→-28.8, fourth central moment 20→320, while standardized skewness stayed -0.6288941187 and standardized kurtosis 1.953125. Twelve in-session arithmetic assertions covering both examples passed. These are mathematical checks, NOT repository tests, a new production scorer, or market evidence. The existing 16-check C1 measurement attachment was not changed or rerun.

The candidate's later incremental study should therefore retain scale controls, standardized-shape diagnostics and the published raw-moment measurement as distinct comparisons. A generic SKEW index, estimated dealer gamma or put/call-volume ratio is not a validated substitute for the published measurement.

## 6. Bounded reproduction package, not model promotion

The next implementer should have one finite task, not rediscover the literature:

1. Preserve S1/S2 identity and the above A4 table as external reported targets. Pin actual licensed input availability, option quote filters, settlement clocks, interpolation/extrapolation and units. Never invent an OptionMetrics-equivalent corpus from a superficially similar index.
2. Resolve the exact score code or document the squared-error interpretation explicitly; resolve daily-return aggregation and price endpoints before claiming an exact table match. Preserve a discrepancy rather than silently picking whichever convention matches the reported number.
3. Reproduce all reported A4 horizons/predictors with their original recursive chronology and identical admitted events. Retain missingness, quote coverage and the exclusion list. Do not choose the best horizon, retune windows or omit crises after results.
4. Audit information availability separately: t-2 features, contemporaneous release schedules, shock availability, statement/conference/minutes timestamps, and date-effective contract conventions. A planned event later cancelled must not acquire hindsight treatment in an ex-ante strategy.
5. Only after reproducibility and independent review, freeze an incremental out-of-sample comparison against existing price/volatility/event baselines, with dependence-aware uncertainty and multiplicity control. Do not use A4 positivity as an automatic pass criterion.
6. Only a later policy study can assess exposure, cash carry, costs, gap timing, foregone rallies and re-entry. No coefficients, thresholds, probabilities or sizing rules are adopted by this packet.

Disposition: documentary OOS evidence recovered; causal implementation and data qualification still incomplete. This is a bounded candidate specification, not a dispatched worker or accepted forecast.

## 7. Additional data-source disposition and actual owner inquiries

Exact source inspection at Macro `b9d23ca4bce4308fa7466c4e0f5d318168a50f6f`:

- `config/market_memory_technical_price_basis.v1.json`, blob `3bbedd78a72c9ede516e0f42cd7e7fb52f47c7cf`, explicitly says the v1 Massive flat-file profile is raw/unadjusted, not an economic return, and does not authenticate regular-session closing prices.
- `engine/neuralweb/market_memory_technical_observation.py`, blob `53907401de58b79b4e4b7cbe3feb27c739d09e79`, uses a stable-read transaction for a current 21-session ratio; older support rows are not reconstructed point-in-time observations.
- `contracts/market_memory/spy_daily_price_source_observation.v1.schema.json`, blob `7d20efaa85ba8b0a5b9890fbecd7bad92a16f347`, binds that exact raw profile, not a general historical total-return source.
- Current read of MAS-94 describes the REST v2 hybrid regular-session-price/full-day-activity profile, but it remains unadjusted. This is the described contract, not newly verified live availability.

Therefore neither inspected raw profile can be relabeled as C1's split-adjusted AND total-return input. This is a profile/basis disposition, not a claim that every Massive product or private archive is unsuitable. No raw-data request, manifest download, source capture or historical byte-hash probe was performed.

Evidence/reference inquiries posted, without changing issue status, assignee or source custody:

- MAS-204: comment `fffe9f72-7379-40e9-a117-580bbb26d404`, created 2026-09-24T14:59:41.541Z. Requests already-existing revision-aware CPI/NFP/FOMC schedule evidence, known-at precision and positive/negative coverage for C1 chronology. No new collection or F1 restart.
- MAS-94: comment `356dafb3-8370-486c-b768-7db190757188`, created 2026-09-24T14:59:56.330Z. Requests already-existing longer dual-basis SPY source/manifest refs and limitations. No corpus build, API request, writer restart or refused-action substitute.

The tool returned each saved comment and ID. No reply, pickup, START, runtime admission or automatic wake is inferred. Sol retains the next recovery/adjudication action; these inquiries do not park the entire mission or transfer it to historical owners.

## 8. Tool effects and continuation

The public appendix URL was recovered by a read-only public-article HTML request on the MacBook, process 8564, HTTP200, completed exit0. This made no repository or market-data write. Web rendering verified A4, main page652 and the standardized-moment definition on page669; the appendix's A14 sensitivity page had also been rendered. A requested main table10 screenshot failed; the time-leakage interpretation uses the readable Section V.B/footnote14 and the Fed's explicit publication notice, not an unviewed numeric table.

Firecrawl's initial schema error was corrected once on the same tool; the corrected request returned insufficient credits before execution. No credits were purchased and no job was started. Technical failure on that optional public-literature route was not a safety refusal. An unrelated Harvard PDF endpoint returned405 and the NBER landing page403; no successful retrieval of Campbell–Thompson full text is claimed. Its Harvard bibliographic record was accessible [S4].

Earlier R0 acquisition/write, R1 native footer/hash and combined Agent OS validation/options-manifest refusals remain held, pre-dispatch EFFECT_NONE, not retried or delegated. Native verification checkout and all existing writers are unchanged. No new empirical market run, price corpus, live page, forecast, trade or sizing effect. No active process or worker remains from this tranche.

The exact next productive unit is a supplied-input implementation of the already-frozen C1-M1 benchmark, with synthetic time/label/purge/score tests and no source acquisition, followed by actual evaluation only if the existing-owner inputs qualify. The tail candidate remains separate; the newly recovered appendix must not trigger another broad literature audit. Resolve any returned metadata evidence before opening fresh source searches. Full source review, test enrollment, required exact-head CI and record acceptance remain outstanding.

## Sources

[S1] Main article, DOI10.1017/S0022109025101828: https://www.cambridge.org/core/services/aop-cambridge-core/content/view/567F3B47420074A6521C31755E7AE587/S0022109025101828a.pdf/tail-risk-around-fomc-announcements.pdf . Inspected sections III.B, V.B/footnote14 and VI.B; rendered pp652/669.

[S2] Publisher-linked online appendix: https://static.cambridge.org/content/id/urn:cambridge.org:id:article:S0022109025101828/resource/name/S0022109025101828sup001.pdf . TableA4, printedp11,29-page appendix dated May15,2025. Exact link recovered from publisher HTML; parsed text and rendered A4 agree. No original-byte hash or author-code verification claimed.

[S3] Federal Reserve, April5,2017 minutes release: https://www.federalreserve.gov/newsevents/pressreleases/monetary20170405a.htm . Establishes release at14:00EDT, three weeks after the March14–15 meeting.

[S4] Campbell and Thompson (2008), bibliographic record only: https://dash.harvard.edu/entities/publication/73120378-7dd1-6bd4-e053-0100007fdf3b . Full-text retrieval unsuccessful in this tranche; squared-error identity above is independently derived.
