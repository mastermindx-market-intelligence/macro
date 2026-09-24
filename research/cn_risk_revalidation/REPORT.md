# China External-Driver Risk Radar — Preregistered Revalidation

**Operation:** `cn-risk-p1-radar-revalidation-20260923-solpro-001`  
**Base:** `8db6896dab2199a4b7fc61a005c225380cac7cd6`  
**Preregistration:** `db5590accaa03f78396ca91b6874f04b9bcf4cf3`  
**Status:** Draft/HOLD research package; production behavior unchanged.

## Executive conclusion

As of **2026-09-23**, the exact production composite is **98.02 / 100** and emits **risk-off** with the context gate open. This score is a causal trailing-504-session rank, not a 98% drawdown probability.

The construction retains meaningful hazard discrimination, especially for the historical 10%/42-session target, but the independent-episode ceiling is 18 for the current loud state. That supports directional hazard language, not certification of the exact 50% displayed odds.

## Claim-by-claim adjudication

| Claim | Verdict | Basis |
|---|---|---|
| extreme China external-driver hazard | **KEEP_BUT_RELABEL** | emitted risk-off lift is 1.63x for 5%/21d and 2.64x for 10%/42d; effective episodes 18/18. Call this an elevated external-driver hazard, not an exact crisis probability. |
| 98th-percentile intensity semantics | **KEEP_BUT_RELABEL** | current score is 98.02; valid only as a causal trailing-504-session composite percentile, not 98% drawdown odds or all-history extremity. |
| >=5%/21d risk-off probability = 50% | **INSUFFICIENT_EVIDENCE** | observed 0.473 versus displayed 0.500; effective episodes 18; block CI [0.34781895937277263, 0.5800988796034574]; episode CI [0.27406976744186046, 0.6372410220167222]. |
| >=10%/42d historical lift ~2.07x | **KEEP_BUT_RELABEL** | current ungated risk-off reconstruction lift 2.03x with 18 effective episodes; the original 2.07x harness and exact trigger were not committed, so this is a reconstruction, not byte-for-byte replication. |
| elevated vs risk-off separation | **KEEP_BUT_RELABEL** | risk-off minus elevated observed 5%/21d rate 0.062; block CI [-0.06270803504915402, 0.18377055734658934]; effective episodes 18/18. |
| 5d / 10d / 21d ladder | **INSUFFICIENT_EVIDENCE** | The surface is mechanically monotone, but its current calibrator explicitly seeds flat-at-base and the loud-state episode floor is not met across all horizons; supported material inversion=False. |
| context gate value-add | **KEEP_BUT_RELABEL** | gate-minus-ungated Brier difference -0.0021; risk-off lift difference 0.22x; effective gated risk-off episodes 18. |

## Confirmatory targets — Shanghai Composite

| Target | Eligible | Base rate | Risk-off rate | Risk-off lift | Block 95% CI | Effective episodes | Permutation p | AP / base | AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| >=5% / 21 sessions | 5701 | 28.9% | 47.3% | 1.63× | [1.243, 2.053] | 18 | 0.0094 | 1.24× | 0.582 |
| >=10% / 42 sessions | 5680 | 16.9% | 44.4% | 2.64× | [1.817, 3.585] | 18 | 0.0066 | 1.74× | 0.655 |

The primary UI target uses the **emitted** state after the context gate. The historical claim is also shown below using the **ungated >=91st-percentile composite extreme**, because that reconstruction reproduces the recorded split-half pattern while the original executable trigger is unavailable.

## Historical 10%/42-session stability

### Split-half and era

| Slice | Eligible rows | Risk-off rows | Base rate | Conditional rate | Lift |
|---|---:|---:|---:|---:|---:|
| First half | 2840 | 293 | 23.1% | 52.2% | 2.26× |
| Second half | 2840 | 413 | 10.6% | 21.5% | 2.03× |
| Pre-2016 | 3117 | 340 | 24.8% | 51.8% | 2.08× |
| 2016+ | 2563 | 366 | 7.2% | 18.0% | 2.51× |

### Leave-one-crisis-out

| Omitted episode | Applicable | Excluded rows | Remaining lift |
|---|---:|---:|---:|
| asian_russia_ltcm | no | 0 | not testable; pre-sample |
| global_financial_crisis | yes | 466 | 1.63× |
| china_equity_devaluation | yes | 247 | 2.16× |
| us_china_trade_war | yes | 307 | 2.10× |
| covid_shock | yes | 159 | 2.04× |
| china_property_regulatory_zero_covid | yes | 485 | 2.30× |

## A-share replication — 510300.SS ETF proxy

The repository does not contain exact CSI300 cash-index history. These are outcome-only replications on the 510300.SS ETF proxy using the unchanged Shanghai-built signal.

| Target | Eligible | Base rate | Emitted risk-off lift | Ungated risk-off lift | Effective episodes |
|---|---:|---:|---:|---:|---:|
| 5pct_21d | 3463 | 24.3% | 1.99× | 1.59× | 12 |
| 10pct_42d | 3442 | 12.3% | 2.62× | 2.01× | 12 |

## Calibration of the displayed 5d / 10d / 21d surface

| Horizon | Brier | Skill vs baked base | Skill vs delayed expanding base | Intercept | Slope | Supported inversion |
|---|---:|---:|---:|---:|---:|---:|
| h5 | 0.0653 | 1.09% | 1.52% | 0.052 | 1.060 | no |
| h10 | 0.1259 | 2.10% | 3.05% | -0.048 | 1.016 | no |
| h21 | 0.2019 | 1.89% | 3.25% | -0.122 | 0.994 | no |

### Fixed state bins

| Horizon | State | Forecast | Observed | Block 95% CI | Episode 95% CI | Effective episodes | Hit / non-hit episodes |
|---|---|---:|---:|---:|---:|---:|---:|
| h5 | calm | 6.0% | 5.7% | [4.0%, 7.6%] | [2.7%, 8.9%] | 12 | 9 / 3 |
| h5 | watch | 8.0% | 7.7% | [4.7%, 11.2%] | [3.5%, 12.6%] | 34 | 13 / 21 |
| h5 | caution | 9.0% | 6.0% | [3.6%, 8.9%] | [3.1%, 11.5%] | 27 | 13 / 14 |
| h5 | elevated | 12.0% | 13.3% | [4.9%, 22.7%] | [1.5%, 27.3%] | 18 | 6 / 12 |
| h5 | risk-off | 15.0% | 15.4% | [8.7%, 22.6%] | [4.0%, 26.9%] | 18 | 7 / 11 |
| h10 | calm | 13.0% | 12.2% | [9.1%, 15.7%] | [6.4%, 18.9%] | 12 | 10 / 2 |
| h10 | watch | 16.0% | 15.3% | [10.6%, 20.7%] | [9.8%, 21.1%] | 34 | 17 / 17 |
| h10 | caution | 18.0% | 16.1% | [11.2%, 21.8%] | [10.5%, 25.9%] | 27 | 14 / 13 |
| h10 | elevated | 21.0% | 20.4% | [10.1%, 31.0%] | [6.0%, 36.8%] | 18 | 8 / 10 |
| h10 | risk-off | 32.0% | 31.0% | [19.7%, 41.8%] | [13.0%, 48.0%] | 18 | 9 / 9 |
| h21 | calm | 27.0% | 25.1% | [20.5%, 30.0%] | [18.3%, 32.0%] | 12 | 11 / 1 |
| h21 | watch | 32.0% | 28.4% | [22.3%, 35.1%] | [20.9%, 35.1%] | 34 | 23 / 11 |
| h21 | caution | 35.0% | 30.9% | [22.7%, 39.9%] | [22.3%, 46.1%] | 27 | 17 / 10 |
| h21 | elevated | 40.0% | 41.0% | [27.8%, 53.5%] | [22.8%, 56.8%] | 18 | 12 / 6 |
| h21 | risk-off | 50.0% | 47.3% | [34.8%, 58.0%] | [27.4%, 63.7%] | 18 | 10 / 8 |

## Economic baseline comparison

### 5pct_21d

| Construction | AP | AUC | Risk-off lift | Elevated-plus lift |
|---|---:|---:|---:|---:|
| Current emitted radar | 0.358 | 0.582 | 1.63× | 1.56× |
| breadth_only | 0.365 | 0.564 | 1.57× | 1.42× |
| rates_only | 0.324 | 0.522 | 1.24× | 1.11× |
| trend_context | 0.345 | 0.529 | 1.09× | 1.09× |
| ungated_composite | 0.358 | 0.582 | 1.41× | 1.34× |

### 10pct_42d

| Construction | AP | AUC | Risk-off lift | Elevated-plus lift |
|---|---:|---:|---:|---:|
| Current emitted radar | 0.294 | 0.655 | 2.64× | 2.46× |
| breadth_only | 0.272 | 0.588 | 2.12× | 1.82× |
| rates_only | 0.238 | 0.575 | 1.58× | 1.33× |
| trend_context | 0.223 | 0.535 | 1.12× | 1.12× |
| ungated_composite | 0.294 | 0.655 | 2.03× | 1.87× |

## Context-gate value-add

- 5%/21d gated risk-off lift: **1.63×**; ungated: **1.41×**.
- Lift difference: **0.22×**, block CI [-0.019, 0.493].
- Brier difference, gated minus ungated: **-0.0021**, block CI [-0.005, 0.000]. Negative favors the gate.
- 10%/42d gated/ungated lifts: **2.64× / 2.03×**.

## Genuinely issued forward ledger — kept separate

| Rows | Matured | Pending | Matured loud | Loud hits | Matured risk-off | Risk-off hits | can_force |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 34 | 16 | 18 | 5 | 2 | 4 | 1 | false |

Pending issuance spans **['2026-08-26', '2026-09-23']**; the September episode remains unresolved. `not eligible: fewer than 30 matured rows or 8 matured loud alerts`

## Provenance and reproducibility

- Exact construction hash: `a09fce6e68960eaa89dd05c387fc6f547ede35e89a9a097d42559acb6fe16f74`
- Historical PIT qualification: **causal_transform_on_snapshot_not_vintage_pit**.
- CSI replication: **510300.SS ETF proxy**, not the exact CSI300 cash index.
- Historical reconstruction and issued forward evidence are distinct evidence classes and are never pooled.

### Data files

| Source | Role | Rows | Date range | SHA-256 |
|---|---|---:|---|---|
| shanghai_composite | canonical_benchmark_and_context_gate | 7083 | 1997-07-02 → 2026-09-23 | `fde7953ffe4db529…` |
| csi300_etf_proxy | outcome_only_replication_proxy | 3485 | 2012-05-04 → 2026-09-23 | `5fd8228d7a1bc548…` |
| china_breadth | breadth_subleg | 8901 | 1991-03-12 → 2026-09-23 | `270504c850f35868…` |
| us_2y | rate_subleg | 12573 | 1976-06-01 → 2026-09-21 | `bfaeca464df49b4a…` |
| us_10y_real | rate_subleg | 5934 | 2003-01-02 → 2026-09-21 | `82194cc322bd53a4…` |
| us_10y | rate_and_differential_subleg | 16165 | 1962-01-02 → 2026-09-21 | `34b9744f940966ea…` |
| usd_cnh | fx_subleg | 3360 | 2013-02-11 → 2026-09-23 | `f8392d542451d8e3…` |
| dxy | pre_cnh_fx_backfill | 14161 | 1971-01-04 → 2026-09-23 | `dee55311cc22f153…` |
| china_10y | differential_subleg | 6178 | 2002-01-04 → 2026-09-23 | `32b42dbde1937ede…` |
| cn_forward_ledger | genuinely_issued_forward_evidence | 34 | n/a | `11577f99d426d3b8…` |

## Discoveries

- The current production calibrator explicitly treats raw state rates as descriptive and emits a flat-at-base probability surface; it is not the provenance of the baked CN ladder.
- Merged PR #711 and the engine docstring preserve the 2.07x claim, but no executable research harness, immutable result artifact, or exact original extreme trigger accompanied the claim.
- The available CSI300 replication series is 510300.SS, an ETF proxy. No exact CSI300 cash-index series was found in the repository.
- Historical transforms are causal on repository snapshots, but vintage identifiers are unavailable; this is not fully vintage point-in-time evidence.
- Issued forward rows remain a separate evidence class and are not pooled with reconstructed history.

## Proposed follow-up

- Do not retune production in this PR. Open a separately preregistered calibration candidate only after the forward authority floors and independent loud-state episode floors mature.
- Recover or rebuild the original PR #711 validation harness under a new provenance-only commission; do not retroactively call the present reconstruction byte-identical replication.
- Acquire a lawful exact CSI300 cash-index history if the cash-index replication claim must remain exact; otherwise relabel the current evidence as a 510300.SS ETF-proxy replication.

## What must not be redone

- Preregistration commit db5590accaa03f78396ca91b6874f04b9bcf4cf3 is immutable and must not be rewritten after outcome inspection.
- Do not merge reconstructed historical evidence with the issued forward ledger.
- Do not reinterpret the 98th-percentile intensity as a 98% drawdown probability.
- Do not change production bands, probabilities, gate logic, can_force, UI, Market State policy, or consumers in this research PR.
- Do not silently substitute FXI or label 510300.SS as the exact CSI300 cash index.

## One-command reproduction

```bash
python3 -m scripts.research.cn_risk_radar_revalidation \
  --repo-root . \
  --output-dir research/cn_risk_revalidation \
  --bootstrap-reps 5000 \
  --permutation-reps 5000 \
  --seed 20260923
```
