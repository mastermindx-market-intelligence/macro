# Commodity conviction — calibration

Measured forward-return predictive strength per factor (Spearman, 63d & 126d), split-half @ 2013-01-01. Weight = polarity x |corr| x stability, normalized to 0.8 panel mass (+ live cycle/mtf/alerts). Thresholds = score quantiles; buckets verified monotone in forward 126d return.


## Gold

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| carry | +0.184 | 0.178 | 0.122 | 0.275 | ✓ |
| liquidity | +0.150 | 0.148 | 0.086 | 0.173 | ✓ |
| inflation | -0.126 | -0.129 | -0.179 | -0.11 | ✓ |
| value | -0.113 | -0.112 | -0.101 | -0.205 | ✓ |
| cycle | +0.100 | — | — | — | · |
| trend | +0.063 | 0.159 | -0.25 | 0.253 | · |
| dollar | -0.062 | -0.056 | -0.063 | -0.044 | ✓ |
| mtf | +0.060 | — | — | — | · |
| positioning | -0.041 | -0.091 | 0.062 | -0.146 | · |
| alerts | +0.040 | — | — | — | · |
| real_rates | +0.030 | 0.066 | -0.184 | 0.208 | · |
| growth | -0.030 | -0.057 | 0.053 | -0.184 | · |

Cycle (amp 0.18, 14 legs): bull median 1012d (n=7, 95.2%); bear median 177d (n=7, 21.9%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 14 | +2.48 | 100.0 |
| SELL | 1329 | +2.68 | 64.2 |
| HOLD | 2786 | +5.07 | 64.7 |
| BUY | 1649 | +9.72 | 79.6 |
| STRONG BUY | 493 | +13.00 | 94.9 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Silver

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| value | +0.211 | 0.175 | 0.184 | 0.28 | ✓ |
| inflation | -0.137 | -0.106 | -0.095 | -0.123 | ✓ |
| carry | +0.122 | 0.088 | 0.037 | 0.209 | ✓ |
| cycle | +0.100 | — | — | — | · |
| growth | -0.089 | -0.07 | -0.006 | -0.198 | ✓ |
| risk | -0.068 | -0.041 | -0.004 | -0.062 | ✓ |
| mtf | +0.060 | — | — | — | · |
| shock | -0.053 | -0.032 | -0.01 | -0.072 | ✓ |
| real_rates | +0.051 | 0.092 | -0.122 | 0.223 | · |
| liquidity | +0.042 | 0.076 | -0.029 | 0.138 | · |
| alerts | +0.040 | — | — | — | · |
| riskoff | -0.026 | -0.049 | 0.0 | -0.164 | · |

Cycle (amp 0.35, 14 legs): bull median 631d (n=7, 150.5%); bear median 453d (n=7, 43.2%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 541 | +0.59 | 43.1 |
| SELL | 1710 | +6.27 | 52.0 |
| HOLD | 1799 | +8.11 | 56.0 |
| BUY | 1736 | +8.42 | 67.5 |
| STRONG BUY | 550 | +19.46 | 83.3 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Copper

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| risk | -0.187 | -0.158 | -0.125 | -0.214 | ✓ |
| riskoff | +0.151 | 0.135 | 0.13 | 0.138 | ✓ |
| growth | +0.145 | 0.114 | 0.042 | 0.141 | ✓ |
| real_rates | +0.106 | 0.084 | 0.055 | 0.078 | ✓ |
| structure | +0.103 | 0.084 | 0.136 | 0.007 | ✓ |
| cycle | +0.100 | — | — | — | · |
| mtf | +0.060 | — | — | — | · |
| liquidity | +0.042 | 0.096 | -0.038 | 0.235 | · |
| alerts | +0.040 | — | — | — | · |
| dollar | +0.035 | 0.061 | -0.051 | 0.17 | · |
| carry | -0.030 | -0.048 | -0.188 | 0.163 | · |

Cycle (amp 0.28, 14 legs): bull median 711d (n=7, 69.8%); bear median 258d (n=7, 35.6%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 844 | -5.61 | 38.9 |
| SELL | 1720 | +2.90 | 49.7 |
| HOLD | 2777 | +10.47 | 64.7 |
| BUY | 1040 | +10.15 | 70.0 |
| STRONG BUY | 41 | +1.31 | 39.0 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context

## Oil

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| trend | -0.141 | -0.184 | -0.39 | -0.13 | ✓ |
| growth | +0.121 | 0.159 | 0.189 | 0.1 | ✓ |
| real_rates | +0.112 | 0.155 | 0.346 | 0.028 | ✓ |
| cycle | +0.100 | — | — | — | · |
| dollar | +0.096 | 0.146 | 0.073 | 0.223 | ✓ |
| shock | -0.090 | -0.132 | -0.159 | -0.12 | ✓ |
| risk | -0.088 | -0.092 | -0.153 | -0.065 | ✓ |
| value | +0.073 | 0.088 | 0.222 | 0.024 | ✓ |
| mtf | +0.060 | — | — | — | · |
| alerts | +0.040 | — | — | — | · |
| structure | -0.033 | -0.032 | -0.051 | -0.031 | ✓ |
| liquidity | +0.028 | 0.101 | -0.038 | 0.221 | · |
| riskoff | +0.018 | 0.069 | -0.001 | 0.094 | · |

Cycle (amp 0.4, 18 legs): bull median 194d (n=9, 55.9%); bear median 342d (n=9, 57.3%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 879 | -7.66 | 40.8 |
| SELL | 1693 | +0.59 | 45.1 |
| HOLD | 2479 | +7.15 | 62.1 |
| BUY | 1223 | +19.18 | 77.4 |
| STRONG BUY | 152 | +2.08 | 42.8 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context
