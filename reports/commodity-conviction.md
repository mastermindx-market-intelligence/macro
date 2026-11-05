# Commodity conviction — calibration

Measured forward-return predictive strength per factor (Spearman, 63d & 126d), split-half @ 2013-01-01. Weight = polarity x |corr| x stability, normalized to 0.8 panel mass (+ live cycle/mtf/alerts). Thresholds = score quantiles; buckets verified monotone in forward 126d return.


## Gold

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| carry | +0.184 | 0.18 | 0.122 | 0.277 | ✓ |
| liquidity | +0.146 | 0.142 | 0.086 | 0.164 | ✓ |
| inflation | -0.129 | -0.131 | -0.179 | -0.115 | ✓ |
| value | -0.116 | -0.117 | -0.101 | -0.215 | ✓ |
| cycle | +0.100 | — | — | — | · |
| dollar | -0.062 | -0.055 | -0.063 | -0.043 | ✓ |
| trend | +0.061 | 0.152 | -0.25 | 0.242 | · |
| mtf | +0.060 | — | — | — | · |
| positioning | -0.041 | -0.09 | 0.062 | -0.144 | · |
| alerts | +0.040 | — | — | — | · |
| growth | -0.030 | -0.06 | 0.053 | -0.189 | · |
| real_rates | +0.030 | 0.067 | -0.184 | 0.208 | · |

Cycle (amp 0.18, 14 legs): bull median 1012d (n=7, 96.9%); bear median 177d (n=7, 21.9%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 14 | +2.48 | 100.0 |
| SELL | 1330 | +2.70 | 64.4 |
| HOLD | 2787 | +5.02 | 64.5 |
| BUY | 1652 | +9.71 | 79.8 |
| STRONG BUY | 501 | +12.89 | 94.4 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Silver

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| value | +0.214 | 0.179 | 0.184 | 0.287 | ✓ |
| inflation | -0.139 | -0.108 | -0.095 | -0.126 | ✓ |
| carry | +0.123 | 0.091 | 0.037 | 0.213 | ✓ |
| cycle | +0.100 | — | — | — | · |
| growth | -0.090 | -0.071 | -0.006 | -0.201 | ✓ |
| risk | -0.066 | -0.037 | -0.004 | -0.055 | ✓ |
| mtf | +0.060 | — | — | — | · |
| shock | -0.052 | -0.03 | -0.01 | -0.069 | ✓ |
| real_rates | +0.051 | 0.092 | -0.122 | 0.223 | · |
| liquidity | +0.041 | 0.071 | -0.029 | 0.131 | · |
| alerts | +0.040 | — | — | — | · |
| riskoff | -0.025 | -0.048 | 0.0 | -0.162 | · |

Cycle (amp 0.35, 14 legs): bull median 631d (n=7, 150.5%); bear median 453d (n=7, 43.2%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 556 | +0.30 | 41.9 |
| SELL | 1685 | +6.11 | 51.6 |
| HOLD | 1791 | +8.24 | 56.2 |
| BUY | 1736 | +8.49 | 67.6 |
| STRONG BUY | 580 | +18.68 | 81.9 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Copper

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| risk | -0.188 | -0.158 | -0.125 | -0.213 | ✓ |
| riskoff | +0.151 | 0.134 | 0.13 | 0.136 | ✓ |
| growth | +0.146 | 0.114 | 0.042 | 0.143 | ✓ |
| real_rates | +0.105 | 0.083 | 0.055 | 0.077 | ✓ |
| structure | +0.102 | 0.082 | 0.136 | 0.004 | ✓ |
| cycle | +0.100 | — | — | — | · |
| mtf | +0.060 | — | — | — | · |
| liquidity | +0.043 | 0.098 | -0.038 | 0.238 | · |
| alerts | +0.040 | — | — | — | · |
| dollar | +0.035 | 0.06 | -0.051 | 0.169 | · |
| carry | -0.031 | -0.05 | -0.188 | 0.157 | · |

Cycle (amp 0.28, 14 legs): bull median 711d (n=7, 69.8%); bear median 258d (n=7, 35.6%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 845 | -5.76 | 38.5 |
| SELL | 1732 | +3.13 | 49.9 |
| HOLD | 2789 | +10.45 | 64.9 |
| BUY | 1029 | +10.08 | 69.8 |
| STRONG BUY | 39 | +1.50 | 38.5 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context

## Oil

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| trend | -0.141 | -0.184 | -0.39 | -0.13 | ✓ |
| growth | +0.121 | 0.158 | 0.189 | 0.099 | ✓ |
| real_rates | +0.110 | 0.155 | 0.346 | 0.027 | ✓ |
| cycle | +0.100 | — | — | — | · |
| dollar | +0.095 | 0.147 | 0.073 | 0.223 | ✓ |
| shock | -0.091 | -0.132 | -0.159 | -0.12 | ✓ |
| risk | -0.089 | -0.091 | -0.153 | -0.065 | ✓ |
| value | +0.073 | 0.089 | 0.222 | 0.026 | ✓ |
| mtf | +0.060 | — | — | — | · |
| alerts | +0.040 | — | — | — | · |
| structure | -0.034 | -0.033 | -0.051 | -0.031 | ✓ |
| liquidity | +0.028 | 0.099 | -0.038 | 0.218 | · |
| riskoff | +0.019 | 0.07 | -0.001 | 0.094 | · |

Cycle (amp 0.4, 18 legs): bull median 194d (n=9, 55.9%); bear median 342d (n=9, 57.3%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 896 | -7.40 | 40.7 |
| SELL | 1677 | +0.44 | 45.0 |
| HOLD | 2483 | +7.29 | 62.4 |
| BUY | 1230 | +18.85 | 77.0 |
| STRONG BUY | 152 | +2.15 | 42.8 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context
