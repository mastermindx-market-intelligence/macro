# WTI production evidence bindings (T005.S7)

This source extension depends on the held T005.S5/S6 interfaces at `31fd21cf`.
It is not installation, supplier enrollment, formal approval, or numeric
Scenario acceptance. It changes neither #10614 nor #10619 and supplies no live
configuration or evidence objects.

## Existing entry points

`scripts.collect._run_one` supplies `native_session_reader()` only when it
constructs the Yahoo adapter. Other adapters retain their existing constructor.
The callback reads already retained facts for that exact returned observation;
it never performs a provider fetch or derives dates from a price frame.

`app.main` calls `configure_wti_sessions(app)` beside the ontology router.
The installed callable uses the same server-selected `MACRO_REPO` publication
root as that router. Startup performs no evidence-object read. The authenticated
Scenario POST invokes the selector only through the existing runtime subject
construction and admission checks.

## Two independent, explicit deployment selections

- `WTI_NATIVE_SESSION_FACTS_SHA256`: the 64 lowercase hex SHA-256 of an already
  retained `yahoo.wti_native_sessions.v1` object. Its existing closed schema
  binds provider, merged and adapter-context images, native label/session
  mapping, completion, future sessions, clocks and source use. The callback
  requires the facts to be known by the observation; capture separately checks
  their labels and clocks against its actual frame.
- `WTI_SCENARIO_ADMISSION_SHA256`: the SHA-256 of a **separate, independently
  authorized** admission object. Its closed JSON shape has `schema` equal to
  `ontology.wti_session_admission.v1`, `subject` equal to all five fields of
  `WTISessionSubject`, `native_facts_sha256`, and `known_by`. The latter fields
  retain the existing `WTISessionAdmission` semantics. The runtime additionally
  requires the matching facts digest and admission after export/TXI completion
  and no later than the selected cutoff, before price decoding.

Both selections read `<data>/yahoo/.availability_capture/objects/<digest>.json`
under the existing Yahoo owner; there is no new store or latest-object scan.
Selections are fixed when each callable is constructed. New data requires a
new explicitly qualified deployment selection; old admission never carries to
a changed observation, parquet, TXI generation, manifest or cutoff.

**A content hash proves bytes, not authenticity.** Whoever installs these server
configuration pins must first qualify the actual supplier/issuer, factual
mapping, completion, future sessions and source use under existing release and
installation controls. This module does not sign, create or authenticate that
evidence. Neither export content, a request body, commercial licensing alone,
nor an arbitrary file discovered on disk can install an admission pin.

Absent pins, missing objects, malformed JSON, duplicate keys, nonfinite values,
oversized files, symlinks, digest mismatches and unmatched subjects return no
facts/admission. Numeric Scenario remains unavailable under its existing typed
response. No production pins are provided by this change.

## Source qualification boundary

`tests/test_wti_session_bootstrap.py` uses isolated synthetic objects to exercise
the actual collection constructor and actual `app.main` installation statements
with the authenticated route. It does not start unrelated API services, call a
vendor or install this code. Positive fixture behavior proves composition only;
real supplier evidence and protected release/live acceptance remain separate.
