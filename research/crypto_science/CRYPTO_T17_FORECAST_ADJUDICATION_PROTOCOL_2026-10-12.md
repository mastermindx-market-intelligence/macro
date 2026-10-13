# Crypto T17 forecast adjudication protocol

Date: 2026-10-12. Lane: `claude/cx-t17p-20261012`. Status: protocol and scoring-property tests only. This document fills no cell. The outcome column below stays empty until a non-builder reviewer of record scores a matched forward record.

Search bounds for the census: `engine/**/*.py` and `scripts/**/*.py` for `brier|log_score|logloss|calibrat|coverage|abstain`, plus the files cited by path below. `data/` was not read (sparse checkout omits it). An on-disk claim about `data/` is UNVERIFIED.

## Census

Proper scores that exist and are the ones this protocol calls:

| Function | Role |
| --- | --- |
| `engine.grading_stats.brier_decomposition` | Brier score and Murphy split. No sample-size floor other than empty input (`engine/grading_stats.py:914-1022`, score at line 986). |
| `engine.validation.brier_reliability` | Brier, skill vs in-sample base rate, reliability bins. Returns `{}` when finite pairs `< 30` (`engine/validation.py:527-550`). |
| `engine.seasonality.calibration.log_score` | Mean negative log-likelihood. Named abstention when finite pairs `< MIN_METRIC_ROWS` (30) (`engine/seasonality/calibration.py:131`, `663-692`). |
| `engine.validation.expected_calibration_error` | ECE and MCE. `{}` when finite pairs `< 30` (`engine/validation.py:573-596`). |
| `engine.validation.crps_ensemble` / `crps_score` | Proper score for an issued distribution (`engine/validation.py:834-874`). `{}` from `crps_score` below 10 finite pairs. |
| `engine.grading_stats.reliability_curve` | Equal-width bins plus Wilson interval (`engine/grading_stats.py:829-911`). |
| `engine.vol_fitted_har.log_loss` | Squared log error on positive variances (`engine/vol_fitted_har.py:300-303`). Not the binary log score. |

Named refusal, not a number: `engine.validation._rc_abstain` (`engine/validation.py:1046-1053`); seasonality `_null` (`engine/seasonality/calibration.py:273-277`); `engine.explanation_memory._compute_brier` turns a short sample into `brier: None` (`engine/explanation_memory.py:455-479`).

Measurement surfaces, none of which adjudicate a crypto probability:

- Calibration Lab is the page `scripts/build_measurement.py` renders from `templates/measurement.html.j2` with `page_title="Calibration Lab"` (`scripts/build_measurement.py:1-18`, `2002-2004`). It is the cycle-intelligence measurement hub.
- `engine/calibration_hub.py` is a display-only desk track-record surface. Its promotion constants (`engine/calibration_hub.py:47-56`) belong to not-falsified desk rates. They are not a crypto probability bar.
- `engine/seasonality/calibration.py` is the biopharma seasonality forward chain (`CALIBRATION_SCHEMA` at line 115, `tier="shadow"`). Its `evaluate` bundle (`1063-1106`) is the pattern for "every slot present, unestimable slots named". It is not retargeted at crypto by this protocol.
- `engine/biocatalyst/coverage_epoch.py:derive_coverage_denominator` (`204-211`) records a denominator from the source's own total. Different domain. The rule reused here is only: the denominator is recorded, not inferred.

Trial history and forward ledgers are different objects:

- `data/trial_ledger.jsonl` is the multiple-testing memory of `engine.trial_ledger.TrialLedger` (`engine/trial_ledger.py:48-49`, append in `log_trial` / `log_grid` / `log_declared_budget`). `.github/workflows/signal-foundry.yml:13` commits that file on a Wednesday cron. That workflow is not the nightly collect lane.
- Nightly is the sole advancer of the forward ledgers the collect path grades: `scripts/collect.py:1172-1176` (`COLLECT_LANE=nightly`), the same gate in `engine/foresight_divergence.py:236-242`, and the seasonality module statement that nightly is the sole advancer and the module writes nothing on import (`engine/seasonality/calibration.py:85-87`). `scripts/run_transmission_calibration.py:20-21` states the same shape for its own artifact: a worktree run is not the writer.
- `engine/btc_override_ledger.py` grades four frozen sub-claims of the `midterm_blackout` override into `data/vector/override_ledger.jsonl`. Header: monitoring only, zero allocation authority (`engine/btc_override_ledger.py:1-19`). `scripts/build_vector.py:4544-4548` calls `stamp` and `score` during the vector build. The module file has no `COLLECT_LANE` gate (search of that file for `COLLECT_LANE`: no match). This ledger is not the per-horizon probability ledger.
- No Python writer of a per-horizon × per-asset crypto probability forward ledger turned up under the patterns `crypto.*forward_ledger` and `forward_ledger.*crypto` in `*.py`. Whether such a file already sits under omitted `data/` is UNVERIFIED. This lane does not create one.

`engine/btc_decision.py` `build_decision` (`202-393`) emits `btc.decision/v1`. Scoreable-looking fields and what they actually are:

- `status` `"ok"` or `"unavailable"` (`220`, `390`). A state, not a probability.
- `final.exposure` in `[0, 1]`, `final.exposure_pct`, `action_code` in `{SET_EXPOSURE, INCREASE_EXPOSURE, REDUCE_EXPOSURE, STAY_OUT, HOLD_EXPOSURE}` (`169-199`, `381-386`). An allocation projection. `authority.authority_class` is `"decision_bearing"` (`226`). Not a probability of an up move.
- `raw_model.master_score` copies `master["score"]` (`330`). A score of unspecified probabilistic meaning inside this module. Not a Brier input unless a later pre-registration defines the event.
- `receipts` (`349-358`) carry `authority_class: "context_only"`: `kelly_risk_budget_pct`, `continuous_momentum`, `categorical_momentum`, `risk_index`, `risk_regime`, `valuation_state`, `market_extreme`. Context. Not forecasts and not sizing authority.
- `project_budget` (`396-435`) is fail-closed: `status` `"ok"` only when schema, decision status, `integrity.ok`, and an in-range `exposure_pct` all hold. Otherwise `status` `"unavailable"` and `final_exposure_pct` is `None`. Diagnostic finals on an integrity failure are not a budget.

Crypto consumer contracts this protocol is allowed to score only after a matched ledger exists:

- `scripts/build_crypto.py` writes `crypto.class_state/v1` with `tier: "display"` and `display_only: True` (`495-528`): `universe_coverage.{as_of, listed, requested, excluded, breadth}`, market stance fields, flow states, heat states, per-asset `trend` / `risk` / `relative` / `coverage`. `_allocation` (`244-328`) splits the canonical BTC budget into `btc` / `eth` / `alts` / `cash` or returns a named unavailable reason (`193-242`). Those shares are a split of one budget, not three forecasts.
- `scripts/build_vector.py` `emit_crypto_cockpit_json` writes `crypto.cockpit/v1` with `display_only: True` (`781-831`). `hero.master_score` and `hero.exposure_pct` come from the master band and `project_budget`. The cockpit does not re-score BTC (`793-795`).
- `mastermind.vector_risk_strategy.v2` (`196-333`) keeps a missing allocation as null. A real `0` stays `0`. Equity becomes unknowable after a gap. `availability_clock` is `NOT_ASSERTED`.
- `env_probabilities` (`967-976`) publishes `p_bull_7d` / `p_bear_7d` as `round(100 * p)` for horizon `config.yml` `vector.scenarios.prob_horizon_d` = 7 (`config.yml:6024`). When `p is None` it returns `None`, not 50 (`973-974`).
- `scenarios_3d` (`979-1002`) asks `_cond_up_prob` for horizon 3 (three bars of the close index, `914`). When `p is None`, `bull_prob` is set to 50 (`995`).
- `_conviction` (`1191-1236`) maps a missing `p_bull` to displayed `p_bull: 50`, `p_bear: 50` (`1198-1200`).
- `forward_risk` (`1046-1072`) returns conditional drawdown moments (`avg`, `tail`, `up`) for the live `risk_index` band. `_fwd_dd` returns `None` when `n < 20` (`1040-1041`). A missing `risk_index` or a thin band returns `{"tail": None}` (`1052-1063`). These are moments, not probabilities.
- `engine/crypto_universe.py` `breadth_read` (`158-182`) is the share of eligible names with a positive reported 30-day return. A missing return is excluded, not counted as zero (`161-162`). Below 10 eligible names the state is `"Building history"` and `value` is `None`. Not a forecast.
- `engine/btc_impulse_radar.py` `compute` returns `{"ok": False, "reason": ...}` when disabled or when signals are missing (`241-257`). A radar score is not a probability of a pre-registered event.

The published short-horizon probability is capped. `config.yml:6023-6032`: shrinkage `prob_shrink_alpha: 10`, cell floor `prob_min_cell_n: 20`, cap `[prob_floor, prob_ceil] = [0.30, 0.70]`, macro tilt ±5pp, cycle tilt ±5pp. `_cond_up_prob` applies that cap at `scripts/build_vector.py:963`. A cell thinner than `prob_min_cell_n` falls back to the momentum marginal and is still a number (`933-934`). That fallback is an issued marginal, and the cell label must say so.

## 1. Qualification table

One row is one `(asset, horizon, forecast object)`. Instrument rows do not imply each other and do not imply a market-wide row. The `outcome` cell is filled only by the reviewer of record, and only with `QUALIFIED`, `UNAVAILABLE`, or `ABSTAIN`.

| id | asset | horizon | object | outcome | QUALIFIED requires | UNAVAILABLE when | ABSTAIN when |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BTC-P-3D | BTC | 3 bars of the close index | raw `p` from `_cond_up_prob(..., 3)` before the `else 50` in `scenarios_3d` | | Matched ledger; Brier and log score on the published capped probability; both beat the point-in-time climatology by the reviewer's pre-registered margin; catalogue header attached; non-builder sign-off | `p` is missing, the close needed for the pair is missing, or the slot was never issued | Issuer refused, finite `n < 30`, or the hypothesis was scored and missed the margin. Named reason |
| BTC-P-7D | BTC | `prob_horizon_d` = 7 | `env_probabilities` `p_bull_7d`, which is `None` when `p` is missing | | Same as BTC-P-3D, at the 7-bar operating point | `p_bull_7d` is `None` or the outcome bar is missing | Same |
| BTC-DD | BTC | the horizon passed into `forward_risk` (comments name 3 and 7; Kelly text names 90) | `avg` / `tail` / `up`, or a separately pre-registered binary "drawdown beyond X" | | Moments: a proper score for that functional (squared error for a mean, CRPS if a distribution is what was issued). A binary event uses Brier and log score, and X is frozen before outcomes are read | `tail` is `None` (`n < 20` or no `risk_index`) | A calibration claim was tested and failed, including `stable: false` read as a pass |
| BTC-ALLOC | BTC | none | `btc.decision/v1` `final.exposure` via `project_budget` | | Not a probability. No Brier. A financial-response study is a different pre-registration and still writes no live sizing | `project_budget.status` is `"unavailable"`, integrity is not ok, or `build_crypto._allocation` returns an `authority_error` | An integrity error is a refusal. Diagnostic finals that `project_budget` withholds are not scored |
| ETH-STATE / SOL-STATE | ETH, SOL | none issued | `crypto.class_state/v1` `assets.*.trend/risk/relative` | | No proper score until a probability and a binary event are pre-registered for that asset and horizon | State missing or the coverage note says the history is absent | A label is not promoted to a predictor |
| CLASS-SPLIT | BTC, ETH, alts as shares of one BTC budget | none | `build_crypto._allocation` | | Not three forecasts | Named `CLASS_SPLIT_*` or canonical-decision unavailable reason | |
| BREADTH-30D | universe snapshot | trailing 30d descriptive | `breadth_read` | | Not a forecast. Report `eligible`, `excluded`, `required` | `available` is false, state `"Building history"`, `value` is `None` | |

`QUALIFIED` evidence, all of it, for a probability row: a forward record advanced only by the nightly lane; pairs that satisfy the matched-data rule; the probability that was actually publishable at the stamp (after shrinkage, tilt, and the `[0.30, 0.70]` cap); Brier and log score both strictly better than the point-in-time climatology under the pre-registered margin and the overlap-aware interval; the catalogue header of section 3 printed beside the scores; sign-off by the reviewer of record. Ranking the cell against other cells is not one of these items.

`UNAVAILABLE` is missing data. It is not a zero, not 50, and not a score.

`ABSTAIN` is a refusal or an unsuccessful hypothesis, with a reason string. It stays in the catalogue.

Until the reviewer of record writes the usefulness margin, every probability row's usefulness result is `ABSTAIN` with reason `margin_not_preregistered`. This lane does not invent that margin. `engine/calibration_hub.py:47-56` is not reused as a substitute.

## 2. Proper scores and the matched-data rule

Binary outcome `y ∈ {0, 1}`, issued probability `q ∈ (0, 1)`, empirical frequency `p`.

Brier, the expression both `brier_decomposition` (line 986) and `brier_reliability` (line 538) compute:

```
BS = mean_i (q_i - y_i)^2
E[BS(q)] = (q - p)^2 + p(1 - p)
```

Lower is better. The minimum is `p(1 - p)` at `q = p`.

Log score, the expression `log_score` computes (line 678), natural log, `q` clipped to `[1e-6, 1 - 1e-6]` (`_EPS`, line 136):

```
LS = - mean_i [ y_i log q_i + (1 - y_i) log(1 - q_i) ]
E[LS(q)] = - [ p log q + (1 - p) log(1 - q) ]
```

Lower is better. The minimum is at `q = p`.

`log_score` also returns `base_rate_log_score` from the full-sample outcome frequency and sets `base_rate_is_in_sample=True` (`684-692`). That reference saw the outcomes. It is not the climatology in the matched-data rule. The point-in-time reference already implemented for another domain is `chronological_baseline` (`831-840`): the baseline for row `i` is the mean outcome among rows whose outcome had already resolved when `i` was issued. Rows with too little prior history are excluded from that score and counted in `n_skipped_thin_history` (`840-841`, `865`). Crypto does not yet call that function. A skill ratio against the in-sample base rate does not qualify a cell.

CRPS, when the issued object is a distribution (`838-839`):

```
CRPS(F, y) = E|X - y| - (1/2) E|X - X'|
```

Lower is better. A point forecast's CRPS is absolute error, which is proper for the median, not a substitute for Brier on a probability.

Matched-data rule. One scored pair is all of the following:

- Same asset. A BTC pair is not an ETH pair and not a class-split pair.
- Same horizon. The 3-bar probability, the 7-bar probability, and a drawdown moment are different rows. Their errors are not pooled into one Brier.
- Same information set. `q` is the number publishable at the stamp: the capped, shrunk, tilted probability, not an uncapped in-sample cell rate and not a probability that was rewritten after the outcome printed.
- Outcome anchor: the first close strictly after the stamp. That is `engine/grading_stats.py` `CONVENTION` (`45-49`). The stamp bar itself is not the forward outcome.
- Both `q` and `y` finite. A non-finite side is not a scored pair. `brier_reliability` and `log_score` already drop those pairs (`validation.py:534-535`, `calibration.py:671-672`). Dropping them from the score is correct. Dropping them from the catalogue is not.
- Overlapping horizons are not independent draws. Daily stamps with a 7-bar forward window share path. The Wilson interval understates that uncertainty (`grading_stats.py:861-866`). The Brier on overlapping rows is biased toward looking precise (`957-960`). Uncertainty uses a block bootstrap that moves a whole overlap block together (`grading_stats.py:20-26`), or the seasonality cluster bootstrap when the cluster key is a date (`calibration.py:70-77`). An iid `n` is not the evidence count.

`brier_reliability` reports a bin only when that bin holds at least 10 finite pairs (`545`). `reliability_curve` emits every non-empty bin. ECE's `N` is the finite-pair count (`585-594`). Print the catalogue `n_C` beside it.

## 3. Bins, uncertainty, coverage, abstention

Bins. Equal-width on `[0, 1]`, default 10, matching both existing functions. The last bin includes `q = 1`. A bin with no scored pairs is omitted. A bin with fewer than 10 scored pairs is unreported by `brier_reliability` and is not stored as a gap of zero. ECE skips empty bins and returns `{}` below 30 finite pairs. Below that floor the cell's calibration result is an abstention, not an ECE of 0.

Uncertainty, kept separate:

- Per-bin Wilson interval on the bin's observed rate (`wilson_ci`, `grading_stats.py:57-64`), labeled as a binomial interval that ignores overlap.
- Block or cluster interval on the score and on the difference versus the point-in-time climatology, for any horizon that overlaps.
- `n_skipped_thin_history` and every other side count, printed, not folded into the interval as if those rows had been scored.

Coverage uses the all-catalogue denominator. `C` is the recorded set of issued slots for that row id. It is written down when the slot is issued, not reconstructed from the rows that happened to score.

```
n_C = n_scored + n_abstain + n_unavailable
scored_share = n_scored / n_C
abstain_rate = n_abstain / n_C
unavailable_rate = n_unavailable / n_C
```

An abstention is counted. Removing abstentions from `n_C` raises `scored_share`. That raised share is not coverage. The hit rate among scored pairs is a third fraction and is not coverage either.

`breadth_read` excludes a missing 30-day return from a descriptive ratio (`crypto_universe.py:161-175`). That exclusion is right for breadth, because a missing return is not a vote. It is the wrong denominator for an issued forecast. An issued forecast that later abstains was in `C` on purpose.

Existing scorers do not implement `n_C`. They report the finite-pair `n`. The catalogue header ships in the same payload as the score. A payload that carries a Brier and no `n_C` is incomplete and is not `QUALIFIED`.

## 4. Usefulness at the operating point

The operating point is the probability a reader would have been shown: `_cond_up_prob` after shrinkage, after the macro tilt, after the cycle tilt, and after the clip into `[0.30, 0.70]` (`scripts/build_vector.py:923-963`, `config.yml:6025-6032`).

Usefulness is the proper score of that number against the matched outcomes, compared with the point-in-time climatology, by a margin the reviewer wrote down before looking at the score. A cell that only ranks well, a cell whose uncapped rate looks sharp, and a cell that beats the in-sample base rate inside `log_score`'s `skill` field, are not useful at the operating point. The cap means a displayed 70 is not a claim of 70 if the raw cell was higher; the scored `q` is the capped one, because that is what was publishable.

A marginal fallback (`n < prob_min_cell_n`, line 933) is the operating point only if the published label says it is the marginal. Scoring it as if it were the thin cell is a different experiment.

Nothing in this section promotes a row to authority. Display of a probability can continue while the row is `UNAVAILABLE` or `ABSTAIN`. Promotion is a separate gauntlet and is not granted here.

## 5. Financial response value

Three terms. They are not netted into one number before each is shown, and each has its own uncertainty.

1. Cost. Fees, spread, funding, slippage. A cash term. Its interval is not the interval on the price move.
2. Delay. The position that could have been held only after the forecast existed: first close strictly after the stamp, plus whatever lag the page actually had. The same-bar fill is not the response. `availability_clock: NOT_ASSERTED` on `vector_risk_strategy.v2` (`scripts/build_vector.py:302`) means the delay term is `UNAVAILABLE` until a clock is recorded.
3. Missed upside. The favorable move on slots where the cell abstained, was unavailable, or held less than the later move. A separate term from losses on positions that were taken. The override ledger's `re_entry_captures_recovery` sub-claim (`engine/btc_override_ledger.py:68-73`) is one frozen question about one gate, not this term in general.

`scorecard` and `alloc_equity` (`scripts/build_vector.py:842-874`) forward-fill the allocation and `fillna(0)`. A missing allocation becomes cash on that path. That path is not the adjudication P&L. The gap-aware series is `_risk_strategy_payload` (`224-237`): after a missing decision, later equity is null, and a missing observation is not a trade marker (`239-253`). A real 0% allocation stays 0% (`198-201`).

`receipts.kelly_risk_budget_pct` and `final.exposure` are not inputs to a live size. This protocol writes no live sizing.

## 6. Independence

The reviewer of record is a non-builder Opus seat. This Grok lane writes the protocol and `tests/test_crypto_forecast_scoring_properties.py`. It does not fill an outcome cell, does not sign `QUALIFIED`, and does not inherit review rights by importing `engine.seasonality.calibration.log_score`.

The author of a model does not adjudicate that model. A lane that edits `engine/btc_signals.py`, `scripts/build_vector.py`, or `engine/btc_decision.py` is a builder of the object under review and is not the reviewer of record for that object. The seasonality `evaluate` author is not the reviewer of a crypto cell either. The seat that signs is outside the builder set for the cell.

## 7. Silent-failure rule

An unsuccessful hypothesis is reported as unsuccessful. It is not renamed into a delivered predictor. Research R1–R9 negative results stay unpromoted. A null score is not a zero score.

Existing refusals that already follow the rule, and must stay refusals:

- `brier_reliability` and `expected_calibration_error` return `{}` below 30 finite pairs, not a score of 0 (`validation.py:536-537`, `582-583`).
- `log_score` returns `abstained: True`, `value: None`, and a reason `log_score_unestimable:...` (`calibration.py:676-677`, `_null` at `273-277`).
- `_rc_abstain` returns `statistic: None`, `p_value: None`, `abstained: True` (`validation.py:1046-1053`).
- `build_decision` starts at `status: "unavailable"` and `project_budget` will not promote an integrity failure (`btc_decision.py:220`, `418-432`).
- `btc_impulse_radar.compute` returns `ok: False` with a reason (`btc_impulse_radar.py:245-257`).
- `breadth_read` returns `value: None` and `"Building history"` below its floor (`crypto_universe.py:176-178`).
- `forward_risk` returns `tail: None` rather than a dip of 0 (`build_vector.py:1052-1063`).

Existing substitutions that adjudication must not score as if they were issued probabilities:

- `scenarios_3d` sets `bull_prob` to 50 when `p is None` (`scripts/build_vector.py:995`). Fifty there is a display stand-in, not a measured probability.
- `_conviction` copies that stand-in into `p_bull: 50`, `p_bear: 50` when its input is `None` (`1198-1200`).
- `env_probabilities` does not do this: a missing `p` stays `None` (`973-974`). The honest 7-bar input is that `None`.
- `scorecard` turns a gap into 0 after a forward fill (`850`). That 0 is not "the model chose cash".

The proposed machine-readable flag is the unapplied patch `research/crypto_science/patches/cx-t17p-20261012__build_vector.py.patch`. It adds `probability_issued` and does not change the displayed 50. Until that patch is applied by the integration writer, a scorer reads `_cond_up_prob`'s `p` and `env_probabilities`'s `None`, and does not read `scenarios_3d.bull_prob` or `_conviction.p_bull` as an issued probability.

A cell that was tried and missed its margin is `ABSTAIN` with the reason that names the miss. It is not republished as a predictor that "worked" under a different label, a shorter horizon, or a dropped-abstention denominator.

## What this lane does not do

No new engine module. No forward-ledger append. No network call. No `data/` read. No cell verdict. No live sizing. No change to `scripts/build_vector.py` inside this worktree; the shared-file delta is the patch named above.
