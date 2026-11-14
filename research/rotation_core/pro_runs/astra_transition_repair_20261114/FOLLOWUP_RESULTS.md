# Adverse-day resilience follow-up: observed results

Status: ADAPTIVE EXPLORATORY, NOT UNTOUCHED CONFIRMATION. This is a return-proxy mechanism test, not a proprietary-dot backtest. The primary proposed sign was not supported; no threshold was retuned and no inverse trading rule is authorized.

Protocol committed at `cbad8eef315bb15b800738d62627446e99ed8364`; authored code at `3955b98b8bf9d665f291eaa46e9ce1ec4632c05f`. Process 25298 exited 0. Code SHA256 `2f6fea2ca547ccfb5df3269f81daaee1e5b130a337522e3ecf433e711170201d`. Full local `RESILIENCE_RESULTS.json` SHA256 `0bf2305dc8cf72f17e47f0eee4e3d1f17a16bf0d949f239c1433db427ee776a8`. Original pilot code and both vendor archive hashes were unchanged. No outcome after 2002 was parsed or used.

8,795 of the original 8,902 industry-month events met the additional feature requirements, across 774 distinct months. 107 lacked the required complete training/evaluation history or enough positive and negative market days. Feature prefix invariance passed on 36 sampled event rows.

## Definition and primary finding

S = positive mean return residual on negative-market days in the last 21 completed sessions, relative to an intercept and beta estimated on the 252 sessions ending before that evaluation window. Both up- and down-market sides require at least five sessions. U uses positive-market days instead. R retains the first pilot's simple absolute-and-relative rebound condition. B is historical beta >= 1, not a fundamental stock type. M is negative trailing63 market return, not a monetary regime.

Within R, S selects 1,224 events versus 421 without S.

| Group within R | N | Distinct months | Win % | Bad10 % | Net63 % | Excess63 % | Upper-first % | Lower-first % | Unresolved % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S absent |421|205|62.23|32.54|4.79|1.16|24.47|18.29|57.24|
| S present |1224|364|54.90|35.62|1.35|-0.62|25.33|24.18|50.49|

S-present minus S-absent: Bad10 +3.08 percentage points, descriptive 95% interval [-3.17, 9.56]; excess63 -1.78 points [-3.30, -0.22]; win -7.33 points [-14.27, -0.64]; lower-first +5.89 points [0.59, 10.44]. This is contrary to the hypothesis, not proof that resilience causes losses. Intervals use the fixed 12-month block bootstrap and are unadjusted for multiple comparisons.

Across all retained candidates, S has 3,944 events and no-S 4,851. Bad10 difference +1.37 points [-1.86, 4.43]; excess63 -0.11 [-0.68, 0.43]; win -3.13 [-6.04, 0.08]; lower-first +0.69 [-1.75, 3.43].

U within R selects 1,191 events versus 454. Its Bad10 difference is +2.17 points [-3.69, 8.22]; excess63 -0.57 [-2.07, 0.79]; win -0.07 [-5.69, 5.90]; lower-first +1.50 [-3.63, 6.29]. U is a comparator, not a logically inert placebo.

## Same-month and same-R matching

Within R, the six-feature caliper retained only 276 pairs across 94 months, using 155 unique controls: 22.55% of S events. Features: log volatility, drawdown, distance from low, relative126, absolute21 return, old beta. Remaining standardized mean imbalance was -0.0945, 0.0045, 0.0088, -0.0193, 0.0823 and -0.0068, respectively. The narrow common-support population differs from the full sample.

| Matched S difference within R | Estimate, pp | Descriptive 95% interval, pp |
|---|---:|---:|
| Win | -3.62 | [-12.22, 4.76] |
| Bad10 | 1.81 | [-2.78, 6.34] |
| Net63 / excess63 | 1.20 | [-0.02, 2.63] |
| Net21 | 0.45 | [-0.27, 1.17] |
| Mean MAE | 0.25 | [-0.42, 0.96] |
| Upper first | 3.62 | [-1.33, 8.57] |
| Lower first | 1.09 | [-3.24, 5.70] |
| Unresolved | -4.71 | [-11.76, 1.67] |

Matched group wins are 64.86% versus 68.48%; Bad10 25.00% versus 23.19%. The positive matched mean-return difference must not be selected while hiding its uncertainty, sparse retention or missing tail-risk improvement.

Across both R states with exact same-R matching, 1,667 pairs span 436 months, 1,142 unique controls, 42.27% S retention. Win difference -1.68 points [-4.63, 1.72]; Bad10 +0.06 [-2.24, 2.43]; excess63 +0.60 [-0.13, 1.34]; lower-first -1.08 [-3.32, 1.17]. No clear incremental protection emerges.

## All planned market-state cells

All figures in percent; M is a price-state descriptor, not a retrospectively named macro regime.

| S | R | M | N | Months | Win | Bad10 | Net63 | Excess63 | Upper | Lower | Unresolved |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|0|0|0|1544|387|57.06|32.25|2.00|-0.35|29.34|28.11|42.55|
|0|0|1|2886|303|59.25|35.07|4.30|-0.16|30.01|25.92|44.07|
|0|1|0|179|107|63.69|35.75|5.43|2.01|26.82|22.35|50.84|
|0|1|1|242|98|61.16|30.17|4.32|0.53|22.73|15.29|61.98|
|1|0|0|959|344|49.74|35.87|0.16|-1.14|29.09|29.61|41.29|
|1|0|1|1761|292|59.45|34.81|4.80|0.57|32.20|26.75|41.06|
|1|1|0|644|208|55.43|36.49|0.82|-1.16|26.09|27.02|46.89|
|1|1|1|580|156|54.31|34.66|1.95|-0.02|24.48|21.03|54.48|

## Historical-beta cells within R

| S | Beta >= 1 | N | Months | Win % | Bad10 % | Net63 % | Excess63 % | Upper % | Lower % | Unresolved % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|0|0|150|111|62.67|30.00|4.27|0.69|18.67|18.00|63.33|
|0|1|271|145|61.99|33.95|5.08|1.42|27.68|18.45|53.87|
|1|0|511|236|56.75|31.12|2.13|-0.38|28.38|20.74|50.88|
|1|1|713|276|53.58|38.85|0.80|-0.80|23.14|26.65|50.21|

## Era diagnostics within R

| Era | S | N | Months | Win % | Bad10 % | Net63 % | Excess63 % | Lower-first % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|1927-1962|0|189|93|56.08|39.15|4.65|1.58|20.11|
|1927-1962|1|479|148|48.43|45.30|-1.34|-0.94|29.85|
|1963-1982|0|114|54|69.30|25.44|5.48|0.84|19.30|
|1963-1982|1|381|103|53.81|35.43|1.18|-0.68|28.61|
|1983-2002|0|118|58|65.25|28.81|4.37|0.80|14.41|
|1983-2002|1|364|113|64.56|23.08|5.08|-0.14|12.09|

A favourable modern-era Bad10 comparison does not rescue a selected rule. No new period, threshold, direction or feature combination is promoted from this table.

## Additional arithmetic verification

Process 35906 exited 0. With fixed seed 2047, 32 sampled event paths were recomputed independently from direct cumulative products of simple returns, verifying next-session entry, exactly 63 subsequent returns, 21- and 63-session net returns, market excess, maximum closing loss and Bad10. Rolling63 sigma matched direct sample standard deviation. Thirty-two frozen historical betas matched a separate numpy.linalg.lstsq implementation. Input hashes and both original result hashes were unchanged. This is author self-checking, not an independent reviewer or proof of original-vintage data quality.

## Adjudication

Do not add this S proxy as a validated positive gate or flip its sign into an inverse signal. A positive market-model residual is not evidence that cash-flow damage has stopped, that funding stress has ended, or that economic peers have repaired. Those variables were not observed here. The useful output is a tested falsifier and a narrower next experiment: distinguish the cause and transmission of the decline using point-in-time non-price information, while retaining exact original timer events and comparable risk/coverage.
