# Risk Radar Episode Atlas

**Purpose:** Descriptive replay of the US risk radar's leg readings through five major historical risk episodes. This is display-tier context — base rates, coverage limitations stated explicitly, no promotion/kill language. Findings are descriptive, not authority.

Generated: 2026-09-22T01:11:09.951394+00:00
Signals date range: 1993-01-29 to 2026-09-18 (n_trading_days=8467)

## Headline Warning Persistence at Fixed Reference Dates

These are reconstructed historical states under the committed engine and historical inputs, not genuinely issued forecasts. The five dates were frozen before this warning-path calculation; no nearest-peak substitution is allowed.

| Episode | T-21 | T-5 | T-1 | T0 | T0 gate | caution+ T-21..T0 | elevated+ T-21..T0 | caution+ run into T0 | H21 max loss |
|---------|------|-----|-----|----|---------|--------------------|---------------------|----------------------|--------------|
| 2018Q4 selloff | caution | calm | calm | watch | closed | 8/22 | 0/22 | 0 | -6.9% |
| COVID-2020 | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -29.1% |
| 2022 bear market | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -9.7% |
| SVB March-2023 | risk-off | caution | watch | caution | closed | 14/22 | 1/22 | 1 | -5.3% |
| Aug-2024 yen-carry | caution | caution | caution | caution | closed | 22/22 | 0/22 | 22 | -8.4% |

## Coverage: First Non-NaN Date per Leg

Legs with no data at a historical episode are marked NO DATA — this is NOT the same as a leg being silent (data present but not elevated).

| Leg | Coverage Start | Gate-passed | Notes |
|-----|---------------|-------------|-------|

> **Gate-passed** reproduces the engine's internal `_is_validated` flag (leg lift >= 1.20 in the committed `risk_radar_backtest` evidence gate); it is the engine's own tier name, not a promotion claim by this study.

| credit_oas_roc | 1998-01-29 | Yes |  |
| credit_hyg_tlt | 2008-05-07 | No |  |
| rates_move | 2003-11-11 | Yes |  |
| rates_realrate | 2004-01-08 | No |  |
| bubble_ext | 1994-07-19 | Yes |  |
| bubble_leadership | 2001-08-31 | No |  |
| growth_defensives | 2000-01-20 | Yes |  |
| growth_cyc_def | 2000-01-20 | Yes |  |
| vol_term | 2011-12-30 | No |  |
| jpy_carry | 1994-01-26 | No |  |
| nh_contraction | 1994-02-09 | No |  |
| corr_floor_break | 2006-01-03 | No |  |
| ai_breadth_divergence | 2025-05-28 | No | No data for any named episode |

## All detect_events Onsets (depth >= 8%, fwd=63d, min_gap=40)

n=48 onsets on SPY (1993-2026). Named episodes are flagged.

| Date | In Named Episode |
|------|-----------------|
| 1994-02-02 |  |
| 1997-02-18 |  |
| 1997-08-06 |  |
| 1997-10-07 |  |
| 1998-07-17 |  |
| 1998-09-23 |  |
| 1999-07-16 |  |
| 2000-01-19 |  |
| 2000-03-24 |  |
| 2000-09-01 |  |
| 2000-11-06 |  |
| 2001-02-01 |  |
| 2001-05-21 |  |
| 2001-08-02 |  |
| 2002-01-04 |  |
| 2002-03-19 |  |
| 2002-05-17 |  |
| 2002-08-22 |  |
| 2002-11-27 |  |
| 2007-07-19 |  |
| 2007-10-09 |  |
| 2007-12-10 |  |
| 2008-05-19 |  |
| 2008-08-11 |  |
| 2008-10-13 |  |
| 2009-01-06 |  |
| 2010-04-23 |  |
| 2010-06-21 |  |
| 2011-05-10 |  |
| 2011-07-07 |  |
| 2011-10-27 |  |
| 2012-04-02 |  |
| 2015-07-20 |  |
| 2015-11-03 |  |
| 2015-12-31 |  |
| 2018-01-26 |  |
| 2018-09-20 | YES (named) |
| 2018-12-03 |  |
| 2020-02-19 | YES (named) |
| 2020-09-02 |  |
| 2022-01-03 | YES (named) |
| 2022-03-29 |  |
| 2022-06-02 |  |
| 2022-08-16 |  |
| 2023-07-31 |  |
| 2024-07-16 | YES (named) |
| 2025-02-19 |  |
| 2026-01-27 |  |

## Per-Episode Analysis

**Key:** EARLY = first elevated >=5 trading days before T0; JIT = T-5..T0; LATE = T0..T+5 (first elevated AFTER onset); SILENT = data present in T-63..T+5, never elevated; NO DATA = no non-NaN data in window.

### 2018Q4 selloff

- **Fixed reference date:** 2018-09-20 (source: fixed_named_anchor)
- **Frozen hint date:** 2018-09-20
- **SPY close at T0:** 259.29
- **Max drawdown over next 63 trading days:** -15.4%
- **Context gate at T-5:** False  /  **T0:** False

**Actual gated headline path:**

| Offset | Date | Headline state | Context gate | Signal coverage | Tier-A subscore coverage |
|--------|------|----------------|--------------|-----------------|--------------------------|
| T-21 | 2018-08-21 | caution | closed | 12/13 | 4/4 |
| T-5 | 2018-09-13 | calm | closed | 12/13 | 4/4 |
| T-1 | 2018-09-19 | calm | closed | 12/13 | 4/4 |
| T0 | 2018-09-20 | watch | closed | 12/13 | 4/4 |
| T+5 | 2018-09-27 | calm | closed | 12/13 | 4/4 |

- **T-21..T0:** caution+ 8/22 (36.4%); elevated+ 0/22 (0.0%); consecutive caution+ sessions ending at T0 = 0.
- **T-5..T0:** caution+ 0/6 (0.0%); elevated+ 0/6 (0.0%); consecutive caution+ sessions ending at T0 = 0.
- **Canonical grader forward max loss:** h5=-0.8%, h10=-1.0%, h21=-6.9%.

| Leg | Gate-passed | Coverage Start | T-21 pctile | T-5 pctile | T-1 pctile | T0 pctile | T+5 pctile | First Elevated | Classification |
|-----|-------------|----------------|-------------|------------|------------|-----------|------------|----------------|----------------|
| credit_oas_roc | Y | 1998-01-29 | 0.607 | 0.292 | 0.242 | 0.253 | 0.404 | 2018-07-02 | EARLY |
| credit_hyg_tlt | N | 2008-05-07 | 0.698 | 0.304 | 0.087 | 0.083 | 0.175 | 2018-07-05 | EARLY |
| rates_move | Y | 2003-11-11 | 0.242 | 0.030 | 0.173 | 0.216 | 0.022 | — | SILENT |
| rates_realrate | N | 2004-01-08 | 0.289 | 0.822 | 0.870 | 0.758 | 0.394 | 2018-07-23 | EARLY |
| bubble_ext | Y | 1994-07-19 | 0.417 | 0.522 | 0.506 | 0.736 | 0.486 | — | SILENT |
| bubble_leadership | N | 2001-08-31 | 0.010 | 0.004 | 0.026 | 0.056 | 0.125 | — | SILENT |
| growth_defensives | Y | 2000-01-20 | 0.736 | 0.359 | 0.256 | 0.266 | 0.294 | 2018-06-27 | EARLY |
| growth_cyc_def | Y | 2000-01-20 | 0.827 | 0.268 | 0.337 | 0.532 | 0.659 | 2018-07-03 | EARLY |
| vol_term | N | 2011-12-30 | 0.522 | 0.196 | 0.611 | 0.526 | 0.681 | 2018-06-25 | EARLY |
| jpy_carry | N | 1994-01-26 | 0.720 | 0.371 | 0.375 | 0.376 | 0.381 | — | SILENT |
| nh_contraction | N | 1994-02-09 | 0.550 | 0.282 | 0.318 | 0.316 | 0.381 | — | SILENT |
| corr_floor_break | N | 2006-01-03 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | — | SILENT |
| ai_breadth_divergence | N | 2025-05-28 | — | — | — | — | — | — | NO DATA |

*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated (at or above leg threshold). T0 = onset date.*

**Max Tier-A subscore trajectory (0-100) at selected offsets:**

| Offset | Date | Max Tier-A Subscore | Context Gate |
|--------|------|---------------------|-------------|
| T-21 | 2018-08-21 | 78.2 | False |
| T-10 | 2018-09-06 | 78.5 | False |
| T-5 | 2018-09-13 | 44.4 | False |
| T-1 | 2018-09-19 | 43.4 | False |
| T+0 | 2018-09-20 | 63.4 | False |
| T+5 | 2018-09-27 | 47.6 | False |
| T+10 | 2018-10-04 | 63.2 | False |
| T+21 | 2018-10-19 | 99.7 | False |

_The trajectory above is the raw un-gated max Tier-A subscore; the engine's headline STATE applies the context-gate cap (`engine/risk_radar_backtest.py` `state_series` caps loud states at 'caution' when the gate is False) — and the gate was False at onset for the episodes where the table shows it — so a high subscore here did NOT correspond to a loud banner at the time._

### COVID-2020

- **Fixed reference date:** 2020-02-19 (source: fixed_named_anchor)
- **Frozen hint date:** 2020-02-19
- **SPY close at T0:** 307.64
- **Max drawdown over next 63 trading days:** -33.7%
- **Context gate at T-5:** False  /  **T0:** False

**Actual gated headline path:**

| Offset | Date | Headline state | Context gate | Signal coverage | Tier-A subscore coverage |
|--------|------|----------------|--------------|-----------------|--------------------------|
| T-21 | 2020-01-17 | caution | closed | 12/13 | 4/4 |
| T-5 | 2020-02-11 | caution | closed | 12/13 | 4/4 |
| T-1 | 2020-02-18 | caution | closed | 12/13 | 4/4 |
| T0 | 2020-02-19 | caution | closed | 12/13 | 4/4 |
| T+5 | 2020-02-26 | caution | closed | 11/13 | 4/4 |

- **T-21..T0:** caution+ 22/22 (100.0%); elevated+ 0/22 (0.0%); consecutive caution+ sessions ending at T0 = 22.
- **T-5..T0:** caution+ 6/6 (100.0%); elevated+ 0/6 (0.0%); consecutive caution+ sessions ending at T0 = 6.
- **Canonical grader forward max loss:** h5=-7.9%, h10=-12.4%, h21=-29.1%.

| Leg | Gate-passed | Coverage Start | T-21 pctile | T-5 pctile | T-1 pctile | T0 pctile | T+5 pctile | First Elevated | Classification |
|-----|-------------|----------------|-------------|------------|------------|-----------|------------|----------------|----------------|
| credit_oas_roc | Y | 1998-01-29 | 0.321 | 0.684 | 0.758 | 0.616 | 0.881 | 2020-01-27 | EARLY |
| credit_hyg_tlt | N | 2008-05-07 | 0.625 | 0.883 | 0.903* | 0.851 | 0.913* | 2020-01-27 | EARLY |
| rates_move | Y | 2003-11-11 | 0.222 | 0.772 | 0.829 | 0.829 | 0.980* | 2020-02-24 | LATE |
| rates_realrate | N | 2004-01-08 | 0.619 | 0.375 | 0.553 | 0.380 | 0.053 | — | SILENT |
| bubble_ext | Y | 1994-07-19 | 0.978* | 0.998* | 0.992* | 0.998* | 0.314 | 2019-12-16 | EARLY |
| bubble_leadership | N | 2001-08-31 | 0.724 | 0.577 | 0.568 | 0.629 | 0.583 | 2019-11-25 | EARLY |
| growth_defensives | Y | 2000-01-20 | 0.450 | 0.802 | 0.827 | 0.655 | 0.728 | 2020-01-31 | EARLY |
| growth_cyc_def | Y | 2000-01-20 | 0.470 | 0.377 | 0.333 | 0.224 | 0.561 | — | SILENT |
| vol_term | N | 2011-12-30 | 0.016 | 0.363 | 0.371 | 0.220 | 0.996* | 2020-01-27 | EARLY |
| jpy_carry | N | 1994-01-26 | 0.413 | 0.421 | 0.423 | 0.424 | 0.429 | 2020-01-03 | EARLY |
| nh_contraction | N | 1994-02-09 | 0.040 | 0.004 | 0.009 | 0.014 | — | — | SILENT |
| corr_floor_break | N | 2006-01-03 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | — | SILENT |
| ai_breadth_divergence | N | 2025-05-28 | — | — | — | — | — | — | NO DATA |

*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated (at or above leg threshold). T0 = onset date.*

**Max Tier-A subscore trajectory (0-100) at selected offsets:**

| Offset | Date | Max Tier-A Subscore | Context Gate |
|--------|------|---------------------|-------------|
| T-21 | 2020-01-17 | 94.0 | False |
| T-10 | 2020-02-04 | 91.3 | False |
| T-5 | 2020-02-11 | 93.5 | False |
| T-1 | 2020-02-18 | 92.8 | False |
| T+0 | 2020-02-19 | 94.3 | False |
| T+5 | 2020-02-26 | 88.6 | False |
| T+10 | 2020-03-04 | 97.9 | False |
| T+21 | 2020-03-19 | 99.9 | True |

_The trajectory above is the raw un-gated max Tier-A subscore; the engine's headline STATE applies the context-gate cap (`engine/risk_radar_backtest.py` `state_series` caps loud states at 'caution' when the gate is False) — and the gate was False at onset for the episodes where the table shows it — so a high subscore here did NOT correspond to a loud banner at the time._

### 2022 bear market

- **Fixed reference date:** 2022-01-03 (source: fixed_named_anchor)
- **Frozen hint date:** 2022-01-03
- **SPY close at T0:** 448.37
- **Max drawdown over next 63 trading days:** -12.9%
- **Context gate at T-5:** False  /  **T0:** False

**Actual gated headline path:**

| Offset | Date | Headline state | Context gate | Signal coverage | Tier-A subscore coverage |
|--------|------|----------------|--------------|-----------------|--------------------------|
| T-21 | 2021-12-02 | caution | closed | 11/13 | 4/4 |
| T-5 | 2021-12-27 | caution | closed | 12/13 | 4/4 |
| T-1 | 2021-12-31 | caution | closed | 12/13 | 4/4 |
| T0 | 2022-01-03 | caution | closed | 12/13 | 4/4 |
| T+5 | 2022-01-10 | caution | closed | 11/13 | 4/4 |

- **T-21..T0:** caution+ 22/22 (100.0%); elevated+ 0/22 (0.0%); consecutive caution+ sessions ending at T0 = 22.
- **T-5..T0:** caution+ 6/6 (100.0%); elevated+ 0/6 (0.0%); consecutive caution+ sessions ending at T0 = 6.
- **Canonical grader forward max loss:** h5=-2.5%, h10=-4.4%, h21=-9.7%.

| Leg | Gate-passed | Coverage Start | T-21 pctile | T-5 pctile | T-1 pctile | T0 pctile | T+5 pctile | First Elevated | Classification |
|-----|-------------|----------------|-------------|------------|------------|-----------|------------|----------------|----------------|
| credit_oas_roc | Y | 1998-01-29 | 0.899 | 0.286 | 0.177 | 0.173 | 0.609 | 2021-11-26 | EARLY |
| credit_hyg_tlt | N | 2008-05-07 | 0.925* | 0.216 | 0.167 | 0.030 | 0.212 | 2021-12-01 | EARLY |
| rates_move | Y | 2003-11-11 | 0.934* | 0.919* | 0.891 | 0.941* | 0.893 | 2021-10-18 | EARLY |
| rates_realrate | N | 2004-01-08 | 0.245 | 0.299 | 0.212 | 0.799 | 0.981* | 2021-11-01 | EARLY |
| bubble_ext | Y | 1994-07-19 | 0.248 | 0.443 | 0.367 | 0.403 | 0.232 | — | SILENT |
| bubble_leadership | N | 2001-08-31 | 0.833 | 0.734 | 0.818 | 0.903* | 0.788 | 2021-11-18 | EARLY |
| growth_defensives | Y | 2000-01-20 | 0.760 | 0.742 | 0.857 | 0.635 | 0.790 | 2021-12-13 | EARLY |
| growth_cyc_def | Y | 2000-01-20 | 0.579 | 0.913* | 0.964* | 0.831 | 0.931* | 2021-12-13 | EARLY |
| vol_term | N | 2011-12-30 | 0.841 | 0.101 | 0.052 | 0.091 | 0.554 | 2021-12-01 | EARLY |
| jpy_carry | N | 1994-01-26 | 0.905* | 0.401 | 0.404 | 0.405 | 0.407 | 2021-12-01 | EARLY |
| nh_contraction | N | 1994-02-09 | — | 0.714 | 0.476 | 0.452 | — | — | SILENT |
| corr_floor_break | N | 2006-01-03 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | — | SILENT |
| ai_breadth_divergence | N | 2025-05-28 | — | — | — | — | — | — | NO DATA |

*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated (at or above leg threshold). T0 = onset date.*

**Max Tier-A subscore trajectory (0-100) at selected offsets:**

| Offset | Date | Max Tier-A Subscore | Context Gate |
|--------|------|---------------------|-------------|
| T-21 | 2021-12-02 | 90.3 | False |
| T-10 | 2021-12-17 | 97.8 | False |
| T-5 | 2021-12-27 | 82.7 | False |
| T-1 | 2021-12-31 | 91.1 | False |
| T+0 | 2022-01-03 | 91.2 | False |
| T+5 | 2022-01-10 | 91.0 | False |
| T+10 | 2022-01-18 | 93.4 | False |
| T+21 | 2022-02-02 | 88.0 | False |

_The trajectory above is the raw un-gated max Tier-A subscore; the engine's headline STATE applies the context-gate cap (`engine/risk_radar_backtest.py` `state_series` caps loud states at 'caution' when the gate is False) — and the gate was False at onset for the episodes where the table shows it — so a high subscore here did NOT correspond to a loud banner at the time._

### SVB March-2023

- **Fixed reference date:** 2023-02-02 (source: fixed_named_anchor)
- **Frozen hint date:** 2023-02-02
- **SPY close at T0:** 397.53
- **Max drawdown over next 63 trading days:** -7.5%
- **Context gate at T-5:** False  /  **T0:** False

**Actual gated headline path:**

| Offset | Date | Headline state | Context gate | Signal coverage | Tier-A subscore coverage |
|--------|------|----------------|--------------|-----------------|--------------------------|
| T-21 | 2023-01-03 | risk-off | open | 11/13 | 4/4 |
| T-5 | 2023-01-26 | caution | closed | 11/13 | 4/4 |
| T-1 | 2023-02-01 | watch | closed | 11/13 | 4/4 |
| T0 | 2023-02-02 | caution | closed | 11/13 | 4/4 |
| T+5 | 2023-02-09 | watch | closed | 11/13 | 4/4 |

- **T-21..T0:** caution+ 14/22 (63.6%); elevated+ 1/22 (4.5%); consecutive caution+ sessions ending at T0 = 1.
- **T-5..T0:** caution+ 2/6 (33.3%); elevated+ 0/6 (0.0%); consecutive caution+ sessions ending at T0 = 1.
- **Canonical grader forward max loss:** h5=-2.3%, h10=-2.3%, h21=-5.3%.

| Leg | Gate-passed | Coverage Start | T-21 pctile | T-5 pctile | T-1 pctile | T0 pctile | T+5 pctile | First Elevated | Classification |
|-----|-------------|----------------|-------------|------------|------------|-----------|------------|----------------|----------------|
| credit_oas_roc | Y | 1998-01-29 | 0.726 | 0.054 | 0.113 | 0.038 | 0.242 | — | SILENT |
| credit_hyg_tlt | N | 2008-05-07 | 0.292 | 0.863 | 0.809 | 0.756 | 0.589 | 2022-11-18 | EARLY |
| rates_move | Y | 2003-11-11 | 0.847 | 0.571 | 0.538 | 0.540 | 0.559 | 2022-11-01 ⟵ left-censored: already elevated at window open | EARLY |
| rates_realrate | N | 2004-01-08 | 0.367 | 0.325 | 0.325 | 0.542 | 0.872 | 2022-11-03 | EARLY |
| bubble_ext | Y | 1994-07-19 | 0.270 | 0.502 | 0.524 | 0.554 | 0.520 | — | SILENT |
| bubble_leadership | N | 2001-08-31 | 0.641 | 1.000* | 1.000* | 0.998* | 0.958* | 2023-01-10 | EARLY |
| growth_defensives | Y | 2000-01-20 | 0.936* | 0.026 | 0.030 | 0.016 | 0.014 | 2022-12-12 | EARLY |
| growth_cyc_def | Y | 2000-01-20 | 0.895 | 0.002 | 0.004 | 0.002 | 0.038 | 2022-11-01 ⟵ left-censored: already elevated at window open | EARLY |
| vol_term | N | 2011-12-30 | 0.889 | 0.877 | 0.706 | 0.686 | 0.869 | 2022-11-01 ⟵ left-censored: already elevated at window open | EARLY |
| jpy_carry | N | 1994-01-26 | 0.984* | 0.913* | 0.018 | 0.807 | 0.040 | 2022-11-10 | EARLY |
| nh_contraction | N | 1994-02-09 | — | — | — | — | — | — | NO DATA |
| corr_floor_break | N | 2006-01-03 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | — | SILENT |
| ai_breadth_divergence | N | 2025-05-28 | — | — | — | — | — | — | NO DATA |

*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated (at or above leg threshold). T0 = onset date.*

**Left-censored note (rates_move, growth_cyc_def, vol_term):** A T-63 first_elevated date is a lower bound on lead, not a measured onset-anticipation — the leg was already elevated when the lookback window opened. EARLY counts including these rows are marked with ⟵.

**Max Tier-A subscore trajectory (0-100) at selected offsets:**

| Offset | Date | Max Tier-A Subscore | Context Gate |
|--------|------|---------------------|-------------|
| T-21 | 2023-01-03 | 91.6 | True |
| T-10 | 2023-01-19 | 54.0 | False |
| T-5 | 2023-01-26 | 57.7 | False |
| T-1 | 2023-02-01 | 59.5 | False |
| T+0 | 2023-02-02 | 62.0 | False |
| T+5 | 2023-02-09 | 62.2 | False |
| T+10 | 2023-02-16 | 65.2 | False |
| T+21 | 2023-03-06 | 69.0 | False |

_The trajectory above is the raw un-gated max Tier-A subscore; the engine's headline STATE applies the context-gate cap (`engine/risk_radar_backtest.py` `state_series` caps loud states at 'caution' when the gate is False) — and the gate was False at onset for the episodes where the table shows it — so a high subscore here did NOT correspond to a loud banner at the time._

### Aug-2024 yen-carry

- **Fixed reference date:** 2024-07-16 (source: fixed_named_anchor)
- **Frozen hint date:** 2024-07-16
- **SPY close at T0:** 550.43
- **Max drawdown over next 63 trading days:** -8.4%
- **Context gate at T-5:** False  /  **T0:** False

**Actual gated headline path:**

| Offset | Date | Headline state | Context gate | Signal coverage | Tier-A subscore coverage |
|--------|------|----------------|--------------|-----------------|--------------------------|
| T-21 | 2024-06-13 | caution | closed | 12/13 | 4/4 |
| T-5 | 2024-07-09 | caution | closed | 12/13 | 4/4 |
| T-1 | 2024-07-15 | caution | closed | 12/13 | 4/4 |
| T0 | 2024-07-16 | caution | closed | 12/13 | 4/4 |
| T+5 | 2024-07-23 | caution | closed | 12/13 | 4/4 |

- **T-21..T0:** caution+ 22/22 (100.0%); elevated+ 0/22 (0.0%); consecutive caution+ sessions ending at T0 = 22.
- **T-5..T0:** caution+ 6/6 (100.0%); elevated+ 0/6 (0.0%); consecutive caution+ sessions ending at T0 = 6.
- **Canonical grader forward max loss:** h5=-2.8%, h10=-4.7%, h21=-8.4%.

| Leg | Gate-passed | Coverage Start | T-21 pctile | T-5 pctile | T-1 pctile | T0 pctile | T+5 pctile | First Elevated | Classification |
|-----|-------------|----------------|-------------|------------|------------|-----------|------------|----------------|----------------|
| credit_oas_roc | Y | 1998-01-29 | 0.685 | 0.636 | 0.462 | 0.415 | 0.404 | — | SILENT |
| credit_hyg_tlt | N | 2008-05-07 | 0.796 | 0.675 | 0.439 | 0.401 | 0.274 | — | SILENT |
| rates_move | Y | 2003-11-11 | 0.036 | 0.068 | 0.069 | 0.054 | 0.081 | — | SILENT |
| rates_realrate | N | 2004-01-08 | 0.503 | 0.163 | 0.310 | 0.145 | 0.583 | 2024-04-16 | EARLY |
| bubble_ext | Y | 1994-07-19 | 0.962* | 0.990* | 0.998* | 1.000* | 0.839 | 2024-05-15 | EARLY |
| bubble_leadership | N | 2001-08-31 | 0.829 | 0.796 | 0.736 | 0.712 | 0.744 | 2024-04-15 ⟵ left-censored: already elevated at window open | EARLY |
| growth_defensives | Y | 2000-01-20 | 0.155 | 0.212 | 0.288 | 0.327 | 0.518 | 2024-04-19 | EARLY |
| growth_cyc_def | Y | 2000-01-20 | 0.351 | 0.135 | 0.191 | 0.127 | 0.240 | — | SILENT |
| vol_term | N | 2011-12-30 | 0.077 | 0.218 | 0.421 | 0.304 | 0.712 | 2024-04-15 ⟵ left-censored: already elevated at window open | EARLY |
| jpy_carry | N | 1994-01-26 | 0.429 | 0.429 | 0.429 | 0.429 | 0.939* | 2024-07-17 | LATE |
| nh_contraction | N | 1994-02-09 | 0.059 | 0.121 | 0.076 | 0.056 | 0.046 | — | SILENT |
| corr_floor_break | N | 2006-01-03 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2024-04-15 ⟵ left-censored: already elevated at window open | EARLY |
| ai_breadth_divergence | N | 2025-05-28 | — | — | — | — | — | — | NO DATA |

*Pctile values are 0-1 causal trailing-504d percentiles. Asterisk (*) = elevated (at or above leg threshold). T0 = onset date.*

**Left-censored note (bubble_leadership, vol_term, corr_floor_break):** A T-63 first_elevated date is a lower bound on lead, not a measured onset-anticipation — the leg was already elevated when the lookback window opened. EARLY counts including these rows are marked with ⟵.

**Max Tier-A subscore trajectory (0-100) at selected offsets:**

| Offset | Date | Max Tier-A Subscore | Context Gate |
|--------|------|---------------------|-------------|
| T-21 | 2024-06-13 | 94.2 | False |
| T-10 | 2024-07-01 | 86.5 | False |
| T-5 | 2024-07-09 | 96.1 | False |
| T-1 | 2024-07-15 | 95.9 | False |
| T+0 | 2024-07-16 | 95.7 | False |
| T+5 | 2024-07-23 | 82.5 | False |
| T+10 | 2024-07-30 | 79.8 | False |
| T+21 | 2024-08-14 | 96.1 | False |

_The trajectory above is the raw un-gated max Tier-A subscore; the engine's headline STATE applies the context-gate cap (`engine/risk_radar_backtest.py` `state_series` caps loud states at 'caution' when the gate is False) — and the gate was False at onset for the episodes where the table shows it — so a high subscore here did NOT correspond to a loud banner at the time._

## Lead/Lag Summary: Per Leg Across All 5 Episodes

n = 5 named episodes. Counts reflect how many times each leg fell in each classification across episodes. A NO DATA entry means the leg had no data at that episode (not the same as silent).

| Leg | Gate-passed | Cov Start | EARLY | JIT | LATE | SILENT | NO DATA | All-Late-or-Silent? |
|-----|-------------|-----------|-------|-----|------|--------|---------|---------------------|
| credit_oas_roc | Y | 1998-01-29 | 3 | 0 | 0 | 2 | 0 |  |
| credit_hyg_tlt | N | 2008-05-07 | 4 | 0 | 0 | 1 | 0 |  |
| rates_move | Y | 2003-11-11 | 2 (1 left-censored⟵) | 0 | 1 | 2 | 0 |  |
| rates_realrate | N | 2004-01-08 | 4 | 0 | 0 | 1 | 0 |  |
| bubble_ext | Y | 1994-07-19 | 2 | 0 | 0 | 3 | 0 |  |
| bubble_leadership | N | 2001-08-31 | 4 (1 left-censored⟵) | 0 | 0 | 1 | 0 |  |
| growth_defensives | Y | 2000-01-20 | 5 | 0 | 0 | 0 | 0 |  |
| growth_cyc_def | Y | 2000-01-20 | 3 (1 left-censored⟵) | 0 | 0 | 2 | 0 |  |
| vol_term | N | 2011-12-30 | 5 (2 left-censored⟵) | 0 | 0 | 0 | 0 |  |
| jpy_carry | N | 1994-01-26 | 3 | 0 | 1 | 1 | 0 |  |
| nh_contraction | N | 1994-02-09 | 0 | 0 | 0 | 4 | 1 | YES — worth a second look |
| corr_floor_break | N | 2006-01-03 | 1 (1 left-censored⟵) | 0 | 0 | 4 | 0 |  |
| ai_breadth_divergence | N | 2025-05-28 | 0 | 0 | 0 | 0 | 5 |  |

*Legs flagged 'All-Late-or-Silent' had no EARLY or JIT readings in any episode for which data existed. This is descriptive context, not a kill — other factors may limit historical data coverage (e.g., leg born post-2020), or the mechanism may be genuinely reactive rather than leading.*

**Lead/lag note on left-censored rows (⟵):** EARLY counts marked with ⟵ include rows where `first_elevated` equals the T-63 left-boundary of the lookback window — i.e., the leg was already elevated when the window opened. The T-63 date is a lower bound on lead time, not a measured onset-anticipation. True lead could be months earlier or could reflect a persistent-regime artifact.

## Forward-Evidence Boundary

This atlas is reconstructed historical episode research. The issued Risk Radar forward ledger and its scorecard are a separate evidence class and must not be spliced into these selected episodes as if they were historical issued forecasts. Current probability diagnostics remain descriptive-only and do not validate the reconstructed warning path.

## Causal Spot-Check (Self-Check 3)

**Status:** pass
- Episode: COVID-2020, Leg: bubble_ext, Date: 2020-02-11
- Recomputed (truncated frame): 0.998016
- Precomputed (full frame): 0.998016
- Diff: 0.0
- Causal percentile is identical when derived from truncated vs full frame — confirms leak-free.

## Coverage Limitations

- The coverage table is generated from the current committed signal frame; absent accruing/display-only legs are not synthesized into historical coverage.
- A leg with no value in an episode window remains NO DATA; it is never converted into a silent/quiet reading.
- 2023-02-02 is a preregistered SVB-era reference anchor, not an optimized detect_events onset. The forward-loss columns disclose the realized path from that exact date.
- Selected historical reconstruction, overlapping daily replay windows, and genuinely issued forward forecasts remain separate evidence classes.

## Self-Checks

1. **COVID-2020 check:** See the per-episode table above. Multiple legs should show EARLY or JIT for the Feb-2020 episode; if literally everything is LATE/NO DATA, a join/date bug is likely.
2. **Fixed-anchor outcome disclosure:** SPY close at T0 and forward drawdowns are printed from the preregistered date. The anchor is not optimized to a detected local peak.
3. **Causal percentile check:** Causal percentile is identical when derived from truncated vs full frame — confirms leak-free.
