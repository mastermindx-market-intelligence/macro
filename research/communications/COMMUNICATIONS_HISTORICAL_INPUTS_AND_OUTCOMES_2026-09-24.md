# Communications — Historical Inputs and Financial-Outcome Pilot

**Research date:** 2026-09-24. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794. **Status:** original research and a fixed, retrospective diagnostic. Not native data admission, a production model, independent financial audit, or a trading backtest.

The Chairman will manually deliver the eventual bundle to a **new Fable session later**. Sol retains this research. Semiconductor work is an upstream foundation, not this operation's recipient. No dispatch, placement, worker notice or watcher is part of this phase.

## 1. The material step

Phase 15 described conditional business-to-earnings mechanisms. This phase establishes which inputs can actually be retrieved and tests a small historical sample instead of assigning undisclosed coefficients.

The sample has **16 income observations** spanning **12 distinct company/quarter combinations**: four companies, Q2 2023–2025, with each 2024 observation deliberately retained in two source vintages. It has **12 cash-flow observations** sufficient to calculate Q2 2024 and Q2 2025 cash measures. There are twelve issuer documents and one SEC methodology reference. The 2023 observations are comparisons printed in 2024 releases, **not captured original 2023 releases**.

All four companies' reported operating income increased from Q2 2024 to Q2 2025. The selected post-investment cash measure increased for The Trade Desk but fell for Meta, Alphabet and Magnite. Thus the choice of outcome is materially important before any forecasting coefficient is fitted.

A second result is a real falsifier for blindly extrapolating a historical earnings slope. Magnite's 2023-to-2024 change implies about **$7.87 of operating-profit improvement per $1 of additional revenue**. A fixed extrapolation using that slope forecasts approximately $96.457 million of 2025 Q2 operating income; the selected reported result is $21.959 million. The earlier improvement includes a $74.703 million decline in depreciation and amortization. The slope is not a measured marginal contribution rate. [MG24,MG25]

This is an economic and measurement finding, not evidence that a stock was overvalued or that a different model is predictively superior.

## 2. Exact design and what “historical” means here

We selected the four existing A1 businesses, not winners chosen by this pilot. The annual Q2 comparison reduces one obvious season mismatch but does not control acquisitions, tax timing, cost allocation, product transitions or other structural change. Four surviving, already-selected companies are not representative of Communications.

For each firm:

- The source-date ceiling is the printed date of its Q2 2024 release.
- Inputs are the 2023 comparative and 2024 current consolidated revenue/operating income in that release.
- The target is consolidated Q2 2025 revenue and operating income from the 2025 Q2 release.
- Cash analysis is a separate 2024-versus-2025 outcome diagnostic, not an input to the 2024-origin revenue forecast.
- All nominal values retain the issuer's original printed currency scale. There is no cross-company sum of gross and net revenues.

The method was designed **now, after the outcomes were available**. It is not preregistered, a recovered historical recommendation, or an actual 2024 forecasting run. The original release pages are retrievable, but we have not retained historical native source bytes, proved their original online availability, or censused subsequent edits. A printed publication day supplies a bounded date selector, not intraday or native system-replay proof. This limitation remains even when the arithmetic is exact.

No 2026 financial example from the previous phases enters this experiment. The sample does not reopen the unresolved final-pre-results guidance-history search.

## 3. Available inputs and the questions they can answer

| Business role | Public evidence available in the selected sources | Useful initial outcome | Still not identified |
|---|---|---|---|
| Meta / audience monetization | Consolidated and business revenue, price/impression changes, reported operating expenses, operating cash, capex and finance-lease cash | Later reported advertising/issuer revenue, operating margin and investment-adjusted cash considered separately | Absolute eligible impressions, format-level marginal costs, counterfactual retention, AI-only revenue and infrastructure returns |
| Alphabet / discovery | Search, YouTube and Network revenue; TAC; segment and consolidated operating results; cash capex | Category growth and consolidated profit/cash, with separate reporting-scope checks | Search-only profit, query-level incremental cost, displaced monetization and AI-serving return |
| The Trade Desk / buying intermediation | Revenue, named operating expenses, SBC, quarterly income and cumulative cash statements | Comparable issuer revenue, operating income and cash after identified investment | Quarterly customer-spend cohorts, spend retention, workload elasticity and a complete gross-spend/take-rate panel |
| Magnite / selling intermediation | GAAP revenue/profit, contribution ex-TAC and channels, D&A, buyer/seller working-capital lines and cumulative cash | Contribution growth, GAAP operating results and settlement-sensitive cash as different outcomes | CTV-only operating profit, contract-specific unit economics, durable collection behavior and a causal growth coefficient |

Source discovery is not production access, permission to redistribute a complete paid product, or acceptance of a source's measurement definition. No new provider, paid subscription or connector was purchased.

### Why one generic fundamentals download is insufficient

The SEC's XBRL APIs aggregate non-custom-taxonomy facts applying to the entire filing entity. Company-concept responses separate units. Those APIs can help locate standardized issuer totals; they do not, by themselves, supply this research's customized business measures or segment-level sensitivities. The Frames API selects last-filed facts closest to calendar intervals, so a current frame is not automatically an as-of historical feature panel. Exact periods and filing identities must survive selection. [SECAPI]

Future collection should extend the existing financial/source owners where needed. This study creates no second company-facts store, historical selector, filing crawler, evaluation system or scheduler. The offline JSON and script are fixed research artifacts only.

## 4. The actual income sample

Amounts below are **USD millions** for readability; The Trade Desk and Magnite source amounts are USD thousands and are divided by 1,000 in this table only. The JSON retains the original scales. Operating income is reported GAAP, unaudited.

| Company | Q2 2023 revenue / operating income | Q2 2024 revenue / operating income | Q2 2025 revenue / operating income |
|---|---:|---:|---:|
| Meta | 31,999 / 9,392 | 39,071 / 14,847 | 47,516 / 20,441 |
| Alphabet | 74,604 / 21,838 | 84,742 / 27,425 | 96,428 / 31,271 |
| The Trade Desk | 464.254 / 41.673 | 584.550 / 94.720 | 694.039 / 116.777 |
| Magnite | 152.543 / −71.795 | 162.880 / 9.574 | 173.332 / 21.959 |

Sources: [M24,M25,G24,G25,T24,T25,MG24,MG25].

The 2024 revenue, total operating-cost and operating-income figures agree between the selected 2024 and 2025 releases for all four firms. That is a check of these **three printed consolidated values**, not certification that every line, definition or disclosure is unchanged. The two editions remain separate rows. A later comparative is not backdated into the earlier source window.

### Cost-perimeter warning

Alphabet's 2024 release describes AI model-development teams moving from Google Services to Alphabet-level activities prospectively from Q2 2024. A segment-margin slope around that change would confound operating performance with cost-allocation changes. The pilot uses consolidated results and retains the segment issue as an explicit warning. It does not infer a numerical recast from the consolidated totals. [G24]

## 5. Cash must have a real quarter and a named definition

Meta and Alphabet print quarterly cash figures. The selected TTD and Magnite Q2 releases print **six-month** cash-flow statements. Their Q2 values below are H1 minus Q1, using the original same-year first-quarter release rather than a later comparative. Each subtraction retains both source references, the January start, June/March endpoints, scope, unit and signed-flow meaning. [T124,T125,T24,T25,MG124,MG125,MG24,MG25]

A half-year cash figure is not comparable to a three-month profit figure merely because both appear in a Q2 earnings release. A negative Q1 CFO remains negative when subtracted; clamping it to zero would materially alter Magnite's quarter.

| Company | Q2 2024 CFO | Q2 2025 CFO | Selected post-investment cash, 2024 | Selected post-investment cash, 2025 |
|---|---:|---:|---:|---:|
| Meta | 19,370 | 25,561 | 10,898 | 8,549 |
| Alphabet | 26,640 | 27,747 | 13,454 | 5,301 |
| The Trade Desk | 81.259 | 165.013 | 56.678 | 116.695 |
| Magnite | 89.567 | 18.528 | 76.263 | 2.471 |

All table amounts are USD millions. Sources and periodization are as above, plus [M24,M25,G24,G25].

**Definitions are not standardized across peers.** Meta's selected measure subtracts property/equipment cash purchases and finance-lease principal from CFO. Alphabet subtracts property/equipment cash purchases. TTD and Magnite are explicitly labeled **research subtotals** subtracting cash PP&E and capitalized software; they are not newly certified issuer-defined FCF or comprehensive distributable equity cash. Acquisitions, compensation, debt, tax timing, contingent commitments and replacement economics still require their own analysis.

### Magnite: both profit and the headline cash label can improve while statement cash falls

Magnite's headline “operating cash flow” is adjusted EBITDA less capital expenditure, not statement-of-cash-flows CFO. Its definition is preserved rather than replaced. The selected quarterly GAAP CFO is derived from cumulative statements: 2024 H1 CFO 29.156 less Q1 −60.411 gives 89.567; 2025 H1 21.089 less Q1 2.561 gives 18.528, all USD millions. [MG24,MG25,MG124,MG125]

The receivable and payable/accrued-expense cash lines together move from +50.471 million in Q2 2024 to −31.457 million in Q2 2025, a −81.928 million swing. Total Q2 CFO falls 71.039 million; the remainder of the cash reconciliation offsets 10.889 million. This is an accounting partition, not proof of a single causal explanation, credit deterioration or a normalized cash forecast. The same buyer/seller settlement cycle can make a single quarter unrepresentative. Do not subtract these working-capital lines again from CFO that already includes them.

## 6. Four retrospective baseline tests, without a fitted model

Let `R23,O23,R24,O24` be the revenue and operating income printed in the Q2 2024 source; the target is `R25,O25`. All inputs use matched company, consolidated scope and printed units.

**Revenue baseline A:** `Rhat = R24` (repeat last comparable level).
**Revenue baseline B:** `Rhat = R24² / R23` (repeat the last year-over-year growth rate).

Given revenue baseline B:

**Frozen-margin profit:** `Ohat_margin = Rhat × O24/R24`.
**Historical-slope profit:** `Ohat_slope = O24 + (Rhat−R24) × (O24−O23)/(R24−R23)`.

No coefficient is estimated from the 2025 target. No exceptional company is removed, no slope is clipped after seeing the result, and no best-performing rule is selected for deployment. These equations test two tempting shortcuts, not the complete role-specific models from Phase15.

### Results

Operating-income amounts below are USD millions. Errors are `actual − prediction`; the error columns divide by **target revenue**, so they are percentage points of revenue, not misleading percentage errors on small or negative earnings.

| Company | Actual Q2 2025 operating income | Frozen-margin prediction | Historical-slope prediction | Margin-model error / target revenue | Slope-model error / target revenue |
|---|---:|---:|---:|---:|---:|
| Meta | 20,441.000 | 18,128.289 | 21,507.593 | +4.867 pp | −2.245 pp |
| Alphabet | 31,271.000 | 31,151.806 | 33,771.222 | +0.124 pp | −2.593 pp |
| The Trade Desk | 116.777 | 119.264 | 161.512 | −0.358 pp | −6.446 pp |
| Magnite | 21.959 | 10.223 | 96.457 | +6.771 pp | −42.980 pp |

These are calculations from the income table, not issuer forecasts, consensus estimates or recorded historical model calls.

The repeated-growth revenue baseline is relatively close for Meta, Alphabet and Magnite in this selected window, but overstates The Trade Desk's revenue. Even close revenue does not establish a correct profit projection. The historical-slope method overshoots all four selected profit outcomes and is closer than frozen margin only for Meta. Four inspected cases, chosen and analyzed after the fact, cannot establish general superiority or a dependable forecast advantage.

### Why Magnite's slope is especially misleading

Reported 2023-to-2024 operating income improves by 81.369 million on revenue growth of 10.337 million. Total D&A falls by 74.703 million, about 91.8% of that net profit improvement. A historical ratio therefore incorporates a very large change in accounting expense; projecting it as the profit on additional future sales is not justified. The reduction is an accounting component, not an independent causal attribution or evidence of the same-period cash return. [MG24]

A model with causal ambitions would need to separate ongoing amortization schedules, remaining assets, other cost changes and business economics. Adding back all D&A is not automatically the correct remedy: replacement and development investment still have economic costs. No normalized Magnite coefficient is produced here.

### Revenue error versus realized margin error

The fixed replay verifies this exact decomposition for the frozen-margin method:

`O25 − Ohat_margin = margin24 × (R25 − Rhat) + (O25 − margin24 × R25)`.

The second term explains the observed margin difference using **realized 2025 revenue and profit**. It must never enter a supposedly 2024-origin forecast as a feature. This is a post-outcome diagnosis only.

## 7. Outcome definitions before model fitting

The first operational tests should specify a subject, target period and measurement basis rather than seek one universal “good result.”

1. **Revenue or issuer-defined contribution:** predict the next matching period in its native business scope. Do not mix net intermediary revenue, contribution ex-TAC and gross advertising expenditure into a peer total.
2. **Operating profitability:** use absolute operating income and margin change; preserve signed results. A loss turning into profit does not require a meaningful percentage-growth denominator.
3. **Cash and investment:** forecast named components and cumulative windows where sensible; distinguish CFO, required investment and the issuer's FCF convention. Reconcile quarterization and current working-capital timing before interpreting a turn.
4. **Shareholder outcomes:** only after identities, diluted claims, original-vintage expectations, prices, corporate actions and total returns are qualified. This pilot reaches none of those gates.

For an expanded prospective evaluation, use the existing evaluation owner, retain a frozen origin dataset and model identity before outcomes arrive, and record abstentions and missing cases. Compare predeclared simple baselines, then test whether role-specific features add information. Fit preprocessing on the training window only. Overlapping quarterly targets and issuer/event dependence require appropriate validation, not shuffled row splits.

The four-company annual-quarter sample is too small to estimate causal elasticities, tune many predictors, establish confidence intervals or validate regime-specific stock picking. It is sufficient to expose measurement failures and to prioritize the data needed for a credible next experiment.

## 8. Concrete acquisition and qualification map

| Needed input | Existing-owner route to qualify | Qualification evidence before a model may use it |
|---|---|---|
| Consolidated original-vintage income/cash | Existing Company/Earnings/financial intake over issuer filings and releases | Exact report and filing identity, statement period, unit, source/recorded clocks, preserved correction versions |
| Advertising and channel KPIs | Original release tables/notes through the existing source and GMI assertion owners | Business population, denominator, definition history, comparable period and review of customized metrics |
| Q2/Q4 cash derived from cumulative statements | Existing reviewed financial comparison layer | Matched YTD prefixes, distinct source references, consistent basis, exact subtraction and any restatement reconciliation |
| Financial claims and business-to-security route | Existing Data OS/company identity owner | Actual issuer/security rights and valid-time binding; a research label or CIK text is not a native join |
| Forward guidance / analyst expectations | Existing guidance-history and authorized expectation owners | Question kind, target period, edition, source coverage and vintage; company guide is not consensus |
| Causal AI, cohort retention or marginal processing cost | Qualified new evidence within existing owners, not invented from quarterly totals | Actual appropriate cohorts, experiments, contractual data or a defensible identification design |
| Historical returns and decision outcomes | Existing price/corporate-action and evaluation owners | Correct security, executable time boundary, total-return definition, costs and a frozen decision record |

These are integration obligations, not newly created services or evidence that every owner currently has every required field. The last inspected shared #7870 snapshot remains the one in the cumulative checkpoint; no shared status was polled or source modified in this phase.

The immediate four-company A1 descriptive workflow does not depend on solving the entire forecasting problem. This study supplies sharper interpretations and realistic historical counterexamples while keeping predictive and trading claims separate.

## 9. Verification and limits

The standalone standard-library replay reads the fixed accompanying JSON and writes only an explicitly selected local result file. No native owner, model, network, price feed, private store or account is accessed.

Twenty-four tests cover the fixed roster/record counts, original-versus-later comparative selection, cash periodization and signs, selected-vintage agreement, observed profit/cash directions, the historical-slope counterexample, exact error decomposition, missing-company preservation, invalid unit/currency/source/period variants, and the absence of authority. A coordinated false transcription that preserves arithmetic intentionally passes one test: numerical consistency is not source authenticity.

The temporary empty-result baseline produced nineteen assertion failures and four missing-result errors across the same twenty-four tests; it was not a production bug or an environmental red test. The completed fixed replay passes all twenty-four. This is evidence about the research checker, not model validation or application correctness.

The JSON stores unknown native identity/retention/availability evidence as unknown rather than fabricating it. Selected Alphabet tables were visually inspected in the issuer PDFs. No full document corpus, private data or font asset is exported. No historical recommendation, current valuation, stock return, live source admission, browser/watchlist proof, CI qualification or independent review is claimed.

A local-only export initially failed because the newly created scratch directory lacked group write permission for the Python runtime. The target was confirmed absent; permissions on that new scratch directory were corrected and the same target was written successfully. This is separate from the earlier platform-denied host identity action, which was not retried, rephrased, moved or delegated.

## 10. Source register

Sources are official issuer material except the official SEC methodology page. Dates are the documents' printed release days. Review covers the selected tables and clauses, not a complete financial audit, historical revision census or legal redistribution ruling.

**M24 — Meta, 2024-07-31.** Q2 consolidated income statement, quarterly cash-flow statement and free-cash-flow reconciliation. https://investor.atmeta.com/investor-news/press-release-details/2024/Meta-Reports-Second-Quarter-2024-Results/default.aspx

**M25 — Meta, 2025-07-30.** Q2 consolidated income statement, quarterly cash-flow statement and free-cash-flow reconciliation. https://investor.atmeta.com/investor-news/press-release-details/2025/Meta-Reports-Second-Quarter-2025-Results/

**G24 — Alphabet, 2024-07-23.** Printed p2 reporting change; p5 income statement; p6 three-month cash flow. https://s206.q4cdn.com/479360582/files/doc_financials/2024/q2/2024q2-alphabet-earnings-release.pdf

**G25 — Alphabet, 2025-07-23.** Printed p2 categories; p5 income statement; p6 three-month cash flow. https://s206.q4cdn.com/479360582/files/doc_financials/2025/q2/2025q2-alphabet-earnings-release.pdf

**T24 — The Trade Desk, 2024-08-08.** Three-month consolidated operations; SIX-month cash-flow statement. https://investors.thetradedesk.com/news-and-events/news/news-details/2024/The-Trade-Desk-Reports-Second-Quarter-2024-Financial-Results/default.aspx

**T25 — The Trade Desk, 2025-08-07.** Three-month consolidated operations; SIX-month cash-flow statement. https://investors.thetradedesk.com/news-and-events/news/news-details/2025/The-Trade-Desk-Reports-Second-Quarter-2025-Financial-Results/default.aspx

**T124 — The Trade Desk, 2024-05-08.** Three-month cash-flow statement: operating cash, property/equipment, software. https://investors.thetradedesk.com/news-and-events/news/news-details/2024/The-Trade-Desk-Reports-First-Quarter-2024-Financial-Results/default.aspx

**T125 — The Trade Desk, 2025-05-08.** Three-month cash-flow statement: operating cash, property/equipment, software. https://investors.thetradedesk.com/news-and-events/news/news-details/2025/The-Trade-Desk-Reports-First-Quarter-2025-Financial-Results/default.aspx

**MG24 — Magnite, 2024-08-07.** Three-month operations and D&A table; SIX-month cash flow; non-GAAP contribution reconciliation. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-second-quarter-2024-results

**MG25 — Magnite, 2025-08-06.** Three-month operations and D&A; SIX-month cash flow; contribution reconciliation. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-second-quarter-2025-results

**MG124 — Magnite, 2024-05-08.** Three-month cash flow: CFO, investment, receivable and payable/accrued-expense changes. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-first-quarter-2024-results

**MG125 — Magnite, 2025-05-07.** Three-month cash flow: CFO, investment, receivable and payable/accrued-expense changes. https://investor.magnite.com/news-releases/news-release-details/magnite-reports-first-quarter-2025-results

**SECAPI — SEC, EDGAR Application Programming Interfaces.** XBRL Data APIs, company-concept/company-facts and Frames sections. https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## 11. Continuation and unchanged execution scope

The current consolidated eight-task plan and proof companion remain the two execution readings. This pilot adds no sixty-first release requirement and does not recreate the shared GMI/financial/evaluation layers. The sixty CRV obligations, wider sector research and later manual Fable delivery remain unchanged.

Next: convert the input/outcome findings into the existing final readiness assessment: separate facts needed for the descriptive A1 release from the additional data needed for forecasting; retain the historical counterexamples in its review evidence. Address remaining breadth and independent-review obligations without another equivalent archive sweep or another rewrite of the consolidated plan. No deployment, source-custody transfer or unattended continuation is implied.

Protected Skillpack: Mastermind `605cd056c3463c992d85ba76dbcc90fbb758da75`, schema/version 1.0.1, bootstrap 1. Entering Macro research head `88cae8f64f8578e085658c9025c02e52e378d09b`. Original research carrier and branch unchanged.
