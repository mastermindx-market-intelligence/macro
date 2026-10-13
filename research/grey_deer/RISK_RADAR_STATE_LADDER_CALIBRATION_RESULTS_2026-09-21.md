# Risk Radar State-Ladder Calibration Study — Results

Protocol commit: `e9ff3d234df1f50137bfa38a50995a70f06c1164`.

Descriptive reconstructed-history research only; no live model or probability changed.

## H5 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1304 | 28 | 2.1% | 1.3%..3.2% | 2.0% | +0.1pp | 0.61x |  |
| full | watch | 935 | 12 | 1.3% | 0.5%..2.2% | 2.0% | -0.7pp | 0.37x |  |
| full | caution | 4997 | 101 | 2.0% | 1.6%..2.6% | 3.0% | -1.0pp | 0.58x |  |
| full | elevated | 204 | 29 | 14.2% | 8.9%..19.5% | 5.0% | +9.2pp | 4.05x |  |
| full | risk-off | 771 | 118 | 15.3% | 11.7%..19.3% | 8.0% | +7.3pp | 4.36x |  |
| y2006 | calm | 397 | 6 | 1.5% | 0.5%..2.9% | 2.0% | -0.5pp | 0.40x |  |
| y2006 | watch | 630 | 8 | 1.3% | 0.3%..2.3% | 2.0% | -0.7pp | 0.34x |  |
| y2006 | caution | 3417 | 69 | 2.0% | 1.4%..2.6% | 3.0% | -1.0pp | 0.54x |  |
| y2006 | elevated | 137 | 20 | 14.6% | 7.6%..22.5% | 5.0% | +9.6pp | 3.88x |  |
| y2006 | risk-off | 624 | 93 | 14.9% | 11.0%..18.9% | 8.0% | +6.9pp | 3.96x |  |
| y2020 | calm | 148 | 0 | 0.0% | 0.0%..0.0% | 2.0% | -2.0pp | 0.00x |  |
| y2020 | watch | 199 | 0 | 0.0% | 0.0%..0.0% | 2.0% | -2.0pp | 0.00x |  |
| y2020 | caution | 1078 | 24 | 2.2% | 1.1%..3.5% | 3.0% | -0.8pp | 0.62x |  |
| y2020 | elevated | 33 | 4 | 12.1% | 0.0%..27.8% | 5.0% | +7.1pp | 3.40x | YES |
| y2020 | risk-off | 224 | 32 | 14.3% | 8.4%..20.6% | 8.0% | +6.3pp | 4.00x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -0.9pp | -2.0pp..+0.3pp | NO |
| full | watch->caution | +0.7pp | -0.2pp..+1.5pp | NO |
| full | caution->elevated | +12.2pp | +6.9pp..+17.4pp | NO |
| full | elevated->risk-off | +1.1pp | -5.2pp..+7.6pp | NO |
| y2006 | calm->watch | -0.2pp | -1.7pp..+1.2pp | NO |
| y2006 | watch->caution | +0.7pp | -0.4pp..+1.7pp | NO |
| y2006 | caution->elevated | +12.6pp | +5.6pp..+20.4pp | NO |
| y2006 | elevated->risk-off | +0.3pp | -8.5pp..+8.0pp | NO |
| y2020 | calm->watch | +0.0pp | +0.0pp..+0.0pp | YES |
| y2020 | watch->caution | +2.2pp | +1.1pp..+3.5pp | YES |
| y2020 | caution->elevated | +9.9pp | -2.6pp..+25.6pp | YES |
| y2020 | elevated->risk-off | +2.2pp | -13.6pp..+16.3pp | YES |

## H10 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1304 | 76 | 5.8% | 3.9%..8.0% | 6.0% | -0.2pp | 0.69x |  |
| full | watch | 935 | 44 | 4.7% | 3.0%..6.5% | 6.0% | -1.3pp | 0.55x |  |
| full | caution | 4992 | 321 | 6.4% | 5.4%..7.6% | 8.0% | -1.6pp | 0.76x |  |
| full | elevated | 204 | 51 | 25.0% | 16.9%..33.9% | 12.0% | +13.0pp | 2.94x |  |
| full | risk-off | 771 | 206 | 26.7% | 21.3%..32.4% | 17.0% | +9.7pp | 3.14x |  |
| y2006 | calm | 397 | 15 | 3.8% | 1.4%..7.0% | 6.0% | -2.2pp | 0.45x |  |
| y2006 | watch | 630 | 20 | 3.2% | 1.6%..5.3% | 6.0% | -2.8pp | 0.38x |  |
| y2006 | caution | 3412 | 201 | 5.9% | 4.6%..7.3% | 8.0% | -2.1pp | 0.70x |  |
| y2006 | elevated | 137 | 36 | 26.3% | 15.4%..37.3% | 12.0% | +14.3pp | 3.12x |  |
| y2006 | risk-off | 624 | 166 | 26.6% | 20.1%..33.1% | 17.0% | +9.6pp | 3.16x |  |
| y2020 | calm | 148 | 0 | 0.0% | 0.0%..0.0% | 6.0% | -6.0pp | 0.00x |  |
| y2020 | watch | 199 | 0 | 0.0% | 0.0%..0.0% | 6.0% | -6.0pp | 0.00x |  |
| y2020 | caution | 1073 | 68 | 6.3% | 3.9%..8.9% | 8.0% | -1.7pp | 0.77x |  |
| y2020 | elevated | 33 | 8 | 24.2% | 5.5%..46.7% | 12.0% | +12.2pp | 2.95x | YES |
| y2020 | risk-off | 224 | 62 | 27.7% | 16.5%..38.2% | 17.0% | +10.7pp | 3.36x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -1.1pp | -3.4pp..+1.1pp | NO |
| full | watch->caution | +1.7pp | -0.2pp..+3.6pp | NO |
| full | caution->elevated | +18.6pp | +10.5pp..+27.5pp | NO |
| full | elevated->risk-off | +1.7pp | -7.5pp..+11.2pp | NO |
| y2006 | calm->watch | -0.6pp | -3.5pp..+2.3pp | NO |
| y2006 | watch->caution | +2.7pp | +0.8pp..+4.6pp | NO |
| y2006 | caution->elevated | +20.4pp | +9.7pp..+31.1pp | NO |
| y2006 | elevated->risk-off | +0.3pp | -11.4pp..+12.0pp | NO |
| y2020 | calm->watch | +0.0pp | +0.0pp..+0.0pp | YES |
| y2020 | watch->caution | +6.3pp | +3.9pp..+8.9pp | YES |
| y2020 | caution->elevated | +17.9pp | -1.0pp..+40.3pp | YES |
| y2020 | elevated->risk-off | +3.4pp | -19.1pp..+22.8pp | YES |

## H21 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1297 | 158 | 12.2% | 8.4%..16.5% | 13.0% | -0.8pp | 0.69x |  |
| full | watch | 932 | 93 | 10.0% | 7.1%..12.9% | 13.0% | -3.0pp | 0.57x |  |
| full | caution | 4991 | 786 | 15.7% | 13.3%..18.3% | 16.0% | -0.3pp | 0.89x |  |
| full | elevated | 204 | 86 | 42.2% | 30.9%..53.1% | 25.0% | +17.2pp | 2.39x |  |
| full | risk-off | 771 | 323 | 41.9% | 33.8%..49.5% | 33.0% | +8.9pp | 2.37x |  |
| y2006 | calm | 390 | 31 | 7.9% | 2.8%..14.5% | 13.0% | -5.1pp | 0.45x |  |
| y2006 | watch | 627 | 46 | 7.3% | 4.1%..10.7% | 13.0% | -5.7pp | 0.42x |  |
| y2006 | caution | 3411 | 506 | 14.8% | 12.1%..17.8% | 16.0% | -1.2pp | 0.85x |  |
| y2006 | elevated | 137 | 60 | 43.8% | 29.1%..58.6% | 25.0% | +18.8pp | 2.50x |  |
| y2006 | risk-off | 624 | 265 | 42.5% | 32.9%..51.6% | 33.0% | +9.5pp | 2.43x |  |
| y2020 | calm | 141 | 0 | 0.0% | 0.0%..0.0% | 13.0% | -13.0pp | 0.00x |  |
| y2020 | watch | 196 | 9 | 4.6% | 0.0%..12.2% | 13.0% | -8.4pp | 0.26x |  |
| y2020 | caution | 1072 | 177 | 16.5% | 10.8%..22.6% | 16.0% | +0.5pp | 0.94x |  |
| y2020 | elevated | 33 | 10 | 30.3% | 6.1%..60.0% | 25.0% | +5.3pp | 1.72x | YES |
| y2020 | risk-off | 224 | 98 | 43.8% | 27.2%..59.6% | 33.0% | +10.7pp | 2.48x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -2.2pp | -6.6pp..+1.9pp | NO |
| full | watch->caution | +5.8pp | +2.6pp..+9.0pp | NO |
| full | caution->elevated | +26.4pp | +14.8pp..+37.3pp | NO |
| full | elevated->risk-off | -0.3pp | -11.7pp..+10.4pp | NO |
| y2006 | calm->watch | -0.6pp | -6.9pp..+4.8pp | NO |
| y2006 | watch->caution | +7.5pp | +3.8pp..+11.2pp | NO |
| y2006 | caution->elevated | +29.0pp | +14.0pp..+44.3pp | NO |
| y2006 | elevated->risk-off | -1.3pp | -14.7pp..+12.9pp | NO |
| y2020 | calm->watch | +4.6pp | +0.0pp..+12.2pp | YES |
| y2020 | watch->caution | +11.9pp | +3.1pp..+20.6pp | YES |
| y2020 | caution->elevated | +13.8pp | -10.5pp..+43.1pp | YES |
| y2020 | elevated->risk-off | +13.4pp | -13.8pp..+36.2pp | YES |

## Evidence ceiling

Daily forward windows overlap, so the intervals use the preregistered moving-block bootstrap. This is a current-code historical reconstruction, not genuinely issued forecast history.

Configured probabilities are shown as diagnostics only. Differences do not authorize retuning; any model change requires a separate preregistered candidate and promotion review.
