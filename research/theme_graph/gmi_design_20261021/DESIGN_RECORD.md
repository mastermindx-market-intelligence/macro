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

## 9. Round 2 (2026-10-22): repair after REQUEST_REPAIR on #10054 @ `9559450d`

The coordinator reviewed round 1 and returned six defects (D1–D6). Round 2 repairs them on the same branch and PR.
It keeps the following unchanged: the copy deck, every §0 gate in SPECS, the tracked uppercase eyebrows (ZH stays
untracked per doctrine §13), and S3/S4/S5 apart from where the shared node idiom reaches them.

### D1. S1 composition: one signature ladder, two elevation levels

- **Before.** The S1 fold had six bordered panels at similar weight: answer, lineage ladder, facet, field table,
  unknowns and relationships. The ladder was four equal rungs, so "where Micron sits" read as a category walk
  rather than an answer.
- **After: one hero.** `.gmi-band.gmi-hero1` is the only raised surface. Its contents, in order:
  - the taxonomy ladder (`.gmi-chain--ladder`);
  - the held status ("Held for review");
  - the plain answer, below a hairline.
- **The ladder is anchored on the micro-theme.** "HBM & advanced packaging" leads with a 22px ring+dot pip at
  h1 scale. Each ancestor recedes in pip size, name size, weight and ink:
  - sub-theme: a hollow pip on a dashed connector ("None — sits directly under its theme");
  - theme: "AI Semiconductors";
  - category: "Semiconductors & hardware".

  Connector ink steps down 48% → 34% → 22%. The secondary parents stay one line under their step ("Also listed
  under Memory, HBM & Storage"), so the cross-listing is shown without a second ladder.
- **Below the hero: flat sections, plus one quiet side sheet.**
  - The flat sections are the value-chain facet and the proposal field table (`.gmi-flat`). They have no fill,
    no edge and no shadow, and are separated only by a rule.
  - "What we don't know yet" and "Documented relationships" share one side sheet (`.gmi-sheet`), with an
    internal divider.
- **Elevation budget.** Two levels: the hero and the sheet.

### D2. S1 light is a research workspace you can see

TP-0 law requires light to be a separate art direction, and a token swap is not one. In S1 light, five mechanisms
differ from dark and are visible without a toggle:

| Mechanism | Dark (command center) | Light (research workspace) |
|---|---|---|
| Hero | luminance wash + inset elevation | white card, hairline, two-layer shadow |
| Section heads | 1px `--gmi-hair` luminance hairline | 1.5px `--text` ink rule |
| Proposal field table | rows on hairlines | ruled ledger sheet: `--panel2` label column + vertical rule (`.gmi-dl--ledger`) |
| Side sheet | one luminance step (`--gmi-step`) + hair edge, no shadow | recessed tray: `--panel2` + `--gmi-tray` inset shadow |
| Held pip | ring + dot + bloom | ring + dot, no bloom |

The new token is `--gmi-tray`, a composition with no new hue: `none` in dark, `inset 0 1px 2px rgba(20,30,50,.05)`
in light. SPECS §4 carries the full table. Evidence:
- `png/s1_issuer_light_en_1440.png`;
- `png/r2/s1_dark_vs_light_en_1440.png`.

### D3. S2 at 390 keeps a compact jump

- **Before.** At ≤640 the category jump was hidden and only the group headers stuck.
- **After: a sticky jump strip** (`.gmi-jump`).
  - It is pinned at top 0, sits full-bleed, holds one line and scrolls sideways.
  - Mechanics: scroll-snap, a hidden scrollbar and a 32px edge fade that signals more chips. Chips are 40px tall.
- **Category headers** stick at 57px under the strip. Groups carry `scroll-margin-top:57px`, so a jump lands
  below both bars.
- **Behaviour.**
  - Clicking a chip opens the group and scrolls to it. The URL hash, which holds the lens state, is not touched.
  - An `IntersectionObserver` marks the current group's chip `aria-current` and scrolls it into the strip.
- **The DOM gate is unchanged.** Re-run after round 2, each of the four theme×lang cells at 390 shows 371 visible
  `.gmi-irow-name` elements, with the jump `position: sticky` and the header at top 57px.
- Evidence:
  - `png/r2/s2_index_{dark,light}_en_390_top1200.png`;
  - `png/r2/s2_index_{dark_en,dark_zh,light_en}_390_midlist.png`, a scrolled viewport with the strip and a
    header both stuck.

### D4. One node idiom

`.gmi-chain` (SPECS §11, CSS section O) replaces two different idioms:
- round 1's S1 rungs;
- round 1's S3/S5 path, which used bordered boxes joined by arrowheads (`.gmi-pnode` / `.gmi-pedge`).

The round-1 classes are removed from the CSS. The grammar:
- **Steps.** A step is a pip plus words. Pip shape is the state: **solid** = on file, **ring + dot** = held for
  review, **hollow** = nothing on file.
- **Connectors.** A connector into a hollow pip is dashed.
- **Shape split.** Circles are chain nodes and squares stay census cells, so the two survey idioms never collide.
- **Edge labels.** On S3/S5 they ride above their connector ("supplies · no condition stated").
- **Layout.** Above 760px the chain is horizontal. At ≤760px every chain becomes a vertical rail with labels
  under the node.

Where it applies:
- **S3's "Where this link leads":** Skyworks (solid) → Apple (solid) → a dashed hop to a hollow "No documented
  links from Apple yet".
- **S5's conditioned-path template:** the same chain.

Evidence:
- `png/r2/s1_vs_s3_node_pair_{dark,light}_1440.png`, the S1 ladder stacked over the S3 path at 1440;
- `png/r2/ba/s3_path_*` and `png/r2/ba/s5_path_*`.

### D5. Before/after boards (the capture record format is accepted)

The Paper file is **"GMI Explorer 2026-10-22 — Round 2"**. It is a new file because the round-1 file reached the
tool's size limit. It holds one board per changed surface, each with before and after on the same board:
- **S1 Issuer:** 1440, dark and light, plus the D2 mechanisms table.
- **S2 Theme index at 390:** the top of the page and mid-list.
- **S3 Relationships:** the path at 1440 and at 390.
- **S5 Degraded states:** the template path at 1440 and 390, plus the full states sheet, dark and light.

Each board was reviewed by screenshot. The before halves are in `png/r2/ba/*_before.png`. The after halves are the
regenerated matrix PNGs, or crops of them in `png/r2/ba/*_after.png`.

### D6. Regenerated matrix and checks

The generator re-rendered all 60 matrix PNGs: 7 stems × 1440/390 × dark/light × EN/ZH, plus 4 cells of
371-leaf proof. Checks run on the round-2 tree:

| Check | Result |
|---|---|
| 390 overflow, 6 pages × dark/light × EN/ZH | 24 of 24 cells `scrollWidth == 390` |
| S2 371-row DOM gate at 390, dark/light × EN/ZH | 371 visible `.gmi-irow-name` in all 4 cells; jump sticky, header top 57px |
| `scripts/check_design_system.py --mode enforce-added` (diff vs merge base `9b48e798`) | blocking = 0 |
| `scripts/check_ui_visual_evidence.py` (same diff) | rc 0 |
| `git diff --stat 9b48e798 -- templates site scripts engine config` | empty |

### Round-2 deviations

- **Regeneration and crops ran principal-direct, not on a fabric lane.** Each crop was a judgment call
  (which viewport, which scroll position shows the sticky strip working), interleaved with CSS repairs. Framing a
  packet for each would have cost more than producing the crop. No fabric worker started for this work.
- **A new Paper file** was created for round 2. The round-1 file is untouched.
- **`scripts/check_runtime_style_injection.py`** refuses to run in this sparse worktree, so it was not run. The
  round-2 specimens inject no runtime stylesheet: the only scripts are theme/lang/lens state, the index jump and
  its observer. The implementation PR runs the check in a full checkout.

### What changes for the implementation PR (in addition to §8)

5. Implement `.gmi-chain` once and use it for the S1 ladder, the S3 path and the S5 template. Never reintroduce
   path boxes or rungs.
6. Keep S1 at two elevation levels. Keep the five light mechanisms of D2 as written CSS, not as a token swap.
7. Keep the S2 phone jump strip, the 57px sticky headers and the hash-preserving chip click. Keep the 371-row gate.
