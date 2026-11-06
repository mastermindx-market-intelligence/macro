# QF quarantine fence — 2026-10-13

SNI-local DRAFT contract review. Split membership consumes owner-supplied
opaque identity strings (Stock Identity / Data OS); this lane never mints
issuer or security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority and
trade_authority stay false. Fixtures used in the accompanying tests are
synthetic.

Registered split (S0 SL §2): TRAIN `s` < 2024-01-01; TUNE [2024-01-01, 2026-10-01);
QUARANTINE `s` >= 2026-10-01. TUNE end equals QUARANTINE start.

## Summary

| item | count |
|---|---|
| fence points censused (date boundary / live-split filter / sealed string) | 19 |
| killed by an existing `test_sni_s1_*` / `test_sni_s2_*` test | 10 |
| survived the existing suite (first fail = /tmp git-path baseline) | 9 |
| survivors after `tests/test_sni_quarantine_fence.py` | **0** |
| xfails | 0 |

Unmutated `/tmp/qf-mut-0` baseline (protocol glob, `-x`): 175 passed, 6 skipped,
then `tests/test_sni_s2_v1_1_hardening.py::test_h1_x2_01_leak_scan_before_outcomes`
failed because the throwaway copy is not a git repository. That failure is
excluded from the kill count. `tests/test_sni_quarantine_fence.py`: 19 passed
in 0.98 s.

Label-token assignments (`s1_decomposition.py:44 QUARANTINE = "QUARANTINE"`),
post-hoc QUARANTINE *counts* (`run_s1.py:341`, `run_s2.py:319`), and
split-name loops that hash empty QUARANTINE cells (`s2_splits.py:146/166`)
do not compare 2026-10-01 and cannot leak a dated row into TRAIN/TUNE; they
are not fence points.

## Census

| # | file:line | construct | guards |
|---|---|---|---|
| 1 | `residual/s1_manifest.py:26` | constant `TUNE_END = date(2026, 10, 1)` | S1 TUNE/QUARANTINE date boundary |
| 2 | `residual/s1_manifest.py:133` | filter `time_split`: `s < TUNE_END` | S1 split assignment |
| 3 | `residual/s1_manifest.py:144` | filter `label_unit`: TUNE `coverage >= TUNE_END` | S1 PURGED_TUNE |
| 4 | `event_response/s2_seal.py:177` | constant `SPLIT_QUARANTINE_START = date(2026, 10, 1)` | S2 TUNE/QUARANTINE date boundary |
| 5 | `event_response/s2_splits.py:40` | filter `split_label`: `s_date >= SPLIT_QUARANTINE_START` | S2 split assignment |
| 6 | `event_response/s2_splits.py:64` | filter `purge_flag`: TUNE `coverage >= SPLIT_QUARANTINE_START` | S2 TUNE purge |
| 7 | `residual/s1_prereg.py:188` | seal field `build_spec()["splits"]` tune/quarantine strings | S1 sealed split law |
| 8 | `residual/s1_prereg.py:192` | seal field `build_spec()["splits"]["purge"]["tune"]` | S1 sealed TUNE-purge law |
| 9 | `event_response/s2_seal.py:416` | seal field `build_prereg_spec()["splits"]` TUNE/QUARANTINE strings | S2 sealed split law |
| 10 | `event_response/s2_seal.py:419` | seal field `build_prereg_spec()["splits"]["purge"]` | S2 sealed TUNE-purge law |
| 11 | `residual/s1_report.py:417` | report prose TUNE window `2024-01-01..2026-10-01` | S1 coverage section names the TUNE window |
| 12 | `residual/run_s1.py:309` | filter `evaluate_directional` TRAIN/TUNE-only excess | S1 directional excess never computed for QUARANTINE |
| 13 | `residual/run_s1.py:353` | filter `directional_blocks` TRAIN/TUNE-only stats loop | S1 H0_1/H0_2 blocks omit QUARANTINE |
| 14 | `residual/run_s1.py:349` | filter missing-endpoint count TRAIN/TUNE-only | S1 missing-endpoint exclusions omit QUARANTINE |
| 15 | `residual/run_s1.py:486` | filter `evaluate_p03` skip non-TRAIN/TUNE | S1 P03 decomposition never runs on QUARANTINE |
| 16 | `residual/run_s1.py:643` | filter P03 calibration TRAIN/TUNE-only | S1 P03 diagnostics omit QUARANTINE |
| 17 | `residual/run_s1.py:650` | filter P03 comparison TRAIN/TUNE-only | S1 P03 incremental-explanation blocks omit QUARANTINE |
| 18 | `protocols/S0_PROTOCOL_REGISTER.md:110` | protocol definition Time-axis split | registered SL §2 TUNE end / QUARANTINE start |
| 19 | `event_response/run_s2.py:941` | report prose census window past `2026-10-01` | S2 report names a TUNE census window that crosses the fence |

Paths are under `research/single_name_intelligence/`.

## Mutation

Each point was copied into `/tmp/qf-mut-<id>/` (SNI tree + `tests/test_sni_*.py`
only). One mutation per copy, then:

`python3 -m pytest tests/test_sni_s1_*.py tests/test_sni_s2_*.py -q -p no:cacheprovider -x`

After: same glob plus `tests/test_sni_quarantine_fence.py` first.

| # | mutation | before | after |
|---|---|---|---|
| 1 | `TUNE_END` 2026-10-01 → 2026-12-01 | KILLED-BY-EXISTING `test_sni_s1_manifest.py::test_purge_and_quarantine_labels` | KILLED `test_sni_quarantine_fence.py::test_s1_tune_end_is_2026_10_01` |
| 2 | `time_split` returns TUNE after TRAIN (never QUARANTINE) | KILLED-BY-EXISTING `test_sni_s1_manifest.py::test_purge_and_quarantine_labels` | KILLED `test_sni_quarantine_fence.py::test_s1_time_split_drops_on_and_after_boundary_from_live_splits` |
| 3 | disable PURGED_TUNE | KILLED-BY-EXISTING `test_sni_s1_manifest.py::test_purge_and_quarantine_labels` | KILLED `test_sni_quarantine_fence.py::test_s1_label_unit_purges_tune_when_coverage_reaches_boundary` |
| 4 | `SPLIT_QUARANTINE_START` 2026-10-01 → 2026-12-01 | KILLED-BY-EXISTING `test_sni_s2_property.py::test_split_label_step_function_partition` | KILLED `test_sni_quarantine_fence.py::test_s2_quarantine_start_is_2026_10_01` |
| 5 | disable QUARANTINE branch of `split_label` | KILLED-BY-EXISTING `test_sni_s2_property.py::test_split_label_step_function_partition` | KILLED `test_sni_quarantine_fence.py::test_s2_split_label_drops_on_and_after_boundary_from_live_splits` |
| 6 | disable TUNE purge at quarantine start | KILLED-BY-EXISTING `test_sni_s2_property.py::test_purge_flag_true_when_window_crosses_split_boundary` | KILLED `test_sni_quarantine_fence.py::test_s2_purge_flag_true_when_tune_coverage_reaches_boundary` |
| 7 | shift S1 sealed tune/quarantine strings to 2026-12-01 | KILLED-BY-EXISTING `test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest` | KILLED `test_sni_quarantine_fence.py::test_s1_build_spec_records_quarantine_boundary` |
| 8 | shift S1 sealed TUNE-purge string to 2026-12-01 | KILLED-BY-EXISTING `test_sni_s1_v1_1_hardening.py::test_h1_x1_report_language_and_digest` | KILLED `test_sni_quarantine_fence.py::test_s1_build_spec_records_quarantine_boundary` |
| 9 | shift S2 sealed TUNE/QUARANTINE strings to 2026-12-01 | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s2_build_prereg_spec_records_quarantine_boundary` |
| 10 | shift S2 sealed purge string to 2026-12-01 | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s2_build_prereg_spec_records_quarantine_boundary` |
| 11 | shift S1 report TUNE-window string to 2026-12-01 | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s1_report_names_tune_window_ending_2026_10_01` |
| 12 | compute directional excess for QUARANTINE rows | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s1_evaluate_directional_does_not_score_quarantine_rows` |
| 13 | emit directional stats blocks for QUARANTINE | KILLED-BY-EXISTING `test_sni_s1_info_leak.py::test_step_in_tune_window_produces_retirement_end_to_end` | KILLED `test_sni_quarantine_fence.py::test_s1_directional_blocks_emit_no_quarantine_stat_keys` |
| 14 | count missing-endpoint exclusions on QUARANTINE rows | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s1_quarantine_missing_endpoint_is_not_folded_into_live_exclusions` |
| 15 | decompose P03 units on QUARANTINE rows | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s1_evaluate_p03_skips_quarantine_rows` |
| 16 | compute P03 calibration for QUARANTINE | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s1_p03_calibration_omits_quarantine` |
| 17 | emit P03 comparison stats for QUARANTINE | KILLED-BY-EXISTING `test_sni_s1_report_order.py::test_every_block_names_its_split` | KILLED `test_sni_quarantine_fence.py::test_s1_p03_comparison_blocks_omit_quarantine` |
| 18 | shift S0 Time-axis split 2026-10-01 → 2026-12-01 | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s0_register_time_axis_split_pins_2026_10_01` |
| 19 | shift S2 census report date 2026-10-01 → 2026-12-01 | SURVIVED | KILLED `test_sni_quarantine_fence.py::test_s2_report_names_tune_window_crossing_2026_10_01` |

Nine survivors before the new file: points 9, 10, 11, 12, 14, 15, 16, 18, 19.
S2 seal-integrity tests that would have pinned points 9–10 skip in the
throwaway copy (not a git repo). The S1 report-language pin reads committed
`REPORT.md`, so mutating `s1_report.py:417` was invisible. Eval filters
(points 12, 14–16) never saw a synthetic 2026-10-01 row in the existing suite.

## Xfails

None. Every censused point has a runtime pin (constant, split/filter, sealed
spec field, rendered report string, or the S0 register text). No missing
runtime fence to commission.

## Repair the seat may still want

The nine former survivors are now tested. Optional follow-up, not required
for this QF close: S2 `test_sni_s2_seal_integrity.py` depends on `git cat-file`
of the BASE ref, so a shifted `build_prereg_spec` split string does not fail
in a non-git throwaway copy. A digest pin that does not need blobs would make
that existing test a fence on its own.
