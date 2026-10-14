# Finance rerating historical and prospective evaluation design — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Carrier:** Macro Draft/HOLD PR #7786, `sol/finance-sector-research-20260923`  
**State:** EVALUATION DESIGN PROPOSAL / DRAFT-HOLD  
**Mission complete:** false  
**Authority:** research/evaluation design only. No production store, source admission, feature promotion, ranking, recommendation, entry, sizing or trade authority is created.

## 0. Source, ownership and no-duplicate boundary

- Protected procedure: `mastermindx-market-intelligence/Mastermind@bf764f494b9cd0ecede6234bb472c3344c8e77cc`, Skillpack 1.0.1/bootstrap major 1.
- Prior Finance research head at entry: `14a117f936cda29e4742d2b618d25d78112896da`.
- Original Macro research base: `668237947e016f679782e41e61c91c9133a5ea99`.
- Existing canonical owners retain security identity, market prices, corporate actions, earnings facts, analyst revisions, valuation, Theme Graph/ThemeState, macro/rates/credit facts and outcome/evaluation infrastructure.
- This design proposes Finance-specific episode definitions and comparison law to be implemented through accepted owners. It does not create a second QLedger, outcome store, price store, consensus history, experiment service or promotion authority.
- Principal-duty reason: `PRINCIPAL_JUDGMENT`. No worker, Fable receiver, Executive Attempt or watcher was started.

## 1. Executive ruling

### R-FIN-EVAL-1 — The object of evaluation is a dated rerating state, not a stock label

The unit is:

```text
company/business/subtheme
+ observation date/time
+ operating state
+ expectation state
+ valuation state
+ price-recognition state
+ evidence quality
+ authority limits
```

A ticker by itself is not an episode. The same company can exhibit several economically different states across time.

### R-FIN-EVAL-2 — Finance outcomes require both fundamental and market dimensions

Every eligible episode should measure, where applicable:

**Fundamental realization**

- revenue/fee/premium/NII/underwriting growth;
- EPS/FCF/BVPS/TBVPS/NAV/share change;
- margin/combined ratio/ROTCE/ROE;
- flow/credit/reserve/capital realization;
- share count and capital distribution.

**Market realization**

- absolute and benchmark-relative return;
- subtheme-relative return;
- valuation-multiple change;
- estimate-revision path;
- drawdown, volatility and time-to-recognition;
- participation/breadth where a group is evaluated.

A positive stock outcome with no fundamental realization may reflect a risk-discount or narrative rerating. A strong fundamental outcome with poor stock return may reflect prior expectations or multiple compression. Both are valid outcomes and remain distinct.

### R-FIN-EVAL-3 — Historical reconstruction must be point-in-time

Inputs use only information available at the observation cutoff. Prohibited:

- using a later restatement as earlier knowledge;
- selecting members from today’s basket without a non-PIT label;
- using later reserve development in the initial state;
- using final acquisition outcomes at announcement date;
- using revised consensus that had not yet been published;
- using current company segments before a historical reorganization;
- outcome-picked start dates.

### R-FIN-EVAL-4 — Rerating is decomposed, not scored

The evaluation preserves separate vectors:

```text
operating_delta
expectation_delta
valuation_delta
price_recognition_delta
capital_and_share_count_delta
risk_realization_delta
```

No universal Finance rerating score is authorized.

### R-FIN-EVAL-5 — Archetype-specific success law

Success differs by archetype.

- A bank risk-normalization episode may succeed through P/TBV recovery and declining funding/credit tail risk before EPS growth.
- A payment-network quality episode may require sustained EPS/FCF and multiple durability.
- An insurer underwriting episode may require reserve-quality and BVPS realization, not only a low current combined ratio.
- An asset-manager flow episode requires organic fee-base and earnings realization rather than market-driven AUM.
- A disruption episode may first produce a permission or adoption rerating while earnings remain optionality.

### R-FIN-EVAL-6 — Valuation cohort is mandatory

The same operating change can produce opposite stock returns at different starting valuations. Every episode preserves:

- valuation anchor;
- level and historical/peer percentile where accepted;
- required-return proxy/context;
- profit/return normalization state;
- price already moved before observation;
- crowding/ownership context where accepted.

### R-FIN-EVAL-7 — Regime and business mix are effect modifiers

At minimum preserve:

- policy/real/long-rate regime;
- curve shape;
- credit spread/default regime;
- equity/volatility/issuance regime;
- inflation/loss-cost regime;
- catastrophe/reinsurance capital regime;
- liquidity/risk-appetite regime;
- company business mix and capital model.

Do not pool unlike regimes merely to increase sample size.

### R-FIN-EVAL-8 — Causal claims require stronger evidence than descriptive association

The evaluation may show that a state historically preceded an outcome. It may not claim causality unless design and evidence support it. Membership, similarity and co-movement do not prove transmission.

### R-FIN-EVAL-9 — Promotion is separate from research usefulness

Descriptive historical results may improve dossiers and watch conditions. Any use in ranking, gating, selection, sizing or trade policy requires separate accepted promotion through existing evaluation and authority owners.

## 2. Episode object

Proposed research projection:

```text
finance_rerating_episode.v0_1

identity:
  episode_id
  issuer_id
  business_id_optional
  security_id
  subtheme_or_research_slice
  archetype

clocks:
  observation_at
  market_session
  belief_cutoff
  source_publication_cutoff
  business_effective_at_optional
  period_end_optional
  correction_vintage

state:
  operating_dimensions[]
  expectation_dimensions[]
  valuation_dimensions[]
  price_recognition_dimensions[]
  capital_and_share_count_dimensions[]
  risk_dimensions[]
  conflicts[]

scope:
  product
  geography
  customer
  currency
  accounting_basis
  consolidation_basis

quality:
  source_coverage
  identity_health
  freshness
  point_in_time_health
  comparability
  rights
  null_reasons[]

hypothesis:
  mechanism
  expected_sequence
  catalysts[]
  falsifiers[]
  expected_horizon_range

authority_caps
source_records[]
```

This is not an enrolled wire contract.

## 3. Closed rerating-archetype vocabulary

Initial research vocabulary:

1. `CYCLICAL_EARNINGS_INFLECTION`
2. `RISK_DISCOUNT_NORMALIZATION`
3. `QUALITY_DURABILITY_UPGRADE`
4. `STRUCTURAL_GROWTH_SHARE_GAIN`
5. `CAPITAL_RELEASE_RETURN`
6. `BUSINESS_MIX_TRANSFORMATION`
7. `OPERATING_LEVERAGE`
8. `REGULATORY_MARKET_STRUCTURE_CHANGE`
9. `CONSOLIDATION_SCALE`
10. `DISCOUNT_RATE_FACTOR_RERATING`
11. `PERMISSION_OR_OPTION_VALUE`
12. `OVEREARNING_DERATING`
13. `LOSS_RESERVE_OR_CREDIT_IMPAIRMENT`
14. `FUNDING_LIQUIDITY_REPRICING`
15. `FLOW_FEE_INFLECTION`
16. `UNDERWRITING_RATE_ADEQUACY_INFLECTION`
17. `ADOPTION_MONETIZATION_INFLECTION`

A single episode may have one primary archetype and bounded secondary mechanisms. Arbitrary labels are refused.

## 4. State dimensions by Finance family

### 4.1 Banks and lenders

- deposit balance/mix/cost/beta;
- wholesale funding and liquidity;
- asset yield/repricing;
- loan growth/mix;
- origination vintage;
- delinquency/nonaccrual/charge-off/recovery;
- provision and allowance;
- NII/NIM/PPNR;
- CET1/RWA/stress/capital return;
- EPS/ROTCE/TBVPS;
- consensus and P/TBV/P/E;
- price/relative strength/breadth.

### 4.2 Payments and market infrastructure

- volume/transactions/cross-border/open interest/ADV;
- take rate/RPC/incentives/rebates;
- recurring data/service/software mix;
- operating margin/FCF;
- capital requirements and settlement/counterparty risk;
- revisions and P/E/FCF/EV multiple;
- price recognition.

### 4.3 Asset managers and wealth

- organic flows;
- market/FX/acquisition bridge;
- average fee-paying AUM;
- fee rate and product mix;
- performance and distribution;
- advisor/account/participant growth;
- client cash and funding;
- margin/FCF/capital return;
- expectations and valuation;
- price recognition.

### 4.4 P&C/reinsurance

- exposure and written rate;
- written/earned premium;
- CAY ex-cat loss and expense;
- catastrophe and prior development;
- reserve/capital/reinsurance;
- investment income;
- normalized operating earnings and BVPS/TBVPS;
- expectations, P/B/P/E and price.

### 4.5 Life/annuity/retirement

- sales/deposits/premium/account values;
- fee/spread/insurance margin;
- mortality/morbidity/longevity/lapse;
- assumption/reserve/hedge state;
- statutory/RBC/liquidity/remittance;
- adjusted/GAAP earnings and adjusted book;
- expectations, valuation and price.

### 4.6 Brokers/data/software

- organic/acquired/FX growth;
- retention/new business/ACV;
- commission/subscription/transaction mix;
- fiduciary interest or rate-sensitive revenue;
- margin/FCF/leverage/share count;
- expectations and P/E/FCF/EV multiple;
- price recognition.

### 4.7 Structural disruption

- legal state;
- operational state;
- adoption;
- monetization;
- margin/loss/capital effect;
- legacy cannibalization;
- earnings materiality;
- expectation/valuation/price state.

## 5. Observation anchors

Eligible anchors must be objectively reproducible:

- filing or earnings publication timestamp;
- regulator/statutory release;
- finalized law/rule/effective date;
- temporary exemption/approval timestamp;
- source-backed operating threshold crossing;
- owner-recorded state transition;
- closed market session after eligible information became public;
- point-in-time revision/valuation observation from accepted owner.

Ineligible as the sole anchor:

- final outcome date;
- arbitrary chart low/high;
- undated narrative;
- source file modification time;
- current research curation date substituted for business/publication date.

### 5.1 Market-entry clock

Research outcomes may begin at:

- next eligible close after public information;
- next open or VWAP only if accepted market-data/execution design supports it;
- an owner-specific served-session state.

This program does not establish executable entry assumptions.

## 6. Outcome horizons

Initial descriptive horizons:

```text
1 session
5 sessions
21 sessions
63 sessions
126 sessions
252 sessions
504 sessions where history permits
```

Fundamental outcomes use issuer-appropriate reporting horizons:

- next quarter;
- two quarters;
- four quarters;
- eight quarters;
- annual/accident-year/vintage development where relevant.

Do not force long-tail reserve or credit realization into short equity horizons.

## 7. Market outcome definitions

For each horizon:

- total return;
- benchmark-relative return;
- Financials-sector-relative return;
- subtheme/cohort-relative return;
- maximum drawdown;
- volatility;
- upside/downside capture;
- change in valuation multiple;
- change in estimate path;
- time to peak/trough;
- breadth/participation where group-level.

Benchmarks remain explicit:

- broad market;
- sector;
- business-model cohort;
- factor-matched control;
- macro-driver-matched control where defensible.

## 8. Fundamental outcome definitions

### 8.1 Per-share compounding

Applicable:

- EPS;
- FCF/share;
- BVPS/TBVPS;
- NAV/share;
- dividend/distribution per share;
- diluted share count.

### 8.2 Operating realization

- revenue/fee/NII/premium growth;
- organic flows;
- fee yield;
- margin/efficiency;
- credit loss and reserve state;
- combined ratio and reserve development;
- FRE/NII/underwriting/spread earnings;
- regulatory/statutory capital;
- cash remittance/capital return.

### 8.3 Expectation realization

- consensus EPS/revenue/book/flow/combined-ratio revisions;
- dispersion;
- target/ratings only as secondary context with source/coverage;
- management guidance revisions;
- implied expectation changes where an accepted method exists.

## 9. Initial hypothesis families

These are preregistration candidates, not accepted findings.

### H-FIN-01 — Bank P/TBV rerating requires normalized ROTCE-cost-of-equity improvement

Hypothesis:

- risk-discount normalization without durable normalized ROTCE improvement produces a bounded rerating;
- durable P/TBV expansion requires improved per-share TBV growth and a lower expected tail-risk burden.

Falsifier:

- P/TBV expansion persists without ROTCE/TBVPS improvement after controlling for rates/credit/market.

### H-FIN-02 — NII growth without funding and credit quality has weak durability

Falsifier:

- NII-only episodes deliver similar long-horizon per-share and stock outcomes as matched multi-clock episodes.

### H-FIN-03 — Payment-network quality rerating depends on net monetization, not gross volume

Hypothesis:

- volume/cross-border/service growth supports durable rerating only when incentives, loss/regulatory cost and margin preserve FCF/share.

### H-FIN-04 — Exchange rerating is strongest when recurring mix and structural volume broaden together

Test transaction-only, recurring-only and combined episodes separately.

### H-FIN-05 — Asset-manager flow inflection requires fee-base confirmation

Hypothesis:

- market-driven AUM or low-fee inflows without base-fee/FCF realization do not support the same rerating as organic high-quality flow inflection.

### H-FIN-06 — Wealth organic gathering is more durable than acquisition/recruiting asset growth

Compare same-store organic cohorts with acquisition/recruiting-heavy cohorts after debt, dilution and transition expense.

### H-FIN-07 — P&C rerating requires current-year underwriting and reserve credibility

Hypothesis:

- combined-ratio improvement led by favorable prior development has weaker forward BVPS/stock outcomes than CAY ex-cat improvement with credible reserves.

### H-FIN-08 — Reinsurance hard-market rerating decays when capital enters before terms/loss economics weaken visibly

Track rate/terms/capacity, not only premium growth.

### H-FIN-09 — Life-insurer rerating requires cash/remittance and capital confirmation

Hypothesis:

- adjusted earnings growth without statutory/cash/book confirmation has weaker durability.

### H-FIN-10 — Broker acquisition growth requires per-share FCF/deleveraging proof

Compare organic-led, acquisition-led-with-proof and acquisition-led-without-proof cohorts.

### H-FIN-11 — Recurring data/software rerating requires organic growth and FCF, not subscription share alone

### H-FIN-12 — Regulatory permission creates announcement rerating before earnings, but durability depends on adoption and monetization

Apply to stablecoins, tokenized securities, clearing, open banking and other rule-dependent changes.

### H-FIN-13 — Price often leads Finance fundamentals at tail-risk inflections

Measure whether price/relative strength stabilizes before estimate/fundamental confirmation in risk-discount episodes, while guarding against outcome-picked lows.

### H-FIN-14 — Starting valuation controls the payoff from otherwise similar fundamental improvement

Stratify by accepted valuation percentile rather than fitting one global relationship.

## 10. Initial historical episode families

These are candidate casebook strata, not accepted conclusions.

### 10.1 Bank rate/funding cycle

- pre-hike asset sensitivity;
- early NIM expansion;
- deposit-beta inflection;
- duration/liquidity crisis;
- funding normalization;
- credit normalization/deterioration.

Potential periods include 2015–2019 and 2021–2026, separated by reserve regime, institution size and business mix.

### 10.2 Payment/travel cycle

- 2020 cross-border collapse;
- reopening/recovery;
- normalization and service-mix expansion;
- regulatory/incentive pressure.

### 10.3 Exchange/market-activity cycle

- volatility/trading spikes;
- issuance and listing cycles;
- options/derivatives structural growth;
- recurring data/technology mix transformation.

### 10.4 Asset-management flow cycle

- secular active outflows;
- ETF/index inflows;
- fixed-income flow turns;
- target-date/retirement persistence;
- private-market fundraising/deployment/realization cycles.

### 10.5 Wealth cash-sorting cycle

- near-zero-rate cash economics;
- rapid tightening and deposit/sweep migration;
- supplemental funding/normalization;
- advisory and asset gathering offset.

### 10.6 Insurance pricing/reserve cycle

- personal-auto loss-cost shock and repricing;
- commercial hard/soft market;
- casualty reserve deterioration;
- catastrophe/reinsurance capacity cycle;
- investment-income repricing.

### 10.7 Life/annuity spread and assumption cycle

- low-rate spread compression;
- rising-rate new-money yield;
- surrender/competition response;
- assumption/reinsurance/runoff actions;
- capital/remittance changes.

### 10.8 Broker consolidation cycle

- organic exposure/rate growth;
- acquisition wave;
- leverage/integration/deleveraging;
- rate moderation and organic-quality test.

### 10.9 Disruption cycle

- rule/approval announcement;
- production pilot;
- commercial launch;
- adoption;
- monetization;
- earnings realization;
- incident/regulatory correction.

## 11. Cohort construction

### 11.1 Company/business model cohorts

Closed initial cohort families:

- money-center/universal banks;
- regional/community banks;
- card/consumer lenders;
- auto finance;
- mortgage originators/servicers;
- payment networks/processors;
- exchanges/clearing/market infrastructure;
- custody/asset servicing;
- ratings/data/index providers;
- traditional asset managers;
- alternative managers;
- wealth/advisor platforms;
- retirement/recordkeeping;
- P&C personal/commercial/specialty;
- reinsurers;
- life/annuity;
- insurance brokers;
- financial/insurance software/data.

### 11.2 Point-in-time membership

Preferred:

- historical owner roster/evidence.

Fallback:

- current membership labeled `CURRENT_MEMBERSHIP_NON_PIT` and excluded from claims requiring unbiased historical membership.

### 11.3 Multi-business issuers

Use business exposure weights only when source-backed. Otherwise:

- evaluate issuer-level outcome with visible mixed-business limitation;
- do not duplicate the same security as independent observations across cohorts;
- cluster standard errors or use one primary classification with secondary flags.

## 12. Valuation state

### 12.1 Anchor selection

Per episode select one primary valuation anchor based on business model:

- P/TBV and normalized ROTCE for banks;
- P/E/FCF for networks/exchanges/brokers/software;
- P/BV/P/TBV and normalized ROE for insurers;
- NAV and NII/distribution for BDCs;
- recurring fee earnings/FCF for managers;
- SOTP for mixed issuers.

### 12.2 Normalization

State whether valuation uses:

- reported trailing;
- forward consensus;
- normalized/cycle-adjusted;
- owner-derived scenario;
- unavailable.

Never compare a loss-year P/E with normalized profitable peers as if comparable.

### 12.3 Valuation cohorts

Suggested descriptive cohorts:

- own-history percentile;
- peer percentile;
- required-return/rate regime;
- high/medium/low only after thresholds are preregistered from training data or economically fixed, not outcome-optimized.

## 13. Expectation state

Preserve:

- estimate vintage and provider;
- fiscal period;
- mean/median and contributor count;
- dispersion;
- revision direction/magnitude;
- new-estimate versus changed-estimate distinction;
- corporate-action/segment/accounting comparability;
- rights and coverage.

Missing consensus remains missing. Management guidance and market-implied expectations are separate sources.

## 14. Price-recognition state

Descriptive dimensions may include accepted owner outputs for:

- absolute and sector-relative trend;
- multi-horizon relative strength;
- breadth/participation;
- volume/turnover;
- volatility and drawdown;
- gap/reaction to eligible evidence;
- short interest/options/ownership only under their own source/authority.

No chart pattern creates a fundamental or causal claim.

## 15. Confound and bias controls

### 15.1 Overlapping events

Flag or exclude episodes with:

- M&A;
- capital raise/buyback authorization;
- major litigation/regulatory action;
- index addition/deletion;
- accounting/tax change;
- crisis-wide intervention;
- simultaneous macro shock;
- catastrophic loss;
- segment sale/spin;
- data-definition change.

Overlapping events may be studied as joint archetypes rather than silently ignored.

### 15.2 Survivorship and delisting

Include acquired, failed, delisted and reorganized firms where data/identity permit. Excluding failures biases risk-normalization studies.

### 15.3 Look-ahead

Freeze:

- source availability;
- membership;
- consensus;
- financial restatement vintage;
- corporate action;
- index/sector classification;
- security/listing identity.

### 15.4 Publication delay

Use actual filing/release/publication time, not period end. If only date is known, use conservative next-session availability.

### 15.5 Multiple hypothesis control

- preregister primary archetype/dimensions/horizons;
- keep a holdout period;
- report all tested cohorts;
- apply false-discovery or family-wise controls as appropriate;
- avoid choosing the best horizon after observing results;
- record failed/null studies.

### 15.6 Repeated company observations

Use clustered or block-aware inference. Do not treat quarterly observations from one issuer as independent firms.

## 16. Counterfactual/control design

Control hierarchy:

1. same business-model cohort, same date;
2. valuation-matched cohort;
3. size/quality/profitability/beta matched;
4. sector/market benchmark;
5. event-time placebo;
6. time-shifted state;
7. random eligible company within cohort;
8. alternative mechanism state.

No single control is universally sufficient.

## 17. Return and fundamental attribution

### 17.1 Return decomposition

Where data permit:

```text
stock return
≈ per-share anchor growth
+ multiple change
+ distribution yield
+ residual / interaction
```

This is an accounting approximation, not a causal model.

### 17.2 Fundamental bridge attribution

Examples:

**Bank**

```text
EPS/TBVPS
← NII + fees − expense − credit loss − tax ± share count/capital
```

**Asset manager**

```text
FCF/share
← average fee-paying AUM × fee rate + other
 − expense − tax ± share count
```

**P&C insurer**

```text
BVPS
← underwriting + investment income + realized/other
 − tax − dividends ± buybacks/issuance/market value
```

**Broker/data**

```text
FCF/share
← organic + acquired + price/volume/mix
 − compensation/integration/interest/capex ± share count
```

## 18. Casebook protocol

Every case contains:

```text
case_id
why selected under a non-outcome rule
business model
pre-observation state
public evidence available then
expectation/valuation/price state
mechanism and falsifiers
subsequent fundamental path
subsequent market path
multiple/per-share decomposition
alternative explanations
what would have made the case ineligible
source records
```

Do not write a retrospective story without the eligibility rule and contemporaneous evidence.

### 18.1 Positive, negative and null cases

For each archetype include:

- successful rerating;
- false positive;
- correct fundamentals but poor stock outcome;
- stock rerating without later fundamental confirmation;
- unavailable/ambiguous case.

## 19. Prospective shadow evaluation

### 19.1 Admission

A research state enters the prospective tape only after:

- identity and source eligibility;
- complete required dimensions or typed nulls;
- immutable observation cutoff;
- preregistered mechanism, horizons and falsifiers;
- zero direct ranking/trade authority.

### 19.2 Correction

Same-session corrections supersede under owner contract. Later evidence does not rewrite the original state; it creates a new observation and outcome update.

### 19.3 Accrual

Outcomes accrue automatically through accepted market/fundamental owners. The Finance program must not build a second price collector or scheduler.

### 19.4 Reporting

Report:

- sample size and coverage;
- missing/null state;
- estimate and uncertainty;
- regime and valuation splits;
- placebo/control;
- failed/null hypotheses;
- no promotion claim unless separately accepted.

## 20. Evaluation acceptance ladder

1. **Schema/semantic validity** — fields mean what they say.
2. **Historical reconstruction validity** — no look-ahead or identity errors.
3. **Reproducible descriptive results** — exact inputs and code.
4. **Adversarial review** — alternative explanations, leakage and confounds.
5. **Holdout result** — no threshold shopping.
6. **Prospective shadow accrual** — natural-time observations.
7. **Calibration/stability** — regime, source and population robustness.
8. **Product usefulness** — users interpret states correctly.
9. **Separate promotion decision** — only if a decision-bearing use is proposed.

Research/product display may ship before predictive promotion if it remains truthful and non-decision-bearing.

## 21. Evaluation wire proposal

A future owner-compatible projection may include:

```text
finance_rerating_evaluation.v0_1

episode_ref
archetype
cohort
observation_state_ref
outcome_horizon
market_outcome
fundamental_outcome
expectation_outcome
valuation_outcome
capital_share_count_outcome
risk_outcome
control_outcome
coverage
regime
confounds[]
method_version
source_refs[]
authority_caps
```

This is a design proposal, not an enrolled contract.

## 22. Product interpretation law

Allowed copy:

- “Historically, comparable source-qualified episodes showed…”
- “The sample is small/thin/conflicted.”
- “Fundamentals improved, but the multiple compressed.”
- “Price led estimate stabilization in this cohort.”
- “This is context, not a forecast or trade signal.”

Disallowed without accepted evidence:

- “This stock will rerate.”
- “The setup has a 70% win rate” from an outcome-picked/small cohort.
- “The model predicts…” when only descriptive association exists.
- “Cheap/expensive” without anchor and normalization.
- “Best Finance theme” from a fused score.

## 23. Initial implementation sequence for evaluation

### E0 — Semantic fixture

Create a small closed set of manually reviewed episodes across different business models to prove clocks, nulls and outcome joins.

### E1 — Historical casebook

Build positive/negative/null cases under preregistered eligibility; no broad backtest yet.

### E2 — Cohort reconstruction

Establish point-in-time membership, identity and source-availability proof.

### E3 — Descriptive cohort study

Run primary archetypes/horizons with controls and full null reporting.

### E4 — Holdout/adversarial review

Freeze methods before holdout.

### E5 — Prospective shadow

Accrue natural-time states under existing owners.

### E6 — Product outcome context

Expose only accepted descriptive/calibrated results with coverage and authority limits.

### E7 — Separate promotion review if ever warranted

No automatic progression to ranking or trading.

## 24. Explicit non-claims

This design does not claim:

- a completed historical dataset;
- accepted point-in-time memberships;
- validated predictive relationships;
- calibrated probabilities;
- implementation or prospective tape;
- product acceptance;
- ranking, selection or trade authority.

## 25. Exact next action

Freeze the Finance product experience and owner-preserving read/data contract, then run a whole-program gap/collision review. Only after those research/design gates should the final implementation plan and Fable CEO handoff be drafted.
