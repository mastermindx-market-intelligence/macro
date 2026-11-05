# Government Revenue serving attribution

This implements the source-observability portion of original V2/A42. It supplies
evidence for diagnosing the two existing entitled dossier reads. It does not
authorize a production request wave, establish a performance result, change the
accepted corpus or relax the original targets.

Successful responses from these routes include the following headers:

- `/api/government-revenue/dossier/company/{ticker}`
- `/api/government-revenue/company/{ticker}/awards`

| Header | Meaning |
| --- | --- |
| `X-GovRev-Generation` | The validated public dossier `content_id` also present in this response body. |
| `X-GovRev-Cache` | `hit` when the existing twin-stat cache was reused; `miss` after the existing full validation accepted and cached the generation. |
| `X-GovRev-Process-Epoch` | Opaque, process-local correlation value. Stable within a running process, different across forked workers or fresh process starts. It is not a PID or an authentication identity. |
| `Server-Timing` | Fixed phase durations in milliseconds, with three decimal places. |

The timing names are `govrev_stat`, `govrev_lock_wait`, `govrev_read_decode`,
`govrev_validate` and `govrev_route`. The last span contains the route function's
work, starting after the router's authentication/entitlement dependencies. It
excludes dependency execution, FastAPI serialization, proxy/network time and
browser rendering. Phase values are not additive end-to-end latency. Read/decode
includes the existing twin-byte comparison. Validation includes the existing
schema/content-ID checks and cache update. A warm hit reports zero for the two
unexecuted read/decode and validation phases.

Observations belong to the current call and are never a shared last-request
record. Failed authentication, invalid parameters, unsupported companies,
cursor failures and artifact failures have no success-attribution headers.
Existing response status/body/cursor, router-level entitlement, twin checks,
cache keys/contents/locking and API `private, no-store` behavior are unchanged.
Only fixed duration names, cache state, public generation ID and opaque process
epoch are emitted. No raw paths, file times, process IDs, account identifiers,
query/filter values, bearer tokens, raw source bodies or new logs are introduced.

The process epoch is salted with process-local random bytes and the process ID,
so a pre-fork import does not make workers appear identical. It does not replace
independent runtime worker/corpus/twin evidence. No `Timing-Allow-Origin` or
cross-origin exposure setting is added.

The contract is qualified with local ASGI fixture requests and affected loader
tests. These are semantic checks, not production authentication or performance
samples. The original A42 acceptance still requires the agreed real corpus,
known cache/process/generation state, ten independent concurrent readers,
cached dossier p95 at most one second, useful initial viewport at most three
seconds with 500 ms RTT and 1.6 Mbps downlink, zero request-time source/model
fan-out, and reconciled capture/review/compute cost. Prior duplicated/warm-mixed
canaries cannot be relabeled as acceptance.

Original publisher-history, saved-workflow P2, prospective Q3, client pending-auth
sharing/c287 and other uncertain operations retain their existing carriers and
holds. This server instrumentation does not consume or replace any of them.
The exact Chrome extension-UI refusal also remains unresolved. A qualified
installed candidate and an actually admitted transport/measurement grant are
required before a new production measurement.
