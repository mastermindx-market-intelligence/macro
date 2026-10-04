# Finance expectations, valuation and price-recognition join contract — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** OWNER-PRESERVING JOIN DESIGN / DRAFT-HOLD  
**Mission complete:** false  
**Authority:** research and interface design only. This document does not create a consensus store, valuation engine, price signal, rank, recommendation, entry, sizing, trade, graph write, source admission, merge or deployment authority.

## 0. Source and current-interface boundary

- Protected procedure: `mastermindx-market-intelligence/Mastermind@bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap major 1.
- Current Finance predecessor head: `820e59363fbcebb5ceee86b7800559b65c653a4d`.
- Original Macro research base: `668237947e016f679782e41e61c91c9133a5ea99`.
- Current Macro interface-read pin used for bounded reconnaissance: `fc5c1fc49e4f552d8e3e55b5528a6d280d7415e8`.
- The repository already contains a native analyst-revisions plane, including `data/revisions/latest.parquet` consumption through `engine.analyst_revisions.revision_map`, and a display-tier Leader Radar rerating watch that combines revisions, generic valuation and earnings inputs.
- That existing display logic is useful precedent but is not a Finance-domain valuation contract. This design consumes accepted owner outputs rather than extending a generic stock-page or Leader Radar field into another canonical owner.
- Exact current production paths, provider rights and accepted schemas require refresh immediately before implementation.
- Principal-duty reason: `PRINCIPAL_JUDGMENT`. No worker, Fable receiver, Executive Attempt or watcher was started.

## 1. Outcome

A Finance user should be able to answer:

```text
What did the market expect?
What changed in those expectations?
What business-model-specific anchor was investors valuing?
Was the anchor trailing, forward, normalized, book-based or scenario-based?
What required return or risk discount was embedded?
How much of the operating improvement was already recognized by price?
Did price lead, confirm or contradict estimates and fundamentals?
```

The machine must answer without creating a universal Finance multiple, mixing fiscal periods, laundering stale consensus, or treating a generic sector comparison as economically valid.

## 2. Executive rulings

### R-FIN-EVP-1 — Expectations are plural

Keep separate:

1. analyst consensus;
2. management guidance;
3. statutory/regulatory or contractual expectations;
4. market-implied expectations;
5. house scenarios/interpretation;
6. price/positioning recognition.

No source may silently substitute for another.

### R-FIN-EVP-2 — Estimate level and revision delta remain separate

A high estimate can be falling. A low estimate can be improving. Preserve:

- estimate level;
- prior estimate level;
- revision direction/magnitude;
- number of contributors;
- dispersion;
- age and fiscal period;
- new coverage versus changed view.

### R-FIN-EVP-3 — Valuation anchor follows business economics

The primary anchor must be declared by business model:

- bank/lender: P/TBV, normalized ROTCE versus cost of equity, normalized P/E;
- BDC/credit vehicle: P/NAV, NII/dividend coverage and credit/funding quality;
- payment network/exchange/broker/data/software: P/E, FCF yield, EV/EBITDA with recurring/transaction mix;
- asset/wealth manager: recurring fee earnings, normalized P/E/FCF and flow/fee quality;
- P&C/reinsurer: P/BV or P/TBV versus normalized ROE/BVPS compounding, plus P/E;
- life/annuity: adjusted book, adjusted operating P/E, statutory cash/remittance and SOTP;
- mixed issuer: explicit sum-of-parts or visible mixed-business refusal.

A fallback multiple may be displayed as a limited cross-check, never as the governing anchor.

### R-FIN-EVP-4 — Reported, forward and normalized values are different objects

Closed valuation-basis states:

- `TRAILING_REPORTED`;
- `FORWARD_CONSENSUS`;
- `MANAGEMENT_GUIDANCE`;
- `OWNER_NORMALIZED`;
- `CYCLE_NORMALIZED`;
- `BOOK_OR_NAV_BASED`;
- `SUM_OF_PARTS`;
- `SCENARIO_OR_OPTION_VALUE`;
- `NOT_COMPARABLE`;
- `UNAVAILABLE`.

### R-FIN-EVP-5 — Per-share anchor and share count must align

EPS, FCF/share, BVPS, TBVPS, NAV/share and distributions use the point-in-time diluted/common share basis appropriate to the source. Acquisitions, buybacks, stock compensation, convertibles and issuance remain visible.

### R-FIN-EVP-6 — Fiscal-period identity is mandatory

A consensus number carries:

- issuer/security/business identity;
- fiscal year/quarter;
- period end;
- currency;
- accounting/non-GAAP basis;
- provider/vintage;
- contributor count;
- as-of time.

Calendar-year alignment cannot silently replace issuer fiscal periods.

### R-FIN-EVP-7 — Revision history is correction-safe and prospective

Current latest values alone cannot reconstruct what the market expected historically. Historical evaluation requires the accepted revisions-history owner with original vintages and no later-knowledge backfill.

### R-FIN-EVP-8 — Price recognition is not an expectation source by default

Price can reveal that investors are reacting, but it does not identify the mechanism or expectation without evidence. The product may infer a conflict such as `PRICE_LEADS_FUNDAMENTALS`, not “the market expects X” unless a method and evidence support that claim.

### R-FIN-EVP-9 — Generic peer comparisons can be false

Examples:

- a custody bank versus a regional lender;
- a P&C broker versus an underwriter;
- a card network versus a consumer lender;
- an exchange/data conglomerate versus a pure transaction venue;
- a traditional manager versus an alternative manager;
- a life insurer versus a P&C carrier.

Peer cohorts require business-model and accounting compatibility, not sector membership alone.

### R-FIN-EVP-10 — No fused expected-return score

The view exposes operating, expectation, valuation and price dimensions, conflicts and scenario conditions. It does not compute one Finance opportunity or expected-return score.

## 3. Expectation-source hierarchy

### 3.1 Analyst consensus

Fields:

```text
metric
fiscal_period
estimate_mean/median
high/low
dispersion
contributors
as_of
provider
currency
accounting_basis
revision_delta_7d/30d/90d where accepted
net_up/net_down and breadth where accepted
coverage/rights/freshness
```

Metrics may include:

- revenue;
- EPS;
- BVPS/TBVPS;
- NII/NIM;
- credit/provision/charge-off;
- payment/transaction/volume;
- AUM/flows/fee revenue;
- premium/combined ratio;
- adjusted operating earnings;
- segment/FCF where provider coverage supports it.

Absent estimates remain absent; zero is not substituted.

### 3.2 Management guidance

Fields:

- source filing/call/deck;
- metric and exact wording;
- range/point/direction;
- fiscal period;
- GAAP/non-GAAP/constant-currency basis;
- assumptions/exclusions;
- issue/publication time;
- supersession/withdrawal.

A management target is not consensus or realized fact.

### 3.3 Regulatory/statutory/contractual expectations

Examples:

- capital phase-in;
- policy effective date;
- contractual fee activation;
- loss/capital requirement;
- announced mandate funding;
- committed but not fee-paying assets.

These are owner-native future conditions, not analyst forecasts.

### 3.4 Market-implied expectations

Possible accepted methods:

- reverse residual-income/growth implication;
- option-implied distribution;
- CDS/credit/equity-implied risk;
- price-to-book versus normalized return gap;
- issuance/activity or volume implied by price.

Each method requires its own registered inputs, assumptions, uncertainty and evaluation. No generic reverse-DCF is silently introduced.

### 3.5 House scenarios

A house scenario includes:

- explicit method/version;
- inputs and source vintages;
- scenario probabilities or bands if authorized;
- per-share outcome;
- valuation anchor;
- limitations/falsifiers;
- zero direct trading authority.

Model-generated narrative cannot originate the scenario without an accepted method/owner.

## 4. Valuation observation object

Proposed page/read projection:

```text
finance_valuation_observation.v0_1

identity:
  issuer_id
  business_id_optional
  security_id
  observation_at

anchor:
  anchor_type
  anchor_value
  anchor_period
  anchor_basis
  anchor_source
  normalized_state

market_value:
  price
  market_cap
  enterprise_value_optional
  common_equity_optional
  tangible_common_equity_optional
  nav_optional
  diluted_shares

multiple:
  value
  unit
  basis
  numerator_ref
  denominator_ref

context:
  own_history_percentile_optional
  peer_percentile_optional
  rate_required_return_context
  quality_growth_risk_dimensions[]
  comparability_state

expectations:
  consensus_refs[]
  guidance_refs[]
  implied_refs[]

freshness
coverage
rights
limitations[]
source_records[]
authority_caps
```

This is a design name, not an enrolled contract.

## 5. Finance anchor registry proposal

A small versioned mapping may declare allowed anchors by business model. It must not contain current values, rankings or target multiples.

Example shape:

```text
business_model: regional_bank
primary:
  - P_TBV
  - NORMALIZED_ROTCE_MINUS_COST_OF_EQUITY
secondary:
  - NORMALIZED_PE
invalid_without_extra_context:
  - PRICE_TO_SALES
required_dimensions:
  - TBVPS
  - ROTCE
  - CET1
  - credit/funding state
```

Other initial models:

- money-center/universal bank;
- card/consumer lender;
- payment network;
- processor/core software;
- exchange/clearing;
- custody/asset servicing;
- ratings/data/index;
- traditional asset manager;
- alternative manager;
- wealth/adviser platform;
- BDC;
- mortgage originator/servicer;
- P&C carrier;
- reinsurer;
- life/annuity;
- insurance broker;
- financial/insurance data software.

The registry extends existing owner vocabulary only after accepted review; it is not a valuation service.

## 6. Business-model anchor details

### 6.1 Banks and lenders

Required:

- price and P/TBV/P/BV;
- TBVPS/BVPS period and reconciliation;
- normalized ROTCE/ROE;
- cost-of-equity or required-return context as a separate assumption/source;
- EPS/credit/funding/capital forecasts;
- AOCI/acquisition/day-one CECL and share-count effects;
- peer cohort.

Refuse reassurance when:

- TBV is unavailable or basis inconsistent;
- reported ROE is distorted and normalization unavailable;
- negative/near-zero book makes multiple uninterpretable;
- acquisition/restructuring destroys comparability.

### 6.2 BDCs and credit vehicles

Required:

- price/NAV and NAV vintage;
- NII/share and dividend coverage;
- cash versus PIK income;
- nonaccruals/marks/leverage/funding;
- manager fees and dilution;
- credit cycle.

High yield does not substitute for NAV and loss quality.

### 6.3 Networks, exchanges, processors and software

Required:

- forward/trailing EPS and FCF;
- EV/EBITDA where debt/acquisitions matter;
- recurring versus transaction revenue;
- volume/take rate/RPC/incentive or ARR/retention economics;
- margin and capital intensity;
- organic/acquired mix.

Revenue multiple requires a mature-margin/cash-conversion bridge.

### 6.4 Asset and wealth managers

Required:

- recurring base-fee earnings or FCF;
- average fee-paying AUM;
- organic flows and fee rate;
- performance/realization income separately;
- market beta and share count/capital return;
- wealth cash/bank economics separately where material.

Price/AUM remains descriptive only unless fee/margin economics match.

### 6.5 P&C/reinsurance

Required:

- P/BV/P/TBV and current book vintage;
- normalized underwriting and investment earnings;
- current-year, catastrophe and reserve-development state;
- normalized ROE/volatility and capital;
- BVPS compounding with dividend/share-count treatment.

A low P/E in a benign-loss year is not automatically cheap.

### 6.6 Life/annuity

Required:

- adjusted book definition and AOCI/MRB exclusions;
- adjusted operating EPS and reconciliation;
- statutory cash/remittance and capital;
- spread/fee/insurance/assumption state;
- SOTP for mixed/legacy/international businesses.

### 6.7 Brokers/data

Required:

- organic versus acquired revenue;
- normalized margin and FCF;
- debt/earnout/equity issuance;
- recurring/transaction/advisory mix;
- retention/new business/ACV where applicable.

## 7. Revision observation object

```text
finance_expectation_observation.v0_1

identity
metric
fiscal_period
as_of
provider
level
prior_level
revision_delta
revision_window
contributors
net_up/net_down
breadth
dispersion
new_coverage_count
currency
accounting_basis
source_generation
freshness
coverage
rights
limitations[]
authority_caps
```

Existing `revision_map` and historical revision owners should be consumed where accepted. Do not re-implement net-up/breadth definitions in the Finance adapter.

## 8. Alignment and join rules

### 8.1 Identity

Join only through validated issuer/security/listing/business bridges. Ticker text alone is insufficient.

### 8.2 Time

At read time preserve:

- market close/session;
- consensus as-of;
- filing/guidance publication;
- financial period;
- valuation observation;
- source generation.

A page generated today cannot make stale consensus current.

### 8.3 Fiscal period

Match FY/Q estimates to the issuer’s fiscal calendar and current corporate structure. Recast/restated history stays versioned.

### 8.4 Accounting basis

Do not compare:

- GAAP EPS with adjusted EPS;
- stated book with adjusted book;
- reported combined ratio with normalized/CAY ex-cat;
- ARR with revenue;
- FCF with adjusted EBITDA;
- NII with EPS.

### 8.5 Currency and FX

Preserve reporting currency, price currency and FX conversion vintage. Constant-currency growth remains issuer-native.

### 8.6 Corporate actions

Splits, mergers, spinoffs, share classes, conversions, issuance and buybacks use the security/corporate-action owner.

### 8.7 Business composition

If consensus is consolidated but research is business-line specific:

- show consolidated expectation separately;
- use segment expectations only when source/provider supports them;
- do not allocate consensus mechanically from current revenue share.

## 9. Expectation-versus-realization bridge

For each report/event:

```text
reported value
− matched consensus/reference value
= surprise
```

But the product must also preserve:

- guidance versus consensus;
- quality/mix/cash/capital effects;
- comparable/one-time items;
- estimate revisions after the report;
- price reaction;
- valuation change.

A headline beat can accompany lower forward expectations.

### 9.1 Finance-specific surprise families

**Banks**

- NII/NIM;
- fees;
- provision/credit;
- expense;
- CET1/TBVPS;
- guidance.

**Payments/exchanges**

- volume/cross-border/ADV/RPC;
- incentives/rebates;
- recurring data/services;
- margin/FCF.

**Managers/wealth**

- organic flows;
- fee rate;
- average AUM/client assets;
- cash/payout/expense;
- capital return.

**Insurance**

- CAY ex-cat/combined ratio;
- catastrophe/prior development;
- premium/rate;
- investment income;
- reserve/capital/BVPS.

**Data/software/brokers**

- organic/ARR/ACV;
- acquired revenue;
- margin/FCF;
- debt/share count.

## 10. Four-plane conflict grammar

Proposed display-level conflicts:

- `OPERATING_UP_EXPECTATIONS_UP_VALUATION_FLAT_PRICE_UP`
- `OPERATING_UP_EXPECTATIONS_UP_VALUATION_COMPRESSES`
- `OPERATING_UP_EXPECTATIONS_DOWN`
- `EXPECTATIONS_UP_PRICE_DIVERGES`
- `PRICE_LEADS_EXPECTATIONS`
- `PRICE_RERATES_WITHOUT_EARNINGS_MATERIALITY`
- `REPORTED_BEAT_FORWARD_CUT`
- `EPS_UP_PER_SHARE_BOOK_DOWN`
- `AUM_UP_BASE_FEE_EXPECTATIONS_DOWN`
- `PREMIUM_UP_COMBINED_RATIO_EXPECTATIONS_WORSE`
- `ADOPTION_UP_REVENUE_EXPECTATIONS_UNCHANGED`

The adapter should generate plain-language explanations from owner observations, not treat these labels as a new lifecycle or signal state.

## 11. Valuation context and peer construction

### 11.1 Peer eligibility

Require:

- compatible business model;
- comparable accounting/metric basis;
- comparable geography/regulatory regime where material;
- source-qualified current observation;
- no unresolved transformative corporate action;
- adequate sample size.

### 11.2 Own-history context

Use point-in-time historical observations from the valuation owner. Current scraped values without history cannot support a percentile.

### 11.3 Required-return context

Keep separately sourced dimensions:

- risk-free/real/long yields;
- credit spread;
- equity-risk/capital/risk regime;
- business-specific tail risk;
- leverage/duration/capital intensity.

Do not turn them into one unvalidated cost-of-equity estimate.

### 11.4 Comparability states

- `COMPARABLE`
- `PARTIAL_BUSINESS_MIX`
- `ACCOUNTING_BASIS_MISMATCH`
- `FISCAL_PERIOD_MISMATCH`
- `NEGATIVE_OR_NONMEANINGFUL_DENOMINATOR`
- `INSUFFICIENT_PEERS`
- `HISTORICAL_SERIES_UNAVAILABLE`
- `RIGHTS_RESTRICTED`
- `IDENTITY_UNRESOLVED`

## 12. Price-recognition join

Consume accepted price/relative-strength/breadth owners. Proposed dimensions:

- price through date;
- absolute and sector/subtheme-relative returns;
- multi-horizon relative strength;
- drawdown and distance from prior high;
- participation/concentration;
- reaction to eligible source event;
- current stale/coverage state;
- entry/eligibility reference only through incumbent owner.

The Finance adapter may classify timing relationships:

- `PRICE_LEADS`
- `PRICE_CONFIRMS`
- `PRICE_LAGS`
- `PRICE_DIVERGES`
- `UNAVAILABLE`

It may not originate a buy/sell/entry decision.

## 13. Current-state product projection

For each company/business/subtheme, expose:

```text
operating_path
expectation_level_and_revision
valuation_anchor_and_basis
valuation_context
price_recognition
conflicts[]
what_changed[]
watch_conditions[]
source_records[]
coverage/freshness/rights
authority_caps
```

### 13.1 Glance copy examples

- “Operating evidence is improving and estimates are rising, but the multiple has already expanded.”
- “Reported earnings improved while tangible-book and credit expectations remain mixed.”
- “Organic flows have not confirmed the market-driven AUM increase.”
- “Price is leading, but no material revenue is yet reported from the structural-change theme.”

No “cheap,” “expensive,” “buy,” “avoid” or probability language without an accepted method/authority.

## 14. Historical evaluation compatibility

Every expectation/valuation observation used in the casebook must preserve the original vintage. Required negative proof:

- no current consensus backfill;
- no later restatement used as earlier knowledge;
- no current peer membership unless labeled non-PIT;
- no outcome-selected normalized anchor;
- no provider revision-history reconstruction from latest values.

## 15. Rights and access

Consensus, valuation and market data are commonly licensed. The product must preserve:

- provider and entitlement;
- tenant/user scope;
- display/redistribution limits;
- private/no-store response;
- no public fixture/screenshots/source-map leakage;
- derived-result rights.

When rights do not permit detail, show a typed unavailable/limited state rather than copying values into public artifacts.

## 16. Validation and refusal tests

Reject/hold when:

- identity is ticker-guessed;
- estimate provider/as-of/fiscal period is missing;
- GAAP/non-GAAP basis is ambiguous;
- current valuation uses stale price or stale denominator;
- forward multiple denominator is negative/nonmeaningful;
- a book multiple lacks book-vintage/basis;
- a peer cohort mixes incompatible business models;
- an own-history percentile lacks point-in-time history;
- a consolidated estimate is allocated to business lines without evidence;
- price state is used to infer a specific expectation;
- consensus rights do not permit display;
- a current latest value is used in historical evaluation;
- any output grants ranking/trading authority.

## 17. Implementation boundary

A future implementation should:

1. discover and consume the accepted revisions, valuation, company, market and identity interfaces;
2. add the business-model anchor registry only if the current vocabulary owner accepts it;
3. implement a pure read adapter and typed refusals;
4. validate first-vertical records;
5. show four-plane conflicts on the authenticated Finance dossier;
6. preserve source generations and rights;
7. accrue point-in-time histories only through existing owners;
8. obtain browser/privacy/degraded proof.

It must not create a second consensus collector, valuation history, peer database, target-price service or rerating scorer.

## 18. Explicit non-claims

This design does not establish:

- current accepted Finance valuations;
- current consensus coverage or rights;
- normalized target multiples;
- price-implied forecasts;
- historical valuation series;
- implementation, tests, CI or deployment;
- predictive edge or trade authority.

## 19. Exact next action

Continue principal research with the global/regional Finance extension and a preregistered small historical casebook fixture. At the implementation-plan boundary, refresh the exact revisions/valuation/market interfaces and map this contract to current accepted owners.
