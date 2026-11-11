# Rotation Core — protocol header v2 (DRAFT revision 1, NOT FROZEN)

> **Power.**
> - **H2 cannot detect a 2 pp/yr effect.** It is H-only (6.85 years), and its minimum detectable effect at 80 % power is about **8.2 pp/yr**.
> - **H1's primary statistic** can detect about **1.1 pp/yr** on the pooled L+H sample (1.3 under Holm m = 2).
> - **H1's full joint rule** (pooled significance, H > 0 and both L eras > 0) needs about **1.5 pp/yr** for 80 % power.
> - These are projections from D variance, scaled by years. Whether L's per-year variance is higher or lower than D's is unknown.

**Status.** This draft has been through one separate-context review. The parent freezes it after folding in three inputs:
- the Sector Intelligence yardstick and signal shortlist;
- their Kimi review of v1;
- Pro run A.

**Freeze procedure.**
- Every change goes in a logged diff, committed before the frozen JSON, with its source and reason.
- No computation of any kind on L or H before freeze.
- Changed or added rules raise the `rotation_core_v2` trial budget and are listed in the contamination disclosure.
- Each confirmation stage runs once at the frozen hash.

Where this file and `protocol_header_v2.DRAFT.json` differ, the JSON governs.

## Question

When conditions turn bad, does rotating out of broad equity leadership into the defensive sectors (staples, utilities, health care) add value? Cash is an option, not the default. Value here means beating holding the same market exposure without rotating.

## Hypotheses

**Testing order (proposed): fixed sequence at α = 0.05.** H1 is tested first. H2 is tested only if H1 is rejected. This keeps H1 at full α while H2 stays confirmatory.

The parent may instead choose:
- Holm m = 2 over {H1, H2}, which costs H1 about 12 % in minimum detectable effect; or
- H2 as descriptive only.

| Id | One rule | Primary statistic | Samples |
|---|---|---|---|
| **H1** | ^GSPC < SMA200 at close t → equal-weight defensive leg; otherwise equal-weight risk-on leg. The switch executes at the next close when the state changes. Within each leg, rebalance at month-end (decided at the last session of the month, executed at the next close), drifting in between. Always fully invested. | **Beta-matched rotation value.** On days H1 holds the defensive leg, compare it with β_t × risk-on leg + (1 − β_t) × cash. Here β_t is the defensive leg's trailing 252-session beta to the risk-on leg, lagged one day, using at least 200 observations and clipped to [0, 1.5]. On risk-on days the difference is 0. The statistic is the annualised mean difference. | **L + H pooled** |
| **H2** | v1 J1-E unchanged: SPY goes to cash only when T and real-time Sahm ≥ 0.50 agree. | H2 minus a static SPY/cash mix at H2's mean weight | **H only** |
| third | **Not included.** J3-C's primary contrast was weak on D, it has no long sample, and its minimum detectable effect would be about 11 pp/yr. The reviewer agreed. | — | — |

**Legs.**
- **D/H:**
  - **Risk-on:** equal weight of all eligible SPDR sectors. XLRE and XLC join at the first month-end after their 253rd session.
  - **Defensive:** XLP, XLU and XLV.
- **L (Ken French 12 industries, value-weighted daily):**
  - **Risk-on:** all 12 industries.
  - **Defensive:** NoDur, Utils and Hlth.

**Why the primary statistic changed (review blocker).** The draft's original contrast compared H1 with a static mix of its two legs. That contrast still contained T's market timing, because the risk-on leg has the higher beta. v1 had already measured T's market timing on L (the 200-day rule against cash), so a pooled test would mostly have re-tested it. The beta-matched statistic removes that term and asks only whether defensives beat equal market exposure during T's risk-off spells.

The old static-mix contrast X1 is kept as a secondary result. It now uses H1's month-end calendar, so it is no longer rebalanced daily.

## Why H1 is built this way (D evidence)

- **Risk-on leg = equal-weight sectors.** No D sector-selection rule beat equal weight. SPY would add a cap-weight bet the defensive leg lacks. A "high-beta set" would have to be chosen from D outcomes.
- **Defensive leg = the trio.** Peak to trough, the trio beat SPY in all five D episodes that have SPDR data: +31.5, +19.2, +12.9, +9.6 and +10.7 pp.
- **Switch on risk state, not sector momentum.** At the 2000 and 2007 peaks, the D sector-momentum rules did not hold the trio as a group.
- **T rather than crisis-only J1-E.** J1-E got out before the trough in only 2 of 6 D episodes. It never left equities in 2011, 2015–16 or 2018Q4, which are the episodes where the trio won by 9.6–12.9 pp.
- **Faster trigger.** With cash as the fallback, T's false risk-off calls cost 3.73 % per calm year on D. With defensives as the fallback, a false call costs only the spread between the risk-on and defensive legs. Defensives have the lower market beta, so they keep part of any rise. That asymmetry is the argument for using the faster T rather than J1-E.
- **T rather than trend-and-credit.** Trend-and-credit exited on the same dates as T in all six D episodes. Its lower false-pivot count matters less once false calls are cheap. Credit data also only starts in 1986, which would make H1 H-only.
- **Ancestor disclosure.** H1 descends from v1 J2-E: the same switch, but with the J1-E trigger and a monthly cadence. J2-E's D result was seen: +0.39 %/yr over equal-weight sectors. Changing to T and a daily cadence came after that result, which is why D has no confirmatory role.

## Samples and cleanness

**D (1998–2019).** Seen. Used for design only.

**L: `12_Industry_Portfolios_Daily.csv`, value-weighted, returns 1928-10-17 → 1997-12-31.**
- **Size:** 18,423 sessions (69.2 years), including 1,158 Saturdays before 1952.
- **Why this file:** v1 had already declared it as the long-history file, and it has no missing cells.
- **Mapping is not one-to-one:**
  - NoDur is SIC "consumer nondurables". It includes food, beverages and tobacco, but also textiles, apparel, toys and some publishing. It excludes household products.
  - Utils and Hlth are close analogues of XLU and XLV.
- **Staples sensitivity (descriptive):** the 17-industry Food portfolio with Utils and the 12-industry Hlth. The 17-industry file has no health group, so it cannot carry the whole trio.
- **Calendar:**
  - ^GSPC is aligned to French dates as-of: the last ^GSPC close dated on or before each French date.
  - Annualisation uses each year's observed sessions.
  - Pooling weights each sample by years.

**L eras.** 1928-10 → 1945 and 1946 → 1997. H1 must be positive in both (LAW-ERA-SPLIT).

**H.** Returns 2020-01-02 → 2026-11-06, the v1 data pin. No dates are excluded: v1's burned dates applied only to J4. H has not been computed by Rotation Core.

**What is clean on L:**
- **H1 primary statistic: largely clean.** It removes T's market timing, and no industry-level return has ever been computed on L. Not clean for the trigger: T's path and its market-level timing were seen in v1. General knowledge of the published history also applies.
- **H2: not clean.** J1-E was run on 1960–1997, and real-time Sahm has no long real-time substitute. H2 is H-only.
- **Existing outputs on the French industry panels: none.** v1's J2_L tier was deferred and never run, no worker produced industry returns, and Macro main has no consumer of these files. Only the raw CSVs exist, in scratch.

## Declared comparators (every book; descriptive)

- **Comparators:** SPY; RSP (from 2003-05); the risk-on leg alone; the defensive leg alone; X1; X2.
- **Capture:** full-period monthly up/down capture, and stress-episode capture against SPY and RSP, pooled and per episode.
- **Stress episodes:**
  - **L:** 1929–32, 1937, 1962, 1966, 1969–70, 1973–74, 1980–82, 1987, 1990.
  - **H:** 2020, 2022, 2025, and 2026 by its v1 rule.
  - All drawdowns of 15 % or more.

**Descriptive variants:** H1 with the trend-and-credit trigger (H only); H1 with the J1-E trigger; T computed on the French market index; the staples sensitivity.

## Decision rule

**H1 primary test.**
- A sample-stratified stationary bootstrap: L and H are each resampled independently (block 21, sensitivity 63, B = 10,000).
- Seeds: L 20261111, H 20261112, H2 20261113.
- Pooled statistic = (Y_L × mean_L + Y_H × mean_H) / (Y_L + Y_H), with Y in years. L carries about 91 % of the weight.
- Requiring H > 0 and both L eras > 0 is what stops one period carrying the result. At a true 1.5 pp/yr the joint rule passes about 80 % of the time; at 1.0 pp/yr it is closer to a coin flip.

**L1 accepted historical, H1.** All of:
- significant pooled;
- effect ≥ +1.0 pp/yr;
- H > 0 and both L eras > 0;
- the significance and effect conditions still hold at 2× costs;
- pooled stress capture against SPY ≤ 0.80, where pooled stress capture = (product of (1 + H1 return) over all named episodes − 1) ÷ (the same for SPY);
- H1 CAGR ≥ risk-on leg CAGR − 1.0 pp/yr on L and on H separately.

**L1 accepted historical, H2.** All of:
- significant on H;
- effect ≥ +1.0 pp/yr;
- holds at 2× costs;
- max drawdown ≤ 0.70 × SPY's;
- CAGR ≥ SPY − 2.0 pp/yr.

H2's realistic outcome is L0. H's largest drawdown, in February–March 2020, ended before real-time Sahm could confirm.

**L0.** Anything else. A null is reported as "not detectable" with its power line.

**L2.** L1, then at least 252 forward sessions under the unchanged hash, containing a SPY drawdown of 10 % or more. **Owner: QLedger**, with one claim per decision. Nothing is written to QLedger, Reflex Registry or Chronicle unless L1 is earned.

## Power (D variance only)

Scripts and their exact output are committed in `v2_power/` with SHA256SUMS. No point estimate was printed.

| | D SE (ann.) | MDE80 |
|---|---|---|
| H1 beta-matched, pooled L+H | 0.89 % (19.9 D years) | **1.14 pp** fixed-sequence; 1.28 pp Holm m = 2; 1.19 pp L only; 3.79 pp H only |
| H1 full joint rule | — | about 1.5 pp at 80 % |
| H2, H only | 1.85 % | **8.2 pp** |

Formula: SE_sample = SE_D × √(D years ÷ sample years); MDE = (z₁₋α + z₀.₈) × SE.

## Unchanged from v1, and dropped

**Unchanged:** harness, costs (5 bp ETF, 10 bp French), t+1 execution, metrics and data pin.

**Trial ledger:** `rotation_core_v2` is declared at freeze with a budget of 11. The deflated-Sharpe count also carries v1's 36.

**Dropped:** sector RS velocity, graded MTF, J4.

## Review dispositions

Review file: `/home/ubuntu2/tmp/rotation-core/review/V2_DRAFT_REVIEW.md` (Opus, separate context, draft at `89c521cc7f`).

| # | Finding | Disposition |
|---|---|---|
| 1 BLOCKER | The pooled test mostly re-tests T's market timing, already seen on L | **Accepted.** Beta-matched primary statistic; X1 kept as secondary; L-clean text rewritten |
| 2 | H1's ancestor J2-E not disclosed | **Accepted.** Disclosed with its D number |
| 3 | NoDur ≠ staples; 17-industry file and v1 pre-declaration not mentioned | **Accepted.** Honest SIC description; 17-industry staples sensitivity declared; v1 pre-declaration cited |
| 4 | X1 rebalanced daily, H1 monthly | **Accepted.** X1 on H1's calendar |
| 5 | Saturdays on L; session count | **Accepted.** 18,423 sessions; year-based annualisation and weighting |
| 6 | Decision rule rationale and power overstated | **Accepted.** Rationale rewritten; joint-rule power stated |
| 7 | Era split missing | **Accepted.** Two L eras, both must be positive |
| 8 | H2 foreclosed on H; it costs H1 power | **Accepted in part.** Fixed-sequence testing proposed; Holm or H2-descriptive left to the parent |
| 9 | Freeze-time inputs are an open forking path | **Accepted.** Logged-diff freeze procedure and run-once rule |
| 10 | About ten definitions too loose | **Accepted.** Month-end, warm-up, XLRE/XLC entry, w_on, seeds, block-63 reporting-only, 2× cost re-test, CAGR reference, pooled stress capture, calendar alignment, run-once all defined. *Data sha pins are written at freeze.* |
| 11 | General-knowledge contamination on L | **Accepted.** Disclosed |
| MINORs | Wording, D-only citations, seed mismatch, power formula | **Accepted.** Five-episode wording; "did not hold the trio as a group"; beta argument without a non-D number; seed disclosed; formula printed |
