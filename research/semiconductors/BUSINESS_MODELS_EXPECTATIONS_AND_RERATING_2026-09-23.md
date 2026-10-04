# Semiconductor Intelligence — Business Models, Expectations and Re-rating Mechanics

**Research installment 5 — 23 September 2026 · principal-owned research · not the final Fable handoff**

Operation: `gmi-semiconductors-research-20260923-sol-001`. Parent: `WS:GMI-THEME-GRAPH`. Existing carrier: Macro draft/HOLD PR #7780, branch `sol/semiconductors-research-20260923`. Research resumes from canonical head `78f9d5be8e53df5b0f2d146ebb4ce5333158fa6a`. Governing protected procedure at research start: Mastermind `bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap 1.

This document is original editorial synthesis using bounded public-source examples. It is not an accepted production contract, consensus-estimate database, house forecast, live basket, ranking, price target, trade recommendation, native assertion import, or alternate evidence/identity system. The purpose is to make the eventual Semiconductor Theme explain **how industrial change becomes—or fails to become—per-share economic change and changing market expectations** without forcing Fable or implementation workers to rediscover the logic.

## 1. Outcome: move from industrial relevance to expectation-aware economics

The first four research installments established semiconductor physical/manufacturing structure, process/material/IP dependencies, application economics, capacity qualification, scenario counterexamples and research baskets. The remaining high-leverage research question is different:

> **When the semiconductor industry changes, what exactly must change in a business model, financial statement and point-in-time expectation set before the development can rationally matter to a stock?**

The proposed analytical chain is:

`industrial event -> product/process relevance -> units/content/price/share -> recognized revenue -> gross profit -> operating profit -> cash and capital needs -> diluted per-share economics -> point-in-time expectation revision -> valuation multiple / required return -> observed price`

Every arrow is conditional. A technology can be important without producing recognized revenue. Revenue can rise while contribution falls. Cash can improve because customers prepay. EPS can rise while diluted share count or valuation multiple offsets it. A stock can rise before reported earnings because expectations change first, or fall despite better earnings if the new result was already embedded in expectations. This research does **not** decide which security deserves a higher multiple or predict a price. It defines what Mastermind must preserve before such analysis can be responsibly attempted by its existing analytical owners.

## 2. Seven economic archetypes require different leading indicators

A single “semiconductor earnings growth” model is structurally wrong. The same industry event transmits differently through seven recurring business archetypes.

| Archetype | Primary economic engine | Early indicators that may matter | Key offsets / failure modes | Examples used in this installment |
|---|---|---|---|---|
| Foundry | Paid wafer/process/package work | qualified capacity, wafer output, utilization, node/mix, pricing, customer ramps | yield, depreciation, overseas/start-up dilution, FX, mix, customer concentration | TSMC; prior UMC/Hua Hong work |
| Fabless platform | Product/program shipment and content | design wins, platform ramps, supplied capacity, segment/product revenue, ASP/mix | foundry/package constraints, customer concentration, export controls, inventory, R&D/SBC/dilution | NVIDIA, AMD |
| Custom/data-infrastructure silicon | Program ramps plus connectivity/custom content | AI/custom bookings, customer program timing, data-center mix, product generations | concentration, third-party IP/manufacturing, acquisitions, preferred-stock/share-count changes | Broadcom, Marvell |
| Memory | Bits × ASP × mix, with extreme cycle sensitivity | bit shipments, ASP, HBM/DDR/NAND mix, inventory, utilization/capex, qualification | price collapse, node-shrink density, supply response, inventory digestion | Micron, Nanya |
| Semiconductor equipment/process control | Systems plus service/installed-base economics | orders/bookings, shipments, customer acceptance, systems mix, installed-base service, fab capex | customer acceptance, timing, export controls, service/system mix, capacity at customers | ASML, Lam, KLA, Applied Materials |
| EDA/IP | License/subscription/hardware plus royalties | backlog/RPO/ACV, bookings, product adoption, customer shipments, royalty rates | timing of large licenses, acquisitions/perimeter, metric-definition changes, R&D, SBC | Cadence, Synopsys, Arm |
| Analog/power/embedded | Broad product portfolio and end-market recovery | end-market revenue, bookings, channel/customer inventory, factory utilization, content/qualification | replenishment vs consumption, mix, price, acquisitions, internal manufacturing absorption | Analog Devices, onsemi, TI, NXP |

These are **research archetypes**, not mutually exclusive sectors. One issuer can span several. A business can move between them over time through acquisitions, divestitures or an expanding production role. The machine must therefore attach the economic mechanism to the business/product evidence, not permanently stamp a company with one label.

## 3. The point-in-time expectations contract

### 3.1 Three owners must remain separate

The eventual system should never collapse these into one “expected EPS” or “expected revenue” field:

1. **Management outlook** — issuer-authored guidance or target, including the exact publication date and assumptions.
2. **External consensus** — a licensed/accepted estimate owner, with vendor, observation timestamp, contributor universe and revision history. This installment does not create or scrape one.
3. **Mastermind house expectation** — only if an accepted existing forecast owner produces it; must retain model version, input cut, uncertainty and evaluation receipt. Research evidence does not self-originate a forecast.

A fourth object, **actual reported result**, settles a period but does not rewrite what was knowable earlier.

### 3.2 Required fields for an expectation observation

This is a requirement for existing evidence/time-series owners, not a new database schema. Every observation should preserve at least:

- issuer/business/security identity through the accepted native resolver;
- publisher/expectation owner;
- `published_at` and source-availability clock;
- fiscal period and measure period;
- measure name and definition version;
- low / midpoint-or-point / high, and whether midpoint is source-provided or derived;
- currency and unit;
- GAAP / non-GAAP / operational-metric basis;
- continuing-operations / consolidated / segment scope;
- acquisition/divestiture perimeter;
- FX and tax assumptions where supplied;
- diluted-share assumption where supplied;
- product or end-market scope for subset guidance;
- conditional exclusions (for example, China revenue excluded from an outlook);
- source locator and lineage;
- explicit supersession link to the prior outlook for the same scope;
- actual result when later reported;
- derived surprise only when definitions are compatible;
- missing fields as typed unknowns, never guessed from a nearby period.

### 3.3 Comparison is a contract, not subtraction

A guide-versus-actual “surprise” is only valid when the metric, period, unit, accounting basis and business perimeter are compatible. If a company changes reporting segments, closes an acquisition, changes a non-GAAP definition, executes a stock split, or changes the scope of a product subset, the comparison must either bridge the change or explicitly refuse a naïve delta.

A midpoint derived from `(low + high) / 2` is a calculation and should be labeled as such. A company can guide to an approximate point with a tolerance, a range, a growth rate, a margin or an EPS value; these shapes must not be coerced into a single false precision.


### 3.4 Current Mastermind ownership and immediate implementation boundary

A current-repository owner census changes how this research should be implemented. The Semiconductor Theme must **consume existing expectation, financial, temporal and market owners** rather than create a semiconductor-specific expectations database. Current Macro research architecture records the following capability states and ownership boundaries:

- Earnings Intelligence owns company-event, document, guidance and Q&A truth. Its event model already preserves `observed_at` and `source_available_at`; source documents have `fetched_at`, `published_at` and `available_at` clocks.
- Financial Intelligence Fabric owns governed financial facts and historical-cutoff query semantics. Its packet requires both source-event and system-recorded cutoffs for point-in-time work.
- Current analyst-revision snapshots are only `PARTIAL / ACCRUING`; they are useful prospectively from their observation-era birth, not as reconstructed historical consensus.
- Deep historical Street-consensus vintages are `NOT_BUILT` at the required depth. Public vendor research has identified candidate products, but record semantics, rights and licensed samples remain unaccepted.
- Common catalyst expectation semantics remain a future federation seam rather than a new Market-OS or GMI truth store. Market-incorporation research belongs to its existing Alpha/expectation owner; Semiconductor Themes must not originate a universal gap score.
- The current price estate has multiple adjustment bases/vintages and no accepted point-in-time corporate-action event store sufficient to pretend every historical adjusted-price comparison is clean. Price-reaction or re-rating analysis must consume a valid accepted market owner or degrade/refuse.

Canonical current repository references include `research/market_os/FISCAL_RESEARCH_OS_ARCHITECTURE_DELTA_2026-08-22.md`, `research/alpha_intelligence/expectation_market_dynamics/VEND_0_INSTITUTIONAL_ESTIMATES_BAKEOFF_2026-08-23.md`, `research/earnings_intelligence/g0/G0_EVENT_CLOCK_AND_CONTRACT_CENSUS.md`, `research/entry_stack/W4_EARNINGS_REACTION_PRIOR.md`, `research/MASTERMIND_TEMPORAL_DATA_STANDARD.md` and `research/MASTERMIND_DATA_SOURCE_CATALOG.md`. These are owner/interface evidence, not permission to revive their historical implementation proposals.

**Immediate research/product boundary:** management guidance vintages can be used as source-backed expectation observations when admitted through the existing event/evidence owners. Historical Street consensus must remain typed unavailable/unlicensed until an accepted owner supplies it. A semiconductor page may explain an issuer guide-to-actual or guide-to-new-guide transition; it may not invent historical consensus, interpolate a missing estimate history, or create a shadow consensus store. Likewise, the page can display accepted market observations through existing owners but cannot claim a clean historical re-rating attribution when the required point-in-time price/corporate-action basis is unavailable.

This narrows the first implementation slice usefully: **prove point-in-time management-guidance composition first; federate licensed consensus and incorporation evidence later through their native owners.**

## 4. Source-backed expectation vintages: why the contract matters

The following are dated examples. Percentages labeled **derived** are arithmetic from the cited issuer values; they are not consensus surprises, stock-return predictions or independent forecasts.

### 4.1 Foundry — TSMC: revenue can accelerate while margin guidance softens

TSMC's Q1 2026 result page reported actual Q1 revenue of **$35.90 billion** and Q2 guidance of **$39.0–40.2 billion**, with gross-margin guidance of **65.5–67.5%**. Its Q2 result subsequently reported **$40.20 billion** of revenue and **67.7%** gross margin, then guided Q3 revenue to **$44.6–45.8 billion** and gross margin to **65–67%**. Sources: https://investor.tsmc.com/english/quarterly-results/2026/q1 and https://investor.tsmc.com/english/quarterly-results/2026/q2 .

Derived observations:
- Q2 revenue finished approximately **1.52% above the prior range midpoint** of $39.6 billion and at the prior range high.
- The Q3 revenue-guide midpoint of $45.2 billion is approximately **12.44% above Q2 actual revenue**.
- Yet the Q3 gross-margin guide midpoint of 66% is below the Q2 actual 67.7%.

Research implication: a “revenue acceleration” thesis and a “margin expansion” thesis are separate. The product should expose the incremental revenue mechanism and the margin bridge instead of assuming they move together.

### 4.2 Fabless platform — NVIDIA: outlook assumptions are part of the number

NVIDIA's Q1 FY2027 release reported **$81.615 billion** of revenue and guided Q2 revenue to **$91.0 billion ±2%**, explicitly assuming **no Data Center compute revenue from China**. Q2 actual revenue was **$96.221 billion**, and the company guided Q3 to **$108.0 billion ±2%**, again with no China Data Center compute revenue assumed. Sources: https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027 and https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027 .

Derived observations:
- Q2 revenue was approximately **5.74% above the prior $91.0 billion guide point**.
- Q3 guide-point revenue is approximately **12.24% above Q2 actual revenue**.

The source also changed its non-GAAP presentation beginning in Q1 FY2027 by including stock-based compensation in non-GAAP measures. That definition change is itself time-series metadata. A historical non-GAAP margin/EPS comparison that ignores it can manufacture a false economic change.

### 4.3 Fabless platform — AMD: segment concentration changes the interpretation of company growth

AMD's Q1 2026 release guided Q2 revenue to **$11.2 billion ±$0.3 billion**. Q2 actual revenue was **$11.536 billion**, with Data Center revenue of **$6.718 billion** and management stating that Data Center represented 58% of company revenue. AMD then guided Q3 revenue to approximately **$13.0 billion ±$0.3 billion**. Sources: https://ir.amd.com/news-events/press-releases/detail/1284/amd-reports-first-quarter-2026-financial-results and https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000121/q22026991.htm .

Derived Q2 revenue was approximately **3.00% above the prior $11.2 billion guide point** if the exact reported $11.536 billion actual is used. The company also disclosed a material prior-year inventory/export-control charge in Q2 2025. The comparison therefore needs both current segment mix and prior-period exceptional-item treatment; “AI exposure” is not enough.

### 4.4 Custom/data infrastructure — Broadcom: subset guidance and company guidance are different objects

Broadcom's Q2 FY2026 release reported **$10.8 billion of AI semiconductor revenue** and forecast Q3 AI semiconductor revenue of **$16.0 billion**. Q3 actual AI semiconductor revenue was **$16.7 billion** and the company forecast Q4 AI semiconductor revenue of **$21.7 billion**; Q3 consolidated revenue was **$29.591 billion** and Q4 consolidated revenue was forecast at approximately **$34.8 billion**. Sources: https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial and https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial .

Derived observations:
- Q3 AI semiconductor revenue was **4.38% above the prior $16.0 billion forecast**.
- Q4 AI semiconductor revenue forecast is approximately **29.94% above Q3 actual AI semiconductor revenue**.

The AI subset must not be compared directly with total company growth without preserving infrastructure-software revenue and the subset denominator.

### 4.5 Custom/data infrastructure — Marvell: acquisitions and share-count mechanics can change the per-share bridge

Marvell's Q1 FY2027 release guided Q2 net revenue to **$2.700 billion ±5%**, while also disclosing that Q1 results included Celestial AI and XConn from their February acquisition dates. Q2 actual net revenue was **$2.739 billion**, $39 million above the prior midpoint, and Q3 revenue was guided to **$3.150 billion ±5%**. Q2 Data Center revenue was **$2.1715 billion**, 79% of total. The Q2 release also provides different basic/diluted share assumptions and notes Series A convertible preferred stock in EPS calculations. Sources: https://investor.marvell.com/sec-filings/all-sec-filings/content/0001835632-26-000014/q127_8kx522026ex-991.htm and https://investor.marvell.com/sec-filings/all-sec-filings/content/0001835632-26-000022/q227_8kx812026ex-991.htm .

Derived observations:
- Q2 revenue was approximately **1.44% above the prior guide midpoint**.
- Q3 guide midpoint is approximately **15.01% above Q2 actual revenue**.

Research implication: acquisition contribution, organic program ramp, and per-share denominator changes are separate. A revenue guide raise does not by itself establish the change in organic EPS power.

### 4.6 Memory — Nanya: revenue acceleration can be almost entirely price

Nanya's Q2 2026 release reported **68.2% sequential revenue growth**, **flat bit shipments**, and **average selling price growth above 60%**. Source: https://www.nanya.com/en/IR/16/Press%20Release?IRId=13150 .

This is a direct falsifier for any model that treats revenue growth as a volume proxy. Memory requires at least `bits shipped × price × product mix`, with inventory and capacity response layered on top. A price-led recovery can produce very different future supply and margin dynamics from a volume-led recovery.

### 4.7 Memory — Micron: product milestones and financial guide must coexist without becoming the same claim

Micron's fiscal Q3 2026 release guided fiscal Q4 revenue to **$50.0 billion ±$1.0 billion** and gross margin to approximately **86%**, while separately describing HBM4 high-volume shipments, HBM4E development and qualification samples for other products. Source: https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Results-for-the-Third-Quarter-of-Fiscal-2026/default.aspx .

The product milestones help explain mix/capacity hypotheses; they are not themselves the revenue guide. Mastermind should show the causal chain without turning a product qualification milestone into an invented financial contribution.

### 4.8 Equipment — ASML: installed-base revenue and new-system units are separate demand channels

ASML's Q1 2026 release guided Q2 net sales to **€8.4–9.0 billion** and full-year sales to **€36–40 billion**. Q2 actual sales were **€9.326 billion**, including **€2.762 billion of Installed Base Management sales**, with 86 new lithography systems sold. ASML then guided Q3 sales to **€11–12 billion** and raised full-year 2026 guidance to **€43–45 billion**. Sources: https://www.asml.com/en/news/press-releases/2026/q1-2026-financial-results and https://www.asml.com/en/news/press-releases/2026/q2-2026-financial-results .

Derived observations:
- Q2 actual sales were approximately **7.20% above the prior €8.7 billion midpoint**.
- The full-year midpoint rose from €38 billion to €44 billion, approximately **15.79%**.

But the source separately reports system units and Installed Base Management revenue. A model that interprets all upside as more scanner shipments loses the recurring service/upgrade channel.

### 4.9 Equipment — Lam Research: shipment does not always equal revenue

Lam's June 2026 quarter reported **$6.722 billion** revenue, of which **$4.250 billion** was systems revenue and **$2.472 billion** customer-support-related revenue and other. It guided the September quarter to **$8.10 billion ±$0.4 billion**. Lam also disclosed **$2.43 billion of deferred revenue**, and said shipments to customers in Japan remain inventory until customer acceptance, with approximately **$490.2 million** of estimated future revenue from such shipments at June 28. Source: https://investor.lamresearch.com/2026-07-29-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-June-28,-2026 .

Derived September guide midpoint is approximately **20.50% above June-quarter actual revenue**. Yet an installed machine, a shipment awaiting acceptance, systems revenue, deferred revenue and service revenue remain different states. This should be a regression requirement for the final data model.

### 4.10 Process control — KLA: per-share history must survive stock splits

KLA's fiscal Q4 2026 release reported **$3.658 billion** of revenue, above the prior midpoint, and guided the following quarter to **$4.0 billion ±$0.2 billion**. The release also says a **10-for-1 stock split** occurred on June 11, 2026 and that share/per-share information in the release was retroactively adjusted. Source: https://ir.kla.com/news-events/press-releases/detail/518/kla-corporation-reports-fiscal-2026-fourth-quarter-and-full .

A point-in-time system must distinguish the historical number investors saw before a split from a subsequently restated comparable series. Restatement enables comparison; it must not fabricate earlier source bytes or timestamps.

### 4.11 EDA — Cadence: guidance raises can cross an acquisition-perimeter boundary

Cadence's February 2026 initial FY2026 outlook guided revenue to **$5.9–6.0 billion** and explicitly **excluded the pending Hexagon Design & Engineering acquisition**. By Q2, Cadence guided FY2026 revenue to **$6.26–6.34 billion**, while its business highlights described continued integration of the Hexagon D&E business in System Design & Analysis. Sources: https://investor.cadence.com/news/news-details/2026/Cadence-Reports-Fourth-Quarter-and-Fiscal-Year-2025-Financial-Results/default.aspx and https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr-ir/2026/cadence-reports-second-quarter-2026-financial-results.html .

The simple midpoint increase from $5.95 billion to $6.30 billion is approximately **5.88%**, but **must not be labeled an organic guidance raise** without a same-perimeter bridge. This is a canonical acceptance case: apparently compatible metrics can be economically non-comparable because the company changed scope.

### 4.12 IP — Arm: royalties, license timing and KPI definitions are three separate clocks

Arm Q1 FYE27 reported **$715 million royalty revenue** and **$574 million license/other revenue**. Its SEC filing explains that most royalty revenue is accrued for the quarter in which customer products ship, using estimates that can be adjusted later when licensee reports arrive. It defines ACV as annualized committed license fees **excluding potential future royalties** and explicitly says ACV is not GAAP revenue. Beginning Q1 FYE27, Arm stopped reporting certain RPO/license-count metrics because it judged them less relevant as the business extends into production silicon. Source: https://investors.arm.com/node/8356/html .

The same filing shows Q1 revenue guidance of **$1.26 billion ±$50 million**, actual revenue of **$1.289 billion**, and Q2 guidance of **$1.38 billion ±$50 million**.

Derived observations:
- Q1 actual was approximately **2.30% above the prior midpoint**.
- Q2 guide midpoint is approximately **7.06% above Q1 actual**.

Research implication: the system needs metric-definition versioning. A disappearing KPI is not a zero, and ACV must never be added to royalty revenue as though both were recognized revenue.

### 4.13 EDA — Synopsys: acquisition-expanded business requires explicit perimeter tags

Synopsys' Q3 FY2026 release reported **$2.477 billion** of quarterly revenue and raised its full-year revenue expectation to a **$9.715 billion midpoint** and non-GAAP EPS to a **$15.07 midpoint**. Source: https://news.synopsys.com/2026-08-26-Synopsys-Posts-Financial-Results-for-Third-Quarter-Fiscal-Year-2026 .

The company operates after material acquisition-driven expansion. The required research principle is the same as Cadence: guidance and backlog comparisons must retain the reporting perimeter, rather than treating every increase as same-business organic acceleration.

### 4.14 Analog — Analog Devices: end-market acceleration and company acceleration are not synonymous

ADI guided fiscal Q3 2026 revenue to **$3.9 billion ±$0.1 billion**. Q3 actual revenue was approximately **$4.02 billion** and Q4 guidance was **$4.3 billion ±$0.1 billion**. Sources: https://www.analog.com/en/newsroom/press-releases/2026/5-20-2026-adi-reports-record-fiscal-second-quarter-2026-financial-results.html and https://www.analog.com/en/newsroom/press-releases/2026/8-19-2026-adi-reports-record-fiscal-3q2026-financial-results.html .

Derived observations:
- Q3 actual was approximately **3.13% above the prior $3.9 billion guide point**.
- Q4 guide midpoint is approximately **6.91% above Q3 actual revenue**.

ADI describes broad demand strengthening, but a mature analog model still needs end-market/channel inventory and mix; it should not mechanically call every recovery secular AI demand.

### 4.15 Power/analog — onsemi: segments can move in opposite directions during a company recovery

Onsemi's Q1 2026 release guided Q2 revenue to **$1.535–1.635 billion**. Q2 actual revenue was **$1.6035 billion** and Q3 guidance was **$1.650–1.750 billion**. But Q2 segment movements differed: Power Solutions Group was up 13% sequentially, Analog and Mixed-Signal Group up 1%, and Intelligent Sensing Group down 3%. Sources: https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-first-quarter-2026-results and https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-second-quarter-2026-results .

Derived observations:
- Q2 revenue was approximately **1.17% above the prior range midpoint**.
- Q3 guide midpoint is approximately **6.02% above Q2 actual**.

A company-level recovery label should therefore preserve the business that actually drives the change.

### 4.16 Broad analog — Texas Instruments: free cash flow definitions can differ materially

TI's Q2 2026 release reported revenue of **$5.463 billion** and Q3 guidance of **$5.65–6.15 billion**. It defines its reported free cash flow as cash flow from operations less capital expenditures **plus proceeds from U.S. CHIPS Act incentives**. Source: https://investor.ti.com/node/38476 .

That is a valid issuer-defined non-GAAP metric, but it is not identical to simple CFO minus capex. Both can be useful if labeled; substituting one silently for the other would distort cross-company cash comparisons.

### 4.17 Embedded/edge — NXP: growth narrative must retain share count and GAAP/non-GAAP bridges

NXP's Q2 2026 result guided Q3 revenue to a midpoint of **$3.750 billion** and supplied both GAAP and non-GAAP gross/operating margins, tax assumptions, non-controlling interests and a **254 million diluted-share assumption**. Source: https://investors.nxp.com/news-releases/news-release-details/nxp-semiconductors-reports-second-quarter-2026-results .

This is the correct level of detail for per-share expectation work. A revenue or edge-AI story does not reach EPS without the expense, tax, minority-interest and diluted-share bridge.

## 5. Re-rating mechanics: decompose rather than rank

For a positive forward-EPS company under a simple P/E representation:

`Price = forward EPS × forward P/E multiple`

and therefore:

`Price change factor = EPS revision factor × multiple change factor`.

This is an identity under the chosen representation, not a valuation recommendation. A 20% EPS increase paired with a 20% multiple decline gives `1.20 × 0.80 = 0.96`, or a 4% lower price. The example proves only that earnings improvement does not mathematically guarantee price appreciation.

For cash-flow or loss-making companies, a P/E representation may be inappropriate; use the existing accepted valuation owner and the metric appropriate to that company. Research should never force negative/near-zero EPS into a meaningless multiple.

### 5.1 What can change the expected EPS path?

- unit / bit / wafer / system volume;
- semiconductor content per end product;
- price / ASP / royalty rate;
- product and customer mix;
- market share and customer program timing;
- gross-margin mix, yields and factory utilization;
- service/installed-base contribution;
- R&D and go-to-market investment;
- depreciation and start-up costs;
- interest/tax/minority interests;
- share count, stock compensation, convertibles and repurchases;
- acquisitions/divestitures and accounting perimeter.

### 5.2 What can change the market multiple independently of EPS?

These are **research variables to observe**, not reasons to assign a higher/lower multiple mechanically:

- perceived duration and visibility of growth;
- cyclicality / inventory sensitivity;
- customer concentration and contract visibility;
- capital intensity and incremental return on invested capital;
- dependence on constrained or single-source inputs;
- competitive substitution and vertical integration risk;
- recurring versus transactional revenue composition;
- balance-sheet and dilution risk;
- regulatory/export/geographic exposure;
- confidence in the accounting/metric bridge;
- gap between current expectations and the next evidence needed to sustain them.

A price move around earnings does not prove which one caused the move. Causal claims about market reaction require an accepted point-in-time market-data/event-study owner and controls; this research does not create one.

## 6. Archetype-specific forward chains

### Foundry
`customer designs / end demand -> tape-outs and qualified process demand -> wafer starts/output -> utilization + node/package mix + price -> gross margin -> depreciation/capex/start-up costs -> operating cash -> diluted earnings -> expectation revision`

Key refusal: announced fab capacity is not realized revenue. A node mix shift is not automatically margin-positive if start-up and overseas costs dominate.

### Fabless/custom silicon
`program/design win -> customer platform schedule -> foundry/package allocation -> sellable units × ASP/content -> gross margin -> R&D/SBC/opex -> diluted shares -> EPS/FCF`

Key refusal: bookings or customer forecast is not recognized revenue; AI subset growth is not total-company growth; design win is not shipment.

### Memory
`end demand + inventory -> bits shipped × ASP × product mix -> revenue -> utilization/yield/node economics -> gross profit -> capex/supply response -> cash/EPS`

Key refusal: revenue growth is not bit growth; a technology transition can increase density and reduce wafer requirements per bit.

### Equipment/process control
`fab investment + process complexity -> orders/bookings -> shipment -> customer acceptance/revenue -> installed base -> service/upgrade revenue -> margin/FCF`

Key refusal: shipment can precede acceptance, and installed-base revenue has different recurrence than new-system units.

### EDA/IP
`design activity / complexity -> license/hardware bookings -> backlog/RPO/ACV -> recognized license/subscription revenue + customer shipment royalties -> R&D/SBC -> cash/EPS`

Key refusal: ACV/backlog/RPO are not revenue; license and royalty clocks differ; KPI definitions may change when the business model changes.

### Analog/power/embedded
`industrial/auto/communications/consumer demand -> customer/channel inventory -> bookings and shipments -> end-market/product mix -> factory utilization + price/cost -> margin -> capex/FCF -> EPS`

Key refusal: inventory replenishment is not necessarily final consumption; company recovery can be concentrated in one segment while others remain weak.

## 7. Proposed mechanism-based research collections

These are research filters for the existing Themes system, **not live portfolios, scores or weights**.

| ID | Research collection | Inclusion evidence | Key counterargument |
|---|---|---|---|
| ER01 | Same-perimeter guide acceleration | comparable current/prior management outlook with unchanged scope | acquisition, divestiture or definition change explains the increase |
| ER02 | Volume-led operating improvement | compatible unit/bit/wafer/system evidence plus revenue | price/mix alone explains sales growth |
| ER03 | Price/mix-led operating improvement | ASP/mix evidence plus compatible volume | higher price triggers supply response or demand destruction |
| ER04 | Utilization/absorption recovery | output/utilization plus margin bridge | one-time accounting or product mix dominates margin change |
| ER05 | Installed-base recurring growth | service/upgrade/maintenance evidence | service spike is non-recurring or tied to unusual upgrade cycle |
| ER06 | Royalty compounding | customer shipments, architecture/product mix, rate scope | unit weakness, estimation revisions or lower-rate mix offsets adoption |
| ER07 | License/backlog conversion | bookings/ACV/RPO plus revenue-recognition scope | large-contract timing or acquisition perimeter drives the change |
| ER08 | Program-ramp custom silicon | customer/program milestone plus manufacturing access | delay, customer concentration or vertical integration reduces capture |
| ER09 | Inventory replenishment | supplier shipments plus downstream inventory/sell-through evidence | sell-through fails to confirm durable final demand |
| ER10 | Capital-intensity transition | capex/start-up/depreciation and output evidence | capital rises before economically useful output |
| ER11 | Per-share improvement quality | compatible earnings/cash plus diluted-share bridge | dilution, convertibles or share-based compensation absorbs business growth |
| ER12 | Expectation-gap resolution | prior explicit expectation plus new discriminating evidence | evidence was already known or metric/perimeter is incomparable |

Research membership can be positive, negative or mixed. A company can legitimately appear in multiple collections with opposing channels. No extraction confidence becomes a financial weight.

## 8. Ten user journeys the shared Semiconductor Theme should eventually support

1. **What changed since the last earnings report?** Show prior management guide, actual, new guide, compatible derived deltas and the source timestamps.
2. **Was the improvement volume or price/mix?** Reconcile unit/bit/wafer/system measures with ASP and revenue, refusing the conclusion when a denominator is missing.
3. **Is the guide raise organic?** Surface acquisitions/divestitures/reporting-perimeter changes before calculating a same-business revision.
4. **Which business actually drives the company change?** Show subset/segment movement alongside the company total; do not let a theme label substitute for mix evidence.
5. **Is this shipment recognized revenue?** Preserve shipment, customer acceptance, deferred revenue and recognition separately.
6. **Is this recurring?** Split installed-base/service/royalty/subscription flows from new systems, licenses or one-time transactions.
7. **Did cash improve for the same reason earnings improved?** Reconcile working capital, customer advances, incentives, capex and issuer-specific FCF definitions.
8. **Did per-share economics improve?** Preserve diluted shares, splits, convertibles, repurchases and stock compensation instead of stopping at net income.
9. **What expectation was knowable on a historical date?** Use only sources/estimates published by that cut; do not backfill later results or revised definitions.
10. **What evidence would overturn the interpretation?** Pair every mechanism with the next discriminating observation and a plausible alternative explanation.

## 9. Forty-eight future acceptance requirements

All are **NOT_EXECUTED_PRODUCT_SPECIFICATIONS**. Offline editorial checks for this research artifact are not application tests.

### Point-in-time / source law
- **BEV-01** Later guidance cannot overwrite what was available at an earlier date.
- **BEV-02** Management, external consensus and house forecasts remain different owners.
- **BEV-03** Unknown publication time remains unknown; it is not rounded to midnight.
- **BEV-04** Superseded guidance remains historically readable with a link to its successor.
- **BEV-05** Source publication, fiscal period, business-effective period and system observation clocks remain distinct.
- **BEV-06** A revised/restated historical series does not imply the revised values were published historically.

### Metric compatibility
- **BEV-07** Guide/actual surprise requires compatible metric, period, currency and perimeter.
- **BEV-08** A derived midpoint is labeled derived, not issuer-reported.
- **BEV-09** Point guidance, tolerance guidance, range guidance and growth-rate guidance retain their native shapes.
- **BEV-10** GAAP and non-GAAP values are never silently mixed.
- **BEV-11** Non-GAAP definition changes are versioned and break naïve trend comparison.
- **BEV-12** Stock-split restatements preserve both comparable series and original publication lineage.
- **BEV-13** Issuer-specific free-cash-flow definitions retain their reconciliation.
- **BEV-14** Backlog, RPO, ACV, bookings, deferred revenue and recognized revenue remain distinct.
- **BEV-15** Segment/subset revenue is not company-total revenue.
- **BEV-16** Unit, bit, wafer, system and dollar growth remain separate measures.

### Business perimeter / ownership
- **BEV-17** Acquisition-affected guidance cannot be labeled organic without a bridge.
- **BEV-18** Divested business history retains its original owner and effective date.
- **BEV-19** Reporting segment reclassifications are versioned; prior periods are reconciled only when the issuer provides or an accepted owner derives a bridge.
- **BEV-20** Product/theme relevance cannot manufacture a revenue exposure percentage.
- **BEV-21** A security binding requires the native identity resolver; similar names do not establish it.
- **BEV-22** Joint ventures/minority interests and consolidated operations remain separate economic views.

### Revenue mechanics
- **BEV-23** Design win, booking, order, shipment, acceptance and recognized revenue are different states.
- **BEV-24** Customer forecast is not supplier recognized revenue.
- **BEV-25** A product qualification milestone cannot be assigned a financial contribution without evidence.
- **BEV-26** Systems and installed-base/service revenue remain separate.
- **BEV-27** License and royalty revenue clocks remain separate.
- **BEV-28** Royalty estimates can be corrected later without rewriting the historical estimate record.
- **BEV-29** Inventory replenishment is not automatically final-demand growth.
- **BEV-30** Revenue growth with flat units/bit shipments is not called volume growth.

### Margin / cash / per-share
- **BEV-31** Revenue acceleration does not imply gross-margin acceleration.
- **BEV-32** Utilization, yield, price and mix are separate margin drivers.
- **BEV-33** Customer advances and working-capital timing are not recurring profit.
- **BEV-34** Incentive proceeds are retained separately when an issuer includes them in a non-GAAP cash metric.
- **BEV-35** Capex, depreciation and asset reclassification remain distinct.
- **BEV-36** Net income cannot become per-share improvement without the diluted-share bridge.
- **BEV-37** Basic and diluted share assumptions retain their own scope.
- **BEV-38** Convertible/preferred instruments and stock compensation are not silently ignored in per-share research.

### Valuation / interpretation
- **BEV-39** EPS revision and multiple change remain separate components of a simplified P/E decomposition.
- **BEV-40** Negative or near-zero EPS companies are not forced into a P/E framework.
- **BEV-41** Price reaction does not establish causal attribution without an accepted event-study owner.
- **BEV-42** Research confidence is not valuation conviction or portfolio weight.
- **BEV-43** Technical importance is not pricing power without competitive/economic evidence.
- **BEV-44** A theme label is revised when another business becomes the actual marginal growth driver.

### Product / shared architecture
- **BEV-45** Research collections do not alter incumbent basket constituents, rankings, entries, sizing or trading outputs.
- **BEV-46** Current full-fidelity research uses the incumbent authenticated/private publication path; no public static leak.
- **BEV-47** The shared template provides an intelligible mechanism summary plus exact evidence; a source drawer alone is not completion.
- **BEV-48** A production release must prove one real source-to-visible-result journey with unchanged legacy behavior; schema/tests alone are insufficient.

## 10. Research QA: derived examples and falsifiers

The following calculations are intentionally limited and reproducible:

- TSMC Q2 midpoint surprise: `40.20 / 39.60 - 1 = 1.5152%`.
- TSMC Q3 guide midpoint sequential change: `45.20 / 40.20 - 1 = 12.4378%`.
- NVIDIA Q2 versus prior guide point: `96.221 / 91.0 - 1 = 5.7374%`.
- Broadcom Q3 AI actual versus prior Q3 AI forecast: `16.7 / 16.0 - 1 = 4.3750%`.
- Broadcom Q4 AI forecast versus Q3 actual: `21.7 / 16.7 - 1 = 29.9401%`.
- Marvell Q2 versus prior midpoint: `2.739 / 2.700 - 1 = 1.4444%`.
- ASML Q2 versus prior midpoint: `9.326 / 8.7 - 1 = 7.1954%`.
- ASML FY guide midpoint change: `44 / 38 - 1 = 15.7895%`.
- Lam September guide midpoint versus June actual: `8.10 / 6.722238 - 1 = 20.4956%`.
- Arm Q1 versus prior midpoint: `1.289 / 1.26 - 1 = 2.3016%`.
- Arm Q2 guide midpoint versus Q1 actual: `1.38 / 1.289 - 1 = 7.0597%`.
- ADI Q3 versus prior guide point: `4.021899 / 3.9 - 1 = 3.1256%`.
- ADI Q4 guide point versus Q3 actual: `4.3 / 4.021899 - 1 = 6.9147%`.
- onsemi Q2 versus prior midpoint: `1.6035 / 1.585 - 1 = 1.1672%`.
- onsemi Q3 midpoint versus Q2 actual: `1.7 / 1.6035 - 1 = 6.0181%`.
- A hypothetical +20% EPS and −20% multiple gives `1.2 × 0.8 − 1 = −4%` price change.

These arithmetic examples test definitions and data plumbing. They are not evidence that an issuer is mispriced, likely to beat, or likely to re-rate.

### Falsifiers the product must surface

- A guide raise attributed to “AI” can be falsified as an **AI-company-wide** explanation if a different segment or acquired business supplies the incremental revenue.
- A revenue recovery can be falsified as **volume-led** when units/bits are flat and price explains the change.
- A margin-expansion thesis can be falsified when start-up/depreciation/mix offsets the revenue ramp.
- A recurring-revenue thesis can be falsified when a large license/order/advance is timing-specific.
- A per-share compounding thesis can be weakened when diluted shares rise faster than net income.
- A multiple-expansion narrative is not established merely because price rose; an accepted expectations/market-data owner must show what information changed when.

## 11. Primary-source register

All sources were reviewed on 23 September 2026. `BODY` means relevant page text was inspected; it is not a whole-report audit or immutable-retention receipt. Duplicate publisher/release lineages are not independent corroboration. Sources already used in prior installments are deepened rather than counted as new independent evidence.

| ID | Publisher / period | Review | URL / role |
|---|---|---|---|
| E01 | TSMC / Q1 2026 | BODY | https://investor.tsmc.com/english/quarterly-results/2026/q1 — Q2 guide vintage |
| E02 | TSMC / Q2 2026 | BODY | https://investor.tsmc.com/english/quarterly-results/2026/q2 — Q2 actual / Q3 guide |
| E03 | NVIDIA / Q1 FY2027 | BODY | https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027 — Q2 outlook / reporting changes |
| E04 | NVIDIA / Q2 FY2027 | BODY | https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027 — actual / Q3 outlook |
| E05 | AMD / Q1 2026 | BODY | https://ir.amd.com/news-events/press-releases/detail/1284/amd-reports-first-quarter-2026-financial-results — Q2 outlook |
| E06 | AMD / Q2 2026 | BODY | https://ir.amd.com/financial-information/sec-filings/content/0000002488-26-000121/q22026991.htm — segment actual / Q3 outlook |
| E07 | Broadcom / Q2 FY2026 | BODY | https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial — AI subset forecast |
| E08 | Broadcom / Q3 FY2026 | BODY | https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial — AI/total actual + outlook |
| E09 | Marvell / Q1 FY2027 | BODY | https://investor.marvell.com/sec-filings/all-sec-filings/content/0001835632-26-000014/q127_8kx522026ex-991.htm — acquisition perimeter / Q2 guide |
| E10 | Marvell / Q2 FY2027 | BODY | https://investor.marvell.com/sec-filings/all-sec-filings/content/0001835632-26-000022/q227_8kx812026ex-991.htm — Q2 actual / Q3 guide / share assumptions |
| E11 | Nanya / Q2 2026 | BODY | https://www.nanya.com/en/IR/16/Press%20Release?IRId=13150 — ASP versus bits |
| E12 | Micron / FQ3 2026 | BODY | https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Results-for-the-Third-Quarter-of-Fiscal-2026/default.aspx — Q4 outlook / product milestones |
| E13 | ASML / Q1 2026 | BODY | https://www.asml.com/en/news/press-releases/2026/q1-2026-financial-results — Q2 + FY outlook |
| E14 | ASML / Q2 2026 | BODY | https://www.asml.com/en/news/press-releases/2026/q2-2026-financial-results — actual / installed base / raised FY outlook |
| E15 | Lam / June 2026 | BODY | https://investor.lamresearch.com/2026-07-29-Lam-Research-Corporation-Reports-Financial-Results-for-the-Quarter-Ended-June-28,-2026 — systems/service, acceptance, outlook |
| E16 | Applied Materials / Q3 FY2026 | BODY | https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-announces-third-quarter-2026-results — equipment economics comparator |
| E17 | KLA / Q4 FY2026 | BODY | https://ir.kla.com/news-events/press-releases/detail/518/kla-corporation-reports-fiscal-2026-fourth-quarter-and-full — process control, split-adjusted per-share data, guide |
| E18 | Arm / Q1 FYE27 | BODY | https://investors.arm.com/node/8356/html — license/royalty/ACV clocks and metric change |
| E19 | Cadence / FY2025 | BODY | https://investor.cadence.com/news/news-details/2026/Cadence-Reports-Fourth-Quarter-and-Fiscal-Year-2025-Financial-Results/default.aspx — initial 2026 outlook excludes pending acquisition |
| E20 | Cadence / Q2 2026 | BODY | https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr-ir/2026/cadence-reports-second-quarter-2026-financial-results.html — current outlook / integrated acquired business |
| E21 | Synopsys / Q3 FY2026 | BODY | https://news.synopsys.com/2026-08-26-Synopsys-Posts-Financial-Results-for-Third-Quarter-Fiscal-Year-2026 — raised outlook |
| E22 | ADI / Q2 2026 | BODY | https://www.analog.com/en/newsroom/press-releases/2026/5-20-2026-adi-reports-record-fiscal-second-quarter-2026-financial-results.html — Q3 outlook |
| E23 | ADI / Q3 2026 | BODY | https://www.analog.com/en/newsroom/press-releases/2026/8-19-2026-adi-reports-record-fiscal-3q2026-financial-results.html — actual / Q4 outlook |
| E24 | onsemi / Q1 2026 | BODY | https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-first-quarter-2026-results — Q2 guide / segment baseline |
| E25 | onsemi / Q2 2026 | BODY | https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-second-quarter-2026-results — segment divergence / Q3 guide |
| E26 | Texas Instruments / Q2 2026 | BODY | https://investor.ti.com/node/38476 — Q3 guide / FCF definition |
| E27 | NXP / Q2 2026 | BODY | https://investors.nxp.com/news-releases/news-release-details/nxp-semiconductors-reports-second-quarter-2026-results — GAAP/non-GAAP/share-count bridge |

## 12. What remains before the final Fable packet

This installment materially narrows the remaining principal research but does not complete it. Current owner boundaries are now known: do not create a semiconductor consensus, market-belief or price-history plane. The next work should:

1. **Run a bounded management-guidance point-in-time replay** across representative foundry, fabless/custom, equipment, EDA/IP and analog/power cases. This should prove the temporal/refusal rules using only issuer evidence available at each cut, while deliberately leaving unlicensed historical Street consensus unavailable.
2. **Resolve only material competitor/expectation holes** that could change the ontology, economic mechanism or first implementation slice; do not expand into an indiscriminate ticker census.
3. **Freeze the first native-owner vertical** around management-guidance composition plus the already researched industrial evidence. Historical consensus and causal market-incorporation remain federation dependencies on their existing owners.
4. **Write the semiconductor native-owner design specification** against current GMI/Earnings/FIF/K1/F04 interfaces, reusing the shared Robotics/Theme architecture with no new graph/store/queue/publisher.
5. After Chairman review of that written design, create the executable implementation plan and only then assemble the mature Fable CEO orchestration packet.

Fable should inherit the source-backed ontology, business-model rules, point-in-time expectation contract, explicit current-owner boundaries, implementation slices and proof requirements. It should not be asked to invent these from scratch.

`MISSION_COMPLETE: false`.