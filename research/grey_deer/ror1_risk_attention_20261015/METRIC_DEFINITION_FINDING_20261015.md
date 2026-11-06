# ROR-1 — False-positive-rate versus false-discovery-rate research audit

**Recorded:** October 15, 2026. **Status:** verified arithmetic inconsistency in
a historical tuning **report**, not evidence of a new production model bug.
**Source:** Macro `research/RISK_RADAR_TUNING.md` Git blob
`913ad64f531681415473457dd0fea4e4bcd5eca7`, inspected at Macro
`9df20a3ac37d1f33d616d871abfd9857f8cd5d26`.

## Reproduced discrepancy

The report defines `fp_rate = FP / non-positive days` in section 1: conventional
false-positive rate (FPR), the fraction of truly negative **days** that alerted.
In section 2's `regime_gating` comparison, it instead reports:

| Run | Reported precision | Reported fp_rate | 1 − precision |
| --- | ---: | ---: | ---: |
| Full baseline | 0.085 | 0.915 | **0.915** |
| Full gated | 0.249 | 0.751 | **0.751** |
| 2020+ baseline | 0.099 | 0.901 | **0.901** |
| 2020+ gated | 0.259 | 0.741 | **0.741** |

All four match **false-discovery rate** (FDR = FP/(TP+FP) = 1 − precision),
not necessarily the true FPR. The `conjunction_required` comparison's
precision .188 and stated fp_rate .351 are not FDR; the report thus appears
to mix metric definitions. This can mislead review of alert-fatigue costs.

## Arithmetical falsifier from one named population

The report's **full-history** regime-gating headline H21/8% forecast
comparison states approximate gated fire-rate **17%** and precision **.249**.
It also shows full-history H21 **5%** event prevalence **.1890**, which is
an upper bound on the frequency of H21 **8%** events under the same price
path and eligible day set. Using these rounded published quantities:

- False alerts / all days = .17 × (1 − .249) = **.12767**.
- FDR = 1 − .249 = **.751**.
- Conventional FPR = FP / non-events; with event prevalence bounded between
  0 and .189, FPR lies approximately in **[.12767, .15742]**, not .751.

This inequality **requires the same eligible day population and horizon**,
the usual nesting of 8%-event days within 5%-event days, and assumes the
reported ~17% fire-rate is representative; it is an **illustrative bound**
based on rounded table values, not recovery of the original confusion
counts. The decisive, assumption-light signal is the repeated
`fp_rate == 1 − precision` equality in the four regime-gating rows.

## Mandatory source-owner response

1. Recover the original evaluation runs and exact eligible populations for
   the day-level, episode-level, full-history and modern-era comparisons.
2. Report the raw `TP, FP, TN, FN` and exact negative/population counts for
   each horizon, event definition, fold and episode policy.
3. Recompute independently `precision=TP/(TP+FP)`,
   `FDR=FP/(TP+FP)`, `FPR=FP/(FP+TN)`,
   `fire_rate=(TP+FP)/N`, episode false interruptions and
   how long users remain warned.
4. Correct the historical report and downstream calibration/alert-budget
   claims only through the incumbent model/evaluation source owner.
5. Do not loosen the current Risk Radar gate, retrospectively retune issued
   forecasts, or claim that the historical 0.751 number measures
   false interruptions per trading session.

## Reproduction

Pure standard-library calculator: `metric_definition_audit.py`.
Tests: `test_metric_definition_audit.py`, **4/4 passed** under Python
3.14 after a test-first RED against a stub. No price series, user
notification or trading model was executed or changed.

The report's 17% fire-rate is explicitly approximate, so the numerical
FPR bounds are explanatory; exact counts remain mandatory. A corrected
research metric is not production acceptance or evidence of October 14
prediction skill.
