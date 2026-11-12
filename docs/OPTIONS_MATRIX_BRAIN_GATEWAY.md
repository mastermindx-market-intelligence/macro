# Matrix selection questions at the Brain wire boundary

P8.T3 source integration, stacked on producer #10711 and dependent on Lab #10710.
This is not a runtime installation, enrolled processor grant or browser acceptance.
The original #10126/#61394 unknown effects and producer review refusal remain held.
The unrelated #10634 four-path publisher refusal and locked workspace are untouched.

The existing `/api/brain/chat` and `/api/brain/stream` accept only an
`options_question_reference`. The request cannot inject policy, provider, runtime,
capture or source bytes. The existing verified caller token and user id reach the
native producer. Startup installs a lazy server-only runtime constructor after the native Matrix
display constructor. Each Options request resolves the existing Brain configuration
into a typed runtime; absent, invalid or OFF configuration refuses. No configuration
or activation flag is changed by this patch. Native source/evidence rights remain
freshly checked, independently of configuration pins.

Options questions prepare and validate native source/entitlement/policy before
the existing quota check, then dispatch through a dedicated stateless path.
Guest, missing token, research, other source attachment, images, history or thread
requests refuse. No tool loop, persistent thread, generic source fallback or
provider fallback runs. The stream endpoint buffers the final checked response
and emits normal meta/delta/done events; it does not stream unchecked model text.

The actual first selected Anthropic-compatible client, model and public base URL
identify the destination. Unsupported provider clients refuse. A request-scoped
public SDK clone uses retries=0, no ambient proxy or redirects, and its own HTTPX
transport. Shared clients and their credentials are neither changed nor logged.
The wire guard validates the final POST URL, model and complete serialized bytes,
strictly extracts exactly one source attachment, freshly reauthorizes the native
producer, and delegates only those bytes once. It refuses duplicate JSON keys,
ambiguous fences, tools/history or a second attempt. It is not an exactly-once
network journal. If transport started but a complete model result was not
recovered, the route returns EFFECT_UNKNOWN/retry_allowed=false. It never
silently retries on another provider or sends through the generic route.

Qualification must include actual installed SDK serialization over inert HTTPX,
wrong-destination/model/source negative tests, fresh entitlement/policy refusal,
no-retry behavior, both gateway routes, and unchanged ordinary Brain behavior.
Actual Lab/native-producer integration is separately bound to immutable Lab bytes;
stub SDK/unit fixtures alone do not prove that composition or live access.

Remaining release obligations: accepted independent review of the changed risk;
protected integration of both existing dependencies without disturbing their
original effects; exact enrolled policy and registry revision for each destination;
qualified OFF deployment; subsequent authorized activation and authenticated EN/ZH
Matrix→Brain selection behavior with real clocks and explicit missing data.
No provider probe, live send, account enrollment or new scheduler is authorized by
this source candidate. IW2 remains the sole Plan Save/reopen implementation.

## Retained qualification and limitations

Parent qualification found and reproduced two failures in the raw Fabric wire
candidate: a mutable request stream could change after authorization, and an
endpoint literal was normalized. The parent repaired both, rebuilding a fresh
HTTPX request from returned checked bytes and rejecting normalized endpoint
substitutions. Closing or an unsupported async attempt also consumes the guard.
The raw worker candidate is REPAIR_REQUIRED, not independently approved.

The installed Anthropic 0.86.0 / HTTPX 0.28.1 combination is exercised with real
SDK serialization and inert transport. The worker used a different HTTPX2 SDK;
that runtime is not claimed supported by this candidate. The existing Brain CI
job pins Anthropic0.86.0 and runs the three added suites; no workflow is added.
Native Lab4bda8a8f + producer + SDK composition passed both chat/stream channels:
one exact1984-byte inert request per channel and zero additional requests after
fresh entitlement revocation. Each channel performed8Auth/4entitlement reads.
A fixture-clock omission initially refused rights; the gateway now passes the
trusted native capture clock (production None remains actual UTC). These are
source fixtures, not real customer authorization or production observations.


## Startup and withdrawal (source only)

`app/options_question_runtime.py` installs no reader, credential or policy store.
It reuses `options_matrix_display_runtime` and the existing Brain config loader.
The optional server-only `options_question_gateway` block has exactly `enabled`
(boolean) and `policies` (1–32 exact destination/evidence pin rows). Each row has
provider, endpoint, model, evidence_sha256, registry_revision and
required_rights_rationale. Invalid rows, duplicate destinations, nonliteral URLs,
empty rationale or ambiguous configuration refuse the whole runtime. There are
no shipped enabled settings or fabricated policy values.

Configuration is resolved for each request and rechecked before/after final native
wire authorization. OFF, invalid pins, changed capture, or reinstalling/removing the
runtime source invalidates an earlier prepared turn. Ordinary Brain requests do
not consult this optional runtime. Options stream responses never register with
`brain_runs`; they cannot recover through the generic run registry. A prior
successful request does not authorize a future send. As with all synchronous
checks, this is not an atomic distributed revocation/remote-effect transaction.

Source qualification executes startup installers, the actual extracted HTTP
functions, immutable Lab4bda adapter, native source/Auth/policy and Anthropic0.86
serialization over inert HTTPX. Both routes send once; absent, invalid, OFF and
preexisting revoked-entitlement cases send and debit zero additional times.
Configuration withdrawn during final native authorization is also withheld.
These fixtures do not prove live rights, a real provider response, installation,
activation, Paper parity, authenticated customer acceptance or persistence.


Independent Fabric review of93fd returned REPAIR_REQUIRED: repeated access to a
mutable dispatch payload property, missing Content-Type, unconstrained headers,
and unpinned HTTPX. Four inert regressions reproduced the wire/header findings.
The repaired guard sends the single checked local bytes value, requires JSON
Content-Type, rejects duplicate/unlisted headers, and retains only the supported
SDK's header names. CI and runtime qualify Anthropic0.86.0/HTTPX0.28.1 explicitly.
The SDK's request-options DEBUG logger is suppressed only in the Options send's
context, with an inert regression proving ordinary logging still works afterward.
This parent repair is not represented as the earlier independent review's PASS;
changed startup/withdrawal/pre-quota/wire risk needs scoped review.
