# D04 — Product and interaction contract

**Version:** D04-SPEC/0.1.0. **Status:** source/specification candidate; editable final composition, independent reference review and implementation are outstanding. This specifies intended behavior. It does not claim that proposed interactions ship today. Evidence and current/proposed distinctions are in [SOURCE_INDEX.md](SOURCE_INDEX.md), [ROUTES_AND_DATA.md](ROUTES_AND_DATA.md) and [PAPER_REVIEW_AND_GATES.md](PAPER_REVIEW_AND_GATES.md).

## 1. The product and the user

The primary user is a self-directed market researcher with a broad question and limited attention: **where is something worth investigating, which names explain it, and what evidence survives comparison?** The outcome is a defensible shortlist with its universe, observations and caveats intact. A shortlist is research context; it does not activate an alert, add a portfolio position, place an order or grant permission to trade.

The fast daily user needs a useful answer in the first screen. The deeper researcher needs membership, ranking, source clocks, alternative measures and contradictory evidence without changing products or losing their place. Mobile should support the whole decision, including comparison, inspection and explicit saving; it should not become a read-only teaser.

### Taxonomy decision

Use **Discover** as the existing product entry. Within it, retain distinct analytical jobs and expose a shared universe/context bar only where the inputs actually mean the same thing. Local view names are labels in this contract, not newly registered routes.

| Job / surface | Main question and primary object | What stays distinct |
| --- | --- | --- |
| Stock Screener | Which listings meet my criteria? A sortable, filterable result table. | Asset class, market, currency-qualified liquidity, classification source, technical/fundamental predicates and unknown observations. |
| Market Heatmaps | Where is movement concentrated and how broad is it? A dense map with table access. | Macro company capitalization, Terminal legacy CAP price×volume proxy, explicit USD CAP and equal sizing; price versus flow; company versus theme/subtheme tiles. |
| Confluence / Signals | Which builder-ranked signal combinations currently match names? Comparable rank rows with paired historical evidence. | Recipe identity, variable D/W legs, recent/older sample bases and public evidence versus protected identities. No UI reranking disguised as filtering. |
| Top Picks | Which names have stronger conviction, and separately which have an entry condition? A dense ranking table with independent timing column. | Conviction, residual alpha, entry signal, extension, valuation and trend are not one interchangeable score. |
| Themes / basket detail | What does a defined group contain and what drives its behavior? Membership plus performance, comparison and evidence. | Curated equal-weight baskets versus provider theme trees; curation dates versus index masks; back-projected history versus point-in-time observations. |
| Fund moves | What changed in actual disclosed fund holdings? Fund/stock evidence and ranked research context. | Share changes, portfolio-weight changes, price effects, freshness and free versus gated rows. This is not generic ETF price screening. |
| Dislocations | Which qualifying episodes deserve investigation, and what changed? Confirmed, Forming and Ended episode groups with catalyst/evidence. | Watchlist versus paid Market access, episode lifecycle, knowable-at clock, coverage and stale-empty qualification; no forced comparison to confluence win rates. |
| Quant Lab | How concentrated, correlated and fragile is the market context? Matrix, risk budget, stress replay, factor evidence and breadth comparisons. | Model definitions and horizon/risk assumptions. `/advanced.html` is this existing analytical route; do not rename its content to “advanced filters.” |
| Movers compatibility | Where did the biggest moves and activity occur? Existing Stocks hub movers section. | Preserve `/movers.html` as the current fixed replacement redirect to `/stocks/index.html#today-movers`. |

Sector analysis remains D05's product. Graph membership truth remains D13's. D03 supplies macro context; D07 owns company research; D19/D20 qualify regional universes; D23 owns saved objects; F01 owns global search and shared navigation. A local search filters the active list only and says so. It must not become a second global entity search.

### New or strengthened proposals

The common inspector, cross-perspective selection, matched-cohort comparison, staged filter preview, portable return context and typed fixed/live heatmap saving extend existing production/Paper capabilities. They are **proposed integrations**, not a claim of implemented parity. Reuse existing source owners and adapters. Do not introduce another auth store, save queue, membership registry, navigation coordinator or assistant.

## 2. First useful view

The first screen has one primary analytical object and at most two supporting modules: a concise scope/quality strip and a context inspector when width permits. The map or table occupies the useful area. No decorative hero should push every result below the fold.

1. A compact title and a one-line question establish the current job.
2. A scope row names market/universe, asset type, membership date, observation session, measure and active filters. If any input is unsupported, the field says why and the preceding valid context stays intact.
3. A quality strip distinguishes the full eligible universe, observed records, rendered subset and missing observations. “Showing 500 of 10,258” must not borrow the denominator of a 500-row drawing for a 10,258-symbol breadth statistic.
4. The primary map/table shows consistent signs, units and sorting. The selected group or entity is visibly identified using a neutral surface and a semantic selection mark; color alone does not carry state.
5. The secondary inspector answers “what is this, why is it here, how current is the evidence, what should I inspect next?” It offers company research, peer comparison, source detail and explicit shortlist action. It does not silently save.

Confluence has a different first object: the verified count and ranks 1–3, each with the same evidence grammar. Show recipe/leg stack, recent and older validation, sample bases, baseline difference, historical appearances, last observed and current match count. Entitlement can conceal matching identities; it cannot demote public evidence into tiny compressed text. Always-visible concise honesty includes survivorship, searched recipes and watch/research status. Extended method disclosure supplements that line.

## 3. Complete normal-data journeys

### J1 — Discover → compare → inspect → exact return

The researcher opens Discover with an explicit universe and sees its observation clock. They narrow the universe with staged filters. The preview accounts for matches, excluded records and unknown records. They apply a valid preview, then choose a heatmap cell or basket. The whole group remains accessible; selecting a company opens an inspector without changing the cohort. They compare the selected and reference observations on the same membership/definition and open company research. **Back to [named group]** returns to the same route/view, filters, time range, comparison pair, membership version, selected entity, sort, visible row/map position and focus origin.

If observations changed meanwhile, restore the prior confirmed display when the incumbent data owner can supply it; otherwise restore the same configuration and say that newer observations are shown. Never imply exact historical replay when only the query survived. Offer **Review update** with changed membership/observations. Membership, cursor and result-set revision are different identities.

### J2 — Save → reopen with changed observations

The researcher selects **Save view**. The choice is explicit:

- **Live filter:** “Keep these rules. Matching companies can change.” The inspected D23 candidate persists its constrained price-return rule, not arbitrary display/comparison settings. Persisting additional settings needs separate D23 schema qualification; until then retain supported display context through the existing route/history seam and explicitly list it as excluded from the saved object. A preview can be included through an existing evidence owner; it is not a permanent roster.
- **Fixed group:** “Keep these companies. Prices and other observations can change.” Persist exact qualified listing IDs and membership receipt. “Fixed” never means frozen prices or a historical portfolio.

The review names destination, privacy, object type, included count and what will update. Submit one owner request. While pending, prevent duplicate submission. Confirm **Saved** only with D23's authoritative object/request readback. If transport is uncertain, preserve the original request and present **Check this save**; leaving does not cancel it. On reopening, show saved configuration time and new observation time separately. For a live filter, display entrants, exits and unknowns before replacing a previously reviewed cohort. For a fixed group, absent/unpriced/delisted members remain accounted for.

The inspected #778 recovery handle retains only `{version, ownerId, requestId, fingerprint}` in owner-scoped sessionStorage. Same-tab recovery depends on that storage remaining available. It does not retain the full submitted name/members/condition or establish an account-wide pending list. Full-draft restoration and discovery of unresolved requests from Saved views are additional D23 integration requirements; do not promise them before qualification. Lost/blocked storage needs honest limited-recovery copy. Fixed membership also does not persist a general metric definition or comparison configuration in that candidate.

### J3 — Legacy and cross-product entry

A legacy URL, a `#theme-*` basket link, a selected heatmap company or an ETF row arrives at its exact current destination. Parse the existing route contract first. A source-compatible route alias is not permission to change its fragment or rewrite a saved definition. Company identity is market/listing-qualified. Cross-market discovery uses verified mappings and explicit unavailable states; changing language never changes market, currency or universe.

## 4. Interaction rules

All rows below are intended behavior unless the route/data contract marks them as observed incumbent behavior. Following the refreshed F01/F02 concurrence, every focus-return instruction is conditional on the retiring surface legitimately owning focus; preserve deliberate later focus elsewhere and let the active owner handle nested Escape. “No write” means no account/domain mutation; transient URL/history state can change as specified.

| Control / event | Preconditions and resulting state | URL/history / write owner | Feedback, focus, touch and recovery |
| --- | --- | --- | --- |
| Switch local analytical tab | Same qualified universe where compatible; preserve each view's own controls. Show incompatible dimensions before dropping them. | Preserve existing `tab` parser and other permitted query keys. Commit deliberate tab change to incumbent history; no account write. | New tab selected; focus stays on tab. Arrow keys navigate tabs; Enter/Space activates. Mobile exposes every tab in an explicit view menu or contained strip. |
| Change market/universe | Validate source availability and identity mapping. Stage any filters invalid in the new universe. | One committed context transition; no save or alert activation. | “This filter is not available for [market].” Keep the old results until Apply or Cancel; never relabel US observations. |
| Search within active view | Filter only the active universe; label it “Find in this view.” | Replace transient query while typing; one committed history step on deliberate submission. Existing parser support must be added by its owner before new keys ship. | Preserve selected entity when it remains in scope; otherwise keep an “Outside current results” inspector with Clear selection. Escape clears only the search when it owns focus. |
| Open Filters | Copy current committed predicates into a draft. | No URL/account mutation. | Modal/drawer focus moves to title/first field; Cancel discards the draft and restores trigger focus. |
| Preview filters | Evaluate against a named membership + data revision + metric definition. | Read only; owner producer supplies match/exclude/unknown and preview token. | “N match · M excluded · U unknown.” Unknown is neither a match nor a zero. Keep every member accounted for. |
| Apply preview | Accept only the exact reviewed definition and revision; membership identity matters even when counts are unchanged. | Commit configuration through existing view state; no saved-object mutation. | If outdated: “The results changed. Review the updated preview.” Keep draft and previous results; do not auto-apply. |
| Undo applied filter | Restore previous committed configuration and cohort receipt. | One reversible view transition; not a new saved version. | “Filter removed.” Restore prior selection/focus/position where still valid; explain observation updates separately. |
| Change horizon/date | Check availability, session/calendar and metric basis. | Preserve group and other display choices; record committed query using the route owner. | An unsupported horizon remains named/disabled with its reason. Do not silently substitute 1D while leaving a 1M label. |
| Change size or color | Only list source-qualified measures for this universe. Size and color have separate legends/units. | View configuration only. | Reflow after user action; selected identity remains stable. For incumbent Terminal CAP announce “Area: price × volume proxy; color: one-day return.” USD CAP and Macro company capitalization have different definitions. No unqualified currency sums. |
| Select map cell / row | Select a stable group/listing identity; show full cell membership. | Selection can be URL-visible if the parser supports it; transient hover is not history. | Enter opens inspection; Space adds/removes selection when multi-select is explicit. Tiny tiles are reachable through Search/Table/Full cell. No hover-only action. |
| Compare selection | Preserve order, membership and observation references. Default to a small legible comparison; the full group remains reachable. | Comparison state, no write. | Same scale and dates across columns; labels expose weighting and missing denominators. Keep the same company positions in paired maps. |
| Inspect group member | Keep parent cohort and comparison; never filter the parent simply because one member is selected. | Shared inspector slot owned by F01/F02; domain evidence retained. | Desktop dock only if minimum useful width remains; otherwise modal/full-screen. Escape closes the top surface only. |
| Open company / chart | Resolve actual listing and available target using D07/current route factory. Retain origin context before navigating. | Existing shared-shell/navigation owner; cross-origin handoff only through qualified owner seam. | Destination title identifies exact entity. Back returns to named origin; missing origin falls back to safe canonical parent with disclosure, not a guessed browser-back. |
| Open Sources + method | Pin evidence to field, observation and membership revision. | Read only; source links allowed by incumbent data/access rules. | Focus enters evidence heading. Close returns to the exact trigger if it still owns the transition; do not steal focus from subsequent user work. |
| Sort table | Keep the incumbent research-order semantics, stable ties and null-last behavior. | View state; no source reranking. | Native header button with `aria-sort`; sort direction and rank definition are announced. Scroll/focus anchored to selected stable row after refresh. |
| Shortlist selected | Use existing local selection first; account persistence is an explicit D23 action. | No automatic watchlist, portfolio or alert write. | Display selected count and identity basis; unavailable members remain visible with reason. |
| Open Save | Review fixed group versus live filter, included/excluded fields and exact destination. Arbitrary display/comparison settings are excluded by the inspected candidate. | No write until Submit; additional persistence fields require D23 schema qualification. | “Fixed group keeps companies, not prices.” Cancel returns to original result state. |
| Submit Save | One request for one immutable submitted definition. | D23 existing persistence/request owner. | “Saving…”; submission disabled while that request is unresolved. Correctable field errors preserve draft and focus the error summary. |
| Save outcome unknown | Original request still may have applied. | Query original owner request using its recovery handle; do not issue a replacement request. | “Save status unknown. Your save may have completed.” Buttons: “Check this save”, “Return to results.” Same-tab handle recovery depends on available sessionStorage; account-wide pending discovery and full-draft restoration are unqualified requirements. |
| Reopen saved view | Authorize before returning private payload; validate schema/version and entity mappings. | D23 read; no implicit migration, refresh-save or alert activation. | Report fixed/live meaning, saved time, observation time and changes. Unsupported version offers review/export when owner supports it; do not silently downgrade. |
| Background refresh | Accept qualified revision atomically; reject wrong-universe response and stale response ordering. | Existing data owner, one subscription per source. | Keep committed truth while refreshing. Announce a concise update; avoid reordering the user's comparison under their pointer. Offer review when membership changes. |
| Theme / locale | Existing F01/F02 preference owner; preserve data state. | Existing preference mechanism only. | Re-render labels and semantic palette; keep signs/units. EN green-up and ZH red-up where currently governed are explicit legend mappings, not data inversion. |
| Reset | Reset only controls in the named scope after showing the scope in the action label. | View state; no deletion of saved objects. | “Reset filters” differs from “Reset display.” Keep current universe unless explicitly included. |

## 5. Exact return specification

This is a **proposed extension of the existing F01/domain navigation seam**, not a new global state service. The incumbent URLs remain valid while owners qualify it.

`ReturnContext` needs: origin route/host, canonical route ID, active view; qualified universe and membership revision; committed filter definition; primary/reference observation IDs and date range; metric definition including neutral threshold; sort key/direction/tie rule; selected group/listing and comparison order; map zoom/viewport or table row identity and offset; disclosure state where meaningful; logical focus trigger; owner-approved history entry identifier; saved-view ID/version if applicable. Scroll is an enhancement to the logical row/cell anchor, not the identity itself.

Restore in order: validate authorization and route → parse configuration → restore membership/observation receipt if available → render stable rows/tiles → restore selection → restore logical anchor/scroll → restore focus without additional scrolling only while the retiring transition legitimately owns it → announce updates. Preserve deliberate later focus elsewhere, including after delayed callbacks or a dock/overlay placement change. A missing row returns to its nearest surviving group header with “The previously selected company is not in this result.” Browser back/forward must not create a second history entry during restoration. Direct external entry without an origin uses a named canonical parent and makes no exact-return claim.

Cross-origin context must not contain private saved-view contents, protected tickers, credentials or arbitrary redirect URLs. Do not assume session storage can be read across hosts. Preserve existing source links until F01/D07 have qualified the handoff. If the complete state cannot be carried, disclose “Returned to the same view; position could not be restored” rather than claiming exact restoration.

Qualify three separate return paths: same-document history; same-origin cross-document navigation; and specifically allowlisted Macro↔Terminal cross-origin handoff. The first two do not prove the third. F01/D07 must name the destination allowlist, handoff mechanism and restoration limits. An unqualified external URL is rejected. Explicit incumbent reset actions remain exceptions to incidental preservation: Leaders/Radar active-tab reselection resets their drill, and Terminal price/flow layer change clears selection and changes the sizing default. These are user-selected scope changes, not silent saved-object mutation.

## 6. State and copy contract

State axes are independent: access, request, data availability, freshness, coverage and write outcome. For example, a signed-in user can have a stale partial map and an uncertain save at once. Do not flatten that into one green success badge.

| State | Required truth and useful action | EN / ZH primary copy |
| --- | --- | --- |
| First use | Explain the current universe and one next action; keep normal loaded object visible when available. | “Choose a universe to start.” / “选择市场范围以开始。” |
| Initial loading | Skeleton matches final geometry; no fabricated count/rate. | “Loading this view…” / “正在载入此视图…” |
| Refreshing | Keep last confirmed data visibly dated, preserve controls. | “Updating · showing [session]” / “正在更新 · 当前显示 [时点]” |
| Filter-empty | Valid source with zero matches under these filters; global availability separate. | “No matches for these filters.” / “没有符合这些筛选条件的结果。” Action: Reset filters. |
| Global zero | Valid complete evaluated universe, verified zero matches. | “No setups matched in [universe] at [session].” / “[时点]的[范围]内没有匹配组合。” |
| Missing/unpriced | Roster member remains; numeric observation absent. | “No observation for [session]. Still a group member.” / “[时点]暂无观测值，仍属于此分组。” |
| Partial | Explicit numerator/denominator, missing reason, links to affected rows. | “N of M observed. U unavailable.” / “M 项中已观测 N 项，U 项不可用。” |
| Stale | Clock/expected session and scope of stale component visible. | “Last confirmed [session]. Update unavailable.” / “最后确认于[时点]，暂时无法更新。” |
| Unsupported | Feature/universe reason, retain context, show supported alternative only by explicit action. | “This measure is not available for [universe].” / “[范围]暂不支持此指标。” |
| Error | Failure is not zero; retry read does not recreate a write. | “Could not load this view. Your filters are kept.” / “无法载入此视图，筛选条件已保留。” |
| Guest / plan required | Public evidence and allowed identities only. Server omission remains the boundary. | “Matching identities require access.” / “查看匹配标的需相应权限。” |
| Expired session | Keep non-sensitive local draft; reauthorize before private read/write. | “Sign in again to continue this save.” / “请重新登录以继续此保存操作。” |
| Save pending | Bind to original request, no success until authoritative readback. | “Saving…” / “正在保存…” |
| Save failed | Only definitive rejected/not-applied outcome permits edited resubmission. | “Not saved. Your draft is kept.” / “未保存，草稿已保留。” |
| Save uncertain | Preserve the original request recovery handle; check original request. Full-draft restoration is not guaranteed by the inspected candidate. | “Save status unknown.” / “保存状态未知。” |
| Save confirmed | Identify object and location; undo only when owner supports it. | “Saved to [destination].” / “已保存到[位置]。” |
| Outdated preview | Same count can hide changed identities; require a new review. | “Results changed. Review before applying.” / “结果已变化，请核对后再应用。” |

Confluence: filter-empty and global-zero are separate, and entitled hydration can be loading/failed while public evidence remains useful. ETF: a denied payload must not expose protected rows in static HTML, hidden DOM or search indexing. Dislocations: no evaluated candidates is different from unavailable producers. Save states are not applicable to purely read-only compatibility redirects; their source page state survives as defined by the existing redirect.

## 7. Accessibility, motion and measurement

Keyboard users can reach every view, filter, sort, group member, comparison cell, source and return action. A virtualized table exposes row counts and position without misleading assistive technology. Provide a real table/list alternative for 2D charts and tiny map tiles. Tooltip evidence is available by focus/tap; motion does not reveal information unavailable without animation.

Use F02's type, control and data-formatting roles after release. Tabular numbers align comparable observations; content sets row height for long Chinese labels and variable leg stacks. The house target is 44px for important touch controls, with at least 48px phone result rows where content permits; these are product targets, not a misstatement of WCAG's 24px minimum/spacing criterion. Verify text contrast, selected/disabled distinctions, zoom/reflow and non-color signs against the actual compositions.

Motion is purposeful: brief selection emphasis, panel transition and explicit data refresh. Do not continuously rearrange maps, pulse price colors without need, or animate uncertain writes as success. Under reduced motion, replace movement with immediate state changes and concise status announcements.

Success measures are **proposed**, not measured: time to first useful comparison; proportion of detail visits with successful named return; number of unexplained reset/drop events; filter-preview/accounting failures; fixed/live-save comprehension; duplicate save requests; discoverability of offscreen members and unknown data. Existing analytics owner must approve minimal event schemas and avoid protected identities/raw queries. Performance targets and tests are in [BUILD_AND_ACCEPTANCE.md](BUILD_AND_ACCEPTANCE.md).
