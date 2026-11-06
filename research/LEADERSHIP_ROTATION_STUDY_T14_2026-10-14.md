# Leadership Rotation — Study T14 (H3 paired migration vs receiver-only legs)

Development-phase study record for **H3** (paired migration vs B3 receiver-only legs on beta residual targets; A37 common-factor control via B4). Partition executed: **P0 (synthetic) only**.

## Exemplars and current regime

PENDING — P1 not executed (prereg §12 invalidator 6: prereg not yet on origin/main). Command once it lands: python3 scripts/leadership_rotation_run.py p1 --repo . --out <path>; the refusal guard runs before any data load.

Once P1 runs, the October 2026 and July 2026 episodes and the last 63 sessions will be DEVELOPMENT exemplars for H3: whether mean `Y_20^res` after A1 pair entries exceeds B3 receiver-only entries by at least +0.25 log-ratio points, with B4 beta-only residual control printed and shared-leg clustering disclosed per R13 — never confirmatory.

## Honest-N

P0 δ = 0 cells (H3 rows, Table 4; verdict honest-N uses §8 group rule; literal shared-leg count is sensitivity only — not computed in P0 grid):

| cell | group | median_honest_n | median_window_years |
|---|---|---:|---:|
| 0 | defensive_sector | 21.000 | 3.488 |
| 0 | broadening_proxy | 20.000 | 3.488 |
| 1 | defensive_sector | 44.000 | 7.026 |
| 1 | broadening_proxy | 40.000 | 7.026 |
| 3 | defensive_sector | 20.000 | 4.290 |
| 3 | broadening_proxy | 20.000 | 4.290 |
| 4 | defensive_sector | 41.000 | 8.427 |
| 4 | broadening_proxy | 40.000 | 8.427 |
| 48 | defensive_sector | 22.000 | 3.310 |
| 48 | broadening_proxy | 20.000 | 3.310 |

Honest-N for δ > 0 cells is not tabulated. Prereg minimum: ≥ 20 clusters (episodes).

## In-sample status

2026-10-14 is not in any executed sample. P0 is synthetic. P1 ends 2026-10-12 and was not executed. P3 begins after prereg merge.

## Who is missing

XLRE and XLC absent (prereg §2). `xlp_vs_smh` excluded from P2. Constituent overlap UNMEASURED historically. P0 synthetic pairs do not share physical legs — R13 shared-leg sensitivity not exercised. ETF composition drift not modelled.

## Uncertainty

Stationary block bootstrap, mean block 21, 2000 replicates, seed 20261014, paired across arms; clustered ±10 sessions within group. Holm m = 6. Wilson 95 % on δ = 0 pass rates: simulation uncertainty only.

## All baselines

| arm | P0 |
|---|---|
| H3 verdict (defensive_sector) | δ=0: 0/100 (cell 0), 0/100 (cell 1), 0/42 (cell 3), 0/42 (cell 4), 0/79 (cell 48). δ>0: 0 passes Table 2. Table 4 δ=0 median_raw_p: 0.532 (cell 0), 0.499 (cell 1), 0.388 (cell 3), 0.515 (cell 4), 0.523 (cell 48). |
| H3 verdict (broadening_proxy) | δ=0: 0/100, 0/100, 0/42, 0/42, 0/79. δ>0: 0 passes. Table 4 δ=0 median_raw_p: 0.575 (cell 0), 0.602 (cell 1), 0.443 (cell 3), 0.517 (cell 4), 0.563 (cell 48). |
| A1 on residual target `Y_20^res` | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B3 receiver-only residual comparator | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| B4 beta-only residual control (A37) | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |

## Nulls

δ = 0 size: **no SIZE_VIOLATION** for H3 in cells run.

| cell | defensive_sector/H3 | broadening_proxy/H3 |
|---|---|---|
| 0 | 0/100 (0.000) | 0/100 (0.000) |
| 1 | 0/100 (0.000) | 2/100 (0.020) |
| 3 | 0/42 (0.000) | 0/42 (0.000) |
| 4 | 0/42 (0.000) | 0/42 (0.000) |
| 48 | 0/79 (0.000) | 0/79 (0.000) |

Power: zero H3 passes at every δ in Table 2 — power NOT MEASURED (N9), not evidence against migration. The H1 test is MIS-SIZED at δ = 0 (see T12); Holm coupling on this grid therefore loosens H2/H3 thresholds until H1 is repaired.

### Interpretation notes (T14)

- N2 (T14, H3 overlap — prereg ambiguity, ruling R13). The prereg says "pairs sharing a leg are one cluster". Read literally as connected components of the shared-leg graph, every registered group collapses to ONE cluster and H3 can never reach 20 honest-N. The harness uses the section 8 rule (+/-10 sessions, single linkage, within group) for the verdict's honest-N and prints the literal shared-leg count as a sensitivity number only. P0's synthetic pairs do not share physical legs, so P0 does not exercise this sensitivity. The seat rules on which reading binds before P2/P3.
- N9 (T13 and T14 — H2 and H3: size holds in the cells run; power is not identifiable under the prereg section 8 generator). Size: in every delta = 0 row of Table 1, H2 and H3 pass in at most a few simulations and carry no size flag, and their raw p-values fall below 0.025 in at most a few percent of delta = 0 simulations (Table 4), so on this generator the H2/H3 bootstrap behaves like a null-calibrated test. H2's point estimate sits below zero at delta = 0 because its comparator is the BETTER of two baselines (the prereg requires A1 to beat both B1 and B2), and the larger of two noisy means is biased upward: a conservative construction, faithful to the prereg. Power: H2 and H3 pass in no delta > 0 simulation in Table 2, including the delta = 1.00 cells. That is NOT evidence that A1 lacks a continuation or migration edge. The generator adds the drift to every session of a group regime, so any entry that happens to fire inside a regime collects it, whichever rule fired it; H2 and H3 test A1's margin OVER its baselines (+0.50 points for H2, +0.25 points for H3), and the only edge the generator can give A1 is selectivity and timing (how much more of A1's 20-session windows fall inside regimes than the baselines' windows do), a fraction of delta. With delta at most 1.00 point that fraction rarely clears the margins. P0 as specified therefore SIZES H2 and H3 but cannot MEASURE their power; the grid does not carry per-arm metrics, so this mechanism is the reading the results are consistent with, and the post-repair P0 rerun with per-arm metrics is its falsifier (it would show A1, B1 and B2 20-session means moving together with delta). An honest power statement needs an alternative in which A1 has an edge over its baselines; choosing one is a seat ruling (N11). Holm coupling: H2 and H3 are adjusted in one Holm family of six together with H1. The mis-sized H1 p-values are tiny, take the strictest Holm slots, and leave H2/H3 a LOOSER threshold than they would get beside a correctly sized H1. The H2/H3 false-pass counts here are therefore upper bounds (safe for the size statement), and any H2/H3 power reading on this machinery would be optimistic until H1 is repaired. H3 clustering follows ruling R13 (note N2); the literal shared-leg reading would leave one cluster per group and make H3 UNDERPOWERED by construction.
- N4 (T11, T12, T13, T14 — coverage). The section 7 clause 3 gate counts SOURCE_INVALID and UNMEASURED pair-days in the denominator (ruling R2: neither is ever zero-filled or forward-filled). P0 has no missingness, so all-event coverage is 100 % by construction in every cell; the gate is exercised on real data only.
- N5 (T12, T13, T14 — stability thirds, ruling R22). The calendar pair-sessions are the (pair, day) slots with a finite R inside the formation window; thirds are cut on that multiset (a day appears once per measured pair), and each cluster sits in the third containing its earliest onset. With all pairs measured every day (P0) this equals cutting the calendar into equal thirds.
- N7 (T11, T12, T13, T14 — size rule). Prereg section 8: the false-pass rate at delta = 0 must be <= alpha = 0.025, else the machinery is repaired before any read. The grid flags SIZE_VIOLATION when the Wilson 95 % LOWER bound of the delta = 0 pass rate exceeds 0.025 (the excess is beyond simulation noise) and prints every cell whose POINT rate exceeds 0.025 as SIZE_EXCEEDS_POINT (excess not distinguishable from simulation noise at this sim count). Both are reported; neither is softened.

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

P1 looks: 0. P2 looks: 0. P0 runs: 9 grid invocations and 1 summary aggregation.

## Verdict

H3 — P0: no SIZE_VIOLATION in the δ = 0 cells run; power NOT MEASURED (see N9); honest-N by the §8 group rule with the literal shared-leg reading printed as sensitivity only (ruling R13, see N2); no real-data read.
