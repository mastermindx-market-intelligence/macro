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
