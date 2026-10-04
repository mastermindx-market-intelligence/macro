# Cross-Session Source Timing — Advisory Preview

Date: 2026-09-26
State: EXPLORATORY_ADVISORY / SOURCE_ONLY / NON_POPULATION / NO MOTIVE INFERENCE
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Source census: research/CROSS_SESSION_SOURCE_TIMING_CENSUS_RAW_V0_2026-09-25.json
Source census blob: bb7109a6c1b38f199d93efcd475e6d81bd5fa877
Protected procedure pin: 58c842d5ab99e29785ec9b4d16ccee67e85e19c4
Skillpack index blob: 94d1af402598894372858793a5b1931019c5fa77

## 1. Why this preview exists

The motivating hypothesis was that favorable U.S.-Iran/Hormuz information may often arrive
after major Asian cash markets have closed, potentially creating a session-handoff effect.

The frozen cross-session preregistration explicitly separates:
1. publication-clock distribution;
2. price handoff across closed/open regional sessions;
3. any claim about human intent.

This receipt addresses only the first question with an advisory fixed-hour sensitivity.

## 2. Hard limitation

The raw source census contains 35 recovered unique event clusters, but its coverage status is
`retrieval_incomplete`.

Public search/index recovery does not prove that every qualifying Newsquawk headline in the
2026-06-14 through 2026-09-24 window was enumerated.

Therefore:
- the primary timing-frequency test remains BLOCKED;
- these percentages are NOT estimates of the true population rate;
- no Fisher/exact significance test is run;
- this receipt may not be cited as evidence of deliberate timing, manipulation, or targeting
  of Asian investors.

The inference firewall in research/cross_session_source_census.py remains unchanged.

## 3. Advisory session approximation

This sensitivity was preregistered as allowable only for exploration.

Rules:
- weekday event clusters only;
- `after major Asia cash close` approximated as available_at >= 08:00 UTC;
- no exchange-holiday, half-day, lunch-break, or exceptional-session claim is made;
- relief cohort = relief + implementation_relief;
- control cohort = escalation + implementation_escalation + denial_or_breakdown +
  mixed_conflict + neutral_process.

This is an advisory clock bucket, not the eventual authoritative regional-session classifier.

## 4. Recovered-corpus result

Among weekday timing-eligible rows:

| Cohort | N | >=08:00 UTC | Advisory rate |
|---|---:|---:|---:|
| Relief | 22 | 18 | 81.8% |
| Escalation / denial / mixed controls | 11 | 10 | 90.9% |

Observed difference:
- relief minus control = **-9.1 percentage points**

Restricting to weekday rows with exact live/market-feed clocks:

| Cohort | N | >=08:00 UTC | Advisory rate |
|---|---:|---:|---:|
| Relief | 21 | 17 | 81.0% |
| Controls | 9 | 9 | 100.0% |

Observed difference:
- relief minus control = **-19.0 percentage points**

The recovered sample therefore does NOT show favorable/relief headlines as uniquely
concentrated after the major-Asia-close approximation. If anything, the recovered control
headlines are at least as concentrated there.

## 5. Clock-bucket shape

Weekday recovered rows:

| UTC bucket | Relief | Controls |
|---|---:|---:|
| Before 08:00 | 4 / 22 (18.2%) | 1 / 11 (9.1%) |
| 08:00-13:30 | 7 / 22 (31.8%) | 5 / 11 (45.5%) |
| 13:30-20:00 | 10 / 22 (45.5%) | 3 / 11 (27.3%) |
| >=20:00 | 1 / 22 (4.5%) | 2 / 11 (18.2%) |

Median weekday publication clock:
- relief: about 13:17 UTC
- controls: about 12:57 UTC

The medians are close. This is more consistent with a broad source-geography/news-cycle
effect than a recovered-sample pattern specific to favorable news.

## 6. Interpretation

The dramatic September 24 sequence remains real as an individual event:
- a materially constructive narrative arrived after Asia cash hours;
- U.S. liquid markets repriced sharply.

But the recovered source corpus does not support the stronger timing story:

> favorable Iran/Hormuz information is specially released after Asia closes.

A more defensible working model is:

> material Iran/Hormuz information of many directions tends to arrive during Europe/U.S.
> hours, after major Asian cash sessions have often finished.

That structural timing can still matter for cross-session market assimilation even without
directional publication bias.

## 7. What remains potentially useful

The absence of favorable-news timing asymmetry does NOT eliminate a session-handoff edge.

A different, still-live question is:

> Conditional on a source-clean event arriving while Asian cash markets are closed and being
> confirmed by the causal market, how much repricing is left for the next Asian cash open?

That is a price-handoff question, not a publication-frequency question.

It needs:
- authoritative regional exchange calendars;
- lawful regional previous-close / next-open data;
- intraday first-5m data where available;
- competing-headline contamination through the closed interval.

Current data census:
- U.S.: native minute path available;
- mainland China: canonical calendar + minute-plane implementation exist, materialization /
  read-path coverage still needs reconciliation;
- Hong Kong, Japan, Europe: native historical first-5m lanes remain source-gated.

## 8. Product consequence

Narrative Repricing Radar should NOT include a heuristic such as:

`RELIEF + ASIA_CLOSED = stronger signal`

based on current evidence.

Instead, a future SESSION HANDOFF panel should display:
- event clock;
- which regional cash sessions are open/closed;
- source quality and narrative direction;
- causal confirmation/rejection;
- global assimilation before the next regional open;
- competing headlines;
- how much movement remains at the next regional open;
- historical recovered-sample context;
- explicit warning that timing does not imply intent.

## 9. Exact continuation

1. Do not unlock the primary timing-frequency inference until source enumeration coverage is
   demonstrably complete.
2. Reconcile the existing TuShare trade_cal + stk_mins read path for mainland China rather
   than create a new regional data plane.
3. Freeze a price-handoff source manifest before reading next-session outcomes.
4. Use causal-confirmed versus causal-rejected events as separate strata.
5. Keep the prospective V2 holdout untouched.
