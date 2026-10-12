# TTI R1-B: exhaustion, continuation and usable-entry contract

Status: design-only, no trial registration or empirical outcome computation. This extends the approved program design, not any live signal or lifecycle authority. Existing Radar owns events, Setup Species/Evaluation own scientific admission, and Terminal consumes evidence. It is independent of unfinished Executive activation.

## The three questions must not share one success label

A local reversal asks whether a favorable move occurs before a specified adverse move over the next 30/60/120 minutes. A candidate LOD/HOD asks whether the present extreme survives until the scheduled close. An executable opportunity asks what remains after a feasible entry and its costs. These can disagree. A valuable bounce can precede a later LOD; a correct final LOD can be untradeable at the retrospectively perfect price.

Candidate extremes must carry observed_at, confirmed_at, earliest_decision_at, earliest_entry_at and invalidation, with distinct event/knowledge clocks. Plot an anticipation zone at observation and a confirmation marker at confirmation. Never backpaint the confirmation as an earlier call. The calendar's current session, not midnight or an arbitrary 24-hour window, defines HOD/LOD.

A close-to-close winning label is not an intrabar target/stop label. Five-minute bars touching both barriers are ambiguous unless qualified finer observations resolve the ordering. Report adverse-first, favorable-first, neither, same-bar ambiguity and censored paths. Do not optimize ordering. Next-bar open is a price reference, not proof of an executable fill.

## State progression inside the existing event owner

1. Context: describe prior/session weakness or strength, sector/market direction, volatility, information catalysts and observed participation.
2. Forming: price tests or extends an already-known extreme while progress per observation weakens. This is evidence of price behavior, not proof buyers or sellers have exhausted.
3. Armed: a specific recovery/rejection condition and invalidation are known before the next observation. No retroactive thresholds.
4. Confirmed: a completed observation satisfies the condition. Confirmation delay, the movement already spent and the remaining space to a target are recorded.
5. Invalidated/expired: the known invalidation is crossed, input quality fails, or the horizon expires. The existing Radar transition, not a second watcher/queue, owns this event.

These are semantic states for integration with the existing two-queue contract; do not introduce another persistent lifecycle or mint parallel event IDs. Current executable state vocabulary must be reconciled at implementation, rather than inferred from these prose labels.

## Distinguishing exhaustion from healthy trend pauses

Downside hypothesis: prior adverse displacement, repeated new-low attempts with diminishing incremental distance, recovery from a tested extreme, and a subsequent reclaim. Upside hypothesis is researched separately; neither short profitability nor symmetric thresholds follow from a successful long study.

Healthy-trend control: direction remains coherent, pullbacks are shallow relative to prior-known volatility, a previously established balance is retained, and renewed expansion occurs with observed participation. A stretched oscillator alone cannot discriminate these states. Every exhaustion experiment must include the continuation control so that a reversal detector is tested against the precise situation in which premature fading is costly.

Effort-versus-result from OHLCV is a proxy. Volume is unsigned, bar range does not identify an aggressor, and a price-volume divergence does not establish dealer inventory, absorption, insider accumulation or participant intent. Actual quote/trade evidence can become a separately qualified witness, never a story inferred solely from a smooth chart.

## The first discriminating experiment, after registration

Use a fixed-current liquid universe plus explicit missing/delisted limitations. Register long and short arms separately; model prices first and short borrow availability/cost separately. Test first eligible events per symbol/day/family, then separately test a frozen re-entry policy rather than counting every overlapping bar as an independent trade.

Decision grid: completed five-minute bars; use one-minute data only when actual coverage/source rights/clock behavior have been qualified. Start with 30/60/120-minute local-turn labels and separate same-session-extreme survival. One-to-three-session holding is an additional outcome family, not a renamed intraday label. Register the entire grid before opening outcome columns.

Define all lookback units explicitly. A daily 14-bar ATR is not a 5m 14-bar ATR. Compare displacement and reclaim buffers against the chosen prior-only volatility reference; prior-session normalization and within-session normalization must be separate specified alternatives, not silently swapped after results.

Match controls on ticker or a preregistered peer set, decision time, remaining session length, prior-known volatility, adverse displacement and market/sector state. Do not allow a later-day high hit rate to beat a morning baseline merely because less time remains. Controls cannot be selected by their eventual outcomes. Preserve no-control and low-overlap cells.

Report date- and episode-clustered uncertainty. Cross-sectional signals on the same index move are correlated, and consecutive bars around one turn are one episode rather than many independent discoveries. Keep all names from a shock together in resampling. Purge boundary overlaps for multi-session labels. Show chronological/sector/name concentration and cost sensitivity, not just aggregate win rate.

## Real-time decision-support packet

The eventual producer-to-Terminal record needs: instrument identity; setup family/version; horizon with explicit units; evidence time and source availability; current state; anticipation zone; exact confirmation condition; invalidation; expiry; elapsed confirmation delay; already-realized displacement; remaining target space; positive evidence; contradictory evidence; missing witnesses; freshness; and calibration cohort/version/sample size when actually validated.

A field being absent is not a neutral vote. Unknown options, news or volume evidence remains unknown. No calibrated probability appears until an accepted calibration exists. An explanation model can summarize a deterministic record but cannot turn sentiment, a pattern narrative or an unvalidated score into trade origination/ranking/sizing authority.

## User journey and non-goals

The opening workspace shows Forming/Armed versus Triggered/Confirmed, not one opaque leaderboard. A trader can select a name, see the prior-RTH/AH/PM chain, inspect the opposing continuation thesis, and replay what became knowable at each timestamp. No-edge, conflicting-evidence, stale-source, incomplete-session and already-extended are first-class results.

Initial implementation is descriptive/shadow only. No extra cron, event store, indicator-math fork, native mobile implementation, order router or paid provider. Browser acceptance later requires the real feed-to-card/chart path on desktop/tablet/mobile with visible stale/unknown states; passing math tests is not that proof.

## Options integration later

Keep flow events, inferred packages, positioning and volatility context distinct under existing options owners. A burst of calls is not necessarily bullish opening exposure. A strike node or gamma surface is not a guaranteed support/resistance level. Evaluate whether each qualified options witness adds information to the price-only baseline before allowing a promotion.

An underlying target hit does not prove a profitable option trade. A separate contract-level study needs contemporaneous bid/ask, expiry/strike, implied volatility, executable fills, time decay, spread/liquidity and gap/expiry loss. Do not extrapolate an intraday stock result into 0DTE profitability.

## Formal estimands for the next registered recipe

Let F(t) mean only the qualified information available by decision t. Let e(t) be the earliest admissible entry opportunity after decision/processing latency, not the preceding swing extreme. Let P(e) be an explicitly labeled price reference until actual executable quotes/fills are available. Let A(t)>0 be a fixed prior-only volatility scale whose time unit is declared.

For a long candidate define Tplus = first post-entry time P >= P(e)+a*A(t), and Tminus = first post-entry time P <= P(e)-b*A(t), within a registered horizon H. The local-reversal target is Pr[Tplus<Tminus and Tplus<=H | F(t)]. It is not Pr[close(H)>close(t)] and it is not the final LOD probability. Preserve competing outcomes, neither-hit and censoring. When both thresholds are crossed inside a single unresolved OHLC interval, report an ambiguity set rather than supplying an invented order. A known subsequent opening gap through a threshold is a separate observable first-price event; a stop price is not a guaranteed fill price.

For a candidate low L(t), extreme survival is Pr[min subsequent eligible prices >= L(t) through the scheduled close | F(t)]. The prediction must condition on remaining session length and time of day; comparing a late-day candidate against a morning unconditional baseline is invalid. Local favorable-target probability can be useful even when final-low survival is low, and vice versa. Evaluate each separately and retain their disagreement rather than hiding it inside a composite score.

For remaining opportunity, retain the confirmation cost Cdelay = signed(P(e)-P(formation))/A(t), the distance from executable entry to the frozen invalidation, and space to the predeclared target. A label that starts at P(formation) rewards a move the user could not have captured. Event-time anticipation and actual entry quality must both be visible.

An expected-value statement requires calibrated outcome probabilities AND realistic payoffs/costs. The elementary two-outcome identity p*G-(1-p)*L-C is an explanatory check, not a live sizing rule. For example, hypothetical 70% wins of 0.3%, 30% losses of 1.0%, and 0.1% round-trip costs imply -0.19% expected return. The example is arithmetic, not an observed TTI result. Thus a win-rate headline cannot stand in for decision quality.

## Analytic falsifiers before market-data testing

These are constructive counterexamples, not backtest results. A steadily observed path 100,101,102 has signed efficiency 1. A path 100,98,102 has the same endpoint gain but efficiency 2/6; endpoint return alone cannot establish persistent bidding. Three widely separated prints at 100,101,102 can also have efficiency 1, yet establish no continuous bidding between them. Therefore both signed geometry and independent observation-span/gap evidence are necessary, and neither establishes actual tradeable liquidity.

A high-volume flat bar can represent balanced aggressive trading, offsetting participants, auction activity or other arrangements that share the same OHLCV projection. The projection cannot uniquely identify an aggressor or motive. Quote-supported order-flow imbalance can supply different evidence, but only from its required data and source semantics; it cannot be reconstructed uniquely from unsigned bar volume.

A centered smooth curve can place a turn earlier after later bars arrive. A causal detector can instead report the turn's historical extreme and its later confirmation separately. Those are two truthful times; erasing their difference creates a nontradable backtest advantage.

## Scientific basis and limits

Lo, Mamaysky and Wang, Foundations of Technical Analysis (2000), formalized automatic pattern recognition and conditional-versus-unconditional return comparisons. Their daily historical findings motivate systematic definitions, not a claimed present-day intraday edge: https://www.nber.org/papers/w7613 .

Andersen and Bollerslev, Intraday Periodicity and Volatility Persistence in Financial Markets (1997), demonstrate why within-day periodicity matters for high-frequency volatility modeling. For this proposal, time-of-day normalization is a hypothesis/design requirement to implement causally from prior sessions, not a retrospectively selected correction: https://www.kellogg.northwestern.edu/academics-research/research/detail/1997/intraday-periodicity-and-volatility-persistence-in-financial-markets/ .

Cont, Kukanov and Stoikov, The Price Impact of Order Book Events, study a relationship between best-quote order-flow imbalance and short-interval price changes, with trade volume a noisier explanatory variable. This supports separating actual order-book evidence from OHLCV proxies. Contemporaneous price-impact explanation is not future-return profitability: https://arxiv.org/abs/1011.6402 .

## Bounded next methods, not an unregistered model search

After the first recipe is genuinely registered and run, compare a simple fixed rule with a small regularized model on the SAME decision population and costs. More features or model complexity do not earn promotion automatically. Any learned model uses only training-window normalization, nested model selection without assessment feedback, explicit date/episode grouping and out-of-time calibration. Regime or options variants each add declared trials and must beat the appropriate price-only or context-only control on the same eligible dates. No broad neural search or personalized ticker threshold is authorized by this design packet.
