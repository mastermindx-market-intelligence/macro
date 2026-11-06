# Prospective Cross-Session Transfer Protocol

Date: 2026-09-26
State: PROSPECTIVE_PROTOCOL_FROZEN / RESEARCH_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`
Development result: `research/CROSS_SESSION_US_TO_HK_MATCHED_CONTROL_RESULTS_2026-09-26.md`
Protected Mastermind pin: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`

## 1. Prospective boundary

The prospective clock begins at the Git commit timestamp that first adds this file.
Any event with `available_at` at or before that commit timestamp is development/history and
cannot enter this prospective cohort.

The existing Narrative Repricing V2 prospective holdout is a different asset and remains
**UNTOUCHED**. This protocol does not open, relabel, or consume it.

## 2. Hypothesis frozen before future outcomes

Development observation:

- event-conditioned U.S. SMH-minus-QQQ +5->+35 residual vs next HSI open:
  75.0% sign agreement on 12 measured rows;
- broad ordinary daily control:
  37.9% sign agreement on 66 session pairs;
- same-clock matched non-event control:
  50.0% sign agreement on 20 complete rows;
- clean-primary event slice:
  71.4% sign agreement on seven rows;
- corresponding clean-primary matched controls:
  38.5% sign agreement on 13 complete rows.

These are development values, not prospective expectations.

Frozen prospective question:

> For future source-resolved geopolitical repricing events, does the sign and magnitude of
> the realized U.S. SMH-minus-QQQ +5->+35 response contain reproducible information about
> the next Hong Kong cash-session opening gap beyond matched same-clock non-event controls?

## 3. Event admission

Qualifying narrative families:

1. physical energy/shipping security events with plausible global risk-premium transmission;
2. ceasefire/de-escalation or escalation events in active geopolitical conflicts;
3. official or attributed policy/operational developments that materially change an
   already-active geopolitical risk channel.

Excluded:
- routine macro data;
- earnings/company-specific semiconductor news;
- unattributed social-only rumors;
- retrospective article clocks;
- generic diplomatic commentary with no material change in the active risk channel;
- any event first selected because its market move looked large.

Source clock:
- earliest exact decision-eligible public clock available from official/wire/live attributed
  source;
- preserve both source time and observed-at time when operational ingestion exists;
- no timestamp shifting after returns are visible.

Source state must be one of:
- SOURCE_RESOLVED;
- SOURCE_CONFOUNDED;
- SOURCE_UNRESOLVED.

Confounded/unresolved events remain in the log but outside the clean-primary prospective slice.

## 4. Frozen U.S. measurement

For every admitted future event:

- response: SMH;
- benchmark: QQQ;
- event clock: exact frozen `available_at`;
- first response start: first admitted minute-close observation at/after +5m within the
  existing 2-minute tolerance;
- response end: first admitted observation at/after +35m within the same tolerance;
- metric: SMH return(+5->+35) minus QQQ return(+5->+35), basis points;
- no re-anchoring on market-closed or missing bars;
- missing geometry = DATA_GAP.

Causal context is recorded separately using the existing evidence-state model and existing
causal-asset owner. It is not allowed to change the frozen U.S. response geometry.

## 5. Frozen Hong Kong endpoint

Primary currently-admitted endpoint:

- HSI observed cash close on the event date -> first observed later HSI cash open;
- incumbent Yahoo transport, `auto_adjust=true`;
- no forward fill;
- missing event-date HSI close or later HSI open = DATA_GAP.

Secondary capability-gated endpoint:

- equal-weight Hong Kong semiconductor basket first five minutes after the next HK open,
  residualized against the frozen broad benchmark;
- only if the separately frozen HK intraday source gate is healthy;
- source outage never permits substitution with a new regional data plane inside this study.

## 6. Frozen matched controls

For each future event:

- nearest prior and next observed U.S. SMH session;
- exclude every date containing an admitted source event;
- <=10 observed-session distance;
- reuse the event's exact UTC time-of-day;
- identical SMH-minus-QQQ +5->+35 geometry;
- same HSI next-open geometry;
- no return-based control replacement.

If one side is missing, keep the other. If both are missing, retain the event with control DATA_GAP.

## 7. Evidence-state fields per event

Every prospective record must preserve:

- event_id;
- source family and exact source clock;
- source quality / conflict state;
- causal asset confirmed / rejected / unmeasured;
- U.S. first impulse observed / missing;
- U.S. +5->+35 SMH-minus-QQQ residual;
- event-conditioned transfer sign agreement;
- prior-control result;
- next-control result;
- next-HSI-open gap;
- target-region assimilation observed / not observed / data gap;
- competing headline contamination;
- analogue family;
- all source receipts.

No later layer may collapse causal rejection, source conflict, and a lucky next-HSI move into
the same validated state.

## 8. Evaluation checkpoints

Before the first **10** qualifying prospective events:
- no pooled performance claim;
- event-by-event evidence only.

At n >= 10:
- publish descriptive sign agreement, correlations, missingness, and matched-control deltas;
- no threshold/model tuning.

At n >= 20:
- first formal review is permitted, clustered by event;
- compare event sign agreement with the average valid prior/next matched-control agreement;
- report uncertainty intervals and family concentration;
- do not treat repeated same-family events as independent proof of generalization.

Any product promotion still requires:
- prospective separation from matched controls;
- no dependence on one event family;
- source and regional data capability stable enough for operational use;
- explicit product/user-path acceptance;
- a separate authority decision.

## 9. Failure publication law

Every qualifying event must be retained, including:
- wrong-sign transfer;
- no causal confirmation;
- source conflict;
- market-closed;
- regional source outage;
- missing U.S. bars;
- missing HSI anchor/open.

No deletion because an event weakens the thesis.

## 10. Product boundary

Current intended consumer: read-only Narrative Repricing / Historical Analogue surface.

The protocol grants no:
- alert;
- ranking;
- trade;
- sizing;
- portfolio;
- execution;
- automated strategy authority.

The prospective result may eventually inform a read-only `EVENT_CONDITIONED_TRANSFER`
context state. It is not a trade state.
