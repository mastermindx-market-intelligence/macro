The price stores are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). This lane consumed the **B1 ROUND 3** panel (sha256 `209e224686955cf1…`, 296,637 1D rows; B1/RESULT.md records `k inverted`). **ANSWER FIRST:** SCOPED_NULL: no family×partition meets the winner rule (Holm-adjusted p<0.05, same sign in both eras, all eight era-cells above floor); 10/12 tests had all cells above floor.

## Answer first
**SCOPED_NULL** — SCOPED_NULL: no family×partition meets the winner rule (Holm-adjusted p<0.05, same sign in both eras, all eight era-cells above floor); 10/12 tests had all cells above floor

## Regime clock
regime_v2_pit.parquet row at date d carries features that use data THROUGH d: scripts/build_regime_v2_pit.py:376 `f_pit = build_features(overrides=overrides)`; engine/inputs.py:171 `idx = pd.bdate_range(closes.index.min(), end)` and :262-267 `basket_index(...).reindex(idx).ffill(limit=5)` (row d includes the closes at d); macro legs via pit_availability_panel (scripts/build_regime_v2_pit.py:103-105, as-of d by reindex+ffill). The E join is conservative: merge_asof direction='backward' with allow_exact_matches=False picks the strictly-prior row, so events at signal_date use regime data through ≤ signal_date − 1 calendar day.
Regime file index is business-daily 1971-01-04..2026-07-02 (14,479 rows). Late-2026 events whose prior regime row is older than 7 calendar days are dropped under `match_older_than_7d` because the PIT series ends on 2026-07-02 (K12).
Citations (verified by `test_regime_clock_citation_resolves`):
- `scripts/build_regime_v2_pit.py:376` `f_pit = build_features(overrides=overrides)`
- `engine/inputs.py:171` `idx = pd.bdate_range(closes.index.min(), end)`
- `engine/inputs.py:262` `basket_index(closes, g["cyclical_basket"]).reindex(idx).ffill(limit=5)`
- `scripts/build_regime_v2_pit.py:103` `def pit_availability_panel(vintages: pd.DataFrame, sid: str) -> pd.Series:`

## Design recap
- Primary outcome: `excess_h10_net` on `B1 events_panel.parquet with variant == '1D'`
- Secondary outcome: `excess_h21_net` on the same primary events
- Secondary set: 3D.p0-confirmed events joined to the 3D.p0 row
- Regime join: merge_asof direction=backward allow_exact_matches=False with fallback_max_days = 7
- Floors: eight (T1/T3 × state × era) cells; ≥ 300 events, ≥ 24 months, ≥ 100 names
- Inference: entry-month cluster resample WITH replacement, multiplicity weights (np.bincount), n_draws=1000, seed=20261004; per test (one month-draw sequence per test; not shared across the 12 tests)
- Verdict rule is in `result.json["verdict_rule"]` (written as a constant before any I is computed).

Participation survivorship caveat: the date-level share's denominator is names with a *valid* SMA50 on that date (warm-up NaNs excluded from both num and denom, K8). Names with no row on d are also excluded; the universe is current-membership only (survivor-selected).

## Tercile cuts (fixed, computed on the PRIMARY set)
| family | T1/T2 cut | T2/T3 cut |
|---|---:|---:|
| trend | -0.04932 | +0.09809 |
| momentum | -0.06812 | +0.22813 |
| compression | +0.80088 | +1.04462 |
| participation | +0.46829 | +0.63380 |
| rs | -0.07931 | +0.05123 |
| structure | -0.25974 | -0.08519 |

## The twelve primary tests (H10 net, primary 1D events)
| # | family | partition | I (obs) | 95% CI lo | 95% CI hi | SE | raw p | Holm p | era 2014-2019 | era 2020-2026 | same-sign | floor |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 1 | trend | P1_growth | +0.00227 | -0.00683 | +0.01028 | 0.00454 | 0.6160 | 1.0000 | +0.01138 | -0.00153 | no | PASS |
| 2 | trend | P2_stress | -0.00508 | -0.01184 | +0.00205 | 0.00348 | 0.1540 | 1.0000 | +0.00168 | -0.00791 | no | PASS |
| 3 | momentum | P1_growth | -0.00145 | -0.00979 | +0.00696 | 0.00434 | 0.8940 | 1.0000 | +0.01351 | -0.00780 | no | PASS |
| 4 | momentum | P2_stress | -0.00463 | -0.01185 | +0.00212 | 0.00362 | 0.1920 | 1.0000 | +0.00076 | -0.00694 | no | PASS |
| 5 | compression | P1_growth | -0.00160 | -0.00729 | +0.00474 | 0.00303 | 0.5340 | 1.0000 | -0.00250 | -0.00107 | yes | PASS |
| 6 | compression | P2_stress | +0.00230 | -0.00298 | +0.00787 | 0.00280 | 0.4600 | 1.0000 | -0.00169 | +0.00464 | no | PASS |
| 7 | participation | P1_growth | +0.00494 | -0.00672 | +0.01508 | 0.00566 | 0.3880 | 1.0000 | +0.00882 | +0.00387 | yes | FAIL |
| 8 | participation | P2_stress | +0.00024 | -0.00941 | +0.01006 | 0.00492 | 0.9440 | 1.0000 | -0.00428 | +0.00223 | no | FAIL |
| 9 | rs | P1_growth | +0.00043 | -0.00824 | +0.00825 | 0.00408 | 0.8580 | 1.0000 | +0.01067 | -0.00358 | no | PASS |
| 10 | rs | P2_stress | -0.00125 | -0.00712 | +0.00455 | 0.00299 | 0.6980 | 1.0000 | +0.00301 | -0.00285 | no | PASS |
| 11 | structure | P1_growth | +0.00213 | -0.00718 | +0.01152 | 0.00470 | 0.5980 | 1.0000 | +0.01250 | -0.00098 | no | PASS |
| 12 | structure | P2_stress | -0.00687 | -0.01453 | +0.00044 | 0.00390 | 0.0680 | 0.8160 | -0.00107 | -0.00814 | yes | PASS |

## Cell-level table (eight era cells per test; floors)

### trend
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 12,371 | 51 | 1,769 | -0.01184 | PASS |
| P1_growth | 2020-2026/T1/EXPANSION | 28,142 | 76 | 2,567 | -0.00510 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 16,416 | 45 | 1,869 | -0.00194 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 40,718 | 69 | 2,581 | -0.00871 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 17,309 | 51 | 1,873 | -0.00404 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 38,816 | 76 | 2,571 | -0.00471 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 13,239 | 45 | 1,852 | -0.00552 | PASS |
| P1_growth | 2020-2026/T3/CONTRACTION | 27,302 | 69 | 2,563 | -0.00679 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 16,135 | 53 | 1,859 | -0.00778 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 38,320 | 79 | 2,577 | -0.00314 | PASS |
| P2_stress | 2014-2019/T1/CALM | 12,652 | 48 | 1,857 | -0.00418 | PASS |
| P2_stress | 2020-2026/T1/CALM | 30,540 | 71 | 2,577 | -0.01237 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 19,378 | 53 | 1,877 | -0.00538 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 37,957 | 79 | 2,569 | -0.00500 | PASS |
| P2_stress | 2014-2019/T3/CALM | 11,170 | 48 | 1,826 | -0.00346 | PASS |
| P2_stress | 2020-2026/T3/CALM | 28,161 | 71 | 2,562 | -0.00632 | PASS |

### momentum
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 14,537 | 51 | 1,738 | -0.01325 | PASS |
| P1_growth | 2020-2026/T1/EXPANSION | 33,961 | 76 | 2,563 | -0.00400 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 14,106 | 45 | 1,737 | -0.00177 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 34,982 | 69 | 2,561 | -0.00946 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 15,425 | 51 | 1,814 | -0.00352 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 34,216 | 76 | 2,548 | -0.00739 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 15,175 | 45 | 1,841 | -0.00556 | PASS |
| P1_growth | 2020-2026/T3/CONTRACTION | 31,959 | 69 | 2,558 | -0.00505 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 15,916 | 53 | 1,745 | -0.00857 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 37,913 | 79 | 2,567 | -0.00277 | PASS |
| P2_stress | 2014-2019/T1/CALM | 12,727 | 48 | 1,725 | -0.00638 | PASS |
| P2_stress | 2020-2026/T1/CALM | 31,030 | 71 | 2,558 | -0.01166 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 20,248 | 53 | 1,855 | -0.00502 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 40,177 | 79 | 2,564 | -0.00550 | PASS |
| P2_stress | 2014-2019/T3/CALM | 10,352 | 48 | 1,771 | -0.00357 | PASS |
| P2_stress | 2020-2026/T3/CALM | 25,998 | 71 | 2,544 | -0.00745 | PASS |

### compression
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 18,164 | 51 | 1,930 | -0.00663 | PASS |
| P1_growth | 2020-2026/T1/EXPANSION | 34,358 | 76 | 2,586 | -0.00388 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 14,632 | 45 | 1,938 | -0.00450 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 30,446 | 69 | 2,584 | -0.00657 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 15,912 | 51 | 1,925 | -0.00654 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 26,688 | 76 | 2,585 | -0.00727 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 18,976 | 45 | 1,949 | -0.00191 | PASS |
| P1_growth | 2020-2026/T3/CONTRACTION | 35,754 | 69 | 2,585 | -0.00889 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 21,370 | 53 | 1,947 | -0.00599 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 36,951 | 79 | 2,586 | -0.00390 | PASS |
| P2_stress | 2014-2019/T1/CALM | 11,426 | 48 | 1,909 | -0.00510 | PASS |
| P2_stress | 2020-2026/T1/CALM | 27,853 | 71 | 2,585 | -0.00679 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 19,432 | 53 | 1,940 | -0.00516 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 34,500 | 79 | 2,585 | -0.00482 | PASS |
| P2_stress | 2014-2019/T3/CALM | 15,456 | 48 | 1,944 | -0.00259 | PASS |
| P2_stress | 2020-2026/T3/CALM | 27,942 | 71 | 2,586 | -0.01235 | PASS |

### participation
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 6,587 | 17 | 1,864 | -0.00695 | FAIL |
| P1_growth | 2020-2026/T1/EXPANSION | 13,046 | 38 | 2,553 | -0.00209 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 22,498 | 25 | 1,948 | -0.00002 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 56,748 | 46 | 2,586 | -0.00650 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 26,382 | 37 | 1,958 | -0.00725 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 49,612 | 50 | 2,586 | -0.00360 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 8,950 | 22 | 1,948 | -0.00913 | FAIL |
| P1_growth | 2020-2026/T3/CONTRACTION | 12,724 | 25 | 2,550 | -0.01189 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 14,469 | 27 | 1,910 | -0.00034 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 43,958 | 49 | 2,586 | -0.00466 | PASS |
| P2_stress | 2014-2019/T1/CALM | 14,616 | 20 | 1,944 | -0.00282 | FAIL |
| P2_stress | 2020-2026/T1/CALM | 25,836 | 37 | 2,583 | -0.00739 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 19,922 | 35 | 1,967 | -0.00851 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 31,113 | 44 | 2,585 | -0.00281 | PASS |
| P2_stress | 2014-2019/T3/CALM | 15,410 | 31 | 1,939 | -0.00670 | PASS |
| P2_stress | 2020-2026/T3/CALM | 31,223 | 40 | 2,585 | -0.00777 | PASS |

### rs
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 13,122 | 51 | 1,884 | -0.01185 | PASS |
| P1_growth | 2020-2026/T1/EXPANSION | 31,840 | 76 | 2,584 | -0.00320 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 14,452 | 45 | 1,903 | -0.00146 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 38,024 | 69 | 2,586 | -0.00804 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 17,075 | 51 | 1,907 | -0.00475 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 34,405 | 76 | 2,582 | -0.00676 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 15,059 | 45 | 1,923 | -0.00503 | PASS |
| P1_growth | 2020-2026/T3/CONTRACTION | 30,388 | 69 | 2,582 | -0.00802 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 16,185 | 53 | 1,918 | -0.00799 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 40,237 | 79 | 2,586 | -0.00289 | PASS |
| P2_stress | 2014-2019/T1/CALM | 11,389 | 48 | 1,880 | -0.00416 | PASS |
| P2_stress | 2020-2026/T1/CALM | 29,627 | 71 | 2,584 | -0.00983 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 19,823 | 53 | 1,928 | -0.00520 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 35,561 | 79 | 2,583 | -0.00550 | PASS |
| P2_stress | 2014-2019/T3/CALM | 12,311 | 48 | 1,889 | -0.00437 | PASS |
| P2_stress | 2020-2026/T3/CALM | 29,232 | 71 | 2,581 | -0.00960 | PASS |

### structure
| partition | cell | n_events | n_months | n_names | mean_y | floor |
|---|---|---:|---:|---:|---:|:---:|
| P1_growth | 2014-2019/T1/EXPANSION | 11,365 | 51 | 1,289 | -0.01535 | PASS |
| P1_growth | 2020-2026/T1/EXPANSION | 32,422 | 76 | 2,449 | -0.00608 | PASS |
| P1_growth | 2014-2019/T1/CONTRACTION | 13,404 | 45 | 1,511 | -0.00290 | PASS |
| P1_growth | 2020-2026/T1/CONTRACTION | 40,065 | 69 | 2,525 | -0.00903 | PASS |
| P1_growth | 2014-2019/T3/EXPANSION | 22,477 | 51 | 1,826 | -0.00283 | PASS |
| P1_growth | 2020-2026/T3/EXPANSION | 31,944 | 76 | 2,496 | -0.00377 | PASS |
| P1_growth | 2014-2019/T3/CONTRACTION | 18,220 | 45 | 1,798 | -0.00288 | PASS |
| P1_growth | 2020-2026/T3/CONTRACTION | 24,460 | 69 | 2,441 | -0.00574 | PASS |
| P2_stress | 2014-2019/T1/STRESSED | 13,857 | 53 | 1,384 | -0.00952 | PASS |
| P2_stress | 2020-2026/T1/STRESSED | 40,410 | 79 | 2,489 | -0.00359 | PASS |
| P2_stress | 2014-2019/T1/CALM | 10,912 | 48 | 1,479 | -0.00745 | PASS |
| P2_stress | 2020-2026/T1/CALM | 32,077 | 71 | 2,510 | -0.01290 | PASS |
| P2_stress | 2014-2019/T3/STRESSED | 26,080 | 53 | 1,837 | -0.00398 | PASS |
| P2_stress | 2020-2026/T3/STRESSED | 32,370 | 79 | 2,496 | -0.00412 | PASS |
| P2_stress | 2014-2019/T3/CALM | 14,617 | 48 | 1,771 | -0.00084 | PASS |
| P2_stress | 2020-2026/T3/CALM | 24,034 | 71 | 2,471 | -0.00530 | PASS |

## Winner block
No (f, P) meets the winner rule (SCOPED NULL if ≥8/12 tests above floor).

**Secondary (H21 net, same tests; era values K7):**
| family | partition | I (H21 obs) | CI lo | CI hi | SE | era 2014-2019 | era 2020-2026 |
|---|---|---:|---:|---:|---:|---:|---:|
| trend | P1_growth | +0.00875 | -0.00338 | +0.02058 | 0.00622 | +0.01252 | +0.00731 |
| trend | P2_stress | -0.00781 | -0.01817 | +0.00254 | 0.00544 | +0.00406 | -0.01286 |
| momentum | P1_growth | -0.00050 | -0.01231 | +0.01049 | 0.00592 | +0.01533 | -0.00732 |
| momentum | P2_stress | -0.00964 | -0.01912 | +0.00004 | 0.00498 | -0.00364 | -0.01236 |
| compression | P1_growth | -0.00033 | -0.00812 | +0.00873 | 0.00425 | -0.00109 | -0.00018 |
| compression | P2_stress | +0.00016 | -0.00789 | +0.00779 | 0.00394 | -0.00213 | +0.00135 |
| participation | P1_growth | +0.00044 | -0.01444 | +0.01660 | 0.00804 | -0.00170 | +0.00214 |
| participation | P2_stress | -0.00126 | -0.01447 | +0.01175 | 0.00700 | -0.00414 | -0.00025 |
| rs | P1_growth | +0.00288 | -0.00917 | +0.01456 | 0.00593 | +0.01192 | -0.00066 |
| rs | P2_stress | -0.00124 | -0.01040 | +0.00741 | 0.00449 | +0.00584 | -0.00394 |
| structure | P1_growth | +0.00838 | -0.00357 | +0.02009 | 0.00624 | +0.01494 | +0.00697 |
| structure | P2_stress | -0.00874 | -0.01833 | +0.00138 | 0.00523 | +0.00292 | -0.01275 |

**Secondary (3D.p0-confirmed set, H10; era values K7):**
| family | partition | I (obs) | CI lo | CI hi | SE | era 2014-2019 | era 2020-2026 |
|---|---|---:|---:|---:|---:|---:|---:|
| trend | P1_growth | +0.00523 | -0.00222 | +0.01276 | 0.00395 | +0.00314 | +0.00622 |
| trend | P2_stress | +0.00194 | -0.00564 | +0.00970 | 0.00394 | +0.01000 | -0.00164 |
| momentum | P1_growth | +0.00058 | -0.00725 | +0.00888 | 0.00408 | +0.01026 | -0.00403 |
| momentum | P2_stress | +0.00339 | -0.00425 | +0.01115 | 0.00398 | +0.00042 | +0.00440 |
| compression | P1_growth | +0.00235 | -0.00467 | +0.00897 | 0.00362 | +0.00131 | +0.00355 |
| compression | P2_stress | +0.00046 | -0.00656 | +0.00784 | 0.00376 | +0.00123 | -0.00003 |
| participation | P1_growth | +0.00255 | -0.00832 | +0.01365 | 0.00548 | +0.00360 | +0.00249 |
| participation | P2_stress | -0.00280 | -0.01334 | +0.00790 | 0.00539 | +0.00397 | -0.00555 |
| rs | P1_growth | +0.00348 | -0.00529 | +0.01277 | 0.00453 | +0.00419 | +0.00358 |
| rs | P2_stress | +0.00402 | -0.00260 | +0.01120 | 0.00345 | +0.00984 | +0.00171 |
| structure | P1_growth | +0.00234 | -0.00615 | +0.01035 | 0.00433 | +0.01137 | -0.00027 |
| structure | P2_stress | -0.00076 | -0.00892 | +0.00754 | 0.00426 | +0.00225 | -0.00092 |

## Regime main effect (context)
| partition | state | mean y | CI lo | CI hi | SE | n_events | n_months |
|---|---|---:|---:|---:|---:|---:|---:|
| P1_growth | EXPANSION | -0.00531 | -0.00915 | -0.00110 | 0.00203 | 144,519 | 127 |
| P1_growth | CONTRACTION | -0.00576 | -0.00954 | -0.00203 | 0.00191 | 147,422 | 114 |
| P2_stress | STRESSED | -0.00452 | -0.00748 | -0.00103 | 0.00165 | 170,272 | 132 |
| P2_stress | CALM | -0.00697 | -0.01066 | -0.00336 | 0.00190 | 121,669 | 119 |

## Family main effect spread(T3−T1) pooled across states (context)
| family | spread | CI lo | CI hi | SE | n_T3 | n_T1 |
|---|---:|---:|---:|---:|---:|---:|
| trend | +0.00164 | -0.00292 | +0.00628 | 0.00244 | 96,666 | 97,647 |
| momentum | +0.00130 | -0.00363 | +0.00596 | 0.00241 | 96,775 | 97,586 |
| compression | -0.00137 | -0.00491 | +0.00145 | 0.00163 | 97,330 | 97,600 |
| participation | -0.00170 | -0.00777 | +0.00466 | 0.00329 | 97,668 | 98,879 |
| rs | -0.00054 | -0.00487 | +0.00377 | 0.00220 | 96,927 | 97,438 |
| structure | +0.00406 | -0.00131 | +0.00923 | 0.00269 | 97,101 | 97,256 |

## Quad descriptive table
| quad | n_events | n_months | n_names | mean_h10_net |
|---|---:|---:|---:|---:|
| Q1 | 59,130 | 43 | 2,586 | -0.00593 |
| Q2 | 128,120 | 92 | 2,586 | -0.00634 |
| Q3 | 32,132 | 22 | 2,585 | -0.00512 |
| Q4 | 72,559 | 52 | 2,586 | -0.00400 |

## Context: recession / transition_ratcheted
- recession share (joined rows): **0.062159819963622784**
- transition_ratcheted share (joined rows): **0.23852764770963997**

## Drops by reason
| reason | n |
|---|---:|
| no_prior_regime_row | 0 |
| match_older_than_7d | 4,696 |
| regime_series_ended_late_2026 | 4,696 |
| feature_nan_trend | 0 |
| feature_nan_momentum | 0 |
| feature_nan_compression | 0 |
| feature_nan_participation | 0 |
| feature_nan_rs | 0 |
| feature_nan_structure | 0 |

## Round-0 vs round-1 (K10)
Round-0 verdict **INSUFFICIENT_SUPPORT** (0/12 above floor) was a code bug (K1 floor gate counted 6 pooled cells including T2). Panel swap r2→r3: −32 1D rows. max|ΔI| excluding participation = 1.46e-05 (structure × P1; within the ≲ 1.5e-05 panel-swap bound). Participation ΔI is larger (−8.61e-04 / +1.00e-04) because K8 changed the SMA50 denominator and therefore the participation tercile cuts. Remaining SE/p movement is the K2 with-replacement bootstrap repair (structure × P2: round-0 SE 0.00289 / p 0.014 → round-1 SE 0.00390 / p 0.068; reviewer reference SE ≈ 0.00383, p ≈ 0.058).
| family | partition | round0 I | round1 I | ΔI | round1 SE | round1 p | floor |
|---|---|---:|---:|---:|---:|---:|:---:|
| trend | P1_growth | +0.00227 | +0.00227 | -3.64108e-06 | 0.00454 | 0.6160 | PASS |
| trend | P2_stress | -0.00508 | -0.00508 | +7.06106e-06 | 0.00348 | 0.1540 | PASS |
| momentum | P1_growth | -0.00145 | -0.00145 | -7.75999e-07 | 0.00434 | 0.8940 | PASS |
| momentum | P2_stress | -0.00463 | -0.00463 | -4.83146e-06 | 0.00362 | 0.1920 | PASS |
| compression | P1_growth | -0.00160 | -0.00160 | -7.09957e-08 | 0.00303 | 0.5340 | PASS |
| compression | P2_stress | +0.00230 | +0.00230 | -1.92196e-06 | 0.00280 | 0.4600 | PASS |
| participation | P1_growth | +0.00580 | +0.00494 | -0.000860507 | 0.00566 | 0.3880 | FAIL |
| participation | P2_stress | +0.00014 | +0.00024 | +0.000100337 | 0.00492 | 0.9440 | FAIL |
| rs | P1_growth | +0.00044 | +0.00043 | -5.56008e-06 | 0.00408 | 0.8580 | PASS |
| rs | P2_stress | -0.00125 | -0.00125 | +3.09366e-06 | 0.00299 | 0.6980 | PASS |
| structure | P1_growth | +0.00215 | +0.00213 | -1.45594e-05 | 0.00470 | 0.5980 | PASS |
| structure | P2_stress | -0.00687 | -0.00687 | +5.88343e-06 | 0.00390 | 0.0680 | PASS |

## Verdict
**SCOPED_NULL** — reasons: no (f,P) meets the winner rule, 10/12 tests had all cells above floor

N tests with all eight era-cells above floor: **10 / 12**.
INSUFFICIENT tests and failing cells:
- participation × P1_growth: ['2014-2019/T1/EXPANSION', '2014-2019/T3/CONTRACTION']
- participation × P2_stress: ['2014-2019/T1/CALM']

## Tests
`17 passed`
Mutation B (resampler replaced by keep-all-months) fails `test_unclustered_resample_fails_cluster_invariant`. The pooled-6 floor mutant fails `test_floor_gate_counts_eight_cells`. The `np.isin` bootstrap mutant fails `test_cluster_bootstrap_matches_analytic_se`.
Two consecutive compute passes of the 12-test core: `cb16e951115df666c21ca164440b80e5beef9e3df9c982cde30a6998a471b92d` and `cb16e951115df666c21ca164440b80e5beef9e3df9c982cde30a6998a471b92d` (byte-identical=True).

## Provenance
Host `m2studio`; python `/opt/homebrew/opt/python@3.14/bin/python3.14` 3.14.7; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1. repo_head `052e02d085b01f29baf499357e224c836d8eb224`.

## K1–K12 repairs
- **K1** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/stats.py:168` — floors on eight T1/T3 × state × era cells; pooled-6 mutant in tests
- **K2** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/stats.py:330` — month multiplicity weights; isin mutant fails analytic-SE test
- **K3** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:138` — SeedSequence(20261004).spawn; no builtin hash(); two-pass sha recorded
- **K4** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:62` — hash at load and write-out; abort INPUT_CHANGED; pin 209e2246 / d20cd405
- **K5** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:75` — real citations; test_regime_clock_citation_resolves
- **K6** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/test_E.py:357` — unclustered SE ≥30% below clustered; mutation B keep-all fails the invariant
- **K7** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:273` — H21 and 3D.p0 secondary rows carry both era values
- **K8** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/features.py:119` — SMA50 NaN excluded from num and denom; warmup test
- **K9** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:785` — pytest counts folded; per-test pairing disclosed as a deviation
- **K10** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:98` — round-0 headlines beside round-1; max|ΔI| reported
- **K11** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/run.py:1063` — json/md → pytest → fold → hashes LAST → post-hoc pytest → DONE
- **K12** FIXED `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/E/code/stats.py:96` — drop count by reason; PIT ends 2026-07-02 stated in RESULT.md

## Deviations
- Bootstrap draws are per test (SeedSequence(20261004).spawn(4) then spawn(12) per branch); pairing holds within a test, not across all 12 cells (K9).
- hashes.txt pins the panel, pairs, regime, manifest, B1 RESULT.md, cited engine/regime scripts, and lane outputs — not every basket parquet (manifest already carries per-name sha256; disk is near full).

## Gaps
- Participation × P1 has a second under-floor cell besides the expected 17 months @ 2014-2019/T1/EXPANSION: 2014-2019/T3/CONTRACTION has 22 months (names 1,948, events 8,950). P2 matches the expected 20 months @ 2014-2019/T1/CALM. The extra P1 cell is the K8 tercile-cut shift, not a hidden winner.
- This SCOPED NULL closes the specific construction tested (one pre-declared feature per family, whole-sample terciles, P1/P2 binary partitions, month-cluster bootstrap, Holm over 12 tests). It does not close the broader search space of other features, cut rules, or partitions.
- Bootstrap pairing is within each test, not one shared month-draw across all 12 cells (K9 deviation).
