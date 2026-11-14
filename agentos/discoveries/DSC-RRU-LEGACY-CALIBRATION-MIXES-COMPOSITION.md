---
key: RRU-LEGACY-CALIBRATION-MIXES-COMPOSITION
claim: >
  The pinned Risk Radar audit and tuner select every graded row, so explicitly
  modern or malformed-modern composition can change legacy sample counts, realized
  odds, eligibility evidence, Brier evaluation and calibration proposals.
falsifier: >
  Run python3 research/grey_deer/RRU_LEGACY_COHORT_TESTS_2026_09_09.py --baseline
  and then the same command without --baseline. Legacy-only and mixed-cohort
  numerical parity plus exclusion of explicit modern-only data closes this finding
  for the research candidate, not the deployed source or runner attachment.
so_what: >
  Preserve the serializer's method metadata and select the same evidence cohort
  through the existing audit owner for scorecard, realized odds and tuner.
  Filtering calibration evidence does not qualify an old grant for a new snapshot.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  RRU_LEGACY_COHORT_CONTRAST_RED_2026_09_09.txt and
  RRU_LEGACY_COHORT_CONTRAST_GREEN_2026_09_09.txt under research/grey_deer/;
  original source Macro eb9e91961ddc4f3043d0dad358602525e66eccda.
scope: ["WS:GREY-DEER-RISK-INTELLIGENCE", "engine/risk_radar_intl_audit.py", "engine/risk_radar_intl_tune.py"]
confidence: verified
---

Seven test methods: baseline ten expected assertion failures including subcases,
one legacy control; candidate seven passes. All inputs synthetic; no ledger I/O.
The native 179-test regression passed; the separate force probe remains red.
