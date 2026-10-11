# Q11 — Persistent off-exchange activity regimes with explicit detection delay: PRE-REGISTRATION

Status: frozen before any evaluation outcome is computed. The sha256 of this file and a `date -u`
timestamp are written to `FREEZE.log`. `evaluate.py` refuses to run unless the current sha256
of this file equals the FREEZE.log hash. Any later change goes only in `PREREG_AMENDMENT.md`.

Pre-freeze work completed (none of it computes a challenger output or a comparison metric):

- the incumbent baseline reproduction and eligibility census (`baseline_repro.py`, RUNS.log line 1);
- hermetic synthetic unit tests of the reference module.

## 1. Question

The incumbent off-exchange activity state is the consecutive-session streak above the trailing
median, `engine.darkpool_signals.streak_above_norm`. `engine/darkpool_context.py` reads `streak >= 5` as "N sessions
of above-normal hidden volume". The candidate is an explicit-duration (hidden semi-Markov)
filter, `engine/darkpool_episode_duration.py` (sha256 at freeze, below). It has Student-t
emissions and keeps detection time separate from the retrospective onset.

The question: on held-out sessions, at a matched training false-alarm rate, does the candidate
detect a sustained participation shift materially earlier or more often than the streak, without
more spike-driven false episodes?

## 2. Estimand and unit

- **Unit:** one (name, injection position, injection type) replicate on a held-out test series.
- **Primary estimands (paired, filter − streak):**
  - **P1a** — excess 10-session detection probability on sustained steps:
    `EXD10 = P(new episode detected in [s, s+10) | step at s) − P(new episode detected in [s, s+10) | no injection)`.
    Computed per detector, then differenced.
  - **P1b** — mean censored detection delay on sustained steps: the first new-episode detection
    index in `[s, s+40)` minus `s`, set to 40 if there is none.
  - **P2** — spike excess false-episode probability: the same window rule as P1a, applied to a
    single-session spike instead of a step.
  - **P3** — the untouched (uninjected) held-out episode-start rate per 1000 observed evaluable
    sessions, as the ratio filter / streak.
- **Secondary (descriptive, not decision-bearing):**
  - P1a/P1b split by step magnitude;
  - P4, fragmentation: the number of distinct new-episode detections in `[s, s+L+5)` on steps;
  - the streak trade-off curve for k ∈ {3, 4, 6, 8} (EXD10, delay, untouched rate);
  - the detection-vs-retro-onset gap of the filter, `detected_at − retro_onset_at_detection`.

## 3. Clocks

- **Input clock:** the session calendar is the trading dates of `yahoo/SPY.parquet` inside the FINRA panel
  range: 2023-08-01 → 2026-10-08, 801 sessions, all with a FINRA date (census).
- **Value at session t:** participation = FINRA `total_vol` ÷ Yahoo consolidated `volume`.
  - Exact-date inner join, consolidated volume > 0, no forward fill (the incumbent construction).
  - A missing session is NaN on the calendar.
- **Output clock:** each detector emits at session t using only values at sessions ≤ t.
  - The detection index is the first session at which an episode is knowable.
  - The filter's retrospective onset is a separate field and is never used as a detection time.

## 4. Cohort

The deep-panel names (`finra_short_volume/panel_deep.parquet`) that meet all of:

- Yahoo volume present;
- no share-count basis break, i.e. `engine.darkpool_signals.share_break_index` returns None;
- at least 300 observed train sessions and at least 150 observed test sessions.

Census at freeze: 374 deep names. 327 are eligible; 31 are excluded for a share-basis break, 15 for a short train
window and 1 for a short test window. The panel is the union of the deep panel and the collector panel, with the
collector winning; the overlap is 548 rows with 0 differing `total_vol`. Missing sessions inside an eligible name's span: median 0, max 82, and 121 names have more than 0.

## 5. Source vintages (read-only, `macro-main/data` at vintage cdab6268)

| input | sha256 |
|---|---|
| finra_short_volume/panel.parquet | 63c69080d88baf4bbc039d1906995e37fa7c5078f6370cac46d1a03a7df4f6f4 |
| finra_short_volume/panel_deep.parquet | 12cc30a28547c30d7effd0991c6dab773b419f36b2fc4cc2133069fc444d5d9f |
| yahoo/SPY.parquet (calendar) | 6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152 |
| darkpool/context/latest.json (baseline repro only) | 5326961a11e27e21f28e8dff2626157c3be55a62f69dc449f2ed17beeb4e186d |
| manifest of all 377 per-file sha256 (results/baseline_inputs_sha256.json) | 0553f7e4a264e1c922f60459908fdd00ce28a2d84a8b3830718f3fff2215601b |

Code at freeze:

- engine/darkpool_episode_duration.py `f3a3134d2abd97b38c79956ba87f8d5978111913351fed744fff98f3701d1189`
- engine/darkpool_signals.py (incumbent, unchanged) `4483200a3c09456bb1f26b76850c5f216925d2b0b2e681cc8698608bcb1e95ec`

If the hashes differ, `evaluate.py` records the observed ones and the difference is reported.

## 6. Hypotheses

- **H1 (sensitivity):** filter − streak EXD10 ≥ +0.10 with the 95% CI lower bound > 0, **or** the
  filter − streak mean censored delay ≤ −1.0 session with the 95% CI upper bound < 0. Pooled over both step magnitudes.
- **H2 (spike robustness):** the upper bound of the 95% CI of the filter − streak spike excess false-episode probability is ≤ +0.02.
- **H3 (false-alarm parity):** the untouched held-out start-rate ratio, filter / streak, has a point estimate ≤ 1.20.
- **H0 / falsifier:** if any of H1, H2 or H3 fails, the explicit-duration filter does not earn a
  place over the incumbent streak. The verdict is REJECT and the streak remains the owner.

## 7. Competitors

- **Baseline (incumbent, exact):**
  - On observed sessions only, `above_t = p_t > median(previous ≤ 60 observed p)`, which requires ≥ 5 prior observations.
  - `streak_t = streak_{t−1} + 1` if `above_t`, else 0.
  - Missing sessions are skipped, as in the incumbent's `dropna`.
  - A new episode is detected at the session where the streak first reaches k = 5. The episode ends when the streak returns to 0.
  - `evaluate.py` checks that its incremental streak equals `streak_above_norm(observed p up to t)` at sampled
    sessions for every name. Any mismatch aborts the run.
- **Challenger:** `filter_path(robust_activity_z(p))` with the module defaults:
  - hazards: enter 1/250, Elevated duration 1 + NegBin(r=2), mean 20, cap 120;
  - max_gap 5;
  - `mu_elevated_sd = 1.0`.
  - (nu, scale) are fit by `fit_emission_params` on the pooled TRAIN z of all eligible names.
  - A hysteresis alarm with `tau_off = tau_on / 2` turns `p_elevated` into episodes.
- **Matched alarm calibration (train only):**
  - `tau_on` is the smallest value in {0.30, 0.35, …, 0.95} whose pooled train episode-start rate
    per 1000 observed evaluable sessions is ≤ the streak (k = 5) pooled train rate.
  - If no grid value qualifies, `tau_on = 0.95` and this is reported.
- **Evaluable session:** an observed session with ≥ 60 prior observed values for that name, so both detectors are fully warmed.

## 8. Practical effect bar

- +0.10 in 10-session excess detection probability, or a 1.0-session earlier mean censored detection.
- Spike-false-episode tolerance: +0.02.
- False-alarm parity tolerance: ratio 1.20.

## 9. Trial family

This is one trial: a single challenger configuration against a single baseline (k = 5).

- No per-name tuning and no grid over hazards, durations or emission shape.
- Only (nu, scale) and `tau_on` are chosen, and only on train data.
- The k-curve is descriptive only. It cannot replace the baseline after the fact (DNR:KILL-OUTCOME-AUDITION).

## 10. Outcome windows and injections (semi-synthetic, held-out test only)

- **Train:** sessions dated ≤ 2025-06-30. **Test:** sessions after that date.
- **Injection positions per name:** `s_j = test_start + 20 + shift + 60·j`, with j = 0..4 and
  `shift = int(sha256(ticker)[:8], 16) % 30`.
  - `test_start` is the first calendar index after the train end.
  - A position is kept only if `s_j + 50 ≤` the name's last observed index.
- **Injection types**, each applied to its own copy of the name's series and run from scratch. Only observed values are multiplied; NaN stays NaN; z is recomputed causally:
  - `step125`: p × 1.25 on calendar sessions [s, s+40);
  - `step150`: p × 1.50 on [s, s+40);
  - `spike300`: p × 3.0 at session s only. Excluded if s is missing.
- **Replicate exclusion (attrition reported):** a replicate is excluded when either detector's alarm is on at s − 1 in the uninjected series. Exclusions are counted by type and by detector.
- **The untouched rate (P3)** uses the uninjected series over all evaluable test sessions.

## 11. Chronological split and training-only choices

- The z baseline window (60) and min_hist (20) are fixed constants.
- (nu, scale) are fit on train-session z only.
- `tau_on` is calibrated on train-session episode starts only.
- The step magnitudes and windows above are fixed here.
- Test data is used once.

## 12. Dependence-aware uncertainty

Two-way pigeonhole block bootstrap, B = 2000, numpy `default_rng(1101)`:

- Names are resampled with replacement, and so are 20-session calendar blocks (`block = calendar index of s // 20`).
- Each replicate's weight is name multiplicity × block multiplicity. Statistics are weighted means of
  paired per-replicate differences.
- For P3 the unit is (name, 20-session test calendar block) start counts and evaluable-session counts, and the statistic is the ratio of weighted sums.
- Percentile 95% intervals.
- Honest N is reported: names, blocks, and replicates by type after exclusion.

## 13. Data sufficiency

If the eligible cohort is below 50 names, or any primary metric has fewer than 200 replicates after exclusion, the verdict is
INSUFFICIENT_DATA, naming the short input.

## 14. Stop rule

- One evaluation run produces the verdict.
- A rerun is allowed only for a code fault that stops the run before any metric is written. Every run, including failed ones, is appended to RUNS.log.
- A deterministic re-run after a docstring-only change to the module (the verdict line) is
  allowed. It must reproduce byte-identical result files and is reported as such.
- No holdout search. No change of thresholds, k, magnitudes or windows after seeing results.

## 15. Non-duplication (incumbent refresh and collision check)

- **Collision grep:** `_base/engine`, `_base/scripts` and `_base/tests` were searched for
  episode_duration | run_length | changepoint | BOCPD | semi_markov.
  - Only unrelated run-length counters matched: `engine/manager_lag.py`, `engine/market_os/macro_workspaces/rates_curves.py`,
    `scripts/build_regime_v2_pit.py`, `scripts/research_flow_observatory_methods.py` and their tests.
  - No off-exchange episode, changepoint or duration detector exists.
  - The module name `darkpool_episode_duration.py` is new.
- **Incumbent owners, unchanged:**
  - `engine/darkpool_signals.py`: participation, `streak_above_norm`, share-break handling;
  - `engine/darkpool_context.py`: labels, the `streak >= 5` read;
  - `scripts/build_darkpool_desk.py`: panel union.
  - Q11 imports the incumbent only inside `evaluate.py`, to reproduce the baseline. The module imports nothing from `engine/`.
- **EXCLUSIONS table:**
  - No incumbent row covers off-exchange episode duration.
  - The off-exchange dependency row sets the sequence "Q03 first; Q09 independent; Q10 then Q11". Its rule is that one activity owner integrates
    basis/residual/state changes and that venue analysis never enters frozen PSS-AF1.
  - Narrow relation: Q11 is a state-duration measurement on the incumbent participation series. It
    uses the incumbent split-break exclusion in place of the Q03 basis correction and raw participation in place of
    Q10 residuals. That dependency is a stated limitation.
- **Standing kills/holds respected:**
  - DNR:HOLD-PSS-AF1-FINRA: no short-volume ratio, no ATS split, nothing enters PSS-AF1.
  - DNR:KILL-OUTCOME-AUDITION: pooled parameters, no per-name or k selection on outcomes.
  - DNR:KILL-REGIME-SCORECARD and DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR: a per-name activity state, not a market-regime fusion or monitor.
  - DNR:KILL-FUSED-COMPOSITE and DNR:KILL-POSITIONING-FUSION: no composite.
  - DNR:KILL-LLM-ORIGINATION: no LLM in the loop.
  - DNR:KILL-CAUSAL-DAG-ALPHA: no causal claims.
  - DNR:HOLD-PSS-CD1-CROWDING: not touched.
- **Scientific restrictions:**
  - FINRA facility volume is a venue/reporting category, not intent, accumulation or short interest.
  - The elevated regime is a statistical activity state, never "institutional buying".

## 16. Limitations declared in advance

- Semi-synthetic injections multiply observed participation. Real activity regimes may change dispersion or autocorrelation rather than level.
- No Q10 residualization and no Q03 basis correction. Split-break names are excluded instead.
- Yahoo volume restatements are taken at vintage cdab6268. Revision behaviour is exercised only in unit tests (req2/req3).
- The test window is about 320 sessions, so later injection positions have more attrition.
- No returns or prices are read. This is a detection-quality study, not a predictive one.
