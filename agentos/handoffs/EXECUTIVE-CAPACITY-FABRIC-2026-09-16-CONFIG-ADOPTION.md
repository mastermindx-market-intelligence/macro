---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/vps-config-adoption-20260916-sol
model: sol
ended_because: blocked
mission: >
  Make installed versus loaded AI configuration observable through the existing
  administrative response, preserving one loader and all native credential owners.
state_before: >
  The existing GitHub config publication path transports source, but lib.config
  caches it for a process lifetime; no source-snapshot adoption observation existed.
changed:
  - path: lib/config.py
    what: Retain loaded-byte identity in the existing cache and expose a bounded observer.
  - path: admin/ai_cost.py
    what: Add the observation to the existing /api/cost response without diagnostic imports.
  - path: tests/test_config_adoption.py
    what: Real loader, HTTP, auth, error, race, cache compatibility and privacy tests.
  - path: .github/ci/legacy-jobs.yml
    what: Add only this feature suite to the existing code-gated unrun-brain-desks job.
  - path: docs/ops/AI_CONFIGURATION_ADOPTION.md
    what: Existing-owner distribution, adoption and credential-custody contract.
verified:
  - claim: The missing readback was reproduced before implementation.
    command: python3 -m pytest tests/test_config_adoption.py -q
    result: Initial 7 failed and 1 legacy control passed; later feature suite has 25 tests.
  - claim: Existing configuration, provider and Brief behavior passes the bounded regression.
    command: >
      MM_DATA_GUARD=1 python3 -m pytest tests/test_config_adoption.py
      tests/test_admin_config_store.py tests/test_admin_health.py tests/test_admin_flags.py
      tests/test_ai_costs.py tests/test_llm_auth.py tests/test_codex_provider.py
      tests/test_key_pool.py tests/test_ollama_provider.py tests/test_provider_health.py
      tests/test_provider_capacity.py tests/test_master_brain.py
      tests/test_master_brain_ladder.py tests/test_master_brain_zh_ladder.py
      -q --tb=short --basetemp OUTSIDE_REPOSITORY_TEMP
    result: >
      341 passed in 8.54 seconds. AI_COSTS_STATE_ROOT and PROVIDER_HEALTH_PATH
      were isolated outside the repository; no tracked data or real provider touched.
  - claim: A real existing HTTP route consumes the new readback and retains its auth boundary.
    command: >
      test_existing_http_response_reports_stale_loaded_source;
      test_existing_http_auth_blocks_the_adoption_observer
    result: >
      Actual loopback Handler GET /api/cost returns SOURCE_CHANGED after a synthetic
      file update; auth-required request returns 401 before the observer executes.
unverified:
  - claim: These bytes are deployed or other VPS/worker processes adopted any change.
    what_would_verify: >
      Independent source review, normal release checks and an approved real target
      process readback before/after its existing lifecycle's adoption operation.
  - claim: The observations establish credentials, effective models or capacity readiness.
    what_would_verify: >
      Separate existing Provider Control, runtime and Capacity owner evidence;
      those facts are explicitly outside this diagnostic contract.
unresolved:
  - This observes one loader snapshot, not retained references, every process or effective model selection.
  - The main source differs from installed H0 proof; future adoption requires existing-owner qualification.
  - Native account enrollment, service admission and atomic shared quota claims remain existing-owner work.
next_actions:
  - Publish this independent same-writer candidate for bounded non-author review of loader and HTTP behavior.
  - Preserve installed source and credentials until the owning release path approves a target-process proof.
  - Compose the observation with real consumer receipts without treating matching hashes as execution authority.
do_not_redo:
  - Do not recover, tune, poll or cancel CI runners; the Chairman assigned that work to another session.
  - Do not repair the blocked W1 SDK edit through this independent branch, another worker or alternate carrier.
  - Do not copy native credentials, add another router/cache/queue, or infer retired account identities.
  - Do not update installed H0 material artifacts or repeat its completed source transfer from this receipt.
danger_areas:
  - An admin-process observation cannot attest a separate VPS API, scheduled process or native worker.
  - Hash equality is exact source-byte equality only; runtime dictionary overrides are deliberately excluded.
  - Read-only response caches preserve their original observation time; they do not make observations fresh.
  - Initial fault injection patched global os.open through teardown; scoped context fixed the test, not production.
decisions:
  - DEC:EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT
---

## Retained scope and responsibility

Direct implementation: LOWER_TOTAL_OVERHEAD on the independent source-observation
boundary. No provider execution or Executive lifecycle was admitted. Existing
Fable principal, W0/W1 writers, PF1, Family-B and H0/W1-H3 custody remain unchanged.
