# Sector Central — Macro Dashboard design and completion plan

Date: 2026-10-20
Status: Provisional actual Macro source candidate. 565 tests across 13 named suites and three separate targeted CI checks pass. Native Screener handoff and Sector caution snapshot receipt are implemented. Unpublished; Paper edits, complete design review and browser acceptance remain unqualified.

## 1. Application authority and current result

Sector Central belongs in **Macro Dashboard**, repository **mastermindx-market-intelligence/macro**, at **https://www.mastermind-x.com/sector_central.html**. Its canonical source is templates/sector_central.html.j2 and its production builder is scripts/build_sector_central.py. Macro navigation, language and theme behavior, access boundaries and deployment remain authoritative.

The rejected Terminal replacement [#1055](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1055) is closed unmerged. Its evidence remains historical. Terminal can be an outbound destination or an optional Shared Shell host; neither changes Sector Central's native Macro ownership.

**Assigned operation:** sector-central-macro-paper-pivot-20261020-sol-001
**Branch:** sol/web-sector-central-macro-paper-pivot-20261020-sol-001
**Base:** 3667000ca153496d8ff69e8864b159ac1e7b9de0

The original acquisition response was unqualified. Same-operation publisher status and the actual worktree registry subsequently established this exact workspace and branch. All changes remain there. No replacement source carrier or raw Git publication was used.

## 2. Paper direction

The actual [Sector Intelligence Paper page](https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-Y-0) supplies the observed design references. Inspected boards include original Brief 24RC-0, Rotation 2596-0, measured Brief 6K0C-0 and authority board 24OB-0. A fresh exact-page read now shows **26 artboards and 3,840 nodes**. Root also inspected the actual Dossier desktop 6L4C-0 and Research-question desktop 6LQ6-0 JSX, plus unedited screenshots of Dossier desktop and Research-question mobile 6LSO-0. The matching mobile Dossier 6L8V-0 is present in the inventory. These observations do not confer structural-migration approval.

The candidate follows its Macro country header, horizontal workflow, open two-column Brief, restrained typography, neutral dividers, evidence chart and coverage summary. Paper's illustrative numbers were not inserted into production data. The implementation uses Macro's existing color and type tokens.

**Permanent rule: no decorative colored container edges.** The Sector candidate removes inherited container stripes, heading ticks and selected-navigation edge treatments. A scoped neutral-border rule covers legacy organs inserted after lazy loading. Chart marks, financial direction colors and functional focus indicators retain their meanings. The new Prophet context uses neutral horizontal rules.

Paper itself has not been updated by this candidate. A prior guarded authority-text mutation returned INVALID_ARGUMENT with an unqualified effect; readback remained unchanged. **This connector's fresh catalog** still reports accepted_for_write=false and catalog_compatible=false: observed 1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db versus expected ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9. The client now exposes paper_prepare; its earlier absence is superseded. The original #9592 parent reports an accepted catalog on its own connector, so this is a scoped qualification discrepancy, not a global Paper outage. Exact-target reads and write_binding_ready remain true here, but do not override the unaccepted write receipt. Reconcile this same connector/operation before another mutation.

### Remaining Paper product work

The newer Dossier uses the same Macro header, neutral dividers, open two-column hierarchy, compact company-return bars and a clear distinction between sector strength and a stock's own entry read. It retains source order, source dates, supplied-group identity and the explicit absence of a demonstrated Technology–Semiconductors relationship. Its September 23 numbers are historical design fixtures, not new market data or verified ETF holdings.

The newer Research view organizes three questions around participation, company evidence and shared exposure. Its action prepares an **unsaved editable question** in the existing research workspace; the Sector snapshot is not retained with that question. My watches means symbol saving, not condition-alert delivery. These Dossier/Research desktop and mobile journeys still require native source/receiver integration and exact browser proof. The candidate's current Research/Watch links retain existing instruments while that work is unresolved. No saved-research store, alert service or fabricated relationship is implied.

## 3. The native workflow

The question sequence is **What is changing? → Where is it happening? → What evidence supports it? → What deserves watching?**

| Native destination | Visible label | Purpose and retained capabilities |
|---|---|---|
| #overview | Brief | Leadership, chart and coverage summary, action board, trace, regime and grader |
| #map | Market map | Rankings, measured changes, cycle map, sector detail and overlays |
| #moving | Rotation | Rotation map, events, early observations, accumulation and desk watches |
| #money | Breadth & money | Breadth, internals, money-flow evidence and concentration |
| #explore | Themes & compare | Basket table, comparison chart, narratives and Time Machine |
| #confluence | Entry evidence | Existing S&P 500, Nasdaq-100, Russell-2000 and thematic universes |
| #tm-mount | Research | Existing Time Machine within Themes & compare |
| #accumulation-section | Watches | Existing accumulation instrument within Rotation |
| #si-measured | Review sector evidence | Existing measured-sector panel within Market map |

Brief / Explore / Research / Watches are the primary workflow. Explore exposes the five evidence views. Research and Watches reach existing instruments; they do not imply a new saved-research database, persistent watch service or notification delivery.

All six router identities remain. The original 21 anchors, the two existing runtime aliases and the new measured-panel alias total **24**. Theme links, read-trace links, mount IDs, si:view and language events remain. Views are made visible and synchronously measured before lazy chart loading. templates/si_workspace.js and site/si_workspace.js are byte-identical.

Existing capability inventories remain inputs:
- research/reference_integrity/mastermind-xpv2-sector-r3/capability_disposition_ledger.md
- research/redesign/SECTOR_CENTRAL_20261018_CAPABILITY_CROSSWALK_DRAFT.md
- research/redesign/SECTOR_CENTRAL_20261018_PAPER_ACCEPTANCE_DRAFT.md

Their application and acceptance assumptions must follow this Macro correction.

## 4. Implemented evidence and truth conditions

### Brief chart

The Brief uses the existing leadership state and first strength subject supplied by the source context. It introduces no new ranking or stock-entry recommendation. Unknown leadership and absent market-concentration verdicts remain explicitly unmeasured.

The chart binds the exact basket ID to BASKETS.chart.baskets and the existing benchmark, aligned to BASKETS.chart.dates. It calculates relative wealth:

    ((group_close / group_start) / (benchmark_close / benchmark_start) - 1) × 100

The window is **20 observed session intervals using 21 matching closes**. It is neither a percentage-point return subtraction nor the separate producer's rs_21d measurement. The complete tail must have aligned arrays, positive finite closes and valid, strictly increasing ISO dates. Invalid or missing observations produce an unavailable state. The actual start/end dates and endpoint are printed.

US sector baskets are identified as equal-weight baskets, distinct from sector ETFs. Theme baskets remain identified as baskets. No historical-membership or intraday-currentness guarantee is inferred from this chart.

### Measured-sector coverage

The neutral summary below the chart consumes the existing **SECTOR_CENTRAL.measured_read** projection independently of basket initialization. It loads immediately after the synchronous Sector payload and makes no additional request.

It checks the declared schema, display-only authority, SPY benchmark, price basis, us_sectors_11 cohort, 63-session horizon, exactly 11 unique canonical ETF identities, measured metric/units, finite values and reconciled coverage/missing counts. All ranking, gating, sizing and trade-authority flags must remain false.

Missing, unavailable, invalid, missing-date and incompatible-date inputs are distinct states. A valid zero-measured cohort remains 0 of 11. An older measurement retains its actual date and is labeled as older than its source page. This read is separate from the 20-interval basket chart.

The actual checked-out input yields **11 of 11 measured sectors**, **63 sessions**, **total return**, **evidence date 2026-10-16** in both languages. The full existing panel remains the destination for numbers, reconstruction and recorded events.

## 5. Prophet: established connections and implemented handoff

The correct general destination is **us_stocks.html**, whose canonical renderer is templates/dashboard.html.j2 in stocks mode. The old #prophet-live target is a conditional intraday “Forming today” strip; it was hidden during the public-page inspection. It is not the general Prophet board. The us_stocks_v2 template is an unlinked shadow preview.

### Existing backend connections established from source

| Connection | Actual owner | Qualification |
|---|---|---|
| Sector conviction into stance context | scripts/build_stance_matrix.py | Reads Sector ticker, conviction label and as_of; existing five-calendar-day freshness rule omits stale/missing Sector input |
| Basket/ETF proxy mapping | Same stance builder | Retains registered proxy/fallback identity, including SMH → XLK |
| Published stance context | site/mlcdata/stance_matrix.json | mlc.stance_matrix.v1; display-only tier mappings |
| Theme-card mixed/split reads | templates/baskets_desk.js | Existing bilingual explanation chips consume the stance matrix |
| Sector caution on Prophet buy cards | scripts/build_site.py::_attach_board_display_chips | Canonical GICS_TO_ETF join attaches sector_stance and sector_stance_zh in memory |
| Prophet caution presentation | templates/_us_board_cards.html.j2 and _prophet_card.html.j2 | Reduce/Cautious Sector reads enter the existing single-stock caution popover |

The public Prophet DOM corroborated existing Health Care and Financials/Technology caution text. This establishes display-context consumption, not Sector participation in Prophet's origination, stock ranking or entry decisions. The new candidate now carries the direct caution's own Sector snapshot identity/date, described below; it adds no new freshness policy.

### New implemented identity roundtrip

Selecting a canonical ETF in the existing measured panel exposes a native link:

    us_stocks.html?si_sector=<ETF>#sector-prophet-context

The actual Macro stocks template now hosts a neutral “From Sector Central” context row outside stock-card, Today, Plan and hydration owners. Its shared controller accepts one exact canonical ETF identity. Duplicate, unknown or malformed selections produce an explicit invalid state. Labels come from the existing canonical sector mapping, and rendering uses textContent.

The return link is reconstructed internally:

    sector_central.html?g=<ETF>#map

Clear context removes only si_sector, retaining unrelated query values and native fragments; its own context fragment returns to #us-standouts. The controller rereads location on Back/Forward and the Shared Shell acknowledgement event, and uses the existing language event. It writes no history, makes no requests and changes no card ordering, ranking, gating or entry state. URL values cannot supply measurements, dates or an arbitrary return destination.

The actual source-data probe traces **XLB → Materials · XLB in Prophet → XLB in Market map** through the shipped controllers. All 11 identities also pass fixture-based roundtrip tests. These are DOM-harness/source-composition results, not a browser acceptance claim.

### Implemented native Screener action

The context row now has an explicit **Show sector in Screener** action. It becomes available only after both native owners exist: the US table's selection API and USProphetSource.set. Each owner announces availability. Arrival, language changes, navigation and hydration never automatically apply a sector filter.

The shared StockTable.init now returns a per-instance sector controller. Its setter validates against the actual dropdown and delegates to the native selector, counts, pagination and renderer. Only the US owner opts into the 11 registered canonical sector choices and the truthful zero-result message. Other market callers retain their original option and empty-state behavior.

The US action validates the canonical GICS identity, applies that native filter, chooses the existing candidates source and table view, then focuses the native table control. Existing reader filters remain in the filter intersection. Hydrated-row replacement captures and restores the **current** sector selection, including a manual clear or change; the baseline behavior of other filters during hydration is unchanged.

The source chain is established: build_stock_library normalizes the two legacy aliases and filters spurious nonempty classifications before publication; us_board_rank preserves those row identities/order semantics; build_site uses the same row sector in the public/locked split and table presenter. Missing or unknown classifications are not relabeled into a canonical sector.

The actual checked-out public table contains **three rows**. Selecting **Materials / XLB** yields **0 of 3 loaded matches**, eleven available registered sector choices, the native candidates/table state and: “No matching stocks in the loaded table. Clear filters to widen the view.” It makes no extra request and does not manufacture a complete or entitled population. The shipped source/view and filter/render functions were exercised in a DOM harness; a browser journey remains unqualified. Both stocktable assets are byte-identical.

### Implemented Sector snapshot receipt on existing Prophet cautions

scripts/build_site.py::_attach_board_display_chips still performs the existing canonical GICS-to-ETF join for buy-card display. Each matched row now carries sector_stance_source/v1 with the exact matched ETF and a strictly validated top-level Sector snapshot date. It does not substitute measured_read.history_as_of, a stock signal date, a board date or the build clock.

The existing Reduce/Cautious warning appends “Sector snapshot date (ETF): YYYY-MM-DD” in the **same bilingual caution row**. Invalid or missing dates preserve the warning and display an unavailable date. Reattachment clears the old receipt before reading a replacement or missing sidecar. Existing legacy stance behavior remains intact; no new warning count, rank, gate, score or freshness classification is introduced.

The source probe used the real checked-out inputs: **101 buy rows** all matched their existing sector join; **29** had Reduce/Cautious stances. The example XLV caution renders a **2026-10-16** Sector snapshot while the Prophet board retains **2026-10-14**. All other fields and ordering remained unchanged. The actual attach and US card partial ran with unrelated display enrichments isolated. This is not a full production build, immutable generation receipt, per-sector assessment timestamp or synchronized-clock guarantee.

A deeper measurement-level context must retain each reading's own identity, benchmark, window, basis and date. The composite caution snapshot cannot supply those distinct measurement clocks or establish stock-entry authority.

## 6. Preserving and exposing the robust intelligence

The incumbent rotation, turn and grading engines remain the source of truth. This candidate changes presentation and navigation, not their algorithms or source payloads.

| Next display increment | Source detail to preserve | Interpretation to protect |
|---|---|---|
| Basket provenance | Existing coverage, live/stale-member counts, ETF proxy and membership basis | Live-member count is not registered population; current membership is not point-in-time reconstruction |
| Fast / slow comparison | 21-session strength, 63-session strength, source conviction and their separate rank populations | Do not collapse fast rotation and slow conviction or treat price-relative motion as observed capital flow |
| Turn windows | Last confirmed anchor, peak/trough kind, central date, low/high timing range and overdue status | Historical spacing bounds are not calibrated confidence intervals; overdue windows stay anchored |
| Early rotation context | Two-session pair coverage, missing legs, both-up/both-down cases and own observation date | Early context remains separate from confirmed events and sector confirmation |
| Recorded-event receipts | Exact identities, event start, event date, recorded-at time and reconstruction mode | A page refresh must not make every evidence leg appear current |

These are bounded preservation/exposure requirements from source review. They are not delivered algorithm improvements or predictive-performance claims. Any model change requires separate point-in-time, missing-data, benchmark and out-of-sample evidence.

## 7. Verification and evidence

The evidence directory is design_refs/sector-central-macro-paper-20261020/.

| Check | Actual result |
|---|---|
| Thirteen named Sector, Screener, compatibility and caution-display suites | **565 passed in 45.35 seconds**; exit 0 |
| Three targeted manifest/gate/packing tests | **3 passed in 116.10 seconds** |
| Added-line design-system gate, including all seven new partials | Passed, zero blocking additions |
| Runtime style-injection gate | Passed within existing allowances |
| Whitespace and paired router / stocktable assets | Passed; both pairs byte-identical |
| Actual Macro Sector template render | 581,154 bytes; successful |
| Five core source inputs before/after render | All hashes unchanged |
| Actual coverage and native Screener probe | Passed; dated 11-sector read, XLB roundtrip and honest 0/3 loaded-table result |
| Actual Sector caution source/render probe | Passed; own Sector/Prophet dates, bilingual receipt, other fields/order unchanged |

Final Sector render SHA-256:

    7a1b170f459c96df943dcd0095a671d3b370ad51b3b7062ba1e8431f27e1d29a

The review renderer uses actual checked-out payloads and the canonical builder's read/context helpers. It does not call Sector Central compute, grade calls, write a premium payload or publish production. Baskets/source-generation date is 2026-10-14; Sector evidence is 2026-10-16. A later page/build time does not replace those observation dates.

CI registration retains the literal test invocations. Comparing HEAD and candidate manifests on the same source tree produced identical selected job IDs for every packing probe. Only public-render-fastlane changed weight, 24 → 30, from the three new explicit suite paths. The exact free-content ceiling was funded from 5664 to 5670. Other weight bounds, job bounds, selectors, all suite execution and the ten-pack ceiling remain. The existing exclusive countercase owner now declares its shared JS dependency.

The final candidate-test-receipt.json records all 13 suite paths, the exact argv, timestamps, source-file hashes before/after and the pass-log hash. The checked source set did not change during the run. Its aggregate SHA-256 is 04237259b7ec0d741e2a28b474603d65581a7b651f0e409384ee43a14e3d5290. This is selected local verification, not all repository tests or hosted CI.

The initial expanded run had nine failures. An isolated copy of the exact untouched base reproduced those same nine failing node IDs: stale non-US template pins and the US table helper's missing native macro import. The HK/Intl pins were reconciled to proven unchanged base bytes; the actual FileSystemLoader/native import replaced the incomplete render helper without removing assertions. Those three compatibility suites then passed **60 tests**, and are included in the final 565-pass run. Historical baseline failures remain in separate receipts, not as unresolved candidate failures. The StockTable pin reflects the explicitly reviewed shared asset change.

A selected-sector link also exposed a Chinese-copy assertion that included href text; it now extracts rendered text while retaining every English-twin prohibition. Separate focused increments passed 98 Screener tests and 149 Sector-caution/adjacent-display tests; those overlap the final run and must not be added to its count.

## 8. Browser, Paper and publication boundaries

The public baseline pages were inspected in the Browser plugin. The native measured panel displayed its own 2026-10-16 evidence date and 11-sector coverage. The Prophet board showed its separate delayed-price disclosure and existing Sector cautions. Those were incumbent pages, not this candidate.

The source host served the candidate review page with HTTP 200, but the connected browser's loopback navigation returned net::ERR_SOCKET_NOT_CONNECTED. There is no candidate screenshot, mobile/theme matrix or full browser-interaction acceptance. The temporary review server was stopped. No alternate hosting or access-policy workaround was introduced.

The managed commit request returned:

    REFUSED / TYPED_GIT_PRECHECK_REFUSED / NOT_APPLIED / INVALID_ARGUMENT

Same-operation status retained base HEAD, no remote branch head, a dirty workspace and publication_state=NOT_APPLIED. No commit, push, Macro PR, merge or deployment occurred.

Read-only publisher source diagnosis found a generic precheck catch that discards the failing stage. Macro enrollment and the inspected argument shapes do not establish the cause. ready_to_push=false is expected for a dirty workspace and is not a diagnosis. The publisher needs a sanitized failing-stage/exception receipt before another commit attempt; no blind retry was made.

A fresh read-only main refresh at 11:10 UTC observed **4290a79a222da944dbee0b438474029d67d0c4b2**, **66 commits ahead**, with 16,003 changed paths. Candidate overlap is **.github/ci/legacy-jobs.yml**, **scripts/build_site.py**, and **tests/test_ci_pack.py**. The existing caution-enrichment function itself is byte-identical between the base and that observed main; this does not replace integration of the complete builder. The workspace has not been rebased or merged. Compose the actual current-main builder/CI changes and remeasure the combined budget before release. Older six-ahead/no-overlap and 35-ahead/two-overlap observations are superseded.

## 9. Related carriers and completion order

[#7949](https://github.com/mastermindx-market-intelligence/macro/pull/7949) remains an open Shared Shell integration at observed head e2d10f933587f58be8716505529a37f8839901f7. It preserves native Macro ownership and the six Sector routes. Its dashboard/router overlap needs normal composition and served-tree acceptance.

[#9495](https://github.com/mastermindx-market-intelligence/macro/pull/9495) remains a draft opportunity/setup carrier at observed head 0661c53d2af2b3995163aef08e3b8ba285fc4e39. Keep this context receiver outside its cards, Plan/setup return and daily-brief owners. An open PR is not proof of an active writer.

Compact-card restoration [#9566](https://github.com/mastermindx-market-intelligence/macro/pull/9566) merged. Its older hold repeated in #9035 is superseded; source merge and production acceptance remain distinct. [#9592](https://github.com/mastermindx-market-intelligence/macro/pull/9592) merged earlier design references, not acceptance of this new candidate.

Original repair carriers #7595 and #7076 keep their own custody and unresolved asset/error/truth/localization work. The refusal around #7579 remains scoped to its denied audit/matrix/scanner actions; this candidate does not replay them through another carrier.

### Reference-integrity status reconciled on the original parent

The old notice that three October 18 migration packets still block dependent carriers is superseded. Root read the current original [#9592 dependency record](https://github.com/mastermindx-market-intelligence/macro/pull/9592#issuecomment-6248814344), the landed DEC-UNAPPROVED-SECTOR-DOCUMENTATION-DEADMISSION decision and the current candidate README. Those original proposal blobs remain preserved under research/design_candidates/sector_central_20261018; the false executable admission was withdrawn. No second packet repair or replacement approval is needed.

**Full RIG for this structural migration remains owed.** It requires the actual frozen before/after artifacts, the complete 92-capability scope, independent Product Regression and Visual/Taste reviews with rationale quarantine, and the designated design authority's verdict/approval bound to the judged bytes. The current code tests, C3 source counsel, Paper screenshots and historical packet de-admission are not substitutes. Candidate status stays provisional; no compliance or approved-reference claim is made.

Completion requires, in order:

1. Reconcile the managed publisher and accepted Paper write boundary on this same operation.
2. Compose the builder and two CI overlaps against qualified current main; preserve all test execution and measure the combined budget.
3. Update the same Paper authority/final design, including the remaining reference stripe; finish the Dossier and Research receiver/source contracts in the existing Macro workflow.
4. Obtain a reachable preview of the exact Macro candidate. Freeze the actual production/proposal comparisons and complete Full RIG, including 92-capability dispositions, independent reviews and genuine approval; prove desktop/mobile, light/dark, both languages, access states, retained instruments and new journeys.
5. Complete source review and concluded CI on an actual Macro PR.
6. Use the canonical Macro build and deployment lane to produce and qualify the paired generated pages/assets.
7. Verify the served canonical Sector page, all six hashes, the measured deep link and the actual Prophet handoff.
8. Complete the remaining Dossier/Research journeys and qualify any stronger measurement-level or Prophet decision-consumption claim with its own evidence. The native Screener action and caution snapshot receipt are complete in this source candidate; no model-validation or full-system acceptance is implied.

Durable project checkpoint: [Macro #7646](https://github.com/mastermindx-market-intelligence/macro/issues/7646#issuecomment-6247254582).

A passing local candidate, a Paper update, a browser pass, a merge and a live release are separate results. The present result is the verified Macro source candidate and its review package.
