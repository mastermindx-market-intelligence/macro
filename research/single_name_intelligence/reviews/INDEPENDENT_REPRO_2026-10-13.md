# Independent reproduction of SNI v1.1 registered hit/return statistics

Date: 2026-10-13
Lane: IRP (commission 8659, acceptance row A29)
Implementation: stdlib-only (`tests/test_sni_independent_repro.py`); no import of production SNI packages.

This module is an SNI-local DRAFT comparison. It CONSUMES committed observation files and committed result JSON. Identity strings (`episode_key`, `issuer_key`) are caller-supplied opaque values owned by Stock Identity / Data OS. This file does not mint identifiers and does not feed a rank, gate, size, signal, escalation, or trade path. Every authority flag in the result files is literal false.

## Summary

An independent counter read the committed v1.1 observation files and recomputed the registered headline statistics in `results/P01.json` … `P06.json`.

- S1 P01: 24/24 blocks MATCH (honest_n, cluster_n, literal_rows, every exclusions counter, hit/pos/neg statistic, exact binomial or sign-test p-value within 1e-12, reject/no-reject at the stated alpha).
- S1 P02: 48/48 blocks MATCH on the same fields.
- S1 P03 M0/M1/M2 pairs: 36/36 blocks MATCH on honest_n, cluster_n, literal_rows, exclusions (including `pair_incomplete`), and `delta_R2` / `paired_units`.
- S1 P03 IPCA_vs_M1: 6/6 blocks GAP — IPCA model rows are not in the committed observation JSON (files hold M0/M1/M2 only). literal_rows of those files still MATCH. Tests pin the GAP as `xfail(strict=True, reason="IRP-GAP: P03 IPCA model rows not committed in observations/")`.
- S2 P04–P06: every TRAIN/TUNE/QUARANTINE × h5/h21/h63 cell MATCHES on honest_n.PRIMARY, cluster_n.PRIMARY, confounded, absorbed, purged, quarantine, and the registered abstention token (`ABSTAIN_NO_EPISODES` or `ABSTAIN_INSUFFICIENT_CLUSTERS`). The TEST split MATCHES the prospective-only string. P04 TUNE cells have honest_n.PRIMARY = 1 (the graded alibaba episode) and cluster-N = 1, so the token is `ABSTAIN_INSUFFICIENT_CLUSTERS`. Numeric hit/excess values are null on those rows (RETIRED-CONTAMINATED; outcome not computed) and MATCH as null.
- S2 `literal_row_count` (registered 7 on every cell) is GAP: episodes.jsonl does not contain the census that produces 7.
- S2 `excluded_and_listed` identities on P04 (`earnings.parquet#ticker=BABA`) and P05 (`12295308,12295380,12300619`) are GAP: those strings are not on episode rows. P06 listed identities are empty and MATCH `[]`.

No integer disagreement was found on any field that the committed observations can support. There is no IRP-F* DIFF.

## Rules as re-derived

Written here in this lane's words after reading the spec files. Production functions were not copied.

### Splits, purge, quarantine

From `research/single_name_intelligence/runs/s1_residual_v1_1/PREREG_SPEC.json` line 1, key `splits`, and `event_response/s2_splits.py` lines 39–44 and 57–66:

- TRAIN is an opener/anchor session date s before 2024-01-01.
- TUNE is 2024-01-01 ≤ s < 2026-10-01.
- QUARANTINE is s ≥ 2026-10-01: listed and counted, never evaluated.
- A TRAIN window whose last session (coverage) is on or after 2024-01-01 is PURGED_TRAIN. A TUNE window whose coverage is on or after 2026-10-01 is PURGED_TUNE. Purged units keep a visible flag and are never moved into another split.
- S2 TEST is prospective only; REG §2 is not met, so the historical-descriptive run has no TEST cells (`s2_splits.py` module docstring, lines 1–7; result files store a string on `splits.TEST`).

S1 observation rows carry both `time_split` (TRAIN/TUNE/QUARANTINE from the anchor date) and `split` (the membership label, which may be PURGED_*, QUARANTINE, or an abstention token such as ABSTAIN_RESOLVER_NONE). A TRAIN/TUNE block's listed abstentions are the rows whose `time_split` equals that block's split. File-level `purged` and `quarantine` counters count every PURGED_* / QUARANTINE label in the observation file, which is how P01/P02 registered those two fields.

### What is a hit, a tie, an abstention (P01/P02)

From `PREREG_SPEC.json` line 1, key `protocols.P01.hit_rule` (P02 says "as P01"), `residual/s1_direction.py` lines 21–22 and 32–47, and `residual/s1_stats.py` lines 23–44:

- Baseline always-long: direction is +1 (`s1_direction.py` line 22).
- Baseline trail63: sign of the trailing-63-session excess at D(s). Missing endpoints or an exact-zero trail yield direction 0; direction 0 abstains (listed in `direction_0_abstain`, not a hit and not a miss).
- A hit is `sign(excess) == direction`. An exact-zero excess is a non-hit listed as a tie (`ties_non_hit`) and stays in honest-N. H0_2 drops zeros from the sign-test n (`s1_stats.py` lines 37–39: "Zeros (exact ties) are excluded by the caller").
- Window abstentions ABSTAIN_RESOLVER_NONE, ABSTAIN_FILL_MISMATCH, and ABSTAIN_MISSING_ENDPOINT are listed, increment `excluded_listed`, and leave honest-N. On P02 hkd_0700 those resolver-none rows are stored with `split=ABSTAIN_RESOLVER_NONE` and `time_split=TRAIN`.

honest-N is the count of remaining evaluable rows on that split. cluster-N for rolling anchors equals the number of distinct `anchor_session_date` values in that honest set (`PREREG_SPEC.json` key `rolling_anchors`).

### Tests and sidedness (P01/P02)

From `s1_stats.py` lines 20, 23–29, 32–34, 37–44 and `PREREG_SPEC.json` key `protocols.P01.tests`:

- H0_1: null hit rate = 0.50. Exact one-sided binomial (greater), P(X ≥ k) for X ~ Bin(n, 1/2), summed through `math.comb`, alpha 0.05. Reject when p ≤ 0.05.
- H0_2: null median excess = 0. Exact two-sided sign test: n = pos + neg, b = max(pos, neg), p = min(1, 2 × P(X ≥ b)). Alpha 0.05. This lane recomputes that p-value because it is the registered `test.p_value` on H0_2 blocks.
- A block with honest_n < 153 still stores the statistic and p-value; the `null` string leads with ABSTAIN (REG power floor). The reproduction compares the stored numbers, not the lead wording.

This lane uses `fractions.Fraction` over `math.comb` and compares the float p-value within 1e-12 absolute.

### P03 incremental explanation

From `PREREG_SPEC.json` line 1, key `protocols.P03.incremental_criterion`:

- Pair units where both models are OK on the split.
- d_i = (r − common_prev)² − (r − common_next)², equivalently resid_prev² − resid_next².
- delta_R2 = sum(d) / sum(r²). paired_units = number of OK pairs.
- If the previous model is OK on the split and the next model is missing or not OK, the unit is `pair_incomplete` (and `excluded_listed`). `challenger_not_ok` is registered 0 on these v1.1 files; this lane reproduces 0.
- The S0 decision (delta_R2 > 0 AND bootstrap CI lower bound > 0) uses `engine.grading_stats.block_bootstrap_ci`. That CI is not recomputed here (engine primitive, not an observation). The registered numeric statistic on each P03 block is delta_R2 and paired_units; those are what this lane reproduces.

### S2 counting and abstention ladder

From `event_response/s2_outcomes.py` lines 27–29 and 77–99, `s2_stats.py` lines 27–30 and 33–41, `s2_splits.py` lines 39–66, and `runs/s2_event_response_v1_1/PREREG_SPEC.json` keys `splits`, `statistics`, `abstention_ladder`, `honest_n_note` in the result files:

- honest-N counts the graded cohort (alibaba) only. Rows with `census_only=true` (tencent in the committed file) are listed and never enter honest-N.
- The committed `observations/episodes.jsonl` holds six rows, all P04 TUNE: three census-only tencent, three graded alibaba with outcome state RETIRED-CONTAMINATED (information_leak) — outcome not computed. Per horizon that is honest_n = 1, cluster_n = 1.
- Abstention ladder, first match (`PREREG_SPEC.json` key `abstention_ladder`): honest-N 0 → ABSTAIN_NO_EPISODES; cluster-N < 2 → ABSTAIN_INSUFFICIENT_CLUSTERS; below 153 → DESCRIPTIVE_ONLY; else TESTED. Never a 0.5 fill (A25).
- When a cell is ABSTAIN_*, there is no binomial statistic to recompute. Registered `hit` on the printed baseline episode rows is null; this lane MATCHES null.
- `s2_stats.py` lines 33–41 state the exact one-sided binomial (greater) that would apply to a TESTED cell. No v1.1 cell is TESTED.

## Reproduction table

Headline tallies: S1 MATCH 108 blocks, S1 GAP 6 blocks (IPCA), S1 DIFF 0. S2 core/test MATCH on all 27 cells plus 3 TEST rows; S2 GAP on 27 `literal_row_count` fields and 18 P04/P05 `excluded_and_listed` fields; S2 DIFF 0.

### S1 (P01–P03)

| protocol | block | field | registered | reproduced | status |
| --- | --- | --- | --- | --- | --- |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | honest_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | cluster_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | statistic.hits | 170 | 170 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | statistic.n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_1` | p_value | 0.6661759028156388 | 0.6661759028156388 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | honest_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | cluster_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | statistic.pos | 170 | 170 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | statistic.neg | 177 | 177 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/always_long/H0_2` | p_value | 0.7474320683398622 | 0.7474320683398622 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | honest_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | cluster_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.hits | 50 | 50 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | p_value | 0.9201192461074909 | 0.9201192461074909 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | honest_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | cluster_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.pos | 50 | 50 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.neg | 64 | 64 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | p_value | 0.2232303624555456 | 0.2232303624555456 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | honest_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | cluster_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | statistic.hits | 182 | 182 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | statistic.n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_1` | p_value | 0.19520610073617778 | 0.19520610073617778 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | honest_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | cluster_n | 347 | 347 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | statistic.pos | 170 | 170 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | statistic.neg | 177 | 177 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=5/TRAIN/trail63/H0_2` | p_value | 0.7474320683398622 | 0.7474320683398622 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | honest_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | cluster_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.hits | 57 | 57 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | p_value | 0.5372825193716376 | 0.5372825193716376 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | honest_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | cluster_n | 114 | 114 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | literal_rows | 464 | 464 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.pos | 50 | 50 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.neg | 64 | 64 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=5/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | p_value | 0.2232303624555456 | 0.2232303624555456 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | honest_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | cluster_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | statistic.hits | 46 | 46 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | statistic.n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_1` | p_value | 0.6214054629287974 | 0.6214054629287974 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | honest_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | cluster_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | statistic.pos | 46 | 46 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | statistic.neg | 48 | 48 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/always_long/H0_2` | p_value | 0.9179230673157426 | 0.9179230673157426 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | honest_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | cluster_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.hits | 15 | 15 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | p_value | 0.639949934091419 | 0.639949934091419 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | honest_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | cluster_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.pos | 15 | 15 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.neg | 16 | 16 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | honest_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | cluster_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | statistic.hits | 53 | 53 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | statistic.n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_1` | p_value | 0.12822117446648462 | 0.12822117446648462 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | honest_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | cluster_n | 94 | 94 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | statistic.pos | 46 | 46 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | statistic.neg | 48 | 48 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=21/TRAIN/trail63/H0_2` | p_value | 0.9179230673157426 | 0.9179230673157426 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | honest_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | cluster_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.hits | 14 | 14 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | p_value | 0.7634351700544357 | 0.7634351700544357 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | honest_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | cluster_n | 31 | 31 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | literal_rows | 127 | 127 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.pos | 15 | 15 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.neg | 16 | 16 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=21/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | honest_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | cluster_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | statistic.hits | 14 | 14 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | statistic.n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_1` | p_value | 0.8114572062622756 | 0.8114572062622756 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | honest_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | cluster_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | statistic.pos | 14 | 14 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | statistic.neg | 18 | 18 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/always_long/H0_2` | p_value | 0.5966148958541453 | 0.5966148958541453 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | honest_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | cluster_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.hits | 4 | 4 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | statistic.n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_1` | p_value | 0.828125 | 0.828125 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | honest_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | cluster_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.pos | 4 | 4 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.neg | 6 | 6 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/always_long/H0_2` | p_value | 0.75390625 | 0.75390625 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | honest_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | cluster_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | statistic.hits | 16 | 16 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | statistic.n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_1` | p_value | 0.5699749670457095 | 0.5699749670457095 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | honest_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | cluster_n | 32 | 32 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | statistic.pos | 14 | 14 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | statistic.neg | 18 | 18 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=63/TRAIN/trail63/H0_2` | p_value | 0.5966148958541453 | 0.5966148958541453 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | honest_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | cluster_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.hits | 4 | 4 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | statistic.n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_1` | p_value | 0.828125 | 0.828125 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | honest_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | cluster_n | 10 | 10 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | literal_rows | 44 | 44 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.pos | 4 | 4 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.neg | 6 | 6 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P01 | `P01/adr_baba/h=63/TUNE (NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK))/trail63/H0_2` | p_value | 0.75390625 | 0.75390625 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | honest_n | 121 | 121 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | cluster_n | 121 | 121 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | statistic.hits | 49 | 49 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | statistic.n | 121 | 121 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_1` | p_value | 0.9856484004131315 | 0.9856484004131315 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | honest_n | 121 | 121 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | cluster_n | 121 | 121 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | statistic.pos | 49 | 49 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | statistic.neg | 72 | 72 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/always_long/H0_2` | p_value | 0.045051739725735895 | 0.045051739725735895 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | honest_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | cluster_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | statistic.hits | 53 | 53 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | statistic.n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_1` | p_value | 0.7153898860982126 | 0.7153898860982126 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | honest_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | cluster_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | statistic.pos | 53 | 53 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | statistic.neg | 58 | 58 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/always_long/H0_2` | p_value | 0.7043793154248914 | 0.7043793154248914 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | honest_n | 119 | 119 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | cluster_n | 119 | 119 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | statistic.hits | 64 | 64 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | statistic.n | 119 | 119 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_1` | p_value | 0.23174408831138207 | 0.23174408831138207 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | honest_n | 119 | 119 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | cluster_n | 119 | 119 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | `{'excluded_listed': 4, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 4, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | statistic.pos | 47 | 47 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | statistic.neg | 72 | 72 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=5/TRAIN/trail63/H0_2` | p_value | 0.027379102500930414 | 0.027379102500930414 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | honest_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | cluster_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | statistic.hits | 54 | 54 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | statistic.n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_1` | p_value | 0.6478103422875543 | 0.6478103422875543 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | honest_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | cluster_n | 111 | 111 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | literal_rows | 239 | 239 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 1, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | statistic.pos | 53 | 53 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | statistic.neg | 58 | 58 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=5/TUNE/trail63/H0_2` | p_value | 0.7043793154248914 | 0.7043793154248914 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | honest_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | cluster_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | statistic.hits | 14 | 14 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | statistic.n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_1` | p_value | 0.8518968157004565 | 0.8518968157004565 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | honest_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | cluster_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | statistic.pos | 14 | 14 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | statistic.neg | 19 | 19 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/always_long/H0_2` | p_value | 0.48685024166479707 | 0.48685024166479707 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | honest_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | cluster_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | statistic.hits | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | statistic.n | 28 | 28 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_1` | p_value | 0.9075333289802074 | 0.9075333289802074 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | honest_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | cluster_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | statistic.pos | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | statistic.neg | 17 | 17 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/always_long/H0_2` | p_value | 0.34492845088243484 | 0.34492845088243484 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | honest_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | cluster_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | statistic.hits | 12 | 12 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | statistic.n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_1` | p_value | 0.9599283437710255 | 0.9599283437710255 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | honest_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | cluster_n | 33 | 33 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | statistic.pos | 14 | 14 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | statistic.neg | 19 | 19 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=21/TRAIN/trail63/H0_2` | p_value | 0.48685024166479707 | 0.48685024166479707 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | honest_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | cluster_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | statistic.hits | 12 | 12 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | statistic.n | 27 | 27 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_1` | p_value | 0.7789658308029175 | 0.7789658308029175 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | honest_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | cluster_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | literal_rows | 66 | 66 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | statistic.pos | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | statistic.neg | 16 | 16 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=21/TUNE/trail63/H0_2` | p_value | 0.44206833839416504 | 0.44206833839416504 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | honest_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | cluster_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | statistic.hits | 2 | 2 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | statistic.n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_1` | p_value | 0.994140625 | 0.994140625 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | honest_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | cluster_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | statistic.pos | 2 | 2 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | statistic.neg | 9 | 9 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/always_long/H0_2` | p_value | 0.0654296875 | 0.0654296875 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | statistic.hits | 5 | 5 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | statistic.n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_1` | p_value | 0.623046875 | 0.623046875 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | statistic.pos | 5 | 5 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | statistic.neg | 5 | 5 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/always_long/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | honest_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | cluster_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | statistic.hits | 7 | 7 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | statistic.n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_1` | p_value | 0.2744140625 | 0.2744140625 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | honest_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | cluster_n | 11 | 11 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | statistic.pos | 2 | 2 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | statistic.neg | 9 | 9 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=63/TRAIN/trail63/H0_2` | p_value | 0.0654296875 | 0.0654296875 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | statistic.hits | 6 | 6 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | statistic.n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_1` | p_value | 0.376953125 | 0.376953125 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | literal_rows | 23 | 23 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | statistic.pos | 5 | 5 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | statistic.neg | 5 | 5 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_9988/h=63/TUNE/trail63/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | honest_n | 404 | 404 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | cluster_n | 404 | 404 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | statistic.hits | 200 | 200 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | statistic.n | 404 | 404 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_1` | p_value | 0.5982078220201428 | 0.5982078220201428 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | honest_n | 404 | 404 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | cluster_n | 404 | 404 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | statistic.pos | 200 | 200 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | statistic.neg | 204 | 204 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/always_long/H0_2` | p_value | 0.8813758029467572 | 0.8813758029467572 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | honest_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | cluster_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | statistic.hits | 60 | 60 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | statistic.n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_1` | p_value | 0.16909270609833058 | 0.16909270609833058 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | honest_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | cluster_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | statistic.pos | 60 | 60 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | statistic.neg | 49 | 49 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/always_long/H0_2` | p_value | 0.33818541219666115 | 0.33818541219666115 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | honest_n | 400 | 400 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | cluster_n | 400 | 400 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}` | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | statistic.hits | 190 | 190 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | statistic.n | 400 | 400 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_1` | p_value | 0.853145940919109 | 0.853145940919109 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | honest_n | 400 | 400 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | cluster_n | 400 | 400 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}` | `{'excluded_listed': 363, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 360, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 3, 'direction_0_abstain': 4, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | statistic.pos | 196 | 196 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | statistic.neg | 204 | 204 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=5/TRAIN/trail63/H0_2` | p_value | 0.7263869151831212 | 0.7263869151831212 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | honest_n | 104 | 104 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | cluster_n | 104 | 104 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}` | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | statistic.hits | 53 | 53 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | statistic.n | 104 | 104 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_1` | p_value | 0.46097441381321547 | 0.46097441381321547 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | honest_n | 104 | 104 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | cluster_n | 104 | 104 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | literal_rows | 881 | 881 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}` | `{'excluded_listed': 2, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 5, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | statistic.pos | 59 | 59 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | statistic.neg | 45 | 45 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=5/TUNE/trail63/H0_2` | p_value | 0.20217310609617567 | 0.20217310609617567 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | honest_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | cluster_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | statistic.hits | 67 | 67 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | statistic.n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_1` | p_value | 0.010543202856568812 | 0.010543202856568812 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | honest_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | cluster_n | 109 | 109 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | statistic.pos | 67 | 67 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | statistic.neg | 42 | 42 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/always_long/H0_2` | p_value | 0.021086405713137624 | 0.021086405713137624 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | honest_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | cluster_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | statistic.hits | 14 | 14 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | statistic.n | 28 | 28 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_1` | p_value | 0.5747229903936386 | 0.5747229903936386 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | honest_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | cluster_n | 28 | 28 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | statistic.pos | 14 | 14 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | statistic.neg | 14 | 14 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/always_long/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | honest_n | 107 | 107 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | cluster_n | 107 | 107 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | statistic.hits | 58 | 58 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | statistic.n | 107 | 107 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_1` | p_value | 0.21972005088954139 | 0.21972005088954139 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | honest_n | 107 | 107 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | cluster_n | 107 | 107 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | `{'excluded_listed': 100, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 98, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 2, 'direction_0_abstain': 2, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | statistic.pos | 65 | 65 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | statistic.neg | 42 | 42 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=21/TRAIN/trail63/H0_2` | p_value | 0.03294666029982694 | 0.03294666029982694 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | honest_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | cluster_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | statistic.hits | 14 | 14 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | statistic.n | 27 | 27 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_1` | p_value | 0.5 | 0.5 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | honest_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | cluster_n | 27 | 27 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | literal_rows | 241 | 241 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | `{'excluded_listed': 1, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 1, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 1, 'direction_0_abstain': 1, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | statistic.pos | 13 | 13 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | statistic.neg | 14 | 14 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=21/TUNE/trail63/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | honest_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | cluster_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | exclusions | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | statistic.hits | 22 | 22 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | statistic.n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_1` | p_value | 0.1620043000439182 | 0.1620043000439182 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | honest_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | cluster_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | exclusions | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | statistic.pos | 22 | 22 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | statistic.neg | 15 | 15 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/always_long/H0_2` | p_value | 0.3240086000878364 | 0.3240086000878364 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | statistic.hits | 5 | 5 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | statistic.n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_1` | p_value | 0.623046875 | 0.623046875 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | statistic.pos | 5 | 5 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | statistic.neg | 5 | 5 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/always_long/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | honest_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | cluster_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | exclusions | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | statistic.hits | 20 | 20 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | statistic.n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_1` | p_value | 0.3714146793645341 | 0.3714146793645341 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | honest_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | cluster_n | 37 | 37 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | exclusions | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 34, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 34, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | statistic.pos | 22 | 22 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | statistic.neg | 15 | 15 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TRAIN/trail63/H0_2` | p_value | 0.3240086000878364 | 0.3240086000878364 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | statistic.hits | 7 | 7 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | statistic.n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_1` | p_value | 0.171875 | 0.171875 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | honest_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | cluster_n | 10 | 10 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | literal_rows | 83 | 83 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 2, 'quarantine': 0, 'detail': {'abstain_resolver_none': 0, 'abstain_fill_mismatch': 0, 'abstain_missing_endpoint': 0, 'direction_0_abstain': 0, 'ties_non_hit': 0}}` | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | statistic.pos | 5 | 5 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | statistic.neg | 5 | 5 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | statistic.zeros_excluded | 0 | 0 | MATCH |
| P02 | `P02/hkd_0700/h=63/TUNE/trail63/H0_2` | p_value | 1.0 | 1.0 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | honest_n | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | cluster_n | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.18408397 | 0.18408397236350038 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M1_vs_M0` | statistic.paired_units | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | honest_n | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | cluster_n | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.10975489 | 0.10975488648231867 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M1_vs_M0` | statistic.paired_units | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | honest_n | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | cluster_n | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.52577345 | 0.5257734469636997 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/M2_vs_M1` | statistic.paired_units | 347 | 347 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | honest_n | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | cluster_n | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.54676282 | 0.546762819310439 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/M2_vs_M1` | statistic.paired_units | 114 | 114 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/IPCA_vs_M1` | honest_n | 346 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=5/TRAIN/IPCA_vs_M1` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TRAIN/IPCA_vs_M1` | statistic | `{'delta_R2': 0.01351695, 'paired_units': 346}` | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=5/TUNE/IPCA_vs_M1` | honest_n | 114 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=5/TUNE/IPCA_vs_M1` | literal_rows | 1383 | 1383 | MATCH |
| P03 | `P03/adr_baba/h=5/TUNE/IPCA_vs_M1` | statistic | `{'delta_R2': -0.00290051, 'paired_units': 114}` | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | honest_n | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | cluster_n | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.10403221 | 0.10403220859182032 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M1_vs_M0` | statistic.paired_units | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | honest_n | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | cluster_n | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.05614115 | 0.05614115417515398 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M1_vs_M0` | statistic.paired_units | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | honest_n | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | cluster_n | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.53929845 | 0.5392984475947236 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/M2_vs_M1` | statistic.paired_units | 94 | 94 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | honest_n | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | cluster_n | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.53901104 | 0.5390110448091225 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/M2_vs_M1` | statistic.paired_units | 31 | 31 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/IPCA_vs_M1` | honest_n | 93 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=21/TRAIN/IPCA_vs_M1` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TRAIN/IPCA_vs_M1` | statistic | `{'delta_R2': 0.00864227, 'paired_units': 93}` | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=21/TUNE/IPCA_vs_M1` | honest_n | 31 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=21/TUNE/IPCA_vs_M1` | literal_rows | 375 | 375 | MATCH |
| P03 | `P03/adr_baba/h=21/TUNE/IPCA_vs_M1` | statistic | `{'delta_R2': -0.01964421, 'paired_units': 31}` | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | honest_n | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | cluster_n | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.16935998 | 0.1693599766668331 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M1_vs_M0` | statistic.paired_units | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.03191235 | 0.03191235090379785 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M1_vs_M0` | statistic.paired_units | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | honest_n | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | cluster_n | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.5935294 | 0.5935293964688831 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/M2_vs_M1` | statistic.paired_units | 32 | 32 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.30317151 | 0.30317151084108346 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/M2_vs_M1` | statistic.paired_units | 10 | 10 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/IPCA_vs_M1` | honest_n | 31 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=63/TRAIN/IPCA_vs_M1` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TRAIN/IPCA_vs_M1` | statistic | `{'delta_R2': 0.00358868, 'paired_units': 31}` | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=63/TUNE/IPCA_vs_M1` | honest_n | 10 | IPCA rows not committed | GAP |
| P03 | `P03/adr_baba/h=63/TUNE/IPCA_vs_M1` | literal_rows | 126 | 126 | MATCH |
| P03 | `P03/adr_baba/h=63/TUNE/IPCA_vs_M1` | statistic | `{'delta_R2': -0.02005018, 'paired_units': 10}` | IPCA rows not committed | GAP |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | honest_n | 121 | 121 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | cluster_n | 121 | 121 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | literal_rows | 711 | 711 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.67209468 | 0.6720946799670247 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M1_vs_M0` | statistic.paired_units | 121 | 121 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | honest_n | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | cluster_n | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | literal_rows | 711 | 711 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.64736264 | 0.6473626441402973 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M1_vs_M0` | statistic.paired_units | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | honest_n | 99 | 99 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | cluster_n | 99 | 99 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | literal_rows | 711 | 711 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 22, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 22, 'challenger_not_ok': 0}}` | `{'excluded_listed': 22, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 22, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.02143186 | 0.02143185992567952 | MATCH |
| P03 | `P03/hkd_9988/h=5/TRAIN/M2_vs_M1` | statistic.paired_units | 99 | 99 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | honest_n | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | cluster_n | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | literal_rows | 711 | 711 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.00279343 | 0.002793427828929501 | MATCH |
| P03 | `P03/hkd_9988/h=5/TUNE/M2_vs_M1` | statistic.paired_units | 111 | 111 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | honest_n | 33 | 33 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | cluster_n | 33 | 33 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | literal_rows | 189 | 189 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.54944911 | 0.5494491129651777 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M1_vs_M0` | statistic.paired_units | 33 | 33 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | honest_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | cluster_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | literal_rows | 189 | 189 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.67827296 | 0.6782729641800718 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M1_vs_M0` | statistic.paired_units | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | honest_n | 26 | 26 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | cluster_n | 26 | 26 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | literal_rows | 189 | 189 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 7, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 7, 'challenger_not_ok': 0}}` | `{'excluded_listed': 7, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 7, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.08160776 | 0.08160776453364002 | MATCH |
| P03 | `P03/hkd_9988/h=21/TRAIN/M2_vs_M1` | statistic.paired_units | 26 | 26 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | honest_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | cluster_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | literal_rows | 189 | 189 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.02128548 | 0.02128548432186744 | MATCH |
| P03 | `P03/hkd_9988/h=21/TUNE/M2_vs_M1` | statistic.paired_units | 28 | 28 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | honest_n | 11 | 11 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | cluster_n | 11 | 11 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | literal_rows | 63 | 63 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.64629226 | 0.6462922581122739 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M1_vs_M0` | statistic.paired_units | 11 | 11 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | literal_rows | 63 | 63 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.40734683 | 0.40734683210969597 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M1_vs_M0` | statistic.paired_units | 10 | 10 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | honest_n | 8 | 8 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | cluster_n | 8 | 8 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | literal_rows | 63 | 63 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 3, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 3, 'challenger_not_ok': 0}}` | `{'excluded_listed': 3, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 3, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | statistic.delta_R2 | -0.03529472 | -0.03529472289532918 | MATCH |
| P03 | `P03/hkd_9988/h=63/TRAIN/M2_vs_M1` | statistic.paired_units | 8 | 8 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | literal_rows | 63 | 63 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.06248689 | 0.062486892965095756 | MATCH |
| P03 | `P03/hkd_9988/h=63/TUNE/M2_vs_M1` | statistic.paired_units | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | honest_n | 404 | 404 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | cluster_n | 404 | 404 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | literal_rows | 1554 | 1554 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.57576813 | 0.5757681301029356 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M1_vs_M0` | statistic.paired_units | 404 | 404 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | honest_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | cluster_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | literal_rows | 1554 | 1554 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.63124453 | 0.6312445306396673 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M1_vs_M0` | statistic.paired_units | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | honest_n | 101 | 101 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | cluster_n | 101 | 101 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | literal_rows | 1554 | 1554 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 303, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 303, 'challenger_not_ok': 0}}` | `{'excluded_listed': 303, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 303, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.06291382 | 0.06291381897243095 | MATCH |
| P03 | `P03/hkd_0700/h=5/TRAIN/M2_vs_M1` | statistic.paired_units | 101 | 101 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | honest_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | cluster_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | literal_rows | 1554 | 1554 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | statistic.delta_R2 | 0.0050775 | 0.00507750141086255 | MATCH |
| P03 | `P03/hkd_0700/h=5/TUNE/M2_vs_M1` | statistic.paired_units | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | honest_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | cluster_n | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | literal_rows | 420 | 420 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.61073409 | 0.6107340886247419 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M1_vs_M0` | statistic.paired_units | 109 | 109 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | honest_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | cluster_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | literal_rows | 420 | 420 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.6226734 | 0.6226733974774246 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M1_vs_M0` | statistic.paired_units | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | honest_n | 26 | 26 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | cluster_n | 26 | 26 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | literal_rows | 420 | 420 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 83, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 83, 'challenger_not_ok': 0}}` | `{'excluded_listed': 83, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 83, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | statistic.delta_R2 | 0.03396839 | 0.03396839110561312 | MATCH |
| P03 | `P03/hkd_0700/h=21/TRAIN/M2_vs_M1` | statistic.paired_units | 26 | 26 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | honest_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | cluster_n | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | literal_rows | 420 | 420 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | statistic.delta_R2 | -0.00576019 | -0.005760193412894876 | MATCH |
| P03 | `P03/hkd_0700/h=21/TUNE/M2_vs_M1` | statistic.paired_units | 28 | 28 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | honest_n | 37 | 37 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | cluster_n | 37 | 37 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | literal_rows | 141 | 141 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | statistic.delta_R2 | 0.61631175 | 0.616311750043988 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M1_vs_M0` | statistic.paired_units | 37 | 37 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | literal_rows | 141 | 141 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | statistic.delta_R2 | 0.62180687 | 0.6218068723699506 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M1_vs_M0` | statistic.paired_units | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | honest_n | 8 | 8 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | cluster_n | 8 | 8 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | literal_rows | 141 | 141 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | exclusions | `{'excluded_listed': 29, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 29, 'challenger_not_ok': 0}}` | `{'excluded_listed': 29, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 29, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | statistic.delta_R2 | -0.13727726 | -0.1372772617178499 | MATCH |
| P03 | `P03/hkd_0700/h=63/TRAIN/M2_vs_M1` | statistic.paired_units | 8 | 8 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | honest_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | cluster_n | 10 | 10 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | literal_rows | 141 | 141 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | exclusions | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | `{'excluded_listed': 0, 'confounded': 0, 'absorbed': 0, 'purged': 0, 'quarantine': 0, 'detail': {'pair_incomplete': 0, 'challenger_not_ok': 0}}` | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | statistic.delta_R2 | -0.01802509 | -0.018025092989334086 | MATCH |
| P03 | `P03/hkd_0700/h=63/TUNE/M2_vs_M1` | statistic.paired_units | 10 | 10 | MATCH |

### S2 (P04–P06)

| protocol | split | field | registered | reproduced | status |
| --- | --- | --- | --- | --- | --- |
| P04 | `TRAIN/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TRAIN/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `TRAIN/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TRAIN/h5` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `TRAIN/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TRAIN/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `TRAIN/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TRAIN/h21` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `TRAIN/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TRAIN/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `TRAIN/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TRAIN/h63` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `TUNE/h5` | honest_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h5` | cluster_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TUNE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TUNE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TUNE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TUNE/h5` | test | ABSTAIN_INSUFFICIENT_CLUSTERS | ABSTAIN_INSUFFICIENT_CLUSTERS | MATCH |
| P04 | `TUNE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TUNE/h5` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `TUNE/h21` | honest_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h21` | cluster_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TUNE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TUNE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TUNE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TUNE/h21` | test | ABSTAIN_INSUFFICIENT_CLUSTERS | ABSTAIN_INSUFFICIENT_CLUSTERS | MATCH |
| P04 | `TUNE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TUNE/h21` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `TUNE/h63` | honest_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h63` | cluster_n.PRIMARY | 1 | 1 | MATCH |
| P04 | `TUNE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `TUNE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `TUNE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `TUNE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `TUNE/h63` | test | ABSTAIN_INSUFFICIENT_CLUSTERS | ABSTAIN_INSUFFICIENT_CLUSTERS | MATCH |
| P04 | `TUNE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `TUNE/h63` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `QUARANTINE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h5` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `QUARANTINE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h21` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P04 | `QUARANTINE/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P04 | `QUARANTINE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P04 | `QUARANTINE/h63` | excluded_and_listed | `['earnings.parquet#ticker=BABA']` | not in episodes.jsonl | GAP |
| P04 | TEST | TEST | none (prospective only; REG §2 registration gate not met) | same string | MATCH |
| P05 | `TRAIN/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TRAIN/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TRAIN/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TRAIN/h5` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `TRAIN/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TRAIN/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TRAIN/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TRAIN/h21` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `TRAIN/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TRAIN/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TRAIN/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TRAIN/h63` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `TUNE/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TUNE/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TUNE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TUNE/h5` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `TUNE/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TUNE/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TUNE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TUNE/h21` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `TUNE/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `TUNE/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `TUNE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `TUNE/h63` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `QUARANTINE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h5` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `QUARANTINE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h21` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P05 | `QUARANTINE/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P05 | `QUARANTINE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P05 | `QUARANTINE/h63` | excluded_and_listed | `['12295308,12295380,12300619']` | not in episodes.jsonl | GAP |
| P05 | TEST | TEST | none (prospective only; REG §2 registration gate not met) | same string | MATCH |
| P06 | `TRAIN/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TRAIN/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TRAIN/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TRAIN/h5` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `TRAIN/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TRAIN/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TRAIN/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TRAIN/h21` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `TRAIN/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TRAIN/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TRAIN/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TRAIN/h63` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `TUNE/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TUNE/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TUNE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TUNE/h5` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `TUNE/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TUNE/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TUNE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TUNE/h21` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `TUNE/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `TUNE/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `TUNE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `TUNE/h63` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `QUARANTINE/h5` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h5` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `QUARANTINE/h5` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `QUARANTINE/h5` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `QUARANTINE/h21` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h21` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `QUARANTINE/h21` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `QUARANTINE/h21` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | `QUARANTINE/h63` | honest_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | cluster_n.PRIMARY | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | exclusions.confounded | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | exclusions.absorbed | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | exclusions.purged | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | exclusions.quarantine | 0 | 0 | MATCH |
| P06 | `QUARANTINE/h63` | test | ABSTAIN_NO_EPISODES | ABSTAIN_NO_EPISODES | MATCH |
| P06 | `QUARANTINE/h63` | literal_row_count | 7 | not in episodes.jsonl | GAP |
| P06 | `QUARANTINE/h63` | excluded_and_listed | `[]` | `[]` | MATCH |
| P06 | TEST | TEST | none (prospective only; REG §2 registration gate not met) | same string | MATCH |

## Findings

No IRP-F* DIFF. Every field that the committed observations can support agreed with the registered integer or p-value.

## Gaps

- **IRP-GAP1.** P03 `IPCA_vs_M1` blocks (adr_baba, h ∈ {5,21,63}, TRAIN and TUNE): observation JSON contains models M0, M1, M2 only. Registered honest_n / pair_incomplete / delta_R2 for IPCA cannot be recomputed from committed observations. xfail reason: `IRP-GAP: P03 IPCA model rows not committed in observations/`.
- **IRP-GAP2.** S2 `literal_row_count` is 7 on every TRAIN/TUNE/QUARANTINE cell. `observations/episodes.jsonl` has 6 lines total (P04 TUNE only). The census that produces 7 is not committed. xfail reason: `IRP-GAP: S2 literal_row_count source not committed in observations/episodes.jsonl`.
- **IRP-GAP3.** S2 P04 `excluded_and_listed` = `["earnings.parquet#ticker=BABA"]` and P05 = `["12295308,12295380,12300619"]`. Those identities are not fields on episode rows. xfail reason: `IRP-GAP: S2 excluded_and_listed identities not committed in observations/episodes.jsonl`.
- **IRP-GAP4.** P03 S0 CI lower bound (mirror-trick block bootstrap) and S1 `ci` intervals are not observation-only statistics; they call `engine.grading_stats.block_bootstrap_ci`. This lane does not reproduce those intervals. Narrowed by the follow-up lane in `IRP_GAP4_BOOTSTRAP_REPRO_2026-10-13.md`: 108 S1 `ci.ci95` intervals (P01/P02, P03 M1_vs_M0 and M2_vs_M1) and the 36 P03 S0 lower bounds now MATCH; P03 IPCA_vs_M1 (6, the IRP-GAP1 rows) and the 27 S2 `ci` fields stay GAP.
- **IRP-GAP5.** S2 numeric hit/excess for a TESTED cell would need window returns. v1.1 graded P04 TUNE rows are RETIRED-CONTAMINATED with excess null; P05/P06 have no committed episodes. There is no TESTED binomial to recompute.

## What this does NOT prove

- the inputs are vintage-unpinned / BLOCKED-AS-EVIDENCE as the result labels say;
- this is a reproduction of registered hit/return statistics, not probabilistic forecast support;
- nothing is registered;
- A29 stays PARTIAL under the R1 gate.

The comparison does not speak to causal news impact (A24). Families that cannot be estimated from the committed files abstain with a named IRP-GAP reason; they are not filled with 50/50 (A25). Mirror-trick intervals, Wilson intervals, trial-ledger effective_n, membership sha256, and any rank/gate/size/signal/escalation/trade use are outside this reproduction.
