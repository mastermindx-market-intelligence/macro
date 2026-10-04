# Finance global/regional metric, accounting and regulatory dictionary — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Intended carrier:** Macro Draft/HOLD PR #7786  
**Prepared against:** `0b4f93ff27c74fa735744439ab741e7887db8ad8`  
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`  
**State:** NON-CANONICAL LOCAL RESEARCH CONTRACT / PENDING SAME-CARRIER PERSISTENCE  
**Authority:** not an enrolled schema, identity mapping, valuation model, source admission, ranking input or trade signal.

## 0. Outcome

The product must let a reader compare financial businesses across regions without turning local accounting, prudential rules, currencies, listings and policy systems into false precision.

The governing rule is:

```text
source-native fact
→ local accounting/regulatory interpretation
→ normalized comparison family
→ explicit comparability state
→ economic/valuation interpretation
```

Normalization never overwrites the source-native fact.

## 1. Comparability states

- `EXACT_NATIVE_ONLY` — useful within the issuer/source definition; no peer normalization.
- `LOCALLY_COMPARABLE` — comparable within the same country/rule/accounting cohort.
- `MAPPED_WITH_CAVEATS` — normalized family exists, with visible mapping and residual differences.
- `ECONOMICALLY_ANALOGOUS_NOT_NUMERICALLY_COMPARABLE` — mechanism similar, number not safely comparable.
- `NOT_COMPARABLE` — refuse.
- `MISSING` — source absent or not disclosed.
- `RIGHTS_RESTRICTED` — known but unavailable to this product.
- `REGIME_BREAK` — pre/post rule or accounting change cannot be pooled without adjustment.

## 2. Universal laws

1. Every observation retains issuer, business, legal entity, listing and currency scope.
2. Every observation retains accounting standard, fiscal period and consolidation basis.
3. Every prudential ratio retains local rule, transition and denominator.
4. Stock, flow, count, value, rate, notional and per-share measures remain distinct.
5. Average-period and period-end values never silently mix.
6. Reported, adjusted, statutory, economic-value, regulatory and cash-remittance measures remain distinct.
7. Constant-currency growth is not shareholder-currency growth.
8. A/H/ADR and secondary listings remain separate securities until the identity owner supplies conversions.
9. State or policy role is an attributed condition, not an automatic guarantee or valuation premium.
10. Restatements and rule changes append/supersede; history is not rewritten.

## 3. Proposed record envelope

```text
metric_assertion_id
issuer_id / business_id / security_id_optional
country / regulatory_home / operating_geography
native_metric_name / normalized_metric_family
accounting_standard / fiscal_period / consolidation_scope
prudential_or_insurer_regime / transition_state
reporting_currency / functional_currency / shareholder_currency
measurement_class / unit / gross_net / average_end
value / numerator / denominator
reported_derived_estimated
publication / period / as_of / effective / observed / belief clocks
source / locator / definition
comparability_state / mapping_notes
rights / retention / review / correction
limitations
```

## 4. Identity, listing and currency

| Field / family | Required meaning |
|---|---|
| `legal_issuer_id` | Legal issuer identity from incumbent identity owner; never inferred from ticker similarity. |
| `security_listing_id` | Listing/line identity including exchange, share class, settlement currency and depositary-receipt ratio. |
| `domicile_vs_operating_region` | Legal domicile, regulatory home and economic exposure are separate. |
| `reporting_currency` | Currency used in the financial statements. |
| `functional_currency` | Business/segment functional currency where supplied. |
| `shareholder_return_currency` | Currency used for the price/return observation. |
| `fx_translation` | Reported, constant-currency and transactional FX effects remain separate. |
| `dual_listing_basis` | A/H/ADR or secondary listing; no price or share-count merge without validated conversion. |

## 5. Accounting and fiscal-period identity

| Field / family | Required meaning |
|---|---|
| `accounting_standard` | IFRS, UK-adopted IAS, J-GAAP, US GAAP, PRC Accounting Standards, Ind AS/Indian GAAP, AASB, K-IFRS, SFRS(I), HKFRS or another exact basis. |
| `fiscal_year_end` | Issuer fiscal year-end and reporting period; calendar alignment is not assumed. |
| `restatement_state` | Original, restated, reclassified, pro forma or acquisition-recast state. |
| `reported_adjusted_statutory` | Reported GAAP/IFRS, management-adjusted, regulatory/statutory and cash/remittance measures are separate. |
| `consolidation_scope` | Group, regulated bank, insurer, holding company, segment or vehicle. |
| `acquisition_basis` | Organic, acquired, disposed, pro forma or purchase-accounting contribution. |

## 6. Bank capital and liquidity

| Field / family | Required meaning |
|---|---|
| `CET1_ratio` | CET1 numerator and RWA denominator with local rule basis and transition state. |
| `core_tier1_ratio` | Local core Tier 1 term retained where not equivalent to Basel CET1. |
| `total_capital_ratio` | Total regulatory capital; not common equity. |
| `leverage_ratio` | Exact leverage-exposure denominator and local rule. |
| `RWA` | Credit/market/operational RWA with standardized/IRB/output-floor basis. |
| `MREL_TLAC` | Resolution liabilities/capital; not distributable equity. |
| `LCR_NSFR` | Liquidity ratios with local scope and averaging basis. |
| `excess_distributable_capital` | Management estimate only when source-defined; never inferred from headline CET1. |
| `APRA_CET1` | Australian APRA basis retained separately from international/harmonized presentation. |
| `India_CRAR` | RBI capital adequacy basis; preserve CET1, Tier 1 and total CRAR. |
| `China_core_tier1` | NFRA/PBOC basis; do not map automatically to European fully loaded CET1. |
| `Japan_fully_loaded_vs_domestic` | Japan FSA presentation basis and transition state. |

## 7. Deposit and funding economics

| Field / family | Required meaning |
|---|---|
| `deposits_period_end` | Period-end stock by currency, customer, product and geography. |
| `deposits_average` | Average-period balance; required for matched yield/cost ratios. |
| `deposit_mix` | Noninterest-bearing, demand, savings, term, brokered/wholesale, operational and wealth cash. |
| `deposit_cost` | Average cost with all-deposit versus interest-bearing denominator. |
| `deposit_beta` | Cumulative, incremental or down-cycle beta with exact policy-rate reference. |
| `structural_hedge` | Notional, duration, reinvestment schedule, yield and accounting treatment; UK-specific owner output. |
| `wholesale_funding` | Secured/unsecured, currency, maturity, spread and entity. |
| `central_bank_funding` | Program, eligibility, maturity and accounting; not normalized funding. |
| `covered_bonds_securitization` | Funding and encumbrance basis. |
| `FX_funding_basis` | Cross-currency and foreign-currency funding cost. |

## 8. Credit quality and vintage

| Field / family | Required meaning |
|---|---|
| `IFRS9_stage1_2_3` | Stage population and ECL basis; Stage 3 is not automatically NPL. |
| `NPL_NPA_nonaccrual` | Native definition, days-past-due, product exclusions and gross/net basis. |
| `special_mention_watchlist` | Early-risk classification; not realized default. |
| `slippages` | New NPA/NPL formation during period; India-specific labels retained. |
| `delinquency_bucket` | 30/60/90+ or issuer-native bucket by product and vintage. |
| `charge_off_write_off` | Gross charge-offs/write-offs and policy basis. |
| `recoveries` | Cash/reinstatement recoveries; separate from reserve release. |
| `net_credit_loss` | Charge-offs minus recoveries with average receivable denominator. |
| `provision` | Income-statement flow. |
| `allowance_ECL` | Balance-sheet stock by product/stage. |
| `coverage_ratio` | Allowance/NPL or another explicit denominator; never cross-compared without mapping. |
| `forborne_restructured` | Modification/forbearance population and cure/default state. |
| `property_LGFV_project_finance` | Exposure class with borrower, collateral, guarantee and policy treatment. |
| `vintage` | Origination period and underwriting regime; later performance never backfilled as originally known. |

## 9. Bank earnings and book-value bridge

| Field / family | Required meaning |
|---|---|
| `NII` | Net interest income with tax-equivalent and accounting basis. |
| `NIM` | NII/average earning asset basis; local/issuer definition retained. |
| `fee_income` | Payment, wealth, cards, transaction, market, custody and other fees split where available. |
| `trading_markets_income` | Client, inventory and valuation components where disclosed. |
| `PPNR` | Pre-provision net revenue or local analogue with definition. |
| `credit_cost` | Provision or realized loss basis; not assumed. |
| `reported_ROE_ROTE_ROTCE` | Numerator/denominator and adjusted/notable-item treatment. |
| `BVPS_TBVPS_TNAV` | Per-share accounting anchor and reconciliation. |
| `AOCI_FVOCI` | Securities/hedge/pension/FX reserve treatment. |
| `policy_share_gains` | Japan cross-shareholding disposals/marks, separated from recurring operating earnings. |
| `state_policy_cost` | Attributed policy-directed economics only when source-supported; no model invention. |

## 10. Insurance capital and earnings

| Field / family | Required meaning |
|---|---|
| `SolvencyII_ratio` | Eligible own funds/SCR with group scope, volatility adjustment and transitional state. |
| `SolvencyUK_ratio` | UK-specific solvency regime and matching-adjustment scope. |
| `Japan_ESR_ICS` | Economic-value solvency or ICS basis; not directly comparable to Solvency II. |
| `CROSS_ratio` | China Risk-Oriented Solvency System phase and group/entity basis. |
| `HK_RBC_ratio` | Hong Kong risk-based capital basis. |
| `KICS_ratio` | Korean Insurance Capital Standard basis. |
| `APRA_insurer_capital` | Australian prescribed capital amount/coverage basis. |
| `India_solvency_ratio` | IRDAI required/available solvency margin basis. |
| `VONB` | Value of new business with currency, market, assumption and economic basis. |
| `new_business_margin` | VONB denominator such as APE/PVNBP; definition retained. |
| `embedded_value` | EV methodology, economic assumptions and group scope. |
| `CSM` | IFRS 17 contractual service margin stock and release; not cash. |
| `free_surplus_generation` | Issuer-defined operating free surplus; not GAAP profit or automatic remittance. |
| `statutory_remittance` | Cash/dividend upstream from regulated subsidiaries. |
| `combined_ratio` | Current accident year, catastrophe and prior-year development decomposition. |
| `reserve_development` | Gross/net, accident year, line and nominal/discounted basis. |
| `reinsurance_cession` | Ceded premium/loss, attachment, counterparty and commission. |

## 11. Market infrastructure and payments

| Field / family | Required meaning |
|---|---|
| `cash_ADT_ADV` | Cash turnover by venue/currency, value/count and on/off-book basis. |
| `derivatives_ADV_open_interest` | Contracts/value, asset class and rate per contract. |
| `Connect_flow_holdings` | Northbound/southbound turnover, holdings and quota/channel state. |
| `listing_issuance` | IPO/follow-on/bond/listing activity; announced, priced and completed separate. |
| `clearing_collateral` | Margin/collateral stock and gross/retained interest treatment. |
| `market_data_index_revenue` | Subscription, usage, pricing and linked-asset drivers. |
| `UPI_transactions_value` | Count/value, person-to-person/person-to-merchant scope and operator definition. |
| `domestic_fast_payment` | Rail, participants, availability, finality, value/count and commercial economics. |
| `card_network_vs_issuer` | Network/switch/acquirer/issuer roles never merged. |
| `rate_per_contract_take_rate` | Matched numerator/denominator and rebate/pass-through treatment. |

## 12. Asset, wealth and retirement

| Field / family | Required meaning |
|---|---|
| `AUM_AUA_client_assets` | Native population and ownership; not interchangeable. |
| `fee_paying_fee_generating_assets` | Fee base, average/end and activation state. |
| `net_new_money_flows` | Client flows separated from market, FX and acquisitions. |
| `advisor_agent_productivity` | Headcount, active/productive definition and sales/asset denominator. |
| `cash_sorting_sweep` | Client cash mix, bank sweep/MMF yield and sharing economics. |
| `retirement_participants_assets` | Participant count, administered assets and proprietary AUM separate. |
| `cross_border_wealth` | Booking center, client domicile, currency and regulatory channel. |

## 13. Regional policy and ownership

| Field / family | Required meaning |
|---|---|
| `state_ownership` | Ownership percentage, voting/control and effective date. |
| `policy_mandate` | Specific source-backed public-policy role; not inferred support. |
| `priority_sector` | India priority-sector target/asset basis. |
| `ring_fence` | UK ring-fenced entity perimeter. |
| `currency_board` | Hong Kong base-rate/HIBOR/aggregate-balance transmission. |
| `BOJ_normalization` | Policy rate, yield curve and JGB-purchase regime; mechanism context only. |
| `LPR_policy_rates` | China LPR/MLF/OMO and deposit-rate transmission. |
| `macroprudential_limits` | LTV/DTI/CCyB/serviceability or local borrower-based measures. |
| `resolution_regime` | MREL/TLAC/bail-in or local resolution perimeter. |
| `tax_distribution` | Franking/imputation, withholding and investor scope; never universalized. |

## 14. Valuation and price recognition

| Field / family | Required meaning |
|---|---|
| `local_anchor` | Business-model-specific P/TBV, P/E, EV/EBITDA, FCF, EV/VONB/EV, dividend or SOTP anchor. |
| `required_return` | Local rates, currency, sovereign, regulation, tail risk and governance components remain named. |
| `current_consensus` | Accepted revisions owner only; fiscal/accounting/listing identity required. |
| `current_valuation` | Accepted valuation owner only; local currency/share/ADR conversion required. |
| `price_return` | Security-specific local and base-currency total return with distributions. |
| `relative_strength` | Against local sector, market and global peer benchmarks separately. |
| `breadth_flow_positioning` | Accepted owners only; not invented from a small basket. |
| `security_conversion` | ADR ratio, A/H shares, FX and withholding/corporate action. |

## 15. Clocks and correction

| Field / family | Required meaning |
|---|---|
| `publication_at` | Upstream publication/filing time. |
| `period_start_end` | Business measurement period. |
| `as_of_date` | Point-in-time stock/capital/asset date. |
| `effective_at` | Regulatory or ownership rule effective date. |
| `observed_retained_at` | System observation/retention clock. |
| `belief_cutoff` | No later knowledge after this time for PIT evaluation. |
| `restatement_supersession` | Append-only correction link to predecessor. |
| `regime_version` | Accounting/capital/rule regime version. |

## 16. Regional minimum comparison packets

### 16.1 Europe / UK bank packet

```text
IFRS basis
legal/ring-fenced entity
reported and normalized RoTE
TNAV/TBVPS
CET1 + RWA/output-floor state
MREL/TLAC
deposit and structural-hedge bridge
Stage 2/3 + NPL + cost of risk
sovereign/country exposure
capital distribution
```

### 16.2 Japan bank/insurer packet

```text
J-GAAP or IFRS basis
domestic/overseas business
yen deposit and asset repricing
JGB/foreign-bond valuation and duration
policy-shareholdings and realized gains
domestic/fully loaded capital
ESR/ICS for insurers
book/economic-value per share
capital return
```

### 16.3 China/Hong Kong packet

```text
PRC AS / IFRS / HKFRS basis
A/H/ADR security identity
state/control and policy role
LPR/deposit/NIM bridge
property/LGFV/consumer exposure
NPL/special-mention/provision coverage
core Tier 1 / C-ROSS / HK RBC
VONB/EV/CSM/free surplus where insurance
Connect/HIBOR/HKD channel where applicable
dividend/remittance
```

### 16.4 India packet

```text
Indian GAAP / Ind AS and fiscal period
bank versus NBFC perimeter
deposit/CASA/funding bridge
GNPA/NNPA/slippage/credit-cost definitions
CRAR/CET1/liquidity
priority-sector and RBI constraints
product/vintage growth
ROA/ROE/BVPS
UPI/payment distribution where relevant
```

### 16.5 Developed Asia packet

```text
local accounting/regulator
currency and cross-border exposure
mortgage/household/real-estate credit
local capital basis
wealth/transaction/market infrastructure mix
tax distribution such as franking
insurer capital such as K-ICS/APRA
local and global return benchmarks
```

## 17. Derived measures and refusal conditions

### 17.1 Permitted derivations

- period-matched fee yield = fee revenue / average native fee base;
- local deposit beta with exact policy-rate start/end and deposit denominator;
- TBVPS/BVPS growth adjusted only by disclosed dividends/share changes and source reconciliation;
- normalized current-year combined ratio when catastrophe and reserve-development components are source-disclosed;
- local-currency and base-currency return decomposition with exact FX and distribution dates;
- market-activity monetization = net transaction revenue / matched volume population;
- VONB growth at reported and constant exchange rates when both are supplied;
- AUM/asset bridges using issuer-reported flow, market, FX and acquisition components.

### 17.2 Mandatory refusal

Refuse when:

- the security conversion or share class is unresolved;
- fiscal periods or accounting regimes do not match;
- average and period-end values would be mixed;
- a regulatory-capital denominator/rule is unknown;
- the insurer-capital regimes differ without an accepted mapping;
- current valuation/consensus would require a duplicate or unavailable owner;
- a state-policy relationship is merely inferred;
- constant-currency and reported growth are conflated;
- an acquisition contribution cannot be separated;
- a later outcome would be backfilled into an earlier PIT record;
- public rights do not permit the intended product display.

## 18. Product display requirements

Every global/regional metric panel shows:

- native label and normalized family;
- issuer/business/security/listing scope;
- country, accounting and regulatory regime;
- currency and conversion state;
- period/as-of and publication dates;
- stock/flow/rate/count class;
- average/end and gross/net basis;
- comparability badge;
- source and locator;
- limitation and correction state.

The default copy must say why two similar-looking figures may not compare. A hidden tooltip is insufficient for a load-bearing difference.

## 19. Evaluation requirements

- never pool pre/post IFRS 9, IFRS 17, CRR3 output-floor, Solvency II review, K-ICS, C-ROSS or another material regime without an era field;
- align expectations and valuation to the exact listing/currency/fiscal identity;
- preserve state ownership and regulatory interventions as observed context, not ex-post explanatory labels;
- separate local market return, global base-currency return and sector-relative return;
- record survivorship, delisting, mergers and dual-listing changes;
- use contemporaneous source availability and revision vintages;
- refuse a cohort when normalization removes the economic mechanism under study.

## 20. Non-claims

This dictionary does not establish one global Finance database, one global capital ratio, one global loss definition, one valuation engine, one consensus history, or any direct investment authority.