# Plugin Integration Handoff — Data + Automation + Observability

Date: 2026-09-07
Parent: `WS:CHAIRMAN-CONTROL-ROOM`
Read first: `agentos/handoffs/CHAIRMAN-CONTROL-ROOM-PLUGIN-INTEGRATION-INDEX-2026-09-07.md`
Scope: Airbyte Agent Engine, Make, PostHog

## Mission

Use the new data, automation, and telemetry connectors to widen Mastermind's reach without creating duplicate ingestion, queue, lifecycle, state, retry, or control planes.

## Why it matters

Airbyte can bridge business systems not covered by direct plugins, Make can automate external workflows, and PostHog can close the product-learning loop. These are high-leverage capabilities, but they overlap strongly with infrastructure Mastermind already owns. Their value comes from thin integration at the edge, not from becoming a second operating system.

## Authority precedence

- Executive OS owns lifecycle, admission, jobs, attempts, workers, and canonical runtime events.
- Existing Mastermind data/identity/event/state planes remain canonical.
- Direct first-party connectors are preferred when they already expose the needed system cleanly.
- Airbyte is a connector/data-access bridge, not a new data authority.
- Make is an external automation executor/transport, not Mastermind's queue or orchestration authority.
- PostHog owns product telemetry/analytics surfaces it actually receives, not market truth, organizational truth, or trading authority.

## Verified state

### Airbyte Agent Engine — `PARTIAL`

Initial connector listing returned `401 User has no embedded organizations`. The prescribed enrollment check was then run and provisioning is now `COMPLETED` for a MastermindX Airbyte organization.

Current remaining state:

- account enrollment: complete,
- default workspace: reachable,
- created connectors: **0**,
- payment setup: still required according to enrollment status.

Do not call this fully integrated until at least one justified connector has a real consumer and production proof.

### Make — `PROVEN_LIVE`

Authenticated against `us2.make.com` with an organization and two reachable team/private spaces, including a MastermindX private space. No scenario was created or activated during this assessment.

### PostHog — `PROVEN_LIVE`

The `MastermindX` organization is reachable in PostHog. This proves account/organization access, not event instrumentation completeness.

## Exact scope

### Airbyte

Approved role:

Use Airbyte when a required business system does not have a better direct connector or when Airbyte's unified indexed access materially improves a defined research/operations workflow.

Setup order:

1. Future session checks enrollment status and current organization/workspace.
2. Complete payment setup if required and if Chairman intends to use Airbyte.
3. List created connectors before creating anything; avoid duplicates.
4. If a new source is justified, list available connector templates and use the provider's browser credential flow. Never request/paste API keys or passwords in chat.
5. After connector creation, inspect/describe its schema before any execute/query call.
6. Choose a narrow producer -> consumer use case and explicit selected fields.
7. Prefer read-only first. Any write back into a business system requires explicit user intent and source-specific authority.
8. Do not duplicate data into a new Mastermind store unless the existing architecture explicitly requires it.

Recommended first acceptance slice:

- Connect one genuinely needed business source that is **not already better served by a direct plugin**.
- Retrieve a small real dataset with explicit field selection.
- Consume it in one Mastermind workflow or decision-support view.
- Preserve source IDs/timestamps/provenance.
- Demonstrate correction/null handling.

Failure rules:

- Missing enrollment/payment: stop at provisioning boundary.
- Credential failure: restart provider credential flow; never accept secrets in chat.
- Search-index lag: honor Airbyte's list/search semantics; do not silently present stale indexed data as live.
- Duplicate connector found: use the newest valid instance per connector rules; do not create another.
- Unknown write effect: read the source system before retrying.

### Make

Approved role:

Use Make for bounded external automations where the provider ecosystem or visual workflow materially reduces implementation effort and where Mastermind does not already own the same orchestration capability.

Good examples:

- forwarding a non-authoritative notification between SaaS tools,
- formatting/delivering a scheduled report whose canonical data comes from Mastermind,
- low-risk synchronization where one side remains explicitly authoritative,
- temporary bridge while a direct integration is being validated.

Rejected roles:

- CEO Job/Attempt queue,
- worker allocation/control,
- canonical retry engine,
- canonical lifecycle state,
- canonical event bus,
- durable transcript/memory store,
- invisible production-critical orchestration that Mastermind cannot reconcile.

Setup order:

1. Call Make environment discovery and select the intended team explicitly.
2. List existing scenarios/folders before creating a scenario.
3. Define trigger, source of truth, idempotency key, expected side effects, and recovery path.
4. Build inactive first unless the Chairman specifically needs it live immediately and all mappings are proven.
5. Run with a real but low-risk input.
6. Inspect execution output and downstream effect.
7. Only then activate recurring/triggered behavior.
8. Record the scenario ID/name and owning Mastermind workstream in Agent OS.

Acceptance:

- One real end-to-end automation works.
- Retry cannot create duplicate consequential effects.
- Mastermind can determine whether a run succeeded or failed.
- Disabling Make does not destroy canonical lifecycle/data state.

### PostHog

Approved role:

PostHog is the product learning/observability plane for product telemetry that is intentionally instrumented there: usage analytics, funnels, retention, experiments, feature flags, errors/logs/LLM analytics as appropriate.

It must not become:

- market-data truth,
- a trading-signal authority,
- organizational lifecycle authority,
- a replacement for production database truth.

Setup order:

1. Inventory current PostHog project/org instrumentation and existing events before adding anything.
2. Map each product question to a minimal event/property contract.
3. Ensure identity semantics align with Mastermind's existing identity architecture; do not create a second user/entity identity model.
4. Add or repair one event path with a real producer and an insight/dashboard consumer.
5. Verify event freshness, property null behavior, and environment separation.
6. For feature flags/experiments, define owner, exposure event, success metric, rollout/rollback behavior, and guardrails.
7. Connect errors/logs only where they add actionable diagnosis rather than duplicating observability blindly.

Recommended first product-learning slice:

Pick one premium workflow in Mastermind and answer a concrete question such as: **Can the primary persona complete the workflow, and where do they abandon or encounter failure?** Instrument the minimal start/success/failure events, prove them on production traffic, and create a usable insight.

Acceptance + production proof:

- A real production interaction emits the intended event.
- The event appears in PostHog with correct identity/environment/properties.
- The insight answers a named product question.
- Null/correction/duplicate event behavior is understood.
- No analytics summary is elevated into market/trading authority without the separate validation architecture required by Mastermind law.

## Deterministic vs model method

Deterministic:

- connector/workspace/scenario/project identity,
- event receipt and timestamps,
- automation run status,
- data-source schema and returned records,
- feature-flag configuration.

Model-assisted:

- choosing research fields,
- explaining analytics movement,
- proposing automation/design improvements,
- synthesizing product-learning conclusions.

Model synthesis must remain downstream of observable evidence.

## Data / time / null / correction behavior

- Preserve provider timestamps and source IDs.
- Distinguish event time from ingestion/index time.
- Explicitly handle empty result vs connector failure.
- Do not fill missing business fields with inferred values unless clearly labeled and the workflow permits it.
- Corrections in authoritative systems must flow through or trigger reconciliation; stale replicas must not silently win.

## Non-goals

- No generic enterprise data lake because Airbyte exists.
- No Make-based Mastermind operating system.
- No PostHog-based business/market truth model.
- No duplicate identity or event ontology.
- No automations without a named user/machine job and consumer.

## Continuation handoff

After a material integration slice, record: exact connector/workspace/scenario/project, authority owner, schema/event contract, real input, visible result, failure/retry semantics, production proof, and exact next action.

## Stop condition

Stop when integration would duplicate an existing canonical plane, requires secrets in chat, or creates a consequential write whose effect cannot be reconciled on the same carrier.
