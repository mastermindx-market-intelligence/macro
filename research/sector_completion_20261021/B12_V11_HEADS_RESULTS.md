# B12 v1.1 — results: four forecast heads + seven comparators

**Protocol:** `B12_V11_HEADS_PROTOCOL.md`, committed at `9a7fbf9e2563` before any result existed.
**Runner:** `b12/v11_heads.py`, written after the protocol. **Result:**
`b12/v11_heads_result.json` (sha256 `cfcfeb2ce7e7fcb8222a935ef3da009a5bd8aba08f4aa19aa3547369bd6e70a9`;
first committed at `3c4a2346f5cb`, re-run after the review fixes below with identical head numbers). **Data:** real tracked `main` parquets `data/yahoo/{XL*,SPY,BIL}`
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
| H2 adverse tail | Brier 0.07676 vs 0.07755 | +0.0102 | [+0.0022, +0.0192] | 0.018 | survives | rate 0.0843, forecast 0.0858, decile slope 0.62 | 12/19 | **QUALIFIED_RESEARCH — fragile** (see adjudication) | withheld · `live_state_not_protocol_epoch` |
| H3 target before invalidation | Brier 0.17446 vs 0.17923 | +0.0267 | [+0.0093, +0.0434] | 0.0035 | survives | rate 0.233, forecast 0.229, decile slope 1.00 | 15/19 | **QUALIFIED_RESEARCH** | withheld · `live_state_not_protocol_epoch` |
| H4 transition time (first-known) | Brier 0.08805 vs 0.09805 | +0.1020 | [+0.0670, +0.1416] | < 0.0005 | survives | rate 0.109, forecast 0.122, decile slope 0.85 | 16/19 | **QUALIFIED_RESEARCH — mostly leg direction** (see adjudication) | withheld · `live_state_not_protocol_epoch` |

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
drifted-weight turnover, BIL on cash. No-entry periods for C3: 1. No-fill signals (a signal on
the last session): 0. Signals filled but not yet mature: 1, not scored.

| | ann. return | vol | excess over cash | max DD (period level) | beta | TE | up / down capture | invested | turnover/yr | costs paid |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 passive market (SPY) | 11.5% | 16.6% | 11.1% | −44.6% | 1.00 | — | 1.00 / 1.00 | 1.00 | 0.00 | 0 |
| C2 simple participation (SPY > 200d) | 9.4% | 11.4% | 8.3% | −17.6% | 0.46 | 12.3% | 0.66 / 0.58 | 0.77 | 1.60 | 1.5% |
| C3 sector allocation only (confirmed up-leg sectors, EW) | 9.7% | 15.5% | 9.3% | −46.4% | 0.87 | 5.9% | 0.86 / 0.86 | 0.996 | 3.41 | 3.2% |
| C3-EW neutral (all sectors EW) | 10.3% | 16.0% | 9.8% | −43.7% | 0.94 | 3.6% | 0.91 / 0.92 | 1.00 | 0.33 | 0.3% |
| C3 exposure-matched reference (w = 0.996 — nearly identical to C3-EW because C3 is almost always fully invested) | 10.2% | 15.9% | 9.8% | −43.6% | 0.93 | 3.6% | 0.91 / 0.92 | 0.996 | — | — |
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
- **Rebounds** (one period per drawdown episode, the next 20 sessions after C1 first reaches −10%;
  an episode ends at a new high): 6 episodes in 2008–2026, 5 with a usable denominator
  (|C1| ≥ 0.5%). Median return ratios against C1: C3 0.72, C2 0.01. Mean period returns: C1 +0.28%,
  C3 −1.11%, C2 +0.10%. Six episodes is too few to read as anything but a description.

**Reading (SP19/SP21/SP22):** the cycle-state sector allocation did not beat the passive market,
or the equal-weight neutral reference, after costs and the exposure match. Whatever difference it
shows disappears under the exposure match, so no selection-value claim is made
(`selection_claim → not_established`). It also holds almost every failed leader, and it does not
find emerging leaders more often than chance. These negative results stay in this document.

## Deviations from the committed protocol (all corrections toward the protocol; head numbers identical in every run)

1. First-run corrections, before the review:
   - No-entry periods are counted on test periods only, as §5 implies.
   - Turnover is measured against drifted weights ("every traded weight change", §5).
   - Failed-leader and emergence counts are restricted to the 2008+ test span.
2. Review corrections:
   - **Calibration slope.** §4 rule 6 asks for a forecast-decile slope; the runner had fitted
     OLS on raw windows. It now uses the decile slope; the raw slope is kept as a diagnostic.
     Decile slopes are 0.62 / 1.00 / 0.85 and all three stay within [0.5, 1.5].
   - **Rebounds.** Now one period per drawdown episode (§5); it was every period spent in
     drawdown.
   - **No-fill vs immature.** The two are counted separately. The old loop could never reach the
     no-fill branch.
3. **Not changed (disclosed).** One random generator is shared in sequence across the four heads,
   then the comparators. Each head's interval therefore depends on the draws before it: it is
   reproducible as a whole, but not one head alone. The year-block percentile interval over 19
   clusters is likely narrow, and the one-sided p is a bootstrap share, not a test under a null
   hypothesis. Changing either now would be a post-result change of method, so neither was
   changed.
4. Capture months are 20-session periods, and maximum drawdown is measured at period level, so
   drawdowns inside a period are not seen.

## Independent review and adjudication (2026-11-10)

**Reviewer:** a native read-only Opus reviewer in a separate context, with no write access.
It reproduced the committed result byte-for-byte (`cmp`), confirmed that the post-run patches
changed no head number, recomputed the BH cut-offs, and found no look-ahead:
- turns come from past bars only;
- the training pool takes only windows matured by *t*;
- sigma20 uses closes through *t*;
- entry is at *t+1*.

It stopped at its turn limit before running its two decisive checks. The lane ran them
itself, and they are now part of the runner as `sensitivity_not_verdict`; they never feed a
verdict.

| item | reviewer verdict | lane adjudication |
|---|---|---|
| H1 remaining-return distribution | UPHELD (fails on skill alone; band 0.769 is fine) | **WITHHELD_FAILED stands.** It is also no better than direction-only (−0.24%) or age-only (−0.08%) states. |
| H2 adverse tail | UPHELD-WITH-NOTES, provisional: fragile — skill 1.0%, CI lower bound 0.002, 12/19 years against an 11.4-year bar; the 0.03 calibration gap is loose at a 0.084 base rate | **QUALIFIED_RESEARCH under the protocol as committed, flagged fragile.** Direction-only earns 0.32% and age-only 0.27% against climatology. The full state adds 0.70% over direction-only. This head must not be wired to any record without a fresh preregistered confirmation on later data. |
| H3 target before invalidation | UPHELD-WITH-NOTES, provisional: no direction-only comparison | **QUALIFIED_RESEARCH.** Direction-only earns 1.52% of the 2.67%; the full state adds 1.16% over direction-only and 2.51% over age-only. Most of the head is leg direction plus age, and its wording must say so. |
| H4 transition time | UPHELD-WITH-NOTES, provisional: is it mechanical? | **QUALIFIED_RESEARCH, and mostly leg direction.** Direction-only reaches 9.28% of the 10.2%; age adds 1.0%. Observed rate of a new turn first-known within 20 sessions, by cell: up/A1 0.15, up/A2 0.05, up/A3 0.06, down/A1 0.45, down/A2 0.26, down/A3 0.31. That is a real but basic fact: confirmed down legs in these ETFs flip faster than up legs. It is not a timing model, and historical duration is not remaining upside. |
| current-MODEL hazard gate | UPHELD-WITH-NOTES: no path emits a MODEL or PRIOR number on Sector Cycles | **Upheld.** Docstring nit fixed. The ungated callers are outside this lane: see the request below. |
| M2: research statistics on every live record | finding | **Fixed.** A record's head now carries only `status`, `reason_code`, `research_disposition`, `research_reasons`, target text, horizon, market and an evidence pointer. `test_every_head_is_present_and_withheld_with_its_own_reason` and `test_live_sector_build_emits_forecast_heads_all_withheld` now fail if any number other than the horizon appears. |
| m7: wrong reason for non-sector kinds | finding | **Fixed.** Kinds other than sector and basket get `record_kind_not_evaluated`: `test_other_record_kinds_are_not_evaluated_not_mislabelled`. |
| m2/m4/m5 (calibration, no-fill, rebounds) | findings | **Fixed** toward the protocol (Deviations 2). |
| m3: bootstrap dependence and shared generator | finding | **Disclosed, not changed** (Deviations 3). |
| M1: ungated `hazard_score.score()` in `scripts/build_cycle.py:140-143,182` and `engine/commodity_cycle_state.py:134-136` | finding | **OPEN, outside this lane.** Those callers still emit 1m/3m/6m cells, including the row-weighted PRIOR, which B12 Q9 rules NO-GO as a displayed probability. Routed to their owners as a request. |

**Bottom line:**
- No head emits a number today.
- H1 is withheld because it failed.
- H2, H3 and H4 pass the research bar for US SPDR sectors on the v2 epoch. They are still withheld
  on every live record (`live_state_not_protocol_epoch`), because the live turn state is not that
  epoch.
- H2 is fragile.
- H3's and H4's skill is largely leg direction: true, but basic. A UI must describe them that
  way, never as a cycle-timing edge.
- Not covered by the review: the reviewer's own leave-one-year-out run, the 2008/2020 contribution
  and other H2 thresholds.
