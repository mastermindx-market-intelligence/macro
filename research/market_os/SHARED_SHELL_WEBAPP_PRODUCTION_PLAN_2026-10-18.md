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
