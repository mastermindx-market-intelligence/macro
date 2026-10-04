# B1_RETURN — round 4 record + round 5 seat record repair (2026-10-04)

STATUS: DONE (round 4 lane record; round 5 = record-only repair executed by the seat under the continuation law while host2 was unreadable — no number, panel, test or production line changed)

## Frozen bytes (unchanged since round 3)

- `events_panel.parquet` sha256 `209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8` (296,637 1D rows)
- `confirmation_pairs.parquet` sha256 `d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae`
- `result.json` sha256 `e480d73a06b1fe01ebbd67ce4c80f1e83b08466d0f82a4b82f03955fc0dd4d09` (round 4 final record; verdict leaves identical to round 3 `0deef95b…`: grain_effect_3d / grain_effect_2d / memory_effect_3 all NOT SUPPORTED; pooled Δ(3D.p* − 1D.M3) H10 net +7.038e-05 [−2.876e-04, +4.176e-04])
- `result_partial.json` sha256 `192da18996b8e46bc32d5bc5f98821b4a09eedc4317c17749a34a8a1fa25af7f` (stats stage; reproduced by two independent `stats.py` processes on copies of this tree, see L8)

## L1..L11 — each FIXED, with file:line (independently confirmed by the round-4 grok-4.6 review)

| item | status | production site | named test (code/test_B1.py) | mutant that fails it |
|---|---|---|---|---|
| L1 live look-ahead in `_name_events` | FIXED | `code/run.py:163` (`_name_events`, true-cross site ~:176) | `:820 test_live_lookahead_name_events_true_cross` | M2a, M2c |
| L2 outcomes anchored at the entry index | FIXED | `code/run.py:242` (`_outcomes_for_event`, entry index :255/:261) | `:847 test_outcomes_anchored_at_entry_position` | M2b |
| L3 month-cluster bootstrap, non-constant draws | FIXED | `code/stats.py:392` and `:627` (`rng.integers(0, len(all_months), …)`) | `:882 test_delta_bootstrap_pair_cluster_se_and_nonconstant_draws` | M6a |
| L4 short buckets dropped (size == n) | FIXED | `code/run.py:105` (`_build_n_day_bars`, `sizes == n` :121) | `:156 test_bucketing_drops_short_buckets` | M6b |
| L5 bar date == last session of the bucket | FIXED | `code/run.py:125` (`d=("d","last")`) | `:172 test_bar_date_is_last_session_of_bucket` | M6c |
| L6 half-life table from the k constants | FIXED | `code/run.py:57-59` (`K_1D_M2`, `K_1D_M3`, `K_3D_K1`), `:90 half_life_table` | `:928 test_half_life_table_matches_constants_and_record`, `:950 test_production_variant_table_uses_k_constants_not_inverted_literals`, `:548 test_half_life_reads_run_module_constants` | M3a-table, M3a_const, M3b |
| L7 drop identity (no_entry 99/1/62/0/0/47/25/19/2) | FIXED | `code/run.py:194-196` and `:202-204` (both `no_entry` increments) | `:980 test_drop_identity_result_json`, `:1001 test_no_entry_incremented_on_terminal_session_cross` | G6 |
| L8 two-process identity | FIXED (round 5) | stats stage: `result_partial.json` `192da189…` ×2 processes; final file `result.json` `e480d73a…` written by `finalize.py` (fold explained in RESULT.md ## Tests) | `:700 test_hashes_verify` | — |
| L9 notes are numbers recomputed from `confirmation_pairs.parquet` | FIXED | `code/finalize.py:114` (`_compute_confirmation_mfe_notes`), `:554-599` (RESULT.md rendering) | round-4 review independent recompute (35,502 = 34,178 ≤ 0 + 1,324 in (0, 0.001); 2D.p1 raw −0.187151 / trimmed +0.266977) | — |
| L10 horizon gate literal `+ 21`, full-panel walk | FIXED | `code/run.py:139-151` (`_horizon_exceeds_name`) | `:1018 test_horizon_gate_uses_21_not_10`, `:661 test_panel_horizons_within_name_data` | G1 (+21→+10) |
| L11 mutant → failing-test table | FIXED | `code/mutant_results.json`; RESULT.md ## Tests | 11/11 mutants fail at least one named test (round-4 review re-ran every mutant) | — |

## L8 closure (round 5)

The lane's printed pair `ad3f1651…` was the sha256 of a pre-fold `result.json` and is not reproducible from the shipped files; the shipped record cannot contain its own sha256. The reproducible statement is the stats-stage identity above (`192da189…` from two independent `stats.py` processes, equal to the shipped `result_partial.json`), plus the explicit fold: `finalize.py` → `result.json` `e480d73a…` (hashed final file). RESULT.md ## Tests carries the same note.

## Round 5 provenance (seat)

- Executed by the seat (session f273dd7d) on 2026-10-04 while `/Volumes/Mastermind` (host2) hung on every read; inputs were the seat worktree's byte-identical mirror of the round-4 lane tree (parquet shas above), `engine/` and `lib/` from the seat worktree (engine shas equal to the hashes.txt pins), and `data/yahoo/SPY.parquet` fetched from git at `052e02d085b0` (sha256 `02b1b37acd5f7130e286780869a47307893a06c8d150c5cbb4f9bc1184602187`, equal to the pin).
- Files changed in round 5: `RESULT.md` (L8 note only), this `B1_RETURN.md` (new), `code/hashes.py` (two paths added to its fixed output list: `result_partial.json`, `B1_RETURN.md`), `hashes.txt` (regenerated last). `result.json`, both parquets, `summary.json`, `code/run.py`, `code/stats.py`, `code/finalize.py`, `code/test_B1.py`, `code/mutant_results.json` are byte-unchanged.
- Re-check used: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest code/test_B1.py -q -p no:cacheprovider` on a copy of this tree (count below), then `python3 code/hashes.py` last.
- pytest (round 5 copy): 29 passed, 2 failed, 3 skipped on the seat copy — the 2 failures (`test_truncation_invariance_real_names`, `test_emitted_c0_matches_basket_at_entry`) and 3 skips (`AAPL.parquet missing`) are environment-only: the seat copy has no `data/baskets/ohlcv` (sparse mirror; the primary checkout's basket is a later nightly vintage and does not match the manifest shas). `test_hashes_verify` passes on the regenerated manifest. The round-4 lane recorded 34 passed on host2 with the full basket and the round-4 review reproduced 34 passed; the seat re-runs the full suite on host2 once `/Volumes/Mastermind` is readable again and records that count in the W1 handoff.
