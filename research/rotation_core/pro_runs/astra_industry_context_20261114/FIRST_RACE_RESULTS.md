# First industry-model race: executed, no promotion

Source implementation e6b8b471ce5b04058bac8369da1c7fb7578e83fc; process 54114 exited 0. Twenty-two focused unit tests passed before the real-data run. pandas 3.0.5 exposed a read-only-array issue in the first unit run; explicit copying fixed it before historical fitting. Runtime versions: numpy 2.5.2, pandas 3.0.5, scipy 1.18.0.

## Design and sample

Three model tracks fixed before outcomes: momentum-information baseline, additive context, conditional interactions. Separate raw 12-minus-1-month momentum ranking benchmark. Four expanding chronological train/test folds: 1963-72, 1973-82, 1983-92, 1993-2002. Every training label matures before its test boundary. 23,153 out-of-fold industry-month observations across 477 decision months. Each same-month top-quintile selection has 4,752 observations and identical monthly coverage. Entry next-session close; 63 subsequent sessions; fixed +/-10% closing first-passage boundaries; 20 bp cost. Equal-month statistics, not overlapping-position portfolio returns.

French49 current-vintage (202609 CRSP) reconstruction, with both inputs numerically cut off at 2002-12-31. Industry archive SHA256 b9d36d571e968d71f7b03207e7fed6398554f953719b8c1bf3ee3ad8d00e7520; factors archive 96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89. Actual-input prefix checks passed at year-end dates in 1950, 1982 and 2001. No post-2002 outcomes were used.

## Registered top-quintile comparison

| Selection | Mean net63 | Mean excess63 | Win rate | Any 10% closing loss | Mean adverse excursion |
|---|---:|---:|---:|---:|---:|
| Raw momentum | 4.3067% | 1.4687% | 64.3792% | 22.9863% | -6.4394% |
| Momentum-information model | 4.1363% | 1.2983% | 62.9676% | 25.3203% | -6.9755% |
| Additive context model | 4.0026% | 1.1647% | 63.3543% | 24.1183% | -6.7473% |
| Conditional interactions | 3.9923% | 1.1544% | 63.9087% | 24.1230% | -6.7638% |

Interactions minus raw momentum: -0.3143 percentage points mean excess63; descriptive 95% 12-calendar-month moving-block interval [-0.7134,-0.0302] pp. Interaction minus additive: -0.0103 pp [-0.2158,+0.1641]. Win and tail differences do not establish a superiority claim. Intervals are unadjusted exploratory; no sector-specific selected winner is promoted.

Probabilistic description improves modestly without improving selection. Equal-month 3-class Brier: momentum-information 0.61065, additive 0.60612, interactions 0.60568. Tail Brier: 0.16763, 0.16618, 0.16624. These diagnostic improvements are not proof of calibrated trading confidence or profitable selection.

## Interpretation and next discriminating action

Do not replace the momentum benchmark with the more complex expected-return model. The result argues for separately testing a risk overlay conditional on existing industry leadership, rather than assuming a joint mean-return model will learn a superior ordering. A second, prospectively specified *within this already-seen historical discovery dataset* experiment will compare a shallow boosted-tree challenger and risk-overlay selection against raw momentum and an equally selective low-volatility filter. This is adaptive development, not an untouched confirmation. K3E numeric historical estimates were not invented; live/source-dated industry context composition proceeds independently.

## Durable source versus original aggregate files

The original complete local aggregate report is `research/rotation_core/pro_runs/astra_industry_context_20261114/results/industry_discovery_results.json`, 31,186 bytes, SHA256 cec1b7fb832c47dda4a2c640063b50665f10b42fb4499f447fa97bb92a47789d. Model serialization is `industry_research_models.json`, 20,415 bytes, SHA256 16538f2182eff96e4f8cf8a9576efc4003aa33e77de9d9ac3a1cd1c21f01f9d4. These originals remain in the admitted operation-bound M2 SSD proof workspace, not falsely claimed committed. This committed summary preserves the main results; the deterministic committed runner reproduces all state/era slices and probability bins from the hash-bound inputs.

No raw vendor observations committed, no live ranking/size/order changed, no reserve release, no predictive candidate promoted. The parent industry-first Prophet implementation remains incomplete; the ready next phase is the adaptive risk/model comparison and real-input K3E/Prophet consumer proof.
