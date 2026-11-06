# Derived-result dictionary

All percentage-like CSV values are decimal fractions unless the name states otherwise. Prices are proxy prices as specified in the protocol. `t` indices refer to the common SPY session calendar starting 2010-01-04. The cutoff is 2026-10-08. `date` is signal close; entries occur at the next open. An event outcome requires a full scheduled horizon. Account paths also retain immature entries.

## Event and attribution tables

| File or field | Meaning |
|---|---|
| `defensive_events.csv` | All 1,872 complete daily RSI-MACD crosses, with context, return, stop, reference and comparator fields. |
| `cell` | JOINT, WEEKLY_ONLY, TWO_WEEK_ONLY or NEITHER; higher-timeframe conditions use confirmed bars. |
| `panel` | CORE5 or PEERS13, with the exact frozen retrospective roster in PROTOCOL.md. |
| `net` | Adjusted-proxy endpoint/next-open return after proportional entry and exit fees. |
| `price_net` | Same dates and fees using price-only open/close instead of the adjustment-factor return proxy. This is a sensitivity, not a PIT corporate-action reconstruction. |
| `net50` | Same return proxy with 25 basis points per leg. |
| `stop_net` | Same entry and scheduled release with initial three-ATR stop; early stopped capital has zero return until release in the event table. |
| `mae` | Worst adjusted low relative to entry during the outcome window, capped at zero; includes entry session. |
| `reference_low`, `reference_age` | Lowest low in 63 sessions through signal; age uses the most recent tied low. |
| `entry_distance_atr` | (Next-open entry minus frozen reference)/signal ATR. |
| `reference_break_horizon` | At least one future low strictly below the frozen low. Primary survival is its complement. |
| `reference_touch_horizon` | At least one future low at or below the frozen low. |
| `tolerant_reference_break_horizon` | Separate sensitivity: undercut exceeds 0.25 signal ATR. Never substitute for strict breach. |
| `reference_intact_at_stop` | Stop occurs and every future low through the stop day stays strictly above reference. In prose, reference untouched. False for all unstopped events. |
| `reference_undercut_at_stop` | Reference is undercut on or before the stop date. Daily bars do not order same-day touches. |
| `both_levels_touched_on_stop_day` | Reference first touched on stop day; stop/reference intraday sequence unknown. |
| `winner_stopped_reference_untouched` | `net > 0 AND stop_net <= 0 AND reference_intact_at_stop`. Required intersection, not separate marginals. |
| `ordinary_*` | Average other complete outcomes in same asset/half-year/own trend/market trend cell, with focal date removed and at least ten comparators. |
| `core_peer_net`, `broad_peer_net`, `spy_net` | Same-date endpoint returns of other core names, other peer names and SPY. Focal stock excluded where applicable. |
| `defensive_summary.csv` | All context classes, both cohorts and all declared periods. Split outcomes must mature within their period. |
| `defensive_common_support.csv` | Joint events with every comparator available within each cohort. Does not equate dates or regimes between cohorts. |
| `defensive_subgroups.csv`, `defensive_influence.csv` | First/repeat/watch strata and leave-one-stock/year diagnostics. These do not define replacement strategies. |
| `*_delta_lo`, `*_delta_hi` | Pointwise calendar-block interval for mean paired difference. Not selection-adjusted or a causal interval. |
| `*_populated_halfyears`, `*_bootstrap_valid` | Calendar support and usable-draw fraction. At least four populated half-years and 95% valid draws are required for an interval. |
| `defensive_contrasts.csv` | Shared-resampling contrasts with each arm's support and joint valid-draw fraction. |

## Sector comparisons

`sector_events.csv` contains 104 complete events on 56 dates. The input catalogue includes 108 signals; capital occupancy yields 97 accepted entries, of which 93 scheduled endpoints are mature. `sector_accepted_paired.csv` retains all 97 with closed/marked status. `sector_accepted_contrasts.csv` uses the same 93 mature slots and reports selected minus all-sector basket or SPY trade returns. Its intervals are not CAGR-difference intervals. The event peer basket excludes the focal sector; the executable capital basket contains all twelve sectors.

## Capital tables

| File or field | Meaning |
|---|---|
| `portfolio_summary.csv` | 51 population/policy/scenario combinations. Primary, constant-3%-cash scenario and 50bp-cost sensitivity are separate. |
| `portfolio_paths.csv` | Primary daily NAV, gross marked holdings and actual turnover, with one row per policy/date. NAV includes a liquidation-fee adjustment on open holdings. |
| `invested_fraction` | Mean daily gross marked holdings divided by gross account wealth, not the share of dates with any position. |
| `cagr` | Terminal wealth annualized with 252 sessions/year. No annualization by exposure. |
| `max_drawdown` | Worst close-marked NAV decline from prior peak, including initial capital. Not intraday liquidation risk. |
| `max_underwater_sessions` | Longest consecutive close-marked run below prior peak, including unfinished episodes. |
| `gross_turnover_initial_capital` | Summed traded notional divided by initial capital, not average annualized turnover. |
| `portfolio_annual.csv` | Calendar-year account returns; 2026 is partial and explicitly excluded from full-year win counts. |
| `portfolio_trades.csv` | Actual closed trades and cutoff marked-open positions. Closed status can differ between stopped and unstopped policies. |
| `portfolio_trade_maturity.csv` | Shared scheduled-endpoint maturity denominator. Use this for paired hit-rate comparisons across stop policies. |
| `open_positions.csv` | Cutoff unfinished positions, signal/entry dates and net marked returns; neither omitted losses nor completed trades. |
| `capital_rosters.csv` | Accepted and rejected signals, preserving capital-occupied and no-next-open reasons. Reserved intervals persist after early stop. |
| `portfolio_diagnostics.csv` | Retrospectively selected worst-drawdown dates, exposure and full-year outcomes. Not a new trading rule. |
| `drawdown_sleeve_attribution.csv` | Exact sleeve contributions to the two headline account drawdowns; sums checked against aggregate drawdown. |

Continuous-ownership positions intentionally have no scheduled endpoint inside the sample; their trade hit rate is unavailable. Their account performance is fully measured. Primary defensive fees are 5bp each side, sector fees 10bp each side. Defensive stop geometry uses adjusted proxies; sector geometry uses raw prices. Neither account contains leverage, inter-sleeve capital transfers or portfolio rebalancing.

## Reconciliation and receipts

`v11_reconstruction_comparison.csv` joins every daily event to the original archive. `v11_cohort_membership.csv` reconciles 74 context signals with 50 filled first-watch entries, preserving distinct endpoints and unmatched reasons. `archived_first_watch_core.csv` also retains six incomplete and one skipped watch. `registration.json` and `audit_corrections.json` distinguish initial and corrected code hashes; the protocol hash remains unchanged. `mechanical_verification.json` records 13 focused checks.

Raw prices and private ordinary-date panels are excluded from Git. The input provenance identifies source/acquisition/hash evidence without publishing private corpora. Reproduction requires the registered inputs or an explicitly labeled new-vintage reconstruction; no rerun may silently claim byte-identical data from a new download.
