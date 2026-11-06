# C2 ROUND 1 independent review

## STATUS

PASS — review completed against the packet ROUND-1 block, the preserved round-0 record, the C2 ROUND 1 artifacts, hashes, mutants M5/M6/M7 plus a C1-status mutant, and a post-hoc pytest run.

## RESULT

**REQUEST_REPAIR**

The round did consume B1 ROUND 3 `events_panel.parquet` `209e2246…` and C1 ROUND 3 `rotation_state_daily.parquet` `9361dbf0…` / `result.json` `d51c5708…`. J1–J3 mutant tests exist and catch M5/M6/M7. J5 timing is stripped. Those are not enough. The frozen verdict rule was not applied: C1 `controls.status` is `BROKEN`, so every rotation-conditioned cell and ANSWER FIRST must be **INSUFFICIENT SUPPORT** with the descriptive DiD beside it. The lane printed **NOT_SUPPORTED** as the headline, hard-coded `C1_controls_status` at `run.py:661`, rewrote the rule text so the BROKEN clause is gone, and no test pins a C1-status flip. The estimator itself was rewritten (not a J1–J6 repair): `n_1d_events_joined` moved 296,635 → 849,380, pooled 3D H10 DiD moved +0.00345 → +0.00016, false-starts/large-winners collapsed to 1.0, and the phase-count definition changed. A −32 1D-row panel swap cannot explain those leaves.

### Per-item verdict

| item | verdict | file:line |
|---|---|---|
| Verdict rule | **NOT FIXED** | packet L49, L64–69; `RESULT.md:4–6` ANSWER FIRST; `RESULT.md:213–215` ## Verdict; `result.json:1130–1146`; `run.py:661`; `stats.py:44–64` VERDICT_RULE; `stats.py:283–321` `compute_verdict` |
| Provenance | **PARTIAL** | `hashes.txt:1–5` pins `209e2246…` / `9361dbf0…` / `d51c5708…` and `shasum -c` is 0 non-OK; `RESULT.md:7–12` deltas omit C1 `result.json` `d51c5708…` and zero-pad the round-0 B1 sha |
| J1 (M7 paired bootstrap) | **FIXED** | `test_C2.py:264–329` `test_compute_all_paired_zero`; `stats.py:148–155` shared month draw. M7 fails that test. `RESULT.md:217–220` does not paste the failing name |
| J2 (M5 DiD sign) | **FIXED** | `test_C2.py:335–384` `test_compute_all_did_sign_under_h10`; `features.py:209–210` `did = d[0]−d[1]`. M5 fails that test (and `test_bootstrap_is_month_clustered_negative_control_fails`) |
| J3 (M6 floors) | **FIXED** | `test_C2.py:390–464` `test_compute_all_floors`; `features.py:297–301` `meets_floor`. M6 fails that test |
| J4 (honest-N / cost-curve n) | **PARTIAL** | secondary tables `RESULT.md:136–168` carry `n_events`/`n_months`/`n_names`, cost-curve has `n_finite_mfe` + medians/min/sd; DiD pooled/era/phase tables `RESULT.md:53–81` still have no N |
| J5 (byte-reproducible tests string) | **FIXED** | `result.json:1147` `"tests": "9 passed, 3 skipped"` (no wall time); `run.py:108–131` strips `in N seconds`. Two consecutive `run.py` shas were not independently reproduced (would write `results/C2/`) |
| J6 (era date ranges) | **PARTIAL** | dedicated table `RESULT.md:47–51` and `result.json:56–66` `era_labels` carry ranges; cell/DiD/support tables still print bare `2014-2019` / `2020-2026` (`RESULT.md:92–118`, `result.json:75+`) |
| Leaf diff vs round 0 | **NOT FIXED** | all four rule inputs moved by a code rewrite, not by the panel swap; false-starts/large-winners = 1.0 is a mapping bug (`stats.py:537`) |
| Tests | **PARTIAL** | three skips are the record-existence tests at `test_C2.py:473/488/500` (K11 write-order: `run.py:353` then `run.py:356`); post-hoc from repo root **12 passed**; no test asserts the verdict label under BROKEN controls |

### Defect list (each with the re-check that closes it)

1. **Headline verdict is NOT_SUPPORTED, not INSUFFICIENT SUPPORT.** Packet L49: *if controls.status == "BROKEN", every rotation-conditioned cell is reported INSUFFICIENT SUPPORT and ANSWER FIRST says so.* Packet L66–69: *INSUFFICIENT SUPPORT otherwise (also whenever C1 controls are BROKEN …).* Lane ANSWER FIRST (`RESULT.md:4–6`): `**H10: NOT_SUPPORTED** — H10 NOT_SUPPORTED (pooled DiD = +0.0002, 95% CI [-0.0010, +0.0013], phase count 2/3, era-signed=no, monotonic=no)`. Lane ## Verdict (`RESULT.md:213–215`): `**3D: NOT_SUPPORTED**`. DEVIATIONS item 6 (`RESULT.md:236`) admits the BROKEN clause was not applied. **Re-check:** ANSWER FIRST and `verdict.3D` / `verdict.2D` read exactly `INSUFFICIENT SUPPORT` (spaces, not underscores) while C1 is BROKEN, with the descriptive pooled 3D H10 DiD printed beside it; `verdict.reasons` includes the BROKEN clause; a COUNTERFACTUAL-if-C1-PASS line is restored as in round 0.

2. **`C1_controls_status` is hard-coded, not read from the C1 record; flipping it does not change the label; no test pins the rule.** `run.py:661` is `"C1_controls_status": "BROKEN"`. `write_hashes_txt` hashes `C1/result.json` but nothing parses `controls.status`. `compute_verdict` (`stats.py:283–321`) has no C1 argument and returns `NOT_SUPPORTED` as soon as `pooled_obs >= 0` (`stats.py:298–299`). Mutant MC1 (`BROKEN`→`OK` at `run.py:661`) still `9 passed, 3 skipped`. `test_verdict_each_clause_can_flip` never mentions BROKEN. Embedded `verdict_rule` (`stats.py:44–64`, `result.json:34`) dropped the BROKEN/B1-INSUFFICIENT clause and replaced the packet’s NOT-SUPPORTED / INSUFFICIENT definitions. **Re-check:** `run.py` reads `controls.status` from C1 `result.json`; a synthetic/unit test fails when that status is BROKEN and the label is not `INSUFFICIENT SUPPORT`, and fails when status is flipped to a passing value and the label does not follow the remaining clauses; `verdict.rule` is the packet L66–69 text.

3. **Phase-count / monotonicity clauses were rewritten, so even the descriptive DiD is scored under a different rule.** Packet: *DiD(p) < 0 with CI excluding zero for ≥ 2 of 3 phases* and *3D cost curve monotonic fast > mid > persistent*. Round 1 counts phases that match the *pooled* sign (`RESULT.md:81` “2 / 3”) and uses `weak_monotonic` on `diff(confirmed−baseline)` (`stats.py:317–319`, `features.py:237–247`). Under the packet, r1 phase CIs are p0 `[−0.00383, +0.00011]` (negative point, CI includes 0), p1/p2 positive — **0 of 3** packet-phases, not 2/3. Cost-curve means fast=0.1399, mid=0.1582, persistent=0.0123 — not fast>mid>persistent. **Re-check:** `phase_count` is the packet definition (DiD<0 and CI excludes 0); cost-curve monotonicity is `mean_mfe21_consumed_frac` fast>mid>persistent; both printed next to the INSUFFICIENT SUPPORT headline.

4. **Unexplained leaf moves vs round 0 — estimator rewrite, not the −32 1D-row panel swap.** Round 0 used all 1D events (296,635 joined) vs confirmation-pair confirmed entries. Round 1 filters `1D.M3+3D.p*` (849,380 rows) and treats grain-variant panel rows as the contrast. False-starts/large-winners shares are all 1.0 because `pd.Series(ev_keys).map(any_confirmed)` maps by integer index, not tuple values (`stats.py:537`). **Re-check:** `n_1d_events_joined` is the 1D-event count (~296,637 on this B1 panel, 0 dropped); false-starts shares are in (0,1) and within noise of round 0 (~0.76 / ~0.50); pooled 3D H10 DiD vs round 0 moves only by an amount attributable to the documented panel delta; a leaf-diff vs `C2_r0/result.json` attributes every remaining changed leaf to (a)/(b)/(c) with no leftovers.

5. **J4 incomplete: DiD tables still have no honest-N.** `RESULT.md:53–81` pooled/era/phase DiD tables have no `n_events`/`n_months`/`n_names`. **Re-check:** those three DiD tables each carry `n_events` / `n_months` / `n_names`; cost-curve `n` used for the mean is the finite `mfe21_consumed_frac` count (`n_finite_mfe`).

6. **J6 incomplete: not every era label carries its date range.** Dedicated table `RESULT.md:47–51` is correct (`2014-2019` → 2015-08-05..2019-12-30; `2020-2026` → 2019-12-31..2026-08-28). Cell/support/DiD rows still say bare `2014-2019`. **Re-check:** every printed era token in `RESULT.md` and `result.json` includes its actual `signal_date` range.

7. **Provenance delta section is not exact.** `hashes.txt` pins the right three input shas (see EVIDENCE). `RESULT.md:7–12` lists B1 `8b170497000000…` → `209e2246…` and C1 rotation SAME `9361dbf0…`, and does not list C1 `result.json` `d51c5708…` vs round-0 `3492dc2d…`. Round-0 B1 sha is zero-padded after the prefix. **Re-check:** “Round-1 vs round-0 sha deltas” lists B1 panel `209e2246…` vs the true round-0 panel sha, C1 table `9361dbf0…` SAME, and C1 `result.json` `d51c5708…`; `shasum -a 256 -c hashes.txt` remains 0 non-OK.

8. **No COUNTERFACTUAL line labelled as in round 0.** Round 0: `COUNTERFACTUAL (if C1 controls were PASS; not a verdict): NOT SUPPORTED`. Round 1 has none. **Re-check:** the exact round-0 counterfactual line is restored under ## Verdict, distinct from the INSUFFICIENT SUPPORT headline.

J1–J3 tests themselves do **not** need repair: M7 → `test_compute_all_paired_zero`; M5 → `test_compute_all_did_sign_under_h10`; M6 → `test_compute_all_floors`. J5 timing strip is in place. Those items are FIXED and should not be re-opened unless a later rewrite drops them.

## EVIDENCE

### Packet rule (quoted)

L49: `.../results/C1/result.json (if controls.status == "BROKEN", every rotation-conditioned cell is reported INSUFFICIENT SUPPORT and ANSWER FIRST says so).`

L64–69:

```
VERDICT (pre-declared, compute mechanically; write the rule text into result.json):
SUPPORTED iff pooled 3D DiD on H10 net < 0 with 95% CI excluding zero, AND the pooled DiD has the same sign in both eras, AND DiD(p) < 0 with CI excluding zero for ≥ 2 of 3 phases, AND the 3D cost curve is monotonic fast > mid > persistent.
NOT SUPPORTED iff the pooled 3D DiD CI includes zero AND all fast/persistent cells meet the floors.
INSUFFICIENT SUPPORT otherwise (also whenever C1 controls are BROKEN or B1's verdict is INSUFFICIENT on every 3D phase).
Also report the 2D verdict with the same rule (≥ 2 of 2 phases).
```

### Lane ANSWER FIRST + ## Verdict (quoted)

`RESULT.md:4–6`:

```
**H10: NOT_SUPPORTED** — H10 NOT_SUPPORTED (pooled DiD = +0.0002, 95% CI [-0.0010, +0.0013], phase count 2/3, era-signed=no, monotonic=no)
2D verdict: **NOT_SUPPORTED**
```

`RESULT.md:213–215`:

```
**3D: NOT_SUPPORTED** — reasons: pooled_did_not_negative
**2D: NOT_SUPPORTED** — phase_count=1/2
```

`RESULT.md:236` DEVIATIONS 6: `the C1 controls.status is BROKEN ... the round-0 verdict logic does not gate on this clause, so the round-0 verdict is preserved exactly.`

Round 0 (preserved) ANSWER FIRST was already the correct label: `the hypothesis is **INSUFFICIENT SUPPORT**: C1 controls.status is **BROKEN** ... Pooled 3D DiD on H10 net = +0.0035 95% CI [-0.0009, +0.0076]`. Round 1 did not preserve that.

### Hard-code vs read; C1-status mutant

```
run.py:661:            "C1_controls_status": "BROKEN",
```

`write_hashes_txt` lists `C1_DIR / "result.json"` among hashed inputs; no `json.load` of that file exists in `run.py`. C1 record itself has `"controls": { ..., "status": "BROKEN" }` and sha `d51c5708e385849231a0f5193a06c2586c546b87c142b262ff3bafa1dba32749`.

MC1 (copy of `code/`, `sed`/python replace `"C1_controls_status": "BROKEN"` → `"OK"`):

```
python3 -m pytest SCR/code_MC1 -q -p no:cacheprovider
.........sss
9 passed, 3 skipped in 0.43s
```

No test name failed. Absence of a pinning test is confirmed.

### Provenance / hashes

`hashes.txt` (first five input lines):

```
209e224686955cf14401b6d65b9cf06464ce17e3c9cf092aef968319334d7ef8  .../B1/events_panel.parquet
d20cd4056e8e6b1fbb6e9545ddfda50109cb65cbf030af60461bf90cf41f61ae  .../B1/confirmation_pairs.parquet
9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd  .../C1/rotation_state_daily.parquet
0deef95be1c10f13fcecc30cfafb74b2045e55de0baf730eef25a7dc26b03508  .../B1/result.json
d51c5708e385849231a0f5193a06c2586c546b87c142b262ff3bafa1dba32749  .../C1/result.json
```

Command: `shasum -a 256 -c research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C2/hashes.txt` from repo root.

Output: all 11 paths `OK`; `shasum_rc=0`. `hashes.txt` lists no `data/yahoo/*` or `data/prophet/ledger.jsonl`, so the local nightly-vintage exception did not fire. `git show 052e02d085b0:<path>` was not required.

B1 panel live row counts (`pd.read_parquet`): `nrows=1406344`; `variant=="1D"` **296637** (matches the mission’s B1 ROUND 3 1D count); `1D.M3=101575`, `3D.p0=99912`, `3D.p1=99665`, `3D.p2=99702` (sum 849380 = r1 `n_events_after_variant_filter` / `n_1d_events_joined`).

`RESULT.md:7–12` deltas: B1 `8b170497000000…` → `209e2246…` DIFFERS; C1 rotation `9361dbf0…` SAME; confirmation_pairs `d20cd405…`; C1 status BROKEN. C1 `result.json` `d51c5708…` is not in that list. Preserved round-0 `hashes.txt` B1 panel is the full `8b17049773a32c6e517a614a48e530f29bc250f126e4ee9b8871ecd4cd7690a1`, not the zero-padded form and not `ba58e043…`.

### Mutants (every id named in the ROUND-1 block)

Copies under `SCR/code_M5`, `SCR/code_M6`, `SCR/code_M7`. Round-0 line numbers `run.py:604` / `:562-563` / `:355` do not exist in the rewritten tree; equivalent sites: `features.py:210` (DiD subtraction), `stats.py` shared `picked` draw, `features.py:297` `meets_floor`. `C2_REPO` set to the repo root (see DEVIATIONS). Command each time: `python3 -m pytest SCR/<copy> -q -p no:cacheprovider`.

**M5** (persistent − fast at `features.py:210`):

```
FAILED .../code_M5/test_C2.py::test_bootstrap_is_month_clustered_negative_control_fails
  observed DiD should be negative ... got 0.038799377548208315
FAILED .../code_M5/test_C2.py::test_compute_all_did_sign_under_h10
  J2 FAIL: observed pooled DiD should be clearly negative ... got 0.036373699463895307
2 failed, 7 passed, 3 skipped in 0.61s
```

Failing test named in the J2 re-check: **`test_compute_all_did_sign_under_h10`**.

**M6** (`meets_floor = True` at `features.py:297`):

```
FAILED .../code_M6/test_C2.py::test_compute_all_floors
  J3 FAIL: every cell has n_months=10 < FLOOR_MONTHS=24 but meets_floor was True
1 failed, 8 passed, 3 skipped in 0.56s
```

Failing test: **`test_compute_all_floors`**.

**M7** (independent month draw per cell in `_bootstrap_did_for_phase`):

```
FAILED .../code_M7/test_C2.py::test_compute_all_paired_zero
  J1 FAIL: phase 3D.p0 paired bootstrap had max |DiD| = 3.925e-03
1 failed, 8 passed, 3 skipped in 0.56s
```

Failing test: **`test_compute_all_paired_zero`**. No named mutant was uncaught.

Unmutated copy `SCR/code_orig`: `9 passed, 3 skipped in 0.56s` with `-rs`:

```
SKIPPED .../code_orig/test_C2.py:473: result.json not yet written; run.py first
SKIPPED .../code_orig/test_C2.py:488: RESULT.md not yet written; run.py first
SKIPPED .../code_orig/test_C2.py:500: hashes.txt not yet written; run.py first
```

Those are `test_result_json_schema_if_present`, `test_result_md_present_and_contains_answer_first`, `test_hashes_txt_verifies`. Write-order: `run.py:353` `_run_tests_summary()` then `run.py:356` `write_artifacts(...)` which writes `result.json` / `RESULT.md` / `hashes.txt` last. K11-style; not missing mutant tests.

### Leaf diff vs preserved round 0

Compared `results_prev/C2_r0/result.json` vs lane `results/C2/result.json`. Flatten: r0 653 leaves, r1 787 leaves, 27 common, **21 changed common**, 626 r0-only, 760 r1-only (schema rewrite). Full dump: `SCR/leafdiff.txt`.

**Four rule inputs, side by side**

| rule input | round 0 | round 1 | attribution |
|---|---|---|---|
| pooled 3D H10 DiD | +0.003451310614323792, CI [−0.0008754812751993297, +0.007598016858986852] | +0.00015688786729110897, CI [−0.0010106644038954918, +0.0012778911698355956] | **(c) code change** (estimator rewrite 1D-events vs confirmation_pairs → 1D.M3 vs 3D.p* panel rows). Not (a): a ~2-to-32 row 1D delta cannot move DiD by 0.0033. Not (b): C1 table sha `9361dbf0…` identical |
| era signs | 2014–2019 +0.00327896; 2020–2026 +0.00513916 (both +, packet “same sign” is about the predicted negative) | 2014–2019 +0.00005217; 2020–2026 +0.00026431; `era_signs_same_negative=false` | **(c)** |
| phase count | **0 of 3** DiD<0 with CI excluding 0 (p0 +0.00242 [−0.00215,+0.00706]; p1 +0.00445 [−0.00020,+0.00876]; p2 +0.00349 [−0.00121,+0.00799]) | reported **2/3 matching pooled sign**; packet-definition still **0 of 3** (p0 −0.00175 [−0.00383,+0.00011] includes 0; p1 +0.00030; p2 +0.00192) | **(c)** definition change + estimator rewrite |
| cost-curve monotonicity | False; mean mfe fast=0.04783, mid=0.14673, persistent=0.12145 | False; pooled-phase means fast=0.13995, mid=0.15818, persistent=0.01227 | **(c)** |

Other changed common leaves, all **(c)** unless noted:

- `n_1d_events_joined` 296635 → 849380 — **(c)** (r1 counts 1D.M3+3D.p*, not 1D events). Live `variant=="1D"` is 296637, so a correct 1D join on this panel would be ~296,637 (a), not 849,380.
- `verdict.3D` / `verdict.2D` `INSUFFICIENT SUPPORT` → `NOT_SUPPORTED` — **(c)** rule rewrite (defect 1).
- `verdict.rule` and `verdict.reasons` rewritten — **(c)**.
- `false_starts_avoided.*.share_unconfirmed` ~0.76 → **1.0**; `large_winners_excluded.*` ~0.50 → **1.0** — **(c)** `stats.py:537` index-map bug, not panel swap.
- `did.2D.pooled.h10.delta` 0.00299 → 0.00021 — **(c)**.
- `did.3D.pooled.h21.delta` 0.00266 → 0.00091 — **(c)**.
- `tests` `"9 passed in 1.47s"` → `"9 passed, 3 skipped"` — **(c)** J5 (legitimate) + write-order skips.
- `repo_head` `ca2e4abd…` → `052e02d085b0…` — checkout, not a statistic.
- `data_class.universe` string change; `deviations` list → `[]` in JSON (prose still in RESULT.md) — **(c)**.

No leaf is attributable to **(b)** C1 ROUND 3: rotation table sha is unchanged `9361dbf08018f0c2…`. The C1 `result.json` sha did move `3492dc2d…` → `d51c5708…`, but the table is frozen and r1 never reads `controls.status` from that file.

Unexplained moves (defect 4): pooled DiD, era DiDs, phase DiDs, n_1d, false-starts, large-winners, cost-curve means, verdict label.

### Tests

Post-hoc from repo root:

```
python3 -m pytest research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C2/code -q -p no:cacheprovider
............
12 passed in 0.69s
```

(repeat with `-rs`: 12 passed, no skips.)

Lane-recorded string `result.json:1147` / `RESULT.md:217–220`: `9 passed, 3 skipped` — consistent with pytest-before-write.

Does any test assert the verdict label under BROKEN controls? **No.** `test_C2.py` hits INSUFFICIENT only at `:239–241` (`pooled_ci_hi=0.001` and `sufficient_power=False` → `INSUFFICIENT_SUPPORT`) and `:482` (schema membership of `{SUPPORTED, NOT_SUPPORTED, INSUFFICIENT_SUPPORT}`). Zero references to `BROKEN` or `C1_controls` in `test_C2.py`.

## GAPS

- Did not re-run `code/run.py` end-to-end (it writes `results/C2/`). J5 “two runs, identical sha256, print both” is therefore not independently reproduced; only the strip in `_run_tests_summary` and the on-disk `"9 passed, 3 skipped"` string were checked.
- Did not independently recompute the 1,000-draw pooled DiD; numbers above are read from the two `result.json` files.
- Mission text said round 0 consumed B1 panel `ba58e043…` with 296,669 1D rows. The preserved `C2_r0/hashes.txt` pins `8b17049773a32c6e…` and `n_1d_events_joined=296635`. Leaf diff used the preserved artifact named in this packet. `ba58e043…` was not located in this worktree’s C2_r0 record.
- MC1 proves no *test* notices a C1-status flip. Whether a full `run.py` with status `OK` would change the written headline cannot be shown without writing `results/C2/`; `compute_verdict` has no C1 argument, so it cannot.
- `git show 052e02d085b0:data/yahoo/...` restore was unnecessary: `hashes.txt` has no those paths and all listed hashes were OK.

## DEVIATIONS

- Pytest on SCR copies exported `C2_REPO` to the worktree root because `test_C2.py` derives `REPO` as `RESULTS_DIR` five parents up, which from `SCR/code_*` is not the git checkout (`engine/` missing). The packet’s `python3 -m pytest SCR/<copy> -q -p no:cacheprovider` was otherwise used verbatim.
- M5/M6/M7 were applied at the round-1 equivalent sites (`features.py:210`, `features.py:297`, `stats.py` per-cell redraw), not at the round-0 `run.py:604/562/355` line numbers, which the rewrite deleted.
- Added mutant MC1 (hard-coded BROKEN→OK) because the mission asked whether a C1-status flip changes the label / whether a pinning test exists.
- Did not restore `052e02d085b0` bytes for `data/yahoo/*.parquet` or `data/prophet/ledger.jsonl` (not in `hashes.txt`; all hashes OK).
- No git writes, no `gh`, no ssh, no network, no edits under `research/prophet_v4/astra_regime_indicator_handoff_20261004/results/` or any tracked file. All mutants and notes live under `SCR`.
