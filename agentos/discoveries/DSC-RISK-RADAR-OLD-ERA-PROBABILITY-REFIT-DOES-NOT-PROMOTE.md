---
key: RISK-RADAR-OLD-ERA-PROBABILITY-REFIT-DOES-NOT-PROMOTE
claim: >-
  A preregistered state-only Risk Radar probability surface fitted exclusively on
  pre-2020 reconstructed history does not clear the 2020+ promotion bar. It
  preserves the current H21 authority partition and improves point Brier at H5/H10,
  but worsens H21 Brier and misses the paired uncertainty gates, so no live
  probability change is supported.
falsifier: >-
  Re-run scripts/research/risk_radar_probability_recal_oos.py from method freeze
  293b19626d426d1812b5a88a574773fc1dca9d63 on the receipt-bound committed
  inputs. The candidate surface, 2020+ population fingerprints, paired Brier
  deltas, and promotion verdict must reproduce.
so_what: >-
  Do not tune another candidate against the already-observed 2020+ holdout or
  promote the old-era ~42% upper-state H21 fit. Keep current live odds. Harden
  the self-correction loop so future prob_cal changes require their own
  probability/Brier and authority-partition do-no-harm gate.
kind: data
verified_at: 2026-09-22
verified_by: "python3 -m pytest tests/test_risk_radar_review.py -k probability_recal_oos -q"
scope:
  - macro
  - grey-deer-risk-intelligence
  - risk-radar-probability-calibration
confidence: verified
---
