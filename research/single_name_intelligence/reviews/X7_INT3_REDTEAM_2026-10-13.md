# X7 INT3 red-team — 2026-10-13

Scope: INT3 head `5b6fd2e8798886141e074d50a4468c063d44ad28` versus INT2 head `e4c2f672bed06eef3fac0b7bb88d46275a228f28`. Read-only composition review of that diff. rank_authority false, gate_authority false, size_authority false, signal_authority false, escalation_authority false, trade_authority false.

## Summary

Four MAJOR, three MINOR, one NIT. The residual tree is still the sealed v1.1 runner (`f9f4bf6442a948b7500228f9f963fc50a2ac7168`) and S2 v1.1 regenerates byte-identically on this host, but three composition holes survive the per-lane judgements: `check_join` ALLOWED on a one-sided `period_start` and on a ratio whose `segment_scheme_version` differs; `tests/test_sni_seal_full_check.py` (schk_09/schk_10) is off the `sni-acceptance-evidence` job while `test_schk_05_full_regeneration_s1` fails on this Linux x86_64 host with 10 ULP-equivalent P03 files. The SNI suite under `-x` stops on that schk_05 failure. S2 clock-law and non-finite edits did not move sealed S2 bytes on the sealed inputs.

## Findings

### X7-01 — MAJOR

CLAIM: On this Linux x86_64 host, S1 v1.1 regeneration is not byte-identical: `test_schk_05_full_regeneration_s1` fails with 10 ULP-equivalent P03 files (worst relative difference 4.76e-12), while `seal_full_check.py --study all` still prints OK because ULP tolerance is on by default.

EVIDENCE: `python3 -m pytest tests/test_sni_seal_full_check.py -q -p no:cacheprovider` and `python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --repo-root .` (numpy 2.5.4). schk_05 assertion at `tests/test_sni_seal_full_check.py:59`. CLI final lines:

```
s1: files compared=48 identical=35 named-exception passes=3 ulp-equivalent=10 failures=0 [Linux x86_64]
s2: files compared=23 identical=22 named-exception passes=2 ulp-equivalent=0 failures=0 [Linux x86_64]
SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)
```

The 10 ULP paths are the nine `observations/P03_*.json` files plus `results/P03.json`. `git rev-parse 5b6fd2e8798886141e074d50a4468c063d44ad28:research/single_name_intelligence/residual` is `f9f4bf6442a948b7500228f9f963fc50a2ac7168`; `git diff --stat e4c2f67..5b6fd2e -- research/single_name_intelligence/residual/` is empty. Residual code did not move; the Linux byte-identity pin in schk_05 did not hold on this interpreter.

FALSIFIER: Re-run `test_schk_05_full_regeneration_s1` on the numpy/platform that cut the v1.1 seal and observe `ulp_equivalent == 0`.

REPAIR: Pin the S1 regen runtime (numpy/BLAS) to the seal-cut environment, or drop the Linux `ulp_equivalent == 0` pin to match the CLI's ULP path, and put `tests/test_sni_seal_full_check.py` on `sni-acceptance-evidence` so the pin is actually run.

### X7-02 — MINOR

CLAIM: INT3 edited the sealed S2 runner (`event_response/s2_clocklaw.py`, `event_response/s2_outcomes.py`) without a new registered S2 version; the v1.1 seal still matches because the sealed inputs never take the new branches, so the seal is silent on those cases.

EVIDENCE: INT3 `event_response/` diff-stat is only those two files (+21/−6). `session_part` is written into sealed `EVENT_CENSUS.json` (`s2_selection.py:106-107`). Census has 7 rows, 0 on the six owner-published HK half-days, 0 with `t_avail` in 12:00–13:00 HKT. `_usable_close` (`s2_outcomes.py:39-44,82-83`) abstains on non-finite or non-positive closes; `info_leak_scan` now differences the full series then clips to `[first_tune_anchor, last_bar]` (`s2_outcomes.py:149-156`). S2 regen: 23 compared, 22 identical, 2 named-exception passes, 0 ULP, 0 failures. S2 does not stamp `HEAD:event_response` the way S1 stamps `HEAD:residual` (`run_s1.py` `code_tree_sha`; S1_SEALED_RUNNER_DEFERRAL_2026-10-13.md). S1FIX was reverted for that stamp; S2FIX landed under v1.1.

FALSIFIER: Place a sealed census row with `t_avail` 12:05 HKT on 2026-02-16, or a non-finite BABA close on a graded endpoint, regenerate S2, and observe a bytes-differ on `EVENT_CENSUS.json` or a results JSON.

REPAIR: Register an S2 runner version for the clock-law and non-finite edits, or add a seal-adjacent fixture that exercises a published half-day and a non-finite close so v1.1 cannot stay green while those branches rot.

### X7-03 — MAJOR

CLAIM: `check_join` returns ALLOWED on a `same_fact` (and `ratio`) pair whose `period_start` is an ISO date on one side and absent / None / `""` on the other.

EVIDENCE: Period compare at `sni_join_guard.py:407-422` fires only when `_present` is true on both sides. `validate_fact` requires `period_end` (`sni_join_guard.py:271-272`) and does not require `period_start`. `/tmp` probe against this worktree:

```
period_start hole ALLOWED ()
```

Left fact is the synthetic A09 `_base_fact`; right is a copy with `period_start` deleted. Status ALLOWED, reasons empty. Same ALLOWED for `period_start=None` and `period_start=""`. Two different `period_start` dates still REFUSE with `PERIOD_MISMATCH`.

FALSIFIER: Call `check_join` on that pair and observe status REFUSED with `PERIOD_MISMATCH` (or a named `PERIOD_START_*` reason).

REPAIR: Treat one-sided `period_start` as `PERIOD_MISMATCH` (or refuse unknown with a named reason) for every join_kind that already compares period.

### X7-04 — MAJOR

CLAIM: A `ratio` join whose `segment_scheme_version` values differ is ALLOWED when neither fact carries a `segment`.

EVIDENCE: `_add_segment_rules` (`sni_join_guard.py:328-335`) for `join_kind == "ratio"` checks scheme only when both segments are set, then returns. `same_fact` still refuses scheme-only mismatch via the `elif` at lines 343-347. `/tmp` probe:

```
ratio scheme hole ALLOWED ()
```

Left `segment_scheme_version="v1"`, right `"v2"`, no `segment`, otherwise the synthetic A09 base fact. The A09 module docstring (`sni_join_guard.py:379-380`) says the guard refuses a join whose segment scheme does not match. `test_a09_positive_ratio` (`tests/test_sni_join_guard.py:547-552`) pins one-sided *segment* as ALLOWED; it does not pin scheme-only mismatch.

FALSIFIER: The same pair returns REFUSED with `SEGMENT_SCHEME_MISMATCH`.

REPAIR: For `ratio`, compare `segment_scheme_version` whenever both sides carry it, matching the `same_fact` `elif` branch.

### X7-05 — MINOR

CLAIM: `test_mut4f_s2_seal_module_1` (and `_2`, `_3`) in the new MUT4F file pin imported constants, so a mutant that keeps the name and changes only runtime use of the constant still passes.

EVIDENCE: `tests/test_sni_mutation_report_s2seal.py:261-273`:

```
def test_mut4f_s2_seal_module_1():
    """s2_seal.py:216, INFO_LEAK_STEP_TOLERANCE `1e-6` -> `1e-6*1.001`."""
    assert INFO_LEAK_STEP_TOLERANCE == 1e-6
```

The test never calls `info_leak_scan` or compares a step against the tolerance. Bounds: this one test in `tests/test_sni_mutation_report_s2seal.py`; `_2` and `_3` are the same shape for `TRAILING63_SESSIONS` and `MIN_TRAIN_CLUSTERS_POOLED_PRIOR`.

FALSIFIER: Show a call-path assertion in that test that fails when the constant is 1e-6*1.001 at use, even if the module attribute is restored.

REPAIR: Drive `OutcomeEngine.info_leak_scan` (or the S2 seal consumer) with a step of 1e-6 and 1e-6*1.001 and assert the leak bit.

### X7-06 — MINOR

CLAIM: `test_mut4b_s1_synth_module_2` pins source text of `sys.path.insert(0, …)` via AST, not the import behaviour.

EVIDENCE: `tests/test_sni_mutation_manifest_synth.py:185-199` reads `Path(s1_synth.__file__).read_text`, walks `ast.Call` nodes, and asserts `0 in zeros`. A mutant that inserts at 0 via a name (`POS = 0; sys.path.insert(POS, p)`) keeps behaviour and fails the test; a mutant that inserts at 0 then immediately reorders `sys.path` keeps the AST literal and passes.

FALSIFIER: The test imports `s1_synth` under a poisoned `sys.path` and asserts residual still wins, without reading the `.py` file.

REPAIR: Replace the AST walk with a behavioural import-order probe (the schk_09 pattern).

### X7-07 — MAJOR

CLAIM: Two INT3-touched `tests/test_sni_*.py` files on `5b6fd2e` are in neither the `paths` list nor the run line of `sni-acceptance-evidence`, including the file that carries schk_09, schk_10, and the failing schk_05; 45 of 78 `tests/test_sni_*.py` files on that commit are absent from that job.

EVIDENCE: `.github/ci/legacy-jobs.yml` job `sni-acceptance-evidence` (from line 26355). `paths` list of `tests/test_sni_*.py` has 33 entries; the pytest run line has the same 33 (`set(paths)==set(run)`). INT3 `git diff --name-only e4c2f67..5b6fd2e -- tests/test_sni_*.py` is 21 files; of those, `tests/test_sni_seal_full_check.py` and `tests/test_sni_injection_safety.py` are False/False for paths and run. No listed non-glob path is missing from the tree. `test_schk_05` (X7-01) lives in the unwired file. `python3 -m pytest tests/test_ci_pack.py -k curated_exclusive -q -p no:cacheprovider` : `test_the_curated_exclusive_set_is_actually_declared` passed; `test_curated_exclusive_scopes_cover_their_own_import_closure` raised `ValueError: information-to-price-eval-receipts derives no closure — curation cannot be checked` on this sparse worktree (unrelated job; see GAPS).

FALSIFIER: Both INT3-touched files appear in the job's `paths:` and in the pytest run line on `5b6fd2e`, and `ls tests/test_sni_*.py` equals that list.

REPAIR: Add `tests/test_sni_seal_full_check.py` (and the four-line INT3 edit `tests/test_sni_injection_safety.py`) to both the `paths` list and the run line, or document a named exclusion for regen tests that need the input_ref.

### X7-08 — NIT

CLAIM: `check_join` returns ALLOWED when `scale` is int `1` on one side and `True` on the other, because `True == 1`.

EVIDENCE: `/tmp` probe `true-vs-1 ALLOWED ()`. `_add_eq_mismatch` uses `!=` (`sni_join_guard.py:314`). `1 != True` is False in Python. `scale=0` vs `scale="0"` is REFUSED (`SCALE_MISMATCH`).

FALSIFIER: The pair returns REFUSED with `SCALE_MISMATCH`.

REPAIR: Compare `(type(left), left)` or reject non-str / non-int scale in `validate_fact`.

## CHECKED-CLEAN

### Attack 1 — residual tree pin (bounds: `e4c2f67..5b6fd2e` on `research/single_name_intelligence/residual/`, plus `git rev-parse 5b6fd2e:research/single_name_intelligence/residual`)

`git diff --stat e4c2f672bed06eef3fac0b7bb88d46275a228f28..5b6fd2e8798886141e074d50a4468c063d44ad28 -- research/single_name_intelligence/residual/` printed no rows. `git rev-parse 5b6fd2e8798886141e074d50a4468c063d44ad28:research/single_name_intelligence/residual` equals `f9f4bf6442a948b7500228f9f963fc50a2ac7168`. S1FIX is not on this head. ULP drift on regen is X7-01; the tree hash itself matches the v1.1 stamp. `test_schk_10_residual_tree_is_the_sealed_v1_1_runner` passed in `tests/test_sni_seal_full_check.py` (9 passed, 1 failed = schk_05).

### Attack 2 — S2 seal bytes on sealed inputs (bounds: INT3 `event_response/` file list; `EVENT_CENSUS.json` 7 rows; `seal_full_check.py --study all` S2 stanza)

S2 regen: 23 compared, 0 failures, 0 ULP, 22 identical, 2 named-exception passes. Census `session_part_hk` values seen: `after_close`, `pre_open`, `null`. No census `t_avail` lands on a published HK half-day or in 12:00–13:00 HKT, so the half-day `session_part` branch cannot rewrite sealed census bytes on this input. Non-finite abstain and the leak-scan window change are likewise untriggered (X7-02 is the stale-branch point, not a byte mismatch).

### Attack 3 — HK half-day clock law (bounds: `s2_clocklaw.session_part` + `lib.exchange_holidays.early_close` over 2019-01-01..2027-12-31; constructed HKT stamps below)

`MARKET_HK == "HK"`. Owner HK half-days in that span, all `time(12, 10)`: 2026-02-16, 2026-12-24, 2026-12-31, 2027-02-05, 2027-12-24, 2027-12-31. No date is in both `_HALF_NAMES` and `_ANNOUNCED` for HK 2026/2027. Probes on 2026-02-16 (half) and 2026-02-13 (full session):

| local HKT | day | session_part | first_session_after |
| --- | --- | --- | --- |
| 11:59 | 2026-02-16 half | in_session | 2026-02-20 |
| 12:00 | 2026-02-16 half | in_session | 2026-02-20 |
| 12:09 | 2026-02-16 half | in_session | 2026-02-20 |
| 12:10 | 2026-02-16 half | after_close | 2026-02-20 |
| 12:11 | 2026-02-16 half | after_close | 2026-02-20 |
| 12:00 | 2026-02-13 full | midday_break | 2026-02-16 |
| 13:00 | 2026-02-13 full | in_session | 2026-02-16 |

`12:09:59.999999` → in_session; `12:10:00` → after_close. `first_session_after` does not read `early_close` (open-only; `s2_clocklaw.py:71-82`). 2024-02-09 `early_close` is None; 12:05 HKT → midday_break — already named `test_clk_03_hk_half_days` strict xfail (A12-GAP, owner has no 2024 notice). Typhoon/halt: `session_part` does not consult `is_session`; `test_clk_08_halt_gap_named` is a strict xfail. Unscheduled closures are outside the owner table this module consumes.

### Attack 4 — join-guard refusals that held (bounds: synthetic A09 `_base_fact` pairs; join_kinds `same_fact`/`ratio`/`time_series`; None, `""`, `" "`, case, Cyrillic A, ZWSP, fullwidth CNY, `0` vs `"0"`, `123` vs `"123"`)

REFUSED as intended: issuer/period_end/period_start(both set)/basis/currency/scale/denominator/security-counter/unlinked-version mismatches; None or `""` issuer (`LEFT:ISSUER_UNRESOLVED`); whitespace vs real id (`ISSUER_MISMATCH`); case, Cyrillic look-alike, ZWSP, fullwidth currency, numeric-vs-string scale and issuer. `time_series` different periods ALLOWED (positive control `test_a09_positive_time_series`). Issuer-level different `counter_id` ALLOWED (documented `test_a09_e1p6_e2p6_issuer_level_ignores_counter`). Ratio one-sided segment ALLOWED (documented `test_a09_positive_ratio`). Linked `supersedes` ALLOWED (documented). Holes that returned ALLOWED on a real mismatch are X7-03, X7-04, X7-08.

### Attack 5 — mutation file that asserts behaviour (bounds: one test in `tests/test_sni_mutation_s2_state_loaders.py`)

`test_mut4a_s2_state_compute_state_1` (`tests/test_sni_mutation_s2_state_loaders.py:89-92`) calls `compute_state` on a synthetic empty loader and expects `SystemExit` matching `seal pins`. That is a behaviour assertion, not a source-string pin. (X7-05 and X7-06 are the two files that did not.)

### Attack 6 — listed CI paths exist; INT3-new tests other than the two misses are wired (bounds: 78 `tests/test_sni_*.py` on `5b6fd2e`; 33-entry job lists; 21 INT3-touched test files)

The 33 `paths` entries equal the 33 run-line files. Zero listed non-glob job paths are missing from the tree. Of 21 INT3-touched `test_sni_*.py` files, 19 are on both lists. The two misses and the 45/78 remainder are X7-07.

### Attack 7 — authority, public surface, ticker branches, prose (bounds: `git diff e4c2f67..5b6fd2e` added lines in `*.py`/`*.md`; `git diff --stat` on `site/` `mockups/` `docs/`)

No added production assignment of an authority flag to a value other than literal `False`. `True` appears only as refuse-payloads in tests (`tests/test_sni_injection_safety_ext.py`, join-guard/authority tests). `git diff --stat … -- site/ mockups/ docs/` is empty. No new `if ticker == …` / `== "BABA"` branch in INT3 production files; `0700`/`tcehy`/`tme` literals in the INT3 py diff are identity-hardening test tokens and pre-existing S2 series names (`("BABA", self.baba_close, …)` in `s2_outcomes.py`). Added prose uses "signal"/"forecast" only in authority-denial sentences. The substring `validated` does not appear as a claim of a statistic.

### Attack 8 — suite xfails other than A20B-F1 (bounds: `pytest.mark.xfail` / `pytest.xfail` / `pytest.skip` under `tests/test_sni_*.py`)

Known open: `test_a20b_08_loader_authority_smuggle_refused_or_not_true[p04]` strict xfail, reason A20B-F1 (`p04_v2_draft_loader.py:186` does not walk smuggled `*_authority` keys). Other xfails that fired in the 96: A12-GAP `test_clk_03_hk_half_days` (no 2024 HK notice); A12-GAP `test_clk_08_halt_gap_named`; `test_clk_02_hk_holidays` params 2024-02-12 and 2024-02-13 (calendar vs published LNY closures); IRP-GAP4 P03 IPCA rows and S2 episode-excess fields; IRP-F4 identical interval under a different seed; IRP-GAP P03 IPCA / S2 `literal_row_count` / S2 excluded-and-listed identities in `test_sni_independent_repro.py`; conditional `pytest.xfail` in `test_sni_p03_ulp_stability.py` (near-threshold) and `test_sni_dual_counter_property.py` (DCP-F1 ads_ratio path). One skip: `test_a20b_09_seal_full_check_study_requires_committed_runs` (explicit skip; regen needs input_ref, not synthetic JSON).

## What this review does NOT prove

This review does not move an acceptance row, cut a seal, or register a runner. ULP-equivalent P03 files are descriptive float-token differences, not a causal claim, a news-impact claim, or a forecast. Join-guard ALLOWED/REFUSED is a DRAFT library verdict; owners on main still join without calling it. S2 byte identity on v1.1 inputs does not prove the half-day or non-finite branches. `sni-acceptance-evidence` remaining green does not prove schk_05/09/10 ran. Sparse-worktree `test_curated_exclusive_scopes_cover_their_own_import_closure` is not a verdict on that job's SNI paths. Historical facts after a date were not treated as then-known. Identity ids in fixtures are opaque synthetic strings; this lane did not mint HK/US issuer or security identifiers.
