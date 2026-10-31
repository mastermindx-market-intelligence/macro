---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-f0-financial-inputs
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task F0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A28, A29 and A30): bind the allowed financial-owner
  inputs to cash, debt, covenant and committed-use definitions without
  rebuilding FIF, so that F1 can project funding with each item at its own
  availability and basis.
state_before: >
  E0 (reference pack) and C0 (frozen issuer-state contracts) are on main. C0
  defines FinancialInputs, CommitmentInputs, Flow, FundingPeriod and
  FundingSchedule. Its COMPATIBLE_INPUT_SCHEMAS['financials'] is (), so no
  financial fact can bind. FIF owns 50 metric cells; covenant_terms and
  document_terms exist as code. Nothing recorded which owner feeds which
  funding item, or at what availability.
changed:
  - path: config/capital_structure_financial_input_binding.v1.json
    what: >
      New binding record (capital_structure.financial_input_binding.v1,
      capital-structure-financial-input-binding/1.0.0). It contains the
      contract status (the seat's delta PR #9266); the proposed
      financial_item_observation.v1 item schema; ten items with availability,
      cash-basis membership, flow role, source and owner state; five context
      items that never substitute; eight refused FIF headline metrics;
      cash-basis composition; burn and flow rules; six owners with sha256
      witnesses at main 1c8ff99ff7c0; seven limitations; four owner actions; and the
      forbidden list.
  - path: agentos/decisions/DEC-CS-V2-FINANCIAL-INPUT-BINDING-F0.md
    what: Record the binding, the rejected alternatives and the evidence.
verified:
  - claim: The C0 contract admits no financials schema on main.
    command: /opt/homebrew/bin/python3.12 probe constructing GenerationBinding('financials', 'capital_structure.financial_item_observation.v1', 'partial', generation_id='gen:fif-cells-2026-10-14') plus one fact
    result: ContractViolation, schema is not compatible with [].
  - claim: FIF cash_and_cash_equivalents excludes restricted cash.
    command: sed -n 78,92p config/fundamental_forensics/metrics/v1/mappings/core.yaml
    result: one alias, us-gaap:CashAndCashEquivalentsAtCarryingValue.
  - claim: No owner emits restricted cash, revolver availability, accrued interest, dated maturities or committed expenditures.
    command: grep metric_id config/fundamental_forensics/metrics/v1/metric_catalog.yaml; sed -n 30,70p engine/capital_structure/covenant_terms.py; sed -n 145,175p engine/capital_structure/document_terms.py
    result: 50 FIF ids with no such item; six covenant term names; five fee-table term names.
  - claim: covenant_terms emits minimum_liquidity_amount without a normalized value.
    command: sed -n 360,412p engine/capital_structure/covenant_terms.py
    result: non-schedule terms carry normalized.value null with raw clause text.
  - claim: The record is valid JSON and Agent OS validates.
    command: python3 -m json.tool config/capital_structure_financial_input_binding.v1.json; python3 scripts/agentos.py validate
    result: parse ok; validate exit 0.
unverified:
  - claim: F0 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green, then a bare git fetch and a per-path blob comparison of the three changed paths against origin/main.
  - claim: F1 enforces this record.
    what_would_verify: engine/capital_structure/funding.py tests that fail on a collapsed headline, net loss as burn, an infinite runway or a conditional commitment counted as cash.
unresolved:
  - >
    C0 delta PR #9266 (seat-owned) adds the financials schema. Until it lands
    on main, F1 binds financials not_built with facts=() and the opening
    balance is unknown.
  - >
    Restricted cash, revolver availability, accrued interest, dated
    maturities and committed expenditures have no owner. The covenant
    monetary value is not normalized. These are owner actions, not F0 or F1
    work.
  - >
    The workstream record (decisions and handoffs lists) is not patched here;
    it goes in the seat's records PR.
next_actions:
  - Merge F0 on concluded green (records/config only, no CI-authority path); verify landing by blob comparison.
  - Start F1 (deps F0) in a fresh worktree; project_funding reads this record.
do_not_redo:
  - Re-census FIF and the CS term owners to rediscover the item owners; read this record and re-read only owners whose sha256 changed.
  - Rebuild FIF, add a financial collector, or parse raw covenant clause text in a consumer.
  - Use net_debt, working_capital, free_cash_flow or another collapsed headline as a funding input.
danger_areas:
  - The owner sha256 values are witnesses at main 1c8ff99ff7c0 and are not compared live; a test that compares them would red on every unrelated owner edit.
  - C0 counts assumed flows in the balance identity. F1 must keep scenario financing proceeds conditional, so that an assumption never adds cash.
  - A covenant's defined Liquidity may include revolver availability. Never compare it to a cash basis without the declared minimum_liquidity_basis assumption.
prs: [9268]
---

# Capital Structure V2 — F0 financial-input binding handoff

Read config/capital_structure_financial_input_binding.v1.json before any funding work.
It binds each funding item to its owner, availability and cash-basis membership, and it
names the items no owner emits yet. Ship state at write time: branch pushed, pull request
open, armed with merge-on-green last.
