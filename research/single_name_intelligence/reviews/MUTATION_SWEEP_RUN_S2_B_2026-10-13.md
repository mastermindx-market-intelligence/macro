# MUT5E mutation sweep — `run_s2.py` (generate_outputs..EOF) — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against the second half of the S2 evidence
runner (`generate_outputs` through `main`). It does not move any
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

Existing tests that import (or execute) this module:

- `tests/test_sni_s2_abstain.py` — `abstention_state`, `build_block`, `plain_word_null`
- `tests/test_sni_s2_info_leak.py` — `maybe_log_retirement`
- `tests/test_sni_quarantine_fence.py` — `render_report`
- `tests/test_sni_s2_seal_integrity.py` — `verify_seal`
- `tests/test_sni_s2_v1_1_hardening.py` — `generate_outputs`, `verify_seal`, `render_report`, `multiplicity_sentence`
- `tests/test_sni_s2_cli.py` — subprocess execution of `run_s2.py` (`main`)

`tests/test_sni_injection_safety.py` names `event_response/run_s2.py` as a
string and does not import it. `tests/test_sni_mutation_build_seal.py`
installs a fake `run_s2` module. Neither was in the kill suite.

Owned site range: functions defined from line 481 (`generate_outputs`) to
EOF. Unmutated importer tests: 57 passed in 4.36 s (under the 20 s cap,
so the 30-mutant budget applied). New killing tests: 15 passed in 1.19 s
on unmutated code. Importer tests plus the new file: 72 passed in 5.70 s
(0 new failures).

`python3 research/single_name_intelligence/evaluation/seal_full_check.py
--study all --strict-bytes` → `SEAL FULL CHECK: OK`.

## Summary

| item | count |
|---|---|
| generated (selected) | 30 |
| killed-before | 15 |
| survived-before | 15 |
| killed-after | 15 |
| equivalent | 0 |
| timeout | 0 |
| timeout-unsafe | 0 |
| score before | 15/30 = 50.0% |
| score after | 30/30 = 100% |
| new killing tests | 15 |

Candidate sites before sampling: 114 in the owned range of `run_s2.py`.
Seed `20261013`, stratified by function, cap 30. Wall-clock of the 30
runs: 130.2 s. No mutant wrote under `research/` other than the module
under test (0 TIMEOUT-UNSAFE).

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut5e/harness.py`, not committed):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per mutant)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.
After every mutant, `git status --porcelain -- research/` was compared;
any dirty path other than the mutated module would have been restored and
classified TIMEOUT-UNSAFE. None occurred.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `run_s2.py` (L481–EOF) | 114 | 30 | 15 | 15 | 15 | 0 | 0 | 15/30 | 30/30 |
| **total** | **114** | **30** | **15** | **15** | **15** | **0** | **0** | **15/30** | **30/30** |

Candidate counts by function (owned range): `generate_outputs` 29,
`render_report` 15, `run_check` 15, `main` 14, `verify_seal` 13,
`multiplicity_sentence` 11, `build_version_record` 9, `_fmt` 3,
`prereg_digest_of` 2, `render_observations` 2, `full_spec_digest` 1.

## Surviving-mutant list with killing test name

All 15 non-killed mutants were re-applied against the named new test and
failed (KILLED-after).

| file:line | original → mutated | killing test |
|---|---|---|
| `run_s2.py:589` | `indent=2` → `3` (`results` `json.dumps`) | `test_mut5e_run_s2_generate_outputs_1` |
| `run_s2.py:626` | `ensure_ascii=False` → `True` (`LANE_MANIFEST` dumps) | `test_mut5e_run_s2_generate_outputs_2` |
| `run_s2.py:720` | `digest == v1_digest` → `!=` | `test_mut5e_run_s2_build_version_record_1` |
| `run_s2.py:693` | `want != got` → `==` (mismatch append) | `test_mut5e_run_s2_build_version_record_2` |
| `run_s2.py:734` | `descriptive_only True` → `False` | `test_mut5e_run_s2_build_version_record_3` |
| `run_s2.py:747` | `return f"{x:+.6f}"` → `return None` | `test_mut5e_run_s2__fmt_1` |
| `run_s2.py:748` | `return str(x)` → `return None` | `test_mut5e_run_s2__fmt_2` |
| `run_s2.py:922` | `hit == 1` → `!=` | `test_mut5e_run_s2_render_report_1` |
| `run_s2.py:924` | `episode_key[:12]` → `[:13]` | `test_mut5e_run_s2_render_report_2` |
| `run_s2.py:993` | `retired_cells or set()` → `and` | `test_mut5e_run_s2_render_observations_1` |
| `run_s2.py:1081` | `"..." + ", ".join(problems)` → `-` | `test_mut5e_run_s2_run_check_1` |
| `run_s2.py:1072` | `tmp / "trial_ledger.jsonl"` → `*` | `test_mut5e_run_s2_run_check_2` |
| `run_s2.py:1078` | `json.dumps(la) != json.dumps(lb)` → `==` | `test_mut5e_run_s2_run_check_3` |
| `run_s2.py:1102` | `text=True` → `False` (`git rev-parse`) | `test_mut5e_run_s2_main_1` |
| `run_s2.py:1117` | `exist_ok=True` → `False` (`out_dir.mkdir`) | `test_mut5e_run_s2_main_2` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test. `_fmt` is uncalled by the importer suite
except the `None` branch (killed-before by import/error on a span that
broke the `return "—"` line). `run_check` is never invoked by the
importer suite (`--check` is not exercised), so Path-join, ledger-compare,
and the failed-print concat all survived until the new tests. `main`'s
`text=True` / `exist_ok=True` branches are skipped when tests pass
`--repo-root` and a fresh `--out-dir`.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
census point 19 is `event_response/run_s2.py:941` (report prose names a
TUNE census window that crosses 2026-10-01). That exact line was excluded
from the candidate set. No operator in this set produced a site on line
941 (the fence text is a string constant). Other QF points live in
`residual/`, `s2_seal.py`, `s2_splits.py`, and the S0 register — outside
this owned range.

## What this does NOT prove

Mutation score is test strength against this operator set and this
stratified 30-site sample, not statistical validity of SNI estimators. A
killed mutant does not mean a CI is well-calibrated and does not mean the
`--check` byte-compare is a complete seal proof. No acceptance-matrix row
moves to DONE. The sweep does not claim completeness over operators
outside this set (`in`/`not in`, `is None`, string constants) and does not
cover functions defined above line 481. Nothing here feeds a ranker,
gate, sizer, signal, escalation, or trade path.
