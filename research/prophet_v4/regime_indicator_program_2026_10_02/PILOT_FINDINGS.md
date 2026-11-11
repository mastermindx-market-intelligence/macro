# Prophet continuation findings: identity, calendar, and regime pilot

Evidence class: EXPLORATORY / RETROSPECTIVE. No live strategy, rank, gate, sizing, trade, publisher or calendar changed. Full Prophet/all-weather mission remains incomplete. These results extend, rather than replace, MASTER_PLAN and the original R0 evidence.

## What actually ran

Exact code: `0b0bc00c5efae74618824581639f7bfa7c8e190b`.
Saved macro/data source: `b4f95f98ef80b8cbb4636afbd723b5091658e1f1`.
Original pre-analysis specification: `8bc732d4c15c020bcafe068a9fad8a096e9d6e5e`.
Pre-outcome calendar amendment: `8431a5452f561caafd60277c9393aa9260a5983b`.
The original 2006-start run stopped before event or return calculation. The amended run retained the hard calendar check and begins January 3, 2007. See CALENDAR_PILOT_AMENDMENT.md; the excluded 2006 interval is not silently restored.

The amended run calculated 2,730 raw bullish-cross events in QQQ, IWM and SOXX over 2007-2025, on 1,458 distinct signal dates, 2,176 distinct instrument-entry pairs, 227 entry months and 76 entry quarters. All events matured and passed exact entry/exit-price checks; no event had a missing mathematical regime state. These are NOT 2,730 independent trades or a portfolio backtest. Early period had 1,149 events; later period 1,581. Actual signal bounds were 2007-01-04 through 2025-12-29.

Entry: next SPY session CLOSE after the signal label. Exit: ten SPY sessions after entry. Assumed round-trip cost: 0.20 percentage points, charged once. The source `close` field is used unchanged; this is saved historical price-source evidence, not a certification of point-in-time adjustment or execution availability. September 2026 outcomes were not calculated in this pilot.

States use only inputs ending strictly before the signal label: five-SPY-session change in 10Y real yield and five-session RSP return minus SPY return. Hidden-fragility shorthand means rising real yield plus negative participation spread; relief/broadening means non-rising real yield plus nonnegative participation spread. Mixed states remain in the output. These two proxies are NOT a complete macro regime or observed institutional capital flow.

## Primary results: no universal 3D failure

Each cell below reports mean ten-session SPY-excess return after the declared cost. Difference = hidden minus relief, in percentage points. Intervals are descriptive 95% joint entry-quarter bootstrap intervals, 1,000 draws, seed 20261003. They are not multiplicity-adjusted strategy-promotion tests.

| Input / native kernel | Grain | Hidden N | Relief N | Hidden excess % | Relief excess % | Difference pp | 95% interval pp |
|---|---:|---:|---:|---:|---:|---:|---|
| Price MACD 12/26/9 | 1D | 113 | 176 | -0.0670 | -0.1773 | +0.1103 | [-0.5971, +0.7892] |
| Price MACD 12/26/9 | 2D | 65 | 94 | -0.0647 | +0.1389 | -0.2036 | [-0.9868, +0.5522] |
| Price MACD 12/26/9 | 3D | 49 | 56 | +0.1251 | -0.0212 | +0.1462 | [-0.9687, +1.1271] |
| Price MACD 12/26/9 | 1W | 20 | 45 | +1.0629 | -0.5236 | +1.5865 | [+0.4074, +2.8974] |
| RSI14 -> MACD 14/60/5 | 1D | 147 | 211 | -0.0987 | -0.0756 | -0.0231 | [-0.5183, +0.4891] |
| RSI14 -> MACD 14/60/5 | 2D | 86 | 85 | -0.0805 | -0.3712 | +0.2907 | [-0.4281, +1.0354] |
| RSI14 -> MACD 14/60/5 | 3D | 55 | 94 | -0.3441 | +0.5450 | -0.8891 | [-1.8486, +0.0753] |
| RSI14 -> MACD 14/60/5 | 1W | 33 | 43 | -0.1632 | -0.0726 | -0.0907 | [-1.2151, +1.0423] |

The pre-specified difference-in-differences, (3D hidden-minus-relief) minus (1D hidden-minus-relief):

| Family | 2007-2014 | 2015-2025 | Combined | Combined 95% interval |
|---|---:|---:|---:|---|
| Price MACD | +0.3521 pp | -0.1912 pp | +0.0359 pp | [-1.2848, +1.1990] |
| RSI-MACD | -0.4718 pp | -1.0992 pp | -0.8660 pp | [-1.8181, +0.0929] |

Interpretation: the price-MACD test does not support a general 3D disadvantage under these conditions. RSI-MACD has a negative, era-consistent point estimate, but both the direct 3D regime contrast and its 3D-versus-1D interaction still include zero. This warrants a targeted independent test, NOT a validated live regime switch. Raw event populations differ by policy; these are not paired identical admission dates and do not establish causality.

For RSI-MACD 3D, net ASSET return was -0.5392% in the hidden state versus +1.3700% in relief; positive net-asset fractions were 54.5% and 68.1%. Part of the raw gap is the market itself, which is why the benchmark-relative interaction is essential. These are not Prophet's candidate win rates.

## Heterogeneity diagnostic: retain the counterexamples

A subsequent, explicitly post-pilot descriptive check used the already-calculated events; no new sources or outcome windows were selected. The 3D RSI-MACD hidden-minus-relief excess differences were QQQ -0.4778 pp (20 versus 27 events), IWM -0.9476 pp (13 versus 33), and SOXX -1.1907 pp (22 versus 34). Equal ETF weighting gives -0.8720 pp, close to the event-pooled -0.8891 pp. That reduces the concern that the pooled sign is solely an ETF-mixture artifact, but these are correlated instruments with small cells, not three independent replications.

The conspicuously positive weekly price-MACD contrast is NOT a reliable universal weekly rule. Its individual differences were QQQ -0.0379 pp, IWM -0.2170 pp, SOXX +3.6189 pp. The hidden-state cell includes only three IWM events and six QQQ events. Early-period weekly contrast failed the predeclared sample-support floor. We retain this result rather than promoting the most attractive cell.

## The indicator identity problem is real; its performance impact is not established

Pinned native source shows three different species:
- `engine/technicals.macd_hist`: price MACD 12/26/9.
- `engine/confluence_tiers._rsi_macd`: RSI14 first, then EMA14 minus EMA60, signal EMA5.
- Terminal MACD Ultimate at `c35b9a1d50ca4960c361645f0300fa9f95158a4e`: price MACD normalized on a trailing window, with its signal on the normalized curve.

Macro's RSI and EMA use pandas adjusted EWM initialization. Terminal's shared primitives use SMA-seeded Wilder RMA / recursive EMA. In isolated native-excerpt synthetic tests, a 512-sample uninterrupted advance or flat series yielded zero finite Macro RSI values versus 498 Terminal RSI values of 100 or 50. This documents the primitive's zero-loss/flat handling, NOT a claim that real candidates experience 512 uninterrupted rises or that every caller passes such input.

On the oscillating fixture, replacing Macro primitives with the Terminal primitive recipe produced numerical differences but NO mature RSI-MACD upcross-date changes after index 80. Histogram differences declined from at most 0.2850 after index 80 to 0.000004679 after index 400. Thus the probe does not explain Prophet's losses. Actual MACD Ultimate was not executed by this hypothetical substitution.

Warm-up floor is not convergence: computing the same fixture's final RSI-MACD value from only 80, 160, 232 and 400 native input bars differed from the 512-bar calculation by approximately 0.99185, 0.01284, 0.001027 and 0.000002465 respectively. These are case measurements, not a universal 400-bar warm-up prescription.

A second confound remains in the ETF comparison: input transformation AND kernel parameters differ. For an EMA span N, asymptotic half-life is ln(0.5)/ln(1-2/(N+1)) native observations. The slow price-MACD span26 is about 9.006 bars; the RSI-MACD span60 is about 20.792 bars. On 3-session bars these correspond to about 27.02 versus 62.38 exchange sessions before accounting for RSI preprocessing and the other filters. Half-life is not fixed signal delay; nonlinear and cascaded filters cannot be made equivalent simply by matching one half-life.

Consequently the next scientific ablation must separate input transformation, kernel memory, sampling grain, observation basis and decision policy. A timeframe-only router would hide exactly the differences this continuation exposed.

## Engineering changes and evidence

Published: native primitive probe + 10 tests; frozen ETF pilot + 19 tests; Test-prefixed names for all prior 48 intake/observation tests. The class renames repair the HOUSE discovery heuristic; pytest already supports unittest.TestCase regardless of that naming issue.

Hash-verified connected-host execution at `0b0bc00c5efae74618824581639f7bfa7c8e190b`: **77 tests passed**. Earlier 77 at `0afd2bdb222313ca5663d9506c6bf36e9e1cb699` predate the calendar amendment and remain separately identified. Local 29 new-suite tests also passed; do not sum repeated environments as independent tests. No hosted-CI execution or independent scientific acceptance is inferred.

The first calendar run found the omitted January 2, 2007 closure. Adding that date can shift later absolute-session 2D/3D buckets. It is an existing-owner version/migration obligation, not permission to change production here. Current slice invariance remains 0/60 in R0 and is not contradicted: invariance and calendar truth test different properties.

Independent reviewer comment `5965501070` on #8303 demonstrated that green CI did not run the old 48 tests. Prefix repair is done; explicit enrollment in the existing `gate: code` `unrun-factor-research` lane and exact-head selection/execution proof remain owed. No new workflow or shadow CI controller is proposed.

## Reproducibility receipts

Full amended output (2,730 events, 96 state/period cells, 30 contrasts, 10 input hashes):
`/Volumes/Mastermind/research/prophet-regime-indicator-program-20261002/pilot-0b0bc00c5efa/etf-pilot-v2.json`
Bytes: 1,591,356. SHA-256: `ce0abe8268301b7f3ac9dee5dc6807e79d1644dd689007b29b2195197a402b9e`.

Post-pilot heterogeneity output in the same directory: `etf-heterogeneity-diagnostic.json`, SHA-256 `627982f0aedfb17917ae08622df3bd95c68c23421bb82eaf17cfec8b1149981f`.

The directory retains exact source-manifest, unit-tests, pilot-run and result-receipt files. Amended pilot source SHA-256 `11aca84c03bb6ffed4baedba35c81048d918aeff79379f5e484933b468f87abf`; Git blob `55fa6488f0cda2288a7a85f74a700d05db2425de`.

Native primitive source Git blob `c985d93bb47e0cb61e41147473ebd7887abe4ec8`; test blob `e6a604ebf100a11a5384c24b651436825f49a0f7`. Local synthetic result SHA-256 `82590ae10f6507cd9f35ce968f2c2213192800036c77bbde49c97145dfe291bd`; this hash denotes the original local report, not a claimed production artifact.

## What changes in the master program

No blanket 3D removal, 1D replacement, daily-overbought veto, weekly promotion, or semiconductor-only rule is earned here. Keep the candidate-selection baseline unchanged.

Prioritize R1 exact species/observation/calendar contracts and R2 full-window historical regime and PIT membership qualification. For R3, use a small predeclared factorial comparison of input transformation and kernel memory before expanding through the existing indicator catalog. Compare validated Prophet takes on point-in-time candidate populations, not just raw crosses or later-selected winners. Test fresh 2D inside constructive older 3D as its own sequence hypothesis; the present raw-cross pilot neither proves nor rejects that rule.

For the eventual strategy router, distinguish persistent concentration from rapid leadership turnover, growth-supported falling rates from recessionary rate declines, and market risk from opportunity-set breadth. These are proposed discriminating coordinates for the existing regime/PFI/GMI owners, not measured alpha from this pilot. Preserve long-cycle capture alongside any separately validated tactical sleeve.

Next acceptance requires independent scientific/code review, automatic test enrollment, source-window qualification, matched-population comparisons, cost/exposure-matched portfolio evidence and prospective checks through the existing owners. A favorable descriptive table cannot authorize a live change.
