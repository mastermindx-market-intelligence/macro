# China Market State P3 — preregistration

**Operation:** `cn-risk-p3-market-state-validation-20260923-solpro-001`  
**Repository/base:** `mastermindx-market-intelligence/macro@d5eb16f3b3a093afb053efe275be62778729dcf4`  
**Protected Skillpack:** `mastermindx-market-intelligence/Mastermind@63555e1f9405c79405fc30682aa502a68d8abf80` (`mastermind.sol_skillpack.v1`, 1.0.1/bootstrap1)  
**Branch:** `sol/cn-risk-p3-market-state-validation-20260923`  
**Frozen sample end:** `2026-09-24`  
**Prereg payload SHA-256:** `0533cb7add838e65553756e9f21b59b9ff1ae058f347dac0d946da4e977671d8`

## Purpose and authority ceiling

Determine whether the current six-leg China Market State construction, its hand weights, and its 42/60 product cuts add information beyond simple A-share baselines, and what the 0–100 score may honestly mean. This is research-only. It changes no production score, weights, cuts, mapping, UI, sizing, Risk Radar, Portfolio, or Prophet behavior. Reconstructed historical evidence is class A. It cannot become class C authority by prose.

No forward outcome statistic may be generated before the commit containing this preregistration exists. The machine-readable contract is `preregistration.v1.json`; that file is authoritative for exact thresholds, horizons, challengers, slices, timing transforms, metrics, and decision gates.

## Frozen identity

- Model-source mapping SHA-256: `4c7e9e7e4abdce13d8447affd3d8cca9c57fbd2e85264ccc6a44945c065cbe20`
- Input mapping SHA-256: `652af799ba40d7a0820c5249e5dec9eb332887b4af5483f4995d672f456d7c74`
- Method mapping SHA-256: `09c32763c7a848abb52a45852c3b42ff4aee63f61e3af269813ef2b9ddec6356`
- Manifest files: `model_source_manifest.v1.json`, `input_manifest.v1.json`, `method_manifest.v1.json`
- Source qualification: `source_qualification.v1.json`

All series are truncated to `2026-09-24` before model reconstruction or target creation. The committed HG/GC files contain later rows; those later rows are explicitly out of sample.

## Primary study

Primary benchmark is Shanghai Composite `000001.SS`. `510300.SS` is an ETF proxy diagnostic only; it is never described as the exact CSI300 cash index. SPY is forbidden as a grading benchmark. The primary contract-complete reconstruction begins 2012-08-14; pre-2012 history is descriptive/coverage context only. Chronological halves split at 2019-09-02, with mandatory post-2016 and near-current (2020-06-15+) slices.

Outcomes start at the first SHCOMP close strictly after the score stamp: >=5% max drawdown within 21 sessions, >=10% max drawdown within 42 sessions, and 21/42-session returns. Partial forward windows are excluded.

## Frozen challengers and sensitivity

The candidate set is fixed before outcomes: current hand weights, equal weight, trend-only, breadth-only, trend+breadth, trend+breadth+liquidity, stress-half, stress-zero, and one-component-at-a-time LOCO. No free/learned weight search is allowed. Cut sensitivity is frozen to lower cuts 34/38/42/46/50 and upper cuts 52/56/60/64/68. These are diagnostics, not a post-hoc menu for selecting production constants.

Crisis LOCO reuses the already-committed China `ERA_TABLE`: 2015 H2 crash, 2018 deleveraging, 2020 COVID crash, and 2021–2022 grinding bear; 2023–2024 grind is a separate stress-era sensitivity.

## Temporal/source honesty

Current production-reference history and the conservative release-lagged current-vintage reconstruction are reported separately. Neither is genuine historical vintage PIT. Macro release shifts are frozen in `preregistration.v1.json`. Breadth is a current-universe 82-name reconstruction with explicit roster coverage. The current production 3-session trend anchor and a CN-session-anchor counterfactual are both required; P3 does not silently repair production.

## Inference and adjudication

The raw 0–100 score is not a probability; Brier scoring is forbidden. Report event discrimination, base-rate lift, continuous rank association, return/drawdown magnitude, horizon-sized paired moving-block uncertainty, and effective-N/episode views. Overlapping daily rows are not treated as independent authority.

`FORECAST_CAPABLE` cannot be earned by this retrospective study. It requires genuinely issued same-model prospective evidence plus separately accepted promotion law. P3 can at most classify the score `CONDITIONAL_FORECAST_VALUE`; otherwise it is `DESCRIPTIVE_ONLY`. Exact enum gates for weights, cuts, and components are frozen in the JSON contract.
