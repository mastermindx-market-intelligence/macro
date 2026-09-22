# Risk Radar Displayed-Probability Audit — Interpretation

This note interprets the preregistered no-fit audit. It changes no live model value.

## What the corrected historical replay supports

The complete shipped probability surface — corrected gated state plus the existing hot-Tier-A
conjunction bump — has **useful discrimination** but is **not numerically calibrated cell-by-cell**
in the modern historical reconstruction.

For 2020+ H21:

- unconditional event rate: **17.6%**;
- mean displayed probability: **19.4%**;
- Brier skill versus the unconditional base-rate forecast: **+8.8%**;
- weighted absolute exact-cell calibration error: **6.1 percentage points**.

The mean-level gap is +1.8pp, but its 90% moving-block interval spans zero. The stronger finding is
inside the exact discrete cells rather than the aggregate mean.

Among H21 cells with at least 100 observations:

| Displayed | n | Observed | Interpretation |
|---:|---:|---:|---|
| 13% | 300 | 1.3% | calm/watch floor is historically much too high in this modern replay |
| 16% | 746 | 12.2% | modest overstatement; block interval includes 16% |
| 19% | 270 | 24.8% | directionally higher risk; block interval includes 19% |
| 39% | 100 | 49.0% | high-risk state remains genuinely high; block interval is wide |

Those non-thin cells are point-monotonic. The surface therefore separates lower from higher risk
better than an unconditional forecast, but the labels should not be read as precision-grade
frequencies.

## Conjunction bump

Within caution, the exact H21 cells move from 16% at zero/one hot Tier-A scare to 19% at two hot
scares and 22% at three. Realized rates are 12.2%, 24.8%, and 24.2% respectively; the 22% cell is
thin (n=66). This is directionally consistent with extra confluence carrying more risk, but it is
not enough evidence to fit or alter the bump.

## Shorter horizons

The same broad pattern appears at H5/H10: positive Brier skill versus the unconditional base, with
very low realized event rates in calm/watch and stronger realized rates in risk-off. Modern Brier
skill is +4.8% at H5 and +7.1% at H10.

## Product consequence

Treat the current percentages as a **risk gradient with evidence limits**, not as exact actuarial
odds. The lower-state floor is the clearest modern historical miscalibration. High-risk cells
retain useful separation but several are thin.

If the UI is upgraded, the scientifically supported direction is evidence-depth disclosure
(sample depth / historically broad vs thin) and wording that avoids false precision. Do not create
a second alert tier, do not turn the percentages into trade authority, and do not silently replace
them with fitted values.

## Calibration consequence

No retune follows from this audit. The next model step, if pursued, is a separately preregistered
candidate that tests a simpler or recalibrated probability surface against the **unchanged current
surface** under held-out / prospective promotion rules. The issued-forward probability ledger
remains a separate, higher-authority evidence class.

## Evidence ceiling

This is current-code historical reconstruction with overlapping forward windows. Moving-block
uncertainty is used, but reconstructed states/probabilities are not genuinely issued forecasts.
