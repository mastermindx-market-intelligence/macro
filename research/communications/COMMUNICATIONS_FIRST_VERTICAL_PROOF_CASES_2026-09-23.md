# Communications First Vertical — Source Examples and Proof Boundary

**Date:** 2026-09-23. **Operation:** `gmi-communications-research-20260923-sol-001`.
**Carrier:** Macro Draft/HOLD PR #7794. **Status:** public research examples, not admitted native evidence, live product data, executed application tests or an investment model.

Read with the Communications business-intelligence design and advertising implementation plan. The spec defines the user job; the plan maps forty CRV requirements to implementation tasks. This companion supplies the original-source numerical and interpretation examples needed for those tasks. It does not grant source-retention/display rights or populate production identity.

## 1. Reporting and expectation scope

Actuals refer to the quarter from 2026-04-01 through 2026-06-30; prior-year growth comparisons use 2025-04-01 through 2025-06-30. Company guidance sources were published before the reported quarter result but refer to that same Q2 2026 metric. They are original company-guidance observations, not a census of later revisions or analyst consensus.

Money remains in the issuer table's source unit. Where the original guide uses USD millions and actuals use USD thousands, the guide is explicitly multiplied by 1,000. The source publication dates below have day precision in this pack; this is not proof of an intraday knowable cutoff. Arithmetic examples never create evidence/issuer/security/retention IDs. Those fields remain null in the portable JSON.

## 2. Primary-source register

The seven selected primary sources were opened in this design phase. Their full reports are not reproduced here. Locators below select exact statements/tables; no inferred source hash or access receipt is supplied.

| ID | Publisher and publication date | Selected source |
|---|---|---|
| M2Q | Meta; 2026-07-29 | https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/meta-06302026xexhibit991.htm |
| M1Q | Meta; 2026-04-29 | https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-First-Quarter-2026-Results/ |
| G2Q | Alphabet; 2026-07-22 | https://www.sec.gov/Archives/edgar/data/1652044/000165204426000066/googexhibit991q22026.htm |
| T2Q | The Trade Desk; 2026-08-06 | https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-Second-Quarter-2026-Financial-Results/default.aspx |
| T1Q | The Trade Desk; 2026-05-07 | https://investors.thetradedesk.com/news-and-events/news/news-details/2026/The-Trade-Desk-Reports-First-Quarter-2026-Financial-Results/default.aspx |
| MG2Q | Magnite; 2026-08-05 | https://investor.magnite.com/news-releases/news-release-details/magnite-reports-second-quarter-2026-results |
| MG1Q | Magnite; 2026-05-06 | https://investor.magnite.com/news-releases/news-release-details/magnite-reports-first-quarter-2026-results |

## 3. Twelve reference calculations

Decimal and Fraction independently evaluate the same transcribed inputs. Agreement checks arithmetic, not source authenticity or statistical usefulness. Six decimals are a reproducibility convention; displayed financial values should follow their source precision.

| ID | Inputs and operation | Reference result | Interpretation and source selector |
|---|---|---|---|
| CV01 | 60801, 47516; pct_change; USD million | 27.959003 percent | Reported issuer growth, not AI revenue growth. [M2Q]: Condensed consolidated income statement |
| CV02 | 18775, 20441; pct_change; USD million | -8.150286 percent | Negative profit growth despite revenue growth; not a cost attribution. [M2Q]: Condensed consolidated income statement |
| CV03 | 31862, 30116, 962; net_cash; USD million | 784.000000 USD million | CFO minus property/equipment purchases and finance-lease principal. [M2Q]: Free cash flow reconciliation |
| CV04 | 60801, 58000, 61000; closed_range; USD million | WITHIN_ORIGINAL_RANGE categorical | Within original company range; not analyst consensus. [M2Q,M1Q]: Current revenue and Q1 CFO outlook |
| CV05 | 63271, 54190; pct_change; USD million | 16.757704 percent | Business-scope growth, not all-issuer growth. [G2Q]: Revenue category table: Google Search & other |
| CV06 | 7303, 7354; pct_change; USD million | -0.693500 percent | Network decline does not become a Search decline. [G2Q]: Revenue category table: Google Network |
| CV07 | 39069, 44924; net_cash; USD million | -5855.000000 USD million | Signed consolidated cash; not a Search-only subtotal. [G2Q]: Non-GAAP free cash flow reconciliation |
| CV08 | 715057, 694039; pct_change; USD thousand | 3.028360 percent | Reported revenue; supplier-cost presentation still requires explanation. [T2Q]: Condensed consolidated statement of operations |
| CV09 | 101577, 116777; pct_change; USD thousand | -13.016262 percent | Reported operating-income change, not a normalized sensitivity. [T2Q]: Condensed consolidated statement of operations |
| CV10 | 715057, 750000; pct_change; USD thousand | -4.659067 percent | Original 750 million floor explicitly multiplied by 1000; below floor, not consensus surprise. [T2Q,T1Q]: Reported revenue and original Q2 outlook |
| CV11 | 189595, 161956; pct_change; USD thousand | 17.065746 percent | Issuer-defined contribution, not GAAP revenue. [MG2Q]: Contribution ex-TAC reconciliation |
| CV12 | 189595, 181000; pct_change; USD thousand | 4.748619 percent | Original 181 million ceiling explicitly multiplied by 1000; not consensus surprise. [MG2Q,MG1Q]: Contribution ex-TAC and original Q2 outlook |

CV10 and CV12 are proportional differences from a floor and a ceiling, not generic surprise percentages. The real view must first express the correct categorical comparison. A range midpoint is optional reference arithmetic, never a substitute for the original range. Source rounding that overlaps a threshold remains indeterminate.

### A source-label refinement from this pass

Alphabet's selected current release explicitly includes the consolidated non-GAAP free-cash-flow reconciliation used by CV07. Earlier research conservatively described the same calculation as a consolidated cash subtotal. This phase refines the label to a reported issuer-defined reconciliation while preserving the amount, scope and non-GAAP basis. It does not make the result Search-only, change prior source bytes, or normalize away investment. The result remains negative and must survive the shared assertion pipeline.

## 4. Four reviewable example explanations

These are proposed response patterns, not unqualified live recommendations. The implementation must regenerate numerical observations from admitted owner data and apply only templates whose supporting conditions are satisfied. Management causality and house interpretation remain separate from the stated measurements.

**Meta.** The cited quarter combines approximately 28% issuer revenue growth with an approximately 8% decline in reported operating income. Advertising-volume and price observations support stronger monetization, while reported costs limit how much reaches operating profit. The original revenue result is inside the original company range. Do not call it a consensus beat or attribute all issuer costs to advertising or AI. Next evidence to inspect: a comparable profit/cash bridge and whether monetization gains persist without proportionate cost growth. [M2Q,M1Q]

**Alphabet.** Search & other revenue increases while Network revenue declines. The consolidated free-cash-flow measure is negative after capital expenditure. This supports a split business interpretation, not a verdict that every Alphabet activity deteriorated or that Search alone consumes that cash. Next evidence to inspect: the separate operating/capital allocation disclosures needed to connect Search economics to the issuer result. No unsupported segment allocation is filled in. [G2Q]

**The Trade Desk.** Reported revenue increases while reported operating income declines; revenue is below the original company-guidance floor after matching units. These facts do not prove a market-share transfer to another intermediary or a consensus miss. Supplier-cost presentation, established-client spending and operating costs need their disclosed explanations before organic or normalized inferences. Next evidence to inspect: comparable retained economics and the qualified customer-spend trajectory. [T2Q,T1Q; detailed definitions remain in Phase 2]

**Magnite.** Issuer-defined contribution excluding traffic-acquisition costs grows and exceeds the original guidance ceiling. It is not GAAP revenue, and the release's named operating-cash measure is adjusted EBITDA minus capital expenditure rather than the statement-of-cash-flows measure. Next evidence to inspect: the disclosed segment mix and conversion into comparably defined cash, not a mechanically ranked comparison with other companies' margins. [MG2Q,MG1Q]

These templates are deliberately qualified. The first product must still lead with the useful economic finding rather than forcing the investor to read raw source provenance before learning what changed.

## 5. Illustrative interpretation checks

The local check script exercises twelve reference-level properties: exact guidance-boundary inclusion; above/below range; null versus zero; positive-prior percentage domain; explicit unit scaling; within-range versus midpoint; zero-sum budget conservation; loss-turnaround absolute change; no duplicate cash component; and no summing unlike populations. These checks are local demonstrations of the desired semantics, not execution of the proposed production comparison module.

The application acceptance set is CRV-01 through CRV-40 in the implementation plan. It additionally requires native round-trip, actual clocks, rights/identity, unauthorized-request denial before source access, logout-race protection, fixed coverage denominators, bilingual dual-theme layouts, real company/watchlist behavior and alternate-mirror negative proof. None of those application outcomes was executed by the arithmetic helper.

## 6. Fixture and production boundaries

The portable `COMMUNICATIONS_FIRST_VERTICAL_REFERENCE_CASES_2026-09-23.json` exports this document's twelve examples. It is not an extra source owner. Production code must not load the research or tests directory as an accepted current source. Test-native assertions and identity receipts must be explicitly synthetic and use the existing owner's test grammar; real native IDs, source digests, entitlements and source generations come only from actual admission.

Required source/identity fields are intentionally unassigned in this reference pack. Missing source-retention evidence is not cured by placing a URL in a field named digest. An accepted public report is not a license for republishing a proprietary consolidated product snapshot. All actual publication follows the existing owner rights/private-transport decision.

The first application may display latest accepted evidence while reporting that its completeness against all newer releases is unqualified. It may not call the old Q2 examples current merely because this file is served today. Corrections and newer admitted observations recompile the affected results; the historical examples remain unchanged as tests.

## 7. What was verified in this research phase

The local helper evaluated twelve source-input cases using Decimal and Fraction and checked their expected labels/units. Document checks verify the sixteen specification sections, eight implementation tasks, forty unique acceptance IDs, source-ID closure, parseable Python plan examples, no placeholder markers, intentional null native IDs and exact file hashes. The twelve illustrative checks are explicitly reference-level only.

Not verified here: the proposed product schema, shared-contract acceptance, actual private owner placement, live source admission, live identity joins, full repository Agent OS validation, CI, production application behavior, Fable pickup or deployment/browser acceptance. The checkpoint and native write/readback receipts identify exactly which documents were persisted.
