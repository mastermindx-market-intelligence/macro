---
key: PROPHET-US-B16-CYCLE-INTERNAL-DIAGNOSTIC-ERA
question: >
  After the B16-a closure matrix and the rule-4 era record, what Cycle work is admissible
  now, on which era, and what remains gated? (R6 work card B16, rulings R6-B16-01 and
  R6-B16-01a, pre-registration in PR 7847)
answer: >
  The measured matrix admits NO pilot domain: for domain (a) rule 1 passes on the tracked
  ALFRED vintages (NEWORDER 354, ISRATIO 354, AWHMAN 357, AMTMUO 183 periods) but rules 2
  and 3 fail at every cut (first membership 2026-08-13; one of six constituents delisted;
  no failed universe), rule 4 is UNKNOWN and rule 5 is unresolved; domains (b) and (c) fail
  rule 1. The rule-4 era record finds no usable macro-only era while AWHMAN break dates stay
  UNKNOWN, so R6-B16-01a substitutes INDPRO (output; 357 periods; breaks 2002-12 and
  2025-11-24) as the third mechanism beside NEWORDER and ISRATIO and ratifies a macro-only
  INTERNAL diagnostic era 2002-12 → 2025-05-15 (about 269 months), admissible only once the
  rights register merged. The Cycle (a) diagnostic is pre-registered (endpoint H1
  concordance ≥ 0.60 with lower 95% bound > 0.50 on N ≥ 12 distinct episodes; frozen
  initial-release transforms with a 3-month availability deadline; window and exclusions
  verbatim) and no return may be computed before the pre-registration merge sha
  0c9e30ad4da0325b135bbf621b4498174dcc875b. The result is internal-only evidence about
  the machinery, never "no alpha" and never a pilot, public surface or B18 unblock.
rationale: >
  The gate (DEC:PROPHET-US-D03-SOURCE-READINESS-SCOPE) was measured rather than argued:
  the matrix run was read-only and allowlisted, every rule carries a receipt, and the era
  question was answered by a separate record that reported "none" honestly before the seat
  substituted a series with recorded breaks. A pre-registered internal diagnostic is the
  only construction that can learn whether the mechanism is worth a provider question
  without an outcome-selected domain.
alternatives:
  - option: Run the diagnostic on AWHMAN with an assumed break-free history.
    why_not: Its break dates are UNKNOWN in the era record; an assumed history is the rule-4 forbidden shortcut.
  - option: Treat a passing internal diagnostic as a pilot admission or a B18 unblock.
    why_not: Rules 2, 3 and 5 still fail; the diagnostic is bounded to machinery evidence by the pre-registration's release limit.
  - option: Ask the Chairman the paid-provider question before the matrix.
    why_not: Rule 5 (rights/publication) is unresolved and the question is askable only with a measured matrix attached.
evidence:
  - research/prophet_v4/r6_program/wave2/D03_SOURCE_READINESS_MATRIX_2026-09-23.md
  - research/prophet_v4/r6_program/wave2/alfred_depth_b16a.json
  - research/prophet_v4/r6_program/rulings/R6-B16-01_ADMISSION_2026-09-23.md
  - research/prophet_v4/r6_program/wave2/CYCLE_A_ERA_TREATMENT_RECORD_2026-09-23.md
  - research/prophet_v4/r6_program/rulings/R6-B16-01a_ERA_RATIFICATION_2026-09-23.md
  - research/prophet_v4/r6_program/wave2/CYCLE_A_MACRO_DIAGNOSTIC_PREREG_2026-09-23.md
  - research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md
  - Macro PRs 7842 (matrix + admission), 7843 (rights register), 7845 (era + ratification), 7847 (pre-registration)
affects:
  - WS:PROPHET-US-V4-RECOVERY
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-23
---

## Scope

Closes D03 at the matrix (measured, not argued) and admits exactly one thing: a
pre-registered, internal-only, macro-only diagnostic on the ratified era with three
mechanisms. The diagnostic run is a separate fabric lane that starts only after the
pre-registration merged and reports its endpoint as internal evidence.

## What this decision does not do

It admits no pilot domain, no public or user-facing Cycle surface, and no B18 policy
research; it does not license any provider data; it does not compute or cite a strategy
return; and a diagnostic that misses its endpoint says only that this construction on
this era missed — never that the mechanism does not exist.
