# Narrative Handoff / Event Microstructure Study

Date: 2026-09-24
State: RESEARCH_ONLY / PRODUCTION_INERT / NO_TRADING_AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: sol/geopolitical-relief-event-study-20260924
Mastermind procedure pin: 605cd056c3463c992d85ba76dbcc90fbb758da75
Skillpack: mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1

## 1. Why this exists

The motivating observation is a possible September 24, 2026 intraday sequence in which
social discussion of U.S.-Iran de-escalation appeared during U.S. hours while technology
shares were already weak, followed by a sharp risk-on reversal. The observation is useful
as a hypothesis seed, not as proof. This study does not assert that the reported policy
headline was authentic at the earliest social timestamp, that U.S. officials intentionally
timed information to affect another region's investors, or that the observed market move
was caused by one headline.

The reusable research question is narrower and more valuable:

When a material narrative shock becomes knowable, does a causal asset move first and then
leave a measurable, repeatable lag in related risk assets after causal confirmation?

For oil-sensitive geopolitical de-escalation, the proposed causal chain is:

public narrative change
-> crude reprices lower
-> broad risk assets reprice higher
-> high-beta semiconductor expressions catch up
-> the lag either closes or fails

This is a generic event-microstructure primitive, not an Iran-specific signal. The same
framework can later test tariff truces, sanctions relief, ceasefires, trade agreements,
supply shocks, and opposite-direction escalation events.

## 2. Canonical owner boundaries

Do not create another event store, news store, timestamp authority, replay plane, Market
Memory, scheduler, evaluator, ranking engine, alert bus, or trading plane.

Reuse the existing owners:

- Market Memory owns point-in-time source and feature semantics.
- Market Memory already defines news_narrative and intraday_microstructure domains.
- Existing Market Memory clocks remain distinct: event_time, available_at, observed_at.
- Macro PR #7165 owns its scheduled macro-turnaround research/replay problem and remains
  independent. This work does not modify or replace that carrier.
- Data OS and existing provider/source contracts own original bytes and price observations.
- Existing evaluation owners must own any later prospective promotion decision.
- Portfolio and execution authority remain completely outside this research slice.

The new research/event_microstructure_study.py module is a pure calculator over
caller-supplied observations. It writes nothing and its authority block is all-false for
rank, gate, size, alert, execution, trade, and Market Memory writes.

## 3. Point-in-time law

Two modes are allowed and must never be mixed silently.

operational_pit:
- decision eligibility begins at observed_at;
- a public source that existed earlier is not treated as known by Mastermind before the
  system actually observed it.

public_reconstruction:
- decision eligibility begins at available_at;
- later Mastermind acquisition is preserved but may not move the historical public clock
  backward.

For every event:
event_time <= available_at <= observed_at

If that ordering cannot be proved, the row is excluded from the primary study.

Social posts are timing context, not authoritative confirmation. A social-first claim may
be measured as an information-diffusion lead only if later official/wire evidence is
recorded separately. Social lead never upgrades source authority.

### September 24 public-source anchor

Fresh public-source reconciliation on September 25 found a materially stronger anchor for
the motivating event than the original social observation:

- Reuters' report that U.S. and Iranian negotiators were exploring a phased path involving
  reopening Hormuz and lifting the U.S. blockade was published by Reuters republishers at
  12:16-12:17 p.m. EDT on September 24, 2026.
- Reuters' 2:35 p.m. EDT U.S.-stocks update explicitly said the S&P 500 and Nasdaq pared
  losses after that report.
- Reuters separately reported at 12:32 p.m. EDT that crude-oil futures pared gains after
  the talks report.

These observations make the event suitable for reconstruction, but they do not establish
the exact original Reuters wire tick, the first social timestamp, a causal price ordering,
or a reusable edge. The historical fixture must bind one exact authoritative source
identity/timestamp before the primary replay is run. The 12:16-12:17 interval is evidence
for source reconciliation, not permission to choose whichever minute produces a better
result.

Public references observed:
- Reuters via MarketScreener, "US and Iran discuss phased deal to reopen Hormuz and end US blockade, sources say", published 2026-09-24 12:16 EDT.
- Reuters via Investing.com, same report, published 2026-09-24 12:17 EDT.
- Reuters via Fidelity, "US STOCKS-Wall Street dips as investors focus on US-Iran war", published 2026-09-24 14:35 EDT.
- Reuters via MarketScreener, crude-oil flash, published 2026-09-24 12:32 EDT.

## 4. Preregistered first hypothesis family

Family: geopolitical de-escalation with oil-risk transmission.

Event inclusion:
1. material de-escalation, ceasefire, sanctions-relief, or negotiation-progress claim;
2. exact public/source timestamp and source identity are available;
3. primary sample requires official or wire publication, or social-first discovery that
   is later corroborated by an official/wire source;
4. one-minute or finer price observations exist for the causal and response assets with
   no stale baseline at the decision cutoff;
5. the event is not merged into the sample as multiple independent observations merely
   because many accounts repeated the same claim.

Event clustering:
- materially identical claims within six hours form one event cluster;
- follow-up wording that adds genuinely new information may form a new event only if the
  new information and clock are separately identifiable;
- event cluster, not post count or ticker count, is the primary independence unit.

### Primary causal asset

The economic causal asset remains WTI or Brent when an admitted point-in-time intraday
commodity source exists. The current Massive/Polygon stocks entitlement does not establish
historical futures-minute authority for CL=F/BZ=F, so the first executable equity-entitled
replay must not label an ETF as crude truth.

First executable proxy hierarchy:

1. USO downside — primary *oil-price proxy* because it is a U.S.-listed ETF inside the
   existing stocks minute-aggregate entitlement.
2. XLE downside — secondary energy-equity confirmation, never a substitute for oil.
3. Direct WTI/Brent — preferred causal asset once a separately admitted commodity-minute
   source is available; if adopted, it replaces the proxy as primary rather than being
   stacked as another confirmation vote.

For a de-escalation event, causal direction is lower oil / lower oil proxy. Every result
must disclose which causal substrate was actually used.

Initial causal confirmation definition:
- first decline of at least 25 bps from the latest valid pre-event baseline;
- the cross must occur within 10 minutes after the decision-eligible timestamp;
- baseline must be no more than five minutes stale.

These parameters are frozen before outcome-bearing historical results are inspected.
They may be changed only through a new preregistered version.

### Primary response

Primary response basket: SMH or SOXX, selected by the admitted historical price substrate.
Primary benchmark: QQQ.

Primary endpoint:
- 30-minute semiconductor-basket excess return versus QQQ;
- measurement begins at the first qualifying crude causal-confirmation timestamp.

Secondary endpoints:
- 5, 15, and 60 minute response return and benchmark residual;
- lag in seconds from crude confirmation to semiconductor response threshold;
- SPY/QQQ broad-risk response;
- AMD, ARM, INTC, and NVDA single-name responses as descriptive diagnostics only;
- oil-to-equity sequence failure rate.

The primary result is not the total move from the first rumor. It is the residual move
remaining after causal confirmation. That distinction is what determines whether the
information can still be actionable after evidence arrives.

## 5. Narrative Handoff interaction

The user observation suggests a possible timezone/session effect. This study will test the
mechanics without making claims about intent or specific investor groups.

Each event receives exchange-calendar/session state at the decision cutoff:
- Asia cash sessions open/closed;
- Europe cash sessions open/closed;
- U.S. premarket/regular/after-hours;
- local clock hour for Shanghai/Hong Kong/Tokyo, London, and New York.

The interaction question is:

Does post-confirmation response lag differ when a material event arrives during U.S. hours
after Asian cash sessions have closed versus when multiple major regions are concurrently
active?

This is an interaction term and subgroup analysis, not a standalone event label and not a
claim that anyone was deliberately shaken out.

## 6. Confounders and exclusion rules

Primary-sample exclusions or separately labeled strata:

- CPI, PPI, payrolls, FOMC statement/press conference, or other top-tier scheduled U.S.
  macro release within plus/minus 10 minutes;
- EIA petroleum release or other scheduled oil-specific release within plus/minus
  10 minutes;
- exchange open/close auction window if the return cannot be separated cleanly;
- a major index constituent earnings release that independently explains the response
  basket;
- stale/missing price baseline;
- source-clock ambiguity;
- conflicting duplicate price observations at the same timestamp;
- trading halt or obvious bad tick;
- an already-completed response move before causal confirmation.

The last case remains measured, but it fails the ordered-propagation hypothesis instead of
being rewritten as a success.

## 7. Controls

Three controls are required before promotion-quality inference.

1. Failed-rumor controls
   Social or low-authority geopolitical claims with no authoritative corroboration and no
   causal crude confirmation.

2. Matched non-event windows
   Same weekday and time-of-day, matched approximately on VIX state, QQQ pre-event
   30-minute return, crude pre-event 30-minute return, and U.S. session phase.

3. Narrative-family counterexamples
   Similar authoritative de-escalation events where crude confirms but semiconductors do
   not show a positive residual response.

The pure research helper currently produces descriptive event-versus-control summaries.
Statistical inference must be added through the existing evaluation/research owner, not by
turning this helper into a second evaluator.

## 8. Statistical acceptance design

Do not count posts, tickers, or same-day securities as independent events.

Before any production promotion is considered:
- chronological train/development/holdout split;
- event-clustered uncertainty;
- block bootstrap or equivalent time-cluster-aware inference;
- no threshold tuning on the final holdout;
- report mean, median, hit rate, missingness, and tail losses;
- show effect with and without the largest individual event;
- show failed-rumor and matched-window controls;
- report results separately by narrative family and session-handoff state.

Initial minimum evidence bar for any claimed reusable edge:
- at least 20 independent event clusters in the complete analyzed sample;
- at least two distinct geopolitical/narrative subfamilies;
- the held-out primary 30-minute residual effect remains positive after estimated spread
  and slippage sensitivity;
- the effect is not entirely carried by one event or one calendar period;
- matched controls do not show the same effect;
- false positives from unconfirmed rumors are materially worse than confirmed events.

These are research-promotion gates, not trading thresholds. A separate accepted portfolio
and execution study would still be required.

## 9. What Mastermind should eventually create if the effect survives

Product concept: Narrative Handoff Radar.

It should be a view over existing owners, not a new intelligence plane.

Candidate states:
1. RUMOR / SOCIAL DIFFUSION
2. PUBLIC / UNCONFIRMED BY CAUSAL ASSET
3. CAUSAL ASSET CONFIRMED
4. PROPAGATION UNDERWAY
5. LAG CLOSED / FULLY PRICED
6. FAILED / CONFLICTED / DATA GAP

The card should show:
- exact source ladder and clocks;
- first authoritative publication;
- first causal-asset confirmation and move size;
- current response lag;
- broad index and sector residuals;
- candidate laggards as context, not auto-ranked trades;
- historical eligible analogue count;
- confirmed-event versus failed-rumor base rates;
- session-handoff state;
- explicit freshness and missingness;
- a falsifier: what would make the current propagation thesis fail.

No alert or action authority should be enabled by this research PR.

## 10. Data reality and next implementation slice

The current repository already has the semantic homes needed for news_narrative and
intraday_microstructure. There is no permanent broad U.S. minute store, but the existing
Massive/Polygon stock entitlement and accepted Entry Radar research law establish
episode-windowed historical one-minute aggregates from at least 2010-06-15 for U.S.
equities/ETFs. The accepted pattern is bounded per-event/per-name REST, never a bulk crawl,
and no permanent minute store.

The existing engine/entry_radar/vendor_minutes.py is NOT repurposed as a research plane:
its cache and semantics belong to Entry Radar C3. Research may reuse the generic incumbent
PolygonOptions/Massive transport and the same bounded aggregate endpoint contract, with an
injected transport in tests and zero minute-data persistence.

The remaining data gap is direct WTI/Brent minute truth: the current stocks entitlement
does not establish futures-minute authority. Therefore the first replay uses USO as an
explicit oil proxy plus XLE as a secondary energy check. Direct crude remains a stronger
future replacement when its source is admitted.

Two lawful paths can advance independently:

A. Historical reconstruction
- use the existing bounded Massive/Polygon one-minute equity/ETF aggregate path for
  USO/XLE, SMH/SOXX and QQQ;
- construct a source-timestamp event manifest without looking at post-event returns;
- run the frozen study;
- keep direct futures-minute data excluded until a commodity source owner admits it.

B. Live-forward evidence
- consume existing Market Memory / Data OS receipts prospectively;
- capture event and intraday observations through the existing owners;
- grade events only after horizons mature.

Missing historical minute data blocks retrospective microstructure inference for that
event. It does not block prospective collection.

## 11. First concrete experiment

The first experiment should use the September 24 motivating observation only as a replay
fixture once its exact source clocks and admissible minute bars are available.

Required outputs:
- earliest social-known time, if source identity can be recovered honestly;
- exact authoritative-known time;
- USO first qualifying downside cross (proxy disclosure required);
- XLE secondary downside confirmation;
- QQQ and SMH/SOXX first qualifying upside cross;
- causal-to-response lag seconds;
- 5/15/30/60 minute semiconductor excess returns after causal confirmation;
- confounder labels;
- explicit result classification: ordered propagation, response-led, unconfirmed, or
  data-gap.

A single successful replay is not evidence of alpha. It proves only that the machinery can
reconstruct the sequence honestly.

## 12. Verification in this slice

Focused local research battery:
- 9 tests passed;
- operational versus public reconstruction clocks;
- impossible clock ordering refused;
- causal-before-response lag measurement;
- response-first sequence rejected as ordered propagation;
- stale baseline becomes data_gap, never zero return;
- missing forward bar remains null;
- social lead remains timing context, not source authority;
- conflicting duplicate price timestamp refused;
- event-versus-control missingness preserved.

Hosted CI and current-base review remain separate release gates.

## 13. Exact continuation

1. Keep this carrier Draft and research-only.
2. Run repository CI against the exact branch head.
3. Use the existing bounded Massive/Polygon equity-minute transport through a
   research-only no-persistence adapter; do not create another source store or reuse the
   Entry Radar C3 cache as a research authority.
4. Bind one exact Reuters authoritative timestamp and build the timestamp-only historical
   event fixture before inspecting post-event returns.
5. Run the first USO -> SMH/SOXX vs QQQ replay, with XLE as a secondary energy check.
6. Separately resolve direct WTI/Brent minute source authority; if admitted, rerun as a
   preregistered substrate upgrade, not as an outcome-tuned threshold change.
7. Run the frozen controls and chronological/event-clustered evaluation after the event
   manifest is assembled without outcomes.
8. If the effect survives chronological holdout and controls, design the read-only
   Narrative Handoff Radar consumer.
9. Any ranking, alerting, portfolio use, or execution remains a later separately accepted
   authority decision.
