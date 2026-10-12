# Q11 — six acceptance requirements: proof map

Each requirement is pinned by a hermetic test in `tests/test_darkpool_episode_duration.py`. Requirement 2 has a second test, added after the independent audit. The tests use synthetic integer-indexed data, fixed seeds, and no repo files, network or clock. Where an empirical check exists it is cited too.

The focused suite command below exited **0** (8 passed; RUNS.log `focused_pytest` entries):

```
PYTHONPATH=<Q11> PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest <Q11>/tests/test_darkpool_episode_duration.py --rootdir <Q11> --noconftest -p no:cacheprovider -q
```

## Requirement 1. An isolated spike and a sustained shift produce distinguishable uncertainty/duration diagnostics

**Test:** `test_req1_isolated_spike_and_sustained_shift_have_distinguishable_diagnostics`

**Spike (×3 at one session):**
- `surprise` exceeds the 99th percentile of the pre-spike surprise.
- `p_elevated` stays below 0.2.
- No episode opens.

**Sustained ×1.5 shift:**
- `p_elevated` exceeds 0.9 within 10 sessions.
- The posterior expected duration grows (> 5, and increasing).
- P(duration ≥ 5) exceeds 0.8.
- Exactly one episode opens.

**Empirical:**
- Spike excess false-episode probability: filter 0.018, streak 0.037. The filter − streak difference is −0.018 [−0.046, +0.006] (H2 met).
- Fragmentation per step episode: filter 1.17, streak 2.19.

## Requirement 2. Detection is stamped when knowable; retrospective onset is not used as the live event date

**Tests:** `test_req2_detection_is_stamped_when_knowable_and_never_backdated` and `test_req2_new_episode_while_record_open_closes_old_and_stamps_new`

**Prefix invariance:**
- The filter output at t, computed from `x[:t+1]`, equals the full-series output at t (checked at 4 indexes).
- `retro_onset_at_detection ≤ detected_at`.
- `onset_indicator` marks the detection index, never the retro onset.

**Revision scenario:**
- A restated vintage would have alarmed earlier.
- `update_detection_records` stays append-only: earlier records come back unchanged.
- The new record is stamped `detected_at = asof` (211).
- The earlier index a backdating system would claim is kept only as `backfilled_detection_index` (< 211).

**Superseded episode scenario:**
- Two shifts occur, and the first episode ends and the second begins between two runs.
- The as-of run at 320 appends `closed` for episode 1 and then `detected` for episode 2, both stamped 320.
- The new record's backfilled index (215 < index < 320) is kept separately.
- A run at 216, still inside the same episode, appends nothing.

**Empirical:** every metric in `evaluate.py` uses the detection index. The retro onset is reported separately: the median gap from detection is 5 sessions.

## Requirement 3. Missing sessions and revisions cannot create artificial persistence

**Test:** `test_req3_missing_sessions_and_revisions_cannot_create_persistence`

- **Missing values stay missing.** NaN sessions stay NaN in the causal z. Observed z equals the z of the compressed series, so nothing is interpolated.
- **A gap adds no evidence.** A missing session is a prediction-only step, so across a gap the probability only drifts toward its stationary level at the duration hazards. The test checks that an elevated (above-stationary) `p_elevated` is non-increasing across the gap. The decay is slow (mean Elevated duration 20 sessions), so an open episode can span a gap of up to `max_gap` sessions.
- **Long gaps reset.** A gap longer than `max_gap` (5) sets `gap_reset` and closes the open episode.
- **Holes do not count as evidence.** Holes reduce the episode's `n_observed`.
- **Revisions are append-only.** The append-only as-of records (Requirement 2) stop a revision from moving a recorded detection earlier.

**Empirical:**
- Missing sessions stay NaN on the 801-session calendar; there is no forward fill (incumbent construction).
- A spike at a missing session is excluded (2 replicates).

## Requirement 4. Heavy-tailed shocks do not force endless false regime resets in controlled tests

**Test:** `test_req4_heavy_tailed_shocks_do_not_force_regime_resets`

The test runs 3 seeds. Each series has a sustained +1.2 regime, 4 in-regime −9 shocks and 5 out-of-regime +9 shocks, and the result is compared against the same series without shocks.

| metric | Student-t (nu = 4) | Gaussian control (nu = 1e6) |
|---|---|---|
| extra in-regime episodes caused by the shocks | ≤ 1 | ≥ 5 |
| spurious openings within 2 sessions of an out-of-regime shock | 0 | ≥ 5 |

**Empirical:** (nu, scale) were fit on train z only, giving nu = 3.61.

## Requirement 5. Hazard/model choices are not tuned to the evaluation return outcomes

**Test:** `test_req5_model_choices_are_not_tuned_to_return_outcomes`

- **No return or price inputs.** No public function parameter or dataclass field names a return, price, close, PnL, outcome or forward input, and `CONTRACT["uses_returns_or_prices"]` is False.
- **Fixed constants.** The hazards (1/250, mean 20, NegBin r = 2) are fixed.
- **Deterministic fit.** `fit_emission_params` is a deterministic, bounded function of the training values.

**Empirical:**
- `evaluate.py` reads no return or price file.
- tau_on was calibrated on the train false-alarm rate only.
- PREREG §9 was frozen before any outcome.

## Requirement 6. Existing events, labels, PSS-AF1 policy and alert delivery owners are unchanged

**Test:** `test_req6_existing_events_labels_policy_and_alert_owners_unchanged`

- **Contract.** `CONTRACT` has empty `modifies_owners` and empty `consumers`.
- **No owner imports.** The module imports no `engine.*`, darkpool or alert module.
- **Records stay in memory.** Detection records are plain in-memory dicts with a closed key set. Nothing is persisted, delivered or given an identity.
- **Repository scope.** The change is new files only. No existing repo file is edited. `engine/darkpool_signals.py`, `engine/darkpool_context.py` and PSS-AF1 are untouched (DNR:HOLD-PSS-AF1-FINRA).

## No silent activation

**Test:** `test_no_silent_activation_module_contract`

- Re-importing the module in an empty temp cwd creates no files.
- `RESEARCH_ONLY is True`.
- The docstring starts with "RESEARCH REFERENCE — NOT WIRED".
- `activation_status()` reports wired / alerts / writes / persists all False.

The CI job is staged with `if: ${{ false }}` (`_handoff/ci_job.yml`).
