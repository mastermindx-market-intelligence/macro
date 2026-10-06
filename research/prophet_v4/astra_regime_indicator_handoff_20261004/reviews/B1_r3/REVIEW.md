# B1 ROUND 3 independent review

## STATUS

PASS (review completed; every named mutant was applied to a scratch copy and pytest'd; per-variant row counts recomputed from the round-2 panel; result.json leaf diff reported)

## RESULT

**Recommended ruling: REQUEST_REPAIR**

The 123 stale rows are gone, the headline Δ moved only as predicted, 2014-2019 means are bitwise frozen, and NOT SUPPORTED stands. G3 Jaccard now matches the session-based reference values. That is not enough. The round-3 packet's binding re-check was that every named mutant must fail a named test: M2a, M2b, M6a, M6b, M6c, and the packet-text M3a table invert do not; RESULT.md never pastes failing-mutant names; G8 still does not report the required counts or trimmed mean.

### Per-item verdict

| item | verdict | file:line |
|---|---|---|
| G1 horizon gate | PARTIAL | code correct `run.py:359-361`; inverted wording `run.py:277`, `RESULT.md:162`, `finalize.py:56`; test `test_B1.py:672-707` (caps at `:702`) |
| G2 look-ahead mutants | NOT FIXED | `test_B1.py:235` (truncation), `:296` (entry, panel-frozen), `:323` (c0, panel-frozen), `:357` (M2a does not apply a mutant), `:396` (M2b checks entry not c0), `:428` (M2c live — this one works) |
| G3 tolerant Jaccard | FIXED | `stats.py:262-312`; unit `test_B1.py:535-555`; values in `result.json` `phase_dispersion.*.jaccard_tolerant` |
| G4 phase-0 / cluster mutants | NOT FIXED | M6a `stats.py:382` / tests `test_B1.py:467-529`; M6b `run.py:84` / `test_B1.py:156`; M6c `run.py:88` / `test_B1.py:183` |
| G5 half-life constants | PARTIAL | constants `run.py:56-58`; test `test_B1.py:561-583`; packet strings `"1D.M3": (close_1d, 1.0 / 3.0)` absent; no `result.json` half-life table |
| G6 no_entry reconcile | PARTIAL | buckets `run.py:133-144`; numbers in `result.json` `drops_per_variant.*.no_entry`; **no** pytest of `pre_warmup − warmup − horizon21 − outcomes_none − no_entry == panel_n` |
| G7 sorted-cell seeds | PARTIAL | `stats.py:61-81` `_build_cell_streams`, `:639-687` collect-then-spawn; RESULT.md has no two-process `result.json` sha256 under `## Tests` |
| G8 F12 notes | NOT FIXED | `RESULT.md:134-139` / `finalize.py:468-498`: qualitative prose, not per-variant r1→r2→r3 counts, not MFE21_1D<0.001 count, not 5%-trimmed mean |
| Frozen numbers | explained | panel −123 only on 2020-2026; 2014-2019 means bitwise equal; CIs moved from G7; Jaccard from G3; headline Δ 6.979e-05 → 7.038e-05 (expected ≈7.04e-05); NOT SUPPORTED stands |

### Defects (each with the re-check that closes it)

1. **G2 M2a is still vacuous.** Mutant `events = _bullish_cross(macd.shift(-3), sig.shift(-3))` applied; `test_truncation_invariance_real_names` and `test_m2a_forward_peek_mutant_caught` both still PASS (23 passed besides vintage c0 + hashes). Truncation compares only events with `entry+21 ≤ T−30`, so a 3-session peek never crosses the cut. `test_m2a_*` independently shifts MACD and never calls the mutated `_name_events` site. **Close:** apply M2a to a copy; `test_truncation_invariance_real_names` (or a new live look-ahead test) must FAIL; paste that name into RESULT.md `## Tests`.

2. **G2 M2b is still vacuous.** Mutant `spy_index.get_indexer([entry])[0] + 1` applied at both `_outcomes_for_event` sites (n=2); only `test_emitted_c0_matches_basket_at_entry` (same 941/2000 vintage failure as clean) and `test_hashes_verify` fail. `test_m2b_corrupted_entry_index_caught` checks `entry_date`, which this mutant does not change. The c0 test reads the frozen parquet, not a live pipeline emit. **Close:** apply M2b; a live c0/entry-index test must FAIL; paste the name.

3. **G2 RESULT.md never pastes failing-mutant test names.** There is no `## Tests` section; grep for `M2a`/`M2c`/`M6a` is empty. **Close:** RESULT.md `## Tests` contains one failing test name per named mutant.

4. **G4 M6a is not caught.** `drawn = np.full(len(all_months), rng.integers(0, len(all_months)))` applied at both `all_months` sites (n=2). `test_delta_bootstrap_pair_is_month_clustered` and `test_delta_bootstrap_month_indices_vary` still PASS (finite CI only). `test_delta_bootstrap_negative_control_per_event_draw_splits_month` tests `numpy.rng.choice`, not `_delta_bootstrap_pair`. **Close:** apply M6a; a test that calls `_delta_bootstrap_pair` on a 12-month two-arm panel with month-specific shifts, asserting CI width in `[0.5×, 2×]` of the analytic month-cluster SE **and** that a draw's month indices are not constant, must FAIL.

5. **G4 M6b is not caught.** `full_buckets = sizes.index[sizes >= 1]` applied. `test_bucketing_drops_short_buckets` still PASS (`len(events) <= 3*expected_bars + 100` is slack). **Close:** apply M6b; a test that builds a series whose final bucket has size `< n` and asserts `run._build_n_day_bars` **drops** that bucket (bar count, not a loose event bound) must FAIL.

6. **G4 M6c is not caught.** `d=("d", "first")` applied. `test_bar_date_is_last_session_of_bucket` still PASS because consecutive first-of-bucket dates are still 3 sessions apart. Phase-0 close tests compare closes by bucket id, not dates. **Close:** apply M6c; a test that asserts each bar date **equals the last session of its bucket** (not merely that bar-to-bar gaps equal n) must FAIL.

7. **G5 packet M3a cannot be applied, and the production table invert is uncaught.** Exact strings `"1D.M3": (close_1d, 1.0 / 3.0)` and `"3D.K1": (bars["3D.p0"], 3.0)` are NOT_FOUND (n=0). Analog table invert `"1D.M3": (close_1d, 3.0)` + `"3D.K1": (bars["3D.p0"], 1.0 / 3.0)` leaves `K_*` alone; `test_half_life_reads_run_module_constants` still PASS. The test never reads `result.json` half-lives (none exist). Inverting the **constants** does fail the test (M3a_const_both, M3a2_const, M3b). **Close:** (i) packet-or-table M3a applied to a copy must FAIL a named test; (ii) test asserts a half-life table in result.json at 1e-3 sessions.

8. **G6 has no pytest.** `pre_warmup − warmup − horizon21 − outcomes_none − no_entry == panel_n` holds in `result.json`/`summary.json` for every variant, and `no_entry` matches the packet (99/1/62/0/0/47/25/19/2), but `test_B1.py` has no such assert. **Close:** a test that reads `result.json` and asserts the identity for every variant; a mutant that restores a silent `continue` without incrementing `no_entry` must FAIL it.

9. **G7 two-process identity was not reported.** `_build_cell_streams` does `SeedSequence(20261004).spawn(len(sorted_labels))` once per call and remakes the parent SS (so `reset_registry` is no longer sticky). RESULT.md has no `## Tests` with two `result.json` sha256s from separate processes. **Close:** run the stats pipeline twice in two processes; paste both sha256s; they must be identical.

10. **G8 notes are still instructions, not numbers.** `RESULT.md:134-139` says every variant "GREW slightly (+7 to +34)" and "back the denominator floor (MFE21_1D < 0.001) and report the trimmed mean" without doing so. No r1→r2→r3 per-variant table. Recompute from `confirmation_pairs.parquet` ⋈ 1D `mfe21`: 2D.p1 raw mean = −0.187151; n(MFE21_1D < 0.001) = 35502 (of which ≤0: 34178; 0<mfe<0.001: 1324); 5%-trimmed mean = +0.266977. **Close:** finalize.py emits the nine r1/r2/r3 counts and those two 2D.p1 numbers.

11. **G1 wording is inverted, and the 16-row r1→r2 explanation is missing.** Code at `run.py:359` gates h21 on `spy_pos_e + 21 > name_last_pos` and `:360` gates h10 on `+ 10` (h10_bad ⇒ h21_bad, so the drop set equals the +21 gate). Docstring `run.py:277` and Deviations item 10 (`RESULT.md:162`, `finalize.py:56`) still say "e+10 … covers h10 AND h21". RESULT.md never explains FI 9 / NXXT 4 / NFE 3. The +21→+10 mutant **did** fail `test_truncation_invariance_real_names` (AAL new=1), because that test hardcodes `cutoff_pos - 21`. `test_panel_horizons_within_name_data` did **not** fail (reads the frozen panel; also `break`s at 50k of 1.4M rows). **Close:** (i) docstring/deviations say e+**21** covers h21 (and therefore h10); (ii) apply `spy_pos_e + 21 > name_last_pos` → `+ 10` and a **panel-or-pipeline** G1 test fails; (iii) Notes name FI/NXXT/NFE 16-row r1→r2 change.

## EVIDENCE

Workspace B1 = `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/`. Round-2 baseline = `…/scratchpad/results_prev/B1_r2/`. Scratch copies under `SCR/fake` and `SCR/mutants/<id>/` (nested so `run.py`'s 5-parent REPO derivation resolves; `data/yahoo/SPY.parquet` overlaid with `git show 052e02d085b0:data/yahoo/SPY.parquet`).

### Code gate (G1)

`run.py:349-364` (clean):

```
h21_bad = spy_pos_e < 0 or spy_pos_e + 21 > last_spy_pos or spy_pos_e + 21 > name_last_pos
h10_bad = spy_pos_e + 10 > name_last_pos
if h21_bad or h10_bad:
```

Docstring `run.py:277`: `G1: drop events when e+10 SPY exceeds the name's last close (covers h10 AND h21).`

### Per-variant row counts (G1 recompute)

Vintage SPY sha256 `02b1b37acd5f7130…` (matches `hashes.txt`). Manifest last dates from r3 `universe_manifest.json`. Round-2 panel sha256 `ba58e043eaf450a8…` (296,669 1D rows). Stale = `SPY[e+21] > name_last_date`.

```
r3 rows=1406344 r2 rows=1406467 delta=-123
  1D:     r2=296669 r3=296637 delta=-32  stale_r2_h21=32 h10=14
  2D.p0:  r2=148802 r3=148790 delta=-12  stale_r2_h21=12 h10=6
  2D.p1:  r2=148665 r3=148652 delta=-13  stale_r2_h21=13 h10=8
  3D.p0:  r2= 99919 r3= 99912 delta=-7   stale_r2_h21=7  h10=3
  3D.p1:  r2= 99673 r3= 99665 delta=-8   stale_r2_h21=8  h10=4
  3D.p2:  r2= 99710 r3= 99702 delta=-8   stale_r2_h21=8  h10=3
  1D.M2:  r2=151097 r3=151084 delta=-13  stale_r2_h21=13 h10=8
  1D.M3:  r2=101582 r3=101575 delta=-7   stale_r2_h21=7  h10=4
  3D.K1:  r2=260350 r3=260327 delta=-23  stale_r2_h21=23 h10=9
  TOTAL stale_r2 h21=123 h10=59
r3 stale h21=0 h10=0 (full panel, not the 50k test cap)
key-set only_r2=123 only_r3=0
only_r2_top_names NFBK 13, STEL 10, WBS/SEM/RMAX/GTLS/TALK/XOMA 9, …
horizon21 drop counts r2→r3 rose by exactly those 123 (1D 2547→2579, …)
```

Matches the expected 32/12/13/7/8/8/13/7/23 and r3 panel_n 296,637 / 148,790 / 148,652 / 99,912 / 99,665 / 99,702 / 151,084 / 101,575 / 260,327.

Panel shas: r3 events `209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8`; r3 confirm `d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae`. r3 panel gained column `c0`.

### Headline / verdict / Jaccard

```
r2 Δ(3D.p* − 1D.M3) H10 net = 6.979350869048932e-05  CI [-0.00026845, 0.00042102]
r3 Δ(3D.p* − 1D.M3) H10 net = 7.038224133275317e-05  CI [-0.00028765, 0.00041759]
|r3 − 7.04e-05| = 1.78e-08  (packet stop threshold 1e-05)
RESULT.md prints +0.0001 95% CI [-0.0003, +0.0004]
verdict grain_effect_3d/2d/memory_effect_3 = NOT SUPPORTED ×3 (both rounds)
jaccard_tolerant r3: 2D p0-p1=0.565517 (ref 0.5655); 3D 0.573926 / 0.576095 / 0.576585 (ref 0.5739 / 0.5761 / 0.5766)
jaccard exact all 0.0; tolerance_sessions 2D=1, 3D=2
```

G3 unit test passed on baseline. Fixture calendar dates map via `session_positions` to relative sessions `{0,2,3,6}` vs `{0,2,5,12}` (not `{0,3,6,9}` vs `{1,4,8,20}`) but still greedy-match 3 / union 5 = 0.6 with tol=2.

### G6 identity (from result.json; same in summary.json)

```
1D     341020 - 41705 - 2579 - 0 - 99 = 296637
2D.p0  165945 - 16129 - 1025 - 0 -  1 = 148790
2D.p1  165572 - 15885 -  973 - 0 - 62 = 148652
3D.p0  107632 -  7234 -  486 - 0 -  0 =  99912
3D.p1  107233 -  7094 -  474 - 0 -  0 =  99665
3D.p2  107543 -  7316 -  478 - 0 - 47 =  99702
1D.M2  173562 - 21434 - 1019 - 0 - 25 = 151084
1D.M3  116471 - 14379 -  498 - 0 - 19 = 101575
3D.K1  282142 - 19613 - 2200 - 0 -  2 = 260327
```

### G8 2D.p1 outlier (not in RESULT.md)

`confirmation_pairs.parquet` n=1,483,185; join 1D panel `mfe21` on `(name, signal_session_1d)`:

```
2D.p1 n=296637 raw_mean=-0.187151  n_mfe<0.001=35502  n_mfe<=0=34178  n_0<mfe<0.001=1324
      5%-trimmed mean (drop 5% each tail)=+0.266977
2D.p0 raw=+0.046559 trimmed=+0.267040  (same MFE denominator; the −0.187 is a 2D.p1 numerator tail)
```

### Provenance

- `hashes.txt`: 18 lines, `sha256  repo-relative-path` only; no `repo_head` pseudo-entry; no `name=` suffixes; no self-hash of `hashes.txt`.
- Every listed B1 output and engine file matches; live `data/yahoo/SPY.parquet` is `71b5007f5c4e…` vs listed `02b1b37acd5f…` (host-head vintage; `git show 052e02d085b0:data/yahoo/SPY.parquet` hashes to the listed value).
- `result.json` keys include `repo_head=052e02d085b01f29baf499357e224c836d8eb224`; `files.*` are repo-relative; no `timestamp` / `generated_at` / `HH:MM:SS` wall-clock field.
- Old F12 falsehoods "SMALLER because of F4/F8" and "warm-up 100" as **claims** are gone; they remain only as quoted corrections. Jaccard calendar-day method is gone from `stats.py` (session position + union).

### Frozen leaf diff (`result.json` r2 vs r3)

`n_same=409  n_changed=437  n_numeric=420`.

**2014-2019 means and n_events bitwise identical** for all 9 variants (e.g. 1D n=99574 mean_h10_net=-0.004622793056881533). All 123 dropped keys have 2026 entry dates.

Changed leaves, judged:

| class | examples | explained by |
|---|---|---|
| n_events overall & 2020-2026; confirmation.n (−32); horizon21 (+32/12/13/7/8/8/13/7/23) | `variants.1D.overall.n_events` 296669→296637 | −123 G1 rows |
| 2020-2026 means / hit rates / medians (1e-6–1e-5) | `variants.3D.p0.by_era.2020-2026.n_events` 65820→65813 | −123 G1 rows |
| headline Δ 6.979e-05→7.038e-05; CI still straddles 0 | `headline.pooled_across_phases_delta_h10_net` | −123 G1 rows (matches ~7.04e-05) |
| 2014-2019 **CIs only** (means frozen) | `variants.1D.by_era.2014-2019.ci_h10` | G7 seed re-key (in-scope) |
| Jaccard 0.7425/0.7898/0.7931/0.7929 → 0.5655/0.5739/0.5761/0.5766 | `phase_dispersion.*.jaccard_tolerant` | G3 method (in-scope); r2 values were the packet's "wrong" numbers |
| added `drops_per_variant.*.no_entry`; deviations[9..12] | no_entry 99/1/62/0/0/47/25/19/2 | G6 / G1 / G5 / G3 text |
| file shas, `tests` string 16 passed → 25 passed | | regeneration |
| confirmation means ~1e-6 to 1e-5 | `confirmation.2D.p1.mean_mfe_consumed` −0.18709→−0.18715 | −32 1D events |

No unexplained move of a 2014-2019 **mean** or of the mechanical verdict. NOT SUPPORTED stands.

### Mutants

Apply log (`SCR/apply_log.txt`): G1_plus21 n=1 APPLIED; M2a n=1; M2c n=1; M2b n=2; M6a n=2; M6b n=1; M6c n=1; M3a_exact n=0 NOT_FOUND; M3a table analog n=1+1; M3a2_const n=1; M3a_const_both n=1+1; M3b n=2 (`_rma_alpha_for` and `_ema_alpha_for`).

Command: `python3 -m pytest <copy>/code -q -p no:cacheprovider --tb=line`.

Baseline (clean fake, vintage SPY overlay): **`1 failed, 24 passed in 32.08s`**. Sole failure `test_emitted_c0_matches_basket_at_entry` (941/2000) — local basket vintage vs panel `c0`. `test_hashes_verify` **passed**. Subtract this vintage failure (and hashes, which fail on any edited source file) when judging mutants.

| mutant | substantive FAIL (beyond vintage c0 + hashes) | intended test still PASS? |
|---|---|---|
| G1_plus21 (`+21 > name_last_pos` → `+10`) | **`test_truncation_invariance_real_names`** (AAL: missing=0, new=1). 3 failed, 22 passed in 12.52s | `test_panel_horizons_within_name_data` PASS (frozen panel) |
| M2a | **none**. 2 failed, 23 passed in 31.93s | `test_truncation_invariance_real_names` PASS; `test_m2a_forward_peek_mutant_caught` PASS |
| M2b | **none**. 2 failed, 23 passed in 33.92s | `test_m2b_corrupted_entry_index_caught` PASS; c0 test still the vintage 941/2000 |
| M2c | **`test_m2c_corrupted_entry_offset_caught`** (50/50); also `test_m2b_corrupted_entry_index_caught` (627/627). 4 failed, 21 passed in 32.13s | `test_entry_equals_next_spy_session` PASS (frozen panel) |
| M6a | **none**. 2 failed, 23 passed in 33.13s | all three bootstrap tests PASS |
| M6b | **none**. 2 failed, 23 passed in 33.41s | `test_bucketing_drops_short_buckets` PASS |
| M6c | **none**. 2 failed, 23 passed in 33.80s | `test_bar_date_is_last_session_of_bucket` PASS; both phase-0 close tests PASS |
| M3a_exact | NOT_FOUND (no pytest delta vs clean) | — |
| M3a table analog | **none**. 2 failed, 23 passed in 36.21s | `test_half_life_reads_run_module_constants` PASS |
| M3a2_const (`K_3D_K1=1/3`) | **`test_half_life_reads_run_module_constants`** (`K_3D_K1=0.333 ≯ 1`). 3 failed, 22 passed in 28.33s | — |
| M3a_const_both | **`test_half_life_reads_run_module_constants`** (`K_1D_M3=3.0 ≮ 1`). 3 failed, 22 passed in 36.46s | — |
| M3b (`base ** (1/k)`) | **`test_half_life_reads_run_module_constants`** (1D.M3 hl 6.93 vs 62.4). 3 failed, 22 passed in 41.12s | `test_cascade_matches_canon` PASS (k=1) |

G1 +21→+10 G1-mutant line after edit: `h21_bad = … spy_pos_e + 21 > last_spy_pos or spy_pos_e + 10 > name_last_pos` (confirmed in `mutants/G1_plus21/.../run.py:359`).

## GAPS

- Did not re-run the full B1 panel pipeline (hours; would write under `results/B1/`, which is forbidden). G7 two-process `result.json` identity therefore not independently reproduced; only the seed-construction code and the 2014-2019-CI-moved-while-means-frozen pattern were checked.
- `test_emitted_c0_matches_basket_at_entry` fails locally 941/2000 against current `data/baskets/ohlcv` (packet: host 25 passed; local vintage). Did not `git show` every basket to recover host c0. This is **not** counted as a G2 production defect; it **is** why M2b cannot be judged via that test locally.
- Round-1 panel is not in `results_prev`; r1→r2 per-variant counts could not be recomputed here. G8's missing table is judged against RESULT.md contents, not against a recovered r1 parquet.
- The 16 FI/NXXT/NFE value-changed rows are a r1→r2 (F7) story; without the r1 panel they were not re-derived. They are absent from RESULT.md.
- `test_panel_horizons_within_name_data` only walks 50k rows; the reviewer walked the **full** r3 panel (0 stale). The cap is a test-coverage gap, not a remaining stale-row fact.
- MCP `figma` / `linear-server` / `mastermind-executive` were unavailable; not used.

## DEVIATIONS

- Mutants were applied on nested copies under `SCR/mutants/<id>/` (not `SCR/<copy>/code` directly) so `run.py`'s `Path(__file__).parents[5]` REPO derivation and `test_B1.py` panel paths resolve. `data/yahoo/SPY.parquet` in those trees is the host-head vintage from `git show 052e02d085b0:data/yahoo/SPY.parquet`; baskets remain the live worktree (c0 vintage failure).
- Packet M3a/M3a2 exact strings were applied (NOT_FOUND) **and** analogs on the named constants and on the current variant table were also run, because G5 moved k into `K_*`.
- M3b was realized as `return float(1.0 - (base ** (1.0 / k)))` in both `_rma_alpha_for` and `_ema_alpha_for` (the packet named "alpha uses 1/k" without a unique line).
- Vintage c0 / hashes failures were subtracted when deciding whether a mutant was **caught**; hashes always fail on an edited source file and are not a look-ahead/cluster/horizon catch.
- Did not hand-edit RESULT.md or any tracked file. Did not write under `results/`. No git writes, no gh, no ssh, no network.
