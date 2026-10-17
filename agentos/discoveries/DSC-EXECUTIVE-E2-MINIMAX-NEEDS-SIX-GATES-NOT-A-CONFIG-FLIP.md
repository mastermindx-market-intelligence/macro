---
key: EXECUTIVE-E2-MINIMAX-NEEDS-SIX-GATES-NOT-A-CONFIG-FLIP
claim: >
  The nearest distinct second provider for the Executive worker path is MiniMax via the
  reviewed codex-cli binding minimax-token-plan.codex-responses (transport proven for codex-cli
  0.154.0 / MiniMax-M3 / wire_api responses; binding BUILT_NOT_PROVEN, autonomous_allowed
  false). Six gates stand between it and a live worker: (G1) a minimax provider entry on adapter
  codex-cli in config/executive_worker_routes.json; (G2) a worker-eligible alias on a codex
  execution surface; (G3) a non-codex worker slot plus a readiness identity kind for an API-key
  provider (slot inventory is locked to four codex slots; the identity policy is closed-world
  over OpenAI credential kinds); (G4) a non-Codex inference canary (the existing canary is
  hard-wired to codex-01); (G5) a provider-agnostic COO binding (the loader checks adapter,
  surface and profile but not provider_alias, so this is small); (G6) the binding's
  autonomous_allowed flip, gated by activation_gates evidence (capacity_known,
  real_canary_passed, usage_policy_satisfied) and refused at runtime by
  _assert_service_activation_allowed until then. The realm is selected inside the spawned
  phase1c worker from the broker config's harness_binding_id, not by the supervisor.
falsifier: >
  A MiniMax-backed worker completing a sealed job through the same admission, claim, broker
  start, result seal and validation path with fewer than these changes; or
  scripts/executive_os_phase1c_worker.py::_assert_service_activation_allowed no longer refusing
  a BUILT_NOT_PROVEN binding; or ops/executive_os/provider_worker_slots.py accepting a
  non-codex slot id without a source change.
so_what: >
  Commission E2 as ordered bounded units, not one flip: G1+G2 are config plus tests and are
  disjoint from every E1 file; G3 is a receipt/identity-contract change that belongs to the
  readiness owner (and ops/executive_os/provider_readiness.py is held by the readiness-refresh
  child until it lands); G4 is a new module; G5 is a one-line widening once G1-G4 exist; G6 is a
  data flip that needs a live canary receipt and a capacity observation. Do not enable
  qwen/glm/xai on the openai-compatible adapter (implemented=false; refused by the router).
  A transport proof is not a governed canary.
kind: architecture
verified_at: 2026-09-24
verified_by: >
  control_plane/codex_provider_realm.py:269-298 (MINIMAX_TOKEN_PLAN in
  REVIEWED_CODEX_PROVIDER_REALMS) and :304-318 (transport-proof note, review_evidence
  artifact sha256 84771422af5ef24e12f6ec0e82a2b107763fceaca77f1c7c7915493802bee3dd);
  config/subscription_harness_bindings.v1.json:78-95; scripts/executive_os_phase1c_worker.py:212-248
  (realm resolution) and :259-264 (_assert_service_activation_allowed);
  control_plane/model_router.py:652-656 and :697-709; ops/executive_os/provider_worker_slots.py:80-172;
  ops/executive_os/provider_identity_policy.py:15-74; control_plane/executive_service.py:2045-2056;
  Mastermind PR #665 merge e878878c9; E2-PREP-1 census (MiniMax construction lane, 2026-09-24)
  consumed and spot-checked by the Fable delivery principal, recorded on Mastermind #600.
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - control_plane/codex_provider_realm.py
  - scripts/executive_os_phase1c_worker.py
  - ops/executive_os/provider_worker_slots.py
confidence: verified
---

# E2 via MiniMax needs six gates, not a config flip

MiniMax already has a reviewed transport realm and a codex-cli binding, but the binding is
`BUILT_NOT_PROVEN` with `autonomous_allowed: false`, and the worker process refuses to activate
any binding in that state. Between the transport proof and a live governed worker sit six
ordered gates (routes entry, eligible alias, non-codex slot + API-key readiness kind, a
MiniMax canary, a provider-agnostic COO binding, and the evidence-gated flip). The first two are
config and disjoint from E1; the slot/readiness gate is a contract change owned by the
readiness owner; the flip is the only step with production effect.
