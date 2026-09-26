---
key: SIGNAL-FOUNDRY-MIXED-FREQUENCY-CLOCK
claim: At macro 9579caf3f950f1a2e7b959a9b3b68d26e42e5d06 the sf-battery-1 evaluator
  applies price horizons as native feature-row strides and annualizes compressed monthly/weekly
  strategy returns as daily.
falsifier: Run the original and repaired evaluators on the identical pinned five-candidate
  inputs and 22-construction trial family described in research/evidence/signal-lab-clock-repair-20260915/same-data-comparison.json;
  disprove either the 3-5 original HAC counts or the original frequency-mismatched
  annualization.
so_what: 'Do not interpret the five original insufficient_power verdicts or exaggerated
  backtest statistics as correctly measured research. Preserve them historically,
  use a versioned correction for review, and do not promote any of the five: the corrected
  diagnostic still produces zero pass candidates.'
kind: landmine
verified_at: '2026-09-15'
verified_by: tests/test_sf_clock_repair.py; native same-data comparison PID 55657;
  research/evidence/signal-lab-clock-repair-20260915/verification.json
scope:
- research-factory
- macro:engine/signal_foundry/harness.py
confidence: verified
---

# Versioned numerical defect

The same-data repair retained 106, 58, 108, 58 and 108 nonoverlapping price-label windows for SF-0013, SF-0014, SF-0020, SF-0021 and SF-0022 respectively. These are not independent-episode counts. Four diagnostics were era-specific and one null; none passed. Release/vintage cleanliness remains unproven.
