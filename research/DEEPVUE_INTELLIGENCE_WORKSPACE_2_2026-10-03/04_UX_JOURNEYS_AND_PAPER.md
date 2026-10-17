# Intelligence Workspace 2.0 — UX system, journeys and Paper assessment

Date: 2026-10-03. This is a proposed experience architecture grounded in the current owner census and inspected Paper design. The market questions below are **illustrative research tasks, not claims about current prices, market regimes, leadership or investment opportunities**.

## 1. Product information architecture

Use three distinct nouns consistently:

**Investigations** are saved research questions. **Layouts** are saved visual arrangements. **Theses** are authored, versioned beliefs. The current menu may retain a familiar “Workspaces” entry, but its sections and actions must explain which object is being opened or saved. Do not rename all three to Workspace and hide the difference.

Primary entry points:

* Global Investigations library: recent, open, concluded, archived, shared and needs-review filters.
* Existing Analysis, Company Intelligence, Theme/Market Ontology, Prophet, Options and macro surfaces: **Investigate this** or **Add to investigation**.
* Existing chart layout menu: **Save layout** remains; **Start investigation from this layout** is separate.
* Existing Thesis: **Investigate this thesis**, linking the exact current version rather than copying its statement into a new owner.
* Brain: **Save this question** creates explicit research intent; **retain this analysis** references the historical run; neither silently creates an alert or a Thesis.

The library's last-reviewed time is not a source-freshness clock. A needs-review indicator means an explicitly defined change/qualification condition, not that AI has decided the thesis is invalid. Successful empty inventory, denied access, load failure and unknown state have different screens.

## 2. The investigation frame

### Above the fold

The header answers: **What am I investigating? What scope/time am I in? What changed since my last review?** Show the saved question, subject chips, temporal mode and a compact baseline/change summary. Separate “Saved” from “Reviewed”; show any unresolved write outcome prominently.

The initial content is an orientation card: previous authored belief or “No thesis recorded,” last reviewed evidence basis, most consequential qualified changes, unresolved contradiction and next observation. It is a projection over references, not a new AI-written canonical summary. A generated recap is explicitly labeled and can be unavailable without destroying orientation.

### Research lenses

Use a modest lens set: **Overview, Evidence, Hypotheses, Scenarios, History**. Layout/chart tools remain available within these lenses, not as six additional permanent header layers. Brain is a contextual companion drawer/pane with visible scope rather than a second navigation hierarchy.

Desktop can show a central research canvas and a right evidence inspector. The library rail is collapsible. Default templates mount two or three useful analytical widgets, not all available widgets. A widget catalog states subject support, input/output context ports, historical capability, source owner and approximate resource class before Add.

### Component grammar

| Component | Purpose | Required states |
|---|---|---|
| QuestionHeader | Research intent, subject scope, lifecycle, saved/reviewed state | Draft, saved, conflict, unknown write, archived |
| ResumeCard | Recover prior belief and next step | No baseline, reviewed baseline, changed evidence, historical view |
| ContextChip/GroupControl | Show what a widget follows | Linked, local, pinned, unsupported, collision |
| EvidenceCard | A qualified reference, not an invented fact | Current, pinned, stale, missing, rights-blocked, historical unavailable |
| ChangeReceipt | Explain a meaningful or structural difference | Added, revised, corrected, incomparable, qualification changed |
| HypothesisCard | Versioned authored interpretation | Draft/proposed, current version, historical, invalidated/archived |
| ArgumentRelation | Supporting/weakening/discriminating interpretation | Human-authored, AI-proposed, accepted, unresolved |
| ScenarioPanel | Explicit assumptions over a named basis | Base, edited assumptions, calculated, unavailable, non-reproducible |
| BrainScopeReceipt | Show inputs and limits of an answer | Included, excluded, expanded sources, incomplete, historical |
| SourceInspector | Verify lineage and retrieve owner content | Exact field/record, pending span lineage, denied, removed |
| SaveOutcomePanel | Recover safely from uncertain writes | Applied, replayed, conflict, rejected, pending/unknown |
| SharePreflight | Explain recipient-visible scope | Full permitted view, redactions, blocked refs, confirmation |

Do not make a green status mean all of readable, comparable, answerable, current and correct. Separate these dimensions in plain language. Use explicit missing-baseline copy: **No reviewed baseline yet. Changes cannot be compared.**

## 3. Responsive and accessibility behavior

**Desktop:** question/change frame remains visible while navigating evidence. A selected receipt opens alongside the analysis. Charts have local context controls and time labels; a historical panel cannot inherit the live header's time label. Layout editing is a deliberate mode and never changes Thesis meaning.

**Tablet:** reduce to a primary content region; library and evidence become separate sheets with focus return. Persist which evidence reference is selected, not the desktop inspector's pixel width. Do not keep multiple heavy offscreen charts actively rendering merely to simulate desktop continuity.

**390px and 320px:** question and temporal mode come first, then Resume/Changes and one selected lens. Inspector/detail uses a full-screen route or sheet with a clear back action. Scenario comparisons become stacked base/alternative/delta cards. Hypothesis comparison uses successive cards with consistent labels instead of a squeezed matrix. Chart/table panning is contained locally; prose and controls reflow.

Desktop/tablet/mobile are views of the same research revision. Device-specific pane arrangements are subordinate layout preferences, not divergent questions or duplicate investigations. Navigation back to the original source preserves a typed return reference rather than reconstructing context from a long URL blob.

Proposed interaction requirements: all important actions keyboard-operable; meaningful focus order and return; no hover-only linking; text alternatives for semantic color; readable loading/error announcements without flooding assistive technology; reduced-motion support; at least 44px touch targets as a product target; 200% text-resize and 400% zoom/reflow tests; EN/ZH wrapping and long identifiers. These targets do not claim current conformance. WCAG reflow has limited two-dimensional exceptions, not a whole-application exemption. [External L10 in 02_RESEARCH_AND_THESIS.md]

Use existing Terminal typography, spacing, interaction tokens and dark-mode doctrine. Paper light studies are not permission to expand the production theme scope independently. Semantic warning/contradiction color should be restrained and supplemented by text, not a decorative accent system.

## 4. Common journey rules

Every journey below uses the same durable identity and owner boundaries. Creating an investigation is explicit. Captured visual context is previewed. Evidence references preserve owner identity and rights; user interpretation stays separate. A save preserves the question even when AI fails. Reopen reads current qualified evidence without revising prior beliefs, advancing the reviewed baseline, changing portfolio membership or creating alerts.

Sharing and forking always perform rights checks. Closing a question records an authored conclusion or an explicit unresolved outcome, not a synthetic trade result. Archive hides active work without deleting references/history. Any actual watch/portfolio/trade operation is separately confirmed through its existing owner.

## 5. Seven end-to-end journeys

### J1 — Why is NVDA weakening despite positive AI-theme breadth?

**Create/capture.** From the chart or Company Intelligence, choose Investigate. Preview the security, referenced AI theme, timeframe and available theme-membership vintage. The question is saved without assuming that the premise is true; the first task is to verify price weakness and the definition of breadth.

**Compose/evidence.** Start with price/relative-strength, theme breadth and company-event context. Security charts follow group A; theme breadth follows group B. Selecting a peer should not replace the question's primary subject. Add exact receipts for price period, breadth denominator, earnings/catalyst records and relevant source documents.

**Brain/contradiction.** Brain distinguishes observations from possible causes such as concentration, valuation or company-specific news. Competing explanations become proposed links to separate Thesis versions, not facts. A breadth measure whose universe or dates differ is incomparable, not evidence that the source is wrong.

**Scenario.** The analyst creates a sensitivity recipe over an identified baseline—such as different relative-performance or valuation assumptions—only when the relevant calculator is admitted. Otherwise assumptions remain inspectable text/typed inputs with calculation unavailable. No price forecast is fabricated.

**Save/live/reopen.** Save the reviewed evidence basis and an unresolved test. Later reopen shows new source revisions, changed breadth definition or company events separately from price changes. Historical belief remains visible. Current synthesis explains which cited inputs changed or says that the explanation remains uncertain.

**Collaborate/close.** Share a permitted revision with a teammate; inaccessible research is redacted without leaking its contents. A fork can test an alternative interpretation. Conclude only when the analyst records the answer and limitations, or leave open pending a discriminating observation. No linked chart move can invalidate the Thesis automatically.

### J2 — Is optical networking taking leadership from memory?

**Create/capture.** Start from Theme/Market Ontology with two owner-resolved subtheme references, membership vintages, horizon and a defined leadership measure. Do not convert them into two arbitrary ticker lists or treat current membership as historical membership.

**Compose/evidence.** Use comparison widgets for relative performance, breadth/participation, earnings revisions or other qualified owner metrics. The two groups retain independent subjects while sharing an explicitly linked time range. Add witnesses through source receipts, not copied table rows.

**Brain/contradiction.** Ask for evidence that would distinguish durable rotation from one concentrated stock move. Brain must disclose coverage and return competing explanations. Strong price momentum with weak participation is tension between indicators, not automatically a logical contradiction; the interpretation is attributed.

**Scenario.** Compare a user-specified exclusion of a dominant constituent or alternative membership vintage only if a deterministic owner query/calculator can reproduce it. The baseline stays unchanged and the output states the selected cohort and calculation.

**Save/live/reopen.** Preserve the definition of leadership and the reviewed membership/evidence basis. On return, separate constituent changes from metric changes. A newly admitted constituent cannot silently improve historical breadth. Missing vintage data makes the historical comparison unavailable.

**Collaborate/close.** Share the question and qualified cohort/query references; fork to study a different horizon. Conclude as supported, unsupported or unresolved according to the analyst's recorded criteria. A resulting saved screen or watchlist update is a separate owner action, not a side effect of the conclusion.

### J3 — Are we entering a different real-rate/liquidity regime?

**Create/capture.** Begin with economy/regime references and a precisely stated horizon. The save dialog exposes nominal versus real rates, expected inflation definition and the liquidity proxy under discussion. Unsupported regime identities remain unbound intent rather than invented classifications.

**Compose/evidence.** Add owner-qualified rate, inflation, liquidity and market-response views. Each shows observation period, release time and vintage. A daily market series and monthly economic series are not presented as synchronized observations merely because their panels share a date range.

**Brain/contradiction.** Brain compares at least two mechanisms and points out missing discriminators. An inflation revision can alter an estimated real rate without implying a new contemporaneous policy action. Conflicting definitions and revised data appear before narrative synthesis.

**Scenario.** Store explicit rate/inflation/liquidity assumptions and method references. A deterministic transformation may be calculated; causal macro forecasts require a qualified model and remain forecasts. No general macro probability engine is invented for this screen.

**Save/live/reopen.** Pin the then-known release vintages and the analyst's interpretation. Reopen distinguishes new releases from corrections to old periods. Historical replay excludes data first known after the cutoff; revised-history analysis has a separate label and request scope.

**Collaborate/close.** A shared fixed revision allows colleagues to inspect the earlier belief without freezing current source rights. Fork for an alternative mechanism. Conclude with stated uncertainty or retain the question for the next release; a calendar/watch reminder is separately created through its existing owner.

### J4 — Is this earnings selloff a temporary dislocation or a thesis break?

**Create/capture.** Start from a generation-pinned Company Intelligence event and an existing Thesis version. Preview the fiscal event identity so switching earnings periods cannot leave an old receipt attached under a new event label.

**Compose/evidence.** Reuse Brief/Transcript/History/Topics/Sources, price reaction and a small relevant fundamental set. Transcript navigation goes through the existing archive reader. Field-lineage receipts are usable but explicitly distinguish pending paragraph/span attribution. [I18]

**Brain/contradiction.** Compare the prior Thesis's falsifiers with reported observations. Brain can propose that a criterion was met, but cannot mark the Thesis invalidated. Separate management statements, normalized reported facts, deterministic changes and AI interpretations.

**Scenario.** Build base/alternative assumption recipes only for supported financial calculations. Record the report vintage and any assumptions about margins/growth; do not replace reported values with modeled values. An unavailable calculator yields a clearly uncalculated scenario, not a guessed target.

**Save/live/reopen.** Save the event/reference vector and the question even if transcript retrieval or AI is degraded. On return, show source corrections, transcript availability and new evidence. Preserve the old belief and its original source basis for fair retrospective assessment.

**Collaborate/close.** Share with source-rights preflight. A colleague's Thesis amendment uses that owner's proposal/revision pathway rather than overwriting the author's statement. Conclude by explicitly retaining, revising or invalidating the Thesis through its owner; any portfolio action remains separate.

### J5 — What would invalidate this Prophet candidate?

**Create/capture.** From Prophet, bind the exact candidate/fire/evaluation identity, generation, horizon and readiness state. Do not bind only a ticker and later show a different candidate as though it were the original.

**Compose/evidence.** Add the candidate rationale, qualification/readiness, price/participation context and existing outcome ledger views where admitted. Missing fields remain missing. Preserve shadow status and any producer authority ceiling.

**Brain/contradiction.** Ask for discriminating evidence and possible invalidation conditions, separately labeling producer rules and user-authored criteria. Brain may suggest a criterion; it does not originate a signal, modify selection policy or promote shadow evidence into an approved strategy.

**Scenario.** Evaluate only supported rule/condition previews against specified inputs. A scenario is not a new backtest and cannot use future outcomes to rewrite the candidate's initial rationale. Forecast probabilities require an owner method, not a model's confidence language.

**Save/live/reopen.** Save the original candidate vintage and reviewed criteria. Returning later shows evidence, readiness or outcome updates in separate sections. A completed outcome is historical evaluation, not proof that an earlier unqualified setup was justified.

**Collaborate/close.** Share a fixed candidate investigation with permitted evidence; forks preserve lineage and independent user hypotheses. Explicitly create a watch only through the alert owner. Close as reviewed/invalidated/unresolved while leaving the candidate/fire lifecycle untouched.

### J6 — Is options structure warning against the price-action setup?

**Create/capture.** Begin with underlying, optional contract/expiry, session date and price-action hypothesis. Preview the exact Options producer context rather than guessing expiry from the active chart.

**Compose/evidence.** Add price, exposure/surface and flow views using existing owners. One replay owner drives the admitted temporal group. Current EOD-only or live-only views disclose their limits; an archived session's last frame is not “live.”

**Brain/contradiction.** Separate deterministic topology from dealer-sign-dependent estimates, coverage and flow interpretation. A contrary exposure estimate is evidence to examine, not an automatic trade veto. Brain must carry the sign convention and truncated strike-window disclosure into its answer. [I20,I21]

**Scenario.** Reuse the existing spot/volatility/time scenario calculation and label all units and conventions. Changing the dealer-sign assumption creates a distinct recipe/output, not a revised current fact. Show sensitivity and unknowns rather than invented odds of a pin or reversal.

**Save/live/reopen.** Pin the chosen session/input receipts, expiry and method version. On return, distinguish expiry roll, new session and source revision. Do not silently substitute today's chain into a saved historical scenario.

**Collaborate/close.** Share the permitted research revision; a fork can test another expiry or assumption set. Closing records what the analyst learned and whether the price hypothesis changed. No options order, position change or alert is created by replay or reopening.

### J7 — Has the evidence supporting my Japan policy-divergence thesis changed?

**Create/capture.** Start from R10 or an existing Thesis. Preserve country pair, date window, currency/measure definition, policy or market rate definition, saved question and exact Thesis version. The current saved-view filter serializer is not used as a shortcut.

**Compose/evidence.** Use the Paper question/evidence-refresh pattern with country comparison, source/release/observation clocks and explicit coverage. A domestic 10Y–2Y curve is not a cross-country policy spread. Required aligned periods/definitions must exist before the comparison is answerable.

**Brain/contradiction.** Brain receives the comparison definition and missing evidence. If two of three cards qualify but the key country comparator does not, it states incomplete analysis rather than claiming a direction from the available subset.

**Scenario.** User assumptions about future policy paths are separate from sourced current rates. Calculations label signed spread and absolute divergence separately. The -3.0 to -2.5 pp test yields +50 bp signed change and 50 bp narrowing of absolute divergence; no ambiguous widening label.

**Save/live/reopen.** Save a reviewed baseline only after explicit review. A week later, the old Thesis and its basis remain; new releases/corrections appear in the change account. Missing baseline means unavailable comparison, not “nothing changed.” Current AI synthesis can differ without overwriting historical user analysis.

**Collaborate/close.** Share a fixed review or a live head deliberately. Fork for a different comparison definition. Close or retain through the Investigation lifecycle, while Thesis revision and any watch/calendar actions use their separate owners. This journey is one universal template, not the architecture for every investigation.

## 6. Paper assessment: what was actually inspected

The exact current design resolved to **International Markets · R10 · Current Build**, file `01M3P1TW5Y3XWQC37ADDS8K5AG`, page `p-5-0`. The run read board `6EG-0`'s structure and all 129 text nodes, viewed desktop `5ZJ-0`, and viewed narrow `6IO-0`. Other tablet/mobile/light/ZH boards were enumerated but not all visually inspected. No edits were made; no screenshot is treated as a runtime accessibility test. [I26]

### Retain universally

The question-first orientation, distinct inventory/evidence/write states, explicit baseline, source clocks, qualification before answer, source changes before refreshed narrative, visible save/readback and safe uncertain-write handling are strong universal primitives. Responsive continuity should retain the same research object and selected reference. Reopen remains read-only with respect to alerts, retries and research baseline.

### Retain only as domain behavior

Country pair, currency, policy-measure selection, macro release alignment and signed-versus-absolute spread interpretation are R10/International Markets semantics. They become a template and owner adapter, not universal fields forced onto company or options investigations.

### Redesign or extend

The slogan about not freezing answers needs a historical-belief complement: **Preserve what the analyst believed and why; qualify what the evidence says now.** Do not store a rendered current answer as timeless truth, but do not delete human-authored conclusions or their evidence basis.

Add competing hypotheses, explicit argument relations, scenario assumptions, owner-version history, context-link receipts, historical capability limitations, revision/live-head sharing, transitive-rights prevention and a layout-versus-investigation distinction. The current design correctly exposes that `rms_saved_view` cannot persist the rich question payload; production must fix the contract rather than reproduce the mockup against a lossy endpoint.

Desktop's changed-first layout is a useful baseline. Avoid turning the evidence rail into a wall of source metadata: lead with the research consequence, then expose exact provenance. The 320px design provides a readable direction, but implementation must independently prove keyboard, focus, text resize, translation and long-content behavior.

## 7. Required new board/state set before each affected implementation wave

These are proposed boards, not claimed existing Paper artifacts. Do not create a new design file merely for convenience; re-inspect and use the accepted product design home.

| Board family | Required states | Unlocks |
|---|---|---|
| IW2-A Library and optional creation | Layout-only vs Investigation, empty/read failure, create from chart/Thesis/source, free question | P1 |
| IW2-B Save/reopen vertical slice | Private save, exact readback, cross-device reopen, no baseline, AI unavailable, write unknown/conflict | P1 |
| IW2-C Context laboratory | Linked/local/pinned, two subjects, type rejection, collision, duplicate-symbol/MTF exception | P2 |
| IW2-D Evidence and argument | Qualified/current/pinned, correction, rights change, missing comparator, competing hypotheses | P3/P4 |
| IW2-E Historical and scenario | Live vs then-known vs revised history, unsupported widget, assumptions vs facts, non-reproducible recipe | P5 |
| IW2-F Sharing and forks | Layout vs Investigation, fixed revision vs live head, redacted source, revocation, private fork, attribution | P6 |
| IW2-G Cross-product journeys | Company, theme, macro, Prophet and Options entry/return paths with typed refs | P7 |
| IW2-H Mobile/accessibility | 820px, 390px, 320px, 200% text, keyboard/focus, EN/ZH, loading/empty/error/unknown | Every wave |
| IW2-I Review/close/history | Belief change, unresolved conclusion, archive/reopen, old evidence unavailable | P4/final |

Board review must compare rendered implementation at the same viewport, state and source fixture, not merely similar colors. A design state is accepted only when its copy does not claim more source freshness, temporal validity, write certainty or user authority than the underlying contract supplies.

## 8. UX acceptance definition

A novice can save a question without learning graph terminology or creating a Thesis. A returning analyst can identify the old belief, new evidence and next test before opening Brain. A specialist can inspect exact inputs, context links and temporal limits without those details burdening every routine read. The interface is useful while AI is unavailable, on a phone, after a source revision and after entitlement changes. These are proposed outcomes to prove through the build and user-evaluation program—not achievements of this document.
