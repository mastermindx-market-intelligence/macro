# Capacity Fabric router observatory

Open **Workspace → Capacity Router** (`/#/page/capacity_router`). The page is part
of the existing admin application and uses its existing signed-session gate.
`GET /api/capacity-router?minutes=15` is authenticated and never cached. The
accepted windows are 5, 15, 60 and 120 minutes.

## What the interface measures

- A live output-flow map: provider/pool → served model → requested routing lane
  → downstream consumer. Faint edges describe configuration; highlighted edges
  describe retained requests. Animated particles mean a response is streaming,
  not one particle per token. Select any node to inspect its traffic.
- Concurrent requests, requests awaiting first content, provider-reported input,
  output and cache usage, output per second averaged over the selected window,
  and first-content p50/p95 with sample count. Percentiles use linear interpolation.
- Request status, requested and served model, upstream model ID, selected route,
  route attempts, HTTP status, first-content timing and total elapsed time.
- Provider route inventory and cooldown state. Route-wide priorities/weights
  are configuration, not live quota or capacity promises; model-specific rules
  in the incumbent router remain authoritative.
- **Overflow ladders** (Overflow tab): per-family diversion state, the configured
  target ladder with the current rung highlighted, recheck countdowns, seat
  token-rate pressure, and a recent diversion log. Seat pressure is a local
  router estimate, never a provider balance.
- **Claude family lanes** (Claude lanes tab): per-account weekly budgets for each
  model family, the shared 5-hour window, bench/reset times with provider-reported
  vs estimated reset sources, drain and expiring-soon markers, and the gateway's
  stranded-family boost and account preferences. The observer polls the incumbent
  gateway's existing loopback status surface every 30 seconds using an
  operator-configured token (`claude_status_url` / `claude_token_env` in
  `observatory-export.json`); a failed read keeps the last observation with its
  original timestamp rather than inventing capacity.
- The Z.ai peak-window gate state (active/idle) appears in the metrics strip.
- Known sessions and caller-reported agent/parent/project relationships. Unknown
  identity is shown as unattributed. SDK account IDs are never treated as sessions.
- Search, model/state filters, pause/resume, window selection, topology zoom,
  full screen, keyboard selection, reduced motion and sanitized snapshot export.

## Observation and ownership

The existing M2 unified router owns all provider calls, route selection, retries,
credentials, admission and lifecycle. `capacity_fabric_observer.py` is an
observational adapter. It wraps the already-existing `/v1/messages` endpoint's
three forwarders and observes successfully delivered ASGI bytes. Context-local
request identity isolates concurrent calls. `/count_tokens`, health endpoints,
unauthorized requests and non-loopback callers are left untouched.

The OpenAI/Responses translators substitute zeros when usage is absent. The
adapter therefore observes their original parsed provider usage and ignores
translated downstream usage. An absent provider report remains unknown. Latest
cumulative usage replaces prior values; it is never added as event deltas.
Usage is reset between route attempts. Consumption from failed upstream attempts
may be unavailable. Cache fields remain separate from input/output totals.

One publisher in the incumbent process sends the latest bounded snapshot every
two seconds through the existing `vps-mmx` SSH identity. There is no new listener,
credential copy, inference proxy, background service, queue, or database.
`python -m admin.capacity_ingest` reads that private stdin stream and atomically
replaces `/var/lib/macro-admin/capacity-router.json` with mode 0600. A sequence and
process-epoch fence prevents an old draining process from replacing newer data.

## Coverage and privacy

Coverage is **one instrumented router process**. Work bypassing that router is
not claimed as observed. History starts when its observer starts and retains at
most 256 tracked active requests, 400 recent requests and 120 minute buckets.
Overflow concurrency is counted separately. The 2 MiB transport budget drops
optional old history first and explicitly reports compaction. A snapshot older
than 15 seconds is stale, not evidence that inference stopped.

Only allowlisted scalar telemetry is exported. Prompt/completion text, arbitrary
provider errors, credentials and raw account/session identifiers are excluded.
Model labels must belong to the installed vocabulary. IDs are SHA-256
pseudonyms, not an authenticated agent registry.

Callers can supply `x-fabric-client`, `x-fabric-session-id`, `x-fabric-agent-id`,
`x-fabric-parent-agent-id` and `x-fabric-project-id`, or the corresponding
`metadata.fabric` fields. Recognized Claude SDK session metadata works without a
caller change. These fields grant no routing or execution authority.

## Verification and release

Run the focused suite from the macro root:

```sh
python -m unittest admin.tests.test_capacity_router -v
node --check admin/static/capacity-router.js
node --check admin/static/app.js
```

The incumbent router has locally retained production patches. Do not replace
its source with a different remote checkout. The one-shot
`admin/deploy/stage_capacity_observer.py` checks the exact release, plist and
gateway hashes, copies and verifies the existing source, adds the two observer
modules, and changes only the service factory reference. It does not activate.
The staged generation contains `CAPACITY_OBSERVER_SOURCE.json` with hashes and
provenance. Run `admin/tests/prove_capacity_runtime.py <staged-release>` using the
router's existing venv before activation. Its 12 closed-transport cases exercise
the exact gateway and translators, without loading production credentials or
calling a provider, and compare complete response status, headers and bytes.

Deploy admin through the existing VPS release owner. Then activate the verified
overlay in the existing `ai.mastermind.fabric-router` launchd job while holding
its existing `state/reload.lock`; preserve the old plist/release for rollback.
Verify the actual loaded working directory, router health, a fresh VPS snapshot,
the authenticated admin API and real consumer traffic. A health response alone
does not prove the new generation or telemetry delivery.

## Architectural references

The native interface reuses established observability concepts without importing
a second gateway or tracing platform:

- [LiteLLM router metrics](https://docs.litellm.ai/docs/proxy/prometheus)
- [Langfuse agent graphs](https://langfuse.com/docs/observability/features/agent-graphs)
- [Helicone session tracking](https://docs.helicone.ai/features/sessions)
- [OpenTelemetry agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)

The implementation and visuals are original and use the admin's existing Python,
JavaScript and CSS stack, with no new production dependency.
