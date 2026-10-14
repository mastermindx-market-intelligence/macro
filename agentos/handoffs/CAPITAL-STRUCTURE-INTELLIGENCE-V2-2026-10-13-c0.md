---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-c0-state-contracts
model: fable
ended_because: ci_handoff
mission: >
  Masterplan task C0 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13, wave W0): freeze the same-owner state and scenario types, per-family
  provenance, projection compatibility and §9 interface ownership as one typed
  module plus one JSON Schema, with tests that pin the §15 acceptance rows
  A05, A06, A20, A21, A31, A32 and A48, registered in the capital-structure CI
  pack, and ship it through the ordinary chain.
state_before: >
  R1 was CLOSED by the masterplan. R2 (byte-exact source-ledger sharding) was
  built and open as PR #9146 on claude/cs-v2-r2-ledger-sharding at head
  c443fa8fde62. No V2 state, scenario, capacity, supply or funding type
  existed; the reader app/capital_structure.py served the verified
  capital_structure.projection_bundle.v1 generation with eight unavailable
  capabilities. Fabric lane hosts were ineligible on disk, so the seat executed
  C0 directly under the continuation law.
changed:
  - path: engine/capital_structure/issuer_state_contracts.py
    what: >
      New frozen contract module (capital-structure-state-contracts/2.0.0):
      typed quantities with unit/basis/status/evidence/applicability,
      GenerationBinding and FamilyProvenance, StateRequest, CapitalInputs bound
      to generation schemas, RulePack with rule classes, FinancingScenario with
      assumption-digest identity, CapacityEnvelope with routes, shared pools,
      aggregate and witness checks, SupplyEnvelope with four named bases,
      FundingSchedule with dated and conditional flows, InstrumentSet,
      ShareBasisResult, CalculationReceipt, projection_compatibility, the §9
      INTERFACE_OWNERSHIP table and the forbidden-property law.
  - path: contracts/capital_structure_state.v2.schema.json
    what: >
      Draft 2020-12 schema for capital_structure.state.v2 and every record kind,
      with enum defs pinned to the module tuples, unknown-never-numeric
      quantity shapes and a safe_property_name pattern.
  - path: tests/test_capital_structure_issuer_state_contracts.py
    what: >
      Schema round-trips per record kind, enum pins, compatibility and
      capability-proof law, unknown never 0 or infinity, basis law, scenario
      identity, shared-pool and route-sum aggregate bounds, witness bounds,
      evidence law, rule classes, forbidden keys at every level, receipts,
      input bindings, interface ownership, frozen dataclasses.
  - path: .github/ci/legacy-jobs.yml
    what: Register the new suite in the capital-structure contracts step.
  - path: agentos/decisions/DEC-CS-V2-STATE-CONTRACTS-FROZEN-V2.md
    what: Record what C0 froze and what a later wave may not change.
verified:
  - claim: The frozen module, schema and new suite pass together with the two existing capital-structure suites.
    command: >
      /opt/homebrew/bin/python3.12 -m pytest
      tests/test_capital_structure_issuer_state_contracts.py
      tests/test_capital_structure_contracts.py
      tests/test_capital_structure_projection.py -q
    result: 124 passed in 6.04s.
  - claim: The new suite is registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0.
  - claim: All twelve legacy packs still validate after the registration edit.
    command: >
      python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml
      --pack-index N --pack-count 12 --validate-only, N = 0..11
    result: rc=0 for every pack.
  - claim: The Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: exit 0 with the decision and this handoff present.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head apart from the inherited ci-pack-0 red.
    what_would_verify: >
      The ci.yml run for the pushed head concluding with every pack green once
      main's ci-pack-0 heal (PR #9141) lands and a main proof postdates it.
  - claim: C0 is merged and landed on origin/main.
    what_would_verify: >
      Squash-merge on concluded green, then a bare git fetch and a per-path
      blob comparison of the five changed paths against origin/main.
  - claim: A runtime consumer compiles a CapitalState against this contract.
    what_would_verify: >
      T0/I0/B0 producing a state record that validates against
      contracts/capital_structure_state.v2.schema.json and is read by
      app/capital_structure.py without a second calculation path.
unresolved:
  - >
    main is red on ci-pack-0 (tests/test_ci_pack.py
    test_exclusive_curation_narrows_ordinary_code_prs, probe weights 5813>5800
    and 5618>5600). The heal lane is PR #9141 (draft, checks concluded green).
    Both R2 #9146 and this C0 edit .github/ci/legacy-jobs.yml, so the sweeper's
    live-inherited-red path is ineligible for them; they clear through the
    update-branch path after main is proven green, or by hand-merge on a green
    rerun.
  - >
    The workstream record (decisions and handoffs lists, next_action) is not
    patched in this PR to avoid a conflict with #9146's edit of the same
    region; a records PR after both merge owes it, together with correcting
    the stale line in the 2026-10-13-r2 handoff that says the Company Facts
    head-witness test fails locally (98 passed locally).
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml baseline
    is owed after merge, dispatched only over a clear field.
  - >
    Fabric lane hosts: only mb was eligible at 13:2xZ; the Opus domain
    suborchestrators O1-O6 are not yet spawned.
next_actions:
  - Merge C0 by hand with --match-head-commit on concluded green after the ci-pack-0 heal lands; verify landing against origin/main by blob comparison.
  - Preflight for an in-flight main baseline, then dispatch ONE ci.yml run on main to prove the merged CI authority.
  - Open the records PR (workstream record refresh plus the r2 handoff correction) once #9146 and C0 are both on main.
  - Start E0 (qualify reference documents, source policy, rights, identities, gold cases), then T0 (deps E0, C0), then I0/B0/B1/F0/F1 per §13.
  - Spawn the Opus domain suborchestrators when host_pick admits hosts; use mb for one separable lane meanwhile.
do_not_redo:
  - Re-freeze, rename or re-version STATE_CONTRACT_VERSION, RECORD_SCHEMAS or INTERFACE_OWNERSHIP without a superseding decision.
  - Rename or break capital_structure.projection_bundle.v1 or its AUTHORITY; compatibility is checked against those constants by import.
  - Remove a label from a state's unavailable list without a matching capabilities_proven entry.
  - Add a score, probability, rank, sizing, entry, runway, overhang or fully_diluted property anywhere in a state record.
  - Encode Release 33-11418 as an enforceable rule; it is proposed_reform.
  - Dispatch daily.yml to manufacture proof, lift the #8673 UI hold by inference, or heal ci-pack-0 inside a capital-structure PR (the heal lane is #9141).
  - Assert literal equality between FORBIDDEN_PROPERTY_PATTERN and the schema safe_property_name pattern; the schema carves out prophet_authority.
danger_areas:
  - CapitalInputs.bindings is a tuple of GenerationBinding, not a mapping; every record is checked against its family binding's schema and support level.
  - CalculationReceipt.input_digest hashes the full inputs.as_record() (schema and input_digest included), not inputs.input_digest.
  - FinancingScenario.scenario_id excludes label; other_assumptions keys must be unique; fee and discount rates are decimals at most 1.
  - The capital-structure pack step gained one suite; the Capital Structure job runtime warning is unchanged but pack weights move on any job edit.
  - Sparse worktree: never git add -A; a write into an omitted tree truncates the committed artifact.
decisions:
  - DEC:CS-V2-STATE-CONTRACTS-FROZEN-V2
prs: [9159]
---

C0 is a freeze, not a product. No state has been compiled against the
contract yet, and the reader keeps serving the verified event projection. The
seat holding the end-to-end commission continues with E0 and T0 in the same
session; this handoff exists so a cold successor can resume at the merge step
without re-deriving the contract.
