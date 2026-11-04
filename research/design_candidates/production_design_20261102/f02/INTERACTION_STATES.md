# Interaction, state and accessibility contract

Companion to `F02-SYSTEM/1.0.0-candidate.2`, with the source-policy refinements bound by [F02 concurrence with F01 candidate.4](F01_HANDSHAKE_CANDIDATE.md). This is a proposed component contract, not a new domain API. See [SOURCE_AND_DATA_CONTRACT.md](SOURCE_AND_DATA_CONTRACT.md) for actual owners and current behavior. The HTML specimen demonstrates local state transitions in source; browser execution is unverified. No production save, preference, export or entitlement was exercised or changed during this assignment.

## Independent state axes

| Axis | Vocabulary | What must remain separate |
| --- | --- | --- |
| Availability | loading, loaded, empty-with-reason, unavailable, unsupported, error | A completed zero-result query versus a publisher that never supplied data |
| Coverage | complete, partial, unknown | Available count, eligible population and missing count; no invented denominator |
| Freshness | current by owner policy, stale, unknown | Source observation, publication, retrieval and successful network response |
| Transport | connecting, connected, reconnecting, failed | The age/completeness of the data carried by the connection |
| Market session | open, closed, holiday, unknown | Connection state and source update state |
| Access | guest, allowed, denied/plan-required, expired, service-unavailable | Resource denial versus entitlement provider failure; never use a client color as enforcement |
| Interaction | default, hover, selected, focused, disabled, busy | Selection can persist after focus moves; keyboard focus must remain visible |
| Mutation | idle/draft, pending, saved, failed, uncertain | Network ambiguity is not confirmed failure; saved requires actual owner confirmation/readback |
| Provenance | reported, derived, estimated, illustrative, model output | A source citation does not validate a model or turn a heuristic into probability |

Combination rule: keep usable values when their source identity still matches the current context, show the original clock and a concise affected-scope caveat, and prevent incompatible actions. If the entity/listing/context changes, do not relabel retained data from the previous entity. Use the existing request-generation/race guard. One compact receipt can express several axes, for example “Connected · Market closed · Source 30 Oct · Partial 7/8”; it is not four decorative status cards.

## Copy and recovery matrix

Copy below is final proposed component copy with placeholders to be supplied by the actual owner. The specimen supplies illustrative availability, freshness, coverage, access and write axes. Its local simulations do not demonstrate every consumer recovery route or producer state. Public static articles do not manufacture account/save or live-transport states; they reuse relevant source/error patterns only where such behavior actually exists.

| State | English | Simplified Chinese | Retained content / recovery |
| --- | --- | --- | --- |
| Loading | **Loading observations.** Values will appear when the source responds. No result count is available yet. | **正在加载观测数据。** 来源响应后将显示数值。当前尚无结果数量。 | Keep stable layout and any valid earlier snapshot clearly dated. `aria-busy=true`; skeleton decorative; no “empty” label. |
| Loaded | **Source: {observation}.** {coverage}. | **来源：{观测时间}。** {覆盖范围}。 | Values, units and evidence reachable. No permanent success banner for routine fetches. |
| Empty query | **No observations match this view.** The request completed with 0 matching records. | **没有符合此视图的观测数据。** 请求已完成，匹配记录为0。 | Show current filters and clear/reset action. Do not imply no market activity. |
| No publication yet | **No observation has been published for {period}.** | **{期间}尚未发布观测数据。** | Keep calendar/source context. No “0” until the producer reports zero. |
| Partial | **Partial coverage.** {available} of {eligible} observations are available. Missing values are not zero. | **覆盖不完整。** {eligible}次观测中{available}次可用。缺失值不等于零。 | Preserve available chart/table; explicit gaps. If denominator unknown, say “Coverage not quantified” rather than a fraction. |
| Stale | **Older observations retained.** Source: {time}. The expected update has not arrived. | **保留较早观测。** 来源：{时间}。预期更新尚未到达。 | Source policy supplies expected cadence; retain exact period and source, no “live” label. |
| Unknown freshness | **Source age unavailable.** A source observation time was not supplied. | **无法确定来源时效。** 未提供来源观测时间。 | Retrieval time can be shown separately; it cannot substitute for source time. |
| Unsupported | **This source is not supported for this listing.** No value has been inferred. | **此挂牌标识尚不支持该来源。** 未推断任何数值。 | Existing owner/coverage explanation, alternative valid sources, return to supported context. |
| Source unavailable | **This source is unavailable.** Other available evidence remains visible. | **此来源不可用。** 仍显示其他可用证据。 | Retry only if actual owner supports it; no fake refresh control on a static document. |
| Refresh error | **Refresh failed.** The last successful view is still available. | **刷新失败。** 仍可查看上次成功加载的数据。 | Retry read; keep error context and prior clock. Do not clear useful data or mutate a saved view. |
| Guest | **Sign in to save this view.** Public evidence remains available. | **登录后可保存视图。** 仍可查看公开证据。 | Only when the actual route allows public reading. Preserve existing return URL through the existing sign-in flow. |
| Plan required | **This source requires an eligible plan.** Available public data remains visible. | **此来源需要符合条件的订阅。** 仍显示可用公开数据。 | Server omits restricted payload. Existing plan entry only; no fabricated plan names or prices. |
| Expired before send | **Your session expired.** Your view is retained. Sign in again before saving; no change has been sent. | **会话已过期。** 已保留当前视图。再次登录后方可保存；尚未发送更改。 | Applicable only with proof request was not sent. Preserve draft/context and exact authorized return target. |
| Expired after send | **Your session expired while saving.** The outcome is unknown. Check the existing request after signing in. | **保存期间会话已过期。** 结果未知。登录后请检查现有请求。 | Do not label failed or resend without readback/deduplication evidence. |
| First use | **Choose a starting view.** Open an example or select an available instrument. | **选择起始视图。** 打开示例或选择可用标的。 | Show real valid choices supplied by domain owner; no arbitrary unsupported default. |
| Pending save | **Saving…** This request is pending. | **正在保存…** 请求待处理。 | Disable repeat submission. Persist request identity when the real owner supports it; do not block unrelated reading. |
| Saved | **Saved.** {object} is confirmed. | **已保存。** 已确认{对象}。 | Only after owner's successful result/readback. Offer existing open/return action, not a fabricated new object. |
| Failed save | **Save failed.** Your last saved view is unchanged. Retry when ready. | **保存失败。** 上次保存的视图未改变。可准备好后重试。 | Only for a confirmed noncommit/failure. Retain local draft. If prior state cannot be established, use uncertain. |
| Uncertain save | **Save outcome unknown.** Check the existing request before retrying. | **保存结果未知。** 重试前请检查现有请求。 | Primary action “Check request status / 检查请求状态”; keep request/object identity; prevent blind duplicate writes. |
| Corrected source | **The source revised this observation.** View the correction and prior value. | **来源修订了此观测值。** 查看修订内容及先前数值。 | Preserve revision lineage and as-of semantics from actual producer; do not fabricate a historical version. |

## Control/action contracts

| Control | Preconditions and resulting state | URL, writes and ownership | Keyboard / touch / focus / scroll |
| --- | --- | --- | --- |
| Local tab | Visible enabled tab; select corresponding panel; retain filters/selection per domain contract | Use existing domain parser if tab is URL-addressable; otherwise local UI only. Never reuse specimen query keys as production route grammar. | Tab enters selected tab. Arrow keys/Home/End move roving focus. Manual Enter/Space activates. Selected fill is neutral; focus outline distinct. Active panel has an accessible label. |
| Sort | Loaded rows and declared sortable field; comparator uses raw values, stable secondary identity and explicit absence placement | Existing view-state owner; no backend mutation. Server-sort routes retain existing pagination/cursors. | Button in a scoped column header; `aria-sort` on that header. Announce resulting order. Keep focus on the header button, not page top. |
| Filter | Apply valid domain filter; show filter summary and count/scope | Preserve existing query parsing and invalid states; no implicit saved-screen write. Option tape's complete filter set remains D08-owned. | Enter or explicit Apply, clear action and label. Updating rows does not steal focus. No-results gives recovery action. |
| Row evidence | Stable row/field/source identity; open one inspector for that exact observation | No new route unless existing owner supports addressable evidence; no write. Preserve return route/hash/scroll. | Each trigger names its row. Wide dock does not trap; narrow modal traps focus and makes background inert. The active owner handles Close/Escape. If the retiring surface owns focus, restore the connected current trigger by identity; if removed, use the named table heading and announce why. Preserve deliberate later focus elsewhere. |
| Chart values | Same dataset/version as plotted marks; expose exact period/value/unit/absence | Existing data inspector where available; ordinary native table otherwise. No duplicate independently fetched series. | Keyboard-accessible action moves focus to the values panel/tab. Touch requires no hover. Exact-value path exposes missing points too. |
| Horizontal table region | Required 2D comparison exceeds usable width | Local scroll only; avoid whole document width inflation. Preserve active row/column on inspector return. | Named region with focusable scroll container. Sticky identity column and visible scroll hint; complete-row evidence reachable without dragging to the final column. |
| Virtualized list/grid | Existing domain-specific inspector and canonical item/time keys | Preserve replay identity, selected record set, sort, CSV scope and paging. F02 does not implement a second virtualizer. | Existing Arrow/Page/Home/End/Shift/Space/Enter/Escape semantics retained. Mounted active descendant, row count/index, correct focus after recycling and screen-reader verification required. |
| Disclosure | Optional details only; expanded content belongs to the current context | No hidden mutation on expansion. Preserve source request/cache semantics if existing lazy read. | Native details/summary or equivalent accessible pattern. Enter/Space; no essential hover; expanded state announced. |
| Refresh | Real refresh callback exists; request new observation under same entity | Read only. Preserve source clocks and request generations; no global TTL added by F02. | Explicit busy state, recoverable error, no focus jump. Announce completion politely without live-region flooding. |
| Save | User identity/entitlement and real write owner valid; explicit click | D23/current owner controls payload, dedupe, request identity, commit and readback. UI follows confirmed outcome. | Pending action disabled; failure retains draft; unknown outcome directs reconciliation. Theme/region/context navigation never invokes it. |
| Language/theme/density | Explicit view preference; no domain semantic change | Preserve current preference scope until F01 defines migration. Do not add storage. HTML lab changes only in-memory UI and its own query string. | Label and selected value remain visible. Focus remains on the controlling selector. Language changes labels/format, not listing, market or Options side/exposure meaning. |
| Editorial anchor | Existing heading slug in current canonical article | Hash navigation preserves exact slug; no translated route invented. | TOC and in-text links are keyboard accessible. Heading scroll margin prevents header occlusion; sensible focus/return behavior verified in the real browser. |
| Source link | Actual source URL and permission valid | Preserve existing link destination and citation precision; external links disclose new-context behavior when used. | No icon-only unexplained link. Unavailable/restricted source has explanatory text instead of an inert link. |

## Focus, overlays and input details

The shared inspector replaces the previous shared inspector. It does not stack multiple modal contexts. A modal uses an accessible dialog name, initial focus on the close control or contextual heading, contained Tab/Shift+Tab cycling, active-owner Escape, background inertness and preserved background scroll. If the viewport crosses the dock/overlay threshold while open, retain the exact evidence identity and return target; do not silently close, change rows or reset the table. Reconcile focus/inertness once through the existing owner. Move or restore focus only when the retiring surface legitimately owns it; preserve intentional later focus elsewhere. Nested Brain/chart Escape priorities must not also retire an outer layer or activate a background shortcut.

The docked inspector is a complementary region. It may receive focus after explicit opening but must not trap users. When the closing dock legitimately owns focus, return to the still-connected current trigger by stable identity, never a different row at the old positional index. If that row is absent, focus the named table/section heading and announce why. If the user intentionally moved focus elsewhere, preserve that later focus instead of stealing it back. Preserve the table state and context without automatically scrolling a different active task. Candidate 2 captures the stable evidence key, source record and table scroll context; its historical prototype resolves a visible trigger by key after a sort/filter rerender. That prototype is not proof of the refined conditional-ownership behavior. Connected-node return, removal fallback, retained scroll and no-focus-theft transitions still need real browser/assistive-technology testing.

### Shared evidence, Brain and the focused reader

F01 owns shared-layer policy; F02 supplies the applicable anatomy and accessibility primitives. The existing Brain/D14 and host owners retain widget lifecycle, requests and exact context. For the proposed shared policy, suspend evidence presentation coherently when invoking the existing singleton, retain its evidence/return identity, and provide truthful recovery if opening fails. Evidence remains reachable but closed until the user explicitly reopens it; revalidate entity/field/period, source generation and access before showing it again. No forced reopen, queued surprise modal or new coordinator is introduced. `open()` invocation, a true opener result, readiness and mounted state are not visibility acknowledgments. Conditional `MM_BRAIN_CFG.onClose` is a focus-return hook, not an all-close event. Hiding or resizing a panel is distinct from Stop, cancellation, rollback and save confirmation. These owner-bound transitions remain specified, not executed.

Focused `/terminal` keeps its separate reader and chrome. The source reader starts at 360px, accepts a requested 300–520px width through incumbent `mm.railW`, and adapts effective fitting without overwriting that request. It does not inherit the shared 320+24 inspector geometry. D06/Terminal/Options qualify plot-specific minimums and inline/focused fallback; the proposed 640px price plot is not the shared 640px primary-container measurement.

The shared inspector's captured evidence record must not create a committed-versus-hover pin in the focused reader. Crosshair and stepping share one visual inspection cursor; AI locked selection and Intelligence event selection retain their existing owners. Presentation-only changes preserve the current valid reader context. Exact historical Ask must validate listing/market, interval, time/time basis and source/context generation before dispatch. A prepared attachment revalidates when that context changes; a dispatched request keeps its original object identity despite later cursor movement. Missing historical evidence remains unavailable. Exact accepted return URLs, picker-history restoration and complete selection/scroll/focus restoration remain separate qualifications under the [versioned F01/F02 concurrence](F01_HANDSHAKE_CANDIDATE.md).

At 400% zoom from 1280px, the target is a usable 320 CSS-pixel page. Body copy, headings, errors, actions and inspector controls must reflow. Necessary chart/table 2D interaction stays inside that component. A smaller screenshot is not proof of zoom, keyboard operation or target size.

The 44px programme target applies to important phone controls. Dense desktop controls may be smaller while meeting the applicable WCAG 2.2 target-size rule and spacing. Do not call 44px the AA minimum. Touch equivalence includes long-label disclosure and evidence access without a hover prerequisite.

Reduced-motion treatment is a meaningful static state. Do not animate numeric transitions in a way that manufactures intermediate prices. Do not auto-scroll a table or use motion as the sole update cue. Forced-color mode retains labels, outlines and shapes; semantic meaning survives loss of custom hue.

## Component state applicability and specimen coverage

| Component family | Applicable scenarios | Supporting artifact | What is still unproved |
| --- | --- | --- | --- |
| Analytical data frame | Loaded, loading, empty, partial, stale, unsupported, read error, first use | `pattern-lab.html` independent availability/freshness/coverage controls; static state sheet | Actual rendering, focus, announcement and responsive behavior |
| Access boundary | Guest, plan required, expired before send; actual expired-after-send contract above | Independent access axis, expired-after-pending transition and source contracts | Real auth roles, server omission and return URLs; no auth changes were attempted |
| Save feedback | Pending, saved, failed, uncertain | Local simulation only; no external write | D23 integration, commit/readback/dedupe and multi-tab behavior |
| Public article | Existing English article, bilingual chrome; static content/date/anchor/table patterns | Editorial specimen and sheets | Real article-template reflow, anchors and publication metadata migration |
| Virtualized inspector | Existing domain keyboard/selection behavior; source-bound retention | Actual Terminal source and this contract | Executable specimen not implemented; existing real path must be regression tested during later build |
| Domain verdict/lifecycle/count ladder | Existing domain states and counts | Retained canonical Paper boards and source contract | Domain-specific updated editable composition and independent review |

## Release verification cases

1. Read `0.00`, `—`, +1.13 pp and +33.3% with color removed; identify the comparator and missing reason.
2. With partial and stale simultaneously, inspect both clocks and confirm usable values stay associated with the same entity.
3. Use only a keyboard to select a tab, sort a table, open evidence, traverse and dismiss a modal, and return to the connected current trigger/scroll when that retiring surface owns focus. Separately move focus intentionally to another allowed task before dock closure or placement change; verify that it is not stolen. Exercise nested Escape so only the active owner acts.
4. Repeat at 320/390px, 400% zoom, EN/ZH chrome, light/dark, long labels, unknown currency and complete-row access.
5. Change the instrument during an outstanding read; old data must not be relabeled. Preserve existing generation/race guards.
6. Filter away the current evidence row. With focus still owned by the closing inspector, close it and verify the named connected, focusable, visible fallback and applicable announcement. Repeat after intentionally moving focus outside the inspector; closing it must preserve that focus and must not force fallback focus or scroll. In both cases, retain the evidence identity/invalidation rules and avoid a second inspector.
7. Interrupt a save after sending. Retain request identity and reconcile; never claim failed without confirmation or emit a duplicate blind retry.
8. Open a focused Terminal route; no additional investor shell or duplicate Brain instance appears.
9. Compare chart values against displayed marks, including a missing middle observation, an actual zero and a source revision.
10. Confirm Options side/exposure colors do not flip with language or directional color preference, while the explicit price-direction convention remains source-owned.

All cases are acceptance requirements unless explicitly recorded as completed evidence in [VERIFICATION.md](VERIFICATION.md). They are not asserted as passing from code inspection alone.

## Candidate 2 model and integration boundary

The supporting reference has separate `availability`, `freshness`, `coverage`, `access` and `write` fields. `SAVE_START`, `SAVE_RESULT` and `SAVE_CHECK` only change the write axis. An access change after pending changes the write outcome to uncertain. A read retry changes availability only; it cannot assert a newer source clock or repaired coverage without a corresponding read result. The fixture's “Response complete” harness setting refers to delivery of its declared example records, not a guarantee that every optional field is known; individual missing/unsupported fields keep their labels.

The combined case is available through `?consumer=macro&availability=loaded&freshness=stale&coverage=partial&access=member&write=pending`. Saving from a loaded, stale, partial state retains both read notices after the local success simulation. Loading, empty and unsupported availability also remain unchanged by save transitions. No account service is called.

The source model was checked across 480 state combinations and 3,360 write/access transitions. These checks establish read-state invariance for the enumerated pure transitions; they do not establish DOM behavior, focus, real service authority, or end-to-end preservation.

Access recovery remains a host integration requirement. The reference does not invent a sign-in or plan URL for its fictional EXM entity. F01/D25 and each route owner must bind actual return URLs and access destinations; D23 must bind real request identity, confirmation and reconciliation. The decorative shell context carries no fabricated entity-navigation link. Full Company statement/period/transcript controls, Options share/export/saved-screen flows, Macro regime/risk/calendar paths and the existing virtualized inspector remain open qualification cases, not passing paths inferred from painted controls.

The public article's retained English content has `lang="en"`; shared bilingual chrome and component demonstrations retain their own language. A translated article route is not created.
