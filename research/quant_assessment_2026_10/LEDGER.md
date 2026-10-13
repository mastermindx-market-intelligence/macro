# Quant assessment 2026-10 — Q01–Q20 ledger

Compiled 2026-10-10 from each brief's staged `_handoff/INTEGRATE_READY.json` and `VERDICT.md`, plus GitHub merge state. Source package: `macro_quant_assessment_2026-10-08` (assessment pin Macro `main@094097a5a7a4`).

Every brief shipped as a pure, opt-in research reference with synthetic red→green tests, a PREREG frozen before outcomes were read, one dependence-aware empirical comparison on licensed retained local data, an independent read-only Opus audit, and a verdict. **Nothing here is wired into a producer, page, gate, rank or size.** A KEEP is a research-tier result only; promotion requires the owning program's own gauntlet and acceptance.

Verdict counts: INSUFFICIENT_DATA 8, KEEP 6, REJECT 6

| Brief | Title | Verdict | PR | State | Merge | Research record |
|---|---|---|---|---|---|---|
| Q01 | Bid/ask-aware, arbitrage-constrained volatility surfaces | **INSUFFICIENT_DATA** | [#8730](https://github.com/mastermindx-market-intelligence/macro/pull/8730) | MERGED | `0ebcffbfbe3e` | `research/quant_assessment_2026_10/Q01_arbitrage_constrained_surface/` |
| Q02 | American-exercise and discrete-dividend pricing/Greek qualification | **INSUFFICIENT_DATA** | [#8732](https://github.com/mastermindx-market-intelligence/macro/pull/8732) | MERGED | `845328fa055a` | `research/quant_assessment_2026_10/Q02_american_exercise_greeks/` |
| Q03 | Corporate-action-correct off-exchange participation history | **KEEP** | [#8710](https://github.com/mastermindx-market-intelligence/macro/pull/8710) | MERGED | `0a8d031f8068` | `research/quant_assessment_2026_10/Q03_offexchange_share_basis/` |
| Q04 | Trade-sign uncertainty and measurement-error calibration | **INSUFFICIENT_DATA** | [#8717](https://github.com/mastermindx-market-intelligence/macro/pull/8717) | MERGED | `ef42dd6d54cd` | `research/quant_assessment_2026_10/Q04_signing_uncertainty/` |
| Q05 | Option outcome sensitivity to latency, available size and execution cost | **INSUFFICIENT_DATA** | [#8720](https://github.com/mastermindx-market-intelligence/macro/pull/8720) | MERGED | `e4c0cf071067` | `research/quant_assessment_2026_10/Q05_option_execution_sensitivity/` |
| Q06 | Feasible sparse-data calibration for the existing FS-3 study | **REJECT** | [#8722](https://github.com/mastermindx-market-intelligence/macro/pull/8722) | MERGED | `f710aec2c1a8` | `research/quant_assessment_2026_10/Q06_sparse_weighted_calibration/` |
| Q07 | Fitted, leakage-controlled HAR volatility challenger | **KEEP** | [#8707](https://github.com/mastermindx-market-intelligence/macro/pull/8707) | MERGED | `41378472e286` | `research/quant_assessment_2026_10/Q07_fitted_har_volatility/` |
| Q08 | Regularized covariance and uncertainty-aware independent-bet counts | **REJECT** | [#8733](https://github.com/mastermindx-market-intelligence/macro/pull/8733) | MERGED | `f4952a57732a` | `research/quant_assessment_2026_10/Q08_regularized_covariance/` |
| Q09 | Publication-vintage ATS/non-ATS concentration and venue-change analysis | **INSUFFICIENT_DATA** | [#8736](https://github.com/mastermindx-market-intelligence/macro/pull/8736) | MERGED | `090c4e3a4ab6` | `research/quant_assessment_2026_10/Q09_released_ats_concentration/` |
| Q10 | Condition-adjusted abnormal off-exchange participation | **KEEP** | [#8737](https://github.com/mastermindx-market-intelligence/macro/pull/8737) | MERGED | `ff19e24a0cbf` | `research/quant_assessment_2026_10/Q10_conditional_offexchange_anomalies/` |
| Q11 | Persistent off-exchange activity regimes with explicit detection delay | **KEEP** | [#8738](https://github.com/mastermindx-market-intelligence/macro/pull/8738) | MERGED | `363b4e6296b7` | `research/quant_assessment_2026_10/Q11_offexchange_episode_duration/` |
| Q12 | Robust option-implied forward and carry-consistency estimates | **INSUFFICIENT_DATA** | [#8739](https://github.com/mastermindx-market-intelligence/macro/pull/8739) | MERGED | `ed8a8294a9a4` | `research/quant_assessment_2026_10/Q12_implied_forward_carry/` |
| Q13 | Risk-neutral tail-density estimation with quote-uncertainty bounds | **INSUFFICIENT_DATA** | [#8740](https://github.com/mastermindx-market-intelligence/macro/pull/8740) | MERGED | `3a030d23a4cf` | `research/quant_assessment_2026_10/Q13_risk_neutral_tail_density/` |
| Q14 | Horizon-matched variance-risk-premium research | **REJECT** | [#8741](https://github.com/mastermindx-market-intelligence/macro/pull/8741) | MERGED | `fdbdad7eb00e` | `research/quant_assessment_2026_10/Q14_forward_variance_premium/` |
| Q15 | Microstructure-noise-aware realized variance measurement | **REJECT** | [#8742](https://github.com/mastermindx-market-intelligence/macro/pull/8742) | MERGED | `9a894158db29` | `research/quant_assessment_2026_10/Q15_noise_robust_realized_variance/` |
| Q16 | Delayed-feedback and regime-shift calibration of existing forecast intervals | **REJECT** | [#8743](https://github.com/mastermindx-market-intelligence/macro/pull/8743) | MERGED | `66f3fb005587` | `research/quant_assessment_2026_10/Q16_delayed_interval_calibration/` |
| Q17 | Stable factor whitening under collinearity and missing observations | **REJECT** | [#8744](https://github.com/mastermindx-market-intelligence/macro/pull/8744) | MERGED | `1e139787c7a3` | `research/quant_assessment_2026_10/Q17_stable_factor_whitening/` |
| Q18 | Asynchronous-session covariance and lead/lag measurement qualification | **KEEP** | [#8745](https://github.com/mastermindx-market-intelligence/macro/pull/8745) | MERGED | `3df94392b6c2` | `research/quant_assessment_2026_10/Q18_asynchronous_covariance/` |
| Q19 | First-passage ambiguity and censoring-aware outcome diagnostics | **INSUFFICIENT_DATA** | [#8746](https://github.com/mastermindx-market-intelligence/macro/pull/8746) | MERGED | `41c8d416d88c` | `research/quant_assessment_2026_10/Q19_censoring_path_ambiguity/` |
| Q20 | Dependence-aware challenger comparison on the existing trial budget | **KEEP** | [#8747](https://github.com/mastermindx-market-intelligence/macro/pull/8747) | MERGED | `1df2defcf16a` | `research/quant_assessment_2026_10/Q20_dependence_aware_model_comparison/` |

## Verdict lines (verbatim from each VERDICT.md)

- **Q01** — VERDICT: INSUFFICIENT_DATA
- **Q02** — VERDICT: INSUFFICIENT_DATA. The single empirical trial (E2) was not run.
- **Q03** — Q03 VERDICT — KEEP (research reference only; not wired, not promoted)
- **Q04** — VERDICT: INSUFFICIENT_DATA
- **Q05** — Q05 VERDICT — INSUFFICIENT_DATA
- **Q06** — Q06 verdict: REJECT (K1 failed)
- **Q07** — Q07 verdict: KEEP (weak vs EWMA; research candidate only; no production effect)
- **Q08** — VERDICT: REJECT (the estimator contest). The incumbent sample correlation stays.
- **Q09** — Q09 VERDICT — INSUFFICIENT_DATA
- **Q10** — VERDICT: KEEP — as a research-tier, descriptive explanatory calibration correction for the incumbent own-history participation anomaly. This is not an alpha signal, carries no direction, and nothing imports or wires the module (`engine/offexchange_conditional_residual.py`, `RESEARCH_ONLY = True`).
- **Q11** — Q11 — VERDICT: KEEP (research reference only, not wired)
- **Q12** — Q12 verdict — INSUFFICIENT_DATA
- **Q13** — VERDICT: `INSUFFICIENT_DATA`
- **Q14** — VERDICT: REJECT the predictive upgrade (trial `Q14-T1`).
- **Q15** — Q15 — Verdict: REJECT (clear)
- **Q16** — VERDICT: REJECT
- **Q17** — VERDICT: REJECT
- **Q18** — Q18 verdict: KEEP (research reference only, nothing wired)
- **Q19** — Q19 VERDICT: INSUFFICIENT_DATA (brief level; no admitted cohort). The exploratory trial REJECTs, and the ambiguity correction is kept as a research reference.
- **Q20** — Study verdict: KEEP. The Q20 module (`engine/challenger_spa_comparison.py`) is kept as a research-only, unwired diagnostic for the existing statistics owner. Every pre-registered §8 method-control gate passed, and the single frozen empirical comparison ran on the eligible admitted family (PREREG §9).

## Preserved restrictions

DNR keys honoured by every brief: `DNR:KILL-OUTCOME-AUDITION`, `DNR:KILL-LLM-ORIGINATION`, `DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-POSITIONING-FUSION`, `DNR:KILL-REGIME-SCORECARD`, `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR`, `DNR:KILL-CAUSAL-DAG-ALPHA`, `DNR:HOLD-PSS-AF1-FINRA`, `DNR:HOLD-PSS-CD1-CROWDING`. FINRA short volume is not short interest; ATS classification is not owner intent; inferred dealer inventory is never called observed; hedge repricing is not realized impact.
