# Macro Alert Center — Figma execution brief

**Status: DESIGN EXECUTION BRIEF / SPEC_ONLY.** This turns the accepted `MACRO_ALERTS_MARKET_CHANGES_DESK_EXPERIENCE_FREEZE_20260914.md` into an editable Figma work plan. It is not a design-completion or implementation claim.

**Procedure:** Mastermind Skillpack 1.0.1 at protected `master` `af9fce32861f9c1496b85a580e3569712170d92b`. **Macro source reference:** `2e972811e82a56928e5f4871300ecb91daf0bed3`.

## 1. File identity

Target file name: **MastermindX — Macro Alert Center — Market Changes Desk**.

Do not modify, rename or overwrite the Terminal Alert Center files `wvVt4GTPGMqnaPprVnbloU` and `EQlAQXIOdRdO63nMX2RK3u`. They may be read as interaction/reference material only.

The new Macro target should reuse the same Mastermind visual constitution: Inter/CJK-compatible typography, shared page/navigation anatomy, existing colors/tokens, monoline icons, panels, buttons, status strips, empty states and LENS idioms. It should not copy the Terminal AppShell.

If file creation is unavailable through the connected Figma tool, stop and report that exact boundary before editing another Alert Center file. Do not create confusion by pretending a Terminal page is the Macro file.

## 2. Page structure

Create these pages in order:

1. `00 — Foundations + Design Law`
2. `01 — Components`
3. `02 — Now`
4. `03 — Explore`
5. `04 — History`
6. `05 — Evidence Inspector`
7. `06 — Mobile`
8. `07 — States · Light · ZH`
9. `08 — Prototype + Handoff`

### 00 — Foundations + Design Law

One concise reference frame naming:

- product: Macro Alert Center / Market Changes Desk;
- archetype: `monitor` / change-log timeline;
- primary tasks: Now / Explore / History;
- source truth: `alert_triage` existing authority;
- no giant pressure hero / no storyline cards / no new score;
- Situation reserved;
- private monitoring remains Terminal/F08-owned;
- examples are source-shaped **SAMPLE DATA**, not live market claims.

Include dark and light material boards and the existing semantic color meanings. No bespoke color palette.

## 3. Component inventory

Build editable components/variants only where they are specific compositions of existing design-system primitives.

### PageHeader / SessionHeader

- `Alert Center`
- subtitle `Market changes worth understanding now.`
- New York board-day stamp using `.dtp` visual language;
- optional device-local `since last visit` line, visibly secondary;
- Now / Explore / History task tabs.

Desktop target height before context: ~88–100px. Mobile: ~74–88px.

### ContextStrip

Three compact facts at rest: regime, cross-asset context, next catalyst. Achromatic/low-emphasis. It is not a metrics dashboard.

Variants:

- complete;
- blocking partial coverage -> warning callout replaces whole-market context;
- nonblocking source loss -> restrained warning note;
- unknown/no catalyst.

### LeadChangeRow

For `What Matters Now`, 0–3 maximum.

Desktop anatomy:

- source + event date eyebrow;
- short plain title;
- one short meaning/limitation line;
- research-attention action at trailing edge;
- optional subtle recurrence wording (`Observed again`) only when truthful.

No raw priority number. No giant severity icon. No progress/gauge.

Variants:

- Review now;
- Confirm first;
- Watch closely;
- Re-fired today;
- selected/focus/hover.

Target height 86–108px depending on copy. Keep all three leads plus three ordinary rows above fold at 1440×900.

### ChangeRow

Ordinary timeline row. Target 64–76px desktop.

Anatomy:

- source + event date;
- one-line headline at desktop Tier 1;
- one meaning/limitation line only when lawful and space allows;
- trailing `Investigate`/attention cue;
- keyboard focus and selected states.

Mobile may use a two-line headline/meaning stack; avoid card bloat.

### DayDivider

`Today`, `Yesterday`, or explicit date. It is structural, not another card.

### QuietLeadState

Compact copy, no large empty illustration:

> No major fresh change requires review right now.  
> <N> other observations are available below.

### CoverageCallout

Blocking version:

> Market read incomplete  
> Bonds evidence is unavailable. Mastermind is withholding the whole-market summary; available changes remain below.

Nonblocking version states source loss without withdrawing unrelated evidence.

### FilterBar

Explore only. Search + Source + Topic + Attention + Time/New/Re-fired + Reset. Desktop can be one compact row with overflow/details; mobile uses a sheet or wrapped controls without horizontal page scroll.

### EmptyState

Use canonical `.mx-empty` visual grammar with explicit why. Required causes:

- no observations;
- no filter matches;
- source unavailable;
- selection no longer in snapshot;
- interactive evidence unavailable.

### EvidenceInspector

Desktop side sheet 520–600px; mobile full-screen.

Sections in order:

1. What changed
2. Why it matters
3. Original evidence
4. Current read, only if source contract supports it
5. Context
6. Why this ranked here
7. Observed history
8. Investigate further

Use disclosures/LENS for technical receipts, not stacked badges.

### RelatedObservations

Inside inspector/Explore only. Label exactly **Related observations** with helper text such as `Same explicit subject; not independent confirmation.` Never `Situation` in v1.

### HistoryRow

Neutral event-history row. No current priority/severity repainted as historical truth. Action `Open firing`.

## 4. Now artboards

Create these desktop 1440 frames first because they define the product hierarchy:

### N1 — Now / complete / two leads / dark EN

Primary reference frame.

Required fold content:

- header/session/tabs;
- compact context strip;
- `What Matters Now` with two leads;
- `Today` divider;
- at least four ordinary rows visible within 900px if practical (minimum three);
- counted Explore transition below the initial rows or just below fold.

Use source-shaped sample families that actually exist in current Alert Triage (for example a macro transition, a commodity risk observation, theme/rotation/alt-data rows). Label page/artboard as **SAMPLE DATA**. Do not invent live Prophet or News alerts.

### N2 — Now / complete / three leads / dark EN

Stress maximum lead count and fold budget.

### N3 — Now / quiet lead / dark EN

Zero lead-worthy observations but several ordinary observations. Show calm quiet line and timeline immediately.

### N4 — Now / true empty / dark EN

Source reads complete but no observations in window. Copy must tell the user this is a quiet window, not a loading or source failure.

### N5 — Now / blocking partial coverage / dark EN

Coverage callout replaces normal whole-market context. Surviving source-specific rows remain useful. No pressure score or directional whole-tape summary.

### N6 — Now / nonblocking source unavailable / dark EN

Example source warning that does not invalidate the board. Keep hierarchy calm.

### N7 — Now / unknown event time

Unknown-time observation is visible lower in timeline/Explore but not placed under Today/lead. Demonstrate copy `Time not established` and evidence handling.

### N8 — Now / re-fired

Lead/ordinary recurrence wording must show `Observed again` or `Re-fired today`, plus inspector history preview; no persistence claim.

## 5. Explore artboards

### E1 — Explore populated / dark EN

Complete population managed list. Show count and filters. Use canonical attention sorting as the default visual treatment; do not imply the source machine order has been mutated.

### E2 — Explore filtered

One source + one topic/freshness filter, visible removable filter state, search term, stable result count.

### E3 — Explore no results

Clear cause + `Reset filters` action. Keep source coverage separate from filter emptiness.

### E4 — Explore source unavailable

Selected source has no available coverage; other sources remain accessible.

### E5 — Related observations

Show one result/inspector with multiple same-source exact-subject observations and explicit `not independent confirmation` copy.

## 6. History artboards

### H1 — History populated

Group actual firings by date/time. Show bounded-history receipt if applicable. No interpolated duration graphics.

### H2 — Selected historical firing

Inspector displays selected firing's historical detail and clocks. Any separate current read is visually and semantically distinct.

### H3 — Missing historical selection

Deep-link points to firing outside published cap/window or corrected away. Copy says the firing is not available in this snapshot; do not substitute another event.

## 7. Inspector artboards

Create at least these explicit variants:

### I1 — Current observation / full evidence

All eight inspector sections where the source supports them.

### I2 — No accepted current-state contract

Omit Current read entirely rather than filling it from the firing/recurrence.

### I3 — Negative/null validation

Show a valid observed event with a measured/documented null/NO-GO limitation. The limitation must change interpretation visibly, not hide in a tooltip.

### I4 — Re-fired history

Observed-history section distinguishes first/latest occurrence and says continuity is not verified where appropriate.

### I5 — Broken source link / missing selection

Names what failed and preserves useful remaining evidence.

## 8. Responsive + language/theme matrix

Primary canonical frames to create in all 8 combinations:

- Now complete reference;
- Inspector current observation.

Matrix: dark/light × EN/ZH × 1440/390.

Then create supplemental negative states in dark EN desktop first, with selected mobile/light/ZH variants where geometry or semantics change materially.

### Mobile rules

- 390px width, zero page horizontal scrolling;
- header/tabs/context do not consume the first viewport;
- first lead/timeline item immediately visible;
- first non-lead row within first swipe;
- inspector full-screen with clear close/back;
- filters use an explicit mobile control/sheet, not a squeezed desktop toolbar;
- no bottom-fixed controls covering the last timeline row;
- touch targets >=44px where actionable.

### Chinese rules

Chinese copy is independently plain, not literal English jargon. Do not leave machine slugs or EN action verbs inside ZH. Direction colors obey existing locale semantics; severity/health colors do not flip.

## 9. Prototype flows

Wire these before calling the design complete:

### P1 — Now investigation
`Now lead -> Evidence inspector -> Investigate further source link -> back/close preserves Now state`.

Figma cannot prove external source behavior; link/button target can be documented as external source handoff rather than fake navigation if necessary.

### P2 — Ordinary + history
`Now ordinary row -> inspector -> Observed history -> selected historical firing -> inspector historical state -> return`.

### P3 — Explore
`Now -> Explore -> apply source/topic/search -> select row -> inspector -> close -> filters remain -> reset`.

### P4 — History
`History -> selected firing -> original evidence -> distinct current-read block if supported -> return`.

### P5 — Coverage degraded
`blocking coverage state -> available source-specific observation -> inspector`; no route through a false whole-market summary.

## 10. Sample-content rules

Every new design frame that resembles current market content must carry a small but visible **SAMPLE DATA / PROTOTYPE** disclosure in the design handoff area, and screenshots used as evidence must not be presented as a real current-market alert.

Use only actual source-family shapes present in current `alert_triage` (macro, bonds, forex, vector, commodity, themes, emergence, altdata, demand, rotation, oracle where exposed). Do not depict customer Prophet or News integration as live.

Good sample wording is source-shaped but non-factual, for example:

- `Macro regime changed` / `Review now`;
- `Commodity risk read moved higher` / `Watch closely`;
- `Alternative-data convergence observed for SAMPLE` / `For context`;
- `Theme leadership rotation observed again` / `Observed again`.

Avoid invented returns, positions, probabilities, company guidance, or exact market levels unless bound to a retained fixture and clearly labeled historical/sample.

## 11. Visual direction

The design should feel like a **premium institutional tape**, not a social notification feed.

- timeline rhythm and typography create hierarchy more than containers;
- lead rows receive slightly greater type/spacing, not loud filled backgrounds;
- ordinary rows are mostly neutral/achromatic;
- brand blue is for action/selection/navigation;
- warning/act colors appear only where the semantic state justifies them;
- one-pixel rules and generous whitespace replace thick dashboard cards;
- no emoji; monoline icons only;
- no red glowing hero, no heat-map aesthetic, no rainbow source colors;
- light mode is paper/white-panel structure, not inverted black glass.

A useful mental model: Bloomberg/terminal information density disciplined by Mastermind's calmer visual language — but do not copy competitor visual assets or proprietary layouts.

## 12. Copy budgets

Apply house doctrine:

- page title: short;
- subtitle <=14 words;
- lead title target <=6 words where source meaning allows;
- lead meaning <=14 words;
- ordinary desktop row: one short headline line plus at most one restrained explanation line;
- mobile may use two-line stack but no paragraph;
- technical receipts and numeric breakdowns live in inspector/LENS;
- one as-of/session stamp per visible panel/section, never repeated on every row.

If the copy cannot fit, demote detail; do not compress it into jargon.

## 13. Required interaction/accessibility annotations

The handoff page must state:

- selected tab lives in URL/hash;
- selected observation permalink behavior;
- filters combine predictably and survive inspector close;
- Escape closes inspector; focus returns to opener;
- focus ring is visible in both themes;
- reduced motion removes nonessential transition/ink effects;
- list semantics/heading outline are retained;
- buttons/rows have explicit hover/focus/pressed states;
- empty/loading/error/source-unavailable are different components/states.

## 14. Handoff proof checklist

Before design acceptance, record:

- exact Figma file key + page/node IDs;
- working/reference choice and why;
- frame inventory;
- component inventory;
- all prototype reaction targets, with zero missing targets;
- dark/light × EN/ZH × desktop/mobile primary screenshots;
- supplemental partial/empty/no-results/history/missing-selection captures;
- geometry checks for horizontal overflow/text containment;
- fonts used (names only; never distribute font files);
- any visual-only controls whose implementation remains unbuilt;
- explicit statement that Figma acceptance is not product/browser/production acceptance.

## 15. Completion boundary

Figma is **PARTIAL** until all primary flows and state matrix are editable, connected and reviewed. It becomes the accepted visual specification only after the real canvas is inspected against this brief and the experience freeze.

No code implementation starts merely because the first Now screen looks good. Once visual acceptance is reached, implementation is a separate bounded program: reconcile the current shared source plane and selectively port useful #7022 projection capability onto fresh main, then prove real browser journeys.