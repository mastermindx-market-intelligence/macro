---
key: CS-V2-JOINT-CAPACITY-C2
question: >
  Masterplan task C2 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §5 lines 80-100, §13 row C2, §16 review class 1, acceptance rows A15, A20,
  A21 and A22) must turn the C1 capacity adapter into the joint
  financing-constraint answer: per-route bounds, one joint witness, binding
  constraints, blockers, unknowns and a receipt, under actions the scenario
  asserts, routes that exclude each other, a price that moves along a path
  and an at-the-market programme that has already sold part of its
  reservation. How are those four inputs applied so that the answer stays
  exact, never adds route maxima, never double-deducts a use, never reads an
  unknown as zero or infinity, and never turns an optimizer maximum into
  intent?
answer: >
  C2 extends the C1 adapter (engine/capital_structure/capacity.py) and
  leaves the kernel (capacity_joint.py) and the contracts untouched. (1)
  Asserted actions: an ActionSelection with a quantity is a fixed cash use of
  its own route; its gross dollars are subtracted from the route limit and,
  times each coefficient, from every pool the route consumes, and the kernel
  solves only the residual. The aggregate is fixed plus residual, the witness
  is fixed plus residual allocation, and RouteBound limits stay the full
  limits. A residual below zero is contradicted with a named blocker, or
  unknown when only one price branch fails. An action without a quantity is
  recorded only. (2) Exclusive routes come from the declared assumption
  route_exclusivity and reach both the kernel and the envelope; a fixed member
  removes the others from the residual. (3) Path prices: the price in effect
  on a date is the latest path point on or before it. A takedown is priced at
  the horizon start; an at-the-market route is priced at the lowest and the
  highest price in effect within the horizon, giving a pessimistic and an
  optimistic solve. The NASDAQ 20 percent pool is known in shares on both
  branches; only the per-route dollar-to-share coefficient branches. The
  aggregate is known only when both branches agree; otherwise it is unknown
  with the pessimistic floor and the optimistic ceiling, and the missing fact
  is named as the programme's dated sale schedule. (4) Programme usage: the
  dollars already sold under a reservation reduce the at-the-market limit and
  the registered pool once and never the takedown; unresolved usage is a named
  Unknown, solved as fully used in the pessimistic branch and unused in the
  optimistic branch. (5) Review rulings (opus review of head 73c05f6a, findings
  F1-F5): the aggregate is known only when every asserted action fits in every
  branch, the branches agree, every active route limit is a known dollar amount
  and every dollar pool shared by two or more routes has a known bound;
  otherwise it is unknown with a floor and ceiling, or contradicted when the
  actions fit in no branch. The witness is empty whenever an asserted action
  fails on any branch, because no allocation honours the commitment in every
  branch. A one-branch failure is labelled
  asserted_actions_infeasible_on_price_branch only when the price path is the
  sole branch reason, and asserted_actions_infeasible_on_branch otherwise. A
  non-positive price anywhere in the path is rejected as an input error rather
  than skipped (F5, kept strict). A floor is a guarantee, so the unknown
  aggregate's floor is stated as unstated when the pessimistic branch cannot
  carry the asserted actions (review R1). The masterplan's single C2 task is split into C2a
  (this record: the joint answer above), C2b (actions that are not capacity
  routes, read from I1 instrument terms; adapter identity c2_adapter.v2),
  C2x (programme and shelf usage read from the X0 transaction ledger as a
  fact, a floor or a contradiction, with no identity bump) and C2c (the
  authorized-unreserved share pool). The split supersedes nothing accepted;
  it only orders C2 so that each part lands on a merged dependency.
  (6) C2c-A (SPEC_C2C_A): the authorized-unreserved common-share headroom
  that C2c-P selects at its instant becomes one more stock pool
  (authorized_unreserved, kind reserved_authorized_shares). Share-issuing
  routes draw on it at a coefficient of one over the horizon-start price, with
  per-route coefficients under path pricing exactly as for the Nasdaq 20
  percent pool. A known headroom binds in shares; a shortfall is a zero bound
  with a condition; a ceiling-only answer (reserved count not reported) feeds
  the ceiling solve only; an unknown, contradicted or invalid answer is an
  unknown pool or a named blocker, never zero. With no price in effect at the
  horizon start the pool is unknown and no ceiling is offered. A split
  recorded after the headroom instant turns the headroom unknown; it is never
  rescaled. With no authorized-capital records the output is byte-identical
  to C2b.
rationale: >
  The masterplan's worked example (L92-94) is a joint answer: an 8 and a 7
  million dollar route sharing a 10 million dollar pool give 10 million with
  the witness 8 plus 2, or 6 million when only 3 million shares can be
  issued, and an unknown share count gives no number at all. Fixing an
  asserted use before solving keeps that example true when the scenario
  commits part of a route, without letting the commitment look like a cap.
  Pricing a takedown at one dated price and a programme across the window's
  low and high is the only reading that uses no price after the horizon and
  invents no sale schedule. Because every bound is non-decreasing in price,
  the low branch is a true floor and the high branch a true ceiling, so the
  pair brackets every schedule the path allows. Treating usage as a flow
  deducted once in the pool and the programme's own route, never in the
  takedown, is exactly A15. Keeping the kernel and contracts fixed means C1's
  accepted digests for fixed-price scenarios without actions stay
  byte-identical.
alternatives:
  - option: Add the route maxima, or report the larger of the per-route maxima, as the aggregate
    why_not: Routes share pools, so their maxima are not additive (A21) and
      the largest single route ignores what the others can still use.
  - option: Price every route at one path price (the first, the last or an average)
    why_not: The first or last picks one schedule without evidence, the last
      can read a price after the sale, and an average is a probability the
      scenario does not state.
  - option: Enumerate sale dates and solve every schedule
    why_not: Exponential in path length and still a guess at timing. The
      low/high bracket already contains every schedule, because each bound is
      monotone in price.
  - option: Shrink a route's reported limit by an asserted action
    why_not: A committed use is not a cap. The limit is a fact about the
      route; the commitment belongs in the witness and the remaining capacity.
  - option: Treat unresolved programme usage as zero
    why_not: Unknown is never zero (A20). It would overstate the
      at-the-market capacity by whatever the programme has already sold.
  - option: Deduct programme usage from the takedown too
    why_not: The usage already reduces the shared pool. Deducting it from
      the takedown as well double-counts it (A15).
  - option: Report a known aggregate when both branch optima agree even though an asserted action fails on one branch
    why_not: The number would rest on a commitment the issuer cannot honour
      in that branch, so it is not a fact about the scenario (review F1).
  - option: Report the witness of the branch where the actions fit
    why_not: That witness includes an action the other branch cannot carry,
      so it would present an infeasible allocation as a feasible one.
  - option: Skip a non-positive path price instead of rejecting it
    why_not: A zero or negative price is a broken input, and skipping it
      silently changes the window's low price and so the floor (review F5).
  - option: Change the kernel to branch internally
    why_not: The kernel is accepted, exact and price-free. Branching on
      evidence is an adapter concern, and two calls keep each solve
      reproducible from its recorded input.
evidence:
  - research/capital_structure/e2e_20261013/MASTERPLAN.md lines 80-100, 233, 258 and §15 rows A15, A20, A21, A22, A48 (PR #9115 @93c82c90)
  - engine/capital_structure/capacity_joint.py solve_joint and JointSolution (C1 kernel af5cf079)
  - engine/capital_structure/capacity.py C1 adapter (PR #9374) _nasdaq_pool, _registered_pools, _aggregate, _witness
  - engine/capital_structure/issuer_state_contracts.py ActionSelection, FinancingScenario, PriceAssumption, CapacityEnvelope._check_aggregate and _check_witness
  - SPEC_C2 §4 fixtures, computed exactly with Fraction on 2026-10-14 (A21 10,000,000 / 6,000,000 / unknown; path bracket 6,000,000.00 to 6,666,666.66)
  - Opus review of head 73c05f6a (findings F1-F5) and the five test_review_* regression tests in tests/test_capital_structure_capacity_c2.py (fix commit bea60cb4)
  - Opus re-review of bea60cb4 (PASS, one minor finding R1 on the floor of an infeasible pessimistic branch, closed by the follow-up fix commit)
  - SPEC_C2C_A §0 items 1-13 and tests/test_capital_structure_capacity_c2c_a.py (lane commits cec2edaa and 1e8d37ef; known-headroom worked example 2,000,000 authorized, 1,000,000 issued, 500,000 reserved at $2.00 binds at 1,000,000.00 USD)
affects:
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - engine/capital_structure/capacity.py
  - tests/test_capital_structure_capacity.py
  - tests/test_capital_structure_capacity_c2.py
  - tests/test_capital_structure_capacity_c2c_a.py
  - masterplan tasks C2b, C2c and S0 (consume the joint envelope; never re-derive it)
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
---

# Joint capacity applies what the scenario asserts and brackets what it does not know (C2)

The capacity answer now takes the scenario's committed uses, mutually
exclusive routes, moving prices and an at-the-market programme's past sales
into account. Committed uses are fixed first and only what remains is
optimised. When the price moves, the answer is given as a range from the
lowest to the highest price in the window, and it names the missing fact, the
programme's dated sale schedule, instead of guessing one. Past programme sales
are counted once. Unknown inputs stay named unknowns, and the result is a
capacity in gross dollars, never a recommendation or a size.
