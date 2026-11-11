# Prophet beta-first evaluation — results v1

**Protocol:** `PROTOCOL_HEADER_v1.md` / `protocol_header_v1.json`, sha256 `3be32166…2ada`, committed `07f1c9cd8c` before any outcome access.
**Code:** `engine/prophet_beta_evaluation.py` + `scripts/run_prophet_beta_evaluation.py` at `6fabf196d9` (clean). Seed 20261110, B = 10,000.
**Artifact:** `site/prophet/beta_evaluation.json` (`prophet.beta_evaluation/v1`). Data pin: Macro `b5a5c846f8`, plan snapshot 2026-11-09 (source 2026-11-06).
**Release level achieved: L0 descriptive, for every job.** This is the predeclared cap: the window is 64 sessions (minimum 252) and SPY's deepest drawdown was −5.9% (minimum 8%). The 320 resolved positions met the third condition (minimum 150).

## Answer in plain words

1. **Beta capture (job A).** The incumbent Prophet book stays invested and moves with the market, though somewhat less than one-for-one:
   beta 0.81 (95% CI 0.63–1.14), mean invested weight 100%, upside capture 1.13 (CI 0.56–2.12), downside capture 0.83.
   It made +1.0% while SPY lost −4.6%, a +5.6 pp total difference with CI [−9.9, +23.0] pp. **The interval includes zero and the sample is far too short.**
   The point estimates would pass most job-A criteria. Two fail: the upside-capture CI lower bound and the CI lower bound for non-inferiority.
   The global minimum fails anyway, so job A stays L0.
2. **One name carries the book's lead.** MRNA (+177% on 2026-08-19, on 199M shares) contributed +4.0 pp of the book's +2.7 pp gross daily-sum return.
   Without MRNA the book is +2.1 pp vs SPY, CI [−10.3, +14.8] pp. Without MRNA, the context-aligned Prophet subset falls from +10.7 pp to +1.9 pp vs SPY.
3. **Published plans alone, held without Prophet's exits, lagged the market.** In the policy-free event study (748 published plans, next-bar fill):
   - H = 21 sessions: mean excess vs SPY −2.7 pp, date-cluster CI [−4.8, −0.6], n = 430 over 24 publication dates. Only 35% of plans beat SPY.
     Stock vs own sector ETF was −2.7 pp [−4.0, −1.4]; sector ETF vs SPY was +0.0 pp [−1.5, +1.6].
   - H = 42: −5.7 pp [−9.1, −2.1], n = 258 over 16 dates. Within-sector selection was −4.6 pp; sector was −1.2 pp.
   - H = 10: +0.6 pp [−0.8, +2.0]. H = 63 covers a single publication date and is marked too_few_dates.

   These intervals are likely too narrow: nearby publication dates share overlapping market paths. The direction still differs from the book.
   The book's result depends on Prophet's entry-zone fills and its stop/target exits (plus MRNA), not on its raw picks.
4. **Sector context and member selection did not add value in this window.**
   - Sector rotation (C3): −0.9 pp total vs SPY.
   - Sector-neutral S&P 1500 member momentum (C4): −1.0 pp.
   - The two combined (C5): −3.0 pp.

   None is significant, and every interval is very wide. Lane 8 reported the same direction for sector rotation over a longer window.
5. **Aligned vs independently emerging Prophet plans (K7).** Plans in the leading sectors beat plans outside them: +41.8 pp/yr annualised, CI [−33, +131], Holm p = 1.00.
   This is not significant, and MRNA is its largest contributor. Plans outside leading sectors (C7) were +0.7 pp vs SPY.
6. **Bottom line:** Nothing here shows that sector context or member selection adds value beyond market participation.
   The data cannot establish beta capture either: the book has plausible market exposure, but its excess return is indistinguishable from zero and dominated by one name.

## Headline table (window 2026-08-10 → 2026-11-06, 63 daily returns, net of costs)

| Comparator | Total | vs SPY (total) | 95% CI | Beta [CI] | Up / down capture | Max DD | Turnover/yr |
|---|---|---|---|---|---|---|---|
| C1 Passive SPY | −4.7% | 0.0 | — | 1.00 | 1.00 / 1.00 | −5.9% | 2.0* |
| C2 SPY > 200-day else BIL | −4.7% | 0.0 | — (never left SPY) | 1.00 | 1.00 / 1.00 | −5.9% | 2.0* |
| C3 Sector top-3 | −5.6% | −0.9 pp | [−10.0, +8.8] | 0.63 [0.26, 0.80] | 0.54 / 0.69 | −7.6% | 6.0 |
| C4 Member-only (sector-neutral) | −5.6% | −1.0 pp | [−8.7, +7.7] | 0.83 [0.61, 1.06] | 0.84 / 0.93 | −6.8% | 9.4 |
| C5 Joint sector × member | −7.6% | −3.0 pp | [−14.1, +10.3] | 0.89 [0.59, 1.30] | 0.93 / 1.10 | −11.8% | 9.8 |
| **C6 Incumbent Prophet (as built)** | **+1.0%** | **+5.6 pp** | **[−9.9, +23.0]** | **0.81 [0.63, 1.14]** | **1.13 / 0.83** | −6.5% | 28.1 |
| C7 Prophet outside leading sectors | −3.9% | +0.7 pp | [−13.3, +15.6] | 0.76 [0.59, 0.99] | 0.75 / 0.77 | −8.4% | 28.8 |
| C6A Prophet inside leading sectors | +6.1% | +10.7 pp | [−7.9, +39.7] | 0.88 [0.68, 1.40] | 1.64 / 0.99 | −7.8% | 28.1 |
| X6 SPY/BIL at C6's invested weight | −4.6% | 0.0 | — | 1.00 | — | −5.9% | — |

\*Turnover annualises the initial buy-in. C6 hit rate vs SPY over each position's own holding window: 269/510 = 52.7% (Wilson CI 48.4–57.0%).
At 2× costs C6 is −0.3% total, still +4.3 pp vs SPY.

**Confirmatory family (Holm, α 0.05, one-sided "a beats b"):** no contrast is rejected.
- K1 C6−C1: +23.7 pp/yr, p 0.25.
- K2 C6−X6: +23.6, p 0.25.
- K3 C3−C1: −3.9, p 0.59.
- K4 C4−C1: −3.8, p 0.59.
- K5 C5−C4: −7.6, p 0.64.
- K6 C5−C3: −7.5, p 0.62.
- K7 C6A−C7: +41.8, p 0.16.
- K8 C2−C1: 0.0, p 1.00.

All Holm-adjusted p are 1.00. Block-21 sensitivity and 2× costs change no conclusion.
**Secondary (admission_class strata vs SPY):** patience +31.6 pp/yr (343 positions), confirmation +12.7 (151), early_turn_starter −70.2 (16). Holm p 0.68 / 0.68 / 0.89.

## Attribution bridge (C6; daily arithmetic accounting identity, sector ETFs as segments)

Strategy sum (+1.37) = benchmark (−4.53) + uninvested shortfall (0.00) + sector allocation (+4.44) + selection within sector (+2.77) + cash (0.00) + costs (−1.31), all in pp.
The identity error is 0. The compounding residual of −0.38 pp brings the compounded total to +0.98%.
- C7: sector +6.12, selection −3.97.
- C6A: sector +0.44, selection +12.12 (mostly MRNA).

This is accounting with an equal-weight model book, not a factor decomposition. The selection leg includes stock beta different from one.

## Data limits and biases

- **Sample:** 64 sessions, one regime (a mild decline). No crash or rebound, so the rebound test is not evaluable. Annualised figures from 63 returns are extremely noisy.
- **Plans:** 760 incumbent-era plans, all classified.
  - 510 evaluated positions: 289 exits on the recorded resolution date, 31 on published levels, 190 still open at window end.
  - Excluded: recorded NO_ENTRY 76, zone still live 104, zone expired 22, resolved at/before a follower's fill 34, published after window 12, no close at fill 2.
  - The 34 resolved-before-fill plans are a real selection versus the plan record: a follower could not have held them.
- **Membership:** S&P 1500 point-in-time (start/end dates), but the file has no recorded change after 2026-06-02.
  36 point-in-time members had no price file (≈2.4%, excluded and listed). Theme-basket rosters were not used. macro#10965's PIT basket store begins 2026-08-13 and was not used.
- **Sector labels:** current-basis GICS. The two label sources never disagreed; that does not make them era-correct.
  C4's style weights put zero weight on XLB and XLRE, so C4/C5 hold no Materials or Real Estate names.
- **Fills:** close-only; zone fills at the filled_date close. These are not the plan record's own same-bar outcomes, and `stock_result_pct` was never read.
- **Not evaluable:**
  - The eight catalog sleeves: no plan carries a sleeve link.
  - Issuer-excluded peer counts: listing-ticker identity only.
  - Calibrated forecasts and actual-holdings attribution: no holdings exist.

## Deviations from the header (also in the artifact's `deviations[]`)

- **D1** (before outcomes): reason keys renamed from `ledger_*` to `recorded_*`, because lane 8's validator forbids the substring "edge". Names only.
- **D2** (after outcomes): post-hoc concentration diagnostics added (per-asset contribution, concurrency, leave-top-contributor-out). They are labelled descriptive and cannot change any level.
- **D3:** the final scheduled rule rebalance executes at the last close, and its cost (< 0.1 pp) is not charged.
- **D4:** event-study horizons with fewer than 5 publication dates are marked too_few_dates (H = 63 has one date).

No threshold was changed.

## What the product may truthfully claim today

- It may describe the observed window: "Over 2026-08-10 to 11-06 the model book of published Prophet plans returned +1.0% vs SPY −4.6%, with market sensitivity about 0.8."
  The claim must carry its interval, the single-name concentration and the "descriptive, not validated" label.
- It may not claim beta capture, outperformance, alpha, sector-context value, member-selection value or that following leading sectors helps.

To claim more (L1):
- at least 252 evaluated sessions under this unchanged header hash, including an SPY drawdown of 8% or more;
- the job criteria met with Holm control, robust to 2× costs and to dropping the largest single name;
- for sector/member claims, a point-in-time sector membership source and as-published plan vintages.

Re-running this header after 2026-11-11 accrues prospective sessions; L2 needs a further 126 post-freeze sessions after L1.
