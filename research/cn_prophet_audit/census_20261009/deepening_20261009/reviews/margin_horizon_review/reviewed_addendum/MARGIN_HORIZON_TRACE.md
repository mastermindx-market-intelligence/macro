# Margin feature horizon: source trace and bounded repair

The issuer margin feature has a source-defined lookback. Its division by `20.0` in the scoring function is a separate scaling operation. The native producer targets an observation 20 positions before the selected current date in the existing index store, with a fallback to 21 or 22 positions when an earlier source date is the newest populated choice. All **155,688 frozen stored rows** have a date pair exactly 20 positions apart in the pinned `000001.SS` index. This establishes the actual stored window in this snapshot, while preserving the separate source-time and calendar qualifications. [Evidence: margin_horizon_results.json; pinned_margin_collector.py.]

## Exact producer and consumer chain

`collectors/china_margin_detail.py` at study pin `3d90aad6d83152dfeeaf8345bc995826ac9d3139` has Git blob `0d5fc5fbe92a61a4327a59359f3b40fc6a9df801` and SHA-256 `55fb01d20519069aec85f23328a5507c95d86cec2d2fd6dbb3e14eb059b0cdd6`. Its `LOOKBACK_TD = 20` is explicit. `_trading_dates(40)` uses the first nonempty index store among `000001.SS`, `510300.SS` and `399001.SZ`. `_first_populated` searches the supplied dates newest first. The current observation comes from the last three dates. For the selected current index `ci`, the prior candidates are:

```python
dates[max(0, ci - LOOKBACK_TD - 2): ci - LOOKBACK_TD + 1] or dates[:1]
```

With sufficient history this yields the three candidate positions `ci-22`, `ci-21`, `ci-20`. The first populated whole-source date wins. There is no further per-issuer fallback when that date has no prior balance for a particular issuer. The producer stores the actual selected `date`, `prior_date`, `fin_balance`, `fin_balance_prior` and collection `asof`.

The pinned `engine/china_extras.py::margin_positioning` computes `(fin_balance / fin_balance_prior - 1) * 100`, rounded to one decimal when the prior is positive. Its returned feature retains the current date but drops `prior_date`. `engine/china_altdata.py::_margin_score` then divides this change by `20.0` and clips it. The number in the latter expression scales the feature; it is the producer's stored pair that supplies the observation window. `source_input.json` retains the extras source identity but not this particular function's text; `weight_input.json` retains the alternative-data source. The independent `reviews/margin_horizon_review` binds and retains the exact extras consumer bytes, closing the function-text custody gap identified during review.

## Actual frozen data

| Measure | Result |
| --- | ---: |
| Detail rows / unique tickers | 155,688 / 3,538 |
| Observation dates / distinct stored date pairs | 62 / 62 |
| Rows with both dates present in the pinned index | 155,688 |
| Rows with a 20-position stored gap | 155,688 |
| Rows with a missing prior date | 0 |
| Rows with a missing prior balance | 916 |
| Latest observation | 2026-10-08 |
| Latest rows / missing prior balances | 3,530 / 9 |

The index has 7,089 unique dated rows through October 9. The input receipts bind the exact Parquet bytes. Date-pair agreement with this index does not establish that every historical index row was available then, that the calendar is complete, or when either balance became publicly or internally known. Collection `asof` remains distinct from those clocks. Missing prior balance is not a measured zero change. No score, rank, board or investment return was recalculated.

## Underfilled-history failure and tested repair

The producer only requires at least 21 index rows. If the selected current observation is the oldest of the last three in a 21-row history (`ci=18`), the slice's stop is `-1`. Python interprets `dates[0:-1]` as nearly the entire history. With stable source responses, the prior lookup can therefore select the current observation again. If a newer source date becomes populated between the two lookups, it can select a date newer than that current observation. With `ci=19`, the `or dates[:1]` fallback supplies a 19-position gap. These are synthetic boundary findings; **none is observed in the frozen stored pairs**.

The final probe executes the exact native current lookup as well as the prior lookup. It explicitly records whether source availability changes between the calls. Eight scenarios cover the normal 20/21/22 choices, missing prior data, stable self-selection, changed-response future selection, a 19-position fallback and the valid 21-row/latest-current case. The same scenarios test this bounded replacement:

```python
target = ci - LOOKBACK_TD
prior_candidates = dates[max(0, target - 2):target + 1] if target >= 0 else []
```

It preserves all tested valid choices and returns no prior for the underfilled cases. The existing producer should also require the resolved prior date to be strictly earlier and within its declared source-session window before emitting a measured change. An unavailable window should remain unavailable under the existing nullable feature contract. This does not introduce a new lookback policy or source store.

The final host probe completed with exit 0 in 1.60 seconds. It uses immutable `git show` reads and executes only AST-extracted pure slice/lookup code with synthetic source responses. It never imports the collector, contacts a vendor or runs a production data writer. `margin_horizon_development/` preserves the initial slice-only result; that initial version did not execute the current-date selection and is superseded for the end-to-end synthetic claim. The final version supplies the missing consistency check.

## Calibration consequence

Carry the actual date pair and feature-contract identity through the existing margin feature owner. Qualify the source's publication/first-seen clocks separately. Calibration must match this issuer-level balance-change feature, its actual window and orientation, the outcome horizon, benchmark and price basis. A whole-market financing/CSI300 timing result does not qualify this cross-sectional feature. The independently accepted weight audit remains unchanged; this addendum resolves its explicit measurement-window premise and adds a small collector-boundary repair. It supplies no case for changing the current baseline coefficients.
