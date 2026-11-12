# Prophet beta-first evaluation — protocol header v1 (FROZEN)

**Frozen:** 2026-11-11 (UTC), before any outcome access. **Owner:** Lead C (scientific evaluation lead).
**Machine-readable header:** `protocol_header_v1.json`, SHA-256
`3be32166c7be5170c5153f7c6e66af02e988e88dda52167140e7ac12f30b2ada` (hash of the exact file bytes).
The harness refuses to run if the file hash differs. This Markdown explains the JSON; where they differ, the JSON governs.
**Governing law:** `SECTOR_QUANT_PROTOCOL.md` §3.2 (one coherent return-explanation method), §5.1–5.5 (immutable header,
baseline family, time-respecting evaluation, metrics, predeclared job-specific acceptance, separate release levels).
**Data pin:** Macro `b5a5c846f8b597d4c041e11c624b7fbf74684ffe` (origin/main at freeze).

## 1. Question and hypotheses

Does the incumbent Prophet plan book participate in the US market (beta capture) before it claims anything more,
and does sector context, member selection or their combination add anything beyond passive participation?

- **H1 market participation (job A):** C6 (incumbent Prophet book) has market beta near one, captures up-markets,
  stays mostly invested, and is not materially worse than passive SPY after costs (non-inferiority margin −3.0 pp/yr).
- **H2 sector allocation (job B):** sector context adds value beyond market exposure: C3 > C1 (K3), C5 > C4 (K5),
  and within Prophet, plans aligned with leading sectors outperform independently emerging plans, C6A > C7 (K7).
- **H3 member selection (job C):** name selection adds value: C4 > C1 (K4), C5 > C3 (K6), C6 > exposure-matched SPY/BIL (K2).
- **H4 participation rule:** C2 > C1 (K8) — included so that a trivial trend rule is in the same family as the claims.
- K1 (C6 vs C1) is the headline beta-first contrast.

## 2. Comparator family (exact definitions in the JSON)

| Id | Meaning | Construction (short) |
|---|---|---|
| C1 | Passive market | 100% SPY |
| C2 | Simple participation | SPY when SPY > 200-session SMA, else BIL; daily, t+1 execution |
| C3 | Sector allocation only | Top 3 of the 11 SPDR sector ETFs by 63-session return minus SPY; equal weight; every 21 sessions |
| C4 | Member selection only | S&P 1500 point-in-time members; within each sector, top 10% (min 3) by 63-session return minus own sector ETF; sectors weighted at SPY style weights estimated pre-window |
| C5 | Joint sector + member | C3's three sectors × C4's within-sector picks |
| C6 | Incumbent Prophet, as built | Every `anticipation-v1-2026-08-08` era plan, entered as the system recorded it (zone filled/converted, not NO_ENTRY), never before its publication session; exit at the ledger's resolution date or the plan's own published stop/T1/horizon; equal weight across open positions; BIL when none |
| C7 | Independent emergence | C6 plans whose sector was not in the C3 top 3 at the plan's price-basis close |
| C6A | Context-aligned Prophet (diagnostic) | C6 plans whose sector was in that top 3 |
| X6 | Exposure-matched reference | C6's previous-close risky weight in SPY, remainder in BIL |

Member-only/joint are rule baselines on a point-in-time universe, not Prophet. C3/C4/C5 parameters are conventional
defaults fixed here without tuning. The eight Prophet catalog sleeves cannot be evaluated: plans carry no sleeve link.
`admission_class` strata (patience, confirmation, early_turn_starter) are the secondary family.

## 3. Universe, window, execution, costs

- **Market / benchmark / basis:** US, USD, SPY, dividend- and split-adjusted total-return closes (`data/yahoo/*.parquet` `close`); cash = BIL total return.
- **Window:** daily returns from the 2026-08-10 close through the 2026-11-06 close (64 sessions, 63 returns). The start
  is fixed by the incumbent selection era; the end by the plan snapshot's `source_asof`. Warm-up data from 2025-01-02 is
  used only for signals. Halves are reported for stability (descriptive).
- **No look-ahead:** every rule signal uses closes dated ≤ t and executes at the t+1 close. Prophet entries never precede
  the publication session P (the first session after `price_basis_date` and on/after `recorded_at`; the nightly runs
  before the US open on its recorded date).
- **Splits / embargo:** nothing is fitted on the window. Rules are fixed here, so the whole window is out-of-sample. The only
  estimated quantity (C4 sector weights) uses the 252 sessions ending 2026-08-07. Overlapping holding periods are
  handled in inference (block/cluster bootstrap), not by an embargo.
- **Fills:** close-only; zone fills at the `filled_date` close; a missing close is a no-fill (counted).
- **Costs:** 3 bp per side for ETFs, 10 bp per side for stocks, on traded notional including rebalancing; stress at 2×.
- **Cash:** uninvested weight earns BIL. Long-only, no leverage.

## 4. Metrics

Per comparator, all computed from the daily net return series: total and annualised return; total and annualised excess vs SPY;
beta vs SPY (OLS on BIL-excess returns); annualised intercept (a regression residual, **not** labelled alpha);
tracking error; up/down capture (geometric, guarded near zero); max drawdown; one-way annual turnover; mean invested
weight; time in market; costs paid; no-entry/no-fill counts; position hit rate vs SPY with a Wilson CI (Prophet books).

**Attribution bridge (C6/C7/C6A only):** a daily arithmetic accounting identity with sector ETFs as benchmark segments:
market = Σwᵢ·r_SPY, sector allocation = Σwᵢ·(r_ETF(i) − r_SPY), selection = Σwᵢ·(rᵢ − r_ETF(i)), cash = w_cash·r_BIL, minus costs.
The legs sum exactly to the sum of daily net returns. The compounding residual to the total return is shown separately.
This is not a regression or factor decomposition (§3.2 forbids mixing the two). The selection leg includes stock beta
different from one; beta is reported separately.

**Event study:** all published era plans, policy-free, at H = 10/21/42/63 sessions. It uses the existing
`engine.grading.forward_metrics` next-bar ruler. Each plan has three numbers: excess vs SPY, its sector ETF minus SPY,
and the stock minus its sector ETF. Only matured horizons are counted.

## 5. Statistics

Stationary bootstrap (mean block 10 sessions; sensitivity 21) with B = 10,000 and seed 20261110. Paired rows are resampled
together, and the CIs are 95%. P-values are one-sided, testing a positive mean daily net differential. The event study
uses a date-cluster bootstrap. **Multiplicity:** Holm at α = 0.05 over the confirmatory family K1–K8. A separate Holm
family covers the three `admission_class` strata vs C1.

## 6. Predeclared acceptance by release level

| Level | Requirement |
|---|---|
| **L0 descriptive** | Source-correct run: ≥ 90% of era plans either evaluated or excluded with a closed reason, and ≥ 95% of entered positions priced. Numbers are descriptive with CIs and carry no performance claim. |
| **L1 accepted historical** | Global minimum: window ≥ 252 sessions, it contains an SPY peak-to-trough drawdown ≥ 8%, and there are ≥ 150 resolved positions. Job A (C6): β in [0.8, 1.3] with CI lower bound ≥ 0.6; up-capture ≥ 0.90 with CI lower bound ≥ 0.75; mean invested ≥ 0.80; annualised excess vs SPY CI lower bound > −3.0 pp; non-inferior at 2× costs. Jobs B/C: Holm-adjusted p < 0.05, point estimate ≥ +2.0 pp/yr, holds at 2× costs, and K3 also beats the exposure-matched SPY/BIL reference (CI lower bound > 0). |
| **L2 prospective shadow** | L1 met, then ≥ 126 sessions after 2026-11-11 under this unchanged header hash and the same criteria. |
| **L3 approved product prediction** | L2 plus independent non-author review and Evaluation-owner acceptance. This harness can never assign L3. |

**If the global minimum is not met, every performance job is capped at L0 regardless of point estimates.** The available
window is about 64 sessions, so this run can deliver L0 at most. It also creates a frozen baseline. Re-running the
same header after 2026-11-11 accrues prospective sessions toward L1/L2. That is stated now, before any outcome.

## 7. Biases and how each is bounded

1. **Membership/survivorship.** C4/C5 use S&P 1500 point-in-time start/end dates (`data/breadth/sp1500_pit_membership.parquet`).
   The file's last recorded change is 2026-06-02, so later index changes are unrecorded. Members without price files are
   excluded and counted, and delisted names are counted. Theme-basket rosters (`data/baskets/membership.json`) are current with
   back-dated `added`, so they are not used. The unmerged PIT basket store in macro#10965 (`a089d2f9b4`; snapshots from
   2026-08-13, theme baskets only) was inspected and is not used: theme baskets are outside this family. It would cover
   most of this window for a later theme amendment.
2. **Sector labels** are current-basis GICS (`era_correct=false`). Disagreements between the two label sources are counted.
3. **Plan selection/backfill.** The publication clock governs entry. Legacy-era plans are excluded from C6.
   Resolved-before-fill plans are excluded and counted. A sensitivity run drops plans with a `plan_corrections.jsonl` row.
   `index.json` is the 2026-11-09 snapshot, not each plan's as-published bytes.
4. **Short sample, one regime.** This is capped by the global minimum.
5. **Overlapping horizons.** Handled by block bootstrap (books) and date-cluster bootstrap (event study).
6. **Close-only fills.** There is no intraday data. The ledger's own same-bar fills are not reused, so these numbers differ from the ledger's.

## 8. Contamination disclosure (what was seen in the data census before freezing)

- Ledger field names and the outcome-label vocabulary (EXPIRED, INVALIDATED, NO_ENTRY, T1_HIT, T2_HIT); no category counts
  and no `stock_result_pct` values.
- Index `lifecycle_counts` (resolved 529, entered 275, ready 64, invalidated 25).
- Outcome labels and `days_held` of 6 printed ledger rows.
- One plan (GPCR-BULL-20260604) closed/stopped out with last price 20.35 vs entry 53.14.
- SPY adjusted closes for 1993-01-29/02-01 and 2026-11-06 (735.29) / 2026-11-09 (752.69); no window return.
- The brief's report that lane 8's sector-rotation comparator did not beat passive SPY after costs on its own window.

No strategy, comparator or plan-population return over the window was computed or seen. Lead C's model knowledge
ends June 2026 and contains no August–November 2026 market path.

## 9. Deviations

Any departure from this header is logged in `RESULTS_v1.md` and in the artifact's `deviations[]` with a reason.
Thresholds are never changed after outcome access.
