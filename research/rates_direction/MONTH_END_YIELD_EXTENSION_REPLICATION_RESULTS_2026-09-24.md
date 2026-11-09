# Direct Treasury-yield month-end extension replication — PASS with current-regime caution

## Predeclared result

The known TLT/IEF/LQD month-end bond-price extension effect translates directly into
Treasury yields over the frozen 2007-01-01 through 2026-09-22 source interval.

Freeze commit: cfef07d2424a27604698c65eed03df3e0fe8c747
Freeze time: 2026-09-25T01:33:15.401908Z

The frozen sample correctly excludes the incomplete September 2026 month, leaving
236 complete month-end observations from 2007-01-31 through 2026-08-31.

Lower yields were the predeclared expected sign. Every tenor passed both raw
last-day-change and same-month excess gates:

| Cell | n | Mean bp | HAC t | p | BH q | Split halves | Gate |
|---|---:|---:|---:|---:|---:|---|---|
| DGS2 raw | 236 | -1.288 | -4.127 | <0.0001 | <0.0001 | -1.797 / -0.780 | PASS |
| DGS2 excess | 236 | -1.337 | -4.185 | <0.0001 | <0.0001 | -1.709 / -0.966 | PASS |
| DGS5 raw | 236 | -1.555 | -4.216 | <0.0001 | <0.0001 | -2.161 / -0.949 | PASS |
| DGS5 excess | 236 | -1.622 | -4.303 | <0.0001 | <0.0001 | -2.115 / -1.129 | PASS |
| DGS10 raw, HEADLINE | 236 | -1.186 | -3.267 | 0.0011 | 0.0015 | -1.534 / -0.839 | PASS |
| DGS10 excess | 236 | -1.242 | -3.276 | 0.0011 | 0.0015 | -1.481 / -1.002 | PASS |
| DGS30 raw | 236 | -1.144 | -3.167 | 0.0015 | 0.0015 | -1.669 / -0.619 | PASS |
| DGS30 excess | 236 | -1.211 | -3.183 | 0.0015 | 0.0015 | -1.659 / -0.763 | PASS |

The predeclared primary therefore passes: DGS10 raw and excess are both negative,
HAC t <= -2, BH q <= 0.10, and both chronological halves retain the sign.

These eight cells are strongly dependent term-structure observations, not eight
independent discoveries. Their role is tenor breadth inside one calendar-flow mechanism.

## Disjoint historical context

The exact same DGS10 construction before the TLT/IEF source window is also negative.
For 485 complete months from February 1962 through June 2002:

- raw last-day DGS10 change: -0.703 bp, HAC t=-2.581, p=0.0098
- excess versus other days: -0.745 bp, HAC t=-2.614, p=0.0090
- both chronological halves retain the negative sign

This was predeclared as historical context, not a promotion rescue. It nevertheless
shows the yield-space sign predates the ETF sample used by the original family.

## Source-clock qualification

The 236 DGS10 month-end event dates match the repository's incumbent
engine.rebalance_calendar.month_end_sessions() NYSE-session owner exactly: 236/236,
with zero DGS observations outside the calendar set and zero calendar month-ends
missing from the DGS event set through August 2026.

That means a prospective calendar flag does not need to infer future dates from the
yield series. The existing calendar owner can identify the date in advance.

## Same-author integrity

An independent arithmetic reconstruction from the four raw FRED parquets, without
importing the study module, reproduced all eight primary sample counts and means.
The pre-registration TrialLedger prefix hash is unchanged and exactly eight
direct-yield configs were appended to the existing d2_rates_calendar_flows family,
raising its literal width from 13 to 21.

Evidence:
- registration SHA256 deed993281afeeabdb5f86f8554ddf65794eae45e0a3de23a041ee88f6626ff7
- result SHA256 7ecd8a9d89b24c45da83603991d2eb6a8b7bede9dbe109adc8bf0a6f7c0aa20c
- same-author integrity file:
  research/rates_direction/month_end_yield_extension_replication_integrity_v1.json

A conservative post-result diagnostic multiplying each new cell's rounded p-value by
the full 21-trial family width still leaves the largest bound at 0.0315. This is not
the preregistered correction and is reported only as a robustness diagnostic.

## Critical current-regime diagnostics — NOT promotion evidence

The long-history PASS is not enough to turn this directly into a current rate call.

Post-result failure-cluster inspection found material heterogeneity:

- quarter-end months (Mar/Jun/Sep/Dec): DGS10 raw +0.295 bp, t=+0.502, p=0.616
- non-quarter month-ends: DGS10 raw -1.918 bp, t=-4.370
- 2022-2026: DGS10 raw -0.250 bp, t=-0.387, p=0.699
- 2022-2026 excess: -0.536 bp, t=-0.767, p=0.443
- after trimming the largest 5% absolute month-end DGS10 moves: raw -0.787 bp,
  t=-2.688, p=0.0072

The quarter/non-quarter and recent-era cuts were opened only after the primary result.
They must not be promoted as selected trading rules. They do establish a product
caution: the aggregate historical effect is neither uniform across quarter-ends nor
demonstrably strong in the latest 2022-2026 slice.

Five-year descriptive raw means were:
- 2007-2011: -2.317 bp
- 2012-2016: -0.650 bp
- 2017-2021: -1.467 bp
- 2022-2026: -0.250 bp

So the correct interpretation is:

**a real long-run month-end duration-flow tendency exists in both bond prices and
Treasury yields, but current directional authority is not established.**

## Product ruling

This result is strong enough to retain month-end duration extension as a source-backed
RIC calendar context and to prospectively validate its current usefulness.

It is NOT strong enough to:
- add a hawkish/easing score leg;
- assume every quarter-end should lower yields;
- override CPI/PCE/FOMC or other release catalysts;
- drive equity risk-on/off state;
- create ranking, sizing, gating or trade authority.

The next validation must be forward-only from the frozen rule, using the existing
rebalance calendar for event dates. Quarter-end status may be reported as a diagnostic
flag but cannot alter the frozen generic sign without a separately registered future
hypothesis.

Authority remains false.
