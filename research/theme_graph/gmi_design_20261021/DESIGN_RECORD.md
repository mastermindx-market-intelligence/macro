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
