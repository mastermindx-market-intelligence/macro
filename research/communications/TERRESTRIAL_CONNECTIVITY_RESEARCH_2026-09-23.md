# Communications Phase 5 — Terrestrial Connectivity and Capital Returns

**Research date:** 2026-09-23. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794, `claude/communications-sector-research-20260923`.
**Status:** Original research and proposed requirements. Not an accepted final specification, admitted taxonomy, current securities recommendation, return backtest or Fable dispatch.

## 1. The question this phase resolves

The investor needs to understand whether a network transition creates more value for the shareholder, rather than merely more connections, construction or reported cash. The proposed organizing question is: **Does a local network and customer cohort earn enough incremental retained cash to fund acquisition, connection, service, capacity replacement and financing?** This is a research framework, not an empirically accepted stock-selection factor.

This phase covers wireless, fiber, cable, fixed wireless, convergence, wholesale access and network partnerships. Nine current issuer anchors span the United States and Canada: AT&T, Verizon, T-Mobile, Charter, Comcast, BCE, TELUS, Rogers and Quebecor. They are not a complete census, nor automatically one comparable peer group. Prior advertising, media, rights and gaming findings are preserved. Satellite has a separate next research phase because deployment and service availability require additional models.

The machine job is to connect a specific operating change to its network footprint, customer population, financial mechanism, capital obligation and dated expectation. National adoption must not substitute for local economics. A service may be improving while the consolidated issuer is not; an issuer may generate more adjusted cash while its service economics weaken. Both situations should remain explainable.

The shared sector template, GMI semantic/evidence ownership, ThemeState, F04 composition and existing evaluation/selection owners remain unchanged. These chapters add domain knowledge and design requirements. They create no graph, geography identity service, data collector, valuation store, scheduler, or trading policy.

## 2. Six economic roles and their distinct constraints

**Mobile network operator.** Investigate retained service relationships, device subsidies, spectrum, coverage, busy-hour capacity, site costs, acquisition economics and financing. A phone, connected device, account and household are different units. The relevant margin is not necessarily the reported segment margin.

**Fiber infrastructure owner.** Investigate construction cost, serviceability, connection timing, cohort penetration, maintenance, access revenue and capital commitments. A passed location has different economic meaning from a connected paying location. A newly built network and a mature network cannot be compared using one aggregate penetration number.

**Retail broadband provider.** Investigate the customer relationship, price realization, installation, service/support costs, wholesale terms and churn. The retailer may not own the underlying network. A seemingly lower-capital retail model can carry large wholesale payments or equity funding elsewhere.

**Cable converged operator.** Investigate the whole broadband/mobile household contribution, network upgrades, wholesale mobile access, legacy video exposure and competitive overlap. A new mobile line can protect a household or subsidize an existing one; line growth alone does not distinguish these outcomes.

**Fixed-wireless access operator.** Investigate spatially available radio capacity, equipment, backhaul, performance under load and opportunity cost to other services. Capacity that is attractive to monetize today may require expensive incremental investment at higher utilization. This is a conditional engineering/economic hypothesis, not evidence that every operator is currently constrained.

**Wholesale network or infrastructure partner.** Investigate access contracts, committed funding, control rights, minority interests, financing and the separation of retail and asset ownership. An infrastructure counterparty may sit in another formal sector; economic relevance does not amend its classification.

These roles overlap within issuers. The research map must preserve role, geography, legal ownership and business scope rather than assign a single permanent company label.

## 3. Customer economics: measure survival and contribution, not just net adds

### 3.1 Cohort-level model

For a proposed acquisition cohort, let S(t) be the probability a customer remains economically active in month t; C(t) is cash contribution in that month after relevant service costs and promotions; A is acquisition plus initial connection expenditure. A finite-horizon research estimate is:

`cohort value = -A + sum[S(t) * C(t) / (1 + monthly discount rate)^t] - separately scoped reinvestment`

The horizon, discount convention, survival curve, costs and residual value must be explicit. A model does not become a fact because the arithmetic is reproducible. Constant churn is an illustration, not a validated forecast of every cohort. In particular, `ARPU / churn` is not cash lifetime value: it ignores cost, discounting, reactivation, changes in hazard, promotions and a finite observation window.

Track voluntary and involuntary exits separately when reported. Investigate whether apparently better retention reflects better service, longer installment commitments, delayed disconnection, a change in population, or customer selection. A contract asset's amortization period is not a measured customer lifetime. Reactivation cannot be silently counted as both a retained customer and a new unique customer.

### 3.2 A falsifiable convergence thesis

The proposed thesis is that a combined household relationship may reduce churn and acquisition expense sufficiently to exceed discounts and added service costs. The competing hypothesis is that the operator pays a large discount to households that would have stayed anyway.

The appropriate quantity is incremental household contribution relative to a credible alternative, not the sum of standalone product margins. Distinguish genuinely new households, cross-sold existing households, migrations, extra phone lines and acquired relationships. Test retention across comparable pre-existing tenure, credit risk, product quality and geography. Observational bundle customers self-select; a lower observed churn rate is not automatically a treatment effect.

Suggested leading evidence includes offer changes, take-up by eligible cohort, retention after introductory discounts expire, realized revenue after credits, support cost and the evolution of the competitive footprint. Public evidence may reveal only some links. In that case the product should explain the hypothesis and its missing evidence, not manufacture a causal coefficient.

### 3.3 Current sources that fix the denominator

AT&T reports 42.5% convergence using advanced home internet connections whose primary wireless account holder also subscribes to consumer postpaid phone service. Its 38.6 million fiber locations reached include owned/operated and partner/open-access locations. The source's definitions—not an intuitive meaning of “household” or “owned network”—govern these measures [AT1]. Comcast's 7% wireless penetration uses total addressable wireless lines, a different denominator [CM1]. Comparing 42.5% and 7% as the same adoption measure is invalid.

T-Mobile reports 277,000 net account additions and a separate 16,000 account-base reduction associated with Metronet repurchases. Its account reconciliation is 34.439m + 0.277m - 0.016m = 34.700m. The adjustment is not another churn observation. Its ARPA of $152.91 is per account, not a phone-line ARPU [TM1].

These examples support an implementable research requirement: every number must identify what was counted, which population was eligible, and which base changes were excluded from organic activity.

## 4. Fiber: construction success is not yet investment success

### 4.1 Separate the deployment states

A useful research progression is planned footprint, built/passed location, marketable location, installation, activated service, paid service, retained cohort and realized cash contribution. This is an analytical decomposition to map into existing evidence, not a new execution lifecycle. Each transition can fail independently.

A construction milestone reduces one uncertainty while leaving demand and financing uncertain. Record original schedule, revised schedule, expenditure to date, remaining expenditure, serviceability and the eventual paying population at the appropriate grain. A location passed in a press release does not certify installation cost, occupancy, customer acquisition or a particular speed under load.

### 4.2 Cohort dilution can look like deterioration

Illustration: 1,000 mature locations with 500 customers have 50% penetration. Add 1,000 new locations with 100 customers. Aggregate penetration becomes 30%, although the mature cohort has not deteriorated and the system added 100 customers. The reverse can also happen if low-penetration locations are removed from the denominator.

The proposed view therefore shows penetration by construction vintage where the source supports it, alongside aggregate penetration and denominator changes. Do not divide this quarter's net subscriber additions by this quarter's new passings and label the result a take rate: they need not come from the same cohort. Charter's rural passing and subscriber-addition disclosures make that an important boundary to preserve [CH1].

### 4.3 Capital-allocation threshold

For each build cohort, compare the present value of retained cash from expected adoption with passing cost, activation cost, shared incremental infrastructure, maintenance, and the opportunity cost of capital. Include the delay between cash construction and monetization. Density and addressability affect costs; overlap and competitor behavior affect adoption and price. Those effects require local evidence rather than a national multiple.

The discriminating research is whether new cohorts reach viable economics at lower cost or faster penetration, whether legacy cohorts retain pricing, and whether expansion consumes more cash than the mature base can supply. A falling company capex ratio can be a maturation milestone, a perimeter change, delayed necessary work or a move into off-balance-sheet funding. It is not automatically a positive return signal.

In the companion's deliberately simplified ten-year case, an initial cost of 1,000 and 160 annual contribution at a 10% discount rate has NPV about -16.87; 180 annual contribution has NPV about +106.02. A modest difference in the assumed economic yield changes the conclusion. These are teaching assumptions, not telecom underwriting benchmarks, estimates of actual passing costs or an approved hurdle rate.

## 5. Fixed wireless: value the marginal capacity, not theoretical reach

The attractive hypothesis is monetization of usable residual network capacity with a smaller initial customer connection cost. The opposing hypothesis is that growing demand forces incremental spectrum, densification, backhaul or service-quality spending that consumes the apparent advantage. T-Mobile's dated 2024 description explicitly connected home-internet availability with capacity for both mobile and home customers; it is a historical methodology anchor, not current market-by-market availability proof [FW1].

Model the relevant time and place. National covered population does not identify a home's eligibility, current installation acceptance, busy-hour throughput or marginal cost. A drop in additions can reflect admission limits, weaker demand, seasonality, pricing or distribution—not one predetermined explanation. Device capability, spectrum, load, backhaul, customer usage and competing demands must be studied together.

A proposed marginal decision is `incremental home cash contribution - additional operating/connection cost - expected displaced mobile contribution - required capacity investment`. Keep any displaced contribution as a labeled scenario until supported. Average bytes or average national speeds cannot establish this opportunity cost. When cell-level data are private, retain the national evidence as partial, and investigate source-defined service availability and quality at permitted geographic aggregation.

FWA and fiber can be substitutes in some locations, complementary segmentation in others, and migration stages within the same operator. Do not persist a universal “FWA harms fiber” relation. The graph explanation should state the local overlap, customer segment and financial pathway on which that conclusion depends.

## 6. The US issuer contrasts: acquisitions, substitution and ownership

### 6.1 AT&T: transition includes a fixed-cost exit problem

AT&T's reported legacy revenue fell 25.9% while direct operating costs fell 10.8%. Management forecasts that legacy EBITDA will turn negative after 2027 until copper direct costs are substantially removed. Its explanation ties geographic cost removal to decommissioning after customers have migrated [AT1]. This is a forecast of an uneven transition, not evidence that shutdown savings have already been achieved.

Research must map gross advanced-service contribution, lost legacy contribution, dual-running expense, migration costs and actual shutdown milestones. Treat a customer migration as a change in service economics, not necessarily a newly acquired household. The last costly migration in a geography can have different value from the first. The opportunity to remove a fixed cost needs an achieved prerequisite, not a management target alone.

AT&T's Q2 FCF reconciliation subtracts both capex and cash vendor financing; rounded billions reconcile as 10.8 - 5.7 - 0.4 = 4.7. Network investment is not fully measured by the capex line alone [AT1]. The underlying 10-Q was located but not comprehensively audited [AT2].

### 6.2 Verizon: a better growth label can still need a comparable perimeter

Verizon reported total revenue down 0.7% and mobility/broadband service revenue up 2.8% [VZ1]. Its Consumer filing attributes a $712m fiber increase primarily to Frontier, alongside a $365m postpaid decrease affected by promotions and acquisition-related discounts. Frontier closed in January 2026 [VZ2]. These are reported drivers with segment scope, not a complete organic-growth bridge.

The appropriate research asks what the existing customer base is doing after separating acquired activity, service categories and effective promotional economics. Do not subtract the whole fiber increase from consolidated revenue and call the residual organic. A segment driver's external/intersegment basis must match the total to which it is compared.

### 6.3 T-Mobile: owning the customer is not owning all the infrastructure

The filing describes Lumos and Metronet as wholesale network structures, with T-Mobile owning retail customer relationships. Equity interests and further capital contributions coexist with postpaid retail revenue, network-access costs and equity-method earnings [TM2]. Thus a retailer's lower reported network capex does not establish that growth requires no capital. Avoid adding the retailer's revenue, the network's access revenue and the parent's share of network earnings as three independent industry revenue pools.

The research map should link specific retail relationships, access contracts, equity stakes, future contributions and accounting perimeter. Pending i3 and GoNetspeed/Greenlight transactions remain announced/expected in this filing; they are not admitted as completed holdings without subsequent completion evidence [TM2]. Announced plans create questions for later research, not current ownership facts.

### 6.4 Charter and Comcast: mobile activity does not automatically replace broadband economics

Charter's residential internet revenue declined $193m while mobile revenue increased $174m, leaving combined connectivity revenue down $19m. Its 406,000 mobile-line additions and 172,000 internet losses describe different units [CH1]. This establishes the need to measure total relationship economics, not that either product by itself determines the equity outcome.

Comcast reported domestic convergence revenue down 3.2%, with broadband losses and wireless additions. Its release also presents pro forma adjustments for portfolio changes [CM1]. The conceptual comparison is the same; the measurement populations are not necessarily identical to Charter's.

Research should investigate whether cross-selling improves survival and total contribution, and what it costs in introductory offers and wholesale payments. Internet price realization, video run-off, support and investment can offset mobile gains. A new line can be financially useful without compensating fully for a lost broadband household. No counterparty market-share transfer is inferred from these releases alone.

## 7. Canada: contrast operators, not a single country label

### 7.1 BCE: AI exposure introduces a funding obligation

BCE reported CFO of C$2,162m versus C$1,947m, capex of C$1,080m versus C$763m, and FCF of C$1,042m versus C$1,152m. It also provides FCF after lease-liability payments of C$784m. Bell Canada results and the acquired US Ziply contribution require separate analysis [BC1]. A Canadian issuer is not purely Canadian operating exposure.

The dated guidance table distinguishes February 5 FCF of C$3.3–3.5bn from the March 16 C$2.1–2.3bn range incorporating the Saskatchewan AI data-center investment. This is an earlier guidance revision restated in the Q2 report, not a new Q2 revision or a verified consensus surprise [BC1].

Our thesis question is whether the new investment's contracted utilization, price, funding and retained returns justify its near-term cash demand. The evidence so far establishes the cash commitment and management's intended growth pathway, not the realized project return. AI-related enterprise activity and ownership of computing infrastructure are different exposures.

### 7.2 TELUS: cash growth and dividend safety are different claims

TELUS reported CFO of C$1,342m versus C$1,166m and FCF of C$545m versus C$535m, while adjusted EBITDA declined. The reconciliation shows lower tax cash payments and lower lease principal. It announced a roughly 55% dividend reset and a revised deleveraging timeline. Its capex discussion explicitly mentions customer-equipment inflation/supply dynamics and AI infrastructure investment [TU1]. Those are company-scoped physical/capital constraints, not evidence of a universal equipment shortage.

Research must separate tax timing, lower lease cash, earnings, working capital, new commitments and distributions. A higher non-GAAP FCF figure cannot alone certify the old dividend, and a dividend reset does not on its own establish an attractive investment. Evaluate cash retained for financing and reinvestment, then the shareholder claims and expectations. Non-cash impairment changes accounting carrying value; it does not pay debt.

### 7.3 Rogers: the name of a cash measure is not its definition

Rogers reports C$1,517m CFO versus C$1,596m, but company-defined FCF rises to C$982m from C$925m. The published reconciliation includes interest, working capital, restructuring-related adjustments and C$117m distributions to non-controlling interests. Its quoted 66.0% wireless adjusted EBITDA margin uses service revenue, not total wireless revenue [RC1].

The proposed comparison must preserve the full cash bridge and denominator. It should neither declare Rogers' figure wrong nor silently compare it with another issuer's unadjusted CFO less cash capex. Equity partner cash claims are economically material even when the consolidated infrastructure still appears in a company's operating presentation.

### 7.4 Quebecor: a useful counterexample to country-wide inference

Quebecor reports telecom revenue up 4.0%, telecom adjusted EBITDA up 5.3%, and mobile ARPU up 2.5%, in contrast to some incumbent readings [QB1]. This is evidence of differing issuer trajectories, not a buy recommendation or proof of a particular incumbent-to-challenger customer transfer.

Investigate footprint, brand, distribution, customer composition, contract costs, and achieved integration. A growing period-end customer base and increasing ARPU do not mechanically reconstruct organic revenue without average populations and scope. Its share-price-linked compensation also reinforces the earlier finding that equity-price movement can affect expenses; it is not automatically independent operational information [QB1].

## 8. Valuation: earn the multiple through a cash and claim bridge

### 8.1 Keep the cash conventions aligned

For each issuer, retain reported CFO, cash capex, vendor-financing repayments, lease principal, spectrum transactions, equity/JV contributions, acquisitions, pension effects, securitization effects and non-controlling/preferred claims at their native scope. Not every item applies to every issuer. Do not deduct an item twice when the reported starting measure already includes it.

An enterprise valuation should use a cash flow before the financing claims subtracted from enterprise value; an equity valuation should use cash attributable after those claims. Mixing after-interest cash flow with a pre-interest valuation bridge can double-count financing. Similarly, choose a lease-consistent convention: an after-lease earnings/cash measure and a debt-like lease capitalization require careful reconciliation, not mechanical addition.

“Maintenance” and “growth” capex must remain disclosed, explicitly modeled, or unknown. A company may label a project strategic; the analyst still needs to determine whether comparable future cash assumes ongoing replacement. Do not use a temporary investment trough as the permanent cash base or treat every acquisition as optional while depending on acquired growth indefinitely.

### 8.2 Three distinct rerating pathways

**Earnings revision:** better retained service contribution, lower genuine operating cost or improved capital productivity changes a matched-horizon earnings/cash estimate. Fewer tax payments in one quarter need not establish this pathway.

**Risk reduction:** confirmed deployment, stable utilization, a completed refinancing or funded commitments reduce uncertainty around an existing cash stream. An announcement or target is weaker evidence than an executed result.

**Capital allocation and claim change:** repurchases, partner transactions, divestitures or debt reduction change cash entitlement and risk. A smaller equity denominator can raise EPS even if total earnings are flat. New shares issued through reinvestment programs can offset repurchases. Authorization is not execution; expected sale proceeds are not cash received.

A scenario illustrates leverage: enterprise value 100 less net claims 60 leaves equity 40. At enterprise value 90 with claims unchanged, equity is 30, a 25% decline. This arithmetic does not imply any issuer's current valuation or predict a return. It explains why apparently stable network revenue does not guarantee low equity sensitivity.

### 8.3 Macro and regional conditioning

Investigate real/nominal rates through separate channels: discounting, refinancing schedule, customer affordability, capital costs and competitive investment. A fixed-rate liability is not immediately repriced like new borrowing. Foreign operating cash, reporting currency, debt currency and the investor's trading currency may differ. Model them separately; do not impose one “rates-sensitive telecom” label on every business.

Sector classification, country of domicile, operating geography and listing identity remain existing-owner facts. The collision between AT&T's NYSE T and TELUS's TSX T is a useful identity acceptance case: a ticker string alone cannot resolve an issuer. This research does not create its own security master.

## 9. What constrains growth, and what can be observed lawfully

The useful adaptation of the Robotics question is “what prevents the next economically valuable unit of service?” The answer may be equipment, construction, access to a site, installation, demand, financing, utilization or a difficult final legacy migration. A source must establish a particular constraint's scope; a generic bottleneck tag is insufficient.

Public evidence can include operator disclosures, price/offer changes, original guidance, reported construction and subscriber measures, aggregate quality indicators, and source-defined availability. FCC methodology distinguishes availability from actual subscriptions and describes serviceability conditions. Public location-based availability does not automatically confer access to an enriched licensed Location Fabric, and subscription data can carry confidentiality restrictions [FD1–FD3]. No individual customer tracking or private-address enrichment is proposed.

The CRTC changelog demonstrates mixed freshness: its August 21, 2026 release includes quarterly series through Q1 2026, other monthly observations, and preliminary year-end coverage. It also records revised household availability and changes in ARPU series, including device-inclusive/exclusive treatment [CR1]. A current page date is not a common observation date for all its metrics.

The first data-feasibility output should be a field-level matrix of provider, unit, coverage, time, revisions, rights, cost and missingness. Missing a local subscriber count should not erase the measured availability map, but the map must not be relabeled penetration. A source license held by a telecom partner does not automatically grant Mastermind equivalent rights.

## 10. Historical study and learning design

Frontier's April 2020 restructuring announcement paired an intention to reduce more than $10bn of debt with continued customer service [H1]. It is an original proposed restructuring event, not a later emergence receipt. The useful lesson for research design is to separate continuity of the network/service from the capital claims on that asset. No stock-return attribution or single-cause explanation is established here.

Build historical cases around the actual decision: new fiber cohorts, cross-sell offers, FWA admission, mature-network investment transitions, failed funding assumptions, acquisitions, and legacy closures. Preserve unsuccessful operators, restructuring events, acquired businesses and changed perimeters. Today's surviving issuers are not a complete historical population.

For descriptive analysis, reconcile source definitions and cash arithmetic. For operating forecasts, use information genuinely available at the decision time and hold out later periods and geographies. For an investment application, separately qualify original estimate vintages, returns, corporate actions, market/sector exposures and the existing decision-authority gates. No predictive qualification has been performed in this phase.

A proposed local-rollout study should compare pre-existing trends, competitive overlap, density and demand before interpreting treated versus untreated areas. Rollouts are selected, not random; aggressive builders may choose locations with better demand. Spillovers, concurrent competitor investment, acquisitions and price changes can defeat a simplistic causal comparison. A difference-in-differences label is not proof that the identification assumptions hold.

Research should measure whether a new feature adds information beyond basic revenue, capex and leverage baselines. Keep missed opportunities and abstentions, not only successful narratives. Before any return claim, separate original forecast-horizon revisions from fiscal-year roll and source corrections. Current-cache freshness is not proof of a pre-event consensus vintage, consistent with the prior earnings-owner inspection.

## 11. Proposed product and Fable-ready requirements

The investor journey should be: existing theme view → what changed → relevant network/customer role → operating and capital explanation → dated expectation → contrary/missing evidence → company/watchlist. The shared template remains the presentation owner. A separate map or universal opportunity score is not required.

Three useful proposed panels are a **cohort/deployment explanation**, a **service-to-shareholder cash bridge**, and an **expectation/capital-commitment timeline**. Each must answer an investment question. A map is useful only if scope and data rights allow the user to evaluate overlap; decorative geographic coverage is not the outcome.

The glance view should say things such as “service revenue improved, but acquired fiber accounts for a material part,” “mobile gains nearly offset internet revenue loss, while household profit remains unqualified,” or “growth investment reduced the earlier cash outlook; project returns are not yet observed.” Technical state codes stay in evidence details. Shared dark/light, EN/ZH and responsive design requirements remain controlling at implementation; no UI acceptance is claimed here.

The eventual Fable package should map these requirements into existing contracts, choose a bounded first slice and supply production-path examples with missing/conflicting states. The current advertising-first candidate is not replaced by each new research chapter. Cross-domain design selection and the final written specification still require completion of the remaining work and the established review gates.

Thirty proposed metric definitions and thirty-two adversarial cases in the companion focus on actual harm: false organic growth, wrong penetration, fictional recurring cash, lease/claim double-counting, stale estimates, and broken drill-through. They are not thirty-two passed application tests.

## 12. Coverage and exact next research unit

This phase supplies a source-backed US/Canada operating comparison, local cohort/capacity/capital models, worked cash bridges, conditional rerating mechanisms, a historical capital-structure case, public-data constraints and concrete future acceptance requirements. It does not supply a full company census, accepted exposure weights, private contract economics, a validated return model or current production proof.

**Next: satellite communications and direct-to-device economics.** Start with the actual operator/service distinctions, deployment and capacity evidence, licenses, partner payment arrangements, funding and dilution. The T-Mobile filing's May 14 agreement in principle with AT&T and Verizon is a navigation lead: definitive agreements and conditions remain outstanding in that source, so it is not evidence of an operating unified platform [TM2]. Reconcile the then-current event state before using it as an exposure. Preserve original network, identity, ownership and evidence authorities.

Then complete remaining geographic/issuer gaps, cross-family exposure mapping, historical expectation qualification and the written design/master plan. Fable has not been dispatched, ACKed or STARTed. No product code, templates, live evidence, membership, publisher or trade policy changed.

## 13. Source register and provenance

The following are 18 public primary-source references, not 18 independent experiments. [AT2] is limited filing navigation, not a complete financial audit. Company releases and their exhibits are one evidence family. Dates below are verified publication dates where available; an unknown date stays unspecified rather than inferred from checkout time. Most current observations concern the quarter ended June 30, 2026. US amounts are USD and Canadian issuer amounts CAD unless explicitly stated. Selected Rogers and TELUS tables were visually inspected. No bulk private corpus was copied and no data-license entitlement is claimed.

**[AT1] AT&T Q2 2026 release** — 2026-07-22. Consolidated Results; Legacy; footnotes 1–5; FCF and capital investment definitions.
https://about.att.com/story/2026/2q-earnings.html

**[AT2] AT&T Q2 2026 Form 10-Q** — 2026-07-22. Underlying filing identified; limited inspection, not a full note-level review.
https://www.sec.gov/Archives/edgar/data/732717/000073271726000297/t-20260630.htm

**[VZ1] Verizon Q2 2026 release** — 2026-07-24. Service/equipment revenue and broadband additions.
https://www.verizon.com/about/news/verizon-delivers-record-2q26-results

**[VZ2] Verizon Q2 2026 Form 10-Q** — publication date not fully qualified in this register. Acquisitions; Consumer mobility and broadband service revenue, three months ended June 30.
https://www.sec.gov/Archives/edgar/data/732712/000073271226000046/vz-20260630.htm

**[TM1] T-Mobile Q2 2026 earnings exhibit** — 2026-07-23. Postpaid accounts table and footnotes; cash measures; outlook.
https://www.sec.gov/Archives/edgar/data/1283699/000128369926000100/tmus06302026ex991.htm

**[TM2] T-Mobile Q2 2026 Form 10-Q** — publication date not fully qualified in this register. Fiber Joint Ventures; revenue from contracts; wholesale costs; proposed satellite JV.
https://www.sec.gov/Archives/edgar/data/1283699/000128369926000101/tmus-20260630.htm

**[CH1] Charter Q2 2026 release** — 2026-07-24. Residential connectivity revenue; customers; capital expenditure and free cash flow.
https://ir.charter.com/news-releases/news-release-details/charter-announces-second-quarter-2026-results

**[CM1] Comcast Q2 2026 release** — publication date not fully qualified in this register. Connectivity and Platforms; convergence; pro forma presentation and separation footnotes.
https://cmcsa.gcs-web.com/news-releases/news-release-details/comcast-reports-2nd-quarter-2026-results

**[BC1] BCE Q2 2026 release** — 2026-08-06. Bell CTS; outlook February 5/March 16 vintages; FCF and FCF after lease liabilities reconciliations.
https://www.bce.ca/news-and-media/newsroom?article=bce-reports-second-quarter-2026-results

**[TU1] TELUS Q2 2026 release** — 2026-07-31. Printed pp.1–3, operating metrics and p.14 cash bridge; p.14 table visually inspected.
https://assets.ctfassets.net/fltupc9ltp8m/3KvDmEmGVUDgr7aFIavStc/3b9906c65cf459c7cc92e86ff70e3d4b/TELUS_Q2_2026_News_Release.pdf

**[RC1] Rogers Q2 2026 release** — publication date not fully qualified in this register. Printed pp.7 and 18 visually inspected: Wireless and FCF reconciliation.
https://about.rogers.com/wp-content/uploads/Rogers-Q2-2026-Press-Release.pdf

**[QB1] Quebecor issuer-distributed Q2 2026 release** — 2026-08-06. Issuer release carried by PR Newswire; Telecom, mobile, ARPU and share-price-linked compensation.
https://www.prnewswire.com/news-releases/quebecor-inc-reports-consolidated-results-for-second-quarter-2026-302844252.html

**[FW1] T-Mobile home internet product/methodology announcement** — publication date not fully qualified in this register. 2024 historical methodology anchor: home internet availability tied to capacity for mobile and home; not current pricing/coverage proof.
https://www.t-mobile.com/news/network/home-internet-plus-and-away

**[FD1] FCC Broadband Data Collection FAQs** — publication date not fully qualified in this register. Availability versus subscriptions; location IDs and standard installation.
https://help.bdc.fcc.gov/hc/en-us/articles/7682769466395-Broadband-Data-Collection-BDC-FAQs

**[FD2] FCC Location Fabric access guidance** — publication date not fully qualified in this register. Licensing/access distinctions; public availability is not automatic access to enriched Fabric.
https://help.bdc.fcc.gov/hc/en-us/articles/10419121200923-How-Entities-Can-Access-the-Location-Fabric

**[FD3] FCC filer confidentiality requests** — publication date not fully qualified in this register. Subscription-data confidentiality; no assumption of public customer counts.
https://help.bdc.fcc.gov/hc/en-us/articles/8162804537883-Filer-Confidentiality-Requests

**[CR1] CRTC current-trends release changelog** — publication date not fully qualified in this register. Version 20, August 21, 2026; mixed coverage periods and revised household availability; device-inclusive/exclusive ARPU series.
https://crtc.gc.ca/eng/publications/reports/policymonitoring/chg.htm

**[H1] Frontier original restructuring announcement** — 2020-04-14. Voluntary Chapter 11/RSA; proposed debt reduction and uninterrupted operations; original announcement not emergence receipt.
https://www.sec.gov/Archives/edgar/data/20520/000114036120008876/ex99_1.htm

## 14. Canonical continuity

Protected procedure: Mastermind `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`, compatible Skillpack 1.0.1/bootstrap 1. Current branch/INDEX confirmed the unchanged same-revision procedures already loaded. Research rationale: PRINCIPAL_JUDGMENT under the Chairman's continuing instruction.

Original Macro base: `c4da107fe729e46b4d4036b3e0e290390315d0fd`. Incumbent head entering this phase: `4e9cba7d1b9707e80fc085c219e5e9c1efd176fe`. No rebase or replacement carrier. Existing `WS:GMI-THEME-GRAPH`, shared design and Robotics #7773 remain preserved; repository research is not a new runtime or data authority.

Companion: `research/communications/CONNECTIVITY_METRICS_AND_ACCEPTANCE_2026-09-23.md`.
Cumulative checkpoint: `agentos/handoffs/GMI-COMMUNICATIONS-RESEARCH-2026-09-23.md`.
The public JSON/ZIP exports are portable copies of these research definitions and examples, not live source datasets. Final research and product completion remain false.
