Audited head: 1c3e2215ee395217f2d8349b4e9e41eb028bd497

# Round-11 acceptance audit, group A (R195's class; families A0, A1, A2) — PR #7905

## Identity receipt and zero-drift proof (after the re-bind, before any other run; verbatim)
```
2026-09-30T01:18:02Z
$ git -C $WT rev-parse HEAD
1c3e2215ee395217f2d8349b4e9e41eb028bd497
$ git -C $WT status --porcelain
(end status)
$ git log --format=... --name-status $B944..$HEAD
1c3e2215ee395217f2d8349b4e9e41eb028bd497 d5c9b9e87e31f96a59f388b27bd257ed6e0fb177 | mastermindx-2 | chore: remove accidental connector test file

D	NOT_A_REAL_PATH
d5c9b9e87e31f96a59f388b27bd257ed6e0fb177 b944cd3574e04daa0a519b942dd5f6947e2e96f1 | mastermindx-2 | x

A	NOT_A_REAL_PATH
$ git diff --name-status $B944 $HEAD
(end diff)
$ git rev-parse $B944^{tree} $HEAD^{tree}
0ea4e6658ef2f97a27e372d773866c706424b93d
0ea4e6658ef2f97a27e372d773866c706424b93d
$ git ls-tree $HEAD NOT_A_REAL_PATH
(end ls-tree)
test -e NOT_A_REAL_PATH: false
$ diff -r $WT/{engine,tests,lib,config} a/tree/...
engine identical
tests identical
lib identical
config identical
```
- The last block is mine: my mutable tree `a/tree` is byte-identical (diff -rq) to `$WT` at $HEAD for config/ engine/ lib/ tests/, so runs from it are runs on $HEAD's tree.
- Zero-drift holds: two commits, add/delete of NOT_A_REAL_PATH only; empty name-status diff; tree 0ea4e6658ef2 at both; path absent in tree and on disk.

## Evidence provenance
- MADE BEFORE THE RE-BIND, on $B944's tree (reused only because the zero-drift proof holds): A0 (both interpreters), the A1 harness at PYTHONHASHSEED=0 (both interpreters), the A1-values walk Q1 and Q2 (3.14).
- MADE AFTER THE RE-BIND, at $HEAD: the probe file on 3.12 and 3.14; the probe file against $R10HEAD's validator; the A1-values walk Q3; the A1 harness at PYTHONHASHSEED=12345 with int_max_str_digits=640; the unchanged seat walk Q3 (the pre-stop run was killed by the stop at 100/676 paths and was restarted from zero).

## A0 — round-10 group B probe file, unchanged, at $HEAD
- Copy: `a/a0/test_envelope_audit_probes_r10_b.py` + its `g2common.py` (identical to the seat walker's).
- `PYTHONPATH=. <py> -m pytest -p no:cacheprovider -q -rA a/a0/test_envelope_audit_probes_r10_b.py` from `a/tree`:
  - venv312_min (3.12.13): `72 passed in 2.70s`
  - venv_t1 (3.14.7): `72 passed in 2.67s`
- Accounting: 57 `test_b_r10_*` finding probes (expected refusal) now pass on both = B-R10-B1/B2 refused; 15 `ctl_` controls pass. 0 fail, 0 error.
- Made on $B944's tree (pre-re-bind); reusable under the zero-drift proof.

## A1 — the entry, argument by argument
Harness `a/a1/a1_run.py` with values `a/a1/a1values.py` (every hostile method appends to `CALLS` and then raises).
- Value set (98 per placement): Fraction slots assigned after construction with None / text / float / bool / hostile int subclass (24 instrumented dunders) / Fraction / int subclass, as numerator and denominator; zero and negative denominators, (2,4), (0,5), (-6,4), slot-less Fractions (object.__new__); ints and Fraction parts at 10**640-1, 10**640, negatives; subclasses of int, Fraction, IntEnum, str (plain and instrumented); instances, metaclass-made instances and the classes themselves for each of `__class__` (property), `__hash__`, `__eq__`, `__instancecheck__`, `__subclasscheck__`, `__getattribute__`, `__len__`, `__iter__`, `__index__`, `__bool__`; an instance whose `__class__` property claims `dict`; a Mapping.register'd class; an instrumented dict subclass; dicts keyed by int / float / NaN / bool / None / Fraction / tuple / mixed / 640-digit int / lone surrogate / str subclass; lone-surrogate strs.
- Placements, per quarter Q1-Q3: workspace as a whole; 22 workspace fields on the envelope route and the same 22 on the non-envelope route (event_id, fiscal_period and its three fields, sources, the release entry and its kind/receipt_state/document_id, facts, a present pg_ row and its value/metric/source_span/source_span.document_id/receipt/span_start_byte, a typed_absence and its reason, a new root key, a new row key); hash-colliding keys with an instrumented `__eq__` inserted in 5 mappings on the read path (armed only during the call); source_texts as a whole, as the release value, as an extra value, and 7 key forms (str subclass, lone surrogate, int, None, colliding, tuple, Fraction) plus the str-subclass and lone-surrogate release text; fiscal_scope as a whole, each of its 4 items, and 10 forms (list, tuple subclass, len 3/5, str-subclass items, instrumented str item, fullwidth and Arabic-Indic digits, basic ISO format, lone surrogate); depth 29-34 and size 99,999/100,000/100,001 (None, and 640-digit ints / canonical Fractions) at an unread release-entry key; 5 bound values at an unread release-entry key.
- Results, 13,788 runs per interpreter, identical flags on 3.12.13 (venv312_min) and 3.14.7 (venv_t1), PYTHONHASHSEED=0 (made on $B944's tree):
  - `{'CTRL_OK': 42, 'refused': 13692, 'ACCEPTED': 42, 'CTRL_REFUSED': 12}`; **0 exceptions other than EconomicObservationError, 0 calls into value-supplied code.**
  - The 42 ACCEPTED are all `zz_new_root_key` (a new top-level workspace key with an admitted value) — R7 G2-O1's recorded observation (top-level keys are not the validator's contract); binds nothing.
  - Controls: untampered Q1-Q3 accepted; depth 32 accepted / 33, 34 refused; 100,000 values accepted / 100,001 refused (both with None and with 640-digit parts); basic-format fiscal_scope (`20250701`) accepted identically; the 5 unread-key bound values accepted (n-B2).
  - 30 of 13,788 outcomes differ between interpreters in message text only (see note A-R11-n2); 0 differ in flag.
- R196's net inside A1 (not a finding): 46 placement groups reach the R196 conversion message: the slot-less Fractions (cause AttributeError, raised by the walk's own `.numerator` read, stdlib code) at every placement, and the non-envelope `source_span.document_id` list/dict (cause TypeError, B-R10-B2's site).
- Byte-only outcome check (at $HEAD, 3.14): the same 13,788 runs under PYTHONHASHSEED=12345 and `sys.set_int_max_str_digits(640)` (the interpreter's minimum): `{'CTRL_OK': 42, 'refused': 13692, 'ACCEPTED': 42, 'CTRL_REFUSED': 12}`, 0 flag and 0 message differences against PYTHONHASHSEED=0 / default limit.

## Probe file `a/test_envelope_audit_probes_r11_a.py` (all CONTROLS; no blocking finding reproduced)
- At $HEAD (tree identical to $WT), from `a/tree`: 3.12.13 venv312_min `599 passed in 5.26s`; 3.14.7 venv_t1 `599 passed in 5.14s`.
- Against $R10HEAD's validator (`a/r10tree` = the same copy with `git show 6caa2ffc1a95:engine/company_intelligence/economic_observations.py`; engine diff R10HEAD..HEAD is that one file), 3.14: `56 failed, 543 passed in 10.96s` — the Fraction-slot, slot-less, metaclass `__hash__`/`__class__`/`__getattribute__`, instance `__class__`/`__getattribute__`, instrumented-str and zero-denominator probes fail there (value code runs or a non-refusal exception escapes); the bound controls pass at both.

## A2 — the walk
- A1-values copy `a/walk_a1/seat_walk_a1.py` (the seat walker with VALUES = 52 A1 values, every call instrumented; extra/rename keys widened with an unreduced-Fraction key, a lone-surrogate key, a str-subclass key and a 10**640 key), envelope route, 3.14, 676 paths per quarter:
  - Q1 (made on $B944's tree): `{'rejected': 17970, 'OK_ACCEPTED_DIFFERENT': 36}` in 281.0 s
  - Q2 (made on $B944's tree): `{'rejected': 17970, 'OK_ACCEPTED_DIFFERENT': 36}` in 272.8 s
  - Q3 (at $HEAD): `{'rejected': 17970, 'OK_ACCEPTED_DIFFERENT': 36}` in 276.9 s
  - 0 CALLED (value code run), 0 EXC, across 54,018 runs. The 36 accepted per quarter are all n-B2: extra keys of admitted types in `fiscal_period` (6) and the release entry (6), and tampers inside the entry's unread `filing_key` (18), `source_sha256` (2), `form` (2), `url` (2). **No tamper of a `pg_` fact row, `event_id`, `fiscal_period.calendar_end`, or the entry's kind/receipt_state/document_id is accepted.**
- Unchanged seat walk (`a/walk/seat_walk.py`, the seat's 73 values + key ops, byte-identical copy), Q3 envelope, 3.14, at $HEAD (restarted after the stop; the pre-stop $B944 run reached only 100/676 paths before it was killed: `{'rejected': 7270, 'OK_ACCEPTED_DIFFERENT': 217, 'ok_jsonequal': 9}`):
  - last line at the report's close: `Q3 envelope progress 400 676 {'rejected': 29624, 'OK_ACCEPTED_DIFFERENT': 217, 'ok_jsonequal': 45} s 1444.1`
  - PARTIAL (turn cap): the run keeps going under its 3,000 s alarm and writes `a/walk/unchanged_h1c3e_Q3_envelope_314.log` and `a/walk/seat_walk_unchanged_h1c3e_Q3_envelope_314.jsonl`.
  - classification of every non-refused record so far (kind, path): `{('OK_ACCEPTED_DIFFERENT', 'fiscal_period'): 6, ('OK_ACCEPTED_DIFFERENT', 'fiscal_period.quarter'): 1, ('OK_ACCEPTED_DIFFERENT', 'sources.0'): 6, ('OK_ACCEPTED_DIFFERENT', 'sources.0.filing_key'): 108, ('OK_ACCEPTED_DIFFERENT', 'sources.0.source_sha256'): 32, ('OK_ACCEPTED_DIFFERENT', 'sources.0.form'): 32, ('OK_ACCEPTED_DIFFERENT', 'sources.0.url'): 32}`
  - Seat's figure for comparison: 50,482 runs per quarter/route/interpreter, none raised; envelope accepts only n-B1 quarter and n-B2. Seat JSONL for Q3 envelope was not in `$SP/r10_work/sweep/` (Q1/Q2 only), so the per-quarter accept count is compared by class, not by number.

## Identity after the last run
```
2026-09-30T01:44:34Z
$ git -C $WT rev-parse HEAD
1c3e2215ee395217f2d8349b4e9e41eb028bd497
$ git -C $WT status --porcelain
(end status)
```

## Verdict (group A: A0, A1, A2)
STATUS: ACCEPT under the release-blocking bar for R195's class. No blocking finding.

Non-blocking notes (one line each, no further search):
- A-R11-n1 (observation, R196 dependence): a slot-less exact Fraction (`object.__new__(Fraction)`) makes the walk's own `item.numerator` read raise AttributeError (economic_observations.py:578); it is refused only through R196's conversion, cause AttributeError. Fail-closed; stdlib code, not value code.
- A-R11-n2 (observation, message only): economic_observations.py:192 `raise EconomicObservationError(str(exc))` copies the interpreter's TypeError text into the refusal, so 30 refusal messages differ between 3.12 and 3.14 ("unhashable type: 'dict'" vs "cannot use 'dict' as a set element ..."); outcome identical.
- A-R11-n3 (observation, known G2-O1): a new top-level workspace key of any admitted type is accepted (42 runs); binds nothing.
- A-R11-n4 (code quality): the entry's first test `type(workspace) is not dict and not _unprintable(workspace)` (economic_observations.py:627) routes an unprintable non-dict to the later "cannot print" refusal; both branches refuse.

## Close-out (coordinator wrap-up order: Sol accepted R11 at 01:33Z, comment 5902318060)
- Unchanged seat walk stopped by SIGALRM on the coordinator's order. Its alarm output: `Q3 envelope TIMEOUT {'rejected': 34785, 'OK_ACCEPTED_DIFFERENT': 217, 'ok_jsonequal': 53} s 1705.1 exit=3 `
- Classification of every non-refused record of that walk (kind, path): `{('OK_ACCEPTED_DIFFERENT', 'fiscal_period'): 6, ('OK_ACCEPTED_DIFFERENT', 'fiscal_period.quarter'): 1, ('OK_ACCEPTED_DIFFERENT', 'sources.0'): 6, ('OK_ACCEPTED_DIFFERENT', 'sources.0.filing_key'): 108, ('OK_ACCEPTED_DIFFERENT', 'sources.0.source_sha256'): 32, ('OK_ACCEPTED_DIFFERENT', 'sources.0.form'): 32, ('OK_ACCEPTED_DIFFERENT', 'sources.0.url'): 32}` — all n-B1 (quarter) or n-B2 (fiscal_period / release-entry extra keys and unread metadata); no pg_ fact-row tamper accepted; no EXC record.
- Final identity receipt (supersedes the one above):
```
2026-09-30T01:47:00Z
$ git -C $WT rev-parse HEAD
1c3e2215ee395217f2d8349b4e9e41eb028bd497
$ git -C $WT status --porcelain
(end status)
```
- STATUS unchanged: ACCEPT for group A; no release-blocking finding.
