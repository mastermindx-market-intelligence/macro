# Integration note

Root adopted the proposed additive target route grammar in 04 §4.1. These fields remain implementation targets, not current accepted source syntax. B04 is governed by the new-case-only adjudication in 04 §7.2. This appendix is an assigned reasoning review, not a formal GitHub approval or new release gate. The current consolidated decisions are in [04](../04_ARCHITECTURE_HARDENING.md), [05](../05_IMPLEMENTATION_MASTERPLAN.md) and [06](../06_FUTURE_ROUNDS.md).

---

# Options rounds 3–4 — C3 frontend and product architecture review

**Date:** 2026-11-10 UTC  
**Role:** bounded, read-only frontend/product architecture witness for the principal.  
**Governance pin:** Mastermind `9e6659c4a49ee6f11a6f6ee690d222ce81d67b09`, reused from the assigned session.  
**Current Terminal source inspected:** `26c800c265d2cc627098955d186ddc8ef2886960`.  
**Planning carrier:** Macro PR #10898, principal-supplied head `626715ab73e3a0f9413c69faabd8a2a5030227de`.  
**Design inputs:** local `01_MASTERPLAN.md`, `02_PAPER_DESIGN.md`, and `03_PAPER_MANIFEST.json`; the manifest records 34 boards and 44 state components. No new Paper census or canvas mutation was performed.

This review distinguishes current implementation, proposed architecture and missing proof. It does not certify production behavior. It adds no router, cache, global selection store, Investigation owner, watcher, runtime or task hierarchy. Existing holds remain, especially D08D `p-2-0/1N2L-0` and the exact Plan bridge release hold. No GitHub, Paper, Slack or other external writes or dispatch occurred.

## 1. Decisions the final plan should lock

1. **Six destinations are an additive presentation and composition change, not a claim that six route homes already exist.** The current implementation is seven-category Stage A with fifteen workspace view keys. Preserve the accepted URLs and their current underlying capabilities. Treat new Research and Plans & review homes, Overview recomposition, and shared context handoffs as implementation work with named owners. [F01][F02][F03]

2. **Retain one workspace/router owner and one contextual pane.** The pane changes between Inspect, Case, Scenario or Review according to the task. Do not mount a separate always-present case rail beside a standalone inspector. Reuse existing reducers, readers and command owners; a presentation descriptor can map destinations to those owners without becoming a new state system.

3. **Use exact identity types at handoff boundaries.** An observed Flow group, child print, matrix coordinate, published IV point, qualified contract, authored Plan, immutable Investigation revision and firing receipt are different objects. A root-only transfer is a legitimate, explicitly labeled transition. It must not masquerade as an exact-contract or source-preserving transfer.

4. **Separate durable links from transient return state.** URLs identify supported destinations and identity-bearing objects. The existing validated history mechanism retains origin, filters, scroll and focus. A pasted link must resolve or explain an unavailable original; it cannot depend on a hidden local object left by an earlier visit. Do not serialize private authored text, credentials, account identity or raw source bytes into URLs.

5. **Reuse the held Plan bridge.** The principal refreshed #804 at head `27df56d997df0ae94a17b6b8e2d14867431bb394`: its canonical Analysis exact-revision reader and detached whole-Plan New/Add/Save/reopen/edit/separate-calculate path are implemented on that held branch. Master still has an unmounted preparation host. The final graph should integrate and qualify that implementation after its actual release conditions, not commission a new greenfield adapter. Release hold `5989604142` is not cleared by this review. This branch finding is principal-supplied; this witness did not duplicate the backend read.

## 2. Material current-source findings

These are source-level counterexamples and obligations, not browser-reproduced incident claims.

| Priority | Current evidence | Consequence and required disposition |
|---|---|---|
| P0 | `FlowDeskView.fetchTickerCtx` clears state, awaits a read, then writes an untagged result. `InspectorPane.EventDetail` renders that context independently from the selected event. Hub `fetchTicker` likewise has no request-generation/root-result guard. [F04][F05][F03] | Select root A, select B, allow B's response to finish first, then A's. A's context can win under the later selection. Add owner-local request-generation and render-time identity checks; clear/requalify before the next header can display. Prove inversion, deselection, unmount and account change. |
| P0 | `VolView` initializes both root and input to SPY; it receives only optional `liveSpot`, not root/expiry navigation context. There is no URL receiver in this component. [F09] | Paper Exposure → Volatility is not implemented merely by changing `tab`. Add an admitted receiver through the existing workspace. Keep root, explicit expiry/tenor and separate source clocks; refuse or visibly widen unsupported context. |
| P0 | `VolView.selectedExpiry` uses the requested expiry only while it remains in the inventory, otherwise returns the first available expiry. [F09] | On refresh, a previously explicit expiry can silently change. Distinguish default selection from requested selection. Preserve a missing requested expiry as unavailable and require an explicit choice; do not substitute the first expiry. |
| P0 | Options route entries are authoritative at the workspace level, but GEX symbol, axis and Research-open state are initialized once. The GEX popstate handler only updates ticker for a valid Sector origin. Hub keeps visited GEX mounted. [F02][F03][F08] | Cold-load `prism → matrix` is implemented; already-mounted Back/Forward or another `prism/view/research` URL is not equivalent proof. Reuse one decoder on initial entry and navigation changes. Test a warm GEX mount, not only fresh-page loads. |
| P1 | `zero_dte` is an internal key, not an accepted literal URL alias. The route map accepts `0dte`. Missing or unknown tabs resolve to Tape. [F01][F02] | Correct the plan's “0dte / zero_dte” notation. Preserve `/options` → Tape unless a deliberate, separately tested default change is approved. Do not claim a new home works because an unknown tab falls back to Tape. |
| P1 | Screener ΔOI is preset `doi`, fetched through `flowGet("oi")`; it is local state. Its chip disappears when its payload is absent. [F03] | Paper's OI changes action needs an explicit preset handoff and state classifier. Opening `?tab=vol` alone lands on the default preset. Keep the requested capability visible and show loading/absent/failed/denied accurately rather than switching or hiding it. |
| P1 | Prophet lane is local state initialized to `macro`; lane selection is not URL-bound. [F13] | Research → Options Alpha / Issue Desk must receive and retain an explicit lane. A `?tab=prophet` link alone cannot promise either lane. No conflation of Macro Plans, option candidates or research issuance. |
| P1 | Flow projection explicitly sets receipt time, conditions, lineage and quote to null; packages are not admitted. [F06][F07] | Child-print timelines, at-ask partitions and correction/withdrawal drilldowns need the versioned producer evidence already identified by round 2. Keep E01 aggregate fallback. Do not derive children from `n_prints`, estimated side or neighboring observations. |
| P1 | FlowDesk uses `selectedEvent` for both selection and inspection; selecting the same ID toggles it to null. Its watchlist root handler chooses the latest event for that root. [F04] | The Paper contract needs selected identity and pane visibility to be distinct local presentation state. Closing detail must not delete retained selection. A new root-filter control must not reuse the current watchlist handler and silently select the latest event. |
| P1 | Research coordinate keys are root/expiry/side/strike. The adapter does not establish exact-contract terms, OI session or first availability. The Lab's Save action is disabled. [F10][F11] | A coordinate is not an exact Plan pin or durable Investigation. Retain source epoch separately; requalify coordinates on refresh and mint action evidence through existing source-use owners. Never promote a matching coordinate into verified deliverables. |
| P1 | Flow cache and stream registry are keyed by source URL/`f`, not by account. Cache invalidation protects its own in-flight write identity, but that does not automatically fence consumer promises. The Options mount takes no owner props; Analysis does have authenticated owner/revision remounting. [F14][F15][F17][F18] | Require an account-switch/entitlement-withdrawal witness through the incumbent shell/auth owner. Bind withdrawal, consumer-generation cancellation and cache/stream lifetime there. This review does not claim an observed data leak; current inspected ownership does not by itself prove isolation. |
| Preserve | Research admission checks the existing shell identity and entitlement owner, then remounts the Lab by owner. `ResearchQuestionAction` binds acquired matrix bytes and owner, withdraws the staged reference on context change, and requires explicit Brain send. [F10][F12] | Reuse these safeguards. Do not replace them with a front-end “confidence” shortcut, generic source cache or automatic question submission. |
| Preserve | GEX already separates absent from failed reads, tags several results by root/request generation and resets dependent source state before children render. Volatility uses request counters for its main and supplemental reads. [F08][F09] | Generalize these established patterns to the remaining handoffs; do not create a second global epoch manager. |

## 3. Six destinations mapped to current paths and owners

All paths in the **current entry** column are current capabilities. Additional route fields described later are targets, not current accepted syntax. The fifteen view keys remain addressable.

| Target destination | Current entry / internal key | Current module or owner | Implementation choice |
|---|---|---|---|
| Overview | `/options?tab=desk` / `desk` | `FlowDeskView` through Hub | Compose O01 around current Command evidence; preserve the advanced desk's feed/inspection/watchlist capabilities in reachable Flow views. Do not delete them when replacing the three-column presentation. |
| Flow — Tape | `/options?tab=tape` / `tape`; bare `/options` | Hub Tape, existing tape-view codec, shared stream/cache | New O02 presentation must use one canonical observation selection projection; retain saved-filter and export contracts. |
| Flow — Tide | `?tab=tide` / `tide` | Hub Tide, `SessionFlowPane`, lazy Tide chart | Keep population/time basis and active-tab subscription semantics. |
| Flow — 0DTE | `?tab=0dte` / `zero_dte` | Hub Flow board | `zero_dte` is not presently a URL alias. Preserve session and expiry. |
| Flow — Largest | `?tab=largest` / `largest` | Hub / `OptionsFlowBoardView` | Preserve the eligible population and magnitude sort; no implied conviction. |
| Flow — Surface | `?tab=surface` / `surface` | `SurfaceView` | Keep strike × session-time Flow semantics and its original temporal owner; not IV terrain. |
| Flow — Screener | `?tab=vol` or `?tab=screener` / `screener` | Hub, `optionsScreener`, shortlist | Keep `vol` meaning Screener. Target serialized preset selection must use the existing selector, not a new ranking implementation. |
| Flow — Tickers | `?tab=tickers` / `tickers` | Hub ticker drill | Root is currently local; bind a target root receiver and fix late-response fencing. |
| Exposure — GEX | `?tab=gex` / `gex` | `GexDeskView` | Retain `symbol`, `view=strike|expiry|matrix|chart`, original origin/chart-return grammar and source qualification. |
| Exposure — Matrix compatibility | `?tab=prism` / `gex` | GEX's matrix initializer | Preserve matrix destination on both cold and warm history paths. |
| Exposure — Positioning | `?tab=positioning` / `positioning` | `msc/PositioningView` | Retain reported/model basis; do not replace with GEX totals. |
| Exposure — Levels | `?tab=levels` / `levels` | `levels/LevelsView` | Preserve level identity, source, metric and baseline. |
| Exposure — Structure | `?tab=structure` / `structure` | `structure/StructureView` | Move category presentation, not ownership or chart/companion behavior. |
| Volatility | `?tab=volatility` / `volatility` | `vol/VolView` and its term/skew/comparison panels | Implement the missing root/expiry receiver; retain exact-expiry vs constant-tenor distinctions. |
| Research — Statistics | `?tab=statistics` / `statistics` | `OptionsStatisticsView` outside Hub | Preserve the validated Statistics source and denominators; do not synthesize from the visible Tape. |
| Research — Macro/Alpha/Issue | `?tab=prophet` / `prophet` | `ProphetLanesView` → three independent lane components | Add typed lane serialization through the same workspace; current default is Macro. |
| Research — Lab | `?tab=gex&symbol=SPY&research=1`; compatibility `view=research` | GEX → `AdmittedOptionsResearchLab` → `OptionsResearchLab` | Preserve the current host/admission route while a direct Research entry invokes it. Lab is not presently its own top-level `tab`. |
| Plans & review — authored Plan | Current Screener shortlist; GEX Lab handoff explicitly switches to `screener` / `doi` | Shortlist / existing Plan draft / held #804 bridge | Keep exact pins and explicit New Plan. Current handoff does not transfer matrix coordinates and does not auto-create a Plan. |
| Plans & review — Saved/Review | `/analysis?view=investigations`; exact `&investigation=<uuid>&revision=<positive integer>` | `analysisRoute`, Analysis page, existing Investigation workspace | Preserve canonical links and exact-revision validation. Embed by the incumbent host mode only when admitted; do not create a parallel Options case store. |
| Contextual Futures | `/options/futures?pair=ES` | Existing Futures route/codec | Keep its native contract/session/basis/cutoff grammar; do not append a generic Options cursor. |
| Contextual Equity replay | `/options/equity-replay?symbol=SPY` | Existing equity replay route/codec | Keep artifact/sample/admission identity and native time grammar. |

Workspace also preserves redirects for `leaders` and `radar` to Discover, and `fundamentals` to Analysis. They must not be absorbed as extra Options lanes. [F02]

### Recommended route delivery decision

Ship the six destination labels and view catalog in the existing `optionsIa`/workspace owner, while retaining all current `tab` meanings. Do not invent an unimplemented `tab=research` or `tab=plans` and let fallback-to-Tape make the button look live.

For the full Paper implementation, the recommended target primary homes are `tab=desk`, `tab=tape`, `tab=gex`, `tab=volatility`, **new additive `tab=research`**, and **new additive `tab=plans`**. The last two must be registered explicitly in the existing IA/route owner; they are not accepted at the inspected source pin. O05 is a Research composition using incumbent Statistics/Prophet/Lab sources, rather than a relabeling of Statistics. O06 is an embedded presentation of the incumbent Investigation library, rather than a new case store. Preserve all old `tab` links and canonical Analysis exact-revision URLs. The six homes are implementation scope, not a menu-only substitute for the Paper deliverable.

For deterministic shortcuts, recommend additive **`preset=doi`** on the Screener route and **`lane=macro|options|issue`** on the Prophet route, decoded by the same workspace owner. Continue using `symbol` for the intended root; add an explicit `expiry` receiver to Volatility and retain its native tenor value vocabulary rather than inventing a cross-source tenor codec. The final principal should adopt these names or record an explicit alternative before implementation. None is claimed as a currently accepted preset/lane/Volatility handoff field.

The Plans home must reuse the existing `investigation`/`revision` parser and a host-aware navigation callback; no hardcoded Analysis navigation should silently escape the embedded host. Saved/Watching/Review are presentation filters or modes over that owner. An exact firing link requires the root-owned receipt identity/selection contract; it must not be invented from a latest trigger stamp. Until the embedded host is qualified, the legitimate compatibility action is the canonical Analysis route, labeled as such. That fallback is useful but does not complete O06/O08 integration.

The typed additive codec belongs in the existing route owner. Reject duplicate/invalid identity fields, apply view-specific fields only to their own view, preserve compatible origin/history state, and test cold/warm roundtrip before publishing links. No separate global route registry or navigation store is needed.

## 4. Paper action-to-implementation contract

The actions below cover `02_PAPER_DESIGN.md` §5. Grouping is by owner, not a reduction in acceptance coverage. Every row requires a handler or a legitimate named unavailable state.

| Paper action / state | Current owner or source binding | Target work and acceptance |
|---|---|---|
| O01 Inspect activity → O02/M01/M02/M10 | FlowDesk selection + Hub Tape source; currently distinct local presentations | Choose one shared observation identity projection, pass exact source/group revision, and preserve Overview origin. Selection, root filtering and navigation are separate actions. |
| Flow row Inspect / close / exact Back | `selectedEvent` / `FeedPane.selectedId`, existing Tape filters | Preserve source snapshot, group ID, applied filters, sort and focus. Do not auto-select a neighbor. Restore a stable labeled list target if withdrawn. |
| Inspect six child prints / E01 | `FeedPane.FlowEvent`, `flowPrintInspector`, `PrintInspector` | Producer-qualified child evidence remains a feature gate. Aggregate-only fallback must keep available totals without fabricating child arrays or quote classes. |
| Source & corrections / E02/E03 | Existing source/print inspector; lineage currently null | Implement source revision/correction/withdrawal reading under original identity. Correction review cannot silently replace the selected historical bytes. |
| Filters Apply/Cancel / E04 | Existing Tape codec and Flow filters | Explicit draft vs applied filter state. Apply changes the eligible population; Cancel preserves it. Saved filters are not saved evidence. |
| Largest / 0DTE / More views | Existing `largest`, `0dte`, Flow subviews | Keep original aliases and exact source population; show explicit view label after transition. |
| Unusual | Existing `selectUnusualRows` / Screener `unusual_z`, or existing Tape filter owner | The final implementation must pick the actual incumbent rule. Recommended explicit shortcut: Unusual activity in Screener. If design requires a filtered Tape instead, name and reuse that Tape predicate; do not imply these two populations are identical. |
| **OI changes** | `?tab=vol` → `screenerPreset="doi"`; `flowGet("oi")`; `selectOiRows`; `ContractPinButton` | This is the concrete existing capability. Bind preset, root/filter and source session. If absent/failed/denied, preserve the requested ΔOI view and show E05/E06/E07; no fallback to Top Premium or empty hidden chip. |
| See all observations | Same Tape eligible array; existing export pipeline | Expand presentation only. Eligible, observed, displayed and exported counts must remain explicitly different where appropriate; export is not viewport-limited. |
| Flow Open Exposure / E08 | Existing GEX `symbol` receiver | Root-only transfer into an independent book. Keep selected Flow group in return context; do not call it the book's source or carry a fabricated exact contract. |
| Exposure bar/row / exact contract | GEX matrix/ladder/companion; Lab coordinate adapter | Coordinate selection is allowed. “Exact contract” requires terms/identity qualification beyond coordinates. Failure stays explicit; no nearest-strike/expiry substitution. |
| Compare 05 Nov / O10 cohort tabs | Existing GEX history / Market Memory and comparable-source owners | Pin both source identities, models, spots and units. All/matched/unknown/added/removed change display cohort only; do not reuse a matched subtotal as a full total. |
| Inspect both source rows / method | Same source detail for each bound book | Two distinct source receipts remain inspectable; no synthetic availability timestamp. |
| Matrix / By strike / Price context | GEX `view` + existing matrix and chart companion | Synchronize URL/history and selection through existing owner. Reusing a page-host companion must preserve its original access and no-extra-Escape behavior. |
| 3D / exact 2D / A06 | Admitted Lab, pure adapter, ResearchScene boundary, exact table | Same admitted rows and selection. Current table paginates 50 rows and retains full admitted population; 3D failure cannot remove exact data. |
| Exposure Open Volatility | Target receiver in current VolView | Root plus explicit expiry only when qualified. Missing requested expiry stays missing; independent spot/IV/book clocks remain. |
| Expiry / tenor / missing wing | VolView + VolTerm/VolSkew/VolCompare | Do not join expiry and constant-tenor identities. Preserve conflicts/missing wings and exact table values. No fitted curve across absent wings. |
| Volatility Source/method/exact table | Existing source panels, Lab published-IV adapter | Source session matching does not establish first availability or verified terms. Keep unavailable fields unavailable. |
| Qualified shortlist / Lab / Plan | Existing contract shortlist and admitted Lab navigation | Matrix coordinates remain unverified. Current Lab Scenario action navigates to shortlist, retains existing pins and requires explicit draft creation. |
| Research evidence maturity / family / E11 | Statistics, Prophet's three lanes, existing evaluation owners | Bind a named family and candidate; separate formation, sample maturity, calibration and permitted claim. No frontend aggregate confidence score. |
| Research Ask about this selection | Existing `ResearchQuestionAction` + acquired matrix/source-use receipt | Preserve owner/byte identity, withdrawal on change, explicit review/send in Brain and rechecked access. The new shell must not bypass this already implemented capability. |
| Plan edit / recalculate / compare / sample / E12/P01/P02 | Existing Plan/shortlist owners; root's detailed bridge review | Keep authored inputs, exact admitted terms, sampled axis, comparison baseline and result identity. Changed input invalidates current-result use. Do not infer a Plan from aggregate exposure. |
| Open saved Exposure case / P09 | Existing draft lifetime + canonical Analysis Investigation entry | Guard potentially destructive navigation. Do not promise unproven reload/resume or imply Exposure capture includes the old exact Plan. |
| Exposure Save / exact Plan target B04 | Existing Investigation admission/command/history; held #804 implementation | Wire the admitted bridge after release conditions; supported evidence only. Save and Arm stay separate. Root owns detailed schema mapping and write/reconciliation acceptance. |
| Saved open exact case/revision/source / P12/E09 | Canonical Analysis decoder and exact reader; current source digest resolver | Exact requested revision or explicit unavailable. Original-source resolution is a separate capability from loading the saved reference; current/latest bytes cannot fill it silently. |
| Create new Plan from Saved | Existing qualified shortlist or held exact-Plan reopen path | Explicit New versus detached reopen. Do not represent an excluded Plan as persisted. |
| Manage watch / preview / Arm / W01–W03/W08/W10 | Existing watch detail/command/evaluator | Saved identity, one-shot expiry and cadence visible. Confirmed owner result precedes Armed. Unconfirmed evaluator status is not Armed proof. |
| Review exact firing / W04/W06/W07/W09 | Existing receipt projector and revision owner | Freeze selected event identity through editing. Null-ID fallback cannot claim exact event binding. Newer event is offered, not automatically substituted. |
| Review Load comparable book | Comparable-source resolver | Original remains visible; later book must qualify comparability. A firing price does not replace the book. |
| Delivery history / W05/W06 | Existing alert/outbox detail | Distinguish firing record, pending delivery, delivery result, unreadable history and readable empty history. |
| Review assessment / Save revision | Existing revise command | Explicit assessment, Unicode-safe limits, original evidence pinned, latest-revision requirement and exact readback. Root owns the detailed command review. |
| Later observations / W12 | Existing Flow transport with target consumer snapshot choice | Keep current pinned snapshot, or explicitly enter latest. Updates cannot mutate the user's return origin or assessment target. |
| Global/Options navigation / M07 | Existing shell/layer arbitration | One open foreground layer; Escape dismisses the topmost relevant layer and restores its opener. Preserve current route family and source mode. |

## 5. Context, invalidation and history rules

### 5.1 A projection of existing owners, not a new global object store

The interface should be able to describe these fields together, but each remains owned where it is today:

- **Access lifetime:** existing account owner, its lifetime/generation and verified entitlement result.
- **Surface:** destination, native view/lane/lens and current/history/scenario mode.
- **Source:** family, exact artifact/reference or digest where supplied, publication/source session, source epoch, declared cutoff and availability semantics.
- **Selection:** discriminated identity — group/revision, child print, coordinate, qualified contract, or comparison member. A numerical strike alone is insufficient.
- **Case:** requested Investigation ID/revision and selected firing identity, independent of latest values.
- **Authored calculation:** existing draft identity, input revision and result/input binding.
- **Return:** validated same-origin route, origin identity, filters/sort, scroll position and stable focus target.

The source-as-of string alone is not a correction epoch. A source can change with the same displayed date. Use the incumbent fingerprint/version/receipt where provided, and show that a new source must be qualified.

### 5.2 Transition contract

| Transition | Retain | Requalify or clear before render | Required negative witness |
|---|---|---|---|
| Root A → B | Origin/Back and user-owned case only where meaningful | All root-bound reads, selected coordinates/contracts, comparison and calculation eligibility | A response resolves after B; no A data under B header |
| Account A → B → A | Only explicitly account-independent presentation preferences | Protected values, selection, staged Brain reference, drafts, in-flight consumers and access result | Earlier A lifetime cannot revive after returning to A |
| Entitlement revoked/unverified | Requested identity and non-sensitive explanation | Values/actions requiring permission; pending action dispatch | Cached payload/3D fallback does not bypass the gate |
| New source epoch, same coordinate | Coordinate intent only if requalified and visibly restamped | Old source-bound claim/result/action receipts | Same root/expiry/strike with corrected bytes does not look like unchanged evidence |
| Correction/withdrawal | Original identity, origin and original supported receipt | Current source usability and dependent claims | No auto-selected neighbor; explicit correction review |
| Explicit expiry disappears | Requested expiry and user context | Curve/result availability | Never select another expiry as if it were requested |
| Latest → pinned history | Exact requested artifact/session/cutoff | Live-only overlays and current OI/context | Current source cannot dress an archived book |
| Filter hides selected item | Exact retained selection and filter intent | Visible row marker; show “outside filter” where supported | Do not modify filters merely to make a selected pin appear |
| Route/Back/Forward | Supported URL identity and merged router/history state | All view-local derived navigation state | Warm mounted GEX/Vol/Lab yields the same destination as a cold link |
| Narrow ↔ wide | Selection, authored input, source epoch and case | Layout/focus target only | Resize cannot remint evidence, submit, clear draft or change selected object |
| Later firing arrives | Frozen selected firing and authored assessment | “Newer firing available” indication only | An edited assessment cannot attach to the new event silently |
| Source read fails | Last qualified bytes with original clock where the owner permits | Fresh/live claims and dependent action admission | Failure, unpublished, denied and empty have different messages/actions |

History writes must preserve the incumbent router's state. Workspace currently uses `replaceState(null, ...)`; GEX generally retains `window.history.state`. Therefore a new return envelope must not be added and then erased by the next tab write. Navigation that creates a meaningful return step needs a deliberate history entry; display-only toggles may replace. Document that choice per handler and verify Back/Forward. [F02][F08]

The Analysis decoder already rejects duplicate/invalid investigation IDs and revision fields, requires `view=investigations`, and bounds revisions to positive integers ≤2,147,483,647. Reuse that decoder rather than accepting a loose Options-only duplicate. The existing Analysis entry authenticates and keys the workspace by owner/ID/revision. [F18][F19]

## 6. Responsive, accessibility, locale and performance acceptance

These are target budgets and required proofs, not measurements made by this review.

| Area | Target | Concrete proof |
|---|---|---|
| First viewport | Subject, source/result state and primary action visible before deep detail | Actual O01/O02/O03/O04/O07/O08 consumer screenshots on the supported desktop profile; retain critical limits with values |
| Desktop pane | One contextual pane; evidence remains readable at 1440 | Selected row/node and active case, no competing fourth column or clipped unit/qualification |
| Narrow layouts | 390px journey plus 320px effective reflow; tablet 820px | Flow full-detail/Back, Exposure exact slice, Plan input/result, Saved/Review, and open navigation at each relevant size |
| Magnification | 200% text and 400% zoom/effective 320px where applicable; Options route retains scalable viewport | Real browser proof, including focused controls, menus, tables and error text |
| Keyboard/focus | Semantic buttons/links; table equivalent for chart selection; visible focus; topmost Escape; return to opener or stable fallback | Current ΔOI table headers and row click targets must become keyboard-operable in the changed journey, not remain pointer-only `th/tr onClick` |
| Touch | Important actions target at least 44px in the design contract | Actual hit areas with dynamic EN/ZH copy; no overlap after wrapping |
| Language/themes | EN/ZH and both themes preserve numbers, meaning, state and actions; no edge stripes | Critical journeys in each, long labels and errors; Chinese direction colors retain signs/text while health status meaning stays fixed |
| Unicode | Limits count the agreed codepoint rule and preserve over-limit text for correction | Astral characters, Chinese text, paste beyond limit and exact revision save; no native UTF-16 truncation masquerading as A08 |
| Interaction | Proposed p95 ≤200ms for local selection/filter/control feedback on named supported device profile | Measured actual consumer with the original P74 ~13k-contract population; report source/build/device/sample counts |
| Web loading | Retain D08's proposed p75 LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 where applicable | Field or explicitly labeled representative lab measurement; no claim from static Paper/JSX |
| Heavy views | Lazy load 3D/charts; preserve independent exact table; no unnecessary hidden-view work | Chunk/network/main-thread trace; visit and leave GEX/Lab/Vol, count active requests/subscriptions |
| Subscription/cache | One incumbent owner per source; hidden consumers only retain work required by an explicit consumer | Hub intentionally shares feed; stream registry deduplicates by `f`. Keep that benefit; audit other keep-alive timers rather than banning or duplicating all subscriptions |
| Failure recovery | Stable geometry, preserved truthful data, legitimate next action | Timeout/malformed/denied/unpublished/empty/corrected/withdrawn plus lost save and conflict paths through real UI |
| Export | Same eligible array and order as the current selector, not only rendered rows | Representative table/CSV equality including nulls and filtered-out pinned contracts |

The current Lab already has exact-table pagination, a renderer failure boundary, no-data disclosures and focus fallback after removed elements. Preserve those assets. The Paper atlases are requirements/examples; neither their 44 state components nor 34 boards prove that corresponding runtime state handling exists. [F11]

### Minimum C3 proof packet

1. **Route compatibility:** all fifteen view keys plus accepted aliases, redirects, bare Options default, cold and warm navigation, malformed/duplicate identity-bearing fields.
2. **Action closure:** every action in section 4 has a handler, exact receiver, source/gate and return; no enabled cosmetic buttons.
3. **Race matrix:** slow A/fast B, deselect while pending, source correction with same date, owner A→B→A, revoked entitlement, unmounted consumer.
4. **Continuity:** Flow origin → independent Exposure → qualified Volatility → shortlist/Plan → saved exact revision; all explicit widenings/refusals recorded.
5. **Exact Back:** filters, sort, selection, source mode, scroll and focus preserved; deleted/withdrawn item handled without neighbor substitution.
6. **State/readiness:** source truth and command truth remain independent; no mock-success adapters in production paths.
7. **Real build/browser evidence:** exact source/build, permitted authenticated consumer, data/artifact identity, console/network results, responsive/locale interaction evidence.
8. **Scoped feature gates:** failed child-feed, historical resolver, scientific or Plan admission blocks only its own action; honest aggregate/table/draft/research-only alternatives remain useful.

## 7. Cutover gates and work ordering

Use the original programme tasks and owners; these are dependencies, not new task IDs.

**First: route and context hardening.** Complete the fifteen-view crosswalk, explicit preset/lane receivers, warm-history reconciliation, Flow/ticker race fixes and Volatility missing-expiry behavior. These are foundations for a believable shared shell.

**Second: source-backed compositions.** Implement the Paper main surfaces with existing data owners and classifiers. Keep E01 while child evidence is absent, retain exact-table fallback, and preserve the current admitted Research question path. Source detail and correction controls cannot be stubbed with fixture output.

**Third: case integration using existing held work.** Integrate the qualified #804 bridge and existing Investigation/receipt owners only after their original admission/release conditions. Root's backend review governs exact capture, original-source resolution, command reconciliation and selected-event persistence. Keep current canonical Analysis URLs working during any host-mode integration.

**Fourth: actual consumer acceptance and family cutover.** Complete C3 witnesses alongside domain and backend evidence, then record the approved family disposition. Original Terminal remains the working source until that cutover. The untouched D08D held target cannot be substituted by a newly drawn or renamed temporal board.

A route label is not a capability gate; a verified entitlement is not source qualification; a source reference is not a historical resolver; a successful write response is not exact-revision readback; a firing is not delivery or a confirmed thesis. The final checklist must preserve these distinctions.

## 8. Additional design rounds worth considering after the final plan

Do not defer core route receivers, source truth, exact return, accessible controls or held-bridge integration into optional future design rounds. Those are obligations of this package.

Additional rounds should be commissioned only when they unlock a meaningful new user capability with a real owner/data contract:

| Optional round | New user capability | Entry condition and useful design output |
|---|---|---|
| Cross-case research and alert triage | Compare several saved hypotheses, find which changed and decide which deserves review without losing immutable originals | Existing revision/watch owners support the required list/query. Design a multi-case prioritization workspace with explicit change basis and individual review actions, not bulk arming or an invented score. |
| Portfolio-aware hedge studies | Relate an exact hypothetical expression to a qualified position set and inspect concentration, scenario loss and basis risk | Portfolio/position authority and units/terms/source dates are admitted. Design portfolio-to-case navigation and scenario explanations; no automatic sizing or execution authority. |
| Reproducible event studies and replay | Revisit what was knowable at a chosen event and compare later outcomes using compatible sources | Native temporal owners provide lawful first availability, artifact identity and qualified comparison. Preserve Futures/IEX/chain differences; no universal cursor. Original D08D hold remains binding. |
| Calibrated signal explanation | Understand a scientifically promoted signal's target, cohort, uncertainty, failures and permitted action | The existing formation/evaluation/promotion owner admits the claim. Design calibration and falsifier explanations, abstention states and source drilldowns; avoid universal confidence rings. |

The next optional design round should be selected by admitted capability and user value, not because the programme has unused design capacity.

## 9. Evidence register

All Terminal links below are pinned to the inspected commit. Local source snapshots are under `options-round4/frontend-sources/` for the principal's review; they are read-only evidence snapshots, not code edits. Source-level reasoning did not run application tests or production browser sessions.

- **F01:** [optionsIa.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/optionsIa.ts) — categories, fifteen view keys, page keys.
- **F02:** [OptionsWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/workspaces/OptionsWorkspace.tsx) — ROUTE_VIEW, default Tape, shallow history, redirects and workspace ownership.
- **F03:** [OptionsHubView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/OptionsHubView.tsx) — visited views (1592–1605), ticker fetch (1676–1685), OI reads (1953–1970), shortlist (2063–2079), preset/ΔOI UI (3555–3586, 3881–3941), Lab-to-shortlist handoff (4083–4093).
- **F04:** [FlowDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/flowdesk/FlowDeskView.tsx) — selectedEvent (494–503), fetchTickerCtx (587–593), selection effect (658–666), stream/cache and inspector binding.
- **F05:** [InspectorPane.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/flowdesk/InspectorPane.tsx) — independently supplied context rendered by EventDetail (239–256, 341–355).
- **F06:** [FeedPane.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/flowdesk/FeedPane.tsx) — aggregate FlowEvent, filtering and selection props.
- **F07:** [flowPrintInspector.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/flowPrintInspector.ts) and [PrintInspector.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/flowdesk/PrintInspector.tsx) — truthful aggregate projection and unavailable print evidence.
- **F08:** [GexDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/gexdesk/GexDeskView.tsx) — initial route/context (240–306), history handling (270–340), pre-render source reset (395–410), Lab host (1012–1025).
- **F09:** [VolView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/vol/VolView.tsx) — SPY initialization (123–147), request fences (220–261), explicit expiry and fallback (340–365).
- **F10:** [AdmittedOptionsResearchLab.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/researchlab/AdmittedOptionsResearchLab.tsx) and [researchLabAdapter.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/researchlab/researchLabAdapter.ts) — existing access owner, coordinate identity and missing metadata.
- **F11:** [OptionsResearchLab.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/researchlab/OptionsResearchLab.tsx) — pure consumer, local lenses, reconciliation, focus, renderer fallback, exact table, explicit gaps and disabled Save.
- **F12:** [ResearchQuestionAction.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/researchlab/ResearchQuestionAction.tsx) — acquired bytes, reference/owner context, withdrawal and explicit Brain action.
- **F13:** [ProphetLanesView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/prophet/ProphetLanesView.tsx) — independent Macro/Options/Issue lanes and local default.
- **F14:** [flowClientCache.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/flowClientCache.ts) — URL keys, shared request, classified read, in-flight identity check and invalidation.
- **F15:** [flowStream.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/flowStream.ts) — source-key registry, ref-counted connection, generation/key fencing and held payload behavior.
- **F16:** [useOptionsPlanScope.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/useOptionsPlanScope.ts) — existing account lifetime observer; display lifetime is separate from authoritative API access.
- **F17:** [Options page](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/app/%28shell%29/options/page.tsx), [OptionsWorkspaceMount](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/mounts/OptionsWorkspaceMount.tsx), [AppShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/chrome/AppShell.tsx) — page access/zoom, mount and existing identity presentation.
- **F18:** [Analysis page](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/app/%28shell%29/analysis/page.tsx) — authenticated owner/ID/revision mount.
- **F19:** [analysisRoute.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/analysisRoute.ts) — exact public URL validation and shared browser decoder.
- **F20:** [optionsTapeView.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/lib/optionsTapeView.ts) — existing versioned Tape filter codec.
- **F21:** [OptionsStatisticsView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/26c800c265d2cc627098955d186ddc8ef2886960/terminal/components/options/OptionsStatisticsView.tsx) — separate Statistics consumer.

### Review completion

Delivered: route/module/action decisions; current-source gap list; identity/invalidation/history rules; responsive/a11y/locale/performance proof requirements; feature-gate ordering; meaningful optional design rounds.

Not claimed: code changes, tests, deployed reproduction, new Paper acceptance, whole-repository census, release of any hold or T3 implementation pickup. The principal can incorporate this witness into the existing canonical planning carrier.

