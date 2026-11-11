# Alert Center V2 — product and implementation freeze

Operation: `MMX-ALERT-CENTER-V2-ASTRA-20260908`.
Owner: Sol / Astra, directly commissioned by Chairman Chris in the current conversation.
Status: design frozen for the bounded investigation-workspace slice; not a shipped-product claim.
Procedure: Mastermind `686af274d8ae1558f3f3ae35e0b3aae68be80a01`, Skillpack 1.0.1.
Implementation base: macro `7692303dcc785c8af7f4438ffd88e91a7e9b0be5`.
Source carrier: `claude/alert-center-v2-astra-20260908`, own isolated sparse Mac worktree.
Figma: https://www.figma.com/design/QO3CthsB5KzPVKdgfcVPMI (editable design, not runtime authority).

## Outcome and thesis
A research user should identify the important changes within 10 seconds and investigate their evidence within a minute without losing the queue.
The machine job is to expose the existing cross-domain evidence with source identity, real event clocks, validation limits and correction-safe references intact.
The moat is useful cross-domain investigation, not notification volume, ornamental scores or an invented trading recommendation.
Completion requires the real assembler -> shared renderer -> browser journey, not merely this document or a Figma file.

## Archaeology and disagreement
The base snapshot contains 60 ranked alerts, including 45 alternative-data rows. The source readers report 1,206 firings across 12 feeds before grouping/caps.
A missing source in the capped list does not mean that source has no evidence. Full investigation must not be limited to the notification-oriented top 60.
Existing broad storyline categories are taxonomy, not proof of a coherent situation or independent confirmation.
The stress category even contains a historical 'Copper risk turned Calm' event; category counts must not become a fresh directional market verdict.
The old six-day-old Bitcoin firing can still receive an act-tier priority. Attention ordering is not current condition verification or trade authority.
The public HTML was HTTP 200 at 2026-09-09T11:32:36Z, SHA256 `3648ca4d443a2055e53d327b7d65a566f9918371c0ddb0d573d9b5df212d7338`.
The two public JSON endpoints returned 401. Repository snapshots and fixture/browser checks are not authenticated production proof.
Baseline sparse tests: 111 pass, 4 fail from absent real-data inputs, 1 skip. Preserve that distinction; do not weaken tests to manufacture green.

## Selected approach
Reject a cosmetic reskin: it retains source starvation and the long-card scanning tax.
Reject a new alert service/database: it duplicates existing identity, assembly, preferences, delivery and publication ownership.
Select a source-grounded investigation workspace inside the existing assembler, Jinja template and static publication plane.

## Experience contract
One calm header answers what to investigate, with the New York board day and a visible missing-evidence caveat when needed.
Now shows the existing top-ranked queue, initially eight rows; Signals exposes the complete grouped population, with explicit counts and incremental display.
Situations contains only specific subjects with at least two distinct alert types. Generic source names, broad story categories and shared generic links do not join unrelated entities.
A situation is a deterministic evidence bundle, not a causal claim, forecast or independent confirmation. It inherits no stronger authority than its individual evidence.
History exposes actual logged firings, not interpolation between the first and latest event. Recurrence never implies continuous persistence.
A selected signal opens an evidence inspector with source link, full text, clock provenance, measured validation if present, attention breakdown and observed history.
Search and source/priority/story/recurrence filters combine with AND. Selection and task state are shareable, reloadable and keyboard accessible.
Legacy hash keys `sev`, `cl`, `q`, `s` remain supported. Unknown values and malformed percent encoding never crash the page.
No read/saved/mute/delivery control is simulated. Account preferences and outbox work remain with their existing owners.

## Intelligence and authority freeze
`build_triage` remains the only assembler. The existing `alerts` array, IDs, order, caps, scores, severity and outbound-push inputs remain unchanged.
Add `explorer` as a pure projection over the already-enriched population and raw records inside the same build. No extra reader, store, registry or scheduler.
`explorer.signals` retains existing canonical alert IDs. A situation is a derived view anchored to a member alert, not a new durable entity identity.
Only explicit source subjects can group. Cross-source ticker aliases, inferred relationships, LLM narrative and independent-source claims are out of scope until canonically grounded.
History is bounded and announces truncation. Exact canonical event dates/instants are preserved; unknown event time stays unknown and future-dated firings stay quarantined.
A missing source is not zero. Source-read status is not a producer freshness guarantee, and an old last firing does not by itself mean a broken feed.
Correction replaces the build projection from its source. No stale browser cache may restore removed evidence as current truth.
Numeric hit rates, IC, DSR and sample sizes are shown only when finite and present; zero is a real value. String 'engine' is not boolean backtested proof.
The old pressure calculation is retained only as disclosed methodology, never promoted into the primary user instruction or trading recommendation.

## Design system and failure states
Use the shared nav, monoline icons, type/space/radius/color tokens, and archetype-G Monitor composition. No page-local palette, font stack or runtime stylesheet injection.
Dark/light and EN/ZH are first-class. At 390px the page never scrolls horizontally, touch targets remain usable and the first answer is visible within one swipe.
Differentiate genuine empty evidence, filter no-results, source outage, unknown time, stale page snapshot and unsupported selection. Each state names what still works.
Details are progressive disclosure, never a place to hide a caveat that changes the headline. Reduced motion, visible focus, native dialog Escape and focus restoration are required.

## Bounded implementation plan
1. RED: add `tests/test_alert_center_explorer.py` covering uncapped projection, unchanged ranked output, actual-firing history, exact-subject grouping, missing/unknown time and no promotion.
2. GREEN: implement `engine/alert_center_view.py` as a pure projection helper; call it once from `engine/alert_triage.py` using the existing enriched and raw populations.
3. RED: add template/browser contract tests for the four tasks, selected evidence, AND filters, malformed/legacy hash, no-results reset, coverage and unknown-time states.
4. GREEN: replace `templates/alerts.html.j2` with scoped Jinja composition, source CSS and plain JavaScript includes. Keep the shared renderer, nav, icons and theme.
5. Render through `scripts/build_site.py::build_alerts_page`; run existing semantic suites plus new contracts, browser interactions and design-system/style-injection checks.
6. Capture real-source local output in dark/light x EN/ZH at 1440 and 390, plus empty, partial and unknown-time controls. Retain baseline and selected evidence state.
7. Record exact candidate, test receipts, source-input hashes, Figma nodes, reviewed limitations and next action. Open one bounded PR; review is not production acceptance.

## Acceptance and stop boundary
Primary journey: Now -> Signals/source filter -> selected signal -> original evidence -> return with filters intact; specific situation -> member evidence; History -> actual logged firing.
No source disappears merely because the old top-60 population excluded it. Population counts and truncation labels must agree.
No existing alert ID, priority term, validation verdict, push rule, preference, outbox or shared navigation implementation changes.
No fabricated causal links, measured hit rates, continuous-state claims, event times or active-work claims.
Hold production release at a missing authorization, competing writer, unresolved modifying effect, failed current integration or missing real browser proof. Do not bypass publication ownership.

## Primary-source workflow research
TradingView, Manage alerts: https://www.tradingview.com/support/solutions/43000595311-manage-alerts/ — filtering, keyboard navigation and fired history are separate useful jobs.
AlphaSense, monitoring tools: https://help.alpha-sense.com/hc/en-us/articles/41815509396371-Maximizing-Your-Monitoring-Tools-in-AlphaSense — preserve context and the path into precise source evidence.
Dataminr, Investigation Insights: https://www.dataminr.com/products/cyber-defense/investigation-insights — reduce investigation context-switching; different-domain workflow precedent, not market validation.
Original Mastermind implementation and visual design only. No competitor code, assets, branding or proprietary corpus is copied.

## Held adjacent work
Canonical account-alert preferences and delivery/outbox PRs #6907/#6906 remain with their owners. No duplicate saved/mute/read/delivery persistence.
Shared theme changes, other build-site functions, autonomous deployment and broad cross-source entity/causal inference are outside this slice.
Broader verified relationships and learning instrumentation extend this workspace only through existing company identity and analytics contracts, not a new control plane.

## Continuation reconciliation — 2026-09-09 18:50 UTC
Protected procedure re-pinned to Mastermind `63e3ddec6d8819dffe6509f3d13d41f2e94b9709`; INDEX/COLD_START/RECONCILE_STATE/CLOSEOUT are compatible 1.0.1 at that exact commit.
The earlier chat conclusion 'prototype only' is superseded: this same source carrier contains the real implementation and a successful 12:41 UTC local real-builder browser proof.
No source writer is active in this worktree. The current census traversed all 155 open Macro PRs and found no overlap on the eight owned alert source/contract paths.
Macro main at reconciliation: `e75998821888d5bc457ea669c603f8e298f64b13`. Governing docs, alert sources and renderer are unchanged against the carrier base; shared theme adds only language-stable freshness aliases and documentation.
There is no existing Agent OS parent matching this operation in current main. Do not invent a workstream or Executive lifecycle record.
The existing standalone Inbox/Rules/Delivery-health sandbox prototype is exploratory and NOT this ship specification. No account state or delivery plane is being added.

## Trust and experience repair amendment
Preserve negative validation verdicts (NO-GO, tested-no-edge, underpowered) explicitly in the inspector; a truthy backtest flag must not erase the verdict.
The briefing quotes the highest-ranked available source observation with its actual event date, instead of a generic instruction. This does not change ranking or introduce synthesis authority.
Collapsed rows show source-assigned severity in plain words; historical rows identify historical firings without inventing historical scores.
An unavailable/invalid snapshot day is visibly unknown. Missing JS payload must leave genuine original source links accessible, not promise a hidden noscript fallback.
Historical detail preserves the selected firing's original detail and clock fields. Multiple firings on the same source date remain multiple observations, not a fabricated unique event.
Legacy `sev=major` keeps its exact major filter semantics. Search/filter/pagination and permalink recovery must preserve the user's investigation place.
Related changes remain explicit same-source subject bundles. This slice does NOT complete rich cross-domain Situation intelligence; the next intelligence contract must ground links in the existing entity/graph owners and preserve contrary evidence.

## DARK TREATMENT / LIGHT TREATMENT
DARK: the existing navy/aurora canvas, luminance-separated panels, restrained blue selected-state inset and low-chroma dividing rules. No decorative severity glow.
LIGHT: cool research-paper canvas, white panels with the existing card-shadow depth, stronger control boundaries and a soft blue selected-row wash; no dark glow or translucent dark material carried over.
Both share the same hierarchy, source facts, state meanings, geometry, priority order and interactions. Missing data is a warning in either theme and either language, not a direction-color change.
The Figma account currently permits one variable mode. Separate editable light artboards will document light materials explicitly; no paid upgrade, second-mode capability or production release is assumed.

## This continuation's proof target
First establish failing acceptance cases for verdict retention, selected-history detail, missing snapshot dates and JS-failure source access; repair only the existing view projection and template/client.
Repeat the existing real-builder journey with source and output hashes bound to every proof, plus laptop, partial, empty, no-match, unknown-time and long-content controls.
Retain real-source screenshots and editable Figma states separately, compare them, and publish the exact candidate as a DRAFT with release held. No merge/deployment authority is granted by this amendment.
