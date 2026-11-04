# Matrix selection questions at the Brain wire boundary

P8.T3 source integration, stacked on producer #10711 and dependent on Lab #10710.
This is not a runtime installation, enrolled processor grant or browser acceptance.
The original #10126/#61394 unknown effects and producer review refusal remain held.
The unrelated #10634 four-path publisher refusal and locked workspace are untouched.

The existing `/api/brain/chat` and `/api/brain/stream` accept only an
`options_question_reference`. The request cannot inject policy, provider, runtime,
capture or source bytes. The existing verified caller token and user id reach the
native producer. Server app state must explicitly contain an enabled
`OptionsQuestionRuntime` with a native Matrix capture and exact policy pins;
there is deliberately no default enrollment or activation. No configuration or
activation flag is changed by this patch.

Options questions use the existing quota check, then a dedicated stateless path.
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
