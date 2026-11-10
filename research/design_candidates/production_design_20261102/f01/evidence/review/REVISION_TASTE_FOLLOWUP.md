# F01 revision taste follow-up — frozen bounded advisory

## Verdict

**T1, T2 and T4 are addressed in the supplied static artifacts. T3's requested destination-copy repair is implemented and is consistent with the attributed source basis supplied in the follow-up brief; the underlying user-choice hypothesis remains untested.** I observed no new visual defect requiring a repair in these three captures. This is an advisory judgment about the specific changes, not formal design acceptance, complete accessibility qualification, route proof, or product acceptance.

The D selection judgment comes from the actual composited JPEG: the selected row remains visible under the existing dark scrim, including an explicit “Selected” label. The cue is subdued, so the result does not establish robust recognition for every viewer or display. It does satisfy the original artifact-level requirement that the originating row be distinguishable independently of the drawer's return prose.

## Scope, custody and evidence

This is a post-first-pass follow-up. The first report remains unchanged. I inspected the supplied `REVIEW_INPUT.md`, `CAPTURE_MANIFEST.json`, and C/D/F JPEG/JSX pairs only, plus the first report's bytes solely to verify its hash. I did not reopen changing general source, author rationale, other F01 boards, or the underlying D08 source. I performed no Paper, browser, GitHub or Slack action, and launched no workers. The only new file written is this separate follow-up report.

| Binding | Value |
|---|---|
| Review date | 2026-11-03 |
| Immutable containing Macro commit | `8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177` |
| Source path | `research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/` |
| Manifest Git blob supplied by owner | `6db267b01f996ab072058b199b343acb26b8e567` |
| Paper file / page | `01M2WGNCX9475G79JRKJTCM08P` / `p-27-0` |
| Original six-board input commit | `be157007c4d4a33feb576a43f431eba3db5650ac` |
| First taste report source commit | `0d558e74ff16912e431772688d9c79f2a71ad44c` |
| First product report source commit, supplied for custody | `4dfcfde749d1c8566546224da5e9715de1d2b249` |
| Reused protected Mastermind law pin | `9f65957e29eba92245d78609f032aaea523b7cb4`, compatible INDEX 1.0.1 / bootstrap 1 |
| Six-member aggregate SHA256 | `cc448df630698e66ce8706d79f6ca26307a976967dbda4e7b88a079ef6dc5396` |
| Follow-up brief SHA256 | `8023d74ac2e03fafd324f4a702685bb37501df2f669d7277c5d42a5bf34ae2c2` |
| Unchanged first-report SHA256 | `6199dc781403d93da9cc30bebc75c1afef99ca227260820ce5ac78103a24d121` |

The parent supplied the immutable publication binding after reporting publication and manifest readback. I independently verified the local reviewed member bytes, byte counts and aggregate against the supplied manifest; I did not independently fetch GitHub. The manifest's operation/effect claims are owner metadata, not effects proved by this advisory.

[Immutable follow-up review input](https://github.com/mastermindx-market-intelligence/macro/blob/8ee1a8d1dc81dd8bf28d4bfcf2d7ba3316d45177/research/design_candidates/production_design_20261102/f01/evidence/native_followup_20261103/REVIEW_INPUT.md)

| Actually viewed JPEG | Exact board | Verified image dimensions | JSX corroboration |
|---|---|---|---|
| C.jpg | `6ZYB-0` | 1280 × 1180 | Matching root ID; table and selected-cell IDs, unit typography, 1180 px sidebar height |
| D.jpg | `6ZYC-0` | 1024 × 960 | Matching root ID; 196 px sidebar + 828 px content; 1024 × 960 scrim; 440 px drawer at x = 584 |
| F.jpg | `6ZZV-0` | 320 × 960 | Matching root ID and explicit root dimensions; four destination rows and target geometry |

All three original JPEGs were opened with `view_image` at original detail. Dimensions were checked from the JPEG files. JSX corroborates node identity and design geometry; its exported divs do not establish implemented semantic controls or behavior.

## Finding-by-finding disposition

### T1 — C table units: addressed in the static artifact

**Original severity: P2 observed defect.** Board `6ZYB-0`; table `70G7-0`; heading `70G9-0`; selected cell `72A2-0`.

The table now has the local line **“USD billions, except diluted EPS (USD/share)”** directly beneath “Income statement · selected rows.” The JPEG shows this line without clipping or collision. Its 12 px, regular-weight, 18 px line-height span is visibly subordinate to the 17 px bold heading, while staying close enough to apply to the table. The monetary rows no longer depend on a reader transferring units from the chart or the evidence panel, and the EPS exception is explicit.

The Revenue FY2024 selection remains visually intact. The additional unit line does not crowd the period headings or obscure the final table notes at the captured size. The amounts remain marked illustrative elsewhere in the capture, and the panel still says no filing is attached; the unit repair supplies interpretation, not a new source claim.

**Smallest further repair:** none required for the original local-unit defect in this capture. **Remaining falsifier:** if a user cannot identify the units of Operating income and Diluted EPS with the chart and evidence panel hidden, the wording or placement needs another pass. That task test and zoom/reflow behavior were not performed here.

Evidence: C.jpg; C.jsx nodes `70G7-0`, `70G9-0`, `70GV-0`, `72A2-0`, `70FV-0`, `70EB-0`.

### T2 — D originating-row selection: addressed in the static artifact, with a subdued presentation

**Original severity: P2 observed defect.** Board `6ZYC-0`; selected row `724R-0`; time/selection label `724T-0`; ticker `724V-0`; scrim `70JO-0`; drawer `70JQ-0`.

In the actual JPEG, the row beginning **15:58:12 / NVDA** now has a visible gray band with top and bottom boundaries, and “Selected” appears beneath the time in the exposed portion of the row. These cues are present to the left of the drawer. I can locate the originating row without using the explanatory return paragraph. The explicit word also means the design is not relying solely on a change of fill.

The JSX agrees with the observed presentation: row `724R-0` is 48 px high, has the selected fill token and 1 px `#777777` top/bottom borders; `724T-0` adds an 11 px semibold, 14 px line-height label beneath the 13 px time. This does not visibly overflow the row. The full 1024 × 960 scrim remains `#0000009E` (approximately 62% black), and the drawer still starts at x = 584 with a width of 440 px. The selected cue therefore survives the actual overlay; it is not merely present in unobscured JSX.

The background is still very dark. The thin boundaries and small label are quiet compared with the drawer. I regard this as sufficient to address the original absent-selection cue in this static modal context, not as proof that it is immediately recognizable to all users or under lower-contrast viewing conditions. I do not recommend lightening the whole background solely to make the inactive table compete with the drawer.

**Smallest further repair if recognition fails:** strengthen a local leading marker or the selected-label treatment while preserving drawer priority. **Falsifier:** with the drawer return paragraph covered, a viewer should identify the selected print from the background cue. No representative-user or low-vision test was performed. Separately, closing the drawer must restore the exact originating control and preserve the selected print, filters and horizontal position; `70LX-0` remains a promise of that behavior, not proof it occurs.

Evidence: D.jpg; D.jsx nodes `724R-0`, `724T-0`, `724V-0`, `70JO-0`, `70JQ-0`, `70LX-0`.

### T3 — F destination descriptions: repair implemented; user-choice inference remains open

**Original severity: P2 design inference, not a demonstrated route failure.** Board `6ZZV-0`; rows `70PQ-0`, `70PV-0`, `70Q0-0`, `70Q5-0`.

The revised descriptions explain concrete tasks instead of generic workspace categories. The four visible titles and route strings remain represented:

| Visible destination | Description node | Revised description | Visible route string |
|---|---|---|---|
| Options | `70PS-0` | Inspect flow, exposure and volatility. | `/options` |
| Options & market structure | `70PX-0` | Read the daily brief, flow and leaders. | `/options.html` |
| Options Screener | `70Q2-0` | Open the scanner in Options & market structure. | `/options_screener.html` |
| Futures | `70Q7-0` | Explore ES/NQ futures by session. | `/options/futures` |

This creates meaningful distinctions for volatility/exposure, the daily brief/leaders, the scanner, and session-based futures. The screener description also explains its relationship to the broader destination. Both Options entries still mention flow, so a flow-only task can remain ambiguous; the new copy reduces the original concern without proving that users choose correctly in that overlapping case.

The supplied brief attributes the vocabulary to D08's SOURCE_MAP at commit `e89f527e3267b1d1dd27ac7507e9a25983c0c903`, blob `dc7a280598567daefdcb5ea1e5f72ddc0d7daab8`. The copy is consistent with the excerpt provided in the brief: native Options Flow/Exposure/Volatility; legacy Daily Brief/Flow/Scanner/Ticker/Leaders; the screener replacement into `options.html#scanner`; and separate ES/NQ/session futures grammar. I did not independently reopen that source or verify its routes. This is attributed source support for the copy, not execution evidence.

At 320 × 960, all four results and the company-search fallback are visible. The longer screener description wraps to two lines without apparent clipping or overlap. The 15 px semibold titles, 12 px task descriptions and quieter route strings maintain a useful reading order. The JSX retains a 104 px minimum height for each result row; the capture does not establish whether the whole row is an active target.

**Smallest further repair:** none required merely to implement the requested source-grounded descriptions. **Remaining falsifier:** give representative users distinct volatility/exposure, daily-brief, scanner and ES/NQ-session tasks, plus an explicit flow task; check whether they select the intended destination without relying on route-string familiarity. If the flow task still confuses users, clarify the specific flow purpose from owner evidence. Do not invent a capability distinction or remove an advanced destination to force a cleaner menu.

Actual links, legacy replacement behavior, back navigation and destination contents remain unverified.

Evidence: F.jpg; F.jsx nodes `70PQ-0` through `70Q8-0`; attributed D08 excerpt in the follow-up `REVIEW_INPUT.md`.

### T4 — F internal route-preservation copy: addressed in the static artifact

**Original severity: P3 observed copy issue.** Board `6ZZV-0`; node `70OU-0`.

The results count now reads **“4 destinations.”** The internal phrase “exact routes retained” is absent. The line tells users how many results are shown without exposing an implementation claim. The JPEG and JSX agree.

**Smallest further repair:** none for this finding. No additional behavioral claim is implied by the count.

## Remaining limits and regression assessment

No new visible clipping, collision or hierarchy regression was observed in the three reviewed frames. C's local units remain subordinate to its financial table; D retains the evidence drawer as the dominant reading surface; F retains all four represented advanced destinations and its company-search fallback. These observations apply only to the captured sizes and shown states.

The following limits remain open and must not be converted into passes:

- **Behavior and context restoration:** no browser interaction, route execution, filtering, selection update, drawer dismissal, scroll restoration, focus return, or back-navigation path was tested. Source/return copy and visible route strings are design representations.
- **Accessibility and touch:** the D selection and F search-focus styling are visible presentations. Keyboard order, focus trapping, accessible names/roles, actual hit regions, contrast compliance, zoom/text scaling and reduced-motion behavior are not established by these JPEG/JSX exports. No conformance verdict is made.
- **User comprehension:** the destination wording has a supplied source basis and clearer task content. Its user-choice effectiveness, including the shared “flow” term, is not proven. Likewise, the D origin cue has not been tested with representative or low-vision users.
- **Full coverage:** A/E/H were not re-reviewed here; the brief identifies them as unchanged in the original six-board input. B/G/Readme/I are outside this follow-up. This report supplies no new Chinese-mobile, theme/locale, loading, empty, stale, error, permission or success-state coverage. Earlier evidence limits remain in place.
- **Effects and qualification:** the manifest labels this an unqualified bounded three-board capture. Its original I/grid `EFFECT_UNKNOWN` and Readme `DOCUMENT_CHANGED` holds remain outside this review and are not reconciled by it. No runtime admission, Pro receipt, operation qualification, formal review acceptance, or design/product acceptance is claimed.

## Integrity appendix

All six member SHA256 values and byte counts passed against `CAPTURE_MANIFEST.json`. The aggregate was independently recomputed as SHA256 of sorted `member path + NUL + member SHA256 + newline` and matched the assigned aggregate.

| Member | Bytes | SHA256 |
|---|---:|---|
| C.jpg | 142416 | `fdc42fb5c69891f0b11864ef19aeeced07fc304347e7c7b38099e42aab3f3281` |
| C.jsx | 42140 | `93f2bc32f6e5131eb5417f1de6902d4585c8cb145b6a2b4370db3e6b8ba5e8ee` |
| D.jpg | 106207 | `9889b663690d27c9ebd07a1ccfb21d30b2a9fbb6d86e40ec59a6b6c91bb6a3ba` |
| D.jsx | 60629 | `3e34643a2d64be2ff8dac94186bb6e01a584eabf50c34682c0a6c283b9228200` |
| F.jpg | 38728 | `9fbfe4fd0f3fef87b9c4682ee182621b6ddca1a8ddf5fe01a58899927fd83a64` |
| F.jsx | 11540 | `38efd24e4f7c97387250a5be8cf4b0a6e8d63f03c6f26682ff9f6b8207a33f42` |

The first report's SHA256 matched its frozen value before this follow-up and again at save verification. Its content was not edited.

**Disposition: PROVEN_OUTCOME for this bounded artifact advisory and its integrity checks only.** T1/T2/T4 have static remedies; T3 has the requested source-grounded copy repair with user-task validation still open. No formal acceptance is issued. This separate follow-up is frozen on save; the bounded assignment stops here.
