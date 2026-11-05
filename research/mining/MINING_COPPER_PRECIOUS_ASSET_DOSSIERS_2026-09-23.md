# Mining research, Pass 02: assets, economic rights and expectation changes

**Date:** 23 September 2026. **Status:** principal research / proposed requirements / HOLD. **Mission complete:** false. **Fable implementation handoff:** not created.

Operation: `gmi-mining-principal-research-20260923-sol-001`. Existing carrier: Macro draft PR #7795, branch `sol/mining-principal-research-20260923`. Parent: `WS:GMI-THEME-GRAPH`; existing GMI evidence and F04 composition ownership remain unchanged. Protected Mastermind procedure: `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap 1. Original Macro interface baseline: `c4da107fe729e46b4d4036b3e0e290390315d0fd`; no current-main integration or production acceptance is asserted.

## 1. What this pass resolves

Pass 01 established that physical scarcity, economic entitlement and value per share must be separated. This pass tests that proposition against seven connected dossiers: Freeport's asset reporting; Antamina's ore domains; Antamina's two silver streams; Southern Copper's Tia Maria development; Detour Lake's operating and resource boundaries; Kamoa-Kakula's smelter/by-product economics; and Aurubis's earnings, cash conversion and published expectations.

The principal conclusion is a proposed research model: **a mine plan allocates scarce processing time and capital; a contract allocates its proceeds; a security prices an expectation about those proceeds.** A list of metals or a supply-chain diagram alone does not answer the investor's job. Mastermind should explain which of those three allocations changed, which data supports the conclusion, and which missing variable prevents a stronger inference.

A useful development is the recovery of a dated issuer-published analyst benchmark for Aurubis. The prior blanket research gap, “no expectation benchmark acquired,” is narrowed for this one comparison. It is not solved for the whole sector, and the present retrieval does not establish an archived historical receipt. [A21]

This document is editorial research, not a complete technical due-diligence report, investment recommendation, accepted schema, or production dataset. Reported facts, calculations, hypotheses and proposed product behavior are separated below. All additional arithmetic is reproduced by the companion research-only script. A passing arithmetic check does not validate a company valuation or reconcile an unexplained source difference.

## 2. Dossier 1 — Freeport: the same ownership formula cannot be used everywhere

### Selected evidence

Freeport's Q2 filing uses proportionate consolidation for its 72% Morenci interest. Cerro Verde is fully consolidated; its ownership increased from 55.08% to 55.66% during May 2026. PTFI is consolidated despite a 48.76% holding. PTFI's 66%-owned PT Smelting is accounted for under the equity method. These are distinct accounting/control relationships, not one percentage rule. [A01]

The Q2 operating table reports 117 million recoverable pounds of Morenci copper production on the already-proportionate basis, compared with 202 million at fully consolidated Cerro Verde. Across the portfolio, 786 million consolidated pounds less 218 million attributable to noncontrolling interests gives 568 million net pounds. These are production measures, not sales or cash receipts. The release also reports 47 million incremental leach pounds in Q2, a portfolio-level figure. [A02]

The South America operations page still displays 55.08% for Cerro Verde while the filing describes the change. Its process descriptions distinguish Cerro Verde's concentrators and solvent-extraction/electrowinning facilities from El Abra's current leaching operation and proposed sulfide development. The page is useful for process context but not the preferred evidence for the later ownership change. [A04]

### What the model must preserve

A fact needs a **reporting basis** as well as an ownership edge. A model that applies 72% to Morenci's already-attributable 117 million pounds would create 84.24 million pounds and understate the reported interest by 28%. That is an arithmetic error, not a conservative estimate.

Conversely, Cerro Verde's consolidated output is not automatically Freeport's economic entitlement. Applying quarter-end ownership to the entire quarter would also assert a temporal allocation not established by the data. Knowing that a transaction occurred in May does not supply the exact daily production split around its effective date. For the company total, the reported noncontrolling-interest reconciliation is more defensible than inventing that split.

The research representation should therefore preserve four independent observations: the legal/economic interest and effective interval; the accounting method; the basis of the particular operating number; and the issuer's own attribution bridge. Where these do not reconcile, show the residual and the source of uncertainty instead of adjusting the numbers until they fit.

### Recovery, expansion and new capacity are different economic mechanisms

In April, Freeport lowered its expected second-half 2026 Grasberg Block Cave operating level from the earlier approximately 85% to approximately 65%, with material-handling work relevant to the subsequent ramp. This is a dated change to an operating-recovery expectation, not a new copper discovery. [A03]

The proposed dossier should distinguish restoring an existing operation, extracting additional metal from previously placed material, expanding a concentrator, and developing a different orebody/process route. They can have different capital requirements and different effects on the timing of cash flow even when each headline is described as “more copper.”

For the leaching case, investigate how incremental recovery is measured against its baseline, whether recovered metal is incremental to the mine plan or accelerated from a later period, and whether costs and sustaining requirements rise with the expansion. Do not assign the portfolio figure to every leach-capable mine or treat a corporate target as a site-specific guarantee.

**Investment mechanism to test:** more attributable saleable copper from an existing asset base, or a better-supported recovery timetable, could change expected cash generation. **Counter-thesis:** a production improvement may be offset by costs, downtime, inventory accumulation, ownership changes or prior expectations. **Discriminating evidence:** successive mine-specific throughput/recovery/sales observations, exact cost definitions, capital spending, and a matching forecast vintage. No target share price is inferred here.

## 3. Dossier 2 — Antamina: ore domains are part of the meaning of a grade

### Selected evidence

Teck's Q2 2026 Antamina table separates 7.412 million tonnes of copper-only ore and 3.572 million tonnes of copper-zinc ore. Copper grade/recovery of 1.08%/92.0% apply to all processed ore; zinc's 1.73%/84.3% apply only to copper-zinc ore. Reported production is 108.5 thousand tonnes of copper and 54.0 thousand tonnes of zinc. The footnote is decisive. The figures describe the operation; Teck's interest is 22.5%. The PDF table and footnote were visually checked. [A05]

### A falsifiable reconstruction, not a replacement for the reported result

For an illustrative reconstruction, multiply feed by the displayed grade and recovery. With tonnes expressed in thousands:

`Copper reconstruction = (7,412 + 3,572) × 1.08% × 92.0%`

`Zinc reconstruction = 3,572 × 1.73% × 84.3%`

The results are approximately **109.137 thousand tonnes of copper** and **52.094 thousand tonnes of zinc**. Applying zinc grade to all feed instead produces approximately **160.190 thousand tonnes**. The wrong feed basis makes the zinc reconstruction roughly 3.075 times the correctly scoped reconstruction.

Crucially, the correct-domain calculation still does not exactly reproduce reported production. The zinc reconstruction is about 3.53% below the reported 54.0 thousand tonnes. Its residual remains **NOT_RECONCILED**. The document does not silently attribute the entire difference to rounding, alter the grade, or replace the reported output. The research utility also tests the limited question of whether independent nearest-rounding intervals, under an explicitly assumed rounding convention, explain the difference. That convention is a diagnostic hypothesis, not a verified description of Teck's calculation method.

This is an important intelligence distinction. A graph should be able to say, “The relevant ore domain is known; the full production-accounting bridge is not.” It should not choose between falsely clean arithmetic and discarding the whole source.

### Why this changes investment research

A shift in the mix of ore sent to a shared mill can change the metal basket without changing the plant's name or nominal capacity. Our proposed research should ask which material is scheduled, what displaces what, and whether the opportunity is an additional tonne, a higher-value tonne, or an earlier tonne.

**Hypothetical capacity example, not an Antamina estimate:** a mill with no spare throughput replaces 400 daily tonnes earning $30 per tonne of contribution with material earning $50. The incremental contribution is $8,000 a day, not $20,000; the displaced feed has an opportunity cost. Neither figure includes any new mining or development capital unless explicitly added to the example.

The proposed machine model needs an ore-domain link on grade and recovery observations, and an allocation link between a feed source and a processing constraint. A change in grade must not be interpreted as new reserves without the relevant technical evidence. A growth comparison also needs to distinguish ordinary operation from a disrupted comparison period.

**Mechanism to test:** changes in scheduling, recoverability or metal mix can alter asset economics. **Counter-thesis:** better headline grades can coexist with less valuable throughput, worse recovery, higher costs or deferred processing elsewhere. **Evidence needed next:** unrounded production-accounting definitions where available, material-specific operating data, realized product terms, and the mine plan's displaced production. The residual above is not a finding of company misconduct or a basis for a trade.

## 4. Dossier 3 — Antamina's silver: two contracts, one physical mine

### Source-backed relationship model

Wheaton's asset description identifies Compania Minera Antamina and four underlying owners: BHP and Glencore at 33.75% each, Teck at 22.5%, and Mitsubishi at 10%. Its description connects the mine and concentrator to separate concentrate products and port transport. It does not make each shareholder another operator or another physical mine. [A06]

The original Glencore stream has a fixed 100% payable factor on a 33.75% silver interest, reducing to 22.5% after 140 million delivered ounces, with an ongoing purchase price of 20% of spot. [A07] The BHP stream closed effective April 1, 2026: 33.75%, fixed 90% payability, a separate 100-million-ounce threshold before reduction to 22.5%, and the same stated ongoing purchase-price percentage. [A08] BHP describes settlement in metal credits, not physical delivery to Wheaton. [A09]

### Conditional entitlement arithmetic

Adding the headline interests gives 67.5%. That is not automatically the share of a common gross-silver quantity received after contract payability. Under a deliberately simplified, common-gross-production example with both contracts still before their respective thresholds:

`33.75% × 100% + 33.75% × 90% = 64.125%`

If only the BHP stream has stepped down, the equivalent fraction is 54.0%; if only the Glencore stream has stepped down, it is 52.875%; after both step down, it is 42.75%. These are **conditional contract calculations**, not an assertion about the actual threshold state, current deliveries, Wheaton's guidance, or a revised forecast. Contract-specific cumulative deliveries have not been reconciled in this pass.

A period crossing a threshold must be split. In a hypothetical BHP-like contract with 100,000 high-rate delivered ounces remaining, one million common gross ounces cannot all receive the pre-threshold rate. The research utility allocates gross production up to the delivered-ounce threshold, then applies the lower rate to the remainder. Unknown cumulative deliveries must return “threshold state unknown,” not a default assumption that a new high-rate period begins.

The ongoing 20%-of-spot purchase cost is another term. Subtracting it gives a simplified cash spread on delivered ounces, not a return on the upfront investment. Debt, financing, taxes and the timing of the original payment remain relevant to the equity-holder outcome. Do not credit the same physical silver once to the mine owner and again to the stream as new world supply.

### Resource reporting has its own entitlement boundary

The February transaction announcement labels 65.7 million reserve ounces as the BHP attributable silver portion. Its Antamina mine-plan discussion includes a cutoff expressed in dollars per mill-hour, rather than a universal metal-grade cutoff. These are two different clues: the volume already has an ownership basis, and the scheduling criterion values constrained processing time. [A10]

The proposed model must not multiply that attributable reserve number by the BHP percentage a second time. It also must not compare a dollars-per-mill-hour cutoff directly with another project's grams-per-tonne cutoff as though the units measured the same thing.

**Mechanism to test:** a contractual right may offer a different cost, reinvestment and commodity-price profile from owning the mine. **Counter-thesis:** the contract's price, funding, thresholds, timing, asset life and counterparty conditions may already absorb that apparent advantage. **Required evidence:** signed terms and amendments, delivered-ounce balances, funding claims, remaining mine plan and company-level valuation expectations. A stream is not intrinsically superior or inferior to the producer.

## 5. Dossier 4 — Tia Maria: financed construction is not delivered annual output

### Dated primary observations

Southern Copper's first-quarter filing reported Tia Maria progress of 32.5% and $948 million in commitments, with a third-quarter 2027 startup target. [A11] Its July results release reports 42% progress at June 30, $1.101 billion committed and $693 million invested, with startup described as second-half 2027. The planned capacity is 120,000 tonnes a year of cathode through a leaching/solvent-extraction/electrowinning route. Those are project and forecast observations, not current production. [A12]

A June financing announcement describes $1.25 billion of 5.35% senior unsecured company notes due in 2036, with proceeds for the Peruvian branch and broader capital/general corporate purposes. [A14] The June 24 closing notice confirms completion of the issue and gives a $1.802 billion project investment estimate. An earlier expected financing event and a later completed financing event therefore have separate evidence. [A13]

### What changes, and what remains unknown

The project-progress change is 9.5 percentage points. It is not proof that 9.5% of all remaining risks disappeared, or that the rest of construction will proceed at the same rate. A percentage of overall completion cannot be substituted for completion of a specific critical-path system. Likewise, a particular earthworks percentage is not the same denominator as total project progress.

A subtraction of reported project investment from the stated budget yields $1.109 billion of unspent budget on those selected observations. It does **not** establish a financing deficit, available cash, remaining signed payment obligations or the final cost to completion. Budget, commitments, cash paid and consolidated debt need separate definitions and dates before they can be reconciled.

The notes' simple annual coupon is $66.875 million before fees, amortization, taxes or principal repayment. That is a company financing calculation, not a project-level cost per pound. Allocating the whole issue to Tia Maria would contradict the broader use-of-proceeds description. A debt issue also does not certify that every future commissioning or working-capital requirement has been met.

The shift from a third-quarter startup reference to a broader second-half window is not, by itself, proof of delay: the original quarter falls inside the later half-year. Preserve the precision of both statements, and seek a later more specific update before labeling a schedule slippage.

### Research consequences

The prospective timeline should show separately: financing announcement, financing closing, funds available under the actual structure, construction packages, utilities and processing readiness, first material processed, product meeting specification, first commercial sale, and sustained production. These are different questions, not a new lifecycle authority. They should be evidence facets under the existing project and source owners.

**Mechanism to test:** an advancing development may convert uncertain future supply into more credible saleable output. **Counter-thesis:** costs, commissioning performance, schedule, working capital or commodity conditions may offset that reduction in delivery uncertainty. **Evidence needed:** package-level progress, exact funded commitments, commissioning criteria, recoveries, realized product terms and the expectation baseline. This pass has not established that Southern Copper or this project is free of all streams, royalties or other claims; “producer/developer comparator” is the correct description, not “unencumbered comparator.”

## 6. Dossier 5 — Detour Lake: resource aggregates and mine-plan sequencing

### Observations with distinct boundaries

Agnico's Q2 release reports Detour mill throughput of 80,275 tonnes per day, gold grade of 0.97 grams per tonne, and 207,279 payable ounces. It also discusses mine sequencing and maintenance timing. A strong quarter is an observation, not proof of a sustainable annual production rate or of the proposed underground plan's completion. [A15]

The year-end 2025 detailed tables distinguish open-pit, underground and Zone 58N resource components, with reserves separately classified. Those table pages were visually inspected. [A16]

The operating page presents an aggregate of approximately 17.7 million measured-and-indicated and 6.3 million inferred ounces; it also describes a high-grade corridor. [A17]

### A resolved aggregation ambiguity

For measured-and-indicated resources, the open-pit and underground components sum to 13.685 + 3.472 = 17.157 million ounces, rounded to 17.2. Adding Zone 58N's 0.534 gives 17.691 million, rounded to 17.7. Inferred resources similarly sum to 2.290 + 3.878 = 6.168 million, or 6.304 million including Zone 58N's 0.136. [A16] Different aggregation boundaries can therefore explain those headline pairs; they need not represent competing estimates for an identical subject.

This finding does not permit arbitrary addition. The high-grade corridor is a spatial/grade lens that may overlap the already-described inventory. It must not be appended as another independent asset simply because its name or presentation differs. Reserves and resources must also stay separate until the applicable reporting convention establishes whether and how the inventories overlap; no combined reserve-plus-resource total is calculated here.

The proposed ontology needs a relation such as “part of” or “overlapping interpretation,” with evidence and dates, rather than treating every named zone, study boundary and mine plan as disjoint physical tonnes. That relation belongs to the incumbent semantic/evidence owner, not a new global deposit master built by this research branch.

### Timing can create value without inventing more ounces

The 2024 preliminary economic assessment describes bringing higher-grade underground feed forward while deferring some lower-grade open-pit material. Its base-case assumptions include a gold price of $1,900 per ounce and a development-capital estimate of $731 million. Its 18% internal rate of return is conditional on that study's cash-flow assumptions, not a current guaranteed investment return. The initial approved exploration work is not the entire underground investment. [A18]

The research implication is more useful than “underground adds another gold mine.” A shared processing system creates an opportunity-cost problem. Higher-value feed may improve near-term cash generation while another inventory is processed later. A forecast should identify whether the increment is additional lifetime production, earlier production, different recovery, or changed costs.

**Hypothetical timing example:** receiving $100 million in year five instead of year ten, with an assumed 10% discount rate, increases present value by approximately $23.538 million, holding the cash amount constant and excluding all other changes. This illustrates timing only; neither the cash amount nor discount rate estimates Detour's value. The model must not count both an accelerated cash flow and the same original later cash flow.

**Mechanism to test:** better access and scheduling could change the timing or economics of production. **Counter-thesis:** development costs, displacement of other feed, lower recoveries, dilution of grade, or new funding needs may erode the benefit. **Evidence needed:** the actual capacity constraint, an updated comparative mine plan, full capital scope, explicit resource/reserve treatment, and current validation of study assumptions. A quarterly throughput record alone cannot settle those questions.

## 7. Dossier 6 — Kamoa-Kakula: an output can be another producer's input constraint

### Evidence capsule

Ivanhoe's Q2 report says further smelter ramp-up is constrained by concentrate feed. Sulfuric-acid sales were 119,603 tonnes at an average $465 per tonne; approximately $840 per tonne refers to subsequent July/August contracts, not Q2 realization. Reported smelter operating cost of $0.41 per payable copper pound is largely offset by $0.39 of acid credits. The report sells acid to nearby operations and distinguishes costs per pound produced from other measures per pound sold. [A19]

### Proposed economic interpretation

This is a network with potentially opposing economic exposures, not a uniform “copper beneficiary” basket. A saleable by-product may support one operation's cash economics while becoming an input expense for a consuming process. That is a mechanism to investigate; it does not establish that every neighboring miner buys at the same price, that each is acid-constrained, or that a price change causes a specific equity return.

The physical boundary matters. Adding downstream installed capacity does not ensure that the upstream process can supply enough suitable feed. Conversely, new by-product output can change a local input market. Research should identify the **currently binding constraint**, the condition that would relieve it, and the constraint likely to become binding next. It should not permanently assign a bottleneck label to whichever node appeared constrained in the first report.

A useful analytical worksheet would separate concentrate availability, smelter throughput, acid production, acid sales, contract realization, local delivery cost, and required working capital. Sales and production must not be interchangeable. A rounded price multiplied by volume is at most an approximate revenue check, not a substitute for accounting revenue or its timing.

The simplified netback question is: what proceeds remain after the relevant physical conversion, contractual deductions, logistics, operating requirements and reinvestment? It should be answered separately for the integrated producer, the standalone treatment provider and the reagent-consuming producer. Summing all of their revenues would double-count transfers along the same chain.

**Mechanism to test:** upstream recovery, better feed access, coproduct realization or logistics changes could alter cash capture. **Counter-thesis:** feed shortfalls, input prices, unsold inventory, financing and capitalization conventions can defeat a nominal capacity story. **Evidence needed:** node-specific quantities and utilization, ownership/contract boundaries, dated realized prices versus new contracts, and cash conversion. This remains regional, process-specific research—not a claim about a universal worldwide acid price.

## 8. Dossier 7 — Aurubis: operating improvement is not the same as an expectation surprise

### Primary observations

For the nine months ended June 30, 2026, Aurubis reports group operating earnings before tax of EUR 374 million versus EUR 286 million. Custom Smelting & Products operating earnings before tax were EUR 355 million versus EUR 342 million. The report describes weaker treatment/refining-charge effects alongside stronger metal and sulfuric-acid contributions. Group net cash flow was negative EUR 28 million versus positive EUR 357 million, with higher inventory discussed as a cause. Operating and IFRS measures are explicitly distinct. [A20]

The issuer's consensus page, labeled July 14, 2026, shows nine estimates for nine-month operating earnings before tax: mean EUR 363 million, range EUR 341-377 million. It is an issuer compilation of analyst estimates, with a disclaimer, not an audited prediction. This page was retrieved on September 23. [A21]

### The comparison that matters

The year-on-year operating-earnings change is approximately **30.77%**. The actual result is approximately **3.03% above the published mean**, and below that sample's highest estimate. Both calculations can be true. Neither calculation establishes the price reaction, the market's complete expectation distribution, or an exploitable surprise.

The comparison is intentionally narrow: same company, same nine-month interval, same currency and scale, same operating metric. Comparing the operating consensus with IFRS earnings would be invalid. Comparing nine-month actual earnings with a full-year expectation would also be invalid. A range of analyst values is not a statistical confidence interval unless a justified method establishes that interpretation.

This materially improves the research specification. It shows how the system could distinguish “the business improved” from “the result exceeded a stated benchmark.” It also establishes why accurate headline growth is insufficient for an assertion of rerating potential.

### Timing and counterfactual limits

The page's stated estimate date predates the earnings release, but retrieving it now does not establish that Mastermind retained those exact bytes at that earlier time. Store the publisher's as-of date separately from first observed/retrieved time and any accepted immutable receipt. This case supports a presently reconstructed comparison, not a backtest claiming native knowledge on July 14.

Before event-return analysis, recover contemporaneous security prices, release timing, market/session calendars, relevant market and commodity returns, competing disclosures, forecast revisions and an appropriate comparison method. No causal stock-return attribution is performed in this pass. Even a correctly measured earnings surprise can coincide with a different message about future margins, capital or cash conversion.

The earnings/cash-flow divergence adds another required question: is the improvement turning into distributable cash, or is it tied up in inventory and investment? The issuer's explanation is evidence about management's interpretation, not independent proof of duration or reversibility. Research should track the subsequent conversion rather than simply repeat the explanation.

**Mechanism to test:** a durable margin or cash-conversion improvement beyond an identified expectation may matter to valuation. **Counter-thesis:** reported growth could be expected, non-recurring, cash-intensive, offset by future guidance, or already priced. **Evidence needed next:** more than one benchmark vintage, metric reconciliation, the cash-flow bridge and supported event/market data. The proposed system should display these limits beside the conclusion rather than hide them in a generic disclaimer.

## 9. An investor-facing synthesis: seven distinct questions, not seven stock rankings

These dossiers imply seven candidate research lenses. They are not approved baskets, constituent changes or quantitative factors.

| Research lens | Question the user should be able to answer | Key invalidation check |
|---|---|---|
| Attributable operating recovery | Which issuer actually receives an improvement in a specific asset's output? | Already-attributable inputs, ownership timing, sales/inventory and cost offsets. |
| Ore scheduling and processing value | Is the mill receiving more valuable feed, and what feed is displaced? | Ore-domain mismatch, opportunity cost, recovery and the shared throughput limit. |
| Contractual precious-metal exposure | Which terms allocate payable metal and cash, now and after thresholds? | Unknown cumulative deliveries, amendments, upstream operating risk and financing. |
| Development-to-production conversion | Which remaining event changes delivery confidence or cash requirements? | Capacity mistaken for output, commitment mistaken for cash, and unsupported schedule precision. |
| Resource-to-mine-plan conversion | Are new observations additive inventory, overlapping descriptions or earlier access? | Reserve/resource overlap, zone double-counting and displaced future production. |
| Processing and coproduct netbacks | Who earns a coproduct and who consumes it, under which local terms? | Feed limits, realized versus prospective prices, logistics and double-counted transfers. |
| Earnings-to-expectations conversion | How different is a result from a matched benchmark, and does it convert to cash? | Wrong metric/period, revised history, incomplete consensus and unsupported causal attribution. |

This structure preserves the user's stock-price-growth question without pretending that a deterministic ranking follows from a supply constraint. Research priority, scenario valuation and validated trade authority remain separate. A useful descriptive dossier can exist before predictive evidence is sufficient; the product should clearly state which kind of intelligence it is providing.

### Proposed valuation discipline

Do not use one sector-wide multiple to compress these mechanisms. For an existing operation, start with attributable saleable products and their realized terms, then test costs, capital and funding. For a development, retain the schedule, ramp and remaining capital explicitly. For a stream, model the contract's delivered units, thresholds and purchase obligations rather than simply applying mine ownership. For processing, reconcile input/output spreads and coproducts. For the corporate security, reconcile all relevant claims, cash and the diluted share basis.

The scenario worksheet should distinguish an observed change from a changed assumption. Its output can be a transparent sensitivity without being a claim of fair value. When the tax regime, reserve/resource treatment, company debt allocation, working-capital requirement or share basis is not sufficiently established, keep the relevant model component unresolved. Do not fill an attractive scenario with silent defaults.

Joint risks must not be counted as independent simply because different sources discuss them. For example, throughput, recovery, unit costs and cash conversion can be different consequences of the same operating condition. The proposed research should show the dependency and avoid four independent “positive signals” for one underlying event. No numerical correlation or probability is invented here.

## 10. Proposed first product workflow and evidence contract

The eventual user journey should begin with a concrete question, such as: **“What changed in this copper exposure, who captures the change, and what could make the interpretation wrong?”** It should not begin with a requirement to navigate a large graph.

A proposed dossier header would show the conclusion at its actual strength, the material change, the relevant interval, and the most important unresolved condition. The next view would connect commodity/process, asset, economic right and issuer. The user could then inspect the operating bridge, the rights/funding bridge and a matched expectation comparison where available. A source drawer would show the decisive field and its caveat, not just a link to a hundred-page report.

The displayed narrative should be generated from accepted structured observations plus separately labeled analysis. Where a calculation fails to reconcile, the narrative must retain the discrepancy. A model should not be rewarded for smooth prose that hides a broken denominator.

Proposed observations need these dimensions, bound to existing native identities rather than new ad hoc IDs: subject and component boundary; metric and exact definition; unit/currency/scale; gross/proportionate/consolidated/payable basis; observation interval; ownership/contract effective interval; scenario horizon; publisher date; first observed time; source version; supporting location; and uncertainty/reuse status. The same source may be strong for one field and stale or insufficient for another.

Three alternatives were considered. A flat company-to-commodity table is simple but cannot explain the demonstrated differences. A giant new mining graph offers detail but would duplicate incumbent owners and create excessive up-front integration. The proposed approach is a thin, evidence-backed asset/rights dossier under existing owners, expanded through representative cases. This is a research/design recommendation; a written architectural specification, implementation plan, current-owner reconciliation and required acceptance still precede product code.

### Six practical persona tasks for later acceptance

1. Determine whether a displayed production figure already includes the issuer's interest; explain a dated ownership change without double application.
2. Reconstruct a metal-output estimate using the correct ore domain, inspect the residual, and distinguish the estimate from the reported result.
3. Follow a stream's current and conditional terms without treating the claim as extra physical supply or guessing an unknown threshold state.
4. Separate announced capacity, funded construction, startup expectations and saleable operating output, with clear missing evidence.
5. Compare resource inventories only after understanding their physical, classification and overlap boundaries.
6. Compare an earnings result with a metric-matched, dated benchmark while seeing cash conversion and historical-availability limitations.

These are proposed user tasks, not executed browser proofs. They make the implementation goal testable without claiming this research branch has delivered it.

## 11. Twenty additional prospective requirements

Pass 01's MN-01 through MN-30 remain unchanged. The following narrow their application; they are not another runtime control plane or executed application test suite.

| ID | Requirement |
|---|---|
| MA-01 | Carry observation-specific consolidation/proportionate basis, not just an issuer-level ownership percentage. |
| MA-02 | Block a second attribution multiplication and expose unsupported within-period ownership allocation. |
| MA-03 | Resolve apparent source conflicts field by field using applicable dates and definitions. |
| MA-04 | Attach grade/recovery to the correct ore domain and processing interval. |
| MA-05 | Retain reported production beside reconstructed output and an unresolved residual. |
| MA-06 | Do not assert that rounding explains a mismatch without testing a supported rounding model. |
| MA-07 | Represent displaced feed and shared processing capacity in a scenario. |
| MA-08 | Distinguish nominal stream interest, payability and the delivered-ounce threshold. |
| MA-09 | Handle within-period threshold crossing; unknown cumulative deliveries remain unknown. |
| MA-10 | Separate physical settlement, metal-credit settlement and the underlying mine's output. |
| MA-11 | Distinguish project budget, commitments, spending, financing proceeds and actual available funding. |
| MA-12 | Do not allocate a general corporate financing wholly to one asset without evidence. |
| MA-13 | Preserve precision when a quarter-specific target becomes a broader half-year window. |
| MA-14 | Represent resource aggregates, subzones and overlapping grade/spatial interpretations explicitly. |
| MA-15 | Keep reserves/resources separate unless their inclusion convention is established. |
| MA-16 | Distinguish lifetime increments from accelerated cash flow and displaced later production. |
| MA-17 | Map coproduct output and consuming-process input separately, with local contract and logistics scope. |
| MA-18 | Match expectation comparisons on metric, period, currency, scale and subject. |
| MA-19 | Separate publisher as-of date, first retrieval and native immutable historical receipt. |
| MA-20 | Explain earnings changes, benchmark differences and cash conversion separately; no automatic return claim. |

## 12. What was verified, what remains open, and the next tranche

The principal inspected current public issuer sources and selected PDF tables/footnotes, compared accounting and contractual definitions, resolved the Detour aggregation example, and recovered the Aurubis benchmark. The research-only utility checks the document index and arithmetic plus negative cases for invalid assumptions. It does not test the Mastermind application, establish complete source reuse rights, independently audit issuer statements, or validate an investment strategy.

The Antamina zinc accounting residual is still unresolved; a conditional rounding-bound calculation cannot supply the missing accounting explanation. Actual Antamina stream threshold balances, a complete asset-encumbrance census, current full project models, global cost curves, independently reconciled reserve/resource conventions, and a broad point-in-time expectation dataset remain missing. Southern Copper's Q2 filing exceeded the direct HTML fetch limit; selected Q2 project evidence instead comes from its official Spanish results release. No claim of full Q2 filing or global technical-report review follows.

The recovered Aurubis benchmark narrows one gap but is not a reusable historical-consensus pipeline. No analyst-estimate redistribution licence, vendor subscription, source-admission approval or native historical retention has been established by public page access. Only limited editorial extracts and original analysis are included in this public research artifact.

**Next principal tranche:** battery-material and rare-earth process economics, using the same discipline to distinguish product specification, conversion yield, customer qualification, contract realization, capacity utilization and funding. Begin with a small set of integrated versus non-integrated lithium and rare-earth businesses and a processor/customer comparison; select actual primary evidence before freezing constituents or an implementation schema. Carry forward the unresolved copper/precious-metal questions without repeating the completed broad foundation.

Fable remains held until representative sector research is mature and an accepted written design/plan reconciles the existing template, identity, evidence, publication and source-custody owners. No job, worker, watcher, merge, deployment, basket, ranking, entry, sizing or trade was started. Continued research remains the principal's work, not an autonomous background task.

## 13. Source register and access limits

Sources were retrieved on 23 September 2026. Dates below describe publication or reporting intervals, not native historical retention. “HTML” means selected rendered sections; “PDF” means selected text and specified visual table checks, not review of every technical assumption. Source summaries are limited editorial descriptions, not copied reports. All URLs are primary issuer or regulatory locations.

- **A01 — Freeport Q2 filing**, quarter ended June 30, 2026; HTML, consolidation and ownership notes. https://www.sec.gov/Archives/edgar/data/831259/000083125926000036/fcx-20260630.htm
- **A02 — Freeport Q2 results**, July 23, 2026; PDF, production tables visually checked at zero-based pages 12-13. https://s22.q4cdn.com/529358580/files/doc_news/2026/FCX_260723_2Q_2026_Earnings_Release.pdf
- **A03 — Freeport Q1 results**, April 23, 2026; PDF, operating-recovery outlook narrative. https://s22.q4cdn.com/529358580/files/doc_news/2026/FCX_260423.pdf
- **A04 — Freeport South America operations**, current HTML retrieval, undated page; process descriptions and ownership discrepancy. https://www.fcx.com/operations/south-america
- **A05 — Teck Q2 results**, July 22, 2026; PDF, operating-table and footnote screenshots at zero-based pages 10, 12, 26 and 37. https://www.teck.com/media/Teck-Q2-2026-Unaudited-Results.pdf
- **A06 — Wheaton Antamina profile**, current HTML retrieval; ownership/process context. https://www.wheatonpm.com/portfolio/operating-mines/antamina/default.aspx
- **A07 — Original Glencore silver-stream announcement**, 2015; official release text, historical contract terms. https://www.wheatonpm.com/news/news-details/2015/Silver-Wheaton-acquires-silver-stream-from-Glencores-Antamina-mine/default.aspx
- **A08 — Wheaton/BHP stream closing**, April 1, 2026; official release text, effective date and terms. https://www.wheatonpm.com/news/news-details/2026/Wheaton-Precious-Metals-Announces-Closing-of-Silver-Stream-with-BHP-on-Antamina/default.aspx
- **A09 — BHP stream closing**, April 2, 2026; official release text, settlement description. https://www.bhp.com/es/news/media-centre/releases/2026/04/bhp-completes-silver-streaming-agreement-with-wheaton-precious-metals
- **A10 — Wheaton transaction announcement**, February 16, 2026; HTML, attributable reserve quantity and mill-hour cutoff. https://www.wheatonpm.com/news/news-details/2026/Wheaton-Precious-Metals-Announces-Acquisition-of-Additional-Silver-Stream-on-Antamina-Through-New-Partnership-with-BHP/default.aspx
- **A11 — Southern Copper Q1 filing**, March 31, 2026 reporting date; selected official filing text. https://www.sec.gov/Archives/edgar/data/1001838/000110465926052647/scco-20260331x10q.htm
- **A12 — Southern Copper Q2 Spanish results**, July 21, 2026; PDF project narrative, June 30 observations. https://southerncoppercorp.com/wp-content/uploads/2026/07/np260721.pdf
- **A13 — Southern Copper financing close**, body dated June 24, 2026; Spanish PDF. Body date controls over stale template/header metadata. https://southerncoppercorp.com/wp-content/uploads/2026/06/pr260624.pdf
- **A14 — Southern Copper note offering**, June 17, 2026; issuer-hosted filing PDF, terms and use of proceeds. https://southerncoppercorp.com/wp-content/uploads/2026/06/8k260617_2.pdf
- **A15 — Agnico Q2 results**, July 29, 2026; HTML, Detour operating figures and qualifications. https://agnicoeagle.com/English/news-and-media/news-releases/news-details/2026/AGNICO-EAGLE-REPORTS-SECOND-QUARTER-2026-RESULTS---RECORD-QUARTERLY-FREE-CASH-FLOW-REFLECTS-SOLID-OPERATIONAL-PERFORMANCE-RECORD-QUARTERLY-SHAREHOLDER-RETURNS/default.aspx
- **A16 — Agnico detailed mineral inventory**, December 31, 2025 effective date, February 2026 publication; PDF, visual checks of zero-based pages 0 and 3. https://s205.q4cdn.com/243646470/files/doc_downloads/agnico_downloads/RnR-Tables/2025/AEM_YE_2025_MRMR_Tables_Detailed_Feb12_2026.pdf
- **A17 — Agnico Detour operating profile**, current HTML retrieval; aggregate inventory and corridor descriptions. https://www.agnicoeagle.com/English/operations-and-projects/global-operations-and-development-projects/detour-lake/default.aspx
- **A18 — Agnico Detour preliminary study**, June 19, 2024; HTML, historical sequencing, capital and conditional return assumptions. https://www.agnicoeagle.com/English/news-and-media/news-releases/news-details/2024/AGNICO-EAGLE-RELEASES-DETOUR-LAKE-PROPOSED-UNDERGROUND-MINING-PLAN-DEMONSTRATING-STRONG-RETURNS-AND-PATHWAY-TO-ANNUAL-GOLD-PRODUCTION-OF-ONE-MILLION-OUNCES-06-19-2024/default.aspx
- **A19 — Ivanhoe Q2 financial/operating report**, 2026, quarter ended June 30; HTML, feed constraint, acid realization and cost definitions. https://www.ivanhoemines.com/news-stories/news-release/ivanhoe-mines-issues-2026-second-quarter-financial-results-overview-of-operations-and-exploration-activities/
- **A20 — Aurubis nine-month report**, August 6, 2026; interval October 1, 2025-June 30, 2026; PDF with zero-based pages 1 and 7 visually checked. https://www.aurubis.com/en/dam/jcr:28af3925-b00a-4899-86b5-c34dd376fb17/Aurubis_Quarterly%20Report_Q3_2025_26.2026-08-06-05-59-59.pdf
- **A21 — Aurubis issuer-compiled consensus**, page labeled July 14, 2026; HTML retrieved September 23, not a contemporaneously captured historical snapshot. https://www.aurubis.com/en/investor-relations/aurubis-share/consensus

## 14. Continuity and immutable evidence

Pass 01 remains unchanged at commit `1991c91bc6ca7678a455cabaf38bdfe14e800028`, blob `d107e5527a898c834c26b4869d6de7e51b254af1`. Its earlier checks are historical receipts, not newly rerun application tests. The in-turn checkpoint for the present tranche was written and read back at `7b1df7f8fc49a21cb73e06079038ed6d6e3c19b2`, blob `54fe94cabd2070bbc5dfe1fcc2ec2a5b095a1b75`.

The final continuation record must bind this report and its actual new arithmetic receipt to their immutable GitHub revisions. These documents are a research contribution on the same draft/HOLD carrier, not main-canonical implementation law. No source-custody transfer, automatic wake or completed mission is implied.
