# Workflow and state contract

## Complete normal journey

**J1: Scan → unusual observation → investigation → evidence → exact return.**

1. Open retained Tape, Desk or Screener. Read source session/population and current rank. Apply a view-specific predicate. The result count means matching loaded source rows, not the whole market.
2. Choose **Inspect observation** on a specific row. Preserve the source row/reference, source family/grain, clocks, rank reason and existing origin view state. The former root-filter behavior survives as **Filter to NVDA**, a separate action.
3. Inspect the object first: exact identity if supplied, aggregate/event grain, premium/contracts/print count, estimated side and unusual predicate. Unknown fields remain “Not supplied.” No selection implicitly saves or creates a plan.
4. Choose **Investigate contract** only when the existing validator and receiver admit that exact source identity. Otherwise offer **Open underlying context** when listing identity is qualified, with explicit root-only copy. An ambiguous listing permits source evidence but no automatic cross-source join.
5. D08B resolves its actual dated book. It displays the origin observation separately from the book's own session, availability, spot/quote and OI clocks. If the requested contract is absent, the user may independently choose a valid book row; the UI never fills origin gaps from that later row.
6. Open **Source evidence**. Inspect exact source/schema/record/digest when supplied, population/coverage, aggregation/classification and temporal limits. A historical cutoff requires source availability at/before the cutoff; a later book remains labeled later context.
7. Choose **Back to [origin view]**. Restore original filters, sort, source-session intent, selected-row reference, scroll anchor and focus if still qualified. If the row aged out or access changed, preserve only lawful context and explain the exact limitation.

**J2: Change view/filter/root/session safely.** View changes preserve only semantically valid filters. If switching into OI/hot, clear unsupported group filtering with visible copy and retain the prior view's state for return. Session/root changes start a new qualified read generation. Old results never appear under a new heading. Apply a new window explicitly when the old source has expired.

**J3: Save and revisit.** Local Tape “Save screen” preserves filters only in the existing browser-local owner. Shared URLs carry supported filter grammar, not protected records or a fixed market snapshot. Durable research requires D23/Investigation admission and exact receipt/readback; absent admission remains draft-only. Watch activation is separate. On revisit show original evidence and new observation separately.

~~~mermaid
flowchart TD
  S["Scan with population and source session"] --> O["Inspect original observation"]
  O --> Q{"Identity qualifies?"}
  Q -->|Exact contract| B["D08B dated investigation"]
  Q -->|Root only| U["Labeled underlying context"]
  Q -->|Ambiguous| E["Source evidence and reason"]
  U --> B
  B --> E
  E --> R{"Origin still recoverable?"}
  R -->|Yes| X["Restore scan, row and focus"]
  R -->|No| F["Named origin with absence or access state"]
~~~

## Controls, route and effect semantics

| Control | Preconditions / result | Route and write effect | Focus / recovery |
| --- | --- | --- | --- |
| Category/local view | Existing D08 key; named view visible even when source unavailable | Existing parser and aliases; no durable write | Selected tab has aria-selected; arrow-key behavior matches Tabs; focus does not jump to data on every load |
| Filter sheet / Apply | Explicit draft controls, validation and matching count basis | Apply local filters atomically; no persisted screen update | Closing without Apply discards sheet draft, keeps applied scan; Reset explicitly resets draft and Apply confirms |
| Sort heading | Valid field for selected family | Same selector array drives table/export; nullable values last in proposed behavior | One aria-sort; numeric direction and absolute-rank semantics announced |
| Inspect observation | Readable source row/reference | Read-only selection; no URL extension or save | Row contains a named button/link, Enter/Space works; row is not only a clickable tr |
| Filter to exact root | User explicitly chooses root filter | Existing supported filter codec; origin view retained | Focus filter/results heading; clear chip names root |
| Investigate contract | Exact tuple, terms, uniqueness and receiver source qualification | D08 A→B; receiver resolves book | Focus receiving selected-object heading; decline leaves origin evidence usable |
| Open underlying context | Exact listing/root, contract not uniquely supplied | D08 A→B root-only scope, same origin | Announce scope change; no implied matched contract |
| Source evidence | Authorized observation or safe reference | One shared contextual inspector; read-only | Dock nonmodal; overlay named/inert/trapped; close restores owned trigger |
| Compare shortlisted contracts |2–4 qualified existing pins | Existing shortlist/Plan boundaries, no pricing/order side effect | Show source/list/session/terms per column; missing evidence visible |
| Show N new observations | Buffered source update available | Replace displayed collection explicitly; keep selection reference | Announce changed count once; no automatic reorder under keyboard focus |
| Local Save screen / Share | Valid existing v1 Tape codec | Existing local store / supported URL only | “Saved on this browser”; show local quota/storage failure; no false synced claim |
| Durable Save research | Existing D23 owner admission, auth, reconciliation identity | Explicit owner operation only | Readback exact object/revision before Saved; uncertain outcome stays same intent |
| Activate watch | Separately admitted explicit action | Existing alerts owner, never coupled to save/navigation | Independent receipt; avoid duplicate submission |
| Back/Close | Valid origin history context, revalidated access | Restore same-origin context; no save | Restore row action if present; otherwise results heading + absence notice |

## History, focus and source lifetime

Preserve host history state; current null replacement is a baseline integration defect, not a pattern to copy. Merge only owner-approved transient return metadata within the existing mechanism. Do not append return/origin keys to closed futures/equity grammars. Futures already admits its validated integer at cutoff; preserve that exact meaning and do not infer the same parameter is accepted by another reader. Public fragment/query parsing remains its incumbent parser; #ticker?t=AAPL and legacy forms keep their meaning.

Return context contains safe references, validated origin, named fallback, filter/sort/view/session intent and focus/scroll anchors. It never contains credentials, protected source rows, durable-write intent or an unvalidated external URL. Direct entry/new tab/reload without origin produces a clearly named fallback; it does not promise restoration that was not retained. Cross-host public→native navigation preserves only what the existing validated entry codec admits.

Use identity references, not row number or nearest timestamp. On return, reapply filters, wait for bounded result materialization, restore the anchor, then focus the selected action without scrolling twice. If the row is absent, focus the origin results heading and announce the original reference is outside the available window. Source corrections and denied access may prevent original-byte recovery. Do not silently select a lookalike.

When an overlay closes, restore focus only if that retiring surface still owns focus and the trigger remains valid. Respect intentional later focus and existing Brain/search/chart layer arbitration. Escape closes the top applicable surface; evidence never deletes or duplicates the Brain singleton. Resizing dock↔overlay preserves one selected object and one mounted inspector while reconciling trap/inert state.

## State matrix

All proposed states below need final Paper and browser evidence after the named gates. “Normal” does not imply current production success. The short Chinese copy is specification input for the incumbent localization owner, with exact IDs/units untouched.

| ID / condition | English visible copy / next step | 中文文案 | Data, action and focus rule |
| --- | --- | --- | --- |
| S01 loaded | “2,000 qualifying events · Session2026-10-30” / Inspect | “2,000条符合条件的事件 · 来源交易日2026-10-30” | Example based on observed baseline; use actual source count/session |
| S02 initial load | “Reading the source snapshot…” | “正在读取来源快照…” | Stable layout skeleton; no0 values; status once; focus stays at control |
| S03 filter empty | “No events match these filters.” / Clear filters | “没有符合这些筛选条件的事件。” | Source has rows; preserve predicates and source receipt |
| S04 source observed empty | “No qualifying observations in this source window.” / View coverage | “此来源窗口内没有符合条件的观测。” | Source-confirmed empty, never whole-market zero |
| S05 source absent | “OI snapshot has not been published for this session.” / Source details | “此交易日尚未发布持仓快照。” | Only after actual absence outcome; unavailable preset remains discoverable |
| S06 partial | “Flow available; chain heat unavailable.” / Inspect flow | “资金流可用；合约热度暂不可用。” | Independent module failure; do not blank unrelated data |
| S07 old retained source | “Retained snapshot · Source session2026-10-30” / Check source | “保留的快照 · 来源交易日2026-10-30” | Show actual source age, no promise of next update |
| S08 refresh failed | “Could not refresh. Showing the last read.” / Retry read | “刷新失败，正在显示上次读取的数据。” | Same authorized object only; bounded existing retry, no new loop |
| S09 unavailable transport | “The source could not be reached.” / Retry | “暂时无法连接来源。” | Not empty, not absence, no protected fallback across changed scope |
| S10 denied/plan required | “This options view requires access.” / Existing access action | “查看此期权页面需要相应权限。” | Server/API result authoritative; stop protected subscriptions |
| S11 access unverified | “We could not verify access.” / Try again | “暂时无法验证访问权限。” |503/uncertainty is not a subscription upsell or grant |
| S12 expired session | “Your session has expired.” / Sign in through existing flow | “登录已过期。” | Clear protected values; keep permitted return context only |
| S13 unsupported market | “Options coverage is not available for this listing.” | “此上市证券暂无期权数据覆盖。” | No US data relabeled as CN/HK/CA/International |
| S14 ambiguous identity | “A unique contract was not supplied.” / Source evidence | “来源未提供可唯一识别的合约。” | No synthetic ID/tuple; root context only if separately qualified |
| S15 missing field | “Not supplied” / Definition | “来源未提供” | Null/NaN distinct from0; no numeric ranking as real0 |
| S16 source corrected | “This source has a newer correction.” / Compare references | “此来源已有更新的更正版本。” | Original reference preserved; new bytes explicitly separate |
| S17 book after cutoff | “This book became available after the observation.” | “此合约簿在该观测之后才可用。” | Later context, not evidence known at event time |
| S18 original aged out | “Original observation is outside this window.” / Return to filters | “原始观测已不在此窗口内。” | No nearest-row replacement; focus origin heading |
| S19 original bytes missing | “Original source bytes are unavailable.” / View current source | “原始来源数据已不可获取。” | Retained reference≠original-byte recovery |
| S20 buffered update | “12 new observations” / Show updates | “有12条新观测” | Count from actual update; preserve focus and frozen selection |
| S21 changed request | “Reading NVDA…” | “正在读取NVDA…” | Retire SPY generation; late SPY response ignored |
| S22 invalid link | “This view link is not supported.” / Back to Tape | “此视图链接不受支持。” | Existing parser fails closed; no guessed cursor/query rewrite |
| S23 first use | “Choose a view or inspect an observation.” / Optional guide | “选择视图或查看观测详情。” | Tutorial optional, close/revisit; no blocked research prerequisite |
| S24 local saved | “Screen saved on this browser.” | “筛选视图已保存在此浏览器。” | Filter preference only, no research/sync/snapshot promise |
| S25 local save failure | “Could not save this screen.” / Retry after resolution | “无法保存此筛选视图。” | Distinguish quota20, invalid codec and unavailable storage |
| S26 draft-only | “Draft only · research save is not connected.” | “仅草稿 · 尚未接通研究保存功能。” | No invented endpoint or receipt; keep editing locally as current owner permits |
| S27 save pending/saved | “Saving…” then “Saved · revision…” only after readback | “正在保存…” / “已保存 · 版本…” | Button disabled for same intent; receipt exact owner/object/revision |
| S28 definite rejection | “Save was not accepted.” / Resolve stated cause | “保存请求未被接受。” | Show owner reason; no automatic resubmission |
| S29 unknown outcome | “Save outcome is not confirmed.” / Check status | “尚未确认保存结果。” | Reconcile same operation; no new identity/send/failover |
| S30 watch separate | “Saved. Watch is off.” / Activate watch | “已保存，监测尚未启用。” | Only if save actually proven; activation separate authority/receipt |
| S31 invalid statistics | “This snapshot failed source validation.” / Source details | “此快照未通过来源校验。” | No partial arithmetic presented as full valid snapshot |
| S32 valid statistics without premium | “Qualified premium unavailable ·0%coverage” | “有效权利金合计不可用 · 覆盖率0%” | Counts may remain useful; null premium is not$0 |
| S33 rate limited | “The source is limiting requests.” / Existing retry timing | “来源正在限制请求频率。” | Respect actual retry instruction; do not poll around limit |
| S34 source conflict | “Sources disagree on this identity/date.” / Inspect both | “来源的标的身份或日期存在冲突。” | No merged “best” value; qualification blocks dependent action |

Live trading/order/position success states are **not applicable**: this slice has no trade execution authority. Operator Issue Desk retains its own research-confirmation states; it is not simulated as an investor success state.
