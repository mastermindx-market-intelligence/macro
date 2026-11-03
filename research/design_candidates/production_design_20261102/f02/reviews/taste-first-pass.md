# F02 Visual / Taste Critic — Frozen First Pass

**Verdict: BLOCK for adoption of this exact set as the shared product reference.**

This is an independent native advisory critique. It is **not** an admitted Opus RIG receipt, authority approval, browser verification, or Paper qualification.

**First-pass freeze:** 2026-11-03 02:04:52 UTC

## Artifact identity and review boundary

| Identity | Value |
| --- | --- |
| Supplied Macro commit | `6ee221069deba909b0f1eceee53869d4f4569ac9` |
| Artifact-set SHA256 | `2823e06343b79f47474657310a9301f22e25b8051e0cd168db60150d6ece97a0` |
| Manifest | `reviews/first-pass-artifacts.json` |
| Manifest file SHA256 | `9cc39370f50e0b0c97614f3742f953d42a1453f89ec1d3f2a132829b489915a5` |
| First-pass packet SHA256 | `bfcb8bc963903cdbca576a0d0691fd4d4f2887df0e3b1a5820b02163287c3a95` |
| Local identity check | All 32 files matched the manifest's byte lengths and individual SHA256 digests. The supplied commit was not independently checked through Git. |

All paths below are relative to `/workspace/scratch/55964f568673/f02/`.

I visually inspected the four production-before PNGs; all three canonical Paper-before JPGs; all eight light/dark desktop PNGs; `sheets/mobile-comparison.png`; `sheets/macro-dark-390.png`; and `sheets/states-and-semantics.png`. These 18 raster artifacts are the visual basis of this review.

I also read the listed narrow SVGs and selected text/layout coordinates from the listed Macro, Company, Options, mobile-comparison and state SVGs. The image viewer could not display `macro-light-zh-390.svg`; its text and coordinates were inspected, but its rendered typography was not verified. The Company 320px evidence composition is visible within the mobile-comparison raster.

The complete source specimen and remaining SVGs were included in the identity check; hashing them is not a claim to have executed or visually inspected them. No browser or HTML renderer was used. No candidate file was changed. I did not read author rationale, source contracts, READMEs, continuity/verification reports, PR discussion or the other critic's review. Explanatory labels already inside the permitted images were visible but were not treated as proof of behavior or capability preservation.

This first pass is frozen. Later rationale may explain a decision, but should not overwrite what these artifacts visibly communicate.

## Overall judgment

The visual language is a promising improvement. It is quieter, has a coherent warm neutral palette, and gives numbers, units and source information a much more deliberate relationship. Light and dark feel like the same product. The editorial slice has a particularly good reading rhythm.

The composition is not yet a convincing shared reference for an investor who needs dense comparisons. The same generous heading, metric strip and chart treatment is imposed on several different jobs. It postpones the table, while the table itself is made small enough to fit a specimen. Options is the clearest failure: a professional tape becomes a small-text table below a large introduction. Company also presents substantially less longitudinal information than the current screenshot. Mobile carries the desktop ordering forward rather than prioritizing the first useful comparison.

These are visible product tradeoffs, not a claim that unshown functions were deleted. Nevertheless, an investor scanning prints or comparing several years of statements has a credible reason to prefer the current product for that task. Cleaner styling does not resolve that loss.

## What is working

- **Metrics convey their meaning more honestly.** The prior canonical metric displays `66.7%` and `+1.13%` without a defined comparator. The proposed Macro shows `+1.13 pp vs prior session`, a coverage count and a reported-zero example. Company separates USD billions, percentages and USD/share, and uses a dash with an explicit missing explanation for EPS. These are meaningful reading improvements.
- **The visual palette is controlled.** Light surfaces have enough separation without relying on heavy shadows. Dark text hierarchy remains readable; the warm chart series is distinguishable from green/red direction and cyan/purple trade side. Neither theme looks like a simple color inversion.
- **The editorial page is substantially calmer.** The supplied before image has an alert strip, strong blue chrome, a floating assistant and a dense calculation box competing with the article. The after page establishes a clear title, restrained TOC, comfortable body measure and an aligned calculation table. Its left rail and continuation links are easy to locate.
- **Evidence is presented as useful content.** The desktop evidence panel names the sector, shows the value and comparator, and separates observation/publication/retrieval. The narrow Company panel keeps the entity and fiscal periods above the longer explanatory material. The visible focus outline around its close control is strong.
- **The state vocabulary is much clearer.** Loading, empty, stale, partial, failure and uncertain save outcomes have distinct titles and consequences. The former canonical state specimen includes a skeleton-looking treatment labelled EMPTY; the proposed text makes the difference between waiting for a response and a completed zero-match request clearer. Actual transitions remain unverified.

## Findings

### VTC-001 — Major — The desktop hierarchy delays the core comparison

**Type:** Observable visual/product defect.  
**Tasks:** T01, T07; also affects T06, T08 and T12.

In `options-light-1440.png` and `options-dark-1440.png`, the tape header begins around y=722 and the first row's text is at y=780. Before it come the page introduction, a source line, connection strip, three metrics, a two-bar chart, a classification explanation and the filter row. In `evidence/options-before.png`, the tape header begins around y=410, alongside the activity-leader column and below the existing workflow/filter controls.

The snapshots have different native widths, so this is not a controlled same-viewport benchmark. The visible displacement is nevertheless large: the proposed image requires a 1,250px canvas to show twelve rows, and the main reading task starts roughly 300px later. At an ordinary laptop-height viewport, a much larger share of the page is introductory material.

The same pattern occurs in Macro and Company: the comparison headers begin around y=804 and y=842 respectively. The top of the screen looks spacious, while the actual numeric work is concentrated near the bottom.

**Required direction:** Make the primary comparison determine the composition. Compress the overview and source context; place the principal filters and useful rows earlier. The two-expiry summary can occupy a compact supporting area or a deliberate alternate view. Recover space from the introduction before reducing data text.

### VTC-002 — Major — The narrow layout puts comparison after more than a screen of setup

**Type:** Observable visual/product defect.  
**Tasks:** T01, T03, T05.

In `macro-dark-390.png`, the first sector value is at y≈1057. The image spends the first ~990px on the title, description, source action, summary metrics, chart, chart-value action and tabs. The 1,420px composition then shows only three sector rows.

Each visible row places its Evidence button on a separate line, producing an approximately 80px row pitch. The button is comfortably sized, but the resulting presentation is slow for scanning ten sectors. The metric `9 / 10` is visible long before any raw comparison supports it.

The horizontal-scroll hint is helpful. It does not compensate for ordering the primary table this late. The PNG does not prove whether the table actually scrolls, whether labels stay visible during scrolling, or whether more rows continue; those are separate unknowns.

**Required direction:** Put the task choice and first useful rows substantially earlier in the 390px layout. Use a compact summary and a deliberate chart/table priority. Preserve an adequate touch target while designing evidence access into a tighter row. Show enough adjacent rows for comparisons to feel like a table rather than repeated cards.

### VTC-003 — Major — The Company example weakens longitudinal comparison

**Type:** Observable reduction in the depicted comparison; capability preservation is unknown.  
**Tasks:** T01, T06, T12.

`evidence/company-before.png` displays a five-series statement chart across 2010–2026 and a raw-value table with five visible annual columns, 2022–2026. The proposed Company sheets display one revenue series for five years and only three table periods, FY2024–FY2026. The table has ample width and adds a separate change/source area, but the investor sees fewer periods at once.

The small `17-year history remains reachable` link expresses a route to more information. It does not demonstrate the current ability to inspect several financial measures across the longer history together. The generic instruction that history is retained is not visual proof of an equally useful comparison.

A focused revenue chart is useful for that specific question. It is insufficient as the only demonstrated reference for the broader statements task.

**Required direction:** Include a dense Company treatment that demonstrates the longer historical comparison and enough side-by-side raw periods. Preserve direct access to the useful multi-series view without making the investor reconstruct it through repeated navigation. Show the pattern under realistic statement density, including long labels and unavailable/non-comparable cells.

### VTC-004 — Minor — The tape spends its smallest type on its most important content

**Type:** Observable typography/scanning defect.  
**Tasks:** T01, T07, T11.

The Options SVG specifies 11px body text and 10px headers across twelve columns. The screenshot also removes most internal row separators. On a wide, flat table, a user must track small text across instrument, time, expiry, type, strike, estimated side, premium, contracts, DTE, moneyness, flags and source.

The prior tape is visually busier, but its horizontal rules and compact categorical treatments help the eye hold a row. The proposed version reduces that assistance at the same time that it makes the raw data small. This is especially incongruous beside the generous overview above it.

**Required direction:** Increase sustained-reading text size and add a restrained row-tracking treatment. Use grouping or spacing to distinguish contract identity from execution/value fields. Validate the result at native scale; fitting all twelve example rows into a long export image is not the useful target.

### VTC-005 — Minor — The open evidence panel is only weakly connected to its selected row

**Type:** Observable selection/context defect.  
**Tasks:** T02, T03.

The Macro evidence panel is open for Communication services. In the comparison, that row is indicated only by bolding its sector name. Other selected surfaces, such as the Comparison tab and Analysis rail item, use a filled treatment. The row's values receive no equivalent selection cue, and the repeated Evidence links all look alike.

The panel correctly names the sector, so the identity is recoverable. It takes more deliberate visual matching than necessary. The headline value also happens to equal the selected sector value, while the top-level title describes Market breadth; a more explicit scope cue would reduce ambiguity about which observation the open inspector is explaining.

**Required direction:** Give the selected row a quiet, persistent treatment across the row, and clearly distinguish selected context from keyboard focus. Keep the panel's entity/field title. Label the scope of the headline/chart when it differs from the row being inspected.

### VTC-006 — Minor — Some state copy is written for implementers

**Type:** Observable user-facing language defect.  
**Tasks:** T10.

In `states-and-semantics.png`, the SAVED specimen's headline is `Readback confirmed`, followed by an owner returning a saved object generation. The access specimen discusses a restricted payload being sent to the client. These phrases describe implementation mechanics rather than what an investor needs to know.

The outcome taxonomy is good. The technical wording makes the most reassuring state harder to understand than the nearby `Refresh completed` state.

**Required direction:** State the user result first: what was saved, whether the current view is retained, and what the next action does. Keep authority/readback requirements in implementation documentation rather than the product message. This recommendation does not relax those requirements.

## Task judgments

These judgments apply to the **depicted product experience**. BETTER does not certify execution, and WORSE does not establish that an unshown capability was deleted.

| Task | Judgment | Basis and limit |
| --- | --- | --- |
| T01 Compare dense numeric rows | **WORSE** | Alignment and units improve, but desktop placement, mobile ordering, tape text size and Company period count weaken useful simultaneous comparison. |
| T02 Interpret a metric and change | **BETTER** | Explicit pp, comparator periods, currency, reported zero and missing fields improve interpretation. Scope of the Macro headline/selected evidence could be clearer. |
| T03 Inspect exact evidence and return | **UNKNOWN** | The evidence layouts are strong and identify their context. Static images do not prove correct binding, source access, focus return or scroll restoration. |
| T04 Understand stale/partial/connected states | **BETTER** | The displayed language separates connection, source time, session and coverage. Runtime retention and state transitions are unverified. |
| T05 Use keyboard/touch/400% zoom | **UNKNOWN** | The mobile controls and visible focus ring are encouraging. No keyboard journey, zoom render, table-scroll behavior or virtualized-list semantics was exercised. |
| T06 Preserve Company depth | **WORSE** | The shown comparison has fewer periods and much less multi-series history. Routes and controls are visible, but preservation of the deeper interaction is unknown. |
| T07 Preserve Options depth and meaning | **WORSE** | Estimated-side meaning is clearer, but scanning the tape becomes a lower-priority, smaller-text task. Full workflow, saved-screen and export scope preservation cannot be inferred from the slice. |
| T08 Preserve Macro capabilities | **UNKNOWN** | A breadth slice cannot establish regime/risk/calendar/linked-desk preservation. The before image demonstrates these other jobs; the after set does not show their integration. |
| T09 Read and navigate public editorial | **BETTER** | Stronger reading hierarchy, table alignment and continuation layout. The before page exposes the annualization formula inline; the after's Inspect calculation route would need to retain that derivation. Anchor/navigation behavior remains unknown. |
| T10 Handle exceptional states | **BETTER** | The depicted distinctions and recovery intentions are clearer. State transitions, retained data and write authority are not proved by cards. |
| T11 Switch theme/locale/density | **UNKNOWN** | The inspected EN light/dark styles are visually coherent. Actual switching, density modes, rendered CJK and long-label behavior were not established. |
| T12 Domain verdict/count/lifecycle and focused charts | **UNKNOWN** | The displayed charts clearly name units and show a real missing-data gap. Existing domain partitions, lifecycle transitions, replay and specialized chart capabilities are outside the demonstrated visual evidence. |

## Strongest argument against acceptance

The reference systematically gives more screen space to explaining the specimen than to performing the investor's comparison. This is not simply a taste preference for denser screens. The current Options page exposes a working tape early, and the current Company page exposes many periods and financial series together. The proposed images are cleaner but defer the first task and show less of the second. Mobile intensifies the same priority error.

Adopting these compositions as the shared standard would risk standardizing a pleasant overview at the expense of the product's strongest analytical work. The visual tokens and editorial direction can survive revision; the comparison hierarchy needs to change before this set should be accepted.

## Unknowns and acceptance boundary

The following are **not asserted defects**, and they must not be converted into passes by reading explanatory labels:

- Rendered ZH typography, wrapping and font fallback. Only the supplied ZH SVG text/coordinates were readable through the permitted tools.
- Narrow Company statements, Options tape and public editorial compositions. The supplied narrow raster pair covers Macro and a Company evidence overlay.
- Keyboard navigation, tab order, Escape behavior, focus/scroll return, horizontal overflow, sticky context, touch gestures, 400% zoom and virtualization.
- Source-to-field binding, evidence destinations, query freshness, save outcomes, access enforcement, historic routes, export scope, density switching and retained domain logic.
- Whether the standalone source produces the same geometry as the supplied static sheets.

For a revised visual pass, the decisive evidence is a comparison-first desktop and 390px composition, a credible dense Company history example, readable Options rows at native size, and clearer selected evidence context. Those changes should be judged against the same production-before tasks. Behavioral proof remains a separate requirement.

**Freeze statement:** No rationale reveal or peer critique was available to this critic before the freeze recorded above. Amendments, if later requested, must be appended or separately versioned so this first-pass judgment remains intact.

