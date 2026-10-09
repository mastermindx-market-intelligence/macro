# Risk Radar Displayed-Probability Audit — Results

Protocol commit: `f520eda41e0ff5051caf4bc019e198eabd949e49`.

Historical reconstructed diagnostic only; no live probability or model value changed.

## H5

| Window | n | Events | Base | Mean displayed | Gap | Brier | Base Brier | Brier skill | WACE | RWSCE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 8211 | 288 | 3.5% | 3.7% | +0.1pp | 0.0326 | 0.0338 | 0.036 | 0.0167 | 0.0285 |
| y2006 | 5205 | 196 | 3.8% | 4.0% | +0.2pp | 0.0347 | 0.0362 | 0.043 | 0.0196 | 0.0300 |
| y2020 | 1682 | 60 | 3.6% | 4.1% | +0.5pp | 0.0327 | 0.0344 | 0.048 | 0.0229 | 0.0288 |

| Window | Displayed p | n | Events | Observed | 90% block CI | Obs-p | Thin | Composition |
|---|---:|---:|---:|---:|---|---:|---|---|
| full | 2.0% | 2154 | 38 | 1.8% | 1.1%..2.4% | -0.2pp |  | calm+0hot:1304, watch+0hot:850 |
| full | 3.0% | 3636 | 58 | 1.6% | 1.1%..2.1% | -1.4pp |  | caution+0hot:386, caution+1hot:3250 |
| full | 4.2% | 1159 | 36 | 3.1% | 2.1%..4.1% | -1.1pp |  | caution+2hot:1159 |
| full | 5.0% | 139 | 18 | 12.9% | 7.1%..18.3% | +7.9pp |  | elevated+1hot:139 |
| full | 5.4% | 257 | 8 | 3.1% | 1.2%..5.2% | -2.3pp |  | caution+3hot:257 |
| full | 6.2% | 58 | 6 | 10.3% | 3.1%..18.3% | +4.1pp | YES | elevated+2hot:58 |
| full | 6.6% | 12 | 1 | 8.3% | 0.0%..37.8% | +1.7pp | YES | caution+4hot:12 |
| full | 7.4% | 4 | 1 | 25.0% | 0.0%..66.7% | +17.6pp | YES | elevated+3hot:4 |
| full | 8.0% | 190 | 32 | 16.8% | 9.9%..24.1% | +8.8pp |  | risk-off+1hot:190 |
| full | 9.2% | 355 | 37 | 10.4% | 6.6%..15.1% | +1.2pp |  | risk-off+2hot:355 |
| full | 10.4% | 247 | 53 | 21.5% | 14.5%..28.8% | +11.1pp |  | risk-off+3hot:247 |
| y2006 | 2.0% | 942 | 12 | 1.3% | 0.5%..2.2% | -0.7pp |  | calm+0hot:397, watch+0hot:545 |
| y2006 | 3.0% | 2333 | 31 | 1.3% | 0.8%..1.9% | -1.7pp |  | caution+0hot:253, caution+1hot:2080 |
| y2006 | 4.2% | 908 | 31 | 3.4% | 2.2%..4.8% | -0.8pp |  | caution+2hot:908 |
| y2006 | 5.0% | 83 | 10 | 12.0% | 5.4%..19.7% | +7.0pp | YES | elevated+1hot:83 |
| y2006 | 5.4% | 232 | 8 | 3.4% | 1.4%..5.8% | -2.0pp |  | caution+3hot:232 |
| y2006 | 6.2% | 47 | 5 | 10.6% | 2.4%..19.2% | +4.4pp | YES | elevated+2hot:47 |
| y2006 | 6.6% | 11 | 1 | 9.1% | 0.0%..42.9% | +2.5pp | YES | caution+4hot:11 |
| y2006 | 7.4% | 4 | 1 | 25.0% | 0.0%..66.7% | +17.6pp | YES | elevated+3hot:4 |
| y2006 | 8.0% | 89 | 10 | 11.2% | 3.8%..20.8% | +3.2pp | YES | risk-off+1hot:89 |
| y2006 | 9.2% | 309 | 34 | 11.0% | 6.7%..15.5% | +1.8pp |  | risk-off+2hot:309 |
| y2006 | 10.4% | 247 | 53 | 21.5% | 14.5%..28.2% | +11.1pp |  | risk-off+3hot:247 |
| y2020 | 2.0% | 310 | 0 | 0.0% | 0.0%..0.0% | -2.0pp |  | calm+0hot:148, watch+0hot:162 |
| y2020 | 3.0% | 752 | 8 | 1.1% | 0.4%..1.9% | -1.9pp |  | caution+0hot:101, caution+1hot:651 |
| y2020 | 4.2% | 270 | 13 | 4.8% | 2.0%..7.8% | +0.6pp |  | caution+2hot:270 |
| y2020 | 5.0% | 24 | 0 | 0.0% | 0.0%..0.0% | -5.0pp | YES | elevated+1hot:24 |
| y2020 | 5.4% | 66 | 3 | 4.5% | 0.0%..9.5% | -0.9pp | YES | caution+3hot:66 |
| y2020 | 6.2% | 8 | 0 | 0.0% | 0.0%..0.0% | -6.2pp | YES | elevated+2hot:8 |
| y2020 | 6.6% | 10 | 0 | 0.0% | 0.0%..0.0% | -6.6pp | YES | caution+4hot:10 |
| y2020 | 7.4% | 1 | 0 | 0.0% | 0.0%..0.0% | -7.4pp | YES | elevated+3hot:1 |
| y2020 | 8.0% | 46 | 8 | 17.4% | 4.8%..33.3% | +9.4pp | YES | risk-off+1hot:46 |
| y2020 | 9.2% | 95 | 12 | 12.6% | 4.0%..22.5% | +3.4pp | YES | risk-off+2hot:95 |
| y2020 | 10.4% | 100 | 16 | 16.0% | 6.5%..27.3% | +5.6pp |  | risk-off+3hot:100 |

## H10

| Window | n | Events | Base | Mean displayed | Gap | Brier | Base Brier | Brier skill | WACE | RWSCE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 8206 | 698 | 8.5% | 9.1% | +0.6pp | 0.0747 | 0.0778 | 0.041 | 0.0224 | 0.0324 |
| y2006 | 5200 | 438 | 8.4% | 9.7% | +1.3pp | 0.0729 | 0.0771 | 0.055 | 0.0326 | 0.0394 |
| y2020 | 1677 | 138 | 8.2% | 9.9% | +1.7pp | 0.0702 | 0.0755 | 0.071 | 0.0475 | 0.0563 |

| Window | Displayed p | n | Events | Observed | 90% block CI | Obs-p | Thin | Composition |
|---|---:|---:|---:|---:|---|---:|---|---|
| full | 6.0% | 2154 | 116 | 5.4% | 3.8%..7.0% | -0.6pp |  | calm+0hot:1304, watch+0hot:850 |
| full | 8.0% | 3631 | 212 | 5.8% | 4.6%..7.1% | -2.2pp |  | caution+0hot:382, caution+1hot:3249 |
| full | 10.0% | 1159 | 92 | 7.9% | 5.7%..10.3% | -2.1pp |  | caution+2hot:1159 |
| full | 12.0% | 396 | 51 | 12.9% | 8.6%..17.7% | +0.9pp |  | caution+3hot:257, elevated+1hot:139 |
| full | 14.0% | 70 | 13 | 18.6% | 10.0%..29.6% | +4.6pp | YES | caution+4hot:12, elevated+2hot:58 |
| full | 16.0% | 4 | 2 | 50.0% | 0.0%..100.0% | +34.0pp | YES | elevated+3hot:4 |
| full | 17.0% | 190 | 53 | 27.9% | 18.3%..38.2% | +10.9pp |  | risk-off+1hot:190 |
| full | 19.0% | 355 | 80 | 22.5% | 16.3%..29.3% | +3.5pp |  | risk-off+2hot:355 |
| full | 21.0% | 247 | 79 | 32.0% | 21.4%..42.5% | +11.0pp |  | risk-off+3hot:247 |
| y2006 | 6.0% | 942 | 31 | 3.3% | 1.8%..5.1% | -2.7pp |  | calm+0hot:397, watch+0hot:545 |
| y2006 | 8.0% | 2328 | 106 | 4.6% | 3.4%..5.8% | -3.4pp |  | caution+0hot:249, caution+1hot:2079 |
| y2006 | 10.0% | 908 | 78 | 8.6% | 5.7%..11.7% | -1.4pp |  | caution+2hot:908 |
| y2006 | 12.0% | 315 | 39 | 12.4% | 7.5%..17.7% | +0.4pp |  | caution+3hot:232, elevated+1hot:83 |
| y2006 | 14.0% | 58 | 10 | 17.2% | 8.2%..28.3% | +3.2pp | YES | caution+4hot:11, elevated+2hot:47 |
| y2006 | 16.0% | 4 | 2 | 50.0% | 0.0%..100.0% | +34.0pp | YES | elevated+3hot:4 |
| y2006 | 17.0% | 89 | 20 | 22.5% | 9.8%..34.3% | +5.5pp | YES | risk-off+1hot:89 |
| y2006 | 19.0% | 309 | 73 | 23.6% | 16.6%..30.8% | +4.6pp |  | risk-off+2hot:309 |
| y2006 | 21.0% | 247 | 79 | 32.0% | 21.2%..42.3% | +11.0pp |  | risk-off+3hot:247 |
| y2020 | 6.0% | 310 | 0 | 0.0% | 0.0%..0.0% | -6.0pp |  | calm+0hot:148, watch+0hot:162 |
| y2020 | 8.0% | 747 | 28 | 3.7% | 2.1%..5.5% | -4.3pp |  | caution+0hot:97, caution+1hot:650 |
| y2020 | 10.0% | 270 | 32 | 11.9% | 5.9%..18.4% | +1.9pp |  | caution+2hot:270 |
| y2020 | 12.0% | 90 | 10 | 11.1% | 3.7%..19.5% | -0.9pp | YES | caution+3hot:66, elevated+1hot:24 |
| y2020 | 14.0% | 18 | 0 | 0.0% | 0.0%..0.0% | -14.0pp | YES | caution+4hot:10, elevated+2hot:8 |
| y2020 | 16.0% | 1 | 1 | 100.0% | 100.0%..100.0% | +84.0pp | YES | elevated+3hot:1 |
| y2020 | 17.0% | 46 | 12 | 26.1% | 7.2%..47.0% | +9.1pp | YES | risk-off+1hot:46 |
| y2020 | 19.0% | 95 | 25 | 26.3% | 11.5%..43.0% | +7.3pp | YES | risk-off+2hot:95 |
| y2020 | 21.0% | 100 | 30 | 30.0% | 14.5%..46.6% | +9.0pp |  | risk-off+3hot:100 |

## H21

| Window | n | Events | Base | Mean displayed | Gap | Brier | Base Brier | Brier skill | WACE | RWSCE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 8195 | 1446 | 17.6% | 18.0% | +0.4pp | 0.1379 | 0.1453 | 0.051 | 0.0229 | 0.0357 |
| y2006 | 5189 | 908 | 17.5% | 19.1% | +1.6pp | 0.1343 | 0.1444 | 0.070 | 0.0403 | 0.0501 |
| y2020 | 1666 | 294 | 17.6% | 19.4% | +1.8pp | 0.1326 | 0.1453 | 0.088 | 0.0610 | 0.0719 |

| Window | Displayed p | n | Events | Observed | 90% block CI | Obs-p | Thin | Composition |
|---|---:|---:|---:|---:|---|---:|---|---|
| full | 13.0% | 2144 | 241 | 11.2% | 8.1%..14.4% | -1.8pp |  | calm+0hot:1297, watch+0hot:847 |
| full | 16.0% | 3630 | 520 | 14.3% | 11.9%..17.0% | -1.7pp |  | caution+0hot:381, caution+1hot:3249 |
| full | 19.0% | 1159 | 222 | 19.2% | 15.0%..23.4% | +0.2pp |  | caution+2hot:1159 |
| full | 22.0% | 257 | 45 | 17.5% | 10.0%..26.1% | -4.5pp |  | caution+3hot:257 |
| full | 25.0% | 151 | 64 | 42.4% | 30.1%..55.0% | +17.4pp |  | caution+4hot:12, elevated+1hot:139 |
| full | 28.0% | 58 | 22 | 37.9% | 20.5%..53.9% | +9.9pp | YES | elevated+2hot:58 |
| full | 31.0% | 4 | 2 | 50.0% | 0.0%..100.0% | +19.0pp | YES | elevated+3hot:4 |
| full | 33.0% | 190 | 82 | 43.2% | 29.0%..56.4% | +10.2pp |  | risk-off+1hot:190 |
| full | 36.0% | 355 | 139 | 39.2% | 29.2%..49.2% | +3.2pp |  | risk-off+2hot:355 |
| full | 39.0% | 247 | 109 | 44.1% | 29.5%..56.7% | +5.1pp |  | risk-off+3hot:247 |
| y2006 | 13.0% | 932 | 67 | 7.2% | 4.3%..11.1% | -5.8pp |  | calm+0hot:390, watch+0hot:542 |
| y2006 | 16.0% | 2327 | 287 | 12.3% | 9.7%..15.4% | -3.7pp |  | caution+0hot:248, caution+1hot:2079 |
| y2006 | 19.0% | 908 | 176 | 19.4% | 14.7%..25.1% | +0.4pp |  | caution+2hot:908 |
| y2006 | 22.0% | 232 | 44 | 19.0% | 10.2%..28.2% | -3.0pp |  | caution+3hot:232 |
| y2006 | 25.0% | 94 | 43 | 45.7% | 28.1%..63.5% | +20.7pp | YES | caution+4hot:11, elevated+1hot:83 |
| y2006 | 28.0% | 47 | 17 | 36.2% | 16.4%..53.9% | +8.2pp | YES | elevated+2hot:47 |
| y2006 | 31.0% | 4 | 2 | 50.0% | 0.0%..100.0% | +19.0pp | YES | elevated+3hot:4 |
| y2006 | 33.0% | 89 | 37 | 41.6% | 25.4%..59.8% | +8.6pp | YES | risk-off+1hot:89 |
| y2006 | 36.0% | 309 | 126 | 40.8% | 30.1%..51.7% | +4.8pp |  | risk-off+2hot:309 |
| y2006 | 39.0% | 247 | 109 | 44.1% | 29.3%..57.3% | +5.1pp |  | risk-off+3hot:247 |
| y2020 | 13.0% | 300 | 4 | 1.3% | 0.0%..3.9% | -11.7pp |  | calm+0hot:141, watch+0hot:159 |
| y2020 | 16.0% | 746 | 91 | 12.2% | 7.4%..17.5% | -3.8pp |  | caution+0hot:96, caution+1hot:650 |
| y2020 | 19.0% | 270 | 67 | 24.8% | 13.8%..36.0% | +5.8pp |  | caution+2hot:270 |
| y2020 | 22.0% | 66 | 16 | 24.2% | 5.0%..45.5% | +2.2pp | YES | caution+3hot:66 |
| y2020 | 25.0% | 34 | 11 | 32.4% | 0.0%..61.5% | +7.4pp | YES | caution+4hot:10, elevated+1hot:24 |
| y2020 | 28.0% | 8 | 0 | 0.0% | 0.0%..0.0% | -28.0pp | YES | elevated+2hot:8 |
| y2020 | 31.0% | 1 | 1 | 100.0% | 100.0%..100.0% | +69.0pp | YES | elevated+3hot:1 |
| y2020 | 33.0% | 46 | 17 | 37.0% | 9.7%..69.4% | +4.0pp | YES | risk-off+1hot:46 |
| y2020 | 36.0% | 95 | 38 | 40.0% | 16.7%..60.5% | +4.0pp | YES | risk-off+2hot:95 |
| y2020 | 39.0% | 100 | 49 | 49.0% | 23.9%..69.1% | +10.0pp |  | risk-off+3hot:100 |

## Evidence ceiling

These are overlapping historical replay windows under the current code, not genuinely issued probabilities. Exact probability cells are not post-hoc bins: they are the discrete values the shipped function emits.

No result in this audit authorizes a retune. Issued/prospective forecast evidence remains separate and higher authority.

