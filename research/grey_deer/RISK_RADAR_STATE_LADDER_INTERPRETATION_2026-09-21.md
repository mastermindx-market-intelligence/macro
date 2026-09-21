# Risk Radar State-Ladder Interpretation — 2026-09-21

This note interprets the preregistered state-ladder calibration result. It is not a model change.

## What the current reconstruction supports

The ladder is empirically useful as a **coarse risk progression**, but not every adjacent state is a separately calibrated probability bucket.

- **Calm / watch:** low and statistically similar. Since 2020, H21 realized rates are 0.0% and 3.4%; the current configured state-only probability is 13% for both.
- **Caution:** correctly behaves like “risk building,” not a loud alert. Since 2020, H21 is 16.1% versus a 17.6% unconditional base and the configured 16%.
- **Elevated:** strong in the longer 2006+ history (40.3% H21, n=124), but **thin in the modern slice** (11.1%, n=36, 90% block interval 0–27.3%). Its modern point estimate is below caution, but the difference interval spans both signs.
- **Risk-off:** the robust high-risk state. Since 2020, H21 is 43.5% (n=239; 90% block interval 27.2–59.5%) versus a configured state-only 33%.

At H10 the modern point estimates are monotonic. At H5 and H21, the modern elevated cell breaks point monotonicity because the elevated state is both thin and transitional; risk-off remains clearly separated.

## Product consequence

Do not collapse the ladder and do not promote caution. Preserve the existing plain-language hierarchy, but treat precise probabilities for the modern elevated state as low-confidence until more issued or prospective evidence accrues.

The UI should continue to reserve its strongest language for risk-off. Caution should remain “risk building.” If model-quality context is surfaced later, it should disclose evidence depth rather than manufacturing a new badge or confidence score.

## Calibration consequence

The configured state-only surface is not numerically identical to the current reconstruction:
lower states generally run below their configured values, while risk-off runs above them. This study
does **not** test the final displayed probability because the live probability also adds a
conjunction bump based on the number of hot Tier-A scares.

Therefore the next calibration question is the complete displayed probability surface
(state + conjunction), evaluated without parameter fitting. Do not change `_PROB_CAL` or
`_CONJ_BUMP` from this state-only study.

## Evidence ceiling

The evidence is reconstructed historical state, not genuinely issued forecasts. Daily windows
overlap; 90% intervals use the preregistered horizon-length moving-block bootstrap. The forward
issued-probability audit remains separate and currently has too few adverse events to validate
the live surface. Any probability change requires a separate preregistered candidate and promotion.
