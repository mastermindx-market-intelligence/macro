# Industrials Wave 3 - Replacement, fleet, distribution and network economics

23 September 2026. Principal research and proposed product requirements, not a final Fable handoff.

Operation: `gmi-industrials-sector-research-20260923-sol-001`. Carrier: Macro Draft/HOLD PR #7789, `sol/industrials-sector-research-20260923`. Protected procedure: Mastermind `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, Skillpack 1.0.1/bootstrap 1. Original Macro interface: `c4da107fe729e46b4d4036b3e0e290390315d0fd`. Capability: SPEC_ONLY. MISSION_COMPLETE: false.

Evidence identifiers refer to `INDUSTRIALS_WAVE3_EVIDENCE_2026-09-23.md` for W3-S01 through W3-S27 and `INDUSTRIALS_WAVE3_ASSET_MARKET_EVIDENCE_2026-09-23.md` for W3-S28 through W3-S31. They are bibliography identifiers, not a new production evidence authority. Issuer facts, management explanations, research hypotheses and illustrative calculations remain separate. Research calculations use the accompanying `calculate_wave3.py`; no current share price, security selection, consensus gap, fair value or trade is produced.

## 1. What this wave changes

The decisive object for these businesses is often the customer's productive asset, not the component bill. An agricultural machine, rental fleet, distribution relationship and freight network earn money differently even when they participate in the same construction or manufacturing theme. This wave connects customer affordability and physical activity to channel inventories, supplier profit, capital consumption and possible changes in valuation.

The proposed intelligence should answer five questions in order. Is the customer's need growing, or merely aging? Can the customer afford the economically preferred decision? Does the resulting expenditure become a supplier order, a rental contract, a repair or a used-equipment purchase? Does the supplier capture incremental cash after supporting the business? What new evidence would change a dated earnings expectation or a defensible valuation scenario?

The main conclusion is not that cyclical indicators are useless. It is that superficially similar improvements can occur at different points in the mechanism. Finishing dealer destocking can lift factory shipments without a recovery in retail demand. Expanding a fleet can lift revenue without raising its lifetime return. Higher freight charges can raise revenue while physical shipments fall. A stronger operating business can deliver weaker per-share earnings after acquisition financing. These explanations require different thesis tests and should not collapse into one positive theme score.

Wave 2's four measurements remain controlling: commercial commitment, physical progress, accounting recognition and cash collection are distinct. Here we add the customer decision and the remaining economic life of assets. Neither addition creates a new state machine, forecast originator or trading owner.

## 2. Replacement is an economic choice, not a calendar event

### 2.1 Define the paying cohort before using aggregate demand

A proposed replacement model starts with the actual customer. Large crop producers, dairy farms, livestock operations, small property owners, contract miners and general contractors have different revenue, cost and financing exposures. A sector-average income statistic cannot stand in for the marginal customer's willingness to buy a particular machine. USDA's separate sector and farm-business forecasts demonstrate the population and definition issue; both remain forecasts. [W3-S09, W3-S10]

For every customer cohort, the proposed research record should describe its output price, output volume, operating inputs, labor constraints, balance-sheet liquidity, financing terms and existing equipment. Then distinguish capacity expansion from replacement, efficiency upgrades, compliance-driven changes and repair. A customer can postpone a new machine while buying parts or retrofitting an existing one. Whether that benefits an original manufacturer, a dealer or an independent service provider requires separate evidence.

This creates more useful subthemes than a single agricultural or construction-equipment basket. Large agricultural tractors and combines can have a different purchase threshold from hay equipment or compact machines. Mining support needs the relevant mine plan, ore characteristics, haul distance, utilization and cost per unit of output, not merely a metal-price chart. Those variables are proposed research requirements, not data that this wave has already recovered for every customer.

Age is an input, not a purchase order. Record both calendar age and operating hours, maintenance condition, application severity, parts availability, technological obsolescence and residual value. A mean fleet age can rise because replacement is delayed, because the product mix changes, or because old but economically useful assets remain. A weighted average is not a cohort survival curve. We have not yet estimated an empirical age-to-replacement hazard function.

### 2.2 Compare keeping, repairing, replacing and renting

For a common workload and horizon H, a transparent ownership comparison discounts the relevant cash and opportunity costs. Let A be the discounted annuity factor at required return r:

`A(r,H) = sum((1+r)^(-t), t=1..H)`

`PV_keep = current sale value of old asset + immediate repair + PV(old running costs) - PV(old terminal value)`

`PV_replace = installed new purchase cost + PV(new running costs) - PV(new terminal value)`

`Equivalent annual cost = PV_cost / A(r,H)`

Including the owned asset's current sale value treats continued ownership as foregoing a sale. Do not then subtract the same trade-in proceeds a second time from the replacement-versus-keep difference. Financing affordability is a separate constraint: a positive economic return does not guarantee that the customer can fund the down payment or meet debt-service requirements. Conversely, adding interest to an unlevered discounted-cash-flow calculation can double count financing unless the model is consistently reformulated.

Illustration only, arbitrary units: five years, 8% required return, old asset sale value 80, immediate repair 10, annual old costs 30 and old terminal value 30. The replacement costs 200, incurs annual costs 12 and ends worth 90. At the assumed identical workload, equivalent annual cost is 47.43 for keeping and 46.75 for replacing. The replacement advantage is small.

Hold every other input fixed and reduce only today's trade-in value from 80 to 60. Keeping now costs 42.42 annually, while replacing still costs 46.75; the cash gap to purchase rises from 120 to 140. This is a partial sensitivity, not a forecast that terminal values remain unchanged after a market-wide shock. It demonstrates why an aging fleet and lower used prices do not mechanically imply stronger new-equipment demand.

A full rental comparison must put the quote, expected billable days, transport, insurance, consumables, downtime and any common operating costs on the same workload basis. Reducing rental days while holding the owner's variable operating costs unchanged is not a fair comparison. The value of flexibility or avoiding an uncertain resale can matter, but should be expressed as a scenario rather than invented precision.

### 2.3 Connect the customer decision to supplier economics

The same used-price change can affect several parties. A buyer may find used equipment cheaper, an owner may receive less for a trade, a rental company may realize less on disposal, and a dealer or lender may face a different collateral position. These are conditional mechanism links, not independent positive or negative signals to be summed.

A strong dossier traces both cash and risk. It identifies who owns the inventory, who funds it, who guarantees residual value, what support the manufacturer supplies, and when the end user accepts the asset. A manufacturer's wholesale sale is not automatically the final customer's purchase. A financing promotion can help volumes while changing realized economics. The purpose is to understand profitable adoption rather than count announcements.

### 2.4 Observe market clearing, not just inventory or a price average

The new public asset-market sources make the model more concrete. Sandhills reports shrinking aerial-lift inventory alongside lower estimated auction values. Tractor Zoom reports opposite auction-average directions for two horsepower bands; those averages are not constant-quality prices. These are different populations and measurement methods, not a single fungible used-equipment index. [W3-S28, W3-S29]

A proposed clearing view asks what sold, how long it took, at what discount and in which cohort. Inventory can shrink because purchases slow; a higher transaction average can reflect a change in what sells. Price and speed need matched equipment and comparable exposures. A sale count within a listing-age threshold is not a conversion probability without the eligible listing denominator. Research must distinguish reported facts from estimates about the unobserved remainder of the market.

Customer funding can independently delay an economically attractive purchase. The Chicago Fed's repayment diffusion measure improved sequentially while still indicating deterioration relative to a year earlier; its survey population also changed in 2026. The multi-district synthesis describes slower deterioration alongside tightening collateral. These are lender observations, not default probabilities or actual equipment orders. [W3-S30, W3-S31]

The proposed thesis test is consequently multi-part: is the relevant used cohort clearing without increasingly adverse concessions; are customer cash generation and financing sufficient; and does that translate into paid new or replacement demand at profitable terms? A failure in one part can redirect demand to repair, renting or smaller used assets. The system should explain that substitution rather than call every delay a collapse in the whole theme.

This is a useful source-feasibility advance, not a recovered full transaction panel. The public reports support differentiated research questions. Machine-level matching, historical outlier rules, publication vintages, lender populations and data rights remain required before forecasting or automated ingestion.

## 3. The channel creates a distinct earnings cycle

### 3.1 Stock-flow arithmetic explains a recovery without end-market growth

For compatible units and scope:

`Ending dealer inventory = Opening inventory + manufacturer sell-in - dealer sell-through + documented other movements`.

The illustrative model assumes no other movements and six-month periods. Retail demand stays at 600 units each period. Inventory begins at 900. Manufacturer shipments of 400 reduce it to 700; shipments of 500 in the next period reduce it to 600; shipments of 600 thereafter hold it at 600. Shipments grow 25%, then 20%, despite flat customer purchases.

With a constant unit price of 10, variable cost of 7 and fixed half-year costs of 700, modeled operating profit rises from 500 to 800 to 1,100. This is not a company forecast. It isolates the earnings effect of ending underproduction and absorbing fixed costs. It explains why a plausible early recovery thesis need not require a boom in customer demand.

The downside is equally important. From opening inventory of 600, suppose six-month retail demand falls to 480 and dealers target six months at the new 80-unit monthly pace. Target inventory becomes 480, so shipments need fall to 360. Relative to the flat-retail normalization case, a 20% retail decline is associated with 40% fewer manufacturer shipments and modeled operating profit of 380 rather than 1,100. The inventory target amplifies the shock; the amplification is conditional on the assumed behavior, not a universal industry multiplier.

AGCO's disclosures make this mechanism worth investigating: inventory reductions coexist with planned production restraint. Its North American financial comparison also changes with Mexico's reclassification. The observed data motivate the model; they do not establish that the exact illustrative sequence will occur. [W3-S03, W3-S04]

### 3.2 Months of supply has two moving inputs

`Months of supply = compatible inventory units / compatible monthly sell-through rate`.

A hypothetical decline in inventory from 900 to 810 units can coincide with months of supply rising from 9 to 10.125 when monthly sales decline from 100 to 80. An analyst who sees only the numerator may overstate normalization; one who sees only the ratio may miss real inventory liquidation.

The source must state whether the sales denominator is trailing, seasonally adjusted, forecast or otherwise normalized. Product mix and geography must agree. AGCO's financial recast is explicit, but an identical recast of the dealer-unit series was not established here. Do not present a simple nine-to-seven-month comparison as a precisely harmonized inventory improvement without that qualification.

### 3.3 Separate restocking, retail acceleration and margin-floor improvement

These are three hypotheses, not stages that every company must pass. Restocking concerns desired channel inventory. Retail acceleration concerns customer activity and purchases. A higher margin floor concerns retained economics when production weakens. A company can display one without the others.

Deere's reported Production & Precision Agriculture comparison provides an adverse baseline: across the selected 2024 and 2026 quarters, sales fell 21.59% and reported operating profit fell 54.65%. That arithmetic is not a complete constant-scope or special-item-adjusted cycle study. CNH's higher construction sales accompanied lower adjusted EBIT, including catch-up shipments. The observations prevent us from equating more delivered machines with an improved earnings floor. [W3-S01, W3-S02, W3-S05]

The discriminating next evidence is business-specific: retail orders, dealer stocks, used-inventory age, discounting, production schedules, price realization, labor absorption and cash. A PMI recovery alone does not resolve that sequence. A mid-cycle margin target is an attributed management ambition until tested against actual weaker periods.

## 4. Rental is a portfolio of assets with finite lives

### 4.1 Decompose growth without relabeling the parts

A simplified operating model uses available fleet units, eligible days, time utilization and realized rates, then adds separately priced ancillary and re-rental services. Real reported systems often use original equipment cost rather than units and include category mix. Their definitions must be preserved rather than forced into this simplified formula.

United Rentals explicitly defines fleet productivity as a composite. Its growth bridge therefore does not establish a standalone rental-rate increase. Sunbelt's reported dollar utilization is influenced by ancillary revenue and uses a trailing window. Herc excludes specified ancillary categories. An investor-facing table should not rank those metrics as if they measured the same utilization. [W3-S11, W3-S13, W3-S15]

There is also a source conflict: Sunbelt's FY2026 segment footnotes describe ending OEC, while its definition paragraph describes average OEC. The current document uses average OEC, but that alone does not prove a formal change from an accepted prior method. Preserve the discrepancy and hold the affected comparison. [W3-S14]

Fleet age needs the same discipline. Original-cost-weighted age is not the mean age of physical units. Purchase inflation, category mix, acquisitions and refurbishment can affect cost-based measures. A younger fleet may have higher near-term availability but more capital tied up; an older fleet may be economical or may carry increasing maintenance and failure risk. Neither conclusion follows from average age alone.

### 4.2 Count the full asset cycle

For an illustrative tax-free, unlevered asset with purchase cost C, annual operating cash K after recurring maintenance, disposal proceeds S at year H and discount rate r:

`NPV = -C + K*A(r,H) + S/(1+r)^H`.

This is an asset-level sensitivity, not an issuer valuation. Common overhead, working capital, taxes, financing and interactions between assets would have to be added for the business model. Accounting depreciation is not subtracted again when the purchase and disposal cash flows already represent the investment.

With C=100, K=20, S=40, H=5 and r=9%, NPV is 3.79. Keep the annual cash unchanged and raise the acquisition cost to 110: NPV becomes -6.21. Instead keep cost at 100 but lower disposal proceeds to 25: NPV becomes -5.96. Lower annual cash to 16 at the original purchase/resale values: NPV becomes -11.77.

The baseline capital-recovery annuity is 19.03, leaving only 0.97 of annual economic surplus over the specified hurdle. A profitable-looking operating asset can therefore have a thin return cushion after its capital cost. The lower-use case changes net operating cash, not a purported exact percentage change in physical utilization; its variable/fixed cost split is deliberately unspecified.

Rental revenue and operating earnings should be studied alongside purchase cohorts, holding periods, maintenance, downtime, damage and resale. Extending useful life can create value when incremental maintenance and lost availability are modest. It can destroy value when costs or service failures rise. A lower capex quarter does not decide which occurred.

### 4.3 Reconcile cash investment, accounting investment and disposals

United Rentals' H1 cash reconciliation in the companion calculations retains rental purchases, other purchases, rental disposals, other disposals and insurance receipts. Its gross rental capex differs from cash purchases by 211. The difference is not itself an accounting defect, nor do we attribute all of it to a single payable without a supporting bridge. [W3-S11]

Used-equipment sale margins compare proceeds with carrying values, while original-cost recovery uses a different denominator. A large book gain does not prove a strong lifetime return. A model that uses sale proceeds in terminal cash and adds the same gain again double counts the exit. Historical depreciation assumptions can alter reported gains without changing the cash buyer pays. Historical URI disposal evidence supplies a reason to model resale rather than assume it is constant. [W3-S12]

Fleet reduction can release cash while reducing future rental capacity. A valid sustainable-free-cash estimate must choose and justify a maintained service capacity and replacement policy. Labeling all current capex as growth, all depreciation as maintenance, or all disposals as surplus financing would each impose an unproven assumption.

### 4.4 Acquisition scale is not per-share value creation

Herc's EBITDA and adjusted-EPS directions diverge in the selected quarter. The relevant question is not which measure is correct; each measures a different layer of the capital structure. Acquisition debt, share issuance, incremental depreciation, integration costs and acquired earnings need a consistent bridge. Pro-forma leverage uses a different historical perimeter from a simple reported revenue comparison. [W3-S15]

For a proposed consolidation rerating, investigate branch overlap, customer retention, fleet redeployment, repair capacity, transport density, realized procurement savings and actual return after the acquisition price. Announced synergies are not realized cash. Temporary integration costs can be real and temporary, but removing them from one earnings measure does not erase their financing needs or execution risk.

## 5. Distribution economics are more than the product gross margin

The proposed distributor model separates customer activity, share of customer wallet, realized selling price, product availability, rebates, service cost and working-capital funding. Direct production material and indirect maintenance supplies can respond to different parts of the cycle. Digital ordering and inventory-management tools may strengthen a relationship, but evidence of usage does not itself establish a separately priced software business.

Fastenal's reported gross-margin pressure and operating-expense leverage motivate a cost-to-serve model rather than an automatic quality downgrade from gross margin alone. The source attributes different economics to large customers; the research still needs mature cohort evidence, retention, service effort and incremental capital before calling that a permanently superior relationship. Its broad manufacturing sales share cannot be relabeled a narrow industrial theme's exposure. [W3-S16, W3-S27]

A useful unit of analysis is contribution after the cost of fulfilling, delivering, financing and servicing the account. A customer can bring lower percentage gross margin but more absolute profit and lower selling effort per dollar. Another can absorb special inventory, extended receivables and bespoke service that erase apparent scale benefits. The same total sales growth can represent those very different outcomes.

Grainger's selected free-cash improvement splits almost equally between operating cash growth and lower capex. That bridge does not establish whether the reduced spending is permanent or desirable. Wesco's quarter and first-half operating-cash directions differ; receivables, supplier prepayments, deferred revenue and payables connect the customer project to distributor funding. Analyze the full operating cycle instead of treating deposits as free profit or all working-capital use as distress. [W3-S17, W3-S18, W3-S19]

The proposed rerating hypothesis is that a distributor becomes more valuable when it demonstrably captures durable customer spend at attractive incremental capital returns, or provides a harder-to-replace service. It fails if growth is primarily inflation, acquired volume, low-return inventory expansion or a transient supplier rebate. Test realized economics after price/cost lags and account maturation. Do not infer actual market mispricing without dated expectations and market evidence.

## 6. Freight networks and brokers require different models

### 6.1 Physical freight is not the invoice total

For compatible scope, freight revenue can be decomposed into shipments, weight/distance or another service quantity, underlying yield, mix and fuel-related charges. Those components are not always separately observable. Yield per hundredweight still reflects service and shipment mix; excluding fuel does not make it a pure like-for-like price index.

Old Dominion's latest evidence contains different period windows. August operating volume and quarter-to-date yield are not an accounting identity. Even the rounded August shipment and weight changes do not exactly reproduce the reported tonnage change: their product implies -0.7408% versus the reported -0.9%, a -0.1592 percentage-point residual. The explanation is not established here. Preserve it rather than manufacturing a corrected observation or automatically assigning it to rounding. [W3-S21]

A newer monthly release should update the relevant current observations while leaving the completed quarter intact. It must not silently replace a quarter's financial denominator, a forecast vintage or a source's historical definition.

### 6.2 Operating ratio can change with no change in operating profit

The hypothetical pass-through example begins with revenue 100, operating costs 80 and profit 20: operating ratio is 80%. Add 20 of reimbursed fuel revenue and 20 of fuel cost. Profit remains 20, but operating ratio becomes 83.33%. This does not prove that fuel explains any issuer's full ratio change; it shows why a ratio needs its numerator and denominator.

Old Dominion's quarter also includes asset-sale gains. A network-efficiency thesis should isolate such effects before attributing all margin improvement to density or service quality. J.B. Hunt's distinct businesses should not be collapsed into a single trucking model merely because they transport related freight. [W3-S20, W3-S22]

For asset networks, proposed measures include loaded capacity, empty miles, terminal density, shipment mix, service reliability, wage and purchased-transport costs, maintenance and expansion capital. Idle capacity can provide operating leverage in recovery, but it still costs money while demand is weak. Cutting service capacity can improve a near-term expense ratio while reducing the ability to win business later; that requires longitudinal evidence, not assumption.

### 6.3 Broker gross profit is an economic spread

A freight broker's billed revenue includes amounts paid to transportation providers. The useful model separates transactions, gross profit per transaction, service effort, credit and operating overhead. When carrier purchase rates and shipper contract rates reset at different times, gross revenue growth alone does not determine spread economics.

C.H. Robinson's selected operating-income figure yields 5.18% against gross revenue and 34.66% against adjusted gross profit. Those two ratios describe the same company and period but answer different questions. The issuer's adjusted margin must not be compared unqualified to a carrier's revenue-denominator margin. [W3-S23]

For a productivity or AI thesis, require paid activity handled per comparable employee, quality, retention, exception resolution and durable operating costs, including the technology expenditure. Lower headcount and higher aggregate earnings do not isolate the causal contribution of AI. A differentiated service can create value without recurring software revenue; the product should explain that mechanism accurately rather than assign a fashionable category.

## 7. An operating indicator can be useful and still fail a backtest

Komatsu supplies a promising first-party connection between machinery and actual use. Komtrax reports sample-average hours for a defined contactable population, including zero-hour machines and excluding specific equipment types. Its construction sample is not the mining-equipment order universe. [W3-S24, W3-S25, W3-S26]

The Japan population changed with connectivity retirement, and prior comparisons were revised. This creates two legitimate analyses: a latest-vintage comparable-sample view, and an as-known-at-the-time historical test. They must not be silently combined. An apparent historical signal can change because the denominator or retained population changed, not because customer behavior changed.

The proposed feature therefore stores metric period, source publication, first observed time, population definition, revision, geographic basis and known exclusions. If the publication timestamp is unknown, the observation can support current descriptive research with a limitation; it cannot be placed at an invented exact historical decision time. A remote-monitoring sample may also reflect availability, weather, working days and machine mix. Average hours multiplied by an undisclosed installed base is not total fleet work.

The mining order/sales charts are a separate input. Their six-month monetary windows smooth and lag current conditions, and the plotted product sets differ. We did not digitize unreported endpoints. A chart direction can motivate a question; precise historical modeling requires actual values and vintage records from a lawful source.

## 8. What would actually support a valuation rerating?

The operating models above become investment research only when connected to expectations and price. This wave has not recovered a matched point-in-time consensus/price panel and makes no current cheap/expensive judgment. The following are proposed mechanisms with explicit tests, not recommendations or fitted return signals.

| Mechanism | Economic change to establish | Evidence that would weaken it |
|---|---|---|
| End of underproduction | Wholesale shipments normalize without renewed channel excess | Retail deteriorates or dealers rebuild unwanted stock |
| Better customer replacement economics | Savings, workload and financing support paid replacements | Used alternatives, lower trade values or liquidity constrain adoption |
| Higher through-cycle margin floor | Comparable weak-period costs and mix preserve more profit | Favorable utilization, refunds or temporary price/cost explain the result |
| More service/retrofit profit | Paid installed-base activity improves contribution and retention | Catalog capability does not become adoption or profitable service |
| Better rental capital productivity | Rate/use/mix improve lifetime cash after replacement and disposal | Purchase inflation, maintenance or weaker residuals consume the benefit |
| Profitable consolidation | Realized integration benefits exceed incremental capital and financing | EBITDA rises while durable per-share cash and returns deteriorate |
| Stronger distribution relationship | Retained customer contribution grows after service and capital costs | Revenue requires discounts, bespoke inventory or extended credit |
| Freight operating leverage | Matched physical volume and density improve normalized profit | Fuel/mix, gains or temporary capacity cuts explain the ratio |
| Broker productivity | More gross profit after full operating cost and quality controls | Spread compression or service deterioration offsets throughput gains |

A cyclical earnings recovery can justify a higher earnings estimate without a higher multiple. A structural improvement can support a different duration or risk assumption, but a change in required return can offset it. A low multiple on peak earnings and a high multiple on trough earnings are both ambiguous without a normalized model. Normalized does not mean choosing a convenient historical peak; it requires a defended workload, margin, reinvestment and capital-structure scenario.

For machinery, build scenarios around retail, channel change, price/mix and plant costs, then finance and tax. For rental, use fleet purchase/age cohorts, operating contribution, replacement and exit values. For distribution, model account contribution and working capital. For networks, connect physical service and capacity to revenue, costs and investment. For brokers, model transaction spreads and cost-to-serve. A sum-of-parts must also retain corporate costs, captive-finance funding, minorities and consistent debt treatment.

The required investment evidence is dated guidance, dated external estimates where licensed, actual prices and corporate actions, and a clearly labeled house scenario. Revisions from volume, margin, share count, interest, tax, ownership and currency should be separated. No fundamental observation here self-originates a stock recommendation, trade size or execution decision.

## 9. Granular research slices and user workflow

These 24 proposed slices are research filters, not accepted live baskets or mutually exclusive issuer classifications.

| Slice | Primary mechanism | Company/business seed or evidence question |
|---|---|---|
| MR-01 Large crop equipment | Replacement affordability and channel stocks | Deere PPA; AGCO; CNH Agriculture |
| MR-02 Small agriculture and turf | Different customer/use cohorts | Deere Small Agriculture; further customer mapping required |
| MR-03 Construction and forestry machinery | Project activity, catch-up and fleet renewal | Deere C&F; CNH Construction; Caterpillar CI |
| MR-04 Mining production equipment | Mine plan and operating economics | Komatsu's separately identified mining product sets |
| MR-05 Used-equipment clearance | Trade value, stock age and funding | Sandhills/Tractor Zoom public cohorts; raw comparable histories still required |
| MR-06 Parts, repair and retrofit | Installed activity and paid service | Revenue/profit purity not presumed from offerings |
| MR-07 Captive equipment finance | Credit, residuals and funding | Cat Financial; industrial and finance scopes separate |
| MR-08 Dealer normalization | Sell-in versus sell-through | AGCO current and historical channel disclosures |
| RF-01 General rental fleets | Rate, time utilization and capital | URI general; Sunbelt General Tool; Herc |
| RF-02 Specialty power and climate | Contract duration and solution mix | Separate rental, ancillary and re-rent economics |
| RF-03 Fluid, trench and remediation | Application and service cost | Specialist capability/customer evidence needed |
| RF-04 Event and temporary infrastructure | Event timing and redeployment | Sunbelt attributed event contribution |
| RF-05 Fleet renewal and residuals | Holding period and maintenance | Purchase cohorts and disposal recovery |
| RF-06 Rental consolidation | Integration, financing and dilution | Herc/H&E perimeter and shareholder bridge |
| DS-01 Production consumables | Factory activity and customer share | Fastenal end-market and margin evidence |
| DS-02 Industrial MRO | Recurring operating needs and service | Grainger and Fastenal; not subscription by default |
| DS-03 Electrical/project distribution | Delivery coordination and financing | Wesco business-level cash cycle |
| DS-04 Digital/onsite supply services | Customer retention and cost-to-serve | Paid economics, not digital-label valuation |
| TR-01 LTL networks | Density, service mix and terminal capital | Old Dominion financial and monthly metrics |
| TR-02 Intermodal | Container turns and purchased transport | J.B. Hunt business-specific evidence |
| TR-03 Dedicated contracts | Contract economics and fleet use | J.B. Hunt DCS, not spot-market proxy |
| TR-04 Truckload/final-mile | Capacity, labor and service obligations | Separate operating units and delivery mix |
| TR-05 Freight brokerage | Gross profit per transaction and overhead | C.H. Robinson; J.B. Hunt ICS |
| TR-06 Global forwarding | Mode-specific spreads and volumes | C.H. Robinson Global Forwarding |

The proposed user journey is Theme Tracker to research slice, customer mechanism, business exposure, latest change, profit/capital implication, expectations/scenarios and falsifier, then back to the existing company workflow. Existing GMI, evidence, identity, forecast and publication owners remain authoritative. Research-source labels do not bind an issuer to a security automatically.

The most useful new views are a channel stock-flow bridge, a replace/repair/rent comparison, a fleet-lifetime cash view, a customer contribution/cash-cycle table and a physical-volume versus revenue panel. These can use the shared template without forcing a supply-chain graph into every subtheme. Every view should expose unavailable inputs and definition conflicts rather than imply complete current coverage.

## 10. Proposed acceptance cases - not executed application tests

| Case | Required behavior |
|---|---|
| W3-T01 | Separate wholesale shipments, retail purchases and dealer inventory. |
| W3-T02 | Keep inventory numerator, sales denominator and target assumptions explicit. |
| W3-T03 | Refuse negative or impossible illustrative channel balances. |
| W3-T04 | Do not promote inventory normalization to observed retail recovery. |
| W3-T05 | Keep current/recast business geography distinct from unrecast history. |
| W3-T06 | Separate the latest comparable vintage from the historical as-known vintage. |
| W3-T07 | Use the same workload and horizon for replacement alternatives. |
| W3-T08 | Do not count a trade-in opportunity value or financing cost twice. |
| W3-T09 | Keep fleet age weighting and machine population visible. |
| W3-T10 | A productivity composite cannot be relabeled pure rate or utilization. |
| W3-T11 | Conflicting KPI definitions remain unresolved, not silently repaired. |
| W3-T12 | Different ancillary and original-cost bases block naive peer ranking. |
| W3-T13 | Capital expenditure and cash payment differences require a bridge. |
| W3-T14 | Disposal cash, accounting gain and original-cost recovery stay separate. |
| W3-T15 | Asset-lifetime models do not subtract depreciation and purchase cash twice. |
| W3-T16 | Lower capex or fleet liquidation cannot automatically become sustainable FCF. |
| W3-T17 | Acquisition pro-forma figures cannot replace reported figures silently. |
| W3-T18 | Preserve the bridge from EBITDA through financing to per-share results. |
| W3-T19 | Operating cash and free cash use the same entity/period definitions. |
| W3-T20 | Organic/daily/constant-currency growth is not automatically volume growth. |
| W3-T21 | Distribution contribution includes service and capital requirements. |
| W3-T22 | Quarterly and year-to-date cash conclusions remain distinct. |
| W3-T23 | Freight revenue, fuel, weight, shipments and mix remain distinct. |
| W3-T24 | A monthly volume cannot be combined with quarter-to-date yield as an identity. |
| W3-T25 | Preserve unexplained source arithmetic residuals without false precision. |
| W3-T26 | Broker AGP-denominator margins cannot be ranked as revenue margins. |
| W3-T27 | Telematics exclusions, zero-use units, connectivity and sample revisions remain visible. |
| W3-T28 | Unknown publication times are not invented for historical testing. |
| W3-T29 | Management productivity/AI attribution remains separate from causal validation. |
| W3-T30 | Research filters, scenarios and coverage do not change trading authority. |
| W3-T31 | Asking prices, estimated values and transaction averages remain different observation types. |
| W3-T32 | Listing counts, aged shares and early-sale counts retain distinct denominators. |
| W3-T33 | Different machine cohorts and outlier rules do not become a constant-quality price index. |
| W3-T34 | Lender diffusion indexes retain population, direction and revision; they are not default rates. |

The local verifier tests selected arithmetic and deliberately incompatible research fixtures. It is not a production admission checker and does not prove the application satisfies these cases. Actual UI/schema integration, privacy, access, retention and browser proof remain later obligations under the existing owners.

## 11. Next research and completion boundary

The wave resolves a useful cross-business set of economic and measurement questions. It does not establish a complete global equipment universe, current mispricing, source-complete customer exposures or empirically validated return prediction. Selected matched quarters are not a full-cycle panel.

This wave has now recovered public used-equipment category comparisons and regional lender evidence, not merely proposed looking for them. Remaining depth work requires comparable underlying transaction/age cohorts, customer financing decisions and multi-period asset capital histories. Those obligations should remain in the cross-sector data-feasibility and validation program. The next principal domain unit is aerospace original equipment versus aftermarket economics: distinguish installed fleets, usage, service events, contract obligations, development/production investment, durability costs and cash conversion before inferring a longer earnings runway. Then extend the existing program into project and essential-service businesses. Do not rerun this 31-source Wave 3 sweep.

Before the final Fable package, the research still owes a dated expectations/valuation data route and discriminating historical validation, not just more narratives. Tests should compare the proposed mechanisms with simpler industry/activity and momentum baselines, retain failed cases, use original source vintages and separate descriptive explanation from prediction. Any downstream trade rules require their own accepted evaluation and authority.

Fable remains the eventual build orchestrator. No worker, Executive Attempt, watcher, new source owner, product deployment, live basket, rank, sizing, entry or execution change is created by this document. Continue on PR #7789; preserve Wave 1, canonical Wave 2 and W2X without replaying their source sweeps.
