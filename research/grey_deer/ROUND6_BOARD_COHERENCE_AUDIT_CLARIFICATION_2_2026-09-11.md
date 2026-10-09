# Round 6 clarification 2 — entry dates, ranking definition, and numeric admissibility

**Frozen before outcome-column access:** 2026-09-11 UTC  
**Parent registration:** `ROUND6_BOARD_COHERENCE_AUDIT_PREREG_2026-09-11.md` at `a30e94b1e7db63161a3a21664ad6cce525ce706f`  
**Prior clarification:** `ROUND6_BOARD_COHERENCE_AUDIT_CLARIFICATION_2026-09-11.md` at `fca4d0d317691017c5f7e3e41be1af3690397b4a`  
**Frozen input:** Macro `bbf6c1e65fc9cad1ba40efa26126cc60036713d0`, path `data/us_board_ledger/retro_grades.parquet`, Git blob `af8bdb5a0cedfcfe3c3ea0de37c86e79f7736462`, SHA256 `fecaf0aa3e454ad93bd04cebd28b916f6bc71f50d71946ce5f03c5c50aa43399`

This clarification closes remaining parsing and grain ambiguities before any numeric return, category frequency, date range, ranking definition, price-basis frequency, or board-level result is read. It changes no population, threshold, horizon, model, or authority.

## 1. Required columns and board identity

The audit requires `as_of`, `entry_date`, `horizon`, `lane`, `rank_by`, `ticker`, `position`, `sector`, `ret`, `spy_ret`, `excess_spy`, and `price_basis`.

`as_of` must parse as a date-only value. The research grain remains `(as_of, horizon, ticker)` after the frozen `buy`-lane and product-era filters. Duplicate rows at that grain abort the audit; they are not averaged or selected by file order.

The allowed horizons remain exactly 5, 10, 21, and 63 sessions. A horizon or position must be finite and integral. Position must be strictly positive. Duplicate positions are allowed because the source can express a tie; ticker is the deterministic secondary key for the visible-top ordering.

## 2. Entry-date contract

A row with finite `ret` is a resolved outcome and must carry a valid date-only `entry_date`. All resolved rows in one `(as_of, horizon)` board must name the same entry date, and that date must be strictly after `as_of`.

An unresolved row may have a missing entry date and remains part of the issued denominator. A missing resolved entry date, a non-date-only timestamp, an entry date on/before `as_of`, or multiple resolved entry dates aborts the audit instead of being silently repaired. This validates the ledger's declared next-session-close comparison identity; it does not claim that close is the user's desired intraday fill.

## 3. Ranking-definition disclosure

Every issued row on one board must carry one non-empty `rank_by` value, and the board must contain exactly one such definition. The value is preserved in coverage and board results, and board counts by `rank_by` are disclosed.

`rank_by` is not a post-hoc performance slice. The audit will not select the best ranking-definition era, combine unlike definitions, or use a definition change to rescue an unfavorable headline. Any material definition change is a product-instrument boundary that requires its existing owner to adjudicate separately.

## 4. Numeric admissibility and benchmark consistency

`ret`, `spy_ret`, and `excess_spy` are nullable numeric evidence. A true null remains missing. A non-null value that cannot be parsed as numeric, or positive/negative infinity, aborts the audit; malformed values do not become harmless nulls.

A finite `excess_spy` requires finite `ret` and finite `spy_ret`. Where all three are finite, `excess_spy` must equal `ret - spy_ret` to absolute tolerance `1e-10`. All finite `spy_ret` values within one board must agree to absolute tolerance `1e-12`.

Per the parent registration, benchmark disagreement rejects and reports that one board while allowing other independently valid board dates to remain in the frozen audit. Malformed numeric evidence, invalid entry identity, duplicate grain, or another file-wide contract violation still aborts the audit rather than being repaired after outcome access.

Return coverage and excess-return coverage remain separate. Missing `excess_spy` cannot be treated as a zero or as full benchmark-comparison coverage. A visible-top-versus-remainder excess comparison requires at least 80% excess coverage in both subsets in addition to the existing return-coverage requirements.

## 5. Price-basis sensitivity

The cleaner post-August-6 sensitivity requires every resolved row on an eligible board to carry one non-empty, identical price-basis value, excluding `unverified_pre_20260806`. A mixture or missing basis does not enter that sensitivity. The full registered result retains all stamped basis states.

## 6. Inference and audit code proof

The inference unit remains one ordered board date. Board size is disclosed but does not create additional independent observations. The visible top twelve is selected from issued rows before outcome missingness. All thresholds and missingness bounds remain exactly those in the parent registration and first clarification.

The offline audit implementation is research-only and pure pandas/numpy. Before any real ledger outcome is read, its current synthetic contract suite passes 30 tests and a separate mutation run kills 20 deliberately wrong variants. These author tests establish the declared mechanics only; they are not empirical findings or independent review.

The next permitted action is one execution against the frozen input bytes. If the file fails a file-wide contract above, the truthful result is `CONTRACT_BLOCKED` with the exact violated field; no alternative artifact or relaxed rule may be substituted after seeing the failure.