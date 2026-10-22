# GMI Explorer — design record (2026-10-21 / 22)

Author: ORCH-DESIGN (Opus 5.5 suborchestrator) under GMI Meta-CEO seat `6f14c2da`.
Deliverable: reference designs and an exact spec for five GMI product surfaces. No product code ships here.
Exact spec: `mockups/refs/gmi_explorer/SPECS.md`. References: `mockups/refs/gmi_explorer/png/` (60 PNG).
Paper file: "GMI Explorer 2026-10-21" (16 boards). Rendered against `templates/theme.css` at main `9b48e798a3eb`.

## 1. Brief

**User.** An authenticated investor reading in English or Chinese, on a 1440px desk or a 390px phone.

**Job.** Answer three questions in plain words, with the evidence one tap away:

1. What does this company actually do?
2. Where does it sit in the theme map?
3. Who does it depend on?

When an answer is not known yet, the page says so. A missing number is never drawn as a zero.

**Surfaces.**

| # | Surface | Archetype (MASTER_PRODUCT_DESIGN_SYSTEM_V1) | Status |
|---|---|---|---|
| S1 | Issuer explainer | C instrument_analyzer | Designed |
| S2 | Theme tree explorer: map with coverage and value-chain lenses, plus the full index | B discovery_board; the index uses B list mode | Designed |
| S3 | Relationship explorer | C, as an evidence task | Designed and documented; one real edge |
| S4 | Coverage & receipts | E intelligence_desk | Designed |
| S5 | Degraded states | States sheet | Designed |

**Mood: "Surveyed ground".** The map reads like a survey plate. The ground has been walked, every plot is marked, and
the honest marking for almost every plot today is "not yet surveyed". It does not read as a dashboard of live
signals. Membership in a theme is context, not a stance. No stance chip appears anywhere (doctrine A7).

**The bold move: survey marks.** Each of the 371 micro-themes is drawn as one cell, and the cell's shape carries its
meaning. Hue only reinforces the shape.

| Mark | Meaning | Count today |
|---|---|---|
| Solid | Admitted | 0 |
| Ring + dot | Held: proposed, not a member | 1 (Micron → HBM packaging) |
| Hatched | Core: one of the frozen 68 acceptance micro-themes | 67 empty |
| Dashed | Extended: one of the 303 display-tier micro-themes | 303 |

A single held flag among 371 cells is the honest picture of the program today, and the page is built to make it
legible rather than to hide it. The design still has to work when the 371 cells fill with admitted members. The
mark CSS was checked for that: a solid mark keeps its contrast in both themes.

**Two art directions (TP-0).** These are two designs, not one design with swapped tokens.

- **Dark: command center.** Depth comes from luminance. The hero carries a faint information wash. Elevation is an
  inset highlight plus a drop. The held mark gets a restrained bloom.
- **Light: research workspace.** A cool canvas carries white material. Structure comes from hairline rules, and depth
  comes from a two-layer soft shadow instead of glow. The held mark is a ring only. The stale veil becomes muted ink
  over a hatched band.

The mechanism table, the theme-specific degraded states and the evidence matrix are in SPECS §4 and §13.

## 2. Inputs read (read-only)

**Doctrine and design system**

- `docs/DESIGN_DOCTRINE.md` (wins on any conflict)
- `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`
- `mockups/design_system/specimen.html`
- `templates/theme.css`
- the `_site_nav` family, captured as `inputs/nav.html` (no third header)
- `ontology.html.j2` / `ontology.css`, preserved and not redesigned

**Data**

- The crosswalk on main (merged #10017).
- `data/theme_graph/probation/activity_proposals.jsonl` @ `64ef5131`.
- `research/theme_graph/coverage_20261019/coverage_report.json` @ `64ef5131`.
- The coverage-proof disposition record.
- The #10005 relationship objects @ `f955f52f`. These were read only; the PR is not on main.
- The seat's pre-registered premise table `describe_premises_v1.json`, used verbatim.

All of this is frozen into `mockups/refs/gmi_explorer/inputs/fixture.json`. The generator asserts the population
integers on every render: 371 / 68 / 303 / 1 / 0, US 1931, CN 1019.

## 3. Method

**Specimen pipeline.** A data-driven specimen generator, `build_specimens.py`, takes `fixture.json` and produces six
HTML pages. Each page links `templates/theme.css` plus one extension stylesheet, `gmi_explorer.css`. Playwright then
captures every cell of the matrix:

- 7 surface rows (S2 counts twice, once per lens)
- × dark/light
- × EN/ZH
- × 1440/390
- plus the four 371-leaf proof cells
- = 60 PNG

Every page × language at 390px was audited for `scrollWidth == 390`. Paper holds the captures as 16 review boards,
each of which was screenshot-reviewed.

**Why HTML first.** The implementation PR must reproduce the markup exactly. An HTML specimen is the implementation
source, and Paper is the review surface.

## 4. Critique rounds

Every surface was critiqued at least three times: at 1440 dark-EN, then at 390, then across the light and ZH cells.

### S2 Theme map (5 rounds, plus 1 on the value-chain lens)

**Round 1.**
- The tally read as a templated boxed KPI row.
- "Extended · not counted" wrapped.
- Census cells were too faint and too monotone in dark.
- The held mark was too subtle.
- The band card was double-nested.

Fixes:
- The tally became a hairline inline ledger.
- Mark density is now 78% in dark and 86% in light, with hatch at 40% and 30% respectively.
- The held mark got a ring plus dot, with a bloom in dark only.
- The band was de-nested.

**Round 2.** The census heading did not follow the lens. It now does. The coverage lens and the value-chain lens
each name what the cells mean.

**Round 3.** On 390px, the columns overflowed. `.gmi-cols` now stretches to a column at ≤900px. Tree rows truncate,
while index names wrap. Both are deliberate: the tree is a scan, and the index is a lookup.

**Round 4 (Light).** Glow does not exist in the light treatment. Census bands use hairline rules at radius 0, and
selection is a 2px ring.

**Round 5 (ZH).** No uppercase and no tracking. The scope strings stay in English (see GAP 25). Every ZH h1 stays
within budget.

**Value-chain lens.** Position is not on the frozen 68, so the lens renders an honest "position not set yet" band.
It does not invent a position.

### S2 Index (2 rounds)

- Default: the groups collapse, so the fold holds the answer plus two modules.
- `#open=all` opens every group. That state is the 371-leaf proof, captured after a DOM assertion that 371 names are
  visible at 390px.
- Index names wrap so a long micro-theme name never truncates into ambiguity.

### S1 Issuer (2 rounds, plus the cross-theme pass)

- The principal activity is "Not disclosed yet". No principal_business_activity rows exist, so the page does not
  guess.
- The admitted-activities ladder (micro → sub-theme → theme → category) shows the held proposal as HELD, with its
  reason and as-of date.
- Value-chain position: "Not set yet".
- The correction lineage is a "Read updated" chip that opens a dated list.
- Unknowns are printed in a dedicated "What we don't know yet" module.

### S3 Relationships (2 rounds)

- The hero pairs the claim with a figure, next to a facts grid showing direction, as-of date, source, lineage and
  magnitude.
- The verbatim filing excerpt sits one tap below, inside the hero.
- The deck sentence is a plain paragraph. It is templated, not a quotation.
- The Micron → HBM packaging state renders as HELD, with three facts: "proposed, not a member", "magnitudes
  undisclosed" and "graph use not granted".
- The 2-hop path is an honest empty-hop state laid out as a template, labelled "Conditioned path · layout only". No
  second documented hop exists.
- No propagation score and no predictive sign appear anywhere.

### S4 Coverage & receipts (1 round, plus fixes)

- The frozen denominators are one integer per population: US [1926, 1931] and CN [1, 1019], with 0 admitted.
- The Extended tier is reported separately.
- The precision sample reads "not measured yet", because it needs 200 admitted members first.
- The disposition ledger shows 68 = 67 empty + 1 proposed.
- The corrections log is included.
- Fixes:
  - The legend swatches did not render, because the selectors only hit `.gmi-stack`.
  - A capture-only aurora override was needed.

### S5 States (1 round, plus fixes)

- Ten state keys, each in EN and ZH, with an action and a dark and light treatment (SPECS §10).
- Fix: purpose_denied, empty and read_updated each gained a next step, because a dead-end state is a doctrine
  violation.

### Paper board pass

All 16 boards were screenshot-reviewed after placement; no further defects beyond those already fixed in the specimens.

## 5. Removals (kept out on purpose)

**Visual pattern**

- A boxed KPI tally row. It was templated and competed with the census.
- A double-nested band card.

**Signals that would overclaim**

- Any stance or direction chip on a theme surface (A7: membership is context).
- A propagation score, an exposure magnitude or a predictive sign on relationships. None exists in the contract.

**Things that would mislead or break a rule**

- `.mx-ladder` for the census. It carries Prophet semantics, so the census uses its own `.gmi-census`.
- A hidden zero for any unmeasured quantity. Each one prints "not measured yet" or "not set yet".
- Vendor names as taxonomy labels.
- Internal study or state names on Tier 1.
- Front-facing refutation language.
- Translated `title=` attributes. Tips use `data-tip-en` and `data-tip-zh`.

## 6. GAP list (fields or contracts the design needs that do not exist yet)

Each GAP names what the UI does today in its absence.

| # | GAP | UI behaviour without it |
|---|---|---|
| 1 | `value_chain_position` is absent on the frozen 68 | "Position not set yet" band; the lens stays honest |
| 2 | No correction-lineage field on activity or edge records | "Read updated" chip spec'd against a lineage list that has no producer |
| 3 | Rights state is unknown (G-R1) | Size withheld by default; "Open the filing" |
| 4 | The Micron witness is `planned_product_integration`, not SUPPLIES | Rendered as HELD with its own reason; never as a supply edge |
| 5 | No `principal_business_activity` rows | "Not disclosed yet" |
| 6 | 0 admitted activities | Every count shows 0 with a tier label; no fill |
| 7 | The precision sample is EMPTY_POPULATION until ≥200 admitted | "Not measured yet" |
| 8 | Exposure axes are null | Magnitude reads "Not disclosed" |
| 9 | The role enum lacks foundry, CDMO, licensor and distributor | Species are spec'd; only the supplier/customer edge is real |
| 10 | `.mx-ladder` is Prophet-semantic | Own `.gmi-census` (design-system GAP) |
| 11 | One edge only (SWKS → AAPL); no real 2-hop | Empty-hop template, "layout only" |
| 12 | G-DS1: `.mx-*` classes and `--sp`/`--r` scales live in the specimen, not `theme.css` | The extension consumes `theme.css` tokens only; the implementation PR must promote or restate them |
| 13 | The specimen's `.mx-error` uses a coloured edge, against doctrine | GMI states use labelled ink plus a hatched band |
| 14 | The Micron activity excerpt is not on main | Fixture carries it from `64ef5131` |
| 15 | No primary-category rule (`theme:hbm_packaging` has path_count 3) | The issuer view lists all paths; no primary is asserted |
| 16 | The edge `admission_state` is `proposed` | Shown as "Documented · not admitted" |
| 17 | Identity denominators and activity denominators can differ | One integer per population, labelled |
| 18 | G-DEN: precision bounds [1928, 1931] vs coverage bounds [1926, 1931] | S4 shows coverage bounds; the precision panel names its own population |
| 19 | No plain-word map for reason codes | The deck carries a draft map; it needs a contract owner |
| 20 | Most sub-themes are empty | An empty-sub-theme summary row inside the accordion |
| 21 | No issuer display-name contract | The fixture uses the filing name |
| 22 | `data-lens` attribute collision with the existing page lens | Uses `html[data-gmi-lens]` |
| 23 | `.gmi-tip` duplicates `.lens-q` | The implementation should reuse `.lens-q` |
| 24 | Tier names were renamed to Core/Extended for users | Mapping to acceptance/display tier in SPECS §6 |
| 25 | Some ZH scope strings stay in English (ticker and source identifiers) | Intentional; needs a ZH glossary owner |
| 26 | `aria-label` and `placeholder` cannot be bilingual in one attribute | The implementation swaps them on a language change |
| 27 | S5 state keys are specimen-only | The implementation needs a state enum owner |
| 28 | Index names wrap while tree rows truncate | Deliberate (§4); documented |
| 29 | Nav JS is not loaded in the specimens | The nav is a static capture of `_site_nav` |
| 30 | The capture used an aurora override | Capture-only, not part of the spec |
| 31 | Deck correction strings embed accession numbers | Mono, inline; needs a formatting owner |
| 32 | The deck magnitude sentence is templated | Rendered as a plain paragraph, never as a quote |
| 33 | Jump-nav `#id` links clobber the hash state | Implementation: scroll via JS or a separate state key |
| 34 | The path_template condition label comes from premise `concentration_risk` | Verbatim from the prereg table |
| 35 | The S4 100/100 sample split comes from the fixture | Display only until a sample exists |
| 36 | `.gmi-relgrid` uses CSS grid despite the flex-only header note | Grid is fine in product; flex-only applied to Paper port sections |
| 37 | `--accent` was undefined | Fixed to `var(--link)` |
| 38 | `.gmi-vh` sr-only spans sit past 390px | Clipped and not scrollable (`scrollWidth` 390); documented |

## 7. Deviations

- **Paper holds placed captures, not a native-vector rebuild.** The boards carry the rendered specimen captures for
  every matrix cell. The HTML and CSS specimens are the exact implementation source. Rebuilding 60 cells as native
  Paper vectors would duplicate the source without adding fidelity.
- **The optional ZH-naturalness GLM review lane was not run.** The ZH copy was authored and checked in-seat against
  doctrine §13 (no uppercase, no tracking, h1 budgets). A native-speaker or GLM naturalness pass remains a
  recommended pre-implementation step.
- **The commit trailer names Opus 5.5,** the model that actually authored the work.
- **The specimens link `templates/theme.css` by path but never edit it.** `git diff origin/main -- templates/` is
  empty.

## 8. What the implementation PR owes (summary; SPECS §0 is binding)

1. Port the exact markup and CSS from SPECS §5–§11. Tokens must extend `templates/theme.css` only.
2. Match every matrix cell (dark/light × EN/ZH × 1440/390) against `png/` and post the crops in the PR.
3. Keep the 371-leaf index at 390px with no horizontal scroll.
4. Bind each GAP above to a real contract, or keep its honest unknown state. Never a hidden zero.
