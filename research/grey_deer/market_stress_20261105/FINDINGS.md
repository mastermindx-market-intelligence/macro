# November 5, 2026 market-score incident: findings and architecture
Status: confirmed diagnosis and qualified score/claims repairs in PR #10782; hosted release and production acceptance remain open.
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

Illustration only, not a reconstruction of November5 intraday: carrying November4 non-fast components contributes33.10 points. Carrying the41st-percentile VIX while the term ratio moves to its most stressed bucket gives a volatility component34 after engine rounding. With trend40, the combined score is48.14/Mixed. A large one-day loss need not destroy a200-day trend instantly.

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

## 10. Implemented containment and qualification

The parent implemented the bounded repair in the existing managed C3 workspace after the paid freshness builder `macro-stress-freshness-containment-20261105-c3-01` returned a terminal host-temperature admission refusal. It was not redispatched.

Changed existing paths:
- `scripts/build_risk_state.py`: refresh the existing VIX percentile from the spliced VIX series with the same configured lookback and shared percentile function used nightly. Publish the existing quote admission budget. Require clocked SPY, QQQ, IWM and both existing volatility inputs before `live_active` can certify a current calculation; expose missing inputs and truthful live/partial/carried component bases. The existing envelope consumes that same eligibility flag.
- `templates/risk_state_live.js` and byte-identical `site/risk_state_live.js`: expire current guidance by browser time, separately check artifact age and source-observation age, and reject old-session/live-clock failures. Recheck immediately on tab visibility and page resume. Show the unchanged numerical snapshot with its date and an explicit unavailable assessment. Update both the hero and What To Do Now. Retain an already displayed newer session when the producer falls back after close. HTTP, JSON and network failures cannot leave guidance current indefinitely; fresh observations restore the normal existing presentation.
- Existing CI-wired `tests/test_risk_state_live_session_floor.py`: add production-shaped regressions and a producer-to-envelope eligibility test. No new score engine or test lane.
- `scripts/official_release_parsers.py` and `scripts/watch_release_publications.py`: require a matching DOL entry's own printed date, release identity and preceding-Saturday reference week before claims facts become verified. Support the observed canonical, index.php and node paths without borrowing another entry's date. An unmatched or unchanged undated listing cannot fall back to generic numeric parsing. Withdraw retained unbound claims values into the existing published-unparsed/retry state while retaining their original source digest and detection ancestry. Correctly preserve the prior year for a December reference week released in January. No CPI parser, source pacing, service or release-lifecycle changes.

Qualification at this boundary:
- Original focused source suite after materializing its omitted site assets: **61 passed**.
- Score candidate (session-floor, copy-sync, participation-copy, existing live-envelope suites): **168 passed**, no skips, in10.91s.
- Combined score/claims candidate: **314 passed**, no skips, in13.65s across official-release parsers, existing VPS orchestration, release-actual ingestion, release-publication client, status error hygiene and the four score/envelope suites. Five unrelated PCE fixture failures on the first combined run were resolved by materializing the repository's tracked `data/release_forecast` fixtures; no fixture was invented or changed.
- Seven new claims regressions run against the original immutable source gave **6 failed / 1 passed** (`claims_failing_before.json`); the repaired combined suite passed. `node --check`, template/site byte parity and `git diff --check` passed.
- `consumer_replay.json` executes the original and repaired JavaScript against the actual captured production payload. Before:57/Mixed with “Trade small. Stay selective.” After: the same57 and identical path with “Current risk assessment unavailable” and explicit November4 historical date. This is a controlled Node DOM replay, not a deployed browser claim.
- Tests also exercise partial equity/volatility coverage, a naive critical quote clock, current source data, genuine VIX percentile shock response, the unchanged two-tick debounce, postclose rollback prevention, tab-resume expiry, HTTP/JSON/network failure and recovery. Claims tests cover stale/future/malformed/wrong-week entries, cross-node date contamination, HTML void tags, holiday/year boundaries, withdrawal/recovery and keep-first behavior.
- `claims_consumer_replay.json` applies the repair to the actual captured November5 production row:194k is withdrawn, data_ready becomes false, and original source URL/hash/detection ancestry remain. This is controlled replay, not a production correction receipt.
- The connected authenticated production browser remains usable. A loopback preview on the separate source computer was not reachable from that browser; its temporary server was stopped. Visual and actual production acceptance remain owed after release.

The paid read-only audit `macro-stress-live-audit-20261105-c3-01` returned successfully and was accepted after parent source/evidence review. Response digest: `7d73a28051d5dca9a75882f98816d16bc8dc599a6ae1bb3d2b0c93fdc33e9091`. Its illustrative crash scores are scenarios, not a November5 intraday replay. The parent did not adopt its suggestion to conflate the artifact and quote freshness budgets.

The claims worker `macro-stress-claims-identity-20261105-c3-01` returned a local-only candidate at `27898dfecdbe86c4007815b27e8eab4239665f5e`; it was not pushed or deployed. Response digest: `a81e478ba248182bf90763d0e607ac6055fcf25e7c3fcb20ca1bbb0efc655194`. Its artifact resides under a path outside the installed generic artifact export contract; no path guard was widened and no alternate read was used to bypass it. The worker code artifact is NOT_ACCEPTED because it was not retrieved or independently verified. After that terminal return, the parent implemented and qualified the claims repair directly in this original managed workspace from verified source. The worker's reported test counts are not used as parent acceptance evidence. #9435 remains an independent armed carrier; inspection shows its parser changes are CPI-specific while this patch changes DOL claims identity. Its pacing/service/lock/recovery changes are not copied or taken over; normal merge-conflict checks still apply.

Owed before claiming live repair:
- required exact-head hosted CI and the existing protected release controller;
- merged source and actual served client/producer bytes;
- authenticated long-open browser proof of current/historical labeling;
- deployed claims receipt withdrawal/correction; source repair and controlled replay are verified;
- original intraday payload history, if retained, to distinguish which failure operated during regular trading hours;
- the existing source/hazard consumer integration and scientific evidence gates for predictive improvements.

The measured-score repair changes source truthfulness and current-assessment availability. It does not validate a crash forecast, promote Radar82 to a probability, change risk weights/thresholds, release an old hold, or grant trading authority. A tested patch, green CI, merge, deployment and the accepted user outcome remain distinct.

## 11. Release boundary
PR: https://github.com/mastermindx-market-intelligence/macro/pull/10782
The first source head `3fce398ed4fb6f4dae48c11b2daabbc5cecd46b8` contains the score repair; the following same-branch commit adds the qualified claims identity repair and tab-resume expiry. No merge-on-green label has been armed at this record boundary. Main-branch rules were read: no enforced formal approval requirement was returned; the protected source delivery contract and existing controller remain binding. The main authority check passed on the first head. The red `ci-authority/codex/merge-queue-pilot` check explicitly identifies an inactive base context; it is not the main authority check. Exact final-head qualification is still required.

## 12. Pre-open warning, production runtime, and consumer interaction — November 6 follow-through

### The system had recorded substantial damage before the crash

Accepted source commit [f1fc8efbed084af73d14b82f93247703e6fa018e](https://github.com/mastermindx-market-intelligence/macro/commit/f1fc8efbed084af73d14b82f93247703e6fa018e), timestamped November 5 11:36:13 UTC / 06:36:13 ET, contains a November 4 Leadership Crack assessment: BROKEN, median member drawdown -39.23% from the 63-session high, index drawdown -1.58%, dislocation true, and 42/42 members meeting the detector's own freshness definition. Its state_since October 16 is state history, not first customer availability.

Ancestry and exact Leadership blob equality establish the same record in accepted main head 5f20e1571d6793cee6fdb3124033c2d9cc5cd1c6. GitHub main/push [fences run 42030287026](https://github.com/mastermindx-market-intelligence/macro/actions/runs/42030287026) was created at November 5 12:48:39 UTC / 07:48:39 ET. This is an observed upper bound on accepted-source availability before the 08:30 claims release and cash open. It is not a subscriber delivery/acknowledgment clock.

The envelope at that received main head (Git blob 61b231ae4cfd2458ef1aae67937c469945d10acb) reports 57/MIXED usable, FRAGILE, fresh same-session BROKEN leadership and Radar caution/82. It was produced at 11:19:07 UTC. Policy NORMAL means zero active policies; all execution, gating, ranking and sizing grants remain false. The older f1fc envelope blob 2e79abf49ad545b320ecd8913cb0a43a569c040f carries the same selected foreground fields.

This is a failure to present and consistently apply an existing warning, not evidence that the specific crash's timing or magnitude was predictable. Original #9428 owns the foreground response. The exact selected-field replay there preserves57/history, presents the qualified warning above the gauge, and gives the existing warning response precedence in What To Do Now. Advancing the expected session without new evidence produces unavailable rather than ordinary guidance. Both cases passed. These are controlled consumer tests, not production acceptance.

### Original #9428 effects are reconciled

The old body was stale. Original combined Fabric review risk-response-integration-review-20261015-c1-01 is terminal and ACCEPTED/reviewer. Canonical [October 17 source receipt](https://github.com/mastermindx-market-intelligence/macro/pull/9428#issuecomment-6235653016) records genuine resolution of the old CI/CSS source refusals on the same carrier. The foreground polish worker risk-response-pro-briefing-polish-20261017-c1-01 is terminal; its already-applied useful result was reviewed and accepted, response SHA256 635a742109341b84a3502c051c36273abf6a7e9d36eb569695c37e7f0a5c2e7f.

Recovery remains on its original C1 workspace/branch. Current-main integration preserves the existing EW-P4 detail consumer and all387 current CI jobs, with only the original15 additive risk-response closure paths. The current October18 no-accent-edge design rule replaces the obsolete top stripe with neutral even borders and labeled semantic ink. Earlier specifically refused mission-note bytes remain unchanged and unstaged. Separate #8132/#7029/forecast/portfolio holds remain separate.

### Actual production runtime was inspected

The existing documented Macro deployment identity authenticated on the verified M2 Studio route; no key bytes, host inventory, credentials or raw sensitive configuration were exposed or changed. The first fleet-mapping helper returned an invalid owner result; a bounded runtime-metadata diagnostic and direct M2 hardware identity established the actual carrier, then two accepted Macro source records identified the serving role and existing credential.

At November6 00:06:30 UTC, serving-tier source was aa95b0d1d204dc9fd958afbe22e4be3ed647d806, not this candidate. Latest risk_state was built November5 22:59:33 UTC, expected completed session November5, nightlyNovember4, live=false, stale=true, n_live=0, display57. The separate envelope marked measured data unusable. This confirms the after-close stale-guidance contradiction.

Two bounded retained journal reads found291 risk-state task-status records across the premarket/regular/postclose windows. One was failed at14:00:55 UTC; subsequent executions succeeded. The incumbent journal reports task status and duration, not historical score/quote payloads. These logs do not establish that57 was displayed throughout regular hours or that the single failure caused the incident.

### A real two-reader expiry defect was found before release

Running this PR's actual unavailableAssessment function with original #9428's actual warning consumer reproduced a dangerous sequence:
1. Score assessment expires: visible action correctly becomes Current risk assessment unavailable.
2. The element still retains its older data-wtd-base-* fields.
3. A subsequent eligible quiet warning response restores Stay selective. Add where setups confirm from that expired baseline.

The repair invalidates the existing action baseline alongside the visible label, using UNAVAILABLE as the presentation baseline verdict. Valid score recovery updates that same baseline. It does not add a resolver, forecast, risk state, queue, policy grant or trader.

Both template/site regressions failed before the fix. All91 affected session-floor, copy-sync and participation-copy checks pass after repair. The same combined-consumer replay now preserves unavailable through the later quiet response. Current paired-JS SHA256: 9a52dbd1d204eb4938a99f25b973cf100c825617f6059cd885529a534edddb17. Node/DOM execution is software proof, not a real browser.

For #9428's current-main integration, the wider selection initially returned567passed,2failed,2existing artifact-dependent skips. The two failures used different simulated publications under one identical build clock and were correctly rejected by the ordering fence; distinct sequential publication clocks restore the intended healthy/degraded/healthy test, with2passed on focused rerun. Production ordering was not weakened.

### Release state at this repair boundary

Old head d2826053 passed all26 binding hosted checks. The controller required a main refresh and deferred it under its workload cap (17 indexed proofs vs cap8). A subsequently reproduced consumer defect materially invalidated integration readiness; the current session [explicitly disarmed its own PR](https://github.com/mastermindx-market-intelligence/macro/pull/10782#issuecomment-6673408881) before source changes and retains ownership through repair/requalification/release. This is not an empty refresh or a capacity-gate workaround.

New-head tests and release qualification remain required. #9428 must consume the accepted freshness repair on its original carrier before combined acceptance. Browser currently reports missing originating browser context; verified server access does not substitute for the authenticated UI path. No merged/deployed/customer-accepted outcome is asserted at this boundary.

## November 6 C4 required-quote expiry repair

The earlier consumer-time checks were incomplete when required inputs had different quote clocks. With a 15:05 build, QQQ at 14:45:30, other required quotes at 14:50, and a 20-minute quote budget, QQQ expires at 15:05:30. At 15:06 the newest aggregate source clock and the carrying artifact are still within their budgets. They cannot certify the older required leg.

C4 recorded this material counterexample in [HOLD6679754341](https://github.com/mastermindx-market-intelligence/Macro/pull/10782#issuecomment-6679754341), removed its earlier admission, and recovered the original C3 workspace with unchanged c2180b76 local/remote head, no tracked changes or active merge/rebase/lock, while preserving ignored historical proof artifacts. The historical production investigation above was not rerun.

### One producer deadline through the existing consumers

The producer records clocks only when its existing `clocked()` eligibility check accepts an already-required input. An active payload's absolute `stale_after` is the earliest of those clocks plus the existing configured quote budget, capped at the same whole-second `built` stamp plus five minutes. Inactive payloads have no live deadline. Optional/carried quotes gain no veto. The newest `source_event_time`, full clock provenance, VIX selection/percentile computation and historical fallback retain their original roles.

The existing risk-state browser gate requires that deadline. The live-envelope wrapper also requires it and passes it through the existing composer, shortened further by a stricter configured carrying-artifact horizon when applicable. Rebuilding the envelope never renews the underlying inputs. The envelope browser's existing `active()` gate checks the carried expiry and its existing tick precheck withdraws a cached envelope even while a request remains pending. Both consumers refuse missing, malformed or timezone-naive live deadlines and expire at equality. No new timer, required-symbol policy, risk factor, state machine or publication owner was introduced.

The existing `engine/risk_envelope.py` is unchanged; #10795 owns its separate context/engine work. The wrapper, paired browser gates and their test surfaces are source-disjoint from #10795's published changes. Terminal's existing absolute-deadline contract can read the new field, but installation and authenticated consumption are not proved by source compatibility.

### Actual qualification

- On the original producer/client source,35 new cases produced27 behavior failures and8 passes, with zero pytest errors. The first receipt wrapper wrongly required an optional JUnit failure-type attribute. The retained failure messages were reconciled by process 44702, exit0, without rerunning tests; the failures were7 missing-field KeyErrors and20 consumer assertions.
- On the unchanged envelope wrapper and paired browser source,24 additional cases produced20 behavior failures and4 valid controls. Process 65703 completed exit0 after qualifying those expected failures.
- The producer/client repair first passed all 116 session-floor cases. The final coherent producer/envelope/paired-browser repair passed the original nine-module affected selection with **373 passed, zero failures, zero skips**, including 59 new cases. Process 82074 completed exit0; pytest 15.76 seconds, five existing dependency deprecation warnings.
- Both JavaScript pairs were emitted with `lib.site_assets.copy_asset`, compared by exact Git blobs, and passed Node syntax checks. Real producer output was consumed by the actual envelope builder and both shipped envelope JavaScript copies. Cached-feed expiry, pending fetch, exact boundaries, stricter envelope horizons and lack of renewal were exercised with deterministic temporary fixtures.
- Existing shared-helper arithmetic tests remain intact. The old wrapper assertions requiring a null expiry and byte equality with a no-expiry implementation were updated for this material contract change. Settled bundle identity, provenance clocks, future-clock refusal, dwell law, source/consumer copy and release-parser tests remain in the passing selection.

The exact command, process receipts and eight source blobs are recorded in `qualification.json`. This is controlled software qualification. It is not authenticated-browser, production or customer acceptance.

### Integration and release boundary

At the compared main 075445df snapshot, all eight original modified paths and the inspected envelope/emitter companions are byte-identical to the original main parent 9531f6b1. Preserve the complete current-main tree and the original 17-file incident investigation when publishing the repair.

#9428 remains on original Draft head e935c61023fd646a29dbeb2774152927a4a33b1b. Its source explicitly assigns freshness eligibility to #10782. Its `active()` and `market_freshness()` insertion surfaces were unchanged; its distinct foreground/action synchronization, publication-order fences and native Radar-asof preservation must survive when it consumes this repair. This PR does not import or replace those unmerged foreground changes. #9435's separate uncertain review and the forecast/portfolio holds remain separate.

Fresh CI and explicit hold disposition remain required before re-admission. The original authenticated production-browser path remains unproved. No replay of the denied production-snapshot transfer, new serving-tier write, deployment or final product acceptance is claimed.


## November 6 C4 consumer-fixture compatibility follow-through

Original hosted [run42187372021, pack10](https://github.com/mastermindx-market-intelligence/Macro/actions/runs/42187372021/job/127806620899) exposed seven Radar integration failures and66 rotation-consumer failures on60fabc3a. Both automatic exact-base075445df owner replays completed successfully; the candidate semantic artifact13493533833 finalized. This was a settled compatibility failure, not an unknown replay or publication failure.

The shared Radar fixture supplied only built plus a relative TTL. The rotation tests invoked the actual envelope builder over synthetic upstream risk-state inputs that omitted the newly required absolute expiry. Production correctly refused these inputs before the intended lifecycle and negative-receipt assertions could run.

The two existing fixture modules now supply explicit, timezone-qualified deadlines for their original observations. The actual builder output is accepted immediately before its14:05 deadline and rejected at equality and afterward. A separately deep-copied, deliberately later-expiring synthetic envelope preserves every original carrying-TTL assertion: inclusive TTL boundary, rejection one microsecond later, no renewal on republication and the existing120-second carrying-clock tolerance. That altered copy is not represented as actual producer output. The weekend case moves its fixture expiry with its deliberately moved observation, preserving the original session-rejection assertion.

All75 existing test functions and their decorators/imports are preserved. All234 original assertions remain, with three added assertions for the real producer deadline. No production function, shared engine, CI owner, manifest, budget or existing negative expectation changed.

The two complete affected modules pass **169 tests, zero failures/errors/skips**, in74.55 seconds pytest time. Both repository guards stayed active; the module guard reported zero leaks. The original receipt driver then failed an extra, incorrect empty-baseline assertion: this existing source workspace already had the two intended site JavaScript modifications. The canonical data guard permits a starting baseline and rejects newly dirtied paths. Bounded reconciliation verified those same two watched paths and their unchanged blobs, all25 measured source/dependency blobs, the original successful pytest exit and complete169-case XML. Reconciliation process44439 exited0; the tests were not rerun and neither guard was changed or waived.

Current main allocation and stockdata template bytes were reused as qualification inputs, not added to this PR's published delta. Engine/lib/config trees match the published source, and the existing renderer/test helpers are unchanged. The earlier373-case producer/envelope/paired-browser proof is retained for identical production bytes and is explicitly not a new run.

Exact fixture blobs, original failure/run identities, test and reconciliation receipt hashes are recorded in qualification.json. Current-head hosted CI and the explicit release disposition remain owed. #9428's original integration, #10795's separate engine surface, authenticated browser/production acceptance and all prior refused operations retain their existing boundaries.
