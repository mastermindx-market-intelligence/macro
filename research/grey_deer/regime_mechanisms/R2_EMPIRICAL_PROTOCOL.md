# R2 protocol — rates, growth and credit as distinct risk pathways

**Version:** research protocol r1, frozen before any new R2 outcomes are computed. This is a diagnostic study specification, not a promoted trading policy. Existing historical episodes and the earlier MOVE result are already design-exposed; no historical fold is described as a pristine unseen sample.

## 0. Decision and scope

**Question:** does conditioning rates-related warning information on the real-time growth/inflation backdrop and credit deterioration improve forecasting over a pooled additive model and the exact incumbent Risk Radar at comparable warning burden?

**Primary market:** US, existing broad benchmark SPY, total-return basis verified against source convention. **Country replications:** the ten existing Radar profiles, each on its native documented benchmark and local session calendar. A missing or unqualified replication is reported separately, never silently replaced with a convenient ETF or treated as a US-equivalent sample.

**Historical research window:** January 1, 2007–September 25, 2026, with prerequisite prehistory for transforms. A shorter input history limits eligible dates transparently. September 2026 observations whose outcomes have not matured are ungraded. No additional outcome dates beyond the cutoff may be inserted into this frozen diagnostic.

**Out of scope:** changing any live thresholds, policy weights, equity rank, gross exposure, country schema, alert controller, ledger or production source. R2 does not resolve denied MOVE integration by another carrier.

## 1. First work unit: data qualification, not fitting

For every required measurement produce a record with:

- canonical producer/store identifier, exact file or provider request and instrument definition;
- immutable raw hash, retrieval time, source release/available time, covered observation period;
- units, currency, price/total-return basis, adjustment policy and trading calendar;
- whether values are first-release, actual historical vintages, reconstructed current snapshots, or synthetic;
- the first date and fraction of eligible data available to the study, gaps and revisions;
- entitlement/redistribution restrictions and the permitted consumer;
- source and model definition changes, historical memberships and parameter-fit cutoff.

Read the existing source rather than making a parallel collector. Freeze these records before outcome construction. Not finding vintage data does not prohibit an explicitly labeled reconstruction, but reconstruction is not the authority-grade confirmatory lane.

Required classes: nominal and real yields; credit spread level/change; MOVE; VIX; growth/inflation context; primary benchmark; local session calendar. Breadth, dollar and local bond returns create declared augmented models/secondary outcomes only if qualified. Preserve the incomplete model and missing source in the report instead of silently altering features.

SOFR, EBP, CMDI, COT and macro releases must use actual public availability times. A date-only market feed defaults to the first local decision cut at which that date's complete value is demonstrably known. For Asian markets, never use a later US close on the same calendar date. Macro observations do not become known on the month or quarter they describe. [S05, S22, S31, S32]

## 2. Existing regime source qualification

Use `regime_one`/`quad_vector` as the candidate source-owned backdrop. Do not use full-sample smoothed `regime_hmm` chart history. For every reconstructed historical posterior require:

1. input releases available no later than the decision cut;
2. model parameters fit only through the declared training cutoff;
3. filtered, not forward-backward smoothed, state inference;
4. state meaning/mapping fixed from past training data;
5. no current-vintage normalization or retrospective label as a feature;
6. missing, degraded and unfamiliar-state metadata retained.

A causal filtering function alone is not sufficient if it is run with full-sample fitted parameters. Failure of this qualification blocks the claimed historical conditional model, not the entire research: the pooled baseline and source-gap report can still be completed.

## 3. Targets and clocks

Let `P_t` be the qualified local benchmark close at decision date t. Inputs must have `available_at <= decision_at(t)`. The forecast is issued after that cut, not executed at a price already passed.

**Primary Y21:** 1 when any of the next 21 observed local-session closes is <=0.95×P_t, otherwise 0 only after all 21 sessions are observed. Today's already-realized loss is excluded. Missing future prices or an incomplete horizon give null, not zero.

**Secondary Y63:** same definition using <=0.90×P_t over 63 local sessions.

**Secondary joint-loss outcome:** both the benchmark and a declared duration-bearing local government-bond total-return proxy end the next 21-session interval below their t levels. This is a declared hedge-failure outcome, not automatically systemic dysfunction. No broad bond substitute is permitted without its duration/currency/basis disclosure.

**Secondary credit-pressure outcome:** 21-session change in the same OAS series; report continuous change and preregistered threshold sensitivity at +25/+50/+100 bp. These are analytical stress bands, not claims of economically optimal crisis thresholds.

**Event initiation versus continuation:** stratify by the incumbent source-native warning state at t, fixed before outcomes. Also report future loss relative to P_t separately from existing drawdown from the trailing 252-session high. Do not count the pre-t loss as a forecast success.

No macro recession or banking-crisis outcome is used as a substitute success label for Y21.

## 4. Frozen hypotheses

H1: MOVE/rates changes contain different incremental Y21 information when credit deterioration is present than when it is absent, conditional on the backdrop and current benchmark damage.

H2: A rising-real-yield/inflation-pressure pathway has a different relationship with joint equity/bond loss than a weakening-growth/widening-credit pathway.

H3: Added conditional complexity improves calibration or first-warning coverage at matched warning burden versus the additive model, rather than winning solely by issuing more warnings.

H4: The conditional model does not systematically suppress stress outside the recognized two pathways; mixed/unknown states remain explicit and the incumbent risk observation is retained.

H5: The effect survives removal of each major global episode family and does not exist only in 2020 or 2022.

These are hypotheses, not findings. H1–H5 cannot be rewritten after looking at their outcomes. New observations warrant a versioned later study, not a relabeled success.

## 5. Model comparisons

**B0:** expanding, training-only base rate for each outcome; country pooling is explicit.

**B1:** exact incumbent source/transition replay. Read and reuse the accepted replay/live parity repair; do not reconstruct an approximate state machine. Current `can_force`, gross and live consumers are unchanged.

**B2:** regularized pooled additive model over the qualified fixed input set. Rates/yield levels and 5/21-session changes, OAS level/21-session change, MOVE relative level/frozen acceleration, VIX relative level, existing growth/inflation context and current benchmark damage. Withhold a model whose mandatory input set cannot be qualified. All transformations are fit or specified without future data.

**C1:** B2 plus these prespecified interactions only: real-yield change × inflation context; credit change × growth deterioration; MOVE acceleration × credit change; and real-yield change × current benchmark damage. These are empirical interaction terms, not automatic causal labels.

**C2 (separate augmented test):** C1 plus qualified point-in-time breadth, broad-dollar change and relevant local exposure descriptors. It cannot be compared on a different sample without showing B0–C1 on the identical augmented-sample dates.

Keep the first implementation parsimonious. More flexible models are a new experiment, not an unreported search. No LLM-generated risk score or retrospective narrative feature is allowed.

## 6. Time validation and dependencies

Use expanding annual test folds beginning in 2015 after the initial 2007–14 training period. Fit on only rows whose outcome horizons matured before the training cutoff. Use the largest 63-session horizon for temporal purge in the common comparison. Hyperparameters are selected only inside earlier chronological folds; initial regularization search is limited to three declared values (0.1, 1, 10, with software parameter convention recorded).

2026 through the fixed cutoff is a final historical diagnostic slice, not prospective validation. The latest historical crisis knowledge has influenced this research design. A prospective cohort must begin only after the final model/version is frozen and be issued through the existing evidence owner.

Cluster uncertainty by global episode family and calendar blocks. Report block-length sensitivity of 21, 63 and 126 sessions with 2,000 seeded bootstrap replications; seed 20260927. A one-year crisis is not eleven independent country crises. Country models should shrink toward the shared model and disclose effective event counts; sparse cells do not earn precise country-specific cutoffs.

## 7. Warnings and episode scoring

For diagnostic model comparisons, evaluate threshold-free precision-recall and calibration first. Then compare warnings at training-only target burdens of 5%, 10% and 20% of eligible dates. Ties are handled deterministically without splitting equal predictions using their outcomes. These are comparison budgets, not live alert settings.

Use the incumbent episode owner/rearm definitions where applicable and report them verbatim. For model-only diagnostic alerts, use a derived, nonpersisted research episode view: first threshold crossing anchors an episode; rearm requires 21 consecutive observed, eligible quiet sessions. Missing observations never count as quiet; regime relabeling never restarts the clock. First-warning precision, first-to-event lead and alarm duration are separate from daily overlapping precision.

For recall, construct event episodes independently of the candidate's warnings. Merge overlapping Y21-positive windows into event clusters; disclose that this is a retrospective target grouping rather than a real-time state. Report detections before the first barrier crossing, after existing damage and missed entirely. Also show results under a nonoverlapping 21-session evaluation grid so target clustering choices remain visible.

## 8. Primary reporting and acceptance

Report by full sample, pre-2020/2020 onward, backdrop, country and pre-existing damage state:

- common eligible sample and excluded dates/reasons;
- Brier score/log loss and reliability diagram, with uncertainty;
- precision-recall, event/episode precision and recall, warning burden and duration;
- first-warning lead/lag distribution, missed episode names, and contained stress false alarms;
- conditional baseline and incremental change versus B1 and B2;
- feature ablations and leave-one-global-episode-family-out results;
- raw data and model hashes, timing guard receipts, reproducibility command, numerical warnings;
- exposed versus less-exposed recipient comparisons only when membership is genuinely point-in-time.

No fixed p-value or row-count threshold alone grants promotion. R2's outcome is an explicit adjudication of evidence strength and limitations. Progress to prospective shadow qualification only after an independent reviewer finds no material leakage/target mismatch, the improvement is not dominated by one crisis or warning burden, and uncertainty is narrow enough for the proposed consumer. If the conditional model fails, retain useful context and reject that construction; do not imply the entire regime-aware research space is refuted.

## 9. Capital-policy study remains separate

Any later “go cash” or re-entry research must freeze its policy before outcomes, compare against constant full exposure, exposure-matched constant exposure, and a simple volatility target, and include transaction costs, spread/slippage, next-executable-price lag, cash carry, currency hedging, missed upside and recovery delay. Short-selling/leveraged rules are not silently introduced. Historical rescue effects are not removed to improve results. No R2 model gains size/gate/execute authority.

## 10. Exact next actions

1. Recover the source manifests and causal-regime parameter lineage from the existing producers, with current writer/custody gates for any eventual changes.
2. Build the read-only R2 eligibility/availability manifest and prove rejected future/smoothed inputs with the contract tests.
3. Freeze model/feature/exposure manifests and the incumbent replay identity before computing new outcomes.
4. Run B0/B1/B2/C1 on the same qualified dates, then the separately qualified C2 and country replications.
5. Publish the immutable diagnostic, failure cases and uncertainty through the existing research carrier; seek independent scientific review before a shadow candidate.
