# CPU leadership recovery — RS threshold findings

Status: RESEARCH RESULT / SHADOW-CHALLENGER ELIGIBLE / ZERO PRODUCTION AUTHORITY
Carrier: macro PR #7572
Protected procedure at adjudication: Mastermind `1358f9d9ab7b612e03c441982d442118116f837d`

## What was tested

The existing US theme stack uses the theme's own rolling relative-price-history percentile as two
different anti-chase cutoffs:

- `basket_score.clean_entry`: block at `rs_pctile >= 0.75`;
- dominant US recommendation: block at `rs_pctile >= 0.85`.

The construction was preregistered before descriptive outcomes in
`ENTRY_RS_THRESHOLD_PREREG_2026-09-21.md`. The descriptive artifact was then frozen as
`evidence/rs-threshold-study.json` (SHA-256
`2d9bb6c6226f95bd7b720e879b25a45bb48710239d3a5f95af0ba4cbd76eb297`).
After that descriptive look, dependence-aware monthly inference was separately preregistered before
inference in `ENTRY_RS_THRESHOLD_INFERENCE_PREREG_2026-09-21.md`.
## Descriptive result — 27-year US SPDR proxy

The committed/store-backed panel spans 1998-12-22 through 2026-09-04, 11 sectors, with all 12
input parquet files hash-bound in the artifact.

Distinct otherwise-clean episode onsets:

| Cohort | Episodes | 21d rel median | 21d DD median | P(DD < -8%) | continuation failure |
|---|---:|---:|---:|---:|---:|
| RS < .75 | 3,523 | +0.068% | -1.896% | 8.88% | 48.77% |
| .75 <= RS < .85 | 1,201 | +0.379% | -1.749% | 7.41% | 43.80% |
| RS >= .85 | 1,686 | +0.106% | -2.040% | 10.68% | 48.70% |

The middle band is not a small corner case: it spans every sector and every decade in the sample.
Under the incumbent .75 rule, 59.5% of its blocked episodes later re-open below .75 within 21
sessions, median wait 3 sessions. The median move before that re-open is -0.37% absolute / -0.64%
relative — a real cost to waiting, but not itself proof that immediate entry is superior.
## Dependence-aware inference

Frozen result: `evidence/rs-threshold-inference.json`, SHA-256
`ec5268b932b9fff368149383ff25023232773930fac0d2128b963c221802a063`.
Monthly cohort means are paired only where both cohorts exist; Newey-West uses 3 monthly lags and
the moving-block bootstrap uses 3-month blocks, 5,000 draws, seed 20260921.

### A. .75-.85 minus <.75 — does .75 protect us?

267 overlapping months:

- 21d relative return difference: +0.063%, NW p=0.735, bootstrap CI [-0.308%, +0.403%].
- 21d maximum-adverse-excursion difference: +0.108% (less adverse), p=0.509,
  CI [-0.204%, +0.413%].
- >8% drawdown-risk difference: +0.34pp, p=0.736, CI [-1.51pp, +2.42pp].
- continuation-failure difference: -3.06pp, p=0.195, CI [-7.27pp, +1.72pp].

**Ruling:** there is no measured evidence that the .75 cutoff improves chase-risk protection.
The descriptive middle-band advantage is not statistically decisive after dependence correction,
so this is not evidence to promote .85 live. It is sufficient to reject the claim that .75 is
already validated as the necessary protective boundary and to advance .85 as a challenger.
### B. >=.85 minus .75-.85 — is there a real hotter zone?

261 overlapping months:

- 21d relative return difference: -0.323%, NW p=0.0515,
  bootstrap CI [-0.637%, -0.002%].
- 21d maximum-adverse-excursion difference: -0.172%, p=0.144,
  CI [-0.384%, +0.063%].
- >8% drawdown-risk difference: +0.56pp, p=0.628, CI [-1.80pp, +2.67pp].
- continuation-failure difference: **+6.05pp**, NW p=0.0139,
  bootstrap CI **[+1.34pp, +10.45pp]**.

**Ruling:** the data support keeping an anti-chase boundary near the existing .85 region rather
than removing extension protection entirely. The strongest result is continuation failure, not a
proven drawdown reduction.
## September-18 motivating tape — acceptance exemplar, not tuning data

Independent native audit on #7669 exact head `521676dfa795615bdb8a77b67e76ae84387de341`
reproduces all 49 stored theme rows. Among seven existing Enter/Accumulate themes, three are
blocked **only** by the .75 RS veto:

| Theme | recommendation | RS percentile | native clean-entry quality | separate ATR-extension context |
|---|---|---:|---:|---|
| AI Semiconductors | Accumulate | 0.845 | 0.70 | 1.77, extended |
| Memory, HBM & Storage | Accumulate | 0.845 | 0.80 | 1.83, extended |
| AI Infrastructure | Accumulate | 0.833 | 0.80 | 0.87, normal |

Thus all three motivating AI-hardware themes sit in the exact historical middle band the .75 rule
deletes. But the separate extension texture disagrees across them: Semis/Memory are extended while
AI Infrastructure is not. That is evidence that **relative-strength leadership and own-price chase
risk must remain separate dimensions**.

The ATR join is date/count matched but does not prove atomic generation or identical membership;
it remains context-only.
## Model decision at this boundary

1. **Do not hard-code CPUs or semiconductors.**
2. **Do not change the live .75 threshold from this study.**
3. Admit an **RS<.85 clean-entry challenger** to the existing promotion/evaluation path, with zero
   live gate/rank/trade authority.
4. Preserve direct own-price extension as a separate chase-risk hypothesis. Mastermind already
   owns a display-only close-based ATR extension texture in `engine/theme_extension.py`:
   median-member 1.5 ATR = extended, 3.0 = stretched, 5.0 = parabolic.
5. Next experiment: preregister whether the existing 1.5-ATR extension boundary adds protection
   inside the RS<.85 otherwise-clean population. If it does, the candidate policy is
   **leadership allowed through .85 + direct extension veto**, not “strong relative performance =
   overextended.”
6. Keep Prophet leadership discovery separate from entry permission. Lane C / Theme Intelligence
   can surface concentrated compute leadership with all authority false while the entry geometry
   decides whether to act now or wait for a pullback.

This closes a mechanism uncertainty, not the parent mission. China controlled ordering #6992,
Theme Intelligence Lane C/Lane E convergence, Prophet F3 theme-structure authority, and prospective
shadow evidence remain separate gates.
