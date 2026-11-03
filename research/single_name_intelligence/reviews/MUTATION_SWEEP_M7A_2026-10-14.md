# MUTATION_SWEEP_M7A_2026-10-14 — counter-relation + entitlement guards

SNI DRAFT mutation sweep, lane M7A (SNI commission 8659). Two target
modules, no production code changed; deliverables are
`tests/test_sni_mut7_a.py` (new killing tests) and this review.

Importer-test sets (grep over `tests/test_sni_*.py`; no other file imports
either module):

- `tests/test_sni_counter_relation_guard.py` — 38 tests, unmutated 1.46 s
- `tests/test_sni_entitlement_guard.py` — 39 tests, unmutated 0.81 s

Both are far under the 20 s cap, so the 15-mutant module cap did not apply.

## Summary

| measure | value |
|---|---|
| mutants generated | 60 (30 per module; caps 40/module, 60 total) |
| killed by the pre-existing suite (killed-before) | 36 |
| survived the pre-existing suite (survived-before) | 24 |
| killed-after (by `tests/test_sni_mut7_a.py`) | +16 → 52 total |
| equivalent | 8 |
| timeout | 0 |
| score before | 36/60 = **60.0%** |
| score after | 52/60 = **86.7%** (52/52 = 100% of non-equivalent mutants) |

New killing tests: 16 (`tests/test_sni_mut7_a.py`, all passing on unmutated
code; combined run with both existing suites: 93 passed, 0 failed).

## Operator set and seed

Operators (frozen method): comparison flip (`<`<->`>`, `<=`<->`>=`,
`==`<->`!=`); arithmetic swap (`+`<->`-`, `*`<->`/`); constant perturbation
(int `n`->`n+1`, float `x`->`x*1.001`, `True`<->`False`); `return x` ->
`return None`; `and`<->`or`; deletion of one `if ...: raise` guard
(replaced by `pass`).

Draw: candidate sites collected by AST walk over the whole owned range
(all functions plus module-level constants), stratified by enclosing
function, shuffled and drawn round-robin with `random.Random(20261015)`
(module order: counter_relation, then entitlement). No arithmetic (`+ - * /`)
sites exist in either module, so that operator drew zero mutants.

Harness: scratch AST rewriter outside the repo (`~/lanes/scratch/m7a/`,
not committed). Each mutant was applied in place inside the worktree, run
under `timeout 60 python3 -m pytest <importer tests> -x -q
-p no:cacheprovider`, then the original bytes were restored and the
module's sha256 was verified before the next mutant. Base sha256s
(confirmed identical after the sweep and before commit):

- `sni_counter_relation_guard.py` `aa641e954f79f342b7f1a09cf838569197921cb73cb0e1153f40eec7966361b0`
- `sni_entitlement_guard.py` `81db9627f2fabc95b44f3f19088848a569b7e368386b34a59f9b8d3783d235f7`

Every killed-after claim below was re-verified by re-applying the exact
drawn mutant and re-running only its named test (16/16 KILLED, rc=1).

## Per-module table

`K` = killed by existing suite; `S>K` = survived, then killed by the new
test named in the next section; `S=E` = survived, classified equivalent.

### counter_relation (`common/sni_counter_relation_guard.py`)

| # | site | operator | mutant | result |
|---|---|---|---|---|
| 1 | `<module>:61` | const | `False -> True` (AUTHORITY_FLAGS) | K |
| 2 | `refuse_nonfalse_authority:85` | guarddel | delete Mapping-check raise | S>K |
| 3 | `__post_init__:106` | guarddel | delete unknown-reason raise | K |
| 4 | `authority_flags:116` | retnone | `return AUTHORITY_FLAGS -> None` | K |
| 5 | `relation_key:121` | retnone | `return (a,b) -> None` | K |
| 6 | `_blank:126` | retnone | `return True -> None` | S>K |
| 7 | `_freeze_reasons:134` | retnone | `return tuple -> None` | K |
| 8 | `_as_date:143` | retnone | `return None -> None` | S=E |
| 9 | `_as_datetime:153` | retnone | `return datetime(...) -> None` | S=E |
| 10 | `_aware_datetime:165` | boolop | `or -> and` | K |
| 11 | `_members:181` | retnone | `return () -> None` | S>K |
| 12 | `_contains_both:196` | retnone | `return bool -> None` | K |
| 13 | `check_counter_relation:250` | boolop | `or -> and` (availability) | K |
| 14 | `<module>:58` | const | `False -> True` (AUTHORITY_FLAGS) | K |
| 15 | `refuse_nonfalse_authority:88` | guarddel | delete per-key raise | K |
| 16 | `relation_key:121` | cmpflip | `<= -> >=` | K |
| 17 | `_blank:129` | retnone | `return False -> None` | S>K |
| 18 | `_as_date:139` | retnone | `return None -> None` | S=E |
| 19 | `_as_datetime:158` | retnone | `return parsed -> None` | K |
| 20 | `_aware_datetime:172` | retnone | `return None -> None` | S=E |
| 21 | `_members:186` | guarddel | delete member-Mapping raise | K |
| 22 | `_contains_both:196` | boolop | `and -> or` | K |
| 23 | `check_counter_relation:275` | boolop | `and -> or` (echo) | K |
| 24 | `<module>:63` | const | `False -> True` (AUTHORITY_FLAGS) | K |
| 25 | `refuse_nonfalse_authority:78` | guarddel | delete AUTHORITY_FLAGS-loop raise | S>K |
| 26 | `_blank:127` | cmpflip | `== -> !=` | K |
| 27 | `_as_date:138` | boolop | `or -> and` | S>K |
| 28 | `_as_datetime:152` | retnone | `return None -> None` | S=E |
| 29 | `_aware_datetime:175` | retnone | `return parsed -> None` | K |
| 30 | `_members:182` | guarddel | delete str/bytes/Mapping raise | S>K |

18 killed-before, 12 survived-before, 7 killed-after, 5 equivalent.

### entitlement (`common/sni_entitlement_guard.py`)

| # | site | operator | mutant | result |
|---|---|---|---|---|
| 1 | `<module>:60` | const | `False -> True` (AUTHORITY_FLAGS) | K |
| 2 | `refuse_nonfalse_authority:85` | const | `False -> True` in `flags is None` | K |
| 3 | `__post_init__:109` | boolop | `and -> or` (payload refusal) | K |
| 4 | `authority_flags:114` | retnone | `return AUTHORITY_FLAGS -> None` | K |
| 5 | `_blank:122` | retnone | `return False -> None` | S>K |
| 6 | `_present:126` | retnone | `return not _blank(...) -> None` | K |
| 7 | `_freeze_reasons:131` | retnone | `return tuple -> None` | K |
| 8 | `_as_date:138` | const | `10 -> 11` in `text[:10]` | S>K |
| 9 | `_as_datetime:145` | retnone | `return None -> None` | S=E |
| 10 | `_aware_datetime:162` | cmpflip | `== -> !=` | K |
| 11 | `_document_entitled:180` | retnone | `return membership -> None` | K |
| 12 | `_add_window_reasons:187` | boolop | `or -> and` (valid_from) | K |
| 13 | `gate_access:216` | guarddel | delete request-Mapping raise | S>K |
| 14 | `<module>:59` | const | `False -> True` (AUTHORITY_FLAGS) | K |
| 15 | `refuse_nonfalse_authority:75` | guarddel | delete AUTHORITY_FLAGS-loop raise | S>K |
| 16 | `__post_init__:109` | guarddel | delete payload-on-refusal raise | K |
| 17 | `_blank:121` | const | `True -> False` | K |
| 18 | `_as_date:135` | const | `10 -> 11` in `len(text) < 10` | S>K |
| 19 | `_as_datetime:157` | retnone | `return None -> None` | S=E |
| 20 | `_aware_datetime:172` | retnone | `return None -> None` | K |
| 21 | `_document_entitled:179` | const | `False -> True` (container check) | S>K |
| 22 | `_add_window_reasons:197` | cmpflip | `>= -> <=` (revoked) | K |
| 23 | `gate_access:218` | guarddel | delete entitlement-Mapping raise | S>K |
| 24 | `<module>:92` | const | `@dataclass(frozen=True) -> frozen=False` | S>K |
| 25 | `refuse_nonfalse_authority:82` | guarddel | delete per-key raise | K |
| 26 | `_blank:121` | const | `True -> False` | K |
| 27 | `_as_date:140` | retnone | `return None -> None` | S=E |
| 28 | `_as_datetime:155` | retnone | `return parsed -> None` | K |
| 29 | `_aware_datetime:162` | boolop | `or -> and` | K |
| 30 | `_document_entitled:177` | retnone | `return False -> None` | S>K |

18 killed-before, 12 survived-before, 9 killed-after, 3 equivalent.

## Surviving-mutant list with killing test

| module | # | mutant (file:line, original -> mutated) | killing test |
|---|---|---|---|
| counter_relation | 2 | `:85` delete `if not isinstance(flags, Mapping): raise ValueError` | `test_m7a_counter_relation_refuse_nonfalse_authority_2` |
| counter_relation | 6 | `:126` `return True -> return None` (blank-None branch) | `test_m7a_counter_relation__blank_6` |
| counter_relation | 11 | `:181` `return () -> return None` (members None) | `test_m7a_counter_relation__members_11` |
| counter_relation | 17 | `:129` `return False -> return None` | `test_m7a_counter_relation__blank_17` |
| counter_relation | 25 | `:78` delete AUTHORITY_FLAGS-loop raise | `test_m7a_counter_relation_refuse_nonfalse_authority_25` |
| counter_relation | 27 | `:138` `or -> and` in `_as_date` type guard | `test_m7a_counter_relation__as_date_27` |
| counter_relation | 30 | `:182` delete `if isinstance(members, (str, bytes, Mapping)): raise` | `test_m7a_counter_relation__members_30` |
| entitlement | 5 | `:122` `return False -> return None` | `test_m7a_entitlement__blank_5` |
| entitlement | 8 | `:138` `text[:10] -> text[:11]` | `test_m7a_entitlement__as_date_8` |
| entitlement | 13 | `:216` delete request-Mapping raise | `test_m7a_entitlement_gate_access_13` |
| entitlement | 15 | `:75` delete AUTHORITY_FLAGS-loop raise | `test_m7a_entitlement_refuse_nonfalse_authority_15` |
| entitlement | 18 | `:135` `len(text) < 10 -> < 11` | `test_m7a_entitlement__as_date_18` |
| entitlement | 21 | `:179` `return False -> return True` (container check) | `test_m7a_entitlement__document_entitled_21` |
| entitlement | 23 | `:218` delete entitlement-Mapping raise | `test_m7a_entitlement_gate_access_23` |
| entitlement | 24 | `:92` `frozen=True -> frozen=False` | `test_m7a_entitlement_module_24` |
| entitlement | 30 | `:177` `return False -> return None` | `test_m7a_entitlement__document_entitled_30` |

Notes on the two behaviour-bearing public-surface kills: entitlement #21 is
the sharpest survivor — a bare-string `document_ids` would have been treated
 as an entitlement, flipping a refusal to an allow and invoking the
 private-document loader; #25/#15 are defence-in-depth — they are
 unreachable while `AUTHORITY_FLAGS` is genuinely all-False, so the
 killing tests monkeypatch the module constant to the state the guard
 exists to catch.

## Equivalent arguments

- counter_relation #8, #18, #20, #28 and entitlement #9, #19, #27 — the
  `return x -> return None` operator fired on source that already reads
  `return None`; the mutated bytes are identical to the original (a
  harness artifact), so no test can distinguish them.
- counter_relation #9 (`_as_datetime:153` `return datetime(...) -> None`)
  — only changes a date-only string from "naive datetime" to `None`; its
  sole consumer `_aware_datetime` refuses naive values either way, and no
  public function distinguishes those two paths to `None`.

Judgment note, recorded honestly: counter_relation #17/#27 and entitlement
#5/#8/#18/#30 are also caller-collapsed through the public API; they are
counted KILLED (not equivalent) because their killing tests pin the
private helpers' typed contracts directly (`_blank`/`_document_entitled`
return literal bools; `_as_date` parses 10-char ISO dates and ignores
characters past the tenth; non-string input refuses to `None`). A reviewer
who regards those as implementation details may reclassify them as
equivalent; the killed-after count would drop accordingly.

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` censuses 19 fence points, all
in `residual/` and `event_response/` files. Neither target module appears
in that census, so **zero mutants were excluded** for QF coverage.

## What this does NOT prove

- A mutation score measures test strength against the drawn mutant set,
  not the statistical validity of any study or contract; nothing here is
  evidence about market data, residuals, or event response.
- No acceptance row moves to DONE; this sweep only strengthens the test
  evidence behind rows that cite these two guards.
- The sweep is bounded: 60 mutants from one seeded draw over the operator
  set, not an exhaustive enumeration of all possible mutations; sites not
  drawn (e.g. the counter-relation `frozen=True` decorator twin of
  entitlement #24) remain unswept.
- Six killing tests pin private-helper contracts directly (see the
  judgment note above); through public entry points alone those mutants
  are not observable.
- The two modules themselves are byte-identical to the base commit
  (sha256 receipts above; `git diff --stat` lists only the two owned
  files).
