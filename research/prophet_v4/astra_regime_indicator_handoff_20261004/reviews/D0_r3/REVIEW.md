# D0 ROUND 3 independent review

Checkout (read-only): `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7` detached `052e02d085b0`.
Lane record: `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/`.
Scratch: this directory. No writes under the checkout. `run.py` / `census.main()` were not executed.

## STATUS

PASS

Review completed every listed item (frozen greps, fake-`gh` pytest, citation `sed -n`, I3/I4/I6/M1 mutants, `shasum -c` from repo root, I8 leaf-diff recompute against `prior/round2_result.json`).

## RESULT

**REQUEST_REPAIR**

Round-3 closed the I1 label, I3 fail-able reason, I4 write-time cites, I5 hash coverage, I6 `matches_disk` derivation, I7 week-33 marker, H1–H6 pins, and the I2 snapshot/no-network pytest path. It did **not** keep every frozen number byte-identical to round 2 / the seat list, did **not** print two consecutive `main()` `result.json` shas, and the I8 emitted round-2→3 list is truncated and contains 61 numeric leaves.

Live `result.json` sha256: `b16f444ad83741d04d0e2f8cf85fc134d1566e93ea087844c5aa05d5e2d6bd7e` (matches `hashes.txt` and RESULT.md fold sha).
As-found round-2 sha256: `c4b0241f5622656e7bb79cc9e6080a895f5a503c57b8b20fca67c859119ddd61` (printed; equals `prior/round2_result.json`).

### Per-item verdict

| Item | Verdict | file:line |
| --- | --- | --- |
| Frozen numbers | NOT FIXED | `result.json:1182-1183` (`start=2026-07-05`, `end=2026-10-01` not `2026-10-03`); `result.json:1586-1588` (last change-point date `2026-10-01` n=932, no `2026-10-03`); `result.json:3350-3397` (`frozen_number_guard.n_moved=2`); `RESULT.md:3,341,394,452-457` |
| I1 context_history honest_start | FIXED | `census.py:38 CONTEXT_HISTORY_FIRST_WRITE`; `census.py:1078 census_context`; `result.json:685` `honest_start=2026-07-19`; `result.json:687-696` BACKFILLED/PIT_HONEST split; `RESULT.md:25,42,95,450`; leading join `result.json:1625` / `RESULT.md:32,248` still `2026-08-13`. No residual **honest_start** of `2026-06-18` (only `date_min` / `before`). |
| I2 no-network reproducibility | PARTIAL | Snapshot `gh_evidence.json:1-10` (`until=2026-10-02T07:02:07Z` = HEAD committer date); pinned `hashes.txt:2845`; readers `census.py:204 load_gh_evidence`, `census.py:2058 collect_write_time_commits`; writer only `census.py:280 ensure_gh_evidence` → `census.py:233 ["gh","api",…]`. Fake-`gh` pytest: **29 passed**. Missing: two consecutive `main()` shas in `RESULT.md` ## Tests (only one fold sha at `RESULT.md:413`). |
| I3 a test that can fail | FIXED | Builder+fallback `census.py:314-334`; applied at `census.py:2377`; tests `test_d0.py:347` and `test_d0.py:356`. Blank-snapshot mutant: named test **FAILED** with reason `evidence unavailable`. |
| I4 citations | FIXED | Renderer `census.py:98 cite_function` (`inspect.getsourcelines`); `census.py:2218 build_repair_items`; assert `test_d0.py:391`. Every round-1/2/3 `file:line` `sed -n`'d; **0 real misses** (see EVIDENCE). Mutating I1 cite to `census.py:1` **FAILED** the test. |
| I5 hashes coverage | FIXED | `census.py:3212 CENSUS_READ_TARGETS` (31 paths, all present in `hashes.txt`); grep-only named at `census.py:2146` / `RESULT.md:506-522`; `touch_opened_inputs` `census.py:2165`. `shasum -a 256 -c hashes.txt` from repo root: **2848 OK, 0 non-OK**. `hashes.txt` 02:12:06, `DONE` 02:13:10. |
| I6 matches_disk from disk_result | FIXED | `census.py:2008-2014` `matches_disk=bool(derived)` from `disk_result` needles; `test_d0.py:378`. Flip `disk_result` on a copy → test **FAILED** (`True is False`). |
| I7 ISO week 33 | FIXED | `census.py:549,604` status `BEFORE_HONEST_START`; `result.json` week 33 `status=BEFORE_HONEST_START` dates `2026-08-12,2026-08-13`; `RESULT.md:282,291`; `test_d0.py:315`. |
| I8 changed-key lists | PARTIAL | Emitter `census.py:167 leaf_diff` (used). Recomputed r2→r3 from `prior/round2_result.json`: n_added=1227, n_removed=35, n_changed=169, **n_numeric=61**, n_label=108. Includes `sources[8].honest_start` 06-18→07-19 and `provenance.host.*`. Truncated `added[:80]` is self-keys of `changed_keys.round1_to_round2.added[i]` — **omits** `provenance.host` / `gh_evidence`. Violates “NO numeric leaf”. |
| H1 | FIXED | `census.py:517 honest_in_force_names`; `census.py:1650 compute_honest_window`; `census.py:3327 _mutate_m1`; `test_d0.py:241,252,262`. Reviewer M1 mutant: **3 failed** (`test_honest_window_computed_once_and_used_for_verdict`, `test_honest_change_points_pinned`, `test_in_force_from_tree_and_snapshot_only`), 1 passed (`test_d_star_is_exactly_2026_07_05`). |
| H2 | FIXED | `census.py:3255 write_hashes`; `census.py:3394 main` last write `write_hashes` at `census.py:3433-3434`. |
| H3 | FIXED | `census.py:3394` folds pytest then `render_result_md`; `RESULT.md:413` is the fold sha, not a hand edit of a different value. |
| H4 | FIXED | `census.py:2058 collect_write_time_commits`; `census.py:1216 census_tree_history`; `census.py:314 tree_pit_class_reason_from_commits`; reason built from snapshot commits (I3). |
| H5 | FIXED | `census.py:494 PER_DATE_IN_FORCE_SEMANTICS`; `census.py:767 census_edges`; edges clock “BACKFILLED source; excluded from the honest series”. |
| H6 | FIXED | `census.py:2026 run_disk_command`; `census.py:549 iso_week_leading_table`; `engine/theme_graph/local_sources.py:8-18` quoted. |
| Provenance | FIXED | `result.json:3333-3348` `provenance.host` hostname `m2studio` + versions + rerun notice naming `rs_20261004T051657Z_81412`; `RESULT.md:524-530` ## Provenance. |

### Defect list

1. **Frozen numbers moved vs round-2 / seat list.** Observed `honest_window.end=2026-10-01` (round-2 and seat list: `2026-10-03`); last change-point date is `2026-10-01` n=932 (seat list: `2026-10-03=932`); ISO week 40 dates `['2026-09-30','2026-10-01','2026-10-02']` / max N 134 / cov 0.051638 / max date `2026-10-02` → `['2026-09-30']` / 108 / 0.041618 / `2026-09-30`; observed-clock weeks 90 / 12.8571 → 88 / 12.5714; plus 55 other numeric leaves (source row counts, `weeks_start_to_Estar`, etc.). Cause on this host: `data/theme_graph/_meta.json` `belief_time=2026-10-01` and assume-unchanged (`git ls-files -v` = `H`) working copies of history tapes, not a rewrite of the census definitions. Lane recorded only two guard leaves and continued. **Re-check that closes it:** (a) `honest_window.end` and `change_points` dates/Ns byte-equal the seat list (end `2026-10-03`, `10-03=932`); (b) ISO week 33–40 min/max/dates equal `prior/round2_result.json` except the I7 `status` field; (c) `frozen_number_guard.n_moved==0`; (d) r2→r3 `leaf_diff` `n_numeric_changed==0` for census leaves (not `changed_keys.*` metadata). If the working copies cannot produce those numbers, STOP with both values as DEVIATION and do not publish a moved record as FIXED.

2. **I2 two consecutive `main()` shas not printed (and not independently re-run).** `RESULT.md` ## Tests / ## Reproducibility prints one fold sha `b16f444a…` and the round-1 sha `6ed2c879…`, not two identical consecutive-`main()` shas. `census.main()` / `run.py` have no output-directory override; this review did not run them (would rewrite `results/D0/`). In-process `test_result_json_byte_identical_across_two_builds` passed. **Re-check that closes it:** `RESULT.md` ## Tests contains two identical sha256 strings, each equal to `shasum -a 256 results/D0/result.json`, produced by two consecutive `main()` runs that write into a non-checkout output dir (or an added override).

3. **I8 emitted round-2→3 list is truncated and contains numeric leaves.** `leaf_diff` cap=80; `added` is dominated by nested `changed_keys.round1_to_round2.added[i]`; required `provenance.host` / `gh_evidence` keys are absent from the printed 80; `n_numeric_changed=61`. **Re-check that closes it:** untruncated (or filtered-to-payload) code-emitted list includes `sources[…themes_context_history].honest_start` (06-18→07-19), `provenance.host.*`, and `write_time_commits.source`/`gh_evidence`, and `n_numeric_changed==0` once defect 1 is closed.

No other I/H item failed its local re-check.

## EVIDENCE

### Environment / identity

```
python 3.14.7  pandas 3.0.5  numpy 2.5.2  pyarrow 25.0.1  scipy 1.18.0  pytest 9.1.1
HEAD 052e02d085b01f29baf499357e224c836d8eb224  committer 2026-10-02 07:02:07 +0000
LIVE result.json sha256 b16f444ad83741d04d0e2f8cf85fc134d1566e93ea087844c5aa05d5e2d6bd7e
prior/round2_result.json sha256 c4b0241f5622656e7bb79cc9e6080a895f5a503c57b8b20fca67c859119ddd61
prior/round1_result.json sha256 6ed2c8799dc622f76662b1c6c352be47c08ab9ec7746c0ef5f8ddafb893bcf18
gh_evidence.json sha256 72f3bb6d7ff498dab814f822b0f3f09f50fcc1cbea7483d58ce8ea3eda450967
hashes.txt sha256 cea2d5a0c84e3355fe11cf586b0fb6957d27c2732413f457bea5c7583de84cfd
```

`data/theme_graph/_meta.json` now: `belief_time 2026-10-01`, `computed_at 2026-10-01T18:13:29Z`.
`git ls-files -v`: `H` (assume-unchanged) on `_meta.json`, `context_history.jsonl`, `theme_state.json`, `tree_history.jsonl`, `edges.parquet`.

### Frozen numbers (grep quotes)

Seat list vs observed:

| Frozen leaf | Seat / r2 | r3 observed | Quote |
| --- | --- | --- | --- |
| honest window | 2026-07-05→2026-10-03 | 2026-07-05→**2026-10-01** | RESULT.md:3 `the honest window is **2026-07-05 → 2026-10-01**`; RESULT.md:11 `Honest end E* = 2026-10-01`; result.json:1182-1183 `"start": "2026-07-05"`, `"end": "2026-10-01"` |
| cp 07-05 | 660 | 660 | RESULT.md:389 `\| 2026-07-05 \| 660 \| 25.43% \|`; result.json:1543 `"n_univ_tickers": 660` date 2026-07-05 |
| cp 08-13 | 933 | 933 | RESULT.md:390; result.json:1551-1552 `"date": "2026-08-13"`, `"n_univ_tickers": 933` |
| cp 08-15 | 932 | 932 | RESULT.md:391; result.json:1560-1561 |
| cp 08-18 | 931 | 931 | RESULT.md:392; result.json:1569-1570 |
| cp 09-04 | 932 | 932 | RESULT.md:393; result.json:1578-1579 |
| cp 10-03 | 932 | **missing** (10-01=932) | RESULT.md:394 `\| 2026-10-01 \| 932 \| 35.92% \|`; result.json:1587-1588 `"date": "2026-10-01"`, `"n_univ_tickers": 932`; guard `change_points.2026-10-03` expected 932 observed null |
| leading min | 29 (1.118%) on 09-16 | 29, cov **0.011175** (~1.12% in MD) on 09-16 | RESULT.md:267 `29 (1.12%)`; result.json:1728,1736-1737 date 2026-09-16, n=29, 0.011175 |
| leading max | 307 (11.83%) on 08-24 | 307 / 0.118304 on 08-24 | RESULT.md:254 `307 (11.83%)`; result.json:2366,2375-2376 |
| any-theme | 35.99% | 35.99% / 0.359923 | RESULT.md:3,207,346; result.json:1616 `"union_max_ever": 0.359923` |
| min coverage | 25.43% (660/2595) | 25.43% / 0.254335 on 07-05 | RESULT.md:3,345; result.json:1596-1600 |
| 2014–2025 zeros | zeros | zeros | RESULT.md:204-218 Q2 table all `0` for 2014–2025 on every source |
| ISO weeks 33–39 | r2 values | **unchanged** (status field added) | week 33–39 min/max/dates equal r2 |
| ISO week 40 | r2 dates 09-30,10-01,10-02 max N 134 cov 0.051638 max date 10-02 | **09-30 only, max N 108, cov 0.041618, max date 09-30** | RESULT.md:289; `frozen_number_guard.iso_week_40` |

Lane as-found sha: RESULT.md:530 `` `c4b0241f5622656e7bb79cc9e6080a895f5a503c57b8b20fca67c859119ddd61` ``.
Lane round-3 sha: RESULT.md:413 `` `b16f444ad83741d04d0e2f8cf85fc134d1566e93ea087844c5aa05d5e2d6bd7e` ``.
Before/after table RESULT.md:452-457 does **not** show every number unchanged:

```
- `honest_window.end`: expected '2026-10-03', observed '2026-10-01'
- `change_points.2026-10-03`: expected 932, observed None
```

result.json:3397 `"n_moved": 2`.

`1.118%` vs MD `1.12%` is rounding of `29/2595=0.011175` (same json leaf as r2) — not a separate numeric move.

### I1

result.json:685 `"honest_start": "2026-07-19"`; :671 pit_class_reason names commit `15c39ef87650` at `2026-07-19T03:22:13Z`; :687-696 `asof_classes.before_first_write.pit_class=BACKFILLED` (16 rows), `from_first_write=PIT_HONEST` (38 rows); :698 `"honest_start_before_i1": "2026-06-18"`.
write_time_commits.context_history_first: sha `15c39ef87650`, date `2026-07-19T03:22:13Z`.
RESULT.md:25 Data-law row `themes_context_history | asof >= 2026-07-19 … | 2026-07-19`.
RESULT.md:95 I1 sentence; :450 `before=2026-06-18 after=2026-07-19`.
Leading join honest_start still `2026-08-13` (RESULT.md:32,248; result.json:1625).
`2026-06-18` residuals in result.json are `date_min`, `honest_start_before_i1`, `i1.before`, first join `per_date` asof, and prose — **not** `honest_start`.

### I2

`gh_evidence.json:1-10`:

```
"repo_head": "052e02d085b01f29baf499357e224c836d8eb224",
"until_repo_head_committer_date": "2026-10-02T07:02:07Z",
"endpoint": "repos/mastermindx-market-intelligence/macro/commits?path=data/themes_heatmap/tree_history.jsonl&per_page=5&until=2026-10-02T07:02:07Z"
```

Three of four queries use `until=2026-10-02T07:02:07Z`. `context_history_first` uses `until=2026-07-20T00:00:00Z` (first-write window).

hashes.txt:2845 `72f3bb6d…  …/gh_evidence.json`.

`subprocess` `["gh","api",…]` only inside `fetch_gh_path_commits` (`census.py:233`), called from `ensure_gh_evidence` (`census.py:280`). `collect_write_time_commits` (`census.py:2058`) reads the snapshot. `test_d0.py` has no `gh` subprocess.

Fake `gh` (SCR/bin/gh, `exit 1`) first on PATH; cwd = repo root; `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code_copy -q -p no:cacheprovider`:

```
.............................                                            [100%]
29 passed in 13.86s
```

which gh: SCR/bin/gh; fake gh rc=1. 0 skipped, 0 network errors.

Two-run shas in RESULT.md ## Tests: **not present**. Only:

```
result.json sha256 after the final fold: `b16f444ad83741d04d0e2f8cf85fc134d1566e93ea087844c5aa05d5e2d6bd7e`
Round-1 result.json sha256 …: `6ed2c8799dc622f76662b1c6c352be47c08ab9ec7746c0ef5f8ddafb893bcf18`
```

Live file sha equals the fold sha.

### I3

Builder (`census.py:314-334`): reason assembled from `write_time["tree_history"]["commits"]`; fallback `Write-time proof: evidence unavailable.` when `not rec.get("ok") or not commits`. Applied `census.py:2377` `tree["pit_class_reason"] = tree_pit_class_reason_from_commits(write_time)`.

Mutant: `load_gh_evidence` on SCR copy returns `{"queries":{}}`.

```
FAILED … test_tree_pit_class_reason_names_commit_evidence - assert 'b35bac058e' in "… Write-time proof: evidence unavailable."
1 failed, 1 passed, 27 deselected
```

`test_tree_pit_class_reason_unavailable_without_evidence` still passed (asserts the fallback branch).

### I4

Renderer `census.py:98-107` `inspect.getsourcelines`; symbol search `cite_assign` / `cite_test`; `build_repair_items` `census.py:2218`. Test `test_d0.py:391-407`.

`sed -n '<line>p'` for every round-1/2/3 cite (and local_sources.py:8-18): each line contains the cited symbol. Examples:

```
census.py:68  HONEST_WINDOW_RULE = (
census.py:1650 def compute_honest_window(
census.py:2527 def render_result_md(…
census.py:38  CONTEXT_HISTORY_FIRST_WRITE = "2026-07-19"
census.py:1078 def census_context(…
census.py:280 def ensure_gh_evidence(…
census.py:204 def load_gh_evidence(…
census.py:314 def tree_pit_class_reason_from_commits(…
census.py:3212 CENSUS_READ_TARGETS = [
census.py:167 def leaf_diff(…
test_d0.py:391 def test_repair_item_cites_contain_symbol():
local_sources.py:8 * a membership present in vintages i..j opens at ``asof(i)``;
```

Miss list: **none**. (A first regex treated trailing markdown backticks as part of the symbol; `sed -n` shows the symbol on the line.)

I4 mutant (`I1` where → `census.py:1 CONTEXT_HISTORY_FIRST_WRITE`):

```
FAILED … test_repair_item_cites_contain_symbol - AssertionError: ('I1', 'census.py', 1, 'CONTEXT_HISTORY_FIRST_WRITE', '#!/usr/bin/env python3')
1 failed, 28 deselected in 7.96s
```

### I5

Opened paths in `census.py` (open/read_text/read_parquet/load_jsonl/read_bytes/glob ohlcv): theme_graph `{_meta,nodes,edges,evidence,identity_resolution,node_lifecycle,capability}`, `membership_history.parquet`, jsonl histories, `program_ledger.parquet`, `phase0.json`, `theme_state.json`, `themes/state.json`, Q4 code/docs (`membership_evidence.py`, `theme_rollup_pit.py`, commission md, schema), engine files in `GREP_OPENED_PATHS` + `local_sources.py`, `gh_evidence.json`, `prior/round{1,2}_result.json`, `data/baskets/ohlcv/*.parquet`. All non-ohlcv opens are in `CENSUS_READ_TARGETS` (31/31 present in hashes). ohlcv glob hashed separately (2848 total paths).

Grep-only (not opened, not hashed as inputs) — RESULT.md:508-522 matches `GREP_ONLY_NAMED_PATHS`: `engine/theme_{placebo,extension,discovery,scoring,crowding,context,emergence}.py`, `engine/neuralweb/{theme_thesis,thematic_state,factor_contradictions,earnings_context_reader}.py`, `data/theme_graph/probation/proposals.jsonl`, `data/baskets/membership.json`, `data/themes_heatmap/{themes_tree,perf_snapshot}.json`.

```
cd <repo>
shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/hashes.txt
SHASUM_RC=0
OK count=2848
FAILED count=0
```

mtimes: result.json/RESULT.md 02:12:05, hashes.txt 02:12:06, DONE 02:13:10.

### I6

`census.py:2008-2014`: `derived = all(n in ran for n in needles)`; `"matches_disk": bool(derived)` with `disk_result: ran`. Test `test_d0.py:378-388`.

Mutant: after derivation, `out[0]["disk_result"]="MUTANT_FLIPPED_DISK_RESULT"`.

```
FAILED … test_matches_disk_derived_from_disk_result - AssertionError: engine/theme_graph/membership_evidence.py
assert True is False
1 failed, 28 deselected in 3.94s
```

### I7

result.json week 33:

```
"iso_week": 33,
"dates": ["2026-08-12", "2026-08-13"],
"min_leading_n": 0,
"status": "BEFORE_HONEST_START",
"n_dates_before_honest_start": 1
```

RESULT.md:282 `| 33 | BEFORE_HONEST_START | 2026-08-12, 2026-08-13 | 0 | …`; :291 I7 sentence. `census.py:604` `"status": "BEFORE_HONEST_START" if n_before else "HONEST"`.

### I8

Emitter `census.py:167 leaf_diff`. Lane stored `changed_keys.round2_to_round3` n_added=763, n_removed=35, n_changed=169, n_numeric_changed=61, truncated=True.

Independent recompute vs `prior/round2_result.json`: n_added=1227 (lane counts exclude some nested-after-fold keys / uses `strip_private` pre-fold in one blob), n_removed=35, n_changed=169, n_numeric=61, n_label=108. Numeric set matches RESULT.md:465-504 plus additional source `n_rows` / ISO week 40 max.

Required keys in the **full** diff: `sources[8].honest_start` 2026-06-18→2026-07-19; `honest_window.per_source[8].honest_start` same; `provenance.host.hostname=m2studio` and versions; `write_time_commits.source=…/gh_evidence.json`. Printed `added[:80]` starts `changed_keys.round1_to_round2.added[0]…` — **does not list** provenance/gh_evidence. `changed_paths[:80]` does include `honest_window.per_source[8].honest_start` and `honest_window.end`.

Round-2 copy **does exist**: `results/D0/prior/round2_result.json` sha `c4b0241f…`.

### H1–H6 / M1

H1–H6 cites `sed -n` verified (table above). Clean-copy pytest 29 passed includes `test_honest_change_points_pinned`, `test_d_star_is_exactly_2026_07_05`, `test_in_force_from_tree_and_snapshot_only`, ISO-week, Data-law heading.

M1 on SCR copy with fake gh (`-k` the four H1 tests):

```
FAILED test_honest_window_computed_once_and_used_for_verdict - assert 0.371869 <= 0.359923
FAILED test_honest_change_points_pinned - assert 966 == 660
FAILED test_in_force_from_tree_and_snapshot_only - assert 660 == 966
3 failed, 1 passed, 25 deselected in 7.83s
```

Same three failing names as the lane’s round-3 `orchestrated_run` (`3 failed, 26 passed` on the full 29). `test_d_star_is_exactly_2026_07_05` still passed (M1 does not move D*).

### Provenance

result.json:3335 `"hostname": "m2studio"`; versions python 3.14.7 / pandas 3.0.5 / numpy 2.5.2 / pyarrow 25.0.1 / scipy 1.18.0 / pytest 9.1.1; :3346 rerun notice names `rs_20261004T051657Z_81412` / mini2 / `DONE rc=124`. RESULT.md:524-528 same notice under ## Provenance; :528 `Host m2studio`.

## GAPS

- Two consecutive `census.main()` / `run.py` runs were **not** executed. `run.py` delegates to `census.main()` with no output-directory override; a run would rewrite `results/D0/`. Packet forbids that. Independently verified: in-process two `build_payload` identity (test passed) and live sha == printed fold sha. Not verified: two full `main()` artifacts (pytest fold + hashes) byte-identical.
- M1 was run on the four H1 tests, not the full 29. The three failures match the lane’s named list; full-suite pass count (26) was not re-counted here. M2 was not re-run (packet: rerun one of M1/M2).
- `leaf_diff` n_added 1227 (reviewer, full live json) vs lane 763 (`round2_to_round3` after fold, `added` truncated and nested `changed_keys` present). n_changed / n_numeric / n_removed match. The 763 vs 1227 gap is the truncated/nested counting, not a second numeric disagreement.
- Mini2 artifacts remain unreachable; no cross-host reproduction check.
- `context_history_first` endpoint `until=` is `2026-07-20T00:00:00Z`, not the repo_head committer date. Treated as intentional first-write bound, not a GAP in snapshot existence.

## DEVIATIONS

- Packet said the round-2 record was not preserved on this host. It is, at `results/D0/prior/round2_result.json` (sha `c4b0241f…`). Used it for the I8 recompute and frozen comparison (allowed: “if it kept one”).
- Lane RESULT.md calls the drifted files “skip-worktree”; `git ls-files -v` shows assume-unchanged `H`, not `S`. Same effect (hidden working copies).
- Fake `gh` is `SCR/bin/gh` (`#!/bin/sh` / `exit 1`), never under the checkout.
- Tests ran from repo cwd against `SCR/code_copy` and `SCR/mutants/*` with `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. Checkout `results/D0/` was not written.
- I4 first-pass “misses” from a backtick-greedy regex were discarded after `sed -n`; the miss list in RESULT is empty.
- Did not run `gh`, ssh, git writes, or lane `run.py`.
