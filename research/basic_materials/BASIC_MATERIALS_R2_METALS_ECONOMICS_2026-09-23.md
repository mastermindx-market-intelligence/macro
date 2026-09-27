# Basic Materials Theme Intelligence
## R2 — Copper, aluminium and steel: from operating economics to equity rerating

**Research date:** 2026-09-23  
**Operation:** `gmi-basic-materials-research-20260923-sol-001`  
**Incumbent carrier:** Macro PR #7796, `sol/basic-materials-research-20260923`  
**Status:** Principal research and design proposal; not an accepted implementation specification or current stock recommendation.  
**Parent mission:** Incomplete. Eventual Fable CEO integration remains ahead, not delivered, acknowledged or started.

## 1. Research outcome and scope

R1 established that Materials intelligence must distinguish material conditions, operating economics, company cash flow, per-share value and market/entry context. R2 now tests that direction against five operating businesses: Freeport-McMoRan, Antofagasta, Aurubis, Hydro and Nucor. Copper is examined across production and processing; aluminium and steel test whether the proposed framework handles opposite exposures inside integrated businesses.

The resulting product direction is **a business-specific explanation of the change in expected shareholder economics**, rather than a uniform commodity-strength score. The useful question is not merely “which material is scarce?” It is “which business can convert the observed change into incremental cash, when, on what financial-claim basis, and how much of that change was already expected?”

This annex adds worked accounting reconciliations, conditional rerating hypotheses, a granular research-cohort design and production acceptance requirements. It does not establish complete sector coverage, causal identification, prospective alpha, current valuation attractiveness or a buy/sell decision. Reported periods below differ intentionally; the cases are analytical discriminators, not a synchronized current-market comparison.

### Canonical integration boundaries

Protected Mastermind procedure remains pinned to `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap 1. The current turn re-read protected master and INDEX; required companion procedures were already loaded at this identical unchanged revision. Research remains on the existing operation and PR.

The R1 foundation is preserved unchanged at `research/basic_materials/BASIC_MATERIALS_RESEARCH_FOUNDATION_2026-09-23.md`, blob `31cfbcdae510940e09161a4989b360df0b4f6818`. The existing shared STSI architecture, GMI Theme Graph/ThemeState, source-native evidence and identity owners, MarketOntology F04, Prophet and Evaluation OS retain their responsibilities. R2 creates no graph, source warehouse, lifecycle, correction, publication or decision authority. The neighboring template is a dependency to consume, not a design to replace.

## 2. Worked business cases

The source register in section 10 identifies each original source and locator. Figures below are selected facts and original calculations, not reproductions of entire statements. All derived residuals are explicitly named; none is silently relabelled as an issuer's free-cash-flow measure.

### 2.1 Antofagasta: cost improvement and cash conversion answer different questions

Antofagasta's H1 2026 production release reports cash costs before by-products of $2.85/lb, by-product credits of $1.63/lb, and net cash costs of $1.22/lb. It describes gross costs rising while net costs fell. Its H1 cash-flow statement separately reports $2,772.9 million cash from operations, $252.7 million interest paid, $926.8 million tax paid and $1,593.4 million net operating cash. Cash purchases of property, plant and equipment were $1,672.1 million. [M01, M02]

The two calculations are:

`2.85 - 1.63 = 1.22 dollars per pound`

`2772.9 - 252.7 - 926.8 = 1593.4 million dollars`

`1593.4 - 1672.1 = -78.7 million dollars`

The last line is our **reported net operating cash less cash PP&E purchases**, not the company's official free cash flow and not cash available to parent shareholders. It excludes separately classified receipts, acquisitions, lease financing, minority distributions and other financing flows. Starting instead with the headline operating figure gives `2772.9 - 1672.1 = 1100.8`; the $1,179.5 million difference is exactly the interest and tax already identified. The two measures are not interchangeable.

**Interpretation for the proposed system.** A lower net copper cost can reflect stronger gold or molybdenum credits rather than better ore throughput or physical efficiency. Both can be economically valuable, but they imply different durability, sensitivities and basket exposures. Likewise, investment-phase cash consumption need not invalidate a profitable asset thesis; it changes the timing and financing analysis needed before assigning value to common equity.

We therefore propose displaying two independent explanations: what changed in unit economics, and what happened to cash after the issuer's actual tax/interest/investment classifications. Neither should overwrite the other with a single “fundamentals improving” label.

**Reconciliation boundary.** The management net-debt table shows cash from operations of 2,772.8 versus 2,772.9 in the primary cash-flow statement. Both values remain preserved with their locators. Net debt increased by 1,216.6, reconciled in the management bridge through 574.6 cash movement, 645.6 noncash movement and a 3.6 favorable FX offset. Net-debt movement is therefore not a substitute for a simple free-cash-flow calculation. [M02, physical pages 21 and 29]

A separate late-page APM extraction differed from the production headline. The relevant page images were not retrievable. It remains **UNVERIFIED_SOURCE_RECONCILIATION**; we do not assert that the company made an error, choose a cause, or admit the extracted metric into a feature. The headline calculation above uses the independently accessible production release.

### 2.2 Freeport: consolidation, unusual receipts and excluded costs

Freeport's H1 2026 cash-flow statement reports $3,543 million operating cash flow, $2,077 million capital expenditure and a $699 million insurance receipt. Its Indonesia Q2 unit-cost discussion reports a net credit of $0.81/lb while excluding $1.86/lb of idle-facility/restoration costs. PTFI is fully consolidated despite Freeport's 48.76% ownership interest. [M03]

Our two cash calculations are:

`3543 - 2077 = 1466 million dollars`

`3543 - 2077 - 699 = 767 million dollars`

The second removes exactly one identified receipt. It is **not** a full normalization, sustainable cash-flow estimate or parent-distribution capacity. Related operating disruption, insurance accounting, taxes, replacement investment and future receipts require their own analysis. It is a sensitivity to a stated classification, not a claim that the receipt should always be ignored economically.

The cost arithmetic is similarly limited:

`-0.81 + 1.86 = 1.05 dollars per pound`

This adds back one specifically excluded expense. It does not create a new published unit cost or all-in cost measure. The important requirement is to carry the sign, exclusion set, denominator and operating perimeter. A negative net cost is not proof that operating the mine consumes no economic resources.

**Interpretation for the proposed system.** The same issuer needs distinct production, cost, cash-flow and ownership views. Consolidated output cannot automatically become attributable output, and consolidated operating cash cannot automatically become common-shareholder cash. Income attribution and actual cash distributions are also different measurements.

The filing additionally describes provisional pricing, later settlement and hedging mechanics. These support a research requirement for a **realization calendar**: what volume has been sold, which price remains open, what settlement window applies, what exposure is net of hedges/intercompany flows, and what part is attributable to the parent. A spot copper-price change is not a complete revenue or earnings sensitivity. [M03, sales/pricing and operating-review sections]

A practical first implementation should show source-reported sensitivities with their original scope and assumptions, not reconstruct a falsely exact sensitivity from rounded volumes. Do not subtract a parent interest twice when a figure is already attributable; do not exclude a project's debt while retaining its full cash generation in the same valuation perimeter.

### 2.3 Aurubis: accounting profit, operating profit and cash can diverge

Aurubis's nine-month 2025/26 report presents IFRS earnings before tax of EUR1,272 million and operating EBT of EUR374 million after EUR898 million of adjustments. Reported net operating cash was negative EUR28 million. Its company-defined free cash flow was negative EUR435 million and includes dividend payments. Management attributes part of the cash pressure to inventory build associated with Pirdop commissioning; the anticipated release remains an expectation, not an observed outcome. [M04]

`1272 - 898 = 374 million euros`

The operating-cash components displayed in whole millions sum to -27 while the statement reports -28. The displayed free-cash-flow components similarly sum to -436 versus the reported -435. Those one-million residuals remain recorded. We neither alter a source cell to force equality nor infer a substantive accounting error from rounded presentation.

**Interpretation for the proposed system.** Rising earnings, a large inventory position and weak cash conversion can coexist. A research card should explain whether the discrepancy concerns metal-price measurement, working capital, new plant inventory, maintenance, operating margin or distributions. It should not automatically call the economic thesis broken because cash is temporarily negative; equally, it should not treat management's expected cash release as already realized.

The processor model must track compensation for processing, recoverable metal, by-products, purchased feedstock, conversion cost, hedges and inventory funding inside a declared boundary. “Treatment charges fell” is a relevant observation, not a complete company forecast. The accepted synthesis should explain which competing components dominate and what future observation would change that interpretation.

A useful rerating hypothesis is **cash-conversion improvement after a verifiable operating milestone**, conditional on inventory actually normalizing without damage to recurring margins. This is testable through subsequent operating and cash reports. It is not proven by a commissioning announcement alone.

### 2.4 Hydro: integration creates offsets, not several independent bets

Hydro's Q2 2026 release attributes weaker Bauxite & Alumina performance partly to lower alumina prices while Aluminium Metal benefited from higher all-in aluminium prices and lower alumina cost. Its quarterly report shows adjusted EBITDA of NOK522 million for Bauxite & Alumina and NOK6,421 million for Aluminium Metal. Group adjusted EBITDA was NOK8,923 million. The report's Other and eliminations line is negative NOK13 million, versus positive NOK1,241 million a year earlier; eliminations mainly concern unrealized gains/losses on intra-group inventory. [M05, M06]

The current five operating-segment values sum to 8,937. Including the published -13 gives 8,924, leaving a -1 residual against the reported group total. The prior-year five segments total 6,549; adding 1,241 reconciles exactly to 7,790. The apparent large prior-year gap was therefore a missing consolidation line, not evidence of an unknown sixth independent economic business. [M06, physical pages 5 and 17]

**Interpretation for the proposed system.** An integrated company's upstream and downstream segments can respond oppositely to a common input. An alumina producer's favorable price move can be a smelter's cost problem. A group with internal transfers cannot be modeled by summing several unconstrained segment sensitivities as though each traded wholly with outside customers.

We propose scenario calculations first at operating-segment level, then consolidation and financial-claim reconciliation. Internal margins and inventory eliminations must be removed on the group boundary. The product may show an aluminium producer, refiner, energy position and downstream fabrication role, but those labels do not establish four independent confirmations or four additive exposures.

The relevant research variables include realized metal price and regional premium, actual alumina cost with contract lag, electricity contract/hedge exposure, currency, product mix, utilization, recycling economics and consolidation. A terminal commodity quote is not equivalent to the quarter's realized price. Recycling profitability can also be embedded within other segments rather than exist as an extra additive segment.

The candidate rerating mechanism is **an improving realized conversion margin and cash return on operating assets**, potentially before downstream volume recovers. Its invalidators include offsetting energy/currency costs, adverse realization lags, weak product mix, financing demands and reversals in inventory-related effects. These are proposed tests, not a current attractiveness judgment about Hydro.

### 2.5 Nucor: adjusted earnings and fresh information need separate treatment

Nucor's July 27 release reports Q2 diluted EPS of $5.04 and adjusted EPS of $4.84. The adjustment removes a $0.20-per-share noncash investment benefit. The same release includes a $130 million reduction in steel-mill cost of sales from cash refunds relating to earlier raw-material procurement. Both items had already been identified in June 17 guidance. [M07, M08]

`5.04 - 0.20 = 4.84`

The June adjusted-guidance range was $4.50–$4.60; its midpoint is $4.55. Actual adjusted EPS was $0.29 above that midpoint. This is **actual versus management guidance**, not actual versus analyst consensus, not the market's surprise, and not evidence of a profitable trading response.

**Interpretation for the proposed system.** “Adjusted” does not automatically mean recurring. A valid extraction must preserve what the issuer adjusted and what it left in the measure. A model should not strip all unusual items mechanically either: a cash recovery can matter to balance-sheet value even when it is not a repeatable quarterly margin driver.

Nucor's filing reports improved steel-mill metal margins but lower steel-products gross margins year over year because increased steel input costs outpaced sales-price and volume gains. Scrap-input costs use a gross-ton denominator, whereas the sales table uses per-ton finished sales. Total mill shipments and external mill sales are also distinct: 7,100 less 5,659 equals 1,441 thousand source-reported tons of internal shipments. [M09, M07]

The correct model separates a steel mill, downstream fabricator, raw-material supplier and integrated group. It must bind quantity units and conversion yield before deriving a numeric steel-minus-scrap spread. R2 deliberately does not publish such a spread from an unresolved common denominator. The difference between gross ton and a table's unqualified ton is not fixed by deleting the adjective.

A second rerating hypothesis concerns **start-up losses giving way to profitable utilization**. The filing defines when the company ceases to treat a facility as in start-up. Research should distinguish a paper change in classification from evidenced throughput, product acceptance, contribution and cash return. This is a mechanism to investigate, not a license to add every current start-up cost back permanently. [M09]

## 3. Copper physical-state model: preserve the stages

The ICSG Factbook defines refined usage at the semi-fabricator/first-user level. Its apparent-usage calculation incorporates refined production, net trade and stock changes. Total copper use also includes directly melted scrap; refined usage is not the same as final consumer demand. Its stock definition does not include semi-fabricated products such as wire rod or tubes. [M10, printed pages 3 and 35; physical pages 8 and 40, visually inspected]

These definitions resolve a foundational design question: **Mastermind needs stage-specific balances and cannot use one “copper demand” field for every mechanism.**

The following are proposed research objects, to map into accepted owner-native contracts only after review:

| Research object | What must be bound | What it cannot prove alone |
|---|---|---|
| Ore and contained-metal production | Asset, grade, recovery, process, ownership, period | Payable sales, current refined availability or cash realization |
| Concentrate market | Specification, payable content, processing terms, impurities, delivery basis | Global refined-metal shortage |
| Refined-metal market | Refined production, applicable trade, measured usage, inventory definition | Final end-user consumption in every geography |
| Fabricator demand | Orders, production, shipments, inventory and customer/product mix | Equivalent growth in all upstream businesses |
| Secondary supply | Direct melt versus re-refined route, scrap grade, recovery and collection basis | Additive supply if already counted in the reported refined balance |
| Deliverable exchange stock | Venue, brand, warehouse, warrant state, reporting lag | All global stocks, all commercially available metal or final consumption |
| Project pipeline | Source-vintage milestones, usable output, financing, process and dependencies | Current production or a calibrated probability of timely arrival |

### Material balance discipline

A balance is only meaningful inside a stated physical boundary. For a defined refined-material population, measured supply, imports, exports, usage and stock movements need compatible units and periods. Residuals should be visible and interpreted against measurement uncertainty; they are not automatically hidden demand or an investment signal.

The system must not add mine output to refinery output as two independent quantities of the same copper. Nor should it add direct-melt scrap to a refined-production total without checking whether the intended demand definition includes that route. Processing losses, recirculating internal material and by-products require process-specific treatment, not a universal conversion coefficient.

**A useful theme page should answer “tight where?” before “tight overall?”** Tight concentrate availability, regional cathode availability, qualified high-conductivity product demand and long-term project scarcity can describe different economic populations and horizons. They may reinforce one another, conflict, or simply be incomparable.

### Exchange-stock and availability clocks

LME's dedicated off-warrant material describes daily T+1 subscriber availability and delayed T+3 public availability. The off-warrant release distinguishes that category from live warrants and cancelled tonnage. The broader warehouse overview still includes older monthly wording, so a generic overview should not override the more specific dated reporting description. [M11, M12]

Proposed stock observations therefore preserve venue, material/brand, warehouse location, warrant state, quantity, reference date, publication/availability time and coverage. A title transfer, warrant cancellation, physical withdrawal and downstream consumption are separate events. Do not count them as interchangeable confirmations.

For a retrospective experiment, today's availability is not evidence that the same observation was obtainable at the earlier decision time. Public visibility does not itself establish a commercial redistribution right or entitlement to an API. Existing Mastermind source owners must verify rights and actual subscription coverage before implementation.

### Forecast-vintage boundary

The ICSG April 23, 2026 forecast landing page was recovered and identifies a later site-update date. Its linked PDF body was not recovered through the attempted route. R2 therefore does **not** admit a quantitative current global surplus/deficit claim from summaries elsewhere. [M14]

This lane-local limitation does not erase the verified Factbook definitions. It demonstrates the intended separation between known physical definitions and an unverified current forecast. Historical forecasts must retain their original vintage, horizon, revisions and realized comparison; a later forecast cannot be substituted into a prior decision.

## 4. Granular research cohorts and company roles

These are proposed research cohorts, not accepted GMI nodes, traded baskets or rankings. The five issuers are seed cases with source-supported operating roles, not a complete constituent census or a resolved security master.

### Copper

**Operating sulphide/concentrate producers.** Research grade, recovery, throughput, payability, treatment terms, by-products, delivery and sustaining investment. Freeport and Antofagasta provide seed disclosures, but individual assets must be resolved rather than treating all group output as one process.

**Leach/electrowinning operations.** Investigate leach kinetics, recoverable inventory, acid/energy, ramp-up and saleable cathode. Do not force these operations through a smelter-fee model. No numerical unit-cost or recovery assumption is adopted in R2.

**Complex-feedstock smelting and recycling.** Aurubis is a seed case for distinguishing processing fees, recoverable metals, by-products, product economics and inventory funding. Research feedstock capability does not prove capacity availability or pricing power for every material.

**Refining, wire rod, foil and fabrication.** Research conversion fees, order/backlog changes, product quality and customer qualification. A copper-price rise can inflate sales while increasing funding needs; it is not itself proof of higher conversion margins.

**Developers and expansion projects.** Track financing, construction, commissioning, qualification and cash requirements separately from operating-production exposure. A large resource statement is not a funded operating business. Full project/financing research remains part of the next broader units.

### Aluminium

**Bauxite/alumina supply; primary smelting; integrated producers; remelt/recycling; extrusion and specialty fabrication** should be independently navigable descriptions. Proposed comparisons should distinguish purchased versus captive alumina, contracted versus exposed energy, regional premiums, metal-quality requirements, customer markets and group eliminations.

Hydro is an integrated seed case, not proof of the economics of every pure-play aluminium producer or recycler. Its value here is showing why a single material narrative can have different effects inside one company.

### Ferrous materials and steel

Proposed cohorts are **steelmaking inputs; scrap/DRI supply; electric-arc steelmaking; blast-furnace/basic-oxygen steelmaking; flat products; long products; plate; specialty grades; and downstream fabrication**. Nucor supports an initial mill/raw-material/downstream integration case. R2 does not yet provide an independent blast-furnace case or complete regional steel cost curve.

Product and process must remain separate attributes. A sheet-steel basket is not the same thing as an electric-arc-furnace basket, and neither is an automatic demand basket for every construction use. A downstream fabricator can face a different price-reset schedule from the mill supplying it.

### Membership and exposure rules

Source-scoped business descriptions should first connect to the existing company identity. Security/listing resolution, source-family rights and any canonical-theme mapping remain existing-owner decisions. Revenue share, production share, ownership share, scenario cash-flow exposure and share-price beta remain different measurements.

A company may participate in multiple research cohorts without its economic exposure being duplicated. The measurement view should disclose overlap and internal transfers. No exposure percentage should be invented from a company description, and no current constituent list should be silently used as historical membership.

## 5. Rerating research: what to detect before a mature stock move

The following are **candidate explanatory mechanisms and prospective hypotheses**, not established predictive models. A favorable mechanism only becomes relevant to an equity decision after expectation, valuation, financing and existing entry context are considered.

| Mechanism to investigate | Early evidence to seek | Cash/equity transmission | What would weaken the interpretation |
|---|---|---|---|
| Realized margin widening | Contract resets, realized premiums, output/input lags, comparable mix | Higher contribution on actual saleable volume | Cost inflation, hedges, lost volume, temporary credits or adverse product mix |
| Volume/grade/recovery inflection | Comparable operating measures and bottleneck removal | More payable units through the existing asset base | Poor recovery, grade trade-offs, downstream constraints or capital overrun |
| By-product profitability | Credited quantity, ownership and realized price | Higher net revenue or lower reported net cost | Unstable by-product volume/prices, changed accounting allocation or offsetting charges |
| Working-capital release | Actual stock normalization and settlement after an operating milestone | Cash conversion without assuming an earnings change | Inventory merely moved category, supply damage, weaker demand or replacement funding |
| Project cash-flow transition | Verified commissioning, qualified output and declining remaining investment | Cash consumption shifts toward sustainable operating generation | Ramp-up failure, customer rejection, new spending or dilution |
| Contract/cost de-risking | Disclosed duration, pricing basis, exposure and counterparty obligations | Lower volatility or improved expected cash conversion | Incomplete pass-through, unfavorable lag, volume weakness or credit exposure |
| Capital discipline and balance-sheet repair | Cash deployment, debt/claims reconciled, funded plans | More value attributable to continuing common shareholders | Buybacks funded by borrowing, inadequate sustaining investment or hidden obligations |
| Genuine expectation revision | New comparable guidance or evidence relative to its prior vintage | Change in expected future cash, not merely a strong headline | Previously disclosed items, a mismatched denominator or already-rich valuation |

### 5.1 The four questions that should precede an “early opportunity” description

**What changed economically?** Identify a new material observation rather than restating a structural story. The observation can concern supply, demand, margin, operating execution, financing or a measured valuation assumption.

**Where does the change enter the financial model?** Show the affected input, sign, quantity basis and timing. A treatment-charge change has a different location in a miner's and processor's calculation. A refund is different from a recurring lower procurement price. A project milestone affects both remaining investment and expected delivery, not just a narrative score.

**What was already expected?** Preserve prior management guidance separately from analyst consensus, forward-price assumptions, model estimates and historical-normal benchmarks. Missing consensus means no consensus-surprise claim, not zero expected growth.

**What has the market already reflected?** Consume the existing owners' relative strength, participation, valuation and entry observations. Do not infer “early” from a fundamental improvement alone. A stock can have moved before a reported result, or a seemingly cheap multiple can reflect peak-cycle earnings.

### 5.2 Proposed timing horizons

Use the actual contract, operating and funding clocks rather than impose one universal horizon. Processing-fee renegotiation, inventory liquidation, permit progress, mine ramp-up and valuation response can occur at different times.

For each hypothesis, specify the observable next milestone, the date or interval supplied by the source, and the evidence required to distinguish success from delay. Historical replay must use the original scheduled milestone and its revisions, not the eventual outcome date backfilled into history. Unknown dates remain unknown.

### 5.3 Avoid turning uncertainty into an uncalibrated score

A scarcity or rerating probability needs explicit target, horizon, eligible universe and calibration. Until those exist, publish structured evidence and conditional interpretations. Do not combine inventory tightness, earnings surprise, price strength and a project announcement into a 0–100 score merely because all can be normalized.

The initial user value can be substantial without a prediction claim: show what changed, the business that may benefit, the relevant cash bridge, opposing evidence, the next observation and the existing market context. Prediction admission should follow evidence of incremental performance, not precede it.

## 6. Valuation and sensitivity contract proposed for later design

No target prices or issuer valuations are calculated in R2. The proposed model below specifies what a future analysis must declare.

### 6.1 Operating scenario inputs

For each material/business period, record payable sales, realized benchmark basis, premium/discount, hedges, processing/service income where applicable, non-overlapping by-products, costs, working capital and investment. Some inputs will be source-reported, some derived, some explicitly hypothetical. Their statement modes cannot collapse.

A schematic scenario can evaluate:

`incremental operating contribution = change in external realized receipts - change in non-overlapping operating costs`

`incremental cash = incremental operating contribution - incremental relevant tax - incremental investment - incremental working-capital requirement - other declared cash effects`

These are analytical boundaries, not accounting-standard definitions. If starting from reported CFO, do not subtract working capital or tax already included. If starting from an equity cash flow, do not apply an enterprise-value debt subtraction again.

### 6.2 Nonlinearity and scenario interaction

A single commodity-price derivative is not enough when output, cost, by-products, investment and financing co-vary. The research should test one-variable sensitivities for explainability and combined scenarios for realism. A high-price scenario may improve receipts while increasing royalty, tax, working capital, procurement cost and replacement investment.

If scenarios use probabilities, identify their source and calibration; do not invent probabilities merely to produce an expected value. Otherwise show named cases, assumptions and sensitivities without probability labels. A forecast range must not be portrayed as a statistical confidence interval unless that interpretation is justified.

### 6.3 Ownership and equity bridge

Define whether an operating valuation is consolidated, proportionate, project-level or already equity-level. Reconcile debt, minority/preferred claims, cash restrictions, leases and other obligations consistently. Share count must reflect the valuation scenario's financing and dilution assumptions.

A lower debt figure excluding a development business cannot be combined without explanation with full consolidated cash generation. A royalty holder cannot inherit the mine operator's production-cost sensitivity automatically. The next precious-metals/project unit should stress-test these financial-claim differences directly.

### 6.4 Valuation state versus entry state

The product should display whether the proposed upside comes from improved normalized cash, a lower required return, a better financing outcome, greater attributable ownership or a changed multiple. It must also disclose assumptions that explain why the equity might already be priced for that improvement.

Entry eligibility stays with the existing technical/decision owner. Economic evidence may justify research attention while the trade remains ineligible. A strong thesis and a poor entry are not necessarily contradictory.

## 7. The product workflow this research should enable

This is an extension proposal for the shared template, not a new dashboard or approved interface.

**User journey:** existing Theme Tracker or sector surface → material/subtheme dossier → business-role explanation → company/asset exposure → source and financial bridge → existing stock/watchlist workflow.

The first screen should offer a compact synthesis of the material change and its economic consequence. The detail should progressively disclose five separate views:

**Economic change.** What changed, in which material form/location, and over what horizon? Is it reported actual, preliminary, guidance, a calculation or a hypothesis?

**Who captures the change.** Display business roles and conditional effects. Avoid a universal green “copper” label applied to all miners, processors and fabricators.

**Cash and valuation consequence.** Show the bridge, its perimeter, material exclusions, remaining investment and shareholder claims. Permit “not measurable yet” where the evidence is insufficient.

**Expectation and market context.** Show what was known before, how the current observation differs, and the separate existing leadership/entry dimensions. Never label management-guidance variance as consensus surprise.

**What changes the read next.** A dated observation or milestone, opposing evidence and explicit missing inputs. The user should leave knowing why the system is paying attention and what would justify changing that attention.

### Recommended initial real-data proof set

The eventual first slice should demonstrate the distinctions with a small number of accepted public-source observations before broad automated coverage:

- Antofagasta: gross cost versus by-product-net cost, plus operating cash before/after tax and interest.
- Freeport: consolidated cash versus specified-receipt sensitivity and parent ownership limitations.
- Aurubis: IFRS/operating earnings versus inventory-related cash conversion.
- Hydro: opposite upstream/downstream movements with the actual consolidation bridge.
- Nucor: adjusted-earnings definition and information already present in prior guidance.

This is a proof-set proposal, not a live basket or immediate implementation commission. The integration owner must still reconcile native contracts, lawful private/public transport, source retention, corrections and shared-template custody. No full-fidelity paid evidence is authorized into public Git.

### What must not be built separately

No dedicated Materials evidence warehouse, new universal product/security identity service, standalone hypothesis propagation graph, duplicate ThemeState producer, new source scheduler, duplicate correction mechanism or independent publishing plane. The design should extend the existing owners' accepted contracts and compose their outputs through F04 and the shared page grammar.

## 8. Verification, evaluation and acceptance design

### Executed research checks

`R2_RESEARCH_ARITHMETIC_VERIFICATION_2026-09-23.json` records **31 exact arithmetic checks** and **4 retained displayed-precision/source residuals**. These validate selected stated inputs and arithmetic, not every source fact, product behavior, a full accounting audit or predictive performance. Three semantic admission cases remain held: the Antofagasta late-page extraction, a source-specific common steel/scrap output denominator, and the unrecovered ICSG forecast body.

The initial local-file write encountered directory permissions. The directory and absence of a prior output were checked, permissions on this research directory were corrected, and the entire calculation cell reran successfully. No ambiguous write or missing output is being presented as a successful check.

| Reconciliation | Result | Interpretation |
|---|---:|---|
| Antofagasta after-interest/tax CFO less cash PP&E | -$78.7m | Own residual, not official FCF |
| Freeport CFO less capex | $1,466m | Consolidated cash perimeter |
| Freeport same residual less identified insurance receipt | $767m | One-factor sensitivity, not complete normalization |
| Aurubis IFRS EBT less operating adjustments | EUR374m | Company operating-measure reconciliation |
| Hydro prior-year segments plus Other/eliminations | NOK7,790m | Group bridge; current-year rounded residual retained |
| Nucor actual adjusted EPS less June management midpoint | $0.29/share | Management-guidance comparison, not consensus surprise |

### Proposed semantic acceptance cases

The implementation proof set should enforce at least the following. These are requirements, not executed application tests.

| Case | Required behavior |
|---|---|
| BM-R2-01 | Preserve before-credit and net unit costs separately; do not infer physical efficiency from net cost alone. |
| BM-R2-02 | Distinguish cash from operations before tax/interest from net operating cash. |
| BM-R2-03 | Do not subtract working capital or tax again from a starting measure that includes it. |
| BM-R2-04 | Show a one-receipt cash sensitivity as a scenario, not normalized FCF. |
| BM-R2-05 | Preserve signed unit credits and the complete known exclusion set. |
| BM-R2-06 | Retain consolidated, attributable and parent-distribution boundaries. |
| BM-R2-07 | Keep provisional-pricing volumes, settlement windows and hedges source-bound. |
| BM-R2-08 | Reconcile IFRS versus operating measures without declaring either universally superior. |
| BM-R2-09 | Preserve an issuer FCF definition including dividends rather than compare it silently to pre-dividend FCF. |
| BM-R2-10 | Keep displayed rounding/source residuals visible; never change an input solely to balance a table. |
| BM-R2-11 | Include intra-group eliminations before deriving group exposure or earnings. |
| BM-R2-12 | Do not add embedded recycling profits as an extra independent segment. |
| BM-R2-13 | Preserve the issuer's adjusted-item definition; unusual cash items may remain inside adjusted profit. |
| BM-R2-14 | Distinguish new guidance, prior guidance and actual results; prevent duplicate surprise events. |
| BM-R2-15 | Refuse a spread using unresolved mass/input-output denominators or yield. |
| BM-R2-16 | Separate internal shipments from external sales. |
| BM-R2-17 | Distinguish refined apparent usage, direct-melt scrap use and final demand. |
| BM-R2-18 | Keep warehouse stock categories, reporting lags and rights separate; no double counting. |
| BM-R2-19 | A current forecast without its source body cannot become an admitted balance claim. |
| BM-R2-20 | A real accepted source must traverse the existing user journey with correct clocks, source scope and limitations while incumbent ranking/entry outputs remain unchanged. |

### Predictive and workflow evaluation

The first evaluation question is whether role-aware models explain subsequent company results better than a simple commodity-direction baseline. Test earnings/cash outcomes separately from share returns. Use the historical information set, native source revisions, eligible company universe and contemporaneous membership. Retrospective explanatory fit is insufficient for predictive qualification.

For early discovery, compare the proposed economic-change context with sector momentum, commodity momentum and existing theme/technical baselines. Measure incremental discovery lead time, false-positive burden, missing-data abstention, breadth of coverage and any concentration in one cycle or commodity. Use time-separated evaluation and later prospective shadow operation before admission to decisions.

Measure workflow quality independently: can a user explain the business exposure, identify why a headline differs from cash, inspect the source, and state the next evidence that matters? Browser proof establishes that the journey works; it does not establish investment edge. Conversely, a statistically promising model is not a finished product if its actual user path is incoherent or inaccessible.

## 9. Coverage and remaining work

R2 is a substantial operating-model test, not a global metals census. Independent blast-furnace steel economics, additional pure-play aluminium businesses, complete copper asset ownership, global cost curves, current source-licensed balances, project/financing valuation and historical security membership remain incomplete. The unresolved cases above stay explicit rather than being filled with guessed values.

The next bounded research unit is **R3: precious metals, royalty/streaming claims and development-stage financing**. It should test gold/silver/PGM demand differences, co-production, operator versus royalty/stream cash rights, reserve/resource/production distinctions and dilution-sensitive asset-to-equity valuation. It must use original issuer and industry evidence, not repeat the R1 architecture or R2 operating-case crawl.

After the remaining sector-specific units, consolidate data coverage, company-exposure records, cohort/basket methodology, valuation/evaluation choices, UI requirements and exact implementation dependencies into the final Fable CEO packet. Fable should receive researched decisions, source-bound examples, acceptance evidence and explicit unresolved assumptions—not a request to rediscover Basic Materials from scratch.

## 10. Primary-source register and access limits

**M01 — Antofagasta, Q2 2026 Production Report.** H1/quarter operating cost and production definitions. Public issuer HTML. Locator: H1 costs before by-products, by-product credits and net costs. Accessed in this R2 turn. Exact publication timestamp was not retained here.
https://www.antofagasta.co.uk/investors/news/2026/q2-2026-production-report/

**M02 — Antofagasta, 2026 Half Year Results.** Release associated with August 13, 2026. Physical PDF pages 21 and 29 visually inspected for cash/net-debt and the primary cash statement. Later APM-page extraction not admitted where images failed.
https://prod.antofagasta.co.uk/media/4972/20260813_antofagasta-hy26-aug26-vf.pdf

**M03 — Freeport-McMoRan, Form 10-Q for June 30, 2026.** SEC accession 0000831259-26-000036. HTML cash-flow, ownership, provisional-pricing and unit-cost sections inspected. Period is known; exact filing acceptance timestamp is not reproduced here.
https://www.sec.gov/Archives/edgar/data/831259/000083125926000036/fcx-20260630.htm

**M04 — Aurubis, Quarterly Report Nine Months 2025/26.** Nine months ending June 30, 2026. Physical pages 5, 22 and 24 visually inspected. Do not derive a publication timestamp from the filename alone.
https://www.aurubis.com/en/dam/jcr:28af3925-b00a-4899-86b5-c34dd376fb17/Aurubis_Quarterly%20Report_Q3_2025_26.2026-08-06-05-59-59.pdf

**M05 — Hydro, second-quarter 2026 results release, July 22, 2026.** Business-specific management explanations. The HTML's wording for one adjusted-net-income period is superseded for this analysis by the report's period-labelled table; no ambiguous HTML period is used in a calculation.
https://www.hydro.com/en/global/media/news/2026/hydros-second-quarter-2026-operational-strength-delivering-solid-results/

**M06 — Hydro, Second Quarter Report 2026.** Obtained from the official release attachment. Physical pages 5 and 17 visually inspected for segment/group reconciliation and Other/eliminations. Actual source line is -13; do not invent -14 to eliminate the rounding residual.
https://www.hydro.com/globalassets/06-investors/reports-and-presentations/quarterly-reports/2026/q2k9pev/second-quarter-report-2026.pdf

**M07 — Nucor, Q2 2026 results release, July 27, 2026.** Period is 13 weeks ending July 4, not calendar June 30. HTML operational tables, adjusted-item definition and cash flow inspected.
https://investors.nucor.com/news/news-details/2026/Nucor-Reports-Results-for-the-Second-Quarter-of-2026/default.aspx

**M08 — Nucor, Q2 earnings guidance, June 17, 2026.** Prior management forecast and prior disclosure of the two identified items. Not analyst consensus.
https://investors.nucor.com/news/news-details/2026/Nucor-Announces-Guidance-for-the-Second-Quarter-of-2026-Earnings/default.aspx

**M09 — Nucor, Form 10-Q for July 4, 2026.** SEC accession 0001193125-26-345891. Original SEC HTML inspected after following an indexed mirror's original-source link. Gross-margin, input-cost, start-up and internal/external sales discussion; no mirror-generated analysis adopted.
https://www.sec.gov/Archives/edgar/data/73309/000119312526345891/nue-20260704.htm

**M10 — ICSG, The World Copper Factbook 2025.** Definitions and physical flow coverage; selected definition/usage pages visually inspected. The Factbook is a structural reference, not a September 2026 market observation. No entire table or document is redistributed.
https://icsg.org/copper-factbook/

**M11 — LME, Off-warrant stock reporting.** Dedicated reporting-cadence and availability description. Source-native availability and licensing requirements must be confirmed by the existing data owner before production use.
https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports/Off-warrant-stock-reporting

**M12 — LME, daily off-warrant insight announcement, March 17, 2025; and warehouse-report overview.** Provides category and release-history context. Older overview cadence wording is not substituted for the dedicated reporting page. These are one source family for related claims, not independent corroboration.
https://www.lme.com/News/Press-releases/2025/LME-provides-daily-insight-into-off-warrant-stocks
https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports

**M13 — ICSG, Online Statistical Database description.** Describes subscription access to monthly/annual country statistics since 1995, including stage-specific production, trade, prices and stocks. This is a potential source-coverage path, not evidence that Mastermind already holds rights or a working adapter.
https://icsg.org/whats-icsg-online-statistical-database/

**M14 — ICSG, April 23, 2026 forecast download landing.** Landing page recovered; source-body retrieval failed. July site-update metadata is not a replacement forecast date. No forecast numbers admitted from this landing.
https://icsg.org/download/2026-04-23-press-release-icsg-copper-market-forecast-2026-2027/

## 11. Closeout boundary

R2 changes research and design understanding only. No product source, live evidence, graph membership, price basket, scoring, recommendation, publisher or runtime configuration changed. No subagent, Executive Attempt, Fable receiver, watcher or autonomous continuation was created. Research files and this annex remain on #7796 under its research-only Draft/HOLD.

The cumulative Agent OS checkpoint must identify the exact committed annex and verification evidence, preserve the three held semantic cases and the uncompleted R3 action, and be read back at its immutable revision. The final masterplan is not complete and no Fable handoff is claimed.
