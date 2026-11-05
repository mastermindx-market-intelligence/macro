# November 5, 2026 market-score incident: findings and architecture
Status: confirmed diagnosis; implementation and production acceptance remain open.
Operation: macro-market-stress-20261105-c3.
Source: Macro@20959c5e8183f44678df4dbfc26ac246665ba2bf; Mastermind law@d3d96e44f6fbf48ceb8f2f6e8a453b2156bd60ad.
This document records incident analysis, not a new forecast model or trading authority.

## 1. What failed
The product conflated a descriptive prior-close backdrop with a current decision surface. The November4 settled score was57/Mixed, not Risk-on. A sharp increase toward60 nevertheless looked like recovery. By the authenticated November5 postclose observation, the publisher had a fresh build time but zero live symbols, no source-event clock, all six components carried from November4, and normal trade-caution guidance. The dashboard repeated that under “What To Do Now” beside severe November5 futures losses.

The canonical derived risk envelope already declared its measured assessment unusable, with null score/verdict and DEGRADED data. That judgment did not govern the prominent legacy score/action presentation. A smaller fragility82 warning existed; the issue was neither complete absence of warning nor proof that a crash probability model predicted safety. It was inconsistent data eligibility and hierarchy across the actual user journey.

A second confirmed bug attached prior-week initial-claims facts from an undated DOL listing to the November5 release identity, then marked them verified/live. This is an event-identity error, separate from market direction.

## 2. Exact settled-score attribution
The original forward ledger, read at the pinned source, contains:
- November3 asof, logged November4 12:11:28Z:46/Mixed, Radar86 caution, can_force=false.
- November4 asof, logged November5 10:04:20Z:57/Mixed, Radar82 caution, can_force=false.
Both radar authority reasons are early_tier_advisory; no binding score cap was applied.

| Component | Weight | November3 | November4 | Contribution to unrounded change |
|---|---:|---:|---:|---:|
| Trend/technicals |24%|42|49|+1.68|
| Risk appetite |18%|22|22|0.00|
| Volatility |16%|45|75|+4.80|
| Breadth |16%|63|88|+4.00|
| Liquidity/credit |14%|40|39|-0.14|
| Downturn guard |12%|79|80|+0.12|
| Total |100%|46.40|56.86|+10.46|

Rounding produces46→57. Volatility plus breadth explain8.80/10.46=84.13% of the increase. This is exact arithmetic from issued component rows, not a hindsight reconstruction from revised prices.

The breadth88 is a normalized percentile score derived from the distribution of stocks above their200-day average; it is not a claim that88% of all stocks were healthy. Long-horizon broad breadth can improve while a concentrated technology cohort deteriorates. Trend49 and cross-asset risk22 already contradicted a broad recovery interpretation.

Sources: data/market_state/forward_log.jsonl; data/market_state/latest.json; engine/market_state.py.

## 3. Confirmed production defect
Authenticated browser:
- /macro.html reproduced57/Mixed, November4 chart endpoint, “What To Do Now”, and NQ futures-6.87% at the observed visit.
- /live/risk_state.json built2026-11-05 22:25:53 UTC: session.postclose; open=false; expected_session2026-11-05; nightly_asof2026-11-04; live_active=false; stale=true; stale_reason=market closed; n_live_symbols=0; live.source_event_time=null.
- /live/risk_envelope.json built22:27:54 UTC: measured_state.usable=false; score/verdictnull; data_stateDEGRADED; hazardFRAGILE; all four authority booleansfalse.
- Price/session timestamps differ from build/observation timestamps. The evidence file preserves the separate source fields. Payloads were assembled at22:32:09Z; that is not a claim that each was fetched at exactly that instant.

The producer intentionally falls back to nightly at close or when no quotes are usable. The legacy client accepts this as the displayed score and normal guidance. It also silently ignores fetch/HTTP/parse failures and never independently expires a previously painted risk_state payload at browser consumption time. The rendered-session floor only prevents a feed older than the baked page; a November4 page and November4 fallback both pass that floor on November5.

This proves the postclose failure. The original November5 regular-hours payloads were not retained in the evidence read, so we do not claim the57 persisted unchanged throughout the session or invent an intraday detection time. The screenshot was already marked market closed.

Sources: production_observations.json; scripts/build_risk_state.py; templates/risk_state_live.js; scripts/build_live_risk_envelope.py; templates/risk_envelope_live.js.

## 4. Structural responsiveness and a further source inconsistency
The live builder recomputes the existing engine after splicing selected quote series. It carries risk appetite18%, breadth16%, liquidity14% and downturn guard12% from the nightly snapshot:60% of the headline blend. That behavior is consistent with a slow backdrop, not a sufficient acute-shock detector.

Within the16% volatility leg, the builder replaces the VIX term ratio when a fresh pair exists, but does not replace conditions.complacency.vix_pctile. The leg formula is62% term structure and38% inverse VIX percentile. Therefore another6.08% of the whole blend is tied to the prior percentile even when the volatility leg is labeled live. Correcting this should reuse engine.indicators.pct_rank_window and the same configured504-session window used by engine.conditions; it must not create a new volatility factor or tune weights to November5.

Illustration only, not a reconstruction of November5 intraday: carrying November4 non-fast components contributes33.10 points. Carrying the41st-percentile VIX while the term ratio moves to its most stressed bucket gives a volatility component around35. With trend40, the combined score remains approximately48.3/Mixed. A large one-day loss need not destroy a200-day trend instantly.

Separately, Risk Radar’s loud-context gate requires SPY below its200-day mean AND weak breadth. An AI/technology collapse can precede that broad confirmation, especially when breadth is carried from the prior close. Its unvalidated advisory82 cannot legitimately be promoted into a forced market-state cap just to make this event look correct. The existing hazard/leadership evidence must remain visible independently.

The source already permits volatility-index moves up to200% for its outlier sanity check. The hypothesis that a normal equity outlier cap rejected the60% VIX move is not supported.

These findings call for truthful fast-component freshness and separate acute observations, not a redesigned universal risk score.

## 5. Claims identity failure
Official November5 DOL release:
https://www.dol.gov/ui/data.pdf
Initial claims for week endingOctober31:189,000, down6,000 from revised195,000. Continuing claims for the separately lagged week endingOctober24:1,718,000, up23,000. Do not combine their week identities.

Live row claims:2026-11-05 instead carried194,000/-1,000, reference weekOctober24, parsed from https://www.dol.gov/index.php/newsroom/releases/eta. Detection was13:30:41Z and source_released_at13:30:00Z had basis scheduled_embargo_floor. A scheduled time identifies when to look; it does not prove that the bytes describe that release. The exact source digest is preserved in production_observations.json. Retained prior release rows show similar stale-reference patterns.

Repair must bind the dated first-party entry/document, event date and actual reference period before data_ready=true. Missing/mismatched evidence stays unverified; never patch the number manually or relabel an old source. Recovery must use the incumbent retained-row correction path and preserve original detection/correction ancestry. PR9435 owns active CPI recovery/service work and remains intact.

The lower initial-claims result could contribute to rate expectations, but the evidence does not establish it as the primary cause of this sector-led collapse. The observed ten-year yield decline is not the simple pattern of a selloff caused solely by higher yields. A causal claim would require timestamped surprise, rates and equity response around08:30ET, not just same-day coexistence.

## 6. Most supported market mechanism
The evidence supports a sequence, not one proven culprit:
1. November4 election uncertainty fell and major indices rallied, while semiconductor/data-center weakness persisted. Reuters’ November4 intraday account reported SOX down3.6% despite the index rally. This was a composition warning visible before November5.
2. Qualcomm’s results were released after the November4 close. Weak handset revenue and the subsequent price reaction were known before November5 regular trading. They were not available to a forecast frozen before the release.
3. At November5 premarket, Reuters reported neoclouds/chips lower while Amazon was up and Microsoft flat. “Hyperscalers up” did not establish recovery of suppliers, leveraged infrastructure providers or financing-sensitive names.
4. As prices fell, renewed protection demand, possible short-gamma hedging and systematic/leveraged deleveraging could amplify the move. Contemporaneous analysts described these mechanisms; actual net dealer inventory and fund flows have not been obtained.
5. A common crowded exposure and broad risk reduction can spread losses to otherwise defensive sectors. Relative outperformance during a selloff is not a positive absolute return.

Sources:
- https://ca.marketscreener.com/news/wall-street-rallies-after-democrats-win-congress-data-center-stocks-slide-ce785fdfdd81f52c
- https://investor.qualcomm.com/files/content_files/FY2026-4th-Quarter-Earnings-Release.pdf
- https://www.investing.com/news/stock-market-news/ai-datacenter-stocks-slip-as-democratic-sweep-clouds-expansion-plans-5003196
- https://www.reuters.com/business/energy/global-markets-global-markets-2026-11-05/
- https://www.interactivebrokers.com/campus/traders-insight/ibkr-market-insights/a-3-move-signaling-less-volatility/
- https://www.interactivebrokers.com/campus/traders-insight/ibkr-market-insights/yesterday-was-supposed-to-be-about-lower-volatility/

Dealer hedging is conditional. Long-gamma hedging can damp moves; short-gamma hedging can reinforce them. Gross options volume/open interest alone does not identify dealer net exposure, customer direction or offsetting books. Event-volatility unwinding, short covering, discretionary buying and dealer hedge reduction may coexist; prices alone cannot apportion them or prove manipulation. Many systematic risk strategies respond to realized volatility/covariance, not mechanically to VIX alone.
Primary mechanism references:
https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options/
https://www.imf.org/-/media/files/publications/gfsr/2026/april/english/ch1.pdf
https://www.rba.gov.au/publications/fsr/2020/oct/box-a-risks-from-investment-funds-and-the-covid-19-pandemic.html

## 7. What could have been anticipated
Before November4 close: unresolved trend weakness, risk-appetite22, elevated fragility, divergent sector participation and volatile election-related repricing were observable. The justified statement was “relief rally with unresolved fragility,” not “tomorrow must crash6%.”

After earnings / before November5 open: deteriorating chip/neocloud prices and the mismatch with resilient hyperscalers supported a specific AI infrastructure stress watch. Primary earnings timestamps and actual premarket quote clocks matter; overnight information must not be backdated into yesterday’s forecast.

During November5: loss magnitude/velocity, renewed option-implied stress and spreading sector weakness become detection/nowcast inputs. An alert after the first3% decline is not a prediction before the decline. Report first-known, first-issued and first-served lead separately.

No exact sigma classification is justified without an instrument, horizon and ex-ante volatility model. VIX is a30-day SPX implied-volatility measure, not a Nasdaq one-day crash probability. Neither score57 nor radar82 is a calibrated percentage probability.

## 8. Architecture: complete the existing separation
Keep existing canonical owners and paths:
- Measured backdrop: original score and source date.
- Hazard evidence: current native leadership, volatility, credit/liquidity and transmission observations, each with coverage and original clocks.
- Repair: explicit source-native evidence that damage has healed; a price rebound or VIX collapse alone does not prove it. Reuse existing registered rules; do not resurrect rejected synchronized gates.
- Data quality: unavailable/partial observations cannot silently vote calm or justify current guidance. Expiry must hold on initial load, tab resume, long-open sessions and fetch failures.
- Capital policy: separate authorized policies. No numerical sizing or execution authority is inherited from a description, forecast or warning.

The primary surface should state the conflict plainly: “Settled backdrop improving; AI leadership remains damaged” when those facts are current and verified, or “Current assessment unavailable; previous settled assessment57/Mixed, November4” when they are not. A small warning below a large improving gauge is inadequate if the repeated action panel ignores it.

Use existing sector memberships and point-in-time constituents to distinguish hyperscaler platforms, semiconductors, neoclouds, data-center power/equipment and defensive breadth. Show absolute and relative returns together. Do not count price-derived correlated inputs as independent confirmations. Existing #10229 owns EOD shock diagnostics; no duplicate calculator is commissioned.

## 9. Prediction and validation boundaries
The current snapshot marks the current model unvalidated and has3 same-model issued forecasts with0 graded at this pin. Its probabilities concern a SPY close-relative loss of at least5% over5/10/21 subsequent closing observations. They do not answer “Nasdaq will lose6% today.” Different model epochs and overlapping daily labels cannot be pooled to manufacture evidence.

The existing frozen defensive-rotation study failed its combined gate, with39 out-of-sample triggers and about80% false alarms on its primary event. This event cannot retroactively validate it. The existing EW-P3 prospective reader has its own NOT_EXECUTABLE gate and earliest look2027-12-31; incident analysis does not release that gate.

For any genuinely new research candidate, use the existing science owner and preregister:
- exact asset/universe, event definition and horizon;
- forecast cutoffs before close, after earnings,08:30 release, premarket and intraday separately;
- original availability and source-rights-qualified vintages, not corrected hindsight data;
- chronological development/holdout, embargo for overlapping labels, event-cluster uncertainty and a finite trial budget;
- same-target simple baselines, proper probability scores/calibration if actual probabilities are issued;
- precision/recall, false-warning occupancy, event-level misses, usable lead and abstentions for categorical warnings;
- prospective promotion only after independent episodes and the existing evidence gates mature.

Scenario stress tests can be useful immediately without claiming forecast accuracy: estimate what concurrent shocks to correlated exposures would do under an explicitly hypothetical scenario. They do not originate or size trades.

## 10. Delivery and unresolved evidence
The source audit and two bounded implementation commissions remain under this operation. Worker controller creation is not worker START or an accepted patch. Original run IDs and held effects are recorded in the continuation; no duplicate execution or bypass of #9428/#9435 effects is authorized.

Owed before claiming live repair:
- consume and inspect exact patches, integrate only disjoint authorized changes;
- failing-before/passing-after producer and actual-JS regressions;
- required exact-head hosted CI and the existing protected release controller;
- merged source and actual served client/producer bytes;
- authenticated long-open browser with postclose, stale/missing input and fresh-recovery behavior;
- retain historical observations and label any remaining research/runtime limitations explicitly.

The market explanation is evidence-qualified. The immediate engineering failures are actionable. A tested patch, green CI, merge, deployment and the user-visible accepted outcome remain different states.
