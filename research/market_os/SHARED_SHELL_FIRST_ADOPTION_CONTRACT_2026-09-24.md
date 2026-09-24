# Shared application shell — first-adoption compatibility contract

Status: design candidate with a verified existing-source baseline. NOT implementation-admitted, NOT deployed, NOT an accepted full-site design.

Operation: `market-os-shared-shell-design-20260924-sol-001`. Existing parent: `WS:MARKET-OS`. Sole branch / Draft PR: `sol/market-os-shared-shell-design-20260924` / Macro #7949. Chairman commission: Sol leads the common Macro/Terminal experience, with editable mockups and refinement before site-wide release. This contract does not displace any incumbent source writer.

## 1. The useful pilot

A user can enter the US market overview, inspect the stock board or a native sector view, open one exact security in the existing Terminal, use the existing watchlist capability, and return to the originating research context. A second native market tests whether the frame really generalizes without relabeling US content as Chinese content. New navigation is successful only when the destination works or presents its intentional access/unavailable state.

The machine job is to project existing route, market, listing, access, data and personal-state owners consistently. The shell does not generate a new signal, fused rank, forecast, sizing recommendation or trade instruction. Layout migration must not alter the intelligence behind the pages.

### First adoption set and boundaries

| Consumer | Source boundary | What the pilot may change | What remains owned elsewhere |
|---|---|---|---|
| `/macro.html` and `/us_stocks.html` | `templates/dashboard.html.j2`, `scripts/build_site.py` | Outer page frame and placement of existing navigation/controls; qualify BOTH summary and dense-board output | Risk/participation interpretation, action lanes, data builders and generated payloads |
| `/china.html` | `templates/china.html.j2`, `scripts/build_china.py` | Same outer-frame contract with native China context | China calculations, risk semantics, event/data coverage and native content |
| `/china_intel.html` | Existing distinct China Intelligence template/builder | Preserve a clearly named route in the new navigation; compose its candidate before promoting it as a new default | It does not silently replace `/china.html` or inherit US modules |
| US Sector route and Confluence | Existing `sector_central.html.j2` and `si_workspace.js` | Preserve its six native entry points inside the common frame | Sector redesign, state/filters, entity hashes, lazy consumers and MM-07 serving repair |
| China Sector route | Existing China template/router | Preserve five native entry points, not six copied from US | No fabricated Money & Breadth view or cross-market entity equivalence |
| Security entry and Terminal return | Macro `theme.js`, `stocktable.js`, `terminal_overlay.js`; Terminal `originNav.ts` and current shells | Consume the existing handoff; do not introduce another launcher, modal, history or session owner | Listing resolution, quote/data delivery, auth, watchlist writes and chart lifecycle |

This is a pilot boundary, not permission to edit every listed file. The first implementation packet must identify exact current hunks and custody after design approval. The filename-level bindings above are verified; exact outer-header insertion points have not been finalized. A source-line extraction attempt was safety-refused and is not represented as completed.

Terminal's focused mockup describes the desired common experience. The first Macro frame adoption must not require a simultaneous rewrite of Terminal's native navigation. Use the existing Terminal first, and migrate its visual frame separately through its own owner after the shared behavior is proven.

## 2. Layout ownership — protect the working portal

The proposed Macro frame owns the global sidebar, top-level search/market context, page-heading boundary and responsive placement. Each workspace owns its tabs, filters, tables, charts, content and evidence. The existing account/settings, search, watchlist, alert and Brain owners remain singular.

**Preserve document scrolling in the first pilot.** `terminal_overlay.js::lockDashboard` records `window.scrollX/scrollY`, fixes the body and marks other body children inert/aria-hidden. `unlockDashboard` restores body styles, those exact document coordinates and desktop focus, including delayed restoration. Moving the main scroll owner into a new inner container is therefore a compatibility change, not a cosmetic CSS decision. Do not make it in the first frame slice without an explicit owner-supported test and design change.

**Keep the portal in its existing document-level ownership.** Do not nest/reparent it inside a transformed, clipped or inert sidebar/workspace subtree. Do not add a second keyboard trap, body-lock manager, overlay history guard or launcher. Mobile drawer integration must compose with the existing overlay/keyboard owner rather than assume two modal locks can safely coexist. This is a source-backed compatibility constraint; the proposed nested-portal browser falsifier was not executed.

The frame must not remount the current workspace merely because the sidebar collapses. Local table scrolling is not document scrolling; preserve deliberate internal overflow without making the entire application a new scroll container. Keep overlays outside new frame-local clipping/transform effects. Existing lazy chart consumers must still mount after their native view becomes visible and measurable.

The implementation must scope new chrome styles so they cannot rewrite page-global table, panel, heading or dialog rules. Retain existing IDs, data attributes and legacy hrefs consumed by current JavaScript. Do not copy an entire old page inside a new frame and leave duplicate navigation running underneath.

## 3. Country and route context

The selector changes the current viewing context only. Explicit URL/route context wins over a default preference. It does not mutate followed/enabled markets, the derived home field, holdings, watchlist membership, entitlement or the selected listing.

| Current task | Required transition |
|---|---|
| US overview -> China overview | Use the established native China overview; new country label and corresponding loading/content state change coherently |
| Native Sector subview -> another market | Keep the subview only when its consumer meaning is qualified; otherwise present named alternatives before leaving the current task |
| US Money & Breadth -> China | Do not fabricate an equivalent China tab or carry US data under China context |
| Sector -> HK/Canada | Existing baskets and narrative rotation remain distinct named choices until same-workspace equivalence is actually established |
| China overview versus China Intelligence | Preserve both jobs and URLs; a visually attractive hub does not authorize silent consolidation |
| Global comparison versus International | Preserve existing destination meanings; do not create a new global landing page or move the owning `intl.html` program |
| Exact security selected | A market choice cannot silently replace it with another listing; security selection remains explicit and owner-resolved |
| Target denied, stale, missing or unknown | Keep the actual target identity and typed reason; never show previous-country content as the new country's reading |

Use existing navigation/route definitions and their current ownership. This document is not a second runtime route catalog. No new global localStorage preference, registry table or shell-managed state service is introduced. Keep existing public URLs and bookmarks; a framework or URL migration is not a prerequisite for the pilot.

## 4. Terminal continuation has two different modes

### Same-document portal

Macro already opens the Terminal through `window.MDXTerminalOverlay`. The original document survives. Existing portal code owns history guard, body scroll locking, loader lifecycle, close, desktop warm-frame behavior and mobile remount behavior. Macro stock rows also enter through the same portal.

For this mode, pilot proof must cover original page URL/hash, selected group/filter, document scroll position, keyboard return and functioning controls after close. It must also cover reopening: desktop retains a warm frame while compact/mobile creates a fresh frame. A displayed loader or iframe load fallback is not proof that a real chart or selected security became usable.

### Direct / modified-click / new-tab entry

Macro's `terminalUrl` carries `from=macro` plus an encoded `ret=location.href`. `terminalExistingUrl` preserves existing destination parameters while attaching return context. Modified clicks must retain native browser behavior. On the Terminal side, fresh entry context outranks old session context.

The current `backToMacro` implementation sends `terminal:close` for a validated embedded session; otherwise it navigates to the remembered Macro URL. It does NOT simply call browser Back after arbitrary Terminal sub-navigation. One preceding source comment describes a back shortcut, but the executable implementation and its explanatory inline comment explicitly use `location.assign`.

**Do not over-promise return-state persistence.** The direct/new-tab path carries a URL, not a snapshot of unsaved in-memory filters. Exact route/hash restoration is a different claim from restoration of every ephemeral control. Preserving such a control across a new document requires an existing workspace-owned URL/state contract; do not create a second shell snapshot store to manufacture the promise.

Preserve meaningful destination parameters, listing suffixes and return context. Test them at both sender and receiver. Keep strict expected-origin and expected-frame checks; navigation convenience cannot weaken identity, message or open-redirect boundaries.

## 5. Visual correction actually made in this phase

On the existing Paper file `01M2WGNCX9475G79JRKJTCM08P`, review page `p-D-0`, the existing Sector artboard `UBT-0` now shows **Overview / The map / What's moving / Money & breadth / Explore / Confluence**, with The map active for the displayed map content. No replacement artboard or alternate design carrier was created.

The first three labels were corrected in place; three missing tabs were added to the same navigation row. Source-backed six-view preservation now has a visible counterpart. The map, inspector, footer and global sidebar were retained. Original Sector/China/International design pages and shared tokens were not edited.

Targeted tree readback shows six tab frames; Confluence is visible and measured at72x40. Final screenshot `13-sector-native-six-views-final.png`, 1440x900, was visually inspected. SHA-256: `60a84fae1e3a94c5b3bae7ab8a4b3c94f441b91ca02083815ff3a7a8694bcbfd`. Tokens remained `5ae876bc`. `finish_working_on_nodes` returned OK for this artboard.

Review verdict: six labels align and fit; active treatment matches the map; text is legible at desktop review size; existing content and disclosure remain visible. This is a static design review, not interactive tab, mobile, bilingual or production proof. The earlier three-tab screenshot remains historical, not the current first-adoption contract. The separate popup scaffold still depicts its older, uncomposed state and must not be mistaken for an updated design.

## 6. Executed baseline — 34 existing tests passed

Fresh code inputs for this bounded compatibility phase:
- Macro: `dd34ca7445635edb1df9649febbb289419f80b1c`.
- Terminal: `54eb1caa799bd6f8f951cbe582be0f8ac9c7b0af`.
- Protected Skillpack: Mastermind `819abc8c23609cdded2b33f6e1bfc7854bd5c847`, version1.0.1/bootstrap1, same previously loaded procedure revision.

Only17 exact source/test files were downloaded for this new portal/frame question. The previous334-row registry qualification was NOT rerun. A disposable test environment was created on MacBook-Pro-9; no product checkout or application dependency files were changed.

Existing tests were executed unchanged:

```text
python -m pytest source/macro/tests/test_terminal_overlay_contract.py \
  source/macro/tests/test_terminal_overlay_closed_state.py \
  -q --tb=short -p no:cacheprovider --junitxml=baseline-junit.xml

.................................. [100%]
34 passed in 0.04s
process exit 0
```

The first suite verifies source contracts including paired assets, the shared portal, strict message guards, history ordering, scroll/focus restoration and mobile frame handling. The second evaluates the existing stylesheet's closed-state cascade. These34 passes are an existing-code compatibility baseline, not tests of a newly implemented shell, not the full repository suite and not fresh real-browser evidence.

Native scratch evidence: `/tmp/market-os-shared-shell-design-20260924-sol-001/pilot-compatibility-dd34-54eb` on MacBook-Pro-9. `sources.json`, `baseline-tests.txt` and `baseline-junit.xml` retain inputs/output. Test process98790 was read back as exit0. Scratch is convenience evidence, not another durable state owner.

### Browser and inspection limitations

A local synthetic-frame browser probe was prepared but NOT RUN. The append containing the actual interaction cases was safety-blocked before dispatch. Same-carrier readback showed the59-line incomplete prefix unchanged. No local browser server or browser test was started by that file; no case or screenshot is claimed. Do not append/run/recreate that denied operation through another payload or carrier without actual permitted recovery.

A separate extraction of outer body/header/navigation line positions from the two pilot templates was also safety-refused and not retried. Exact insertion hunks remain unqualified. Earlier Paper/mobile/popup/US-fit/extraction holds remain unchanged. The independent six-tab Sector correction did not perform any of those refused effects.

## 7. Acceptance matrix for the candidate implementation — still owed

| Scenario | Acceptance evidence |
|---|---|
| US overview and dense stock board share the new frame | Both real outputs usable, no duplicate header/search/settings, no intelligence/body regression |
| Native China route in same frame | Correct country content, existing access/data states, no US substitution |
| Six US / five China Sector views | Direct hash, click, refresh, Back and lazy-consumer activation or legible intentional failure |
| Portal close and reopen | Correct URL/hash, retained workspace state, scroll/focus policy, no residual painted loader |
| Direct/new-tab Terminal return after internal navigation | Exact intended return URL, meaningful destination parameters retained; ephemeral-state limits tested explicitly |
| Different instrument on warm re-entry | Actual selected listing and chart correspond to the new input, not stale previous security |
| Invalid or unrelated frame message | Existing source/origin guards reject it; no close, state change or privilege widening |
| Slow, denied or failed Terminal launch | User can recover; loader fallback is not reported as successful chart readiness |
| Sidebar/drawer/portal interaction | One coherent focus/scroll-lock behavior; no inert visible workspace or trapped background focus |
| Narrow EN/ZH, supported themes and desktop | Controls and long labels fit; evidence distinguishes Chromium emulation from real Safari/iOS |
| Save and return | Existing canonical watchlist receives the intended listing; no duplicate store or portfolio mutation; use a designated disposable proof identity and exact cleanup |
| Excluded surfaces | Macro fragments, embeds, account utilities, public editorial/marketing and operator/developer surfaces do not receive an accidental full application frame |

Do not copy these rows into another test registry. They are the first-pilot acceptance contract; existing test/evidence and page-registry owners record actual results.

## 8. Next gate, rollout and rollback

Complete and review the integrated design/interaction set, including the missing country/menu/mobile states. Then freeze the smallest implementation plan with one admitted shared-chrome writer and exact current hunks. Reconcile #6872 navigation/registry overlap and existing page owners; keep MM-07 as the Sector serving dependency. Passing source tests or one static mockup does not clear those gates.

Roll out a bounded representative page family through the existing release mechanism, with the previous frame recoverable per family. Do not flip every generated HTML file at once. Rollback concerns presentation only: it must not roll back accepted data, personal-state or signal changes. Preserve paired/bundled asset publication and exact candidate/served identities.

Parent mission remains incomplete. This phase makes the first-pilot boundary concrete, verifies the existing portal baseline, and repairs the visible native-view mismatch. It does not grant merge, deployment, implementation custody or production acceptance.
