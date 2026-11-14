# Follow-up: adverse-day resilience and pre-existing market sensitivity

Status: adaptive exploratory follow-up. The first pilot's aggregate pre-2003 outcomes have been seen. This design is fixed before its own feature/result reads, but it is NOT an untouched holdout or independent confirmation. The published first-pilot nulls remain unchanged. No search over windows, thresholds or models is authorized by this file.

Question: does a washed-out industry that has started resisting market selling have lower subsequent failure risk than a superficially similar rebound? This is distinct from calling every relative-strength turn a favourable gate. A market beta is an exposure descriptor, NOT a fundamental compounder/cyclical classification.

Data, candidate population, next-session-close entry, 63-session labels, 20 bp assumed costs, no-raw-data publication, pre-2003 cutoff, bootstrap and reserve fences remain exactly as in PROTOCOL.md. No private dot panels, industry 2003-2019 outcomes or 2020+ outcomes are read. No industry average is claimed to validate a single-stock signal.

For each candidate, fit an intercept and market beta to 252 daily log returns ending t-21. Evaluate residuals in the following 21 completed sessions, t-20 through t. Require complete training/evaluation data, positive residual variance, and at least five strictly negative and five strictly positive market sessions in the evaluation window. No missing returns are filled. This gives a frozen pre-window expected market response rather than fitting beta to the rebound itself.

S (adverse-day resilience) = mean residual on negative-market days > 0.
U (up-day residual strength; comparator) = mean residual on positive-market days > 0.
B (slow exposure) = fitted pre-window market beta >= 1; the other group has beta < 1.
M (market decline) = market trailing 63-session total log return < 0.

Primary contrast: S present versus absent within original R recipient-repair candidates. Primary outcomes: Bad10 and excess63. Secondary diagnostics: S overall; U within R; S absent/present within R x B and R x M, plus full S x R x M cells, win rate, mean return, competing upper/lower/unresolved labels. Prediction: S reduces Bad10 without sacrificing excess63; it must not be a disguised low-beta, already-rebounded or unresolved-trade filter. U is not claimed as a placebo immune from real effects; it asks whether any incremental result is specific to adverse days.

Same-month, same-R nearest-neighbour matching with replacement: log sigma63, drawdown126, distance21low, relative126, recent21 absolute log return and pre-window beta; feature-only whole-sample standardization for this descriptive matching; Euclidean caliper 1. Report balance, retention and unique controls. This is observational robustness, not causal identification. Report all planned strata even if sparse or contrary. Matching parameters and periods will not be chosen for favourable outcomes.

Inference: same 12-calendar-month moving-block bootstrap, 2000 resamples, seed 20261114. Describe intervals as unadjusted exploratory. Print conditional group counts and distinct months; do not count industries in the same month as independent. A result must be checked for timing/indexing errors and feature prefix invariance before interpretation. State exclusions and unchanged input hashes.

Falsifier: if S has no incremental benefit after same-date and risk/geometry/ordinary-rebound controls, or benefit only removes both successful and failed opportunities, this exact price-only resilience gate is not nominated as validated. Fundamental cash-flow deterioration, economic links and actual fund flows remain untested and cannot be inferred from these return proxies.
