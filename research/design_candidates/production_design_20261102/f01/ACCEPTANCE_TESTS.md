# F01 — Acceptance test specifications

**Status: NOT_RUN.** These are proposed acceptance cases derived from inspected source and F01 design requirements. They are not executable-test results, browser proof, independent qualification or RIG approval.

Source: `mastermindx-market-intelligence/mastermind-terminal@3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9`. Full immutable source links, observed/proposed distinctions and data boundaries are in [SOURCE_AND_DATA_CONTRACT.md](SOURCE_AND_DATA_CONTRACT.md). Existing carriers: [F01 #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645) and provisional [F02 #10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630) candidate `c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82`.

## 1. Evidence and qualification rules

For each executed case, record actual source/build identity, route/raw query/hash, viewport and usable content width, theme/locale, initial identity/access state, actions, observable result, screenshot or accessibility evidence where useful, and remaining limitation. Do not copy a result across changed artifacts. Source-only cases cannot substitute for browser journeys. Record product-regression and visual/taste findings separately; preserve the programme's independent first-pass and RIG requirements.

## 2. Route bytes and admission

Owner functions: [`resolveShellTarget`, `withoutTransport`, `isPresentationHref`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellContracts.ts), [`legacyFrameHref`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellRoutes.ts).

| ID | Setup/action | Falsifying result / required outcome |
| --- | --- | --- |
| R01 | Resolve admitted `/stock.html?q=a+b&q=a%20b&filter=%2F&mmx_shell=1&x=&mmx_generation=g#filing` | Retain ordinary bytes/order/repeats/empty value/hash exactly; remove only the two transport segments. Any ordinary reserialization fails. |
| R02 | Append generation transport to a query/hash URL, then canonicalize it | Original ordinary query/hash returns unchanged; transport is before hash and does not survive canonical return. |
| R03 | Native and legacy sets overlap on a pathname | Typed route collision; no renderer wins implicitly. Unknown internal route remains unknown. |
| R04 | Test admitted native, admitted legacy, mail/tel/external, credentials, unsupported schemes and invalid base/catalog | Preserve resolver classifications and actual host policy. A child NAVIGATE must not reinterpret external/blocked as native. |
| R05 | Authentication material in query and fragment, including `#route?token_hash=…` | No presentation bridge message carries it. Preserve the existing policy; do not broadly reject unrelated data fields merely named code. |
| R06 | Same-document push, replace, hash navigation and browser traversal | Parent and child canonical href agree; push/replace semantics remain correct; no duplicate child-only history entries. |

## 3. Analysis and exact company

Owner: [`parseAnalysisRoute`, `parseAnalysisSearchParams`, `ambientForAnalysisRoute`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/analysisRoute.ts), [`navHref`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/navSymbol.ts).

| ID | Setup/action | Required result |
| --- | --- | --- |
| A01 | Server entry and browser history for missing view, company, theses and investigations | Identical closed-parser result and correct workspace; no second shell parser. |
| A02 | Duplicate/blank/unsupported view; invalid or duplicate thesis; thesis outside its view | Preserve exact current invalid/unsupported distinctions; malformed links never mount the wrong store-consuming workspace. |
| A03 | Investigation with invalid UUID, missing-ID revision, zero, leading-zero, negative or excessive revision | Preserve existing validation and intentional parsed identity normalization; no URL repair that silently changes meaning. |
| A04 | Company `page` versus `pane`, including empty and duplicate values | Preserve current precedence and optional-parameter policy. Do not assume all duplicates are identity errors or all empty values can be removed. |
| A05 | URL-selected company differs from active cursor; switch company using same-route history | Rendered identity, chart entry and Brain context agree with the current source-selected company. Ret includes the latest URL. |
| A06 | Invalid explicit company; enter via topbar, mobile, directory, AI and direct link | No silent fallback to a stale cached company. “Current chart” and generic Terminal affordances follow their explicitly specified meanings. |

## 4. Return, history and restoration

Owners: [`sharedShellTerminalHref`](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellNavigation.ts), [originNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/originNav.ts), [LegacyPageHost](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/LegacyPageHost.tsx).

| ID | Journey | Required result and evidence limit |
| --- | --- | --- |
| H01 | Today → US market → exact Company → focused Terminal → named return | Preserve intended path/query/hash/listing, then separately prove local selection, scroll and focus. URL preservation alone does not pass the full journey. |
| H02 | Analysis → Terminal → another Terminal subpage → named return | Return to captured Analysis, not the immediately preceding Terminal page. Retain current hard-navigation semantics unless owner-qualified change is commissioned later. |
| H03 | Open Terminal in a new tab with valid ret; also direct Terminal with no valid origin | Correct safe return when known; no fabricated historical Back target when unknown. |
| H04 | Legacy → native → browser Back; two entries share the same canonical URL | Correct history-entry-specific view restoration, no merged snapshots. Verify child application, not only INIT payload. |
| H05 | Record more than 64 legacy view entries | Eviction degrades honestly; no promise of unlimited restoration. Missing snapshot must not borrow another entry's focus/scroll. |
| H06 | Switch account A to B; deliver late A-frame messages | Clear A snapshots, fresh frame identity, stale messages ignored. Server/domain access is still enforced. |
| H07 | Embedded Terminal close versus beta named return | Keep return-destination allowance distinct from embedded-parent origin authority; no newly trusted origin inferred from a valid ret. |

**Partial observation reported by root:** Company Financials updated the captured return destination to /analysis?symbol=NVDA&page=statements. The full chart return was not completed after the managed tab disappeared. This does not pass H01/H02 or establish scroll/focus restoration; the exact live receipt remains the sole writer's evidence to bind.

## 5. Host handshake, access and data truth

Owners: [message schema](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellContracts.ts) and [host](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/LegacyPageHost.tsx). Test auth/data states only with actual owner-provided fixtures or observed responses.

| ID | Condition/action | Required result |
| --- | --- | --- |
| B01 | Wrong window, origin, generation, extra fields or invalid message shape | No effect. A valid schema alone does not admit navigation. |
| B02 | Status build/protocol/bridge/document/registry/enablement mismatch | Changed-generation/recovery boundary; stale iframe is not presented as a working integration. |
| B03 | READY correct versions but wrong canonical URL; stale context revision | Wrong URL fails. Stale presentation revision reinitializes without accepting stale presentation as current. |
| B04 | Duplicate navigation request ID; same-document request for another pathname | No duplicate navigation; invalid same-document target fails explicitly. |
| B05 | Slow readiness, HTTP/network failure, visibility return after rollback | Honest loading/failure/change behavior; hidden frame stays inert. Retry/open-original are reachable and preserve the safe target. |
| B06 | Actual guest, denied plan, expired session, account-unavailable and known-page-unavailable inputs | Distinct copy and recovery from real owners. Do not derive all states from coming_soon or empty claims. |
| B07 | Composed data contains zero, null, stale/partial records and distinct source clocks | Domain semantics and actual dates survive; build ID/context revision cannot become a market timestamp or synchronize unrelated vintages. |
| B08 | Session expires during D23-owned save; response outcome uncertain | Preserve uncertain outcome and actual readback/deduplication path. No automatic repeat, false success or invented failure. Pane close cannot cancel the source mutation. |
| B09 | Inspect served /api/shared-shell/status for enabled/disabled/unversioned build fixtures and response headers | Match the [GET producer](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/api/shared-shell/status/route.ts): enabled requires the existing env predicate and a versioned build; exact six response fields; private, no-store, max-age=0; noindex, nofollow. Neither successful status nor enabled=true establishes account access or financial freshness. Source inspection of this producer is completed; this served-response test remains NOT_RUN. |

## 6. Navigation, directory and keyboard

Owners: [AppNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/AppNav.tsx), [MobileNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/MobileNav.tsx), [ShellDirectory](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/ShellDirectory.tsx), [SharedShellRuntime](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/SharedShellRuntime.tsx).

| ID | Action | Required result |
| --- | --- | --- |
| N01 | Visit market, Company, Options, Research and specialist families | One primary global destination; independent market context; local tabs do not compete as another global selection. F03 mapping remains authoritative for admission. |
| N02 | US → China while research is open | Correct available destination/listing or truthful unsupported state. Never relabel cached US data. No watchlist, holdings or preference mutation from navigation. |
| N03 | Search EN/ZH/full-width aliases, same-label destinations and canonical paths | Correct admitted matches with product/market/type disambiguation; no guessed URL; no deduplication by display title alone. |
| N04 | Change search/category, Show more, close/reopen | Intentional query/category retention, correct 48-result increments and count, stable focus; no accidental reset hiding a previous result. |
| N05 | Ctrl/Command+K and slash from shell, text input and focused legacy frame | Preserve editable-control behavior. Frame-global support must be actually proven; parent listener registration is insufficient. |
| N06 | Mobile drawer → All Tools → company search; Escape at each stage | Exactly one modal owner, correct focus trap/restoration and scroll-lock release. No hidden focusable closed-drawer links. |
| N07 | Keyboard open/close search, account/help and docked/modal inspector | Escape affects nearest applicable layer; modal trap only in modal mode; stable logical focus fallback if invoker vanished. |
| N08 | 320/390 with long Chinese labels and every local view | All destinations, local tabs and controls reachable; justified chart/table overflow is component-scoped. |

### 6.1 Company search cases — NOT_RUN

Owners: [ShellSearch](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/ShellSearch.tsx), [SymbolPicker](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/SymbolPicker.tsx), [SearchModal](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/SearchModal.tsx), [dataCache](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/dataCache.ts), existing market-preference and D07 company owners. Use controlled fixtures for faults; do not mutate production publisher data to create them.

| ID | Setup/action | Required outcome / known limit |
| --- | --- | --- |
| C01 | Cold manifest read; idle, pointer and keyboard intent race; open before response | One usable loading/recovery flow through GET /data/manifest.json; no invented company query API and no no-match state while the initial read is unresolved. Verify mounted/unmounted behavior without accepting a source comment as runtime proof. |
| C02 | 404, 410, 403, 429, 5xx, network failure, malformed JSON and literal null fixtures | Absence and unavailable stay distinct in the transport; no-universe UI is unavailable with recovery, never company nonexistence. Verify the existing ten-minute absence cache: a visible Retry control alone does not prove immediate refetch. Record any needed owner change explicitly. |
| C03 | Parseable body with as_of but no symbols; invalid symbols shape; later valid response | No infinite initial loading, crash or false empty-market claim. The current apply function's truthiness check leaves a source-derived gap; qualification requires actual recovery evidence and an owner-qualified correction if reproduced. |
| C04 | Exact symbol, same-name companies on different manifest keys, missing venue, unsupported sec and the explicit fund exception set | Admit only the actual company predicate; display symbol/localized name/real mkt or Venue unavailable. Keep suffixes and record identity distinct. No deduplication by name, invented issuer/MIC or claim of exhaustive fund detection. Pick pushes the exact encoded symbol to /analysis?symbol=… and updates the existing active cursor. |
| C05 | Exact/prefix/name/substring matches in EN and ZH, followed and unfollowed markets; empty query and Stocks browse | Preserve the source ranking tiers, within-tier boost, stable tie ordering, 30-result query cap, filtered Recent and 60-row browse cap. Display one language with fallback while both names remain searchable. Do not promise fuzzy/pinyin/NFKC matching that this owner does not implement. No watchlist-add or composite action in company pick mode. |
| C06 | Preferences initially unresolved, then a market disabled; type a matching company; explicitly choose Show all markets | Before ready, hide nothing; after ready, disclose hidden matches and markets. Query/navigation alone performs no preference write. Explicit Show all markets invokes the existing persisted visibility owner, leaves followed markets unchanged and does not claim account delivery without its receipt. |
| C07 | Memory/disk stale manifest, failed/successful/superseded background refresh, null or absent publication date | Bind any freshness copy to an actual source field. Row presence and the cache TTL cannot prove a fresh universe; the current picker ignores as_of and stale metadata. Retain usable identity honestly and record any agreed stale/recovery design separately. |
| C08 | Keyboard, Chinese IME, desktop dialog and phone sheet; open/close after selecting and after cancelling | One focus owner; valid active-descendant/option pairing; composition keys do not commit or dismiss unexpectedly; all results and close/retry controls remain reachable; meaningful focus return and scroll-lock release. Verify actual phone keyboard/reflow behavior rather than infer it from helper names. |
| C09 | Committed choice while telemetry succeeds, is blocked or fails; same symbol/source chosen twice within five seconds | Navigation does not wait on /api/track/search. Preserve existing telemetry deduplication and source=shared-shell; no search-log success UI, saved-object claim or hidden extra result request. Do not execute production logging merely to qualify a static source contract. |

### 6.2 Options local hierarchy cases — NOT_RUN

Owners: [OptionsWorkspace](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/workspaces/OptionsWorkspace.tsx), [optionsIa](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/optionsIa.ts), [WorkspaceTabs](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/WorkspaceTabs.tsx), [page access gate](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/%28shell%29/options/page.tsx). The exact EN/ZH view/path table is §3.1 of the source contract; this work creates no new Options owner or domain specification.

| ID | Setup/action | Required outcome / known limit |
| --- | --- | --- |
| O01 | Bare /options and every actual local destination; select each category from a nondefault subview | Bare route opens Flow → Options Tape. Category homes are deterministic, and all 15 retained view/home destinations match the source table. Statistics has no invented child tab; Futures remains /options/futures. Do not replace the IA with Overview/Plans or infer components from old comments. |
| O02 | vol/screener, gex/prism, unknown/blank/repeated tab, and client passthrough of leaders/radar/fundamentals | Keep source alias/default/first-value semantics. Client guards preserve the existing Discover/Analysis destinations. Verify any earlier server redirect separately; its existence is only mentioned in this inspected component's comments. |
| O03 | Start with /options?tab=tape&q=a%20b&q=a+b&filter=%2F&x=#section, retain history metadata, then select a different local view and traverse Back/Forward | The agreed target is an intentional tab update with canonical destination and unrelated context preserved; the existing writer uses URLSearchParams.set plus replaceState(null), so raw ordinary bytes can change and metadata preservation is unproved. Record actual before/after bytes, duplicate-tab behavior, hash and Next history state. This case cannot be marked passed merely because shared-shell transport preserves bytes. Any correction remains with the Options owner. |
| O04 | Actual allowed, denied and unavailable access fixtures at the page gate | Correct workspace, paywall or unavailable surface; unavailable is not an empty Options dataset. Never derive access from shell status. The FLOW_FIXTURE source branch is not production-environment proof, and this test does not authorize changing it. |
| O05 | Keyboard traversal of both category and view rows, EN/ZH change and deep link near the end of a narrow row | Roving focus/selection, arrows/Home/End and horizontal reveal work; each emitted aria-controls has a real appropriate panel. No unintended vertical jump or second global current-page marker. Source props alone do not qualify panel linkage. |
| O06 | 320, 390, 768, 1024 and docked-inspector widths with actual longest local labels/content; magnification | All seven categories, actual subviews, guide and Futures remain reachable; local overflow is bounded and primary content usable. Preserve page magnification. Do not accept a standalone wide Options frame as shared-shell proof. |

## 7. Theme, locale and composition boundaries

Owner: [SharedShellPresentation](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/SharedShellPresentation.tsx), existing account/locale/domain owners.

| ID | Condition/action | Required result |
| --- | --- | --- |
| P01 | Browser theme choice, account theme, auto mode, blocked storage, account switch | Actual precedence and persistence remain correct; shell toggle does not claim account-saved state without actual delivery/readback. |
| P02 | EN/ZH switch with active listing, current data, source inspector and open local view | Correct document language and labels; unchanged region/listing/unit/currency/source clock; status meaning remains stable. |
| P03 | Shared-shell light theme → focused Terminal → return | Incumbent Terminal dark behavior remains explicit; return reapplies the correct existing preference owner. No nested shell or duplicate Brain. |
| P04 | Public article/shared-chart → login/entitlement → beta deep link → return | Real public and private access owners retain their boundaries; no invented public access or SEO proof. |
| P05 | Internal OS/admin route in source inventory or directory | Audience/access remains independently governed; listing does not grant access or promote it to public navigation. |
| P06 | Reduced motion and keyboard-only use across loading, drawers and inspector | Controls remain comprehensible without animation; focus and scroll changes remain deliberate. |

## 8. Exact geometry probes

Candidate: 224px nav ≥1200;196px at >860 and <1200;72px explicit compact;overlay≤860. Header64 above860/56 at≤860. Gutters16 each ≤600;20 each >600 and <1200;24 each≥1200. Overlay440 at represented768/1024 widths, constrained to viewport; full width≤600. Inspector320+gap24 only if remaining central content≥640.

| ID | Width/mode | Expected usable width / behavior |
| --- | --- | --- |
| G01 | 320/390/768, default | 288/358/728 usable; modal inspector. Verify actual data density, EN/ZH and every control. |
| G02 | 1024 default196 | 788 usable; dock would leave444, so modal. |
| G03 | 1280/1440/1600 default224 | 1008/1168/1328 usable; docked central664/824/984. Measure real insets; prevent double gutters. |
| G04 | 1255/1256 default224, actual48 total inset | Dock would leave639/640. Modal at1255; docking eligible at1256. |
| G05 | 1095/1096 explicitcompact72, actual40 total inset | Dock would leave639/640. This is the actual compact threshold under the specified responsive gutters. |
| G06 | 1103/1104 explicitcompact72, forced48 total inset fixture | Dock would leave639/640. This tests allocation arithmetic; it is not the live responsive breakpoint. At actual40 inset both widths permit docking. |
| G07 | 600/600.5, 860/860.5/861 and1199/1199.5/1200 transitions; explicit compact retained | Continuous candidate cutoffs without fractional-width gaps; correct independent gutter/nav/header decisions; no hidden focus or modal lock; layout choice does not silently overwrite the explicit nav preference. |
| G08 | 400% zoom/reflow and full inspector on small CSS viewport | Application reflows; component-scoped two-dimensional overflow only; close/action controls remain visible and reachable. |
| G09 | Macro, Company and Options under every materially different content class | Actual primary task remains usable in the measured content slot. Standalone1440 screenshots do not satisfy shell integration. |

## 9. Review closure

No case is passed by this document. Future implementation-entry evidence must bind the exact F01/F02 source versions, editable Paper candidates, supported captures/exports, actual source/data contracts and independent review findings. Preserve formal RIG state and predecessor conditions. Design acceptance, implemented code, deployment and served-production proof remain separate.

