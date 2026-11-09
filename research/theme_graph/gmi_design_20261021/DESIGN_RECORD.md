# GMI Explorer — design record (2026-10-21 / 22)

Author: ORCH-DESIGN (Opus 5.5 suborchestrator) under GMI Meta-CEO seat `6f14c2da`.
Historical deliverable: reference designs and an exact spec. The active product implementation and consolidation scope is defined in §11, which supersedes prior design-only completion.
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


## 10. GMI editable makeover — completed 2026-11-03

Chairman assignment: substantially upgrade the GMI Explorer UI/UX and its theme system in the original Paper file. The complete static design and implementation handoff are delivered. This does not claim a production application deployment.

- Operation: `gmi-paper-makeover-20261103-sol`
- Paper file: `01M5H6EARN9YHQV17JC6ZG9BRY`
- Governing source: Mastermind `b2326bbe30e9988d26199f5e774a482b9c09068a`
- Product/data source: Macro `21444bcfd9001654935eb4b43b0005eb5a7eb47b`
- Displayed reference snapshot: 31 October 2026; original publication/on-file dates remain separate.
- Root was the sole Paper writer; independent readers reviewed visuals, data semantics, translation and exported variants.
- Original 16 reference boards remain intact on the archive page.

### Outcome and task tree

| Task | Outcome / DONE_WHEN | Dependencies | Final state / evidence |
|---|---|---|---|
| GMI-D1 | Inspect original boards and current product semantics | None | Complete: original raster reference census and current committed source census |
| GMI-D2 | Editable atlas and shared semantic/type/spacing system | D1 | Complete: 48 Paper tokens; native editable desktop and mobile atlas |
| GMI-D3 | Coherent detail/value-chain, index, issuer, relationship and coverage views | D2 | Complete: six desktop journeys in Noir and Day |
| GMI-D4 | Theme, locale, mobile and state coverage | D3 | Complete: six mobile journeys in Noir and Day; representative Chinese atlas at both sizes/modes; mobile filter sheet/value-chain lens; nine operational states in both themes |
| GMI-D5 | Actual captures, repaired defects, board map, native JSX and saved handoff | D3,D4 | Complete: 34 JSX +34 native JPEG exports, manifest hashes, no canvas overlaps, final static review accepted, handoff archive saved |

All design tasks are complete. The remaining implementation/browser/accessibility/deployment work is a separate stage, not an unfinished design claim.

### Final Paper structure

| Page | Boards | Link |
|---|---:|---|
| 01 · Desktop · Noir + Day |14| [Open desktop](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-2-0) |
| 02 · Mobile · Journeys & controls |16| [Open mobile](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-3-0) |
| 03 · System · Tokens & states |4| [Open system](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-4-0) |
| Archive · 21 Oct references |16 preserved| [Original references](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-1-0) |

Desktop Noir EN: atlas `9A-0`, detail `I4-0`, index `QH-0`, company `YU-0`, relationship `177-0`, coverage `1FK-0`.
Desktop Day EN: `26V-0`, `2F8-0`, `2KO-0`, `2RB-0`, `2W0-0`, `310-0`.
Desktop Chinese atlas: `4H1-0` / `4PE-0`.

Mobile Noir EN: atlas `35A-0`, detail `3NX-0`, index `3QZ-0`, company `3U1-0`, relationship `3X3-0`, coverage `405-0`.
Mobile Day EN: `38N-0`, `4XR-0`, `51O-0`, `559-0`, `58M-0`, `5C5-0`.
Mobile Chinese atlas: `3BP-0` / `3ER-0`; filter sheet `3HT-0`; value-chain lens `3KV-0`.
System: foundations `5FQ-0`; Noir states `5FR-0`; Day states `5X8-0`; interaction contracts `5FS-0`.

### Design decisions and preserved semantics

Mastermind Noir foundations with an intentional Day counterpart; Inter/PingFang SC with mono numeric detail; restrained blue actions, explicit state text and symbols, no colored container rails. Readable rows, category navigation and an evidence inspector replace tiny status-square walls. Preserve full index access, optional subthemes/multiple parents, coverage/value-chain lenses, issuer explanations, directed relationships and source receipts.

The current source snapshot has 371 micros (68 Core/303 Extended), one reviewed Micron company/link and zero held. Reviewed classification remains separate from graph-use permission. Micron's product/platform example retains Planned. Relationships remain proposed/unreviewed; Cirrus Logic→Apple retains 91% of seller revenue FY2026, 89% FY2025 and87% FY2024. Provisional U.S. and unresolved China denominators, unmeasured accuracy and untracked changes remain explicit. No live-feed, exposure, validation-score or production acceptance is fabricated.

### Final review and corrections

Root and independent reviews inspected the actual static compositions. All six Day desktop and mobile variants passed; EN mobile visible-text sequences match their Noir counterparts. Representative Chinese desktop/mobile Noir/Day layouts, all system states, filter sheet and value-chain view passed without clipping or remaining layout blockers.

Applied corrections include Taxonomy path wording; explicit global Core/Extended scope (Chinese 全库); Planned in mobile theme evidence; fiscal-year chart labels; neutral withheld-excerpt language; No recorded link yet in mobile index; disabled first-page Previous controls; and the exact 371-micro-theme value-chain denominator.

48-token hash: `ac191fd9`. Final finish operation: `gmi-paper-makeover-20261103-sol-finish-all-design-boards`, result `APPLIED_RESPONSE_OBSERVED`. No unresolved modifying effect remains.

### Saved handoff

`GMI-Explorer-Design-Handoff-2026-11-03.zip` — 3,992,532 bytes, SHA-256 `35319072a59e3e61b3bb2f59acf9ab21a77863152b28c18edfb687aa88c8c7d8`.

Contains an offline visual gallery, 34 native JSX snippets with node IDs, 34 unmodified JPEG captures, 48-token JSON/CSS, the full implementation/data/interaction contract, final page inventory and hashed manifest. Relative links, all content hashes and ZIP integrity were verified. Artboard dimensions and coordinates show zero overlaps.

Chinese atlas composition is supplied at both sizes and in both modes; separate Chinese deep-view/state mockups are not included. Their complete language parity is an implementation requirement.

No live product build, merge, deployment, authentication change, qualification promotion, parent runtime-wave update or source-law change was performed. Implementation should use the existing governed navigation, theme/language controller, components, readers and permissions, then obtain ordinary real-path/browser and accessibility evidence.

## 11. Chairman-directed product rebuild and file consolidation — ACTIVE, 2026-11-03

### Authority, feedback and custody

The Chairman resumed this assignment and explicitly required execution and implementation, rejected the current design/product as mediocre and unclear, and directed consolidation of the two GMI Paper files. This supersedes §10's visual acceptance and separate-stage boundary. Prior exports remain historical evidence, not current production acceptance.

Original operation root: `gmi-paper-makeover-20261103-sol`. Current attended parent/source operation: `gmi-product-upgrade-20261103-sol`. New bounded implementation child: `gmi-product-upgrade-20261103-model01`. These are source-custody continuity identifiers on the existing trusted connection, not new authentication or runtime authority. No prior active or uncertain effect is transferred. Root owns product judgment, Paper edits, integration and acceptance; bounded Fabric workers own only commissioned code paths. Native consultations are read-only reasoning/census.

Protected law: Mastermind `9f65957e29eba92245d78609f032aaea523b7cb4` (compatible Sol skillpack 1.0.1/bootstrap 1).
Product base: Macro `b8f14e308b57cd772e1464217e1e2becc1286086`.
Earlier source materialization at `12c551c2512fc57e12743fac17a2874e001cf6db` is compatible for inspected GMI paths; eight critical blobs were rechecked at b8f14e3.
Source branch: `claude/gmi-product-upgrade-20261103`. Existing workstream: `agentos/workstreams/WS-GMI-THEME-GRAPH.md`; parent program and D2E/W3 closure remain with their existing owners.

### Product contract

Persona: a research reader using English or Chinese on desktop or phone. Primary job: understand a theme, identify a documented business connection, inspect the dated source and limitations. The first viewport must communicate that job without requiring taxonomy/status-code literacy.

Tier-1 title: **GMI Explorer**.
Deck: **Understand themes, business connections, and the evidence behind them.**
Main workspace: answer-first theme research; relationship research is a separate capability. Coverage, full taxonomy and technical receipts remain available without dominating the opening answer.
A selected theme must explain its meaning using approved definitions when available, show taxonomy context, show only permitted documented company evidence, and distinguish absent evidence from absent real-world participation. Never invent definitions or company links from labels.
The Micron example retains Planned and the 26 February 2024 source date alongside its claim. Product context is Micron → 24GB 8H HBM3E → NVIDIA H200; this is not inferred revenue exposure or a qualified supply-chain graph.
Search/filter/select state must be addressable, restore through browser history, work in both locales, support keyboard/focus/touch, and have useful zero-result recovery.

### Current truth and permission invariants

- All 371 themes and multiple-parent context remain navigable; Core/Extended describes scope, not completed review or an investment ranking.
- Current relationship package: 248 records, 165 distinct endpoint companies, 283 distinct coverage issuer IDs. These populations must never be conflated. Package is proposed as of 21 October 2026.
- All current relationship records have public_display, magnitude_display and excerpt_display = unknown, with purposes private_api/research. Public GMI HTML/JSON MUST NOT contain restricted records, parties, magnitudes, excerpts or hidden payloads. Enforce permission before serialization/rendering; do not implement CSS-only hiding or infer rights from a public source URL. Public aggregate context uses approved package fields only. Rich relationship browsing is available only from a lawful permitted projection/context; no new grant or auth bypass.
- The old MU graph_membership_use=NOT_GRANTED is stale. The existing APPEND event and bridge receipt authorize internal graph use. The owner state remains NOT_QUALIFIED / D2E_UNSEALED and graph synchronization disagrees (0 materialized, 1 projected). All gate/materialize/publish/qualify/rank/size authority remains false. This UI reads existing owner outputs; it does not write or reinterpret authority.
- Missing, denied, unknown, stale, failed, empty and loading are distinct. Freshness uses actual source/package/build clocks, not a fabricated live-feed timestamp.
- Do not consume the frozen 19 October coverage report or design fixture as current production data.

### Paper consolidation and visual contract

Canonical file: `01M5H6EARN9YHQV17JC6ZG9BRY`.
Original entry `p-1-0` becomes the current product entry, after moving the original 16 references to an explicit historical page.
Secondary file: `01M5J3GC90GAKHK8B6SAPRV3JQ` (Round 2), four historical boards `1-0,1D-0,29-0,3D-0`. Preserve unique reference content inside the canonical file before marking the secondary file superseded and pointing to the canonical destination. No third GMI file. If archive/delete is unavailable in the guarded catalog, do not bypass it.
Root is the sole writer for these specific consolidation/new-board effects. Each mutation uses current target read, fresh snapshot and stable operation ID; unknown effects are reconciled on the original carrier.
Dark: restrained luminance hierarchy, selective raised interaction surfaces, neutral fine rules, deliberate answer typography.
Light: cool canvas, white research surface, crisp hairlines, controlled layered shadows and neutral selection. Shared semantics/geometry, different material mechanisms; palette swap alone is insufficient.
Use governed theme tokens and existing shared navigation. No colored container-edge stripes, parallel theme system, duplicate header, speculative charts or unsupported metrics.
Actual Paper screenshots and JSX follow visual acceptance; browser screenshots prove the integrated product separately.

### Task tree and DONE_WHEN

| Task | Dependency | Required outcome | Status |
|---|---|---|---|
| GMI-P1 | None | Live two-file census, current data/rights/custody, preserved advanced functions | Proven read-only |
| GMI-P2 | P1 | One clear canonical Paper entry; four Round 2 references consolidated; prior versions marked historical | Active |
| GMI-P3 | P1 | New answer-first compositions, distinct Noir/Day, EN/ZH and desktop/mobile; actual visual review | Active |
| GMI-P4 | P1 | Render-boundary rights, current MU status from owner outputs, deterministic searchable/selectable model, meaningful tests | Ready for bounded worker |
| GMI-P5 | P3,P4 | Real template/CSS/JS implementation in existing routes, no raw restricted payload, full user journeys and recovery | Pending |
| GMI-P6 | P5 | Current builder, relevant regression/design checks, browser matrix and independent exact-head review | Pending |
| GMI-P7 | P6 | Reviewable coherent candidate, ordinary approved release path, verified served behavior where authorized | Pending |
| GMI-P8 | P2,P3,P6,P7 | Durable exact Paper/source/proof record; clear distinction between candidate, merge, deployment and acceptance | Pending |

Implementation seam: scripts/build_gmi_explorer.py, scripts/gmi_explorer/{model,present,variants}.py; templates/_gmi*.html.j2, templates/gmi*.html.j2, templates/gmi.{css,js}; paired generated site/gmi*; relevant existing GMI tests plus focused regressions. Do not modify shared theme.css/nav, identity/security owner files, history/bridge producers or active PR #10638 paths. PR #10641 remains separate identity research; #10654 owns shared accent-stripe cleanup.

Build must preserve lib.pages.write_page and shared _site_nav/_navlinks/theme.js/supabase.js. Use current proof and real model. A saved current --model-in is allowed for isolated render; synthetic fixtures are tests, never production facts. Generated CSS/JS must match templates byte-for-byte.

Acceptance: a reader understands purpose in five seconds; can find/select a non-default theme, inspect permitted evidence, follow a company/source path, share and restore state, clear an empty search, use keyboard and a 390px phone, and read equivalent EN/ZH in both themes. Relationship denial is enforced at serialization and explained plainly; lawful future GRANTED records support real search/filter/select rather than hardcoded edges[0]. A rendering, passing CI, PR or deployment alone is not acceptance.

### Execution controls and current frontier

Direct retention reason: PRINCIPAL_JUDGMENT for product/visual decisions; UNIQUE_APPROVED_ACCESS for canonical Paper effects; integration remains with root. Routine bounded source work will use qualified Fabric if admitted; no provider/model/authority invention.
Git proxy authentication was unavailable, but authenticated GitHub reads and Git-data writes are available. Exact-source materialization and atomic tree/commit/ref publication remain lawful. No credentials or infrastructure change is requested.
Read-only census found no frontend-path overlap with #10638. There is no claimed file-wide lease.
Next: verify this plan readback; commission model/projection slice; consolidate Paper; implement/review the visual frontend; prove actual browser journeys and pursue the ordinary release gate.

### 11.8 Current execution frontier — consolidation and product implementation
- Paper consolidation is visually verified. Canonical file `01M5H6EARN9YHQV17JC6ZG9BRY` is now **GMI Explorer · Product system**, with `p-1-0` as the current-product entry. Original references are preserved on `p-5-0`; Round 2 boards were imported as `61N-0`, `62X-0`, `63T-0`, `64V-0`, and all 21 owned raster fills were restored and screenshot-checked.
- Secondary file `01M5J3GC90GAKHK8B6SAPRV3JQ` is renamed **Archived · GMI Round 2 · merged into Product system**. Its first page contains canonical pointer `4N-0`; original Round 2 boards remain on its archive page. Rename timeout was reconciled against the same exact file and observed name; no Paper effect remains unknown.
- Current answer-first product boards: Noir desktop `61M-0`, Day desktop `6A7-0`, Noir mobile `6DR-0`, Day mobile `6FY-0`. An independent critique was applied: topic hierarchy strengthened, source publication date placed beside Planned, platform label corrected, evidence coverage made explicit. Day has separate surface/shadow/recessed-ledger treatment. These boards establish visual direction, not product acceptance or shipped proof. Chinese variants and final state review remain.
- Model child `gmi-product-upgrade-20261103-model01` ended **EFFECT_UNKNOWN**, `remote_cleanup_unproven`, lease `868f3981b9bd` preserved. Root/parent remain unverified; result consumption is denied. No result was consumed, no retry or successor dispatched, no retained receipt was accessed through another carrier. Original model/presentation/test paths in §11 remain fenced.
- Exact model-lane gate: original installed Fabric owner must reconcile this same run/root/parent/process/lease and publish an eligible terminal status through its existing owner. No applicable exposed settlement action was found. This blocks only that lane.
- Root continues principal visual/integration judgment in disjoint existing GMI templates, CSS, JS, and production render integration. Next action is actual frontend construction, followed by fresh-source build and browser validation. Current binary source acquisition uses ordinary Macro repository objects only and must not access the fenced worker result.
- Current source remains Macro `b8f14e308b57cd772e1464217e1e2becc1286086`; public relationship permissions remain unknown for all current records. The public renderer must not emit restricted records, parties, amounts, excerpts, or search payloads. The actual public permission state is an intended product path.
- **DO_NOT_REDO:** accepted consolidation/imports and completed visual refinements. **MORE_WORK_EXISTS:** frontend implementation, real browser journeys, accessible mobile/keyboard/history/copy flows, current permission enforcement, focused validation, exact candidate/review/release, and durable evidence.

### 11.9 Implemented product candidate and real browser proof — 2026-11-03

The Chairman's resumed instruction includes implementation, product clarity and consolidation of the two Paper files. The root retained principal product judgment and owned the disjoint frontend integration. This section records the resulting candidate; it does not close the parent GMI data program or establish production delivery.

#### Product behavior and preserved depth

The primary journey now answers, in order: which theme is selected, what that theme means, which dated company/product connection is documented, what the source does not establish, and where the reader can inspect the company or source. The current Micron claim is explicitly historical and planned: “Micron planned HBM3E for NVIDIA H200.” The 26 February 2024 source date sits beside the planned lifecycle. Current delivery, deal size and revenue exposure are not inferred.

The implementation includes seven generated public routes: `gmi.html`, `gmi-companies.html`, `gmi-issuer-mu.html`, `gmi-relationships.html`, `gmi-index.html`, `gmi-coverage.html`, and `gmi-states.html`. The company catalogue is a real searchable route; the issuer view renders all eligible documented connections rather than taking only the first link.

All 371 microthemes remain addressable. Search covers English/Chinese topic names, classification paths, company names, tickers and named products. Category filtering considers every actual parent path. Core/Extended and evidence-only filters, URL state, browser back/forward restoration, related themes, source receipts, the full index, taxonomy tree, coverage census and value-chain lens remain available. Advanced detail is disclosed after the primary research answer.

On mobile, the same browse component moves into a native dialog rather than creating a second search owner. Escape, focus return, selection focus, roving result tab stops, empty results and reset behavior are implemented. Link copying confirms success only after the actual clipboard succeeds; denial provides a selectable address. Server-rendered evidence and the full index remain usable with JavaScript disabled or a malformed interactive payload.

The existing shared theme/language controllers and Brain owner remain authoritative. Brain's original root container is docked in the product header, retaining its tokens, delegated handlers, lazy loading, language and focus behavior. Header paragraph selectors are scoped so they cannot alter Brain message styling. No second theme, language, authentication, chat, storage or publication controller was created.

All new GMI color treatments consume existing canonical theme tokens. Day mode uses white surfaces, recessed context and the existing elevation; Noir uses the existing dark materials and hero wash. Chinese tracking remains natural. Final visual corrections separated the coverage band from the following sections, grouped denominator help with its text, spaced the publication icon/label, and preserved contrast on the selected topic. The unsupported specimen sampling threshold was removed because the source model supplies no such rule.

#### Public-data boundary and outstanding model work

The template payload is a presentation allowlist of topics, paths and current reviewed product cards. It does not serialize the raw model, relationship edges, party names, deck or private correction lineage. Rejected/unreviewed product records are excluded. Source links are restricted to HTTP(S), and text/JSON escaping is verified.

The current relationship model contains internal observations without a verified public projection. The public route therefore withholds relationship identities, facts, amounts, excerpts, package receipts and hidden search payloads. Its empty presentation clearly describes a publication restriction, not an absence of relationships. The state reference contains generic examples, preserves the original state keys and adds confirmed-action success; it does not publish provider-derived examples or simulated incident timestamps.

ACCEPT/RATIFIED filtering is **not** a general public-fact permission rule. The separately cleared current source fact is distinct from internal graph-use permission. Broader qualification and the owner-supplied public projection remain unfinished in the fenced model lane. No frontend rendering result is offered as a substitute for that work.

The original `scripts/gmi_explorer/model.py` and `present.py` remain byte-identical to base, with Git blobs `2614997dd87bf7d7e2d0b61b283c6b364801e1b1` and `c5ae61d80a484c07d583831577db52881843061b`. No retained worker result was consumed. The original model test file also remains upstream-identical. A historical name test initially lacked its 21 October input in the isolated materialization; fetching the exact original snapshot resolved it without changing model or test behavior.

#### Canonical Paper home and current boards

Canonical file: `01M5H6EARN9YHQV17JC6ZG9BRY`, **GMI Explorer · Product system**, current page `p-1-0`.

| Current product variant | Board ID |
|---|---|
| Noir / desktop / EN | `61M-0` |
| Day / desktop / EN | `6A7-0` |
| Noir / mobile / EN | `6DR-0` |
| Day / mobile / EN | `6FY-0` |
| Noir / desktop / ZH | `6I6-0` |
| Day / desktop / ZH | `6LQ-0` |
| Noir / mobile / ZH | `6PA-0` |
| Day / mobile / ZH | `6R7-0` |

All eight are actual editable Paper boards and have screenshot plus JSX exports under `product_20261103/paper-*`. The secondary file `01M5J3GC90GAKHK8B6SAPRV3JQ` is explicitly named **Archived · GMI Round 2 · merged into Product system**. Its first page points to the canonical home through board `4N-0`; its four originals remain in history. The consolidation is not a claim that the secondary file was deleted. The four imported reference boards and all 21 raster fills were preserved and inspected as recorded in §11.8.

The final Paper working indicators were released through observed operation `gmi-product-upgrade-20261103-sol-release-final-claim-boards`. The 48-token hash remains `ac191fd9`; no Paper effect is unresolved. Do not repeat the accepted consolidation.

#### Verification and durable proof

- Full incumbent GMI suite plus the new public-view suite: **148 passed in 57.38 seconds** at the final candidate. This includes the original model and reason-code tests, source rendering/round-trip, taxonomy and denominator arithmetic, safe output, source/date/stage, injection, paired assets and route coverage.
- Real headless Chrome **156.0.8078.80**, fresh anonymous profiles on the authorized M2: **64/64 cases passed**, with no uncaught page exceptions. Every one of the seven routes passed desktop/mobile × dark/light × EN/ZH checks, including horizontal geometry and one H1. The remaining cases exercised real product navigation, search, history, dialog/focus, copy success and injected denial, malformed-payload fallback, no-JS rendering, reduced-motion configuration and the existing Brain open/close path.
- **66 original PNG captures**, with actual dimensions, byte counts and SHA-256/Git hashes. The canonical `mastermind.p0_evidence.v2` manifest covers **56 REST cells plus four actual desktop EN hover/focus captures**, and the existing `mastermind.page_evidence_receipt.v1` receipt owns the changed GMI templates/assets. Additional screenshots show selected-empty, no-results, company/publication and Brain-restored paths.
- Canonical artifacts: `mockups/evidence/gmi-product-20261103/EVIDENCE.yml`, `manifest.json`, `browser-report.json`, `capture-metadata.json` and the PNGs. The exact generated HTML/CSS/JS hashes match the bytes served to the browser. The executable browser proof is `research/theme_graph/gmi_design_20261021/verify_product_browser.py`.
- The design-system added-line gate reports zero blocking findings. The GMI JavaScript has zero runtime-style injection signatures. The full-estate runtime ratchet and hosted CI remain distinct from this scoped check.
- Independent read-only review inspected primary and secondary captures and the shared-owner integration. It found the Brain root/style ancestry issue and the three coverage/publication spacing issues; these were fixed and recaptured. The independent final review of both coverage captures and mobile Chinese publication status returned PASS: all three spacing/help issues resolved, with no clipping, overlap or loss of context.

The browser proof uses generated public pages on a loopback HTTP server. It does not establish authenticated backend flows, external-source availability, production performance, native branch-protection enforcement, merge, deployment or live URL acceptance. Clipboard-denied and malformed-payload scenarios are explicitly injected faults; they are not claims of observed production incidents. Network-response/console telemetry and performance timings were not measured. Long-index screenshots may show the initial viewport; full-document horizontal geometry and every index target were checked separately.

The existing `gmi-explorer` CI job now includes the new public-view test, `_gmi*` partial-template selection and its explicit BeautifulSoup dependency. No new workflow or deployment plane was introduced. Current main was rechecked at `8bc2f6f211636874a3b0438700f818ac908ef3bd`: all 23 existing candidate paths still equal the original base, all eight new paths are absent, and the canonical design record on main is unchanged. The branch retains its earlier scope/consolidation record.

#### Exact remaining release gate

The original Fabric run `gmi-product-upgrade-20261103-model01`, root `gmi-paper-makeover-20261103-sol`, parent `gmi-product-upgrade-20261103-sol`, controller PID `38742`, lease `868f3981b9bd`, remains fenced as **EFFECT_UNKNOWN / remote_cleanup_unproven / ROOT_UNVERIFIED**. Result consumption was denied and the retained result was not read through another carrier. The same run/process/lease must be reconciled by the original installed runtime owner and an eligible terminal status published before its result or affected model paths can be resumed. No applicable settlement action is exposed in this session.

Until that settlement, owner-qualified public projection, concluded CI, normal release and live user-path verification are complete, this remains a verified frontend candidate. Do not arm merge or infer production acceptance from the screenshots, test counts, Paper edits, JSX or commit. Preserve the same branch, root, writer and model fence; do not dispatch a replacement or recreate fenced work in another file.



### 11.10 Company-evidence completion and native-site hardening — 2026-11-04

Chairman direction: resume the actual Paper design and native-site implementation, resolve blockers rather than repeating status-only checkpoints. This continuation preserves the existing branch, operation root, current data permissions and no-merge/no-Ready/no-enqueue/no-relabel boundary. Direct execution rationale: PRINCIPAL_JUDGMENT for visual acceptance and LOWER_TOTAL_OVERHEAD for completing the already-owned disjoint frontend patch. No new model worker was dispatched.

**Implemented capability.** The company catalogue now explains each eligible product connection before drill-down: company/ticker, theme, product, named platform, publication date, lifecycle and original HTTP(S) source. It renders all eligible connections, includes a server-rendered result count and zero-evidence state, and gives clear limits beside the result. Desktop uses a broad evidence list with a reading guide; mobile stacks the same content. Existing classification filters are preserved, not promoted into a general public-permission rule.

The existing URL-state implementation now retains theme/filter/search context through Coverage, Full Index, Relationships and state-reference visits. Index search survives reload, preserves unrelated lens/open/return keys, and Escape clears it without losing the other keys. Company and issuer return behavior, new-tab safety, keyboard focus, malformed-payload recovery and the shared Brain remain intact. No second router, state store, theme/language controller, authentication owner or data-publication path was added.

**Corrected proof/source mismatch.** Commit 2144ca13 contained the return-context JavaScript and regression script but omitted two return-context CSS rules used by its 74-case local browser proof. This continuation commits those rules in both paired assets and recaptures the actual candidate. The older 74-case proof is not treated as exact-style proof of 2144ca13. A new company-symbol radius fallback was caught by the incumbent primitive test and corrected to the existing 10px button token; no test was weakened.

**Native implementation.** Eight source/test paths change: templates/gmi.js, site/gmi.js, templates/gmi.css, site/gmi.css, templates/gmi_companies.html.j2, site/gmi-companies.html, tests/test_gmi_product_public_view.py and research/theme_graph/gmi_design_20261021/verify_product_browser.py. The company HTML was generated through the real build_gmi_explorer / make_env / lib.pages.write_page pipeline using exact committed source inputs, without model/presentation modifications or the fenced worker result. Missing materialization dependencies were restored from the same immutable source, including the shared data_base.js injection. The six other generated HTML routes remain byte-identical to 2144ca13. Coverage retains its committed 3 November snapshot; this UI patch does not publish a new review-ledger date or reorder coverage reasons. The generated CSS and JavaScript exactly equal their template sources.

**Paper delivery.** The canonical file remains 01M5H6EARN9YHQV17JC6ZG9BRY, page p-1-0. The eight current theme-research boards and the completed two-file consolidation are preserved. Two additional editable boards complete the company-evidence direction:

| Board | Native ID | Size |
|---|---|---|
| Company evidence / Noir / EN / desktop | 6VF-0 | 1440 × 1090 |
| Company evidence / Day / ZH / mobile | 6Y9-0 | 390 × 1727 |

Actual direct-Paper screenshots were inspected; inherited text and SVG contrast defects were corrected and re-inspected. The mobile layout is genuinely rearranged and translated, not a scaled desktop screenshot. Final company-card JSX was read from node 6X2-0 after visual QA. Both boards' working indicators were released through observed operation gmi-product-upgrade-20261103-sol-company-finish01. Snapshot 3eb8340a707e6ffd1b2ef55b35f91d5894be95542a75d631662cd2ac16b44fe7; token hash ac191fd9 unchanged. The screenshots above were native MCP observations, not invented on-disk Paper exports; the repository PNGs are separate actual browser captures.

**Verification.** The final exact candidate passed 151 incumbent-plus-public-view tests without warnings using an operation-owned temporary directory, and 92/92 real Chrome browser cases with zero uncaught page exceptions. The added cases cover context returns from secondary routes, date/lifecycle/source visibility on company results, and persisted full-index search across desktop/mobile, Noir/Day and EN/ZH. Additional server tests prove multiple connections, unsafe-source withholding and useful no-JavaScript empty results. Three representative browser tests failed on the prior implementation before their corresponding fixes.

The existing design-system enforce-added check passed with zero added blocking findings, and the existing visual-evidence validator passed against the actual eight-path diff. Ninety-one original PNGs (including 56 REST matrix cells and four real hover/focus cells) are hashed in capture-metadata.json; the existing page evidence receipt and 60-state manifest are refreshed. All nine GMI browser-input hashes match the files intended for this commit. These are generated-public, fresh-anonymous browser checks, not authenticated-backend, live deployment, performance or user acceptance claims. The repository-wide/hosted checks remain distinct from the 151-test local GMI suite.

**Remaining original-model fence.** Run gmi-product-upgrade-20261103-model01 still requires original-runtime reconciliation; root gmi-paper-makeover-20261103-sol, parent gmi-product-upgrade-20261103-sol, controller PID 38742, lease 868f3981b9bd. The original Fabric controller-output read now reports no retained session for that PID but explicitly does not prove execution absence. No result was consumed, no lease/root was rewritten, and no replacement was dispatched. The exposed Fabric catalog has no settlement action; Executive session_targets reports the installed Session Bridge owner unavailable. A bounded Slack coordination send was blocked by the platform, was not delivered, and was not retried or rerouted. No background worker or observer is claimed. These observations preserve EFFECT_UNKNOWN; they do not clear it.

**Release boundary.** The frontend and Paper improvements are implemented and locally validated. Production release remains gated by that exact original-run settlement, the existing qualified public-data projection and ordinary protected release/live-path verification. Required non-author approvals, if any, cannot be satisfied by this source writer. The existing hold, noindex posture, no-merge/no-Ready/no-enqueue/no-relabel instructions remain unchanged. Do not repeat accepted consolidation, regenerate already-proven frontend work without a material invalidator, consume the denied model result through a different carrier, or infer production completion from this record.


### 11.11 Submitted-diff validation and evidenced CI repair — 2026-11-04

This continuation starts from PR #10676 head `8a612a8e818bc49ab6de532508784a3dec9afbb9` and preserves every accepted outcome in §11.10. The source-law pin is protected Mastermind/master `b5e8a9682f72b1bf802e50cf16f77f878ce596f3`, bootstrap major 1. Direct execution is the bounded repair of an observed integration failure; no new model worker or Paper writer was admitted.

**Consumed evidence.** The already-started Studio process 15509 completed successfully (exit 0); its design-system validation used the actual submitted PR diff, 2,242,182 bytes, with zero added blocking findings. It was not rerun. Hosted CI run [41770439156](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41770439156), attempt 1, has concluded. Eleven of twelve packs passed, including the GMI job with **151 passed in 81.20 seconds**. Contract-delta passed. The final semantic evidence contains 117 logical jobs and identifies one failing logical job: product-experience-registry. Its page-registry contract failed because the upstream test expected six surfaces while the accepted GMI builder correctly adds Companies as the seventh. The two subsequent design-system steps in that logical job did not run after the failure; they remain owed in successor CI. No unrelated failure was inferred from the aggregate red gate.

**Exact source integration and repair.** CI tested merge commit `08f1132e0206667df80c9285ee70124837d0b78e`, tree `b54ab791fa84fecb1cfb69f8293d81c1c7d180d0`, composed from main `4a2291747fd2d8d364a3838e1ed2263636bc64a6` and the candidate head above. The registry test and its expanded scanner arrived on that tested main after the candidate branch diverged. This repair uses that actual tested composition in a normal two-parent integration commit on the existing source branch: first parent is the accepted candidate, second parent is the tested main. It does not merge the PR into main. Relative to the CI-tested tree, only this record and `tests/test_build_product_page_registry.py` change. The test now requires the exact seven-surface set, including `("/gmi-companies.html", False, "gmi_companies.html.j2")`, and its name says seven surfaces. No assertion was relaxed and no upstream scanner tests were discarded.

**Focused red/green proof.** The original six-surface assertion failed locally against exact immutable CI source inputs with the same unexpected Companies tuple. After the two-line contract repair, all **81 tests in tests/test_build_product_page_registry.py passed in 0.70 seconds**. Validation used an isolated evidence directory on the existing authorized M2, exact scanner/GMI/ontology builder/config/registry/conftest blobs, and an operation-owned pytest temporary directory; it did not mutate the primary checkout. The repaired test blob is `cd3f8a7f9677d87c30a041b758da2e81697371c7`. Logs are retained at `/Users/chriswong/agent-evidence/gmi-10676-registry-ci-41770439156-2w0h1bcb/registry-before.txt` and `registry-after.txt`. This is focused module proof, not a claim that the full-estate registry build or successor hosted CI already passed.

**Preservation.** Before repair, all 29 candidate-owned implementation/test files compared across the accepted head and CI-tested composition were byte-identical. The complete mockups tree, including the 91 PNG captures, has unchanged tree SHA `c3862605dd4ecd5b1dfdc280baba8ae6f0185b23`; the research/theme_graph subtree was also identical before appending this record. The shared theme, navigation, Supabase/data-base assets and fenced scripts/gmi_explorer subtree were unchanged. The completed Paper consolidation, ten product boards, 151-test GMI result and 92-case browser proof remain accepted. They were not regenerated or rerun. No UI change in this repair invalidates that proof.

**Original-owner reconciliation remains unresolved.** The same run `gmi-product-upgrade-20261103-model01`, root `gmi-paper-makeover-20261103-sol`, parent `gmi-product-upgrade-20261103-sol`, controller PID `38742`, lease `868f3981b9bd` remains fenced. A fresh owner status reports EFFECT_UNKNOWN, ROOT_UNVERIFIED, EXECUTION_NOT_ELIGIBLE, no authorized result consumption, no retry/dispatch authorization and no proof of execution absence. The exposed Fabric catalog has no settlement action. Executive V2 reports its backend unavailable; Executive V3 reports the installed Session Bridge owner unavailable. A bounded read-only inspection of the selected incumbent owner generation `8cefc4b27b2036f86bcec1d626e864f45f792e2c290ab8de56fbde89f78ac94a` established that its reconciliation/observation helpers have closed scope for other historical runs, not this November run. Those ineligible helpers were not invoked. No result was read through another carrier, no root/lease/status was rewritten, and no replacement or retry was dispatched. The blocked Slack and PR-note sends were not retried.

**Continuation and release boundary.** The next CI evidence must bind the successor head on the same branch and resolve the registry job, its two previously unrun steps and the normal aggregate gate. Original-model reconciliation must continue only through its existing eligible installed runtime owner for the exact tuple above; the current client has no applicable admitted settlement action. Until owner settlement, qualified public-data projection, protected release requirements and real live-path verification are complete, keep the PR Draft, noindex and all existing no-merge/no-Ready/no-enqueue/no-relabel holds. No production completion, background observer, terminal model result or user acceptance is claimed.

### 11.12 Public-fact render-boundary hardening — 2026-11-04

The accepted §11.10 Paper consolidation, 10 product boards, 151-test GMI suite, 92-case Chrome proof and 91 original PNGs remain DO_NOT_REDO. The registry correction at §11.11 passed hosted successor CI [41777490547](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41777490547): all 12 packs, contract-delta, the 81-test product registry and the previously skipped 69/97 design-system steps passed; aggregate ci-gate SUCCESS. Fences [41777490350](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41777490350) SUCCESS. These passes bind the previous exact head `f328fe875d48db8392533ff649271d687961219d`, not this new hardening commit.

**Reproduced risk, not a production incident.** The existing Jinja public-topic list admitted any future product with curation ACCEPT and status RATIFIED, even where `emission_state` remained unresolved. A controlled Jinja render demonstrated that a synthetic unqualified company/product fact then enters the public topic JSON. Separately, the builder emitted issuer pages for every model issuer and did not retire previously generated issuer pages after a rights withdrawal. No actual unauthorized production record or incident was observed.

**Targeted correction.** The frontend builder now supplies Jinja a bounded public presentation model. Only the separately cleared existing Micron planned-product sentence remains visible, bound to the exact proposal, issuer, microtheme, status, source key/span SHA, publication date, product/platform/lifecycle and original source URL accepted for the current snapshot. The upstream `source_rights.public_emission` remains unresolved: this narrowly preserves the already accepted factual display; it is not a new source-rights grant, graph-use permission, relationship publication projection, or general ACCEPT/RATIFIED admission. All other issuer facts remain withheld until the existing owner delivers a qualified public-fact projection. Raw edges and party_names are excluded from the template context. The builder emits only cleared issuer pages and retires stale feature-owned `gmi-issuer-*.html` output; a nonregular/symlink target refuses rather than being followed or removed.

The public-view suite adds negative future-issuer and future-link cases, four exact-fact-change/revocation cases and a symlink refusal. The existing HTML/JSON escaping regression now mutates an issuer display name, not the provenance-bound product fact. The separate multi-record renderer test retains its own synthetic test-only qualification to check multi-connection and unsafe-URL behaviour without pretending it is a production rights grant. A pure AST/synthetic source-level probe compiled the builder and tests, retained the current Micron fact, withheld an unqualified issuer and private edge context, refused altered clearance and validated stale output/symlink guards. This is **not** yet a full hosted or live browser acceptance for the new head.

The original model run `gmi-product-upgrade-20261103-model01` remains EFFECT_UNKNOWN / ROOT_UNVERIFIED; original root `gmi-paper-makeover-20261103-sol`, parent `gmi-product-upgrade-20261103-sol`, controller PID 38742, lease 868f3981b9bd. None of its fenced model/presentation/test files was edited and no result was consumed, retried or reassigned. The qualified data projection, noindex and all Draft/no-merge/no-Ready/no-enqueue/no-relabel release holds remain in force. Next: consume fresh exact-head CI after this bounded frontend hardening; repair only its evidenced defects, then continue model settlement solely through the original installed runtime owner.

**Self-QA of the submitted fence (subsequent correction).** The existing `lib.pages.write_page` performs `Path.write_text` and would follow a symlink at a *currently permitted* issuer filename. The first guard rejected nonregular stale filenames only; it missed this permitted-name case. An isolated red/green test observed the old allowed-name path bypass and the corrected upfront nonregular/symlink refusal without modifying the unrelated target. The regression test now covers both stale `gmi-issuer-zz.html` and active `gmi-issuer-mu.html`. This remains a frontend output-safety repair, not a model rights settlement. New exact-head hosted CI is owed.

**Public-context closure (second self-QA correction).** The first source guard restricted issuer links, but still used `{**model}`, which unnecessarily exposed internal `deck`, `edge_package`, `owners`, `identity`, raw issuer/link fields and unrelated `theme_links` to Jinja, even when not currently serialized. The hardened renderer now supplies an explicit top-level allowlist of taxonomy/coverage/current date fields, a build-clock-only provenance object, minimal cleared issuer/product/source display fields, and a theme-focus list derived only from cleared product links. No original private relationship edges, party names, internal correction/scope metadata or arbitrary future `theme_links` reach the template environment. A controlled source/AST test passed for the retained Micron fact, suppressed unauthorized company/source/context sentinels, and preserved the existing approved theme-focus knowledge clock. The public-view suite asserts the exact projection shape and sentinel exclusion. This is still not hosted CI or real-browser proof for the successor head. No new qualification/publishing owner was created; the original model fence and release holds remain.


### 11.13 Public-boundary regression alignment and exact-input proof — 2026-11-04

This continuation binds original draft PR #10676 to parent head `bc05ff3f82742c694d6e3ff75d82e2fbc14fd0dc`, the same `claude/gmi-product-upgrade-20261103` branch and operation `gmi-product-upgrade-20261103-sol`. Protected Mastermind/master `690e5316629815ae3e78f65ebdec2eb87f0cad16` is compatible with Sol skillpack 1.0.1/bootstrap 1. Direct execution is LOWER_TOTAL_OVERHEAD for the observed, bounded frontend test repair; no new model worker or Paper writer was dispatched.

**Evidenced failure.** Fresh local verification matched 130 source/data/template/test input files to exact parent-head Git blobs, with zero mismatches before the intended repair. The latest committed symbol-directory snapshot is 2026-11-03. The new public-view suite passed 19/19. The seven incumbent GMI suites then produced 138 passes and three failures, all in `tests/test_gmi_explorer_s1_s5.py`. Each failed while reading an issuer page that §11.12 correctly no longer creates for an unreviewed or incomplete raw fact. This was an integration-test contract mismatch, not evidence to weaken the fail-closed renderer.

**Repair and retained coverage.** The held-fact test now requires the issuer file, its links, proposal ID and product text to be absent from all generated public pages, together with the useful company-catalogue empty state. The excerpt test checks all public pages and injects a nonempty private sentinel into both cleared-product and held-product inputs. The existing EN/ZH missing-value typography test remains, exercised directly on an already projected presentation model; it does not override production admission. Three new production-render cases independently withhold missing product, platform and lifecycle. No assertion was skipped, xfailed or weakened, and no source-rights grant was created. Only the frontend test module changes; its repaired Git blob is `17001d563f87bb9cd4191fd63e92edb67b96a26c`.

**Green proof.** The repaired S1/S5 module passed **25/25 in 35.24 seconds**. The exact eight-suite command selected by the existing `gmi-explorer` hosted job then passed **163/163 in 79.08 seconds**, with process 46300 ending exit 0. The source-bound validation record is [PUBLIC_BOUNDARY_VALIDATION_20261104.json](PUBLIC_BOUNDARY_VALIDATION_20261104.json); its logs and input manifest remain on the original M2 evidence carrier `/Volumes/Mastermind/agent-workspaces/verify/gmi-product-continuation-hzln4tqh/`. This is local proof; successor hosted CI remains owed.

**Proof preservation.** Both the incumbent and hardened renderer were executed against the identical saved accepted model. All seven HTML pages plus paired CSS and JavaScript were byte-identical between the two renderers. The saved model's coverage order/build clock differs from the committed 3-November coverage display in both renderers, so no new coverage snapshot or generated-page update was published. The committed nine GMI browser inputs retain the exact hashes in the accepted 92/92 Chrome report, with zero recorded page exceptions. All template/site/mockup/data/model/shared-library trees remain unchanged by this repair. The accepted 91 PNGs and 92-case browser proof were not recaptured.

**Paper readback.** A real native Mastermind Paper explicit-file read confirmed `01M5H6EARN9YHQV17JC6ZG9BRY`, current entry `p-1-0`, all ten current product boards, historical-reference pages and unchanged token hash `ac191fd9`. The user-active unrelated Paper file was not edited. Accepted consolidation and canvas work remain DO_NOT_REDO.

**Hosted and runtime frontier.** Before this repair, exact-head fences run 41787361491 passed; CI run 41787361445 had completed planning and was executing its packs. No terminal full-CI pass was asserted. A new source head must be observed separately. Original model run `gmi-product-upgrade-20261103-model01`, root `gmi-paper-makeover-20261103-sol`, parent `gmi-product-upgrade-20261103-sol`, controller PID 38742 and lease `868f3981b9bd` remain EFFECT_UNKNOWN / ROOT_UNVERIFIED. The original Fabric status explicitly denies result consumption, retry and dispatch; its current catalog exposes no settlement action. Executive V3 state reports its reader request was not sent because the backend is unavailable; session_targets reports the installed Session Bridge owner unavailable. No denied result, lease rewrite, alternate controller, replacement worker or blocked message was attempted.

**Next action and holds.** Consume the successor head's ordinary hosted CI and repair only evidenced failures. Continue original-run settlement only through its eligible installed runtime owner. Public-data qualification and the normal protected release/live-path gates remain open independently. Keep Draft, noindex and every no-merge/no-Ready/no-un-draft/no-enqueue/no-relabel hold. The existing hourly observer remains attention only, not a worker or release authority. This is a verified candidate and a removed regression blocker, not production completion.

### 11.14 Bound display attribution for the current product specimen — 2026-11-04

This bounded frontend continuation uses parent `e2488ac7840ccfacd647a1c184895bf79c6cac1c`, the same draft PR #10676 and protected source pin as §11.13. The previous tests-only commit was read back exactly; its compare contained only the three intended test/evidence paths. No accepted Paper, visual, model-owner or generated-site work was reopened.

**Confirmed input-integrity defect.** Source analysis identified that the current receipt predicate bound issuer ID/ticker and the factual source tuple but not visible descriptive attribution. The original carrier reproduced the issue: changing only the current issuer's display name to a sentinel left admission true and put that altered company name on the topic, company-catalogue and issuer pages. The corresponding production-render regression failed before the fix (one failure, 6.32 seconds). This demonstrates an input-integrity gap, not a claim that the accepted live specimen was already wrong or that a general source-rights grant exists.

**Bounded repair.** The existing builder now binds six display fields to the same already accepted specimen: Micron Technology, Nasdaq, the EN/ZH HBM theme labels and the EN/ZH company-source labels. An altered field withholds the fact and retires the stale issuer page. Six independent regression cases check the issuer route, all remaining public HTML, the company empty state and topic connection payload. The existing escaping test still exercises hostile text in an already projected template fixture; production identity mutation no longer doubles as a grant. Two incumbent issuer expectations and the company-catalogue expectation now explicitly represent the one cleared specimen instead of asserting blanket publication for every raw issuer or ACCEPT/RATIFIED row. Existing multi-record rendering, unsafe URL and bilingual missing-value capabilities remain covered.

**Proof.** The exact existing eight-suite GMI CI command passed **169/169 in 82.67 seconds**, process 75347 exit 0. The isolated materialization matched all 130 bound inputs with only the three intended source/test blob overrides and no unexpected differences. The accepted input produced all nine HTML/CSS/JS files byte-identical before and after this repair. Templates, committed generated pages, the 91 PNGs and accepted 92/92 browser report remain unchanged; no new browser or production claim is made. [PUBLIC_ATTRIBUTION_VALIDATION_20261104.json](PUBLIC_ATTRIBUTION_VALIDATION_20261104.json) records the red/green reproducer, exact blobs, source inputs, command and original-carrier logs. A bounded native reasoning adviser supplied source analysis, returned and received terminal STOP; it was optional advice, not an independent approval gate or a substitute Fabric execution.

**Current frontier.** Parent-head fences 41792645034 passed; parent CI 41792644982 was pending when observed. Successor hosted CI must be read at the new source head. The original model run, root/parent, controller PID 38742, lease `868f3981b9bd`, EFFECT_UNKNOWN / ROOT_UNVERIFIED result restriction and original-owner-only settlement remain as recorded in §11.13. No model result, lease, worker or release effect was consumed, replaced or advanced. Keep Draft, noindex and all no-merge/no-Ready/no-un-draft/no-enqueue/no-relabel holds; public-data qualification and protected release/live-path proof remain separate obligations.

**Exact next action.** Read the ordinary hosted CI for the resulting head and repair only evidenced failures. Keep the existing observer attention-only and aligned with the current source frontier; do not create another watcher or infer background execution from a scheduled observer. Original-run settlement requires an eligible action from the original installed runtime owner. Current accepted design and browser work remain DO_NOT_REDO without a material invalidator.


### 11.15 Preserve unknown knowledge dates without fabricating publication fallback — 2026-11-04

This continuation binds parent head `71d7124f6634c4080ad4d926826d4a24dd60b68b`, the existing draft PR #10676, branch `claude/gmi-product-upgrade-20261103` and operation `gmi-product-upgrade-20261103-sol`. Protected Mastermind/master `3f420c7a8020254a45386cd1614bdec2b0c67c73` was verified with INDEX and the required laws at the same SHA; Sol skillpack 1.0.1/bootstrap 1 is compatible. Direct execution is LOWER_TOTAL_OVERHEAD for this bounded frontend correction. No replacement model worker, Paper writer or new watcher was created.

**Confirmed defect.** The frontend projection substituted source publication for missing, UNKNOWN or UNDISCLOSED knowledge time. A rendered held-link tooltip therefore asserted “first seen 26 Feb 2024” when no first-seen date was recorded. Further production-render regressions demonstrated a missing/nonstring KNOWN value could stop rendering, while an impossible calendar date could appear in the tooltip. The test-first run produced **7 failures and 1 pass in 11.73 seconds**, process 46306 exit 1; the positive control kept knowledge time distinct from publication.

**Repair.** The frontend builder now accepts only a valid recorded KNOWN ISO date/timestamp for this display. Missing, unknown, undisclosed and malformed values remain unknown. The owned tooltip macro renders “first seen not recorded” / “首次收录时间未记录” without passing missing values to the date formatter. Valid knowledge dates, source publication date and the Planned lifecycle remain independent and unchanged. Eight production-render cases cover both language attributes, seven failure states and the known-date control. The model/presentation subtree and model-owner tests were not modified.

**Verification.** The original evidence carrier first matched all **130 bound inputs** to their parent-head blobs. The candidate changed only the builder, tooltip macro and product-view tests among those inputs; no unexpected differences were found. The exact existing eight-suite GMI command passed **177/177 in 71.52 seconds**, process 51097 exit 0. Self-review covered the complete three-file source diff. Rendering the same saved accepted model produced **9/9 byte-identical HTML/CSS/JS outputs**. The committed generated pages, 91 accepted PNGs and 92/92 Chrome report remain unchanged, so the accepted browser matrix was preserved rather than recaptured. The new fallback states are covered by production-render regression tests; no additional browser or production acceptance is asserted. [PUBLIC_KNOWLEDGE_CLOCK_VALIDATION_20261104.json](PUBLIC_KNOWLEDGE_CLOCK_VALIDATION_20261104.json) records all input blobs, red/green results, commands, output hashes and original-carrier evidence.

**Paper and runtime readback.** Native explicit-file inspection confirmed the canonical product-system file `01M5H6EARN9YHQV17JC6ZG9BRY`, entry `p-1-0`, ten current boards and unchanged token hash `ac191fd9`; no canvas edits were needed. Original model run `gmi-product-upgrade-20261103-model01`, root `gmi-paper-makeover-20261103-sol`, parent `gmi-product-upgrade-20261103-sol`, PID 38742 and lease `868f3981b9bd` remain EFFECT_UNKNOWN / ROOT_UNVERIFIED. Native Fabric status denies result consumption, retry and dispatch. The current catalog exposes no eligible settlement action; Executive session targets report the installed Session Bridge owner unavailable. The original M2 filesystem/process carrier remains usable, so this is a narrow runtime-owner gap. No result, lease, controller or work ownership was reassigned. An optional native reasoning adviser failed before returning findings and received terminal STOP; it created no review dependency or source changes.

**Current frontier and exact successor action.** Parent-head fences run 41793928552 passed. Parent CI 41793928668 completed planning and was executing ordinary packs when last read; a complete parent or successor hosted pass is not asserted here. After this commit, read the successor head's ordinary hosted CI and repair only an evidenced failure. Original-run settlement must come from its eligible installed runtime owner at the same run/process/lease, followed by the incumbent public-data qualification and protected release/live-path gates. Keep Draft, noindex and every no-merge/no-Ready/no-un-draft/no-enqueue/no-relabel hold. Keep the existing observer attention-only and update its handled source frontier without creating a duplicate. Accepted Paper/design/browser work remains DO_NOT_REDO absent material change. This closes the bounded knowledge-clock defect and leaves a verified candidate at a real hosted-CI/runtime boundary.


### 11.16 Guard pre-existing fixed GMI output symlinks — 2026-11-04

This continuation binds the exact original Draft PR #10676, branch \`claude/gmi-product-upgrade-20261103\`, operation \`gmi-product-upgrade-20261103-sol\` and parent commit \`0a7e8e66f7ac63ed297548026936c096531d3167\`. Protected Mastermind/master \`124df8d533dd01400a7dc514ac98b92b2d63186e\`, skillpack 1.0.1/bootstrap 1, was loaded at one commit with its required owner laws. The accepted Paper file, ten boards, 48-token hash, 91 PNGs and 92-case browser proof remain DO_NOT_REDO.

**Observed independent defect, not a production incident.** The GMI builder's prior nonregular-output guard covered the generated issuer family but not six fixed HTML routes, paired \`gmi.css\`/\`gmi.js\`, or the requested \`site_dir\` itself. An isolated, disposable \`site/gmi.html\` symlink redirected \`lib.pages.write_page\` into an outside sentinel and overwrote it with 972,129 bytes. No production path or non-test file was used. Nine production-render regressions then failed at the original head: six HTML files, two paired assets and the output directory all failed to refuse pre-existing symlinks.

**Bounded source fix.** Before stale issuer pruning or any page/asset write, \`render_site\` now refuses a symlink output directory and refuses symlink or other nonregular targets for every fixed HTML/paired-asset name. The existing issuer page guard, \`lib.pages.write_page\`, default data/model/rights projection and normal builder remain unchanged. No alternate writer, source permission, file server, pipeline or renderer was introduced. This check is deterministic preflight, not a claim of race-free protection against a hostile concurrent filesystem actor.

**Red/green and preservation.** The nine new tests failed on the original code (\`9 failed, 33 deselected in 10.07s\`), then all nine passed after the fix. The exact incumbent eight-suite GMI test selection passed **186/186 in 109.89 seconds** (process 10446 exit 0). The isolated carrier matched all 130 bound source/data/template/test inputs with no unintended changes; the only owned source edits are \`scripts/build_gmi_explorer.py\` and \`tests/test_gmi_product_public_view.py\`. Their new Git blobs are \`96789b43ca2b9ca7b612400913b9697704094233\` and \`148754bf9c7a6d470ff40b09c46ab5a88cef595d\`. Rendering the same saved accepted model produced **9/9 byte-identical** HTML/CSS/JS outputs, so the prior 92-case browser proof and 91 original captures remain applicable to the unchanged generated inputs; those browser cases were not rerun. \`PUBLIC_OUTPUT_SYMLINK_VALIDATION_20261104.json\` binds exact inputs, tested behavior, local red/green logs and comparison.

**Cross-program interface.** A read-only current-source comparison found that Market-OS PR #10696 at \`941f3ed2\` registers six GMI routes but not the new \`/gmi-companies.html\` route from this PR; both branches change the registry test file. The accountable registry owner received the exact combined-source acceptance contract in [#10696 comment 6626264216](https://github.com/mastermindx-market-intelligence/macro/pull/10696#issuecomment-6626264216). This is a future composition requirement, not a new Shared Shell audience grant or authority to edit the registry owner branch.

**Holds and exact next action.** The previous head's normal CI run [41797747897](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41797747897) had passed planning and contract delta and was executing packs when last observed; its fences [41797747751](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41797747751) passed. These are not successor-head checks. Read naturally triggered exact-head hosted CI/fences after this commit and repair only evidenced failures. The original model worker \`gmi-product-upgrade-20261103-model01\` remains EFFECT_UNKNOWN / ROOT_UNVERIFIED with PID 38742 and lease \`868f3981b9bd\`; result consumption/retry/dispatch remain denied. Settlement requires the same original runtime owner. Public-fact/relationship qualification, combined product-registry admission, protected release, authenticated live-path proof and user acceptance remain separate unmet obligations. Keep Draft, noindex and all no-merge/no-Ready/no-un-draft/no-enqueue/no-relabel holds. No model result, lease, watcher successor or production effect was advanced.

### 11.17 Registry scanner attribution repair — 2026-11-04

**Exact existing ownership:** Draft Macro PR #10676, branch `claude/gmi-product-upgrade-20261103`, parent source `d6500a8398d11d717ca4af7015d557c61fb084b1`; protected Mastermind source pin `124df8d533dd01400a7dc514ac98b92b2d63186e`, skillpack 1.0.1/bootstrap 1. The ten editable Paper boards and prior 92-case browser proof are accepted and preserved.

**Observed CI regression:** Current-head CI [41801221560](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41801221560) concluded FAILURE solely because pack 8, job `product-experience-registry`, failed its seven-surface AST attribution test (`tests/test_build_product_page_registry.py::test_gmi_real_gmi_builder_binds_all_seven_surfaces`; 1 failed, 80 passed). Eleven other CI packs, planner and contract-delta passed; semantic gate had one `pr_regression` and zero infrastructure findings. Fences [41801221276](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41801221276) passed. This is a real source defect, not an excuse to rerun CI unchanged.

**Root cause and minimal fix:** The safety hardening in §11.16 iterated `(*TEMPLATES, *PAIRED_ASSETS)`. The incumbent conservative `scripts/build_product_page_registry.py::_reassigned_or_mutated` treats that as a possible alias/mutation and refuses the entire table, falsely omitting six literal fixed-route write sites while retaining the issuer family. The sole code change extracts fixed pages through `TEMPLATES.items()` (the scanner's deliberately permitted immutable read), then runs the unchanged pre-write symlink guard across the resulting six fixed pages and paired CSS/JS assets. The shared registry scanner, registry test, producer data, permissions and other owners remain unmodified.

**Original-source red/green proof:** On an isolated Studio verification mirror pinned to parent source, the real scanner (blob `1e359523bffcc9c74f33e4b0557f853c5c8546e6`) initially reported one issuer family and six unresolved fixed routes. After the patch it reports exactly seven routes and zero GMI unresolved sites. The *exact* failed source test (blob `cd3f8a7f9677d87c30a041b758da2e81697371c7`) passed `1 passed, 80 deselected` after staging its unchanged ontology sibling (blob `597dba23fb8f4bd377d0cd41193e6fc04a7e5650`) into the isolated mirror. The 186-case GMI suite passed in 77.50s, all 130 previously bound GMI source/data inputs were accounted for with no unintended changes, and the nine accepted generated HTML/CSS/JS files remained byte-identical. The original 92-case Chrome proof was not rerun. New builder Git blob `900253d42a7b1d43ad41aa493e8032444c4570de`; [structured validation](CI_PRODUCT_REGISTRY_REPAIR_20261104.json) binds exact tests, copies, limitations and logs.

**Continuing holds:** The new semantic head requires its own natural hosted CI/fences. Separate Market-OS PR #10696 still must compose the new `/gmi-companies.html` registry entry with existing access/rights restrictions; cross-owner [comment 6626264216](https://github.com/mastermindx-market-intelligence/macro/pull/10696#issuecomment-6626264216) remains the designated boundary. Original model run `gmi-product-upgrade-20261103-model01` remains `EFFECT_UNKNOWN / ROOT_UNVERIFIED` and blocks result consumption/retry/replacement. No Paper edit, public relationship qualification, merge, Ready, un-draft, enqueue, relabel, indexing, deployment, authenticated backend proof or user acceptance occurred. Keep the original holds and observer only. **Next action:** consume successor-head natural CI evidence, repair only actual failures, then obtain combined-source product-registry proof through its incumbent owner.


### 11.18 Companies catalogue integration — 2026-11-04 US / 2026-11-05 UTC

Current Chairman continuation authorizes substantive implementation and blocker resolution, not a repeated status handoff. The original GMI branch/PR #10676 remains the publication target; Draft/no-merge/no-Ready/no-enqueue/no-relabel/no-deploy holds remain. Protected pin `700eef54bca4a2dc4e30d94a6b30dcfa733ad57c` is compatible with skillpack 1.0.1/bootstrap 1. Direct execution reason: LOWER_TOTAL_OVERHEAD for the bounded known integration defect on the original source carrier.

**Prior gate closed.** Exact GMI head `be851458055efbffa1f2db61da12b7744502479a` completed hosted CI 41898455221 and fences 41898455029 with SUCCESS. No old green is transferred to a new head. The existing workspace owner recovered an exact-base isolated M2 workspace; its initial incomplete checkout was reconciled on the same operation until the owner reported clean. No duplicate worker, new PR or third GMI design was created.

**Implemented rather than handed off.** We composed immutable P12.T9 head `e5dd3a7393bfc82c86217c134ed7022505f6ee2b` into the GMI candidate without changing that other branch. Two test-first failures proved the missing Companies source override and generated row. One `macro:gmi_companies` override now classifies the searchable evidence catalogue as `discovery_board` and retains `shared_shell:admission_withheld`; anonymous standalone serving remains distinct. Source freeze `ce005b5d9d7cabcbbed9a053ff3fbe2cf61ca8f7` has exact GMI/P12 parents. The incumbent generator then produced 356 rows from that source, retaining Terminal `e0d4cabfccd3f1fd83b4362288124ba8078de731` and clean Mastermind `7ab47f0b62d9a22ff16a13f6b99b96b681874a93`. Exactly one row was added, none removed, and every pre-existing non-provenance row field is unchanged. Normal generation reproduced byte-identically; no derived row was hand-edited.

**Actual consumer proof.** The production exporter consumed the generated registry, seven real immutable GMI HTML documents and actual serving deny policy. Only map/index/coverage remain admitted; Companies/issuer/relationships return `consumer_admission_withheld`; States remains internal; PLNT remains absent. Expanded source-overlay and committed-artifact regression tests pin this behavior. Six affected suites verified 416 distinct cases: the first run passed 414 and identified two missing sparse-fixture errors; restoring the exact unchanged PLNT/SEO input blobs made all six withdrawal tests pass. Existing registry validation passes. Structured evidence: [COMPANIES_REGISTRY_INTEGRATION_20261105.json](COMPANIES_REGISTRY_INTEGRATION_20261105.json). This closes the previously reported Companies integration omission without granting a new audience.

**Preserved work and remaining boundary.** GMI templates, generated user-facing pages/assets, source model/presentation and accepted 92-case browser/91-PNG/10-board evidence remain unchanged. The original model run `gmi-product-upgrade-20261103-model01` remains EFFECT_UNKNOWN / ROOT_UNVERIFIED. The current verified native runtime generation exposes only closed historical or original-native-parent observation routes; none admits this Web-origin unknown-effect run. No identity/environment spoofing, raw retained result read, replay, runtime hotpatch or lease rewrite was used. Successor hosted CI and ordinary protected release/live-path proof remain owed.


### 11.19 Preserve open source receipts through locale redraws — 2026-11-09

The Chairman's continuing Paper implementation mandate applies to this narrow frontend follow-up on the **same existing Draft PR10676 / claude/gmi-product-upgrade-20261103**, parent **80d6ff71b9913524c4a381b543ec7a53383f50dc**. Fresh PR/source readback found that exact original carrier with native auto-merge absent and no release label. This is a source-linked continuation of the disjoint frontend permission in §11.8; the model child, its files and denied/unknown effects are not consumed or reassigned.

**Concrete defect.** The existing `data-lang` observer calls `sync`, and `renderAnswer` replaces every evidence card. Its native `<details>` therefore loses open state during a locale change, and a focused summary or action can be removed. This is verified in the candidate frontend, not claimed as a production regression. The maintained Paper contract is file **01M5H6EARN9YHQV17JC6ZG9BRY**, p7, Build **7M9-0**, locale/focus nodes **7MZ-0 / 7N3-0**.

**Implementation.** `templates/gmi.js` and identical `site/gmi.js` now carry one synchronous locale-only DOM capture through the existing render owner. A WeakMap associates the currently rendered card with its native receipt and actions. Only explicit `sync(true)` can restore state. The key is the exact tuple of theme, receipt, source key and source text hash; all fields must be supplied, and every member of a duplicate receipt-ID group is ineligible. Restoration never uses card order, ticker or a translated label. Open/closed state is restored only to exact eligible matches. Focus restores only when the old focused element was actually removed and no surviving control acquired it. The same action role and full post-navigation-rewrite URL must match; changed/missing actions use the corresponding receipt summary, and changed/missing/ambiguous records use the existing focusable topic heading. The capture is discarded within the call. Theme selection, history, filtering, URL state, public admission, shared theme ownership and persistence remain with their existing owners.

**Observed qualification.** The original exact JavaScript blob **6f5ee7dbd70c71b6dec99094b860cfaf2d6e78a3** failed the open-receipt/reordering assertion at both 1440px and 390px. The candidate pair **0a5a6b51f7c836e34523a476751fc3eca054302d** passed the two named locale cases, covering **32 fresh anonymous Chrome contexts**, with zero page errors and process exit 0. Chrome was **157.0.8103.39** on the existing authorized M2. JavaScript syntax and the complete updated Python verifier syntax also passed. Exact added regression code is in the incumbent `verify_product_browser.py` as `locale_receipts`; it supplies `locale-receipt-state-1440` and `locale-receipt-state-390` through the existing `--case` selector. [Structured receipt](LOCALE_RECEIPT_VALIDATION_20261109.json) binds source/test/markup/fixture hashes and observed scope.

The executed bounded harness used the exact added test function and actual candidate JavaScript on extracted committed GMI component DOM, test-only record clones and controlled presentation mutations, with all external networking blocked. It proves the locale/card/focus behavior, including negative identity and action cases. It does **not** claim the full shared-shell/CSS visual matrix, signed-in backend, current market facts, publication or live deployment. Prior 92-case / 91-image / ten-board evidence remains preserved historical proof, not successor-head acceptance. No data model, projection, builder, admission policy, registry, shared theme asset or accepted Paper product board changed.

**Release boundary.** Preserve original model run `gmi-product-upgrade-20261103-model01` as **EFFECT_UNKNOWN / ROOT_UNVERIFIED**, including every no-consume/no-retry/no-replacement constraint. PR10676 remains Draft with no auto-merge and every no-merge/no-Ready/no-un-draft/no-enqueue/no-relabel/no-deploy hold. New source requires its own naturally triggered hosted checks and eventual qualified full product/live proof. The locale fix supplies no clearance of those holds.


### 11.20 Keep copy feedback with its initiating view; qualify disclosure targets — 2026-11-09

The continuing Paper implementation mandate covers this follow-up on **the original Draft PR10676**, parent **cc47f34daf1850392521018c40380258e61b33a6**. It uses the disjoint frontend lane established by §11.8. No model result, model/presentation file, source record, policy, registry or shared theme owner is changed.

**Reproduced defect.** The old handler awaits a clipboard write and then updates whichever answer is currently displayed. A late success for theme A therefore says “Link copied” on theme B. Its rejection reads the later `location.href`, presents the wrong attempt's URL and takes focus. A previous success timer can clear a newer operation's label. The existing lens handler changes the URL with `replaceState`, so listening only to normal navigation misses that transition. The exact pre-fix JavaScript failed the first stale-success assertion on desktop and mobile.

**Builder contract.** The existing handler now captures the complete URL and selected theme in one in-memory attempt object. The same object must still own the action, and both values must still match, before any success, failure or final button update is applied. There is no persisted state, new service, queue or retry owner.

| Event | UI behavior |
| --- | --- |
| Copy begins | Capture the final normalized research URL once; show “Copying…” / “正在复制…” and disable this action. |
| Current success | Show and announce success in the current language; its own 2500 ms timer may reset it. |
| Current denial/unavailability | Show the captured URL in the existing read-only manual fallback. Never substitute a later URL. |
| Selection, filter URL change, history, lens action or page exit | Retire the attempt and its timer; late completion cannot publish feedback, reveal fallback or enable another action. Returning to the same URL does not revive it. |
| Locale-only redraw | Retain a still-current attempt and manual URL; translate its owned feedback through the same renderer. Preserve §11.19 receipt behavior. |
| Later user focus, pointer intent or window blur | Relinquish automatic fallback focus. A body's active-element status by itself does not prove ownership. |
| Current manual fallback is closed | Retire it and return focus to the existing Copy control. |

The lens path uses the existing click lifecycle and attribute observer, including a batch containing both language and lens changes. The timer callback also checks attempt identity in case an already-queued callback outlives cancellation. Cleanup clears the shared live region only while it still contains that action's owned text. A current rejection may select the URL only while the initiating action still owns focus; otherwise the fallback is available without moving the user's focus. These rules apply to **UI feedback**: a previously issued operating-system clipboard write cannot be cancelled or reversed, and this handler does not issue a corrective write.

**Target sizing.** Both paired GMI stylesheets change the existing source-receipt and theme-context summary rule from a 40 px to a **44 px minimum**. No shared token or component is forked. Browser measurements of source markup before enhancement and the enhanced DOM found 40→44 px at 1440 px in EN/ZH. At 390 and 320 px the existing wrapped content already measured **53.59375 px**, which remains unchanged while the minimum becomes 44 px. This is a measured minimum correction, not a claim that mobile targets previously measured 40 px.

**Qualification and exact source.** Candidate JavaScript blob **387383b0e237162421dfebf5eb9d7ef85302cb1e** and stylesheet blob **23ce5f275ffc07a57278450b560d9d0c20f86632** are mirrored byte-for-byte between templates and site. Existing `verify_product_browser.py` now includes `clipboard_context_paths`, exposed as `clipboard-context-races-1440` and `clipboard-context-races-390` through its existing selector. The final run passed **42 copy contexts plus the 32 existing locale contexts**, zero page errors, exit 0, Chrome **157.0.8103.39**, 40.72 s. The verifier's complete syntax and JavaScript syntax pass. The source test adds deferred clipboard outcomes, controlled stale timers, history/lens/selection/filter transitions, overlapping attempts, pointer/focus ownership, and locale integration; the existing real-clipboard positive control remains intact.

[Structured evidence](COPY_CONTEXT_VALIDATION_20261109.json) binds all source, test and fixture hashes, the reproduced baseline failure, the final native run and 24 before/after geometry observations. Execution used exact candidate JS and test functions on extracted committed explorer DOM plus actual source lens controls, complete GMI CSS and extracted shared root/language rules, with all external network blocked. The race tests do not touch the system clipboard. These are bounded anonymous component proofs, not full shared-shell/font/account/production/admission acceptance. Prior 92-case/91-image/ten-board evidence remains historical.

**Continuing boundary.** Preserve the original model01 **EFFECT_UNKNOWN / ROOT_UNVERIFIED** and no-consume/no-retry/no-replacement fences. PR10676 stays Draft, with no auto-merge, Ready, un-draft, enqueue, relabel, merge or deploy. Natural successor checks and qualified full-product/live proof remain owed. Paper Build module 06's remaining no-JavaScript/static-copy alignment is separate work; these changes do not claim it completed.


### 11.21 Align the generated Theme details label with Paper — 2026-11-09

The existing `topic_answer` macro now names the classification disclosure **Theme details / 主题详情**, matching Paper S06. Its separate **Source receipt / 来源凭证** still contains the exact record, source key and source text hash. No additional panel, route, data field or state owner is needed. The runtime already retains this generated summary while updating its contents, so the label serves both enhanced and no-JavaScript readers.

**Qualified production rendering.** This continuation uses original Draft PR10676 parent **83f05e360844da4b28d9bbb2d82079908809ba5f**. The accepted saved input is source-linked by PUBLIC_ATTRIBUTION_VALIDATION_20261104.json and PUBLIC_KNOWLEDGE_CLOCK_VALIDATION_20261104.json; the actual file still matches SHA256 **e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f**. It belongs to the principal verification carrier, not the fenced model01 output. A new isolated verification directory binds 48 current immutable renderer/template/library inputs and this unchanged model. It imports the existing `render_site` path, retaining `_public_render_model`, `make_env` and `lib.pages.write_page`; it does not build a new model or run coverage proof. The original mirror, primary checkout and live site remain untouched.

Before editing the macro, that path reproduced the current committed `gmi.html` **byte-for-byte**, SHA256 **12f2f5aee1ded9d656878db968e3c218e7797c659c89043f12346a14f013f190**. After the one bilingual label change, the same renderer changed **only `gmi.html`** among its nine HTML/CSS/JS outputs. The full target delta is one generated summary line; all other bytes, including public data, dates, search JSON, source receipt and shared shell, remain exact. The generated target blob is **f821055256f57d3fa777e77c14c4a555ef4375cf**, paired with macro blob **3e82a587bb0ad17f536d0513d85a1c0a66304999**. The actual generated diff was transported against the canonical prior page and its complete output hashes checked before publication.

The saved model is not permission to replace the whole committed bundle. Its historical coverage render differs from the committed 3-November snapshot; that output is excluded. Only the generated target page and its source macro are published with this section and evidence.

**Native behavior.** Twelve fresh anonymous Chrome cases passed at 1440, 390 and 320 px, EN/ZH, JavaScript enabled and **actually disabled**, with reduced motion and zero page errors. Each checks the separate visible labels, one admitted card, unchanged identifier bytes, native Enter/Space expansion, focus retention and target height. The desktop targets remain 44 px; the wrapped mobile targets remain 53.59375 px. The browser uses extracted actual generated explorer DOM plus the exact current JS, complete shared theme CSS and GMI CSS with networking blocked. Static language attributes are explicit presentation fixtures; this does not claim a working no-JavaScript language switch or full shared-shell/account/live acceptance.

[DISCLOSURE_LABEL_VALIDATION_20261109.json](DISCLOSURE_LABEL_VALIDATION_20261109.json) binds the accepted input, all 48 source blobs, baseline/candidate render receipts and twelve native results. Existing locale/copy source and their accepted bounded proofs remain unchanged. Paper Build module 06's generated/no-JavaScript label mismatch is now closed. Original model01 unknown-effect fences and every Draft, admission and release hold remain.


### 11.22 Make tree selection and index search behave coherently — 2026-11-09

This continuation uses original Draft PR10676 parent **696f370a3b47c2abc893a7c111b5669cce66d654**. Native checks reproduced two defects in the committed generated pages at desktop and phone sizes: arrow-key focus reached a theme leaf but Enter did not select it; index search hid categories while their jump shortcuts remained available. An HBM query also displayed two rows beneath a shortcut count of **64**. The repair stays in the existing frontend owners.

**Keyboard and navigation.** Eligible plain Enter/Space on a visible tree-leaf wrapper delegates to its existing `a[data-topic-select][href]`. The current topic-selection handler still owns URL updates, the answer, copy retirement and heading focus. Expandable rows retain their native tree behavior; modifiers and IME remain untouched; repeats are cancelled without another activation; a nested anchor's native Enter is not doubled. Empty categories acquire no destination.

Category shortcuts now follow the existing filtered groups. An unavailable, detached or no-longer-owned target cannot fall through to a native fragment navigation and erase query/lens/return context. The existing observer rejects stale entries before changing any current-link state. Its redundant cached link identity was removed; the owned ARIA state determines whether a restored category needs to be revealed again. No additional observer, route, catalogue or URL-state owner was added.

Search releases focus immediately before its own hide operation removes an active row, category or shortcut. This includes a hidden row whose category still contains another match. Clearing/restoring a query also releases focus before restoring a previously collapsed group. A surviving control, a category summary that remains visible, and unrelated focus are preserved. The existing index input is the recovery target.

**Counts that describe the visible results.** The same `indexRender()` pass produces the compact **2 results / 2 个结果** status and matching category/subgroup counts. HBM's two rows therefore produce category counts of two and subgroup counts of one. The single live status uses the existing no-match wording at zero; it does not repeat the query or add an explanation. Generated `data-gmi-total` values restore the original totals on Clear, while the footer explicitly says **Full index / 完整索引**. Static core/extended breakdowns are hidden during search: tier and held/admitted review status are different dimensions and are not inferred from each other. Bilingual spans remain under the existing language owner.

**Responsive correction.** The full generated main content exposed a 320 px English document width of 351 px, caused by primary-navigation labels that could not wrap. The existing mobile tab rule now allows wrapping while retaining 44 px targets. Category shortcuts increase from 40 to **44 px**; their mobile sticky-header and destination offsets increase together from 57 to **61 px**. Native measurements place the sticky rail bottom at 61 px and group-header tops at 61.69–62.44 px. No overflow clipping, smaller type, hidden destination or second navigation was used.

**Production rendering and source.** The existing builder (`900253d42a7b1d43ad41aa493e8032444c4570de`) uses the unchanged, previously qualified accepted model, SHA256 **e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f**, in a new isolated verification root with 48 bound inputs. The baseline reproduces both the committed explorer and index byte-for-byte. The candidate changes only **gmi-index.html, gmi.js and gmi.css** among nine outputs. The other six HTML outputs are byte-identical between renders; the historical coverage output remains excluded from publication. The index's exact generated bytes are transported and hash-verified, not edited by hand.

Current JavaScript is blob **6231f3aeacffa0ea1645772633ee2362ab375e0d**; CSS is **8bdb7f167e2524ce37da863251181362be495e57**; generated index is **7426afdcddd4b8bca944725b23d8234ab6815c2f**. The source/mirror assets are exact pairs. The entire answer-first controller, including the accepted copy and locale owners, remains byte-identical to the parent.

**Focused proof.** [KEYBOARD_INDEX_VALIDATION_20261109.json](KEYBOARD_INDEX_VALIDATION_20261109.json) records the four original keyboard/shortcut falsifiers, two count mismatches, the overflow diagnosis, input/render hashes and the current native results. The accepted current matrix comprises **12 named cases in 18 fresh anonymous contexts**, at 1440, 390 and 320 px in EN/ZH, with no page errors. Six taxonomy cases (12 contexts) passed on the final product assets in PID73914. Six index cases (six contexts) passed in PID81809 after correcting one test query: “advanced packaging” actually matched three canonical rows, so the singular assertion now uses the unique full HBM label. Product code did not change between those runs, and the successful taxonomy test functions were verified byte-identical and reused. This is not a claim that the initial index assertions passed.

The canonical `verify_product_browser.py` exposes the new `taxonomy-keyboard-<width>-<language>` and `index-shortcuts-<width>-<language>` cases through its existing selector. The bounded component harness executes those actual definitions, with explicit queued-observer, modifier/repeat and empty-row fault injections; it does not maintain a second selection/filter implementation. Two native mobile captures were inspected for count consistency, wrapping and clipping. JavaScript and complete Python-verifier syntax pass.

These are actual generated-component proofs with complete GMI/shared theme CSS and blocked external networking, not full shared-shell/font/live-account/publication acceptance. No model was regenerated or consumed from model01. Original **EFFECT_UNKNOWN / ROOT_UNVERIFIED**, Draft, admission and release holds remain unchanged.


### 11.23 Give the taxonomy one dependable keyboard entry — 2026-11-09

This continuation uses original Draft PR10676 parent **386937ff4b3b689be5bd4a42a1b6e17a7f3dc6eb**. The committed generated tree had seven visible tree rows with `tabindex=0` plus seven visible native topic links in the sequential Tab order. Tab from an arrow-focused leaf revisited that leaf's nested link. A zero-match query also left three empty category rows visible, and the tree had no accessible name. Native desktop EN and mobile ZH baseline observations reproduce each condition.

**One existing owner.** The current tree controller now normalizes every treeitem, including hidden and empty category rows. Exactly one visible row is the sequential row entry; no row remains a Tab entry when search has no matches. Arrow navigation, Home/End and branch expansion stay in that controller. Nested theme anchors leave the sequential Tab order only after JavaScript enhancement, retaining their original destinations and pointer behavior. Information buttons and the existing **See all** link remain separately reachable. Without JavaScript, all 371 original native theme links retain their generated attributes.

The existing visible bilingual heading labels the tree with `aria-labelledby`. This follows the focus/selection distinction and composite keyboard guidance in the [WAI-ARIA tree pattern](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/) and [keyboard interface practices](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/). It does not claim complete tree-pattern conformance: flat hierarchy semantics, retained information-button stops, typeahead and assistive-technology speech remain separate qualifications.

| Event | Focus and row entry |
| --- | --- |
| Tab into the tree | Enter its one current visible row; arrow keys move within the rows. |
| Pointer or programmatic focus enters a visible row or its link | Align the row entry without moving the nested focus. |
| Search will hide the active row, nested link or information control | Move focus to the existing search input immediately before that owned hide. |
| Collapse will hide an active descendant | Return to its nearest visible ancestor before hiding it. |
| Search leaves the current focused row visible | Preserve that focus and row entry. |
| Unrelated control retains focus | Do not move it. |
| Clear after an empty result | Restore the existing expansion snapshot and choose the first visible row as the next entry; no new remembered-focus store is introduced. |

**Exact source and proof.** Mirrored JavaScript blob **ec0e5b7c96d1dc876c6f13d0df14daf5e0749d2b** changes only the tree owner and its existing search call. The index controller and complete answer-first controller are byte-identical to the parent. Generated HTML, CSS, source records, accepted model, copy and locale owners are unchanged. Complete JavaScript and Python-verifier syntax pass.

The canonical verifier adds `tree-roving-<width>-<language>` cases and retains the existing `taxonomy-keyboard` activation cases. The final native run passed **12 named cases in 24 fresh anonymous contexts**, at 1440, 390 and 320 px in EN/ZH, Chrome **157.0.8103.39**, zero page errors, exit 0 in 36.95 seconds. Coverage includes actual Tab/Shift+Tab, arrows, collapse/search recovery before hiding, surviving and unrelated focus, zero results including empty categories, bilingual accessible names, unchanged 371-link destinations, retained information controls, and actual JavaScript-disabled native-link markup. A real platform-modified click creates a separate tab and loads the chosen theme while leaving the original page unchanged. Two phone captures were inspected for visible focus, wrapping and clipping.

**Fixture correction is explicit.** The initial component run passed three activation cases but stopped during a third roving case after two timeouts waiting for a page `popup` event. Native Cmd/middle clicks produced a browser-context page while the fictional-origin interceptor did not observe its first navigation. The corrected test listens to the context's page event; the bounded harness serves the same generated component on a dedicated loopback server, blocks external requests, and verifies the loaded destination. Product JavaScript did not change to accommodate this fixture repair. The stopped run is not counted as a passing matrix.

[TREE_ROVING_VALIDATION_20261109.json](TREE_ROVING_VALIDATION_20261109.json) binds baseline observations, exact source/test/harness inputs, the interrupted attempt, native-link diagnosis, final results and capture hashes. The harness executes named definitions from the one canonical verifier rather than duplicating behavioral test logic. These are generated-component proofs with complete GMI/shared theme CSS; full shared shell, fonts, account, live serving, screen-reader speech and release acceptance remain separate. The existing no-match paragraph's announcement lifecycle is not claimed by this phase.

Original model01 **EFFECT_UNKNOWN / ROOT_UNVERIFIED**, Draft, admission and release holds remain. No model generation, fenced result consumption, new route, registry, persisted state or lifecycle owner was introduced.


### 11.24 Recover from filters without leaving the answer — 2026-11-09

This continuation uses original Draft PR10676 parent **340cff37388b2567366d61985f610c7dfe654350**. The existing answer survives Browse filters, including zero results, but the old notice told a phone reader to clear filters while both reset controls were inside the closed Browse region. The exact committed generated page failed the new directly available action assertion at 1440 px EN and 390 px ZH. No new research state is needed to close that gap.

**Visible recovery.** A short **This topic is outside your filters. / 当前主题不在筛选范围内。** notice now contains **Clear filters / 清除筛选** beside the retained answer. The existing panel/button tokens provide a quiet single surface, a wrapping layout and a 44 px action. At 390 px EN the sentence and action share a row; at 320 px ZH the action wraps below the sentence without overflow or smaller targets. The message remains separate from the button's accessible name.

The existing notice owner derives text, region visibility and recovery eligibility together. It exposes a nonempty region before changing its status text and avoids rewriting unchanged text. This preserves the previous visibility-before-text order; it is not screen-reader speech acceptance. If a visibility change is about to hide the focused answer-side action, focus returns to the existing topic heading first.

| Situation | Answer-side behavior |
| --- | --- |
| Valid selected topic excluded by Browse filters | Show the short notice and Clear filters action. |
| Selected topic matches | Hide the notice and action. |
| Invalid saved topic | Keep the unavailable-topic/fallback explanation; no unrelated filter-recovery action. |
| Presentation data cannot load | Keep the existing available answer and index fallback; the new action stays hidden. |
| JavaScript disabled | The generated recovery region starts hidden; no inert reset action is exposed. |
| Mobile Browse is open | Native modal behavior keeps the background answer unavailable; its own reset continues to operate within Browse. |

**Use the current reset path.** The new button joins `[data-topic-reset]`, clearing the existing query, category, scope and evidence filters while retaining `state.theme`. The current `writeURL('replace')` preserves lens, qualified return context and other retained keys without adding a history entry. It also retires a pending or visible manual-copy attempt. The new caller finishes on the visible `#gmi-topic-title`; existing sidebar/drawer callers keep their original `search.focus()` behavior.

Reset does not call `select()`, `sync()` or `renderAnswer()`. Existing evidence nodes, their exact record/source identifiers and an open source receipt remain intact. Returning from a category filter may restore the theme's primary category label under the current filter renderer; this is not a theme or evidence change. A late clipboard success or rejection cannot publish feedback, expose the old fallback or steal focus after this URL change. No second copy, filter, modal, URL, storage or announcement lifecycle was added.

**Exact production rendering.** The unchanged accepted model, SHA256 **e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f**, was read through a new isolated root with 48 source-bound inputs and existing builder **900253d42a7b1d43ad41aa493e8032444c4570de**. The baseline reproduced both committed explorer and index byte-for-byte. The candidate changes only **gmi.html, gmi.js and gmi.css** among nine outputs. Its entire HTML delta is one generated notice line. The other six HTML outputs remain identical between renders; the historical coverage output is excluded from publication. Actual generated explorer bytes were transported and verified by complete SHA256 and Git-blob identity.

| Current artifact | Git blob |
| --- | --- |
| Paired GMI JavaScript | **812c1374f9d65a2675f5d73696de212c62fe0717** |
| Paired GMI stylesheet | **dbd070549d2ea64d692774508a34e9a7a3ac8928** |
| `templates/gmi_map.html.j2` | **b4f2a69ce7588d1b51296329d54d38cbcbeab4a5** |
| Generated `site/gmi.html` | **64e049b6a17e09e0ef8dd71c3cabe30b826ab484** |
| Canonical browser verifier | **f484804e107a11fc16e94fd3065073e5cff529bc** |

**Focused native proof.** The final run passes **eight named cases / 18 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, exit 0 in 26.34 seconds. The recovery journey runs at 1440/390/320 px in EN/ZH with both late clipboard outcomes, then checks existing drawer/sidebar reset focus and retirement of a visible manual fallback. It verifies retained URL/history, selected topic, evidence-node identity, open receipts, language changes, 44 px targets and no overflow. EN/ZH negative controls cover invalid topics, explicitly damaged presentation JSON and actually disabled JavaScript.

The earlier candidate also passed all eight cases in 18 contexts. A source-only review then restored the original visibility-before-text order for the live notice; the final exact JS was rendered and the affected matrix run again. Both runs and the two reproduced original failures are retained. No system clipboard write is issued by these fault-injection cases.

[ANSWER_FILTER_RECOVERY_VALIDATION_20261109.json](ANSWER_FILTER_RECOVERY_VALIDATION_20261109.json) binds source/render hashes, actual generated diff, canonical test definitions, bounded harness, native receipts and two inspected phone captures. The tree/index code, receipt renderer, selection owner, copy/URL owner and copy event handlers are byte-identical to the parent. Their accepted historical suites are not claimed as rerun. Complete JavaScript and canonical Python syntax pass.

The browser fixture uses actual generated main content and complete GMI/shared theme CSS in light mode with reduced motion, a dedicated loopback origin and blocked external requests. Full shared shell, fonts, live account, public admission, operating-system clipboard and assistive-technology speech remain separate qualifications. Original model01 **EFFECT_UNKNOWN / ROOT_UNVERIFIED**, Draft and release holds remain.

## 11.25. Persistent tree no-match feedback — 9 November 2026

### Observed defect and existing owner

At parent `11aed18841b996babe1b81c0b4eb0ebd7f27a797`, the tree's no-match paragraph was visually correct but had no persistent status container. The browser could reach zero visible tree rows and move from search to See all without an equivalent status role/content in that path. Desktop English and phone Chinese baseline cases reproduce the missing container. The existing `search_box()` macro, `noMatch()` helper and tree input/render remain the owners.

The non-index macro now wraps that same hidden bilingual paragraph in one always-mounted `data-gmi-tree-status` container with `role="status"`, `aria-live="polite"` and `aria-atomic="true"`. Its paragraph stays hidden until the existing tree render finds no matches. `noMatch()` assigns `hidden` only when the requested value changes. This avoids redundant visibility mutations during successive unmatched queries; it adds no query state, event owner, observer, timer or copied translation.

The container is present before feedback occurs, following the procedure in [W3C ARIA22](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA22). The existing language owner selects the visible EN/ZH span; no clear/repopulate cycle is introduced to force announcements. An empty result is feedback, so focus remains in search. Matching and cleared queries remove the paragraph's content from the rendered/accessibility status while preserving the container. Actually disabled JavaScript keeps the paragraph hidden and leaves the original native links intact.

### Preserve the panel's spacing

The parent `.gmi-panel` is a column flex layout with a 12 px gap. The first persistent wrapper introduced a second gap while its child was hidden: the source-bound native comparison measured 12 → 24 px at both 1440 and 320 px for initial, matching and cleared queries. Both versions already measured 89 px across the visible no-match message in the English fixture.

The final paired CSS has one scoped rule: `[data-gmi-tree-status]:has(> [data-gmi-nomatch][hidden])` offsets only that extra empty flex gap using the same `--sp-3` token. It does not hide the live region, change the original paragraph's padding/margins or affect the index. The source comment explains why the offset exists. The verifier compares actual geometry against the original parent gap and the existing visible message height/margins in every language/width case, including static loading.

### Source, render and affected proof

Current exact blobs: JavaScript **ae2aee39d3adbaff4687bd0efcca0a8b5e70ea9b**; CSS **bbf4395ff8e119d7d6161703693c6f4b03142029**; shared macro **ea0a7e36538c1df65e5b1280c3d86e050fb8f30f**; generated explorer **7427ca297e76cfd2fb07d3cf39713803e7f7f7e8**; canonical verifier **31a3d3895e5c3847e2da456d5c1a848e9bb63144**. Template/site assets remain identical. Every other JavaScript function is byte-identical to the parent; the index macro branch is exact, and the CSS diff contains only the scoped empty-gap rule/comment.

The existing production renderer reproduced the current explorer and index from 48 checked inputs and the same accepted model. The candidate changes only explorer HTML and paired GMI assets among nine outputs. The HTML diff is one wrapper line; all six other generated HTML files remain exact. The actual renderer's changed byte span was transported with baseline/replacement/candidate SHA-256 and final Git blob checks; the reconstructed explorer exactly matches the renderer's 972,414 bytes. No model was generated, and no fenced model01 output was read.

Final focused proof uses 8 cases / 8 fresh anonymous Chrome157.0.8103.39 contexts: EN/ZH at 1440/390/320 px, plus two truly JavaScript-disabled cases. It verifies stable container/message identity, one visibility change per actual transition, zero redundant writes for successive no-match input, correct rendered and accessibility-snapshot language, retained focus/URL/answer identity, zero/one tree entry, Tab to See all, clear/re-entry, exact original spacing, native static links, 44 px navigation and no overflow. Two phone captures were inspected. The initial behavior-only pass and the spacing falsifier remain in the receipt; they are not represented as the final proof.

`TREE_STATUS_VALIDATION_20261109.json` records the exact inputs, source hashes, baseline failures, initial/final candidates, measured spacing regression/correction and native receipts. `verify_tree_status_component.py` extracts the named functions from the canonical verifier and serves only the actual generated main/JSON plus complete shared theme/GMI CSS on an isolated loopback origin, with external requests blocked. It owns no product behavior.

These checks establish the bounded DOM, accessibility-tree and interaction contract. They do not establish spoken screen-reader behavior, the full shared shell/fonts, live account/public admission, system clipboard or deployment. Original Draft, model01 **EFFECT_UNKNOWN / ROOT_UNVERIFIED** and release holds remain; no Tools receipt or navigation owner changed.

## 11.26. Persistent index result feedback — 9 November 2026

At parent `37c7cf217f9d63605843a8b1e860f3e4139486b4`, the index's role-bearing paragraph started hidden. `indexRender()` changed its nested count/no-match content before exposing that host. The revised macro places the same visual paragraph inside one persistent `data-gmi-index-status` wrapper and moves the polite/atomic status attributes to that wrapper. There is no nested status role. Existing bilingual count/no-match spans, count derivation, category/subgroup totals and locale presentation remain unchanged.

The only JavaScript change makes `indexHidden()` assign `hidden` when its value actually changes. Its existing `releaseIndexFocus()` call stays outside the guard, so a requested hide still performs owned focus recovery. Existing `indexText()` already skips unchanged text. Repeated equivalent searches and duplicate language notifications therefore do not mutate the status contents. No count cache, locale observer, query render, history or announcement owner was added.

The existing empty-region CSS rule now includes the index wrapper, keyed to the whole feedback paragraph's hidden state. It must not key to the inner count span: that span is hidden for valid no-match feedback. Actual search-to-legend spacing remains **12 px** at initial load and Clear, and is **42.75 px** with either positive or zero-result feedback in the tested fixture. The existing paragraph's `margin:0` and type remain intact. With scripts truly disabled, feedback remains empty and all 371 native index destinations remain.

Exact source blobs: paired JS **d578f494935c7c2dbc9e6f352d2669e885fef488**; paired CSS **d12725489b7c8baad38ec53570c8f7e25f759606**; macro **9b876f4b543e6335e695991fbca689c8005fa653**; generated index **29d9a58633f05f05a73abba58d5c867750d8a0a7**; verifier **cc73d06d334051ccd6d36a39993f0ab23b37ecb7**; extracting harness **dc2d9b1517cd8bff91d43fe0c34f2dacf20d954d**. Every other JavaScript function, the tree macro branch and the existing tree CSS rule are exact to the parent.

The qualified production renderer reproduced the current explorer/index from the same 48 checked inputs and accepted model. Only the generated index wrapper line and paired assets changed among nine outputs; the explorer and five other HTML pages remain byte-identical between renders. The actual 262,301-byte index was transported using the renderer's checked changed span and exact baseline/span/candidate SHA-256 plus Git blob equality.

Baseline PID76771 fails two cases for the missing persistent owner. Candidate PID78730 passes **14 cases / 14 fresh anonymous contexts**, Chrome157.0.8103.39, zero page errors, exit0, 19.78 seconds. Eight status cases cover EN/ZH at 1440/390/320 px and two actual JavaScript-disabled contexts. They exercise zero → positive → singular → zero → Clear, repeated unmatched/equivalent queries, duplicate language notifications, exact active-language accessibility-tree content, stable node identity, focus, URL/history, disclosure restoration and geometry. Six existing filtered-index cases were also rerun because the shared hide helper serves the rows and shortcuts; queued observer rejection, category/subgroup counts, hidden-focus recovery, retained unrelated focus, history, 44 px shortcuts and sticky geometry all pass unchanged.

Four native phone captures—both no-match panels and both complete filtered pages—were inspected. `INDEX_STATUS_VALIDATION_20261109.json` preserves exact inputs, commands, hashes and results; `verify_index_status_component.py` extracts five named functions from the canonical verifier. The anonymous loopback fixture uses actual generated main content with complete shared theme/GMI CSS and blocks external requests.

This implements the persistent-container procedure described by [W3C ARIA22](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA22); DOM and accessibility-tree observations do not prove spoken screen-reader output. Full shared shell/fonts, live account/public serving, clipboard and deployment remain separate. Original Draft/model01/release holds remain. No Tools, navigation, release or other incumbent owner was changed.

## 11.27. Explicit Clear search on the tree and index — 9 November 2026

### One visible action, one existing search owner

At parent `472146a6532a7bd48db5cdc433ff4e36ecfee456`, tree and index searches lacked an authored, localized clear action. Their native search cancellation was browser-dependent, and Escape cleared even an already-consumed or composing keyboard event. Two baseline cases reproduce the missing control.

The shared `search_box()` now contains one icon button named **Clear search / 清空搜索**, hidden by default. The original 44 px-high field keeps its footprint; a 44 × 44 px suffix replaces the slash hint only while the raw input value is nonempty. Raw whitespace remains clearable. The original search icon, placeholder, bilingual label and persistent result-status containers remain unchanged. The close mark is an original inline decorative SVG matching the existing icon stroke grammar; no presentation/icon registry or model file was edited.

Successful enhancement binds the native button's click, adds the clearable class and synchronizes visibility. The stylesheet suppresses WebKit's native cancel affordance only under that class. Without JavaScript, the custom button stays hidden, the original slash hint remains, and all 371 native destinations stay usable. No inert custom action replaces native behavior.

| Event or state | Result |
| --- | --- |
| Click, native Enter or native Space on the visible action | Focus the existing input, set its value to empty, dispatch its existing input event exactly once. |
| Ordinary Escape in a nonempty input | Use that same clear path. |
| Consumed Escape, composing event or legacy key code 229 | Leave the query untouched. |
| Empty input | Hide the custom action; clearing is a no-op. |
| Raw whitespace | Keep the action available even though the normalized filter may be empty. |
| Index URL/history restores a query | Derive the action from the restored input, including initial loading. |
| A restore is about to hide the focused clear button | Return focus to the input before hiding it; retain unrelated valid focus. |

`clearSearch()` and `syncSearchClear()` are small helpers inside the current search IIFE. The existing input handler remains the sole query/render/URL owner. Tree clearing restores its existing expansion snapshot without changing the selected answer, primary Browse filters, evidence nodes or an open receipt. Index clearing preserves lens, qualified return context and unrelated hash keys, removes only its query through the existing replace-state path, and retains the existing disclosure/history behavior. Locale changes use the existing data-aria owner. There is no second state store, history writer, observer, announcement cycle or translated copy source.

### Rendered source and focused proof

Self-check reconstructs the parent by removing only the two new helpers, one restore sync and the input/keyboard/button binding delta; every other JavaScript byte is exact. The CSS diff contains only the suffix rules. Removing the default-hidden button from the macro reproduces the entire parent macro, including both status branches. Full JavaScript and Python syntax pass.

| Current artifact | Git blob |
| --- | --- |
| Paired JavaScript | **7caa903eb1fd78bb6b4cdd611c1c69d2f0c09224** |
| Paired stylesheet | **4225a93b50eaa668dbc3acf72a0d4c1b4b2d7e6a** |
| Shared search macro | **2b90130394a11df2e4b10fa1ab65041727d18836** |
| Generated explorer | **e765336c2b840108aff2dadb45543ea5524e6026** |
| Generated index | **16be2eb38d020a753df418c0b0abcca1487bf0dc** |
| Canonical browser verifier | **a2ca4d53c03e0e66935877b38a9c87cc45f2507a** |
| Extracting component harness | **7e340af7a59976a186936d322620f6358326f738** |

The current production renderer reproduced the parent explorer and index from 48 checked source inputs and accepted model SHA256 **e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f**. Candidate output changes only the two search-box HTML lines and paired JS/CSS among nine outputs. The other five HTML outputs stay byte-identical. Actual generated spans were transported and verified against complete SHA-256 and Git-blob identities; the explorer is 972,780 bytes and index 262,667 bytes. No model was generated or fenced model01 artifact consumed.

Final native PID33720 passes **36 cases / 42 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, exit0 in 77.23 seconds. Twelve light-theme cases cover both searches in EN/ZH at 1440/390/320 px; two dark cases cover EN390 and ZH320. Four actually JavaScript-disabled cases retain native links and no custom focus stop. The affected existing tree roving, persistent tree status and filtered-index navigation/history suites also pass. Two existing Tab expectations were deliberately updated to traverse the newly visible clear action before the previous destination.

The proof exercises exactly one input event per native activation, ordinary and guarded Escape, raw whitespace, initial/restored history, focus before hiding, language changes while focused, unchanged field geometry, 44 px targets, hint exclusion, native destinations, tree expansion and selected evidence retention. Six light/dark phone field captures were inspected for one clear mark, visible focus, no overlap and intact field geometry.

### Retained fixture correction and limits

The first candidate run was stopped after six failures: its test incorrectly requested the accessible name of the intentionally hidden button. A one-case diagnostic exposed the first assertion with improved logging. The final test checks the hidden aria-label attribute and checks the accessible name after the button becomes visible. Product source and rendered bytes were unchanged. Guarded termination and a process readback proved the original runner absent before the corrected matrix began. The harness now fails fast and requires all 36 expected cases, preventing a partial run from looking complete. Initial, diagnostic and final receipts remain in `SEARCH_CLEAR_VALIDATION_20261109.json`; the stopped run has no numeric exit-code claim.

The renderer's recorded verifier hashes precede that test-only correction. The validation file separately binds the exact final verifier and harness hashes used by PID33720. `verify_search_clear_component.py` extracts the named canonical verifier functions and owns no product behavior.

These results establish the anonymous component's rendered, DOM, accessibility-tree and interaction behavior. Synthetic composition events do not prove OS IME behavior. Spoken screen-reader output, full shared shell/fonts, live account/public serving and deployment remain separate. Original Draft/model01/release holds remain. No Tools, original Paper style hold, navigation, publication or release owner was changed.

## 11.28. Reach the full index through one clear header — 9 November 2026

### Remove the repeated introduction, preserve the page's owners

At parent `16a87f43743fe3a9bae02db7e3d64969871d8cd9`, the full index rendered a large GMI brand and generic introduction, a Snapshot date and product navigation, then a second breadcrumb/title/total sentence and Read as of date before search. Both dates derive from the same `model.asof`. The extra introduction displaced the user's primary task while adding no distinct freshness information.

The existing `page_key == 'index'` now selects a compact variant of `_gmi_product_header.html.j2`. It retains **GMI Explorer** as a real secondary link with its existing `.gmi-product-name` hook and a minimum 44 px target. The sole H1 becomes **All micro-themes / 全部细分主题** in that header. The index's legacy `head()` call/import is removed; its noninteractive breadcrumb, repeated count sentence and second date go with it. The total remains in search and the explicitly labelled Full index footer.

The complete snapshot/stale subtree, `data-gmi-snapshot` value, Brain slot, navigation markup, active index destination and following index content remain exact. No generic head/base template or renderer context was changed. The non-index branch produces identical HTML, including its existing introductory paragraph. No production JavaScript was changed.

### Layout and navigation contract

Desktop uses a 32 px H1 and 24/16 px header block padding. At ≤820 px, the title is 24 px and padding is 16/12 px. Chinese title tracking stays natural at every width. The smaller brand keeps a 44 px-high link target. Title and stale qualification can grow vertically; there is no fixed header height or single-line truncation.

The existing 72 px right reservation and Brain slot positioning remain at ≤820 px. Index-specific navigation and contextual-return bottom margins are 16 px. These rules are scoped through the index header's adjacent siblings, so they reach the return holder that the existing `refreshJourney()` inserts immediately after navigation.

The brand retains its contextual research destination. Theme-return and company-return cases preserve complete qualified fragments, including one upstream research return. Direct entry has no fabricated back action. Initial focus remains on the document, and native Tab moves from brand through an occupied Brain slot to product navigation. Search, clear, result feedback, category shortcuts and index history continue using their existing owners.

| Direct entry, light theme, empty Brain slot | Previous search top | Current search top | Vertical saving |
| --- | ---: | ---: | ---: |
| 1440 px, EN or ZH | 364.78 px | 218.80 px | 145.98 px |
| 390 px, EN | 467.44 px | 282.80 px | 184.64 px |
| 390 px, ZH | 437.19 px | 271.30 px | 165.89 px |
| 320 px, EN | 508.69 px | 282.80 px | 225.89 px |
| 320 px, ZH | 455.94 px | 271.30 px | 184.64 px |

These are measured coordinates within the anonymous generated-main fixture, not a claim about the full shared-shell viewport. Across **66 matched entry/language/width/theme/stale/Brain states**, the saving ranges from **145.98 to 233.89 px**. The comparison keeps the same return and launcher conditions on both sides.

### Exact source and affected proof

| Artifact | Git blob |
| --- | --- |
| Shared product header | **207ad3b122a9db95f4c017413207385275dfee3f** |
| Index template | **0b4a23d3818c27f62778074969270640ef48780a** |
| Paired stylesheet | **5b9c70ed21a5c94dc565258304d061dbabf0bb56** |
| Generated index | **3c6d1512da13534cb23882626c748ca4e269a973** |
| Canonical browser verifier | **1bccdb51065c550a7214e0a2cf7c42728807179c** |
| Extracting header harness | **dec19d9e0bce3cfc0ac6ee2d96e24ec0f064a466** |

The production renderer reproduced the exact parent explorer/index from 48 checked inputs and the same accepted e644fa48… model. Only **gmi-index.html and gmi.css** change among nine outputs. All six other generated HTML pages and gmi.js remain byte-identical. The actual 261,797-byte index was reconstructed from the renderer's checked span and verified against complete SHA-256 and Git-blob identities. Source self-check also confirms exact snapshot/slot/nav markup, exact index content after the removed introduction, and unchanged pre-existing CSS and canonical verification definitions.

Baseline PID264 records **11 original-layout observations / 11 contexts**, exit0 in 31.01 seconds. Those passes verify the baseline's repeated introduction/date and measurement setup; they are not new-header acceptance. Candidate PID3454 passes **23 cases / 23 fresh anonymous contexts**, Chrome157.0.8103.39, zero page errors, exit0 in 47.29 seconds.

Eleven candidate header cases cover EN/ZH at 1440/390/320, three crowded stale states including 768 px, and two dark cases. Each uses direct, research-return and company-return entry with an empty and populated Brain slot. Checks include one H1 and date, exact snapshot identity, stale visibility, full destination fragments, 44 px navigation and brand targets, 72 px reservation, no collision/overflow, no load-time focus movement, native Tab order and existing search/clear behavior. Four actually JavaScript-disabled cases retain 371 links, native disclosures and the static title/date. Six existing filtered-index cases and two Clear-search cases pass against the new geometry. Seven native header captures were inspected.

The Brain button and November 9/20 clocks are explicit fixtures. They exercise the existing docking event and seven-day stale condition without claiming the shared Brain's runtime or a changed public snapshot. No-JavaScript markup does not generate stale qualification, Brain docking or a contextual return; tests deliberately preserve that boundary.

`INDEX_HEADER_VALIDATION_20261109.json` and `verify_index_header_component.py` retain commands, inputs, all measurements and source hashes. Anonymous component proof does not establish full shared shell/fonts, live accounts/public serving, spoken assistive-technology output or deployment. Original Draft/model01/release holds remain; no Tools, navigation or release owner was changed.

## 11.29. Reach every category without a hidden horizontal search — 9 November 2026

### A compact choice with an explicit action

At parent `20179e319a3f5219488fda4f1642a49e77ed8b13`, the phone index presents ten category chips in a horizontally scrolling strip. Most destinations sit outside the first viewport. The index now enhances that strip at the existing **≤640 px** breakpoint with a native **Category / 类别** select and a separate **Go / 前往** button. Desktop retains the existing anchor track.

The select chooses a **pending destination**. It does not assert the category currently in view, and changing it does not scroll, open a disclosure, rewrite the URL or add history. Go invokes the existing retained anchor's click path after revalidating its target. The destination remains selected so the same Go action can be used again. Native pointer click, Enter and Space each invoke that owner once.

The explicit action is deliberate. Disposable native-Chrome probes showed that typing a category name can produce intermediate select changes: an instant-reset prototype fired eleven changes while typing Category 10; retaining the choice still produced two. The final product therefore keeps native selection/typeahead free of navigation effects. Real Energy typeahead is exercised against the product; OS-native popup arrow handling is not inferred from headless probes.

The layout keeps a **44 px select**, **8 px gap**, **44 × 44 px Go**, and the existing **61 px sticky strip**. The select can shrink within the available width; Go remains a stable target. Existing shared tokens, focus treatment and reduced-motion behavior apply. The track's decorative fade is suppressed only for the enhanced picker so it cannot cover the native arrow. No instructional paragraph is added to the page.

### Reuse the category, search and locale owners

`syncIndexJump()` lives alongside the existing category-jump controller. It reads the current eligible anchor/group inventory and counts after `indexRender()`, and active-language labels after the existing locale `apply()`. It does not create another query model, current-category state, URL parameter, storage key, language observer or navigation controller.

| Situation | Required behavior |
| --- | --- |
| Initial or cleared index | Show Choose category / 选择类别, disable Go, and include all ten available categories in canonical order. |
| Unfiltered category with zero topics | Keep it available. Availability comes from group visibility/ownership, not a positive count. |
| Valid choice during filtering or locale change | Retain its ID; update count and the single active-language label. Keep focused select/Go where it is. |
| Pending category no longer matches but other categories do | Reset to the prompt. Move owned focus from Go to the select before disabling Go. Never choose the first result on the user's behalf. |
| No categories match | The existing index hide owner returns owned focus to search before hiding the entire nav. |
| Search is cleared | Existing query/disclosure owners restore the prior disclosure snapshot and category inventory. |
| Hidden, disconnected or reparented target/link at activation | Reject navigation and refresh the pending choice. Do not fall through to a native hash or another category. |
| Passive category intersection | Keep updating existing anchor aria-current behavior; do not rebuild options or overwrite the pending selection. |
| Equivalent filter/locale refresh | Preserve option-node identities when their IDs and labels have not changed; skip redundant value/disabled writes. |

The option labels derive from existing `.l-en`/`.l-zh` category spans and current count elements. The nav, select and Go aria labels use the existing bilingual data attributes. The visible Go label uses the existing translation macro. A prompt is disabled as a destination; Go is disabled until a current eligible ID is selected.

The target validator checks that the retained link remains a connected direct child of the original track and that the destination remains a connected, visible direct child of the index. Go delegates only to that mapped link. The existing anchor handler remains the sole disclosure-open and scroll owner. Query, open=all, lens, qualified return, unrelated hash keys and history remain intact.

### Responsive focus is part of the interaction

The media listener reveals the incoming presentation before transferring focus, then hides the outgoing presentation. A valid focused desktop anchor carries its ID into the mobile pending choice. An unrelated focus owner is preserved, as is a previously pending choice when focus is elsewhere.

When moving from mobile to desktop, owned focus goes to the valid pending anchor, then the current or first available anchor if needed; an entirely stale inventory falls back to the existing index search. Responsive transfers use `preventScroll`, avoiding a focus-induced jump back to the non-sticky desktop rail after the user has reached a distant category. This is presentation focus recovery, not category activation.

Initialization happens before the optional IntersectionObserver branch, so category selection/filtering/navigation still work when that observer is unavailable. The authored select wrapper starts hidden. With JavaScript actually disabled, the original ten category links and all 371 topic links remain available, native anchor jumps and details disclosures work, and there is no inert custom Go action.

### Source binding and focused proof

| Artifact | Git blob |
| --- | --- |
| Paired JavaScript | **b6572ba96c76cf8ee2b1939d538027fe27dfd3e8** |
| Paired stylesheet | **1869d4bb1dbcd3ee56756a98da77427dd732b03e** |
| Index template | **4556d16e03e06375a314c7278c4936dea36fd0e9** |
| Generated index | **d0cff23fec423c3480ea12ee200c272396fd53a0** |
| Canonical browser verifier | **7c99a499f7e3508896175f47d74f3ddd6b294181** |
| Extracting component harness | **0fcfae4962d4553d711bb00015ba45ee6d59b4f1** |

The production renderer reproduces the exact parent explorer/index from 48 checked inputs and the same accepted **e644fa48…** model. Only index HTML and paired JS/CSS change among nine outputs; all six other generated HTML pages remain exact. The actual index adds a 488-byte nav-prefix span and is **262,285 bytes**, SHA256 **3e6e6f4846598bc6240f3aa69c5523a5500e7f79f7838e655ea7ecd7800536d4**. Its full SHA-256 and Git-blob identities were checked after transport.

Self-check reconstructs every unrelated JavaScript byte by removing this category-controller change and two synchronization calls. Previous CSS is an exact prefix, and the index template differs only in the nav prefix. Thirty-nine existing top-level verification definitions are exact. The affected `index_filtered_shortcuts` test deliberately uses select+Go on mobile while retaining its count, target, history, stale-observer, focus and sticky-geometry assertions.

Baseline PID81615 records two expected failures because the exact parent has no picker/Go. Final PID81814 passes **24 cases / 24 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, exit0 in **37.83 seconds**. Six mobile cases cover EN/ZH at 390/320 px and two dark states. Two responsive cases cover 640/641 px, destination identity, unrelated focus, late-category focus-induced scrolling and all-stale recovery. Two observer-disabled and four actual JavaScript-disabled cases pass. Six existing filtered-index, two Clear and two persistent-index-status cases pass.

The matrix also verifies three native Go activations, repeated destination use, the final empty category, all six stale link/group conditions, valid and invalid selection recovery, equivalent refresh identity, focus before hide/disable, 44 px targets, the 61 px strip, retained URL/history and no horizontal overflow. Six new viewport captures were inspected. Native popup interaction, spoken assistive-technology output and full shared-shell/live-account behavior remain separate.

Two initial harness launches stopped at a missing newline between the module docstring and import, before any browser was launched. The harness was corrected and syntax-checked; product bytes did not change. Those exit1 receipts remain explicit in `CATEGORY_PICKER_VALIDATION_20261109.json`. Final browser and renderer hashes bind the accepted source and exact verifier.

`verify_category_picker_component.py` extracts the named canonical verification definitions and owns no product behavior. Original Draft/model01/release holds remain. No fenced model result, Tools owner, shared admission, navigation publication or deployment boundary was changed.

## 11.30. Enter company evidence sooner and recover search safely — 9 November 2026

### A company task header, with the evidence intact

At parent `9bdc486c6b7622d9f306d29e9d12d572ed88415c`, company entry repeats a generic product introduction, a noninteractive Research breadcrumb, a second title region and a sentence describing the search workflow. The company template already has **one page-level snapshot**: its old `head()` call does not receive an as-of value. This change does not claim to remove a duplicate company date.

The existing shared-header branch now recognizes exactly `page_key == 'companies'`. GMI Explorer remains a small real link with a 44 px minimum target; **Company evidence / 公司证据** becomes the single H1 in that header. The page then proceeds through the existing active navigation and utilities to search and results. The issuer page retains its own existing title path.

The compact index CSS declarations are shared with the company task header using equally specific `:is()` selectors. This preserves their 32 px desktop / 24 px narrow title, 72 px Brain-slot reservation, mobile snapshot wrapping and 16 px nav/return spacing. No alternative header owner, route, component framework or token set is introduced. Index HTML remains byte-identical.

The card remains source-rendered. Its company, ticker, product, theme, source publication date, planned lifecycle, named platform, source URL/label, unavailable-source behavior, historical-context qualification and issuer action are unchanged. The interpretation guide remains complete. Only the final standalone paragraph that repeats the guide's qualification is removed. The source date **26 February 2024** remains separate from the page snapshot **3 November 2026**.

### Count the filtered companies and keep focus on a surviving control

The existing company catalogue controller still owns query, history and result filtering. `companyHidden(node, hidden)` is a small helper within that controller: when hiding an owner that contains the active element, it first focuses the existing company search. It then assigns `hidden` only when the value changes. It applies to company cards and the no-match container.

Explicit Clear search focuses search **before** emptying its value and invoking the existing `updateCompanies()` path. Pointer click, Enter and Space continue to use the native button and make exactly one existing replaceState update. Hashchange, real back/forward and locale refresh use the same existing owners; no observer, return stack, query parameter or state store is added.

| Situation | Result and focus |
| --- | --- |
| Blank or whitespace-only normalized query | Preserve the on-file count: N companies with evidence on file / 有收录证据的公司：N 家. |
| Active query | Report N matching companies / 匹配到 N 家公司, with English singular handled. The count means visible company cards, not product connections or the complete catalogue. |
| Focused card is filtered out | Move focus from its source or issuer link to search before hiding the card. |
| Focused no-match Clear is about to disappear | Move focus to search before hiding its container. |
| Focus remains in a surviving card, navigation, guide or another unrelated control | Leave it in place. No load-time focus movement. |
| Equivalent input/history/locale refresh | Skip unchanged hidden assignments and complete localized count text. Preserve card/control identities. |
| Query has no match in a populated catalogue | Show No matching company and the native Clear search action. |
| Actual catalogue has no admitted company cards | Preserve No company evidence yet / 暂无公司证据 and Explore themes; keep Clear hidden. A search reset must not promise unavailable evidence. |

The visible Chinese Clear label is aligned with the existing search control: **清空搜索**. The polite count owner remains the existing element; this work verifies DOM mutation and focus behavior, not spoken assistive-technology output.

### Measured layout and exact source scope

Eleven matched header scenarios cover EN/ZH at 1440/390/320, crowded stale/return states including 768 px, and two dark states. Each uses direct and research-return entry with empty and populated fixture Brain slots: **44 matched layout pairs**. Search moves upward by **145.984375–215.140625 px**.

| Direct entry, light theme, empty Brain slot | Previous search top | Current search top | Space removed before search |
| --- | ---: | ---: | ---: |
| 1440 px, EN or ZH | 343.78125 px | 197.796875 px | 145.984375 px |
| 390 px, EN | 454.1875 px | 265.796875 px | 188.390625 px |
| 390 px, ZH | 401.4375 px | 254.296875 px | 147.140625 px |
| 320 px, EN | 472.9375 px | 265.796875 px | 207.140625 px |
| 320 px, ZH | 442.6875 px | 254.296875 px | 188.390625 px |

These are generated-main browser measurements with exact accepted source/CSS. The Brain launcher and November 9/20 clocks are explicit layout fixtures. They preserve the existing docking/stale boundary and do not change the published snapshot or establish shared Brain runtime.

| Artifact | Git blob |
| --- | --- |
| Shared product header | **b3b860d924408c4d4de0dcb7ad7ea38f7f1e0788** |
| Company template | **729e2a4a93246d87e9203abd84efdc16fb6f1aea** |
| Paired stylesheet | **dba2809660f0f16d25325db4bb401674758529a2** |
| Paired JavaScript | **1facd1b2edcb062422ff65f22689edd7ae160cf8** |
| Generated company page | **c4b1c81c92c270411c6698a473b55354a05dc8a5** |
| Canonical browser verifier | **89f32143b6b61e0c12bf1534452550a4e416e1d1** |
| Extracting company harness | **b21ada78f14a4df72a49e9f3b74fcb4efd35e2d6** |

The production renderer reproduces all nine parent outputs from 48 checked inputs and the same accepted **e644fa48…** model. Final rendering changes only **gmi-companies.html, gmi.css and gmi.js**; all six other HTML pages, including index and issuer, remain exact. Paired template/site assets match. The actual company page is **65,156 bytes**, SHA256 **fda702382d62068f8f39874bcd07bbb915ddacee6a3d4f734b337b58f3e47d3c**, checked against its full transported bytes and Git blob.

Source self-check reverses only the company JS block/reset order, compact CSS selector extension, exact companies header branches and enumerated company-template edits to reproduce their parents. All 44 previous suite-level verifier definitions remain exact; four company definitions are added. Local self-check diagnostics were corrected to reinsert the removed paragraph only at the final template block and to enumerate the actual suite definitions inside the Playwright context, with an asserted count of 44. Those diagnostic corrections changed no product or browser-test bytes.

### Focused proof and builder reuse

Baseline PID42094 records **11 passing original-header observations** and **two expected failures**: Reset hides its focused empty-state owner before releasing focus, in EN390 and ZH320. Exit1, 25.42 seconds, no page errors. Baseline header passes describe the old geometry and are not new-header acceptance.

The initial candidate PID43386 passed 29 cases. A subsequent clarity improvement distinguished active-query counts from the on-file catalogue count. Its initial source, renderer and proof are preserved under `candidate-initial-*`; they are not reported as the final wording proof. Final renderer PID63976 exits0 in 1.90 seconds. Final browser PID66703 passes **29 cases / 29 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, exit0 in **46.77 seconds**.

The final matrix includes 11 header scenarios, six company focus/count scenarios across EN/ZH and 1440/390/320, four actually JavaScript-disabled cases, two genuinely empty-catalogue fixtures, two existing source-context cases, two real issuer/return journeys and two existing mobile category-picker regressions. It exercises native reset activation, focus before hide, surviving focus, repeated-write suppression, exact localized count scope including whitespace, actual history traversal, 44 px navigation, one H1 and snapshot, slot reservation, no collision or overflow, and static source links.

The empty-catalogue case is produced by the real renderer from an in-memory deep copy of the accepted model with `issuers=[]`. No replacement public model is saved or consumed. Its fixture model SHA256 is **d7425eff920310d8febecd53672fe95173e1c60815e554e51d5e34dc7eb22269**. The component harness alone supplies this fixture; the canonical full-site context receives no incompatible empty-catalogue keyword.

Nine final company captures were inspected, covering EN/ZH light/dark, crowded stale/Brain/return states and no-match recovery. The card truthfully continues below the first phone viewport; it is not compressed to fit an artificial fold.

`COMPANY_ENTRY_VALIDATION_20261109.json` retains exact inputs, process receipts, source checks, both baseline failures, all final measurements and captures. Final geometry/comparison arrays were verified on the native host as exactly equal to the initial accepted layout proof; the transported final delta was reconstructed and checked with normalized sorted-JSON SHA256 **d871e29941e34e7e43eb0ba0c146f1927ed6d4fffb15ac5cd1eea81422b6b74d**. This binds the final count/focus results without replaying unchanged measurements.

Original Draft/model01/release holds remain. This proof does not establish full shared shell/fonts, live account/admission, current hosted CI, public serving, spoken assistive technology or deployment. No fenced model result, relationship publication, Tools owner, shared admission or release control is changed.

## 11.31. Recover qualified returns and make relationship availability actionable — 9 November 2026

### Keep return removal inside its existing owner

At parent `49d47033f4d758af2ec7212fccee04d762fec956`, `refreshJourney()` removes a return holder as soon as its qualified context disappears. If the Back link owns keyboard focus, the holder is removed while still containing the active element. The exact baseline reproduces this on the company and relationships routes.

Only that removal branch changes. Before removing a holder that contains the active element, it focuses the existing `a.gmi-product-name[href]` outside the holder with `preventScroll:true`. If focus remains in the holder and a product navigation link exists, that existing link is the bounded fallback. A focus handler that already moves to another surviving control is respected. Unrelated focus never enters this recovery path.

If the brand and navigation destinations are both unusable in an exceptional malformed DOM, the invalid holder is still removed. The code does not keep a stale Back action, create a replacement element, assign tabindex to the page, manufacture a return destination or throw because the brand is absent. That exceptional fixture is explicitly not represented as successful focus recovery.

The existing `safeReturn()`, `originalHrefs`, source/catalogue/research projection and following link-refresh loop remain byte-identical. Recovery does not activate the focused link, navigate, call a history writer or copy the retired destination onto the brand. The ordinary href projection completes synchronously afterward. Valid-to-valid context changes keep the same Back anchor, including during localization.

`preventScroll` scopes the effect of the focus call. A diagnostic observed scrollY **300 before focus, 300 immediately after focus, and 240 after the return holder's layout removal**. The later browser layout adjustment must not be misreported as a focus-induced jump or suppressed by another custom scroll owner. The final verifier checks those effects separately; history scroll restoration remains with the browser.

### The Relationships page states availability, then offers useful work

The compact task header now applies to the exact **relationships** page key as well as companies. Its H1 is **Company relationships / 公司关系**. The real brand link, snapshot/stale owner, Brain slot, active tabs and utility navigation remain unchanged. The generic product introduction and old noninteractive breadcrumb/title/instruction region are removed. No stylesheet change is required; the existing compact header declarations are reused.

The state heading becomes **Public relationship view unavailable / 暂无公开关系视图**. The template establishes that no verified public projection is available in this snapshot; it does not inspect every underlying clearance decision. The new heading describes that actual boundary without asserting that no relationship has been cleared.

The existing two explanation paragraphs and native publication disclosure remain exact. They still distinguish a publication restriction from the absence of real relationships, withhold parties/details/figures here, and distinguish public source access from permission to display facts, magnitudes or excerpts.

The panel now gives **Browse company evidence / 浏览公司证据** the primary action. Explore themes and Coverage & methodology remain secondary destinations. These are ordinary native anchors in source markup, including without JavaScript. The new action does not promise a populated company catalogue or expose relationship records. It reaches the existing company page, whose admitted evidence and empty-state rules remain authoritative.

| Entry context | Company-evidence action |
| --- | --- |
| Direct arrival | Ordinary `gmi-companies.html` destination. |
| Qualified theme research | Existing company destination carrying the qualified upstream research return. |
| Qualified company catalogue | Reuse its exact permitted catalogue search and one qualified upstream research context. |
| Rejected or absent return | Ordinary company destination; rejected values are not forwarded. |
| JavaScript disabled | Ordinary company link and native publication disclosure remain usable; no dynamic return is invented. |

The unchanged navigation owner already supplies those projections to the new main-content link. No new routing, URL, storage, language, permission, publication, source-model or retry owner is introduced. No relationship parties, records, financial amounts, excerpts or hidden relationship-search payload is rendered.

### Exact source and measured presentation

| Artifact | Git blob |
| --- | --- |
| Shared header | **945b464b1a0380e4b1b86c873866f273fe0c9574** |
| Relationship template | **e30d0df9e359e529c707468cf952e0aa84a36987** |
| Paired JavaScript | **ef00b9aca6d4e343a8dea7bbd8010020fec671f1** |
| Generated relationship page | **8a693c57b649b300a5c3e53e9d24cfa9c92987c7** |
| Canonical verifier | **77944d4bb9e863d97635dbeda007eba1c30424d3** |
| Extracting return/relationship harness | **20c26d3a87906a884f81bf25ba4a739d25533bb7** |

Forty-eight checked renderer inputs and the same accepted **e644fa48…** model reproduce all nine parent outputs exactly. Final rendering changes only **gmi-relationships.html and gmi.js**. All six other HTML pages, including company/index/issuer, and gmi.css are byte-identical. The paired template/site script is identical.

The generated relationship page is **61,988 bytes**, SHA256 **86243e69c432370eb83600a45cda897e29a1a63697f55e3a72ccffcf9468c377**. Full transported bytes match the native Git blob. Native subtree checks preserve the complete publication disclosure, both explanation paragraphs, product navigation, snapshot and Brain slot. Source reversal reproduces every prior byte outside the return-removal branch, exact relationship header branch and enumerated template changes. All **48 existing suite-level verifier definitions** remain exact; five definitions are added.

Eight header cases cover EN/ZH at 1440/390/320 plus two crowded dark/stale/Brain cases. Direct, research and catalogue entry produce **24 matched layout pairs**. The publication panel begins **145.984375–196.390625 px sooner**. Six final relationship captures were inspected. The Brain button and stale clock are explicit fixtures, not shared-runtime or changed-public-snapshot claims.

### Focused browser proof and diagnostic corrections

Final PID50506 passes **28 cases / 28 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, exit0 in **52.66 seconds**. The matrix is:

- Eight relationship-header cases and 24 matched layouts, with complete source-qualified destinations, active navigation, one H1/snapshot, 44 px actions and no horizontal overflow.
- Twelve return-focus cases: EN/ZH on company, issuer, index, coverage, relationships and state-reference routes.
- Two actual relationship-to-company journeys: direct, research, catalogue and invalid entries, native primary Enter, native disclosure Enter/Space, preserved company query and real return to research.
- Four genuinely JavaScript-disabled cases at 1440/320 EN/ZH, including native disclosure and actual company navigation.
- Two existing company focus/count regressions.

The return matrix covers absent and three rejected returns, valid anchor identity and localized labels, unrelated source/nav focus, real hash/back/forward restoration and unchanged history ownership. Relationship cases additionally exercise hidden/missing brand fallback, another focus handler's redirect, the focus-time scroll measurement, and an exceptional fixture with no usable destination. No exceptional focus success is fabricated.

Corrected baseline PID43349 records **eight original-header observations** and **two expected focused-holder removal failures**, exit1 in **23.48 seconds**. Those header observations describe the previous layout; they are not upgraded-page acceptance.

An earlier baseline run, PID39951, exposed a test-fixture serialization error: the nested research-return string used a different parameter order from the existing canonical projection. Three fixture constants were corrected to that owner's order; product bytes were unchanged. The original ten-failure report is preserved, distinguishing eight fixture-comparison failures from the two actual focus failures.

Initial candidate PID45302 passed 16 cases and stopped at a test that equated final scroll position with the focus effect. Diagnostic PID48600 established 300→300 during focus and 300→240 after removal. The corrected verifier records native focus timing and keeps later layout behavior separate. The initial candidate and diagnostic are preserved; no product code was changed to satisfy either test correction.

`RETURN_RECOVERY_VALIDATION_20261109.json` retains commands, exact source/input hashes, original and corrected receipts, final measurements and scope. The component harness extracts the actual definitions from the canonical verifier and owns no product behavior. No additional relationship model is generated or consumed.

The editable [Relationships · Availability](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-A-0) page shows the current EN390 Day state, ZH320 Noir catalogue-return state and an expanded publication disclosure. Builder guidance must keep return retirement, publication availability, catalogue content and release acceptance separate.

Original Draft/model01/release holds remain. This local proof does not establish full shared shell/fonts, live accounts/public admission, spoken assistive technology, current hosted CI or deployment. No fenced relationship data, Tools owner, original protected Paper style or release control is changed.


## 11.32 · Coverage separates company populations, core themes and source clocks — 9 Nov 2026

### Problem and source-bound decision

The old coverage view combined two different populations in its company-reason legend. In `_activity_market` in `scripts/gmi_coverage_proof.py`, resolved issuer IDs are deduplicated company records; each unresolved security contributes separately to `IDENTITY_NOT_QUALIFIED`. A label such as “726 companies” therefore counted four listings as though their distinct companies were known. The global hero also added the US and China market numerators while saying “any theme”, without establishing a globally unique company population or including extended activity. Separately, the old footer labeled `provenance.built_at_utc` as a review-ledger date, although it records model creation.

This phase changes the existing frontend only. Parent `ed2a0d178b459a8bdb1cc233f257ee82d946f71a`, accepted model SHA256 `e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f`, builder blob `900253d42a7b1d43ad41aa493e8032444c4570de` and the producer/model inputs remain bound in [COVERAGE_CLARITY_VALIDATION_20261109.json](COVERAGE_CLARITY_VALIDATION_20261109.json). No activity is admitted, record cleared, private graph projected or source regenerated by this work.

### Population contract and implemented result

The page now begins with **Core-theme company coverage / 核心主题公司覆盖** and separate US and China cards. Each displays the unchanged admitted numerator, company-count bounds, matched-company count and, when nonzero, listings without a company match. “Matched” means linked to a company record; identity qualification remains separate.

| Accepted market input | US | China |
|---|---:|---:|
| Admitted companies | 1 | 0 |
| Company count range | 1,928–1,931 | 1–1,019 |
| Matched companies | 1,927 | 0 |
| Listings without a company match | 4 | 1,019 |
| Matched companies not counted | 1,926 | 0 |

Only the identity reason mixes populations. The template subtracts unresolved listings from `IDENTITY_NOT_QUALIFIED`, leaves every other reason untouched and iterates the existing configured reason-word order. The resulting US breakdown is **722 identity-unconfirmed companies, 1,200 vendor-only companies and 4 companies without activity evidence**: exactly 1,926 = 1,927 − 1. China has no resolved-company reason population; its 1,019 unresolved listings remain visible with their original range. Zero resolved companies never produces an “all counted” or complete-coverage claim. No count is silently clamped, no uncertain percentage is manufactured, and the two markets are not summed into a globally unique total.

Core-theme activity is a different measure. Both summary counts and all 68 cells now derive from acceptance-tier micros and `admitted > 0`: one core theme with admitted activity and 67 without. The 303 extended micro-themes are explicitly separate and excluded. This avoids combining a core-only EMPTY count with an admitted total that can include extended themes. A proposed-only note, when present, describes a subset without admitted activity. It does not label `kind == held` as every pending proposal, or `kind == acc` as necessarily EMPTY. Theme counts are not distinct market-company counts and need not reconcile to the market numerator.

### Interface, disclosure and clocks

The shared compact task header adds only `page_key == 'coverage'`: one **Coverage & methodology / 覆盖与方法** H1, original snapshot/stale owner, active navigation, qualified return, 44 px brand target and 72 px Brain reservation. The generic repeated introduction, breadcrumb/title block and second as-of are removed. The six other rendered HTML pages and JS remain byte-identical to the bound baseline; CSS changes are shared only through page-specific coverage rules and the two equivalent selector wrappers described below.

Market cards use two columns at desktop and one on narrow screens. The company-reason list is a native disclosure with explicit company units. The **Method & sources / 方法与来源** disclosure contains the admission rule, the distinction between matching and identity qualification, the source's range calculation, theme-versus-company units, the independent public-publication check, the unchanged corrections statuses and “Not measured yet” accuracy status. These explanations stay available on demand while the initial screen prioritizes counts.

The source adds between one and the number of unresolved listings to the matched-company count when unresolved listings exist; without them it reports an exact count. That is the existing producer rule, not a newly inferred estimate. Method copy makes its meaning explicit.

Clock fields are intentionally narrow:

- **Snapshot as of / 快照截至** uses `model.asof`; do not assert that this always equals a directory snapshot because the producer accepts an explicit as-of value.
- **Coverage model generated / 覆盖模型生成于** uses `provenance.built_at_utc`, retaining the exact `datetime` and visible UTC time. This accepted model was generated on 4 Nov 2026 at 02:29 UTC.
- **Sources / 来源** lists company filings, exchange symbol directory and review records without inventing a source-specific review timestamp.

Native disclosure semantics provide Enter/Space and no-JS operation. Language changes preserve independent open states, URL/history and focus. Only the existing caret transition moves; reduced-motion proof reports zero transition duration. No new data, route, locale, history, storage, animation or navigation owner is introduced.

### Verification and diagnostic interpretation

Final native render PID **12941**, exit 0, 1.98 s, changes only `gmi-coverage.html` and `gmi.css` relative to the exact source/accepted-model baseline. The final coverage HTML is 75,416 bytes, SHA256 `893408143f6c0cb1db08084ad9c7c57b56386421f3a3958f1879a87f9035b745`, Git blob `5df5c79f27a467894d125da61d3cf88b3969edf9`. Paired CSS is exact; JS remains blob `ef00b9aca6d4e343a8dea7bbd8010020fec671f1`.

Final native render tests PID **15231**, exit 0, **28 passed** (4.82 s pytest, 5.37 s process), use the unchanged production renderer and all canonical test bodies. The isolated verification root overrides only the local `proof_model` fixture to load the retained accepted model hash; the committed canonical fixture remains exact. Assertions cover publication withholding, one-H1/page laws, exact reason accounting and units, bounds, mixed and empty populations, all matched companies counted with and without unresolved listings, core/extended separation, consistent mixed-disposition fixtures and independent clocks surviving repeated rendering. The isolated root reports the existing unregistered `needs_full_checkout` mark warning.

The existing frontend regression path `tests/test_gmi_explorer_s3_s4.py` was already authored by the principal integration commit `2a9d6d6d0ce1d0cd8234acfaa9e0ddf0bd8d726f`; its blob there, `4860c8af14d5eaf65a5ef88b4ca2e8bc4b918998`, is exact at this phase's parent. This establishes the specific path's ordinary frontend ownership without consuming the original model01 worker's unknown result. Four S3 tests update only obsolete title strings from the already accepted relationship phase; withholding assertions remain. Eight prior fixture/helper/test definitions are exact. Producer, model, presenter, variants and the original model test remain untouched.

Final browser PID **15311**, exit 0, **24 named cases in 24 fresh anonymous contexts**, 0 page errors, Chrome **157.0.8103.39**, 41.58 s:

- Eight header cases cover EN/ZH at 1440, 390 and 320 px, plus crowded dark-mode cases. Direct and research-return entries provide 16 matched layouts.
- Six disclosure cases cover EN/ZH with normal motion, reduced motion and JavaScript actually disabled. Reasons, units, source clocks, focus, locale and independent open states are asserted.
- Two existing upstream research-return journeys and two coverage return-focus regressions use actual generated routes.
- Four search-clear and two mobile-category-picker regressions protect the two equivalent CSS selector changes.

The first market card starts **194.9375–254.09375 px sooner** across the 16 matched baseline/candidate observations. Seven coverage captures were visually inspected. All **79 prior named Python function definitions, including nested helpers**, in the canonical browser verifier remain AST-exact; three coverage-specific functions were added.

Both unchanged design-asset gate functions pass. The scanner interpreted two prior BEM-selector `--` strings as custom-property references. Wrapping those existing selectors in equivalent `:is()` forms resolves the false positives without altering the scanner or its accepted card-class warnings. The clear/picker browser cases prove their behavior after that change.

Diagnostic failures are retained, not relabeled as acceptance. The first test-file write failed before effect because the isolated tests directory did not exist. Initial test PID 93506 then lacked exact historical variant fixture inputs; hash-bound canonical JSON/parquet were acquired read-only and the tests passed. Initial 18-case and pre-copy 24-case browser reports remain separate; final acceptance follows the explicit company-count-range and Chinese core-theme-unit refinements.

A final source reconciliation found that the old **committed** coverage HTML (blob `3c0f21129b1a799e4406998ad1a69b373b339071`) differed from the retained accepted-model baseline (blob `167364ad1bae490799e853743943c89bc93c5fe7`) in reason iteration order and the old mislabeled review-ledger date. The baseline receipt's `all_nine_outputs_exact` means exact against the **prior phase's rendering**, not every committed site output. Both old versions are retained in the diagnostic comparison. The candidate reconstructs to the verified full native SHA and blob and is the coverage HTML delivered here. This distinction does not create a new model or change the counts.

### Paper and builder handoff

Paper file `01M5H6EARN9YHQV17JC6ZG9BRY`, page **Coverage · Companies and listings** (`p-B-0`), now contains one editable flow group `9K8-0` with five specimens: CV01 EN390 Day and CV02 ZH320 Noir phones, CV03 expanded US reasons, CV04 complete method/source clocks and CV05 the ZH core activity strip. Phone shells remain 844 px viewports; below-fold content is not compressed away. Full components are visible alongside them. A final group capture confirms their layout; original relationship roots `8T0-0` and `8V9-0` read back exactly and token hash remains `ac191fd9`.

Build root `7M9-0` gains module 16, **Coverage uses honest units and clocks** (`9O4-0`, title `9O5-0`, body `9O7-0`); the proof module becomes 17. It spells out the accounting formula, zero-population behavior, core/extended distinction, source-clock mapping and native disclosure implementation.

The local proof uses actual generated main content, shared theme/GMI CSS and unchanged production JS with external requests blocked. Brain/stale clocks are explicit fixtures. It does not establish full shared-shell/font runtime, spoken assistive-technology output, live account/admission, current hosted CI, deployment or public acceptance. PR10676 stays Draft; original model01 `EFFECT_UNKNOWN/ROOT_UNVERIFIED`, result-consumption/retry/replacement restrictions and every original release hold remain. No merge or deployment is attempted.


## 11.33 · Recover failed interactive research through the native index — 9 Nov 2026

### Defect and bounded scope

At parent `e0d7550087c564529270c12049ae62782d5b0101`, the payload parse/validation catch installed a click handler on the mobile Browse button. That button is hidden while `data-gmi-ready` is absent, so the supposed recovery action was unreachable. The notice also called the source-rendered starting answer simply “the answer”, although a nondefault requested hash had not been rendered. The catch returned before the normal history listeners and observed language alone, leaving the existing full-index link on stale return context after hash/Back/Forward or lens changes.

Two baseline browser cases reproduce the missing inline action/ambiguous notice and stale global index context. The first fails at the new wording assertion; its retained observation records zero inline recovery anchors. The second uses the existing global index link and fails after a real hash change. These are defect receipts, not accepted results.

This phase changes only the existing frontend payload-failure branch and one initially hidden native anchor in `templates/gmi_map.html.j2`, plus paired generated output and focused verification. It uses the same retained accepted model SHA256 `e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f`. No model, public JSON, producer, source admission or publication decision changes.

### Reader workflow and preserved evidence

The failure notice now says **Interactive research could not load. The starting topic is shown below. / 交互研究未能加载。下方显示起始主题。** One native **Open the full index / 打开完整索引** anchor appears inside the existing notice region. Its ordinary href supports keyboard activation, native link menus and opening a separate page. The starting topic remains visible and is never presented as the successfully selected requested topic.

Browse, Reset and Copy remain unavailable. The source-rendered dated evidence, company/source actions, product context, Evidence coverage and native Source receipt, Theme details and taxonomy disclosures remain available. The empty Related topics section is hidden only in this failure branch: its payload container must have neither element children nor non-whitespace text, and its nearest section must remain inside the answer. The adjacent evidence-coverage section is retained. Normal topic rendering and no-JavaScript content are not rewritten by this condition.

The copy keeps the 26 Feb 2024 source publication, Planned lifecycle and current-delivery/revenue limitation distinct from the 3 Nov 2026 snapshot. Recovery does not infer newer business facts.

### Existing journey owner and failure boundaries

The native anchor is in the markup before `restoreCompanies()` calls `refreshJourney()`. That existing owner captures the original href and qualifies all main links. No second URL parser, return policy or navigation state is introduced.

Within the failure branch only:

- `hashchange` and `popstate` call the existing `refreshJourney`.
- The existing observer watches `data-lang` and `data-gmi-lens`. Lens observation is necessary because the incumbent lens action uses `history.replaceState`, which does not dispatch either history event.
- Only a language mutation runs `languageOptions()` and rewrites the localized failure notice. Either observed attribute refreshes journey links.
- The branch returns without setting ready, reparsing, fetching, retrying, changing the displayed topic or writing history.

The original `safeReturn`/`originalHrefs` policy remains exact. Qualified context follows native index navigation; an absent or rejected context restores the original `gmi-index.html` href. Returning to the still-failed research route retains the requested context while continuing to show the explicitly identified starting topic. Language changes preserve the same focused recovery anchor and answer nodes.

No-JavaScript remains a separate state with the existing `noscript` native index action. A missing bundle or exception before payload parsing is outside this catch; static global navigation remains available. A valid payload with a missing topic, or a valid topic excluded by filters, retains its existing notice and Clear filters owner. The new failure anchor stays hidden in those states.

### Source and focused browser proof

Final native render PID **16628**, exit 0, **1.75 s**, changes only `gmi.html` and `gmi.js` against the bound accepted-model baseline. Six other HTML pages and CSS remain byte-exact; paired JS is exact. Removing the one added native anchor from the generated explorer reproduces the canonical parent explorer exactly, including its public payload.

| Delivered source | Exact Git blob / SHA256 |
|---|---|
| Paired GMI JS | `34b2ad1110ace6a667e87e7164ff74bde701eb85` / `74db8222c79911a06add34d076e69d7e838aa67a21740522d8c31b60e4f58896` |
| Map template | `fd6ed9c5bfa16e0cfeb1bd964e84ab809fb6595d` / `4ef78e0c937e00472de19ff6ca676eff3d0cc64b4a328b3a9b6ea8cdcbb4cb8b` |
| Explorer HTML | `9c142c6854de795372cc2b256d74eab6071cf3ea` / `8cdbadf83bcfb49153f4c0f258f72541349d0eb34becbf34772f00d2ccfe676d` |

Final browser PID **22269**, exit 0, **20 named cases in 22 fresh anonymous contexts**, zero page errors, Chrome **157.0.8103.39**, **29.70 s**:

- Six malformed-payload scenarios cover EN/ZH at 1440, 390 and 320 px; two dark scenarios cover EN320 and ZH390.
- Eight schema faults cover categories, paths, connections, source fields, duplicate IDs, missing default ID, category labels and invalid parents.
- Two failure journeys exercise actual hash changes, clear/Back/Forward, the existing lens `replaceState`, locale/focus retention, removal of old/unknown fields, bounded query qualification and rejected overlong context.
- The native href is opened in a second page and activated with Enter, followed by the real index return to the still-failed research route.
- Two boundary cases each use valid JavaScript and an actually disabled-JavaScript context: normal Clear filters/answer focus, distinct missing-topic behavior, and the existing native no-JS index route remain intact.
- Failure scenarios assert that the empty Related section is hidden while Evidence coverage remains visible. EN390 and ZH320 also open/close Source receipt and Theme details with Enter/Space, preserving focus, URL and history.

All eight final native screenshots were visually inspected across the principal and design-judgment roles. The notice/action fit, evidence hierarchy and retained disclosures have no observed overflow or empty related-content invitation. This is rendered component evidence; it does not assert spoken assistive-technology behavior.

The canonical browser verifier registers these cases. All **86 existing function definitions**, compared by qualified lexical path and occurrence, remain AST-exact. Four new top-level test helpers and their two nested helpers are added. This count avoids collapsing duplicate nested helper names. The isolated `verify_payload_recovery_component.py` harness extracts those canonical definitions, serves actual generated main content and production GMI JS/CSS, blocks external requests, and uses explicit Brain/stale fixtures. It owns no product behavior. [PAYLOAD_RECOVERY_VALIDATION_20261109.json](PAYLOAD_RECOVERY_VALIDATION_20261109.json) includes exact input/source hashes, commands, retained native receipts and source self-checks.

### Diagnostics retained separately

Initial candidate PID 94219 passed the first 16 cases and then timed out in the rejected-context test predicate. A bounded diagnostic captured both global and inline hrefs already restored to exactly `gmi-index.html`, with no added product history writes. The test now asserts that exact attribute directly. No unproven null-serialization cause is claimed and no product behavior was changed for that predicate.

The corrected pre-related candidate passed 20 cases/22 contexts at PID 1678. Its source and reports remain separately retained. Visual inspection then identified the empty Related section; the final source hides only that empty section and strengthens checks for retained disclosures. PID 22269 is the final acceptance for the delivered JS. Earlier results are not substituted for this final run.

### Editable Paper and builder contract

The [Research · Load recovery](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-C-0) page contains flow group `9Z7-0`: F01 EN390 Noir (`9O9-0`), F02 ZH390 Day (`9QM-0`) and F03 complete starting-topic fallback (`9Z9-0`). The first two are truthful 844 px viewports; the separate full component shows below-fold source/evidence/coverage/disclosure content. The empty Related block is absent. Existing source-receipt seed specimens are preserved.

Build root `7M9-0` gains module 17, **Recover failed topic research** (`A1B-0`, title `A1C-0`, body `A1D-0`); the proof module becomes 18. It records the failure/no-JS distinction, starting-answer semantics, native anchor, incumbent projection owner, lens/history event behavior, empty-section condition and available evidence. It explicitly excludes retries and new URL/state owners.

PR10676 stays Draft. The original model01 `EFFECT_UNKNOWN/ROOT_UNVERIFIED`, result-consumption/retry/replacement restrictions and every release hold remain. This local proof does not establish full shared-shell/font runtime, live account/public admission, current hosted CI, deployment or release acceptance. No fenced model result, shared Tools writer, original protected Paper style, release control or production environment is changed.


## 11.34 · Primary search respects consumed and composing Escape — 9 Nov 2026

### Source defect and event ownership

At parent `60cd0e21fd5f8d08f19248198780efc5cf12937d`, the primary Browse input cleared every nonempty Escape, including `defaultPrevented`, `isComposing` and legacy `keyCode == 229` events. Three baseline cases at PID56742 reproduce the authored defect: the query becomes empty, its URL field disappears and `replaceState` runs even when another interaction owns that key.

GMI's only authored Browse Escape branch is this input handler. Its dialog has native `showModal`/close cleanup, no second Escape or cancel controller. The GMI document shortcuts handle slash. Separately, the exact shared `theme.js` blob `21a1fb1627ac34badc6078cff486f98486e9b773` contains document-bubble Escape handlers for navigation/settings; several do not inspect composition or consumed-event flags. Therefore simply returning would still allow a guarded key to reach those handlers. The shared-shell source remains unchanged.

The paired GMI JS change stays in the existing input handler:

1. Non-Escape keys return unchanged.
2. Escape already consumed, composing or carrying code229 stops propagation and returns. It does not clear, invoke `updateFilters` or add `preventDefault`.
3. Ordinary nonempty Escape keeps the existing preventDefault, stopPropagation, query clear and `updateFilters` call.
4. Ordinary empty Escape remains available to the browser and the existing dialog close/focus lifecycle.

Stopping propagation is not default-action cancellation. [UI Events composition guidance](https://www.w3.org/TR/uievents/#events-composition-key-events) allows the exiting key to remain composing, and canceling keydown can suppress composition events. [HTML close requests](https://html.spec.whatwg.org/multipage/interaction.html#close-requests) separately depend on whether the relevant keydown was canceled. The guard leaves the input method's default intact; it does not claim to control every native IME/browser combination.

No composition state, delay, dialog cancel blocker, ignore-next-close flag, new clear control, history owner or shared-shell change is added. The ordinary clear path preserves category, scope, evidence, lens and selected answer through the incumbent update owner.

### Focused actual-browser proof

Final PID **57258**, exit0, **6 named cases / 6 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, **13.24 s**. Cases cover EN/ZH at 1440, 390 and 320 px; EN390/ZH320 use dark mode and 320 px cases use reduced motion. All use the actual generated research main content, paired product JS and shared theme/GMI CSS.

- **36 synthetic guarded events** exercise composing, code229 and already-consumed Escape on both nonempty and empty input. Query, selection range, URL/history, category/scope/evidence/lens, visible result IDs, selected title, answer/input node identity, focus and dialog state remain exact. A document bubble observer receives none. The guard leaves each event's existing default-prevention flag unchanged.
- **12 trusted already-consumed Escape keys** use a capture listener that prevents the real key before the production input bubble handler. Both nonempty and empty states stay exact. These are actual browser key presses, distinct from the synthetic composition checks.
- Ordinary nonempty Escape clears the query exactly once through `replaceState`, with no history growth or cancel/close event. Other filters and the selected answer remain. The EN fixture expands from three HBM-related results to ten category/core results; ZH retains the active evidence filter.
- The next ordinary empty Escape on mobile produces native **cancel → close**, reparents Browse home once and focuses the existing opener. Desktop empty Escape passes through without extra writes.
- A one-use test-only cancel listener independently prevents one native dismissal. Browse remains in the modal. The next Escape dismisses normally after that listener is gone, proving no retained suppression state.
- The two final mobile captures were inspected; the focused field, selected text, filters and resulting rows remain legible at EN390/ZH320.

The composition cases are **authored-event contract proof, not native OS IME proof**. Synthetic events do not establish native dialog dismissal behavior. The trusted ordinary/consumed cases and native cancel observations are recorded separately. No blanket cancellation policy was introduced to make synthetic tests pass.

The source pair is Git blob **d7d9107dbb08c8098ea8be168a4378aef30c0338**, SHA256 **e3d444b31192b272eca62d1e97e671b074f1acfac0a6ffdbc399c9669e459373**. All seven generated HTML pages and CSS remain byte-exact to the preceding accepted source; no renderer/model regeneration is needed for this paired-JS-only product change. All **92 existing verifier function definitions**, keyed by lexical path/occurrence, remain AST-exact. One new test function and two nested helpers are added and six canonical cases registered.

[PRIMARY_ESCAPE_VALIDATION_20261109.json](PRIMARY_ESCAPE_VALIDATION_20261109.json) retains input/source hashes, the three expected baseline failures, final cases, commands and limits. The isolated `verify_primary_escape_component.py` harness extracts the canonical test definition and owns no product behavior. It excludes shared-shell/font runtime and external requests; the document bubble probe establishes propagation, not full-shell acceptance.

### Paper guidance and correct builder destination

Existing Build module11, **Clear the search; keep the research**, body `7YQ-0`, gains the primary-input contract. Its old tree/index paragraph now explicitly says those actions do not clear primary Browse filters. This avoids conflating separately owned controls. No additional module or duplicate product specimen is created; Build remains 18 modules.

A native parent read confirms that current Build root **7M9-0 belongs to p-7-0**, alongside the receipt specimens. Page **p-6-0** contains the earlier preservation reference root **73U-0**. The immediately preceding PR/README Build link pointed to that reference page, so it is corrected to the current guide.

Paper navigation is now **Build · Interaction & receipts** (`p-7-0`) and **Reference · Preservation rules** (`p-6-0`). The reference remains available and its content is preserved; only page names/icons change. This clarifies where future builders find current interaction contracts without archiving useful rules. Current source/proof references are updated in place.

Original model01 `EFFECT_UNKNOWN/ROOT_UNVERIFIED` and all release holds remain. These checks do not establish native OS IME interaction, full shared shell/fonts, spoken assistive technology, live account/admission, current hosted CI, deployment or public release. The existing Draft stays unmerged.


## 11.35 · Recover Browse focus before results disappear — 9 Nov 2026

### Defect and the existing projection owner

At parent `2b2ab6615039e2e4172a0d0a713eae50fc237c1e`, primary Browse assigns result-row and empty/results visibility while the disappearing subtree can still own focus. Four actual-browser baseline cases reproduce this at the mutation itself: Back from a focused result into no matches, Forward from the focused no-match Clear all filters action into results, a positive-to-positive filter change hiding the focused row, and clicking Clear all filters. A later focus call does not undo that ordering defect.

The existing `filters()` owner now computes the complete visible-row projection and the retiring rows/region before applying any visibility changes. It recovers only focus inside a retiring subtree. Search remains the first choice. An open native Browse dialog can fall back to its Done button; the sidebar can use a reachable Browse opener or the selected topic heading. Each candidate must still be connected, enabled, visible, outside hidden/inert ancestors and outside every retiring subtree. The bounded loop inspects actual activeElement after focus: a listener redirect to a surviving control is respected; a redirect into another retiring row continues to the next valid destination.

A local monotonically increasing filter-pass number protects synchronous reentrancy. If a focus listener starts a newer filter update, the older pass returns before applying stale rows, counts, notice or region visibility. This is a local projection guard, not an additional query, history, queue or dialog owner. Hidden values are written only when they change. Existing category/scope/evidence controls, selection, count wording and roving row entry remain under the same owner.

The existing Reset handler now writes its cleared-filter URL and chooses its established destination **before** calling `filters()`: the answer-side recovery action goes to the topic heading; sidebar/drawer Reset goes to search. There is no second focus assignment after filters, so a surviving intentional focus redirect is not overwritten. Reset still retains the selected topic, lens and qualified return, and does not rerender the answer: source-card nodes and open receipts remain exact. History restoration itself still uses its existing answer-render path; the proof does not claim source-node identity across history.

### Browser proof at the hide boundary

Final PID **17601**, exit0, **28 cases / 30 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, **52.14 s**. The test wraps the actual hidden-property setter and inspects focus before the mutation. All **94 retained probe snapshots** contain **zero owned hides**.

- Eight history cases cover EN/ZH at 1440, 390 and 320 px plus the actual 820/821 px layout boundary. Real Back/Forward restores positive, no-match and different-positive result sets. Surviving row/control focus is retained; unrelated focus is not pulled into search. Restoration adds no product history writes and retains qualified navigation fields.
- Four Reset cases use pointer click, Enter and Space on the no-match action; they retain selected research, exact evidence nodes and open receipts while clearing only the established full filter set. An intentional search-focus redirect to Category survives. The answer-side action retains its heading destination.
- Four edge cases cover focus redirected to a surviving control, focus redirected into another retiring row, an unavailable search target and a nested input/filter update. The nested newer projection wins and produces its one legitimate replaceState.
- Two closed-mobile cases retain opener/heading/brand focus without focusing the inaccessible search field or opening the drawer.
- Two existing answer-filter recovery cases use two contexts each to retain asynchronous copy resolve/reject, manual fallback and exact source/receipt behavior.
- Eight existing primary Escape cases retain the accepted event/native-dismissal contract, including the newly exercised 820/821 px boundary.

The prior primary-Escape helper's unused intermediate-width predicate is corrected from 900 to the actual CSS breakpoint, **820 px**. Of **95 prior qualified verifier definitions**, 94 remain AST-exact and that one outer definition changes only by this threshold. After accounting for the threshold, every prior definition is AST-exact. Six top-level helpers and four nested helpers are added. This is a test-boundary correction; no product breakpoint changes.

The paired JS is blob **4f207215835bdfe41cada91f496d1c8956898b25**, SHA256 **f6ec608f73ac9e2478e67174a2981bc5a7b90ce9451f762561c1e9fa2e175648**. Only the two exact filter/reset blocks change in product JS. All seven HTML pages and CSS remain byte-exact; renderer and model inputs are not regenerated. Two final EN390/ZH320 captures were inspected.

[BROWSE_FOCUS_VALIDATION_20261109.json](BROWSE_FOCUS_VALIDATION_20261109.json) binds the four expected baseline failures, final 28 cases, input/output hashes, commands, source comparison and limits. `verify_browse_focus_component.py` extracts the canonical helpers and runs the actual product main/CSS/JS in isolated anonymous browser contexts.

### Builder guidance and delivery boundary

Extend existing Build module08 (`7NL-0`) with primary Browse's projection-before-hide, modal reachability, actual-focus and reentrant-pass contract. Extend module10 (`7SS-0`) with Reset's focus-before-filter ordering and the absence of a second focus assignment. Keep the existing eighteen modules and their source-bound proof module; no duplicate controller or explanatory product paragraph is added.

The source remains in Draft PR10676 with original model01 `EFFECT_UNKNOWN/ROOT_UNVERIFIED` and all release holds unchanged. This component proof does not establish native OS IME, spoken assistive-technology output, full shared-shell/font runtime, live account/admission, current hosted CI or deployment. No held model result, independent lane, protected original style or production release is changed.


## 11.36 · A visible query-only Clear action in primary Browse — 9 Nov 2026

### User-visible change and ownership

Primary Browse previously offered the browser's small cancel icon alongside a slash hint. Its visible Reset action clears the full filter set, so it is not a substitute for an easy query-only action. The primary field now uses the accepted **44 × 44 px** clear treatment with the accessible name **Clear search / 清空搜索**. The slash hint gives up that same trailing slot while the raw input is nonempty. Whitespace counts as nonempty even when the matcher normalizes it to an empty query. No explanatory paragraph is added to the product.

The new native button delegates once to the existing primary `updateFilters()` owner. It clears only `q`, preserving the selected topic, category, Core/Extended scope, evidence-only state, lens, qualified return and unrelated fragment fields. The open drawer, answer/source-card nodes and open receipts remain. An empty stale/programmatic activation is inert. The separate Reset and Clear all filters actions retain their existing broader contract.

Clearing the query does not guarantee a result. If other filters still exclude every topic, the existing no-match state and Clear all filters action remain available. In the checked ZH HBM fixture, query clearing retains Semiconductors & hardware + Core + company evidence and still shows **1** topic. Full Reset shows **371** topics. In the EN category/Core fixture, clearing HBM expands **3 → 10** results.

### Implementation details a builder must preserve

1. The source button starts hidden. Bind its click action before adding the enhancement class. No-JS and failed-payload paths keep the custom control hidden and unenhanced.
2. The field wrapper becomes a plain `div`; the input retains its bilingual aria-label/data-aria attributes. [HTML's label content model](https://html.spec.whatwg.org/multipage/forms.html#the-label-element) does not permit a second labelable descendant besides the labeled control. The button therefore is not nested inside the former input label.
3. Reuse the existing clear-button styles. Two scoped primary rules retain the 58 px suffix allowance despite the later primary padding shorthand and suppress the browser cancel icon only while this primary field is enhanced. The editable input area ends before the 44 px target.
4. Include the button in `filters()`'s existing next-visibility and retiring-subtree projection. History restoring `q` to empty must release its focus before hiding it; a query-to-query update retains the same focused button. Do not introduce a separate post-render visibility helper.
5. On explicit activation, capture the current filter pass and URL, focus search with preventScroll, then yield if either changed during a focus callback. Otherwise empty the input and invoke `updateFilters()` once. This protects both synchronous nested filtering and asynchronous hash restoration begun by the callback. Preserve a redirect to a surviving control; do not focus a second time.
6. The accepted primary Escape handler stays byte-exact, including consumed/composing/code229 guards and native empty-query dismissal. No composition listener/state, pointerdown cancellation, timer, additional observer or query/history owner is added.

### Render and browser evidence

The isolated root is `/Volumes/Mastermind/agent-workspaces/verify/gmi-primary-clear-20261109-hzhiwlz2`. Its **48 pinned source inputs** and unchanged accepted-model SHA256 `e644fa48a2bb6e6affe8d1fda74556d9db5f82acadffdad839e1efe8f095359f` reproduce all **nine parent outputs byte-exactly** before patching. The candidate renderer changes only `gmi.html`, `gmi.css` and `gmi.js`; all six other HTML pages remain exact. Within generated Explorer HTML, only the primary field region changes. No model/renderer code or new public fact is introduced.

| Candidate source | Git blob |
|---|---|
| Paired JS | `da28f4622372c072225b140cf59d61385570b364` |
| Paired CSS | `fcfa6cf06646f0406ca366d5f015205c72176bce` |
| Map template | `77b4e3ffdaeafbb60914639ee3018f1c483fb00e` |
| Generated Explorer | `a7fcc7db25acbe1cf85dbf63807bbceedc3b4a8a` |

Final PID **65978**, exit0, **30 cases / 34 fresh anonymous contexts**, Chrome **157.0.8103.39**, zero page errors, **60.72 s**. All **142 retained before-hide snapshots** contain **zero owned hides**.

- Eight control cases exercise EN/ZH1440/390/320 and actual820/821 boundary widths. Pointer, Enter and Space clear only the query with one replaceState and no history growth. Exact source-card identity/open receipts, selected research and other filters remain.
- Whitespace visibility, stale empty activation, retained zero-result filters and full Reset are checked separately. Geometry proves a 44 px square and no input/target overlap. The localized names and exclusive clear/slash slot are checked.
- Four history cases cover actual Back/Forward, nonempty-to-nonempty button focus, locale/theme changes and closed mobile state.
- Four edge cases cover a surviving focus redirect, nested new query, hash restoration started by focus, reentrant history projection and redirection into another retiring action.
- Two unenhanced cases use four contexts for no-JS and malformed payload in EN/ZH; the button remains hidden, no enhancement class appears, native theme links/source recovery remain.
- Six primary Escape, four existing Browse focus and two answer-recovery cases retain the accepted keyboard/native-dialog, filter focus, pending copy/fallback and receipt contracts. The two answer cases use four contexts.
- Five final native captures were inspected: EN390/ZH320 query states, both query-cleared states, and ZH320 full Reset.

The two baseline cases confirm the missing custom action at the parent; they are expected absence checks, not additional event/focus defects. All **105 prior qualified verifier definitions remain AST-exact**; six new top-level helpers and their canonical registrations are added. The isolated harness extracts the real definitions and owns no product behavior.

[PRIMARY_CLEAR_VALIDATION_20261109.json](PRIMARY_CLEAR_VALIDATION_20261109.json) retains input/source/render hashes, commands, all case results, full new clear observations, screenshot hashes and limits. Repeated earlier-regression detailed snapshots remain in the exact hashed native report; their test definitions and every result row are retained. The focused export is a declared projection, not a claim that omitted snapshots were newly canonicalized.

### Editable Paper workflow and boundaries

[Browse · Search and filters](https://app.paper.design/file/01M5H6EARN9YHQV17JC6ZG9BRY/p-D-0) adds one editable group **A1F-0**: Q01 EN390 Noir (**A1N-0**) and Q02 ZH320 Day (**A3E-0**) use truthful 844 px viewports; Q03 query-cleared (**A53-0**) and Q04 Reset (**A66-0**) show the same ZH fixture's different filter/count outcomes. The existing product's original phone seeds remain untouched. The comparison uses actual controls and counts outside product chrome, with no extra in-product explanatory text.

Extend existing Build module11 body **7YQ-0** with raw-value visibility, query-only ownership, pre-hide projection and focus-callback guards. Keep the eighteen-module guide. The new Browse page follows the current-product page; existing workflow/reference/history pages keep their relative order.

A transient DESKTOP_BUSY preflight sent no Paper call and no mutation. A same-carrier read-only inspection subsequently proved CONNECTED with the same file and a fresh snapshot; only then was the never-issued page operation applied. No active writer was interrupted, no lock was cleared and no alternate carrier was used.

PR10676 remains Draft with original model01 `EFFECT_UNKNOWN/ROOT_UNVERIFIED` and all release holds. Component proof excludes full shared shell/fonts, spoken AT, native OS IME, live account/admission, hosted current-head CI and deployment. This action adds no source-emission authority or release acceptance.
