# Rotation Core — historical rotation protocol header v1 (FROZEN)

**Frozen:** 2026-11-11 (UTC), before any candidate's outcome was computed.
**Owner:** Rotation Core research lead, Prophet programme.
**Machine-readable header:** `protocol_header_v1.json`, SHA-256
`af2a09886132bb784535e21134b63c2c86c579e186c248b20bb617fc77580f32` (hash of the exact file bytes).
The Phase 2 harness must refuse to run if the hash differs. **Where this Markdown and the JSON differ, the JSON governs.**
**Data pin:** Macro `4d49b23a8f0246718fd48a24b4124c35129a1cfe`, plus the vendor cache in `/home/ubuntu2/tmp/rotation-core/data` (scratch, never committed). Last close used: 2026-11-06.
**Census:** `CENSUS_2026-11-10.md` (this directory).
**Trial ledger:** family `rotation_core_v1`, declared budget 36, appended to `data/trial_ledger.jsonl` in the same commit as this header.

## 1. Question

Can signals the organisation already computes, or cheap transparent extensions of them, call risk-on/off pivots and
sector and cross-asset rotations well enough to beat simple baselines after costs, out of sample? The census (§1) finds
no prior evidence that they can. Sector momentum, the trend gate, cycle-state allocation, cross-asset TSMOM and the
cycle-turn ontology have each been tested, and each came out null, negative, or as drawdown control that costs return.
This header tests the untested combinations the Chairman's directive names, against the baselines they must beat:
- confluence of trend, credit and macro;
- multi-timeframe trend;
- sector RS and RS velocity;
- conditional rotation;
- cross-asset rotation;
- amplification;
- the combined stack.

## 2. Jobs, baselines, candidates

Each job has a fixed candidate family. **No parameter grid exists anywhere in the protocol.** Every parameter is named
below and is a textbook default (200-day SMA, 252-day spread SMA, Sahm 0.50, 12-1 and 6-month momentum, top 3,
50/100/200-day MTF, 63-day RS with 21-day velocity, 10-month Faber SMA).

Signal shorthand:
- **T** = S&P 500 below its 200-day SMA.
- **C** = HY OAS above its 252-observation SMA, using the repo series from 1996-12-31, lagged one day.
- **M** = real-time Sahm rule (`SAHMREALTIME`) ≥ 0.50, available from the 10th business day of the following month.
- **MTF** = share of the 50/100/200-day SMAs that price sits above.
- **RS63** = 63-session relative wealth versus SPY.
- **VEL** = RS63 minus RS63 21 sessions earlier.

| Job | Baselines it must beat | Candidates (confirmatory unless noted) |
|---|---|---|
| **J1** market risk state → SPY vs cash | B1 SPY, B2 60/40, B3 SPY > 200 d else cash, B4 vol-target 15 %, **X** exposure-matched SPY/cash constant mix | **J1-A** C → cash. **J1-B** T ∧ C → cash. **J1-C** T ∨ C → cash. **J1-D** weight = MTF. **J1-E** T ∧ M → cash (crisis-only). Secondary: the same five with IEF as the risk-off asset. |
| **J2** sector rotation (SPDRs; XLRE / XLC enter when eligible) | B1, B5 EW sectors, B6 12-1 top 3, B7 6-month top 3 | **J2-A** top 3 by RS63. **J2-B** top 3 by VEL. **J2-C** RS63 > 0 ∧ VEL > 0, up to 3, else SPY. **J2-D** MTF = 1 sectors, top 3 by RS63, else SPY. **J2-E** (H only) J1* risk-off → EW XLP / XLU / XLV, else J2*. |
| **J3** cross-asset (SPY, EFA, EEM, TLT, IEF, GLD, DBC, cash) | B1, B2, B8 EW-7, B9 Faber GTAA-7, B10 dual momentum, X3 | **J3-A** top 3 by 12-1 with absolute filter. **J3-B** sleeve weight = MTF / 7. **J3-C** J1-B state switches between a defensive top 2 of IEF / TLT / GLD and a risk top 3 of SPY / EFA / EEM / DBC / GLD by 6-month return, each with an absolute filter. |
| **J4** amplification (PIT S&P 500) | Within-sector selection in all sectors | **J4-A** Δ = (top-quintile RS[t−126, t−21] selection spread in the 3 leading sectors) − (the same in the 3 lagging sectors). **J4-B** a book of leaders inside leading sectors versus leaders everywhere, at 10 bp. Sector membership is assigned statistically from trailing returns (no back-applied GICS). |
| **J5** stack | J1* alone, X5, J5-A | **J5-A** J1* risky weight in the J2* sector book. **J5-B** J5-A with the remainder in the better of IEF / GLD by 6-month return, else cash. Both on H only. |

**How J1* and J2* are picked:** J1* is the best development-period J1 candidate (or B3 if none is positive); J2* is the
best development-period J2 candidate (or B5).

**Incumbents (replication only, capped at L0 because their designs used the whole available history):**
- J1-I1: spvector glide as built.
- J1-I2: Risk Radar v2 gross as built. If its replay cannot be run, it is recorded as unavailable, with no substitute.
- J2-I1: `sector_signals` non-avoid sectors.
- J3-I1: cross-asset TSMOM, long-only.

**Counts:**
- 36 strategy configurations, declared to the trial ledger.
- 30 confirmatory tests in five Holm families: J1 10, J2 8, J3 6, J4 2, stacks 4.
- 8 incumbent replication tests in a separate Holm family.
- 38 tests in all.
- Deflated Sharpe for every strategy, with `n_trials` read from the ledger.

## 3. Evaluation design

- **Clock:** decision at the close of t using data ≤ t, with macro series only from their availability date. Execution at the close of t+1.
- **Cadence:** J1 rules are evaluated daily and trade only on a change. J2, J3, J4 and J5's sector and defensive legs rebalance monthly.
- **Return basis:** dividend-adjusted total return (Yahoo Adj Close). Cash accrues at the 3-month T-bill rate (DTB3, lagged one day).
- **Costs:** per side, 5 bp for ETFs and funds and 10 bp for stocks. A 2× stress is part of acceptance. Long-only, no leverage.
- **Windows:**
  - Development D runs from each job's first full-warm-up decision (J1 1998-01-02, J2 1999-12-31, J3 2007-02-28) to 2019-12-31.
  - Hold-out H runs 2020-01-02 → 2026-11-06.
  - D is reported for both eras, ≤ 2009 and 2010–2019 (LAW-ERA-SPLIT).
  - J4 uses formation months: D 1998-01 → 2015-12, H 2016-02 → 2022-05. The burned trend-persistence formation dates 2022-07-06 → 2026-06-02 are excluded entirely.
- **Two-stage access:** Stage D is computed and committed first; the harness cannot print H until then. Stage H then runs the identical code and header.
- **Fitting:** nothing is fitted. The only selection (J1*, J2*) uses D returns only, so it is confirmatory on H only.
- **Statistics:**
  - Stationary block bootstrap of paired daily differences: mean block 21 sessions (63 sensitivity), B = 10,000, seed 20261110.
  - Months for J4: mean block 3 (6 sensitivity).
  - One-sided centred p-values; 95 % intervals; Holm at 0.05 within each family.
- **Descriptive tiers (never confirmatory):**
  - J1 on ^GSPC and French market data, 1928–1997.
  - J2 on Ken French 12 industries, 1927–1999.
  - J3 on mutual-fund and futures proxies, 1995–2007.
  - J2 on today's 16 industry ETFs from 2007 (survivor-selected).
  - Themes are excluded: they have no PIT history before 2026-08-13.

**Metrics:**
- Return, volatility, Sharpe, Sortino, max drawdown, Calmar.
- Beta and residual intercept (not called alpha).
- Tracking error and information ratio.
- Monthly up/down capture against SPY.
- Turnover, costs paid, mean exposure and time in market.
- Deflated Sharpe.

**Pivot metrics** (J1, J5, and the J1 baselines and incumbents), for each named episode — 1998, 2000–02, 2008–09, 2011, 2015–16, 2018Q4, 2020, 2022, 2025, and 2026 if a ≥ 10 % drawdown occurred:
- Peak and trough are found from SPY closes inside fixed search windows.
- **Exit lead:** sessions before the peak at which weight falls to ≤ 0.5.
- **Re-entry lag:** sessions from the trough to re-entry.
- **Drawdown captured** and **126-session recovery participation**.
- **False pivots and their cost** per calm year, plus whipsaw counts.

## 4. What success means (decided now)

| Level | Requirement |
|---|---|
| **L0 descriptive** | A source-correct run. Every number is printed with its interval, its baseline beside it and the count of alternatives tried. No performance claim. |
| **L1 accepted historical** | All of G1–G7 hold (listed below this table). |
| **L2 prospective shadow** | Required before **anything** is presented as a call, pivot alert or rotation recommendation. L1 must be met first, then forward accrual after this commit under the unchanged hash, written nightly with no backfill: ≥ 252 sessions (J1, J5) or ≥ 12 monthly decisions (J2–J4). The forward contrast must stay ≥ 0 with no G6 breach. For J1/J5 the shadow must contain a ≥ 10 % SPY drawdown. Passing gives promotion-review eligibility only (DEC:RIC-E0). |

The L1 conditions:
- **G1:** Holm-adjusted p < 0.05 on the primary contrast in D. The primary contrasts are:
  - J1: timing return over the exposure-matched mix.
  - J2: excess over EW sectors.
  - J3: excess over the exposure-matched EW-7.
  - J4: Δ > 0.
  - Stacks: the F5 test, on H.
- **G2:** effect ≥ +1.0 pp/yr (J4 ≥ +2.0 pp/yr).
- **G3:** positive in both D eras.
- **G4:** positive in H with an unadjusted p < 0.10.
- **G5:** G1 and G2 still hold at 2× costs.
- **G6, job-specific risk tests:**
  - **J1/J5:** down-capture ≤ up-capture − 0.20; max drawdown ≤ 0.70 × SPY's; CAGR ≥ SPY − 2.0 pp/yr; ≤ 1.5 false pivots per calm year; exit before the trough in ≥ 6 named episodes; Sharpe ≥ B2, B3 and B4.
  - **J2:** information ratio vs EW ≥ 0.20; drawdown no worse than EW − 5 pp; beats B1, B6 and B7 on point estimate.
  - **J3:** Sharpe ≥ B2, B9 and B10; drawdown ≤ EW-7.
  - **J4:** same sign under all three survivorship treatments, and priced coverage ≥ 85 %.
- **G7:** the candidate's parameters were not chosen on the evaluation data.

**Caps stated before outcomes:**
1. **J4 cannot reach L1 on current data.** Fewer than 85 % of PIT members have prices in every year before 2024 (census §9.4). J4 history is descriptive unless licensed delisted prices are added. Its real test is the prospective shadow.
2. **The four incumbents fail G7** and are capped at L0.
3. **J5 and J2-E rest on about 6.8 hold-out years** containing three named episodes, so their power is low.

"Every rotation correctly called" is not a criterion. The criteria above are the measurable version: capture asymmetry,
drawdown, return non-inferiority, lead/lag at named peaks and troughs, false-pivot rate and cost, exposure-matched
excess, and survival of multiplicity correction and the hold-out.

## 5. Biases and how each is bounded

1. **Survivorship:**
   - ETF universes are as-listed. Today's industry-ETF and theme sets are descriptive only.
   - J4 handles survivorship with three treatments: exclude unpriced names, report the unpriced share per arm, and apply a −30 % terminal return.
2. **Back-applied sector labels:** J4 assigns sectors statistically from trailing returns. GICS labels are a sensitivity only.
3. **Revised macro:** only real-time or unrevised series are used (`SAHMREALTIME`, HY OAS, Baa), each with an explicit lag rule. NFCI and EBP are excluded from candidates.
4. **Adjusted prices are today's restatement:** disclosed. Effects on monthly ETF rankings are small but nonzero.
5. **Few episodes:** about 9 named episodes in 1998–2026. Pivot metrics are therefore descriptive per episode, and L1 also requires the return contrast.
6. **Hindsight in design:** see §6. Incumbents are capped. Textbook rules carry fixed published parameters.

## 6. Contamination disclosure

**Seen before freezing, all prior repo results:**
- Sector-ETF phase-0 momentum and dual-momentum numbers, 1998–2026.
- The sister team's comparators, 2008–2026, including SPY > 200 d minus SPY at −2.73 %/yr.
- spvector Sharpe and drawdown.
- Risk Radar lifts.
- Cross-asset TSMOM Sharpe 0.54 against 0.56.
- International trend overlay drawdowns.
- Beta-first 64-session results.

**Computed by the lead:** only data availability (first and last dates, counts) and PIT membership, label and price
coverage by year. **No strategy, baseline or episode return was computed.**

**Knowledge:** the lead's model knowledge runs to June 2026 and includes the named episodes and the published textbook
rules. Neither D nor H is unseen in that sense. That is why the protocol has no grids, controls multiplicity, splits D and
H access, and requires L2.

## 7. Deviations

Any departure is logged in the results file's `deviations[]` with a reason. Thresholds and families are never changed
after outcome access; a change needs a v2 header and a new trial-ledger declaration.
