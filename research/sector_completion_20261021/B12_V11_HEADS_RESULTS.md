# B12 v1.1 — results: four forecast heads + seven comparators

**Protocol:** `B12_V11_HEADS_PROTOCOL.md`, committed at `9a7fbf9e2563` before any result existed.
**Runner:** `b12/v11_heads.py`, written after the protocol. **Result:**
`b12/v11_heads_result.json` (sha256 `06d02d66a1662638cb81735abc54f928a7e670428002e0b3d69419008e5b69b4`),
first committed at `3c4a2346f5cb`. **Data:** real tracked `main` parquets `data/yahoo/{XL*,SPY,BIL}`
(the result JSON stores each tape's sha256). No synthetic value feeds any number here.

**Reproduce:** `python3 research/sector_completion_20261021/b12/v11_heads.py --tape-dir <dir with data/yahoo> --out out.json`
(deterministic; about 2.5 minutes; research only, off the render path).

Nothing below ranks, gates, sizes, trades or escalates. Raw relative strength is not estimated
alpha. Positive selection contribution is not evidence of portfolio skill. Historical duration is
not remaining upside. The historical W4.2 4/6 verdict is not an input and authorizes nothing here.

## PIT check

`detect_turns` on the tape truncated at every decision date returned exactly the full-tape turns
with `confirmed_at <= t` (dates, kinds and confirmations) on all 3,130 decision dates
(9 ETFs × 326, XLRE 115, XLC 81). Event date (pivot) and first-known date (`confirmed_at`)
stay separate. H4 is scored on `confirmed_at`.

## Per-head disposition (US SPDR sectors, 20-session horizon, test 2008-01 → 2026-09)

2,318 test windows; 2,300 scored (coverage 0.992); 430 decision dates; 19 years. Leave-one-sector-out
and time-respecting: a forecast for ETF *s* at *t* is fitted only on the other ten ETFs' windows
that matured by *t*. Baseline = the same pool, unconditional. Uncertainty: year-block bootstrap
(2,000 draws, seed 11). BH-FDR q = 0.10 over the four primary tests.

| head | score: model vs baseline | skill | CI90 | p (one-sided) | BH | calibration | years positive | research disposition | emitted |
|---|---|---|---|---|---|---|---|---|---|
| H1 remaining-return distribution | pinball 0.009621 vs 0.009615 | −0.0006 | [−0.0075, +0.0058] | 0.562 | fails | q10–q90 band holds 0.769 (ok) | 9/19 | **WITHHELD_FAILED**: CI includes 0, fails BH, < 60% of years | withheld · `research_withheld_failed` |
| H2 adverse tail | Brier 0.07676 vs 0.07755 | +0.0102 | [+0.0022, +0.0192] | 0.018 | survives | rate 0.0843, forecast 0.0858, slope 0.73 | 12/19 | **QUALIFIED_RESEARCH** (pending review, below) | withheld · `live_state_not_protocol_epoch` |
| H3 target before invalidation | Brier 0.17446 vs 0.17923 | +0.0267 | [+0.0093, +0.0434] | 0.0035 | survives | rate 0.233, forecast 0.229, slope 0.99 | 15/19 | **QUALIFIED_RESEARCH** (pending review) | withheld · `live_state_not_protocol_epoch` |
| H4 transition time (first-known) | Brier 0.08805 vs 0.09805 | +0.1020 | [+0.0670, +0.1416] | < 0.0005 | survives | rate 0.109, forecast 0.122, slope 0.87 | 16/19 | **QUALIFIED_RESEARCH** (pending review) | withheld · `live_state_not_protocol_epoch` |

Scored windows by cell: up/A1 217, up/A2 496, up/A3 1,215, down/A1 119, down/A2 198, down/A3 55.

**What "QUALIFIED_RESEARCH" covers:** the stated target (see `engine/sector_heads.py::TARGETS`)
for US SPDR sector ETFs, with the state taken from ZigZag v2 at 14% on `close_price` (epoch
`price_c4414dcb`), at a 20-session horizon after a next-close entry. It does not cover the live
Sector Cycles record: that record uses the legacy v1 detector and has no epoch. It also does not
cover baskets or amalgams (`membership_not_point_in_time`), HK or CN (`market_not_evaluated`),
or any other horizon. A research-qualified head emits no number until a live record carries the
protocol state and an estimator is wired to it. The skill is measured against climatology, not
against a direction-only or age-only model. See the review for whether it is the cycle state or
something simpler that earns it.

## Seven comparators (descriptive economic evaluation; not a qualification)

236 twenty-session periods, 2008-01 → 2026-09. Next-close execution, 5 bp per side on
drifted-weight turnover, BIL on cash. No-entry periods for C3: 1. No-fill signals: 0.

| | ann. return | vol | excess over cash | max DD (period level) | beta | TE | up / down capture | invested | turnover/yr | costs paid |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 passive market (SPY) | 11.5% | 16.6% | 11.1% | −44.6% | 1.00 | — | 1.00 / 1.00 | 1.00 | 0.00 | 0 |
| C2 simple participation (SPY > 200d) | 9.4% | 11.4% | 8.3% | −17.6% | 0.46 | 12.3% | 0.66 / 0.58 | 0.77 | 1.60 | 1.5% |
| C3 sector allocation only (confirmed up-leg sectors, EW) | 9.7% | 15.5% | 9.3% | −46.4% | 0.87 | 5.9% | 0.86 / 0.86 | 0.996 | 3.41 | 3.2% |
| C3-EW neutral (all sectors EW) | 10.3% | 16.0% | 9.8% | −43.7% | 0.94 | 3.6% | 0.91 / 0.92 | 1.00 | 0.33 | 0.3% |
| C3 exposure-matched reference (w = 0.996) | 10.2% | 15.9% | 9.8% | −43.6% | 0.93 | 3.6% | 0.91 / 0.92 | 0.996 | — | — |
| C4 member selection only | `unavailable: no_pit_constituent_membership` (today's holdings would be survivorship-biased) |||||||||
| C5 joint sector and name | `unavailable: no_pit_constituent_membership` |||||||||
| C6 exact incumbent Prophet | `unavailable: incumbent_record_not_in_lane_scope` (Terminal/Prophet owner) |||||||||

Differences (annualized, year-block CI90): C3 − C1 −1.82% [−3.54%, +0.05%]; C3 − exposure-matched
−0.53% [−1.73%, +0.59%]; C3 − C3-EW −0.57% [−1.74%, +0.50%]; C2 − C1 −2.73% [−6.87%, +2.35%].

- **C7 independent emergence:** 493 emergers (outside the trailing-63 top 3 at *t*, inside the
  next-63 top 3). C3 held 76.1% of them, against 78.3% of all non-top-3 sectors. That is no
  better than the base rate.
- **Failed leaders:** 326 trailing top-3 sectors finished in the bottom half over the next 20
  sessions. C3 held 93.6% of them.
- **Rebounds:** 67 periods after a ≥ 10% C1 drawdown, 61 with a usable denominator. Median
  return ratios against C1: C3 0.93, C2 0.04. Mean period returns: C1 1.22%, C3 1.08%, C2 0.75%.

**Reading (SP19/SP21/SP22):** the cycle-state sector allocation did not beat the passive market,
or the equal-weight neutral reference, after costs and the exposure match. Whatever difference it
shows disappears under the exposure match, so no selection-value claim is made
(`selection_claim → not_established`). It also holds almost every failed leader, and it does not
find emerging leaders more often than chance. These negative results stay in this document.

## Deviations from the committed protocol

1. After the first run, and before any head verdict changed, the runner was corrected in three
   places. No-entry periods are now counted on test periods only, as §5 implies. Turnover is now
   measured against drifted weights ("every traded weight change", §5). Failed-leader and
   emergence counts are now restricted to the 2008+ test span. The head numbers were identical
   across all three runs.
2. Capture months are 20-session periods, and maximum drawdown is measured at period level
   (intra-period drawdowns are not seen). Both are disclosed in the table headings.

## Independent review and adjudication

_(pending — filled from the reviewer's verdict)_
