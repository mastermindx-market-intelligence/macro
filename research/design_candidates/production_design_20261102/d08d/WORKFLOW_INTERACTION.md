# Workflow, controls and state contract

This is a future implementation contract. Existing behavior is documented in [SOURCE_EVIDENCE.md](SOURCE_EVIDENCE.md); no action below is claimed to have been implemented by D08D. Consume D08-OPTIONS/1.0.0 without adding route parameters or a second persistence owner.

## Complete journey

### 1. Start at the actual research selection

From D06's chart or D08's Options view, expose **Open replay / 打开回放** beside a selected historical event or the existing tools menu. The sender supplies the selected listing/instrument, dataset intent, original route bytes and the qualified restoration context it owns. An equity symbol alone must not become ES, NQ, SPX or NDX through heuristic mapping. For unsupported regional/listing data, keep the original identity and explain the unsupported dataset. Do not default a failed cross-listing handoff to NVDA or a US proxy.

If a chart offers both equity and futures context, label the choice **Equity observations · IEX / 股票观测 · IEX** or **Futures · ES/SPX, NQ/NDX / 期货 · ES/SPX、NQ/NDX**. A futures contract is source-selected; the current route only selects its supported pair. Do not imply that the expiry lens selects a futures contract month.

The sender validates the destination using the incumbent parser. It captures transient origin state before leaving and does not save or modify a research plan. D08/D06 must supply the implementation protocol: the semantic interface is not evidence of a live codec. A direct visitor receives a named **Options workspace / 期权工作区** fallback, not a false “Return to your chart” claim.

The sender also supplies D08's required `requestedSelection`: the selected historical event and its known native fields, not just the symbol. Resolve the initial reader state explicitly:

| Qualified incoming selection | Initial replay behavior |
| --- | --- |
| Futures cutoff with supported instrument/pair and complete validated query | Serialize only the existing grammar including `at`; select the greatest admitted matching cutoff at or before the request. Display request and effective cutoff separately. |
| Exact IEX artifact hash + ordinal + copied native session/sequence/time | If the currently admitted artifact matches and every copied field cross-checks, select that position. If not, state that the exact observation is unavailable; never silently use that ordinal in other bytes. |
| Origin supplies only an equity historical time | Retain the requested instant visibly. Time alone does not identify an exact IEX observation. The loaded-observation picker may list matching candidates; the researcher commits one. No new archive lookup endpoint or URL parameter is implied. |
| No qualified equity selection resolver exists at entry | The existing latest-retained default may open only with explicit “Requested [time]; viewing latest retained [different time] / 请求 [时刻]；当前显示最新保留观测 [另一时刻]” context and a Choose observation action. Do not claim the origin's observation was located. |
| Direct entry without a historical request | Label the actual latest retained/published selection and its source basis; use the named fallback. No origin selection is fabricated. |

An unsupported dataset or absent retained window is resolved before offering an apparently successful replay. Requested selection and exact return context remain independent: changing the replay cursor never changes the origin's selected event.

### 2. Resolve access without losing context

Keep the requested instrument, dataset and return action visible while checking access. Never show protected stale values from the last account. Account authentication, subscription access, distribution rights and historical-window availability are separate facts, although current endpoints sometimes compress them. Evaluate the current trusted result, then choose the corresponding copy in the state table below. An access refusal must not trigger a background synthetic source or a broader endpoint query.

Sign-in and plan selection use the existing account/subscription owner. This specification does not invent a checkout or callback parameter. On return, revalidate the intended selection and origin; if the current owner cannot preserve it, state that explicitly and offer the named fallback. Do not promise an exact round trip through authentication until it is tested.

### 3. Orient within the loaded historical data

The page heading is **Futures replay / 期货回放** or **Equity replay / 股票回放**. It is followed by the exact pair/contract or equity listing, a persistent **Historical / 历史** indicator when applicable, venue/unit scope and the selected absolute time. Keep the historical indicator beside the cursor even when the page header scrolls away.

Futures show source basis (`historical`, `delayed`, `realtime`) independently of selection mode (`latest published` or explicit cutoff). Explicit replay selection never becomes live because its source once had real-time basis. Equity always says **IEX only · historical archive · shares / 仅 IEX · 历史档案 · 股**. The observed default latest sample is called **Latest retained observation / 最新保留观测**.

Show three separate bounds when known: **Available in this publication**, **Loaded**, and **Selected observation**. Never turn the current publication's cutoff list or the archive's retained sample array into an assertion of all available historical dates. Where there is no catalog, the heading is **Retained observations / 保留观测** and a wider date selector is absent. Unknown bounds display “Not supplied / 未提供”.

### 4. Select an actual observation

Futures use the existing published cutoff choices. A requested `at` between cutoffs resolves through the incumbent greatest-valid-cutoff-at-or-before rule; show both requested and selected times. Changing interval or row grouping keeps the validated request and re-resolves the available view. If that exact variant is missing, show missing-window; do not silently switch to a different interval. Pair change resets cutoff and expiry as the current owner does, with an explicit “Selection changed to latest available for NQ” message and no saved-state write.

Equity uses the retained observation slider plus proposed **Previous / 上一个** and **Next / 下一个** buttons that step the same native array. Display `137 of 480`, precise market time, and whether the selected sample is observed or withheld. Sample spacing is observation order; it does not imply equal elapsed time. Pointer movement may preview a position, but evidence commits only after the selection is applied. Keyboard arrows move one sample, Home/End move to first/last retained sample, and the accessible value includes ordinal, absolute time, venue and coverage.

**Choose observation / 选择观测** is a visible desktop and mobile action. It can directly select any position in the complete retained array, including observations outside the current chart's last-60 prefix. The picker lists ordinal, precise absolute market time and observed/withheld qualification; repeated native tuples remain distinguishable by artifact position. Direct ordinal input and a bounded search within the loaded array are proposed affordances, not historical-date retrieval. Search results never silently choose a later timestamp. Highlighting is preview; Select commits once, Cancel/Escape leaves the prior committed selection and inspector intact. A changed artifact invalidates an open picker unless the user explicitly opens and reselects within that new publication.

The incumbent has no autoplay, speed engine or historical-date API. Future **Step through observations** is a labeled proposal, not a retained feature or this candidate's active control. If later admitted, use the existing selection reducer and describe speed as steps/second, pause on a gap, hidden tab, access change or evidence open, and never synthesize intervening observations. No “1× market time” promise is admitted here.

### 5. Inspect evidence at the committed selection

**Evidence / 证据** opens one inspector tied to an immutable snapshot of the selected identity. Desktop docks only when the primary content remains usable; narrower widths use the shared modal pattern. It does not fetch a newer artifact and silently substitute it for the selected one. If a refresh produces a different artifact, require an explicit **Open latest publication / 打开最新发布** action. Retain an evidence view of the old loaded artifact while access remains valid; if that artifact is no longer available, say exact reconstruction is unavailable.

“Immutable snapshot” means the evidence never mutates its identity underneath a committed view; it does not pin the inspector to a different ordinary selection. Committing observation B while a dock is open on A atomically replaces the heading, chart, totals, coverage and inspector with B from the same artifact. Preview never partially replaces the committed fields. While a different publication awaits explicit acceptance, the whole old view remains coherent, including its chart and totals. On **Open latest publication**, clear the old picker/preview, use the current reader's explicit latest-retained default (or re-resolve the still-valid futures request), announce the new artifact and effective selection, and update all surfaces together. Do not carry an array index across artifact bytes. Account/access invalidation immediately clears protected content even while this transition is pending.

The summary first states the observation and interpretation. Disclosure exposes exact native fields, clocks, coverage, distribution qualification and source identity. Futures evidence includes pair, contract, session, definition, requested/effective cutoff, source/publication/freshness clocks, frame coverage, unknown-side quantity and any GEX qualification. Equity includes artifact hash, source hash, exact ordinal/native fields, acquisition time, served time, retained-level limits and correction/accounting qualifications. Long identifiers wrap or use an accessible copy control; no truncation may be the only available value.

Opening evidence does not save it. **Save evidence / 保存证据** is absent as an active control until D23's admitted save and reconciliation interface exists. A build may show neutral explanatory text “Saving evidence is not available in this view / 此视图暂不支持保存证据” with a reachable existing research destination, but not a button that falsely succeeds. The current design does not route into the dev plan harness.

### 6. Return exactly, or explain the fallback

The origin action is always available above the workspace and within the mobile evidence sheet. A qualified label is specific: **Return to NVDA chart / 返回 NVDA 图表** or **Return to Options · selected row / 返回期权 · 所选行**. The destination owner validates the envelope, access, source/session/cohort fingerprint and restore capabilities before claiming success.

Restoration covers route bytes, view, selected row, filters, source selection, scroll anchor and focus target. Preserve the originating listing exactly; a company alias is insufficient. Use the existing owner history state without overwriting Next/framework markers or `mmxCompanySearch`. Replace the current `replaceState(null, ...)` behavior only through that owner's integrated codec; do not put full source envelopes or credentials into history.

Browser Back is allowed only when the navigation owner can prove the immediately relevant origin entry. `history.length` alone is insufficient. Existing cross-Macro navigation continues to use its incumbent allowlist and embedded close path. The new replay transient envelope remains same-origin as D08 specifies; it is not authority to widen cross-origin return privileges.

When a target row disappeared, a cohort changed, a new tab has no context, or reload cannot recover full state, navigate only to the validated named fallback and show **Original selection is no longer available. Opened Options instead. / 原选择已不可用，已打开期权工作区。** Do not claim “Restored”. A direct-link equity URL currently cannot encode the exact sample. Label share/copy behavior accordingly and gate durable reconstruction on D23 and artifact retrieval ownership.

## Control contract

| Control | Behavior and route effects | Focus / cancellation / data boundary |
| --- | --- | --- |
| Instrument/pair | Current validated choices only; futures pair resets cutoff+expiry; equity symbol resets sample to latest | Announce new identity; abort old request; never silently change origin identity |
| Futures interval / row step | `interval=1|5`; `rows=1|4|8`, labeled 0.25/1.00/2.00 price points | Stage in mobile controls sheet; Apply once; Cancel preserves prior committed query |
| Expiry lens | All / source-session 0DTE / excluding source-session 0DTE / valid source date | Explain source-session basis and all-expiry landmark exception; no contract-month claim |
| Ratio / basis | Reuse projection method; retain exact input values and units | Does not change market timestamps or transform GEX into native futures gamma |
| Depth / footprint / executions | Presentation-only tabs; same selected observation | Arrow-key tab navigation; tab panel has heading and accessible table alternative |
| GEX / CVD / price zoom | Retain source visibility toggles and 1×/2× price zoom | Zoom changes the view; no source recalculation/rounding or future sample leakage |
| Replay selection | Futures published cutoff / IEX retained sample | Arrow buttons and picker provide non-drag path; no timer loop in historical mode |
| Choose observation | Direct choice from the entire currently retained array; ordinal, exact time and coverage | Preview/Select/Cancel are explicit; repeated tuples retain artifact position; no archive retrieval or route expansion |
| Refresh publication | Explicit read; historical selection is not silently rebound by index | Proposed preserve-or-explain transition; new publication notification, no automatic overwrite of open evidence |
| Evidence open/close | Same committed selection, no source mutation | Close/Escape returns to invoking control if still present; else replay heading |
| Source detail | Show exact values and qualifications | Safe wrapping, readable text alternative, source links marked external |
| Weekly positioning | Opens separate context below chart | Own report date and retrieval time; cannot be added to cursor evidence |
| Return | Validated original state or named fallback | Restore exact focus/scroll only after target data is ready; otherwise explain lost target |
| Future D23 save | Only admitted endpoint/receipt/readback; no active mock success | Pending disables duplicate submission; uncertain effect reconciles original operation, never blind retry |

## State and copy matrix

The state names below are presentation concepts, not a new endpoint schema. Preserve the incumbent typed outcome and reason; an unrecognized refusal remains a general unavailable state. Access state always outranks an old data response.

| State / trusted evidence | English copy and action | 中文文案与操作 |
| --- | --- | --- |
| Checking access / no trusted answer yet | “Checking replay access…” Keep instrument and Return. No protected values. | “正在检查回放权限…” 保留品种和返回入口。 |
| Guest / actual authentication result | “Sign in to open historical replay.” Existing Sign in; Return. | “登录后可打开历史回放。” 登录；返回。 |
| Plan required / verified account feature result | “Your current plan does not include this replay view.” View plans; Return. No promise of available history after upgrade. | “当前套餐不包含此回放视图。” 查看套餐；返回。不承诺升级后一定有历史数据。 |
| Access unverified / generic access_required | “Replay access could not be confirmed. Previously loaded market data has been cleared.” Check access; Return. | “无法确认回放权限。已清除先前加载的市场数据。” 检查权限；返回。 |
| Distribution withheld / source_restricted or explicit admission evidence | “This source is not cleared for subscriber display.” Source details; Return. No upgrade CTA. | “该来源尚未获准向订阅者展示。” 来源详情；返回。 |
| Unsupported instrument or dataset / explicit validator/capability result | “Replay is not available for this instrument in the selected dataset.” Choose a supported instrument; preserve requested identity. | “所选数据集不支持该品种回放。” 选择支持的品种；保留原请求身份。 |
| No published feed / feed_not_published | “No replay archive has been published for NVDA here.” Refresh; Return. Do not claim no historical trades existed. | “此处尚未发布 NVDA 的回放档案。” 刷新；返回。 |
| Missing retained window / no_replay_frame | “No retained observation covers this selection.” Show actual retained bounds; choose observation; Return. | “没有保留观测覆盖此选择。” 显示实际保留范围；选择观测；返回。 |
| Loading permitted publication | “Reading the published archive…” Reserved chart geometry, no fabricated prices. | “正在读取已发布档案…” 保留图表空间，不显示虚构价格。 |
| Empty valid futures interval | “No captured executions in this interval.” Keep independently observed depth; no candle/OHLC fabrication. | “本时段未捕获成交。” 保留独立观测深度，不虚构蜡烛价格。 |
| Book gap / typed IEX reason | “Order-chain coverage is incomplete. The book is withheld.” Show gap and dashes; eligible captured executions remain separately qualified. | “订单链覆盖不完整，暂不显示订单簿。” 显示缺口与破折号，成交数据单独标注范围。 |
| Partial capture / retention truncation | “Partial captured window.” “Earlier observations were omitted by the retention limit.” Evidence explains bounds. | “仅部分捕获时段。” “保留上限已省略较早观测。” 证据中说明范围。 |
| Stale latest source / freshUntil expired | “The latest source is out of date.” Clear current claims; Refresh. Historical age is not this error. | “最新来源已过期。” 清除当前行情声明；刷新。历史数据较旧不等于此错误。 |
| Invalid source / parse or identity failure | “The publication did not pass its source checks. Data is withheld.” Retry only after a fresh allowed read; Return. | “发布数据未通过来源检查，暂不显示。” 合法重新读取；返回。 |
| Transient/network failure | “Replay could not load. Your selection is kept.” Retry; Return. No fabricated failure classification. | “回放加载失败，已保留您的选择。” 重试；返回。 |
| Rate limited / trusted 429 outcome | “Replay is temporarily rate limited.” Manual retry after supplied retry time, if any; no inferred countdown. | “回放暂受请求频率限制。” 有明确时间时显示；不虚构倒计时。 |
| New artifact after refresh | “A different publication is available. Your inspected observation has not changed.” Open latest publication. | “有不同的发布版本可用。正在查看的观测未改变。” 打开最新发布。 |
| Exact evidence cannot be reconstructed | “This exact archived observation is no longer available here.” Keep evidence identity; named fallback. | “此处已无法重建这一精确历史观测。” 保留证据身份；提供明确后备入口。 |
| Return context lost | “The original selection could not be restored.” Open Options / Open chart, accurately named. | “无法恢复原选择。” 打开期权 / 打开图表，准确命名。 |
| Future save pending / failed / uncertain | “Saving…” / “Save failed; nothing confirmed.” / “Save outcome unknown; checking the original request.” Receipt required for “Saved”. | “正在保存…” / “保存失败，尚未确认成功。” / “保存结果未知，正在核对原请求。” 只有回执确认后显示“已保存”。 |

## Keyboard, touch, motion and focus

Every analytical view has an adjacent, persistent encoding key. Futures depth means the combined `bidMean + askMean` resting quantity in contracts; its heat quantity bands must not be relabeled as execution-side colors. Equity depth names resting bid/ask shares and its logarithmic scale relative to the maximum retained level quantity in the displayed selected-prefix books. Footprint numbers explicitly read **Sell | Buy**, with unknown-side quantity separately marked; execution profiles use the same native classifications. Price up/down remains a different meaning. Keys also name selected-column/observation marks and unavailable/gap hatching. Exact cell readouts and the accessible table identify price, interval/sample, units, quantity and coverage; color or position alone is insufficient.

All primary actions use native semantic controls and at least a 44px house touch target. At 320 CSS pixels and 400% zoom, controls reflow and the page has no global horizontal scrolling. Dense depth/footprint tables may have a named, keyboard-scrollable contained region with a visible scroll affordance. The selected timestamp and units stay outside that region.

Use one overlay at a time. At modal widths, opening Evidence closes the controls sheet only after staged changes are either applied or canceled explicitly. Trap focus only in a modal, make the background inert, expose its heading and restore focus conditionally. A docked inspector does not trap focus. A chart pointer tooltip is never the sole path to evidence; select an observation through the picker or table and use Evidence.

Respect reduced motion: static meaningful state, no autoplay or numeric tween. Routine transitions may use F02's 120ms target; reduced motion removes the transition. Do not animate a gap as if data had arrived. Loading can use a quiet status label and reserved geometry without a moving market-like chart. Language switching uses the incumbent provider, preserves native identifiers/time units, and does not invert buy/sell colors. Price direction follows the existing convention owner independently of language.
