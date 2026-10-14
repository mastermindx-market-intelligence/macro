# Finance balance-sheet, credit and private-credit rerating research — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** RESEARCH / DESIGN PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Authority:** current Chairman directed continued principal research before any Fable CEO implementation handoff. This artifact grants no schema enrollment, graph write, basket admission, rank, recommendation, entry, sizing, trade, merge, deployment or worker commission.

## 0. Source and continuity boundary

- Protected procedure: `mastermindx-market-intelligence/Mastermind@bf764f494b9cd0ecede6234bb472c3344c8e77cc`.
- Skillpack: `mastermind.sol_skillpack.v1`, version `1.0.1`, bootstrap major `1` compatible.
- Loaded at that exact pin: `INDEX.md`, `COLD_START.md`, `ACTIVE_EXECUTION.md`, `WEB_CEO_DELEGATION.md`.
- Prior Finance checkpoint: PR #7786 head `35b5199c3ef1de1ff102002b1fe8b118ebac8e6d`.
- Original Macro research base retained: `668237947e016f679782e41e61c91c9133a5ea99`.
- Existing rates research remains an upstream context owner. The Finance program must not create a second rates engine, consensus store, valuation service, price-leadership plane or credit-data owner.
- Principal-duty reason: `PRINCIPAL_JUDGMENT`. No worker, Fable receiver, Executive Attempt or watcher was started.

This artifact continues the rerating-first correction in `FINANCE_RERATING_VALUATION_AND_PRICE_TRANSMISSION_2026-09-23.md`. It focuses on the places where Finance rerating is most often misread: banks, consumer lenders, auto finance, mortgage production/servicing, private-credit managers and BDCs.

## 1. Executive ruling

### R-FIN-BC-1 — Balance-sheet Finance is a multi-clock compounding problem

A bank or lender does not rerate because “rates rose,” “the curve steepened,” “credit improved,” or “deposits grew” in isolation. The stock rerates when the market changes its expectation for the durable relationship among:

```text
asset yield
− funding cost
− expected credit loss
− operating cost
− capital intensity
+ fee income
+ capital return
= per-share economic compounding
```

The correct question is:

> Is normalized return on tangible common equity moving above or below the required return, and can tangible book value per share compound without an unacceptable tail-risk, funding or dilution burden?

### R-FIN-BC-2 — Seven clocks remain separate

1. **Funding clock** — deposit mix, deposit repricing, wholesale funding, liquidity and stability.
2. **Asset-repricing clock** — variable-rate resets, fixed-rate maturation, securities reinvestment, loan growth and prepayment.
3. **Origination-vintage clock** — underwriting, borrower quality, collateral and price at origination.
4. **Credit-performance clock** — delinquency, roll rates, nonaccrual, charge-off, recovery and loss severity.
5. **Provisioning clock** — CECL assumptions, reserve builds/releases and acquisition accounting.
6. **Capital clock** — CET1, RWA, stress loss, capital return, acquisition use and regulatory change.
7. **Expectation/price clock** — consensus revisions, valuation, positioning, relative strength and breadth.

A favorable result on one clock can be offset by deterioration on another. No one-dimensional `BANKS_BENEFIT_FROM_HIGHER_RATES` or `RATE_CUTS_HELP_BANKS` state is valid.

### R-FIN-BC-3 — The valuation anchor is an economic identity, not a screen

For a stable clean-surplus balance-sheet business, the residual-income/Gordon relationship provides a useful conceptual anchor:

```text
P / tangible book ≈ (normalized ROTCE − sustainable growth)
                    / (cost of equity − sustainable growth)
```

This is not a production valuation formula. It makes the governing mechanism explicit:

- a durable increase in normalized ROTCE relative to cost of equity supports a higher P/TBV;
- higher sustainable per-share growth supports value only if the return on retained capital is adequate;
- greater tail risk, opacity or capital uncertainty raises the required return and can compress P/TBV even while current EPS rises;
- acquisition goodwill, AOCI, reserve changes and buybacks can cause book, tangible book, regulatory capital and economic value to diverge.

### R-FIN-BC-4 — Reported EPS is not normalized earning power

Reported earnings can be distorted by:

- reserve builds or releases;
- purchased-credit-deteriorated and acquisition-day-one CECL effects;
- securities gains/losses and balance-sheet repositioning;
- episodic advisory/trading fees;
- unusual deposit or funding movements;
- temporary floating-rate asset benefits;
- tax items;
- integration, restructuring and amortization;
- MSR marks and hedge results;
- realizations or performance fees;
- share issuance or repurchases.

The product must bridge from reported earnings to a source-bound normalized hypothesis rather than silently replacing reported facts.

### R-FIN-BC-5 — Private-credit managers and BDCs are different securities

A private-credit **manager** primarily monetizes fee-paying AUM, deployment, origination, fee rates, margins, performance economics and permanent-capital duration.

A **BDC or private-credit vehicle** owns loans and is primarily exposed to asset yield, nonaccruals, PIK, marks, leverage, funding cost, NAV/share, NII/share and dividend coverage.

The manager can grow while a vehicle’s credit quality deteriorates. A vehicle can report high current NII while future earnings and NAV are impaired. They require separate records, valuation anchors and price baskets.

### R-FIN-BC-6 — Bank/NDFI linkage is first-class

Banks finance mortgage intermediaries, consumer lenders, private-credit funds, BDCs, private-equity funds and other NDFIs through warehouse facilities, revolving lines, subscription facilities, NAV facilities, repo, derivatives, deposits and operating services.

That means “private credit takes share from banks” is incomplete. Banks may lose direct loan assets while gaining financing, treasury, syndication, origination, hedging and servicing economics—and may retain contingent liquidity and counterparty risk.

### R-FIN-BC-7 — Rerating is descriptive context, not trade authority

This framework may explain mechanisms, clocks, conflicts and watch conditions. It may not rank or size securities, change Prophet eligibility or create a credit-cycle trade state.

## 2. Balance-sheet earnings bridge

### 2.1 Core bank bridge

```text
average interest-earning assets × asset yield
− average interest-bearing liabilities × funding cost
= net interest income

net interest income
+ fee and other operating revenue
− operating expense
= pre-provision net revenue

pre-provision net revenue
− provision for credit losses
± realized/market/accounting items
− tax and preferred claims
= common net income

common net income / average tangible common equity
= ROTCE
```

Every line requires decomposition.

### 2.2 Net interest income is a balance and rate bridge

For each major asset and funding class:

```text
change in net interest income
= volume effect
+ rate effect
+ mix effect
+ day-count/other effect
```

A useful record distinguishes:

- loans, securities, cash/reserves and trading assets;
- noninterest-bearing, savings, money-market, time, brokered and wholesale funding;
- fixed versus floating exposures;
- contractual reset, expected maturity, prepayment and hedge effects;
- average balances from period-end balances.

### 2.3 Deposit franchise anatomy

The deposit franchise is not simply total deposits.

Required dimensions include:

- consumer, commercial, wealth, brokered and operational deposits;
- insured/uninsured where lawfully available;
- noninterest-bearing and interest-bearing mix;
- acquisition and divestiture effects;
- average and period-end balances;
- rate paid by product;
- digital, branch, treasury and relationship origin;
- concentration and runoff;
- reciprocal/brokered classification where relevant;
- liquidity and collateral requirements.

### 2.4 Deposit beta

Two different measures are needed.

```text
cumulative deposit beta
= change in deposit rate since cycle start
  / change in policy or reference rate since cycle start

incremental deposit beta
= current-period change in deposit rate
  / current-period change in reference rate
```

Rules:

- declare whether the numerator uses all deposits, interest-bearing deposits or a product cohort;
- a beta can be undefined when the reference-rate change is zero;
- falling-rate betas are not assumed to mirror hiking betas;
- mix migration can change the average deposit rate without repricing the same accounts;
- a low beta created by deposit runoff or replacement with wholesale debt is not automatically favorable;
- no fixed beta threshold becomes a universal rerating gate.

Existing rates research includes an external hypothesis that compression can emerge around a roughly 40% cumulative beta in some contexts. Finance treats that as a research prior requiring company/era validation, not a constant.

### 2.5 Asset repricing

The asset clock includes:

- floating-rate loan resets;
- floors and caps;
- fixed-rate loan maturation and new production;
- securities portfolio cash flows and reinvestment;
- hedges;
- prepayment and extension;
- nonaccrual migration;
- loan mix and growth.

A rate cut may lower variable loan yields immediately while deposit costs fall more slowly; later, lower funding costs and securities/loan growth may reverse the effect. A steep curve may help new production but can coexist with duration losses or weak demand.

## 3. Tangible book, capital and shareholder return

### 3.1 Tangible book value per share bridge

Conceptually:

```text
opening tangible common equity
+ common net income
− common dividends
± OCI / AOCI and other equity movements
− goodwill / intangible creation or amortization effects
± common issuance and repurchases
= ending tangible common equity

ending tangible common equity / ending common shares
= TBVPS
```

The actual issuer reconciliation controls.

### 3.2 Buyback law

All else equal:

- repurchasing below current TBVPS is arithmetically accretive to TBVPS;
- repurchasing above TBVPS is arithmetically dilutive to TBVPS;
- EPS accretion does not prove economic value creation;
- capital consumed, stress capacity, growth opportunity and future losses matter;
- stock compensation and issuance must be included in net share-count change.

### 3.3 Capital metrics

Keep distinct:

- common equity;
- tangible common equity;
- CET1 capital;
- standardized/advanced RWA;
- leverage exposure;
- stress capital buffer;
- LCR/NSFR and internal liquidity;
- distributable capital under the applicable constraint.

A high CET1 ratio can reflect constrained growth or elevated risk weights as well as strength. Capital release is a rerating mechanism only when the market believes excess capital can be returned or redeployed without weakening resilience.

### 3.4 Acquisition accounting

An acquisition can simultaneously:

- add loans, deposits, network or distribution;
- create goodwill and intangibles;
- trigger day-one CECL provision effects;
- change funding and credit mix;
- create integration expense and synergies;
- change regulatory capital and systemic importance;
- change share count and TBVPS.

Therefore pre/post comparisons require a bridge. Capital One’s Discover acquisition is an important current example: reported loan, deposit, provision and network changes cannot be interpreted as organic growth.

## 4. Credit-vintage and loss model

### 4.1 Origination cohort

Each origination vintage should preserve:

- product and channel;
- origination month/quarter;
- amount and account count;
- APR/yield and fee basis;
- credit score/risk band where available;
- LTV/DTI, collateral and term where applicable;
- geography;
- secured/unsecured state;
- dealer, merchant, partner or broker channel;
- underwriting model/rule version;
- promotional terms;
- acquisition or purchased-loan state.

### 4.2 Performance chain

```text
current
→ early delinquency
→ 30/60/90+ days past due
→ nonaccrual / default
→ charge-off
→ recovery
→ net loss and severity
```

The chain differs by product and accounting policy. Do not compare reported delinquency or charge-off rates without source definitions.

### 4.3 Leading and lagging variables

**Leading or early:**

- application and approval mix;
- origination volume and risk bands;
- payment rate;
- minimum-payment behavior;
- early delinquency/first-payment default;
- unemployment, income and debt-service conditions;
- collateral price and utilization;
- line utilization and drawdown;
- lending standards and demand.

**Coincident:**

- delinquency roll rates;
- criticized/classified loans;
- nonaccrual balances;
- modifications;
- reserve and provision.

**Lagging:**

- charge-offs;
- recoveries;
- realized loss severity;
- repossession/foreclosure resolution;
- restructurings and write-downs.

### 4.4 CECL and reserve interpretation

Provision is not the same as realized loss.

```text
ending allowance
= opening allowance
+ provision
− charge-offs
+ recoveries
± acquisitions, sales, FX and other adjustments
```

Rules:

- reserve release can raise earnings while future risk remains;
- reserve build can be prudent rather than evidence that realized loss has already occurred;
- allowance/loans must be read with mix, vintage, delinquency, collateral and macro assumptions;
- reserve/nonaccrual coverage is not comparable across products without loss severity and policy context;
- acquisition-day-one provisions remain separate from ordinary credit deterioration.

## 5. Rerating lifecycle for balance-sheet businesses

### Stage 1 — Stress recognition

Price discounts funding instability, unrealized losses, credit deterioration, regulatory risk or capital inadequacy. Reported earnings may still appear strong.

### Stage 2 — Stabilization

Deposit outflows slow, liquidity improves, delinquency acceleration moderates, marks stop worsening or capital uncertainty narrows. Price can turn before EPS.

### Stage 3 — Estimate trough

Provision, funding cost and expense estimates stop rising; forward EPS/TBVPS revisions stabilize. Risk discount may begin to contract.

### Stage 4 — Operating inflection

NII/fees improve, losses behave better than feared, efficiency improves or origination economics recover. Breadth should expand beyond one reported quarter.

### Stage 5 — Capital release

Stress capacity, CET1, retained earnings and confidence permit buybacks, dividends, growth or acquisitions. Capital action quality depends on price versus intrinsic/tangible value and opportunity cost.

### Stage 6 — Quality compounding

The market assigns a higher multiple to repeatable TBVPS/EPS growth, diversified fees, low tail loss, funding durability and disciplined capital allocation.

### Stage 7 — Overearning / late-cycle risk

Current returns are high but depend on unusually wide spreads, low losses, aggressive growth, reserve releases, elevated transaction activity or asset marks. EPS can rise while the multiple compresses.

The lifecycle is descriptive. It does not determine a trade or probability.

## 6. Subtheme rerating maps

### 6.1 Universal and money-center banks

**Primary anchors:** normalized ROTCE, TBVPS growth, P/TBV and P/E; segment SOTP for material fee/market businesses.

**Earnings drivers:**

- deposit/funding economics;
- consumer/commercial loan balances and spreads;
- payments, custody, wealth and asset management;
- investment banking, markets and trading;
- card credit;
- expense/productivity;
- capital/RWA.

**Rerating conditions:**

- normalized ROTCE exceeds cost of equity with low tail-risk;
- TBVPS compounds after dividends and buybacks;
- fee diversification lowers dependence on one rate/credit outcome;
- capital uncertainty falls;
- market/IB recovery is broad and not offset by rising credit/funding cost.

**De-rating conditions:**

- current returns judged peak-cycle;
- higher capital/RWA or regulatory burden;
- deposit competition, duration or liquidity stress;
- credit losses rise faster than PPNR;
- opaque marks or operational/legal risk;
- capital return consumes resilience.

### 6.2 Regional and community banks

**Primary anchors:** P/TBV, normalized ROTCE, TBVPS growth, deposit-franchise durability, capital and concentration risk.

**Rerating conditions:**

- deposits stabilize or grow without expensive replacement;
- fixed-rate asset/securities repricing improves NIM;
- CRE and other concentration risks become quantifiable and contained;
- AOCI/duration concerns shrink relative to capital and liquidity;
- provision/loss estimates stop rising;
- fee revenue and expense discipline improve;
- M&A creates credible per-share value rather than only scale.

**De-rating conditions:**

- deposit beta/mix migration overwhelms asset yield;
- uninsured/concentrated funding remains fragile;
- CRE/consumer losses emerge after optimistic reserve assumptions;
- securities duration or wholesale funding impairs flexibility;
- weak organic growth encourages value-destructive acquisition;
- stock appears cheap only because normalized ROTCE remains below cost of equity.

### 6.3 Closed-loop card network and lender

American Express is structurally different from an open-loop network and from a pure revolving lender.

**Bridge:**

```text
billed business × discount revenue yield
+ net card fees and services
+ loan balances × net interest yield
− rewards/benefits/marketing
− credit losses
− funding and operating cost
= pre-tax earnings
```

**Rerating conditions:** spending/account growth, premium-customer retention, fee growth, stable credit, operating leverage and disciplined capital return.

**De-rating conditions:** reward inflation, weaker spend/mix, credit normalization, funding pressure, regulation or a weaker membership value proposition.

### 6.4 Partner/private-label card lender

**Bridge:**

```text
purchase volume and active accounts
→ loan receivables through payment rate/utilization
→ loan yield and fees
− retailer/partner share, rewards and loyalty
− funding cost
− credit losses
− operating expense
```

**Rerating conditions:** partner additions, improving receivable growth, pricing/mix, falling funding cost and charge-off normalization without sacrificing future growth.

**De-rating conditions:** merchant concentration, lost programs, underwriting pullback, worsening payment behavior, regulation of fees, rising rewards/partner economics or funding stress.

### 6.5 Auto finance

**Bridge:**

```text
origination volume × risk-adjusted yield
+ commercial/dealer and insurance economics
− deposit/securitization funding
− credit loss and recovery severity
− residual-value risk for leases
− operating expense
```

**Leading indicators:** approval/origination mix, used-vehicle prices, early delinquency, recoveries, payment burden, dealer inventory and funding mix.

**Rerating conditions:** better vintages season, recoveries improve, funding is durable, yield covers losses/capital and originations grow without quality slippage.

### 6.6 Mortgage originator and servicer

**Production bridge:**

```text
lock/origination volume × gain-on-sale margin
+ origination/fulfillment fees
− fulfillment, compensation, hedging and funding cost
```

**Servicing bridge:**

```text
servicing UPB × servicing-fee yield
+ ancillary/recapture economics
± MSR valuation and hedge results
− amortization/prepayment
− advances, default servicing and operating cost
```

Rate declines can help refinance volume while reducing MSR value and accelerating amortization. A balanced producer/servicer needs both clocks visible.

### 6.7 Private-credit manager

**Primary anchors:** fee-related earnings, distributable/adjusted income, fee-paying AUM, permanent-capital share, AUM not yet paying fees, fundraising, deployment, margins and net flows.

**Bridge:**

```text
fee-paying AUM × effective management-fee rate
+ fee-related performance / origination / capital-solutions fees
− compensation and operating cost
= fee-related earnings

+ realized performance/principal/spread economics where applicable
= distributable or adjusted earnings
```

**Rerating conditions:** organic FPAUM growth, deployment converts shadow AUM to fees, permanent capital extends duration, FRE margins scale, credit performance supports fundraising and fee rates remain durable.

**De-rating conditions:** acquisition-driven headline AUM without per-share accretion, delayed deployment, fee compression, redemption/liquidity pressure, performance weakness, insurance/spread complexity or credit losses that impair franchise confidence.

### 6.8 BDC / listed private-credit vehicle

**Primary anchors:** NAV/share, NII/share, dividend coverage, P/NAV, nonaccruals, marks, leverage and funding maturity.

**Bridge:**

```text
average earning assets × asset yield
− debt × funding cost
− base/incentive fees and operating cost
− credit loss / nonaccrual drag
= NII

NII ± realized/unrealized change
− distributions ± issuance/repurchase effects
= NAV/share change
```

**Rerating conditions:** stable/growing NAV, dividend coverage, low nonaccruals, disciplined leverage, funding duration and access, accretive issuance above NAV or buybacks below NAV, and credible underwriting.

**De-rating conditions:** PIK masks weak cash collection, nonaccruals/marks rise, dividend exceeds sustainable NII, leverage/funding cost rises, issuance dilutes NAV, manager conflicts or portfolio concentration surprises.

### 6.9 Bank/NDFI financing linkage

Track:

- warehouse and revolver commitments;
- drawn balances and utilization;
- collateral and advance rates;
- subscription/NAV facilities;
- repo and securities financing;
- derivatives and margin;
- deposits/treasury services;
- syndication, securitization and distribution;
- contingent liquidity obligations;
- concentration by borrower class.

The July 2026 SLOOS reported that bank standards for multiple NDFI categories were at the tighter ends of historical ranges since 2011. That is a funding-condition observation, not proof of NDFI defaults or a trade signal.

## 7. Current system-state observations

These are dated context, not forecasts.

- The July 2026 SLOOS reported basically unchanged C&I standards, stronger demand from large and middle-market borrowers, some easing in CRE standards, tighter credit-card standards, weaker residential-mortgage and auto demand, and historically tight standards for queried NDFI lending categories.
- The Federal Reserve’s August 7, 2026 G.19 release reported that consumer credit grew at a 2.6% annualized rate in 2026Q2, with revolving credit up 3.9% and nonrevolving credit up 2.1%; seasonally adjusted total consumer credit was approximately $5.167 trillion in June.
- The FDIC reported for 2025Q4 that industry NIM reached 3.39%, domestic deposits grew for a sixth consecutive quarter and annual loan growth reached 5.9%, while some CRE and consumer delinquency measures remained elevated.

These observations show why the credit state must not be compressed into `EASING` or `TIGHTENING`: business credit demand strengthened, consumer standards remained restrictive, mortgage/auto demand weakened and NDFI financing conditions remained tight.

## 8. Macro and market transmission matrix

| Shock or regime | First transmission | Potential beneficiaries | Potential losers / offsets | Required confirmation |
|---|---|---|---|---|
| Policy cuts, soft landing | deposit costs, asset yields, demand, securities marks | liability-sensitive banks, mortgage production, selected lenders | floating-rate asset yield, MSR marks, weaker spread income | company rate bridge, beta, volume, credit |
| Policy cuts, recession | same plus defaults and weak demand | high-quality funding, servicing/collections, defensive fee businesses | cards, consumer/CRE, weakly funded lenders | labor, delinquencies, reserves, demand |
| Bear steepening / higher long yields | new asset yields, duration marks, funding and mortgage affordability | cash-rich/new-money investors, some insurers/lenders | duration-heavy banks, mortgage demand, levered credit | AOCI, liquidity, prepayment, funding |
| Bull steepening | lower front-end funding and better term spread | selected banks and originators | severe credit deterioration can dominate | NII bridge plus loss estimates |
| Credit-spread widening | funding, marks, issuance and origination | new-money private credit with dry powder | BDC NAV, levered borrowers, weak funding | actual deployment, defaults, marks |
| Unemployment rise | consumer delinquencies and losses | collections/servicing in bounded cases | cards, auto, unsecured and subprime credit | vintage roll rates, charge-offs, reserves |
| Used-car decline | recoveries and loss severity | new borrowers if affordability improves | auto lenders/lessors with weak vintages | auction/recovery and vintage data |
| Housing turnover/refi rebound | originations, gain-on-sale and recapture | mortgage originators, title/data, servicing recapture | MSR value can fall with prepayment | volume, margin, MSR hedge result |
| Capital relief | buyback, growth and M&A capacity | banks/BDCs with excess capital and sound credit | none automatically; poor allocation can destroy value | capital rule, stress, price vs book |

## 9. Product requirements

### 9.1 Finance dossier balance-sheet module

Show the following separately:

1. funding and deposit bridge;
2. asset-repricing bridge;
3. credit-vintage and loss bridge;
4. reserve/provision bridge;
5. capital/TBVPS bridge;
6. current expectations and revisions;
7. valuation anchor;
8. price-recognition conflict;
9. exact evidence and limitations.

### 9.2 Company card

A useful card answers:

```text
What funds the business?
What assets or risks earn the return?
What is repricing first?
Which vintages are seasoning?
Where do losses appear first?
What capital constraint is binding?
What is the correct per-share anchor?
What would justify a multiple change?
What is market price already recognizing?
```

### 9.3 Required conflict states

- `NII_UP_CREDIT_DOWN`
- `EPS_UP_TBVPS_FLAT_OR_DOWN`
- `TBVPS_UP_ROTCE_BELOW_COST_OF_EQUITY`
- `LOSSES_STABLE_RESERVES_FALLING`
- `VOLUME_UP_UNIT_ECONOMICS_DOWN`
- `AUM_UP_FEE_PAYING_CONVERSION_WEAK`
- `NII_UP_NAV_DOWN`
- `PRICE_LEADS_FUNDAMENTALS`
- `FUNDAMENTALS_IMPROVE_PRICE_DIVERGES`

These are explanatory display states, not scores or trade signals.

## 10. Historical evaluation design

### 10.1 Bank rerating episode unit

Each episode should include:

- source-known date and observation vintage;
- company and business mix;
- funding/deposit state;
- asset-repricing state;
- credit-vintage and loss state;
- reserve and capital state;
- current consensus revisions;
- P/TBV and P/E using point-in-time estimates;
- 1/3/6/12-month total return and relative return;
- change in TBVPS, ROTCE and consensus EPS;
- maximum drawdown and tail event;
- later restatement/correction.

### 10.2 Required cohorts

- 1994–95, 1999–2000, 2004–06, 2015–18 and 2022–26 rate cycles where data permit;
- large/universal versus regional/community;
- card/consumer versus commercial/CRE-heavy;
- mortgage production-heavy versus servicing-heavy;
- private-credit manager versus BDC;
- acquisition and non-acquisition periods.

### 10.3 Nulls and anti-leakage

- do not use later charge-offs to label the entry date as if known;
- do not backfill later revised consensus or membership;
- keep failed reratings and survivorship failures;
- separate macro relief from company-specific alpha;
- record whether price led the evidence;
- do not convert one historical average into a production threshold.

## 11. Research source register

Primary public sources used in this tranche include:

- Federal Reserve Board, July 2026 Senior Loan Officer Opinion Survey on Bank Lending Practices, published 3 August 2026: `https://www.federalreserve.gov/data/sloos/sloos-202607.htm`.
- Federal Reserve Board, Consumer Credit G.19, June 2026 data, released 7 August 2026: `https://www.federalreserve.gov/releases/g19/20260807/`.
- FDIC, Quarterly Banking Profile 2025Q4, released 24 February 2026: `https://www.fdic.gov/news/press-releases/2026/fdic-insured-institutions-reported-return-assets-124-percent-and-net`.
- JPMorgan Chase 2025 Form 10-K: `https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm`.
- PNC 2025 Form 10-K / annual report: `https://investor.pnc.com/sec-filings/all-sec-filings/content/0000713676-26-000020/pnc-20251231.htm`.
- U.S. Bancorp 2026 Q1/Q2 filings: `https://www.sec.gov/Archives/edgar/data/36104/000003610426000024/usb-20260331.htm`, `https://www.sec.gov/Archives/edgar/data/36104/000003610426000044/usb-20260630.htm`.
- Truist 2025 Form 10-K and 2026 Q2 filing: `https://www.sec.gov/Archives/edgar/data/92230/000009223026000030/tfc-20251231.htm`, `https://www.sec.gov/Archives/edgar/data/92230/000009223026000099/tfc-20260630.htm`.
- Capital One 2025 Form 10-K and 2026 Q2 filing: `https://www.sec.gov/Archives/edgar/data/927628/000092762826000024/cof-20251231.htm`, `https://www.sec.gov/Archives/edgar/data/927628/000092762826000089/cof-20260630.htm`.
- American Express filings and investor releases: `https://www.sec.gov/Archives/edgar/data/4962/000000496226000121/axp-20260316.htm` and issuer results.
- Synchrony 2025 Form 10-K and 2026 Q2 filing: `https://www.sec.gov/Archives/edgar/data/1601712/000160171226000006/syf-20251231.htm`, `https://www.sec.gov/Archives/edgar/data/1601712/000160171226000033/syf-20260630.htm`.
- Ally 2025 Form 10-K and 2026 filings: `https://www.sec.gov/Archives/edgar/data/40729/000004072926000005/ally-20251231.htm`.
- Rocket 2026 Q2 filing and results: `https://www.sec.gov/Archives/edgar/data/1805284/000162828026054577/rkt-20260630.htm`.
- PennyMac Financial Services 2025 Form 10-K: `https://www.sec.gov/Archives/edgar/data/1745916/000110465926018142/pfsi-20251231x10k.htm`.
- Ares Management 2025 Form 10-K and 2026 Q2 presentation: `https://www.sec.gov/Archives/edgar/data/1176948/000162828026011413/ares-20251231.htm`, `https://www.sec.gov/Archives/edgar/data/1176948/000162828026051191/a2026q2-ex992earningspre.htm`.
- Apollo 2025 Form 10-K and results: `https://www.sec.gov/Archives/edgar/data/1858681/000185868126000013/apo-20251231.htm`.
- Blue Owl filings and 2026 results: `https://www.sec.gov/Archives/edgar/data/1823945/000182394526000022/blueowlearningsdeck33126.htm`.
- Ares Capital and Blue Owl Capital Corporation results and filings.

## 12. Explicit non-claims

This document does not claim:

- a complete global bank/credit census;
- that current estimates or market multiples have been integrated;
- that the seven-clock model is prospectively validated;
- an approved normalized-earnings series;
- an approved credit, capital or rerating score;
- that a deposit beta, loss rate or capital ratio has one universal threshold;
- basket membership or security attractiveness;
- product implementation, tests, CI, deployment or browser proof.

## 13. Exact next action

Build a primary-source company/business census for the representative bank, consumer-credit, mortgage and private-credit entities named in this tranche, followed by a credit metric/vintage dictionary and a portable research-only assertion packet. Preserve business, issuer, security, economic role, credit population, clock, unit, denominator, reported/derived status and source limitation separately. Do not create the final Fable CEO handoff yet.
