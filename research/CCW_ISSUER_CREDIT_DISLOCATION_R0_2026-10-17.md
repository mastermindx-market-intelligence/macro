# Corporate Credit Watch — Issuer Dislocation & Early-Warning R0
**Date:** 2026-10-17 (America/Vancouver)  
**Status:** research architecture / no new live model, CDS feed, trade signal, backtest, runtime monitor, or production deployment  
**Commission:** assess the issuer-level credit, CDS, equity and bond dislocation opportunity prompted by the 17 October ZeroHedge/Goldman AI-credit article.  
**Source pin:** Macro main `4cfcec9b6d1ac92c0f36f849edb64c952839ee96`; protected Mastermind Skillpack `ef4be2f5c9b0b82fc11be83f03cf7bcdb8cea6f2` (1.0.1, bootstrap 1).

## 1. Decision and no-duplicate boundary

Extend **existing Corporate Credit Watch (CCW)** as the canonical credit-data/calculation owner. Do not create a rival bond engine, credit event store, alert lifecycle, memory plane, risk authority or duplicate Paper design. The existing owners remain:
- **CCW/Bonds:** `collectors/corp_bond_holdings.py`, `engine/corp_credit.py`, `engine/credit_momentum.py`, `engine/bonds.py`, `scripts/build_bonds.py`, bonds.html; issuer/theme/market credit and PIT holding panels.
- **RIC/Transmission:** discount-rate, sovereign curve, term-premium, yield momentum and real-rate shocks; consumed read-only by the credit models.
- **Risk Radar:** graduated Tier-B context/accrual for new issuer stress; promotion under its existing preregistered out-of-sample gauntlet. No direct state origination, position sizing or trade ranking.
- **Capital Structure / company dossiers:** filing-derived legal issuer/obligor, debt/guarantees, covenant facts, committed lines, secured debt and verified liability schedules; consume its existing canonical evidence/events rather than creating another parser/lifecycle.
- **Bonds × Transmission R30 design:** PR #9578 `0ff079356ec41d8a64307885bcb771a441297ceb` already specifies Credit/Issuer route 03, I05 financing schedule, I07 CDS quote conventions, I04 monitor and saved cases/replay. Wire actual producer only after acceptance; don't duplicate UI or claim R30 runtime exists.
- **Terminal/stock dossier:** future read-only borrower/entity exposure and bond-credit chip; no direct trade ticket.

Prior governing documents: `research/CORPORATE_CREDIT_WATCH_MASTERPLAN_BY_FABLE.md` (CCW-R1..16), `research/CCW_CREDIT_FIELD_GUIDE.md`, `research/CCW_STUDY_S1_PREREG.md`, `research/CCW_STUDY_S1_RESULTS.md`.

## 2. Investor-facing source findings (bounded correction on this branch)

The existing `engine/corp_credit.py::canonicalize_bonds` creates `par` by **summing face value held in the five tracked bond funds**. `_build_maturity_wall` aggregates those fund-held positions, not every issuer's total debt outstanding; a company's revolving credit facilities, loans, private placements and non-index bonds are missing. The old bonds.html heading, "When the debt comes due", and an unconditional "All themes had zero bonds maturing within 1 year" falsely elevate limited fund coverage to a general liability conclusion. Additionally `scripts/build_bonds.py::_build_maturity_wall` historically took `par_total.iloc[0]` without pinning `as_of`, so an old holdings bucket could be displayed with a newer date. This PR's reversible code slice restricts all themes to one latest observed snapshot, prints the holdings date, labels coverage, and removes the unsupported zero-maturity sentence. It **does not** create a true issuer maturity wall. That requires source-backed debt contracts.

Another gap: `scripts/build_bonds.py::build_corp_credit_vm` explicitly hardcodes `divergence_ready=False` with the comment "No scored divergence read ships in this packet (engine-lane)". The credit-vs-stock UI is intentionally in a provisional/unbuilt state. Do not bypass this to imply qualification.

## 3. Credit-leading-equity scientific claim: conflicting evidence

Research requires competing hypotheses. Blanco/Brennan/Marsh (2005, Journal of Finance / Bank of England) found CDS typically led **cash bonds** in their IG sample, a different claim from CDS leading common equities. Gilchrist/Zakrajsek (2012, AER) isolated an excess bond premium correlated with financial intermediary risk-bearing capacity and future economic weakness. Conversely, a 2017 multi-region study found equities often led CDS; a 2023 study found the relationship bidirectional with equity still exerting greater influence; Zhou et al. (first published 2025; Accounting & Finance 2026) find CDS leadership strongest for lower-credit-quality/smaller firms, depending on microstructure and information arrival. Never assert universal credit-first timing.

Mastermind CCW S1 (15 July 2026) returned HY OAS 21-day velocity top 15% followed by mean 63-day SPX worst drawdown -7.6% vs -5.2% unconditional, but 84.9% of flags occurred **after** SPX had already fallen in the prior 21 days, modern-era difference ~-0.9 percentage points inconclusive, episode-level permutation p=0.0505. The first new study must distinguish actual pre-drawdown alerts from mere confirmation.

ZeroHedge's 17 October 2026 headline reports a Goldman basket "pricing a 15% drop" in hyperscaler stocks. The underlying Goldman chart, constituent membership, normalization, model and time horizon were not independently accessible; preserve as an unverified scenario. Do not translate any CDS default-risk number directly into an equity-price target.

Sources:
- https://www.zerohedge.com/markets/trick-or-treat-goldmans-spooky-chart-pack-shows-ai-credit-pricing-15-drop-hyperscalers
- https://www.bankofengland.co.uk/working-paper/2004/an-empirical-analysis-of-the-dynamic-relationship
- https://pubs.aeaweb.org/doi/10.1257/aer.102.4.1692
- https://www.sciencedirect.com/science/article/pii/S1042443117304560
- https://www.sciencedirect.com/science/article/pii/S1044028323000443
- https://onlinelibrary.wiley.com/doi/10.1111/acfi.70116

## 4. Product topology and staged feeds

**Free/readily accessible baseline**: reuse daily SSGA fund-held ISIN/CUSIP-level snapshots (SPSB/SPIB/SPLB/JNK/SPHY), existing credit G-spread and composition guards, Treasury FRED/ALFRED, funding/MOVE/EBP and index spread context; SEC EDGAR companyfacts/submissions/10-K/10-Q/8-K/424B filings for date-stamped debt/FCF/terms; public issuer IR maturity/liquidity disclosures. For each source retain rights, UTC observation/release/availability, coverage gaps and source vintage.

**FINRA**: the public fixedIncomeMarket Query API provides breadth/sentiment/capped volume, not a generally free institutional issuer-by-issuer TRACE transaction tape. Existing `collectors/finra_corp_bonds.py` requires FINRA OAuth credentials and is a different dataset from individually licensed TRACE. FINRA's published Fixed Income Data terms explicitly limit developer use to noncommercial personal/professional purposes and condition redistribution, including derived/resultant data. Commercial Mastermind deployment needs entitlement/legal review; do not equate public credentials with unrestricted resale permission.
- https://developer.finra.org/node/1171
- https://developer.finra.org/specific-terms-fixed-income-data
- https://www.finra.org/filing-reporting/trace/data

**CDS**: DTCC free Top 1000 single-name data are **quarterly activity**, not five-year quoted spreads. DTCC/CME swap-data public dissemination can expose transactions and contract metadata; feasibility pilot must verify reference entity, seniority, restructuring, scheduled term, currency, coupon/upfront, execution, reporting lag, corrections and ability to reconstruct standardized par spreads. Sparse prints are not continuous mid quotes. DTCC/CDS Kinetics or other licensed vendor marks are a separate entitlement lane; implement input adapter contracts but do not invent observations.
- https://www.dtcc.com/market-index-data
- https://www.cmegroup.com/market-data/repository/data.html
- https://www.isda.org/traditional-protocol/big-bang-protocol/

**Coverage gap**: holdings data exclude many non-index 144A/Reg S, private credit facilities, revolvers, project-finance SPVs, converts/equity-linked debt and some collateralized borrowing. Display a per-issuer coverage matrix; absence from ETF sample is not absence of issuer debt. Fund par is not total issue outstanding. Obtain authoritative outstanding principal and maturity schedule from filed terms, not market fund positions.

## 5. Risk model — separable, interpretable organs

An instrument must link legal obligor, issuer, guarantor, parent, reference entity, CUSIP/ISIN and equity ticker without flattening distinct claims. Maintain seniority, security, currency, coupon, maturity, callable terms, conversion provisions, accrual, duration, tenor and rating as-of. In the first wave prefer senior noncallable USD bullet bonds; quarantine problematic callable HY, converts, subordinated/private facilities until term-aware valuation exists.

Let `s_b(t)` be an eligible cash spread using a consistent risk-free curve and verified price convention. The existing CCW estimated `G-spread = bond YTM - tenor-matched Treasury` is **not** an option-adjusted spread nor a CDS quote.

- **Relative widening**: `W_i,h(t) = delta_h(s_i) - weighted_median_matching_peers(delta_h(s_peer))` for h=1,5,21 trading observations, with legal-term/duration, rating, seniority, currency, subsector and liquidity comparability disclosed. Do not mix cash spread level, Treasury yield and CDS without matched definitions.
- **Velocity and acceleration**: `V5=(s_t-s_(t-5))/5` in bp per observed eligible trading session; `A5=V5(t)-V5(t-5)`, oriented widening = increasing risk. Use causal historical percentile/median absolute deviation only with a sufficiently long observed history. CCW theme accrual starts July 2026; do not produce falsely precise percentile thresholds from a few dozen dates.
- **Cross-tranche confirmation**: same legal borrower stress observed in two independent senior bullet maturities after removing a common Treasury and liquidity shock; don't count several ETF shares of the same ISIN as independent observations.
- **Bond-CDS basis when real CDS available**: consistent-sign `basis=normalized CDS spread - matched cash-bond credit spread`, with tenor, deliverability/cheapest-to-deliver, coupon/upfront conversion, funding and market liquidity; wide basis is an explanation question, not automatic default signal.
- **Equity residual**: equity total return net of causally estimated sector/size/beta effects and applicable earnings/capex news; distinguish debt warning before a stock move from both markets already selling off. Avoid doubled sector/index exposure in residual regressions.
- **Credit-to-equity dislocation**: a *joint observation* of abnormal credit deterioration, noncorroborating residual equity strength, issuer financial vulnerability, and independent cross-market evidence; output a vector of observed facts/falsifiers/coverage, not a single invented probability. First stage descriptive quadrants. After successful preregistered evaluation, a competing-risk classifier may distinguish (a) equity catch-up, (b) credit normalization, (c) joint repricing, (d) unresolved — calibrated and allowed to abstain.
- **Default interpretation**: the flat-hazard approximation `lambda≈CDS_spread/(1-recovery)` yields a risk-neutral, recovery-dependent hazard; it is not a physical default probability or expected stock decline. Merton/KMV structural asset-value models are separately estimated and especially weak for high-grade distant defaults.
- **Cash-flow/financing**: audited issuer-level CFO, capex, unencumbered cash, FCF, interest/fixed-charge coverage, debt/EBITDA, contractual interest resetting, term-loan facilities, covenants, debt due in 0-1/1-3/3-5/5+ years, liquidity sources/uses, restricted collateral, projected refinancing at alternative spreads. Separate reported facts, inferred calculations, projections and illustrative shocks.
- **Hybrid/equity-linked bonds**: value straight-debt floor plus equity-conversion option and actual contract triggers, anti-dilution, call/put clauses, resets and counterparty hedging; **do not** treat the convertible's yield as default compensation. Quarantine until metadata is complete.
- **Contagion**: direct financing/guarantee/loan/customer/supplier/landlord relationships on an evidence graph; exposure weights based on disclosed economic amounts and guarantees, not shared buzzwords or ETF membership. Preserve customer concentration and SPV isolation. Example AI financing clusters are *hypotheses* unless actual financing is verified.
- **Liquidity alternate**: identify stale matrix prices, sparse transactions, new-issue supply concessions, quarter-end dealer constraints, duration moves, temporary basis dislocations and recoveries. The null scenario (credit absorbs the fear) gets a first-class explanation, not a dismissive disclaimer.

All proposed outputs are `DISPLAY_ONLY` with exact `authority: {rank:false,size:false,gate:false,escalate:false}`; missing/stale quotes print absent, never zero or synthetic "observed".

## 6. Do not build Goldman's baskets; construct original, documented cohorts

Define issuer cohorts independently: (1) AI hyperscalers, (2) neocloud/AI compute renters, (3) power/utilities, (4) datacenter REIT, (5) memory hardware, (6) upstream AI hardware, (7) telecom capex historical controls, plus IG BBB/BB/B/CCC matched-control ladders. Freeze issuer and bond inclusion **as-of**, each legal obligor and eligible seniority, and compare value-/equal-/issuer-weighted sensitivity separately. Mark bonds missing from the tracked source and avoid survivorship bias. A Goldman basket label/chart is neither a source license nor permission to claim replication or use unknown constituents.

Version weights and timestamp, and calculate index contributions with actual matched bond dispersion, duration, exposure and liquidity. Issuers with multiple bonds cannot silently dominate equal-name baskets. No dollar-size outstanding series may be inferred from ETF shares owned. Compare AI-minus-matched-non-AI spread change, spreads conditional on debt structure, credit-carry duration vs rate shocks, and matched bond-equity residuals; establish an explicit base/neutral case.

## 7. Point-in-time longitudinal memory and alerts

Extend existing `data/corp_bonds` time-series and canonical company/incident/alert consumers, not a second memory or task plane. Each record: `legal_entity_id, instrument_id, share_class, parent_guarantor, source_uri, provider, content_digest, observed_at, released_at, available_at, revision_id, effective_date, maturity_date, calendar, currency, settlement, accrued_price_convention, as_of, model_version, data_license, coverage_reason`. Corrections append provenance and supersession rather than rewrite historical knowledge.

Store a **hypothesis episode** tied to the existing evidence/alert ledger with trigger timestamp, exact observations (before equity moved or after), confirming and invalidating facts, prior state, peer basket version, model version, data staleness and outcome maturity. Preserve the snapshot originally observable at alert time. A change detector must not re-arm on identical evidence or use later restatements in earlier simulations.

Cadence: daily holdings; SEC on filings; FRED by publication; market/CDS only at observed licensed feed cadence; quarterly DTCC activity as participation context. "Live" cannot be claimed for a T+1 fund value or quarterly aggregate. LLMs can generate cited countercases from permitted evidence but never originate/synthesize an observed price, state, probability or trade action.

## 8. Frozen R0 research program and empirical gates

**R0-0 source/rights audit:** inventory actual latest holdings/PIT rows, independent bond price sample, instrument identity quality and missing disclosures, FINRA access/redistribution restrictions, CFTC/DTCC transaction sparsity and normalized CDS feasibility. Render coverage and worst-available delay. No "CDS built" until independent price reconciliation and commercial entitlement.

**R0-1 cash-bond first-event study:** pre-register issuer cohort, comparable control selection, eligibility, financial health label and cutoff. Primary outcome: issuer-specific total-return drawdown **at least 10% from alert close within 63 business sessions**, conditioned on being within 5% of own trailing 21-session high at alert onset (explicit price-not-yet-damaged cohort). Compare price-to-earnings/growth/sector risks as covariates. Distinguish alert *before onset* from subsequent negative continuation, and separately report outcomes for already-damaged stocks. Use an eligible historical dataset with independently verified **first-publication timestamp**; if issuer spread history is only July 2026 onward, report forward accrual with **NO RETROSPECTIVE CLAIM**. Avoid treating repeated daily flags of one crisis as independent events.

**R0-2 convergence and countercases:** primary descriptive endpoint 21/63/126 eligible sessions: did matched credit return toward peer levels, did equity residual underperform, or did both move? Declare neutral/censored/missing outcomes. Include equity-only, credit-only and simple spread-level baselines; separable proxies for rate/liquidity/new-issue supply. Preregister tie/treatment definitions before outcomes. Use issuer/time clustered uncertainty, embargo and purging for overlapping labels, blocked/episode-level permutation and chronological walk-forward.

**R0-3 stress mechanics:** verify each candidate warning against actual issuer financing deterioration: interest reset/rollover, new-issue concessions, audited leverage/FCF, covenant/rating/news publication, funding access. Keep causality/mechanism evidence separate from a stock drawdown outcome.

**R0-4 CDS incremental value (conditional on data):** compare issuer credit models with and without genuine as-of CDS observations; enforce matched contract quote quality, no interpolation through missing quotes, correct upfront-to-par conversions and feed entitlement. If available history insufficient, mark untestable, not null.

**R0-5 out-of-regime replay and future ledger:** negative controls 2020 liquidity shock, macro/rate-only 2022, tech growth/credit 2000-02, energy 2014-16, distress 2008 and 2023 bank funding, with historical sample rights and actual instrument presence; 2026 AI episode is ongoing and cannot serve as a mature outcome. Report false alarms per issuer-year, unique episodes, real pre-event lead days, median forward drawdown and uncertainty, modern-era survival, calibration, Brier score (only for qualified probabilities), abstention and rejected/null indicators.

Fail/promotion gates: no historical / commercial feed => accrue observations only; incomplete instrument/corporate identity => no scored credit-equity dislocation; no modern holdout or dependent-episode inference => context only; no genuinely independent CDS => bond-only explanation; no causal/vintage eligibility => historical analogy only; no subscriber redistribution entitlement => internal research only; no production/browser receipt => `BUILT_NOT_PROVEN`. Promote to Risk Radar through its existing owner and accepted gauntlet, not via passing repository tests.

## 9. Implementation sequence / DONE_WHEN

1. **Source truth repair** (on this draft branch): guard newest PIT maturity panel, relabel tracked ETF holdings, remove unconditional zero claim, test latest/nondate fixtures. No changes to actual company obligations, CDS, alerts or rankings.
2. **Source/coverage adapter**: audit actual issuer ISIN mapping, parent vs guarantor and filed debt maturity schedule; add documented company obligations via existing capital-structure pipeline without conflating ETF positions.
3. **Issuer spread shock**: additive CCW per-issuer relative-spread/dispersion artifacts with causal controls, nulls and timing/quality metadata. Keep display-only and CCW collect lane, no extra render computation.
4. **Genuine CDS interface**: separately add entitled vendor/CDS transaction input when contract normalization and rights are proven; otherwise output unavailable.
5. **Paired equity/divergence episode ledger**: freeze strict prereg and forward score vs equity returns, no unqualified 15% or PD% translations.
6. **Reuse R30 I05/I07/I04**: bind actual credit, issuer financing, contract inspector and saved-case/replay without new monitor/notification stores; verify dates/responsive behavior.
7. **Risk Radar Tier-B**: require value above the validated broad OAS leg and acceptance by existing model owner before changing authority. No override of previous null studies.

**DONE_WHEN for the full parent:** lawful data provenance and redistribution, accurate bond/issuer identity, complete well-labeled coverage, reproducible PIT histories, non-duplicative canonical storage and consumption, empirically tested alert-vs-countercase usefulness, usable R30 issuer workflow and real-path verified delivery. A research document, a draft PR, an illustrative number or passing unit tests alone does not complete this.

**Current continuation:** bounded draft fix must undergo focused unit/render tests, exact-head review and protected delivery. Independently, qualify genuine issuer outstanding-debt schedules and CDS public-SDR normalization/rights. The parent mission is incomplete; no worker, monitor, deployment, trade or live CDS feed was created here.
