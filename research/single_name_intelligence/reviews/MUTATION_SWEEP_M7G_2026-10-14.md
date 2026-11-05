# MUTATION SWEEP M7G — sni_comparison_guard (2026-10-14)

Lane M7G of the SNI mutation-sweep family (method frozen across lanes
MUT1A-C, MUT2, MUT3A-C, MUT4A-F, MUT5A-F, JGMUT, M6A-M6J). Target:
`research/single_name_intelligence/common/sni_comparison_guard.py`
(A13 stale-FX / closed-market / proxy comparison-refusal DRAFT guard),
owned site range: **all functions**. No production code was changed; this
sweep only measures the killing strength of the module's test suite and
adds killing tests for the survivors.

## Summary

| metric | value |
|---|---|
| mutants generated (applied) | 40 |
| killed by existing suite (before) | 29 |
| survived (before) | 11 |
| killed after new tests (`tests/test_sni_mut7_g.py`) | 10 (each re-verified individually) |
| equivalent (with argument) | 1 |
| timeout | 0 |
| **score before** | **29/40 = 72.5%** |
| **score after** | **39/40 = 97.5%** raw; 39/39 = 100% excluding the one equivalent |

Importer-test set for the module: `tests/test_sni_comparison_guard.py`
(73 tests, 0.92 s unmutated — under the 20 s cap, so the full 40-mutan budget
applied; grep over `tests/test_sni_*.py` found no other importer).

## Operator set and seed

Operators (frozen method): comparison flip (`< ⇄ <=`, `> ⇄ >=`, `== ⇄ !=`),
arithmetic swap (`+ ⇄ -`, `* ⇄ /`), constant perturbation (int n → n+1,
float x → x·1.001, `True ⇄ False`), `return x` → `return None` (one return
statement per mutant), `and ⇄ or`, deletion of one `if …: raise` guard
(statement replaced by `pass`).

Candidate sites: 77, enumerated by AST (function bodies only, per the owned
site range) + tokenize for exact operator/constant spans. Selection:
deterministic `random.Random(20261015)`, shuffled within each function then
taken round-robin across functions (stratified), first 40 compile-valid
mutants applied. Each mutant was written in place, run under
`timeout 60 python3 -m pytest tests/test_sni_comparison_guard.py -x -q
-p no:cacheprovider`, then the original bytes were restored and the module
sha256 re-verified (`d686d566e932989508e106f093e8e12c003b75e680be21082032a65c99a03744`)
before the next mutant. The harness lives outside the repo
(`~/lanes/scratch/m7g/harness.py`, not committed).

## Per-module table

One module (`sni_comparison_guard`), 40 applied mutants:

| # | cand id | kind | function | line | original | mutated | before | after |
|---|---|---|---|---|---|---|---|---|
| 1 | 18 | boolop | `_as_aware_datetime` | L182 | `and` | `or` | KILLED | KILLED |
| 2 | 8 | const | `_as_date` | L149 | `10` | `11` | SURVIVED | KILLED-after |
| 3 | 13 | const | `_as_datetime` | L160 | `10` | `11` | SURVIVED | KILLED-after |
| 4 | 49 | ret | `_blank` | L141 | `False` | `None` | SURVIVED | KILLED-after |
| 5 | 22 | boolop | `_finite_positive_real` | L195 | `and` | `or` | KILLED | KILLED |
| 6 | 61 | ret | `_freeze_reasons` | L201 | `tuple(code for code in REASONS …)` | `None` | KILLED | KILLED |
| 7 | 35 | op | `_fx_reasons` | L267 | `!=` | `==` | KILLED | KILLED |
| 8 | 30 | op | `_leg_reasons` | L234 | `==` | `!=` | KILLED | KILLED |
| 9 | 28 | op | `_not_known_as_of` | L209 | `>` | `>=` | KILLED | KILLED |
| 10 | 52 | ret | `_present` | L145 | `not _blank(fact.get(key))` | `None` | KILLED | KILLED |
| 11 | 69 | ret | `authority_flags` | L133 | `AUTHORITY_FLAGS` | `None` | KILLED | KILLED |
| 12 | 73 | guard | `check_comparison` | L303 | `if not isinstance(right, Mapping): raise TypeError` | `pass` | SURVIVED | KILLED-after |
| 13 | 0 | const | `refuse_nonfalse_authority` | L101 | `False` | `True` | KILLED | KILLED |
| 14 | 56 | ret | `_as_aware_datetime` | L186 | `parsed` | `None` | KILLED | KILLED |
| 15 | 7 | op | `_as_date` | L149 | `<` | `<=` | SURVIVED | KILLED-after |
| 16 | 15 | const | `_as_datetime` | L167 | `1` | `2` | KILLED | KILLED |
| 17 | 5 | const | `_blank` | L141 | `False` | `True` | KILLED | KILLED |
| 18 | 20 | op | `_finite_positive_real` | L193 | `>` | `>=` | KILLED | KILLED |
| 19 | 65 | ret | `_fx_reasons` | L280 | `found` | `None` | KILLED | KILLED |
| 20 | 31 | boolop | `_leg_reasons` | L234 | `and` | `or` | KILLED | KILLED |
| 21 | 63 | ret | `_not_known_as_of` | L208 | `True` | `None` | KILLED | KILLED |
| 22 | 68 | ret | `check_comparison` | L338 | `ComparisonVerdict(allowed=not frozen, …)` | `None` | KILLED | KILLED |
| 23 | 70 | guard | `refuse_nonfalse_authority` | L108 | `if not isinstance(flags, Mapping): raise ValueError` | `pass` | SURVIVED | KILLED-after |
| 24 | 17 | op | `_as_aware_datetime` | L176 | `==` | `!=` | KILLED | KILLED |
| 25 | 6 | boolop | `_as_date` | L149 | `or` | `and` | SURVIVED | KILLED-after |
| 26 | 12 | op | `_as_datetime` | L160 | `==` | `!=` | KILLED | KILLED |
| 27 | 4 | const | `_blank` | L140 | `True` | `False` | KILLED | KILLED |
| 28 | 57 | ret | `_finite_positive_real` | L196 | `False` | `None` | SURVIVED | KILLED-after |
| 29 | 67 | ret | `_fx_reasons` | L256 | `found` | `None` | KILLED | KILLED |
| 30 | 64 | ret | `_leg_reasons` | L238 | `found` | `None` | KILLED | KILLED |
| 31 | 26 | boolop | `_not_known_as_of` | L207 | `or` | `and` | KILLED | KILLED |
| 32 | 48 | op | `check_comparison` | L335 | `>` | `>=` | KILLED | KILLED |
| 33 | 75 | guard | `refuse_nonfalse_authority` | L101 | `if value is not False: raise ValueError` | `pass` | SURVIVED | KILLED-after |
| 34 | 16 | boolop | `_as_aware_datetime` | L176 | `or` | `and` | KILLED | KILLED |
| 35 | 53 | ret | `_as_date` | L152 | `date.fromisoformat(text[:10])` | `None` | SURVIVED | KILLED-after |
| 36 | 55 | ret | `_as_datetime` | L169 | `datetime.fromisoformat(body)` | `None` | KILLED | KILLED |
| 37 | 3 | op | `_blank` | L139 | `==` | `!=` | KILLED | KILLED |
| 38 | 60 | ret | `_finite_positive_real` | L195 | `math.isfinite(value) and value > 0.0` | `None` | KILLED | KILLED |
| 39 | 66 | ret | `_fx_reasons` | L252 | `[]` | `None` | KILLED | KILLED |
| 40 | 29 | op | `_leg_reasons` | L214 | `*` | `/` | SURVIVED | EQUIVALENT |

## Surviving-mutant list with killing test

Every non-equivalent survivor has one targeted killing test in
`tests/test_sni_mut7_g.py`; each kill was re-verified by re-applying the
exact mutant and re-running that file (all 10 re-runs failed with rc=1,
exactly one failing test each).

| mutant | site | original → mutated | killing test |
|---|---|---|---|
| id=7 | `_as_date` L149:46 | `<` → `<=` | `test_m7g_sni_comparison_guard__as_date_7` |
| id=8 | `_as_date` L149:48 | `10` → `11` | `test_m7g_sni_comparison_guard__as_date_8` |
| id=53 | `_as_date` L152:15 | `return date.fromisoformat(text[:10])` → `return None` | `test_m7g_sni_comparison_guard__as_date_53` |
| id=6 | `_as_date` L149:33 | `or` → `and` | `test_m7g_sni_comparison_guard__as_date_6` |
| id=13 | `_as_datetime` L160:20 | `10` → `11` | `test_m7g_sni_comparison_guard__as_datetime_13` |
| id=49 | `_blank` L141:11 | `return False` → `return None` | `test_m7g_sni_comparison_guard__blank_49` |
| id=57 | `_finite_positive_real` L196:11 | `return False` → `return None` | `test_m7g_sni_comparison_guard__finite_positive_real_57` |
| id=70 | `refuse_nonfalse_authority` L108-109 | delete `if not isinstance(flags, Mapping): raise ValueError` | `test_m7g_sni_comparison_guard__refuse_nonfalse_authority_70` |
| id=75 | `refuse_nonfalse_authority` L101-105 | delete `if value is not False: raise ValueError` | `test_m7g_sni_comparison_guard__refuse_nonfalse_authority_75` |
| id=73 | `check_comparison` L303-304 | delete `if not isinstance(right, Mapping): raise TypeError` | `test_m7g_sni_comparison_guard__check_comparison_73` |

Why these survived: the `_as_date`/`_as_datetime` parse helpers are only
exercised indirectly, and their exact-10-char-input behavior is masked at
the public layer by `_as_aware_datetime`'s naive-datetime filter (a 10-char
date parses to a naive datetime, which the public layer already maps to
None); the deleted type/self-check guards are error-path contracts the
happy-path suite never trips; the `False`→`None` predicate returns are
indistinguishable to truthiness-based callers.

## Equivalent arguments

- **id=29** (`_leg_reasons` L214:4, `*` → `/`): the token is the PEP 570
  keyword-only marker in `_leg_reasons(leg, *, as_of, requested_role)`, not
  an arithmetic operator. Under the mutant `(leg, /, as_of,
  requested_role)`, only `leg` becomes positional-only — and every caller
  in the module passes `leg` positionally while `as_of`/`requested_role`
  remain keyword-capable, so no call site's behavior changes (verified by
  hand: `check_comparison` on a clean pair returns the same verdict under
  the mutant). Distinguishable only by introspection or by invoking the
  private helper with `leg=` as a keyword, which no caller does.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses fence points in the S1/S2 manifest, build-spec, and
event_response modules; it mentions `sni_comparison_guard` nowhere. **0
mutants were excluded** — no owned site in
`common/sni_comparison_guard.py` is a QF fence line.

## What this does NOT prove

- A mutation score measures TEST STRENGTH, not statistical validity: a
  higher score says the suite pins more of the module's local behavior,
  not that the A13 comparison-refusal idea is correct, calibrated, or
  predictive.
- 40 of 77 candidate sites were sampled (deterministic, stratified); the
  37 unsampled sites are unmeasured, and operators outside the frozen set
  (e.g., swapped argument order, off-by-one day, string mutations) were
  not tried.
- No acceptance row moves to DONE on this evidence; this sweep only
  strengthens the test behind rows that already cite
  `tests/test_sni_comparison_guard.py`.
- The equivalent classification for id=29 is an argument about calling
  convention, not a proof over all possible callers; a future caller that
  passes `leg=` by keyword would observe a difference.

## Verification receipts

- New tests unmutated: `python3 -m pytest tests/test_sni_mut7_g.py -q -p
  no:cacheprovider -rs` → 10 passed.
- Combined unmutated: `tests/test_sni_comparison_guard.py` +
  `tests/test_sni_mut7_g.py` → 83 passed, 0 failures.
- Seal: `python3 research/single_name_intelligence/evaluation/seal_full_check.py
  --study all --repo-root .` → `SEAL FULL CHECK: OK`.
- Module bytes before/after the whole sweep and before commit:
  sha256 `d686d566e932989508e106f093e8e12c003b75e680be21082032a65c99a03744`
  (identical to base 97e9d6e7c3d).
