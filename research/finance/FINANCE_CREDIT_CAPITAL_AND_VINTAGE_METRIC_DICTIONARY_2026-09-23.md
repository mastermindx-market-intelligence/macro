# Finance credit, capital and vintage metric dictionary — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** RESEARCH CONTRACT PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Scope:** semantic, clock, denominator, derivation and evidence requirements for banks, consumer lenders, auto finance, mortgage, private-credit managers and BDCs.  
**Authority:** this is not an enrolled production contract, accepted graph vocabulary, canonical credit store, valuation model, ranking input or trade signal.

## 0. Outcome

The user should be able to compare balance-sheet and credit businesses without being misled by quantities that share a name but not an economic meaning.

The machine must prevent errors such as:

- comparing period-end deposits with average loans to infer an unsupported loan-to-deposit ratio;
- calling deposit growth favorable without showing cost, mix, acquisition and runoff;
- comparing a bank’s net charge-off rate with a BDC’s nonaccrual percentage as if they measured the same loss process;
- treating provision as realized loss;
- treating allowance coverage as comparable across cards, CRE, mortgages and first-lien private credit;
- treating PIK income as equivalent to cash interest;
- treating AUM, fee-paying AUM and permanent capital as the same fee base;
- treating mortgage origination volume, locks, applications and servicing UPB as interchangeable;
- annualizing one quarter’s gain-on-sale margin, provision or performance fee as normalized earnings;
- treating CET1, tangible common equity and distributable capital as one quantity;
- calling an acquisition-driven balance increase organic growth;
- using a later charge-off or restatement as if it had been known at the original observation date.

The product therefore needs a closed semantic dictionary and comparison law. It does **not** need a universal Finance score.

## 1. Controlling laws

### D-FIN-CR-01 — Source-native fact survives normalization

Every metric retains:

- the issuer/regulator’s native name;
- exact definition or lawful paraphrase;
- document and locator;
- business/population scope;
- period and as-of date;
- unit, currency and annualization;
- gross/net and stock/flow class;
- reported/derived/estimated state;
- correction and supersession state.

A normalized family aids comparison. It never overwrites the native fact.

### D-FIN-CR-02 — Average and period-end balances never silently mix

NIM, asset yields and funding costs ordinarily use average balances. Capital ratios, deposit snapshots, allowance and many portfolio measures are period-end. A derived ratio must use matched bases or explicitly state the approximation and refusal status.

### D-FIN-CR-03 — Organic, acquired and disposed changes remain separate

A balance or revenue change requires decomposition where material:

```text
organic volume
+ acquisition / portfolio purchase
− divestiture / run-off
+ FX
+ price / rate
+ mix
+ accounting / classification
= reported change
```

Unknown components remain unknown.

### D-FIN-CR-04 — Credit state is cohort-specific

Product, origination vintage, borrower risk, geography, collateral, channel and underwriting regime remain part of the observation key. A company-wide average cannot silently describe every cohort.

### D-FIN-CR-05 — Provision, allowance and realized loss remain distinct

Provision is an income-statement flow. Allowance is a balance-sheet stock. Charge-off and recovery are realized flows. None substitutes for another.

### D-FIN-CR-06 — Regulatory capital is not common equity

CET1 capital, risk-weighted assets, tangible common equity, GAAP common equity, leverage exposure and distributable/excess capital remain separately sourced.

### D-FIN-CR-07 — Cash and noncash credit income remain distinct

Cash interest, original-issue discount accretion, PIK, fee amortization, amendment fees and realized gains remain separate. Noncash income cannot silently support a cash-dividend conclusion.

### D-FIN-CR-08 — Current yield does not determine total return

High loan, card, BDC or mortgage yield may compensate for loss, funding, duration, capital or liquidity risk. Yield enters through a complete risk-adjusted bridge.

### D-FIN-CR-09 — Null states are typed

At minimum:

- `NOT_DISCLOSED`
- `NOT_APPLICABLE`
- `NOT_COMPARABLE`
- `DEFINITION_CHANGED`
- `POPULATION_CHANGED`
- `RIGHTS_RESTRICTED`
- `SOURCE_UNAVAILABLE`
- `NOT_YET_OBSERVED`
- `DERIVATION_REFUSED`

No null becomes zero.

### D-FIN-CR-10 — Dictionary semantics grant no analytical authority

The dictionary makes facts comparable and prevents false claims. It does not decide quality, attractiveness, expected return, rank, position or action.

## 2. Proposed metric-assertion envelope

```text
metric_assertion_id
schema_version
native_metric_name
normalized_metric_family
metric_subtype
issuer_id
business_id
vehicle_or_fund_id_optional
security_id_optional
product_or_portfolio_scope
customer_or_borrower_scope
geography
currency
source_id
source_locator
source_definition_excerpt_or_paraphrase
source_family
publication_at
observed_at
period_start
period_end
as_of_date
business_effective_at_optional
knowledge_cutoff
value
value_low_optional
value_high_optional
unit
measurement_class
balance_basis
annualization_basis
gross_net_basis
cash_noncash_basis
reported_derived_estimated
formula_optional
numerator_ref_optional
denominator_ref_optional
comparison_key
organic_acquired_fx_price_mix
coverage
quality_state
review_state
rights_state
limitations
predecessor_assertion_id_optional
supersession_reason_optional
```

### 2.1 Measurement classes

Closed initial vocabulary:

- `BALANCE_STOCK`
- `PERIOD_FLOW`
- `POINT_IN_TIME_RATE`
- `PERIOD_AVERAGE_RATE`
- `COUNT`
- `VOLUME_VALUE`
- `NOTIONAL`
- `MARKET_VALUE`
- `NET_EXPOSURE`
- `RATIO`
- `PER_SHARE_VALUE`
- `REGULATORY_RATIO`
- `RUN_RATE`
- `CONTRACTED_NOT_RECOGNIZED`
- `ESTIMATE_OR_GUIDANCE`

### 2.2 Balance bases

- `PERIOD_END`
- `PERIOD_AVERAGE_DAILY`
- `PERIOD_AVERAGE_MONTHLY`
- `PERIOD_AVERAGE_QUARTERLY`
- `WEIGHTED_AVERAGE`
- `SOURCE_DEFINED_AVERAGE`
- `NOT_APPLICABLE`
- `UNKNOWN`

### 2.3 Annualization bases

- `NOT_ANNUALIZED`
- `ACTUAL_FULL_YEAR`
- `ANNUALIZED_QUARTER`
- `ANNUALIZED_MONTH`
- `RUN_RATE_SOURCE_DEFINED`
- `TRAILING_TWELVE_MONTHS`
- `UNKNOWN`

## 3. Identity and clock grammar

### 3.1 Identities that must not collapse

- legal issuer;
- bank subsidiary;
- broker-dealer, insurer or regulated subsidiary;
- reportable segment;
- lending product;
- portfolio/cohort/vintage;
- fund or BDC vehicle;
- external manager;
- security/listing;
- acquired portfolio and acquisition close event.

### 3.2 Required clocks

- source publication time;
- source observation/retention time;
- period start/end;
- balance as-of date;
- origination/vintage date;
- delinquency/default/charge-off/recovery date;
- reserve-recognition date;
- acquisition close and accounting-effective date;
- rule announcement and effective date;
- manager fundraising, deployment and fee-activation date;
- valuation mark date;
- consensus estimate vintage;
- price observation date.

A page-level `as of` cannot collapse these clocks.

### 3.3 Corrections

A restatement, changed definition, resegmentation, acquisition presentation or corrected filing appends a new assertion linked to its predecessor. Historical readers retain both the originally known and corrected states where lawful.

## 4. Deposit and funding metrics

### 4.1 Total deposits

**Normalized family:** `DEPOSITS_TOTAL`  
**Class:** balance stock.  
**Required scope:** bank subsidiary/consolidated, geography, customer type if disclosed, period-end or average.

Do not infer quality from total growth alone.

### 4.2 Average deposits

**Family:** `DEPOSITS_AVERAGE`  
**Class:** average balance stock.

Required for deposit-cost and NII rate/volume bridges when supplied. Period-end deposits cannot substitute without an explicit approximation refusal/qualification.

### 4.3 Noninterest-bearing deposits

**Family:** `DEPOSITS_NONINTEREST_BEARING`.

Required fields:

- amount;
- share of total/average deposits where derived;
- business/customer mix;
- acquisition and seasonal effects;
- average versus period-end basis.

### 4.4 Interest-bearing deposit classes

Initial subtypes:

- demand/transaction;
- savings;
- money market;
- time/CD;
- brokered;
- reciprocal;
- sweep;
- wealth/brokerage cash;
- other source-defined.

Do not infer stability from product label alone.

### 4.5 Deposit cost

**Family:** `DEPOSIT_COST`  
**Class:** period-average rate.

Required denominator:

- all deposits;
- interest-bearing deposits;
- or a specific product cohort.

These rates are not comparable unless the denominator matches.

### 4.6 Spot deposit rate

A current or end-period offered/paid rate is different from the average-period deposit cost. Preserve both when available.

### 4.7 Cumulative deposit beta

```text
(change in source-defined deposit rate since cycle start)
/
(change in selected reference rate since cycle start)
```

Required fields:

- cycle-start date;
- reference rate identity;
- deposit-rate denominator;
- acquisition/mix treatment;
- sign and zero-denominator handling.

### 4.8 Incremental deposit beta

```text
current-period change in deposit rate
/
current-period change in selected reference rate
```

May be volatile or undefined. Do not substitute cumulative beta.

### 4.9 Down-cycle deposit beta

Rate cuts may reprice products asymmetrically. Hiking-cycle beta does not imply cutting-cycle beta. The cycle direction is part of the comparison key.

### 4.10 Wholesale funding

Subtypes include:

- FHLB advances;
- senior debt;
- subordinated debt;
- securitization;
- repo;
- brokered deposits;
- commercial paper;
- secured facilities;
- other source-defined.

Required observations: average and period-end balance, cost, maturity, collateral, unused capacity and liquidity treatment where disclosed.

### 4.11 Deposit runoff and migration

Separate:

- customer outflow;
- movement from noninterest-bearing to interest-bearing;
- movement into time deposits;
- movement into brokerage/wealth products within the same group;
- seasonal change;
- acquisition/divestiture;
- reclassification.

## 5. Asset, yield, NII and NIM metrics

### 5.1 Interest-earning assets

Subtypes:

- loans by portfolio;
- securities by classification/type;
- cash/reserves;
- trading assets;
- federal funds/reverse repo;
- other source-defined.

Required basis: average for yield calculations, period-end for balance-sheet exposure.

### 5.2 Loan balance

Preserve:

- held for investment;
- held for sale;
- fair-value option;
- purchased/acquired;
- PCD/non-PCD where reported;
- gross/net of unearned income and allowance;
- commitments versus funded loans.

### 5.3 Loan originations

**Family:** `LOAN_ORIGINATIONS`  
**Class:** period flow.

Required dimensions: product, channel, vintage, amount/count, purchase/organic, retained/sold, risk band and pricing where available.

### 5.4 Asset yield

**Family:** `ASSET_YIELD`  
**Class:** average rate.

Required denominator: average source-defined asset population. Cash yield, contractual yield, effective yield and taxable-equivalent yield remain distinct.

### 5.5 Funding cost

Preserve deposit, wholesale and total interest-bearing-liability cost separately.

### 5.6 Net interest income

**Family:** `NET_INTEREST_INCOME`  
**Class:** period flow.

Required source treatment:

- GAAP versus taxable-equivalent;
- reported versus adjusted;
- acquisition day count;
- hedge/accounting effects;
- discontinued operations.

### 5.7 Net interest margin

```text
annualized net interest income
/
average interest-earning assets
```

Use the issuer/regulator’s exact definition. Required fields:

- numerator basis;
- denominator basis;
- annualization/day-count;
- taxable-equivalent adjustment;
- acquired/discontinued business treatment.

### 5.8 NII rate/volume/mix bridge

Where issuer-supplied, preserve native categories. A derived bridge requires matched average balances/rates and a declared interaction allocation. Refuse when inputs are insufficient.

### 5.9 Interest-rate sensitivity

Projected NII or economic-value sensitivity is an issuer-modeled estimate, not a realized fact.

Required:

- shock/path shape;
- instantaneous/ramp treatment;
- horizon;
- balance-sheet static/dynamic assumption;
- deposit beta/decay assumptions;
- prepayment;
- floors/caps;
- hedges;
- source date.

Never compare two sensitivity values without aligned assumptions.

### 5.10 Securities duration and unrealized value

Preserve:

- AFS versus HTM;
- amortized cost versus fair value;
- gross unrealized gain/loss;
- duration/weighted life where disclosed;
- AOCI treatment;
- hedges;
- liquidity/pledging state;
- capital treatment.

Unrealized loss is not automatically an economic loss, but funding/liquidity can force realization or raise required return.

## 6. Origination and credit-vintage metrics

### 6.1 Vintage identity

Minimum key:

```text
issuer / business
product
origination quarter or month
channel
geography
risk band
collateral/secured state
term
acquired/organic
underwriting/model regime
```

Unknown fields remain null.

### 6.2 Applications, approvals and bookings

Keep separate:

- application count/value;
- approved count/value;
- booked/originated count/value;
- funded amount;
- retained versus sold;
- commitment versus draw.

### 6.3 Borrower risk attributes

Examples:

- FICO/credit score and source/version;
- internal risk grade;
- LTV/CLTV;
- DTI;
- debt-service coverage;
- income verification;
- collateral type/value;
- sponsor/leverage metrics;
- covenant/structure.

Averages, medians, weighted averages and bands remain distinct.

### 6.4 Pricing

Separate:

- contractual APR/coupon;
- effective yield;
- fees;
- promotional period;
- OID/discount;
- floor/cap;
- benchmark spread;
- expected loss and capital charge where derived.

### 6.5 Payment rate

Common in card lending. Required definition:

- payments during period divided by average or beginning receivables/purchases, as source-defined;
- product/cohort scope;
- charge/reversal treatment.

Payment rate affects receivable conversion, interest income and credit signals.

### 6.6 Utilization

Credit-line utilization requires drawn balance and committed/available line with matched population/date. Revolving utilization is not comparable to term-loan drawdown.

## 7. Delinquency, default and loss metrics

### 7.1 Delinquency

Subtypes:

- 30+ days past due;
- 60+;
- 90+;
- source-native stages;
- current-to-delinquent roll rate;
- cure rate;
- first-payment default.

Required denominator: accounts, balances or exposure. Count and balance rates remain separate.

### 7.2 Nonperforming and nonaccrual assets

Preserve issuer/regulatory definition, product scope, balance basis and whether acquired/PCD assets are treated differently.

### 7.3 Criticized/classified loans

Internal/regulatory categories require source definitions and cannot be equated mechanically with nonaccrual/default.

### 7.4 Gross charge-offs

**Class:** period flow.  
Required product and denominator for rates.

### 7.5 Recoveries

Keep cash recoveries and other source-defined recoveries separate where disclosed.

### 7.6 Net charge-offs

```text
gross charge-offs − recoveries
```

### 7.7 Net charge-off rate

Issuer/regulator definition controls. Required denominator commonly average loans/receivables, with annualization. Period-end loans cannot silently substitute.

### 7.8 Loss severity

```text
net realized loss
/
defaulted exposure or repossessed/foreclosed balance
```

Only where numerator/denominator and recovery horizon are aligned.

### 7.9 Nonaccrual for BDCs/private credit

Required bases:

- fair value;
- cost;
- number of investments;
- source date;
- cash versus PIK status;
- partial nonaccrual treatment.

A BDC nonaccrual percentage is not directly comparable to bank NPL or card delinquency.

### 7.10 PIK income

Required fields:

- PIK income recognized in period;
- cash interest separately;
- portfolio/counterparty scope;
- accrued balance where available;
- conversion/collection/restructuring state;
- source date.

PIK is neither zero nor cash.

## 8. Provision and allowance metrics

### 8.1 Provision for credit losses

Separate:

- funded loans;
- unfunded commitments;
- securities/other financial assets;
- acquisition/day-one CECL;
- source-defined components.

### 8.2 Allowance for credit losses

**Class:** period-end balance stock.

Required reconciliation:

```text
opening allowance
+ provision
− charge-offs
+ recoveries
± acquisitions / sales / FX / transfers / other
= ending allowance
```

### 8.3 Allowance-to-loans ratio

Requires gross loan/receivable denominator at the same date/population. Product mix and purchased-credit treatment remain visible.

### 8.4 Allowance-to-nonaccrual coverage

May be displayed only with aligned definitions and explicit limitations. It is not a universal adequacy test.

### 8.5 Reserve build/release

Derived change must distinguish:

- portfolio growth/mix;
- macro assumption;
- credit migration;
- charge-off/recovery;
- acquisition;
- model/methodology;
- management qualitative adjustment.

Unknown attribution stays unknown.

### 8.6 CECL economic interpretation

CECL is expected-loss accounting under source assumptions. It is not a calibrated forecast produced by Mastermind. The product displays assumptions, changes and later outcomes without treating reserve size as probability truth.

## 9. Common-equity, tangible-book and capital metrics

### 9.1 Common equity

Issuer-native GAAP common shareholders’ equity.

### 9.2 Tangible common equity

Issuer/regulator reconciliation controls. Required deductions and minority/preferred treatment must be sourced.

### 9.3 Book value per share

```text
common equity / common shares outstanding
```

Use issuer-reported value when available; a derived value requires matched date and share class.

### 9.4 Tangible book value per share

```text
tangible common equity / common shares outstanding
```

Do not use weighted-average diluted shares from an income-statement period for period-end TBVPS.

### 9.5 ROTCE

Issuer definition controls. Preserve:

- numerator adjustments;
- average tangible-equity denominator;
- annualization;
- reported/adjusted state;
- period.

### 9.6 CET1 capital and ratio

```text
CET1 capital / risk-weighted assets
```

Required rule basis: standardized, advanced, transitional, fully phased-in or source-defined.

### 9.7 Risk-weighted assets

Keep credit, market, operational and other components if disclosed. RWA change can reflect balance growth, mix, model, regulation or optimization.

### 9.8 Leverage ratio

Required rule/denominator identity. Do not compare directly with CET1 ratio.

### 9.9 Stress capital buffer and stress losses

Rule vintage, scenario, effective period and firm-specific result remain bound. Regulatory stress is not a company forecast.

### 9.10 Payout ratio

Possible numerators:

- common dividends;
- repurchases;
- total common distributions.

Possible denominators:

- reported net income;
- adjusted income;
- distributable earnings;
- capital generation.

The product must state which.

### 9.11 Buyback TBVPS arithmetic

A deterministic scenario may estimate per-share arithmetic if it has:

- repurchase dollars/shares;
- repurchase price;
- pre-buyback tangible common equity and shares;
- no omitted material equity effects.

It remains an arithmetic scenario, not proof of intrinsic-value accretion.

## 10. Card and consumer-finance metrics

### 10.1 Purchase volume / billed business

Period flow. Preserve network/issuer/merchant/customer scope, FX basis and cash-advance treatment.

### 10.2 Card loans/receivables

Period-end and average balances remain separate. Purchased/acquired balances and securitized/retained treatment must be explicit.

### 10.3 Active accounts/cards/credentials

Counts require activity definition and period. Cards, accounts and credentials are not interchangeable.

### 10.4 Net interest yield / receivable yield

Issuer-defined. Required average receivable denominator and fee/charge-off treatment.

### 10.5 Rewards, partner and merchant payments

Keep rewards/benefits, network incentives, merchant/retailer share and loyalty expenses separately where disclosed. Gross purchase volume does not establish net monetization.

### 10.6 Card credit clocks

Required display when available:

- payment rate;
- 30+ and 90+ delinquency;
- net charge-off rate;
- reserve coverage;
- origination/risk mix;
- utilization;
- unemployment and borrower stress;
- funding cost.

## 11. Auto-finance metrics

### 11.1 Consumer auto originations

Preserve new/used, prime/nonprime or risk band, term, APR/yield, channel/dealer, retained/sold and vintage.

### 11.2 Commercial/dealer finance

Separate from retail auto loans. Floorplan utilization, dealer inventory and collateral dynamics differ.

### 11.3 Lease assets and residual values

Preserve:

- original residual assumption;
- current estimated residual;
- depreciation;
- off-lease volume;
- gain/loss on sale;
- used-vehicle price/recovery source.

### 11.4 Repossession/recovery

Required unit/count/value, timing and expense basis. Auction value is not recovery net of costs unless stated.

## 12. Mortgage-production and servicing metrics

### 12.1 Applications, locks and originations

Each is a different stage/population. Required period, amount/count and channel.

### 12.2 Pull-through

```text
closed/funded originations
/
locked volume
```

Only with matched cohort/period and source treatment.

### 12.3 Gain-on-sale margin

Issuer definition controls. Required numerator/denominator and inclusion of hedge/other production revenue.

### 12.4 Servicing UPB

**Class:** balance stock.  
Required owned/subserviced state, product type, geography and as-of date.

### 12.5 Servicing fee yield

Requires servicing-fee revenue and average serviced UPB with matched population. Gross fee is not net servicing profitability.

### 12.6 MSR fair value

Required:

- UPB population;
- fair value;
- valuation multiple/price where source-defined;
- prepayment, discount-rate, servicing-cost and delinquency assumptions;
- hedge result separately;
- period/as-of date.

### 12.7 Recapture/retention

Issuer-native definition, eligible population and measurement window are mandatory.

### 12.8 Advances and default servicing

Keep principal/interest, tax/insurance and other advances separately where disclosed. Advance financing/liquidity is part of the economics.

## 13. Private-credit-manager metrics

### 13.1 Assets under management

Issuer-native AUM definition. Required strategy, acquisition, FX/market/deployment and period.

### 13.2 Fee-paying / fee-generating AUM

FPAUM and FGAUM remain issuer-native labels until mapped. Fee base, rate and activation conditions are required.

### 13.3 Permanent capital

Required legal/vehicle definition, redemption/liquidity features and fee duration. “Permanent” does not mean risk-free or irrevocable under every condition.

### 13.4 AUM not yet paying fees / shadow AUM

Required activation event, expected/unknown timing and rights. This is contracted or committed potential, not recognized revenue.

### 13.5 Fundraising and inflows

Keep gross fundraising, net flows, commitments and acquisitions separate.

### 13.6 Deployment

Required gross/net, strategy, retained/syndicated state, timing and fee activation. Deployment is not automatically revenue or performance.

### 13.7 Management fees

Recognized period revenue. Required relationship to average fee base and effective fee rate where derived.

### 13.8 Fee-related earnings

Issuer-defined non-GAAP measure. Required reconciliation, excluded items and period.

### 13.9 Spread-related earnings

Separate from FRE. Required asset, liability, capital and insurance/retirement perimeter.

### 13.10 Distributable/adjusted net income

Issuer-defined. Required reconciliation and per-share/share-count basis. Do not compare across managers without definition alignment.

### 13.11 Performance income/carry

Keep accrued, realized and cash state separate. Do not annualize episodic realizations as recurring FRE.

## 14. BDC and credit-vehicle metrics

### 14.1 Investment portfolio at fair value and cost

Both are period-end stocks. Unrealized difference does not establish final loss/recovery.

### 14.2 Gross asset yield

Required average portfolio denominator and cash/PIK/fee composition.

### 14.3 Debt/funding cost

Preserve secured/unsecured, fixed/floating, maturity and average/period-end debt.

### 14.4 Net investment income

Issuer-reported GAAP and adjusted NII remain separate. Per-share values require the appropriate weighted-average shares.

### 14.5 Dividend coverage

```text
NII/share or cash-adjusted income/share
/
regular dividend/share
```

The chosen numerator must be named. One quarter does not establish sustainability.

### 14.6 NAV per share

Period-end NAV/common share. Share issuance/repurchases and distributions must be included in the bridge.

### 14.7 Leverage

Required definition: debt/equity, regulatory asset coverage or issuer-defined. Do not mix.

### 14.8 Nonaccrual

Required fair-value and cost basis, portfolio population and source date.

### 14.9 PIK share

Possible denominators: total investment income, interest income or portfolio yield. The product must state which.

### 14.10 Issuance/repurchase relative to NAV

Required transaction price, contemporaneous NAV/share, fees and share count. A price above/below NAV is arithmetic context, not automatic value creation/destruction.

## 15. Derived metric library and refusal rules

### 15.1 Loan-to-deposit ratio

```text
period-end loans / period-end deposits
```

or

```text
average loans / average deposits
```

The basis must match. Cross-basis derivation refuses.

### 15.2 Deposit-mix shares

```text
specified deposit class / matched total deposit denominator
```

Acquisition and average/end basis visible.

### 15.3 NIM spread decomposition

Only when matched yields/costs and average balances exist. Do not derive from period-end balances.

### 15.4 Pre-provision net revenue

Issuer/regulator definition preferred. A derived value must state included revenue/expense and adjustments.

### 15.5 Risk-adjusted revenue proxy

A research-only bridge may show:

```text
net interest/fee revenue
− net charge-offs or expected loss
− direct funding/partner/reward cost
```

It must not be called profit without operating expense, capital and tax.

### 15.6 ROTCE minus cost of equity

Cost of equity is an estimate from an accepted valuation owner, not a reported fact. Until supplied, the spread is unavailable.

### 15.7 P/TBV and P/NAV

Require contemporaneous security price and period/date-aligned per-share anchor. Stale book values remain visibly dated.

### 15.8 Growth decomposition

Growth rate alone does not establish level/materiality. Require start/end levels and organic/acquired/FX/price/mix where available.

### 15.9 Refusal examples

Refuse rather than fabricate when:

- average denominator is absent;
- acquisition changed population without a bridge;
- native definitions changed;
- period/as-of dates mismatch materially;
- gross and net bases conflict;
- source-native populations differ;
- current price/consensus owner is unavailable;
- rights prevent source display;
- one term has no validated identity binding.

## 16. Comparability matrix

| Native concepts | Comparison state | Reason |
|---|---|---|
| period-end deposits vs average deposits | related, not equal | stock snapshot versus period average |
| all-deposit cost vs interest-bearing-deposit cost | not directly comparable | denominator differs |
| NIM across banks | comparable only after definition review | taxable-equivalent, asset and annualization differences |
| bank NCO rate vs BDC nonaccrual | not comparable | realized flow versus status stock and different populations |
| allowance/loans across cards and CRE | context only | product duration/loss severity differ |
| card purchase volume vs receivables | not equal | transaction flow versus credit stock |
| mortgage locks vs originations | related, not equal | pipeline versus funded output |
| servicing UPB vs MSR fair value | related, not equal | underlying balance versus asset valuation |
| AUM vs FPAUM/FGAUM | related, not equal | total managed versus fee-paying base |
| permanent capital vs FPAUM | overlapping, not equal | duration/legal feature versus fee base |
| AUM not paying fees vs ARR/backlog | not equal | investment commitments versus software run-rate/contract |
| BDC NII vs manager FRE | not comparable | vehicle spread income versus management operating earnings |
| TBVPS vs CET1 ratio | not comparable | shareholder anchor versus regulatory ratio |
| EPS accretion vs TBVPS accretion | separate | income/share versus balance-sheet value/share |

## 17. Evidence hierarchy

### Tier A — regulatory/statutory

Examples: Call Reports, FR Y-9C, FDIC QBP, Federal Reserve releases/SLOOS, SEC filings, BDC Investment Company Act disclosures, insurance/statutory sources.

### Tier B — issuer primary

Annual/quarterly filings, earnings releases, supplements, presentations and contractual/fee documents.

### Tier C — accepted owner derivations

Matched formulas with source refs, clocks, denominators and revision identity.

### Tier D — attributed research candidates

Secondary research, news and model extraction. These do not self-ratify accepted current facts.

## 18. User-facing display grammar

Every metric displayed to an investor should answer:

```text
What exactly is measured?
For which business, product and population?
Is it a stock, flow, rate, count or estimate?
What is the period/as-of date?
Is it average or period-end?
Is it gross or net?
Is it cash or noncash?
Is it reported, derived or estimated?
What denominator and definition apply?
Did acquisition, FX, price or mix change the population?
What does the source prove—and not prove?
```

### 18.1 Finance company-card labels

Prefer plain labels with technical detail in evidence:

- “Deposits and funding”
- “Asset repricing”
- “New credit and borrower mix”
- “Early stress”
- “Realized losses”
- “Reserve and provision”
- “Capital and tangible book”
- “What the market expects”
- “Valuation anchor”
- “Price recognition”

### 18.2 No misleading reassurance

Missing/stale/incomparable data cannot render as stable, low risk or zero. A green price state cannot hide unavailable credit/funding evidence.

## 19. Deterministic validation requirements

A future accepted implementation should test at least:

1. required source, identity, period, unit and measurement-class fields;
2. no null-to-zero coercion;
3. stock/flow and average/end basis consistency;
4. numerator/denominator period and population alignment;
5. annualization declaration;
6. gross/net and cash/noncash compatibility;
7. acquisition/population-change state;
8. native definition retention;
9. formula whitelist and operand references;
10. finite numeric values and range sanity;
11. correction/supersession links;
12. no inferred security join without validated identity;
13. no analytic/ranking fields in the semantic assertion;
14. no public emission of rights-restricted full-fidelity payloads;
15. unchanged behavior for legacy evidence without Finance payloads.

## 20. Research-only assertion-packet requirements

The first portable packet should include, for every company/business record:

- issuer/business/security identity state;
- exact source and locator;
- one or more source-native operating assertions;
- funding, credit, capital and per-share-anchor observations where available;
- explicit metric dictionary bindings;
- source publication and business clocks;
- reported versus derived state;
- limitations and comparison state;
- no current valuation, rank or trade output.

It must remain a research artifact until the incumbent evidence, identity, rights and publisher owners accept a native contract.

## 21. Explicit non-claims

This dictionary does not establish:

- a complete credit-data ontology;
- one comparable normalized series across every company;
- accepted production schemas or stores;
- current source admission or private retention;
- normalized earnings or expected loss;
- valuation or cost of equity;
- prospective predictive power;
- product implementation, tests, CI, deployment or browser proof.

## 22. Exact next action

Build the portable research-only assertion packet for the representative company/business census using this dictionary. Then continue principal research into asset management, wealth, insurance and risk-transfer rerating, including their distinct flow, fee, underwriting, reserve, duration and capital clocks. Do not create the final Fable CEO handoff until the research program, product design, schemas, vertical plan and acceptance criteria are mature.
