# Feature retention ledger

This ledger is a design artifact, not a runtime registry. Baselines refer to the audited Terminal pin in [SOURCE_EVIDENCE.md](SOURCE_EVIDENCE.md). New functionality is explicitly called proposed or blocked. No feature is removed. `BLOCKED_DATA` includes an unavailable owner contract/admission as well as data availability; its exact cause is stated.

**52 entries:** RETAIN 25 · IMPROVE 21 · RELOCATE 1 · BLOCKED_DATA 5. Reviewer disposition remains pending unless individually recorded in [REVIEW_RETURN.md](REVIEW_RETURN.md).

| ID | Capability / baseline | Disposition | Reachable successor / reason | Dependency |
| --- | --- | --- | --- | --- |
| F01 | ES/SPX and NQ/NDX identity; named futures contract — FuturesRequest + transport | **RETAIN** | Replay identity header / evidence. Pair controls never substitute SPY/QQQ; source owns active contract | Terminal/source owner |
| F02 | Strict futures query including duplicates and unknown keys — futuresRequest.ts | **RETAIN** | Existing parser at page/API boundaries. No return keys, silent normalization or arbitrary date API | D08 / Terminal |
| F03 | 1/5-minute interval and 1/4/8-tick row grouping — FuturesWorkspaceView | **RETAIN** | Controls disclosure + summary. 0.25 tick → 0.25/1.00/2.00 points; variant availability explicit | Terminal |
| F04 | All, source-session zero/ex-zero and date expiry lenses — FuturesWorkspaceView + source join | **IMPROVE** | Controls; qualifier beside exposure. Separate expiry lens from futures contract selection and source session from intraday tradability | D08B |
| F05 | Ratio/basis index-to-futures mapping — futuresGexProjection | **RETAIN** | Controls and evidence. Keep exact method, quote clocks, skew and original units | D08B / source |
| F06 | Depth with displayed-order coverage and gaps — FuturesMicrostructureChart | **IMPROVE** | Primary chart + accessible depth table. Preserve observed depth on no-trade intervals; missing depth is a marked gap | Terminal |
| F07 | Footprint buy/sell, unknown side, imbalances — FuturesMicrostructureChart | **RETAIN** | Primary view tab + contained table. Do not label resting liquidity as executed volume; unknown side stays explicit | Terminal |
| F08 | Captured volume and known-side delta — FuturesWorkspaceView | **IMPROVE** | Two primary statistics plus coverage detail. Loaded-window basis; qualify partial capture next to values | Terminal |
| F09 | CVD known-side and incomplete total semantics — futuresWorkspace / chart | **RETAIN** | Optional lower plot and evidence. Preserve baseline, null full-CVD, unknown-side accounting and gaps | Terminal |
| F10 | Price zoom 1×/2× and responsive visible footprint count — FuturesMicrostructureChart | **RETAIN** | Display controls; chart footer. No source quantity changes; report narrower visible range | Terminal |
| F11 | GEX show/hide, mapped strike rows and scale legend — FuturesMicrostructureChart + workspace | **RETAIN** | Exposure layer disclosure and evidence table. USD millions per 1% index move, estimate; no native futures-gamma claim | D08B |
| F12 | Call wall, put wall, gamma flip / all-expiry scope — futuresGexLevels / chart | **RETAIN** | Chart labels and accessible key-level table. Preserve source-owned values, mapped precision and collision layout | D08B |
| F13 | Observed captured-window point of control — futuresVolumeProfile / chart | **RETAIN** | Footprint and evidence. Observed executions only; not exchange-wide/session POC | Terminal |
| F14 | Cash-closed or unavailable gamma with valid futures flow — source join + UI copy | **IMPROVE** | Layer-specific unavailable notice. Withhold only unqualified gamma, retain valid depth/executions | D08B / source |
| F15 | Latest / historical cutoff selector — workspace + source join | **IMPROVE** | Prominent replay strip. Requested and effective time; available versus loaded bounds | D08D / source |
| F16 | Historical no-poll; latest bounded polling, hidden abort, owner key — useFuturesWorkspace | **RETAIN** | Existing reader hook. 5s latest / 15s transient; no overlapping reader or duplicate engine | Terminal |
| F17 | 403/401 clearing, terminal request/rate/source restrictions — useFuturesWorkspace + API | **RETAIN** | Access/status presentation. No stale protected response after account change; no blind retry | Access / source |
| F18 | Source-as-of, publication, fresh-until and definition checks — futuresTransport | **IMPROVE** | Evidence clocks and freshness strip. Age of archive is distinct from stale latest source | Terminal / source |
| F19 | Weekly COT positions and OI changes — FuturesCotPanel + futuresCot | **RELOCATE** | Below-chart Weekly positioning disclosure. Retain four groups and links; separately dated context with replayEligible:false | Existing CFTC reader |
| F20 | CFTC source date, retrieved time and null comparison — futuresCot | **RETAIN** | Weekly positioning details. Weekly context is excluded from selected-observation evidence | Existing CFTC reader |
| F21 | EN/ZH via one language provider — futuresUiCopy | **RETAIN** | Shared language control and local copy. No second locale store or language-driven side-color swap | F01 / Terminal |
| F22 | Source distribution versus customer plan gate — Hub + futures API | **IMPROVE** | Specific refusal state when established. Subscriber feature is not a CME distribution license | Publisher / access |
| E01 | One exact uppercase equity symbol; default NVDA for direct entry — equity replay page | **RETAIN** | Existing route parser. No extra cursor, origin or session query; incoming unsupported symbols do not silently default | D08 / Terminal |
| E02 | NVDA/SPY/QQQ plus exact incoming symbol choices — IexDepthReplayView | **RETAIN** | Instrument picker. Presence in picker does not assert an admitted archive | Terminal / publisher |
| E03 | IEX venue-only historical share scope — IEX reader / view | **IMPROVE** | Permanent identity line. No consolidated NBBO, live CME, options-gamma or trading-edge implication | D08D |
| E04 | Observed snapshot slider and latest-retained behavior — IexDepthReplayView | **IMPROVE** | Replay strip with proposed previous/next and full retained-array picker. Exact entry resolution, commit/cancel and coherent inspector follow the same native selection | D08D / Terminal |
| E05 | Nanosecond market/acquisition clocks and native sequence — iexDepthReplay.ts | **IMPROVE** | Evidence with exact values. No Number conversion for identity; ordinal only under verified artifact | Terminal / D08D |
| E06 | Depth snapshot visualization of last 60 selected-prefix samples — DepthSnapshots | **RETAIN** | Depth tab; window count and ordinal axis. Equal sample spacing is not elapsed time; no future-prefix leakage | Terminal |
| E07 | Near observed top ±1% / all retained levels — iexDepthPriceRange | **RETAIN** | Display controls. Price view affects picture only; totals retain all observed orders | Terminal |
| E08 | Bid/ask observed totals and order count — IEX sample contract | **IMPROVE** | Statistics and evidence. Withheld book displays dashes; schema zero is not observed market zero | Terminal |
| E09 | Executed-share profile with buy/sell/unknown — iexExecutionProfile | **RETAIN** | Executed volume tab + table. Reuse Large Trades correction engine; native sequence first | Terminal |
| E10 | Trade breaks, duplicate/conflicting identities and unmatched cancels — largeTrades engine | **RETAIN** | Accounting qualifier in evidence. Later native records do not revise earlier selected states | Terminal |
| E11 | First 64 price rows with complete captured totals disclosure — IexDepthReplayView | **RETAIN** | Executed-volume table footer. Existing disclosure retained; no new pagination endpoint promised | Terminal |
| E12 | Sample retention and level truncation flags — DepthSampler / reader | **IMPROVE** | Visible coverage line + details. Partial capture is prominent; explain max-levels versus full observed totals | IEX producer |
| E13 | Source-gap/prefix, order-chain and multiple-stream states — IEX parser | **IMPROVE** | Gap at cursor, exact typed reason in evidence. Never interpolate a missing book or show withheld totals as zero | IEX producer |
| E14 | Artifact hash and servedAt already returned by client — fetchLargeTrades; currently dropped by view | **IMPROVE** | Carry through reader state into evidence. Source hash alone does not identify the current sampled artifact | Terminal |
| E15 | Distinct signed-out/denied/rate/invalid/unavailable outcomes — fetchLargeTrades; collapsed by view | **IMPROVE** | Honest access and failure states. Preserve established reason; unknown remains generic | Terminal / access |
| E16 | Refresh clears cursor to latest, artifact may change — IexDepthReplayView | **IMPROVE** | Explicit publication-change transition. Do not silently rebind inspected evidence by a fresh array index | Terminal / D08D |
| E17 | IEX attribution and terms link — sourceAdmission + view | **RETAIN** | Source and limitations disclosure. Required attribution survives mobile, themes and localization | Publisher |
| E18 | Partial archive and absence of original intraday knowledge — IEX provenance | **IMPROVE** | Historical/acquired-later labels. Knowledge cutoff is archive acquisition, not a reconstructed live receipt | IEX producer |
| J01 | Generic Options / price chart / sibling replay links — Both current replay views | **IMPROVE** | Qualified origin return plus tools menu. Sender-owned context first; generic destination accurately labeled fallback | D08 / D06 |
| J02 | Existing Macro allowlist, embedded close and company search history — originNav / companySearchContext | **RETAIN** | Existing origin owner. Do not widen cross-origin permissions or overload closed company-search shape | D06 / F01 |
| J03 | Exact origin view/filter/row/focus/scroll restoration — D08 semantic interface; not implemented end-to-end | **BLOCKED_DATA** | Proposed return adapter owned by sender/integration. Requires actual existing-owner codec and path proof | D08 / D06 / D08A |
| J04 | Durable observation save and later reconstruction — D08/D23 semantic boundary; no replay save API identified | **BLOCKED_DATA** | Existing Investigation / D23 after admitted contract. No duplicate evidence store, fake Saved toast or current-artifact substitution | D23 / archive owner |
| J05 | Guest, verified plan and unverified access presentation — OptionsPaywall + APIs | **IMPROVE** | Replay-specific access panel preserving request/return. Current generic live-options pitch does not explain historical replay | Access / D08 |
| J06 | Responsive keyboard/touch and chart text alternatives — Current chart SVG/native controls | **IMPROVE** | One adaptive page and evidence overlay. 44px house controls, non-drag selection and no page overflow | F01 / F02 / Terminal |
| J07 | Dark/light and EN/ZH parity — Current feature copy + shared foundation candidate | **IMPROVE** | Shared theme roles and local copy. Final compositions await foundation/Paper gates; no independent palette plane | F01 / F02 |
| J08 | Native beta projection/registry admission — Programme census excludes equity replay from current 17 native paths | **BLOCKED_DATA** | Existing registry/publisher/F03 admission only. Source path and current direct URL reachability do not establish official admission | F03 / incumbent publisher |
| J09 | Dev futures, futures-sample and options-plan guards — all three page modules; options-plan live404 | **RETAIN** | Development harnesses remain production404. Synthetic ResearchLab and verified local sample imports never become customer fallback, menu or admission expansion | Existing harness owner |
| J10 | Source inspection/publish authorization boundary — Historical research + source owners | **RETAIN** | Existing rights/installation owner. No feed purchase, source-config retry, capture installation or new publisher | Incumbent source owner |
| P01 | Autoplay, speed and arbitrary archive/date catalog — No current route capability | **BLOCKED_DATA** | Proposal only, outside active control set. Requires retained-observation stepping contract/calendar/history owner; no fake 1× clock | D08 / archive owner |
| P02 | Dedicated editable Paper file and immutable visual freeze — Proposed MM · Futures & Replay; no IDs | **BLOCKED_DATA** | P00-qualified dedicated file then exact owned boards. Published action drift and unreleased foundation prevent final qualification | P00 / F01 / F02 / QA01 |

## Relocation and removal decisions

F19 moves the weekly COT panel into a named below-chart disclosure. It remains reachable from the primary futures workspace, keeps all four groups, report/retrieval clocks, open-interest comparisons and its CFTC link. The purpose is to prevent a weekly observation without a first-available timestamp from appearing to be part of historical cursor evidence. This is a presentation relocation, not a route or source change.

There are **zero removals**. Deep source data, precision, failure qualifiers, small-screen access and advanced controls are covered individually rather than replaced with a simplified hero chart. The proposal for exact return, durable save, wider history and autoplay does not make those capabilities existing or accepted.

