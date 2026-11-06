# MUT5A mutation sweep — `stress_set.py` post-IDRFIX — 2026-10-13

SNI-local DRAFT contract review. `us_stress/stress_set.py` consumes
owner-supplied closes, coverage-profile listing tokens, and caller-supplied
opaque identity strings (Stock Identity / Data OS); it does not mint issuer
or security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. Residuals are descriptive, never causal, never
a news-impact claim. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut5a/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. After every mutant run,
`git status --porcelain -- research/` was inspected; extra paths would have
been restored and classified TIMEOUT-UNSAFE (none occurred).

BASE `5b6fd2e8798886141e074d50a4468c063d44ad28`. IDRFIX landing commit on
this module: `c56c503be99b6f46a65f0d5197eb7607b3c83560` (functions
`_walk_refuse`, `check_profile`, `_ticker_refusal_key`,
`_reference_issuer_listings`, `load_profiles`, plus module hooks
`_REFUSE_NON_ASCII_KEYS` / `_STRIP_LEADING_ZEROS`). MUT2 sampled this
module before that repair; this lane re-sweeps the current bytes and
prioritises those functions.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 30 |
| killed-before (existing importer suite) | 21 |
| survived-before (non-equivalent) | 9 |
| killed-after (new `test_mut5a_*`, re-verified) | 9 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 21 / 30 = 70.0% |
| score after | 30 / 30 = 100% |
| new killing tests | 9 |

Score = killed / (generated − equivalent). Unmutated importer suite 10.79 s
(under the 20 s cap), so the module stayed at 30 mutants. 0 xfails.

`SEAL FULL CHECK: OK` from
`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes`.

## Operator set and seed

Seed: `20261013`. Max 30 mutants, stratified by function. IDRFIX functions
are drained first (round-robin over
`<module>`, `_walk_refuse`, `check_profile`, `_ticker_refusal_key`,
`_reference_issuer_listings`, `load_profiles`), then any remaining slots
would have come from other functions. The 30-cap filled entirely from
those six (38 candidate sites in IDRFIX functions; 30 sampled, 8 left).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (one non-None return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (body is only `Raise`, no `else`)

Kill suite (tests that import `stress_set`; `timeout 60 python3 -m pytest
<tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_us_stress.py`
- `tests/test_sni_us_stress_onboarding.py`
- `tests/test_sni_us_stress_then_known.py`
- `tests/test_sni_identity_refusals.py`
- `tests/test_sni_identity_refusals_hardening.py`
- `tests/test_sni_injection_safety_ext.py`
- `tests/test_sni_a07_then_known_exclusion.py`
- `tests/test_sni_missing_not_zero.py`
- `tests/test_sni_mutation_event_stress.py`

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `stress_set.py` | 375 | 30 | 21 | 9 | 0 | 0 | 9 | 21/30 = 70.0% → 30/30 = 100% |

Selected-by-function (IDRFIX-first drain):

| function | candidate sites | selected | of which survived-before |
|---|---:|---:|---:|
| `<module>` | 3 | 3 | 0 |
| `_walk_refuse` | 13 | 7 | 0 |
| `check_profile` | 7 | 6 | 4 |
| `_ticker_refusal_key` | 4 | 4 | 1 |
| `_reference_issuer_listings` | 7 | 6 | 2 |
| `load_profiles` | 4 | 4 | 2 |

Module-level sites were `_REFUSE_NON_ASCII_KEYS = True` (L71, killed),
`_STRIP_LEADING_ZEROS = True` (L72, killed), and `if __name__ == "__main__"`
(L1173, killed: flipping `==` to `!=` runs `main()` on import and the
importer suite INTERNALERRORs).

## Survivors with killing test

Each row was re-applied from the sampled site and failed the named test
(`python3 -m pytest tests/test_sni_mutation_stress_post_idrfix.py::<test> -q`).
New tests pass on unmutated bytes (9 passed).

| i | Site | Mutant | Killing test | Re-verify fail |
|---|---|---|---|---|
| 02 | `check_profile` L212 | `get("authority") or {}` → `and` | `test_mut5a_stress_set_check_profile_02` | `ValueError: authority must be a mapping` |
| 09 | `_ticker_refusal_key` L386 | `rsplit(".", 1)` → `rsplit(".", 2)` | `test_mut5a_stress_set__ticker_refusal_key_09` | `assert '700' == '0700.HK'` |
| 11 | `load_profiles` L457 | `is_file() and suffix in yml` → `or` | `test_mut5a_stress_set_load_profiles_11` | `assert {'extra', 'ok'} == {'ok'}` |
| 14 | `check_profile` L213 | delete `if not isinstance(auth, dict): raise` | `test_mut5a_stress_set_check_profile_14` | `DID NOT RAISE ValueError` |
| 16 | `_reference_issuer_listings` L423 | `not str or not strip` → `and` | `test_mut5a_stress_set__reference_issuer_listings_16` | `assert '' not in {'': frozenset({'ZZZ1'})}` |
| 17 | `load_profiles` L461 | delete `if not isinstance(payload, dict): raise` | `test_mut5a_stress_set_load_profiles_17` | `'int' object has no attribute 'get'` |
| 19 | `check_profile` L210 | delete `if not isinstance(profile, dict): raise` | `test_mut5a_stress_set_check_profile_19` | `'list' object has no attribute 'get'` |
| 27 | `check_profile` L227 | `return profile` → `return None` | `test_mut5a_stress_set_check_profile_27` | `assert None is {profile}` |
| 28 | `_reference_issuer_listings` L414 | `not is_file() or suffix not yml` → `and` | `test_mut5a_stress_set__reference_issuer_listings_28` | `'syntheticalpha' not in listings` |

## Equivalent arguments

None. Every sampled survivor had a reachable behavioural difference and a
killing test.

## Excluded QF lines

`QF_QUARANTINE_FENCE_2026-10-13.md` censuses 19 fence points, all in
`residual/`, `event_response/`, and `protocols/S0_PROTOCOL_REGISTER.md`.
Zero fence lines fall in `us_stress/stress_set.py`. No sites were excluded
on QF grounds.

## What this does NOT prove

- Mutation score is test strength against this operator set and sample, not
  statistical validity of any residual or stress number.
- No acceptance row moves to DONE.
- Completeness of the operator set (no unary `not` deletion, no `is`/`in`
  flips, no statement deletion beyond `if raise`).
- Every candidate in `stress_set.py` (30 of 375 sites). Non-IDRFIX
  functions were not sampled because the IDRFIX-first drain filled the cap.
- The 8 unsampled IDRFIX sites: `check_profile` L221 `and`;
  `_reference_issuer_listings` L407 third `/`; `_walk_refuse` L170 identity
  `del_raise`/`and`; `_walk_refuse` L168 authority `del_raise`/`or`/`!=`/
  `False`.
- Cross-host fallback of `_minimal_yaml_load` (PyYAML is present here).
- Behaviour against real Yahoo parquets (`data/` is absent; engines use
  synthetic frames).
- Anything about rank, gate, size, signal, escalation, or trade paths
  (this lane never writes those flags true).
- Identity minting (ids stay caller-supplied opaque strings).
