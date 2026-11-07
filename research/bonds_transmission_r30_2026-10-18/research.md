# Research dossier: useful cross-asset bond intelligence

Research date: 18 October 2026. The conclusions below distinguish reported evidence, general economic mechanisms and proposed tests. They inform the R30 design; they are not validated forecasts or current trading recommendations.

## 1. The decision the product should support

The user’s example is economically useful because it asks a connected question: if AI-related financing becomes less attractive, does Treasury demand improve, through what channel, and for how long? A dashboard of unrelated spreads and macro facts cannot answer it. The investigation must retain a question, competing explanations, the observations that distinguish them, and the next information likely to change the conclusion.

On 15 October, Reuters described AI-credit stress alongside a government-bond rally and reported a US 10-year yield decline of 8.4 bp to 5.105%. That is contemporaneous reporting, not a live 18 October quote or identified capital transfer. [R01: Reuters](https://www.reuters.com/legal/transactional/is-ai-rout-making-bonds-safe-again-2026-10-15/)

The resulting design decision is to present the Treasury response as an observation and capital substitution as a hypothesis requiring buyer evidence. The user can inspect growth repricing, substitution, safety demand and funding stress separately. A graph edge means a proposed relationship; it does not carry an invented flow volume.

## 2. Four mechanisms with different tests

| Hypothesis | Economic path to investigate | Useful confirming evidence | Evidence that would weaken it |
| --- | --- | --- | --- |
| Growth repricing | Lower expected activity/capex or financing availability can reduce the expected policy path while weighing on earnings | Matched short-rate expectations, real yields, earnings/capex revisions and independently dated financing changes | Inflation/fiscal pressure raises term premium; growth expectations remain strong |
| Capital substitution | Reduced corporate issuance or demand for AI credit can alter competition for a buyer’s capital | Cancelled/delayed issuance, price concessions, actual buyer overlap, allocations and eligible hedged alternatives | Credit-only mandates cannot switch; Treasury supply stays heavy; allocations do not move |
| Demand for safety | Investors change risk appetite or collateral/liability preferences and buy high-quality sovereign exposure | Observed fund/holder allocations, collateral demand and matched duration/currency preferences | Selling is confined to one issuer or investors prefer cash rather than duration |
| Funding stress | Margin, collateral or financing needs force asset sales and change demand for cash | Repo/collateral pressure, deteriorating depth, dealer constraints and concurrent forced selling evidence | Funding and market functioning remain orderly despite wider credit spreads |

These are not four independent signal votes. The same yield or spread observation can be relevant to several explanations. Supporting a growth channel does not automatically prove substitution; stable funding is meaningful counterevidence to a liquidity-squeeze interpretation.

The IMF’s October financial-stability summary discusses AI-related profitability, leverage and concentration alongside broader sovereign and nonbank vulnerabilities. Only the landing-page summary was reviewed. Its role here is to keep competing system channels in scope, not to supply a numerical probability. [R04: IMF](https://www.imf.org/en/Publications/GFSR/Issues/2026/10/13/global-financial-stability-report-october-2026)

## 3. Credit repricing, financing access and liquidity are different

CDS and cash-bond pricing react to risk compensation, liquidity, hedging demand and contract structure. A company’s ability to meet an obligation depends on the relevant legal entity, cash availability, maturity or reset date, collateral, committed funding and operating cash flow. Secondary-price weakness may precede financing difficulty, but it is not itself a dated refinancing event.

New York Fed research on corporate market distress motivates separating primary and secondary market functioning from a spread-level reading. R30 therefore has three distinct overview readings: credit pricing, access to capital, and market plumbing. No current CMDI observation was established in this review. [R10: Federal Reserve Bank of New York](https://www.newyorkfed.org/research/staff_reports/sr957)

The issuer case uses CoreWeave’s reported 30 June 2026 balance-sheet snapshot: cash/equivalents of $5.524 billion, current recourse debt of $6.235 billion and current non-recourse debt of $1.278 billion; current restricted cash of $0.873 billion is separate in the drawer. These are dated accounting classifications, not exact maturity dates or a current funding-gap calculation. [R03: CoreWeave Investor Relations](https://investors.coreweave.com/news/news-details/2026/CoreWeave-Reports-Strong-Second-Quarter-2026-Results/)

The implementation consequence is a financing inspector that maps obligations and resources separately, with a visible roll-forward requirement. It should show when market repricing actually affects interest expense: contractual reset, new borrowing, refinancing or an amendment. The $10 million sensitivity for $1 billion repriced 100 bp higher is arithmetic, not an issuer forecast.

Relationships also require types. BIS discussion of circular AI relationships identifies overlap between investment and commercial links and the resulting opacity. A supplier/customer connection does not automatically create a lender exposure or guarantee. R30 separates lenders/lessors, operating relationships and comparable credit peers. [R05: BIS](https://www.bis.org/publications/bulletin-137-circular-relationships-among-ai-firms)

## 4. Identify the buyer before comparing returns

A raw yield ranking is an incomplete capital-allocation model. A pension, reserve manager, money fund, credit fund, insurer and leveraged relative-value account can face different currencies, durations, permitted instruments, collateral needs and liquidity constraints. The relevant choice is the eligible alternative for the marginal buyer.

Federal Reserve analysis shows that the composition of Treasury buyers differs across periods of Federal Reserve balance-sheet reduction. Aggregate categories and quarterly holdings are limited evidence about individual current transactions; the household category should not be read literally as retail-only demand. [R07: Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/who-buys-treasuries-when-the-fed-reduces-its-holdings-20240614.html)

The R30 comparison therefore declares a JPY-based investment-grade mandate and duration range. It retains Treasury, Bund and JGB duration differences; corporate credit has a separate risk interpretation; the shorter-duration AI basket is outside the selected mandate. An ineligible high-yielding asset does not win the comparison.

The hedged comparison is deliberately modest: yield minus current annualized hedge cost. A rolling three-month hedge does not lock costs over a multi-year holding period. The Treasury/JGB fixture differs by only five basis points, and a 25 bp hedge-cost change reverses the ordering. The interface lets users inspect that sensitivity without implying a robust arbitrage.

Issuer funding is a separate perspective. Reuters’ corrected report concerned governments and state entities considering non-dollar issuance amid AI-related capital competition. It did not establish sovereign wealth fund portfolio reallocations. R30’s issuer view holds the borrower and resulting base-currency liability constant when comparing issue currencies. [R02: Reuters](https://www.reuters.com/business/finance/sovereign-funds-turn-non-dollar-bonds-amid-ai-driven-liquidity-crunch-citi-2026-10-15/)

## 5. Make “liquidity flows” measurable

The interface should ask which quantity is moving, on which clock, and through which balance sheet:

- **Primary supply:** gross issuance, redemptions, net issuance, currency and settlement dates.
- **Investor holdings/allocations:** observed changes, valuation adjustments, fund flows, eligible universe and reporting lag.
- **Funding liquidity:** repo, margins, collateral availability, haircuts, financing terms and balance-sheet capacity.
- **Market liquidity:** depth, bid/ask, price impact and execution quality.
- **Monetary-system liquidity:** reserves, money-fund allocation and central-bank facilities, with the location and distribution of balances.
- **Cross-currency financing:** matched swaps/forwards and collateral/cash settlement, distinct from an FX spot-price change.

These categories are related but cannot be substituted for one another. A net-issuance bar chart measures supply, not where its proceeds came from. A rising bond price is not an investor-flow estimate. Holdings changes require adjustment and provenance before being displayed as flows.

Federal Reserve research on repo and the balance sheet describes connections among issuance, dealer inventories, money funds, reserves and related funding conditions. This motivates a linked funding check rather than one universal “liquidity” badge. The R30 overview’s qualitative status now names the relevant conditions instead of displaying a decorative quantitative sparkline. [R06: Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/repo-markets-and-the-feds-balance-sheet-implications-for-monetary-policy-implementation-20260826.html)

The proposed advanced implementation can expose these balance-sheet channels within I03. A measured flow visual requires an explicit amount, unit, interval, source, reconciliation and scope. Until those exist, the causal map uses thin dashed relationships and clearly identified missing evidence.

## 6. A Treasury bid can fail

The historical work must include episodes in which an initial safe-asset response reversed. The Federal Reserve’s June 2020 report describes an initial fall in long Treasury yields followed by selling pressure and impaired market functioning during the March disruption. That supports testing a cash-demand counterpath. It does not establish that the current episode is identical. [R13: Federal Reserve](https://www.federalreserve.gov/monetarypolicy/2020-06-mpr-part2.htm)

Collateral-reuse research provides separate evidence about dealer intermediation and Treasury-market functioning during that disruption. Its relevance is the financing mechanism, not a universal claim that credit spread widening necessarily causes Treasury selling. [R11: Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/treasury-market-functioning-during-the-covid-19-outbreak-evidence-from-collateral-re-use-20201204.html)

The causal story must remain segment-specific. A later Federal Reserve study of Treasury futures finds a major role for asset-manager liquidity consumption and does not find basis traders to be important drivers of the futures disruption in its analysis. R30 therefore does not describe all March 2020 Treasury stress as a single basis-trade unwind. [R12: Federal Reserve](https://www.federalreserve.gov/econres/feds/market-liquidity-in-treasury-futures-market-during-march-2020.htm)

Bank of England research on the 2022 gilt crisis connects gilt, repo and swap transactions with LDI collateral pressure and forced sales. It is a useful mechanism reference with different institutions, liabilities and market structure. The episode is displayed as a different-market comparison, not a high-confidence analog match. [R09: Bank of England](https://www.bankofengland.co.uk/working-paper/2023/an-anatomy-of-the-2022-gilt-market-crisis)

Recent BIS market discussion also points to dispersion in AI-related profitability and exposure. The product should retain issuer and balance-sheet differences instead of treating every AI-linked security as one homogeneous risk basket. [R08: BIS](https://www.bis.org/publications/qr-202609/yields-climb-yet-risk-appetite-holds-firm)

## 7. Combine macro and technical structure without duplicating evidence

Nominal yields can fall because the expected short-rate component declines even while term premium rises. NY Fed discussion of term premia explains that this decomposition is model-based; components are not directly observed market facts. R30 exposes the decomposition and its calculation/model provenance. [R14: Federal Reserve Bank of New York](https://libertystreeteconomics.newyorkfed.org/2014/05/treasury-term-premia-1961-present/)

Technical structure can make a macro view testable. It should specify an instrument, lookback, volatility context, close convention, confirmation boundary and invalidation boundary. A close-confirmed break, a failed retest or a yield move unusually large for the prevailing volatility can change the action priority. They do not by themselves identify why the move happened.

For future empirical work, useful candidate families include curve level/slope/curvature, rate-path versus premium changes, close-confirmed trend and retest structure, volatility-normalized distance, peer spread breadth, new-issue reception, funding function and equity earnings revisions. Every feature needs an ex-ante definition and publication clock. A Treasury yield, its price approximation and an indicator computed from that price are related descendants, not independent confirmations.

Any claim of incremental predictive content should compare these contextual features with simpler price-only and rates-only baselines. News or financing information received after the market move cannot be treated as a pre-emptive signal for that same move.

## 8. Faster decisions through change and next-check intelligence

R30 increases analytical speed by retaining state rather than multiplying cards. A saved case records the earlier view; the review screen emphasizes changed breadth, unresolved financing evidence, the next threshold and the next source update. This lets the user answer: what changed, does it matter to the hypothesis, and what should I inspect next?

The catalyst drawer attaches each scheduled check to an economic question. An auction tests demand and concession; a financing update tests contractual access; a peer close tests breadth; a funding release tests whether the risk is spreading through market plumbing. Calendar certainty is visible, and unknown dates stay unknown.

Continuation is expressed conditionally. The design distinguishes duration relief with orderly funding, a fading rate tailwind under inflation/supply pressure, and a cash-demand regime in which bonds can also sell. Each path has a useful confirming test, an invalidator and a horizon. A monitor follows that unresolved question using explicit clocks and precedence.

A probability becomes appropriate only after the exact target and horizon are qualified on point-in-time data with out-of-time calibration, relevant baselines, dependence handling and abstention rules. The detailed requirements are in [data_contract.md](data_contract.md). No R30 likelihood or historical forecast performance was estimated in this task.

## Source register and review limits

- **R01 · Reuters · 2026-10-15.** [Is the AI rout making bonds safe again?](https://www.reuters.com/legal/transactional/is-ai-rout-making-bonds-safe-again-2026-10-15/). Reviewed: Article. Use: Contemporaneous reported AI-credit/government-bond repricing; not causal or live-quote proof.
- **R02 · Reuters · 2026-10-15.** [Governments and state entities consider non-dollar financing amid AI-driven capital competition](https://www.reuters.com/business/finance/sovereign-funds-turn-non-dollar-bonds-amid-ai-driven-liquidity-crunch-citi-2026-10-15/). Reviewed: Corrected article. Use: Issuer-currency funding question; corrected identity is governments/state entities, not sovereign wealth fund investment flows.
- **R03 · CoreWeave Investor Relations · 2026-08-11.** [CoreWeave Reports Strong Second Quarter 2026 Results](https://investors.coreweave.com/news/news-details/2026/CoreWeave-Reports-Strong-Second-Quarter-2026-Results/). Reviewed: Release and balance-sheet table. Use: Dated issuer-financing snapshot; no current solvency/runway inference.
- **R04 · IMF · 2026-10-13.** [Global Financial Stability Report, October 2026](https://www.imf.org/en/Publications/GFSR/Issues/2026/10/13/global-financial-stability-report-october-2026). Reviewed: Landing-page summary only; chapter PDF not retrieved. Use: AI-related concentration/leverage and wider financial-stability counterchannels.
- **R05 · BIS · 2026-10-01.** [Circular relationships among AI firms](https://www.bis.org/publications/bulletin-137-circular-relationships-among-ai-firms). Reviewed: Landing-page key takeaways; not full PDF. Use: Typed economic relationships and opacity; investment/supply-chain connections are not automatically guarantees.
- **R06 · Federal Reserve · 2026-08-26.** [Repo markets and the Fed’s balance sheet: implications for monetary policy implementation](https://www.federalreserve.gov/econres/notes/feds-notes/repo-markets-and-the-feds-balance-sheet-implications-for-monetary-policy-implementation-20260826.html). Reviewed: FEDS Note. Use: Issuance, dealer balance sheets, money funds, reserves and funding distribution.
- **R07 · Federal Reserve · 2024-06-14.** [Who buys Treasuries when the Fed reduces its holdings?](https://www.federalreserve.gov/econres/notes/feds-notes/who-buys-treasuries-when-the-fed-reduces-its-holdings-20240614.html). Reviewed: FEDS Note. Use: Marginal-buyer composition and frequency/category limits.
- **R08 · BIS · 2026-09.** [Yields climb, yet risk appetite holds firm](https://www.bis.org/publications/qr-202609/yields-climb-yet-risk-appetite-holds-firm). Reviewed: Selected market discussion excerpt. Use: Dispersion and counterevidence; do not treat AI-related exposures as homogeneous.
- **R09 · Bank of England · 2023-03-31.** [An anatomy of the 2022 gilt market crisis](https://www.bankofengland.co.uk/working-paper/2023/an-anatomy-of-the-2022-gilt-market-crisis). Reviewed: Staff Working Paper 1019 abstract. Use: Gilt/repo/swap and LDI collateral mechanisms; distinct institutional regime.
- **R10 · Federal Reserve Bank of New York · 2021-01.** [Corporate Bond Market Distress](https://www.newyorkfed.org/research/staff_reports/sr957). Reviewed: Staff Report 957 research page. Use: Market functioning across primary and secondary markets is distinct from spread level.
- **R11 · Federal Reserve · 2020-12-04.** [Treasury market functioning during the COVID-19 outbreak: evidence from collateral re-use](https://www.federalreserve.gov/econres/notes/feds-notes/treasury-market-functioning-during-the-covid-19-outbreak-evidence-from-collateral-re-use-20201204.html). Reviewed: FEDS Note. Use: Intermediation and collateral evidence during March 2020.
- **R12 · Federal Reserve · 2025-05.** [Market liquidity in the Treasury futures market during March 2020](https://www.federalreserve.gov/econres/feds/market-liquidity-in-treasury-futures-market-during-march-2020.htm). Reviewed: Research abstract. Use: Contrary segment-specific evidence against a blanket basis-trader explanation.
- **R13 · Federal Reserve · 2020-06.** [Monetary Policy Report, Part 2](https://www.federalreserve.gov/monetarypolicy/2020-06-mpr-part2.htm). Reviewed: Treasury market-functioning and policy-response discussion. Use: Initial yield decline followed by selling pressure and market dysfunction; no single-cause attribution.
- **R14 · Federal Reserve Bank of New York · 2014-05.** [Treasury Term Premia: 1961–Present](https://libertystreeteconomics.newyorkfed.org/2014/05/treasury-term-premia-1961-present/). Reviewed: Liberty Street Economics article. Use: Expected-short-rate/term-premium decomposition is model estimated.

The source register identifies what was actually reviewed. A landing page or abstract is not presented as a full-paper replication. The current design’s numerical market paths and history fingerprints are synthetic and visibly distinguished from these research references.
