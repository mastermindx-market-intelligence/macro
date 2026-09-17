# TTI R1-A report — extended-session persistence

**Status:** retrospective corrected-history result / no promotion / no live authority.

This report adjudicates the exact R1-A construction frozen before outcomes. It does not adjudicate all extended-hours persistence, all low-timeframe trading, or the submitted INTC example. No thresholds were changed after opening outcome columns.

## 1. Immutable identities

- Prereg/config were committed at `5d950c85cd0c8e3a393e555433bf94fd3ee395a7` before outcome computation.
- The full 84-cell grid was appended to the existing `entry_radar` TrialLedger at `0109877f57009973cbebe9f72e43bd23e35a5183`; `REGISTRATION_RECEIPT.json` proves the previous ledger prefix is byte-preserved.
- Causal primitives and offline runner were subsequently implemented and hardened through `30a72e85a25f188d1f654ec71b18872aa4fee3d8` before canonical run-003.
- Terminal dependency: `c0f36cb16fadd190ad747fc47a28405d9ec0fca4`; D0 qualification module SHA256 `d4c5c99114ce80a01fa5dd3ea32b1b2cf688c772be25a21df7b5220d912cf8aa`.
- Prereg SHA256 `35071d8529bd98c717011a9bdade1e587bd2da97e991363e8d5b8bf2e8c91e02`; config SHA256 `2a85964ec61371f7197f6d9d710c71f747cf67b1297bb08bfd58b1ae5ebca679`; input manifest SHA256 `59c50ed405bd76c083a1d2beb20cf25edd6f4bd892c3e55fd38d21a66bef642b`.
- Canonical aggregate result SHA256 `5c75a38d3f5acc61ad5e79fcec2f26af37a6f62da0ed449c4b1533b5cc35ff0b`.
- Private panel/outcome evidence hashes: `e33c04d269ba7c81c19b1487f7c154f235093d84da5fc2b8d94a4be2a0fc3292` and `8da3f4df87cd21af9a12b3082f0146487f14f212d7ed23cab2fed8532b553c1d`; raw licensed rows remain outside Git.

Run-001 was rejected after adversarial review found causal robustness defects. Those defects were repaired test-first. Run-002 and run-003 are byte-identical at the feature-panel, outcomes and result levels on the unchanged captured inputs; this shows the repairs did not opportunistically alter the observed result while closing future contamination paths.

## 2. Population and coverage

Scheduled dates: **312**; name-day candidates: **2464**; comparable rows: **1810**; emitted outcome rows across arms/horizons/costs: **58308**.

Ineligibility counts: `{"ah_ineligible": 180, "early_close_ah_unqualified": 24, "not_comparable": 630, "pre_ineligible": 360}`. These are data/recipe eligibility outcomes, not failed trades.

Fixed-current stock cohort: AMD, NVDA, MU, AVGO, QCOM, AAPL, JPM, XOM; QQQ benchmark. Current-universe survivorship/composition limits remain. INTC is not in this measurement.

## 3. Primary 60-minute / 25 bp comparison

| Arm | Fires | Dates | Mean net beta residual | Same-date delta vs baseline | Week-block 95% interval | Disposition |
|---|---:|---:|---:|---:|---:|---|
| ALL_EARLY | 1810 | 269 | -0.268% | 0.000% | 0.000% .. 0.000% | control |
| GAP_UP | 709 | 243 | -0.269% | -0.002% | -0.085% .. 0.087% | no incremental 60m evidence |
| PERSISTENT | 12 | 10 | -0.159% | -0.174% | -0.436% .. 0.055% | not supported as tested standalone |
| WEAKNESS_PERSISTENT | 1 | 1 | -0.427% | -0.269% | -0.269% .. -0.269% | uninformative (N=1) |
| WEAKNESS_RECLAIM | 514 | 213 | -0.270% | 0.018% | -0.094% .. 0.126% | inconclusive/context-only |
| ALL_LATE | 1810 | 269 | -0.252% | 0.000% | 0.000% .. 0.000% | control |
| PERSISTENT_OPEN_ACCEPT | 3 | 2 | 0.780% | 0.401% | 0.053% .. 0.749% | underpowered prospective hypothesis |

`PERSISTENT` also underperformed the same-date `GAP_UP` comparator by about **-0.165%** over 60 minutes (10 dates; week-block interval approximately -0.538% to +0.152%). The exact strict persistence construction therefore did not add useful short-horizon selection evidence in this cohort.

`PERSISTENT_OPEN_ACCEPT` produced a positive 60-minute observation on only **3 name-days / 2 dates**, all in the development partition. Its positive 60-minute result cannot be treated as validation; the same tiny sample was negative at 1-day and 3-day horizons. It is a prospective question, not an edge claim.

## 4. Full primary-cost horizon grid

All values below use the preregistered 25 bp round-trip cost assumption. Full 10/25/50 bp × 7 × 4 output is preserved in `RESULT.json`.

| Arm | Horizon | Fires | Available | Mean net beta residual | Mean MFE | Mean MAE |
|---|---|---:|---:|---:|---:|---:|
| ALL_EARLY | 60m | 1810 | 1810 | -0.268% | 1.072% | -1.121% |
| ALL_EARLY | close | 1810 | 1810 | -0.215% | 1.583% | -1.650% |
| ALL_EARLY | 1d | 1810 | 1804 | -0.024% | 2.820% | -2.630% |
| ALL_EARLY | 3d | 1810 | 1788 | 0.352% | 4.631% | -3.790% |
| GAP_UP | 60m | 709 | 709 | -0.269% | 1.059% | -1.142% |
| GAP_UP | close | 709 | 709 | -0.259% | 1.570% | -1.648% |
| GAP_UP | 1d | 709 | 704 | 0.038% | 2.848% | -2.532% |
| GAP_UP | 3d | 709 | 702 | 0.584% | 4.707% | -3.676% |
| PERSISTENT | 60m | 12 | 12 | -0.159% | 0.718% | -1.241% |
| PERSISTENT | close | 12 | 12 | 0.461% | 1.262% | -1.390% |
| PERSISTENT | 1d | 12 | 12 | 0.084% | 2.277% | -2.377% |
| PERSISTENT | 3d | 12 | 12 | 1.376% | 4.589% | -3.721% |
| WEAKNESS_PERSISTENT | 60m | 1 | 1 | -0.427% | 0.611% | -1.262% |
| WEAKNESS_PERSISTENT | close | 1 | 1 | 0.379% | 1.102% | -1.262% |
| WEAKNESS_PERSISTENT | 1d | 1 | 1 | -0.514% | 1.661% | -1.262% |
| WEAKNESS_PERSISTENT | 3d | 1 | 1 | 0.917% | 5.355% | -1.262% |
| WEAKNESS_RECLAIM | 60m | 514 | 514 | -0.270% | 1.077% | -1.118% |
| WEAKNESS_RECLAIM | close | 514 | 514 | -0.228% | 1.619% | -1.721% |
| WEAKNESS_RECLAIM | 1d | 514 | 510 | 0.022% | 2.987% | -2.617% |
| WEAKNESS_RECLAIM | 3d | 514 | 508 | 0.396% | 4.672% | -3.678% |
| ALL_LATE | 60m | 1810 | 1810 | -0.252% | 0.885% | -0.929% |
| ALL_LATE | close | 1810 | 1810 | -0.203% | 1.433% | -1.464% |
| ALL_LATE | 1d | 1810 | 1804 | -0.012% | 2.740% | -2.500% |
| ALL_LATE | 3d | 1810 | 1788 | 0.366% | 4.597% | -3.702% |
| PERSISTENT_OPEN_ACCEPT | 60m | 3 | 3 | 0.780% | 1.558% | -0.379% |
| PERSISTENT_OPEN_ACCEPT | close | 3 | 3 | 1.131% | 1.949% | -0.539% |
| PERSISTENT_OPEN_ACCEPT | 1d | 3 | 3 | -0.649% | 3.884% | -0.539% |
| PERSISTENT_OPEN_ACCEPT | 3d | 3 | 3 | -1.265% | 5.935% | -0.811% |

## 5. What survives the experiment

1. **Strict smooth AH→PM persistence is not supported as a standalone selector in this exact construction.** It fired only 12 times across 10 dates, had negative primary incremental performance, and had only one assessment-partition event. Do not rank or alert on it.
2. **Prior weakness + simple premarket reclaim is broad enough to study but not a demonstrated 60-minute edge.** It fired 514 times across 213 dates; the primary incremental delta was near zero with an interval spanning both signs. Later-horizon assessment-period improvement is unstable relative to development and remains context-only.
3. **Opening acceptance is potentially different from raw persistence, but current N is unusably small.** Preserve it as a prospective hypothesis only. The current evidence does not justify threshold relaxation or a post-hoc rescue search.
4. **The next independent critical-path experiment remains exhaustion/reclaim versus healthy continuation.** That question was specified before these outcomes and therefore is not a rescue of R1-A. It should separately measure local reversal, final LOD/HOD survival, confirmation delay and remaining opportunity from an available entry.

## 6. Boundaries and falsifiers

- Corrected archive only: historical knowledge-time, exact quote liquidity and fills are not proven.
- The historical projection discarded provider `vw`/transaction-count detail; HLC3×volume remains a bar-VWAP proxy, not trade VWAP or aggressor/market-maker intent.
- Week-block intervals are descriptive uncertainty; no promotion-grade p-value, Sharpe, DSR or calibrated probability is claimed.
- Costs are fixed sensitivities, not measured NBBO. Options, news, regime and sector witnesses were not added after seeing outcomes.
- A favorable tiny cell does not override the preregistered N/promotion floor. A null/negative R1-A result closes only this exact construction, not the low-timeframe opportunity search space.
- Future research must retain failed candidates, no-control rows, ambiguous same-bar hits and censored paths; no backpainted extrema.

## 7. Product consequence

Nothing from R1-A may become a live rank, alert, sizing input or options expression. Terminal may eventually display these observations only after the existing Radar/Setup Species/Evaluation owners admit an appropriate display-tier species and the current data/freshness path is qualified. The useful product target remains Forming/Armed versus Triggered/Confirmed opportunities with explicit invalidation, remaining opportunity, contradictory evidence and no-edge states.
