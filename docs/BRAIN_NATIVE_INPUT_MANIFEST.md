# Native answer input retention

The Brain message owner writes `native_input_manifest` beside `retained_context`
for deterministic native-fact assistant answers, in both chat transports. The
manifest is generated from the exact native executor receipt used for the answer.
There is no additional table, input query, model call or public read surface.

`brain.native_input_manifest.v1` preserves the rendered typed facts' canonical
entities, field IDs, owner semantic fingerprints, registry digest, units, source
identity, provenance and observed/effective/as-of clocks. Available, unknown,
unavailable, stale, not-applicable and rights-blocked states remain distinct.
Duplicate identities, inconsistent registries, missing owner metadata and invalid
fingerprints refuse the entire manifest. Existing answer and context persistence
continue with an explicit unavailable record.

The raw receipt is bounded to 256 KiB; the projected manifest to 64 KiB and 32
inputs. Overflow never silently truncates the census. A SHA-256 binds the exact
native receipt. Source values, rendered clauses, prompt strings, answer prose and
provider reasoning are excluded from the retained reference projection.

The scope is `rendered_typed_facts_only`. Owner relationship payloads are not
retained; their presence and resolution failures are disclosed separately.
`source_retention=references_only` is explicit: a fingerprint does not prove that
the original source vintage is retained or that it remains authorized. A future
artifact reader must resolve current rights through the canonical owner and must
refuse historical reconstruction when that owner cannot retrieve the pinned
version. This change does not expose metadata through existing history readers.

Non-native, instant-model and deep-model answers do not claim this manifest.
Their actual input instrumentation, artifact references, current-rights reads and
input-manifest comparison remain G6 work. Existing `retained_context` continues
to describe context resolution only; this separate key records the narrower
native fact census.

Validation is in `tests/test_brain_context_retention.py`, including both gateway
transports with providers unavailable. `tests/test_deploy_update_self_heal.py`
also requires future changes to the new import-cached module to restart the API.

History API reads distinguish an unavailable store from a successful empty
result. Thread lists and details return HTTP 503 with no-store when the existing
PostgREST read fails or returns a malformed row container; a genuinely empty list
stays 200 and a successfully absent/foreign thread stays 404. Reads never write
or rerun an answer. Tests cover all three read stages and unchanged authorization.
The shared widget preserves its last successful list with a visible unavailable
notice and read-only retry. It commits a selected conversation only after valid
history arrives; late reads cannot replace a newer selection, new chat or turn.
An authentication identity change clears the displayed history and invalidates
pending history reads. Denied list reads discard cached titles. These guards do
not constitute full account/draft/cache or retained-artifact-reader acceptance.

Browser fixtures cover list/detail outages, recovery, malformed details, late
responses and owner changes, plus EN/ZH desktop/tablet/390px/320px doubled text,
keyboard retry and 44px touch targets. They do not prove live two-principal access.
The current-rights artifact reader and exact production proof remain G6 work.
