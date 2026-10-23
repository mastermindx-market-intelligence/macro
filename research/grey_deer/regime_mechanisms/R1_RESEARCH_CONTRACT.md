# Regime-aware risk intelligence — R1 research contract

Operation: `risk-regime-mechanism-research-20260927-sol-001`. Chairman commission: September 27, 2026. Parent: `WS:GREY-DEER-RISK-INTELLIGENCE` / MAS-258. Cumulative delivery record: Macro #8128.

**R1 research/design only. MISSION_COMPLETE: false. No current-market diagnosis, newly validated forecast, policy, production model, release or deployment is claimed.**

This is the compact canonical research record. The fuller companion package contains `REGIME_RISK_RESEARCH_R1.md`, the 76-entry `INDICATOR_RESEARCH_MAP.md`/`indicator_registry.json`, `HISTORICAL_CASEBOOK.md`, `mechanisms_and_edges.json`, source register, next-study protocol and offline contract checks. Its material artifact hashes are preserved below. This record and the adjacent R2 protocol are sufficient to resume the next scientific phase without replaying the original conversation.

## 1. Outcome and research decisions

The system must explain the environment, vulnerability, initiating shock, amplification, recipients, containment and plausible next paths. A historical analogy must include differences and benign outcomes, not just a memorable crisis.

Keep seven concepts separate:

1. **Backdrop:** growth/inflation level, change and uncertain membership, using the existing source owner.
2. **Vulnerability:** refinancing, duration, runnable liabilities, FX mismatch, leverage, concentration and usable liquidity already present before the shock.
3. **Trigger:** a dated observed shock, distinct from the vulnerable state.
4. **Amplification:** margin, redemptions, funding pressure, credit restriction and dealer constraints.
5. **Propagation:** recipient deterioration through a supported channel, not merely correlated returns.
6. **Repair:** breadth, funding, credit-access and earnings recovery; a price rebound alone is insufficient.
7. **Authority:** what an individually qualified policy may do. Research context creates none.

Regime hypotheses are multi-label, not mutually exclusive. Classification confidence, observed damage and future loss probability are different outputs. Mixed/unknown states are valid. Uncertain attribution must not conceal independently qualified acute stress, and a confident story must not fabricate a stress observation.

**No universal nominal-yield cutoff is assumed.** Rates effects depend on surprise, real yields, term premium, speed, cash-flow duration, refinancing timing, earnings, hedging and funding. Similarly, oil and dollar rises are not permanently bearish votes. Conditional weighting must be earned by common-sample, out-of-sample-style diagnostic comparisons, not hand-set from a narrative.

The existing global source shown on eleven dashboards is one observation. Related measures of the same credit spread, dollar move or volatility shock must not become independent votes.

## 2. Existing source findings and ownership

Read-only evidence base: Macro `f607c857239a5336b1a2196e563b038f62178e67`. Records publication starts from fresh main `251d6eee37f5e2e71c81714b628efffa95489bf1`; no existing implementation file is modified.

- The Grey Deer freeze already separates measured state, transition hazard and capital policy. `engine/risk_envelope.py`, blob `3b0df2d426f50245142b943e38faf4996f96e995`, is a pure source-native composer, not a new score. Its v0 source ceilings intentionally prevent cohort weakness alone from claiming TRANSMITTING/BREAKDOWN. ARMED/TRIGGERING require separately promoted experts. Do not bypass those restrictions.
- `engine/regime_hmm.py`, blob `9d3f1d3a2a7453eb9d55494108908ff6faf16d2f`, explicitly uses a full-sample smoothed historical posterior for display. That history cannot be a real-time predictor.
- `engine/quad_vector.py`, blob `7b70f8ee6dd49e3efcb087cd7af02f3fb60da564`, publishes the existing causal `regime_one` posterior. Current membership differs from historical transition probability. A causal filter still needs input-release and parameter-fit-vintage qualification.
- Existing Contagion Sensing & Propagation work owns context/wiring and already distinguishes a descriptive spread clock from predictive hop order. Reuse its qualified evidence, not a duplicate plane.
- Chronicle remains the settled market-transition owner; Reflex Registry owns bounded policy firing; Evaluation OS/QLedger owns grading. Do not create a market episode ledger or repurpose the per-name Signal Episode Atlas.
- Terminal mirrors; Portfolio retains position/mandate/sizing authority. LLMs explain and challenge source-backed evidence, never originate numeric hazards, escalation, odds, sizing or orders.

Protected procedure: Mastermind `master@dcc4829a811d3f6e4fe8c16a103f813c3501f48e`, compatible Skillpack 1.0.1/bootstrap 1, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`; same-commit COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT read. Direct principal duty: PRINCIPAL_JUDGMENT. No worker, Executive job or watcher started.

## 3. Nine mechanism families

| ID | Mechanism | Critical distinction |
|---|---|---|
| M1 | Demand/earnings contraction | Falling yields can coexist with worsening cash flows. |
| M2 | Inflation/discount repricing | Surprise and receiving exposure, not a universal nominal yield. |
| M3 | Physical supply/energy squeeze | Supply, demand and inventory mechanisms cannot be identified from oil price alone. |
| M4 | Credit/refinancing stress | Financing access and debt service, not just one spread. |
| M5 | Bank balance-sheet/funding stress | Asset exposure interacting with runnable liabilities and usable liquidity. |
| M6 | Sovereign financing stress | Maturity, currency, funding and bank linkage; one weak auction is not insolvency. |
| M7 | External funding/carry reversal | FX mismatches, external obligations and leveraged unwind; broad positioning is an imperfect proxy. |
| M8 | Leveraged liquidation/dysfunction | Margin/redemption/funding feedback; volatility is not identical to dysfunction. |
| M9 | Concentration/leadership unwind | Crowding and earnings/valuation support; not every narrow rally collapses. |

Exogenous operational/health/weather/geopolitical events, policy response, data quality and repair are overlays. They do not become extra votes in a risk total. These mechanisms are hypotheses pending operational definition and empirical qualification, not adopted runtime categories or causal findings.

## 4. Candidate measurement map — 76, not 76 independent signals

The full companion registry supplies a measurement definition, horizon, conditional hypothesis, strongest failure/counterexample, source requirements and candidate existing owner for each. All have `UNPROMOTED_RESEARCH_CANDIDATE`, unqualified dataset status and no capital authority. Source references support the economic mechanisms, not exact predictive cutoffs.

**Rates and discounting (8):** R01 real-yield shock; R02 policy-path repricing; R03 term-premium repricing; R04 curve shape and route; R05 MOVE level/acceleration; R06 joint equity-bond losses; R07 cash-flow discount sensitivity; R08 refinancing pass-through.

**Energy and supply (7):** O01 local-currency oil shock; O02 physical production disruption; O03 inventory/storage tightness; O04 energy-curve tightness; O05 net energy import burden; O06 margin squeeze/pass-through; O07 supply/demand oil attribution.

**Credit/debt service (8):** C01 HY spread level; C02 spread acceleration; C03 excess bond premium; C04 primary-market access; C05 corporate-market functioning; C06 interest coverage/stressed debt share; C07 credit gap/debt service; C08 deteriorating debt quality.

**Banks (7):** B01 bank relative equity stress; B02 market-value rate exposure; B03 runnable deposit concentration; B04 outflows/funding substitution; B05 usable liquidity; B06 lending standards/demand; B07 bank-sovereign linkage.

**Funding/functioning (8):** L01 overnight funding pressure; L02 market depth/price impact; L03 volatility-adjusted illiquidity; L04 Treasury cash-futures basis; L05 swap-spread dislocation; L06 collateral cash demand; L07 redemption mismatch; L08 backstop usage/market repair.

**Cross-border/FX (7):** X01 broad dollar shock; X02 cross-currency basis; X03 external liquidity coverage; X04 carry unwind signature; X05 country capital outflows; X06 issuer FX mismatch; X07 trade/network transmission.

**Macro (6):** G01 growth level/momentum; G02 inflation breadth/persistence; G03 labour deterioration; G04 earnings-revision breadth; G05 activity-price disagreement; G06 real-time regime ambiguity.

**Breadth/leadership (7):** Q01 participation; Q02 breadth velocity/persistence; Q03 new-low expansion; Q04 equal-weight versus cap-weight; Q05 leaders under stress; Q06 cross-sector downside breadth; Q07 concentration/profit support.

**Positioning/volatility (7):** P01 VIX level/term structure; P02 VVIX; P03 tail skew/insurance; P04 implied versus realized variance; P05 dealer hedge sensitivity; P06 crowded positioning/leverage; P07 prolonged low-volatility fragility.

**Sovereigns (5):** S01 sovereign risk compensation; S02 auction absorption; S03 maturity/service capacity; S04 currency-rate-equity stress combination; S05 bank-sovereign feedback.

**Repair (6):** H01 breadth repair quality; H02 credit-access repair; H03 funding repair; H04 failed-repair sequence; H05 profitability repair; H06 shock absorption/policy response.

A/B/C in the companion registry are research sequencing lanes, not empirical strength ratings: readily qualifiable existing/public observations first, richer filings next, licensed/private/limited-history measurements only when lawful and worthwhile. No new collector is assumed. Quarterly vulnerabilities condition fast shocks; they must not impersonate intraday observations. Do not revive killed calendar-gated risk, Hindenburg or standalone cross-organ flip-count constructions.

## 5. Propagation hypotheses and evidence

Fourteen proposed links are recorded, all HYPOTHESIS_ONLY:

- E01 M3→M2: physical squeeze→inflation pressure→policy repricing.
- E02 M2→M4: rate reset→interest burden→financing-access loss.
- E03 M1→M4: earnings decline→coverage erosion→credit repricing.
- E04 M2→M5: asset repricing plus runnable liabilities→bank liquidity pressure.
- E05 M4→M5: borrower losses→bank constraints.
- E06 M5→M1: restricted credit supply→activity/earnings pressure.
- E07 M6→M5: sovereign exposure→bank loss/funding pressure.
- E08 M5→M6: bank support/contingent liabilities→sovereign financing concern.
- E09 M7→M4: FX/funding squeeze→mismatched borrower credit stress.
- E10 M8→M7: leveraged liquidation→currency/funding pressures.
- E11 M9→M8: crowded losses→redemptions/cash demand→liquidation.
- E12 M8→M9: liquidity sales reach previously resilient equity groups.
- E13 M3→M8: commodity volatility→margin cash demand→position sales.
- E14 M6→M7: sovereign financing concern→external withdrawal/FX pressure.

Every claimed observed edge needs independent source and recipient evidence, correct availability-time ordering, a predetermined exposure or documented channel, and comparison against a common-shock alternative. Its ordinary observational ceiling is **transmission-consistent**, not proof of structural causality. Simultaneous returns alone are co-movement. A later report can support a retrospective autopsy but cannot become a then-known edge feature.

Do not force these into a directed acyclic graph: feedback is the research question. Separate the initial origin, amplification and later feedback rather than letting a loop count itself repeatedly. No fitted edge probability or runtime escalation is supplied in R1.

## 6. Historical findings and useful contrasts

The companion casebook contains nine qualitative, source-backed comparisons, not new numerical market backtests:

- 1997–98 Asia: short foreign-currency obligations and usable external liquidity matter; preserve then-known timing rather than importing retrospective tables. [S35,S36]
- 2007–09: housing/credit/funding developments unfolded over a sequence; monetary easing alone is not economic repair. NBER's December 2007 peak label was announced in December 2008, so it is not an available December 2007 predictor. [S25–S27]
- Euro-area sovereign/bank stress: holdings, guarantees, funding and the real economy provide distinct feedback routes. [S37,S38]
- March 2020: separate Treasury selling, funding strain and basis activity. OFR finds basis-trade unwinding likely followed, rather than solely initiated, the disconnect. Attribution is not settled by one popular explanation. [S13,S14]
- 2022 LDI: the relevant receiving exposure included derivative/repo cash demands and the ability to raise liquid collateral promptly. Economic duration hedging and cash-flow survival are different. [S16,S17]
- March 2023 banks: interest-rate exposure and runnable funding interact; bank share weakness alone is not a run. [S18,S19]
- August 2024: leveraged FX/equity exposures amplified an initial shock, followed by stabilization. Quote mechanics contributed to the VIX spike, so instrument quality must be separately assessed. [S20,S21]
- April 2025: Treasury cash liquidity deteriorated, but repo funding remained orderly; the NY Fed found no similar cash-futures basis unwind. This is a contained-funding contrast, not a claim that all asset losses were harmless. [S15]
- Concentration: ECB research contrasts profitable, cash-rich recent leaders with important dot-com-era differences. Narrow breadth is a vulnerability hypothesis, not sufficient evidence of imminent collapse. [S28]

Prolonged unusually low volatility can be associated with later financial fragility in historical cross-country work. That research has a multi-year vulnerability interpretation; it does not validate a next-week low-VIX/coiling rule. [S39,S40]

## 7. Rates damage must be an exposure surface

Use a transparent valuation/financing sensitivity alongside empirical evidence, never a universal dangerous Treasury level.

A deliberately simplified constant-growth illustration, V=CF1/(k−g), with k=10% and g=4% falls 14.29% when k alone rises to 11%. If g simultaneously rises to 4.5%, the decline is 7.69%; if g rises to 5%, the denominator is unchanged. This is algebra with k as the equity required return, not a calibrated Treasury-to-equity forecast.

For debt 100, coupon 3% and EBIT 12, interest is 3 and coverage 4×. If 30% resets to 6%, interest becomes 3.9 and coverage 3.08×; if all debt resets, coverage is 2×. A 20% EBIT decline produces coverage 2.46× and 1.6× respectively. This demonstrates the need to combine reset timing with earnings. It is not a universal default threshold.

For leveraged positions, a key proposed nonlinearity is cash needed before a contractual deadline versus cash/collateral actually mobilizable by that deadline. Total asset value is not automatically usable liquidity. Missing private exposure remains unknown rather than estimated with invented precision.

## 8. Historical memory and model design

Analogue retrieval uses only the information prefix available at the assessment date: backdrop, vulnerability, shock type/speed, sequence stage, market structure and source coverage. Exclude final trough, eventual loss, later interventions, retrospective regime labels and future realized volatility. Fit scaling/distance/feature choices on past training data only.

Return multiple paths—continued deterioration, contained correction, policy-assisted repair and failed repair—with disconfirming differences, sample size and uncertainty. Similarity is not a probability. Analogue cases are not independent if they share a global crisis or overlapping window. Novel environments must yield low confidence or no close analogue, not forced certainty.

Compare simple conditional baselines and regularized interactions before more flexible switching/hazard/graph models. The first question is incremental value versus the exact existing Radar, not whether a sophisticated model looks plausible. Conditioning must not win solely by issuing more warnings. Leave-one-crisis-family-out and first-warning performance are essential.

## 9. Frozen next scientific slice

Adjacent `R2_EMPIRICAL_PROTOCOL.md` owns exact next steps. Its primary question is whether rates information conditioned on growth/inflation and credit improves forecasts at matched warning burden. This is the first tractable vertical, not the limit of the wider program.

Primary US loss target: a future close at least 5% below the assessment close within 21 local sessions, excluding today's loss and requiring full-horizon maturity. Secondary targets: 10%/63 sessions, joint stock/bond loss, and continuous credit-spread deterioration. Later mechanism-specific research must separately grade bank/funding dysfunction, propagation and failed repair; those are not replaced by the equity target.

B0 base rate; B1 exact incumbent replay; B2 pooled additive; C1 four prespecified interactions; C2 separately qualified breadth/dollar/exposure augmentation. Historical window 2007-01-01–2026-09-25, expanding annual diagnostic tests from 2015, past-only fitting, 63-session purge, common samples, warning-burden comparisons, block/episode uncertainty and contained-stress controls. These historical cases are already design-exposed. No pristine holdout or prospective forecast is claimed.

Next action: qualify actual source availability, causal regime parameter lineage and incumbent replay identity, then freeze final feature manifests before constructing new outcomes. Data gaps block affected models only; do not silently substitute instruments or invent vintage metadata.

## 10. Actual verification, limits and continuation

R1 produced 40 primary-source records, 76 candidate measurements, nine overlapping mechanisms, fourteen hypothetical propagation links and nine historical comparisons. A small offline specification reference and 19 synthetic tests passed. They check timing, smoothed/future-data rejection, duplicate global origins, edge evidence, immature outcomes and package reference consistency. **They are not market backtests, production tests, predictive validation or independent scientific review.**

No R2 historical panel, fitted conditional model, source integration, country UI, live warning, sizing rule, deployment or native worker exists from R1. Parent delivery remains incomplete. Scope is retained by Sol; no early native implementation handoff is issued.

Prior MOVE carrier `claude/move-risk-radar-20260927-sol` and preregistration commit `cde02b08c8c7ceab0a06ffee7724c1c0b374eadb` remain separate. Its denied shared snapshot/projection/UI write was reconciled EFFECT_NONE. Do not retry, delegate or route around those exact denied effects. Do not release existing China/Radar/recovery HOLD PRs through this research.

The R1→R2 boundary is substantive: source qualification and empirical construction require a new, materially heavier data phase. Resume from this record and #8128 rather than repeating taxonomy/source archaeology. Re-pin procedure and inspect only material source/custody invalidators.

## Companion artifact SHA-256s

- Main research: `e90e33c6a663fcc94a9023ed82ecbe08e9ffc6ef7f7178dd774ea0cf52d541c3`
- Indicator map: `5473c5bf60e8f37c6d02839dcf318268938138c0b701baa88a3bb578fefa0c7a`
- Indicator registry: `655ef96080d7e9f518d5a34bfd6ae3f726380208e84aff8be106901b3f41dac8`
- Mechanisms/edges: `7736746e02f0c75ddffffac94e8e550da29a0d741109ac87dd3769d016b10b05`
- Casebook: `ef84a63e6cc62b42863cefd5a9e3af51ee836f79a6ca8987bee7b1bdac8698f7`
- R2 protocol: `33059dc1c92359bf0f1c3d54c8e6054c71cdbf17117b59ef2bd0e201d1a7b6d3`
- Source registry: `ccb1e4342980bd9e8bcf13091d7d16deb28956b7cb4e23ccb303586890fdf0c6`
- Experiment contract: `93792c892108129c8ef1bf843afc78e2a64607f1d7f8d4f7316a5b1e1b06684d`

Source references S01–S40 are resolved in the adjacent source register. These are research provenance, not authority grants.
