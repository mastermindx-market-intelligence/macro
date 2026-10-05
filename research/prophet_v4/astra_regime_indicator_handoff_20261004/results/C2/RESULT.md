The price stores are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). Every signal uses only closes at or before the signal session. C1 state joined at the 1D signal date is already one-session shifted. **ANSWER FIRST.** H10: INSUFFICIENT SUPPORT — C1 `controls.status` is **BROKEN** (pre-declared AR(1) gate). Pooled 3D DiD on H10 net = +0.0035 95% CI [-0.0009, +0.0076]; era signs 2014-2019 (2015-08-05..2019-12-30)=+ 2020-2026 (2019-12-31..2026-08-28)=+; phase_count=0 of 3 (DiD<0 with CI excluding zero); 3D cost curve monotonic fast>mid>persistent = False.

## Inputs

- B1 events_panel sha256 `209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8` (prefix `209e2246`)
- B1 confirmation_pairs sha256 `d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae`
- C1 rotation_state_daily sha256 `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` (prefix `9361dbf0`)
- B1 grain_effect_3d = **NOT SUPPORTED**; grain_effect_2d = NOT SUPPORTED; memory_effect_3 = NOT SUPPORTED
- C1 controls.status = **BROKEN**
- 1D events joined = 296,637; dropped (signal_date absent from C1) = 0; joined with NaN rotation_tercile = 0
- Repo head: `052e02d085b01f29baf499357e224c836d8eb224`

## DiD 3D (gap(fast) − gap(persistent))

gap(p,T) = mean(excess_h*_net of confirmed entries | T) − mean(excess_h*_net of all 1D events | T). Pooled DiD = equal-weight mean over 3D phases. Entry-month cluster bootstrap, 1,000 draws, seed 20261004; one month draw per replicate shared across cells. Honest-N: n_events / n_months / n_names for BOTH legs (confirmed entries and all 1D events) per tercile.

| cell | H10 Δ | H10 95% CI | H21 Δ | H21 95% CI | honest-N (fast/pers × confirmed/1D) |
|---|---:|---|---:|---|---|
| pooled | +0.0035 | [-0.0009, +0.0076] | +0.0027 | [-0.0032, +0.0084] | fast conf n_events=75,099 / n_months=119 / n_names=2,566; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=70,996 / n_months=121 / n_names=2,579; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| p0 | +0.0024 | [-0.0021, +0.0071] | +0.0023 | [-0.0035, +0.0080] | fast conf n_events=25,227 / n_months=119 / n_names=2,561; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=23,775 / n_months=121 / n_names=2,576; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| p1 | +0.0045 | [-0.0002, +0.0088] | +0.0021 | [-0.0041, +0.0086] | fast conf n_events=24,833 / n_months=119 / n_names=2,566; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=23,532 / n_months=121 / n_names=2,577; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| p2 | +0.0035 | [-0.0012, +0.0080] | +0.0035 | [-0.0028, +0.0094] | fast conf n_events=25,039 / n_months=119 / n_names=2,565; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=23,689 / n_months=121 / n_names=2,579; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| pooled 2014-2019 (2015-08-05..2019-12-30) | +0.0033 | [-0.0020, +0.0082] | +0.0034 | [-0.0029, +0.0095] | fast conf n_events=35,011 / n_months=51 / n_names=1,933; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=18,823 / n_months=46 / n_names=1,828; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| p0 2014-2019 (2015-08-05..2019-12-30) | +0.0018 | [-0.0031, +0.0070] | +0.0045 | [-0.0022, +0.0113] | fast conf n_events=11,750 / n_months=51 / n_names=1,933; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=6,252 / n_months=46 / n_names=1,824; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| p1 2014-2019 (2015-08-05..2019-12-30) | +0.0049 | [-0.0007, +0.0102] | +0.0027 | [-0.0044, +0.0089] | fast conf n_events=11,581 / n_months=51 / n_names=1,928; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=6,194 / n_months=46 / n_names=1,823; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| p2 2014-2019 (2015-08-05..2019-12-30) | +0.0031 | [-0.0027, +0.0085] | +0.0029 | [-0.0044, +0.0094] | fast conf n_events=11,680 / n_months=51 / n_names=1,931; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=6,377 / n_months=46 / n_names=1,828; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| pooled 2020-2026 (2019-12-31..2026-08-28) | +0.0051 | [-0.0009, +0.0112] | +0.0041 | [-0.0039, +0.0123] | fast conf n_events=40,088 / n_months=68 / n_names=2,559; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=52,173 / n_months=75 / n_names=2,577; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |
| p0 2020-2026 (2019-12-31..2026-08-28) | +0.0043 | [-0.0022, +0.0110] | +0.0033 | [-0.0046, +0.0111] | fast conf n_events=13,477 / n_months=68 / n_names=2,558; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=17,523 / n_months=75 / n_names=2,574; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |
| p1 2020-2026 (2019-12-31..2026-08-28) | +0.0060 | [-0.0001, +0.0118] | +0.0034 | [-0.0054, +0.0120] | fast conf n_events=13,252 / n_months=68 / n_names=2,559; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=17,338 / n_months=75 / n_names=2,577; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |
| p2 2020-2026 (2019-12-31..2026-08-28) | +0.0051 | [-0.0012, +0.0113] | +0.0056 | [-0.0028, +0.0143] | fast conf n_events=13,359 / n_months=68 / n_names=2,558; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=17,312 / n_months=75 / n_names=2,577; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |

## DiD 2D (gap(fast) − gap(persistent))

gap(p,T) = mean(excess_h*_net of confirmed entries | T) − mean(excess_h*_net of all 1D events | T). Pooled DiD = equal-weight mean over 2D phases. Entry-month cluster bootstrap, 1,000 draws, seed 20261004; one month draw per replicate shared across cells. Honest-N: n_events / n_months / n_names for BOTH legs (confirmed entries and all 1D events) per tercile.

| cell | H10 Δ | H10 95% CI | H21 Δ | H21 95% CI | honest-N (fast/pers × confirmed/1D) |
|---|---:|---|---:|---|---|
| pooled | +0.0030 | [-0.0005, +0.0067] | +0.0013 | [-0.0037, +0.0059] | fast conf n_events=90,113 / n_months=119 / n_names=2,584; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=87,896 / n_months=121 / n_names=2,586; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| p0 | +0.0028 | [-0.0007, +0.0064] | +0.0012 | [-0.0040, +0.0062] | fast conf n_events=45,056 / n_months=119 / n_names=2,584; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=43,881 / n_months=121 / n_names=2,586; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| p1 | +0.0032 | [-0.0004, +0.0072] | +0.0014 | [-0.0035, +0.0058] | fast conf n_events=45,057 / n_months=119 / n_names=2,583; fast 1D n_events=94,503 / n_months=119 / n_names=2,586; pers conf n_events=44,015 / n_months=121 / n_names=2,586; pers 1D n_events=94,158 / n_months=121 / n_names=2,586 |
| pooled 2014-2019 (2015-08-05..2019-12-30) | +0.0012 | [-0.0029, +0.0058] | +0.0009 | [-0.0045, +0.0066] | fast conf n_events=41,846 / n_months=51 / n_names=1,957; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=22,589 / n_months=46 / n_names=1,921; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| p0 2014-2019 (2015-08-05..2019-12-30) | +0.0008 | [-0.0037, +0.0057] | +0.0004 | [-0.0054, +0.0064] | fast conf n_events=20,912 / n_months=51 / n_names=1,955; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=11,313 / n_months=46 / n_names=1,921; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| p1 2014-2019 (2015-08-05..2019-12-30) | +0.0016 | [-0.0024, +0.0056] | +0.0015 | [-0.0038, +0.0072] | fast conf n_events=20,934 / n_months=51 / n_names=1,957; fast 1D n_events=43,285 / n_months=51 / n_names=1,965; pers conf n_events=11,276 / n_months=46 / n_names=1,913; pers 1D n_events=23,688 / n_months=46 / n_names=1,957 |
| pooled 2020-2026 (2019-12-31..2026-08-28) | +0.0050 | [-0.0002, +0.0097] | +0.0027 | [-0.0040, +0.0087] | fast conf n_events=48,267 / n_months=68 / n_names=2,584; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=65,307 / n_months=75 / n_names=2,586; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |
| p0 2020-2026 (2019-12-31..2026-08-28) | +0.0051 | [+0.0001, +0.0099] | +0.0033 | [-0.0038, +0.0097] | fast conf n_events=24,144 / n_months=68 / n_names=2,584; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=32,568 / n_months=75 / n_names=2,586; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |
| p1 2020-2026 (2019-12-31..2026-08-28) | +0.0048 | [-0.0005, +0.0099] | +0.0022 | [-0.0041, +0.0080] | fast conf n_events=24,123 / n_months=68 / n_names=2,583; fast 1D n_events=51,218 / n_months=68 / n_names=2,586; pers conf n_events=32,739 / n_months=75 / n_names=2,586; pers 1D n_events=70,470 / n_months=75 / n_names=2,586 |

## Gaps by rotation tercile (H10 net)

gap(p,T) as defined above. n_confirmed = confirmed entries of that phase; n_1d = all 1D events in T (including unconfirmed).

| grain | tercile | phase | gap H10 | 95% CI | n_confirmed | n_1d | n_events_conf / n_months_conf / n_names_conf | n_events_1d / n_months_1d / n_names_1d |
|---|---|---|---:|---|---:|---:|---|---|
| 3D | fast | p0 | +0.0019 | [-0.0007, +0.0047] | 25,227 | 94,503 | 25,227 / 119 / 2,561 | 94,503 / 119 / 2,586 |
| 3D | fast | p1 | +0.0032 | [+0.0007, +0.0059] | 24,833 | 94,503 | 24,833 / 119 / 2,566 | 94,503 / 119 / 2,586 |
| 3D | fast | p2 | +0.0021 | [-0.0003, +0.0046] | 25,039 | 94,503 | 25,039 / 119 / 2,565 | 94,503 / 119 / 2,586 |
| 3D | mid | p0 | +0.0029 | [-0.0003, +0.0061] | 29,180 | 107,976 | 29,180 / 130 / 2,579 | 107,976 / 130 / 2,586 |
| 3D | mid | p1 | +0.0026 | [-0.0004, +0.0057] | 29,620 | 107,976 | 29,620 / 130 / 2,578 | 107,976 / 130 / 2,586 |
| 3D | mid | p2 | +0.0027 | [-0.0001, +0.0053] | 29,563 | 107,976 | 29,563 / 130 / 2,576 | 107,976 / 130 / 2,586 |
| 3D | persistent | p0 | -0.0005 | [-0.0045, +0.0034] | 23,775 | 94,158 | 23,775 / 121 / 2,576 | 94,158 / 121 / 2,586 |
| 3D | persistent | p1 | -0.0012 | [-0.0049, +0.0025] | 23,532 | 94,158 | 23,532 / 121 / 2,577 | 94,158 / 121 / 2,586 |
| 3D | persistent | p2 | -0.0014 | [-0.0050, +0.0023] | 23,689 | 94,158 | 23,689 / 121 / 2,579 | 94,158 / 121 / 2,586 |
| 2D | fast | p0 | +0.0019 | [-0.0003, +0.0041] | 45,056 | 94,503 | 45,056 / 119 / 2,584 | 94,503 / 119 / 2,586 |
| 2D | fast | p1 | +0.0023 | [+0.0002, +0.0044] | 45,057 | 94,503 | 45,057 / 119 / 2,583 | 94,503 / 119 / 2,586 |
| 2D | mid | p0 | +0.0006 | [-0.0024, +0.0033] | 52,384 | 107,976 | 52,384 / 130 / 2,585 | 107,976 / 130 / 2,586 |
| 2D | mid | p1 | +0.0010 | [-0.0017, +0.0034] | 51,754 | 107,976 | 51,754 / 130 / 2,585 | 107,976 / 130 / 2,586 |
| 2D | persistent | p0 | -0.0009 | [-0.0038, +0.0019] | 43,881 | 94,158 | 43,881 / 121 / 2,586 | 94,158 / 121 / 2,586 |
| 2D | persistent | p1 | -0.0010 | [-0.0044, +0.0021] | 44,015 | 94,158 | 44,015 / 121 / 2,586 | 94,158 / 121 / 2,586 |

## Confirmation-cost curve

Mean `mfe21_consumed_frac` and `confirmation_cost_pct` at confirmation, pooled across phases, by rotation tercile of the 1D parent. Monotonic = fast > mid > persistent on mean mfe21_consumed_frac.

| grain | tercile | mean mfe | median mfe | sd | min | max | 95% CI | mean cost pct | n_finite_mfe | n_events | n_months | n_names |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 3D | fast | +0.0478 | +0.3253 | +16.7212 | -2444.0256 | +1.0000 | [-0.1893, +0.1869] | +0.0416 | 72,059 | 75,099 | 119 | 2,577 |
| 3D | mid | +0.1467 | +0.3410 | +4.9778 | -1194.3112 | +1.0000 | [+0.0925, +0.1901] | +0.0470 | 84,760 | 88,363 | 130 | 2,584 |
| 3D | persistent | +0.1214 | +0.3344 | +3.0167 | -256.9006 | +1.0000 | [+0.0756, +0.1624] | +0.0525 | 67,699 | 70,996 | 121 | 2,584 |
| 2D | fast | +0.0858 | +0.2414 | +4.8494 | -1228.1840 | +1.0000 | [+0.0408, +0.1232] | +0.0283 | 85,733 | 90,113 | 119 | 2,584 |
| 2D | mid | +0.0414 | +0.2471 | +4.3499 | -616.2653 | +1.0000 | [-0.0137, +0.0871] | +0.0317 | 98,973 | 104,138 | 130 | 2,585 |
| 2D | persistent | -0.3643 | +0.2331 | +116.3747 | -33488.6094 | +1.0000 | [-1.2929, +0.0677] | +0.0349 | 82,885 | 87,896 | 121 | 2,586 |

- monotonic_3d = **False**
- monotonic_2d = **True**

## False starts avoided

Among 1D events with excess_h10_net < −0.02, share that received no 3D confirmation on any of p0/p1/p2 (pooled phases), by rotation tercile.

| tercile | share unconfirmed | n_events | n_months | n_names |
|---|---:|---:|---:|---:|
| fast | 0.7588 | 36,925 | 119 | 2,581 |
| mid | 0.7546 | 42,009 | 130 | 2,585 |
| persistent | 0.7630 | 38,080 | 121 | 2,584 |

## Large winners excluded

Among 1D events with excess_h21_net > +0.10, share that never received 3D confirmation on any of p0/p1/p2, by rotation tercile.

| tercile | share unconfirmed | n_events | n_months | n_names |
|---|---:|---:|---:|---:|
| fast | 0.4963 | 12,270 | 119 | 2,403 |
| mid | 0.4761 | 15,505 | 130 | 2,513 |
| persistent | 0.5342 | 13,024 | 121 | 2,445 |

## Second axis: breadth tercile (narrow vs broad)

Primary DiD analogue: gap(narrow) − gap(broad), reported only (not used in the verdict).

| grain | cell | H10 Δ | H10 95% CI | H21 Δ | H21 95% CI |
|---|---|---:|---|---:|---|
| 3D | pooled | +0.0032 | [-0.0011, +0.0075] | -0.0012 | [-0.0070, +0.0045] |
| 3D | p0 | +0.0031 | [-0.0019, +0.0082] | -0.0017 | [-0.0078, +0.0042] |
| 3D | p1 | +0.0060 | [+0.0017, +0.0103] | +0.0011 | [-0.0052, +0.0066] |
| 3D | p2 | +0.0006 | [-0.0037, +0.0046] | -0.0029 | [-0.0088, +0.0030] |
| 3D | pooled 2014-2019 (2015-08-05..2019-12-30) | +0.0004 | [-0.0042, +0.0048] | -0.0063 | [-0.0137, +0.0021] |
| 3D | pooled 2020-2026 (2019-12-31..2026-08-28) | +0.0057 | [+0.0000, +0.0110] | +0.0012 | [-0.0067, +0.0086] |
| 2D | pooled | +0.0030 | [-0.0010, +0.0068] | +0.0011 | [-0.0033, +0.0053] |
| 2D | p0 | +0.0022 | [-0.0016, +0.0061] | +0.0010 | [-0.0036, +0.0054] |
| 2D | p1 | +0.0037 | [-0.0002, +0.0078] | +0.0011 | [-0.0034, +0.0055] |
| 2D | pooled 2014-2019 (2015-08-05..2019-12-30) | +0.0004 | [-0.0037, +0.0041] | -0.0013 | [-0.0075, +0.0060] |
| 2D | pooled 2020-2026 (2019-12-31..2026-08-28) | +0.0045 | [-0.0005, +0.0096] | +0.0024 | [-0.0038, +0.0080] |

## Cell support

Every (variant, rotation tercile, era) cell. 1D = all joined 1D events; 2D.p / 3D.p = confirmed entries of that variant. Floors: ≥ 24 months, ≥ 100 names, ≥ 300 events; both eras must be present for the fast/persistent adequate-support test.

| cell_id | n_events | n_months | n_names | meets_floor |
|---|---:|---:|---:|:---:|
| `1D|fast|2014-2019 (2015-08-05..2019-12-30)` | 43,285 | 51 | 1,965 | yes |
| `1D|fast|2020-2026 (2019-12-31..2026-08-28)` | 51,218 | 68 | 2,586 | yes |
| `1D|mid|2014-2019 (2015-08-05..2019-12-30)` | 32,601 | 52 | 1,957 | yes |
| `1D|mid|2020-2026 (2019-12-31..2026-08-28)` | 75,375 | 78 | 2,586 | yes |
| `1D|persistent|2014-2019 (2015-08-05..2019-12-30)` | 23,688 | 46 | 1,957 | yes |
| `1D|persistent|2020-2026 (2019-12-31..2026-08-28)` | 70,470 | 75 | 2,586 | yes |
| `2D.p0|fast|2014-2019 (2015-08-05..2019-12-30)` | 20,912 | 51 | 1,955 | yes |
| `2D.p0|fast|2020-2026 (2019-12-31..2026-08-28)` | 24,144 | 68 | 2,584 | yes |
| `2D.p0|mid|2014-2019 (2015-08-05..2019-12-30)` | 15,650 | 52 | 1,935 | yes |
| `2D.p0|mid|2020-2026 (2019-12-31..2026-08-28)` | 36,734 | 78 | 2,585 | yes |
| `2D.p0|persistent|2014-2019 (2015-08-05..2019-12-30)` | 11,313 | 46 | 1,921 | yes |
| `2D.p0|persistent|2020-2026 (2019-12-31..2026-08-28)` | 32,568 | 75 | 2,586 | yes |
| `2D.p1|fast|2014-2019 (2015-08-05..2019-12-30)` | 20,934 | 51 | 1,957 | yes |
| `2D.p1|fast|2020-2026 (2019-12-31..2026-08-28)` | 24,123 | 68 | 2,583 | yes |
| `2D.p1|mid|2014-2019 (2015-08-05..2019-12-30)` | 15,543 | 52 | 1,935 | yes |
| `2D.p1|mid|2020-2026 (2019-12-31..2026-08-28)` | 36,211 | 78 | 2,585 | yes |
| `2D.p1|persistent|2014-2019 (2015-08-05..2019-12-30)` | 11,276 | 46 | 1,913 | yes |
| `2D.p1|persistent|2020-2026 (2019-12-31..2026-08-28)` | 32,739 | 75 | 2,586 | yes |
| `3D.p0|fast|2014-2019 (2015-08-05..2019-12-30)` | 11,750 | 51 | 1,933 | yes |
| `3D.p0|fast|2020-2026 (2019-12-31..2026-08-28)` | 13,477 | 68 | 2,558 | yes |
| `3D.p0|mid|2014-2019 (2015-08-05..2019-12-30)` | 8,865 | 52 | 1,898 | yes |
| `3D.p0|mid|2020-2026 (2019-12-31..2026-08-28)` | 20,315 | 78 | 2,579 | yes |
| `3D.p0|persistent|2014-2019 (2015-08-05..2019-12-30)` | 6,252 | 46 | 1,824 | yes |
| `3D.p0|persistent|2020-2026 (2019-12-31..2026-08-28)` | 17,523 | 75 | 2,574 | yes |
| `3D.p1|fast|2014-2019 (2015-08-05..2019-12-30)` | 11,581 | 51 | 1,928 | yes |
| `3D.p1|fast|2020-2026 (2019-12-31..2026-08-28)` | 13,252 | 68 | 2,559 | yes |
| `3D.p1|mid|2014-2019 (2015-08-05..2019-12-30)` | 9,118 | 52 | 1,901 | yes |
| `3D.p1|mid|2020-2026 (2019-12-31..2026-08-28)` | 20,502 | 78 | 2,578 | yes |
| `3D.p1|persistent|2014-2019 (2015-08-05..2019-12-30)` | 6,194 | 46 | 1,823 | yes |
| `3D.p1|persistent|2020-2026 (2019-12-31..2026-08-28)` | 17,338 | 75 | 2,577 | yes |
| `3D.p2|fast|2014-2019 (2015-08-05..2019-12-30)` | 11,680 | 51 | 1,931 | yes |
| `3D.p2|fast|2020-2026 (2019-12-31..2026-08-28)` | 13,359 | 68 | 2,558 | yes |
| `3D.p2|mid|2014-2019 (2015-08-05..2019-12-30)` | 9,151 | 52 | 1,893 | yes |
| `3D.p2|mid|2020-2026 (2019-12-31..2026-08-28)` | 20,412 | 78 | 2,576 | yes |
| `3D.p2|persistent|2014-2019 (2015-08-05..2019-12-30)` | 6,377 | 46 | 1,828 | yes |
| `3D.p2|persistent|2020-2026 (2019-12-31..2026-08-28)` | 17,312 | 75 | 2,577 | yes |

- floors_ok (3D fast/persistent + 1D arms) = **True**
- floors_ok (2D fast/persistent + 1D arms) = **True**

## Verdict

**Rule.** SUPPORTED iff pooled 3D DiD on H10 net < 0 with 95% CI excluding zero, AND the pooled DiD has the same sign in both eras, AND DiD(p) < 0 with CI excluding zero for ≥ 2 of 3 phases, AND the 3D cost curve is monotonic fast > mid > persistent. NOT SUPPORTED iff the pooled 3D DiD CI includes zero AND all fast/persistent cells meet the floors. INSUFFICIENT SUPPORT otherwise (also whenever C1 controls are BROKEN or B1's verdict is INSUFFICIENT on every 3D phase).

H10: INSUFFICIENT SUPPORT
2D: INSUFFICIENT SUPPORT

COUNTERFACTUAL (if C1 controls were PASS; not a verdict): NOT SUPPORTED

Reasons (3D):
- C1 controls.status is BROKEN (pre-declared AR(1) gate)
- pooled H10 DiD 95% CI includes zero
- all fast/persistent cells meet the support floors

Reasons (2D):
- C1 controls.status is BROKEN (pre-declared AR(1) gate)
- pooled H10 DiD 95% CI includes zero
- all fast/persistent cells meet the support floors

## Era labels

| era key | actual signal_date range |
|---|---|
| `2014-2019` | 2015-08-05..2019-12-30 |
| `2020-2026` | 2019-12-31..2026-08-28 |

## Provenance

- host: `m2` (m2studio); python `/opt/homebrew/opt/python@3.14/bin/python3.14 3.14.7`; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1
- B1 events_panel round-0 `8b17049773a32c6e517a614a48e530f29bc250f126e4ee9b8871ecd4cd7690a1` → now `209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8` (DIFFERS)
- B1 confirmation_pairs round-0 `22eabfe6287a69233b7de328616f45a7424801dc4cd69fdfb3049dc2328b01eb` → now `d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae` (DIFFERS)
- B1 result.json round-0 `7ede0e4333738127484a82d93a76c7795505b4112d6a61c223d35e8ffaaaad0b` → now `e480d73a06b1fe01ebbd67ce4c80f1e83b08466d0f82a4b82f03955fc0dd4d09`
- C1 rotation_state_daily round-0 `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` → now `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` (SAME)
- C1 result.json round-0 `3492dc2d30ef09a0870aea5f5167be0c1c6f26d167c6b838e3d740625a4e1519` → now `142de0f2541513d9bbe660ff562678c63139e05def86d0048da5db1703cfea2f` (rotation parquet is byte-identical, so C1 record delta moves NOTHING numeric)
- engine/canon.py `bdf34dc8a9b851889e9b6beae939867ca4611ad41a78b4b43322f2a8a9b18165` (SAME as round-0)
- engine/session_anchor.py `1da03cb44684e4b0f91710c7279e3fff40d2344e253ab83473a83f7e2afa5c3f` (SAME as round-0)
- engine/bar_derive.py `eb3a9d4c6ece400902a1765997b741c09a0b1d0c47ff798acffe0049a691e469` (SAME as round-0)

## Leaf diff vs round 0

Round-0 result.json sha256 `9372f0f7ad0a4795e74a46dc7f4fc08d11adc2eb2dd158504b28dfc4f82842e0`. Pooled 3D H10 DiD round-0 = 0.003451310614323792; now = 0.0034518154435143936; delta = 5.048291906017272e-07.

| leaf | round-0 | now | attribution |
|---|---|---|---|
| `n_1d_events_joined` | 296635 | 296637 | (a) B1 panel delta (−32/+2 1D rows) |
| `did.3D.pooled.h10.delta` | 0.003451310614323792 | 0.0034518154435143936 | (a) B1 panel delta |
| `did.3D.pooled.h10.ci` | [-0.0008754812751993297, 0.007598016858986852] | [-0.0008752350470632498, 0.007598139844272105] | (a) B1 panel delta |
| `verdict.3D` | INSUFFICIENT SUPPORT | INSUFFICIENT SUPPORT | (c) N1 packet rule — both INSUFFICIENT SUPPORT under C1 BROKEN |
| `C1_controls_status` | BROKEN | BROKEN | (b) C1 record delta cannot move numerics (rotation parquet byte-identical) |
| `cost_curve.monotonic_3d` | False | False | (a) panel / (c) N2 strict monotonic helper (same predicate as round 0) |
| `false_starts_avoided.fast.share` | 0.7587542315504401 | 0.7587542315504401 | (a) B1 panel + (c) N3 key mapping restore |
| `large_winners_excluded.fast.share` | 0.4963325183374083 | 0.4963325183374083 | (a) B1 panel + (c) N3 key mapping restore |
| `cost_curve.3D.fast.n` | 75099 | 72059 | (c) N5 cost-curve n is finite mfe count |
| `false_starts_avoided.mid.share` | 0.7546419729575319 | 0.7546478135637601 | (a) B1 panel + (c) N3 key mapping restore |
| `large_winners_excluded.mid.share` | 0.4761044824250242 | 0.4761044824250242 | (a) B1 panel + (c) N3 key mapping restore |
| `cost_curve.3D.mid.n` | 88363 | 84760 | (c) N5 cost-curve n is finite mfe count |
| `false_starts_avoided.persistent.share` | 0.7629726890756302 | 0.7629726890756302 | (a) B1 panel + (c) N3 key mapping restore |
| `large_winners_excluded.persistent.share` | 0.5341676904176904 | 0.5341676904176904 | (a) B1 panel + (c) N3 key mapping restore |
| `cost_curve.3D.persistent.n` | 70996 | 67699 | (c) N5 cost-curve n is finite mfe count |
| `C1_rotation_state_sha` | 9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd | 9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd | (b) SAME bytes — no numeric movement from C1 table |

## Round-0 headlines vs this round

| quantity | round-0 | this round | moved? |
|---|---|---|---|
| pooled 3D H10 DiD | 0.003451310614323792 | 0.0034518154435143936 | yes |
| pooled 3D H10 CI lo | [-0.0008754812751993297, 0.007598016858986852] | [-0.0008752350470632498, 0.007598139844272105] | yes |
| verdict 3D | INSUFFICIENT SUPPORT | INSUFFICIENT SUPPORT | no |
| verdict 2D | INSUFFICIENT SUPPORT | INSUFFICIENT SUPPORT | no |
| n_1d_events_joined | 296635 | 296637 | yes |
| monotonic_3d | False | False | no |
| false_starts fast | 0.7587542315504401 | 0.7587542315504401 | no |
| large_winners fast | 0.4963325183374083 | 0.4963325183374083 | no |

## N1..N9

- N1 FIXED run.py:536 run.py:565 test_C2.py:457 test_C2.py:472 (MC1 → test_c1_status_is_read_from_record; MC2 → test_verdict_insufficient_when_c1_broken)
- N2 FIXED run.py:511 run.py:528 test_C2.py:501 test_C2.py:510
- N3 FIXED run.py:780 run.py:654 test_C2.py:516 (old integer-index mapping must fail that test)
- N4 FIXED leaf-diff vs round-0 sha 9372f0f7ad0a4795… in RESULT.md ## Leaf diff
- N5 FIXED run.py:849 honest-N on both DiD legs; cost n = n_finite_mfe run.py:1044
- N6 FIXED run.py:664 era_labels definition table is the only bare era key
- N7 FIXED provenance + hashes.txt pin full sha256 of B1/C1/engine at round 0 and now
- N8 FIXED COUNTERFACTUAL line under ## Verdict run.py:1620
- N9 FIXED run.py:1911 K11 write order records→pytest→fold→hashes LAST; pytest timing stripped run.py:1810

## Tests

```
18 passed
```

result.json sha256 run A: `be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54`
result.json sha256 run B: `be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54`

Mutant → failing test:

| mutant | expected failing test | observed |
|---|---|---|
| M5 | test_compute_all_did_sign_under_h10 | test_compute_all_did_sign_under_h10 - AssertionError: J2 FAIL: pooled DiD should be clearly negative (fast gap << persistent gap), got 0.035. Mutant M5 would flip the sign. |
| M6 | test_compute_all_floors | test_compute_all_floors - AssertionError: J3 FAIL: tiny cell must have meets_floor False; mutant M6 would force True |
| M7 | test_compute_all_paired_zero | 1 passed, 17 deselected |
| MC1 | test_c1_status_is_read_from_record | test_c1_status_is_read_from_record - AssertionError: assert 'OK' == 'BROKEN' |
| MC2 | test_verdict_insufficient_when_c1_broken | test_verdict_insufficient_when_c1_broken - AssertionError: assert 'NOT SUPPORTED' == 'INSUFFICIENT SUPPORT' |
| N3_old_mapping | test_confirmed_share_mapping_by_key | test_confirmed_share_mapping_by_key - assert [False, False, False] == [False, True, True] |

## Deviations

- JSON objects cannot hold two keys named 'gaps'; the spec lists both the gap(p,T) table and the textual gaps array under that name. The nested gap table is stored as 'gaps' (schema body) and the textual array as 'report_gaps' (added key).
- Confirmed-entry bootstrap/era keys use the 1D parent's entry_month and era (the conditioner known when the first signal fired), not the later confirmation date. Cost-curve means use the same parent month.
- False-starts / large-winners 'no 3D confirmation (pooled phases)' is implemented as no confirmation on any of 3D.p0/p1/p2 (never confirmed), not as a stacked (event × phase) share.
- Breadth-axis DiD is gap(narrow) − gap(broad), analogous to gap(fast) − gap(persistent).
- C2 does not recompute indicators; engine.canon / session_anchor / bar_derive are imported per lane law and unused in the join.
- result.json era keys outside era_labels are qualified with the actual signal_date range (N6); internal compute still uses the two era tokens.
- cost-curve n is the finite mfe21_consumed_frac count (N5); n_events is the raw row count.

## Gaps

- C1 controls.status is BROKEN (AR(1) lag-21 of LP = -0.0404); every rotation-conditioned cell is therefore INSUFFICIENT SUPPORT under the pre-declared rule even though every table is computed and reported.
- B1 grain_effect_3d is NOT SUPPORTED (not INSUFFICIENT); the extra 'B1 INSUFFICIENT on every 3D phase' clause does not fire.
- Zero 1D events dropped for a missing C1 date (all 1D signal dates are present on the shifted rotation_state_daily index).
