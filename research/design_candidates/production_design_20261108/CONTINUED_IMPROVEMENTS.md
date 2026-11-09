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

## Verified phase: Government Revenue signal joins, watch viability and clock precision

Paper: https://app.paper.design/file/01M6Y3397SE03G626MJ72N90PF/p-1-0  
Signal Desk: https://app.paper.design/file/01M6Y3397SE03G626MJ72N90PF/p-2-0

### Native changes and clarity

The four phone entries now qualify their signal recommendations before the focus lanes. VM-0, Y8-0 and 10U-0 read “Design preview · simulated signals”; 13G-0 reads “设计预览 · 模拟信号”. The existing desktop/tablet qualifiers and simulated quote-change labels remain consistent. Screenshots verify the 320px and Chinese mobile views.

Route map FA-0 now points to local, verified destinations:

| Purpose | Current destination |
|---|---|
| Blueprint and shared states | Builder p-1-0; blueprint 1-0; components 2G-0 |
| Unmatched AVAV funding preview | 95-0 |
| Desktop price-watch review | 2B8-0, panel 2H5-0 |
| Mobile price-watch review | A1-0 |
| Blocked / no request sent | B4-0 |
| Existing matching watch | BE-0 |
| Confirmed / unknown activation | AI-0 / AT-0 |
| Funding draft / confirmed / unknown | 3P-0 / 4J-0 / 4U-0 |

The R5 signal-first ambition, existing receipts, crossing behavior, funding semantics and recovery specimens remain the product reference. The route repair changes identifiers, not their meaning. Recent separate-writer navigation nodes 3SP/3SS/3SV/3SY and their containers were untouched.

New builder board **40P-0 — R13 Source joins and build acceptance** makes the current implementation boundaries explicit. It contains the product journey, canonical source joins, an exact clock illustration, the threshold-versus-crossing distinction and four build stages. Blueprint 6-0 and route-map FO-0 now point to it. The initial duplicated frame inherited a fixed 1180px height; screenshot review caught clipped lower sections. An authorized write_html clone replacement changed it to content height. Final screenshot shows all six sections at approximately 1440 × 2082, with no clipped acceptance/footer content. The temporary 3UC-0 board was replaced by 40P-0 and is not a current destination.

### Existing source architecture and the intended join

Sources are Macro **aec7f387badcdf69c9a947fafbc73b4c68470c7d** and Terminal **5107f4d84e26aefc540c8c99e0ea3803770f1bb3**.

| Responsibility | Existing owner | Required R5 integration |
|---|---|---|
| Eligibility and validity | [signal_gate.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/signal_gate.py), emitted with the paired board by [build_stock_library.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_stock_library.py) | Consume the same gate emission, source session, settled state, allowed decision session and expiry. |
| Action and stock presentation | [stock_view.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/stock_view.py), [stock_dossier.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/stock_dossier.py), stockdata view projection | Preserve the owner-supplied action and missing/stale reasons. Government context does not promote a wait state or reorder the signal. |
| Selected price level | [entry_signal.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/entry_signal.py), assess | Retain selected level, price basis, timing, horizon and source validity. Dealer-gamma levels have different semantics. |
| Signal evaluation | [track_record.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/track_record.py), [qledger.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/qledger.py) | Bind the same family, era and horizon; preserve immature outcomes. A separate Government Revenue research grader cannot stand in for Stock-signal evaluation. |
| Reviewed Government context | [federation.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/government_revenue/federation.py), reviewed_award_change_context; [prophet_annotation.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/government_revenue/prophet_annotation.py) | Require reviewed issuer linkage, receipt identity and known-at visibility. Preserve selected-plan membership, ordering, levels, triggers and gates. |
| Existing plan attachment | [prophet_bridge.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/prophet_bridge.py), originate_plans → annotation | Call path exists. A current nonempty annotation and real R5 consumer journey remain unverified. |
| Watch lifecycle and receipts | [alerts API](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/app/api/alerts/route.ts), [alerts_engine.py](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/ingest/alerts_engine.py), [receipts API](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/app/api/alerts/receipts/route.ts) | Extend this shared owner for the exact predicate; retain its account ownership, lifecycle, evaluation, outbox and reconciliation. |

The current implemented Government Revenue investor consumer is built from persisted issuer-event generations for LMT, RTX, NOC and LHX. Its [defense_economics_producer.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/government_revenue/defense_economics_producer.py) checks evidence identity, hashes, source spans, period, unit and accounting basis, and separates participation, demand, issuer economics and recognition. It is a concrete source baseline; it does not prove the R5 signal-first consumer is installed.

The minimal R5 projection joins references to the existing Stock record, paired gate/board emission, validity, selected level and basis, evaluation family/era/horizon, reviewed government event/issuer and the eventual shared condition/watch identity. Missing qualified signal data must remain explicit. The design does not authorize a new signal, lifecycle or receipt owner.

### Exact alert viability

The current legacy price condition in [alerts_engine.py](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/ingest/alerts_engine.py) compares last > value or last < value. It returns no previous-side state for this type. Data.last selects a quote last when present, otherwise a manifest EOD last. A controlled first observation of 303 against a below-304 condition returns true; that is threshold satisfaction, not proof of a newly observed regular-session close crossing.

Legacy signal alerts read the Terminal symbol slice’s indicator.signals. They do not automatically identify the same event as Macro’s signal_gate output. An R5 adapter must verify the actual source identity rather than equate matching BUY labels.

The bounded suite review covered [suiteAlerts.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/suiteAlerts.ts), its referenced registry, [smartSR.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/suites/structure/smartSR.ts), the alert API allowlist and adjacent options/Forex contracts. No condition in those inspected paths binds R5’s exact selected fixed level and regular-session crossing. suite_event / structure / sr_break is meaningful for module-generated pivot-cluster support/resistance; its condition cannot select one externally owned level. The suite timing contract does not itself prove a live bar closed. Adding unused threshold or source fields would not establish a new predicate.

The build target is an explicitly registered, versioned close-cross condition inside shared My Alerts. Its final discriminator is an implementation choice, not an existing contract invented by this design. It must:

- Resolve the selected Stock/gate/level source server-side and retain the threshold, price basis and condition revision the user confirmed.
- Consume qualified, finalized regular-session closes under the existing exchange-calendar owner.
- Fire only when previous >= threshold and current < threshold. The first below-threshold observation establishes a baseline without replaying history.
- Retain evaluated close identity and condition revision under the existing alert owner. Missing inputs do not advance state; retries, resume and corrections do not create another event for the same transition.
- Keep persisted row, activation confirmation, evaluation, fire and delivery distinct, using the existing canonical receipts and reconciliation path.

Acceptance examples include 304 → 303.99 and 304 → 293 as crossings; 303.99 → 303.90 and 305 → 304 as non-crossings; a first 303.99 observation as baseline only; live quotes/unfinished bars as insufficient; duplicate close pairs and changed bindings as explicit state cases. Existing AI-0/AT-0/B4-0/BE-0 specimens cover the user-visible outcomes.

The adjacent options gamma-flip evaluator has a useful first-observation arming pattern, but its data and semantics remain options-specific. The Forex close condition is pair/4H constrained and not an available activation shortcut. These are owner implementation references, not interchangeable R5 conditions.

### Clock defect, reachability and repair boundary

The exact request 2026-11-09T12:00:00Z produces:

| Helper | Returned cutoff |
|---|---|
| [point_in_time.analysis_clock](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/government_revenue/point_in_time.py) | 2026-11-09T12:00:00Z |
| [metrics._analysis_clock](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/government_revenue/metrics.py) | 2026-11-09T23:59:59.999999Z |

This is reachable through the ordinary offline/programmatic publisher: [build_government_revenue.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_government_revenue.py) accepts an unrestricted --as-of string, passes it to build_payload and can write latest.json, its site twin and HTML. The widened cutoff reaches award/action filtering and the award-event projection. The inspected [HTTP router](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/app/government_revenue.py) does not expose an as_of request parameter; it reads precomputed artifacts. No observed deployed generation or live request-time leakage is claimed.

The payload then publishes only as_of_day.date().isoformat(), and the builder forwards that date to downstream dossier/projector calls. Opportunities also reconstruct an end-of-day cutoff. Replacing only the metrics helper would therefore leave inconsistent precision elsewhere.

For the present daily publisher, the smallest coherent containment is an explicit date-only contract at build/build_payload, rejecting time-bearing input before any publication. Callers and existing timestamp tests must be inventoried before that intentional restriction. A genuine intraday feature instead needs separate analysis_day and exact cutoff values throughout child projections and published metadata. Reuse the strict existing helper; do not create another clock convention.

Calendar dates have separate meaning: an already-known notice may have a future deadline, and a known award can have a future expiry. Filter the underlying fact/revision by its required knowledge/effective clocks, then preserve legitimate future scheduled dates. Do not indiscriminately filter every calendar item by its display date.

### Executed characterization and remaining acceptance

[verify_government_revenue_source_contract.py](verify_government_revenue_source_contract.py) verifies three exact source-content hashes and extracts only the necessary AST definitions. It imports neither application package and performs no collectors, API calls, alert run, lifecycle mutation or publication.

Four controlled rows on 9 November 2026:

| Row | Known | Effective | Exact noon, both clocks | Rounded end-of-day, both clocks |
|---|---|---|---|---|
| A | 10:00 | 09:00 | Included | Included |
| B | 15:00 | 11:00 | Excluded | Included |
| C | Missing | 11:00 | Excluded | Excluded |
| D | 11:00 | 16:00 | Excluded | Included |

The executed source helpers return strict [A] versus metrics [A, B, D]. Knowledge-only filtering at noon returns [A, D], preserving the distinction for known future context. Date-only input includes A/B/D in both paths; strict nanosecond and legacy microsecond endpoints remain different.

Five exact legacy-price cases also ran: first below, equality, gap below the lower example level, live-quote precedence and no price. Every evaluated legacy case returns next_state=None. A helper’s true return is not a claim that installed software fired or delivered an alert; downstream admission, vintage checks, disarming, receipts and outbox were not executed.

GOV_REVENUE_SOURCE_CHARACTERIZATION.json therefore records **CURRENT_HELPER_BEHAVIOR_REPRODUCED_NOT_FIX_ACCEPTANCE**. GOV_REVENUE_SOURCE_FIXTURES.json separately retains intended R5 crossing examples. Source snapshots remain temporary inputs rather than a copied canonical codebase.

Remaining product proof is a real source-bound card, the exact qualified shared condition, canonical watch/evaluation/fire evidence, and the return path. Builder acceptance also includes payload-level clock filtering, rejection before publication if daily-only, child-projector cutoff propagation if intraday, timezone/boundary precision and preservation of known future calendar facts.

## Verified phase: Returns Calendar navigation, readable charts and exact-session build contracts

Paper studies: https://app.paper.design/file/01M6Y39WH7QVTH07RTWHTSRP65/p-1-0  
Builder page: https://app.paper.design/file/01M6Y39WH7QVTH07RTWHTSRP65/p-2-0  
Terminal design home: https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-Q-0

### Native interface changes

The R3 continuous stock, basket and calendar studies are preserved and refined; their illustrative return values were not changed.

| Surface | Changes |
|---|---|
| Mobile WG-0 | The header now says “Illustrative example · not live” and “Through 16 Oct 2026” before the first return card. Removed the duplicated horizontal inset, made the status bar adapt to width, and gave both lens tabs, the range selector and the calendar action full 44px targets. The calendar action uses a forward chevron. Vertical spacing keeps the footer visible. |
| New 320px proof 140-0 | The same workflow is reflowed at 320px. A screenshot caught +19.25% wrapping its percent sign; the three values now remain on one line at 16px. The fixture qualifier, endpoint, chart and primary action remain readable. |
| Stock N5-0 | Added Calendar & evidence action 107-0. Diagnostics now have a shared 21-session scope in 13G-0; volatility and drawdown subtitles name that window. “Largest session” became “Largest session’s share,” with its 9.1% explicitly described as a share of absolute movement. |
| Calendar S2-0 | Replaced the single text string “‹ Latest session ›” with three separate controls in 10C-0: previous month, latest session and a next-month control unavailable beyond the example endpoint. The options action is a distinct 32px control, 18X-0; the model disclosure is a 44px row, 192-0. |
| Calendar source meaning | S7-0 now says “review each session with its dated evidence.” A dated archive does not by itself establish that the evidence was available during the original session. The price, options and forecast qualification states remain separate. |
| Basket PW-0 | Its single-series chart now says “Absolute returns.” The named SPY benchmark was removed from this particular view because no benchmark series or comparison was supplied there. Existing current-member reconstruction, daily equal weighting and membership-date disclosures remain. |

The calendar’s view and observation are separate: changing the visible month does not change the selected session. Latest session resolves the completed exchange session within the retained endpoint, not the wall clock or merely the latest available price row. A missing observation remains an unavailable state. Returning from calendar/options must preserve instrument, benchmark, lens, range, endpoint, selected session and focus.

### Illustration fidelity and chart reflow

The original stock desktop and mobile SVGs each contain 127 points per series: one baseline plus 126 intervals. Basket contains 127 points. Approximate inverse-geometry checks found the displayed returns, pace, volatility and drawdown broadly compatible with the rounded paths. They do not justify changing the illustrative metrics.

Notable interpretations:
- The final 21-interval lens needs 22 closes. The prior comparison contains its own 21 intervals and shares the boundary close.
- Fitted log-price pace is not simply the endpoint return divided by 21.
- The 6M chart overview and 21-session diagnostics describe different windows.
- A daily-rebalanced equal-weight basket does not equal the arithmetic mean of members’ cumulative returns.
- The three displayed member returns support 3/3 advancing and the displayed median, but Paper alone does not supply the constituent histories required to prove the basket’s full construction or coverage.

Uniformly shrinking the original 320-wide SVG at a 320px screen would make 9px axis labels roughly 7px. build_returns_chart.py instead reflows the same supplied rounded coordinates to actual chart widths of 320 and 250 pixels. Both retain 127 points, their common scale, zero baseline and endpoints; axis text remains 11px and the final date is end-anchored.

RETURNS_CHART_FIXTURE.json preserves the supplied illustration geometry. RETURNS_CHART_REFLOW_VERIFICATION.json records the point counts, native widths, readable labels and an inverse-transform scale error below 1e-10 percentage points. This verifies a geometric reflow, not historical price data, exchange-calendar coverage, corporate-action treatment or a new canonical market fixture.

### Discovery, retained references and ownership

Source Start Here 1-0 repairs the stale v2 Desktop reference to **AD-0** and indexes stock N5-0, basket PW-0, calendar S2-0, phone WG-0 and narrow proof 140-0.

Terminal Start Here **1BBQ-0** still distinguishes its six preserved migration fixtures from current references 07–09. Its retained-source text now identifies Returns source p-1-0 / AD-0, while preserving the historical 613W-0 provenance and the held, empty Terminal pointer **1B5H-0**. The original migration-source URL node **1BCV-0** retains its identity and content.

A new footer row **28T5-0** contains that original source link and a visible R3/R4 studies link to the enhanced Returns file. This makes the later studies discoverable from the existing Terminal home without representing them as a completed migration or installed product.

Recent separate-writer improvements remain intact:
- Current early-close reference **28BZ-0**.
- Current phone **28FS-0**.
- Current pending/closed/loading/unavailable outcomes **28LZ-0**.
- Their index pointers and source note remain unchanged.

The new build contract explicitly directs builders to those current session states. **LV-0 is retained as a historical recovery study**, not promoted over the newer Terminal references.

### Native build contract

**197-0 — R4 source and interaction contract** lives on the new **p-2-0 — R4 · Build contracts** page. It contains:
- A single selection/read contract across continuous path, calendar and dated evidence.
- Existing route, daily-price, intraday, calendar, archived-options and basket owners.
- The exact historical-endpoint reuse hazard and compounding identity.
- Concise state specimens for last observed / close unverified, missing dated options and an expanded unavailable-forecast disclosure.
- Route, calculation, evidence and real-consumer acceptance stages.

The initially appended builder content and Terminal crosslink were clipped by fixed legacy artboard dimensions. Screenshot review caught this before acceptance. The complete builder frame was moved, retaining ID 197-0 and its children, to its own builder page. The Terminal crosslink was refactored into the existing footer; the original source-link text node was moved into the compact row without changing its identity. Final screenshots show the full contract and both source links. No held migration was replayed, no native delete/archive action was used, and no uncertain write was retried.

### Existing implementation and the missing consumer adapter

Source pins remain Macro **aec7f387badcdf69c9a947fafbc73b4c68470c7d** and Terminal **5107f4d84e26aefc540c8c99e0ea3803770f1bb3**.

| Responsibility | Existing source | Integration requirement |
|---|---|---|
| Analysis routing | [analysisRoute.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/analysisRoute.ts), [finPages.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/components/fin/finPages.ts), [AnalysisWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/components/workspaces/AnalysisWorkspace.tsx) | Register the proposed Market/Returns view in the existing parser and mount. The current closed vocabulary is company / theses / investigations; unknown company pages fall back to Overview. Reuse its URL and Back/Forward ownership. |
| Daily OHLC | [dataCache.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/dataCache.ts), [fund.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/fund.ts) | Reuse getOhlc/getBars, retaining or adding the relevant evidence projection. Normalized rows alone do not establish adjustment, finality or historical availability. |
| Dated price | [intraday route](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/app/api/intraday/route.ts), [intradayShared.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/intradayShared.ts), [intradayEvidence.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/intradayEvidence.ts) | Reuse selected-session slicing and evidence. The supported request shape includes sym, tf, ext and date. Source evidence currently marks completeness as not_assessed, adjustment and PIT availability as not_verified. |
| Exchange session | [usEquitySessionClock.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/usEquitySessionClock.ts), [usEquitySessionProjection.json](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/usEquitySessionProjection.json) | Resolve expected regular close, closures, early closes and coverage. The bundled projection declares 2016–2028 and Macro source revision 112eba2036fd1186e67b914e194f4fa541cfc4df. Preserve its actual lineage. Expected close time does not prove returned price finality. |
| Historical options | [GexDeskView.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/components/gexdesk/GexDeskView.tsx), [gexSessions.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/gexSessions.ts), [exposureChartLink.ts](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/5107f4d84e26aefc540c8c99e0ea3803770f1bb3/terminal/lib/exposureChartLink.ts) | Existing loadSession reads gex_at:ROOT:YYYY-MM-DD and checks root/session. Add a validated generic date entry through that owner; a normal root entry currently opens live, while the existing exposure hash requires a real strike/lens/metric/shock/fingerprint. Do not fabricate those fields for a calendar link. |
| Dated options publication | [build_options_hub_nightly.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_options_hub_nightly.py) | Preserve dated-key/index ownership and reconstruction qualifiers. A self_healed or late reconstructed payload cannot gain original-session availability merely from its date key. |
| Basket construction | [basket_index.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/basket_index.py), [basket_membership_pit.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/basket_membership_pit.py) | Retain reconstruction versus dated-membership basis, evidence/fallback reasons and weighting. Synthetic high/low values are not synchronous observed basket trades. |

The existing basket coverage_pct is a latest-row positive-volume member fraction, not a 0–100 number or full-window price-completeness measure. The adapter must name and format that measurement accurately and derive any stronger range-coverage claim from the relevant observations.

Terminal intraday timestamps also have a display-clock convention; market-local display epochs must not be relabelled as actual UTC observation instants. A last returned bar remains “Last observed” until the required finality and expected-close conditions qualify. Continuous-path mode should retain actual observation gaps and source qualifications.

### Historical-return characterization: executed, bounded

[sp500_heatmap.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/sp500_heatmap.py)::daily_returns uses its asof as a reference-window anchor. It still chooses the final available close for now, and its 1D value uses the prior available row. That is appropriate to characterize before reuse; it is not a historical-session selector.

verify_returns_source_contract.py verifies source SHA-256 **94607542cae6a31485bd7116a5af4cbe12a5d21d8fb36f33e8e86289f0853682**, extracts only the four required AST definitions and runs five controlled cases:

| Controlled input | Existing helper 1D | Required selected-session behavior |
|---|---:|---|
| Closes 100, 110, 132 on 14–16 Oct; asof 15 Oct | 20% | 10% for the selected middle session |
| Same input pre-sliced through 15 Oct | 10% | 10% |
| 14 Oct = 100; 15 Oct missing; 16 Oct = 132 | 32% | Unavailable for one-session return because the expected prior observation is missing |
| Two flat closes at 100 | 0% | Preserve valid zero |
| Prior close zero | Unavailable | Preserve unavailability |

The calendar session keys in this harness are controlled fixture inputs, not verified market observations. The production adapter should use existing [nyse_calendar.py](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/lib/nyse_calendar.py) endpoint discipline, including session_n_back / is_prior_session / row_n_sessions_back, and select the exact observations before measurement.

RETURNS_SOURCE_CHARACTERIZATION.json records **CURRENT_HELPER_REUSE_HAZARD_REPRODUCED_NOT_PRODUCT_ACCEPTANCE**. Only pure source definitions ran. No API, collector, route, publisher or installed Returns view was executed. The heatmap owner was not changed, and no claim is made that a deployed calendar currently misuses it.

### Arithmetic, selection and evidence acceptance

For previous close P, regular open O and selected endpoint C:
- Simple gap = O/P − 1.
- Simple regular return = C/O − 1.
- Total = C/P − 1 = (1 + gap)(1 + regular) − 1.
- Log components add.

The executed 100 → 105 → 102 example gives +5.00% gap, −2.8571% regular and +2.00% total. Adding the simple component percentages yields a different answer. The existing [measurement-controls research witness](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/research/rotation_intelligence/intraday_sessions_20261013/measurement_controls.py) uses additive log decomposition; it remains a research witness, not evidence that a production Returns adapter exists.

The consumer must retain distinct requested/resolved endpoints, price basis, unit, benchmark basis, lens and calendar selection. Define percentage-point excess, relative wealth return and log-relative units explicitly. Unverified prices cannot be labelled total return.

Focused acceptance:
1. Copy/reload/Back/Forward preserves the selection tuple. Month navigation changes visibleMonth only; latest session stays inside the retained endpoint.
2. Selected-session price and options results retain the same symbol/date/basis. A late A result cannot appear under B. Missing archives, wrong-root/date payloads and transport failure remain distinct.
3. When a date changes, show that selected date with pending dated content; qualify price and evidence independently. Keep useful price context when evidence is missing, and scope retries to the failed read.
4. Native controls become actual buttons in implementation, with accessible names, disabled semantics, keyboard day selection and focus restoration. Paper hit regions are visual proof, not keyboard/runtime proof.
5. Test closure, early close, DST offsets, incomplete final bar and out-of-coverage calendar dates. Expected session close and verified price close remain distinct.
6. Preserve current-member reconstruction and unreadable-membership evidence; require matched endpoints/basis before benchmark comparison.
7. Reuse the current Terminal outcome references and existing URL/request-counter owners. Do not introduce another history, session, retry or options-data store.

The native layouts, source bindings, helper behavior and geometric reflow are verified at their stated boundaries. Full route integration, live price/archived evidence availability, model qualification and production browser acceptance remain open.


## Phase 7 — Confluence controls and public/protected snapshot identity

### Native outcome and preservation

File [Confluence Screener](https://app.paper.design/file/01M6Y3DCDDW541ZR38J1V52A9Y/p-2-0), R2 eight variants. Operations 230–270 improve all English/Chinese and light/dark desktop/mobile variants while retaining their source order and evidence anatomy.

- Replaced “Start free trial,” “Unlock if matched” and “See every line-up’s matching stocks” promises with **Open Mastermind / 打开 Mastermind**. The existing CTA is a generic app entry; it does not itself start a trial, create a combination or grant stock access.
- Main links have 48px targets and card links have at least 44px targets. Mobile card actions occupy a full row below the public count. Main CTA support text is concise and account-access dependent.
- The four mobile first-card headers now place the title/rank above the equal-width evidence pair. The rank badge no longer competes with both evidence columns.
- Method rows use **How this shortlist works / 信号组合说明**, with a concise subtitle and a single disclosure cue. The builder specifies the whole row as native details/summary using the existing local disclosure behavior.
- “Matching now” was changed to “Matching stocks” in the applicable English anatomy and entitled examples. These snapshots do not prove synchronized current market sessions.
- R4 addendum **2I3-0** extends existing builder **2AG-0** on p-3-0. Both 320px proof containers are within that addendum: **2JO-0** EN dark and **2KX-0** ZH light. No separate artboard family was created.
- All 24 existing R3 builder text IDs and contents were read back unchanged. Governed p1, R3 availability/qualified-zero states, protected recovery states, retained filter studies and current non-filtering semantics remain intact.
- The current authority and flow-map builder pointers now locate the R4 addendum directly.

Eight-variant JSX readback found three correctly named app links per variant, 48px/44px target rules and no obsolete trial/unlock promises. Native screenshots verify EN dark desktop and mobile, ZH light mobile, the complete addendum and both 320px specimens. Native layout verification does not prove runtime keyboard behavior or browser animation.

### Current source defect reproduced

Exact source pin: [Macro aec7f387badcdf69c9a947fafbc73b4c68470c7d](https://github.com/mastermindx-market-intelligence/macro/tree/aec7f387badcdf69c9a947fafbc73b4c68470c7d).

The [miner builder](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_tech_confluence.py) assigns L000n IDs by selected-list position. An ID is artifact-local, and generated_utc has second precision. The [page builder](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/scripts/build_confluence_screener.py) provides the protected payload's full artifact built timestamp but reduces the public asof display to a date; page generated_utc is a different render clock.

The current [template hydration helpers](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/templates/confluence_screener.html.j2) join protected rows using only combo_id. They do not inspect built or recipe identity. They silently skip unmatched IDs or invalid ticker links and then call showUnlockedCta and set hydrated=true.

The isolated source harness **verify_confluence_hydration.js** extracts the exact contiguous bilingual, tickerLink, replaceLockedRow, showUnlockedCta and hydrate functions from template lines 482–585. It executes those unmodified functions in Node v24.22.1 with a minimal fake DOM; no auth, fetch, browser, production data or installed runtime is invoked. Template SHA-256: **a782c6288f2d24917511a182470d521993c567297a965dc7bba8a7e53de83e5b**; extracted helpers: **9ec01d09d3a9850e275e964ea04033e1777f0aaeb2da16e79bb6ff0ae01fe17a**.

| Controlled case | Reproduced current behavior |
|---|---|
| Matching two-row control | Both rows replaced; success claimed |
| Different generation, same ordinal IDs | Both wrong-generation lists attached; success claimed |
| Same timestamp, changed fixture content | Both replacement lists attached; success claimed |
| Empty payload with two expected rows | Neither row replaced; success still claimed |
| Unmatched ID | Neither expected row replaced; success still claimed |
| One of two expected rows | One row replaced; success still claimed |
| Malformed ticker with positive count | Row becomes “No stock matches”; success still claimed |
| No expected protected rows | Paid success still announced |
| Different schema control | Current consumer rejects before replacement |

The artifact and recipe contexts in these fixtures are test declarations; they are not fields the current consumer already reads. **CONFLUENCE_SOURCE_CHARACTERIZATION.json** records current hazards, not acceptance of a deployed repair.

### Build contract and compatibility

**CONFLUENCE_BUILD_DELTA.json** carries the full proposed owner and acceptance contract. Add one pure binding helper in the existing builder, used by public and protected projections:

1. Compute artifact_sha256 over canonical JSON of the original parsed artifact: recursively sorted object keys, preserved array order, compact separators, UTF-8 and rejected non-finite values.
2. Resolve each integer leg index against the artifact before display labels discard machine identity. Derive recipe_key from direction, sorted signal_id/timeframe/kind/direction tuples and applicable event-window parameters.
3. Reject unresolved/duplicate legs, count mismatch, inconsistent direction and missing required parameters. Exclude display labels, ordinal indexes and rank from recipe identity.
4. Preserve existing combo_id, rank, is_free, active_count and built. Add only non-secret expected identity/count metadata to the public shell.
5. Before any DOM replacement, require matching bound schema, artifact fingerprint, full artifact built, exact expected protected-row set, recipe keys, valid unique tickers and consistent counts. Prepare the complete response first.
6. Mark success only after all expected rows are applied. Zero expected rows need no paid-success announcement. Missing-source empty overwrite remains required but cannot mean hydration success.
7. A bound version must reject legacy unbound responses, and old cached v1 consumers must reject the new asset schema. Adding ignored fields to v1 alone is insufficient. Test both rollout directions through existing generic consumption/auth paths before choosing the final schema literal.
8. Preserve the existing protected endpoint, MDXAuth, inFlight, auth-settled and refresh owners. A mismatch preserves usable public evidence and existing protected-unavailable recovery. It does not establish no entitlement or zero matches.

The canonical recipe key is a binding aid within this artifact contract, not a new recipe registry or proof that engine semantics are equivalent across versions. The browser compares metadata; it does not fetch the full artifact or reimplement the miner.

The [engine](https://github.com/mastermindx-market-intelligence/macro/blob/aec7f387badcdf69c9a947fafbc73b4c68470c7d/engine/tech_confluence.py) still checks the final panel position separately per ticker. No synchronized latest-session claim was added. Terminal's separately sourced native technical screener and Smart Screens are not interchangeable owners for this Macro shortlist.

### Delivery boundary

This phase changes editable Paper designs, source-linked build contracts and reproducible characterization artifacts. It does **not** patch the production hydrator, change entitlements, deploy a schema, establish browser animation playback or claim installed-runtime acceptance. Existing R3 source pin 338a10852dcefa5d2bd07e5c6be0955c2b1e83fd remains historical provenance; the R4 source review uses the newer explicit pin above.

## Next safe phase in progress

Bot Paper Portfolio: audit Today → actual Holdings and return continuity in file 01M6Y3AT0XJBWTM3AVCMBJQ8TE, boards 2C-0 / 11E-0 / 77-0 / 14D-0. Preserve the separate selected-history/receipt work, the US S0 candidate's Draft/HOLD scope and the distinction between held positions, accepted targets and historical risk. Focus on the valued-account snapshot boundary and concrete navigation/narrow-layout gaps.

Phase completion is save-and-continue; this record does not terminate the continuing mission.
