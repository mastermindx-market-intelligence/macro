# Admin panel revamp — 21 September 2026

## Scope and acceptance

Chairman request: clean up the randomly accumulated admin console, identify broken or useless content, and improve the actual interface. This batch makes the existing console an operations workspace rather than replacing its engines or creating another control plane.

The inventory is 54 existing page routes, including 22 marketing pages. All 54 remain reachable and searchable. Only 13 everyday pages are expanded by default; 41 specialist pages are grouped behind native disclosures. This is intentional demotion, not a claim that every specialist page should be deleted.

The inspected baseline was `origin/main`, not the occupied `macro-main` worktree. Existing cleanup PR #7345 and API-cache recovery PR #7251 were reconciled, tested against current main, and merged before this implementation. Their respective merge commits are `234ce9df57dd0431b2f3594a4e5b84eb8500a756` and `96e5b35ae123d196694d4576d9c4f94fc7767971`.

## Findings and repairs

| Finding | Evidence in the previous implementation | Repair |
| --- | --- | --- |
| Navigation overwhelms the operator | 54 links expanded across numerous organizational groups | Three everyday task groups plus three expandable specialist groups; all existing route IDs retained |
| Specialist discovery requires scrolling | Research and marketing tools buried in the long list | Search matches titles, route IDs and group labels, including collapsed pages |
| Parent pages cannot be bookmarked reliably | `go()` does not assign a page URL | `#/page/<id>`, reload persistence, browser Back, explicit malformed/unknown-route recovery |
| Rejected reads can leave a dead panel | Async renderers invoked without a common rejection boundary | Recoverable error screen with retry and overview navigation; late obsolete failures cannot replace a newer page |
| Hung reads have no deadline | Unbounded `fetch()` and body parsing | A 30-second deadline for ordinary GETs, including body parsing; writes are never retried or implicitly aborted |
| Failed session transport fabricates an authenticated local state | Startup catch returns `auth_enabled:false, authenticated:true` | Validate the actual session response and remain behind login when verification fails |
| Refresh loses the last valid snapshot | `SUMMARY` replaced before the error check | Validate the next summary before replacing the previous snapshot |
| Analytics reports success without checking data | Hard-coded “Live” / “tracking enabled” Overview tile | Remove the unsupported live-status claim; analytics remains a first-class customer page |
| Failed services still sound healthy | Background-services detail always says “running normally” | State follows explicit reported health; unknown is unavailable, not healthy |
| Header overstates overall health | Unavailable services allowed an overall “Healthy” badge | Healthy requires both known pipeline and service checks; otherwise Attention or Incomplete |
| Research history looks like operational incidents | Historical alerts and seasonality engineering notes dominate Overview | Operations-first landing; dated research records and their full actions retained in a separate collapsed section |
| Global experiment badge distracts from operations | Historical ready-result count shown in every page header | Experiments stay available in research navigation and in the research disclosure |
| Deployment controls are duplicated on the landing | Rebuild/redeploy dispatch buttons before run inspection | Landing links to the existing Build & Deploy page; its confirmation and controls remain intact |
| Navigation emulates native controls | Clickable divs and spans | Native buttons for page links, System and logout; selected page uses `aria-current` |
| Hidden mobile navigation retains keyboard focus | Translated drawer without inert state or focus handling | Closed mobile drawer is inert; opening focuses search, closing returns focus, keyboard focus cycles inside the open drawer |
| Retrying boot can duplicate event listeners | Sidebar wiring runs on every boot | Wire drawer listeners once; state can still be reinitialized |
| Legacy CSS leaks into the new header | Global `header` rule makes every header sticky | Scoped Overview header reset; responsive topbar avoids clipped wrapped metadata |

The read-cache rejected-Promise defect was separately fixed by the preserved #7251 implementation. This batch retains its identity-checked cleanup and request coalescing.

## New primary structure

**Workspace:** Overview, Data health, System status, Build & Deploy.

**Customers:** Analytics, Users, Support Tickets, Email Center, Revenue.

**Publishing:** Publishing overview, Outbox, Content Studio, Publisher.

**Specialists:** Intelligence & research (14), Publishing tools (18), Platform & settings (9). The regression test names every expected route and checks uniqueness, total count and the primary count.

Overview now answers: what is known about the data pipeline, services, host resources and estimated AI cost; what operational check needs attention; and where to do support, publishing, account or release work. Cost is explicitly an estimate, not billed spend. No invented counts or success states are introduced.

## Design and safety boundaries

Reuse the admin console's existing Observatory tokens, materials and native disclosure components. No new palette, external UI framework, generated-data contract or engine rewrite. The baseline admin is English/dark-only; this batch does not claim light-mode or Chinese-language certification. Those are inherited product-wide gaps requiring a separate governed migration, not something a token swap proves.

No research content is deleted. No production customer, payment, publishing, messaging, access or deployment mutation is exercised as a test. Server authentication, CSRF, Caddy boundaries and operator confirmation behavior remain unchanged. The browser smoke command is restricted to a loopback development target and blocks all non-GET/HEAD requests.

## Reproducible checks

```sh
python3 -m admin --port 8798
python3 scripts/qa/admin_workspace_smoke.py --evidence-dir /path/to/evidence
python3 -m pytest -q tests/test_admin_navigation_ux.py tests/test_admin_api_cache_recovery.py tests/test_admin_js_no_undef.py
```

Restart the local admin service after editing assets. Current `admin/server.py` pins content-addressed assets for the process lifetime. Current `app/deploy/update.sh` restarts the deployed admin service for any `admin/` change; older notes claiming that static updates need no restart no longer describe the code.

Browser evidence includes desktop 1440×960, mobile 390×844 and mobile navigation screenshots. The checks cover search, native keyboard activation, bookmark/reload, browser Back, malformed routes, renderer retry, session-read failure, summary retry, mobile overflow, focus/inert behavior and all 54 renderer failure paths. Backend-unavailable fixtures are clearly separated from local data screenshots. A successful fixture sweep is not proof that every authenticated production integration is working.

## Remaining work, in order

1. **Authenticated workflow audit:** verify the read contract, freshness, empty/error state and operator value for every specialist page; then test approved actions with explicit dry-run or staging boundaries. Local missing integrations must not be described as production outages.
2. **Publishing consolidation:** the 22 marketing pages remain the largest overlap. Compare Floor/Desk Health/Sentinel, CMO Office/Departments/Channels, and Lab/Experiments/Learning by actual operator jobs. Consolidate duplicated views, preserve existing API owners, and redirect retired routes rather than silently deleting working features.
3. **Intelligence consolidation:** Observatory/Intelligence OS/Master Brain/AI logs have different existing contracts. Establish a read-first engine index and move specialist diagnostics into engine details only after proving equivalence.
4. **Performance and stale-success races:** the roughly 957 KB JS and 214 KB CSS baseline remain a monolith. Split along stable domain seams; bound and cancel obsolete successful renders as well as obsolete errors. Existing analytics slowdown fixes must be reconciled with their owners, not replaced blindly.
5. **Truth and maturity policy:** require data timestamps, unavailable states, real actions and an owner for retained pages. “Not tracked yet” placeholders, ambiguous research readiness, and unsupported provider capability claims should not occupy the primary operational view.
6. **Theme/language and deeper accessibility:** the existing admin lacks full dual-theme and EN/ZH parity. Audit content contrast, large tables, modal focus and all nested controls beyond the rebuilt shell.

Completion of this first workspace batch is not completion of the entire 54-page admin remediation program. Production deployment proof is tracked separately from local browser and source test evidence.

## Continuation: Content Studio review workflow

Chairman continuation retains the original admin mission. The protected procedure pin for this wave is `mastermindx-market-intelligence/Mastermind@74b475545e179a3256bfebe6b5226f54231cf1cb`: INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT; schema `mastermind.sol_skillpack.v1`, version 1.0.1, bootstrap major 1. Macro implementation base is `91d0269481fef77e82dc0ba6f9469bd2585ad7e7`, branch `claude/admin-publishing-review-20260921-sol`. Sol retained this tightly coupled review-path repair under `PRINCIPAL_JUDGMENT`; no worker started, no alternate provider/control plane was introduced, and no inherited effect was unresolved.

### Before and after

The type filter and desk filter previously overwrote each other's card visibility. The page created every post card and inline chart before wrapping the tail in a twelve-item disclosure. Filtering therefore neither composed correctly nor bounded the amount of rendered content.

The review now intersects **desk + content type + case-insensitive search before pagination**. It mounts at most twelve matching cards, makes all remaining posts reachable with Previous/Next, states the matching count, and offers an explicit empty-result recovery. Search covers the entire plan, not just the visible page. Existing plan, funnel, desk-mix and intraday draft/approval functions remain owned by their original modules.

The consumer requests `/api/marketing/content?charts=metadata`. Default callers of `/api/marketing/content` retain their original inline-chart representation. Both representations return the same plan revision, complete post inventory and existing operational fields. Chart bodies are requested only after the operator opens a preview, through the authenticated read route `/api/marketing/content/chart?id=…&revision=…`.

The preview reader accepts an ID, never a filesystem path, and requires the complete source-plan SHA-256. It rejects a corrected plan, unreferenced chart, duplicate chart ID, malformed body or SVG above 2,000,000 UTF-8 bytes. An old plan is never silently joined to a different chart. The browser uses an image element rather than inserting an SVG document into the admin DOM. Missing/error responses offer a named retry or plan refresh; a late Content Studio response cannot replace a newly selected page.

The review now describes plan times as advisory, provides the existing Outbox handoff, and removes the contradictory claim that nothing in the plan has been sent. Missing drop reasons no longer claim every draft passed, and no longer consume a large decorative empty-state panel.

### Measurements and evidence

On the **same committed local plan**, serialization fell from **2,875,956 to 40,294 bytes (98.60% smaller)**. Both responses retained **13 accounts, 38 posts and 27 chart references**, with identical revision `c9d133b9edbe08d84acb0a75f4e97dd9b277ce8b5568e977c26e858d2663ec86`. These are same-input payload measurements, not production latency measurements or a claim about the size of every future plan.

The actual loopback HTTP read adapters were exercised in a browser using a clearly labeled 48-post fixture. Checks cover both filter orders, a search target beyond the first page, every post reached once, twelve-card bounds, intent-only previews, changed-plan refusal, failed-read retry, refresh, delayed-success navigation, and mobile overflow. All 21 checks passed with no unhandled JavaScript errors and no attempted write. Desktop 1440×960 and mobile 390×844 screenshots use the inherited English/dark admin style, not claimed light/Chinese certification.

Source-backed tests exercise the real JavaScript filtering helper and backend read adapters, including default-API compatibility, payload bounds, revisions, missing/oversized/duplicate/unreferenced charts, HTTP errors and retained anonymous-access denial. The first broad admin run exposed two tests requiring omitted `data/` and `site/` sources; those trees were materialized before the full rerun. No test guard was disabled or assertion weakened to excuse missing data.

Evidence is under `research/evidence/admin-publishing-review-20260921/`. Production delivery remains a separate receipt on the wave's GitHub PR; this committed document does not substitute local browser success for a live integration result.

### Scope held and next action

The accepted #7345/#7251/#7602 work is DO_NOT_REDO. All 54 admin route IDs and the 13-page everyday navigation remain intact. No publishing action, approval gate, customer account, payment, email, or deployment mutation was exercised as a test. The active publishing-truth and media owners (#7487, #7489, #7493 at this wave's collision check) were not modified or replaced.

**The full admin program remains incomplete.** The next publishing step is to reconcile the existing Publisher/Outbox delivery states with their active owners, then consolidate overlapping status views only after proving that their distinct actions and evidence survive. In particular, Content Studio's inherited `posting`→`posted` usage mapping is not external delivery proof and was not silently redefined in this view repair. Other remaining obligations are authenticated specialist workflow checks, Intelligence OS/Site inventory latency, monolith boundaries, and full theme/language accessibility. No autonomous wake or background Web execution is claimed.

Full post-materialization admin regression run: **1,414 passed in 72.74 seconds**, with default data/module guards retained.

### Acknowledgement boundary discovered during review

The same Content Studio carrier also corrects the intraday draft action's acknowledgement handling. A lost response previously said nothing was queued and re-enabled the write. The UI now distinguishes explicit refusal, local enqueue with unconfirmed publisher-queue delivery, confirmed publisher-queue delivery, and unknown effect. Unknown/local-only outcomes keep the action disabled and link to the existing Outbox for reconciliation; they do not originate another queue or automatically repeat a write. A confirmed queue receipt is still not external publication proof. The server's existing approval, idempotency and delivery paths are unchanged.

The source-backed JavaScript tests simulate these acknowledgements without sending HTTP mutations and verify that repeated invocation of the disabled action cannot reissue the request. Full admin regression after this correction: **1,416 passed in 72.39 seconds**; the final notification-only adjustment is additionally covered by the focused JavaScript suite. The existing workspace browser suite also passed all 17 checks, including all 54 degraded route paths. The current implementation carrier is **macro PR #7609**.
