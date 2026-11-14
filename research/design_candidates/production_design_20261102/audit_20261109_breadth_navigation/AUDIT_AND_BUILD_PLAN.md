# Paper design audit and build plan

9 November 2026 · Bounded amendment to [Macro #10617](https://github.com/mastermindx-market-intelligence/macro/pull/10617).

## What changed

The working designs now separate a fast first answer from the material needed to investigate it. Market Breadth has a clearer desktop summary, a much shorter phone overview, a dated session chooser, a visual explanation of the measurements and a source-aware builder contract. Government Revenue starts with its product screens and separates state examples, its large reusable component atlas and source/build material. The Mastermind OS AT00 index now acknowledges the existing Team, Conversations, Code and Settings families.

These are native, editable Paper changes. The JSX exports are visual references. Neither the exports nor this document establish installed application behavior.

The phone overview changed from 3,433 to 1,486 pixels at its existing 390-pixel width, a 56.71% reduction in board height. This is a measured design change, not a performance or usability-study result. Its detailed charts, measurements, comparison rows, coverage and calculation content remain in Full breadth analysis.

## 1. Reading hierarchy and design decisions

### Market Breadth

The original hero led with an unexplained 68/100 composite, a long qualification and three small supporting cards. The new hero leads with “Participation is broadening,” the short qualification “New highs still trail price,” and an Inspect a session action. The desktop also exposes How breadth works directly. The fixture/date label remains visible.

This is an illustrated historical state. A builder must not infer “broadening” from one latest observation or infer divergence without a named benchmark and matched historical window. The latest-only state uses “Participation snapshot.”

The index comparison now renders the existing percentages above the 50-day moving average: 57%, 53%, 62%, 55% and 49%. Bars encode those same percentages. The old composite values 68, 60, 72, 61 and 52 have been retired from current product references. The original score specimens remain on the explicitly named reference page.

Desktop secondary values remain visible: the 65.6% record-high share and the source-labelled HLI values. Retaining these original examples does not qualify an HLI formula or a production source. Its window, formula, membership and missing-value behavior still require an authoritative binding.

The phone overview now contains the primary assessment, a readable session tape, two key measurements, four analysis entries and a direct explanation entry. The four analysis entries lead to named sections of the new Full breadth analysis board. This preserves depth while removing it from the initial reading path. Long tables and detailed calculation text belong in that deeper view.

### Government Revenue

The product family already had substantial source, watch and recovery logic. The main problem addressed here was where that material appeared. The first page now contains the Signals entry and product journeys. Prepared, saved and degraded states are separate. The 11,543-pixel component atlas has a dedicated page, so it cannot obscure smaller state boards. The route map, blueprint and source-acceptance contract are together on Build.

All 28 original boards retain their identities. Five textual references were repaired to point to the component atlas on its new page. The watch semantics, funding arithmetic, source clocks, issuer mismatch handling and unknown-result reconciliation remain intact.

### Mastermind OS

AT00 previously described the current designs as pages 12–12D. Its introduction now includes pages 15–18. The grid is accurately labelled as the core workspace, while the existing Team & Delivery, Team conversations, Code workspace and Unified settings pages are explicitly listed. The existing Start here map remains the full directory. A source pointer to the existing #2345 design/build plan was added.

This correction does not re-open the recently completed product designs, change their release carrier or imply that all listed capabilities are implemented.

## 2. Native Paper destinations

Paper links open the page; use the board IDs below to locate the exact specimen.

### Breadth: 15 boards, including all 9 originals

File: [Market Breadth](https://app.paper.design/file/01M6Y3CRMC345RTB3ZDP3XSYRP/p-1-0).

| Page | Contents | Board IDs |
|---|---|---|
| p-1-0 · Product | Desktop and concise phone overview | 1-0, K6-0 |
| p-4-0 · Session choice & explanations | Session chooser; visual measurement explanation | 45R-0, 47C-0 |
| p-5-0 · Evidence · Desktop | Selected session; constituents; receipts | XZ-0, 17W-0, 1HC-0 |
| p-6-0 · Evidence · Mobile | Existing mobile session evidence | 1RF-0 |
| p-8-0 · Full breadth analysis · Mobile | Retained detailed phone analysis | 4D9-0 |
| p-2-0 · Build · Source & interaction | New overview contract plus existing accessible/source contracts | 48X-0, 2TV-0, 32X-0 |
| p-7-0 · Build · Session states | Existing detailed state contract | 2KS-0 |
| p-3-0 · Retained R1 overview · Reference | Original desktop/phone specimens | 36G-0, 3PX-0 |

### Government Revenue: all 28 boards retained

File: [Government Revenue](https://app.paper.design/file/01M6Y3397SE03G626MJ72N90PF/p-2-0).

| Page | Purpose | Key boards |
|---|---|---|
| p-2-0 · Product · Signals & funding | 21 entry/detail/variant boards | FP-0 desktop entry; V1-0 phone entry; 2B8-0 watch review |
| p-3-0 · States | Prepared, degraded and saved watch examples | 22U-0, 2QY-0, 31R-0 |
| p-4-0 · Components | Reusable funding/watch/recovery atlas | 2G-0 |
| p-1-0 · Build | Route map, blueprint, source joins and acceptance | FA-0, 1-0, 40P-0 |

The route map FA-0 and the source contract 40P-0 now reference the component atlas at p-4-0. Board identity, selected-record meaning and condition identity have not changed.

### Mastermind OS

[Canonical Atelier](https://app.paper.design/file/01M3NRCX55B452A12819WNE1RH/p-D-0), board KSB-0 / AT00. The page order and all product board identities remain unchanged.

## 3. Exact navigation contract

These are design-to-implementation mappings. Paper board IDs are design references, not proposed application URLs.

| Trigger | Destination and effect | Return requirement |
|---|---|---|
| Inspect a session | Chooser 45R-0; show the overview date and genuinely available sessions | Close returns focus to the initiating control |
| Select the Sep 24 example | XZ-0 desktop or 1RF-0 mobile; selected context is visibly Sep 24, 2026 | Return to chooser preserves selected session and its scroll |
| Constituents | Existing 17W-0 for the same session/universe | Keep session, filters, selected row and scroll |
| Coverage/source records | Existing 1HC-0 for that same context | Return to the originating evidence tab |
| How breadth works | 47C-0; explain measurement basis using clearly identified examples | Close/back restores the original trigger and reading position |
| Phone Participation & price | Full analysis 4D9-0, section 4L0-0 | Back restores overview universe, horizon and scroll |
| Phone New highs & lows | Full analysis section 4IC-0 | Same return contract |
| Phone Sectors & indexes | Full analysis section 4FD-0 | Same return contract |
| Phone Coverage & calculation | Full analysis section 4DC-0 | Same return contract |

The overview fixture is September 29. The existing selected-session evidence fixture is September 24. The chooser makes that distinction explicit. A production implementation must never open the latter while continuing to label it as evidence for the former.

Resolve route and history behavior through the existing host/inspector owner. Preserve existing deep links, browser Back, query context, keyboard focus and close behavior. Do not install a second route registry or modal stack.

## 4. Comparison with actual source

The source comparison uses Macro main at b6a683a2334498fd7731e4869fb0d0d94c424664 and Breadth #10212 at 4e072e56654bca4af9dc80af003a4a8578828cb5. These are inspection pins, not an assertion that a production deployment has those identities.

| Existing boundary | Observed responsibility | Required implementation decision |
|---|---|---|
| [templates/dashboard.html.j2](https://github.com/mastermindx-market-intelligence/macro/blob/b6a683a2334498fd7731e4869fb0d0d94c424664/templates/dashboard.html.j2) | The non-macro equity-scoreboard contains #breadth, #advanced-breadth and the #sbx-dlg full board. Its visible population is S&P 1500. | Preserve the existing Stock/D03 boundary and deep links. Do not silently substitute the Paper NYSE universe. |
| [scripts/build_site.py](https://github.com/mastermindx-market-intelligence/macro/blob/b6a683a2334498fd7731e4869fb0d0d94c424664/scripts/build_site.py) | Supplies breadth_panel via breadth_scorecard() and adv_breadth via advanced_breadth_view(). | Keep source definitions, qualification and stance ownership. A rendering change must not refit metrics or invent thresholds. |
| [templates/live.js](https://github.com/mastermindx-market-intelligence/macro/blob/b6a683a2334498fd7731e4869fb0d0d94c424664/templates/live.js) | The dashboard source describes updates to sbx-* from live/breadth.json, with the baked last-close fallback. | Reuse the existing update/fallback path and truthful observation stamp; do not add another poller. |
| [engine/live_breadth.py](https://github.com/mastermindx-market-intelligence/macro/blob/b6a683a2334498fd7731e4869fb0d0d94c424664/engine/live_breadth.py) | pa50/pa200 use eligible price/threshold bases. adv_pct excludes unchanged names. Absent members are excluded and counted as missing. | Map distinct denominators explicitly. Null and missing observations must not become below-average, unchanged or zero. |
| [Breadth #10212](https://github.com/mastermindx-market-intelligence/macro/pull/10212) | Existing breadth source qualification and the larger historical/cohort product plan. | Bind the accepted owner output and actual per-member/time/rights qualification before enabling historical or NYSE-specific claims. |
| [Government Revenue template](https://github.com/mastermindx-market-intelligence/macro/blob/b6a683a2334498fd7731e4869fb0d0d94c424664/templates/government_revenue.html.j2) | Existing government page and progressive front-end consumer. | Retain the existing product rather than building a parallel surface. Use R13 source contract 40P-0 for its already documented integration gaps. |

The existing Breadth consumer already uses a compact glance layer and a deeper full board. The new phone organization is consistent with that architecture. The critical remaining mismatch is population and dated-history capability: an S&P 1500 latest view cannot establish a historical NYSE session.

The inspected dashboard slice also contains numeric fallbacks such as advancing/declining values defaulting to zero. This pass does not establish a production defect without the upstream admissibility proof. Before migrating that rendering, prove that unknown observations cannot reach those branches, or render an explicit missing state. Do not copy zero fallbacks into the new view without qualification.

The preserved Government Revenue R13 board identifies existing Stock/Action, federation, evaluation and shared My Alerts owners. It separately identifies the proposed signal-first join, exact clock propagation and finalized-close crossing adapter as integration work. This pass preserved that contract; it did not independently re-qualify those implementations or activate a watch.

## 5. Feature viability and data rules

### Required source context

Every observation needs a resolved universe/member-set identity, session identity, price basis, source reference, observation time, applicable rights/entitlement, eligibility basis and availability state. Historical comparisons additionally require a qualified historical observation and the appropriate as-known membership/revision.

These are semantic requirements for mapping existing owner fields. They are not a new persisted schema, service, endpoint, queue or source of truth.

A fresh market-wide timestamp does not establish freshness for every constituent. Use the qualified per-member source result. Keep delayed, settled, last-observed and current observations distinguishable.

### Measurement meanings

| Display | Basis in these design examples | Production guard |
|---|---|---|
| 57% above 50-day | 1,244 / 2,182 eligible names, rounded | Require valid source price and the appropriate threshold/history eligibility. Show the denominator. |
| New highs / lows 128 / 67 | Prior 252 sessions; current session excluded | Same lookback, population, price basis and seasoning. |
| Record-high share 65.6% | 128 / (128 + 67) | Zero new extremes gives an unavailable ratio, not an invented 0%. |
| Sep 24 A/D ratio 1.79 | 1,327 / 741 | Ratio is distinct from an advancing share; zero decliners needs an explicit source-defined representation. |
| Sep 24 classified moves 2,172 | 1,327 advancing + 741 declining + 104 unchanged | Unpriced/missing names are outside this classified count. |
| Sep 24 record-high share 69.9% | 121 / (121 + 52) | Keep this dated context separate from September 29. |
| HLI | Retained original labels and values only | Formula/window/eligibility/source binding unresolved in this amendment. Do not infer a formula or derive a new score. |

No composite score, forecast, investment recommendation or trading rule is added. A source-approved historical descriptor can be rendered only when its own comparison contract is satisfied.

### Availability behavior

| Condition | User sees | Behavior |
|---|---|---|
| Qualified comparable history | Source-approved historical assessment and dated measurements | Enable supported session choices and comparisons |
| Latest observation only | Participation snapshot; latest observation date | Do not claim broadening/divergence or offer unsupported history |
| Requested historical session missing | Overview preserved; that date’s evidence unavailable | Offer only actually available sessions |
| Stale/last observation | Original observed date and a last-observed label | Do not relabel it as fresh or silently interpolate |
| Partial observation | Available measurements with coverage/eligibility | Missing entries remain missing |
| Source-rights restriction | Specific source-access state | Preserve allowed context; no misleading retry or paid-upgrade promise |
| Transport failure | Existing reader’s error/retry state | One reader/retry owner; no second request lifecycle |
| Correction/restatement | Source revision/known-at context | Do not imply the revised result was known at the original time |

## 6. Motion, illustration and accessibility

The new explanatory bar encodes the actual 57% example and displays its 1,244/2,182 basis. The new comparison bars encode their visible percentages. Geometry must remain faithful to values and missing data.

Use a restrained 180 ms transition for opening a disclosure or changing an explicitly dated context. The motion explains the state change. Do not count percentages upward, animate through missing observations, simulate live streaming or imply growing certainty.

Reduced motion uses an immediate state change. Content, order, controls, focus and announcements must remain identical. On session change, announce the new date once. Closing a sheet restores focus to its invoking control. Keyboard and touch users need access to chart values and source details without hover.

New primary actions are at least 44 pixels high. The concise phone entry cards have clear destination labels and sufficient reading room. The inherited deep-analysis specimens retain some dense typography; the future implementation still needs text-size/zoom proof, not a claim of accessibility from these screenshots.

The self-contained interaction_specimen.html illustrates normal, latest-only, unavailable, last-observed and source-restricted presentation states, plus the chooser, help, selected session and measurement basis. It includes EN/ZH copy, light/dark styles, a text-size control and reduced-motion behavior. It is deliberately an interaction specimen with synthetic source states, not an application integration.

Static HTML/JavaScript and source guards passed. Browser automation was blocked by an open Chrome extension UI before interaction verification. Browser focus, actual keyboard operation, responsive rendering, localization and motion remain unqualified. The attempted local preview tab was closed and its server stopped; no unattended process remains.

## 7. Build sequence and acceptance

### B1 — Bind source and existing consumers

Reconcile the current #10212 source head and actual release/admission state. Identify the existing Stock/D03 consumer and evidence reader. Confirm whether the qualified population is S&P 1500, NYSE operating companies or another explicitly named universe. Map actual fields and missing states before styling.

Pass: a rendered record can identify its source, universe, observation/session clocks, eligible counts and rights; unsupported history is refused honestly. No second producer, historical store, taxonomy or alert owner is created.

### B2 — Wire the reading and evidence path

Adapt the existing overview/inspector components to the approved shell and design tokens. Implement the short phone overview, Full breadth analysis anchors, dated chooser and explanation view. Preserve existing routes and one evidence identity across docked/overlay/phone treatments.

Pass: a user can reach the exact selected session, inspect its constituents/receipts, return to the same context and distinguish missing evidence from missing overview data. The September 29 / September 24 fixtures must remain a discriminating test.

### B3 — Prove semantics and interaction

Use real owner fixtures plus targeted adverse cases: no eligible observations, unchanged names, missing member clocks, unsupported universe/history, zero extremes, stale data, source-rights restriction and correction. Check that no state silently converts unknown to zero or reuses the wrong date.

Verify the real shell at 320 and 390 pixels, wider content, 200% text, both languages/themes, keyboard and reduced motion. Check focus restoration and browser history. The specimen is a starting reference, not evidence that these gates passed.

### B4 — Verify the real product path

Follow the served overview through session selection, detail, receipts and return. Record the actual source/build/release identities and applicable CI/security/review results. Retain source-owned fallback and rollback behavior.

Production acceptance requires actual served-path proof under the release owner. Green source checks, an editable Paper board, a preview or an open PR cannot stand in for that result.

## 8. Scope, remaining work and recovery

The bounded design amendment is complete when the native edits, screenshots, source exports and result record are saved/read back. The wider Paper programme and the Breadth/Government Revenue implementation outcomes remain open under their existing plans.

The next product action is B1: reconcile the existing breadth source and consumer contract, then bind population, clock, eligibility and historical capability. That action belongs to the currently assigned implementation session after its ordinary custody/source checks; no return to an old chat or named author is required.

The next browser-proof action is to dismiss the open Chrome extension UI and verify the saved interaction specimen. That is a UI-presence constraint on browser testing, not a reason to repeat the completed Paper edits.

Do not redo: the retained original boards, current phone overview, corrected comparison percentages, named detail destinations, Revenue board identity preservation or OS directory correction. Refresh only affected facts if another writer changes these targets.

The existing estate map in Mastermind #2364 remains the estate owner. This packet is evidence for the three touched files, not a replacement global directory. The target delta is Breadth 2→8 pages and 9→15 boards; Revenue 2→4 pages with all 28 boards; OS page and board counts unchanged.

