# Capacity Fabric Router Observatory
Date: 2026-11-10
Operation: capacity-router-observatory-20261110
Parent context: WS:EXECUTIVE-CAPACITY-FABRIC (source plan; organizational linkage not yet updated)
Procedure: Mastermind protected master 76cca6bf0d4f54c1c4a732726a16c70dbe8ed679, Skillpack 1.0.1, bootstrap major 1.
Source owner: macro; isolated GitHub-native branch feat/capacity-router-observatory-20261110, base 7e115b6f1f10832b4b123149215ea7a041279753.

## Outcome and completion
Deliver a sophisticated authenticated router interface at admin.mastermind-x.com showing actual Capacity Fabric providers, models, routes/lanes, concurrent requests, token usage and downstream consumers where identity exists. Complete means source squash-merged by the permitted GitHub path, installed on the VPS, connected to the incumbent live router, and verified through the authenticated browser and actual telemetry. A mock graph, open PR or green test alone is insufficient.

The current assignment explicitly authorizes direct squash merge and VPS deployment. Actual enforced GitHub/CODEOWNERS/security requirements and recorded holds still apply. No blanket external technical-review ceremony.

## Established inputs
- Admin is the existing stdlib Python + vanilla JavaScript console in macro/admin.
- Existing public domain, signed-session auth, Caddy, admin.service and macro-update deployment remain the owners.
- Connected Studio carrier is verified as m2studio. Existing configured VPS SSH identity authenticated to the admin host without exposing secrets.
- Incumbent Capacity Fabric is the M2 loopback unified router on port 8313, with /healthz, bearer-protected /statusz and /v1/models. Source provenance and instrumentation are being reconciled before any runtime change.
- Open-source architectural references: LiteLLM metric decomposition; Langfuse aggregated/expanded trace graphs; Helicone session paths; OpenTelemetry trace/parent identifiers. Reuse existing web stack and router instead of another gateway or tracing database.

## Work tree
1. Discover exact router source, current telemetry, live writers and private transport; map measured/unknown semantics.
2. Implement a bounded secret-free read projection in the existing admin API. Reuse canonical request/route data. If necessary, extend the incumbent router's observational instrumentation without changing selection, credentials, retry, queue or admission.
3. Build a responsive dark router workspace: animated topology, provider/model/lane/consumer drilldowns, throughput/history, concurrency and health, request explorer, detailed lineage and timing inspector, filters, pause and freshness.
4. Qualify actual data semantics, authentication, degraded/stale states, bounded memory/requests, keyboard/reduced-motion behavior, desktop/mobile rendering and affected regression tests.
5. Publish one coherent change, use the current authorized squash release path, deploy exact source through existing owners, prove live data and browser workflow, and save final evidence here.

## Data and interaction contracts
- Never manufacture agents, parent-child relationships, usage, throughput or capacity. Missing values are unknown, not zero.
- Explicitly distinguish requests/streams, observed token totals, final/provisional usage, and inferred versus recorded downstream identity.
- Preserve requested versus served model, route/pool identity, concurrency, cooldown, failures and attempt lineage.
- Read-only interface; no provider/model settings, scheduling, credential changes or destructive controls.
- No prompts/completions, API keys, raw provider error payloads or private account identifiers in browser telemetry.
- Stable node selection; bounded polling or existing event transport, no overlapping refreshes; stale/disconnected indicators; hidden-tab and reduced-motion handling.
- Runtime data remains outside Git; no second router, quota store, agent registry, lifecycle owner or retry plane.

## Execution decision
Principal retains architecture, tightly coupled implementation and deployment under LOWER_TOTAL_OVERHEAD and UNIQUE_APPROVED_ACCESS while source/transport are resolved. A native reasoning child provided architecture synthesis only, with no writes or execution. WHY NOT FABLE: no additional strategic principal is needed. Reassess separable paid-Fabric labor once exact contracts are frozen; never duplicate a live worker.

## Evidence and frontier
Initial discovery and source branch creation verified. Next: inspect incumbent gateway status fields and source provenance, then build the smallest complete producer-to-admin consumer path.
