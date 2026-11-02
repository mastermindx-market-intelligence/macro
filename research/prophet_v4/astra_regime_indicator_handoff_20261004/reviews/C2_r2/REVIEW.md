# C2 ROUND 2 independent review

## STATUS

PASS

Review completed against the ROUND-2 block of `C2_r2.txt` (N1..N9). Checkout was not modified. All tests and mutants ran on copies under this scratchpad. Round-0 `result.json` sha256 verified. Independent join count, leaf-diff, counterfactual recompute, c1-status mutants, and hashes check from repo root all ran.

## RESULT

**Recommended ruling: REQUEST_REPAIR**

Headline science is in the expected place (H10 and 2D **INSUFFICIENT SUPPORT** because C1 `controls.status == BROKEN`; descriptive pooled 3D H10 DiD `+0.0034518154435143936` CI `[-0.0008752350470632498, +0.007598139844272105]`; COUNTERFACTUAL **NOT SUPPORTED**). N1 (rule by code), N3 (pre-declared estimator), N5, N6, N7, and N8 close. Two named round-2 re-checks do not: N4’s attribution table is not exhaustive, and N9’s M7 mutant does not fail `test_compute_all_paired_zero`. N2’s specified operator mutants also do not fail the named tests (implementation is still the packet’s strict clauses).

### Per-item verdict

| item | verdict | file:line | notes |
|---|---|---|---|
| N1 verdict rule by code | FIXED | `run.py:536` `load_c1_controls_status`; `run.py:545` `load_b1_3d_verdicts`; `run.py:565` `compute_verdict`; `run.py:2171` production read; `test_C2.py:457` `test_verdict_insufficient_when_c1_broken`; `test_C2.py:472` `test_c1_status_is_read_from_record` | `controls.status` is read from `results/C1/result.json`. No production literal `c1_status="BROKEN"`. The only `c1_status="OK"` literals are the N8 counterfactual calls (`run.py:2228`, `run.py:2239`). `verdict.rule` is the packet text. Headlines are `H10: INSUFFICIENT SUPPORT` / `2D: INSUFFICIENT SUPPORT` with descriptive numbers beside the ANSWER FIRST label. |
| N2 clauses | PARTIAL | `run.py:511` `phase_count_packet`; `run.py:160` `ci_excludes_zero`; `run.py:528` `cost_curve_monotonic_strict`; `test_C2.py:501`; `test_C2.py:510` | Code and named tests match the packet (phase_count = DiD(p)<0 AND CI excludes 0; monotonic = strict `fast > mid > persistent`). `weak_monotonic` grep is empty. Both numbers are printed next to the headline (`phase_count=0 of 3`, `monotonic … = False`). Specified mutants `<`→`<=` and `>`→`>=` do **not** fail those tests on the published synthetics (defect 3). |
| N3 estimator restored | FIXED | `run.py:780` `e.loc[e["variant"] == "1D"]`; `run.py:231` `attach_confirmed` (`no_confirmation == False`); `run.py:1093–1112` key merge for shares; `run.py:654` `map_confirmed_by_key`; `test_C2.py:516` | Independent join: 296,637 1D rows, 0 dropped. No 849,380 grain-variant filter. Old integer-index `pd.Series(ev_keys).map` is gone from production (merge on `(name, signal_date)`). Re-introducing integer-index mapping on `map_confirmed_by_key` fails `test_confirmed_share_mapping_by_key`. Shares in (0,1) and within round-0 noise. |
| N4 leaf-diff attribution | PARTIAL | `RESULT.md:208–229` (16-row table); `result.json` `leaf_diff.rows` (16) | Independent flatten vs round 0: 83 numeric science-value moves. Lane listed 16 leaves. Pooled 3D H10 DiD moved only `+5.048291906017272e-07` (round 0 `0.003451310614323792` → now `0.0034518154435143936`) — consistent with (a), so N3 is not re-opened. Unlisted numeric leaves remain (defect 1). No numeric leaf was attributed to (b). |
| N5 honest-N | FIXED | `run.py:849–854` both legs; `run.py:1044–1072` `n_finite_mfe`; `RESULT.md:17–46` | All 21 rows in `## DiD 3D` and `## DiD 2D` carry `n_events` / `n_months` / `n_names` for both confirmed and 1D legs per tercile (0 missing). `result.json` `did.*.h10.n` missing-count = 0. Cost-curve `n` == `n_finite_mfe` (3D fast 72,059 finite vs 75,099 events). Breadth-axis table has no honest-N (report-only analogue; not counted against this item). |
| N6 era ranges | FIXED | `run.py:664` `era_token`; `RESULT.md:189–194` era_labels table | `grep -c`: RESULT.md 29 / 29; result.json 47 / 47. Residual **bare** `2014-2019` / `2020-2026` tokens outside the era_labels definition table: **none**. All other uses are qualified `2014-2019 (2015-08-05..2019-12-30)` / `2020-2026 (2019-12-31..2026-08-28)` or the definition-table backticks. |
| N7 provenance | FIXED | `RESULT.md:196–206`; `hashes.txt`; `run.py:2146` LOAD pin; `run.py:2393` END check; `run.py:2426` hashes last | Full 64-hex sha256 for B1 panel/pairs/result, C1 rotation (SAME `9361dbf0…`), C1 result `3492dc2d…` → live `142de0f2541513d9bbe660ff562678c63139e05def86d0048da5db1703cfea2f`, and the three engine files, plus host line. `shasum -a 256 -c hashes.txt` from repo root: 12 OK, 0 non-OK, no caveat. Live C1/B1 shas == hashes.txt == `result.json` inputs. Status `DELIVERED` (INPUT_CHANGED did not fire). |
| N8 counterfactual | FIXED | `RESULT.md:174–177`; `run.py:1620`; `run.py:2220` | Exactly one line, after the INSUFFICIENT SUPPORT headlines: `COUNTERFACTUAL (if C1 controls were PASS; not a verdict): NOT SUPPORTED`. Independent `compute_verdict(..., c1_status="OK")` on the real 3D statistics returns `NOT SUPPORTED`. |
| N9 tests + reproducibility + write order | PARTIAL | `test_C2.py:20` `C2_REPO`; `run.py:2068–2131` mutants; `run.py:2426–2427` write order | Scratch-copy pytest: **18 passed, 0 skipped**. Write order: `hashes.txt` newest among records, `DONE` after it (ns). M5/M6/MC1/MC2/N3 mutants fail the named tests. **M7 does not fail** (`1 passed, 17 deselected`, rc=0) — defect 2. Independent two-run of `run.py` not executed (no output-directory override; would rewrite `results/C2/`). Lane printed identical sha `be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54` twice; that sha matches live `result.json` and `hashes.txt`. |

### Numbered defects

1. **N4 incomplete science-leaf attribution.** Independent flatten of `result.json` vs round 0 found **83 numeric science-value moves** (did / gaps / cost_curve.n / shares / breadth / n_1d). The lane table lists **16** leaves. Unlisted movers include `did.2D.*`, `did.3D.by_phase.*`, `did.3D.pooled.h21`, almost all `gaps.*.gap_h*` and CIs, `cost_curve.2D.*.n`, `false_starts_avoided.mid.n`, and all `breadth_axis` numeric deltas (largest unlisted: `gaps.2D.mid.p1.gap_h10` `0.000871397241975842` → `0.0009976107296557342`, Δ `+1.262e-4`). Era-key qualification (N6) and new honest-N blocks (N5) also rewrite hundreds of paths with no class-level row. Nothing numeric was blamed on (b), and pooled 3D H10 DiD moved only `+5.05e-7` (allowed (a)). **Re-check that closes it:** publish a complete leaf list (or documented class rules covering every changed science path) tagged (a)/(b)/(c); leftover count 0; 0 numeric leaves tagged (b); pooled 3D H10 DiD Δ still ≤ the (a) panel/pairs move.

2. **N9 M7 mutant does not fail.** Lane `run.py:2083–2088` replaces the shared `draws` array with `default_rng(1)` / `default_rng(2)` **inside every `gap_pack` call**. Those seeds are constant, so every cell still shares identical conf/1d draws and `test_compute_all_paired_zero` stays green (`rc=0`, observed `1 passed, 17 deselected`). An unseeded per-call mutant on the same copy **does** fail that test (`max |DiD| = 2.333e-02`). **Re-check that closes it:** M7 must be a true per-cell independent month draw (unseeded or unique seed per call); `pytest -k test_compute_all_paired_zero` on that mutant must FAIL; paste `test_compute_all_paired_zero` into `## Tests` as the failing name (not `1 passed, 17 deselected`).

3. **N2 specified operator mutants do not fail the named tests.** On a scratch copy: `d < 0` → `d <= 0` and `hi < 0` → `hi <= 0` in `ci_excludes_zero` / `phase_count_packet`; `fast > mid > persistent` → `>=`. `test_phase_count_packet_definition` and `test_cost_curve_monotonic_strict` both still **pass** (synthetics have no equality-boundary case: no Δ=0, no CI bound at 0, False monotonic case is `0.14 > 0.158` which remains False under `>=`). Implementation is still the packet’s strict clauses; grep has no `weak_monotonic`. **Re-check that closes it:** add an equality-boundary synthetic (e.g. one phase with Δ=0, and `(0.15, 0.15, 0.10)` for monotonic) so `<`→`<=` fails `test_phase_count_packet_definition` and `>`→`>=` fails `test_cost_curve_monotonic_strict`.

## EVIDENCE

### Round-0 sha (required first)

```
shasum -a 256 …/scratchpad/results_prev/C2_r0/result.json
9372f0f7ad0a4795e74a46dc7f4fc08d11adc2eb2dd158504b28dfc4f82842e0
```

Matches the packet (`r0_sha_ok True`). Live C2 `result.json` sha256 `be4e04d449a61a262753e08fdfae32b81f682a53094e6a376908fb9e1cc00a54` (matches `hashes.txt` and the two shas printed in `## Tests`).

Checkout `git rev-parse HEAD` = `052e02d085b01f29baf499357e224c836d8eb224`. Python `/opt/homebrew/bin/python3` 3.14.7, pandas 3.0.5, numpy 2.5.2, pyarrow 25.0.1, scipy 1.18.0, pytest 9.1.1.

### N1 — verdict rule by code

Production read site (`run.py:2171`):

```
c1_controls_status = load_c1_controls_status(C1_JSON)
b1_3d_verdicts = load_b1_3d_verdicts(B1_JSON)
```

then `compute_verdict(..., c1_status=c1_controls_status, b1_3d_verdicts=b1_3d_verdicts)` at `run.py:2198`. Live C1 `controls.status` = `BROKEN`. Live B1 per-phase 3D verdicts loaded as `['NOT SUPPORTED', 'NOT SUPPORTED', 'NOT SUPPORTED']`.

`verdict.rule` equals the packet text (independent string compare `rule_matches_packet True`).

ANSWER FIRST (`RESULT.md:1`) and `## Verdict` (`RESULT.md:174–175`):

```
H10: INSUFFICIENT SUPPORT — C1 `controls.status` is **BROKEN** … Pooled 3D DiD on H10 net = +0.0035 95% CI [-0.0009, +0.0076]; era signs 2014-2019 (2015-08-05..2019-12-30)=+ 2020-2026 (2019-12-31..2026-08-28)=+; phase_count=0 of 3 … monotonic … = False.
H10: INSUFFICIENT SUPPORT
2D: INSUFFICIENT SUPPORT
```

Grep for production literals: `c1_status="BROKEN"` assignment = none. `c1_status="OK"` only at `run.py:2228` and `:2239` (counterfactual).

Named tests on scratch copy (with `C2_REPO` set): pass as part of `18 passed`.

**(i) hard-code `return "OK"` at `load_c1_controls_status` (read site):**

```
FAILED …/mutants/MC1/test_C2.py::test_c1_status_is_read_from_record
AssertionError: assert 'OK' == 'BROKEN'
1 failed, 17 deselected in 0.89s
```

Hard-coding only `c1_controls_status = 'OK'` in `main` (not the loader) does **not** fail that test (`1 passed, 17 deselected`) — the test exercises the loader / `verdict_from_loaded_inputs`, which is the packet’s read-site mutant.

**MC2 (delete BROKEN clause in `compute_verdict`):**

```
FAILED …/mutants/MC2/test_C2.py::test_verdict_insufficient_when_c1_broken
AssertionError: assert 'NOT SUPPORTED' == 'INSUFFICIENT SUPPORT'
1 failed, 17 deselected
```

**(ii) synthetic C1 `{"controls":{"status":"OK"}}` through `verdict_from_loaded_inputs` (real read path), floors_ok True, CI includes 0:**

```
synthetic OK label NOT SUPPORTED
synthetic BROKEN label INSUFFICIENT SUPPORT
live C1 via loader BROKEN
```

OK-branch label is the packet NOT SUPPORTED label.

### N2 — clauses

`phase_count_packet` (`run.py:511–525`) counts `d < 0 and ci_excludes_zero(ci)`. `cost_curve_monotonic_strict` (`run.py:528–533`) is `fast > mid > persistent`. Grep `weak_monotonic` / `849,380` / `849380` / `1D.M3` in C2 code+results: no matches.

Headline prints `phase_count=0 of 3` and `monotonic … = False`. Independent recompute: `phase_count_packet` on real 3D by_phase = **0**; `cost_curve_monotonic_strict(0.0478, 0.1467, 0.1214)` = **False**.

Named tests pass on the copy. Specified mutants:

```
N2_phase -k test_phase_count_packet_definition → 1 passed, 17 deselected
N2_mono  -k test_cost_curve_monotonic_strict   → 1 passed, 17 deselected
N2_both  → 2 passed, 16 deselected
```

### N3 — estimator + join count

Independent join (B1_r3 `events_panel.parquet` sha `209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8` == live panel) 1D rows to live `results/C1/rotation_state_daily.parquet` on `signal_date`:

```
n_1d_raw 296637
n_1d_joined 296637
n_1d_dropped 0
reported 296637 0
```

≈ 296,637 minus dropped 0. Confirmation pairs: 5 variants × 296,637 = 1,483,185 rows; `no_confirmation` False = 516,605. Production `attach_confirmed` inner-merges `~no_confirmation` pairs to the variant’s `events_panel` outcome row (`run.py:247`, `:267`, `:288`). Contrast population is `variant == "1D"` (`run.py:780`), not a 849,380-row grain filter.

False-start / large-winner shares (all strictly inside (0,1)):

| tercile | false_start | large_winner | vs round 0 |
|---|---:|---:|---|
| fast | 0.7587542315504401 | 0.4963325183374083 | identical |
| mid | 0.7546478135637601 | 0.4761044824250242 | FS Δ `+5.84e-6`; LW identical |
| persistent | 0.7629726890756302 | 0.5341676904176904 | identical |

Pooled ~0.76 / ~0.50 as specified. Round-0 fast FS 0.7587542315504401 / LW 0.4963325183374083.

**N3 old-mapping mutant** (integer-index `Series.map` inside `map_confirmed_by_key`):

```
FAILED …/mutants/N3/test_C2.py::test_confirmed_share_mapping_by_key
assert [False, False, False] == [False, True, True]
1 failed, 17 deselected
```

Production shares use `e1.merge(..., on=["name","signal_date"])` (`run.py:1111`), not the integer-index helper. `map_confirmed_by_integer_index` remains only as the documented buggy helper for the test.

### N4 — independent leaf diff vs round 0

Pooled 3D H10 DiD:

| | delta | CI |
|---|---:|---|
| round 0 | 0.003451310614323792 | [-0.0008754812751993297, 0.007598016858986852] |
| now | 0.0034518154435143936 | [-0.0008752350470632498, 0.007598139844272105] |
| Δ | +5.048291906017272e-07 | lo +2.46e-7, hi +1.23e-7 |

Near round 0’s `+0.00345 [-0.00088, +0.00760]`. Era `2014-2019` pooled 3D H10 delta is **byte-identical** to round 0 (`0.003278961540121713`); `2020-2026` moved `0.0051391635714472085` → `0.005139847746540715` (the +2 1D rows live in the later era).

Independent flatten: 151 in-place value changes, 1188 only-now paths, 372 only-r0 paths. Numeric (both present, values differ): **83**. Lane `leaf_diff.rows`: **16**. Attribution of listed headlines to (a) panel (`8b170497…` → `209e2246…`, pairs `22eabfe6…` → `d20cd405…`) or (c) N1/N3/N5 is consistent. (b) correctly stated as moving nothing numeric (rotation parquet `9361dbf0…` SAME). Unlisted numeric leaves: defect 1.

Cost-curve `n` 75,099 → 72,059 (3D fast) is (c) N5 finite-mfe redefinition, listed.

### N5 — honest-N

`## DiD 3D` + `## DiD 2D`: 21 data rows, **0** missing `n_events` / `n_months` / `n_names`, **0** missing a confirmed or 1D leg. `result.json` did-tree `n` missing-count = 0. Cost curve prints `n_finite_mfe` and uses it as `n`.

### N6 — era tokens

```
grep -c 2014-2019 RESULT.md  → 29
grep -c 2020-2026 RESULT.md  → 29
grep -c 2014-2019 result.json → 47
grep -c 2020-2026 result.json → 47
```

Residual unqualified lines outside era_labels: **none**. JSON bare keys `2014-2019` / `2020-2026` exist only under `era_labels`.

### N7 — hashes

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
…/C2/code/run.py: OK
…/C2/code/test_C2.py: OK
…/C2/result.json: OK
…/C2/RESULT.md: OK
shasum_exit=0
```

12 lines, 0 non-OK, no caveat. Live recomputes equal those pins. C1 result now = `142de0f2541513d9bbe660ff562678c63139e05def86d0048da5db1703cfea2f`. Host line present (`m2` / m2studio / python 3.14.7 / pandas 3.0.5 / …).

Write-order nanoseconds:

```
result.json  1791103495089687709
RESULT.md    1791103495104364594
hashes.txt   1791103495163294258
DONE         1791103495163468091
```

`hashes.txt` newest record; `DONE` after it.

### N8 — counterfactual recompute

Imported `compute_verdict` from the scratch copy on the real `result.json` 3D pooled/by_phase/by_era H10, `monotonic_3d=False`, `floors_ok=True`, `b1_3d_verdicts` from live B1:

```
c1_status='OK'      → NOT SUPPORTED
c1_status='BROKEN'  → INSUFFICIENT SUPPORT
RESULT.md line      → COUNTERFACTUAL (if C1 controls were PASS; not a verdict): NOT SUPPORTED
count of that form  → 1
```

Position: after `H10:` / `2D:` INSUFFICIENT SUPPORT, under `## Verdict`.

### N9 — pytest, mutants, write order

Scratch copy, `C2_REPO` set to the checkout:

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest SCR/code_copy -q -p no:cacheprovider
..................                                                       [100%]
18 passed in 2.06s
```

Repeat with `-rs`: `18 passed in 2.29s`. **0 skipped.** `result.json["tests"]` = `'18 passed'` (timing stripped).

Mutants run by this review on copies:

| mutant | failing test (this review) |
|---|---|
| M5 (`persistent − fast`) | `test_compute_all_did_sign_under_h10` (got +0.035) |
| M6 (`meets = True`) | `test_compute_all_floors` (`True is False`) |
| M7 (lane: `default_rng(1)`/`(2)` inside gap_pack) | **none — 1 passed, 17 deselected, rc=0** |
| M7_strong (unseeded per call, extra check) | `test_compute_all_paired_zero` (max \|DiD\| = 2.333e-02) |
| MC1 (loader returns `"OK"`) | `test_c1_status_is_read_from_record` |
| MC2 (delete BROKEN clause) | `test_verdict_insufficient_when_c1_broken` |
| N3 old mapping | `test_confirmed_share_mapping_by_key` |

Lane `mutant_table` in `result.json` agrees, including M7 `rc: 0` / observed `1 passed, 17 deselected`.

`run.py` has no output-directory override (`RESULTS` is hardcoded). Independent two-run was **not** executed.

### C2 files this review did not touch

C2 `DONE` / `hashes.txt` / `result.json` mtimes still `2026-10-04 01:44:55`. `results/D0/` was not read or written.

## GAPS

- **Independent `run.py` two-run.** Packet forbids running the lane’s `run.py` against this checkout (it rewrites `results/C2/`). No output-directory override exists. Cannot independently confirm the two printed `result.json` shas. Mitigated by: hashes.txt check OK; live sha = `be4e04d4…` = both printed shas; tests field is timing-stripped.
- **LOAD vs END pins as stored fields.** `result.json` stores one `inputs.*_sha256` set (the LOAD hashes). END equality is the `INPUT_CHANGED` check (`run.py:2393`) plus hashes written after it. Status is `DELIVERED`. Live recomputes match. There is no separate `sha_at_end` object to diff.
- **N2 operator-mutant re-check** did not produce failures on the published synthetics (defect 3). Implementation still matches the packet.
- **Breadth-axis DiD analogue** (`RESULT.md:110–122`) has no `n_events` / `n_months` / `n_names`. Treated as out of N5’s “both legs per tercile” DiD tables. If the seat meant those rows too, they are still missing.
- **`map_confirmed_by_key` is not called in production.** Production false-start/large-winner mapping is a key merge. The N3 mutant re-check therefore mutates the helper the test calls, not the merge. The merge is the correct key mapping; the integer-index bug is gone.
- Did not re-bootstrap the 1,000-draw DiD on the full panel (would be a `run.py` re-run). Descriptive numbers were checked against `result.json` and the round-0 record only.

## DEVIATIONS

- All work was confined to `SCR=…/scratchpad/review/C2_r2` (code copy, mutants, logs, this REVIEW.md). The checkout, including `results/D0/` and `results/C2/`, was not written.
- Tests ran as `pytest SCR/code_copy` with `C2_REPO` pointing at the checkout, per packet, not from `results/C2/code/`.
- M7 was applied both as the lane wrote it (fixed seeds 1 and 2 — does not fail) and as an unseeded per-call variant (does fail). The unseeded variant is extra evidence, not a packet step.
- N1 (i) was applied at `load_c1_controls_status` (packet read site) and, separately, at `main`’s assignment (does not fail the named test). The packet mutant is the loader.
- N4 compared a full flatten against the 16-row table; no attempt was made to re-attribute every leaf for the lane.
- `run.py` was never executed.
- No git writes, no `gh`, no ssh, no network.
