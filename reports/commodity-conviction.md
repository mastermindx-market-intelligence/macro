# Commodity conviction — calibration

Measured forward-return predictive strength per factor (Spearman, 63d & 126d), split-half @ 2013-01-01. Weight = polarity x |corr| x stability, normalized to 0.8 panel mass (+ live cycle/mtf/alerts). Thresholds = score quantiles; buckets verified monotone in forward 126d return.


## Gold

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| carry | +0.184 | 0.178 | 0.122 | 0.275 | ✓ |
| liquidity | +0.148 | 0.144 | 0.086 | 0.168 | ✓ |
| inflation | -0.128 | -0.13 | -0.179 | -0.113 | ✓ |
| value | -0.115 | -0.115 | -0.101 | -0.211 | ✓ |
| cycle | +0.100 | — | — | — | · |
| dollar | -0.062 | -0.055 | -0.063 | -0.043 | ✓ |
| trend | +0.062 | 0.155 | -0.25 | 0.248 | · |
| mtf | +0.060 | — | — | — | · |
| positioning | -0.041 | -0.09 | 0.062 | -0.144 | · |
| alerts | +0.040 | — | — | — | · |
| growth | -0.030 | -0.058 | 0.053 | -0.187 | · |
| real_rates | +0.030 | 0.067 | -0.184 | 0.208 | · |

Cycle (amp 0.18, 14 legs): bull median 1012d (n=7, 96.9%); bear median 177d (n=7, 21.9%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 14 | +2.48 | 100.0 |
| SELL | 1323 | +2.71 | 64.5 |
| HOLD | 2784 | +5.03 | 64.5 |
| BUY | 1657 | +9.69 | 79.7 |
| STRONG BUY | 500 | +12.97 | 94.6 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Silver

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| value | +0.213 | 0.177 | 0.184 | 0.285 | ✓ |
| inflation | -0.138 | -0.107 | -0.095 | -0.125 | ✓ |
| carry | +0.123 | 0.09 | 0.037 | 0.211 | ✓ |
| cycle | +0.100 | — | — | — | · |
| growth | -0.089 | -0.07 | -0.006 | -0.199 | ✓ |
| risk | -0.067 | -0.039 | -0.004 | -0.059 | ✓ |
| mtf | +0.060 | — | — | — | · |
| shock | -0.052 | -0.031 | -0.01 | -0.071 | ✓ |
| real_rates | +0.051 | 0.092 | -0.122 | 0.223 | · |
| liquidity | +0.042 | 0.074 | -0.029 | 0.135 | · |
| alerts | +0.040 | — | — | — | · |
| riskoff | -0.025 | -0.048 | 0.0 | -0.162 | · |

Cycle (amp 0.35, 14 legs): bull median 631d (n=7, 150.5%); bear median 453d (n=7, 43.2%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 545 | +0.52 | 42.6 |
| SELL | 1699 | +6.10 | 51.8 |
| HOLD | 1799 | +8.27 | 56.2 |
| BUY | 1732 | +8.43 | 67.4 |
| STRONG BUY | 567 | +19.00 | 82.5 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✓ YES

## Copper

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| risk | -0.188 | -0.158 | -0.125 | -0.214 | ✓ |
| riskoff | +0.151 | 0.134 | 0.13 | 0.136 | ✓ |
| growth | +0.145 | 0.114 | 0.042 | 0.142 | ✓ |
| real_rates | +0.105 | 0.083 | 0.055 | 0.077 | ✓ |
| structure | +0.103 | 0.083 | 0.136 | 0.005 | ✓ |
| cycle | +0.100 | — | — | — | · |
| mtf | +0.060 | — | — | — | · |
| liquidity | +0.043 | 0.097 | -0.038 | 0.237 | · |
| alerts | +0.040 | — | — | — | · |
| dollar | +0.035 | 0.06 | -0.051 | 0.169 | · |
| carry | -0.030 | -0.049 | -0.188 | 0.16 | · |

Cycle (amp 0.28, 14 legs): bull median 711d (n=7, 69.8%); bear median 258d (n=7, 35.6%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 846 | -5.72 | 38.7 |
| SELL | 1730 | +3.09 | 49.9 |
| HOLD | 2784 | +10.44 | 64.8 |
| BUY | 1029 | +10.10 | 69.9 |
| STRONG BUY | 39 | +1.50 | 38.5 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context

## Oil

| factor | weight | corr126 | pre | post | stable |
|---|---:|---:|---:|---:|:--:|
| trend | -0.141 | -0.184 | -0.39 | -0.131 | ✓ |
| growth | +0.121 | 0.158 | 0.189 | 0.099 | ✓ |
| real_rates | +0.111 | 0.155 | 0.346 | 0.028 | ✓ |
| cycle | +0.100 | — | — | — | · |
| dollar | +0.096 | 0.147 | 0.073 | 0.223 | ✓ |
| shock | -0.090 | -0.132 | -0.159 | -0.12 | ✓ |
| risk | -0.088 | -0.092 | -0.153 | -0.065 | ✓ |
| value | +0.073 | 0.088 | 0.222 | 0.025 | ✓ |
| mtf | +0.060 | — | — | — | · |
| alerts | +0.040 | — | — | — | · |
| structure | -0.033 | -0.033 | -0.051 | -0.031 | ✓ |
| liquidity | +0.028 | 0.1 | -0.038 | 0.219 | · |
| riskoff | +0.019 | 0.07 | -0.001 | 0.094 | · |

Cycle (amp 0.4, 18 legs): bull median 194d (n=9, 55.9%); bear median 342d (n=9, 57.3%).

Score buckets (forward 126d):
| action | n | avg fwd126% | hit% |
|---|---:|---:|---:|
| STRONG SELL | 888 | -7.56 | 40.7 |
| SELL | 1686 | +0.51 | 45.1 |
| HOLD | 2478 | +7.27 | 62.3 |
| BUY | 1229 | +18.93 | 77.1 |
| STRONG BUY | 151 | +1.93 | 42.4 |

Score reliable (monotone Strong Sell → Strong Buy, spread ≥6%): ✗ NO — weak for this asset, present as context
