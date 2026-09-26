# Month-end extension: direct Treasury-yield translation replication v1

Parent: WS:RATES-INFLATION-COMMAND / operation rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind a29161fa0a44cca9927afe042b5f7ea25aae1736,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Why this amendment exists

The pre-registered d2_rates_calendar_flows family already found a robust month-end
bond-price effect:
- TLT last-business-day mean return +0.183%, HAC t=3.627
- IEF +0.110%, HAC t=5.017
- same-sign split halves and same-month baselines passed
- later LQD replication also passed

That evidence is useful, but the current rates-direction program needs a result stated
directly in yield space rather than silently assuming ETF return direction translates
one-for-one into DGS10 direction.

This is a source-translation replication, not an independent untouched discovery.
The ETF result is already known. The direct-yield outcomes below have not been opened
for this exact construction before freeze.

## Family / multiple-testing continuity

Append this amendment to the EXISTING TrialLedger family:
d2_rates_calendar_flows.

Existing literal family size before this amendment must equal 13. Add exactly eight
configs:
- DGS2 raw last-day change
- DGS2 excess vs same-month other-day change
- DGS5 raw / excess
- DGS10 raw / excess
- DGS30 raw / excess

No new family is permitted for this mechanism.

## Source and sample

Existing FRED daily market-yield stores only:
- data/fred/DGS2.parquet / us2y
- data/fred/DGS5.parquet / us5y
- data/fred/DGS10.parquet / us10y
- data/fred/DGS30.parquet / us30y

Primary common modern sample:
2007-01-01 through 2026-09-22 inclusive.

2007 is chosen before result access because all four tenors have continuous modern-era
coverage after the historical 30Y issuance gap. This interval overlaps the known ETF
study and is therefore confirmatory/source-translation evidence, not a pristine
holdout.

Historical context, reported separately and never used for promotion:
DGS10 observations before 2002-07-30, the start of the TLT/IEF price history used in
the original family. This asks whether the sign was visible before the ETF test window.
It is not certified untouched by all prior company research.

## Construction

For each tenor:
1. sort finite daily yield observations
2. daily_change_bp = (yield[t] - yield[t-1]) * 100
3. within each calendar month, identify the final finite observation in that month
4. last_day_change_bp = daily_change_bp on that final observation
5. other_day_mean_bp = mean daily_change_bp on all other finite observations in that
   same month
6. excess_bp = last_day_change_bp - other_day_mean_bp

A calendar month is admitted only when the declared sample contains that whole month;
source-cutoff partial first/last months are excluded even if they already contain 5+
finite changes. Among complete months, skip any month with fewer than 5 finite daily
changes. One observation per month enters inference.

Expected sign from the validated bond-price extension mechanism:
- raw last-day yield change < 0
- excess versus other days < 0

No magnitude threshold, month selection, regime filter, holiday exception or parameter
search is authorized.

## Statistics and gates

For each of the eight primary cells:
- one monthly observation per event month
- Newey-West HAC lag = min(4, floor(sqrt(n))), minimum 2 when n permits
- two-sided p-value from the incumbent engine.validation.newey_west_tstat
- Benjamini-Hochberg FDR across ALL eight new cells, while retaining the existing
  d2_rates_calendar_flows family width in the TrialLedger

Headline cell: DGS10 raw last-day yield change.

A tenor is directly confirmed only if BOTH its raw and excess cells satisfy:
- mean < 0
- HAC t <= -2
- BH q <= 0.10
- first-half mean < 0 AND second-half mean < 0

The amendment-level primary passes only if DGS10 is directly confirmed.

DGS2/DGS5/DGS30 are confirmatory term-structure breadth. Their failure does not
retroactively erase the already-validated TLT/IEF/LQD price effect; it limits how the
rates-direction system may translate that mechanism into tenor-specific yield claims.

## Historical context

On DGS10 pre-2002-07-30:
- compute the identical raw/excess month-end statistics
- report sign and HAC t
- no BH promotion test and no decision rescue

If modern DGS10 fails, a positive-looking historical context cannot rescue it.

## Product implication if DGS10 passes

A pass may justify adding a DISPLAY-ONLY calendar-flow context to the existing
Rates & Inflation Command on the last Treasury observation/trading day of a month:
"month-end duration extension historically biases Treasury prices higher / yields
lower."

It must not automatically change the RIC net hawkish/easing score, equity posture,
rank, size, gate or trade behavior. Stronger authority requires prospective proof
and product admission.

## Authority

Research replication only. authority=false.
