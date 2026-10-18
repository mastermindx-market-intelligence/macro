---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-c2a-joint-seat
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task C2, first part C2a (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §5 lines 80-100, §13 row C2, acceptance rows A15, A20, A21 and A22; depends
  on C1): make the C1 capacity adapter give the joint financing-constraint
  answer under asserted actions, exclusive routes, a dated price path and an
  at-the-market programme that has already sold part of its reservation,
  without summing route maxima, double-deducting a use, or reading an unknown
  as zero or infinity.
state_before: >
  C1 (#9374) merged as 8f00ee9a and landed; main ci.yml baseline 38620348302
  concluded success at 8f00ee9a. The adapter answered fixed-price scenarios
  only; ActionSelection, route_exclusivity and PriceAssumption paths were
  carried in the C0 contracts but ignored by capacity. I1a (#9388, instrument
  economic terms) was in CI, so C2a reads no I1 terms; non-capacity actions are
  C2b scope.
changed:
  - path: engine/capital_structure/capacity.py
    what: >
      Adapter identity capital_structure.capacity.c2_adapter.v1 (kernel
      unchanged). Asserted actions with a quantity are fixed uses: their gross
      dollars leave the route limit and every pool the route consumes, the
      kernel solves only the residual, and the aggregate and witness are fixed
      plus residual; RouteBound limits stay the full limits; a negative
      residual is contradicted with a named blocker. Exclusive routes come from
      the route_exclusivity assumption and reach both the kernel and the
      envelope. Path prices: a takedown is priced at the latest point on or
      before the horizon start; an at-the-market route is solved at the lowest
      and highest price in effect inside the horizon, and the aggregate is
      known only when both branches agree, otherwise unknown with the floor,
      the ceiling and the named missing fact (the programme's dated sale
      schedule). Programme usage reduces the at-the-market limit and the
      registered pool once, never the takedown; unresolved usage is a named
      Unknown solved as fully used (floor) and unused (ceiling). After the opus
      review (F1-F5) the aggregate is known only when every asserted action fits
      every branch, the branches agree, and every active route limit and shared
      dollar pool bound is known; the witness is empty when an action fails on
      any branch; a usage-only branch failure is no longer labelled a price one.
  - path: tests/test_capital_structure_capacity_c2.py
    what: >
      39 tests: 34 from SPEC_C2 §5 plus five test_review_* regressions for review findings F1-F4 and the empty-witness rule; the A21 worked example (10,000,000 with witness
      8,000,000 + 2,000,000; 6,000,000 under a 3,000,000-share pool; unknown
      share count gives no number), path bracket 6,000,000.00 to 6,666,666.66,
      programme usage (R 20M, U 3M, C 1M, S 2M, float 300M) deducted once,
      fixed actions, contradictions, exclusive groups, and unknown-is-never-zero.
  - path: tests/test_capital_structure_capacity.py
    what: >
      Re-pinned the adapter identity to c2_adapter.v1, resolved programme
      usage to 0 in the A15 reservation case (usage is now an input C2a reads),
      and removed the C1 test that expected price-path branching to be
      deferred; its four successors are the path fixtures in the C2 suite.
      Fixed-price answers without actions are otherwise unchanged.
  - path: .github/ci/legacy-jobs.yml
    what: Registers tests/test_capital_structure_capacity_c2.py in the capital-structure-intelligence job (CI-authority edit).
  - path: agentos/decisions/DEC-CS-V2-JOINT-CAPACITY-C2.md
    what: Records the four input rules, the C2a/C2b/C2x/C2c split and the rejected alternatives.
verified:
  - claim: The C2a suite and the neighbouring capital-structure suites pass on the C1 merge plus the lane patch.
    command: PYTHONPATH=. /opt/homebrew/bin/python3.12 -m pytest -q -p no:cacheprovider tests/test_capital_structure_capacity_c2.py tests/test_capital_structure_capacity.py tests/test_capital_structure_capacity_joint.py tests/test_capital_structure_registration_integration.py tests/test_capital_structure_rule_applicability.py tests/test_capital_structure_share_basis.py tests/test_capital_structure_funding.py tests/test_capital_structure_issuer_state_contracts.py tests/test_capital_structure_instrument_economics.py tests/test_capital_structure_supply_scenarios.py
    result: 598 passed (2026-10-14, head 0693a0df rebased onto the I1a merge e32d4109; 431 passed earlier on 8472d9cd over the first eight files on base 8f00ee9a).
  - claim: The kernel and the contracts are untouched.
    command: git diff --stat 8f00ee9a..HEAD -- engine/capital_structure/capacity_joint.py engine/capital_structure/issuer_state_contracts.py
    result: empty (2026-10-14).
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X and merge-queue-pilot excluded).
  - claim: C2a is merged and landed on origin/main.
    what_would_verify: Squash-merge on concluded green with --match-head-commit, a bare git fetch and a per-path blob comparison against origin/main.
  - claim: A joint capacity answer reaches the published state and the product page.
    what_would_verify: The first natural nightly generation after C2 and S0 land; the natural chain is dark until the runner-listener fuse clears.
unresolved:
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
  - >
    C2b (non-capacity actions from I1 instrument terms, adapter identity
    c2_adapter.v2), C2x (programme and shelf usage from the X0 transaction
    ledger) and C2c (authorized-unreserved share pool) remain; packets are
    staged in the seat scratchpad and launch on their merged dependencies.
  - >
    The natural chain is dark; never dispatch daily.yml.
next_actions:
  - Merge C2a by hand with --match-head-commit on concluded green after checking reviewDecision; verify landing by blob comparison, then one main ci.yml baseline after the in-flight preflight.
  - Launch C2b on the C2a merge; launch C2x once C2a and X0a are both merged.
do_not_redo:
  - Price an at-the-market route at a single path point, or at an average; the low/high bracket is the answer.
  - Deduct programme usage from the takedown route as well as the shared pool.
  - Shrink a route's reported limit by an asserted action; the action is a fixed use in the witness.
  - Treat unresolved programme usage as zero.
  - Branch on evidence inside capacity_joint.py; branching is an adapter concern.
  - Report a known aggregate or a witness when an asserted action fails on any branch (review F1 and the empty-witness rule).
  - State a numeric floor when the pessimistic branch cannot carry the asserted actions; the floor is unstated (review R1).
danger_areas:
  - The bracket is a true floor and ceiling only because every bound is non-decreasing in price; a pool whose coefficient falls as price rises would break that and must be re-derived before it is added.
  - A fixed action is subtracted before the kernel runs, so the kernel's witness covers only the residual; anything reading kernel output directly must add the fixed uses back.
  - The NASDAQ 20 percent pool is held in shares on both branches; only the dollar-to-share coefficient branches. Converting the pool to dollars at one price reintroduces the single-price error.
prs: [9393]
decisions:
  - DEC:CS-V2-JOINT-CAPACITY-C2
---

# Capital Structure V2 — C2a joint capacity handoff

The capacity adapter now applies what a scenario asserts and brackets what it
does not know. It fixes committed uses first and solves the remainder jointly.
Exclusive routes are branches, and a moving price gives a floor and a ceiling
with the missing sale schedule named. Past programme sales are counted once.
The kernel and the contracts are unchanged. Ship state at write time: branch
committed, PR to be opened ready but NOT armed (CI-authority edit). Next is a
hand merge with --match-head-commit on concluded green, then one main
baseline owed to the seat.
