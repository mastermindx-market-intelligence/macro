---
key: CS-V2-FUNDING-F1
question: >
  Masterplan task F1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A28, A29, A30, A48, A49) needs one deterministic
  function, project_funding(financials, commitments, scenario), that turns the
  frozen C0 FinancialInputs, CommitmentInputs and FinancingScenario into a
  FundingSchedule. Which financial facts may become cash on hand, what counts
  as burn, how are dated obligations, gross, net and fees, scenario financing
  and conditional commitments treated, and when must a closing balance be
  unknown instead of computed?
answer: >
  engine/capital_structure/funding.py composes the opening balance only as the
  exact sum of every member of the declared cash basis (CASH_BASIS_MEMBERS,
  mirroring the F0 binding) measured on one date at or before horizon_start
  and visible at scenario.as_of; a missing member, a same-date disagreement,
  members on different dates, a non-usd member or a later non-known
  observation make the opening unknown, never a partial sum. Burn comes only
  from the scenario's burn_basis: operating_cash_flow over a named reported
  period (a negative value prorated by elapsed period days at 0.01 usd), a
  non-negative fixed_usd_per_day, or unknown. net_loss is refused as "net loss
  is not burn"; a non-negative operating cash flow is no burn and no source,
  and the closing note says no runway is implied; an unknown burn, working
  capital or seasonality basis makes every closing unknown. Dated obligations
  are uses in the period that contains their due date; gross and fee facts
  both count, a net fact never counts and appears only as a note beside its
  gross, a net without its gross and an undated obligation are unknowns that
  block closings. Scenario financing (ATM, shelf takedown, registered direct,
  PIPE, equity line, debt draw, cash-settled warrant exercise) is a
  conditional gross source with a separate conditional fee use; revolver
  availability is a conditional source that must name its condition; a
  conversion or exchange relieves the matching debt maturity as a conditional
  use and provides no cash. Conditional flows never enter a balance.
  Registration capacity and context items (net loss, undated debt balance,
  receivables, registered offering capacity) are never flows. The minimum
  liquidity floor comes only from a direct USD covenant term; ambiguity is
  unknown, distinct values are contradicted, and a scenario resolution fills
  only an unknown floor. A negative computed closing is a deficit: unknown
  closing, computed value in the note, unknown next opening. The schedule
  carries a CalculationReceipt and no probability, score, rank, sizing or
  runway field.
rationale: >
  A29 and A30 fail in the same way: a number that looks like cash or burn is
  used because it is available. Treating every input by its declared role in
  the F0 binding, and refusing to compose a balance whenever any required
  piece is missing, dated differently, conditional or contradicted, removes
  the path by which net loss becomes burn, a revolver or ATM program becomes
  cash on hand, a net figure replaces a gross one, or a positive cash flow
  becomes infinite runway. An unknown closing is the honest answer when the
  inputs do not support a known one.
alternatives:
  - option: Use net loss (or net loss less non-cash items) when operating cash flow is absent
    why_not: REJECTED_BY_DESIGN. A29 says net loss is not burn; an absent burn basis is unknown.
  - option: Count undrawn revolver availability or registered shelf/ATM capacity as liquidity
    why_not: REJECTED_BY_DESIGN. Review class 5 and A30; conditional funding is reported as conditional and never enters a balance.
  - option: Sum the basis members that are present when one is missing
    why_not: A28; a partial sum misstates the basis it claims to measure.
  - option: Report a negative closing as a known negative balance
    why_not: C0 Quantity values are non-negative; the deficit is reported in the note and the next opening is unknown rather than inventing a signed balance.
  - option: Let a scenario UnknownResolution supply an opening member or a flow
    why_not: A30 says assumptions are not cash; only the minimum-liquidity floor may be resolved, and an opening-member resolution is recorded as unhonored.
evidence:
  - engine/capital_structure/funding.py (project_funding, FundingInputError, ITEM_RULES, CASH_BASIS_MEMBERS, RULES, RULE_DIGEST)
  - tests/test_capital_structure_funding.py (every schedule round-trips validate_state_record funding_schedule; config parity with the F0 binding when present)
  - engine/capital_structure/issuer_state_contracts.py (frozen C0 FinancialInputs, CommitmentInputs, FinancingScenario, FundingSchedule, CalculationReceipt)
  - config/capital_structure_financial_input_binding.v1.json (F0, PR #9268)
affects:
  - engine/capital_structure/funding.py
  - tests/test_capital_structure_funding.py
  - .github/ci/legacy-jobs.yml (capital-structure-intelligence registration)
  - masterplan consumers of a funding schedule (read FundingSchedule; never recompute cash or burn)
confidence: high
reversibility: easy
decided_by: opus-o4-under-fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Funding schedule for Capital Structure V2 (F1)

Cash on hand is the exact basis, measured on one date, or unknown. Burn is a
named operating cash flow or a stated rate, never net loss, and a positive
cash flow implies no runway. Obligations are dated, gross and fees count,
net is a note. Scenario financing, revolvers and conversions are conditional
and never move a balance. When an input is missing, conditional or in
conflict, the closing is unknown.
