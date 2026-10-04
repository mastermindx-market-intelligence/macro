# Finance first-vertical metric and evidence dictionary — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** RESEARCH CONTRACT PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Scope:** metric semantics, comparability, clocks, derivations and evidence requirements for Money Movement and Securities Infrastructure.  
**Authority:** this is not an enrolled schema or permission to write accepted graph/evidence data. No ranking, valuation conclusion, basket admission, trade or production publication is authorized.

## 0. Outcome

The user should be able to compare financial businesses without being misled by superficially similar quantities.

The machine must prevent errors such as:

- comparing Visa-branded transactions with Visa-processed transactions as though they were the same population;
- comparing gross payment volume with net processing revenue;
- comparing exchange gross revenue with revenue net of transaction rebates/pass-throughs;
- treating AUC/A, AUM and index-linked assets as equivalent fee bases;
- treating ARR, recurring revenue, remaining performance obligations and recognized revenue as interchangeable;
- treating a mandate win, ACV booking or contracted backlog as current revenue;
- treating gross interest earned on clearing collateral as retained earnings;
- comparing period-end asset values with average-period fee bases;
- treating acquisition, FX, price and organic growth as one undifferentiated rate.

The product therefore needs a **closed semantic dictionary with explicit non-equivalence rules**, not a universal Finance metric table.

## 1. Controlling laws

### D-FIN-01 — Every number carries its population

A metric without a subject, product, geography, customer population or transaction population is incomplete.

### D-FIN-02 — Every number carries its measurement class

Required distinctions include:

```text
stock vs flow
period-end vs period-average
count vs value
notional vs market value vs net exposure
reported vs derived vs estimated
GAAP vs non-GAAP
recognized vs contracted vs billed vs collected
organic vs acquired vs FX vs price vs mix
```

### D-FIN-03 — Gross and net bases never silently mix

Rebates, incentives, interchange, network fees, pass-through costs, brokerage/clearing fees, interest distributions and partner payments may cause gross and net amounts to describe different economics.

### D-FIN-04 — Similar labels remain issuer-native until mapped

`payment volume`, `GDV`, `TPV`, `GPV`, `processed transactions`, `switched transactions`, `AUC/A`, `ARR` and `recurring revenue` retain the issuer's definition and source locator. A normalized family is a comparison aid, not a rewrite of the native fact.

### D-FIN-05 — Denominator and period must match a derived ratio

Do not divide a quarterly revenue numerator by a year-end stock, a gross numerator by a net denominator, or a global numerator by a regional denominator.

### D-FIN-06 — An annualized value is not a full-year observation

ARR and annualized SaaS are run-rate constructs defined by the reporting issuer. They do not become recognized annual revenue merely because the unit is “per year.”

### D-FIN-07 — Current levels and growth rates remain separate observations

A 10% growth rate without the level, period and basis cannot establish scale or materiality.

### D-FIN-08 — Null is not zero

Unavailable, not disclosed, not applicable, rights-restricted and not comparable are separate null states.

### D-FIN-09 — Corrections append

A changed filing, restatement, taxonomy, acquisition presentation or source definition creates a superseding assertion. It does not erase the prior source-native observation.

### D-FIN-10 — Dictionary semantics have no analytical authority

A normalized metric makes evidence comparable. It does not decide whether the level is good, bad, attractive, predictive or tradable.

## 2. Proposed record envelope

```text
metric_assertion_id
schema_version
native_metric_name
normalized_metric_family
issuer_id
business_id
product_or_workflow_scope
security_id_optional
source_id
source_locator
source_definition_excerpt_or_paraphrase
publication_at
observed_at
period_start
period_end
as_of_date
business_effective_at_optional
value
value_low_optional
value_high_optional
unit
currency_optional
measurement_class
stock_flow_class
time_basis
gross_net_basis
recognition_basis
reported_derived_estimated
accounting_basis
organic_acquired_fx_price_mix_bridge
numerator_definition_optional
denominator_definition_optional
geography
customer_or_transaction_population
consolidation_scope
precision
review_state
limitations[]
supersedes_optional
authority_caps
```

### 2.1 Closed field families

**Measurement class**

```text
COUNT
MONETARY_VALUE
PERCENTAGE
RATE
RATIO
MARGIN
MULTIPLE
DURATION
OTHER_DECLARED
```

**Stock/flow class**

```text
PERIOD_END_STOCK
PERIOD_AVERAGE_STOCK
PERIOD_FLOW
POINT_EVENT
RUN_RATE
COHORT_OR_VINTAGE
NOT_APPLICABLE
```

**Gross/net basis**

```text
GROSS
NET_OF_REBATES
NET_OF_INCENTIVES
NET_OF_PASS_THROUGHS
NET_OF_DISTRIBUTED_INTEREST
NET_OF_CREDIT_LOSSES
OTHER_EXPLICIT
NOT_APPLICABLE
UNKNOWN
```

**Recognition basis**

```text
RECOGNIZED_REVENUE
BILLED
CASH_COLLECTED
CONTRACTED
BACKLOG_OR_RPO
MANDATE_ANNOUNCED
MANDATE_INSTALLED
ANNUALIZED_RUN_RATE
OPERATING_ACTIVITY
BALANCE_SHEET
OTHER_EXPLICIT
```

**Reported/derived/estimated**

```text
ISSUER_REPORTED
REGULATOR_REPORTED
HOUSE_DERIVED
THIRD_PARTY_ESTIMATED
ATTRIBUTED_INTERPRETATION
```

## 3. Money-movement metric families

### 3.1 Payment value

#### `PAYMENT_VALUE_BRANDED`

Value of payments carrying a stated network/brand over a defined period, whether or not every transaction was processed by that network.

Required fields:

- brand/network;
- purchase versus cash inclusion;
- geography/currency convention;
- local/constant/reported currency;
- period;
- gross/refund treatment;
- issuer definition.

Never assume branded payment value is the same as processed payment value or issuer receivables.

#### `PAYMENT_VALUE_PROCESSED`

Value actually processed by the reporting platform/network under its stated definition.

Do not infer this from branded volume unless the issuer states the processing share.

#### `GROSS_DOLLAR_VOLUME`

Issuer-native payment-network activity measure. Preserve debit/credit/cash and local-currency definitions.

Mastercard GDV and Visa payments/cash volume may be placed in a common **network activity family** for navigation, but remain distinct source-native metrics.

#### `MERCHANT_GROSS_PAYMENT_VOLUME`

Merchant-platform value processed for merchant clients. Required population includes merchant cohort, geography, acquired portfolio treatment and refund/cash treatment.

A merchant processor's GPV/TPV is not directly comparable with a card network's global branded volume.

### 3.2 Transaction counts

#### `BRANDED_TRANSACTION_COUNT`

Transactions carrying a brand/network designation, including transactions processed by other networks where the source definition does so.

#### `PROCESSED_TRANSACTION_COUNT`

Transactions actually processed by the reporting platform.

#### `SWITCHED_TRANSACTION_COUNT`

Transactions routed/switched through the reporting network. State whether domestic, cross-border or both and whether cash transactions are included.

#### `MONEY_MOVEMENT_TRANSACTION_COUNT`

Transactions through a distinct transfer platform such as push-to-card/account/wallet. Preserve endpoints and use cases.

**Non-equivalence law:**

```text
branded ≠ processed ≠ switched ≠ settled ≠ money-movement transfer
```

One transaction may participate in several stages but cannot be added across stages as independent volume.

### 3.3 Cross-border activity

#### `CROSS_BORDER_PAYMENT_VALUE`

Required dimensions:

- issuer country versus merchant/beneficiary country rule;
- intra-region exclusion such as intra-Europe treatment;
- constant/local/reported currency;
- travel versus e-commerce where available;
- value versus transaction count;
- gross versus net/refund basis.

Cross-border growth is often economically important because monetization differs from domestic activity, but no universal take-rate assumption is permitted.

### 3.4 Credentials, endpoints, merchants and clients

Separate:

- issued credentials/accounts;
- active credentials/accounts;
- merchant locations;
- merchants/legal entities;
- acceptance endpoints;
- network endpoints including accounts/cards/wallets;
- financial-institution clients;
- platform partners;
- active users or businesses.

A potential reachable endpoint is not an active user, merchant or revenue-generating relationship.

### 3.5 Payment revenue families

#### `NETWORK_SERVICE_REVENUE`

Issuer-defined service/assessment economics commonly linked to payment volume or credentials.

#### `PROCESSING_REVENUE`

Issuer-defined processing/switching/data-processing revenue commonly linked to processed/switched transactions.

#### `INTERNATIONAL_TRANSACTION_REVENUE`

Issuer-defined cross-border/currency-related economics.

#### `VALUE_ADDED_SERVICES_REVENUE`

Security, identity, advisory, marketing, data, issuer/acceptance, loyalty, risk or other services. Required subproduct and organic/acquisition treatment where available.

#### `MERCHANT_PROCESSING_REVENUE`

Merchant/acquirer/platform economics. State gross-versus-net presentation, interchange/network pass-through treatment and POS/software inclusion.

#### `ISSUER_PROCESSING_REVENUE`

Account/card/transaction processing for financial institutions. State account and transaction populations and license/service mix.

### 3.6 Incentives, rebates and pass-throughs

Separate:

- client incentives;
- network rebates;
- merchant/acquirer incentives;
- distribution-partner payments;
- interchange and network pass-throughs;
- brokerage/clearance/exchange pass-throughs;
- promotional customer rewards;
- contract liabilities and prepaid incentives.

#### `INCENTIVE_RATIO`

```text
client incentives or rebates
/ compatible gross revenue before that offset
```

Only calculate where numerator and denominator are disclosed on a compatible basis. The ratio is descriptive, not automatically negative; incentives may support profitable volume and long-term contracts.

### 3.7 Settlement exposure

Settlement guarantee, prefunding, merchant receivable, cash advance, intermediary balance and reserve exposure are different.

Required fields:

- gross obligation or net exposure;
- duration;
- collateral/prefunding;
- loss history;
- legal obligor;
- capital/liquidity treatment;
- source date.

Do not infer credit risk from payment value alone.

## 4. Exchange, clearing and market-infrastructure metric families

### 4.1 Volume

#### `AVERAGE_DAILY_VOLUME`

Required dimensions:

- contracts, shares, lots, messages or notional value;
- trading days;
- asset class/product;
- on-exchange, OTC, cleared-only or cash market;
- round-turn/single-side convention;
- period.

#### `TOTAL_CONTRACT_VOLUME`

Period flow of contracts under the issuer's convention.

#### `AVERAGE_DAILY_NOTIONAL`

Monetary notional traded/matched. Not comparable to contract count without contract specifications.

#### `OPEN_INTEREST`

Period-end or average outstanding contracts. A stock, not a period transaction flow.

**Non-equivalence law:**

```text
ADV ≠ open interest ≠ clearing value ≠ collateral ≠ net settlement flow
```

### 4.2 Transaction monetization

#### `TRANSACTION_AND_CLEARING_REVENUE`

Required fields:

- gross/net of rebates;
- execution, matching, novation, clearing and settlement scope;
- cash versus derivatives;
- product and client mix;
- period.

#### `REVENUE_PER_CONTRACT`

```text
compatible transaction/clearing fee numerator
/ compatible contract-volume denominator
```

Required controls:

- same product population;
- same period;
- excluded event/cash/OTC products disclosed;
- round-turn convention;
- rebates and tiering;
- reported versus derived.

An increase can reflect fee changes, product mix or lower high-volume tiers. It does not establish broad pricing power without decomposition.

### 4.3 Market share

Market share requires:

- market definition;
- numerator and denominator source;
- venue/product/geography;
- volume/notional/trades/open-interest basis;
- double-count and internalization treatment;
- period.

Self-reported “leadership” without a denominator remains an attributed claim.

### 4.4 Market data and connectivity

Separate:

- real-time devices/screens;
- delayed/end-of-day data;
- enterprise licenses;
- usage royalties;
- index/benchmark licenses;
- connectivity ports/access;
- colocation;
- derived analytics;
- redistribution rights.

Required drivers may include subscriber/device count, price, product mix, data usage and contract type.

### 4.5 Listings and issuer services

Metrics may include:

- listed companies/ETPs;
- new listings;
- proceeds raised;
- transfers;
- annual listing/subscription fees;
- corporate-action/issuer-service revenue.

IPO proceeds are issuer capital raised, not exchange revenue.

### 4.6 Clearing collateral and interest

Separate:

- performance bonds/margin posted;
- guaranty fund contributions;
- cash held at a central bank/custodian;
- gross interest earned;
- interest distributed to clearing members;
- retained net spread/fee;
- collateral-management fee;
- settlement flow.

#### `NET_COLLATERAL_INTEREST_ECONOMICS`

```text
gross interest on eligible collateral
- amounts distributed to customers / clearing members
- directly attributable cost
```

Do not capitalize gross interest as issuer earnings.

### 4.7 Margin efficiency

Portfolio/cross-margin savings require:

- counterfactual methodology;
- customer/product population;
- gross versus average daily benefit;
- time horizon;
- source method.

A reported client margin saving is not issuer revenue, although it may support client adoption and retention.

## 5. Custody, asset-servicing and investment-platform metric families

### 5.1 Assets under custody and/or administration

#### `AUC_A_PERIOD_END`

Assets held, serviced or administered under the issuer's definition at a point in time.

Required dimensions:

- custody versus administration scope;
- double-count policy;
- asset classes;
- geography/currency conversion;
- period-end date;
- newly installed versus announced mandates;
- market/FX/net-flow bridge where available.

AUC/A is not ownership, issuer balance-sheet assets or a fee-equivalent denominator across mandates.

### 5.2 Assets under management

#### `AUM_PERIOD_END`

Assets managed under the issuer's definition. Preserve discretionary/advisory, alternatives/public, ETF/fund, gross/net and subadvised treatment where available.

#### `AUM_BRIDGE`

```text
ending AUM
= beginning AUM
+ market/performance
+ FX
+ external net flows
+ acquired assets
- divested assets
± other/reclassification
```

Only compatible components may be compared or summed.

### 5.3 Mandates and installation

Separate:

- mandate announced;
- contract signed;
- regulatory/board approvals complete;
- assets installed/onboarded;
- service modules activated;
- revenue recognized;
- full run rate reached.

`MANDATE_AUC_A` is a scope/scale indicator, not a revenue backlog unless a source provides contract economics.

### 5.4 Servicing and management fees

Required dimensions:

- average versus period-end eligible assets;
- service breadth and complexity;
- activity/transaction dependence;
- pricing concessions;
- market-value sensitivity;
- asset mix;
- gross/net presentation;
- geography/currency;
- performance-fee inclusion.

#### `SERVICING_FEE_YIELD`

```text
servicing fee revenue
/ compatible average serviced asset base
```

Use cautiously: AUC/A populations can contain assets with materially different service intensity, and average bases may be unavailable.

### 5.5 Market-value and activity sensitivity

Issuer-reported sensitivity, such as State Street's estimated servicing-fee exposure to asset values/activity, remains source-native and methoded.

Do not generalize one custodian's sensitivity percentages to another.

### 5.6 Pricing pressure

Required fields:

- existing/new client basis;
- gross fee versus expanded service scope;
- annual/contract period;
- sample methodology;
- offsetting automation or term extension;
- revenue versus margin effect.

### 5.7 Net interest income and client cash

Separate:

- client deposits/cash;
- average interest-earning assets;
- securities/loans;
- asset yield;
- deposit/funding cost;
- NIM;
- NII;
- cash-sorting/reallocation;
- reinvestment effects.

A higher AUC/A does not automatically increase NII.

### 5.8 Foreign exchange and securities finance

FX revenue requires volume, realized spread, volatility and treasury/revaluation separation. Securities-finance revenue requires balances, spreads, collateral and indemnification/risk treatment.

## 6. Ratings, data, index and benchmark metric families

### 6.1 Ratings transaction revenue

Revenue from new issuance, refinancing, bank loans, structured finance or other rated transactions.

Required dimensions:

- instrument/asset class;
- issuance volume and mix;
- rating type;
- geography;
- period;
- market share basis where used.

Issuance proceeds are not ratings revenue.

### 6.2 Ratings non-transaction revenue

May include surveillance, monitoring, entity/relationship programs, annual fees, research and intersegment royalties. Preserve issuer definition and recurring status.

### 6.3 Subscription and recurring revenue

Separate:

- fixed subscription;
- usage-based recurring;
- recurring variable;
- annual license;
- enterprise contract;
- transaction/perpetual license;
- professional services.

“Recurring” can still be volume-, asset- or usage-sensitive.

### 6.4 ARR

#### `ANNUALIZED_RECURRING_REVENUE`

Issuer-defined annualized run-rate of eligible contracts/products at a point in time.

Required fields:

- eligible product population;
- FX convention;
- acquisition/divestiture treatment;
- month/quarter-end calculation;
- churn/renewal treatment;
- SaaS subset;
- period.

ARR is not recognized revenue. ARR growth can differ from organic recurring-revenue growth.

### 6.5 ACV / bookings / sales

Annual contract value, bookings and sales are commercial leading indicators. Preserve:

- gross/new/renewal/expansion basis;
- contract term;
- cancellation/implementation conditions;
- one-time services;
- recognized-revenue schedule;
- acquired contribution.

### 6.6 Remaining performance obligations

#### `RPO`

Contracted consideration allocated to unsatisfied/partially satisfied performance obligations under the source's accounting definition.

Required fields:

- invoiced versus unbilled;
- expected recognition timing;
- cancellation/termination rights where disclosed;
- segment/product;
- currency;
- acquisition effects.

RPO is not cash, backlog profit or guaranteed revenue.

### 6.7 Index-linked assets

Separate:

- period-end ETP/fund AUM linked to an index;
- average asset base used for fees;
- net flows;
- market/FX movement;
- new product launches;
- asset-linked fee rate;
- derivatives/usage royalties;
- data subscriptions.

#### `INDEX_AUM_BRIDGE`

```text
ending linked AUM
= beginning linked AUM
+ market/FX movement
+ net flows
+ product additions/removals/reclassifications
```

### 6.8 Benchmark and usage royalties

State the usage population—exchange-traded derivatives, OTC contracts, funds, structured products, redistribution or data access. Contract count or notional is not automatically disclosed royalty revenue.

## 7. Financial-software and processing metric families

### 7.1 Recurring processing revenue

Revenue from ongoing account, transaction, core, issuer, payments or capital-markets processing.

Required dimensions:

- account versus transaction basis;
- minimum commitments;
- price escalators;
- implementation status;
- pass-throughs;
- client/product population;
- organic/acquired growth.

### 7.2 Subscription / SaaS revenue

Preserve hosted/cloud/on-premise status, term, seat/account/usage basis, implementation and support inclusion.

### 7.3 License revenue

Perpetual/term/usage license is not automatically recurring. Termination fees and upfront license sales are separated from recurring growth.

### 7.4 Professional and implementation services

These can be low margin, necessary to activate recurring revenue or evidence of deployment friction. Track backlog, duration, completion and margin separately.

### 7.5 Retention

Separate:

- logo/gross customer retention;
- gross revenue retention;
- net revenue retention;
- product/account retention;
- renewal rate;
- assets/accounts retained.

Do not infer NRR from revenue growth.

### 7.6 Transaction and account drivers

Examples:

- accounts on file;
- active accounts;
- card/account processing transactions;
- digital-payment transactions;
- merchant locations;
- payment volume;
- installed institutions;
- modules per client.

A customer or account count without revenue/margin contribution is a scale observation only.

## 8. Growth-bridge dictionary

Every growth assertion should use the applicable fields below rather than one generic `growth_rate`.

```text
reported_growth
constant_currency_growth
organic_growth
organic_constant_currency_growth
acquisition_contribution
	divestiture_drag
pricing_contribution
volume_or_usage_contribution
mix_contribution
market_value_contribution
net_flow_contribution
FX_translation
FX_transaction_or_volatility_effect
accounting_or_presentation_change
other_explained
unexplained_residual
```

### 8.1 Arithmetic law

Issuer narrative components may be rounded and may not sum exactly. Preserve reported components and label any house residual; never force arithmetic equality by altering source facts.

### 8.2 Organic law

“Organic” remains issuer-defined unless an accepted house methodology independently calculates it. Acquired/divested businesses, FX and reclassifications must use the issuer's stated treatment.

## 9. Revenue and margin dictionary

### 9.1 Gross revenue

Top-line amount before specified rebates, incentives or pass-throughs.

### 9.2 Net revenue

Revenue after issuer-declared transaction-based expenses, rebates, incentives or pass-throughs. The deducted population must be named.

### 9.3 Segment revenue

Segment attribution under the issuer's current presentation. Recasts and reclassifications require dated versioning.

### 9.4 Operating income / EBITDA / adjusted EBITDA

GAAP operating income, EBITDA and adjusted EBITDA are different. Every adjustment requires a source bridge. Do not compare margins across companies without compatible definitions.

### 9.5 Free cash flow

Issuer-reported or house-derived FCF must declare operating cash flow, capex, software capitalization, working capital, settlement balances, acquisitions, SBC and other exclusions.

Financial institutions may not be meaningfully comparable on generic industrial FCF; use appropriate capital/distribution measures.

## 10. Capital-return dictionary

Separate:

- common dividends declared and paid;
- special/variable dividends;
- gross repurchases;
- shares retired;
- issuance/SBC/exercises;
- net share-count change;
- debt repayment/issuance;
- acquisition consideration;
- regulatory capital distribution;
- subsidiary capital constraints.

#### `NET_CAPITAL_RETURN_YIELD`

```text
cash common dividends
+ gross repurchases
- equity issuance proceeds attributable to dilution where methoded
/ compatible average market capitalization
```

This metric does not establish accretion. Buyback price and foregone capital uses remain separate.

## 11. Valuation-field dictionary

The accepted valuation owner should supply current values. This dictionary only defines required metadata.

### 11.1 P/E

Required:

- trailing/forward/normalized;
- GAAP/adjusted;
- estimate vintage;
- diluted share convention;
- period/currency;
- negative/near-zero earnings handling.

### 11.2 P/TBV and P/B

Required:

- tangible/common equity definition;
- AOCI/OCI treatment;
- period-end shares;
- acquisition/intangible treatment;
- current versus forecast book.

### 11.3 EV/EBITDA

Required:

- debt/cash/noncontrolling/pension/lease treatment;
- trailing/forward/normalized EBITDA;
- segment/consolidated scope;
- financial-company suitability warning.

### 11.4 P/FCF

Required FCF definition and share-count basis.

### 11.5 SOTP

Every segment value requires:

- segment metric and multiple;
- comparables/method;
- corporate cost;
- debt/cash and tax leakage;
- separation cost;
- cross-segment synergies/dis-synergies;
- minority interests;
- date and uncertainty.

A SOTP is a house-derived scenario, not a reported fact.

## 12. Derived first-vertical metrics

### 12.1 Network net-revenue conversion

```text
net network / payment revenue growth
versus compatible volume, transaction and cross-border growth
```

Do not compress into one take rate where revenue categories have different denominators.

### 12.2 Value-added-service contribution

```text
VAS revenue and growth
+ organic/acquired bridge
+ margin where available
/ consolidated or segment revenue
```

Missing segment margin remains null.

### 12.3 Exchange transaction bridge

```text
volume growth
+ revenue-per-unit / pricing / mix change
- rebate/pass-through change
= transaction-net-revenue growth, subject to scope
```

### 12.4 Recurring-mix bridge

```text
eligible recurring revenue / compatible net revenue
```

Issuer-defined recurring populations remain disclosed. A higher share can arise because transactional revenue falls.

### 12.5 Asset-servicing fee bridge

```text
market/FX effect
+ net new installed business
+ client activity
+ service-scope/mix
+ pricing
= servicing-fee change, plus unexplained residual
```

### 12.6 Index revenue bridge

```text
average linked assets × effective asset-linked fee
+ derivatives / usage royalties
+ data subscriptions
```

### 12.7 Software revenue bridge

```text
beginning recurring base
+ new sales installed
+ expansion / cross-sell
- churn / contraction
+ price / usage
+ acquisitions / FX
+ licenses / services
= reported revenue change
```

This is a conceptual reconciliation until the source supplies each component.

## 13. Clock grammar

Every first-vertical metric may need several clocks:

```text
transaction_time
trade_time
clearing_time
settlement_time
period_start / period_end
period_end_stock_asof
issuer_publication_time
filing_time
system_observation_time
retention_time
curation/review_time
correction/supersession_time
business-effective time
contract-signing time
implementation/installation time
revenue-recognition time
cash-collection time
```

No page-level “as of” may erase these differences.

### 13.1 Publication versus period

A 2025 annual filing published in 2026 contains facts applicable to 2025 or December 31, 2025. The publication date is not the operating period.

### 13.2 Market-value lag

AUC/A and other alternative/complex assets may be reported with valuation lags. Source-native lag disclosure must survive.

### 13.3 Run-rate clock

ARR/ACV at period end is forward-looking only in the narrow sense of annualizing eligible current contracts; it is not a forecast of recognized annual revenue.

## 14. Null and comparability states

```text
AVAILABLE_COMPARABLE
AVAILABLE_NATIVE_ONLY
NOT_DISCLOSED
NOT_APPLICABLE
NOT_MEASURABLE
RIGHTS_RESTRICTED
STALE
DEFINITION_CHANGED
PERIOD_MISMATCH
POPULATION_MISMATCH
GROSS_NET_MISMATCH
CURRENCY_MISMATCH
ACCOUNTING_MISMATCH
IDENTITY_UNRESOLVED
SOURCE_WITHDRAWN
```

The UI should explain why a comparison is refused rather than presenting a blank zero.

## 15. Company disclosure coverage matrix

`✓` means the company reports a useful version; it does not imply full cross-company comparability.

| Metric family | V | MA | CME | ICE | NDAQ | FI | FIS | BK | STT | SPGI | MCO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| payment / GDV value | ✓ | ✓ |  |  |  | ✓ | activity-linked |  |  |  |  |
| processed / switched transactions | ✓ | ✓ |  |  |  | ✓ | ✓ |  |  |  |  |
| cross-border activity | ✓ | ✓ |  |  |  |  |  |  |  |  |  |
| incentives / rebates | ✓ | ✓ | volume rebates | ✓ | ✓ | partner/pass-through |  |  |  |  |  |
| exchange volume / ADV |  |  | ✓ | ✓ | ✓ |  |  |  |  |  |  |
| revenue per contract/unit | category bridge | category bridge | ✓ | source-dependent | source-dependent | source-dependent | source-dependent |  |  | royalty-dependent |  |
| market data / recurring solutions | VAS | VAS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ARR / ACV |  |  |  | contracted tech | ✓ |  | ✓ |  |  | subscription metrics | ✓ |
| AUC/A |  |  |  |  |  |  |  | ✓ | ✓ |  |  |
| AUM / linked assets |  |  |  |  | index-linked |  |  | ✓ | ✓ | index-linked |  |
| issuance-sensitive revenue |  |  |  | listings/debt data | listings |  | capital markets | issuer services | issuer services | ✓ | ✓ |
| NII / interest-related income | settlement effects | settlement effects | collateral gross/net | collateral/treasury | possible segment effects | ✓ |  | ✓ | ✓ |  |  |
| transaction vs recurring mix | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

This matrix is research coverage, not a completeness or quality score.

## 16. Evidence admission requirements

A metric is eligible for accepted current display only when:

1. source identity and rights are valid;
2. immutable source retention/locator is proven under the incumbent owner;
3. company/business/security identity is validated where required;
4. native definition and scope are retained;
5. clocks and period are explicit;
6. unit, population, stock/flow and gross/net basis are explicit;
7. review/admission state is accepted;
8. correction/supersession behavior is defined;
9. private/public publication rules are satisfied;
10. the consumer preserves limitations.

Search snippets and this research document do not satisfy live admission.

## 17. Deterministic validation requirements

Proposed acceptance checks for a future implementation:

### Identity and scope

- reject missing issuer/business/source IDs where required;
- reject guessed ticker binding;
- reject one source metric mapped to multiple native definitions without a declared mapping.

### Time

- reject period-end stock without `as_of_date`;
- reject period flow without `period_start` and `period_end`;
- preserve publication and business period separately;
- reject future-known estimate/definition in a PIT view.

### Unit and population

- reject ratio derivation with mismatched currency, period, geography or population;
- reject contract count mixed with notional value;
- reject branded transactions as processed transactions;
- reject AUC/A as AUM;
- reject ARR as recognized revenue.

### Gross/net

- reject comparisons that omit disclosed incentives/rebates/pass-through basis;
- reject gross collateral interest presented as retained revenue;
- reject gross exchange revenue compared to net revenue without bridge.

### Derivation

- require formula, inputs and source IDs;
- preserve source rounding and report residual;
- reject division by zero or null denominators;
- distinguish issuer-reported from house-derived.

### Correction

- append superseding assertions;
- preserve old bytes and clocks;
- reject same-identity conflicting current assertions without adjudication.

## 18. User-facing display rules

### 18.1 Always show

- native metric name;
- plain-language definition;
- value/unit/period;
- subject/population;
- reported or derived status;
- source and limitations;
- comparable/degraded state.

### 18.2 On comparison tables

- align period and currency where possible;
- keep native definitions available in a drawer;
- refuse incompatible ratios visibly;
- distinguish reported levels from growth rates;
- use separate columns for gross and net;
- never rank missing values as zero.

### 18.3 On rerating panels

Metrics appear inside a declared earnings bridge. They are not free-floating bullish/bearish badges.

Example:

```text
Visa cross-border volume growth
  → international transaction revenue driver
  → adjusted for mix, FX and incentives
  → operating / EPS relevance
  → expectations and valuation comparison
```

## 19. What is now DO_NOT_REDO

Unless materially invalidated:

- do not create a universal `volume` field;
- do not create a universal `take_rate` field across networks, processors and exchanges;
- do not map ARR/RPO/ACV to revenue without a recognition bridge;
- do not treat AUC/A, AUM and index-linked assets as interchangeable;
- do not compare gross and net exchange/payment revenue silently;
- do not infer retained collateral economics from gross interest;
- do not annualize quarter values without an explicit run-rate label;
- do not use period-end assets as an average fee denominator without qualification;
- do not remove issuer-native definitions after normalization;
- do not let dictionary coverage become a company score.

## 20. Exact next action

Use this dictionary to create a portable, research-only first-vertical assertion packet for the eleven company/business records. The packet must retain source-native metric names and definitions while mapping them to normalized families, include null/comparability states, and contain no current valuation, rank or basket admission.

In parallel, begin the balance-sheet and credit research tranche with a subtheme-specific earnings/valuation map for universal banks, regional banks, card lenders, specialty finance and private credit. Do not create the final Fable CEO handoff yet.
