# Mining research, Pass 07: aluminium, energy contracts and cash conversion

**Research cutoff:** 23 September 2026. **Status:** principal research / proposed product requirements / HOLD. **Mission complete:** false. **Final Fable implementation handoff:** not created.

Operation: `gmi-mining-principal-research-20260923-sol-001`. Carrier: Macro Draft/HOLD PR #7795, `sol/mining-principal-research-20260923`. Parent: `WS:GMI-THEME-GRAPH`; incumbent GMI identity/evidence and F04 composition remain controlling. Protected Mastermind procedure: `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1. Original Macro interface baseline: `c4da107fe729e46b4d4036b3e0e290390315d0fd`, not current-main integration proof.

## 1. The question and the result

This pass asks **which aluminium-chain business benefits from a change, which contract determines that benefit, and what prevents reported earnings from becoming distributable cash?** The answer requires more than a metal-price direction. It requires the relevant production stage, purchased versus internally supplied material, electricity terms, inventory and settlement timing, customer use, and the capital claims on the operation.

The proposed organizing principle is **net economic exposure across matched boundaries**. A company can receive more for primary metal while earning less on alumina or electricity. A converter can improve industrial margins while financing a larger metal inventory. A long power contract can secure future supply without fixing its price. Acquisition financing can close before the assets change hands. A restart can progress without a proportional increase in customer deliveries. These are distinct mechanisms, not synonyms for commodity beta.

The investor job remains: move from a theme into a specific asset, product, contractual right and issuer, understand what changed, and identify the strongest reason the implied economic improvement might not occur. The machine job is to retain enough identity, time, unit, scope and uncertainty to support that explanation. This report proposes behavior for the existing system; it does not create an electricity scheduler, commodity-price service, contract-settlement engine or autonomous valuation/trading authority.

The evidence is representative rather than exhaustive. There are twelve connected dossiers, nineteen primary-source records, six explicitly hypothetical examples and twenty-eight additional proposed requirements. Corporate statements are attributed evidence, not independent operating audits. The coverage assessment advances only the aluminium/energy regime; it does not declare world production, contracts, customer economics or investment returns fully researched.

## 2. Twelve discriminating dossiers

### AL-C01 — A vertically integrated issuer can contain opposite exposures

**Evidence.** Hydro's Q2 2026 adjusted EBITDA was NOK522 million in Bauxite & Alumina versus NOK1,521 million a year earlier, NOK6,421 million in Aluminium Metal versus NOK2,423 million, and NOK499 million in Energy versus NOK1,069 million. Its explanation includes weaker alumina realization, stronger metal realization, lower alumina costs for smelting, and lower energy production/price-area effects. [AL-S01]

Chalco's issuer-authored interim narrative similarly reports an alumina segment loss of about RMB818 million and primary-aluminium segment profit of RMB26,615 million, compared with prior profit of RMB4,706 million and RMB8,105 million respectively. This is a cross-company qualitative comparison, not comparable profit measures or currencies. The issuer index confirms the announcement; its direct PDF failed, so the admitted narrative was read in an issuer-document mirror. Table-derived reconciliations remain unverified visually. [AL-S18]

**Interpretation.** An integrated label does not establish a neutral exposure. The research must identify net external purchases and sales, economic interests, and the observation interval. Internal transfer prices can move segment earnings without creating equal new value for the consolidated group. Nor should segment results be added to a separately valued group without removing overlap.

**Proposed behavior.** Show which stage receives a price and which pays it. Display a descriptive exposure map before estimating sensitivities. Retain incompatible performance definitions instead of forcing a cross-issuer margin ranking. A movement that supports smelting may weaken a merchant refiner; the system should explain both without making a sector-wide investment recommendation.

### AL-C02 — Better future feed is not a current cost assumption

**Evidence.** Alcoa's February 17 statement expected new Huntly mining regions to commence no earlier than 2029 and bauxite quality to remain similar to recent grades until then. Its June-quarter release subsequently reported alumina-production pressure from Pinjarra instability and gas disruption, while some previously delayed shipments were completed. [AL-S19, AL-S07]

**Interpretation.** A future mine region, a plant's design throughput, and the quality currently processed are different inputs. Shipment recovery can coexist with production weakness when inventory or prior logistical delays are involved. The research must not import anticipated future ore quality into current unit-cost forecasts, or treat a shipment catch-up as proof of better refining efficiency.

A useful thesis could concern a future feed transition, near-term reliability repair, or improved delivered sales. Each needs a different falsifier and time horizon. The future-feed thesis fails to explain today's earnings unless the relevant quality change has actually reached the process. Reliability improvements require operating evidence. Delivery improvements require a production/inventory/shipment bridge.

**Proposed behavior.** Bind assumptions to the mine region, refinery, effective interval and product basis. A corporate approval announcement is not a measured grade change. Regulatory statements remain issuer-reported project context, not a legal opinion or independent finding about approval status.

### AL-C03 — Electricity contract duration is not electricity-price protection

**Evidence.** Century's June-quarter filing describes Sebree's market-linked MISO supply, Mt. Holly's cost-of-service supply through December 2031, and Grundartangi arrangements containing LME-variable and fixed components. It also identifies roughly 545 MW in aggregate contractual capacity; a capacity number is not an annual energy-delivery series. [AL-S04]

Hydro's Eviny contract provides 0.5 TWh annually in 2031–2040, totaling 5 TWh, delivered in Norwegian price area NO5. The announcement does not disclose the pricing formula or full hourly profile. [AL-S03]

**Interpretation.** Four questions must be separate: availability, delivered quantity, price formula and timing. A long agreement may reduce renewal risk while preserving market or metal-price exposure. A fixed reference price can still leave a location or delivery-profile mismatch. An available megawatt is not a delivered megawatt-hour, and a contract beginning in 2031 cannot be used to describe 2026 protection.

**Proposed behavior.** Record area, product, currency, settlement reference, index/fixed components, volume basis, tenor and supported delivery profile as scoped evidence. Unknown pricing stays unknown. Do not infer that an energy-intensive plant is fully hedged, or calculate a current margin, from a press release giving only a contract term and total energy.

### AL-C04 — Price protection, collateral and free cash flow are not the same thing

**Evidence.** Hydro's Q2 report explicitly attributes part of Energy's weaker result to price-area differences. Its free-cash-flow reconciliation starts with NOK9,031 million operating cash, removes NOK2,469 million of collateral changes and NOK22 million of trading-security effects, then includes investing cash and short-term-investment adjustments to reach NOK3,963 million. Printed pages 10, 34 and 36 were visually checked. The collateral balance movement is not the same measurement as the cash-flow adjustment. [AL-S02]

**Interpretation.** A hedge can improve long-run economics while consuming liquidity before its offsetting physical cash arrives. Conversely, returned collateral can increase current cash without an equal increase in recurring operating performance. A source can legitimately present an adjusted cash measure that removes such effects, but an investor still needs to understand actual liquidity available for debt, capital or distributions.

**Proposed behavior.** Preserve reported cash flow, adjusted cash flow and the bridge. Keep collateral asset balances, cash movements and derivative fair values distinct. The system must not subtract the same collateral twice or claim that excluding it from a performance measure makes the liquidity obligation irrelevant. A generic 'hedged' flag cannot answer this question.

### AL-C05 — Physical restart and contracted energy solve different problems

**Evidence.** Hydro's July 1 Slovalco announcement describes a first 75,000-tonne restart out of 175,000 tonnes of annual capacity, with EUR100 million of investment and remaining conditions; restarting the other 100,000 tonnes depends on additional arrangements. Alcoa separately reported San Ciprian's restart complete on April 7, 2026, after its July 2025 notice had resumed a restart interrupted by a national power outage. [AL-S05, AL-S06, AL-S07]

**Interpretation.** A commercial energy arrangement does not prove the physical plant is ready, and physical restoration does not establish an acceptable remaining investment return. The meaningful positive update is the specifically supported transition: an initial tranche enabled, a restart resumed, or a restart completed. None automatically establishes full-year output, all tranches, realized product premiums or profit.

**Proposed behavior.** Preserve the dated asset/tranche and distinguish conditional plan, physical restoration, stabilized operation, saleable product and cash generation. Full annual capacity is not production remaining in the calendar year. A later broad schedule should not erase an earlier condition unless the source actually resolves it. The cited project conditions are source descriptions; no political ranking, policy endorsement or legal conclusion is proposed.

### AL-C06 — A physical supply graph needs substitutable routes, not only serial arrows

**Evidence.** EGA's September 2025 debottlenecking project added a third mill and announced up to 50,000 additional annual tonnes of alumina capability. Its August 2026 sources instead describe a recovery regime: the smelter can continue recovering without the refinery at full capacity. On August 26, 315 of 1,262 cells were reported restarted; some hot metal was used for further restarts rather than customer product. [AL-S14, AL-S15, AL-S16]

**Interpretation.** The upstream refinery is not necessarily a hard serial cap when usable purchased alumina is available. A diagram that takes the minimum of each wholly owned stage would be wrong in that situation. The reverse error is treating procurement as unlimited: input specification, delivered price, logistics, credit and timing still constrain the alternative route.

The 315/1,262 calculation is 24.9604% of cells. It is not a forecast of the quarter's saleable output or revenue. Cells have different restart dates and stabilization needs, and internal use can delay sales. Technical restoration and revenue conversion need separate evidence.

**Proposed behavior.** Represent internal and qualified external input routes under the existing relationship owner, with conditions rather than invented unlimited capacity. Preserve the 2025 debottlenecking claim as historical capability; do not let it override a subsequent interruption or imply current incremental supply. Avoid carrying an older restoration percentage forward after a later update.

### AL-C07 — Better conversion earnings can require more financing

**Evidence.** Novelis's quarter ended June 30, 2026 reported adjusted EBITDA of US$516 million versus US$416 million, but operating cash of negative US$455 million versus positive US$105 million. The release attributes cash pressure partly to higher metal-price working capital and disruption effects. Its adjusted free cash flow is negative US$1,134 million after investing cash and an asset-sale adjustment. The release identifies Novelis as a Hindalco subsidiary. [AL-S08]

**Interpretation.** Higher pass-through metal value can increase the cash required to hold inventory and extend customer credit without proportionally improving the industrial conversion margin. This can happen even as scrap sourcing or operating efficiency improves. The right question is whether funding is a temporary timing need, a recurring requirement of a larger operation, or a loss mechanism.

**Proposed behavior.** Separate conversion contribution from metal turnover and financing. Reconcile the actual cash statement before annualizing a current cash outcome. Preserve operating unit versus tradable parent identity; a subsidiary's result is not a new listed security or the parent's complete earnings. Forecast deleveraging remains conditional on actual capital, working-capital and operating developments.

### AL-C08 — Matching the word 'adjusted' does not match performance measures

**Evidence.** Constellium's Q2 2026 adjusted EBITDA of US$439 million includes US$129 million of metal price lag, while its full-year US$980–1,020 million guidance excludes that effect. H1 adjusted EBITDA of US$798 million includes US$226 million of lag. Novelis's adjusted-EBITDA reconciliation removes its US$173 million metal price lag for the June quarter. [AL-S09, AL-S08]

**Interpretation.** Constellium's matched H1 measure is 798−226=572. The implied H2 amount needed to reach its guidance midpoint is therefore 1,000−572=428, not 202. This is an arithmetic implication of management guidance, not consensus, a probability of achievement, or a return forecast.

For Q2 year-on-year comparison, Constellium's prior headline 146 included negative lag of 19: the matched prior figure is 165. Excluding lag, growth is 310/165−1=87.8788%, versus headline growth of 200.6849%. Both describe different defined quantities; neither is an error. Other accounting and business differences remain, so removing lag alone does not establish fully comparable peer profitability.

**Proposed behavior.** Attach inclusion rules to every result, estimate and scenario. A headline can be displayed with a defined bridge, but must not be compared with a guidance measure that excludes something the headline includes. Keep an arithmetic guidance remainder separate from an analyst forecast or investment expectation gap.

### AL-C09 — Financing completion is not ownership completion, and NPV is not annual earnings

**Evidence.** Alcoa's June acquisition announcement proposes US$4.1 billion upfront consideration for selected South32 assets, plus a contingent right capped at US$750 million. The stated synergy estimate is approximately US$900 million **net present value**, not annual savings. Mozal is excluded. On September 23, Alcoa reported completion of US$2.6 billion of notes and termination of the remaining bridge commitments, while the acquisition remained conditional. [AL-S10, AL-S12]

Its September 9 pro forma update uses a financing assumption of two US$1.3 billion tranches at 7.00% and 6.75%. Actual issued tranches were US$1.5 billion at 6.625% and US$1.1 billion at 6.875%. The pro forma excludes anticipated synergies and integration costs, and identifies a locked-box economic mechanism distinct from the completion date. [AL-S11, AL-S12]

**Interpretation.** Actual nominal annual coupons total US$175 million, compared with US$178.75 million under those earlier assumed coupon inputs. The difference is not a complete change in GAAP interest expense, which can include other obligations, fees and timing. Nor can an analyst simply add US$900 million to each year's earnings. The synergy NPV lacks a disclosed annual cash series sufficient for that transformation.

**Proposed behavior.** Advance financing to completed without prematurely transferring the assets into current owned production. Retain the announced transaction perimeter, economic effective terms, pro forma basis and remaining conditions. Do not treat a locked-box description as unconditional ownership if the deal never closes. Preserve the difference between maximum contingent consideration, estimated fair value and cash actually paid. A funded, potentially accretive transaction is a research thesis requiring a consistent per-share and capital analysis, not automatic accepted accretion.

### AL-C10 — A low-carbon sales agreement does not reveal its economic premium

**Evidence.** Hydro and Nexans disclosed an agreement for approximately 85,000 tonnes of low-carbon aluminium wire rod across 2026–2030, linked to Hydro's Karmoy wire-rod expansion. The release identifies applications but does not disclose the contract price or retained premium. [AL-S13]

**Interpretation.** The agreement supports a specific product/customer demand relationship. Dividing by five gives a 17,000-tonne arithmetic annual average, not the actual delivery schedule. A low-carbon attribute, a product premium and the cost of producing and qualifying that product are different variables. The research cannot monetize the attribute without evidence about buyer value, realized commercial terms and incremental cost.

**Proposed behavior.** Recognize the positive commercial relationship without inventing backlog value or profit. Link it to the relevant grid/cable use and asset rather than marking all the issuer's output as equivalent. Cross-theme demand should reuse the same material flow: a tonne used in a grid serving several downstream themes is not several independent tonnes of demand.

### AL-C11 — Recycling stages and acquisitions must not multiply the same material

**Evidence.** EGA completed its 80% Eco Green acquisition on September 10, updating the pending status in its H1 release. Eco Green's announcement describes about 23,000 tonnes of scrap sorted at one location, some feeding another location that casts more than 20,000 tonnes; it separately reports distribution, furnace nameplate and an expansion expected in December. [AL-S17]

**Interpretation.** Sorting, distribution and casting measures cannot automatically be summed into independent recycled-metal supply. They can describe repeated steps through the same chain. Acquired business capacity is also not organic growth, and an 80% interest is not the same measure as 100% plant output. The new owner relationship should update from the effective event without rewriting earlier observations.

A recycler may benefit from scrap availability, purchase discounts, sorting yield, product quality or customer access. A reduction in sorting losses could raise useful output without increasing scrap intake. Conversely, a narrow scrap discount can reduce conversion economics even when the environmental case for recycling remains strong.

**Proposed behavior.** Preserve purchased, sorted, processed and externally sold quantities with their boundaries, and keep expansion distinct from current capability. Use actual feed suitability and yield for numerical routes. Do not substitute a recycled-content label for a measured mass balance or price margin.

### AL-C12 — An idle industrial site can have value outside the original metal business

**Evidence.** Century's filing reports the February 2 sale of its Hawesville site for US$200 million cash and a 6.8% minority interest in the buyer entity, which plans a data center. At June 30, US$44.8 million of proceeds remained restricted. [AL-S04]

**Interpretation.** Sale proceeds can change funding capacity without becoming recurring smelting revenue. A retained financial interest is not restored aluminium production, and restricted cash is not automatically available for another capital project. This is also a disciplined cross-theme connection: an asset's new use can link to data-center research without implying every idle smelter has the same alternative value.

**Proposed behavior.** Keep the old operation, disposal, retained interest and new proposed use distinct. A sum-of-parts valuation must not count both the sold operation and all sale consideration as continuing owned assets. Any future income from the retained interest requires its own evidence and economic-rights analysis.

## 3. Proposed economic model: match exposures before estimating value

### Physical supply and net commodity position

Represent the functional chain as bauxite supply, alumina conversion, primary metal, intermediate/final products, and secondary-material recovery. Do not force every issuer through every stage. An operation may buy qualified feed, sell intermediate material, recycle external scrap, or hold a financial interest rather than operate a plant.

For each stage, the proposed research questions are: what is the feasible input, who owns it, what processing or logistics resource is limiting, which product is saleable, and who pays or receives the relevant price? A headline benchmark need not be the actual transaction basis. Internal price changes redistribute reported segment results; net external receipts and costs determine the group's corresponding exposure.

A useful simplified bridge is `external product receipts − external feed/energy/conversion costs − required reinvestment`, with tax, working capital, financing and ownership then treated consistently. This is not permission to subtract all segment costs from all segment revenue: intra-group transfers, mixed products and differing accounting measures must first be understood. Commodity price sensitivity, physical production and revenue exposure are separate views and may have different denominators.

### Electricity as a set of contractual dimensions

The proposed power-economics view retains location, delivery period and supported profile; volume or capacity units; fixed, market, cost-of-service or metal-linked components; counterparty and settlement terms; physical availability; and collateral or liquidity implications. It must show what is disclosed and what is missing. This extends native evidence relationships, not an operational electricity-market model.

An owned generator is not necessarily a free source of power. Its output has costs, competing uses and a timing/location relationship to industrial consumption. Treating its market value as both power-segment revenue and a free input can create value twice. Conversely, mechanically charging an internal market transfer to the consolidated operation may hide the benefit of owned generation. The proper comparison depends on the stated valuation boundary and feasible alternative use.

A hedge can stabilize one component while leaving another open. If the physical purchase and hedge settle in different areas, the area difference remains. If annual volumes match but delivery profiles do not, an annual total cannot establish hourly protection. The research can identify these missing dimensions without pretending to calculate a plant's actual hedge effectiveness from public summary data.

### Conversion economics and liquidity

For a downstream product, isolate the retained industrial margin from passed-through metal value. Higher metal prices may increase invoice size and inventory funding while leaving conversion fees unchanged. Better collection terms, customer metal ownership or tolling can alter that effect, but they cannot be assumed without a supported contract.

The analytical sequence should connect sales basis, purchased metal, scrap spread, recovery, operating costs, working capital and capital expenditure. Each adjustment should have one place in the bridge. Metal price lag is not universally included or excluded from adjusted earnings. Insurance receipts and recognized compensation need their own timing; neither permanently substitutes for sustainable operation.

A cash-flow inflection can be valuable when construction spending ends or a working-capital build normalizes. It can also be temporary. The dossier should name which recurring operation will fund future reinvestment and obligations rather than simply extrapolating the latest cash quarter.

### Capital, ownership and expectations

An acquisition, restart or new product line is evaluated against its relevant counterfactual. Compare the same economic boundary before and after funding, dilution, obligations and implementation costs. Do not combine an enterprise cash-flow valuation with an equity discount rate or subtract debt twice. An NPV estimate requires its assumed horizon and discount basis; an annual savings target requires a realization schedule and cost to achieve.

Research should preserve management guidance, issuer-provided scenarios and market expectations as distinct evidence types. This pass supplies a guidance-compatibility calculation, not an independently retained market-consensus surprise. A useful economic mechanism does not establish that the security is mispriced or that excess returns follow.

## 4. Six controlled hypothetical examples

These examples use invented assumptions solely to test proposed reasoning. They do not estimate any named company's operating parameters, contract settlement, fair value or appropriate security weight.

### AL-H01 — Partial metal-linked power cost

Assume one tonne of product receives $3,000 and incurs $600 energy plus $1,400 other variable costs: contribution is $1,000. Assume product realization rises $300. With fully fixed energy, contribution rises to $1,300. With half of the original energy bill indexed proportionally to that 10% metal increase, energy rises $30 to $630 and contribution becomes $1,270. With the whole bill indexed, contribution is $1,240.

The example isolates retention of price gains. It is not a Century contract formula; actual fixed/indexed shares, index dates and other costs remain unknown. A 'metal linked' description is not enough to infer the coefficients.

### AL-H02 — A location-basis mismatch survives a hedge

Assume a 100,000-MWh purchase in area A, initially priced at $60/MWh. A same-volume financial hedge pays the increase in area B above $50/MWh. Initially B is $50. Subsequently A rises to $110 and B to $90. Physical cost is $11 million, hedge receipt is $4 million, and net cost is $7 million—up $1 million from the initial $6 million.

The hedge offsets its reference change but not the widened area difference. This ignores fees, timing and credit. No actual Hydro settlement or physical power arrangement is estimated. The $4 million hedge receipt is not also deducted from cost after the net $7 million has already been used.

### AL-H03 — A natural hedge depends on the net external position

Assume a group produces 100 units of intermediate material, consumes 80 internally and sells 20 externally. Its internal price rises $10/unit while final-product receipts and actual production costs stay constant. Upstream segment revenue rises $1,000; downstream internal cost rises $800; the net external gain is $200. If production is only 60 against internal needs of 80, it instead buys 20 externally and the same price increase creates a $200 cost headwind.

The arithmetic assumes uniform material, timing and fully aligned ownership. Those conditions are not established for any real group. Internal billing is not a second external profit source.

### AL-H04 — Better earnings with unchanged volume can still require cash

Assume a converter produces 100,000 tonnes per year and retains $200 contribution per tonne. Its metal-funded inventory is 30 days on a 365-day convention. A $500/tonne metal-price rise requires approximately $4.110 million of additional inventory funding, while annual contribution remains $20 million under these assumptions. At an assumed 8% funding cost, carrying that additional balance costs about $0.329 million per year.

This excludes receivables, payables, taxes, capital and price lags. It is not a complete cash-flow model, and the annual financing expense is not an additional immediate inventory purchase.

### AL-H05 — Recycled-product margin is not just the scrap discount

Assume saleable product realizes $2,600/tonne. Feed costs $1,500/tonne, saleable yield is 75%, and other conversion costs are $300 per output tonne. Feed cost per output tonne is $2,000; contribution is $300. At 80% yield it becomes $425. If feed price rises to $1,700 at the original 75% yield, contribution falls to $33.3333.

These are invented inputs. The comparison must keep input versus output tonnes straight and cannot presume that all scrap grades yield the same qualified product. Additional residue revenue, sorting cost or capital would require separate inputs and must not be silently omitted from a real investment case.

### AL-H06 — Buyer benefit and retained premium

Assume a qualified product delivers $120/tonne of usable benefit to a specific buyer. It costs the producer $90/tonne more to supply. A $100 premium leaves the buyer $20 and producer $10 before capital and other omitted items. If a changed buyer use reduces the usable benefit to $70, that price no longer leaves both parties better off; if producer cost remains $90 there is no mutually non-negative premium interval.

This does not monetize Hydro's carbon attributes or prescribe a customer purchase. It tests whether an attribute's commercial benefit is actually usable and whether its producer retains value after incremental cost.

## 5. Research views and persona workflows

### Proposed aluminium economic views

| View | Question to answer | Observation that could invalidate the interpretation |
|---|---|---|
| Merchant bauxite/feed transition | Can usable feed be delivered at a cost and quality that changes downstream economics? | Expected future ore or logistics never enters the current process |
| Alumina conversion | Which realization, feed, fuel and reagent changes reach external contribution? | Segment earnings move mainly through internal transfer assumptions |
| Primary metal with energy exposure | What portion of metal-price improvement survives actual energy and feed terms? | Contract basis, location, profile or input costs absorb the expected benefit |
| Restoration and restart | Which physically usable capacity returns, at what cost and with what saleable output? | Enabled capacity remains unstable, requires more capital or cannot ship |
| Rolled/extruded product conversion | Are industrial margins and customer volumes improving independently of metal turnover? | Cash and earnings are dominated by price lag, inventory or temporary compensation |
| Recycling and recovery | Is improved qualified yield or sourcing spread producing retained contribution? | Scrap input reprices, grades change or the same tonnes are counted at several stages |
| Product/customer qualification | Does a specific commercial relationship support utilization and usable customer value? | No supported premium, schedule, acceptance or cost-to-serve bridge exists |
| Acquisition and alternative use | What changes in the funded, attributable value and claims on the asset? | Financing closes but ownership does not; synergy units or asset perimeter are misread |

These are proposed research facets, not new canonical theme identifiers or investable constituent lists. A company may participate in several roles, but overlapping measures must be visible. Energy context belongs to the same underlying contractual/asset facts, not a new mining-specific power truth store.

### AL-P01 — “Aluminium rose. Which exposure actually improved?”

Start from an existing theme and an issuer's asset/product dossier. Show external versus internal inputs, relevant realization and cost formulas, and the periods they affect. The answer should distinguish a merchant input seller, a purchased-input smelter, an integrated group and a converter. It should explain a supported mechanism at its actual evidence strength rather than present all as equally positive.

The user should be able to identify the limiting unknown: for example, unreported power index share or a missing external-feed quantity. That unknown stops the numerical sensitivity but not the useful qualitative explanation. Acceptance requires an intelligible counter-thesis and source drilldown, not an unexplained unavailable-score badge.

### AL-P02 — “Is the power agreement enough to restart or protect margins?”

Display start/end dates, location, volume units and pricing evidence beside the plant/tranche. Separately show physical restart and supported commercial conditions. The output must explain which risk narrows: renewal, supply availability, price exposure or something else. Missing hourly shape or price formula must remain visible.

A positive signed agreement should advance the relevant context without claiming current full protection. The same workflow should identify a later completed restart while withholding full-year saleable output until evidence supports it. Financial hedging and physical reliability must remain separate links in the explanation.

### AL-P03 — “Why did earnings improve while cash weakened?”

Show comparable earnings with its metal-lag definition, then the actual operating and investing cash bridge. Identify inventory funding, collateral, insurance and growth investment only where supported. Keep temporary sources of cash separate from the operation expected to generate recurring funds.

The answer should help the reader decide what to investigate next: collection, inventory normalization, restart production, capital completion or a changed financing burden. It must not automatically label every negative cash quarter a deteriorating business, or every positive adjusted measure sufficient to fund obligations.

### AL-P04 — “What did the acquisition announcement and financing actually change?”

Show the announced perimeter, the assets currently owned, financing status and any conditional economic-effective mechanism. Separate consideration, debt, potential contingent payments and shares. State whether a benefit is annual, cumulative, run-rate or discounted value. Pro forma financials require their own assumptions and should not replace historical observations.

The result should recognize genuine financing progress while explaining the remaining execution and value-capture questions. A later closing event should update the owner relationship without rewriting what the earlier company owned. No raw transaction headline should directly originate or size a trade.

## 6. Twenty-eight prospective requirements

These specifications are proposed tests of the future product. The local research checker does not implement them in Mastermind.

| ID | Required behavior |
|---|---|
| ME-01 | Preserve stage, input/output product, operating entity and economic interest before deriving exposure. |
| ME-02 | Separate internal transfers from net external receipts and costs. |
| ME-03 | Do not infer a neutral natural hedge from an integrated corporate label. |
| ME-04 | Bind future feed quality to the source's effective period rather than current cost assumptions. |
| ME-05 | Preserve capacity, production, inventory and shipment boundaries. |
| ME-06 | Distinguish MWh/TWh delivered energy from MW contractual capacity. |
| ME-07 | Retain power price area and supported delivery profile. |
| ME-08 | Distinguish fixed, indexed, cost-of-service and metal-linked pricing; unknown coefficients stay unknown. |
| ME-09 | Do not apply a future PPA to a present-period margin. |
| ME-10 | Separate physical continuity from financial price protection. |
| ME-11 | Separate derivative fair value, settlement cash, collateral balances and collateral cash changes. |
| ME-12 | Reconcile reported and adjusted cash without applying an adjustment twice. |
| ME-13 | Scope restart updates to the supported tranche and dated event. |
| ME-14 | Do not transform cell counts or nominal capacity into proportional revenue. |
| ME-15 | Allow supported external feed as a conditional alternative to captive supply. |
| ME-16 | Distinguish metal pass-through sales from industrial conversion contribution. |
| ME-17 | Preserve subsidiary versus tradable-parent identity and coverage. |
| ME-18 | Match metal-lag inclusion for result, peer and guidance comparisons. |
| ME-19 | Label guidance remainder as arithmetic, not consensus or a forecast. |
| ME-20 | Keep acquisition financing, legal completion and conditional economic-effective terms distinct. |
| ME-21 | Separate NPV, annual savings, run-rate benefits and cost to achieve. |
| ME-22 | Distinguish assumed financing coupons from actual issuance and accounting expense. |
| ME-23 | Preserve contingent maximum, modeled fair value and actual payment separately. |
| ME-24 | Do not infer price, premium or yearly delivery schedule from aggregate contracted tonnes. |
| ME-25 | Do not sum sorting, casting and distribution of overlapping recycled material. |
| ME-26 | Keep disposed operations, restricted proceeds, retained interests and alternative use distinct. |
| ME-27 | Preserve source-access limits and original vintages; mirror access is not native retention. |
| ME-28 | Demonstrate meaningful real-path synthesis, unknown-input and changed-source behavior before product acceptance. |

## 7. What this closes and what remains

The aluminium/energy domain now has representative comparisons across feed, refining, metal, power, conversion, recycling, acquisition and alternative asset use. It is no longer only a taxonomy placeholder. This does not establish a global delivered-cost curve, all current contracts, Chinese company-table audit, commercial carbon premium, customer-program census or an investment strategy.

The remaining high-value regime work is nickel/cobalt and graphite/anode economics, followed by a bounded decision on selected alloy and thermal-coal distinctions. Select cases for a different economic mechanism, not another similar press release. Actual energy pricing coefficients, delivery shapes, feed substitution costs, contract cash flows, settlement values and complete ownership/dilution remain claim-specific gaps.

After those contrasts, consolidate overlapping research requirements into a smaller native behavior contract, inspect then-current GMI/assertion/correction and Themes/F04 publication interfaces, and prepare the written design and staged implementation plan. The first useful slice remains a bounded economic dossier, not a new sector portal, graph authority or automatic stock-ranking engine. Source reuse and publication rights require specific acceptance; public availability alone is not that acceptance.

## 8. Source register and evidence limitations

All records are primary issuer material, with the Chalco document accessed through an archive mirror. Research cutoff is 23 September 2026; actual local checking time is separately recorded. Only selected assertions are admitted. No complete third-party reports, source images or restricted datasets are redistributed. Sources can overlap earlier passes; the count below is not a unique-source census for the entire program.

- **AL-S01. Hydro, Q2 2026 release, July 22.** Full HTML; selected segment statements. https://www.hydro.com/en/global/media/news/2026/hydros-second-quarter-2026-operational-strength-delivering-solid-results/
- **AL-S02. Hydro, Q2 2026 report.** PDF, selected printed pp.10, 34, 36 visually checked for energy, collateral and FCF. https://www.hydro.com/globalassets/06-investors/reports-and-presentations/quarterly-reports/2026/q2k9pev/second-quarter-report-2026.pdf
- **AL-S03. Hydro/Eviny PPA, July 7, 2026.** Full HTML, duration/energy/location, not full price contract. https://www.hydro.com/en/global/media/news/2026/hydro-and-eviny-sign-long-term-power-contract/
- **AL-S04. Century, June 30, 2026 Form 10-Q.** Primary SEC HTML; power agreements and Hawesville disposal selected. https://www.sec.gov/Archives/edgar/data/949157/000162828026054308/cenx-20260630.htm
- **AL-S05. Hydro, Slovalco restart announcement, July 1, 2026.** Dated issuer conditions and tranche, not independently established regulatory status. https://www.hydro.com/en/global/media/news/2026/slovalco-to-restart-75000-tonnes-of-curtailed-aluminium-capacity-supplying-a-critical-raw-material-for-europe/
- **AL-S06. Alcoa, San Ciprian resumed restart, July 14, 2025.** Historical primary HTML. https://investors.alcoa.com/press-releases/press-release-details/2025/San-Ciprin-Smelter-Resumes-Restart-Following-National-Power-Outage/default.aspx
- **AL-S07. Alcoa, Q2 2026 results, July 16.** Primary HTML; production, shipments and actual restart event, not complete asset census. https://investors.alcoa.com/press-releases/press-release-details/2026/Alcoa-Corporation-Reports-Second-Quarter-2026-Results/default.aspx
- **AL-S08. Novelis, Q1 FY2027 results, August 5, 2026.** Quarter ended June 30; primary HTML, earnings/lag/cash tables. https://investors.novelis.com/news-events/press-releases/detail/1425/novelis-reports-first-quarter-fiscal-year-2027-results
- **AL-S09. Constellium, Q2 2026 results, July 29.** Primary SEC HTML, text and financial reconciliation; USD measure definitions retained. https://www.sec.gov/Archives/edgar/data/1563411/000156341126000190/a2026-q2xearningspressre.htm
- **AL-S10. Alcoa, proposed South32 asset acquisition, June 30, 2026.** Primary HTML; consideration/perimeter and synergy NPV. https://investors.alcoa.com/press-releases/press-release-details/2026/Alcoa-Announces-Strategic-Acquisition-of-South32s-Bauxite-Alumina-and-Aluminum-Assets-for-4-1-billion/default.aspx
- **AL-S11. Alcoa, updated unaudited pro forma information, September 9, 2026.** SEC exhibit; assumptions and conditional economic terms, not actual combined operations. https://www.sec.gov/Archives/edgar/data/1675149/000119312526385947/aa-ex99_3.htm
- **AL-S12. Alcoa, financing closing, September 23, 2026.** SEC issuer release; financing completed, acquisition conditional. https://www.sec.gov/Archives/edgar/data/1675149/000119312526399499/aa-ex99_1.htm
- **AL-S13. Hydro/Nexans agreement, July 6, 2026.** Primary HTML; product/customer and aggregate delivery period. https://www.hydro.com/en/global/media/news/2026/hydro-and-nexans-enter-longterm-supply-agreement-to-strengthen-europes-electricity-grid-with-lowcarbon-aluminium/
- **AL-S14. EGA, alumina debottlenecking, September 2, 2025.** Historical primary HTML; not a current annual-output observation. https://media.ega.ae/ega-completes-debottlenecking-expansion-at-al-taweelah-alumina-refinery-unlocking-up-to-50-thousand-tonnes-per-year-of-additional-alumina-production/
- **AL-S15. EGA, H1 2026 results, August 12.** Primary HTML; selected input-route/recovery context, not geopolitical causation analysis. https://media.ega.ae/ega-delivers-resilient-h1-2026-performance-maintaining-operational-and-supply-chain-continuity-amid-regional-disruption/
- **AL-S16. EGA, restoration update, August 26, 2026.** Primary HTML; cells restored and internal use, not direct revenue equivalence. https://media.ega.ae/egas-al-taweelah-smelter-restoration-reaches-25-completion-milestone/
- **AL-S17. EGA, Eco Green acquisition completion, September 10, 2026.** Primary HTML; current ownership and overlapping physical stages. https://media.ega.ae/ega-completes-acquisition-of-80-of-italian-aluminium-recycling-firm-eco-green/
- **AL-S18. Chalco, August 27, 2026 interim issuer document.** Issuer publication identity corroborated at https://www.chalco.com/en/tzzgxen/yjbgen/202608/t20260828_176608.html . Direct PDF fetch failed; issuer-authored narrative and PDF parsed text accessed at https://cdn.financialreports.eu/financialreports/media/filings/50704/2026/RNS/50704_rns_2026-08-27_61eed2e9-cbc3-4890-98a2-e5e5de8d2263.pdf . Screenshot route failed; no table-derived arithmetic, full authenticity/byte-equivalence or visual-table verification claimed. Archive commentary was not used as primary evidence.
- **AL-S19. Alcoa, Australian operations update, February 17, 2026.** Primary issuer HTML, selected future feed timing only. https://fr-ca.news.alcoa.com/press-releases/press-release-details/2026/Alcoa-Furthers-Approvals-Modernization-with-Australian-Government/default.aspx

The Hydro release contains an apparent quarter-label inconsistency in one adjusted-income paragraph; that ambiguous number is not needed here. Chalco direct/mirror access limitations remain explicit. Alcoa's September financing assumptions are not silently overwritten by later actual terms. No model probabilities, live prices, independently retained historical consensus or complete accounting/contract audit were produced.

## 9. Continuation and verification boundary

The companion checker runs selected financial arithmetic, hypothetical examples, document indexing and incompatible-input examples. It is not an application test, accounting audit, production contract engine, source-rights acceptance, independent research review or validated strategy. Exact GitHub commit/blob readbacks and the current cumulative Agent OS checkpoint establish publication; a local filename does not.

Keep all work on the existing carrier. Preserve Passes 01–06, their historical receipts and the canonical/duplicate Pass05 distinction. Update the existing coverage document, not a competing registry. No Fable/worker dispatch, Executive Attempt, watcher, live config/schema/data, basket, rank/entry/size/trade, merge or deployment is authorized or performed by this report. The broader research mission and final Fable package remain incomplete.
