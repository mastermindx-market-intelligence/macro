# Rotation Core — Phase 2 pre-run additions v1 (recorded before Stage D)

Recorded 2026-11-11, before any candidate or baseline outcome was computed. These items implement the parent's Phase 1
adjudication (additions A–G) and fix implementation details the header leaves open. None of them changes a header
threshold, parameter, window, family or test count. Header sha256 `af2a0988…0f32` is unchanged. Each item is listed in
`results_stage_D.json` `deviations[]` with kind `pre_outcome_addition`.

## 1. Hold-out access

See `HOLDOUT_ACCESS_RULING_v1.md`. In Stage D the harness **truncates every input at 2019-12-31 before computing
anything**; J4 drops every formation after 2015-12. **Consequences:**
- **Pivot tables and the J2 episode holdings cover D episodes only** (1998, 2000–02, 2008–09, 2011, 2015–16, 2018Q4).
- The 2020, 2022 and 2025 episodes requested in addition D lie in H and stay sealed until the parent releases them.
- G4 and the H half of G6 are reported as `not_evaluated_sealed`. **G6 is evaluated on D only** and labelled provisional.

## 2. Power (addition A)

For each primary contrast:
- **Standard error:** SE = the standard deviation of the stationary-bootstrap distribution of the statistic (B = 10,000, mean block 21 sessions; J4: months, mean block 3).
- **Minimum detectable effect at 80 % power:** MDE = (z_{1−α/m} + z_{0.80}) × SE, with α = 0.05, one-sided, and m = the size of the Holm family. α/m is the threshold the smallest p must clear under Holm. The MDE under an unadjusted α = 0.05 is printed beside it.
- **Stated sentence:** "this test could / could not have detected an effect of X pp/yr". X is the header's G2 effect, +1.0 pp/yr (J4: +2.0 pp/yr), and "could" means MDE ≤ X.
- **Sharpe contrasts (P2):** stated in Sharpe units, against no G2 value. The MDE is printed and the sentence uses 0.10 Sharpe.

## 3. Deflated Sharpe trial count

`effective_n` = the sum of `TrialLedger.effective_n` over these families:

| Family | Count |
|---|---|
| `rotation_core_v1` | 36 |
| `thematic_rotation_phase0` | 8 |
| `cross_asset_phase0` | 72 |
| `index_direction_phase0` | 8 |

These are the prior registered trials on the same instruments, read from the ledger at `623f0a4623`. The total is
**124**. It is passed through a `ledger=` duck-type, never a literal. spvector's 12 trials are not in the ledger and are
named but not added.

## 4. Long-history descriptive tier (addition B; L0, no Holm family, index-level, no tradable instrument)

**Already in the header:** J1_L (B3, B4, J1-D on ^GSPC and French market, 1928–1997; credit from DBAA from 1987).
**This addition supplies the remainder:**

- **Returns:** Ken French daily market total return (Mkt-RF + RF) and RF as cash, 1928-07-02 → 1997-12-31. T and MTF use ^GSPC price levels. B4 uses French market returns.
- **J1-E (T ∧ real-time Sahm):** from 1960-01. SAHMREALTIME starts 1959-12; availability is the header rule (10th business day of the next month).
- **Credit variant for J1-A/B/C before 1997:** spread = DBAA − DGS10. It is the longest unrevised Baa-minus-Treasury pair in the repo store: DBAA from 1986-01-02, DGS10 from 1962. Rule: C_long = spread(t−1) > SMA of the 252 spread observations ending t−1. First decision once 252 observations exist, about 1987-01. Window 1987-01 → 1997-12.
- **Named long-history episodes.** Peak = highest French market TR index level in the peak search window; trough = lowest after the peak up to the trough date.

  | Episode | Peak search | Trough by |
  |---|---|---|
  | L1929_32 | 1929-08-01 → 1929-10-15 | 1932-12-31 |
  | L1937 | 1937-02-01 → 1937-08-31 | 1938-06-30 |
  | L1962 | 1961-11-15 → 1962-01-31 | 1962-07-31 |
  | L1966 | 1966-01-15 → 1966-02-28 | 1966-12-31 |
  | L1969_70 | 1968-11-15 → 1968-12-31 | 1970-07-31 |
  | L1973_74 | 1972-12-15 → 1973-01-31 | 1974-12-31 |
  | L1980_82 | 1980-11-01 → 1980-12-31 | 1982-09-30 |
  | L1987 | 1987-08-01 → 1987-09-30 | 1987-12-31 |
  | L1990 | 1990-06-15 → 1990-07-31 | 1990-11-30 |

  All French-market closing drawdowns ≥ 15 % are also listed algorithmically.
- **Not included:** the header's J2_L (French 12 industries) and J3_L (proxy tier). They remain descriptive and are deferred to after the Stage D adjudication unless time permits. Their absence is recorded in the results.

## 5. Pivot table (addition C)

Same definitions as header `pivot_metrics`, plus:
- **Exit already in effect:** if the weight is already ≤ 0.5 at peak − 63 sessions, the exit is recorded as `already_out`, with the lead measured from the start of that risk-off spell.
- **"Lost X %":** the strategy's cumulative return from the peak close to the exit close. A negative lead means the strategy returns from the peak are measured to an exit after the peak.
- **"Missed Y %":** SPY's (long tier: French market's) cumulative return from the trough close to the re-entry close.
- **Graded rules** (J1-D, incumbents) are crossed at 0.5.

## 6. J2 episode holdings (addition D; L0)

For each D episode:
- Every J2 candidate's and baseline's holdings at the SPY peak and at the trough.
- The share of sessions between peak and trough each sector was held.
- The equal-weight XLP / XLU / XLV return minus the SPY return, peak → trough.

## 7. J4 implementation details

- **Price sources:** the prophet-eval cache uses column `close` (adjusted). The Phase 2 Yahoo fetch uses `Adj Close`. Series flagged `identity_suspect` by the fetch are excluded and counted.
- **Ending histories:** if a stock's prices end inside a label window, primary treatment (i) compounds the available days and holds zero return thereafter. Treatment (iii) applies the header's −30 % on the last priced day when the name was still a member.
- **Leading / lagging:** among the eligible SPDRs at t (9 in early years).
- **Selection size:** n_sel = max(3, ceil(0.2 n)), capped at n. Sectors with fewer than 3 assigned names are skipped for that month (counted).
- **J4-B turnover:** the sum of |Δweight| between the new targets and the drifted previous holdings.

## 8. Missing closes

On SPY sessions, a missing ETF or fund close within the instrument's life is forward-filled (zero return that day) and counted per instrument. This reproduces "execution deferred to its next close" for a held position.
