---
key: C1-AR1-GATE-UNCALIBRATED-SERIES-FAILS-CALIBRATED
question: >
  Lane C1's pre-declared control (lag-21 AR(1) of the long-period rotation-persistence
  series must exceed 0.5) reads BROKEN at -0.0404. Is the gate miscalibrated, is the
  series genuinely non-persistent, and may the primary verdict be rewritten?
answer: >
  Both, and no. A pre-declared calibrated-control sensitivity (round 2, item E6: 200
  positive-control simulations with fixed sector drift plus iid noise at the observed
  cross-sectional and idiosyncratic scales, 200 block-permuted nulls, seed 20261004)
  shows that a true persistent signal of the simulated magnitude reaches a median lag-21
  AR(1) of only +0.1821 (5th percentile +0.1654), so the 0.5 gate was uncalibrated. But
  the observed statistic (-0.0404) also sits below the null 95th percentile (+0.0181) and
  far below half the positive-control median, so the series fails the calibrated test
  as well: CALIBRATED_FAIL. controls.status stays BROKEN; the primary gate is never
  re-tuned; every downstream consumer (C2) keeps reading INSUFFICIENT SUPPORT by rule.
rationale: >
  The epistemics law allows a null to be printed, never hidden, and forbids re-tuning a
  pre-registered gate after seeing the data. Running a calibrated sensitivity beside the
  primary gate answers the "was the gate fair" question without touching the verdict.
  The answer closes the specific construction tested (the LP series as C1 defines it,
  21-session lag) and not the rotation-persistence search space: a differently
  constructed persistence statistic may be pre-registered in a later wave.
alternatives:
  - option: "Lower the primary gate to the calibrated level (about 0.09) and re-grade C1 PASS"
    why_not: "Post-hoc gate editing; and the series fails even that level, so the re-grade would be false twice."
  - option: "Drop the AR(1) control and let C2 condition on the terciles anyway"
    why_not: "The control is what makes the terciles a state rather than a label; C2's rule was frozen on it."
  - option: "Declare rotation persistence dead"
    why_not: "A kill closes the construction tested, not the search space (house epistemics law)."
evidence:
  - "results/C1/result.json controls: ar1_lag21 -0.0404, ar1_pass false, status BROKEN; calibrated_control: n_sims 200, scales cs_std_median 0.030204 / idio_std_median 0.030204, positive_control median_lag21 0.1821 p5 0.1654, null p95_lag21 0.0181, calibrated_status CALIBRATED_FAIL"
  - "rotation_state_daily.parquet sha256 9361dbf0... byte-identical across rounds 1 and 2"
  - "Opus review of C1 round 2 (2026-10-04): every round-1 number reproduced exactly; the lane's E6 null was mis-built (iid noise with per-row shuffles, not the pre-declared block permutation of the observed panel) — the reviewer's spec-correct block-permutation null (seed 20261004, 200 sims) gives lag-21 p95 +0.0419, median +0.0016, p5 -0.0487, with the observed -0.0404 at the 9.5th percentile, so CALIBRATED_FAIL stands under the correct null; round 3 rebuilds the null and the leak tests (G1-G8) without changing any number"
affects:
  - "WS:PROPHET-REGIME-TIMEFRAME-RESEARCH"
  - "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1/**"
  - "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C2/**"
confidence: high
reversibility: easy
decided_by: "coo-fable seat (Claude Code session f273dd7d)"
decided_at: 2026-10-04
---

# The C1 persistence gate was uncalibrated, and the series fails the calibrated gate too

The honest reading for the product is a scoped null: the September 2026 narrative that
rotation persistence should steer the Prophet confirmation grain has no measurable
persistence to steer by, on this construction, in this data. C2 reports the
counterfactual anyway (NOT SUPPORTED, DiD positive and inside its interval), so the
answer does not depend on the gate.
