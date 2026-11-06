# CRYPTO T12 evaluation contract (DRAFT)

**Status:** DRAFT frozen 2026-10-12. This file is a measurement protocol. It records no market result, changes no sizing authority, and adds no ledger, daemon, collector, or experiment platform.

**Lane:** `claude/cx-t12p-20261012`. **Candidate base:** commit `78e0717c235f749602bffdf3426a70f5e72ebf1f` on `origin/main` `3634a83542de4eb1af47d73620f6c02ef1ebca33`, carrying PR #8050 R2 source `fd8095012e91026640ae07e092ae6272a2e7d30c` (merge-base `7150f29a765387f1c14fbae086314af6e0d6bddc`). **Workstream:** `agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md`. **Budget authority:** `agentos/decisions/DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY.md`.

User-facing copy that later cites this protocol says the comparison is measured under this protocol, or that the sample is `insufficient-n`, or that the input is `unavailable`. A confirmation adjective that implies a passed gauntlet is out of bounds in that copy.

## 1. The one question

On a decision date when `btc.decision/v1` is integrity-valid, does the incumbent class overlay’s BTC / ETH / alts split of that fixed total budget change the next 90-calendar-day price path of the sleeve relative to a budget-matched baseline that holds the same total in BTC?

That is the whole confirmatory question. It is one class-rotation comparison inside one cycle horizon. It is an instrument-sleeve path comparison. It is not a Bitcoin market verdict, not a crypto-wide verdict, and not permission to change the total budget.

Authority stays where DEC-CRYPTO-H5 put it (`agentos/decisions/DEC-CRYPTO-H5-BTC-BUDGET-AUTHORITY.md:6-10` and `:67-77`): `btc.decision/v1.final.exposure_pct` is the total; the overlay only splits it; cash is the residual `100 - budget`; an invalid decision stays non-actionable. A later architecture decision is what would move that owner (`:86-90`).

Display of the existing overlay continues whether this study is unrun, short, or unfavorable. A null sample does not block the display build. Promotion of the overlay into sizing authority is outside this protocol.

## 2. Incumbent objects this protocol reuses

Trial accounting has one implementation: `engine/trial_ledger.py`. `TrialLedger` is line 66. The canonical file is `DEFAULT_PATH = data/trial_ledger.jsonl` (line 49). A declared floor is `log_declared_budget` (line 202) or `register_trials` (line 296). `effective_n` (line 257) is `literal_n` unless a declared floor is higher; correlation credit stays off. `with_declared_budget` (line 236) writes a temp file and is the wrong handle for this family.

`engine/validation.py` is the metric owner the ledger feeds. `deflated_sharpe` (line 254) reads `ledger.effective_n(family)` and rejects a call that passes both `n_trials` and `ledger` (lines 280-283). `purged_folds` (line 333) drops `embargo` rows at each fold’s right edge. `cpcv_paths` (line 370) purges both sides of each test block. `block_bootstrap_ci` (line 455) is a circular block bootstrap, `block=21`, `B=5000`, `seed=7`, and returns `{}` when `n < max(block * 3, 60)` (line 463).

`scripts/check_trial_registration.py` lints harnesses whose names start with `validate_` or contain `_phase0` / `_phase1` (lines 38-40). `scripts/calibrate_vector.py:767` already declares family `"vector"` from `vector.calibration.n_trials` plus override dof. That family is the BTC allocation calibrator. `alt_cycle_leader` appears there only as a whipsaw column (`scripts/calibrate_vector.py:854`). This protocol uses a different family on the same ledger file so the class comparison cannot hide inside, or inflate, the vector DSR count.

The impulse falsifier is a different question and stays on its own gate. `engine/btc_impulse_radar_backtest.py`:

| Piece | Frozen meaning | Line |
| --- | --- | --- |
| Clock | Unique increasing daily dates; a `DatetimeIndex` must be normalized | 69-73 |
| Target | Down if the min close on the next `LABEL_H=3` observations is ≤ −5% of close[t]; up if the max is ≥ +5%. Both are nullable | 43-45, 58-86 |
| Maturity | Full 3-observation window required, including when a partial window has already crossed ±5%. A dated window that skips a calendar day is unscored | 66-67, 80-83 |
| Split | Full sample, and holdout `index >= 2024-01-01` | 43, 136-137 |
| Metric | Lift = P(label \| fire) / P(label) on rows where fire and label are both non-null | 89-95 |
| Uncertainty | Circular shift of the fire mask, `PERM_N=2000`, RNG seed 0, p = (ge+1)/2001 | 46, 98-120, 138 |
| Act rule | `d2` holdout lift ≥ 1.5, `d3` and `u1` ≥ 1.3, plus p ≤ 0.05, plus ≥ 30 holdout fires | 48-55, 151-166 |

R2’s stored-snapshot readout said none of the three legs cleared that gate (`research/CRYPTO_SCIENCE_R2_TIMING_REPAIR_RESULTS_2026-09-28.md` on `fd8095012e91`, decision paragraph). This contract does not retune those floors and does not treat that readout as T12 evidence.

`vector.calibration` (`config.yml:6137-6145`) is also a different object: `start_date=2015-01-01`, `split_date=2021-01-01`, `forward_days=[7, 30, 90]`, `cost_bps=10`, `n_trials=65`, `cv_folds=5`. T12 borrows the 90-day member of `forward_days` as its horizon. It does not borrow `split_date`, `n_trials=65`, or the 2024-01-01 impulse holdout as a fresh test cut. R1 already recorded that another split at 2024 is not new evidence (`research/CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md` §8 on `fd8095012e91`).

## 3. Transforms (frozen)

No new transform, score, or learner. The candidate path is the live split arithmetic.

1. Budget `B_t` is the integer `final_exposure_pct` from an integrity-valid `btc.decision/v1` whose `as_of` equals the clock date. `scripts/build_crypto.py:_allocation` (`:256-265`) is the acceptance rule: schema `btc.decision/v1`, `status=ok`, `integrity_ok is True`, integer percent in `[0, 100]`.
2. ETH/BTC level, 350-day mean (`min_periods=100`), 56-day slope, and 1095-day percent-rank (`min_periods=120`) are `engine/alt_cycle.py:ethbtc_signal` (`:19-37`) with `config.yml:6108-6113`.
3. Season lines stay 0.05 and 0.07 (`config.yml:6109-6110`; `alt_cycle.py:33-34`).
4. Alt-season score stays the 0.60 / 0.25 / 0.15 blend, slope term `50 + clip(slope * 200, -50, 50)`, dominance term `clip((70 - dom) / 0.30, 0, 100)`, weights renormalized when a leg is absent (`alt_cycle.py:40-57`). Buckets stay `<25` / `>75` / else Mixed (`config.yml:6114-6115`).
5. Regime stays `engine.cycles.regime_state`: `bear` if score ≤ −1.5, `bull` if score ≥ 1.5, else `neutral` (`engine/cycles.py:895-958`). `scripts/build_crypto.py:299-304` reads it through `btc_mtf.mtf_ladder(...).ladder.regime`.
6. Cell table stays `ALLOC_GRID` (`engine/alt_cycle.py:63-77`). The cash column of that table is not applied. Live arithmetic drops it and renormalizes the BTC, ETH, and alts legs onto `B_t` (`scripts/build_crypto.py:305-320`): `btc_pct = round(B_t * w_btc / w_sum)`, `eth_pct = round(B_t * w_eth / w_sum)`, `alt_pct = B_t - btc_pct - eth_pct`. Cash display remains `100 - B_t`.
7. SOL/ETH `beta_ratio` and `breadth_view` stay display-only (`alt_cycle.py:79-111`) and are outside the scored path.
8. Dominance enters only with a dated print whose publication time is at or before `as_of`. The module docstring says dominance and TOTAL2–3 are current-context snapshots (`alt_cycle.py:4-7`). A single current CoinGecko print applied to earlier dates is forbidden. When no eligible dominance print exists, the 0.15 leg is omitted and the score renormalizes, and the row carries `dominance=unavailable`.
9. Every rolling value and the regime score are computed on the prefix of observations dated at or before t. A full-sample value at t that differs from the prefix value makes that date `unavailable`. R1 showed a non-prefix-stable resample in `bottom_pressure`; this protocol does not assume `regime_state` or the ETH/BTC rank inherited the same repair. Prefix equality is a precondition, and it is unmeasured in this lane.

Freeze pins (sha256 of the cited line ranges on `78e0717c23`):

| Range | sha256 |
| --- | --- |
| `engine/alt_cycle.py:19-77` | `12255528032d52df85e4678bc010e4686cd8f28c800f3265b6084e4614998395` |
| `config.yml:6108-6118` | `6253ae4060862c7cc1c765ff1edcfd6fda104948897a5db836b95da94b2fe936` |
| `scripts/build_crypto.py:292-328` | `3342a472745a3f5a83763aafaf55988e6b1e567ac2bcec2a4352b09f1994469c` |
| `engine/cycles.py:958` | `dac878e2c7104cacb0c1b9892a3a33e65623c446dec6b22f56a9153ac1e3eb8f` |

A byte drift in any pin is a new trial. It is logged before any outcome is read, and it is not reported as this protocol’s candidate.

`ethbtc_signal` forward-fills ETH onto the BTC index with no age cap (`alt_cycle.py:24`). The measurement mask is stricter: if the last real ETH close is more than one daily bar before t, the ETH leg is `unavailable` and the date is ineligible. Implementing that mask is later harness work. This lane does not patch `alt_cycle.py`.

## 4. Target

Primary target, both paths, same function:

`R_90(t) = sum_i (w_i,t / 100) * (P_i(t+90) / P_i(t) - 1)`

`w_btc + w_eth + w_alts = B_t`, and the cash residual contributes a defined 0 price return because this question has no cash instrument. That 0 is a definition of the residual, not a fill for a missing price. Funding, fees, borrow, and slippage that are absent from the price tape stay `unavailable` and are omitted from the primary number. A cost cell is reported only where a dated cost observation exists.

`P_i(t)` is the completed daily close on calendar date t. `P_i(t+90)` is the completed daily close on calendar date t+90. The next available bar is a different horizon and is not substituted. A window that has already moved a long way before day 90 is still immature. The same full-horizon rule is what `_labels` states at `btc_impulse_radar_backtest.py:66-67`.

The 7-day and 30-day members of `forward_days` may be printed beside the primary number as predeclared companions. They are not a menu for choosing the favorable horizon after seeing it.

Baseline weights on the same date: `w_btc = B_t`, `w_eth = 0`, `w_alts = 0`, cash residual unchanged. The baseline uses BTC’s own `R_90`.

Paired outcome: `D(t) = R_90_candidate(t) - R_90_baseline(t)`.

There is no qualified point-in-time alt total-return series in the split owner. Search bound on this worktree: `engine/alt_cycle.py:6-7` marks TOTAL2–3 as current-context; `scripts/build_crypto.py:_allocation` emits weights and no return; `engine/radar_plus.py:90` `_alt_index` is a ticker dict of published signals, not a sleeve price. Until a later accepted decision names a point-in-time alt total-return series, any date with `alt_pct > 0` has candidate `R_90 = unavailable`. SOL is not a substitute. A zero alt return is not a substitute. Those dates remain in the unconditional denominator.

`B_t = 0` has no sleeve to rotate. The date stays in the unconditional denominator and out of the eligible set. It is not booked as a 0% paired success.

## 5. Fit and test boundaries

No coefficient is estimated. The fit window is empty. `info_cutoff` on the ledger row is `2026-10-12`.

| Region | Dates | Role |
| --- | --- | --- |
| Exploratory | `as_of <= 2026-10-12`, including every R1–R9 window | Description only |
| Confirmatory clock | `as_of >= 2026-10-13` | Eligible only after the gates in §7 |
| Confirmatory outcome | close on `as_of + 90` calendar days has matured | Required before a paired number exists |

Stored `btc.decision/v1` rows are the confirmatory population. A code-vintage replay that rebuilds exposure from today’s `engine.btc_decision` on older prefixes is a separate diagnostic. It is labeled diagnostic, it inherits the exploratory rule when its dates are on or before 2026-10-12, and it cannot replace a missing stored decision. `signals.alloc_optimal` is not a fallback (`DEC-CRYPTO-H5`, and `scripts/build_crypto.py:249-250`).

P0A’s accepted decision surface starts at merged PR #6294 (`agentos/workstreams/WS-CRYPTO-INTELLIGENCE.md:21-28`). Stored integrity-valid rows before that boundary are not assumed to exist. If they are absent, the confirmatory count is whatever the stored file actually contains after 2026-10-12. The study waits. It does not backfill.

## 6. Maturity, purge, embargo

A date is outcome-mature only when `P(t)` and `P(t+90)` exist for every sleeve with nonzero weight, each finite and `> 0`. Otherwise the outcome is `unavailable`.

Feature maturity is the completed daily bar. An intrabar reading is outside this question.

Embargo length is the label horizon. An exploratory or diagnostic row at date u may inform a description of date t only when `u + 90 calendar days` is strictly before t, and the outcome of u is mature. In row units that is the number of index rows spanning those 90 calendar days. `purged_folds(..., embargo=that row count)` is the helper (`engine/validation.py:333-347`). Passing the integer 90 on a business-day index is a different gap and is a protocol breach.

`cpcv_paths` is not used to choose a grid, a threshold, or a horizon. There is nothing to select. A combinatorial search would be a new trial family and is outside this draft.

The open 90-day window also blocks a new episode (§7). That gap is the episode rule. The feature embargo above is the leakage rule. Both apply.

## 7. Denominators and honest-N

Two denominators are reported for every rate.

**Unconditional clock.** Every calendar date in the confirmatory window that has a completed BTC close. This includes unavailable decisions, as-of mismatches, stale ETH, positive alt weight, zero budgets, immature outcomes, and repeated days inside an open episode.

**Eligible episodes.** A clock date enters the eligible set only when all of these hold:

1. Stored decision accepted by the `_allocation` canonical rule, `as_of` equal to the clock date.
2. `B_t > 0`.
3. Class-split inputs pass the same fail-closed reasons as `_allocation` (`CLASS_SPLIT_INPUT_UNAVAILABLE` and `CLASS_SPLIT_UNAVAILABLE` stay ineligible).
4. ETH close age ≤ 1 daily bar when `eth_pct > 0`.
5. `alt_pct == 0`, or a named point-in-time alt price exists under §4.
6. Prefix-stable regime and ETH/BTC transforms at t.
7. Outcome mature for every nonzero sleeve on both the candidate and the baseline.
8. Episode rule below.

Episode rule. Sort eligible clock dates. Episode 1 is the first. The next episode is the next eligible clock date whose `as_of` is at least 90 calendar days after the previous episode’s `as_of`. Clock rows inside an open episode are repeats. They stay in `N_clock` and stay out of `N_episodes`. Weights and `B_t` are frozen at the episode start. A later decision inside the window does not open a new crisis, a new asset sample, or a rewritten target.

Honest-N is `N_episodes`. `N_clock` is a coverage count. The number of assets inside one sleeve path is not a sample size. One selloff that prints on many days is one episode under the gap rule. Leave-one-episode-out is a fragility list, not a new selected result.

Rates that quote the eligible denominator also quote the unconditional denominator beside them. R9’s own memo records why: catalogue recall `20/78` and supported recall `20/37` answer different questions (`research/CRYPTO_SCIENCE_R9_PREBREAK_RESULTS_2026-09-29.md` §6 on `fd8095012e91`). Publishing only the eligible rate is a protocol breach.

Minimum for a confirmatory sentence: `N_episodes >= 8` matured episodes after 2026-10-12. Below that the status is `insufficient-n`. At a 90-day gap, eight episodes are about two years of forward decisions. That wait is the sample. The historical catalogues are not a substitute.

## 8. Control and metrics

The candidate and the baseline share one metric implementation, one episode id list, one price tape, and one cost treatment. A date that is `unavailable` for the candidate is `unavailable` for the baseline in the paired column. The baseline is not scored alone and then compared.

Reported, in this order:

1. `N_clock_unconditional`, `N_clock_eligible`, `N_episodes`.
2. The list of episode-level `D(t)`, then the mean of that list.
3. Leave-one-episode-out means of `D` (the eight-or-more means obtained by dropping one episode).
4. Daily-path `block_bootstrap_ci` on the candidate’s stitched non-overlapping daily simple returns and, separately, on the baseline’s stitched returns, same episode dates, `block=21`, `B=5000`, `seed=7`. Stitching concatenates the matured daily marks inside each episode and does not double-count the overlap that the episode rule removed. When the helper returns `{}`, the interval is `unavailable`.
5. Share of unconditional dates whose split differs from 100% BTC inside `B_t`, with both denominators.
6. A Sharpe of either path is printed only when `N_episodes >= 3`, and then only through `deflated_sharpe` with `ledger` family `crypto_class_rotation_t12` and `t_eff=N_episodes`. `t_eff` replaces raw `T` only when it is an int ≥ 3 (`engine/validation.py:294-297`). Below that the helper keeps raw `T`, so a short episode count must not be passed in and then described as an episode haircut. The `T < 3` early `None` (`:290`) refers to the return-series length argument. A daily path usually clears that bar while `N_episodes` is still 1. That daily length is not honest-N. When `N_episodes < 3` the Sharpe section is `unavailable` and `deflated_sharpe` is not called.

`D` is the primary paired metric. Sharpe is secondary and haircut by the ledger. The vector family’s `n_trials` is not this N.

## 9. Trial budget

Family: `crypto_class_rotation_t12`.

Declared floor: **24**. Basis: `estimated`. This floor counts judgment choices already published in the incumbent split. It is not a license to run 24 new configurations. The confirmatory study runs one candidate and one baseline.

| Count | Already-published choice | Where |
| ---: | --- | --- |
| 2 | ETH/BTC level lines 0.05 and 0.07 | `config.yml:6109-6110` |
| 3 | Windows 350, 56, 1095 | `config.yml:6111-6113` |
| 2 | Score cuts 25 and 75 | `config.yml:6114-6115` |
| 3 | Score weights 0.60, 0.25, 0.15 | `alt_cycle.py:47-51` |
| 1 | Slope clip inside the score | `alt_cycle.py:49` |
| 1 | Regime cut pair ±1.5 | `cycles.py:958` |
| 9 | `ALLOC_GRID` cells | `alt_cycle.py:63-67` |
| 1 | Dominance-omission branch | `alt_cycle.py:50-53` |
| 2 | Candidate renormalization and BTC-only baseline | `build_crypto.py:316-318` and §4 |

Sum = 24. Overestimate is the direction `log_declared_budget` already encodes (`engine/trial_ledger.py:204-211`).

When a later harness runs, it registers before reading outcomes:

`register_trials("crypto_class_rotation_t12", budget=24, basis="estimated", reason="T12 class-rotation floor itemized in CRYPTO_T12_EVALUATION_CONTRACT_2026-10-12.md §9")`

or `TrialLedger.log_declared_budget(24, family="crypto_class_rotation_t12", reason=...)` on the canonical ledger. Registration is idempotent. Any later `log_grid` / `log_trial` raises `effective_n` and never lowers it. Correlation credit stays off.

This lane does not write `data/trial_ledger.jsonl`. The sparse checkout omits `data/`, and a doc freeze is not a calibrator run.

A harness that calls `deflated_sharpe` passes `ledger=` and `family=`. A literal `n_trials=` is a void result under §10.

## 10. Falsifier

The research sentence is withheld, and the status is the first matching row, when any of these is true.

| Id | Condition | Status |
| --- | --- | --- |
| F1 | `N_episodes < 8` | `insufficient-n` |
| F2 | Candidate episode ids differ from baseline episode ids | `unavailable` (coverage mismatch) |
| F3 | Mean `D <= 0`, or the leave-one-episode-out means of `D` change sign | no incremental 90-day path under this protocol |
| F4 | `block_bootstrap_ci` returns intervals and the candidate Sharpe 2.5 percentile is not above the baseline Sharpe 97.5 percentile | no Sharpe separation; an empty `{}` is `unavailable`, which does not count as a pass |
| F5 | Alt return imputed, dominance backfilled, immature tail coded as a non-event, missing price coded as 0, or `w_btc+w_eth+w_alts != B_t` | void |
| F6 | A confirmatory episode has `as_of <= 2026-10-12` or sits in an R1–R9 evaluation window used as the test sample | void |
| F7 | Family `effective_n < 24`, or `deflated_sharpe` received a literal `n_trials` | void |
| F8 | The reviewer is the author of the confirmatory run or of the harness that produced the numbers | not accepted |

Clearing F1–F8 authorizes one research sentence: on this forward episode set, the frozen split’s 90-day price path differed from BTC-only inside the same DecisionState budget, by the reported `D` list. It does not change `btc.decision/v1`, does not resize H5, and does not promote the grid. Display of the overlay does not wait on that sentence.

## 11. R1–R9 history is exploratory

The R1–R9 memos are on R2 `fd8095012e91` under `research/CRYPTO_SCIENCE_R*.md`. They are not in `origin/main` (`git cat-file -e origin/main:research/CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md` fails). They are context for this protocol. They are not the confirmatory sample, and their negative results stay unpromoted.

| Round | Question | Verdict recorded in the R2 memo |
| --- | --- | --- |
| R1 | Are incumbent features prefix-invariant on the declared 366 dates, and are impulse labels mature? | `bottom_pressure` differs on 3/366 dates; immature tails become `False` in the exploratory label check. No strategy accepted. |
| R2 | Do the timing repairs hold on a paired replay, and do the three impulse legs clear the current gate? | Prefix mismatches 0/4393 after the repair; immature labels stay unknown; none of the three legs clears the gate. Correctness repair, not a new edge. |
| R3 | On source-observed cohorts, what remains after repeated trigger rows are collapsed? | 14 bounce rows become 8 onset episodes, 1 meets +5% at zero delay; the DVOL count falls as action is delayed. Not a rehabilitation. |
| R4 | Does a breakdown-plus-shock 24h cash overlay, or a washout/reclaim sequence, beat the incumbent on frozen barriers? | Neither rule promoted. The cash overlay lacks positive net marginal value. The reclaim sequence loses to immediate entry on the matched 14-day windows. |
| R5 | Does unsigned spot volume add to the observable price response? | No promotion. Volume after a six-hour breakdown filters 7 of 171 exits and adds no downside-first events. Recovery-plus-volume is a weak, period-dependent lead. |
| R6 | Does a small price/trend/volatility probability model improve proper scores and the cash decision? | Brier and log loss improve vs an expanding rate, AUC around 0.70, but the Brier-gain interval crosses 0, probabilities overstate frequency, and the cash policy still loses to the incumbent. |
| R7 | Does intercept calibration on prior out-of-training forecasts, plus utility `U = R - max(L - 0.05, 0)`, deliver dependable protection? | No calibrated-probability or protective-policy promotion. The primary calibrated price policy still loses mean return and declared utility versus the incumbent. |
| R8 | Does acting at the first completed breakdown, or predicting action value directly, beat the six-hour-later decision on the same parents? | Earlier selection is modestly better on average; the paired interval includes no improvement. Reused 2024+ has negative return and utility. |
| R9 | On a clock that includes quiet hours, does a fixed ≥10% warning give positive-lead advance notice at an acceptable non-event burden? | Full-history ranking vs a rate baseline is present. The fixed operating point has a heavy non-event burden, weak recent scores, recall 20/78 unconditional and 20/37 supported, and negative protection economics. No live-warning promotion. |

Any statistic computed on those windows for the class split is exploratory under the same heading. It can be shown with both denominators. It cannot clear §10.

## 12. Independent review

The reviewer is a different person from the author of the confirmatory harness and from the author of the run that emitted the numbers. The author of this draft may not review the confirmatory readout of this draft.

The review checks, against the commit that ran the study:

- Metric code path identical for candidate and baseline, episode ids identical.
- Both denominators present, `N_episodes` distinct from `N_clock`.
- Prefix check, ETH age mask, dominance publication time, alt-return source.
- Embargo in calendar days mapped to index rows.
- Ledger family `crypto_class_rotation_t12` with `effective_n >= 24`, correlation credit off, canonical path `data/trial_ledger.jsonl`.
- Freeze pins in §3 unchanged, or the drift logged as a new trial and excluded from this sentence.
- F1–F8 applied in order.
- User-facing wording follows the rule in the header of this file.
- Missing inputs rendered as `unavailable`.

The review is a separate commit by the reviewer. This draft does not name that person and does not pretend the review has happened.

## 13. What this lane did not execute

No backtest was run. `btc_impulse_radar_backtest.validate()` without an injected frame calls `store.read("vector", "signals")` (`engine/btc_impulse_radar_backtest.py:126-127`), which is under the omitted `data/` tree. No fixture file was passed in. `calibrate_vector.py` was not run. The canonical trial ledger was not written. No network call to a market-data provider was made.

The next implementation step, when commissioned, is a harness that consumes this protocol and the existing `TrialLedger` / `validation` helpers. It is not a new platform.

## 14. Contract tests

`tests/test_crypto_t12_contract_invariants.py` pins this draft against the incumbent functions. It changes no rule in §1–§13.

| Test | Pins |
| --- | --- |
| `test_class_split_renormalizes_onto_budget_and_drops_grid_cash` | §3.6 `_allocation` on `ALLOC_GRID` × budgets 0..100: an emitted split sums to `B`, no negative leg, grid cash column dropped |
| `test_impulse_constants_match_t12_section_2` | §2 `HOLDOUT_START`, `LABEL_H`, `LABEL_THR`, `MIN_HOLDOUT_N`, act-leg floors |
| `test_t12_declared_budget_is_counted_and_effective_n_never_falls_below_it` | §9 family `crypto_class_rotation_t12`, floor 24, temp ledger |
| `test_honest_n_is_distinct_nonoverlapping_90_calendar_day_episodes` | §7 episode gap; spec of record, no engine owner yet |
| `test_ethbtc_forward_fill_has_no_age_cap` | §3 current `ethbtc_signal` forward-fill |
| `test_eth_one_bar_age_mask_is_not_engine_behavior` | §3 one-bar age mask, xfail: harness protocol, not engine behavior |
