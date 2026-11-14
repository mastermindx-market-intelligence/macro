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
