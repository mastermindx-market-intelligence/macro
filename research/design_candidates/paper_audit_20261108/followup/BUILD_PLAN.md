# Builder plan — Paper continuation

This is the task tree for the design continuation, not a runtime queue or permission grant. IDs F01–F12 identify bounded implementation slices. Existing programme owners, source custody, admitted operations and release controls continue to govern execution.

## Architecture and content placement

The product should let a customer identify the subject, result, material limitation, unit/window and next action immediately. Short methods and sources belong in named user destinations with a reliable return. Schemas, formulas, capture requirements, state transitions, permission checks, negative cases and archival provenance belong in Build.

Use each feature's existing producer, loader, route state and effect owner. Do not add a cross-product context service, save service, ranking service, retry system or watcher to implement this plan. Treat the context tuples below as required fields carried through existing interfaces, not a proposed global schema.

A read-only navigation is not a save, review, verification, watch or publication event. A displayed static control is not evidence that its operation exists. A data result should commit with its own labels and clocks; a missing result must retain its actual unavailable/unknown state.

## Source and geometry map

| Slice | Existing path or owner | Paper anchor | Dependency |
|---|---|---|---|
| F01 | Macro expectation builder and explorer template | 47N-0 / 47W-0 | Existing comparable-pair rule |
| F02 | Existing Expectations mover/explorer loader | 3XS-0 / 3Y0-0 / 48A-0 | F01 |
| F03 | Terminal volTenorComparison / VolComparePanel / current Flow owner | ET-0 / KT-0 / 16M-0 | Exact admitted payload and entitlement |
| F04 | TickerNewsPanel, NewsLadder, NewsCatchup | 27L-0 / 3H7-0 | Existing story identity and review owner |
| F05 | Risk Radar workspace and probability evidence builder | AZL-0 | Existing model/horizon definition |
| F06 | Existing Sector comparison, stance and dossier owners | FB7-0 / FO0-0 / GYT-0 | Existing qualified measured data; GPL for return extension |
| F07 | Hub command producer and current list navigation | 854-0 / 83A-0 | Matching source generation |
| F08 | PROPHET candidate, verification, research and Plan owners | 10TD-0 / 133D-0 / 13L8-0 | Exact per-subject record identity |
| F09 | Investigation revision/RPC and operation readback | 16M-0 | Supported evidence admission |
| F10 | Existing watch and assessment owners | TP-0 / mobile 1-0 | Qualified observations and supported effect |
| F11 | Existing Guide destination and local search navigation | 26E-1 / 294-1 / 2BP-1 | D25 and R20 return contracts |
| F12 | Existing MX/Freshness and evidence disclosure | 2U8-0 / 2WI-0 | Owner-qualified meaning of each clock |

F03–F08 can be implemented independently after their own source binding is resolved. F09/F10 do not block the honest unavailable or read-only states.

## F01 — Fiscal-period-safe Expectations comparisons

**Existing behavior:** _comparable_pairs in scripts/build_expectation_surface.py requires equal, known period_end for the same security, metric and raw horizon. Zero prior still has a valid role in breadth; it cannot produce a valid percentage denominator. The leading-class threshold is 1.2×, not merely a majority.

**Required extension:** apply the same period discipline to the explorer's previous-value lookup and history. Retain security, metric, raw horizon, actual period_end, source identity, prior_at and latest_at. The selected readout and percentage must refer to the selected fiscal period.

Scope a plot to one fiscal period. If the product intentionally shows earlier periods, break and label every segment by its actual period end; a gap alone is insufficient beneath a single period header.

**Acceptance:**

1. Same known period with a valid nonzero prior produces the expected change.
2. A fiscal-period rollover retains the new estimate but withholds the cross-period percentage.
3. Unknown period, first capture and zero prior each produce their own truthful missing-comparison behavior.
4. A valid zero prior still participates in the existing breadth definition.
5. Different previous-capture dates remain visible rather than being collapsed into a common interval.
6. Latest breadth copy does not silently alter revenue logic, classification thresholds or the historical streak definition.
7. Desktop/light/mobile/ZH readouts preserve complete dates, units and precision under long labels and enlarged text.

**Completion evidence:** focused source tests for pairing and explorer selection, then the real consumer showing at least a same-period pair, rollover and unknown-period case. Paper screenshots are the target geometry.

## F02 — Atomic selection, loading, disclosure and motion

Carry the selected security, metric, fiscal period and source snapshot through the existing mover, explorer and loader. A mover opens that exact tuple. An unavailable horizon must not silently fall back to another horizon through pickHorizon.

When security, metric, fiscal period or an explicitly selected snapshot changes, retire the old chart and values together and name the pending selection. A refresh of the same security/metric/period may retain the last settled values, visibly tied to their original capture clock, while a newer snapshot loads. Commit the accepted snapshot, labels, values and chart together. If refresh reveals a new fiscal period, use the context-change behavior.

Use obsolete-response protection inside the existing loader. Request generation or equivalent incumbent cancellation is an implementation mechanism, not a new service.

“Show numbers” expands exact matching values below the visible chart; “Hide the numbers” collapses them. Preserve the invoking focus and accurate expanded state. At 390px the initial movers are three per direction; expanding uses the existing source list and order, currently capped by the producer at 25 per direction.

**Motion reference:** controls settle around 160ms; an accepted content crossfade around 200ms is a design target. Context-change placeholders are not a zero value. Reduced motion commits directly to the identical final state. No loading shimmer or interpolation may impersonate measured data.

**Acceptance:** rapid A→B→A, out-of-order responses, failed same-selection refresh, failed changed selection, fiscal rollover during refresh, absent horizon, keyboard disclosure, browser Back and reduced motion. The real path must never show a new label over an old result.

**Working study:** [evidence-motion-reference.html](../evidence-motion-reference.html) → Reference controls → Expectations. Switch between the synthetic EPS and Revenue contexts, or refresh the current context. Deliver latest, deliver one retained earlier response, or fail latest. Start an A refresh, select B, return to A, then deliver the earlier response to inspect why request identity must supplement context identity. The study shares theme/language/reduced-motion controls but does not write GMI history, issue service requests, store data, or replace the existing product loader.

The expanded verifier has 14 passing source/DOM cases (nine retained, five new). It proves the simulated reading bundle and request transitions, not actual browser painting, focus behavior under real disabled controls, access enforcement, fiscal rollover during a real refresh, explicit historical-snapshot selection, chart integration or production. Keep those consumer proofs in the acceptance above. The Paper storyboard remains the intended full chart presentation; the working study isolates the value/label/clock transition.

## F03 — Options source fidelity and read-only interpretation

Reuse terminal/lib/volTenorComparison.ts and VolComparePanel; the arithmetic is already implemented at the retained Terminal pin.

- Constant tenor: interpolate total variance, IV² × calendar DTE.
- Skew: interpolate IV in actual strike. Auto uses puts at/below reference and calls above.
- A supplied selected-expiry smile takes precedence; nearest-30D is a fallback when the selected smile is absent.
- Missing legs are not bridged and unsupported wings are not extrapolated.
- The published ATM reference is a display proxy unless the source actually supplies spot or delta.

Bind the fixture and every display label to the same expiry and source generation. Preserve date-only volatility precision, separate spot clock and the independently dated one-day band. Calendar tenor interpolation and the expected-move estimator's declared 252-trading-day annualization are separate conventions.

**Fixture acceptance:** 14D 32.2 and 30D 29.4 produce 21D 30.48015748→30.5. Selected 23 Oct / 2D produces 95% 40.8, ATM 36.9, 105% 34.0, with 90%/110% unavailable. A 36.9 IV / two-trading-day expected move from 236.14 produces $228.38–$243.90 after the incumbent formatter.

In Flow, the $216,000 print is related context outside a ≥$250K filter. The displayed caption counts five matching rows plus one related print. Preserve the producer-defined 23 total under its existing semantics; do not equate it with visible filtered rows or qualify canceled-record membership without source evidence. Possible grouping remains possible, not confirmed.

**Completion evidence:** selected-expiry switches, missing/partial smiles, source-date mismatch, reference-vs-spot distinction, exact formatting and filter membership through the existing consumer. Event weekday corrections are calendar arithmetic only, not validation of real earnings/FOMC schedules.

**Expected-move illustration:** Help 17X-0 is a static dependency figure: IV plus trading-day horizon → percentage estimate; percentage plus qualifying spot → dollar price range. Reuse expectedMoveFromIv at terminal/lib/volTenorComparison.ts:134. A qualifying spot is finite, positive and has a non-empty observation time. Preserve its own clock and admitted source context; this figure does not authorize arbitrary source pairing. The expected-move horizon uses trading days/252, independently of the calendar-DTE total-variance interpolation described above. Keep return 150-0 and supply a meaningful accessible figure name. No animation or new control is required.

## F04 — News touch access with explicit review effects

Implement 44px coarse-pointer targets in TickerNewsPanel, NewsLadder and NewsCatchup, retaining existing DOM hooks, story identity and keyboard semantics. Fine-pointer compact controls remain a valid separate treatment.

Each grouped ladder is one disclosure control with accurate expanded state. Single-report 2C6-0 is static. “More reports” reveals the remainder of the same group; it does not change a story's reviewed state.

Only explicit Mark reviewed creates the review effect. Mark shown uses the shown eligible stories at activation. Reading, opening, expanding, collapsing, filtering, closing and returning create no receipt.

**Acceptance:** actual touch hit geometry, keyboard activation and focus, screen-reader expanded state, filter changes, a provisional group of three reports, a one-report row, a late report/correction, Mark shown with hidden stories, and interrupted review readback through the existing owner. Reuse the existing reading-return proposal; do not add another restoration store.

## F05 — Risk horizon and cohort fidelity

Use the incumbent probability target: native SPY closing observations. Display trading-day labels / 交易日 with a precise next-21-closing-observations definition. Do not borrow the separate onset-lift helper's business-day convention.

Preserve the dated 13% specimen, rounded 18% reference, 0.73× ratio, 23 September 2026 clock, missing coverage and unverified calibration. The 36/100 risk index is a different object. A changed label cannot qualify the separate retained historical cohort; it retains its original 21D label and unverified match.

**Acceptance:** both languages, locale return, direct entry, absent/invalid price window, no missing→zero conversion, distinct index/probability, and history with unknown matching metadata. No fixed calendar completion date or complete exchange-calendar coverage is implied.

## F06 — Sector comparison hierarchy and exact return

Keep the measured comparison usable. Only the unqualified current-model estimate remains unavailable.

The 21-session sector-ETF headline and basis lead before secondary lenses. Current stance is the source's entry assessment. Pair Energy with its Energy dossier and Technology with its Technology dossier; “Watch — don't chase” is not a watch creation affordance.

Reuse action identities FKV-0/FKX-0 and FXD-0/FXH-0. Ordered-pair restoration, benchmark/window/source basis, focus and scroll remain the existing GPL-0 proposal and its incumbent navigation extension. Do not substitute another sector, order or source generation on return.

Historical 14% has its original “up leg ends within” event meaning and retained parity failure; 33%/52% PRIOR examples keep their populations and time horizons. None fills a current unavailable estimate.

**Acceptance:** sector swap, source generation change, absent/changed selected sector, both dossier return paths, narrow layout, keyboard focus and browser Back. Compare measured return, member-stock mean, participation, cycle interpretation, prior and current model as distinct objects. Preserve G4P review-only canary and BML acceptance hold.

## F07 — Hub explanation, source generation and honest unavailable effects

The producer owns ordering. At the retained pin, the command sorts by opportunity_score, then composite_conviction, descending. Edge index is edge_remaining ×100; stage is a separate category. Filtering narrows the supplied order. Do not locally rescore or normalize US and China into one rank.

The no-component edge branch returns 0.4, despite an older 0.5 comment. A default qualifier needs a matching full command record with edge_components =0. The compact hero omits that count. Never infer default from score 40 or claim coverage from an absent field.

75X-0 opens the explanation through the existing list-navigation owner. Return restores market, query, stage, source generation, selected row, scroll and focus. Opening help does not fetch, rescore, refresh or save. Changed/missing origin uses the existing return contract.

Alert activation and draft persistence stay unavailable until their exact existing owners support the operation and readback. Healthy-empty returns to the published list, not an unbound queue.

**Acceptance:** ties, valid zeros, missing coverage, generation change, healthy-empty vs unavailable vs filtered-to-zero, direct help entry, EN/ZH, keyboard/touch/Back, and zero submissions from unavailable controls. Preserve China list/filter/apply/cancel contracts and held AXON shell 43.

## F08 — PROPHET subject-specific verification

Bind each evidence action to its selected candidate occurrence and source generation. Ticker plus date is not a substitute. Use the existing verification owner only when that subject's exact record exists.

INTC/MSFT in 133D-0 lack authoritative occurrence records and exact Plan links. Plain “Evidence record unavailable” is sufficient; do not add dead buttons or bind them to NVDA VBF-0. A future enabled action should identify its subject and return to the same ordered comparison with invoking focus.

Unavailable assessment names missing source checks and retains genuinely bound research/history actions. Missing is not bearish, neutral or zero; a prior subject's result cannot become the current result.

**Acceptance:** partial identity, account change, wrong subject, source-generation mismatch, late old-subject response, missing Plan, safe direct entry and return. Opening evidence is not verification. Preserve the p-C / ZE5 uncertain-effect fence, D03 draft programme and Phase 2A acceptance. Security watchlist membership remains its separate D23 operation, not dated-comparison persistence.

## F09 — Investigation save admission and uncertain outcomes

Reuse applyInvestigationRevision / apply_investigation_revision_v2, operation_id, expected_revision, readInvestigation and readInvestigationOperation. terminal.options_exposure remains the existing Options owner.

The accepted chart entry mints a ready exposure-chart object and matching sector origin. That does not prove standalone Flow-print or Volatility-snapshot admission. VolView currently omits the optional onOpenResearch callback. A future adapter must name an admitted exact evidence object and preserve source version, clocks, basis and provenance; do not invent an evidence kind to make the button active.

**Acceptance:** exact chart object, existing separately admitted matrix selection where applicable, unsupported object refusal, double activation without duplicate logical effect, stale expected revision, lost response reconciled by original operation ID, successful revision readback, reload and unavailable control semantics.

A rendered button, receipt of a request, and a saved revision are separate states. An uncertain outcome stays on its original operation; it is not automatically retried or relabeled failed.

## F10 — Watch condition, receipt and research assessment

Keep watch state and research conclusion separate. The historical condition firing is preserved. The broad “before rotation faded” question remains inconclusive because rotation fade is undefined.

The hero labels the conclusion Draft while revision 3 remains saved. Only the existing assessment write plus revision readback may promote revision 4. A watch receipt does not infer thesis success.

Re-arm retains 230.00 until an explicit supported edit changes it. Show the later 230→232.5 evidence beside the action. Five-minute cadence means a future evaluation, not guaranteed firing. A fresh qualifying observation is required. Keep current quote 21 Oct 16:30:04 ET, historical quote 15:40:01Z and receipt/firing 15:40:03Z distinct.

**Acceptance:** no fresh quote, stale or missing quote, threshold still met, threshold no longer met, explicit threshold edit, manual re-arm, immutable receipt, correction as a new receipt, unsaved assessment, conflicting revision and uncertain effect reconciliation. Use the existing watch owner; no timer in the view, duplicate watch service or foreground polling loop.

## F11 — Guide destination names, selected-lesson visibility and qualified return

Use “Open Macro dashboard” for the three search/recovery headers. It is a named destination, not a promise to restore a prior Macro view. Preserve D25’s distinct Back one step and qualified Return to your view actions.

R20 specifies preserved query, filters, result position and opener focus; those are proposed integration behaviors, not a complete implemented return owner. The source route remains Market Reference at `site/reference.html`. At the Macro comparison pin, the current page keeps local filter state while its document survives, reads `?q=` once without writing it, opens canonical entry hashes and uses `history.back()` for its qualified Back control. This does not establish restored search state after document recreation or a dedicated direct-entry fallback.

| Existing source owner | Current behavior and concrete extension seam |
| --- | --- |
| `templates/reference.html.j2` — `state`, `applyFilters()`, `handleHash()`, `setOpenEntry()` | Owns page-local `{mode, family, letter, q}` substring filtering and canonical lesson expansion. A selected hash can still be hidden by `.is-off` on the lesson or its group. Extend this boundary to reveal the selected canonical lesson without clearing browse filters or counting a revealed nonmatch as a search match. |
| `scripts/build_market_reference.py` — `search_key()`, `validate()`, `build_view_model()` | Owns registry-derived EN/ZH labels, IDs and aliases in `data-search`; duplicate normalized aliases are rejected. Alias search is implemented, while alias-to-canonical route resolution and dominant exact-match ranking remain proposed work through this same registry. |
| `templates/shared_shell_bridge.js` — `sendViewState()`, `currentFocusId()`, `applyRestore()`, `handleLocationAccepted()` | Owns admitted shell navigation and positional restoration using `x`, `y` and optional `focusId`. The actual result and related-link anchors currently have no IDs. Give relevant openers stable unique IDs to make the incumbent focus field usable; generic coordinates alone do not restore analytical or search context. |

**Build order:** first repair filtered canonical-lesson visibility and define stable opener IDs within the existing Reference page. Preserve canonical entry IDs, the current route, actual match counts and the shared-shell acknowledgment path. Then implement R20's exact search return and direct-entry “Market Guide” fallback only as explicit extensions of the incumbent routing/filter contract. State any intended change to the current read-only `?q=` policy or `history.back()` semantics. No new global navigation store, parallel history service or replacement return owner is specified.

**Acceptance:** a filtered-out related lesson and its hidden parent group become visible; original query, filters and true match count remain intact; closing the lesson restores the filtered browse view. Result and related openers have stable unique IDs. Separately prove direct entry, query→lesson→results, browser Back, document recreation, changed/missing origin, scrolling and keyboard focus for the proposed return contract. The existing `test_reference_acknowledged_fragment_expansion_tracks_url_not_native_target()` verifies acknowledged fragment expansion and malformed/unknown hashes, not these added outcomes. Copy changes are verified in desktop and 390px Paper layouts; real route behavior remains a consumer proof obligation. Source findings and current-main refresh are recorded in R13.

## F12 — Primary clock and material second clock

The existing MX/Freshness component names a panel’s primary clock. A second clock belongs beside the verdict or action whenever it changes what the user can infer or do: for example, a current quote with an older assessment, or an observation time with a later firing receipt. Other source timestamps may remain in the existing LENS disclosure.

Do not choose the latest timestamp merely because it is latest. Preserve the source owner and semantic role of every clock. The shared rule changes presentation, not freshness computation, eligibility, assessment status or action admission. The source doctrine at Macro b5674d8ef898e503d6164922654f5ff89be9981c, docs/DESIGN_DOCTRINE.md:263, keeps freshness at its truthful scope and consequential limitations visible.

**Acceptance:** current quote/older assessment, distinct observation/receipt times, missing one clock, same-generation times, source change and narrow/localized layouts. A recent quote must not make a stale assessment appear current; a receipt time must not become the market observation time.

## Builder navigation in Paper

The shared system’s Build page p-B-0 begins with ANH-0, a compact companion linking PR #10872 and this F01–F12 sequence. It precedes the preserved 9ZT-0 reference row. This directory adds no owner, runtime state or acceptance decision. In particular, F01/F02 provenance holds, historical G15 uncertainty, required consumer journeys and the existing freeze boundary remain unchanged.

## Visual and interaction completion

Match the existing token system and neutral container boundaries. Keep status meaning in text as well as color. Preserve exact numeric precision and complete dates; do not solve overflow by dropping units, clocks, coverage or missing-value distinctions.

Use the Paper screenshots for the intended hierarchy and spacing. Verify the implemented consumer at desktop and 390px, long translated labels, enlarged text, keyboard, touch and reduced motion. Tests should target the changed behavior and consequential negative cases; do not duplicate whole suites or existing accepted proof without a changed dependency.

The current evidence is static Paper geometry plus source/readback verification. The prior denied local file preview is not authorization to replay that effect elsewhere. Obtain real consumer proof only through an independently authorized path under the incumbent programme, preserving any actual hold or uncertain effect.
