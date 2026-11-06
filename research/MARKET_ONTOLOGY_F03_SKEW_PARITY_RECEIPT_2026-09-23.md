# Options skew methodology-parity receipt

This receipt compares each legacy polygon_gex row with a fresh ThetaData recompute of the same date and underlying. Both sides use the same skew formula. This run does not change the formula, and it does not edit the engine.

- Run (UTC): 2026-09-23 02:02:03Z
- Ledger: `/Users/chriswong/skew-ops-wt/data/options_skew/snapshots.parquet`
- ThetaData store: `/Users/chriswong/theta-ops-wt/data/thetadata_eod`
- Legacy keys in this run: **12375** (the full legacy population).
- A weekend date is Saturday or Sunday. A root is in the store when eod/<ROOT> exists. A date is in the store when that day appears in eod/<ROOT>/<YEAR>.parquet. Nothing here calls the network.

## Classification

Every legacy key lands in exactly one class. The six classes add up to the legacy key count for this run.

| class | N | share of legacy keys |
| --- | --- | --- |
| weekend_date | 2875 | 23.2 percent |
| root_not_in_store | 124 | 1.0 percent |
| date_not_in_store_for_root | 5411 | 43.7 percent |
| no_usable_tenor | 0 | 0.0 percent |
| other | 0 | 0.0 percent |
| compared | 3965 | 32.0 percent |
| total | 12375 | 100.0 percent |

Recompute errors while pricing a stored chain: 0. An error is counted in other, not dropped.

## Compared keys

Both paths priced **3965** keys. Sign agreement (same non-zero sign, divided by compared keys) is **0.603279**. The absolute skew gap has p50 0.037900, p90 0.167000, and max 3.952900. The percentile is the nearest rank, the same rule as the overlap audit.

Match means both skews are non-zero and share a sign. Flip means both are non-zero and the signs disagree. Zero means at least one skew is exactly zero. Match, flip, and zero add up to the compared count.

| bucket | N |
| --- | --- |
| match | 2392 |
| flip | 1563 |
| zero | 10 |
| total | 3965 |

## Decomposition

The skew gap equals the put-IV gap minus the call-IV gap. Across compared keys, the put IV contributions sum to -27.197700 and the call IV contributions sum to 20.869200. Those two sums add to -6.328500, which is the gap implied by the two IVs. The stored skews sum to a gap of -6.329700. The largest absolute leftover on one key, between that identity and the stored skew, is 0.000200.

Each compared key's absolute gap is assigned to one explanation. A tenor mismatch (more than 5 days) comes first. Otherwise a spot mismatch (more than 2 percent) comes next. Otherwise the gap is assigned to the put leg when the put IV moved at least as much as the call IV, and to the call leg otherwise. On that rule the put leg explains 29.1 percent of the absolute gap, the call leg 24.3 percent, a tenor mismatch 0.2 percent, and a spot mismatch 46.4 percent.

The tenor flag is on 4 compared keys and the spot flag is on 1680 compared keys. 1 key has both flags. A key with both flags is counted in the tenor share, not in both shares. Assignment counts: put 1052, call 1230, tenor 4, spot 1679.

A second split ignores tenor and spot and only compares the size of the two IV moves. The put IV accounts for 53.8 percent of the absolute IV movement, and the call IV accounts for 46.2 percent. Those two shares add to 100 percent when either leg moved. They answer a different question from the four shares above.

compute_skew does not return the strike it picked. This receipt does not invent a second strike picker, and the engine file was not edited to add one.

## Stratification

N is the number of compared keys in the row. Match, flip, and zero add up to N. Sign agreement is match divided by N. A row with N of 0 has no agreement rate and no gap percentile. Quartiles use the compared keys only. Fewer than four distinct values stay in one bin.

### By underlying class

Index ETFs are SPY, QQQ, IWM, and DIA. Every other underlying is a single name.

| stratum | N | match | flip | zero | sign agreement | |delta| p50 | |delta| p90 | |delta| max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| index_etf | 104 | 91 | 13 | 0 | 0.875000 | 0.010700 | 0.026600 | 0.095900 |
| single_name | 3861 | 2301 | 1550 | 10 | 0.595960 | 0.039300 | 0.169300 | 3.952900 |

### By legacy strike count

The quartile is the legacy ledger's n_strikes on the compared keys. Q1 is the lowest strike count.

| stratum | N | match | flip | zero | sign agreement | |delta| p50 | |delta| p90 | |delta| max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 (1.999, 21.0] | 1000 | 632 | 365 | 3 | 0.632000 | 0.055200 | 0.237800 | 3.952900 |
| Q2 (21.0, 34.0] | 1030 | 616 | 410 | 4 | 0.598058 | 0.041600 | 0.163800 | 1.201700 |
| Q3 (34.0, 57.0] | 950 | 543 | 406 | 1 | 0.571579 | 0.036900 | 0.146600 | 1.208400 |
| Q4 (57.0, 434.0] | 985 | 601 | 382 | 2 | 0.610152 | 0.026900 | 0.105700 | 0.973000 |

### By stored open interest

Open interest is the total on the stored chain for that day, across every expiry the file holds, not only the expiry the formula picked. A key whose chain has no open interest is in oi_unavailable.

| stratum | N | match | flip | zero | sign agreement | |delta| p50 | |delta| p90 | |delta| max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 (24.999, 37938.0] | 991 | 643 | 348 | 0 | 0.648840 | 0.050400 | 0.189100 | 3.952900 |
| Q2 (37938.0, 195861.5] | 991 | 602 | 387 | 2 | 0.607467 | 0.037100 | 0.138900 | 2.857400 |
| Q3 (195861.5, 694170.5] | 991 | 574 | 414 | 3 | 0.579213 | 0.038400 | 0.186000 | 0.992200 |
| Q4 (694170.5, 21143083.0] | 991 | 573 | 413 | 5 | 0.578204 | 0.030100 | 0.135900 | 1.208400 |
| oi_unavailable | 1 | 0 | 1 | 0 | 0.000000 | 0.319000 | 0.319000 | 0.319000 |

### By stored volume

Volume is the total on that same stored chain. A key whose chain has no volume is in volume_unavailable.

| stratum | N | match | flip | zero | sign agreement | |delta| p50 | |delta| p90 | |delta| max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 (-0.001, 1354.0] | 992 | 644 | 348 | 0 | 0.649194 | 0.050100 | 0.194000 | 3.952900 |
| Q2 (1354.0, 10118.0] | 991 | 592 | 397 | 2 | 0.597376 | 0.040500 | 0.168300 | 2.857400 |
| Q3 (10118.0, 53996.0] | 991 | 575 | 412 | 4 | 0.580222 | 0.034800 | 0.151900 | 1.201700 |
| Q4 (53996.0, 15669223.0] | 991 | 581 | 406 | 4 | 0.586276 | 0.031000 | 0.136500 | 1.208400 |

## Twenty largest absolute gaps

Both IV legs are shown. Tenor mismatch means the tenors differ by more than 5 days. Spot mismatch means the spots differ by more than 2 percent.

| date | underlying | class | legacy skew | new skew | delta | legacy put IV | new put IV | legacy call IV | new call IV | legacy tenor | new tenor | legacy spot | new spot | tenor mismatch | spot mismatch | legacy strikes | new strikes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-30 | MQ | single_name | 0.187700 | 4.140600 | -3.952900 | 0.757900 | 4.617200 | 0.570200 | 0.476600 | 17.0 | 17.0 | 4.1800 | 4.0600 | no | yes | 4 | 16 |
| 2026-06-25 | MQ | single_name | 0.046500 | 3.556000 | -3.509500 | 0.463500 | 3.993500 | 0.417000 | 0.437500 | 22.0 | 22.0 | 3.9700 | 3.9500 | no | no | 4 | 16 |
| 2026-06-22 | MQ | single_name | -0.046300 | 3.159800 | -3.206100 | 0.414700 | 3.636300 | 0.461000 | 0.476600 | 25.0 | 25.0 | 3.7750 | 3.7600 | no | no | 2 | 16 |
| 2026-06-29 | ALT | single_name | 0.220700 | -2.636700 | 2.857400 | 0.969000 | 0.710900 | 0.748300 | 3.347600 | 32.0 | 32.0 | 2.8200 | 2.9400 | no | yes | 6 | 24 |
| 2026-07-01 | ALT | single_name | 0.180600 | 2.593600 | -2.413000 | 1.202100 | 3.557600 | 1.021600 | 0.964100 | 30.0 | 30.0 | 3.0400 | 3.1500 | no | yes | 5 | 24 |
| 2026-06-26 | ALT | single_name | -0.424200 | -2.715000 | 2.290800 | 1.460500 | 1.048400 | 1.884700 | 3.763500 | 28.0 | 28.0 | 2.8700 | 2.8200 | no | no | 4 | 24 |
| 2026-06-24 | MQ | single_name | -0.105800 | 2.095700 | -2.201500 | 0.245100 | 2.498000 | 0.350900 | 0.402300 | 23.0 | 23.0 | 3.8300 | 3.9700 | no | yes | 2 | 16 |
| 2026-06-23 | ALT | single_name | 0.692700 | 2.824400 | -2.131700 | 1.476400 | 3.666600 | 0.783700 | 0.842200 | 31.0 | 31.0 | 2.9300 | 2.9100 | no | no | 3 | 22 |
| 2026-07-02 | ALT | single_name | 0.453100 | -1.490200 | 1.943300 | 1.346500 | 1.265600 | 0.893400 | 2.755900 | 29.0 | 29.0 | 3.1500 | 3.1600 | no | no | 6 | 24 |
| 2026-06-23 | MQ | single_name | 0.038200 | -1.633200 | 1.671400 | 0.497200 | 1.298400 | 0.459000 | 2.931600 | 24.0 | 24.0 | 3.7600 | 3.8300 | no | no | 2 | 16 |
| 2026-07-02 | EU | single_name | 1.440200 | -0.153100 | 1.593300 | 2.598100 | 1.200000 | 1.158000 | 1.353100 | 15.0 | 15.0 | 1.3600 | 1.2900 | no | yes | 4 | 18 |
| 2026-06-30 | ALT | single_name | -0.430900 | -1.896100 | 1.465200 | 1.097800 | 1.123400 | 1.528700 | 3.019500 | 31.0 | 31.0 | 2.9400 | 3.0400 | no | yes | 5 | 24 |
| 2026-07-22 | SMCI | single_name | 1.207800 | -0.000600 | 1.208400 | 1.626300 | 1.054200 | 0.418600 | 1.054800 | 30.0 | 30.0 | 25.5000 | 30.5600 | no | yes | 48 | 130 |
| 2026-06-30 | AVAV | single_name | 1.191200 | -0.010500 | 1.201700 | 1.523200 | 0.809200 | 0.332000 | 0.819700 | 31.0 | 31.0 | 139.0000 | 165.0700 | no | yes | 27 | 78 |
| 2026-07-02 | FLYW | single_name | -0.174300 | -1.373800 | 1.199500 | 0.453400 | 0.414000 | 0.627700 | 1.787800 | 15.0 | 15.0 | 18.5600 | 18.7500 | no | no | 6 | 22 |
| 2026-06-30 | EU | single_name | 1.262800 | 0.150000 | 1.112800 | 2.313300 | 1.156200 | 1.050500 | 1.006300 | 17.0 | 17.0 | 1.3300 | 1.3100 | no | no | 4 | 18 |
| 2026-06-30 | KVUE | single_name | 0.519500 | -0.550000 | 1.069500 | 0.747400 | 0.182600 | 0.227900 | 0.732600 | 31.0 | 31.0 | 19.0700 | 19.1100 | no | no | 12 | 60 |
| 2026-07-31 | XLU | single_name | -0.024600 | 1.033500 | -1.058100 | 0.187100 | 1.193100 | 0.211700 | 0.159600 | 28.0 | 28.0 | 44.6600 | 44.3500 | no | no | 32 | 60 |
| 2026-06-26 | EU | single_name | 1.246700 | 0.196900 | 1.049800 | 2.143300 | 1.550000 | 0.896600 | 1.353100 | 21.0 | 21.0 | 1.3300 | 1.3500 | no | no | 4 | 18 |
| 2026-06-23 | PCG | single_name | -0.027600 | 0.995100 | -1.022700 | 0.308300 | 1.251900 | 0.335800 | 0.256800 | 31.0 | 31.0 | 16.6300 | 16.7700 | no | no | 14 | 58 |

## Summary

The next line is the summary of the counts above.
{"abs_call_movement_share":0.462264,"abs_delta_max":3.9529,"abs_delta_p50":0.0379,"abs_delta_p90":0.167,"abs_put_movement_share":0.537736,"by_class":[{"abs_delta_max":0.0959,"abs_delta_p50":0.0107,"abs_delta_p90":0.0266,"n":104,"n_sign_flip":13,"n_sign_match":91,"n_zero":0,"sign_agreement_rate":0.875,"stratum":"index_etf"},{"abs_delta_max":3.9529,"abs_delta_p50":0.0393,"abs_delta_p90":0.1693,"n":3861,"n_sign_flip":1550,"n_sign_match":2301,"n_zero":10,"sign_agreement_rate":0.59596,"stratum":"single_name"}],"by_n_strikes_quartile":[{"abs_delta_max":3.9529,"abs_delta_p50":0.0552,"abs_delta_p90":0.2378,"n":1000,"n_sign_flip":365,"n_sign_match":632,"n_zero":3,"sign_agreement_rate":0.632,"stratum":"Q1 (1.999, 21.0]"},{"abs_delta_max":1.2017,"abs_delta_p50":0.0416,"abs_delta_p90":0.1638,"n":1030,"n_sign_flip":410,"n_sign_match":616,"n_zero":4,"sign_agreement_rate":0.598058,"stratum":"Q2 (21.0, 34.0]"},{"abs_delta_max":1.2084,"abs_delta_p50":0.0369,"abs_delta_p90":0.1466,"n":950,"n_sign_flip":406,"n_sign_match":543,"n_zero":1,"sign_agreement_rate":0.571579,"stratum":"Q3 (34.0, 57.0]"},{"abs_delta_max":0.973,"abs_delta_p50":0.0269,"abs_delta_p90":0.1057,"n":985,"n_sign_flip":382,"n_sign_match":601,"n_zero":2,"sign_agreement_rate":0.610152,"stratum":"Q4 (57.0, 434.0]"}],"by_store_oi_quartile":[{"abs_delta_max":3.9529,"abs_delta_p50":0.0504,"abs_delta_p90":0.1891,"n":991,"n_sign_flip":348,"n_sign_match":643,"n_zero":0,"sign_agreement_rate":0.64884,"stratum":"Q1 (24.999, 37938.0]"},{"abs_delta_max":2.8574,"abs_delta_p50":0.0371,"abs_delta_p90":0.1389,"n":991,"n_sign_flip":387,"n_sign_match":602,"n_zero":2,"sign_agreement_rate":0.607467,"stratum":"Q2 (37938.0, 195861.5]"},{"abs_delta_max":0.9922,"abs_delta_p50":0.0384,"abs_delta_p90":0.186,"n":991,"n_sign_flip":414,"n_sign_match":574,"n_zero":3,"sign_agreement_rate":0.579213,"stratum":"Q3 (195861.5, 694170.5]"},{"abs_delta_max":1.2084,"abs_delta_p50":0.0301,"abs_delta_p90":0.1359,"n":991,"n_sign_flip":413,"n_sign_match":573,"n_zero":5,"sign_agreement_rate":0.578204,"stratum":"Q4 (694170.5, 21143083.0]"},{"abs_delta_max":0.319,"abs_delta_p50":0.319,"abs_delta_p90":0.319,"n":1,"n_sign_flip":1,"n_sign_match":0,"n_zero":0,"sign_agreement_rate":0.0,"stratum":"oi_unavailable"}],"by_store_volume_quartile":[{"abs_delta_max":3.9529,"abs_delta_p50":0.0501,"abs_delta_p90":0.194,"n":992,"n_sign_flip":348,"n_sign_match":644,"n_zero":0,"sign_agreement_rate":0.649194,"stratum":"Q1 (-0.001, 1354.0]"},{"abs_delta_max":2.8574,"abs_delta_p50":0.0405,"abs_delta_p90":0.1683,"n":991,"n_sign_flip":397,"n_sign_match":592,"n_zero":2,"sign_agreement_rate":0.597376,"stratum":"Q2 (1354.0, 10118.0]"},{"abs_delta_max":1.2017,"abs_delta_p50":0.0348,"abs_delta_p90":0.1519,"n":991,"n_sign_flip":412,"n_sign_match":575,"n_zero":4,"sign_agreement_rate":0.580222,"stratum":"Q3 (10118.0, 53996.0]"},{"abs_delta_max":1.2084,"abs_delta_p50":0.031,"abs_delta_p90":0.1365,"n":991,"n_sign_flip":406,"n_sign_match":581,"n_zero":4,"sign_agreement_rate":0.586276,"stratum":"Q4 (53996.0, 15669223.0]"}],"chosen_k_exposed":false,"compared":3965,"date_not_in_store_for_root":5411,"explained_share_call_leg":0.243235,"explained_share_put_leg":0.290918,"explained_share_spot":0.463737,"explained_share_tenor":0.00211,"legacy_keys":12375,"limit":null,"max_identity_residual":0.0002,"n_assigned_call":1230,"n_assigned_put":1052,"n_assigned_spot":1679,"n_assigned_tenor":4,"n_both_mismatch":1,"n_sign_flip":1563,"n_sign_match":2392,"n_spot_mismatch":1680,"n_tenor_mismatch":4,"n_zero":10,"no_usable_tenor":0,"other":0,"population_keys":12375,"recompute_errors":0,"reconciles":true,"root_not_in_store":124,"sample_seed":null,"schema":"options_skew_parity.v1","sign_agreement_rate":0.603279,"weekend_date":2875}
