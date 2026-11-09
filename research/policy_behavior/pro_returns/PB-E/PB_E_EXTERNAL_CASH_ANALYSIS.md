# PB-E — External cash, demand linkage and admissible denominators

**Research cutoff:** October 6, 2026, America/Chicago. Sources retrieved October 7 UTC. Claim dates remain those of the latest inspected source; this is not a complete real-time ledger. Source IDs resolve in `PB_E_SOURCE_REGISTER.md` and `PB_E_NETWORK_EDGES.json`.

## Finding

The casebook establishes material financial/commercial links and several actual funding flows. It does **not** identify an industry-wide fraction of AI demand funded by its beneficiaries, or a complete amount of independent final-customer cash. Both aggregate values are `null`, with reasons in the JSON. The 15 cases were deliberately selected for structural variety and include repeated exposure to the same model companies. They cannot estimate prevalence or supply 15 independent statistical observations.

A dual-role counterparty is an observable relationship. The source of money used for a particular invoice is a stronger claim. Sustainable final demand is stronger again: it requires economically useful consumption and recurring customer cash sufficient to support the relevant costs. The return measures each only where the disclosure supports it.

## 1. Define the perimeter before adding money

| Perimeter | What counts as a crossing | What does not establish independent final demand |
|---|---|---|
| A single model company | Investor cash, loans, grants and customer payments entering that legal/economic boundary, classified separately | A cloud supplier's equity investment, an undrawn commitment, or subscriber counts alone |
| Model company plus its participating suppliers, investors and project companies | Cash arriving from parties outside the explicitly listed network | Transfers between included entities, even if one party recognizes revenue |
| An infrastructure project | Sponsor cash, drawn debt, tax/grant receipts and collected offtake payments, each with its own clock | A loan guarantee, an uncalled letter of credit, or a parent debt assumption |
| A mature service or asset cohort | Outside operating receipts and cash operating/capital costs matched to the same cohort and period | Consolidated cash flow that mixes growth projects, prepayments, financing and unrelated operations |

For a fixed boundary B and time interval T:

`gross_external_ingress(B,T) = sum(actual cash transfers from outside B to inside B during T)`

Report separately its operating-customer, equity, debt, government-support and asset-sale components. Net external flow subtracts outward boundary crossings. Neither gross ingress nor net flow is a profitability measure. Internal transfers cancel when the network is consolidated; recognized revenue across several supply-chain stages can exceed the original cash that funded those stages without violating accounting or proving misconduct.

No ratio in this return combines cash flows across currencies without conversion, current cash with multi-year commitments without an explicit horizon, or the same loan with its guarantee. Transaction groups in the JSON mark amendments, snapshots and components that must not be added. That metadata is a guardrail, not a complete transaction ledger.

### A bounded, useful actual-cash observation

At the **OpenAI-only boundary**, two specified 2026 investor flows total **$80 billion**: Amazon's $50 billion invested by its July filing and SoftBank's completed $30 billion follow-on by October 1. The arithmetic counts the completed follow-on, not SoftBank's separate cumulative $64.6 billion investment history. Amazon's June balance and subsequent contribution are components of its $50 billion. This is a documented subtotal of selected financing ingress, not current cash on hand, the final size of all OpenAI rounds, or money from independent operating customers. [R-S23, R-S24]

At a broader boundary that includes Amazon and SoftBank, these same transfers are internal. SoftBank's outside bond financing is a different crossing, while its bridge repayment is an outflow; they cannot all be counted as new net money. The full uses of funds and the wider network's external operating receipts are not disclosed sufficiently to reconcile a global total. NVIDIA's historically announced $100 billion LOI and later announced $30 billion allocation are excluded from this actual-cash subtotal. [R-S06, R-S07, R-S24]

## 2. Preserve the economic state

| Observation | Meaning | Required next evidence |
|---|---|---|
| Equity or debt commitment | Capital may become available subject to terms | Legal execution, conditions, actual transfer and consideration form |
| Funded capital | Financing has been provided | Cash versus noncash breakdown and restrictions on use |
| Purchase contract / minimum spend | A customer's contractual obligation with stated scope | Performance, cancellations, credits, pricing, fulfillment and collectibility |
| RPO / backlog | A defined forward commercial measure | Definition, recognition horizon, cancellation and overlapping totals |
| Revenue | Recognized accounting economics | Customer identity, related-party status, gross/net basis and cash bridge |
| Receivable / contract asset | An asset arising from recognized or conditionally billable economics | Settlement, credit quality, aging and opening-to-closing reconciliation |
| Deferred revenue | Accounting liability associated with prior payment or billing/contract timing | Cash-flow details; the closing balance is not this period's collections |
| Delivered capacity | Available infrastructure under a defined measurement | Commercial acceptance and operating availability |
| Utilization / consumption | Work performed or energy consumed | Paid use, price, cost and external cash collection |
| Warranty, warrant or guarantee | A specific contractual risk or incentive | Correct instrument type, trigger, vesting/exercise/claim state and settlement |

The commission's warrant category includes equity-linked customer incentives. The CoreWeave stock grant is explicitly typed as **issued shares** within that category; it is not described as a warrant. Government warrants at LAC and Intel retain issuance and exercise conditions. A guarantee amount may be a payment cap, an underlying principal limit or a percentage of obligations; these bases are not interchangeable.

## 3. Descriptive measures that survive the denominator test

The JSON contains the inputs, expression, value, units and limitations for the following reproducible calculations. Amounts are rounded as disclosed.

| Measure | Result | Interpretation and limits |
|---|---:|---|
| Microsoft OpenAI share of commercial RPO at December 31, 2025 | Approximately **45%** of **$625bn** | Named commercial concentration involving an investor/customer relationship; not dollar tracing, industry AI demand, or June 2026 share. [R-S04] |
| Implied amount from that rounded RPO share | Approximately **$281.25bn** | Arithmetic from rounded management numbers. It overlaps the announced Azure commitment; do not add them. [R-S01, R-S04] |
| AMD explicitly binding initial capacity / announced roadmap | **1 / 6 = 16.67%** | Capacity scope, not percentage of binding contract dollars. Other tranches may become binding under terms not fully visible. [R-S11, R-S12] |
| AMD maximum strike proceeds if every share vests and all exercise is for cash | **$1.6m** | A hypothetical mechanical upper amount from 160m × $0.01; cashless exercise is permitted and no vesting/exercisability was reported at June 27. This is not observed funding. [R-S11, R-S13] |
| CoreWeave H1 2026 operating cash flow less cash PP&E purchases | **−$10.454bn** | $3.663bn minus $14.117bn. Growth-capital dependence indicator; does not isolate maintenance capex or project returns. [R-S20, R-S21] |
| CoreWeave operating cash flow / same-period cash PP&E | **25.95%** | Company-wide cash coverage of the reported capital-spending line, not independent customer cash conversion. [R-S21] |
| CoreWeave June AR change from December 2025 | **−19.82%** | $2.541bn versus $3.169bn. A six-month balance change; do not divide it by year-over-year revenue growth. [R-S21] |
| CoreWeave Q2 2026 top-three disclosed customer revenue shares | **72%** | 36% + 26% + 10%. Anonymous labels may change across periods; no identity or stable-cohort inference. [R-S20] |
| CoreWeave principal due in remaining 2026 plus 2027 | **$10.597bn** | $4.413bn + $6.184bn. Net operating collections and refinancing availability must be aligned to those dates; gross multi-year RPO is not coverage. [R-S20] |
| Thacker Pass cumulative DOE draws / principal facility limit | **61.37%** | $1.209bn / $1.97bn through June 2026; capitalized interest excluded on both sides. Funding execution, not government share of all project capital. [SEL-S21] |
| Crane draw / closed principal facility | **0% as of August 6, 2026** | Explicit zero observed at that date; does not assert zero at the October research cutoff. [SEL-S04] |
| LAC effective rate less contractual coupon, three advances | **198 / 204 / 213 bp** | Disclosed effective rates less stated coupons; allocated financing-cost amortization, not measured subsidy savings or WACC. [SEL-S21] |

### Measures deliberately not produced

**Industry financing-linked demand share:** unavailable because the numerator and denominator do not share an industry perimeter, transaction definition or observation window.

**External operating cash / total network cash commitments:** unavailable because actual end-customer receipts and a deduplicated, horizon-matched commitment denominator are missing. The proposed form is usually a stock-versus-flow comparison, not cash conversion.

**Government-supported demand or financing as a share of all strategic-industry activity:** unavailable. Several loans, warrants, support payments and commercial purchases are not commensurable; underlying populations are incomplete.

**Receivable-growth / revenue-growth score:** not calculated from mismatched intervals. Microsoft requires an opening balance and broader settlement reconciliation; CoreWeave provides a six-month AR change and separately reported quarter/half-year sales. A paired series or DSO requires the same units, period and scope, with acquisition, credit-loss, factoring and contract-asset effects considered.

**Credit-spread improvement, WACC savings or revision-durability advantage caused by support:** not measured. Contractual rates and completed transactions establish access and terms, while the comparative design remains a proposal in the selective-protection file.

## 4. Cash conversion requires a bridge

The relation `cash = revenue − closing receivables` is invalid. Even an elementary collection bridge needs opening receivables; a reliable bridge also handles contract assets, deferred/billed balances, prepayments, noncash consideration, credits, write-offs, taxes, acquisitions, currency and reclassifications.

Microsoft's $24.1 billion annual related-party revenue and $6 billion closing receivable therefore do not establish $18.1 billion collected. A financing transaction does not reverse properly recognized revenue simply because the investor is also a supplier. The accounting question, collection question and funding-provenance question must remain distinct. [R-S03]

MP provides a useful realized-state example: support income, the support receivable, product sales and government cash are separately disclosed. The receipt of cash on prior-quarter support does not make the same amount current-quarter product revenue. Third-party sales alongside the support also falsify an account in which every protected unit necessarily sits unsold. [SEL-S09, SEL-S10]

CoreWeave's positive operating cash flow and lower closing AR provide counterevidence to universal noncollection. Its simultaneous investment burden means positive OCF alone does not establish a self-financing growth model. Principal repayment belongs in financing cash flow; interest may already be included in operating cash flow, so it must not be subtracted again without a defined cash-flow bridge. [R-S20, R-S21]

## 5. Does support precede demand acceleration?

The cases establish differing sequences. AMD couples the purchase arrangement and incentive in one announcement. Amazon's Anthropic facility makes additional funding availability dependent on delivered compute milestones. CoreWeave's first disclosed OpenAI contract precedes the January 2026 NVIDIA placement, although the vendor relationship existed before that placement. Some government facilities close long before the first draw. These sequences defeat a universal temporal story. [R-S11, R-S15, R-S19, AI_A03, SEL-S02, SEL-S04]

Testing acceleration requires a previously frozen event clock, a comparable operating series and the information actually public at each date. A later 10-Q cannot backfill exact terms into an earlier decision cut. This research overlay is explicitly ineligible for production or point-in-time joins until the incumbent owner admits individual facts with sufficient evidence clocks.

## 6. What would make a loop durable?

The strong version of durability is repeated outside operating cash that covers service delivery, economic asset replacement, debt service and required returns without recurrent support. Capacity can be productively used before a young business reaches that state; temporary financing is not by itself a failure.

The strong fragility mechanism is correlated shortfall: a model company's financing difficulty can reduce its purchases, weaken the supplier's investment, stress a receivable or capacity backstop, and damage the resale value of similar assets. Independent customers, liquid collateral, credible performance, diversified funding and contract terms that allocate risk to parties able to bear it can interrupt that process.

The casebook's benign controls are substantive. Meta's broader advertising-led cash generation, an operating power producer's outside customers and ASML's customer-funded development provide alternative economic routes. None supplies a blanket solvency judgment, and none eliminates its own contractual or execution risks. The goal is to identify the dependence that remains after these alternatives are considered.
