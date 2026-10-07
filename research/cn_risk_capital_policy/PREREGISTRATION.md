# Preregistration — China Risk Radar gross-exposure policy

Operation: `cn-risk-p4-capital-policy-20260923-solpro-001`. Source base: `49ceebf8d1a14c044684abdbeeb5779875cf20fc`. Skillpack: `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`. This protocol is frozen before any policy return is calculated. Historical results are reconstructed, not issued-forward policy performance.

## Fixed state and policy definitions

The exact state order is `calm, watch, caution, elevated, risk-off`. The exact current mapping is `1.00, 0.97, 0.90, 0.78, 0.62`; the harness must read the source constant and abort if it differs.

Policies are evaluated in this fixed order: (1) `current_ladder` exact mapping; (2) `constant_100` all states 1.00; (3) `constant_075` all states 0.75; (4) `matched_constant`, constant gross equal to the current ladder's mean executed gross in that sample/scenario and derived without returns; (5) `binary_loud_075`, 1.00 in calm/watch/caution and 0.75 in elevated/risk-off; (6) `current_riskoff_075`, current mapping with only risk-off changed to 0.75; (7) `vol_target_15`, trailing 20-session annualized realized volatility, target 15%, clipped to 0.50–1.00, initialized at 1.00 until 20 returns exist. No other policy or coefficient may be tested.

## Benchmark, timing, cost, and samples

Primary benchmark/exposure proxy: `china/000001.SS` stored Shanghai Composite close returns, aligned to exact reconstructed Radar states from 2003-03-03. Investable-proxy robustness: `china/510300.SS` stored close returns from 2012-05-04 with the same Radar states. Cash earns zero; no leverage or shorting.

Primary scenario: state/target observed at close `t`, executed for the next close-to-close return (`lag=1`), 10 bps cost per unit of absolute gross change after sample entry. Sensitivities: `lag=2/cost=10`, `lag=1/cost=25`, and `lag=2/cost=25`. State policies rebalance only when their mapped gross changes; vol target may change daily. The first sample allocation is not charged as turnover.

Era windows are `pre_2016` through 2015-12-31 and `post_2016` from 2016-01-01. Fixed crisis peak→trough windows are: `bear_2004_05` 2004-04-06→2005-07-11; `gfc_2007_08` 2007-10-16→2008-11-04; `tightening_2009_10` 2009-08-04→2010-07-05; `slowdown_2011_12` 2011-04-18→2012-12-03; `bubble_2015_16` 2015-06-12→2016-01-28; `trade_deleveraging_2018` 2018-01-24→2019-01-03; `covid_2020` 2020-01-13→2020-03-23; `property_2021_22` 2021-09-13→2022-04-26; `confidence_2023_24` 2023-05-08→2024-02-05. Recovery is the next 63 available sessions after each trough.

## Fixed metrics

Return metrics: total return, CAGR, annualized volatility, zero-cash Sharpe, zero-threshold Sortino, Calmar, maximum drawdown, and 95% historical expected shortfall/CVaR. Policy-cost metrics: average gross, fraction below 1.00, total and annualized turnover, exposure-change count, gross transaction cost, missed positive-return contribution, avoided negative-return contribution, exact excess return versus full gross, and annualized certainty equivalent `mean*252 - 0.5*3*variance*252`.

Crisis metrics include policy return, maximum drawdown, protection versus full gross, recovery return/capture, recovery average gross, and missed recovery upside. LOCO concatenates all non-excluded observations and recomputes metrics after removing one fixed crisis window. Split-era results use the same definitions. Crisis concentration is the largest positive crisis protection divided by total positive crisis protection.

## Independent episodes and uncertainty

A loud observation is `elevated` or `risk-off`. Loud observations remain in one episode when separated by at most ten non-loud sessions; an eligible independent episode must contain at least three loud observations. The episode outcome window is first loud observation through 21 sessions after the last loud observation. Episodes are classified as risk-off-containing or elevated-only, and as downside/false-positive by whether peak-to-trough loss from episode start reaches 5%. Report alert-window excess, 21-session rebound participation, and whether policy timing benefit is positive.

Uncertainty uses 2,000 circular moving-block bootstrap draws, 21-session blocks, seed `20260923`, with 90% intervals for CAGR, maximum drawdown, expected shortfall, Calmar, certainty-equivalent differences, and policy excess versus full gross and matched constant. No resampling choice may change after outcomes.

## Fixed promotion/falsification gates

`CURRENT_LADDER_VALIDATED_FOR_ADVISORY_REFERENCE` requires all of: effective episode N≥40, risk-off-containing N≥12, elevated-only N≥12; primary current ladder improves maximum drawdown by at least 10% relative and CVaR by at least 5% relative versus full gross; Calmar exceeds both full gross and matched constant; CAGR penalty versus full gross is no worse than 1.5 percentage points; certainty-equivalent difference versus matched constant has a positive 90% lower bound; versus `current_riskoff_075`, current improves maximum drawdown by at least 1.5 percentage points, does not reduce Calmar, and loses no more than 0.5 percentage points CAGR; directions survive both lag sensitivities, cost stress, both eras, and every LOCO run; no one crisis supplies 50% or more of positive protection.

`SIMPLER_POLICY_SUPPORTED` requires effective episode N≥20 and risk-off-containing N≥8; `binary_loud_075` improves maximum drawdown by at least 10% relative and CVaR by at least 5% relative versus full gross, beats full gross and matched constant on Calmar, loses no more than 1.5 percentage points CAGR, has positive certainty-equivalent lower bound versus matched constant, produces positive timing benefit in at least 55% of eligible episodes, keeps the protection/Calmar direction under lag/cost sensitivities and both eras, remains directionally positive in at least eight of nine LOCO runs, and has crisis concentration below 60%.

If exact gates pass, verdict 1. Else if simpler gates pass, verdict 3. Else if effective N<20 or risk-off-containing N<8, verdict 5. Else if neither current nor binary improves both Calmar and CVaR versus the matched constant in the primary run, verdict 4. Otherwise verdict 2. Detector validity itself is not re-estimated by this capital-policy study.

## Product-language gate

Only verdict 1 permits the current ladder to be called an advisory `risk-budget reference`; even then it is not trade authority. `Suggested size` is prohibited without a later explicit live-policy promotion. Verdicts 2–5 prohibit presenting `×0.62` as advice; it may appear only in research/debug disclosure as the current unvalidated mapping. Plain-English rounding such as “half of normal” is prohibited because it changes 0.62 to 0.50 and amplifies prescriptive meaning. No verdict in this wave authorizes live sizing, exits, vetoes, `can_force`, or a control-plane consumer.
