# Risk Radar State-Ladder Calibration Study — Results

Protocol commit: `22e779b1f4c7fbb27c1e204667d917c1d92727fa`.

Descriptive reconstructed-history research only; no live model or probability changed.

## H5 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1304 | 28 | 2.1% | 1.3%..3.2% | 2.0% | +0.1pp | 0.61x |  |
| full | watch | 766 | 10 | 1.3% | 0.5%..2.3% | 2.0% | -0.7pp | 0.37x |  |
| full | caution | 5130 | 100 | 1.9% | 1.5%..2.5% | 3.0% | -1.1pp | 0.56x |  |
| full | elevated | 189 | 23 | 12.2% | 7.5%..16.9% | 5.0% | +7.2pp | 3.47x |  |
| full | risk-off | 822 | 127 | 15.5% | 11.9%..19.3% | 8.0% | +7.5pp | 4.40x |  |
| y2006 | calm | 397 | 6 | 1.5% | 0.5%..2.9% | 2.0% | -0.5pp | 0.40x |  |
| y2006 | watch | 474 | 6 | 1.3% | 0.2%..2.5% | 2.0% | -0.7pp | 0.34x |  |
| y2006 | caution | 3538 | 68 | 1.9% | 1.4%..2.5% | 3.0% | -1.1pp | 0.51x |  |
| y2006 | elevated | 124 | 14 | 11.3% | 4.9%..18.3% | 5.0% | +6.3pp | 3.00x |  |
| y2006 | risk-off | 672 | 102 | 15.2% | 11.3%..19.1% | 8.0% | +7.2pp | 4.03x |  |
| y2020 | calm | 148 | 0 | 0.0% | 0.0%..0.0% | 2.0% | -2.0pp | 0.00x |  |
| y2020 | watch | 121 | 0 | 0.0% | 0.0%..0.0% | 2.0% | -2.0pp | 0.00x |  |
| y2020 | caution | 1138 | 24 | 2.1% | 1.1%..3.3% | 3.0% | -0.9pp | 0.59x |  |
| y2020 | elevated | 36 | 0 | 0.0% | 0.0%..0.0% | 5.0% | -5.0pp | 0.00x | YES |
| y2020 | risk-off | 239 | 36 | 15.1% | 8.8%..21.6% | 8.0% | +7.1pp | 4.22x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -0.8pp | -2.1pp..+0.3pp | NO |
| full | watch->caution | +0.6pp | -0.3pp..+1.5pp | NO |
| full | caution->elevated | +10.2pp | +5.6pp..+15.0pp | NO |
| full | elevated->risk-off | +3.3pp | -2.7pp..+9.4pp | NO |
| y2006 | calm->watch | -0.2pp | -1.8pp..+1.3pp | NO |
| y2006 | watch->caution | +0.7pp | -0.6pp..+1.8pp | NO |
| y2006 | caution->elevated | +9.4pp | +3.1pp..+16.5pp | NO |
| y2006 | elevated->risk-off | +3.9pp | -3.9pp..+10.6pp | NO |
| y2020 | calm->watch | +0.0pp | +0.0pp..+0.0pp | NO |
| y2020 | watch->caution | +2.1pp | +1.1pp..+3.3pp | NO |
| y2020 | caution->elevated | -2.1pp | -3.3pp..-1.1pp | NO |
| y2020 | elevated->risk-off | +15.1pp | +8.8pp..+21.6pp | NO |

## H10 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1304 | 76 | 5.8% | 3.9%..8.0% | 6.0% | -0.2pp | 0.69x |  |
| full | watch | 766 | 40 | 5.2% | 3.2%..7.4% | 6.0% | -0.8pp | 0.61x |  |
| full | caution | 5125 | 322 | 6.3% | 5.2%..7.4% | 8.0% | -1.7pp | 0.74x |  |
| full | elevated | 189 | 42 | 22.2% | 14.3%..30.9% | 12.0% | +10.2pp | 2.61x |  |
| full | risk-off | 822 | 218 | 26.5% | 21.3%..31.7% | 17.0% | +9.5pp | 3.12x |  |
| y2006 | calm | 397 | 15 | 3.8% | 1.4%..7.0% | 6.0% | -2.2pp | 0.45x |  |
| y2006 | watch | 474 | 16 | 3.4% | 1.4%..5.9% | 6.0% | -2.6pp | 0.40x |  |
| y2006 | caution | 3533 | 202 | 5.7% | 4.5%..7.1% | 8.0% | -2.3pp | 0.68x |  |
| y2006 | elevated | 124 | 28 | 22.6% | 12.1%..33.8% | 12.0% | +10.6pp | 2.68x |  |
| y2006 | risk-off | 672 | 177 | 26.3% | 20.1%..32.8% | 17.0% | +9.3pp | 3.13x |  |
| y2020 | calm | 148 | 0 | 0.0% | 0.0%..0.0% | 6.0% | -6.0pp | 0.00x |  |
| y2020 | watch | 121 | 0 | 0.0% | 0.0%..0.0% | 6.0% | -6.0pp | 0.00x |  |
| y2020 | caution | 1133 | 68 | 6.0% | 3.7%..8.4% | 8.0% | -2.0pp | 0.73x |  |
| y2020 | elevated | 36 | 3 | 8.3% | 0.0%..22.9% | 12.0% | -3.7pp | 1.01x | YES |
| y2020 | risk-off | 239 | 67 | 28.0% | 17.3%..38.5% | 17.0% | +11.0pp | 3.41x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -0.6pp | -3.1pp..+1.9pp | NO |
| full | watch->caution | +1.1pp | -1.2pp..+3.2pp | NO |
| full | caution->elevated | +15.9pp | +8.1pp..+24.2pp | NO |
| full | elevated->risk-off | +4.3pp | -4.7pp..+12.9pp | NO |
| y2006 | calm->watch | -0.4pp | -3.8pp..+2.9pp | NO |
| y2006 | watch->caution | +2.3pp | -0.0pp..+4.4pp | NO |
| y2006 | caution->elevated | +16.9pp | +6.4pp..+28.0pp | NO |
| y2006 | elevated->risk-off | +3.8pp | -7.9pp..+15.7pp | NO |
| y2020 | calm->watch | +0.0pp | +0.0pp..+0.0pp | YES |
| y2020 | watch->caution | +6.0pp | +3.7pp..+8.4pp | YES |
| y2020 | caution->elevated | +2.3pp | -6.9pp..+16.9pp | YES |
| y2020 | elevated->risk-off | +19.7pp | +2.7pp..+33.7pp | YES |

## H21 state cells

| Window | State | n | Events | Observed | 90% block CI | Configured | Obs-config | Lift | Thin |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| full | calm | 1297 | 158 | 12.2% | 8.4%..16.5% | 13.0% | -0.8pp | 0.69x |  |
| full | watch | 763 | 83 | 10.9% | 7.7%..14.3% | 13.0% | -2.1pp | 0.62x |  |
| full | caution | 5124 | 790 | 15.4% | 13.1%..17.9% | 16.0% | -0.6pp | 0.87x |  |
| full | elevated | 189 | 74 | 39.2% | 27.7%..50.0% | 25.0% | +14.2pp | 2.22x |  |
| full | risk-off | 822 | 341 | 41.5% | 33.6%..49.1% | 33.0% | +8.5pp | 2.35x |  |
| y2006 | calm | 390 | 31 | 7.9% | 2.8%..14.5% | 13.0% | -5.1pp | 0.45x |  |
| y2006 | watch | 471 | 36 | 7.6% | 4.2%..11.1% | 13.0% | -5.4pp | 0.44x |  |
| y2006 | caution | 3532 | 510 | 14.4% | 11.7%..17.5% | 16.0% | -1.6pp | 0.83x |  |
| y2006 | elevated | 124 | 50 | 40.3% | 24.7%..55.2% | 25.0% | +15.3pp | 2.30x |  |
| y2006 | risk-off | 672 | 281 | 41.8% | 32.7%..50.9% | 33.0% | +8.8pp | 2.39x |  |
| y2020 | calm | 141 | 0 | 0.0% | 0.0%..0.0% | 13.0% | -13.0pp | 0.00x |  |
| y2020 | watch | 118 | 4 | 3.4% | 0.0%..10.0% | 13.0% | -9.6pp | 0.19x |  |
| y2020 | caution | 1132 | 182 | 16.1% | 10.6%..21.9% | 16.0% | +0.1pp | 0.91x |  |
| y2020 | elevated | 36 | 4 | 11.1% | 0.0%..27.3% | 25.0% | -13.9pp | 0.63x | YES |
| y2020 | risk-off | 239 | 104 | 43.5% | 27.2%..59.5% | 33.0% | +10.5pp | 2.47x |  |

| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |
|---|---|---:|---|---|
| full | calm->watch | -1.3pp | -5.9pp..+3.0pp | NO |
| full | watch->caution | +4.5pp | +1.0pp..+8.0pp | NO |
| full | caution->elevated | +23.7pp | +12.1pp..+34.9pp | NO |
| full | elevated->risk-off | +2.3pp | -8.9pp..+14.0pp | NO |
| y2006 | calm->watch | -0.3pp | -6.4pp..+5.0pp | NO |
| y2006 | watch->caution | +6.8pp | +3.4pp..+10.5pp | NO |
| y2006 | caution->elevated | +25.9pp | +10.1pp..+41.0pp | NO |
| y2006 | elevated->risk-off | +1.5pp | -13.4pp..+17.6pp | NO |
| y2020 | calm->watch | +3.4pp | +0.0pp..+10.0pp | NO |
| y2020 | watch->caution | +12.7pp | +5.0pp..+20.0pp | NO |
| y2020 | caution->elevated | -5.0pp | -18.2pp..+13.0pp | NO |
| y2020 | elevated->risk-off | +32.4pp | +16.4pp..+50.9pp | NO |

## Evidence ceiling

Daily forward windows overlap, so the intervals use the preregistered moving-block bootstrap. This is a current-code historical reconstruction, not genuinely issued forecast history.

Configured probabilities are shown as diagnostics only. Differences do not authorize retuning; any model change requires a separate preregistered candidate and promotion review.

