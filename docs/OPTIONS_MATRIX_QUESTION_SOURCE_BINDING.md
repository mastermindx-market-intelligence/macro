# Exact Matrix question source binding (source-only candidate)

This extends the original #10126 source-use owner. It creates no reader, route,
policy store, provider client, credentials, enrollment, install or activation.
Original #10126 review61394 and its publication/lease uncertainty remain held.
The #10634 managed publication refusal is unrelated and is not retried here.

## Dependencies and trust boundary

- Exact producer dependency: Macro `4bde86ddc8916c9bc5e6e670805ed2a76ca92e18`
  (#10126). This branch is based on it for source composition, not approval.
- Lab adapter: #10710 `0e87a5917ac5c614e09f0c882e252885fc3a722f`,
  `engine/neuralweb/options_selection_context.py`. The Lab owns that file/tests.
- Existing gateway: #10634 `09865cef3d4b49563e5739684d59a37ab9ecc4a5`.
  Its HTTP routes are `/api/brain/chat` and `/api/brain/stream`; provider selection
  and fallbacks remain with that gateway. No gateway/auth files change here.

`prepare_matrix_question` receives the existing `MatrixHTTPRuntime` capture and
trusted `QuestionPolicyBinding`, authenticates the actual expected principal
before capture, validates the native provenance/DAG and exact selection, then
composes the Lab resolver with the incumbent source-use backend. The fresh
Options entitlement still comes from the existing auth/product predicate.
The entire native field set is conservatively scoped; view filters do not narrow
rights, and the question attachment does not claim metric/quote availability.

All injection is server-owned. Python dataclasses, browser hints, model prose
and caller-supplied policy strings authenticate nothing. The optional adapter
argument exists for audited integration/testing; it is not an HTTP parameter.
The default import fails closed if the independently owned Lab source is absent.

## Versioned source-policy extension

Legacy policy shape and display/customer export semantics remain unchanged.
`schema: options.source_use.question/v2` explicitly selects the new closed form.
Only `actions.export` is legal in that form; it adds one exact `processor`
object with **provider**, **endpoint**, and **model**. The endpoint is a literal
HTTPS URL without user information, query, fragment or wildcard. The intended
channel must be the actual Brain chat or stream route, and recipients must be
exactly `authenticated_customer` plus `external_processor`. The same exact tuple
must come independently from the trusted server context and the pinned policy.

The extension retains all original native registry/right/evidence-pointer,
evidence-hash, revision, dataset, source-family, principal/session, finite policy
window and source-session checks. No rights are inferred from `export`, a model
name or commercial licensing attestation. No live v2 policy is supplied here.
An existing display policy cannot pass this path. A fallback with a different
provider, model or endpoint needs a fresh preparation against a matching policy.
Unknown destinations remain unavailable; this code does not guess the deployed
processor from configuration defaults or call external models `internal_customer`.

## Two distinct request-time checks

1. Preparation validates exact immutable capture/selection and policy for the
   intended processor. It releases only the Lab's ephemeral membership prompt
   to the trusted gateway process. This is **not** external disclosure permission.
2. The gateway assembles its actual outbound immutable bytes. Immediately before
   its existing transport call it invokes `authorize_dispatch`, passing the
   **actual** processor/channel and a trusted strict payload attachment reader.
   That reader must parse the real wire body, return exactly one source block,
   and refuse duplicates, missing/ambiguous attachments or altered serialization.
   The block must equal the prepared bytes. The guard freshly rechecks Auth,
   product entitlement and pinned policy; it refuses late or backwards clocks.
   Its ten-second window includes capture, preparation, Auth and final validation.
   It hashes and returns exactly the checked immutable payload and destination.

A preparation is consumed by its first final-check attempt, including failures;
reuse cannot produce a second authorization. A fallback gets a separate fresh
preparation. This is process-local consumption, **not** exactly-once network
sending, a durable journal or a transferable capability. The gateway must send
only returned bytes to returned destination immediately, without later queuing,
mutation or grant reuse. Raw prompt/capture, token and authorization must never
enter persistent context/history/logs. The earlier prompt's source-decision clock
is preserved as an observation; final fresh checks do not rewrite those bytes.

Actual dispatcher extraction/injection and immediate transport integration remain
unmounted. There is no claim that an unaudited caller obeys the protocol. Tests
use inert send spies and synthetic policy/capture/Auth, never a provider call.
The actual source-path composition was also exercised with the immutable Lab
adapter, not just its callback-signature fixture.

## Acceptance remaining

Source checks must cover wrong principal/session/hash/selection, display policy,
unknown or changed processor/fallback/channel, payload substitution, missing
capture, stale/revoked entitlement/policy, late result and reuse before an inert
send. Preserve existing display/source-use/Auth suites. Independent changed-risk
review, protected source integration of both dependencies, real dispatcher
binding, installed exact policy/registry enrollment and authenticated EN/ZH
consumer behavior remain separate. All four runtime switches stay OFF.
