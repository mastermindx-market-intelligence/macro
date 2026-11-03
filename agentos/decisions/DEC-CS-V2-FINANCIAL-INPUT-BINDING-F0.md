---
key: CS-V2-FINANCIAL-INPUT-BINDING-F0
question: >
  Masterplan task F0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, acceptance rows A28, A29 and A30) must bind the allowed
  financial-owner inputs to cash, debt, covenant and committed-use
  definitions without rebuilding FIF, before F1 projects funding. Which
  owner feeds each item, at what availability and basis, and what may F1
  never infer?
answer: >
  One machine-readable record, config/capital_structure_financial_input_binding.v1.json
  (schema capital_structure.financial_input_binding.v1, version
  capital-structure-financial-input-binding/1.0.0), is the binding. It names
  ten items, each with its own availability and cash-basis membership.
  unrestricted_cash is available now (FIF cash_and_cash_equivalents, which
  maps only CashAndCashEquivalentsAtCarryingValue and so excludes restricted
  cash). restricted_cash is restricted. marketable_securities is available
  after sale (FIF short_term_investments). receivables are collection
  dependent and belong to no cash basis. revolver_availability is
  conditional and undrawn. accrued_interest, debt_maturity and
  committed_expenditure are dated obligations. minimum_liquidity_covenant is
  a floor (covenant_terms minimum_liquidity_amount). financing_cost keeps
  gross, fee and net apart. Five context items (operating cash flow, net
  loss, historical capex, undated debt balances and registered offering
  capacity) may never be substituted for cash, burn, a commitment or a
  maturity. Eight FIF headline metrics are refused because they collapse
  bases. Cash-basis composition, burn rules (net loss is never burn;
  negative or unknown burn gives no runway) and flow rules (an assumption
  never adds cash; a conversion relieves an obligation without cash; an
  undrawn conditional commitment is not cash) are data that F1 enforces.
  The C0 contract on main admits no financials schema; the seat's delta
  PR #9266 adds capital_structure.financial_item_observation.v1. F1 is
  built against that name and consumes it on main only after #9266 lands;
  with no facts it binds financials as not_built and the opening balance
  stays unknown.
rationale: >
  The item owners are uneven. FIF has instant cells for cash, short-term
  investments, receivables and undated debt. covenant_terms states a
  minimum-liquidity term but emits its value un-normalized. document_terms
  emits registration-fee-table rows only. Nothing emits restricted cash,
  revolver availability, accrued interest, dated maturities or committed
  expenditures. Writing each item's availability, basis membership, owner
  and owner state down as data lets F1 report each missing item as a named
  Unknown, never a zero. It also stops F1 from collapsing items into a
  headline cash or net-debt figure, or using net loss or free cash flow as
  burn, which A28 to A30 forbid. Rebuilding FIF or adding a collector is out
  of scope, so missing owners stay owner actions.
alternatives:
  - option: Admit FIF metric-cell receipts directly as FinancialInputs.facts
    why_not: The FIF receipt is a nested selection-proof graph whose proof
      scope is selected-occurrence consistency, not an item with an
      availability class; and the C0 contract admits no financials schema at
      all. A flat CS item schema plus a contract delta keeps the FIF owner
      intact and the availability explicit.
  - option: Use FIF net_debt, working_capital or free_cash_flow as funding inputs
    why_not: Each collapses separate availability bases into one headline
      (A28) or substitutes a historical derived flow for burn (A29).
  - option: Date long_term_debt_current as due within twelve months of the balance-sheet date
    why_not: A balance-sheet classification is not a due date; A30 requires
      dated obligations, so it stays a timing Unknown.
  - option: Parse the raw minimum-liquidity clause text in F1
    why_not: That re-extracts inside a consumer; normalization belongs to the
      covenant_terms owner, so the floor stays unknown until the owner emits
      a usd value.
  - option: Let scenario financing proceeds enter the balance identity as assumed sources
    why_not: A30 says assumptions are not cash. Proceeds that depend on a
      future action stay conditional sources, so an assumption can only
      reduce modeled cash (assumed burn), never add to it.
evidence:
  - config/capital_structure_financial_input_binding.v1.json (contract_status, item_schema, items[10], context_items[5], refused_collapsed_metrics[8], cash_basis_composition, burn_rules, flow_rules, owners[6], limitations[7], owner_actions[4], forbidden)
  - engine/capital_structure/issuer_state_contracts.py COMPATIBLE_INPUT_SCHEMAS['financials'] == () and the probe GenerationBinding('financials', 'capital_structure.financial_item_observation.v1', 'partial', ...) raising ContractViolation
  - config/fundamental_forensics/metrics/v1/metric_catalog.yaml (50 metric ids) and mappings/core.yaml (cash_and_cash_equivalents maps CashAndCashEquivalentsAtCarryingValue only)
  - engine/capital_structure/covenant_terms.py COVENANT_TERM_NAMES and the non-schedule reported/normalized construction (value null)
  - engine/capital_structure/document_terms.py TERM_NAMES (five fee-table fields)
affects:
  - config/capital_structure_financial_input_binding.v1.json
  - masterplan task F1 (engine/capital_structure/funding.py reads the record and enforces its rules)
  - C0 contract delta PR #9266 (seat-owned; adds the financials schema)
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# Financial-input binding for Capital Structure V2 (F0)

F0 binds each funding item to its owner, availability and cash-basis
membership, and it records which items no owner emits yet. It rebuilds
nothing and adds no collector. Today's C0 contract admits no financials
schema, so F1 runs with an unknown opening balance until the seat's delta
PR #9266 lands. Owner sha256 witnesses are taken at main 1c8ff99ff7c0. A changed
witness means the record must be re-read against the new bytes. It does not
mean a missing owner now exists.
