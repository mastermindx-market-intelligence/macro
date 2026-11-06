---
key: FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80
question: >
  What held-out precision floor does the Q1 evaluation apply to the labelled
  specialist packs, and when is it fixed?
answer: >
  0.80 on the Wilson lower bound of held-out precision per (pack, section
  family), predeclared on 2026-10-31 at 07:04Z before the first evaluator lane
  ran, and immutable after any result is seen. Families below the floor, with any
  false positive on a negative example, or underpowered under the Q0 §6 minimum N
  are recorded on failed_families with disposition unavailable_research_only; no
  family is relabelled accepted, no failed cell is dropped from the denominator,
  N is never lowered after a result, and the floor may not move for a later
  generation of the same labels.
rationale: >
  A floor chosen after seeing the numbers cannot distinguish a pack that works
  from a threshold fitted to it. Predeclaring it in the seat's record before the
  evaluator produced any report is what makes the first Q1 result (all twelve
  packs unavailable_research_only; only PK01 above the floor at a lower bound of
  0.8157) an honest negative result rather than a tunable one.
alternatives:
  - option: Pick the floor per pack after inspecting the Q1 reports
    why_not: Post-hoc thresholds are indistinguishable from fitting; the Q0 protocol §10 forbids relabelling a failed family and §11 forbids "underpowered" being cured by lowering N.
  - option: Use raw precision instead of the Wilson lower bound
    why_not: Small held-out cells (N near the §6 minimum) make a raw 1.0 uninformative; the lower bound carries the cell size.
evidence:
  - "Seat memory checkpoint 2026-10-31 07:04Z predeclared the floor before lane fif-heldout-eval-20261031-r2 launched"
  - "research/financial_intelligence_fabric/reports/q1_held_out_20261031/: 12 reports, 336 trials = 306 predictions + 30 exclusions; PK01 precision lower bound 0.8157 is the only cell at or above 0.80"
  - "research/financial_intelligence_fabric/FIF_A37_HELD_OUT_Q1_RECORD_2026-10-31.md (#10299) records the per-pack PARTIAL cells against this floor"
  - "Independent review fif-heldout-evalrev-20261031-r1 note E1-2: the report schema carries no floor field, so the floor lives in this record and the A37 record, not in the reports"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - research/financial_intelligence_fabric/reports/
  - scripts/fif_held_out_evaluate.py
confidence: high
reversibility: one_way
decided_by: FIF Meta-CEO seat 96dc937a (Fable)
decided_at: 2026-10-31
---

Earlier PR text cites this key with a `DSC:` prefix (`DSC:FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80`);
it is a decision, recorded here under the same key. A later generation of
reports on fresh labels may carry its own predeclared floor only if that floor
is written down before that generation runs.
