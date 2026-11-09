# Build plan: native workflows to qualified product behavior

## What this packet supplies

Twenty-four native editable boards cover Catalyst investigation, Intraday scan and evidence, shared Search recovery and empty Watchlists. The packet includes named native destinations, JSX, screenshots, source findings, interaction requirements and a self-contained motion specimen.

The JSX is Paper reference markup. Use it to recover hierarchy, values, tokens and layout; implement semantic components within the existing application. A visual button in Paper is not proof of a wired route, account mutation or tested keyboard interaction. Do not ship fixture company names, prices, dates or result counts as live data.

## Capability map

| Area | Current source capability established by inspection | Design addition | Build dependency |
|---|---|---|---|
| Catalyst | Existing BioCatalyst trial/publication readers and manual owner-scoped note flow | Compact case ledger, distinct evidence views, source-version recovery | Verified issuer-to-trial identity before enabling company-specific save; existing R2 remains the save owner |
| Intraday | One browser compute path over BASE_DATA and mutable quote/pulse/flow state; Python rule implementation | Compact scan, explicit recorded example, complete evidence and unavailable-input states | Qualified source clocks, retention semantics, tri-state consistency and real fixed recorded basis |
| Search | Shared query, independent Companies/Tools service state and existing history/focus owner | Focused Companies-unavailable recovery in EN/ZH320 | Current request matching and cached-result qualification; no new query store |
| Watchlists | Active-subject owned inventory, existing save/reconcile and storage fences | Empty-owned-list screen without unusable Save/chooser | Keep unknown-save recovery independent; prove existing generic Monitor return |
| Illustrations | Existing Signal Ink renderer and shared reveal assets | Native motion storyboard and HTML specimen | Browser/theme/reduced-motion proof in the consuming application |

The source pins and exact path/blob evidence are in the individual workflow files and evidence directory. These findings describe the inspected source versions, not deployed runtime behavior.

## 1. Bind data meaning before rendering the new state

### Catalyst identity and evidence

Keep issuer identity, NCT identity, event/mode, exact row key, publication reference and local manual-note ID distinct. A sponsor name or ticker is not enough to invent an NCT join. The four original fictional companies remain examples. Their “Trial link needed” control is intentionally unavailable.

Use the existing BioCatalyst destination for unbound trial research. When a real eligible trial record is available, use existing R2 board 171-0 and its current subject, owner key, storage and authentication lifecycle. Preserve its price/currency validation and exact saved basis.

A changed publication reference supports source-version change. To show a field diff, both allowed versions must be available for the same owner and exact record. A missing older payload supports an unavailable comparison, not an invented change. Viewing current evidence cannot silently overwrite a saved condition.

### Intraday basis and qualification

The current browser source composes BASE_DATA with mutable quoteState, pulseState and flowState. It does not establish an immutable historical assessment object. “Board built” and “source observed” are different clocks. A recorded product view must bind to an actual fixed result and its basis from the existing producer; re-running current logic on retained values is not retrieval of the old result.

Within the existing readers, qualify each source using actual producer schema, observation time and market/session meaning. Retained values must keep their own age and provenance. Do not relabel all rows live because coverage crosses a threshold or a request succeeds. If a source omits a member, preserve the distinction between deliberate retention, an explicit unavailable member and a newly observed value.

Do not invent freshness limits in presentation code. Confirm the producer's clock/session contract and repair its existing consumer. Current findings to address are:

- Quote and pulse “live” labels are coverage-based at 90% and 80%; absent members and failure can retain old values.
- flowMetaFresh accepts outside-window input without age qualification and its in-window upper age bound accepts future stamps.
- updateFlowStamp does not render the passed source clocks.
- No read/degraded rows are omitted by laneCounts.
- Browser and Python seven-check semantics differ for missing inputs, known traps and selected proxy/fallback cases.

Resolve these in their current owners or record an explicitly accepted rule divergence. Preserve true/false/unknown through the result. Valid zero is not missing. Call-only cumulative NCP and durability remain distinct from total calls-plus-puts premium. K counts true checks; it is not a new composite score.

## 2. Preserve one state and navigation owner

| Interaction | Existing owner to extend | Required result |
|---|---|---|
| Catalyst row → case → source → back | Existing selected-case/filter/mode state and router | Exact subject, selection, filter, scroll and invoker restored |
| Eligible manual save/review | R2 currentSubject, ownerKeyFor, ownerStorage, MDXAuth | Matching readback before success; uncertain effect reconciled at original target |
| Intraday class/filter/row | activeBasket, activeStance, searchQ, groupByStance, openRows, boardExpanded | Summary, count, list and detail project the same qualified computation |
| Search Companies → Tools | SharedSearchWorkspace and existing ShellSearch history | Same current query on scope switch; independent service status; established return restoration |
| Empty list → Monitor/back | CompanyWatchSave and existing shared navigation | Generic Monitor route, no auto-create or save, current-subject inventory refresh only |
| Case overlay close/Escape | Existing route/dialog owner | Focus returns to invoker or established fallback |

Use the existing state owner to carry return context. A new registry, persistence layer, queue, account model, poller or router is not needed for this presentation pass.

For Intraday, evaluate once and project that result into all visible surfaces. Counts, selected row and detail must change together. Do not calculate a second headline classification from a separate set of inputs.

## 3. Implement the concise customer surfaces

### Catalyst

Build the desktop split workbench with a four-row ledger and one selected-case reading surface. On phone, prioritize all four rows and route to a dedicated case view. The selected subject and next action should be visible before long reasoning.

Retain distinct destinations for Aster trial/company/price evidence, Morrow timing risk, Kestrel financing and Lumen read-through comparisons. Preserve the original values, fictional labels and source limitations. The source drawer must return to its actual originating case.

### Intraday

Use compact classification controls instead of six large reading cards. Keep both nonzero recorded classes prominent and all original classes/counts reachable in UP-0. Show all five original candidates on the narrow scan, with details behind each row.

The source specimen lacks individual original check values. The new detail therefore says Not provided for all seven; implementation must replace that with qualified existing results, never infer the checks from the displayed classification.

Use the retained loading and successful-no-match views for their actual states. Use TF-0 when required current inputs are unusable. A partial qualified result keeps explicit coverage and source qualification. Optional options data must not become a universal eligibility gate unless the existing rule requires it.

### Search and Watchlists

Implement the state guards and destination rules in SHARED_STATES.md. Keep support text short. Build-only provenance, request matching and account details belong in the adjacent native Build notes or source documentation, not the customer UI.

## 4. Apply the established visual and motion system

Use Inter and current theme tokens. Light text uses the semantic ink variants where chart/status colors lack enough text contrast. The Catalyst selected light-panel green was corrected from approximately 3.80:1 to 5.56:1. Keep text labels alongside semantic color.

Use shared control heights and spacing, clear selected rows, a dominant useful action and generous separation between scan and deep evidence. Native widths include desktop 1440, phone 390 and narrow 320; runtime intermediate widths still require consumer testing.

Reuse `lib/illus.py`, `templates/illus.css` and `templates/illus.js` for display-tier chart illustrations. Their Signal Ink reveal draws once and settles to a static endpoint. Empty/too-short data stays an honest null. Interactive trading charts remain on their established chart owner.

[motion_specimen.html](motion_specimen.html) inlines the pinned shared CSS/JS and preserves the original example series path. It includes a proposed 180ms opacity/8px case entry, open/close/Escape focus behavior, theme toggle and reduced-motion control. It performs no fetch or account/storage operation. It is a demonstrator, not a new production animation system.

Static JavaScript parsing, exact pinned asset hashes, original-path preservation and absence of fetch/storage calls were checked. Browser animation, responsive rendering, keyboard behavior and screen-reader behavior remain unproven in the actual consumer. System reduced motion must display the final state immediately; counts must never animate from zero while data is unknown.

## 5. Build in this order

| Step | Existing implementation surface | Deliverable | Exit evidence |
|---|---|---|---|
| 1 | Intraday producer and template state owners | Qualified input/basis rules and explicit parity decision | Discriminating cases for stale/future/off-session, retained/missing/zero, known trap/unknown and all-degraded |
| 2 | Intraday existing render/compute path | New scan, counts, evidence and unavailable-input layout | Same computed result across summary/list/detail; recorded/current basis cannot leak |
| 3 | BioCatalyst existing route and manual-note owner | Case workbench and exact evidence/source return | Unjoined issuer stays blocked; eligible real trial uses current R2 and readback |
| 4 | SharedSearchWorkspace / current shell owners | EN/ZH company-failure recovery | Cached vs no-usable-result, shared query, retry matching and focus/history behavior |
| 5 | CompanyWatchSave / current navigation | Empty owned inventory presentation | Independent unknown-save recovery, subject change and Monitor/back proof |
| 6 | Existing illustration/consumer styles | Motion and responsive polish | Both themes, EN/ZH, 320/390/desktop, keyboard, reduced motion and actual browser screenshots |

These are build slices under current code owners and repository controls, not new dispatched jobs. No endpoint, runtime deployment, trading action or account mutation was performed for this design packet.

## 6. Verification that would distinguish a correct build

Test real boundaries rather than static markup mirroring:

- Missing, null, restricted, stale and zero values produce different honest states.
- Old and new source clocks cannot silently combine into a current assessment.
- A fixed recorded basis yields stable output even when current inputs/clock change.
- Count, selected company, classification and check detail agree.
- A source-version change with no older payload cannot create a field diff or clinical-outcome claim.
- Account change and a late read cannot expose another owner's inventory or note.
- A save timeout or unknown result cannot become a new automatic mutation.
- Opening Monitor, switching Search scope, checking storage and viewing evidence remain reads/navigation.
- Keyboard/back return preserves the real invoker, and reduced motion preserves comprehension.

Use affected implementation tests and required CI when code is changed. Native screenshots and this source packet prove the design amendment only.

