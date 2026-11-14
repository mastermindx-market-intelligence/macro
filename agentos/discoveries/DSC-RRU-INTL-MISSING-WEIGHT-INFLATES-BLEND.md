---
key: RRU-INTL-MISSING-WEIGHT-INFLATES-BLEND
claim: >
  International Risk Radar composite_series includes missing group weight in the
  numerator but excludes it from the denominator, inflating partial-input blends.
falsifier: >
  On the pinned source, run the 40-case RRU1A_MISSINGNESS_TESTS_2026_09_08.py;
  if partial/missing-group cases agree with the independent available-weight
  oracle before the candidate is applied, this mechanism is not reproduced.
so_what: >
  Repair the existing arithmetic before discretionary weight changes; evaluate
  downstream percentile/calibration impact and never transfer synthetic proof
  into a claim of historical or live predictive improvement.
kind: data
verified_at: 2026-09-08
verified_by: >
  research/grey_deer/RISK_RADAR_INTEGRITY_RESULTS_2026_09_08.json;
  RRU1A_BASELINE_RED_2026_09_08.txt (40 tests, 20 expected failures);
  RRU1A_CANDIDATE_GREEN_2026_09_08.txt (40 pass); source eb9e91961ddc4f3043d0dad358602525e66eccda.
scope:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - engine/risk_radar_intl.py
  - research/grey_deer/
confidence: verified
---

Two equal-weight component values of 0.9 become a raw blend of 1.4 when one
component becomes missing; the correct available-weight mean is 0.9. The probe
uses an identity percentile to isolate aggregation. This is not a live 140 score.

The one-line research candidate changes only the additive missing contribution
from 0.5 to 0.0 while the denominator continues excluding missing weight. Ten
actual profile definitions passed complete, partial, missing-group and all-missing
synthetic cases with the candidate. Complete-input windows retain exact parity.

Correcting a missing historical observation may still change today's percentile
through the trailing rank window even when today's inputs are complete. Real-data
impact and calibration applicability remain unverified. The candidate is a patch
artifact applied in memory for research; engine source and production are unchanged.
