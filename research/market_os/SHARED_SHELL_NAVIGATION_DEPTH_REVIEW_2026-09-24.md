# Shared shell — desktop navigation depth review

**DESIGN CANDIDATE. Not implemented, interaction-tested, approved for release or deployed.**

Operation: `market-os-shared-shell-design-20260924-sol-001`. Parent: `WS:MARKET-OS`. Sole carrier: Macro #7949 / `sol/market-os-shared-shell-design-20260924`. Chairman intent remains a common Macro/Terminal experience, with editable mockups and refinement before site-wide release. Sol retains design/integration responsibility; incumbent implementation and data owners are unchanged.

## New user capability at the design level

The review set can now show how a reader finds a deeper existing desk without expanding the entire website in the permanent sidebar. This complements the earlier overview, Sector and Terminal compositions; it does not replace the held country-popup or mobile studies.

Paper file: `01M2WGNCX9475G79JRKJTCM08P`, MASTERMIND PAGES.
Review page: `p-D-0`.
URL: https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0
New artboard: `UQV-0`, **08 · All tools · Desktop navigation depth · 1440**, 1440x900, at canvas7020,0.

The expanded Markets group has four 187x40 secondary rows. All tools is the selected destination; Markets is merely disclosed. The main directory shows nine example route entries in three purpose-based groups, explicit market/asset scope, and a shortcut to the existing Confluence view. These are selected examples for layout review, not a complete route inventory or an assertion of access/data availability.

## Recommended interaction model

**Compact primary navigation plus one-level disclosure and a directory projection.** Reject a permanently expanded list of every page and reject a hover-only, multi-level flyout maze. Keep the existing global/sidebar, workspace tabs and local controls distinct.

A disclosure changes which child links are visible, not the current page, market or selected security. It is a real keyboard-operable button in implementation, with expanded state exposed; its child destinations are links with normal modified-click behavior. Do not overload one undifferentiated click target to both navigate and expand. When a group heading also needs a landing-page link, give navigation and disclosure separately named controls. Collapsed-rail and mobile behavior still require their own accepted design/proof.

Expansion is presentation state owned by the existing shell component, not a new persistent navigation service. Collapsing the sidebar must not remount the workspace or mutate personal data. For long localized labels or smaller desktop heights, preserve the existing control floor and readable wrapping; allow the navigation region to scroll deliberately while keeping account controls reachable. The desktop screenshot alone does not prove those cases.

**All tools is a view of existing route ownership, not another catalog.** Reuse the established page registry for qualified identity/eligibility and the owning navigation definitions for destination labels and routes. Reconcile differences in those owners. Do not hand-maintain an independent directory database, runtime route map, search index, entitlement list or compliance ledger. No new production URL or registry schema has been assigned by this mockup.

The existing global search is the intended search entry. A scoped Tools result mode may project approved route metadata there; it is not implemented by this design and must not create a competing search service. Directory categories filter the visible route projection. Empty matches, unknown capability and access denial remain different states; no directory count may imply that raw registry records are all customer destinations.

**Viewing context and tool scope are separate.** The screenshot retains United States in the global context while explicitly marking the directory as All market scopes. An International or asset desk is not relabeled US. A cross-scope link names its actual destination before navigation. Opening it must not change followed/enabled markets, holdings, watchlist membership or selected listing by implication. User-supplied search terms may filter route metadata, never widen access.

## Route evidence and non-duplication

Bounded source reads: `templates/nav_market.js:205-268,390-478` at Macro `25fb8fa805d611727078f65626f2c3b0388070b3`; blob `4edee693e1e6d4391de3482b2a618057df686e56`. The blob matches the previously inspected menu version. No adaptive JavaScript evaluation, complete menu extraction or refused test-source inspection was performed.

| Visible example | Existing destination | Preserved meaning |
|---|---|---|
| Market dashboard | `macro.html` | US market overview |
| Market structure | `market_structure.html` | Positioning, dispersion and weekly range |
| Intraday flow | `intraday_flow.html` | Native session board; existing conditional visibility and delayed-data semantics remain |
| World dashboard | `intl.html` | Existing International cross-market dashboard; not moved to markets.html |
| Country cycles | `country_cycles.html` | Distinct country/region comparison |
| Global market cycles | `markets.html` | Distinct market-cycle comparison |
| Commodities | `commodities.html` | Existing commodity desk |
| Forex | `forex.html` | Existing currency desk |
| Bonds | `bonds.html` | Existing rates/credit/duration desk |
| Confluence shortcut | `sector_central.html#confluence` | Alias to the retained native view, not another scanner or another consumer |

A route string in source proves neither deployed serviceability nor entitlement. Conditional rows must obey their original publication/access behavior. The Confluence shortcut does not resolve the separate MM-07 serving defect or prove its current production usability.

The selection is illustrative, not the final taxonomy. The current directory mockup does not exhaust China, Hong Kong, Canada, research, crypto or other tools. Missing example cards must not become deletion decisions. The earlier334-row qualification and its fragment/utility/operator exclusions remain unchanged; it was not rerun.

## Visual verification actually performed

Used the incumbent Paper client on m2studio, process90003, after identity and targeted sidebar readback. Added one independent artboard on the same review page, cloned only common chrome into it, and edited those clones. The prior six artboards and original China/Sector/International reference pages were not modified. No shared tokens changed; Inter availability and token hash `5ae876bc` were checked.

Incremental screenshots were inspected. Two small asset-scope badges initially wrapped; their new-study text boxes were corrected to non-wrapping widths. Selected All tools text/icon treatment was corrected. The first screenshot after adding a route group showed stale pre-group pixels; targeted tree/node readback plus subsequent screenshots established the actual rendered content. No content was duplicated to compensate.

Final screenshot: `18-directory-complete-check.png`, 1440x900.
SHA-256: `ed9d0a81566114a4d1c3b64dd15f741a94316647b227aa028ba6ada7049a0933`.
Targeted node readback: artboard1440x900; sidebar sublinks four187x40; main content1224x828; three directory columns372x382; footer18px high. Final screenshot shows all nine rows, active destination, scope labels, Confluence shortcut and footer without observed clipping. Review verdict: spacing, hierarchy, contrast, repeated-row alignment and artboard fit are suitable for this desktop candidate. No keyboard, actual search, responsive, bilingual or live-route proof is claimed.

`finish_working_on_nodes` on UQV-0 returned OK with unchanged token hash. The client remains an idle tool client, not an autonomous worker. Screenshot files under `/tmp/market-os-shared-shell-design-20260924-sol-001` are convenience evidence; the editable Paper artifact and this committed receipt carry continuity.

## Boundaries and next adjudication

This independent desktop navigation-depth work did not retry the held US fit/China duplication, country popup, mobile controls/drawer/page-readback, adaptive extraction, browser-probe append or pilot-template hunk extraction. No new refusal or EFFECT_UNKNOWN was observed in this unit. No application, auth, data, market model, personal state, canonical registry, source writer, merge or deployment changed.

The integrated design remains incomplete. Review this hybrid alongside the existing overview, native-six-view Sector and focused Terminal studies. Remaining country/menu/mobile states require permitted recovery on their original targets. Implementation still requires accepted design, exact current source custody and the first-adoption contract's real producer-to-consumer proof. Do not mistake one more composed desktop study for full-site readiness.
