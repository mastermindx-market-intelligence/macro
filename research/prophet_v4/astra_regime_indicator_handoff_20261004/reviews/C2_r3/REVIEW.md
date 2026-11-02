# C2 ROUND 3 independent review

## STATUS

PASS

Review completed against the ROUND-3 BLOCK of `C2_r3.txt` (D1..D4 plus P0/P1/P2). Checkout was not modified. All tests and mutants ran on copies under this scratchpad. `run.py` was never executed. Round-0 and live `result.json` sha256 verified first and last.

## RESULT

**Recommended ruling: ACCEPT**

Round 3 is records + tests only. Science is frozen: live `results/C2/result.json` sha256 is still `be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54` (first and last). The three numbered round-2 defects are closed: M7 now fails `test_compute_all_paired_zero`; N2a/N2b operator mutants fail the named tests on equality-boundary synthetics; the science-leaf attribution is complete (`leftover_untagged = 0`, independent path-set match 1124/1124). Breadth-axis caption is present and the table numbers are unchanged. `run.py` diff vs round-2 backup is a single hunk inside the mutant-harness `m7` block.

Headline science is unchanged from round 2: pooled 3D H10 DiD `+0.0034518154435143936` CI `[-0.0008752350470632498, +0.007598139844272105]`; H10 and 2D **INSUFFICIENT SUPPORT**; COUNTERFACTUAL **NOT SUPPORTED**.

### Per-item verdict

| item | verdict | file:line | notes |
|---|---|---|---|
| P0 science pin | FIXED | `result.json` sha `be4e04d4…`; `RESULT.md:337` last Round-3 line; `RESULT.md:176–179`; `RESULT.md:212` | First sha = last sha = expected pin. Round-3 section prints that sha as its last line. Diff vs round-2 `RESULT.md` is caption + Tests row-update + appended `## Round 3`; no pre-existing numeric value changed. Live JSON pooled 3D H10 DiD / CI match the round-2 quoted numbers. |
| P1 run.py diff confinement | FIXED | `run.py:2083–2088` hunk `@@ -2083,8 +2083,8 @@`; production `gap_pack` `run.py:835`; `run_mutants` `run.py:2068` | `diff` vs `_r2_backup/run.py`: 4 changed lines (`grep -c '^[<>]'` = 4), one hunk. Only the M7 replacement string (`default_rng(1)`/`(2)` → unseeded `default_rng()`). Production `gap_pack` still uses shared `draws`. Estimator / verdict / joins / bootstrap / writers untouched. |
| D1 (r2 defect 2, M7) | FIXED | `run.py:2083–2088` `m7`; `test_C2.py:360` `test_compute_all_paired_zero`; `RESULT.md:273` M7 row | Harness M7 is unseeded `np.random.default_rng()` per `gap_pack` call. Mutant copy: **FAILED** `test_compute_all_paired_zero` — `J1 FAIL: paired bootstrap max \|DiD\| = 1.667e-02`. Unmutated copy: **1 passed, 17 deselected**. `## Tests` M7 row names that failing test (not `1 passed`). |
| D2 (r2 defect 3, N2) | FIXED | `test_C2.py:501–517`; `run.py:160` `ci_excludes_zero`; `run.py:446` / `run.py:520` `d < 0`; `run.py:528` monotonic; `RESULT.md:277–278` | Equality-boundary synthetics present: DiD `0.0` with CI excluding 0; DiD `< 0` with CI upper `0.0`; triple `(0.15, 0.15, 0.10)` is False. N2a (`<`→`<=` at production sites) **FAILED** `test_phase_count_packet_definition` — `assert 3 == 1`. N2b (`>`→`>=`) **FAILED** `test_cost_curve_monotonic_strict` — `assert True is False`. Unmutated: both pass. `test_C2.py` vs `_r2_backup`: additions only (70 → 72 asserts). |
| D3 (r2 defect 1, N4) | FIXED | `code/leaf_attribution.py`; `leaf_attribution.json`; `RESULT.md:304–322` | Script + JSON exist. Redirected rerun byte-identical to live JSON (`7285ea00…`). Independent flatten path-set equals lane list (1124/1124). Every leaf has exactly one allowed tag; `(b)` count 0; C1 parquet `9361dbf0…` byte-identical; `leftover_untagged` 0 independently. `key_rows` pooled 3D H10 DiD r0 `0.003451310614323792` → now `0.0034518154435143936` (delta `5.048291906017272e-07`). Lane count 1124 vs r2 reviewer 83 reconciled by method (see EVIDENCE). Round 3 summarises per-class counts, largest delta per class, pooled row. |
| D4 (r2 GAP, breadth caption) | FIXED | `RESULT.md:106–108` caption; table `RESULT.md:112–124` | One-line caption directly under `## Second axis: breadth tercile (narrow vs broad)`: `report-only analogue — honest-N (n_events / n_months / n_names) not recorded in round 2; not part of the N5 DiD tables`. Diff vs round-2 `RESULT.md` adds only that caption in this section; table numbers unchanged. |
| P2 tests + hashes + write order | FIXED | `hashes.txt`; `DONE`; `test_C2.py`; `RESULT.md:258–288` | Scratch-copy pytest: **18 passed, 0 failed, 0 skipped**. `shasum -a 256 -c hashes.txt` from repo root: **17 OK, 0 non-OK**, rc=0. Pins new `leaf_attribution.py` / `leaf_attribution.json` / edited `run.py` / `test_C2.py` and frozen `result.json` at `be4e04d4…`. ns: `hashes.txt` newest record except `DONE`; `DONE` newest. `## Deviations` and `## Tests` preserved (M7 row updated; N2a/N2b rows appended; Deviations body untouched). |

### Numbered defects

Round-2 numbered defects, with the re-check that closes each:

1. **N4 incomplete science-leaf attribution (round-2 defect 1).** Round 2 listed 16 leaves vs an independent 83 in-place numeric scalars. Round 3 publishes `leaf_attribution.json` with 1124 tagged leaves, `leftover_untagged = 0`, `(b) = 0`, and the pooled 3D H10 DiD key row. **Re-check that closed it:** independent flatten of both `result.json` files (dotted paths, numeric leaves, changed/added/removed, era-paired) produced the same 1124 paths as the lane JSON; every tag is in `{(a),(b),(c) named clause,(a)+(c) jointly}`; C1 rotation parquet sha `9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd` is byte-identical to round 0; key row delta `5.048291906017272e-07`.

2. **N9 M7 mutant does not fail (round-2 defect 2).** Round-2 M7 used constant seeds 1/2 inside every `gap_pack` call. Round 3 uses unseeded `default_rng()` per call. **Re-check that closed it:** apply harness M7 to a scratch copy → `pytest -k test_compute_all_paired_zero` **FAILED** `test_compute_all_paired_zero` with `max |DiD| = 1.667e-02`; unmutated copy passes; `## Tests` M7 row names that failing test.

3. **N2 specified operator mutants do not fail (round-2 defect 3).** Round-2 synthetics had no equality boundary. Round 3 added DiD `== 0.0`, CI upper `== 0.0`, and `(0.15, 0.15, 0.10)`. **Re-check that closed it:** N2a `<`→`<=` at `ci_excludes_zero` / both `d < 0` production sites → `test_phase_count_packet_definition` **FAILED** `assert 3 == 1`; N2b `>`→`>=` → `test_cost_curve_monotonic_strict` **FAILED** `assert True is False`; unmutated copy `2 passed, 16 deselected`.

No new numbered defects. One prose imprecision in `RESULT.md` Round 3 (largest *continuous* `(a)` named as `gaps.2D.mid.p1.gap_h10` Δ `+1.262e-4`; under exploded CI the larger continuous `(a)` is `breadth_axis.2D.by_phase.p1.h10.ci[1]` Δ `+1.625e-4`) does not leave an untagged leaf and does not change the required per-class table (which correctly lists `(a)` largest as `cost_curve.2D.mid.n_finite_mfe` +1, matching `leaf_attribution.json`). Not re-opened.

## EVIDENCE

### Environment / pins (required first)

```
shasum -a 256 …/results/C2/result.json
be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54   # FIRST

shasum -a 256 …/scratchpad/results_prev/C2_r0/result.json
9372f0f7ad0a4795e74a46dc7f4fc08d11adc2eb2dd158504b28dfc4f82842e0
```

Checkout `git rev-parse HEAD` = `052e02d085b01f29baf499357e224c836d8eb224`. Python `/opt/homebrew/bin/python3` → 3.14.7; pandas 3.0.5; numpy 2.5.2; pyarrow 25.0.1; scipy 1.18.0; pytest 9.1.1.

`_r2_backup/` is present. Its shas match `results_prev/C2_r2/` and the round-2 `hashes.txt` pins:

```
2fd664cbd3109d3e09f01d53300d4d998b2a105b4f8604ad188afafc09d361fa  _r2_backup/run.py  == C2_r2/code/run.py == r2 hashes.txt run.py
5a4f8f24a6fa668cb7334cb8292ee8b445f50eb2aa5f85bfe898a4ccbf42620b  _r2_backup/test_C2.py == C2_r2/code/test_C2.py == r2 hashes.txt test_C2.py
be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54  live result.json == C2_r2/result.json
```

Backup `run.py` still contains the round-2 M7 `default_rng(1)` / `default_rng(2)` strings quoted in the round-2 REVIEW.

### P0 — science pin and RESULT.md numbers

Live JSON:

```
did.3D.pooled.h10.delta  0.0034518154435143936
did.3D.pooled.h10.ci     [-0.0008752350470632498, 0.007598139844272105]
verdict.3D / 2D          INSUFFICIENT SUPPORT / INSUFFICIENT SUPPORT
counterfactual_if_c1_pass.3D  NOT SUPPORTED
```

`RESULT.md` ANSWER FIRST still has the rounded form quoted in round 2 (`+0.0035` CI `[-0.0009, +0.0076]`; `phase_count=0 of 3`; monotonic `False`). Precise values remain at `RESULT.md:212`. Verdict block:

```
H10: INSUFFICIENT SUPPORT
2D: INSUFFICIENT SUPPORT
COUNTERFACTUAL (if C1 controls were PASS; not a verdict): NOT SUPPORTED
```

Diff vs `results_prev/C2_r2/RESULT.md`: 48 added lines, 1 removed line. The only removal is the old M7 observed cell `1 passed, 17 deselected` (row-update). Pre-existing science tables, DiD numbers, Gaps, Verdict, Leaf-diff 16-row table, Deviations, and Gaps body are byte-identical except the D4 caption insert under the breadth heading. `## Round 3` first sha line `RESULT.md:298` and last line `RESULT.md:337` both print `be4e04d4…`.

Frozen `result.json["tests"]` remains `'18 passed'`. Frozen `mutant_table` M7 row remains `observed: 1 passed, 17 deselected` / `rc: 0` (science JSON not rewritten; the human Tests table was updated instead).

### P1 — run.py diff confined to mutant harness

```
diff -u _r2_backup/run.py code/run.py
@@ -2083,8 +2083,8 @@
-        new = """        boot_c = cell_boot_means(make_paired_draws(..., np.random.default_rng(1)), m_c, v_c)
-        boot_1 = cell_boot_means(make_paired_draws(..., np.random.default_rng(2)), m_1, v_1)"""
+        new = """        boot_c = cell_boot_means(make_paired_draws(..., np.random.default_rng()), m_c, v_c)
+        boot_1 = cell_boot_means(make_paired_draws(..., np.random.default_rng()), m_1, v_1)"""

diff … | grep -c '^[<>]'  →  4
hunk headers               →  @@ -2083,8 +2083,8 @@
```

Production `gap_pack` (`run.py:829`, boot at `run.py:835`) still:

```
boot_c = cell_boot_means(draws, m_c, v_c)
boot_1 = cell_boot_means(draws, m_1, v_1)
```

`default_rng()` occurs twice, both inside the `m7` replacement string (`run.py:2086–2087`). `def m7` lives only inside `run_mutants` (`run.py:2068`). `main` still *invokes* `run_mutants()` at `run.py:2375` when `run.py` is executed (round-2 mutant-table writer); this round did not execute `run.py`. No production estimator/bootstrap path applies the M7 string transform.

### D1 — M7 independent month sample

Harness `m7` (`run.py:2083–2088`) applied to a scratch copy with `replace(old, new, 1)` (first/`gap_pack` site), same as the harness.

Unmutated copy:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code_copy -q -p no:cacheprovider -k test_compute_all_paired_zero
.                                                                        [100%]
1 passed, 17 deselected in 0.64s
```

M7 mutant copy:

```
FAILED …/mutants/M7/test_C2.py::test_compute_all_paired_zero
AssertionError: J1 FAIL: paired bootstrap max |DiD| = 1.667e-02; mutant M7 (per-cell month draws) would produce non-zero DiDs
assert 0.016666666666666666 < 1e-09
1 failed, 17 deselected in 0.65s
```

Failing assertion: `test_C2.py:375` (`assert max_abs < 1e-9`). `## Tests` M7 row (`RESULT.md:273`) names `test_compute_all_paired_zero` and quotes `1.667e-02`. Round-2 reviewer unseeded variant was `2.333e-02`; this unseeded run is `1.667e-02` (allowed to differ).

### D2 — N2 boundary synthetics and operator mutants

`test_C2.py` vs `_r2_backup/test_C2.py` (additions only):

```
+        "eq0": {"delta": 0.0, "ci": [-0.02, -0.001]},  # DiD exactly 0.0 …
+        "hi0": {"delta": -0.01, "ci": [-0.02, 0.0]},   # CI upper bound exactly 0.0 …
+    extra = tuple(R.PHASES_3D) + ("eq0", "hi0")
+    assert R.phase_count_packet(by_phase, extra) == 1
+    assert R.cost_curve_monotonic_strict(0.15, 0.15, 0.10) is False
```

Assert count 70 → 72. No pre-existing assertion removed or weakened. Pre-existing `== 1` / `is False` / `is True` lines remain.

Unmutated:

```
-k "test_phase_count_packet_definition or test_cost_curve_monotonic_strict"
..                                                                       [100%]
2 passed, 16 deselected in 0.32s
```

N2a (this review, production sites `hi < 0`→`hi <= 0` in `ci_excludes_zero` and both `and d < 0`→`and d <= 0` in `compute_verdict`/`phase_count_packet`, matching the lane `_mutants/N2a` hunks at `run.py:168`, `:446`, `:520`):

```
FAILED …/mutants/N2a/test_C2.py::test_phase_count_packet_definition
AssertionError: assert 3 == 1
1 failed, 17 deselected in 0.33s
```

Failing assertion: `test_C2.py:511`.

N2b (`return bool(fast > mid > persistent)` → `>=` at `run.py:533`):

```
FAILED …/mutants/N2b/test_C2.py::test_cost_curve_monotonic_strict
assert True is False
1 failed, 17 deselected in 0.34s
```

Failing assertion: `test_C2.py:517` (`cost_curve_monotonic_strict(0.15, 0.15, 0.10) is False`).

### D3 — independent leaf flatten vs `leaf_attribution.json`

Redirected copy of `code/leaf_attribution.py` (OUT under SCR; R2 = live checkout `result.json`; R0 = pinned round-0 file). Checkout `leaf_attribution.json` mtime unchanged (`2026-10-04 21:58:11`). Rerun bytes == live JSON sha `7285ea00f719b0989846fe66bdbe7fd730d3968b9822f7de4b74beb0d3cc94d4`.

Lane JSON:

```
changed_numeric_leaves 1124
leftover_untagged 0
(b) C1 record delta count=0
key_rows did.3D.pooled.h10.did
  r0  0.003451310614323792
  now 0.0034518154435143936
  delta 5.048291906017272e-07
classes:
  (a) B1 panel delta                          173  largest cost_curve.2D.mid.n_finite_mfe +1
  (b) C1 record delta                           0
  (c) 1D-row estimator / key-merge / phase_count / monotonic / verdict-by-code  0 each
  (c) era qualification                       189  (key rewrite, delta 0)
  (c) honest-N blocks                         654  (all added; r0 null)
  (c) cost-curve n is n_finite_mfe              6  largest cost_curve.2D.mid.n 104137→98973 (−5164)
  (a)+(c) jointly                             102  largest meta.n_1d_events_joined +2
```

173+189+654+6+102 = 1124.

Independent flatten (this review, not the lane classifier):

```
atomic (lists not exploded):
  in-place any-type 151     only-r0 372     only-now 1071
  in-place numeric scalars  83
explode + science roots:
  in-place numeric 194      (lane method.method.in_place_both_present_no_era_pair)
era-paired science numeric changed/added/removed/renamed:
  1124  (moved 281, added 654, removed 0, renamed 276)
path-set vs lane leaves: only-lane 0, only-mine 0
independent leftover_untagged (missing/empty tag) 0
independent badtag 0
(b) tagged leaves 0
C1 rotation_state_daily.parquet sha 9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd
```

**Count reconciliation (83 vs 1124 vs 194):**

| method | count | what it includes |
|---|---:|---|
| Round-2 independent review | **83** | Atomic flatten (CI arrays *not* exploded, so a `[lo,hi]` list is not an int/float leaf). In-place both-present numeric scalars only. Era-key rewrites are only-r0/only-now, not in-place. Honest-N blocks are new paths, not in-place. This review reproduces **83** exactly; also reproduces r2’s **151** in-place any-type and **372** only-r0. |
| Lane `in_place_both_present_no_era_pair` | **194** | Same in-place restriction, but CI bounds exploded (`ci[0]`/`ci[1]`). This review: **194**. Extra vs 83 = exploded CI bounds that were non-numeric as arrays. |
| Lane `changed_numeric_leaves` / this review era-paired | **1124** | Exploded CI + era-qualified keys paired to bare round-0 counterparts + added/removed (honest-N 654 added; era qualification 189 renamed with delta 0; joint/panel movers). Path set matches the JSON. |

`(b)` explicit statement is in `RESULT.md:205` / Round 3 / `leaf_attribution.py` method note: rotation parquet `9361dbf0…` SAME ⇒ zero numeric leaves tagged `(b)`. Independently verified.

Pooled row matches `key_rows` and both JSON files. `gaps.2D.mid.p1.gap_h10` `0.000871397241975842` → `0.0009976107296557342` (Δ `+1.2621348767989215e-4`) is tagged `(a)`.

### D4 — breadth-axis caption

`RESULT.md:106–108`:

```
## Second axis: breadth tercile (narrow vs broad)

report-only analogue — honest-N (n_events / n_months / n_names) not recorded in round 2; not part of the N5 DiD tables
```

Diff vs round-2 RESULT.md in this section is those two added lines only. Table rows (3D/2D pooled/p0/p1/p2/eras) unchanged, e.g. 3D pooled H10 `+0.0032` `[-0.0011, +0.0075]`.

### P2 — full suite, hashes, write order

Scratch copy, `C2_REPO` = checkout:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code_copy -q -p no:cacheprovider
..................                                                       [100%]
18 passed in 2.11s
```

0 failed, 0 skipped (summary would name skips if present). Lane Round 3 quoted `18 passed in 1.52s`; count matches, timing is not a science number.

`shasum -a 256 -c hashes.txt` from `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7`:

```
…/B1/events_panel.parquet: OK
…/B1/confirmation_pairs.parquet: OK
…/B1/result.json: OK
…/C1/rotation_state_daily.parquet: OK
…/C1/result.json: OK
engine/canon.py: OK
engine/session_anchor.py: OK
engine/bar_derive.py: OK
…/C2_r0/result.json: OK
…/C2_r2/REVIEW.md: OK
…/C2/code/run.py: OK
…/C2/code/test_C2.py: OK
…/C2/code/leaf_attribution.py: OK
…/C2/code/conftest.py: OK
…/C2/result.json: OK
…/C2/RESULT.md: OK
…/C2/leaf_attribution.json: OK
hashes_rc=0
OK count=17  non-OK=0
```

Required pins:

```
221968da5f55a9652a22d499fe42f2d55539b0786fe503fd2ad323138e999e60  …/C2/code/run.py
17ed534537d202a092aa658e0348fabb030f43fee988b0c22dd0deec3c031eae  …/C2/code/test_C2.py
dec4f0b93e9a9061664fa00e69c5f5190a82bdb783ff8c4ad9004641f6c61e44  …/C2/code/leaf_attribution.py
7285ea00f719b0989846fe66bdbe7fd730d3968b9822f7de4b74beb0d3cc94d4  …/C2/leaf_attribution.json
be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54  …/C2/result.json
```

Write-order nanoseconds:

```
result.json            1791103495089687709
leaf_attribution.json  1791176291676832495
RESULT.md              1791176413946711712
hashes.txt             1791176429005833727
DONE                   1791176429587992419
```

`hashes.txt` newer than every other record file; `DONE` newest.

`## Tests` still contains the round-2 `18 passed` block and both run-A/run-B shas; M7 row updated; N2a/N2b rows appended. `## Deviations` body (seven bullets) unchanged.

### P0 last sha (required last)

```
shasum -a 256 …/results/C2/result.json
be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54   # LAST
```

Equals first sha and the Round-3 last line.

## GAPS

- **Independent `run.py` two-run.** Packet forbids executing the lane `run.py` against this checkout. No output-directory override. Frozen `result.json` sha and hashes check substitute. Frozen `mutant_table` still records round-2 M7 as passing; the Tests markdown row is the round-3 record of the new failure.
- **`leftover_untagged` in `leaf_attribution.py` is structurally 0** (`classify` never returns `None`). Closed independently: path-set equality 1124/1124 and every tag in the allowed set.
- **Round-2 `hashes.txt` was overwritten.** Backup bytes were verified against `results_prev/C2_r2/` and that copy’s `hashes.txt` pins (`2fd664cb…` / `5a4f8f24…`), and against the round-2 REVIEW’s quoted M7 source. The round-2 REVIEW EVIDENCE did not itself quote those two hexes.
- **Atomic only-now count** this review = 1071 vs round-2 REVIEW’s 1188. In-place any-type (151), only-r0 (372), and numeric scalars (83) match the round-2 REVIEW exactly; the 83 is the figure being reconciled.
- **Round-3 prose** names `gaps.2D.mid.p1.gap_h10` as the largest continuous `(a)` (the round-2 reviewer’s largest unlisted scalar). Under exploded CI, `breadth_axis.2D.by_phase.p1.h10.ci[1]` is larger (`+1.625e-4` vs `+1.262e-4`). Required per-class table matches JSON. Not treated as an untagged-leaf defect.
- Did not re-bootstrap the 1,000-draw DiD (would be a `run.py` re-run). Descriptive numbers checked against frozen `result.json` and round-0 only.

## DEVIATIONS

- All work confined to `SCR=…/scratchpad/review/C2_r3` (code copy, mutants, redirected leaf-attribution rerun, logs, this REVIEW.md). The checkout, including `results/C2/` and `results/D0/`, was not written.
- Tests ran as `pytest SCR/code_copy` (and `SCR/mutants/{M7,N2a,N2b}`) with `C2_REPO` pointing at the checkout, per packet, not from `results/C2/code/`.
- `leaf_attribution.py` was copied and patched so `OUT_JSON` is under SCR and `R2_JSON` reads the live checkout file. It was not run in-place (it would write `results/C2/leaf_attribution.json`).
- Used read-only `scratchpad/results_prev/C2_r2/RESULT.md` to prove pre-existing numeric sections and the breadth table were unchanged. Not a packet step; extra evidence.
- N2a was applied at the three production sites the lane’s own `_mutants/N2a` touched (`ci_excludes_zero` and both `d < 0` blocks), which is what yields `assert 3 == 1`. A first attempt that only mutated `hi < 0` failed `assert 2 == 1`; the packet’s production-site mutant is the three-site version.
- `run.py` was never executed.
- No git writes, no `gh`, no ssh, no network.
