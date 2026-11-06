# Q07 verdict: KEEP (weak vs EWMA; research candidate only; no production effect)

**Verdict: KEEP (weak vs EWMA).** This comes from the single pre-registered confirmatory trial (PREREG.md, sha256 `6d3b1962…d4de`, frozen 2026-10-09T09:34:35Z).

The challenger is a per-asset fitted log-HAR(1,5,22), refit on an expanding window every 21 sessions with an embargo and Duan smearing. Over the 2008-01-02 → 2026-09-09 holdout its **point estimate** beats every simple control by at least 3% relative QLIKE, and every 95% paired block-bootstrap interval of the mean differential has a lower bound above 0. Against EWMA (C2) the margin is weak: the relative-CI lower bound is 2.8%, below the 3% bar on the interval scale, and the HAC t is 1.85 (§1 below). The outcome is the same at all three declared floors.

"KEEP" means only that the fitted challenger survives as a research candidate. It changes nothing:
- no cone probability
- no model promotion
- no portfolio budget
- no live forecast default

`production_effects("KEEP")` returns all False, which `test_req6_…` checks. Any adoption is a separate decision for the owner.

## Primary trial (h = 21, label `DAILY_CC_MSR`, QLIKE, floor 1e-8)

Panel shape:
- 13 ETFs, unbalanced (XLC and XLRE enter late)
- 4,701 holdout sessions
- **honest N = 37 non-overlapping 126-session blocks**; the prereg minimum is 30
- 223 non-overlapping 21-session target windows

| Control | Mean QLIKE control | Mean QLIKE H | Rel. improvement | 95% block CI (rel.) | 95% block CI (diff) | NW-HAC t (lag 42) |
|---|---|---|---|---|---|---|
| C0 incumbent `har_vol²` | 0.7051 | 0.3206 | **54.5%** | [49.0%, 58.3%] | [0.233, 0.632] | 3.55 |
| C1 RV22 persistence | 0.4308 | 0.3206 | **25.6%** | [19.3%, 31.7%] | [0.060, 0.173] | 3.90 |
| C2 EWMA λ=0.94 | 0.3809 | 0.3206 | **15.8%** | [2.8%, 22.9%] | [0.0071, 0.141] | 1.85 |
| C3 scaled incumbent k·C0 | 0.4847 | 0.3206 | **33.9%** | [24.8%, 39.4%] | [0.082, 0.299] | 2.84 |

Floor sensitivity: the whole pipeline (fit plus loss) was recomputed at each floor. KEEP holds at every floor, so `floor_flip=false`.

| Floor | Decision | Rel. vs C2 | No. of holdout targets below floor |
|---|---|---|---|
| 1e-10 | KEEP | 15.8% | 0 |
| 1e-8 | KEEP | 15.8% | 0 |
| 1e-6 | KEEP | 15.9% | 0 |

## What binds, and what the honest reading is

1. **The binding comparison is EWMA (C2), and it is the weak one.** The bootstrap interval excludes zero, but only just: the lower bound on relative improvement is 2.8%, below the 3% bar on the interval scale, while the point estimate is 15.8%. The Newey–West t is 1.85, under the conventional 1.96. The pre-registered rule is the point estimate ≥ 3% plus a bootstrap difference interval above 0, and that rule is met. Under the prereg the HAC t is a descriptive cross-check, and here it disagrees in strength. Read this as "HAR beats EWMA on average, with modest dependence-aware support", not as overwhelming evidence.
2. **The gain over EWMA depends on regime.** H loses to C2 in 7 of 19 calendar years: 2008, 2009, 2012, 2013, 2017, 2021 and 2023 (`results/per_year.csv`). Per asset, H beats C2 on 12 of 13 names. XLRE is a tie at −0.03%.
3. **The gain is specific to QLIKE.** These secondary losses are descriptive and cannot change the verdict. On squared log error, H vs C2 is −6.3% with CI [−19.2%, +4.1%]. On absolute vol-scale error, H vs every control has a CI that spans 0. QLIKE penalises under-prediction asymmetrically. The smeared HAR forecast is calibrated to the arithmetic mean, so much of its edge is avoiding variance under-forecasts rather than being closer in log or vol terms.
4. **The incumbent C0 is badly biased low on this target.** Its QLIKE of 0.705 is the worst of all models. Level-fixing it (C3) helps, but C3 still loses to plain RV22. Both the incumbent's level (simple returns, ddof=0 on 2- and 5-session windows) and its shape hurt on a 21-session forward variance target. This is a finding about the incumbent as a *variance forecast*. The incumbent was not designed to be a calibrated variance forecast, and this study does not claim it was.
5. **Descriptive robustness rows, which cannot change the verdict:**
   - The balanced 11-asset panel matches the primary result (vs C2: 17.1%, CI [3.4%, 24.9%]).
   - A rolling 1260-row HAR does **not** beat EWMA (5.8%, CI [−10.3%, 17.1%]).
   - At h=5, H vs C2 is 3.2% with CI [−0.3%, 6.5%], so it does not clear.
   - At h=63, H vs C2 is 34.6% with CI [9.0%, 42.9%], but honest N is only 12 blocks.
   - So the edge over EWMA grows with horizon and needs the expanding window.
6. **Coverage (80% nominal, from training log-ratio quantiles):**

   | Model | Coverage |
   |---|---|
   | H | 77.7% |
   | C0 | 76.7% |
   | C1 | 76.4% |
   | C2 | 76.2% |
   | C3 | 76.8% |

   Every model is slightly under-covered. H is closest to nominal.

## Support and attrition

- 11 assets keep 4,701 of 4,722 holdout origins. The last 21 are dropped because their targets have not matured.
- XLC keeps 1,521 of 2,088 (546 dropped before its 504-row training minimum; first kept 2020-08-19).
- XLRE keeps 2,199 of 2,766 (546 dropped for the same reason; first kept 2017-12-07).
- 3,180 of 4,701 sessions have fewer than 13 assets.
- No row was dropped for an incomplete control once H existed.
- Cohort attrition decided before the outcome: `data/stocks/` was excluded because its split/adjustment status could not be confirmed (PREREG §3).

## Limitations

- **The target is the daily close-to-close mean squared return (`DAILY_CC_MSR`), not high-frequency integrated variance.** This is a noisy proxy. Q15's noise-robust RV would be a different estimand and a different study identity. Labels never mix silently (`LabelMismatchError`).
- **There is one universe:** US ETFs on a single vendor vintage (`macro-main/data/yahoo` @ cdab6268). Single names, other asset classes and crypto were not tested.
- 37 honest blocks is only modestly above the 30 minimum. The C2 margin is thin under HAC.
- **Survivorship:** every cohort ETF is still listed, so delisted volatility products are absent. The cohort is a fixed ETF set, not a stock universe, which limits the effect.
- **Prices are back-adjusted, not point-in-time.** The Yahoo `close` is dividend- and split-adjusted as of the vintage, so later corporate actions rescale earlier prices. A pure rescale leaves log returns unchanged; on the 13 frozen files the adjustment moves the mean squared daily log return by −0.01% to −0.82% and no day differs by a split-sized amount (`POST_FREEZE_DISCLOSURES.md` §3). This bounds the effect; it does not prove it is zero.
- **Post-freeze record gaps.** evaluate.py changed after the freeze and before run 1 (`746f…` → `dc5c…`, diff not recoverable), and RUNS.log entries carry no timestamp. Both logged runs used `dc5c…`, which an independent audit found conforms to PREREG. See `POST_FREEZE_DISCLOSURES.md` §1–§2.
- **Q14 dependency:** Q14 (implied-vs-forecast variance) may take this module as a forecast input only after its own admission. Nothing here makes it a signal.

## Model served

The author was Claude Opus 5.5 (model ID `claude-opus-5-5`), invoked as the Q07 author by the workflow harness. The finishing stage (independent-audit fixes: disclosures, two added tests, headline wording) was also Claude Opus 5.5 (`claude-opus-5-5`); it changed no result.
