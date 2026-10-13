# Q04 — the six acceptance requirements mapped to proof

Test command (exit 0, 10 passed):

```
PYTHONPATH=<Q04> python3.12 -m pytest tests/test_flow_sign_uncertainty.py --noconftest -p no:cacheprovider -q
```

Module: `engine/flow_sign_uncertainty.py` (RESEARCH REFERENCE — NOT WIRED, `RESEARCH_ONLY = True`).

## 1. Quote-rule agreement is never labeled verified aggressor accuracy without independent labels

**Code**
- `agreement_report(..., label_provenance=)` reports `metric_kind = self_consistency` and `is_aggressor_accuracy = False` for every quote-derived provenance.
- `calibrate_buy_probability` raises `IndependentLabelsRequired` unless the provenance is in `INDEPENDENT_PROVENANCES`.
- `disagreement_error_floor` reports only the arithmetic lower bound, max error ≥ d/2.
- `annotate_production_sign` sets `sidecar_is_aggressor_accuracy = False`.

**Tests**
- `test_req1_quote_rule_agreement_is_not_aggressor_accuracy`
- `test_req1_calibrated_buy_probability_refuses_quote_derived_labels`

**Evidence**
- VERDICT §1: every local agreement figure is self-consistency, and E1 is INSUFFICIENT_DATA with the missing input named.
- `results/baseline.json` carries `metric_kind` and `agreement_method` verbatim.

## 2. Stale, locked and crossed quotes, ties and corrections have explicit outcomes

**Code**
- `classify_print` returns one of 14 named outcomes (`PRINT_OUTCOMES`): at_ask, at_bid, inside above/below mid, midpoint_tie, outside above/below, locked, crossed, stale_quote, future_quote, no_quote, corrected_or_cancelled, invalid_print. Each carries a sign (or None) and a reason. The at_ask/at_bid signs hold only under the maintained `EDGE_SIGN_ASSUMPTION` (at-ask = buyer, at-bid = seller; untested without independent labels).
- `tick_outcome` separates uptick, downtick, zero-tick carry, zero-tick with no prior, and no prior trade.
- `bounds_from_prints` drops `EXCLUDED_OUTCOMES` (corrected or invalid prints) from the denominator and counts them, and treats every non-edge outcome as unidentified. Its bounds are edge-location-conditional, and U is a lower bound on the unidentified share if the edge-sign assumption fails (PREREG_AMENDMENT.md).

**Tests**
- `test_req2_explicit_print_outcomes`
- `test_req2_tick_ties_and_bounds_exclusions`
- `test_edge_sign_assumption_is_disclosed_and_bounds_are_conditional`: the assumption is exported and disclosed, no docstring claims sharpness, and relaxing edge shares raises U and widens the bounds.

## 3. Historical trade order and receipt cutoff preserved; no silent universal time-lag constant

**Code**
- `order_prints(records, receipt_cutoff=)` uses a stable sort on (trade_ts, seq), so ties keep feed order. It drops and counts prints received after the cutoff, and receipt time filters prints without ever reordering them.
- `align_quote_asof(..., quote_lag_ms=)` takes the lag as a REQUIRED keyword with no default, and never matches a future quote.
- `classify_print` requires both `quote_age_ms` and `max_quote_age_ms`.

**Tests**
- `test_req3_trade_order_receipt_cutoff_and_required_lag`. The test asserts the lag parameter has no default. It also checks behaviorally that a dense quote grid picks indices [10, 9, 9, 7, 5, 0, −1] for lags (0, 1, 1000, 2500, 5000, 10000, 10001) ms, so the lag shifts the as-of cutoff and never matches a future quote. And it checks that `max_quote_age_ms=None` is honored while a quote older than the limit is `stale_quote`.

**Evidence**
- PREREG §3 / `results/e2_summary.json`: the ingest-lag distribution is reported as measured.
- `ts_offset_note`: no lag constant is applied.

## 4. Train/test sessions and contracts separated as preregistered

**Code**
- `chronological_split` assigns training to the earliest floor(0.6·S) sessions.
- `contract_disjoint_mask` keys contracts on (root, right, exp, strike) compared as strings.

**Tests**
- `test_req4_session_and_contract_separation`

**Evidence**
- `results/e2_summary.json` H1: train 2026-09-17 → 09-22, test 09-23 → 09-25.
- Contract-filter attrition: 3,997. Decision cohort: 3,146.
- Tercile edges, cell means and k are fitted on training only (`liquidity_edges_train`, `loso_mse_*`).

## 5. Calibration and abstention reported by liquidity and time segment; correlated prints do not inflate effective N

**Code**
- `liquidity_edges` and `assign_liquidity` produce training-fitted terciles plus `liq_unknown`.
- `time_segment` produces open/mid/late/other cells.
- `session_block_bootstrap_skill` and `session_block_bootstrap_mean` resample whole sessions.
- `effective_n` counts distinct blocks.

**Tests**
- `test_req5_segments_and_honest_n`: duplicating every row 25× leaves `n_blocks` and the CI unchanged.

**Evidence**
- `results/cell_table.csv`: per-liquidity-cell U, premium-weighted U and the labeled-premium share not robust to the edge-conditional bounds, each with a session-block CI.
- `time_support`: the time segment is reported as UNIDENTIFIED (31.3% of events fall outside the window), not fabricated.
- Honest N is reported as n_blocks = 3 against n_rows = 3,146.
- Calibrated buy probability is withheld (requirement 1).

## 6. Negative delta-adjustment evidence and all existing production signing/gate behavior preserved

**Code**
- `DELTA_ADJUSTMENT_NEGATIVE_EVIDENCE` is a read-only mapping: tick 0.556 vs delta-adjusted 0.526, `improves_direction = False`.
- `delta_adjustment_recommended()` returns False.
- `annotate_production_sign` returns the production sign unchanged.
- The module does not import or edit `engine/flow_signing.py`, `scripts/calibrate_flow_signing.py` or `signing_gate.json`. No existing file is modified; all files are new.

**Tests**
- `test_req6_negative_evidence_and_production_preserved`
- `test_no_silent_activation`: import performs no file I/O, adds no engine modules, network modules or threads, and the docstring and `RESEARCH_ONLY` hold.

**Evidence**
- `results/baseline.json` reproduces the incumbent gate record unchanged (`delta_adjusted.improves_direction = false`).

## Process gates

- **Freeze.** PREREG.md sha256 `b74dae57…88fd` was recorded in FREEZE.log at 2026-10-09T09:32:25Z, before evaluation.
- **Refusal on tamper.** evaluate.py refuses a tampered PREREG. Checked on an isolated copy: exit 2, a REFUSED line written, no results written. The copy was not shipped.
- **One decisional run** (09:41:28Z), then one reproduction (09:41:58Z) with identical output sha256s:
  - `e2_summary.json` `a629624d…f5f8`
  - `cell_table.csv` `85fd50e0…6d36`
- No repeated holdout search: same code and same prereg, a determinism check only.
- **Post-audit amendment.** PREREG_AMENDMENT.md (`513141ab…7027`, witnessed in FREEZE.log) changes wording, disclosure and logging only: the edge-sign assumption, conditional bounds, and U read as a lower bound. One post-audit `--mode evaluate` run (09:56:38Z) logs code sha256s and reproduces both outputs byte-identically. A first attempt at 09:56:22Z was REFUSED (exit 2) by the hash parser, and that refusal is logged.
