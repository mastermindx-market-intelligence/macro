# Prophet industry continuation/reversal + K3E implementation

Chairman assignment (2026-11-14): independently build and test the industry-first engine; company-specific alpha is a later extension. Reconstructed/backdated historical research is explicitly permitted. Lack of original-vintage PIT history is not a discovery blocker. Preserve the distinction between reconstructed discovery and observed/predictive validation.

Protected procedure: Mastermind 199fd4f91ecc426b1d974eb3bf47f5162476cf24, skillpack 1.0.1. Macro implementation base: 8b01f3e0e1babcf5e0cfd081f9717fd3427806fe. Operation: prophet-industry-k3e-20261114. Host workspace acquisition returned unqualified; same-operation publication status and mmx-workspace status reconciled an existing clean exact-base workspace on sol/web-prophet-industry-k3e-20261114. No uncertain effect remains from that acquisition.

## Outcome and acceptance

Produce an executable industry transition research engine, a correctly separated K3E research/context adapter, a Prophet research consumer, and reproducible historical results. Distinguish continuation, reversal attempt, and deterioration; compute competing upside/downside/timeout probabilities and separate adverse-excursion risk; expose support, evidence provenance, and explanatory contributions. Research probabilities are not calibrated live trading probabilities or authority to mutate Prophet production ranks, size positions, or trade.

P1: implement lag-safe multi-horizon industry/regime features and return-path labels; numerical fixtures, prefix invariance, missingness and temporal leakage tests.
P2: implement regularized chronological estimation, untouched-within-fold calibration, mature-label training cutoffs and same-coverage comparisons; no hidden random time-series validation.
P3: adapt existing K3E coupling owner and add explicit reconstructed-history research changes with assumed-clock sensitivity. Do not rewrite SRC-A1 or immutable K3E EVAL-0/EVAL-1 registrations. Existing K3E code is ahead of its old capability ledger; reuse actual interfaces.
P4: execute industry research on pre-2003 public French49 data and publish all prespecified comparisons, nulls, costs, support and uncertainty. This is previously investigated history, not pristine external validation.
P5: expose results through an existing Prophet research-facing consumer, execute real artifact-to-consumer integration tests, publish one qualified source PR and drive the permitted release path. No invented production proof.

## Independent lane and custody

Incumbent v4 workers, the archive branch fable/rotation-core-20261110, PR11086, sealed industry confirmation and stock outcomes remain untouched. New paths use industry_transition / industry_k3e names; shared consumer edits require exact source and collision checks. No new warehouse, evaluator registry, scheduler, source writer, credential, trial promotion authority or agent dispatch. Direct implementation retained for PRINCIPAL_JUDGMENT and LOWER_TOTAL_OVERHEAD.

## Frozen first executable experiment (before this experiment's outcome reads)

Data: same public French49 value-weighted daily returns and Fama-French daily factors. Current-vintage historical data explicitly RECONSTRUCTED_DISCOVERY. Drop dates later than 2002-12-31 before numeric parsing. Preserve historical sentinel missingness and complete feature windows. No raw vendor rows committed. Earlier price-only study is not rerun or overwritten.

Population: all sufficiently observed industry month-ends, not only washouts. Input histories 21/63/126/252 sessions. State partition uses trailing126 relative sign and trailing21 relative sign: continuation (both nonnegative), reversal_attempt (long negative, short nonnegative), deterioration (long positive, short negative), persistent_weakness (both negative). These are observed states, not future labels.

Decision at month-end close; entry next-session close; horizon63 following sessions. Primary labels are first closing passage of +10% or -10%, otherwise timeout. Also report any closing loss >=10%, terminal net return, excess return, adverse excursion and coverage. Assumed roundtrip cost20bp; report0/20/50bp sensitivities. No tradable intraday stop/fill claim.

Fit expanding historical windows; test five-year blocks beginning1950 and ending2002. All training label_end dates strictly precede test start. Last36 months of matured training events are calibration-only; fitting labels strictly precede calibration start. Regularized multinomial regression (scipy primitives) with fixed regularization, no parameter search. A scalar temperature is learned only from calibration observations. Separate regularized bad-loss model. Weighted observations give each calendar month equal total fitting weight. Do not call overlapping industry events independent episodes.

Comparisons: smoothed historical base rates; own-industry price/volatility model; industry/market/factor context model with fixed economically motivated interactions; simple trailing126 relative-momentum ranking. Same event population, top20% of each month's eligible industries, plus all-event probabilistic scores. Report full and state-separated outcomes and calibration, no selected winning subset only. Retain predictions and per-fold diagnostics locally, commit aggregate evidence. Interval analysis resamples whole calendar months in12-month moving blocks, fixed seed20261114,1000 replicates. Report exploratory/unadjusted intervals and trial count3 fitted specifications (base, price, contextual), plus fixed momentum comparator.

Feature and model changes after seeing these results require an explicit adaptive amendment, never retroactive preregistration. A negative result changes the next hypothesis, not the printed prior result.

## Remaining acceptance

The parent goal of superior live trading signals is not established by a passing software suite, a retrospective model, a PR or a merge. Keep scientific validation and production activation separate from source delivery. Every milestone records exact code/input/output identities and the next unresolved consumer or empirical test.

## Milestone: executable baseline and connected research consumer

Original experiment ran from a93214df184d29001470a1fcc1f7575314fe0188, process86945, exit0. It produced41223 industry-month labeled events; chronological evaluation covers29861 observations/633months, with22 fitted model-fold receipts. Aggregate BASELINE_RESULTS.json hash72eea568180075f75276af078a831af51331be8d69853ea8188a0e56468d5f92. The source-vintage and cutoff assertions passed. The49-industry historical snapshot passed the actual existing K3E composer and the new Prophet artifact reader; snapshot hash5c7e969eb64a975d86c228c8447ca1d0de2c346ce2e4f9cb92f1af0066f922b5. No production install is inferred.

At equal20%-target coverage, context versus price-only reduced bad10 incidence by2.09percentage points (unadjusted descriptive interval[-3.60,-0.67]), but did not beat simple126-session momentum. All-event probabilistic scores favor the price-only model over the richer context model. Do not hide this counterevidence or promote a sophisticated model because it has more features. Adaptive next-policy specification is preserved separately before its outcome read.

Subsequent engineering changes add numeric JSON model persistence, input/clock validation, tests, and an additive authenticated /api/prophet/industry-research/v1 reader using the existing Lab auth, entitlement, kill-switch and private headers. Existing boards, ranker and K3E qualification are unchanged. Same-file open PRs identified by exact path query:10176(withdrawn episode handling),7399(effective-ledger performance),8333(opportunity-context helper); the new independent endpoint does not retarget their effects or clear holds.

Native focused suite process20497:73passed/5existing-library deprecation warnings,8.59seconds. Includes actual K3E-owner composition, original auth-wrapper401/403 tests, missing/corrupt/historical reader states, future-data separation, probability partitions, reconstruction lag and fiscal-period semantics. Author self-check, not independent review. No production/authenticated human credential path has been exercised.

Parent mission remains incomplete. Next: execute the fixed adaptive momentum-protection comparison; qualify actual SRC-A1-to-industry research context without claiming original-vintage economics; finish consumer/reproducible inference workflow and normal source delivery. No raw vendor rows, local prediction CSV, credentials or live data are staged.
