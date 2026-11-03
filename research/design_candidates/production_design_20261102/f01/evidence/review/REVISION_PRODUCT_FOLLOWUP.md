# F01 — product advisory follow-up on C / D / F

Date: 2026-11-03  
Review type: bounded post-first-pass artifact advisory; native reasoning.  
Disposition: **The three exact P2 concerns from my first report are repaired in these static artifacts.** The additional internal-copy check requested by the follow-up brief is also satisfied in the visible F capture. I observed no new defect in the supplied three-board revision. This does not establish working interactions, successful user task tests, complete design coverage, formal qualification, or design acceptance.

## Scope and provenance

This follow-up inspected only `REVIEW_INPUT.md`, `CAPTURE_MANIFEST.json`, and the C/D/F JPEG/JSX pairs in `evidence/native_followup_20261103/`. I viewed all three actual images and corroborated the changed text, nodes, and geometry in JSX. I verified all six member SHA256 hashes, byte counts, and Git blob SHA1 values against the manifest, then independently recomputed the six-member aggregate. All matched.

The parent supplied immutable containing Macro commit **`8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177`** and reported publication plus manifest readback. My verification is of the local frozen bytes; I did not independently fetch GitHub or operate Paper, a browser, or production in this follow-up.

[Immutable follow-up input directory](https://github.com/mastermindx-market-intelligence/macro/tree/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103)

| Binding | Value |
|---|---|
| Paper file | `01M2WGNCX9475G79JRKJTCM08P` |
| Page | `p-27-0` |
| C | `6ZYB-0`, 1280 × 1180, light EN |
| D | `6ZYC-0`, 1024 × 960, dark EN |
| F | `6ZZV-0`, 320 × 960, dark EN |
| Original six-board input | `be157007c4d4a33feb576a43f431eba3db5650ac` |
| Product first-report publication, supplied by parent | `4dfcfde749d1c8566546224da5e9715de1d2b249` |
| Taste first-report publication, supplied by parent | `0d558e74ff16912e431772688d9c79f2a71ad44c` |
| Reused procedure pin | Mastermind `9f65957e29eba92245d78609f032aaea523b7cb4`, INDEX 1.0.1 / bootstrap 1 |

My first report remains unchanged. This report is a separate follow-up after the four corrections described in the supplied brief. I did not read changing general source, author rationale, or the other reviewer's report. No automated Pro/admission receipt, formal-reviewer status, or broader source qualification is claimed.

## Disposition of the three P2 findings

### C — financial units are now local to the table

**Classification: observed repair; static finding resolved.**

On C (`6ZYB-0`), table-heading node **`70G9-0`** now places **“USD billions, except diluted EPS (USD/share)”** directly below “Income statement · selected rows.” The screenshot shows the complete sentence above the year headers, so a reader can interpret the table without relying on the chart caption or open Revenue evidence panel. JSX confirms a 12px, 18px-line-height secondary line inside the existing heading, within table card **`70G7-0`**, whose width is 664px. The extra line fits without observed clipping or collision in this capture. [C image][Cjpg] [C JSX][Cjsx]

This supplies the smallest repair requested in the first report. The exception is specific to diluted EPS, and the illustration/source limitations remain visible. The supplied brief attributes the scale and EPS basis to the existing illustrative chart/panel; I did not validate any amount against a filing. Nothing in this disposition converts the values into verified financial data.

**Falsifier / reopening condition:** the rendered table loses this units line, the caption is clipped or detached from the table, or a displayed numeric row uses a different unit without a clear exception. No such issue is observed here. Other responsive layouts remain outside this check.

### D — the origin print is visibly selected while its evidence panel is open

**Classification: observed repair; static finding resolved.**

On D (`6ZYC-0`), the NVDA origin row **`724R-0`** now has `var(--noir-selected)` fill plus 1px top and bottom borders in `#777777`. Its first cell **`724T-0`**, inside **`724S-0`**, displays **“15:58:12”** and a second-line **“Selected”** label. The visible selection therefore has a textual cue as well as a visual treatment. The adjacent NVDA node remains **`724V-0`**. The time and ticker match the open Print evidence panel. [D image][Djpg] [D JSX][Djsx]

The cue occupies the exposed left portion of the 994px-wide, 48px-high row. JSX places the 440px evidence panel **`70JQ-0`** at x=584 on the 1024px board. The screenshot visibly preserves the time, Selected label, and ticker to the panel's left despite the background dimming. Ordinary comparison row **`7267-0`** retains its ordinary bottom border and lacks the selected fill, top border, and Selected label.

This supplies the requested origin-row treatment in the open-panel state. It does **not** establish what happens on close. The existing statement in **`70LX-0`** promises return to NVDA at 15:58:12 with the selected print, filters, and horizontal position retained; neither that statement nor this screenshot proves restoration. Close controls **`70LY-0` / `70LZ-0`** remain visual affordances in this evidence.

**Falsifier / reopening condition:** the selected cue disappears in the rendered open-panel state, marks a different row than the evidence panel, or is obscured so the origin cannot be identified. A separate post-close state and an interaction trace remain needed for the behavioral claims. Their absence is a proof gap, not an observed failure of the repaired marker.

### F — destination captions now explain concrete tasks

**Classification: observed copy repair, with source basis attributed to the supplied brief; static finding resolved.**

On F (`6ZZV-0`), the former generic subtitles are replaced by task descriptions. At 320 × 960, all four cards, their route strings, and the company-search action are visible. The scanner description wraps across two lines without observed clipping or overlap. JSX corroborates 12px description text with 18px line height and flexible card height. [F image][Fjpg] [F JSX][Fjsx]

| Destination title | Description node and displayed copy | Displayed route node and string |
|---|---|---|
| Options, `70PR-0` | `70PS-0`: “Inspect flow, exposure and volatility.” | `70PT-0`: `/options` |
| Options & market structure, `70PW-0` | `70PX-0`: “Read the daily brief, flow and leaders.” | `70PY-0`: `/options.html` |
| Options Screener, `70Q1-0` | `70Q2-0`: “Open the scanner in Options & market structure.” | `70Q3-0`: `/options_screener.html` |
| Futures, `70Q6-0` | `70Q7-0`: “Explore ES/NQ futures by session.” | `70Q8-0`: `/options/futures` |

The descriptions provide a useful reason to choose each entry. The scanner caption explicitly identifies its relationship to Options & market structure, reducing the chance that its separate listing implies a wholly independent workspace. The two flow-related destinations still share a capability, but the additional exposure/volatility versus daily brief/leaders wording distinguishes their emphasis. Remaining uncertainty about whether users choose correctly requires a task test; it is not sufficient evidence to reopen the original generic-caption defect.

The supplied [follow-up brief][brief] attributes these capabilities to D08's SOURCE_MAP at `e89f527e3267b1d1dd27ac7507e9a25983c0c903`, blob `dc7a280598567daefdcb5ea1e5f72ddc0d7daab8`. Its excerpt identifies native Options Flow/Exposure/Volatility, the legacy Daily Brief/Flow/Scanner/Ticker/Leaders set, the screener replacement into `options.html#scanner`, and the separate ES/NQ/session futures grammar. The revised descriptions are consistent with that supplied excerpt. I did not independently reopen D08, verify its current implementation, or execute any route. The route strings in JSX are display content; I do not treat them as tested hrefs.

**Falsifier / reopening condition:** owner evidence contradicts these task descriptions, the implemented entry fails to reach the described destination, or a representative task test shows users systematically choose the wrong entry despite the distinctions. Only the first concern's static copy requirement is closed here.

## Additional internal-copy check requested by the brief

F node **`70OU-0`** now says **“4 destinations.”** This accurately counts the four visible cards. It does not make a route-preservation, migration-completeness, or execution claim. The count fits on one line above the results. This satisfies the requested visible internal-copy check; it is an additional observation, not a retroactive addition to my original three P2 findings. [F image][Fjpg] [F JSX][Fjsx]

## Capability and truthfulness limits retained

The inspected repairs preserve the visible task structure: C still supports reading a financial row alongside its selected Revenue evidence; D still identifies the options print, its inferred side, and source-observation limitations; F still displays four specialist entry points and a company-search escape. The revised captures retain the illustrative-data framing and do not supply new filing or trade-source proof. This is a judgment about what is visible in three states, not a complete feature-preservation audit.

The following evidence remains absent from this follow-up:

- **Behavior:** actual route execution and scanner replacement, source/history transitions, evidence close and focus return, selected-cell/print restoration, filter and horizontal-scroll retention, and export behavior. Static affordances and retention copy do not verify these effects.
- **User task tests:** evidence that representative users interpret the units, identify the selected print, and choose the appropriate options destination without assistance. The designs are more explicit; task success has not been measured.
- **Full coverage:** other widths, keyboard and touch interaction, accessible semantics and contrast qualification, reduced motion, themes and languages beyond these captures, and loading/empty/stale/error/permission/success transitions. No broader matrix is closed by these three screenshots.
- **Other boards and inherited holds:** A/E/H are reported unchanged in the original six-board input and were not re-reviewed here. B/G/Readme/I are outside this follow-up. The manifest reports the original I/grid `EFFECT_UNKNOWN` and Readme `DOCUMENT_CHANGED` holds; I did not reconcile or clear them.

No preference-only refinements are promoted to defects. No new P0, P1, or P2 issue was established within the supplied C/D/F revision. The scoped static repairs can be recorded as verified observations while the missing proof remains open.

## Integrity record

| Member | Bytes | Verified SHA256 |
|---|---:|---|
| C.jpg | 142416 | `fdc42fb5c69891f0b11864ef19aeeced07fc304347e7c7b38099e42aab3f3281` |
| C.jsx | 42140 | `93f2bc32f6e5131eb5417f1de6902d4585c8cb145b6a2b4370db3e6b8ba5e8ee` |
| D.jpg | 106207 | `9889b663690d27c9ebd07a1ccfb21d30b2a9fbb6d86e40ec59a6b6c91bb6a3ba` |
| D.jsx | 60629 | `3e34643a2d64be2ff8dac94186bb6e01a584eabf50c34682c0a6c283b9228200` |
| F.jpg | 38728 | `9fbfe4fd0f3fef87b9c4682ee182621b6ddca1a8ddf5fe01a58899927fd83a64` |
| F.jsx | 11540 | `38efd24e4f7c97387250a5be8cf4b0a6e8d63f03c6f26682ff9f6b8207a33f42` |

Aggregate: **`cc448df630698e66ce8706d79f6ca26307a976967dbda4e7b88a079ef6dc5396`**, computed as SHA256 of sorted member path + NUL + member SHA256 + newline.

Local brief SHA256: `8023d74ac2e03fafd324f4a702685bb37501df2f669d7277c5d42a5bf34ae2c2`.  
Local manifest SHA256: `c4f9eda7c841ffb6a45455391130f3ae4582e7178a7195995a7f44cafd31c9a5`.  
Published manifest blob supplied by parent: `6db267b01f996ab072058b199b343acb26b8e567`.

**Closeout: PROVEN_OUTCOME for this bounded follow-up advisory and report only.** No formal qualification, browser validation, behavioral acceptance, or whole-design acceptance is claimed. Stop after freezing this separate report.

[brief]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/REVIEW_INPUT.md
[Cjpg]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/C.jpg
[Cjsx]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/C.jsx
[Djpg]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/D.jpg
[Djsx]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/D.jsx
[Fjpg]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/F.jpg
[Fjsx]: https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/F.jsx
