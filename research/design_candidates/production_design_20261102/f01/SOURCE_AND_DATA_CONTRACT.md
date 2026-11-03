# F01 — Source and data contract

**F01 source-contract candidate, integrated from read-only advisory source analysis by the sole F01 writer.** This document separates observed source behavior, proposed design requirements and unverified browser outcomes. It grants no route admission, Paper write authority, design acceptance or implementation permission.

| Identity | Bound reference |
| --- | --- |
| Assignment package | Macro `6e1862867193ec6486a22001a0e4fb515da20448`, [F01 brief](https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/handoffs/F01-shared-shell.md) |
| Inspected Terminal source | `mastermindx-market-intelligence/mastermind-terminal@3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9` |
| Existing F01 carrier | [Macro #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645); the current F01 receiver remains sole source/Paper writer |
| F02 input | [Macro #10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630), candidate `c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82`; provisional, not an accepted joint release |
| Qualification | Source inspection only. No production code changes, executable tests, browser acceptance, independent approval or RIG receipt established by this draft. |

## 1. Canonical owners and reusable boundaries

| Concern | Existing owner | F01 obligation |
| --- | --- | --- |
| Global job navigation, composition, return affordances | F01; current AppShell/navigation owners | Specify one presentation and preserve existing routes and state owners. |
| Tokens, shared components, typography, density, accessibility and motion primitives | F02 | Bind an exact joint candidate version; request shared changes rather than fork tokens. |
| Route registry/export/admission, coverage and organization projection | Existing exporter/registry owner tracked by F03 | Derive labels and aliases from that source; do not add a parallel catalogue or equate display with admission. |
| Company, thesis and investigation composition | D07; `analysisRoute.ts` | Preserve its closed parser, identity switches and local view semantics. |
| Options local categories, views and query writes | Existing Options owner; `optionsIa.ts` and `OptionsWorkspace.tsx` | Reuse its actual EN/ZH labels, aliases, deterministic category homes and access gate. F01 specifies composition, not another Options IA or data engine. |
| Saved objects, watchlists and alert mutations | D23 | Preserve its actual write/readback/deduplication semantics. Chrome dismissal and navigation cannot declare mutation success, failure or cancellation. |
| Focused chart shell and Brain ownership | D06/existing Terminal owners | Keep `/terminal` outside AppShell and retain the one existing chart/Brain owner. |

### Exact source entry points

- [AppShell.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/AppShell.tsx): one non-chart chrome, identity context, mobile navigation, settings and Analysis Brain host.
- [(shell)/layout.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/%28shell%29/layout.tsx): dynamic/private server identity and explicit shared-shell enablement.
- [(shell)/[...legacyPath]/page.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/%28shell%29/%5B...legacyPath%5D/page.tsx): admitted legacy route entry; no second content host.
- [LegacyPageHost.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/LegacyPageHost.tsx): legacy frame, parent history, readiness, context and bounded restoration.
- [sharedShellContracts.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellContracts.ts): route/message validation and protocol fields.
- [sharedShellRoutes.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellRoutes.ts): generated projection consumer and byte-preserving frame transport.
- [sharedShellNavigation.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/sharedShellNavigation.ts), [navSymbol.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/navSymbol.ts): global presentation, company propagation and Terminal entry.
- [analysisRoute.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/analysisRoute.ts), [originNav.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/originNav.ts): local route vocabulary and named return.
- [SharedShellPresentation.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/SharedShellPresentation.tsx), [SharedShellToolbar.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/SharedShellToolbar.tsx): theme/locale and current-chart entry.
- [ShellDirectory.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/ShellDirectory.tsx), [SharedShellRuntime.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/SharedShellRuntime.tsx), [AppNav.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/AppNav.tsx), [MobileNav.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/MobileNav.tsx): directory, shortcuts and the existing navigation surfaces.
- [shared-shell.css](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/shared-shell.css): scoped current geometry, single mobile breakpoint and presentation.

## 2. Route, query and history contract

**Observed.** `resolveShellTarget` resolves a link against the canonical legacy base, then dispatches an admitted pathname as native or legacy. A collision between the two projection sets is refused. Unknown internal paths remain unknown; route names do not grant product semantics.

`withoutTransport` removes only `mmx_shell` and `mmx_generation` query segments while retaining ordinary segments, order, repeats, empty values and encoding. `legacyFrameHref` appends those transport parameters before the hash without reserializing ordinary query bytes. Browser URL resolution still normalizes relative URL syntax; this is not a promise that every original lexical href remains identical.

`isPresentationHref` prevents authentication material from becoming bridge messages. `readShellChildMessage` binds messages to exact source window, origin, frame generation and a closed field vocabulary. Schema validity alone does not authorize navigation or establish release compatibility.

**Proposed.** All redesigned navigation surfaces consume these owners. Copy/share/return actions retain the canonical path, meaningful raw query and hash. Display aliases must resolve to admitted identities, not synthesize speculative routes. Ordinary context navigation cannot write saved objects. This is a proposed cross-surface requirement, not proof that every native local writer preserves raw bytes: the current Options writer reserializes its query, as documented in §3.1.

## 3. Global, regional and local state

**Observed.** `SHARED_SHELL_NAV` contains Today, Discover, Analysis, Monitor, Research and Portfolio. `SHARED_SHELL_MARKETS` contains direct market destination links. Those links are not a persisted region-selection API.

`sharedShellActiveKey` maps known families and defaults other paths to Today. AppNav and MobileNav also mark exact market links current. This explains the current possibility of Today and a market both carrying current-page treatment.

`ShellContext` contains only `theme`, `locale` and `contextRevision`. A `region` field is not supported by the inspected message contract.

**Proposed.** Show one primary global job, a distinct product/local view, and separate market/entity context. F01/F03 must agree the presentation mapping without changing admission. A genuine region switch requires domain-provided availability and listing semantics; no cached US result may be relabelled as China. Preserve direct market destinations and specialist entry.

**Analysis owner.** `parseAnalysisRoute` and `parseAnalysisSearchParams` govern company/theses/investigations. Repeated `view` values are invalid; thesis and investigation identifiers retain their own validation. Company `page` and existing `pane` alias retain current precedence. Optional symbol handling is not the same policy as identity-bearing view switches. `ambientForAnalysisRoute` remains the only company/theses/null mapping; F01 adds no Brain panel enum.

`navHref` carries the active symbol only to the existing symbol-aware chart/analysis destinations. No arbitrary symbol parameter is attached to workspaces that do not consume it. Company identity and listing/exchange identity remain separate domain responsibilities; the inspected shell is not a listing-resolution backend.

### 3.1 Options local navigation: actual retained vocabulary

**Observed sources.** The route is [options/page.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/%28shell%29/options/page.tsx), mounted through [OptionsWorkspaceMount.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/mounts/OptionsWorkspaceMount.tsx). [OptionsWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/workspaces/OptionsWorkspace.tsx) composes category and view rows from [optionsIa.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/optionsIa.ts); actual labels below come from [i18n.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/i18n.tsx).

| Category EN / ZH | View EN / ZH | Exact local destination | Source label key |
| --- | --- | --- | --- |
| Command / 指挥台 | Flow Desk / 资金流台 | /options?tab=desk | wtFlowDesk |
| Flow / 资金流 | Options Tape / 期权逐笔 | /options?tab=tape | wtOptionsTape |
| Flow / 资金流 | Tide / 资金潮 | /options?tab=tide | wtTide |
| Flow / 资金流 | 0DTE / 0DTE | /options?tab=0dte | wtZeroDte |
| Flow / 资金流 | Largest Events / 最大事件 | /options?tab=largest | wtLargestEvents |
| Flow / 资金流 | Surface / 曲面 | /options?tab=surface | tabSurface |
| Flow / 资金流 | Options Screener / 期权筛选器 | /options?tab=vol | wtOptionsScreener |
| Flow / 资金流 | Tickers / 个股 | /options?tab=tickers | wtTickers |
| Exposure / 敞口 | Exposure / 敞口 | /options?tab=gex | wtGex |
| Exposure / 敞口 | Positioning / 持仓结构 | /options?tab=positioning | wtPositioning |
| Exposure / 敞口 | Levels / 价位图 | /options?tab=levels | wtLevels |
| Structure / 结构 | Structure / 未平仓分布 | /options?tab=structure | wtStructure |
| Volatility / 波动率 | Volatility / 波动率 | /options?tab=volatility | wtVolatility |
| Statistics / 统计 | Category home; no child tab | /options?tab=statistics | optionsCategoryStatistics |
| Prophet / Prophet | Prophet / Prophet | /options?tab=prophet | wtProphet |

Category selection chooses its deterministic default: desk, tape, gex, structure, volatility, statistics and prophet respectively. It does not restore a remembered last subview. Bare /options and an unsupported tab resolve to **Flow → Options Tape**. The first value returned by searchParams.get("tab") is authoritative; this is not Analysis's closed duplicate-parameter parser.

Read aliases remain supported: tab=screener selects the Options Screener whose canonical write value is vol; tab=prism selects Exposure whose canonical write value is gex. Existing client guards send leaders/radar to /discover?tab=leaders or /discover?tab=radar and fundamentals to /analysis; this slice does not independently prove the earlier server redirect mentioned in comments. Internal hub drills continue through the existing onHubTab owner.

**Futures / 期货** remains a separate link to /options/futures, with exact copy in [futuresUiCopy.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/futuresUiCopy.ts). The existing OptionsWorkflowGuide child remains alongside the category navigation. Statistics mounts OptionsStatisticsView directly and has no child-tab row; an older optionsIa comment about its publisher is not evidence that the current component is absent or universally accessible.

**Access boundary.** Outside the existing FLOW_FIXTURE="1" branch, the page calls getLiveOptionsAccess(): denied renders OptionsPaywall; unavailable renders OptionsServiceUnavailable; other returned access proceeds to the workspace. A source comment describes the fixture as dev/CI, but this page contains no separate environment check that proves the flag cannot be enabled in production. No fixture environment was changed. The page explicitly permits magnification. This inspection does not establish Options financial payload schemas or the service producer mentioned in its comments.

**Local interaction owner and limitation.** [WorkspaceTabs.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/WorkspaceTabs.tsx) is controlled: it emits selection; the page owns the URL and tabs. Arrow keys wrap and select; Home/End select endpoints; roving tabindex and aria-selected are emitted. Panels and matching aria-controls targets remain the page's responsibility. The selected tab is revealed by horizontal-only scrolling after active/tab/locale changes. These source mechanisms still require actual keyboard, focus and panel-linkage evidence.

OptionsWorkspace.writeTabToUrl currently constructs a URL from window.location.href, calls url.searchParams.set("tab", pageKey), and passes null to history.replaceState. Consequently ordinary query bytes can be reserialized, duplicate tab values collapse, and preservation of other history metadata must be verified through the actual Next integration. It is inaccurate to claim existing raw-byte or history-state fidelity across this local action solely from the shared-shell resolver. This is an existing-owner qualification issue, not an implemented fix.

**Proposed F01 requirement.** Reuse this exact hierarchy and vocabulary in realistic shell stress frames. Keep all views and aliases reachable; do not introduce invented Overview/Plans labels or another Options registry. F02 supplies the shared tab primitive; the Options owner resolves any agreed query-write change. Local selection must not become a second global current-page marker.

## 4. Terminal entry and return fidelity

**Observed.** `sharedShellTerminalHref` carries `from=macro`, the captured return URL in `ret`, optional `symbol` and optional `ai=1`. Current callers should continue supplying the full absolute browser URL.

The topbar gives a valid URL-selected Analysis company priority over the active cursor and suppresses current-chart entry for an explicit invalid company. Mobile chart entry uses the active cursor; directory links use their direct admitted hrefs. These entry paths need comparative journey evidence.

`useFromMacro` prioritizes a fresh validated `ret`/`return`, then a recognized referrer/fallback, and keeps existing session return state. `safeMacroHref` is the existing destination gate. Its allowance for beta returns is distinct from embedded-parent origin permission.

`backToMacro` asks an admitted embedded parent to close Terminal, or otherwise performs `window.location.assign` to the captured URL. It does not use `history.back()` for the named return.

**Historical limits.** LegacyPageHost stores `{x,y,focusId?}` snapshots against parent history-entry keys in an in-memory map capped at 64 entries. A parent history traversal may pass a retained snapshot in `INIT.restore`. Identity changes clear those snapshots. Native workspace selection/filter state is not part of this shape.

**Proposed.** Distinguish “Open current chart” from generic Terminal entry and specify the same intentional return behavior for every retained entry path. Browser Back/Forward and named product return remain different actions.

**Root-reported live observation, not a new receipt from this advisory:** clicking Company Financials updated the captured `ret` destination to `/analysis?symbol=NVDA&page=statements`. The sole writer must bind its exact browser/source evidence when integrating this statement. This covers the latest local-view URL in the return target, not the complete journey.

**Unverified.** Complete native Analysis → Terminal → named-return restoration of selection, scroll and focus is not established; the root reports that its managed browser tab disappeared before completing the full chart return. The legacy child applying `INIT.restore` also needs browser evidence. Recover these through existing workspace/navigation owners; do not create a new general-purpose persistence system.

## 5. Actual backend, identity and protocol inputs

| Input | Observed producer/fields | Meaning and limits |
| --- | --- | --- |
| Account identity | Server layout calls existing Supabase `auth.getClaims()`; string `claims.sub` and `claims.email` are passed to AppShell | Subject is ownership identity; email is display/routing. Missing values become empty strings. This file alone does not distinguish guest, expired session and account-provider failure. Domain access remains separate. |
| Shell admission/status | [GET producer](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/api/shared-shell/status/route.ts) at existing `/api/shared-shell/status`; LegacyPageHost requests it with `cache:no-store`, same-origin credentials | Exact fields: `enabled`, `protocol`, `buildId`, `bridgeVersion`, `documentVersion`, `registrySha256`. `enabled` is `isSharedShellEnabled(process.env.MMX_SHARED_SHELL) && SHARED_SHELL_BUILD !== "unversioned"`. Producer is `force-dynamic`, `revalidate=0`; headers are `Cache-Control: private, no-store, max-age=0` and `X-Robots-Tag: noindex, nofollow`. No per-user auth/entitlement lookup or market clock occurs in this handler. Enablement is deployment compatibility, not personal access. |
| Route inventory | `sharedShellRoutes.generated.json` consumed by sharedShellRoutes | Existing projection owns `legacyPaths`, `nativePaths`, directory and source metadata. Counts/admission require the actual frozen export; a nav label is not admission. |
| Child READY | `title`, `href`, `contextRevision`, `bridgeVersion`, `documentVersion`, `responseKind` | Empty title has a source-label fallback. `responseKind=content\|coming_soon` does not encode every auth/data state. Host also checks exact canonical URL and current context revision. |
| View restoration | `x,y` finite nonnegative numbers bounded to 10,000,000; optional bounded `focusId` | Invalid shape returns null. Null restoration means no usable retained snapshot, not proof that an exact prior state was restored. |
| Presentation | Existing account meta preferences, `useLang`, browser theme cache; `ShellContext` | Context revision is an interaction revision, not a financial observation timestamp. Locale-provider storage internals were not inspected. |
| Build identity | `NEXT_PUBLIC_SHARED_SHELL_BUILD` or `unversioned`; protocol/version constants | Deployment/compatibility identity, not market freshness, schema approval or Paper revision. |
| Readiness timing | 15-second host deadline; admitted-generation INIT repeats at 250ms until reconciled | Bridge readiness/recovery behavior, not financial data cadence or permission to retry uncertain mutations. |

No security-price, macro-series, portfolio, watchlist, alert or saved-investigation endpoint is established by these files. F01 must reference the actual domain producer and owner when presenting such content; it must not invent a shell data API.

**Clock/null boundary.** A zero financial value is domain data, not a shell-empty state. Shell build identity, frame generation and context revision must not replace domain observation/publication/ingestion clocks. Shell readiness cannot certify that different domains have synchronized financial vintages. Domain owners supply stale/partial/null/unsupported meaning and source access; shell surfaces that meaning without recalculation.

### 5.1 Company search: actual transport, scope and states

**Observed ownership chain.** [ShellSearch.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chrome/shared-shell/ShellSearch.tsx) mounts [SymbolPicker.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/SymbolPicker.tsx) with scope=companies and trackSource=shared-shell. SymbolPicker lazily loads the incumbent [SearchModal.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/SearchModal.tsx) in pick mode. The host writes the selected manifest symbol through writeActiveSymbol, closes, and pushes /analysis?symbol= plus encodeURIComponent(next). That source action opens a new Company destination; it does not preserve an arbitrary preceding Analysis page/pane query. Any proposed retention change requires D07 agreement.

**Read transport and shape.** SymbolPicker calls getJSONResult("/data/manifest.json", { onRevalidate: apply }) from [dataCache.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/dataCache.ts). The underlying transport is fetch(url); there is no inspected server-side company query endpoint. The declared manifest has nullable as_of and a symbols record keyed by the exact selectable symbol. Its row type contains name, col, nullable verdict, and optional vts, mkt, zh, sec, last and chg. The picker stores only symbols. This read establishes the client contract, not the current served manifest contents, publisher provenance or coverage.

Loading starts on idle (requestIdleCallback timeout 2500ms, or 400ms fallback) and on pointer/focus/click intent. An in-flight latch avoids duplicate starts and a mounted guard protects updates. dataCache defaults to a 60-second cache TTL and stale-while-revalidate, with in-flight deduplication and memory/IndexedDB paths. A network failure is unavailable/network; non-success other than 404/410 is unavailable/server; malformed JSON or literal null/undefined is unavailable/malformed. Only 404/410 is transport-level absence. Those outcomes describe the artifact read, not whether a company exists.

| Actual picker condition | Existing displayed state | F01 retention requirement |
| --- | --- | --- |
| No symbols yet, read pending | Loading symbols… / 正在加载代码列表… | Do not show no-match or assert the company is absent. |
| No symbols, absent/unavailable/rejected read | The symbol list could not be loaded. / 无法加载代码列表。; Try again / 重试 | Preserve recovery. A Retry click does not prove a new network request: dataCache remembers 404/410 for 10 minutes unless its existing owner invalidates it. |
| Ready; empty query; no recent/browse rows | No symbols viewed yet / 暂无最近浏览的标的 | Empty navigation history is separate from an empty market. |
| Ready; nonempty query; no visible eligible result | No supported symbol matches / 没有匹配的代码, with the query | Scope, visibility and coverage limit this statement; do not claim global company nonexistence. |
| Query matches companies in disabled markets | Count and market-name disclosure; Show all markets / 显示所有市场 | Keep the cause visible and the existing preference mutation explicit. |
| Ready; selectable result | Exact symbol, one localized company name and available mkt text | Preserve symbol and venue distinction; choose the actual record rather than resolving by display name alone. |

**Eligibility and ranking.** [searchCategory.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/searchCategory.ts) admits a company only when sec is exactly Equities and the symbol is not in the fixed fund exclusion set SPY, QQQ, IWM, DIA, SOXL, GLD, TLT. Unknown classification fails closed. This fixed exception set is not proof of comprehensive fund/issuer classification. Company scope exposes All / 全部 and Stocks / 股票; it excludes composite selection and watchlist/list-add controls.

[markets.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/markets.ts) scores exact ticker 1000; ticker prefix 800 minus a capped length penalty; name/Chinese-name prefix 600; ticker substring 400; name/Chinese-name substring 200. A followed-market boost of 60 can reorder within tiers without overtaking another tier. SearchModal breaks remaining ties by symbol length then lexical order and caps query results at 30. The query is trimmed/lowercased; the directory's NFKC normalization, fuzzy matching and pinyin search are not established here. Both name languages remain searchable; displayName chooses the active UI language with the other as fallback.

With no query, Recent is filtered against current manifest/company/category/visibility. Stocks browse excludes those Recent rows, caps at 60, ranks positive numeric mcap where actually present, then retains manifest order for the remainder. The picker row type does not itself guarantee mcap coverage.

**Disambiguation limit.** Pick rows display the manifest key, localized name and raw mkt string. A missing mkt is shown as Venue unavailable / 交易场所未知. No issuer UUID or authoritative MIC/listing-resolution record is established by this row type. Keep suffixes and distinct symbol records; do not deduplicate companies by name or invent precise exchange metadata from a broad market group. Pick mode suppresses verdict/quote embellishment; search is not a fresh-price or signal statement.

**Preference side effect.** Before prefsReady, market visibility hides nothing. Afterwards the existing market preferences filter eligible results and Recent. [useMarketPrefs.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/useMarketPrefs.ts) binds Show all markets to enableAll: it sets all enabled markets, clears autoNarrowed, writes the local owner cache and queues serialized markets through the existing account preference pump. It leaves the followed list unchanged. This is an explicit preference action, not a temporary search filter; typing a query or following a destination must not call it implicitly. Delivery/readback remains that preference owner's responsibility.

**Telemetry boundary.** On committed choice the existing [trackSearch](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/searchTrack.ts) sends a same-origin keepalive POST to /api/track/search with symbol, source and optional query, deduplicated by symbol+source within five seconds. The [actual POST handler](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/app/api/track/search/route.ts) rate-limits, clamps fields, attempts getUser without requiring it, obtains visitor identity and calls recordSearchEvent. This is telemetry, not the source of company results or a saved-object action. The client never waits for success; failure must not block navigation. The event store and timestamp producer were not inspected, and no POST was executed by this advisory.

**Source-derived gaps to qualify.** SymbolPicker does not retain manifest.as_of or consume CacheOutcome.stale/revalidation metadata. Displaying rows therefore does not prove current publication/freshness, including after failed background refresh; the 60-second cache clock is not a market observation date. Also, apply only tests for a truthy symbols property: a syntactically valid JSON body without symbols can leave the initial picker loading with its latch still set. These are code-derived failure hypotheses, not reproduced browser defects. Required future behavior is truthful unavailable/stale handling through the existing cache/picker owner, with no invented endpoint or field.

**Accessibility boundary.** SearchModal provides combobox/listbox selection, active-descendant IDs, arrow/Enter selection and composition-aware event handling. Phone pick mode uses the incumbent MobileSheet; other layouts use SearchDialog/useDialogFocus. Source presence alone does not qualify IME behavior, spoken labels, focus return, scroll locking or phone keyboard/reflow. F02 controls primitive changes; D07 remains company identity/route owner.

## 6. Access, presentation and failure states

**Observed.** Host states are loading, ready, restricted, failed and changed. Release or registry mismatch produces the changed-generation boundary. A mismatched canonical READY fails. Invalid/stale-source messages are ignored. Nonvisible frames are hidden, inert and excluded from focus. Retry and open-original actions exist.

Guest, plan-required, expired-session, account-unavailable and uncertain-save states need actual auth/domain inputs. The current `coming_soon` discriminator alone cannot distinguish them. The design must not equate them or invent a live protocol enum.

`requestContext` changes presentation; theme requests update the existing browser cache, while explicit Settings persistence remains with the incumbent account preference pump. `applyThemeChoice` supports dark/light/auto. SharedShellPresentation restores incumbent dark chart presentation when it unmounts.

**Proposed.** Copy distinguishes temporary browser presentation from account-saved settings wherever persistence differs. Language changes do not alter region, listing, units or data clocks. A pane close does not claim that a pending/uncertain D23 mutation was cancelled or failed. Real domain recovery/readback remains authoritative.

## 7. Directory, focus and overlays

**Observed.** ShellDirectory searches finite generated destinations and legacy paths, normalizes NFKC/case, uses native aliases and preserves direct route identity. It initially shows 48 results, supports increments, preserves query/category while mounted, avoids prefetch, and uses a native modal dialog. Closing restores the trigger unless a destination/action was selected. Company search stays separate.

SharedShellRuntime registers parent-window `Ctrl/Command+K` and `/`, excluding editable controls. These handlers alone do not prove shortcuts work with focus inside a cross-origin legacy frame.

**Proposed.** Improve short names, grouping and disambiguation through the current registry/export owner. Preserve distinct same-label destinations. One primary inspector replaces its object; modal overlays trap focus, docked inspectors remain nonmodal. Escape dismisses the nearest applicable layer; closing restores a stable logical focus target. Global and local scroll ownership must be explicit. Every local tab remains reachable on phone/zoom.

## 8. F02-preserving geometry

Candidate values, pending joint qualification:

- Navigation: 224px at widths ≥1200; 196px at 861–1199; 72px when explicit compact is selected; overlay with zero consumed width at ≤860.
- Header: 64px above 860; 56px at ≤860.
- Gutters: 16px each below 768; 20px each from 768–1199; 24px each at ≥1200.
- Inspector: 320px plus 24px gap, docked only when remaining useful content is ≥640px. Otherwise modal.
- Useful width = viewport − consumed navigation − two gutters. Docking requires useful width ≥984px.

| Viewport | Default navigation | Useful content | Inspector outcome |
| ---: | ---: | ---: | --- |
| 320 | 0 overlay | 288 | Modal |
| 390 | 0 overlay | 358 | Modal |
| 768 | 0 overlay | 728 | Modal |
| 1024 | 196 | 788 | Modal; docking would leave 444 |
| 1280 | 224 | 1008 | Docked central content 664 |
| 1440 | 224 | 1168 | Docked central content 824 |
| 1600 | 224 | 1328 | Docked central content 984 |

At default expanded navigation, 1255px leaves 639px after docking and must use a modal; 1256px leaves 640px and permits docking.

**Compact threshold precision:** with actual 20px gutters in the 861–1199 range, 1095/1096 is the compact docking boundary. The requested 1103/1104 pair is a separate arithmetic fixture with a forced 48px total inset: 639/640px after docking. Under actual responsive 40px total inset, both 1103 and 1104 permit docking. Do not label that forced-inset fixture as the live responsive breakpoint.

The existing legacy wrapper has zero padding and native children may add their own padding. Future composition must avoid double-applying gutters and must verify actual usable widths across Macro, Company and Options. Navigation choice must not change silently merely to make an inspector fit.

## 9. Focused, public and internal compositions

- **Focused Terminal:** existing chart chrome and Brain singleton remain its owner. No nested AppShell. Named return preserves the valid destination contract; dark presentation exception is explicit. D06 owns chart-local behavior.
- **Public/anonymous:** the programme identifies public articles and `/x/<slug>` shared charts as distinct entry compositions. Retain their actual route/access owners, authentication return and public navigation. This source slice does not certify anonymous access, SEO or a live shared-chart journey.
- **Internal OS/admin:** separate audience, task navigation and authorization. Reuse F02 primitives where appropriate; registry presence or an AppShell title mapping does not grant public access. F03 tracks exact audience/admission evidence.
- **Investor workspace:** shared job navigation, domain-owned local tabs/content and owner-supplied access/data states. F01 cannot promote an unadmitted route or publicize an internal product through a directory label.

## 9A. Existing F02 domain composition dependencies

The [F02 source/data contract at c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82](https://github.com/mastermindx-market-intelligence/macro/blob/c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82/research/design_candidates/production_design_20261102/f02/SOURCE_AND_DATA_CONTRACT.md) supplies these already-researched integration boundaries. They are attributed to F02's own Macro b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e and Terminal b79b1e136290978ff7675087de979bb1b42b3713 pins, not silently described as independently rechecked at the F01 Terminal pin.

| Composition | Existing producer/consumer dependency from F02 | F01 requirement / remaining limit |
| --- | --- | --- |
| Macro /macro.html | scripts/build_site.py renders templates/dashboard.html.j2 with mode=macro; D03 stocks uses the same template with mode=stocks. VM build generated_utc is distinct from domain source/as-of snapshots. | Preserve D02/D03 regions and per-field clocks; do not turn build time into market freshness. Full field/producer qualification remains D02/D03. |
| Company /analysis | AnalysisWorkspace reads /data/${sym}.intel.json through getJSON, existing getBars(sym)/getFund(sym), and /api/quote?view=regular&syms=encodedSymbol with no-store. Prior-symbol state resets and late-response guards remain domain-owned. | Do not invent URLs behind getBars/getFund. Preserve report period, currency, precision, null and exact source citation. Illustrative Paper statement values do not substitute for those field contracts. |
| Options Statistics | useFlowStream("meta") consumes the existing /api/flow/stream?f=meta transport. options.observed_statistics_snapshot/v1 validates population/coverage/continuity, counters, roots, partitions and clocks; its consumer uses cached fallback or >120000ms since last observed record for stale. | This qualifies that statistics consumer, not the tape's complete print schema or current deployment. D08 owns tape fields/classification and source coverage. Connected transport cannot establish current data. |
| Public editorial | build_free_content.py renders seo_article.html.j2/seo_base.html.j2 from content/seo/blog; publication dates, canonical URLs, anchors, related links and English body/bilingual chrome are explicit owners. | Retain authored content and safe-render validation. No /zh/ route family, new publishing ledger or forced investor shell. |

The F01 artifacts are shell stress compositions. Field units, observed dates and limitations remain visible, but their illustrative values are not citations, producer output or evidence of a live consumer. Domain-owned controls and the whole available history remain required even where the specimen shows only a visible window.

## 10. Open qualification obligations

1. F01/F02 exact joint version and independent review evidence; candidate source is not acceptance.
2. Native and legacy exact-return, history, focus and scroll browser receipts.
3. Entry-path consistency for topbar, mobile, directory, AI and direct deep links.
4. Actual account/session-state producer distinctions; locale persistence details; D23 uncertain-save readback.
5. Current route/directory export and any proposed alias/group changes through F03's existing owner.
6. Real content-width, EN/ZH, light/dark, keyboard/touch, zoom and reduced-motion evidence.
7. Domain source clock/identity/access contracts for composed Macro, Company and Options content.
8. Actual legacy child restoration and shortcut behavior. Parent protocol transport is not proof of visible behavior.
9. Company search: current served manifest/source provenance, exact listing/venue disambiguation, stale-refresh disclosure, malformed-shape recovery and the negative-cache effect on Retry. Inspecting the consumer does not certify the live symbol universe.
10. Options local query-byte/history-state behavior and tab-panel accessibility through the existing owner; use the actual seven-category EN/ZH vocabulary in shell integration evidence.

Meaningful test specifications are in [ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md). All remain unexecuted in this advisory work.

