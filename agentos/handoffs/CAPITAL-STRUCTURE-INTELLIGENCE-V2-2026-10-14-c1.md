---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-c1-capacity
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task C1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §5 and §13, acceptance rows A20 and A21; depends on L1 and B1): build the
  joint financing-constraint kernel that every capacity answer goes through,
  and an evidence-qualified adapter that turns issuer state into a C0
  CapacityEnvelope, without ever summing per-route maxima.
state_before: >
  L0 (#9314) and B1 (#9277) merged and landed; main ci.yml baseline
  38587478485 (918fad1e) concluded success. L0 exposes baby_shelf_pool and the
  rule as-of states; B1 exposes the share basis; C0 froze CapacityEnvelope.
  L1 was in flight, so C1 reads registration paths only through the frozen
  SPEC_L1 §A.3 record contract (plain capital_structure.registration_path.v1
  dicts) and never imports the L1a module. No code solved shared pools
  jointly, so the only available answer shape was a per-route maximum.
changed:
  - path: engine/capital_structure/capacity_joint.py
    what: >
      New exact kernel (IMPLEMENTATION
      capital_structure.capacity_joint.lexicographic_simplex.v1): routes with
      optional limits, shared pools as positive-coefficient rows, exclusive
      groups enumerated as branches (at most 4096), Fraction arithmetic with
      floats refused, canonical lexicographic witness, binding versus slack
      pools, and a floor/ceiling bracket with named unknowns when any relevant
      input is unknown. decimal_floor rounds dollar answers down to cents.
  - path: tests/test_capital_structure_capacity_joint.py
    what: >
      17 tests: the 8M ATM plus 7M takedown against a 10M pool answers 10M
      with witness 8M + 2M, share-pool binding, unknown bracket, exclusive
      branching, preference changes the witness not the value, degenerate
      pools, float refusal, a 300-case vertex-enumeration oracle,
      monotonicity, order and scale invariance, never-sum-shared-pool.
  - path: engine/capital_structure/capacity.py
    what: >
      Evidence adapter (fabric lane cs-v2-c1-20261014T1602Z, reviewed by the
      seat's C1 orchestrator against SPEC_C1): reads issuer state, builds
      routes and pools, calls solve_joint twice (evidence, then a ceiling with
      stated substitutes) and emits a CapacityEnvelope whose aggregate is
      gross dollar capacity, never proceeds; the ceiling appears only in the
      note and inputs.
  - path: tests/test_capital_structure_capacity.py
    what: >
      Adapter tests for the SPEC_C1 §10 cases. After merging main with L1b's
      rule pack 1.1.0, two class-4 rule-transition tests were re-pinned: on
      2026-10-14 the Rule 415(a)(5) text (last verified 2026-10-09) correctly
      adds its own requalify condition, so the test now requires every
      requalify condition to come from a beyond-window rule and none from the
      verified Form S-3 text; the "no rule text at all" date moved from
      2007-06-01 to 2004-06-01 because Rule 415 text is in force from
      2005-12-01, and a new test pins that 2007-06-01 refuses rules compiled
      for another date.
  - path: engine/capital_structure/registration_lifecycle.py
    what: >
      Latent defect fix found while merging main: the lifecycle compiler
      checked event identity with a full-body hash, which rejects every event
      written with event identity_format 2 (the W1 identity preimage). It now
      asks event_spine.compute_event_id, the owner of that format; edges keep
      the full-body check. The compiler is not wired into any production
      workflow, so the defect had no production effect.
  - path: .github/ci/legacy-jobs.yml
    what: Registers both new suites in the capital-structure-intelligence job (CI-authority edit).
  - path: agentos/decisions/DEC-CS-V2-JOINT-KERNEL-IN-C1.md
    what: Records the single exact kernel, the bracket rule for unknowns and the rejected alternatives.
  - path: agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md
    what: >
      Folds the 2026-10-13/14 decisions and handoffs into the record, adds the
      kernel do_not_redo line and rewrites next_action to the current DAG.
  - path: agentos/handoffs/
    what: >
      prs lists added to the c0, e0, t0, i0, b0, f0, b1, f1 and l0 handoffs;
      the r2 head-witness item marked resolved with its 2026-10-14 receipt.
verified:
  - claim: The joint kernel passes its suite, including the vertex-enumeration oracle.
    command: PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q -p no:cacheprovider tests/test_capital_structure_capacity_joint.py
    result: 17 passed (2026-10-14, at af5cf079).
  - claim: The Company Facts suite, including the external head-witness test the r2 handoff left unresolved, passes.
    command: PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q -p no:cacheprovider tests/test_sec_capital_structure_companyfacts.py
    result: 98 passed (2026-10-14, at af5cf079).
  - claim: C1 and the neighbouring capital-structure suites pass after merging origin/main at 7dd06ff5 (L1b).
    command: PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q -p no:cacheprovider tests/test_capital_structure_capacity.py tests/test_capital_structure_capacity_joint.py tests/test_capital_structure_rule_applicability.py tests/test_compile_capital_structure_registration_lifecycles.py tests/test_capital_structure_registration_lifecycle.py tests/test_capital_structure_issuer_state_contracts.py
    result: 267 passed (2026-10-14).
  - claim: The Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: exit 0.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: C1 is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green with --match-head-commit, a bare git fetch and a per-path blob comparison against origin/main.
  - claim: A capacity answer reaches the published state and the product page.
    what_would_verify: The first natural nightly generation after C1 and C2 land, carrying capacity envelopes; the natural chain is dark until the runner-listener fuse clears.
unresolved:
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
  - >
    Instrument routes (warrants, conversions) and exclusive groups beyond
    the shelf/ATM pair are C2 scope; the kernel already supports them.
  - >
    The natural chain is dark (no source_manifest.part-0002.jsonl on main;
    last generation 24ab0b613f89 on 2026-09-26); never dispatch daily.yml.
next_actions:
  - Merge C1 by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing by blob comparison, then one main ci.yml baseline after the in-flight preflight.
  - C2 adds instrument routes and exclusive groups through solve_joint; G0 grades the official examples through the same kernel.
do_not_redo:
  - Sum per-route capacity maxima, or solve shared pools anywhere except engine/capital_structure/capacity_joint.py.
  - Use floats or a floating-point LP solver for capacity.
  - Treat an unknown limit or pool bound as zero or as unbounded.
  - Report the ceiling, or proceeds, as the aggregate.
danger_areas:
  - C1 and L1a are coupled only by the SPEC_L1 §A.3 registration_path record shape; a field rename on either side breaks capacity silently unless the adapter tests are updated in the same PR.
  - The witness is canonical only because ties break lexicographically on total use, then on the stated route preference order; changing that order changes the witness, never the optimum.
  - Exclusive groups are enumerated, not relaxed; more than 4096 branches raises JointModelError by design.
  - decimal_floor floors to cents; rounding to nearest can overstate a binding pool.
prs: [9374]
decisions:
  - DEC:CS-V2-JOINT-KERNEL-IN-C1
---

# Capital Structure V2 — C1 joint capacity handoff

capacity_joint.py is the only place shared financing pools are solved. The
capacity adapter translates evidence into routes and pools and the kernel's
answer into a CapacityEnvelope. Ship state at write time: branch committed,
PR to be opened ready but NOT armed (CI-authority edit), then a hand merge
with --match-head-commit on concluded green, then one main baseline owed to
the seat.
