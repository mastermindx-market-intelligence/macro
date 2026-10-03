# Data, analytical and candidate contracts

**Status:** proposed additive research contracts for incumbent owners. These are specifications, not schemas installed by this PR. Current production schemas and authority flags remain authoritative until their owners review a compatible change. Source evidence: [Macro census](options-macro-census.md), [Terminal census](options-terminal-census.md), [Theta audit](options-thetadata.md), [literature ledger](options-literature.md).

**Reviewed reference implementations:** [B1/B2 mechanics](options-reference-kernels.md) now supply direct current-gamma classification, explicit sampled root features, signed strike sensitivity and complete/partial endpoint rehedging. [B3/B5 source admission](SOURCE_ADMISSION_SPEC.md) supplies measured/proxy/unknown denominators and source-to-consumer clock/identity fixtures with an [independent checker](source-admission-independent-check.py). [P3 positive variance](P3_REFERENCE_EVALUATOR.md) supplies the one-feature QLIKE link, numerical refusals and minimum training-chronology checks. [Principal decisions](PRINCIPAL_DECISIONS_20261003.md) accept these isolated uses only. The source reference's `captured_pit_eligible` is a synthetic-contract check, while `source_certified_accepted` remains false; no local pass authenticates real capture or extends the strict candidate schema.

## 1. One economic observation, several clocks

Use the current event/artifact/candidate identities. A research transformation must reference its input identity, source revision and producer version; root plus timestamp is not a sufficient join key. Distinguish the following concepts even when a source cannot supply all of them.

| Concept | Definition | If absent |
|---|---|---|
| Exchange event time | When a trade/quote event occurred according to the source | Unknown; do not replace with a fetch timestamp |
| Publication/sequence context | Feed publication ordering, exchange/channel scope and precision | Equal-time order is ambiguous; no fabricated sub-millisecond ordering |
| Received time | When the existing collector actually received the bytes | Historical reconstruction cannot claim original live receipt |
| Effective time/session | Economic reference of a state, such as previous-session closing OI | Cannot call it current inventory |
| Available time | Earliest evidenced time this exact revision was available to the consuming system | Strict PIT eligibility fails; a separately labelled reconstruction may remain researchable |
| Computed time | When the current transform ran | Never substitutes for source freshness |
| Candidate decision time | When the existing candidate decision consumed evidence | Must follow input availability; distinct from a producer's own event-classification decision timestamp |
| Label maturity time | When a complete outcome can first be evaluated | Immature outcome remains pending, not zero or a failure |

For a candidate decision at t, every required input revision and the feature artifact itself must be available by t. Input timestamps alone do not prove that a backfilled feature existed then. Preserve an artifact revision/publication receipt and the consumer's receipt/admission evidence. Under synchronized clocks, the required chain is max input availability <= computation completion <= artifact availability <= consumer receipt <= candidate decision. Clock precision/offset uncertainty must be recorded and ambiguous order rejected or explicitly reconstructed. Preserve existing producer fields such as observed/decision/available timestamps; do not reinterpret a producer's decision clock as the later candidate decision. Compute freshness from source times and trading calendars, not solely artifact build time or HTTP response time.

Two research modes are explicit. **Captured PIT** uses retained receipt/publication evidence. **Reconstructed history** uses archived event times and a declared latency/revision assumption; its unknown original availability remains a limitation. It may falsify a hypothesis, but it does not alone establish historical live tradability. The October 2 retrospective remains in its stated evidence class.

Corrections retain the original reference, replacement/cancel relationship and later availability. Replay decisions from the revision visible then. Evaluate outcomes against an explicit label-data revision. Do not silently rewrite an old decision because today's historical export changed. Reuse the existing publication/learning/WAL custody mechanisms.

## 2. Contract economics and reference data

Canonical identity requires root, option symbol, expiry, strike and right plus the current source's exact identity/version. Economic interpretation additionally requires currency, quote units, multiplier, deliverable, exercise style and settlement type. Adjusted deliverables cannot be valued by blindly multiplying every price or delta by 100.

Maintain separate last tradable time, payoff-fixing time or rule/status, exercise cutoff and cash/share delivery date. A payment date is not the model expiry. Product calendars include holidays and half days. For AM-SPX, the fixing rule depends on constituent opening prices; an invented universal 09:30 or 16:00 instant is inadmissible. These requirements follow the official exchange/clearing references in the Theta audit.

Reference revisions must be available at the decision. A final daily list of contracts or a subsequently adjusted symbol map cannot establish that each contract was discoverable earlier. Corporate actions, missing contracts, delistings and expired identities remain auditable.

## 3. Trades, quotes, signing and packages

Preserve price, size, exchange, source sequence and scope, trade condition, quote conditions, bid/ask prices and sizes, quote/event clocks and correction linkage. Theta's current trade-quote methods expose more than a stripped price/size row; the ingestion owner should preserve those fields already retained and close specific loss points.

For an eligible print p with prior bid b and ask a, report quote location separately from aggressor inference. The midpoint rule can classify above/below midpoint subject to the registered convention, while at-bid/at-ask shares answer a different descriptive question. Midpoint, crossed/locked, one-sided, stale, zero-price/size, auction, complex and sequencing-ambiguous cases retain reasons. Do not force a direction merely to increase coverage.

Use only evidence available before the consumer decision. A full trade stream may deliver the next two quotes; those can support later markouts but cannot sign the preceding trade as if already known. Millisecond ties require a documented sequence rule or an unknown state. A tick-rule fallback is separately tagged and evaluated.

Let a_i in {-1,+1} be a classified buy/sell aggressor sign and U be the unclassified set. Software may store zero for an unknown contribution for summation, but must retain U and coverage; zero is not an observed neutral transaction. A calibrated sign probability is nullable until validated against actual labels. Historical classifier accuracy from a paper is not a feed-specific calibration.

Complex-order indicators and matching legs support a package hypothesis. Group only through the existing package owner, with source IDs, timing tolerance, size ratios, exchange/condition evidence and alternative interpretations. A same-ticker time cluster, a sweep or matching premium does not prove a strategy, customer identity or opening position. Unsigned OI changes cannot allocate opening/closing intent to individual earlier prints.

## 4. Core analytical units

Notation: q_i is a nonnegative observed contract count; m_i is the contract's appropriate quote multiplier; p_i and model V are option value in currency per quoted unit; S is underlying price; Delta is the signed long-option derivative dV/dS (negative for ordinary puts); Gamma=dDelta/dS; Vega=dV/dsigma and Vanna=dDelta/dsigma for decimal annualized sigma; Charm_cal=dDelta/dcalendar_year=-dDelta/dremaining_year under the specified frozen inputs. RVar denotes realized variance and RVol denotes realized volatility. Nonstandard deliverables require an appropriate valuation transform rather than assuming scalar m alone solves them.

| Quantity | Formula / contract | Meaning and boundary |
|---|---|---|
| Gross premium | sum q_i m_i p_i | Traded option consideration; no direction |
| Signed premium | sum classified a_i q_i m_i p_i | Inferred initiator premium; unknown coverage separate |
| Signed dollar delta | sum classified a_i q_i m_i Delta_i S_i | Signed underlying delta-equivalent notional of classified trades |
| Signed dollar vega per vol point | .01 sum a_i q_i m_i Vega_i | Change in option value for +1 percentage point IV, at frozen other inputs |
| NPP elasticity-weighted demand benchmark | sum signed non-market-maker contracts × Vega_i / p_i, using the paper's eligible maturities and volatility estimate | Original classified-volume construction; public aggressor proxy is separately named |
| Gamma-driven delta-notional sensitivity | sum n_i m_i Gamma_i S² × .01 | Change in option delta, converted to notional at base spot, per +1% move for stated inventory n_i; excludes revaluation of existing delta; not a bullish score |
| Vanna portfolio delta-notional sensitivity | sum n_i m_i Vanna_i S × .01 | Portfolio delta-notional change for +1 vol point; delta-neutral hedge sensitivity has the opposite sign |
| Charm portfolio delta-notional sensitivity per day | sum n_i m_i Charm_cal_i S / year_days | Portfolio delta change from calendar decay; hedge sensitivity has the opposite sign; frozen inputs/day count explicit |
| Variance gap | IV_H² - E_t[RVar_H] | Both annualized variance on compatible horizon/day-count; physical-variance forecast uses only information known at t |

Rates and IV are canonical decimal units; displays can use percentage points with an explicit conversion. Each differentiated variable supplies its own scale factor. Distinguish a volatility gap IV-RVol from a variance gap IV²-RVar; if a comparable RVol is defined as sqrt(RVar), the latter equals IV²-RVol². Portfolio delta sensitivities have the opposite sign to the underlying hedge-share response. Gamma notional is a component: the full derivative of S×portfolio Delta with respect to S is portfolio Delta + S×portfolio Gamma. The GEX expression intentionally excludes the existing-delta revaluation term. Do not sum exposures with different units or horizons into a probability.

The existing legacy minute-bar `options_flow` construction and current per-print `live_flow` are not interchangeable. `sign(sum signed contracts) × gross premium` is not generally `sum signed print premium`. Likewise a categorical .80/.20/.50 chain proxy is not measured at-ask share. Preserve the source-family label and avoid aliasing those fields downstream.

## 5. Greeks and scenario engine

Record pricing model/version, mark type, IV inversion method, rate/dividend inputs and as-of times, underlying feed/price/time, option quote time, day count, economic fixing rule and remaining time. Include solver status, convergence and approximation flags. A row may contain an observed quote and an unavailable Greek; do not coerce the latter to zero.

For a fixed assumed inventory n_i on one hedge underlying and in one currency, define underlying hedge shares B(S,sigma,t)=-sum n_i m_i Delta_i(S,sigma,t). Cross-underlying or currency aggregation requires a separately specified vector hedge/FX convention. Under a specified scenario, hedge trade shares are B*−B0 and hedge trade notional H=S*×(B*−B0), positive for buying underlying. The corresponding cash-account change is −H under this one-step notional convention; path execution, funding and previous rebalancing are not included. This is a scenario quantity, not observed dealer demand.

Reprice the entire book at the hypothetical state. Declare surface dynamics (sticky strike, sticky delta or another registered rule), time path, exercise behavior, dividends and positions expiring during the step. Compare against the local approximation; show the error and suppress conclusions when convergence or coverage is inadequate. A hedge response can be procyclical or countercyclical under those assumptions; market-price amplification/dampening additionally requires an impact/liquidity model or empirical identification. Do not integrate snapshot buckets over contract strikes as if strike were the whole book's hypothetical spot axis.

Report inventory convention and sensitivity. Unsigned OI, call+/put−, alternative participant allocations and classified inventory are different evidence classes. Preserve beginning-of-day inventory assumptions separately from new flow. A number labelled confidence must not merely be absolute call/put imbalance. Report scenario dispersion and the assumptions generating it.

A gamma profile can have multiple roots and either crossing orientation. Determine the current regime from net gamma evaluated at actual spot under the chosen inventory, with a numerical near-zero band. Retain all qualified crossings and their direction; the nearest root alone does not determine the sign. Do not extrapolate beyond the evaluated domain without an explicit state.

The [TTE study](options-theta-tte-study.py) and [mechanics witness](options-mechanics-witness.md) are independent mathematical references. They do not prove vendor behavior, actual positions or predictive value. Numerical acceptance includes price parity, finite differences, sign/unit checks, grid/step convergence, final-hour discontinuities and missing-data cases.

## 6. Feature record and quality decomposition

Add research metadata to existing feature/evidence records, using current IDs rather than introducing another registry or store. The conceptual minimum is:

```yaml
feature_id: catalogue identifier and version
evidence_refs: existing source/event/package/artifact identities
source_revision_refs: exact input revisions
artifact_revision_ref: exact feature output revision
candidate_decision_at: consumer clock when applicable
max_input_available_at: evidenced upper bound
computed_at: transformation completion time
artifact_available_at: publication/materialization receipt time
consumer_received_at: consumer receipt/admission evidence
source_effective_session: where relevant
unit: explicit dimension and scale
horizon: trading/calendar convention and length
value: null or qualified numeric value
evidence_class: observed | inferred | scenario | reconstructed
availability_mode: captured_pit | reconstructed_assumption | unknown
quality:
  source_count: integer or null
  eligible_count: integer or null
  valid_count: integer or null
  premium_coverage: number or null
  quote_age_summary: statistics or null
  completeness: complete | partial | unknown
  reasons: explicit codes
model_ref: formula/model version and training receipt if fitted
uncertainty_ref: calibration or scenario definition, otherwise null
authority: inherited incumbent flags
```

Source quality, inference uncertainty and predictive uncertainty are separate. Source quality describes clocks, gaps, conditions and coverage. Inference uncertainty describes signing/package/model assumptions. Predictive uncertainty describes out-of-time forecast performance. A highly complete observation can have no predictive information; a correct Greek can use an uncertain position assumption.

Coverage requires a denominator with meaning. Report valid/source counts, valid/source premium, root/contract/session completeness and reason distributions. If the true market universe is unknown, describe coverage of received observations rather than claiming market-wide coverage. A partial exposure sum remains partial even when its arithmetic is finite.

## 7. Proposed Prophet extension

The current candidate schema/publisher remains the authority. At candidate PR #8310 head `a15ba9ae77826bf6a1d6fcb40022b6816b705e43`, `contracts/options/options.alpha_candidate_feed.v1.schema.json` has `additionalProperties: false` at both feed and candidate. There is no existing extension slot. Adding `options_context` therefore requires an explicit incumbent schema/version and consumer compatibility change; it cannot be inserted into the current payload as an allegedly backward-compatible extra field. Names below specify proposed meaning, not a replacement serialization contract.

Reuse the current formation/current revision distinction and clocks `source_formed_at`, `first_observed_at`, `decision_at`, `available_at`, `published_at`. Preserve all 15 false authority fields: `may_originate`, `may_rank`, `may_score`, `may_gate`, `may_size`, `may_issue`, `may_trade`, `may_publish_pick`, `may_train_prophet`, `may_feed_neural_web`, `may_select`, `may_escalate`, `may_compute_option_pnl`, `may_infer_bullish_bearish_probability`, `may_create_tactical_event`. The episode/campaign and exact-option policy contracts have different field sets; do not assume one interchangeable authority dictionary.

```yaml
options_context:
  schema_version: proposed research version
  evidence_refs: existing feature and source references
  as_of: qualified consumer time
  horizon: same defined target horizon as candidate comparison
  observational_state: qualified | partial | unavailable | stale
  directional_support:
    estimate: null
    baseline_estimate: null
    incremental_change: null
    target_definition: null
    calibration_ref: null
  counterevidence: source-linked observations with scope and horizon
  volatility_and_tail: separately labelled priced/forecast risk state
  hedge_scenarios: scenario references and inventory assumptions
  expression_quality: existing exact-contract review references
  uncertainty: source, inference and predictive components
  options_support_score: null
  authority: inherit current candidate authority without escalation
```

If a future support score is admitted, define it as a display transform of one calibrated target, for example 100×P(candidate achieves a specified outcome by H), and expose the same baseline probability and incremental difference. Do not call a heuristic weighted sum a probability. Calibration and policy approval are dependencies; every predictive field remains null before them.

Pre-admission evidence can support investigation, risk description or expression feasibility. Data-quality failure may withhold an options observation. Exact-contract expiry, invalid deliverable or unusable quote may block that expression. Neither is an unvalidated veto on the underlying candidate. A predictive veto requires a preregistered decision-loss comparison, false-veto analysis and independent policy approval through the current owner.

After admission, compare a new qualified feature snapshot with the immutable admission snapshot. Use current monitoring/outcome identities, not ticker-only joins. Track persistence, reversal, risk change, approaching expiry, catalyst changes, expression fit and data staleness. A correction triggers a source-linked revision, not a fabricated new trade thesis. Cooldowns and alert deduplication use the incumbent mechanism; statistical repeated testing remains a separate issue.

## 8. Exact-option outcome contract

Freeze contract selection and intended entry rule using information available at decision time. Record contract/deliverable, side/quantity, entry time and quote, latency convention, fees, spread/impact assumptions, financing/borrow when applicable, and exercise/expiry rule. Exit logic and horizon are registered before examining future quotes.

Retain underlying return, option mark-to-market and assumed executable P&L as separate outcomes. A stock return is not an option profit; expiry payoff is not a pre-expiry mark; a midpoint is not an assured fill. Multi-leg economics require coordinated package execution assumptions and total fees. Do not independently choose favorable leg prices after the fact.

Missing entry, absent exit, stale/crossed quote, quote outside the requested clock, partial fill and unpriced exercise are explicit outcome states. They are neither a zero return nor a dropped row without a coverage report. Evaluate selection and execution exclusions alongside performance. Actual execution calibration requires observed fill evidence; historical NBBO supports a bounded simulation, not a promise of execution.

## 9. Terminal acceptance behavior

Every consequential card/chart uses exact root, contract, session, source revision and horizon. Preserve distinct source and artifact clocks. A retained stale frame can remain visible with a stale state; a transport connection cannot make it fresh. A root/session/revision change cannot admit the preceding context's response. Historical observed surfaces and hypothetical scenario matrices label their axes and calculation mode distinctly.

Unknown cells render as unknown. Adjacent cumulative differences use elapsed time before being labelled per-minute; “since open” requires an actual qualified open anchor. Partial Greeks are visible as partial. Trade location, categorical proxy, heuristic attention tier, calibrated forecast and inventory scenario use distinct field names and explanations. Source-level quality remains visible in exports and drilldowns, not just tooltips.

Use the existing Flow/Exposure/Volatility/Prophet/Issue Desk/Payoff/Plan workspaces and alert machinery. The existing #592/#608/#645/#686/#723/#768/#780/#781/#783 carriers contain relevant work and must be reconciled before any new implementation packet.
