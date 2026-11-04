## First-pass judgment

**The 320 px screen is legible, and the four visible destinations are mostly distinguishable by task. The result-count wording needs a small clarification. Recovery of the other eight matches remains unproven because the supplied capture does not show the category menu or an explicit action to restore all results.**

This is advisory criticism of the captured screen, **not approval or formal acceptance**.

Target recorded in [CAPTURE_MANIFEST.json](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/CAPTURE_MANIFEST.json): file `01M2WGNCX9475G79JRKJTCM08P`, page `p-27-0`, artboard `6ZZV-0`, operation `F01-20261104-F-directory-filter-count-v1`. The supplied image, JSX, and facet-input hashes match that manifest. Its freeze scope is original F only.

### Findings by severity

| Severity | Finding and evidence | Smallest concrete repair |
|---|---|---|
| **High evidence gap for a completeness claim; no route-loss defect proven** | The capture displays four rows and **“4 of 12 matches”**, but does not show how to recover the remaining eight. The closed category control could provide that recovery, but its menu contents and behavior are absent from the inputs. Query **Clear** is located inside the search field, so users reasonably interpret it as clearing the query. It does not communicate “remove this category filter while retaining options.” Relevant nodes: category `70OR-0`–`70OT-0`, count `70OU-0`, query clear `72CA-0`–`72CB-0`. | Ensure the category menu offers **All categories**, with category selection preserving the query. To make recovery evident on this screen, add **Show all 12 matches** near the count; it should remove only the category filter. Provide the expanded-menu and restored-results states before claiming all matching destinations remain recoverable. |
| **Medium — result-count scope is underspecified** | Query **options**, category **Options & futures**, and **4 of 12 matches** are individually readable. Their relationship is implied. “4 of 12” can mean four category matches, the first four results, or four currently displayed results with more below. Nothing on the capture resolves that ambiguity. Nodes: query `70ON-0`, selected category `70OS-0`, count `70OU-0`. | Use two short lines: **4 in this category** and **12 matches across all categories**. The adjacent selected category supplies the category name without forcing a long line at 320 px. Couple the second line with the recovery action above. |
| **Low — the screener’s description prioritizes its parent destination over its task** | **Options Screener** is a useful title, but “Open the scanner in Options & market structure” emphasizes the relationship to another visible row. A user could wonder whether it simply opens the same page as **Options & market structure**. The distinct route helps a technical reader, but should not carry the main task distinction. Nodes: row `70Q0-0`, title `70Q1-0`, description `70Q2-0`, route `70Q3-0`. | Make the description action-first: **Open the options scanner.** Retain the parent relationship as secondary context if it is necessary. Keep the existing `/options_screener.html` target. No additional screening capability should be implied without evidence. |

Sources: actual [F.jpg](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/F.jpg), node definitions in [F.jsx](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/F.jsx), and the `directory_options_320` section of [OBSERVATIONS.json](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/live_followup_20261103/OBSERVATIONS.json).

## What works at 320 px

The hierarchy is coherent: title, query, category, count, destination rows, then company search. All four destination titles fit, the two-line screener description remains readable, and the capture has no visible horizontal clipping. Row separators and spacing make the choices easy to scan. **Search companies** is separated from the page/tool results and explicitly describes company-name or ticker search. These are strengths of this captured state. [F.jpg; JSX nodes `70MI-0`, `70ML-0`, `70S1-0`–`70S5-0`.]

The four tasks can be understood as follows:

| Visible destination | Task communicated | Judgment |
|---|---|---|
| **Options** — `/options` | Inspect flow, exposure, and volatility. | Clear analytical workspace purpose. `70PR-0`–`70PT-0`. |
| **Options & market structure** — `/options.html` | Read the daily brief, flow, and leaders. | “Read the daily brief” distinguishes it from the first workspace. The shared “flow” term is a modest overlap, not enough by itself to make the choices indistinguishable. `70PW-0`–`70PY-0`. |
| **Options Screener** — `/options_screener.html` | Open the scanner within the market-structure offering. | Title differentiates the task; description can be clearer as noted above. `70Q1-0`–`70Q3-0`. |
| **Futures** — `/options/futures` | Explore ES/NQ futures by session. | Strongest distinction: instrument and session context are explicit. `70Q6-0`–`70Q8-0`. |

All four displayed route strings agree with the four destination entries in [PROPOSED_FACET_INPUT.json](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/PROPOSED_FACET_INPUT.json) and with the baseline’s matching links. This establishes **textual route retention in the design**. It does not establish working navigation or preservation of the features behind those routes.

## The eight destinations that must remain recoverable

The baseline `directory_options_320` result for query **options** contains twelve destinations. Besides the four visible in F, it contains these eight:

| Baseline group | Matching destination |
|---|---|
| Learn | `/learn/options/charm-and-time-drift.html` |
| Learn | `/learn/options/dealer-hedging-mechanics.html` |
| Learn | `/learn/options/gamma-flip-levels.html` |
| Learn | `/learn/options/gamma-regimes.html` |
| Learn | `/learn/options/market-makers-middleman.html` |
| Learn | `/learn/options/open-interest-limits.html` |
| Learn | `/learn/options/zero-dte-regime.html` |
| Tools | `/tools/calculators/options-profit.html` |

Their absence from this category-filtered capture does **not** prove they were removed. Equally, the displayed total of twelve does **not** prove they can still be reached. The recovery behavior needs separate evidence. [OBSERVATIONS.json, `directory_options_320`, dialog link list and query entry.]

## Limits of the static evidence

The supplied screen cannot establish:

- What the category menu contains, whether **All categories** exists, or whether changing the category preserves the query.
- Whether the count is computed from the correct query and category scopes.
- Whether rows navigate to their shown routes, redirects preserve destination identity, or the advanced functionality behind each route survives.
- How returning from a destination restores the directory’s query, category, and scroll position.
- Keyboard interaction, focus restoration, accessible names, or the behavior of **Clear**. The exported `div` structure is not evidence of the production implementation’s semantics.
- Vertical behavior at the baseline’s **320 × 900** viewport. F is a **320 × 960** artboard with an overflow-clipped root; that difference calls for scroll verification, but does not by itself prove a production clipping defect.
- Light theme, Chinese copy, or loading, empty, stale, error, permission, and success states.

The smallest decisive follow-up is one continuous path: enter **options** with **All categories** and observe twelve results; select **Options & futures** and observe four; restore all matches while retaining **options**; verify that all twelve exact destinations remain available. At 320 × 900, also verify that the results and company-search action are reachable through the intended scroll behavior. That would resolve the central uncertainty without redesigning the directory.
