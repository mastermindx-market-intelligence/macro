# Options workspace revamp — source design and implementation packet
Date: 2026-11-01 America/Chicago (execution may be 2026-11-02 UTC)
Root: options-workspace-revamp-20261101-sol-001
Parent: research/OPTIONS_WORKSPACE_REVAMP_PLAN_2026-11-01.md / WS-ADVANCED-DATA-OPTIONS
Status: SUPPORTING DESIGN / NOT_APPLIED_TO_PAPER / CANDIDATE BUILD AUTHORIZED / RELEASE HOLD

## Outcome and exact boundary
Replace the broken options.html experience with a coherent, polished, accessible research desk while retaining every existing engine and task. This is a display/interaction rebuild, not a scientific model, acquisition, licensing, or production-store change.
Behavioral source: macro@f754bdee6b803b18191841863c35527c0a74571e.
Protected procedure: Mastermind@19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec.
Reference files: reference.html.j2 + reference.css, rendered by render_reference.py in this directory.
The supporting reference contains captured examples and explicitly illustrative failure views. Never transplant its fixtures or placeholder actions into production.
Paper target: MASTERMIND PAGES / 01M2WGNCX9475G79JRKJTCM08P.
Paper write gate: live catalog 16e6b93f0c51a1574ba8acee4df732052898707a04731d3817530971a88fdefd is unreviewed; accepted catalog 1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db. No content mutation has been attempted. Source work is useful supporting work, not a substitute claimed as Paper.
No compliant=true, accepted-reference receipt, merge, deployment, or completion claim before actual Paper, independent reference integrity review, exact-source checks, and real-path proof.

## Evidence corrections that govern implementation
The parent inspected the expanded live Source-session receipt on 2026-11-02:
- Target completed session: 2026-10-30.
- Dealer positioning (GEX): 2026-10-30. Individual index cards use these records.
- Volatility regime: 2026-10-30.
- Index structure/context (market_structure): 2026-10-20, 8 sessions behind.
- Options intelligence: 2026-08-19, 51 sessions behind.
- Options tape and Scanner rows: 2026-08-13, 55 sessions behind.
- Flow leaders: 2026-08-12, 56 sessions behind.
The old headline 372/408 is from the retained scanner record and MUST NOT be described as target-close coverage. The OI-counted clock can be current while the coverage clock is old.
The audit's causal statement that producers are stalled is unproven. Evidence proves old served records, not whether acquisition, composition, publication, caching, or another stage caused it.
The audit's "race-safe" Ticker claim is not accepted: current loadMode then() renders without checking that its captured ticker/request is still current. Verify and repair that risk.
Source mapping for the four posture cells is vol, market_structure, flow_desk, flow_desk. Do not label the second cell with the GEX date.
Preserve engine states and source dates. Never restamp an old record or invent a current market conclusion.

## Product hierarchy / accepted design reasoning
Shared site navigation is retained as the sole global shell.
1. Page identity: Options / research desk, compact latest-completed-session stamp, existing theme/language settings.
2. Task tabs: Daily Brief, Flow, Scanner, Ticker, Leaders, in that exact order. Stable counts disclose their own source date; a retained count must not imply target coverage.
3. Source context: four independent readings. All-current records can use the four-card row. For mixed/stale records, use a compact context disclosure; the summary may show only readings valid for the target session, with dates. Old values appear only inside explicitly dated retained context. No combined market score, no decorative confidence meter. Existing pip scales may remain only with their actual documented meaning.
4. Brief: a current, available engine brief can lead with its substantive answer. When unavailable/stale, use a compact notice naming target and actual brief dates, with "View dated history" and "Source details". Do not reserve a large empty hero.
5. Lead with actual available evidence: four index products and the dealer levels at their individual source close. Keep existing payoff disclosures and ticker deep links.
6. Earlier-session supplementary Brief material sits in a clearly bounded historical section, expanded only by explicit action. Current material must not be swept into history merely because a different source is old. Keep its own dated sections. Full active workflows remain in their original tabs, never buried in the history disclosure.
7. Local sources, caveats, provenance and computation details are placed near the relevant result. Source detail disclosure covers every existing receipt.
8. A clear path from observation to evidence to a ticker/task and back; preserve relevant query/filter/selection state.

## Visual contract
Compose the intelligence_desk archetype using research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md and docs/DESIGN_DOCTRINE.md.
Use only theme.css tokens. Replace local hard-coded slate/brass colors with semantic theme derivations. No new global palette, font stack or component library.
Neutral panels, restrained hairlines, measured spacing, strong type hierarchy, aligned tabular numbers. No colored edge/stripe on any container. Focus outlines and quantitative chart markers remain functional.
Content max width approximately 1280px; desktop 1440, mobile 390. Default should expose useful current evidence in the first screen; no wall of repeated freshness warnings.
Light: crisp white surfaces and cool canvas, quiet shadow. Dark: graphite luminance depth. Do not treat light as a raw inverse.
Use shared --sp-*, --r-*, --fs-*; body 14px, supporting text generally 12.5px; 10/11px only dense metadata, never essential caveats.
The index track is a precise linear diagram of close/floor/flip/ceiling, not decoration. Use numeric data and a visible value legend; no fabricated history/sparkline. Expand domain for out-of-range close, do not clamp it into the band. Missing, coincident or invalid values degrade to the numeric legend; label Close rather than Current. Distinct per-symbol scales.
Mobile cards may become one column when two columns cannot preserve readable labels. Contain table overflow; never page overflow. Touch targets >=40px, preferably44. Keyboard focus visible. Reduced-motion support.
All new interface copy has authored EN/ZH and preserves house color-direction rules.

## Capability retention (nonnegotiable)
Chrome: exact session/OI/coverage clocks, quality explanation, full source receipt, independent readings, source-true coverage, shared nav/settings.
Brief: AIB source pass-through, board/state/order/score/cautions, degraded receipt, watch/event/risk bands, what-changed comparison dates, SPX/SPY/QQQ/IWM, payoff lab, sectors, single bets, for-tomorrow ticker paths, source notes.
Flow: full sector desk, theme groups, sector ETF money, both tide canvases, own horizon/source labels, redraw on theme/language/re-entry.
Scanner: 3 column views, 7 existing presets, all 10 min/max filters, sector and text filters, desc-first sort with nulls last, keyboard sort, source-age column, exact filtered/sorted CSV, clear-all, matched counts, empty-results recovery.
Ticker: search/typeahead, slash shortcut, keyboard selection, per-name regime/levels/expected move, intraday record, IV placement, OI changes, history placement, tape/mood/lean, move/expiry availability, measured flow, expert shelf and all four SVG charts, Terminal symbol/return link.
Leaders: both strategies with original denominators/eligibility/order; n-of-m evidence with missing legs; cautions; expand/collapse actual rows; dates; ticker navigation.

## Functional repairs
- Bound fetches (including optional requests) so a source cannot leave the workspace loading forever. Use AbortController with a timeout and an explicit retry path. Do not silently retry or conceal persistent errors.
- Dedupe in-flight requests for the same URL; clear failed pending/cache entries so retry makes a real request. Successful data can cache for the visit. Don't mark a mode loaded before a successful render.
- Prevent stale Ticker responses from overwriting newer selections; captured request generation and symbol must match before render. Ensure a failed prior request cannot replace a newer success.
- Loading, network/error, no-source, stale-source and genuine no-matches states are distinct. Preserve filters and usable other tabs during a source failure.
- Roving keyboard tabs (arrows/Home/End), aria-selected, aria-controls, hidden states, aria-busy and concise status feedback.
- Browser back/hash/ticker links remain coherent; do not silently change a historical session under a current label.
- Source date moves adjacent to each module heading, including dynamically rendered Ticker/Flow/Leaders modules. Replace present-tense headings for old records with neutral source-labelled copy, without changing engine output text.
- The TSLA same-day-heavy flag and 0% share come from different stores. Preserve original evidence with explicit source/basis/date labels or withhold the ambiguous combined presentation and explain why. Do not choose a preferred value, invent a threshold, rewrite the flag, or imply both are the same observation.

## Source/build boundaries
Own only templates/options.html.j2; scripts/build_options_command.py if annotation/composition is genuinely necessary; focused new/updated UI regression tests; this reference/evidence directory; plan progress.
Do not change engine/, collectors, production datasets, store contracts, source allowlists, thresholds, model scores, producer order, GitHub workflow permissions, shared global nav/theme, or unrelated pages.
Prefer a coherent rewrite of the existing source CSS/markup over layers of competing overrides. Never inject a giant CSS runtime string from JavaScript.
Keep the existing data-externalize pipeline and plain JSON fetch discipline. All render-time data stays in its data script; no stamped static JS with frozen render variables.
No full site/engine/data regeneration. Use hermetic render fixtures and the established narrow options builder. A checkout without site/data yields unavailable output; never publish that as a replacement for the live page.
Inspect whether a paired site/options.html is actually tracked/required. If current-source inputs are absent, retain the truthful limitation and use the normal render lane only when release is authorized.

## Verification and return
Meaningful tests for never-settling request -> recoverable timeout; retry succeeds; out-of-order ticker responses; filtered/sorted CSV; keyboard tabs/typeahead; exact source/coverage dates and no stale current values; all-current/partial/stale/unavailable/empty fixtures.
Focused baseline: tests/test_build_options_command.py, tests/test_options_intel_brief_ui.py, tests/test_render_options_workspace_scope.py. The similarly named options_reference_pages test is a provider cursor test, not UI proof.
The source checkout intentionally lacks site/data. Use existing hermetic fixtures and an isolated test output tree.
Record 1440/390 x light/dark x EN/ZH visual evidence through the project's approved source-test/browser workflow. Do not claim screenshots from HTML source or fabricate a visual approval. Browser policy denied data: URL navigation; do not retry that protocol, alter policies, or bypass it through other browser surfaces.
Final return must include exact commit/tree, changed paths, retained capabilities, tests and their outputs, artifact locations, remaining limits and release hold. Do not merge, deploy, expand scope, contact outside parties, or dispatch another worker.

## Visual critique correction — second source-reference pass
Actual main.ref captures were inspected at desktop light EN and 390 dark ZH. This is provisional content-area evidence, not Paper or shared-shell acceptance.
- Some --sp-*, --r-*, --t-* tokens in the design standard are not globally declared in the current theme.css. Use the standard's exact fallback values in var(), without creating a palette or changing shared global theme.
- Keep all five mobile task labels visible; move dated counts to the active panel. A stale 408/12 badge must not look like a target-session count. A selected Ticker symbol is selection context, not a current count.
- Mobile level values and expected move require 12.5px or larger; use a two-line legend if needed. Labels distinguish Floor, Flip, Ceiling and Close. Do not shrink essential evidence into microcopy.
- Existing build_indexes reads expected_move.daily_pct. Show a one-day expected-move label; do not translate the move into generic implied volatility or invent an expiry.
- Disclosure summary uses one label/chevron row, real source-date preview, and links open AND focus the actual target disclosure. No duplicate views.
- The shared assistant floating button overlaps mobile SPY detail in the content capture. Verify the integrated page, controls and scrolling before release; do not hide it merely to pass a screenshot.

## Newly reproduced clock defect — Leaders
Live Leaders showed 2026-11-02 while the baked receipt said 2026-08-12. Source inspection proves templates/options.html.j2 renderLeaders uses L.as_of; scripts/build_flow_leaders.py explicitly documents as_of as the BUILD wall clock and provides session_date for the underlying research session. Use session_date as the research clock; missing session_date is unknown, never substitute the build clock. A build timestamp may remain separately labelled in a receipt. Do not change the producer or restamp records. Independent synthetic acceptance deliberately sets these clocks apart. The frozen child packet preceded this observed defect; principal must adjudicate this against the implementation return before acceptance.

Scanner age labels must state their basis: ageCell currently compares a row to the newest scanner-row date. A zero lag in an old snapshot is not the latest market close; an absent/invalid row date is unknown, never zero-day fresh. Preserve the existing numeric convention where valid, label calendar lag versus scanner snapshot, and expose each actual date. The independent published fixture confirms the live snapshot is August 13 while its newest-row tooltip claims latest close.
