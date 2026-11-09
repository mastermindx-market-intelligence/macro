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
