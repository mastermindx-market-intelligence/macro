# Fear/Greed v1: frozen descriptive replay

**Retrospective associations, not an executable backtest or accepted predictive signal.**

Observation cutoff: 2026-10-16. Common eligible span: 2007-03-07 to 2026-10-13; 4921 sessions. Rules, horizons, cooldown and bootstrap were frozen before this run.

Every rule uses the same eligible-date universe. Starts are at least 21 sessions apart within each rule. Confidence intervals use 2,000 moving-block resamples of three chronological events. No interval is published with fewer than 12 episodes.

## all

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 56 | -0.05% | [-1.02, +0.94]% | 53.6% | -2.01% | 10.7% | +0.03% |
| high_vix_level / 10d | 56 | +0.03% | [-1.13, +1.01]% | 64.3% | -2.91% | 17.9% | +0.25% |
| high_vix_level / 21d | 56 | +1.09% | [-0.00, +2.19]% | 66.1% | -3.94% | 33.9% | +1.17% |
| vix_relief / 5d | 180 | +0.15% | [-0.25, +0.57]% | 58.3% | -1.14% | 5.6% | +0.09% |
| vix_relief / 10d | 180 | +0.47% | [+0.02, +0.91]% | 62.8% | -1.70% | 10.0% | +0.32% |
| vix_relief / 21d | 180 | +1.08% | [+0.43, +1.71]% | 65.0% | -2.73% | 20.6% | +0.95% |
| relief_broadening / 5d | 144 | +0.17% | [-0.18, +0.47]% | 62.5% | -1.11% | 3.5% | +0.15% |
| relief_broadening / 10d | 144 | +0.44% | [-0.12, +0.93]% | 70.1% | -1.63% | 6.9% | +0.40% |
| relief_broadening / 21d | 144 | +1.27% | [+0.43, +2.04]% | 69.4% | -2.48% | 14.6% | +1.13% |
| stress_broadening / 5d | 121 | +0.73% | [+0.29, +1.16]% | 66.1% | -1.18% | 4.1% | +0.49% |
| stress_broadening / 10d | 121 | +0.96% | [+0.49, +1.44]% | 63.6% | -1.85% | 9.1% | +0.60% |
| stress_broadening / 21d | 121 | +1.11% | [+0.29, +1.95]% | 63.6% | -3.12% | 19.0% | +0.77% |
| shock_watch / 5d | 96 | +0.20% | [-0.37, +0.76]% | 61.5% | -1.58% | 6.2% | +0.27% |
| shock_watch / 10d | 96 | +0.36% | [-0.48, +1.09]% | 64.6% | -2.24% | 12.5% | +0.20% |
| shock_watch / 21d | 96 | +0.75% | [-0.32, +1.68]% | 67.7% | -3.34% | 24.0% | +0.74% |

Eligible-date 21-session baseline: mean +0.99%, positive 66.9%, 5% drawdown 18.0% (4903 overlapping date outcomes; no confidence interval).

## 2007 2019

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 36 | -0.09% | [-1.29, +1.24]% | 50.0% | -2.06% | 13.9% | -0.09% |
| high_vix_level / 10d | 36 | -0.37% | [-1.78, +0.99]% | 63.9% | -3.14% | 22.2% | +0.16% |
| high_vix_level / 21d | 36 | +0.87% | [-0.46, +2.25]% | 63.9% | -4.26% | 38.9% | +0.77% |
| vix_relief / 5d | 118 | -0.04% | [-0.45, +0.37]% | 59.3% | -1.15% | 5.9% | -0.06% |
| vix_relief / 10d | 118 | +0.21% | [-0.28, +0.66]% | 61.9% | -1.77% | 10.2% | +0.06% |
| vix_relief / 21d | 118 | +0.76% | [+0.07, +1.46]% | 62.7% | -2.87% | 22.9% | +0.66% |
| relief_broadening / 5d | 92 | +0.10% | [-0.30, +0.49]% | 64.1% | -1.10% | 3.3% | +0.08% |
| relief_broadening / 10d | 92 | +0.43% | [-0.29, +1.04]% | 71.7% | -1.57% | 7.6% | +0.49% |
| relief_broadening / 21d | 92 | +1.13% | [+0.14, +1.97]% | 68.5% | -2.35% | 15.2% | +1.00% |
| stress_broadening / 5d | 80 | +0.91% | [+0.42, +1.44]% | 67.5% | -1.12% | 3.8% | +0.70% |
| stress_broadening / 10d | 80 | +1.01% | [+0.49, +1.60]% | 63.7% | -1.67% | 7.5% | +0.66% |
| stress_broadening / 21d | 80 | +1.02% | [-0.06, +2.00]% | 65.0% | -3.13% | 18.8% | +0.66% |
| shock_watch / 5d | 65 | +0.45% | [-0.13, +1.03]% | 64.6% | -1.41% | 6.2% | +0.31% |
| shock_watch / 10d | 65 | +0.40% | [-0.63, +1.28]% | 64.6% | -2.10% | 12.3% | +0.42% |
| shock_watch / 21d | 65 | +1.10% | [+0.07, +1.99]% | 70.8% | -3.12% | 21.5% | +0.80% |

Eligible-date 21-session baseline: mean +0.82%, positive 65.9%, 5% drawdown 18.3% (3217 overlapping date outcomes; no confidence interval).

## 2020 2026

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 20 | +0.01% | [-1.40, +1.40]% | 60.0% | -1.91% | 5.0% | +0.25% |
| high_vix_level / 10d | 20 | +0.74% | [-0.64, +2.19]% | 65.0% | -2.49% | 10.0% | +0.41% |
| high_vix_level / 21d | 20 | +1.47% | [+0.02, +2.76]% | 70.0% | -3.37% | 25.0% | +1.89% |
| vix_relief / 5d | 62 | +0.52% | [-0.28, +1.48]% | 56.5% | -1.10% | 4.8% | +0.35% |
| vix_relief / 10d | 62 | +0.98% | [+0.12, +2.01]% | 64.5% | -1.59% | 9.7% | +0.82% |
| vix_relief / 21d | 62 | +1.67% | [+0.46, +3.17]% | 69.4% | -2.49% | 16.1% | +1.50% |
| relief_broadening / 5d | 52 | +0.28% | [-0.31, +0.84]% | 59.6% | -1.12% | 3.8% | +0.27% |
| relief_broadening / 10d | 52 | +0.44% | [-0.36, +1.28]% | 67.3% | -1.75% | 5.8% | +0.22% |
| relief_broadening / 21d | 52 | +1.51% | [+0.01, +2.99]% | 71.2% | -2.71% | 13.5% | +1.36% |
| stress_broadening / 5d | 41 | +0.38% | [-0.47, +1.20]% | 63.4% | -1.31% | 4.9% | +0.08% |
| stress_broadening / 10d | 41 | +0.85% | [-0.18, +1.86]% | 63.4% | -2.19% | 12.2% | +0.48% |
| stress_broadening / 21d | 41 | +1.29% | [-0.26, +2.67]% | 61.0% | -3.09% | 19.5% | +0.99% |
| shock_watch / 5d | 31 | -0.32% | [-1.54, +0.69]% | 54.8% | -1.95% | 6.5% | +0.19% |
| shock_watch / 10d | 31 | +0.28% | [-1.27, +1.63]% | 64.5% | -2.54% | 12.9% | -0.27% |
| shock_watch / 21d | 31 | +0.02% | [-2.14, +1.97]% | 61.3% | -3.81% | 29.0% | +0.60% |

Eligible-date 21-session baseline: mean +1.33%, positive 68.9%, 5% drawdown 17.4% (1686 overlapping date outcomes; no confidence interval).

## gfc 2007 2009

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 9 | +2.03% | thin | 77.8% | -1.27% | 0.0% | +1.06% |
| high_vix_level / 10d | 9 | +0.08% | thin | 66.7% | -2.29% | 22.2% | +0.60% |
| high_vix_level / 21d | 9 | +0.88% | thin | 55.6% | -5.16% | 33.3% | -0.98% |
| vix_relief / 5d | 25 | -0.17% | [-1.27, +0.93]% | 48.0% | -1.83% | 12.0% | +0.11% |
| vix_relief / 10d | 25 | +0.36% | [-1.14, +1.70]% | 60.0% | -2.59% | 12.0% | +0.02% |
| vix_relief / 21d | 25 | +0.88% | [-1.40, +3.09]% | 68.0% | -4.22% | 32.0% | +0.71% |
| relief_broadening / 5d | 19 | -0.16% | [-1.27, +0.99]% | 47.4% | -1.62% | 10.5% | -0.58% |
| relief_broadening / 10d | 19 | -0.36% | [-3.41, +1.86]% | 68.4% | -2.93% | 21.1% | -0.54% |
| relief_broadening / 21d | 19 | -0.27% | [-4.03, +2.75]% | 63.2% | -4.49% | 26.3% | -0.79% |
| stress_broadening / 5d | 19 | +1.64% | [+0.46, +3.20]% | 63.2% | -1.24% | 5.3% | +0.78% |
| stress_broadening / 10d | 19 | +1.55% | [+0.25, +3.26]% | 57.9% | -1.87% | 10.5% | +0.72% |
| stress_broadening / 21d | 19 | +1.62% | [-1.64, +4.43]% | 73.7% | -4.30% | 26.3% | -0.34% |
| shock_watch / 5d | 15 | +0.83% | [-0.56, +2.29]% | 66.7% | -2.41% | 13.3% | +0.12% |
| shock_watch / 10d | 15 | -0.89% | [-4.28, +1.63]% | 60.0% | -3.70% | 20.0% | -0.67% |
| shock_watch / 21d | 15 | +0.21% | [-2.98, +2.79]% | 60.0% | -5.00% | 33.3% | -0.97% |

Eligible-date 21-session baseline: mean -0.25%, positive 56.4%, 5% drawdown 33.8% (713 overlapping date outcomes; no confidence interval).

## covid 2020

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 2 | +2.60% | thin | 100.0% | -1.52% | 0.0% | +3.95% |
| high_vix_level / 10d | 2 | +2.82% | thin | 100.0% | -1.52% | 0.0% | +4.35% |
| high_vix_level / 21d | 2 | -1.50% | thin | 50.0% | -5.48% | 50.0% | +2.64% |
| vix_relief / 5d | 10 | +2.27% | thin | 70.0% | -0.92% | 10.0% | +0.84% |
| vix_relief / 10d | 10 | +4.10% | thin | 90.0% | -1.05% | 10.0% | +2.82% |
| vix_relief / 21d | 10 | +5.87% | thin | 100.0% | -1.17% | 10.0% | +5.29% |
| relief_broadening / 5d | 8 | +0.68% | thin | 62.5% | -1.61% | 0.0% | +1.53% |
| relief_broadening / 10d | 8 | +2.05% | thin | 75.0% | -1.77% | 0.0% | +2.60% |
| relief_broadening / 21d | 8 | +6.56% | thin | 100.0% | -1.93% | 0.0% | +5.93% |
| stress_broadening / 5d | 6 | -0.11% | thin | 50.0% | -1.27% | 0.0% | -1.77% |
| stress_broadening / 10d | 6 | -1.20% | thin | 50.0% | -4.61% | 16.7% | -3.12% |
| stress_broadening / 21d | 6 | -0.11% | thin | 50.0% | -6.80% | 33.3% | -1.23% |
| shock_watch / 5d | 5 | -3.66% | thin | 40.0% | -5.27% | 20.0% | -1.72% |
| shock_watch / 10d | 5 | -2.20% | thin | 60.0% | -5.82% | 20.0% | -3.78% |
| shock_watch / 21d | 5 | -3.13% | thin | 40.0% | -8.96% | 60.0% | -1.08% |

Eligible-date 21-session baseline: mean +1.77%, positive 75.5%, 5% drawdown 24.5% (253 overlapping date outcomes; no confidence interval).

## inflation 2022

| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| high_vix_level / 5d | 5 | -1.22% | thin | 60.0% | -3.00% | 0.0% | -0.32% |
| high_vix_level / 10d | 5 | -0.51% | thin | 40.0% | -3.13% | 0.0% | -1.98% |
| high_vix_level / 21d | 5 | -0.25% | thin | 60.0% | -4.45% | 20.0% | +0.31% |
| vix_relief / 5d | 9 | -0.82% | thin | 44.4% | -2.40% | 22.2% | -1.04% |
| vix_relief / 10d | 9 | -1.07% | thin | 44.4% | -3.69% | 33.3% | -1.59% |
| vix_relief / 21d | 9 | -1.41% | thin | 44.4% | -5.66% | 44.4% | -2.06% |
| relief_broadening / 5d | 8 | -0.96% | thin | 50.0% | -2.47% | 25.0% | -1.46% |
| relief_broadening / 10d | 8 | -2.21% | thin | 37.5% | -3.99% | 37.5% | -2.93% |
| relief_broadening / 21d | 8 | -3.13% | thin | 25.0% | -6.21% | 50.0% | -3.51% |
| stress_broadening / 5d | 7 | -0.69% | thin | 28.6% | -2.51% | 14.3% | -0.85% |
| stress_broadening / 10d | 7 | +0.21% | thin | 42.9% | -3.36% | 42.9% | -0.46% |
| stress_broadening / 21d | 7 | -1.77% | thin | 28.6% | -4.64% | 57.1% | -1.96% |
| shock_watch / 5d | 3 | -0.50% | thin | 66.7% | -1.44% | 0.0% | -0.74% |
| shock_watch / 10d | 3 | -2.88% | thin | 33.3% | -4.54% | 33.3% | -4.52% |
| shock_watch / 21d | 3 | -8.30% | thin | 0.0% | -9.54% | 100.0% | -7.50% |

Eligible-date 21-session baseline: mean -0.86%, positive 43.0%, 5% drawdown 47.8% (251 overlapping date outcomes; no confidence interval).

## Interpretation boundary

A higher average following one rule does not establish an incremental edge: selection dates differ, returns have equity drift, early/late eras may disagree, and stored breadth/credit were not necessarily published by the indicated signal close. Next-close sensitivity is not a substitute for availability vintages. The production feature therefore remains an observable risk-direction and confirmation panel, with no pivot probability or trade authority.

Exact inputs, code hashes, episode dates, censored counts and intervals for all metrics are retained in `replay.json`. Future testing must use the existing keep-first observation ledger and retain this null/uncertainty boundary.
