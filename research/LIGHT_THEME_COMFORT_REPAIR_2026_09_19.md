# Light-theme comfort repair — 2026-09-19

## Outcome and authority
Chairman request: repair overly harsh light mode across the macro site centrally, preserving existing pages and dark mode. Current conversation directly assigns delivery; no worker has been commissioned for this operation.

- Operation/carrier: `claude/light-theme-comfort-20260919-astra` in its same-named isolated macro worktree.
- Protected Skillpack: `mastermindx-market-intelligence/Mastermind@9e796168b467c17d9853f139c4e4a6ccdf3a3a87`; INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT loaded, schema v1 / pack 1.0.1 / bootstrap 1.
- Implementation base: `af92792954e1ad8a4812cf0e73a2dc54dac0672a`; relevant guide/design/theme blobs unchanged from initial macro observation `f372390ce777301890709b7236db5cc4efc3e0db`.
- Direct execution rationale: PRINCIPAL_JUDGMENT for cross-family material/contrast decisions, then LOWER_TOTAL_OVERHEAD for one shared patch. No duplicate worker, provider activation, or control plane.

## Verified diagnosis
`templates/theme.js` unconditionally adds `.soft-contrast` and injects a second palette. Its light canvas is `#e8ebf1`, panels pure white, and its selector overrides theme.css. The self-contained family consumes `--card` and `--ink`, which that palette does not remap. This explains different material/ink treatment on otherwise adjacent pages.

Source census at the implementation base: all 281 top-level generated HTML pages load theme.js; 201 also load theme.css and 80 do not. Motivating routes (verified from their builders): `/allocation_canada.html`, `/narrative_radar.html`, `/flow_velocity.html`. `/baskets_canada.html` is an additional shared-family check, not the first screenshot’s route. User-provided screenshots are the visual complaint baseline; not a fresh production-browser receipt.

## Frozen implementation boundary
Canonical presentation remains `templates/theme.css`. Move the existing contrast override into a marked CSS block; the existing `lib.site_assets.emit_theme_js` exports that exact block for the self-contained family. The standard family consumes the stylesheet early; the identical existing compatibility projection also keeps warm, older stylesheet caches coherent. No new theme store, theme toggle, palette owner, stylesheet loader, or page-by-page redesign.

LIGHT TREATMENT: cool `#eef1f5` canvas; near-white `#fafbfd` panels; nested `#edf1f6`; slate `#334155` body/heading ink; `#536176` secondary ink; restrained structural lines and smaller shadows. Legacy `--card`/`--ink` inherit canonical neutral surfaces/ink in light only. Reduce the light-only ambient wash; do not lower opacity on text or whole containers. Keep market-direction, severity, and action colors on their existing semantic tokens; validate their contrast rather than silently flattening them.

DARK TREATMENT: preserve the existing effective soft-dark palette byte-for-byte, including `--bg:#0d1018`, `--panel:#151820`, `--panel2:#1b1f28`, `--text:#c8d0dc`, `--line:#3a4150`. No typography, geometry, chart, navigation, copy, data, or signal changes in either theme. Language-dependent direction meanings must remain intact.

This is a bounded material repair, not an archetype migration. The existing page layouts and information depth are references to preserve, not permission to simplify content.

## Acceptance and proof
- Source/production asset pairing and third bake-token fallback must agree.
- Canonical CSS export is fail-closed; missing/duplicate markers cannot silently ship a stale palette.
- Browser-free tests measure neutral and semantic ink contrast on actual defined surfaces; existing Prophet ink and design-foundation tests remain binding.
- Canonical capture evidence: light/dark × EN/ZH × desktop/mobile on both stylesheet families, including all three motivating routes, plus representative dashboard/table/chart/navigation pages.
- Verify light-to-dark switching, no new horizontal overflow, and unchanged dark appearance on the real path. Production proof is distinct from tests, PR, merge, and asset publication.

## Continuation checkpoint
Last effect: central source/emitter/sync repair and paired site assets implemented locally. The existing anonymous canonical capture tool is now running successfully after installing its missing matching Chromium dependency. An earlier custom Chrome command was not executed (tool safety-status check); no production effect is claimed. The first capture correctly reported an erroneous guessed route as uncaptured; the canonical builder proves the correct route is /narrative_radar.html, now in the final five-route matrix. No failed capture is represented as a pass.

Next: complete the canonical browser matrix and receipt, publish this exact carrier, reconcile binding CI, then verify merged/cache-versioned production delivery. Keep the same branch/carrier. Do not redo other sessions' page redesigns, China restoration, Forex tooltip repair, chart engineering, or CI/runner recovery.


## Verification checkpoint
- 112 targeted emitter/token/neutral/Prophet-ink tests pass. The 143-test combined pass count included design-foundation tests; its single failure is inherited: `test_no_consumer_wires_the_new_primitives_yet` rejects existing `.skel` consumers in two unchanged templates. Executing the HEAD version of that test against the HEAD stylesheet reproduces the same failure. Do not weaken it inside this palette repair or call the whole suite green.
- Design added-line guard: zero blocking additions; existing estate debt is unchanged.
- Runtime style-injection ratchet: 195 files scanned, 44 injecting, 87 hits, passing. Removing obsolete prose reduced the scanner's markup-hit allowance by one for each theme.js copy; only those two existing entries were reduced.
- Source/production pair check returns zero divergent assets; template and emitted JS parse with `node --check`.
- Light Hold now derives from readable secondary ink, and light Avoid ink mixes are deepened in EN/ZH; the existing complete 80-cell verb/surface/theme/language test plane passes without lowering its contrast floor. Dark tokens remain unchanged.
- Inventory includes 11,814 generated HTML consumers of theme.js, including 281 top-level pages. This is source coverage, not a claim that every route was visually reviewed.
- Cache publication owner remains the existing render lane: `.github/workflows/render.yml` invokes `scripts.optimize_assets` before publication and after overlapping-main reconciliation. A covering render must actually publish refreshed hashes; a running/queued render is not that proof. Do not commit 11,814 hand-edited pages or create another publisher.
- Fresh main `e338508d91bca30fadf9c0bbac3f154bf02f81de` adds an independent cash-runway CSS block far below this repair. Preserve that addition at merge; it is not an invalidator of these material decisions.


## Browser and publisher proof checkpoint
- Canonical anonymous browser runs captured **64/64 states**: six routes × desktop/mobile × EN/ZH × light/dark = 48 rest states, plus 16 actual hover/focus states on Canada allocation. The exact screenshot routes are now confirmed from their builders: allocation_canada, narrative_radar, and flow_velocity.
- All six inspected routes have no document-level horizontal overflow in the canonical metrics. Separate inherited/local-server diagnostics remain visible: baskets_canada calls an undefined `renderFormingNarratives`; the static server cannot supply VPS live/WebSocket endpoints on Forex/Macro. These are not represented as production failures or fixed by this palette change.
- The existing native-browser Prophet ink probe reports all 80 verb/surface/theme/language pairs above 4.5:1 (worst 4.55). Its sources are the actual stylesheet and rendered card macro, with no lowered threshold or color override.
- The bounded committed acceptance packet preserves all eight rest cells for each of the three screenshot routes and the four required desktop EN dark/light hover/focus cells. PNG bytes, digests, applied state and capture-tool identity are untouched. `capture-full.json` in each evidence directory preserves the unabridged canonical capture metadata; additional reviewed page/interaction frames remain local rather than duplicating a large full-page image corpus in Git.
- A further publish-path defect was prevented: the stripped-down no-PyYAML guard must not treat material CSS as an opaque bake token. `lib/theme_materials.py` is a stateless stdlib reader of the existing CSS source, shared by emitter and guard. The guard pre-bakes that known CSS before checking its invariant token segments. A new test proves it rejects a stale standalone projection even when both CSS copies match. This refactor leaves the captured emitted JS bytes unchanged.


## PR 7466 continuation: release-check repair
Current Chairman instruction continues the original site-wide delivery scope. Re-fetched protected Skillpack at `9e796168b467c17d9853f139c4e4a6ccdf3a3a87`; previously loaded companion files remain byte-identical; RECONCILE_STATE additionally loaded from that same commit. Carrier head before repair: `8a97a1808dbac37a9644a28f708580719180a1a6`; no active prior mutation or replacement worker.

Concluded CI run `35480528739` rejected exactly two owned release dependencies: contract-delta requires the new `lib/theme_materials.py` in intelligence-registry's exclusive import closure; research-screener's exact-bake test detects old cache stamps after the theme asset change. Repair widens only that job's source path and invokes the existing screener `bake_html` against its unchanged committed payload. A normalization assertion proves generated HTML differs only in content-version query stamps. Do not lower test floors or rebuild research data.

Fresh main `01896d6da34d67df45056dd82795be6c8cbf187e` leaves governing guides, source emitter, theme JS and screener code/payload unchanged. Its independent cash-runway CSS addition remains preserved by the merge. Vercel preview rate limit is separately reported, not a VPS production deployment result or a claim that CI passed. Next: exact-head revalidation, release gate reconciliation, canonical asset version publication, public-browser proof.

Direct-origin diagnostic lane: the Studio SSH read request was blocked before execution. No SSH mutation occurred and this session will not switch tools/identities to retry that request. GitHub's existing render/pull publisher and anonymous public-browser/HTTP verification remain independent permitted release paths. Public checks still observe the old references (`theme.css?v=d41ce2d4`, `theme.js?v=48082a1e`) on the three motivating routes.


## Mixed-version and current-base integration repair
The initial two CI repairs passed 145 targeted tests, including the complete exclusive import-closure check. Repair head `c308e2e898431b9f394cf31a101109b626176ec7` was pushed and its remote SHA read back before any further branch change.

A bounded integrated-tree check against main `01896d6da34d67df45056dd82795be6c8cbf187e` produced tree `e484486c7c7fadee680c241f331f4178ef343214` and found a REAL template/site mismatch: main's accepted cash-runway CSS was absent from the paired generated asset. Therefore a history-preserving source join was necessary for asset composition, not to make ancestry current. The source join preserves that CSS and its existing tests/evidence; paired assets and the screener's stamped fixture are emitted from the integrated sources. No research inputs were recomputed.

The existing Chromium ink probe then tested prior CSS plus the new exact emitted material projection. It reproduced four small-text failures (EN/ZH Hold and Avoid chips, ratios 4.43–4.48). `mixed-version-before.json` preserves this negative proof. New regression cases reproduce those same four failures without fetching Git history. The calibrated Hold/Avoid inks now reside INSIDE the canonical exported material block, so new JavaScript plus older CSS receives the same readability repair. This changes mixed-version compatibility; fresh-sheet colors and all dark tokens are preserved. A selector-list test also pins the CSS rule that the strongest matching selector controls specificity.

Release remains pending fresh exact-head CI and actual published asset hashes. No screenshot or test is represented as a production deployment.


## Integrated candidate verification
- 225 targeted emitter, token, canonical/legacy contrast and research-screener tests pass. The earlier import-closure proof passed as part of the 145-test repair run; no new imported path was introduced afterward.
- Existing native Chromium probe: 80/80 current-sheet and 80/80 pre-repair-sheet pairs pass, minimum 4.55:1, maximum corresponding-ratio difference zero. Both use the actual soft-contrast boot class and exact emitted compatibility CSS. The four negative cases are preserved rather than erased.
- 99 template/site pairs match; both JavaScript sources parse; runtime-style ratchet passes. The committed visual-evidence gate passes. Existing normal-render screenshots are retained as the preserved layout/material design reference; the compatibility change is separately bound to the before/after native-browser receipts. No new production screenshot is claimed.
- Release ownership remains PR #7466. Do not repeat completed screenshot/contrast work unless its source or behavior changes. Next is fresh exact-head CI and canonical asset publication, then public browser proof on all three motivating routes.


## Coverage correction — parsed consumers, not string matches
The final source census parses actual script src attributes and resolves every
relative path. Of 11,814 generated HTML documents, 11,764 directly load the SAME
root theme.js, another 30 use the shared theme.css without a direct script, 10
are redirects, and 10 are independent public/utility/preview surfaces. The
initial all-pages JS count above was a substring count: it matched the common
data-base shim's comment. This parsed result explicitly supersedes that claim.
The independent marketing/utility surfaces are not restyled by this dashboard
repair, and no source inventory count is a visual acceptance claim. The exact
paths and classifications are in asset-consumer-census.json.

Current source and material work are complete for PR #7466; do not expand this
repair into marketing redesigns, archival previews, or other sessions' page
layout programs. The latest exact-head CI must conclude before release; the
existing render/pull publisher must publish current hashes before live proof.
