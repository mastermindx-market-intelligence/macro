# Finance R11 — candidate basket construction and subtheme atlas freeze

Date: 2026-09-23 / 2026-09-24 UTC.  
Operation: `gmi-finance-sector-research-20260923-sol-001`.  
Carrier: Macro PR #7786 / `sol/finance-sector-research-20260923`.  
State: RESEARCH / DESIGN FREEZE / DRAFT-HOLD.  
Mission complete: false. Product implemented: false.  
Protected procedure: `Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1/bootstrap 1.  
Direct principal reason: `PRINCIPAL_JUDGMENT`.

R10 established how Finance subthemes rerate. R11 freezes how those economic questions become research slices and, only where justified, candidate price baskets.

No candidate below is an approved canonical theme, admitted basket, ranking universe or trading universe.

## 1. Governing rulings

### R11-1 — Research slice and price basket are different objects

A **research slice** is an economic question: deposit-franchise quality, card-network toll economics, private-credit fee conversion, P&C underwriting, clearing infrastructure, mortgage servicing, etc.

A **price basket** is a dated security-membership object with validated security identity, membership history, eligibility/liquidity rules, weighting, rebalance/correction law, price basis and evidence.

A useful research slice may honestly have no price basket.

### R11-2 — Existing broad baskets keep ownership

Existing broad surfaces remain incumbent context owners, including:

- `regional_banks`;
- `payments_fintech`;
- `insurance`;
- XLF `megabanks` and `brokers_asset` legs;
- `intl_banks` and `intl_insurers`.

R11 does not rewrite their memberships to obtain cleaner thematic exposures.

The current broad baskets are intentionally heterogeneous:
- `payments_fintech` spans networks, lenders, merchant processors, remittance, brokerage, BNPL, digital banks and software;
- `insurance` spans carriers, life, reinsurance and brokers;
- `regional_banks` spans several funding, geography, CRE and credit profiles.

They remain useful broad price/rotation surfaces while the Finance dossier overlays more precise semantics.

### R11-3 — Membership is business-line many-to-many

The legal issuer is not duplicated when one company has several Finance roles.

Examples:
- AXP: network + issuer + acquirer + lender;
- COF: card lending + deposit franchise + network exposure;
- NDAQ: venue + index + data + financial software;
- APO: asset management + private credit + retirement/spread ecosystem;
- JPM: deposits + lending + IB + trading + payments + custody + wealth.

Every research membership records the business/exposure justifying it.

### R11-4 — Exposure requires a denominator

Permitted exposure bases include:
- segment revenue/profit;
- assets, loans or receivables;
- deposits/funding;
- payment/transaction volume;
- AUM/FPAUM/AUA/AUC;
- written/earned premium or exposure units;
- fee-bearing assets;
- contracts/open interest;
- servicing UPB;
- ratings/indices/subscriptions;
- explicit operating counts when revenue is unavailable.

No denominator means no claim of high-purity exposure.

### R11-5 — Closed non-scoring role vocabulary

- `DIRECT_PURE_OR_HIGH_EXPOSURE`
- `DIRECT_DIVERSIFIED`
- `ENABLER_OR_TOLL_COLLECTOR`
- `SECOND_ORDER_BENEFICIARY`
- `PROXY_OR_ADJACENCY`
- `AT_RISK_OR_DISRUPTED`
- `HEDGE_OR_OFFSET`

These describe relationship type, not expected return.

### R11-6 — “Pure play” is quantitative

If an issuer does not separately disclose the relevant business, use an honest diversified/unknown state. Narrative relevance does not create purity.

### R11-7 — Historical basket research requires PIT membership

Future admitted membership needs:

```text
valid_from
valid_to
known_at
source_observed_at
membership_reason
business_id
issuer_id
security_id
exposure_period
correction_state
rights_state
```

Current curated membership must not be backfilled as historical truth.

### R11-8 — Weighting cannot hide conviction

Permitted research weighting families:

1. Equal weight.
2. Float-cap context where an incumbent benchmark owner supplies it.
3. Exposure weight when the exposure metric is truly comparable.
4. Exposure-capped weight with explicit cap.
5. Stratified equal weight across visible relationship tiers.

No subjective “quality” or conviction multiplier.

### R11-9 — Multiple baskets are not independent confirmation when they overlap

Audit:
- security overlap;
- business-line overlap;
- macro-driver overlap;
- factor/geography/currency overlap;
- ownership hierarchy overlap.

A collection of correlated labels is not independent evidence.

## 2. Finance subtheme atlas v0.1

### Banking, funding and balance-sheet credit

1. Deposit Franchise Quality
2. Universal / Money-Center Banks
3. Regional / Super-Regional Banks
4. Community / Local Banks
5. Yield-Curve / NIM Normalization
6. Commercial Real-Estate Credit
7. Cards & Consumer Credit
8. Auto / Equipment / Specialty Finance
9. Digital Banks / Neobanks
10. Mortgage Originators
11. Mortgage Servicers / MSR

### Capital formation, trading and market infrastructure

12. Equity & Debt Capital Markets
13. M&A / Advisory
14. Electronic Market Makers
15. Options & Derivatives Ecosystem
16. Exchanges & Trading Venues
17. Clearing / CCP / CSD
18. Custody & Asset Servicing
19. Prime Brokerage / Securities Lending
20. Market / Reference Data
21. Ratings / Credit Information
22. Indices / Benchmarks / ETF Plumbing

### Payments and money movement

23. Card Networks
24. Merchant Acquiring / Processing
25. Issuer Processing
26. Gateways / Orchestration
27. ACH / Instant / B2B Payments
28. Cross-Border / Remittance
29. Embedded Finance / BaaS
30. Fraud / Identity / Tokenization

### Asset management, wealth and private markets

31. Passive / ETF Asset Managers
32. Active Asset Managers
33. Wealth Platforms / RIAs
34. Retirement / Recordkeeping
35. Alternative Asset Managers
36. Private Credit Managers
37. BDC / Direct-Lending Vehicles
38. Fund Administration / Middle-Back Office

### Insurance and risk transfer

39. Personal P&C
40. Commercial / Specialty P&C
41. Reinsurance
42. Insurance Brokers
43. MGAs / Delegated Underwriting
44. Life / Annuity Spread Businesses
45. Claims / Insurance Data / Workflow

### Trust, software and disruption

46. RegTech / KYC / AML
47. Financial Cybersecurity
48. Core Banking / Financial Software
49. Stablecoin Infrastructure
50. Digital Custody / Tokenized Securities
51. Open Banking / API Finance
52. Agentic / AI Finance Workflow

The atlas contains **52 semantic slices**. It is deliberately larger than the number of eventual price baskets.

## 3. Candidate basket admission contract

A research slice may advance toward a price basket only when the following are populated or explicitly held:

```text
slice_id
membership_id
business_id
legal_issuer_id
security_id
listing_id
role
relationship_directness
exposure_metric_native
exposure_metric_family
exposure_numerator
exposure_denominator
exposure_share
exposure_period_start
exposure_period_end
currency
geography
product_or_asset_scope
source_id
source_locator
source_published_at
system_observed_at
valid_from
valid_to
known_at
correction_state
rights_state
review_state
```

Membership states:

- `RESEARCH_CANDIDATE`
- `EXPOSURE_MEASURED`
- `IDENTITY_VALIDATED`
- `PIT_MEMBERSHIP_VALIDATED`
- `PRICE_ELIGIBILITY_VALIDATED`
- `CANDIDATE_READY_FOR_OWNER_REVIEW`
- `ADMITTED`
- `HELD_MISSING_EXPOSURE`
- `HELD_MISSING_IDENTITY`
- `HELD_MISSING_PIT`
- `REJECTED_WEAK_RELATIONSHIP`
- `REMOVED_SUPERSEDED`

R11 creates zero `ADMITTED` memberships.

## 4. Exposure materiality law

Do not use one universal purity threshold.

Examples:
- a network's transaction volume is not revenue share;
- a bank loan balance consumes capital differently from fee revenue;
- custody can be operationally huge at low fee yield;
- ratings/data may be strategic inside a diversified information issuer;
- reinsurance premium is not comparable with broker commissions;
- software can be economically exposed without owning financial assets.

If displayed, purity bands must be metric-family-specific and owner-reviewed.

## 5. Overlap audit

Every basket pair should expose five dimensions.

### Security overlap
- Jaccard: `|A∩B| / |A∪B|`.
- Weighted overlap when comparable weights exist: `Σ min(wAi,wBi)`.

### Business-line overlap
Record common workflow, customer, product, revenue mechanism and retained risk.

### Macro-driver overlap
Examples:
rates, curve, credit, spend, asset values, volatility, issuance, housing, catastrophe, FX, regulatory capital.

### Factor overlap
Measure but never use as membership evidence:
market beta, size, value/growth, duration, volatility, country/currency, liquidity.

### Ownership overlap
Prevent accidental double counting of:
- manager vs BDC;
- parent vs regulated subsidiary;
- holding company vs operating bank;
- sponsor vs listed fund.

## 6. Existing basket coexistence

### regional_banks
Retain existing equal-weight price history and membership owner.

Add semantic facets:
- Deposit Franchise Quality;
- CRE Credit;
- NIM/Curve Normalization;
- Super-Regional vs smaller-bank exposure.

### payments_fintech
Retain as canonical Fintech & Payments theme price surface.

Decompose semantically into:
networks, acquiring, issuer processing, remittance, BNPL, digital banks, brokerage, software, stablecoin infrastructure.

### insurance
Retain the broad Insurance & Brokers price surface.

Decompose semantically into:
personal P&C, commercial/specialty P&C, reinsurance, life/annuity, brokers, MGAs, claims/data/workflow.

### XLF and international context
Keep XLF legs and international baskets under their current owners. R11 research overlays do not replace them.

## 7. Strongest future candidate cohorts

### Tier 1 research candidates
- Card Networks
- Merchant Acquiring / Processing
- Exchanges & Trading Venues
- Clearing / CCP / CSD
- Custody & Asset Servicing
- Market / Reference Data
- Ratings / Credit Information
- Indices / Benchmarks / ETF Plumbing
- Insurance Brokers
- Reinsurance
- Alternative Asset Managers
- Private Credit Managers

These have comparatively clear workflow identities, public metrics and economic anchors.

### Tier 2 candidates
- Deposit Franchise Quality
- Cards & Consumer Credit
- Mortgage Servicers / MSR
- Passive / ETF Asset Managers
- Wealth Platforms
- Commercial / Specialty P&C
- Life / Annuity
- Core Banking / Financial Software
- Fraud / Identity / Tokenization

### Semantic-first / do not rush into price baskets
- Yield-Curve/NIM Normalization
- CRE Credit Cycle
- ACH/Instant/B2B
- Embedded Finance/BaaS
- MGAs
- Stablecoin Infrastructure
- Digital Custody/Tokenization
- Open Banking
- Agentic/AI Finance Workflow
- Financial Cybersecurity

## 8. Basket quality tests

Before an admitted basket can support historical evaluation:

1. identity completeness;
2. exposure coverage;
3. PIT membership;
4. price coverage;
5. corporate-action basis;
6. survivorship audit;
7. overlap audit;
8. concentration audit;
9. benchmark selection;
10. FX treatment;
11. rebalance law;
12. source-rights review;
13. correction handling;
14. explicit null behavior;
15. historical membership reproducibility.

Where these fail, display `CURRENT_MEMBERSHIP_CONTEXT_ONLY` rather than fabricate history.

## 9. R11 freeze result

R11 freezes:

- semantic slice vs price basket distinction;
- 52-slice Finance atlas;
- relationship-role vocabulary;
- membership evidence grammar;
- weighting alternatives;
- overlap dimensions;
- coexistence with current basket owners;
- candidate admission tiers.

R11 does not:
- mutate current baskets;
- mint new canonical themes;
- approve 52 price baskets;
- create security identity;
- create historical membership;
- rank, gate, size or trade.

Next: freeze the product/visualization grammar that makes this system useful rather than encyclopedic.
