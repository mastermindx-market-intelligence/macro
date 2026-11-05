# IRP-GAP4 bootstrap interval reproduction (2026-10-13)

HISTORICAL-DESCRIPTIVE reproduction of sealed v1.1 date-block bootstrap
confidence intervals from committed observation files. This document is
not a forecast, signal, validation, registration, or acceptance-row
move. It consumes owner-supplied observation JSON/JSONL and result JSON
owned by the S1 residual and S2 event-response runners. Identity
strings are caller-supplied opaques owned by Stock Identity / Data OS.

This module is an SNI-local DRAFT contract that CONSUMES owner-supplied
values. It does not re-implement Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation.

Authority flags (literal false everywhere in this lane):

- rank_authority: false
- gate_authority: false
- size_authority: false
- signal_authority: false
- escalation_authority: false
- trade_authority: false

## Summary

In scope: every sealed S1 `ci.ci95` interval on v1.1 P01/P02/P03 blocks
(114), including the P03 S0 CI lower bound on each P03 block, plus every
sealed S2 `ci` field on TRAIN/TUNE/QUARANTINE cells (27). Wilson
intervals (`test.wilson_ci_95`, diagnostics coverage) are a different
estimator and are outside this lane. `below_floor_receipt.ci95` copies
the block `ci.ci95` and is not a second interval.

| class | n | verdict |
| --- | ---: | --- |
| S1 P01 `ci.ci95` | 24 | MATCH |
| S1 P02 `ci.ci95` | 48 | MATCH |
| S1 P03 `ci.ci95` (M1_vs_M0, M2_vs_M1) | 36 | MATCH |
| S1 P03 S0 lower bound (same 36 blocks, `ci95[0]`) | 36 | MATCH |
| S1 P03 IPCA_vs_M1 `ci.ci95` | 6 | GAP |
| S2 P04/P05/P06 `ci` | 27 | GAP |
| DIFF / IRP-F4 | 0 | none |

Headline: **141 intervals in scope / 108 MATCH / 0 DIFF / 33 GAP**.

Agreement is bitwise equality of JSON-decoded floats (the engine rounds
bounds to 4 decimal places before JSON write). No interval needed the
`abs <= 1e-12` fallback.

## Registered parameters and where each was read

Read from `research/single_name_intelligence/runs/s1_residual_v1_1/PREREG_SPEC.json`
key `mirror_trick` (not from `engine.grading_stats` module defaults):

| parameter | value | source |
| --- | --- | --- |
| draws | 800 | `mirror_trick.construction` text `default draws/seed (800/7)` |
| seed | 7 | same |
| stat | `mean` | `mirror_trick.construction` `stat='mean'` |
| block unit | one non-overlapping anchor unit (h+1 sessions >= h) | `mirror_trick.block` |
| cluster variable | cluster key = trade date of s | `mirror_trick.cluster_variable` |
| construction | `dates=concat(k,k), vals=concat(x,-x), mask=concat(1,0)` | `mirror_trick.construction` |

`SEAL_AND_BUDGET.json` does not record draws or seed. Result-file
`ci.method` strings corroborate `default draws 800 seed 7` but were not
used as the registration source.

`PREREG_SPEC.json` `engine_citations.engine/grading_stats.py.BOOT_DRAWS = 43`
and `BOOT_SEED = 44` are **line numbers** of those names in
`engine/grading_stats.py`, not the registered numeric values.

S2 `runs/s2_event_response_v1_1/PREREG_SPEC.json` key
`statistics.mean_excess_ci` registers the same mirror-trick construction
with `stat='mean'` and the phrase `default draws/seed` **without
numerals**. This lane uses the S1 PREREG numerals (800/7) for any S2
call that had committed inputs; no S2 cell had committed excess values.

`common/sni_inference.py` `cluster_mean_ci` is a different estimator
(stdlib `random.Random`, default draws=2000 seed=0). It did not write
these sealed numbers and is not called by this reproduction.

## Per-interval table

| study | block | sealed value | reproduced value | input rows | verdict |
| --- | --- | --- | --- | --- | --- |
| S1 P01 | `P01\|adr_baba\|h=5\|TRAIN\|always_long\|H0_1` | `[-0.0061, 0.0064]` | `[-0.0061, 0.0064]` | 347 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TRAIN\|always_long\|H0_2` | `[-0.0061, 0.0064]` | `[-0.0061, 0.0064]` | 347 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_1` | `[-0.0094, 0.011]` | `[-0.0094, 0.011]` | 114 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_2` | `[-0.0094, 0.011]` | `[-0.0094, 0.011]` | 114 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TRAIN\|trail63\|H0_1` | `[-0.0061, 0.0064]` | `[-0.0061, 0.0064]` | 347 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TRAIN\|trail63\|H0_2` | `[-0.0061, 0.0064]` | `[-0.0061, 0.0064]` | 347 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_1` | `[-0.0094, 0.011]` | `[-0.0094, 0.011]` | 114 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=5\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_2` | `[-0.0094, 0.011]` | `[-0.0094, 0.011]` | 114 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TRAIN\|always_long\|H0_1` | `[-0.0269, 0.0155]` | `[-0.0269, 0.0155]` | 94 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TRAIN\|always_long\|H0_2` | `[-0.0269, 0.0155]` | `[-0.0269, 0.0155]` | 94 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_1` | `[-0.0433, 0.0396]` | `[-0.0433, 0.0396]` | 31 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_2` | `[-0.0433, 0.0396]` | `[-0.0433, 0.0396]` | 31 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TRAIN\|trail63\|H0_1` | `[-0.0269, 0.0155]` | `[-0.0269, 0.0155]` | 94 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TRAIN\|trail63\|H0_2` | `[-0.0269, 0.0155]` | `[-0.0269, 0.0155]` | 94 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_1` | `[-0.0433, 0.0396]` | `[-0.0433, 0.0396]` | 31 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=21\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_2` | `[-0.0433, 0.0396]` | `[-0.0433, 0.0396]` | 31 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TRAIN\|always_long\|H0_1` | `[-0.0776, 0.07]` | `[-0.0776, 0.07]` | 32 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TRAIN\|always_long\|H0_2` | `[-0.0776, 0.07]` | `[-0.0776, 0.07]` | 32 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_1` | `[-0.0963, 0.1193]` | `[-0.0963, 0.1193]` | 10 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|always_long\|H0_2` | `[-0.0963, 0.1193]` | `[-0.0963, 0.1193]` | 10 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TRAIN\|trail63\|H0_1` | `[-0.0776, 0.07]` | `[-0.0776, 0.07]` | 32 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TRAIN\|trail63\|H0_2` | `[-0.0776, 0.07]` | `[-0.0776, 0.07]` | 32 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_1` | `[-0.0963, 0.1193]` | `[-0.0963, 0.1193]` | 10 | MATCH |
| S1 P01 | `P01\|adr_baba\|h=63\|TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))\|trail63\|H0_2` | `[-0.0963, 0.1193]` | `[-0.0963, 0.1193]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TRAIN\|always_long\|H0_1` | `[-0.0117, 0.0063]` | `[-0.0117, 0.0063]` | 121 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TRAIN\|always_long\|H0_2` | `[-0.0117, 0.0063]` | `[-0.0117, 0.0063]` | 121 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TUNE\|always_long\|H0_1` | `[-0.0059, 0.0099]` | `[-0.0059, 0.0099]` | 111 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TUNE\|always_long\|H0_2` | `[-0.0059, 0.0099]` | `[-0.0059, 0.0099]` | 111 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TRAIN\|trail63\|H0_1` | `[-0.0128, 0.0064]` | `[-0.0128, 0.0064]` | 119 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TRAIN\|trail63\|H0_2` | `[-0.0128, 0.0064]` | `[-0.0128, 0.0064]` | 119 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TUNE\|trail63\|H0_1` | `[-0.0059, 0.0099]` | `[-0.0059, 0.0099]` | 111 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=5\|TUNE\|trail63\|H0_2` | `[-0.0059, 0.0099]` | `[-0.0059, 0.0099]` | 111 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TRAIN\|always_long\|H0_1` | `[-0.0504, 0.0138]` | `[-0.0504, 0.0138]` | 33 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TRAIN\|always_long\|H0_2` | `[-0.0504, 0.0138]` | `[-0.0504, 0.0138]` | 33 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TUNE\|always_long\|H0_1` | `[-0.0319, 0.0557]` | `[-0.0319, 0.0557]` | 28 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TUNE\|always_long\|H0_2` | `[-0.0319, 0.0557]` | `[-0.0319, 0.0557]` | 28 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TRAIN\|trail63\|H0_1` | `[-0.0504, 0.0138]` | `[-0.0504, 0.0138]` | 33 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TRAIN\|trail63\|H0_2` | `[-0.0504, 0.0138]` | `[-0.0504, 0.0138]` | 33 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TUNE\|trail63\|H0_1` | `[-0.0261, 0.0583]` | `[-0.0261, 0.0583]` | 27 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=21\|TUNE\|trail63\|H0_2` | `[-0.0261, 0.0583]` | `[-0.0261, 0.0583]` | 27 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TRAIN\|always_long\|H0_1` | `[-0.1097, -0.0269]` | `[-0.1097, -0.0269]` | 11 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TRAIN\|always_long\|H0_2` | `[-0.1097, -0.0269]` | `[-0.1097, -0.0269]` | 11 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TUNE\|always_long\|H0_1` | `[-0.0598, 0.0779]` | `[-0.0598, 0.0779]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TUNE\|always_long\|H0_2` | `[-0.0598, 0.0779]` | `[-0.0598, 0.0779]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TRAIN\|trail63\|H0_1` | `[-0.1097, -0.0269]` | `[-0.1097, -0.0269]` | 11 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TRAIN\|trail63\|H0_2` | `[-0.1097, -0.0269]` | `[-0.1097, -0.0269]` | 11 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TUNE\|trail63\|H0_1` | `[-0.0598, 0.0779]` | `[-0.0598, 0.0779]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_9988\|h=63\|TUNE\|trail63\|H0_2` | `[-0.0598, 0.0779]` | `[-0.0598, 0.0779]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TRAIN\|always_long\|H0_1` | `[-0.0006, 0.0054]` | `[-0.0006, 0.0054]` | 404 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TRAIN\|always_long\|H0_2` | `[-0.0006, 0.0054]` | `[-0.0006, 0.0054]` | 404 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TUNE\|always_long\|H0_1` | `[-0.0051, 0.0055]` | `[-0.0051, 0.0055]` | 109 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TUNE\|always_long\|H0_2` | `[-0.0051, 0.0055]` | `[-0.0051, 0.0055]` | 109 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TRAIN\|trail63\|H0_1` | `[-0.0009, 0.0051]` | `[-0.0009, 0.0051]` | 400 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TRAIN\|trail63\|H0_2` | `[-0.0009, 0.0051]` | `[-0.0009, 0.0051]` | 400 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TUNE\|trail63\|H0_1` | `[-0.0037, 0.0068]` | `[-0.0037, 0.0068]` | 104 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=5\|TUNE\|trail63\|H0_2` | `[-0.0037, 0.0068]` | `[-0.0037, 0.0068]` | 104 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TRAIN\|always_long\|H0_1` | `[0.0042, 0.0294]` | `[0.0042, 0.0294]` | 109 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TRAIN\|always_long\|H0_2` | `[0.0042, 0.0294]` | `[0.0042, 0.0294]` | 109 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TUNE\|always_long\|H0_1` | `[-0.0138, 0.0242]` | `[-0.0138, 0.0242]` | 28 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TUNE\|always_long\|H0_2` | `[-0.0138, 0.0242]` | `[-0.0138, 0.0242]` | 28 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TRAIN\|trail63\|H0_1` | `[0.0041, 0.0301]` | `[0.0041, 0.0301]` | 107 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TRAIN\|trail63\|H0_2` | `[0.0041, 0.0301]` | `[0.0041, 0.0301]` | 107 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TUNE\|trail63\|H0_1` | `[-0.015, 0.0244]` | `[-0.015, 0.0244]` | 27 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=21\|TUNE\|trail63\|H0_2` | `[-0.015, 0.0244]` | `[-0.015, 0.0244]` | 27 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TRAIN\|always_long\|H0_1` | `[0.0061, 0.074]` | `[0.0061, 0.074]` | 37 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TRAIN\|always_long\|H0_2` | `[0.0061, 0.074]` | `[0.0061, 0.074]` | 37 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TUNE\|always_long\|H0_1` | `[-0.0598, 0.0551]` | `[-0.0598, 0.0551]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TUNE\|always_long\|H0_2` | `[-0.0598, 0.0551]` | `[-0.0598, 0.0551]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TRAIN\|trail63\|H0_1` | `[0.0061, 0.074]` | `[0.0061, 0.074]` | 37 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TRAIN\|trail63\|H0_2` | `[0.0061, 0.074]` | `[0.0061, 0.074]` | 37 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TUNE\|trail63\|H0_1` | `[-0.0598, 0.0551]` | `[-0.0598, 0.0551]` | 10 | MATCH |
| S1 P02 | `P02\|hkd_0700\|h=63\|TUNE\|trail63\|H0_2` | `[-0.0598, 0.0551]` | `[-0.0598, 0.0551]` | 10 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TRAIN\|M1_vs_M0` | `[0.0003, 0.001]` | `[0.0003, 0.001]` | 347 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TUNE\|M1_vs_M0` | `[0.0001, 0.0007]` | `[0.0001, 0.0007]` | 114 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TRAIN\|M2_vs_M1` | `[0.0012, 0.0028]` | `[0.0012, 0.0028]` | 347 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TUNE\|M2_vs_M1` | `[0.0011, 0.003]` | `[0.0011, 0.003]` | 114 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TRAIN\|IPCA_vs_M1` | `[-0.0, 0.0002]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|adr_baba\|h=5\|TUNE\|IPCA_vs_M1` | `[-0.0001, 0.0001]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TRAIN\|M1_vs_M0` | `[-0.0006, 0.0034]` | `[-0.0006, 0.0034]` | 94 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TUNE\|M1_vs_M0` | `[-0.0014, 0.0031]` | `[-0.0014, 0.0031]` | 31 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TRAIN\|M2_vs_M1` | `[0.0039, 0.0098]` | `[0.0039, 0.0098]` | 94 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TUNE\|M2_vs_M1` | `[0.0027, 0.0132]` | `[0.0027, 0.0132]` | 31 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TRAIN\|IPCA_vs_M1` | `[-0.0004, 0.0007]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|adr_baba\|h=21\|TUNE\|IPCA_vs_M1` | `[-0.0011, 0.0005]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TRAIN\|M1_vs_M0` | `[-0.0017, 0.018]` | `[-0.0017, 0.018]` | 32 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TUNE\|M1_vs_M0` | `[-0.0095, 0.0078]` | `[-0.0095, 0.0078]` | 10 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TRAIN\|M2_vs_M1` | `[0.0133, 0.0412]` | `[0.0133, 0.0412]` | 32 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TUNE\|M2_vs_M1` | `[-0.0079, 0.026]` | `[-0.0079, 0.026]` | 10 | MATCH |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TRAIN\|IPCA_vs_M1` | `[-0.0022, 0.0028]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|adr_baba\|h=63\|TUNE\|IPCA_vs_M1` | `[-0.004, 0.0028]` | `—` | IPCA rows missing | GAP |
| S1 P03 S0 | `P03\|hkd_9988\|h=5\|TRAIN\|M1_vs_M0` | `[0.0025, 0.006]` | `[0.0025, 0.006]` | 121 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=5\|TUNE\|M1_vs_M0` | `[0.0016, 0.0031]` | `[0.0016, 0.0031]` | 111 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=5\|TRAIN\|M2_vs_M1` | `[-0.0002, 0.0005]` | `[-0.0002, 0.0005]` | 99 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=5\|TUNE\|M2_vs_M1` | `[-0.0001, 0.0001]` | `[-0.0001, 0.0001]` | 111 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=21\|TRAIN\|M1_vs_M0` | `[0.005, 0.0166]` | `[0.005, 0.0166]` | 33 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=21\|TUNE\|M1_vs_M0` | `[0.0054, 0.0285]` | `[0.0054, 0.0285]` | 28 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=21\|TRAIN\|M2_vs_M1` | `[-0.0006, 0.0042]` | `[-0.0006, 0.0042]` | 26 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=21\|TUNE\|M2_vs_M1` | `[-0.0007, 0.0017]` | `[-0.0007, 0.0017]` | 28 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=63\|TRAIN\|M1_vs_M0` | `[0.0047, 0.0377]` | `[0.0047, 0.0377]` | 11 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=63\|TUNE\|M1_vs_M0` | `[-0.0017, 0.0192]` | `[-0.0017, 0.0192]` | 10 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=63\|TRAIN\|M2_vs_M1` | `[-0.0074, 0.0039]` | `[-0.0074, 0.0039]` | 8 | MATCH |
| S1 P03 S0 | `P03\|hkd_9988\|h=63\|TUNE\|M2_vs_M1` | `[-0.0027, 0.0054]` | `[-0.0027, 0.0054]` | 10 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=5\|TRAIN\|M1_vs_M0` | `[0.001, 0.0017]` | `[0.001, 0.0017]` | 404 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=5\|TUNE\|M1_vs_M0` | `[0.0008, 0.0019]` | `[0.0008, 0.0019]` | 109 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=5\|TRAIN\|M2_vs_M1` | `[0.0, 0.0004]` | `[0.0, 0.0004]` | 101 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=5\|TUNE\|M2_vs_M1` | `[-0.0001, 0.0001]` | `[-0.0001, 0.0001]` | 109 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=21\|TRAIN\|M1_vs_M0` | `[0.0038, 0.0095]` | `[0.0038, 0.0095]` | 109 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=21\|TUNE\|M1_vs_M0` | `[0.001, 0.0092]` | `[0.001, 0.0092]` | 28 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=21\|TRAIN\|M2_vs_M1` | `[-0.0008, 0.0021]` | `[-0.0008, 0.0021]` | 26 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=21\|TUNE\|M2_vs_M1` | `[-0.0004, 0.0004]` | `[-0.0004, 0.0004]` | 28 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=63\|TRAIN\|M1_vs_M0` | `[0.0092, 0.0237]` | `[0.0092, 0.0237]` | 37 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=63\|TUNE\|M1_vs_M0` | `[0.0068, 0.0226]` | `[0.0068, 0.0226]` | 10 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=63\|TRAIN\|M2_vs_M1` | `[-0.0068, -0.0]` | `[-0.0068, -0.0]` | 8 | MATCH |
| S1 P03 S0 | `P03\|hkd_0700\|h=63\|TUNE\|M2_vs_M1` | `[-0.0028, 0.0019]` | `[-0.0028, 0.0019]` | 10 | MATCH |
| S2 P04 | `P04/TRAIN/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/TRAIN/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/TRAIN/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/TUNE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/TUNE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/TUNE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/QUARANTINE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/QUARANTINE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P04 | `P04/QUARANTINE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TRAIN/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TRAIN/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TRAIN/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TUNE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TUNE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/TUNE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/QUARANTINE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/QUARANTINE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P05 | `P05/QUARANTINE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TRAIN/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TRAIN/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TRAIN/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TUNE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TUNE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/TUNE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/QUARANTINE/h5` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/QUARANTINE/h21` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |
| S2 P06 | `P06/QUARANTINE/h63` | `CI NOT ESTIMABLE (cluster-N < 2)` | `—` | excess not committed | GAP |


P01/P02 H0_1 and H0_2 share one excess series per (subject, horizon,
split, baseline); both sealed `ci.ci95` values MATCH that single call.
P03 S0 lower bound is `ci.ci95[0]` on the same reproduced interval.

## Mirror-trick derivation

`engine.grading_stats.block_bootstrap_ci` (grading_stats.py:121-190)
returns a 95% percentile CI on the **gap** (conditional stat − base
stat), resampling whole date labels so same-stamp rows move together.

Sealing builds a mirrored panel so that gap equals the mean of x
(residual/s1_stats.py:70-74; residual/run_s1.py:690 for P03 `d`;
residual/run_s1.py:422-427 for P01/P02 excess):

    dates = concat(k, k)
    vals  = concat(x, -x)
    mask  = concat([True]*n, [False]*n)

Each resampled date block then carries that date's x-row and its
negation. Conditional mean = mean(x*). Unconditional mean =
mean(concat(x*, −x*)) = 0. Gap = mean(x*). The returned `[lo, hi]`
(2.5th and 97.5th percentiles of 800 draws, rounded to 4 dp) is
therefore a date-block bootstrap CI of mean(x).

P03 S0 uses only the lower bound: next beats prev on a split iff
`delta_R2 > 0` AND `ci[0] > 0` (approximately one-sided alpha 0.025).
On P03, x is `d_i = (r − common_prev)² − (r − common_next)²` with
cluster key = `anchor_session_date` of the next-model row. On P01/P02,
x is honest-set excess at the block baseline.

A synthetic constant series `x = [0.25]*4` reproduces `[0.25, 0.25]`
from the same registered draws/seed/stat. The residual statistic is
descriptive. It is never treated as causal news impact (A24).

Sealing call sites (read for input shaping only; the test does not
import them):

- `residual/s1_stats.py:47-74` `mirror_mean_ci`
- `residual/run_s1.py:352-375, 422-427` P01/P02 usable excess
- `residual/run_s1.py:671-727` P03 paired `d` and S0 `ci_block`
- `event_response/s2_stats.py:63-73` `mirror_trick_ci`
- `event_response/run_s2.py:327-335` (numeric CI only when the cell is TESTED)

Observation columns:

- P01/P02: filter `manifest_split == split` and `abstention == OK` and
  direction `!= 0`; value column `excess`; date column
  `anchor_session_date`.
- P03: pair by `episode_key`; prev `split == split`, `abstention == OK`,
  `r__oc` present; next `abstention == OK`, `common__oc` present; value
  `d` as above; date = next `anchor_session_date`.

## Gaps

- **IRP-GAP4 / P03 IPCA (6 blocks).** Observation JSON for
  `P03_adr_baba_{5,21,63}.json` contains models M0, M1, M2 only.
  Sealed `IPCA_vs_M1` `ci.ci95` cannot be rebuilt. Strict-xfail reason:
  `IRP-GAP4: P03 IPCA model rows not committed in observations/`.
- **IRP-GAP4 / S2 (27 cells).** `observations/episodes.jsonl` has six
  P04 TUNE rows. Census-only tencent rows have no outcome. Graded
  alibaba rows are RETIRED-CONTAMINATED with excess null. P05/P06 have
  no committed episodes. Sealed `ci` is the string
  `CI NOT ESTIMABLE (cluster-N < 2)`. Strict-xfail reason:
  `IRP-GAP4: S2 episode excess values not committed in observations/episodes.jsonl`.
- `SEAL_AND_BUDGET.json` does not pin draws/seed; numerals come from
  PREREG `mirror_trick.construction`.
- S2 PREREG names `default draws/seed` without numerals.

No IRP-F4 DIFF. Determinism: the same registered call twice is
identical; seed 8 on the P01 adr_baba h=5 TRAIN always_long series
yields a different interval `[-0.006, 0.005]` vs sealed
`[-0.0061, 0.0064]`.

## What this does NOT prove

- reproduction of a registered interval is not statistical validity
- no acceptance row moves
- not probabilistic forecast support
- inputs remain vintage-unpinned as the results label them
- the comparison does not speak to causal news impact (A24)
- families that cannot be estimated from the committed files abstain
  with a named IRP-GAP4 reason; they are not filled with 50/50 (A25)
