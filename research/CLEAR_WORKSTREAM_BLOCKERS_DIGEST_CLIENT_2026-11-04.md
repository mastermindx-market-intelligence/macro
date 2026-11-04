# Authenticated digest client and deterministic asset delivery

This continuation uses the settled server publication 7b3a8d4049fa00f3e498589b5468e82a2d2dc0a3 as its exact base and keeps the original #10597 integration carrier. The earlier server qualification above remains evidence for that immutable source. This section records the additional consumer and publication work; it does not clear the non-author review, installation, P1 or production-acceptance holds.

## Account-bound client contract

The existing account component now presents explicit digest enable, withdraw and status-read controls in English and Chinese. It uses the incumbent API helper, authentication transport, account generation, preference-load sequence and panel styling. There is no new identity store, preference registry, persistent operation queue, scheduler or retry owner.

Successful GET/PUT and conflict state now include the authenticated user_id and server-derived enrollment_available. The UI validates those bindings and the strict boolean/revision contract before presenting a canonical observation. An explicit typed absence is known false with a NULL revision; an unavailable or malformed read is not absence.

The new optional expected_user_id is an assertion against the authenticated actor, not an alternate target. The UI captures it and the chosen revision before asynchronous token acquisition. Invalid assertions are rejected with 422; a changed account is refused with an identifiable 409 before any database call. Existing clients without this optional assertion retain their authenticated-actor target.

Account generation and a small local view sequence reject late presentation callbacks. An old GET or enable reply cannot overwrite a later withdrawal view. Withdrawal can overtake a pending enable, remains usable while enrollment is off, and remains available when a preference read is unavailable. New positive intent requires a valid current observation, enrollment availability, no global veto and no unresolved write.

A revision conflict requires an explicit read and a new click. A lost or malformed write reply remains unconfirmed; reading current state does not prove that original request's execution or cancellation. Repeated withdrawals and new enables remain blocked while an unconditional withdrawal is unresolved. Confirmed withdrawal fences an older revision-bound enable. Closing/reopening the account panel retains this uncertainty in the current page.

This page-local view state does not establish global latest-intent ordering across reloads or devices, and it does not make an SMTP transaction atomically cancellable after its final authorization point.

## Existing asset publisher owns cache invalidation

lib/site_assets now derives the account release key from the exact UTF-8/LF-normalized account payload copied by its existing plain-asset owner, bakes that key into the existing theme loader, and lets the incumbent HTML optimizer derive references from the final served theme/account bytes. The loader's singleton, asset root, progressive-boot behavior and authentication remain in place.

Final account payload: fec5541f828b26646cc90de6eec90656174ee60de11dc87bf9c88906dce7615c.

Final theme payload: 8ca5bdfdb903942656eebe9d1a7741d3bbeccae5537eaca648ba230d072b80fb.

The complete scan covers 14,027 tracked/generated HTML inputs including the four existing plain-copy template pairs. Exactly 13,972 HTML paths require changes: 13,972 theme references and 6,867 direct account references. There are no foreign queries among the selected references. Jinja render inputs retain bare references for the established optimizer; no versioned account/theme URL was found there.

Application was fenced by the complete dry-run preimage manifest. Only the selected script src attributes changed; all other markup and execution attributes remain byte-for-byte identical under per-file neutral-content checks. All postimages and four canonical/generated HTML pairs matched, and a second unchanged optimization pass produced no further changes. The reference manifests retain every selected path and URL without the hosted API's 3,000-file truncation.

Two later source-comment clarifications in templates/theme.js do not change the generated payload: emit_theme_js output was checked equal to the already-qualified site/theme.js. The original asset-test receipt retains the source hashes actually tested.

The complete generated scope remains visible. Macro #10692's separate authority correction and genuine non-author-review hold remain relevant to an authoritative >3,000-path gate. No gate cap, scope limit, CI budget or held authority implementation was changed or transplanted into this digest branch.

## Added qualification

| Scope | Result |
| --- | --- |
| Tests-only new API/client baseline | Recorded expected failures before the consumer/API implementation |
| Existing account Node suite | 102 passed, 0 skipped |
| Existing billing/digest/API/real PostgreSQL owner step | 208 passed, 0 skipped |
| Existing asset owner/optimizer/lane-order suites | 130 passed, 2 pre-existing weekly-workflow structure skips |
| Actual Chromium account component → real ASGI digest routes → isolated PostgreSQL | Six cases passed |
| Real HTTP warm-cache delivery using unmodified generated HTML and JS | Six page forms passed |
| Complete generated-reference closure | 13,972 exact changed HTML paths; fixed point; unchanged unrelated markup |
| Full differential contract gate against 7b3a8d4 | Exit 0; 0 introduced, 0 inherited; 718.98 seconds; tree 274e7371058440239852a8b818e0ee08e0f088f2 |

The six authenticated browser cases cover enable/withdraw, stale revision requiring a fresh read and click, actual committed withdrawal with a lost reply, delayed-token account mismatch refused before storage, Chinese enrollment-off withdrawal, and withdrawal after a read failure. Identity is a synthetic dependency seam; routes, component bytes and PostgreSQL behavior are real. No live account, database, mail service or scheduler was involved. English and Chinese screenshots are retained.

The first browser harness stalled because Playwright awaited the function returned by a token-delay setup expression before any click. Its exact owned process received one SIGINT and terminated; fixture/browser cleanup completed. The final reporting KeyError happened after fixture cleanup. The original partial receipt and cancellation remain preserved. A corrected bounded harness returned six passes; the partial run is not counted as full success.

The cache experiment used one loopback origin and retained each case's browser HTTP cache across deployment changes. No Playwright request routing or cache-disabling control was used, and service workers were blocked. Exact old 7b assets were seeded with immutable cache headers; repeat old loads and an old-reference control after the deployment switch showed genuine cache hits with no corresponding server requests. Updated pages selected and received the exact new payloads, then reused those new cached resources.

The six actual HTML page forms cover root theme-loader, root direct account, nested theme-loader, nested direct account and direct forms at depths two and three. Actual DOM script URLs, payload hashes, browser transfer sizes, cache events and server requests are recorded. This proves bounded delivery under the fixture's cache and restrictive external-dependency CSP; CDN query-key handling, deployed headers and production authentication remain separate acceptance evidence.

The final cache receipt is 18ba51aa20674a26736d355c95ee86f6d56cc227bcc808c49efd7f9c91a5e429; all six cases passed and the fixture server stopped. The final applied reference receipt is 122155c3c5eaf9b4d3f3792023add1db3c960973fd5cf873e4e8d7eabaa1b54d. The complete implementation/test tree and all evidence digests are bound in this directory's publication manifest.

## Source integration and outstanding acceptance

The client is implemented and qualified in this carrier. It neither copies nor modifies the held auth-union workspace/branch, nor replays P1's unresolved original command. A shared canonical filename is not a live-writer grant over independent work; later auth composition must use its resolved exact source and regenerate cache keys from the combined payload.

The Browser connector's single installed-read attempt returned: “Browser access requires the originating browser context.” No browser runtime, tab or authenticated context was obtained. Together with the recorded unavailable Supabase tool bindings and absent existing reader credential, installed catalog/API qualification remains unproved. The isolated local browser tests do not substitute for that access.

Next executable acceptance obligations remain: genuine non-author review; resolve the original P1 request and complete its address-suppression/retry policy; establish the trusted per-account nightly cursor under its canonical owner; qualify installed definitions and PostgREST through an admitted route; deploy through the established owner with enrollment held; then prove authenticated opt-in, one authorized delivery, duplicate suppression and withdrawal on the actual product path. Preserve the original auth and rotation-snapshot UNKNOWN carriers and fixed protected runtime-reader boundary.

This is a source-qualified continuation, not protected merge, installation, production enrollment, delivery acceptance or a claim of a durable running worker.
