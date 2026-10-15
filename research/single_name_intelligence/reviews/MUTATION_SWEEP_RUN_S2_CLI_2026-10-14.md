# M6A mutation sweep — `run_s2.py` S2 CLI (`main`, `run_check`, `refuse_data_path`, `_fmt`) — 2026-10-14

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer suite against the four S2 CLI functions in
`event_response/run_s2.py` that the 2026-10-13 coverage census marked
as NEVER-EXECUTED (`main` L1089-1120, `run_check` L1058-1086,
`refuse_data_path` L92-102, `_fmt` L743-748). It does not move any
acceptance row to DONE. Authority flags stay false; identity ids remain
caller-supplied opaque strings owned by Stock Identity / Data OS.
Fixtures in the killing tests are synthetic. Residuals and event-study
numbers are descriptive, never causal, never a news-impact claim (A24).
An unestimable family still ABSTAINS (A25).

`run_s2.py` is an SNI-local DRAFT runner that CONSUMES owner-supplied
values (pinned blob ids, sealed membership tables, opaque issuer keys).
This sweep does not re-implement Data OS identity, Company Event/Earnings,
FIF, Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation.

Existing tests that import `run_s2`:

- `tests/test_sni_s2_abstain.py` — `abstention_state`, `build_block`, `plain_word_null`
- `tests/test_sni_s2_info_leak.py` — `maybe_log_retirement`
- `tests/test_sni_quarantine_fence.py` — `render_report`
- `tests/test_sni_s2_seal_integrity.py` — `verify_seal`
- `tests/test_sni_s2_v1_1_hardening.py` — `generate_outputs`, `verify_seal`, `render_report`, `multiplicity_sentence`
- `tests/test_sni_mutation_run_s2_a.py` (MUT5D) — 13 killing tests
- `tests/test_sni_mutation_run_s2_b.py` (MUT5E) — 15 killing tests

`tests/test_sni_injection_safety.py` names `event_response/run_s2.py` as
a string and does not import it; it was kept out of the kill suite.

Owned site range: the four functions `main`, `run_check`,
`refuse_data_path`, `_fmt` (line ranges as listed by the 2026-10-13
census). 31 candidate sites; 30 selected under the cap. Unmutated
importer tests: 81 passed in 4.94 s (well under the 20 s cap, so the
30-mutant budget applied). New killing tests: 8 passed in 0.60 s on
unmutated code. Importer tests plus the new file: 89 passed in 3.28 s
(0 new failures).

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study s2 --strict-bytes` →
`s2: files compared=23 identical=22 named-exception passes=2 ulp-equivalent=0 failures=0 [Linux x86_64]`
→ `SEAL FULL CHECK: OK`.
`--study all` reports `SEAL FULL CHECK: DIFFERS` because the sparse
worktree's S1 regen produces 11 S1 bytes-diffs (LANE_MANIFEST.json,
P03 observations and results); S1 sits outside this lane's owned range
and the S2 portion passes 0 failures. See DEVIATIONS.

## Summary

| item | count |
|---|---|
| generated (selected) | 30 |
| killed-before | 23 |
| survived-before | 7 |
| killed-after | 7 |
| equivalent | 0 |
| timeout | 0 |
| timeout-unsafe | 0 |
| score before | 23/30 = 76.7% |
| score after | 30/30 = 100% |
| new killing tests | 8 |

Candidate sites before sampling: 31 in the owned function range. 1
unselected site is unscored.

## Operator set and seed

Seed: `20261014`. Max 30 mutants, stratified by function (round-robin
over `sorted(function names)`, sites shuffled per function with the same
RNG). Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`,
  `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard

Annotations and docstrings were not mutated. `is` / `in` / `**` are
outside the operator set.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_s2_abstain.py`
- `tests/test_sni_s2_info_leak.py`
- `tests/test_sni_s2_seal_integrity.py`
- `tests/test_sni_s2_v1_1_hardening.py`
- `tests/test_sni_quarantine_fence.py`
- `tests/test_sni_mutation_run_s2_a.py`
- `tests/test_sni_mutation_run_s2_b.py`

Harness (scratch only, `~/lanes/scratch/m6a/harness.py`, not committed):
applies each mutant in place, then runs the kill suite under a 60 s
timeout, then restores the original bytes and sha256-checks before the
next. After every mutant, `git status --porcelain -- research/` was
compared; any dirty path other than the mutated module would have been
restored and classified TIMEOUT-UNSAFE. None occurred. Wall-clock of the
30 runs: 152.4 s.

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `run_s2.py` (owned range) | 31 | 30 | 23 | 7 | 0 | 0 | 7 | 23/30 → 30/30 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| run_s2 | `refuse_data_path` | 4 | 3 |
| run_s2 | `_fmt` | 1 | 1 |
| run_s2 | `run_check` | 14 | 14 |
| run_s2 | `main` | 12 | 12 |

## Surviving-mutant list with killing test name

All 7 non-equivalent survivors were re-applied after the new tests were
added and failed the named test (7/7 KILLED-AFTER).

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| run_s2_02 | `run_s2.py:1092` | `main` | `required=True` → `False` (`--out-dir`) | `test_m6a_run_s2_main_1` |
| run_s2_07 | `run_s2.py:1078` | `run_check` | `sort_keys=True` (1st) → `False` | `test_m6a_run_s2_run_check_2` |
| run_s2_08 | `run_s2.py:1093` | `main` | `required=True` → `False` (`--trial-ledger-path`) | `test_m6a_run_s2_main_2` |
| run_s2_16 | `run_s2.py:1105` | `main` | `return 2` → `return None` | `test_m6a_run_s2_main_3` |
| run_s2_17 | `run_s2.py:1078` | `run_check` | `sort_keys=True` (2nd) → `False` | `test_m6a_run_s2_run_check_1` |
| run_s2_20 | `run_s2.py:1105` | `main` | `2` → `3` (exit code literal) | `test_m6a_run_s2_main_4` |
| run_s2_22 | `run_s2.py:1117` | `main` | `parents=True` → `False` (the other True) | `test_m6a_run_s2_main_6` |

Re-verify FAIL lines (two samples; all 7 killed):

- run_s2_16 / `test_m6a_run_s2_main_3`:
  `assert None == 2` (`main()` returns None, not 2, when the mutant fires)
- run_s2_20 / `test_m6a_run_s2_main_3`:
  `assert 3 == 2` (the same test observes the exit code changed from 2 to 3)

The two `sort_keys=True` constants on line 1078 sit on opposite sides of
the same comparison, so each killing test runs the data in a different
key-insertion direction; together they pin both sides of the
canonicalization. Two further L1117 survivors were already covered
(`exist_ok=True` by `test_mut5e_run_s2_main_2`, the other True constants
on lines 1092/1093/1102 by `test_mut5e_run_s2_main_1` and the
`--repo-root`/`--out-dir` argparse paths in the importer suite).

## Equivalent arguments

None. Every selected survivor was distinguishable by a targeted test;
both `sort_keys=True` constants (run_s2_07 and run_s2_17) were
distinguishable by a mirrored data-direction test, and both `True`
constants on `out_dir.mkdir(parents=True, exist_ok=True)` (the second
of which was already killed by `test_mut5e_run_s2_main_2`) were
distinguishable by an additional non-existing-parent scenario.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
census point 19 is `event_response/run_s2.py:941` (report prose names a
TUNE census window that crosses 2026-10-01). That line sits in
`render_report`, outside this lane's owned range. No QF point lies
inside the four owned functions. **No mutant sites were excluded under
the QF fence.**

## What this does NOT prove

Mutation score is test strength against this operator set and this
stratified 30-site sample, not statistical validity of S2 hit-rate
tests, pooled TRAIN prior, or sealed prereg bytes. The single
unselected site (`_fmt` had 1 of 1 selected; one extra `cmp` site for
`refuse_data_path` was unselected and unscored) is unscored. The
MUT5D/MUT5E `run_s2` sweep already covered functions defined before
line 481; this lane is the focused follow-up on the four CLI-entry
functions the 2026-10-13 census listed as UNTESTED. No
acceptance-matrix row moves to DONE. Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.
