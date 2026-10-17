# Leadership Rotation — Study T11 (harness & mandatory controls)

Development-phase study record for the T11 harness lane: mandatory controls C1–C3 and the shared baseline set B1–B7. Partition executed: **P0 (synthetic) only**. Evidence class: DEVELOPMENT — no verdict authority on live markets.

## Exemplars and current regime

PENDING — P1 not executed (prereg §12 invalidator 6: prereg not yet on origin/main). Command once it lands: python3 scripts/leadership_rotation_run.py p1 --repo . --out <path>; the refusal guard runs before any data load.

Once P1 runs, the October 2026 and July 2026 rotation episodes and the last 63 sessions will be described only as DEVELOPMENT exemplars: they will show whether the harness prints C1 (B6 carry / zero-new-return placebo), C2 absolute-leg strata (`both_up` / `both_down` / `mixed`), C3 breadth level vs level+change (SOURCE_LIMITED, never confirmatory), and the full B1–B7 baseline table beside the challenger arms — without selecting pairs, horizons, or arms by past performance.

## Honest-N

P0 (δ = 0 cells only; median honest-N clusters per Table 4, prereg minimum ≥ 20 clusters — episodes, not fires or dates):

| cell | group / hypothesis | median_honest_n | median_window_years |
|---|---|---:|---:|
| 0 | defensive_sector / H1 | 22.000 | 11.317 |
| 0 | defensive_sector / H2 | 21.000 | 3.488 |
| 0 | defensive_sector / H3 | 21.000 | 3.488 |
| 0 | broadening_proxy / H1 | 20.000 | 11.317 |
| 0 | broadening_proxy / H2 | 20.000 | 3.488 |
| 0 | broadening_proxy / H3 | 20.000 | 3.488 |
| 1 | defensive_sector / H1 | 46.000 | 23.119 |
| 1 | defensive_sector / H2 | 44.000 | 7.026 |
| 1 | defensive_sector / H3 | 44.000 | 7.026 |
| 1 | broadening_proxy / H1 | 40.000 | 23.119 |
| 1 | broadening_proxy / H2 | 40.000 | 7.026 |
| 1 | broadening_proxy / H3 | 40.000 | 7.026 |
| 2 | all rows | — | — (cell 2: 0/1 sims ok; UNREACHED) |
| 3 | defensive_sector / H1 | 23.000 | 14.308 |
| 3 | defensive_sector / H2 | 20.000 | 4.290 |
| 3 | defensive_sector / H3 | 20.000 | 4.290 |
| 3 | broadening_proxy / H1 | 20.000 | 14.308 |
| 3 | broadening_proxy / H2 | 20.000 | 4.290 |
| 3 | broadening_proxy / H3 | 20.000 | 4.290 |
| 4 | defensive_sector / H1 | 43.000 | 28.863 |
| 4 | defensive_sector / H2 | 41.000 | 8.427 |
| 4 | defensive_sector / H3 | 41.000 | 8.427 |
| 4 | broadening_proxy / H1 | 40.000 | 28.863 |
| 4 | broadening_proxy / H2 | 40.000 | 8.427 |
| 4 | broadening_proxy / H3 | 40.000 | 8.427 |
| 48 | defensive_sector / H1 | 22.000 | 7.194 |
| 48 | defensive_sector / H2 | 22.000 | 3.310 |
| 48 | defensive_sector / H3 | 22.000 | 3.310 |
| 48 | broadening_proxy / H1 | 20.000 | 7.194 |
| 48 | broadening_proxy / H2 | 20.000 | 3.310 |
| 48 | broadening_proxy / H3 | 20.000 | 3.310 |

Honest-N for δ > 0 cells is not tabulated in the P0 summary; it is not estimated here.

## In-sample status

Record date 2026-10-14 is not inside any executed sample. P0 is synthetic. P1 ends 2026-10-12 and was not executed. P3 formation begins only after the prereg merge commit is an ancestor of `origin/main`.

## Who is missing

XLRE (from 2015) and XLC (from 2018) are not in the cohort (prereg §2). `xlp_vs_smh` is excluded from P2. Constituent overlap is UNMEASURED historically (H3 / A37). Synthetic P0 pairs do not physically share legs, so the R13 shared-leg sensitivity is not exercised by P0. Survivorship: ETF pairs only; no delisting in the registered cohort, but sector ETF composition drift is not modelled.

## Uncertainty

Stationary block bootstrap, mean block length 21 sessions, 2000 replicates, seed 20261014, paired across arms; clusters resampled whole (±10 sessions, single linkage within group, prereg §8 / R10). Holm family size m = 6. Wilson 95 % intervals on P0 δ = 0 pass rates quantify simulation uncertainty only, not market uncertainty.

## All baselines

Harness arms reported for T11 (P0 grid carries hypothesis verdicts only; per-arm fields below unless noted):

| arm | P0 |
|---|---|
| B1 unconditional drift | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B2 static 63-session trend crossing | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B3 receiver vs SPY leg momentum | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B4 past-only beta residual target | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B5 fixed multihorizon sign table | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B6 carry / zero-new-return placebo (C1; carry-entry share) | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B7 abstention | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| C2 absolute-leg strata (`both_up` / `both_down` / `mixed` counts) | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| C3a breadth level / C3b level+change (SOURCE_LIMITED) | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |

## Nulls

### Size at δ = 0 (all three hypotheses, Table 1)

Size verdict: **NOT SIZED** (prereg §8: false-pass at δ = 0 must be ≤ α = 0.025).

| cell | σ (pts) | ρ | N | sims ok/unreached | defensive_sector/H1 | defensive_sector/H2 | defensive_sector/H3 | broadening_proxy/H1 | broadening_proxy/H2 | broadening_proxy/H3 | family_any |
|---|---:|---:|---:|---|---|---|---|---|---|---|---|
| 0 | 0.70 | 0.500 | 20 | 100/0 | 7/100 (0.070) | 0/100 (0.000) | 0/100 (0.000) | 2/100 (0.020) | 0/100 (0.000) | 0/100 (0.000) | 9/100 (0.090) |
| 1 | 0.70 | 0.500 | 40 | 100/0 | 9/100 (0.090) | 0/100 (0.000) | 0/100 (0.000) | 13/100 (0.130) | 0/100 (0.000) | 2/100 (0.020) | 22/100 (0.220) |
| 2 | 0.70 | 0.500 | 80 | 0/1 | 0/0 (—) | 0/0 (—) | 0/0 (—) | 0/0 (—) | 0/0 (—) | 0/0 (—) | 0/0 (—) |
| 3 | 0.70 | 0.800 | 20 | 42/0 | 0/42 (0.000) | 0/42 (0.000) | 0/42 (0.000) | 0/42 (0.000) | 0/42 (0.000) | 0/42 (0.000) | 0/42 (0.000) |
| 4 | 0.70 | 0.800 | 40 | 42/0 | 3/42 (0.071) | 0/42 (0.000) | 0/42 (0.000) | 3/42 (0.071) | 0/42 (0.000) | 0/42 (0.000) | 5/42 (0.119) |
| 48 | 1.40 | 0.500 | 20 | 79/0 | 1/79 (0.013) | 0/79 (0.000) | 0/79 (0.000) | 0/79 (0.000) | 0/79 (0.000) | 0/79 (0.000) | 1/79 (0.013) |

Located size bullets (Wilson 95 % lower bound vs α = 0.025):

- cell 0 (σ 0.70, ρ 0.500, N 20) defensive_sector/H1: 7/100 (0.070), Wilson 95 % lower 0.034 — **SIZE_VIOLATION**
- cell 0 (σ 0.70, ρ 0.500, N 20) family_any: 9/100 (0.090), Wilson 95 % lower 0.048 — **FAMILY_SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) defensive_sector/H1: 9/100 (0.090), Wilson 95 % lower 0.048 — **SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) broadening_proxy/H1: 13/100 (0.130), Wilson 95 % lower 0.078 — **SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) family_any: 22/100 (0.220), Wilson 95 % lower 0.150 — **FAMILY_SIZE_VIOLATION**
- cell 4 (σ 0.70, ρ 0.800, N 40) family_any: 5/42 (0.119), Wilson 95 % lower 0.052 — **FAMILY_SIZE_VIOLATION**
- cell 4 (σ 0.70, ρ 0.800, N 40) defensive_sector/H1: 3/42 (0.071), Wilson 95 % lower 0.025 — **SIZE_EXCEEDS_POINT**
- cell 4 (σ 0.70, ρ 0.800, N 40) broadening_proxy/H1: 3/42 (0.071), Wilson 95 % lower 0.025 — **SIZE_EXCEEDS_POINT**

H2 and H3 show no SIZE_VIOLATION flags at δ = 0 in the cells run; that does not license a market claim. The H1 test is **MIS-SIZED** at δ = 0 under prereg §8; repair before any real-data read (see T12).

A δ = 0 pass rate above α means the verdict machinery fired on rotation-free paths too often — not evidence that rotation does not exist. Power at δ > 0 is summarised in Table 2 of the P0 packet; zero passes for H2/H3 are nulls of the generator, not falsification of continuation or migration.

### Interpretation notes (T11)

- N3 (T11 C3 / A0 quiet mask). A0's 5-session quiet run (ruling R4) counts only MEASURED non-positive days; an unmeasured day breaks the run. In P0 every leg is measured every day, so the missing-data branch of R4 is tested by unit tests, not by the grid.
- N4 (T11, T12, T13, T14 — coverage). The section 7 clause 3 gate counts SOURCE_INVALID and UNMEASURED pair-days in the denominator (ruling R2: neither is ever zero-filled or forward-filled). P0 has no missingness, so all-event coverage is 100 % by construction in every cell; the gate is exercised on real data only.
- N7 (T11, T12, T13, T14 — size rule). Prereg section 8: the false-pass rate at delta = 0 must be <= alpha = 0.025, else the machinery is repaired before any read. The grid flags SIZE_VIOLATION when the Wilson 95 % LOWER bound of the delta = 0 pass rate exceeds 0.025 (the excess is beyond simulation noise) and prints every cell whose POINT rate exceeds 0.025 as SIZE_EXCEEDS_POINT (excess not distinguishable from simulation noise at this sim count). Both are reported; neither is softened.
- N10 (T11, T12, T13, T14 — honest-N and UNREACHED). The prereg minimum honest-N is 20 clusters (episodes, not fires or dates). Cells whose target N could not be reached inside the simulator's maximum synthetic window are recorded UNREACHED and excluded from every rate (Table 1/2 "sims ok/unreached"); this hits mainly the N = 80 cells. The synthetic window lengths in Table 4 are properties of the synthetic generator and say nothing about how many real episodes the 2015–2026 history holds.
- N12 (T11 — the ten SYNTHETIC_FALSIFIERS controls). Prereg section 8 makes the ten controls (both-down pair; missing breadth; empty population; composition-only breadth; shared holdings; rolling carry; beta-only excess; relative units; delayed confirmation; valid zero score) part of P0. They run as `tests/test_leadership_rotation_contract.py::test_sf_synthetic_falsifiers_ten_controls` (10 parametrized cases, all passing; landed on main with the measured-product contract, PR #9240). They exercise the measurement contract (`engine/leadership_rotation_context.py`), not the P0 power grid, and they prove only the stated mathematical distinctions, never a market claim. The study harness adds its own carry test (ruling R12, B6) in `tests/test_leadership_rotation_study.py`.

## Input identities

- Prereg: `research/LEADERSHIP_ROTATION_PREREG_V1.md` frozen at commit `fafdaf094f7271bb09c2bf605f1fd4bcc6ad7ceb`, blob `9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe`, carried by PR #9251 (DRAFT; NOT an ancestor of origin/main when this record was written).
- Study branch: `claude/lr-t11-t14-science-2026-10-14` (PR #9293, DRAFT) at `e6c198eaf74f402cca76f5a7c89d767d2b6153bf`.
- Grid code: every record below was produced by `scripts/leadership_rotation_p0.py` at commit `984306b98138f57be53cd1d8bf511eafe64024a7`. Later commits on the study branch change no simulation or per-simulation extraction code: `fc07f8b6f095e0b618183d7688611fedfd5cae00` makes the size verdict fail closed and repairs the CLI; `a9089805b219c5441df40771e68b720fea3d4941` changes only the markdown rendering (the summary JSON is byte-identical before and after on these records).
- Seeds: numpy `SeedSequence([20261014, cell_id, k])` per simulation `k` of cell `cell_id`; bootstrap seed 20261014, 2000 replicates, stationary blocks of mean length 21.
- Record files (sha256 of the file bytes as aggregated):

| file | sha256 | host | cells | lines |
|---|---|---|---|---|
| `lr_p0_altA.jsonl` | `9152cbefa154be0e8ecc6bc3a3e4f9f0fd5bab956ef655ae2af4ce9adbd53004` | ubuntu2 | 6 | 24 |
| `lr_p0_nullA.jsonl` | `e7930d27ef9768e847a5a53746288fd4187914c9335bc1a596631adf8a200196` | ubuntu2 | 0–2 | 201 |
| `lr_p0_nullB.jsonl` | `bb843caf675add81c11211bfc25c7f394026269b37025590c8985732ea101472` | ubuntu1 | 48 | 79 |
| `lr_p0_r2a.jsonl` | `480ee458e0d012b53ab0a068cdb95ead8896b802b85471953e651ed4b5f196b8` | mmx-ubuntu0 | 18 | 6 |
| `lr_p0_r2b.jsonl` | `a2183a8abfd291dbb13b4d12a305381a6e18681964fdadffde2a57ff1b8fce59` | mmx-ubuntu0 | 45 | 3 |
| `lr_p0_r2n.jsonl` | `1e1968a7ded0230f7169f598e8897ddbcdba6085a8f40960a42517161eee544c` | ubuntu1 | 3–4 | 84 |
| `lr_p0_u0x.jsonl` | `22d1f682c1fc507b2b0dc03365e5999725de033e854d7b74c4e39cdc84ee1854` | mmx-ubuntu0 | 6–9, 48 | 175 |
| `lr_p0_u0y.jsonl` | `0d3901e25a66ffd31f2b2fc2cfab9ef262e98ba216a7cf6652ee656576d8d353` | mmx-ubuntu0 | 30–32 | 72 |

- Aggregation: records kept 541; duplicates 103 (the same `(cell_id, k)` produced by more than one run; the summary aborts on any duplicate whose content differs, so every duplicate kept is an identical re-draw — cross-host reproducibility evidence); partial last lines skipped 0.
- Excluded from aggregation: `lr_p0_r2c.jsonl` (sha256 `279b2325989e70d1a92f9c67877c6c88f708826e72041a9e2ad3333d50c60482`, host ubuntu1, cell 18, k 0–3, 4 lines). It is a redundant subset of `lr_p0_r2a.jsonl` (cell 18, k 0–5, host mmx-ubuntu0). The two runs differ only in the H2 and H3 `point` estimate fields — 15 floating-point values, largest absolute difference 8.85e-17, largest relative difference 7.22e-14 (last-bit rounding between hosts); every decision, confidence bound, honest-N, window end and truth count is identical. The summary's exact-equality duplicate check refuses such near-identical pairs, so r2c was left out rather than the check loosened; its inclusion could change no table entry.
- Grid hosts: python 3.12.3, numpy 2.5.4, pandas 3.0.6 (Linux). Summary host: python 3.14.7, numpy 2.5.2, pandas 3.0.5 (macOS).
- P0 runs: 9 grid invocations (altA, nullA, nullB, u0x, u0y, r2a, r2b, r2c, r2n) and 1 summary aggregation over eight record files (r2c excluded, above).


## Look count

P1 looks: 0. P2 looks: 0. P0 runs: 9 grid invocations and 1 summary aggregation (see §8 identity block).

## Verdict

T11 — DEVELOPMENT EVIDENCE ONLY (P0 synthetic). Harness built; controls C1–C3 and baselines B1–B7 implemented, not computed in P0; no real-data read (P1 not executed, prereg §12 invalidator 6). H1 test MIS-SIZED at δ = 0 (see T12): repair before any read.
