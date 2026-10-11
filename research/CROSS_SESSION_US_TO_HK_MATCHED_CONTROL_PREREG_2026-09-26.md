# Cross-Session U.S. -> Hong Kong Transfer — Matched Intraday Control Preregistration

Date: 2026-09-26
State: DEVELOPMENT_CONTROL_FREEZE / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`
Parent prereg: `research/CROSS_SESSION_US_TO_HK_TRANSFER_PREREG_2026-09-26.md`
Protected Mastermind pin: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`

## 1. Trigger

The post-outcome event join showed:
- all overlapping measured rows: 9/12 sign agreement, Pearson 0.4612, Spearman 0.4476;
- complete primary Wave-1/2 rows: 5/7 sign agreement, Pearson 0.4484, Spearman 0.3929.

The pre-frozen broad daily control then showed, across 66 ordinary U.S./HK session pairs:
- sign agreement: 25/66 = 37.9%;
- Pearson: -0.2204;
- Spearman: -0.1859;
- median next-HSI-open gap after a positive daily SMH-minus-QQQ residual: -7.36 bp;
- median after a negative daily SMH-minus-QQQ residual: +21.21 bp.

Therefore generic same-day U.S. semiconductor-relative momentum does not explain the
event-conditioned development relationship in this window.

This remains hypothesis generation because the event relationship was discovered after HSI
outcomes were opened.

## 2. Matched-control selection law

Event rows are the 12 already-measured source events for which both:
- a U.S. SMH-minus-QQQ +5->+35 residual is already recorded in the frozen Wave receipts; and
- an HSI next-open gap is already recorded in the HK advisory result.

No additional event is added because of its outcome.

For every event row e:

1. Let d be the U.S. calendar date of e.available_at.
2. Let t be the exact UTC time-of-day of e.available_at.
3. Construct the eligible U.S. session calendar from observed SMH daily bars only.
4. Exclude every calendar date appearing in the frozen cross-session source census, regardless
   of that source event's direction, quality, or eventual outcome.
5. Select:
   - the nearest eligible observed U.S. session strictly before d;
   - the nearest eligible observed U.S. session strictly after d.
6. Require each control to be within 10 observed U.S. sessions of d. Otherwise return DATA_GAP.
7. Reuse the event's exact UTC time-of-day t on the control date. Do not shift to a liquid bar,
   U.S. open, close, or another headline clock.
8. Duplicate (control_date, t) pairs produced by multiple event rows are measured once and
   referenced by all parent event rows.

This selection uses dates and frozen source-corpus membership only. No U.S. intraday return or
HK gap is inspected to choose a control.

## 3. Matched-control measurement

U.S. source:
- incumbent Massive/Polygon U.S.-stocks minute aggregate entitlement;
- same one-minute endpoint and PIT timestamp semantics already used by PR #8012;
- zero minute-data persistence.

For each matched (control_date, t):
- response = SMH;
- benchmark = QQQ;
- start target = t + 5 minutes;
- end target = t + 35 minutes;
- minute close is known at vendor minute-start + 60 seconds;
- use the existing bounded pre/post tolerance law;
- residual = SMH return(start->end) - QQQ return(start->end);
- missing start/end bar => DATA_GAP; never re-anchor.

HK target:
- HSI observed close on control_date -> first observed later HSI open;
- same incumbent Yahoo `auto_adjust=true` geometry used by the already-open HK advisory result;
- no forward fill.

## 4. Frozen descriptive comparisons

Compare event rows vs matched non-event controls using only:

- sign agreement between U.S. residual and HSI next-open gap;
- Pearson and Spearman correlations;
- median HSI gap conditional on U.S. residual sign;
- event-minus-control differences in those descriptive quantities;
- exact missingness counts.

Report both:
- all 12 development event rows;
- the seven complete primary Wave-1/Wave-2 rows.

No p-value or threshold is selected from this small development set.

## 5. Decision law

- If matched controls show a relationship similar to the event rows, classify the candidate
  transfer as generic clock/session structure, not event-specific.
- If matched controls are materially weaker, retain **EVENT_CONDITIONED_TRANSFER** as a
  prospective hypothesis only.
- Do not open the existing V2 prospective holdout.
- Any promotion requires a new future-event prospective sample frozen before HK outcomes,
  plus stable regional data capability.
- No score, rank, alert, sizing, trade, portfolio, or execution authority is granted.
