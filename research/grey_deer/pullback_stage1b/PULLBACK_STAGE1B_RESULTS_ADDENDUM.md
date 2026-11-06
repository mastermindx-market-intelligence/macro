# Pullback stage-1b results addendum

## Provenance

- results file: `PULLBACK_STAGE1B_RESULTS.json`
- results sha256: `0cd9b0ae0d426eda7be3ef07162cb2c279bfcd56f50f2b3694dfab715bef606d`
- results_ref: `15ed8fca3ee76329e8cf30332ef8b79c15ea0402`
- schema: `grey_deer_pullback_stage1b/v1`

Derived only from the stored results JSON. No claim was re-run and no verdict changed.

Stored run fields copied from the results JSON:

- status: OK
- commit_sha: df7085bb351e4c6e49415191fb873259769c1780
- run_commit: df7085bb351e4c6e49415191fb873259769c1780
- script_blob_sha: f615c089ba5c396c0578d94d5f4707de1717116b
- test_blob_sha: 3bed87e6da07675dcc0ec9492996a9bdfd2cd0fc
- adjust_module_blob_sha: 60833bfae7fce1e9b2efaeea17c271fc9f91d119
- manifest_path: research/grey_deer/PULLBACK_SOURCE_RIGHTS_QUALIFICATION_V1_1_2026-10-12.md
- manifest_version: 1.1.0
- manifest_blob_sha: c52d93e98f4e4a776a7cf38fce46bcf4a84c52d7
- prereg_path: research/grey_deer/PULLBACK_PREREGISTRATION_V1_1_2026-10-12.md
- prereg_blob_sha: 53837859164ab1d33785101dc0b464272acd5704
- dividend_basis: unadjusted
- trial_family: grey_deer_pullback_v11
- trial_budget: 66
- seed_root: 221012
- n_draws: 10000
- trial_counting:
  - inc: removed from v1's 23
  - note: frozen with prereg v1.1; registered in data/trial_ledger.jsonl before outcomes
  - per_horizon: 22
  - total: 66
- bootstrap:
  - axis: date
  - block_length_rule: stage-1 block_length(h, variant)
  - n_draws: 10000
  - seed_root: 221012
- dividend_disclosure: Pinned splits are adjusted per D14 (table in grey_deer_panel_adjust.PINNED_SPLITS). Dividends are unadjusted. The common axis is the intersection per D15 with pinned exclusion 2026-08-18.
- blocked: (empty)

## Stored claim verdicts

Claim verdicts below are copied from the stored JSON.

Stored claim rows: 12.

| id | h | pop | claim | stored_statistic | stored_point | stored_lb | stored_threshold | flags | stored_verdict |
|---|---|---|---|---|---|---|---|---|---|
| h5/P-all/binary | 5 | P-all | binary | delta_v@alpha=b_h | 0.12423543875826044 | -0.486393193049741 | 0.0 | FRAGILE | rejected candidate |
| h5/P-all/quantile | 5 | P-all | quantile | pinball_skill | 0.000347905278569427 | -0.013134759851198908 | 0.0 | FRAGILE | rejected candidate |
| h10/P-all/binary | 10 | P-all | binary | delta_v@alpha=b_h | 0.11432186254161558 | -0.3615229585304165 | 0.0 | UNDERPOWERED_DISCLOSED | underpowered/blocked claim |
| h10/P-all/quantile | 10 | P-all | quantile | pinball_skill | -0.011483001403053139 | -0.030434265836015977 | 0.0 | FRAGILE, UNDERPOWERED_DISCLOSED | underpowered/blocked claim |
| h21/P-all/binary | 21 | P-all | binary | delta_v@alpha=b_h | 0.05057178116001645 | -0.3789082075071964 | 0.0 | FRAGILE, UNDERPOWERED_DISCLOSED | underpowered/blocked claim |
| h21/P-all/quantile | 21 | P-all | quantile | pinball_skill | -0.028383042919036816 | -0.06568245703241668 | 0.0 | FRAGILE, UNDERPOWERED_DISCLOSED | underpowered/blocked claim |
| h5/P-active/binary | 5 | P-active | binary | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |
| h5/P-active/quantile | 5 | P-active | quantile | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |
| h10/P-active/binary | 10 | P-active | binary | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |
| h10/P-active/quantile | 10 | P-active | quantile | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |
| h21/P-active/binary | 21 | P-active | binary | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |
| h21/P-active/quantile | 21 | P-active | quantile | null | null | null | null | OBSERVER_NOT_ON_MAIN | underpowered/blocked claim |

P-active rows store null `statistic`, `point`, `lb` and `threshold`.

| id | stored_verdict | blocked_type | detail | flags |
|---|---|---|---|---|
| h5/P-active/binary | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |
| h5/P-active/quantile | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |
| h10/P-active/binary | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |
| h10/P-active/quantile | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |
| h21/P-active/binary | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |
| h21/P-active/quantile | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN | P-active stays blocked until close_path.v1 (draft PR #8188) is on main; the claim keeps its 0.05/12 share of the family level | OBSERVER_NOT_ON_MAIN |

## F1. Stored headline label

For each P-all claim whose stored statistic is `delta_v@alpha=b_h`, the stored point and lb are labelled V(M3)@alpha=b_h. The frozen stage-1 helper copies `conditions[1]` into those fields. That condition's statistic is `v_m3@alpha=b`. The delta-V point and lb come from the condition whose statistic name begins with `delta_v`.

Verdicts are computed separately and are unaffected.

| id | stored_statistic | honest_label_of_stored_point_and_lb | stored_point | stored_lb | delta_v_statistic_name | delta_v_point | delta_v_lb | stored_verdict |
|---|---|---|---|---|---|---|---|---|
| h5/P-all/binary | delta_v@alpha=b_h | V(M3)@alpha=b_h | 0.12423543875826044 | -0.486393193049741 | delta_v@alpha=b (V(M3) - max(V(B1-20,B1-63,B2-21,B2-63))) | -0.010839608626607197 | -0.1369666950784323 | rejected candidate |
| h10/P-all/binary | delta_v@alpha=b_h | V(M3)@alpha=b_h | 0.11432186254161558 | -0.3615229585304165 | delta_v@alpha=b (V(M3) - max(V(B1-20,B1-63,B2-21,B2-63))) | 0.007996299991208697 | -0.06379900221255105 | underpowered/blocked claim |
| h21/P-all/binary | delta_v@alpha=b_h | V(M3)@alpha=b_h | 0.05057178116001645 | -0.3789082075071964 | delta_v@alpha=b (V(M3) - max(V(B1-20,B1-63,B2-21,B2-63))) | 0.0038543809132044124 | -0.05948822769357432 | underpowered/blocked claim |

P-all claims whose stored statistic is not `delta_v@alpha=b_h` are not given that label. No delta-V number is invented for them.

| id | stored_statistic | stored_point | stored_lb | stored_verdict |
|---|---|---|---|---|
| h5/P-all/quantile | pinball_skill | 0.000347905278569427 | -0.013134759851198908 | rejected candidate |
| h10/P-all/quantile | pinball_skill | -0.011483001403053139 | -0.030434265836015977 | underpowered/blocked claim |
| h21/P-all/quantile | pinball_skill | -0.028383042919036816 | -0.06568245703241668 | underpowered/blocked claim |

## F2. Abstention tables present; eligibility census absent

The D12 eligibility/maturity census is absent from the stored results JSON. It cannot be recovered without re-running on real data. This is a disclosed deviation. No census count is estimated here.

Abstention tables that do exist are `claims[].conditions[].point.by_type` on M3-ALL (binary) and Q3-ALL (quantile).

### h5/P-all/binary (M3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 0.0
- gap_pp: 0.0
- issued: 14000
- abstained: 0

stored by_type is empty.

### h5/P-all/quantile (Q3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 0.0
- gap_pp: 0.0
- issued: 14000
- abstained: 0

stored by_type is empty.

### h10/P-all/binary (M3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 0.0
- gap_pp: 0.0
- issued: 13930
- abstained: 0

stored by_type is empty.

### h10/P-all/quantile (Q3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 7.178750897343863e-05
- gap_pp: -0.007835762419683435
- issued: 13929
- abstained: 1

| abstention_type | count |
|---|---|
| QUANTILE_CROSSING | 1 |

### h21/P-all/binary (M3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 0.0
- gap_pp: 0.0
- issued: 13776
- abstained: 0

stored by_type is empty.

### h21/P-all/quantile (Q3-ALL)

- statistic: abstention (rate <= 5% of evaluation origins; event-vs-non-event gap <= 5pp)
- rate: 0.0
- gap_pp: 0.0
- issued: 13776
- abstained: 0

stored by_type is empty.

## F3. Per-ticker subframe identity

Each row is one panel ticker. `subframe_sha256` is the stored results value. `rows`, `first_date` and `last_date` are `IDENTITY_PINS` imported from `scripts/research/grey_deer_pullback_stage1b.py` and are not copied into this module. `hash_equals_pin` is `true` when the stored hash equals the imported pin hash. This addendum does not re-read a price subframe.

| ticker | subframe_sha256 | rows | first_date | last_date | hash_equals_pin |
|---|---|---|---|---|---|
| QQQ | d6bd7575c5db3f0fb5d63e6baa2892a5a9d3610a8885562f8ead677a4444373f | 1320 | 2021-07-06 | 2026-10-07 | true |
| IWM | ca2df002ee03ed68c19cd77e73b702c057be11f92435936b1f7d4fd57e218b8b | 1320 | 2021-07-06 | 2026-10-07 | true |
| DIA | f11d142d015fca21c404e4a96524791d17ecaee4eb08f489f620ac47a753d618 | 1321 | 2021-07-06 | 2026-10-07 | true |
| XLB | 0863d459e79a40b0943b2ced0aeea42801e81d9a989b8df07823ee6445055628 | 1321 | 2021-07-06 | 2026-10-07 | true |
| XLC | 121c9b52c6ef4231540b73ad15362cf5927e7e5ae3c8df073ae231cbd158374d | 1321 | 2021-07-06 | 2026-10-07 | true |
| XLE | ebf4be8c9f7f53b2472b1a032d5f105f7ed5ce7f439411f468b6435939176ba3 | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLF | da3a5aa47a06f469dd6a99288e7be423ff63e9a8b9dc10d6832dc7a4af5b1491 | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLI | d153ab22f333d536bdf7c8ef84c981b9c5614e8f62969687d765f043e35e596c | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLK | 7dc854d1e340f1619340c1c26c9be4cc17fd0c925a0bbe036c74c058d53d0e63 | 1321 | 2021-07-06 | 2026-10-07 | true |
| XLP | a480545513732922a2be49c2cf807f7500baf923beb909cdf8d59eae70ef885b | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLRE | c578f88c142f67a237f45a324097fc912c6994abd2aaa355080b5e94ca41fcae | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLU | 238dbbd6d68fa71ae074020ad83a2bbc4ffcd0a45cc087ca1982d56fb4a5b2f1 | 1320 | 2021-07-06 | 2026-10-07 | true |
| XLV | 64f9d9b448b7e93b9e11137db11d9860c1c61d4682b0c685f43a6ff73db5d251 | 1321 | 2021-07-06 | 2026-10-07 | true |
| XLY | 870fa4c0b19e31d5ef33b2d0702b9e9815b89285f3e3eb925434afb36b758ed5 | 1320 | 2021-07-06 | 2026-10-07 | true |

## F4. Fold block table

Stored `fold_block_table` rows: 24.

Per-year, per-test-block and rv20-tercile breakdowns are absent from the stored JSON.
Block-level performance, including the latest block 8 (2026-04-13 onward), is not stored and is unreported. This addendum does not estimate it.

| h | fold | start_index | end_index | start_date | end_date | after_excluded_session |
|---|---|---|---|---|---|---|
| 5 | 1 | 315 | 440 | 2022-10-04 | 2023-04-04 | false |
| 5 | 2 | 441 | 566 | 2023-04-05 | 2023-10-04 | false |
| 5 | 3 | 567 | 692 | 2023-10-05 | 2024-04-05 | false |
| 5 | 4 | 693 | 818 | 2024-04-08 | 2024-10-04 | false |
| 5 | 5 | 819 | 944 | 2024-10-07 | 2025-04-08 | false |
| 5 | 6 | 945 | 1070 | 2025-04-09 | 2025-10-08 | false |
| 5 | 7 | 1071 | 1196 | 2025-10-09 | 2026-04-10 | false |
| 5 | 8 | 1197 | 1314 | 2026-04-13 | 2026-09-30 | false |
| 10 | 1 | 315 | 440 | 2022-10-04 | 2023-04-04 | false |
| 10 | 2 | 441 | 566 | 2023-04-05 | 2023-10-04 | false |
| 10 | 3 | 567 | 692 | 2023-10-05 | 2024-04-05 | false |
| 10 | 4 | 693 | 818 | 2024-04-08 | 2024-10-04 | false |
| 10 | 5 | 819 | 944 | 2024-10-07 | 2025-04-08 | false |
| 10 | 6 | 945 | 1070 | 2025-04-09 | 2025-10-08 | false |
| 10 | 7 | 1071 | 1196 | 2025-10-09 | 2026-04-10 | false |
| 10 | 8 | 1197 | 1309 | 2026-04-13 | 2026-09-23 | false |
| 21 | 1 | 315 | 440 | 2022-10-04 | 2023-04-04 | false |
| 21 | 2 | 441 | 566 | 2023-04-05 | 2023-10-04 | false |
| 21 | 3 | 567 | 692 | 2023-10-05 | 2024-04-05 | false |
| 21 | 4 | 693 | 818 | 2024-04-08 | 2024-10-04 | false |
| 21 | 5 | 819 | 944 | 2024-10-07 | 2025-04-08 | false |
| 21 | 6 | 945 | 1070 | 2025-04-09 | 2025-10-08 | false |
| 21 | 7 | 1071 | 1196 | 2025-10-09 | 2026-04-10 | false |
| 21 | 8 | 1197 | 1298 | 2026-04-13 | 2026-09-08 | false |

## F5. Negative control

Stored `negative_control` for every horizon and both families (`m3-ALL-shifted`, `q3-ALL-shifted`).

### h5

- expectation: at or below 0; neither a claim nor a gate
- shift: numpy.roll(y, len(y) // 2) per pooled training block (deterministic, no seed)

#### m3-ALL-shifted

- bss_vs_b0: 0.019555878451056885
- n_scored: 14000
- v_at_b_h: -0.10077352594641652

#### q3-ALL-shifted

- n_scored: 14000
- pinball_skill: -0.011335770589174121

### h10

- expectation: at or below 0; neither a claim nor a gate
- shift: numpy.roll(y, len(y) // 2) per pooled training block (deterministic, no seed)

#### m3-ALL-shifted

- bss_vs_b0: 0.014092424779949764
- n_scored: 13930
- v_at_b_h: 0.014452203760401513

#### q3-ALL-shifted

- n_scored: 13929
- pinball_skill: -0.020975212762188056

### h21

- expectation: at or below 0; neither a claim nor a gate
- shift: numpy.roll(y, len(y) // 2) per pooled training block (deterministic, no seed)

#### m3-ALL-shifted

- bss_vs_b0: 0.014426570080589785
- n_scored: 13776
- v_at_b_h: 0.005302344714109266

#### q3-ALL-shifted

- n_scored: 13776
- pinball_skill: -0.03222201617864018

## F6. Leave-one-episode-out

`loeo` stores `min`, `fragile` and `n_episodes` only. Episode windows are the stored `episodes` windows for that horizon and family. The episode whose deletion moves the estimate most cannot be named from the stored data.

### h5/P-all/binary

- fragile: true
- n_episodes: 11
- min.bss: -0.003845126909324925
- min.delta_v: -0.020502806931901527
- min.v_m3@b: -0.015758481815963
- episode_windows (`episodes.h5.binary.episode_windows`): 294..371; 372..432; 434..463; 531..592; 594..638; 672..702; 736..799; 822..972; 997..1023; 1073..1120; 1125..1310
- `honest_n.episode_windows` matches the episode windows above.

### h5/P-all/quantile

- fragile: true
- n_episodes: 11
- min.pinball_skill: -0.003097104953781793
- episode_windows (`episodes.h5.quantile.episode_windows`): 294..371; 372..432; 434..463; 531..592; 594..638; 672..702; 736..799; 822..972; 997..1023; 1073..1120; 1125..1310
- `honest_n.episode_windows` matches the episode windows above.

### h10/P-all/binary

- fragile: false
- n_episodes: 4
- min.bss: 0.004220381827114816
- min.delta_v: 0.0016718195350967913
- min.v_m3@b: 0.02305959058440004
- episode_windows (`episodes.h10.binary.episode_windows`): 294..645; 666..805; 808..977; 994..1315
- `honest_n.episode_windows` matches the episode windows above.

### h10/P-all/quantile

- fragile: true
- n_episodes: 4
- min.pinball_skill: -0.01528662938738301
- episode_windows (`episodes.h10.quantile.episode_windows`): 294..645; 666..805; 808..977; 994..1315
- `honest_n.episode_windows` matches the episode windows above.

### h21/P-all/binary

- fragile: true
- n_episodes: 1
- min: stored object is empty.
- episode_windows (`episodes.h21.binary.episode_windows`): 294..1319
- `honest_n.episode_windows` matches the episode windows above.

### h21/P-all/quantile

- fragile: true
- n_episodes: 1
- min: stored object is empty.
- episode_windows (`episodes.h21.quantile.episode_windows`): 294..1319
- `honest_n.episode_windows` matches the episode windows above.

## F7. Comparison fields present

Descriptive baseline-vs-baseline intervals (B1/B2 vs B0, Q1 vs Q0) are not in the payload. `comparison.*.binary.sensitivity` metrics are not in the payload. Both are disclosed deviations and are not estimated. What is stored (`N_common`, and where present `config`, `n`, `note`) is below.

### h5 binary

- N_common: 14000
- sensitivity.config: M3-ALL-C0.1
- sensitivity.n: 14000
- sensitivity.note: sensitivity row only, never a gate

### h5 quantile

- N_common: 14000
- sensitivity: absent

### h10 binary

- N_common: 13930
- sensitivity.config: M3-ALL-C0.1
- sensitivity.n: 13930
- sensitivity.note: sensitivity row only, never a gate

### h10 quantile

- N_common: 13929
- sensitivity: absent

### h21 binary

- N_common: 13776
- sensitivity.config: M3-ALL-C0.1
- sensitivity.n: 13776
- sensitivity.note: sensitivity row only, never a gate

### h21 quantile

- N_common: 13776
- sensitivity: absent

## Bootstrap cells

Stored `bootstrap_cells` for every horizon and family, primary and `sensitivity_L_h`: `n_draws`, `L`, `N_dates`, and `headline`.

### h5 binary primary

- n_draws: 10000
- L: 21
- N_dates: 1000
- headline:
  - headline.bss_m3.interval_90: [-0.06158517092252356, 0.06325907185118601]
  - headline.bss_m3.lb: -0.11593289707627141
  - headline.citl_m3.interval_90: [0.016051972967265907, 0.03714386699868257]
  - headline.delta_v.interval_90: [-0.07527801201469482, 0.010166650681680411]
  - headline.delta_v.lb: -0.1369666950784323
  - headline.v_m3.0.5b.interval_90: [0.05713155166344352, 0.16464779522276257]
  - headline.v_m3.0.5b.lb: -0.023340798679070185
  - headline.v_m3.2b.interval_90: [-0.2960644919788168, 0.08598986311439692]
  - headline.v_m3.2b.lb: -0.4898336134134427
  - headline.v_m3.b.interval_90: [-0.22230530994027414, 0.26337568785592236]
  - headline.v_m3.b.lb: -0.486393193049741
  - headline.wace_m3.interval_90: [0.015167104419967516, 0.0361473695714697]
- seed: [221012, 5, 0, 0, 0]

### h5 binary sensitivity_L_h

- n_draws: 10000
- L: 5
- N_dates: 1000
- headline:
  - headline.bss_m3.interval_90: [-0.037937028471277945, 0.038343131721334384]
  - headline.bss_m3.lb: -0.0678555683624747
  - headline.citl_m3.interval_90: [0.0165691668009955, 0.0356019668188635]
  - headline.delta_v.interval_90: [-0.06018635409462177, 0.009309261182610459]
  - headline.delta_v.lb: -0.10997436273235137
  - headline.v_m3.0.5b.interval_90: [0.06994528638966409, 0.15395751146563869]
  - headline.v_m3.0.5b.lb: 0.0289889115184431
  - headline.v_m3.2b.interval_90: [-0.2809145554268012, 0.09028487593359484]
  - headline.v_m3.2b.lb: -0.45536212927014147
  - headline.v_m3.b.interval_90: [-0.15667204103116025, 0.26495690417172785]
  - headline.v_m3.b.lb: -0.38042936064494404
  - headline.wace_m3.interval_90: [0.01534622715226664, 0.03430073854856087]
- seed: [221012, 5, 0, 0, 1]

### h5 quantile primary

- n_draws: 10000
- L: 21
- N_dates: 1000
- headline:
  - headline.coverage.0.5.interval_90: [0.5072107142857143, 0.5642857142857143]
  - headline.coverage.0.8.interval_90: [0.8182107142857142, 0.8642142857142857]
  - headline.coverage.0.9.interval_90: [0.9155714285714286, 0.9453571428571429]
  - headline.skill.interval_90: [-0.00802987271582999, 0.008927442149315004]
  - headline.skill.lb: -0.013134759851198908
  - headline.skill_q1_vs_q0.interval_90: [0.011365772944588643, 0.046753825816312454]
- seed: [221012, 5, 0, 1, 0]

### h5 quantile sensitivity_L_h

- n_draws: 10000
- L: 5
- N_dates: 1000
- headline:
  - headline.coverage.0.5.interval_90: [0.5100714285714286, 0.5613607142857142]
  - headline.coverage.0.8.interval_90: [0.8212107142857142, 0.8615714285714285]
  - headline.coverage.0.9.interval_90: [0.917, 0.9436428571428571]
  - headline.skill.interval_90: [-0.007725916678226285, 0.008323005741103142]
  - headline.skill.lb: -0.012609774313381793
  - headline.skill_q1_vs_q0.interval_90: [0.015273582825564475, 0.04246754704120602]
- seed: [221012, 5, 0, 1, 1]

### h10 binary primary

- n_draws: 10000
- L: 21
- N_dates: 995
- headline:
  - headline.bss_m3.interval_90: [-0.02956410938243938, 0.07035841713233926]
  - headline.bss_m3.lb: -0.06566420555093111
  - headline.citl_m3.interval_90: [0.03994749798887604, 0.08963838958189889]
  - headline.delta_v.interval_90: [-0.03513786751467251, 0.022992748891746045]
  - headline.delta_v.lb: -0.06379900221255105
  - headline.v_m3.0.5b.interval_90: [-0.0029926108343480795, 0.029599700092335857]
  - headline.v_m3.0.5b.lb: -0.013932400370212062
  - headline.v_m3.2b.interval_90: [-0.4555058424048737, -0.047696956058885825]
  - headline.v_m3.2b.lb: -0.6631315412748332
  - headline.v_m3.b.interval_90: [-0.14693676474533354, 0.14859423109196032]
  - headline.v_m3.b.lb: -0.3615229585304165
  - headline.wace_m3.interval_90: [0.04100719053436147, 0.0893992809926558]
- seed: [221012, 10, 0, 0, 0]

### h10 binary sensitivity_L_h

- n_draws: 10000
- L: 10
- N_dates: 995
- headline:
  - headline.bss_m3.interval_90: [-0.021001395403628928, 0.05872782267381431]
  - headline.bss_m3.lb: -0.049252184352499354
  - headline.citl_m3.interval_90: [0.042312053894491455, 0.08693673164737442]
  - headline.delta_v.interval_90: [-0.030499972801397587, 0.02301758139151334]
  - headline.delta_v.lb: -0.05308485663643386
  - headline.v_m3.0.5b.interval_90: [-0.0018049946149767575, 0.02846256632765812]
  - headline.v_m3.0.5b.lb: -0.012512154835731962
  - headline.v_m3.2b.interval_90: [-0.42910062314116415, -0.0529772656955038]
  - headline.v_m3.2b.lb: -0.5909861223701719
  - headline.v_m3.b.interval_90: [-0.10501733584746155, 0.1448502469881503]
  - headline.v_m3.b.lb: -0.30223497781220704
  - headline.wace_m3.interval_90: [0.04250706992138214, 0.08669486719873018]
- seed: [221012, 10, 0, 0, 1]

### h10 quantile primary

- n_draws: 10000
- L: 21
- N_dates: 995
- headline:
  - headline.coverage.0.5.interval_90: [0.5242283157292857, 0.6020839990131472]
  - headline.coverage.0.8.interval_90: [0.8291328491679041, 0.8894496356269752]
  - headline.coverage.0.9.interval_90: [0.9164390396028015, 0.957286432160804]
  - headline.skill.interval_90: [-0.023256929754596402, -7.452439446747314e-06]
  - headline.skill.lb: -0.030434265836015977
  - headline.skill_q1_vs_q0.interval_90: [0.013913662596257021, 0.05975135072463782]
- seed: [221012, 10, 0, 1, 0]

### h10 quantile sensitivity_L_h

- n_draws: 10000
- L: 10
- N_dates: 995
- headline:
  - headline.coverage.0.5.interval_90: [0.5272829747325286, 0.599569989831821]
  - headline.coverage.0.8.interval_90: [0.8323761665470208, 0.8872218234027279]
  - headline.coverage.0.9.interval_90: [0.9185929648241206, 0.9557100612518697]
  - headline.skill.interval_90: [-0.022543182579287568, -0.0008991363941039291]
  - headline.skill.lb: -0.02925644419819503
  - headline.skill_q1_vs_q0.interval_90: [0.018545310909914903, 0.05545119241135021]
- seed: [221012, 10, 0, 1, 1]

### h21 binary primary

- n_draws: 10000
- L: 42
- N_dates: 984
- headline:
  - headline.bss_m3.interval_90: [-0.02226574492643478, 0.0699036863676361]
  - headline.bss_m3.lb: -0.054341982276647854
  - headline.citl_m3.interval_90: [0.05244983716886797, 0.15625966388502224]
  - headline.delta_v.interval_90: [-0.03416712336542772, 0.0237920131125193]
  - headline.delta_v.lb: -0.05948822769357432
  - headline.v_m3.0.5b.interval_90: [0.0002668504995153842, 0.004781839458676171]
  - headline.v_m3.0.5b.lb: 0.0
  - headline.v_m3.2b.interval_90: [-0.46171981758288205, -0.09576455608570904]
  - headline.v_m3.2b.lb: -0.6470589802400488
  - headline.v_m3.b.interval_90: [-0.12689686725422225, 0.0808259451423005]
  - headline.v_m3.b.lb: -0.3789082075071964
  - headline.wace_m3.interval_90: [0.06161034002016735, 0.15659528776665857]
- seed: [221012, 21, 0, 0, 0]

### h21 binary sensitivity_L_h

- n_draws: 10000
- L: 21
- N_dates: 984
- headline:
  - headline.bss_m3.interval_90: [-0.018248042606675306, 0.06379258221503165]
  - headline.bss_m3.lb: -0.04576322237949999
  - headline.citl_m3.interval_90: [0.055325108101349316, 0.1525764758228983]
  - headline.delta_v.interval_90: [-0.03286274941754102, 0.023746761094247254]
  - headline.delta_v.lb: -0.05652731120995521
  - headline.v_m3.0.5b.interval_90: [0.00034801827468377184, 0.004641396194583686]
  - headline.v_m3.0.5b.lb: 0.0
  - headline.v_m3.2b.interval_90: [-0.4798791010632207, -0.08284348169961335]
  - headline.v_m3.2b.lb: -0.6577121272911901
  - headline.v_m3.b.interval_90: [-0.09086328962046492, 0.08429002551518448]
  - headline.v_m3.b.lb: -0.3161616042790646
  - headline.wace_m3.interval_90: [0.06355841785600046, 0.1529708984043139]
- seed: [221012, 21, 0, 0, 1]

### h21 quantile primary

- n_draws: 10000
- L: 42
- N_dates: 984
- headline:
  - headline.coverage.0.5.interval_90: [0.5491434378629501, 0.665650406504065]
  - headline.coverage.0.8.interval_90: [0.8403709349593496, 0.9247277874564459]
  - headline.coverage.0.9.interval_90: [0.9083914053426249, 0.9755371660859465]
  - headline.skill.interval_90: [-0.05154132772390883, -0.00663808730553997]
  - headline.skill.lb: -0.06568245703241668
  - headline.skill_q1_vs_q0.interval_90: [0.01770659242591059, 0.07731594054082119]
- seed: [221012, 21, 0, 1, 0]

### h21 quantile sensitivity_L_h

- n_draws: 10000
- L: 21
- N_dates: 984
- headline:
  - headline.coverage.0.5.interval_90: [0.5528455284552846, 0.6604965156794426]
  - headline.coverage.0.8.interval_90: [0.8456010452961672, 0.9217479674796748]
  - headline.coverage.0.9.interval_90: [0.914924506387921, 0.9728513356562137]
  - headline.skill.interval_90: [-0.04911747006090748, -0.008779835892187948]
  - headline.skill.lb: -0.06372619771622563
  - headline.skill_q1_vs_q0.interval_90: [0.02251627464551458, 0.0724012457395471]
- seed: [221012, 21, 0, 1, 1]

## Honest-N and frozen base rates

Frozen b_h values are `BASE_RATES` imported from `scripts/research/grey_deer_pullback_stage1.py`. They are not retyped.

- h=5: `0.036`
- h=10: `0.082`
- h=21: `0.176`

`derived_row_base_rate` equals `ticker_events / origins`. `derived_rate_over_b_h` equals that rate divided by frozen b_h. Both columns are derived in this addendum. Every other column is stored.

Event-date index lists are summarised by count, first stored entry and last stored entry. They are not dumped.

| id | origins | ticker_events | derived_row_base_rate | frozen_b_h | derived_rate_over_b_h | events | clusters | episodes | event_months | power_floor_met | power_min_episodes | power_min_months |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h5/P-all/binary | 14000 | 405 | 0.02892857142857143 | 0.036 | 0.8035714285714286 | 175 | 31 | 11 | 35 | true | 10 | 10 |
| h5/P-all/quantile | 14000 | 405 | 0.02892857142857143 | 0.036 | 0.8035714285714286 | 175 | 31 | 11 | 35 | true | 10 | 10 |
| h10/P-all/binary | 13930 | 1168 | 0.08384781048097631 | 0.082 | 1.0225342741582477 | 395 | 20 | 4 | 44 | false | 10 | 10 |
| h10/P-all/quantile | 13929 | 1168 | 0.08385383013855983 | 0.082 | 1.0226076846165832 | 395 | 20 | 4 | 44 | false | 10 | 10 |
| h21/P-all/binary | 13776 | 2726 | 0.19788037166085948 | 0.176 | 1.1243202935276106 | 625 | 5 | 1 | 46 | false | 10 | 10 |
| h21/P-all/quantile | 13776 | 2726 | 0.19788037166085948 | 0.176 | 1.1243202935276106 | 625 | 5 | 1 | 46 | false | 10 | 10 |

| id | event_dates_count | event_dates_first | event_dates_last | event_month_list_count | event_month_first | event_month_last |
|---|---|---|---|---|---|---|
| h5/P-all/binary | 175 | 315 | 1305 | 35 | 2022-10 | 2026-09 |
| h5/P-all/quantile | 175 | 315 | 1305 | 35 | 2022-10 | 2026-09 |
| h10/P-all/binary | 395 | 315 | 1305 | 44 | 2022-10 | 2026-09 |
| h10/P-all/quantile | 395 | 315 | 1305 | 44 | 2022-10 | 2026-09 |
| h21/P-all/binary | 625 | 315 | 1298 | 46 | 2022-10 | 2026-09 |
| h21/P-all/quantile | 625 | 315 | 1298 | 46 | 2022-10 | 2026-09 |

Stored `per_ticker_episodes`:

| id | ticker | per_ticker_episodes |
|---|---|---|
| h5/P-all/binary | QQQ | 10 |
| h5/P-all/binary | IWM | 8 |
| h5/P-all/binary | DIA | 2 |
| h5/P-all/binary | XLB | 10 |
| h5/P-all/binary | XLC | 6 |
| h5/P-all/binary | XLE | 11 |
| h5/P-all/binary | XLF | 5 |
| h5/P-all/binary | XLI | 4 |
| h5/P-all/binary | XLK | 10 |
| h5/P-all/binary | XLP | 2 |
| h5/P-all/binary | XLRE | 8 |
| h5/P-all/binary | XLU | 7 |
| h5/P-all/binary | XLV | 2 |
| h5/P-all/binary | XLY | 8 |
| h5/P-all/quantile | QQQ | 10 |
| h5/P-all/quantile | IWM | 8 |
| h5/P-all/quantile | DIA | 2 |
| h5/P-all/quantile | XLB | 10 |
| h5/P-all/quantile | XLC | 6 |
| h5/P-all/quantile | XLE | 11 |
| h5/P-all/quantile | XLF | 5 |
| h5/P-all/quantile | XLI | 4 |
| h5/P-all/quantile | XLK | 10 |
| h5/P-all/quantile | XLP | 2 |
| h5/P-all/quantile | XLRE | 8 |
| h5/P-all/quantile | XLU | 7 |
| h5/P-all/quantile | XLV | 2 |
| h5/P-all/quantile | XLY | 8 |
| h10/P-all/binary | QQQ | 10 |
| h10/P-all/binary | IWM | 12 |
| h10/P-all/binary | DIA | 5 |
| h10/P-all/binary | XLB | 13 |
| h10/P-all/binary | XLC | 9 |
| h10/P-all/binary | XLE | 12 |
| h10/P-all/binary | XLF | 9 |
| h10/P-all/binary | XLI | 7 |
| h10/P-all/binary | XLK | 7 |
| h10/P-all/binary | XLP | 5 |
| h10/P-all/binary | XLRE | 10 |
| h10/P-all/binary | XLU | 12 |
| h10/P-all/binary | XLV | 7 |
| h10/P-all/binary | XLY | 8 |
| h10/P-all/quantile | QQQ | 10 |
| h10/P-all/quantile | IWM | 12 |
| h10/P-all/quantile | DIA | 5 |
| h10/P-all/quantile | XLB | 13 |
| h10/P-all/quantile | XLC | 9 |
| h10/P-all/quantile | XLE | 12 |
| h10/P-all/quantile | XLF | 9 |
| h10/P-all/quantile | XLI | 7 |
| h10/P-all/quantile | XLK | 7 |
| h10/P-all/quantile | XLP | 5 |
| h10/P-all/quantile | XLRE | 10 |
| h10/P-all/quantile | XLU | 12 |
| h10/P-all/quantile | XLV | 7 |
| h10/P-all/quantile | XLY | 8 |
| h21/P-all/binary | QQQ | 7 |
| h21/P-all/binary | IWM | 9 |
| h21/P-all/binary | DIA | 9 |
| h21/P-all/binary | XLB | 8 |
| h21/P-all/binary | XLC | 8 |
| h21/P-all/binary | XLE | 7 |
| h21/P-all/binary | XLF | 8 |
| h21/P-all/binary | XLI | 8 |
| h21/P-all/binary | XLK | 7 |
| h21/P-all/binary | XLP | 7 |
| h21/P-all/binary | XLRE | 9 |
| h21/P-all/binary | XLU | 10 |
| h21/P-all/binary | XLV | 9 |
| h21/P-all/binary | XLY | 8 |
| h21/P-all/quantile | QQQ | 7 |
| h21/P-all/quantile | IWM | 9 |
| h21/P-all/quantile | DIA | 9 |
| h21/P-all/quantile | XLB | 8 |
| h21/P-all/quantile | XLC | 8 |
| h21/P-all/quantile | XLE | 7 |
| h21/P-all/quantile | XLF | 8 |
| h21/P-all/quantile | XLI | 8 |
| h21/P-all/quantile | XLK | 7 |
| h21/P-all/quantile | XLP | 7 |
| h21/P-all/quantile | XLRE | 9 |
| h21/P-all/quantile | XLU | 10 |
| h21/P-all/quantile | XLV | 9 |
| h21/P-all/quantile | XLY | 8 |

## Stored panel and INC

Stored `panel`:

- first_date: 2021-07-06
- last_date: 2026-10-07
- n_dates: 1320
- spy_excluded: true
- tickers: [QQQ, IWM, DIA, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY]

Stored `inc`:

- evidence_class: NOT_APPLICABLE
- gate: false
- id: INC
- reason: the incumbent is SPY-only and SPY is excluded from the panel
- status: NOT_APPLICABLE
