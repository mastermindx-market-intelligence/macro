---
key: RIC-BASIS-CONTRACT-V1-QUALIFIED-COMPARISON
question: >
  How should Rates & Inflation Command produce numerical comparisons between releases, house
  forecasts, futures-implied rates, SEP projections, curve points and decompositions so that target,
  model, vintage, basis and rights survive to every human and machine consumer?
answer: >
  Every comparison goes through one pure, versioned basis module (engine/rates_command_basis.py,
  rates_command_basis.v1) that wraps each value in a QualifiedObservation with a closed evidence-class
  enum and a value state, evaluates a registered ComparisonRule in a fixed refusal order, and returns
  a ComparisonResult whose status is one of directly_comparable, comparable_after_transformation,
  not_comparable, not_identified or unavailable. Unknown basis yields no number; an under-identified
  policy path yields the feasible alternatives, never one forced path. The board adds the contract
  additively (basis_contract_version, qualified_comparisons, per-row basis) and leaves regime_outlook
  byte-compatible.
rationale: >
  The 2026-10-13 masterplan's principal requirement is correct interpretation, not another dashboard.
  Current main fabricates a "ZQ fed-funds futures" source label when the Fed-path source is absent
  (engine/rates_inflation_command.py:847-848) and drops target/epoch/maturity qualifications in the
  board summary. A single pure contract with frozen reason codes makes every refusal auditable and
  testable, prevents SOFR/EFFR, par/zero, CPI/PCE and KW/ACM conflation by construction, and lets the
  same object travel to the template, machine projection and brain packet without re-interpretation.
  The monthly-average identity (15 days at 4.50 plus 15 at 4.00 averages 4.25: -25 bp average, -50 bp
  level) proves that one number cannot identify a path without effective dates and a pre-change rate.
alternatives:
  - option: Add per-consumer qualification fields ad hoc in each builder and template.
    why_not: >
      Each consumer would re-derive comparability differently; the A03 defect is exactly a consumer-side
      default. No single place could prove refusal order or rights handling.
  - option: Build a new rates evaluation/publication plane that recomputes comparisons nightly.
    why_not: >
      Forbidden by the commission (no new source/calendar/forecast/evaluation/publication/control plane)
      and by DEC:RIC-CANONICAL-COMPOSITION-BOUNDARIES; the contract is a pure library consumed by the
      existing board builder.
  - option: Convert SR3 to an EFFR-equivalent with a fixed SOFR-EFFR spread so one strip always shows.
    why_not: >
      Invents a basis the evidence does not identify; the masterplan forbids it. sr3_vs_zq.v1 refuses
      with basis_mismatch:rate_index unless a qualified basis is supplied.
evidence:
  - "research/rates_inflation_command/seat_20261014/B0_BASIS_CONTRACT_FREEZE.md (frozen names, enums, reason codes, rules, 13 named tests)"
  - "engine/rates_inflation_command.py:847-848 defaults a missing implied source to 'ZQ fed-funds futures' (A03 defect, origin/main 402b57de)"
  - "engine/fed_path.py:113-119 labels ZQ/SR3 correctly only when that strip is used"
  - "engine/market_os/macro_workspaces/monetary_policy.py:572 re-defaults the same label downstream (excluded Market OS owner; routed as a gap)"
affects:
  - WS:RATES-INFLATION-COMMAND
  - engine/rates_command_basis.py
  - contracts/rates_command_basis.v1.schema.json
  - engine/rates_inflation_command.py
  - engine/fed_path.py
confidence: high
reversibility: costly
decided_by: fc3dfe4b-8c15-4c7b-ab42-5741f284f47b
decided_at: 2026-10-14
---

## Context

Rates & Inflation e2e completion programme, Chairman masterplan 2026-10-13 (§4 semantic model, §5
interfaces, §6 first implementation, acceptance A03-A06, A16-A19, A22-A24). The freeze is binding on
both domain orchestrators: names, fields, enums and refusal codes may not be renamed, dropped, merged
or re-meant; a needed change returns to the seat as a spec delta.
