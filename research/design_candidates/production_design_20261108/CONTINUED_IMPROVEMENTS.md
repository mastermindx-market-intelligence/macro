# Continued Paper improvements — 8–9 November 2026

## Current assignment and source
The Chairman explicitly extended the estate mission: continue auditing, fixing, implementing and enhancing the existing Paper designs autonomously. This record continues PR #10864 and the wider #10617 programme. It does not create a second programme or claim a product release.

Protected Mastermind procedure pin remains 5c3d3885234358aefb97ecdbc59be0864df14f8b. Breadth, Policy and CPI checks use Macro b5674d8ef898e503d6164922654f5ff89be9981c; the subsequent Bonds audit refreshes its affected files at aec7f387badcdf69c9a947fafbc73b4c68470c7d. The earlier audit's 338a1085 baseline and accepted results remain historical evidence and are not rewritten.

The current census returned 82 resources, versus 37 in the first pass. MASTERMIND PAGES has been relabelled “MOVED - Navigation only” and separate family/reference files are present. Their presence is not a claim that every migration or copied journey has passed acceptance. ESTATE_INVENTORY_CONTINUATION.json preserves the observed inventory, including actual archived flags separately from names.

## Verified phase: Breadth session inspection, arithmetic and build viability

Paper file: https://app.paper.design/file/01M6Y3CRMC345RTB3ZDP3XSYRP/p-1-0
New interaction/build page: https://app.paper.design/file/01M6Y3CRMC345RTB3ZDP3XSYRP/p-2-0

### Native changes
- Existing desktop 1-0 and phone K6-0 now say “Market breadth” and expose an explicit Inspect a session action. The phone action has a full 48px target. The blanket “Data complete” claim became the fixture's 97.2% priced coverage.
- The one-session formula is now Record-high share: 128/(128+67)=65.6%. Display values, explanation and gauge markers agree. The unsupported 4.6-point delta was removed. Raw-share buckets describe the share of new extremes rather than an inferred market regime.
- A new phone session view, 1RF-0, contains explicit previous/date/next controls, 1,327 advancing / 741 declining / 104 unchanged, 1.79 A/D ratio, 121/52 new extremes, 69.9% raw share, the exact existing illustrative index readings and constituent/source actions. It is a proposed design, not a wired app.
- New build/state board 2KS-0 defines selected-session identity, dated-list selection, exact return/focus, six evidence outcomes, source owners, phased implementation and concrete acceptance. It includes a visible session chooser.
- Three chart regions now share one deterministic SVG generator and an explicit illustrative fixture. The Sep 24 marker is geometrically consistent with 108.7 and 106.2. The old hand-positioned plot was not consistent with those numbers. Non-selected chart points are deliberately authored synthetic design context, not retrieved market history.
- No numeric gap between differently constructed series is called a return, prediction or validated lead. Production must qualify the rebasing method and handle a zero/negative A/D baseline.
- The existing desktop inspector's left chart and summary strip were updated. Another admitted writer changed its right evidence panel during this pass, adding Summary / Constituents / Receipts. Those new nodes and their additional artboards 1HC-0 / 17W-0 were preserved. Our prior text receipts do not prove that a later writer retained those exact words; do not claim the current entire right panel as our completed correction. The new phone and build board carry the corrected raw-share contract.
- Finish was scoped to our new boards and exact chart/gauge/action groups, not the concurrent writer's evidence-panel subtree.

### Source findings that change what can be built
At the exact Macro pin:
1. engine/advanced_breadth.py::high_low_index emits separate raw record-high share and a rolling high-low index. Default window is 10 retained rows with at least five valid ratio observations. It averages daily percentages, not pooled counts.
2. NH+NL=0 makes raw share undefined. The current source can select a prior non-null value while an outer payload uses the latest frame date. A dated inspector must qualify the actual contributing observation date and cannot silently carry the old value into the selected day.
3. collectors/breadth.py uses current S&P 500 constituents and reconstructed history. scripts/build_site.py::advanced_breadth_view reads S&P 500 data; breadth_scorecard combines S&P 500/400/600. LIMITATIONS.md expressly distinguishes this from true NYSE breadth. The NYSE UI remains a proposed source integration.
4. A nightly composite may skip missing tiers and use the maximum tier date. Same-session / complete-universe labels require explicit evidence. Reuse engine/live_breadth.py::evaluate_usable for the existing live replacement gate; do not create a second browser policy.
5. Eligibility differs for priced, prior-close, MA50, MA200 and NH/NL observations. Not all denominators are currently exposed. A new funnel requires a producer-projection extension; the browser must not reverse-engineer counts from rounded percentages.
6. Existing advanced sparks are value-only. A dated point inspector needs a bounded dated projection through the existing owner. Reuse templates/charts.js range behavior and templates/macro_suite.js evidence-drawer interaction.

### Build sequence and acceptance
First qualify the existing S&P universe and metric-specific values. Next extend the existing projection with dates, source version, eligibility, raw/smoothed values and source references. Then bind chart, date list, numeric table and evidence drawer to one selection. Full NYSE requires a verified roster/history/identity/delisting/split contract. Do not manufacture a NYSE feed by relabelling current-member S&P data.

Verify actual consumer selection by tap, keyboard and date list; retained-session boundaries; same universe/date/value throughout; true zero counts versus undefined ratio; missing session versus prior reading; partial windows; mixed tier dates; unavailable member details; source-version change; dismissal and focus return. Check 320/390px and enlarged text, EN/ZH, and reduced motion. Those are implementation acceptance gates, not claims this static Paper pass completed them.

## Verification and limits
- Native screenshots were inspected for the new phone view, full build board, corrected overview and exact chart region. A fixed-height cloned build board initially clipped later sections; it was converted to fit-content and the full resulting board was visually verified.
- build_breadth_chart.py executed locally. Three SVGs XML-parse. Arithmetic checks: classified moves 2,172; A/D ratio1.79; shares69.9%/65.6%; selected numeric gap2.5. SVG marker geometry agrees with the fixture.
- One rename request returned INVALID_ARGUMENT. The original names were read back unchanged; a reduced single-node request with a shorter name/correlation identifier succeeded. The underlying argument cause was not proven. No blind retry or unknown effect remains.
- No production code, deployment, merge, archive/delete, runtime gate or external message was performed. The earlier inline-browser execution denial remains fenced; no carrier workaround was attempted.
- Paper/source execution receipts are in PAPER_CONTINUATION_RECEIPTS.json. They distinguish response observation from visual verification and installed-product acceptance.

## Verified phase: Policy mobile controls and narrow chart evidence

Paper: https://app.paper.design/file/01M6Q4WK0EMPV1G2KDGGRQBC1B/p-1-0  
Build reference: https://app.paper.design/file/01M6Q4WK0EMPV1G2KDGGRQBC1B/p-2-0

### What changed
Ten English/Chinese mobile disclosure labels are now full-width targets of at least 44px: source notes, rate values, Fed projections, Sources, and Methodology. Each contains one label and its canonical theme chevron. The chart SVGs fit the existing mobile cards without changing their viewBox, values, dates, or legend. Chinese unknown-publication copy now plainly says the Fed projection publication date is unverified and a numeric comparison is withheld.

Build amendment 12K-0 adds paired 320px EN/ZH components, numeric-disclosure controls, and exact native details/summary ownership. In the narrower Paper specimens the 340×234 viewBox is resolved to 268×184.45; the build contract requires proportional responsive sizing. This avoids the extra vertical space left when Paper retained the SVG's original intrinsic height.

### Current collaboration and limits
The compact historical channel/context summaries and expanded reference bodies were created by another active writer and preserved. We did not redo or claim those changes. Existing #10493 source notes, October 30 reference values, July 18 narrative review, uncertain-effect custody and release controls remain with their existing owners. The native amendment does not prove that candidate's deployment.

Screenshots verified the 390px chart cards, full disclosure targets and the paired 320px components. Full-page browser zoom, actual keyboard behavior and native disclosure interactions are still consumer proof, not Paper screenshot proof. The existing numeric table and dialog owner remain authoritative; no asynchronous request, new Escape handler, or operation lifecycle is added.

## Verified phase: CPI period selection and exact-reference outcomes

Paper workflow: https://app.paper.design/file/01M6PXFEP1E1T59M2B3N673PMG/p-4-0  
Existing build contract: https://app.paper.design/file/01M6PXFEP1E1T59M2B3N673PMG/p-3-0

### Native changes
New board 1F2-0, “R3 Period chooser and reference outcomes”, has matched 320px English/Chinese inline choosers. Search and native single-choice selection stage a draft; Show history explicitly applies it. The shown query is 1987-01, with the already selected January 1987 month marked Current. No neighboring months or revision counts were invented.

The manual copy fallback retains the existing exact key, zero-based row, record-read clock, full fingerprint and unspecified cutoff. It uses the same selected-reference payload contract; it does not introduce a second serializer. English/Chinese success and failure copy distinguish completed clipboard writes from source verification, receipt binding, saving or synchronization. The dark clear-search icon was visually corrected after the first render.

Six behavior specimens distinguish invalid month, a complete-index no-match outside the retained range, incomplete index lookup, pending selected history, failed history read, and complete zero/one/multiple-record outcomes. Pending January 1947 uses the manifest's real minimum key and displays no invented values or revision counts. January 1987 remains the committed history until a qualified result is ready.

Existing V1-0 text now accurately separates the implemented collector, bounded reader and pure comparison engine from the missing CPI consumer integration. Its entry/return contract uses the active period rather than hard-coding the January example. The full-matrix binding, explicit CPI comparison rule, unavailable-version recovery and incumbent page-path work were preserved.

### Architecture and exact evidence

At Macro b5674d8ef898e503d6164922654f5ff89be9981c:

- The CPI manifest records 293,509 rows, 956 actual periods and 377 distinct vintage dates; period endpoints are 1947-01-01 and 2026-09-01. There are 957 calendar months between those endpoints, so a generated continuous calendar would invent availability. These are whole-archive counts, not January 1987 counts.
- The selected full archive fingerprint is eabad732825e9d6820774f067e8f86791cc3f64a6a81b655522af621c851f22c. statv1 is a reader file-version guard, not a verified content hash.
- The internal Market Memory intake retains a newest-vintage slice. It cannot substitute for the full vintage matrix when reopening historical operands.
- The bounded reader's row_positions, next_offset and scan_complete determine lookup progress. Follow its returned offset; a partial empty result is not absence.
- engine/rates_command_basis.py remains the pure comparison owner. Its QualifiedObservation can represent CPI identity without stock security/listing IDs. The generic same_basis_level_change.v1 rule defaults to bp and lacks explicit reference_start/reference_end matching. Preserve that rule and bind the explicit CPI contract with same-period matching, source-backed basis and output_unit=index_level. Since the engine computes left minus right, the CPI adapter must bind later as left and earlier as right.
- The displayed 111.5 / 111.4 values and row 180960 are retained from previously accepted evidence designs. This phase did not re-read those corpus rows. Unknown basis still withholds the real-pair difference.

Exact sources:
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/data/fred_vintage/release_targets/manifest.json
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/lib/dataos/web_readers.py
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/lib/dataos/web_workspace.py
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/engine/neuralweb/market_memory_sources.py
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/engine/rates_command_basis.py
- https://github.com/mastermindx-market-intelligence/macro/blob/b5674d8ef898e503d6164922654f5ff89be9981c/app/gmi_bea_view.js

### Implementable interaction contract
Keep committed context and picker draft under the incumbent page state. Search only filters the actual, content-bound period index. A current-month apply closes with no redundant read. For a different verified month, retain the correctly labelled current history while reading; commit the new period and its qualified history together. Clear or explicitly reselect comparison operands. Do not change the source version or cutoff to make a request succeed.

Cancel discards the draft and restores the Period control. Cancelled or superseded responses cannot commit through the existing request/context guard. Use a labelled input, native radio results and explicit actions; no separate modal or focus trap. Respect IME composition. Preserve access-denied, fingerprint-mismatch, source-change and unavailable-version distinctions already designed.

The structured CPI_PERIOD_FLOW_CONTRACT.json records the sparse fixture, invariants and acceptance cases. A production proof must include a real non-January history from the exact archive; the design does not fake that step.

## Source preservation and delivery

This continuation uses the existing PR #10864 branch. The preceding Breadth milestone is 65a339d04a31110def1db5d4835e12db7119e5d3. Paper's Breadth build board now visibly links to that immutable report. Changes since it are recorded in the continuation receipts; no production implementation, merge or deployment is claimed.

The attempted individual check-run REST read returned INVALID_ARGUMENT because that URL shape is unsupported by the connector. This is a connector schema limitation, not proof of a new CI failure or a permission denial. The earlier inactive-context result is historical and is not asserted as current-head evidence.

## Verified phase: Bonds evidence, source semantics and touch workflows

Current journeys: https://app.paper.design/file/01M6Y3RNXNXP3YX0NFBT0YEXS4/p-1-0  
New source/recovery page: https://app.paper.design/file/01M6Y3RNXNXP3YX0NFBT0YEXS4/p-2-0

### Corrected the displayed story
The selected five-session fixture has 3M and 2Y yields falling 2 bp, 10Y nominal yield rising 18 bp, 10Y real yield rising 12 bp and HY spread widening 6 bp. R10 had said the front end was rising and that recession evidence was not rising. Those claims exceeded or contradicted its displayed inputs.

Desktop 2H1-0, phone GJ-0 and tablet JP-0 now lead with “Real yields rose. Credit spreads widened.” Their supporting copy states the actual changes. The policy/real-rate and growth/cut hypotheses use neutral UNCONFIRMED badges until their evidence rules are qualified; the disproved “front end is not rallying” explanation was removed. The 21-day and 63-day curve examples remain explicitly separate windows.

The phone/tablet now identify the illustrative status before the conclusions and show 18–25 Sep / 5 sessions above the move table. Their Evidence and Inspect explanations actions have full 44px/48px targets. Original label-node IDs HR, KX, JG and MM were preserved. Recent navigation work by another writer was left intact.

The migrated R2 build references now point to local Briefing NL-0 and Studio U8-0, with current R10 board IDs alongside them. A source/recovery addendum points to the new build page.

### Added evidence views without duplicating ownership
- 3I2-0: read-input overview. It lists nominal yield, real yield and credit separately, then expands the known 10Y nominal example (4.28% → 4.46%, +18 bp). It does not borrow nominal-yield evidence or cadence for the other inputs. The lack of a live source receipt stays visible.
- 3C6-0: controlled partial-composite coverage. The score remains 74; 3/5 inputs and 70% configured weight are available. The valid zero-stress rates-volatility input remains available. Component observation dates are not invented.
- 3FC-0: build contract with signed FINRA net evidence, coverage, curve sample dates, compatibility, four acceptance fixtures and exact source links.

The generic headline / What changed Evidence action opens the read-input overview; a selected curve action can open that tenor directly. Coverage links share one coverage overview. Explanation links start from the hypotheses and pass a selected explanation only when the user chooses one. One incumbent inspector owns source snapshot, country, metric/tenor, endpoints, window, origin, scroll and focus return.

The health-composite specimen is one coverage section, not a substitute for every input behind the current R10 read. Market-source failures and manual duration-input failures keep separate state families. The existing duration, shock and input-error specimens were preserved.

### Current source findings and compatible build plan
All four affected Bonds files were refreshed at current main aec7f387badcdf69c9a947fafbc73b4c68470c7d and were byte-identical to the earlier b567 baseline.

**FINRA:** engine/credit_momentum.py computes (fiftyTwoWeekHigh − fiftyTwoWeekLow) / totalTrades. scripts/build_bonds.py applies abs, labels the magnitude as lows_pct, and exports it as finra_lows_share; the template says “touched 1-year lows.” Add the correctly signed observation and its metadata under the existing projection. Retain the legacy nullable key, stop manufacturing it from net share, supply an explicit unavailable reason, and verify every consumer handles null before rollout. Do not silently drop the key or rewrite retained historical payloads. The denominator field is observed; its universe meaning remains unverified.

**Health:** engine/bonds.py renormalizes over available weighted legs. Preserve that calculation and expose active/expected positive-weight legs, available/expected weight, coverage fraction, calibration/prior basis and per-component source dates. Older payloads without coverage are unknown, not complete. Do not invent a new score threshold or collapse the three R10 questions into one composite.

**Curves:** the current builder samples frame rows −1, −64 and −252 and suppresses a role with fewer than four valid tenors. Keep that behavior while adding actual sampled dates, roles, offsets, nullable tenor values and explicit insufficient-data states. Frame dates and original per-tenor observation dates are distinct.

Exact sources:
- https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/credit_momentum.py
- https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/bonds.py
- https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_bonds.py
- https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/templates/bonds.html.j2

### Executed source characterization
verify_bonds_source_contract.py checks exact SHA-256 hashes, extracts only the named pure functions and the existing health-arithmetic AST block, and executes them with controlled inputs. It imports no repository module, runs no collector, and performs no browser work. The local run used pandas 2.2.3 and numpy 2.3.5.

The run reproduced:
- Net values −0.20 and +0.20 remain opposite in the raw view-model field but both become lows_pct=20 and machine finra_lows_share=0.20.
- The current view model preserves valid numeric zero versus missing; the proposed correction must retain that distinction.
- Available stresses 20, 40 and 0 at weights .30, .30 and .10 give 74.2857… → 74 with available weight .70. A denominator of 1.0 would incorrectly give 82.
- A controlled build on 16 October with sampled rows 14 October / 10 July / 30 September 2025 produces “Today” / “3 mo ago”, omits sampled dates and silently suppresses the third role with only three tenors.

BONDS_SOURCE_CHARACTERIZATION.json is evidence of current behavior, not a passing test of the proposed adapter. BONDS_SOURCE_FIXTURES.json states the desired producer-to-page-and-machine acceptance. Those integrations remain to be built and verified.

### Visual and mutation verification
Both new mobile views, the full source contract, the revised main phone view, neutral badges, and phone/tablet evidence actions were visually inspected.

Two attempted moves returned an outer APPLIED_RESPONSE_OBSERVED envelope but contained upstream errors: Paper imported empty div wrappers as Rectangles, which cannot contain children. Original node parents and empty wrappers were read back, proving no move occurred. The wrappers were replaced with genuine Frames containing SVG chevrons, then the original labels were moved successfully. The final screenshots show the correct filled touch targets. Receipts retain the initial errors and their reconciliation; they are not counted as successful moves.

Intermittent Paper read transport timeouts recovered after bounded diagnosis and independent source work. No uncertain write was replayed or moved to another carrier.

## Source/CI status after the Policy and CPI milestone
The branch was read back at 0e9ccf41a0bb62ba0c0b28fd716b39017afd468e before this save. Its check-run collection confirms ordinary_change / allowed=true for ci-authority, with the merge-queue-pilot context failing only because context_active=false / inactive_base_context. Most CI packs were successful; ci-pack-10 was still running at observation. This is not a claim that every check or acceptance gate was complete. No context/base change, merge or release hold was altered.

## Next safe phase in progress
Government Revenue: preserve the accepted signal-first design intent and compare it with the concrete existing investor, procurement, evaluation and shared My Alerts owners. Inspect migrated route references, visible fixture qualification, amount/unit scope, bounded coverage, saved-workflow promises and exact historical clock behavior. Existing canonical activation/reconciliation and funding-meaning specimens are accepted work to preserve.

Phase completion is save-and-continue; this record does not terminate the continuing mission.
