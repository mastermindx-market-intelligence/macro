# D02 interaction and state contract

**Proposed behavior for future approved implementation**, anchored to the existing routes and source controls. Existing behavior is identified explicitly. No save/alert service or shell v1 is released by this document.

## 1. Exact navigation contracts

| Surface | Existing URL/interaction identity | Required preservation |
| --- | --- | --- |
| Macro overview | /macro.html; existing dialog IDs and anchors | Do not invent query parameters for inspector state. Keep inbound anchors; future URL reflection needs F01 agreement. |
| Macro Command | #<section>/<subtab>; e.g. #money/central_banks, #growth/business, #credit/funding | Existing changes use replaceState. Preserve twelve sections and subtab state after delayed fragment insertion. |
| Economic workspace | #current, #drivers, #history | Existing mmx:shell-location reveals a hidden panel before anchor resolution; retain roving tab keyboard behavior. |
| Macro Context | #hero, #radar, #board, #quad, #rates, #matrix, #timeline, #census, #footnote | Preserve all destinations and readable headings; account for sticky host offset. |
| Odds | Validated ?t=<ticker>; #days, #path, #returns, #fm | Preserve query and tab meaning. Unknown ticker must expose any fallback. Existing ?lang=en/zh localStorage side effect needs F01/D25 policy decision. |
| Demand → company | stock.html#<ticker> | Preserve exact syntax until destination owner accepts a compatibility adapter. |
| Impulse → company | stock.html?t=<ticker> | Preserve exact syntax; do not normalize to Demand's form. |
| Anticipation data | Per-asset filenames replace = and ^ with _, retaining BRK-B's dash | Preserve stable asset identity and do not treat display labels as filenames. |
| Macro family assets | /macro/fragments/{consumer,credit,debt,growth,housing,inflation,jobs,money,policy,rates,trade}.html | Fetch-only inner HTML. No new document or redirect derived from /macro/<id>.html. |
| Internal surfaces | /crossasset.html, /macro_signals.html | Preserve server 404/access boundary even if a source template or candidate exists. |

A country or listing change is explicit navigation to a supported target. Retain the originating return context; never reuse cached US content under a China label. Terminal keeps its own focused chrome and Brain singleton. “Open chart” must use the existing accepted destination/return parser; no double wrapping.

## 2. Controls and effects

| Control / precondition | Result and feedback | URL/write | Focus, keyboard, scroll and return |
| --- | --- | --- | --- |
| Inspect evidence from overview, valid or degraded data | Open selected reading with value/qualification/source context | Local state; no persistence | Record trigger and scroll; focus inspector heading; Escape returns to trigger |
| Open driver details | Show raw/normalized value, contribution, history and definitions | Same inspector; no second modal | Use disclosure semantics; Enter/Space; preserve selected row and table scroll |
| Open method/source from Risk Radar | Replace inner inspector view; show target, evidence class, clocks and model | No navigation unless explicit source link | One overlay; Back returns to same horizon and Risk Radar reading, not page top |
| Change 5/10/21 observation horizon | Update matched target/estimate/evidence atomically | Local state unless existing URL supports it | Preserve active control; announce one concise result; no scrolling jump |
| Select Command section/subtab | Existing content then lazy fragment; selected state reapplied on response | replaceState using existing hash | Roving local focus; loading doesn't steal focus; no new history entry per repeated tab selection |
| Activate Current/Drivers/History | Reveal relevant suite panel | Existing hash behavior | Left/Right and Home/End tabs as existing implementation; focusable active tab, logical panel heading |
| Jump to hidden-panel anchor | Reveal owner panel first, then focus/scroll target | Existing hash/event | Sticky host offset; preserve Back/Forward and avoid scrolling both host and embedded content |
| Sort/filter laboratory results | Deterministic rows and visible count | Existing local/URL behavior only | Keep focus on header/control; aria-sort; missing values last both ways; preserve column labels on phone |
| Unknown Odds ticker | Show “Requested asset is unavailable; showing [actual asset]” with correction control | Preserve requested context until explicit selection | Focus error/selection region appropriately; do not imply requested asset was loaded |
| Open exact company/sector/chart | Navigate to existing owner route with identity and return context | Navigation only | Standard link behavior; modified click/new tab works; returning restores valid source state |
| Refresh source details after failure | Re-read same source; current data stays labeled retained until replaced | Read only | Busy feedback on control; bounded retry; no model rebuild or alert activation |
| Open external primary source | Open a real source URL with source name/date | Explicit navigation | Accessible link text; preserve current investigation/return position |
| Change locale/theme/context | Apply F01 policy and supported destination semantics | No save/watchlist/portfolio mutation | Preserve focus; maintain logical selected state and readable bilingual values |
| Save condition, only when D23 service/predicate qualified | D23 owns validation → pending → confirmed object/readback | Explicit mutation through D23 | Focus status; no close-on-submit before acknowledgment; preserve edits on error/expiry |
| Activate notification | Separate explicit D23 action after saved identity | D23 activation, not implied by save | Announce actual activation result only; reversible state according to owner contract |

Existing suite drawer traps buttons, links and summaries; adding inputs/selects requires a broader tested focus set. Its local-navigation inert handling does not prove the outer host is inert. F01/F02 must resolve the actual host/embedded focus and scroll boundary.

### Retained specialist controls recovered during source review

| Control | Existing effect to preserve | Proposed acceptance requirement |
| --- | --- | --- |
| Odds range / tolerance | 5y, 10y, 20y,max; exact,±1,±2 buckets; selection calls recompute | Keep selected criteria, label sample scope, show empty/thin state without relaxation; preserve focus. |
| Odds condition inclusion | Individual condition inclusion; unavailable conditions disabled | Do not manufacture unavailable factor values or re-enable by changing layout. |
| Odds factor match | Existing template selection, minimum N and sector filters | Keep their independent meanings, selection and result counts through other tab changes. |
| Odds matching-days CSV | Existing downloadCSV exports the full matched set | Do not export only visible/truncated rows; retain return definition, conditions, asset and horizon context. |
| Command/suite Ask the analyst | Existing MMBrain.explain(sectionId, localizedLabel), open or launcher boot; chat.html fallback | Same contextual singleton and accessible fallback. Existing Brain owner governs request/conversation effects; D02 creates no new service. |
| Cycle phase groups | Select one phase; selecting the sole phase again restores all; Select all restores groups. Frames remain separate. | Distinguish group filtering from focus; preserve filtered legend/card interpretation. |
| Cycle chip/card/chart-line | Toggle focus; setFocus updates the detail pane and replaces hash with #id, clearing to pathname+search | Focused frame has no measured hero line; preserve valid inbound hash and same selected identity on phone. |
| Cycle zoom / fullscreen | Full, 15y, 8y,Cycle,Reset with source domains; mobile15-year initial view; separate chart fullscreen | Preserve chart view on presentation changes; keep drag/pinch and keyboard-equivalent controls; fullscreen scroll lock must respect detail sheet. |
| Cycle detail sheet | Focus opens half on mobile; full/half/peek detents; clearing focus alone does not always collapse | Explicit close/scrim returns to peek and clears focus; Escape closes only the uppermost active layer and preserves host scroll responsibility. |

Source-level risk: cycle_app.js registers separate fullscreen and sheet Escape listeners. The first can clear the fullscreen class before the second tests it, so the same event may also collapse the sheet. This is a source inference, not an executed browser result; qualify and repair the one-layer behavior during the later authorized implementation. Source: [cycle_app.js](https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/cycle_app.js).

## 3. Shared state matrix with actual copy

| State / evidence trigger | Proposed copy and retained content | Recovery and invalidation |
| --- | --- | --- |
| Loaded | State/value + unit + observed date; material qualification adjacent | New compatible source generation can update atomically |
| First visit | Plain product question and one useful action; real current data when available | No mandatory tour or blank promotional page |
| Loading first read | “Loading macro evidence / 正在加载宏观证据” | Skeleton reflects intended layout; timeout becomes explicit failure |
| Refresh with prior verified data | “Showing the last available reading from [date]” | Keep data readable; new build time does not refresh old observation |
| Empty result after valid filter | “No names match these filters” plus reset | Preserve filters/count; distinct from failed fetch |
| No underlying observations | “No eligible observations are available for this reading” | No 0%, calm, neutral or fabricated chart |
| Partial | “Partial reading — [eligible]/[required] inputs available” | Expose actual counts/weighted coverage; recovery follows producer eligibility |
| Late within tolerance | “Update is later than usual; within the source's allowed window” | Show source's actual date and cadence |
| Stale | “Last observed [date]; the expected update is overdue” | Explain affected claim; do not blanket-hide other valid sources |
| Not yet released | “The next observation has not been released” | Scheduled time if real; distinguish publication detected/parse pending |
| Source failure | “This source could not be read. Other evidence remains available.” | Retry the read; preserve failure reason without technical stack traces |
| Unknown observation time | “Observation time unavailable / 观测时间未知” | Owner must supply timestamp; build date is not substitute |
| Rights blocked | “This data is unavailable under the current access or source-rights conditions” | Offer sign-in/plan action only when the access owner identifies a user-entitlement issue; otherwise preserve source-rights restriction; no restricted prefetch/preview |
| Unsupported region | “This workspace is currently available for the United States” | Explicit supported link; never relabel cached data |
| Disagreement | Show both interpretations, each date, basis and reason | No automatic averaging or “data error” claim without source evidence |
| Incompatible snapshot | “These readings come from different generations” | Retain a compatible bundle or explain individual observations |
| Unmatched model evidence | “Evidence is not matched to this model version” | No validation badge or inherited N |
| Thin reconstruction | “Historical reconstruction · limited evidence” | Event definition, N, events, interval and overlap/non-issued limitations remain accessible |
| Prospective immature | “Forward evidence is still accruing” | Issued and graded counts separate; time alone does not certify validation |
| Incomparable operands | “Comparison unavailable — [producer-qualified reason]” | Preserve independently valid rows; use the observed reference-period wording only for basis_mismatch:reference_end; distinguish rate-index mismatch, unknown basis and unavailable operand |
| Raw label pending | “New axis reading awaiting confirmation: [n] of [required] sessions” | Only when actual pending field exists; no browser countdown |
| Unsupported confirmed label | “Current axes no longer support the displayed label” | Preserve producer's raw/confirmed distinction and invalidation evidence |
| Risk context cap | “Stress inputs are high; broad market confirmation is absent” | Gate/coverage and both state labels inspectable |
| Revision / new model | “Revised observation” or “Method changed; numerical change is unavailable” | Preserve predecessor and effective date; do not backdate new knowledge |
| Guest | Preserve allowed shell/content with explicit existing sign-in destination | Return to exact route/query after auth; no entitlement assumption |
| Expired session during read | “Your session has expired” with existing continuation path | Preserve navigation and locally unsaved view; refetch only after authorization |
| Known route unavailable | “This workspace is temporarily unavailable” when host has that evidence | Distinct from unknown route 404 and denied internal route |
| Unknown / denied internal route | Existing 404 behavior | No alternative URL probing or route promotion |

The source distinguishes UNAVAILABLE from the raw score. Current internals raw=100 with display_score=null must remain unavailable. Macro Context's older projection currently drops those guard fields; future implementation must repair that projection.

## 4. Saving and uncertain outcomes

Current workspace alert_contract.service_available is false. A decorative active Save button is therefore not permitted as existing behavior. A future qualified D23 integration must represent:

| D23 state | Feedback | Permitted next action |
| --- | --- | --- |
| Unavailable | “Condition saving is unavailable for this reading” | Inspect method/source; no fake success |
| Editing / validation error | Field-level reason, preserved entered condition | Correct condition; no mutation until explicit submit |
| Pending | “Saving condition…” | Disable duplicate submission, retain operation identity |
| Saved with readback | “Condition saved” and authoritative object destination | Inspect saved object; activation is separate |
| Definitive failure before write | “Could not save; your condition is retained” | Retry through D23's contract |
| Timeout / expired after submit / unknown effect | “Save status is unknown. Checking the original request…” | Reconcile original identity; never blindly create a second object |
| Duplicate | Existing matching condition and actual current status | Open/reuse or explicitly modify through D23 |
| Activation pending/failed/confirmed | Separate accurate notification status | Never infer active from saved or from navigation |

## 5. Overlay and accessibility rules

Maintain at most one blocking modal at a time. Nested evidence is an internal view or replaces the inspector with a Back affordance. A nonmodal desktop inspector follows F01/F02's released contract; it must not declare aria-modal or trap unrelated page focus. A mobile modal has an accessible name, visible close, Escape, background inertness and a bounded scroll region. Do not infer pointer-away dismissal for every overlay; accidental closing must not discard unsaved D23 edits.

Store trigger identity, selected horizon/tab and logical reading context. On close, return to a still-existing trigger; otherwise use the nearest relevant section heading. Preserve the actual scroll owner. Browser Back while an overlay is open follows the released URL policy; do not rewrite existing history solely for visual convenience.

Interactive charts provide keyboard-accessible values, a textual interpretation and a table/CSV-equivalent view of the actual same data where the existing product permits export. Never invent an export entitlement. Tooltips do not contain the only explanation of a refusal or model limit. Tables use real headings, units and aria-sort. Horizontal scroll is contained within genuinely two-dimensional objects, with visible affordance and reachable controls.

Live updates announce only material changes, not every tick. Reduced motion disables decorative line draws, pulses and unnecessary transitions. At 400% zoom, close/actions/selected state remain reachable and the entire page does not overflow. Important phone controls use the programme's 44px house target; WCAG 2.2 AA's minimum target/spacing rule is a separate 24px standard.

## 6. Applicable and intentionally absent states

Empty filters, missing sources, stale evidence, denied access and unsupported region apply to read surfaces. Save pending/failed/uncertain states apply only after a real D23 integration is qualified. Trade execution, portfolio order confirmation and payment states are outside D02. Static historical documentation does not need a fake loading or transaction-success specimen. The future Paper state matrix must label such cases not applicable with these reasons.

