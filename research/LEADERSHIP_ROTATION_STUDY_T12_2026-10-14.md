# Leadership Rotation — Study T12 (H1 early detection)

**Headline (P0):** the H1 intersection–union test is **MIS-SIZED** at δ = 0 — false-pass rates exceed α = 0.025 beyond simulation noise in cells 0 and 1 (and family-wide excess in cells 0, 1, and 4). Under prereg §8 the H1 verdict machinery must be repaired before any read of real data. Partition executed: **P0 (synthetic) only**.

## Exemplars and current regime

PENDING — P1 not executed (prereg §12 invalidator 6: prereg not yet on origin/main). Command once it lands: python3 scripts/leadership_rotation_run.py p1 --repo . --out <path>; the refusal guard runs before any data load.

Once P1 runs, the October 2026 and July 2026 episodes and the last 63 sessions will be DEVELOPMENT exemplars for H1: whether A1 detects qualifying zig-zag onsets earlier than A2 delayed confirmation (condition a) and with lower false-alarm burden than A0 suppressed onsets (condition b), under the §7 margins and Holm family — without using those windows in any confirmatory set.

## Honest-N

P0 δ = 0 cells (H1 rows, Table 4):

| cell | group | median_honest_n | median_window_years |
|---|---|---:|---:|
| 0 | defensive_sector | 22.000 | 11.317 |
| 0 | broadening_proxy | 20.000 | 11.317 |
| 1 | defensive_sector | 46.000 | 23.119 |
| 1 | broadening_proxy | 40.000 | 23.119 |
| 2 | both | — | — (UNREACHED) |
| 3 | defensive_sector | 23.000 | 14.308 |
| 3 | broadening_proxy | 20.000 | 14.308 |
| 4 | defensive_sector | 43.000 | 28.863 |
| 4 | broadening_proxy | 40.000 | 28.863 |
| 48 | defensive_sector | 22.000 | 7.194 |
| 48 | broadening_proxy | 20.000 | 7.194 |

Honest-N for δ > 0 cells is not tabulated in the P0 summary. Prereg rule: ≥ 20 clusters (episodes, not fires or dates).

## In-sample status

2026-10-14 is not in any executed sample. P0 is synthetic. P1 ends 2026-10-12 and was not executed. P3 begins after the prereg lands on `origin/main`.

## Who is missing

XLRE (from 2015) and XLC (from 2018) are not in the cohort (prereg §2). `xlp_vs_smh` is excluded from P2. Constituent overlap is UNMEASURED historically (H3). Synthetic P0 pairs do not share physical legs (R13 sensitivity not exercised). Survivorship: ETF pairs; composition drift not modelled.

## Uncertainty

Stationary block bootstrap, mean block 21, 2000 replicates, seed 20261014, paired across arms; clusters ±10 sessions single linkage within group (prereg §8). Holm m = 6. Wilson 95 % intervals on P0 δ = 0 pass rates are simulation uncertainty only.

## All baselines

| arm | P0 |
|---|---|
| H1 verdict (defensive_sector) | δ=0 pass: cell 0 7/100 (0.070); cell 1 9/100 (0.090); cell 3 0/42; cell 4 3/42 (0.071); cell 48 1/79 (0.013). δ=0.25 pass: cell 6 1/24; cell 7 4/24; cell 8 3/14; cell 9 0/24; cell 18 1/6; cell 30 0/24; cell 31 2/24; cell 32 7/24; cell 45 0/3. Table 4 δ=0 median_raw_p defensive_sector: 0.001 (cell 0), 0.000 (cell 1), 0.001 (cell 3), 0.000 (cell 4), 0.001 (cell 48). median_honest_n: see §2. |
| H1 verdict (broadening_proxy) | δ=0 pass: cell 0 2/100 (0.020); cell 1 13/100 (0.130); cell 3 0/42; cell 4 3/42 (0.071); cell 48 0/79. δ=0.25 pass: cell 6 1/24; cell 7 2/24; cell 8 2/14; cell 9 1/24; cell 18 0/6; cell 30 0/24; cell 31 0/24; cell 32 3/24; cell 45 0/3. Table 4 δ=0 median_raw_p broadening_proxy: 0.001 (cell 0), 0.000 (cell 1), 0.001 (cell 3), 0.000 (cell 4), 0.003 (cell 48). |
| H1 Table 3 — median delay reduction (A1 vs A2), δ = 0 cells | cell 0: defensive_sector 5.000, broadening_proxy 5.000. cell 1: 5.000 / 5.000. cell 3: 5.000 / 5.000. cell 4: 5.000 / 5.000. cell 48: 5.000 / 5.000. (δ > 0 cells: see Table 3 in P0 packet.) |
| H1 Table 3 — median burden cut (A1 vs A0 suppressed) | defensive_sector: 0.513 (cell 0), 0.501 (cell 1), 0.503 (cell 3), 0.508 (cell 4), 0.478 (cell 6), 0.488 (cell 7), 0.480 (cell 8), 0.489 (cell 9), 0.354 (cell 18), 0.500 (cell 30), 0.528 (cell 31), 0.522 (cell 32), 0.474 (cell 45), 0.546 (cell 48). broadening_proxy: 0.513 (cell 0), 0.508 (cell 1), 0.487 (cell 3), 0.518 (cell 4), 0.468 (cell 6), 0.509 (cell 7), 0.489 (cell 8), 0.499 (cell 9), 0.443 (cell 18), 0.517 (cell 30), 0.525 (cell 31), 0.506 (cell 32), 0.454 (cell 45), 0.523 (cell 48). |
| A0 incumbent (suppressed onsets) | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| A1 challenger hysteresis | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |
| A2 delayed confirmation | not computed in P0 — the grid records do not carry per-arm metrics; scheduled for the post-repair P0 rerun |

## Nulls

Size verdict: **NOT SIZED** (prereg §8: false-pass at δ = 0 must be ≤ α = 0.025).

δ = 0 H1 pass rates (Table 1):

| cell | σ | ρ | N | defensive_sector/H1 | broadening_proxy/H1 |
|---|---:|---:|---:|---|---|
| 0 | 0.70 | 0.500 | 20 | 7/100 (0.070) | 2/100 (0.020) |
| 1 | 0.70 | 0.500 | 40 | 9/100 (0.090) | 13/100 (0.130) |
| 3 | 0.70 | 0.800 | 20 | 0/42 (0.000) | 0/42 (0.000) |
| 4 | 0.70 | 0.800 | 40 | 3/42 (0.071) | 3/42 (0.071) |
| 48 | 1.40 | 0.500 | 20 | 1/79 (0.013) | 0/79 (0.000) |

Located size bullets (H1 and family; prereg §8):

- cell 0 (σ 0.70, ρ 0.500, N 20) defensive_sector/H1: 7/100 (0.070), Wilson 95 % lower 0.034 — **SIZE_VIOLATION**
- cell 0 (σ 0.70, ρ 0.500, N 20) family_any: 9/100 (0.090), Wilson 95 % lower 0.048 — **FAMILY_SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) defensive_sector/H1: 9/100 (0.090), Wilson 95 % lower 0.048 — **SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) broadening_proxy/H1: 13/100 (0.130), Wilson 95 % lower 0.078 — **SIZE_VIOLATION**
- cell 1 (σ 0.70, ρ 0.500, N 40) family_any: 22/100 (0.220), Wilson 95 % lower 0.150 — **FAMILY_SIZE_VIOLATION**
- cell 4 (σ 0.70, ρ 0.800, N 40) family_any: 5/42 (0.119), Wilson 95 % lower 0.052 — **FAMILY_SIZE_VIOLATION**
- cell 4 (σ 0.70, ρ 0.800, N 40) defensive_sector/H1: 3/42 (0.071), Wilson 95 % lower 0.025 — **SIZE_EXCEEDS_POINT**
- cell 4 (σ 0.70, ρ 0.800, N 40) broadening_proxy/H1: 3/42 (0.071), Wilson 95 % lower 0.025 — **SIZE_EXCEEDS_POINT**

Power nulls (Table 2): at injected δ > 0, H1 pass rates in σ 0.70 cells are not distinguishable from δ = 0 at the same ρ and N; that is a null of the test under this generator, not evidence against early detection in markets.

### Interpretation notes (T12)

- N1 (T12, H1 condition a — construction note). A2 is A1 with a 5-session confirmation (ruling R5: an A1 entry at e is confirmed iff A1 stays ON for e+1..e+5; the alarm date is e+5). Whenever A1 and A2 match the same onset through the same entry, A2's delay is exactly A1's delay + 5. The H1(a) statistic (median-delay reduction, margin >= 5 sessions) therefore sits on its margin by construction, independent of any market signal; it moves off 5 only through entries A2 rejects or later entries A2 matches instead. A P0 pass of H1 at delta = 0 is read through this note: it measures the arm construction, not an edge. Condition (b) (burden versus A0) is not mechanically tied this way.
- N8 (T12 headline — H1 is MIS-SIZED; DEVELOPMENT_FAIL). At δ = 0 (no injected rotation) the H1 intersection–union test passes more often than α = 0.025 allows, and in cells 0 and 1 (σ 0.70 pts, ρ 0.5, N 20 and 40) the excess is beyond simulation noise (Wilson 95 % lower bound above 0.025 — SIZE_VIOLATION; the counts are in Table 1 and the located size bullets). In cell 4 (σ 0.70 pts, ρ 0.8, N 40) H1 passes in 3 of 42 simulations in each group: a point rate above α whose Wilson lower bound is 0.0246, just under α, so within simulation noise (SIZE_EXCEEDS_POINT; Table 1 prints it rounded as 0.025); the family-wide rate there, 5 of 42, comes only from those H1 passes (H2 and H3 pass in none) and is beyond noise (FAMILY_SIZE_VIOLATION). Cell 3 (σ 0.70 pts, ρ 0.8, N 20) has no H1 pass in 42 simulations and cell 48 (σ 1.40 pts, ρ 0.5, N 20) one in 79; the largest excesses are at N 40 (cells 1 and 4), cell 0 at N 20 also violates, and the cells run cannot separate an N or ρ effect from simulation noise. Under prereg §8 the H1 verdict machinery is therefore repaired before any read; no real-data H1 verdict may be computed with the frozen V1 machinery. Mechanism, from Tables 3 and 4: (i) condition (b) — A1's burden cut against A0 suppressed onsets — holds in EVERY δ = 0 simulation, because A0 carries roughly twice A1's non-matched alarm burden on pure noise, so the 0.25 margin is cleared by how the two arms are built, not by any rotation; (ii) condition (a) holds in a majority of δ = 0 simulations because the A1-vs-A2 median delay reduction sits exactly on its 5-session margin (note N1); (iii) the H1 raw p-value is below 0.025 in the large majority of δ = 0 simulations (Table 4), so it is not a null-calibrated p-value — the bootstrap tests each margin against differences between arms that exist with no rotation at all. A further reason δ = 0 is not a null for H1's estimand: the truth labeller finds zig-zag up-phases on rotation-free noise paths, and a trend-following arm detects those noise phases too, so "detects up-phases early" is true of A1 even when there is nothing to rotate. What holds the observed false-pass rate to single digits or low teens rather than near 100 % is the non-inferiority detection clause, the stability thirds and Holm — not the test's size. At δ = 0.25 the H1 pass rates (Table 2) are not distinguishable from the δ = 0 rates in the σ 0.70 cells, the only noise level run at both δ = 0 and δ = 0.25 with matching ρ and N: on this evidence H1 does not respond to the injected effect (the σ 1.00 cells were run at δ > 0 only and have no δ = 0 reference).
- N4 (T11, T12, T13, T14 — coverage). The section 7 clause 3 gate counts SOURCE_INVALID and UNMEASURED pair-days in the denominator (ruling R2: neither is ever zero-filled or forward-filled). P0 has no missingness, so all-event coverage is 100 % by construction in every cell; the gate is exercised on real data only.
- N5 (T12, T13, T14 — stability thirds, ruling R22). The calendar pair-sessions are the (pair, day) slots with a finite R inside the formation window; thirds are cut on that multiset (a day appears once per measured pair), and each cluster sits in the third containing its earliest onset. With all pairs measured every day (P0) this equals cutting the calendar into equal thirds.
- N7 (T11, T12, T13, T14 — size rule). Prereg section 8: the false-pass rate at delta = 0 must be <= alpha = 0.025, else the machinery is repaired before any read. The grid flags SIZE_VIOLATION when the Wilson 95 % LOWER bound of the delta = 0 pass rate exceeds 0.025 (the excess is beyond simulation noise) and prints every cell whose POINT rate exceeds 0.025 as SIZE_EXCEEDS_POINT (excess not distinguishable from simulation noise at this sim count). Both are reported; neither is softened.
- N11 (T12, cited from T11, T13 and T14 — H1 repair options for the SEAT; not applied here). The prereg is frozen at fafdaf09 and ORCH-SCI does not amend it. Options, any of which must be recorded as a dated amendment (or a revision before PR #9251 merges), re-verified on the P0 δ = 0 cells, and landed BEFORE any outcome-bearing commit: (A, recommended by ORCH-SCI) noise-referenced H1 — compare each condition's observed statistic with M rotation-free (δ = 0) surrogate paths matched on σ, ρ, N and calendar, run through the same arms; p = (1 + #{surrogate ≥ observed}) / (1 + M); apply each margin to observed minus the surrogate median; (C) make condition (a) a non-inferiority clause only (delay reported, not tested) and make condition (b) rate-matched — compare detection at EQUAL burden by thresholding A0 to A1's burden — which removes the construction gap; (D, minimal) drop H1 from the confirmatory family (Holm m = 4) and report H1 descriptively only. Each option changes what H1 can claim; choosing among them is a seat ruling.

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

P1 looks: 0. P2 looks: 0. P0 runs: 9 grid invocations and 1 summary aggregation (see §8).

## Verdict

H1 — P0 DEVELOPMENT_FAIL: MIS-SIZED (prereg §8: false-pass at δ = 0 above α = 0.025 beyond simulation noise in cell(s) 0, 1; in cell(s) 4 the H1 point rate exceeds α within simulation noise and the H1-driven family-wide rate exceeds it beyond noise). No real-data read until a seat ruling repairs the H1 test and the repaired test is re-sized on the P0 δ = 0 cells.
