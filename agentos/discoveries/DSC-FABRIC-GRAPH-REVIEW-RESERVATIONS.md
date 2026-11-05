---
key: FABRIC-GRAPH-REVIEW-RESERVATIONS
claim: >
  At Mastermind source adf612f8041f12597ec732f8898c06c8adcddf59, a COO plan with two
  independently reviewed work steps reserves 19 cumulative descendants against a limit of 16,
  so adding sequential dependency edges alone cannot make that plan admissible.
falsifier: >
  Inspect control_plane/executive_coo_policy.py at that exact commit and run
  tests/test_fabric_graph_planning.py::test_review_reservation_is_cumulative_even_in_a_pipeline
  from Mastermind PR #1910; a different canonical reservation or a permitted total of 19
  at the named source disproves the claim.
so_what: >
  Reserve required review, repair and integration before widening builders. Use the incumbent
  validator-backed graph advisor to inspect prospective demand, preserve required review and
  original-root budgets, and distinguish numeric slot shortage from hierarchy/depth incompatibility.
  Do not treat serialization, a replacement root or a cheaper model as a repair for cumulative demand.
kind: constraint
verified_at: 2026-11-01
verified_by: >
  Mastermind PR #1910, source 805a5a77a992b89fd06b9e52a474aa29efaf11e1;
  python -m pytest -q tests/test_fabric_graph_planning.py tests/test_agent_eval_resource_summary.py
  tests/test_agent_eval_store.py tests/test_fabric_graph_policy_package.py
  tests/test_provider_orchestrator_policy.py (137 passed on Python 3.12 / pytest 9.1.1).
scope:
  - mastermind
  - executive-os
  - control_plane/executive_coo_policy.py
  - control_plane/fabric_graph_planning.py
confidence: verified
---

# Reserve the complete review cycle before choosing fanout

The incumbent policy reserves one planner plus nine descendants for each reviewed work step:
three possible work/repair rounds, each with one work and up to two review attempts. One
reviewed step therefore demands ten; two demand nineteen. These are reservations, not
predictions of worker count, token use or dollars.

The source candidate in [Mastermind PR #1910](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1910)
adds direct, pipeline, fanout_join, hierarchical and custom composition methods, an advisory
consumer of the current ExecutionPlan validator, and honest observed EVAL resource coverage.
Its [operating guide](https://github.com/mastermindx-market-intelligence/Mastermind/blob/805a5a77a992b89fd06b9e52a474aa29efaf11e1/docs/FABRIC_GRAPH_ENGINEERING.md)
and [task tree](https://github.com/mastermindx-market-intelligence/Mastermind/blob/805a5a77a992b89fd06b9e52a474aa29efaf11e1/docs/FABRIC_GRAPH_ENGINEERING_PLAN.md)
hold implementation detail. This discovery records the cross-session constraint, not another
plan or runtime registry.

A source test pass, dependency join, technical EVAL validity or lower slot reservation is not
independent product acceptance or measured cost improvement. The candidate is BUILT_NOT_PROVEN.
It still needs non-author review, required CI, protected release, actual instruction loading,
lawful runtime admission and comparative accepted-task evidence. No default route or runtime
cap was changed.

Related organizational context remains WS:EXECUTIVE-ECOSYSTEM-COMPLETION and
WS:AGENT-EVAL-FABRIC. Existing host/canary operations retain their original owners, roots,
carriers and effect fences.
