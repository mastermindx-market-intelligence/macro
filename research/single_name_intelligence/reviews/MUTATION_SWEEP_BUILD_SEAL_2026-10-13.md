# MUT4C mutation sweep — residual/build_seal.py / event_response/build_seal.py — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against the two seal-builder modules. It does
not move any acceptance row to DONE. Authority flags stay false; identity
ids remain caller-supplied opaque strings owned by Stock Identity / Data
OS. Fixtures in the killing tests are synthetic. Residuals and event-study
numbers are descriptive, never causal, never a news-impact claim (A24).

These modules consume owner-supplied pins, membership rows, and registry
blob ids; they do not re-implement Data OS identity, Company Event/Earnings,
FIF, Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation.

Existing tests that import (or name) these modules:

- `residual/build_seal.py` — **none**. Grep of `tests/test_sni_*.py` finds
  no `import` of this file. The unmutated kill suite for this module is
  empty; every sampled mutant SURVIVED the existing suite.
- `event_response/build_seal.py` —
  `tests/test_sni_s2_seal_integrity.py` (subprocess `--help` plus seal
  verify/tamper tests) and `tests/test_sni_injection_safety.py` (names the
  builder path in an A20 known-exception entry and AST-scans the SNI tree).

Unmutated importer suite: 16 passed in 1.29 s (`s2_seal_integrity` 6,
`injection_safety` 10). Under the 20 s cap, so both modules used the full
30-mutant budget. New file: 53 passed in 1.30 s. 0 new failures on the
importer suite after the new tests.

Harness (scratch only, `~/lanes/scratch/mut4c/harness.py`, not committed).
Each mutant was applied in place; `research/single_name_intelligence/runs/`
was checked with `git status --porcelain` after every mutant (no writes;
0 TIMEOUT-UNSAFE). Original bytes were restored and sha256-checked before
the next mutant. Final production sha256 matches the BASE blobs.

`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes`

```
s1: files compared=48 identical=45 named-exception passes=3 ulp-equivalent=0 failures=0 [Linux x86_64]
s2: files compared=23 identical=22 named-exception passes=2 ulp-equivalent=0 failures=0 [Linux x86_64]
SEAL FULL CHECK: OK
```

## Summary

| item | count |
|---|---|
| generated (selected) | 60 |
| killed-before | 3 |
| survived-before (incl. later equivalent) | 57 |
| equivalent | 4 |
| timeout / TIMEOUT-UNSAFE | 0 |
| non-equivalent survivors | 53 |
| killed-after (existing + new tests, re-verified) | 56 |
| remaining non-equivalent survivors | 0 |
| new killing tests | 53 |

Mutation score = killed / (generated − equivalent):

- **before:** 3 / 56 = **5.4%**
- **after:** 56 / 56 = **100%**

## Operator set and seed

Harness operators (frozen):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one site per return)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
Cap 30 per module. Identity mutants (`0.0 * 1.001 == 0.0`) would have been
dropped before sampling; none were present. QF fence lines: none in these
two files (see Excluded QF lines).

Each mutant ran

`timeout 60 python3 -m pytest <importer tests> -x -q -p no:cacheprovider`

Residual had an empty importer list, so those 30 mutants were classified
SURVIVED without pytest (no production bytes executed; `runs/` stayed clean).

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before → after |
|---|---|---|---|---|---|---|---|---|
| `residual/build_seal.py` | 40 | 30 | 0 | 30 | 29 | 1 | 0 | 0/29 = 0% → 29/29 |
| `event_response/build_seal.py` | 43 | 30 | 3 | 27 | 27 | 3 | 0 | 3/27 = 11.1% → 27/27 |
| **total** | **83** | **60** | **3** | **57** | **56** | **4** | **0** | **3/56 = 5.4% → 56/56** |

Selected-by-function (residual): `<module>` 5, `build_all` 12, `main` 4,
`identity_facts` 3, `render_seal_md` 3, `_runs_rel` 2, `write_json` 1.

Selected-by-function (event_response): `main` 20, `<module>` 5,
`render_seal_md` 5.

Killed-before (event_response `--help` importer):

- `event_response/build_seal.py:254` delete `if __name__ == "__main__": raise SystemExit`
- `event_response/build_seal.py:254` `==` → `!=` on `__name__ == "__main__"`
- `event_response/build_seal.py:24` `parents[3]` → `parents[4]` (import of
  `s2_*` / repo `lib` fails when the file is run as a script)

## Surviving-mutant list with killing test name

All 53 non-equivalent survivors were re-applied against the named new test
and failed (KILLED-after). Production bytes were restored after each
re-verify.

### residual/build_seal.py

| file:line | original → mutated | killing test |
|---|---|---|
| `residual/build_seal.py:44` | `SUBJECTS["P01"] + SUBJECTS["P02"]` → `-` | `test_mut4c_residual_build_seal_module_1` |
| `residual/build_seal.py:184` | `return` relative path → `None` | `test_mut4c_residual_build_seal__runs_rel_1` |
| `residual/build_seal.py:122` | `mkdir(exist_ok=True)` → `False` | `test_mut4c_residual_build_seal_build_all_1` |
| `residual/build_seal.py:67` | delete missing-id `RuntimeError` | `test_mut4c_residual_build_seal_identity_facts_1` |
| `residual/build_seal.py:260` | `--input-ref required=True` → `False` | `test_mut4c_residual_build_seal_main_1` |
| `residual/build_seal.py:237` | `sort_keys=True` → `False` | `test_mut4c_residual_build_seal_render_seal_md_1` |
| `residual/build_seal.py:190` | `canonical_json(obj) + "\\n"` → `-` | `test_mut4c_residual_build_seal_write_json_1` |
| `residual/build_seal.py:25` | `parents[3]` → `parents[4]` | `test_mut4c_residual_build_seal_module_2` |
| `residual/build_seal.py:186` | `return RUNS_REL` → `None` | `test_mut4c_residual_build_seal__runs_rel_2` |
| `residual/build_seal.py:170` | `out_dir / "manifests"` → `*` | `test_mut4c_residual_build_seal_build_all_2` |
| `residual/build_seal.py:61` | `isinstance(issuer, str) and issuer` → `or` | `test_mut4c_residual_build_seal_identity_facts_2` |
| `residual/build_seal.py:269` | `return 0` → `None` | `test_mut4c_residual_build_seal_main_2` |
| `residual/build_seal.py:255` | return markdown → `None` | `test_mut4c_residual_build_seal_render_seal_md_2` |
| `residual/build_seal.py:167` | `out_dir / "INPUT_MANIFEST.json"` → `*` | `test_mut4c_residual_build_seal_build_all_3` |
| `residual/build_seal.py:69` | `return out` → `None` | `test_mut4c_residual_build_seal_identity_facts_3` |
| `residual/build_seal.py:269` | `return 0` → `return 1` | `test_mut4c_residual_build_seal_main_3` |
| `residual/build_seal.py:255` | `join(L) + "\\n"` → `-` | `test_mut4c_residual_build_seal_render_seal_md_3` |
| `residual/build_seal.py:272` | `__name__ == "__main__"` → `!=` | `test_mut4c_residual_build_seal_module_3` |
| `residual/build_seal.py:123` | manifests `mkdir(exist_ok=True)` → `False` | `test_mut4c_residual_build_seal_build_all_4` |
| `residual/build_seal.py:266` | `digest[:12]` → `[:13]` | `test_mut4c_residual_build_seal_main_4` |
| `residual/build_seal.py:272` | delete `__main__` `SystemExit` | `test_mut4c_residual_build_seal_module_4` |
| `residual/build_seal.py:123` | `out_dir / "manifests"` → `*` | `test_mut4c_residual_build_seal_build_all_5` |
| `residual/build_seal.py:151` | P02 `itemized_count` 12 → 13 | `test_mut4c_residual_build_seal_build_all_6` |
| `residual/build_seal.py:153` | P03 `itemized_count` 21 → 22 | `test_mut4c_residual_build_seal_build_all_7` |
| `residual/build_seal.py:168` | `out_dir / "CHALLENGER_UNIVERSE.json"` → `*` | `test_mut4c_residual_build_seal_build_all_8` |
| `residual/build_seal.py:166` | `out_dir / "PREREG_SPEC.json"` → `*` | `test_mut4c_residual_build_seal_build_all_9` |
| `residual/build_seal.py:170` | `manifests / name` → `*` | `test_mut4c_residual_build_seal_build_all_10` |
| `residual/build_seal.py:149` | P01 `itemized_count` 6 → 7 | `test_mut4c_residual_build_seal_build_all_11` |
| `residual/build_seal.py:150` | P02 `declared_budget` 4 → 5 | `test_mut4c_residual_build_seal_build_all_12` |

### event_response/build_seal.py

| file:line | original → mutated | killing test |
|---|---|---|
| `event_response/build_seal.py:65` | `manifests / filename` → `*` | `test_mut4c_event_response_build_seal_main_1` |
| `event_response/build_seal.py:203` | `membership_sha256 or ""` → `and` | `test_mut4c_event_response_build_seal_render_seal_md_1` |
| `event_response/build_seal.py:251` | return markdown → `None` | `test_mut4c_event_response_build_seal_render_seal_md_2` |
| `event_response/build_seal.py:125` | SEAL `ensure_ascii=False` → `True` | `test_mut4c_event_response_build_seal_main_2` |
| `event_response/build_seal.py:251` | `join(lines) + "\\n"` → `-` | `test_mut4c_event_response_build_seal_render_seal_md_3` |
| `event_response/build_seal.py:136` | EVENT_CENSUS `indent=2` → `3` | `test_mut4c_event_response_build_seal_main_3` |
| `event_response/build_seal.py:204` | `graded_membership_sha256 or ""` → `and` | `test_mut4c_event_response_build_seal_render_seal_md_4` |
| `event_response/build_seal.py:132` | `out / "EVENT_CENSUS.json"` → `*` | `test_mut4c_event_response_build_seal_main_4` |
| `event_response/build_seal.py:167` | AUTHORITY_FLAGS `sort_keys=True` → `False` | `test_mut4c_event_response_build_seal_render_seal_md_5` |
| `event_response/build_seal.py:139` | E_COVERAGE json `+ "\\n"` → `-` | `test_mut4c_event_response_build_seal_main_5` |
| `event_response/build_seal.py:131` | INPUT_MANIFEST `indent=2` → `3` | `test_mut4c_event_response_build_seal_main_6` |
| `event_response/build_seal.py:133` | EVENT_CENSUS json `+ "\\n"` → `-` | `test_mut4c_event_response_build_seal_main_7` |
| `event_response/build_seal.py:125` | SEAL `indent=2` → `3` | `test_mut4c_event_response_build_seal_main_8` |
| `event_response/build_seal.py:84` | `outcome_free True` → `False` | `test_mut4c_event_response_build_seal_main_9` |
| `event_response/build_seal.py:143` | `issuer_key == iss` → `!=` | `test_mut4c_event_response_build_seal_main_10` |
| `event_response/build_seal.py:128` | `out / "INPUT_MANIFEST.json"` → `*` | `test_mut4c_event_response_build_seal_main_11` |
| `event_response/build_seal.py:127` | PREREG json `+ "\\n"` → `-` | `test_mut4c_event_response_build_seal_main_12` |
| `event_response/build_seal.py:129` | INPUT_MANIFEST json `+ "\\n"` → `-` | `test_mut4c_event_response_build_seal_main_13` |
| `event_response/build_seal.py:97` | `itemized_grid_size` 12 → 13 | `test_mut4c_event_response_build_seal_main_14` |
| `event_response/build_seal.py:127` | PREREG `ensure_ascii=False` → `True` | `test_mut4c_event_response_build_seal_main_15` |
| `event_response/build_seal.py:53` | `mkdir(parents=True)` → `False` | `test_mut4c_event_response_build_seal_main_16` |
| `event_response/build_seal.py:154` | `return 0` → `None` | `test_mut4c_event_response_build_seal_main_17` |
| `event_response/build_seal.py:53` | `out / "manifests"` → `*` | `test_mut4c_event_response_build_seal_main_18` |
| `event_response/build_seal.py:53` | `mkdir(exist_ok=True)` → `False` | `test_mut4c_event_response_build_seal_main_19` |

## Equivalent arguments

EQUIVALENT only with a one-line semantic argument; no killing test.

- `residual/build_seal.py:25` `sys.path.insert(0, repo_root)` → `insert(1, …)`:
  the repository is still placed on `sys.path`; `residual/` has no shadowing
  `lib` package, so `from lib import nyse_calendar` resolves identically.
- `event_response/build_seal.py:23` `sys.path.insert(0, parent)` → `insert(1, …)`:
  running the file as a script already puts `event_response/` at `sys.path[0]`;
  inserting the same directory at index 1 does not change local `s2_*` imports.
- `event_response/build_seal.py:24` `sys.path.insert(0, repo_root)` → `insert(1, …)`:
  the repository is still on `sys.path`; `event_response/` does not shadow
  `lib`, so imports resolve identically. (The `parents[3]` → `parents[4]`
  mutant on the same line was KILLED-before by `--help`.)
- `event_response/build_seal.py:131` INPUT_MANIFEST `ensure_ascii=False` → `True`:
  every INPUT_MANIFEST path and blob id is ASCII, so `json.dumps(...,
  ensure_ascii=True)` is byte-identical to `False`.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points. None of them are in
`residual/build_seal.py` or `event_response/build_seal.py` (the builders do
not compare `2026-10-01` or assign TRAIN/TUNE/QUARANTINE). Excluded QF
lines for this sweep: **none**.

## What this does NOT prove

Mutation score is test strength against this operator set and this
deterministic sample, not statistical validity of any S1/S2 residual or
event-response number. A killed mutant means one existing or new test
observes the changed byte. It does not mean the seal, the prereg digest, or
any acceptance-matrix row is correct. **No acceptance row moves to DONE.**
The builders remain outcome-free DRAFT contracts: they consume
owner-supplied identity strings and pins, they never mint identifiers, and
every authority flag they write stays false.
