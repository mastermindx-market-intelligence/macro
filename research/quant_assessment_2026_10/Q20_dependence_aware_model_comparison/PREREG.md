# Q20 — Dependence-aware challenger comparison on the existing trial budget — PRE-REGISTRATION

Status: written and frozen BEFORE any holdout differential, SPA statistic, simulation
outcome or baseline-reproduction number of this study was computed. The only outcome
numbers seen before freeze are the incumbent's own PUBLISHED full-sample figures in
`data/vector/calibration.json` (listed under "Baseline" below). Changes after freeze go
only to `PREREG_AMENDMENT.md` (reason + sha256, written before reading new outcomes).

Author: Claude (served model reported by the environment: Opus 5.5, model ID
`claude-opus-5-5`), workflow brief Q20, AUTHOR role. Research reference only — nothing is
wired, registered, scheduled, promoted or gated by this study.

## 1. Question

Does honest dependence- and selection-aware accounting (Hansen 2005 SPA with a common-index
stationary block bootstrap) preserve the incumbent's claim that the best Vector BTC
allocation variant is a genuine improvement over buy-and-hold, once (a) the comparison is
risk-matched, (b) every generation-time trial in the admitted family is retained, (c) the
original declared trial budget is kept, and (d) the reuse status of the outcome window is
disclosed?

And, as the method question the brief commissions: does the reference evaluator hold its
nominal size under correlated null candidates, detect a true-signal control, show that
naive best-candidate testing oversizes, and keep the trial budget monotone?

## 2. Admitted comparison family and loss/export contract (frozen)

- Family: trial-ledger family `vector`, source `alloc_variant` (written by
  `scripts/calibrate_vector.py` `_led.log_grid([{"variant": k} ...], family="vector",
  source="alloc_variant")`).
- Generation-time trial identities (ledger rows, ts 2026-07-02T03:43:12Z, `info_cutoff` null):

  | variant | config | config_hash |
  |---|---|---|
  | conservative | `{"variant":"conservative"}` | 0692c70992c525bb |
  | moderate | `{"variant":"moderate"}` | 8018a48758dddb05 |
  | aggressive | `{"variant":"aggressive"}` | 3fe71a26c76dfed9 |
  | optimal | `{"variant":"optimal"}` | 911496757c3b4247 |

  evaluate.py recomputes each hash with the ledger's own rule
  `sha1(family + "\x00" + json.dumps(config, sort_keys=True, default=str,
  separators=(",",":")))[:16]` and REFUSES to run if any candidate fails to map or if any
  itemized family trial lacks a candidate panel (no losing trial may disappear).
- Declared family budget rows: n=68 (2026-07-02T03:30:48Z) and n=71
  (2026-07-18T17:09:33Z). Budget used = max over declared rows and literal distinct configs
  = 71 (evaluate.py derives it from the ledger at run time; it never hard-codes 71).
- Export (precomputed candidate outputs): `data/vector/signals.parquet` columns
  `close`, `alloc_conservative`, `alloc_moderate`, `alloc_aggressive`, `alloc_optimal`.
  The `*_raw` allocation columns are NOT itemized in the ledger, are not candidates, and are
  excluded with that reason recorded in the result file.
- Loss contract: per-day net strategy return
  `r_k,t = alloc_k,t-1 * r_t - c * |alloc_k,t-1 - alloc_k,t-2|`, with `r_t = close_t/close_t-1 - 1`,
  `c = cost_bps/1e4` (one-way cost charged on position change, matching the incumbent
  docstring), position lag fixed at 1 day (decision at close t-1 applied to return t).
  The loss differential vs the benchmark is `d_k,t = r_k,t - beta_k * r_t` (positive = the
  candidate beats the benchmark).
- Unit: one calendar day (BTC trades 7 days a week; annualisation factor 365, as in the
  incumbent's TRADING_YEAR).

## 3. Clocks, cohort and source vintages

- Input clock: daily close timestamps of `signals.parquet` (DatetimeIndex). Output clock:
  the same day t; the allocation decision is formed at t-1 close and earns r_t.
- Cohort: the single BTC series; all days from `config.yml vector.calibration.start_date`
  (2015-01-01) to the last row of the export. No days dropped except the warm-up rows needed
  for lags.
- Source vintages (licensed retained data, macro-main data vintage cdab6268, READ-ONLY):

  | input | sha256 |
  |---|---|
  | `data/vector/signals.parquet` | b0df9712370c4af4f5cf779512c862c0ba6e453639d2ec51b0e54a411ada1996 |
  | `data/vector/calibration.json` | 1fc7b6e664d55bf6c75d39d42ae430d02f394b748af4bcc5078e6b680ba290ce |
  | `data/trial_ledger.jsonl` | 58b7feba20efafca5125faaf21330343a07141496379b4b9aea0fa8cc112380d |
  | `config.yml` | b8963682e5f2fe209cee1a604f19e51bbce232992d75c0b26c60a615600a310f |
  | `scripts/calibrate_vector.py` (read for contract, `_base`) | a7b10d2b955c33d749da91d28c9e2828e6bed57799253f87485994d33298c5c4 |
  | `engine/trial_ledger.py` (read for hash rule, `_base`) | 7b99683c9aee822df138d35b8294318e3316c3b6a8b5a80934614141a15413f7 |
  | `engine/calibration_hub.py` (read for constants, `_base`) | a5066de626af6d95fe6d437d4fb2b6f0f541fd60f9c52646aef3c93d24069224 |

  evaluate.py re-hashes the four data/config inputs and refuses to run on a mismatch.
- Vintage caveat (disclosed, not curable): `signals.parquet` is recomputed nightly over full
  history by the CURRENT code, so it is a current-vintage reconstruction of positions, not a
  point-in-time decision log. Post-generation days were produced by code that may differ from
  the code that existed at trial generation.

## 4. Chronological split and outcome windows

- Training window: [start_date, split_date) = [2015-01-01, 2021-01-01) from `config.yml`.
  Used ONLY to estimate the risk-matching coefficient `beta_k = sd(r_k) / sd(r)` per
  candidate (the single preprocessing parameter). No other parameter is estimated anywhere.
- Evaluation window (primary): [split_date, last row]. This window is the incumbent
  calibration's post-split half and was available when the trials were generated
  (2026-07-02), so it is REUSED. It is reported as non-confirmatory and never described as a
  fresh confirmation.
- Post-generation window (support only): days strictly after the latest generation
  timestamp of the itemized trials (read from the ledger). It holds about 97 days, about 4
  non-overlapping 21-day blocks, which is below the 10-block minimum (the same minimum as
  `calibration_hub._MIN_INDEPENDENT_BLOCKS`). It is reported descriptively (N, mean d,
  blocks) and is NOT tested. It becomes testable only when a future owner run has at least
  10 post-generation blocks — that is the named missing input for fresh confirmation.
- No shuffled cross-validation is used for any inference. CSCV/PBO is computed only as a
  supplementary selection-instability diagnostic on the evaluation window and cannot
  change any verdict.
- The holdout is evaluated exactly once with the frozen specification. There is no
  repeated holdout search: block lengths other than the primary are fixed in advance as
  sensitivity rows, not alternatives to choose from.

## 5. Estimand, hypotheses, competitors, effect bar

- Estimand: `mu_k = E[d_k,t]` over the evaluation window, for each candidate k, with the
  family-wise null `H0: max_k mu_k <= 0` (no allocation variant beats risk-matched
  buy-and-hold).
- H1: at least one variant has `mu_k > 0`.
- Baseline competitor (benchmark): buy-and-hold BTC scaled by `beta_k` (training-window
  volatility match), i.e. risk-matched HODL. Secondary benchmark (disclosure only):
  unscaled HODL and cash (zero).
- Practical effect bar: the best candidate's annualised mean differential
  `365 * mean(d_k)` must be at least 0.02 (2 percentage points per year).
- Trial family for multiplicity: the 4 itemized candidates are tested jointly by SPA. The
  original declared budget (71) is reported alongside through a budget-Bonferroni bound
  `min(1, budget * p_naive_best)`; the 67 budget trials without retained loss panels are
  counted as `UNAVAILABLE_LOSS_PANEL` attrition (they are not dropped from the count).

## 6. Dependence-aware uncertainty method

- Hansen (2005) SPA test, studentised, consistent p-value (`p_c`) primary; lower (`p_l`)
  and upper/Reality-Check-like (`p_u`) p-values reported.
  `T = max(0, max_k sqrt(n) dbar_k / omega_k)`; bootstrap
  `T* = max(0, max_k sqrt(n) (dbar*_k - g(dbar_k)) / omega_k)`, with recentring
  `g_l(x)=max(0,x)`, `g_c(x)=x * 1{sqrt(n) x / omega_k >= -sqrt(2 log log n)}`, `g_u(x)=x`.
  `omega_k^2` = bootstrap variance of `sqrt(n) dbar*_k`.
- Resampling: Politis–Romano stationary bootstrap with ONE common index matrix shared by
  all candidates (preserves cross-model and serial dependence and the common calendar).
  Primary mean block length 21 days (the incumbent's bootstrap block), B = 5000, seed 7.
- Block-length sensitivity (pre-specified, not a search): mean block lengths
  {7, 14, 21, 42, 63}, same B and seed.
- Honest N: non-overlapping 21-day blocks in the evaluation window; also the Newey–West
  (Bartlett, lag floor(4 (n/100)^(2/9))) effective sample size `T_eff = n * var / lrvar` of the
  best candidate's differential.
- Support/attrition: rows in the export, rows after the start date, rows lost to lags, NaN
  rows (expected 0), per-window N and blocks, and candidates retained/excluded with
  reasons.
- Secondary disclosures (non-decisional): naive best-candidate one-sided p (ignores
  selection; a HAC t on the best candidate); budget-Bonferroni bound; SPA vs cash
  (`d = r_k`); log-growth differential vs unscaled HODL; CSCV PBO with S = 16
  chronological partitions on the evaluation window, using per-day net returns of the 4
  candidates and Sharpe as the in-sample ranking metric.

## 7. Baseline reproduction (inspected incumbent)

Published incumbent baseline (`calibration.json`, `allocation`, net of cost_bps 10,
n_obs 4287): conservative sharpe 1.38 / cagr 50.4; moderate 1.44 / 62.9; aggressive 1.32 /
62.2; optimal 1.42 / 61.5; hodl sharpe 1.05 / cagr 61.0. `multiple_testing`: DSR 0.9601 with
n_trials 71, selected_variant optimal, verdict "SURVIVES multiple-testing (DSR>=0.95)".
`allocation_bootstrap` sharpe CI [0.79, 1.41, 2.01] (block 21, B 5000).

evaluate.py independently recomputes full-sample (from start_date) net Sharpe
(`mean/sd * sqrt(365)`) and CAGR per variant plus HODL with the frozen loss contract and
logs the absolute differences. Tolerance for "reproduced": |dSharpe| <= 0.05 and
|dCAGR| <= 3 pp for every variant (the export now has more rows than n_obs 4287, and the
incumbent's `backtest_core` was not opened — it lives in the refused validation core — so
exact equality is not expected). A lag-0 variant of the reproduction is also logged as a
disclosed diagnostic only; the primary lag stays 1 whatever the reproduction shows.
A reproduction miss is reported, does not stop the study, and is listed as a limitation.

## 8. Method-control simulation (must pass for KEEP)

Synthetic panels, n = 2100 (close to the evaluation-window length), K = 20 candidates,
each candidate an AR(1) with phi = 0.3 and unit marginal variance, cross-candidate
innovation equicorrelation rho, B = 499 bootstrap draws, mean block 21, 1000 Monte Carlo
replications per scenario, master seed 20 (scenario seeds derived deterministically).

| scenario | rho | means | gate |
|---|---|---|---|
| N1 least-favourable null | 0.9 | all 0 | SPA_c rejection rate at 0.05 <= 0.075 |
| N2 least-favourable null | 0.5 | all 0 | SPA_c rejection rate <= 0.075; naive best-candidate rejection rate >= 0.10 |
| N3 null with poor alternatives | 0.9 | 5 at 0, 15 at -0.1 | SPA_c rejection rate <= 0.075 (reported p_u rate shows RC conservativeness) |
| P1 true-signal control | 0.9 | one at +0.1 (marginal-sd units), 19 at 0 | SPA_c rejection rate >= 0.80 |

Budget monotonicity control (deterministic): adding m = 1..50 correlated null candidates
(rho in {0.5, 0.9, 0.99}) to the declared family must never return a trial budget below the
original (71 in the empirical family; the declared figure in synthetic fixtures).

## 9. Decision rules (frozen)

Empirical claim test (vector family, evaluation window, reported as SURVIVES or VANISHES):
the claim SURVIVES iff ALL hold —
1. SPA `p_c <= 0.05` at the primary block length 21;
2. SPA `p_c <= 0.10` at every sensitivity block length {7, 14, 42, 63};
3. the best candidate's annualised mean differential >= 0.02.
Otherwise the claim VANISHES. Falsifier / stop rule (from the brief): if the claimed
improvement vanishes under honest dependence/selection accounting, keep the incumbent
algorithm unchanged and file the negative comparison; do not choose a friendlier test,
benchmark, block length, window or lag afterward. Even a SURVIVES result is labelled
"REUSED window — not fresh confirmation" and grants no promotion or gate change.

Study verdict (deliverable verdict for the reference evaluator):
- KEEP — every method-control gate in §8 passes AND the empirical comparison ran on the
  eligible admitted family (whatever its SURVIVES/VANISHES result). Keep means: retain the
  Q20 module as a research-only, unwired diagnostic for the existing statistics owner.
- REJECT — any §8 gate fails (the evaluator is not trustworthy as specified).
- INSUFFICIENT_DATA — the admitted family's export or ledger identities are missing or fail
  the integrity checks at run time (the exact missing input is named).

## 10. Non-duplication

Collision check (grep of `_base` at staging base d252f919): `engine/challenger_spa_comparison.py`
and `tests/test_challenger_spa_comparison.py` are absent. Incumbents and their narrow relation:

- `engine/trial_ledger.py` — owns generation-time trial accounting, `effective_n` and the
  DSR count. Q20 does NOT write to, import or rebuild the ledger; it only re-derives the
  ledger's config-hash rule (a pure function) to check candidate identity, and reads the
  ledger JSONL read-only. No new ledger is created.
- `engine/calibration_hub.py` — display-only calibration/promotion reporting owner
  (`_MIN_INDEPENDENT_BLOCKS = 10`, Holm alpha 0.05). Q20 reuses that block minimum as a
  documented constant and does not report into, gate or alter the hub.
- `engine/validation.py` (`spa_test`, `reality_check`, `backtest_core`, referenced by
  `engine/seasonality/foundation.py` and `engine/seasonality/program_watch.py`) — the
  validation core. Its read was safety-refused for this assessment; it is NOT opened,
  imported, replayed or replaced. Q20's SPA is an independent research reference that
  lives only in the research tree and claims no production role; the core remains the
  owner of production validation.
- `scripts/calibrate_vector.py` — owns the Vector DSR, the Sharpe bootstrap and the
  `vector` ledger rows. Q20 adds no second DSR (brief L20) and does not alter the family.
- Purged validation / a general Eval OS — not built (brief exclusion).

Standing kills/holds respected: DNR:KILL-OUTCOME-AUDITION (no outcome-driven re-selection;
one frozen pass), DNR:KILL-FUSED-COMPOSITE and DNR:KILL-REGIME-SCORECARD (no composite or
scorecard is formed), DNR:KILL-LLM-ORIGINATION (no LLM originates any signal or score).
No FINRA, positioning, causal-DAG or crowding input is used.

## 11. Outputs

`results/` small JSON files: `baseline_repro.json`, `simulation_controls.json`,
`empirical_comparison.json`; every run appended to `RUNS.log` with command, exit code,
input and output sha256s. evaluate.py refuses to run if sha256(PREREG.md) differs from
the hash recorded in FREEZE.log.
