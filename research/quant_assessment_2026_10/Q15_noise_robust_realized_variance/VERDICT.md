# Q15 — Verdict: REJECT (clear)

**Trial:** Q15-T1. This was the only confirmatory comparison, and it ran once.
**Prereg:** `PREREG.md`, sha256 `f1dc7c14e2e8d79a685e7aa80ed01ff375b9ee4f4c37bf2e1e95af8e37254f2f`. It was frozen at `Fri Oct  9 10:13:59 UTC 2026` (`FREEZE.log`), before any outcome on the admitted data was computed. No amendment exists.
**Served model:** Opus 5.5, model ID claude-opus-5-5. Author. An independent read-only audit returned PASS_WITH_FIXES (0 blockers, 0 majors, 6 minors); its findings are disclosed in this file, REQUIREMENTS.md and the PR body. None changes the verdict, and no result-bearing code or output was changed after the confirmatory run.

## Question

Admitted intraday tape: Coinbase BTC-USD hourly candles. Does the noise-aware weekly variance label give a more reliable measurement than fixed-interval hourly RV? Labels:

- **L2:** non-flat-top Parzen realized kernel. The bandwidth comes from the BNHLS rule with ξ² fitted on training data only.
- **L1:** fixed-interval hourly RV.

Reliability is measured by the persistence of week-to-week log variance. Measurement noise in a variance label attenuates its lag-1 autocorrelation, so a cleaner label of the same latent quantity should persist more.

## Decision-bearing result (holdout 2022-01-03 .. 2026-09-28)

| Quantity | Value |
|---|---|
| ρ1(log L2) | 0.5322 |
| ρ1(log L1) | 0.5505 |
| **Δρ = ρ1(L2) − ρ1(L1)** | **−0.0183** |
| 95% moving-block bootstrap CI (block 8 weeks, 2000 reps, seed 1515, pairs kept within blocks) | [−0.0489, +0.0123] |
| Bootstrap sd | 0.0154 |
| Practical bar (prereg) | Δρ ≥ +0.05 with CI lower bound > 0 |

The KEEP rule is not met. The point estimate has the wrong sign, and the whole CI lies below the +0.05 bar. Under the frozen decision rule this is **REJECT (clear)**: the upper CI bound, +0.012, is below the practical bar.

## Honest N, support and attrition

- **Holdout:** 248 calendar weeks. All 248 are eligible: ≥152 of 168 hourly candles, no internal gap over 6 h, and all 8 daily closes present. That gives **247 consecutive-week pairs**. The 31 non-overlapping 8-week blocks all contain pairs. The prereg minimum support is 104 weeks and 13 blocks, so support is met.
- **Training (2016-01-04 .. 2021-12-27):** 313 calendar weeks, 310 eligible. Lost: 2 for a missing daily close and 1 for a gap. No week was imputed. Non-positive labels count as attrition by rule; none occurred.
- **Eligibility-code disclosure (independent audit):** the non-positive-label drop in `evaluate.py` (line 337) also checks the descriptive label `L2_rk_week_feasible`, which PREREG does not declare as an eligibility input. It dropped zero weeks in either split (no `nonpositive_label` reason appears in `result_confirmatory.json` attrition), so the primary sample is unchanged. Any future amendment should restrict primary eligibility to the declared labels.
- **Training-only hyperparameter:** ξ²_train = 2.99e-4, the median of training ω̂²/RV₆. With n ≈ 168 this gives bandwidth H = 3 for every holdout week. The holdout was never used to choose H, the block length, or the estimator.

## Falsifier and stop rule

The frozen falsifier says to retain the coarse proxy if the noise share is below 1%, if ξ²_train = 0, or if the KEEP rule fails.

- The median training noise share was 9.1%, not below 1%.
- ξ²_train is greater than 0.
- **The KEEP rule failed, so the falsifier fired.**
- **Code-to-prereg disclosure (independent audit):** the `evaluate.py` KEEP branch (line 376) and `falsifier["fired"]` do not test the §16 "noise share below 1%" branch; they record it only as `noise_share_below_1pct`. The code could therefore have issued KEEP where the prereg forbids one. That did not happen here: the verdict is REJECT and the training noise share is 9.1%. Any reuse must add `and not noise_share_below_1pct` to the KEEP condition.

Consequence: the simple fixed-interval proxy is retained with its stated limitation. Weekly hourly RV includes a small amount of microstructure-type autocorrelation, and this tape cannot separate it from economic variation. No high-frequency precision is manufactured. The stop rule bars any further holdout search on this question.

## Descriptive, not decision-bearing

| Comparison | Δρ | 95% CI |
|---|---|---|
| L1 − L0 (hourly RV vs daily-close RV) | **+0.338** | [+0.210, +0.423] |
| Week-feasible H (BNHLS with the in-week ξ²) vs L1 | −0.0426 | [−0.0874, −0.0001] |
| Primary, block length 4 | −0.0183 | [−0.0514, +0.0124] |
| Primary, block length 13 | −0.0183 | [−0.0437, +0.0078] |

- **Training-period L2 − L1:** −0.0133. **Holdout halves:** −0.0075, then −0.0363. The sign is the same in every slice.
- **Level effect:** mean log(L2/L1) = −0.041, so the kernel removes about 4% of hourly RV. Mean log(L1/L0) = +0.219, so hourly RV is about 24% above daily-close RV.
- **Signature curve, holdout mean of RV(k-hour)/RV(1h):** 2h 0.978, 4h 0.951, 6h 0.941, 12h 0.923, 24h 0.926. The training values are similar (6h 0.914). The curve falls gently, which is typical of mild intraday mean reversion. It is not the steep 1/k bid/ask signature.
- **Median noise share by year:** from 0.8% (2022) to 15% (2017). The median weekly lag-1 return autocorrelation runs from about −0.06 to +0.015 every year, and never crosses the −2/√168 ≈ −0.154 flag threshold.

## Interpretation

On this tape the apparent noise excess ω̂² is not classical bid/ask noise. With BTC-USD spreads near 1 bp, i.i.d. noise of that size would contribute only about 0.07% of weekly RV across 168 hourly returns. Our hypothesis, not a tested claim, is that the excess measured at the 1h-vs-6h scale (median about 9%) reflects mild intraday mean reversion plus estimator noise. What the trial shows is narrower: removing that excess does not raise week-to-week persistence. The point estimate is negative (−0.018), but the 95% CI [−0.049, +0.012] includes 0, so the data do not establish that the kernel lowers persistence or discards economic variation.

The large, well-supported reliability gain comes from **using intraday data at all**: daily-close RV (L0) moving to hourly RV (L1) gives Δρ ≈ +0.34. Noise correction at hourly resolution adds no measurable reliability.

## Scope of the verdict

The verdict covers exactly one construction: the Parzen kernel label at hourly-candle resolution on Coinbase BTC-USD, with weekly windows and lag-1 persistence as the ruler. It does **not** say noise-aware estimators fail at tick/quote resolution. Tick and quote data are not admitted here; acquisition belongs to TP1 #8660.

The estimator module stays a research reference. Its synthetic controls behave as theory predicts (`mc_bias_table.json`, all prereg criteria pass). It is ready for the day an owner admits tick or quote data.

## Limitations

- Only one intraday resolution (1h candles) and one instrument were admitted. Candle closes are last-trade prints, not mid quotes, so the noise model cannot be checked against quotes.
- Lag-1 persistence is a reliability proxy, not an oracle. It assumes latent weekly variance persistence is the same for both labels, which holds by construction because they measure the same window. It also assumes the measurement errors are roughly independent week to week.
- Under the 2016–2026 crypto 24/7 session there is no overnight break. The overnight bucket here contains only data gaps over 6 h, and none occurred in the holdout. Equity session/overnight treatment is implemented and unit-tested, but untested empirically here.
- The bootstrap CI treats the frozen bandwidth as fixed. ξ²_train uncertainty is not propagated. Given H = 3 throughout and a negative sign in every slice, this cannot plausibly reverse the verdict.
- The hand-typed `--stamp` values on two RUNS.log lines are inaccurate. Bracketing `date -u` readings are disclosed in the appended RUNS.log note line. The independent audit confirmed that the synthetic line's stamp (10:17:58) is later than a witness snapshot (10:17:52) that already contains that line, so it cannot be true; the field name `stamp_utc_from_date_u` is also misleading, because the value was typed by hand. RUNS.log is append-only and is left unedited; future trials should have `evaluate.py` write its own UTC timestamp instead of accepting `--stamp`.

## Provenance

| Input | sha256 |
|---|---|
| `data/coinbase/btc_hourly.parquet` (macro-main data, vintage cdab6268, read-only) | `1c1b02fd8cd6b0b7d2aec6563abe896694b27659dcb6fed17cf84bf6b450a34d` |
| `data/coinbase/btc_daily.parquet` | `4ddd11111becf7540788f39934377418dde69e73a4ddfa6eca99828b3a5cfc95` |
| `engine/vol_forecast.py` (incumbent, unmodified) | `bcd6ec2cc8c116b469173ab475dc495be7e024b4ea452b9d1cf6de58301e06c0` |
| `engine/vol_noise_robust_realized.py` | `e54eb5782885279e81fdfdd4c8c2c554e567ebb6078a26c4554c85608a44dd2b` |
| `evaluate.py` | `91fd4b01a42901d4340406dcff208e7ddae5fc7ae38d3949e82cb890a365649f` |

- **Outputs:** `result_confirmatory.json` (`db85be89…4cb5`), `labels_weekly.csv` (`ed7cbcc6…bf89`).
- **Label version:** `8927a507ec813145cfbdfff5c05677e15dfac08a34afe01f13b5f75f7cf04f0f`. Labels carry `research_only=true` and `accepted_label=false`. They do not replace any accepted label, ruler, or P5 estimator; MAS-260 and the existing variance owners are unchanged.
