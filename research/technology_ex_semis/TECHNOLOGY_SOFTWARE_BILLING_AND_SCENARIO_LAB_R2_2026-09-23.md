# Technology software — Billing units and economic scenario laboratory

23 September 2026. Supplement to `TECHNOLOGY_EX_SEMIS_SOFTWARE_ECONOMICS_R2_2026-09-23.md` on Macro draft/HOLD PR #7793. Operation `gmi-technology-ex-semis-research-20260923-sol-001`; existing GMI workstream and research branch remain unchanged.

**Research only.** Five source-backed billing-model examples and seven original illustrative scenarios. Catalog-derived calculations are not actual customer invoices, realized vendor prices, accounting revenue, production product tests or stock forecasts. No transaction, subscription purchase, external account change or product implementation was performed. Fable has not been dispatched. The full Technology ex-Semiconductors program remains incomplete.

## 1. What must be understood before modeling software growth

A theme can expand useful activity while reducing the chargeable resource required for each task. A vendor can earn less revenue yet more gross profit if its delivery cost falls faster. Conversely, a product can attract users and revenue without earning an acceptable return on implementation, support, capital or dilution. These are distinct analytical possibilities; they are not claims about the future results of any company below.

The proposed intelligence model therefore retains three related quantities:

- **Activity:** the technical work performed, with its actual unit and population.
- **Billing:** the entitled or chargeable quantity under a particular contract, allowance, price and period.
- **Customer outcome:** useful work accepted by the customer, with quality, failure and rework considered.

The objects may have many-to-many relationships. One customer task can invoke several actions; one subscription can cover many tasks; a single person can use multiple products; one capacity window can serve several requests. None of these relationships authorizes a global product identity or a new event store. Source-scoped descriptions and any later validated joins must use the existing owners.

The investor's question is not only whether a new technology is being used. It is whether increased use expands a vendor's paid economic role, and whether that role remains profitable and defensible after customer optimization, competition and product substitution.

## 2. Five native billing examples

The public pages in section 8 were observed on 23 September 2026. They are mutable catalogs/documentation, not a historical pricing archive or a statement of any customer's negotiated terms. Current publication observation and contract-effective dates must remain separate. A future implementation needs accepted retention and rights through the incumbent owners before claiming point-in-time production coverage.

### 2.1 Salesforce Agentforce: action is not outcome

The catalog lists Flex Credits at USD 500 per 100,000 credits; a standard action uses 20 credits. It also offers other charging arrangements, so one rule cannot represent every deployment [B01]. The selected rate implies USD 0.10 per standard action before allowances, discounts and other charges. No useful-outcome count, realized enterprise price or revenue-recognition policy follows from this catalog arithmetic.

**Original scenario:** assume 1,000 business cases produce equivalent accepted outcomes, initially requiring four standard actions each and later two. Selected charges are `1,000 × 4 × 0.10 = 400` and `1,000 × 2 × 0.10 = 200`. The equivalent quality and absence of additional work are assumptions. This is not Salesforce's published customer example or a forecast. The research question is whether lower cost per completed case induces enough incremental paid cases, retained subscriptions or better margins to offset the lower action count.

### 2.2 Snowflake virtual warehouses: query count is not billed compute

Warehouse charges depend on size, clusters and provisioned runtime. The documented provisioning minimum is 60 seconds, followed by per-second billing [B02]. These rules alone do not determine a customer's full invoice or the performance consequences of changing execution patterns.

**Original scenario:** 100 jobs each take 30 seconds at the same warehouse rate. If each independently resumes resources, selected billed time is `100 × max(30,60) = 6,000 seconds`. If all fit sequentially into one continuous 3,000-second run, it is `max(3,000,60) = 3,000 seconds`. The example assumes no idle time, resizing, other charges or change in runtime/quality. Equal job counts can therefore correspond to different billed units under the stated assumptions. This is an economic illustration, not a recommendation to batch every production workload.

### 2.3 Datadog logging: ingestion and selected retention differ

The pricing page separately lists log ingestion starting at USD 0.10 per GB and standard indexing with 15-day retention at USD 1.70 per million events under the annual billing option [B03]. Other fees, tiers, commitments and services are outside this selected calculation.

**Original scenario:** a month initially has 100 GB and 100 million log events, with 10% indexed. Selected charges are `100 × 0.10 + 100 × 0.10 × 1.70 = 27`. A later month has 200 GB and 200 million events but indexes 2%; selected charges become `200 × 0.10 + 200 × 0.02 × 1.70 = 26.8`. Raw volume doubles while these selected charges decrease approximately 0.74%. No assumption is made that the change is appropriate for the customer's operational requirements. Retention policy and billable mix matter alongside activity.

### 2.4 GitLab: included allowance and purchased pool have different scopes

The current pricing page lists a limited-time Premium inclusion of 12 credits per human user per month [B04]. Documentation distinguishes individual included credits, which are not shareable, from a purchased shared commitment pool. Human and non-human usage also have different included-entitlement treatment; Duo Pro/Enterprise are not generally converted into this usage-billing rule [B05].

**Original scenario:** ten eligible human users each have 12 included credits; one consumes 40 and nine consume zero. Assume no evaluation or purchased pool and valid on-demand terms. Excess is `max(40−12,0) + 9×max(0−12,0) = 28 credits`, not `max(40−10×12,0) = 0`. This does not estimate enterprise revenue. The scenario shows why allowance scope, promotional validity and subject identity must survive the model; organization-wide averaging would misstate this example.

### 2.5 Autodesk Flex: product-day is not application open

For applicable per-day products, Flex charges once per user/product within a 24-hour window, not again for each reopening; AutoCAD is listed at seven tokens per day. A subscription for the same product is used before Flex tokens, and per-result services have different rules [B06].

**Original scenario:** the same eligible user opens the same product at relative hours 0, 5 and 23, with sessions closed before the next 24-hour boundary and no overlapping subscription. The selected charge is one window, seven tokens, not three opens × seven = 21. A distinct opening at hour 24 establishes a second window in the boundary check. Neither token purchases nor expiration are modeled as product revenue. A useful adoption signal must retain the paid time unit rather than simply count launches.

## 3. Original workload and value-capture scenario

Consider a hypothetical usage vendor with base revenue 100, cost of revenue 30 and gross profit 70. Suppose useful workloads rise 40%, billable resources per workload fall 30%, and realized price per resource falls 5%.

Under a simplified linear model:

`New revenue = 100 × 1.40 × 0.70 × 0.95 = 93.10`

Revenue falls 6.9% despite the larger useful workload. For revenue merely to remain flat under the assumed resource and price changes, workload growth must exceed the break-even factor:

`1 ÷ (0.70 × 0.95) = 1.5037593985`, or approximately **50.38% growth**.

Now separately assume total cost of revenue falls to 18. New gross profit is `93.10 − 18 = 75.10`, about 7.29% higher than the original 70. The cost change is an invented scenario input, not inferred from the resource change and not attributed to a company. Research should test delivery cost and realized price independently.

This demonstrates why all four questions matter: Is the customer doing more useful work? Is the provider billing more? Is the provider retaining more gross profit? Does the resulting cash return justify its valuation? A positive answer to one does not mathematically determine the others.

For small changes, the log identity can organize decomposition:

`change in log revenue = change in log useful workloads + change in log chargeable resources per workload + change in log realized price`

This identity assumes the selected revenue partition is multiplicative and comparable. Fixed fees, contract floors, nonlinear tiers, credits, product mix, currency and recognition timing require explicit additional terms or a different model. It is not a universal production formula to impose on every software company.

The most informative research falsifier is a change in the relation between useful work and billed work: observed efficiency improvement, pricing reset, shift into included tiers, or a replacement charging unit. The impact can remain ambiguous when customer-level usage or costs are not disclosed. Ambiguity should be visible rather than hidden behind a demand score.

## 4. Original per-share and valuation scenario

Assume a fictional business has annual revenue 100, net margin 20%, 100 comparable shares and P/E 50. Its EPS is 0.20 and the corresponding price is 10. Next period, assume revenue rises to 120, margin to 22%, shares to 110, and P/E falls to 40.

`New EPS = 120 × 0.22 ÷ 110 = 0.24`

`New price = 0.24 × 40 = 9.60`

Revenue and EPS both increase 20%, yet price falls 4%. The higher margin's contribution is offset by the share-count change in this specific setup, while multiple compression more than offsets EPS growth. The inputs are deliberately invented to isolate the arithmetic, not to assign a target multiple or probability to a real stock.

This is why a theme dossier cannot end at revenue acceleration. It should explain the conversion into cash and per-share economics, and then examine what expectations valuation already embeds. Capital intensity, financing, dilution and the duration of profitable growth belong in that assessment. Current market prices, consensus and share data must later come from their existing governed owners at compatible clocks; none was loaded to produce company target prices in this research unit.

A reverse valuation can be useful without claiming certainty: state a market-value input and solve for the growth, retained margin, capital burden or duration necessary under a disclosed scenario. Report a surface of assumptions, not an authoritative single number. Do not infer probabilities merely from the spacing of optimistic and pessimistic cases.

## 5. Connect pricing, customer value and moat without inventing measurement

### 5.1 Incremental monetization is a net bridge

For a defined customer cohort and period, investigate additional product fees, paid usage and realized price, then subtract demonstrable displacement of legacy subscriptions, discounts or service credits. Keep acquisition and currency effects separate. This is a research decomposition; it does not replace issuer revenue recognition or imply that every term is publicly observable.

Customer cost savings and vendor revenue are not the same economic pool. A buyer can retain most of the benefit. A supplier can also capture value through retention, broader deployments or a different charging unit rather than a higher price per technical action. The hypothesis must name which mechanism is proposed and what observation would distinguish it from simple free adoption.

### 5.2 The relevant moat is control of paid, useful work

Candidate mechanisms to investigate include embedded workflow knowledge, proprietary customer context used with permission, trusted integration, switching and migration costs, distribution, reliability, accumulated validation and a product's ability to satisfy a demanding budget owner. These are analytical hypotheses to investigate company by company, not an assertion that every incumbent possesses all of them.

Alternative explanations must be equally concrete. A new application may be bundled into a broader platform; an open alternative may reduce paid resource demand; the buyer may internalize a formerly outsourced workflow; or a new interface may shift the customer relationship to another provider. A technically impressive feature is not automatically a durable pricing advantage.

To evaluate a claimed moat, ask for evidence of retention under competitive pressure, successful paid expansion, implementation time and cost, customer switching behavior, realized pricing and incremental delivery cost. A famous customer logo or a large unpaid user base does not supply all of this evidence.

### 5.3 Separate three horizons

A technical improvement may reduce billed intensity immediately; customer deployment may expand over subsequent quarters; renewal or repricing may change value capture later. Treat these as separate horizons with their own evidence dates. A single positive-or-negative impact sign can be misleading when the effects arrive at different times.

The same distinction matters for market interpretation. A stock may move on anticipated adoption before paid use is reported, or on a valuation change before the next operating disclosure. The research can describe this sequence, but claiming incremental return prediction requires the existing point-in-time evaluation and market-incorporation owners. Pricing documentation does not by itself establish investor surprise or an entry signal.

## 6. Concrete product requirements for the existing template

The shared Technology/theme/company journey should expose a **business model explanation**, not a reproduction of a vendor billing console. The proposed investor panel is small: the job performed, buyer, paying unit, main demand variable, optimization/substitution risk, reported economic evidence, unresolved quantity and next discriminating observation.

A source drawer should retain product, tier, hosting/offering, geography/currency, list-versus-contracted status, source observation date, rule version and customer scope where known. Contract allowances require a scope such as person, organization, product, capacity or time window. Runtime implementation must use accepted native identity and time semantics, not infer a new global customer or product identity from a descriptive label.

For comparative research, a view could place useful activity, billed unit and retained economics side by side. It should label a catalog calculation as a scenario and a reported financial measure as reported; do not display both with the same certainty styling. Missing customer-level price or cost stays unknown. No price estimate should silently become an earnings forecast.

The model must refuse tempting but invalid joins: launches into paid days; registered users into paid seats; credits into successful outcomes; queries into billed seconds; parent revenue into one product's materiality; a historical price into a current contract. Explain the missing bridge so the reader understands what would be needed to resolve it.

Use the incumbent source/evidence, financial, company, K1 and GMI owners for retention and facts. The proposed research transformations are deterministic and reviewable where inputs permit them. They do not authorize a new crawler, billing simulator service, source registry, continuous watcher, queue or event store. F04 and the shared STSI template remain the product-composition direction. No research result in this supplement grants Prophet ranking, candidate gating, entry, sizing, veto or trading authority.

## 7. Reproducibility and acceptance boundary

The companion portable JSON contains the exact numerical inputs and outputs for these seven scenarios and the three management-guidance bridges already preserved in R2 section 5. Its local path is `TECHNOLOGY_SOFTWARE_R2_CALCULATIONS.json`; SHA-256 at this checkpoint is `7318d474cbf4b2d4368eb0dcb24402fd7b3c45c67df49b88b070082f034aaa8c`. The GitHub documents are the canonical research recovery path; an attachment is not a new source authority or a substitute for this persisted analysis.

**Executed verification:** 32 arithmetic assertions passed: 15 on the three guidance examples; 15 on the seven illustrative scenarios, including a 24-hour boundary case and the revenue-neutral workload threshold; and two coverage-count checks. Decimal arithmetic was used. Manual extraction from public sources is not independently verified by arithmetic. These checks do not constitute product tests, source parser tests, pricing engine conformance, independent design review, calibrated forecasts, CI qualification or production acceptance.

The three guidance results remain: selected remaining-year management-revenue midpoint revisions of USD 93.546 million for Datadog, 29.727 million for MongoDB and 0.244 million for UiPath. Exact dated inputs, source links and an independent algebraic reconciliation are in the R2 report. They are not analyst-consensus surprises, organic-demand measurements or relative stock rankings.

Additional future product acceptance should demonstrate: clear hypothetical labels; preservation of actual billing units and allowances; correct product-day boundaries; no pooling of individual entitlements; versioned price assumptions; refusal of unsupported realized-price inference; disclosure of acquisition/FX and accounting scope; and no trading-authority promotion. These are requirements, not claims that a product implementation already passes.

A useful final browser proof will require a retained accepted source, the proper native owner, a reviewed transformation, the existing authenticated UI and exact evidence drilldown. Test the missing-definition, changed-price, unknown-cost and contradictory-source cases as well as the populated view. No such production implementation or browser proof was attempted in this research unit.

## 8. Official-source register and limits

| ID | Public source | Exact use |
|---|---|---|
| B01 | https://www.salesforce.com/agentforce/pricing/ | Selected Flex Credit rate and standard action quantity; list pricing, not realized contracts. This source also appears in R2, so it is not counted as an independent new source. |
| B02 | https://docs.snowflake.com/en/user-guide/warehouses-considerations | Warehouse runtime/provisioning minimum; workload examples in this supplement are original assumptions. |
| B03 | https://www.datadoghq.com/pricing/ | Selected log ingestion and standard 15-day indexing prices under the annual option; other charges excluded. |
| B04 | https://about.gitlab.com/pricing/ | Limited-time 12-credit Premium inclusion; promotional validity and plan must remain explicit. |
| B05 | https://docs.gitlab.com/subscriptions/gitlab_credits/ | Individual versus shared entitlement, billing subject and usage exclusions; current documentation, not a retroactive historical rule. |
| B06 | https://www.autodesk.com/buying/flex | Selected seven-token AutoCAD rate, 24-hour reopening behavior and subscription precedence; no whole-invoice or revenue estimate. |

All six locators were read on 23 September 2026. They cover five vendors and are not six independent confirmations of one economic claim. No claim is made that the examples cover every region, edition, account, contract or future price. Source URLs can change and do not establish immutable source retention, private-data rights or native runtime admission.

## 9. Cumulative program frontier

R1, R2 and this supplement now preserve the whole-sector map, a detailed first software/cloud/security cross-section, and concrete unit-economic/expectations cases. This is a meaningful research phase boundary, not completion of the full software census or the parent delivery mission.

The next domain unit is D08–D15: IT/engineering services, devices, systems/storage, networking, non-semiconductor components, EMS/ODM, distribution and electronic measurement. It should identify retained economic value rather than mechanically copy software KPIs. Start with contract/labor/outcome economics for services and then follow a defined system-to-component-to-manufacturing network, retaining buyer program, inventory, acceptance, financing and cash-conversion distinctions. Semiconductors and dedicated equipment remain excluded and referenced through their existing owner.

Before final Fable delivery, the program still owes broader regional/company coverage, source-feasibility and rights mapping, point-in-time expectations/evaluation, current native contract and shared-template reconciliation, an accepted written specification and an executable implementation roadmap. No Fable binding, START, worker, watcher, merge, deployment or autonomous continuation has been created here. Effects are limited to original public-source research and cumulative continuity documentation on the existing carrier.
