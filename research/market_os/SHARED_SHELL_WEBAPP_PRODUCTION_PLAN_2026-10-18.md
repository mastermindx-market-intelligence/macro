# Shared Shell web app — production master plan

Status: ACTIVE PRODUCTION COMMISSION. Source implementation and beta delivery are authorized by the Chairman's 2026-10-18 request. This document is a build contract, not a claim of deployed or accepted behavior.

Programme: WS:MARKET-OS

Original operation: market-os-shared-shell-design-20260924-sol-001

Attended parent: shared-shell-production-20261018-c1

Existing carriers: Macro #7949, sol/market-os-shared-shell-design-20260924; Terminal #859, claude/investor-shell-native-20261008-c1.

## 1. Product intent and scope

Build the shared shell as a persistent web application using the existing Terminal application infrastructure. Put the current Macro HTML/Jinja pages into the shell's content area. Preserve useful page content, intelligence semantics, and existing behavior while individual pages are progressively converted to native application views. Install the reviewed beta at https://beta.mastermind-x.com.

The Chairman explicitly described the Paper material as scattered, incomplete, and non-final. It supplies design and interaction references, not a complete feature specification. This programme owns the missing organization, architecture, compatibility work, verification, and release work. The optional creation of another Paper file is an organization choice, not a prerequisite for engineering.

This request advances the previous design-only and preview-only scope. Historical holds remain useful records of unproven dependencies; they do not erase the new build commission. Required source review, exact release admission, auth boundaries, and proof gates still apply. Existing economic, data, risk, alert, portfolio, watchlist, and entitlement owners do not transfer to the shell.

Success means a real user can enter a direct beta URL, move among existing workspaces without restarting the outer shell, use an existing dashboard at the reduced content width, open supported native capabilities, and return with the context promised by that route's contract. Every live customer-facing route must have an explicit integration disposition. A directory full of links alone is not completion.

## 2. Recovered source and observed baseline

| Area | Observed source / evidence | Consequence |
| --- | --- | --- |
| Macro design carrier | PR #7949 head 9b54c2d7f1f19a7371a7ee2102fb706f46e1b7ac | Retain existing All-tools, navigation, account and return-focus work. |
| Original Macro workspace | shared-shell-r27 was clean at 1b895236dfec4f20e0a62812a7c9c4c6d2db901c; fast-forwarded normally to 9b54c2d7 | The original carrier remains the integration owner. |
| Current Macro main | 4f52d22596545cbd67b5143e188baf5660237024 fetched on 2026-10-18 | Preserve current data and behavior when joining the older carrier. |
| Terminal preview | PR #859 head 2e7cf6663733e1394b5f3e389dde4f1cd341bf40 | Existing AppShell, expanded/compact rail and native analysis/discover preview are reusable. |
| Current Terminal master | d6515f47232538161af8d3d4c27064165eda40fe | Joined without conflicts as f1f2cc79c5961d84117d686caf87e5f41a9e9d79 and pushed to the same PR859 branch. |
| Canonical page registry | data/product_experience/page_registry.json, mastermind.page_registry.v1, 331 records; generated_at 2026-09-04T22:43:01Z | This is an existing derived registry. Refresh against current source before claiming complete coverage. |
| Registry owners | scripts/build_product_page_registry.py and config/product_experience/page_registry_overrides.yml | Export a derived consumer projection; do not maintain another route database. |
| Live Macro UI | Connected-browser inspection of /macro.html: dense navigation, live risk/regime dashboard, charts, panels and Brain launcher | Preserve actual dashboard content; never replace live values with illustrative Paper numbers. |
| Current serving plane | VPS Caddy; Macro /opt/macro/site.served; independently refreshed /var/lib/macro-live/public; Terminal service on port3000 | Reuse the existing deployment and data owners. |
| Terminal production marker | 3e6e9591d21b849227de3633b4322d7d3b0d3b37; BUILD_ID build-TfctsWXpff2fKS; terminal.service active | Source merge, running production, and beta are distinct states. |
| Beta DNS and host | beta.mastermind-x.com failed DNS resolution from the connected host; no beta block found in live Caddy | DNS/TLS and a source-managed beta serving target are required. |

The first paid Fabric census, shared-shell-route-audit-20261018-c1-r1, completed at the pinned Macro source edc7c8976a50482cd52e13910b1b1ad188d113dd. Its result is NOT ACCEPTED as a complete route census: it mistook sparse omission of data/ for absence of the canonical registry. Parent verified the 331-row registry directly with git show. Its template/runtime observations are leads requiring source checks, not blanket proof.

Paid leaf shared-shell-macro-join-20261018-c1-r1 was requested for the bounded current-main merge candidate. It stopped before worker execution with FABRIC_SPARSE_HELPER_BLOB_MISMATCH on the selected host's donor helper; no merge candidate was produced. Do not patch or bypass that qualification fence. The parent will use the already-owned original workspace for the join (NO_ELIGIBLE_PRE_EFFECT_WORKER on this selected source-mint route). A distinct artifact-only leaf, shared-shell-contracts-20261018-c1-r1, was commissioned for pure route/protocol modules without repository allocation or helper changes. Source adoption and release remain with the parent.

## 3. Paper organization and provenance

The refreshed reference graph contains eleven known files. This is a census of the supplied files and their connected reference graph, not a claim that an unavailable account-wide file listing was performed.

| File | Current role | Relevant locations |
| --- | --- | --- |
| MASTERMIND PAGES, 01M2WGNCX9475G79JRKJTCM08P | Investor shell and original interaction studies | p-D-0 shared shell; p-1R-0 All Tools; p-1S-0 Search/Comparison; p-1T-0 Watchlists/Save; p-1U-0 Research/Reading; p-18-0 current investor candidate. |
| MarketOntology, 01M3P1X4FR6BRTB13KA736Y1HT | Retained company comparison and evidence | p-4-0 retained references; p-5-0 duplicate QA hold is not build authority. |
| Mastermind OS, 01M3NRCX55B452A12819WNE1RH | Executive Atelier product, distinct from investor IA | p-8-0 now contains H7R-0 desktop and IOE-0 mobile OS shell; p-F-0 contains UYR-0 MOVED notice pointing investor work back to MASTERMIND PAGES. |
| Terminal, 01M3NSZGE8JWN2EZCSF0DT05RM | Current native product plus retained stock/setup states | p-E-0 retained shell references; YY4-0 directory; XOA-0 stock/setup desktop and watchlist/recovery variants. |
| Mastermind AI, 01M3P1QEHS5XXQY85BJT6QR2E1 | Current AI product with retained reading/evidence | p-5-0 retained references; 5HW-0 directory; p-6-0 duplicate QA hold. |
| Product Design System, 01M312VSDSZFVT45674GDVJVZN | Canonical foundations and working-file directory | 42T-0 navigator; foundations/components/patterns pages. |
| International, 01M3P1TW5Y3XWQC37ADDS8K5AG | Current country/market navigation and research | R10 country, comparison, research and recovery families; no literal Shared Shell text match in the file-wide query. |
| Intelligence Hub, 01M2VWK62FA5S4VVF6G7SBPE5J | Domain workspace, commands and evidence | Current working and state families; no literal Shared Shell text match. |
| PROPHET, 01M3NT5Y3G5HTJHVR0K5W2MDJM | Opportunity workspace and setup states | Shared shell text nodes 7ZL-0, 805-0, 80P-0; current drafts remain drafts. |
| Market Guide, 01M32XYWDYSFTNDZVJKQ5QHT33 | Contextual help and search/recovery | No literal Shared Shell text match. |
| Risk Popups, 01M38EVF74SJWG1GANN5VP380Z | Popup/evidence behavior and risk journeys | Shared shell reference text node7T4-0; popup ownership remains domain-specific. |

Key visual source: MASTERMIND PAGES p-18-0, artboards61GR-0 desktop dark, 61LF-0 mobile dark,61MY-0 mobile light navigation. All three were visually inspected. Retain the restrained rail, clear workspace title, useful content area, semantic active state, and mobile drawer. Do not treat the market overview illustration or its 61/100 value as production data.

The older p-D-0 journey map21H2-0 and Terminal-focus U19-0 remain interaction evidence. Search must distinguish loading, no matches, selected result and unavailable. Saving must distinguish prepared, pending, saved, failed and outcome unknown. Unknown writes must be reconciled by their existing owner before a retry. Closing a dialog restores the actual invoking control where the incumbent contract promises it.

The Paper adapter currently reports write-schema qualification failure: observed catalog1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db versus reviewed ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9, accepted_for_write=false. No edit has been attempted. Do not bypass this through raw MCP, another carrier, or UI. Continue source design/build work; record any later qualified Paper edit under its real receipt. Do not delete, move or rename source studies as if they were duplicates proven disposable.

## 4. Architecture decision

### Existing application owner

Extend Terminal's existing Next App Router application and nonchart AppShell. The shell stays outside the page subtree so route loading, page crashes and workspace navigation cannot remove global navigation. Keep the existing AccountIdentity, OnboardingProvider, SettingsProvider, language owner, theme owner, active-symbol contracts and native route implementations.

The chart route /terminal keeps its current chart shell and Brain owner. Do not nest its providers inside another chart shell. The first beta may use the incumbent Terminal portal or an explicit full chart focus route where that preserves the existing return contract. Do not copy the chart implementation into Macro.

The server-only feature flag MMX_SHARED_SHELL=1 enables the full beta shell. Any other value is off. The earlier MMX_INVESTOR_SHELL_PREVIEW flag remains independently compatible until deliberately retired with tests. Beta configuration enables the new flag; normal production does not silently opt in.

### Legacy document adapter

Use a real document boundary for legacy Jinja pages. A stable adapter contract separates canonical beta navigation from how a particular page renders. Native and legacy routes are interchangeable behind that contract.

The first compatibility implementation uses the existing canonical Macro origin https://www.mastermind-x.com as a fixed, source-approved legacy origin. This preserves root and relative asset URLs, Macro API/data ownership, existing auth cookies and page scripts without a broad proxy or fetch monkey patch. It also avoids assigning Macro and Terminal incompatible meanings for a shared /data namespace.

Legacy documents opt into a versioned bridge only when actually embedded by the approved beta parent. The ordinary Macro page retains its current standalone experience. Framing permission must be exact to the beta parent and opt-in response, with existing payload gates still applied. No arbitrary URL input may select an origin or upstream.

A separate same-origin prefix or dedicated legacy host is a possible future mechanism, not an automatic fallback. It requires a recorded revision and proof of path, auth, CSP, asset and history behavior. A prefix is not a security boundary; a same-origin iframe would allow its scripts to access the parent and shared storage.

Do not adopt arbitrary response HTML with innerHTML, eval or generic script re-execution. Native page conversion later must supply explicit mount/dispose and data-owner contracts.

### Route identity and coverage

Canonical browser URLs remain ordinary beta paths, queries and fragments, including existing .html paths. Internal bridge markers are not shareable product route state. The catch-all route resolves only the generated approved projection; unknown, internal, admin, lab and denied routes fail closed.

Generate the projection from the refreshed existing registry and source inventory. Include source commit and registry digest. Each entry records canonical route/family, original page identity, rendering mode, legacy path or native owner, and navigation metadata. Derived output is not hand edited. Reject native/infrastructure collisions such as /api, /auth, /_next, /terminal and named native workspaces before publication.

Directory navigation is not the census. Pages omitted from an old menu still need a recorded disposition. Family rows must match only their supported path shape; no catch-all prefix that accidentally exposes internal artifacts. Public/corporate, account/callback and operator surfaces retain their distinct access/interaction boundaries. A route intentionally opened through its existing standalone owner must be labelled and documented; it cannot count as an in-shell page until that experience is proven.

## 5. Shell experience and design contract

Use the existing product typography and semantic tokens. The investor reference supplies a224px expanded rail,72px compact rail and64px desktop header. The content area uses remaining width and min-width:0; its layout does not assume the old full browser width. At mobile/tablet breakpoints use the existing primary mobile navigation owner and make all destinations reachable with touch and keyboard. Do not mount both an old and a new drawer.

The persistent shell provides:
- A clearly active workspace and usable expanded/compact navigation.
- Market overview and regional research entry points.
- Existing native Analysis, Discover, Dislocations, Options, Scripts, Portfolio and Alerts destinations.
- All tools directory with search, categories, no-results and recovery states.
- A global search entry using existing company/search data owners. Tool search and company search are distinct result kinds.
- Existing account/settings, theme and EN/ZH controls.
- Contextual access to Terminal and Brain through their incumbent owners.
- A visible page loading/error/retry boundary that leaves navigation usable.

Use the real existing page heading where appropriate; do not stack a second hero/title over every legacy dashboard. Strip only verified global chrome in embedded mode, leaving local tabs, chart toolbars, evidence panels, page actions and footer disclosures intact. A blanket hide of every header/nav/footer element is forbidden.

The light theme must be intentionally legible, not just a dark layout with inverted colors. Use localized labels and ensure Chinese expansion does not clip destinations. Disabled or unavailable controls explain the actual state; do not ship decorative Save/Compare/Search actions with fake success.

## 6. Bridge, history, context and lifecycle

Protocol: mmx.shared-shell.v1. Every message has version, type and frameGeneration. Parent accepts only the exact approved legacy origin, the active iframe contentWindow, the current generation, and a closed message schema. Child accepts only its actual parent window at the approved beta origin. Generation is a freshness fence, not authentication.

Minimum messages:
- INIT: canonical route, theme, locale, context revision and allowed navigation projection.
- CONTEXT: a new supported theme/locale revision.
- READY: plain-text title, capabilities and the applied context revision.
- NAVIGATE: request for one validated canonical path/query/fragment.
- CONTEXT_REQUEST: request for a supported preference change through the existing owner.
- ERROR: a bounded initialization or unsupported-context error.
- VISIBILITY and SCROLL/FOCUS restoration are added only with their implemented lifecycle contracts.

Never include access tokens, arbitrary executable strings, provider credentials, user-write payloads or unrestricted destinations in bridge messages. Theme/locale application must not create account-preference write loops. Market navigation selects an existing supported market route; it does not silently mutate portfolio/watchlist or invent a market data state.

The top-level shell owns product history. Normal qualified links request parent navigation; native Next routing commits the URL; iframe document loading uses replacement/fresh-frame behavior proven against real browser joint session history. Back/Forward and fragment changes must not create duplicate entries. Downloads, modified clicks, copied URLs, external links and forms retain explicit behavior. Unknown internal links must not accidentally load a second shell inside the frame.

Keep at most one retained legacy document. A legacy-to-legacy route transition disposes the previous document unless it is the same-document fragment/state transition. If a native workspace temporarily retains the originating legacy document, it must be hidden/inert, keep a fixed bound of one, and obey its declared visibility/resource contract. No unbounded hidden iframe cache. Dispose the retained frame on identity change, explicit reload, incompatible release or a new legacy document.

Preserve exact scroll, focus and local state where promised. The incumbent Macro-to-Terminal portal is already a context-preserving owner and should remain intact until its replacement has stronger proof. Do not claim that a recreated document restores arbitrary unsaved filters merely because its URL was restored.

Late READY/title/context messages from an old generation are ignored. A page timeout shows a recoverable unavailable state and a real link to its canonical original; it must not fake readiness. Auth expiry, denied payloads and stale/partial market data remain visible under their existing owners.

## 7. Identity and data boundaries

Terminal's shell resolves claims once for display identity; this does not authorize Macro payloads. Macro regwall/paywall and canonical user-state owners continue to authorize every request.

Verify beta cookie scope, refresh, login/callback redirects, logout, cross-tab identity transitions and credentialed API requests. Reuse the existing shared cookie policy where already configured; never widen cookie scope or copy browser tokens as a shortcut. An authenticated failure cannot fall back to a guest's local portfolio/watchlist.

Beta initially uses the incumbent live intelligence and account services. A separate hostname is not a separate database. Navigation and theme changes must not create personal trading/saved-state effects. Test mutations only through an explicitly authorized disposable identity or existing isolated fixtures, with authoritative readback and exact cleanup.

Premium bodies, owner-specific results, RSC responses and prefetches must remain private/no-store where required. No route projection, search index or static beta asset may contain private account data. Independently refreshed live artifacts remain owned by their current publisher; a shell deploy must not replace them with repository snapshots.

## 8. Delivery packages and sequence

| Package | Owner/carrier | Result required before advancement |
| --- | --- | --- |
| S0: custody and references | Parent, Macro7949/Terminal859 | Source joins, refreshed Paper map, current route provenance, host facts. |
| S1: route projection | Macro existing registry owner | Current registry plus deterministic shell export; denied/native collisions and family boundaries tested. |
| S2: native shell | Terminal859 | Persistent shell, shared navigation, directory, loading/error states and legacy adapter interface. |
| S3: Macro compatibility | Macro7949 | Versioned opt-in bridge through common page owners, exact framing policy, verified chrome removal and original standalone parity. |
| S4: complete route integration | Same carriers | Every live customer route classified and reachable; representative hard families prove real runtime behavior. |
| S5: identity and interaction proof | Existing auth/state owners, parent acceptance | Direct entry, login/expiry, query/hash/Back, theme/locale, mobile and personal-action semantics. |
| S6: beta release | Existing deploy owners | Source-managed beta target, admitted immutable builds, DNS/TLS, private cache policy, release marker and rollback proof. |
| S7: staged native conversion | Subsequent bounded programme leaves | Convert one page family at a time behind the same canonical route contract; remove the legacy adapter only after parity proof. |

S7 does not delay the first shell beta when S0–S6 are accepted. Conversely, a source-only preview does not satisfy the requested installed beta.

## 9. Verification matrix

Representative legacy families: Macro, US stocks, China, HK/Canada or International, Sector Central with #confluence, a runtime-heavy flow/Prophet surface, a research article/evidence route, and a watchlist/account interaction surface. Also test a nested-path public dossier and a deliberately excluded internal route.

For each admitted family:
- Cold direct URL, reload, internal navigation, Back/Forward and copied/open-in-new-tab link.
- Correct query/fragment and market/security identity.
- No duplicated global chrome; local page tabs/actions remain usable.
- Page runtime loads its real assets; charts resize to the content viewport; dialogs, keyboard shortcuts and downloads function.
- Desktop1440×900 dark EN and light ZH; tablet820×1180; mobile390×844;320px stress;200% text/zoom and keyboard focus.
- Loading, page failure, bridge mismatch, no-results and unavailable states remain distinct.
- Theme/locale changes apply without preference loops or wrong-market value colors.
- Identity change disposes stale user content; denied/private payloads do not appear in public cache.
- There is only one shell and at most one retained legacy frame; listeners/subscriptions do not accumulate after repeated journeys.

Use source/unit tests for route normalization, origin/schema validation, generation fences and serving boundaries. Use real-browser evidence for history, focus, scrolling, iframe behavior and responsive geometry. Static screenshots alone cannot prove persistence, auth, save outcomes or keyboard behavior. Required CI, independent review, deployment proof and parent acceptance are separate.

## 10. Beta release and rollback

The normal Terminal release owner is /opt/terminal/terminal-build.sh, from ops/terminal-build.sh. Its production contract requires an explicit full SHA contained by freshly fetched protected master and a CLEAN live-source preflight. Do not deploy a worktree via the obsolete local rsync script.

Implement beta as a reviewed, source-managed sibling target/service through the existing release ownership. Bind the exact Terminal commit, Macro compatibility/route revision, bridge protocol, assets and configuration into a release manifest. Keep production's default flag off.

Provision beta.mastermind-x.com DNS through its existing provider; configure Caddy/TLS and the beta upstream. The currently absent DNS record is an infrastructure task, not permission to change DNS providers. Respect current edge behavior and prevent private shell/RSC caching. Robots noindex does not replace access controls.

Before traffic cutover, verify service health and direct origin behavior with the intended Host header. After cutover, verify public TLS, exact release identity, all required user journeys and original-production nonregression. Retain the prior compatible beta release and immutable chunks. Rollback changes the beta release/configuration only, never engines, live data or account state.

## 11. Acceptance and current frontier

Accepted now: current commission captured; same source carriers recovered; original Terminal branch joined with current master and published; eleven-file Paper reference graph inspected; live Macro and serving-plane baseline observed; canonical registry existence/count verified.

Not yet accepted: refreshed route coverage, new shell implementation, bridge, complete family integration, identity/browser matrix, Paper write qualification, beta DNS/service, required CI, independent source review, deployment or production proof.

Next actions are executable S1–S3 leaves alongside completion of the bounded Macro merge candidate. Preserve each worker's stable ID and exact result; no unknown-effect resubmission. The first census remains unaccepted and is not route-coverage authority. Continue healthy implementation after checkpoints; this document is not a completion announcement.

## Attended production checkpoint — 2026-10-18, resumed session

The original carriers remain Macro PR #7949 (`sol/market-os-shared-shell-design-20260924`, owned `shared-shell-r27` worktree) and Terminal PR #859 (`claude/investor-shell-native-20261008-c1`). Protected Mastermind authority remains c355e6a4ce3c15ac1e46c14f642bb5984da810d2; inventory provenance at other commits is not an authority repin. The programme root correlation remains market-os-shared-shell-design-20260924-sol-001 and this attended commission remains shared-shell-production-20261018-c1. Neither is asserted to be a native run ID.

### Source implemented and bounded verification

Macro published HEAD 8eea49839b22fc332edeff1d687d80a62d413acf includes the protected-main source join and the exact canonical registry projection. Terminal published HEAD e44aa9e2f3c798b76b537cdbbb66444a29c9e85d includes the persistent native host, flag, route boundary, catalog/directory, status endpoint and original identity/settings owners.

The canonical projection contains 13,015 admitted legacy paths, 14 native paths and 293 directory entries, with zero unexplained tracked-HTML gaps. The 13,039 tracked HTML files include 13,028 full documents; eleven fragments remain byte-preserved by the injector. The first capability sweep stamped 13,028 served documents plus three paired source templates. This is route/document coverage, not proof of every page's interactive behavior.

Current additional source work includes strict document response classification (content versus the actual coming-soon gate), parent recovery states, responsive mobile reuse, preserved Terminal return locations, the common HTML writer/optimizer capability integration, exact beta framing headers and the isolated beta Caddy vhost. The bridge remains opt-in, bound to the exact parent/child context; production's native flag defaults off.

Observed bounded checks before this checkpoint:
- Macro document injector/gate producer: 22 passing tests.
- Bridge VM suite: 36 passing tests, before the subsequently identified boot-context interop repairs.
- Native TypeScript check and contract suite: passed; latest completed contract run had 14 passing tests.
- Full first HTML capability sweep: completed with zero process error; bridge digest prefix 996086e0 at that sweep.
- Actual Caddy configuration adaptation: passed without a live reload.
- Isolated HTTP execution of the actual Caddy framing rules: ten cases passed, including ordinary DENY, exact beta admission, wrong referrer/flag/path, and the gate response.
- Relevant Macro regression run: 216 passed, two skipped, one failed. The remaining failure is `test_every_workflow_that_stages_html_runs_externalize`: options-intel.yml stages options.html without the canonical normalizer chain. It is under repair; this checkpoint does not label that suite green.

### Returned work and integration adjudication

Ordinary Fabric artifacts were retained under the approved evidence root with matched manifests and verified producer contracts. Retention is separate from outcome acceptance. Navigation and owner candidates are not accepted as final implementations: integration review found active-only guards that miss pre-INIT queues and initial context application. Review also found legacy boot theme/locale overwrites and the actual zh-CN document language convention requiring bridge normalization.

The returned beta target profile is also not accepted: it lacks the shared build-resource lock, lacks first-install admission, and moved production hub-change detection after the runtime overlay. These defects are being repaired before adoption. No candidate release owner has been installed on the VPS.

The continuing ordinary artifact leaves are:
- shared-shell-navigation-final-20261018-c1-r1: candidate-safe redirects, actual hash owners, declarative redirect fallbacks and targeted VM tests.
- shared-shell-owner-final-20261018-c1-r1: existing theme/account/onboard ownership, initial apply suppression and centralized auth handoff.
- shared-shell-options-publish-20261018-c1-r1: the scoped Options publication normalizer gap.
- shared-shell-beta-bootstrap-20261018-c1-r1: isolated target, shared build lock, preserved production behavior, enforced source-provisioned bootstrap, real source-audit tests and source-managed beta unit.
- shared-shell-bridge-final-20261018-c1-r1: post-boot parent context, zh locale normalization and explicit-target href projection.

These are original continuing requests; controller polling alone is not worker liveness or acceptance. Reconcile each stable request/result before any retry.

### Beta runtime decision and remaining gates

Use the existing source-managed Terminal release owner with an exact beta target profile: app /opt/terminal/beta/terminal, canonical source /opt/terminal/.gitsrc-beta, terminal-beta service on 3001, and /var/lib/mastermind-terminal-beta/release-preflight receipts. Protected-source containment, trusted policy/runtime custody and ordinary CLEAN preflight remain mandatory.

A first install must have an enforced source-provisioned state distinct from runtime acceptance and rollback eligibility. Unexpected prior state refuses bootstrap; a matching interrupted provisioning state can resume only after verification. Successful installation requires the actual running status/build identity, not a generic HTTP 200 or the mere presence of a source marker.

The actual native app/API filesystem census found read/stat access, not a writable intraday runtime cache. Reuse the existing published production data through a service-namespace read-only bind, with a non-root beta identity and production paths unwritable through every alias. The beta build/prebuild sees only its own local tree. Caddy reuses the existing public-data owner. Before install, verify publication-root lifetime, intended coverage masking, namespace/capability enforcement, denied data writes, permitted beta cache writes and publication continuity. This avoids inventing another market-data producer.

DNS remains at DNSPod. The official console is at a sign-in wall; no DNS mutation has been attempted. The concrete intended record is beta A 146.190.142.17, leaving apex/www ownership intact. The user sign-in is a real remaining provider step. Paper reads remain usable, but the actual catalog qualification mismatch still refuses Paper writes; no bypass or new design-file mutation was attempted.

Both PRs remain under their existing review/hold custody. Required CI, independent current-source review, full Next build, the actual browser history/auth/theme/focus/responsive matrix, beta installation/TLS/build identity, rollback proof and programme acceptance remain outstanding. No deployment, merge, complete product acceptance or unattended continuation is claimed. Continue useful authorized work after this checkpoint.


## 2026-10-18 continuation checkpoint — native integration published; beta release pending

The original programme and worktrees remain the delivery owners. Terminal PR859 now publishes a9f0d78810b6fec05d80c50f59fef8ff9e3e1b2d, joining protected master 9f26d3a00dbaada3580706f7e059dd8eff682d7e without conflicts. Source repairs preserve the incumbent global CSS/i18n bytes, ordinary mobile Escape focus, true pre-stream legacy-route 404s, safe beta signup/callback return paths and chart-only exact beta framing. The production beta build passed. Ten actual Next HTTP cases passed across beta and ordinary flags: exact build/protocol/bridge/document/registry identity, appropriate macro route 200/404, unknown404 and one chart CSP with beta admitted only on the chart route. Both owned local servers were stopped. This is server evidence, not deployed or browser acceptance.

The current Terminal CI watcher has closed with actionable failures: two CodeQL substring-check reports and the plain-language scanner failing to recognize the new feature copy dictionary. The review findings are being corrected at their source; no required checks are bypassed. The serial and mobile-2 browser CI shards passed at that observation, while remaining shards were pending. No merge or beta deployment is claimed.

Macro has adopted 74 recorded navigation/owner/Options adapters plus the qualified Terminal handoff integration. The final r3 bridge was qualified by the existing Fabric artifact owner. Principal review then reproduced and repaired four readiness defects: interactive readyState before deferred scripts complete; losing DOMContentLoaded before a delayed INIT; queued startup callbacks escaping preference suppression; and accepting a correct semantic locale with a wrong html language. All 161 bridge/navigation/owner/handoff tests pass after the repairs. Bridge source SHA256 is 674abd8c95ecf60d96afaad049f5199d260d76717380c925af4a90acb263c64d. Generated site copies still await final canonical propagation and asset stamping.

The remaining navigation audit completed through run shared-shell-navigation-coverage-20261018-c1-r1, result SHA256 f95c724916289fd38609caf131a2ea9f32527f0bae6e67d7e3e2c0444ab8a1c5. Both advertised files were retained with manifest match and producer verification. It classified all 109 entries across 48 first-party files and proposed 25 further exact adapters, now under parent review. The source-only optional Terminal return-path concern is retained: transient credential material must not be nested into a return query. Normal current-page returns have not been shown to contain secrets.

Supabase redirect configuration was saved with two exact beta callback entries, bringing the observed count to 13; the incumbent Site URL remains www. No auth emails, user records, roles or RLS were changed. The unsaved DNS editor was cancelled; existing beta DNS is unchanged. The beta release-owner candidate remains unadopted and under independent principal review, including shared build locking, exact runtime identity, service file readability, cache-only write access, read-only data aliases and truthful first-bootstrap/rollback evidence. No beta unit, beta runtime, DNS cutover or VPS mutation has been performed. Paper write qualification remains blocked on the existing catalog proof; the published accessible-file design census remains authoritative for observed design references.

Next delivery steps are final adapter integration and canonical generated-output propagation, CI repair and protected landing, qualified release-owner adoption, installation and TLS/DNS proof on beta.mastermind-x.com, followed by actual desktop/tablet/mobile and fresh-session browser acceptance. This checkpoint preserves continuation; it does not close the commissioned programme.

## 2026-10-18 13:56 UTC — principal review corrections and generated-page checkpoint

The production task remains active. Beta installation, DNS cutover, actual public TLS/header acceptance, and responsive browser acceptance are still pending; none is claimed here.

- Native PR859 is published at 56055052a6b5753340b01f427876f0e86ed0abe0. Its CodeQL and Terminal unit/typecheck jobs pass. At the last exact-head observation, the serial and tablet-2 browser shards also passed; five other browser shards were still running. The subsequent parent URL-boundary repair is working-tree source, not yet published.
- The current Macro bridge SHA256 is 9e98cc403b65a433d2699885c793dcd8c95a656296d400074c977f5d7e5cb554. The protocol, bridge version, and document version remain mmx.shared-shell.v1 / 20261018.1 / 20261018.1.
- Principal review used SHA-verified local snapshots after large remote reads stalled. The reviewer independently reproduced cross-path history desynchronization, direct-fragment authentication leakage, false post-INIT context readiness, and persisted-pagehide teardown. Root added regressions that failed on the inspected implementation, then fixed the actual template. History now distinguishes pathname replacement from query/fragment state before child mutation, and a full pre-INIT queue cannot silently alter the URL. Credential-bearing/current authentication URLs cannot become protocol messages. Every READY proves theme, semantic locale, and HTML language. Persisted pagehide retains its bridge owners.
- The native parent now parses direct and routed fragment parameters together with query state, rejects credentials and split recovery context, and applies this predicate at first-party route admission. Current parent source SHA256 dc7c893852c287b2a18c6b71cbced07bfa0996c1168490c5a8c24e4d3de01266. Native contract/header/auth/status tests: 91 passed; typecheck passed.
- Actual Macro bridge/navigation/owner/Terminal-handoff integration: 179 tests passed. Python injection/projection/assets/stamping/render-gate coverage: 182 passed, 2 existing skips. The old minified-overlay test now checks the actual five-method interface; its initialization/listener/config assertions remain.
- Navigation/owner adoption ledger contains 102 exact source edits. The qualified coverage return contributed 25 reviewed edits; root corrected its theme fallback to exact-origin bounded native handoff and separately covered the dashboard alert event twin. Safe Terminal return validation rejects recursive or credential-like state. The controller-absent fallback retains a page-only return.
- Generated propagation applied 59 actual adapter replacements across 29 output pages. Seventeen canonical paired assets and the earnings-wire asset owner were synchronized; 13,028 HTML documents were stamped. The latest bridge change was synchronized and all 13,028 documents restamped again. The prior full integration gate passed 128 template/site pairs, 13,015 legacy plus 14 native route projection (293 directory entries, zero gaps), zero dead/pin/ticker asset references, and ten actual isolated Caddy response-header cases. Those gates will be rerun after joining current main.
- Incoming Macro main eb0dbd77cf380f019d6a0e98bf5eb65656b80b92 includes 67 commits beyond this branch's merge base, principally current market data/generated output. Preserve its data while joining, then reapply canonical shared-shell adapters and stamping. The new design doctrine forbids container accent stripes; Shared Shell CSS was checked and uses neutral surfaces/even borders, with color retained for complete focus outlines and semantic ink.
- The original qualified beta installer candidate is not accepted or installed. Principal review found additional upgrade-transaction defects beyond exact tuple verification and cache-only service writes: original provisioning provenance incorrectly tied to each new release, non-advancing accepted pointers, premature rollback-marker removal, insufficient binding of the accepted baseline, incomplete failed-bootstrap cleanup, and service-user ancestor/readability gaps. The ordinary Fabric repair successor shared-shell-beta-owner-repair-20261018-c1-r2 is active on ubuntu1. Its predecessor was refused before execution by the host staging-disk reserve. Candidate repairs must be checked against these findings and actual fixture/runtime evidence before adoption.
- Supabase's two exact beta callback patterns are saved; its existing site URL is unchanged. DNS remains on the existing EdgeOne CNAME records. Paper write qualification remains false, so no new Paper file or bypass has been attempted. The accessible-file design census and programme design decisions remain in this branch.

Owned evidence logs on M2: /tmp/shared-shell-principal-integration-green-20261018.log; /tmp/shared-shell-principal-final-stamp-python-20261018.log; /tmp/shared-shell-parent-auth-boundary-final-20261018.log; /tmp/shared-shell-all-principal-regressions-red-20261018.log; /tmp/shared-shell-lifecycle-credentials-red-20261018.log.

### 2026-10-18 14:09 UTC — current Macro main integrated and verified

Joined protected main eb0dbd77cf380f019d6a0e98bf5eb65656b80b92 into the e25071ab254264b39944a5ab35c9a0cc6734a634 integration checkpoint. All application source merged cleanly. Nine conflicts were generated HTML only; their incoming content was retained byte-for-byte before reapplying five required adapters (three US Stocks seams, ETF sign-in, and Special Situations sign-in). The other 54 generated adapter applications survived the merge, and the six previously documented mode-absent pairs remained absent.

Post-join verification passed: 128 canonical template/site pairs; 13,028 stamped documents with no further injection changes; exact canonical registry SHA30516d80cd64baf1f542e0d1cbf90ed254a1eab02cb55da3504766f5ae245535 and native projection (13,015 legacy, 14 native, 293 directory, zero unregistered gaps); zero dead/pin/ticker asset references; ten actual isolated Caddy response-header cases; 182 Python tests with two existing skips; and all179 bridge/navigation/owner/Terminal-handoff tests. Sparse checkout omitted the registry working file after merge, so the check consumed its exact stage-zero Git blob at an explicit temporary path; no registry pin or content was changed.

The independent bridge review and exact-source correction closure are now recorded in research/market_os/SHARED_SHELL_BRIDGE_PRINCIPAL_REVIEW_2026-10-18.md. The actual M2 parent source hash matched the reviewer snapshot. Installer transaction fixes and actual beta deployment/browser acceptance remain outstanding.


## 2026-10-18 14:48 UTC — reviewed source and generated publication boundary

Current main advanced to 8dc33f6df0a48df4492a16350fa849bbd0b49423. The integration joined that content, resolved seven generated conflicts from exact incoming blobs, and reapplied four reviewed adapters. The CI inventory refusal was traced to the unchanged 3,000-file API ceiling. After exact comparison, 12,988 files containing only the generated capability/stamp delta were returned to incoming-main bytes; all 32 behavior/content HTML deltas and all three required plain-copy pairs remain. The source diff is now bounded, and the existing trusted renderer owns the mass document emission. Full generator projection passed for 13,028 documents plus 11 unchanged fragments. Source checks and registry coverage passed in the existing validation environment. See SHARED_SHELL_GENERATED_PUBLICATION_2026-10-18.md for the required rendered-commit and actual served-tree gates before beta exposure. No source-only or local-fixture proof is public-beta acceptance.

## 2026-10-18 17:08 UTC — source integration and bounded release qualification

The commissioned Shared Shell programme remains active. Terminal PR859 is published and ready for review at 1d6024c8ae39bafee328017fa96769d17b3be378, joining protected master 98b9e664a0a3387a72f7bf360f5159235c1d8eb6. Macro PR7949 still publishes b84eeee5976bf3f315c55ea286157f77b11e8ee3 while this integrated repair checkpoint is being prepared. No PR has been merged by this session and no VPS, beta unit/runtime or DNS record has been changed.

### Native release and runtime evidence

The final joined Terminal release owner passed 83 bootstrap/transaction/cache lifecycle tests. These exercised the real Git/archive/rsync/audit modules with explicit service/build/network fixtures. Seventeen beta fixture logs contained no global npx bundling; the production positive control executed its three incumbent bundles. A further 207 incumbent admission tests passed on M2. The merge preserves the new production-only fundamental-scan bundle and the existing beta admission, transaction and rollback boundaries. The final owner SHA-256 is 4d1b7c05d975a30be21de9556cc9eef964d07f30ba468f88abd0b40a61a84247.

The merged app passed 94 contract/header/auth/status tests and typecheck. The 52 nightly/build-shard tests passed after their source-extraction harness was updated to recognize the owner's own closing branch; its failed-bundle artifact assertion remains intact. The production Next build passed on the published commit.

The first local request attempt exposed missing local Supabase configuration. Rebuilding with the existing repository's public fixture URL/key supplied that required configuration; no auth fixture bypass was enabled in production mode. The subsequent server verification passed 25 assertions for exact release/protocol/bridge/document/registry identity, no-store status, Macro root redirect, admitted route responses, private uncached shell envelopes, bounded frame sources and an actual pre-stream 404 for an unregistered legacy path. The temporary owned server was stopped and reaped. AppShell explicitly loads SharedShellRuntime with ssr:false, so the legacy content host belongs to hydrated-browser verification, not raw server HTML.

The exact-head hosted CI observation at 16:54:53 UTC had 13 passing checks and four browser shards still running, with no failures. This is a timestamped observation, not a claim of final hosted CI acceptance or landing readiness.

### Macro source integration

The reviewed static stylesheet repair, canonical retained-page refresh and current source identities are recorded in SHARED_SHELL_GENERATED_PUBLICATION_2026-10-18.md. Actual integration evidence now includes 184 Node cases, 89 bridge/public-policy/export/Caddy Python cases, all 83 unchanged fresh-builder cases, full source/publication guards and a clean complete contract census.

Earlier hosted-CI failures were repaired at their actual sources: exact additive module dependency declarations; root import precedence; source wording; API restart detection for lib/shared_shell; release-key alignment; evidence-backed registry archetypes; the actual auth helper setup in its Node harness; executable Oracle adapter verification; and the research builder's canonical HTML capability owner. No CI authority policy, inventory ceiling, RIG rule, source claim allowlist or generated-output comparator was weakened.

Sparse checkout omitted required tracked inputs. Only exact needed Git blobs were materialized: the registry/claim allowlist, the three persisted market-state fixtures, and the existing P0b evidence directory. The restored inputs match HEAD and are not new data production. The original P0b artifacts are preserved for the canonical refresh; no regenerated browser result is claimed at this checkpoint.

The reviewed P0b runner will execute the unchanged renderer and browser verifiers on committed, clean source, preserve the complete original target/history fields and original visual/degraded PNGs, bind actual output/PNG hashes, and run the unchanged first-frame and same-diff closure tests. The separate local shell browser qualification will exercise actual mounted parent/child controllers on loopback origins. Both remain fixture evidence and do not qualify public hosting or authentication.

### Concrete landing and serviceability dependencies

Macro's completed b84 semantic evidence correctly classifies three preexisting Sector Central RIG failures as inherited, but it also records authority_changed:true and authority_self_excuse_refused. The existing law refuses inherited-red self-excuse for this authority-changing source PR. Current accepted main 66ee4c52f711699b9572fd46df8c9831c116b7df contains the same three October migration packets without their required reference-review receipts. The genuine August Sector R3B.2 approval binds different frozen design bytes and does not approve the October Brief/Explore/Dossier/Research composition.

The existing owner is Macro #7646 / sector-central-redesign-20260921-sol-001. Its actual October reference needs completed independent product-regression and visual review evidence plus the designated design-authority verdict. This is not a new Chairman approval gate. A bounded attempt to locate its current governed continuation target on 2026-10-18 at 16:58:29 UTC was refused by unavailable Executive reader and Session Bridge backends; no exact target/operation binding was returned and no duplicate request was created.

There is a separate PR Completion compatibility issue. The shipped all-check policy rejects the intentionally failed inactive ci-authority/codex/merge-queue-pilot context on a main PR. Its required-check policy receives an empty required set, and its readiness predicate also requires CLEAN. The observed ruleset is evaluate-only; source additionally requires the organization required-workflow rule. The session has not edited helpers, fabricated readiness, bypassed checks or activated a wider ruleset. A legitimate landing mechanism must represent the repository's applicable authority after the actual CI proof is complete.

The connected Browser plugin again reported no connected originating browser instance at the latest resume check. Local repository browser fixtures remain usable. Public fresh-session browser verification and the signed-in DNS provider action remain pending through an available authorized browser surface; no fallback was attempted. Paper's existing write-catalog qualification remains false. The accessible-file design census and source programme remain the available design records.

Continue with final source/evidence publication, observed CI and legitimate landing, generated Macro publication, qualified isolated beta installation and namespace/rollback checks, then beta DNS/TLS and real desktop/tablet/mobile acceptance. Preserve every unresolved effect and existing carrier; a local build or passing fixture cannot close the programme.


## 2026-10-19 qualification update

Actual browser qualification found and corrected two integration defects: host navigation sampled a prior pathname during a committed Next transition, and About's body-level Main marketing navbar was outside the existing shell suppression selectors. The Terminal navigation correction is committed at 4717376dc582f69ffadc17026dd2eb99c9cb60fb and retained by the current 9c3e29fbac0891a2e15eee6a2cd3e33faa9a33fe candidate. All 17 current Terminal release checks passed at 2026-10-19T03:37:09Z. These checks do not substitute for the new R7 desktop, tablet, mobile and CSS-failure/retry run.

The About stylesheet fix has meaningful failing-before/passing-after tests and actual canonical publication proof. See the generated-publication contract and its versioned evidence directory for exact identities, all 34 Python/all 70 Node results, 129 template/site pairs and the full 13,028-document/11-fragment publisher boundary.

The proposed October Sector standalone reference received two actual independent BLOCK reviews. Its separate authority decision is REVISE; it is not an approved replacement for the existing Sector page. The Shared Shell beta retains existing native content under the Chairman's gradual-migration intent. The three Sector migration packets require a substantive, independently reviewed phase amendment and an applicable reference binding before their repository gate can close. Neither successful fixture captures nor older reference approval certifies the deficient new design or today's native runtime.

No beta service installation, DNS cutover or public acceptance is claimed by this update.
