# Energy R5A — Expectations, valuation claims and global value capture

**Principal:** Sol. **Research date:** 2026-09-23. **Operation:** `gmi-energy-sector-research-20260923-sol-001`. **Sole carrier:** Macro PR #7791, `sol/energy-sector-research-20260923`.

**Research-only / HOLD.** This document does not authorize product changes, live ingestion, canonical identities, basket weights, ranking, entry, sizing, trading, deployment or a Fable commission. Its publication time is the actual Git commit time, not the date in the filename. R1–R4 remain preserved. Fable remains the eventual implementation/orchestration principal after mature research and design.

## 1. What became possible in this tranche

R1–R4 established economic mechanisms. R5A adds selected real analyst-estimate observations from four issuer-published services, an explicit valuation-claim reference case, and seven additional geographic/business comparisons. The companion model has 20 source locators, 22 grouped observations, 11 cases of differing depth, 45 proposed product requirements and six remaining research obligations. These counts describe research coverage, not accepted graph facts or complete company models.

The earlier statement that no usable analyst values had been acquired is now narrowed: selected source-labelled estimates have been acquired; an independently recoverable historical panel has not. A last-input label, publication policy and downloaded page do not together prove exactly which numbers were available to an investor before an event. That limitation restricts surprise and return claims, not the usefulness of understanding the business or inspecting current source-labelled expectations.

Three questions continue to govern the project:

1. What changes the business's future distributable economics?
2. What does the available evidence say analysts expect, on a matched metric and horizon?
3. How does the security's price compare with an attributable, financing-consistent valuation of those economics?

An answer to the first is not automatically an answer to the second or third. R5A makes the interfaces between them concrete instead of postponing every valuation question behind a generic data gap.

### Evidence convention

[S01]–[S20] point to the companion source register. Issuer filings establish reported facts and issuer-defined measures; issuer consensus services distribute analysts' estimates, not management endorsement. Research interpretations, synthetic examples and proposed product behavior are original analysis. Numerical examples are not named-security targets. The source register preserves partial-read, mutable-page and publication limitations. Selected factual values and authored analysis are retained; no full third-party analyst panel or copyrighted report corpus is republished.

## 2. Expectations are measured objects, not one generic number

### 2.1 Orsted: real estimates, with a still-open historical-vintage boundary

The Euroland summary reached through the issuer page displays July 29, 2026 as last input and Q2 medians of DKK5,103 million EBITDA including new partnerships and DKK1,364 million profit after tax. A linked FY2026 detail returns April 27 instead, with its own sample information. The retrieval discrepancy is preserved; it is not labelled a proven analyst revision or a selected historical archive. [S01–S03]

For the reported Q2 outcome, EBITDA was DKK5,423 million and group profit DKK687 million; DKK518 million belonged to owners and DKK169 million to noncontrolling interests. The owner measure must not replace the group measure simply because the eventual investment is common equity. [S06,S07]

The corresponding source-labelled arithmetic is about +6.27% for EBITDA and -49.63% for group profit. Those percentages are not independently qualified earnings surprises, evidence of market mispricing, or explanations of a stock return. The unresolved item is historical availability and complete metric mapping, not the subtraction itself.

The FY2026 summary also demonstrates why a consensus is not a forecast income statement assembled by subtracting every visible row. Independently aggregated medians need not add. It is mathematically possible for every contributor's forecast to reconcile while medians of the separate lines do not. The engine should preserve the supplied aggregates and their methods, not overwrite them to make the page appear arithmetically tidy.

**Research decision:** support a useful descriptive comparison now, explicitly marked with its evidence limitations. Reserve historically qualified surprise, revisions and return studies for observations with a defensible first-known time, consistent definition, period and contributor treatment.

### 2.2 Vestas: a post-results panel cannot be used before the result

The examined Vestas panel is dated August 21 and explicitly post-Q2. Selected FY2026 means are EUR21,417 million revenue and EUR1,813 million EBIT before special items, each with 16 estimates, versus 15 for free cash flow. The issuer explains that participation varies. [S08,S09]

Dividing mean EBIT by mean revenue gives approximately 8.47%. That is a ratio of aggregate means, not necessarily the mean of analysts' individual margin forecasts. Equal sample counts do not prove the same contributors, and an overall analyst-coverage list does not establish a row's sample.

The economic study should examine whether delivery, pricing, manufacturing and service evidence changes a *fixed* year's expected earnings. It should not mistake a change in sample composition, forecast-year label or accounting treatment for a fundamental revision. This builds directly on R4's distinction between equipment revenue and continuing service obligations; it does not redo that work.

### 2.3 Equinor and Repsol: different aggregation laws

Equinor's July Q2 collection has 17 overall contributors. It trims the highest and lowest input by item and constructs specified operating totals from components. Its consensus adjusted operating income after tax is USD3.380 billion. The reported result is USD3.44 billion; adjusted net income is a different USD3.22 billion measure. Comparing the latter to the operating consensus would answer the wrong question. Adjusted EPS of USD1.33 versus USD1.34 is a separate comparison. Reported billion-dollar rounding limits variance precision. [S18,S19]

Repsol explicitly says business-line estimates need not sum to group adjusted net-income consensus because participation differs. The selected components sum to EUR1,636 million while the supplied group estimate is EUR1,634 million. Its stated publication schedule is evidence of process, not independent proof of the exact historical snapshot retrieved here. [S20]

**Proposed adapter rule:** preserve whether the source supplies a median, mean, trimmed mean or constructed total. Do not impose one calculation on every issuer. Do not silently substitute net income, operating profit after tax, underlying earnings or cash because labels look similar.

### 2.4 How a false revision appears without anyone changing their forecast

In a hypothetical old panel, analyst A forecasts 100 and B forecasts 120: the average is 110. In a new panel, A still forecasts 100 and new contributor C forecasts 160: the average is 130, up 18.18%. The only matched contributor has revised nothing.

A future product should show both the raw aggregate change and a matched-panel calculation when the necessary data exist. With only aggregates, contributor change is an explicit limitation, not something a model can infer away. No invented individual forecasts may be used to manufacture an apparently stable panel.

A second false revision arises from horizon rollover. If FY2026 EPS is 2 and FY2027 EPS is 3, relabelling the next fiscal year can produce an apparent 50% increase despite unchanged forecasts for each year. Research must anchor the target fiscal period before judging revision direction. A constant twelve-month estimate is a different construction again and needs transparent weights and dates.

## 3. The first valuation reference: useful, but not a completed fair-value verdict

### 3.1 Resolve the quote and share unit before constructing a multiple

The Orsted quote module displays September 15, 2026 at 12:12 GMT+02 and a DKK128.65 price. Its million-labelled fields contain a full share count of 1,321,197,680 and market capitalization of DKK169,972,081,532. Exact multiplication reconciles those numbers, and the completed 2025 capital increase independently supports the issued-share count. It is not a current quote or proof that issued shares equal net outstanding shares. [S04,S05]

A unit parser that trusts the caption mechanically would multiply by a million twice. A parser that silently fixes the caption without evidence would introduce a different integrity problem. The proposed behavior retains the original label, the normalization, the independent evidence, and the fact that the quote is dated.

### 3.2 The shareholder claim is not identical to consolidated operating value

The June balance sheet and debt note separately report net debt, hybrid capital, noncontrolling interests and leases. The issuer net-debt measure already includes lease debt; adding the leases again duplicates a claim. Its adjusted-debt convention includes 50% of hybrid capital and additional adjustments. That credit-analysis convention is not automatically an enterprise-value convention. Book minority interests are not established market values. [S07]

The exact debt bridge is retained in the model. On source checking, two preliminary component descriptions were corrected to the note's actual labels: other interest-bearing debt addback and other interest-bearing receivables addback. The numbers were not changed to force a result. This is a pre-publication scope correction, not an accounting restatement or a model validation claim.

A valuation must choose and consistently apply one of two approaches: consolidated operations with all associated debt and ownership claims, or proportionate/parent cash flows with claims treated on the same basis. Neither approach permits subtracting an ownership claim twice or valuing an investee's sales as consolidated operating cash.

The research model therefore retains `EV_market_value`, `EV_EBITDA` and `fair_value` as null. It has a dated equity-capital reference and explicit claim observations, not a complete enterprise valuation. In particular, it must not attach an attractive-looking multiple to a numerator missing consequential claims.

### 3.3 Different input dates are normal; unjustified availability is not

A market valuation commonly combines a current quote with the latest published balance sheet and a forward forecast. Requiring all three measurement dates to be identical would make a normal valuation impossible. The appropriate rule is that every input must have been available by the valuation time, its scope must match, and subsequent capital changes must be reconciled.

Here, the quote is itself older than the research date, the consensus's exact first-publication history is unestablished, and the claim mapping is incomplete. The notebook is labelled a mixed-clock reference, not current fair value or a point-in-time backtest. The user can still inspect what the arithmetic includes and excludes.

A company may look cheaper because a debt item was omitted, a rights issue was ignored, consolidated EBITDA was compared with parent equity only, or a seasonal result was annualized. These are not investment discoveries. They are measurement defects that must be excluded before applying judgment about durability, growth and risk.

### 3.4 Original decomposition: earnings growth, multiple change and financing

In an explicitly hypothetical business, EBITDA rises from 100 to 120 while its enterprise multiple falls from 8 to 7. Enterprise value moves from 800 to 840, or +5%, not +20%. If net claims fall from 400 to 350, common equity rises from 400 to 490, or +22.5%, before distributions and changes in shares.

The value change depends on both operations and financing. A rise in equity value larger than enterprise value need not mean an expansion in the enterprise multiple. Similarly, buying back shares with debt does not create free per-share value before the financing claim is considered.

This is the research grammar we want across Energy: fixed-horizon operating revisions, duration and required return, net claims, diluted shares, distributions and investor-currency effects. It should explain a result without hiding everything inside the word 're-rating'.

### 3.5 Rights issues and currency are not optional return adjustments

A hypothetical issuer has 100 shares at 10 and raises 200 by issuing 50 shares at 4. The theoretical ex-rights price is 8. The price decline from 10 to 8 is not a 20% economic loss to a holder who retains or sells the associated rights: each old share carries half the entitlement to a new share, worth 2 per old share in this simplified example. A subscribing holder contributes new capital; that contribution is not investment performance.

In another hypothetical, a 10% local share-price gain combined with a 10% fall in that currency against the investor's currency produces -1%, before distributions. The return database must separate these components rather than infer business deterioration from the converted quote.

Actual applications require the relevant security ratio, rights treatment, fees, taxes where modeled, dates and cash-flow convention. These examples are algebra, not estimates of historical issuer returns.

## 4. Global comparisons: the same theme has different economic transmission

### 4.1 VERBUND — hydro resource, realized prices and the hedge vintage

VERBUND's H1 hydro realization was EUR86.2/MWh, down from EUR117.2, while its hydro coefficient fell from 0.76 to 0.68. The June-end book covered 86% of planned 2026 own-hydro output at EUR87/MWh. These are realized and contract-vintage facts, not September spot exposure. [S10,S11]

The research model needs two separate paths. Hydrology changes physical availability; contract vintages determine what price is realized on that availability. A high spot price may matter little for already committed output and much more for later uncontracted years. Shortfalls can also change replacement purchases and the ability to perform under contracts.

Its June-end capitalization/debt comparison illustrates why equity price and enterprise claims cannot be interchanged. Comparing market capitalization alone with EBITDA would ignore the change in net debt. Comparing half-year earnings to an annual forecast would introduce seasonality. Even same-date reported numbers require publication-time discipline before a historical return claim.

**Potential mechanism to test:** resource normalization plus economically favorable contract replacement could lift attributable earnings, but not necessarily contemporaneously. **Countercase:** weaker water conditions, expiring favorable hedges, higher replacement costs or financing needs can offset a seemingly favorable European power narrative. R5B needs delivery-year exposure and the actual historical forecast path; the current source does not supply a September hedge certificate.

### 4.2 Neste — exceptional conversion economics can consume more cash

Neste reported Q2 comparable EBITDA of EUR1,203 million versus EUR341 million, while cash before financing was EUR164 million versus EUR226 million. It identifies a EUR842 million increase in working capital, including inventory prepared for maintenance. [S12]

The research must distinguish stronger unit conversion economics from the funding required to operate at those prices. Inventory prices, quantities, maintenance preparations and collection timing can make cash weaker during an earnings improvement. That does not prove the improvement is illusory, and adding all working capital back does not prove cash will promptly return.

The renewable-fuel model must connect feedstock, product, applicable commercial credit rights, location, utilization and investment. Regulatory sensitivity is an economic scenario input, not a political judgment; issuer comments alone are not a complete current legal interpretation. The scenario must allow customers or feedstock suppliers to capture some of the incentive's value through prices.

**Potential mechanism to test:** improved recurring spread, feedstock flexibility and operating reliability. **Countercase:** a temporary extreme margin, inventory funding or competition erodes the apparent gain. Compare the sustainable cash left after replenishing inventory and maintaining operations with the expectations that were actually available.

### 4.3 Veolia — energy-service growth is not a pure power-price bet

Veolia's energy revenue was EUR5,933 million, with 0.6% organic growth or 2.7% excluding energy prices. Its group commodity-price effects include both revenue and EBITDA impacts and have a wider scope than that energy row. [S13]

A service or concession arrangement can pass some price movements to customers while retaining efficiency, availability, volume, timing or residual market exposure. Falling pass-through revenue need not imply weaker service economics. Conversely, pass-through language is not proof that commodity changes have no margin effect.

Waste-to-energy research also needs the payment for accepting or treating waste, the useful heat/electricity rights, feedstock and operating constraints, maintenance, and the concession's duration. The issuer's group results are not a pure waste-to-energy exposure measure. No quantitative theme weight is assigned from the broad energy revenue line.

**Potential mechanism to test:** contract renewal, efficiency and profitable service-volume growth. **Countercase:** unrecovered costs, temporary service interruptions, adverse resource prices or competitive concessions. The full local contract, not a generic Energy label, determines which case applies.

### 4.4 JinkoSolar — shipment growth is not margin recovery

JinkoSolar's Q2 shipments rose 16.7% sequentially while revenue rose 0.9%; gross margin moved from 8.3% to 4.2%, and the parent-attributable loss widened. It also changed the consolidation of a U.S. business after a partial sale. The ADS ratio differs from the ordinary-share unit. [S14]

A manufacturer can deliver more equipment into a growing global market while competition, product mix, factory absorption or retained costs prevent shareholders from benefiting. Aggregate revenue divided by headline shipment growth is not necessarily a clean selling-price series because the numerator and denominator can have different product and ownership scopes.

This comparison sharpens R4's manufacturer-versus-developer distinction. Cheaper modules can improve a buyer's project economics while weakening a supplier's margins. Cost reductions create shareholder value only to the extent they exceed price concessions, warranty and replacement obligations, working capital and expansion needs.

**Potential mechanism to test:** repeatable manufacturing cost advantage and pricing stabilization on a comparable perimeter. **Countercase:** greater volume requires cash while prices fall faster than costs. Retained stakes need equity-method rather than full-consolidation treatment; a U.S. listing cannot be used as a geographic exposure proxy.

### 4.5 Kazatomprom — group growth can conceal a weaker shareholder outcome

The issuer's H1 release reports higher revenue and adjusted EBITDA but lower attributable EBITDA, owner profit and operating cash. Revenue rose from KZT660,167 million to KZT717,834 million; attributable EBITDA fell from KZT302,408 million to KZT264,840 million. The document is issuer-authored RNS carried by London South East, not the London Stock Exchange website. [S15]

The accounting and commercial model must preserve production ownership, delivery commitments, purchased material, joint-venture adjustments, currency translation and the parent's cash claim. One legal ownership percentage is not a substitute for the issuer's explicitly different attributable-earnings construction.

**Potential mechanism to test:** better delivery economics, reliable owned production and improved attributable cash after funding. **Countercase:** currency effects, purchased supply, minority claims or timing overwhelm favorable headline uranium exposure. Do not infer spot-price sensitivity by multiplying all sales volumes by a spot change. The business model and contract mix still govern.

### 4.6 NTPC — fiscal and regulatory differences must remain local

NTPC's Q1 FY2027 release refers to the quarter ended June 30, 2026. Its standalone and consolidated profit figures are separate, non-additive scopes, expressed in crore. [S16]

This is a limited comparison case, not a full station-level valuation. It establishes neither the actual tariff terms for every plant nor permission to import a U.S. utility's return-on-equity formula. Research must distinguish the commissioned asset, payment for availability, dispatch, fuel-cost recovery, working capital, receivable collections and the correct subsidiary claim using local evidence.

The next useful expansion is a station- or contract-specific cash model, not more broad labels. Until it is sourced, the tariff and local recovery fields remain unknown. Fiscal calendars, currency scaling and standalone-versus-group numbers are necessary conditions for a comparison, not the completed economic conclusion.

### 4.7 Canadian Natural — unchanged operating capital can conceal new investment

Canadian Natural's revised plan retained CAD5,990 million of operating capital while total capital moved from CAD6,880 million to CAD7,641 million, including CAD761 million of additional acquisitions. Its scope also excludes abandonment spending. Its broader shareholder-return description includes debt reduction alongside dividends and buybacks. [S17]

The long-life asset research must compare productive investment, acquisition consideration, maintenance, abandonment obligations and depletion. A higher output plan with unchanged operating capex is not proof of higher organic capital efficiency when the ownership perimeter changes.

Debt reduction may support future common-equity value and financing resilience, but it is not cash already paid to shareholders. The historical return analysis must not add debt paydown to cash distributions and then count its effect on equity valuation a second time.

**Potential mechanism to test:** durable low-replacement-cost production, improved reliability, better realized product mix and disciplined net-share reduction. **Countercase:** unrecognized closure spending, acquisition costs, financing needs or a nonrepresentative commodity price. Different Canadian product streams need their own quality and location basis; one headline oil differential is not sufficient.

## 5. What a research-grade re-rating study must actually measure

The proposed empirical unit is an economic event linked to a specific issuer/business, with a fixed forecast period and an independently recoverable pre-event knowledge set. This is a specification, not an executed predictive test.

Before each event, record the admissible operating thesis, estimates, dispersion and sample, prices and security/capital data available at that time. After the event, distinguish the immediate reported outcome, subsequent fixed-horizon revisions and the stock's measured return over predeclared windows. A revised publication must not be inserted into the earlier feature set. Separate duplicate coverage of the same disclosure from independent confirmation.

The analysis should compare several explanations rather than assume a theme effect: broad market exposure, relevant commodity or power curves, currency, interest rates, changes in net claims, operating revisions and changes in the price assigned to future cash. Residual performance is not automatically causal alpha. Overlapping company and macro events, thin trading, inconsistent timestamps and selection of only successful examples all weaken causal interpretation.

Missing individual estimates do not authorize synthetic analyst histories. Missing historical constituents do not authorize present-day basket backfilling. Missing corporate-action treatment prevents a clean share-price-return comparison. A simple ratio with an economically inappropriate denominator should be unavailable rather than precise-looking.

The target is useful intelligence even before a predictive study is accepted: explain which expectation was surpassed or weakened, what changed in the business, how much belongs to the shareholder, and which terms remain uncertain. Trade selection and sizing remain with their existing owners.

## 6. Product proposal: an expectation-to-shareholder-value dossier

The selected first capability should combine a real source-labelled estimate and reported outcome with the economic bridge and explicit limits. It should not initially promise a calibrated re-rating probability.

A useful Orsted or Equinor case would let the user move from the existing Theme Tracker into the issuer's evidence, choose a metric and fixed period, inspect the source date/method, compare actuals on the same basis, and see the operating-versus-owner reconciliation. A separate valuation section lists the quote date, share basis, net claims and assumptions. An incomplete bridge renders as incomplete; that should not erase the useful operating comparison.

The glance explanation should answer: what changed, why the business is exposed, what reached or may reach common shareholders, and what evidence would alter the interpretation. Detail should expose sample changes, stale dates, unit corrections, capital actions and contradictions. A positive theme thesis and an unattractive entry setup can remain simultaneously visible.

Reuse native evidence and correction ownership. The research record is not a new consensus warehouse, security master, scheduler or valuation authority. Data admission, source licensing, historical snapshots and product privacy belong to their current owners. Field names and observation IDs in this notebook are local research cross-references, not a parallel canonical schema.

## 7. Coverage boundary, remaining work and exact continuation

R5A has acquired selected estimates and completed the comparison/claim framework; R5B still needs independently recoverable historical observations and a complete matched valuation case. The most concrete next source action is the issuer archive behind Equinor's historical-consensus area, followed by the exact Orsted date-selection service when a lawful read path works. Do not repeat the failed Firecrawl request without a credit-state change or the same failing direct request without a connection change. An available issuer download or independent licensed historical source is a distinct research input, not a bypass of a denial.

Complete a bounded historical case before claiming earnings surprise, priced-in value or predictive return skill. Validate first-known dates, fiscal horizon, adjusted measure, panel composition, security ratio, capital events, debt/NCI/hybrid treatment and return convention. Then predeclare the evaluation and hold it out from the data used to design the method.

Global breadth remains selective, not a census. Additional local tariffs, hydro/contracted owners, carbon-capture commercial terms and differentiated regional storage mechanisms remain research obligations. Prioritize a genuinely missing payment or capital mechanism over a larger ticker list. Existing R1–R4 facts and resolved source issues are DO_NOT_REDO without a material invalidator.

R6 will reconcile the shared template and freeze the final owner-compatible product specification, build sequence, acceptance journey, rights/freshness behavior and implementation packet. Fable should receive a researched economic model and bounded build work, not an instruction to reinvent Energy research. The full handoff remains NOT_ISSUED.

## 8. Verification scope and sources

The companion verifier checks selected research invariants, arithmetic and deliberately invalid notebook mutations. It is not an application test, link audit, independent source-truth certificate, contract/legal audit or return backtest. The exact pass count and content hashes belong to its execution receipt, not an advance claim in this document. Current published facts are scoped to their named source dates; no named stock-price target, current cheap/expensive verdict or expected return is established.

Source URLs, dates and limitations are retained once in `ENERGY_R5_EXPECTATIONS_GLOBAL_MODEL_2026-09-23.json`: S01–S07 Orsted and Euroland; S08–S09 Vestas; S10–S11 VERBUND; S12 Neste; S13 Veolia; S14 JinkoSolar; S15 Kazatomprom issuer RNS via London South East; S16 NTPC; S17 Canadian Natural issuer release via Newsfile; S18–S19 Equinor; S20 Repsol. PDF references were read selectively with the relevant table pages visually inspected, not as complete audits.
