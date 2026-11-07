# Dealer inventory reconstruction specification

**Status: SPEC_ONLY.** Extend existing options ingestion, chain snapshots and evaluation owners. No new store, collector or state authority is installed. All numerical research settings are proposed defaults, not empirically optimal choices.

## 1. State and target

For contract `i` and decision time `t`, retain beginning covered signed inventory `h_i,0`, intraday change `u_i,t`, reference/adjustment state `a_i,t`, and latent market regime `z_t`. Output a distribution or scenario set for `h_i,t=h_i,0+u_i,t+a_i,t`, plus cohort coverage. Net positions are in contracts; all derivative exposures carry their unit convention and contract deliverable version.

The estimation target is **aggregate signed inventory within the stated source/participant universe**, not a reconstructed integer for each individual dealer. Public trade-side prediction is a separately evaluated submodel. Store its result beside the raw observation; never overwrite the evidence with the estimate.

## 2. Admitted observation vector

Retain trade identity; source sequence and its scope; event and received/available clocks; price/quantity; venue; sale condition; cancellation/correction reference; contract identifier; quote condition; eligible bid/ask prices and sizes; quote clock; contemporaneous underlying; contract model/Greeks and input vintage; expiry/fixing/exercise/deliverable state; raw package flags; package-association evidence; prior settled OI with effective session; cumulative volume with reset identity. Later OI is a later reconciliation observation. Inferred parent/package links have their own version and known-at time.

Eligibility is explicit. Locked/crossed/one-sided/stale quotes, unsequenced events, complex legs without defensible parent allocation and unresolved busts are retained as unknown/excluded, not silently signed. Full quotes needed to repair economic ordering are not interchangeable with a trade-sampled NBBO. A later reconstructed sequence may train a historical classifier but cannot be projected back into an earlier live receipt.

## 3. Competing models

| Model | State/update | Data need | Advantage | Failure mode and admission |
|---|---|---|---|---|
| M0 unsigned structural | Prior OI with explicit call/put or symmetric allocations | Existing snapshots | Cheap baseline, transparent | Not inventory truth; retain as scenario benchmark |
| M1 deterministic signed flow | Add `−aggressor_sign×q` under an explicit dealer-counterparty scenario | Trades/prior eligible quotes | Reproducible, interpretable | Wrong participant side, packages, starting inventory; no calibrated posterior |
| M2 scenario ensemble | Vary starting allocation, dealer participation, passive-customer rates and package assignments jointly | M1 + bounded priors | Honest partial identification; first candidate | Scenario range is not probability; reject invented precise weights |
| M3 calibrated state-space filter | Factorized latent participant regime plus correlated contract increments | Representative labels or defensible partial likelihood | Pools evidence, learns changing participation | Nonidentifiable parameters remain prior-driven; likelihood audit required |
| M4 constrained overnight smoother | Fit opening/closing assignments to later OI and adjustments, preserving M3 real-time path | Complete eligible prior history + correctly aligned OI | Removes inconsistent histories; can improve future parameters | Many solutions; expired contracts and missing adjustments defeat exactness |
| M5 exchange participant benchmark | Cumulative MM buys minus sells, series history and adjustments | Licensed scoped labeled aggregates | Stronger measurement and evaluation anchor | Venue/segment coverage, interval latency, initial state, busts, missing OTC |
| M6 particle filter | Sample joint discrete package/participant states, reweight/resample | M3/M4 inputs and sufficient compute | Non-Gaussian, multimodal state | Expensive pseudo-precision; use only if M3 loses material information |

**Recommended order:** M0/M1/M2 and M5 benchmark first. M3 only after source labels or predictive evidence justify it. M4 is a subsequent training/reconciliation lane. M6 is optional and must beat M3 after resource cost. Neural trade classifiers may compete inside M3 if representative labels exist; deep learning cannot supply missing participant identity by architecture alone.

## 4. Public-flow filter

Let `a_n` be aggressor side, `d_B,d_S` participant indicators, `o_B,o_S` opening indicators and `g_n` package assignment. Define

\[
E[\delta h_n\mid O_n,z_t]=q_n\{P(d_B=1\mid O_n,z_t)-P(d_S=1\mid O_n,z_t)\}.
\]

Use separate likelihood components for aggressor, capacity, opening/closing and package structure. Do not multiply independently fitted probabilities if the variables are correlated. A joint categorical model over buyer/seller capacity combinations, constrained by package membership, is a defensible small model. In ambiguous cases the model returns a distribution including zero dealer change.

Candidate feature inputs for signing: normalized spread location, distance from eligible bid/ask, quote age, trade size relative to displayed size, nearby underlying return known at formation, venue/condition, time to expiry and sequence anomalies. First compare a transparent rule plus abstention against multinomial/logistic calibration. Calibrate on chronological labeled data, reweight only for demonstrated selection differences, report reliability by venue/moneyness/size/expiry/package. Capacity labels collected only from C1 cannot establish universal SPY/QQQ calibration.

Filtering uses only `available_at≤decision_at`; posterior smoothing uses later observations and creates a distinct research revision. Preserve both. Never replace an archived live estimate with a smoother and call its backtest prospective.

## 5. Overnight constrained optimization

For nonexpiring contract `i`, introduce nonnegative assignment quantities `x_n,oo`, `x_n,oc`, `x_n,co`, `x_n,cc` summing to each eligible trade quantity. Minimize

\[
\sum_{n,k}x_{n,k}\log\frac{x_{n,k}}{q_n\pi_{n,k}}
+\lambda\,\mathrm{penalty}(A_i,\text{missing coverage})
\]

subject to `Σ_n(x_oo−x_cc)+A_i=ΔOI_i`, nonnegative long/short capacity, package-ratio restrictions that are actually evidenced, and source correction constraints. Use bounded residual slack with a published reason where exact data are unavailable. Zero prior mass cannot be repaired by an optimizer without an explicit model revision. Integer assignments matter when solving exact small audit examples; fractional quantities are expectations in the scalable approximation.

Opening/closing assignments alone do not identify dealer inventory. To bound dealer hedge risk, introduce joint assignments `y_n,k,dB,dS` whose marginals equal `x_n,k`, with dealer-capacity indicators `dB,dS∈{0,1}` and signed change `Σ_k,dB,dS y_n,k,dB,dS(dB−dS)`. Link only capacity categories actually observed in participant data; otherwise retain all feasible capacity cases and their explicit priors. Package/long-short constraints must use this joint state. Next OI constrains opening/closing marginals, not an invented participant identity.

Run two outputs: feasible min/max dealer hedge sensitivities across these joint assignments, and a regularized representative solution. Neither is a uniquely observed history. For same-day expirations, handle lapse/exercise extinguishment explicitly and report OI's weak identification; do not pretend the zero end state labels each trade.

Evaluate whether parameters learned from sessions through D improve filtering on D+1 and later. Comparison against the evaluated day's smoothed path is a measurement study, not a live trading simulation.

## 6. Labeled aggregate benchmark

For published cumulative market-maker contract volumes `MMBuy(t)` and `MMSell(t)`, session change is `MMBuy(t)−MMSell(t)`. Interval change is a difference between compatible cumulative snapshots. Source `qty` can mean trade count while `vol` means contract count; use actual versioned schema. Do not sum cumulative snapshots or double signed two-sided execution records.

Carry the last released interval forward with its original clock and staleness. Missing intervals remain gaps. A decrease in cumulative fields may be a cancellation or reset; it is not automatically new selling. C1 regular/global/curb sessions require exact segment and trading-date reconciliation. Near-expiry contracts with complete series-inception coverage can have an anchored starting inventory; prehistory, transfers and non-trade adjustments remain explicit uncertainty.

M5 is a stronger scoped benchmark, not omniscient ground truth. Retain original published vintages and subsequent corrected vintages; a final historical file without original releases yields reconstructed research, not captured PIT proof.

## 7. Numerical and statistical acceptance

Required conservation witnesses: dealer–dealer cancellation; customer–customer zero; buying-to-close increases signed inventory; seller-to-open does not by itself increase OI; split fills and duplicate reports; cumulative snapshot differencing; corrections changing a prior interval; contract exercise/expiry; adjusted multipliers; session resets; correlated spread legs; incomplete series history; known-at delayed OI.

Measurement metrics: signed-change MAE in contracts; gamma/delta-weighted error; sign reliability outside a preregistered near-zero band; posterior interval coverage where labeled inventory is sufficiently known; calibration/coverage of participant categories; unknown rate weighted by contracts and delta; error stratified by high-impact and final-hour observations. Unweighted trade accuracy can hide the largest hedge errors.

Predictive admission is separate: M2/M3/M5 must add value to the frozen incumbent plus liquidity model under the validation masterplan. If adequate coverage and power rule out the preregistered useful gain from the scoped labeled benchmark, stop the corresponding complex reconstruction even if measurement accuracy improves. An imprecise null is inconclusive, and a limited C1 book does not bound every cross-product portfolio.

## 8. Output contract and consumer semantics

Proposed additive record: `inventory_model_id`, `model_version`, `scope`, `source_revision_ids`, `contract_reference_revision`, `anchor_state`, `h_mean` if a model expectation exists, `scenario_bounds`, `posterior_quantiles` only if defined, `prior_sensitivity`, `participant_coverage`, `eligible_volume_coverage`, `history_start`, `last_available_at`, `gap_ranges`, `adjustment_state`, `correction_lineage`, `evidence_class`, `null_reason`.

Source quality, inventory-model uncertainty and forecast calibration are three independent axes. Avoid a composite 0–100 confidence value. Human displays and machine consumers must expose the same source and inference fields. Existing observation, scenario and candidate-policy authority flags remain authoritative.
