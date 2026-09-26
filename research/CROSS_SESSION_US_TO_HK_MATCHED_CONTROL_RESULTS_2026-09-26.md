# Cross-Session U.S. -> Hong Kong Transfer — Matched Control Results

Date: 2026-09-26
State: DEVELOPMENT_EVIDENCE / POST-OUTCOME_HYPOTHESIS / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / `sol/geopolitical-relief-event-study-20260924`
Prereg: `research/CROSS_SESSION_US_TO_HK_MATCHED_CONTROL_PREREG_2026-09-26.md`
Frozen controls: `research/CROSS_SESSION_US_HK_MATCHED_CONTROL_MANIFEST_2026-09-26.json`
Protected Mastermind pin: `763ec8f920177fdf48b18df1b8e37b61ab482ef0`

## 1. Evidence boundary

This is a development result for a hypothesis discovered only after the HSI event outcomes
had already been opened. It cannot be confirmatory evidence.

The matched-control dates and exact UTC clocks were frozen before the control intraday returns
were read. Controls were selected solely by:
- nearest prior / next observed SMH session;
- exclusion of every date present in the frozen source census;
- <=10 observed-session distance;
- reuse of the parent event's exact UTC time-of-day.

No control was selected by return sign or magnitude.

U.S. controls used the incumbent Massive/Polygon one-minute stock aggregates with the same
minute-close-known-at +60s semantics already used by the event study. No minute data was
persisted.

HK outcomes used the incumbent Yahoo HSI daily Open/Close geometry with `auto_adjust=true`
and no persistence.

## 2. Development event relationship already observed

All 12 overlapping measured event rows:
- n = 12
- U.S. SMH-minus-QQQ +5->+35 residual / next-HSI-open sign agreement = **9/12 = 75.0%**
- Pearson = **+0.4612**
- Spearman = **+0.4476**
- leave-one-event-out sign-agreement range = **72.7% to 81.8%**

Seven complete primary Wave-1/Wave-2 rows:
- n = 7
- sign agreement = **5/7 = 71.4%**
- Pearson = **+0.4484**
- Spearman = **+0.3929**

Again: these event statistics were discovered after the HSI outcomes were opened.

## 3. Broad daily non-event control

The separately pre-frozen broad control used ordinary same-date daily SMH-minus-QQQ return
versus the next HSI open across 66 U.S./HK session pairs:

- sign agreement = **25/66 = 37.9%**
- Pearson = **-0.2204**
- Spearman = **-0.1859**
- median next-HSI-open gap when U.S. daily residual > 0 = **-7.36 bp**
- median next-HSI-open gap when U.S. daily residual < 0 = **+21.21 bp**

Generic daily U.S. semiconductor-relative momentum therefore did not explain the event result
in this window.

## 4. Same-clock matched non-event controls

Requested matched-control rows: **24**  
Unique U.S. control sessions fetched: **16**  
Complete U.S.-intraday + HSI pairs: **20**  
Honest data gaps: **4**

All complete matched controls:
- n = **20**
- sign agreement = **10/20 = 50.0%**
- Pearson = **-0.1805**
- Spearman = **-0.3169**
- median HSI gap when matched U.S. residual > 0 = **+23.56 bp**
- median HSI gap when matched U.S. residual < 0 = **+31.37 bp**

Controls corresponding to the seven clean-primary parent events:
- complete control rows n = **13**
- sign agreement = **5/13 = 38.5%**
- Pearson = **-0.4996**
- Spearman = **-0.7358**
- median HSI gap when matched U.S. residual > 0 = **+23.56 bp**
- median HSI gap when matched U.S. residual < 0 = **+31.37 bp**

Descriptive event-minus-control separation:
- all-row sign agreement: **+25.0 percentage points** (75.0% event vs 50.0% matched control)
- clean-primary sign agreement: **+32.9 percentage points** (71.4% event vs 38.5% matched control)

Do not convert the correlation differences into a significance statistic. Several controls
share U.S. dates and HSI target gaps at different frozen clocks, so observations are not
independent.

## 5. Missingness

Four pre-frozen matched controls remained missing under the exact-clock law:

- 2026-09-21 09:14Z: U.S. residual DATA_GAP
- 2026-09-25 09:14Z: U.S. residual DATA_GAP and next HSI open not yet observable
- 2026-06-18 10:47Z: U.S. residual DATA_GAP
- 2026-07-31 09:14Z: U.S. residual DATA_GAP

No clock was moved to a later liquid bar.

## 6. Current interpretation

The original story has changed materially.

Unsupported / falsified:
- a clean one-minute "oil leads semis" lag;
- headline polarity by itself;
- oil confirmation by itself;
- generic post-Asia-close headline direction -> next HSI open direction;
- generic daily U.S. semiconductor-relative momentum -> next HSI open.

Still alive as a **prospective hypothesis only**:

> In source-resolved geopolitical repricing episodes, the realized U.S.
> semiconductor-relative response may contain information about the direction of the next
> Hong Kong cash-session gap that is not present in ordinary same-clock/non-event U.S.
> semiconductor moves.

The development sample is small, concentrated in the 2026 Iran/Hormuz complex, and the
hypothesis was discovered after event HSI outcomes were opened. The matched controls reduce
two obvious confounds but do not establish causality, generalization, or economic
tradability.

## 7. Product consequence

The read-only evidence-state / analogue layer should preserve separate fields for:

- source/narrative state;
- causal-asset confirmation/rejection;
- U.S. first impulse;
- U.S. +5->+35 sector-relative continuation;
- cross-session transfer candidate;
- target-region assimilation observed/not observed/data gap;
- contamination/conflict;
- analogue-family concentration.

No downstream layer may translate `EVENT_CONDITIONED_TRANSFER` into a trade state before a
prospective sample survives.

## 8. Next gate

Freeze a new **future-event prospective cross-session transfer protocol** before any future
HK outcome is read. Do not open or repurpose the existing V2 prospective holdout.

The future protocol must:
- use source clocks as observed;
- compute U.S. response with the already-frozen +5->+35 geometry;
- record the next HSI open before any tuning;
- predeclare event-family inclusion and contamination handling;
- keep matched controls;
- keep regional first-5m as a separate capability-gated endpoint;
- publish every qualifying future event, including failures and data gaps.

No score, alert, ranking, sizing, trade, portfolio, or execution authority is granted.
