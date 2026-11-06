# Cross-Session U.S. -> Hong Kong Transfer — Development Preregistration

Date: 2026-09-26
State: POST-OUTCOME_HYPOTHESIS_FREEZE / DEVELOPMENT_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`
Parent HK result: `research/CROSS_SESSION_DAILY_HANDOFF_HK_RESULTS_2026-09-26.md`
Protected Mastermind pin: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`
Skillpack INDEX blob: `94d1af402598894372858793a5b1931019c5fa77`

## 1. Why this hypothesis exists

The source-selected HK daily handoff diagnostic falsified the simple semantic rule
"relief headline -> positive next HK open" and its escalation mirror.

After those HK outcomes were already observed, an exploratory join was made between the
pre-existing U.S. event response receipts and those already-open HK gaps.

For the 12 events with an available U.S. SMH-minus-QQQ +5->+35 residual and an HSI next-open gap:

- sign agreement: **9/12 = 75.0%**
- Pearson correlation: **0.4612**
- Spearman rank correlation: **0.4476**
- leave-one-event-out sign-agreement range: **72.7% to 81.8%**

For the seven complete primary Wave-1/Wave-2 rows only:

- sign agreement: **5/7 = 71.4%**
- Pearson correlation: **0.4484**
- Spearman rank correlation: **0.3929**

These numbers are explicitly **post-outcome hypothesis generation**. They are not confirmatory
evidence, alpha, a signal, a threshold, or a reason to open the prospective V2 holdout.

Candidate mechanism:

> Once the source event is public, the realized U.S. semiconductor-relative repricing may
> summarize information that the next Asian cash session has not yet assimilated better than
> the original headline polarity does.

## 2. Immediate confound to test before any promotion

The observed relationship may be ordinary cross-market continuation rather than an
event-conditioned effect.

Freeze a broad non-event baseline before reading its U.S. outcomes:

Window:
- 2026-06-14 through 2026-09-24.

Per U.S. trading date d:
- predictor = same-date daily SMH return minus same-date daily QQQ return, in basis points,
  using the incumbent Yahoo transport with `auto_adjust=true`;
- target = HSI close on observed HK session d -> open on the first observed HK session after d,
  in basis points;
- no weekday/calendar approximation beyond observed market bars;
- if an HSI bar does not exist on date d, that U.S. date is not admitted because the
  pre-U.S.-session HK close anchor is unavailable;
- no forward fill.

Primary descriptive controls:
- sign agreement;
- Pearson correlation;
- Spearman rank correlation;
- median HSI next-open gap conditional on positive vs negative U.S. SMH-minus-QQQ daily residual.

This daily control is deliberately broader than the event +5->+35 geometry. It asks whether
the proposed transfer is merely a generic U.S.-tech-to-HK overnight relationship. It is not
a substitute for the stronger matched same-clock intraday control required before promotion.

## 3. Decision law

After the broad daily control is read:

- if the generic baseline is similar to or stronger than the event-conditioned development
  relationship, treat the event-specific transfer hypothesis as **not differentiated**;
- if the generic baseline is materially weaker, retain the event-conditioned hypothesis for
  a stronger same-clock matched-control study;
- no numerical promotion threshold is selected from the already-open event outcomes;
- the prospective V2 holdout remains untouched.

A stronger second-stage control, if still justified, must pre-freeze:
- matched non-event dates;
- exact U.S. clock windows corresponding to each event;
- the same SMH-minus-QQQ +5->+35 geometry;
- target HK open geometry;
- exclusion/contamination rules.

## 4. HK intraday source status

A separate source-capability probe found the incumbent CN/HK AkShare/Eastmoney endpoint can
return 5-minute HK bars. A non-target HSBC canary initially returned 1,386 5-minute bars
from 2026-08-27 09:35 HKT through 2026-09-24 16:00 HKT.

After the candidate HK semiconductor set was frozen in
`research/HK_INTRADAY_HANDOFF_CANDIDATE_SPEC_2026-09-26.json`, all candidate/benchmark
coverage requests failed with `RemoteDisconnected`. A single same-source HSBC canary recheck
then failed identically.

Classification:
- source capability: **observed once**
- current transport state: **transient upstream failure / rate protection suspected, cause unproven**
- target outcomes: **NOT READ**
- persistence: **none**
- retries: **STOPPED**

Do not retry-loop or create a second HK market-data plane from this research PR.

## 5. Authority boundary

Research context only. No score, alert, rank, trade, sizing, portfolio, or execution authority.
