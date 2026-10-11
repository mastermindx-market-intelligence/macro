# Finance asset-management, wealth, insurance and risk-transfer metric/evidence dictionary — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** RESEARCH CONTRACT PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Scope:** semantic, clock, denominator, derivation, comparison and evidence requirements for asset managers, wealth/retirement platforms, P&C/life/reinsurance businesses, brokers and insurance-data/workflow providers.  
**Authority:** this is not an enrolled contract, canonical data store, graph vocabulary, valuation model, rank, recommendation, trading input or publication permission.

## 0. Outcome

The user should be able to compare financial businesses without being misled by quantities that look similar but describe different populations, clocks or economics.

The machine must prevent errors such as:

- treating ending AUM growth as organic flow growth;
- comparing AUM with AUA or client assets;
- treating non-fee-paying commitments as current fee revenue;
- comparing an ETF sponsor’s AUM with an index provider’s linked assets;
- treating total net new assets as organic when acquisitions/recruiting are included;
- treating client cash as advisory assets;
- treating written premium as earned premium or underwriting profit;
- comparing combined ratios without current-year, catastrophe and reserve-development anatomy;
- treating favorable reserve development as recurring current underwriting;
- comparing gross and net loss ratios;
- treating reinsurance premium growth as evidence of better price/terms;
- treating insurance premiums or annuity deposits as revenue without liability/benefit context;
- treating adjusted operating earnings as GAAP, statutory cash or distributable capital;
- treating broker reported revenue growth as organic growth;
- treating acquired annualized revenue as recognized revenue;
- treating subscription share as retention or organic growth;
- using a later reserve restatement as if known at the original observation date.

The product therefore requires a **closed semantic dictionary with explicit non-equivalence and refusal rules**, not a universal Finance metric table or score.

## 1. Controlling laws

### D-FIN-AWI-01 — Source-native fact survives normalization

Every metric retains:

- issuer/regulator-native name;
- exact definition or lawful paraphrase;
- document and locator;
- legal entity/business/product/population;
- period and as-of date;
- unit and currency;
- average/end and stock/flow/rate/count class;
- gross/net/ceded/reported/adjusted basis;
- reported/derived/estimated state;
- correction and supersession state.

A normalized family aids comparison; it never overwrites the native fact.

### D-FIN-AWI-02 — Ending assets and average fee base remain separate

Ending AUM/AUA/client assets are point-in-time stocks. Management/advisory revenue commonly depends on average balances, daily/monthly balances or contract-specific billing conventions. Ending balance cannot silently become the denominator of a fee-yield calculation.

### D-FIN-AWI-03 — AUM, AUA, client assets and linked assets are not synonyms

- `AUM` generally implies investment discretion/management under issuer definition.
- `AUA` generally implies administration/advisement/recordkeeping under issuer definition.
- `CLIENT_ASSETS` may include advisory, brokerage, cash, custody, bank, trust or other assets.
- `INDEX_LINKED_ASSETS` describe assets using/licensing an index, not assets managed by the index provider.
- `SERVICING_UPB` or insured exposure are not AUM.

### D-FIN-AWI-04 — Fee state is mandatory

Every asset observation must state, when applicable:

- fee-paying/generating;
- non-fee-paying;
- unfunded/uninvested commitment;
- advised only;
- administered only;
- proprietary versus third-party;
- eliminated in consolidation;
- fee base unknown.

### D-FIN-AWI-05 — Organic, acquired, recruited, market and FX changes remain separate

Required bridge where material:

```text
beginning balance
+ same-store organic net flow
+ recruited/transferred assets
+ acquired assets
− divested/offboarded assets
+ market change
+ FX
± distributions / realizations / reclassifications
= ending balance
```

Unknown components remain unknown.

### D-FIN-AWI-06 — Written and earned premium remain separate

Written premium records contract binding during the period. Earned premium recognizes coverage over time. Written growth does not establish current earned revenue or profit.

### D-FIN-AWI-07 — Gross, ceded and net insurance populations never silently mix

Premiums, losses, reserves, recoverables, exposure and ratios preserve:

- gross before reinsurance;
- ceded to reinsurers;
- net retained;
- assumed from cedents;
- retroceded;
- collateralized or unsecured state where applicable.

### D-FIN-AWI-08 — Current-year, catastrophe and prior-year development remain separate

A reported combined/loss ratio must preserve, where disclosed:

```text
current accident year ex-cat
+ catastrophe effect
+ prior accident-year development effect
= reported ratio
```

### D-FIN-AWI-09 — Premium growth does not establish rate adequacy

Rate, exposure, mix, insured-value inflation, retention, new business, acquisition, reinstatement, FX and term length can all change premium. Rate adequacy requires a prospective risk/loss-cost bridge.

### D-FIN-AWI-10 — Insurance reserves are estimates with vintages

Reserve observations preserve:

- accident/policy/underwriting year;
- case reserve versus IBNR;
- paid versus incurred;
- gross/ceded/net;
- line/geography/product;
- nominal/discounted basis;
- source estimate date and later development.

A later ultimate-loss estimate cannot be backfilled as earlier knowledge.

### D-FIN-AWI-11 — GAAP, adjusted, statutory and cash-remittance earnings remain distinct

Life and P&C companies may disclose:

- GAAP net income;
- operating/adjusted operating earnings;
- statutory income;
- distributable or holding-company cash;
- segment non-GAAP profit.

Each carries its reconciliation and cannot substitute for another.

### D-FIN-AWI-12 — Broker organic/underlying growth excludes specified acquisition/FX effects only under issuer definition

`ORGANIC_REVENUE_GROWTH` and `UNDERLYING_REVENUE_GROWTH` retain the issuer’s exact adjustment policy. They are not interchangeable across issuers without a mapping receipt.

### D-FIN-AWI-13 — Acquired annualized revenue is not current recognized revenue

Acquisition pipeline, purchase consideration, annualized acquired revenue, pro forma revenue, recognized acquired revenue and organic revenue remain separate.

### D-FIN-AWI-14 — Recurring/subscription revenue does not establish retention or organic growth

Recurring share describes revenue type. Retention, price, seat/module expansion, acquisition and FX require separate evidence.

### D-FIN-AWI-15 — Per-share and capital effects remain visible

Growth in earnings, book value, AUM, premium or revenue must preserve:

- diluted share count;
- buybacks and issuance;
- stock compensation;
- acquisition equity;
- debt and interest;
- required regulatory/statutory capital;
- dividends/distributions.

### D-FIN-AWI-16 — Null is not zero

Closed null states:

- `NOT_DISCLOSED`;
- `NOT_APPLICABLE`;
- `NOT_COMPARABLE`;
- `RIGHTS_RESTRICTED`;
- `SOURCE_LOCATOR_PENDING`;
- `IDENTITY_UNRESOLVED`;
- `PERIOD_MISMATCH`;
- `BASIS_MISMATCH`;
- `HELD_FOR_REVIEW`.

### D-FIN-AWI-17 — Corrections append

Restatement, actuarial refinement, taxonomy change, acquisition presentation, metric-definition change or source correction appends a superseding assertion. History is not rewritten.

### D-FIN-AWI-18 — Dictionary semantics grant no analytical authority

Normalization makes facts comparable. It does not determine attractiveness, prediction, ranking, portfolio action or trade.

## 2. Proposed metric assertion envelope

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
balance_basis
flow_basis_optional
gross_net_basis
reinsurance_basis_optional
fee_state_optional
organic_acquired_market_fx_basis_optional
accident_policy_underwriting_year_optional
annualization_basis
reported_derived_estimated
numerator_ref_optional
denominator_ref_optional
formula_optional
comparison_eligibility
limitations[]
review_state
supersedes_assertion_id_optional
```

## 3. Measurement classes

Closed initial vocabulary:

- `BALANCE_STOCK`;
- `AVERAGE_BALANCE_STOCK`;
- `PERIOD_FLOW`;
- `VOLUME_VALUE`;
- `COUNT`;
- `RATE_OR_YIELD`;
- `RATIO`;
- `PER_SHARE_VALUE`;
- `FAIR_VALUE_ESTIMATE`;
- `REGULATORY_CAPITAL_MEASURE`;
- `CONTRACTED_NOT_RECOGNIZED`;
- `ANNUALIZED_RUN_RATE`;
- `POINT_IN_TIME_STATE`;
- `DURATION_OR_LAG`;
- `DISTRIBUTION_MEASURE`.

## 4. Asset-management metric families

### 4.1 Assets under management

**Normalized family:** `ASSETS_UNDER_MANAGEMENT`

Required dimensions:

- client type;
- asset class;
- style;
- vehicle;
- region/currency;
- active/index/ETF/cash/private;
- fee state;
- proprietary/third-party;
- ending/average.

Forbidden inference:

> AUM × headline fee = revenue

unless the average fee-paying population, fee schedule and period match.

### 4.2 Average AUM

**Normalized family:** `AVERAGE_ASSETS_UNDER_MANAGEMENT`

Preserve issuer calculation frequency and period. A quarterly/monthly/daily average cannot be reconstructed from two endpoints without explicit estimate status.

### 4.3 Fee-paying or fee-generating AUM

**Families:**

- `FEE_PAYING_AUM`;
- `FEE_GENERATING_AUM`.

These remain issuer-native because inclusion and billing conventions differ.

### 4.4 Assets under administration/advisement

**Family:** `ASSETS_UNDER_ADMINISTRATION_OR_ADVISEMENT`

Required role:

- recordkeeping;
- custody/administration;
- advice;
- plan services;
- wealth platform;
- other.

Do not combine with AUM unless the issuer supplies a non-overlap/elimination bridge.

### 4.5 Index-linked assets

**Family:** `INDEX_LINKED_ASSETS`

Required index/licensing scope. Does not establish manager AUM, index revenue or royalty rate.

### 4.6 Gross inflows and gross outflows

**Families:**

- `GROSS_CLIENT_INFLOWS`;
- `GROSS_CLIENT_OUTFLOWS`.

Required product/channel/region and reinvested-distribution treatment.

### 4.7 Net flows

**Families:**

- `NET_LONG_TERM_FLOWS`;
- `NET_CASH_MANAGEMENT_FLOWS`;
- `NET_ORGANIC_FLOWS`;
- `NET_ACQUIRED_OR_RECRUITED_ASSET_CHANGE`;
- `NET_MARKET_AND_FX_CHANGE`.

A company-defined `organic asset growth` retains its denominator and exclusions.

### 4.8 Realizations and distributions

**Families:**

- `PRIVATE_MARKETS_REALIZATIONS`;
- `DISTRIBUTIONS_NOT_REINVESTED`;
- `MANAGER_DRIVEN_DISTRIBUTIONS`.

Do not label realizations as client outflow when the economic meaning differs.

### 4.9 Unfunded/uninvested commitments

**Family:** `NON_FEE_PAYING_UNFUNDED_COMMITMENTS`

Measurement class: `CONTRACTED_NOT_RECOGNIZED` or source-defined potential fee base.

Required:

- fee starts on commitment versus invested capital;
- expiration/cancellation rights;
- deployment conditions;
- expected/unknown timing.

### 4.10 Base management/advisory fee revenue

**Family:** `BASE_MANAGEMENT_FEES`

Preserve:

- gross/net of distribution/pass-through;
- average fee base;
- fee waiver;
- performance-fee exclusion;
- securities-lending inclusion/exclusion.

### 4.11 Performance/incentive fees

**Family:** `PERFORMANCE_OR_INCENTIVE_FEES`

Required period, crystallization, hurdle/high-water mark where disclosed, associated compensation and realization status.

### 4.12 Effective fee rate

**Family:** `EFFECTIVE_MANAGEMENT_FEE_RATE`

Preferred formula only when issuer bases match:

```text
annualized management/advisory fee revenue
÷ matched average fee-paying AUM
```

Required inclusions/exclusions. Refuse when revenue and asset bases differ.

### 4.13 Technology/subscription ACV for diversified managers

**Family:** `FINANCIAL_TECHNOLOGY_ACV`

ACV remains a run-rate contract measure, not recognized annual revenue.

### 4.14 Investment performance

**Families:**

- `PRODUCT_OUTPERFORMANCE_SHARE`;
- `AUM_WEIGHTED_OUTPERFORMANCE_SHARE`;
- `MORNINGSTAR_HIGH_RATED_SHARE`;
- `CONSULTANT_OR_PLATFORM_RATING_STATE`.

Required benchmark, fee basis, universe, horizon, survivorship and source.

## 5. Wealth and adviser-platform metric families

### 5.1 Total client assets

**Family:** `TOTAL_CLIENT_ASSETS`

Required decomposition:

- advisory;
- brokerage;
- cash/deposits;
- custody/trust;
- lending collateral/other;
- internal double-count/elimination.

### 5.2 Advisory assets

**Family:** `ADVISORY_ASSETS`

Required discretionary/non-discretionary, fee-based, average/end and channel.

### 5.3 Brokerage assets

**Family:** `BROKERAGE_ASSETS`

Does not establish transaction revenue or advice fee.

### 5.4 Fee-based asset share

**Family:** `FEE_BASED_ASSET_SHARE`

Formula:

```text
fee-based/advisory assets
÷ matched total eligible client assets
```

Required eligible population.

### 5.5 Total net new assets

**Family:** `TOTAL_NET_NEW_ASSETS`

Must disclose inclusion of:

- recruited advisors;
- acquisitions;
- institution onboarding;
- internal channel transfer;
- planned offboarding;
- market movement exclusion.

### 5.6 Organic net new assets

**Family:** `ORGANIC_NET_NEW_ASSETS`

Retain company definition and denominator. Do not compare across firms until acquisition/recruiting/offboarding treatment is mapped.

### 5.7 Advisor headcount

**Families:**

- `FINANCIAL_ADVISOR_COUNT`;
- `PRODUCING_ADVISOR_COUNT`;
- `RECRUITED_ADVISOR_COUNT`;
- `ADVISOR_ATTRITION_COUNT`.

Employee, independent, RIA/custody, trainee and affiliated definitions remain distinct.

### 5.8 Active accounts/clients

**Families:**

- `ACTIVE_BROKERAGE_ACCOUNTS`;
- `HOUSEHOLD_COUNT`;
- `CLIENT_COUNT`;
- `NEW_ACCOUNTS`.

Account is not customer/household/advisor.

### 5.9 Client cash

**Families:**

- `CLIENT_CASH_TOTAL`;
- `BANK_SWEEP_BALANCE`;
- `THIRD_PARTY_BANK_SWEEP_BALANCE`;
- `MONEY_MARKET_FUND_BALANCE`;
- `BROKERAGE_CASH_BALANCE`.

Required location, owner, average/end, yield and revenue mechanism.

### 5.10 Cash-sorting flow

**Family:** `CLIENT_CASH_SORTING_FLOW`

Direction and destination required. A transfer inside the platform is not net client asset outflow.

### 5.11 Advisory fee yield

**Family:** `NET_ADVISORY_FEE_YIELD`

Required matched revenue, payout/pass-through treatment and average assets.

### 5.12 Advisor payout and recruiting assistance

**Families:**

- `ADVISOR_COMPENSATION_PAYOUT`;
- `RECRUITING_TRANSITION_ASSISTANCE`;
- `ACQUISITION_OR_ONBOARDING_COST`.

Cash, forgivable loans, equity and deferred consideration remain distinct.

### 5.13 Daily average trades and transaction activity

**Families:**

- `DAILY_AVERAGE_TRADES`;
- `CLIENT_TRADING_VOLUME`;
- `MARGIN_LOAN_BALANCE`;
- `SECURITIES_LENDING_BALANCE`.

Trading activity is not recurring advisory growth.

## 6. Retirement and recordkeeping metric families

### 6.1 Participant accounts

**Family:** `RETIREMENT_PARTICIPANT_ACCOUNTS`

Participant account may not equal unique person. Preserve active/inactive and plan populations where disclosed.

### 6.2 Employer/plan count

**Family:** `RETIREMENT_PLAN_COUNT`

Required market segment and product.

### 6.3 Retirement AUM and AUA

**Families:**

- `RETIREMENT_AUM`;
- `RETIREMENT_AUA`;
- `RETIREMENT_TOTAL_CLIENT_ASSETS`.

Eliminations and proprietary assets required.

### 6.4 Proprietary asset penetration

**Family:** `PROPRIETARY_ASSET_SHARE`

Formula only when populations match:

```text
proprietary managed assets
÷ eligible retirement assets
```

This is not automatically beneficial; fiduciary suitability, fee and retention matter.

### 6.5 Defined-contribution recordkeeping assets

**Family:** `DEFINED_CONTRIBUTION_RECORDKEEPING_ASSETS`

Recordkeeping AUA does not imply management fees.

### 6.6 Net deposits/contributions/withdrawals

**Families:**

- `RETIREMENT_CONTRIBUTIONS`;
- `RETIREMENT_WITHDRAWALS`;
- `RETIREMENT_NET_DEPOSITS`;
- `PLAN_WIN_ASSET_TRANSFER`;
- `PLAN_LOSS_ASSET_TRANSFER`.

### 6.7 Stable-value/general-account assets

**Families:**

- `STABLE_VALUE_ASSETS`;
- `GENERAL_ACCOUNT_RETIREMENT_LIABILITIES`;
- `CREDITING_RATE`;
- `PORTFOLIO_YIELD`;
- `NET_INVESTMENT_SPREAD`.

Managed wrap/stable-value and insurer general-account populations remain distinct.

### 6.8 Participant/asset-based fees

**Families:**

- `PARTICIPANT_BASED_ADMIN_FEE`;
- `ASSET_BASED_RETIREMENT_FEE`;
- `MANAGED_ACCOUNT_FEE`;
- `RECORDKEEPING_REVENUE`.

## 7. P&C insurance premium and exposure families

### 7.1 Gross written premium

**Family:** `GROSS_PREMIUM_WRITTEN`

Gross before ceded reinsurance; assumed premium included only as defined.

### 7.2 Net premium written

**Family:** `NET_PREMIUM_WRITTEN`

Required gross/ceded/assumed anatomy where available.

### 7.3 Net premium earned

**Family:** `NET_PREMIUM_EARNED`

Period flow recognized for coverage elapsed.

### 7.4 Policy count/policies in force

**Family:** `POLICIES_IN_FORCE`

Policy count is not exposure unit, vehicle, insured or customer. Product/term required.

### 7.5 Exposure units

**Families:**

- `INSURANCE_EXPOSURE_UNITS`;
- `INSURED_VALUE`;
- `PAYROLL_EXPOSURE`;
- `VEHICLE_EXPOSURE`;
- `LIMITS_EXPOSED`.

### 7.6 Renewal retention

**Family:** `POLICY_RETENTION_RATE`

Count, premium or exposure retention basis required.

### 7.7 New business

**Families:**

- `NEW_BUSINESS_PREMIUM`;
- `NEW_POLICY_COUNT`;
- `QUOTE_VOLUME`;
- `APPLICATION_VOLUME`;
- `BIND_RATE`.

### 7.8 Written-rate change

**Family:** `INSURANCE_WRITTEN_RATE_CHANGE`

Required line, region, layer and mix method. Not premium growth.

### 7.9 Rate-on-line

**Family:** `REINSURANCE_RATE_ON_LINE`

Formula:

```text
premium
÷ limit
```

where contract definition permits. Does not establish risk-adjusted adequacy without expected loss/terms.

## 8. P&C loss and underwriting families

### 8.1 Paid loss

**Family:** `PAID_LOSS_AND_LAE`

Required gross/net, line, accident year and period.

### 8.2 Incurred loss

**Family:** `INCURRED_LOSS_AND_LAE`

Includes paid plus reserve change under source definition.

### 8.3 Claim frequency

**Family:** `CLAIM_FREQUENCY`

Required claim/exposure definition.

### 8.4 Claim severity

**Family:** `CLAIM_SEVERITY`

Required paid/incurred/ultimate basis and claim cohort.

### 8.5 Loss ratio

**Family:** `LOSS_AND_LAE_RATIO`

Formula under matching basis:

```text
loss and LAE
÷ earned premium
```

Required gross/net, CAY/PY, cat/ex-cat and expense inclusion.

### 8.6 Expense ratio

**Family:** `UNDERWRITING_EXPENSE_RATIO`

Required denominator and acquisition/operating treatment.

### 8.7 Combined ratio

**Family:** `COMBINED_RATIO`

Required anatomy:

- loss/LAE ratio;
- expense ratio;
- CAY ex-cat;
- cat impact;
- prior-year development;
- source basis.

### 8.8 Underwriting income/margin

**Families:**

- `UNDERWRITING_INCOME`;
- `UNDERWRITING_MARGIN`.

Underwriting margin may be defined as `100% − combined ratio` or issuer-specific. Definition required.

### 8.9 Catastrophe loss

**Family:** `CATASTROPHE_LOSS`

Required named event/event set, gross/net, reinstatement, period and modeled/actual state.

### 8.10 Large-loss event

**Family:** `LARGE_LOSS_EVENT_IMPACT`

Issuer-defined grouping, not automatically catastrophe.

### 8.11 Prior-year development

**Families:**

- `FAVORABLE_PRIOR_YEAR_DEVELOPMENT`;
- `ADVERSE_PRIOR_YEAR_DEVELOPMENT`.

Required accident years/lines and ratio/amount basis.

### 8.12 Current accident year ex-cat

**Family:** `CURRENT_ACCIDENT_YEAR_EX_CAT_COMBINED_RATIO`

Do not infer if only reported combined ratio is disclosed.

## 9. Reserve metric families

### 9.1 Case reserve

**Family:** `CASE_RESERVES`

### 9.2 IBNR

**Family:** `IBNR_RESERVES`

### 9.3 Total loss reserves

**Family:** `LOSS_AND_LAE_RESERVES`

Required gross/ceded/net, discounted/nominal and line/vintage.

### 9.4 Reinsurance recoverable

**Family:** `REINSURANCE_RECOVERABLE`

Required paid/unpaid, collateral, counterparty/allowance where available.

### 9.5 Reserve-development triangle observation

**Family:** `ULTIMATE_LOSS_ESTIMATE_BY_VINTAGE`

Preserve original estimate date and subsequent development. Never overwrite earlier knowledge.

### 9.6 Loss-reserve discount

**Family:** `LOSS_RESERVE_DISCOUNT`

Required nominal reserve, rate, duration and accretion treatment where disclosed.

## 10. Reinsurance and capital metric families

### 10.1 Ceded premium

**Family:** `CEDED_PREMIUM`

### 10.2 Assumed premium

**Family:** `ASSUMED_REINSURANCE_PREMIUM`

### 10.3 Retrocession cost

**Family:** `RETROCESSION_PREMIUM_OR_COST`

### 10.4 Attachment point and limit

**Families:**

- `REINSURANCE_ATTACHMENT_POINT`;
- `REINSURANCE_LIMIT`.

Required contract/currency/occurrence/aggregate state.

### 10.5 Reinstatement premium

**Family:** `REINSTATEMENT_PREMIUM`

Do not treat as ordinary new business.

### 10.6 Alternative/third-party capital

**Families:**

- `THIRD_PARTY_CAPITAL_MANAGED`;
- `INSURANCE_LINKED_SECURITIES_AUM`;
- `CATASTROPHE_BOND_ISSUANCE`;
- `FEE_INCOME_FROM_THIRD_PARTY_CAPITAL`;
- `TRAPPED_COLLATERAL`.

### 10.7 Statutory surplus/RBC

**Families:**

- `STATUTORY_SURPLUS`;
- `RISK_BASED_CAPITAL_RATIO`;
- `AVAILABLE_CAPITAL`;
- `REQUIRED_CAPITAL`.

Jurisdiction/entity/formula required.

### 10.8 Premium-to-surplus

**Family:** `PREMIUM_TO_SURPLUS_RATIO`

Required numerator/denominator population and jurisdiction.

## 11. Investment and book-value metric families

### 11.1 Net investment income

**Family:** `NET_INVESTMENT_INCOME`

Required insurance/holding-company/segment population and recurring/variable treatment.

### 11.2 New-money yield and portfolio yield

**Families:**

- `NEW_MONEY_YIELD`;
- `PORTFOLIO_BOOK_YIELD`;
- `PORTFOLIO_MARKET_YIELD`.

### 11.3 Duration and unrealized gains/losses

**Families:**

- `PORTFOLIO_DURATION`;
- `UNREALIZED_INVESTMENT_GAIN_LOSS`;
- `REALIZED_INVESTMENT_GAIN_LOSS`.

### 11.4 Book value per share

**Families:**

- `BOOK_VALUE_PER_SHARE`;
- `TANGIBLE_BOOK_VALUE_PER_SHARE`;
- `ADJUSTED_BOOK_VALUE_PER_SHARE`.

Adjusted book definition and AOCI/MRB exclusions mandatory.

### 11.5 Book-value-per-share growth

**Family:** `BOOK_VALUE_PER_SHARE_GROWTH`

Formula must incorporate dividend treatment explicitly when claiming total economic growth.

### 11.6 ROE/operating ROE

**Families:**

- `RETURN_ON_AVERAGE_COMMON_EQUITY`;
- `OPERATING_RETURN_ON_AVERAGE_COMMON_EQUITY`.

Required numerator reconciliation and average-equity basis.

## 12. Life, annuity and protection metric families

### 12.1 Premiums

**Families:**

- `LIFE_INSURANCE_PREMIUMS`;
- `GROUP_BENEFIT_PREMIUMS`;
- `PENSION_RISK_TRANSFER_PREMIUMS`;
- `ANNUITY_DEPOSITS`.

Premium and deposit remain distinct. PRT premium may have offsetting benefit/liability recognition.

### 12.2 Account values and reserves

**Families:**

- `POLICY_ACCOUNT_VALUES`;
- `INSURANCE_POLICY_LIABILITIES`;
- `MARKET_RISK_BENEFIT_FAIR_VALUE`;
- `SEPARATE_ACCOUNT_ASSETS`.

### 12.3 Policy fees

**Family:** `POLICY_FEE_REVENUE`

Required product/account-value driver.

### 12.4 Crediting rate and spread

**Families:**

- `CREDITING_RATE`;
- `NET_INVESTMENT_SPREAD`;
- `GENERAL_ACCOUNT_SPREAD_EARNINGS`.

### 12.5 Mortality/morbidity/longevity

**Families:**

- `MORTALITY_EXPERIENCE`;
- `MORBIDITY_EXPERIENCE`;
- `LONGEVITY_EXPERIENCE`;
- `CLAIMS_INCURRENCE_RATIO`.

Required expected/actual population and period.

### 12.6 Lapse/surrender

**Families:**

- `LAPSE_RATE`;
- `SURRENDER_RATE`;
- `POLICYHOLDER_BEHAVIOR_VARIANCE`.

### 12.7 Adjusted operating income

**Family:** `INSURANCE_ADJUSTED_OPERATING_INCOME`

Issuer-defined reconciliation mandatory. GAAP/statutory/cash state remains separate.

### 12.8 Assumption review/refinement

**Families:**

- `ACTUARIAL_ASSUMPTION_REVIEW_IMPACT`;
- `RESERVE_REFINEMENT_IMPACT`;
- `MODEL_REFINEMENT_IMPACT`.

Point-in-time event with affected product/segment.

### 12.9 Cash remittance/excess capital

**Families:**

- `SUBSIDIARY_CASH_REMITTANCE`;
- `EXCESS_CAPITAL_GENERATION`;
- `HOLDING_COMPANY_LIQUID_ASSETS`.

## 13. Broker/advisory metric families

### 13.1 Reported revenue

**Family:** `BROKER_REPORTED_REVENUE`

### 13.2 Organic/underlying revenue growth

**Families:**

- `BROKER_ORGANIC_REVENUE_GROWTH`;
- `BROKER_UNDERLYING_REVENUE_GROWTH`.

Issuer-specific adjustment policy mandatory.

### 13.3 Acquired revenue

**Families:**

- `ACQUIRED_REVENUE_RECOGNIZED`;
- `ANNUALIZED_ACQUIRED_REVENUE`;
- `PRO_FORMA_ACQUIRED_REVENUE`.

Never combine without labels.

### 13.4 Client retention and new business

**Families:**

- `BROKER_CLIENT_RETENTION`;
- `BROKER_NET_NEW_BUSINESS`;
- `BROKER_RENEWAL_REVENUE_GROWTH`.

### 13.5 Fiduciary interest

**Family:** `FIDUCIARY_INTEREST_INCOME`

Required average fiduciary balance and rate basis if available. Not core commission growth.

### 13.6 Commission and fee mix

**Families:**

- `INSURANCE_BROKER_COMMISSIONS`;
- `INSURANCE_BROKER_FEES`;
- `REINSURANCE_BROKERAGE_REVENUE`;
- `CONSULTING_REVENUE`.

### 13.7 EBITDAC/adjusted margin

**Families:**

- `ADJUSTED_EBITDAC`;
- `ADJUSTED_OPERATING_MARGIN`;
- `FREE_CASH_FLOW`.

Reconciliation and acquisition/earnout treatment required.

### 13.8 Acquisition consideration and leverage

**Families:**

- `ACQUISITION_PURCHASE_CONSIDERATION`;
- `ACQUISITION_EARNOUT_LIABILITY`;
- `BROKER_DEBT_OUTSTANDING`;
- `ACQUISITION_EQUITY_ISSUED`.

## 14. Data, claims and insurance-software metric families

### 14.1 Subscription revenue

**Family:** `SUBSCRIPTION_REVENUE`

Required hosted/on-premise, term, renewal, advance-bill and product population.

### 14.2 Subscription revenue share

**Family:** `SUBSCRIPTION_REVENUE_SHARE`

Formula:

```text
subscription revenue
÷ matched total revenue
```

Does not establish retention.

### 14.3 Transaction revenue

**Family:** `TRANSACTION_OR_USAGE_REVENUE`

Required event/unit population.

### 14.4 Advisory/consulting revenue

**Family:** `ADVISORY_CONSULTING_REVENUE`

Not recurring subscription unless contract supports that classification.

### 14.5 ARR/ACV/RPO

**Families:**

- `ANNUAL_RECURRING_REVENUE`;
- `ANNUAL_CONTRACT_VALUE`;
- `REMAINING_PERFORMANCE_OBLIGATION`.

None is recognized revenue. Issuer definition mandatory.

### 14.6 Retention and expansion

**Families:**

- `GROSS_REVENUE_RETENTION`;
- `NET_REVENUE_RETENTION`;
- `CUSTOMER_RETENTION`;
- `MODULE_ATTACH_RATE`;
- `SEAT_OR_USAGE_EXPANSION`.

### 14.7 Organic constant-currency growth

**Family:** `ORGANIC_CONSTANT_CURRENCY_REVENUE_GROWTH`

Acquisition/disposition and FX policy required.

### 14.8 Adjusted EBITDA and FCF

**Families:**

- `ADJUSTED_EBITDA`;
- `FREE_CASH_FLOW`;
- `FCF_CONVERSION`.

Stock compensation, capitalized development, acquisitions and restructuring remain visible.

## 15. Derived research metrics

Derived metrics are `RESEARCH_ONLY` until separately accepted.

### 15.1 Organic flow rate

```text
organic net flow
÷ matched beginning or average eligible asset base
```

State denominator and annualization.

### 15.2 AUM quality bridge

Display-only vector:

```text
organic flow
market/FX
acquired/recruited
fee-state
fee-rate mix
```

No composite score.

### 15.3 Effective fee-yield change

```text
current matched fee rate
− prior matched fee rate
```

Requires same fee/revenue scope.

### 15.4 Wealth organic gathering rate

```text
organic net new client assets
÷ beginning eligible client assets
```

Company definition and annualization required.

### 15.5 Advisory penetration

```text
advisory/fee-based assets
÷ eligible client assets
```

### 15.6 Current-year ex-cat underwriting margin

```text
100% − CAY ex-cat combined ratio
```

Only if issuer provides CAY ex-cat combined ratio.

### 15.7 Rate-versus-loss-cost gap

```text
written rate change
− estimated prospective loss-cost trend
```

Requires aligned line/geography/layer and explicit estimate methodology. Otherwise refuse.

### 15.8 Reserve-development contribution

```text
prior-year development amount or ratio points
÷ matched earned premium or reported earnings basis
```

### 15.9 BVPS total economic growth

```text
(BVPS_end − BVPS_begin + dividends_per_share)
÷ BVPS_begin
```

Only when book basis and dividend period match.

### 15.10 Broker acquisition-adjusted growth bridge

```text
reported growth
= organic/underlying
+ acquisition
+ FX
+ disposition/other
```

Use issuer components; do not solve missing residual as fact.

### 15.11 Subscription operating leverage

```text
organic recurring-revenue growth
versus
organic operating-cost growth / margin change
```

No fused score.

## 16. Comparison keys

### Asset management

```text
issuer/business
client type
asset class
style/vehicle
fee state
region/currency
period/as-of
average/end
flow/change source
```

### Wealth/retirement

```text
issuer/channel
asset population
advisory/brokerage/cash/recordkeeping
organic/acquired/recruited
account/participant/plan population
period/as-of
```

### Insurance/reinsurance

```text
legal insurer/entity
line/product
geography
admitted/E&S
gross/ceded/net/assumed
accident/policy/underwriting year
cat/ex-cat
current/prior development
period/as-of
```

### Life/annuity

```text
legal entity
product/cohort
premium/deposit/account-value population
fee/spread/insurance margin
GAAP/adjusted/statutory
assumption/hedge state
period/as-of
```

### Broker/data

```text
business/segment
organic/acquired/FX
commission/fee/subscription/transaction
client/product/geography
period/as-of
```

Only matching comparison keys support direct change or cross-company comparison.

## 17. Deterministic validation requirements

A future validator should reject or hold records when:

- source/locator is missing for an accepted assertion;
- period/as-of is missing;
- stock/flow/rate/count class is absent;
- average/end basis is absent where relevant;
- AUM/AUA/client/index-linked population is unspecified;
- fee state is missing for asset monetization claims;
- organic/acquired/market/FX change is collapsed where the source separates it;
- written/earned premium is ambiguous;
- gross/ceded/net basis is missing;
- combined ratio lacks issuer basis;
- CAY, catastrophe or prior development is inferred without source;
- reserve vintage is missing;
- adjusted operating income lacks reconciliation reference;
- acquired annualized revenue is labeled current revenue;
- ARR/ACV/RPO is labeled recognized revenue;
- a ratio lacks matched numerator and denominator;
- a later correction overwrites rather than supersedes;
- a ticker hint is treated as canonical identity;
- a research metric contains ranking/trade authority.

## 18. Product-display requirements

### 18.1 Asset manager

Display:

- ending and average AUM;
- organic flows;
- market/FX/acquisition bridge;
- fee-paying state;
- effective fee rate;
- base/performance/other revenue;
- expense/margin;
- per-share capital return;
- expectation/price conflict.

### 18.2 Wealth/retirement

Display:

- total/advisory/brokerage/cash or retirement AUM/AUA;
- organic versus recruited/acquired assets;
- accounts/advisors/participants/plans;
- cash/sweep and spread state;
- fee/payout/expense;
- integration and per-share economics.

### 18.3 P&C/reinsurance

Display:

- exposure/rate/written/earned premium;
- CAY ex-cat, catastrophe and prior development;
- expense and reported combined ratio;
- reserve/capital/reinsurance state;
- investment income;
- BVPS/TBVPS and capital return.

### 18.4 Life/annuity

Display:

- sales/deposits/premium/account values separately;
- fee/spread/insurance margin;
- claims/benefits and behavior;
- adjusted/GAAP/statutory/cash state;
- assumption/hedge/reserve changes;
- capital and book value.

### 18.5 Broker/data

Display:

- organic/underlying versus reported/acquired/FX;
- retention/new business where disclosed;
- fiduciary interest separately;
- margin/FCF/debt/integration;
- subscription/transaction/consulting mix for data providers.

## 19. Source hierarchy

1. audited/statutory/regulatory source;
2. issuer filing and supplemental tables;
3. issuer-defined reconciliation;
4. owner-approved deterministic derivation;
5. attributed secondary research candidate;
6. model extraction candidate pending review.

No lower tier silently upgrades to a higher tier.

## 20. Explicit non-claims

This dictionary does not establish:

- a production schema;
- source admission or rights;
- current company valuations;
- reserve adequacy;
- normalized earnings;
- approved basket membership;
- ranking or trading authority;
- predictive efficacy.

## 21. Exact next action

Encode a bounded research-only assertion packet for the representative census. Records with missing exact locator, identity or basis remain explicitly held. Then proceed to Finance disruption, cross-subtheme product design and historical evaluation before implementation planning and the final Fable CEO handoff.
