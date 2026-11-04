# F01 revised native captures — independent first-pass design advisory

## Advisory verdict

**Recommend three narrow revisions before treating these six captures as visually settled:** clarify the financial table's monetary units on C, visibly identify the originating Options row on D, and make the similar tool destinations on F distinguishable by their purpose. The first two are observable presentation defects. The third is a comprehension risk inferred from the visible copy and requires a small task test to confirm its practical severity. F also contains one low-priority line of implementation-oriented copy.

No P0 or P1 visual defect was observed in the six inspected frames. The core hierarchy is strong, the desktop workspaces retain substantial depth, the Chinese mobile table fits its capture, and the compact rail has a convincing visible focus example. This is a bounded design advisory. It does not establish formal review, owner concurrence, design acceptance, working interactions, or acceptance of boards outside this set.

## Evidence identity and review boundary

- **Containing immutable Macro commit:** `be157007c4d4a33feb576a43f431eba3db5650ac`.
- **Neutral brief:** [REVIEW_INPUT.md at that commit](https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/REVIEW_INPUT.md).
- **Paper file:** `01M2WGNCX9475G79JRKJTCM08P`; **page:** `p-27-0`.
- **Protected law pin reused:** Mastermind `9f65957e29eba92245d78609f032aaea523b7cb4`, compatible INDEX 1.0.1 / bootstrap major 1.
- **Input directory:** `/workspace/scratch/43a778472c23/f01-drafts/evidence/native_revision_20261103`.
- **Member aggregate SHA256:** `8465612640379507ac49a88fa6d3b3618736d7f8c586db45b4682b9905d584bc`.
- **Neutral brief SHA256:** `90ad8125abdd24d1ebe51cc3cdffca67b75c2fdd9604d2a494cc9ae6e6ce7c98`.

I visually inspected all six JPEGs using `view_image` and corroborated relevant geometry, wording, and node identities from the paired JSX. All twelve member hashes and byte counts, the aggregate, and the brief hash matched. I read the applicable Paper workflow and Mastermind review guidance, but kept this first pass within the explicitly frozen artifact boundary. I did not inspect live Paper, earlier critiques, author rationale, other F01 source files, or implementation. No Paper, GitHub, or production write was made. No worker was launched. Native reasoning here is advisory; no automated admission or Pro execution receipt is claimed.

The screenshots are actual Paper captures. Their dimensions describe artboards, not verified browser viewports. JSX establishes native structure and declared dimensions; it does not establish DOM semantics, hit areas, accessible names, tab order, or browser behavior. Illustrative financial values are treated solely as design content.

| Board | Exact artboard | Capture | Main task |
|---|---|---|---|
| A | `6ZY9-0` | 1440 × 960, dark EN | Understand workspace, compare participation, inspect sources, retain history |
| C | `6ZYB-0` | 1280 × 1180, light EN | Find financial period and measure, inspect selected value, retain table context |
| D | `6ZYC-0` | 1024 × 960, dark EN | Inspect an Options print and retain its originating context |
| E | `6ZYD-0` | 390 × 1140, light ZH | Perform the market-participation task in Chinese on a narrow surface |
| F | `6ZZV-0` | 320 × 960, dark EN | Distinguish similarly named tools and select an exact destination |
| H | `70WJ-0` | 1280 × 960, dark EN | Use the market workspace with compact navigation |

All artifact citations below refer to the corresponding `.jpg` and `.jsx` pair in the bound immutable input directory. Node references identify the smallest observed target or its immediate native container.

## Findings and smallest useful repairs

Severity here means impact on the stated design task: P1 would obstruct a core task or create a serious misinterpretation; P2 is a material clarity or context defect; P3 is a local polish issue. An interaction proof gap is not automatically a visual failure.

### T1 — C: the statement table does not state its monetary scale locally

**P2 — observed omission, with an interpretation risk.** Exact targets: board `6ZYB-0`; table `70G7-0`, heading `70G9-0`, Revenue row `70GM-0`, Operating income label `70GV-0`; selected cell `72A2-0`.

The revenue chart states “Illustrative · USD bn · FY2024 selected” at `70FV-0`, and the open evidence panel states “USD 61.0 bn” at `70EB-0`. The table itself is headed “Income statement · selected rows” and displays four monetary rows without a local currency/scale statement. Diluted EPS explicitly says USD. A reader must carry the chart's units into a different component, or infer the scope of the evidence panel's selected Revenue unit. That is avoidable ambiguity in a financial comparison surface. The issue is the scope of the label, not whether the illustrative arithmetic is correct. [C.jpg; C.jsx, nodes cited above.]

**Smallest repair:** add a compact table-level line such as “USD bn, except diluted EPS (USD per share)” if that accurately describes all supplied rows. Keep the chart caption and the evidence value explicit. Do not repeat the unit in every cell or enlarge the table substantially.

**Falsifier / closure evidence:** in the revised table, a reader can identify the units for an unselected monetary row and EPS without consulting the chart or opening evidence. If the monetary rows intentionally use different scales, label those row units instead. A simple task asking for the unit of Operating income and Diluted EPS would resolve the remaining comprehension question.

### T2 — D: the source row is present but not visibly selected while evidence is open

**P2 — observed presentation defect.** Exact targets: board `6ZYC-0`; originating row `724R-0`, timestamp `724T-0`, ticker `724V-0`; scrim `70JO-0`; evidence drawer `70JQ-0`; return statement `70LX-0`.

The drawer identifies NVDA at 15:58:12 and says the selected print, filters, and horizontal position stay in place. The background row carrying that timestamp and ticker has no visible selected treatment. Its JSX defines a 48px row with a bottom border but no selected fill or selection border. The full-canvas black scrim is `#0000009E`, approximately 62% opacity, and the 440px drawer starts at x=584. Together they make the background context deliberately subordinate, but the remaining visible row does not explain which item originated the panel. The copy promises contextual continuity more clearly than the image communicates it. [D.jpg; D.jsx, `724R-0`, `70JO-0`, `70JQ-0`, `70LX-0`.]

**Smallest repair:** persist an obvious selection cue on `724R-0`, preferably a restrained fill plus a leading rule or selected marker that remains distinguishable through the scrim. Preserve the modal's visual separation. Change scrim opacity only if the selected cue remains too weak; globally brightening all background content could undermine focus on the evidence.

**Falsifier / closure evidence:** in an equivalent drawer-open screenshot, someone can point to the originating row without reading the return sentence. Actual close behavior must separately demonstrate restored filters, horizontal position, selected row, and focus. A stronger screenshot cannot prove those behaviors. The deliberately covered local tabs are not classified as a clipping defect.

### T3 — F: similar Options destinations are differentiated principally by route strings

**P2 — comprehension risk inferred from visible copy, not proven navigation failure.** Exact targets: board `6ZZV-0`; rows `70PQ-0`, `70PV-0`, `70Q0-0`; descriptions `70PS-0`, `70PX-0`, `70Q2-0`; route labels `70PT-0`, `70PY-0`, `70Q3-0`.

“Options / Research workspace / /options” and “Options & market structure / United States · Market research / /options.html” sound close in purpose. “Specialist destination” adds little meaning to Options Screener. The routes make the destinations technically distinct, but they do not explain which tool fulfills a user's next task. The four large result rows provide sufficient room to carry a useful distinction, so this is primarily a wording problem. [F.jpg; F.jsx, nodes above.]

**Smallest repair:** replace the generic descriptions with one concise task or outcome for each destination, using the actual destination's verified function. Retain route strings as secondary diagnostic information if they are valuable to the intended users. Do not invent route behavior from its name, and do not hide a powerful destination merely to make the list shorter. The parent owner should supply the accurate functional distinction after this blind report is frozen.

**Falsifier / closure evidence:** give intended users two concrete Options tasks and ask them to choose a destination without opening it. If they consistently choose correctly from the current wording, this concern can be downgraded. Otherwise revise the descriptions and repeat the same small discrimination task. Route execution, deep-link handling, search ranking, and keyboard selection remain implementation proof questions.

### T4 — F: one result-summary line exposes internal preservation language

**P3 — observed copy issue.** Exact target: board `6ZZV-0`, `70OU-0`: “4 destinations · exact routes retained.”

“Exact routes retained” explains a construction constraint rather than helping a person choose a tool. It also consumes scarce width at 320px. [F.jpg; F.jsx, `70OU-0`.]

**Smallest repair:** use “4 destinations” or another plain result count. **Falsifier:** retain the phrase only if a documented user task specifically depends on knowing that a migration preserved exact routes and the wording is understood by those users.

## Board-level assessment

| Board | What the capture establishes well | What remains unestablished |
|---|---|---|
| A | Workspace and country context are visible; the question headline leads; KPIs separate level, change, and coverage; numeric labels accompany bars; signed changes avoid relying only on color; Current, Drivers, and History retain depth. | Source opening and return, the expanded/compact switch, country changes, full-sector ordering, and history behavior are unproved. |
| C | Selected FY2024 chart, selected Revenue cell, and evidence value form a readable relationship. The 664px table area and 320px evidence panel preserve comparison. Deep financial views, annual/quarterly controls, periods, and transcript availability remain visible. | Correct period switching, table scrolling, focus restoration, chart accessibility, source retrieval, and behavior with real filing evidence are unproved. T1 is visible in the current table. |
| D | The evidence panel gives contract identity, premium, inferred side, time, DTE, missing fields, freshness, and source limitations. It clearly separates inference from intent and preserves local research choices behind the modal. | Origin-row selection is visually weak as described in T2. Closing, Escape, focus containment/restoration, and actual filter/scroll preservation are unproved. |
| E | Chinese title and task copy are legible; five named industries fit; rates and signed changes are aligned; the source date and history gap are stated; source and history paths remain visible. | Browser scrolling, text scaling, source-sheet behavior, history return, localization outside this frame, and the complete 11-industry set are unproved. |
| F | Large separated results fit 320px; a visible search focus outline, clear action, dismissal, and company-search alternative are present. | Distinguishing close destinations needs the T3 task test. Search submission, clearing, keyboard results, empty results, and route execution are unproved. |
| H | Compact navigation releases horizontal space without reducing the main comparison table. The focused Expand control and tooltip explain the demonstrated rail action. Focus is visibly distinct from the selected navigation item. | Other rail tooltips/names, navigation meaning for new users, collapsed/expanded persistence, and keyboard operation are unproved. Only one tooltip state is shown. |

## Craft, accessibility presentation, and density

### Hierarchy, typography, and spacing

A and H have a disciplined reading sequence: workspace context, the analytical question, freshness, key measurements, then sector comparisons and source actions. The large headline and restrained gold bars give the page an editorial center without hiding numerical work. C is denser and has several navigation levels before the revenue chart. That density is justified by the task's requirement to preserve deeper financial capability. I would not remove financial tabs or period controls to make the screenshot quieter. The useful simplification is clearer local measurement context, as in T1. [A.jpg; H.jpg; C.jpg/C.jsx, `70FS-0`, `70G7-0`, `70E5-0`.]

C's selected cell is declared 100 × 44px and has a neutral fill and outline. Its evidence amount is 28/34px, with 14/22px explanatory copy and smaller metadata; the distinction between value, explanation, and provenance is readable. D similarly gives the contract and premium priority while retaining source limitations. No title/body overlap or visibly cut text was apparent in the six images at their captured dimensions. That observation does not establish reflow at other sizes. [C.jsx, `72A2-0`, `70EB-0`, `70EC-0`; D.jpg/D.jsx.]

### Selection, focus, and semantic color

Selection is credible in A's navigation (`700O-0`), C's value (`72A2-0`), and H's compact rail (`70ZZ-0`). F's search outline and H's Expand outline present focus clearly. D is the exception because the selected print is asserted but not visually marked. Positive and negative market changes also have explicit signs, which improves comprehension without requiring color discrimination. [A.jpg/A.jsx; C.jpg/C.jsx; D.jpg/D.jsx; F.jpg; H.jpg/H.jsx.]

The captures are insufficient for a contrast-conformance claim: native tokens are not all resolved to actual browser colors, and JPEG pixels do not establish every text/background/focus combination in implementation. The quieter 12–13px metadata deserves actual-browser contrast and text-scale checks, especially when it carries freshness or source limitations. This is missing verification, not a claim that those labels fail.

### Chinese readability and touch presentation

E preserves the same analytical question in idiomatic, readable Chinese without forcing the desktop bars into the narrow table. The two-line change header clarifies percentage points, and the positive/negative values stay compact. At this capture size the longer industry label fits and the date is readable. “市场参与面” is a vocabulary choice, not an observed defect; only domain-user testing would justify changing it. [E.jpg/E.jsx.]

The small-looking “查看” label must not be mistaken for a small native control: its wrapper `72BP-0` is explicitly 44 × 44px, inside a row with minimum height 52px (`70OW-0`). The second inspected row uses the same 44 × 44px pattern (`72BS-0`). C's close affordances and D's close affordances likewise declare 44px dimensions. These are good design dimensions; actual hit testing is still owed when built. F's result rows declare a minimum 104px height, giving generous touch separation. [E.jsx, nodes above; C.jsx, `70E8-0`, `729R-0`; D.jsx, `70JT-0`, `70LY-0`; F.jsx, `70PQ-0`, `70PV-0`.]

### Source, return, and context comprehension

The explicit illustrative labels, source dates, partial coverage, missing filing, absent source citation, and closed market session are valuable. They prevent the polished presentation from implying a live or fully evidenced observation. C's selected value remains visible beside its panel, which is the strongest source-context relationship in this set. D's return sentence is unusually specific but needs the visible row cue and eventual behavioral proof. [A.jpg; C.jpg/C.jsx, `70EA-0`–`70EI-0`; D.jpg/D.jsx, `70LW-0`, `70LX-0`; E.jpg.]

A's “Inspect source ↗” at `703P-0` may suggest an external link or new window. If the intended action opens an internal evidence panel, a panel/detail affordance would be a better match. This is a low-priority affordance inference: the capture does not reveal the actual destination, so it is not a confirmed mismatch. A task test or the verified interaction design can falsify it.

## Missing state evidence, not inferred failure

The set supplies useful examples of selection, search/navigation focus, partial coverage, historical observation dates, absent source evidence, and market-session/transport distinction. It does not supply a complete loading, empty, recoverable-error, permission, success-feedback, reduced-motion, or keyboard sequence. Those omissions cannot be turned into findings about implementation. They also cannot be silently counted as passing states.

The smallest later proof set should follow the actual tasks: open and close evidence from C and D; preserve selection/filter/scroll context; select each ambiguous F destination; switch A/H navigation while retaining the workspace; and complete E's source/history flow with Chinese text scaling. These are later owner/prototype or browser checks, not work performed by this advisory.

Optional preferences are explicitly non-blocking: C's small revenue chart could add a minimal vertical-scale cue if quantitative chart reading is expected, but the adjacent table already supplies exact values; E's domain vocabulary can be tested with Chinese users; compact-rail icon familiarity should be assessed without assuming that hidden text in JSX proves an accessible name. None warrants removing advanced task paths.

## Scope conclusion

The six frames provide a credible visual direction with focused remaining repairs. Preserve the existing analytical hierarchy, financial and Options subviews, source limitations, history access, mobile numerical comparison, and generous declared touch areas. Address the three P2 items with the smallest changes above, then collect only the missing proof relevant to the implemented tasks.

**Outcome classification: PROVEN_OUTCOME for this bounded artifact review and its integrity checks only.** The input manifest's separate effect uncertainties remain outside this review and are not cleared by it. No live-design, implementation, formal acceptance, or production outcome is asserted.

## Integrity appendix

All twelve rows below were checked against the local frozen bytes; each byte count and SHA256 matched the supplied manifest. Aggregate recomputation used sorted `path + NUL + member SHA256 + newline`, exactly as the manifest defines. The JPEGs were inspected visually in their original form; no transformed image was substituted for an input.

| Member | Artboard | Bytes | SHA256 | Result |
|---|---|---:|---|---|
| `A.jpg` | `6ZY9-0` | 123859 | `f9566d05145b05bb1611c62c499eed19222153c1aecdf47b6177ec0765e51904` | PASS |
| `A.jsx` | `6ZY9-0` | 35541 | `40b681e539af78d90403e9090865a84ab50e04b14c2e42ee72b3ead13e91a15f` | PASS |
| `C.jpg` | `6ZYB-0` | 140091 | `7990201eecb765492fd731b320164e2b806833802f46f22c91a9f00550fadd12` | PASS |
| `C.jsx` | `6ZYB-0` | 41969 | `5abd4b4f48360c699b587b5dee3a7d654aa9b7d8a74e169f5b7b8a16a66f8251` | PASS |
| `D.jpg` | `6ZYC-0` | 105876 | `ccb8b0dbedfe280cfed262af4e01f13ac30a98841e26f9da3dca26ee487f2e53` | PASS |
| `D.jsx` | `6ZYC-0` | 60396 | `18712d1739f137edf98bb26de28394798736b82f7f2ff6b0a1334c2565f44035` | PASS |
| `E.jpg` | `6ZYD-0` | 55429 | `05cc4c09682062a6ac1277c851385364cd8ec01f1fa11f0d8d092eba1dfa8a15` | PASS |
| `E.jsx` | `6ZYD-0` | 20911 | `ff966235e3bddb9bcfd9f139a5b0927b2ae8f5d8cb010ccb42470e609f1a1b7c` | PASS |
| `F.jpg` | `6ZZV-0` | 37625 | `a60511e2d97da7326aa4f68d4fe7c0671122b7685fc08924512844275dd18f89` | PASS |
| `F.jsx` | `6ZZV-0` | 11504 | `f18200ef593b20961250f710e1a5655f5753a126704794fb77ff0166708c6129` | PASS |
| `H.jpg` | `70WJ-0` | 109406 | `24cbbb8221b02027c1d284af7c5fe6cfa0c91dcad12d0b1c06e7b9b1b7da3d22` | PASS |
| `H.jsx` | `70WJ-0` | 37850 | `b7d5e4400cd19d62e7e0bfc4df5828b08cd37d20b04f3ca748e8d8294a0577d3` | PASS |

**Aggregate:** `8465612640379507ac49a88fa6d3b3618736d7f8c586db45b4682b9905d584bc` — PASS.

**Neutral brief:** `90ad8125abdd24d1ebe51cc3cdffca67b75c2fdd9604d2a494cc9ae6e6ce7c98` — PASS.
