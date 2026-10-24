# R32 — completed design and executable reference

**Status:** the native Paper design and its offline interaction reference are complete for review. This document extends the R30/R31 contracts without adding product routes. Production data, retained research, compound alerts and forecast qualification remain explicit integration work in their existing owners.

## Review the result

- [Bonds in Paper](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1H-0)
- [Cross-Asset in Paper](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1E-0)
- [Working reference](reference/index.html): download and open this single HTML file in a browser. It needs no server or external assets.
- [Feature and implementation scorecard](feature-scorecard.md)
- [Rendered journey results](verification/journey-results.json) and [analytical results](analytics-results.json)

The product still has eight destinations. Fifteen core tool families use detail drawers, sheets and expanded states. Seven atlases hold implementation detail. Four standalone responsive boards and three embedded mobile specimens show the relevant adaptations. Twenty-eight earlier artboards remain in the existing archive; they are not additional navigation destinations.

## The decision hierarchy

The default experience answers: **what changed, which question matters next, and which observation could change the view?** The selected outlook precedes the sensitivity calculator. Users can inspect a mechanism, challenge it, apply a typed addition and return to the same case.

The native R32 receiving state is visible in the Case Workspace and S07. The offline reference starts with an empty local draft so reviewers can experience the actual apply journey. Its implementation-review control can load the two-addition native specimen. These are deliberately different starting states of the same flow.

The desktop/reference navigation is:

| Route | Decision | Useful continuation |
| --- | --- | --- |
| 01 Bonds desk | Read rates, credit and funding together | Curve, issuer or buyer lens |
| 02 Curve & duration | Separate yield drivers from price sensitivity | Structure, curve shape, auction check |
| 03 Credit & issuers | Separate repricing from actual financing consequences | CDS conventions and dated obligations |
| 04 Capital competition | Compare the same buyer’s eligible alternatives | Hedge, issuer funding, transactions and repo |
| 05 Transmission | Compare explanations and missing links | Evidence, outlook and contrary episodes |
| 06 Outlook & scenarios | Read the next test and stress explicit assumptions | Local draft, price conditions and save admission |
| 07 Compare episodes | Freeze a decision before exposing outcomes | Filters, fingerprint and model evidence |
| 08 Saved cases | Inspect retained scope and meaningful changes | Exact revision review and the local draft |

The surrounding product shell, account features, instrument search and the Forex workspace retain their existing owners. Their selectors do not fabricate additional data or unsupported functionality in this bounded reference.

## Conditional outlook and causal interpretation

R32 presents three nonexclusive continuation paths: rate relief, supply pressure, and a funding interruption. Selecting a path updates its consequence, next discriminating check and rule-review status together. Existing additions survive the selection.

The explanation drawer compares growth repricing, buyer substitution, issuer-specific risk, and funding stress. A Treasury bid alongside weaker AI credit is compatible with several explanations. The buyer-flow example does not identify the source of the Treasury purchases. The funding fixture is orderly, which is counterevidence to a contemporaneous liquidity squeeze. An issuer-only alternative prevents a single CDS move from automatically becoming a system-wide explanation.

Three claims remain distinct:

1. **Market-test event:** did the authored conjunction match at an eligible cutoff?
2. **Later continuation:** did later observations challenge the expected path?
3. **Mechanism:** what evidence actually distinguishes the proposed cause?

The matched-event → reversal specimen preserves the original event and records the later interpretation separately. Shared source families describe lineage, not statistical independence. No confidence vote, likelihood percentage or empirically validated forecast is manufactured from the number of displayed indicators.

## Typed additions and edit preservation

Each addition retains a stable local key, kind, title, source, origin, period, relevant instrument/borrower/horizon, and its typed payload. Reapplying the same key replaces that addition instead of duplicating it. The visible draft provides Inspect, Remove and Undo.

The reference separates the applied assumptions from pending main-page inputs and from unapplied tool forms. Route navigation preserves the pending main-page fields. Nested tool navigation preserves its form values and dirty state. Explicit discard clears only unapplied tool edits; applied case contents remain.

Application validates context before clearing a tool form. A rejected rule or cash scenario keeps the entered values and returns the actual mismatch reason and source tool. A 20-session case cannot silently consume the fixed 1–5-session rule. The preserved inactive rule remains inspectable with its original thresholds.

Applied rule, curve-shape and hedge values are derived from their active additions. Removing or undoing an addition restores the corresponding effective calculation. Applying parallel assumptions explicitly replaces an active shape addition. The history also records owned assumption/context changes so unrelated pending edits remain separate.

## Calculation behavior

The reference uses deterministic, declared sensitivities from the existing fixtures:

- Treasury parallel price approximation: `100 × (−D × Δy + 0.5 × C × Δy²)` with decimal yield changes. Duration 7.8 and convexity 64 give +1.97% for −25 bp and −1.93% for +25 bp.
- Corporate benchmark and spread effects remain separate. Policy −10 bp plus premium +2 bp gives benchmark −8 bp. Rate duration 5.5 gives +0.44%; spread duration 4.7 with +40 bp gives −1.88%; combined −1.44%.
- Curve shape uses `−Σ(KRD × shock_bp) / 100`, displayed as percent. The four-node example produces −0.276%. It excludes convexity and does not reuse scalar convexity for a curve twist.
- Shape application updates the Treasury result and makes the corporate result unavailable until a compatible corporate key-rate vector exists. Native S06 includes this state. It does not silently keep a parallel corporate result under a nonparallel scenario.
- Current annualized hedge cost is an explicit assumption. Treasury 5.10% less 3.60% gives an indicative 1.50%; future rolling costs remain open.
- Issuer currency funding is a same-borrower/tenor illustration. It is separate from an investor’s hedged yield.

Blank, malformed and incompatible inputs produce an unavailable calculation. Missing is never zero. The reference is a price-sensitivity illustration, not a promised return or a funding/default forecast.

The Parent A cash schedule is an explicit synthetic example with a separate borrower identity. It shows payment financing need, buffer need and cash timing. A late $900m draw can produce $710m projected ending cash while leaving $190m unfunded at the earlier payment cutoff. Adding that result to CoreWeave is rejected.

## Rule evaluation and later evidence

The default authored rule requires all three conditions at an eligible close: 10Y below 5.08%, the arithmetic mean OAS change of the frozen 12-peer cohort at least +15 bp, and current orderly funding. Fresh 10Y above 5.22% or current funding stress invalidates first. The fifth close is evaluated before expiry; pauses do not extend the window.

The UI previews current, matched, issuer-only, stale, missing-peer, invalidated, fifth-close, expired, late-publication, later-reversal and corrected-input fixtures. A current +11 bp peer mean and five widening peers are separate facts. Rounding does not determine threshold outcomes.

Every relevant evaluation retains a copy of the authored rule. Later interpretation and correction use that frozen rule, including custom thresholds. A review must be later than the event to describe continuation. Closed events are not reopened; corrections preserve the original record and create a separate revised interpretation without retrospective notification.

These are deterministic fixture tests. Production eligibility, session calendars, entitlements and freshness must come from qualified source owners. The current Alerts owner does not admit the complete compound rule; activation remains unavailable. Splitting the conjunction into separate alerts does not satisfy this contract.

## Retention and replay

The reference makes **no API calls and has no persistent store**. It creates in-memory demonstration receipts only. Reloading or closing the tab removes the draft and demo record.

The demonstrated retained scope is question, next check, admitted subject reference and horizon. Evidence charts, additions, scenarios and monitor rules are explicitly excluded. The reopened question is rendered from the receipt payload alone; local excluded contents remain visibly separate.

An uncertain result retains the original operation and payload. Recovery consumes that operation’s receipt instead of issuing a fresh save. Exact-read failure preserves the requested revision and never substitutes latest. Conflict keeps the question, next check and case additions; returning to the form restores the submitted text. A complete-case revision-3 comparison remains a clearly labeled future-capability specimen.

Replay keeps future observations out of the displayed chart until a hypothesis and its cutoff are frozen. Subsequent edits belong to the working view and do not rewrite the frozen record. The response fingerprint uses explicitly synthetic 1D/5D/20D values. Historical mechanism references are separate from a qualified analog model.

## Accessibility and responsive proof

The executable reference was exercised at 1440, 1024 and 390 pixels. Main pages avoid horizontal page overflow; eligible comparison tables scroll locally. Phone signal cards use a compact grid and related-route tabs scroll horizontally. The mobile navigation has an internal close control and Escape return.

Tool sheets use a named modal, a reachable close button, an internally scrolling flex body, visible focus and explicit first/last Tab wrapping. Escape returns to the invoking control. Labels keep units visible. Hover information is also available through keyboard focus, Enter and tap. Conditional outcomes include words, not color alone.

The verification covers this offline DOM reference. It is not a production WCAG audit, screen-reader matrix, touch-device certification or validation of all chart-library keyboard behavior. The native scorecards retain those component-level implementation requirements for the production team.

## Build and reproduce

From this directory in the repository:

```sh
node build-reference.cjs
node test-analytics.cjs
node test-journeys.cjs
```

The builder uses the current parent manifest, token snapshot, R30/R31 fixtures and 21 JSX exports. During authoring it also accepts a local `source-input.json`; that redundant intermediate is not part of the handoff. The output is `reference/index.html`.

The UI test needs Playwright and a compatible Chromium executable. Set `MMX_CHROMIUM_PATH` to an installed executable if Playwright’s default browser is absent. The tested browser was Chromium 151.0.7922.34. The harness aborts HTTP(S) requests and reads only the local artifact. No project data is uploaded during verification.

## Production continuation

Reuse the pinned owners in [R31 source bindings](../r31/source_bindings.json). Extend Investigation v2 admission and exact resolvers for typed bond evidence and scenarios. Extend the existing Alerts schema, evaluator, dry-run and receipts for the complete conjunction. Bind entitled instrument/CDS observations, transaction provenance, exact payment schedules, legal cash pools and compatible sensitivities. Qualify each empirical target and horizon using point-in-time data, out-of-time evaluation, dependence-aware sample treatment, calibration and abstention before showing likelihood.

Those are explicit production dependencies. No deployment, database mutation, live research save, notification, trade or calibrated forecast was performed by this design/reference delivery.
