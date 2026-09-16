---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/vps-aibrief-policy-adoption-stack-20260916-sol
model: sol
ended_because: blocked
mission: >
  Carry the shared workload policy through the existing AI Brief producer and
  publication path without consuming developer subscriptions or creating another
  router. Source-only consumer adoption; no production cutover or provider call.
state_before: >
  The Brief custom endpoint bypassed build_providers; reply caches and refresh
  intervals ignored policy/model identity; TypeError compatibility could repeat
  a request; a policy error could be treated as ordinary waterfall failure.
changed:
  - path: engine/master_brain.py
    what: >
      Shared-policy preflight, per-invocation and publication rechecks, cache/model
      identity and provenance, policy-aware intervals, and typed degraded output.
  - path: engine/llm_auth.py
    what: Propagate typed workload refusals without fallback or provider-failure accounting.
  - path: tests/test_master_brain_ladder.py
    what: Real producer/builder/cache/publication/template regressions with inert providers.
  - path: tests/conftest.py
    what: Permit only seven named tmp-root policy tests to exercise the real reply cache.
  - path: templates/_aibrief_body.html.j2
    what: Plain bilingual policy-refusal copy in the existing degraded component.
  - path: docs/superpowers/plans/2026-09-16-ai-brief-workload-adoption.md
    what: Frozen scope, acceptance, source proof, dependency and rollout boundaries.
verified:
  - claim: Tests discriminate the missing consumer protections before implementation.
    command: pytest tests/test_master_brain_ladder.py with the corresponding new cases
    result: >
      Consumer RED 15 failed; cache envelope RED 2 failed; publisher/interval RED
      5 failed; within-waterfall and SDK-replay RED 3 failed. Real cache tests use
      isolated tmp roots, not the blanket miss/no-op fixture.
  - claim: Existing provider and Brief behavior remains covered by the composed regression.
    command: >
      MM_DATA_GUARD=1 python3 -m pytest tests/test_codex_provider.py tests/test_llm_auth.py
      tests/test_provider_workload_policy.py tests/test_key_pool.py tests/test_ollama_provider.py
      tests/test_ai_costs.py tests/test_provider_health.py tests/test_provider_capacity.py
      tests/test_master_brain.py tests/test_master_brain_ladder.py tests/test_master_brain_zh_ladder.py
      tests/test_master_brain_policy.py tests/test_master_brain_producer.py tests/test_master_brain_scorer.py
      tests/test_w7_llm_determinism.py -q --tb=short --basetemp <outside-repo-operation-temp>
    result: 419 passed in 16.29 seconds; no real provider, credential or publication effect.
  - claim: The actual producer writes one consistent payload consumed by the existing template.
    command: tests/test_master_brain_ladder.py::test_brief_real_run_publishes_policy_result_to_existing_template
    result: >
      Synthetic provider result equals returned Brief, fixture data JSON and fixture
      site JSON; the actual shared Jinja template renders it. Refusal rendering has
      English/Chinese plain copy and no internal workload code in its visible text.
unverified:
  - claim: The new source is merged, installed, enabled or production-proven.
    what_would_verify: >
      Parent #7179 acceptance; exact-head independent review; current-main integration
      and binding CI; authorized deployment plus real VPS input/result consumption.
  - claim: Browser or real provider acceptance exists for this consumer.
    what_would_verify: >
      An actual browser receipt and approved provider/service-principal canary.
      The browser-capture request was blocked before execution; path presence and
      successful Jinja rendering are not browser or production proof.
unresolved:
  - Core-fabric H0/P0/atomic claims, native realm evidence and service admission remain incumbent gates.
  - Native Mastermind waterfall and marketing provider caches are not migrated by this slice.
  - Policy fingerprints do not synchronize credentials or establish atomic distributed revocation.
next_actions:
  - >
    Recover the Draft PR by exact head branch claude/vps-aibrief-policy-adoption-stack-20260916-sol.
    Review its complete consumer delta above #7179, without merging into the parent branch.
  - >
    Obtain independent review through the incumbent Fable integration route; preserve
    the same writer for repairs and all current runtime/provider holds.
  - >
    After parent protection, perform current-main composition and normal PR retargeting,
    conclude binding checks, then separately qualify an approved live AI Brief shadow.
do_not_redo:
  - Do not rebuild the policy engine, cache store, scheduler, account/quota database or Executive admission.
  - Do not activate profiles, call providers, rotate/copy credentials or spend from this source receipt.
  - Do not overwrite #7024 regime work, #7178 scheduling, #7114 routing or existing Fable/PF1 children.
danger_areas:
  - An already-sent provider request cannot be undone; observed policy change discards its result, not its cost.
  - Internal provider descriptors contain credentials; only the closed policy receipt is published.
  - Unprofiled legacy callers deliberately retain existing behavior until explicitly migrated.
  - Source tests are not API entitlement, available quota, service authentication or production acceptance.
decisions:
  - DEC:EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT
---

## Source ownership and continuation

Consumer operation: vps-site-aibrief-adoption-20260916-sol-001. Existing principal
operation: agent-fabric-end-to-end-fable-integration-20260913-sol-001; exact carrier
C0BSBM78V1N / 1789324397.992989. This record creates no Executive Job or worker.

The native sparse helper created an isolated clean carrier at main 9579caf3f950f1a2e7b959a9b3b68d26e42e5d06.
A separate stack branch was then created at #7179 head 889174901bdaabba44a8f60f3179ff7bd32c8061,
without rewriting the parent branch or another worker. Source custody remains Sol.
The #7024 patch was read: its regime helpers and template receipt are separate
from these provider/cache/degraded-copy changes; current composition is still owed.
#7178 changes only the existing nightly workflow and reachability test.

HOLD-FOR-SOL: Draft, no merge-on-green and autoMerge null. Source release is not
production activation. Continue with exact-head independent findings; never infer
review pickup, execution, terminality or a successor from Slack delivery alone.


## Composed-source validation receipt

Full differential contract-delta against Macro main
52380b870218b61865fb56458500cac00ce4932b completed with exit 0:
zero introduced / zero inherited findings (268.44 seconds). The script's own
reported base matches the captured revision. No gate or scope was weakened.
Compile checks and git diff --check pass. Agent OS: 1118 records, zero errors,
97 warnings. The composed provider/Brief regression remains 419 passing tests.
No runtime, credential, provider, deployment or production proof is implied.


## Same-writer composition repair

The first W1 head 9069f63fcef117c34ca80f39223a238912213ceb composed cleanly with
main 52380b870218b61865fb56458500cac00ce4932b (tree caa4300a6c81f1b6cd6bb320da99425c1474003a).
The #7024 composition probe exposed two W1 source-position conflicts: adjacent
stdlib imports and both consumers inserting immediately after translation.
The writer moved only its own insertion points and preserves the regime writer.
The finalization recheck now also has an explicit persist=False regression.
Fresh complete provider/Brief regression: 420 passed in 15.81 seconds.

The CI-manifest collision between #7024 and the W0 dependency also exists when
composing #7024 with parent 889174901 alone. It is not created by W1 and remains
with the incumbent integration owners; this branch does not edit that manifest.
Current-head composition and full dependency recheck remain separate receipts.
