# MUT4A mutation sweep — s2_state / s2_loaders — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against the two S2 event-state/loader modules. It
does not move any acceptance row to DONE. Authority flags stay false;
identity ids remain caller-supplied opaque strings owned by Stock Identity /
Data OS. Fixtures in the killing tests are synthetic. Residuals and
event-study numbers are descriptive, never causal, never a news-impact
claim (A24). An unestimable family still ABSTAINS (A25).

These modules consume owner-supplied values (pinned blob ids, metadata
columns, identity instants). This sweep does not re-implement Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity,
Options, Research Vault, or qledger/Evaluation.

Existing tests that import these modules:

- `tests/test_sni_s2_seal_integrity.py` — `GitBlobLoader`, `compute_state`
- `tests/test_sni_s2_v1_1_hardening.py` — `GitBlobLoader`, `compute_state`

`tests/test_sni_injection_safety.py` names `s2_state.py` in a docstring
and does not import either module; it was not in the kill suite.

Unmutated importer tests: 23 passed in 1.66 s (under the 20 s cap, so
the 30-mutant/module budget applied). New killing tests: 15 passed in
0.64 s on unmutated code. Importer tests after the new file: 23 passed
in 1.83 s (0 new failures).

## Summary

| item | count |
|---|---|
| generated (selected) | 36 |
| killed-before | 21 |
| survived-before | 15 |
| killed-after | 15 |
| equivalent | 0 |
| timeout | 0 |
| timeout-unsafe | 0 |
| score before | 21/36 = 58.3% |
| score after | 36/36 = 100% |
| new killing tests | 15 |

Candidate sites before sampling: 11 in `s2_state.py`, 25 in
`s2_loaders.py`. Both modules sat under the 30-site cap, so every
candidate was applied. Seed `20261013`, stratified by function.
No mutant wrote under `research/single_name_intelligence/runs/`.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut4a/harness.py`, not committed):

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
| `s2_state.py` | 11 | 11 | 10 | 1 | 1 | 0 | 0 | 10/11 | 11/11 |
| `s2_loaders.py` | 25 | 25 | 11 | 14 | 14 | 0 | 0 | 11/25 | 25/25 |
| **total** | **36** | **36** | **21** | **15** | **15** | **0** | **0** | **21/36** | **36/36** |

## Surviving-mutant list with killing test name

All 15 non-killed mutants were re-applied against the named new test and
failed (KILLED-after).

### s2_state.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s2_state.py:55` | delete `if got != want: raise SystemExit` (identity pin) | `test_mut4a_s2_state_compute_state_1` |

### s2_loaders.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s2_loaders.py:48` | `400` → `401` (`_git` stderr slice) | `test_mut4a_s2_loaders__git_1` |
| `s2_loaders.py:46` | delete `if proc.returncode != 0: raise` (`_git`) | `test_mut4a_s2_loaders__git_2` |
| `s2_loaders.py:68` | delete `if proc.returncode != 0: raise` (`GitBlobLoader.read_bytes`) | `test_mut4a_s2_loaders_read_bytes_1` |
| `s2_loaders.py:71` | `400` → `401` (`GitBlobLoader.read_bytes` stderr slice) | `test_mut4a_s2_loaders_read_bytes_2` |
| `s2_loaders.py:110` | `return self.inner.read_bytes(path)` → `return None` (`ColumnRequestSpy`) | `test_mut4a_s2_loaders_read_bytes_3` |
| `s2_loaders.py:83` | `return json.loads(...)` → `return None` (`GitBlobLoader.read_json`) | `test_mut4a_s2_loaders_read_json_1` |
| `s2_loaders.py:104` | `return self.inner.read_json(path)` → `return None` (`ColumnRequestSpy`) | `test_mut4a_s2_loaders_read_json_2` |
| `s2_loaders.py:98` | `return self.inner.read_parquet(...)` → `return None` (`ColumnRequestSpy`) | `test_mut4a_s2_loaders_read_parquet_1` |
| `s2_loaders.py:86` | `return self.read_bytes(path).decode(...)` → `return None` (`GitBlobLoader.read_text`) | `test_mut4a_s2_loaders_read_text_1` |
| `s2_loaders.py:107` | `return self.inner.read_text(path)` → `return None` (`ColumnRequestSpy`) | `test_mut4a_s2_loaders_read_text_2` |
| `s2_loaders.py:80` | `return yaml.safe_load(...)` → `return None` (`GitBlobLoader.read_yaml`) | `test_mut4a_s2_loaders_read_yaml_1` |
| `s2_loaders.py:101` | `return self.inner.read_yaml(path)` → `return None` (`ColumnRequestSpy`) | `test_mut4a_s2_loaders_read_yaml_2` |
| `s2_loaders.py:118` | `return out` → `return None` (`ColumnRequestSpy.requested_columns`) | `test_mut4a_s2_loaders_requested_columns_1` |
| `s2_loaders.py:35` | delete `if got != want: raise InputVerificationError` (`verify_pinned_blobs`) | `test_mut4a_s2_loaders_verify_pinned_blobs_1` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test. The two `400 → 401` stderr-slice mutants
are observable: a 500-byte synthetic stderr is truncated to 400 characters
in the raised message. The deleted identity-pin and blob-mismatch guards
are observable because the live importer path only exercises the matching
success case.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `s2_state.py` or `s2_loaders.py`.** No mutant sites were
excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
full-candidate sample, not statistical validity of SNI estimators. A
killed mutant does not mean a CI is well-calibrated and does not mean
the loader's git-cat-file path is a complete input-integrity proof. No
acceptance-matrix row moves to DONE. The sweep does not claim completeness
over operators outside this set (`in`/`not in`, `is None`, string
constants). `ColumnRequestSpy` and the yaml/text readers were unimported
by the existing kill suite; the new tests pin them with synthetic
fixtures. Nothing here feeds a ranker, gate, sizer, signal, escalation,
or trade path.
