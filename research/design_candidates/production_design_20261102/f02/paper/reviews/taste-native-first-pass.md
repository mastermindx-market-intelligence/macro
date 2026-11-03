# F02 native observed candidate — independent Visual Taste first pass

## Decision

**BLOCK — advisory judgment on the supplied frozen reference set.**

The desktop visual direction has substantial strengths: quieter surfaces, coherent light/dark treatments, useful analytical density, clearer financial units, and a much stronger public reading layout. It should not yet become the complete shared reference. The actual native consumer tables regress numeric alignment, the Company table reduces the visible history of growth comparisons, and the required narrow/locale/density variants are not represented in this freeze. These are specific reference defects and evidence gaps; they are not a claim that the running product has deleted features or that an untested interaction has failed.

This is an independent **Visual Taste advisory review**, not an Opus reviewer-class formal RIG receipt, design-authority approval, product integration acceptance, or production approval.

## Identity, immutable input, and integrity

- Agent: `/root/native_taste_critic_v1`.
- Model identity exposed in this session: **GPT-6 Astra Pro**. No separate provider model ID was available to verify.
- First-pass report frozen at UTC: **2026-11-03T05:32:55+00:00**.
- Input artifact ID: `F02-native-observed-20261103-a`.
- Input manifest frozen at UTC: `2026-11-03T05:22:42.159981+00:00`.
- Supplied repository provenance: `mastermindx-market-intelligence/macro`, commit `245d70bbd3ac773f3074277c771095264b31269d`. The commit is supplied task provenance; I did not inspect Git or files outside the quarantine to independently verify repository membership.
- Input root: `/workspace/scratch/55964f568673/f02-native-review-freeze-1`.
- Independently computed artifact-set SHA256: **`98c7569adb5827e7b3ab16350e56be642ede4ddd961dc4d599b99b7bf4d69b3b`**.

Before making visual judgments, I read the first-pass packet and manifest, then independently verified the byte length and SHA256 of **all 44 members**. There were **44 unique paths, zero length mismatches, and zero hash mismatches**. I recomputed the canonical aggregate from UTF-8 records of sorted relative path, NUL, lowercase member SHA256, and newline, excluding the manifest itself. It exactly matches the supplied aggregate. Verification did not substitute for visual examination: all **25 supplied images** were subsequently opened and inspected at original detail.

`paper/native-capture-scope.json` limits the state evidence. The sixteen-row state matrix is the in-progress capture from `2026-11-03T05:09:09.734Z`–`2026-11-03T05:09:13.274Z`; the two supplied combined-state sections were captured at `05:10:11.897Z` and `05:10:33.317Z`. The full final state board and its later semantic/selection-focus sections are **not captured evidence**.

## Findings

### NVTC-001 — BLOCKER — Consumer numbers do not share a right or decimal edge

**Kind:** observed visual defect. **Tasks:** T01; also affects T06, T07, T11.

**Before evidence:** `evidence/company-before.png`, income-statement value columns, and `evidence/options-before.png`, Size/Premium comparison lanes. The Company view places differently sized values against a common right edge, including values such as `26.91B` and `−100.00M`.

**After evidence:** `paper/screenshots/company-light.jpg` and `company-dark.jpg`, FY 2022 column; `paper/screenshots/options-light.jpg` and `options-dark.jpg`, Strike and Contracts columns. The same start edge is used for `12.00` and `6.00` in Company, so their decimal points and trailing digits do not line up. In Options, `1,500`, `940`, and `730` start in the same position instead of sharing an integer right edge. Macro's zero and missing-value lanes show the same consumer construction, though the mostly equal-length percentages make the problem less conspicuous.

This is a native-image observation, not merely a CSS concern. Targeted export inspection corroborates it: Company text nodes `5MI-0` (`12.00`) and `5M0-0` (`6.00`), and Options nodes `6GM-0` (`1,500`), `6B2-0` (`940`), and `68Z-0` (`730`), carry `textAlign: 'right'` on `width: 'max-content'` text frames. The visible result remains positioned at the start of each cell. A right-align declaration does not overcome the observed geometry.

The inconsistency is especially clear against `paper/screenshots/metrics.jpg` and `metrics-light.jpg`, where the numeric lanes visibly end-align the percentages, changes, and coverage. `paper/screenshots/grammar.jpg` and `foundations.jpg` propose right/decimal alignment; those statements do not establish that the consumer boards achieve it.

**Why it matters:** magnitude comparison is a primary financial reading task. A user must mentally compensate for shifting decimal and digit positions across rows, and the shared specimen is not carried consistently into its consumers.

**Required correction:** position numeric text against the cell's actual end edge, preserve tabular numerals, and align like quantities by decimal/right edge. Re-capture Company, Options, and Macro in both themes with mixed integer lengths, negative values, zero, missing values, and realistic unit exceptions. Merely retaining the existing alignment annotation is insufficient.

### NVTC-002 — MAJOR — Company loses the visible history of period-by-period changes

**Kind:** observed view-level tradeoff/regression; no claim of product-wide feature deletion. **Tasks:** T01, T02, T06.

**Before evidence:** `evidence/company-before.png`, the five visible annual columns. Each year shows its value and its corresponding growth/change beneath it. The Revenue row exposes a sequence of annual changes, and the Gross profit and Operating income rows include a visible negative historical change. This lets the reader scan acceleration, deceleration, and reversals across the same row.

**After evidence:** `paper/screenshots/company-dark.jpg` and `company-light.jpg`. Five annual raw values remain, but the only change column is `FY26 / FY25 change`. The earlier four periods have no accompanying change values in this table. The raw values are readable, but a user must now calculate earlier changes or leave this view to compare the growth sequence.

This is not solved by the 17-year grouped bar chart: its geometry communicates scale and long-run shape, not the exact period-to-period growth values formerly visible in the table. The references to existing owners in the footer are proposals and do not show a retained alternate comparison mode.

**Why it matters:** a reasonable investor comparing historical growth quality could prefer the current Company table even while preferring the candidate's calmer surfaces and clearer unit labels. More whitespace and a single recent-change lane should not silently reduce analytical information.

**Required correction:** show how historical change comparisons remain reachable and scannable in the shared table pattern, for example through a demonstrated value-plus-change density mode or an explicit comparative view. Preserve the distinction between percentage growth and pp changes. If this is intentionally a reduced slice, the native reference needs a visible retained path to the fuller comparison rather than only a footer assertion.

### NVTC-003 — MAJOR — Narrow, localized analytical, and density variants are absent from the visual evidence

**Kind:** absent proof, not an observed responsive or translation failure. **Tasks:** T05, T11; also limits T01, T03, T09.

**Exact evidence:** the manifest and `paper/native-capture-scope.json` supply all eight consumer screenshots at **1440px wide**. None is a narrow consumer layout. `paper/screenshots/states-matrix--combined-dark.jpg` is a **680 × 280** component capture; it is not a phone screen or evidence-overlay layout. `paper/screenshots/builder.jpg`, `controls.jpg`, and `readme.jpg` contain written mobile/zoom promises. The readme even refers to mobile boards, but no such boards are present in this frozen set.

The EN/ZH evidence is also bounded. `paper/screenshots/editorial-light.jpg` visibly shows Chinese public navigation and breadcrumb chrome with an English article body. That is a useful, internally coherent public-language example, consistent with the board's stated English-body policy. It does not establish Chinese analytical labels, long localized column names, filter wrapping, or a translated evidence panel. The three analytical consumers remain English, with an `EN / 中文` label in their headers. Likewise, `foundations.jpg` names dense, comfortable, and mobile dimensions, but the freeze does not show the same consumer changing density.

**Why it matters:** dense tables, a docked evidence panel, long labels, and public prose create different narrow-layout problems. Their proportions cannot be assessed from a 1440px screen or from written breakpoint instructions. No conclusion about 400% zoom behavior is possible from this packet.

**Required evidence:** native narrow captures for the four consumer roles, including table horizontal movement/context, an evidence overlay, and the public reading/TOC arrangement; localized analytical long-label examples; and an actual density comparison with the same data. Light/dark treatment should remain visible in the relevant constrained patterns. Browser keyboard, touch, focus-return, and 400% reflow verification remains a separate unproven step, outside this first-pass permission boundary.

### NVTC-004 — MINOR — Consumer unit labels fall below the demonstrated core type scale

**Kind:** observed internal consistency and legibility concern. **Tasks:** T02, T06, T11.

**Evidence:** `paper/screenshots/foundations.jpg` explicitly demonstrates `12 / Source, unit and status`, and the metrics boards give units and comparator context clear supporting text. In `paper/screenshots/company-light.jpg` and `company-dark.jpg`, row-level `USD bn`, `%`, and `USD/share` labels are visibly much smaller. Targeted JSX inspection confirms **10px** row-unit text, for example `company-light.jsx` node `5MK-0`; the table headers are **11px**. Macro and Options also use 11px table headers. The earlier production Company screenshot supplies a prominent table-level currency label; the candidate retains that general idea but makes its row-level exceptions less prominent.

This is not a measured contrast failure or a claim that every 10px annotation is essential. It is a specific inconsistency where unit exceptions carry financial meaning. The core specimens are easier to read than the consumer realization.

**Correction:** carry the demonstrated 12px source/unit floor into meaningful consumer unit labels and test the header/row proportions with actual dense data. Preserve the useful row density; increasing every annotation or surrounding container is not necessary.

## What the images do well

The reference is visually coherent across consumers. Titles, secondary descriptions, quiet tab fills, restrained separators, and consistent evidence-link colors make Macro, Company, and Options feel related. The public article shares the type and color language while retaining an appropriate reading column rather than inheriting an investor sidebar. Light mode uses white data surfaces against a lightly tinted canvas; dark mode retains legible primary text and subdued supporting text. Neither theme depends on large decorative gradients or pervasive colored cards.

Financial semantics improve materially over `evidence/paper-metric-before.jpg`. The new metric specimens explicitly distinguish pp from relative percentage growth, show the comparator, render missing EPS as a dash plus “Unknown,” and distinguish it from a reported zero dividend. The Macro receipt visibly separates observation, publication, and retrieval clocks. Positive/negative changes have signs as well as color. Options uses approximate Buy/Sell labels with cyan/purple treatments, keeping side classification distinct from green/red market movement. These are visible gains; source binding and live semantic correctness are not inferred.

The charts remain useful compressed views. Company retains 17 annual groups with five series, a zero baseline, units, readable year labels, and a legend. Options provides twelve visible tape rows plus a compact expiry-grouped premium chart with direct value labels. Macro shows ten sector rows and an eight-session chart whose missing observation remains a gap. The grammar board is much more interpretable than the earlier pattern board's unbound bars: the new graph has units, scale, session labels, a deliberate gap, and exact values. Because the before and after images have different capture heights and content, I do not claim a measured per-viewport density improvement simply from their row counts.

The public article is a particularly strong desktop improvement. `editorial-dark.jpg` and `editorial-light.jpg` use a clear title/deck/body hierarchy, an approximately 720px reading column, a quiet TOC, a compact calculation table, and visible assumptions and continuation destinations. The calculation and prose remain legible without a stack of oversized cards. Publication and example-update dates are presented as document context. Anchor navigation and continuation destinations are visible affordances, not verified routes.

The state matrix communicates materially more specific outcomes than the supplied earlier state cards. Loading, zero matching results, partial coverage, source staleness, access requirements, pending save, confirmed save, failure, and uncertain outcome have distinct copy and recovery labels. The combined captures keep stale and partial caveats beside the retained value while the save outcome changes. “Loaded” is not presented as a permanent green success claim. I credit this visible state anatomy while reserving all authority, deduplication, reconciliation, and transition behavior for actual implementation evidence.

## Consumer comparison and current-product preference

| Consumer | Observed visual assessment | Important preference or evidence limit |
| --- | --- | --- |
| Macro | Breadth comparison and source receipt are clearer and calmer; coverage, zero, missing values, and the chart gap are visible. | `macro-before.png` is a regime/risk overview with a 61-session chart, instrument strip, and action/calendar context. The candidate is a different breadth slice. A user doing that overview task would still prefer the supplied current screen; this packet does not show a corresponding replacement or retained visual integration. |
| Company | Long history, statement selectors, annual/quarterly labels, source links, and a five-series chart remain represented. | Numeric alignment and the loss of per-year change companions make historical financial comparison harder in the supplied after table. Functional access to earlier periods and the rest of Company depth remains unverified. |
| Options | Explicit expiry, type, strike, time, approximate side, coverage caveats, and retained unknown moneyness make the fixture easier to interpret. The twelve-row tape remains reasonably dense. | The current screenshot shows category/view tabs, saved screens, activity leaders, and other workflow context not represented in the after slice. The footer cannot prove that context remains easy to find. Numeric alignment still needs correction. |
| Public editorial | Readability, theme coherence, calculation hierarchy, assumptions, and continuation affordances are stronger. | Only wide reading is shown. Chinese public chrome is visible in light mode; the English body is intentional in this specimen. Narrow TOC, focus, anchors, and destination behavior remain unknown. |

## Twelve-task judgment

These judgments concern task-facing evidence in the frozen artifacts. **BETTER** credits a visible improvement, not untested runtime behavior. **UNKNOWN** means a material part of the required task cannot be judged from the supplied images/exports. All twelve tasks are critical in the packet.

| Task | Judgment | Observable basis and limit |
| --- | --- | --- |
| T01 Compare dense numeric rows | **WORSE** | Useful row/column density survives, but consumer numeric edges do not align and Company historical change companions disappear from the shown comparison. NVTC-001/002. |
| T02 Interpret a metric and its change | **BETTER** | Core metrics and consumer labels distinguish units, pp, comparator periods, missing values, and reported zero. Company historical-change coverage and very small unit labels remain qualifications. |
| T03 Inspect exact evidence and return | **UNKNOWN** | Macro visibly improves receipt anatomy, selected-row context, entity naming, and three clocks. Exact binding, opening/closing, focus return, and scroll restoration are only asserted. |
| T04 Understand stale/partial/connected states | **BETTER** | State and combined captures keep coverage and source age explicit and retain the value; Options separates connected transport from market session and snapshot time. Live ownership and clocks are not verified. |
| T05 Use keyboard/touch/400% zoom | **UNKNOWN** | A focus specimen and interaction instructions exist, but no native narrow consumer layout, touch journey, or browser zoom/focus evidence is supplied. NVTC-003. |
| T06 Preserve Company depth | **UNKNOWN** | 17 years, five plotted series, annual/quarterly and statement selectors, unknown EPS, and evidence links are represented. Earlier-period behavior, definitions/citations, route/entity continuity, and full depth are not demonstrated; the visible growth comparison regresses. |
| T07 Preserve Options depth and meaning | **UNKNOWN** | The after tape has clearer contract components and separate side semantics. Full workflow tabs, saved screens, exposure, share/export scope, entitlement, and domain integration are not demonstrated by the fixture. |
| T08 Preserve Macro capabilities | **UNKNOWN** | The after breadth slice is legible, but it is not a like-for-like depiction of the before regime/risk/calendar overview. Retained domain functions and their visual integration cannot be established. |
| T09 Read and navigate public editorial | **BETTER** | Wide reading hierarchy, calculation, assumptions, dates, TOC, and continuation labels are clearer. This does not verify links, anchors, keyboard navigation, or narrow reading. |
| T10 Handle exceptional read/write/access states | **BETTER** | The supplied state anatomy is more explicit and distinguishes pending, failed, uncertain, saved, guest, plan-required, and expired-after-send outcomes. Actual authority and state transitions remain unknown. |
| T11 Switch theme/locale/density | **UNKNOWN** | Both desktop themes are visibly coherent. A Chinese public-chrome example is supplied. Analytical ZH, long-label stress, narrow layout, and density changes are absent; consumer type/number consistency also needs correction. NVTC-001/003/004. |
| T12 Use domain-owned verdict/count/lifecycle and focused charts | **UNKNOWN** | Focused charts have clearer visual grammar, but the retained verdict/count/lifecycle/replay patterns are not shown in a comparable after integration. Ownership statements are not visual or behavioral proof. |

## Examined files and quarantine attestation

**Visually examined — all seven before images:**

- `evidence/macro-before.png`
- `evidence/company-before.png`
- `evidence/options-before.png`
- `evidence/editorial-before.png`
- `evidence/paper-metric-before.jpg`
- `evidence/paper-state-before.jpg`
- `evidence/paper-pattern-before.jpg`

**Visually examined — all eighteen after images:**

- `paper/screenshots/readme.jpg`
- `paper/screenshots/foundations.jpg`
- `paper/screenshots/metrics.jpg`
- `paper/screenshots/metrics-light.jpg`
- `paper/screenshots/controls.jpg`
- `paper/screenshots/grammar.jpg`
- `paper/screenshots/builder.jpg`
- `paper/screenshots/macro-dark.jpg`
- `paper/screenshots/macro-light.jpg`
- `paper/screenshots/company-dark.jpg`
- `paper/screenshots/company-light.jpg`
- `paper/screenshots/options-dark.jpg`
- `paper/screenshots/options-light.jpg`
- `paper/screenshots/editorial-dark.jpg`
- `paper/screenshots/editorial-light.jpg`
- `paper/screenshots/states-matrix-in-progress.jpg`
- `paper/screenshots/states-matrix--combined-dark.jpg`
- `paper/screenshots/states-matrix--combined.jpg`

**Text/scope examined:** `paper/reviews/NATIVE_FIRST_PASS_PACKET.md`, `paper/reviews/native-first-pass-artifacts.json`, and `paper/native-capture-scope.json`. Targeted layout, numeric, type-scale, and variant statements were inspected in the fifteen complete-board JSX exports: `readme.jsx`, `foundations.jsx`, `metrics.jsx`, `metrics-light.jsx`, `controls.jsx`, `grammar.jsx`, `builder.jsx`, `macro-dark.jsx`, `macro-light.jsx`, `company-dark.jsx`, `company-light.jsx`, `options-dark.jsx`, `options-light.jsx`, `editorial-dark.jsx`, and `editorial-light.jsx`, all under `paper/exports/`. This was targeted export corroboration, not a claim of source-code or runtime review. The two combined-state JSX exports were integrity-verified; their actual screenshots supplied the visual evidence.

All 44 manifest members were read for byte/hash verification. Only content within the immutable input root was used as review input. I did not inspect other F02 files, external author rationale, previous reviews, operational notes, pending inputs, or the peer review. Visible candidate annotations and references to other documents/reviews were encountered only as parts of permitted native boards; I did not follow them and did not accept them as proof. No Paper, Browser, external website, or design-mutation call was made. The immutable inputs were not changed. The only review deliverable written outside the input root is this specifically authorized report.

**First pass stops here.** No author-rationale reconciliation or peer-review synthesis has been performed.
