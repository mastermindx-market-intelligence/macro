# Skew-overlap audit receipt — 2026-09-22

- Ledger: `data/options_skew/snapshots.parquet`
- ThetaData store: `/Users/chriswong/theta-ops-wt/data/thetadata_eod`
- Keys compared: **3965** (limit=none, skipped=8410)
- Sign agreement rate: **0.603279**
- |delta skew| p50/p90/max: **0.0379 / 0.167 / 3.9529**
- Sign buckets: match=**2392**, flip=**1563**, zero=**0** (match + flip + zero == keys_compared)

## Top 10 worst keys (by |delta skew|)

| date | underlying | legacy_skew | new_skew | delta_skew |
| --- | --- | --- | --- | --- |
| 2026-06-30 | MQ | 0.1877 | 4.1406 | -3.9529 |
| 2026-06-25 | MQ | 0.0465 | 3.556 | -3.5095 |
| 2026-06-22 | MQ | -0.0463 | 3.1598 | -3.2061 |
| 2026-06-29 | ALT | 0.2207 | -2.6367 | 2.8574 |
| 2026-07-01 | ALT | 0.1806 | 2.5936 | -2.413 |
| 2026-06-26 | ALT | -0.4242 | -2.715 | 2.2908 |
| 2026-06-24 | MQ | -0.1058 | 2.0957 | -2.2015 |
| 2026-06-23 | ALT | 0.6927 | 2.8244 | -2.1317 |
| 2026-07-02 | ALT | 0.4531 | -1.4902 | 1.9433 |
| 2026-06-23 | MQ | 0.0382 | -1.6332 | 1.6714 |

## Skipped keys (8410)

| date | underlying | reason |
| --- | --- | --- |
| 2026-06-21 | AAPL | no_chain |
| 2026-06-21 | AMD | no_chain |
| 2026-06-21 | DIA | no_chain |
| 2026-06-21 | IWM | no_chain |
| 2026-06-21 | META | no_chain |
| 2026-06-21 | MSFT | no_chain |
| 2026-06-21 | NVDA | no_chain |
| 2026-06-21 | QQQ | no_chain |
| 2026-06-21 | SPY | no_chain |
| 2026-06-21 | TSLA | no_chain |
| 2026-06-21 | AAL | no_chain |
| 2026-06-21 | ABNB | no_chain |
| 2026-06-21 | ACLS | no_chain |
| 2026-06-21 | ADBE | no_chain |
| 2026-06-21 | ADI | no_chain |
| 2026-06-21 | AEIS | no_chain |
| 2026-06-21 | AEP | no_chain |
| 2026-06-21 | AFRM | no_chain |
| 2026-06-21 | ALAB | no_chain |
| 2026-06-21 | ALB | no_chain |
| 2026-06-21 | ALHC | no_chain |
| 2026-06-21 | ALM | no_chain |
| 2026-06-21 | ALT | no_chain |
| 2026-06-21 | AMAT | no_chain |
| 2026-06-21 | AME | no_chain |
| 2026-06-21 | AMGN | no_chain |
| 2026-06-21 | AMZN | no_chain |
| 2026-06-21 | ANET | no_chain |
| 2026-06-21 | APH | no_chain |
| 2026-06-21 | APLD | no_chain |
| 2026-06-21 | APP | no_chain |
| 2026-06-21 | ARM | no_chain |
| 2026-06-21 | ASPI | no_chain |
| 2026-06-21 | ASTS | no_chain |
| 2026-06-21 | AVAV | no_chain |
| 2026-06-21 | AVGO | no_chain |
| 2026-06-21 | AXON | no_chain |
| 2026-06-21 | AXP | no_chain |
| 2026-06-21 | AZN | no_chain |
| 2026-06-21 | AZO | no_chain |
| 2026-06-21 | BA | no_chain |
| 2026-06-21 | BBY | no_chain |
| 2026-06-21 | BJ | no_chain |
| 2026-06-21 | BKNG | no_chain |
| 2026-06-21 | BKR | no_chain |
| 2026-06-21 | BKSY | no_chain |
| 2026-06-21 | BLD | no_chain |
| 2026-06-21 | BLDR | no_chain |
| 2026-06-21 | BTDR | no_chain |
| 2026-06-21 | BURL | no_chain |
| ... | ... | (+8360 more) |
