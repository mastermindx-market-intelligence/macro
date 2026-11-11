# Rotation Core v2 — SELECTION WINDOW results (1998-01-02 → 2019-12-31)

**Label: selection-window, not evidence.** This window was previously examined (v1, Pro run B; disclosed in the frozen header `ca5af27429b5…`). These numbers choose the grid point and nothing else. closes from 1996-01-02 used only as signal warm-up (252-session beta, 126-session look-backs); no statistic computed on dates before 1998-01-02. Annualised differences; 95% stationary-bootstrap intervals (block 21, B = 10,000) on the matched-mix contrast, whose mix is rebuilt inside every resample. Industry portfolios are not tradable.

| Book | vs exposure-matched mix (after-the-fact attribution yardstick, not holdable; binding contrast) | vs SPY | vs RSP (EW proxy before 2003-05) | vs BASE (EW industries) | MaxDD vs mix | One-way turnover/yr | Costs/yr (10 bp) | False DEFEND calls / calm yr |
|---|---|---|---|---|---|---|---|---|
| H1 h3_b25.0 | -2.29% [-4.95, +0.39] p=0.953 | -0.48% | -5.53% | -1.97% | -66.1% vs -57.7% | 6.12 | +1.22% | 2.08 |
| price-only h3_b25.0 | -2.24% [-5.18, +0.69] p=0.932 | -0.51% | -5.56% | -2.00% | -66.1% vs -56.7% | 6.85 | +1.37% | 2.84 |
| cash ablation h3_b25.0 | -4.55% [-8.08, -1.11] p=0.992 | -4.27% | -9.32% | -5.76% | -65.7% vs -51.2% | 4.12 | +0.82% | 2.08 |
| H1 h3_b37.5 | -2.62% [-5.22, -0.00] p=0.976 | -0.81% | -5.85% | -2.29% | -67.4% vs -57.8% | 5.66 | +1.13% | 1.73 |
| price-only h3_b37.5 | -2.24% [-5.10, +0.57] p=0.936 | -0.51% | -5.56% | -2.00% | -66.1% vs -56.7% | 6.85 | +1.37% | 2.84 |
| cash ablation h3_b37.5 | -4.81% [-8.27, -1.50] p=0.997 | -4.40% | -9.45% | -5.89% | -68.1% vs -51.9% | 3.94 | +0.79% | 1.73 |
| H1 h5_b25.0 | -2.87% [-5.67, +0.01] p=0.978 | -1.13% | -6.18% | -2.62% | -66.6% vs -57.0% | 7.07 | +1.41% | 3.05 |
| price-only h5_b25.0 | -3.15% [-6.10, -0.15] p=0.982 | -1.49% | -6.53% | -2.97% | -66.6% vs -56.2% | 7.98 | +1.60% | 3.81 |
| cash ablation h5_b25.0 | -5.22% [-9.12, -1.26] p=0.994 | -5.45% | -10.50% | -6.94% | -66.9% vs -48.5% | 4.39 | +0.88% | 3.05 |
| H1 h5_b37.5 | -2.69% [-5.41, +0.13] p=0.974 | -0.92% | -5.97% | -2.41% | -66.6% vs -57.3% | 6.66 | +1.33% | 2.77 |
| price-only h5_b37.5 | -3.15% [-6.11, -0.18] p=0.981 | -1.49% | -6.53% | -2.97% | -66.6% vs -56.2% | 7.98 | +1.60% | 3.81 |
| cash ablation h5_b37.5 | -4.28% [-8.07, -0.54] p=0.987 | -4.27% | -9.32% | -5.76% | -66.9% vs -49.7% | 4.21 | +0.84% | 2.77 |
| H3 (R5 on beta legs) | +1.33% [-2.16, +4.67] p=0.217 | +3.13% | -1.92% | +1.64% | -52.6% vs -56.4% | 1.75 | +0.35% | 0.90 |

| Setting | H1 vs matched mix at 2× costs | Costs/yr at 2× | H2: H1 − price-only (paired) | H1 state share N / D / A |
|---|---|---|---|---|
| h3_b25.0 | -3.65% [-6.45, -0.92] | +2.44% | +0.03% [-0.85, +0.94] p=0.473 | 42% / 19% / 39% |
| h3_b37.5 | -3.89% [-6.56, -1.17] | +2.26% | -0.29% [-1.32, +0.75] p=0.709 | 43% / 18% / 39% |
| h5_b25.0 | -4.43% [-7.30, -1.55] | +2.83% | +0.36% [-0.42, +1.11] p=0.171 | 38% / 25% / 37% |
| h5_b37.5 | -4.16% [-6.95, -1.32] | +2.66% | +0.56% [-0.33, +1.51] p=0.116 | 40% / 22% / 37% |

**Selected setting: `h3_b25.0`** (highest H1 excess over its matched mix; exact tie -> smaller h, then larger b). H2's price-only control and the cash ablation use the selected setting.
Observed H1 excess over matched mix by setting (selection-window): h3_b25.0 -2.29%, h3_b37.5 -2.62%, h5_b25.0 -2.87%, h5_b37.5 -2.69%

Named episodes used for false-call counts: E1998, E2000_02, E2008_09, E2011, E2015_16, E2018Q4. Dropped industry-days (no imputation; eligible industries only, not the header's 366 scope): 0.

