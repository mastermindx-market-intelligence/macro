# Cross-Session Narrative Handoff Preregistration — 2026-09-25

State: PREREGISTERED_RESEARCH / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation family: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Parent: Narrative Repricing V2
Purpose: test session-timing and regional information handoff without re-anchoring market-closed events

## 1. Why this is separate from V2

V2 is a same-session microstructure study. It measures an exact source clock, a first
five-minute cross-asset impulse, and residual continuation from +5 minutes onward.

Some economically important geopolitical events arrive when one or more target markets are
closed or too sparse for that design. Moving the event timestamp to the next liquid U.S. bar
would manufacture timing and violate point-in-time law.

Cross-Session Narrative Handoff is therefore a separate experiment.

It addresses two distinct questions:

A. Source-timing question:
Are material relief headlines disproportionately first distributed during U.S. hours after
major Asian cash markets have closed, relative to escalation and other material geopolitical
headlines?

B. Price-handoff question:
When a material event first becomes public while a region's cash market is closed, how much
of the subsequent repricing appears at that region's next liquid session open versus before
or after it?

Neither question asserts intentional timing, investor targeting, manipulation, or a
tradable edge.

## 2. Anti-selection law for the timing question

The existing 20-cluster Narrative Repricing corpus is NOT a valid denominator for proving
headline-timing asymmetry. It was assembled to investigate specific de-escalation and control
hypotheses, not as an exhaustive census of all geopolitical headlines.

The timing study must first build an outcome-blind, fixed-window headline census from one or
more predeclared source families.

Preferred source families:
- one market-moving live feed with recoverable exact first-publication clocks;
- Reuters/wire records where first market dissemination can be pinned;
- official first-party releases as source-origin corroboration.

The census must include qualifying relief, escalation, denial, breakdown, implementation,
and materially mixed/conflicted events. It may not search only for events whose market move
is already known.

Every source family/date window included in the denominator must be declared before the
timing statistic is calculated.

## 3. Timing-unit definition

Independent unit = material event cluster, not article count, repost count, ticker count, or
social amplification count.

Cluster window:
- materially identical information within six hours remains one cluster;
- a later claim is separate only when it adds material new information.

Each cluster records:
- event_id;
- exact available_at;
- source origin;
- dissemination channel;
- narrative direction;
- novelty role;
- resolution stage;
- physical-channel specificity;
- corroboration state;
- source-clock quality;
- scheduled/unscheduled state;
- competing material headline flags.

No market returns are needed for the source-timing test.

## 4. Regional session state

For each exact available_at, classify with the estate's existing exchange-calendar owners,
never approximate weekdays or fixed UTC hours when an exchange calendar exists.

Required regions:
- United States / XNYS;
- Hong Kong / XHKG;
- mainland China / XSHG or the estate's canonical mainland session calendar;
- Japan / XTKS when an admitted calendar exists;
- Europe / the canonical broad European cash-session proxy used by Macro.

Per region:
- previous cash close;
- next cash open;
- whether cash market is open at available_at;
- minutes since previous close when closed;
- minutes until next open when closed.

Derived source-side fields:
- asia_cash_any_open;
- asia_cash_majority_closed;
- after_asia_cash_close;
- us_cash_open;
- us_premarket;
- us_after_hours;
- europe_cash_open.

DST, holidays, half-days, and local exchange breaks must come from calendars.

## 5. Source-timing hypotheses

Primary timing null:

> Conditional on the fixed source census and source-origin/time-zone strata, relief events
> are not more likely than escalation/control events to first become public after major Asian
> cash markets have closed.

Primary descriptive statistic:
- share of relief clusters with after_asia_cash_close=true;
- same share for escalation/control clusters;
- difference in proportions with exact/event-cluster-aware uncertainty.

Required sensitivity:
- exclude U.S.-origin claims;
- U.S.-origin claims only;
- exact live-feed clocks only;
- official/named-principal origin only;
- physical-channel events only;
- weekday only;
- remove clusters with source-clock conflict.

This is a timing-distribution test, not evidence of motive. Even a large asymmetry could be
explained by ordinary Washington/New York work hours, source geography, newsroom cadence, or
the underlying negotiation process.

## 6. Price-handoff event eligibility

Price-handoff analysis is separate from the timing-frequency test.

Eligible cluster:
1. exact source clock;
2. material narrative direction;
3. target region is closed or meaningfully illiquid at available_at;
4. a lawful point-in-time market substrate exists for the target region;
5. previous regional close and next regional open are identifiable;
6. no clock re-anchoring;
7. competing material headlines between event and target open are recorded.

If no lawful regional price substrate exists, result = data_gap. A U.S.-listed ETF may be
used only as an explicitly labeled proxy and never called the Asian market's own response.

## 7. Cross-session return geometry

For each target region, preserve the original event clock and measure separate intervals.

A. Pre-event state
- target asset previous cash-session return;
- previous close-to-event available information where a lawful continuously traded proxy exists;
- volatility/regime context known before the event.

B. Closed-market handoff
- previous target cash close -> next target cash open;
- previous close -> first 5m target VWAP/close after open;
- first 5m -> +30m continuation;
- next-session full cash return as secondary context.

C. Global assimilation path
When lawful substrates exist:
- causal commodity/risk asset reaction after event;
- U.S. or European liquid-session reaction before target region reopens;
- target-region next-open gap;
- residual target move after removing broad/global benchmark movement.

These are separate measurements. The next target open is never substituted for available_at.

## 8. Primary price-handoff endpoint

For events where major Asian cash markets are closed at available_at:

Primary endpoint:
- next-session first-5-minute residual return of a predeclared Asian target basket versus
  its regional broad benchmark, measured from the previous cash close.

Secondary:
- open-gap component;
- first-5m -> +30m continuation;
- U.S. response before Asia reopens;
- sign agreement between causal asset, U.S. risk assets, and next Asia open;
- magnitude remaining unassimilated at the Asia open.

The exact target basket and benchmark must be frozen only after lawful historical intraday
coverage is established. No ticker may be selected because it produced a large known move.

## 9. "Shakeout" hypothesis decomposition

The colloquial hypothesis "bad move in Asia, then U.S. releases good news after Asia sleeps"
contains multiple testable claims. They must not be collapsed into one story.

Test independently:

1. Pre-event Asia weakness:
   Was the relevant Asian sector/market materially weak before its close?

2. Post-close source timing:
   Did a genuinely new relief event first become public only after that cash close?

3. U.S. immediate repricing:
   Did U.S./global liquid assets move consistently with the event?

4. Next-Asia assimilation:
   Did the next Asian open gap/reprice in the same direction?

5. Reversal persistence:
   Did the handoff persist after the first 5/30 minutes, or was it merely an opening gap?

6. Timing asymmetry:
   Across the exhaustive census, are relief events unusually concentrated after Asia closes
   versus escalation/control events?

Only if these separate facts survive controls is there a session-handoff phenomenon worth
productizing. None establishes intentional targeting by officials or media.

## 10. Controls

Required controls:
- escalation events;
- relief rumors later denied/unconfirmed;
- mixed/conflicted clusters;
- same-clock matched non-event days;
- source-origin matched headlines without material physical/economic implication;
- events arriving while Asia cash is open;
- events arriving after U.S. cash close;
- major scheduled macro releases in the handoff interval;
- competing geopolitical headlines before next regional open.

For price outcomes, attribution confidence must fall when the event-to-next-open interval
contains additional material news.

## 11. Statistical law

Independent unit = event cluster.

Timing-frequency analysis:
- report raw counts and coverage;
- Fisher exact or equivalent small-sample proportion test;
- source-origin stratification;
- leave-one-family-out sensitivity;
- no p-value fishing across many clock buckets.

Price-handoff analysis:
- chronological train/development/holdout;
- event-clustered bootstrap or equivalent;
- matched non-event windows;
- leave-one-event-out;
- source-clock sensitivity only when the ambiguity was known before outcome access;
- transaction-cost sensitivity only if the study later reaches a tradability question.

No promotion from one dramatic day.

## 12. Existing events suitable for source-side handoff classification

The current research already contains examples whose exact clocks make same-session U.S.-ETF
measurement impossible or incomplete, including weekend/very-early events. They are not
re-anchored here.

Examples may be admitted only through a frozen source manifest under this preregistration.
Their existence motivates the design; it does not pre-score them.

## 13. Data-source boundary

Do not create a second regional market-data plane.

Use existing Data OS / Market Memory / canonical regional price owners when they provide:
- exact exchange calendar;
- point-in-time previous close;
- intraday next-open observations;
- vintage/provenance.

Direct WTI/Brent, futures, Hong Kong, mainland China, Japan, or European intraday data each
remain separate source-authority questions. Missing one source blocks only that measurement
lane.

## 14. Product mapping if evidence survives

Possible read-only extension to Narrative Repricing Radar:

SESSION HANDOFF panel:
- exact event clock and source ladder;
- which major cash sessions were open/closed;
- minutes since Asia close / until next Asia open;
- U.S./global assimilation before the reopen;
- next-region opening gap and first-30m follow-through;
- competing-headline contamination;
- historical source-timing base rate;
- matched-control comparison;
- explicit "timing does not imply intent" provenance note.

No alert, ranking, trade, sizing, or execution authority is granted by this preregistration.

## 15. Exact next action

1. Freeze a fixed-window exhaustive source census for the timing-frequency test.
2. Census existing canonical regional intraday/calendar coverage before naming target baskets.
3. Freeze a cross-session source manifest without market outcomes.
4. Only then calculate timing asymmetry and cross-session price handoff.
5. Keep this family separate from V2 same-session microstructure results.
