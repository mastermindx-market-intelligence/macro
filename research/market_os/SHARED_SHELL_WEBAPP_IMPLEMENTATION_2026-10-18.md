# Shared Shell web app implementation plan

Goal: ship the persistent Shared Shell beta at beta.mastermind-x.com while preserving the current Macro/Jinja page runtimes and enabling later native page conversion.

Architecture: extend the existing Terminal AppShell and use a versioned document adapter for Macro pages. Derive route coverage from the existing Macro page registry and Git inventory. Reuse current auth, preference, data and deployment owners.

Tech stack: existing Next App Router/React/TypeScript, existing Jinja/Python generation, existing browser JavaScript and Caddy deployment.

Spec: research/market_os/SHARED_SHELL_WEBAPP_PRODUCTION_PLAN_2026-10-18.md in Macro #7949.

Execution method: Chairman-authorized Fabric delegation for eligible bounded work; parent performs reserved architecture, accepted-source integration and release decisions. A real Fabric capability refusal stays attached to its operation. Do not substitute native labor children or bypass a qualification fence.

## Global constraints

- Exact server flag MMX_SHARED_SHELL=1; any other value is off.
- The default production presentation stays under its existing flag until reviewed release configuration enables the new shell.
- Canonical initial legacy origin: https://www.mastermind-x.com. Exact approved beta parent: https://beta.mastermind-x.com.
- Protocol mmx.shared-shell.v1; validate origin, source window, generation and closed schema.
- No arbitrary HTML adoption, upstream proxy, token messaging, auth/cookie widening, route database or data-engine rewrite.
- One AppShell and at most one retained legacy document.
- Dark/light, EN/ZH;1440x900,820x1180,390x844 and320px stress.
- Original programme/carriers and every unknown effect remain intact.

## Review focus

1. Iframe navigation participates in joint session history: test actual Back/Forward across legacy and native routes, not only mocked router calls.
2. Root-relative assets and APIs retain Macro ownership; a path that looks harmless must not expose denied artifacts or overwrite Terminal /data semantics.
3. An identity switch must dispose old page state and preserve payload authorization; shell display claims are not entitlement proof.
4. A page dialog, terminal portal or scripted navigation can bypass anchor interception: test representative real workflows and retain the incumbent owner where needed.
5. Partial/no-result/unavailable/save-unknown states must not become success merely because shell hydration completed.

## Task1 — reconcile original source carriers

Files: the existing Macro #7949 and Terminal #859 branches; current handoff and source evidence.

- [x] Verify both original workspaces are clean and identify exact remote heads.
- [x] Fast-forward Macro original carrier to9b54c2d7f1f19a7371a7ee2102fb706f46e1b7ac.
- [x] Merge Terminal masterd6515f47232538161af8d3d4c27064165eda40fe into PR859 without conflicts; publish f1f2cc79c5961d84117d686caf87e5f41a9e9d79.
- [ ] Resolve the twelve Macro conflicts against exact main4f52d22596545cbd67b5143e188baf5660237024; preserve current market payloads, old return/account semantics and real receipt history.
- [ ] Verify source/paired-copy coherence with focused tests and git diff --check. Do not bless historical screenshots as combined-tree proof.

## Task2 — refresh coverage and export the route projection

Create scripts/export_shared_shell_routes.py and tests/test_shared_shell_projection.py in Macro. Consume existing scripts/build_product_page_registry.py, config/product_experience/page_registry_overrides.yml and the generated registry. Output terminal/lib/sharedShellRoutes.generated.json for the native consumer.

Interfaces:
- Input: exact Macro registry JSON, exact git-tracked site HTML paths and source SHA; current Terminal native route inventory.
- Output: schema mastermind.shared_shell_routes.v1, sourceSha, registrySha256, legacyPaths (exact concrete canonical paths), nativePaths, directory entries with page identity/route/archetype/navigation metadata, and explicit dispositions for excluded records.
- Family records map to actual tracked paths; no unrestricted runtime wildcard. The projection is generated, not hand maintained.

- [ ] Test that internal/lab/dev_only and admin/operator/denied entries cannot enter legacyPaths.
- [ ] Test nested source paths, family expansion, duplicate/native/infrastructure collisions, absent source and stale registry detection.
- [ ] Run the existing generator with exact sibling refs and a fixed as-of timestamp; preserve unknowns and report missing source.
- [ ] Export the projection and reconcile every live customer row. Counts must be derived from this run, not the historical331.
- [ ] Run focused tests and record projection/source digests. Commit only reviewed source and derived output.

## Task3 — pure route and message contracts

Create terminal/lib/sharedShellContracts.ts and terminal/lib/__tests__/sharedShellContracts.test.ts.

Interfaces:
- isSharedShellEnabled(value:unknown):boolean, true only for exact string1.
- resolveShellTarget(href,canonicalPath,shellOrigin,legacyOrigin,catalog): legacy/native canonical href, external href or blocked reason.
- readShellChildMessage(event,expected): a validated READY/NAVIGATE/CONTEXT_REQUEST/ERROR object or null.
- ShellRouteCatalog contains exact legacyPaths/nativePaths, not authority-changing user input.

- [ ] Exercise approved relative/nested URLs, query/hash preservation, modified transport markers, unknown paths, schemes, credentials, origin/config errors and collisions.
- [ ] Exercise exact origin/source/generation and closed variant schemas, including stale messages and extra token fields.
- [ ] Consume and independently inspect the contracted Fabric artifacts. The leaf may not create a repository or repair a host helper.
- [ ] Run the integrated Vitest file plus TypeScript checks before adopting the module.

## Task4 — native persistent shell host

Modify terminal/app/(shell)/layout.tsx, terminal/components/chrome/AppShell.tsx, terminal/components/AppNav.tsx and the existing preview stylesheet only where shared semantics require it. Create focused components under terminal/components/chrome/shared-shell/ for navigation/directory/legacy host. Create terminal/lib/sharedShellRoutes.ts and terminal/app/(shell)/[...legacyPath]/page.tsx.

- [ ] Validate the flag and route on the server; unknown/denied legacy paths return404.
- [ ] Put the legacy host outside the page subtree so valid shared-layout navigation preserves the shell. Preserve existing AccountIdentity, settings, onboarding and Brain ownership.
- [ ] Extend the one AppNav/MobileNav destination owner; reconcile #697's current independent mobile work before overlapping its files.
- [ ] Implement224px/72px rail,64px desktop header, min-width0 content and responsive mobile navigation using current tokens.
- [ ] Add a searchable All tools directory from the derived projection, with keyboard/focus handling, categories, selected state, no-results and unavailable behavior.
- [ ] Reuse SearchModal in pick mode and the incumbent universe/market-preference loader for global company selection. Do not invent watchlist callbacks or a new search backend.
- [ ] Add a beta entry redirect from/ to/macro.html while preserving normal production landing behavior.
- [ ] Add local loading/error/retry states that retain outer navigation.
- [ ] Verify native Analysis/Discover and other shared workspaces keep their real body/providers and active-symbol behavior.

## Task5 — Macro opt-in document bridge

Create templates/shared_shell_bridge.js and its paired site asset through existing owners. Modify common page-generation/chrome owners only after exact source inspection. Modify config/site_access.yml and app/deploy/Caddyfile for the new public asset and exact opt-in framing policy. Do not disable the default frame restriction.

- [ ] Install the bridge through the common HTML generation/bake owner; idempotent inclusion, no regex rewrite of arbitrary page internals.
- [ ] Activate only for a real approved parent and the explicit transport marker. Standalone pages retain current behavior.
- [ ] Hide only verified global-chrome selectors. Page headings, local tabs, charts, evidence, account actions and disclosures remain.
- [ ] Apply context through existing theme/locale setters without persistence loops.
- [ ] Use the same protocol fixture cases as the native validator. INIT/CONTEXT cannot carry authentication or user-write commands.
- [ ] Intercept qualified ordinary navigation before existing handlers where needed; preserve downloads, forms, modified clicks and original Terminal portal semantics.
- [ ] Send READY only after required bridge/context initialization. Bound errors and late messages.
- [ ] Prove original standalone page parity and embedded-mode behavior before broad regeneration.
- [ ] Re-bake existing artifacts through their owner without invoking data engines, then verify all admitted pages contain the compatible bridge.

## Task6 — real compatibility and state proof

Create terminal/e2e/shared-shell.spec.ts and focused Macro bridge/serving-boundary tests. Retain real screenshot and machine receipts in existing source evidence locations.

- [ ] Use actual current Macro page artifacts in the local integration server and the actual native shell; synthetic bodies are allowed only for isolated protocol tests.
- [ ] Cover Macro, US stocks, China, a regional dashboard, Sector Central #confluence, a live-heavy flow/Prophet view, research/evidence and nested dossier paths.
- [ ] Prove direct entry/reload/Back/Forward, canonical copied links, native transition/return, scroll/focus contracts and no duplicate shell.
- [ ] Test real local tabs/charts/dialogs/portal/downloads after repeated navigation.
- [ ] Test dark EN, light ZH, tablet, mobile,320px, enlarged text and keyboard dismissal/focus.
- [ ] Measure retained frame count, listener/subscription behavior, startup asset cost and readiness failure. Resolve concrete remaining risks; do not rerun broad tests for ritual.
- [ ] Report any not-yet-qualified route family explicitly and continue its repair before estate-complete acceptance.

## Task7 — identity, access and cache integration

Use existing Supabase and Macro account owners. Load their applicable source guidance before changes.

- [ ] Verify beta host cookie/refresh/callback behavior and exact allowed origins.
- [ ] Test guest, denied, expired and authenticated read behavior; use approved isolated/disposable fixtures for effects.
- [ ] Dispose stale user content on identity change and forbid authenticated-to-local fallback.
- [ ] Inspect response headers for personalized HTML/RSC/prefetch and protected payloads. Preserve private/no-store and data entitlement gates.
- [ ] Verify shell navigation itself creates no portfolio/watchlist/alert/save mutations.

## Task8 — source-managed beta release

Modify the existing deploy/configuration owners with a separately reviewed beta target. Do not use scripts/deploy_terminal.sh to rsync a worktree. Normal production remains on its incumbent service.

- [ ] Define beta service/upstream, immutable release manifest, environment flag, health marker and retained previous release.
- [ ] Pass the current CLEAN source preflight and exact protected-ref target admission through the incumbent release owner.
- [ ] Provision beta DNS through the existing provider and configure Caddy/TLS, cache/noindex policy and public routes.
- [ ] Build and stage the matched shell/bridge/projection assets; verify intended Host-header behavior before cutover.
- [ ] Complete required CI and independent review; remove Draft/HOLD only for the reviewed releasable candidate.
- [ ] Merge and deploy the admitted exact revisions through their real owners.
- [ ] Verify public beta TLS, release marker and full acceptance journeys; verify original production remains healthy.
- [ ] Prove rollback restores a compatible beta release without changing live data or user state.

## Task9 — programme return

- [ ] Update the same handoff with exact source/CI/review/deployment/browser receipts and worker adjudications.
- [ ] Mark only proven packages complete; preserve any exact remaining blocker with a concrete reviewable artifact.
- [ ] Record the next page-family native conversion behind the same route contract without turning it into a beta prerequisite.
