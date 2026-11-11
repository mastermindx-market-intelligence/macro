# Capacity Fabric Router Observatory
Date: 2026-11-10
Operation: capacity-router-observatory-20261110
Parent context: WS:EXECUTIVE-CAPACITY-FABRIC (source plan; organizational linkage not yet updated)
Procedure: Mastermind protected master 76cca6bf0d4f54c1c4a732726a16c70dbe8ed679, Skillpack 1.0.1, bootstrap major 1.
Source owner: macro; isolated GitHub-native branch feat/capacity-router-observatory-20261110, base 7e115b6f1f10832b4b123149215ea7a041279753.

## Outcome and completion
Deliver a sophisticated authenticated router interface at admin.mastermind-x.com showing actual Capacity Fabric providers, models, routes/lanes, concurrent requests, token usage and downstream consumers where identity exists. Complete means source squash-merged by the permitted GitHub path, installed on the VPS, connected to the incumbent live router, and verified through the authenticated browser and actual telemetry. A mock graph, open PR or green test alone is insufficient.

The current assignment explicitly authorizes direct squash merge and VPS deployment. Actual enforced GitHub/CODEOWNERS/security requirements and recorded holds still apply. No blanket external technical-review ceremony.

## Established inputs
- Admin is the existing stdlib Python + vanilla JavaScript console in macro/admin.
- Existing public domain, signed-session auth, Caddy, admin.service and macro-update deployment remain the owners.
- Connected Studio carrier is verified as m2studio. Existing configured VPS SSH identity authenticated to the admin host without exposing secrets.
- Incumbent Capacity Fabric is the M2 loopback unified router on port 8313, with /healthz, bearer-protected /statusz and /v1/models. Source provenance and instrumentation are being reconciled before any runtime change.
- Open-source architectural references: LiteLLM metric decomposition; Langfuse aggregated/expanded trace graphs; Helicone session paths; OpenTelemetry trace/parent identifiers. Reuse existing web stack and router instead of another gateway or tracing database.

## Work tree
1. Discover exact router source, current telemetry, live writers and private transport; map measured/unknown semantics.
2. Implement a bounded secret-free read projection in the existing admin API. Reuse canonical request/route data. If necessary, extend the incumbent router's observational instrumentation without changing selection, credentials, retry, queue or admission.
3. Build a responsive dark router workspace: animated topology, provider/model/lane/consumer drilldowns, throughput/history, concurrency and health, request explorer, detailed lineage and timing inspector, filters, pause and freshness.
4. Qualify actual data semantics, authentication, degraded/stale states, bounded memory/requests, keyboard/reduced-motion behavior, desktop/mobile rendering and affected regression tests.
5. Publish one coherent change, use the current authorized squash release path, deploy exact source through existing owners, prove live data and browser workflow, and save final evidence here.

## Data and interaction contracts
- Never manufacture agents, parent-child relationships, usage, throughput or capacity. Missing values are unknown, not zero.
- Explicitly distinguish requests/streams, observed token totals, final/provisional usage, and inferred versus recorded downstream identity.
- Preserve requested versus served model, route/pool identity, concurrency, cooldown, failures and attempt lineage.
- Read-only interface; no provider/model settings, scheduling, credential changes or destructive controls.
- No prompts/completions, API keys, raw provider error payloads or private account identifiers in browser telemetry.
- Stable node selection; bounded polling or existing event transport, no overlapping refreshes; stale/disconnected indicators; hidden-tab and reduced-motion handling.
- Runtime data remains outside Git; no second router, quota store, agent registry, lifecycle owner or retry plane.

## Execution decision
Principal retains architecture, tightly coupled implementation and deployment under LOWER_TOTAL_OVERHEAD and UNIQUE_APPROVED_ACCESS while source/transport are resolved. A native reasoning child provided architecture synthesis only, with no writes or execution. WHY NOT FABLE: no additional strategic principal is needed. Reassess separable paid-Fabric labor once exact contracts are frozen; never duplicate a live worker.

## Evidence and frontier
Implementation milestone: native admin workspace, authenticated API, bounded observer, private SSH projection, retained-history/epoch fencing and exact-release staging helper are implemented. Focused 23-case Python suite passes; Python and JavaScript syntax checks pass.

Runtime census: the incumbent router is a single M2 process at port 8313 with 20 configured routes and four aliases. Existing source is a locally retained Mastermind build with production wire patches; the recorded base commit is unavailable on remote GitHub. The deployment will preserve that exact immutable release and its gateway/routes/wire/auth hashes, then add the macro-owned observer and replace only the service factory reference. No primary host checkout or credential file will be edited.

Key runtime correction: OpenAI and Responses translators synthesize missing usage as zero. Original parsed provider usage is captured through observational translation hooks; translated downstream zeros are never treated as provider reports. Unknown input/output remains unknown. Request identity is pseudonymous and only recorded parent IDs establish agent relations.

Next: publish this implementation checkpoint; run the 12 closed-transport cases against the exact staged gateway and translators; complete browser layout/interaction review; inspect current actual GitHub controls; squash and deploy through incumbent owners; verify live consumer telemetry and save receipts. This milestone is not completion.


## Qualification before release
- 25 focused Python tests pass, including concurrency, cancellation, fallback identity, byte preservation, original-error preservation, fragmented SSE, usage replacement, privacy canaries, missing usage, bounded compaction, atomic ingestion and stale/epoch fencing.
- All 12 cases against the exact incumbent gateway/translators pass: Anthropic, OpenAI and Responses; streaming and non-streaming; reported and absent usage. Status, headers and response bytes are identical with and without the adapter. Tests use only a closed in-memory HTTPX transport and isolated credential fixtures.
- Existing gateway hash: d3d325a5e8342409ec1af74c696914757538d279ddb5e8441c6adce5f90deafc. Existing plist hash: 6af3e3ab18b393568ad0ae07a00c1e96cc88184e83b48e0cf70a2f37d33397b8. Staging preserved and verified 749 source files.
- Current main advanced to 45aea60fa7254ce185752dbc25e749d0fa6b2d6f through unrelated data work; all three edited incumbent admin files are unchanged from the task base. Main is unprotected and its sole listed ruleset is evaluate-only. Recheck the actual candidate before the authorized direct squash.
- The connected browser has an extension UI blocking control. The isolated browser reaches the real admin sign-in page but has no authenticated session. Local preview is not network-accessible from that browser. No browser authentication or security control has been bypassed. Authenticated CLI verification can reuse existing server credentials in memory; visual live verification requires an existing browser session or secure user sign-in.
- NEXT: ready PR, permitted direct squash, existing VPS deployment, exact observer overlay activation, live projection and real request proof, then final evidence readback. No deployment or acceptance is claimed yet.

## Resumption: deployed telemetry and observation integrity
- Current Chairman assignment resumes this same dashboard project. Procedure is pinned to Mastermind protected master `d8240eb033a3025aaa119a61c2adec8fb943b27c` (skillpack 1.0.1). Original feature PR #10950 is merged at `e11afd6d8549eede47182a3fdac0c29f4fca4cfb`; no original source work is being replayed.
- Follow-up source carrier: `fix/capacity-router-observation-integrity-20261110`, based on Macro `ca1b02cd10f70fc8fe07a54ee4277fd964a2698f`. The original feature branch is finished. Current open capacity PR #10951 owns only its two CI dependency-path repairs; those paths remain with that active repair.
- Read-only live proof: existing VPS admin service is active; deployed checkout is `ca1b02cd10f70fc8fe07a54ee4277fd964a2698f`; admin files are clean. The loaded incumbent router overlay provenance binds the original feature merge. Snapshot sequence 1198 was 2.2 seconds old, with 20 routes, 19 active requests, 890 starts, 831 completed, 40 failures, 400 retained rows, zero overflow/dropped requests and two observation errors. These are point-in-time observations, not a permanent health claim.
- Native reasoning adviser identified three source-level display defects: an unknown-only minute is graphed as zero, selecting a child hides its retained parent, and provider/inspector request counts ignore active filters. Principal retains the small coupled implementation under LOWER_TOTAL_OVERHEAD; no paid/native implementation worker is active. The adviser has no source or runtime effects.
- Next bounded phase: repair these display semantics, clarify metric scopes, qualify actual production data and affected interaction tests, publish the exact diff, deliver under the existing release controls, and finish authenticated desktop/mobile visual acceptance.
- Browser control currently stops at an open Chrome extension panel. No sign-in, access control, credential or browser restriction has been bypassed. No uncertain production mutations exist.
- DONE_WHEN remains the original complete live dashboard journey, including real downstream identity only when actually reported. Source, deployment, API proof and browser acceptance remain distinct.

### Follow-up qualification
- Implemented explicit unknown-minute chart markers, retained-parent navigation with filter reset, consistent provider/inspector traffic filtering, a global-summary scope label, and a truthful route-cooldown label. Stale chart/history windows stay anchored to the snapshot.
- Local qualification: 26 Python cases and seven actual-JavaScript behavior cases pass; JavaScript syntax passes. The first new Python fixture used an incorrect store method; it was corrected to the real begin/input API before the final successful run. No new provider calls or production restart were needed for these checks.
- Real projection at sequence 1268 was live (1.9 seconds old): 20 active requests, 17 known active consumers, 18 awaiting output, two streaming; retained activity included 253 SDK-attributed sessions and zero agent/parent-agent identities. Session attribution is proven; live parent-child lineage is not. Neither source support for headers nor synthetic lineage tests claim producer adoption.
- Public HTTPS serves the router assets and rejects unauthenticated telemetry with 401/no-store. A credential-related source search was rejected by automatic approval review; it was not repeated through another carrier. Subsequent checks used only the already-authorized snapshot reader, service metadata and unauthenticated public endpoints. Browser authentication remains an unchanged normal sign-in boundary.
- Remaining acceptance: exact-source publication/release, VPS asset/projection verification, and authenticated desktop/mobile browser inspection after the Chrome extension panel is closed. The incumbent inference router and its overlay do not need restarting for this admin-only correction.

### Backlog repair: identity separation and current-main integration
- The current Macro backlog assignment takes over original PR #10952 at `709e1b41f10c2b8748468b4b2748d402a065bb3b`. Receiving main `86030e7e27ef9e700703f2669c26f9b753bad6ba` already contains the navigation/prune fixes from #10897 and the separate import-path repair from #10951; those accepted repairs are integrated without duplication.
- Bounded source review identified a remaining lineage defect: agent and session IDs use the same pseudonym function, and an untyped consumer key combined their traffic when the same raw ID was used in both roles. The existing renderer now includes the identity role in its internal grouping/selection keys; the existing projection counts typed identities. Telemetry fields, hashes, observer, credentials, request lifecycle, API parameters and routing are unchanged.
- Discriminating fixtures failed before repair: three distinct UI consumers appeared as two, and the real observer-to-snapshot-to-panel path counted one active consumer instead of two. The repaired behavior isolates the retained parent from a colliding session and preserves the separate session selection. Final focused results are recorded on the exact published successor in the PR.
- These are source and synthetic behavior checks. They do not claim a production collision, deployment, authenticated visual acceptance or observed live parent-child lineage. The earlier credential-search refusal remains fenced, and the existing VPS/browser acceptance obligations remain open.
