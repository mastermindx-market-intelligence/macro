---
key: CS-V2-STATE-CONTRACTS-FROZEN-V2
question: >
  Masterplan task C0 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  wave W0) must freeze the same-owner state and scenario types, per-family
  provenance, projection compatibility and interface ownership before any V2
  compiler, resolver, capacity, supply or funding module is written. What
  exactly is frozen, where does it live, and what may a later wave not change
  without a superseding decision?
answer: >
  One typed module, engine/capital_structure/issuer_state_contracts.py
  (STATE_CONTRACT_VERSION capital-structure-state-contracts/2.0.0, record
  schema capital_structure.state.v2), and its JSON Schema
  contracts/capital_structure_state.v2.schema.json are the frozen contract.
  Eleven record kinds (state, state_request, capital_inputs, rule_pack,
  financing_scenario, capacity_envelope, supply_envelope, funding_schedule,
  instrument_set, share_basis_result, calculation_receipt) each carry one
  schema constant in RECORD_SCHEMAS. Every quantity names unit, basis, status,
  evidence and applicability; an unknown quantity has a null value and is
  never 0 or infinity; a known bound needs evidence. Every state family
  (identity, share_basis, registration, instruments, cash_funding,
  transactions, uncertainty, change_events) carries its own provenance:
  support level, bound input generations with their schemas, as-of, and the
  unavailable capabilities it still cannot answer. Compatibility with the
  shipped projection family (capital_structure.projection_bundle.v1, version
  prefix capital-structure-event-projection/1., identical context-only
  AUTHORITY) is checked by projection_compatibility, never assumed, and a
  label from UNAVAILABLE_CAPABILITIES leaves a state only alongside an entry in
  capabilities_proven. Scenario identity is the digest of every assumption
  with the label excluded, so any assumption change is a new scenario and a
  scenario-bound result names that scenario in its receipt. A capacity
  aggregate is bounded by the sum of its route limits and by every shared pool
  its routes consume; a feasible witness must respect each route, each pool
  and the aggregate. The §9 interface table (compile_issuer_state,
  resolve_instruments, select_share_basis, evaluate_capacity, evaluate_supply,
  project_funding) and the single reader app/capital_structure.py are frozen
  as INTERFACE_OWNERSHIP under owner capital-structure-intelligence. Property
  names that would smuggle a score, probability, rank, sizing, entry, runway,
  overhang or fully-diluted figure into the state are rejected by both the
  module and the schema (prophet_authority remains the one allowed prophet_*
  key, and it stays false).
rationale: >
  The 2026-08-18 ontology (DEC:CS-V2-SIX-QUESTION-ONTOLOGY) fixed the six
  questions; nothing since has fixed the types that answer them, so the
  original waves reasoned about capacity, supply and funding in prose and the
  reader still lists eight unavailable capabilities. The masterplan's §5 joint
  financing-constraint model, §8 share selector and §9 interfaces are only
  enforceable if the quantities they exchange are typed with unit, basis,
  status and evidence, and if an unknown can never collapse to a number.
  Freezing the contract first lets T0, I0, B0/B1, F0/F1 and the §13 graph be
  built by separate owners against one schema instead of inventing six, and
  lets the single reader stay a reader. Compatibility is pinned to the live
  projection constants by import so a rename there fails this contract
  instead of silently de-linking the observed-event path.
alternatives:
  - option: Extend capital_structure.projection_bundle.v1 in place with state, scenario and capacity fields
    why_not: The projection bundle is a shipped observed-event artifact with a
      frozen schema name and eight honest unavailable labels; mixing scenario
      results into it would make a filing projection carry scenario-bound
      numbers and would break every current reader of v1.
  - option: Freeze the §9 interfaces as prose only and let each wave define its own dataclasses
    why_not: Six owners would mint six incompatible share-basis and quantity
      shapes; the summing and unknown-as-zero failures the masterplan forbids
      (A20, A21) can only be refused by a shared type.
  - option: One flat capital-state record with a single share count and a single remaining-capacity number
    why_not: REJECTED_BY_DESIGN. It is the competitor failure mode; share basis
      must be selected and named, capacity is per route under named
      constraints, and an unknown must stay unknown.
  - option: Enforce the forbidden-property law by review only
    why_not: A regex in the module plus a propertyNames pattern in the schema
      costs nothing and catches the drift a reviewer tired of reading a
      1,000-line record will miss.
evidence:
  - "research/capital_structure/e2e_20261013/MASTERPLAN.md §4 §5 §8 §9 §13 task C0 and §15 rows A05 A06 A20 A21 A31 A32 A48"
  - "engine/capital_structure/issuer_state_contracts.py INTERFACE_OWNERSHIP, PROJECTION_COMPATIBILITY, RECORD_SCHEMAS, STATE_FAMILIES"
  - "contracts/capital_structure_state.v2.schema.json root consts, 92 $defs, safe_property_name"
  - "tests/test_capital_structure_issuer_state_contracts.py with tests/test_capital_structure_contracts.py and tests/test_capital_structure_projection.py: 124 passed (local, /opt/homebrew/bin/python3.12)"
  - "DEC:CS-V2-SIX-QUESTION-ONTOLOGY"
affects:
  - "WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2"
  - "capital-structure-intelligence"
  - "engine/capital_structure/"
  - "contracts/"
  - "app/capital_structure.py"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-13
review_by: 2026-11-13
---

Decided by the Fable Meta-CEO seat holding the Capital Structure Intelligence
V2 end-to-end commission (masterplan at commit 93c82c9058ee). The contract is
a freeze of types, provenance and interface shape, not a product claim: no
state has been compiled against it yet, every family may still be bound as
unavailable or not_built, and the reader continues to serve the verified
event projection. Later waves implement the six §9 functions behind these
signatures; a wave that needs a new quantity kind, basis, route kind or record
field adds it through a superseding decision and a contract-version bump,
never by relaxing a validator. Release 33-11418 is bound as proposed_reform
and is never enforceable under this contract.
