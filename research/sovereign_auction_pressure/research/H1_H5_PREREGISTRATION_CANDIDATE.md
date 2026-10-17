# H1–H5 preregistration candidate — Sovereign Auction and Funding Pressure

Prepared 2026-10-08. **CANDIDATE, NOT CANONICALLY FROZEN.** Parent adoption must bind this specification, source-revision manifest, exact model implementation, eligible-data manifest and digest before outcome access. These are proposed research rules, not trading authority. No new model or study result has been computed in this task.

## A. Shared research contract

### A1. Separate explanation, prediction and the product

The all-security official event product is independently useful and may ship as context. H1 causal-event evidence does not approve H2, H2 rates evidence does not approve H5, and H5 retrospective improvement does not approve portfolio decisions. The existing SLF-006 NO-GO, D2 auction-cycle FAIL and Terminal market-risk exit-modulation KILL remain recorded exclusions.

The primary hypothesis family has five registered comparisons, one for each H1–H5. All additional asset, horizon, tenor and regime outcomes are explicitly secondary. Report every attempted specification, including nulls and broken assumptions. An insufficiently precise interval means `INSUFFICIENT_EVIDENCE`, not proof of no effect.

### A2. Observation and decision clocks

Every row must contain:

`auction_episode_id`, `phase_episode_id`, `instrument_class`, `source_revision_id`, `official_published_at_or_null`, `first_observed_at`, `input_known_at`, `decision_cutoff_utc`, `market_quote_at`, `outcome_window_start/end`, `source_digest`, `source_rights_status`, `missing_reason`, `baseline_version` and `model_version`.

`input_known_at` is the first time the particular vintage is demonstrated available. For forward production this is no earlier than actual collector receipt plus successful parsing. Historical official publication can establish a market information set only if verified; it does not establish that our own system consumed the record then. Preserve those two claims separately. Derived inputs inherit the maximum known time of all dependencies and the model/statistical transform version.

No imputed historical release time that uses future events, retrospective weekly interpolation, same-day close after the decision, corrected final data, full-sample normalization, or in-sample historical maximum is allowed to masquerade as a prior input. Carry forward only a previously released observation. Missingness indicators may be features only when their historical availability is itself known.

The preregistration must fix the market calendar implementation. ET means `America/New_York`, with daylight saving and early-close handling; UTC is the stored clock. Actual Treasury deadlines override generic schedules.

### A3. Study units and calendar support

- H1: one announcement episode per unique release timestamp, grouping all securities announced together. Separate quarterly-refunding episodes from ordinary announcements.
- H2/H4: one auction-time episode, with tenor-level measurements inside the episode. Collapse common-day equity/benchmark outcomes before computing effective sample size.
- H3: one settlement cohort per effective settlement day. Aggregate across securities; do not count one funding-rate outcome repeatedly.
- H5: one US equity decision day, evaluated on every eligible trading session. Coupon proximity/DV01 vary by day; do not define “all Treasury auction days” as a treatment because bills make that indicator nearly ubiquitous. Same-day coupon auctions are one exposure cohort.

Retain Bills/CMB, nominal coupons, TIPS and FRNs in the product. Primary H2/H4 nominal-rate tests use nominal fixed-rate coupons. TIPS real-yield and FRN reset mechanics have separate secondary study definitions; exclude unsupported types from a particular outcome study with an explicit reason rather than silently from the calendar.

### A4. Historical and prospective separation

All history through the adoption cutoff is retrospective for this program. Existing null studies already exposed much of 2016–June/July 2026. Repartitioning those dates is a useful chronological robustness check, not an untouched prospective holdout.

For retrospective model development, split the eligible chronological decision dates into the first 60% training, next 20% calibration/selection, and final 20% challenge. Compute split boundaries using the eligible-date manifest only, before loading outcomes. Keep whole issuance weeks in a single fold; purge any example whose outcome window crosses a boundary. Embargo five trading sessions beyond the longest primary window. Record actual boundary dates and hashes. Calling the challenge set “unseen by this particular fit” must not imply unseen by the organization.

Prospective launch is the first successfully logged decision cutoff after canonical model/specification freeze and collector readiness. Do not backdate it to this document's date. The first fixed evaluation window comprises 252 eligible US equity trading sessions, with H1–H4 episode outcomes collected within that same interval. Unscheduled model changes end the versioned evaluation and require a separately frozen successor; retain the original version's record.

During that interval, inspect operational coverage, timeliness, rights and failures. Do not repeatedly inspect performance and stop when favorable. At the fixed endpoint, wide uncertainty or too few episodes means no promotion; extend only under an explicitly new, prospective protocol. The first 252-session evaluation is not promised to have enough power for a small effect. No background collection or scheduled evaluation is claimed until an existing owner actually starts it.

## B. Hypotheses, features, outcomes and falsifiers

### H1 — Unexpected announcement supply and repricing

**Estimand:** the association/identified effect of new supply information at its release, relative to the pre-release expectation, on subsequent market prices. This is not a forecast of the announcement surprise before it exists.

**Primary exposure:** announced nominal coupon DV01 minus a independently time-stamped pre-release expected DV01. Freeze the expectation source before selecting events. If only previous auction amounts or prior official plans exist, name the variable `offering_change` or `plan_revision` and report a descriptive revision study; do not admit that row to the market-surprise estimand.

**Primary outcome:** change in the 10-year benchmark yield from five minutes before to fifteen minutes after verified announcement publication. Use the same identified benchmark/contract across the window, not a mechanically rolled series. Quote gaps, ambiguity about simultaneous releases and missing release timestamps cause explicit exclusion. The outcome is descriptive repricing; it cannot represent an executed strategy capturing an instantaneous jump.

**Model:** linear regression with fixed pre-release controls and an episode-level quantity surprise. Use quarter-clustered/wild-bootstrap inference where episodes are sparse. Prespecified confounds: scheduled CPI/PPI/NFP/GDP/FOMC/retail-sales releases, contemporaneous policy news, QRA versus ordinary announcement, tenor mix and pre-release rate volatility. The primary clean sample excludes overlapping high-impact announcement windows; a separately reported collision sample is sensitivity analysis.

**Secondary reconstruction:** if licensed futures are available, reproduce a price-derived announcement factor with loadings fitted only in training. Call it an after-release inferred-news instrument. Evaluate subsequent windows beginning after the factor was observed. Do not regress its own construction-window yield change on itself and call that independent forecast evidence.

**Falsification:** wrong-signed/indistinguishable response; similarly large effects on same-time matched non-announcement dates; pretrends before publication; response dominated by macro collisions; no adequate expectation history; unstable sign across volume and maturity-composition shocks. A price reaction alone cannot validate dollar surprise measurement.

**Current readiness:** official release/plan comparisons can begin; true market-expectation and licensed intraday gates are unresolved.

### H2 — Burden × fragility before auction

**Primary hypothesis:** ex-ante nominal duration burden interacts with already known rates fragility to improve prediction of pre-auction rate movement beyond either input alone.

**Decision:** three hours and one minute before the official competitive cutoff. The model receives only features already available then. T-1 close is a separate secondary decision, never substituted for the intraday one.

**Primary exposure block:** same-class announced nominal coupon DV01, next-three-trading-day known nominal coupon DV01, and one fixed interaction between auction DV01 and lagged log MOVE. Normalize using training-only statistics. If MOVE rights or PIT availability fail, freeze a separately named released yield-volatility proxy before outcome analysis; that is not the same MOVE model.

**Primary outcome:** own-tenor benchmark yield at cutoff minus one minute less its yield at cutoff minus 181 minutes, in basis points. A matching pre-release benchmark is required. Rate volatility/depth and post-result reversal are separate outcomes. Do not use today's dealer takedown or result bid-to-cover as pre-auction information.

**Models:** benchmark using Macro's previously known regime/volatility/funding/credit inputs; burden main-effects model; benchmark plus burden; and benchmark plus burden and the one interaction. Penalized linear prediction, with penalty selected only in training/calibration. Primary comparison is paired squared forecast error of interaction model versus benchmark-plus-burden. Also require improvement over the existing regime baseline, not just raw notional.

**Falsification:** no incremental performance, interaction sign reversal, dependence on a small crisis cohort, same-clock effects on week-matched controls, or loss of effect after proper input release lags. Public dealer inventories may be a predeclared secondary proxy, not a measured capacity numerator/denominator from private data.

**Novelty relative to D2 V1:** different information set, true intraday own-tenor yields and a prespecified burden×fragility interaction, not TLT's observed three-day pre-loss followed by a hoped-for three-day rebound. Without the required feed, H2-intraday is `NOT_TESTABLE`. A daily rates-volatility experiment must be a separately named reduced-form branch, not an announced replication.

### H3 — Net settlements and funding-market response

**Primary hypothesis:** known net coupon and bill settlement financing contributes incremental prediction of funding-spread change; the effect depends on already observed funding/liquidity conditions.

**Decision:** equity-session close on settlement S−1; the first forward version may instead use the last verified nightly publication time if the distinction is recorded. US Treasury settlement holidays and repo business days determine S.

**Inputs:** net coupon cash and net bill/CMB cash due on S, separately; known principal redemptions, SOMA treatment and buybacks; previously released TGCR/SOFR/IORB; lagged released dealer inventory; lagged released government-MMF AUM when entitled; last released reserve/ON-RRP state; and known tax/month-end/quarter-end/Fed-operation schedules. Use the canonical liquidity baseline. No S-day realized TGA, dealer holdings or MMF inflows are pre-settlement features.

**Primary outcome:** `(TGCR−IORB)_S − (TGCR−IORB)_(S−1)` in basis points, after its actual next publication. Register SOFR−IORB, S+1 cumulative change and S+5 persistence as secondary. Reserve/TGA balance-sheet reconciliation is an independent descriptive endpoint.

**Model:** baseline funding autoregression plus canonical previously known liquidity state and calendar controls; add net bill/coupon cash as a joint block; then one predeclared interaction block with prior funding scarcity. Use separate quantities for bill and coupon channels. The scarcity scalar must come from an existing frozen canonical input; a public-proxy variant is labeled separately. Interpolate neither dealer inventory nor MMF AUM between weekly reports. Scale stock levels using the most recently published GDP vintage only if that feature is admitted.

**Primary test:** paired out-of-sample squared forecast error improvement of baseline plus net-cash/interaction block over baseline. Additionally report both coefficients, signs and uncertainty; do not hide an opposite bill effect behind their sum. Week-block inference and same-weekday/seasonality matched settlement controls are mandatory.

**Falsification:** no improvement; sensitivity explained by tax dates or Fed interventions; sign wrong/unstable; feature unavailable until after S; gross issuance performs identically after proper netting; measured liquidity already exhausts information. For causal interpretation, report realized TGA as a mediator/accounting channel separately. Conditioning on it is not the total-effect estimate.

**First executable step:** create the settlement-cohort ledger and outcome-blind coverage report. Retrospective descriptive association may use final official outcomes with that limitation stated. The pre-settlement forecast requires recorded S−1 terms; final issue outcomes are never backfilled as forecasts.

### H4 — Post-result surprise and future rates behavior

**Primary hypothesis:** true auction tail, after the result is actually observed, improves near-future rates-volatility prediction beyond the immediately available price/rate-volatility baseline.

**Decision:** 60 seconds after `result_known_at`, provided the parsed record and source quote are available. If the system first sees results later, use the later actual cutoff. No return before that cutoff is credited to the forecast.

**Primary feature:** official stop-out yield minus the same security's licensed, timestamped WI yield immediately before auction cutoff. Quote-side convention, maximum quote age (60 seconds), benchmark identity and yield convention are frozen. Missing genuine WI quote means `TRUE_TAIL_UNAVAILABLE`; a constant-maturity close or high-minus-median auction yield cannot substitute.

**Primary outcome:** absolute own-tenor benchmark yield change during the 60 minutes following the decision cutoff. Normalize by training-only same-tenor scale for pooled estimation. Signed change and the first 1/3/5 trading-day returns are secondary. The initial result-release jump is observed context, not predictable post-result return.

**Models:** baseline using prices and volatility already observed at decision cutoff, plus true tail. Same-tenor historical bid-to-cover residuals and competitive allocations are a separately registered secondary block. Historical allocation baselines use only earlier published auctions. Changes to the old equal-weight composite are tracked as new formulations, not fixes that inherit validation.

**Falsification:** no improvement after excluding the release jump; effect disappears with quote freshness/matching; sign reversals or isolated crisis dependence; apparent benefit depends on corrected result data or late investor-class releases. Dispersion and bidder shares remain descriptive even under an untestable or null predictive result.

### H5 — T-1 equity downside warning, independent decisive gate

**Primary hypothesis:** auction-specific information available at T−1 close improves SPY downside prediction over the actual Macro risk baseline, with tolerable false alerts and opportunity costs.

**Decision:** 16:15 ET on session d, after verifying receipt of that session's equity close and every other feature. The predicted exposure window begins at the next session's open. This prevents an unrealistic trade at the same close used to compute the prediction. Separately report informational close-to-close forecasts; do not conflate them with execution.

**Primary descriptive target:** with `C_d` the dividend-consistent close and `σ_d` the sample standard deviation of the preceding 60 one-session log returns including d, define

`Z_d = min(log(C_(d+1)/C_d), log(C_(d+2)/C_d)) / (σ_d * sqrt(2))`.

Primary binary downside is `Z_d <= −1.5`. This is a close-observed two-session drawdown from the decision close; it is **not intraday maximum drawdown**. The fixed 1.5-volatility threshold is a research relevance choice, not a calibrated risk limit. Missing/corrupt/nonpositive scale causes abstention. QQQ at the identical target, signed two-session excess return, and realized variance are secondary; elevated variance alone never approves a sell direction.

**Inputs:** canonical risk regime/credit/MOVE/term-premium/liquidity-quality/Risk Radar as actually known at cutoff; announced upcoming coupon DV01 and settlement net cash; known calendar clustering; prior announcement revisions already public. Exclude future auction results, true tails, realized settlement data, later macro revisions and future price-derived announcement shocks.

**Model comparisons:** use B0–B6 below. Primary comparison is B5 versus B1. B6 is confirmatory only if its settlement-aligned addition was fixed before outcome access; otherwise secondary. Penalized logistic regression with one burden×fragility interaction is the default. Freeze coefficients and calibration after development. No numerical client probability is authorized by merely creating a fitted model.

**Virtual alert rule:** choose the threshold from the calibration fold for no more than 10% of eligible decision dates; freeze its numerical value before challenge/forward testing. At most one new alert episode in five trading sessions and 26 in any trailing 252 sessions, enforced causally. Apply identical rules to B1. No live alert is sent by the research harness.

**In-regime controls:** compare flagged dates with nonflagged dates sharing the pre-decision Macro regime, volatility bin, season and material macro-news exposure. Assess overlap explicitly. Match on variables observed before the decision, not on realized returns. Add week/day-matched pseudo-auction dates and constrained calendar permutations; if stratum support is inadequate, report an unidentified contrast.

**Hypothetical defense test:** for each alert, measure moving a fixed unit exposure to the existing eligible cash benchmark from the next session open through the second session close, then returning. Count overnight returns before the next open as unavoidable. Include the whole missed-upside distribution, measured execution fees/slippage, taxes excluded explicitly, and identical ordinary exposure outside registered windows. This remains simulated evaluation and cannot alter holdings. Do not choose costs or targets after seeing whether the strategy passes.

**Falsification:** proper-score improvement vanishes; in-regime/placebo matches perform equally; downside direction fails despite high variance; calibrated confidence fails; alerts are driven by baseline stress only; after realistic timing/costs the defense is worse; or sample size leaves useful effects unproven. Failure leaves context intact and risk/exit/cash authority unchanged.

## C. Baseline ladder and exactly-once use

| Model | Inputs / role |
|---|---|
| B0 | Training-estimated unconditional downside/base rate and same-class simple size rank |
| B1 | Existing Macro regime, rates volatility, term premium, credit, liquidity and Risk Radar; all from prior available vintages |
| B2 | B1 plus schedule proximity only |
| B3 | B1 plus face notional and tenor controls |
| B4 | B1 plus separately identified DV01, net cash and known announcement-revision/surprise fields; quantities and missingness explicit |
| B5 | B4 plus exactly one prespecified burden×fragility interaction |
| B6 | B5 plus a settlement-specific interaction evaluated only on an aligned settlement target/window |

This ladder is a comparison plan, not seven sources of evidence that may be counted independently. Every trial and feature family is logged. Shared term-premium/MOVE/credit inputs are consumed once. To claim increment over the actual baseline, that exact baseline must be reconstructed or logged; a public-proxy baseline has narrower acceptance.

## D. Inference, tuning and promotion rules

### D1. Locked modeling and multiple testing

Use a fixed regularization grid `{0.1, 1, 10}` with expanding chronological training validation. Record the precise library parameter convention because some use inverse penalty strength. Fit scalers, imputation choices, ranks, calibration and any factor/loadings inside training only. Use a linear calibration layer on the reserved calibration fold; isotonic is not admitted to the initial small-sample model.

Five primary family tests use Holm correction at familywise 0.05. Secondary prelisted asset/horizon results use BH-FDR q≤0.10 and are never a substitute for a failed primary test. Prespecify an estimator appropriate to the test: explanatory coefficient inference for H1, and paired forecast-loss differences for H2–H5. Penalized coefficient t-statistics are not the predictive test.

Use time blocks that preserve dependence across nearby auctions and shared outcomes: a 20-trading-session block bootstrap, 10,000 resamples, seed `20261008`, for paired forecast differences. H1 sparse quarterly episodes use quarter-level/wild-cluster inference. Report uncertainty sensitivity to 10/40-session blocks as secondary without picking the best. Outcome-window purging, not a small fixed HAC lag alone, addresses overlapping labels.

### D2. Research grades

- `MEASURED_DESCRIPTIVE`: reconciled observations and clearly delimited event associations; no prospective claim.
- `RETROSPECTIVE_ONLY`: historical analysis with imperfect vintages or already viewed outcomes.
- `INSUFFICIENT_PIT`: necessary prior information or publication proof unavailable.
- `NULL_NO_GO`: the registered predictive candidate fails its prespecified promotion gates with adequate evidence; the descriptive product remains valid.
- `SHADOW_ELIGIBLE`: a candidate passes retrospective predictive, clock, placebo and calibration checks and may be forward logged by an admitted existing owner. No client probability/action effect follows automatically.
- `PROSPECTIVE_PASS`: the frozen forward version meets the same substantive checks at the fixed endpoint; decision authority still requires the separate existing-owner gate.

### D3. Initial quantitative promotion requirements

These thresholds are proposed outcome-blind engineering choices for the initial research version and must be adopted before outcome analysis:

1. **PIT:** no known leakage violations in any included row; all primary features trace to recorded vintages. There is no tolerated percentage of known future leakage.
2. **Prediction:** at least 1% relative improvement in mean squared error (continuous H2/H3/H4) or Brier score (H5) over the primary registered baseline, with a positive paired improvement interval after the primary family correction. H5 log loss must also improve in point estimate. One favorable metric cannot offset failed timing or placebo.
3. **Stability:** same direction of improvement in both chronological halves of the challenge/forward window; the result must not depend entirely on one crisis. If either half lacks usable variation, label the stability requirement unresolved.
4. **Calibration for H5:** show reliability bins, calibration intercept/slope and uncertainty. Candidate pass requires slope in [0.8,1.2], absolute intercept ≤0.10 on the log-odds scale, and no material underprediction in the alerted tail. Sparse bins block a claim of calibrated tail probability. These are not proof of performance by themselves.
5. **Alert value:** meet the frozen alert budget; conditional precision must exceed the same-regime matched baseline with its paired interval above zero. Report false-positive and missed-event costs as distributions. H5 cash-defense eligibility additionally requires positive paired value after audited execution costs and no advantage arising solely from duplicated existing risk decisions.
6. **Power and small samples:** retain the actual event and independent-week counts. If the fixed evaluation cannot distinguish the economically useful improvement from noise, report insufficient evidence and do not promote. Do not broaden the target/horizon/asset universe after seeing scarcity of positive events.

These requirements are deliberately stricter than merely a positive t-statistic. They do not promise that the first one-year forward record will settle a subtle effect. The initial completed product may therefore legitimately remain context-only.

## E. First bounded implementation/evaluation tasks

1. **Outcome-blind eligibility audit:** produce the exact episode manifest and column-level availability coverage without loading future return labels. Hand-check ten selected events, including each instrument class and at least one correction/reopening/holiday case supplied by the official-source audit.
2. **Feature contract and replay gate:** assert `max(input_known_at) <= decision_cutoff` for every derived feature and baseline input. Fixtures must fail on future result fields, interpolated weekly records, revised-old observations and CUSIP-only joins. This is a meaningful leakage test, not an implementation-mirroring test.
3. **Settlement ledger first:** reconcile net coupon versus bill/CMB cash by S, with SOMA/buyback/interest conventions. Attach actual next-release TGCR/SOFR observations as outcomes. Begin with descriptive completeness and accounting, then run H3 only on eligible prior snapshots.
4. **Freeze:** parent commits adopted hypothesis/model/data-manifest digests and writes them into the existing evaluation/continuity owner. Only then expose challenge outcomes or start admitted prospective logging.
5. **Independent checks before any forecast consumer:** audit a raw-source event casebook, feature clocks, same-regime placebos, multiple testing and actual consumer authority. Existing nulls stay beside every verdict. No new database, calendar authority, notifier or exit-control surface is required.

The branch is ready for canonical adoption/implementation by the parent after its source-custody reconciliation. No empirical execution, registered timer, forecast model, released feed or consumer promotion has occurred in this bounded support task.
