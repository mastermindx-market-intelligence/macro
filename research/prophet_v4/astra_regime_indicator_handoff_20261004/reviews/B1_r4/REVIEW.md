# B1 ROUND 4 independent review

## STATUS

PASS (review completed; all items below were checked)

## RESULT

**Recommended ruling: REQUEST_REPAIR**

Panel bytes and frozen numeric leaves are unchanged (NOT SUPPORTED × 3; pooled Δ(3D.p* − 1D.M3) H10 net +7.038e-05 [−0.000288, +0.000418]). L1–L7, L9–L11 live tests exist and the named mutants fail them. Two record items are not closed: L8 (two-process shas are not the finally written `result.json` and fold-counts is not explained) and the on-disk return (no L1..L11 FIXED with file:line).

### Per-item verdicts

| item | verdict | file:line |
|---|---|---|
| Frozen bytes | FIXED | `results/B1/events_panel.parquet`, `confirmation_pairs.parquet`; `result.json` `files.*_sha256` / `headline` / `verdict` / `variants` / `contrasts` |
| L1 live look-ahead | FIXED | `code/test_B1.py:820` `test_live_lookahead_name_events_true_cross`; production `code/run.py:176` |
| L2 live entry-index | FIXED | `code/test_B1.py:847` `test_outcomes_anchored_at_entry_position`; production `code/run.py:255` and `:261` |
| L3 month-cluster bootstrap | FIXED | `code/test_B1.py:882` `test_delta_bootstrap_pair_cluster_se_and_nonconstant_draws`; production `code/stats.py:392` and `:627` |
| L4 short-bucket drop | FIXED | `code/test_B1.py:156` `test_bucketing_drops_short_buckets`; production `code/run.py:121` |
| L5 bar date == last session | FIXED | `code/test_B1.py:172` `test_bar_date_is_last_session_of_bucket`; production `code/run.py:125` |
| L6 half-life table | FIXED | `result.json` `half_life_sessions`; `code/test_B1.py:928` / `:950`; production `code/run.py:58-59`, `:399-400` |
| L7 drop identity | FIXED | `code/test_B1.py:980` `test_drop_identity_result_json`; live increment `code/test_B1.py:1001`; production `code/run.py:194-196` |
| L8 two-process identity | PARTIAL | `RESULT.md:183`; live `result.json` sha `e480d73a…` ≠ printed pair `ad3f1651…` |
| L9 notes are numbers | FIXED | `RESULT.md:134-152`; `code/finalize.py:114-137`, `:554-599` |
| L10 wording + full-panel walk | FIXED | `code/run.py:140-151`, `:337-338`; `code/finalize.py:75` (Deviations item 10); `code/test_B1.py:661` `test_panel_horizons_within_name_data`; G1 mutant site `code/run.py:148,150`; named G1 test `code/test_B1.py:1018` |
| L11 mutant → failing-test table | FIXED | `RESULT.md:165-181`; `code/mutant_results.json`; all 11 named mutants fail at least one named test |
| Provenance + write order | PARTIAL | `result.json` `provenance.*`; `RESULT.md:186-188`; `hashes.txt` (20/20 OK from repo root). Missing on-disk L1..L11 FIXED with file:line |

### Defects (each with closing re-check)

1. **L8 — two-process shas are not the finally written record.** `RESULT.md:183` prints identical `ad3f1651333b1744a2edfaf6ee5340f25ef6a5c2ce9fce216e84762a32b11a06` / same, labelled “stats-pipeline sha256”. Live `results/B1/result.json` sha256 is `e480d73a06b1fe01ebbd67ce4c80f1e83b08466d0f82a4b82f03955fc0dd4d09` (also the hashes.txt entry). No fold-counts rewrite explanation. **Re-check that closes it:** either (a) run the stats+finalize path that produces the *finally written* `result.json` in two processes, paste those two sha256 values, and have them equal `e480d73a…`, or (b) keep the stats-pipeline pair *and* state in `RESULT.md` ## Tests that finalize/fold (half-life table, confirmation_mfe_notes, mutant_tests, provenance, tests summary, deviations item 14) rewrites the record from `ad3f1651…` → `e480d73a…`, with the latter being the hashed final file.

2. **Return packet does not carry L1..L11 FIXED with file:line.** `RESULT.md` has a mutant table and an unchanged-panel deviations item (14) but no `L1 FIXED <file:line>` … `L11 FIXED <file:line>` list. No `B1_RETURN` block is on disk under `results/B1/`. **Re-check that closes it:** `RESULT.md` (or a captured `B1_RETURN` written under `results/B1/`) lists L1..L11 each `FIXED` with file:line and the statement that `events_panel.parquet` / `confirmation_pairs.parquet` shas are unchanged (`209e2246…` / `d20cd405…`).

## EVIDENCE

### Environment

`/opt/homebrew/bin/python3` 3.14.7; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1.

Checkout: `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7` (read-only). Tests ran only on copies under this scratchpad.

### Frozen parquet shas

```
shasum -a 256 results/B1/events_panel.parquet results/B1/confirmation_pairs.parquet
209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8  …/results/B1/events_panel.parquet
d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae  …/results/B1/confirmation_pairs.parquet
```

Round-3 preserved copies print the same two shas. Required freeze values match exactly.

`result.json` `files.events_panel_sha256` / `files.confirmation_pairs_sha256` equal those values in both r3 and r4.

### `result.json` leaf-diff vs r3 (`0deef95be1c1…` → `e480d73a06b1…`)

Flattened leaves: prev=829, cur=959, same=827, **changed=2**, **added=130**, **removed=0**.

Frozen-root walk of `variants`, `phase_dispersion`, `contrasts`, `confirmation`, `verdict`, `headline`, `n_names_*`, `drops_per_variant`, `pre_warmup_counts`, `files`, `repo_head`, `lane`, `warmup_sessions`: **0 changed/added/removed**. Headline identical: `pooled_across_phases_delta_h10_net = 7.038224133275317e-05`, CI `[-0.00028764647875340987, 0.00041759000819275216]`. Verdicts identical: `grain_effect_3d` / `grain_effect_2d` / `memory_effect_3` = `NOT SUPPORTED`.

**CHANGED (2), both admissible wording/tests:**

| leaf | r3 | r4 | class |
|---|---|---|---|
| `tests` | `'25 passed in 17.01s'` | `'34 passed'` | tests/mutant table (counts-only rewrite) |
| `deviations` | 13 strings; item 10 said “entry + **10** SPY sessions … covers h10 AND h21 since e+21 > e+10” | same 1–9, 11–13; item 10 rewritten to “entry + **21** … covers h21, and therefore h10, since h10_bad ⇒ h21_bad”; item 14 added (round-4 freeze note) | wording |

**ADDED (130), all admissible:**

- `half_life_sessions.{1D,2D.p0,2D.p1,3D.p0,3D.p1,3D.p2,1D.M2,1D.M3,3D.K1}` (sessions, ~1e-3 of 20.792 / 41.585 / 62.377)
- `confirmation_mfe_notes.*` (`n_1d_events_mfe_lt_0_001=35502`, `n_1d_events_mfe_le_0=34178`, `n_1d_events_mfe_between_0_and_0_001=1324`, `p1_raw_mean_mfe_consumed=-0.1871509171936404`, `p1_trim05_mean_mfe_consumed=0.2669771064884692`, `p1_n_finite_consumed=133491`)
- `round_panel_n.r1|r2|r3.{9 variants}`
- `mutant_tests.*` (11 mutants + details + `l8_sha_a/b` + `pytest_summary_counts`)
- `provenance.{host,python,python_version,pandas,numpy,pyarrow,scipy,pytest}`

No numeric leaf of variant means / CIs / deltas / verdicts changed.

### hashes.txt

From repo root:

```
cd <checkout> && shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/hashes.txt
```

20 lines, **0 non-OK**, 20 `: OK`. Paths are repo-relative (`engine/…`, `data/yahoo/SPY.parquet`, `research/prophet_v4/…/results/B1/…`). No `repo_head` pseudo-entry, no `name=` suffixes.

Timestamps (local): `events_panel.parquet` / `confirmation_pairs.parquet` 2026-10-03 20:44:58 (frozen); `code/run.py` 00:45; `result.json` / `RESULT.md` / `hashes.txt` 2026-10-04 00:50:42; `DONE` 00:51:30. `hashes.txt` is newest among hashed artifacts; `DONE` is the lane sentinel after it.

### Clean suite (copy under SCR, `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest <copy> -q -p no:cacheprovider`)

```
..................................                                       [100%]
34 passed in 27.25s
```

Wall-time-free counts: **34 passed**. Matches `RESULT.md` / `result.json` `tests` = `34 passed`.

### L1–L7, L10 mutants (applied with python string replace on copies; never on the delivered tree)

| mutant | site mutated | first fail under suite `-x` | named test (if different) | summary (counts) |
|---|---|---|---|---|
| M2a | `run.py:176` `events = _bullish_cross(macd.shift(-3), sig.shift(-3))` | `test_live_lookahead_name_events_true_cross` | same | 1 failed, 25 passed |
| M2b | `run.py:255` and `:261` `get_indexer([entry])[0] + 1` | `test_outcomes_anchored_at_entry_position` | same | 1 failed, 26 passed |
| M2c | `run.py:197` `spy_index[min(i + 2, …)]` | `test_m2b_corrupted_entry_index_caught` | `test_live_lookahead_name_events_true_cross` also **FAILED** when selected: `entry_date 2016-12-05 != … 2016-12-02` | 1 failed, 9 passed (`-x`); named 1 failed |
| M3a-table | `run.py:399-400` `"1D.M3": (close_1d, 3.0)` + `"3D.K1": (bars["3D.p0"], 1.0 / 3.0)` | `test_production_variant_table_uses_k_constants_not_inverted_literals` | same | 1 failed, 29 passed |
| M3a_const | `run.py:58-59` `K_1D_M3=3.0`, `K_3D_K1=1/3` | `test_half_life_reads_run_module_constants` | also `test_half_life_table_matches_constants_and_record`, `test_production_variant_table_uses_k_constants_not_inverted_literals` (**3 failed**, 31 deselected) | 1 failed, 15 passed (`-x`) |
| M3b | `cascade_lib.py` `_rma_alpha_for` + `_ema_alpha_for`: `base ** (1.0 / k)` | `test_half_life_reads_run_module_constants` (`1D.M3 half-life should be 62.4, got 6.93`) | also `test_half_life_table_matches_constants_and_record`; production-table source test passed | 1 failed, 15 passed (`-x`); named pair 2 failed, 1 passed, 31 deselected |
| M6a | `stats.py:392` and `:627` `drawn = np.full(len(all_months), rng.integers(0, len(all_months)))` | `test_delta_bootstrap_pair_cluster_se_and_nonconstant_draws` | same | 1 failed, 27 passed |
| M6b | `run.py:121` `sizes >= 1` | `test_bucketing_drops_short_buckets` | same | 1 failed, 3 passed |
| M6c | `run.py:125` `d=("d", "first")` | `test_bar_date_is_last_session_of_bucket` | same | 1 failed, 4 passed |
| G1 +21→+10 | `run.py:148,150` `spy_pos_e + 10` | `test_truncation_invariance_real_names` | `test_horizon_gate_uses_21_not_10` also **FAILED**: `assert False is True` on `_horizon_exceeds_name(1000, 5000, 1015)` | 1 failed, 5 passed (`-x`); named 1 failed |
| G6 continue | `run.py:194-196` silent `continue` without `no_entry += 1` | `test_no_entry_incremented_on_terminal_session_cross` | same | 1 failed, 31 passed |

L1 test (`test_B1.py:820`) imports production `_name_events`, plants a synthetic 1D close + macd/sig with a single true cross at session 500, asserts emitted `signal_date` / `entry_date` equal the true cross / next session. M2a fires three sessions early → FAIL.

L2 test (`test_B1.py:847`) calls production `_outcomes_for_event` on a series where `close[entry+1] ≠ close[entry]` and asserts `c0` / `excess_h10` / `excess_h21` equal the entry-anchored values.

L3 test (`test_B1.py:882`) calls `_delta_bootstrap_pair` on a 12-month two-arm panel with month-specific shifts; asserts CI width in `[0.5×, 2×]` of analytic month-cluster 95% width and `_LAST_PAIR_DRAWN` not constant.

L4 exact bar count: `n=3`, `n_sessions=10` → `len(bars) == 3`. L5 asserts each bar date is the last session of its size-`n` bucket and the first session is *not* in the index.

Packet M3a strings `"1D.M3": (close_1d, 1.0 / 3.0)` / `"3D.K1": (bars["3D.p0"], 3.0)` **do not exist** as production literals. Production lines that play their role: `run.py:399` `"1D.M3": (close_1d, K_1D_M3)` and `run.py:400` `"3D.K1": (bars["3D.p0"], K_3D_K1)` with `K_1D_M3 = 1.0 / 3.0` (`run.py:58`) and `K_3D_K1 = 3.0` (`run.py:59`). Stated in `run.py:61-63` and `test_B1.py:950-954`.

`test_panel_horizons_within_name_data` (`test_B1.py:661-694`) walks the **full** panel (`n_check = len(panel)`); no 50k `break`. Clean suite included this test (34 passed).

### L8

Printed in `RESULT.md:183`:

```
L8 two-process stats-pipeline sha256: `ad3f1651333b1744a2edfaf6ee5340f25ef6a5c2ce9fce216e84762a32b11a06` / `ad3f1651333b1744a2edfaf6ee5340f25ef6a5c2ce9fce216e84762a32b11a06`
identical
```

Live:

```
shasum -a 256 results/B1/result.json
e480d73a06b1fe01ebbd67ce4c80f1e83b08466d0f82a4b82f03955fc0dd4d09
```

The two values are identical to each other and to `result.json` `mutant_tests.l8_sha_a/b`. They are **not** the live record. Label “stats-pipeline” is not a fold-counts rewrite explanation.

Did not re-run `stats.py` / `finalize.py` / `run.py` against the checkout (they write `result_partial.json` / `result.json` / `RESULT.md` under `RESULTS_DIR` with no output-directory override). Independent two-process reproduction of `ad3f1651…` is a GAP (below).

### L9 independent recompute

Source: r3 preserved `confirmation_pairs.parquet` (sha `d20cd405…`) joined to r3 `events_panel.parquet` 1D `mfe21` on `(name, signal_session_1d)`. Confirmation file has no `MFE21_1D` column (`mfe21_consumed_frac` only).

**MFE21_1D < 0.001 counts** (unique 1D events = 296,637; equivalently panel 1D `mfe21`):

| predicate | n |
|---|---:|
| `mfe21 < 0.001` | **35,502** |
| `mfe21 <= 0` | **34,178** |
| `0 < mfe21 < 0.001` | **1,324** |

Joined pair rows (5 variants × 1D events = 1,483,185) scale 5× (177,510 / 170,890 / 6,620). Notes correctly count 1D events, “hence on every variant's pair rows”.

**2D.p1 `mfe21_consumed_frac`:** `n_rows=296637`, `n_finite=133491` (NaNs dropped — non-positive MFE21_1D).

- raw mean = **−0.187150917194** (record −0.1871509171936404; abs diff < 1e-12)
- 5%-trimmed mean, `scipy.stats.trim_mean(x, 0.05)` = **+0.266977106488** (record +0.2669771064884692)
- same value from manual `sort` then drop `floor(0.05 * n)` = 6,674 observations from each tail

Trimming convention: **5% from each tail of the finite consumed-frac vector** (`proportiontocut=0.05`), not 5% total. Matches the record and the packet reference (−0.187151 / +0.266977) to the printed 6 decimals.

r3 panel_n from the parquet: 296637 / 148790 / 148652 / 99912 / 99665 / 99702 / 151084 / 101575 / 260327. Notes table matches. Drop identity `no_entry` 99/1/62/0/0/47/25/19/2 matches `test_B1.py:974-977` and `RESULT.md:22-30`.

### L10 wording

- `run.py:140-151` `_horizon_exceeds_name`: “e+21 covering h21 also covers h10, since (e+10 > name_last) ⇒ (e+21 > name_last)”. Literal `+ 21` at `:148` and `:150`.
- `run.py:337-338` `_per_name_full` docstring: “covers h21, and therefore h10, since h10_bad ⇒ h21_bad”.
- `finalize.py:75` Deviations item 10: same wording. `RESULT.md` deviations item 10 matches.
- Notes (`RESULT.md:153`): “The 16 value-changed rows between round 1 and round 2 (FI 9 / NXXT 4 / NFE 3) are the F7 story”.

### L11 table vs this review

Lane table (`RESULT.md:167-179`) names a failing test for all 11 mutants. Independent runs confirm each mutant fails a test; for M2c and G1 the *first* failure under full-suite `-x` is an earlier test than the lane’s targeted selection, but the lane’s named test also fails when selected. Counts-only summaries above (wall time stripped).

### Provenance

`result.json` `provenance`: `host=m2`, `python=/opt/homebrew/bin/python3`, `python_version=3.14.7`, pandas 3.0.5, numpy 2.5.2, pyarrow 25.0.1, scipy 1.18.0, pytest 9.1.1.

`RESULT.md:186-188` ## Provenance prints the same host + five library versions.

No on-disk `L1 FIXED …` … `L11 FIXED …` list.

## GAPS

1. **Stdout `B1_RETURN` packet** was not captured under `results/B1/` (or anywhere this reviewer may write). Cannot verify whether the lane printed L1..L11 FIXED with file:line to stdout. On-disk `RESULT.md` does not contain that list (defect 2).
2. **L8 two-process sha `ad3f1651…` not independently reproduced.** Reproducing it requires running the stats pipeline, which writes `result_partial.json` (and finalize writes `result.json` / `RESULT.md`) with no output-directory override. Packet forbids running `run.py` against the checkout; the same write-path applies to `stats.py` / `finalize.py`. Did not run them. The live-vs-printed sha mismatch is still observed from the files.
3. **G6 second silent-continue site** (`run.py:202-204`, name stopped trading) was not mutated separately. The packet’s mutant is “a silent `continue` without bucket increment”; the terminal-session site (`run.py:194-196`) was the one applied, and `test_no_entry_incremented_on_terminal_session_cross` failed. The identity test reads the frozen record and would not fail from a code-only mutant.

## DEVIATIONS

1. Tests were not executed from `results/B1/code/` (would derive `RESULTS_DIR` as the live lane directory). Copies lived under `SCR/tree/research/prophet_v4/astra_regime_indicator_handoff_20261004/results/B1/` (and `mut_*` siblings) so `run.py`’s five-parent `REPO` derivation resolved; `engine/` and `data/` were **symlinked read-only** from the checkout; panel/json records were **copied** (not symlinked) so a stray write could not mutate the shared tree. `B1_REPO` pointed at the checkout so `test_hashes_verify` hashed the live files.
2. Did not run `run.py`, `stats.py`, `finalize.py`, or `hashes.py` against the checkout or in a way that could rewrite `results/B1/`.
3. Mutants used python `str.replace` on copies (equivalent to the packet’s sed). M3b inverted **both** `_rma_alpha_for` and `_ema_alpha_for` (`base ** (1.0 / k)`). M6a was applied at both `all_months` sites (`stats.py:392` and `:627`), not the third `len(months)` site at `:161`.
4. Full suite run once on the clean copy; each mutant then with `-x`. Named tests for M2c and G1 were re-run selected because `-x` stopped on an earlier failure. Wall times appear in raw pytest output; counts above are stripped.
5. L9 pair counts used a pandas merge of `confirmation_pairs.parquet` onto panel 1D `mfe21` because the pairs file has no `MFE21_1D` column. Unique-1D and panel-1D counts agree.
6. No git / gh / ssh / network. Scratch writes only under `SCR`.
