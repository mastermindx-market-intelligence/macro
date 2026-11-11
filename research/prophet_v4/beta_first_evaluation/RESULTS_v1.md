# Prophet beta-first evaluation — results v1 (corrected)

**Protocol:** `PROTOCOL_HEADER_v1.md` / `protocol_header_v1.json`, sha256 `3be32166…2ada`, committed `07f1c9cd8c` before any outcome access. The header is unchanged.
**Code:** `engine/prophet_beta_evaluation.py` + `scripts/run_prophet_beta_evaluation.py` at this commit. Seed 20261110, B = 10,000.
**Artifact:** `site/prophet/beta_evaluation.json` (`prophet.beta_evaluation/v1`). Data pin: Macro `b5a5c846f8`, plan snapshot 2026-11-09 (source 2026-11-06).
**Renewal:** the artifact is frozen evidence — no scheduled job regenerates it. It changes only by a deliberate rerun of `scripts/run_prophet_beta_evaluation.py`, committed with its review (exact command: "How to rerun" in `ARTIFACT_CONTRACT_v1.md`).
**Release level achieved: L0 descriptive, for every job.** This is the predeclared cap: the window is 64 sessions (minimum 252) and SPY's deepest drawdown was −5.9% (minimum 8%). The 308 resolved positions met the third condition (minimum 150).

## Population correction (deviation D5) — read this first

The originally published v1 numbers treated 16 outage-reconstructed plans as if they had been published historically.
They had not been. Thirteen replay the receipted 2026-08-09 bake but were instantiated at 2026-08-11T05:32Z;
three (HCC, LNG, NXPI) were reconstructed on 2026-08-13T13:31Z from a 2026-08-11 board that was never published.
`MRNA-BULL-20260616` entered at the 2026-08-10 close — before it existed for any user.
*(Census clarified 2026-11-11, adjudication finding 12: "16" is the incumbent-era count. Across all eras 17
outage-backfill plans were minted — 14 receipted replays and 3 reconstructions; RIO-BULL-20260731 sits outside
the incumbent era and was never eligible for this book. The artifact's `population.excluded_cohort` now carries
both counts.)*

This corrects the population to what the header's own word "published" means: **live-published plans only**.
It is a rule that predates the evaluation (`research/PROPHET_OUTAGE_BACKFILL_2026_08.md`: a reconstructed pick may
never be presented as a live historical call), applied after outcomes were seen, and it **lowers** the headline.
The excluded cohort is detected from the data (`origination_mode`, `backfill_executed_at`, the backfill disclosure
receipts) — never a hard-coded id list — and the run now refuses to start if those sources disagree.
Nothing is hidden: the superseded as-run numbers are retained verbatim in `sensitivity.superseded_as_run`,
and sensitivity (a) admits the 13 receipted replays only from their actual availability.

Source: independent scientific review `REVIEW_beta_evaluation.md`
(sha256 `6296bf4cb77d09e47f1311dbd46cd915a794e050ce7460a228ad821e7b13541a`), BLOCKER finding, accepted by the programme CEO.

**What changed in one line: C6 goes from +1.0% (+5.6 pp vs SPY) to −3.1% (+1.5 pp vs SPY), 95% CI [−10.5, +13.4].**

## Answer in plain words

1. **Beta capture (job A).** The incumbent Prophet book of live-published plans stays invested and moves with the
   market, though less than one-for-one: beta 0.79 (95% CI 0.63–1.08), mean invested weight 98%, upside capture 0.93
   (CI 0.53–1.55), downside capture 0.88. It lost −3.1% while SPY lost −4.7%: a +1.5 pp total difference with CI
   [−10.5, +13.4] pp. **The interval includes zero: this is not evidence of outperformance, and the sample is far too
   short.** Three job-A point criteria now fail: beta below 0.8, the upside-capture CI lower bound, and the CI lower
   bound for non-inferiority. The global minimum fails anyway, so job A stays L0.
2. **The book's lead is small and not one-name-proof, but the famous name is gone.** MRNA is no longer in the book
   (it was a reconstruction). *(Corrected 2026-11-11, adjudication finding 12: MRNA-BULL-20260616 is a receipted
   replay of the 2026-08-09 bake — origination_mode outage_backfill_2026_08_09, instantiated 2026-08-11T05:32:28Z —
   not a synthetic-board reconstruction. The exclusion is unchanged; only the label was wrong.)* The largest
   remaining contributor is AMR (+0.8 pp gross); without it the book is
   +0.8 pp vs SPY, CI [−10.7, +12.1]. In sensitivity (a), where the 13 replays are admitted from their actual
   availability, MRNA re-enters at the 2026-08-11 close and the book returns to +0.1% (+4.7 pp vs SPY,
   CI [−10.2, +21.4]) — still not significant, and resting on the same single move.
3. **Live-published plans held without Prophet's exits lagged the market.** In the policy-free event study
   (732 published plans, next-bar fill):
   - H = 21 sessions: mean excess vs SPY −3.0 pp, date-cluster CI [−5.1, −0.9], n = 414 over 22 publication dates.
     Only 34.5% of plans beat SPY. Stock vs own sector ETF was −3.0 pp [−4.2, −1.9]; sector ETF vs SPY was +0.0 pp
     [−1.6, +1.6].
   - H = 42: −6.6 pp [−9.8, −3.2], n = 242 over 14 dates. Within-sector selection was −5.4 pp; sector was −1.2 pp.
   - H = 10: +0.4 pp [−1.0, +1.7], n = 609 over 28 dates. H = 63 no longer matures for any plan and is marked
     unmatured (its only mature cohort was the 2026-08-10 reconstructions).

   These intervals are likely too narrow: nearby publication dates share overlapping market paths.
   The event study and the managed book are two different descriptive constructions: they differ in cohort
   (all published plans versus entered-and-held), timing, weighting, exits and censoring. Because they differ on
   all of these at once, their different outcomes cannot be attributed to fills, exits or any single mechanism.
   A matched-cohort counterfactual that changes one rule at a time would be needed for a causal statement.
4. **Sector context and member selection did not beat SPY on this window.**
   - Sector rotation (C3): −0.9 pp total vs SPY.
   - Sector-neutral S&P 1500 member momentum (C4): −1.0 pp.
   - The two combined (C5): −3.0 pp.

   None is significant and every interval is very wide. **Insignificant means value is not shown, not that there is
   none.** Lane 8 reported the same direction for sector rotation over a longer window.
5. **Aligned vs independently emerging Prophet plans (K7).** Plans in the leading sectors did better than plans
   outside them: +11.7 pp/yr annualised, total +2.8 pp, CI [−9.7, +15.0], Holm p = 1.00. Not significant; the
   interval spans zero by a wide margin.
6. **X6 is an arithmetic reference, not a selection test.** The book is ~98% invested, so the "exposure-matched"
   SPY/BIL reference nearly repeats SPY itself and K2 nearly repeats K1. **K2 cannot identify member-selection
   value, and an insignificant K2/K4/K6 establishes nothing about the absence of value.** A comparator matched on
   eligible cohort, concentration, sector/factor exposure, timing and costs belongs to a new pre-declared protocol
   (below); it was deliberately not substituted here after seeing results.
7. **Bottom line:** Nothing here shows that sector context or member selection adds value beyond market
   participation. The data cannot establish beta capture either: the book has plausible market exposure, but its
   excess return is indistinguishable from zero, and the corrected point estimate is negative.

## Headline table (window 2026-08-10 → 2026-11-06, 63 daily returns, net of costs, live-published plans only)

| Comparator | Total | vs SPY (total) | 95% CI | Beta [CI] | Up / down capture | Max DD | Turnover/yr |
|---|---|---|---|---|---|---|---|
| C1 Passive SPY | −4.7% | 0.0 | — | 1.00 | 1.00 / 1.00 | −5.9% | 2.0* |
| C2 SPY > 200-day else BIL | −4.7% | 0.0 | — (never left SPY) | 1.00 | 1.00 / 1.00 | −5.9% | 2.0* |
| C3 Sector top-3 | −5.6% | −0.9 pp | [−10.0, +8.8] | 0.63 [0.26, 0.80] | 0.54 / 0.69 | −7.6% | 6.0 |
| C4 Member-only (sector-neutral) | −5.6% | −1.0 pp | [−8.7, +7.7] | 0.83 [0.61, 1.06] | 0.84 / 0.93 | −6.8% | 9.4 |
| C5 Joint sector × member | −7.6% | −3.0 pp | [−14.1, +10.3] | 0.89 [0.59, 1.30] | 0.93 / 1.10 | −11.8% | 9.8 |
| **C6 Incumbent Prophet (as built, live-published)** | **−3.1%** | **+1.5 pp** | **[−10.5, +13.4]** | **0.79 [0.63, 1.08]** | **0.93 / 0.88** | −6.6% | 25.6 |
| C7 Prophet outside leading sectors | −4.8% | −0.2 pp | [−13.5, +13.6] | 0.77 [0.59, 1.01] | 0.77 / 0.83 | −8.3% | 27.5 |
| C6A Prophet inside leading sectors | −2.1% | +2.6 pp | [−8.8, +15.5] | 0.83 [0.66, 1.24] | 1.18 / 1.01 | −8.1% | 24.6 |
| X6 Exposure-weight arithmetic reference (SPY/BIL at C6's invested weight) | −4.3% | +0.3 pp | [−0.0, +0.9] | 1.00 | 1.00 / 0.98 | −5.9% | — |

\*Turnover annualises the initial buy-in. C6 hit rate vs SPY over each position's own holding window: 265/498 = 53.2%
(Wilson CI 48.8–57.6%). At 2× costs C6 is −4.3% total, +1.7 pp/yr vs SPY (point estimate; CI lower bound −43.5 pp/yr).
X6 is a reference row (no costs) and is not a member-selection test (see plain words 6).

**Confirmatory family (Holm, α 0.05, one-sided "a beats b"):** no contrast is rejected.
- K1 C6−C1: +6.6 pp/yr, p_raw 0.41, total +1.5 pp [−10.5, +13.5].
- K2 C6−X6: +5.1, p_raw 0.43. Nearly a repeat of K1 (see plain words 6); identifies nothing about selection.
- K3 C3−C1: −3.9, p_raw 0.58.
- K4 C4−C1: −3.8, p_raw 0.59.
- K5 C5−C4: −7.6, p_raw 0.64.
- K6 C5−C3: −7.5, p_raw 0.62.
- K7 C6A−C7: +11.7, p_raw 0.33, total +2.8 pp [−9.7, +15.0].
- K8 C2−C1: 0.0, p_raw 1.00.

All Holm-adjusted p are 1.00. Block-21 sensitivity and 2× costs change no conclusion.
**Secondary (admission_class strata vs SPY):** patience +8.7 pp/yr (331 positions), confirmation +12.7 (151),
early_turn_starter −70.2 (16). Holm p 0.98 / 0.98 / 0.98.

## Attribution bridge (C6; daily arithmetic accounting identity, sector ETFs as segments)

Strategy sum (−2.92 pp) = benchmark (−4.53) + uninvested market shortfall (+0.32) + sector allocation (+3.99)
+ selection within sector (−1.53) + cash (+0.01) + costs (−1.18). The identity error is 0. The compounding
residual of −0.22 pp brings the compounded total to −3.14%.
- C7: sector +5.88, selection −5.06.
- C6A: sector +0.28, selection +3.32 (largest single leg; TEM and CRCL dominate).

This is accounting with an equal-weight model book, not a factor decomposition. The selection leg includes stock
beta different from one.

## Sensitivity blocks (separately labelled — never the headline)

**(a) Receipted replays admitted from their actual availability.** The 13 replayed plans enter from the first
session at/after their `backfill_executed_at` (2026-08-11); the 3 synthetic-board reconstructions are never
admitted. Book: 509 positions, +0.1% total, +4.7 pp vs SPY, CI [−10.2, +21.4], beta 0.82, mean invested 98.4%,
hit rate 268/509. MRNA re-enters at the 2026-08-11 close and again dominates: this variant shows how much of the
as-run lead depended on plans that no user could see on their nominal dates. It is a counterfactual labelled as
such, not a backtest.

**(b) Superseded as-run numbers (retained verbatim so nothing is hidden).** Same engine, seed, prices and costs;
only the population differs (the 16 reconstructions included as if published):

| Measure | As run (superseded) | Corrected primary |
|---|---|---|
| C6 total | +0.98% | −3.14% |
| C6 vs SPY | +5.63 pp [−9.87, +22.97] | +1.51 pp [−10.49, +13.46] |
| C6 beta | 0.81 | 0.79 |
| C6 positions / hit rate | 510 / 52.7% | 498 / 53.2% |
| C7 vs SPY | +0.72 pp | −0.18 pp |
| C6A vs SPY | +10.72 pp [−7.9, +39.7] | +2.58 pp [−8.8, +15.5] |
| K1 / K2 / K7 (pp/yr) | +23.7 / +23.6 / +41.8 | +6.6 / +5.1 / +11.7 |
| Event study H=21 | −2.71 pp, n = 430, 24 dates | −3.02 pp, n = 414, 22 dates |
| C6 attribution sector / selection | +4.44 / +2.77 | +3.99 / −1.53 |

## Data limits and biases

- **Sample:** 64 sessions, one regime (a mild decline). No crash or rebound, so the rebound test is not evaluable.
  Annualised figures from 63 returns are extremely noisy.
- **Plans:** 760 incumbent-era plans, all classified.
  - 498 evaluated positions: 277 exits on the recorded resolution date, 31 on published levels, 190 still open at
    window end.
  - Excluded: recorded NO_ENTRY 75, not live origination 16 (deviation D5), zone still live 104, zone expired 19,
    resolved at/before a follower's fill 34, published after window 12, no close at fill 2.
  - The 34 resolved-before-fill plans are a real selection versus the plan record: a follower could not have held them.
- **MRNA price note:** the 2026-08-19 one-day move of +177% (62.96 → 174.38; raw and adjusted closes agree; volume
  199,252,300) exists only in the single price cache used by this harness. No second source authenticates it. It
  affects the as-run population and sensitivity (a), not the primary book.
  *(Superseded 2026-11-11, adjudication finding 15: two post-publication second sources now authenticate the move —
  a ChartExchange end-of-day sweep and a Yahoo live-chart API pull matching all 64 window sessions. Both were
  gathered after outcomes were seen and are labelled as audit evidence; the artifact's
  `population.mrna.price_authentication` carries the current text.)*
- **Membership:** S&P 1500 point-in-time (start/end dates), but the file has no recorded change after 2026-06-02.
  36 point-in-time members had no price file (≈2.4%, excluded and listed). Theme-basket rosters were not used.
  macro#10965's PIT basket store begins 2026-08-13 and was not used.
- **Sector labels:** current-basis GICS. The two label sources never disagreed; that does not make them era-correct.
  C4's style weights put zero weight on XLB and XLRE, so C4/C5 hold no Materials or Real Estate names.
- **Fills:** close-only; zone fills at the filled_date close. These are not the plan record's own same-bar outcomes,
  and `stock_result_pct` was never read.
- **Weights:** equal weight across open positions (per position, not per distinct ticker). This sample contains no
  overlapping same-ticker positions, so the two definitions coincide numerically on every date; the corrected
  implementation is pinned by a staggered-overlap test.
- **Not evaluable:** the eight catalog sleeves (no plan carries a sleeve link); issuer-excluded peer counts
  (listing-ticker identity only); calibrated forecasts and actual-holdings attribution (no holdings exist).

## Deviations from the header (also in the artifact's `deviations[]`)

- **D1** (before outcomes): reason keys renamed from `ledger_*` to `recorded_*`, because lane 8's validator forbids
  the substring "edge". Names only.
- **D2** (after outcomes): post-hoc concentration diagnostics added (per-asset contribution, concurrency,
  leave-top-contributor-out). They are labelled descriptive and cannot change any level.
- **D3:** the final scheduled rule rebalance executes at the last close, and its cost (< 0.1 pp) is not charged.
- **D4:** event-study horizons with fewer than 5 publication dates are marked too_few_dates (H = 63 now has no
  matured plan at all and is unmatured).
- **D5** (after outcomes, 2026-11-10): population corrected to live-published plans only — the 16 outage
  reconstructions excluded from C6/C7/C6A, the event study, attribution, coverage counts and every contrast that
  uses them; detected from `origination_mode` / `backfill_executed_at` and the disclosure receipts; an
  availability test now fails if any plan enters its book before its own auditable first availability; the
  per-position weighting of the header implemented exactly; `#` documentation lines in the resolution log are
  skipped so the malformed counter counts only real bad rows. Full before/after table above; source: the
  independent review named at the top. No threshold, comparator definition or test family changed.

No threshold was changed.

## Next protocol (note, not a result)

A future member-selection test needs a comparator matched ex ante on eligible cohort, concentration,
sector/factor exposure, entry timing and costs, pre-declared in a new header before outcome access — not X6,
which only matches risky weight. The same header should carry the live-published population rule explicitly so
the distinction never has to be reconstructed from receipts again. Prospective sessions after 2026-11-11 accrue
toward L1/L2 under the unchanged header hash.

## What the product may truthfully claim today

- It may describe the observed window: "Over 2026-08-10 to 11-06 the model book of live-published Prophet plans
  returned −3.1% vs SPY −4.7% (a +1.5 pp difference, 95% CI [−10.5, +13.4]), with market sensitivity about 0.8."
  The claim must carry its interval, the population definition (live-published plans only), the "descriptive, not
  validated" label, and the fact that an earlier version of these numbers included plans no user could see and
  showed a larger lead.
- It may not claim beta capture, outperformance, alpha, sector-context value, member-selection value or that
  following leading sectors helps.

To claim more (L1):
- at least 252 evaluated sessions under this unchanged header hash, including an SPY drawdown of 8% or more;
- the job criteria met with Holm control, robust to 2× costs and to dropping the largest single name;
- for sector/member claims, a point-in-time sector membership source, as-published plan vintages and a
  pre-declared matched comparator.

Re-running this header after 2026-11-11 accrues prospective sessions; L2 needs a further 126 post-freeze sessions after L1.

---

## Correction, 2026-11-11 (independent audit RUN-D + stock-minus-sector diagnosis)

Two engine defects confirmed by two independent re-derivations (ChatGPT Pro run D; Kimi) are fixed, with
regression tests, on the audit branch; every superseded figure is retained beside its corrected value in the
artifact's `correction` block, and the full finding-by-finding verdicts are in `ADJUDICATION_RUN_D.md`.

1. **Final-close trade cost charged** (deviation D6). v1 computed the cost of a target defined at the final close
   and silently dropped it. Corrected: C6 −3.1382% → −3.2351% total, +1.5077 → +1.4108 pp vs SPY
   (CI [−10.509, +13.221]); costs 1.1826% → 1.2822%. C3/C4/C5 terminal rebalances now charged (≤ 0.2 pp);
   C1/C2/X6 unaffected. **The release level and verdict are unchanged: L0 descriptive, not distinguishable from
   passive — every headline interval still spans zero.**
2. **Price bytes verified against the data pin** (audit finding 6). v1 trusted the local cache directory. The
   corrected runner byte-compares every parquet to the pin's git blob ids and reads all non-price inputs from the
   pin. One ticker (ZWS) was falsely counted missing; it was eligible but never selected, so no frozen number
   moves; the missing-file census is 35, not 36.
3. **Disclosure additions** (findings 4, 5, 11, 14): missing held marks itemised (LFUS, SBH) with a total-loss
   stress (−4.4205%, +0.2254 pp vs SPY, CI spans zero); coverage priced-share basis stated as entry-marks-only;
   top-three concentration view (excluding AMR/CRCL/TEM: −5.0104%, −0.3645 pp — the headline's sign rests on
   three names); undated conversions itemised (78 plans) with the excluding sensitivity (−5.7289%, −1.0831 pp,
   CI [−12.081, +9.522]).
4. **Yardstick correction** (deviation D7, from the independent stock-minus-sector diagnosis, recomputed on this
   engine): beside the frozen stock-minus-sector-ETF leg, the event study now also reports the equal-weight
   same-sector member benchmark and a random-member placebo. At H21 the average same-sector member trailed its
   own fund by −0.63 pp and picks sat a further −2.41 pp below that average (placebo 95% range [−1.62, +0.49]);
   at H42, −2.15 and −3.28 ([−3.72, −0.44]). Part of the published leg is the cap-weighted yardstick, not member
   choice; no claim of negative member selection and none of its absence.
5. **Off-index sensitivity** (deviation D8): 46 of 732 published plans name stocks outside the point-in-time
   S&P 1500 at the signal date; excluding them moves the H21 stock-minus-sector mean from −3.04 to −2.44 pp and
   the H42 mean from −5.43 to −3.89. Membership-file limits (no recorded change after 2026-06-02) are restated
   with the block.
6. Labels corrected in place above: MRNA is a receipted replay, not a reconstruction (finding 12); its price move
   is now second-source authenticated (finding 15); the 16/17 census is clarified (finding 12).

The forward pre-registration derived from the diagnosis is `PREREG_MEMBER_SELECTION_v1.md` (one confirmatory
hypothesis, two descriptive ones); its freeze record is the sidecar `PREREG_MEMBER_SELECTION_v1.FREEZE.json`.
The diagnosis itself is `DIAGNOSIS_STOCK_MINUS_SECTOR_20261111.md`. The earlier v0 draft is superseded and
removed. None of this changes what Prophet publishes.
