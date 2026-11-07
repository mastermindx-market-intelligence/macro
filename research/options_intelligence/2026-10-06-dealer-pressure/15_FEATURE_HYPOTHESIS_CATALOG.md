# Feature and falsifiable-hypothesis catalog

**72 research candidates; all SPEC_ONLY.** This is an extension index to the October 3 OIF ontology, not an options score or automatic selection for implementation. Exact aliases retain the earlier feature's eligibility, clock, units and registration. Changes in population, formula or horizon are additive hypotheses. No row has a fabricated confidence percentage.

## Common notation and limits

The inventory h is signed dealer contracts under a named model/scenario; m is the actual deliverable/risk multiplier; Delta/Gamma/Vanna use the declared native pricing coordinate; S is that coordinate; B is the negative covered option delta and H is endpoint target-change reference notional. Q_exec requires an explicit execution policy; otherwise use a labeled policy scenario. a denotes option aggressor sign, never dealer capacity. q is contracts for options or native quantity for the named tape; option_price is premium per quoted unit. Price/volatility/scale conventions are fixed at formation.

scale_t is a positive ex-ante price scale fitted on previous data, not the day's eventual range. h0 is the qualified beginning inventory, not all prior OI assigned to dealers. For cross-product quantities use report08's native-to-common-factor map before summing. Every row includes formula, units, economic and availability clocks, evidence class, source, mechanism, confounders, horizon, falsifier, null behavior and an incumbent owner. Sources referenced by report filename inherit that report's exact source register; they are not unsourced performance claims.

All source-age limits, lookbacks, price bands and thresholds are preregistered training choices, not secretly optimized on test outcomes. The primary slice takes only a small predeclared block; the full catalog is a finite research backlog under the incumbent TrialLedger inspection budget. Incomplete source coverage is not zero economic activity. Model probabilities, unweighted scenario fractions and descriptive frequencies remain different quantities.

Machine-readable equivalents: [CSV](15_FEATURE_HYPOTHESIS_CATALOG.csv) and [JSON](specs/feature_catalog.json).

## Structural inventory

### DPF-01 — OI strike concentration

- **Formula:** sum_k (OI_k / sum_j OI_j)^2; same root and deliverable class
- **Units:** dimensionless HHI
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** Concentrated contract activity may locate mechanically sensitive areas.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 15–60 min; remaining session
- **Falsifier:** No incremental score improvement over distance/volatility-matched price levels.
- **Missing data:** Null for zero/missing total OI; partial coverage explicit.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** Refines OIF-16

### DPF-02 — Gross gamma strike concentration

- **Formula:** sum_k (Ggross_k / sum_j Ggross_j)^2, Ggross_k=sum_i_in_k |h_i| m_i Gamma_i S^2*0.01
- **Units:** dimensionless HHI
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** Measures concentration of scenario risk without net-sign cancellation.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 5–60 min
- **Falsifier:** Effect vanishes after unsigned activity and near-spot distance controls.
- **Missing data:** Null if denominator zero/unknown; inferred h stays scenario.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** OIF-16 extension

### DPF-03 — Signed inventory expectation

- **Formula:** E[h_i,t | O_available<=t] for each canonical contract i
- **Units:** contracts, per contract identity
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** A probabilistic book can improve delta-risk measurement over assumed signs.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 5–60 min
- **Falsifier:** Risk-weighted measurement and forecast error do not improve over M0/M2.
- **Missing data:** No mean unless model probabilities defined; otherwise feasible interval only.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** New extension

### DPF-04 — Inventory scenario entropy

- **Formula:** -sum_r w_r log(w_r), discrete joint scenario weights summing to1
- **Units:** nats
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** High disagreement can govern abstention and sensitivity reporting.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** Current decision
- **Falsifier:** Entropy does not stratify subsequent measurement or forecast errors.
- **Missing data:** Null for unweighted scenario set; do not fabricate probability weights.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** New extension

### DPF-05 — Nearest signed-gamma transition distance

- **Formula:** (S - nearest root of sum_i h_i m_i Gamma_i(s)=0)/scale_t in declared domain
- **Units:** ex-ante scale units
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** A risk-response transition may alter continuation/reversal tendencies.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 5–60 min
- **Falsifier:** Matched random transitions perform equally after density/distance controls.
- **Missing data:** No root -> explicit no_crossing; unknown book -> null.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** Refines OIF-17; not gross wall alias

### DPF-06 — Gamma topology count

- **Formula:** count of resolved sign-changing roots in frozen domain, with plateau/tangency flags
- **Units:** count
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** Multiple transitions invalidate a one-flip regime description.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** Current–60 min
- **Falsifier:** Topology has no incremental value or is numerically unstable.
- **Missing data:** Unknown roots/missing intervals reported; finite grid is not exhaustive proof.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** New extension

### DPF-07 — Expiry risk concentration

- **Formula:** sum_e (Ggross_e / sum_j Ggross_j)^2
- **Units:** dimensionless HHI
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** One expiry may dominate sensitivity to time and fixing.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 15 min–close
- **Falsifier:** No incremental value beyond total gross gamma and time-to-fixing.
- **Missing data:** Null for zero/unknown gross risk.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** Extends OIF-16 / expiry VEX-CEX

### DPF-08 — Inherited versus intraday traded gamma

- **Formula:** (G_inherited,G_traded,G_adjustment)=S^2*0.01*sum_i m_i Gamma_i*(h_i,0, u_i,t, a_i,t)
- **Units:** USD per 1% spot move, three components
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [R02]; [R03]; [I04]; [I19]
- **Mechanism:** Separates inherited inventory from net trading, including closures, and nontrade adjustments; traded does not mean newly opened.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 10–60 min
- **Falsifier:** New-trade-only model matches performance and inherited block adds nothing.
- **Missing data:** Unknown start -> interval/scenario; never treat all volume as new risk.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** New extension

### DPF-09 — Signed to gross gamma

- **Formula:** sum_i h_i m_i Gamma_i / sum_i |h_i| m_i Gamma_i
- **Units:** dimensionless signed fraction
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** max(source receipt, reference availability, completed inference); next OI only after actual release
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** High cancellation exposes sensitivity to inventory error.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** 5–60 min
- **Falsifier:** Cancellation fraction does not explain instability or improve forecasts.
- **Missing data:** Null when gross risk zero/unknown; complete net zero may be valid.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** New extension

### DPF-72 — Later-OI reconciliation residual

- **Formula:** OI_Dplus1 - OI_D - sum_n(x_oo-x_cc) - nontrade_adjustments
- **Units:** contracts per canonical series
- **Event clock:** Eligible chain/OI economic vintage and decision state
- **Known at:** Actual following OI availability; permitted only after receipt, including model-label maturity.
- **Evidence / sources:** Model/scenario; descriptive structure — [I04]; [I11]; [I14]; [I19]; [R18]
- **Mechanism:** Diagnoses model/source consistency and trains later filters.
- **Confounders:** Incomplete signed inventory; stale OI; corporate actions; selection
- **Horizon:** Following release; future sessions only
- **Falsifier:** Residual fit improves without better future filtering or predictive value.
- **Missing data:** Unknown adjustments/history -> bounded residual; never force exact fit.
- **Owner:** engine/gex_engine.py; engine/thetadata_store.py; existing options owner
- **OIF relationship:** OIF-18 extension

## Live flow

### DPF-10 — Classified signed dollar delta

- **Formula:** sum_n a_n q_n m_n Delta_n S_n; a=+1 buy aggressor,-1 sell aggressor
- **Units:** USD underlying-risk equivalent
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Public aggressive option-risk flow is a simple competing predictor.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 1–30 min
- **Falsifier:** Fails against synchronized underlying returns and unsigned activity.
- **Missing data:** Unknown sign excluded with risk/premium coverage; no dealer label.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** OIF-04 alias with same eligibility

### DPF-11 — Signed gamma turnover

- **Formula:** sum_n a_n q_n m_n Gamma_n S_n^2*0.01
- **Units:** USD per 1% move
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Measures aggressor-side gamma demand, separately from dealer inventory.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 5–30 min
- **Falsifier:** No gain over unsigned gamma turnover or signed delta.
- **Missing data:** Unknown sign/Greek -> unknown; do not infer capacity.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** Extends gross OIF-31; not exact alias

### DPF-12 — Ask versus bid quote-location imbalance

- **Formula:** (premium_at_ask - premium_at_bid)/(premium_at_ask + premium_at_bid)
- **Units:** dimensionless signed fraction
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Execution location describes urgency/quote interaction.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 1–15 min
- **Falsifier:** Disappears after quote-age and underlying-return controls.
- **Missing data:** Zero denominator -> null; inside/outside/unknown shares retained.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** Existing live-flow measurement refinement

### DPF-13 — Unclassified premium fraction

- **Formula:** sum_unknown q*m*option_price / sum_all_valid_source q*m*option_price
- **Units:** fraction
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Measures inference abstention and selection risk.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** Current window
- **Falsifier:** Unknown fraction fails to predict error or silently removes difficult trades.
- **Missing data:** Null if source premium denominator missing; retained-source coverage not national coverage.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** OIF-06 / OIF-37 extension

### DPF-14 — Verified package net delta flow

- **Formula:** sum_verified_packages sum_legs s_leg q_leg m_leg Delta_leg S_leg
- **Units:** USD risk equivalent
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Economic leg netting prevents overstating outright directional demand.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 1–30 min
- **Falsifier:** No improvement over leg-level flow with identical source coverage.
- **Missing data:** Unknown package or leg direction -> unclassified package; do not infer solely from timestamps.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** New extension

### DPF-15 — Signed flow persistence

- **Formula:** sum_b x_b / sum_b |x_b| for prior completed buckets x_b=DPF-10
- **Units:** dimensionless signed fraction
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Repeated same-direction activity may outlast a single print.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 5–30 min
- **Falsifier:** Time-of-day and underlying momentum explain all value.
- **Missing data:** Zero sum of absolute bucket-net flows -> explicit no_net_flow; can occur despite gross trading. Missing buckets -> null/coverage.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** Magnitude-weighted OIF-05 variant; original sign-agreement comparator retained

### DPF-16 — Flow acceleration

- **Formula:** OLS slope of x_b/duration_b against bucket time over trailing window
- **Units:** USD per second squared
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Change in risk-flow rate may precede book-state revisions.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 1–15 min
- **Falsifier:** No gain beyond current rate and lagged stock movement.
- **Missing data:** Insufficient completed buckets -> null; no centered future window.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** New extension

### DPF-17 — Participant-coded MM net buy

- **Formula:** Delta[MM_buy_vol_cumulative - MM_sell_vol_cumulative] per canonical series and compatible segment; _vol is contracts, _qty is trade count
- **Units:** contracts per compatible interval
- **Event clock:** Canonical-series aggregate interval end with cumulative trading-date/segment/reset identity
- **Known at:** Actual release/receipt after interval end; corrected vintage separately tagged.
- **Evidence / sources:** Observed scoped participant-coded net trading; absolute starting inventory remains inferred — [A29]; [A30]; [A31]; [A33]; [R02]; [R03]
- **Mechanism:** Directly measures scoped signed inventory change, irrespective open/close.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** 15–30 min with release lag
- **Falsifier:** Does not improve scoped inventory measurement or forecasts over public model.
- **Missing data:** Missing/corrected/reset interval -> explicit gap/revision, not new trade.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** New extension

### DPF-18 — Trade/quote age tail

- **Formula:** 95th percentile of trade_event_time - preceding_quote_event_time in eligible common clock
- **Units:** milliseconds
- **Event clock:** Eligible trade event and preceding quote in the same clock domain
- **Known at:** max(trade receipt, quote receipt, reference/Greek availability, completed aggregation)
- **Evidence / sources:** Observed quote location plus separately inferred sign — [I04]; [I13]; [I14]; [I25]; [I31]; [R04]; [R07]
- **Mechanism:** Stale quote matching can create false apparent information.
- **Confounders:** Packages; stale quotes; passive customers; corrections; sample coverage
- **Horizon:** Current window
- **Falsifier:** Stratification does not change sign/leading-signal error.
- **Missing data:** Unknown clock relationship -> null; receipt latency reported separately.
- **Owner:** engine/live_flow.py; engine/flow_signing.py; scripts/live_flow_poller.py
- **OIF relationship:** OIF-37 extension

## Nonlinear hedging

### DPF-19 — Full spot-only hedge stress

- **Formula:** H=S_star*[B(S_star,sigma0,t0,h0)-B(S0,sigma0,t0,h0)]
- **Units:** USD reference notional
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Nonlinear delta response to a declared spot shock.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** Scenario 5–30 min
- **Falsifier:** Fails to add value over gamma-only approximation after equal inputs.
- **Missing data:** Null if whole-book endpoint coverage fails.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-13 factor ablation

### DPF-20 — Full IV-only hedge stress

- **Formula:** H=S0*[B(S0,sigma0+0.01,t0,h0)-B(S0,sigma0,t0,h0)]
- **Units:** USD per stated +1 IV-point scenario
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Reprices nonlinear delta under parallel volatility shift.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** 5–30 min
- **Falsifier:** Vanna/full-IV block adds nothing beyond raw IV movement.
- **Missing data:** Unsupported surface nodes -> explicit partial bounds or null.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-13 / OIF-14 extension

### DPF-21 — Exact time-runoff demand

- **Formula:** H=S0*[B(S0,sigma0,t0+h,h0)-B(S0,sigma0,t0,h0)]
- **Units:** USD per declared horizon
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Measures changing target delta from advancing time.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** 1–30 min
- **Falsifier:** No incremental forecast value after gamma, time-of-day and controls.
- **Missing data:** Fixing crossing -> explicit settlement transition; not tiny positive TTE.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-15 / OIF-32 extension

### DPF-22 — Joint spot-vol-time-inventory demand

- **Formula:** H=S_star*[B(S_star,sigma_star,t_star,h_star)-B(S0,sigma0,t0,h0)]
- **Units:** USD reference notional
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Reference nonlinear scenario including interactions and new positions.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** 5–60 min
- **Falsifier:** Does not beat simpler flow/gamma/liquidity model out of sample.
- **Missing data:** Missing h_star -> scenario family; no fabricated expectation.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-13 expanded inventory contract

### DPF-23 — Local vanna diagnostic

- **Formula:** -S0*sum_i h_i m_i Vanna_i*0.01
- **Units:** USD per +1 IV-point local change
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Explains local IV sensitivity within exact repricing.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** Small shock
- **Falsifier:** Wrong sign/large residual versus independent endpoint repricing.
- **Missing data:** Missing vanna -> null, never zero.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-14 alias under identical convention

### DPF-24 — Local hedge elasticity

- **Formula:** dB/dS=-sum_i h_i m_i Gamma_i
- **Units:** underlying-equivalent units per price point
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Countercyclical/procyclical target response to small moves.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** Current–15 min
- **Falsifier:** Response fails finite-difference sign/unit witness or adds no forecast value.
- **Missing data:** Unknown inventory/Greek -> scenario/null.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** OIF-11/12 derivative interpretation

### DPF-25 — Linearization residual

- **Formula:** H_exact - H_gamma_vanna_charm
- **Units:** USD reference notional
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Identifies when local Greeks are inadequate near expiry or large shocks.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** Scenario horizon
- **Falsifier:** Residual stays within useful tolerance and full repricing offers no gain.
- **Missing data:** Relative error null near zero reference; absolute residual retained.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** New extension

### DPF-26 — Surface-convention dispersion

- **Formula:** max_model H_model - min_model H_model over fixed/sticky/learned eligible surfaces
- **Units:** USD reference notional
- **Event clock:** Frozen anchor state and explicit future scenario endpoint
- **Known at:** Anchor inputs available and scenario computation completed; future state is hypothetical
- **Evidence / sources:** Conditional mathematical scenario — [I03]; [I04]; [I21]; [I22]; [I23]; [R14]; [R15]
- **Mechanism:** Exposes model rather than inventory uncertainty.
- **Confounders:** Inventory sign; surface dynamics; hedge policy; missing book
- **Horizon:** 5–60 min
- **Falsifier:** Disagreement does not stratify forecast error and costly models add no value.
- **Missing data:** Fewer than2 qualified alternatives -> unavailable dispersion; not zero.
- **Owner:** engine/options_scenario_surface.py; engine/intraday_greeks.py; engine/exposure_math.py
- **OIF relationship:** New extension

## 0DTE

### DPF-27 — Same-day-expiry activity share

- **Formula:** sum_0DTE q*m / sum_all_same_root q*m
- **Units:** fraction
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Relative expiring activity may interact with liquidity and inherited risk.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** 5–60 min
- **Falsifier:** No incremental effect after time-of-day and total activity.
- **Missing data:** Null if same-root denominator zero/incomplete.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-29 alias with same cohort

### DPF-28 — Near-spot 0DTE gamma fraction

- **Formula:** sum_0DTE,|log(K/S)|<=0.005 |h|m Gamma / sum_0DTE |h|m Gamma
- **Units:** fraction
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Locates risk concentrated near the current fixing region.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** 1–30 min
- **Falsifier:** Matched concentration/distance baselines perform equally.
- **Missing data:** Zero/unknown denominator -> null; missing book bound explicit.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-33 refinement; h assumption preserved

### DPF-29 — Exact sixty-second runoff velocity

- **Formula:** -sum_0DTE h*m*[Delta(t+60s)-Delta(t)]/60
- **Units:** underlying-equivalent units per second
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Separates exact near-expiry target adjustment from charm shorthand.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** Next60seconds scenario
- **Falsifier:** Local charm is adequate or no incremental predictive value.
- **Missing data:** At/inside60s fixing margin use explicit transition, not clipped formula.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-32 alias plus unit conversion

### DPF-30 — Classified 0DTE signed dollar delta

- **Formula:** sum_0DTE a*q*m*Delta*S
- **Units:** USD risk equivalent
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Same-day aggressive risk demand distinct from inherited inventory.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** 1–15 min
- **Falsifier:** Adds no value beyond all-expiry flow and underlying returns.
- **Missing data:** Unknown sign/Greek -> abstain with coverage.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-30 alias

### DPF-31 — Inventory-induced hedge uncertainty

- **Formula:** quantile_0.95(H_h)-quantile_0.05(H_h) under defined inventory posterior
- **Units:** USD reference notional
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Inventory uncertainty may overwhelm a precise-looking node.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** 5–30 min
- **Falsifier:** Intervals miscalibrated against scoped labels or fail useful error stratification.
- **Missing data:** No calibrated posterior -> min/max scenario range labeled nonprobabilistic.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** New extension

### DPF-32 — Fixing-clock margin

- **Formula:** economic_fixing_time - decision_time, plus last-tradable/exercise state
- **Units:** seconds; categorical state
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Near-expiry formulas depend on payoff time and trading eligibility.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** Current–close
- **Falsifier:** Wrong calendar/reference recreates false Greeks or unsupported trading state.
- **Missing data:** Unknown/variable AM fixing -> fixing_pending state, not a guessed timestamp.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-40 / near-expiry clock extension

### DPF-33 — Remaining total implied variance

- **Formula:** sigma_i^2 * tau_i in declared annualization convention
- **Units:** dimensionless total variance
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Prevents confusing vanishing time value with annualized IV going to zero.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** Current–fixing
- **Falsifier:** No diagnostic improvement over explicit exact-time price residuals.
- **Missing data:** Invalid bid/ask/model/TTE -> null; no forced sigma=0.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** New extension

### DPF-34 — Exact-time joint IV and Greek discrepancy

- **Formula:** (IV_floor-IV_exact, Greeks_floor-Greeks_exact), Greeks=(delta,gamma,vanna,charm), plus separately labeled fixed-IV sensitivity comparison
- **Units:** IV decimal points and native declared Greek units; advancing-calendar charm
- **Event clock:** Contract-specific fixing clock, observed chain/trade anchor
- **Known at:** max(required input receipts, exact reference availability, computation); no later OI
- **Evidence / sources:** Observed activity or conditional near-expiry mechanics — [I04]; [I05]; [I14]; [I22]; [R02]; [R03]
- **Mechanism:** Joint IV/Greek qualification avoids missing time-floor error when price refitting preserves gamma.
- **Confounders:** TTE floors; inherited positions; fixing/assignment; price precision
- **Horizon:** Finalhour
- **Falsifier:** A universal scalar correction fails paired-price and exact-clock numerical witnesses.
- **Missing data:** Unavailable exact fixing or executable price -> null.
- **Owner:** engine/intraday_greeks.py; engine/options_structure_intraday.py; existing flow owner
- **OIF relationship:** OIF-34 joint diagnostic retained; floor-minus-exact convention

## Cross-product

### DPF-35 — SPX versus SPY demand divergence

- **Formula:** H_SPX/GrossH_SPX - H_SPY/GrossH_SPY using same shock,horizon,factor and covered gross cohort demand
- **Units:** dimensionless signed difference
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Divergence may reveal substitution or incomplete book assumptions.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** 5–30 min
- **Falsifier:** Disappears under synchronized prices/basis or adds no value.
- **Missing data:** Any gross denominator zero/unknown -> null; show native H values.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

### DPF-36 — ES-equivalent target change

- **Formula:** n_ES(x1)-n_ES(x0), n_ES=-sum_i h_i*m_i*Delta_i*dU_i/dI /(50*dF_ES/dI)
- **Units:** ES contracts
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Converts S&P common-factor risk into an executable hedge coordinate.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** 5–30 min
- **Falsifier:** Residual basis risk dominates or cross-product model fails single-product baseline.
- **Missing data:** Missing conversion/contract/roll -> null; SPX not treated as shares.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

### DPF-37 — NQ-equivalent target change

- **Formula:** n_NQ(x1)-n_NQ(x0), n_NQ=-sum_i h_i*m_i*Delta_i*dU_i/dI /(20*dF_NQ/dI)
- **Units:** NQ contracts
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Native Nasdaq product risks require distinct multipliers/basis.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** 5–30 min
- **Falsifier:** No incremental value after residual-risk and liquidity adjustment.
- **Missing data:** Missing admitted Nasdaq source -> unavailable; no SPX beta substitution.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

### DPF-38 — Futures/index basis residual

- **Formula:** F_t - I_t*exp((r-q)*(T_f-t)); empirical alternative F_t-alpha_t-beta_t*ETF_t
- **Units:** native index points
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Carry/ETF substitution state can distinguish hedge basis from direction.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** 1–60 min
- **Falsifier:** Apparent signal is stale-reference or roll artifact.
- **Missing data:** Unsynchronized source/carry -> null; train alpha/beta before decision.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

### DPF-39 — Joint product coverage

- **Formula:** eligible canonical contracts / expected contracts from admitted population manifest; interval receipt coverage separately
- **Units:** fractions with denominator identities
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Prevents treating retained rows as full market coverage.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** Current window
- **Falsifier:** Coverage claims fail manifest reconciliation or systematically omit high-risk contracts.
- **Missing data:** Unknown expected universe -> unknown coverage; risk coverage only with excluded-risk bounds.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

### DPF-40 — Cross-product net-to-gross demand

- **Formula:** abs(sum_p H_p) / sum_p abs(H_p) in one common factor and horizon
- **Units:** fraction
- **Event clock:** Synchronized native product states and economic contract/roll references
- **Known at:** max(all product input receipts, reference/basis-model availability, computation)
- **Evidence / sources:** Conditional common-factor risk; not whole-dealer-book truth — [I03]; [I21]; [I23]; [IPR8451]; 08_CROSS_PRODUCT_EXPOSURE_SPEC.md
- **Mechanism:** Offsetting product demands may reduce external hedge requirement.
- **Confounders:** Basis; beta instability; OTC omissions; duplicate exposures; settlement
- **Horizon:** 5–30 min
- **Falsifier:** Apparent netting fails hedge-allocation/residual-risk tests.
- **Missing data:** Zero complete gross -> zero-flow state; unknown coverage -> null.
- **Owner:** engine/exposure_math.py; existing options owner; Data OS / Macro #8451
- **OIF relationship:** New extension

## Liquidity

### DPF-41 — Best-level order-flow imbalance

- **Formula:** sum_n[1(b_n>=b_prev)qB_n-1(b_n<=b_prev)qB_prev-1(a_n<=a_prev)qA_n+1(a_n>=a_prev)qA_prev]
- **Units:** shares or futures contracts
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Queue changes capture supply/demand beyond trade prints.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 1–15 min
- **Falsifier:** No incremental value over signed trades, depth and returns.
- **Missing data:** No continuous eligible quote events -> unavailable, never OHLCV substitute.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-42 — Depth imbalance

- **Formula:** (D_bid(epsilon)-D_ask(epsilon))/(D_bid(epsilon)+D_ask(epsilon))
- **Units:** dimensionless signed fraction
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Asymmetric accessible depth may condition pressure impact.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** Seconds–5 min
- **Falsifier:** Cancels/spoof-like ephemeral quotes or market controls explain effect.
- **Missing data:** Zero/unknown depth -> null; band and venue coverage explicit.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-43 — Trailing depth depletion

- **Formula:** max(0,D_side(t-w)-D_side(t))/D_side(t-w)
- **Units:** fraction per fixed trailing window
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Weakening side capacity may expose a fragile move.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** Seconds–5 min
- **Falsifier:** No incremental value after contemporaneous return/OFI; cancels confound.
- **Missing data:** Missing book interval or initial zero -> null.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-44 — Matured replenishment ratio

- **Formula:** (D_side(tau+h)-D_min_event)/D_pre_event for depletion episodes with tau+h<=t
- **Units:** fraction
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Observed refill history informs expected executable capacity.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** Next1–15 min
- **Falsifier:** Historical refill does not predict next-episode capacity/impact.
- **Missing data:** Unmatured/unknown episode -> excluded with counts; no future refill leak.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-45 — Relative quoted spread

- **Formula:** 10000*(ask-bid)/mid
- **Units:** basis points
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Wide spread signals execution friction and source quality.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** Current–15 min
- **Falsifier:** Adds no useful forecast/friction information after volatility/depth.
- **Missing data:** Locked/crossed/one-sided -> explicit state, not zero.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** OIF-35 underlying analogue; contract quote owner unchanged

### DPF-46 — Lag-trained impact coefficient

- **Formula:** beta_Q in past-only regression r_h=alpha+beta_Q*signed_quantity+state_controls
- **Units:** return per share or futures contract
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Maps flow scale to conditional price response.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 1–15 min
- **Falsifier:** Out-of-sample impact error matches naive volume curve; reverse causality dominates.
- **Missing data:** Insufficient matured response sample -> null; coefficient not causal.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-47 — Hedge participation proxy

- **Formula:** abs(E[Q_exec_h])/E[market_volume_h] in identical units/instrument
- **Units:** fraction
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Tests whether modeled net demand is material relative to horizon activity.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 5–30 min
- **Falsifier:** Fails to beat raw demand and time-of-day volume separately.
- **Missing data:** Execution expectation unavailable -> labeled policy scenario; denominator unknown -> null.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-48 — Directional executable-capacity ratio

- **Formula:** abs(Q_exec_h)/L_side,h(epsilon)
- **Units:** dimensionless ratio
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Compares demand with capacity under declared impact tolerance.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 1–15 min
- **Falsifier:** No gain beyond participation proxy after equal input/cost.
- **Missing data:** No qualified depth/refill/impact model -> unavailable; not fabricated from ADV.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-49 — Impact relative to volatility

- **Formula:** abs(expected_return_impact_h)/predicted_return_sd_h
- **Units:** dimensionless ratio
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Measures potential importance against normal horizon movement.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 5–30 min
- **Falsifier:** No predictive interaction gain or severe calibration failure in stress.
- **Missing data:** Either estimate unavailable/zero scale -> null.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-50 — Eligible trade intensity

- **Formula:** eligible_contracts_or_shares_in(t-w,t] / w_seconds; trade count separately
- **Units:** contracts or shares per second
- **Event clock:** Eligible quote/trade event window ending at decision t
- **Known at:** All required events received; response-fit labels mature before model freeze
- **Evidence / sources:** Observed microstructure or lag-trained predictive estimate — [I08]; [I10]; [IPR8451]; [R01]; [R10]; [R11]
- **Mechanism:** Activity regime changes expected replenishment and competition for liquidity.
- **Confounders:** Cancellations; hidden liquidity; news; endogenous flow; feed gaps
- **Horizon:** 1–15 min
- **Falsifier:** Seasonality-only model performs equally.
- **Missing data:** Gap/unknown coverage -> null; complete zero activity -> zero.
- **Owner:** Existing Quote Plane and Data OS; Macro #8451; incumbent evaluation owner
- **OIF relationship:** New extension

## Nodes

### DPF-51 — Absorption elasticity

- **Formula:** -dB/dS near zone, conditioned on materiality and fixed scenario
- **Units:** hedge units per price point
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** The negative of local hedge elasticity interpreted within a frozen zone and materiality gate; no duplicate evidentiary credit.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** 5–30 min
- **Falsifier:** Frozen-zone hold probability adds nothing after matched price/liquidity controls.
- **Missing data:** Sign disagreement -> scenario-sensitive; missing liquidity -> unqualified.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** Node-conditioned negative of DPF-24; not independent feature evidence

### DPF-52 — Anchored inward-pressure strength

- **Formula:** min(F(z-w),-F(z+w)) for expected signed execution rate F, requiring F(z)=0
- **Units:** hedge units per second
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** Positive inward signs may define an attractor under a stated dynamic policy.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** 5–30 min
- **Falsifier:** No stable root or no calibrated retention gain versus damping-only baseline.
- **Missing data:** No justified F expectation -> scenario attractor only; no probability.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** New extension

### DPF-53 — Procyclical acceleration gradient

- **Formula:** d^2B/dS^2 on an explicitly oriented break path, plus sign(dB/dS)>0
- **Units:** hedge units per price-point squared
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** A break may increase required procyclical target adjustment.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** 1–15 min
- **Falsifier:** No incremental break/continuation value beyond return,volatility,depth.
- **Missing data:** Grid/derivative unstable or assumptions disagree -> null/bounds.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** New extension

### DPF-54 — Nearest behavioral-transition distance

- **Formula:** min_z |S-z|/scale_t over qualified transitions; signed side retained
- **Units:** ex-ante scale units
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** Proximity to a robust response-state change may alter passage hazards.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** 5–60 min
- **Falsifier:** Matched random nodes explain same hazards.
- **Missing data:** No qualified transition -> no_transition, not zero distance.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** New extension

### DPF-55 — Scenario classification stability

- **Formula:** number_of_admissible_scenarios_with_same_label / total_admissible_scenarios
- **Units:** fraction, explicitly not probability
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** Exposes sensitivity of a zone label to modeling assumptions.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** Current–30 min
- **Falsifier:** Stability does not stratify later classification/forecast error.
- **Missing data:** No scenarios or incomplete domain -> unavailable; ensemble design versioned.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** New extension

### DPF-56 — Liquidity-reservoir memory

- **Formula:** lag-trained expected executable size within zone and impact tolerance from matured depth/response episodes
- **Units:** shares or futures contracts
- **Event clock:** Frozen anchor field and price/liquidity window
- **Known at:** All anchor inputs and extraction complete; no subsequent extrema or retests
- **Evidence / sources:** Scenario topology; probability only after separate calibration — [I04]; [I23]; [R01]; [R09]; 09_BEHAVIORAL_NODE_SPEC.md
- **Mechanism:** Underlying liquidity can absorb independently of option positioning.
- **Confounders:** Grid domain; inventory sign; liquidity; moving boundaries; selection
- **Horizon:** 1–30 min
- **Falsifier:** No value versus current depth and matched price-volume zones.
- **Missing data:** Only historical prints available -> execution-memory statistic, not resting capacity.
- **Owner:** Existing GEX/scenario owner and topology carrier Macro #7322
- **OIF relationship:** New extension

## Closing

### DPF-57 — Scheduled rebalance demand relative to ADV

- **Formula:** sum_f AUM_f*(w_new-w_price_drifted)_i / (price_i*ADV_shares_i), with tracking/execution fractions as scenarios
- **Units:** signed fraction of ADV
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A42]; [A43]; [A45]; [A59]; [A60]; [A61]; [A62]; [A63]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Public weight changes can create predictable benchmark demand.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Announcement–close
- **Falsifier:** Does not improve official-imbalance/close forecasts after event controls.
- **Missing data:** Missing AUM/weights/known-at -> bounds or unavailable; no exact passive ownership claim.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-58 — Pre-public signed auction-demand forecast

- **Formula:** E[MOC_like_net_shares | pre_public_information_t], interval and source universe included
- **Units:** shares
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A19]; [A20]; [A42]; [A45]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Forecasts late benchmark imbalance before relevant official dissemination.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Before venue-specific first disclosure
- **Falsifier:** Fails against historical symbol/time/event auction baseline.
- **Missing data:** Uncalibrated model -> scenario range; early indication receipt never backdated.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-59 — Normalized official imbalance

- **Formula:** signed_imbalance_shares/(paired_shares+abs(imbalance_shares))
- **Units:** dimensionless signed fraction
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Measures mismatch relative to matched interest in that feed.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** After official publication–auction
- **Falsifier:** No gain beyond raw imbalance/auction phase; venue pooling hides errors.
- **Missing data:** Both zero -> zero only with valid message; missing fields -> null.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-60 — Official imbalance velocity

- **Formula:** (I_t-I_prev)/(message_time_t-message_time_prev)
- **Units:** shares per second
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Revisions reflect arriving/canceling auction demand.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Last1–10 min by venue
- **Falsifier:** No gain beyond current I and message-age state.
- **Missing data:** Gap/correction/reset -> flagged or null; unchanged messages handled by feed law.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-61 — Indicative clearing displacement

- **Formula:** 10000*(indicative_price/reference_price-1)
- **Units:** basis points
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Current auction-clearing pressure relative to reference.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** After dissemination–close
- **Falsifier:** No added close-price accuracy beyond continuous midpoint/basis.
- **Missing data:** Indicative/reference undefined or invalid -> null, never0.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-62 — Nasdaq near-far price spread

- **Formula:** 10000*(near_price-far_price)/reference_price
- **Units:** basis points
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Separates two rule-defined clearing calculations.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Full NOII phase–close
- **Falsifier:** Adds no nowcast value after current imbalance/indicative price.
- **Missing data:** Venue/phase does not supply valid fields -> not_applicable/null.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-63 — Paired-interest growth rate

- **Formula:** (paired_t-paired_prev)/delta_seconds
- **Units:** paired shares per second
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Tracks matched auction interest and potential changing elasticity.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Last1–10 min
- **Falsifier:** No value after total size and phase; not monotonic by assumption.
- **Missing data:** Missing/reset/corrected snapshot -> flagged or null.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-64 — First-disclosure surprise

- **Formula:** first_public_signed_imbalance - forecast_frozen_before_publication
- **Units:** shares; optional lag-trained standardized residual
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A15]; [A19]; [A20]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Separates anticipated close demand from new disclosed information.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** First disclosure–close
- **Falsifier:** No incremental response prediction after imbalance level.
- **Missing data:** No genuinely earlier forecast -> unavailable; never reconstruct it after seeing first message.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-65 — Time to next phase cutoff

- **Formula:** next_venue_rule_cutoff - decision_time
- **Units:** seconds plus phase/rule version
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A07]; [A13]; [A15]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Cancel/entry/freeze constraints change message informativeness.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Last60 min
- **Falsifier:** Pooled model performs equally across verified phases/eras.
- **Missing data:** Unverified implementation version/early-close calendar -> phase unknown.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

### DPF-66 — Historical auction elasticity

- **Formula:** beta in past-only regression close_return_bps ~ signed_imbalance/ADV + paired_liquidity + state
- **Units:** bps per fraction of ADV
- **Event clock:** Primary-venue auction phase and security-specific close calendar
- **Known at:** max(actual message/announcement receipt, completed model); freeze pre-public features before first eligible disclosure
- **Evidence / sources:** Observed official fields or explicitly modeled forecast — [A01]; [A13]; [A49]; [A51]; [R16]; 11_CLOSING_PRESSURE_AUCTION_SPEC.md
- **Mechanism:** Maps auction imbalance to conditional price impact for venue/symbol.
- **Confounders:** Venue/rule era; strategic cancellations; price collars; event changes; latency
- **Horizon:** Pre-public and nowcast
- **Falsifier:** Unstable coefficient/poor OOS close prediction or reversal dominates.
- **Missing data:** Insufficient same-rule matured auctions -> pooled shrinkage with uncertainty or null.
- **Owner:** Existing Data OS/source owner; adjacent auction contract; incumbent evaluation owner
- **OIF relationship:** New extension

## Off-exchange

### DPF-67 — Abnormal eligible print notional

- **Formula:** (N_window - trailing_same-time_median)/(1.4826*trailing_MAD)
- **Units:** robust standardized units
- **Event clock:** Qualified trade execution/report clocks or matched published week
- **Known at:** Actual report/publication receipt; all response/retest labels must already mature
- **Evidence / sources:** Observed participation/response; no participant intent — [I16]; [I32]; [I33]; [I34]; [I35]; [I36]; 13_OFF_EXCHANGE_ABSORPTION_SPEC.md
- **Mechanism:** Finds unusual observed participation without assigning intent.
- **Confounders:** Late prints; special conditions; internalization; market movement; share units
- **Horizon:** 5 min–session
- **Falsifier:** Effect vanishes after report conditions,market volume and volatility.
- **Missing data:** Zero MAD uses preregistered robust fallback; missing denominator -> null.
- **Owner:** engine/darkpool_signals.py; engine/darkpool_context.py; existing tape owner
- **OIF relationship:** New extension

### DPF-68 — Execution-zone concentration

- **Formula:** eligible_notional_in_frozen_zone / all_eligible_offexchange_notional_in_window
- **Units:** fraction
- **Event clock:** Qualified trade execution/report clocks or matched published week
- **Known at:** Actual report/publication receipt; all response/retest labels must already mature
- **Evidence / sources:** Observed participation/response; no participant intent — [I16]; [I32]; [I33]; [I34]; [I35]; [I36]; 13_OFF_EXCHANGE_ABSORPTION_SPEC.md
- **Mechanism:** Repeated execution near price may form a memory candidate.
- **Confounders:** Late prints; special conditions; internalization; market movement; share units
- **Horizon:** 15 min–multi-session
- **Falsifier:** No value versus matched all-tape/on-exchange volume-profile zones.
- **Missing data:** Zero/missing eligible total -> null; source coverage displayed.
- **Owner:** engine/darkpool_signals.py; engine/darkpool_context.py; existing tape owner
- **OIF relationship:** New extension

### DPF-69 — Matured residual impact response

- **Formula:** a_k*[log(M_tk+h/M_tk_minus)-beta_k*market_return_tk_to_tk+h], only tk+h<=decision
- **Units:** log return
- **Event clock:** Qualified trade execution/report clocks or matched published week
- **Known at:** Actual report/publication receipt; all response/retest labels must already mature
- **Evidence / sources:** Observed participation/response; no participant intent — [I16]; [I32]; [I33]; [I34]; [I35]; [I36]; 13_OFF_EXCHANGE_ABSORPTION_SPEC.md
- **Mechanism:** Low signed response can support an absorption hypothesis after controls.
- **Confounders:** Late prints; special conditions; internalization; market movement; share units
- **Horizon:** Next retest; not earlier than maturity
- **Falsifier:** Signal disappears with correct report/quote clocks or improved signing.
- **Missing data:** Unknown aggressor -> unsigned response; absent path -> unobservable.
- **Owner:** engine/darkpool_signals.py; engine/darkpool_context.py; existing tape owner
- **OIF relationship:** New extension

### DPF-70 — Past retest hold frequency

- **Formula:** number_matured_hold / number_observable_matured_retests; break/unresolved fractions separately
- **Units:** descriptive fraction with counts
- **Event clock:** Qualified trade execution/report clocks or matched published week
- **Known at:** Actual report/publication receipt; all response/retest labels must already mature
- **Evidence / sources:** Observed participation/response; no participant intent — [I16]; [I32]; [I33]; [I34]; [I35]; [I36]; 13_OFF_EXCHANGE_ABSORPTION_SPEC.md
- **Mechanism:** Tests whether fixed historical execution zones repeatedly reject price.
- **Confounders:** Late prints; special conditions; internalization; market movement; share units
- **Horizon:** Next qualified retest
- **Falsifier:** No future calibration gain over zone age/distance/volume controls.
- **Missing data:** No observable retests -> null; not a calibrated probability by itself.
- **Owner:** engine/darkpool_signals.py; engine/darkpool_context.py; existing tape owner
- **OIF relationship:** New extension

### DPF-71 — Published ATS structural share

- **Formula:** published_ATS_shares_same_symbol_week / matched_consolidated_shares_same_week
- **Units:** fraction
- **Event clock:** Qualified trade execution/report clocks or matched published week
- **Known at:** Actual report/publication receipt; all response/retest labels must already mature
- **Evidence / sources:** Observed participation/response; no participant intent — [I16]; [I32]; [I33]; [I34]; [I35]; [I36]; 13_OFF_EXCHANGE_ABSORPTION_SPEC.md
- **Mechanism:** Describes source-covered trading structure at its publication vintage.
- **Confounders:** Late prints; special conditions; internalization; market movement; share units
- **Horizon:** Weekly structural context
- **Falsifier:** Apparent forecast edge vanishes with actual publication lag.
- **Missing data:** Unmatched week/share units or >100% impossible ratio -> quarantine.
- **Owner:** engine/darkpool_signals.py; engine/darkpool_context.py; existing tape owner
- **OIF relationship:** Existing darkpool structural context

<!-- Report-local source links. Scope and access limits are in SOURCE_REGISTER.md. -->

[A01]: https://www.nyse.com/trade/auctions
[A07]: https://www.govinfo.gov/content/pkg/FR-2026-08-18/pdf/2026-16783.pdf
[A13]: https://listingcenter.nasdaq.com/rulebook/nasdaq/rules/nasdaq-equity-4
[A15]: https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2019-66
[A19]: https://www.amerx.com/market-on-close-portal
[A20]: https://mrtopstep.com/catalog/market-imbalance-meter
[A29]: https://datashop.cboe.com/cboe-options-open-close-volume-summary
[A30]: https://datashop.cboe.com/documents/Open_Close_10m_Spec_v1.6.pdf
[A31]: https://datashop.cboe.com/documents/Open_Close_1m_Spec_v1.5.pdf
[A33]: https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf
[A42]: https://www.dtcc.com/products-and-services/data-services/corporate-actions-reference-data/etf-portfolio-data-service
[A43]: https://dtcclearning.com/products-and-services/equities-clearing/etf-processing/etf-timeline.html
[A45]: https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/russell-reconstitution-2026-schedule
[A49]: https://www.sciencedirect.com/science/article/pii/S1386418123000502
[A51]: https://www.sciencedirect.com/science/article/pii/S0304405X21005092
[A59]: https://www.msci.com/eqb/pressreleases/archive/ir_dates.pdf
[A60]: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf
[A61]: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf
[A62]: https://indexes.nasdaq.com/docs/Methodology_NDX.pdf
[A63]: https://ir.nasdaq.com/news-releases/news-release-details/nasdaq-concludes-public-consultation-nasdaq-100-indexr
[I03]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/CONTRACTS.md
[I04]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-signal-catalog.md
[I05]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/options_intelligence/2026-10-03/options-near-expiry-spec.md
[I08]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/COMMISSION_15_HARDENED_REPORT.md
[I10]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/market_microstructure/commission15/VALIDATION_PROTOCOL.md
[I11]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/gex_engine.py
[I13]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/live_flow.py
[I14]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/thetadata.py
[I16]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/research/DARKPOOL_DESK_AUDIT_AND_UPGRADE_2026-08-05.md
[I19]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/thetadata_store.py
[I21]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/exposure_math.py
[I22]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/intraday_greeks.py
[I23]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/options_scenario_surface.py
[I25]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/live_flow_poller.py
[I31]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/flow_signing.py
[I32]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_signals.py
[I33]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/engine/darkpool_context.py
[I34]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/scripts/build_darkpool_desk.py
[I35]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_short_volume.py
[I36]: https://github.com/mastermindx-market-intelligence/macro/blob/c9631f8b2469587dec643bec94b16e77c09ef511/collectors/finra_ats_transparency.py
[IPR8451]: https://github.com/mastermindx-market-intelligence/macro/pull/8451
[R01]: https://abarbon.com/papers/gamma-fragility
[R02]: https://www.jean-sebastienfontaine.com/papers/0dte-options-volatility.pdf
[R03]: https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
[R04]: https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf
[R07]: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/on-inferring-the-direction-of-option-trades/FDA4541B57F78B2C8DCE129AFC25AAF0
[R09]: https://www.sciencedirect.com/science/article/pii/S0304405X05000577
[R10]: https://arxiv.org/abs/1011.6402
[R11]: https://arxiv.org/abs/1104.4596
[R14]: https://doi.org/10.1016/j.jbankfin.2017.05.006
[R15]: https://arxiv.org/abs/1204.0646
[R16]: https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf
[R18]: https://www.optionseducation.org/referencelibrary/faq/general-information
