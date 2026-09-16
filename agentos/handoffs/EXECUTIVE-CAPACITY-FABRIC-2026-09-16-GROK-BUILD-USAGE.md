---
workstream: WS-EXECUTIVE-CAPACITY-FABRIC
status: BUILT_NOT_PROVEN
owner: Sol
updated_at: 2026-09-16T09:51:40Z
---

# Grok Build weekly usage meter — Provider Control continuation

## Mission

Expose Grok Build / SuperGrok subscription headroom to the existing Shared AI Provider Control truth plane so Capacity can eventually rank Grok work without guessing quota from plan labels or from `grok usage`.

This matters because the installed Grok CLI's public `usage` command reports local disk/worktree usage, not account subscription allowance. A live, prompt-free ACP billing read is available and matches the Grok Settings > Usage weekly SuperGrok Heavy meter.

## Authority precedence

- Executive OS remains Job/Attempt/Worker/Event and claim authority.
- Model Router owns task/model suitability.
- Shared AI Provider Control owns provider entitlement, quota/headroom/reset/cooling facts.
- Capacity Fabric consumes those facts for placement/economics.
- Runtime/carrier law owns START/EFFECT_UNKNOWN continuity.

This slice adds no router, quota ledger, account registry, credential store, worker lifecycle, retry plane, or provider-specific Executive state.

## Verified state

Carrier: `sol/grok-build-subscription-usage-20260916`, stacked on the incumbent Provider Control usage owner `sol/opencode-go-subscription-usage` / Macro #7143 at `facf7074dbbe58a3a9ffef4eae0ca92c97031634`.

Added:

- `engine/provider_subscription_usage_grok.py` — converts Grok CLI ACP `_x.ai/billing` into `mastermind.provider_subscription_usage/v1`.
- `scripts/grok_build_usage.py` — read-only operator/machine projection.
- `tests/test_provider_subscription_usage_grok.py` — exact/shared/fail-closed/prompt-free transport coverage.
- SuperGrok overlay telemetry now records the UI + CLI ACP acquisition surface.

A real Mac Studio observation through `/opt/homebrew/bin/grok` at `2026-09-16T09:51:40Z` returned:

- provider `xai`
- tier `heavy`
- weekly `supergrok_shared`
- `used_percent = 1.0`
- `reported_remaining_percent = 99.0`
- reset `2026-09-21T05:54:40Z`
- exact observability, no degraded codes

This agrees with the Chairman-provided Grok Usage UI for the SuperGrok Heavy weekly bucket. The separate Grok Bot weekly bucket is deliberately not read or merged into Build capacity.

The native read sends only ACP `initialize` followed by `_x.ai/billing`; it never sends a model prompt and never reads or returns credential files/tokens. Authentication remains inside the installed Grok CLI.

## Scope / non-goals

In scope: one current SuperGrok weekly provider-reported percentage/reset observation for the authenticated CLI account.

Not in scope: Grok Bot quota, absolute token/request inference, model debit calibration, account pooling, routing preference, provider activation, Executive claim, or worker dispatch.

## User / machine journey

1. Provider Control invokes `scripts/grok_build_usage.py` on the host carrying the authenticated Grok CLI.
2. The CLI's ACP surface returns the current weekly billing snapshot.
3. Provider Control emits one secret-free `provider_subscription_usage/v1` row scoped to `supergrok_shared`.
4. A generic capacity bridge may consume that observation only after the existing Provider Control/Capacity contract explicitly maps this schema and freshness into capacity facts.
5. Model Router + Capacity then rank Grok only after suitability, policy, health, admission, and claim-time revalidation gates pass.

## Data / time / null / correction behavior

- `creditUsagePercent` is preserved as provider-reported percent; no absolute allowance is invented.
- `currentPeriod.type` must be weekly.
- reset must parse and be after observation time.
- tier must map to a reviewed SuperGrok tier.
- missing/malformed/stale dimensions emit no quota row and explicit `GROK_BUILD_*` degraded codes.
- a later fresh observation supersedes an earlier observation; this slice persists no ledger and therefore cannot double-count corrections.

## Deterministic vs model method

Entire capability is deterministic parsing and bounded local process RPC. No LLM judgment is used for quota truth.

## Failures

- CLI unavailable / process failure -> bounded `GROK_BUILD_ACP_UNAVAILABLE`.
- ACP timeout -> `GROK_BUILD_ACP_TIMEOUT`.
- JSON-RPC error/missing billing response -> fail closed.
- unknown tier, non-weekly period, missing usage %, missing/stale reset -> no quota row.

## Implementation order and proof

Completed source order: contract parser -> bounded ACP acquisition -> operator projection -> focused tests -> live provider observation.

Local source evidence:

- `python3 -m py_compile` for implementation/script/tests: PASS.
- focused pytest set reached all 27 test bodies green (`........................... [100%]`); this host then exhibited a pytest process teardown wait in uninterruptible I/O and was terminated after the test bodies completed. Treat this as source-test evidence, not hosted exact-head CI.
- `git diff --check`: PASS.
- live prompt-free Grok ACP usage read: PASS with the values above.

## Acceptance / production proof still required

This source slice is **BUILT_NOT_PROVEN**, not live routing. Acceptance requires:

1. publish this exact source head and obtain normal exact-head review/CI on the stacked Provider Control carrier;
2. reconcile/land the parent subscription-usage owner (#7143/#7103) rather than duplicating it;
3. use one generic, reviewed subscription-usage -> Capacity fact bridge so Grok, OpenCode, MiniMax, GLM, etc. do not get provider-specific routing planes;
4. prove the router/load balancer sees the fresh Grok weekly fact, excludes it when stale/exhausted/unknown, and gives a visible routing explanation;
5. prove one bounded real Grok Build task through the governed worker path with before/after usage and parent result consumption.

## Stop condition / continuation

Do not patch `provider_capacity.v1` with an inline Grok provider probe: that producer is intentionally provider-call-free. Do not make the router call `_x.ai/billing` directly. Do not merge Grok Bot allowance into SuperGrok Build.

Exact next action after publishing this carrier: locate or implement the **generic** Provider Control observation-to-capacity bridge at the incumbent capacity owner, map `provider_subscription_usage/v1` `provider=xai`, `scope=supergrok_shared`, `horizon=weekly` into fresh Capacity evidence, then prove it through the existing load-balancer/placement projection before any worker activation.
