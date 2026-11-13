# Incumbent SI — failure-audit packet for Astra Pro

SI engine-upgrade lead, 2026-11-12. Macro pin a53877ee8 (2026-11-10). Audit period:
calls ≤2026-11-10 (self-grader ledger ends 2026-10-16), outcomes ≤2026-11-11. All
figures are replication on a seen period; derived families are touched, confirmed
only forward. Engine-published figures marked LOOK. Diagnosis of the released
audit period. Full-precision tables (same numbers, more rows): macro PR #11096,
research/rotation_core/v4/pro_packet/engine_diagnosis/ —
https://github.com/mastermindx-market-intelligence/macro/pull/11096

## 1. The two graded records (definitions exact)

**Self-grader** (calls.parquet; 4,294 calls 2026-06-28→10-16, uniformly score-v1 —
the v2 stamp shipped 11-02, after the ledger ended): horizons 21/63/126 TRADING
sessions; entry at the NEXT bar's close (t+1); excess = same-window SPY difference;
dir_hit = correct up + correct down over ALL graded rows INCLUDING Neutral (Neutral
can never hit); rank-IC = mean per-date Spearman(score, fwd). After freeze
exclusions the graded sample is 770 rows at h21 = the 11 sector ETFs × 70 dates
(zero baskets survive) and 352 at h63.

**Track record** (subsector snapshots, 16,131 rows ≤ cut): all 269 keys (268 Finviz
subsectors + megacapgenerals). emerging_score = 0.5·z_accel + 0.8·nanmean(z1W,z1M)
+ 0.3·z1W from the Finviz perf snapshot; entry at the SAME bar's close; h CALENDAR
days; return = member-EW minus SPY; ≥3 priced members. n = 15,593/14,517/9,406 at
5/21/63.

## 2. Incumbent conviction score construction (v1)

state = 0.6·(50−pos)/50 + 0.4·phase_dir {Trough .5, Recovery .6, Expansion .25,
Peak −.4, Downturn −.55}; +0.12 on BUY signal, −0.12 on SELL; hard cap −0.25 when
the fast-rollover detector fires. Gate: score × clip(gate·(1+0.25·β·risk_on), 0.2,
1.0) for longs; absolute-trend-gate failure halves a positive score; momentum adds
0.5·(peer-percentile ±0.3); caps: below-trend or pos ≥ 80 or crowded ≥ 0.34 → score
≤ 57. pos is the LEGACY 0–100 detrended-oscillator stochastic (EMA252 detrend,
EMA10 smooth, 252-bar stochastic) — the ontology's pos_v2 is used elsewhere in the
same pipeline (mixed semantics; the two are different quantities).

## 3. Results: below chance, not merely unskilled

Placebo = within-date permutation of labels AND scores, 2,000 draws, seed 20261112
(same universe, dates, mix — definition held fixed). observed | placebo [2.5–97.5]:

| ledger·h | metric | obs | placebo band | base rate |
|---|---|---|---|---|
| self 21 | hit, Neutral incl | 25.2% | 27.1–31.0 below | always-up 51 |
| self 21 | hit, Neutral excl | 44.8% | 48.3–55.2 below | coin 50 |
| self 21 | rank-IC | −.079 | ±.068, p=.014 | 0 |
| self 63 | hit, incl | 29.3% | 28.7–36.9 inside | 49 |
| self 63 | hit, excl | 45.6% | 44.7–57.5 inside | 50 |
| self 63 | rank-IC | −.147 | ±.110, p=.0065 | 0 |
| track 5 | emerging hit | 43.8% | 42.5–50.0 inside | board-EW up 46.3 |
| track 21 | emerging hit | 41.5% | 42.6–50.2 below | 46.5 |
| track 63 | emerging hit | 32.1% | 39.3–48.6 below | 44.2 |
| track 21 | score IC | −.025 | ±.017, p=.0015 | 0 |
| track 63 | score IC | −.135 | ±.020, p≈0 | 0 |

The h63 hit metrics sit inside their bands; the h63 case rests on rank-IC. Each
direction misses its own base rate: self h21 up calls 40.0% vs P(up)=51.0 (−11 pp),
down 45.7% vs 49.0; h63 up 39.1% vs 46.3, down 48.2% vs 53.7.

## 4. Where the damage is (score ~ rs20 + rs63 + heat, pooled OLS, date-cluster SE)

| ledger·h | R² | rs63 β (SE) | rs20 β (SE) | IC score | IC rs63 | IC resid |
|---|---|---|---|---|---|---|
| self 21 | .19 | −97.3 (5.9) | +65.5 (24.2) | −.079 | +.104 | −.095 |
| self 63 | .20 | −85.2 (7.4) | +78.8 (23.3) | −.147 | +.168 | −.068 |
| track 21 | .86 | −4.6 (0.1) | +3.9 (0.3) | −.053 | −.041 | −.126 |
| track 63 | .87 | −4.9 (0.1) | +4.7 (0.4) | −.206 | +.178 | −.255 |

Both take mildly predictive relative strength and flip the sign through
state/acceleration transforms (washed-out = +setup prefers fallen names). Not an
AI-cluster artefact: removing AI keys/XLK makes the IC worse.

## 5. Sample reality and eras

One date cluster everywhere. Independent windows (mine = the engine's own LOOK):
track 18.86/9.0/3.95/0.84 at 5/10/21/63 vs the engine's promotion floor 6.0;
engine verdict "measuring", all horizons proven:false. Self: 3.47/0.49. Point
estimates only — no horizon curves, regime splits or repair acceptance supportable.
Era note (descriptive, confounded with market regime): worst damage pre-07-16;
post-rollover-fix conditional hit ≈ coin, IC still negative.

## 6. Input faults ruled out as the explanation

Dividend-vintage breadth cache (#11124, fix #11125 merged): 0 conviction-scored
calls read it; track contamination <1% of member-weeks, direction pessimistic.
Staleness: the sector_central lane ends 10-16 (24 audit days uncalled). Baskets:
membership back-projected (35/49); member prices start 2014.

## 7. The ask

Chairman's frame: call sector/asset rotations and risk pivots EARLY; durable washout
bottoms; breadth of competing groups; always read RSP beside SPY; sector level alone
is too coarse; the modern regime (2020+) is the test bed. The incumbent turn organs
are being delivered to the desk as hindsight alert series on block D
(2020-01-02→2023-12-29): rolling-over chip, phase_v2, subsector_turn turn_down (F2
tops); us_basket_turn WASHED_OUT→CONFIRMED (F3 bottoms). Repair hypotheses to
pre-declare and test on reconstructed history ≤2023-12-29 (hindsight-labelled,
three-way reporting: all groups / listed-before / by cluster; same-cohort
counterfactuals): extension guard (fade stretched entries), strong-vs-buyable
separation, grading turns not levels, equal-vote confluence count (approval §C).
