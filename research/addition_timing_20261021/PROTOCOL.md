# Does waiting for a recovery signal improve monthly additions?

Frozen continuation protocol, 2026-10-21. This study follows accepted Macro PR #9989 (merge `56a05ecb5146a01119bb04ddb6b8f40e82c6cd57`). The histories, selected signal, and earlier outcomes have been inspected. This registration limits new discretion; it does not create an untouched holdout. No live signal, ranking, sizing, broker action, or production data change is authorized by this research.

## Decision and falsifiers

Test a practical unresolved claim: can a fixed monthly contribution acquire a more useful ownership position by waiting for a frozen recovery signal? Compare the same external funding, assets, costs, and subsequent ownership. Primary comparison is SPY signal waiting versus immediate monthly purchase. A blind month-end purchase is one prespecified mechanism control. Failure to beat immediate purchase rejects the practical waiting contract in this history; failure to beat blind month-end weakens attribution to the signal.

No oscillator parameters, event thresholds, calendar phases, entry filters, waiting windows, stops, or exits will be optimized. A positive contribution outcome does not establish a durable low. This experiment concerns additions to an ownership position, not identifying the final low or managing exits.

## Inputs and separate universes

Reuse the verified current-vintage price snapshot through **2026-10-08**, and the complete sector RSI30-recovery capital roster published in PR #9989. The inherited roster is 108 rows from the 12 instruments XLK, XLF, XLE, XLI, XLY, XLP, XLU, XLV, XLB, XLRE, XLC, SOXX. Use every row, irrespective of the previous policy's accepted/occupied status. Do not select only events with complete forward outcomes. Preserve inherited signal readiness and cooldown. Signal index uses the original SPY calendar beginning 2010-01-04. Execute only at the next observed session open. Deduplicate simultaneous nominations into one execution-date opportunity while retaining the nominating names. A final-session signal with no observed next open is not executable and is separately counted.

All four purchase baskets use this **same calendar** and the same evaluation start, 2020-01-01:

| Basket | Role | Fixed allocation of each contribution |
|---|---|---|
| SPY | Primary | 100% SPY |
| SECTOR11 | Secondary fund-family sensitivity | Equal dollars to XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY |
| CORE5 | Conditional ownership diagnostic | Equal dollars to MCD, WMT, WM, COST, PG |
| PEERS13 | Conditional ownership diagnostic | Equal dollars to RSG, KO, PEP, CL, CHD, KMB, MDLZ, HSY, CLX, JNJ, ADP, CTAS, KR |

The source calendar includes SOXX; the ordinary sector-fund purchase basket does not. Neither is silently substituted for the other. The core and peer lists remain retrospectively selected surviving companies. SPY is a US large-cap fund, not a total-market or stock-selection universe. Sector portfolios and classifications evolve; constant tickers are not constant constituents or weighting laws. The actual funds are purchased after their inception, without backfilling constituents. No new signal is calculated for a purchase instrument.

Prices use the prior study's adjusted-OHLC proxy: multiply each raw OHLC observation by adjusted-close/raw-close for that date. This supplies a total-return-like path, not an exact dividend cash/pay-date ledger or original point-in-time corporate-action vintage. No dividends are credited again. Missing or invalid prices fail validation; no forward fill or synthesized opens. Verify every input file hash. Source prices stay outside git; publish hashes and source provenance.

## Funding, information, and purchase rules

Each account starts empty. Exactly **$1,000** arrives immediately before the first observed exchange-session open of every calendar month, January 2020 through the cutoff. Future contributions do not exist in the account before those dates. No prefunded future capital, common legacy holding, borrowing, or leverage.

1. **IMMEDIATE:** spend the monthly budget at its funding-date open.
2. **SIGNAL:** spend at the first eligible execution open on or after funding and no later than the last exchange-session open of that same month. If no earlier signal executes, spend at that month-end open.
3. **MONTH_END:** spend at the same predetermined month-end open regardless of signals.

A signal from the session immediately preceding a funding day may nominate that funding-day open. Earlier signals are not carried forward. Multiple nominations spend a budget once. A signal on the mandatory deadline is labeled `signal_at_deadline`; it has zero timing difference from the blind control. Alerts arriving after that month's budget is spent remain recorded as unfunded alerts. No additional contribution is invented for them.

Month-end dates come from a fixed session calendar, with month boundaries verified by a following-month session in that calendar. Keep that calendar independent of any truncated priced prefix: a prefix ending on a certified month-end still executes its deadline. The final partial month of the fixed calendar has no certified month-end deadline. The cutoff must never become an artificial deadline. Pending October cash stays cash unless a qualifying signal already executes. No future prices or outcomes determine deadline or funding dates.

Every spent budget is split equally by dollars among the basket's names, including accrued cash interest. Hold acquired shares through the common cutoff. No rebalance of existing holdings, sale, fixed-horizon exit, stop, replacement entry, or occupancy exclusion. Equal-dollar purchases on different dates acquire different share vectors; report the exact per-asset waiting decomposition rather than implying identical acquired portfolio weights.

## Cash, costs, and capital accounting

Primary: zero cash yield, **10 basis points per purchase and 10 basis points on terminal liquidation** for every basket. The common fee removes different friction assumptions as a source of cross-basket differences. A budget C buys total notional C/(1+fee); sell-value convention is market value times (1-fee). Costs are proportional; fractional shares and sufficient liquidity are assumed. Taxes, spreads beyond the declared cost, and investor-specific constraints are outside this experiment.

Two separately reported, non-selected sensitivities: (a) constant 3% annual cash yield with primary costs; (b) 25bp each side with zero cash yield. The 3% is a hypothetical scenario, not realized Treasury returns. Accrue waiting cash by elapsed calendar days/365.25 between observed opens; mark the final close with the same date convention. Both accounts receive identical external budgets even if one earns interest while waiting.

At each open: accrue existing cash, value existing shares at that open, issue units for any external contribution at the preflow account value per unit, then execute purchases and their fees. Initialize the first funding at unit NAV 1. Daily closing NAV is account wealth divided by outstanding units. A contribution alone cannot change unit NAV. The overnight movement before funding belongs to existing holders, not the arriving contribution. Mark all open holdings and pending cash at cutoff; terminal wealth includes the common liquidation adjustment. The account has no actual interim sales.

## Outcomes and attribution

Primary descriptive decision outcome: **net terminal wealth difference, SIGNAL minus IMMEDIATE**, with identical contributed capital. Also report SIGNAL minus MONTH_END and the latter versus IMMEDIATE. Report net gains, money-weighted annualized return, time-weighted annualized return, close-marked unitized maximum drawdown, annual returns, annualized volatility, average/peak invested fraction, time under water, worst-drawdown dates/exposure, fees, cash interest, pending budgets, waiting duration, signal/deadline purchase counts, and unfunded alerts. Never annualize a growing raw account balance as a portfolio CAGR.

Keep a labeled contribution ledger. At a common endpoint **126 observed sessions after funding**, compare both policies' marked liquidation wealth, irrespective of actual purchase date. Include every contribution whose common endpoint is observed. All immature contributions remain in the account path. Show positive absolute outcomes, paired mean/median differences, fraction favoring waiting, and downside quantiles. These overlapping monthly cohorts are not independent trades.

For paired cohort differences only, report an exploratory 95% circular moving-block interval with 12 consecutive monthly contributions per block, 2,000 draws, seed 20261021. Retain the ordered full calendar. Do not describe this as a confidence interval for account CAGR, a causal effect, or an adjustment for prior signal selection. Show funding-year summaries and the fixed funding-date split 2020-2022 versus 2023-cutoff without fitting. Show the full result and the contribution of the 2020 funding cohort, not an ex-post exclusion claimed as validation.

For each contribution and asset, record cash growth during the wait, asset return over exactly the same open-to-open interval, acquired adjusted shares, and contribution to terminal wealth difference. For a completed purchase, the exact terminal difference against immediate purchase is

`sum_i [B*w_i/(1+fee)] * [cash_gross(s,t)/open_i(t) - 1/open_i(s)] * close_i(H) * (1-fee)`.

Split this into avoided/forgone asset movement (cash gross=1) and cash interest. This is an accounting identity, not causal identification. For any still-pending budget, compare its actual cash with the immediate holdings at cutoff, without inventing a purchase; isolate unincurred purchase/liquidation fees as a separate component so flat-price fee savings are not labeled avoided price movement. Aggregate by signal, deadline, funding year, and basket. Identify whether one episode dominates the difference.

## Minimum verification and reporting

Verify hashes; exact common funding; chronology; no duplicate spending; true month-end/partial-month handling; contribution-based maturity; all budget/share/cash/fee identities; flat-price and cash-yield identities; overnight-gap unitization; no-flow NAV invariance; known money-weighted-return example; exact waiting decomposition; terminal account equals summed contribution lots; unchanged history when a later cutoff is truncated before future outcomes. Independently review decisive code and adverse results. Fix defects with an audit trail; do not tune rules after outcomes.

Publish all four baskets and all three policies/scenarios. Interpret the predeclared primary first. Four overlapping equity baskets are not four independent asset-class replications. Exposed history and selected survivors remain exposed history and selected survivors. Any favorable result is a bounded candidate for subsequent confirmation, not a deployment approval.

## Separate information-measurement lane

An outcome-blinded source pilot may classify all four quarterly earnings releases published in calendar 2022 for MSFT, CAT, and DUK (12 purposively chosen packets, selected for differing guidance formats before joining returns). Freeze fields distinguishing annual headline changes, remaining-period operating outlook, realized-results roll-forward, and exceptional effects. Preserve unknown/noncomparable states and original-source timestamp precision. No prices, later outcomes, consensus substitution, or investment-effect claim enters that pilot. Previously discussed WMT/CLX cases remain calibration only.
