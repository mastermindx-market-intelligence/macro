# R32 current handoff

The current design and verified offline reference are documented in [R32 implementation](r32/implementation.md), [feature scorecard](r32/feature-scorecard.md), [R32 data/state extension](r32/data_contract.md), and [validation](r32/validation.md). These R32 documents govern the current journey and reference behavior; the historical baseline below remains preserved for traceability.

---

# R30 + R31 implementation contract

**Current extension:** [R31 depth and continuity](r31/implementation.md), [exact owner bindings](r31/data_contract.md), and [action map](r31/action_map.json). R31 expands the inventory to I01–I15 and resolves the previously unknown Investigation/Alerts owners. Its capability and retention boundaries take precedence over the baseline descriptions below. Native specimens remain design references; no runtime activation is implied.

## Accepted R30 baseline

This document defines the behavior behind the native Paper specimens. It does not assert that the controls already run. Visual completion, API/data binding, effect acceptance and empirical model acceptance are tracked independently.

## Navigation and disclosure

| Route | Question | Paper node | Primary next step |
| --- | --- | --- | --- |
| 01 · Bonds desk | Read the change; choose the next test. | 63GL-1 | 02 Curve · 03 Credit · 04 Capital |
| 02 · Curve & duration | Separate policy, term premium and sensitivity. | 63S3-1 | I02 Calculation · I10 Auction |
| 03 · Credit & issuer | Trace spread stress to financing obligations. | 63YS-1 | I05 Financing · I07 CDS · 05 Case |
| 04 · Capital competition | Compare the same buyer’s eligible alternatives. | 648A-1 | I06 Hedge · I08 Funding · 05 Case |
| 05 · Transmission | Inspect the proposed link and contrary evidence. | 64G1-1 | I03 Evidence · 06 Scenario · 07 Replay |
| 06 · Scenario | Change assumptions; retain confirmation and failure. | 64PQ-1 | I02 Calculation · I04 Monitor |
| 07 · Replay | Record the view before revealing outcomes. | 64WP-1 | I09 Filter · I11 Model · I12 Outcome |
| 08 · Saved cases | Review changed evidence and the next decision. | 670P-1 | Reopen case · I04 Monitor · I10 Check |

The default desktop shell has a 188 px sidebar and a 64 px top bar. Product content uses existing light research tokens, a 28 px primary heading, 14 px body copy, restrained state colors, 12 px card radii and deliberate spacing. Primary headings are brief; numerical interpretation sits next to the metric. Do not bring the specification atlas prose into the daily product interface.

One case owns the journey. Route changes preserve its revision, hypothesis, instruments, benchmark, base currency, hedge perspective, analysis horizon, evidence cutoff and mode. A local filter can remain local; a shared horizon change must recalculate dependents or identify incompatible comparisons. Closing a drawer restores its invoker, selection and position. Opening new evidence does not rewrite a saved historical revision.

## Core tool scorecards

### I01 · Value tooltip

Paper specimen: **662W-1**. Routes: 01, 02, 03, 04, 05, 06, 07, 08.

- **Entry:** Hover, keyboard focus or tap a value/information icon.
- **Behavior:** Show measure, units, change baseline, observation time, source availability, provenance and mode in at most 80 words. Tap opens a sheet on mobile. A source-detail action keeps the current case and returns to the same metric.
- **Data dependency:** A typed observation and lineage receipt; existing source date/gap fields where available. Raw values, revised releases, model estimates and synthetic fixtures remain distinguishable.
- **Required states:** Current, delayed, stale, unavailable, loading, source error.
- **Permitted effect:** Read-only inspection.
- **Acceptance:** Missing is not zero. Build time cannot replace the observation clock. Focus and Esc dismissal restore the invoking value; color is accompanied by text.

### I02 · Calculation popover

Paper specimen: **663U-1**. Routes: 02, 06.

- **Entry:** Calculation icon, duration result or scenario price effect.
- **Behavior:** Expose signed decimal shocks, units, sensitivity inputs and exclusions. Treasury price approximation uses modified duration and convexity. The corporate example separates benchmark-rate and spread duration and remains first order. Applying assumptions updates every dependent result together.
- **Data dependency:** Verified calculation owner plus instrument/benchmark identity and sensitivity date. Inputs are user assumptions unless a qualified source is explicitly bound.
- **Required states:** Valid, invalid numeric input, absent sensitivity, incomparable benchmark, approximation warning.
- **Permitted effect:** Local scenario state; persistence only through an explicit save.
- **Acceptance:** 1 bp converts to 0.0001. Invalid input clears the calculated output and identifies the field. All-in corporate yield cannot be combined with a separate spread shock. Mathematical sensitivity is never labeled expected return.

### I03 · Mechanism evidence drawer

Paper specimen: **6644-1**. Routes: 01, 03, 04, 05, 06, 08.

- **Entry:** Select a mechanism, inspect evidence, funding conditions or overlapping inputs.
- **Behavior:** Open the selected hypothesis with supporting observations, counterevidence, missing links, source lineage and the next independent check. The same observation may inform several hypotheses without becoming several independent confirmations. On mobile, expand one path and open its evidence sheet.
- **Data dependency:** Existing rates/credit and cross-asset projections plus approved observations; explicit analytical interpretation and hypothesis identity. No new state engine is introduced by the view.
- **Required states:** Partly supported, contested, missing link, source stale, no evidence.
- **Permitted effect:** Read-only interpretation; Add to scenario carries the hypothesis into route 06.
- **Acceptance:** Growth, substitution, safety demand and funding squeeze remain distinct. A Treasury price response does not fill a missing buyer-allocation link. Dashed edges carry no flow volume or causal proof.

### I04 · Case monitor composer

Paper specimen: **665W-1**. Routes: 01, 02, 03, 05, 06, 08.

- **Entry:** Monitor this view/case, Use this path or Manage monitors.
- **Behavior:** Inherit the case revision and show all confirmation conditions, explicit invalidators, source freshness/alignment policy, session expiry and delivery mode before saving. A composer preview explains unresolved data. Canonical persistence and activation are different outcomes.
- **Data dependency:** Existing canonical monitor/save/notification owner must be resolved in implementation. Qualified clocked evidence and a versioned rule definition are required for activation; a display-only projection cannot arm a qualified live monitor.
- **Required states:** Draft, saving, saved, effect uncertain, save failed, waiting, data paused, confirmed while watching, invalidated, expired, window closed.
- **Permitted effect:** A user-directed configuration save through the canonical owner. This design task activated no monitor or notification.
- **Acceptance:** Fresh valid invalidation outranks confirmation. Unknown critical evidence blocks confirmation. The fifth eligible close is evaluated before expiry. Pauses do not extend the window silently. Late data cannot silently reopen or backdate a terminal outcome. Duplicate saves have one canonical effect.

### I05 · Financing schedule

Paper specimen: **66AY-1**. Routes: 03, 06.

- **Entry:** Open financing schedule/window or inspect issuer obligations.
- **Behavior:** Retain legal obligor, recourse, collateral, currency, maturity/refixing schedule, cash restrictions, committed facilities, lease obligations and filing date separately. Source and mapping actions focus the relevant filing/schedule section; incomplete mapping remains visibly incomplete.
- **Data dependency:** Dated issuer filings and an instrument/obligation-level schedule. Existing capital_structure.event.v1 may supply relevant filing facts but is not a complete bond-maturity or covenant feed.
- **Required states:** Reported snapshot, mapped schedule, missing maturity date, restricted cash, amended financing, stale roll-forward.
- **Permitted effect:** Read-only inspection; an explicit manual assumption belongs to the scenario revision.
- **Acceptance:** Cash minus current debt is not labeled a funding gap or runway. Current classification is not an exact maturity calendar. Fixed debt reprices at contractual reset/refinance, not automatically with every market spread change.

### I06 · FX hedge inspector

Paper specimen: **669F-1**. Routes: 04, 06.

- **Entry:** Buyer selector, edit hedge assumptions or FX hedge inspector.
- **Behavior:** Preserve buyer base currency, mandate, duration, asset currency, quote direction, hedge tenor and comparison horizon. Separate observed quotes from manual assumptions. Changing any shared perspective invalidates incompatible cached comparisons and recalculates the full table.
- **Data dependency:** Exact forward/hedge quote, base instrument yield, quote clocks, day-count/annualization convention, costs and currency direction. The observed comparison pauses if a required quote is missing.
- **Required states:** Observed quote, manual assumption, expired quote, missing basis/forward, excluded instrument, incompatible duration.
- **Permitted effect:** Apply buyer perspective to the current case; save only on explicit action.
- **Acceptance:** 5.10% minus current annualized rolling-3M hedge cost 3.60% equals 1.50%. The 5 bp difference against a 1.55% JGB is not presented as a robust winner. Future roll costs remain open, and quotation inversion cannot reverse the economics accidentally.

### I07 · CDS quote conventions

Paper specimen: **66DX-1**. Routes: 03, 05.

- **Entry:** CDS value, quote details or contract inspector.
- **Behavior:** Identify the reference legal entity, seniority, currency, tenor, restructuring clause, coupon/upfront/spread convention, price side, contributor coverage, event terms and observation time before comparing instruments. Cash-bond spread matching remains a separate eligibility check.
- **Data dependency:** Licensed, correctly entitled instrument-level CDS observations and cash-bond metadata. A matching top-level CDS dataset was not established by the bounded local catalog search.
- **Required states:** Current, stale, no quote, insufficient contributors, contract mismatch, incomparable cash instrument.
- **Permitted effect:** Read-only quote inspection.
- **Acceptance:** CDS spread is not a real-world default probability. A price move cannot stand in for a filing-confirmed refinancing event. No synthetic CDS path enters observed-support scoring.

### I08 · Issuer currency funding

Paper specimen: **66CC-1**. Routes: 04.

- **Entry:** Issuer funding view switch.
- **Behavior:** Compare the same borrower, tenor, seniority and fixed/floating base-currency obligation across issue currencies after a matched swap. Keep fees, collateral terms, tax, liquidity and execution timing inspectable. Switching back restores the investor perspective.
- **Data dependency:** Borrower-specific new-issue terms, benchmark and spread, matched cross-currency swap terms, base currency, quote direction and same-time market inputs.
- **Required states:** Manual scenario, observed quote, missing swap/basis, tenor mismatch, borrower mismatch, incomplete costs.
- **Permitted effect:** Local comparison view; explicit save stores a case revision.
- **Acceptance:** The manual USD/EUR/JPY example is illustrative. Absent direct basis or swap terms remains unavailable. CNH basis or a generic funding proxy does not substitute for direct market-wide USD cross-currency basis.

### I09 · Episode filters

Paper specimen: **67NJ-1**. Routes: 07.

- **Entry:** Filter episodes, match mechanism, include contrary cases or inspect selection method.
- **Behavior:** Select the mechanism, horizon, market/funding regime and macro backdrop using only information admissible at the cutoff. Show exclusions and retain failed/contrary episodes. Reset changes filters without discarding the case.
- **Data dependency:** A versioned episode registry, eligible point-in-time features, data rights, release-clock admission and complete outcome windows for revealed analysis.
- **Required states:** Matches, valid zero matches, unavailable history, partial coverage, reset.
- **Permitted effect:** Read-only cohort selection; Save episode set persists explicit constraints through the canonical case owner.
- **Acceptance:** No future outcome, revised later feature or chosen success label leaks into matching. Date-only vintage metadata cannot imply intraday knowability. Zero eligible matches is distinct from no loaded history.

### I10 · Catalyst/check calendar

Paper specimen: **67OU-1**. Routes: 01, 02, 03, 04, 05, 08.

- **Entry:** View catalysts, auction/new-issue calendar, next check or attach a check.
- **Behavior:** Show the dated check, certainty of its schedule, source, affected hypothesis and what finding would strengthen or weaken it. Separate announcements, settlement dates, expected dates, cancellations and delayed releases.
- **Data dependency:** Official issuance/auction/release calendars and issuer reporting/financing records with availability clocks. The shown schedule is a fixture, not a current event feed.
- **Required states:** Scheduled, estimated, moved, cancelled, delayed, date unknown.
- **Permitted effect:** User-directed case attachment; no external message or real calendar action is implied.
- **Acceptance:** Unknown dates stay unknown. Net issuance arithmetic and settlement timing do not establish which investor supplied the capital. Opening a check preserves the case and returns to its prior route.

### I11 · Model evidence

Paper specimen: **67QO-1**. Routes: 06, 07.

- **Entry:** Likelihood status or Model evidence.
- **Behavior:** Show the registered target, horizon, model/data versions, admission coverage, effective episode count, out-of-time performance, baseline comparisons, calibration, uncertainty and abstention reason. Conditional paths remain available while qualification is pending.
- **Data dependency:** An existing approved model/evaluation owner and reproducible qualification receipts; no such new R30 evaluation was run in this task.
- **Required states:** Unavailable, insufficient cohort, qualified model, incompatible requested target, drift/coverage abstention.
- **Permitted effect:** Read-only qualification inspection.
- **Acceptance:** No LLM-authored probability. A probability trained for one event or horizon cannot be transferred to an arbitrary user monitor. Sliders are sensitivities and cannot silently become likelihood estimates.

### I12 · Outcome fingerprint

Paper specimen: **67RX-1**. Routes: 07.

- **Entry:** Record the decision, then Reveal outcome; choose single episode or cohort distribution.
- **Behavior:** Freeze the decision snapshot. Reveal response paths at common eligible horizons with explicit units, currency, price/total-return convention and coverage. Cohort mode shows the complete distribution and dependence-adjusted sample information; an unqualified cohort has a designed empty state.
- **Data dependency:** Admitted episode histories and complete future windows. Current 1D/5D/20D values are explicitly synthetic interface fixtures, separate from documented historical research episodes.
- **Required states:** Hidden, revealed, incomplete horizon, revised history, no qualified cohort.
- **Permitted effect:** Local reveal/record state, persisted only through explicit case actions.
- **Acceptance:** Later outcomes cannot alter the frozen hypothesis or matching features. Missing horizons remain blank. Overlapping episodes are not counted as independent trials.


## Other visible controls and existing design references

| Control family | Destination or behavior | Existing reference |
| --- | --- | --- |
| Global search and Compare / Compare a peer | Shared search/comparison; inherit the selected instruments and case perspective | Paper p-1S-0: 1NAV-1, 1NLR-1, mobile 5OWS-1; unavailable 5P6D-1 |
| Watchlist/save/undo feedback | Reuse established saving, confirmation, failure and uncertain-effect patterns; bind the correct canonical case effect | Paper p-1T-0: 1TPI-1, 1V82-1, 5RAG-1, 5RP0-1, 5S01-1, 5S90-1 |
| All tools and research launcher | Shared launcher; the case is an optional context payload | Paper p-1R-0: 5LOX-1, 5LW3-1, 5MR6-1 |
| Account, language and theme | Existing account/settings context; localize labels, dates, numbers and accessible names | Paper p-1C-0; R30 dark Chinese sheet is a responsive specimen |
| Open Terminal | Existing terminal route with admissible research context | Paper p-1O-0; no trade ticket or automatic order |
| Open Forex | p-1F-0 owned by the other active session; pass identifiers and return context | Destination binding pending coordination; no Forex mutation |
| Ask Mastermind | Existing assistant entry with the selected case and explicitly admissible evidence | Existing shared shell; no autonomous action implied |
| Tabs, back links and case selector | Switch among the eight route definitions; preserve shared context | R30 route map C01 |
| Map zoom + / − | Bounded local pan/zoom; Fit view restores the initial extent | Route 05 diagram; keyboard labels and focus must remain usable |
| Mechanism node, safety-demand row, evidence/source/relationship actions | I03 with the selected hypothesis or relationship; source detail is a nested receipt view, not a new route | I03 and I01; typed edges distinguish contracts from operating relationships |
| Sliders, numeric fields, Reset and Apply | Local draft, explicit apply, reproducible recalculation; dirty-state handling before navigation | Route 06 and I02; state S05 / S12 |
| Replay step, previous and speed | Advance only admissible observations; pause at the cutoff; reveal uses I12 | Route 07; keyboard-operable controls, reduced motion |
| Saved-case list, timeline, monitor logic and reopen | Open the recorded revision; compare changed evidence; I04 for monitor configuration | Route 08; preserve current and frozen histories separately |

These references prove reusable **design patterns**, not that an API or persistence owner has already been bound. Implementation must inspect the current canonical components and owners. A missing binding stays explicitly pending; do not add a second alert, case or evidence store.

## Responsive and accessibility behavior

At 1440 px, the primary chart or mechanism occupies the wide column and the selected decision occupies the side column. At 768 px, navigation condenses and comparisons retain the critical columns; the tablet example keeps a useful two-column sensitivity/next-action arrangement. At 390 px, metrics become short cards, the mechanism graph becomes an ordered accordion, and the selected evidence opens as a sheet. One mechanism is expanded at a time. Tables use prioritized fields or explicit horizontal exploration rather than illegibly shrinking text.

Desktop popovers are focusable; transient hover-only help never contains the sole route to an action. Modal drawers/sheets trap focus where appropriate, Esc dismisses, and dismissal restores the invoker. Tooltips do not trap focus. Mobile primary controls are at least 44 px; the R30 mobile buttons use a 46 px minimum height. Reading order, keyboard order, names and selected/expanded states must be semantic in runtime components. Color has a companion label or shape. Reduced motion applies to chart/replay transitions. Theme and language changes preserve the case and do not change financial direction semantics.

## Failure and transition acceptance

The native S03 atlas includes stale data, missing hedge input, mismatched horizons, valid empty history, invalid numeric input, paused monitoring, confirmation, invalidation, expiry, initial loading/refresh failure, an empty saved list and unsaved changes. S04 adds unavailable cohort distribution. Shared save references cover in-progress, failed, uncertain and undo outcomes.

Required journey checks:

1. Credit → Scenario → Capital → Evidence → Save → Reopen retains case revision, units, horizon and cutoff.
2. A rate series reused as yield, technical structure and duration sensitivity does not create three independent confirmations.
3. Missing peer data, stale funding or mismatched close conventions cannot confirm a monitor; an independently fresh invalidator still takes precedence.
4. Simultaneous confirmation/invalidation resolves as invalidated; a fifth-close confirmation is evaluated before expiry.
5. A paused data feed does not quietly extend the five-session window. Post-closure evidence enters the audit and does not reopen it.
6. Save timeout uses the canonical operation identity for reconciliation; retry cannot duplicate a monitor. Undo affects the acknowledged saved object, not an uncertain guessed ID.
7. Intraday replay excludes same-day date-only vintages without a verified availability time. Outcome filters stay unavailable before the decision is frozen.
8. Changing FX direction, hedge tenor or buyer currency cannot reuse incompatible quoted costs.
9. Invalid scenario input clears stale computed output and focuses the error. Dismissing an unsaved scenario offers Cancel, Discard or explicit Save.
10. A source correction can update current descendants while the earlier saved revision remains inspectable.

These are implementation acceptance cases, not a claim that end-to-end browser or production tests passed during this Paper task.
