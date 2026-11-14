# D06 interaction and state contract

**Proposed requirements for a draft design candidate.** The “current owner” column names observed source ownership; proposed behavior that needs implementation is explicit. See [data contracts](ROUTE_DATA_CONTRACTS.md) for payload truth and [migration cases](BUILD_AND_TEST_PLAN.md) for verification.

## Control contracts

| Control / event | Preconditions and resulting state | URL / source write and current owner | Focus, scroll and recovery |
| --- | --- | --- | --- |
| Open exact instrument | Valid canonical chart token; resolve one symbol once across preload, shell and data cache. Ambiguous listing requires the identity owner's choice. | Existing `symbol` / `sym` route; preserve accepted return parameters. No saved-object write. D07 resolver + Terminal route. | Focus instrument/chart heading after navigation; announce unavailable identity without substituting another market. |
| Same-route symbol or research-pane open | New navigation intent supersedes older load. Pane reopening must retain existing open/close events. | `mm:open-pane` / `mm:close-pane` semantics remain; URL-only `router.push` is insufficient in current shell. | Keep temporary old chart visibly attributed/dimmed until committed new generation; never relabel old data as new symbol. |
| Change timeframe/session | Interval functional for current market/access; no fake seconds or intraday parity. | Existing TerminalShell state and preferences. Generic incoming `tf=` is not currently a route guarantee. | Preserve applicable user drawings and meaningful calendar window; reset timeframe-specific auto drawings by owner rule; invalidate bar/readout context. |
| Select reader bar | Exact sample exists in rendered series. Latest-loaded, historical and replay labels differ. | Reader local `selectedTime`; no account write. | Move via chart or previous/next controls; boundary controls disabled with reason. Update concise selected-bar summary, not every moving crosshair. |
| Ask about this bar — proposed explicit bridge | Reader symbol, TF, bar/time basis and data generation still match the active chart. | Existing shell AI callback/locked-line owner; no second Brain/store/kernel. D14 owns action semantics. | Show the bound bar before dispatch. If selection changes, discard/mark obsolete result. Never silently use current quote for an old bar. |
| Open/close Chart Context | Chart workspace owns eligible destination; research/table/native dossier may exclude it. | Existing ChartContextDock/TerminalShell placement; no URL or saved-object mutation. | Dock/inline reader nonmodal; blocking sheet modal. Explicit open focuses close/header. Close restores a visible enabled launcher/fallback with preventScroll only while that close legitimately owns focus; never steal a settings/navigation transfer. |
| Latest bar reset | A reader inspection is active and a rendered series exists. | Existing inspect(null) and onInspectTime callback; no account mutation. | Clear the local historical selection and show the latest loaded bar, with its actual clock; this is not proof of live freshness. |
| Reader layers, re-enable and Hide | User explicitly selects a setting. | Existing onSettings callback for visualRegime, visualVolume, visualLevels, visualEvents and visualContext; retain the existing settings owner. Hide sets visualContext=false and closes; re-enable sets it true. | Preserve reachable re-enable state. Keep the existing explicit layer-toggle analytics; do not create another persistence system. |
| Reader candle settings | onCandleSettings destination exists. | Existing close(false), then onCandleSettings callback. | Transfer focus to the settings destination; reader close must not steal it back to the chart launcher. |
| Useful / Unclear feedback | Explicit user feedback action. | Existing analytics track click with feature, action, ticker, timeframe, language and useful detail; local acknowledgement changes. | “Thanks” reflects local acknowledgement, not a verified saved-feedback receipt. Do not silently submit feedback on navigation. |
| Expand Intelligence / switch Summary, Oracle, Research, Activity | Correct symbol; independent sources may be partial/stale. | Existing OracleDash/Intelligence owner, source readers and local view state. No inference that four tabs share one clock. | Preserve chart instance and viewport. Activity filter has a labeled selected state. Full research goes through D07's parser. |
| Focus/full chart / rail drag / pane split | Existing chart mounted; active pane known. | Existing workspace state; only the owner persists final rail width/layout. No new layout store. | Coalesce resize once per frame; preserve logical range/selected bar. Provide keyboard resize and reset. Mobile mode changes must not reopen dismissed sheets. |
| Link panes | Same TF and valid calendar mapping. | `paneSync` and groupsA/B/C only. Does not synchronize symbols/TFs. | Refuse mixedTF links with explanation; don't leave a silently partial group. Read-only subscribers never activate panes. |
| Replay | Valid single-chart axis/span and supported data. | Existing replay owner; historical rendering only. | Show historical cutoff. Current calendar withheld. Exit visibly if split/mode/data invalidates replay. Drawing mutations remain blocked under current replay rules. |
| Draw/edit/hide/lock/delete | Active chart and rightful owner; exact tool point grammar/capabilities. | Existing drawing store and UUID epoch. Alert creation remains D23. | Escape cancels pending tool before retiring it/clearing selection. Delete only selected object; keyboard clipboard/undo scope respects editors and modal focus. |
| Save workspace | Signed-in owner; current revision and actual name decision. | Existing `/api/layouts` `save_workspace`; not drawing/watchlist/favorite storage. | Pending→authoritative success/conflict/failure/uncertain. Never show success for transport ambiguity; retain current workspace and reconcile receipt. |
| Edit/compile script | Signed-in; loaded own script or locked flagship. | Local editor buffer; synthetic diagnostic worker. No automatic server save. | Diagnostic says synthetic130-bar sample, not backtest. Superseded compile results discarded; preserve dirty buffer. |
| Save script | Fresh paid entitlement, captured clicked buffer, exact owner and `expected_updated_at`. | Existing POST`/api/scripts/save`; per-script in-flight dedup + server CAS. | Mark clean only for matching ID + valid returned update stamp and clicked snapshot. Newer typing stays dirty; conflict preserves buffer and offers comparison/reload of server version. |
| Add script to chart | Saved realID resolved by own library. | Current `/terminal?addScript=<id>` consumed once. Context-preserving URL is proposed owner work. | Paid-gated dirty save must explain blocked Add rather than silently stall. UnknownID doesn't add a phantom indicator. |
| Delete script | Authenticated owner, explicit target. | Existing DELETE`/api/scripts/delete?id=`; no paid gate; receipt has no row/CAS detail. | Confirm destructive target through current UI. On uncertain response reconcile owner list before retry. Do not turn list503 into empty success. |
| Legacy image download/copy | Existing chart snapshot action. | Existing mm:snapshot download/copy path; no public upload. | Preserve actual image behavior and copy/download errors. Do not claim this path automatically produces review metadata. |
| Private review capture | Stable scene and accepted render generation; explicit review flow. | Separate review capture contract; no public upload. Optional annotations default off. | Show exclusions/unknown clocks and before/after scene evidence. Release objectURLs, restore focus; moving scene fails honestly. |
| Public share | User explicitly invokes sharing; valid PNG within4MiB. | Existing anonymous POST`/api/snapshot`; public R2 upload. | Show “Creating link…”; clipboard failure exposes selectable link. Lost upload receipt is uncertain; avoid automatic duplicate upload. |
| Open snapshot | Exact valid10-character lowercase base36slug. | Existing `/x/<slug>` HEAD+PNG. No owner/expiry/revoke metadata; current footer links to `/`. | Accessible description says snapshot. A generic `/terminal` CTA is proposed D26 work, not current exact-chart return. Current notFound conflates missing/network: do not invent precise revoked/expired reason. |
| Open embed | Supported symbol grammar and daily data. | Existing `symbol,theme,lang,transparent,range,hdr,clean,fs` parser. | Widget only. Native fullscreen message and browser behavior differ; ordinary-browser no-op needs an honest alternative. |
| Return to research | Existing safe captured href or trusted embed parent. | `originNav`; exact href hard navigation or trusted `terminal:close`. No saved-state write. | Restore origin scroll/row only with explicit originating owner support. Otherwise land at accepted href and expose section navigation. |
| Macro tab/range/filter | Valid current source/published artifact; preserve current filters and local ranges. | Stage six top-level hash tabs; Market range localStorage; S&P Plotly relayout. Other filters aren't existing URL state. | Tab panel focus and status announce useful count; table overflow contained; filter changes never create alerts/watchlists. |

Observed owners: [TerminalShell](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/TerminalShell.tsx), [ChartPanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/ChartPanel.tsx), [VisualIntelligencePanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/VisualIntelligencePanel.tsx), [originNav](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/originNav.ts), [PineEditor](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/PineEditor.tsx), [capture dialog](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/components/chartCapture/ChartCaptureDialog.tsx).

## Outcome and microcopy matrix

The copy below is proposed EN/ZH content. Substitute only verified fields. A missing value is never rendered as zero or a prediction. Offer retry only when it can change the current outcome; preserve last-good data and unsaved work.

| State | English / Chinese specimen | Action and retained state |
| --- | --- | --- |
| First use / useful loaded chart | “Chart ready · {symbol} · {interval}. Open Context to inspect a bar.” / “图表已就绪 · {symbol} · {interval}。打开「上下文」查看K线。” | Chart tools available according to access. No onboarding mutation. |
| Loading | “Loading {symbol} history…” / “正在加载 {symbol} 历史数据…” | Reserve chart space. Keep identity; do not fabricate candles, quote or percentages. |
| Switching data generation | “Loading {newSymbol}. Previous chart: {oldSymbol}.” / “正在加载 {newSymbol}。当前仍显示 {oldSymbol} 的图表。” | Dim/attribute old generation until new data paints; controls cannot apply to mismatched context. |
| Empty with reason | “No history is available for this instrument and interval.” / “该证券在此周期暂无历史数据。” | Choose a supported interval or return. This is not upstream failure. |
| No filter matches | “No results match these filters.” / “没有符合筛选条件的结果。” | Clear filters; retain query for editing. Never imply source dataset is empty. |
| Partial | “Chart available. Volume context is unavailable.” / “价格图表可用，成交量上下文暂不可用。” | Render valid prices; dash/reason for missing volume-derived fields. |
| Stale saved copy | “Showing saved data from {observedAt}. Refresh failed.” / “正在显示截至 {observedAt} 的已保存数据，刷新失败。” | Retry existing reader; show saved-copy and market-observation clocks separately. |
| Closed market | “Market closed · last session {sessionDate}.” / “市场已收盘 · 最近交易日 {sessionDate}。” | Do not equate closed with delayed/offline. |
| Delayed source | “Delayed data · last print {time} {zone}.” / “延迟行情 · 最近成交 {time} {zone}。” | Explain actual feed category; not a global page-live badge. |
| Unsupported coverage | “{interval} data is not supported for this market.” / “此市场暂不支持 {interval} 数据。” | Supported alternatives; never fake US parity or upsample seconds. |
| Unknown time/adjustment | “Time basis unavailable” / “时间基准未提供”; “Adjustment basis unverified” / “复权依据未核实” | Keep chart source detail reachable; no green verified badge. |
| Upstream unavailable | “Chart data could not be loaded. Your workspace is unchanged.” / “无法加载图表数据。工作区保持不变。” | Retry current generation; no blank-save or reseeding. |
| Guest | “Sign in to save your workspace.” / “登录后可保存工作区。” | Continue permitted reads. Cross-navigation guest-state recovery needs an owner-approved handoff; no automatic import into an account. |
| Plan required | “Saving scripts requires an eligible plan.” / “保存脚本需要符合条件的订阅方案。” | Preserve buffer. Explain access and return; do not imply source already saved. |
| Session expired | “Your session expired. Your edits remain in this open editor.” / “登录已过期。当前编辑仍保留在此页面中。” | Preserve the mounted same-owner buffer. Before full authentication navigation, offer only a supported recovery/export path; persistent cross-navigation recovery is unproven. Recheck owner and outcome before mutation; no automatic import across accounts. |
| Save pending | “Saving…” / “正在保存…” | Disable duplicate submission for same object; editing may continue with captured snapshot semantics. |
| Saved | “Saved” / “已保存” | Only authoritative matching owner/object/revision receipt. Newer buffer may still say “Unsaved changes.” |
| Failed, no commit confirmed | “Could not save. Your edits are still here.” / “无法保存。当前编辑仍保留。” | Correct entitlement/input/connection then explicit retry; don't claim rollback without evidence. |
| Conflict | “This script changed elsewhere. Compare versions before saving.” / “此脚本已在其他位置更改。请先比较版本再保存。” | Read server version into separate comparison; never overwrite local buffer silently. |
| Uncertain save | “We could not confirm whether this was saved. Checking the saved version…” / “暂无法确认是否已保存。正在核对服务器版本…” | Read through current owner; no blind duplicate or new-owner replay. |
| Public PNG ready | “Snapshot link created” / “快照链接已创建” | Show actual link. Describe static image, not interactive restore. |
| Snapshot unavailable | “This snapshot is unavailable.” / “此快照暂不可用。” | Generic Terminal link. Distinct expired/revoked copy only if a future trusted lifecycle record proves it. |
| Source mismatch | “This research does not match the selected instrument.” / “此研究数据与所选证券不匹配。” | Withhold affected panel; keep correctly attributed chart. No cached relabel. |
| Historical calendar excluded | “Current calendar is hidden for historical context.” / “查看历史上下文时不显示当前日历。” | Return to latest loaded bar for current calendar; do not inject future-known events. |

N/A rules: static Macro pages have no account-save lifecycle unless a real shared saved-object control is introduced. Public PNGs have no edit/saved states. Dev harness data are synthetic, not a denied customer entitlement state. Loading and inaccessible data do not justify a subscription upsell unless the server actually reports that access boundary.

## Keyboard contract

Retain canonical bindings and advertise the executable registry:

- Symbol search: type alphanumeric outside text entry; Cmd/Ctrl+K. Palette: `>` outside input/contenteditable/modal/IME and without repeat or modifier conflicts.
- Draw: Alt+T trendline, Alt+J ray, Alt+H horizontal, Alt+V vertical, Alt+C crossline, Alt+F Fibonacci, **Alt+Shift+R rectangle**, Alt+M measure, Alt+X text, Alt+N note. An old ChartPanel comment says Alt+R; registry exact-modifier behavior wins.
- Escape: the active layer owns dismissal before chart actions. Brain source priority is slash palette → context inspector → streaming Stop → search close → panel close; live second-Escape closure was not observed, so qualify the discrepancy and exact focus return before acceptance. Drawing pending cancel → armed tool retire → selection clear. Double Escape≤500ms resets chart only when the chart owns the event. See [Brain lifecycle](BRAIN_SHELL_HANDSHAKE.md).
- Drawing edit: Delete/Backspace; Cmd/Ctrl+Z undo; Shift+Z or Y redo; Cmd/Ctrl+C/V drawing copy/paste; arrows nudge, Shift ten-unit step. No replay mutation.
- Hide drawings: Cmd/Ctrl+Alt+H. Alert: Alt+A at latest loaded close, under D23 ownership.
- Day Trade Mode: Alt+D; while active Alt+1/2/3/4 selects1m/5m/15m/1h.
- Snapshot: Alt+Cmd+S download; Shift+Cmd+S copy; Alt+S public share.

Existing handlers do not all prove contenteditable/IME/modal parity; these are required migration checks, not claimed current behavior. Every touch-only gesture needs a reachable control or keyboard alternative. See [drawing registry](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/drawingTools.ts) and [command palette](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/3cc8da8432d8d2d4e4cb597f49c4eaa95f1980c9/terminal/lib/commandPalette/catalog.ts).

## Persistence and race rules

Authentication is a hard renderer/owner boundary. In-flight reads/writes carry owner epoch, symbol, TF and generation as applicable; results from the previous owner cannot seed the next account. Keep UUID ownership, not mutable email. Unknown watchlist inventory means retry/provisioning state, not an empty list to seed or upsert.

Saved layouts own only their defined fields: arrangement, paneTFs, split, active pane, sync, chart type, indicators/settings/hidden state, comparisons/config and locked vertical line. They do not own human drawings, watchlists, toolbar favorites, alerts or separate Day Trade Mode snapshots. Legacy absent fields mean “no claim,” not reset. Deep-linked symbol sessions skip both `mm.ws` restore and persistence.

Closing a drawer, changing region or navigating back must not save or delete anything. A mutation starts only from the user action that names the target; server owner/entitlement validation and matching readback determine success.


## Additional qualified-state requirements from the live baseline

| State transition | Proposed outcome | Evidence boundary |
| --- | --- | --- |
| Reader open → Brain requested | Where the shared-shell policy applies, suspend evidence presentation/width and preserve domain identity through its current owner; open the existing Brain. Focused Terminal adoption requires its own qualified integration. | Current Terminal retained the 460px reader under Brain. No new close event or second store is authorized. |
| Brain close → evidence available | Confirm the actual lifecycle, restore connected invoker or logical fallback without stealing focus, and expose the reader trigger. Reopen only on explicit action after remeasuring space. | Actual close exists; Terminal does not bind conditional onClose. Visible close is not request cancellation. |
| Dock/inline/focused placement → valid inspection cursor | One existing cursor is shared by crosshair and bar stepping; retain it through presentation-only changes until a legitimate owner event changes it. Latest clears it. Keep AI locked state separate; exact Ask needs explicit binding. | Later pointer-outside-plot tests retained2026-10-27; disclosure/scroll reset and dock-to-inline BODY focus were observed. No separate reader pin exists. |
| Presentation transition with reader focus/open state | Keep open intent and valid disclosure/scroll within the existing reader owner; move focused control only if its removed subtree still owns focus. A dismissed reader stays dismissed; phone sheets follow their distinct breakpoint rule. |460px requested rail width survived a boundary roundtrip; disclosure/scroll reset. Phone close restored More; hub return focused reader Close. These are bounded paths, not universal success. |
| Intelligence event → reader | Event location preserves its event date/known date and chart coordinate. Reader either explicitly acknowledges a supported event selection or continues to say Latest truthfully. | Live historical viewport and latest reader date coexisted under separate current owners. |
| Comparison anchor/readout unavailable | Keep primary and comparison identities and actual coverage. Show a reason rather than imply a measured zero or shared price basis. | Owner qualification still needed for observed 1993 anchor/readout. |
| Stage slice failure | “This view could not be loaded.” / “无法加载此视图。” Offer the existing affected-source retry where supported; keep other states independently attributed. | Do not append “other views are unaffected” unless their current successful state is actually known. |
| Chinese embed | Preserve canonical identity while exposing matching document/content language and meaningful source clock. | Live visual translation with lang=en and zoom-restricting meta is an unresolved accessibility finding. |

Existing session origin state may persist after a new symbol-only entry. A new accepted ret/return or qualifying origin supersedes it; absent fresh origin, existing session context remains eligible. Retain originNav's actual cache and hard-navigation/trusted-parent rules, not a new generic history store.

## Later source-state qualifications

[SOURCE_DELTA_20261103.md](SOURCE_DELTA_20261103.md) binds the current-source contracts: company preview versus explicit Open, validated company_query/history with exact listing context; cache observedAtMs unknown/valid/exact-payload states; no-store GET/HEAD404 missing-data fallback; and optional Pine retained receipt versus explicit unavailable/worker_required. Preserve ordinary workflows and current owners. None of these source states is an independently proved served path.

[RESPONSIVE_AND_STATE_AUDIT.md](RESPONSIVE_AND_STATE_AUDIT.md) separates requested/effective rail width, provisional640px price-plot fit, conditional focus, current inspection identity and bounded scroll/disclosure retention. Root Terminal zoom restrictions are now observed as well as Embed's earlier issue; no actual zoom conformance is claimed.
