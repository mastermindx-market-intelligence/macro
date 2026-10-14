---
key: RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES
question: >
  How may Rates & Inflation Command use inherited MRI release-forecast models, reaction windows and
  interpretation tests as evidence, given that every model spec was frozen after its designers had seen the
  2010+ history it would be scored on, and the accuracy record mixed legacy cross-vintage targets?
answer: >
  A coherent-target retrospective walk-forward of the frozen specs (task M0, 13 declared evaluations) can
  falsify or retrospectively qualify a model's claim but can never promote it; only forecasts issued after the
  E0 freeze commit and scored against their first print in the existing forward ledger are promotion-capable,
  with a prospective verdict at no fewer than 24 scored episodes per target (display from 12 with a CI).
  Legacy epochs stay readable as superseded and never validate the repaired target. Reaction windows are
  descriptive only, and the interpretation test is one blinded confirmatory run. E0 only tightens owners'
  kill rules and never relaxes or reactivates one.
rationale: >
  The PREREG files under research/release_forecast/ were frozen in 2026-07 with 2010+ data visible, so a
  rerun over that history is in-sample to design and its gains cannot be distinguished from selection. The
  forward ledger's issued rows are hashed (inputs_hash, code_receipt, model_epoch, target_epoch) and keep-first,
  which makes it the only record whose timing a reader can trust. The #7909 RD1 and swing results show the
  base rate: richer constructions lost to no-change on the expanded panel, so a retrospective win is weak prior
  evidence. Splitting falsify (cheap, now) from promote (natural time, later) lets the product withdraw stale
  accuracy claims immediately without inventing new ones.
alternatives:
  - option: Promote any model whose coherent-target backtest beats naive in both windows.
    why_not: >
      In-sample to the design period; repeats the legacy cross-vintage error under a new target name and would
      put an unearned accuracy badge on live surfaces (A11, A30).
  - option: Re-tune or extend the model set for the coherent target before evaluating.
    why_not: >
      Adds uncounted trials (A28) and is new research beyond the commission; any variant requires a superseding
      E0 revision with a declared budget first.
  - option: Build a dedicated RIC evaluator or scorecard to run M0/E1.
    why_not: >
      Forbidden (no new evaluation/forecast/publication plane). Existing owners cover it: trial_ledger,
      build_release_forecast forward ledger, the lib.store fred group, event_window's FOMC dates,
      grading_stats and the existing HAC/Holm helpers.
evidence:
  - "research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md (frozen questions, budgets, margins, stop rules)"
  - "E0 read-only census of origin/main 1e9364f5ab8c4452820731e87da2c138e53b0571 (PASS-WITH-GAPS): 2111 forward-ledger rows, no issued/withheld/abstained/missed row types; MRI families absent from trial_ledger"
  - "config/release_forecast_model_registry.yml:26 (official_first_print_epoch withheld) and :194 (historical_backfill_to_forward_ledger_allowed false) — coherent_ridge_v1 retrospective runs are research artifacts, never forward-ledger rows"
  - "Independent fabric review ric-e0-review-1 (grok-4.6, ubuntu2) of b493baa3: REJECT, 15 findings, all accepted and applied in protocol revision 2 (E0_RESEARCH_PROTOCOL.md §9)"
  - "PR #7909 head 1ddc25a80f6c2f6ce87a602f883056671f1f0d50 — RD1 48 configs (no-change MSE 176.53 vs 184.13), swing 18 configs (no candidate); DEC:RIC-RD1-NO-PROMOTION"
affects:
  - WS:RATES-INFLATION-COMMAND
  - scripts/build_release_forecast.py
  - data/release_forecast/forward_ledger.jsonl
  - data/trial_ledger.jsonl
  - engine/event_window.py
confidence: high
reversibility: costly
decided_by: fc3dfe4b-8c15-4c7b-ab42-5741f284f47b
decided_at: 2026-10-14
---

## Context

Rates & Inflation e2e completion programme, Chairman masterplan 2026-10-13 §7 (research programme H1–H4)
and task-graph row E0 ("freeze bounded research and outcome protocols … independent review before outcome
work", A28). Downstream tasks M0, E1, X0 and E2 execute the frozen protocol; a needed change returns to the seat
as a superseding E0 revision with its own declared trial budget before any run.
