# Breadth Intelligence — Paper design handoff (governed)

**Status:** Design-ready specification, not a saved Paper artboard. **Date:** 2026-10-30. **Parent:** research/breadth_intelligence/MASTER_PLAN.md. **Target product:** Macro existing Markets / Sector Central exploration, with contextual Theme Graph and Group Reads links. **House authority:** Mastermind docs/DESIGN_DOCTRINE.md → research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md → templates/theme.css → governed Paper reference, per Mastermind skill mastermind-design-system. **Archetype:** D / regime_dashboard. User question: “Is participation improving or deteriorating, who is participating, and is that change durable beyond today's tape?” No tenth visual language.

## Available Paper references / status

Read-only style/reference file MASTERMIND PAGES: Paper ID 01M2WGNCX9475G79JRKJTCM08P, governed page p-5-0, reference artboards 5FE2-2 (dark atlas), 5FGO-2 (light), 5FPP-2 (data/chart dark), 5FSH-2 (light) and 5FJA-2/5FLR-2 (mobile thread). These references come from the pinned Mastermind design-system read, NOT a fresh live Paper inspection. They are not an authorization to mutate the system file. The exact product target must be re-inspected and its file/board/artboard snapshot guarded before any write.

On October 30 2026, the requested Mastermind Paper paper_inspect call and Studio Direct Paper inspection returned HTTP 429 SSE transport before obtaining active file snapshot. NO Paper edit, screenshot, render proof, JSX extraction, product implementation or specific artboard file was saved by this commission. Use this brief and the local fixture HTML as the disjoint target plan when the approved Paper carrier is available. Do not retry an un-reconciled uncertain effect.

## Frame and page anatomy

L1 user wants: state -> meaning -> stance -> top changed groups -> evidence. Desktop 1440×900 should show chrome + the verdict + two supporting modules (time-series and first eight sector rows). Detailed group data, historical controls and the last 3 sectors are named destinations/disclosures. A diagnostics lens includes freshness/membership/rights. All outputs are display-only.

Archetype D composition / canonical components:
1. Existing PageShell + one h1 “Breadth Intelligence”, five-point context in page header only when needed.
2. VerdictHero .mx-vh with one descriptive word, e.g. “BROADENING · UNEVEN”, 14-word maximum explanation, stance “Watch — verify at the close”, source/time stamp and Evidence Lens. A display-only breadth context is NOT a trading instruction or verified forecast. No composite mystery score.
3. **Support A, question first:** “Is participation improving during today's regular session?” — ChartFrame/illus existing chart primitive and up to four named legs (advancing share, % above 50D, cap-weight index or equal-weight reference, bounded missing interval as optional shade). Baselines and units on axes are distinct; never draw price normalised as if same magnitude as breadth without a separate clearly named axis. Horizon 1D|5D|1M|3M|1Y|3Y|ALL changes the actual source/time meaning.
4. **Support B, what is changing:** sector change rows or L1 table .mx-tbl limited to eight of eleven sectors, with “See all 11 sectors” landing. Sectors show 15min | 1D | 5D | 1M | 3M | 1Y signed breadth changes, eligible/observed counts, and a source confidence label. Click goes to side panel/landing.
5. Deep group detail: one selected GICS sector → industry → subindustry hierarchy; SEPARATE semantic category → canonical house theme → microtheme. Show overlap/parent plurality and why theme cannot be counted as a disjoint sector. Link original owner surfaces.
6. Named historical analysis: synchronized date window with source vintage and membership known-at controls, 5/15/30/60-minute RTH slot comparison (only if retained), daily 1/5/20/63/126/252 sessions and optional longer history, own-history percentile restricted to mature comparable universes.
7. Evidence Lens: vendor source delay, last original source time, current display time, raw-vs-adjusted basis, current/retro taxonomy mode, rights and observed N, logical bounds and exclusions. Staleness never replaced by a newer wrapper timestamp.

## Semantic visual law

Use existing CSS/JS production tokens and components (templates/theme.css); Paper is a reference projection, not a source of new literal colors or component naming. Graphite/luminance in dark and cool white/research density in light. No colored container-edge accents, striped callouts or repurposed violet. Hue only for market direction, health/severity, wayfinding, epistemic status, lock. EN and ZH have correctly flipped market direction red-up/green-down under ZH, but HEALTH stays the same. Direction is always paired with signs/language, not color alone. All data areas use tabular numeric typography.

L1 primitive budget ≤5, one canonical count per population, one freshness stamp per panel. Use VerdictHero, ChartFrame, .mtile, .mx-tbl, .mx-tabset, .mx-disc, .dtp-asof, .qual2, .mx-callout and shared LENS. At 390px, recomposition order: verdict + settled/delayed proof → single most important breadth change → stance → 3 top groups → “See full sector matrix” landing → data quality. Do NOT squeeze 11 columns into the full page; only a matrix panel may scroll internally. One h1, semantically correct h2, visible focus and ≥40px controls. No hover-only data or emoji icons. Respect reduced motion.

## Paper board/artboard plan

**B1 Desktop dark, 1440×900** / existing navigation and tokens. Primary answer + breadth curve + first eight sector changes. Proof: chart as-of and evidence lens, signed change labels, no page-level overflow.

**B2 Desktop light** / own light art direction from the light component atlas, not CSS negative filter. Identical metrics and states.

**B3 Desktop chart-expanded / time travel** / source-qualified historical window, comparison checkpoint and distinct “retrospective reconstruction” or “original observed” badge.

**B4 Group drilldown** / GICS sector path side-by-side with a separately labeled canonical theme graph path and member-count overlap caution.

**B5 Mobile dark / B6 Mobile light, 390px** / deliberate answer-first recomposition; no disappearance of evidence action.

**B7 EN + ZH mirror states** / proper translations, no forced English uppercase; direction convention flips only when translating market-direction elements.

**B8 Degraded/state matrix** / loading skeleton, no quote, first 09:31 sparse data, old snapshot, weekend/closed, denied/licence-unverified, partial coverage, unknown microtheme, missing PIT membership, no intraday retention, correction and successful member read. No false 0% breadth.

**B9 Interaction anatomy** / focus, pressed, selected, disabled, expanded, touch hover equivalence, keyboard chart data table and count toggles.

## Prototype artifact coverage

A standalone 26KB responsive HTML design reference accompanies the commission, explicitly labelled SYNTHETIC FIXTURE on every view and fetching no vendor data. It sketches the macro hero, KPI cards, six-horizon chart, 11-sector change heat matrix, group-detail selection and evidence/coverage panel. Its custom CSS is **not** approved to be copied into production, its charts do not show live data, and it does not discharge dark/light/EN/ZH Paper proof. Use it to communicate composition/interaction, then implement from governed tokens after exact Paper inspection.

## Acceptance and falsifiers

Visual: compare exact desktop dark/light EN/ZH board captures and mobile twins to same-source production tokens. Browser/user: user can see the verdict and reach the three weakest sectors, navigate both hierarchy dimensions, find the source clock/rights and understand nulls without hover. Performance: chart and matrix remain usable under absent feed, mobile pinch zoom and prefers-reduced-motion. Scientific: the D1 return basis and D2 denominator stay the same across horizon toggles; a change of source or cohort is visibly disclosed. Release: prototype design is not production user-path proof. Protected CI/independent review are separate from Paper screenshot acceptance.