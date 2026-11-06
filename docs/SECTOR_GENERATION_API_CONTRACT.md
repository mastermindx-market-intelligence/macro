# Coherent Sector generation HTTP envelope

Status: source integration under PR #10780. The concrete verified-snapshot reader is implemented and locally tested; application mounting and production binding remain inactive. No live API or beta acceptance is claimed.

## Existing authorities

`app/sector_generation.py` owns the HTTP envelope only. It calls the existing `app.regwall.regwall_check` and then `app.paywall.paywall_check` for every required canonical resource, using the current site-access policy. It does not create a new authentication, entitlement, cache, manifest resolver, publication, collection or watch-state owner.

`create_router(reader=None)` exposes `GET /api/sector-generation`. The sole query parameter is `audience=preview|entitled`; omission selects preview. Repeated audience parameters, unsupported values and all other query parameters return400. A client cannot choose a source path, origin, domain, root or generation.

An injected reader takes precedence. Otherwise the application owner may install `app.state.sector_generation_reader`. No usable reader means503. The application must bind the existing publisher's verified read facade and canonical pure projection; this HTTP module does not implement either. Caddy excludes `/api/*` from static-asset gates, which is why this route explicitly enforces the incumbent gates itself.

## Required resource checks

The preview audience requires authorization for all five resources:

- `/sectordata/sector_central.json`
- `/sectordata/sector_cycles.json`
- `/basketdata/baskets.json`
- `/basketdata/si_handoff.json`
- `/basketdata/action_board.json`

The entitled audience requires the same five plus `/premiumdata/sector_central.json`. Preview describes the representation; it does not make these underlying resources public. Current unknown paths retain the incumbent premium default. The premium-data resource remains subject to the existing early-enforcement rule even while the global paywall switch is off. A future policy applying specifically to the action-board resource must also be honored.

For each gate call, the server supplies the canonical `X-Original-Uri` and `X-Original-Kind: asset`, keeps the caller's session cookie, and drops all other caller headers, including document-classification headers. Spoofed resource paths or document hints cannot change which resource is checked. The incumbent registration and entitlement decisions run in their existing order. The reader is called exactly once only after every required check allows access.

## Trusted reader and response

The reader implements `read_selected_generation(SectorGenerationRequest(audience))`. It returns `SectorGeneration(payload, source_session, published_at, qualification)` or a structurally equivalent object. The payload is the already authorized projection, including its public `receipt`.

The response schema is `sector_generation.read/v1` and contains audience, the three source facts, and projection. The transport validates:

- `source_session` is a real calendar date in `YYYY-MM-DD` form.
- `published_at` is a valid timezone-aware ISO timestamp.
- `qualification` is exactly `accepted`, `stale` or `degraded`, matching `SectorViewReceipt`.
- All three facts exactly equal their values in `projection.receipt`.
- The native data and receipt schemas match, and `projection.data.audience` equals the requested audience. An entitled projection cannot be returned under a preview envelope.

The outer fields are copied from the matching receipt. There is no poll-time substitution or new freshness calculation. The projection may explicitly disclose an older common Brief baseline while its core cohort describes a later source session. That transitional state must remain visible; it is not full fresh-input acceptance. A `current`, `closed` or `unavailable` word is not a successful projection qualification. Unavailability is an error response.

The final encoded HTTP response must contain only finite JSON and be no larger than4MiB. The envelope materializes the outer mapping and serializes the response bytes; it does not claim that a shallow mapping copy makes every nested object immutable. The trusted reader must resolve one selected generation and project the requested audience from its captured, verified bytes. Calling the resolver separately for each artifact would violate the intended binding.

## Failure behavior

All responses carry `Cache-Control: private, no-store`, `Vary: Cookie`, `X-Content-Type-Options: nosniff`, and `X-Robots-Tag: noindex, noarchive`.

Failures use `sector_generation.error/v1` with a closed code. Invalid query is400. Existing registration/entitlement/resource denials preserve401/403/404. Incumbent service failures and unavailable/corrupt readers return503; oversize results use the dedicated too-large code. There is no redirect, empty successful fallback, legacy-file fallback, diagnostic path, manifest, private hash or exception message in the error body.

Reader resolution, property access, mapping conversion and JSON serialization all share one closed exception boundary. A throwing capability property, malformed result mapping, deeply nested JSON or provider-reader exception therefore cannot escape as an uncacheable-header-free500. The envelope logs only the exception class. It does not retry a read or publish in response to failure.

## Qualification and original-run reconciliation

The API input was independently recovered from commit `bd7c4437992cca7db8d9fbacbd9fcf532baa590e`, patch SHA-256 `19837828d575e201a1c90b540ac1f68e20107eafb82864ef42affd8b23e03c43`.

The later `macro-always-on-20261106-c3-sector-api-repair-01` run terminated. Its exact owned-process receipt proves verified identity, completed census and zero residual processes; its past private file effects were not enumerated. No worker repair/test result or effect absence is claimed. Its packet assigned a private worker workspace and reserved canonical PR10780 integration for the parent. The parent independently integrated the recovered candidate after exact canonical-target, source, operation-marker and patch readback. The failed provider run was neither retried nor accepted, and no private worker workspace was replaced.

Parent changes add the missing action-board gate, align metadata with the actual projection receipt, and close the entire reader/serialization error boundary. Tests retain the original auth, spoofing, bounded-response and source-clock checks, and add independent expected-resource lists, real temporary-policy action-board denials, invalid-date/clock/state and contradictory-receipt cases, hostile properties/mappings/deep JSON, and actual canonical projections carrying an older disclosed Brief baseline. The final parent run of the API and native-projection suites passed 84 tests. Its 67 warnings were framework/per-request-cookie deprecations and pre-existing temporary-directory cleanup warnings; no failed test was waived. The audience/schema mismatch was additionally repaired and covered before this final run.

## Installation still owed

`app/sector_generation_reader.py::SectorGenerationReader(generations_root=absolute_private_root)` now connects the single verified snapshot facade to shared Sector semantics, canonical audience projection and this HTTP envelope. The complete-response encoder is shared with admission preflight; the original publication receipt and current evaluation clock remain distinct. See `research/market_os/SECTOR_GENERATION_READER_CONTRACT_2026-11-06.md`. The parent still must produce qualified live Sector outputs, mount this router through the existing application owner, connect the incumbent Terminal BFF, satisfy required CI and release controls, and prove the authenticated beta journey. Unit fixtures and a locally constructed projection are not a running production data source.

## Complete native projection

The canonical projector now includes allowlisted core and reconstructed history in the same authorized data hash as Brief and board. Identity mappings, source dates, measured counts and response bounds are validated before publication. See `research/market_os/SECTOR_COMPLETE_NATIVE_GENERATION_2026-11-06.md`. This does not activate a runtime reader or Terminal binding.
