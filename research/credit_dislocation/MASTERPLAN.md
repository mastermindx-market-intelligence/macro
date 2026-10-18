# Credit Dislocation Intelligence - implementation masterplan

Status: first issuer-comparison backend, Bonds component and pipeline wiring implemented locally and preserved in draft PR #9590. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for observed tests and remaining gates. No deployment, live CDS access, calibrated forecasts or subscriber data rights are claimed.

Owner: existing Corporate Credit Watch (CCW), Macro repository. Operation: `web-ccw-dislocation-20261018-sol001`.
Chairman commission: create and publish the full masterplan, then implement research, infrastructure, backend, Paper design, frontend and total integration across subsequent useful phases.
Source base: `29438bef07502bec9a410092316012b0dcb5562f`. Protected Mastermind law: `ef4be2f5c9b0b82fc11be83f03cf7bcdb8cea6f2`, skillpack 1.0.1/bootstrap 1. Existing corrective PR: #9589 at `270380d8aeefc4e5458c6cb74bb84be4c39745aa`. R30 Paper reference: #9578 at `0ff079356ec41d8a64307885bcb771a441297ceb`.

## 1. Product outcome and completion ruler

An investor opens Macro, notices concentrated borrower stress before it is hidden in an index average, identifies the actual bonds and issuer, compares credit with the corresponding equity, inspects the financing mechanism and strongest countercase, saves the analysis through existing owners, and returns to a dated account of what changed and how the original thesis resolved.

The machine does five jobs: normalize legal/instrument identity; measure rate-adjusted credit deterioration; distinguish joint repricing from disagreement; preserve genuinely available evidence over time; assess whether credit eventually normalizes or equity suffers subsequent damage. It must abstain when the data cannot answer the question.

Completion means lawful data and clocks; usable bond/issuer/basket analysis; true debt-obligation coverage where claimed; independently verified pricing math; persistent point-in-time episodes and corrections; responsive bilingual UI; actual producer-to-consumer integration; historical/forward evaluation of incremental value; production-path proof. A plan, design, green unit suite or PR is not the complete parent outcome.

## 2. Placement: one credit engine, several consumers

The primary experience lives on `bonds.html` under Corporate credit / Credit & issuer, immediately reachable from Macro's existing Bonds route. Add a compact dislocation summary to Macro's existing context projection and a link into the issuer inspector. Do not add a competing global navigation family.

- CCW owns cash-bond calculations, credit observations, derived issuer/basket comparisons and their histories.
- Rates & Inflation Command owns Treasury curves, rates, real yields and rate momentum. Consume, do not recompute a rival rate state.
- Capital Structure Intelligence owns filings, instrument/guarantor/covenant evidence, cash funding and financing schedules. The existing `capital_structure.state.v2`, `funding_schedule.v2`, document-term and event families are upstream contracts; source existence is not proof of complete current issuer debt.
- Risk Radar consumes qualified contextual summaries. New CDI fields start with rank/size/gate/escalate all false. Existing Tier-B terminology does not override CDI's stricter ceiling. No probability or existing risk-score change in the first deployment.
- Terminal/Company Dossier receives attributed issuer-level facts and deep links, not a second calculation implementation.
- Existing case/save/alert, evidence, Data OS and evaluation owners retain their functions. Resolve their exact APIs before persistence/activation; no separate generic memory, notification, identity, authorization or workflow plane.

Paper: file `01M2WGNCX9475G79JRKJTCM08P`, Bonds page `p-1H-0`, R30 Credit & Issuer artboard `63YS-1`. Reuse route 03 and I05 Financing/I07 CDS, scenario, replay and saved-case patterns. Add focused CDI specimens without rewriting unrelated Bonds, Forex or Transmission work.

## 3. Verified starting point and risks

Implemented CCW source includes five SSGA holdings collectors, `engine/corp_credit.py` pricing and aggregate series, `engine/credit_momentum.py`, FINRA aggregate breadth/sentiment, Bonds projection and tests. It lacks a verified continuous single-name CDS feed and accepted issuer-level predictive dislocation model.

The original S1 report found broad HY velocity usually confirmed stress already underway: 84.9% of flagged observations followed negative trailing-21-session SPX performance; the modern-era result was weak and the episode null borderline. Preserve that result; do not relabel a confirmation signal as early warning.

The existing latest per-bond panel is a snapshot, while issuer_daily retains historical aggregates. First implementation must not invent historical bond observations. Fund-held par is not outstanding issuer debt. Existing registry mappings are economic-parent/name mappings, not proof of the legal CDS reference entity or guarantor.

A bounded native-source inspection found a September 8, 2026 latest CCW panel with 10,305 rows, and some values in its `isin` field were nine-character CUSIPs. This is an observed local binding, not a statement about every production replica. Currentness and identifier type must be checked rather than inferred from a column name. The source must be able to say stale or incomplete.

PR #9589 corrects misleading maturity coverage, earliest-row selection and unconditional zero-maturity copy. Preserve that carrier; do not duplicate its changes. Its unrelated research-factory CI failure is a release dependency, not a reason to stop independent CDI implementation.

## 4. User journeys and UI states

J1: Macro -> Bonds -> issuer list -> one borrower -> actual tracked bonds -> price/spread and equity comparison -> explain competing mechanisms.
J2: Theme basket -> contribution/dispersion -> weakest issuer -> maturity/financing inspector -> counterparty connections with documented amounts.
J3: Credit/equity disagreement -> freeze dated case -> watch confirmation/invalidation -> revisit evidence -> replay outcome without hindsight.
J4: Select a bond -> legal terms and quote provenance -> curve benchmark -> clean/dirty, YTM/YTW/OAS distinction -> CDS basis only if compatible.
J5: Stale/missing feed -> visible date/coverage -> retained historical view -> no false current verdict, no fabricated zero.

First view: one answer line; as-of and coverage; issuer filter; compact issuer rows; credit change, equity change, data quality and next inspection. Expanded row shows bond tranches and source limitations. Numerical labels specify bp versus percentage points and price return versus total return. No implied default/stock-downside percentage from CDS arithmetic.

Required states: fresh eligible, partial coverage, no eligible peers, no equity, no CDS, stale, insufficient history, unresolved legal identity, unsupported option terms, duplicate/conflicting observations, corrected evidence, data rights pending, request failed. Empty is not calm. No label promises recovery or imminent default.

Light treatment: existing white/cool research surfaces, hairlines, strong typography. Dark treatment: existing graphite material depth, restrained semantic highlights and readable muted text. Inter and current tokens; no new global palette. Desktop 1440, tablet 768, mobile 390. English/Chinese parity; widening means deterioration in both languages, while price-direction conventions remain separate. Keyboard, focus restoration, reduced motion, screen-reader table labels and mobile tap targets are acceptance criteria.

## 5. Data contracts and clocks

Every observation retains instrument/provider identity, source locator/digest, observation date/time, publication and first-system-availability where actually observed, correction/version, currency, quote side, valuation convention and source rights. Unknown availability remains unknown. File modification time is not fabricated publication time. A first current capture cannot certify earlier historical knowability.

Issuer: canonical legal entity when available, economic parent separately, CIK/LEI, ticker/share class mapping, guarantors with scoped obligations, source and valid interval.
Bond: native identifier plus type, issuer/obligor, seniority, security, currency, coupon schedule, day count, maturity, calls/puts/conversion/reset terms, outstanding principal, source terms and eligibility. Validate CUSIP/ISIN format and checksums; never interpret a nine-character CUSIP as a twelve-character ISIN.
CDS: reference entity, currency, seniority, restructuring clause, effective/maturity date, tenor, coupon/upfront/par-spread convention, side, contributor/transaction status, observed/reported/corrected timestamps. Missing fields fail compatibility; transaction prints are not a synthetic daily mid.
Equity: identifier/share class, currency, close convention, split/dividend adjustment, source generation and availability. Raw close yields a price return, never silently a total return. Exclude unqualified corporate-action discontinuities.
Coverage: separate fund-held principal, total issue outstanding and consolidated liabilities. Record source cadence, expected delay, observed history, instrument and issuer counts, missing families, and rights status.

Persistent data stays in existing `data/corp_bonds` producer families. CDI may add a versioned derived projection (`credit_dislocation.json`) and extend existing CCW series/forward-evaluation records, not a second independent raw-data authority. Immutable source generations and case/evaluation records use their existing owners. Publication writes must be atomic and consumers reject malformed/stale generations.

## 6. Source strategy and acquisition gates

1. Reuse SSGA daily fund holdings and current CCW price-convention validation. Evaluated fund prices are not executable trades. Fixed-income sample coverage does not include every issuer liability.
2. Reuse Treasury/FRED/ALFRED and current rate owner; align dates and convention. A par CMT curve is not a zero curve and cannot directly serve as a discount-factor curve without a justified transformation.
3. Reuse Capital Structure SEC source intake and document terms for instrument identity, principal, covenants, cash and facilities. Add domain extraction tests, not a competing generic SEC collector.
4. FINRA aggregate API and licensed TRACE are different products. Public credential availability proves neither instrument-level tape access nor commercial redistribution rights.
5. DTCC public activity is not a quoted CDS series. A separate permitted SDR pilot must establish exact contract normalization, duplicates/corrections, sparsity, clock and usage rights before any adapter can supply CDS observations.
6. Licensed CDS/TRACE is an optional acquisition decision; no purchases or account/security changes are authorized by this plan. Bond-only analysis stays useful without it.

Maintain rights decisions in the existing source inventory. Until rights are resolved, retain internal diagnostics or source links; do not expose restricted raw/resultant data to paying subscribers. This gate applies to the affected data/product, not all independent code and synthetic tests.

Primary anchors, checked during this commission: FINRA TRACE data and Developer terms; DTCC market activity; SEC developer resources; Federal Reserve GZ/EBP methodology. This plan's models are proposals, not claims that those providers endorse the engine.

- https://www.finra.org/filing-reporting/trace/data
- https://developer.finra.org/specific-terms-fixed-income-data
- https://www.dtcc.com/market-index-data
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.federalreserve.gov/econresdata/notes/feds-notes/2016/recession-risk-and-the-excess-bond-premium-20160408.html
- https://pubs.aeaweb.org/doi/10.1257/aer.102.4.1692

## 7. Calculation modules

### 7.1 Cash bonds: reuse and improve, not rewrite blindly

Reuse CCW's clean/dirty price and accrued-interest validation, cash flows/YTM and matched Treasury G-spread. G-spread is not OAS or CDS. Add independent fixtures for coupon/ex-coupon dates, leap dates, stub periods, day count, negative rates and solver convergence. Later compute zero-curve Z-spread and OAS only for supported schedules/options with qualified model inputs. Distressed instruments use recovery scenarios; YTM is not expected realized return.

Duration decomposition: approximate price change = -modified_duration * (risk_free_yield_change + spread_change), plus convexity, carry and other terms. Separate rates, credit and liquidity, including Treasury rally plus worsening borrower funding.

### 7.2 Comparable credit changes and first wave

First wave uses the existing issuer-level **matched-panel daily changes**, not naive differences of a changing fund-weighted average. Require all expected trading sessions inside the declared window; five observations separated by weeks are not five sessions. Preserve provider-date calendar limitations explicitly. Each 5/21-session change is a sum of eligible daily matched changes with coverage and matched counts.

The initial comparator is a transparent segment/maturity-cohort median of distinct other issuers. Without exact rating, seniority, currency and liquidity matches, label it a **coarse peer comparison**, not a residual fair-value model. A minimum of three eligible other issuers is a display-quality requirement, not statistical significance. No percentile from a three-month series masquerades as a long-run extreme.

W_i,h = issuer matched spread change - peer median change, in bp.
V_h = matched spread change / h, in bp per session.
Acceleration compares nonoverlapping h-session velocities, retaining missingness and session alignment. Use absolute bp moves as primary; percentage ROC near zero can exaggerate high-grade stress.

Later tranche-level same-instrument residuals control duration, curve, rating, liquidity, new-issue concession and bond features. Robust peer fits train only on earlier data. Cross-tranche agreement does not count the same bond in five ETFs as five observations.

### 7.3 Equity disagreement, not a universal stock target

Align issuer credit and equity windows at a common source-eligible cutoff. Label raw equity price returns explicitly until adjusted total-return data is proven. First stage: credit widening with steadier equities, joint deterioration, credit improving with equity weakness, joint improvement, or insufficient evidence. Thresholds are configurable descriptive candidates and never calibrated risk classes.

A later model compares sector/beta/earnings-adjusted equity returns and credit residuals. Distinguish already-damaged stocks from warnings before damage. Do not invert an unstable credit/equity regression into a point stock target. Structural Merton/KMV and reduced-form candidates compete against simple baselines; neither automatically wins.

### 7.4 Financing and severity

Obligations due/reset, unrestricted cash, actual committed/available facilities, FCF, interest/fixed charges, covenant headroom, collateral and concentration determine the transmission mechanism. New interest expense applies only to debt actually refinanced/reset/issued, not all existing fixed coupons. Avoid double counting facilities, restricted cash, leases and parent guarantees.

Quantify scenario interest = principal repricing * change in all-in rate; show scenario rather than forecast. For debt maturity ladders require principal/terms coverage and reconcile issuer roll-forwards. Accounting snapshots are not complete contractual schedules.

### 7.5 CDS and hybrid debt

A real CDS-cash basis requires matched reference entity, seniority, currency, tenor, deliverability, recovery and conventions. Normalize upfront and fixed coupon via a qualified pricing model. Lambda ~= spread/(1-recovery) is a simplified risk-neutral hazard, not physical default probability or stock downside.

Convertibles and equity-linked notes require straight-debt and embedded-option decomposition, conversion/call/put/reset/anti-dilution terms, volatility/borrow and coverage. Do not place them in straight-bond peer fits. Unsupported instruments are visible but explicitly excluded, not silently discarded.

### 7.6 Original baskets and contagion

Version issuer membership as-of: hyperscalers, leveraged compute/neoclouds, power, datacenter REITs, memory/hardware, telecom controls and matched non-AI comparators. Preserve all original issuers, including defaults/delistings, and distinguish historical membership from today's list.

Compute equal-issuer, capped-issuer and amount-outstanding alternatives only where their denominators are observed. ETF-held par weighting is explicitly a fund-sample lens. Publish contributions, breadth, dispersion and concentration; no claim to recreate an undisclosed Goldman index.

Contagion edges must name lender/guarantor/customer/supplier/lessor/project-SPV relationship, amount and date when disclosed. Shared AI membership is not financial exposure; supplier revenue loss is not creditor principal loss. Initial graph is explanatory; stress propagation needs separately validated elasticities and no automatic trade authority.

## 8. Persistent episode memory and research synthesis

Each case keeps initial cutoff and data/model/basket versions, observed evidence, rival mechanisms, confirmation/invalidator, horizon, prior states and material updates. Source corrections append lineage and do not rewrite what was known. Repeated identical observations do not create repeated cases or notifications.

Use existing CCW forward/evaluation infrastructure for deterministic outcomes and existing saved-case/notification owners for user effects. Inspect compatibility before extending schemas. A case save, monitor activation, evaluation and notification delivery are distinct operations. No browser-local fake save or scheduled worker is presented as canonical persistence.

Outcome classes after qualified observation: equity catch-down, credit normalization, both adjust, neither resolves, missing/censored. No 'fear unfounded' label just because a stock did not fall; inspect actual financing/credit normalization and horizon. Retain false alarms, missed events, negative controls and model abstentions.

Grounded AI synthesis consumes the numeric record, filings and source lineage. It proposes explanations/counterevidence and what would change the conclusion. It cannot originate prices, debt facts, probabilities, ranks or order sizes. Duplicate source lineage contributes no extra independent vote.

## 9. Research protocol and promotion

Freeze eligibility, thresholds, peer method and outcomes before evaluation. Existing S1 evidence is retained and not retuned away. Current October 2026 examples are ongoing cases, not mature success labels.

R1 data feasibility: coverage, exact identifiers, actual update cadence, price conventions, rights, historical availability and reproducibility. A public spreadsheet today does not certify a historical first-publication timestamp.
R2 early warning: first alert while stock remains within 5% of trailing-21-session high; primary descriptive loss target 10% below alert close within next 63 eligible sessions. Separate the already-declining population. This is a proposed evaluation target, not an asserted optimal strategy.
R3 convergence: credit normalization versus equity catch-down, 21/63/126-session horizons, including neither and censored cases. Freeze normalization/tie rules and baseline before outcomes.
R4 mechanism: matched financing changes and liquidity/supply countercases; credit price is not direct proof of solvency or causation.
R5 incremental CDS: compare the same model/sample with and without genuine eligible CDS; sparse history is insufficient evidence, not a failed model.
R6 regime transfer: chronological walk-forward, modern holdout, delisted/defaulted names, financial versus non-financial cohorts, clustered episodes, overlap purging/embargo, transaction and information availability, correction/revision sensitivity.

Metrics: independent episodes, issuer-years covered, false warnings per issuer-year, precision/recall with denominator, pre-event lead time, economic severity, missed events, abstention and coverage. For qualified probabilities add calibration/Brier/log score and uncertainty, never classifier confidence relabeled as event probability. Trading costs and execution are a separate policy study.

Promotion requires incremental value beyond broad HY velocity, equity momentum, sector/beta/volatility and relevant earnings information, plus prospective performance. The build and descriptive use do not wait for promotion; Risk Radar authority does.

## 10. Ordered delivery waves

| Wave | Deliverable | Consumer unlocked | Acceptance |
| --- | --- | --- | --- |
| W0 | Published masterplan, bindings, source census | Recoverable engineering direction | Exact GitHub commit/readback and no owner collision |
| W1 | Pure CDI compiler, quality/identifier checks, source adapter, snapshot artifact and tests | Dated issuer/credit/equity comparison and actual coverage | Missing/stale/duplicate/future/session-gap tests; measured native data run |
| W2 | Paper CDI specimens and existing Bonds frontend binding | Filter issuers, inspect securities, understand countercase | Actual template rendering, keyboard/mobile/EN-ZH/light-dark visual evidence |
| W3 | Canonical CCW producer and Macro/Radar context integration | Daily update without manual rebuild | DAG/synapse/workflow, bounded timing, atomic publication, exact-head CI; authority unchanged |
| W4 | Per-bond historical series and term-aware comparables | First-tranche widening, curves and dispersion | Price/identity/option/currency fixtures; independent reference validation |
| W5 | Capital Structure financing schedule and scenarios | Distinguish price fear from funding cliff | Legal entity/guarantee reconciliation, loan/private/lease gaps and dollar-denominator tests |
| W6 | Existing case/evaluation memory and grounded explanations | Save, revisit, compare evidence and outcomes | Idempotence/correction/censoring/supersession and real save-readback path |
| W7 | Genuine CDS pilot and optional licensed adapter | Term-structure/basis/price-discovery evidence | Contract normalization, sparse-trade/revision and entitlement proof |
| W8 | Historical/forward model race and contagion research | Calibrated incremental risk only where supported | Preregistered holdout, independent review, prospective limits |
| W9 | Dossier/Terminal and production qualification | Complete cross-asset investor workflow | Deployed user journey, observed data clocks, rollback and negative-path proof |

W1-W3 are useful without CDS purchases. W4-W6 can continue while rights/history questions are resolved. W7 may remain legitimately source-blocked without falsely blocking cash-credit progress. Terminal changes get their own source-custody and actual integration checks; this plan is not authority to modify unrelated billing/auth systems.

## 11. Test and operational contract

Unit: identifier checksums, duplicate conflicts, NaN/infinity, negative quantities, stale/future observations, missing sessions, date alignment, peer exclusion, insufficient peers, composition change, zero denominators, no total-return mislabel, unsupported callable/convertible pricing.
Property: input row order cannot change output; extending the dataset beyond a frozen cutoff cannot change historical output; adding more ETF occurrences of the same bond cannot increase independent count; adding future revisions cannot alter earlier knowledge; output is JSON-safe without NaN.
Integration: actual CCW files and registry, equity adapter clocks, no network on render, atomic derived snapshot, no stale source re-dating, no read-only mode source mutation, output authority all false, failed lanes visibly unavailable.
UI: actual template plus component tests, search/filter, expansion/focus, empty/error/stale states, no misleading zero-maturity or current-credit reassurance, both languages and both art directions at desktop/mobile.
Performance: record real wall time/input size on representative dataset; bounded startup JSON and detail loading; no giant per-bond JSON in `macro.html`; do not add an unconditional heavy mobile fetch.
Delivery: focused local tests, scoped source review, exact candidate CI and normal protected merge/release. No admin bypass. Data/licensing and predictive validation remain independent of CI success.

## 12. Working boundary and continuation

This session owns the new isolated CDI source branch and only explicitly addressed Paper nodes. #9589 remains a separate original correction carrier. Other R30/Forex/Capital Structure source owners and active writers are preserved. There is no dispatched external worker, no activated monitor, and no unresolved modifying effect at this plan's initial publication.

Principal retention rationale for W0/W1: PRINCIPAL_JUDGMENT while input/identity/quality semantics are being resolved; bounded adapter/test labor can move to an admitted paid Fabric worker only through an actually available authorized route. The current Workbench API exposes fixed-file canaries, not a general Fabric submit. This is an action-specific limitation, not a fabric-wide outage or permission to create native labor workers.

The next material action after plan publication is the pure W1 compiler and actual-input quality report, then Paper and the existing Bonds consumer. Save accepted results, source hashes, test receipts, remaining gates and the next action in this directory and the existing Agent OS home. Continue safe work across wave boundaries; never call the parent complete at plan publication.
