# Communications Phase 6 — Satellite Metrics and Acceptance Requirements

**Operation:** `gmi-communications-research-20260923-sol-001`. **Carrier:** Macro PR #7794.
**Status:** Proposed research definitions and future acceptance requirements. Not a production schema, application test result or validated forecast.

Read with `SATELLITE_D2D_ECONOMICS_RESEARCH_2026-09-23.md`; bracketed source IDs refer to that chapter. Existing identity, evidence, rights, time/correction, composition and evaluation owners remain authoritative. No separate metric registry or state plane is created.

## 1. Twenty-eight proposed definitions

Each measure needs a source, locator, reporting/knowledge clock, units, basis, subject and uncertainty. These are requirements to assess, not assertions that every measure is disclosed or already ingested.

| ID | Measure | Required scope | Failure to prevent |
|---|---|---|---|
| SD01 | Economic identity | Issuer, operating business, network, partner and security under existing owners | Ticker-only or ownership inferred from an announcement |
| SD02 | Observation clocks | Period, publication, knowledge, observation and correction versions | Backdated later deployments or overwritten original targets |
| SD03 | Generation and configuration | Satellite/terminal generation and scoped component capability | Counts treated as identical units of useful capacity |
| SD04 | Deployment stage | Ordered, funded, assembled, launched, deployed, accepted and live | Launch treated as full commercial acceptance |
| SD05 | Geographic service reach | Named geography and service-class coverage basis | Land area or partner reach treated as customer adoption |
| SD06 | Temporal availability | Customer-relevant time fraction and interruption definition | Occasional access treated as continuous high-availability service |
| SD07 | Qualified throughput | Endpoint, direction, offered load, latency/reliability and test conditions | Single-user peak presented as an unconstrained fleet forecast |
| SD08 | Path bottleneck | Same-basis access, feeder, gateway, routing and scheduling constraints | Global throughput inferred by summing incompatible capacities |
| SD09 | Spectrum/service entitlement | Authorized market, use, bandwidth and date from existing owner | One country's permission treated as global commercial readiness |
| SD10 | Customer unit | Eligible, enabled, active, billable and paying units | An MNO subscriber count becomes satellite subscribers |
| SD11 | Retained service revenue | Service class, period, customer and retained versus gross fee | Gateway or engineering revenue labeled consumer network adoption |
| SD12 | Revenue per unit | Compatible numerator and average billable population | Ending counts or mixed IoT/voice devices used indiscriminately |
| SD13 | Reimbursements | Cost scope, corresponding recognized revenue and retained margin | Reimbursed cost growth treated as high-margin organic demand |
| SD14 | Contract scope | Binding base, options, delivery conditions and amendments | Framework ceiling or optional term treated as guaranteed award |
| SD15 | Backlog composition | Revenue/cash/remaining obligations, prepaid balances and date | Unreconciled components forced into an apparently coherent total |
| SD16 | Milestone collections | Earned payment, invoice, receivable, collection and remaining work | Signed funding becomes unrestricted cash or recurring earnings |
| SD17 | Customer prepayments | Cash classification, future obligations and recoupment | Advance removed from cash and its costs deducted twice |
| SD18 | Liquidity restrictions | Available cash versus restricted cash and undrawn facilities | All liquidity labels treated as deployable cash |
| SD19 | Cost to complete | Funded scope, required spending, timing and contingency | Direct satellite cost presented as entire network need |
| SD20 | Unit capital cost | Generation, included cost and accepted service capacity | Mixed contract divided by added satellites becomes disclosed price |
| SD21 | Investment classification | Initial, expansion, maintenance, replacement and funding basis | All negative cash described as optional growth investment |
| SD22 | Economic replacement | Fleet vintages, service life, disposal and comparable replacement cost | Low current capex mistaken for perpetual steady-state FCF |
| SD23 | Claims on equity | Debt, preferred/partner claims, restricted funds and contingencies | Gross operating value treated as common-equity value |
| SD24 | Dilution | Actual shares and scenario-dependent convertibles/new funding | Announced project progress automatically raises per-share value |
| SD25 | Comparable growth | Currency, acquisitions, segments and original/recast perimeter | A reported growth figure mixed with constant-FX comparisons |
| SD26 | Dated expectations | Original and revised target, scope, date and actual outcome | Company guidance described as verified analyst consensus |
| SD27 | Managed-service margin | Owned and purchased capacity, installation/support and renewals | Orbit operator and reseller both credited with full customer receipt |
| SD28 | Rights and visibility | Source retention, publication tier and private-data exclusions | Public announcement treated as blanket ingestion/display permission |

## 2. Twenty-four issuer-input arithmetic examples

Amounts are USD millions unless the unit explicitly states CAD billions, a percentage or a count. The formulas are transcribed research examples; Decimal and Fraction agree on those inputs, which does not independently authenticate the inputs. Six-decimal output is reproducibility detail, not economic precision. Most reporting periods end June 30, 2026; contract changes are dated August and Eutelsat is a fiscal-year comparison. Derived subtotal and sensitivity labels are mandatory.

| ID | Source / calculation | Result | Required interpretation |
|---|---|---:|---|
| SC01 | [AS1] AST rounded Q2 revenue: `24.4 + 7.1` | 31.500000 USD m | Product plus development/service revenue; not SpaceMobile Service receipts |
| SC02 | [AS1] AST product share: `24.4 / 31.5 * 100` | 77.460317 percent | Rounded product mix, not AI/D2D exposure |
| SC03 | [AS1] AST insurance amounts: `21.6 + 10.9` | 32.500000 USD m | Collected plus receivable; not all collected cash |
| SC04 | [GS1] Globalstar H1 cash less capex: `159.7 - 208.3` | -48.600000 USD m | Mechanical cash subtotal; not company-defined adjusted FCF |
| SC05 | [GS1] Globalstar receipt-timing sensitivity: `159.7 - 104.8 - 15` | 39.900000 USD m | Remove two disclosed receipts, not a normalized-CFO assertion |
| SC06 | [GS1] Globalstar sensitivity after capex: `159.7 - 104.8 - 15 - 208.3` | -168.400000 USD m | No judgment on quality or recurrence; do not deduct costs twice |
| SC07 | [TS2] Telesat funded-plan increment: `225 - 156` | 69.000000 satellites | Funded plan, not additional supplier order count |
| SC08 | [MD1] MDA order increment: `225 - 198` | 27.000000 satellites | Supplier order basis, not funded-plan change |
| SC09 | [TS2, MD1] Starting-population difference: `198 - 156` | 42.000000 satellites | Explains 69 versus 27; not an additional new order |
| SC10 | [TS2] Funded-plan expansion: `(225 / 156 - 1) * 100` | 44.230769 percent | Calculation from stated counts, not delivered capacity growth |
| SC11 | [MD1] Order-scope expansion: `(225 / 198 - 1) * 100` | 13.636364 percent | Count change only; mixed payload/cost scope remains |
| SC12 | [TS2] Contract with both options: `2.3 + 0.2 + 0.2` | 2.700000 CAD bn | Options included, not guaranteed base receipts |
| SC13 | [TS1, TS2] Unreconciled reported backlog bridge: `5.6 - 1.1 - 2.7` | 1.800000 CAD bn | Unexplained difference in selected sources; do not invent its cause |
| SC14 | [VS1] Viasat communications revenue change: `(825 / 827 - 1) * 100` | -0.241838 percent | Rounded-input reconstruction; company describes flat |
| SC15 | [VS1] Viasat communications EBITDA change: `(311 / 322 - 1) * 100` | -3.416149 percent | Rounded inputs and company-defined adjusted EBITDA |
| SC16 | [VS1] Viasat adjusted cash bridge: `291 - 219` | 72.000000 USD m | Excludes specified sale-related cash taxes; not unadjusted GAAP cash |
| SC17 | [IR1] Iridium service growth: `(161328 / 155570 - 1) * 100` | 3.701228 percent | Quarterly service, not total or per-subscriber growth |
| SC18 | [IR1] Iridium broadband change: `(11674 / 12724 - 1) * 100` | -8.252122 percent | Service-category revenue; no causal market-share inference |
| SC19 | [IR1] Iridium IoT change: `(47071 / 44741 - 1) * 100` | 5.207751 percent | Revenue, not average spend derived from ending devices |
| SC20 | [IR1] Iridium hosted/other change: `(16571 / 14545 - 1) * 100` | 13.929185 percent | Mixed category retained as reported |
| SC21 | [IR1] Iridium OEBITDA change: `(119107 / 121313 - 1) * 100` | -1.818437 percent | Company-defined operating measure, not CFO |
| SC22 | [SE1] SES raw reported-perimeter change: `(1602 / 978 - 1) * 100` | 63.803681 percent | NOT the reported constant-FX 72.4% |
| SC23 | [SE1] SES raw like-for-like-perimeter change: `(1602 / 1799 - 1) * 100` | -10.950528 percent | NOT the constant-FX -5.0%; currency still differs |
| SC24 | [EU1] Eutelsat LEO share of total revenue: `297 / 1235.9 * 100` | 24.031070 percent | Named total denominator; not operating-vertical or market share |

## 3. Twelve synthetic boundary illustrations

Every input in this section is invented for explanation. These are arithmetic sanity checks, not commercial forecasts, empirical network models, issuer valuations or live risk probabilities. They run no Mastermind application code.

| ID | Assumed calculation | Result | Limitation |
|---|---|---:|---|
| SY01 | Serial-link constraint: `min(100, 60, 80)` | 60.000000 capacity units | Same unit/time/direction; no alternate paths |
| SY02 | Remove nonbinding constraint: `min(200, 60, 80)` | 60.000000 capacity units | Doubling a nonbinding link does not improve throughput |
| SY03 | Geographic mismatch: `min(100, 10) + min(10, 100)` | 20.000000 capacity units | No transfer between two locations; aggregate supply/demand overstates usable amount |
| SY04 | Steady replacement allowance: `120 / 6 * 8` | 160.000000 units/year | Simplified economic-life allowance, not a company forecast |
| SY05 | Funding at lower issue price: `950 / (100 + 200 / 5)` | 6.785714 units/share | Final total equity value after deployed funding; no cash added twice |
| SY06 | Funding at higher issue price: `950 / (100 + 200 / 10)` | 7.916667 units/share | Same project value, different share count |
| SY07 | Retained-share hurdle: `40 / 0.30` | 133.333333 spending units | Recover 40 of contribution at a 30% retained share |
| SY08 | Retail-free but wholesale-paid: `100000 * 3` | 300000.000000 units/month | Assumed billed eligible units and wholesale price, not a market estimate |
| SY09 | Undiscounted backlog versus value: `100 / (1.1 ** 3)` | 75.131480 value units | Assumed discount rate/date, not investment guidance |
| SY10 | Conditional chain probability: `0.9 * 0.8` | 0.720000 probability | Second value explicitly conditional on first; not independent marginals |
| SY11 | Intersection lower bound: `max(0, 0.9 + 0.9 - 1)` | 0.800000 probability | Two marginal availabilities alone do not imply 0.81 intersection |
| SY12 | Intersection upper bound: `min(0.9, 0.9)` | 0.900000 probability | With previous case bounds are [0.8,0.9], not a point estimate |

## 4. Thirty proposed adversarial acceptance cases

Every case is a future requirement to map into the existing owners and then execute on the real path. **No case below is represented as an executed product-test PASS.** Arithmetic passing above does not satisfy these requirements.

| ID | Challenge | Required behavior |
|---|---|---|
| SAT01 | A launch succeeds, but service acceptance is missing | Display achieved launch only; network paid-service state remains unavailable. |
| SAT02 | Insurance includes collected cash and a receivable | Retain the split and replacement timing; neither restores in-service capacity. |
| SAT03 | AST reports products and development activity but no SpaceMobile Service revenue | Show real revenue while withholding the false consumer-service-adoption inference. |
| SAT04 | A partner discloses its entire mobile base | Do not count all customers as enabled, active or billed satellite users. |
| SAT05 | Light data exists and broadband is targeted later | Present two capabilities and two clocks; do not upgrade current capability. |
| SAT06 | Satellite broadband supports a terrestrial tower | Label backhaul, not direct handset connectivity. |
| SAT07 | Capacity is idle in one area and demand is elsewhere | Do not combine them as if resources were universally transferable. |
| SAT08 | A paper evaluates static single-user UDP | Retain experiment/model scope; no unqualified commercial network ranking. |
| SAT09 | Funded plan is 156 to 225; supplier order is 198 to 225 | Explain compatible increments 69 and 27; preserve distinct populations. |
| SAT10 | An order includes satellites, configuration changes and long-lead items | Do not label total divided by added count as disclosed satellite unit cost. |
| SAT11 | Backlog components do not reconcile | Preserve reported figures and unresolved difference; invent no missing component. |
| SAT12 | A base contract has optional extensions | Separate base from options; do not treat all options as secured receipts. |
| SAT13 | Milestone funding may overlap the headline contract | Require component/recognition reconciliation before adding values. |
| SAT14 | Operating cash includes infrastructure prepayments | Expose future obligation; an adjusted sensitivity is not reported normalized cash. |
| SAT15 | Management excludes specified cash taxes from a headline metric | Show formula/basis; do not silently label it unadjusted GAAP CFO. |
| SAT16 | Reported and like-for-like growth differ in currency and perimeter | Compare only matched bases; do not force raw arithmetic to the constant-FX percentage. |
| SAT17 | A growing segment offsets declining legacy operations | Retain both and the whole-issuer bridge; no pure-growth label on all consolidated value. |
| SAT18 | A transaction or JV is proposed, but closing is not verified | Keep status unverified; do not claim either completion or abandonment. |
| SAT19 | A gateway is commissioned before constellation service | Explain the enabled ground milestone without claiming commercial network launch. |
| SAT20 | A service is included in a retail plan | Do not infer zero supplier revenue or fabricate undisclosed wholesale economics. |
| SAT21 | Terminal installation or delivery is still incomplete | Separate a commercial award from activated and paying installations. |
| SAT22 | Current capex is unusually low | Do not infer sustainable cash without replacement and maintenance context. |
| SAT23 | Funding arrives through convertible or new equity | Reflect scenario-dependent claims/shares; no automatic project-to-per-share uplift. |
| SAT24 | A target changes generation, geography or date | Preserve the prior promise; evaluate the matched capability rather than relabeling success. |
| SAT25 | Public data omit pricing or materiality | Render an informative qualitative exposure with unknown magnitude, not zero or a fabricated percentage. |
| SAT26 | An event dataset includes only successful launches | Require failed/degraded/withdrawn cases before outcome qualification. |
| SAT27 | Related press releases repeat one contract | Treat as one evidence family, not independent confirmation counts. |
| SAT28 | Content has restricted rights or sensitive customer data | Use the existing permission/publication owner; no public raw-data mirror. |
| SAT29 | A descriptive mechanism has not passed forecast/trading evaluation | No stock-rank, position-size or trade-authority promotion. |
| SAT30 | The dossier renders correctly but cannot reach the company/watchlist workflow | Fail the user-journey requirement; provenance-only display is insufficient. |

## 5. Integration and evaluation gate

Source acceptance must preserve the original evidence class and make missing materiality visible. Product proof must show a real source observation reaching a useful explanation and the existing company/watchlist path, including disagreements and unavailable states. Design-system, privacy and source-custody requirements remain those of their current owners. Any forecasting or investment use requires its separate existing evaluation/authority gate.

Unresolved in this phase: Telesat's selected contract/backlog-component bridge; later closing/operational status of proposed transactions and the US JV; complete country/device availability; original expectation vintages; undisclosed wholesale and cost coefficients. None authorizes guessed inputs or a replacement source system.

The principal next action is cross-family business/exposure mapping and targeted gap closure using the six preserved research phases. No implementation or Fable receiver has been started.
