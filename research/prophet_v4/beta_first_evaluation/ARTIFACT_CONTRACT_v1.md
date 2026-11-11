# `site/prophet/beta_evaluation.json` — artifact contract v1 (for the Terminal Strategy Evaluation / SX05 renderer)

Schema `prophet.beta_evaluation/v1`. `view` = `STRATEGY_EVALUATION_VIEW`: an evaluation adapter, not a Record population.
The file passes lane 8's `validate_evaluation_result` (macro#10924 `engine/sector_heads.py`) unchanged: all seven `C*` ids are present, no forbidden key names, and the authority flags are false.

**Corrected population (deviation D5, 2026-11-10):** every headline number in this artifact uses **live-published
plans only**. The 16 outage-reconstructed incumbent-era plans (13 receipted replays, 3 synthetic-board
reconstructions) are excluded from C6/C7/C6A, the event study, attribution and coverage; the numbers as
originally run are retained verbatim under `sensitivity.superseded_as_run` and must never be rendered as the
current result. See `population` below.

**Units:** every return/difference is a **fraction** (0.01 = 1% or 1 pp). `*_ci95` = `[lo, hi]` 95% bootstrap percentile interval. `null` = unavailable; never render it as 0.
Annualised fields (`ann_*`) are mean daily × 252 from 63 returns and are very noisy. **Lead with total-window fields** (`total_*`, `vs_passive_market.total_diff`).
Render nothing as a recommendation. All `may_*` flags are false.

## Identity and clocks
| Field | Meaning |
|---|---|
| `schema`, `view`, `protocol_ref` | Contract identity; path of the frozen header JSON |
| `protocol.{id, header_sha256, header_commit, frozen_on}` | Frozen protocol binding. Show it in "Evaluation details". |
| `code.{commit, harness_dirty, module, runner, bootstrap{B, seed, mean_block, sensitivity_block}}` | Code that produced the numbers. `harness_dirty` must be false. |
| `data_clocks.macro_data_commit` | Repo pin of all inputs |
| `data_clocks.plans_index.{path, sha256, asof, source_asof, computed_at}` | Prophet plan snapshot used |
| `data_clocks.resolution_log.{path, sha256, rows, malformed_lines_skipped, max_asof, close_date_corrections_applied, quarantined_ids_removed}` | Plan resolution record (`data/prophet/ledger.jsonl`) |
| `data_clocks.pit_membership.{path, sha256, last_recorded_change}` | S&P 1500 point-in-time membership; `last_recorded_change` shows its staleness |
| `data_clocks.prices.{source, tickers_loaded, digest_sha256, missing_files, last_close_used}` | Price inputs |
| `market`, `benchmark`, `currency`, `return_basis`, `cash_instrument`, `costs_bp_per_side{etf, stock}` | Evaluation basis ("US · SPY · USD · total return · cash = BIL") |
| `window.{first_return_close, last_close, sessions, daily_returns, spy_total_return, spy_max_drawdown}` | Period and the market's own path |

## Release (show first, in words)
| Field | Meaning |
|---|---|
| `release.overall_level` | Lowest level across jobs. Today `L0_descriptive`. |
| `release.levels_defined` | Ordered L0…L3 |
| `release.jobs.{A_market_participation, B_sector_context, C_member_selection}.level` | Per-job level |
| `release.jobs.*.criteria[] {criterion, required, observed, met}` | The predeclared tests with observed values. Render as a checklist. |
| `release.global_minimum_for_L1[]`, `global_minimum_met` | Sample-size gate. The cap applies when it is false. |
| `release.l0_source_checks[]`, `l0_met` | Source-correctness checks |
| `release.cap_rule`, `release.l2_l3_note` | Plain-language rules |
| `headline[]` | Ready-to-render plain sentences, computed from the numbers (English). |
| `limitations[]` | Plain-language limitations. Show them where the claim is made, not hidden. |

## Comparators (`comparators[]`, one row each; ids C1…C7 + `C6A_context_aligned_prophet` + `X6_exposure_matched_reference`)
| Field | Meaning |
|---|---|
| `id`, `label`, `definition` | Identity, short label, exact header definition |
| `status`, `reason` | `evaluated` or `unavailable` (+ reason) |
| `total_net_return`, `ann_return` | Net of costs, BIL on uninvested weight |
| `excess_total_vs_spy`, `ann_excess_vs_spy`, `ann_excess_over_cash` | Point differences |
| `vs_passive_market.{total_diff, total_diff_ci95, ann_diff, ann_diff_ci95, p_one_sided}` | Comparison with SPY and its CI. **Main bar/row of SX05.** |
| `beta_vs_market`, `beta_ci95` | Market sensitivity (OLS on BIL-excess daily returns) |
| `intercept_ann` | Regression intercept × 252. **Do not label it alpha**; label it "unexplained return (not validated)" or omit it. |
| `tracking_error`, `max_drawdown` | Risk |
| `upside_capture`, `upside_capture_ci95`, `downside_capture`, `downside_capture_ci95` | Geometric capture on SPY up/down days; `null` when SPY's move on those days is near zero |
| `mean_invested`, `time_in_market`, `no_entry_periods` | Exposure. `no_entry_periods` = days with no risky position. |
| `annual_turnover` | One-way turnover per year (includes the initial buy-in) |
| `costs_paid_total`, `at_2x_costs.{total_net_return, ann_excess_vs_spy}` | Costs and cost stress |
| `no_fill_signals`, `stale_asset_days` | Fill accounting |
| `sample.{positions, distinct_assets, censored_open_at_window_end, resolved}` | Prophet books only (C6/C7/C6A) |
| `hit_rate_vs_spy.{n, beat_spy, rate, ci95_wilson}` | Prophet books: share of positions beating SPY over their own holding window |
| `window` | Per-row window (same for all rows in v1) |
| `note` | X6 only: reference row, no costs |

**X6 is an exposure-weight arithmetic reference only** (label says so): it matches risky weight alone, the book is
~98–100% invested, so K2 nearly repeats K1 and **cannot identify member-selection value**. Never caption X6/K2 as
a selection test, and never read an insignificant K2/K4/K6 as "no value" — render "value not shown".

## Contrasts
- `contrasts.rows[] {id K1…K8, a, b, header_definition, ann_diff, ann_diff_ci95, total_diff, total_diff_ci95, p_raw, p_holm, reject_h0, block21{ann_diff_ci95, p_raw, p_holm, reject_h0}, at_2x_costs{ann_diff, ann_diff_ci95}}`.
  This is the confirmatory family. Show `reject_h0` as "significant after correction: no/yes".
- `secondary_contrasts.rows.{S_patience, S_confirmation, S_early_turn_starter} {stratum, positions, ann_diff_vs_spy, ann_diff_ci95, beta_vs_market, mean_invested, p_raw, p_holm, reject_h0}` covers the admission-class strata.
- `exposure_matched_reference.{definition, invested_fraction, c6_minus_reference, c3_minus_reference}` shows the result after matching market exposure (SP19).

## Attribution bridge (`attribution.<C6|C7|C6A>`)
| Field | Meaning |
|---|---|
| `method`, `linking`, `unit` | `daily_arithmetic_accounting_identity_sector_etf_segments`; unlinked arithmetic sum of daily contributions |
| `gap_vs_benchmark_bridge.{benchmark, uninvested_market_shortfall, sector_allocation, selection_within_sector, cash, costs, strategy}` | **The SX05 bridge.** `benchmark + uninvested_market_shortfall + sector_allocation + selection_within_sector + cash + costs = strategy` exactly (sums of daily returns, not compounded). Render on one signed pp scale with zero visible. |
| `legs.{market_participation, sector_allocation, selection_within_sector, cash, costs}` | Same legs with market participation shown in absolute terms (= benchmark + shortfall) |
| `sum_of_daily_net_returns`, `identity_error` (≈0), `compounded_total_net_return`, `compounding_residual` | Reconciliation. Show the residual so "sum ≠ total return" is explained. |
| `benchmark_sum_of_daily_returns`, `unmapped_sector_weight_days` | Inputs/coverage |

Honest framing: this is an accounting identity of an equal-weight **model book of published plans**. It is not a factor model, not alpha, and not user holdings.
The selection leg includes beta ≠ 1. The spec's "3.2 + 4.4 + 4.6 = 12.2" single-name arithmetic is a different, descriptive display; use this bridge only for the book.

## Event study (`event_study`)
`{ruler, population, plans, excluded_backfilled_plans, horizons.{"10","21","42","63"}}`. Each horizon carries:
- `n`, `n_dates`, `status` (`matured_subset` | `too_few_dates` | `unmatured`);
- `excess_vs_spy`, `sector_etf_minus_spy`, `stock_minus_sector_etf`, each `{mean, median, n, ci95_date_cluster}`;
- `share_beating_spy{k, n, rate, ci95_wilson_naive}`.

These are policy-free fixed-horizon marks of every **live-published** plan (`population` names the D5 exclusion;
`excluded_backfilled_plans` counts them). H = 63 is `unmatured` in the corrected population — do not render it.
Caveat the CIs: overlapping dates make them optimistic.

## Population (`population`, added by D5)
| Field | Meaning |
|---|---|
| `primary` | One sentence: every number in this artifact uses live-published incumbent-era plans only |
| `excluded_cohort.reason` / `.detection` | Why (outage reconstructions are not live historical calls) and how detected (`origination_mode`, `backfill_executed_at`, disclosure receipts; run refuses on disagreement — never a hard-coded id list) |
| `excluded_cohort.{era_plans_excluded, of_which_replayed_receipted_bake, of_which_synthetic_board_reconstructions, origination_mode_counts, backfill_executed_at_by_kind, plan_ids, would_have_entered_positions_as_run, would_have_entered_ids_as_run}` | Cohort census with receipts |
| `mrna.{note, as_run_entry, in_sensitivity_a, sensitivity_a_entry, price_authentication}` | MRNA specifically: entered as-run before it existed for any user; the +177% one-day move is single-source |
| `review.{file, sha256}` | The independent review that is the correction's source |

Show `excluded_cohort` wherever the C6 headline is shown.

## Sensitivity (`sensitivity`, added by D5 — never the headline)
- `label`: says exactly that.
- `backfill_replays_admitted_after_availability`: book metrics (positions, total, excess + CI, ann excess + CI,
  beta, mean invested, hit rate) for the counterfactual that admits the 13 receipted replays only from the first
  session at/after their actual `backfill_executed_at`; the 3 synthetic-board reconstructions are never admitted
  (`excluded_from_this_variant` shows the `not_live_origination: 3` reason). MRNA re-enters 2026-08-11.
- `superseded_as_run`: the v1 numbers under the superseded population, recomputed with the same engine, seed,
  prices and costs (`same_engine_seed_prices_costs: true`): C6/C7/C6A rows, K1/K2/K7 bootstrap contrasts,
  `attribution_C6`, `event_study_h21/h42`, and the `reason`. Render, if at all, only in a clearly superseded
  presentation.

## Coverage (the "Coverage" disclosure)
`coverage.{era_plans, evaluated_positions, excluded{reason: count}, entry_shifted_to_publication, exit_basis{recorded_close_date, mechanical_published_levels, censored_open_at_window_end}, classified_share, priced_share, sector{unmapped_plans, label_source_disagreements, labels_basis}, c7_c6a_split{outside_leading, inside_leading, unmapped}, member_universe_by_rebalance[]{decision, execution, pit_active, no_price_file, no_sector, short_history, price_below_min, eligible, c4_names, c5_names, c5_sectors}, member_universe_missing_price_files[], c4_sector_weights{}, issuer_excluded_peers{status, reason}, drop_corrected_sensitivity{positions, excluded}}`

Exclusion reasons (closed set):
- `recorded_no_entry`: the plan record says the entry never happened;
- `not_live_origination` (D5): outage-reconstructed plan, not a live historical publication;
- `not_entered_zone_live` / `not_entered_zone_expired` / `not_entered_zone_none`: the entry zone never filled;
- `resolved_at_or_before_follower_fill`: the plan closed before a follower could buy at a close;
- `published_after_window`, `fill_after_window`: outside the window;
- `no_fill_no_close_at_entry`: no price at the fill session;
- `no_publication_clock`, `not_long`, `excluded_by_sensitivity`.

`resolution_log.malformed_lines_skipped` counts only genuinely malformed data rows: `#` documentation lines in
the ledger are skipped as comments and do not count (0 in this run; the superseded v1 artifact reported 6, which
were comments).

`issuer_excluded_peers` is `unavailable` in v1 (listing-ticker identity only). Show the reason; do not invent a count.

## Other blocks
- `stability_halves.<id>.{first, second}`: point metrics for each half. Descriptive only.
- `post_hoc_diagnostics.<C6|C7|C6A>.{concurrent_positions{min, median, max, first_5_sessions}, top_contributors[], bottom_contributors[], top5_share_of_positive_contribution, without_top_contributor{dropped_asset, total_net_return, excess_total_vs_spy, excess_total_ci95, ann_excess_vs_spy, ann_excess_ci95, beta_vs_market}}`.
  The block is labelled `POST_HOC_DESCRIPTIVE_DIAGNOSTIC`. Show the single-name dependence next to the C6 headline.
- `failed_leaders{c3_sector_picks, lagged_spy_over_hold}`, `rebounds{status, reason}`.
- `claims.{observed_relative_performance, estimated_exposure_residual, participation_attribution, incremental_selection_value}.{status, basis}`.
  `incremental_selection_value.status` is never `established` here.
- `deviations[] {id, kind, when, what, why}`: every departure from the header. Show it in "Evaluation details".
  D5 records the population correction with the full before/after numbers in `what`; render it with the headline,
  not buried.
- `may_rank`, `may_gate`, `may_size`, `may_trade`, `may_escalate`: all false.

## SX05 / SX12 mapping
- **SX05 answer:**
  1. `release.overall_level` + `headline[0..3]` (the population sentence is part of the answer).
  2. A signed bar of `vs_passive_market.total_diff` with its CI for each comparator, C1 as the zero line.
  3. Beta and capture from the C6 row.
  4. The C6 bridge.
  5. The single-name note from `post_hoc_diagnostics`.
  6. The D5 population note (`population.excluded_cohort`); sensitivity blocks only if explicitly asked for.
- **SX12 "Evaluation details":** `protocol`, `code`, `data_clocks`, window/basis fields, `deviations`, `release.jobs.*.criteria`.
- **SX12 "How attribution works":** `attribution.*.{method, linking}` plus the identity and its compounding residual.
- **SX12 "Coverage":** `coverage` + `sample` + `hit_rate_vs_spy`.
- **SX12 "Open Portfolio":** the model book is not holdings. `claims.participation_attribution.basis` says so; no reconciliation is offered.
