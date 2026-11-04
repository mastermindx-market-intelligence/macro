## First-pass advisory judgment

**The captured F01 directory is visually coherent at 320px. I found no visible clipping, overlap, broken wrapping, or severe density problem.** Its main remaining clarity issue is the meaning of **“4 of 12 matches.”** That wording leaves the user uncertain whether the four visible rows are the complete filtered result.

This is a first-pass visual assessment of **Original F only**, not design approval or programme acceptance.

**Target:** file `01M2WGNCX9475G79JRKJTCM08P` · page `p-27-0` · board `6ZZV-0`  
**Capture operation:** `F01-20261104-F-directory-filter-count-v1`

Evidence inspected: [F.jpg](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/F.jpg), [F.jsx](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/F.jsx), and [CAPTURE_MANIFEST.json](sandbox:/workspace/scratch/43a778472c23/f01-drafts/evidence/native_directory_20261104/CAPTURE_MANIFEST.json).

### Visual findings

| Area | Judgment and exact evidence |
|---|---|
| **Hierarchy** | Clear. “All tools” (`70MI-0`, 20/24 bold) establishes the screen. The outlined search field (`70OM-0`) attracts attention next, followed by category, count, and results. Result titles use 15/21 semibold, with smaller descriptions and routes. |
| **Wrapping** | Controlled at the captured width. “Options & market structure” (`70PW-0`) remains on one line. The Screener description (`70Q2-0`) wraps naturally into two lines without crowding its route (`70Q3-0`). No awkward word breaks are visible. |
| **Clipping and alignment** | No visible clipping or overlap. The 16px outer gutters remain intact. Search and category align with the content column; result text receives additional inset padding. Footer content fits within the captured 960px height. |
| **Density** | Comfortable rather than cramped. Four results, their descriptions and routes, and the company-search exit all fit. The row treatment provides enough separation to scan similar tool names. There is no visible need to tighten spacing. |
| **Contrast** | The title, secondary copy, routes, boundaries, and search outline are visibly differentiated. Smaller route text is intentionally subdued and remains readable in this capture. Numerical contrast compliance cannot be established because the JSX references unresolved `--noir-*` color tokens. |
| **Search/category relationship** | Spatially clear: query “options” (`70ON-0`) precedes “Options & futures” (`70OS-0`), with the result count immediately below (`70OU-0`). The count’s wording needs clarification. |
| **Touch affordances** | The declared geometry is adequate: close (`70MJ-0`) 44×44; Clear (`72CA-0`) 44×44; search (`70OM-0`) 48px high; category (`70OR-0`) 44px high; company CTA (`70S3-0`) at least 44px high. Result rows declare `minHeight:104px`, providing ample potential whole-row targets. Actual interactive hit areas remain unproven. |

### Repair finding

**Medium — ambiguous result completeness**

- **Node:** `70OU-0`
- **Current text:** “4 of 12 matches”
- **Visible evidence:** Four result rows are followed by the company-search footer. There is no visible continuation or explanation of the remaining eight.
- **User consequence:** A reader cannot tell whether the category leaves four matching tools, whether the screen displays only four of twelve matches, or whether twelve is the total directory size.
- **Minimal repair:** Make the denominator explicit using the actual search contract. For example:
  - If four tools match out of twelve directory tools: **“4 of 12 tools match.”**
  - If four belong to this category out of twelve search matches: **“4 in this category · 12 overall.”**
  - If twelve are still matching results and only four are presented, copy alone is insufficient: the screen needs a visible way to reach the rest.

The capture does not establish which interpretation is correct, so this should be resolved against the existing behavior contract before choosing the copy.

I found **no other mandatory visual repair** in this first pass. Result rows could optionally receive a trailing navigation cue if testing finds that users do not recognize them as actionable, but the present directory context does not justify calling their appearance a defect.

### Limits of this evidence

The **Futures** result (`70Q5-0`) does not contain “options” in its title, but its visible route (`70Q8-0`) is `/options/futures`. This could be a valid route or metadata match; the static board does not establish incorrect filtering.

The capture also cannot prove query matching, category filtering, count updates, Clear behavior, navigation destinations, whole-row activation, keyboard focus order, or accessible control semantics. Exported `div` elements alone do not establish the production implementation.

Finally, root `6ZZV-0` uses a fixed 960px height and `overflow:clip`. That is not evidence of a production scrolling defect. It does mean this capture cannot establish behavior on a shorter screen, with the keyboard open, or under enlarged text.

**No files or application state were changed.**
