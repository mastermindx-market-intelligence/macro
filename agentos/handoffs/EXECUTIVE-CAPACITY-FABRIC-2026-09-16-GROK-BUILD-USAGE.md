---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/grok-build-subscription-usage-20260916
model: sol
ended_because: blocked
mission: >
  Expose the authenticated Grok Build / SuperGrok weekly subscription meter through
  Shared AI Provider Control, prove it against the real provider surface without a
  model prompt, and preserve the exact architecture gates before Capacity routing.
state_before: >
  Grok Build had no machine-readable subscription usage meter in Provider Control;
  the installed `grok usage` command described local disk/worktree usage, and the
  load balancer could not lawfully reason about SuperGrok weekly headroom.
changed:
  - path: engine/provider_subscription_usage_grok.py
    what: >
      Added bounded prompt-free ACP `_x.ai/billing` acquisition and fail-closed
      normalization into the existing provider_subscription_usage/v1 observation.
  - path: scripts/grok_build_usage.py
    what: >
      Added a read-only secret-free operator/machine projection for the current
      SuperGrok weekly usage observation.
  - path: tests/test_provider_subscription_usage_grok.py
    what: >
      Added exact/shared/exhausted/stale/unknown-tier/prompt-free transport and
      secret-free regression coverage.
  - path: config/provider_subscription_plan_overlay.v1.json
    what: >
      Recorded the existing SuperGrok telemetry surface as UI plus Grok CLI ACP
      billing without changing plan allowance or routing authority.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-GROK-BUILD-USAGE.md
    what: >
      Corrected the continuation to the current live proof and the accepted
      Provider Capacity V2 -> #657 -> CF2-I -> C2 dependency boundary.
verified:
  - claim: >
      The exact source head 343fdfb09043f5b3e3bdfb99c81232d2a960a349 passes the
      focused Grok meter suite, compile and diff checks.
    command: >
      PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider
      tests/test_provider_subscription_usage_grok.py --tb=short; then py_compile and
      git diff --check HEAD^..HEAD in the owned Mac Studio worktree.
    result: >
      11 tests passed; seven warnings were unrelated external pytest-cache cleanup
      permission warnings. Compile and diff checks passed.
  - claim: >
      The prompt-free real provider read exposes the SuperGrok Heavy weekly shared
      bucket as 1 percent used, 99 percent remaining, reset 2026-09-21T05:54:40Z.
    command: >
      python3 scripts/grok_build_usage.py --grok-binary /opt/homebrew/bin/grok
      --timeout-seconds 8 at 2026-09-16T10:46:51Z.
    result: >
      provider=xai, tier=heavy, scope=supergrok_shared, observability=exact, no
      degraded codes, with the stated percentage and reset. Carrier was grok 1.0.30
      (04b7ffed98c6), SHA-256 d53b6e543e482716236748914331db50145c696ac7af91f1ebdedcf5654cfecb.
  - claim: >
      An independent exact-head minimal-source replay on the MacBook reproduced the
      deterministic parser/observer behavior without using the Mac Studio worktree.
    command: >
      Fetch the four exact GitHub source blobs at 343fdfb0, compile them, and run eight
      direct deterministic parser/observer assertions under system Python.
    result: >
      Compile passed and all eight deterministic assertions passed. Pytest was not
      installed on that MacBook and was not installed for the proof.
unverified:
  - claim: The Capacity/load-balancer consumes this Grok usage observation.
    what_would_verify: >
      Accept #688 Step-A semantics, implement the canonical Provider Capacity V2
      resource evidence path, then prove #657 -> CF2-I -> C2 consumption with stale,
      exhausted, unknown and policy-ineligible cases.
  - claim: The observed Grok binary identity is a durable Provider Capacity capability generation.
    what_would_verify: >
      Bind the reviewed executable/source identity into the accepted Provider Capacity
      V2 generation contract; this handoff records only the carrier used for the live proof.
  - claim: #7213 has passing hosted exact-head CI.
    what_would_verify: >
      Reconcile the stacked parent carrier and run the repository authority/hosted gates
      from a supported base; the current ci-authority failure is unsupported_base_ref.
  - claim: One real Grok Build task is accepted through the governed routing path.
    what_would_verify: >
      After all architecture, policy, claim and parent-stack gates pass, run a bounded
      task from fresh usage truth to visible result, before/after usage and parent consumption.
unresolved:
  - >
    Mastermind #688 Step A remains HOLD pending Sol's typed-result repair: policy
    INELIGIBLE must not collapse into numeric KNOWN_ZERO.
  - >
    Macro #7103 has advanced to d801a562 but still owes fail-closed static plan
    quantification semantics before routing; #7143 has not yet reconciled that parent.
  - >
    #657 is BUILT_NOT_PROVEN / REPAIR_REQUIRED, CF2-I is UNBUILT, and the canonical
    C2/Executive atomic resource+worker commitment is UNBUILT.
  - >
    #7213 remains Draft on a stacked feature base and its authority check refuses that
    base; this is not hosted acceptance.
next_actions:
  - >
    Accept the #688 Step-A resource-composition and execution-mode contract before
    implementing any subscription-usage-to-Capacity consumer.
  - >
    Reconcile the existing #7103 -> #7143 stack in owner order; do not leapfrog #7143
    or retarget #7213 around its incumbent parent.
  - >
    Once Step A is frozen, instantiate xai/supergrok_shared/weekly only through the
    canonical Provider Capacity V2 resource graph and incumbent #657 -> CF2-I -> C2 chain.
  - >
    Then prove stale/exhausted/unknown/policy gates, a visible routing explanation, and
    one bounded real Grok Build task with before/after native usage.
do_not_redo:
  - >
    Do not patch legacy provider_capacity.v1 with a Grok provider call and do not make
    Model Router call `_x.ai/billing` directly.
  - >
    Do not create a Grok-specific quota ledger, selector, retry plane, account registry,
    worker lifecycle or commitment state.
  - >
    Do not merge Grok Bot allowance into the SuperGrok Build weekly bucket or invent
    absolute token/request capacity from the provider percentage.
  - >
    Do not bypass the #7103/#7143 stack or repeat a modifying effect after ambiguous transport.
danger_areas:
  - >
    A working prompt-free meter is Provider Control observation capability, not routing
    authority, enrollment, worker admission or production acceptance.
  - >
    Legacy provider_capacity.v1 is strict and source-identity locked; widening it would
    violate the current V2/resource-composition direction.
  - >
    Provider policy/rights and execution mode remain hard gates even when Grok shows
    abundant unused quota.
prs: [7213, 7143, 7103]
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

Carrier: Macro PR #7213 (`sol/grok-build-subscription-usage-20260916`). The exact source head independently re-proven before this records update is `343fdfb09043f5b3e3bdfb99c81232d2a960a349`. Its immediate base remains the incumbent Provider Control usage owner `sol/opencode-go-subscription-usage` / Macro #7143 at `facf7074dbbe58a3a9ffef4eae0ca92c97031634`. The grandparent #7103 has independently advanced to `d801a562655c7a3f4b75dd7736c99142ba97fbf6`; do not leapfrog or retarget #7213 around #7143 while that stack is unreconciled.

Added:

- `engine/provider_subscription_usage_grok.py` — converts Grok CLI ACP `_x.ai/billing` into `mastermind.provider_subscription_usage/v1`.
- `scripts/grok_build_usage.py` — read-only operator/machine projection.
- `tests/test_provider_subscription_usage_grok.py` — exact/shared/fail-closed/prompt-free transport coverage.
- SuperGrok overlay telemetry now records the UI + CLI ACP acquisition surface.

A fresh real Mac Studio observation through `/opt/homebrew/bin/grok` at `2026-09-16T10:46:51Z` returned:

- provider `xai`
- tier `heavy`
- weekly `supergrok_shared`
- `used_percent = 1.0`
- `reported_remaining_percent = 99.0`
- reset `2026-09-21T05:54:40Z`
- exact observability, no degraded codes

The observed carrier identity for that proof was `grok 1.0.30 (04b7ffed98c6) [stable]`, SHA-256 `d53b6e543e482716236748914331db50145c696ac7af91f1ebdedcf5654cfecb`. This binary identity is evidence for the live receipt; it is not yet a Provider Capacity capability-generation contract.

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

Local source evidence at exact source head `343fdfb09043f5b3e3bdfb99c81232d2a960a349`:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider tests/test_provider_subscription_usage_grok.py --tb=short`: **11 passed**. Seven warnings came only from pytest cleanup of an unrelated external browser-runtime cache and did not name this worktree or test.
- `python3 -m py_compile` for implementation/script/tests: PASS.
- `git diff --check HEAD^..HEAD`: PASS.
- an independent exact-head minimal-source replay on the MacBook (which lacks pytest) ran eight deterministic parser/observer assertions: PASS.
- fresh live prompt-free Grok ACP usage read: PASS with the values above.

The earlier 27-body combined run remains historical evidence only; the focused 11-test exact-head run above supersedes it for this slice.

## Acceptance / production proof still required

This source slice is **BUILT_NOT_PROVEN**, not live routing. Acceptance requires:

1. publish this exact source head and obtain normal exact-head review/CI on the stacked Provider Control carrier;
2. reconcile/land the parent subscription-usage owner (#7143/#7103) rather than duplicating it;
3. do **not** invent a generic bridge directly into legacy `provider_capacity.v1`. Current Mastermind #688 freezes Provider Capacity V2/resource-composition semantics; once Step A is accepted, Grok must enter that one canonical Capacity evidence path;
4. preserve the existing consumer chain: Model Router lawful tier -> concrete C1 Worker candidates -> Capacity resource/economics evidence -> incumbent #657 tie/abstention seam -> CF2-I -> C2/Executive atomic resource+worker commitment. No second selector or provider-specific placement plane;
5. prove the router/load balancer sees the fresh Grok weekly fact, excludes it when stale/exhausted/unknown or policy-ineligible, and gives a visible routing explanation;
6. prove one bounded real Grok Build task through the governed worker path with before/after usage and parent result consumption.

## Stop condition / continuation

Do not patch `provider_capacity.v1` with an inline Grok provider probe: that producer is intentionally provider-call-free. Do not make the router call `_x.ai/billing` directly. Do not merge Grok Bot allowance into SuperGrok Build.

Exact next action is now dependency-gated: first accept Mastermind #688 Step-A resource semantics (its current Sol review still holds one typed-result blocker: policy `INELIGIBLE` must not collapse into numeric `KNOWN_ZERO`). Then reconcile the #7103 -> #7143 parent stack and instantiate `provider=xai`, `scope=supergrok_shared`, `horizon=weekly` only through the accepted Provider Capacity V2/resource graph and the incumbent #657 -> CF2-I -> C2 chain. Do not implement a parallel bridge while that architecture is unfrozen.

Durable implementation proof is also recorded on Macro #7213 comment `5696227274`; the Step-A repair request is Mastermind #688 comment `5696107260`.
