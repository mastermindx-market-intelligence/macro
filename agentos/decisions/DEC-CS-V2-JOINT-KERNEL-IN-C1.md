---
key: CS-V2-JOINT-KERNEL-IN-C1
question: >
  Masterplan §5 (research/capital_structure/e2e_20261013/MASTERPLAN.md) makes
  the joint financing-constraint model the seat's hard architectural
  responsibility: several financing routes (shelf takedowns, an ATM program,
  later warrants and conversions) draw on shared pools (registered amount,
  baby-shelf headroom, the Nasdaq 20% share budget), so per-route maxima must
  never be summed. Task C1 (deps L0, B1) needs remaining-capacity answers now,
  and C2 adds instrument routes and exclusive groups later. Where does the
  optimisation live, and how does it answer when an input is unknown?
answer: >
  One exact kernel, engine/capital_structure/capacity_joint.py
  (IMPLEMENTATION capital_structure.capacity_joint.lexicographic_simplex.v1),
  owns every joint answer. Routes are nonnegative use variables with an
  optional limit; shared pools are rows sum(coefficient x use) <= bound with
  positive coefficients; mutually exclusive groups are enumerated as branches
  (at most 4096), never relaxed. solve_joint maximises total use in exact
  Fraction arithmetic (floats are refused) and returns the optimum, a
  canonical witness (lexicographic maximum of total use, then of each route in
  the stated preference order, so input order never changes it), and which
  pools bind (removing the pool strictly raises the optimum) or are slack.
  When any relevant limit or bound is unknown it returns no optimum: only the
  floor with every unknown at zero (with a witness feasible for every
  nonnegative value of the unknowns) and the ceiling with every unknown relaxed
  (None when nothing else bounds it). engine/capital_structure/capacity.py is a
  thin adapter: it reads the issuer state, builds routes and pools, calls the
  kernel twice (evidence, then a ceiling with stated substitutes), floors
  dollar answers to cents and emits a C0 CapacityEnvelope. The aggregate is
  gross dollar capacity and never proceeds; the ceiling is reported only in
  the note and inputs, never as the aggregate.
rationale: >
  The failure this prevents is the additive answer: an ATM at 8M plus a
  takedown at 7M against a 10M registered pool is 10M, not 15M, and the
  witness must show a feasible split (8M + 2M). A per-route adapter that sums
  limits, or a float solver that rounds a binding pool open, would overstate
  what the issuer can raise. Keeping the optimisation in one exact,
  order-invariant kernel with a vertex-enumeration oracle in its tests means
  C1, C2 and G0 cannot each grow their own arithmetic. Returning a bracket
  instead of a number when an input is unknown keeps A20 (unknown is never 0
  or infinity), and the floor witness is a lower bound that holds whatever the
  unknown turns out to be.
alternatives:
  - option: Sum each route's own maximum
    why_not: Double-counts shared pools; A21 forbids it.
  - option: A floating-point LP solver (scipy/linprog)
    why_not: Rounding can open a binding pool and the witness depends on
      solver internals and input order; adds a heavy dependency to the
      nightly path.
  - option: Mixed-integer programming for exclusive groups
    why_not: Branch enumeration is exact and bounded at the sizes an issuer
      has; MIP adds a solver and tolerances for no gain.
  - option: Treat an unknown limit or bound as zero or as unbounded
    why_not: A20; both are guessed facts. The kernel returns a floor/ceiling
      bracket and names the unknowns instead.
  - option: Let the fabric lane write capacity.py and the kernel together
    why_not: The kernel is the seat's architectural responsibility; the lane
      builds the evidence adapter against a frozen spec (SPEC_C1) and imports
      the kernel.
evidence:
  - engine/capital_structure/capacity_joint.py (solve_joint, JointRoute, JointPool, JointSolution.as_record, exact, decimal_floor)
  - tests/test_capital_structure_capacity_joint.py (worked 8M+7M example against a 10M pool, share-pool binding, unknown bracket, exclusive branching, preference changes witness not value, degenerate pools, float refusal, 300-case vertex-enumeration oracle, monotonicity, order and scale invariance, never-sum-shared-pool)
  - /opt/homebrew/bin/python3.12 -m pytest -q -p no:cacheprovider tests/test_capital_structure_capacity_joint.py (17 passed, 2026-10-14)
affects:
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - engine/capital_structure/capacity_joint.py
  - engine/capital_structure/capacity.py
  - masterplan tasks C1, C2 and G0 (import the kernel; never re-implement optimisation)
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
---

# One exact joint kernel for financing capacity (C1)

Shared pools are solved jointly, exactly and order-invariantly in one kernel.
An unknown input produces a floor/ceiling bracket with named unknowns, never a
number. The capacity adapter only translates evidence into routes and pools
and the kernel's answer into a CapacityEnvelope.
