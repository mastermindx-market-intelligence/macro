# Capacity Fabric router observatory

Open **Workspace → Capacity Router** (`/#/page/capacity_router`). The page uses
the existing admin application and its signed-session gate. The live snapshot,
SSE events, durable history, intelligence and settings endpoints under
`/api/capacity-router` require that session and return private, uncached data.
Settings writes additionally require the existing Origin, JSON and CSRF checks.

## Live topology and requests

The topology includes every exported provider/pool, served model, requested
routing lane and downstream consumer, with configured and observed connections.
Pan, zoom, fit and selection keep a large topology navigable without hiding nodes
behind an aggregate count. Coverage remains limited to the incumbent router's
exported vocabulary and retained observations; it is not an agent registry.

Topology nodes and request rows retain their DOM identity across incremental
updates. One bounded SSE connection per page receives a full snapshot on connect
or reconnect, then changed rows and membership cursors. The server checks for
new observations every 250 ms, sends keepalives and periodically rechecks the
session. The source observation cadence is separate and is visible in settings.
Polling remains available if streaming delivery fails. Pause, search, model/state
filters, keyboard selection, reduced motion and snapshot export are supported.

Animated flow means that a response is streaming; it does not represent one
particle per token. The metrics distinguish concurrent requests, waiting for
first content, reported input/output/cache usage, window-average output rate and
first-content p50/p95 with sample count. Request details show requested and served
model, selected route, attempts, HTTP status and elapsed time.

The existing Overflow and Claude lanes panels continue to show the incumbent
router's diversion ladders, cooldowns, local seat pressure and reported family
budgets. Shared five-hour budgets are counted once per account, not once per
model. Provider-reported and estimated reset times remain distinct. A failed
quota read retains its original observation timestamp and cannot imply fresh
capacity. The Z.ai peak-window state remains visible.

## Durable history and demand intelligence

The existing SSH snapshot ingress writes sanitized telemetry to
`/var/lib/macro-admin/capacity-router.sqlite3`, next to its atomic current snapshot.
This SQLite database is a derived observation store, not a quota or routing
owner. Connections are closed explicitly, writes use WAL and bounded busy waits,
and read endpoints open the store read-only. The process-epoch and sequence fence
rejects duplicate or stale deliveries before history is recorded.

The UI offers 5m, 15m, 1h, 6h, 24h, 7d, 30d, all-observed and custom ranges.
`/history` accepts `minutes`, or Unix `from`/`to`, and an optional `resolution`.
Adaptive bins keep charts at no more than 720 points. Supported bin widths range
from one minute to one week. The retention boundaries are explicit:

- Completed-request detail and quota samples: seven days, with at most 200,000
  detailed terminal rows.
- Minute counters, model/pool demand and recorded gaps: 400 days.
- Per-epoch cumulative totals: all retained observed epochs. These may cover an
  older interval than the detailed chart and model/pool ledger.

Cumulative counters replace prior observations; they are never added as deltas.
Epoch totals and time-series totals describe overlapping consumption and must not
be summed together. There is no fabricated chart before observation. Minute-bin
boundaries, ingestion gaps and per-field usage coverage are returned explicitly.
Unknown usage stays unknown; a reported zero stays zero. Cache fields are separate
from ordinary input/output totals, and failed-attempt consumption may be absent.

The Intelligence panel derives model membership, routing classes and shared
pools from current configuration and observed demand. It explains traffic share,
saturation, measured versus estimated limits, reset observations, compatible
alternatives and conditional expansion requirements. It reports the evidence
window and coverage used. Its fallback is labeled as a retained-request sample
when the durable demand ledger is not available. Advice does not purchase a
subscription, grant capacity, change routing or authorize execution.

## Settings and recovery

The installed native `ConfigRefresh` owner remains the authority for effective
configuration. The admin transport reuses the existing bidirectional SSH
observation pipe; it adds no listener, inference proxy, retry daemon or queue.
Settings remain non-writable until the current native owner is reachable, its
effective revision matches the persisted routes document, all known installed
writer adapters match the qualified fingerprints, and no unresolved transaction
is fencing that document.

An edit requires validation followed by an explicit apply. Editing the form
invalidates its earlier validation. The allowlist permits:

- Observation intervals of 0.25, 0.5, 1, 2 or 5 seconds.
- Existing route/model priorities and weights, within bounded numeric ranges.
- Reordering the existing members of an existing routing class.

Credentials, provider/model enrollment, quota ceilings, subscriptions and paid
routing permissions are excluded. A candidate cannot remove the last configured
usable path for a model. Changes affect future admissions; active bindings remain
owned by the native router.

The admin adapter and enrolled native configuration writers share one stable
file lock. Each reads the document after acquiring that lock. Apply checks the
expected revision, persists a prepared receipt before replacement, atomically
writes the candidate, asks the existing event-loop owner to adopt it, and records
the verified outcome. A busy owner returns a known NOT_APPLIED result before the
new operation has effects. Unresolved receipts fence subsequent writers.

A lost reply is not permission to submit another apply. **Reload effective
settings** sends a distinct reconcile-only request for the same operation and
original intent, then reads effective state. Reconciliation can confirm an
existing terminal receipt, adopt an already persisted postimage, or prove a
non-effect from an unchanged preimage with writer continuity. It never rebuilds
or rewrites the patch. Missing/ambiguous durable evidence remains EFFECT_UNKNOWN.
An old runtime epoch cannot execute an old apply in a new epoch; reconciliation
preserves the operation's origin epoch while using the currently observed owner.
A later authoritative terminal receipt supersedes cached transport uncertainty.

## Observation, privacy and ownership

The M2 unified router owns provider calls, route selection, retries, credentials,
admission and lifecycle. The observer wraps its existing forwarders and observes
successfully delivered ASGI bytes. Context-local identity isolates concurrent
calls. Token-count, health, unauthorized and non-loopback requests are untouched.

The OpenAI/Responses translators may substitute zeros for absent upstream usage.
The observer therefore uses original parsed provider usage, ignoring translated
downstream substitutes. Latest cumulative usage replaces prior values and is
reset between route attempts.

One publisher inside the incumbent process sends bounded snapshots through the
existing `vps-mmx` identity. The native ingress atomically replaces the current
snapshot with mode 0600 and records the derived history. Snapshot limits remain
256 tracked active requests, 400 recent requests and 120 minute buckets, with an
explicit overflow count and transport-compaction report. Durable storage does not
make unexported traffic observable. A snapshot older than 15 seconds is stale,
not proof that inference stopped.

Only allowlisted scalar telemetry is exported. Prompt/completion text, arbitrary
provider errors, credentials and raw account/session identifiers are excluded.
Model labels belong to the installed vocabulary. IDs are SHA-256 pseudonyms.
Caller-supplied client/session/agent/parent/project fields describe observations
and grant no routing or execution authority. Unknown identity is unattributed.

## Qualification and deployment

Run the focused composition from the macro root:

```sh
python -W always::ResourceWarning -m unittest \
  admin.tests.test_capacity_router admin.tests.test_capacity_history \
  admin.tests.test_capacity_intelligence admin.tests.test_capacity_stream \
  admin.tests.test_capacity_controls admin.tests.test_capacity_api \
  admin.tests.test_capacity_staging
python -m admin.tests.prove_capacity_router_ui
node --check admin/static/capacity-router.js
node --check admin/static/app.js
```

The API suite exercises the actual HTTP handler, session/Origin/CSRF guards,
SSE sockets and reconnects, settings transport and history across server restart.
The Chromium fixture checks all topology nodes, stable row/node identity,
validation/apply, same-operation reconciliation, desktop themes and mobile reduced
motion. Synthetic proof does not establish production acceptance.

The incumbent router has independently maintained production patches. The
one-shot `admin/deploy/stage_capacity_observer.py` requires the exact installed
release, plist and gateway hashes. It copies and verifies that release, overlays
the observer/schema/control-owner/shared-lock modules, preserves its export
configuration and source manifest, and writes `CAPACITY_OBSERVER_SOURCE.json`.
`--prepare-controls` prepares adapters for the actually installed configuration
writers without installing or running them. The candidate preserves each
writer's existing policy transform and adds locking before its document read.
Control capability is gated by exact installed adapter fingerprints.

Staging does not activate a service, install a native writer or change routes.
Run `admin/tests/prove_capacity_runtime.py <staged-release>` using the incumbent
venv. Its 12 closed-transport cases exercise the exact gateway/translators without
production credentials or provider calls and compare status, headers and bytes.
Inspect the real native writer diffs and qualify the existing configuration owner
before enabling controls.

Publish the qualified branch and use the repository's existing release controls.
Deploy the accepted admin revision through the incumbent VPS owner. Native
activation must preserve the current release's custody, active requests and
existing reload lock. Retain exact rollback preimages; an old destructive
kickstart recipe is not evidence of stream-preserving activation.

Acceptance requires the actual loaded source and generation, fresh telemetry at
the VPS, authenticated live dashboard interactions, SSE reconnect, durable
history across restart, effective settings readback and an explicit reversible
observation-cadence change. A health response, green CI or merged PR alone does
not establish those outcomes. Recovery and production receipts belong in the
existing observatory report and `review_evidence/capacity_router/` task record.

## Architectural references

The implementation and visuals are original, using the admin's existing Python,
JavaScript and CSS stack. Established concepts are documented by
[LiteLLM](https://docs.litellm.ai/docs/proxy/prometheus),
[Langfuse](https://langfuse.com/docs/observability/features/agent-graphs),
[Helicone](https://docs.helicone.ai/features/sessions) and
[OpenTelemetry](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md).
