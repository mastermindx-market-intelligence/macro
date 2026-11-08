---
key: EXECUTIVE-ROUTES-ALIAS-ELIGIBILITY-IS-A-PLACEMENT-GRANT
claim: >
  In config/executive_worker_routes.json a model alias with worker_eligible true on a provider
  that is enabled and autonomous_allowed is a placement grant, not a label: the COO binding loader
  (control_plane/executive_service.py::_load_coo_execution_binding) checks adapter, surface and
  profile but never the provider alias, and the host work_placement_union is derived from the
  configured coo_model_alias. So a routes-policy entry for a new provider written "as a seam"
  with enabled/autonomous_allowed/worker_eligible true let a one-line control.json
  coo_model_alias swap mint a MiniMax placement union with no harness-binding check. Independent
  review caught this on #947 round 1; the safe shape is enabled false, autonomous_allowed false,
  worker_eligible false with the real provider model id, which the router refuses at
  resolve_model_alias and at tier load.
falsifier: >
  control_plane/executive_service.py:2028-2060 (_load_coo_execution_binding) refusing an alias
  whose provider is not the proven harness binding without a routes-policy change; or a
  worker_eligible true alias on an enabled autonomous provider that
  control_plane/model_router.py:697-709 still refuses to place (run
  `pytest tests/test_executive_model_router.py` at Mastermind #947 head 8b59fb43).
so_what: >
  Never add a provider to the routes policy as enabled/autonomous/eligible before the six E2
  gates (see DSC:EXECUTIVE-E2-MINIMAX-NEEDS-SIX-GATES-NOT-A-CONFIG-FLIP) are proven; declare it
  unarmed and non-eligible, and require an independent review of any routes-policy diff that
  flips those three fields. Treat routes policy as authority configuration under the governor,
  not as inert data.
kind: constraint
verified_at: 2026-09-24
verified_by: >
  #947 round-1 independent review (Mastermind #947 comment 5808346075) against head dc2e333d;
  control_plane/executive_service.py:2028-2060 and 2124-2127; control_plane/model_router.py:321-322
  and 697-709; repair at #947 head 8b59fb43 with tests proving the refusals
  (tests/test_executive_model_router.py).
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - config/executive_worker_routes.json
  - control_plane/executive_service.py
confidence: verified
---

# A worker-eligible alias is a placement grant

The routes policy is read by the COO binding loader without a provider check, so eligibility
flags on a new provider are authority, not documentation. Declare new provider seams unarmed
and non-eligible until their harness binding is proven, and review routes-policy flips as
authority changes.
