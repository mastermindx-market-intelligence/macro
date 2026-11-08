# Continued Paper improvements — 8 November 2026

## Current assignment and source
The Chairman explicitly extended the estate mission: continue auditing, fixing, implementing and enhancing the existing Paper designs autonomously. This record continues PR #10864 and the wider #10617 programme. It does not create a second programme or claim a product release.

Protected Mastermind procedure pin remains 5c3d3885234358aefb97ecdbc59be0864df14f8b. New source checks use Macro b5674d8ef898e503d6164922654f5ff89be9981c. The earlier audit's 338a1085 baseline and accepted results remain historical evidence and are not rewritten.

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

## Next safe phases already identified
Policy Monitor: full-row mobile disclosures, plain EN/ZH unknown-data copy, compact historical channel summaries with complete background retained in the existing disclosure. Preserve candidate #10493's data, source-note and release/effect owners.

Market Memory CPI revision evidence: a source-qualified period chooser, explicit comparison-pair rules for zero/one/multiple changes, and truthful copy-reference success/failure. Preserve the newer R2 record and unavailable-version work; do not duplicate it.

These are ongoing work items, not a reason to terminate the continuing mission.
