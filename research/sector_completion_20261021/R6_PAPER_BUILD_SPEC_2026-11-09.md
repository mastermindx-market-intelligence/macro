# Sector Intelligence v1.1 — R6 Paper build specification

**Scope:** the additive Sector × Prophet v5.1 integration, 9 November 2026 America/Vancouver (10 November UTC).  
**Governing source:** [v1.1 amendment](https://github.com/mastermindx-market-intelligence/macro/blob/0ccc0fbe31e9a08eab999ce514e9b9d8f8be9788/research/sector_completion_20261021/PROPHET_V51_INTEGRATION_AMENDMENT_2026-11-09.md), together with Prophet §18/§18.14 at 1f645a751ea22d7ad5fe512165017873d8b65382.  
**Status:** eleven editable R6 roots and one additive README pointer were applied, inspected, extracted as JSX and finished on the existing file. This is reviewed design evidence and implementation direction, not browser, source-retention, scientific or production acceptance.

## 1. Design inheritance and exact map

Use existing file **01M6FAXA774QT1VRDMAG7DFQ2W**. Preserve all 47 retained R4 roots and the existing Fable R5 work (19 product/state frames and one build frame). R6 is a new, disjoint extension on three pages; it does not replace native Cycles, calls, Bottoming Watch, flow, four-universe or rich company/Prophet depth.

| Code | Applied root | Page | Design | Width / theme / language |
|---|---|---|---|---|
| R6-01 | QNB-0 | p-L-0 | Market participation | 1440 / dark / en |
| R6-02 | QRX-0 | p-L-0 | Healthcare · Full population · Light EN | 1440 / light / en |
| R6-03 | QWH-0 | p-L-0 | Company economics · Sector evidence · Dark EN | 1440 / dark / en |
| R6-04 | R0W-0 | p-L-0 | HCA · Independent peer context · Light EN | 1440 / light / en |
| R6-05 | R5B-0 | p-L-0 | Saved context · Original and current · Dark EN | 1440 / dark / en |
| R6-06 | R8Z-0 | p-L-0 | Market to company · 390 · Light EN | 390 / light / en |
| R6-07 | RA8-0 | p-L-0 | HK relative leader · 390 · Dark ZH | 390 / dark / zh |
| R6-08 | RCM-0 | p-L-0 | Original unavailable · 320 · Dark EN | 320 / dark / en |
| R6-09 | RDH-0 | p-M-0 | States and user explanations | 1440 / light / en |
| R6-10 | RGP-0 | p-N-0 | Build · Data, science and persistence | 1440 / light / en |
| R6-11 | RGW-0 | p-N-0 | Build · Journey, markets and delivery | 1440 / light / en |

- [R6 product page](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-L-0)
- [R6 states and help](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-M-0)
- [R6 build instructions](https://app.paper.design/file/01M6FAXA774QT1VRDMAG7DFQ2W/p-N-0)
- Existing README HBU-0 on p-9-0 now starts with the **additive child RN3-0**. Its original ten children and ordering relative to one another remain intact. No R5 node was edited.

Use the new **R6_PAPER_MANIFEST_2026-11-09.json** for operation receipts, root identities, extraction hashes, review and completion. **R6_PAPER_JSX_2026-11-09.json** is the real inline-styles extraction. It is a design reference, not production component code; preserve original shared shell components, chart helpers, tokens, data contracts and accessible semantics in implementation.

### Visual direction

The hierarchy answers the market/sector question first, shows the strongest counter-evidence nearby, then offers company investigation. The brief has a single primary sector action. Deep evidence stays one deliberate action away rather than filling the landing page with every backend field.

Dark surfaces use luminance depth and restrained borders; light uses white panels on a cooler canvas. Preserve existing Inter typography, shared shell navigation/header, density and locale-aware directional colors. Do not add colored container-edge decoration, an alternative application shell, new token ownership or an architectural status dashboard in customer flows.

The new numerical mockups are all marked **Illustrative**. Real views replace that with actual source/basis/availability disclosure only after qualified real inputs exist. Build IDs, PRs, fingerprints, SQL versions and operation IDs stay on build/evidence surfaces, not the default customer view.

## 2. Component and interaction contract

### Brief, context strip and member continuation

R6-01 shows US market, sector return comparisons and breadth/concentration. “Strength is broadening” is supported by an explicit earlier observation of the **same member cohort**, not by a high single-point breadth count. Equal denominators alone do not establish unchanged membership. A live title needs comparable membership IDs, price definitions and observation dates; otherwise use a neutral current-state title and disclose the population change.

The fixture's current breadth is 42/60 above each member's 50-session average; the earlier observation is 28/60 in the same synthetic cohort. It is not the saved-original fixture of 38/60 on 6 November. The fixture does not assert real exchange-session endpoints or a real previous source timestamp. The real Sources/Compare observation dates view must show exact timestamps, membership identity, classification and threshold semantics; no made-up date may be filled from the mockup.

- **Research Healthcare / Explore Healthcare members:** opens the same group's full member view with captured context, not a Top-N shortlist.
- **Explore all sectors:** preserves market and source capture, and clears only the single-group selection through the existing URL codec.
- **Healthcare row / Comparison details:** distinct click targets; one changes selection, the other explains the aligned basis.
- **Inspect participation:** opens constituent-level participation and contribution evidence, including missing observations, issuer concentration and source cutoff.
- **New leaders can emerge:** opens the existing company discovery path with the independent-emergence intent visible; weak sector support never makes original company research inaccessible.
- **What remains ahead:** opens retained Cycles/qualification explanation; unavailable return forecasts are not replaced with a fabricated gauge.
- **Did participation help:** opens existing Strategy Evaluation, with a source-compatible protocol selection where available. It does not pre-populate a live result from the synthetic 6.1% specimen.

The 61% concentration specimen means the top five issuer contributions divided by the **sum of positive contributions** over the declared interval and weight convention. It is neither 61% of total signed sector return nor a five-listing count. A zero positive-contribution denominator yields unavailable. Keep the observed breadth, same-cohort comparison and concentration question visible together.

### R6-02 full population and selection

60 = 52 with Prophet research coverage + 5 without it + 3 awaiting identity confirmation is a synthetic coverage partition. It says nothing about trade eligibility or the user's entitlement; those are additional independent dimensions. Every native member remains in the population even when its Setup is unavailable. Membership/issuer/listing semantics must match the source rather than using ticker string equality.

Search operates over the complete captured population before cursor/page limits. Filters and results expose source count, matching count and visible range using real counts. Do not claim “all” from a preview. An empty search has a visible clear-filter action; a failed query is not an empty result. Stable ordering comes from declared source order or the explicit chosen sort, never accidental Prophet coverage.

The frame shows HCA and ISRG selected, LLY unselected and **Compare 2** enabled. The checkbox is a separate control from row navigation and Open Setup.

| Situation | Required behavior |
|---|---|
| Zero selected | Compare unavailable with “Choose at least two companies”; keyboard can reach the explanation |
| One selected | “1 selected”; Compare remains unavailable; allow deselection |
| Two selected | Compare 2 opens the existing comparison destination with exact listing IDs and captured source |
| More selected | Respect the existing comparison owner's actual maximum; show the count and a clear limit reason before accepting an excess selection |
| Page or query changes | Preserve the explicit selected IDs; show selected-but-not-visible count and a review/clear action |
| Cohort/capture changes | Preserve the old selection as original context and ask the user to review against current membership; never silently retarget an ID |
| Member without Prophet coverage | No invented Setup; retain membership, available research and original member source |
| Identity unresolved | No guessed company link; show original source and unresolved listing/exchange reason |
| Access refused | Explain current access separately from coverage; do not remove it from group totals or leak private source content |

“Research in Prophet” opens a group-filtered research universe, not a newly admitted or automatically tradable cohort. A specific member's **Open Setup** opens the current Prophet destination using its supported identity bridge and captured Sector reference. Full Setup, entry geometry, invalidation, timing, risk and policy remain Prophet-owned.

### R6-03 original economic evidence

The operating-margin example is a count-based issuer aggregate for a declared comparable reporting cohort. Show the full eligible → reported/unreported → comparable/noncomparable → improved/weakened/unchanged ladder. Missing reporting is unknown, never weakness or flat performance. Research coverage is a separate count and may not become the reporting denominator.

The illustration's improved/weak/unchanged stack uses one issuer scale: **20 px per issuer**, widths 380/180/80, total 640. The current proportion is 19/32 = 59.375%; do not divide by the 40 reported or 60 eligible entities. A selected issuer's exclusion recalculates the appropriate full ladder, not only the numerator.

Each observation links to the original source assertion with issuer/listing bridge, reporting period, measure definition, event date, first-available timestamp, vintage/correction and current rights. Issuer A/B/C and their example observations are illustrative. Multiple measures from one filing remain one underlying source root for provenance counting. Source diversity, statistical independence and economic contribution are different claims.

### R6-04 independent peer context

The raw market/sector/company returns share a single **0–15%** axis in the positive example. The width scale is **30 px per percentage point**: market 96, sector 228, HCA 366. The figure includes exact readable numerical labels; no hover is needed. A general production chart must also handle negative returns with a shared signed axis.

The raw full-sector return remains visible for description. The peer panel excludes **HCA and every same-issuer listing**, using actual bridge/version and start weights. Show excluded weight, residual population and coverage. Its illustrative peer return is 7.30%, 41/59 above the same 50-session average, excluded start weight 6.12%. Do not recompute one side on a newer source.

**Inspect excluded members** opens the exclusion set and method, including aliases and residual denominator. **Inspect shared sources** explains which observations overlap and which issuer evidence adds a distinct source; it must not call deduped data statistically independent. **Open company evidence** opens dated assertions rather than a narrative recap without sources.

The +4.60 pp HCA versus Healthcare difference is an observed return difference. It is not estimated beta-adjusted alpha, independent selection skill or incremental portfolio value. Model-based claims require the distinct qualified protocol in the amendment.

### R6-05 saved original/current

Original and current are separate explicit reads, with separate source/cutoff/rights. The specimen uses original 6 November breadth 38/60 and current 9 November 42/60 in the same unchanged synthetic cohort. The user's note remains their note; it does not become source evidence.

- **Open original:** resolves the retained original reference under current rights. A digest or revision without retained bytes is insufficient.
- **Open current:** opens a current view with clear new source identity; it never overwrites the original.
- **Save investigation:** uses current admission/actor/journal/idempotency contracts. A receipt must identify the saved record/revision/source qualification.
- **Follow sector:** has separate capability from saving a preference, adding a note or a price alert. Without a real material-change producer/outbox, show unavailable with reason. Do not imply monitoring from a stored flag.

On account switch, abort/ignore stale private completions and preserve the prior account's uncertain-save operation. A later owner_mismatch or not_found is not proof that an earlier write failed. The new account cannot check or replay the old operation. Existing same-account status recovery remains available on return.

### Phone and locale variants

R6-06 is 390px light EN, with market, group, breadth/concentration, member continuation and first company action in a compact sequence. R6-07 is 390px dark ZH and shows a falling Hong Kong relative leader with a local cutoff. R6-08 is a 320px original-source-unavailable state; the note remains available and the current view is a separate action.

Use the shared mobile shell/status/navigation pattern. The designs are deliberate pairwise coverage, **not every language/theme/width combination**. Full 320/390/430/tablet/desktop, light/dark, EN/ZH and long-label coverage remains the actual consumer's implementation proof. Mobile tables become meaningful labelled rows/cards, retaining selection, units, source state and actions. Body/controls cannot require horizontal page scrolling. Chart/table details may use an accessible bounded region when necessary, with an equivalent value view.

Keep locale convention explicit: the ZH negative price returns use the shared falling-green convention and the positive relative difference is still labelled +2.00 pp. Color does not determine the sign; text and numerical sign do.

## 3. Named disclosure destinations and accessible behavior

Every help/source action in the design is a real named view using the existing sheet/dialog/full-page owner. Desktop can use the shared sheet; mobile uses a full-width sheet or page. Do not invent a new universal disclosure router.

| Trigger | Destination and required contents |
|---|---|
| Sources & comparison basis / Comparison details | Benchmark owner ID, period endpoints, number of completed local sessions, price/total return, currency, FX convention, group weights, cohort identity, source/event/published/available/captured clocks and qualification |
| Compare observation dates | Both breadth observations, actual member IDs, same/different cohort, per-member threshold and missing-count handling |
| How coverage works | Full/visible population, native identity bridge, Prophet covered/uncovered/unresolved and separate eligibility/access status |
| Inspect participation | Numerators/denominators, missing members, issuer-level positive contribution and concentration, retained source identity |
| How counts work / Inspect periods and sources | Eligible/reporting/comparable cohorts, exact period/measure definitions, original assertions, excluded reasons and missing observations |
| Inspect excluded members | All same-issuer aliases/listings, exclusion weight, peer denominator, basis, method and coverage failure reason |
| Inspect shared sources | Repeated roots and overlapping features; dedupe rules and explicit limit on independence claims |
| Why estimates are unavailable | Per-head state, source/model availability, current withdrawal and retained observed-cycle destination |
| Original unavailable / source status | Original ref identity without leaked restricted payload, missing/withdrawn reason, retained note and explicit current-view option |
| Evaluation details | Existing Evaluation protocol, actual/illustrative status, benchmark, period, currency, capital basis and acceptance |
| How attribution works | Existing Evaluation method, weights, inputs, cash/cost/FX conventions and numerical reconciliation |
| Coverage in Evaluation | Eligible/observed/missing/no-entry/no-fill cohorts; no completeness claim from a label alone |
| Open Portfolio | Existing authorized holdings view, with actual positions separate from model/research plans |

All triggers are keyboard and touch operable; all icon-only controls have accessible names. Use the actual shared focus model: move focus to the destination heading, retain the invoking element, keep modal focus within a modal, allow Escape/Back and restore focus to a surviving trigger or a named parent fallback. Browser Back restores route and context; it is not an unconditional current-data refetch that silently replaces an original capture.

Interactive targets have at least the shared 44px touch area, including visually quiet text links and checkboxes. Provide meaningful table headings, selected state, exact-value alternatives, visible focus, reduced-motion behavior and live status for save/search completion without repeated announcements. Long ZH text must reflow. Real accessible DOM and screen-reader behavior remain to be tested in the implementation.

## 4. Exact eight-field build cards in Paper

These are internal build directions, never default product copy.

### A. Capture once. Keep the full population.

Paper root: RH3-0.

- **User job:** Move from a market or sector decision into every eligible member and the right Prophet Setup.
- **Owner / source:** Existing Macro generation and membership owners → Prophet immutable read bundle; Terminal lane 3 presents it.
- **Inputs / identity:** Native group, issuer and listing IDs; exact bridge version; source + knowledge clocks; basis, rights, full counts and captured refs.
- **Calculation / claim:** 20 completed sessions is this fixture's window. Native 21/63 stays distinct. Membership, research coverage and access are separate.
- **Interaction:** Search before paging. Select with checkbox; Open Setup is a different action. Preserve filters, comparison and return context.
- **States:** 52 covered + 5 uncovered + 3 unresolved = 60 illustrative members. Missing/denied/stale/zero are distinct; never guess an identity.
- **Proof:** One captured context for all panels; complete pages and group joins; later publication cannot change the in-flight decision.
- **Custody:** Extend lane 1's bounded authenticated reader, 4 MiB ceiling and finite JSON. Keep its HOLD and shared lane 3 file ownership.

### B. Independent peers. Original company evidence.

Paper root: RHU-0.

- **User job:** Find sector support, then test what the company adds and what could weaken the case.
- **Owner / source:** Sector membership/aggregation owns peers. Existing issuer evidence and Research owners supply original observations.
- **Inputs / identity:** All listings/aliases of the same issuer; frozen start weights; original filings, measures, reporting periods and availability times.
- **Calculation / claim:** Show full group for description; exclude the entire issuer for confirmation. Reveal removed weight, residual coverage and concentration.
- **Interaction:** Inspect excluded listings and shared sources. Open exact company evidence, then return to the selected member and source version.
- **States:** 60 eligible = 40 reported + 20 unreported; 40 = 32 comparable + 8 noncomparable; 32 = 19 improved + 9 weakened + 4 unchanged.
- **Proof:** Perturb excluded issuer inputs while benchmark, membership and other inputs stay frozen. Peer-only context must be unchanged.
- **Custody:** No Prophet winners, rankings or confidence become upstream facts. Dedupe source roots; do not claim statistical independence from that alone.

### C. Separate history from qualified forecasts.

Paper root: RIL-0.

- **User job:** Understand observed participation and cycles, then see only predictions supported by the relevant current evidence.
- **Owner / source:** Existing Sector Cycles/hazard/science lane 8; Prophet consumes qualified context. No second forecast engine.
- **Inputs / identity:** Event time, confirmation/first-known time, feature cutoff, retained vintages, membership history, model and calibration versions.
- **Calculation / claim:** Four separate heads: remaining-return distribution, adverse tail, target-before-invalidation and transition timing.
- **Interaction:** Unavailable forecasts retain useful observed cycles and explanation. Exact values and calendar/session definitions stay inspectable.
- **States:** Current #10924 withholds hazard and the malformed prior. No age-based upside gauge or historical 4/6 pass promoted to current output.
- **Proof:** No future disclosure leakage. Confirmed pivots use first-known time. Historical windows stay anchored as the observation date advances.
- **Custody:** Owner-only qualification/retraction. No model number from an unavailable head; stale probabilities cannot survive a source correction.

### D. Compose retained records through lane 6.

Paper root: RJC-0.

- **User job:** Save the exact reasoning context, reopen it later, and compare it with a separately labelled current view.
- **Owner / source:** Existing Investigation/Thesis/admission owner. Terminal #1410 owns the reserved 0049 sequence and actor journal.
- **Inputs / identity:** Original source refs + retained bytes/rights; original account; revision and operation receipt; exact Thesis version for Prophet.
- **Calculation / claim:** 0049 is structural v2 admission, not source retention. Prophet adds compatible v3 decisions/milestones and closed research evidence.
- **Interaction:** Install readers before new writes. Check save status after uncertain effects; never replay through a different account.
- **States:** Original unavailable; access withdrawn; changed account; in-flight save unknown. Keep user notes and separate current-view action.
- **Proof:** Read installed validator body first; compose one migration path; test old Options/scenario/review, v1/v2 readers and new v3 parity.
- **Custody:** Never create another 0049 or independent v3 migration against old 0047. Rollback disables new writes while preserving created-record readers.

### E. One journey, with exact return.

Paper root: RK3-0.

- **User job:** Brief → full members → Prophet Setup → source evidence → return without losing the investigation.
- **Owner / source:** Shared shell, existing URL codec and return-context owner; lane 3 integrates shared files once.
- **Inputs / identity:** Market, group/listing, filters, sort, selection, page/cursor, active view, captured version and original source refs.
- **Calculation / claim:** Raw return differences are percentage points. They do not establish beta-adjusted alpha, selection skill or a trade instruction.
- **Interaction:** 0/1/2 selection states, separate row actions, named help destinations, focus return, Escape/Back and 44px touch targets.
- **States:** Source refusal, coverage gaps, unavailable Setup, old original context, stale request completion and actor changes are explicit.
- **Proof:** Actual browser journey with coherent source, keyboard/touch, EN/ZH, themes and 320–1440 widths; Paper is design evidence only.
- **Custody:** Preserve all R4 and R5 designs, native Cycles, Calls, Bottoming Watch, flows and four universes. R6 is additive integration depth.

### F. Native markets and information clocks.

Paper root: RKU-0.

- **User job:** Read US, Hong Kong or mainland China leadership on the market's own basis and know what was available then.
- **Owner / source:** Existing native region, exchange-session, benchmark, listing and corporate-action owners.
- **Inputs / identity:** Local currency, exchange calendar, sessions, benchmark and total/price return basis; announcement and first-available times.
- **Calculation / claim:** HK fixture: market −4%, group −2%, relative +2 pp. Less negative is still falling. Do not substitute a US close.
- **Interaction:** Sources & comparison basis opens endpoints, cutoff, excluded later information and currency treatment. A/H listings remain distinct.
- **States:** Local holiday, suspension, unreleased report, later US close, revision and incomplete membership do not become zero or current data.
- **Proof:** 02:30Z cutoff includes 02:29 available evidence; excludes 02:31 and 21:00 even when their event dates are earlier.
- **Custody:** Chinese directional colors follow the shared locale rule. Published/available/ingested/event times retain their distinct meanings.

### G. Evaluate participation and keep action owners.

Paper root: RLL-0.

- **User job:** See whether the strategy participated, what cash and allocation cost, and what selection actually contributed.
- **Owner / source:** Existing Prophet Strategy Evaluation and authorized Portfolio; current Record types remain unchanged.
- **Inputs / identity:** Protocol, period, benchmark, currency, weights, actual/simulated capital, complete eligible decisions, cash, costs and FX.
- **Calculation / claim:** Fixture: benchmark 8.0 → strategy net 6.1; gap −1.9 pp. +0.5 pp selection does not erase the total gap.
- **Interaction:** Open Evaluation details, attribution method, Coverage and authorized Portfolio. Follow sector, price alert and note have separate capabilities.
- **States:** Missing weights prevent reconciliation; near-zero benchmark prevents capture ratio. Material Follow remains unavailable without a real watcher.
- **Proof:** Common signed attribution scale; cash/cost counted once; decision-time cash reasons; seven comparators and full no-entry/no-fill cohort.
- **Custody:** Do not touch Prophet's unresolved SX05 attribution or older mobile Plans operation. R6 exposes an entry, not a replacement evaluation board.

### H. Amend the existing Fable build.

Paper root: RMC-0.

- **User job:** Deliver a useful integrated consumer, then preserve depth through production and operational proof.
- **Owner / source:** Existing Fable 5.2 T3 thread 2f136a11-91f9-4bca-bf10-8a1d8b7f4e5d and its nine lanes. No new team or control plane.
- **Inputs / identity:** v1.0 B/P/J, 134 stable capabilities, 24 anchors; Prophet v5.1 SI01–SI20 / SP01–SP24; current exact carrier heads.
- **Calculation / claim:** Design/fixture/source/served/scientific/operational acceptance are different. Current numerical designs are illustrative.
- **Interaction:** First real path: Sector → population → Setup → evidence → exact return. Next: retained save/reopen, upstream economics, qualified evaluation.
- **States:** Keep live writers, release holds, denied/unknown effects and unresolved sources. Block the affected capability, continue independent work.
- **Proof:** Real authorized source, ordinary scheduled update or qualified no-change, correction/withdrawal, compatible rollback and exact original reopen.
- **Custody:** Full brief belongs in GitHub; transport is recipient/action/link/return. Delivery is not Fable adoption or a new START receipt.

## 5. Deterministic synthetic fixtures

These are arithmetic/design fixtures, not real observations or an evaluation result. They do not supply point-in-time price histories, trading calendars or scientific validation.

| Fixture | Inputs | Required check |
|---|---|---|
| Aligned US returns | 20 completed sessions; USD total return; market 3.2%, Healthcare 7.6%, HCA 12.2% | Sector-market +4.4 pp; company-sector +4.6 pp; company-market +9.0 pp |
| Compounded relative wealth | Same inputs | (1.076/1.032)-1 = 4.263565891%; (1.122/1.076)-1 = 4.275092937%; (1.122/1.032)-1 = 8.720930233%; label separately from pp |
| Coverage | 60 members; 52 covered, 5 uncovered, 3 unresolved | 52+5+3=60; no coverage-based change to membership |
| Breadth | 42 of 60 above 50-session average; prior 28 of same 60 | 70% current; 46.6667% prior; same member identities required in live data |
| Industries | Counts 12/18/30; above-average 9/14/19 | Counts 60 and breadth 42; rates 75%, 77.7778%, 63.3333% |
| Industry returns | 9.4/8.1/6.2%; weights 25/31.5789473684/43.4210526316% | Weighted sector return 7.6%; issuer counts are not weights |
| Issuer exclusion | Raw 7.6%, HCA 12.2%, start weight 3/49 | Residual peer return 7.3%; 41/59 breadth = 69.491525%; exclusion weight 6.122449% |
| Reporting | 60 eligible, 40 reported, 20 unreported; 32 comparable, 8 not; improved19/weak9/unchanged4 | Every partition reconciles; improvement 19/32 = 59.375% |
| Exclude one comparable improver | From prior reporting fixture | 59 eligible,39 reported,20 unreported,31 comparable,8 noncomparable,18 improved,9 weak,4 unchanged |
| Concentrated aliases | X1 .5 and X2 .3 weights, each +20%; Y/Z .1 each, each −5% | Raw +15%; remove both aliases → peers −5%; 80% excluded |
| Independent emergence | Company +9%, sector −1%, company weight .05 | Excluded peers −1.526315789%; strong company remains reachable with weak group support |
| Falling relative leader | HKD total return market −4%, group −2%, breadth24/60 | +2 pp advantage, wealth-relative2.083333%; both absolute returns still negative |
| Regional cutoff | 2026-11-09T02:30Z; local source available02:29; source event02:20 but available02:31; US source available21:00 | Include first; exclude later-available inputs regardless of earlier event date |
| Historical rhythm | Event session100, first-known103, current115; historical durations18/27/36 | Event age15, information age12; windows118/127/136 remain anchored when current date advances |

### Evaluation v5.1 fixture and safeguards

The existing Prophet source owns the Evaluation figure and its unresolved SX05 write. The following is the arithmetic and disclosure contract for eventual integration, not a replay or a second evaluation screen.

Benchmark sectors A/B have weights .5/.5 and returns 10%/6%: benchmark8%. Policy starting weights are .49375/.19375/cash .3125. Sector policy returns are 10.6875%/6.3125%, cash0. Gross portfolio6.5%; costs0.4pp; net6.1%.

| Contribution | pp | Width at one common signed scale of 120 px/pp |
|---|---:|---:|
| Equity allocation | +0.6 | 72 |
| Cash allocation | −2.5 | 300 |
| Selection | +0.5 | 60 |
| Interaction | −0.1 | 12 |
| Costs | −0.4 | 48 |
| Total active gap | −1.9 | — |

8.0 + .6 − 2.5 + .5 − .1 − .4 = 6.1. Cash and costs count once. The −2.5 cash bar is five times the +.5 selection bar. Actual multi-period evaluation requires its own validated linking method; this is a single-period fixture.

Use **“Includes invested assets and cash”**, **“Starting invested allocation · 68.75%”** and **“Starting cash allocation · 31.25%.”** Do not call those starting weights an average or imply a time series of invested/cash periods. Cash decisions are explained from the information and reasons available at each decision time; a realized market rise does not prove an earlier opportunity.

Missing weights or incompatible capital/basis make reconciliation unavailable. Zero/near-zero benchmark makes a capture ratio unavailable under the predeclared denominator rule. Keep return differences visible; never divide by an unstable denominator to manufacture an impressive capture score. Preserve the existing Record type union and existing actual-holdings authorization.

## 6. Engineering and real-consumer acceptance

Use existing APIs, entity/URL codecs, source references, admission, retained-store, watch/outbox and observability owners. The source amendment defines semantic requirements; it does not mint a second payload registry. A closed-field change needs the owning schema/runtime validator and backward-compatible consumers.

The current lane 1 API accepts only authenticated preview/entitled audience and has a 4 MiB finite-JSON bound. Full member pagination must retain one qualified captured source and access partition using the actual owner's versioned mechanism. Do not add arbitrary generation/path/root/domain queries or silently truncate a full population.

Integrate source unavailable, stale, denied, withdrawn, zero, unresolved identity and unqualified model states independently. A fresh price does not refresh the Sector context. Late responses after account/selection changes cannot commit to the visible or saved record. Corrected evidence links to the original and never silently rewrites saved knowledge.

The minimum integrated witness is actual authorized Sector capture → whole population → a real covered Prophet Setup → exact original evidence → original Sector filters/selection/focus. A second witness proves save/reopen original versus current. Further witnesses prove upstream issuer economics, all-alias exclusion, native Asia cutoff, Follow delivery only when present, Evaluation attribution/coverage and ordinary update/correction/rollback. Complete the original J01–J15/capability acceptance and inherited SP01–SP24; design review cannot stand in for them.

Record backend, Paper, browser, installed persistence, research/science, release and operational outcomes separately. All R6 mockups and this pass's arithmetic checks are **design/fixture evidence only**.

## 7. Custody, verified design work and protected effects

Every R6 write used the existing Mastermind Paper carrier with a fresh observed snapshot and unique operation ID. All writes returned APPLIED_RESPONSE_OBSERVED; none is a new uncertain effect. The manifest records applied IDs, screenshot review, extraction and exact finish operation. Product page focus was not changed. Existing R4/R5 nodes were preserved except the explicitly additive README child.

The original Prophet unknowns remain untouched:

- prophet-sector-20261109-sx05-attribution, file01M3NT5Y3G5HTJHVR0K5W2MDJM, target1G3F-0/root1G21-0.
- prophet-four-turn-t2-20261109-mplans-tabs, same original file, target1EF3-0/root1EEH-0.

Absence of children is not cancellation. Do not retry, recreate, re-home, delete or finish those targets before original-effect reconciliation. R6's independent Evaluation entry does not reproduce the held attribution board.

Source qualification and all actual implementation holds remain with their existing owners. Fable's existing team receives the amendment through **FABLE_V11_AMENDMENT_HANDOFF_2026-11-09.md**, not a new admission or team launch.
