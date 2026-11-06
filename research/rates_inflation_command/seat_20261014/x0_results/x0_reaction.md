# X0 release reaction — descriptive receipt

Descriptive co-movement in daily closes only. Not a prediction, not a sizing input, and not an explanation of why rates moved.

Benchmark: change vs a no-change benchmark

Protocol: research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md (sha256 87b51dcad66c6f84989675e9cce91eb5b46b3888d60b2e599a8736d87e2309df)

As-of: 2026-10-14

## Inputs

| input | sha256 | rights |
|---|---|---|
| research/rates_inflation_command/seat_20261014/x0_inputs/ppi_release_dates_receipt.json | 29efcee22e76d99ba39bfa709aaa5ad84628df9ec926eb8c6b2dafa1a7a9f0c3 | public_domain |
| research/rates_inflation_command/seat_20261014/x0_inputs/gdp_advance_dates_receipt.json | 7e8086bd46bb7fdab388bbad6064e80ae5ee6a9cbf6431cec76beb4fdf2269fb | public_domain |
| data/fred_vintage/vintages.parquet | 4492376642df7eca46ba1657113e1b72290af29aa6cbe7fc532f1d3f2a6c7ecf | — |
| data/fred_vintage/release_targets/CPILFESL_all_vintages.parquet | 891693ac01a6046a2c1119eb053a45e94ccdc067485c3fe31f62ac3fadf2a484 | — |
| data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet | 218ee4e111c4372dd12a1f6e57b4079784418fd018f3cc1819c275f21d0c505d | — |
| data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet | 572f0ebcbea40c98c90e6a1a100d38f5cbb3de15e9e436676bc3aa317785b98b | — |
| data/fred/DGS2.parquet | 6424aca3173f751ea50ad8b26bdce4b66f925106a4b920929c0a166c707e03aa | — |
| data/fred/DGS10.parquet | 1e4a03e813593256e27e7df6a765ba64da05da8e7c4e4f4af6a7d36236a7f64e | — |
| data/fred/DFII10.parquet | 37f62c3ca0e0650234adb2d80a9460f43d09d587082a388b11cd394ab848fe8a | — |
| data/fred/T10YIE.parquet | 6df313258e1fafbe1356928810057258e6c0eac5f30c9c9fc88175b2eab59674 | — |

Windows: h0 = prior trading-day close to release-day close (the only tested window). h1 = release-day close to next trading-day close (descriptive only).

## Tests — era 2010s (2010-01-01 .. 2019-12-31)

| test | n | beta (bp/sd) | se | p_holm_normal | p_holm_t | label |
|---|---|---|---|---|---|---|
| CPI:DGS2 | 111 | 0.1428 | 0.2894 | 1 | 1 | NOT_IDENTIFIED |
| CPI:DGS10 | 111 | -0.1151 | 0.3596 | 1 | 1 | NOT_IDENTIFIED |
| CPI:DFII10 | 111 | -0.7400 | 0.3002 | 0.09588 | 0.1068 | NOT_IDENTIFIED |
| CPI:T10YIE | 111 | 0.6249 | 0.2749 | 0.1269 | 0.1378 | NOT_IDENTIFIED |
| NFP:DGS2 | 115 | 1.1344 | 0.3937 | 0.03168 | 0.03792 | NOT_IDENTIFIED |
| NFP:DGS10 | 115 | 1.5246 | 0.6613 | 0.1269 | 0.1378 | NOT_IDENTIFIED |
| NFP:DFII10 | 115 | 1.2263 | 0.5463 | 0.1269 | 0.1378 | NOT_IDENTIFIED |
| NFP:T10YIE | 115 | 0.2983 | 0.2312 | 0.5908 | 0.5987 | NOT_IDENTIFIED |

## Tests — era 2021+ (2021-01-01 .. open)

| test | n | beta (bp/sd) | se | p_holm_normal | p_holm_t | label |
|---|---|---|---|---|---|---|
| CPI:DGS2 | 65 | 3.0372 | 1.1014 | 0.04076 | 0.05327 | NOT_IDENTIFIED |
| CPI:DGS10 | 65 | 2.2682 | 0.7997 | 0.03652 | 0.04906 | NOT_IDENTIFIED |
| CPI:DFII10 | 65 | 1.6024 | 0.6961 | 0.1067 | 0.1233 | NOT_IDENTIFIED |
| CPI:T10YIE | 65 | 0.6659 | 0.3424 | 0.1602 | 0.1758 | NOT_IDENTIFIED |
| NFP:DGS2 | 69 | 4.9960 | 1.9902 | 0.07237 | 0.08689 | NOT_IDENTIFIED |
| NFP:DGS10 | 69 | 3.1668 | 1.5928 | 0.1602 | 0.1758 | NOT_IDENTIFIED |
| NFP:DFII10 | 69 | 2.6801 | 1.3054 | 0.1602 | 0.1758 | NOT_IDENTIFIED |
| NFP:T10YIE | 69 | 0.4866 | 0.4616 | 0.2918 | 0.2955 | NOT_IDENTIFIED |

## Labels

- CPI:DGS2: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+)
- CPI:DGS10: NOT_IDENTIFIED (not_significant:2010s, sign_flip)
- CPI:DFII10: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+, sign_flip)
- CPI:T10YIE: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+)
- NFP:DGS2: NOT_IDENTIFIED (not_significant:2021+)
- NFP:DGS10: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+)
- NFP:DFII10: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+)
- NFP:T10YIE: NOT_IDENTIFIED (not_significant:2010s, not_significant:2021+)

## Exclusions and episode counts

| release | status | n |
|---|---|---|
| CPI | INSUFFICIENT_HISTORY | 24 |
| CPI | MISSING_RESPONSE | 8 |
| CPI | MISSING_SOURCE | 1 |
| CPI | NO_BENCHMARK | 1 |
| CPI | OK | 177 |
| CPI | OUT_OF_ERA | 21 |
| CPI | TIER1_COLLISION | 9 |
| NFP | INSUFFICIENT_HISTORY | 24 |
| NFP | NO_BENCHMARK | 1 |
| NFP | OK | 184 |
| NFP | OUT_OF_ERA | 21 |
| NFP | TIER1_COLLISION | 5 |

MISSING_RESPONSE counts (episode, response) pairs; the per-episode lists name the response series.

## Descriptive companions — CPI headline co-movement (never tested)

| response | era | n | beta (bp/sd) | se | p_normal | p_t |
|---|---|---|---|---|---|---|
| DGS2 | 2010s | 111 | 0.0879 | 0.2936 | 0.7648 | 0.7653 |
| DGS2 | 2021+ | 65 | 1.9656 | 0.5654 | 0.000509 | 0.000927 |
| DGS10 | 2010s | 111 | -0.1099 | 0.5409 | 0.839 | 0.8394 |
| DGS10 | 2021+ | 65 | 1.1351 | 0.4620 | 0.01402 | 0.01678 |
| DFII10 | 2010s | 111 | -0.3714 | 0.5360 | 0.4884 | 0.4899 |
| DFII10 | 2021+ | 65 | 0.6374 | 0.5769 | 0.2692 | 0.2734 |
| T10YIE | 2010s | 111 | 0.2615 | 0.6778 | 0.6997 | 0.7004 |
| T10YIE | 2021+ | 65 | 0.4977 | 0.3677 | 0.1759 | 0.1807 |

## Descriptive companions — h1 windows (never tested)

| test | era | n | mean (bp) | median (bp) | sd (bp) |
|---|---|---|---|---|---|
| CPI:DGS2 | 2010s | 111 | 0.2703 | 0.0000 | 3.2834 |
| CPI:DGS2 | 2021+ | 65 | -0.3231 | 0.0000 | 8.4744 |
| CPI:DGS10 | 2010s | 111 | 0.0270 | 0.0000 | 4.8307 |
| CPI:DGS10 | 2021+ | 65 | -0.1385 | 0.0000 | 6.5309 |
| CPI:DFII10 | 2010s | 111 | 0.0811 | 0.0000 | 4.7119 |
| CPI:DFII10 | 2021+ | 65 | -0.0769 | 0.0000 | 5.9747 |
| CPI:T10YIE | 2010s | 111 | -0.0541 | 0.0000 | 3.0357 |
| CPI:T10YIE | 2021+ | 65 | -0.0615 | 0.0000 | 3.2010 |
| NFP:DGS2 | 2010s | 115 | 0.2174 | 0.0000 | 2.9847 |
| NFP:DGS2 | 2021+ | 69 | 0.2754 | 1.0000 | 8.6380 |
| NFP:DGS10 | 2010s | 115 | -0.2609 | 0.0000 | 4.7996 |
| NFP:DGS10 | 2021+ | 69 | 1.1739 | 2.0000 | 5.8585 |
| NFP:DFII10 | 2010s | 115 | 0.0609 | 0.0000 | 3.8917 |
| NFP:DFII10 | 2021+ | 69 | 0.4058 | 0.0000 | 4.9388 |
| NFP:T10YIE | 2010s | 115 | -0.3217 | 0.0000 | 2.6209 |
| NFP:T10YIE | 2021+ | 69 | 0.7681 | 1.0000 | 2.9958 |

## Descriptive companions — h0 by surprise tercile (never tested)

| test | era | tercile | n | x range | h0 mean (bp) | h0 median (bp) |
|---|---|---|---|---|---|---|
| CPI:DGS2 | 2010s | not computable | — | — | — | — |
| CPI:DGS2 | 2021+ | 1 | 22 | [-2.579, -0.376] | -6.6818 | -7.0000 |
| CPI:DGS2 | 2021+ | 2 | 21 | [-0.360, 0.379] | 4.6190 | 3.0000 |
| CPI:DGS2 | 2021+ | 3 | 22 | [0.379, 3.106] | 4.2273 | 3.5000 |
| CPI:DGS10 | 2010s | not computable | — | — | — | — |
| CPI:DGS10 | 2021+ | 1 | 22 | [-2.579, -0.376] | -5.5455 | -5.0000 |
| CPI:DGS10 | 2021+ | 2 | 21 | [-0.360, 0.379] | 2.7143 | 3.0000 |
| CPI:DGS10 | 2021+ | 3 | 22 | [0.379, 3.106] | 2.2273 | 3.0000 |
| CPI:DFII10 | 2010s | not computable | — | — | — | — |
| CPI:DFII10 | 2021+ | 1 | 22 | [-2.579, -0.376] | -4.0455 | -3.0000 |
| CPI:DFII10 | 2021+ | 2 | 21 | [-0.360, 0.379] | 2.0952 | 2.0000 |
| CPI:DFII10 | 2021+ | 3 | 22 | [0.379, 3.106] | 0.9545 | 1.5000 |
| CPI:T10YIE | 2010s | not computable | — | — | — | — |
| CPI:T10YIE | 2021+ | 1 | 22 | [-2.579, -0.376] | -1.5000 | -2.0000 |
| CPI:T10YIE | 2021+ | 2 | 21 | [-0.360, 0.379] | 0.6190 | 1.0000 |
| CPI:T10YIE | 2021+ | 3 | 22 | [0.379, 3.106] | 1.2727 | 1.0000 |
| NFP:DGS2 | 2010s | 1 | 39 | [-4.569, -0.302] | -0.9487 | -1.0000 |
| NFP:DGS2 | 2010s | 2 | 38 | [-0.286, 0.489] | 0.4211 | 0.0000 |
| NFP:DGS2 | 2010s | 3 | 38 | [0.503, 2.937] | 1.8421 | 2.0000 |
| NFP:DGS2 | 2021+ | 1 | 23 | [-2.125, -0.131] | -4.8696 | -3.0000 |
| NFP:DGS2 | 2021+ | 2 | 23 | [-0.128, 0.053] | 0.7391 | 0.0000 |
| NFP:DGS2 | 2021+ | 3 | 23 | [0.063, 2.383] | 8.3913 | 8.0000 |
| NFP:DGS10 | 2010s | 1 | 39 | [-4.569, -0.302] | -2.0256 | -2.0000 |
| NFP:DGS10 | 2010s | 2 | 38 | [-0.286, 0.489] | 0.8684 | 0.5000 |
| NFP:DGS10 | 2010s | 3 | 38 | [0.503, 2.937] | 2.6579 | 3.0000 |
| NFP:DGS10 | 2021+ | 1 | 23 | [-2.125, -0.131] | -2.8696 | -3.0000 |
| NFP:DGS10 | 2021+ | 2 | 23 | [-0.128, 0.053] | 0.9565 | 3.0000 |
| NFP:DGS10 | 2021+ | 3 | 23 | [0.063, 2.383] | 6.0870 | 6.0000 |
| NFP:DFII10 | 2010s | 1 | 39 | [-4.569, -0.302] | -1.7179 | -2.0000 |
| NFP:DFII10 | 2010s | 2 | 38 | [-0.286, 0.489] | 0.2105 | -1.0000 |
| NFP:DFII10 | 2010s | 3 | 38 | [0.503, 2.937] | 2.3158 | 3.0000 |
| NFP:DFII10 | 2021+ | 1 | 23 | [-2.125, -0.131] | -2.1304 | -2.0000 |
| NFP:DFII10 | 2021+ | 2 | 23 | [-0.128, 0.053] | -0.6087 | -1.0000 |
| NFP:DFII10 | 2021+ | 3 | 23 | [0.063, 2.383] | 5.5652 | 5.0000 |
| NFP:T10YIE | 2010s | 1 | 39 | [-4.569, -0.302] | -0.3077 | 0.0000 |
| NFP:T10YIE | 2010s | 2 | 38 | [-0.286, 0.489] | 0.6579 | 1.0000 |
| NFP:T10YIE | 2010s | 3 | 38 | [0.503, 2.937] | 0.3421 | 0.0000 |
| NFP:T10YIE | 2021+ | 1 | 23 | [-2.125, -0.131] | -0.7391 | 0.0000 |
| NFP:T10YIE | 2021+ | 2 | 23 | [-0.128, 0.053] | 1.5652 | 2.0000 |
| NFP:T10YIE | 2021+ | 3 | 23 | [0.063, 2.383] | 0.5217 | 0.0000 |

## Descriptive companions — sign agreement (never tested)

| test | era | k | n | share | wilson 95% | zero excluded |
|---|---|---|---|---|---|---|
| CPI:DGS2 | 2010s | 29 | 51 | 0.569 | [0.433, 0.695] | 60 |
| CPI:DGS2 | 2021+ | 34 | 44 | 0.773 | [0.630, 0.872] | 21 |
| CPI:DGS10 | 2010s | 33 | 62 | 0.532 | [0.410, 0.651] | 49 |
| CPI:DGS10 | 2021+ | 31 | 49 | 0.633 | [0.493, 0.753] | 16 |
| CPI:DFII10 | 2010s | 21 | 54 | 0.389 | [0.270, 0.522] | 57 |
| CPI:DFII10 | 2021+ | 30 | 48 | 0.625 | [0.484, 0.748] | 17 |
| CPI:T10YIE | 2010s | 40 | 58 | 0.690 | [0.562, 0.794] | 53 |
| CPI:T10YIE | 2021+ | 30 | 46 | 0.652 | [0.508, 0.773] | 19 |
| NFP:DGS2 | 2010s | 60 | 100 | 0.600 | [0.502, 0.691] | 15 |
| NFP:DGS2 | 2021+ | 42 | 64 | 0.656 | [0.534, 0.761] | 5 |
| NFP:DGS10 | 2010s | 67 | 112 | 0.598 | [0.506, 0.684] | 3 |
| NFP:DGS10 | 2021+ | 38 | 67 | 0.567 | [0.448, 0.679] | 2 |
| NFP:DFII10 | 2010s | 69 | 110 | 0.627 | [0.534, 0.712] | 5 |
| NFP:DFII10 | 2021+ | 42 | 64 | 0.656 | [0.534, 0.761] | 5 |
| NFP:T10YIE | 2010s | 54 | 95 | 0.568 | [0.468, 0.663] | 20 |
| NFP:T10YIE | 2021+ | 29 | 53 | 0.547 | [0.415, 0.673] | 16 |

