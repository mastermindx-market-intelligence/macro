## Data class

Inputs are **final-vintage** (the price stores are as observed today, not point-in-time) and the universe is **survivor-selected** (current membership only). Every signal uses only closes at or before the signal session.

## Answer first

After matching elapsed memory (1D.M3 = k=1/3), the 3D grain effect is **NOT SUPPORTED**: the **pooled-across-phases Δ(3D.p* − 1D.M3)** on cost-adjusted SPY-excess H10 is +0.0001 95% CI [-0.0003, +0.0004]. The pooled 3D.p* mean is -0.0043 [-0.0074, -0.0015]; the pooled 1D.M3 mean is -0.0044 [-0.0075, -0.0014]. Phase/era sign pattern follows below. 2D grain effect: **NOT SUPPORTED**; memory effect (1D.M3 − 1D): **NOT SUPPORTED**.

## Universe and exclusions

- Names in (raw `data/baskets/ohlcv/*.parquet`): **2,812**
- Excluded for <800 rows: **225**
- Excluded for any internal gap > 5 SPY sessions: **1**
- Names used: **2,586**

## Per-variant event counts (F4)

Each event passes THREE drop gates. `pre_warmup` is the count of bullish-cross candidates BEFORE the warm-up filter (events with both bars non-NaN and a valid signal). `warmup` is the count of candidates whose signal session fell inside the first 400 sessions of the name's inner-joined series (D2/F4: warm-up measured from the name's first session, not from the absolute SPY position). `horizon21` is the count of events whose entry_date + 21 sessions would have overrun the data (F7: SPY-grid based). `outcomes_none` is the count of events whose outcome row could not be computed (e.g. zero or negative closes at entry or at the SPY grid position).

| variant | pre_warmup | warmup | horizon21 | no_entry | outcomes_none | after_warmup | panel_n |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1D | 341,020 | 41,705 | 2,579 | 99 | 0 | 299,315 | 296,637 |
| 2D.p0 | 165,945 | 16,129 | 1,025 | 1 | 0 | 149,816 | 148,790 |
| 2D.p1 | 165,572 | 15,885 | 973 | 62 | 0 | 149,687 | 148,652 |
| 3D.p0 | 107,632 | 7,234 | 486 | 0 | 0 | 100,398 | 99,912 |
| 3D.p1 | 107,233 | 7,094 | 474 | 0 | 0 | 100,139 | 99,665 |
| 3D.p2 | 107,543 | 7,316 | 478 | 47 | 0 | 100,227 | 99,702 |
| 1D.M2 | 173,562 | 21,434 | 1,019 | 25 | 0 | 152,128 | 151,084 |
| 1D.M3 | 116,471 | 14,379 | 498 | 19 | 0 | 102,092 | 101,575 |
| 3D.K1 | 282,142 | 19,613 | 2,200 | 2 | 0 | 262,529 | 260,327 |

## Per-variant statistics

Mean excess_h10_net, mean excess_h21_net, hit_rate_h10, plus month-cluster bootstrap 95% CIs (1,000 resamples over distinct entry_months, SeedSequence-derived RNG). n_events, n_months, n_names.

| variant | n_events | n_months | n_names | mean_h10_net | 95% CI h10 | mean_h21_net | 95% CI h21 | hit_h10 | median_mfe21 | median_mae21 |
|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| 1D | 296,637 | 133 | 2,586 | -0.0057 | [-0.0085, -0.0030] | -0.0098 | [-0.0144, -0.0056] | 0.464 | +0.0545 | -0.0491 |
| 2D.p0 | 148,790 | 133 | 2,586 | -0.0053 | [-0.0084, -0.0024] | -0.0097 | [-0.0141, -0.0055] | 0.466 | +0.0542 | -0.0488 |
| 2D.p1 | 148,652 | 133 | 2,586 | -0.0052 | [-0.0080, -0.0020] | -0.0095 | [-0.0141, -0.0052] | 0.465 | +0.0543 | -0.0490 |
| 3D.p0 | 99,912 | 133 | 2,586 | -0.0043 | [-0.0076, -0.0011] | -0.0087 | [-0.0135, -0.0041] | 0.468 | +0.0545 | -0.0479 |
| 3D.p1 | 99,665 | 133 | 2,586 | -0.0039 | [-0.0068, -0.0008] | -0.0089 | [-0.0136, -0.0041] | 0.471 | +0.0547 | -0.0482 |
| 3D.p2 | 99,702 | 133 | 2,586 | -0.0046 | [-0.0077, -0.0016] | -0.0091 | [-0.0139, -0.0042] | 0.467 | +0.0555 | -0.0474 |
| 1D.M2 | 151,084 | 133 | 2,586 | -0.0054 | [-0.0083, -0.0026] | -0.0099 | [-0.0145, -0.0052] | 0.466 | +0.0544 | -0.0489 |
| 1D.M3 | 101,575 | 133 | 2,586 | -0.0044 | [-0.0073, -0.0009] | -0.0091 | [-0.0141, -0.0041] | 0.469 | +0.0549 | -0.0479 |
| 3D.K1 | 260,327 | 133 | 2,586 | -0.0057 | [-0.0085, -0.0026] | -0.0092 | [-0.0138, -0.0051] | 0.464 | +0.0544 | -0.0494 |

### Per-era, per-variant H10 net

| variant | 2014-2019 mean | 2014-2019 CI | 2020-2026 mean | 2020-2026 CI |
|---|---:|---|---:|---|
| 1D | -0.0046 | [-0.0070, -0.0021] | -0.0062 | [-0.0103, -0.0020] |
| 2D.p0 | -0.0055 | [-0.0085, -0.0026] | -0.0052 | [-0.0098, -0.0006] |
| 2D.p1 | -0.0047 | [-0.0074, -0.0019] | -0.0054 | [-0.0094, -0.0010] |
| 3D.p0 | -0.0059 | [-0.0090, -0.0028] | -0.0035 | [-0.0082, +0.0010] |
| 3D.p1 | -0.0058 | [-0.0087, -0.0025] | -0.0029 | [-0.0071, +0.0013] |
| 3D.p2 | -0.0061 | [-0.0092, -0.0025] | -0.0038 | [-0.0082, +0.0004] |
| 1D.M2 | -0.0050 | [-0.0079, -0.0022] | -0.0055 | [-0.0097, -0.0014] |
| 1D.M3 | -0.0060 | [-0.0089, -0.0030] | -0.0035 | [-0.0077, +0.0007] |
| 3D.K1 | -0.0046 | [-0.0074, -0.0019] | -0.0062 | [-0.0103, -0.0021] |

## Phase dispersion

Range across phases of the H10_net mean; Jaccard of (name, signal_date) event sets (exact-date, mechanically 0 because phases' bar end-dates never coincide); tolerant Jaccard (events from different phases match when their 1D signal sessions lie within n−1 SPY sessions — F13 amendment); pooled-across-phases mean with its bootstrap CI; phase_fragile = range > pooled CI width.

| grain | range_h10 | pooled_mean_h10 | pooled 95% CI | fragile | tol(sessions) | jaccard p0-p1 | jaccard p0-p2 | jaccard p1-p2 |
|---|---:|---:|---|:---:|---:|---:|---:|---:|
| 2D | +0.00018 | -0.0052 | [-0.0081, -0.0024] | no | 1 | exact=0.000 tol=0.566 | — | — |
| 3D | +0.00069 | -0.0043 | [-0.0072, -0.0011] | no | 2 | exact=0.000 tol=0.574 | exact=0.000 tol=0.576 | exact=0.000 tol=0.577 |

## Contrasts

Each contrast = Δ(A − B) of the H10_net mean. Same-month-cluster bootstrap (1,000 draws, SeedSequence-spawn-derived RNG) is used for both A and B. Overall and per-era. Every cell carries n_events, n_months, n_names for BOTH arms (F9).

| contrast | overall Δ | overall h10 CI | n_a/n_b events | n_a/n_b months | n_a/n_b names | 2014-2019 Δ | 2014-2019 CI | n_a/n_b events | 2020-2026 Δ | 2020-2026 CI | n_a/n_b events |
|---|---:|---|---:|---:|---:|---:|---|---:|---:|---|---:|
| 3D.p0_minus_1D | +0.0013 | [-0.0010, +0.0037] | 99,912/296,637 | 133/133 | 2,586/2,586 | -0.0013 | [-0.0037, +0.0010] | 34,099/99,574 | +0.0027 | [-0.0006, +0.0060] | 65,813/197,063 |
| 3D.p0_minus_1D.M3 | +0.0000 | [-0.0007, +0.0007] | 99,912/101,575 | 133/133 | 2,586/2,586 | +0.0001 | [-0.0010, +0.0010] | 34,099/34,791 | -0.0000 | [-0.0009, +0.0009] | 65,813/66,784 |
| 3D.p1_minus_1D | +0.0017 | [-0.0006, +0.0038] | 99,665/296,637 | 133/133 | 2,586/2,586 | -0.0012 | [-0.0034, +0.0010] | 34,105/99,574 | +0.0032 | [+0.0004, +0.0062] | 65,560/197,063 |
| 3D.p1_minus_1D.M3 | +0.0004 | [-0.0003, +0.0012] | 99,665/101,575 | 133/133 | 2,586/2,586 | +0.0002 | [-0.0007, +0.0011] | 34,105/34,791 | +0.0006 | [-0.0004, +0.0015] | 65,560/66,784 |
| 3D.p2_minus_1D | +0.0011 | [-0.0011, +0.0031] | 99,702/296,637 | 133/133 | 2,586/2,586 | -0.0015 | [-0.0035, +0.0006] | 34,238/99,574 | +0.0023 | [-0.0008, +0.0053] | 65,464/197,063 |
| 3D.p2_minus_1D.M3 | -0.0002 | [-0.0010, +0.0005] | 99,702/101,575 | 133/133 | 2,586/2,586 | -0.0001 | [-0.0012, +0.0009] | 34,238/34,791 | -0.0003 | [-0.0013, +0.0006] | 65,464/66,784 |
| 2D.p0_minus_1D.M2 | +0.0000 | [-0.0005, +0.0006] | 148,790/151,084 | 133/133 | 2,586/2,586 | -0.0005 | [-0.0011, +0.0001] | 50,642/51,181 | +0.0003 | [-0.0004, +0.0011] | 98,148/99,903 |
| 2D.p1_minus_1D.M2 | +0.0002 | [-0.0003, +0.0007] | 148,652/151,084 | 133/133 | 2,586/2,586 | +0.0004 | [-0.0002, +0.0009] | 50,588/51,181 | +0.0001 | [-0.0006, +0.0008] | 98,064/99,903 |
| 1D.M3_minus_1D | +0.0013 | [-0.0008, +0.0035] | 101,575/296,637 | 133/133 | 2,586/2,586 | -0.0013 | [-0.0034, +0.0008] | 34,791/99,574 | +0.0027 | [-0.0003, +0.0057] | 66,784/197,063 |
| 1D.M2_minus_1D | +0.0003 | [-0.0013, +0.0018] | 151,084/296,637 | 133/133 | 2,586/2,586 | -0.0004 | [-0.0018, +0.0010] | 51,181/99,574 | +0.0007 | [-0.0017, +0.0030] | 99,903/197,063 |
| 3D.K1_minus_3D.p0 | -0.0013 | [-0.0034, +0.0008] | 260,327/99,912 | 133/133 | 2,586/2,586 | +0.0013 | [-0.0010, +0.0036] | 87,452/34,099 | -0.0027 | [-0.0057, +0.0003] | 172,875/65,813 |

## Confirmation pairs (1D events)

For each 1D event (name, s), find the FIRST event of the variant on the same name with signal session s' in [s, s+10]. no_confirmation_share = share with no candidate; median_delay_sessions; mean_confirmation_cost_pct (C[s'+1]/C[s+1]−1); mean_mfe21_consumed_frac = (ln C[s'+1] − ln C[s+1]) / MFE21_1D.

| variant | n | no_confirmation_share | median_delay | mean_cost_pct | mean_mfe_consumed |
|---|---:|---:|---:|---:|---:|
| 2D.p0 | 296,637 | 0.524 | 4.00 | +0.0318 | +0.0466 |
| 2D.p1 | 296,637 | 0.525 | 4.00 | +0.0315 | -0.1872 |
| 3D.p0 | 296,637 | 0.736 | 5.00 | +0.0471 | +0.1042 |
| 3D.p1 | 296,637 | 0.737 | 5.00 | +0.0468 | +0.1202 |
| 3D.p2 | 296,637 | 0.736 | 5.00 | +0.0468 | +0.0977 |

## Verdict

**Rule**: grain_effect_3d REAL iff Δ(3D.p − 1D.M3) on H10_net has the same sign and CI excludes zero in BOTH eras for ≥ 2 of the 3 phases, AND the qualifying phases all share a common sign. grain_effect_2d same rule on Δ(2D.p − 1D.M2), requiring BOTH phases. memory_effect_3 same on Δ(1D.M3 − 1D) (one phase, both eras, same sign in both eras and both CIs exclude zero).

| effect | verdict |
|---|---|
| grain_effect_3d | **NOT SUPPORTED** |
| grain_effect_2d | **NOT SUPPORTED** |
| memory_effect_3 | **NOT SUPPORTED** |

### 3D grain effect: phase/era sign pattern (Δ(3D.p − 1D.M3))

| phase | 2014-2019 Δ | 2014-2019 CI | 2020-2026 Δ | 2020-2026 CI | sign | excl-0 both |
|---|---:|---:|---:|---:|:---:|:---:|
| 3D.p0 | +0.0001 | [-0.0010, +0.0010] | -0.0000 | [-0.0009, +0.0009] | MIXED | no |
| 3D.p1 | +0.0002 | [-0.0006, +0.0011] | +0.0006 | [-0.0004, +0.0016] | + | no |
| 3D.p2 | -0.0001 | [-0.0012, +0.0009] | -0.0003 | [-0.0013, +0.0007] | - | no |

### 2D grain effect: phase/era sign pattern (Δ(2D.p − 1D.M2))

| phase | 2014-2019 Δ | 2014-2019 CI | 2020-2026 Δ | 2020-2026 CI | sign | excl-0 both |
|---|---:|---:|---:|---:|:---:|:---:|
| 2D.p0 | -0.0005 | [-0.0011, +0.0001] | +0.0003 | [-0.0005, +0.0011] | MIXED | no |
| 2D.p1 | +0.0004 | [-0.0002, +0.0008] | +0.0001 | [-0.0006, +0.0008] | + | no |

### Memory effect: era sign pattern (Δ(1D.M3 − 1D))

| era | Δ | CI | sign | excl-0 |
|---|---:|---:|:---:|:---:|
| 2014-2019 | -0.0013 | [-0.0033, +0.0009] | - | no |
| 2020-2026 | +0.0027 | [-0.0004, +0.0056] | + | no |
| **verdict** | — | — | — | **NOT SUPPORTED** |

## Notes (F12/G8/L9)

- Warm-up = **400 sessions** (D2: measured from each name's FIRST inner-joined session, NOT from absolute SPY position).
- Per-variant panel_n round 1 → round 2 → round 3 (r1/r2 from preserved round records; r3 from the frozen panel):

| variant | r1 | r2 | r3 | r1→r2 | r2→r3 |
|---|---:|---:|---:|---:|---:|
| 1D | 296,635 | 296,669 | 296,637 | +34 | -32 |
| 2D.p0 | 148,790 | 148,802 | 148,790 | +12 | -12 |
| 2D.p1 | 148,651 | 148,665 | 148,652 | +14 | -13 |
| 3D.p0 | 99,912 | 99,919 | 99,912 | +7 | -7 |
| 3D.p1 | 99,665 | 99,673 | 99,665 | +8 | -8 |
| 3D.p2 | 99,702 | 99,710 | 99,702 | +8 | -8 |
| 1D.M2 | 151,084 | 151,097 | 151,084 | +13 | -13 |
| 1D.M3 | 101,575 | 101,582 | 101,575 | +7 | -7 |
| 3D.K1 | 260,327 | 260,350 | 260,327 | +23 | -23 |

- Confirmation pairs with MFE21_1D < 0.001 (counted on 1D events, hence on every variant's pair rows): **35,502**, of which ≤ 0: **34,178** and 0 < mfe < 0.001: **1,324**.
- 2D.p1 mean_mfe21_consumed_frac raw = **-0.187151**; 5%-trimmed mean = **+0.266977**. The negative raw mean is a tail effect of the 1,324 near-zero positive MFE21_1D denominators (plus the 34,178 non-positive MFE rows, which are NaN and excluded from the mean).
- The 16 value-changed rows between round 1 and round 2 (FI 9 / NXXT 4 / NFE 3) are the F7 story: those 10 gap names had outcomes indexed on the name grid in r1 and were re-indexed onto the SPY calendar in r2, so the h10/h21 values changed even when the event survived. Round 2 → round 3 then dropped 123 stale rows (G1: e+21 past the name's last close).
- Jaccard = 0 explanation: exact-date Jaccard across phases is mechanically 0 because phases' bar end-dates never coincide (phase-0 ends on session n-1 of every n-bucket; phase-1 ends on session n). The tolerant Jaccard (G3) matches on SPY session POSITION with |Δpos| ≤ n−1, one-to-one greedy matching, and produces non-zero values.

## Files

- `events_panel.parquet` (sha256: `209e224686955cf1…`)
- `confirmation_pairs.parquet` (sha256: `d20cd4056e8e6b1f…`)
- `code/universe_manifest.json` (per-name rows + sha256; listed in hashes.txt)
- `result.json`, `RESULT.md`, `hashes.txt`, `summary.json`, `code/run_all.py`

Tests: 34 passed

## Tests

| mutant | failing test |
|---|---|
| M2a | `test_live_lookahead_name_events_true_cross` |
| M2b | `test_outcomes_anchored_at_entry_position` |
| M2c | `test_live_lookahead_name_events_true_cross` |
| M3a-table | `test_production_variant_table_uses_k_constants_not_inverted_literals` |
| M3a_const | `test_half_life_reads_run_module_constants` |
| M3b | `test_half_life_reads_run_module_constants` |
| M6a | `test_delta_bootstrap_pair_cluster_se_and_nonconstant_draws` |
| M6b | `test_bucketing_drops_short_buckets` |
| M6c | `test_bar_date_is_last_session_of_bucket` |
| G1 +21→+10 | `test_horizon_gate_uses_21_not_10` |
| G6 continue | `test_no_entry_incremented_on_terminal_session_cross` |

pytest summary (counts only): **34 passed**

L8 two-process stats-pipeline sha256: `ad3f1651333b1744a2edfaf6ee5340f25ef6a5c2ce9fce216e84762a32b11a06` / `ad3f1651333b1744a2edfaf6ee5340f25ef6a5c2ce9fce216e84762a32b11a06`
identical

L8 note (round 5, seat-executed record repair, 2026-10-04): the pair above is the lane's receipt of two stats.py+finalize.py runs taken BEFORE `code/mutant_results.json` was folded into the record. It is NOT the sha256 of the shipped `result.json`, and it is not reproducible from the shipped files (the seat re-serialized twelve candidate pre-fold shapes of the final record; none matched). No shipped record can carry its own sha256 (fixed point), so the reproducible two-process identity is stated on the stats stage: two independent `stats.py` processes on copies of this tree (frozen `events_panel.parquet` 209e2246… / `confirmation_pairs.parquet` d20cd405…) each wrote `result_partial.json` with sha256 `192da18996b8e46bc32d5bc5f98821b4a09eedc4317c17749a34a8a1fa25af7f`, identical to each other and to the shipped `result_partial.json`. `finalize.py` folds `result_partial.json` + `summary.json` + `code/mutant_results.json` + the pytest summary into the final `result.json`, sha256 `e480d73a06b1fe01ebbd67ce4c80f1e83b08466d0f82a4b82f03955fc0dd4d09` — the hashed final file (hashes.txt). The L1..L11 FIXED list with file:line is in `B1_RETURN.md`.

## Provenance

Host **m2**; python `/opt/homebrew/bin/python3` 3.14.7; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1.

## Deviations

1. spec amended by seat 2026-10-04 (round 1): k inverted — 1D.M2 = cascade(close_1D, k=1/2); 1D.M3 = cascade(close_1D, k=1/3); 3D.K1 = cascade(close_3D(p=0), k=3) (masterplan §5.2 items 4-5 superseded; cascade_lib.py docstring)
2. spec amended by seat 2026-10-04 (round 2, F13): tolerant Jaccard across phases — events from different phases of the same grain are the same event when their 1D signal sessions lie within n-1 sessions; reported alongside the (mechanically 0) exact-date Jaccard
3. warm-up measured from the name's FIRST inner-joined session, not from the absolute SPY position (D2/F4; run.py:_name_events)
4. warm-up drops now COUNTED per variant (F4): drops[v]["warmup"] is incremented for each event whose signal session fell inside the first 400 sessions of the name's inner-joined series
5. n-DAY buckets kept only when bucket size == n (D7; run.py:_build_n_day_bars)
6. outcomes indexed on the SPY session calendar for BOTH arms of excess_H and MFE/MAE (F7; run.py:_outcomes_for_event)
7. per-cell RNG derived from numpy SeedSequence.spawn(len(cells)) over a STABLE SORTED cell label list (F8/G7; stats.py:_build_cell_streams) — no encounter-order dependency, byte-identical result.json across processes
8. verdict REAL requires same sign across the ≥ 2 qualifying phases AND both eras (D9/F10; stats.py:_compute_verdict); the 2-agree-1-dissent case now keeps details (F10)
9. phase-0 bar equality test compares bucket CLOSES by aligned bucket index (bar_derive labels each bucket by the FIRST session; spec §VARIANTS labels by the LAST session — the bucket set and closes agree, the date labels differ by n-1 sessions)
10. G1: horizon gate drops events whose entry + 21 SPY sessions exceeds the NAME's last available close (covers h21, and therefore h10, since h10_bad ⇒ h21_bad); `_name_close_at_spy_pos` carries `name_last_pos` and returns None past it; `c0` (entry close) is emitted on every panel row
11. G5: run.py module-level K_1D_M2 = 1/2, K_1D_M3 = 1/3, K_3D_K1 = 3.0 — tests read these constants directly (no string search); variant_inputs reads them
12. G6: 'no_entry' drop bucket counts two silent continues in `_name_events` (signal on the final SPY session → no next-session entry; name stopped trading → no later close for the entry)
13. G3: tolerant Jaccard matched on SPY session POSITION with |Δpos| ≤ n−1, one-to-one greedy matching in date order within each name, union = |A| + |B| − matched (replaces calendar-day approximation; reference values: 3D p0-p1 0.5739, p0-p2 0.5761, p1-p2 0.5766; 2D p0-p1 0.5655)
14. round 4 (2026-10-04): tests-and-record repair; events_panel.parquet and confirmation_pairs.parquet byte-frozen (sha256 209e2246… / d20cd405…); no panel number changed

## Gaps

1. no real-data basket input was read at finalize time — the panel was produced in run.py and is referenced by its sha256
