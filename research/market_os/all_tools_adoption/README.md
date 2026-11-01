# Shared Shell — source-fed All tools

## Current adoption — R41 reference parity and recovered verification

The source owner remains the embedded All tools controller in
`templates/nav_market.js`, paired with `site/nav_market.js`. Presentation remains
in paired `navigation-refresh.css`; `_site_nav.html.j2` includes the strict
opt-in host. Only Macro overview, Sector Central and Reports index opt in.
This is built source on PR7949, not merged, deployed or production-accepted.

R39 makes source-authored section headings searchable in English and Chinese.
Each public field is normalized separately so long bilingual copy cannot hide
later topic fields. URLs, badges, permissions, source ordering and market
selection are not a search taxonomy and are not changed.

After the Chairman reopened Studio Direct filesystem access, R41 recovered the
same clean worktree at b68658a649165ec683604d8f3ec449f273e35e13. A new parity
regression first failed on the stale reference, then passed after synchronizing
`src/all-tools.js` from the exact production marker block. Both now have SHA256
`49bc32c1bca12098c8a958cf686325fbc7f918304f1ad9f3892cce346b4249be`.
This also preserves the production shared-asset boot behavior; the reference is
not a second source owner and is not separately loaded into production.

Current source checks execute the synchronized reference rather than historical
bytes: the three Node suites pass **107/107**, mutation testing detects **12/12**
deliberate breaks, the template contract passes **20/20**, template/site sync
passes **105 pairs**, and the shared All-tools/nav/account pytest slice passes
**141/141**. The parity regression remains in `tests/test_all_tools_menu.py` so a
future reference fork fails immediately. Four recurring pytest cleanup warnings
for old temporary Chromium framework directories remain non-assertion noise; no
cleanup or permission change was used to obtain green.

R41 also finally executed the previously blocked real-Chrome R38 matrix. The first
17-case run passed 16 and reproduced one real 320px/light-ZH/double-typography
failure on Macro: wrapped category controls squeezed `.mmx-tools-body` to a 155px
scrollport while a long destination row grew to about 293px, so that row could not
be fully reachable inside the dialog. The smallest shared-owner repair keeps the
mobile category rail on one horizontally scrollable line (`flex-wrap: nowrap`,
nonshrinking buttons) instead of allowing it to consume the vertical reading
budget. The targeted reproduction then passed, followed by a full **17/17** run
across all three pilots. The paired CSS digest is now `edfd821b`, and the three
admitted static pilot pages carry that digest in both preload and stylesheet links.
The release key `20261001-all-tools-topics`, nav/account digest `28d0c024`, route
inventory, persistence semantics and pilot ceiling are unchanged.

The 320px double-type case is an application-token layout stress test, not native
browser 200% zoom, physical-device or assistive-technology certification. Current
native Paper renders remain design evidence, not runtime acceptance; deployment
and production proof remain separate gates.

## Historical R23 component record — retained, not current deployment state

**BUILT_NOT_PROVEN / DEFAULT OFF / NOT INSTALLED / NOT APPLIED TO PAPER**

Existing owner: WS:MARKET-OS / Macro PR7949 / `sol/market-os-shared-shell-design-20260924`.
This is the recovered R22 adoption component with R23 interaction repairs, not a new menu inventory, router, auth owner or production release.

## Product decision

All tools opens a mega menu first. Full browsing remains available inside it; the existing directory pages remain available as alternatives. Opening the menu must not force a page transition, change market preferences, reset research filters or imply a save.

The first view is prepared from the current source section. Every source category remains reachable. Familiar tool names, meaningful source groups, concise descriptions, source-authored blueprint icons, language variants and source tier badges are retained. Search is for tools; the existing stock search keeps its separate job.

## Current implementation

`src/all-tools.js` projects the incumbent product-navigation anchors at opening, preserving actual hrefs, prefixes, queries and hashes. It does not ship a copied fixed destination list or infer equivalent tools in another country. `src/_all_tools_menu.html.j2` is a default-OFF shared-header host. `src/all-tools.css` is a static stylesheet consuming the existing design tokens. `shared-header.patch` is the unapplied one-include hook. None of these files is imported into production by this directory.

### R23 repairs

R22 could disable a stale link after a navigation-source update, then recreate an enabled copy from its old snapshot during search, category selection or language redraw. R23 revalidates on every redraw and at click, auxiliary-click and context-menu boundaries. Once withdrawn within an opening, a destination remains visibly unavailable until explicit close/reopen refreshes the source. Other destinations continue to work.

The list does not silently reorder or erase the item the user was reading. The count distinguishes displayed destinations from unavailable ones. A focused destination retains its identity across language changes; a no-longer-usable focused item returns to the menu heading, with preventScroll. Typing retains input focus. These are source-tested behaviors, not browser or assistive-technology proof.

A local per-opening withdrawn map is presentation memory only. It is discarded on close/reopen and never changes server permissions, the source DOM, account preferences, saved work or routing. Valid anchors retain native navigation, including new tabs and modifier keys.

## Visual direction retained

The existing static stylesheet remains unchanged. Dark uses the shared graphite material and restrained luminance emphasis. Light uses white research material, crisp strokes and a pale inset note. Both retain the same information and actions; there is no parallel palette or runtime-injected material sheet. Desktop uses a bounded panel; phone uses a sheet with a scrollable body and reachable footer, with a short-height escape treatment. These are authored compositions, not measured browser layouts.

The user-supplied menu remains the visual reference: blueprint-like line drawings, spacious grouped destinations and concise explanatory copy. No new screenshot or award-level visual acceptance is claimed for R23.

## Verified in this recovery turn

- Exact R22 controller and three original test/fixture files were reconstructed and matched to their Git blob hashes before editing.
- The first new test run terminated with SIGKILL while formatting a failed cyclic DOM-object identity comparison. Assertions were changed to boolean identity checks without changing the behavior under test. The meaningful baseline then ran: **21 cases, 6 pass / 15 fail**.
- The repaired component initially passed those 21 cases. Rejoining the original 70 tests exposed one singular/plural status-copy regression, which was repaired without modifying the original tests.
- Final suite: **97 passed / 0 failed**, comprising the unchanged 70 original cases and 27 R23 cases.
- **12 deliberately broken variants were detected** by those same tests. Source syntax passed.
- R22's 20 Jinja/static-style checks are historical evidence, not rerun claims. The template and stylesheet are unchanged.

All execution above is Node plus a recording DOM double. No browser was launched. No Paper mutation, real page installation, production account, entitlement or human-comprehension proof occurred. No earlier browser/host refusal was bypassed.

Run from this directory:

```sh
node --test tests/navigation.test.cjs tests/controller.test.cjs tests/refresh-boundaries.test.cjs
python tests/mutation-check.py
python tests/template-contract.py
```

The last command requires Jinja2; it is retained from R22 and was not rerun in that research phase. The updated mutation script uses only Python standard library and Node.

Adoption update (2026-10-01): `tests/test_all_tools_menu.py` now extracts the shipped controller from `templates/nav_market.js`, executes the 97-case Node behavior contract, and checks the Jinja/template/site integration under the existing `unrun-nav-chrome` product-navigation owner in `.github/ci/legacy-jobs.yml`. No parallel workflow, job, catalogue, router, store, or navigation owner was added. Historical R22/R23 evidence below remains historical rather than being rewritten as current release proof.

## Recovery and source identity

R22 staged subtree: `84a7773b3063f8b8d3fc0bef574215b17948834f`. All 13 blob entries were observed in a fresh recursive tree read. Its original controller was `78e5ad34eb296df6413a3fa8dff952e6a125d598`, SHA256 `fb0d93119b85c04c87f2d8fe3ce6b3e9b4e195f56e04c7f7a5a5f2e699c9a736`.

R23 controller: `1a616e0ee1bfc7dce63783ca7b53201f254fc69a`, 21,188 bytes, SHA256 `991dc0095a40e18199b9c4b12f041f71304edd396c464a491161b3a37637be5c`.

The interrupted R22 root-tree call has no returned root SHA. Its possible effect is an immutable, unreferenced object; no commit/ref-update call was dispatched after it. The actual PR branch remains at `7630295d0caf7287bc67a146fcd51dde2cca1bd7` before this publication. That old creation is not replayed and its existence is not claimed. R23 publishes a distinct revised tree while preserving the verified R22 source and evidence.

R22 inspected product source at `dea858959c6f37122fd500dd673c44b271f19fa9`; shared header fixture blob `9848b9366d43553f9d69997ecdb0a07e15e4ad2b`; nav controller `4edee693e1e6d4391de3482b2a618057df686e56`. They are compatibility inputs, not a current full-site acceptance claim. Historical R22 README/qualification/mutations are retained under explicitly named evidence paths.

## Remaining installation gates

Adopt through the existing product header/navigation/stylesheet owners, not through per-page header copies. Qualify paired template/site assets, cache keys, serving access and default-OFF inclusion. Current pilot ceiling remains `/macro.html`, `/sector_central.html`, `/reports.html`; no page is enabled here. Preserve anonymous/public chrome and all native workspace/Terminal semantics.

Then register tests with the existing owner and obtain real dark/light × EN/ZH × desktop/phone visual and interaction proof: actual navigation transforms/populations, ordinary and modified-link activation, body scroll, focus/return, foreign overlays, short screens, stylesheet failure, browser back/forward and actual source withdrawal. A browser menu already opened before a withdrawal cannot be revoked by client JavaScript; backend access remains authoritative.

The R18 failing assertion, three R19 consumer failures, current-base merge compatibility and PR7129 persistence-before-rebind boundary remain separate release requirements. No menu test waives them.

## Native state

The newly selected Mastermind Paper app exposed all five actions, but its inspect and catalog calls both returned JSON-RPC32600, `Session terminated`. No content call was made through it. Studio Direct inspection worked, but its backend still identifies M2, not the assigned M1. No fallback edit, file transition or native working-indicator change occurred. Repair/reconnect the intended Paper session before native composition; do not infer write permission from an unrelated source test.
