# AI Brief runtime and recovery

## Contract and ownership

AI Brief is a read-through of existing signals, never a signal or trade source.
`master_brain.refresh_owner: vps_live` selects the existing VPS live orchestrator
as its single production writer. The former nightly `master_brain.run/run_all`
entry points then delegate without dispatch, including `--force`. Their state
gatherers, prompts and deterministic key readings remain the source vocabulary.

The independent `aibrief` lane runs under the incumbent `_lock_lane` fence and
publishes through its atomic writer. `macro-live-aibrief.timer` checks every ten
minutes, after the previous run ends. It does not wait for quote/history jobs,
CI, a full dashboard render or a frontend release. A run is bounded to ten
minutes and one inference per lens. Identical successful input waits for that
lens's configured cadence; changed input can regenerate at most hourly. Known
terminal failures are limited to three attempts per unchanged input/route.

`engine/aibrief_runtime.py` consumes the existing application Fabric factory,
`provider_production_modes.make_application_fabric_factory`, and
`llm_auth.build_fabric_provider/make_call/close_fabric_provider`. The trusted
host selector is `MM_PROVIDER_APPLICATION_MODE`, workload `site_batch`, lane
`master-brain`. The service reuses `/etc/macro-api.env` and `/etc/macro-live.env`.
It creates no credential store, provider list, capacity broker, account router,
queue or fallback controller. Capacity selection and eligible provider/model
fallback belong to that existing Fabric owner. An absent/unqualified owner or
selector never falls through to an old API/OAuth credential.

## Failure behavior

Each lens has one private envelope at
`$MACRO_LIVE_STATE_DIR/aibrief-{macro,china,btc}.json` (default
`/var/lib/macro-live/state`). Its schema is `aibrief.live.v1`:

* `last_good`: complete validated AI output with its original generation and
  evidence dates, model/provider identity and exact consumed-input digest.
* `facts`: current qualified deterministic readings and an evidence manifest.
  Dated secondary inputs outside the explicit age budget and undated inputs
  are excluded, never made current by the primary lens date. Their exclusion
  is disclosed to the reader.
* `attempt`: latest observed result, original operation ID, counters and clocks.
* `hold`: original running/uncertain/refused operation, retained independently
  of source outages, disablement or changed route metadata.
* `sequence`: publication order under the existing lane lock.

The whole envelope is replaced atomically. A RUNNING operation and its identity
are saved before binding/dispatch. A crash, transport ambiguity or failed final
write leaves that original operation held; the next tick does not replay or
move it. A refusal cannot be cleared by changing a model, account, route hash,
input or host. Recovery requires the original owner's authoritative disposition
and any actually required authorization. There is deliberately no `--force`
switch, hand-edited reset receipt, synthetic completion or cross-provider replay
for these states. The currently inspected Fabric consumer interface has no
qualified read-only durable application-turn reconciliation method; installing
that owner capability is an activation requirement for fully autonomous recovery
from interrupted application turns. Do not claim that this gap is solved by a
new scheduler or an HTTP retry.

A complete known AI reply may remain useful after an uncertain native close.
It is retained with degraded status while the original operation remains held.
A qualified legacy owner's `local_only` close observation is not described as a
native CLOSED receipt. A provider outage, malformed/truncated output or empty
reply cannot overwrite the previous valid read or advance its generation clock.
When AI is unavailable, the reader shows explicitly labelled existing dashboard
readings. These are not an invented AI summary, confidence or trading stance.

## Freshness and the browser

Generation age and source age are separate. The draft expires on its configured
cadence. Primary date-only evidence uses an explicit elapsed-age limit from the
start of its stamped UTC date: 96 hours for macro/China and 48 hours for Bitcoin.
These are conservative elapsed-age policies, not claims of exchange-calendar
qualification. The browser always shows the actual evidence and generation
dates. Future/unknown clocks cannot be current. A different consumed-input
digest supersedes the old interpretation even when the source date is unchanged.

`GET /api/aibrief/v1/{lens}` uses the existing site-full authentication dependency,
reads the private envelope and renders the same `_aibrief_body.html.j2` macro as
the static pages. It is read-only, accepts no source-path or generation options,
and returns private/no-store headers. No inference occurs on a page view.

`aibrief.js` loads visible lenses, with one outstanding request per lens, a ten
second deadline, a two MiB response bound, same-origin credentials, no redirects,
and a thirty second minimum between reads. It rejects older publication
sequences, stale cached API clocks and active content. Expiry continues even
when the network/writer stops. An old interpretation is collapsed as a previous
read; it cannot retain an unconditional green “Updated daily” claim. A 401/403
removes protected cached content. Footer navigation and focused controls are
preserved on refresh.

The existing deployment's mirror calls `scripts.aibrief_shells` to refresh only
the shared fragment in the six existing page shells. This uses the same Jinja
macro and committed fallback JSON, never private live output. It preserves the
rest of each page and footer, stages candidates before atomic publication and
is byte-idempotent. Thus deploying this repair does not depend on the broken
nightly render completing again. Normal future builds render the same template.

## Monitoring and release evidence

`/api/status` exposes only `checks.ai_brief` health metadata. Its verdict is
computed from content/evidence clocks on every read, not file mtime, timer exit,
CI success or deployment timestamp. The existing freshness sentinel monitors
this contract using its existing breach/blindness/recovery and notification
mechanisms. A cached or malformed health response is indeterminate, never green.

The existing deploy installs/verifies/enables only this lane's two systemd units;
other live timers are not restarted by this change. Rollback disarms the lane.
Do not manually install a draft branch, overwrite an active provider source
branch, grant a held mode or bypass release controls to make an activation test
pass.

Required production acceptance:

1. Actual merged source and loaded service/timer paths match the intended change.
2. The incumbent Fabric source is installed, eligible, selected and admitted for
   the exact production service/workload, with owner-controlled capacity fallback.
3. A real generation has a terminal inference receipt, actual provider/model,
   current qualified evidence and the original operation identity.
4. An entitled browser sees the new publication without a page rebuild; an old
   or unavailable generation remains visibly degraded/archived.
5. Real disabled/unavailable/uncertain paths preserve content, do not replay
   effects or cross credential boundaries, and appear in the existing sentinel.

Source/tests alone do not prove steps 2–5. No system can guarantee an AI response
during every network, provider, authorization or source-data outage. The product
contract is bounded recovery where authorized, truthful degradation otherwise,
and no silent stale-success state.
