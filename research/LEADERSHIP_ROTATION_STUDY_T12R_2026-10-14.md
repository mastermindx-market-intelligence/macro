# Leadership Rotation — Study T12R (H1 re-size under prereg V2: Option A null + two-part size rule)

**Headline (P0):** **SIZED.** Under V2 §2 Option A and the V2 §3 two-part rule, all 42 δ = 0 rows (6 (hypothesis, group) rows + `family_any` × cells 0, 1, 2, 3, 4, 48) pass both parts at M = 400 each; no violation, no missing cell, no `SIZE_NOT_EXECUTABLE`. The largest row is cell 1 `broadening_proxy/H3` = 3/400 (point 0.0075, Wilson 95 % lower 0.0026; α = 0.025, envelope 0.0406). H1 passes 0 of 4,800 (sim, group) evaluations; across the six cells H3 accounts for all 8 row passes and `family_any` totals 8/2,400. The V2 §2 falsifier did not fire, so Option A is **not rejected** and no V3 is triggered by size. Being SIZED is necessary, not sufficient: H1's condition (a) is degenerate by construction (see the notes), and H1 power is reported in T13R. Partition executed: **P0 (synthetic) only**. Development harness — no verdict authority over markets.

This record is the prereg V2 §3 re-size record. It does **not** edit or supersede the T12 record (`research/LEADERSHIP_ROTATION_STUDY_T12_2026-10-14.md`), which stays the record of the V1 result (bootstrap null, single-part rule: MIS-SIZED). T12R re-sizes the repaired protocol: V2 §2 Option A replaces only the H1 null; V2 §3 replaces the size rule; arms A0–B7/C3, margins, α = 0.025 and Holm m = 6 are unchanged.

## Protocol under test

- Prereg V1 `research/LEADERSHIP_ROTATION_PREREG_V1.md`, blob `9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe` (unchanged).
- Prereg V2 `research/LEADERSHIP_ROTATION_PREREG_V2.md`, blob `1fcd151cfc4cdeb321789feb50d3fbb127cce056` (unchanged): §2 Option A H1 null; §3 cells, M ≥ 400, two-part rule, per-arm metrics; §6 C2 strata; §8 items 10–13.
- Prereg V2.1 `research/LEADERSHIP_ROTATION_PREREG_V2_1.md`, blob `8f48509b65c70f7f3786402cba9b21940a907e83` (new in this PR): §5 F1/F2 ruling — M is the row's OWN count of OK sims; M < 400 → `SIZE_NOT_EXECUTABLE`; zero OK sims → `SIZE_NOT_EXECUTABLE`; §6 Option A precision clauses.
- Size rule (V2 §3.3), per (hypothesis, group) row and per `family_any`: SIZED only if BOTH (i) the Wilson 95 % lower bound of the pass rate ≤ α = 0.025, AND (ii) the point pass rate ≤ α + 2·√(α(1 − α)/M) (0.0406 at M = 400). At M = 400 the largest SIZED count is 16/400 (0.0400); 17/400 (0.0425) fails part (ii).
- **`SIZE_EXCEEDS_POINT` is retired** (V2 §3.3; §8 item 11): a point exceedance is now gated by part (ii), not printed as an advisory label. The harness no longer emits that label (`scripts/leadership_rotation_p0.py` `SIZE_RULE = "V2_SEC3_TWO_PART"`).

## Exemplars and current regime

PENDING — P1 not executed. `scripts/leadership_rotation_run.py p1` now refuses before any data load unless (1) V1 is landed (`assert_protocol_landed`), (2) V2.1 is landed (`assert_prereg_landed`), and (3) the committed size-gate artifact `research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.size_gate.json` (this record's companion, below) carries `sized: true` under rule `V2_SEC3_TWO_PART`, cells 0, 1, 2, 3, 4 and 48 with 7 rows each, every row M ≥ 400, null `V2_OPTION_A` with K ≥ 1000, and harness blobs equal to the reading head's. Once P1 runs, October 2026, July 2026 and the last 63 sessions are DEVELOPMENT exemplars only (V1 §12).

## Honest-N

H1 honest-N is the realised onset-cluster count of the read (V1 §8; Table 4 `median_honest_n`). Under Option A the null is matched to that N (V2 §2; matched N per group in §8 item 10 below). Prereg rule: ≥ 20 clusters (episodes, not fires or dates).

## In-sample status

2026-10-14 is not in any executed sample. P0 is synthetic. P1 ends 2026-10-12 and was not executed. P3 begins after the protocol lands on `origin/main`.

## Who is missing

XLRE (from 2015) and XLC (from 2018) are not in the cohort (V1 §2). `xlp_vs_smh` is excluded from P2. Constituent overlap is UNMEASURED historically; V2 §5 R13 now governs H3 overlap. Synthetic P0 pairs do not share physical legs. Survivorship: ETF pairs; composition drift not modelled. The Option A null is parametric (generator G1 at δ = 0): it matches σ, ρ and N but not the read's higher moments, regime structure or missingness pattern — a disclosed limitation (V2 §2), not a property this record can test.

## Uncertainty

Wilson 95 % intervals on the P0 δ = 0 pass rates are simulation uncertainty only. H1 p-values: Option A, K = 1000 matched null paths per (sim, group), p = (1 + #{null ≥ observed}) / (1 + K) per condition, H1's Holm entry max(p_a, p_b); the smallest attainable H1 p is 1/1001 ≈ 0.0010. H2/H3 p-values are unchanged from V1: stationary block bootstrap, mean block 21, 2000 replicates, seed 20261014, paired across arms. Holm m = 6.

## §8 item 11 — size, both parts per row, M (V2 §3)

| cell | σ | ρ | N | row | passes / M | point | Wilson lower | envelope | (i) lower ≤ α | (ii) point ≤ envelope | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.70 | 0.500 | 20 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | defensive_sector/H3 | 1/400 | 0.003 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | broadening_proxy/H3 | 1/400 | 0.003 | 0.000 | 0.041 | yes | yes | SIZED |
| 0 | 0.70 | 0.500 | 20 | family_any | 2/400 | 0.005 | 0.001 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | defensive_sector/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | broadening_proxy/H3 | 3/400 | 0.007 | 0.003 | 0.041 | yes | yes | SIZED |
| 1 | 0.70 | 0.500 | 40 | family_any | 3/400 | 0.007 | 0.003 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | defensive_sector/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | broadening_proxy/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 2 | 0.70 | 0.500 | 80 | family_any | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | defensive_sector/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | broadening_proxy/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 3 | 0.70 | 0.800 | 20 | family_any | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | defensive_sector/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | broadening_proxy/H3 | 2/400 | 0.005 | 0.001 | 0.041 | yes | yes | SIZED |
| 4 | 0.70 | 0.800 | 40 | family_any | 2/400 | 0.005 | 0.001 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | defensive_sector/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | defensive_sector/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | defensive_sector/H3 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | broadening_proxy/H1 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | broadening_proxy/H2 | 0/400 | 0.000 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | broadening_proxy/H3 | 1/400 | 0.003 | 0.000 | 0.041 | yes | yes | SIZED |
| 48 | 1.40 | 0.500 | 20 | family_any | 1/400 | 0.003 | 0.000 | 0.041 | yes | yes | SIZED |
Size rule: prereg V2 §3 two-part rule (i) Wilson 95 % lower ≤ α AND (ii) point ≤ α + 2·√(α(1−α)/M). The former advisory label SIZE_EXCEEDS_POINT is retired (V2 §3.3); a point exceedance is now gated.
Size verdict: SIZED (prereg V2 §3: every δ = 0 row satisfies both parts at α = 0.025)

## §8 item 10 — Option A null for every H1 result (V2 §2)

Formation-window derivation (V2 §2; precision pinned in V2.1 §6 and in the `scripts/leadership_rotation_null.py` module docstring):

- σ̂ = median over the group's registered pairs of sd(daily ΔR) over the read's FORMATION window (ΔR over t ∈ (s0, end] with R_t and R_{t−1} finite; ddof = 1).
- ρ̂ = median of the within-group pairwise-complete Pearson correlations of daily ΔR, same window (≥ 2 pairs).
- Matched to G1's own parameters: σ_b = σ̂ rounded to the 0.0005 grid; ρ_gen = (ρ̂·σ_b² − MARKET_VAR)/(σ_b² − MARKET_VAR) with MARKET_VAR = 9e-6, clipped to [0, 0.95] and rounded to the 0.05 grid (G1's ρ is the idiosyncratic-factor correlation; ΔR also carries the common market term). σ_b² ≤ MARKET_VAR → NOT_EXECUTABLE (p = 1).
- N = the read's realised H1 honest-N cluster count; each null path is evaluated at e*_N, the first index at which its honest-N count reaches N (N_real ≥ N recorded). A null path that never reaches N within 96 formation years, and a NaN null statistic, count as ≥ observed (conservative).
- Seed = 20261014 + crc32("P0|<group>"); null path j draws from `SeedSequence(entropy=seed, spawn_key=(j,))`, j ∈ [0, K), standard normals in fixed 252-row chunks. P0 test sims draw from `SeedSequence([20261014, cell_id, k])` — independent of every null seed (V2 §3.2: no path is both reference and test).
- Null (1 − α) quantile of each condition statistic: `numpy.quantile(finite values, 0.975)` (linear).

Aggregate over the OK sims of each (cell, group) — medians and ranges across sims; every sim's full block (K, seed, matched, quantiles, p_a, p_b, p_h1, n_unreached, n_nan_a, n_nan_b, n_real_over_N, bank_key) is in the record files listed under Input identities:

| cell | group | sims | K | null status | seed key / crc32 | median σ̂ (gen → bank) | median ρ̂ (gen → bank) | median N (range) | T_a q0.975 median (range) | T_b q0.975 median (range) | median p_a / p_b / p_H1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.499 → 0.50 | 20 (20–26) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.489 / 0.731 |
| 0 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 22 (20–36) | 5.00 (5.00–5.00) | 0.599 (0.582–0.607) | 0.713 / 0.441 / 0.716 |
| 1 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 40 (40–49) | 5.00 (5.00–5.00) | 0.579 (0.571–0.579) | 0.718 / 0.484 / 0.718 |
| 1 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 46 (40–65) | 5.00 (5.00–5.00) | 0.572 (0.562–0.577) | 0.679 / 0.483 / 0.700 |
| 2 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 80 (80–88) | 5.00 (5.00–5.00) | 0.557 (0.557–0.560) | 0.695 / 0.482 / 0.708 |
| 2 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 93 (80–119) | 5.00 (5.00–5.00) | 0.552 (0.549–0.560) | 0.671 / 0.469 / 0.756 |
| 3 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.801 → 0.80 | 20 (20–29) | 5.00 (5.00–5.00) | 0.609 (0.593–0.609) | 0.710 / 0.490 / 0.724 |
| 3 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.800 → 0.80 | 22 (20–36) | 5.00 (5.00–5.00) | 0.598 (0.586–0.603) | 0.728 / 0.418 / 0.733 |
| 4 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.800 → 0.80 | 40 (40–50) | 5.00 (5.00–5.00) | 0.582 (0.576–0.582) | 0.686 / 0.468 / 0.722 |
| 4 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.800 → 0.80 | 44 (40–62) | 5.00 (5.00–5.00) | 0.579 (0.564–0.582) | 0.698 / 0.407 / 0.704 |
| 48 | broadening_proxy | 400 | 1000 | OK: 400 | P0\|broadening_proxy / 3923611080 | 0.0140 → 0.0140 | 0.501 → 0.50 | 20 (20–28) | 5.00 (5.00–5.00) | 0.652 (0.642–0.655) | 0.640 / 0.508 / 0.794 |
| 48 | defensive_sector | 400 | 1000 | OK: 400 | P0\|defensive_sector / 1109301814 | 0.0140 → 0.0140 | 0.499 → 0.50 | 22 (20–39) | 5.00 (5.00–5.00) | 0.645 (0.625–0.653) | 0.648 / 0.506 / 0.745 |

## H1 intersection–union components

| cell | group | cond_a_true/n_ok | cond_b_true/n_ok | median delay_reduction | median burden_cut_b |
|---|---|---|---|---|---|
| 0 | defensive_sector | 284/400 | 400/400 | 5.000 | 0.509 |
| 0 | broadening_proxy | 302/400 | 400/400 | 5.000 | 0.505 |
| 1 | defensive_sector | 293/400 | 400/400 | 5.000 | 0.504 |
| 1 | broadening_proxy | 288/400 | 400/400 | 5.000 | 0.509 |
| 2 | defensive_sector | 274/400 | 400/400 | 5.000 | 0.506 |
| 2 | broadening_proxy | 279/400 | 400/400 | 5.000 | 0.507 |
| 3 | defensive_sector | 278/400 | 400/400 | 5.000 | 0.509 |
| 3 | broadening_proxy | 295/400 | 400/400 | 5.000 | 0.507 |
| 4 | defensive_sector | 276/400 | 400/400 | 5.000 | 0.510 |
| 4 | broadening_proxy | 271/400 | 400/400 | 5.000 | 0.509 |
| 48 | defensive_sector | 262/400 | 400/400 | 5.000 | 0.537 |
| 48 | broadening_proxy | 252/400 | 399/400 | 5.000 | 0.536 |

## Calibration (δ = 0)

| cell | row | median_raw_p | share_raw_p_lt_alpha | share_holm_p_lt_alpha | median_honest_n | median_window_years |
|---|---|---|---|---|---|---|
| 0 | defensive_sector/H1 | 0.716 | 0.000 | 0.000 | 22.500 | 11.321 |
| 0 | defensive_sector/H2 | 0.697 | 0.000 | 0.000 | 21.000 | 3.532 |
| 0 | defensive_sector/H3 | 0.521 | 0.007 | 0.003 | 21.000 | 3.532 |
| 0 | broadening_proxy/H1 | 0.731 | 0.000 | 0.000 | 20.000 | 11.321 |
| 0 | broadening_proxy/H2 | 0.690 | 0.003 | 0.000 | 20.000 | 3.532 |
| 0 | broadening_proxy/H3 | 0.522 | 0.013 | 0.003 | 20.000 | 3.532 |
| 1 | defensive_sector/H1 | 0.700 | 0.000 | 0.000 | 46.000 | 23.097 |
| 1 | defensive_sector/H2 | 0.694 | 0.000 | 0.000 | 44.000 | 7.044 |
| 1 | defensive_sector/H3 | 0.510 | 0.000 | 0.000 | 44.000 | 7.044 |
| 1 | broadening_proxy/H1 | 0.718 | 0.000 | 0.000 | 40.000 | 23.097 |
| 1 | broadening_proxy/H2 | 0.650 | 0.005 | 0.000 | 40.000 | 7.044 |
| 1 | broadening_proxy/H3 | 0.512 | 0.022 | 0.007 | 40.000 | 7.044 |
| 2 | defensive_sector/H1 | 0.756 | 0.000 | 0.000 | 93.000 | 46.647 |
| 2 | defensive_sector/H2 | 0.643 | 0.005 | 0.000 | 87.000 | 13.988 |
| 2 | defensive_sector/H3 | 0.512 | 0.007 | 0.000 | 87.000 | 13.988 |
| 2 | broadening_proxy/H1 | 0.708 | 0.000 | 0.000 | 80.000 | 46.647 |
| 2 | broadening_proxy/H2 | 0.677 | 0.007 | 0.000 | 80.000 | 13.988 |
| 2 | broadening_proxy/H3 | 0.503 | 0.015 | 0.000 | 80.000 | 13.988 |
| 3 | defensive_sector/H1 | 0.733 | 0.000 | 0.000 | 22.000 | 14.200 |
| 3 | defensive_sector/H2 | 0.688 | 0.005 | 0.000 | 20.500 | 4.260 |
| 3 | defensive_sector/H3 | 0.531 | 0.005 | 0.000 | 20.500 | 4.260 |
| 3 | broadening_proxy/H1 | 0.724 | 0.000 | 0.000 | 20.000 | 14.200 |
| 3 | broadening_proxy/H2 | 0.684 | 0.003 | 0.000 | 20.000 | 4.260 |
| 3 | broadening_proxy/H3 | 0.524 | 0.013 | 0.000 | 20.000 | 4.260 |
| 4 | defensive_sector/H1 | 0.704 | 0.000 | 0.000 | 44.000 | 28.931 |
| 4 | defensive_sector/H2 | 0.670 | 0.000 | 0.000 | 42.000 | 8.425 |
| 4 | defensive_sector/H3 | 0.514 | 0.013 | 0.000 | 42.000 | 8.425 |
| 4 | broadening_proxy/H1 | 0.722 | 0.000 | 0.000 | 40.000 | 28.931 |
| 4 | broadening_proxy/H2 | 0.645 | 0.007 | 0.000 | 40.000 | 8.425 |
| 4 | broadening_proxy/H3 | 0.502 | 0.015 | 0.005 | 40.000 | 8.425 |
| 48 | defensive_sector/H1 | 0.745 | 0.000 | 0.000 | 22.000 | 7.161 |
| 48 | defensive_sector/H2 | 0.692 | 0.000 | 0.000 | 21.000 | 3.337 |
| 48 | defensive_sector/H3 | 0.526 | 0.010 | 0.000 | 21.000 | 3.337 |
| 48 | broadening_proxy/H1 | 0.794 | 0.000 | 0.000 | 20.000 | 7.161 |
| 48 | broadening_proxy/H2 | 0.710 | 0.005 | 0.000 | 20.000 | 3.337 |
| 48 | broadening_proxy/H3 | 0.530 | 0.013 | 0.003 | 20.000 | 3.337 |

## §8 item 11 — per-arm metrics (V2 §3.4)

| cell | σ | δ | ρ | N | group | A0 raw burden | A0 burden | A1 burden | A1 median delay | A1 detection | A2 median delay | sims |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.007 | 0.000 | 0.500 | 20 | defensive_sector | 11.078 | 5.190 | 2.550 | 18.000 | 0.946 | 22.000 | 400 |
| 0 | 0.007 | 0.000 | 0.500 | 20 | broadening_proxy | 11.044 | 5.188 | 2.565 | 17.000 | 0.957 | 22.000 | 400 |
| 1 | 0.007 | 0.000 | 0.500 | 40 | defensive_sector | 11.057 | 5.187 | 2.574 | 18.000 | 0.942 | 22.000 | 400 |
| 1 | 0.007 | 0.000 | 0.500 | 40 | broadening_proxy | 11.039 | 5.191 | 2.540 | 18.000 | 0.940 | 22.000 | 400 |
| 2 | 0.007 | 0.000 | 0.500 | 80 | defensive_sector | 11.048 | 5.189 | 2.558 | 18.000 | 0.942 | 22.000 | 400 |
| 2 | 0.007 | 0.000 | 0.500 | 80 | broadening_proxy | 11.031 | 5.169 | 2.550 | 18.000 | 0.937 | 22.000 | 400 |
| 3 | 0.007 | 0.000 | 0.800 | 20 | defensive_sector | 11.054 | 5.182 | 2.537 | 18.000 | 0.953 | 22.000 | 400 |
| 3 | 0.007 | 0.000 | 0.800 | 20 | broadening_proxy | 11.020 | 5.166 | 2.551 | 18.000 | 0.964 | 22.000 | 400 |
| 4 | 0.007 | 0.000 | 0.800 | 40 | defensive_sector | 11.051 | 5.191 | 2.559 | 18.000 | 0.954 | 22.000 | 400 |
| 4 | 0.007 | 0.000 | 0.800 | 40 | broadening_proxy | 11.043 | 5.184 | 2.543 | 18.000 | 0.950 | 22.000 | 400 |
| 48 | 0.014 | 0.000 | 0.500 | 20 | defensive_sector | 10.644 | 4.883 | 2.248 | 18.000 | 0.908 | 23.000 | 400 |
| 48 | 0.014 | 0.000 | 0.500 | 20 | broadening_proxy | 10.610 | 4.833 | 2.240 | 18.000 | 0.900 | 23.000 | 400 |
Medians over OK sims. "A0 raw" = A0 fires before the 5-quiet-session suppression, through the same window filter, merge and classifier as A0 ("suppressed"); burden = REPEATED + LATE + FALSE_START per measured pair-year.

## §8 item 13 — C2 direction strata (V2 §6)

Prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed Trend-Persistence-era study also called 'C2', which stays closed. Points only, no p-values; SOURCE_LIMITED where the stratum's clustered n < 5.
| cell | row | stratum | sims | status counts | median n | median point(s) |
|---|---|---|---|---|---|---|
| 0 | defensive_sector/H1 | both_up | 400 | COMPUTED: 259, SOURCE_LIMITED: 141 | 5.000 | 5.000 / 0.788 |
| 0 | defensive_sector/H1 | both_down | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 11.000 | 5.000 / 0.224 |
| 0 | defensive_sector/H1 | mixed | 400 | COMPUTED: 387, SOURCE_LIMITED: 13 | 8.000 | 5.000 / 0.167 |
| 0 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 0 | defensive_sector/H2 | both_up | 400 | COMPUTED: 359, SOURCE_LIMITED: 41 | 7.000 | -0.003 |
| 0 | defensive_sector/H2 | both_down | 400 | COMPUTED: 400 | 13.000 | -0.003 |
| 0 | defensive_sector/H2 | mixed | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 10.000 | -0.004 |
| 0 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 0 | defensive_sector/H3 | both_up | 400 | COMPUTED: 359, SOURCE_LIMITED: 41 | 7.000 | -0.001 |
| 0 | defensive_sector/H3 | both_down | 400 | COMPUTED: 400 | 13.000 | 0.000 |
| 0 | defensive_sector/H3 | mixed | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 10.000 | -0.001 |
| 0 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 0 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 212, NOT_EXECUTABLE: 1, SOURCE_LIMITED: 187 | 5.000 | 5.000 / 0.793 |
| 0 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 397, SOURCE_LIMITED: 3 | 10.000 | 5.000 / 0.220 |
| 0 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 319, SOURCE_LIMITED: 81 | 6.000 | 4.000 / 0.179 |
| 0 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 0 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 313, SOURCE_LIMITED: 87 | 6.000 | -0.003 |
| 0 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 400 | 11.000 | -0.003 |
| 0 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 386, SOURCE_LIMITED: 14 | 8.000 | -0.004 |
| 0 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 0 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 313, SOURCE_LIMITED: 87 | 6.000 | -0.002 |
| 0 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 400 | 11.000 | -0.000 |
| 0 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 386, SOURCE_LIMITED: 14 | 8.000 | 0.001 |
| 0 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 1 | defensive_sector/H1 | both_up | 400 | COMPUTED: 396, SOURCE_LIMITED: 4 | 12.000 | 5.000 / 0.788 |
| 1 | defensive_sector/H1 | both_down | 400 | COMPUTED: 400 | 22.500 | 5.000 / 0.223 |
| 1 | defensive_sector/H1 | mixed | 400 | COMPUTED: 400 | 16.000 | 4.000 / 0.177 |
| 1 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 1 | defensive_sector/H2 | both_up | 400 | COMPUTED: 400 | 15.000 | -0.003 |
| 1 | defensive_sector/H2 | both_down | 400 | COMPUTED: 400 | 26.000 | -0.002 |
| 1 | defensive_sector/H2 | mixed | 400 | COMPUTED: 400 | 21.000 | -0.003 |
| 1 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 1 | defensive_sector/H3 | both_up | 400 | COMPUTED: 400 | 15.000 | 0.000 |
| 1 | defensive_sector/H3 | both_down | 400 | COMPUTED: 400 | 26.000 | 0.000 |
| 1 | defensive_sector/H3 | mixed | 400 | COMPUTED: 400 | 21.000 | -0.001 |
| 1 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 1 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 384, SOURCE_LIMITED: 16 | 9.000 | 5.000 / 0.788 |
| 1 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 400 | 19.000 | 5.000 / 0.218 |
| 1 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 400 | 13.000 | 4.000 / 0.197 |
| 1 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 1 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 12.000 | -0.002 |
| 1 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 400 | 23.000 | -0.002 |
| 1 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 400 | 17.000 | -0.002 |
| 1 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 1 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 12.000 | 0.000 |
| 1 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 400 | 23.000 | -0.000 |
| 1 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 400 | 17.000 | 0.000 |
| 1 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 2 | defensive_sector/H1 | both_up | 400 | COMPUTED: 400 | 23.000 | 6.000 / 0.791 |
| 2 | defensive_sector/H1 | both_down | 400 | COMPUTED: 400 | 46.000 | 5.000 / 0.227 |
| 2 | defensive_sector/H1 | mixed | 400 | COMPUTED: 400 | 32.000 | 4.000 / 0.170 |
| 2 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 2 | defensive_sector/H2 | both_up | 400 | COMPUTED: 400 | 30.000 | -0.001 |
| 2 | defensive_sector/H2 | both_down | 400 | COMPUTED: 400 | 51.000 | -0.001 |
| 2 | defensive_sector/H2 | mixed | 400 | COMPUTED: 400 | 41.000 | -0.002 |
| 2 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 2 | defensive_sector/H3 | both_up | 400 | COMPUTED: 400 | 30.000 | -0.001 |
| 2 | defensive_sector/H3 | both_down | 400 | COMPUTED: 400 | 51.000 | -0.000 |
| 2 | defensive_sector/H3 | mixed | 400 | COMPUTED: 400 | 41.000 | -0.001 |
| 2 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 2 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 18.000 | 5.000 / 0.787 |
| 2 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 400 | 39.000 | 5.000 / 0.228 |
| 2 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 400 | 26.000 | 4.000 / 0.170 |
| 2 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 2 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 400 | 24.000 | -0.001 |
| 2 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 400 | 45.000 | -0.001 |
| 2 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 400 | 33.000 | -0.003 |
| 2 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 2 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 400 | 24.000 | -0.000 |
| 2 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 400 | 45.000 | 0.000 |
| 2 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 400 | 33.000 | 0.000 |
| 2 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 3 | defensive_sector/H1 | both_up | 400 | COMPUTED: 310, SOURCE_LIMITED: 90 | 6.000 | 5.000 / 0.787 |
| 3 | defensive_sector/H1 | both_down | 400 | COMPUTED: 400 | 11.000 | 5.000 / 0.222 |
| 3 | defensive_sector/H1 | mixed | 400 | COMPUTED: 391, SOURCE_LIMITED: 9 | 9.000 | 4.000 / 0.209 |
| 3 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 3 | defensive_sector/H2 | both_up | 400 | COMPUTED: 375, SOURCE_LIMITED: 25 | 8.000 | -0.003 |
| 3 | defensive_sector/H2 | both_down | 400 | COMPUTED: 400 | 14.000 | -0.003 |
| 3 | defensive_sector/H2 | mixed | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 11.000 | -0.005 |
| 3 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 3 | defensive_sector/H3 | both_up | 400 | COMPUTED: 375, SOURCE_LIMITED: 25 | 8.000 | -0.000 |
| 3 | defensive_sector/H3 | both_down | 400 | COMPUTED: 400 | 14.000 | -0.001 |
| 3 | defensive_sector/H3 | mixed | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 11.000 | -0.000 |
| 3 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 3 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 256, NOT_EXECUTABLE: 1, SOURCE_LIMITED: 143 | 5.000 | 5.000 / 0.786 |
| 3 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.224 |
| 3 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 364, SOURCE_LIMITED: 36 | 7.000 | 5.000 / 0.185 |
| 3 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 3 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 329, SOURCE_LIMITED: 71 | 7.000 | -0.004 |
| 3 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 400 | 12.000 | -0.003 |
| 3 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 393, SOURCE_LIMITED: 7 | 9.000 | -0.005 |
| 3 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 3 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 329, SOURCE_LIMITED: 71 | 7.000 | -0.001 |
| 3 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 400 | 12.000 | -0.000 |
| 3 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 393, SOURCE_LIMITED: 7 | 9.000 | 0.001 |
| 3 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 4 | defensive_sector/H1 | both_up | 400 | COMPUTED: 398, SOURCE_LIMITED: 2 | 12.000 | 5.000 / 0.791 |
| 4 | defensive_sector/H1 | both_down | 400 | COMPUTED: 400 | 24.000 | 5.000 / 0.223 |
| 4 | defensive_sector/H1 | mixed | 400 | COMPUTED: 400 | 17.000 | 4.000 / 0.188 |
| 4 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 4 | defensive_sector/H2 | both_up | 400 | COMPUTED: 400 | 15.000 | -0.002 |
| 4 | defensive_sector/H2 | both_down | 400 | COMPUTED: 400 | 27.000 | -0.002 |
| 4 | defensive_sector/H2 | mixed | 400 | COMPUTED: 400 | 22.000 | -0.003 |
| 4 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 4 | defensive_sector/H3 | both_up | 400 | COMPUTED: 400 | 15.000 | -0.000 |
| 4 | defensive_sector/H3 | both_down | 400 | COMPUTED: 400 | 27.000 | -0.000 |
| 4 | defensive_sector/H3 | mixed | 400 | COMPUTED: 400 | 22.000 | -0.000 |
| 4 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 4 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 397, SOURCE_LIMITED: 3 | 10.000 | 5.000 / 0.788 |
| 4 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 400 | 20.000 | 5.000 / 0.224 |
| 4 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 400 | 15.000 | 4.000 / 0.185 |
| 4 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 4 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 13.000 | -0.002 |
| 4 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 400 | 25.000 | -0.002 |
| 4 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 400 | 18.000 | -0.003 |
| 4 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 4 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 399, SOURCE_LIMITED: 1 | 13.000 | 0.000 |
| 4 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 400 | 25.000 | -0.000 |
| 4 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 400 | 18.000 | 0.000 |
| 4 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 48 | defensive_sector/H1 | both_up | 400 | COMPUTED: 206, SOURCE_LIMITED: 194 | 5.000 | 5.000 / 0.762 |
| 48 | defensive_sector/H1 | both_down | 400 | COMPUTED: 293, SOURCE_LIMITED: 107 | 6.000 | 5.000 / 0.538 |
| 48 | defensive_sector/H1 | mixed | 400 | COMPUTED: 400 | 13.000 | 4.000 / 0.269 |
| 48 | defensive_sector/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 48 | defensive_sector/H2 | both_up | 400 | COMPUTED: 312, SOURCE_LIMITED: 88 | 6.000 | -0.007 |
| 48 | defensive_sector/H2 | both_down | 400 | COMPUTED: 360, SOURCE_LIMITED: 40 | 7.000 | -0.008 |
| 48 | defensive_sector/H2 | mixed | 400 | COMPUTED: 400 | 16.000 | -0.006 |
| 48 | defensive_sector/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 48 | defensive_sector/H3 | both_up | 400 | COMPUTED: 312, SOURCE_LIMITED: 88 | 6.000 | -0.001 |
| 48 | defensive_sector/H3 | both_down | 400 | COMPUTED: 360, SOURCE_LIMITED: 40 | 7.000 | -0.001 |
| 48 | defensive_sector/H3 | mixed | 400 | COMPUTED: 400 | 16.000 | -0.000 |
| 48 | defensive_sector/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 48 | broadening_proxy/H1 | both_up | 400 | COMPUTED: 149, SOURCE_LIMITED: 251 | 4.000 | 5.000 / 0.778 |
| 48 | broadening_proxy/H1 | both_down | 400 | COMPUTED: 228, SOURCE_LIMITED: 172 | 5.000 | 5.000 / 0.560 |
| 48 | broadening_proxy/H1 | mixed | 400 | COMPUTED: 398, SOURCE_LIMITED: 2 | 11.000 | 4.000 / 0.258 |
| 48 | broadening_proxy/H1 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — / — |
| 48 | broadening_proxy/H2 | both_up | 400 | COMPUTED: 254, SOURCE_LIMITED: 146 | 5.000 | -0.010 |
| 48 | broadening_proxy/H2 | both_down | 400 | COMPUTED: 319, SOURCE_LIMITED: 81 | 6.000 | -0.007 |
| 48 | broadening_proxy/H2 | mixed | 400 | COMPUTED: 400 | 14.000 | -0.008 |
| 48 | broadening_proxy/H2 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |
| 48 | broadening_proxy/H3 | both_up | 400 | COMPUTED: 254, SOURCE_LIMITED: 146 | 5.000 | -0.003 |
| 48 | broadening_proxy/H3 | both_down | 400 | COMPUTED: 318, NOT_EXECUTABLE: 1, SOURCE_LIMITED: 81 | 6.000 | -0.000 |
| 48 | broadening_proxy/H3 | mixed | 400 | COMPUTED: 400 | 14.000 | -0.000 |
| 48 | broadening_proxy/H3 | unmeasured | 400 | UNMEASURED: 400 | 0.000 | — |

## Interpretation notes (T12R)

1. **The size reading.** Each Table 1 row shows passes / M, the point rate, the Wilson 95 % lower bound, the part (ii) envelope α + 2·√(α(1 − α)/M) = 0.0406 at M = 400, and the result of each part. M is the row's own count of OK sims (V2.1 §5 F1), and it is 400 in all 42 rows. The tightest part (ii) margin is 0.0331 (0.0406 − 0.0075), and the largest Wilson lower bound is 0.0026, an order of magnitude below α. The re-size was run once, at a pre-set M = 400 with pre-set seeds, and pooled exactly as launched. Partial progress was looked at while the runs were in flight, but nothing was changed, re-run or selected as a result.
2. **What "SIZED" licenses.** It satisfies only the V2 §3 size half of R-H1-4. It is **not** a P1 read and not an H1/H2/H3 result. R-H1-4 (V2 §3.6) also requires this record to be on `origin/main`. `run_p1` additionally refuses unless V1 and V2.1 are landed **and** the companion artifact (below) carries `sized: true` with harness blobs equal to the reading head's. Any later edit to a harness module therefore needs a new size artifact before P1. Nothing in this record is a promotion claim.
3. **H1 condition (a) is structurally degenerate. This is a finding and is reported, not repaired: arms A0–B7/C3 are frozen.** T_a is the A2 median confirmation delay minus the A1 median delay, which equals `iut.delay_reduction`. Under V1 ruling R5, A2 ≡ A1 + 5 sessions, so T_a is about 5 on every path, observed and null alike. In the table below the null 0.975-quantile of T_a is exactly 5.0 in all 4,800 (sim, group) evaluations. Measured p_a by observed T_a over those 4,800 evaluations: T_a = 5 (3,326 evaluations) gives median 0.695 (range 0.585–0.748); T_a ≤ 4 (1,445) gives ≥ 0.915; T_a = 6 (29) gives 0.003–0.020. None of the 29 T_a = 6 evaluations passed H1, because the intersection–union p is max(p_a, p_b) and p_b stayed near 0.48. Because H1's Holm entry is max(p_a, p_b), H1 is conservative at δ = 0 (0 passes). The same structure predicts H1 power near 0 at any planted δ. T13R tests that prediction instead of assuming it. Table 3's margin counts show the other side of the same fact: the H1 *margins* are met by construction at δ = 0 (cond_b 4,799/4,800; cond_a 3,354/4,800), so H1's size rests entirely on the Option A significance step. Table 3 counts are margin checks only, not significance.

| cell | (cell, group) rows | observed T_a (value: count) | null T_a q975 (value: count) | median p_a | H1 PASS (margin AND p_H1 < α) | of which T_a ≥ 6 |
|---|---|---|---|---|---|---|
| 0 | 800 | 2.0: 6, 3.0: 26, 4.0: 182, 5.0: 572, 6.0: 14 | 5.0: 800 | 0.714 | 0 | 0 |
| 1 | 800 | 3.0: 10, 4.0: 209, 5.0: 578, 6.0: 3 | 5.0: 800 | 0.718 | 0 | 0 |
| 2 | 800 | 3.0: 2, 4.0: 245, 5.0: 553 | 5.0: 800 | 0.695 | 0 | 0 |
| 3 | 800 | 2.0: 3, 3.0: 34, 4.0: 190, 5.0: 567, 6.0: 6 | 5.0: 800 | 0.719 | 0 | 0 |
| 4 | 800 | 3.0: 10, 4.0: 243, 5.0: 544, 6.0: 3 | 5.0: 800 | 0.686 | 0 | 0 |
| 48 | 800 | 1.0: 1, 2.0: 11, 3.0: 50, 4.0: 223, 5.0: 512, 6.0: 3 | 5.0: 800 | 0.643 | 0 | 0 |

All cells: 4800 (sim, group) rows; H1 PASS in 0; of those, observed T_a ≥ 6 in 0.

4. **The Option A null was matched as specified.** The formation-window estimates are on target: median σ̂ is 0.0070 (0.0140 in cell 48), and median ρ̂ is within 0.002 of the generator's 0.5 or 0.8. They map to bank parameters equal to the generator's on the 0.0005 σ and 0.05 ρ grids. The bank N is the read's realised honest-N, and every one of the 4,800 null blocks has status OK with K = 1000. At σ = 0.007 the T_b (burden-cut) quantile falls with N, from about 0.61 at N = 20 to about 0.55 at N = 80, as expected from a less noisy median.
5. **§8 item 12 (power curves) does not apply to a size record.** The G1 and G2 power curves and the per-hypothesis disposition are in `research/LEADERSHIP_ROTATION_STUDY_T13R_2026-10-14.md`.
6. **Units.** Table 1 and the null table print σ as % per session (0.70 = 0.007). Table 5 and the artifact print the raw fraction.
7. **The null bank is shared within a group.** The V2 §2 seed, 20261014 + crc32("P0|<group>"), is the same for every cell and every sim of a group. So the K = 1000 null normals form one common bank per group, re-scaled to each read's matched σ/ρ/N. Only the test paths, `SeedSequence([20261014, cell_id, k])`, are independent across sims. The 400 sims therefore estimate size *conditional on that bank draw*: Monte Carlo error in the null quantiles is common to all sims rather than averaged over. This is the registered design (V2 §2 pins the seed), disclosed here as a limitation of what M = 400 measures. The Wilson intervals cover test-path variation only.

## Size-gate artifact

- Path: `research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.size_gate.json` (schema `leadership_rotation.size_gate.v1`), sha256 `747ab295c63a8fc16f30e34f1979d4f5da092e3b637ef3a9b155cd0431d439bb`, 19262 bytes.
- `sized`: **True**; rule `V2_SEC3_TWO_PART`; α = 0.025; `min_m` = 400; H1 null `V2_OPTION_A`, K = 1000.
- Required cells [0, 1, 2, 3, 4, 48]; missing cells []; violations 0; not-executable rows 0.
- Prereg blobs pinned: V1 `9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe`, V2 `1fcd151cfc4cdeb321789feb50d3fbb127cce056`, V2.1 `8f48509b65c70f7f3786402cba9b21940a907e83`.
- Harness: `engine/leadership_rotation_context.py` `762798dec815`, `scripts/leadership_rotation_episodes.py` `73a04da34c7b`, `scripts/leadership_rotation_inference.py` `1f377832625d`, `scripts/leadership_rotation_null.py` `84b685b14693`, `scripts/leadership_rotation_p0.py` `ab28c3aea9ca`, `scripts/leadership_rotation_run.py` `ffd3805988c0`, `scripts/leadership_rotation_study.py` `ba82a9950f23`
  - harness `head`: `b85c8979e8efce1ec2e5200dc686361fd45614a2`
- Inputs: 2400 records kept, 0 duplicates; files: `size_k0.jsonl` sha256 `aaa14e9f23d3c519`; `size_k100.jsonl` sha256 `27ec7fe9dc6f9644`; `size_k200.jsonl` sha256 `6830370213842c04`; `size_k300.jsonl` sha256 `7c12920609ded815`.
- Generated 2026-10-14T20:09:21Z by `scripts/leadership_rotation_p0.py size --min-m 400 --require-cells 0,1,2,3,4,48 --out research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.size_gate.json`.

| cell | σ | ρ | N | rows | M (min–max) | rows SIZED | flags |
|---|---|---|---|---|---|---|---|
| 0 | 0.007 | 0.50 | 20 | 7 | 400–400 | 7 | SIZED ×7 |
| 1 | 0.007 | 0.50 | 40 | 7 | 400–400 | 7 | SIZED ×7 |
| 2 | 0.007 | 0.50 | 80 | 7 | 400–400 | 7 | SIZED ×7 |
| 3 | 0.007 | 0.80 | 20 | 7 | 400–400 | 7 | SIZED ×7 |
| 4 | 0.007 | 0.80 | 40 | 7 | 400–400 | 7 | SIZED ×7 |
| 48 | 0.014 | 0.50 | 20 | 7 | 400–400 | 7 | SIZED ×7 |
- The artifact's `inputs.files[].path` values are the absolute scratch paths on the M2 at generation time. The files are identified by sha256, not by path, and are not committed (they are 2,400 records, ~600 lines per file). `run_p1` reads only `sized`, the rule, the cells/rows/M, the null method/K and the blobs — never the input paths.

## Input identities

| file | sha256 | lines | cells | k | status | head | start (UTC) | end (UTC) | secs | rc |
|---|---|---:|---|---|---|---|---|---|---:|---:|
| `size_k0.jsonl` | `aaa14e9f23d3c519903291e443338b31acd6a60486ef7e3f2d6aa73b2ddd8e1c` | 600 | 0,1,2,3,4,48 | 0–99 | OK:600 | `b85c8979e8ef` | 2026-10-14T18:37:08Z | 2026-10-14T20:07:32Z | 5424 | 0 |
| `size_k100.jsonl` | `27ec7fe9dc6f9644026147a75a686a605bc86abbd90df764725e4a87ed439533` | 600 | 0,1,2,3,4,48 | 100–199 | OK:600 | `b85c8979e8ef` | 2026-10-14T18:37:10Z | 2026-10-14T20:08:15Z | 5465 | 0 |
| `size_k200.jsonl` | `6830370213842c04eedd02f351f2f2c8bc256d03625a87de0fb960c536bb7088` | 600 | 0,1,2,3,4,48 | 200–299 | OK:600 | `b85c8979e8ef` | 2026-10-14T18:37:12Z | 2026-10-14T20:08:06Z | 5454 | 0 |
| `size_k300.jsonl` | `7c12920609ded815ee2a143eb4fcdbf2569f3e018abd186b5d41bddb0fee0ac6` | 600 | 0,1,2,3,4,48 | 300–399 | OK:600 | `b85c8979e8ef` | 2026-10-14T18:37:14Z | 2026-10-14T20:08:56Z | 5502 | 0 |

harness_id values across records: `0461f9c294ce4749f3cc98e2799b0e9765f179583334022caa2d26d4640920d7` ×2400

- Code head for every record: `b85c8979e8efce1ec2e5200dc686361fd45614a2` (branch `claude/lr-harness-repair-2026-10-14`). `harness_id` (sha256 over the HARNESS_MODULES blobs) is identical in all 2,400 records.
- Command per process (run from `scratch run_one.sh`): `python3 scripts/leadership_rotation_p0.py grid --cells 0,1,2,3,4,48 --sims-null 100 --sims-alt 100 --k-start <0|100|200|300> --workers 1 --null-k 1000 --out <file>`, run under nohup on host m2studio (24 CPUs; python 3.14.7, numpy 2.5.2, pandas 3.0.5). Four processes ran in parallel, within the ≤ 4 cap.
- Null bank: `LR_NULL_BANK_DIR` pointed at one scratch shard cache, shared by all four processes under fcntl locks. A shard's key is the sha256 of its full payload: method, partition, group, n_pairs, σ_b, ρ_b, K, block, seed, crc32, chunk rows, years, and `code_fingerprint()` of the null module. A cached shard can therefore only be reused for an identical computation under identical code, and the cache cannot change any value.
- Test-path seeds: `SeedSequence([20261014, cell_id, k])` for k ∈ [0, 400). Null seeds: 20261014 + crc32("P0|defensive_sector") = 20261014 + 1109301814; 20261014 + crc32("P0|broadening_proxy") = 20261014 + 3923611080.
- Pooling: the summary and size subcommands de-duplicate on (cell_id, k) and raise on a conflicting duplicate. 2,400 records were kept, with 0 duplicates and 0 partial records.
- Excluded, and never pooled or selected among: `probe_c0.jsonl`, a 4-sim smoke probe of cell 0 at the same head used to check the launcher. Earlier timing probes in this wave were also excluded.

## Look count

P1 looks: 0 (the look ledger `research/LEADERSHIP_ROTATION_LOOK_LEDGER.jsonl` is absent; `run_p1` appends one line per executed P1 look). P2 looks: 0. P3 looks: 0. P0 runs for this record: 4 processes (SIZE0–SIZE3), each covering cells 0, 1, 2, 3, 4, 48 × 100 sims, with k ranges [0, 100), [100, 200), [200, 300) and [300, 400). All ran at head `b85c8979`, all exited with rc = 0, and their wall times were 5,424 s, 5,465 s, 5,454 s and 5,502 s (2026-10-14 18:37Z → 20:08:56Z). Each process was launched once, with no reruns.

## Verdict

**SIZED (P0, development harness).** Every δ = 0 row satisfies both parts of the V2 §3 rule at M = 400 in all six required cells. The V2 §2 falsifier ("if any δ = 0 cell fails the two-part rule under Option A, Option A is REJECTED") **did not fire**: Option A stands and no `LEADERSHIP_ROTATION_PREREG_V3.md` is triggered by size. This record satisfies the size half of R-H1-4 only once it is on `origin/main`. It authorises no P1, P2 or P3 read by itself (see note 2). H1 is sized, but its condition (a) is degenerate by construction (note 3). Whether H1 has any power is T13R's question, and H1's power is reported there "for information" only (V2 §4.3).
