# Label audit: an apparent safety advantage is not invariant to risk units

Status: POST-RESULT DESCRIPTIVE DIAGNOSTIC, NOT A NEW GATE OR CONFIRMATORY TEST.

The first pilot showed fewer volatility-scaled downside-first events under R, but no improvement in fixed 10% adverse excursions. This audit examines that discrepancy without altering candidates, registered outcomes or thresholds. It does not audit or invalidate the proprietary dot's close-ATR hold result.

Code: `label_audit.py`, committed at `a3becb06a891b94c070ea6197a0b2dad33b3b8d1`; SHA256 `d94cfad711a174c8c3a63c385c1c178a60ca465c3f5373489d95b31548567826`. Process 57087 exited 0. Full local `LABEL_AUDIT_RESULTS.json` SHA256 `90628f757757488a00ee265ada7e2cfcf66bd554414f2c576da3f25310db726e`. Both public input hashes were asserted unchanged; all numerical observations remain <= 2002-12-31. There are exactly the original 8,902 events.

R is the registered industry repair proxy: a positive trailing21 return both absolutely and relative to the market among previously washed-out industries. R absent: 7,247 events / 773 months. R present: 1,655 events / 411 months.

## Observed differences

| Diagnostic | R absent | R present |
|---|---:|---:|
| Mean trailing63 annualized daily volatility | 26.83% | 31.10% |
| Mean next63 annualized daily volatility | 26.23% | 26.60% |
| Median next63 / trailing63 volatility ratio | 0.963 | 0.844 |
| Mean registered upside barrier from entry | +17.40% | +20.38% |
| Mean registered downside barrier from entry | -13.96% | -16.01% |
| Median log-distance above trailing21 low | 1.79% | 7.12% |
| Registered volatility-scaled upper-first | 30.11% | 25.02% |
| Registered volatility-scaled lower-first | 27.53% | 22.78% |
| Registered volatility-scaled unresolved | 42.36% | 52.21% |
| Fixed +10%/-10% upper-first sensitivity | 40.71% | 41.81% |
| Fixed +10%/-10% lower-first sensitivity | 32.11% | 32.33% |
| Fixed +10%/-10% unresolved sensitivity | 27.18% | 25.86% |
| Any closing loss >=10%, registered Bad10 | 35.06% | 35.05% |

Volatility-scaled barriers are symmetric in log returns, not simple percentages. The fixed +/-10% sensitivity is symmetric in simple-return percentages. The table reports mean percentage barrier widths, not one common stop for every event. Mean forward volatility and mean ratios are different aggregations; neither should be derived by dividing the displayed group means. Log-distance is not a simple percentage price gain.

The repaired group entered with wider volatility-scaled barriers, despite similar average subsequent realized volatility. The reduction in lower-first events disappears under a fixed 10% loss boundary: 32.33% versus 32.11%. This is a concrete sensitivity of the apparent safety result to the risk units and barrier geometry. It does not by itself establish a causal decomposition or prove all of the original difference is explained by volatility.

Bad10 and lower-first are also distinct: an event may hit its upside target first and later sustain a 10% closing loss. All first-passage sensitivities use closes, not intraday tradable stops, and do not model gap fills.

## Research consequence

A candidate gate must be evaluated jointly on executable-entry path loss, the original low-hold label, first-passage upside/downside/timeout, excess and absolute returns, coverage, and entry delay. At least one economically fixed or position-risk-comparable loss measure is needed alongside volatility/ATR-normalized labels. A gain in hold rate cannot be converted directly into a calibrated probability of a profitable trade.

This is a measurement warning for future stock tests, not a repudiation of the existing proprietary-dot evidence. The dot event, close-ATR label, stock panel and same-swing T1 comparison were not reproduced here. Forward volatility was read only as an outcome diagnostic and was never used to decide whether an entry was permitted.
