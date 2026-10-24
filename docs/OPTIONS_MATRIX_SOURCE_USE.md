# Options Matrix source-use decision contract (`options_source_use`)

`engine/intelligence_workspace/options_source_use.py` is the trusted **server**
implementation of the `source_use_decision` callback consumed by
`engine/intelligence_workspace/options_use.py::resolve_authorized_option_selection`.
It produces the closed seven-key response
(`status`, `binding`, `source_family`, `policy_id`, `policy_revision`,
`registry_revision`, `decided_at`) for **display** and **export** of one
already-verified `options_structure.matrix` (`options_structure.matrix/v1`)
selection, and refuses everything else. It is source preparation only: it is
not a rights authority, creates no grant, and wires no HTTP route.

## Trust model (what may answer)

Every input is injected by the server; nothing arrives from a browser:

| Input | Meaning |
| --- | --- |
| `registry` | a loaded `lib.dataos.registry.Registry` |
| `dataset_id` | the one produced source or L3 composite row this backend answers for |
| `expected_evidence_sha256` | operator-pinned digest of the exact policy bytes |
| `expected_registry_revision` | operator-pinned registry revision the policy was authored against |
| `expected_source_family` | operator-pinned genuine source family; never inferred from the request owner |
| `use_context_for_request` | the mandatory trusted server resolver that builds the `ServerUseContext` for one fresh request |
| `evidence_root` | filesystem root for evidence paths (defaults to the repo root) |
| `clock` | evaluation clock (defaults to UTC now) |

`OptionsSourceUseBackend(...)` freezes these; `backend.decision` is the
callback. The only accepted request is the server-built frozen
`options_use.OptionUseRequest`; a plain dict is refused (`request_invalid`).

### Use context (what is actually done, to whom, through what)

The adapter **never infers** a right, an output basis or a delivery channel
from the action verb. `display` and `export` are only labels: nothing about
them implies `internal_computation` or `redistribution`, raw or derived
bytes, or any channel. Instead, every decision invokes
`use_context_for_request` exactly once with the fresh server request, and the
return value must be the exact frozen type
`options_source_use.ServerUseContext`: `binding` (the request itself, all
fourteen fields), `dataset_id`, `vendor`, `source_family`, `fields`, `output`
(`raw`/`derived`), `channel`, `recipients`, `customer_id` and
`required_rights`. The context is built by an independently trusted server
snapshot/handler resolver from the ACTUAL intended output, recipients,
channel and customer — never from policy values, never from a browser dict,
never accepted as a request parameter. Its `binding` must equal every field
of the request of THIS call, type and value, nonce and both digests included
(`context_binding_mismatch`); a missing resolver, a resolver failure or a
non-conforming context refuses (`context_unavailable`, `context_invalid`).

**Honesty about Python mechanics.** Frozen dataclasses, `slots` and the
private `_VerifiedEvidence` token are ordinary Python objects: any code
holding the class can construct or copy them, so they authenticate no
provenance and enforce no server trust, and none of these objects is
"self-proving". The SHA-256 pin authenticates only that the captured bytes
are the pinned bytes. All trust lives in the audited server integration that
injects the registry, the operator pins and a genuine resolver.

The response `binding` is a fresh `request.as_dict()` per call, so the
consumer's exact-binding check holds and a decision made for one request can
never be quoted for another (fresh `request_id` nonce included). No
decision, binding, context or policy is cached or persisted anywhere.

## Decision path (all fail-closed, first refusal wins)

1. **Request shape** — `request_invalid` unless the request is the frozen
   `OptionUseRequest` for owner `options_structure.matrix` / schema
   `options_structure.matrix/v1`, with a uuid4-nonce `request_id`, bounded
   scalars, 64-hex snapshot/selection digests, positive `byte_length`, and
   action `display` or `export`.
2. **Use context** — the trusted resolver is invoked once for this exact
   request; the result must be a well-shaped `ServerUseContext` bound to it
   (`context_unavailable`, `context_invalid`, `context_binding_mismatch`).
3. **Dataset row** — resolved from `registry.all()` (never last-wins
   `get()`): `context_dataset_mismatch` (context dataset is not this
   backend's dataset), `dataset_missing`, `dataset_ambiguous`,
   `source_not_produced` (status must be `PRODUCED`),
   `source_layer_unsupported` (must be L0/L1/L3), `dataset_vendor_mismatch`
   (row vendor must equal the request vendor AND the context vendor), or
   `registry_contract_invalid` (the complete reachable produced lineage is
   re-run through `validate_registry`; `from_mapping` coerces leniently, so
   validation runs before anything is granted).
4. **Right join** — only the rights the trusted context names in
   `required_rights` are consulted, and each must independently be
   `granted` on the row (`right_not_granted`). No right is inferred from the
   verb or from another right, and no single granted flag substitutes for
   another; `purchase_access` is consulted only when the context names it.
   Every required right must carry its own lawful evidence pointer at ONE
   shared file (`evidence_pointer_invalid`, `evidence_unresolvable` for
   `DEC:`/`DSC:` keys, `evidence_pointer_mismatch` when the rights point at
   different files).
5. **Evidence capture** — the shared file is read under the evidence root by
   walking directory file descriptors from the root: every component is
   opened `O_NOFOLLOW` (intermediates also `O_DIRECTORY`), so no symlink at
   any depth can be substituted between a check and the open; `.`/`..`
   components, backslashes and control bytes refuse
   (`evidence_path_forbidden`), the final open must be a bounded regular
   file (`evidence_unreadable`, `evidence_root_invalid`, `evidence_unbounded`).
6. **Digest pin** — SHA-256 of the exact captured bytes must equal the
   operator's `expected_evidence_sha256` (`evidence_digest_mismatch`); a
   valid pointer syntax alone is never evidence, and the pin authenticates
   bytes only.
7. **Policy record** — strict JSON (duplicate keys and `NaN`/`Infinity`
   refuse), closed key set (`evidence_invalid`), then identity joins:
   `source_family` must equal the context family AND the operator pin
   `expected_source_family`. Values are opaque: equality to
   `options_structure.matrix` is neither prohibited nor evidence of provenance
   (`policy_family_mismatch`); `dataset_id`/`vendor` must match the captured
   row, `dataset_version` must join the native row `version`
   (`dataset_version_mismatch`), and `registry_revision` must equal the
   operator pin (`policy_dataset_mismatch`, `policy_vendor_mismatch`,
   `registry_revision_mismatch`).
8. **Currency** — `state: "active"` (`policy_revoked` otherwise); strict
   `known_at` must parse and be `<=` the fresh decision clock
   (`policy_known_at_invalid`, `policy_known_at_future`); the evaluation
   instant must satisfy `effective_from <= now < effective_until` — the
   upper edge is exclusive, so an old snapshot expires on the stroke
   (`policy_window_invalid`, `policy_not_current`); and `source_sessions`
   (null, or a bounded list of unique sessions) must independently cover the
   request's `session` (`source_session_excluded`).
9. **Action scope** — the policy must mention the action explicitly
   (`action_not_licensed`; no wildcards). Each scope names the exact
   `principal_id`, `principal_issuer`, `auth_epoch` and `customer_id` it
   covers and a `required_rights` mapping of native right → bounded nonempty
   rationale; the mapping keys must equal the context's `required_rights`,
   the scope's `fields` must all exist in the captured row's declared
   `schema` and must cover the context's fields, and the scope's `output`,
   `channel`, `recipients` and `customer_id` must match the context exactly —
   whatever the server actually intends, not what the verb suggests
   (`scope_mismatch`, `evidence_invalid` for malformed shapes).

## Responses

* **`allowed`** — only when every step above joins; metadata is quoted from
  the verified bytes.
* **`denied`** — when the same verified policy explicitly sets
  `allowed: false` for the action. Genuine metadata, real answer; the composed
  resolver maps it to `source_denied`.
* **Refusal** — policy/evidence failures raise `SourceUseRefused` with a stable
  code. Invalid server configuration can also raise a Python type/configuration
  exception. Inside the composed resolver either callback failure surfaces as the existing `rights_unavailable`
  callback-error path; no refusal ever invents a policy id, revision or
  family, and none releases evidence or request values.

`load_options_source_policy(...)` runs the identical capture/join path and
returns the minted `OptionsSourcePolicy` (including for an explicit deny) for
audit. `OptionsSourcePolicy` is immutable and can only be constructed inside
the module after verification — assembling one from an arbitrary dict is not
authority, and the immutability itself is bookkeeping, not authentication.

## Test surface

`tests/test_options_source_use.py` — synthetic rows, policy bytes and a
test-owned trusted resolver in test tmp trees only; positive exact scoped
join; the pinned-context binding test mutating all fourteen request fields
(nonce and snapshot included) against a context captured beforehand; fresh
per-call contexts allowing new nonces without replay; arbitrary dict/browser
contexts and missing/failing resolvers; wrong dataset, vendor, family,
version and revision on the context, row and policy; principal, issuer,
auth-epoch, customer, output, channel, field, recipient and required-right
changes; a derived export to the internal customer allowed only by an exactly
matching synthetic record/context/rights; a display needing redistribution
refused when the row lacks it; `known_at` currency against the fresh clock
and the half-open effective window; source-session coverage; stale/revoked/
ambiguous evidence; traversal and symlink escape (including a link swapped
into a previously lawful path); and the composed-resolver wiring (missing
production row → `rights_unavailable` with auth/entitlement still consulted).

```bash
python3 -m pytest -q tests/test_options_source_use.py tests/test_options_use.py tests/test_options_auth.py
```

This initial adapter supports only a named authenticated principal acting as its own customer (`customer_id == principal_id`), with the two explicit recipient classes `authenticated_customer` and `internal_customer`. Organization, tenant, public, or third-party recipient scopes require their own reviewed integration; this input contract does not grant them. Source-family values are opaque external metadata: exact trusted joins decide applicability, without a locally invented family name.

## Integration limits

- The trusted handler must independently determine the native rights required
  by its actual output and recipient scope. The adapter checks that this set
  equals the policy's set; it does not establish a legal minimum from an action
  verb. A misconfigured trusted resolver and matching policy can therefore
  agree on an insufficient set. Audit this mapping before positive production use.
- Contract validation uses the complete reachable native `inputs` DAG. Every
  reachable row must exist unambiguously and be PRODUCED; missing inputs,
  duplicate IDs, cycles and malformed rows refuse `registry_contract_invalid`.
  Each L3 row must declare inputs. Unrelated rows do not enlarge the use scope.
  An L3 result must be classified `derived`; it cannot be relabelled raw/source.
  The composite needs its OWN explicit granted rights and pinned policy for the
  actual use. Upstream grants are never inherited. Native registry validation
  does not define a recursive legal minimum; this module invents none. The
  separately audited determination must account for embedded vendor observations
  and their restrictions. Dataset ownership is not equated with request ownership.
- An evidence pointer's fragment does not select a sub-record. The digest pin
  and JSON evaluation cover the entire file. DEC/DSC shorthand is not resolved.
- Registry and pin freshness is an integration responsibility: the adapter
  rechecks the supplied Registry and rereads evidence on every call, but does
  not reload a registry file or discover replacement policy revisions. A
  long-lived backend must not retain superseded registry/pin inputs.

No production dataset row, policy, pins or snapshot/handler resolver is enrolled
by this change. The existing Theta purchase/display baseline is retained; it is
not converted into a synthetic action grant. Save/IW2 and alert permissions are
outside this callback.


## Native full Matrix display resolver

`engine/intelligence_workspace/options_matrix_context.py` provides the pure
`MatrixDisplayContextResolver`, to be injected into the existing backend. This
is local source composition; no route, enrollment or live policy is configured.

The trusted server supplies the existing native selection resolver's result,
exact `IdentityArtifactRead` and selection bytes, actual authenticated principal/
issuer/auth epoch, bytes intended for release, and an independently captured
`MatrixDatasetBinding`. The binding joins that exact SnapshotReference to a
GENUINE native dataset ID, version, vendor and source family. The Matrix JSON
itself does not contain these dataset identifiers. Missing binding refuses
`context_unavailable`; no values are synthesized from the request owner, vendor
name, storage key, policy or a similarly named registry row. Current row version
must still match the captured version, and its layer must be L3 with validated
native declared inputs. These are consistency checks; Python dataclasses do not
authenticate capture, identity, provenance, or a grant.

Actual delivery at `/api/flow?f=matrix:<ROOT>` releases the full Matrix document.
The intended fields are ALL top-level keys in its captured JSON, in sorted order.
Each object/array field denotes the ENTIRE subtree: `cells` includes every
strike/expiry, call/put OI and volume, delta OI, GEX, unusual and VEX member in the
release; `levels`, `heat_seeker`, reliability and `_build_meta` are included too.
A new top-level member requires explicit policy/schema coverage. This is an
explicit broad whole-document scope, never a projection to selection.view.metric.
The accepted Lab table/inspector show volume, OI and delta OI together and the
adapter also computes exposures; selection filters do not narrow bytes delivered.

The composite is `derived` because `engine/options_matrix.py` combines current/
prior OI, EOD volumes/history and Greeks into exposure, delta, unusual and level
outputs. That classification does not erase embedded vendor observations or
waive their restrictions. Channel is the actual Matrix display URL and recipient
is the captured named authenticated principal as its own customer. This describes
the proposed authenticated server integration; it does not claim the existing
Matrix route already enforces that gate. No Matrix export handler is implemented;
`export` refuses rather than borrowing Tape/Screener CSV semantics.

The server must independently supply `required_rights_rationale` as a nonempty
unique tuple of native-right/rationale pairs from its audited full-output use
determination. A nonempty rationale documents a server input, not authenticated
policy provenance or legal sufficiency. There is no built-in mapping from
`display`, `derived`, channel or purchase to a right. The callback's rights keys
must still exactly join the independently pinned composite policy and every one
must be granted on the composite row. The existing three rights remain separate.

`release_body` must equal the exact captured Matrix bytes. A stale/error-augmented
response, reserialization or different body refuses; a handler emitting such a
response needs a separately qualified exact-output binding. The resolver uses the native closed selection parser to join captured selection
bytes to the supplied identity coordinates, comparisons, view and hidden flags.
It checks every stable request field against the capture and handler; the fresh nonce comes
from the composed consumer and is bound in the returned context on every call.

`tests/test_options_matrix_context.py` exercises the actual native identity and
selection readers with SYNTHETIC captures, rows and policies only: full output,
nonce refresh, all stable request substitutions, exact release-body changes,
absent/wrong snapshot-dataset/version/family/mapping inputs, unsupported export,
source-layer relabel, complete/missing/ambiguous/cyclic/unproduced DAG, explicit
composite policy success, no inherited grant, raw-L3 refusal and incomplete field
scope. Positive synthetic tests establish engineering behavior only.

## Native producer and response-body composition (source only)

`engine.intelligence_workspace.options_matrix_delivery` reads the exact retained
Matrix's native `_build_meta.source_dates` and history window. It keeps the selected
OI/EOD/Greeks session distinct from a later observed OI publication. Top-level
`asof` is a build timestamp, never an invented source publication or known-at
clock. Null EOD/Greeks and an empty history window remain explicitly absent.

`MatrixInputContract` binds each native role (`oi`, `eod`, `greeks`) to an explicit
existing produced dataset/version; EOD includes the unusual-volume history.
The captured composite must be L3, with exactly those three distinct direct
inputs. The existing registry validates the reachable DAG. There is no fuzzy
dataset-name lookup, default ID, registry write, or inheritance of input grants.
Missing native enrollment refuses. Source-family and rights determinations still
come from audited server configuration, independently of the policy under test.
These caller-supplied bindings establish consistency only: the integration owner
must establish their actual native provenance. Matrix does not currently emit
input-artifact hashes, source known-at clocks or dataset IDs; this adapter does
not manufacture them or claim reproducible input-byte/PIT lineage.

`app.options_auth.resolve_authenticated_matrix_display` composes those native
checks with the existing fresh authentication, entitlement, identity/selection
and pinned source-use policy consumer. On success it returns
`AuthorizedMatrixDisplay(body, authorization)`. The body is the exact captured
bytes; the intended HTTP caller must emit it verbatim. Any reserialization or
`stale` augmentation refuses. Each call obtains fresh authentication and rights
observations; the returned object is not a reusable bearer capability.

This source helper **does not register or change an HTTP route**. The current
Terminal `/api/flow` parses/caches/reserializes JSON, and is not silently adopted
as this exact-byte consumer. Wiring that route requires its incumbent writer and
qualified genuine native contracts/policy, with appropriate review and release.
No production dataset/policy enrollment, rights grant, export, Save, database or
publisher effect is performed. Tests use synthetic contracts and policy, the
actual existing identity/auth/source-use code, and one actual Matrix builder
invocation over synthetic local Parquets. They are not production acceptance.

`app.options_matrix_http.matrix_display_response` emits the actual helper result
as `Response(content=result.body)` without JSON serialization or stale augmentation.
Both success and refusal carry `private, no-store`; refusals reveal no artifact,
token or policy detail.

The incumbent `app.main` now registers the narrow display-only
`POST /api/options/matrix/display/{root}`. Its only query fields are the native
`version_ref` and `fingerprint`; its `application/octet-stream` body is the exact
selection (1–2048 bytes). Duplicate selectors/auth headers, request encoding and
client source/configuration fields refuse. A real token/principal observation
precedes the server capture; the final helper repeats fresh authentication,
entitlement and source checks. The whole Matrix response remains bound to the
existing final consumer channel `/api/flow?f=matrix:<ROOT>`; the private POST is
transport, not another rights authority or an export/Save action.

`app.main` installs the concrete lazy `DeployedMatrixCapture(REPO)` through
`install_matrix_display_runtime`. Installation performs no data, credential or
network read. Each authenticated request reads audited deployment configuration
from the existing `config.yml` `options_matrix_display` stanza. No such stanza is
seeded by this change; the tracked config currently refuses with
`configuration_missing:options_matrix_display`.

The stanza has these closed fields, all supplied by the deployment owner:

| Field | Required actual fact |
| --- | --- |
| `source_mode` | Exactly `local_retained` or `r2_public`; no fallback |
| `root`, `vendor` | Existing identity scope `SPY`, `thetadata` only |
| `dataset_id`, `dataset_version`, `source_family` | Audited Matrix composite binding, independent of policy |
| `inputs` | Exactly `oi`, `eod`, `greeks`, each with native `dataset_id` and `version` |
| `required_rights_rationale` | Explicit audited right-to-rationale mapping for the complete delivered output |
| `registry_sha256` | Pin of exact existing `config/dataset_registry.yml` bytes |
| `registry_revision`, `evidence_sha256` | Independently pinned policy revision context and exact evidence digest |

These are server configuration, not another dataset registry or a grant. The
reader captures the existing registry bytes, checks their digest, loads the
existing `DatasetContract`/`Registry` vocabulary, resolves produced contracts and
validates the native Matrix metadata/role DAG before returning `MatrixHTTPInputs`.
Absent contracts refuse `native_produced_contracts_unavailable`; a changed registry
refuses `native_registry_digest_mismatch`. Each final helper call still checks the
actual row rights and policy; configuration never supplies an allowed decision.

`local_retained` reads only the publisher's existing
`data/live_flow_out/options_matrix/history/<ROOT>/<SHA256>.json` beneath REPO.
The publisher runs on a separate producer host; that local history's presence on
the deployed API host is UNKNOWN, and missing files refuse. `r2_public` reads only
the immutable native history key under existing `R2_PUBLIC_BASE` or
`config.yml:r2_data_plane.public_base`. It sends no credentials/bearer/cookies,
disables ambient proxy handling and redirects, requests identity encoding,
requires exact Content-Length, bounds one response buffer to16MiB and verifies
native snapshot bytes. Neither mode reads the mutable head or falls back to the
other mode, cached data or a fixture.

The reader reuses `capture_spy_identity_inputs` with its bounded FD file reader for
canonical `vendor_aliases.parquet`, `security_master.parquet` and `_receipt.json`.
It preserves the existing SPY-only receipt serialization/scope. Read completion
clocks are current observations, not historical known-at or input lineage proof.
The regular-file reader rejects symlinks/FIFOs/oversize files and checks post-read
size/mtime/ctime; registry/Matrix pins catch changed bytes. This is not an atomic
multi-file snapshot or proof against every concurrent same-size rewrite.

A per-runtime nonblocking semaphore admits at most two captures; an occupied
runtime immediately refuses `capture_capacity_unavailable`. The actual reader
holds its slot until it settles, including after its HTTP owner times out. No
queue, retry, store, alternate reader or capacity-based failover is introduced.
Named capture diagnostics are server logs only; HTTP refusals remain generic.

The prepared Terminal source POST path uses the existing verified session token
and `BILLING_BASE`, restricted to the legitimate HTTPS Macro origin
`https://www.mastermind-x.com`; it never sends that token to the Flow sidecar or
R2 and never follows redirects. It first captures exact retained R2 bytes without
JSON parsing. It then forwards only the selector and exact selection to the
native display POST. Native reads its own source/configuration. Terminal compares
returned bytes with the raw capture before emitting them verbatim. It refuses
encoding, invalid/altered/partial data and every fixture/cache/stale/head fallback.
Ordinary Matrix GET behavior remains unchanged. Qualified GET requests receive405
with Allow POST; qualified SSE is unavailable.

Terminal applies one10-second budget to authentication, incoming body, capture,
transport and response reads, including abort/disconnect. Bounded readers allocate
one buffer and do not await cancellation cleanup. Native bounds selection reads
with5 seconds and response work with10 seconds. Native timeout drops late thread
results; it cannot terminate a blocking reader thread. The concrete reader checks a6-second elapsed budget between bounded file/socket
reads and uses2-second socket/open timeouts with read1, closing responses on
settlement. DNS resolution, open and local filesystem syscalls can still stall
beyond those checks; neither Python thread cancellation nor hard all-I/O
cancellation is claimed. Such work retains its capture slot. Request timeout is
not proof that its network read was cancelled.

Local synthetic tests exercise the exact incumbent registration and installation
statements, concrete local/R2 capture and the real authorization helper. A guarded
real `app.main` import also installed the concrete runtime and served its405
method route with no-store headers, with network/DB/credential access denied and
only the observed existing read-only git identity command allowed. Its unrelated
capital-structure router logged a document-term authority startup self-check
warning and remained unmounted. This is qualified Matrix startup proof, not a
claim that every optional router or the full dependency closure passed. Next tests execute its actual
POST through synthetic fetch, including exact response bytes captured from the
ASGI test. They establish source request composition, not deployed execution,
rights enrollment, independent consequential review, release or production proof.
