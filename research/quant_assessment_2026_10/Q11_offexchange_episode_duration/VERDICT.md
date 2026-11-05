# Q11 — VERDICT: KEEP (research reference only, not wired)

**Decision rule (PREREG.md §6, frozen sha256 `10846dad…cd50`, FREEZE.log 2026-10-09T09:54:00Z):**
KEEP needs all of H1, H2 and H3; otherwise REJECT. All three were met in the single evaluation run
(RUNS.log, `evaluate.py`, 2026-10-09T09:58:41Z, exit 0).

KEEP means the explicit-duration filter (`engine/darkpool_episode_duration.py`) is retained as a
research reference that measured better than the incumbent streak on this frozen design. It does
**not** wire, register, promote or gate anything. The incumbent `streak_above_norm` stays the owner of
the served off-exchange activity state. Any promotion would be a separate, gated decision that
runs the adjudication coverage gate first.

## Primary results (held-out test sessions after 2025-06-30, semi-synthetic injections)

The bootstrap is two-way (names × 20-session calendar blocks), B = 2000, seed 1101, with 95% percentile intervals.

| metric (filter − streak) | estimate | 95% CI | bar | met |
|---|---|---|---|---|
| P1a excess 10-session detection, steps (n = 2278) | **+0.154** | [+0.105, +0.199] | ≥ +0.10 and CI lo > 0 | yes |
| P1b mean censored delay, steps (sessions) | −0.40 | [−0.80, −0.05] | ≤ −1.0 and CI hi < 0 | no (H1 needs only one arm) |
| P2 spike excess false-episode probability (n = 1137) | −0.018 | [−0.046, +0.006] | CI hi ≤ +0.02 | yes |
| P3 untouched held-out start-rate ratio (filter / streak) | **0.47** | [0.43, 0.51] | point ≤ 1.20 | yes |

Untouched start rates per 1000 evaluable sessions: filter 12.2, streak 26.1.

H1 passed via the EXD10 arm (P1a); H2 and H3 also passed. → **KEEP.**

## What the gain actually is (read this before citing the number)

The two detectors' raw 10-session detection on steps is about equal:

| step | filter | streak |
|---|---|---|
| ×1.25 | 0.891 | 0.888 |
| ×1.50 | 0.982 | 0.975 |

The +0.154 excess-detection margin comes from the **background**. A fresh streak-5 start occurs in the
same 10-session window of the uninjected series 26.3% of the time, against 11.3% for the filter. So the
candidate's measured advantage is **specificity at equal sensitivity**: about half the false-start rate, with:

- equal or slightly earlier detection: delay −0.71 sessions [−1.05, −0.45] on ×1.50 steps, −0.09 [−0.68, +0.48] on ×1.25 steps;
- half the fragmentation: 1.17 against 2.19 new detections per step episode (P4);
- half the spike-induced false starts: 0.018 against 0.037.

**A different k does not reproduce this.** The streak k-curve, which is descriptive only and cannot replace the baseline (DNR:KILL-OUTCOME-AUDITION), is:

| k | untouched rate /1000 | EXD10 | delay (sessions) |
|---|---|---|---|
| 6 | 18.0 | 0.70 | 6.6 |
| 8 | 8.6 | 0.67 | 10.5 |

At a similar untouched rate (12.2/1000), the filter's EXD10 is 0.82 with a delay of 4.4. That places it above the sampled streak k points (k = 3, 4, 5, 6, 8 in `streak_k_curve_descriptive`; every one has a lower EXD10). This comparison is descriptive, measured on the test window, and has no confidence interval. It is not a frontier claim and does not select a k (DNR:KILL-OUTCOME-AUDITION).

Retrospective onset: the filter reports a median of 5 sessions between detection and its retro-onset
estimate (mean 6.5). The detection index, not the retro onset, is what every metric above uses.

## Honest N, support and attrition

- **Cohort:** 327 / 374 deep-panel names. 31 were excluded for a share-basis break, 15 for a short train window and 1 for a short test window (census).
- **Calendar:** 801 SPY sessions, 2023-08-01 → 2026-10-08. The train end index is 479, so the test window is 321 sessions.
- **Positions:** 1401 per injection type.
- **Exclusions:** a replicate was excluded when either alarm was on at s−1. That removed 105 (filter only), 60 (streak only) and 97 (both) per type, plus 2 spikes at a missing session.
- **Kept:** 1139 step125, 1139 step150 and 1137 spike300 replicates, across all 327 names but only **9 distinct 20-session calendar blocks**.
- **P3 units:** 5256 (name, block) units; 97,152 evaluable test sessions.
- **Training fit:** nu = 3.61 and scale = 0.94, on 149,791 train z values.
- **tau_on calibration:**
  - tau_on = 0.30, the smallest grid value, chosen because it was the first value at or below the streak train rate. No grid fallback was needed.
  - The match is loose. The filter's train rate at 0.30 is 14.1/1000, against the streak's 28.4/1000, so the filter ran at about half the streak's train false-alarm rate. That handicaps the filter on raw sensitivity, not the streak.
- **Incumbent equivalence:** the incremental streak equalled `streak_above_norm` at all 1962 sampled points (0 mismatches).

## Limitations

1. **Injections are semi-synthetic level shifts.** Participation is multiplied by 1.25 or 1.5 over 40 sessions. Real activity regimes may change dispersion, autocorrelation or decay, and the result says nothing about those.
2. **Only 9 calendar blocks carry injections.** The time dimension of the bootstrap rests on 9 clusters, so the intervals are likely too narrow in time, even though the name dimension (327) is large. The P1a lower bound (+0.105) clears 0 comfortably, but it sits only just above the +0.10 bar.
3. **No Q03 basis correction or Q10 residualization.** Split-break names are excluded instead (EXCLUSIONS: "Q03 first; Q10 then Q11"). The input is the raw incumbent participation series.
4. **The tau calibration sits at the grid edge.** A grid that went lower than 0.30 might have matched the rates more tightly. That would raise both the filter's sensitivity and its false starts. This is pre-registered and not explored.
5. **Revision handling is tested only in unit tests (req2, req3).** The data vintage is fixed at cdab6268.
6. **This is a detection-quality result, not a predictive one.** No returns or prices are read. An "elevated" state is a venue/reporting-category activity state. It is not short interest, net buying, accumulation or institutional intent.

## Required before any promotion

KEEP here means research reference only. Limitations 2 and 4 are routed, not just disclosed. Before this filter may be put to the adjudication coverage gate, or proposed for any rank, size or gate role, a new pre-registered run must:

- **Extend the tau grid below 0.30**, so that tau_on is chosen inside the grid, not at its floor.
- **Use a time-cluster-robust interval**, either wider calendar blocks or a cluster-robust method, so the time dimension no longer rests on 9 blocks.

That run must re-test P1a against the +0.10 bar under the new interval. Until it exists, the incumbent `streak_above_norm >= 5` stays the owner of the served state.

## Reproduction

- Inputs: `panel.parquet` 63c69080…, `panel_deep.parquet` 12cc30a2…, SPY 6c785d55…, and a manifest of the 327 per-name Yahoo files `d06ec5ce…`. All 327 match the pre-freeze manifest `0553f7e4…`.
- Outputs: `results/eval_summary.json` 0e829db7…, `results/eval_replicates.csv` 5d9c4b75….
- Module history:
  - Module at evaluation: f3a3134d…. A docstring-only edit made it 3b322794….
  - The permitted deterministic re-run (RUNS.log 2026-10-09T10:00:02Z) reproduced both result files byte-for-byte.
  - The f3a3134d text was not retained, and reconstructing it from 3b322794 did not reproduce that hash. Its link to the current module therefore rests on that byte-identical re-run.
- Independent audit fixes (PREREG_AMENDMENT.md A1, sha256 9a339f1c…, witnessed in FREEZE.log at 10:20:47Z before the re-run):
  - evaluate.py now refuses unless the incumbent equals its PREREG §5 pin. The module must either equal its pin or match the A1 docstring-free evaluation-path AST pin (3b9130bb…). The decision is logged as `module_check`.
  - `update_detection_records` now closes an open record and stamps a new one when a newer episode is live. This function is off the evaluation path.
  - The gap docstring was reworded.
  - The module is now 1afb0d15…, with the same evaluation-path AST digest as 3b322794.
  - The single guarded re-run (RUNS.log 2026-10-09T10:22:27Z, `module_check.ok = true`, basis "eval-path AST equal to amendment A1 pin") reproduced both result files byte-for-byte. The verdict is unchanged.
