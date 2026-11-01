# 06 — Economic lows, highs and causal labels

**Status:** research specification for later preregistration. No target in this file has been fitted or calibrated in this commission. Parameter defaults below are proposed benchmark choices, not accepted trading rules.

## 1. Objects and information set

Let t be the actual decision cutoff, D the versioned economic day, s the active segment, and H one of 5, 15, 30, 60 or 120 minutes, segment end or economic-day end. Let F_t contain only observations usable by t under chapter 04. Use canonical security identity and a source/session qualification mask. An empty or interrupted future quote path is not a successful no-new-low label.

Maintain both a fixed reference low L₀ observed by t and a future finalized low L*. These answer different questions: whether the **current reference** survives, and whether buying at t is close to the ultimately available best price. A reference cannot drift downward after the prediction and still count as having survived.

Separate feature cutoff, forecast-window start, actual consumer availability and order-arrival time. At canonical policy landmark t₀, let r be the actual availability time of the decision inputs and prediction required by that policy, and λ_action the declared remaining action/routing latency. Earliest permitted order arrival is u₀=max(t₀,r)+λ_action. A fixed wait of w uses max(t₀+w,r)+λ_action; an adaptive rule additionally respects its actual causal confirmation and availability times. Keep common terminal E=t₀+H. Delivery delay never restarts the horizon. Use A_q(u₀) for immediate acquisition and [u₀,E] for its forward-available benchmark. Any shorthand t₀+latency below denotes the full delay from the landmark, not routing latency alone. Offline delivery assumptions are simulated, not prospective receipts. If u₀>E, apply the frozen late/no-entry disposition.

## 2. Price bases

| Low / high definition | Precise basis | Legitimate use and limitation |
|---|---|---|
| Raw trade low/high | Min/max eligible unadjusted reported executions; preserve conditions and revisions | Descriptive tape extreme; may be odd-lot, delayed, broken or unreachable |
| NBBO bid low | Minimum qualified consolidated best bid | Pressure/liquidation context; not a buyer's entry price |
| Midpoint low/high | Min/max `(bid+ask)/2` for an eligible simultaneous quote | Cleaner price-path research; midpoint fill is not assumed |
| Buyer-executable low | Minimum simulated marketable acquisition cost for benchmark size q at reachable offers, with declared latency and fees | Quote-supported opportunity bound, still distinct from observed broker fills |
| Liquidity-supported low/high | An executable-side extreme with required valid size, duration/event support and no unobserved gap | Reduces fleeting or tiny-print artifacts; support threshold is preregistered |
| Tactical local low/high | Eligible extreme in a trailing fixed window, evaluated using only F_t | Available feature/reference; no centered pivot before confirmation |
| Segment low/high | Extreme within the explicit current segment | Segment boundaries and incomplete-segment status are retained |
| Economic-day low/high | Extreme within the versioned whole economic cycle D | Final label is hindsight by design; never a live feature |
| Seller-executable high | Maximum simulated liquidation proceeds at reachable bids, net of fees/latency | Long-position exit research; the ask high is not realizable sale value |

For first research benchmarks propose q = 100 shares, with a separately registered fixed-notional sensitivity. These are standardized measurement orders, not portfolio sizing instructions. If displayed eligible quantity is insufficient, the L1-only label is unavailable at q; do not invent deeper liquidity. L2 may later estimate a sweep across levels with venue accessibility and participation constraints. Passive limit fills require their own queue model; touching a limit is not a fill.

Define gross reachable per-share ask a_q(u) and bid b_q(u) at **arrival/fill time u** only when source scope, conditions, stream continuity, sizes, market status and route assumptions pass. Define all-in acquisition cash A_q(u)=q×a_q(u)+entry fees and net liquidation cash B_q(u)=q×b_q(u)−exit fees. Return ratios use B_q/A_q−1; per-share low distances use A_q/q. Fees are charged once. Define side-specific fee conventions so bid-low pressure references remain gross bids while executable acquisition/liquidation targets are explicitly net.

Separate causal support from ex-post execution support. A duration-qualified quote first becomes a usable observation after the duration has elapsed **and its support confirmation is known**. Proposed duration is max(declared latency,250ms). Store `support_completed_at` and `support_known_at`; neither an observed low nor a prediction may be backdated to the quote's earlier start. Forward persistence can grade an already-defined simulated action or hindsight opportunity, but cannot select an action at the earlier time. A quote surviving in recorded data is not guaranteed to survive a real order. Preserve `SIMULATED_QUOTE_SUPPORTED` versus `OBSERVED_FILL`. Equivalent native-event support is a separately registered variant, not a discretionary fallback.

## 3. Materiality and targets

Freeze a material new-low threshold δ_t and near-low tolerance ε_t at decision time. Proposed default δ_t = max(one price tick, one contemporaneous qualified spread, 0.10 × trailing causal 30-minute realized range in price units). Proposed ε_t = max(two ticks, estimated round-trip friction, 0.10 × that same range). Use a small prespecified sensitivity grid, and log every examined value. Sparse/missing inputs make a threshold unavailable or invoke a separately registered simpler baseline; do not estimate volatility from the future day.

### Initial target locked for proposed R3 registration

`PRICE_L30M_30M_v1` uses unadjusted, condition-qualified completed 1-minute OHLC bars in one contemporaneous economic basis. Its offline as-of landmarks t are exact minute boundaries on a five-minute grid. Let a_t be the end of the latest completed bar **already known by t**, not necessarily the bar ending at t. L₀ is the minimum low over 30 contiguous complete RTH minutes ending at a_t; range_t is max(high)−min(low) over that same window. Record a_t and information age; proposed maximum t−a_t is120seconds. δ_t=max(effective price tick,0.10×range_t), with **no spread input**. Require a_t−30m≥actual_open and t+30m≤actual_close. Missing required bars make the landmark unavailable; no carry or lookback shortening occurs inside this label. The outcome uses only intervals starting at or after t and ending by t+30m, so no pre-cutoff part of a minute bar enters it. Opening-drive, closing-transition and overnight variants are separate later labels.

`PRICE_L30M_30M_v1` retains its R3 offline as-of cutoff semantics. Its grid cutoff is not a historical publication receipt or evidence that a decision could have been delivered at that instant. The first historical source mode is `RECONSTRUCTED_CAUSAL` or weaker as warranted, never assumed PIT. A live off-grid decision requires finer ordered data/interval-censoring or a separately named bar-aligned target; do not silently shift its first outcome bar.

For R10, preregister a separate prospective grid variant with forecast start g, positive fixed lead L and input cutoff c=g−L<g. The proposed first operational variant is `PRICE_L30M_30M_LEAD30S_v1`, with L=30seconds, subject to owner latency qualification before registration. Reserve g and freeze L before examining that window. Every feature dependency must be known by c. Define a_c as the end of the latest completed bar known by c; compute the reference low, range and threshold from the prescribed30 contiguous RTH minutes ending at a_c. Apply the information-age gate to g−a_c≤120seconds; require a_c−30m≥actual_open and g+30m≤actual_close. Record feature cutoff and reference age.

The immutable prediction must be durably captured at p<g. A claim that a consumer had it at window start additionally requires a consumer-availability receipt before g. The outcome remains the predeclared complete minute intervals from g through g+30m. Neither late data nor slow inference moves the window; missed deadlines remain late/missed rows in the intended prediction denominator. Do not rescan at g, rewrite the reference with information learned after c or backdate capture. Later observations may produce separately timestamped invalidation/replacement events while the original prediction remains immutable. This variant conditions on F_c, not F_g: it needs matching historical construction, its own qualification/calibration and later-wave trial accounting. Example timing, not a current performance claim: g=10:00, c=09:59:30, qualifying bar end09:59 and capture09:59:45.

`QUOTE_BID_L30M_30M_v1` is a separate proposed R5 target: L₀ is the lowest gross bid with causal support known within the prior 30 RTH minutes, and materiality uses the qualified spread-aware rule above. Buyer-executable near-low is a separate ask/cost target. No observation silently switches between price-only, bid, midpoint and acquisition-cost labels. Segment and economic-day reference variants receive distinct IDs and independent admission.

### A. Observed location

`observed_low_distance = (known_offer_t − observed_eligible_low_t) / known_offer_t` is descriptive. It answers “how far above the low already seen?” It cannot establish that today's final low has occurred. Retain both raw-print and supported-quote distances when available; their disagreement is useful evidence about execution quality.

### B. Near-final-low probability

For whole-day localization, Y_near,D(t)=1 when per-share all-in acquisition cost A_q(t+latency)/q is within ε_t of the finalized minimum per-share buyer-executable acquisition cost over D. For a waiting decision, define distinct Y_near,future(t,H) against the minimum attainable per-share acquisition cost at arrival times u in [t+latency,E], E=t+H. An opportunity that disappears before earliest arrival is excluded from the forward-available benchmark. Earlier missed lows affect the whole-day target but not the forward-available target. Name both explicitly; never swap them after looking at results.

The acquisition cost at t+latency is an **outcome of the simulated action**, not a feature visible at t. Store the last known offer estimate separately. Out-of-scope liquidity excluded by the frozen target definition differs from missing eligible liquidity. Require coverage over the whole relevant interval, not merely around the observed minimum. Missing eligible intervals produce censoring or bounds; they are never assumed not to contain a better price.

### C. Low survival

Let τ_N=inf{u>t: eligible price at u is below fixed L₀−δ_t}; let T_N=τ_N−t be elapsed duration. Predict S_N(H|F_t)=P(T_N>H|F_t). Convert segment/day-end timestamps to durations consistently. Report survival at each horizon with reference basis and censoring status. These probabilities must be nonincreasing in H for a compatible reference/coverage regime. A new reference after a new low requires a new prediction snapshot, while Radar retains its own episode identity rules.

### D. Competing first events

Define T_R as the first **causally confirmed** reclaim: price closes above a reference fixed by t or by an explicitly admitted subsequent causal rule, then satisfies the preregistered hold requirement. Proposed first baseline: two completed 1-minute intervals above the fixed reclaim level with no material reference-low breach. The confirmation timestamp is the second interval's known time, never the first bar's start. Event thresholds and clocks belong to the label version.

Estimate cumulative incidence for first `NEW_MATERIAL_LOW` and first `CONFIRMED_RECLAIM`. Administrative `EXPIRY` is deterministic no-event mass remaining at the declared endpoint, not a separately learned stochastic failure hazard. It differs from source-loss censoring. Use existing minute-resolution work for order ambiguity: if a bar reaches both barriers, ordered tick data can resolve it; otherwise report interval-censored/ambiguous, conservative bounds or a registered exclusion with its coverage cost. [R28; PR7275]

**Critical distinction:** P(new low before reclaim) is not P(any new low by H). A reclaim may happen first and then fail to a later low. Use a separate all-path survival target, or an explicit multistate model that continues after reclaim. Do not identify `1 − first-new-low incidence` with low survival.

### E. Path distributions

For a simulated long entry filled at u_entry with total all-in cash cost C=A_q(u_entry), define executable MAE=min[B_q(u)/C−1] and MFE=max[B_q(u)/C−1] over eligible liquidation arrival times u in [u_entry,E]. B_q already includes exit fees; do not subtract them again. No pre-entry price enters fill-conditioned MAE/MFE. Include immediate spread loss; do not clip negative MFE into a free break-even result. Also retain midpoint/bar path targets as different evidence classes.

Predict 10th/50th/90th quantiles, time to first meaningful low, time to reclaim, time to target and probability of meaningful loss before meaningful gain. An unconditional p-quantile lies beyond the observed horizon when P(T≤H)<p; the half-event rule applies only to the median. Display “not reached within window.” A time quantile conditional on eventual occurrence is a different labelled estimand and must be accompanied by event probability. Separate incidence, censoring, coverage and model uncertainty.

### F. Entry economics

At each canonical candidate landmark t₀, evaluate buy-now, fixed wait 5/15 minutes, reclaim wait, pullback limit and no-entry against the **same initial candidate cohort/state, capital budget and terminal time E=t₀+H**. Each adaptive policy may use F_u at its subsequent decision u, never future information early; reclaim waiting is not frozen to F_t₀ forever. An end-of-economic-day experiment is a separate target. Late policies get less holding time; never give each a fresh H after entry in the primary comparison.

Use net terminal wealth or implementation shortfall as the primary economic ruler. A no-fill policy retains cash through E; its zero exposure is reported together with missed favorable moves and coverage. Do not compare only episodes where waiting eventually filled. Score partial fills and unfilled remainder under a declared terminal convention. Do not add a separate missed-opportunity penalty to a wealth comparison that already charges that opportunity twice; report regret as a separate diagnostic or preregister a specific non-wealth utility.

For the initial standardized policy experiment, target at most 100 shares and set each candidate's common initial capital K₀=100×the qualified known offer at t₀ plus the frozen entry-fee allowance. All policies use that same K₀; quantity is capped by 100, available cash, qualified displayed liquidity and the declared participation limit. A higher delayed price can therefore produce fewer shares; a lower price leaves more cash after 100 shares. No borrowing is assumed. Let W_π(u)=remaining cash plus the net qualified liquidation value of actual holdings. Charge entry fees to cash on entry; include hypothetical exit fees in the mark, and charge them only once on actual liquidation. Cash earns zero over this short benchmark window. Define all-candidate policy adverse excursion A_π=min_{u∈[t₀,E]}(W_π(u)/K₀−1), and terminal return R_π=W_π(E)/K₀−1. No-entry has A=R=0. Partial fills retain cash in both metrics. Fill-conditioned MAE is a separate diagnostic, never the all-candidate promotion denominator. Report time invested and fill/coverage so exposure reduction is not mislabeled superior localization. These overlapping candidate studies do not model a jointly capital-constrained portfolio.

Example, purely illustrative: all 100 candidates start at the same cutoff. Waiting can lower mean MAE among its 40 fills yet lose on common-terminal wealth because 35 omitted names rally and 25 remain flat. That is a risk/coverage tradeoff, not evidence of better entry. Conversely, slightly lower mean return can be worthwhile under a declared adverse-tail objective. The utility coefficient is a policy preference to ratify before outcomes, not a fitted alpha parameter.

## 4. Outcome table and separation

Each outcome row uses typed subject lineage: a market census row has security/day/landmark; a Radar row additionally references its native episode/species; a Prophet candidate row references native B3 and an accepted relation if Radar context is used. These fields are nullable by subject type; do not invent a Radar episode for a census observation or join owner IDs by ticker. Model rows also reference prediction ID. All rows carry clock/label version, source-vintage IDs, first eligible decision time, reference prices, q/latency/cost convention, event times, horizon, resolved/ambiguous/censored status, price- and execution-path metrics, policy results and finalization/revision times.

Predictions are appended through incumbent evidence owners **before** outcomes are known. Outcome writers cannot modify predictions or add hindsight annotations to a live snapshot. Nightly grading remains with the current evidence pipeline unless that owner explicitly accepts a new intraday resolution contract. Existing daily forward-next-bar rules cannot simply be applied to an intraday last-known quote.

## 5. Minimum label acceptance

Require synthetic boundary cases and a manually adjudicated real-source sample spanning RTH, overnight, early close, halt, bad/late/broken print, wide spread, insufficient size, unavailable quote, both-barrier ambiguity, new low after reclaim, duration support not yet known, and a missed-move waiting policy. Every case must have raw source lineage and a written expected label. An observed breach resolves the any-breach binary target even if a later gap occurs; an event-free prefix followed by source loss cannot resolve survival beyond the gap. First-event ordering remains unresolved if a gap could hide an earlier competing event. Coverage failures stay in intended-cohort accounting with the censoring/bounds rules of chapter09. A price-low census may proceed without full quotes, but cannot satisfy the executable-label gate.
