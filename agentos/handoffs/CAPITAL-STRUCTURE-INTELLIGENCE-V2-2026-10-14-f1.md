---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-f1-funding
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task F1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A28, A29, A30, A48, A49): ship
  engine/capital_structure/funding.py with
  project_funding(financials: FinancialInputs, commitments: CommitmentInputs,
  scenario: FinancingScenario) -> FundingSchedule on the frozen C0 contract,
  deterministic, no network, no collector, receipted, plus direct tests for
  review class 5 (conditional funding advertised as cash on hand), absent and
  negative burn, and dated gross, net and fees.
state_before: >
  C0 on origin/main admits the financials family with
  capital_structure.financial_item_observation.v1 (#9266). The F0 binding
  config (config/capital_structure_financial_input_binding.v1.json, PR #9268)
  was open and armed, not landed. The seat's C0 delta PR #9278 (corporate
  actions family plus the financials state-schema array fix) was open and not
  landed. No funding projection existed.
changed:
  - path: engine/capital_structure/funding.py
    what: >
      New deterministic projection. Opening = exact sum of the declared cash
      basis members on one date (else unknown); burn from operating cash flow
      over a named period, a non-negative fixed daily rate, or unknown;
      net_loss refused; non-negative cash flow is no burn and no runway;
      quarter-end period grid ending at horizon_end; dated obligations,
      gross and fee counted, net as a note only; scenario financing,
      revolver availability and conversion relief conditional and never
      counted; minimum liquidity from direct USD covenant terms only; deficit
      reported as an unknown closing with the computed value in the note;
      owner gaps from F0 named as unknowns. RULES and RULE_DIGEST published;
      CalculationReceipt on every schedule. state_id is the C0 schema-valid
      identity of the funding inputs consumed, not an IssuerCapitalState join
      key.
  - path: tests/test_capital_structure_funding.py
    what: >
      Direct tests covering the thirteen packet cases (review class 5,
      absent/unknown burn with no runway key anywhere, non-negative cash
      flow, net loss refusal, cent-quantized proration and period chaining,
      dated gross/net/fees, basis composition, minimum liquidity, deficit,
      point in time, conversion relief, interface/determinism/receipt, F0
      config parity) plus input refusals, warrant settlement, repurchase and
      other routes, and state-schema round trips of funding_schedule records.
  - path: .github/ci/legacy-jobs.yml
    what: Register the suite in the capital-structure contracts step after the closed-bundle suite.
  - path: agentos/decisions/DEC-CS-V2-FUNDING-F1.md
    what: Record the cash, burn, obligation, conditional-funding and deficit law.
verified:
  - claim: The funding suite and the C0 contract suite pass together with the F0 config present.
    command: >
      /opt/homebrew/bin/python3.12 -m pytest tests/test_capital_structure_funding.py
      tests/test_capital_structure_issuer_state_contracts.py -q -p no:warnings
    result: 167 passed (F0 config overlay byte-identical to PR #9268 head 6785f9fa).
  - claim: pyflakes is clean on both files.
    command: pyflakes engine/capital_structure/funding.py tests/test_capital_structure_funding.py
    result: exit 0.
  - claim: The suite is registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: The F0 config parity test runs in CI.
    what_would_verify: PR #9268 landing on origin/main; the parity test is skipped on a base without the config.
  - claim: F1 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green, a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    FundingSchedule.state_id must match ^state:cs: but F1's three-argument
    interface receives no IssuerCapitalState; the id identifies the funding
    inputs. Seat ruling 2026-10-14: joining belongs to C1, whose assembler
    holds the issuer state and re-stamps with
    dataclasses.replace(schedule, state_id=state.state_id); a schedule that
    was not re-stamped is a standalone computation and never a join key, and
    no C0 delta is opened. Pinned by
    test_schedule_state_id_is_an_input_identity_never_an_issuer_state_id
    (the derived id differs from CapitalState.state_id over the same inputs).
    Open for C1: perform the re-stamp.
  - >
    A C0 Quantity cannot be negative, so a deficit closing is unknown with
    the computed value in the note rather than a signed balance.
  - >
    Owners for restricted_cash, revolver_availability, accrued_interest,
    debt_maturity and committed_expenditure are not built (F0); each absent
    kind is a named unknown and known closings say they cover observed dated
    flows only.
  - >
    One commitment family per call: covenant_terms supply the floor,
    document_terms supply registration fees; a call with document_terms
    leaves the floor unknown.
  - >
    minimum_liquidity_covenant financial facts are not read; the floor comes
    only from covenant_terms.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
  - >
    All fabric labor lanes were exhausted (GLM 429 until 2026-10-19), so O4
    implemented F1 directly under the continuation law (accepted by the seat).
next_actions:
  - Merge F1 by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing by blob comparison.
  - '#9278 landed (05bcc762) before F1 opened; F1 is rebased onto it and test_consumed_financial_facts_are_admissible_capital_inputs_records validates CapitalInputs carrying the consumed financials against the C0 schema.'
  - Consumers of a funding schedule read FundingSchedule; they never recompute cash, burn or liquidity.
do_not_redo:
  - Use net loss as burn or as a fallback for an absent operating cash flow.
  - Count revolver availability, shelf or ATM capacity, or any scenario financing as cash on hand.
  - Substitute a net amount for a gross one, or sum a partial cash basis.
  - Report runway, probability, score, rank or sizing from a funding schedule.
  - Edit issuer_state_contracts.py or the state schema from an F-lane PR; the seat writes C0 deltas.
danger_areas:
  - ITEM_RULES and CASH_BASIS_MEMBERS mirror the F0 config and feed RULE_DIGEST; a config change without the module change fails the parity test once F0 is on main.
  - The quarter-end period grid and inclusive operating-cash-flow day count are part of RULE_DIGEST; changing either changes every receipt.
  - A producer that omits available_at on a financial fact or covenant term makes it invisible at every as_of.
prs: [9283]
---

# Capital Structure V2 — F1 funding schedule handoff

project_funding is the only projector of cash, burn and liquidity. Ship
state at write time: branch committed, PR to be opened NOT armed
(CI-authority edit), hand-merge with --match-head-commit on concluded green,
then one main baseline owed to the seat.
