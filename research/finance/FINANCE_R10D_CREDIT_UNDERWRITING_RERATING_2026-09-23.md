# Finance R10D — credit-supply and underwriting regulation rerating research

Date: 2026-09-23 / 2026-09-24 UTC research continuation.  
Operation: `gmi-finance-sector-research-20260923-sol-001`.  
Carrier: Macro PR #7786 / `sol/finance-sector-research-20260923`.  
State: RESEARCH / RETROSPECTIVE MEASUREMENT / DRAFT-HOLD.  
Mission complete: false. Product implemented: false.  
Protected procedure: `Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1.  
Direct principal reason: `PRINCIPAL_JUDGMENT`.

This tranche advances two frozen R10 mechanism cases:

- `R10-IN-RBI-CONSUMER-NBFC-RISK-WEIGHTS-20231116`
- `R10-AU-APRA-SERVICEABILITY-BUFFER-20211006`

It preserves the R10 retrospective-design amendment and the R10B price-basis law. Formal causal outcome labels remain `UNMEASURED`. The purpose is to understand how two superficially similar “credit tightening” actions transmit through very different financial business models.

---

## 1. Executive conclusions

### R10D-1 — Regulatory credit tightening has at least four distinct economic forms

Do not create a generic `CREDIT_TIGHTENING` state.

The RBI and APRA cases demonstrate at least four separate mechanisms:

1. **capital-intensity tightening** — more regulatory capital per unit of exposure;
2. **funding-cost tightening** — higher capital/risk treatment for a lender's wholesale funders;
3. **underwriting-capacity tightening** — lower maximum amount a borrower can qualify for;
4. **portfolio-risk tightening** — changing the mix or growth rate of riskier cohorts before losses appear.

These mechanisms can point in different directions for current earnings, future growth, expected losses and valuation.

### R10D-2 — RBI's November 2023 action directly changed lender economics

The Reserve Bank of India's 16 November 2023 measures were immediately effective for the relevant risk-weight provisions. They raised risk weights on covered consumer credit and card receivables and increased the risk weight on certain bank exposures to NBFCs. The regulator also required board-approved subsegment limits by 29 February 2024.

The transmission chain is:

```text
covered unsecured / card / NBFC exposure
→ higher risk-weighted assets
→ lower capital ratio for unchanged equity
→ higher marginal capital requirement
→ repricing / slower growth / portfolio mix change / capital raise
→ funding interaction
→ risk-adjusted ROE and per-share growth
→ valuation
```

For NBFCs dependent on bank funding, there is an additional channel:

```text
bank loan to NBFC receives higher risk weight
→ bank's capital cost of that exposure rises
→ NBFC marginal bank borrowing can become more expensive or constrained
→ NBFC funding mix / asset pricing / growth changes
```

This is materially different from APRA's serviceability rule.

### R10D-3 — RBI's objective was pre-emptive, not a response to broad observed distress

RBI's own later publications state that broad portfolio asset quality did not show major signs of stress when the intervention was taken. The concern was sustained rapid consumer-credit growth and rising bank dependence by NBFCs.

That matters for the rerating model. A prudential action taken **before** losses emerge can:

- reduce future growth;
- reduce future tail risk;
- increase current capital/funding cost;
- improve future portfolio quality;
- change competitive share among lenders with different capital and funding models.

Therefore an immediate earnings drag and a longer-run reduction in required return can coexist.

### R10D-4 — The aggregate credit response is visible but not cleanly causal

RBI subsequently reported:

- covered consumer-loan growth moderating from 23.3% in November 2023 to 13.9% in June 2024;
- bank credit to NBFCs moderating from 18.5% to 8.2%;
- credit-card outstanding growth moderating from 34.2% to 23.3%.

These observations are consistent with the intended prudential transmission. They do not isolate the regulation from interest rates, lender risk appetite, base effects, borrower demand or other supervisory actions.

The Finance product should label them `POST_POLICY_SYSTEM_OBSERVATION`, not `CAUSAL_EFFECT`.

### R10D-5 — Company impact is measurable and highly heterogeneous

**Bajaj Finance** reported that the increase in consumer-credit risk weights reduced its 31 December 2023 capital adequacy ratio by about **290 basis points**. Reported CRAR was 23.87%; the company said it would have been 26.77% without the change.

The same quarter still showed:

- AUM +35% YoY;
- NII +29%;
- PAT +22%;
- ROA 4.9% versus 5.4% in the comparison period;
- ROE 22.0% versus 24.0%;
- loan losses/provisions +48%.

The company also completed an approximately ₹8,800 crore QIP on 9 November 2023, one week before the RBI action. That capital raise is a major confounder: later capital resilience cannot be attributed solely to operating profitability or post-rule adaptation.

**SBI Cards** disclosed an even more direct capital/funding bridge in its Q3 FY24 investor material:

- CAR fell from 23.3% in Q2 FY24 to 18.4% in Q3 FY24;
- Tier 1 fell from 20.8% to 16.3%;
- the company attributed approximately **400 basis points** of CRAR impact to the RBI risk-weight increase;
- incremental bank borrowing was described as roughly **25–30 bp more expensive**;
- cost of funds rose to 7.6%;
- gross credit cost was 7.5%, up 193 bp YoY;
- ROA was 4.1%, down 67 bp YoY;
- PAT still grew 8% YoY.

This is the cleanest mechanism witness in the tranche: the same rule simultaneously affected capital consumption and marginal funding economics.

Do not infer that the contemporaneous rise in credit cost was caused by the regulatory action. Credit performance and risk-weight rules are separate clocks.

### R10D-6 — The frozen Indian price cohorts show dispersion, not a policy verdict

Before looking at returns, the research froze:

**Consumer/NBFC cohort**
- Bajaj Finance
- Cholamandalam Investment and Finance

**Bank cohort**
- HDFC Bank
- ICICI Bank
- Axis Bank
- Kotak Mahindra Bank
- State Bank of India

SBI Cards is a separate direct-mechanism witness because it is absent from the incumbent international price store used for the cohort calculation. A fresh direct vendor request for SBI Cards was rate-limited on the inspected host, so no return was invented.

Adjusted-return paths from the incumbent store, using the prior observed close as base:

| Offset | Consumer/NBFC cohort | Bank cohort | NBFC minus banks |
|---|---:|---:|---:|
| day 0 | +0.89% | -0.31% | +1.20pp |
| +1 | -1.75% | -2.10% | +0.35pp |
| +5 | -3.26% | -2.16% | -1.10pp |
| +20 | +5.31% | +8.68% | -3.36pp |
| +60 | -5.73% | +6.40% | -12.12pp |
| +120 | +0.84% | +12.27% | -11.43pp |
| +252 | +1.55% | +23.59% | -22.04pp |

The two-NBFC cohort experienced an observed maximum peak-to-trough drawdown of about -22.34% in the measured window; the five-bank cohort's was about -8.57%.

This pattern is consistent with a period in which some consumer/NBFC exposures faced more difficult capital/funding/growth economics than selected banks. It is **not** evidence that the RBI action caused a 22 percentage-point relative return.

Material confounders include:

- Bajaj's pre-event QIP;
- separate RBI product restrictions at Bajaj;
- credit-cost changes;
- bank-specific deposit and NIM cycles;
- India's broader equity and credit cycle;
- company-specific execution;
- later regulation and policy changes.

### R10D-7 — APRA tightened underwriting capacity, not mortgage pricing directly

APRA announced on 6 October 2021 that authorised deposit-taking institutions should assess new mortgage borrowers using a serviceability buffer at least **3.0 percentage points** above the loan product rate, versus 2.5 points commonly used previously.

APRA's letter says institutions using a lower buffer beyond the end of October 2021 would face individual prudential-capital consequences. Therefore preserve two clocks:

- **announcement/information clock:** 6 October 2021;
- **operating-compliance clock:** by the end of October / effectively November 2021 for normal implementation analysis.

APRA estimated the 50 bp increase would reduce the maximum borrowing capacity of a typical constrained borrower by roughly 5%, while expecting a fairly modest aggregate housing-credit impact because many borrowers did not borrow at their maximum.

The transmission chain is:

```text
higher serviceability assessment rate
→ lower maximum qualified loan for constrained applicants
→ changed approval / loan-size / borrower-mix frontier
→ origination volume and market-share competition
→ future borrower leverage / portfolio risk
→ later credit loss and risk-adjusted returns
```

This is **not** a direct increase in the bank's regulatory risk weight on every mortgage, and it does not mechanically raise mortgage pricing.

### R10D-8 — The risky-lending mix eventually improved, but interest rates became a major co-treatment

The share of new lending at DTI ≥6:

- was 23.3% in the September 2021 quarter;
- reached roughly 24.3–24.4% in December 2021;
- fell to 23.1% in March 2022;
- 22.1% in June 2022;
- 17.1% in September 2022;
- 11.0% in December 2022;
- 7.5% in March 2023;
- 6.1% in June 2023.

APRA and RBA publications attribute the later decline to a combination of the serviceability-buffer increase, lender policy changes and rising interest rates.

Therefore:

- the early 2022 fall is useful mechanism evidence;
- later declines cannot be attributed to the October 2021 rule alone;
- the post-May-2022 RBA tightening cycle is a major treatment overlap.

### R10D-9 — APRA achieved a different kind of “success” than an earnings catalyst

The economically desirable outcome of a serviceability rule can be **less risky new production**, even if it modestly constrains loan growth.

RBA later judged that the higher buffer had reduced riskier lending at the margin, though it explicitly noted the difficulty of isolating the effect from wider trends.

This demonstrates a critical Finance rule:

> A regulation can improve the resilience of future earnings while reducing the amount of near-term balance-sheet growth available to earn those earnings.

That trade-off belongs in the Finance dossier.

### R10D-10 — The four-major bank price path does not show a uniform negative rerating

The APRA cohort was frozen before measuring returns:

- Commonwealth Bank;
- Westpac;
- National Australia Bank;
- ANZ.

Adjusted-return equal-weight path from the prior observed close:

| Offset | Four-major cohort |
|---|---:|
| day 0 | -1.12% |
| +1 | -0.13% |
| +5 | -0.40% |
| +20 | -0.93% |
| +60 | -2.94% |
| +120 | +5.04% |
| +252 | -1.97% |

Observed maximum cohort drawdown was about -20.67%. Individual +252 results varied materially:

- CBA: -4.55%;
- Westpac: -10.50%;
- NAB: +14.08%;
- ANZ: -6.89%.

There is no common return result that can be interpreted as “the serviceability buffer de-rated Australian banks.”

### R10D-11 — Subsequent bank earnings were dominated by more than the APRA rule

ANZ's FY2022 disclosures provide a useful company witness:

- statutory profit after tax increased 16%;
- cash profit from continuing operations increased 5%;
- CET1 was 12.3%;
- cash ROE was 10.4%;
- management reported restored momentum in Australian home loans.

ANZ also reported rising-rate benefits to deposits/capital and strong second-half margin recovery while home-loan competition remained intense.

This is exactly the conflict the Finance system must show:

```text
tighter mortgage qualification
+ improving underwriting mix
+ restored operational origination capacity
+ rising cash rates helping deposit economics
+ intense home-loan price competition
= mixed earnings transmission
```

A one-factor APRA label cannot explain the later stock or earnings path.

---

## 2. RBI measurement details

### 2.1 Frozen cohort return observations

All percentages below use the incumbent adjusted international close store and the R10B convention: prior non-null observation is the base; offset 0 is the event-date observation; subsequent offsets count non-null price observations rather than asserting certified exchange-session counts.

| Name | 0 | +1 | +5 | +20 | +60 | +120 | +252 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bajaj Finance | +1.91 | -0.05 | -2.09 | +4.02 | -8.00 | -6.60 | -6.72 |
| Cholamandalam | -0.12 | -3.46 | -4.44 | +6.60 | -3.45 | +8.29 | +9.81 |
| HDFC Bank | +0.26 | +0.05 | +1.12 | +10.11 | -8.00 | -1.61 | +22.11 |
| ICICI Bank | -0.54 | -2.05 | -1.92 | +10.23 | +8.67 | +20.18 | +39.40 |
| Axis Bank | -1.44 | -4.51 | -4.06 | +7.59 | +5.33 | +9.41 | +10.49 |
| Kotak Bank | +0.19 | -0.28 | -1.71 | +4.58 | -1.16 | -5.51 | +0.88 |
| State Bank of India | -0.01 | -3.70 | -4.23 | +10.87 | +27.14 | +38.87 | +45.05 |

These are descriptive shareholder-return proxies, not factor-adjusted excess returns.

### 2.2 What Mastermind should infer — and abstain from

Supported descriptive observations:

- the direct regulatory capital burden is source-measurable for Bajaj and SBI Cards;
- system credit growth later slowed in the targeted areas;
- the frozen NBFC/consumer cohort lagged the frozen bank cohort over the longer measured horizon;
- dispersion inside both cohorts is substantial.

Not established:

- policy-causal abnormal return;
- policy-causal credit-loss improvement;
- a universal “banks benefit / NBFCs lose” rule;
- an optimal trade;
- a calibrated predictive factor.

---

## 3. APRA measurement details

### 3.1 New-lending risk-mix timeline

The post-announcement path must be split:

**Phase A — low-rate implementation period**
- Nov 2021 implementation;
- high-DTI lending still rose into the December quarter;
- March 2022 showed only an initial decline.

**Phase B — overlapping rate-tightening period**
- RBA cash-rate increases materially reduced borrowing capacity;
- bank internal policies also changed;
- high-DTI share fell much more rapidly.

This prevents a classic attribution error: giving the October 2021 policy credit for every later decline after the macro regime changed.

### 3.2 Individual four-major return observations

| Bank | day 0 | +20 | +60 | +120 | +252 | max drawdown |
|---|---:|---:|---:|---:|---:|---:|
| CBA | -1.97% | +1.42% | -4.27% | +2.63% | -4.55% | -19.46% |
| Westpac | -0.62% | -10.31% | -15.08% | -3.39% | -10.50% | -22.97% |
| NAB | -0.83% | +2.88% | +6.20% | +18.20% | +14.08% | -21.04% |
| ANZ | -1.08% | +2.30% | +1.38% | +2.71% | -6.89% | -24.36% |

The dispersion is too large to support a simple common-event interpretation.

---

## 4. Reusable product object — Credit Constraint Transmission State

Do not build a scalar score.

Required fields:

1. **policy type** — capital intensity / funding / underwriting capacity / portfolio limit / provisioning / pricing restriction;
2. **information clock**;
3. **effective/compliance clock**;
4. **covered products and explicit exclusions**;
5. **covered institution classes**;
6. **pre-event growth / underwriting / risk baseline**;
7. **capital effect** — RWA and ratio impact when disclosed;
8. **funding effect** — cost, availability, maturity and mix;
9. **origination effect** — approvals, maximum loan size, volume and product mix;
10. **pricing effect**;
11. **risk-mix effect** — DTI/LVR/vintage/borrower risk;
12. **credit-performance clock**;
13. **profitability clock** — NIM/NII, PPOP, provisions, ROA/ROE;
14. **capital-management response** — equity raise, retained earnings, slower growth, securitization, distribution changes;
15. **market-share response**;
16. **expectation state** — dated consensus/guidance or explicit missingness;
17. **valuation anchor and recognition**;
18. **price path and drawdown**;
19. **co-treatments / confounders**;
20. **falsifier**.

### Example conflict states

- `GROWTH_SLOWS / RISK_QUALITY_IMPROVES`
- `CAPITAL_COST_UP / REPORTED_EARNINGS_STILL_UP`
- `FUNDING_COST_UP / ASSET_YIELD_REPRICES`
- `ORIGINATION_CAPACITY_DOWN / DEPOSIT_MARGIN_UP`
- `PORTFOLIO_RISK_DOWN / STOCK_FLAT`
- `STOCK_UP / POLICY_EXCESS_RETURN_UNPROVEN`

These are descriptive states, not investment recommendations.

---

## 5. Rerating implications

### Consumer/NBFC lender

Primary valuation bridge:

```text
risk-adjusted asset yield
− funding cost
− expected loss
− operating cost
− capital charge
= sustainable return on equity
```

A tighter capital rule can de-rate the stock even if nominal loan growth remains high when the same assets consume more equity and reduce future marginal ROE.

But a rule can ultimately support a higher quality multiple if it:

- curbs weak underwriting;
- reduces tail loss;
- improves portfolio durability;
- lowers the required return.

The timing of these two effects can differ by years.

### Bank funding an NBFC

The bank may respond through:

- higher loan pricing;
- exposure reduction;
- collateral/structure changes;
- migration to borrowers with better capital economics.

The NBFC and funding bank do not necessarily have opposite outcomes; the funding bank can also lose fee/spread volume.

### Mortgage bank under serviceability tightening

For APRA-style underwriting policy, the primary bridge is:

```text
eligible borrower capacity
→ approved loan size / conversion
→ mortgage volume and mix
→ pricing competition
→ funding/deposit economics
→ expected loss / capital
→ per-share earnings
```

Higher rates can simultaneously:

- reduce mortgage borrowing capacity;
- increase refinancing stress;
- expand deposit margins;
- change fixed/variable mix;
- alter credit losses.

Therefore serviceability policy must be separated from the subsequent rate cycle.

---

## 6. Data and source requirements unlocked

### Regulatory owner

Need source-native storage of:

- exact circular / standard;
- publication and effective dates;
- covered products;
- exclusions;
- institution classes;
- quantitative parameter change;
- sunset/review/reversal dates.

### Company owner

Need contemporaneous:

- RWA and capital ratio;
- disclosed regulatory impact;
- funding cost;
- loan book / receivables / originations;
- asset yield;
- NIM;
- credit cost;
- ROA/ROE;
- equity issuance and distributions;
- product restrictions and other co-treatments.

### Market owner

Need:

- adjusted return basis;
- quote-price basis when computing valuation;
- correct listing/session/currency;
- dividends/corporate actions;
- local benchmark and sector context.

### Expectations owner

Need actual historical estimates or guidance from the correct fiscal period. Do not backfill today's consensus into 2023 or 2021.

---

## 7. Source register

### RBI and India

- RBI prudential action and immediate-effect / board-limit chronology:
  https://systemhealth.rbi.org.in/Scripts/PublicationsView.aspx_id%3D22349.html
- RBI Financial Stability Review / regulation detail:
  https://www.rbi.org.in/Scripts/PublicationReportDetails.aspx?ID=1255&UrlPage=
- RBI subsequent credit-growth observations:
  https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=58448
- RBI later review of NBFC bank-funding risk weights:
  https://www.rbi.org.in/scripts/AnnualReportPublications.aspx?Id=1436
- Bajaj Finance FY2024 annual report site:
  https://www.bajajfinserv.in/finance-digital-annual-report-fy24/index.html
- Bajaj Finance Q3 FY24 press release:
  https://cms-assets.bajajfinserv.in/is/content/bajajfinance/q-3-press-releasepdf?fmt=pdf&scl=1
- SBI Cards Q3 FY24 investor presentation:
  https://www.sbicard.com/sbi-card-en/assets/docs/pdf/who-we-are/notices/SEFilingInvestorPresentationJan24.pdf

### APRA / Australia

- APRA 6 Oct 2021 decision:
  https://www.apra.gov.au/news-and-publications/apra-increases-banks-loan-serviceability-expectations-counter-rising-risks
- APRA detailed letter:
  https://www.apra.gov.au/news-and-publications/strengthening-residential-mortgage-lending-assessments
- APRA December 2021 statistics:
  https://www.apra.gov.au/news-and-publications/apra-releases-quarterly-authorised-deposit-taking-institution-statistics-9
- APRA September 2022 statistics:
  https://www.apra.gov.au/news-and-publications/apra-releases-quarterly-authorised-deposit-taking-institution-statistics-12
- APRA December 2022 statistics:
  https://www.apra.gov.au/news-and-publications/apra-releases-quarterly-authorised-deposit-taking-institution-statistics-13
- RBA April 2022 FSR regulatory developments:
  https://www.rba.gov.au/publications/fsr/2022/apr/regulatory-developments.html
- RBA March 2023 non-bank lending review:
  https://www.rba.gov.au/publications/bulletin/2023/mar/non-bank-lending-in-australia-and-the-implications-for-financial-stability.html
- ANZ FY2022 results:
  https://www.anz.com.au/newsroom/media/2022/10/2022-full-year-result---proposed-final-dividend-/
- ANZ FY2022 CFO commentary:
  https://www.anz.com.au/newsroom/media/2022/10/anz-2022-full-year-results--chief-financial-officer-farhan-faruq

---

## 8. Evidence limitations

- The historical return cohorts are retrospective and purposively defined; they are not randomized or untreated controls.
- The international price store uses current vendor-adjusted historical series and is not a frozen vintage of what was available at each event date.
- Exact local exchange-calendar reconciliation remains outside this tranche; exact observed dates are retained.
- Historical aggregate analyst consensus is not established for these cases.
- SBI Cards is absent from the incumbent international price store used here. No price outcome was invented.
- A direct fresh Yahoo request for SBI Cards from the inspected host returned an HTTP 429; this is a route-local failure, not evidence of permanent unavailability.
- SBI Cards and Bajaj PDF table sources were text-extracted; screenshot retrieval through the web PDF path was attempted and failed with a cache error. Do not describe them as independently visually verified through that path.
- APRA's later high-DTI decline overlaps with RBA rate increases and lender policy changes.
- Bajaj's capital position is confounded by its pre-event QIP and other regulatory/product actions.
- No source in this tranche creates a canonical identity, admitted dataset, approved basket, recommendation or trade signal.

---

## 9. Material hypotheses and falsifiers

### H-RBI-1 — Capital-intensive consumer lending should face a weaker marginal-growth/ROE frontier

Evidence that would support:
- slower targeted portfolio growth;
- repricing;
- increased capital;
- reduced risk-weight-intensive mix;
- lower growth unless returns compensate.

Falsifier:
- exposed lenders maintain the same growth and risk-adjusted returns without additional capital, pricing, funding changes or risk migration.

### H-RBI-2 — Bank-dependent NBFCs should exhibit a funding transmission

Evidence:
- higher marginal borrowing cost;
- migration from bank loans to bonds/deposits/securitization;
- slower balance-sheet growth or asset repricing.

Falsifier:
- no measurable funding-cost/mix effect after controlling for the general rate cycle.

### H-APRA-1 — The buffer should reduce very-high-DTI origination at the margin

Evidence:
- decline in high-DTI share after implementation, before or controlling for major rate-cycle effects.

Falsifier:
- high-DTI share persistently rises despite implementation, absent a documented composition shift that defeats the measure.

### H-APRA-2 — Stronger underwriting can improve resilience without producing a positive near-term stock catalyst

Evidence:
- safer new loan mix;
- low realized mortgage losses;
- no consistent common-stock rerating.

Falsifier:
- the only measurable effect is lost profitable volume with no improvement in portfolio risk or future losses.

---

## 10. Product consequence

R10D adds a reusable distinction to the Finance system:

> **Credit regulation should be represented by the economic variable it constrains—not by a generic positive/negative regulatory tag.**

The Finance dossier should let the user move:

```text
regulatory parameter
→ covered exposure
→ company-specific balance-sheet consequence
→ management response
→ growth / funding / loss / capital bridge
→ per-share return on capital
→ valuation recognition
→ price recognition
```

The key user questions become:

- Did the rule change the amount of business the company can write?
- Did it change the amount of equity needed to support that business?
- Did it change the cost of funding?
- Did it improve the risk quality of future production?
- Was the effect offset by a macro rate cycle?
- Did the company reprice, raise capital, change mix or accept lower returns?
- Did per-share economics improve?
- Did the multiple change?
- Did the stock outperform an appropriate context?
- Which parts are observed versus inferred?

---

## 11. Exact next research action

R10D materially advances the RBI and APRA cases but does not close R10.

The remaining four frozen mechanism cases are:

1. UBS / Credit Suisse transaction completion;
2. TSE cost-of-capital / stock-price-conscious management request;
3. China's May 2024 housing-policy easing;
4. Hong Kong RBC insurance-capital implementation.

The next principal pair should be **UBS/Credit Suisse + TSE cost-of-capital** because together they test capital allocation, restructuring, integration, governance and multiple recognition rather than another credit-underwriting mechanism.

Do not merge PR #7786 or begin final Fable implementation orchestration yet.
