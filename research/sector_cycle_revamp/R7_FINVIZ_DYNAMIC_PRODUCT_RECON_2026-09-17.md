# R7 — Finviz Matrix and Bubbles Dynamic Product Recon

Date: 2026-09-17
Status: RESEARCH / PROPOSED DESIGN INPUT / HOLD
Parent programme: existing Chairman-commissioned Sector & Cycle Intelligence revamp

This record extends the existing R1–R6 research. It is not a new programme, an accepted architecture, a source-rights ruling, an implementation specification, a worker assignment, or proof of predictive improvement. Existing GMI, Group Reads, F04, Data OS, FIF, Company Theme Exposure, Prophet, Terminal and publication ownership remains unchanged.

## 1. Evidence boundary

Public product behavior was inspected in a fresh temporary headed Chrome profile on the authorized Mac Studio. No login, subscription session, credential entry, private payload, bypass, scraping fleet, or hidden administrative endpoint was used. The observed public pages were:

- `https://finviz.com/map?t=sec_all&view=matrix`
- `https://finviz.com/map?t=sec_all&view=matrix&render=clusters`
- `https://finviz.com/bubbles?idx=any`
- `https://finviz.com/bubbles`

The inspection records interaction semantics, aggregate counts, control names, URL behavior and response shape. It does **not** copy Finviz's constituent catalogue into a Mastermind store, reproduce logos/assets, claim a license, or establish the competitor's proprietary source code or maintenance process.

## 2. Matrix: verified public behavior

### 2.1 Current displayed population

The public all-US Matrix displayed:

| Market-cap tier | Displayed securities |
|---|---:|
| Large/Mega | 961 |
| Mid | 1,138 |
| Small | 1,438 |
| Micro | 1,057 |
| Nano | 953 |
| **Total** | **5,547** |

The page also displayed **145 industries**. The five tier counts sum exactly to the displayed ticker total. These are Finviz public page observations on 2026-09-17, not Mastermind coverage claims or a licensed catalogue.

The Bubbles market-cap filter publishes these thresholds:

- Mega: at least $200B
- Large: $10B to $200B
- Mid: $2B to $10B
- Small: $300M to $2B
- Micro: $50M to $300M
- Nano: below $50M

It is a strong product-level inference that the Matrix's identically named tiers align to this shared convention, but the Matrix page itself did not expose equality-boundary text during this pass. Mastermind must declare its own accepted tier policy rather than silently inherit a competitor label.

### 2.2 Rendering model

The main Matrix surface is canvas-rendered. In the observed desktop state it used one primary 1185 × 1052 canvas.

**Grid**:

- rows are industries;
- columns are the five market-cap tiers;
- sector bands group industry rows;
- cells contain compact ticker/logo chips;
- cells summarize hidden overflow with `+N`;
- the header and each cell retain tier/population counts.

**Clusters**:

- rows change to sectors;
- columns remain the same five market-cap tiers;
- each cell becomes a deterministic packed-circle display;
- circle area represents relative market capitalization;
- color represents the selected data field;
- only selected larger bubbles receive labels.

Changing Grid → Clusters changed the URL to `render=clusters`, while the displayed 5,547-ticker / 145-industry universe and tier totals remained unchanged. This is a representation switch, not an analytical rescope.

Packed-circle proximity is not documented as correlation, common economic exposure, causality, or machine-discovered clustering. Mastermind must not let display geometry acquire analytical authority.

### 2.3 Matrix controls

Observed control inventory:

- **66 data-type options**, spanning ticker labels; intraday, after-hours and multi-horizon performance; 52-week drawdown/gain; volume; valuation; dividends; growth; profitability; liquidity/debt; ownership/short interest; analyst and earnings fields.
- **12 sector options**: Any plus 11 sectors.
- A virtualized industry picker under the page's 145-industry catalogue.
- Five independent market-cap-tier checkboxes.
- Settings named **Why Is It Moving**, **Ticker Logos**, and **Colorblind Mode**.
- Ticker search and a collapsible member directory.

The public metric endpoint observed for one-day performance was:

`/api/map_perf?t=sec_all&st=d1`

Its response shape was an object with `nodes`, `additional`, `subtype`, `version`, and `hash`. The observed `nodes` object carried 5,902 numeric keys while the current Matrix displayed 5,547 admitted tickers. This establishes that the metric payload and displayed classification population are not necessarily identical. It does **not** establish why the extra records are excluded, whether they are valid securities, or permission to republish them.

### 2.4 Matrix filter semantics

A bounded public interaction selected **Technology** while Clusters was active:

| State | Tickers | Industries | URL |
|---|---:|---:|---|
| Any sector | 5,547 | 145 | `...view=matrix&render=clusters` |
| Technology | 787 | 12 | unchanged |
| Restored Any sector | 5,547 | 145 | unchanged |

The sector filter therefore changed the active analytical population, not merely the visibility of already-measured marks. Yet that scope change was not serialized into the URL.

This is a major design lesson. Mastermind must never make the user infer whether a filter:

1. hides marks while preserving the existing measurement;
2. requests a newly measured universe;
3. loads a previously frozen cohort; or
4. changes only presentation.

Each action needs an explicit type, and every reproducible analytical scope needs a durable identity or shareable state.

## 3. Bubbles: verified public behavior

### 3.1 Default and state persistence

The Reset state was:

- X axis: Sector
- Y axis: Change %
- size: Market Capitalization
- color: Sector
- index: S&P 500
- sector/industry/market-cap/average-volume filters: Any

The page explicitly states that ETF size represents assets under management, while stock size is market capitalization.

Changing the X axis to Market Capitalization serialized a complete chart state:

`?x=marketCap&y=lastChange&size=marketCap&color=sector&idx=any`

Selecting Technology serialized `sec=technology`. Reset returned the page to `/bubbles` and the S&P 500 default. Bubbles therefore has materially better reproducibility than the observed Matrix filter state.

### 3.2 Control depth

Observed picker counts:

| Control | Options |
|---|---:|
| X axis | 35 |
| Y axis | 53 |
| Bubble size | 7 |
| Bubble color | 18 |
| Index | 5 |
| Sector | 12 |
| Market-cap filter | 15 |
| Average-volume filter | 19 |

Additional controls include industry, include-ticker and exclude-ticker filters, axis swapping, Reset, and Load Preset.

Sizing choices include constant, market capitalization/AUM, volume, dollar volume, average volume, average dollar volume and relative volume. Color choices include categorical sector/industry/country as well as capitalization, returns, volume and analyst recommendation.

The chart uses a main canvas plus overlay/range-control canvases. Horizontal and vertical range controls preserve extreme observations rather than silently deleting them. The interface instructs users to double-click a bubble for detailed information in a new window.

An ordinal/categorical X axis such as Sector places groups at discrete positions. Distance along that axis must not be narrated as an economic or statistical distance.

### 3.3 Preset workflow

The public preset catalogue provides preconfigured questions rather than only empty axis controls. Observed examples include:

- institutional ownership, forward P/E, employees, gross margin, market capitalization, average dollar volume, SMA200, RSI14 and short-interest views by sector;
- today's performance by relative volume, market capitalization and average dollar volume;
- YTD, one-week, 52-week-high/low and high-vs-low views;
- insider transactions vs six-month performance;
- institutional ownership vs six-month performance;
- market capitalization or ROA vs twelve-month performance;
- RSI14 vs four-week performance;
- short-interest ratio vs RSI14;
- income vs sales, five-year EPS vs sales growth, and analyst-recommendation-distribution views.

The relevant Mastermind lesson is not to clone those exact presets. It is to ship **governed research lenses** that name their universe, formula, benchmark, clock, null behavior and permitted downstream authority.

## 4. What Finviz does well

1. **Coverage visibility.** The product communicates broad ticker and industry counts and preserves lower-cap strata.
2. **Fast lens switching.** Grid, Clusters and Bubbles answer different questions without forcing a user to leave the market-map workflow.
3. **Configurable encodings.** Axis, size and color are independently selectable.
4. **Progressive disclosure.** Dense overview, labels for important marks, ticker directory and drill-through coexist.
5. **Useful defaults and presets.** The user can begin with a question, not a blank chart.
6. **Outlier preservation.** Range controls help inspect compressed central populations without silently discarding extremes.
7. **Shareable Bubbles state.** Modified axis/filter state becomes an explicit URL.

## 5. Where Mastermind must exceed it

### 5.1 Truth and provenance

The competitor interface is strong, but the public view does not expose the observation receipts, denominator members, exclusions, definition version or point-in-time membership required for trustworthy intelligence. P1's complete-member evidence is the correct Mastermind foundation.

Every Atlas measurement must bind:

- catalogue scope;
- semantic membership version;
- metric-observed cohort;
- optional trade-eligible cohort;
- effective and known-at timestamps;
- source and rights;
- benchmark, currency and weighting recipe;
- observed, excluded and unresolved members;
- numerator/denominator where applicable.

### 5.2 Scope versus display

Mastermind should preserve four separate concepts:

- **analytical scope** — the population measured;
- **view state** — Grid/Clusters/Bubbles/table and visual encodings;
- **display filter** — rows/marks temporarily hidden without recomputation;
- **frozen cohort** — a versioned population retained for later comparison.

A visual filter must never silently redefine a score. An analytical rescope must create a new measured scope and update its receipts.

### 5.3 Structural, thematic and behavioral lenses

The product must not flatten three different group types:

1. structural sector/industry classification;
2. economic theme/subtheme relationships;
3. observed co-movement candidates.

They can share interaction components while retaining different membership and evidence semantics. Co-movement does not prove a business relationship, and a business association does not prove economic exposure or forecast value.

### 5.4 Better presets

A Mastermind preset should be a versioned research lens, not only visual settings. Proposed fields for later owner review:

- lens identity and definition version;
- admitted universe and frozen cohort option;
- measurement IDs and formulas;
- benchmark and currency;
- X/Y/size/color encodings;
- clock and source receipts;
- null and outlier treatment;
- owner and permitted consumer authority;
- explanation template and invalidation conditions.

This is a projection over existing owners, not a new state, identity or publication plane.

### 5.5 Intelligence and user journey

Mastermind's differentiated journey should answer:

> What is strengthening, how broad and independent is it, which businesses actually participate, what changed, what evidence is missing, and how should this affect an existing candidate or holding?

The Atlas overview should lead into the existing group page and complete-member evidence, then into company, portfolio/watchlist and eventually Prophet context. The user should not have to reconstruct the joins between visualization, group state and company evidence.

## 6. Proposed shared Atlas read model — design candidate only

The following are proposed interfaces for owner adjudication, not accepted schemas:

### `atlas_scope.v1`

- scope identity and version;
- region, exchange and security-type rules;
- structural/theme/behavioral lens;
- membership and identity receipts;
- effective/known-at cutoffs;
- catalogue, semantic, measured and optional trade cohorts;
- benchmark/currency;
- rights and publication permissions.

### `atlas_measurement.v1`

- existing-owner measurement ID;
- formula and aggregation authority;
- member observations and exclusions;
- weighting and concentration;
- coverage and missing-data bounds;
- source receipts;
- descriptive versus predictive authority.

### `atlas_view_state.v1`

- representation: Grid, Clusters, Bubbles or table;
- row/column/grouping choices;
- X/Y/size/color encodings;
- display-only filters;
- range/zoom state;
- locale/theme/accessibility preferences.

### `atlas_lens.v1`

- named governed question;
- accepted scope plus measurements;
- view-state defaults;
- explanation/invalidation template;
- owner and consumer authority.

These should be compact projections composed from existing GMI, Group Reads, Data OS, FIF, Company Theme Exposure, F04 and evaluation owners. They must not become another graph, ThemeState, membership store, event log or ranking authority.

## 7. Recommended product sequence after P1 acceptance

1. **Accept the observation substrate.** Exact-head review, CI, publication-owner integration and deployed proof for P1.
2. **Freeze one real Atlas scope.** Choose a rights-safe admitted US structural/thematic slice with full catalogue and cap data, not a synthetic fixture.
3. **Build one shared read model.** Same population and measurements across Grid, Clusters, Bubbles and table.
4. **Connect the existing detail journey.** Every group opens a complete member/evidence page using matching receipts.
5. **Add governed lenses.** Useful questions, definitions and null behavior—not chart-only presets.
6. **Measure behavior.** Instrument view switching, drill-through, saved scope reuse and missing-evidence inspection.
7. **Only then add predictive research.** Point-in-time, overlap-aware, issuer-leave-out and forward-validated context before Prophet ranking authority.

## 8. Acceptance requirements for the first real Atlas slice

- One admitted universe and membership version produces all four representations.
- Switching representation changes no analytical population, benchmark, weighting or metric.
- Display filtering does not change the measurement.
- Explicit rescope produces a new scope identity and receipts.
- Every visible count reconciles to catalogue/measured/excluded populations.
- Missing, zero and false are visually and machine-distinct.
- Outliers remain discoverable and exact values remain available in the table.
- Structural and thematic overlap does not inflate unique-security or issuer counts.
- Group drill-through preserves the same scope and observation version.
- EN/ZH, dark/light, desktop/mobile, keyboard and reduced-motion evidence is obtained.
- Publication uses existing owner paths and proves a real deployed user journey.
- No claim of predictive improvement occurs without PIT replay and forward validation.

## 9. Current state and next action

This pass completed the previously missing dynamic-product reconnaissance. It did not refresh or ingest Finviz membership, settle source rights, implement Atlas code, alter P1, change any model, or deploy a page.

The next critical path remains:

1. conclude exact-head CI and independent review for P1 PR #7252;
2. reconcile publication-owner PR #7211 for current-run validation and deployed proof;
3. select and freeze one rights-safe real Atlas scope using the accepted compact observation model;
4. implement one shared Grid/Clusters/Bubbles/table journey through existing owners.

Do not repeat the dynamic Finviz interaction matrix unless a material product revision invalidates these observations.