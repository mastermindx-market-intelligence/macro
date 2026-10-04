# TTI R1-B v4 — registered retrospective result

Disposition: **NO_PROMOTION**

Corrected-history exploratory research only. No rank, alert, sizing or trade authority; no production signal can be promoted from this batch regardless of outcome.

## Identity

- study_id: `tti-r1b-exhaustion-reclaim-v4`
- code_sha: `13caccc4cd7c949dae75ed5f1ab85b7627c5311e`
- prereg_sha256: `a8afab8d87cfe912aeaed02c105112869943433cf6b7bb7c765bd2768d0dfcd3`
- config_sha256: `24b5a89f8df9c441160f1162c0f08d62796e842e29fff3c55766160fe388bc19`
- rulings_sha256: `73e1713f19f0edfe886b414f0cf90b5f829b29cf4662d0993c61d351c4230c84`
- grid_sha256: `151c0cb20af85537287413b4ecdeaf2ccad18232ed4eb0a20091cbd46cdb6b17`
- registered_rows_sha256: `8fc5a844886cfa2d69ec25f38fd6948b4a4556e01829bea76338e94570def281`
- input_manifest_sha256: `59c50ed405bd76c083a1d2beb20cf25edd6f4bd892c3e55fd38d21a66bef642b`
- prior attempts before this run: 1

## Gate — EXHAUSTION_RECLAIM at 60m / 25 bp, all four readings

| reading | fires with delta | dates | tickers | statistic | interval low | interval high | early | late | counts | interval > 0 | same sign | concentration | mechanical pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L-A | 52 | 40 | 8 | -0.000226 | -0.002206 | 0.001921 | -0.000226 | — | no | no | no | yes | no |
| L-B | 52 | 40 | 8 | -0.000226 | -0.002206 | 0.001921 | -0.000226 | — | no | no | no | yes | no |
| S-A | 52 | 40 | 8 | -0.000226 | -0.002206 | 0.001921 | -0.000226 | — | no | no | no | yes | no |
| S-B | 52 | 40 | 8 | -0.000226 | -0.002206 | 0.001921 | -0.000226 | — | no | no | no | yes | no |

Gate bullet 5 (no systematic admission artifact) is not mechanical: `REQUIRES_ADJUDICATION` by an independent reviewer.

## Matched delta, stated once per selector and horizon

The selected event and its controls carry the same round-trip cost, so the matched delta does not depend on the cost cell. The last column prints whether that held.

| selector | horizon | L-A | L-B | S-A | S-B | identical across costs |
|---|---|---|---|---|---|---|
| BASE_FRESH_LOW | 30m | -0.000007 | -0.000007 | -0.000007 | -0.000007 | yes/yes/yes/yes |
| BASE_FRESH_LOW | 60m | -0.000212 | -0.000212 | -0.000212 | -0.000212 | yes/yes/yes/yes |
| BASE_FRESH_LOW | 120m | -0.000729 | -0.000729 | -0.000729 | -0.000729 | yes/yes/yes/yes |
| BASE_FRESH_LOW | close | -0.001087 | -0.001087 | -0.001087 | -0.001087 | yes/yes/yes/yes |
| EXHAUSTION_FORMING | 30m | 0.000499 | 0.000499 | 0.000499 | 0.000499 | yes/yes/yes/yes |
| EXHAUSTION_FORMING | 60m | 0.000589 | 0.000589 | 0.000589 | 0.000589 | yes/yes/yes/yes |
| EXHAUSTION_FORMING | 120m | 0.000751 | 0.000751 | 0.000751 | 0.000751 | yes/yes/yes/yes |
| EXHAUSTION_FORMING | close | 0.001500 | 0.001500 | 0.001500 | 0.001500 | yes/yes/yes/yes |
| RECLAIM_ONLY | 30m | -0.000116 | -0.000116 | -0.000116 | -0.000116 | yes/yes/yes/yes |
| RECLAIM_ONLY | 60m | 0.000013 | 0.000013 | 0.000013 | 0.000013 | yes/yes/yes/yes |
| RECLAIM_ONLY | 120m | -0.000216 | -0.000216 | -0.000216 | -0.000216 | yes/yes/yes/yes |
| RECLAIM_ONLY | close | -0.000532 | -0.000532 | -0.000532 | -0.000532 | yes/yes/yes/yes |
| EXHAUSTION_RECLAIM | 30m | -0.000088 | -0.000088 | -0.000088 | -0.000088 | yes/yes/yes/yes |
| EXHAUSTION_RECLAIM | 60m | -0.000226 | -0.000226 | -0.000226 | -0.000226 | yes/yes/yes/yes |
| EXHAUSTION_RECLAIM | 120m | 0.000313 | 0.000313 | 0.000313 | 0.000313 | yes/yes/yes/yes |
| EXHAUSTION_RECLAIM | close | 0.000619 | 0.000619 | 0.000619 | 0.000619 | yes/yes/yes/yes |
| CONTINUATION_RISK | 30m | -0.001050 | -0.001050 | -0.001050 | -0.001050 | yes/yes/yes/yes |
| CONTINUATION_RISK | 60m | -0.002337 | -0.002337 | -0.002337 | -0.002337 | yes/yes/yes/yes |
| CONTINUATION_RISK | 120m | -0.000471 | -0.000471 | -0.000471 | -0.000471 | yes/yes/yes/yes |
| CONTINUATION_RISK | close | 0.000682 | 0.000682 | 0.000682 | 0.000682 | yes/yes/yes/yes |

## All 60 registered cells

Counts are per cell; the selected events' own net beta-residual mean is event-weighted and descriptive. Reading shown for the delta columns: L-A.

| selector | horizon | cost bp | fires | available | censored | no control | fires with delta | mean net return | mean net beta residual | matched delta |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE_FRESH_LOW | 30m | 10 | 616 | 616 | 0 | 463 | 145 | -0.000617 | -0.000711 | -0.000007 |
| BASE_FRESH_LOW | 30m | 25 | 616 | 616 | 0 | 463 | 145 | -0.002117 | -0.002211 | -0.000007 |
| BASE_FRESH_LOW | 30m | 50 | 616 | 616 | 0 | 463 | 145 | -0.004617 | -0.004711 | -0.000007 |
| BASE_FRESH_LOW | 60m | 10 | 616 | 616 | 0 | 463 | 145 | -0.000397 | -0.000576 | -0.000212 |
| BASE_FRESH_LOW | 60m | 25 | 616 | 616 | 0 | 463 | 145 | -0.001897 | -0.002076 | -0.000212 |
| BASE_FRESH_LOW | 60m | 50 | 616 | 616 | 0 | 463 | 145 | -0.004397 | -0.004576 | -0.000212 |
| BASE_FRESH_LOW | 120m | 10 | 616 | 603 | 13 | 463 | 145 | 0.000263 | -0.000462 | -0.000729 |
| BASE_FRESH_LOW | 120m | 25 | 616 | 603 | 13 | 463 | 145 | -0.001237 | -0.001962 | -0.000729 |
| BASE_FRESH_LOW | 120m | 50 | 616 | 603 | 13 | 463 | 145 | -0.003737 | -0.004462 | -0.000729 |
| BASE_FRESH_LOW | close | 10 | 616 | 616 | 0 | 463 | 145 | 0.000524 | 0.000018 | -0.001087 |
| BASE_FRESH_LOW | close | 25 | 616 | 616 | 0 | 463 | 145 | -0.000976 | -0.001482 | -0.001087 |
| BASE_FRESH_LOW | close | 50 | 616 | 616 | 0 | 463 | 145 | -0.003476 | -0.003982 | -0.001087 |
| EXHAUSTION_FORMING | 30m | 10 | 352 | 352 | 0 | 294 | 56 | -0.001119 | -0.000851 | 0.000499 |
| EXHAUSTION_FORMING | 30m | 25 | 352 | 352 | 0 | 294 | 56 | -0.002619 | -0.002351 | 0.000499 |
| EXHAUSTION_FORMING | 30m | 50 | 352 | 352 | 0 | 294 | 56 | -0.005119 | -0.004851 | 0.000499 |
| EXHAUSTION_FORMING | 60m | 10 | 352 | 352 | 0 | 294 | 56 | -0.001048 | -0.000704 | 0.000589 |
| EXHAUSTION_FORMING | 60m | 25 | 352 | 352 | 0 | 294 | 56 | -0.002548 | -0.002204 | 0.000589 |
| EXHAUSTION_FORMING | 60m | 50 | 352 | 352 | 0 | 294 | 56 | -0.005048 | -0.004704 | 0.000589 |
| EXHAUSTION_FORMING | 120m | 10 | 352 | 344 | 8 | 294 | 56 | -0.000596 | -0.000615 | 0.000751 |
| EXHAUSTION_FORMING | 120m | 25 | 352 | 344 | 8 | 294 | 56 | -0.002096 | -0.002115 | 0.000751 |
| EXHAUSTION_FORMING | 120m | 50 | 352 | 344 | 8 | 294 | 56 | -0.004596 | -0.004615 | 0.000751 |
| EXHAUSTION_FORMING | close | 10 | 352 | 352 | 0 | 294 | 56 | 0.000124 | -0.000260 | 0.001500 |
| EXHAUSTION_FORMING | close | 25 | 352 | 352 | 0 | 294 | 56 | -0.001376 | -0.001760 | 0.001500 |
| EXHAUSTION_FORMING | close | 50 | 352 | 352 | 0 | 294 | 56 | -0.003876 | -0.004260 | 0.001500 |
| RECLAIM_ONLY | 30m | 10 | 577 | 577 | 0 | 463 | 108 | -0.000801 | -0.001027 | -0.000116 |
| RECLAIM_ONLY | 30m | 25 | 577 | 577 | 0 | 463 | 108 | -0.002301 | -0.002527 | -0.000116 |
| RECLAIM_ONLY | 30m | 50 | 577 | 577 | 0 | 463 | 108 | -0.004801 | -0.005027 | -0.000116 |
| RECLAIM_ONLY | 60m | 10 | 577 | 577 | 0 | 463 | 108 | -0.000509 | -0.000641 | 0.000013 |
| RECLAIM_ONLY | 60m | 25 | 577 | 577 | 0 | 463 | 108 | -0.002009 | -0.002141 | 0.000013 |
| RECLAIM_ONLY | 60m | 50 | 577 | 577 | 0 | 463 | 108 | -0.004509 | -0.004641 | 0.000013 |
| RECLAIM_ONLY | 120m | 10 | 577 | 564 | 13 | 463 | 108 | 0.000187 | -0.000654 | -0.000216 |
| RECLAIM_ONLY | 120m | 25 | 577 | 564 | 13 | 463 | 108 | -0.001313 | -0.002154 | -0.000216 |
| RECLAIM_ONLY | 120m | 50 | 577 | 564 | 13 | 463 | 108 | -0.003813 | -0.004654 | -0.000216 |
| RECLAIM_ONLY | close | 10 | 577 | 577 | 0 | 463 | 108 | 0.000534 | -0.000056 | -0.000532 |
| RECLAIM_ONLY | close | 25 | 577 | 577 | 0 | 463 | 108 | -0.000966 | -0.001556 | -0.000532 |
| RECLAIM_ONLY | close | 50 | 577 | 577 | 0 | 463 | 108 | -0.003466 | -0.004056 | -0.000532 |
| EXHAUSTION_RECLAIM | 30m | 10 | 319 | 319 | 0 | 265 | 52 | -0.000998 | -0.000706 | -0.000088 |
| EXHAUSTION_RECLAIM | 30m | 25 | 319 | 319 | 0 | 265 | 52 | -0.002498 | -0.002206 | -0.000088 |
| EXHAUSTION_RECLAIM | 30m | 50 | 319 | 319 | 0 | 265 | 52 | -0.004998 | -0.004706 | -0.000088 |
| EXHAUSTION_RECLAIM | 60m | 10 | 319 | 319 | 0 | 265 | 52 | -0.000986 | -0.000569 | -0.000226 |
| EXHAUSTION_RECLAIM | 60m | 25 | 319 | 319 | 0 | 265 | 52 | -0.002486 | -0.002069 | -0.000226 |
| EXHAUSTION_RECLAIM | 60m | 50 | 319 | 319 | 0 | 265 | 52 | -0.004986 | -0.004569 | -0.000226 |
| EXHAUSTION_RECLAIM | 120m | 10 | 319 | 311 | 8 | 265 | 52 | -0.000549 | -0.000535 | 0.000313 |
| EXHAUSTION_RECLAIM | 120m | 25 | 319 | 311 | 8 | 265 | 52 | -0.002049 | -0.002035 | 0.000313 |
| EXHAUSTION_RECLAIM | 120m | 50 | 319 | 311 | 8 | 265 | 52 | -0.004549 | -0.004535 | 0.000313 |
| EXHAUSTION_RECLAIM | close | 10 | 319 | 319 | 0 | 265 | 52 | 0.000285 | 0.000024 | 0.000619 |
| EXHAUSTION_RECLAIM | close | 25 | 319 | 319 | 0 | 265 | 52 | -0.001215 | -0.001476 | 0.000619 |
| EXHAUSTION_RECLAIM | close | 50 | 319 | 319 | 0 | 265 | 52 | -0.003715 | -0.003976 | 0.000619 |
| CONTINUATION_RISK | 30m | 10 | 52 | 52 | 0 | 41 | 10 | -0.001138 | -0.000929 | -0.001050 |
| CONTINUATION_RISK | 30m | 25 | 52 | 52 | 0 | 41 | 10 | -0.002638 | -0.002429 | -0.001050 |
| CONTINUATION_RISK | 30m | 50 | 52 | 52 | 0 | 41 | 10 | -0.005138 | -0.004929 | -0.001050 |
| CONTINUATION_RISK | 60m | 10 | 52 | 52 | 0 | 41 | 10 | 0.000971 | -0.000260 | -0.002337 |
| CONTINUATION_RISK | 60m | 25 | 52 | 52 | 0 | 41 | 10 | -0.000529 | -0.001760 | -0.002337 |
| CONTINUATION_RISK | 60m | 50 | 52 | 52 | 0 | 41 | 10 | -0.003029 | -0.004260 | -0.002337 |
| CONTINUATION_RISK | 120m | 10 | 52 | 51 | 1 | 41 | 10 | 0.004688 | 0.001283 | -0.000471 |
| CONTINUATION_RISK | 120m | 25 | 52 | 51 | 1 | 41 | 10 | 0.003188 | -0.000217 | -0.000471 |
| CONTINUATION_RISK | 120m | 50 | 52 | 51 | 1 | 41 | 10 | 0.000688 | -0.002717 | -0.000471 |
| CONTINUATION_RISK | close | 10 | 52 | 52 | 0 | 41 | 10 | 0.006727 | 0.001933 | 0.000682 |
| CONTINUATION_RISK | close | 25 | 52 | 52 | 0 | 41 | 10 | 0.005227 | 0.000433 | 0.000682 |
| CONTINUATION_RISK | close | 50 | 52 | 52 | 0 | 41 | 10 | 0.002727 | -0.002067 | 0.000682 |

## Coverage

| symbol | rows | complete sessions | incomplete | prefix-incomplete | row cap reached | sessions before first bar |
|---|---|---|---|---|---|---|
| AMD | 60000 | 312 | 0 | 0 | yes | 0 |
| NVDA | 60000 | 312 | 0 | 0 | yes | 0 |
| MU | 60000 | 312 | 0 | 0 | yes | 0 |
| AVGO | 58775 | 312 | 0 | 0 | no | 0 |
| QCOM | 44309 | 312 | 0 | 0 | no | 0 |
| AAPL | 59603 | 312 | 0 | 0 | no | 0 |
| JPM | 40769 | 312 | 0 | 0 | no | 0 |
| XOM | 43672 | 312 | 0 | 0 | no | 0 |
| QQQ | 60000 | 312 | 0 | — | yes | 0 |

## Limits

- Retrospective, current-universe, eight tickers; survivorship and composition limits apply.
- Historical per-bar availability, live fills and contemporaneous quotes are not proven.
- The 10/25/50 bp costs are sensitivities, not measured spreads.
- The early/late split is a stability split, not an untouched holdout.
- Event-, outcome- and match-level files and every licensed bar stay outside Git.
