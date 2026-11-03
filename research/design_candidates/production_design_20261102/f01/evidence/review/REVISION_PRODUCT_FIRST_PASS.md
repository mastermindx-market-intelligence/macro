# F01 native revision — independent product/UX first pass

## Judgment and scope

The six compositions make their principal tasks understandable. They preserve visible routes to substantial analytical capability, and their treatment of illustrative data, missing observations, source availability, and inferred options direction is generally candid. Three bounded repairs would improve task completion: explain the job served by similarly named destinations, state the financial table’s numeric units locally, and mark the originating options row as selected.

This is a frozen-input product/UX advisory. It is neither a formal reviewer decision nor design acceptance, implementation verification, browser proof, or a claim that the displayed navigation works. In particular, source inspection, history traversal, exact destination routing, and restoration of selection, filters, or horizontal position remain unproved. Their labels make those behaviors legible as intended behavior; these captures do not establish them as actual behavior.

**Evidence boundary.** I inspected all six supplied JPEGs with `view_image` and used the corresponding JSX to corroborate relevant nodes and geometry. I verified all twelve capture member hashes and the neutral brief hash. I did not consult other F01 files, previous reports, or the author’s rationale. No Paper, GitHub, production, or existing source mutation was performed for this advisory.

**Containing input commit:** `be157007c4d4a33feb576a43f431eba3db5650ac`, on the existing F01 Draft #10645, as supplied by the parent after publication and manifest readback. Local byte verification is independent; remote publication/readback is parent-supplied provenance and was not repeated here. The [neutral review brief][brief] and [capture manifest][manifest] define the bounded input.

**Procedure pin:** Mastermind `9f65957e29eba92245d78609f032aaea523b7cb4`, compatible INDEX 1.0.1 / bootstrap 1. Applicable bootstrap, Paper connection/integration, and craft review guidance were used. This is native reasoning advisory; no automated Pro or admission receipt is claimed.

**Paper identity:** file `01M2WGNCX9475G79JRKJTCM08P`, page `p-27-0`. The manifest classifies this set as partial, six changed boards only, and unqualified design evidence. Other manifest effects and untouched targets are outside this review.

## Task coverage across the six boards

| Board and exact ID | Intended task and observed support | Assessment and evidence limit |
| --- | --- | --- |
| A — `6ZY9-0`, 1440×960, dark EN | Understand US market participation; compare the current reading with change and sectors; reach sources and history from expanded navigation. | The question, percentage, percentage-point change, partial-coverage cue, and five-of-eleven disclosure form an understandable sequence. Current/Drivers/History and row source actions preserve deeper access. History and source destinations are not shown. [Image][A-img] · [JSX][A-jsx] |
| H — `70WJ-0`, 1280×960, dark EN | Continue the participation task with compact navigation and return to expanded navigation. | The market content remains recognizable. The compact rail and visible Expand navigation tooltip/focus treatment explain the immediate action. A static compact state does not establish retained view, focus, selection, or scroll across the transition. [Image][H-img] · [JSX][H-jsx] |
| C — `6ZYB-0`, 1280×1180, light EN | Choose a company financial measure/period, inspect the selected value, and return to the financial table while retaining access to deeper research. | Revenue FY2024 and USD61bn are identifiable in the evidence panel, and the matching table value is selected. Broad company/research navigation and statement/period choices remain visible. Table units need local reinforcement; close/return behavior and other metric states are absent. [Image][C-img] · [JSX][C-jsx] |
| D — `6ZYC-0`, 1024×960, dark EN | Inspect an options print, interpret source and inferred direction, then resume the originating row and filters. | The panel identifies NVDA, contract, observation time, and premium; it separates inference from intent and prediction. Tape, local views, specialist destinations, and horizontal fields remain visible. The visible origin row needs a selection cue; return/retention/export behavior is unproved. [Image][D-img] · [JSX][D-jsx] |
| E — `6ZYD-0`, 390×1140, light ZH | Perform the participation task in Chinese on a narrow screen. | Question, current/change values, history gap, source actions, all-eleven action, and history action remain understandable without observed horizontal overflow in this capture. This supports this particular ZH/light/narrow composition, not general localization or responsive coverage. [Image][E-img] · [JSX][E-jsx] |
| F — `6ZZV-0`, 320×960, dark EN | Find the intended options-related destination among similar names. | Four distinct route strings and differentiated titles preserve destination identity at 320px. The first two descriptions mainly identify product areas rather than the user task, so choosing the correct route still requires prior knowledge. Actual navigation is not demonstrated. [Image][F-img] · [JSX][F-jsx] |

## Prioritized actionable findings

Severity here reflects likely interference with the stated task. None of these frozen captures establishes a P0 or P1 failure. P2 findings are focused usability repairs; they do not imply a backend defect.

### P2-01 — Explain why a user would choose each options destination

**Classification:** observed copy gap, with inferred decision cost. This is not evidence that any route is broken.

**Exact location:** F `6ZZV-0`; first Options card `70PQ-0`, title `70PR-0`, description `70PS-0`, route `70PT-0`; Options & market structure title `70PW-0` and description `70PX-0`; Options Screener title `70Q1-0`, description `70Q2-0`, and route `70Q3-0`. The result-count/route-retention claim is `70OU-0`. [Image][F-img] · [JSX][F-jsx]

“Research workspace,” “United States · Market research,” and “Specialist destination” locate the tools organizationally. They do not explain the analytical job that differentiates Options, Options & market structure, and Options Screener. The exact routes distinguish identity, but a user who does not already know `/options` versus `/options.html` must infer which destination fits the intended task. The title “Screener” provides more help, though its subtitle adds little.

**Smallest repair:** replace each generic subtitle with one short, verified “Use for…” description stating the destination’s distinct job. Retain the exact route as secondary identity and preserve all four destinations. Confirm those descriptions with the destination owner; this report does not invent capabilities for either options surface.

**Falsifier:** the current labels alone allow a user unfamiliar with the route strings to choose the intended destination for representative, explicitly stated jobs and explain the difference between the first two cards. Evidence that only route-literate users can do this would not falsify the concern.

### P2-02 — Put numeric scale in the financial table’s own heading or caption

**Classification:** observed local unit omission; inferred risk of reading inconsistent scales. No claim is made that the displayed figures are numerically wrong.

**Exact location:** C `6ZYB-0`; table heading `70G9-0`, Revenue label `70GN-0`, Operating income label `70GV-0`, selected revenue value `72A3-0`, EPS label `70HJ-0`. The chart caption `70FV-0` and evidence value `70EB-0` supply USD-billions context elsewhere. [Image][C-img] · [JSX][C-jsx]

The selected revenue panel explicitly expresses USD61bn. The table itself pairs unqualified revenue/operating-income numbers with an EPS row that specifies USD. A careful reader can infer the intended scale from the surrounding chart and panel, but the table should not depend on the currently open Revenue evidence panel to explain Operating income or on carrying a chart caption into a separate section.

**Smallest repair:** add one table-local caption at `70G9-0`, for example “USD billions, except EPS (USD/share)” if the owner verifies that basis. If the basis is not supplied, state that uncertainty rather than assigning a scale. Keep the explicit EPS exception and existing unsupplied-value treatment.

**Falsifier:** a crop containing only the table and its immediate heading unambiguously communicates the units of Revenue, Operating income, and EPS to a reader, without using the chart or selected Revenue panel. A verified existing table-local unit label would also remove the finding.

### P2-03 — Mark the options print that owns the open evidence panel

**Classification:** observed absence of a distinct selection cue in the visible origin-row segment; inferred reorientation cost. The post-close restoration claim remains a separate proof gap.

**Exact location:** D `6ZYC-0`; originating NVDA row `724R-0`, time wrapper/text `724S-0` / `724T-0`, ticker wrapper/text `724U-0` / `724V-0`; comparison ordinary row `7267-0`. The panel’s return/retention copy is `70LX-0`; close control `70LY-0` / `70LZ-0`. [Image][D-img] · [JSX][D-jsx]

The 440px panel occupies the right side of the 1024px board. Its header/time clearly identifies the selected print, but the visible time/ticker portion of that originating row does not visibly distinguish selection from adjacent prints. JSX corroborates that `724R-0` and ordinary row `7267-0` share the same 48px row wrapper treatment, with no selected background or outline in that wrapper. This makes the user locate the row again by matching panel details.

**Smallest repair:** add a durable selected cue at the visible start of the origin row—such as a selection marker plus a subtle row treatment—while retaining time/ticker and the panel’s explicit return context. Do not change the panel’s width merely to address this concern. Carry the same selected cue into a depicted post-close state.

**Falsifier:** the supplied image contains a recognizable selected-row marker in the visible time/ticker segment that distinguishes NVDA15:58:12 without reading and matching the panel, or an equivalent updated composition demonstrates that identification directly. A hidden cue beneath the overlay would not solve the visible-state concern.

## Truthfulness of data, history, source, and retention claims

The participation boards visibly qualify the values as illustrative and not live, expose the 30 Oct 2026 source date, disclose partial history, and distinguish the displayed five sectors from a complete ranking. These are meaningful safeguards against treating a selected current view as a live or exhaustive market feed. E additionally says that history has a gap while the current two periods are comparable. That is a coherent proposition; verifying the underlying periods is outside the supplied evidence. [A][A-img] · [E][E-img] · [H][H-img]

C does not fabricate a filing citation: the panel says none is attached, and accounting basis/retrieval time are not supplied. D distinguishes inferred buy direction from participant intent or prediction, labels the market as closed, and explains that connected transport does not make an older observation current. It also leaves moneyness/flags unsupplied instead of making them look known. These qualifiers should survive future simplification. D’s 21-day interval is consistent with its illustrated 30 October observation and 20 November expiry; this is not a claim about a live remaining duration on the review date. [C][C-img] · [D][D-img]

The evidence panel statements about preserved selection/filters/horizontal position, F’s “exact routes retained,” and the export-all-30-fields affordance describe intended behavior without demonstrating it. Treat them as pending behavioral claims in the design record. The captures neither prove them true nor establish that they are false. If a production-ready assertion is required, the relevant transition or export needs its own evidence; an explanatory sentence on a board cannot provide that evidence.

## Smallest next evidence needed

These are targeted design states or transition specifications for the owner, not a request to implement or run a browser in this advisory.

| Uncertainty | Minimal additional evidence and pass condition |
| --- | --- |
| Financial inspection and return | Depict selecting a different measure/period and closing evidence. The table must retain that exact cell, period, visible context, and intended focus target; the source panel’s identity/units must change with selection. |
| Options return and retention | Depict the same print before opening, during inspection, and after close with a non-default filter and nonzero horizontal position. The selected print, filters, and position must be specified consistently, including what happens if that print becomes unavailable. |
| History and missing observations | Show one history view with the disclosed missing session. Make observation dates and the comparison window explicit; avoid visually bridging the missing session as an observed value. |
| Source inspection on participation | Show one populated source state and one unsupplied-source state, with a clear return to the same sector/context. Preserve the source date and the distinction between observation freshness and connection state. |
| Expanded/compact navigation | Specify the A↔H transition’s current destination and focus return. A/H similarity is promising; it does not prove state retention. |
| Exact destination choice | Supply the verified task descriptions and destination mapping for F, including the two similarly named options surfaces. Then evaluate task choice without assuming route familiarity. |

Loading, empty, error, permission, success, keyboard, reduced-motion, and additional locale/theme/responsive states are not comprehensively represented by these six captures. Their absence is **missing evidence**, not an observed defect in those states. No general accessibility or interaction-completeness claim should be inferred from the one visible navigation focus example.

## Preserve and clarify

Preserve C’s visible access to statements, statistics, revenue, dividends, comparison, income/balance/cash choices, annual/quarterly periods, and deeper company research. Preserve D’s tape/local views, specialist options destinations, field access, and the explicit boundary around directional inference. Preserve A/E/H’s source/history entry points, coverage disclosure, and access to all eleven sectors. F should clarify choices while retaining its four distinct destinations.

Two secondary questions remain **inferences**, not blocking findings. “Advancing sectors” may mean price advancement or a participation threshold; an explicit definition would help if those differ in the product. “Your workspace” on A and its hidden counterpart on H do not establish a specific workspace identity; if users can switch among meaningful workspaces, show that identity where it affects interpretation. This evidence set does not prove either ambiguity causes a failure, so neither justifies a broad redesign.

There is no preference-only request to change the visual style or reduce density. The actionable concerns above concern interpretation and orientation within the supplied journeys.

## Integrity record

Neutral brief SHA256: `90ad8125abdd24d1ebe51cc3cdffca67b75c2fdd9604d2a494cc9ae6e6ce7c98`.

Twelve-member aggregate SHA256: `8465612640379507ac49a88fa6d3b3618736d7f8c586db45b4682b9905d584bc`. Aggregate construction: sorted member path, NUL, member SHA256, newline; SHA256 of that byte sequence. All twelve members matched the manifest.

| Member | Bytes | Verified SHA256 |
| --- | ---: | --- |
| A.jsx | 35541 | `40b681e539af78d90403e9090865a84ab50e04b14c2e42ee72b3ead13e91a15f` |
| A.jpg | 123859 | `f9566d05145b05bb1611c62c499eed19222153c1aecdf47b6177ec0765e51904` |
| C.jsx | 41969 | `5abd4b4f48360c699b587b5dee3a7d654aa9b7d8a74e169f5b7b8a16a66f8251` |
| C.jpg | 140091 | `7990201eecb765492fd731b320164e2b806833802f46f22c91a9f00550fadd12` |
| D.jsx | 60396 | `18712d1739f137edf98bb26de28394798736b82f7f2ff6b0a1334c2565f44035` |
| D.jpg | 105876 | `ccb8b0dbedfe280cfed262af4e01f13ac30a98841e26f9da3dca26ee487f2e53` |
| E.jsx | 20911 | `ff966235e3bddb9bcfd9f139a5b0927b2ae8f5d8cb010ccb42470e609f1a1b7c` |
| E.jpg | 55429 | `05cc4c09682062a6ac1277c851385364cd8ec01f1fa11f0d8d092eba1dfa8a15` |
| F.jsx | 11504 | `f18200ef593b20961250f710e1a5655f5753a126704794fb77ff0166708c6129` |
| F.jpg | 37625 | `a60511e2d97da7326aa4f68d4fe7c0671122b7685fc08924512844275dd18f89` |
| H.jsx | 37850 | `b7d5e4400cd19d62e7e0bfc4df5828b08cd37d20b04f3ca748e8d8294a0577d3` |
| H.jpg | 109406 | `24cbbb8221b02027c1d284af7c5fe6cfa0c91dcad12d0b1c06e7b9b1b7da3d22` |

**Closeout:** PROVEN_OUTCOME applies only to completion of this bounded advisory and local report. Design acceptance and interaction proof remain unclaimed. Parent retains all decisions and any subsequent writes. This is the unchanged first report.

[brief]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/REVIEW_INPUT.md
[manifest]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/CAPTURE_MANIFEST.json
[A-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/A.jpg
[A-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/A.jsx
[C-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/C.jpg
[C-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/C.jsx
[D-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/D.jpg
[D-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/D.jsx
[E-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/E.jpg
[E-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/E.jsx
[F-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/F.jpg
[F-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/F.jsx
[H-img]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/H.jpg
[H-jsx]: https://github.com/mastermindx-market-intelligence/macro/blob/be157007c4d4a33feb576a43f431eba3db5650ac/research/design_candidates/production_design_20261102/f01/evidence/native_revision_20261103/H.jsx
