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


## 4A. Parent-event collapse robustness check

The row-level matched-control comparison above reuses some nearby U.S. control dates at different
frozen clocks. That is valid for the declared same-clock control geometry, but the repeated dates mean
the row-level percentage-point gap should not be read as 20 or 13 fully independent controls.

A post-result robustness pass therefore collapsed the frozen controls back to their parent event:

- each event keeps its binary event sign-agreement result;
- each event's valid prior/next controls are averaged into one parent-level control-agreement rate;
- parents with zero valid controls remain DATA_GAP and are excluded from the paired delta;
- no dates, clocks, returns, or inclusion rules were changed.

All parents with at least one valid matched control:
- parent events: **11**
- mean event agreement: **72.7%**
- mean parent-control agreement: **54.5%**
- mean paired difference: **+18.2 percentage points**
- parent deltas: **4 positive / 4 zero / 3 negative**

Clean-primary parents:
- parent events: **7**
- mean event agreement: **71.4%**
- mean parent-control agreement: **42.9%**
- mean paired difference: **+28.6 percentage points**
- parent deltas: **3 positive / 2 zero / 2 negative**

A fixed-seed parent-level bootstrap was run only as a descriptive fragility check, not as a
confirmatory p-value or promotion test. Its 5th-95th percentile mean-delta interval crossed zero for
both the all-parent and clean-primary slices.

Interpretation:

- collapsing reused control dates reduces the apparent row-level separation;
- the clean-primary event-conditioned relationship still remains directionally stronger than its
  own matched controls;
- the development evidence is **not** strong enough to claim statistical separation or alpha;
- the prospective protocol remains the only legitimate path to promotion.

Do not replace the earlier row-level figures; they answer the declared row-level control question.
This section adds the parent-level dependence correction that a future reviewer needs in order not to
over-read those figures.


## 4B. Session-phase robustness

A secondary structural audit split the already-fixed event and control clocks by the U.S. cash-session
boundary. The split was not optimized: June-September 2026 daylight-time RTH is 13:30-20:00 UTC;
earlier clocks are labeled premarket.

Using the original SMH-minus-QQQ +5->+35 construction:

| Slice | Event agreement | Same-clock control agreement |
|---|---:|---:|
| RTH, all | 5/8 = **62.5%** | 8/16 = **50.0%** |
| RTH, clean-primary | 3/5 = **60.0%** | 4/10 = **40.0%** |
| Premarket, all | 4/4 = **100.0%** | 2/4 = **50.0%** |
| Premarket, clean-primary | 2/2 = **100.0%** | 1/3 = **33.3%** |

The candidate is therefore not exclusively an RTH-clock artifact, but the headline 75% event
agreement is materially helped by a **four-event premarket slice**. That slice is too small to
support a separate premarket hypothesis. No session-specific promotion or threshold is authorized.

## 4C. Cross-asset specificity audit

A second post-outcome diagnostic asked whether the apparent transfer is genuinely
**semiconductor-relative**, or whether the same frozen +5->+35 event windows carry a broader U.S.
growth/risk impulse.

No event, clock, HK outcome, or matched-control date was reselected. The incumbent Massive/Polygon
minute transport was used for SPY, QQQ and SMH at the already-frozen clocks.

### Development events

| U.S. response | All 12 sign agreement | Pearson | Spearman | Clean 7 sign agreement | Clean Pearson | Clean Spearman |
|---|---:|---:|---:|---:|---:|---:|
| SPY absolute | 7/12 = 58.3% | +0.388 | +0.399 | 5/7 = 71.4% | +0.397 | +0.357 |
| QQQ absolute | 8/12 = 66.7% | +0.560 | +0.455 | 6/7 = 85.7% | +0.689 | +0.607 |
| QQQ minus SPY | 10/12 = **83.3%** | +0.530 | +0.525 | 6/7 = **85.7%** | +0.681 | +0.893 |
| SMH minus QQQ | 9/12 = 75.0% | +0.461 | +0.448 | 5/7 = 71.4% | +0.448 | +0.393 |

### Same-clock matched controls

| U.S. response | All controls | Pearson | Spearman | Clean-parent controls | Pearson | Spearman |
|---|---:|---:|---:|---:|---:|---:|
| SPY absolute | 13/23 = 56.5% | -0.176 | -0.242 | 8/14 = 57.1% | -0.288 | -0.385 |
| QQQ absolute | 13/23 = 56.5% | -0.268 | -0.205 | 8/14 = 57.1% | -0.408 | -0.302 |
| QQQ minus SPY | 14/23 = 60.9% | -0.356 | -0.210 | 9/14 = 64.3% | -0.561 | -0.347 |
| SMH minus QQQ | 10/20 = 50.0% | -0.181 | -0.317 | 5/13 = 38.5% | -0.500 | -0.736 |

A standardized two-variable descriptive regression of HSI next-open gap on QQQ absolute and
SMH-minus-QQQ gave the larger coefficient to QQQ in both the full and clean development slices.
This is descriptive only; the sample is too small for model-selection claims.

### Specificity ruling

The development evidence does **not** support calling the surviving relationship a
semiconductor-specific handoff. A better description is:

> during source-resolved geopolitical repricing episodes, the realized U.S. growth/technology
> response relative to the broad market may contain cross-session information about the next
> Hong Kong cash open.

QQQ-minus-SPY was discovered after the development HK outcomes were already visible. It therefore
cannot replace the original SMH-minus-QQQ prospective primary or inherit its historical evidence.
It is admitted only as a **versioned prospective challenger** under
`CROSS_SESSION_TRANSFER_PROSPECTIVE_AMENDMENT_V1_1_2026-09-26.md`.

SPY absolute, QQQ absolute and SMH absolute remain nuisance diagnostics, not additional candidate
families. This freezes the candidate count rather than continuing post-hoc predictor search.

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

> In source-resolved geopolitical repricing episodes, the realized U.S. growth/technology
> response relative to the broad market may contain information about the direction of the next
> Hong Kong cash-session gap beyond ordinary same-clock/non-event moves.

The original SMH-minus-QQQ construction remains the frozen V1 prospective primary for continuity.
The semiconductor-specific interpretation itself is no longer supported. QQQ-minus-SPY is a
post-development challenger only.

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
