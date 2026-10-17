# Narrative Repricing V2 Preregistration — 2026-09-25

State: PREREGISTERED_RESEARCH / PRODUCTION_INERT / NO_TRADING_AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Parent pilot: research/NARRATIVE_HANDOFF_PILOT_REPLAY_RECEIPT_2026-09-25.md
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924

## 1. Separation from V1

V1 tested a causal-asset threshold followed by a semiconductor response threshold. Its first real replay falsified the simple one-minute oil-leads-semis-lag interpretation at the earliest recovered September 24 public distribution clock.

V2 is a new hypothesis family. It does not rewrite V1, does not reinterpret V1 failures as successes, and does not choose thresholds from the September 24 outcome.

## 2. Hypothesis

Geopolitical Risk-Premium Unwind Continuation:

When a material geopolitical risk premium is already embedded in the oil complex, a genuinely incremental and source-credible relief event can trigger a large causal oil reversal and a synchronized first equity impulse. Conditional on that state, high-beta or geopolitically sensitive equity cohorts may continue repricing after the first impulse has completed.

The proposed edge is therefore second-stage continuation after a validated macro risk-premium unwind, not a claim that oil must lead equities minute by minute.

## 3. Event universe

Build the event manifest from sources and timestamps before looking at outcome returns.

Eligible event families may include:
- ceasefire / hostilities de-escalation;
- sanctions relief or blockade easing;
- credible negotiation breakthrough;
- trade-war de-escalation or tariff truce;
- other geopolitical events with a clearly identified causal commodity/risk-premium channel.

Each event cluster must carry:
- event family;
- exact source identity;
- event_time, available_at, observed_at when available;
- source class and corroboration state;
- narrative direction;
- scheduled/unscheduled flag;
- confounder flags;
- session / region activity state;
- causal-asset mapping declared without outcome knowledge.

Materially identical headlines within six hours remain one cluster unless a later item contains genuinely new information.

## 4. Pre-event feature family

Features are measured strictly before available_at.

Primary pre-event feature families:

### A. Causal risk-premium state
- causal asset return from regular-session open to event;
- causal asset return over trailing 30 and 60 minutes;
- distance from same-session high/low;
- normalized move versus trailing intraday realized volatility;
- optional direct commodity basis when an admitted commodity-minute source exists.

USO may be used only as an explicitly labeled oil-price proxy. It is not WTI/Brent truth.

### B. First-impulse magnitude
- causal asset reversal over the first eligible post-event window;
- broad-index first impulse;
- sector first impulse;
- first-impulse breadth / dispersion where lawful data exists.

The first impulse must be defined from training-only history or a source-independent mechanical rule before development/holdout scoring.

### C. Equity state before event
- sector / basket return versus prior close;
- sector / basket return from regular-session open;
- cross-sectional dispersion;
- single-name damage versus prior close and sector benchmark;
- pre-event realized volatility.

These are interactions, not automatic ranking rules.

## 5. Primary outcome

Primary outcome:
- 30-minute residual return of the declared response cohort versus its benchmark, measured from the mechanically defined end of the first synchronized impulse.

Secondary outcomes:
- 15-minute and 60-minute residual return;
- cohort hit rate;
- cross-sectional dispersion of residual returns;
- tail loss / adverse excursion;
- response persistence after transaction-cost sensitivity.

Do not move the anchor to the causal-confirmation minute merely because that maximizes a historical result. The first-impulse-end rule is part of the preregistration and must be fixed before holdout.

## 6. Cohorts

The first response cohort is semiconductor equities because it motivated the pilot, but promotion evidence cannot depend on one name or one industry.

Semiconductor diagnostics should include a fixed, predeclared universe such as liquid U.S.-listed major semiconductor / equipment names with survivorship-safe membership where available.

Later subfamilies may use other high-beta or duration-sensitive cohorts only if their economic transmission is predeclared.

## 7. Controls

Required controls:
1. Failed-rumor / no-causal-confirmation events.
2. Credible relief events where the causal asset was already moving in the relief direction before the headline.
3. Same-time matched non-event windows.
4. Opposite-direction escalation events where the causal mechanism should reverse sign.
5. Events with causal confirmation but failed equity continuation, including September 14.

Matched-window variables should include time of day, weekday, broad-index pre-event return, causal-asset pre-event return, volatility state, and major scheduled macro-event proximity.

## 8. Dataset split and threshold law

Minimum complete sample target before promotion analysis: 20 independent event clusters, preferably more.

Chronological partition:
- training block: feature engineering and threshold selection only;
- development block: one bounded model/threshold selection pass;
- holdout block: untouched until the family is frozen.

Thresholds for elevated pre-event risk premium, large reversal, and first-impulse completion must be derived only from the training block or from source-independent economic units chosen before outcome inspection.

September 24 may remain in development evidence because it has already been inspected. It must not be treated as unseen holdout evidence.

September 14, July 20, and September 22 have also been inspected and therefore cannot be promoted into an unseen holdout set.

## 9. Statistical honesty

Independent unit = event cluster, not ticker and not headline count.

Required reporting:
- event-clustered bootstrap or equivalent time-cluster-aware uncertainty;
- mean and median residual return;
- positive-rate / hit rate;
- worst-event and tail-loss statistics;
- leave-one-event-out sensitivity;
- results with and without the largest event;
- coverage / missingness;
- matched-control delta;
- transaction-cost / spread sensitivity;
- subgroup results by event family and session state.

No claim of alpha from narrative coherence, one event, or same-day cross-sectional N.

## 10. Promotion bar

Research may recommend a read-only product consumer only if all are true:
- chronological holdout primary effect remains positive;
- matched non-event controls do not reproduce the effect;
- failed-rumor/no-confirmation controls are materially weaker;
- result is not carried by one event, one name, or one calendar period;
- effect survives reasonable transaction-cost sensitivity;
- source-clock ambiguity does not determine the sign;
- direct causal-source substitutions do not reverse the finding where both proxy and direct source are available.

Even then, ranking, alerting, portfolio sizing, and execution remain separate later authority decisions.

## 11. Product mapping if research survives

Read-only product concept: Narrative Repricing Radar.

States:
1. NARRATIVE DETECTED
2. SOURCE CREDIBILITY / NOVELTY ESTABLISHED
3. PRE-EVENT RISK PREMIUM MEASURED
4. CAUSAL ASSET CONFIRMED
5. FIRST IMPULSE COMPLETE
6. SECOND-STAGE REPRICING / NO CONTINUATION
7. THESIS FAILED / DATA GAP

Candidate display fields:
- exact source ladder and clocks;
- pre-event causal risk-premium state;
- causal reversal magnitude and normalized surprise;
- first-impulse completion timestamp;
- response-cohort residual continuation;
- dispersion and damaged-name context;
- historical analogue successes and failures;
- confounders and missingness;
- explicit falsifier.

Authority remains display/research only until a separate accepted promotion wave.

## 12. Exact next action

Construct the source-only event manifest without fetching or calculating post-event outcome returns. Freeze event identities, timestamps, families, causal mappings, and confounders first. Only after that manifest is versioned may training/development outcome extraction begin.
