# Commodities · Paper-based visual revamp · 2026-10-22

## Outcome and custody

Current Chairman instruction rejects the shipped Commodities visual design and authorizes polishing the existing Paper design and implementing a complete page revamp. Publication/auth acceptance remains dated evidence; visual acceptance is reopened. This work is not complete until visual, functional, release and real-user-path proof are accepted.

Operation: commodities-paper-revamp-20261022. Repository: mastermindx-market-intelligence/macro. Base: 2148a98367be4239baac6af5bad103b2fb6f78e9. Branch: sol/web-commodities-paper-revamp-20261022. Workspace: /Volumes/Mastermind/agent-workspaces/macro/web/commodities-paper-revamp-20261022. Root owns design decisions, integration and final acceptance; an admitted bounded builder may own the implementation files below. No other worker may write the same paths concurrently.

Protected procedure pin: Mastermind@0454ada03d2c6d3023f0347e713f38b46e1ff629, Skillpack 1.0.1. Current source laws remain governing. This document is design direction and evidence, not a new authority or lifecycle store.

## Verified design sources and exact Paper boundary

Paper file 01M2WGNCX9475G79JRKJTCM08P, page p-L-0:
https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-L-0

- 1HCJ-0: original desktop Overview, strongest market narrative and comparative hierarchy.
- 1HDH-0: light Overview reference; 1HDI-0: mobile Overview reference.
- 6JKF-0 and 6K5V-0: R3 Overview/WTI evidence, functional and semantic reference only; their sparse visual composition is insufficient.
- 21WR-0: North Star cockpit, use only its asymmetric evidence density, never its unimplemented quote/curve/positioning/derivatives/monitoring concepts.

Actual screenshots and original JSX are retained beside this packet under mockups/evidence/commodities-revamp-20261022/references. Example market values are fixtures, not facts to copy.

Paper returned: "Your file is too large. Further changes will result in data loss. Please start a new file." No Paper edits have been dispatched. Source and preview work may proceed; proposed refinements are NOT_APPLIED_TO_PAPER. The existing file is preserved. Safe successor Paper file identity is the remaining canvas gate; no raw open/create/delete or alternate-carrier bypass.

## Art direction and primary question

Primary question: Which commodity moves deserve closer research, and what evidence would support their explanation?

Use the original study's market narrative, visual breadth and comparison hierarchy with R3's honest data contract. Aim for a calm, finished institutional research desk, visibly superior to R3's flat text cards. Preserve the current shared product shell. Do not introduce a duplicate sidebar, change global navigation, or add decorative imagery.

Typography: canonical Inter / theme scale, confident 800 headline, 600-700 section titles, tabular numerical alignment, short readable copy. Use theme tokens for type, spacing, radius, surfaces, ink and motion. No parallel palette or new root token family. Reserve hue for semantic direction, action and evidence state. No colored container edge/rail on any side. Use quiet selected fill, even neutral borders, stronger text and full focus outlines.

DARK TREATMENT: graphite canvas, layered neutral panels with deliberate luminance difference, generous primary headline, restrained semantic ink, chart marks with clear shared zero/scale. Reduce heavy repeated outlines; use hairlines to separate aligned rows. No glow/pulse suggesting live data.

LIGHT TREATMENT: cool research-paper canvas, white primary surfaces, crisp neutral hairlines and controlled existing shadow tokens; stronger typographic separation and lightly raised controls. No translucent dark slates, washed-out gray-on-gray panels, or colored glow. Signed chart marks retain direction inks and visible neutral tracks. Judge light as a separate composition, not merely a palette swap.

Mobile: preserve shared shell, page title and market answer within one swipe; horizontally scroll only the task/asset strips, never the page. Reorder summary before evidence, collapse primary/supporting split into one deliberate reading order, preserve all data through expandable detail. 40px minimum controls. EN/ZH parity, Chinese directional color inversion, reduced motion, keyboard focus and URL state are required.

## Frozen composition by route

### Overview — narrative and market map

Keep the five existing task views. Make tabs a compact, neutral selected-state strip without decorative underlines/edges. Place the page title/date/actions compactly, then the market answer. Hero uses approximately two-thirds narrative and one-third breadth in desktop; mobile narrative then breadth. The headline is the existing deterministic ws.headline, never a mockup string. One short research stance and one primary "Explore the evidence" action; no invented trading advice.

Use existing index return plus breadth as distinct labeled observations. Add an honest proportional breadth graphic with the actual denominator, and a separately labeled count of positive/negative one-month observations if derived. Never call trend, momentum and return counts votes or a composite score. Do not duplicate the same headline count elsewhere.

Retain oil/gold/copper research entry points, but compose them as a refined three-column analysis strip with commodity, prominent signed move, compact explanation and clear next action. Remove large dead space and repeated footer chrome. If adding a return visualization, use actual period returns, not invented time-series points.

Turn Across the complex into a compact visual map of all 17 assets grouped in their existing families. Every asset shows a common-baseline signed bar and exact one-month percentage plus a selection affordance. Shared scale uses the largest absolute finite one-month return across the displayed population; preserve explicit unavailable values with no bar. Empty family space must not dominate: compact rows and intentional family grouping/column flow. Explain the basis once. Data marks may use semantic colors; container edges remain neutral.

### Explore — selected instrument workspace

Retain all 17 selections and URL behavior. Strong selected-commodity header with move/window and concise reading. Bring price evidence up before lengthy physical detail: a primary analytical panel plus narrower interpretation/next-check panel, then physical evidence and explanation controls. Show the actual 5/20/60/252-session returns as a labeled signed comparison graphic/rows, with a shared zero and scale per instrument. These overlapping lookbacks are NOT a chronological series. Keep publisher one-month distinct from 20 sessions.

Trend and momentum are separate concise labeled states. Keep the oil stock/flow and Gold China-premium sections with their complete semantics, dates, units, caveats, provenance and deeper disclosures. Large unsupported empty diagrams are forbidden. Use clear evidence section headers, quiet statistic cells and aligned units rather than a wall of equal cards.

### Relationships — explanation and evidence path

Keep asset selection and selected hypothesis immediately visible. Visually separate the observation, explanation-to-test, supporting evidence and what would disprove it. Use two-column primary/supporting composition on desktop, single reading flow on mobile. Connectors must be neutral and conditional; only actual state can indicate confirmed conditions.

Preserve actual source qualification. Current unavailable/earlier-context chains must not look confirmed, current, or causal. Their absent stages remain withheld. A concise useful unavailability state must say what remains inspectable and offer the existing price/physical/source links. Preserve real rates/relative price/business context and identity-verified company links. Keep advanced receipts and equity screens in intentional disclosures, with usable summaries.

### Compare — purpose-built comparison

Persistent compact selected-asset controls (max four) and one comparison-window selector. Add a prominent real signed-return comparison graphic bound to the existing state; shared scale across finite selected values for the exact chosen window; each row has commodity and exact signed value. Preserve nulls and empty-selection state. Keep the existing accessible table as supporting detail or aligned companion, not the entire design. Window changes, language changes and history restoration update both graphic and table. All-zero values produce an honest zero state without division by zero or fake minimum magnitude.

### Research note — analyst worksheet

Keep the existing form, exact draft validation/import/export and inactive semantics. Compose a clean research document with numbered neutral sections: context/explanation, precise condition, and review/export. Use a narrower supporting evidence/limitations column and a clear export action. Reflect selected commodity/hypothesis/window. Preserve all required fields, threshold ownership, expiry and method copy. No new persistence, alert engine, evaluation, auto-threshold or account-save claim.

## Implementation boundaries

Primary files: templates/_commodity_decision_workspace.html.j2, templates/commodity-workspace.css, templates/commodity-workspace.js and paired site assets/page. Existing engines/data/builders/guard remain owners; do not change data semantics, schema, fingerprint rules, economic state, signal thresholds, source clocks, monitoring or trading authority. Minimal deterministic presentation helpers in the existing workspace module are allowed only if needed for honest chart geometry, with focused tests and no contract change.

Use canonical components (mx-vh, panel, mx-tabset, mx-disc, mx-tbl, mx-empty, gbtn), scoped composition classes. Display charts use the existing illus ChartFrame convention; no new charting library or fabricated historical path. Static signed bars/proportions may use semantic HTML/data geometry. No substantive stylesheet injected by JS. Preserve canonical theme loading, exactly one runtime logo config and shared-shell compatibility.

Keep data-cw hooks, IDs, ARIA relationships, five routes, history, companyReturnHref, shared assistant ownership, retained Advanced analytics, export/import, hashes and safe company identity fields. Avoid hidden DOM duplicates and contradictory labels. All authored UI strings have natural EN/ZH twins.

The review renderer pairs new UI with accepted legacy HTML. Use scripts/render_commodity_workspace_review.py on exact base, never run collectors/full nightly pipeline just for UI. Do not truncate omitted sparse artifacts; materialize only needed paths through the existing helper. Source owner has materialized site and mockups. data remains sparse; read immutable Git bytes or request the correct bounded opt-in.

## Qualification and acceptance

Capture actual implementation, not a detached mock: all five views, desktop1440 and mobile390, dark/light and EN/ZH; include available, partial/unavailable, empty compare, and focus/selected states. Keep a compact representative contact sheet for independent taste review plus exact screenshot references in the evidence manifest. Inspect screenshots for hierarchy, excessive blank space, legibility, chart labels, overflow and actual click paths. Do not green a screenshot matrix without visual judgment.

Run existing meaningful commodity Python, Node/DOM and Chromium checks; add only discriminating tests for new geometry/state behavior (positive/negative/null/zero, compare window/language/history). Run design-system enforce-added, runtime-style-injection, paired asset/publication checks appropriate to the changed files. Do not weaken guards or broaden tests to unrelated data collectors.

Independent source/visual review is separate from the author. Root must inspect the integrated result before release. CI, merge, normal covering-render, exact serving asset cohort and actual browser user path remain separate acceptance facts. Paper remains NOT_APPLIED until a safe successor destination is provided and the real canvas is updated/visually verified.

## Durable references

Previous accepted publication: Macro PR9878 comment6332067001; observer shutdown6332093988. Macro9878/9926/9950/9961 and Terminal1092 merged. Existing observer remains stopped; do not revive it for this new wave. New design work must not rewrite historical publication evidence or reuse merged branches.

## Execution reconciliation · first implementation attempt

Fabric run commodities-revamp-build-20261022-01, root commodities-paper-revamp-20261022, controller91891 terminated rc75/admission. Exact retained response SHA256 1bea64e73d2fb3563c9874a0a08f2503f3ea3a8f2d316fdf9e166d5a3bcc313f: REMOTE_SUB_ADMISSION_REFUSED, reason host_temperature_at_or_above_limit on ubuntu1. No retry or reroute of that worker launch. The adapter does not assert execution_absence_proven; preserve that narrow field. The original controller is terminal, no worker result/source change is claimed, and the separately owned Studio source files were reread unchanged before direct work. Direct principal source work uses NO_ELIGIBLE_PRE_EFFECT_WORKER / PRINCIPAL_JUDGMENT in its existing isolated workspace; independent review remains owed. This does not bypass the Ubuntu host's worker admission or establish that the worker ever started.

## Qualified implementation and source publication

Draft PR10038 contains the implemented redesign and durable evidence. Independent source-delta review passed; representative visual review found no blocking composition defect in five inspected states. After main advanced, the sole generated-page conflict was resolved against64ef513 with its newer published payload unchanged byte for byte. All five views were recaptured, and focused integrated renderer/DOM/browser/publication checks passed. Detailed identities, actual review scopes and remaining production/Paper boundaries are recorded in mockups/evidence/commodities-revamp-20261022/qualification.json and reviews.md. The unsafe Paper file remains unchanged.
