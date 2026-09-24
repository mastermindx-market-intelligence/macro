---
key: RIC-RD1-NO-PROMOTION
question: >
  Does the frozen yield/curve/real-rate-only RD1 experiment justify promoting
  a rates-direction or jump-warning model into production decision authority?
answer: >
  No. Reject this exact construction for promotion while preserving the reproducible
  research consumer, observed rates context and the broader program. Proceed toward
  qualified market-implied paths and consensus-relative, point-in-time macro inputs;
  do not tune the failed model after seeing these outcomes and call that validation.
rationale: >
  All 48 generated configurations were registered before source reads. The primary
  2021-2025 10Y/five-observation-interval candidate had 4.3034% higher MSE than
  no-change on 1244 origins and lost in every primary year. Real-rate decomposition
  improved curve-only MSE by only 0.0252%. Eleven of twelve cells lost to no-change.
  At the predeclared jump threshold the richer candidate generated zero alerts.
  The September 22 reconstruction was not a strong warning and was not issued then.
alternatives:
  - option: Promote the richer model because it beat naive momentum.
    why_not: The simpler no-change benchmark beat it, failing the primary practical hurdle.
  - option: Select the small positive 30Y one-interval secondary cell.
    why_not: Its 0.14% gain cannot rescue the predeclared primary failure or justify selection after outcomes.
  - option: Abandon real yields and the entire rates forecasting program.
    why_not: This test concerns one frozen construction, not all conditional or macro-surprise hypotheses.
evidence:
  - "Macro PR #7909; frozen source 8796829eea9fe8792a73155f64d5c1dbe83ae3b6"
  - "research/rates_direction/RD1_RESULTS_2026-09-24.md"
  - "research/rates_direction/results_v1.json; SHA256 4c91cbd0afb4e5051478e15df9029747f0864323f0a5a40960cbfb3b92a3d812"
  - "data/trial_ledger.jsonl family ric_rates_direction_v1: 48 append-only registrations"
affects: ["WS:RATES-INFLATION-COMMAND", "engine/rates_direction_research.py"]
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-24
---

This ruling blocks promotion, not research. It does not add a universal DNR kill,
change existing display-context authority, or claim independent statistical review.
A demonstrated source/method bug is a material invalidator; preserve this freeze and
all trial history, register any replacement construction, and state what changed.
The program delegation DEC:RIC-RATES-DIRECTION-PROGRAM remains in force.
