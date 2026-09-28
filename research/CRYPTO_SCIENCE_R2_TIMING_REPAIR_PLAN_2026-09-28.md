# Crypto science R2 timing repair and paired replay plan

**Goal:** remove the two R1 timing defects without tuning signals or promoting a live strategy.
**Architecture:** repair the incumbent btc_signals and impulse-evaluator functions; preserve original feature definitions, three-day membership, allocation authority and evaluator thresholds. Reuse existing tests, Vector CI owner and research evidence directory. No new live gate, collector, workflow, strategy or registry.
**Spec:** CRYPTO_SCIENCE_R1_FINDINGS_AND_PROGRAMME_2026-09-28.md, R1 audit at 060c6bab567a7e45e6aad73393ade9aff9a55016.
**Tools:** Python/pandas, existing pytest suites, M2 Studio Direct incumbent workspace.

## Authority and current recovery

Chairman: current live `good job, continue` accepts the next planned correction/replay phase. Law pin e981ec1b0b6e3bd47e267b6abc92adee4a94d6a8; INDEX 94d1af402598894372858793a5b1931019c5fa77; compatible 1.0.1/bootstrap 1. Same operation crypto-vector-r2-20260926-sol-001; same branch/PR #8050 and M2 carrier. No active process referencing the owned workspace was observed; local HEAD and origin agree at 060c6bab567a7e45e6aad73393ade9aff9a55016 with a clean tree. Observed main c492e673fbda08a5b1c25fb988ea989b2cec805c has no changes to the two engines, their tests or config versus this head.

Collision investigation: first 200 open PR changed-path records contained no affected-path match but hit the count limit. A 1000-PR expanded file query failed with HTTP502; a smaller metadata-only recovery found 509 open PRs. Crypto/BTC/Vector/timing-relevant titles narrowed to this #8050 and #7645; #7645's exact paths exclude these engines/tests. This is a bounded relevant-source census, not a claim of every file in all open PRs exhaustively reviewed. No observed incumbent writer or effect is displaced. Direct work: PRINCIPAL_JUDGMENT for as-of semantics and CRITICAL_PATH_SHORTCUT for two coupled small fixes. Independent review remains owed before release; self-tests do not satisfy it.

## Global constraints / review focus

- Candidate source only: no merge/deploy, raw data mutation, gate-file write, provider call or live sizing change.
- Stored daily price index denotes the observation date, and the model runs after its daily close; a closing-day label is not a claim of midnight availability. Source publication/ingestion clocks remain a distinct unresolved baseline qualification.
- Preserve legacy three-day constituent membership rather than promote R1's right-closed re-anchored counterfactual. Only make each bucket observable at its third day's completed close.
- Invalid/missing future prices and incomplete horizons stay unknown; do not restore old tests that treated unknown as false.
- Nonempty masks, tail-only signals, missing daily rows, duplicate/reversed dates, zero/negative/infinite prices and cold starts must be tested. Do not tune floors or permutations to recover a passing strategy.
- Existing 2024+ periods remain reused retrospective validation, never a new untouched holdout.

## Task 1: completed higher-timeframe input

Files: engine/btc_signals.py; tests/test_btc_signals.py.
Interface: _completed_three_day_closes(close: pd.Series) -> pd.Series; bottom_pressure public signature unchanged.

- [ ] Add failing direct helper and end-of-prefix tests. Synthetic fixed seed19, 360 daily bars, all last90 cutoffs; observed incumbent mismatch 2020-11-11. This is a diagnostic fixture, not market-outcome selection.
- [ ] Helper preserves each original left-closed three-day bin, labels it two daily dates later, excludes unfinished terminal bins and leaves incomplete/invalid bins unknown. Empty input is safe. No future data can revise any value whose closing date has passed.
- [ ] bottom_pressure consumes those completed closes. Daily/weekly terms, thresholds and weights remain unchanged. Explicitly retain Sunday-closed weekly convention.
- [ ] Verify red/green, original grouping by hand, every bucket boundary/remainder, missing data and the real 366 R1 cutoffs. Expand to every available daily cutoff for a stronger timing test; report warm-up zeros separately.

## Task 2: nullable mature outcome labels

Files: engine/btc_impulse_radar_backtest.py; tests/test_btc_impulse_falsifier.py.
Interface: _labels(close) -> two nullable boolean Series; _lift/_perm_p consume only available labels.

- [ ] Replace the existing tail assertion `not bool(label)` with explicit isna and add hand-verified positive/negative labels, invalid inputs, missing daily gaps and a tail-only signal test.
- [ ] Preserve fixed strictly-forward H=3 extrema and +/-5% thresholds. Require finite positive reference and all future prices, complete future count, and consecutive daily timestamps for date-indexed data; unknown windows remain pd.NA.
- [ ] Handle empty mature samples in _lift and _perm_p without a misleading zero base rate or pd.NA boolean coercion. Do not change existing model promotion floors, sample minimum or permutation count.
- [ ] Verify original future-label anti-overlap tests and radar/ledger integration. Record the obsolete research snippet as superseded; do not rewrite earlier evidence.

## Task 3: actual paired replay and regression ownership

Files: research/crypto_science/r2_replay.py and derived results; existing Vector CI invocation in .github/ci/legacy-jobs.yml only if these suites are not already invoked.

- [ ] Commit this plan before any new full-history outcome calculation. Read/retain baseline engine code by exact R1 git ref in the research process; do not overwrite repository engines with legacy code.
- [ ] Load the existing stored input snapshot read-only once; hash files before/after. Run old and corrected compute_all on identical inputs. Enumerate changed columns, raw/final allocations and last-observation effects; require unaffected columns identical. A replay using current stored vintages is NOT point-in-time source certification.
- [ ] Frozen diagnostic metrics: one-observation-lag exposure times next close return, zero-cost gross and 10/25 basis-point one-way turnover sensitivity; calendar span, annualized geometric growth, max drawdown, average exposure and turnover. These fee assumptions are arbitrary stress diagnostics, not exchange execution proof. No threshold search, new feature or strategy optimization.
- [ ] Compare old/corrected impulse validator outputs on identical data without calling main/write_gate. Separate mature sample count, base rate, precision/lift, event overlap limits and status changes. Keep null-feature coverage limitations visible.
- [ ] Run existing tests including both corrected suites; enroll in the existing Vector test command if absent. No new CI job/runner/control plane.
- [ ] Persist source/data identity, exact commands/results and limitations to existing Agent OS decision/workstream, publish candidate and read it back. No live release acceptance.

## Stop/continuation boundary

Complete the two source fixes and bounded paired replay, then report what evidence changed and what did not. Do not infer improved forecasting from a repaired temporal invariant. Expanded source-availability audit, independent review and actual out-of-sample fast-downside/recovery experiments remain the next substantive science phase.

## Primary method references checked this turn

Pandas official resampling documentation: https://pandas.pydata.org/docs/user_guide/timeseries.html and https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.resample.html . Labels and closed sides are independent and defaults can pull information backward.
Pandas nullable boolean / missing data semantics: https://pandas.pydata.org/docs/user_guide/missing_data.html . Ordinary NaN comparisons versus nullable missing outcomes must not be conflated.
