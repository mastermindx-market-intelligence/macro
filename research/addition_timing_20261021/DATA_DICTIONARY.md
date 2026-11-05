# Result dictionary and interpretation

Dollar amounts are in the hypothetical account's USD units. Each monthly external contribution is $1,000. No output is a live recommendation.

## Identities

- `basket`: SPY primary; SECTOR11 ordinary Select Sector family; CORE5 and PEERS13 the previously selected surviving-stock groups. All share the same 12-instrument source calendar.
- `policy`: IMMEDIATE, SIGNAL with true month-end deadline, or MONTH_END regardless of signal.
- `scenario`: PRIMARY is zero cash yield and 10bp per leg; CASH3 is constant hypothetical 3% cash yield with the same fees; COST50 is zero cash yield and nominal 25bp per leg. These are declared sensitivities, not optimized scenarios.
- `month` is the contribution's funding month, not the month in which a return was earned.

## Files

| File | Row unit and important fields |
|---|---|
| `account_summary.csv` | One basket/policy/scenario account; 36 rows. `terminal_wealth` includes pending cash and liquidation fees. `contributions` is external funding only. `xirr` is a fraction per annum on dated flows. `twr_annualized` annualizes unit NAV, not raw growing balance. Drawdown/volatility/exposure fields are fractions. |
| `account_contrasts.csv` | Same-basket, same-scenario paired accounts. Dollar difference and percentage of contributions are distinct from `xirr_difference_pp`, which is annual percentage points. |
| `annual_returns.csv` | Calendar-year change in unit NAV. Last year is partial. These are not funding-year terminal attributions. |
| `contribution_ledger.csv` | Every budget under every account policy, including six immature cohorts. Dates, actual purchase reason, waiting duration, terminal wealth and common-endpoint outcomes are retained. |
| `completed_cohorts.csv` | Only budgets whose common funding+126-session endpoint exists. This is a marked-value diagnostic with no actual account sale. |
| `cohort_absolute_summary.csv` | Absolute marked return and positive fraction. Positive does not mean better than the comparator or an intact reference low. |
| `cohort_contrasts.csv` | Paired differences in percentage points of each $1,000 contribution. The interval is a 12-month circular-block resampling interval, not a portfolio-CAGR interval or untouched validation. |
| `cohort_year_summary.csv` | Complete cohorts grouped by funding year. |
| `cohort_half_summary.csv` | Fixed funding-date groups 2020-2022 and 2023-cutoff. This is descriptive, not a new holdout. |
| `waiting_attribution.csv` | Per contribution and constituent, for SIGNAL or MONTH_END against IMMEDIATE. `scheduled_adjusted_units` and `actual_adjusted_units` are units of the adjusted-price proxy, not an exact cash-dividend share register. `relative_units_acquired` is a fractional quantity difference; zero can be a genuine same-open tie. |
| `funding_year_attribution.csv` | Sum of per-asset waiting components by funding year and purchase reason, marked through the common cutoff. |
| `signal_calendar.csv` | One eligible execution date, with all nominating symbols retained. Simultaneous nominations do not supply multiple budgets or independent evidence. |
| `daily_paths.csv.gz` | One account/date: cash, invested value, units, unit NAV, contributions and fees. Only the final row includes the terminal liquidation-fee adjustment in `wealth`; `gross_wealth` is used for prefix checks. |
| `figure_daily.csv` | Primary SPY subset used in the publication chart, rounded to 10 decimal places for presentation. Exact numerical conclusions use the complete computed outputs. |
| `run_manifest.json` | Executed analysis/verification/protocol/config hashes and observed counts. |
| `mechanical_verification.json` | Synthetic checks plus independent daily lot-account reconstruction. |
| `environment.json` | Executed Python and numerical package versions. |

## Waiting decomposition

For a completed purchase, `price_movement_component` is the terminal benefit/cost of buying later with zero waiting interest, and `cash_interest_component` is the terminal value of units purchased using accrued waiting interest. `unincurred_fee_component` is zero when both alternatives purchased and are marked with the same liquidation convention.

For a still-unspent budget B, let K=(1-fee)/(1+fee), R=terminal close/funding open and G=waiting cash growth. The components are BK(1-R), B(G-1), and B(1-K). Their sum is BG-BKR, the actual pending-cash value minus the immediate account's net liquidation value. Flat prices and zero interest therefore generate no price-movement benefit; only unincurred fees differ.

`signal_at_deadline` is a signal-associated purchase but is identical in timing to the blind month-end control. `deadline` means the signal policy exhausted its waiting window without an earlier execution. `pending` keeps real cutoff cash. An `unfunded_signal_date` is an alert with no unspent budget, not a failed or missed hypothetical trade supplied with new money.

## Signal custody and clocks

`inputs/signal_roster.csv` uses the accepted study's SPY index beginning 2010-01-04. `entry_t=signal_t+1`; dates are explicitly verified against the original index. The old `accepted` status is retained as `previous_accepted_ignored` and is never a new filter. The study's `entry_i` in the collapsed calendar is local to the 2020 evaluation index.

Funding precedes a same-day open purchase. A close-generated trigger cannot execute at that earlier day's open. The fixed session calendar is separate from a priced prefix; a cutoff cannot create or erase a known month-end. All source price hashes are checked before analysis. Current-vintage adjusted OHLC remains a proxy with the stated corporate-action limitations.
